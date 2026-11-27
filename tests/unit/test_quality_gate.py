"""
质量门禁检查器测试
"""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from super_dev.change_ledger import ChangeLedger
from super_dev.evidence_contract import EvidenceStatus
from super_dev.extensions.builtins.fresh_verification import parse_junit_summary
from super_dev.extensions.evidence import build_candidate_identity
from super_dev.review_state import save_host_runtime_validation, save_workflow_state
from super_dev.reviewers.quality_gate import (
    CheckStatus,
    QualityCheck,
    QualityGateChecker,
    QualityGateResult,
    inspect_current_fresh_verification,
)
from super_dev.reviewers.ui_review_evidence import RUNTIME, VISUAL
from super_dev.scope_advisory import build_scope_advisory
from super_dev.workflow_guard import save_bound_docs_confirmation
from tests.support.ui_evidence_inputs import create_ui_project, dump, publish_source


def _write_quality_config(
    project_dir: Path,
    *,
    frontend: str,
    fresh_verification: bool = False,
) -> None:
    extensions = ""
    if fresh_verification:
        extensions = (
            "extensions:\n"
            "  enabled: true\n"
            "  allowed_builtin_methods:\n"
            "    - fresh-verification\n"
            "  fresh_verification:\n"
            "    profile: pytest-current-python\n"
            "    plan_id: test-plan\n"
            "    args:\n"
            "      - -q\n"
            "      - tests\n"
            "    timeout_seconds: 120\n"
        )
    (project_dir / "super-dev.yaml").write_text(
        f"name: demo\nplatform: cli\nfrontend: {frontend}\nbackend: python\n{extensions}",
        encoding="utf-8",
    )


def _activate_quality_change(project_dir: Path, change_id: str = "current-change") -> None:
    (project_dir / ".super-dev" / "changes" / change_id).mkdir(parents=True)
    state_path = project_dir / ".super-dev" / "workflow-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"active_change_id": change_id}),
        encoding="utf-8",
    )


def _write_scope_ledger(
    project_dir: Path,
    *,
    change_id: str,
    changed_surfaces: set[str],
    scope_complete: bool = True,
) -> None:
    change_dir = project_dir / ".super-dev" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    ledger = ChangeLedger.create(
        change_id=change_id,
        harness_version="2.5.1",
        intent="build",
        governance_depth="architectural",
        work_mode="evolve",
    )
    ledger.scope_advisory = build_scope_advisory(
        changed_surfaces=changed_surfaces,
        work_mode="evolve",
        governance_depth="architectural",
        scope_complete=scope_complete,
        generated_at="2026-09-15T00:00:00+00:00",
    )
    (change_dir / "ledger.json").write_text(
        json.dumps(ledger.to_dict()),
        encoding="utf-8",
    )


def _write_fresh_run_files(
    project_dir: Path,
    *,
    run_id: str,
    tests: int = 12,
    failures: int = 0,
    errors: int = 0,
    skipped: int = 1,
    duration: float = 0.25,
) -> tuple[Path, Path]:
    run_dir = project_dir / ".super-dev" / "extensions" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    junit_path = run_dir / "pytest.xml"
    junit_path.write_text(
        (
            f'<testsuite tests="{tests}" failures="{failures}" errors="{errors}" '
            f'skipped="{skipped}" time="{duration}"></testsuite>'
        ),
        encoding="utf-8",
    )
    summary_path = run_dir / "pytest-summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "PASS",
                "pytest_summary": parse_junit_summary(junit_path).to_dict(),
            }
        ),
        encoding="utf-8",
    )
    return summary_path, junit_path


class TestQualityGateChecker:
    @pytest.mark.parametrize("surface", ["data", "database", "migration"])
    def test_high_risk_scope_requires_independent_review_evidence(
        self,
        temp_project_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        surface: str,
    ) -> None:
        _write_quality_config(temp_project_dir, frontend="none")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python", "database": "none"},
            scenario_override="1-N+1",
        )
        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        monkeypatch.setattr(
            "super_dev.reviewers.quality_gate.build_shadow_ledger_summary",
            lambda _project_dir: {"changed_surfaces": [surface]},
        )
        checker._rule_engine = None

        result = checker.check(None)

        external = [check for check in result.checks if check.category == "external_review"]
        assert len(external) == 1
        assert external[0].status is CheckStatus.FAILED
        assert result.passed is False
        assert any("高风险" in item for item in result.critical_failures)

    def test_high_risk_review_requires_exact_file_and_candidate_attestation(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_quality_config(temp_project_dir, frontend="none")
        config_path = temp_project_dir / "super-dev.yaml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8") + "version: 1.0.0\n",
            encoding="utf-8",
        )
        save_workflow_state(
            temp_project_dir,
            {
                "status": "quality",
                "flow_variant": "standard",
                "work_item_id": "current-change",
                "binding_status": "pre_spec",
            },
        )
        candidate_digest = build_candidate_identity(temp_project_dir).candidate_digest
        review_dir = temp_project_dir / "output" / "external-reviews"
        review_dir.mkdir(parents=True)
        review_path = review_dir / "deepseek.json"
        review_path.write_text(
            json.dumps(
                {
                    "source": "deepseek-v4-flash",
                    "passed": True,
                    "score": 95,
                    "issues_count": 0,
                    "critical_count": 0,
                    "summary": "read-only review passed",
                    "review_execution": {
                        "review_session_id": "review-session",
                        "producer_session_id": "producer-session",
                        "model": "deepseek-v4-flash",
                        "provider": "deepseek-payg-gy-com-dsv4f",
                        "readonly_scope": ["tracked.patch", "current/"],
                        "tool_evidence": ["read scoped bundle"],
                        "file_change_evidence": "bundle digest unchanged",
                        "work_item_id": "current-change",
                        "target_version": "1.0.0",
                        "candidate_digest": candidate_digest,
                        "host_attested": True,
                        "residual_risk_accepted": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        review_digest = hashlib.sha256(review_path.read_bytes()).hexdigest()

        def checker(attested: bool) -> QualityGateChecker:
            instance = QualityGateChecker(
                project_dir=temp_project_dir,
                name="demo",
                tech_stack={"frontend": "none", "backend": "python", "database": "none"},
                scenario_override="1-N+1",
                attested_review_files=({"review-session": review_digest} if attested else {}),
            )
            monkeypatch.setattr(instance, "_check_documentation", lambda: [])
            monkeypatch.setattr(instance, "_check_security", lambda _r: [])
            monkeypatch.setattr(instance, "_check_performance", lambda _r: [])
            monkeypatch.setattr(instance, "_check_testing", lambda: [])
            monkeypatch.setattr(instance, "_check_code_quality", lambda: [])
            monkeypatch.setattr(instance, "_check_compliance_artifacts", lambda: [])
            instance._rule_engine = None
            return instance

        monkeypatch.setattr(
            "super_dev.reviewers.quality_gate.build_shadow_ledger_summary",
            lambda _project_dir: {"changed_surfaces": ["authorization"]},
        )
        untrusted_checker = checker(False)
        untrusted_result = untrusted_checker.check(None)
        attested_result = checker(True).check(None)

        untrusted_reviews = [
            check for check in untrusted_result.checks if check.category == "external_review"
        ]
        attested_reviews = [
            check for check in attested_result.checks if check.category == "external_review"
        ]
        untrusted_advisories = [
            check
            for check in untrusted_result.checks
            if check.category == "external_review_advisory"
        ]
        assert any(check.status is CheckStatus.FAILED for check in untrusted_reviews)
        assert any("independence=blocked" in check.description for check in untrusted_advisories)
        assert all(
            check.category != "external_review_advisory"
            for check in untrusted_checker._score_bearing_checks(untrusted_result.checks)
        )
        assert len(attested_reviews) == 1
        assert attested_reviews[0].status is CheckStatus.PASSED
        assert "independence=independent" in attested_reviews[0].description

    def test_real_scope_advisory_drives_high_risk_review_requirement(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_quality_config(temp_project_dir, frontend="none")
        _write_scope_ledger(
            temp_project_dir,
            change_id="current-change",
            changed_surfaces={"authorization"},
        )
        save_workflow_state(
            temp_project_dir,
            {
                "status": "quality",
                "flow_variant": "standard",
                "work_item_id": "current-change",
                "active_change_id": "current-change",
                "binding_status": "bound",
            },
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python", "database": "none"},
            scenario_override="1-N+1",
        )
        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        checker._rule_engine = None

        result = checker.check(None)

        required = next(
            check
            for check in result.checks
            if check.name == "External Review: required for high-risk change"
        )
        assert required.status is CheckStatus.FAILED
        assert not any(check.name == "High-Risk Scope: undetermined" for check in result.checks)

    def test_missing_scope_advisory_for_explicit_work_item_is_conservative(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_quality_config(temp_project_dir, frontend="none")
        save_workflow_state(
            temp_project_dir,
            {
                "status": "quality",
                "flow_variant": "standard",
                "work_item_id": "current-change",
                "binding_status": "pre_spec",
            },
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python", "database": "none"},
            scenario_override="1-N+1",
        )
        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        checker._rule_engine = None

        result = checker.check(None)

        scope = next(
            check for check in result.checks if check.name == "High-Risk Scope: undetermined"
        )
        required = next(
            check
            for check in result.checks
            if check.name == "External Review: required for high-risk change"
        )
        assert scope.status is CheckStatus.WARNING
        assert scope.category == "external_review_advisory"
        assert required.status is CheckStatus.FAILED

    def test_high_risk_review_collection_exception_fails_closed(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from super_dev.reviewers.external_reviews import ExternalReviewCollector

        _write_quality_config(temp_project_dir, frontend="none")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python", "database": "none"},
            scenario_override="1-N+1",
        )
        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        monkeypatch.setattr(
            "super_dev.reviewers.quality_gate.build_shadow_ledger_summary",
            lambda _project_dir: {"changed_surfaces": ["data"]},
        )
        monkeypatch.setattr(
            ExternalReviewCollector,
            "collect_all",
            lambda _self: (_ for _ in ()).throw(OSError("review evidence unavailable")),
        )
        checker._rule_engine = None

        result = checker.check(None)

        collection = next(
            check for check in result.checks if check.name == "External Review: evidence collection"
        )
        assert collection.status is CheckStatus.FAILED
        assert "review evidence unavailable" in collection.description

    def test_high_risk_residual_acceptance_is_explicit_and_not_independent(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_quality_config(temp_project_dir, frontend="none")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python", "database": "none"},
            scenario_override="1-N+1",
            residual_review_risk_accepted=True,
        )
        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        monkeypatch.setattr(
            "super_dev.reviewers.quality_gate.build_shadow_ledger_summary",
            lambda _project_dir: {"changed_surfaces": ["authorization"]},
        )
        checker._rule_engine = None

        result = checker.check(None)

        review = next(
            check
            for check in result.checks
            if check.name == "External Review: required for high-risk change"
        )
        assert review.status is CheckStatus.WARNING
        assert "不得称为独立评审" in review.description

    def test_cross_review_uses_only_applicable_artifact_roles(
        self, temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_quality_config(temp_project_dir, frontend="none")
        output = temp_project_dir / "output"
        output.mkdir(parents=True, exist_ok=True)
        (output / "demo-architecture.md").write_text(
            "# Architecture\n\n当前模块边界与回退策略。",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python", "database": "none"},
            scenario_override="1-N+1",
        )
        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        checker._rule_engine = None

        result = checker.check(None)
        cross_reviews = [check for check in result.checks if check.category == "cross_review"]

        assert cross_reviews
        assert all(check.name.startswith("Cross-Review: ARCHITECT") for check in cross_reviews)

    def test_scenario_override_zero_to_one(self, temp_project_dir: Path):
        # 即使存在源码目录，通过 override 仍应按 0-1 判定
        (temp_project_dir / "src").mkdir(parents=True, exist_ok=True)

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="0-1",
        )
        assert checker.is_zero_to_one is True

    def test_scenario_override_one_to_many(self, temp_project_dir: Path):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="1-N+1",
        )
        assert checker.is_zero_to_one is False

    def test_threshold_override(self, temp_project_dir: Path, monkeypatch):
        _write_quality_config(temp_project_dir, frontend="none")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python"},
            scenario_override="1-N+1",
            threshold_override=95,
        )

        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        monkeypatch.setattr(checker, "_calculate_total_score", lambda _c: 100)
        monkeypatch.setattr(checker, "_calculate_weighted_score", lambda _c: 90.0)
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])
        checker._rule_engine = None

        result = checker.check(None)

        assert result.total_score == 100
        assert result.weighted_score == 90.0
        assert result.critical_failures == []
        assert result.passed is False

    def test_threshold_override_uses_weighted_score(self, temp_project_dir: Path, monkeypatch):
        _write_quality_config(temp_project_dir, frontend="none")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python"},
            scenario_override="1-N+1",
            threshold_override=90,
        )

        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        monkeypatch.setattr(checker, "_calculate_total_score", lambda _c: 89)
        monkeypatch.setattr(checker, "_calculate_weighted_score", lambda _c: 90.93)
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])
        checker._rule_engine = None

        result = checker.check(None)

        assert result.total_score == 89
        assert result.weighted_score == 90.93
        assert result.gate_score == 90.93
        assert result.threshold == 90.0
        assert result.critical_failures == []
        assert result.passed is True
        assert result.to_dict()["gate_score"] == 90.93
        assert result.to_dict()["threshold"] == 90.0

    def test_required_failed_check_blocks_gate_even_with_high_score(
        self, temp_project_dir: Path, monkeypatch
    ):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="1-N+1",
        )

        failed_required = QualityCheck(
            name="安全审查",
            category="security",
            description="存在 critical 漏洞",
            status=CheckStatus.FAILED,
            score=95,
            weight=1.5,
        )
        passing_docs = QualityCheck(
            name="PRD 文档",
            category="documentation",
            description="文档完整",
            status=CheckStatus.PASSED,
            score=100,
            weight=1.0,
        )
        checks = [failed_required, passing_docs]

        monkeypatch.setattr(checker, "_check_documentation", lambda: [passing_docs])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [failed_required])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约执行",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(checker, "_calculate_total_score", lambda _c: 95)
        monkeypatch.setattr(checker, "_calculate_weighted_score", lambda _c: 95.0)
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])

        result = checker.check(None)
        assert result.passed is False
        assert result.critical_failures
        assert checks[0].description in result.critical_failures[0]

    def test_testing_check_runs_pytest(self, temp_project_dir: Path, monkeypatch):
        tests_dir = temp_project_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_demo.py").write_text("def test_demo(): assert True\n", encoding="utf-8")
        (temp_project_dir / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )

        monkeypatch.setattr(
            "super_dev.reviewers.quality_gate_evidence_mixin.shutil.which",
            lambda _: "/usr/bin/pytest",
        )
        monkeypatch.setattr(
            checker,
            "_run_command",
            lambda cmd, timeout=120: {
                "returncode": 0,
                "stdout": "1 passed in 0.01s",
                "stderr": "",
                "timed_out": False,
            },
        )
        monkeypatch.setattr(checker, "_read_coverage_percent", lambda: 82)

        checks = checker._check_testing()
        names = {c.name: c for c in checks}
        assert names["测试执行"].status.value == "passed"
        assert names["测试覆盖率"].score == 82

    def test_testing_check_failed_when_pytest_fails(self, temp_project_dir: Path, monkeypatch):
        tests_dir = temp_project_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_demo.py").write_text("def test_demo(): assert False\n", encoding="utf-8")

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )

        monkeypatch.setattr(
            "super_dev.reviewers.quality_gate_evidence_mixin.shutil.which",
            lambda _: "/usr/bin/pytest",
        )
        monkeypatch.setattr(
            checker,
            "_run_command",
            lambda cmd, timeout=120: {
                "returncode": 1,
                "stdout": "1 failed in 0.01s",
                "stderr": "",
                "timed_out": False,
            },
        )
        monkeypatch.setattr(checker, "_read_coverage_percent", lambda: 40)

        checks = checker._check_testing()
        names = {c.name: c for c in checks}
        assert names["测试执行"].status.value == "failed"
        assert names["测试覆盖率"].status.value == "failed"

    def test_testing_uses_current_fresh_pass_without_running_ambient_pytest(
        self,
        temp_project_dir: Path,
        monkeypatch,
    ):
        _write_quality_config(
            temp_project_dir,
            frontend="none",
            fresh_verification=True,
        )
        _write_fresh_run_files(temp_project_dir, run_id="run-current")
        payload = {
            "extension_id": "fresh-verification",
            "run_id": "run-current",
            "status": "PASS",
            "candidate": {"candidate_digest": "candidate-current"},
        }
        monkeypatch.setattr(
            "super_dev.reviewers.fresh_verification_evidence.EvidenceStore.latest_result",
            lambda self, *, extension_id: payload,
        )
        monkeypatch.setattr(
            "super_dev.reviewers.fresh_verification_evidence.build_candidate_identity",
            lambda project_dir: SimpleNamespace(candidate_digest="candidate-current"),
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python"},
        )
        monkeypatch.setattr(
            checker,
            "_run_command",
            lambda *args, **kwargs: pytest.fail("ambient pytest must not run"),
        )
        monkeypatch.setattr(checker, "_append_testing_evidence_checks", lambda checks: None)

        checks = checker._check_testing()
        execution = next(item for item in checks if item.name == "测试执行")

        assert execution.status == CheckStatus.PASSED
        assert "executed=11" in execution.details
        assert "failures=0" in execution.details
        assert "errors=0" in execution.details

    @pytest.mark.parametrize("mutation", ["delete-junit", "tamper-summary"])
    def test_fresh_pass_requires_junit_and_matching_summary(
        self,
        temp_project_dir: Path,
        monkeypatch,
        mutation: str,
    ) -> None:
        summary_path, junit_path = _write_fresh_run_files(
            temp_project_dir,
            run_id="run-current",
        )
        payload = {
            "extension_id": "fresh-verification",
            "run_id": "run-current",
            "status": "PASS",
            "candidate": {"candidate_digest": "candidate-current"},
        }
        monkeypatch.setattr(
            "super_dev.reviewers.fresh_verification_evidence.EvidenceStore.latest_result",
            lambda self, *, extension_id: payload,
        )
        monkeypatch.setattr(
            "super_dev.reviewers.fresh_verification_evidence.build_candidate_identity",
            lambda project_dir: SimpleNamespace(candidate_digest="candidate-current"),
        )
        if mutation == "delete-junit":
            junit_path.unlink()
        else:
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            summary_payload["pytest_summary"]["tests"] += 1
            summary_path.write_text(json.dumps(summary_payload), encoding="utf-8")

        evidence = inspect_current_fresh_verification(temp_project_dir)

        assert evidence.passed is False
        assert "JUnit" in evidence.detail

    @pytest.mark.parametrize(
        ("payload", "expected_detail"),
        [
            (None, "缺少证据"),
            (
                {
                    "extension_id": "fresh-verification",
                    "run_id": "run-stale",
                    "status": "PASS",
                    "candidate": {"candidate_digest": "candidate-old"},
                    "pytest_summary": {
                        "tests": 1,
                        "executed": 1,
                        "skipped": 0,
                        "failures": 0,
                        "errors": 0,
                    },
                },
                "已过期",
            ),
        ],
    )
    def test_testing_does_not_run_ambient_when_fresh_evidence_is_missing_or_stale(
        self,
        temp_project_dir: Path,
        monkeypatch,
        payload,
        expected_detail: str,
    ):
        _write_quality_config(
            temp_project_dir,
            frontend="none",
            fresh_verification=True,
        )
        monkeypatch.setattr(
            "super_dev.reviewers.fresh_verification_evidence.EvidenceStore.latest_result",
            lambda self, *, extension_id: payload,
        )
        monkeypatch.setattr(
            "super_dev.reviewers.fresh_verification_evidence.build_candidate_identity",
            lambda project_dir: SimpleNamespace(candidate_digest="candidate-current"),
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python"},
        )
        monkeypatch.setattr(
            checker,
            "_run_command",
            lambda *args, **kwargs: pytest.fail("ambient pytest must not run"),
        )
        monkeypatch.setattr(checker, "_append_testing_evidence_checks", lambda checks: None)

        checks = checker._check_testing()
        execution = next(item for item in checks if item.name == "测试执行")

        assert execution.status == CheckStatus.FAILED
        assert expected_detail in execution.details

    def test_read_coverage_percent(self, temp_project_dir: Path):
        coverage = temp_project_dir / "coverage.xml"
        coverage.write_text(
            '<?xml version="1.0" ?><coverage line-rate="0.756"></coverage>',
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        assert checker._read_coverage_percent() == 76

    def test_frontend_none_quality_skips_all_ui_checks(
        self,
        temp_project_dir: Path,
        monkeypatch,
    ):
        _write_quality_config(temp_project_dir, frontend="none")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python"},
        )
        checker._rule_engine = None
        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda report: [])
        monkeypatch.setattr(checker, "_check_performance", lambda report: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_accessibility",
            lambda: pytest.fail("accessibility is not applicable"),
        )
        monkeypatch.setattr(
            checker,
            "_check_performance_budget",
            lambda: pytest.fail("frontend performance budget is not applicable"),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: pytest.fail("UI contract is not applicable"),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_review",
            lambda: pytest.fail("UI review is not applicable"),
        )

        result = checker.check()

        assert checker.frontend_required is False
        assert checker.latest_ui_review_report is None
        assert not any(
            item.category in {"accessibility", "ui_quality", "uiux_compliance"}
            for item in result.checks
        )

    def test_frontend_project_quality_keeps_ui_checks(
        self,
        temp_project_dir: Path,
        monkeypatch,
    ):
        _write_quality_config(temp_project_dir, frontend="react")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        checker._rule_engine = None
        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda report: [])
        monkeypatch.setattr(checker, "_check_performance", lambda report: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_accessibility",
            lambda: [
                QualityCheck(
                    name="Accessibility",
                    category="accessibility",
                    description="frontend accessibility",
                    status=CheckStatus.PASSED,
                    score=100,
                )
            ],
        )
        monkeypatch.setattr(checker, "_check_performance_budget", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: QualityCheck(
                name="UI Contract",
                category="ui_quality",
                description="frontend UI contract",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_review",
            lambda: QualityCheck(
                name="UI Review",
                category="ui_quality",
                description="frontend UI review",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])

        result = checker.check()

        assert checker.frontend_required is True
        assert {item.name for item in result.checks} >= {
            "Accessibility",
            "UI Contract",
            "UI Review",
        }

    def test_frontend_none_document_consistency_uses_current_confirmation_binding(
        self,
        temp_project_dir: Path,
    ):
        _write_quality_config(temp_project_dir, frontend="none")
        _activate_quality_change(temp_project_dir)
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True)
        prd_lines = ["# PRD", "", "## 产品愿景", "", "## 功能需求", "", "## 验收标准"]
        prd_lines.extend(f"1. 当前需求说明 {index} 可追踪。" for index in range(100))
        architecture_lines = [
            "# Architecture",
            "",
            "## 技术栈",
            "",
            "## 数据库",
            "",
            "## API",
            "",
            "## 运行约束",
            "",
            "```",
            "config=true",
            "```",
        ]
        architecture_lines.extend(f"架构说明 {index}" for index in range(80))
        experience_lines = [
            "# 使用体验",
            "",
            "## 命令入口",
            "",
            "## 输出层级",
            "",
            "## 错误恢复",
            "",
            "## 验收反馈",
        ]
        experience_lines.extend(f"使用体验说明 {index}" for index in range(80))
        (output_dir / "current-change-prd.md").write_text("\n".join(prd_lines), encoding="utf-8")
        (output_dir / "current-change-architecture.md").write_text(
            "\n".join(architecture_lines), encoding="utf-8"
        )
        (output_dir / "current-change-uiux.md").write_text(
            "\n".join(experience_lines), encoding="utf-8"
        )
        save_bound_docs_confirmation(
            temp_project_dir,
            {"status": "confirmed", "actor": "pytest", "run_id": "docs-current"},
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python"},
        )

        checks = checker._check_documentation()
        by_name = {item.name: item for item in checks}

        assert by_name["使用体验文档"].status == CheckStatus.PASSED
        assert "Token" not in by_name["使用体验文档"].details
        assert by_name["三文档一致性"].status == CheckStatus.PASSED
        assert "binding_matches_current=True" in by_name["三文档一致性"].details
        assert "UI 五端覆盖" not in by_name["三文档一致性"].details

    def test_quality_gate_runs_compliance_checks_proactively(
        self, temp_project_dir: Path, monkeypatch
    ):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )

        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_accessibility", lambda: [])
        monkeypatch.setattr(checker, "_check_performance_budget", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="ok",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_review",
            lambda: QualityCheck(
                name="UI 审查",
                category="ui_quality",
                description="ok",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])

        monkeypatch.setattr(
            "super_dev.reviewers.spec_compliance.run_spec_compliance",
            lambda project_dir, output_dir=None: SimpleNamespace(
                total_requirements=3,
                coverage_percent=66.7,
                score=67,
            ),
        )
        monkeypatch.setattr(
            "super_dev.reviewers.architecture_drift.run_architecture_drift",
            lambda project_dir, output_dir=None: SimpleNamespace(
                total_drifts=1,
                critical_count=0,
                declared_tech_stack=["FastAPI"],
                score=78,
            ),
        )
        monkeypatch.setattr(
            "super_dev.reviewers.uiux_compliance.run_uiux_compliance",
            lambda project_dir, output_dir=None: SimpleNamespace(
                total_violations=2,
                files_scanned=4,
                score=82,
            ),
        )

        result = checker.check(None)
        categories = {check.category for check in result.checks}

        assert {"spec_compliance", "architecture_drift", "uiux_compliance"} <= categories

    def test_quality_gate_executive_summary_explains_layered_host_runtime_gap(
        self, temp_project_dir: Path, monkeypatch
    ):
        (temp_project_dir / "super-dev.yaml").write_text(
            "name: demo\nplatform: web\nfrontend: uni-app\nbackend: python\n",
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "analysis": {"frontend": "uni-app"},
                    "framework_playbook": {
                        "framework": "uni-app",
                        "implementation_modules": ["navigation"],
                        "platform_constraints": ["safe area"],
                        "execution_guardrails": ["freeze pages.json"],
                        "native_capabilities": ["login provider"],
                        "validation_surfaces": ["mini-program navigation"],
                        "delivery_evidence": ["platform matrix"],
                    },
                }
            ),
            encoding="utf-8",
        )
        save_workflow_state(
            temp_project_dir,
            {
                "status": "missing_frontend",
                "workflow_mode": "continue",
                "current_step_label": "先做前端与运行验证",
                "recommended_command": "继续当前流程，进入前端实现与运行验证",
            },
        )
        save_host_runtime_validation(
            temp_project_dir,
            {
                "hosts": {
                    "codex-cli": {
                        "status": "passed",
                        "comment": "manual accepted",
                        "actor": "pytest",
                    }
                }
            },
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )

        monkeypatch.setattr(checker, "_check_documentation", lambda: [])
        monkeypatch.setattr(checker, "_check_security", lambda _r: [])
        monkeypatch.setattr(checker, "_check_performance", lambda _r: [])
        monkeypatch.setattr(checker, "_check_testing", lambda: [])
        monkeypatch.setattr(checker, "_check_code_quality", lambda: [])
        monkeypatch.setattr(checker, "_check_accessibility", lambda: [])
        monkeypatch.setattr(checker, "_check_performance_budget", lambda: [])
        monkeypatch.setattr(checker, "_check_compliance_artifacts", lambda: [])
        monkeypatch.setattr(
            checker,
            "_check_host_compatibility",
            lambda: QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_contract_execution",
            lambda: QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约执行",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(
            checker,
            "_check_ui_review",
            lambda: QualityCheck(
                name="UI 审查",
                category="ui_quality",
                description="UI 审查",
                status=CheckStatus.PASSED,
                score=100,
            ),
        )
        monkeypatch.setattr(checker, "_generate_recommendations", lambda _c: [])

        result = checker.check(None)

        assert "codex-cli 已人工通过" in result.executive_summary
        assert "continuity / harness / runtime 证据仍未闭环" in result.executive_summary
        markdown = result.to_markdown()
        assert "## 执行摘要" in markdown
        assert "codex-cli 已人工通过" in markdown

    def test_quality_gate_executive_summary_explains_compliance_artifact_gap(self):
        result = QualityGateResult(
            passed=False,
            total_score=72,
            weighted_score=72.0,
            checks=[
                QualityCheck(
                    name="Spec Compliance (Requirement Traceability)",
                    category="spec_compliance",
                    description="Source: missing; Coverage: 0.0% (1 requirements)",
                    status=CheckStatus.FAILED,
                    score=0,
                )
            ],
            critical_failures=[],
            recommendations=[],
            scenario="1-N+1",
            summary_context={
                "compliance_signal_summary": " 合规链当前优先卡在证据状态：Spec Compliance (Requirement Traceability)=missing。"
            },
        )
        assert "合规链当前优先卡在证据状态" in result.executive_summary
        assert "Requirement Traceability)=missing" in result.executive_summary

    def test_quality_gate_executive_summary_names_warning_when_score_is_below_threshold(self):
        result = QualityGateResult(
            passed=False,
            total_score=89,
            weighted_score=89.4,
            checks=[
                QualityCheck(
                    name="Coverage Report",
                    category="testing",
                    description="覆盖率报告尚未生成",
                    status=CheckStatus.WARNING,
                    score=50,
                )
            ],
            critical_failures=[],
            recommendations=[],
            scenario="1-N+1",
            threshold=90,
        )

        assert "优先修复：Coverage Report" in result.executive_summary
        assert "关键检查" not in result.executive_summary

    def test_quality_gate_executive_summary_exposes_workflow_and_baseline_context(self):
        result = QualityGateResult(
            passed=False,
            total_score=72,
            weighted_score=72.0,
            checks=[],
            critical_failures=[],
            recommendations=[],
            scenario="1-N+1",
            summary_context={
                "workflow_signal_summary": " 当前流程状态为 waiting_baseline_confirmation，入口 gate=waiting_baseline_confirmation。 下一步：/super-dev-review baseline confirm。",
                "baseline_signal_summary": " 当前是已有项目模式，但 baseline 还没确认。 下一步：/super-dev-review baseline confirm。",
            },
        )
        assert "当前流程状态为 waiting_baseline_confirmation" in result.executive_summary
        assert "baseline 还没确认" in result.executive_summary

    def test_has_pytest_config_requires_real_marker(self, temp_project_dir: Path):
        (temp_project_dir / "pyproject.toml").write_text(
            "[project]\nname='demo'\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        assert checker._has_pytest_config() is False

    def test_has_pytest_config_from_pyproject_marker(self, temp_project_dir: Path):
        (temp_project_dir / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\naddopts='-q'\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        assert checker._has_pytest_config() is True

    def test_discover_js_test_targets_and_run(self, temp_project_dir: Path, monkeypatch):
        frontend = temp_project_dir / "frontend"
        frontend.mkdir(parents=True, exist_ok=True)
        (frontend / "package.json").write_text(
            '{"name":"frontend","scripts":{"test":"vitest run"}}',
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "node"},
            scenario_override="1-N+1",
        )

        monkeypatch.setattr(
            "super_dev.reviewers.quality_gate_evidence_mixin.shutil.which",
            lambda cmd: "/usr/bin/npm" if cmd == "npm" else None,
        )
        monkeypatch.setattr(
            checker,
            "_run_command",
            lambda cmd, timeout=120: {
                "returncode": 0,
                "stdout": "1 passed in 0.01s",
                "stderr": "",
                "timed_out": False,
            },
        )
        monkeypatch.setattr(checker, "_read_coverage_percent", lambda: 85)

        checks = checker._check_testing()
        names = {c.name: c for c in checks}
        assert checker._has_js_test_script() is True
        assert names["测试执行"].status.value == "passed"

    def test_spec_task_completion_passed(self, temp_project_dir: Path):
        task_file = temp_project_dir / ".super-dev" / "changes" / "demo" / "tasks.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            "# Tasks\n\n- [x] **1.1: done**\n- [x] **1.2: done**\n",
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_spec_task_completion()
        assert check.status.value == "passed"
        assert check.score == 100

    def test_spec_task_completion_failed_with_pending(self, temp_project_dir: Path):
        task_file = temp_project_dir / ".super-dev" / "changes" / "demo" / "tasks.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            "# Tasks\n\n- [x] **1.1: done**\n- [ ] **1.2: pending**\n",
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_spec_task_completion()
        assert check.status.value == "failed"

    def test_spec_task_completion_uses_latest_change_file(self, temp_project_dir: Path):
        legacy_task_file = temp_project_dir / ".super-dev" / "changes" / "legacy" / "tasks.md"
        legacy_task_file.parent.mkdir(parents=True, exist_ok=True)
        legacy_task_file.write_text(
            "# Tasks\n\n- [x] **1.1: done**\n- [ ] **1.2: pending**\n",
            encoding="utf-8",
        )

        latest_task_file = temp_project_dir / ".super-dev" / "changes" / "latest" / "tasks.md"
        latest_task_file.parent.mkdir(parents=True, exist_ok=True)
        latest_task_file.write_text(
            "# Tasks\n\n- [x] **2.1: done**\n- [x] **2.2: done**\n",
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_spec_task_completion()
        assert check.status.value == "passed"
        assert "latest" in check.details

    def test_document_consistency_passed_when_new_sections_complete(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text(
            "## 1\n### 1.7 联网研究证据与方案对比\n### 1.8 关键决策账本\n### 1.9 用户到专业交付统一协议\n",
            encoding="utf-8",
        )
        (output_dir / "demo-architecture.md").write_text(
            "## 1\n### 1.4 架构选型取舍与证据链\n### 1.5 架构决策账本\n### 1.6 Agent 执行流水线（全端）\n",
            encoding="utf-8",
        )
        (output_dir / "demo-uiux.md").write_text(
            (
                "## 1\n主视觉气质\n字体组合\n配色逻辑\n图标系统\n备选实现路径\n明确不默认采用\n"
                "Design Token 冻结输出\n2 个视觉方向候选\n"
                "## 2\n### 2.8 多端适配与平台化设计策略\n### 2.9 商业级设计质量门禁\nWEB\nH5\n微信小程序\nAPP\n桌面端\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_document_consistency(
            prd_path=output_dir / "demo-prd.md",
            arch_path=output_dir / "demo-architecture.md",
            uiux_path=output_dir / "demo-uiux.md",
        )
        assert check.status.value == "passed"
        assert check.score == 100

    def test_document_consistency_failed_when_platform_coverage_missing(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text(
            "## 1\n### 1.7 联网研究证据与方案对比\n### 1.8 关键决策账本\n### 1.9 用户到专业交付统一协议\n",
            encoding="utf-8",
        )
        (output_dir / "demo-architecture.md").write_text(
            "## 1\n### 1.4 架构选型取舍与证据链\n### 1.5 架构决策账本\n### 1.6 Agent 执行流水线（全端）\n",
            encoding="utf-8",
        )
        (output_dir / "demo-uiux.md").write_text(
            "## 2\n### 2.8 多端适配与平台化设计策略\n### 2.9 商业级设计质量门禁\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_document_consistency(
            prd_path=output_dir / "demo-prd.md",
            arch_path=output_dir / "demo-architecture.md",
            uiux_path=output_dir / "demo-uiux.md",
        )
        assert check.status.value == "failed"
        assert "UI 五端覆盖" in check.details

    def test_document_consistency_warns_when_ui_system_decisions_missing(
        self, temp_project_dir: Path
    ):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-prd.md").write_text(
            "## 1\n### 1.7 联网研究证据与方案对比\n### 1.8 关键决策账本\n### 1.9 用户到专业交付统一协议\n",
            encoding="utf-8",
        )
        (output_dir / "demo-architecture.md").write_text(
            "## 1\n### 1.4 架构选型取舍与证据链\n### 1.5 架构决策账本\n### 1.6 Agent 执行流水线（全端）\n",
            encoding="utf-8",
        )
        (output_dir / "demo-uiux.md").write_text(
            "## 2\n### 2.8 多端适配与平台化设计策略\n### 2.9 商业级设计质量门禁\nWEB\nH5\n微信小程序\nAPP\n桌面端\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_document_consistency(
            prd_path=output_dir / "demo-prd.md",
            arch_path=output_dir / "demo-architecture.md",
            uiux_path=output_dir / "demo-uiux.md",
        )
        assert check.status.value == "warning"
        assert "UI 风格决策冻结" in check.details

    def test_pipeline_observability_check_passed(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-pipeline-metrics.json").write_text(
            (
                "{\n"
                '  "project_name": "demo",\n'
                '  "success": true,\n'
                '  "success_rate": 100,\n'
                '  "stages": []\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_pipeline_observability()
        assert check.status.value == "passed"

    def test_host_compatibility_check_passed(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 92.5,\n'
                '    "ready_hosts": 2,\n'
                '    "total_hosts": 3\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "passed"
        assert check.score == 92

    def test_host_compatibility_check_failed_when_score_low(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 48,\n'
                '    "ready_hosts": 0,\n'
                '    "total_hosts": 5\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "failed"
        assert check.score == 48

    def test_host_compatibility_check_warning_when_missing(self, temp_project_dir: Path):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "warning"

    def test_host_compatibility_uses_config_thresholds(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "host_compatibility_min_score: 90\n"
                "host_compatibility_min_ready_hosts: 2\n"
            ),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 85,\n'
                '    "ready_hosts": 1,\n'
                '    "total_hosts": 3\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "warning"
        assert "90" in check.details

    def test_host_compatibility_override_thresholds_take_precedence(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "host_compatibility_min_score: 95\n"
                "host_compatibility_min_ready_hosts: 3\n"
            ),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 82,\n'
                '    "ready_hosts": 1,\n'
                '    "total_hosts": 3\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
            host_compatibility_min_score_override=80,
            host_compatibility_min_ready_hosts_override=1,
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "passed"

    def test_host_compatibility_uses_selected_host_profile(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "host_compatibility_min_score: 80\n"
                "host_compatibility_min_ready_hosts: 1\n"
                "host_profile_targets:\n"
                "  - codex-cli\n"
                "  - claude-code\n"
                "host_profile_enforce_selected: true\n"
            ),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 20,\n'
                '    "ready_hosts": 0,\n'
                '    "total_hosts": 6,\n'
                '    "hosts": {\n'
                '      "codex-cli": {"score": 100, "ready": true},\n'
                '      "claude-code": {"score": 90, "ready": true},\n'
                '      "cursor": {"score": 0, "ready": false}\n'
                "    }\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value == "passed"
        assert "profile=codex-cli,claude-code" in check.details

    def test_host_compatibility_selected_profile_missing_hosts(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "host_profile_targets:\n"
                "  - codex-cli\n"
                "host_profile_enforce_selected: true\n"
            ),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-host-compatibility.json").write_text(
            (
                "{\n"
                '  "compatibility": {\n'
                '    "overall_score": 100,\n'
                '    "ready_hosts": 3,\n'
                '    "total_hosts": 3,\n'
                '    "hosts": {\n'
                '      "cursor": {"score": 100, "ready": true}\n'
                "    }\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_host_compatibility()
        assert check.status.value in {"warning", "failed"}

    def test_launch_rehearsal_check_warning_when_missing(self, temp_project_dir: Path):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_launch_rehearsal()
        assert check.status.value == "warning"

    def test_rehearsal_verification_report_passed(self, temp_project_dir: Path):
        rehearsal_dir = temp_project_dir / "output" / "rehearsal"
        rehearsal_dir.mkdir(parents=True, exist_ok=True)
        (rehearsal_dir / "demo-rehearsal-report.md").write_text("# report", encoding="utf-8")
        (rehearsal_dir / "demo-rehearsal-report.json").write_text(
            '{"passed": true}', encoding="utf-8"
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_rehearsal_verification_report()
        assert check.status.value == "passed"

    def test_rehearsal_verification_report_warning_when_missing(self, temp_project_dir: Path):
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_rehearsal_verification_report()
        assert check.status.value == "warning"

    def test_cli_project_skips_service_deployment_rehearsal(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            "name: demo\nplatform: cli\nfrontend: none\nbackend: python\ndatabase: none\n",
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"platform": "cli", "frontend": "none", "backend": "python"},
            scenario_override="1-N+1",
        )

        preparation = checker._check_launch_rehearsal()
        verification = checker._check_rehearsal_verification_report()

        assert preparation.status.value == "passed"
        assert preparation.score == 100
        assert "不适用服务部署演练" in preparation.details
        assert verification.status.value == "passed"
        assert verification.score == 100

    def test_schema_drift_is_not_applicable_without_database(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            "name: demo\nplatform: cli\nfrontend: none\nbackend: python\ndatabase: none\n",
            encoding="utf-8",
        )
        source_dir = temp_project_dir / "src"
        source_dir.mkdir()
        (source_dir / "models.py").write_text("class Report: pass\n", encoding="utf-8")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"platform": "cli", "frontend": "none", "backend": "python"},
        )

        check = checker._check_schema_drift()

        assert check.status.value == "passed"
        assert check.score == 100
        assert "不适用" in check.details

    def test_task_execution_review_trace_passed(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-task-execution.md").write_text(
            (
                "# Spec 任务执行报告\n\n"
                "## 执行期验证摘要\n\n"
                "- 任务闭环: 通过\n\n"
                "## 宿主补充自检（交付前必做）\n\n"
                "- [ ] 运行项目原生 build / compile / type-check / test / runtime smoke，并确认没有编译错误\n"
                "- [ ] 检查本轮新增函数、方法、字段、模块都已接入真实调用链；未接入则删除\n"
                "- [ ] 检查没有新增 unused code、未引用文件或新增 warning\n"
                "- [ ] 对本次 diff 做最小自审，确认新增日志、埋点、恢复逻辑真正生效\n"
            ),
            encoding="utf-8",
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
        )
        check = checker._check_task_execution_review_trace()
        assert check.status.value == "passed"

    def test_task_execution_review_trace_warning_when_missing_markers(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-task-execution.md").write_text(
            "# Spec 任务执行报告\n", encoding="utf-8"
        )
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_task_execution_review_trace()
        assert check.status.value == "warning"

    def test_active_change_does_not_borrow_task_evidence(self, temp_project_dir: Path) -> None:
        _activate_quality_change(temp_project_dir)
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "current-change-prd.md").write_text("# Current PRD\n", encoding="utf-8")
        complete_trace = (
            "# Spec 任务执行报告\n\n"
            "## 执行期验证摘要\n\n"
            "## 宿主补充自检（交付前必做）\n\n"
            "build / compile / type-check / test / runtime smoke\n"
            "新增函数、方法、字段、模块都已接入真实调用链\n"
            "新增 warning\n"
            "对本次 diff 做最小自审\n"
        )
        (output_dir / "historical-task-execution.md").write_text(
            complete_trace,
            encoding="utf-8",
        )
        historical_dir = temp_project_dir / ".super-dev" / "changes" / "historical"
        historical_dir.mkdir(parents=True)
        (historical_dir / "tasks.md").write_text("# Tasks\n\n- [x] complete\n", encoding="utf-8")
        current_tasks = temp_project_dir / ".super-dev" / "changes" / "current-change" / "tasks.md"
        current_tasks.write_text("# Tasks\n\n- [ ] pending\n", encoding="utf-8")
        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "none", "backend": "python"},
        )

        assert checker._check_task_execution_review_trace().status.value == "warning"
        completion = checker._check_spec_task_completion()
        assert completion.status.value == "failed"
        assert "0/1" in completion.details

        (output_dir / "current-change-task-execution.md").write_text(
            complete_trace,
            encoding="utf-8",
        )
        assert checker._check_task_execution_review_trace().status.value == "passed"

    def test_knowledge_governance_passed(self, temp_project_dir: Path):
        (temp_project_dir / "super-dev.yaml").write_text(
            (
                "name: demo\n"
                "knowledge_allowed_domains:\n"
                "  - openai.com\n"
                "knowledge_cache_ttl_seconds: 120\n"
            ),
            encoding="utf-8",
        )
        cache_dir = temp_project_dir / "output" / "knowledge-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "demo-knowledge-bundle.json").write_text(
            (
                "{\n"
                '  "cache_signature": "abc123",\n'
                '  "cache_ttl_seconds": 120,\n'
                '  "metadata": {\n'
                '    "web_enabled": true,\n'
                '    "allowed_web_domains": ["openai.com"],\n'
                '    "web_stats": {"filtered_out_count": 1}\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_knowledge_governance()
        assert check.status.value == "passed"

    def test_knowledge_governance_failed_when_signature_missing(self, temp_project_dir: Path):
        cache_dir = temp_project_dir / "output" / "knowledge-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "demo-knowledge-bundle.json").write_text(
            ("{\n" '  "cache_ttl_seconds": 120,\n' '  "metadata": {"web_enabled": false}\n' "}\n"),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        check = checker._check_knowledge_governance()
        assert check.status.value == "failed"

    def test_knowledge_governance_warning_when_web_without_domains(self, temp_project_dir: Path):
        cache_dir = temp_project_dir / "output" / "knowledge-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "demo-knowledge-bundle.json").write_text(
            (
                "{\n"
                '  "cache_signature": "abc123",\n'
                '  "cache_ttl_seconds": 120,\n'
                '  "metadata": {"web_enabled": true, "allowed_web_domains": []}\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        checker = QualityGateChecker(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="0-1",
        )
        check = checker._check_knowledge_governance()
        assert check.status.value == "warning"

    @staticmethod
    def _ui_contract_fixture(project_dir: Path):
        evidence = create_ui_project(project_dir)
        contract = {
            "style_direction": "Editorial workspace",
            "typography": {"heading": "Space Grotesk", "body": "Inter"},
            "icon_system": "lucide-react",
            "emoji_policy": {
                "allowed_in_ui": False,
                "allowed_as_icon": False,
                "allowed_during_development": False,
            },
            "ui_library_preference": {"final_selected": "shadcn/ui + Radix + Tailwind"},
            "design_tokens": {"color": {"primary": "#0f172a"}},
            "screen_recipes": [
                {
                    "id": "home",
                    "section_order": ["main"],
                    "trust_modules": ["案例"],
                    "required_states": ["loading"],
                }
            ],
            "design_context_protocol": {
                "preferred_import_order": ["tokens"],
                "github_import_targets": ["theme.ts"],
                "single_source_rule": "single source",
            },
            "tweak_strategy": {
                "mode": "single source",
                "default_controls": ["密度"],
                "persistence_rule": "persist",
            },
            "verification_handoff": {
                "verification_order": ["preview"],
                "required_artifacts": ["index.html"],
                "acceptance_checks": ["no emoji"],
            },
        }
        dump(evidence.contract, contract)
        tokens = evidence.output / "frontend/design-tokens.css"
        tokens.parent.mkdir()
        tokens.write_text(":root { --color-primary: #0f172a; }", encoding="utf-8")
        checker = QualityGateChecker(
            project_dir=project_dir,
            name=evidence.prefix,
            tech_stack={"frontend": "react", "backend": "python"},
            scenario_override="1-N+1",
        )
        return evidence, contract, checker

    def test_ui_contract_execution_source_pass_does_not_pass_runtime_or_vision(
        self, temp_project_dir: Path
    ):
        evidence, _, checker = self._ui_contract_fixture(temp_project_dir)
        publish_source(evidence)
        assert checker._check_ui_contract_execution().status is CheckStatus.PASSED
        assert evidence.result(RUNTIME).status is EvidenceStatus.BLOCKED
        assert evidence.result(VISUAL).status is EvidenceStatus.BLOCKED

    @pytest.mark.parametrize("summary_passed", [True, False])
    def test_ui_contract_execution_does_not_use_legacy_reports(
        self, temp_project_dir: Path, summary_passed: bool
    ):
        evidence, _, checker = self._ui_contract_fixture(temp_project_dir)
        dump(evidence.path(RUNTIME), {"passed": True, "checks": {"ui_contract_json": True}})
        dump(
            evidence.output / f"{evidence.prefix}-ui-review.json",
            {
                "passed": summary_passed,
                "alignment_summary": {
                    "runtime_claude_design_protocol": {"passed": summary_passed},
                    "source_claude_design_protocol": {"passed": summary_passed},
                    "screenshot_visual_judge": {"passed": summary_passed},
                },
            },
        )
        assert checker._check_ui_contract_execution().status is CheckStatus.BLOCKED
        assert evidence.result(RUNTIME).reason == "legacy"
        assert evidence.result(VISUAL).status is EvidenceStatus.BLOCKED

    @pytest.mark.parametrize("missing", ["emoji_policy", "screen_recipes", "framework_playbook"])
    def test_ui_contract_execution_fails_when_required_contract_sections_are_missing(
        self, temp_project_dir: Path, missing: str
    ):
        evidence, contract, checker = self._ui_contract_fixture(temp_project_dir)
        if missing == "framework_playbook":
            contract["analysis"] = {"frontend": "uni-app"}
        else:
            contract.pop(missing)
        dump(evidence.contract, contract)
        check = checker._check_ui_contract_execution()
        assert check.status is CheckStatus.FAILED
        assert missing in check.details

    def test_ui_contract_execution_retains_actual_source_failure(self, temp_project_dir: Path):
        evidence, _, checker = self._ui_contract_fixture(temp_project_dir)
        publish_source(evidence, status=EvidenceStatus.FAIL)
        assert checker._check_ui_contract_execution().status is CheckStatus.FAILED
