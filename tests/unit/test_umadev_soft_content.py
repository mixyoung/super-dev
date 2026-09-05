"""Verify adapted guidance through the existing rendering and retrieval paths."""

from pathlib import Path

import pytest

from super_dev.creators.document_generator import DocumentGenerator
from super_dev.orchestrator.knowledge_pusher import KnowledgePusher

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("frontend", ["none", "react"])
def test_acceptance_matrix_follows_frontend_scope(frontend: str) -> None:
    prd = DocumentGenerator(
        name="sample", description="校验输入并报告错误", frontend=frontend
    ).generate_prd()
    matrix = prd.split("### 7.4 业务验收矩阵", 1)[1].split("## 8. 发布计划", 1)[0]
    assert ("| UI/UX 完成度 |" in matrix) == (frontend != "none")
    assert "| 工程质量 |" in matrix
    # Traceability is a blank recording structure, not invented requirements or passing tests.
    trace = matrix.split("| 需求/缺陷/不变量 |", 1)[1]
    rows = [line for line in trace.splitlines() if line.startswith("|")]
    assert len(rows) == 1  # separator, with no fabricated data rows


def test_cli_delivery_guidance_does_not_require_pages() -> None:
    prd = DocumentGenerator(
        name="local-tool", description="离线日志检查", platform="cli", frontend="none"
    ).generate_prd()
    delivery = prd.split("所有核心页面必须覆盖")
    assert len(delivery) == 1
    assert "按当前交付形态验证安装/启动" in prd


@pytest.mark.parametrize(
    "phase,query,filename",
    [
        ("docs", "产品发现 需求 审查", "product-discovery-and-prd-deep-dive.md"),
        ("quality", "测试策略 验证完整性", "testing-strategy-deep-dive.md"),
        ("quality", "风险驱动 测试矩阵", "risk-based-test-matrix.md"),
        ("spec", "代码评审 交付 证据", "code-review-quality-complete.md"),
        ("docs", "架构决定 未决事项 交接", "adr-template-and-examples.md"),
    ],
)
def test_adapted_knowledge_is_available_through_existing_push(
    phase: str, query: str, filename: str
) -> None:
    result = KnowledgePusher(knowledge_dir=ROOT / "knowledge").push(phase, query)
    assert any(Path(item["path"]).name == filename for item in result.files)
