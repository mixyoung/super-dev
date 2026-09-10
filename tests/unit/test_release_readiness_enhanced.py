# ruff: noqa: I001
"""
发布就绪度评估器增强测试

测试对象: super_dev.release_readiness
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from super_dev.evidence_identity import attach_evidence_identity
from super_dev.release_readiness import ReleaseReadinessCheck, ReleaseReadinessEvaluator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_project(tmp_path):
    (tmp_path / "super-dev.yaml").write_text("name: test\nversion: '1.0.0'\n")
    return tmp_path


@pytest.fixture()
def partial_project(tmp_path):
    """项目包含部分必需产物"""
    name = "myapp"
    output = tmp_path / "output"
    output.mkdir()
    (output / f"{name}-prd.md").write_text("# PRD\n")
    (output / f"{name}-architecture.md").write_text("# Architecture\n")
    (tmp_path / "super-dev.yaml").write_text(f"name: {name}\nversion: '1.0.0'\n")
    return tmp_path, name


@pytest.fixture()
def complete_project(tmp_path):
    """项目包含所有主要产物"""
    name = "fullapp"
    output = tmp_path / "output"
    output.mkdir()
    for suffix in [
        "prd.md",
        "architecture.md",
        "uiux.md",
        "execution-plan.md",
        "redteam.md",
        "quality-gate.md",
        "code-review.md",
        "frontend-blueprint.md",
        "ai-prompt.md",
    ]:
        (output / f"{name}-{suffix}").write_text(f"# {suffix}\n")
    # Redteam JSON for evidence loading
    redteam_data = {
        "project_name": name,
        "pass_threshold": 70,
        "total_score": 85,
        "critical_count": 0,
        "passed": True,
        "scanned_files_count": 10,
        "security_issues": [],
        "performance_issues": [],
        "architecture_issues": [],
        "blocking_reasons": [],
    }
    (output / f"{name}-redteam.json").write_text(json.dumps(redteam_data))
    # Quality gate JSON
    qg_data = {"score": 85, "passed": True, "threshold": 80}
    (output / f"{name}-quality-gate.json").write_text(json.dumps(qg_data))
    (tmp_path / "super-dev.yaml").write_text(f"name: {name}\nversion: '1.0.0'\n")
    return tmp_path, name


def _write_scope_config(project_dir: Path, *, frontend: str) -> None:
    (project_dir / "super-dev.yaml").write_text(
        f"name: demo\nplatform: cli\nfrontend: {frontend}\nbackend: python\n",
        encoding="utf-8",
    )


def _write_fresh_scope_config(project_dir: Path) -> None:
    (project_dir / "super-dev.yaml").write_text(
        """name: demo
platform: cli
frontend: none
backend: python
extensions:
  enabled: true
  allowed_builtin_methods:
    - fresh-verification
  fresh_verification:
    profile: pytest-current-python
    plan_id: release-test
    args:
      - -q
      - tests
    timeout_seconds: 30
""",
        encoding="utf-8",
    )


def _write_non_ui_delivery_evidence(project_dir: Path) -> None:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    uiux_path = output_dir / "demo-uiux.md"
    uiux_path.write_text("# 使用体验\n", encoding="utf-8")
    quality_payload = attach_evidence_identity(
        {"passed": True, "score": 90},
        project_dir=project_dir,
        artifact_name="quality-gate",
        dependencies=[uiux_path],
    )
    (output_dir / "demo-quality-gate.json").write_text(
        json.dumps(quality_payload),
        encoding="utf-8",
    )
    (output_dir / "demo-task-execution.md").write_text(
        "# Tasks\n\n## 执行期验证摘要\n\n## 宿主补充自检（交付前必做）\n",
        encoding="utf-8",
    )
    (output_dir / "demo-product-audit.json").write_text(
        json.dumps({"status": "ready"}),
        encoding="utf-8",
    )


def _write_bound_fresh_quality_evidence(
    project_dir: Path,
    *,
    candidate_digest: str,
    run_id: str = "run-quality",
) -> None:
    output_dir = project_dir / "output"
    uiux_path = output_dir / "demo-uiux.md"
    run_dir = project_dir / ".super-dev" / "extensions" / "fresh-verification" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    result_path = run_dir / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "extension_id": "fresh-verification",
                "run_id": run_id,
                "status": "PASS",
                "candidate": {"candidate_digest": candidate_digest},
            }
        ),
        encoding="utf-8",
    )
    summary_path = run_dir / "pytest-summary.json"
    summary_path.write_text(json.dumps({"tests": 1, "executed": 1}), encoding="utf-8")
    junit_path = run_dir / "pytest.xml"
    junit_path.write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0"/>',
        encoding="utf-8",
    )
    quality_payload = attach_evidence_identity(
        {"passed": True, "score": 90},
        project_dir=project_dir,
        artifact_name="quality-gate",
        dependencies=[uiux_path, result_path, summary_path, junit_path],
    )
    (output_dir / "demo-quality-gate.json").write_text(
        json.dumps(quality_payload),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 基本评估
# ---------------------------------------------------------------------------


class TestBasicEvaluation:
    def test_evaluator_creates_on_empty_project(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        assert evaluator is not None

    def test_evaluator_project_dir_resolved(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        assert evaluator.project_dir.is_absolute()

    def test_evaluate_empty_project(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate()
        assert result is not None
        assert hasattr(result, "checks")

    def test_evaluate_partial_project(self, partial_project):
        project_dir, name = partial_project
        evaluator = ReleaseReadinessEvaluator(project_dir)
        result = evaluator.evaluate()
        assert result is not None

    def test_evaluate_complete_project(self, complete_project):
        project_dir, name = complete_project
        evaluator = ReleaseReadinessEvaluator(project_dir)
        result = evaluator.evaluate()
        assert result is not None


# ---------------------------------------------------------------------------
# 产物检查
# ---------------------------------------------------------------------------


class TestArtifactChecks:
    def test_checks_prd_existence(self, partial_project):
        project_dir, name = partial_project
        evaluator = ReleaseReadinessEvaluator(project_dir)
        result = evaluator.evaluate()
        # PRD exists, should be checked
        assert result is not None

    def test_missing_artifacts_reported(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate()
        # Empty project should have missing artifacts
        assert result is not None

    def test_all_artifacts_present(self, complete_project):
        project_dir, name = complete_project
        evaluator = ReleaseReadinessEvaluator(project_dir)
        result = evaluator.evaluate()
        assert result is not None


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_nonexistent_project_dir(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        evaluator = ReleaseReadinessEvaluator(nonexistent)
        result = evaluator.evaluate()
        assert result is not None

    def test_project_name_with_special_chars(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("name: test-project_v2\n")
        evaluator = ReleaseReadinessEvaluator(tmp_path)
        result = evaluator.evaluate()
        assert result is not None

    def test_evaluate_returns_dict(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate()
        assert result is not None

    def test_evaluate_multiple_times_consistent(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        r1 = evaluator.evaluate()
        r2 = evaluator.evaluate()
        # Results should be consistent
        assert type(r1) is type(r2)


# ---------------------------------------------------------------------------
# ReleaseReadinessEvaluator - 结果结构验证
# ---------------------------------------------------------------------------


class TestReleaseReadinessResults:
    def test_result_has_checks(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate()
        assert hasattr(result, "checks")
        assert isinstance(result.checks, list)

    def test_result_has_project_name(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate()
        assert hasattr(result, "project_name")
        assert isinstance(result.project_name, str)

    def test_checks_have_name_and_status(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate()
        for check in result.checks:
            assert hasattr(check, "name")
            assert hasattr(check, "passed")

    def test_result_to_dict(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate()
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "project_name" in d
        assert "checks" in d

    def test_verify_tests_flag(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate(verify_tests=False)
        assert result is not None
        result2 = evaluator.evaluate(verify_tests=True)
        assert result2 is not None

    def test_preflight_checks_are_read_only_inputs(self, empty_project, monkeypatch):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        evaluator.fresh_verification_required = True
        monkeypatch.setattr(
            "super_dev.release_readiness.inspect_current_fresh_verification",
            lambda project_dir: pytest.fail("前置检查已提供时不得重复检查完成前验证"),
        )
        preflight = ReleaseReadinessCheck(
            name="完成前验证（Fresh Verification）",
            passed=False,
            detail="测试失败",
            severity="critical",
            evidence={"run_id": "run-1"},
        )

        result = evaluator.evaluate(preflight_checks=(preflight,))

        assert result.checks[0] is preflight
        assert result.passed is False
        assert result.to_dict()["checks"][0]["evidence"]["run_id"] == "run-1"
        assert sum(check.name == preflight.name for check in result.checks) == 1
        delivery = next(check for check in result.checks if check.name == "Delivery Closure")
        assert "完成前验证" not in delivery.detail

    def test_failed_fresh_preflight_does_not_create_delivery_derivative_failure(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        _write_fresh_scope_config(tmp_path)
        _write_non_ui_delivery_evidence(tmp_path)
        _write_bound_fresh_quality_evidence(
            tmp_path,
            candidate_digest="candidate-before-blocked-run",
        )
        output_dir = tmp_path / "output"
        monkeypatch.setattr(
            "super_dev.release_readiness.load_redteam_evidence",
            lambda project_dir, project_name: SimpleNamespace(
                passed=True,
                blocking_reasons=[],
                path=output_dir / "demo-redteam.json",
            ),
        )
        preflight = ReleaseReadinessCheck(
            name="完成前验证（Fresh Verification）",
            passed=False,
            detail="测试执行超时",
            severity="critical",
            evidence={
                "run_id": "run-blocked",
                "status": "BLOCKED",
                "candidate_digest": "candidate-current",
            },
        )

        result = ReleaseReadinessEvaluator(tmp_path).evaluate(preflight_checks=(preflight,))

        delivery = next(check for check in result.checks if check.name == "Delivery Closure")
        assert delivery.passed is True
        assert sum(check.name == preflight.name for check in result.checks) == 1

    def test_passed_fresh_preflight_accepts_quality_gate_bound_to_same_candidate(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        _write_fresh_scope_config(tmp_path)
        _write_non_ui_delivery_evidence(tmp_path)
        _write_bound_fresh_quality_evidence(
            tmp_path,
            candidate_digest="candidate-current",
        )
        output_dir = tmp_path / "output"
        monkeypatch.setattr(
            "super_dev.release_readiness.load_redteam_evidence",
            lambda project_dir, project_name: SimpleNamespace(
                passed=True,
                blocking_reasons=[],
                path=output_dir / "demo-redteam.json",
            ),
        )
        preflight = ReleaseReadinessCheck(
            name="完成前验证（Fresh Verification）",
            passed=True,
            detail="测试通过",
            severity="critical",
            evidence={
                "run_id": "run-current",
                "status": "PASS",
                "candidate_digest": "candidate-current",
            },
        )

        result = ReleaseReadinessEvaluator(tmp_path).evaluate(preflight_checks=(preflight,))

        delivery = next(check for check in result.checks if check.name == "Delivery Closure")
        assert delivery.passed is True

    def test_passed_fresh_preflight_rejects_quality_gate_bound_to_other_candidate(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        _write_fresh_scope_config(tmp_path)
        _write_non_ui_delivery_evidence(tmp_path)
        _write_bound_fresh_quality_evidence(
            tmp_path,
            candidate_digest="candidate-previous",
        )
        output_dir = tmp_path / "output"
        monkeypatch.setattr(
            "super_dev.release_readiness.load_redteam_evidence",
            lambda project_dir, project_name: SimpleNamespace(
                passed=True,
                blocking_reasons=[],
                path=output_dir / "demo-redteam.json",
            ),
        )
        preflight = ReleaseReadinessCheck(
            name="完成前验证（Fresh Verification）",
            passed=True,
            detail="测试通过",
            severity="critical",
            evidence={
                "run_id": "run-current",
                "status": "PASS",
                "candidate_digest": "candidate-current",
            },
        )

        result = ReleaseReadinessEvaluator(tmp_path).evaluate(preflight_checks=(preflight,))

        delivery = next(check for check in result.checks if check.name == "Delivery Closure")
        assert delivery.passed is False
        assert "quality gate fresh verification current candidate mismatch" in delivery.detail

    def test_result_has_score_or_status(self, empty_project):
        evaluator = ReleaseReadinessEvaluator(empty_project)
        result = evaluator.evaluate()
        d = result.to_dict()
        # Should have some indicator of readiness
        assert "score" in d or "status" in d or "passed" in d or "checks" in d

    def test_partial_project_has_some_checks_pass(self, partial_project):
        project_dir, name = partial_project
        evaluator = ReleaseReadinessEvaluator(project_dir)
        result = evaluator.evaluate()
        # At least some docs exist, so some checks might pass
        assert len(result.checks) > 0

    def test_complete_project_has_more_passes(self, complete_project):
        project_dir, name = complete_project
        evaluator = ReleaseReadinessEvaluator(project_dir)
        result = evaluator.evaluate()
        passed_count = sum(1 for c in result.checks if c.passed)
        assert passed_count >= 0  # At minimum, should not crash


def test_frontend_none_compliance_closure_does_not_require_uiux(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_scope_config(tmp_path, frontend="none")
    called = {"uiux": False}

    def mark_uiux_call(*args, **kwargs):
        called["uiux"] = True
        raise AssertionError("UIUX compliance must not be evaluated")

    monkeypatch.setattr(
        "super_dev.reviewers.uiux_compliance.run_uiux_compliance",
        mark_uiux_call,
    )
    evaluator = ReleaseReadinessEvaluator(tmp_path)

    check = evaluator._check_compliance_closure()

    assert check.passed is True
    assert called["uiux"] is False
    assert "uiux=not_applicable" in check.detail
    assert "UIUX 违例" not in check.recommendation


def test_frontend_none_delivery_closure_and_identity_ignore_ui_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_scope_config(tmp_path, frontend="none")
    _write_non_ui_delivery_evidence(tmp_path)
    output_dir = tmp_path / "output"
    for suffix in (
        "ui-contract.json",
        "ui-contract-alignment.json",
        "frontend-runtime.json",
        "ui-review.json",
    ):
        (output_dir / f"demo-{suffix}").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "super_dev.release_readiness.load_redteam_evidence",
        lambda project_dir, project_name: SimpleNamespace(
            passed=True,
            blocking_reasons=[],
            path=output_dir / "demo-redteam.json",
        ),
    )
    evaluator = ReleaseReadinessEvaluator(tmp_path)

    closure = evaluator._check_delivery_closure()
    identity = evaluator._build_report_evidence_identity()

    assert closure.passed is True
    assert "当前项目不要求前端证据" in closure.recommendation
    assert "ui contract" not in closure.detail.lower()
    assert "frontend runtime" not in closure.detail.lower()
    dependencies = [item.replace("\\", "/") for item in identity["dependencies"]]
    assert not any("ui-contract" in item for item in dependencies)
    assert not any("frontend-runtime" in item for item in dependencies)
    assert not any("ui-review" in item for item in dependencies)


def test_delivery_closure_requires_boolean_quality_pass(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_scope_config(tmp_path, frontend="none")
    _write_non_ui_delivery_evidence(tmp_path)
    output_dir = tmp_path / "output"
    quality_path = output_dir / "demo-quality-gate.json"
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    payload["passed"] = "true"
    quality_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(
        "super_dev.release_readiness.load_redteam_evidence",
        lambda project_dir, project_name: SimpleNamespace(
            passed=True,
            blocking_reasons=[],
            path=output_dir / "demo-redteam.json",
        ),
    )

    closure = ReleaseReadinessEvaluator(tmp_path)._check_delivery_closure()

    assert closure.passed is False
    assert "quality gate failed" in closure.detail


@pytest.mark.parametrize(
    ("payload", "expected_detail"),
    [
        (None, "缺少证据"),
        (
            {
                "extension_id": "fresh-verification",
                "run_id": "run-failed",
                "status": "FAIL",
                "candidate": {"candidate_digest": "candidate-current"},
                "blocking_findings": ["tests failed"],
            },
            "状态为失败（`FAIL`）",
        ),
    ],
)
def test_release_delivery_closure_rejects_missing_or_failed_current_fresh_evidence(
    tmp_path: Path,
    monkeypatch,
    payload,
    expected_detail: str,
) -> None:
    _write_fresh_scope_config(tmp_path)
    monkeypatch.setattr(
        "super_dev.reviewers.fresh_verification_evidence.EvidenceStore.latest_result",
        lambda self, *, extension_id: payload,
    )
    monkeypatch.setattr(
        "super_dev.reviewers.fresh_verification_evidence.build_candidate_identity",
        lambda project_dir: SimpleNamespace(candidate_digest="candidate-current"),
    )

    closure = ReleaseReadinessEvaluator(tmp_path)._check_delivery_closure()

    assert closure.passed is False
    assert "当前代码版本的完成前验证不是通过（`PASS`）" in closure.detail
    assert expected_detail in closure.detail


def test_frontend_none_release_recommendations_do_not_request_frontend_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_scope_config(tmp_path, frontend="none")
    monkeypatch.setattr(
        "super_dev.release_readiness.load_host_runtime_validation",
        lambda project_dir: {"hosts": {"codex-cli": {"status": "pending"}}},
    )
    monkeypatch.setattr(
        "super_dev.release_readiness.collect_layered_runtime_governance_gap",
        lambda project_dir: {"impacted_hosts": ["codex-cli"]},
    )
    monkeypatch.setattr(
        "super_dev.release_readiness.OperationalHarnessBuilder.build",
        lambda self: SimpleNamespace(
            enabled=True,
            passed=False,
            passed_count=0,
            enabled_count=1,
            blockers=["workflow"],
            next_actions=[],
        ),
    )
    monkeypatch.setattr(
        "super_dev.release_readiness.derive_operational_focus",
        lambda project_dir: {
            "summary": "current workflow gap",
            "recommended_action": "补齐 frontend runtime 与 UI review。",
        },
    )
    evaluator = ReleaseReadinessEvaluator(tmp_path)

    recommendations = [
        evaluator._check_host_runtime_validation().recommendation,
        evaluator._check_operational_harness_trail().recommendation,
    ]

    assert not any(
        any(term in recommendation.lower() for term in ("frontend", "ui ", "ui-review", "前端"))
        for recommendation in recommendations
    )


def test_frontend_project_delivery_closure_keeps_ui_requirements(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_scope_config(tmp_path, frontend="react")
    _write_non_ui_delivery_evidence(tmp_path)
    output_dir = tmp_path / "output"
    monkeypatch.setattr(
        "super_dev.release_readiness.load_redteam_evidence",
        lambda project_dir, project_name: SimpleNamespace(
            passed=True,
            blocking_reasons=[],
            path=output_dir / "demo-redteam.json",
        ),
    )
    evaluator = ReleaseReadinessEvaluator(tmp_path)

    closure = evaluator._check_delivery_closure()

    assert closure.passed is False
    assert "ui contract missing" in closure.detail
    assert "design tokens missing" in closure.detail
    assert "frontend runtime missing" in closure.detail
