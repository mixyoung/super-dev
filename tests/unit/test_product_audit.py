from pathlib import Path

from super_dev.analyzer import (
    ProductAuditBuilder,
    ProductAuditFinding,
    ProductAuditReport,
)
from super_dev.review_state import (
    save_host_runtime_validation,
    save_workflow_state,
)


def _prepare_product_docs(project_dir: Path) -> None:
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text(
        "super-dev update\n/super-dev 你的需求\n继续当前流程\n",
        encoding="utf-8",
    )
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text(
        "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n",
        encoding="utf-8",
    )
    (docs_dir / "WORKFLOW_GUIDE.md").write_text(
        "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
        encoding="utf-8",
    )
    (docs_dir / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n",
        encoding="utf-8",
    )


def test_product_audit_detects_missing_product_audit_doc(temp_project_dir: Path) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text(
        "super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8"
    )
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text(
        "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8"
    )
    (docs_dir / "WORKFLOW_GUIDE.md").write_text(
        "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
        encoding="utf-8",
    )

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    assert any(item.title.startswith("缺少关键产品文档") for item in report.findings)


def test_product_audit_writes_report(temp_project_dir: Path) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text(
        "super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8"
    )
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text(
        "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8"
    )
    (docs_dir / "WORKFLOW_GUIDE.md").write_text(
        "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
        encoding="utf-8",
    )
    (docs_dir / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8"
    )

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()
    files = builder.write(report)

    assert files["markdown"].exists()
    assert files["json"].exists()


def test_product_audit_reserves_revision_required_for_critical_findings() -> None:
    report = ProductAuditReport(
        project_name="demo",
        findings=[
            ProductAuditFinding(
                owner="CODE",
                category="maintainability",
                severity="high",
                title=f"high-{index}",
                summary="Existing noncritical debt.",
                recommendation="Track and reduce the debt.",
            )
            for index in range(6)
        ],
    )

    assert report.score == 0
    assert report.status == "attention"

    report.findings.append(
        ProductAuditFinding(
            owner="PRODUCT",
            category="closure",
            severity="critical",
            title="critical",
            summary="Critical product closure failure.",
            recommendation="Fix before delivery.",
        )
    )
    assert report.status == "revision_required"


def test_product_audit_uses_active_change_prefix_and_strict_closure_artifacts(
    temp_project_dir: Path,
) -> None:
    _prepare_product_docs(temp_project_dir)
    change_dir = temp_project_dir / ".super-dev" / "changes" / "current-change"
    change_dir.mkdir(parents=True)
    state_path = temp_project_dir / ".super-dev" / "workflow-state.json"
    state_path.write_text('{"active_change_id":"current-change"}', encoding="utf-8")
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "current-change-prd.md").write_text("# Current PRD\n", encoding="utf-8")
    for suffix in (
        "feature-checklist.json",
        "quality-gate.md",
        "proof-pack.json",
        "release-readiness.json",
    ):
        (output_dir / f"historical-{suffix}").write_text("{}\n", encoding="utf-8")

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()
    files = builder.write(report)

    assert report.project_name == "current-change"
    assert files["markdown"].name == "current-change-product-audit.md"
    assert files["json"].name == "current-change-product-audit.json"
    closure = next(item for item in report.findings if item.title == "交付闭环证据不完整")
    assert all(
        label in closure.summary
        for label in ("feature coverage", "quality gate", "proof pack", "release readiness")
    )


def test_product_audit_detects_layered_host_runtime_gap(temp_project_dir: Path) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text(
        "super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8"
    )
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text(
        "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8"
    )
    (docs_dir / "WORKFLOW_GUIDE.md").write_text(
        "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
        encoding="utf-8",
    )
    (docs_dir / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8"
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

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    finding = next(
        item for item in report.findings if item.title == "宿主 runtime 与交付闭环证据脱节"
    )
    assert finding.severity == "high"
    assert "codex-cli" in finding.summary
    assert "workflow continuity" in finding.recommendation


def test_product_audit_detects_compliance_artifact_gap(temp_project_dir: Path) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text(
        "super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8"
    )
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text(
        "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8"
    )
    (docs_dir / "WORKFLOW_GUIDE.md").write_text(
        "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
        encoding="utf-8",
    )
    (docs_dir / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8"
    )
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-prd.md").write_text(
        "# PRD\n\n## Requirements\n\n- The system must support auditable delivery workflows.\n",
        encoding="utf-8",
    )

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    finding = next(item for item in report.findings if item.title == "合规链证据状态未闭环")
    assert finding.severity == "high"
    assert "spec=missing" in finding.summary


def test_product_audit_distinguishes_missing_baseline_for_existing_project(
    temp_project_dir: Path,
) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text(
        "super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8"
    )
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text(
        "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8"
    )
    (docs_dir / "WORKFLOW_GUIDE.md").write_text(
        "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
        encoding="utf-8",
    )
    (docs_dir / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8"
    )

    save_workflow_state(
        temp_project_dir,
        {
            "status": "missing_baseline",
            "workflow_mode": "continue",
            "work_mode": "evolve",
            "current_step_label": "先完成当前项目 baseline 扫描",
            "recommended_command": "先扫描当前项目，再继续当前流程",
        },
    )

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    finding = next(
        item for item in report.findings if item.title == "已有项目模式缺少 baseline audit"
    )
    assert finding.severity == "high"
    assert "baseline audit" in finding.summary


def test_product_audit_distinguishes_waiting_baseline_confirmation(
    temp_project_dir: Path,
) -> None:
    docs_dir = temp_project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "QUICKSTART.md").write_text(
        "super-dev update\n/super-dev 你的需求\n继续当前流程\n", encoding="utf-8"
    )
    (docs_dir / "HOST_USAGE_GUIDE.md").write_text(
        "/super-dev 你的需求\n继续当前流程\n现在下一步是什么\n", encoding="utf-8"
    )
    (docs_dir / "WORKFLOW_GUIDE.md").write_text(
        "super-dev update\n/super-dev 做一个企业级项目管理系统\nevolve / variant / patch\n",
        encoding="utf-8",
    )
    (docs_dir / "PRODUCT_AUDIT.md").write_text(
        "super-dev product-audit\nproof-pack\nrelease readiness\n", encoding="utf-8"
    )
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "demo-baseline-audit.md").write_text("# baseline\n", encoding="utf-8")

    save_workflow_state(
        temp_project_dir,
        {
            "status": "waiting_baseline_confirmation",
            "workflow_mode": "continue",
            "work_mode": "evolve",
            "current_step_label": "等待 baseline 确认",
            "recommended_command": "先确认 baseline，再继续当前流程",
        },
    )

    builder = ProductAuditBuilder(temp_project_dir)
    report = builder.build()

    finding = next(item for item in report.findings if item.title == "已有项目 baseline 尚未确认")
    assert finding.severity == "high"
    assert "missing" in finding.summary
