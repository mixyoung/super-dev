"""Current-code verification evidence used by quality and release checks."""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

from ..config import ConfigManager
from ..evidence_identity import (
    build_evidence_identity,
    evidence_identity_matches,
    load_json_payload,
)
from ..extensions.builtins.fresh_verification import (
    JUnitSummaryError,
    parse_junit_summary,
)
from ..extensions.evidence import EvidenceStore, build_candidate_identity, candidate_matches


def fresh_verification_required(config: object) -> bool:
    extensions = getattr(config, "extensions", {})
    if not isinstance(extensions, dict) or extensions.get("enabled") is not True:
        return False
    allowed = extensions.get("allowed_builtin_methods", [])
    return isinstance(allowed, list) and "fresh-verification" in allowed


def _latest_fresh_verification_evidence(
    project_dir: Path,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    Path | None,
    list[Path],
]:
    store = EvidenceStore(project_dir)
    payload = store.latest_result(extension_id="fresh-verification")
    if not isinstance(payload, dict):
        return None, None, None, []

    run_id = str(payload.get("run_id", "")).strip()
    if not run_id:
        return payload, None, None, []
    try:
        run_dir = store.run_dir(run_id)
    except ValueError:
        return payload, None, None, []

    dependencies: list[Path] = []
    result_path = run_dir / "result.json"
    if result_path.is_file():
        dependencies.append(result_path)

    summary_path = run_dir / "pytest-summary.json"
    if summary_path.is_file():
        dependencies.append(summary_path)
        try:
            loaded_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError):
            loaded_summary = None
        summary_payload = loaded_summary if isinstance(loaded_summary, dict) else None
    else:
        summary_payload = None

    junit_candidate = run_dir / "pytest.xml"
    if junit_candidate.is_file():
        dependencies.append(junit_candidate)
        junit_path: Path | None = junit_candidate
    else:
        junit_path = None
    return payload, summary_payload, junit_path, dependencies


@dataclass(frozen=True)
class FreshVerificationEvidence:
    """Read-only view of the latest fresh verification for the current code version."""

    payload: dict[str, Any] | None
    summary_payload: dict[str, Any] | None
    dependencies: tuple[Path, ...]
    candidate_digest: str
    run_id: str = ""
    status: str = ""
    passed: bool = False
    detail: str = ""
    counts: dict[str, int] = field(default_factory=dict)


def inspect_current_fresh_verification(project_dir: Path) -> FreshVerificationEvidence:
    """Inspect, without writing, whether the latest fresh result proves this code version."""

    project_dir = Path(project_dir).resolve()
    payload, summary_payload, junit_path, dependencies = _latest_fresh_verification_evidence(
        project_dir
    )
    current_candidate = build_candidate_identity(project_dir)
    candidate_digest = current_candidate.candidate_digest

    if payload is None:
        return FreshVerificationEvidence(
            payload=payload,
            summary_payload=summary_payload,
            dependencies=tuple(dependencies),
            candidate_digest=candidate_digest,
            detail=("完成前验证已启用，但当前代码版本缺少证据；" "不得改用环境中的 pytest 结果。"),
        )
    if str(payload.get("extension_id", "")).strip() != "fresh-verification":
        return FreshVerificationEvidence(
            payload=payload,
            summary_payload=summary_payload,
            dependencies=tuple(dependencies),
            candidate_digest=candidate_digest,
            detail="完成前验证证据类型不匹配，需重新补证据。",
        )

    run_id = str(payload.get("run_id", "")).strip()
    status = str(payload.get("status", "")).strip().upper()

    def make_evidence(
        *,
        detail: str,
        passed: bool = False,
        counts: dict[str, int] | None = None,
    ) -> FreshVerificationEvidence:
        return FreshVerificationEvidence(
            payload=payload,
            summary_payload=summary_payload,
            dependencies=tuple(dependencies),
            candidate_digest=candidate_digest,
            run_id=run_id,
            status=status,
            passed=passed,
            detail=detail,
            counts=counts or {},
        )

    if not candidate_matches(payload, current_candidate):
        return make_evidence(
            detail="完成前验证证据已过期，与当前代码版本不匹配；需重新补证据。",
        )
    if status in {"FAIL", "BLOCKED"}:
        findings = payload.get("blocking_findings", [])
        finding_text = (
            "; ".join(str(item) for item in findings) if isinstance(findings, list) else ""
        )
        status_label = {
            "FAIL": "失败（`FAIL`）",
            "BLOCKED": "受阻（`BLOCKED`）",
        }[status]
        detail = f"当前完成前验证状态为{status_label}"
        if finding_text:
            detail += f"：{finding_text}"
        return make_evidence(detail=detail)
    if status != "PASS":
        return make_evidence(
            detail=f"完成前验证证据状态无效：{status or 'missing'}。",
        )
    if not isinstance(summary_payload, dict):
        return make_evidence(
            detail="完成前验证缺少当前运行的 pytest_summary。",
        )
    if str(summary_payload.get("run_id", "")).strip() != run_id:
        return make_evidence(
            detail="完成前验证的测试摘要与运行编号不匹配。",
        )
    summary_status = str(summary_payload.get("status", "")).strip().upper()
    if summary_status and summary_status != status:
        return make_evidence(
            detail="完成前验证的测试摘要状态与结果不一致。",
        )
    summary = summary_payload.get("pytest_summary")
    if not isinstance(summary, dict):
        return make_evidence(
            detail="完成前验证缺少结构化 pytest_summary。",
        )
    if junit_path is None:
        return make_evidence(
            detail="完成前验证缺少当前运行的 JUnit XML（pytest.xml）。",
        )
    try:
        junit_summary = parse_junit_summary(junit_path)
    except JUnitSummaryError as exc:
        return make_evidence(
            detail=f"完成前验证的 JUnit XML 无效：{exc}",
        )

    actual_summary = junit_summary.to_dict()
    counts: dict[str, int] = {}
    for key in ("tests", "executed", "skipped", "failures", "errors"):
        value = summary.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return make_evidence(
                detail=f"完成前验证的 pytest_summary.{key} 无效。",
            )
        counts[key] = value
        if value != actual_summary[key]:
            return make_evidence(
                detail=(
                    f"完成前验证的 pytest_summary.{key} 与 JUnit XML 不一致："
                    f"saved={value}, junit={actual_summary[key]}。"
                ),
                counts=counts,
            )

    duration = summary.get("duration_seconds")
    if (
        isinstance(duration, bool)
        or not isinstance(duration, int | float)
        or not math.isfinite(float(duration))
        or duration < 0
    ):
        return make_evidence(
            detail="完成前验证的 pytest_summary.duration_seconds 无效。",
            counts=counts,
        )
    if float(duration) != actual_summary["duration_seconds"]:
        return make_evidence(
            detail=(
                "完成前验证的 pytest_summary.duration_seconds 与 JUnit XML 不一致："
                f"saved={duration}, junit={actual_summary['duration_seconds']}。"
            ),
            counts=counts,
        )

    junit_digest = summary.get("junit_digest")
    if not isinstance(junit_digest, str) or junit_digest != actual_summary["junit_digest"]:
        return make_evidence(
            detail="完成前验证的 pytest_summary.junit_digest 与 JUnit XML 不一致。",
            counts=counts,
        )
    if counts["executed"] != counts["tests"] - counts["skipped"]:
        return make_evidence(
            detail="完成前验证的实际执行数与总数/跳过数不一致。",
            counts=counts,
        )
    if counts["executed"] <= 0 or counts["failures"] or counts["errors"]:
        return make_evidence(
            detail=(
                "完成前验证的结构化计数不满足通过条件："
                f"tests={counts['tests']}, executed={counts['executed']}, "
                f"skipped={counts['skipped']}, failures={counts['failures']}, "
                f"errors={counts['errors']}。"
            ),
            counts=counts,
        )
    return make_evidence(
        passed=True,
        detail=(
            "完成前验证通过："
            f"tests={counts['tests']}, executed={counts['executed']}, "
            f"skipped={counts['skipped']}, failures={counts['failures']}, "
            f"errors={counts['errors']}。"
        ),
        counts=counts,
    )


def quality_evidence_dependency_paths(
    project_dir: Path,
    *,
    project_name: str,
    frontend_required: bool,
    include_fresh_verification: bool = True,
) -> list[Path]:
    output_dir = Path(project_dir) / "output"
    dependencies = [output_dir / f"{project_name}-uiux.md"]
    if frontend_required:
        dependencies[:0] = [
            output_dir / f"{project_name}-ui-review.json",
            output_dir / f"{project_name}-ui-contract-alignment.json",
        ]
    config = ConfigManager(project_dir).load()
    if include_fresh_verification and fresh_verification_required(config):
        evidence = inspect_current_fresh_verification(project_dir)
        dependencies.extend(evidence.dependencies)
    return dependencies


def stored_quality_evidence_dependencies(
    project_dir: Path,
    payload: dict[str, Any],
) -> tuple[list[Path], str]:
    """Validate and return the dependencies recorded by a quality report."""

    identity = payload.get("evidence_identity", {})
    if not isinstance(identity, dict):
        return [], "missing"
    raw_dependencies = identity.get("dependencies", [])
    if not isinstance(raw_dependencies, list) or not all(
        isinstance(item, str) and item.strip() for item in raw_dependencies
    ):
        return [], "missing"
    dependency_count = identity.get("dependency_count")
    if (
        isinstance(dependency_count, bool)
        or not isinstance(dependency_count, int)
        or dependency_count != len(raw_dependencies)
    ):
        return [], "missing"

    project_dir = Path(project_dir).resolve()
    dependencies: list[Path] = []
    for raw_label in raw_dependencies:
        label = raw_label.strip()
        label_path = Path(label)
        windows_path = PureWindowsPath(label)
        if label_path.is_absolute() or bool(windows_path.drive) or ".." in windows_path.parts:
            return [], "unsafe"
        resolved = (project_dir / label_path).resolve(strict=False)
        try:
            resolved.relative_to(project_dir)
        except ValueError:
            return [], "unsafe"
        if not resolved.is_file():
            return [], "missing"
        dependencies.append(resolved)

    expected = build_evidence_identity(
        project_dir,
        artifact_name="quality-gate",
        dependencies=dependencies,
        run_id=str(identity.get("run_id", "")),
    )
    if expected.get("dependencies") != raw_dependencies:
        return [], "mismatch"
    matched, reason = evidence_identity_matches(payload, expected=expected)
    return (dependencies, "matched") if matched else ([], reason)


def quality_fresh_binding_matches(
    dependencies: list[Path],
    *,
    candidate_digest: str,
) -> tuple[bool, str]:
    """Check that quality evidence binds one complete passing run to the candidate."""

    fresh_results: list[tuple[Path, dict[str, Any]]] = []
    for path in dependencies:
        if path.name != "result.json":
            continue
        payload = load_json_payload(path)
        if str(payload.get("extension_id", "")).strip() == "fresh-verification":
            fresh_results.append((path, payload))
    if len(fresh_results) != 1:
        return False, "missing"

    result_path, payload = fresh_results[0]
    run_id = str(payload.get("run_id", "")).strip()
    if not run_id or result_path.parent.name != run_id:
        return False, "invalid"
    sibling_names = {path.name for path in dependencies if path.parent == result_path.parent}
    if not {"result.json", "pytest-summary.json", "pytest.xml"}.issubset(sibling_names):
        return False, "incomplete"
    if str(payload.get("status", "")).strip().upper() != "PASS":
        return False, "not_passed"
    candidate = payload.get("candidate", {})
    if not isinstance(candidate, dict):
        return False, "candidate_missing"
    bound_digest = str(candidate.get("candidate_digest", "")).strip()
    if not candidate_digest or bound_digest != candidate_digest:
        return False, "candidate_mismatch"
    return True, "matched"
