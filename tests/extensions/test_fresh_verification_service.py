from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

import yaml

from super_dev.extensions import service as service_module
from super_dev.extensions.evidence import build_candidate_identity
from super_dev.extensions.models import ExtensionStatus
from super_dev.extensions.service import ExtensionService


def _configure(project_dir: Path, *, args: list[str], timeout: int = 30) -> None:
    (project_dir / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "fresh-verification-test",
                "frontend": "next",
                "backend": "python",
                "extensions": {
                    "enabled": True,
                    "allowed_builtin_methods": ["fresh-verification"],
                    "fresh_verification": {
                        "profile": "pytest-current-python",
                        "plan_id": "completion-pilot",
                        "args": args,
                        "timeout_seconds": timeout,
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_service_runs_fresh_pytest_and_never_reuses_run_id(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_sample.py"])
    (tmp_path / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    service = ExtensionService(tmp_path)

    first = service.run_fresh_verification()
    second = service.run_fresh_verification()

    assert first.status == ExtensionStatus.PASS
    assert second.status == ExtensionStatus.PASS
    assert first.run_id and second.run_id and first.run_id != second.run_id
    assert first.summary is not None and first.summary.executed == 1
    assert first.result_path is not None and first.result_path.exists()
    assert (first.result_path.parent / "pytest.xml").exists()
    assert (first.result_path.parent / "pytest-summary.json").exists()
    payload = json.loads(first.result_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == first.run_id
    assert "invocation_id" not in json.dumps(payload)


def test_service_never_reuses_old_pass_after_candidate_changes(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_sample.py"])
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    service = ExtensionService(tmp_path)
    first = service.run_fresh_verification()
    test_file.write_text("def test_ok():\n    assert False\n", encoding="utf-8")

    second = service.run_fresh_verification()

    assert first.status == ExtensionStatus.PASS
    assert second.status == ExtensionStatus.FAIL
    assert first.run_id != second.run_id


def test_service_aggregates_non_strict_xpass_advisory(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_xpass.py"])
    (tmp_path / "test_xpass.py").write_text(
        """import pytest

@pytest.mark.xfail(reason="known")
def test_one():
    assert True

@pytest.mark.xfail(reason="known")
def test_two():
    assert True
""",
        encoding="utf-8",
    )

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.PASS
    assert len(outcome.advisories) == 1
    assert outcome.advisories[0].occurrences == 2
    assert outcome.advisories[0].run_id == outcome.run_id
    assert "原本预计失败" in outcome.message


def test_service_allows_partial_skip_when_one_test_executes(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_partial.py"])
    (tmp_path / "test_partial.py").write_text(
        """import pytest

def test_ok():
    assert True

@pytest.mark.skip(reason="not available")
def test_skipped():
    pass
""",
        encoding="utf-8",
    )

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.PASS
    assert outcome.summary is not None
    assert outcome.summary.tests == 2
    assert outcome.summary.executed == 1
    assert outcome.summary.skipped == 1


def test_service_maps_real_test_failure_to_fail(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_failure.py"])
    (tmp_path / "test_failure.py").write_text(
        "def test_failure():\n    assert False\n",
        encoding="utf-8",
    )

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.FAIL
    assert outcome.summary is not None and outcome.summary.failures == 1


def test_service_maps_strict_xpass_to_fail(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_strict_xpass.py"])
    (tmp_path / "test_strict_xpass.py").write_text(
        """import pytest

@pytest.mark.xfail(reason="known", strict=True)
def test_strict_xpass():
    assert True
""",
        encoding="utf-8",
    )

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.FAIL
    assert outcome.result is not None
    assert outcome.result.commands[0].exit_code == 1


def test_service_blocks_when_no_tests_are_collected(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "empty_tests"])
    (tmp_path / "empty_tests").mkdir()

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.result is not None
    assert outcome.result.commands[0].exit_code == 5


def test_service_blocks_all_skipped(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_skipped.py"])
    (tmp_path / "test_skipped.py").write_text(
        """import pytest

@pytest.mark.skip(reason="not available")
def test_skipped():
    pass
""",
        encoding="utf-8",
    )

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.summary is not None and outcome.summary.executed == 0


def test_service_blocks_invalid_enabled_plan_without_starting_pytest(tmp_path: Path) -> None:
    _configure(tmp_path, args=["--junitxml=outside.xml"])

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.result is not None
    assert outcome.result.commands == []
    assert any("Core 固定参数" in item for item in outcome.result.blocking_findings)


def test_service_blocks_when_test_changes_candidate(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_mutates.py"])
    (tmp_path / "test_mutates.py").write_text(
        """from pathlib import Path

def test_mutates_candidate():
    Path("changed-during-test.txt").write_text("changed", encoding="utf-8")
""",
        encoding="utf-8",
    )

    service = ExtensionService(tmp_path)
    outcome = service.run_fresh_verification()

    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.result is not None
    assert any("当前代码版本发生变化" in item for item in outcome.result.blocking_findings)
    metric_path = service.record_verification_metric(outcome, legacy_would_pass=True)
    assert metric_path is not None
    metric = json.loads(metric_path.read_text(encoding="utf-8").splitlines()[-1])
    assert metric["candidate_changed_during_run"] is True


def test_service_isolates_home_and_temp_inside_run_dir(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_home.py"])
    (tmp_path / "test_home.py").write_text(
        """from pathlib import Path

def test_home_is_writable():
    (Path.home() / "fresh-verification-marker.txt").write_text("ok", encoding="utf-8")
""",
        encoding="utf-8",
    )

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.PASS
    assert outcome.result_path is not None
    marker = outcome.result_path.parent / "user-home" / "fresh-verification-marker.txt"
    assert marker.read_text(encoding="utf-8") == "ok"


def test_service_timeout_blocks_and_confirms_process_tree_cleanup(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_slow.py"], timeout=1)
    (tmp_path / "test_slow.py").write_text(
        """import time

def test_slow():
    time.sleep(10)
""",
        encoding="utf-8",
    )

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.result is not None
    assert outcome.result.process_tree_clean is True
    assert outcome.result.commands[0].timed_out is True


def test_service_cancellation_blocks_and_confirms_process_tree_cleanup(tmp_path: Path) -> None:
    _configure(tmp_path, args=["-q", "test_slow.py"], timeout=30)
    (tmp_path / "test_slow.py").write_text(
        """import time

def test_slow():
    time.sleep(10)
""",
        encoding="utf-8",
    )
    cancel = threading.Event()
    timer = threading.Timer(0.3, cancel.set)
    timer.start()
    try:
        outcome = ExtensionService(tmp_path).run_fresh_verification(cancel_event=cancel)
    finally:
        timer.cancel()

    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.result is not None
    assert outcome.result.process_tree_clean is True
    assert outcome.result.commands[0].cancelled is True


def test_fresh_verification_manifest_and_source_lock_are_aligned(tmp_path: Path) -> None:
    service = ExtensionService(tmp_path)
    manifest = service.load(service.fresh_verification_manifest_path)

    verification = service.verify_source(manifest)

    assert verification.status == ExtensionStatus.PASS


def test_service_records_unreviewed_metric_without_self_adjudication(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _configure(tmp_path, args=["-q", "test_sample.py"])
    (tmp_path / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    replay_contract_path = (
        tmp_path / ".super-dev" / "changes" / "completion-verification" / "replay-scenarios.yaml"
    )
    replay_contract_path.parent.mkdir(parents=True)
    replay_contract_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "scenarios": [
                    {"id": f"scenario-{index}", "expected_status": "PASS"} for index in range(10)
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    service = ExtensionService(tmp_path)
    outcome = service.run_fresh_verification()
    captured_digest = ""
    actual_summarize = service_module.summarize_verification_metrics

    def capture_current_digest(*args, **kwargs):
        nonlocal captured_digest
        captured_digest = kwargs.get("current_candidate_digest", "")
        return actual_summarize(*args, **kwargs)

    monkeypatch.setattr(service_module, "summarize_verification_metrics", capture_current_digest)

    metric_path = service.record_verification_metric(outcome, legacy_would_pass=True)

    assert metric_path is not None
    assert captured_digest == build_candidate_identity(tmp_path).candidate_digest
    payload = json.loads(metric_path.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["run_id"] == outcome.run_id
    assert payload["adjudication"] == "unreviewed"
    assert payload["false_block"] is None
    summary_path = metric_path.with_name("verification-pilot-summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total_runs"] == 1
    assert summary["unreviewed_runs"] == 1
    assert summary["replay_scenarios_defined"] == 10
    assert summary["replay_scenarios"] == 0
    assert any("缺失 10 条实测回放记录" in item for item in summary["warnings"])
    assert summary["recommend_stage_2b"] is False


def test_service_stops_temp_projects_from_inheriting_parent_git(tmp_path: Path) -> None:
    subprocess.run(
        ["git", "init", "-q"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    _configure(tmp_path, args=["-q", "test_git_boundary.py"])
    (tmp_path / "test_git_boundary.py").write_text(
        """import subprocess
from pathlib import Path

def test_git_boundary(tmp_path):
    project = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
        check=False,
        capture_output=True,
        text=True,
    )
    nested = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert project.returncode == 0
    assert nested.returncode != 0
""",
        encoding="utf-8",
    )

    outcome = ExtensionService(tmp_path).run_fresh_verification()

    assert outcome.status == ExtensionStatus.PASS
