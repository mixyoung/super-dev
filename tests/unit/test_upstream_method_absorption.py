"""Tests for upstream method absorption (REF-003 BMAD Method & REF-005 Matt Pocock Skills).

Verifies that:
1. Design It Twice (ADR dual-solution comparison) is pushed in architecture/docs phases.
2. Domain Glossary (PRD vocabulary specification) is pushed in product/docs phases.
3. Review Perspectives & Depth Levers (multidimensional code review) is pushed in qa/drafting phases.
4. Unrelated UI/frontend queries do not suffer from knowledge cross-contamination.
"""

import shutil
from pathlib import Path

import pytest

from super_dev.orchestrator.knowledge_pusher import PHASE_KNOWLEDGE_MAP, KnowledgePusher

ROOT = Path(__file__).resolve().parents[2]
ADR_DOC = "adr-template-and-examples.md"
PRD_DOC = "product-discovery-and-prd-deep-dive.md"
REVIEW_DOC = "code-review-quality-complete.md"


@pytest.fixture
def pusher(tmp_path: Path) -> KnowledgePusher:
    # Use isolated copy of knowledge directory to avoid polluting the workspace
    knowledge = tmp_path / "knowledge"
    shutil.copytree(ROOT / "knowledge", knowledge)
    return KnowledgePusher(knowledge_dir=knowledge)


def test_design_it_twice_pushed_in_architecture_phase(pusher: KnowledgePusher) -> None:
    result = pusher.push("docs", "系统架构设计 ADR 决策记录 双方案比对 技术选型权衡")
    source = next((item for item in result.files if Path(item["path"]).name == ADR_DOC), None)
    assert source is not None, f"Expected {ADR_DOC} to be matched in docs phase"
    assert len(result.files) <= PHASE_KNOWLEDGE_MAP["docs"]["max_files"]

    injection = result.to_prompt_injection()
    assert ADR_DOC in injection
    # Verify the absorbed Design It Twice method is present
    assert "Design It Twice" in source["excerpt"] or "双方案比对" in source["excerpt"]


def test_domain_glossary_pushed_in_product_phase(pusher: KnowledgePusher) -> None:
    result = pusher.push("docs", "产品需求 PRD 领域词汇表 业务名词 实体边界 禁止别名")
    source = next((item for item in result.files if Path(item["path"]).name == PRD_DOC), None)
    assert source is not None, f"Expected {PRD_DOC} to be matched in docs phase"
    assert len(result.files) <= PHASE_KNOWLEDGE_MAP["docs"]["max_files"]

    injection = result.to_prompt_injection()
    assert PRD_DOC in injection
    # Verify the absorbed Domain Glossary method is present
    assert "Domain Glossary" in source["excerpt"] or "领域统一词汇表" in source["excerpt"]
    assert "禁止别名" in source["excerpt"] or "实体边界" in source["excerpt"]


def test_review_perspectives_pushed_in_qa_phase(pusher: KnowledgePusher) -> None:
    result = pusher.push("qa", "代码评审 code review 范围 发现 交付证据 多视角审查集 严格度档位")
    source = next((item for item in result.files if Path(item["path"]).name == REVIEW_DOC), None)
    assert source is not None, f"Expected {REVIEW_DOC} to be matched in qa phase"
    assert len(result.files) <= PHASE_KNOWLEDGE_MAP["qa"]["max_files"]

    injection = result.to_prompt_injection()
    assert REVIEW_DOC in injection
    # Verify the absorbed Review Perspectives & Depth Levers are present
    assert "多视角审查集" in source["excerpt"] or "Review Perspectives" in source["excerpt"]
    assert "严格度档位" in source["excerpt"] or "Review Depth" in source["excerpt"]


def test_unrelated_frontend_push_does_not_contaminate_with_adr_or_review(
    pusher: KnowledgePusher,
) -> None:
    result = pusher.push("frontend", "开发一个模态弹窗组件，包含点击事件和关闭动画")
    file_names = [Path(item["path"]).name for item in result.files]
    assert ADR_DOC not in file_names
    assert REVIEW_DOC not in file_names

    injection = result.to_prompt_injection()
    assert "Design It Twice" not in injection
    assert "多视角审查集" not in injection


def test_engineering_contracts_embedded_in_generators_and_reviewers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    from super_dev.creators.adr_generator import ADRGenerator
    from super_dev.creators.document_generator import DocumentGenerator
    from super_dev.creators.prompt_generator import AIPromptGenerator
    from super_dev.orchestrator.experts import ExpertRole, get_expert_prompt_section
    from super_dev.reviewers.code_review import CodeReviewGenerator

    # 1. PRD 术语表契约
    doc_gen = DocumentGenerator(
        name="demo",
        description="企业级SaaS工单系统",
        frontend="react",
        backend="python",
    )
    prd = doc_gen.generate_prd()
    assert "禁止使用的别名" in prd
    assert "概念边界与反例" in prd

    # 2. 架构文档与 ADR 生成器包含双方案比对与放弃理由
    arch = doc_gen.generate_architecture()
    assert "双方案比对契约" in arch
    assert "放弃方案 B 的核心原因" in arch

    adr_gen = ADRGenerator(tmp_path)
    adrs = adr_gen.generate_from_architecture({"database": "postgresql", "backend": "fastapi"})
    assert adrs
    adr_md = adrs[0].to_markdown()
    assert "放弃其他备选方案的原因" in adr_md
    assert "适用边界" in adr_md

    # 3. 代码审查指南契约包含四视角、三档严格度与反作弊红线
    review_md = CodeReviewGenerator(
        project_dir=tmp_path,
        name="demo",
        tech_stack={"platform": "web", "frontend": "react", "backend": "python"},
    ).generate()
    assert "多视角审查集与审查严格度档位" in review_md
    assert "架构一致性视角" in review_md
    assert "极简速审" in review_md
    assert "测试完整性反作弊红线" in review_md

    # 4. AI 提示词与专家画像契约对齐
    (tmp_path / "super-dev.yaml").write_text(
        "name: demo\ndescription: 构建SaaS平台\nplatform: web\nfrontend: react\nbackend: python\n",
        encoding="utf-8",
    )
    prompt = AIPromptGenerator(project_dir=tmp_path, name="demo").generate()
    assert "测试完整性反作弊红线" in prompt
    assert "多视角与按风险分级自审" in prompt
    assert "设计双方案与词表契约" in prompt

    assert "双方案比对" in get_expert_prompt_section(ExpertRole.ARCHITECT)
    assert "禁止别名" in get_expert_prompt_section(ExpertRole.PM)
    assert "极简速审" in get_expert_prompt_section(ExpertRole.CODE)
    assert "注释断言" in get_expert_prompt_section(ExpertRole.QA)
