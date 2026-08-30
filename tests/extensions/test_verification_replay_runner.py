from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.release_readiness import ReleaseReadinessCheck, ReleaseReadinessReport
from tests.support import run_verification_replays as replay_runner


def _copy_contract(project_dir: Path) -> Path:
    contract_path = (
        project_dir / ".super-dev" / "changes" / "completion-verification" / "replay-scenarios.yaml"
    )
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(
        replay_runner.REPLAY_CONTRACT_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return contract_path


def _stub_scenario_runner(
    *,
    fail_on_call: int | None = None,
) -> replay_runner.ScenarioRunner:
    calls = 0

    def run(
        scenario: replay_runner.ReplayScenario,
        evidence_dir: Path,
    ) -> replay_runner.ScenarioExecution:
        nonlocal calls
        calls += 1
        if fail_on_call == calls:
            raise replay_runner.ReplayBatchError("controlled replay failure")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        for name in (
            "legacy-report.json",
            "verification-result.json",
            "verification-release-report.json",
            "pytest-summary.json",
        ):
            (evidence_dir / name).write_text("{}\n", encoding="utf-8")
        return replay_runner.ScenarioExecution(
            scenario_id=scenario.scenario_id,
            legacy_status="PASS",
            verification_status=scenario.expected_status,
            legacy_duration_ms=float(calls),
            verification_duration_ms=float(calls + 10),
            safety_regression=False,
            details={
                "stub": True,
                "measurement_boundaries": {
                    "legacy": {"start": "request", "end": "report"},
                    "verification": {"start": "request", "end": "report"},
                },
            },
        )

    return run


def _disable_real_surface_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(replay_runner, "collect_user_surface_paths", lambda *_args: [])


def _controlled_report(
    preflight_checks: tuple[ReleaseReadinessCheck, ...] = (),
) -> ReleaseReadinessReport:
    return ReleaseReadinessReport(
        project_name="controlled-replay",
        checks=[
            *preflight_checks,
            ReleaseReadinessCheck(
                name="Controlled unrelated check",
                passed=True,
                detail="controlled pass",
                severity="low",
            ),
        ],
    )


def test_batch_failure_never_partially_appends_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    contract_path = _copy_contract(project_dir)
    ledger_path = project_dir / ".super-dev" / "extensions" / "metrics" / "verification-pilot.jsonl"
    ledger_path.parent.mkdir(parents=True)
    original = '{"record_type":"sentinel"}\n'
    ledger_path.write_text(original, encoding="utf-8")
    _disable_real_surface_scan(monkeypatch)

    with pytest.raises(replay_runner.ReplayBatchError, match="controlled replay failure"):
        replay_runner.run_replay_batch(
            project_dir,
            contract_path,
            scenario_runner=_stub_scenario_runner(fail_on_call=4),
            replay_run_id="controlled-failure-batch",
        )

    assert ledger_path.read_text(encoding="utf-8") == original


def test_missing_verification_release_report_never_appends_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    contract_path = _copy_contract(project_dir)
    _disable_real_surface_scan(monkeypatch)
    complete_runner = _stub_scenario_runner()

    def missing_report_runner(
        scenario: replay_runner.ReplayScenario,
        evidence_dir: Path,
    ) -> replay_runner.ScenarioExecution:
        execution = complete_runner(scenario, evidence_dir)
        (evidence_dir / "verification-release-report.json").unlink()
        return execution

    with pytest.raises(replay_runner.ReplayBatchError, match="证据不完整"):
        replay_runner.run_replay_batch(
            project_dir,
            contract_path,
            scenario_runner=missing_report_runner,
            replay_run_id="controlled-missing-report-batch",
        )

    ledger_path = project_dir / ".super-dev" / "extensions" / "metrics" / "verification-pilot.jsonl"
    assert not ledger_path.exists()


def test_batch_appends_ten_records_with_one_batch_and_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    contract_path = _copy_contract(project_dir)
    _disable_real_surface_scan(monkeypatch)

    result = replay_runner.run_replay_batch(
        project_dir,
        contract_path,
        scenario_runner=_stub_scenario_runner(),
        replay_run_id="controlled-complete-batch",
    )

    ledger_path = project_dir / ".super-dev" / "extensions" / "metrics" / "verification-pilot.jsonl"
    records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 10
    assert {item["replay_run_id"] for item in records} == {"controlled-complete-batch"}
    assert {item["candidate_digest"] for item in records} == {result.candidate_digest}
    assert {item["measurement_scope"] for item in records} == {
        replay_runner.REPLAY_MEASUREMENT_SCOPE
    }
    assert result.summary.replay_scenarios == 10
    assert result.summary.legacy_correct_replays == 4
    assert result.summary.verification_correct_replays == 10
    assert result.summary.timing_comparable_replays == 4
    assert result.summary.replay_candidate_matches_current is True
    assert result.summary.recommend_stage_2b is False
    assert result.completion_report_path == result.evidence_root / "completion-report.md"
    assert result.completion_report_path.is_file()
    completion_report = result.completion_report_path.read_text(encoding="utf-8")
    assert "`controlled-complete-batch`" in completion_report
    assert "本批次共有 10 个场景" in completion_report
    assert "阶段 2B 推荐（`recommend_stage_2b`）：`false`" in completion_report
    for artifact_name in replay_runner.REQUIRED_BATCH_EVIDENCE_FILES:
        assert (result.evidence_root / artifact_name).is_file()
    for scenario_id in replay_runner.EXPECTED_SCENARIO_IDS:
        evidence_dir = result.evidence_root / scenario_id
        assert f"| {scenario_id} |" in completion_report
        for artifact_name in replay_runner.REQUIRED_SCENARIO_EVIDENCE_FILES:
            assert (evidence_dir / artifact_name).is_file()
        scenario_result = json.loads(
            (evidence_dir / "scenario-result.json").read_text(encoding="utf-8")
        )
        assert scenario_result["measurement_scope"] == replay_runner.REPLAY_MEASUREMENT_SCOPE
        assert set(scenario_result["measurement_boundaries"]) == {
            "legacy",
            "verification",
        }


def test_completion_report_write_failure_rolls_back_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    contract_path = _copy_contract(project_dir)
    _disable_real_surface_scan(monkeypatch)
    metrics_dir = project_dir / ".super-dev" / "extensions" / "metrics"
    metrics_dir.mkdir(parents=True)
    ledger_path = metrics_dir / "verification-pilot.jsonl"
    summary_path = metrics_dir / "verification-pilot-summary.json"
    original_ledger = '{"record_type":"sentinel"}\n'
    original_summary = '{"sentinel":true}\n'
    ledger_path.write_text(original_ledger, encoding="utf-8")
    summary_path.write_text(original_summary, encoding="utf-8")
    original_atomic_write_text = replay_runner._atomic_write_text

    def controlled_report_failure(path: Path, content: str) -> None:
        if path.name == "completion-report.md":
            raise OSError("controlled completion report failure")
        original_atomic_write_text(path, content)

    monkeypatch.setattr(replay_runner, "_atomic_write_text", controlled_report_failure)

    with pytest.raises(replay_runner.ReplayBatchError, match="完成报告无法写入"):
        replay_runner.run_replay_batch(
            project_dir,
            contract_path,
            scenario_runner=_stub_scenario_runner(),
            replay_run_id="controlled-report-failure-batch",
        )

    assert ledger_path.read_text(encoding="utf-8") == original_ledger
    assert summary_path.read_text(encoding="utf-8") == original_summary
    failed_report = (
        metrics_dir / "replays" / "controlled-report-failure-batch" / "completion-report.md"
    )
    assert not failed_report.exists()


def test_required_batch_artifacts_reject_missing_completion_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    contract_path = _copy_contract(project_dir)
    _disable_real_surface_scan(monkeypatch)
    result = replay_runner.run_replay_batch(
        project_dir,
        contract_path,
        scenario_runner=_stub_scenario_runner(),
        replay_run_id="controlled-artifact-validation-batch",
    )
    result.completion_report_path.unlink()

    with pytest.raises(replay_runner.ReplayBatchError, match="completion-report.md"):
        replay_runner._assert_batch_evidence(result.evidence_root)


def test_representative_scenarios_execute_real_new_and_legacy_flows(tmp_path: Path) -> None:
    scenarios = {
        item.scenario_id: item
        for item in replay_runner._load_contract(replay_runner.REPLAY_CONTRACT_PATH)
    }

    non_strict = replay_runner._run_scenario(
        scenarios["current-pass-non-strict-xpass"],
        tmp_path / "non-strict-evidence",
    )
    timeout = replay_runner._run_scenario(
        scenarios["timeout-or-cancel"],
        tmp_path / "timeout-evidence",
    )

    assert non_strict.legacy_status == "PASS"
    assert non_strict.verification_status == "PASS"
    assert non_strict.details["advisory_codes"] == ["NON_STRICT_XPASS"]
    assert timeout.legacy_status == "PASS"
    assert timeout.verification_status == "BLOCKED"
    assert timeout.details["timed_out"] is True
    assert timeout.details["process_tree_clean"] is True
    assert timeout.safety_regression is False
    non_strict_report = json.loads(
        (tmp_path / "non-strict-evidence" / "verification-release-report.json").read_text(
            encoding="utf-8"
        )
    )
    timeout_report = json.loads(
        (tmp_path / "timeout-evidence" / "verification-release-report.json").read_text(
            encoding="utf-8"
        )
    )
    assert non_strict_report["report"]["passed"] is True
    assert timeout_report["report"]["passed"] is False
    assert timeout_report["report"]["failed_checks"] == ["完成前验证（Fresh Verification）"]


def test_scenario_uses_external_temp_root_when_process_temp_is_inside_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = next(
        item
        for item in replay_runner._load_contract(replay_runner.REPLAY_CONTRACT_PATH)
        if item.scenario_id == "current-pass-clean"
    )
    nested_process_temp = (
        replay_runner.PROJECT_ROOT
        / ".super-dev"
        / "extensions"
        / "runs"
        / "controlled-outer-run"
        / "temp"
    )
    monkeypatch.setattr(
        replay_runner.tempfile,
        "gettempdir",
        lambda: str(nested_process_temp),
    )
    observed_projects: list[Path] = []

    class InspectingEvaluator:
        def __init__(self, project_dir: Path):
            self.project_dir = project_dir
            observed_projects.append(project_dir)

        def evaluate(
            self,
            verify_tests: bool = False,
            preflight_checks: tuple[ReleaseReadinessCheck, ...] = (),
        ) -> ReleaseReadinessReport:
            assert verify_tests is False
            return _controlled_report(preflight_checks)

    execution = replay_runner._run_scenario(
        scenario,
        tmp_path / "nested-temp-evidence",
        evaluator_factory=InspectingEvaluator,
    )

    assert execution.verification_status == "PASS"
    assert observed_projects
    for project_dir in observed_projects:
        temporary_root = project_dir.parent
        assert temporary_root.parent == replay_runner.PROJECT_ROOT.parent.resolve()
        assert not replay_runner.path_is_within(project_dir, replay_runner.PROJECT_ROOT)
        assert not temporary_root.exists()


def test_verification_time_includes_release_evaluator_and_persists_report(
    tmp_path: Path,
) -> None:
    scenario = next(
        item
        for item in replay_runner._load_contract(replay_runner.REPLAY_CONTRACT_PATH)
        if item.scenario_id == "current-pass-clean"
    )
    elapsed = [0.0]

    class DelayedEvaluator:
        def __init__(self, project_dir: Path):
            self.project_dir = project_dir

        def evaluate(
            self,
            verify_tests: bool = False,
            preflight_checks: tuple[ReleaseReadinessCheck, ...] = (),
        ) -> ReleaseReadinessReport:
            assert verify_tests is False
            elapsed[0] += 0.250 if preflight_checks else 0.010
            return _controlled_report(preflight_checks)

    evidence_dir = tmp_path / "timing-evidence"
    execution = replay_runner._run_scenario(
        scenario,
        evidence_dir,
        evaluator_factory=DelayedEvaluator,
        clock=lambda: elapsed[0],
    )

    assert execution.legacy_duration_ms == pytest.approx(10.0)
    assert execution.verification_duration_ms == pytest.approx(250.0)
    release_report_path = evidence_dir / "verification-release-report.json"
    assert release_report_path.is_file()
    release_report = json.loads(release_report_path.read_text(encoding="utf-8"))
    assert release_report["measurement_scope"] == replay_runner.REPLAY_MEASUREMENT_SCOPE
    assert release_report["duration_ms"] == pytest.approx(250.0)


@pytest.mark.parametrize(
    ("scenario_id", "assert_final_state"),
    [
        (
            "old-pass-current-fail",
            lambda project: "assert False"
            in (project / "test_replay.py").read_text(encoding="utf-8"),
        ),
        (
            "old-pass-current-candidate",
            lambda project: (project / "candidate-revision.txt").is_file(),
        ),
    ],
)
def test_old_evidence_legacy_evaluator_sees_mutated_final_candidate(
    tmp_path: Path,
    scenario_id: str,
    assert_final_state,
) -> None:
    scenario = next(
        item
        for item in replay_runner._load_contract(replay_runner.REPLAY_CONTRACT_PATH)
        if item.scenario_id == scenario_id
    )
    legacy_seen = []

    class InspectingEvaluator:
        def __init__(self, project_dir: Path):
            self.project_dir = project_dir

        def evaluate(
            self,
            verify_tests: bool = False,
            preflight_checks: tuple[ReleaseReadinessCheck, ...] = (),
        ) -> ReleaseReadinessReport:
            assert verify_tests is False
            if not preflight_checks:
                legacy_seen.append(bool(assert_final_state(self.project_dir)))
            return _controlled_report(preflight_checks)

    execution = replay_runner._run_scenario(
        scenario,
        tmp_path / f"{scenario_id}-evidence",
        evaluator_factory=InspectingEvaluator,
    )

    assert legacy_seen == [True]
    assert execution.details["prior_verification_run_id"]
    assert execution.details["new_run_id_observed"] is True
