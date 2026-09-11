"""
专家建议服务测试
"""

from pathlib import Path

from super_dev.experts import (
    has_expert,
    has_expert_team,
    list_expert_advice_history,
    list_expert_teams,
    list_experts,
    read_expert_advice,
    render_expert_advice_markdown,
    render_team_advice_markdown,
    save_expert_advice,
    save_team_advice,
)


def test_default_qa_is_not_replaced_by_verification_variant(tmp_path):
    from super_dev.experts.loader import load_expert_definitions, load_expert_profiles
    from super_dev.orchestrator.experts import ExpertRole

    definitions = load_expert_definitions(tmp_path)
    profiles = load_expert_profiles(tmp_path)

    assert "VERIFICATION" in definitions
    assert profiles[ExpertRole.QA].title == definitions["QA"].title
    assert profiles[ExpertRole.QA].goal == definitions["QA"].goal


def test_project_expert_definition_reaches_generated_prompt(tmp_path):
    from super_dev.creators.prompt_generator import AIPromptGenerator

    expert_dir = tmp_path / ".super-dev" / "experts"
    expert_dir.mkdir(parents=True)
    (expert_dir / "PM.md").write_text(
        "---\nname: PM\nrole: PM\ntitle: 预约产品顾问\n"
        "goal: 解释候补预约的业务边界\n"
        "thinking_framework:\n  - 区分已预约和候补队列\n"
        "handoff_checklist:\n  - 候补顺序与取消规则已有依据\n---\n",
        encoding="utf-8",
    )

    prompt = AIPromptGenerator(tmp_path, "booking")._build_expert_profiles_section()

    assert "预约产品顾问" in prompt
    assert "区分已预约和候补队列" in prompt
    assert "候补顺序与取消规则已有依据" in prompt


def test_builtin_profiles_and_fallbacks_share_the_same_guidance():
    from dataclasses import asdict

    from super_dev.experts.loader import definition_to_profile, parse_expert_from_markdown
    from super_dev.orchestrator.experts import EXPERT_PROFILES, ExpertRole

    builtin = Path(__file__).resolve().parents[2] / "super_dev" / "experts" / "builtin"
    for role in ExpertRole:
        path = builtin / f"{role.value}.md"
        if path.exists():
            definition = parse_expert_from_markdown(path)
            assert definition is not None
            assert asdict(EXPERT_PROFILES[role]) == asdict(definition_to_profile(definition))


def test_project_role_override_takes_priority_over_global_alias(tmp_path):
    from super_dev.experts.loader import load_expert_profiles
    from super_dev.orchestrator.experts import ExpertRole

    user_dir = Path.home() / ".super-dev" / "experts"
    project_dir = tmp_path / ".super-dev" / "experts"
    user_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)
    (user_dir / "Z.md").write_text(
        "---\nname: CUSTOM\nrole: QA\ntitle: 全局验证方法\ngoal: 全局目标\n---\n",
        encoding="utf-8",
    )
    (project_dir / "QA.md").write_text(
        "---\nname: QA\nrole: QA\ntitle: 项目验证方法\ngoal: 项目目标\n---\n",
        encoding="utf-8",
    )

    assert load_expert_profiles(tmp_path)[ExpertRole.QA].goal == "项目目标"


class TestExpertService:
    def test_list_experts_contains_rca(self):
        experts = list_experts()
        ids = {item["id"] for item in experts}
        assert "PRODUCT" in ids
        assert "PM" in ids
        assert "RCA" in ids

    def test_list_expert_teams_contains_product_audit(self):
        teams = list_expert_teams()
        ids = {item["id"] for item in teams}
        assert "PRODUCT_AUDIT" in ids

    def test_render_advice_markdown(self):
        content = render_expert_advice_markdown("PM", "规划认证模块")
        assert "# PM 专家建议" in content
        assert "建议清单" in content
        assert "规划认证模块" in content

    def test_save_expert_advice(self, temp_project_dir: Path):
        path, content = save_expert_advice(temp_project_dir, "QA", "补测试策略")
        assert path.exists()
        assert "QA 专家建议" in content
        assert "补测试策略" in content
        assert path.read_text(encoding="utf-8") == content

    def test_has_expert(self):
        assert has_expert("PM") is True
        assert has_expert("UNKNOWN") is False

    def test_has_expert_team(self):
        assert has_expert_team("PRODUCT_AUDIT") is True
        assert has_expert_team("UNKNOWN") is False

    def test_render_team_advice_markdown(self):
        content = render_team_advice_markdown("PRODUCT_AUDIT", "做一次全项目闭环审查")
        assert "# PRODUCT_AUDIT 团队审查报告" in content
        assert "团队组成" in content
        assert "做一次全项目闭环审查" in content

    def test_save_team_advice(self, temp_project_dir: Path):
        path, content = save_team_advice(temp_project_dir, "PRODUCT_AUDIT", "做一次全项目闭环审查")
        assert path.exists()
        assert "PRODUCT_AUDIT 团队审查报告" in content
        assert path.read_text(encoding="utf-8") == content

    def test_history_and_read(self, temp_project_dir: Path):
        path, _ = save_expert_advice(temp_project_dir, "PM", "测试")
        history = list_expert_advice_history(temp_project_dir, limit=10)
        assert any(item["file_name"] == path.name for item in history)

        file_path, content = read_expert_advice(temp_project_dir, path.name)
        assert file_path.name == path.name
        assert "PM 专家建议" in content

    def test_read_expert_advice_rejects_invalid_name(self, temp_project_dir: Path):
        try:
            read_expert_advice(temp_project_dir, "../bad.md")
            assert False, "should raise ValueError"
        except ValueError:
            assert True
