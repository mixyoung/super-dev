from __future__ import annotations

import hashlib
import re
import subprocess
import unicodedata
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .state_store import StateStore

ARTIFACT_SUFFIX_WEIGHTS: dict[str, int] = {
    "-prd.md": 5,
    "-architecture.md": 5,
    "-uiux.md": 5,
    "-research.md": 4,
    "-spec-compliance.json": 4,
    "-spec-compliance.md": 4,
    "-architecture-drift.json": 4,
    "-architecture-drift.md": 4,
    "-uiux-compliance.json": 4,
    "-uiux-compliance.md": 4,
    "-ui-contract.json": 4,
    "-frontend-runtime.json": 4,
    "-ui-review.json": 3,
    "-ui-contract-alignment.json": 3,
    "-quality-gate.md": 3,
    "-proof-pack.json": 3,
    "-release-readiness.json": 3,
    "-product-audit.json": 2,
    "-knowledge-bundle.json": 1,
    "-pipeline-metrics.json": 1,
}

CORE_ARTIFACT_SUFFIXES: tuple[str, ...] = (
    "-research.md",
    "-prd.md",
    "-architecture.md",
    "-uiux.md",
)

_CHANGE_ID_PATTERN = re.compile(r"^[^\W_](?:[\w.-]{0,126}[^\W_])?$", re.UNICODE)
_CHANGE_BRANCH_PREFIXES = {
    "bugfix",
    "chore",
    "docs",
    "feature",
    "fix",
    "hotfix",
    "patch",
    "refactor",
    "release",
    "test",
}

WORK_ITEM_IDENTITY_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class WorkItemIdentity:
    work_item_id: str
    artifact_prefix: str
    active_change_id: str
    binding_status: str
    legacy: bool
    valid: bool
    issues: tuple[str, ...] = ()


def sanitize_artifact_name(name: str) -> str:
    raw = unicodedata.normalize("NFKC", str(name)).strip()
    if not raw:
        return ""
    value = raw.lower()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value).strip(" .-")
    return value or "project"


def _artifact_prefix_variants(prefix: str) -> set[str]:
    """返回当前格式和旧格式的产物前缀，兼容已有报告。"""

    raw = str(prefix).strip().lower()
    return {value for value in (raw, sanitize_artifact_name(raw)) if value}


def ui_contract_filename(name: str) -> str:
    """Keep valid legacy filenames; encode unsafe display names on every OS.

    This is only the UI contract filename, not a project/change identifier or a
    replacement for the display name. A digest distinguishes names whose unsafe
    characters would otherwise collapse to the same replacement.
    """
    unsafe = r'[<>:"/\\|?*\x00-\x1f]'
    if re.search(unsafe, name):
        readable = re.sub(unsafe, "-", name).strip(" .-")[:64] or "project"
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
        name = f"{readable}-{digest}"
    return f"{name}-ui-contract.json"


def _nested_values_for_key(payload: Any, key: str) -> Iterator[Any]:
    if isinstance(payload, dict):
        if key in payload:
            yield payload[key]
        for value in payload.values():
            if isinstance(value, dict | list):
                yield from _nested_values_for_key(value, key)
    elif isinstance(payload, list):
        for value in payload:
            if isinstance(value, dict | list):
                yield from _nested_values_for_key(value, key)


def _validated_change_id(project_dir: Path, value: Any) -> str:
    change_id = normalize_work_item_id(value)
    if not change_id:
        return ""

    changes_root = (Path(project_dir).resolve() / ".super-dev" / "changes").resolve()
    try:
        change_dir = (changes_root / change_id).resolve()
        change_dir.relative_to(changes_root)
    except (OSError, RuntimeError, ValueError):
        return ""
    if not change_dir.is_dir():
        return ""
    return change_dir.name


def _valid_identity_text(value: Any) -> str:
    return normalize_work_item_id(value)


def normalize_work_item_id(value: Any) -> str:
    """Return the single NFKC identity form accepted by change and work-item readers."""

    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized or not _CHANGE_ID_PATTERN.fullmatch(normalized):
        return ""
    return normalized


def _load_workflow_identity_payload(project_dir: Path) -> dict[str, Any]:
    return StateStore(Path(project_dir)).load_workflow()


def resolve_work_item_identity(project_dir: Path) -> WorkItemIdentity:
    """Read the standard-flow identity without selecting by age or directory order."""

    project_path = Path(project_dir).resolve()
    payload = _load_workflow_identity_payload(project_path)
    explicit_work_item = (
        "work_item_id" in payload
        and str(payload.get("flow_variant", "standard")).strip().lower() != "seeai"
    )
    raw_work_item = payload.get("work_item_id", "")
    work_item_id = _valid_identity_text(raw_work_item)
    raw_active = payload.get("active_change_id", payload.get("change_id", ""))
    active_text = _valid_identity_text(raw_active)

    if not explicit_work_item:
        legacy_change = _validated_change_id(project_path, active_text)
        legacy_prefix = sanitize_artifact_name(legacy_change or payload.get("artifact_prefix", ""))
        return WorkItemIdentity(
            work_item_id=legacy_change,
            artifact_prefix=legacy_prefix,
            active_change_id=legacy_change,
            binding_status="bound" if legacy_change else "",
            legacy=True,
            valid=True,
        )

    issues: list[str] = []
    if not work_item_id:
        issues.append("invalid_work_item_id")
    expected_prefix = sanitize_artifact_name(work_item_id)
    stored_prefix = str(payload.get("artifact_prefix", "")).strip()
    if stored_prefix and stored_prefix != expected_prefix:
        issues.append("artifact_prefix_mismatch")

    binding_status = str(payload.get("binding_status", "")).strip().lower()
    if not binding_status:
        binding_status = "bound" if active_text else "pre_spec"
    if binding_status not in {"pre_spec", "bound"}:
        issues.append("invalid_binding_status")
    if binding_status == "pre_spec" and active_text:
        issues.append("pre_spec_has_active_change")
    if binding_status == "bound" and active_text != work_item_id:
        issues.append("active_change_mismatch")

    validated_active = ""
    if binding_status == "bound" and active_text == work_item_id:
        validated_active = _validated_change_id(project_path, active_text)
        if not validated_active:
            issues.append("bound_change_missing")

    return WorkItemIdentity(
        work_item_id=work_item_id,
        artifact_prefix=expected_prefix,
        active_change_id=validated_active,
        binding_status=binding_status,
        legacy=False,
        valid=not issues,
        issues=tuple(issues),
    )


def _current_git_branch(project_dir: Path) -> str:
    try:
        result = subprocess.run(  # nosec B603 B607
            ["git", "-C", str(Path(project_dir).resolve()), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def resolve_active_change_id(project_dir: Path) -> str:
    """Resolve the active change only from explicit workflow or Git evidence."""

    project_path = Path(project_dir).resolve()
    workflow_payload = _load_workflow_identity_payload(project_path)

    if isinstance(workflow_payload, dict):
        if (
            "work_item_id" in workflow_payload
            and str(workflow_payload.get("flow_variant", "standard")).strip().lower() != "seeai"
        ):
            identity = resolve_work_item_identity(project_path)
            return identity.active_change_id if identity.valid else ""
        for key in ("active_change_id", "change_id"):
            for value in _nested_values_for_key(workflow_payload, key):
                change_id = _validated_change_id(project_path, value)
                if change_id:
                    return change_id

    branch = _current_git_branch(project_path)
    branch_parts = [part.strip() for part in branch.split("/") if part.strip()]
    if len(branch_parts) >= 2 and branch_parts[0].lower() in _CHANGE_BRANCH_PREFIXES:
        return _validated_change_id(project_path, branch_parts[-1])
    return ""


def _artifact_prefix_for(path: Path) -> str:
    filename = path.name
    for suffix in sorted(ARTIFACT_SUFFIX_WEIGHTS.keys(), key=len, reverse=True):
        if filename.endswith(suffix):
            return filename[: -len(suffix)]
    return ""


def resolve_project_artifact_prefix(
    project_dir: Path,
    *,
    configured_name: str = "",
    fallback_name: str = "",
) -> str:
    project_path = Path(project_dir).resolve()
    identity = resolve_work_item_identity(project_path)
    if not identity.legacy and identity.work_item_id:
        return identity.artifact_prefix
    output_dir = project_path / "output"
    configured = sanitize_artifact_name(configured_name)
    fallback = sanitize_artifact_name(fallback_name or project_path.name)

    scores: dict[str, int] = defaultdict(int)
    freshness: dict[str, float] = defaultdict(float)
    if output_dir.exists():
        for path in output_dir.rglob("*"):
            if not path.is_file():
                continue
            prefix = _artifact_prefix_for(path)
            if not prefix:
                continue
            suffix = path.name[len(prefix) :]
            scores[prefix] += ARTIFACT_SUFFIX_WEIGHTS.get(suffix, 1)
            try:
                freshness[prefix] = max(freshness[prefix], path.stat().st_mtime)
            except OSError:
                pass

    def candidate_score(prefix: str) -> tuple[int, float, int]:
        return (
            scores.get(prefix, 0),
            freshness.get(prefix, 0.0),
            1 if prefix == configured and prefix else 0,
        )

    if configured and scores.get(configured, 0) > 0:
        return configured

    if scores:
        best = max(scores.keys(), key=candidate_score)
        if scores.get(best, 0) > 0:
            return best

    return configured or fallback or "project"


def resolve_current_artifact_prefix(
    project_dir: Path,
    *,
    configured_name: str = "",
    fallback_name: str = "",
) -> str:
    """Prefer the active change prefix when it owns at least one core artifact."""

    project_path = Path(project_dir).resolve()
    identity = resolve_work_item_identity(project_path)
    if not identity.legacy and identity.work_item_id:
        # A pre-Spec work item intentionally shadows every old active change and proof pack.
        return identity.artifact_prefix
    active_change_id = resolve_active_change_id(project_path)
    active_prefix = sanitize_artifact_name(active_change_id)
    output_dir = project_path / "output"
    if active_prefix and any(
        (output_dir / f"{active_prefix}{suffix}").is_file() for suffix in CORE_ARTIFACT_SUFFIXES
    ):
        return active_prefix
    return resolve_project_artifact_prefix(
        project_path,
        configured_name=configured_name,
        fallback_name=fallback_name,
    )


def latest_artifact(
    output_dir: Path,
    pattern: str,
    *,
    preferred_prefix: str = "",
    strict_prefix: bool = False,
) -> Path | None:
    directory = Path(output_dir)
    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    if preferred_prefix:
        prefix_variants = _artifact_prefix_variants(preferred_prefix)
        prefixed = [
            path
            for path in candidates
            if any(path.name.lower().startswith(f"{prefix}-") for prefix in prefix_variants)
        ]
        if prefixed:
            candidates = prefixed
        elif strict_prefix:
            return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def is_artifact_stale(path: Path | None, *, dependencies: Sequence[Path | None]) -> bool:
    if path is None or not path.exists() or not path.is_file():
        return False
    try:
        artifact_mtime = path.stat().st_mtime
    except OSError:
        return False
    for dependency in dependencies:
        if dependency is None or not dependency.exists() or not dependency.is_file():
            continue
        try:
            if dependency.stat().st_mtime > artifact_mtime:
                return True
        except OSError:
            continue
    return False
