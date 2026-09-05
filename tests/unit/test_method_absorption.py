"""Exercise method guidance through existing document, knowledge and install paths."""

from pathlib import Path

import pytest

from super_dev.creators.document_generator import DocumentGenerator
from super_dev.orchestrator.knowledge_pusher import KnowledgePusher
from super_dev.skills import SkillManager
from super_dev.skills.skill_template import SkillTemplate
from super_dev.user_directories import UserDirectoryContext

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "description,domain",
    [("离线图片校验学习工具，无账户", "general"), ("订单部分取消与退款", "ecommerce")],
)
def test_prd_does_not_invent_authentication_glossary(description: str, domain: str) -> None:
    prd = DocumentGenerator(name="example", description=description, domain=domain).generate_prd()
    glossary = prd.split("### A. 术语表", 1)[1].split("### B. 参考文档", 1)[0]
    # With no supplied domain definitions, the renderer must leave rows unpopulated.
    # The previous renderer inserted JWT/Session/RBAC as facts for every project.
    rows = [line for line in glossary.splitlines() if line.startswith("|")]
    assert len(rows) == 2
    assert len(rows[0].split("|")) == 6


def test_bugfix_prd_preserves_repair_scope() -> None:
    prd = DocumentGenerator(
        name="repair", description="修复已确认的日期解析错误", request_mode="bugfix"
    ).generate_prd()
    market = prd.split("### 1.4 市场与对标结论", 1)[1].split("### 1.5", 1)[0]
    assert "同类产品研究" not in market
    assert "不重新开展立项论证" in market


@pytest.mark.parametrize("phase", ["research", "docs"])
def test_existing_knowledge_push_retrieves_method_guidance(phase: str) -> None:
    result = KnowledgePusher(knowledge_dir=ROOT / "knowledge").push(
        phase, "产品发现 价值判断 需求审查 业务术语"
    )
    expected = ROOT / "knowledge/product/product-discovery-and-prd-deep-dive.md"
    assert any(Path(item["path"]).resolve() == expected.resolve() for item in result.files)
    assert len(result.files) <= (5 if phase == "research" else 8)


@pytest.mark.parametrize("host", ["codex-cli", "claude-code"])
def test_builtin_install_uses_current_template_in_isolated_home(tmp_path: Path, host: str) -> None:
    project = tmp_path / "project"
    project.mkdir()
    context = UserDirectoryContext.from_home(tmp_path / "home")
    result = SkillManager(project, user_directories=context).install("super-dev", host)
    assert result.path.is_dir()
    assert result.path.is_relative_to(context.home)
    base = context.home / (".agents" if host == "codex-cli" else ".claude") / "skills"
    installed = (base / "super-dev" / "SKILL.md").read_text(encoding="utf-8")
    assert installed == SkillTemplate.for_builtin("super-dev", host).render(host)
    assert not (project / ".super-dev/workflow-state.json").exists()
