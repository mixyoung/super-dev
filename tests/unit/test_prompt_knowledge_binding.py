"""Exercise expert knowledge through the real final prompt and real stage gates."""

import hashlib
import re
from pathlib import Path

import pytest
import yaml

from super_dev.creators.prompt_generator import AIPromptGenerator
from super_dev.review_state import save_workflow_state
from super_dev.specs import SpecGenerator
from super_dev.workflow_guard import record_stage_progress, save_bound_docs_confirmation

CODE_FILES = (
    "development/04-antipatterns/code-smell-antipatterns.md",
    "testing/01-standards/testing-strategy-complete.md",
    "development/02-playbooks/debugging-playbook.md",
)
DESIGN_FILE = "design/01-standards/ui-design-system-complete.md"


def _project(
    root: Path, *, frontend: str = "none", description: str = "维护现有离线工具"
) -> AIPromptGenerator:
    root.mkdir(parents=True, exist_ok=True)
    (root / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "chosen",
                "description": description,
                "platform": "web" if frontend != "none" else "cli",
                "frontend": frontend,
                "backend": "python",
                "database": "none",
                "quality_gate": 90,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    manager = SpecGenerator(root)
    manager.create_change("chosen", "当前任务", description)
    manager.scaffold_change_artifacts("chosen")
    save_workflow_state(root, {"active_change_id": "chosen", "status": "running"})
    output = root / "output"
    output.mkdir(exist_ok=True)
    for suffix in ("research", "prd", "architecture", "uiux"):
        (output / f"chosen-{suffix}.md").write_text(
            f"# {suffix}\n\n{description}\n", encoding="utf-8"
        )
    record_stage_progress(root, stage="research", status="completed", actor="fixture")
    record_stage_progress(root, stage="docs", status="completed", actor="fixture")
    save_bound_docs_confirmation(root, {"status": "confirmed", "actor": "fixture"})
    record_stage_progress(root, stage="spec", status="completed", actor="fixture")
    generator = AIPromptGenerator(root, "chosen")
    assert generator._current_phase() == ("frontend" if frontend != "none" else "backend")
    return generator


def _knowledge(root: Path, relative: str) -> Path:
    path = root / "knowledge" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Task knowledge\n\nRead original applicability conditions.\n", encoding="utf-8"
    )
    return path.resolve()


def _section(prompt: str, expert: str) -> str:
    match = re.search(rf"^### .+（{expert}）视角\n(.*?)(?=^### |\Z)", prompt, re.M | re.S)
    assert match, f"{expert} must actually be active in the emitted prompt"
    return match.group(1)


def _references(section: str) -> list[str]:
    return [line for line in section.splitlines() if line.startswith("- `")]


def _hashes(root: Path) -> dict[str, str]:
    # Generation may update its existing SQLite statistics cache, not task inputs.
    statistics_cache = {
        ".super-dev/knowledge-stats.db",
        ".super-dev/knowledge-stats.db-shm",
        ".super-dev/knowledge-stats.db-wal",
    }
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file() and path.relative_to(root).as_posix() not in statistics_cache
    }


def test_final_code_prompt_keeps_debugging_reference_with_many_generic_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "target"
    generator = _project(root, description="只诊断后端测试无法收集，不修改代码")
    paths = [_knowledge(root, relative) for relative in CODE_FILES]
    decoys = [
        _knowledge(root, f"development/01-standards/00-general-{index}.md") for index in range(5)
    ]
    unrelated = tmp_path / "unrelated"
    _knowledge(unrelated, CODE_FILES[2])
    monkeypatch.chdir(unrelated)
    before = _hashes(root)
    prompt = generator.generate()
    code = _section(prompt, "CODE")
    references = _references(code)
    assert len(references) == 3
    assert all(str(path) in references[index] for index, path in enumerate(paths))
    assert not any(str(path) in code for path in decoys)
    assert str(unrelated.resolve()) not in code
    assert "仅在排错或验证失败时" in references[2]
    assert "其他任务不新增必读要求" in references[2]
    assert _hashes(root) == before


def test_domain_playbook_scan_reaches_the_real_final_prompt(tmp_path: Path) -> None:
    root = tmp_path / "target"
    generator = _project(root)
    for relative in CODE_FILES[:2]:
        _knowledge(root, relative)
    playbook = _knowledge(root, "development/02-playbooks/diagnosis-reference.md")
    code = _section(generator.generate(), "CODE")
    assert str(playbook) in _references(code)[2]


def test_final_ui_and_ux_prompt_prioritizes_the_correct_explicit_design_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "target"
    generator = _project(root, frontend="react", description="既有单任务表单，无使用分析需求")
    design = _knowledge(root, DESIGN_FILE)
    for index in range(5):
        _knowledge(root, f"design/01-standards/00-generic-{index}.md")
    prompt = generator.generate()
    for expert in ("UI", "UX"):
        references = _references(_section(prompt, expert))
        assert len(references) == 3
        assert str(design) in references[0]
    assert "design/01-standards/design-system-complete.md" not in prompt


@pytest.mark.parametrize("frontend", ["none", "react"])
def test_missing_knowledge_keeps_self_contained_diagnostic_scope(
    tmp_path: Path, frontend: str
) -> None:
    root = tmp_path / "target"
    generator = _project(root, frontend=frontend)
    before = _hashes(root)
    code = _section(generator.generate(), "CODE")
    assert "排错或验证失败时" in code
    assert "仅诊断请求不修改代码" in code
    assert "其他任务不新增必读要求" in code
    assert "**知识要求**" not in code
    assert _hashes(root) == before


@pytest.mark.parametrize(
    "description",
    ["无数据库的离线小工具，仅改帮助文字", "明确容量目标 100 RPS、p95 不高于 200ms"],
)
def test_final_architect_guidance_keeps_capacity_and_adr_conditions(
    tmp_path: Path, description: str
) -> None:
    root = tmp_path / "target"
    generator = _project(root, description=description)
    prompt = generator.generate()
    architect = _section(prompt, "ARCHITECT")
    assert "有容量或扩展需求时" in architect
    assert "容量估算与目标验证" in architect
    assert "已确认的架构、功能、可靠性与容量要求" in architect
    assert "瓶颈分析" in architect
    assert "不预设必须引入" in architect
    assert "重要且难逆" in architect
    for old in (
        "技术选型是否有 ADR",
        "架构决策记录（ADR）已沉淀",
        "关键链路容量估算已完成",
        "缓存/队列/分片策略已明确",
    ):
        assert old not in prompt


def test_confirmed_reliable_delivery_is_not_denied_without_a_performance_bottleneck(
    tmp_path: Path,
) -> None:
    description = (
        "本轮已确认使用持久化队列保证可靠投递与断网重试；"
        "当前没有性能瓶颈，不新增缓存、分片或其他无关基础设施。"
    )
    generator = _project(tmp_path / "target", description=description)
    prompt = generator.generate()
    architect = _section(prompt, "ARCHITECT")

    assert description in prompt  # Preserve the confirmed requirement through the real entry.
    assert "已确认的架构、功能、可靠性与容量要求" in architect
    assert "瓶颈分析决定是否采用" in architect
    assert "不预设必须引入" in architect
    assert "仅在已验证的瓶颈需要时" not in prompt
    assert "不预设必须引入持久化队列" not in prompt


@pytest.mark.parametrize("description", ["没有量化使用分析需求", "已明确要求量化使用分析"])
def test_final_ux_guidance_conditions_analytics_without_losing_feedback(
    tmp_path: Path, description: str
) -> None:
    root = tmp_path / "target"
    generator = _project(root, frontend="react", description=description)
    prompt = generator.generate()
    ux = _section(prompt, "UX")
    assert "有量化使用分析需求时" in ux
    assert "转化漏斗" in ux
    assert "埋点" in ux
    assert "交互反馈（成功/失败/加载）已覆盖" in ux
    assert "- [ ] 转化漏斗路径无断链" not in prompt
    assert "- [ ] 可观测埋点已规划" not in prompt


def test_ux_topic_conditions_match_the_emitted_scenario_guidance() -> None:
    topic = Path(__file__).resolve().parents[2] / "knowledge/design/ux-system-deep-dive.md"
    text = topic.read_text(encoding="utf-8")
    for old in (
        "每个页面至少有一个主任务与一个次任务",
        "表单必须具备即时校验与提交兜底校验",
        "高风险动作必须二次确认并提供撤销方案",
    ):
        assert old not in text
    assert "确有独立次任务" in text
    assert "按场景选择" in text
    assert "提交兜底校验" in text
    assert "不可逆" in text
    assert "已确认的校验和安全要求不得降低" in text
