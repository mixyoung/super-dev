from __future__ import annotations

import json

import pytest

from super_dev.cli import SuperDevCLI
from super_dev.extensions.models import ExtensionStatus
from super_dev.extensions.service import ExtensionService
from super_dev.extensions.source_lock import SourceVerification
from tests.extensions.test_cli import _candidate_project


@pytest.mark.parametrize("failure", ["manifest", "source", "stage"])
def test_preflight_block_has_core_receipt_and_metric(tmp_path, monkeypatch, failure):
    project = _candidate_project(tmp_path, fresh_verification=True)
    service = ExtensionService(project)
    if failure == "manifest":
        service.fresh_verification_manifest_path = tmp_path / "missing.yaml"
    elif failure == "source":
        monkeypatch.setattr(
            service,
            "verify_source",
            lambda _: SourceVerification(
                status=ExtensionStatus.BLOCKED,
                expected_digest="",
                actual_digest="",
                identity_digest="",
                errors=("source mismatch",),
            ),
        )
    monkeypatch.setattr(
        "super_dev.extensions.service.StructuredExecutor.run",
        lambda *a, **k: pytest.fail("preflight must not execute"),
    )
    outcome = service.run_fresh_verification(stage="quality" if failure == "stage" else "delivery")
    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.result is not None
    assert outcome.result.commands == []
    assert outcome.result_path is not None
    receipt = json.loads(outcome.result_path.read_text(encoding="utf-8"))
    assert receipt["run_id"] == outcome.run_id
    assert receipt["extension_id"] == "fresh-verification"
    assert receipt["status"] == "BLOCKED"
    metric_path = service.record_verification_metric(outcome, legacy_would_pass=True)
    metric = json.loads(metric_path.read_text(encoding="utf-8").splitlines()[-1])
    assert metric["run_id"] == outcome.run_id
    assert metric["adjudication"] == "unreviewed"
    assert metric["tests"] is None  # not started is not a zero-test success


def test_unwritable_receipt_is_in_memory_block_not_success(tmp_path, monkeypatch):
    project = _candidate_project(tmp_path, fresh_verification=True)
    service = ExtensionService(project)
    service.fresh_verification_manifest_path = tmp_path / "missing.yaml"

    def deny(*args, **kwargs):
        raise PermissionError("read-only evidence")

    monkeypatch.setattr(service.store, "write_result", deny)
    outcome = service.run_fresh_verification()
    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.result is not None
    assert outcome.result_path is None
    assert "未落盘" in outcome.message
    assert outcome.result.writes == []


@pytest.mark.parametrize("detail", [False, True])
def test_cli_announces_before_execution_and_keeps_default_short(
    tmp_path, monkeypatch, capsys, detail
):
    project = _candidate_project(tmp_path, fresh_verification=True)
    monkeypatch.chdir(project)
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    from super_dev.extensions.executor import StructuredExecutor

    original = StructuredExecutor.run
    before = []

    def execute(self, spec):
        before.append(capsys.readouterr().out)
        return original(self, spec)

    monkeypatch.setattr(StructuredExecutor, "run", execute)
    assert SuperDevCLI().run(["release", "readiness", *(["--verbose"] if detail else [])]) == 1
    assert "测试计划：candidate-test" in before[0]
    assert "不会执行：" in before[0]
    output = capsys.readouterr().out
    assert "实际执行" in output
    assert "耗时：" in output
    assert "进程清理：" in output
    assert "下一步：" in output
    assert ("result_path" in output) == detail
    if not detail:
        assert str(project) not in output


def test_json_has_no_progress_text(tmp_path, monkeypatch, capsys):
    project = _candidate_project(tmp_path, fresh_verification=True)
    monkeypatch.chdir(project)
    assert SuperDevCLI().run(["release", "readiness", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert "checks" in payload


def test_failed_persistence_keeps_actual_command_in_memory(tmp_path, monkeypatch):
    project = _candidate_project(tmp_path, fresh_verification=True)
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    service = ExtensionService(project)

    def deny(*args, **kwargs):
        raise PermissionError("disk read only after execution")

    monkeypatch.setattr(service.store, "write_run_json", deny)
    result = service.run_fresh_verification()
    assert result.status == ExtensionStatus.BLOCKED
    assert result.result_path is None
    assert len(result.result.commands) == 1
    assert result.result.commands[0].exit_code == 0
    assert result.result.process_tree_clean
    assert "未落盘" in result.message
