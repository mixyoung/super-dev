"""批 D2（governance-remediation-2026-09）：发布就绪证据语义回归测试。

核心语义：未知不能算通过——无宿主真人验收记录、范围覆盖 unknown 不再折算为 PASS；
报告以三维度（流程证据/范围核实/宿主验收）+ blocked_unknowns 显式呈现；
spec compliance 解析不到需求时不再给 100 分。历史报告不回溯重打分。
"""

from pathlib import Path

from super_dev.release_readiness import ReleaseReadinessEvaluator
from super_dev.reviewers.spec_compliance import run_spec_compliance


def _prepare_minimal_project(project_dir: Path) -> None:
    output = project_dir / "output"
    output.mkdir(parents=True, exist_ok=True)
    (project_dir / "super-dev.yaml").write_text(
        "name: evidence-dims\nfrontend: none\nbackend: python\n",
        encoding="utf-8",
    )


def _find(checks, name):
    return next(check for check in checks if check.name == name)


def test_missing_host_validation_state_is_blocked_not_passed(tmp_path: Path) -> None:
    _prepare_minimal_project(tmp_path)

    report = ReleaseReadinessEvaluator(tmp_path).evaluate(verify_tests=False)

    host_check = _find(report.checks, "Host Runtime Validation")
    assert host_check.passed is False
    assert "unknown → blocked" in host_check.detail
    assert report.evidence_dimensions["host_accepted"] == "unknown"
    assert any(item.startswith("host_runtime_validation:") for item in report.blocked_unknowns)
    assert report.passed is False


def test_scope_unknown_is_blocked_not_passed(tmp_path: Path) -> None:
    _prepare_minimal_project(tmp_path)

    report = ReleaseReadinessEvaluator(tmp_path).evaluate(verify_tests=False)

    scope_check = _find(report.checks, "Scope Coverage")
    assert scope_check.passed is False
    assert "unknown → blocked" in scope_check.detail
    assert report.evidence_dimensions["scope_verified"] in {"blocked", "unknown"}


def test_report_renders_evidence_dimensions_and_blocked_unknowns(tmp_path: Path) -> None:
    _prepare_minimal_project(tmp_path)

    report = ReleaseReadinessEvaluator(tmp_path).evaluate(verify_tests=False)

    payload = report.to_dict()
    assert set(payload["evidence_dimensions"]) == {
        "process_evidence",
        "scope_verified",
        "host_accepted",
    }
    assert payload["blocked_unknowns"]

    markdown = report.to_markdown()
    assert "## Evidence Dimensions" in markdown
    assert "process_evidence" in markdown
    assert "host_accepted" in markdown
    # 未核实项必须出现在报告中，而不是被总分吸收
    assert "未核实验收项" in markdown
    # 通过口径措辞不得在存在 unknown 时宣称全部已验证
    assert "已具备对外演示、验收和上线评审的基础可信度" not in markdown


def test_spec_compliance_unparsed_requirements_score_zero(tmp_path: Path) -> None:
    _prepare_minimal_project(tmp_path)
    # 存在需求文件但内容解析不出任何需求条目
    (tmp_path / "output" / "evidence-dims-prd.md").write_text(
        "# PRD（空）\n\n本文件没有任何可解析的需求条目。\n",
        encoding="utf-8",
    )

    report = run_spec_compliance(tmp_path, tmp_path / "output", persist=False)

    assert report.total_requirements == 0
    assert report.score == 0
    assert report.requirements_unparsed is True
    payload = report.to_dict()
    assert payload["requirements_unparsed"] is True
