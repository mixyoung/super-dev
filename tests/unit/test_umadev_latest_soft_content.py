"""Exercise the second batch through existing public generation/retrieval paths."""

from pathlib import Path

import pytest

from super_dev.creators.spec_builder import SpecBuilder
from super_dev.orchestrator.knowledge_pusher import KnowledgePusher
from super_dev.specs.generator import SpecGenerator

ROOT = Path(__file__).resolve().parents[2]


def test_spec_scaffold_keeps_unresolved_bindings_empty(tmp_path: Path) -> None:
    generator = SpecGenerator(tmp_path)
    generator.create_change("help-copy", "帮助文字", "只修改现有帮助文字，无 API 或 UI 变更")
    artifacts = generator.scaffold_change_artifacts("help-copy")
    spec = artifacts["spec.md"].read_text(encoding="utf-8")
    # Unknown bindings must remain a blank structure, not fabricated source paths/versions.
    table = spec.split("| 文件/模块或接口 |", 1)[1].split("\n\n", 1)[0]
    assert len([line for line in table.splitlines() if line.startswith("|")]) == 1
    assert "只修改现有帮助文字，无 API 或 UI 变更" in spec
    assert "[x]" not in spec
    assert not (tmp_path / ".super-dev/workflow-state.json").exists()
    # Existing user-authored artifacts still win over regenerated template defaults.
    original = "# 已确认设计\n保留需求 FR-1 与不做清单。\n"
    artifacts["plan.md"].write_text(original, encoding="utf-8")
    generator.scaffold_change_artifacts("help-copy")
    assert artifacts["plan.md"].read_text(encoding="utf-8") == original


def test_builder_cannot_create_spec_before_docs_confirmation(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "unconfirmed-prd.md").write_text("# 未确认需求", encoding="utf-8")
    builder = SpecBuilder(tmp_path, "unconfirmed", "修订帮助文字")
    with pytest.raises(RuntimeError):
        builder.create_change([], {"frontend": "none", "backend": "none"})
    assert not (tmp_path / ".super-dev/changes/unconfirmed").exists()


@pytest.mark.parametrize(
    "phase,query,filename",
    [
        ("drafting", "系统化 调试 debugging", "debugging-playbook.md"),
        ("quality", "测试策略 验证完整性", "testing-strategy-deep-dive.md"),
        ("spec", "风险驱动 测试矩阵", "risk-based-test-matrix.md"),
        ("research", "Agent 评测 基准", "agent-evaluation-benchmark.md"),
        ("spec", "API 契约 版本治理", "api-contract-and-versioning-guide.md"),
        ("research", "AI模型 选型 路由", "ai-model-selection-and-routing-strategy.md"),
        ("frontend", "UI 全生命周期 跨平台", "ui-full-lifecycle-cross-platform-playbook.md"),
        ("delivery", "发布 就绪 门禁", "release-readiness-gate.md"),
    ],
)
def test_knowledge_remains_reachable(phase: str, query: str, filename: str) -> None:
    result = KnowledgePusher(knowledge_dir=ROOT / "knowledge").push(phase, query)
    assert any(Path(item["path"]).name == filename for item in result.files)
