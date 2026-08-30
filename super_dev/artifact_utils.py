from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

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

_CHANGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?$")
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


def sanitize_artifact_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "-").replace("_", "-")


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
    if not isinstance(value, str):
        return ""
    change_id = value.strip()
    if not change_id or not _CHANGE_ID_PATTERN.fullmatch(change_id):
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
    workflow_state_path = project_path / ".super-dev" / "workflow-state.json"
    try:
        workflow_payload = json.loads(workflow_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        workflow_payload = {}

    if isinstance(workflow_payload, dict):
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
        prefixed = [
            path
            for path in candidates
            if path.name.startswith(f"{sanitize_artifact_name(preferred_prefix)}-")
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
