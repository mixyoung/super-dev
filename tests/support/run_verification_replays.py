"""内部完成前验证回放执行器；仅供项目维护者从仓库根目录运行。"""

from __future__ import annotations

import json
import os
import socket
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

from super_dev.cli_release_quality_mixin import CliReleaseQualityMixin
from super_dev.evidence_identity import build_evidence_identity
from super_dev.extensions.evidence import EvidenceStore, build_candidate_identity
from super_dev.extensions.models import ExtensionStatus
from super_dev.extensions.service import ExtensionService, ProbeOutcome
from super_dev.extensions.verification_metrics import (
    REPLAY_MEASUREMENT_SCOPE,
    VerificationMetricsSummary,
    summarize_verification_metrics,
)
from super_dev.release_readiness import ReleaseReadinessEvaluator, ReleaseReadinessReport
from super_dev.review_state import save_workflow_state
from super_dev.reviewers.quality_gate import quality_evidence_dependency_paths
from super_dev.user_directories import UserDirectoryContext
from tests.support.user_surface_snapshot import (
    assert_safe_isolated_home,
    capture_user_surfaces,
    collect_user_surface_paths,
    diff_surface_snapshots,
    has_surface_changes,
    path_is_within,
    unsafe_surface_states,
)
from tests.unit.test_release_readiness import (
    _prepare_release_ready_project,
    _prepare_spec_quality_change,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPLAY_CONTRACT_PATH = (
    PROJECT_ROOT / ".super-dev" / "changes" / "completion-verification" / "replay-scenarios.yaml"
)
EXPECTED_SCENARIO_IDS = (
    "current-pass-clean",
    "current-pass-partial-skip",
    "current-pass-non-strict-xpass",
    "old-pass-current-fail",
    "old-pass-current-candidate",
    "current-fail-assertion",
    "current-fail-strict-xpass",
    "no-tests-collected",
    "timeout-or-cancel",
    "candidate-changed-during-run",
)
REQUIRED_SCENARIO_EVIDENCE_FILES = (
    "legacy-report.json",
    "verification-result.json",
    "verification-release-report.json",
    "pytest-summary.json",
    "scenario-result.json",
)
REQUIRED_BATCH_EVIDENCE_FILES = (
    "batch-result.json",
    "completion-report.md",
)
_STATUS_VALUES = {"PASS", "FAIL", "BLOCKED"}
_SCENARIO_ENV_KEYS = {
    "COMSPEC",
    "LANG",
    "LC_ALL",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PATH",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "WINDIR",
}
_NETWORK_GUARD = """import socket

import pytest


def _network_disabled(*_args, **_kwargs):
    raise RuntimeError("verification replay network access is disabled")


@pytest.fixture(autouse=True)
def _disable_network(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", _network_disabled)
    monkeypatch.setattr(socket.socket, "connect", _network_disabled)
    monkeypatch.setattr(socket.socket, "connect_ex", _network_disabled)
"""


class ReplayBatchError(RuntimeError):
    """回放基础设施或安全合同未满足。"""


@dataclass(frozen=True)
class ReplayScenario:
    scenario_id: str
    expected_status: str
    expected_advisory: str = ""
    expected_new_run: bool = False


@dataclass(frozen=True)
class ScenarioExecution:
    scenario_id: str
    legacy_status: str
    verification_status: str
    legacy_duration_ms: float
    verification_duration_ms: float
    safety_regression: bool
    details: dict[str, object]


@dataclass(frozen=True)
class ReplayBatchResult:
    replay_run_id: str
    candidate_digest: str
    evidence_root: Path
    completion_report_path: Path
    records: tuple[dict[str, object], ...]
    summary: VerificationMetricsSummary


ScenarioRunner = Callable[[ReplayScenario, Path], ScenarioExecution]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _atomic_write_text(path, serialized)


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayBatchError(f"回放证据无法读取: {path.name}") from exc
    if not isinstance(payload, dict):
        raise ReplayBatchError(f"回放证据不是对象: {path.name}")
    return payload


def _load_contract(path: Path) -> tuple[ReplayScenario, ...]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ReplayBatchError("10 场景回放合同无法读取") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ReplayBatchError("10 场景回放合同版本无效")
    raw_scenarios = payload.get("scenarios")
    if not isinstance(raw_scenarios, list):
        raise ReplayBatchError("10 场景回放合同缺少场景列表")

    scenarios: list[ReplayScenario] = []
    for raw in raw_scenarios:
        if not isinstance(raw, dict):
            raise ReplayBatchError("10 场景回放合同含无效场景")
        scenario_id = raw.get("id")
        expected_status = raw.get("expected_status")
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ReplayBatchError("10 场景回放合同含空场景编号")
        if not isinstance(expected_status, str) or expected_status not in _STATUS_VALUES:
            raise ReplayBatchError(f"场景 {scenario_id} 的预期状态无效")
        expected_advisory = raw.get("expected_advisory", "")
        expected_new_run = raw.get("expected_new_run", False)
        if not isinstance(expected_advisory, str) or not isinstance(expected_new_run, bool):
            raise ReplayBatchError(f"场景 {scenario_id} 的附加合同无效")
        scenarios.append(
            ReplayScenario(
                scenario_id=scenario_id.strip(),
                expected_status=expected_status,
                expected_advisory=expected_advisory.strip(),
                expected_new_run=expected_new_run,
            )
        )

    scenario_ids = tuple(item.scenario_id for item in scenarios)
    if scenario_ids != EXPECTED_SCENARIO_IDS:
        raise ReplayBatchError("回放合同必须严格包含已确认的 10 个场景并保持既定顺序")
    return tuple(scenarios)


def _write_config(project_dir: Path, *, args: list[str], timeout_seconds: int) -> None:
    payload = {
        "name": "completion-verification-replay",
        "frontend": "next",
        "backend": "python",
        "extensions": {
            "enabled": True,
            "allowed_builtin_methods": ["fresh-verification"],
            "fresh_verification": {
                "profile": "pytest-current-python",
                "plan_id": "completion-verification-replay",
                "args": args,
                "timeout_seconds": timeout_seconds,
            },
        },
    }
    (project_dir / "super-dev.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _write_scenario_input(project_dir: Path, scenario_id: str) -> tuple[list[str], int]:
    test_path = project_dir / "test_replay.py"
    if scenario_id == "current-pass-clean":
        test_path.write_text("def test_clean():\n    assert True\n", encoding="utf-8")
    elif scenario_id == "current-pass-partial-skip":
        test_path.write_text(
            """import pytest


def test_runs():
    assert True


@pytest.mark.skip(reason="controlled partial skip")
def test_skipped():
    pass
""",
            encoding="utf-8",
        )
    elif scenario_id == "current-pass-non-strict-xpass":
        test_path.write_text(
            """import pytest


@pytest.mark.xfail(reason="controlled non-strict xpass")
def test_non_strict_xpass():
    assert True
""",
            encoding="utf-8",
        )
    elif scenario_id in {"old-pass-current-fail", "old-pass-current-candidate"}:
        test_path.write_text("def test_initial_pass():\n    assert True\n", encoding="utf-8")
    elif scenario_id == "current-fail-assertion":
        test_path.write_text("def test_assertion_failure():\n    assert False\n", encoding="utf-8")
    elif scenario_id == "current-fail-strict-xpass":
        test_path.write_text(
            """import pytest


@pytest.mark.xfail(reason="controlled strict xpass", strict=True)
def test_strict_xpass():
    assert True
""",
            encoding="utf-8",
        )
    elif scenario_id == "no-tests-collected":
        empty_dir = project_dir / "empty-tests"
        empty_dir.mkdir()
        return ["-q", "empty-tests"], 10
    elif scenario_id == "timeout-or-cancel":
        test_path.write_text(
            """import time


def test_controlled_timeout():
    time.sleep(2)
""",
            encoding="utf-8",
        )
        return ["-q", test_path.name], 1
    elif scenario_id == "candidate-changed-during-run":
        test_path.write_text(
            """from pathlib import Path


def test_changes_candidate():
    Path("changed-during-run.txt").write_text("changed", encoding="utf-8")
""",
            encoding="utf-8",
        )
    else:  # pragma: no cover - guarded by the exact contract loader
        raise ReplayBatchError(f"未知回放场景: {scenario_id}")
    return ["-q", test_path.name], 10


def _mutate_after_prior_run(project_dir: Path, scenario_id: str) -> None:
    if scenario_id == "old-pass-current-fail":
        (project_dir / "test_replay.py").write_text(
            "def test_current_failure():\n    assert False\n",
            encoding="utf-8",
        )
    elif scenario_id == "old-pass-current-candidate":
        (project_dir / "candidate-revision.txt").write_text(
            "candidate changed while tests remain green\n",
            encoding="utf-8",
        )
    else:  # pragma: no cover - exact contract allows only the two old-evidence cases
        raise ReplayBatchError(f"场景 {scenario_id} 没有受控代码版本变更方案")


@contextmanager
def _isolated_process_environment(
    user_directories: UserDirectoryContext,
    temporary_directory: Path,
) -> Iterator[None]:
    base = {key: value for key, value in os.environ.items() if key.upper() in _SCENARIO_ENV_KEYS}
    isolated = user_directories.environment(base)
    isolated.update(
        {
            "TEMP": str(temporary_directory),
            "TMP": str(temporary_directory),
            "GIT_CEILING_DIRECTORIES": str(temporary_directory.parent),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    with mock.patch.dict(os.environ, isolated, clear=True):
        yield


@contextmanager
def _network_disabled_in_parent() -> Iterator[None]:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("verification replay network access is disabled")

    with (
        mock.patch.object(socket, "create_connection", blocked),
        mock.patch.object(socket, "socket", side_effect=RuntimeError("network disabled")),
    ):
        yield


def _persist_verification_evidence(
    evidence_dir: Path,
    *,
    service_outcome: object,
    prefix: str = "",
) -> None:
    outcome = service_outcome
    result_path = getattr(outcome, "result_path", None)
    if not isinstance(result_path, Path) or not result_path.is_file():
        raise ReplayBatchError("新流程没有形成 verification result 证据")
    result_payload = _read_json_object(result_path)
    summary_path = result_path.parent / "pytest-summary.json"
    summary_payload = _read_json_object(summary_path)
    _atomic_write_json(evidence_dir / f"{prefix}verification-result.json", result_payload)
    _atomic_write_json(evidence_dir / f"{prefix}pytest-summary.json", summary_payload)


def _persist_release_report(
    evidence_dir: Path,
    *,
    name: str,
    scenario: ReplayScenario,
    status: str,
    duration_ms: float,
    report: ReleaseReadinessReport,
) -> None:
    _atomic_write_json(
        evidence_dir / name,
        {
            "schema_version": 1,
            "scenario_id": scenario.scenario_id,
            "measurement_scope": REPLAY_MEASUREMENT_SCOPE,
            "status": status,
            "duration_ms": duration_ms,
            "report": report.to_dict(),
        },
    )


def _comparison_file_snapshot(project_dir: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(project_dir)
        if relative.parts[:2] == (".super-dev", "extensions"):
            continue
        if any(
            part in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
            for part in relative.parts
        ):
            continue
        snapshot[relative.as_posix()] = path.read_bytes()
    return snapshot


def _restore_comparison_file_snapshot(
    project_dir: Path,
    snapshot: dict[str, bytes],
) -> None:
    current = _comparison_file_snapshot(project_dir)
    for relative in sorted(set(current) - set(snapshot)):
        target = (project_dir / relative).resolve(strict=False)
        if not path_is_within(target, project_dir):  # pragma: no cover - defensive
            raise ReplayBatchError("旧流程产生了越界文件，无法恢复比较边界")
        target.unlink(missing_ok=True)
    for relative, content in snapshot.items():
        target = (project_dir / relative).resolve(strict=False)
        if not path_is_within(target, project_dir):  # pragma: no cover - defensive
            raise ReplayBatchError("旧流程改变了越界文件，无法恢复比较边界")
        if current.get(relative) == content:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def _validate_verification_release_report(
    scenario: ReplayScenario,
    *,
    outcome: ProbeOutcome,
    report: ReleaseReadinessReport,
) -> None:
    completion_check_name = "完成前验证（Fresh Verification）"
    failed_names = [item.name for item in report.failed_checks]
    if outcome.status == ExtensionStatus.PASS:
        if not report.passed or failed_names:
            details_str = "; ".join(f"{item.name}: {item.detail}" for item in report.failed_checks)
            raise ReplayBatchError(
                f"场景 {scenario.scenario_id} 的新流程发布报告含无关失败: {details_str}"
            )
        return
    if report.passed:
        raise ReplayBatchError(f"场景 {scenario.scenario_id} 的新流程发布报告错误通过")
    unrelated = [name for name in failed_names if name != completion_check_name]
    if failed_names.count(completion_check_name) != 1 or unrelated:
        raise ReplayBatchError(
            f"场景 {scenario.scenario_id} 的新流程发布报告含无关失败: {failed_names}"
        )


def _compare_final_candidate(
    scenario: ReplayScenario,
    *,
    project_dir: Path,
    evidence_dir: Path,
    service: ExtensionService,
    prior_outcome: ProbeOutcome | None,
    evaluator_factory: Callable[[Path], ReleaseReadinessEvaluator],
    clock: Callable[[], float],
) -> ScenarioExecution:
    comparison_files = _comparison_file_snapshot(project_dir)
    comparison_candidate = build_candidate_identity(project_dir)
    comparison_candidate_digest = comparison_candidate.candidate_digest
    measurement_boundaries: dict[str, object] = {
        "legacy": {
            "start": "before ReleaseReadinessEvaluator(project).evaluate(verify_tests=False)",
            "end": "after legacy ReleaseReadinessReport is returned",
        },
        "verification": {
            "start": "before ExtensionService.run_fresh_verification()",
            "steps": [
                "run_fresh_verification",
                "refresh quality gate when verification passes",
                "repeat fresh verification for the release decision",
                "completion_verification_check",
                "ReleaseReadinessEvaluator.evaluate with completion preflight",
            ],
            "end": "after verification ReleaseReadinessReport is returned",
        },
    }

    legacy_started = clock()
    legacy_evaluator = evaluator_factory(project_dir)
    legacy_evaluator.fresh_verification_required = False
    legacy_report = legacy_evaluator.evaluate(verify_tests=False)
    legacy_duration_ms = (clock() - legacy_started) * 1000
    legacy_status = "PASS" if legacy_report.passed else "FAIL"
    _persist_release_report(
        evidence_dir,
        name="legacy-report.json",
        scenario=scenario,
        status=legacy_status,
        duration_ms=legacy_duration_ms,
        report=legacy_report,
    )
    if not legacy_report.passed:
        failed_names = [item.name for item in legacy_report.failed_checks]
        raise ReplayBatchError("旧流程因无关发布项未通过: " + ", ".join(failed_names[:5]))
    _restore_comparison_file_snapshot(project_dir, comparison_files)
    candidate_after_legacy = build_candidate_identity(project_dir)
    if candidate_after_legacy.candidate_digest != comparison_candidate_digest:
        changed_fields = [
            field_name
            for field_name, value in comparison_candidate.to_dict().items()
            if candidate_after_legacy.to_dict().get(field_name) != value
        ]
        raise ReplayBatchError(
            "旧流程发布就绪评估改变了最终代码版本字段: " + ", ".join(changed_fields)
        )

    verification_started = clock()
    outcome = service.run_fresh_verification(actor="replay-pilot")
    quality_gate_bound_run_id: str | None = None
    if outcome.status == ExtensionStatus.PASS:
        quality_gate_bound_run_id = outcome.run_id
        quality_deps = quality_evidence_dependency_paths(
            project_dir,
            project_name=project_dir.name,
            frontend_required=True,
        )
        quality_gate_identity = build_evidence_identity(
            project_dir,
            artifact_name="quality-gate",
            dependencies=quality_deps,
        )
        (project_dir / "output" / f"{project_dir.name}-quality-gate.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "total_score": 90,
                    "summary": {"executive_summary": "quality gate passed"},
                    "evidence_identity": quality_gate_identity,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        release_outcome = service.run_fresh_verification(actor="replay-pilot-release")
        if release_outcome.status != ExtensionStatus.PASS:
            raise ReplayBatchError(f"场景 {scenario.scenario_id} 的重复发布检查未保持通过状态")
        if release_outcome.run_id == quality_gate_bound_run_id:
            raise ReplayBatchError(
                f"场景 {scenario.scenario_id} 的重复发布检查复用了质量门禁运行编号"
            )
        if (
            release_outcome.result is None
            or outcome.result is None
            or release_outcome.result.candidate.candidate_digest
            != outcome.result.candidate.candidate_digest
        ):
            raise ReplayBatchError(f"场景 {scenario.scenario_id} 的重复发布检查未保持同一代码版本")
        outcome = release_outcome
    verification_check = CliReleaseQualityMixin._completion_verification_check(outcome)
    verification_report = evaluator_factory(project_dir).evaluate(
        verify_tests=False,
        preflight_checks=(verification_check,),
    )
    verification_duration_ms = (clock() - verification_started) * 1000
    _persist_release_report(
        evidence_dir,
        name="verification-release-report.json",
        scenario=scenario,
        status="PASS" if verification_report.passed else "FAIL",
        duration_ms=verification_duration_ms,
        report=verification_report,
    )
    _validate_verification_release_report(
        scenario,
        outcome=outcome,
        report=verification_report,
    )

    verification_status = outcome.status.value
    if verification_status not in _STATUS_VALUES:
        raise ReplayBatchError(f"场景 {scenario.scenario_id} 的新流程没有返回可比较状态")
    if outcome.result is None or not outcome.run_id:
        raise ReplayBatchError(f"场景 {scenario.scenario_id} 缺少新流程结果")
    if outcome.result.candidate.candidate_digest != comparison_candidate_digest:
        raise ReplayBatchError(f"场景 {scenario.scenario_id} 未从最终代码版本边界开始新流程")
    if scenario.expected_new_run:
        if prior_outcome is None or prior_outcome.result is None:
            raise ReplayBatchError(f"场景 {scenario.scenario_id} 缺少合同要求的前置运行")
        if outcome.run_id == prior_outcome.run_id:
            raise ReplayBatchError(f"场景 {scenario.scenario_id} 复用了旧运行编号")
        if (
            outcome.result.candidate.candidate_digest
            == prior_outcome.result.candidate.candidate_digest
        ):
            raise ReplayBatchError(f"场景 {scenario.scenario_id} 未形成新代码版本摘要")
    elif prior_outcome is not None:
        raise ReplayBatchError(f"场景 {scenario.scenario_id} 产生了合同外前置运行")

    advisory_codes = [item.code for item in outcome.advisories]
    if scenario.expected_advisory and scenario.expected_advisory not in advisory_codes:
        raise ReplayBatchError(f"场景 {scenario.scenario_id} 缺少预期结构化提醒")
    _persist_verification_evidence(evidence_dir, service_outcome=outcome)

    command = outcome.result.commands[0] if outcome.result.commands else None
    details: dict[str, object] = {
        "measurement_scope": REPLAY_MEASUREMENT_SCOPE,
        "measurement_boundaries": measurement_boundaries,
        "comparison_candidate_digest": comparison_candidate_digest,
        "legacy_side_effects_restored_before_verification": True,
        "verification_run_id": outcome.run_id,
        "quality_gate_bound_run_id": quality_gate_bound_run_id,
        "release_verification_repeated": quality_gate_bound_run_id is not None,
        "prior_verification_run_id": (prior_outcome.run_id if prior_outcome is not None else None),
        "new_run_id_observed": (prior_outcome is None or prior_outcome.run_id != outcome.run_id),
        "advisory_codes": advisory_codes,
        "process_tree_clean": outcome.result.process_tree_clean,
        "timed_out": command.timed_out if command is not None else False,
        "cancelled": command.cancelled if command is not None else False,
        "candidate_changed_during_run": any(
            "当前代码版本发生变化" in finding for finding in outcome.result.blocking_findings
        ),
    }
    return ScenarioExecution(
        scenario_id=scenario.scenario_id,
        legacy_status=legacy_status,
        verification_status=verification_status,
        legacy_duration_ms=legacy_duration_ms,
        verification_duration_ms=verification_duration_ms,
        safety_regression=not outcome.result.process_tree_clean,
        details=details,
    )


def _run_scenario(
    scenario: ReplayScenario,
    evidence_dir: Path,
    *,
    evaluator_factory: Callable[[Path], ReleaseReadinessEvaluator] = ReleaseReadinessEvaluator,
    clock: Callable[[], float] | None = None,
) -> ScenarioExecution:
    real_directories = UserDirectoryContext.current()
    with _safe_scenario_temporary_root(prefix=f"super-dev-replay-{scenario.scenario_id}-") as (
        temporary_root,
        temporary_parent,
    ):
        project_dir = temporary_root / "project"
        isolated_home = temporary_root / "home"
        isolated_temp = temporary_root / "temp"
        for directory in (project_dir, isolated_home, isolated_temp, evidence_dir):
            directory.mkdir(parents=True, exist_ok=True)
        if not path_is_within(temporary_root, temporary_parent):
            raise ReplayBatchError("隔离回放项目未创建在选定的仓库外临时目录")
        if path_is_within(project_dir, PROJECT_ROOT):
            raise ReplayBatchError("隔离回放项目不得位于真实仓库")
        assert_safe_isolated_home(
            isolated_home,
            real_home=real_directories.home,
            project_dir=PROJECT_ROOT,
            run_root=temporary_root,
        )
        isolated_directories = UserDirectoryContext.from_home(isolated_home)

        with (
            _isolated_process_environment(isolated_directories, isolated_temp),
            _network_disabled_in_parent(),
        ):
            (project_dir / "conftest.py").write_text(_NETWORK_GUARD, encoding="utf-8")
            args, timeout_seconds = _write_scenario_input(
                project_dir,
                scenario.scenario_id,
            )
            _write_config(project_dir, args=args, timeout_seconds=timeout_seconds)
            service = ExtensionService(
                project_dir,
                user_directories=isolated_directories,
            )
            prior_outcome = None
            if scenario.expected_new_run:
                prior_outcome = service.run_fresh_verification(actor="replay-pilot-prior")
                if prior_outcome.status != ExtensionStatus.PASS or not prior_outcome.run_id:
                    raise ReplayBatchError(f"场景 {scenario.scenario_id} 未取得前置 PASS 证据")
                _persist_verification_evidence(
                    evidence_dir,
                    service_outcome=prior_outcome,
                    prefix="prior-",
                )
                _mutate_after_prior_run(project_dir, scenario.scenario_id)

            # Bind the fixture before preparing its scoped documents and confirmations.
            _prepare_spec_quality_change(project_dir, change_id=project_dir.name)
            save_workflow_state(project_dir, {"active_change_id": project_dir.name})
            _prepare_release_ready_project(project_dir)
            return _compare_final_candidate(
                scenario,
                project_dir=project_dir,
                evidence_dir=evidence_dir,
                service=service,
                prior_outcome=prior_outcome,
                evaluator_factory=evaluator_factory,
                clock=clock or time.monotonic,
            )


def _safe_scenario_temp_parents() -> tuple[Path, ...]:
    candidates: list[Path] = []
    for raw_candidate in (Path(tempfile.gettempdir()), PROJECT_ROOT.parent):
        try:
            candidate = raw_candidate.resolve(strict=False)
        except OSError:
            continue
        if candidate in candidates or path_is_within(candidate, PROJECT_ROOT):
            continue
        if candidate.is_dir():
            candidates.append(candidate)
    if not candidates:
        raise ReplayBatchError("没有可用的仓库外隔离回放临时父目录")
    return tuple(candidates)


@contextmanager
def _safe_scenario_temporary_root(*, prefix: str) -> Iterator[tuple[Path, Path]]:
    last_error: OSError | None = None
    for parent in _safe_scenario_temp_parents():
        try:
            temporary_directory = tempfile.TemporaryDirectory(prefix=prefix, dir=str(parent))
        except OSError as exc:
            last_error = exc
            continue
        try:
            temporary_root = Path(temporary_directory.name).resolve()
            if not path_is_within(temporary_root, parent) or path_is_within(
                temporary_root, PROJECT_ROOT
            ):
                continue
            yield temporary_root, parent
            return
        finally:
            temporary_directory.cleanup()
    raise ReplayBatchError("无法创建仓库外隔离回放临时根") from last_error


def _metric_record(
    scenario: ReplayScenario,
    execution: ScenarioExecution,
    *,
    replay_run_id: str,
    candidate_digest: str,
) -> dict[str, object]:
    legacy_correct = execution.legacy_status == scenario.expected_status
    verification_correct = execution.verification_status == scenario.expected_status
    return {
        "schema_version": 1,
        "record_type": "verification-replay",
        "recorded_at": _utc_now(),
        "measurement_scope": REPLAY_MEASUREMENT_SCOPE,
        "replay_run_id": replay_run_id,
        "candidate_digest": candidate_digest,
        "scenario_id": scenario.scenario_id,
        "legacy_status": execution.legacy_status,
        "verification_status": execution.verification_status,
        "legacy_false_completion": (
            execution.legacy_status == "PASS" and scenario.expected_status != "PASS"
        ),
        "verification_false_completion": (
            execution.verification_status == "PASS" and scenario.expected_status != "PASS"
        ),
        "legacy_false_block": (
            scenario.expected_status == "PASS" and execution.legacy_status != "PASS"
        ),
        "verification_false_block": (
            scenario.expected_status == "PASS" and execution.verification_status != "PASS"
        ),
        "legacy_time_to_accepted_ms": (execution.legacy_duration_ms if legacy_correct else None),
        "verification_time_to_accepted_ms": (
            execution.verification_duration_ms if verification_correct else None
        ),
        "safety_regression": execution.safety_regression,
    }


def _persist_scenario_result(
    evidence_dir: Path,
    *,
    scenario: ReplayScenario,
    execution: ScenarioExecution,
    metric_record: dict[str, object],
) -> None:
    _atomic_write_json(
        evidence_dir / "scenario-result.json",
        {
            "schema_version": 1,
            "scenario_id": scenario.scenario_id,
            "expected_status": scenario.expected_status,
            "measurement_scope": REPLAY_MEASUREMENT_SCOPE,
            "measurement_boundaries": execution.details.get("measurement_boundaries"),
            "legacy_correct": execution.legacy_status == scenario.expected_status,
            "verification_correct": (execution.verification_status == scenario.expected_status),
            "timing_comparable": (
                metric_record["legacy_time_to_accepted_ms"] is not None
                and metric_record["verification_time_to_accepted_ms"] is not None
            ),
            "details": execution.details,
            "metric_record": metric_record,
        },
    )


def _assert_scenario_evidence(evidence_dir: Path) -> None:
    missing = sorted(
        name for name in REQUIRED_SCENARIO_EVIDENCE_FILES if not (evidence_dir / name).is_file()
    )
    if missing:
        raise ReplayBatchError("回放场景证据不完整: " + ", ".join(missing))


def _assert_batch_evidence(evidence_root: Path) -> None:
    missing = [
        name for name in REQUIRED_BATCH_EVIDENCE_FILES if not (evidence_root / name).is_file()
    ]
    for scenario_id in EXPECTED_SCENARIO_IDS:
        evidence_dir = evidence_root / scenario_id
        missing.extend(
            f"{scenario_id}/{name}"
            for name in REQUIRED_SCENARIO_EVIDENCE_FILES
            if not (evidence_dir / name).is_file()
        )
    if missing:
        raise ReplayBatchError("回放批次证据不完整: " + ", ".join(sorted(missing)))


def _format_report_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return json.dumps(value, allow_nan=False)
    raise ReplayBatchError("回放完成报告含无效指标值")


def _render_completion_report(
    *,
    replay_run_id: str,
    candidate_digest: str,
    records: tuple[dict[str, object], ...],
    executions: tuple[ScenarioExecution, ...],
    summary: VerificationMetricsSummary,
) -> str:
    if len(records) != len(EXPECTED_SCENARIO_IDS) or len(executions) != len(records):
        raise ReplayBatchError("回放完成报告缺少完整 10 场景数据")
    if (
        summary.replay_run_id != replay_run_id
        or summary.replay_candidate_digest != candidate_digest
        or summary.replay_scenarios != len(records)
    ):
        raise ReplayBatchError("回放完成报告与指标汇总绑定不一致")

    executions_by_id = {item.scenario_id: item for item in executions}
    if len(executions_by_id) != len(executions):
        raise ReplayBatchError("回放完成报告含重复场景")

    table_rows: list[str] = []
    for record in records:
        scenario_id = record.get("scenario_id")
        if not isinstance(scenario_id, str) or scenario_id not in executions_by_id:
            raise ReplayBatchError("回放完成报告含未知场景")
        execution = executions_by_id[scenario_id]
        if (
            record.get("legacy_status") != execution.legacy_status
            or record.get("verification_status") != execution.verification_status
        ):
            raise ReplayBatchError("回放完成报告的场景状态不一致")
        legacy_time = record.get("legacy_time_to_accepted_ms")
        verification_time = record.get("verification_time_to_accepted_ms")
        timing_comparable = legacy_time is not None and verification_time is not None
        table_rows.append(
            "| "
            f"{scenario_id} | {execution.legacy_status} | {execution.verification_status} | "
            f"{'是' if timing_comparable else '否'} | "
            f"{_format_report_value(legacy_time)} | "
            f"{_format_report_value(verification_time)} |"
        )

    legacy_false_completions = sum(
        record.get("legacy_false_completion") is True for record in records
    )
    verification_false_completions = sum(
        record.get("verification_false_completion") is True for record in records
    )
    legacy_false_blocks = sum(record.get("legacy_false_block") is True for record in records)
    verification_false_blocks = sum(
        record.get("verification_false_block") is True for record in records
    )
    scenario_files = "、".join(f"`{name}`" for name in REQUIRED_SCENARIO_EVIDENCE_FILES)
    report = [
        "# 完成前验证回放完成报告",
        "",
        "## 批次绑定",
        "",
        f"- 回放批次（`replay_run_id`）：`{replay_run_id}`",
        f"- 测量范围（`measurement_scope`）：`{REPLAY_MEASUREMENT_SCOPE}`",
        f"- 代码版本摘要（`candidate_digest`）：`{candidate_digest}`",
        f"- 本批次共有 {len(records)} 个场景，均绑定同一批次与代码版本摘要。",
        "",
        "## 10 场景旧流程、新流程与成对时间",
        "",
        "| 场景 | 旧流程状态 | 新流程状态 | 成对时间 | 旧流程正确验收时间 ms | 新流程正确验收时间 ms |",
        "|---|---:|---:|---:|---:|---:|",
        *table_rows,
        "",
        "## 本批次指标",
        "",
        (
            f"- 旧流程判对 {summary.legacy_correct_replays}/{len(records)}，"
            f"虚假完成 {legacy_false_completions}，误阻断 {legacy_false_blocks}。"
        ),
        (
            f"- 新流程判对 {summary.verification_correct_replays}/{len(records)}，"
            f"虚假完成 {verification_false_completions}，"
            f"误阻断 {verification_false_blocks}。"
        ),
        (
            "- 正确验收时间中位数：旧流程 "
            f"{_format_report_value(summary.legacy_time_to_accepted_median_ms)} ms，"
            "新流程 "
            f"{_format_report_value(summary.verification_time_to_accepted_median_ms)} ms。"
        ),
        f"- 安全回归：{summary.safety_regressions}。",
        (
            "- 回放代码版本与当前工作区匹配（`replay_candidate_matches_current`）："
            f"`{_format_report_value(summary.replay_candidate_matches_current)}`。"
        ),
        (
            "- 试点收益条件满足（`benefit_criteria_met`）："
            f"`{_format_report_value(summary.benefit_criteria_met)}`。"
        ),
        "- 程序化排错需求已撤回；收益观察不派生新功能，也不代替发布门禁。",
        "",
        "## 证据文件合同",
        "",
        "- 批次根目录必须包含 `batch-result.json` 与 `completion-report.md`。",
        f"- 每个场景目录必须包含：{scenario_files}。",
        "- 只有指标账本追加、完成报告原子写入、批次证据校验和正式汇总替换全部成功，本批次才算成功。",
        "- 报告只记录仓库内相对证据合同，不记录凭据或用户目录详情。",
        "",
    ]
    return "\n".join(report)


def _write_completion_report(
    path: Path,
    *,
    replay_run_id: str,
    candidate_digest: str,
    records: tuple[dict[str, object], ...],
    executions: tuple[ScenarioExecution, ...],
    summary: VerificationMetricsSummary,
) -> None:
    content = _render_completion_report(
        replay_run_id=replay_run_id,
        candidate_digest=candidate_digest,
        records=records,
        executions=executions,
        summary=summary,
    )
    try:
        _atomic_write_text(path, content)
    except OSError as exc:
        raise ReplayBatchError("回放完成报告无法写入") from exc


def _append_records(path: Path, records: tuple[dict[str, object], ...]) -> tuple[int, bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        original_size = stream.tell()
        try:
            for record in records:
                line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                stream.write(line.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        except Exception:
            stream.flush()
            os.ftruncate(stream.fileno(), original_size)
            os.fsync(stream.fileno())
            raise
    return original_size, existed


def _rollback_append(path: Path, *, original_size: int, existed: bool) -> None:
    if not path.exists():
        return
    with path.open("r+b") as stream:
        stream.truncate(original_size)
        stream.flush()
        os.fsync(stream.fileno())
    if not existed and original_size == 0:
        path.unlink(missing_ok=True)


def run_replay_batch(
    project_root: Path = PROJECT_ROOT,
    contract_path: Path | None = None,
    *,
    scenario_runner: ScenarioRunner | None = None,
    replay_run_id: str | None = None,
) -> ReplayBatchResult:
    project = Path(project_root).resolve()
    resolved_contract = Path(contract_path or REPLAY_CONTRACT_PATH).resolve()
    scenarios = _load_contract(resolved_contract)
    batch_id = replay_run_id or uuid.uuid4().hex
    if not batch_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in batch_id
    ):
        raise ReplayBatchError("回放批次编号格式无效")

    store = EvidenceStore(project)
    evidence_root = store.metrics_dir / "replays" / batch_id
    resolved_evidence_root = evidence_root.resolve(strict=False)
    replay_parent = (store.metrics_dir / "replays").resolve(strict=False)
    if not path_is_within(resolved_evidence_root, replay_parent):
        raise ReplayBatchError("回放证据目录越出指标目录")
    evidence_root.mkdir(parents=True, exist_ok=False)

    real_directories = UserDirectoryContext.current()
    protected_paths = collect_user_surface_paths(project, real_directories)
    before_surfaces = capture_user_surfaces(protected_paths)
    initial_surface_risks = unsafe_surface_states(before_surfaces)
    candidate_before = build_candidate_identity(project).candidate_digest
    runner = scenario_runner or _run_scenario
    records: list[dict[str, object]] = []
    executions: list[ScenarioExecution] = []
    caught_error: Exception | None = None
    after_surfaces = before_surfaces
    try:
        for scenario in scenarios:
            evidence_dir = evidence_root / scenario.scenario_id
            execution = runner(scenario, evidence_dir)
            if execution.scenario_id != scenario.scenario_id:
                raise ReplayBatchError("回放执行结果与场景编号不一致")
            if execution.legacy_status not in _STATUS_VALUES:
                raise ReplayBatchError(f"场景 {scenario.scenario_id} 的旧流程状态无效")
            if execution.verification_status not in _STATUS_VALUES:
                raise ReplayBatchError(f"场景 {scenario.scenario_id} 的新流程状态无效")
            metric_record = _metric_record(
                scenario,
                execution,
                replay_run_id=batch_id,
                candidate_digest=candidate_before,
            )
            _persist_scenario_result(
                evidence_dir,
                scenario=scenario,
                execution=execution,
                metric_record=metric_record,
            )
            _assert_scenario_evidence(evidence_dir)
            records.append(metric_record)
            executions.append(execution)
    except Exception as exc:
        caught_error = exc
    finally:
        after_surfaces = capture_user_surfaces(protected_paths)

    surface_diff = diff_surface_snapshots(before_surfaces, after_surfaces)
    if caught_error is not None:
        _atomic_write_json(
            evidence_root / "batch-failure.json",
            {
                "schema_version": 1,
                "replay_run_id": batch_id,
                "completed_scenarios": len(records),
                "error_type": type(caught_error).__name__,
                "user_surface_changed": has_surface_changes(surface_diff),
            },
        )
        if isinstance(caught_error, ReplayBatchError):
            raise caught_error
        raise ReplayBatchError("回放场景执行失败，未写入指标账本") from caught_error
    if has_surface_changes(surface_diff):
        _atomic_write_json(
            evidence_root / "batch-failure.json",
            {
                "schema_version": 1,
                "replay_run_id": batch_id,
                "completed_scenarios": len(records),
                "error_type": "UserSurfaceChanged",
                "user_surface_changed": True,
                "changed_surface_counts": {key: len(value) for key, value in surface_diff.items()},
            },
        )
        raise ReplayBatchError("真实用户级宿主接入面发生变化，未写入指标账本")

    candidate_after = build_candidate_identity(project).candidate_digest
    if candidate_after != candidate_before:
        _atomic_write_json(
            evidence_root / "batch-failure.json",
            {
                "schema_version": 1,
                "replay_run_id": batch_id,
                "completed_scenarios": len(records),
                "error_type": "CandidateChanged",
                "candidate_matches": False,
            },
        )
        raise ReplayBatchError("主仓库代码版本在回放期间发生变化，未写入指标账本")
    if len(records) != len(EXPECTED_SCENARIO_IDS):
        raise ReplayBatchError("回放批次没有形成完整 10 条记录")

    records_tuple = tuple(records)
    executions_tuple = tuple(executions)
    _atomic_write_json(
        evidence_root / "batch-result.json",
        {
            "schema_version": 1,
            "replay_run_id": batch_id,
            "measurement_scope": REPLAY_MEASUREMENT_SCOPE,
            "candidate_digest": candidate_before,
            "candidate_matches": True,
            "scenario_count": len(records_tuple),
            "scenario_ids": [item.scenario_id for item in executions_tuple],
            "user_surface_changed": False,
            "initial_surface_risk_count": len(initial_surface_risks),
        },
    )

    original_size, ledger_existed = _append_records(
        store.verification_metrics_path,
        records_tuple,
    )
    completion_report_path = evidence_root / "completion-report.md"
    try:
        summary = summarize_verification_metrics(
            store.verification_metrics_path,
            resolved_contract,
            current_candidate_digest=candidate_after,
        )
        _write_completion_report(
            completion_report_path,
            replay_run_id=batch_id,
            candidate_digest=candidate_before,
            records=records_tuple,
            executions=executions_tuple,
            summary=summary,
        )
        _assert_batch_evidence(evidence_root)
        store.write_verification_summary(summary.to_dict())
    except Exception:
        _rollback_append(
            store.verification_metrics_path,
            original_size=original_size,
            existed=ledger_existed,
        )
        completion_report_path.unlink(missing_ok=True)
        raise
    return ReplayBatchResult(
        replay_run_id=batch_id,
        candidate_digest=candidate_before,
        evidence_root=evidence_root,
        completion_report_path=completion_report_path,
        records=records_tuple,
        summary=summary,
    )


def main() -> int:
    if Path.cwd().resolve() != PROJECT_ROOT:
        print("错误：内部回放执行器只能显式从项目根目录运行。")
        return 2
    try:
        result = run_replay_batch()
    except ReplayBatchError as exc:
        print(f"回放失败：{exc}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive command boundary
        print(f"回放失败：内部错误 {type(exc).__name__}，未确认写入成功。")
        return 1

    statuses = ", ".join(
        f"{record['scenario_id']}={record['legacy_status']}/{record['verification_status']}"
        for record in result.records
    )
    summary = result.summary
    print(f"完成 10 个隔离回放（旧流程/新流程）：{statuses}")
    print(
        "成对时间场景 "
        f"{summary.timing_comparable_replays} 个；旧流程中位数 "
        f"{summary.legacy_time_to_accepted_median_ms} ms，新流程中位数 "
        f"{summary.verification_time_to_accepted_median_ms} ms。"
    )
    print(
        "代码版本一致："
        f"{'是' if summary.replay_candidate_matches_current else '否'}；"
        f"试点收益条件满足：{'是' if summary.benefit_criteria_met else '否'}。"
    )
    print("程序化排错需求已撤回；继续观察现有验证，不产生下一阶段开发建议。")
    print(f"证据根：{result.evidence_root.resolve()}")
    print(f"完成报告：{result.completion_report_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
