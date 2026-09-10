import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "check_knowledge_gates.py"
    spec = importlib.util.spec_from_file_location("check_knowledge_gates", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_knowledge_gates_fail_when_required_files_missing(temp_project_dir: Path):
    run = _load_module().run
    ok, report = run(temp_project_dir)
    assert ok is False
    assert len(report["missing_files"]) > 0


def test_knowledge_gates_pass_with_required_assets(temp_project_dir: Path):
    run = _load_module().run
    required_md = "# 开发：Excellent（11964948@qq.com）\n\n## 内容\n"
    required_files = [
        "knowledge/development/11-ui-excellence/ui-aesthetic-system.md",
        "knowledge/development/11-ui-excellence/ui-component-excellence-standard.md",
        "knowledge/development/11-ui-excellence/ui-accessibility-wcag-playbook.md",
        "knowledge/development/12-scenarios/ai-application-scenario-pack.md",
        "knowledge/development/12-scenarios/multitenant-saas-scenario-pack.md",
        "knowledge/development/14-full-lifecycle/lifecycle-end-to-end-map.md",
        "knowledge/development/14-full-lifecycle/requirement-discovery-playbook.md",
        "knowledge/development/14-full-lifecycle/architecture-decision-gate.md",
        "knowledge/development/14-full-lifecycle/testing-verification-gate.md",
        "knowledge/development/14-full-lifecycle/security-compliance-gate.md",
        "knowledge/development/14-full-lifecycle/release-change-management-playbook.md",
        "knowledge/development/14-full-lifecycle/operations-observability-runbook.md",
        "knowledge/development/15-lifecycle-templates/requirement-template.md",
        "knowledge/development/15-lifecycle-templates/design-handoff-template.md",
        "knowledge/development/15-lifecycle-templates/architecture-adr-template.md",
        "knowledge/development/15-lifecycle-templates/implementation-pr-template.md",
        "knowledge/development/15-lifecycle-templates/testing-report-template.md",
        "knowledge/development/15-lifecycle-templates/security-compliance-template.md",
        "knowledge/development/15-lifecycle-templates/release-change-template.md",
        "knowledge/development/15-lifecycle-templates/operations-runbook-template.md",
        "knowledge/development/15-lifecycle-templates/postmortem-template.md",
        "knowledge/development/15-lifecycle-templates/lifecycle-review-board-template.md",
        "knowledge/development/DEVELOPMENT_KB_MASTER_INDEX.md",
        "knowledge/development/api-governance-complete.md",
        "knowledge/development/backend-engineering-complete.md",
        "knowledge/development/frontend-engineering-complete.md",
    ]
    for rel in required_files:
        _write(temp_project_dir / rel, required_md)

    _write(
        temp_project_dir
        / "knowledge/development/13-implementation-assets/scenario-coverage-matrix.yaml",
        "\n".join(
            [
                "coverage_matrix:",
                "  b2b:",
                "  b2c:",
                "  multitenant_saas:",
                "  internationalization:",
                "  mobile:",
                "  ai_application:",
                "  fintech:",
                "  ecommerce_peak:",
            ]
        ),
    )
    _write(
        temp_project_dir
        / "knowledge/development/13-implementation-assets/ui-kpi-and-quality-gates.yaml",
        "\n".join(
            [
                "ui_quality_gates:",
                "  token_coverage: '>=95%'",
                "  component_state_coverage: '100%'",
                "  accessibility_wcag: '2.2-AA'",
                "  lighthouse_accessibility: '>=95'",
                "  lighthouse_performance: '>=85'",
                "  visual_regression_threshold: '<=0.3%'",
                "  critical_flow_pass_rate: '100%'",
                "  blocking_bugs: 0",
            ]
        ),
    )
    _write(
        temp_project_dir / "knowledge/development/14-full-lifecycle/stage-exit-criteria.yaml",
        "\n".join(
            [
                "stage_exit_criteria:",
                "  requirement:",
                "  design:",
                "  architecture:",
                "  implementation:",
                "  testing:",
                "  security:",
                "  release:",
                "  operations:",
                "  incident_learning:",
            ]
        ),
    )
    _write(
        temp_project_dir / "knowledge/development/15-lifecycle-templates/template-catalog.yaml",
        "\n".join(
            [
                "templates:",
                "  requirement:",
                "  design:",
                "  architecture:",
                "  implementation:",
                "  testing:",
                "  security:",
                "  release:",
                "  operations:",
                "  incident_learning:",
            ]
        ),
    )
    _write(
        temp_project_dir / "knowledge/development/08-catalog/catalog.yaml",
        "\n".join(
            [
                "path: development/11-ui-excellence",
                "- ui-aesthetic-system.md",
                "- ui-component-excellence-standard.md",
                "- ui-accessibility-wcag-playbook.md",
                "path: development/12-scenarios",
                "- ai-application-scenario-pack.md",
                "- multitenant-saas-scenario-pack.md",
                "path: development/13-implementation-assets",
                "- scenario-coverage-matrix.yaml",
                "- ui-kpi-and-quality-gates.yaml",
                "path: development/14-full-lifecycle",
                "- lifecycle-end-to-end-map.md",
                "- requirement-discovery-playbook.md",
                "- architecture-decision-gate.md",
                "- testing-verification-gate.md",
                "- security-compliance-gate.md",
                "- release-change-management-playbook.md",
                "- operations-observability-runbook.md",
                "- stage-exit-criteria.yaml",
                "path: development/15-lifecycle-templates",
                "- template-catalog.yaml",
                "- requirement-template.md",
                "- design-handoff-template.md",
                "- architecture-adr-template.md",
                "- implementation-pr-template.md",
                "- testing-report-template.md",
                "- security-compliance-template.md",
                "- release-change-template.md",
                "- operations-runbook-template.md",
                "- postmortem-template.md",
                "- lifecycle-review-board-template.md",
            ]
        ),
    )

    ok, report = run(temp_project_dir)
    assert ok is True
    assert report["missing_files"] == []
    assert report["missing_scenarios"] == []
    assert report["missing_ui_gates"] == []
    assert report["missing_lifecycle_stages"] == []
    assert report["missing_template_files"] == []
    assert report["missing_template_stages"] == []
    assert report["unindexed_files_total"] == 0


def test_knowledge_gates_detects_duplicate_titles(temp_project_dir: Path):
    module = _load_module()
    required_md = "# 开发：Excellent（11964948@qq.com）\n"
    _write(temp_project_dir / "knowledge/development/11-ui-excellence/alpha-doc.md", required_md)
    _write(temp_project_dir / "knowledge/development/12-scenarios/alpha_doc.md", required_md)
    duplicates = module._collect_duplicate_titles(temp_project_dir)
    assert any(group["key"] == "alphadoc" for group in duplicates)


def test_knowledge_gates_renders_all_formats(temp_project_dir: Path):
    module = _load_module()
    ok, report = module.run(temp_project_dir)
    assert ok is False
    assert module._render_report(report, "json").startswith("{")
    assert "# Knowledge Gate Report" in module._render_report(report, "md")
    assert "<html>" in module._render_report(report, "html")
    assert "<testsuite" in module._render_report(report, "junit")
