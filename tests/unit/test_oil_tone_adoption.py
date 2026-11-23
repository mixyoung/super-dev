"""Check conditional writing guidance through the existing knowledge push, not prose quality."""

import shutil
from pathlib import Path

import pytest

from super_dev.orchestrator.knowledge_pusher import PHASE_KNOWLEDGE_MAP, KnowledgePusher

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = "product-discovery-and-prd-deep-dive.md"
HINT = "涉及文档表达或产品文案时"


@pytest.fixture
def pusher(tmp_path: Path) -> KnowledgePusher:
    # Retain real candidate competition without creating statistics in the working tree.
    knowledge = tmp_path / "knowledge"
    shutil.copytree(ROOT / "knowledge", knowledge)
    return KnowledgePusher(knowledge_dir=knowledge)


@pytest.mark.parametrize("phase", ["research", "docs", "drafting"])
def test_writing_applicability_survives_real_push_and_excerpt(
    pusher: KnowledgePusher, phase: str
) -> None:
    result = pusher.push(phase, "文档表达 产品文案 读者 前置信息 事实 状态")
    source = next(item for item in result.files if Path(item["path"]).name == PRODUCT)
    assert len(result.files) <= PHASE_KNOWLEDGE_MAP[phase]["max_files"]
    # A filename hit alone does not establish that applicability reaches the host.
    assert HINT in source["excerpt"]
    assert "不机械删改“的/了”" in source["excerpt"]
    injection = result.to_prompt_injection()
    assert HINT in injection
    assert PRODUCT in injection
    assert "使用前读取下方来源原文" in injection
    # Conditional prose advice must not become a new unconditional checkbox gate.
    assert not any(HINT in item or "的/了" in item for item in result.constraints)


def test_unrelated_backend_push_does_not_add_writing_guidance(pusher: KnowledgePusher) -> None:
    result = pusher.push("backend", "修复数据库连接池超时，保留现有接口合同")
    assert all(Path(item["path"]).name != PRODUCT for item in result.files)
    assert HINT not in result.to_prompt_injection()
