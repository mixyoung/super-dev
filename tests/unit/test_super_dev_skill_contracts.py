from pathlib import Path

from super_dev.integrations.manager import IntegrationManager
from super_dev.skills.skill_template import SkillTemplate

ROOT = Path(__file__).resolve().parents[2]
CODEX_SKILL = ROOT / "plugins" / "super-dev-codex" / "skills" / "super-dev" / "SKILL.md"
CLAUDE_SKILL = ROOT / "plugins" / "super-dev-claude" / "skills" / "super-dev" / "SKILL.md"
MAINLAND_CHINESE_CONTRACT = """## 面向中国大陆用户的语言与术语契约（强制）
- 面向中国大陆用户的用户界面、聊天、确认问题、错误提示和报告，优先使用自然、直接、符合中国大陆语言习惯的中文。
- 优先使用中国大陆日常开发和产品沟通中的常见说法；避免生僻词、直译腔、翻译软件式句子和不必要的中英混杂。
- 技术概念第一次出现时，使用“中文名称（英文代码名）”；后续优先只用中文名称，仅在精确核对时再次显示英文代码名。
- 状态统一显示为通过（`PASS`）、失败（`FAIL`）、受阻（`BLOCKED`）；不得面向用户只显示裸英文状态。
- `candidate` 面向用户统一称“当前代码版本”，只在证据详情中显示字段（`candidate_digest`）。
- 命令、文件名和程序字段保留精确英文原文并使用代码格式；解释仍先用中文。
- 内部日志、JSON 和 API 字段可以保留英文，但不得直接照搬成用户文案。"""


def _skill_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_host_skills_adapt_language_and_environment() -> None:
    for host in ("codex", "claude-code"):
        skill = SkillTemplate.for_builtin("super-dev", host).render(host)
        assert "## 沟通与环境适配（强制）" in skill
        assert "自然、直接、符合中国大陆语言习惯的中文" in skill
        assert "避免生僻词、直译腔、翻译软件式句子和不必要的中英混杂" in skill
        assert "中文名称（英文代码名）" in skill
        assert "后续优先只用中文名称" in skill
        assert "通过（`PASS`）、失败（`FAIL`）、受阻（`BLOCKED`）" in skill
        assert "当前代码版本" in skill
        assert "`candidate_digest`" in skill
        assert "命令、文件名和程序字段保留精确英文原文并使用代码格式" in skill
        assert "Windows环境不得默认给出只能在Bash执行的命令" in skill


def test_claude_harnesses_share_mainland_chinese_contract() -> None:
    for path in (ROOT / "CLAUDE.md", ROOT / ".claude" / "CLAUDE.md"):
        assert MAINLAND_CHINESE_CONTRACT in _skill_text(path)


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
    expected_claude = SkillTemplate.for_builtin("super-dev", "claude-code").render("claude-code")

    assert _skill_text(ROOT / ".agents" / "skills" / "super-dev" / "SKILL.md") == expected_codex
    assert _skill_text(CODEX_SKILL) == expected_codex
    assert _skill_text(ROOT / ".claude" / "skills" / "super-dev" / "SKILL.md") == expected_claude
    assert _skill_text(CLAUDE_SKILL) == expected_claude

    manager = IntegrationManager(ROOT)
    assert manager._build_codex_plugin_skill_content(skill_name="super-dev") == expected_codex
