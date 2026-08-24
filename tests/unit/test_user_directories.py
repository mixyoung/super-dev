from pathlib import Path

from super_dev.integrations import IntegrationManager
from super_dev.skills import SkillManager
from super_dev.user_directories import UserDirectoryContext


def test_context_expands_current_user_without_using_process_home(tmp_path: Path):
    home = tmp_path / "isolated-home"
    context = UserDirectoryContext.from_home(home)

    assert context.home == home.resolve()
    assert context.expanduser("~") == home.resolve()
    assert context.expanduser("~/.agents/skills") == home.resolve() / ".agents" / "skills"
    assert context.codex_home == home.resolve() / ".codex"
    assert context.xdg_config_home == home.resolve() / ".config"


def test_context_supports_codex_home_outside_user_home(tmp_path: Path):
    home = tmp_path / "isolated-home"
    codex_home = tmp_path / "external" / "codex"
    context = UserDirectoryContext.from_home(home, codex_home=codex_home)

    assert context.codex_home == codex_home
    assert context.codex_home.parent != context.home


def test_context_builds_consistent_windows_environment(tmp_path: Path):
    context = UserDirectoryContext.from_home(tmp_path / "isolated-home")
    env = context.environment({"KEEP": "yes"})

    assert env["KEEP"] == "yes"
    assert env["HOME"] == str(context.home)
    assert env["USERPROFILE"] == str(context.home)
    assert env["CODEX_HOME"] == str(context.codex_home)
    assert env["XDG_CONFIG_HOME"] == str(context.xdg_config_home)
    assert env["XDG_DATA_HOME"] == str(context.home / ".local" / "share")
    assert env["XDG_CACHE_HOME"] == str(context.home / ".cache")
    assert env["APPDATA"] == str(context.home / "AppData" / "Roaming")
    assert env["LOCALAPPDATA"] == str(context.home / "AppData" / "Local")
    if context.home.drive:
        assert env["HOMEDRIVE"] + env["HOMEPATH"] == str(context.home)


def test_skill_manager_uses_injected_user_directories(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    context = UserDirectoryContext.from_home(
        tmp_path / "isolated-home",
        codex_home=tmp_path / "external-codex",
    )
    manager = SkillManager(project, user_directories=context)

    assert manager._target_dir("claude-code") == context.home / ".claude" / "skills"
    assert manager._target_dir("codex-cli") == context.home / ".agents" / "skills"
    assert manager._compatibility_target_dirs("codex-cli") == []
    assert manager._compatibility_target_dirs("codex") == [context.codex_home / "skills"]


def test_integration_manager_uses_injected_user_directories(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    context = UserDirectoryContext.from_home(
        tmp_path / "isolated-home",
        codex_home=tmp_path / "external-codex",
    )
    manager = IntegrationManager(project, user_directories=context)

    assert manager.resolve_global_protocol_path("claude-code") == (
        context.home / ".claude" / "CLAUDE.md"
    )
    assert manager.resolve_global_protocol_path("codex-cli") == (
        context.codex_home / "AGENTS.md"
    )
    assert manager.resolve_compatibility_protocol_path("trae") == (
        context.home / ".trae" / "rules.md"
    )

    codex_paths = manager.expected_skill_paths("codex-cli")
    assert context.home / ".agents" / "skills" / "super-dev" / "SKILL.md" in codex_paths

    surfaces = manager.collect_managed_surface_paths("codex-cli")
    assert any(path == context.codex_home / "AGENTS.md" for path in surfaces.values())
    for key, path in surfaces.items():
        if key.startswith(("project:", "project-slash:")):
            continue
        assert path.is_relative_to(context.home) or path.is_relative_to(context.codex_home)
