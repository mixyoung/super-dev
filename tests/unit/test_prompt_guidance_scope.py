"""The emitted guidance must keep task identity, gates and scope, not just headings."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from super_dev.creators.prompt_generator import AIPromptGenerator
from super_dev.integrations.manager import IntegrationManager
from super_dev.skills.skill_template import SkillTemplate
from super_dev.specs.generator import SpecGenerator
from super_dev.specs.models import Task, TaskStatus
from super_dev.workflow_guard import save_bound_docs_confirmation, save_bound_preview_confirmation


def project(tmp_path: Path, frontend: str = "none") -> AIPromptGenerator:
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "demo",
                "description": "维护已有功能",
                "frontend": frontend,
                "backend": "python",
            }
        ),
        encoding="utf-8",
    )
    return AIPromptGenerator(tmp_path, "demo")


def bind_change(tmp_path: Path, change_id: str = "chosen") -> None:
    manager = SpecGenerator(tmp_path)
    manager.create_change(change_id, "当前任务", "必须保留的当前需求")
    (tmp_path / ".super-dev/workflow-state.json").write_text(
        json.dumps({"active_change_id": change_id}), encoding="utf-8"
    )
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    for suffix in ("research", "prd", "architecture", "uiux"):
        (output / f"{change_id}-{suffix}.md").write_text(f"# {suffix}\n当前需求", encoding="utf-8")


def digest_files(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_latest_change_is_not_the_active_change(tmp_path):
    generator = project(tmp_path)
    bind_change(tmp_path)
    SpecGenerator(tmp_path).create_change("newer", "其他任务", "不应混入的需求")
    content, change_id = generator._read_change_spec()
    assert change_id == "chosen"
    assert "newer" not in content
    assert "当前任务" in content
    assert "其他任务" not in content


def test_unbound_single_change_is_not_selected(tmp_path):
    generator = project(tmp_path)
    SpecGenerator(tmp_path).create_change("only-one", "未指定", "不可猜测")
    before = digest_files(tmp_path)
    _, change_id = generator._read_change_spec()
    assert not change_id
    assert generator.get_pending_tasks() == []
    assert "请开始实现" not in generator.generate_task_specific_prompt("1.1")
    assert digest_files(tmp_path) == before


def test_resume_keeps_completed_tasks_and_uses_active_artifact_paths(tmp_path):
    generator = project(tmp_path)
    bind_change(tmp_path)
    manager = SpecGenerator(tmp_path).change_manager
    change = manager.load_change("chosen")
    assert change is not None
    change.tasks = [Task("1.1", "已完成", status=TaskStatus.COMPLETED), Task("1.2", "当前待办")]
    manager.save_change(change)
    SpecGenerator(tmp_path).create_change("newer", "无关任务", "不能混入")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed"})
    before = digest_files(tmp_path)
    assert [task["id"] for task in generator.get_pending_tasks()] == ["1.2"]
    assert "已完成，不重复实施" in generator.generate_task_specific_prompt("1.1")
    prompt = generator.generate_task_specific_prompt("1.2")
    assert "当前待办" in prompt and "output/chosen-prd.md" in prompt
    assert "output/demo-prd.md" not in prompt
    assert "首个未完成任务 1.2" in generator.generate()
    assert digest_files(tmp_path) == before
    change.tasks[1].status = TaskStatus.COMPLETED
    manager.save_change(change)
    assert "没有待完成任务" in generator.generate()


def test_stale_docs_confirmation_blocks_implementation_without_writing_state(tmp_path):
    generator = project(tmp_path)
    bind_change(tmp_path)
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed"})
    (tmp_path / "output/chosen-prd.md").write_text("# changed requirements", encoding="utf-8")
    before = digest_files(tmp_path)
    assert generator._current_phase() == "docs_confirm"
    prompt = generator.generate()
    assert "从任务 1.1 开始" not in prompt
    assert "当前阶段是 `research`" not in prompt
    assert "绑定" in prompt and "确认" in prompt
    assert digest_files(tmp_path) == before


def test_valid_confirmation_is_not_reopened_for_a_cli_task(tmp_path):
    generator = project(tmp_path)
    bind_change(tmp_path)
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed"})
    before = digest_files(tmp_path)
    phase = generator._current_phase()
    assert phase not in {"research", "docs", "docs_confirm", "frontend", "preview_confirm"}
    assert digest_files(tmp_path) == before


def test_stale_preview_cannot_start_backend(tmp_path):
    generator = project(tmp_path, "react")
    bind_change(tmp_path)
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed"})
    runtime = tmp_path / "output/chosen-frontend-runtime.json"
    runtime.write_text('{"passed": true}', encoding="utf-8")
    save_bound_preview_confirmation(tmp_path, {"status": "confirmed"})
    runtime.write_text('{"passed": true, "updated": true}', encoding="utf-8")
    assert generator._current_phase() in {"frontend", "preview_confirm"}
    assert not generator._workflow_context()["preview_gate"]["confirmed"]
    assert "请开始实现" not in generator.generate_task_specific_prompt("1.1")


def test_partial_documents_do_not_request_confirmation(tmp_path):
    generator = project(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    (output / "demo-prd.md").write_text("# draft", encoding="utf-8")
    assert generator._current_phase() in {"research", "docs"}


def test_new_project_can_get_guidance_without_task_or_confirmation(tmp_path):
    generator = project(tmp_path)
    before = digest_files(tmp_path)
    prompt = generator.generate()
    assert generator._current_phase() == "research"
    assert "研究" in prompt and "文档" in prompt
    assert "unknown-change/tasks.md" not in prompt
    assert "从任务 1.1 开始" not in prompt
    assert digest_files(tmp_path) == before


def test_cli_prompt_does_not_create_ui_or_new_quality_obligations(tmp_path):
    generator = project(tmp_path)
    prompt = generator.generate()
    for unwanted in (
        "前端必须先达到",
        "必须重新执行前端运行验证",
        "覆盖率 > 80%",
        "未接入则删除",
        "### 商业级 UI/UX 强制规则",
        "### 本项目 UI 实现基线",
        "JWT Token 认证",
        "vite.config.js",
        "UI 达到商业级完成度",
    ):
        assert unwanted not in prompt
    assert "默认质量" in prompt and "公共" in prompt


@pytest.mark.parametrize("frontend", ["nextjs", "nuxt", "vue"])
def test_framework_name_does_not_authorize_migration(tmp_path, frontend):
    generator = project(tmp_path, frontend)
    rules = generator._section_tech_stack_rules(frontend=frontend)
    for unwanted in (
        "Pages Router 已废弃",
        "确认使用 App Router（不是 Pages Router）",
        "禁止把 API 写成独立 Express",
        "禁止使用 Options API",
        "确认使用 Nuxt 3",
    ):
        assert unwanted not in rules
    assert "已有架构" in rules and "本次" in rules


@pytest.mark.parametrize("host", ["codex", "claude-code"])
def test_standard_skills_keep_user_selected_knowledge_authority(host):
    skill = SkillTemplate.for_builtin("super-dev", host).render(host)
    assert "无显式适用条件" in skill and "默认强制" in skill
    assert "为何适用" in skill
    assert "不自动成为新需求" not in skill
    assert "暂停等待用户预览确认" in skill


def test_host_rules_do_not_treat_readonly_requests_as_stage_authorization(tmp_path):
    manager = IntegrationManager(tmp_path)
    for rules in (
        manager._claude_rules(),
        manager._generic_ide_rules("qoder"),
        manager._generic_cli_rules("opencode"),
    ):
        assert "read-only" in rules
        assert "no emoji characters in the source" not in rules
        assert (
            "first natural-language requirement in a new host session must also default"
            not in rules
        )


def test_extracted_knowledge_keeps_conditions_and_uses_target_project(tmp_path, monkeypatch):
    generator = project(tmp_path)
    from super_dev.experts.toolkit import get_toolkit

    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    guide = knowledge / "conditional.md"
    guide.write_text(
        "# 指南\n仅当确有数据库时适用。\n## Agent Checklist\n- [ ] 建立索引\n", encoding="utf-8"
    )
    toolkit = get_toolkit("DBA")
    monkeypatch.setattr(
        toolkit.knowledge, "resolve", lambda root: [str(guide)] if root == knowledge else []
    )
    monkeypatch.setattr(generator, "_get_active_experts_for_phase", lambda: {"DBA": toolkit})
    monkeypatch.setattr(generator, "_current_phase", lambda: "spec")
    monkeypatch.chdir(tmp_path.parent)
    section = generator._build_expert_section()
    assert "仅当确有数据库时适用" in section or str(guide) in section
