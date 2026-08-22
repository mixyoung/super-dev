from pathlib import Path

from super_dev.integrations.manager import IntegrationManager
from super_dev.skills.skill_template import SkillTemplate

ROOT = Path(__file__).resolve().parents[2]
CODEX_SKILL = ROOT / "plugins" / "super-dev-codex" / "skills" / "super-dev" / "SKILL.md"
CLAUDE_SKILL = ROOT / "plugins" / "super-dev-claude" / "skills" / "super-dev" / "SKILL.md"


def _skill_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_host_skills_adapt_language_and_environment() -> None:
    for host in ("codex", "claude-code"):
        skill = SkillTemplate.for_builtin("super-dev", host).render(host)
        assert "## 沟通与环境适配（强制）" in skill
        assert "`TASK_ID`" in skill
        assert "Windows环境不得默认给出只能在Bash执行的命令" in skill


def test_host_skills_keep_one_lifecycle_and_one_placement_owner() -> None:
    for host in ("codex", "claude-code"):
        skill = SkillTemplate.for_builtin("super-dev", host).render(host)
        assert "`PLACEMENT_OWNER`" in skill
        assert "`MAY_SPAWN_SUBWORKERS`" in skill
        assert "Orca" in skill
        assert "OMP" in skill
        assert "工作区" in skill


def test_tracked_skill_surfaces_match_the_canonical_generator() -> None:
    expected_codex = SkillTemplate.for_builtin("super-dev", "codex").render("codex")
    expected_claude = SkillTemplate.for_builtin("super-dev", "claude-code").render(
        "claude-code"
    )

    assert _skill_text(ROOT / ".agents" / "skills" / "super-dev" / "SKILL.md") == expected_codex
    assert _skill_text(CODEX_SKILL) == expected_codex
    assert _skill_text(ROOT / ".claude" / "skills" / "super-dev" / "SKILL.md") == expected_claude
    assert _skill_text(CLAUDE_SKILL) == expected_claude

    manager = IntegrationManager(ROOT)
    assert manager._build_codex_plugin_skill_content(skill_name="super-dev") == expected_codex
