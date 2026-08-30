from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from super_dev.cli import SuperDevCLI
from super_dev.evidence_identity import attach_evidence_identity
from super_dev.extensions.builtins.fresh_verification import parse_junit_summary
from super_dev.extensions.evidence import EvidenceStore, build_candidate_identity, utc_now
from super_dev.extensions.models import (
    ExtensionEvent,
    ExtensionEventType,
    ExtensionResult,
    ExtensionStatus,
)
from super_dev.extensions.service import ProbeOutcome
from super_dev.proof_pack import ProofPackBuilder
from super_dev.release_readiness import (
    ReleaseReadinessCheck,
    ReleaseReadinessEvaluator,
    ReleaseReadinessReport,
)
from super_dev.reviewers.quality_gate import (
    QualityGateResult,
    quality_evidence_dependency_paths,
)
from super_dev.web.api import get_release_readiness


def _git(project_dir: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )


def _candidate_project(tmp_path: Path, *, fresh_verification: bool) -> Path:
    project_dir = tmp_path / "candidate-project"
    project_dir.mkdir()
    extensions: dict[str, object] = {
        "enabled": False,
        "allowed_builtin_methods": [],
    }
    if fresh_verification:
        extensions = {
            "enabled": True,
            "allowed_builtin_methods": ["fresh-verification"],
            "fresh_verification": {
                "profile": "pytest-current-python",
                "plan_id": "candidate-test",
                "args": ["-q", "tests"],
                "timeout_seconds": 30,
            },
        }
    (project_dir / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "candidate-demo",
                "platform": "cli",
                "frontend": "none",
                "backend": "python",
                "extensions": extensions,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (project_dir / ".gitignore").write_text(
        "/output/\n/.super-dev/extensions/\n",
        encoding="utf-8",
    )
    (project_dir / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(project_dir, "init")
    _git(project_dir, "config", "user.email", "tests@example.com")
    _git(project_dir, "config", "user.name", "Tests")
    _git(project_dir, "add", ".gitignore", "super-dev.yaml", "source.py")
    _git(project_dir, "commit", "-m", "initial")

    output_dir = project_dir / "output"
    output_dir.mkdir()
    (output_dir / "candidate-demo-uiux.md").write_text(
        "# 使用体验\n",
        encoding="utf-8",
    )
    (output_dir / "candidate-demo-task-execution.md").write_text(
        "# Tasks\n\n## 执行期验证摘要\n\n## 宿主补充自检（交付前必做）\n",
        encoding="utf-8",
    )
    (output_dir / "candidate-demo-product-audit.json").write_text(
        json.dumps({"status": "ready"}),
        encoding="utf-8",
    )
    return project_dir


def _write_fresh_pass(project_dir: Path) -> tuple[str, Path, Path]:
    candidate = build_candidate_identity(project_dir)
    run_id = "run-current"
    store = EvidenceStore(project_dir)
    result = ExtensionResult(
        schema_version=1,
        run_id=run_id,
        extension_id="fresh-verification",
        extension_version="0.1.0",
        status=ExtensionStatus.PASS,
        canonical_stage="delivery",
        source_digest="sha256:" + "0" * 64,
        candidate=candidate,
    )
    result_path = store.write_result(result)
    junit_path = store.run_dir(run_id) / "pytest.xml"
    junit_path.write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0" time="0.01" />',
        encoding="utf-8",
    )
    summary_path = store.write_run_json(
        run_id,
        "pytest-summary.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "status": "PASS",
            "pytest_summary": parse_junit_summary(junit_path).to_dict(),
        },
    )
    store.append_event(
        ExtensionEvent(
            schema_version=1,
            event=ExtensionEventType.COMPLETED,
            run_id=run_id,
            extension_id="fresh-verification",
            canonical_stage="delivery",
            actor="pytest",
            timestamp=utc_now(),
            candidate_digest=candidate.candidate_digest,
            result_artifact=str(result_path.relative_to(project_dir)).replace("\\", "/"),
        )
    )
    return candidate.candidate_digest, result_path, summary_path


def _write_current_quality_gate(project_dir: Path) -> Path:
    output_dir = project_dir / "output"
    dependencies = quality_evidence_dependency_paths(
        project_dir,
        project_name="candidate-demo",
        frontend_required=False,
    )
    payload = attach_evidence_identity(
        {"passed": True, "score": 100},
        project_dir=project_dir,
        artifact_name="quality-gate",
        dependencies=dependencies,
    )
    path = output_dir / "candidate-demo-quality-gate.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_extension_validate_and_disabled_probe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "frontend": "next",
                "backend": "node",
                "extensions": {"enabled": False, "allowed_builtin_methods": []},
            }
        ),
        encoding="utf-8",
    )
    service_manifest = (
        Path(__file__).parents[2] / "super_dev" / "extensions" / "builtins" / "contract_probe.yaml"
    )
    cli = SuperDevCLI()

    assert cli.run(["extension", "validate", str(service_manifest), "--json"]) == 0
    assert cli.run(["extension", "inspect", str(service_manifest), "--json"]) == 0
    assert cli.run(["extension", "verify-source", str(service_manifest), "--json"]) == 0
    assert cli.run(["extension", "probe-contract", "--json"]) == 3


def test_enabled_probe_and_history_are_wired(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "frontend": "next",
                "backend": "node",
                "extensions": {
                    "enabled": True,
                    "allowed_builtin_methods": ["contract-probe"],
                },
            }
        ),
        encoding="utf-8",
    )
    cli = SuperDevCLI()

    assert cli.run(["extension", "probe-contract", "--json"]) == 0
    assert cli.run(["extension", "history", "--limit", "10", "--json"]) == 0
    assert (tmp_path / ".super-dev" / "extensions" / "history.jsonl").exists()


def test_release_readiness_is_the_only_fresh_verification_entry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "frontend": "next",
                "backend": "python",
                "extensions": {
                    "enabled": True,
                    "allowed_builtin_methods": ["fresh-verification"],
                    "fresh_verification": {
                        "profile": "pytest-current-python",
                        "plan_id": "completion-pilot",
                        "args": ["-q", "test_sample.py"],
                        "timeout_seconds": 30,
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n",
        encoding="utf-8",
    )

    result = SuperDevCLI().run(["release", "readiness", "--json"])

    assert result == 1  # 这个最小项目仍缺少其他正式发布证据。
    report_path = next((tmp_path / "output").glob("*-release-readiness.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    check = next(
        item for item in report["checks"] if item["name"] == "完成前验证（Fresh Verification）"
    )
    assert check["passed"] is True
    assert check["evidence"]["run_id"]
    assert check["evidence"]["pytest_summary"]["executed"] == 1
    result_payload = json.loads(Path(check["evidence"]["result_path"]).read_text(encoding="utf-8"))
    assert check["evidence"]["candidate_digest"] == result_payload["candidate"]["candidate_digest"]
    assert (
        tmp_path / ".super-dev" / "extensions" / "metrics" / "verification-pilot.jsonl"
    ).exists()


def test_enabled_fresh_verification_does_not_repeat_legacy_verify_tests(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "frontend": "next",
                "backend": "python",
                "extensions": {
                    "enabled": True,
                    "allowed_builtin_methods": ["fresh-verification"],
                    "fresh_verification": {
                        "profile": "pytest-current-python",
                        "plan_id": "completion-pilot",
                        "args": ["-q", "test_sample.py"],
                        "timeout_seconds": 30,
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "test_sample.py").write_text(
        "def test_ok():\n    assert True\n",
        encoding="utf-8",
    )

    def fail_if_legacy_runs(self):
        raise AssertionError("旧 --verify-tests 路径不应重复执行")

    monkeypatch.setattr(
        "super_dev.release_readiness.ReleaseReadinessEvaluator._check_test_suite",
        fail_if_legacy_runs,
    )

    assert SuperDevCLI().run(["release", "readiness", "--verify-tests", "--json"]) == 1


def test_release_readiness_first_screen_explains_non_strict_xpass(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "frontend": "next",
                "backend": "python",
                "extensions": {
                    "enabled": True,
                    "allowed_builtin_methods": ["fresh-verification"],
                    "fresh_verification": {
                        "profile": "pytest-current-python",
                        "plan_id": "completion-pilot",
                        "args": ["-q", "test_xpass.py"],
                        "timeout_seconds": 30,
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "test_xpass.py").write_text(
        """import pytest

@pytest.mark.xfail(reason="known")
def test_xpass():
    assert True
""",
        encoding="utf-8",
    )

    assert SuperDevCLI().run(["release", "readiness"]) == 1
    output = capsys.readouterr().out
    assert "完成前验证" in output
    assert "原本预计失败" in output
    assert "证据：" in output


@pytest.mark.parametrize(
    ("verification_status", "expected_label"),
    [
        (ExtensionStatus.FAIL, "失败（FAIL）"),
        (ExtensionStatus.BLOCKED, "受阻（BLOCKED）"),
    ],
)
def test_release_readiness_first_screen_distinguishes_fail_and_blocked(
    tmp_path: Path,
    monkeypatch,
    capsys,
    verification_status: ExtensionStatus,
    expected_label: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        "name: cli-test\nplatform: cli\nfrontend: none\nbackend: python\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "super_dev.extensions.service.ExtensionService.run_fresh_verification",
        lambda self, **kwargs: ProbeOutcome(
            status=verification_status,
            message=f"verification {verification_status.value.lower()}",
        ),
    )

    assert SuperDevCLI().run(["release", "readiness"]) == 1
    output = capsys.readouterr().out

    assert f"完成前验证：{expected_label}" in output


def test_proof_pack_and_web_api_do_not_trigger_fresh_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "frontend": "next",
                "backend": "python",
                "extensions": {
                    "enabled": True,
                    "allowed_builtin_methods": ["fresh-verification"],
                    "fresh_verification": {
                        "profile": "pytest-current-python",
                        "plan_id": "completion-pilot",
                        "args": ["-q", "tests"],
                        "timeout_seconds": 30,
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def unexpected_execution(self, **kwargs):
        raise AssertionError("非命令行发布就绪入口不得执行完成前验证")

    monkeypatch.setattr(
        "super_dev.extensions.service.ExtensionService.run_fresh_verification",
        unexpected_execution,
    )

    def unexpected_ambient_pytest(self):
        raise AssertionError("完成前验证启用时 proof-pack 不得运行环境 pytest")

    monkeypatch.setattr(
        "super_dev.release_readiness.ReleaseReadinessEvaluator._check_test_suite",
        unexpected_ambient_pytest,
    )

    ReleaseReadinessEvaluator(tmp_path).evaluate()
    ProofPackBuilder(tmp_path).build(verify_tests=False)
    proof_report = ProofPackBuilder(tmp_path).build(verify_tests=True)
    release_artifact = next(
        item for item in proof_report.artifacts if item.name == "Release Readiness"
    )
    assert release_artifact.status == "pending"
    assert "super-dev release readiness" in release_artifact.summary
    asyncio.run(
        get_release_readiness(
            project_dir=str(tmp_path),
            verify_tests=False,
            persist=False,
        )
    )


def test_proof_pack_preserves_existing_release_readiness_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = _candidate_project(tmp_path, fresh_verification=False)
    builder = ProofPackBuilder(project_dir)
    evaluator = ReleaseReadinessEvaluator(project_dir)
    report_path = project_dir / "output" / f"{builder.project_name}-release-readiness.json"
    payload = {
        "score": 48,
        "passed": False,
        "checks": [
            {
                "name": "完成前验证（Fresh Verification）",
                "passed": True,
                "detail": "当前代码版本已完成隔离验证",
            }
        ],
        "evidence_identity": evaluator._build_report_evidence_identity(),
    }
    original_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    report_path.write_bytes(original_bytes)

    def unexpected_evaluate(*args, **kwargs):
        raise AssertionError("已有发布就绪证据时不得重新评估")

    monkeypatch.setattr(ReleaseReadinessEvaluator, "evaluate", unexpected_evaluate)

    artifact = builder._release_readiness_artifact(False)

    assert report_path.read_bytes() == original_bytes
    assert artifact.name == "Release Readiness"
    assert artifact.status == "pending"
    assert artifact.summary == "score=48/100, passed=False"
    assert artifact.path == str(report_path)
    assert artifact.details == payload


def test_proof_pack_verify_tests_keeps_legacy_test_path_when_fresh_is_disabled(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = _candidate_project(tmp_path, fresh_verification=False)
    calls = 0

    def record_ambient_pytest(self):
        nonlocal calls
        calls += 1
        return ReleaseReadinessCheck(
            name="Test Suite",
            passed=True,
            detail="legacy pytest passed",
            severity="low",
        )

    monkeypatch.setattr(
        "super_dev.release_readiness.ReleaseReadinessEvaluator._check_test_suite",
        record_ambient_pytest,
    )

    artifact = ProofPackBuilder(project_dir)._release_readiness_artifact(True)

    assert calls == 1
    assert artifact.name == "Release Readiness"


def test_source_change_invalidates_quality_release_and_proof_fresh_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = _candidate_project(tmp_path, fresh_verification=True)
    candidate_digest, result_path, summary_path = _write_fresh_pass(project_dir)
    quality_path = _write_current_quality_gate(project_dir)
    output_dir = project_dir / "output"
    monkeypatch.setattr(
        "super_dev.release_readiness.load_redteam_evidence",
        lambda project_dir, project_name: type(
            "RedTeamEvidence",
            (),
            {"passed": True, "blocking_reasons": [], "path": output_dir / "redteam.json"},
        )(),
    )
    evaluator = ReleaseReadinessEvaluator(project_dir)
    incomplete_report = ReleaseReadinessReport(
        project_name=evaluator.project_name,
        checks=[
            ReleaseReadinessCheck(
                name="完成前验证（Fresh Verification）",
                passed=True,
                detail="missing candidate binding",
                severity="critical",
                evidence={"run_id": "run-current", "status": "PASS"},
            )
        ],
    )
    incomplete_path = evaluator.write(incomplete_report)["json"]
    incomplete_bytes = incomplete_path.read_bytes()
    builder = ProofPackBuilder(project_dir)
    incomplete_artifact = builder._release_readiness_artifact(False)
    assert incomplete_artifact.status == "pending"
    assert "completion verification check" in incomplete_artifact.summary
    assert incomplete_path.read_bytes() == incomplete_bytes

    completion_check = ReleaseReadinessCheck(
        name="完成前验证（Fresh Verification）",
        passed=True,
        detail="当前代码版本验证通过",
        severity="critical",
        evidence={
            "run_id": "run-current",
            "status": "PASS",
            "candidate_digest": candidate_digest,
            "result_path": str(result_path),
        },
    )
    report = ReleaseReadinessReport(
        project_name=evaluator.project_name,
        checks=[completion_check],
    )
    release_path = evaluator.write(report)["json"]
    release_payload = json.loads(release_path.read_text(encoding="utf-8"))
    release_dependencies = [
        item.replace("\\", "/") for item in release_payload["evidence_identity"]["dependencies"]
    ]
    assert release_payload["evidence_identity"]["candidate_digest"] == candidate_digest
    assert str(result_path.relative_to(project_dir)).replace("\\", "/") in release_dependencies
    assert str(summary_path.relative_to(project_dir)).replace("\\", "/") in release_dependencies
    junit_path = result_path.parent / "pytest.xml"
    assert str(junit_path.relative_to(project_dir)).replace("\\", "/") in release_dependencies

    assert evaluator._check_delivery_closure().passed is True
    assert builder._quality_gate_artifact().status == "ready"
    assert builder._release_readiness_artifact(False).status == "ready"

    result_bytes = result_path.read_bytes()
    quality_bytes = quality_path.read_bytes()
    release_bytes = release_path.read_bytes()
    (project_dir / "source.py").write_text("VALUE = 2\n", encoding="utf-8")

    closure = evaluator._check_delivery_closure()
    quality_artifact = builder._quality_gate_artifact()
    release_artifact = builder._release_readiness_artifact(False)

    assert closure.passed is False
    assert "当前代码版本的完成前验证不是通过（`PASS`）" in closure.detail
    assert quality_artifact.status == "pending"
    assert "current code version" in quality_artifact.summary
    assert release_artifact.status == "pending"
    assert "stale" in release_artifact.summary
    assert "super-dev release readiness" in release_artifact.summary
    assert result_path.read_bytes() == result_bytes
    assert quality_path.read_bytes() == quality_bytes
    assert release_path.read_bytes() == release_bytes


def test_release_readiness_blocks_when_verification_evidence_cannot_be_written(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        "name: cli-test\nfrontend: next\nbackend: python\n",
        encoding="utf-8",
    )

    def fail_to_write(self, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(
        "super_dev.extensions.service.ExtensionService.run_fresh_verification",
        fail_to_write,
    )

    assert SuperDevCLI().run(["release", "readiness", "--json"]) == 1
    report_path = next((tmp_path / "output").glob("*-release-readiness.json"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    check = next(
        item for item in report["checks"] if item["name"] == "完成前验证（Fresh Verification）"
    )
    assert check["passed"] is False
    assert "无法形成完整证据" in check["detail"]


def test_compliance_spec_preserves_project_description(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    description = "宿主内 AI Coding 流程治理与商业级软件交付的 Python CLI 工具"
    config_path = tmp_path / "super-dev.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "description": description,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assert SuperDevCLI().run(["compliance", "--type", "spec", "--json"]) == 0
    assert yaml.safe_load(config_path.read_text(encoding="utf-8"))["description"] == description


def test_quality_identity_for_frontend_none_keeps_core_doc_and_fresh_result_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        "name: cli-test\nplatform: cli\nfrontend: none\nbackend: python\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "cli-test-uiux.md").write_text("# 使用体验\n", encoding="utf-8")
    (output_dir / "cli-test-ui-review.json").write_text("{}", encoding="utf-8")
    (output_dir / "cli-test-ui-contract-alignment.json").write_text("{}", encoding="utf-8")
    fresh_result = tmp_path / ".super-dev" / "extensions" / "runs" / "run-1" / "result.json"
    fresh_result.parent.mkdir(parents=True)
    fresh_result.write_text('{"status":"PASS"}\n', encoding="utf-8")

    def fake_check(self, redteam_report=None):
        self.latest_fresh_verification_dependencies = [fresh_result]
        return QualityGateResult(
            passed=True,
            total_score=100,
            weighted_score=100.0,
            scenario="1-N+1",
        )

    monkeypatch.setattr(
        "super_dev.reviewers.quality_gate.QualityGateChecker.check",
        fake_check,
    )

    assert SuperDevCLI().run(["quality", "--type", "all"]) == 0
    payload = json.loads((output_dir / "cli-test-quality-gate.json").read_text(encoding="utf-8"))
    dependencies = [
        item.replace("\\", "/") for item in payload["evidence_identity"]["dependencies"]
    ]
    assert "output/cli-test-uiux.md" in dependencies
    assert ".super-dev/extensions/runs/run-1/result.json" in dependencies
    assert "output/cli-test-ui-review.json" not in dependencies
    assert "output/cli-test-ui-contract-alignment.json" not in dependencies


@pytest.mark.parametrize(
    ("quality_type", "suffix"),
    [
        ("prd", "prd"),
        ("architecture", "architecture"),
        ("ui", "uiux"),
        ("ux", "uiux"),
    ],
)
def test_lightweight_quality_requires_exact_active_change_document(
    tmp_path: Path,
    monkeypatch,
    quality_type: str,
    suffix: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        "name: historical\nplatform: cli\nfrontend: none\nbackend: python\n",
        encoding="utf-8",
    )
    change_dir = tmp_path / ".super-dev" / "changes" / "current-change"
    change_dir.mkdir(parents=True)
    (tmp_path / ".super-dev" / "workflow-state.json").write_text(
        json.dumps({"active_change_id": "current-change"}),
        encoding="utf-8",
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / f"historical-{suffix}.md").write_text("# Historical\n", encoding="utf-8")

    assert SuperDevCLI().run(["quality", "--type", quality_type]) == 1

    (output_dir / f"current-change-{suffix}.md").write_text("# Current\n", encoding="utf-8")
    assert SuperDevCLI().run(["quality", "--type", quality_type]) == 0


def test_lightweight_quality_sanitizes_active_change_artifact_prefix(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        "name: historical\nplatform: cli\nfrontend: none\nbackend: python\n",
        encoding="utf-8",
    )
    (tmp_path / ".super-dev" / "changes" / "My_Change").mkdir(parents=True)
    (tmp_path / ".super-dev" / "workflow-state.json").write_text(
        json.dumps({"active_change_id": "My_Change"}),
        encoding="utf-8",
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "my-change-prd.md").write_text("# Current\n", encoding="utf-8")

    assert SuperDevCLI().run(["quality", "--type", "prd"]) == 0


def test_lightweight_quality_keeps_glob_compatibility_without_active_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        "name: demo\nplatform: cli\nfrontend: none\nbackend: python\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "historical-prd.md").write_text("# Historical PRD\n", encoding="utf-8")

    assert SuperDevCLI().run(["quality", "--type", "prd"]) == 0
