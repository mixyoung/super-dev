import ast
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from super_dev.catalogs import HOST_TOOL_ALIASES, HOST_TOOL_CATEGORY_MAP, normalize_host_tool_id
from super_dev.cli import SuperDevCLI
from super_dev.host_registry import HostInstallMode, get_host_definition
from super_dev.integrations import IntegrationManager
from super_dev.skills import SkillManager
from super_dev.skills.skill_template import SkillTemplate
from super_dev.update_hosts import refresh_hosts, snapshot_hosts
from super_dev.user_directories import UserDirectoryContext

HOST = "deepseek-harness"
BEGIN = "<!-- TEST BEGIN -->"
END = "<!-- TEST END -->"

REWORK02_LEGACY_HOSTS = (
    "codex",
    "codex-cli",
    "claude-code",
    "opencode",
    "qoder",
    "qoder-cli",
    "cursor",
    "cursor-cli",
    "kiro",
    "kiro-cli",
    "droid-cli",
    "copilot-cli",
    "kimi-code",
    "trae-solo",
)


def _rework02_baseline_producers():
    root = Path(__file__).resolve().parents[2]
    commit = "26b0cb6c98e723b8c12c4d721785a9cb91d6f761"

    def load(relative, supplied=None):
        source = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=root).decode(
            "utf-8"
        )
        tree = ast.parse(source)
        if supplied:
            tree.body = [
                node
                for node in tree.body
                if not (
                    isinstance(node, ast.ImportFrom)
                    and node.module in {"catalog_mixin", "manager_content_mixin"}
                )
            ]
        namespace = {
            "__name__": "super_dev.integrations._rework02_baseline_fixture",
            "__package__": "super_dev.integrations",
            **(supplied or {}),
        }
        exec(compile(tree, relative, "exec"), namespace)
        return namespace

    content = load("super_dev/integrations/manager_content_mixin.py")
    catalog = load("super_dev/integrations/catalog_mixin.py")
    manager = load(
        "super_dev/integrations/manager.py",
        {
            "IntegrationCatalogMixin": catalog["IntegrationCatalogMixin"],
            "IntegrationManagerContentMixin": content["IntegrationManagerContentMixin"],
        },
    )
    manifest = load("super_dev/integrations/install_manifest.py")
    return manager["IntegrationManager"], manifest["record_install_manifest"]


def _rework02_legacy_install(project, host, newline="windows", global_scope=False):
    producer, record_manifest = _rework02_baseline_producers()
    legacy = producer(project, user_directories=UserDirectoryContext.current())
    rules = (
        legacy.resolve_global_protocol_path(host)
        if global_scope
        else project / ("CLAUDE.md" if host == "claude-code" else "AGENTS.md")
    )
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.write_bytes(b"OLD_USER\n\n")
    if global_scope:
        assert legacy.setup_global_protocol(host) is not None
    else:
        legacy.setup(host, force=host == "windsurf")
    if newline == "lf":
        for path in legacy.collect_managed_surface_paths(host).values():
            if path.is_file():
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    record_manifest(
        project,
        host=host,
        family=legacy.host_family(host),
        scopes={"project": not global_scope, "global": global_scope, "runtime": False},
        paths=[
            str(path)
            for path in legacy.collect_managed_surface_paths(host).values()
            if path.is_file()
        ],
    )
    assert "content_ownership" not in legacy.load_install_manifest()
    installed = rules.read_bytes()
    markers = (
        (legacy.CLAUDE_RULES_BEGIN, legacy.CLAUDE_RULES_END)
        if host == "claude-code"
        else legacy._managed_agents_markers(host)
    )
    if markers:
        from super_dev.integrations.managed_content import block_span

        start, stop = block_span(installed, *markers)
        outside = installed[:start] + installed[stop:]
    else:
        outside = b""
    return IntegrationManager(project, user_directories=legacy.user_directories), rules, outside


def _rework01_legacy_install(project, host, monkeypatch, newline="windows", global_scope=False):
    root = Path(__file__).resolve().parents[2]
    commit = "26b0cb6c98e723b8c12c4d721785a9cb91d6f761"
    old_source = subprocess.check_output(
        ["git", "show", f"{commit}:super_dev/integrations/manager_content_mixin.py"], cwd=root
    ).decode("utf-8")
    writer = next(
        node
        for node in ast.walk(ast.parse(old_source))
        if isinstance(node, ast.FunctionDef) and node.name == "_upsert_managed_block"
    )
    namespace = {"Path": Path}
    exec(
        compile(ast.Module(body=[writer], type_ignores=[]), "baseline-block-writer", "exec"),
        namespace,
    )
    old_manifest_source = subprocess.check_output(
        ["git", "show", f"{commit}:super_dev/integrations/install_manifest.py"], cwd=root
    ).decode("utf-8")
    old_manifest = {}
    exec(compile(old_manifest_source, "baseline-install-manifest", "exec"), old_manifest)
    manager = IntegrationManager(project)
    rules = (
        manager.resolve_global_protocol_path(host)
        if global_scope
        else project / ("CLAUDE.md" if host == "claude-code" else "AGENTS.md")
    )
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.write_bytes(b"LEGACY_USER\n\n")
    owner = next(
        parent
        for parent in IntegrationManager.__mro__
        if "_upsert_managed_block" in parent.__dict__
    )
    with monkeypatch.context() as context:
        context.setattr(owner, "_upsert_managed_block", namespace["_upsert_managed_block"])
        if global_scope:
            manager.setup_global_protocol(host)
        else:
            manager.setup(host)
    if newline == "lf":
        rules.write_bytes(rules.read_bytes().replace(b"\r\n", b"\n"))
    old_manifest["record_install_manifest"](
        project,
        host=host,
        family=manager.host_family(host),
        scopes={"project": not global_scope, "global": global_scope, "runtime": False},
        paths=[
            str(path)
            for path in manager.collect_managed_surface_paths(host).values()
            if path.exists()
        ],
    )
    assert "content_ownership" not in manager.load_install_manifest()
    begin, end = (
        (manager.CLAUDE_RULES_BEGIN, manager.CLAUDE_RULES_END)
        if host == "claude-code"
        else manager._managed_agents_markers(host)
    )
    installed = rules.read_bytes()
    from super_dev.integrations.managed_content import block_span

    start, stop = block_span(installed, begin, end)
    return manager, rules, begin, end, installed[:start] + installed[stop:]


def test_dsh_identity_and_native_skill_entry(tmp_path):
    definition = get_host_definition(HOST)
    assert definition is not None
    assert definition.install_mode == HostInstallMode.HYBRID
    assert definition.supports_slash
    assert HOST_TOOL_CATEGORY_MAP[HOST] == "assistant"
    assert HOST_TOOL_ALIASES[HOST] == ["dsh"]
    assert normalize_host_tool_id("dsh") == HOST
    assert normalize_host_tool_id("deepseek") != HOST
    manager = IntegrationManager(tmp_path)
    assert manager.supports_slash(HOST)
    assert not manager.supports_command_files(HOST)
    assert manager.setup_slash_command(HOST) is None
    profile = manager.get_adapter_profile(HOST)
    assert profile.slash_command_file == ""
    assert profile.certification_level == "experimental"
    assert profile.trigger_command == "/super-dev"
    assert not (tmp_path / ".dsh/commands").exists()


@pytest.mark.parametrize("skill_name", ["super-dev", "super-dev-seeai"])
def test_dsh_frontmatter_and_host_contract(skill_name):
    rendered = SkillTemplate.for_builtin(skill_name, HOST).render(HOST)
    frontmatter = yaml.safe_load(rendered.split("---", 2)[1])
    assert set(frontmatter) == {
        "name",
        "description",
        "whenToUse",
        "metadata",
        "user-invocable",
        "disable-model-invocation",
    }
    assert frontmatter["name"] == skill_name
    assert frontmatter["user-invocable"] is True
    assert frontmatter["disable-model-invocation"] is False
    assert "DeepSeek Harness" in rendered
    assert "active" in rendered and "armed" in rendered
    assert "自动续跑" in rendered and "明确确认" in rendered
    assert "已注入" in rendered and "重复加载" in rendered
    assert "~/.codex" not in rendered
    assert "知识" in rendered and "单" in rendered


@pytest.mark.parametrize(
    "original",
    [
        b"\n\nUSER_CONTENT\r\n\r\n",
        b"\xef\xbb\xbfUSER\r\n\r\n",
        b"USER",
        b"  \r\n\t",
        b"",
        b"USER\n",
    ],
)
def test_managed_block_exact_round_trip(tmp_path, original):
    manager = IntegrationManager(tmp_path)
    path = tmp_path / "AGENTS.local.md"
    path.write_bytes(original)
    arguments = dict(file_path=path, begin=BEGIN, end=END, block_content="TEST_ONLY")
    manager._upsert_managed_block(**arguments)
    first = path.read_bytes()
    manager._upsert_managed_block(**arguments)
    assert path.read_bytes() == first
    manager._remove_managed_block(file_path=path, begin=BEGIN, end=END)
    assert path.exists()
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "broken",
    [
        BEGIN,
        END,
        BEGIN + END + BEGIN + END,
        BEGIN + "<!-- BEGIN SUPER DEV CODEX -->" + END + "<!-- END SUPER DEV CODEX -->",
    ],
)
def test_managed_block_rejects_ambiguous_boundaries(tmp_path, broken):
    manager = IntegrationManager(tmp_path)
    path = tmp_path / "AGENTS.local.md"
    original = broken.encode()
    path.write_bytes(original)
    with pytest.raises(ValueError):
        manager._upsert_managed_block(
            file_path=path, begin=BEGIN, end=END, block_content="TEST_ONLY"
        )
    assert path.read_bytes() == original
    with pytest.raises(ValueError):
        manager._remove_managed_block(file_path=path, begin=BEGIN, end=END)
    assert path.read_bytes() == original


def test_dsh_real_setup_remove_preserves_other_host_and_user_bytes(tmp_path):
    manager = IntegrationManager(tmp_path)
    original = b"\xef\xbb\xbf\r\nUSER\r\n\r\n"
    path = tmp_path / "AGENTS.local.md"
    path.write_bytes(original)
    codex_path = tmp_path / "AGENTS.md"
    codex_path.write_bytes(b"CODEX USER\r\n")
    manager.setup("codex")
    codex_bytes = codex_path.read_bytes()
    manager.setup(HOST)
    first = path.read_bytes()
    manager.setup(HOST)
    assert path.read_bytes() == first
    for skill_name in ("super-dev", "super-dev-seeai"):
        skill_path = tmp_path / ".dsh/skills" / skill_name / "SKILL.md"
        assert (
            skill_path.read_bytes()
            == SkillTemplate.for_builtin(skill_name, HOST).render(HOST).encode()
        )
    assert b"DSH" in first
    manager.remove(HOST)
    assert path.read_bytes() == original
    assert codex_path.read_bytes() == codex_bytes
    assert not (tmp_path / ".dsh/skills/super-dev/SKILL.md").exists()
    assert not (tmp_path / ".dsh/skills/super-dev-seeai/SKILL.md").exists()


def test_dsh_preserves_modified_and_unowned_skills(tmp_path):
    manager = IntegrationManager(tmp_path)
    manager.setup(HOST)
    skill_path = tmp_path / ".dsh/skills/super-dev/SKILL.md"
    modified = skill_path.read_bytes() + b"USER CHANGE\r\n"
    skill_path.write_bytes(modified)
    with pytest.raises(ValueError):
        manager.setup(HOST, force=True)
    assert skill_path.read_bytes() == modified
    with pytest.raises(ValueError):
        manager.remove(HOST)
    assert skill_path.read_bytes() == modified
    unrelated = tmp_path / "unowned"
    unowned_path = unrelated / ".dsh/skills/super-dev/SKILL.md"
    unowned_path.parent.mkdir(parents=True)
    unowned_path.write_bytes(b"USER SKILL")
    with pytest.raises(ValueError):
        IntegrationManager(unrelated).setup(HOST, force=True)
    assert unowned_path.read_bytes() == b"USER SKILL"


def test_dsh_partial_failure_reruns_original_entry(tmp_path, monkeypatch):
    manager = IntegrationManager(tmp_path)
    original = b"\n\nUSER_CONTENT\r\n\r\n"
    rules = tmp_path / "AGENTS.local.md"
    rules.write_bytes(original)
    write_bytes = Path.write_bytes

    def fail_seeai(path, data):
        if path.parent.name == "super-dev-seeai":
            raise OSError("injected write failure")
        return write_bytes(path, data)

    with monkeypatch.context() as context:
        context.setattr(Path, "write_bytes", fail_seeai)
        with pytest.raises(OSError, match="injected"):
            manager.setup(HOST)
    manager.setup(HOST)
    first = rules.read_bytes()
    manager.setup(HOST)
    assert rules.read_bytes() == first
    manager.remove(HOST)
    assert rules.read_bytes() == original


def test_dsh_injected_user_directory_and_legacy_constructor(tmp_path):
    home = tmp_path / "home"
    directories = UserDirectoryContext.from_home(home, dsh_home=tmp_path / "custom-dsh")
    legacy = UserDirectoryContext(home, home / ".codex", home / ".config")
    assert legacy.dsh_home == home / ".dsh"
    assert directories.environment({})["DSH_HOME"] == str(tmp_path / "custom-dsh")
    project = tmp_path / "project"
    skills = SkillManager(project, user_directories=directories)
    skills.install("super-dev", HOST)
    for name in ("super-dev", "super-dev-seeai"):
        path = directories.dsh_home / "skills" / name / "SKILL.md"
        assert path.exists()
    skills.install("super-dev", HOST)
    assert not (home / ".codex").exists()
    assert not (project / ".dsh").exists()
    skills.uninstall("super-dev", HOST)
    skills.uninstall("super-dev-seeai", HOST)


def test_old_render_bytes_match_preimplementation_evidence():
    baseline = {
        "claude-code/super-dev": (
            27019,
            "288ee8c15e527b9acc3c5012387da2cfd7c27e3ad9b2189aa01ada81dd2d900b",
        ),
        "claude-code/super-dev-seeai": (
            40911,
            "92dba112cf44e482262b1e38a4bbc46e79750dc114491cc9e2639bc65a700696",
        ),
        "codex/super-dev": (
            27587,
            "3a5aa563e4dd3771dbac601a2eedf876f314a8f442799192fa0e52f3c521bd9c",
        ),
        "codex/super-dev-seeai": (
            41521,
            "059831378ccfd07853d781911012cb383d76ac4d19e406e3f5f7b887e0fd8cd7",
        ),
    }
    for identity, (size, expected_hash) in baseline.items():
        host, name = identity.split("/")
        rendered = SkillTemplate.for_builtin(name, host).render(host).encode()
        assert len(rendered) == size
        assert hashlib.sha256(rendered).hexdigest() == expected_hash


@pytest.mark.parametrize(
    "host",
    [
        "codex",
        "codex-cli",
        "opencode",
        "qoder",
        "qoder-cli",
        "cursor",
        "cursor-cli",
        "kiro",
        "kiro-cli",
        "droid-cli",
        "copilot-cli",
        "kimi-code",
        "trae-solo",
        "claude-code",
        "windsurf",
    ],
)
def test_shared_block_consumers_preserve_user_bytes(tmp_path, host):
    manager = IntegrationManager(tmp_path)
    name = "CLAUDE.md" if host == "claude-code" else "AGENTS.md"
    path = tmp_path / name
    original = b"\xef\xbb\xbf\n\nUSER_CONTENT\r\n\r\n"
    path.write_bytes(original)
    manager.setup(host)
    first = path.read_bytes()
    manager.setup(host)
    assert path.read_bytes() == first
    manager.remove(host)
    assert path.read_bytes() == original


def test_dsh_update_keeps_ownership_and_outside_bytes(tmp_path, monkeypatch):
    manager = IntegrationManager(tmp_path)
    path = tmp_path / "AGENTS.local.md"
    original = b"\xef\xbb\xbf\r\nUSER\r\n\r\n"
    path.write_bytes(original)
    manager.setup(HOST)
    snapshot = snapshot_hosts(tmp_path, include_user=False)
    assert not snapshot["issues"]
    original_render = SkillTemplate.render

    def updated_render(template, host):
        return original_render(template, host) + ("\nUPDATED\n" if host == HOST else "")

    monkeypatch.setattr(SkillTemplate, "render", updated_render)
    result = refresh_hosts(tmp_path, snapshot, include_user=False)
    assert not result["issues"]
    assert len(result["changed"]) == 2
    manager.setup(HOST)
    manager.remove(HOST)
    assert path.read_bytes() == original


def test_dsh_cli_project_default_doctor_and_real_uninstall(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli = SuperDevCLI()
    home = UserDirectoryContext.current().dsh_home
    assert cli._cmd_onboard(cli.parser.parse_args(["onboard", "--host", "dsh", "--yes"])) == 0
    assert not home.exists()
    capsys.readouterr()
    assert cli._cmd_doctor(cli.parser.parse_args(["doctor", "--host", "dsh", "--json"])) == 0
    report = json.loads(capsys.readouterr().out)
    host_report = report["hosts"][HOST]
    assert host_report["ready"]
    assert report["compatibility"]["hosts"][HOST]["flow_consistent"] is True
    assert report["compatibility"]["flow_consistency_score"] == 100.0
    closure = host_report["injection_closure"]
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is True
    assert not closure["status"].endswith("_competition_incomplete")
    assert closure["competition_project_surfaces_ready"] is True
    assert closure["competition_user_surfaces_ready"] is False
    assert closure["missing_managed_competition_user_surfaces"]
    assert host_report["checks"]["competition_user_surfaces"]["ok"] is False
    assert host_report["checks"]["competition_user_surfaces"]["required"] is False
    assert "competition_user_surfaces" in host_report["optional_missing"]
    assert any("用户级 SEEAI 接入为可选项" in item for item in host_report["suggestions"])
    assert not any(
        "先补齐当前宿主的 Super Dev SEEAI 用户级" in item for item in host_report["suggestions"]
    )
    assert not home.exists()
    assert host_report["desktop_validation"]["status"] == "unverified"
    assert host_report["checks"]["slash"]["mode"] == "native-skill-entry"
    assert (
        cli._cmd_uninstall(cli.parser.parse_args(["uninstall", "--host", "dsh", "--yes", "--json"]))
        == 0
    )
    assert not (tmp_path / "AGENTS.local.md").exists()
    assert not (tmp_path / ".dsh/skills/super-dev/SKILL.md").exists()
    assert not home.exists()


def test_dsh_cli_opt_in_user_and_modified_content_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli = SuperDevCLI()
    args = cli.parser.parse_args(["onboard", "--host", "dsh", "--yes", "--with-user-surfaces"])
    assert cli._cmd_onboard(args) == 0
    path = UserDirectoryContext.current().dsh_home / "skills/super-dev/SKILL.md"
    assert path.exists()
    original = path.read_bytes() + b"USER CHANGE"
    path.write_bytes(original)
    capsys.readouterr()
    assert (
        cli._cmd_uninstall(cli.parser.parse_args(["uninstall", "--host", "dsh", "--yes", "--json"]))
        == 1
    )
    report = json.loads(capsys.readouterr().out)
    assert report["error_count"] > 0
    assert path.read_bytes() == original


@pytest.mark.parametrize("skill_name", ["super-dev", "super-dev-seeai"])
def test_dsh_doctor_reports_flows_not_ready_when_project_skill_content_is_modified(
    tmp_path, monkeypatch, capsys, skill_name
):
    monkeypatch.chdir(tmp_path)
    IntegrationManager(tmp_path).setup(HOST)
    skill_file = tmp_path / ".dsh/skills" / skill_name / "SKILL.md"
    modified = skill_file.read_bytes() + b"\nFixture-only local edit.\n"
    skill_file.write_bytes(modified)
    cli = SuperDevCLI()
    args = cli.parser.parse_args(["doctor", "--host", "dsh", "--json"])

    assert cli._cmd_doctor(args) == 1

    report = json.loads(capsys.readouterr().out)["hosts"][HOST]
    assert report["ready"] is False
    assert report["checks"]["dsh_skill_content"]["skills"][skill_name] is False
    assert report["checks"]["slash"]["ok"] is False
    closure = report["injection_closure"]
    assert closure["standard_flow_ready"] is False
    assert closure["competition_flow_ready"] is False
    assert report["desktop_validation"]["status"] == "unverified"
    assert skill_file.read_bytes() == modified
    assert not UserDirectoryContext.current().dsh_home.exists()


def test_dsh_doctor_repair_preserves_modified_project_skill(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    manager = IntegrationManager(tmp_path)
    manager.setup(HOST)
    path = tmp_path / ".dsh/skills/super-dev/SKILL.md"
    modified = path.read_bytes() + b"USER MODIFICATION"
    path.write_bytes(modified)
    cli = SuperDevCLI()
    args = cli.parser.parse_args(["doctor", "--host", "dsh", "--json", "--repair", "--force"])
    assert cli._cmd_doctor(args) == 1
    assert path.read_bytes() == modified
    assert not UserDirectoryContext.current().dsh_home.exists()


@pytest.mark.parametrize("keep_begin", [False, True])
def test_dsh_doctor_requires_a_complete_dsh_project_rule_block(
    tmp_path, monkeypatch, capsys, keep_begin
):
    monkeypatch.chdir(tmp_path)
    IntegrationManager(tmp_path).setup(HOST)
    rules_file = tmp_path / "AGENTS.local.md"
    rules = rules_file.read_bytes().replace(
        IntegrationManager.DSH_AGENTS_END.encode(), b"<!-- END SUPER DEV OTHER -->"
    )
    if not keep_begin:
        rules = rules.replace(
            IntegrationManager.DSH_AGENTS_BEGIN.encode(), b"<!-- BEGIN SUPER DEV OTHER -->"
        )
    rules_file.write_bytes(rules)
    cli = SuperDevCLI()
    args = cli.parser.parse_args(["doctor", "--host", "dsh", "--json"])

    assert cli._cmd_doctor(args) == 1

    report = json.loads(capsys.readouterr().out)
    host_report = report["hosts"][HOST]
    assert host_report["ready"] is False
    assert host_report["checks"]["dsh_skill_content"]["ok"] is True
    assert "project:AGENTS.local.md" in host_report["checks"]["contract"]["invalid_surfaces"]
    assert host_report["injection_closure"]["standard_flow_ready"] is False
    assert host_report["injection_closure"]["competition_flow_ready"] is False
    assert report["compatibility"]["hosts"][HOST]["flow_consistent"] is False
    assert report["compatibility"]["flow_consistency_score"] == 0.0
    assert rules_file.read_bytes() == rules


def test_dsh_corrupt_manifest_and_modified_block_are_preserved(tmp_path):
    manager = IntegrationManager(tmp_path)
    manager.setup(HOST)
    path = tmp_path / "AGENTS.local.md"
    modified = path.read_bytes().replace(b"DSH", b"DSH USER", 1)
    path.write_bytes(modified)
    with pytest.raises(ValueError):
        manager.setup(HOST)
    assert path.read_bytes() == modified
    manifest = tmp_path / ".super-dev/install-manifest.json"
    manifest.write_bytes(b"{broken manifest")
    with pytest.raises(ValueError):
        manager.setup(HOST)
    assert manifest.read_bytes() == b"{broken manifest"


def test_dsh_pending_ownership_recovers_after_manifest_commit_failure(tmp_path, monkeypatch):
    from super_dev.integrations import managed_content

    manager = IntegrationManager(tmp_path)
    original_save = managed_content.save_record
    count = 0

    def fail_commit(project, key, record):
        nonlocal count
        count += 1
        if count == 4:
            raise OSError("injected manifest commit failure")
        return original_save(project, key, record)

    with monkeypatch.context() as context:
        context.setattr(managed_content, "save_record", fail_commit)
        with pytest.raises(OSError, match="manifest commit"):
            manager.setup(HOST)
    manager.setup(HOST)
    records = managed_content.ownership(tmp_path)
    assert all(not record.get("pending_sha256") for record in records.values())
    manager.remove(HOST)


def test_dsh_doctor_fix_stays_in_selected_project(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cli = SuperDevCLI()
    assert (
        cli._cmd_doctor(cli.parser.parse_args(["doctor", "--host", "dsh", "--fix", "--json"])) == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["selected_targets"] == [HOST]
    assert report["repair_actions"][HOST]["project"] == "refreshed"
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".agents").exists()
    assert not UserDirectoryContext.current().dsh_home.exists()


def test_dsh_builtin_name_cannot_escape_injected_home(tmp_path):
    directories = UserDirectoryContext.from_home(tmp_path / "home")
    manager = SkillManager(tmp_path / "project", user_directories=directories)
    with pytest.raises(ValueError):
        manager.install("super-dev", HOST, name="../../other-file", force=True)
    assert not directories.home.exists()


def test_dsh_missing_both_registered_markers_is_preserved_and_reported(tmp_path):
    manager = IntegrationManager(tmp_path)
    manager.setup(HOST)
    path = tmp_path / "AGENTS.local.md"
    modified = (
        path.read_bytes()
        .replace(manager.DSH_AGENTS_BEGIN.encode(), b"")
        .replace(manager.DSH_AGENTS_END.encode(), b"")
    )
    path.write_bytes(modified)
    with pytest.raises(ValueError, match="边界缺失"):
        manager.setup(HOST)
    with pytest.raises(ValueError, match="边界缺失"):
        manager.remove(HOST)
    assert path.read_bytes() == modified


def test_dsh_reinstall_after_uninstall_clears_old_ownership(tmp_path):
    from super_dev.integrations.managed_content import ownership

    manager = IntegrationManager(tmp_path)
    manager.setup(HOST)
    manager.remove(HOST)
    assert ownership(tmp_path) == {}
    manager.setup(HOST)
    manager.remove(HOST)
    assert ownership(tmp_path) == {}


def test_dsh_cli_does_not_rewrite_corrupt_ownership_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    IntegrationManager(tmp_path).setup(HOST)
    manifest = tmp_path / ".super-dev/install-manifest.json"
    original = b"{broken ownership manifest"
    manifest.write_bytes(original)
    cli = SuperDevCLI()
    assert cli._cmd_onboard(cli.parser.parse_args(["onboard", "--host", "dsh", "--yes"])) == 1
    assert manifest.read_bytes() == original


def test_dsh_api_repair_is_project_only(tmp_path, monkeypatch):
    from super_dev.web import api_host_support

    monkeypatch.setattr(api_host_support, "_detect_host_targets", lambda targets: ([], {}))
    report = api_host_support.run_host_doctor(tmp_path, host=HOST, repair=True)
    assert report["report"]["hosts"][HOST]["ready"]
    assert (tmp_path / ".dsh/skills/super-dev/SKILL.md").exists()
    assert not UserDirectoryContext.current().dsh_home.exists()


def test_dsh_global_legacy_cleanup_preserves_unknown_content(tmp_path):
    directories = UserDirectoryContext.from_home(
        tmp_path / "home", dsh_home=tmp_path / "home/.custom-dsh"
    )
    default = directories.home / ".dsh/skills/super-dev-core/SKILL.md"
    custom = directories.dsh_home / "skills/super-dev-core/SKILL.md"
    for path in (default, custom):
        path.parent.mkdir(parents=True)
        path.write_bytes(b"USER LEGACY CONTENT")
    SkillManager.cleanup_all_legacy(user_directories=directories)
    for path in (default, custom):
        assert path.read_bytes() == b"USER LEGACY CONTENT"
    assert SkillManager(tmp_path, directories).legacy_skill_cleanup_paths(HOST) == []


def test_dsh_silent_refresh_does_not_touch_user_skill(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    SkillManager(tmp_path).install("super-dev", HOST)
    path = UserDirectoryContext.current().dsh_home / "skills/super-dev/SKILL.md"
    original = path.read_bytes()
    original_render = SkillTemplate.render

    def changed_render(template, host):
        return original_render(template, host) + ("\nNEW VERSION\n" if host == HOST else "")

    monkeypatch.setattr(SkillTemplate, "render", changed_render)
    cli = SuperDevCLI()
    cli._auto_refresh_outdated_skills()
    assert path.read_bytes() == original


def test_dsh_hardening_default_is_project_only(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        IntegrationManager, "compare_official_capabilities", lambda *arguments, **options: {}
    )
    cli = SuperDevCLI()
    cli._cmd_integrate(cli.parser.parse_args(["integrate", "harden", "--target", "dsh", "--json"]))
    payload = json.loads(capsys.readouterr().out)
    assert not UserDirectoryContext.current().dsh_home.exists()
    assert payload["hardening_results"][HOST]["skill_install"]["scope"] == "project"
    assert (tmp_path / ".dsh/skills/super-dev/SKILL.md").exists()


def test_dsh_migration_does_not_create_user_skill_for_unrelated_install(tmp_path):
    from super_dev.migrate import migrate_project

    IntegrationManager(tmp_path).setup(HOST)
    user_root = UserDirectoryContext.current().dsh_home / "skills"
    unrelated = user_root / "unrelated/SKILL.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_bytes(b"USER UNRELATED SKILL")
    migrate_project(tmp_path)
    assert unrelated.read_bytes() == b"USER UNRELATED SKILL"
    assert not (user_root / "super-dev").exists()


def test_dsh_custom_home_install_manifest_scope_is_accurate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "custom-dsh-home"
    monkeypatch.setenv("DSH_HOME", str(custom))
    cli = SuperDevCLI()
    args = cli.parser.parse_args(["onboard", "--host", "dsh", "--yes", "--with-user-surfaces"])
    for attempt in range(2):
        assert cli._cmd_onboard(args) == 0
        manifest = json.loads(
            (tmp_path / ".super-dev/install-manifest.json").read_text(encoding="utf-8")
        )
        target = manifest["targets"][HOST]
        assert target["scopes"]["global"]
        for name in ("super-dev", "super-dev-seeai"):
            assert str(custom / "skills" / name / "SKILL.md") in target["paths"]


def test_dsh_migration_preserves_installed_user_scope(tmp_path):
    from super_dev.migrate import migrate_project

    IntegrationManager(tmp_path).setup(HOST)
    SkillManager(tmp_path).install("super-dev", HOST)
    migrate_project(tmp_path)
    manifest = json.loads(
        (tmp_path / ".super-dev/install-manifest.json").read_text(encoding="utf-8")
    )
    target = manifest["targets"][HOST]
    assert target["scopes"]["global"]
    for name in ("super-dev", "super-dev-seeai"):
        expected = UserDirectoryContext.current().dsh_home / "skills" / name / "SKILL.md"
        assert str(expected) in target["paths"]


def test_dsh_real_uninstall_clears_target_and_does_not_resurrect_on_migration(
    tmp_path, monkeypatch
):
    from super_dev.migrate import migrate_project

    monkeypatch.chdir(tmp_path)
    cli = SuperDevCLI()
    assert cli._cmd_onboard(cli.parser.parse_args(["onboard", "--host", "dsh", "--yes"])) == 0
    assert (
        cli._cmd_uninstall(cli.parser.parse_args(["uninstall", "--host", "dsh", "--yes", "--json"]))
        == 0
    )
    manifest = json.loads(
        (tmp_path / ".super-dev/install-manifest.json").read_text(encoding="utf-8")
    )
    assert HOST not in manifest["targets"]
    migrate_project(tmp_path)
    assert not (tmp_path / ".dsh/skills/super-dev/SKILL.md").exists()
    assert not (tmp_path / "AGENTS.local.md").exists()


def test_dsh_partial_scope_removal_keeps_only_remaining_owned_scope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli = SuperDevCLI()
    assert (
        cli._cmd_onboard(
            cli.parser.parse_args(["onboard", "--host", "dsh", "--yes", "--with-user-surfaces"])
        )
        == 0
    )
    IntegrationManager(tmp_path).remove(HOST)
    manifest_path = tmp_path / ".super-dev/install-manifest.json"
    target = json.loads(manifest_path.read_text(encoding="utf-8"))["targets"][HOST]
    assert not target["scopes"]["project"]
    assert target["scopes"]["global"]
    skills = SkillManager(tmp_path)
    skills.uninstall("super-dev", HOST)
    skills.uninstall("super-dev-seeai", HOST)
    assert HOST not in json.loads(manifest_path.read_text(encoding="utf-8"))["targets"]


@pytest.mark.parametrize("host", ["codex", "claude-code"])
@pytest.mark.parametrize("newline", ["windows", "lf"])
@pytest.mark.parametrize("operation", ["reinstall", "remove"])
def test_rework01_legacy_block_maintenance(tmp_path, monkeypatch, host, newline, operation):
    manager, rules, begin, end, outside = _rework01_legacy_install(
        tmp_path, host, monkeypatch, newline
    )
    if operation == "reinstall":
        manager.setup(host, force=True)
    manager.remove(host)
    assert rules.read_bytes() == outside


@pytest.mark.parametrize("host", ["codex", "claude-code"])
def test_rework01_legacy_global_block_maintenance(tmp_path, monkeypatch, host):
    manager, rules, begin, end, outside = _rework01_legacy_install(
        tmp_path, host, monkeypatch, global_scope=True
    )
    manager.setup_global_protocol(host, force=True)
    manager._remove_managed_block(file_path=rules, begin=begin, end=end)
    assert rules.read_bytes() == outside


@pytest.mark.parametrize("host", ["codex", "claude-code"])
@pytest.mark.parametrize(
    "invalid",
    [
        "modified",
        "unknown_version",
        "wrong_manifest_version",
        "wrong_path",
        "wrong_scope",
        "wrong_family",
    ],
)
def test_rework01_legacy_adoption_rejects_unverifiable_blocks(tmp_path, monkeypatch, host, invalid):
    manager, rules, begin, end, outside = _rework01_legacy_install(tmp_path, host, monkeypatch)
    manifest = manager.load_install_manifest()
    if invalid in {"modified", "unknown_version"}:
        rules.write_bytes(
            rules.read_bytes().replace(end.encode(), b"UNRECOGNIZED BODY\n" + end.encode())
        )
    elif invalid == "wrong_manifest_version":
        manifest["version"] = 999
    elif invalid == "wrong_path":
        manifest["targets"][host]["paths"] = [str(tmp_path / "different.md")]
    elif invalid == "wrong_scope":
        manifest["targets"][host]["scopes"] = {"project": False, "global": True}
    else:
        manifest["targets"][host]["family"] = "unrecognized-family"
    if invalid == "unknown_version":
        manifest["version"] = 999
    manager.save_install_manifest(manifest)
    original = rules.read_bytes()
    with pytest.raises(ValueError):
        manager.setup(host, force=True)
    with pytest.raises(ValueError):
        manager._remove_managed_block(file_path=rules, begin=begin, end=end)
    assert rules.read_bytes() == original


@pytest.mark.parametrize("host", ["codex", "claude-code", HOST])
def test_rework01_shared_update_preserves_ownership_and_round_trip(tmp_path, monkeypatch, host):
    manager = IntegrationManager(tmp_path)
    relative = (
        "AGENTS.local.md"
        if host == HOST
        else ("CLAUDE.md" if host == "claude-code" else "AGENTS.md")
    )
    rules = tmp_path / relative
    original = b"\xef\xbb\xbfPRIVATE_OUTSIDE\r\n\r\n"
    rules.write_bytes(original)
    manager.setup(host)
    snapshot = snapshot_hosts(tmp_path, include_user=False)
    assert not snapshot["issues"]
    original_builder = IntegrationManager._build_file_content
    rule_relative = relative

    def upgraded(instance, target, relative):
        body = original_builder(instance, target, relative)
        return (
            body + "\nREWORK_UPGRADED_BODY\n"
            if target in {host, "codex-cli" if host == "codex" else host}
            and relative == rule_relative
            else body
        )

    with monkeypatch.context() as context:
        context.setattr(IntegrationManager, "_build_file_content", upgraded)
        report = refresh_hosts(tmp_path, snapshot, include_user=False)
        assert not report["issues"]
        assert str(rules) in report["changed"]
        manager.setup(host, force=True)
        manager.remove(host)
    assert rules.read_bytes() == original
    for backup in Path(report["backup_dir"]).glob("*.json"):
        assert "PRIVATE_OUTSIDE" not in backup.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "broken",
    [
        b"<!-- BEGIN SUPER DEV CODEX -->\nUSER\n",
        b"<!-- END SUPER DEV CODEX -->\nUSER\n",
        b"<!-- BEGIN SUPER DEV CODEX -->\n<!-- BEGIN SUPER DEV OPENCODE -->\n<!-- END SUPER DEV CODEX -->\n<!-- END SUPER DEV OPENCODE -->\n",
        b"<!-- BEGIN SUPER DEV CODEX -->\nX\n<!-- END SUPER DEV CODEX -->\n<!-- BEGIN SUPER DEV CODEX -->\nY\n<!-- END SUPER DEV CODEX -->\n",
    ],
)
def test_rework01_first_append_rejects_other_broken_boundaries(tmp_path, broken):
    path = tmp_path / "AGENTS.local.md"
    path.write_bytes(broken)
    with pytest.raises(ValueError):
        IntegrationManager(tmp_path).setup(HOST)
    assert path.read_bytes() == broken
    assert not (tmp_path / ".dsh").exists()


def test_rework01_complete_other_block_round_trips_exactly(tmp_path):
    rules = tmp_path / "AGENTS.local.md"
    original = (
        b"\xef\xbb\xbf\r\nUSER\r\n<!-- BEGIN SUPER DEV CODEX -->\r\n"
        b"OTHER\r\n<!-- END SUPER DEV CODEX -->\r\nTAIL"
    )
    rules.write_bytes(original)
    manager = IntegrationManager(tmp_path)
    manager.setup(HOST)
    first = rules.read_bytes()
    manager.setup(HOST)
    assert rules.read_bytes() == first
    manager.remove(HOST)
    assert rules.read_bytes() == original


def test_rework01_project_only_uninstall_stays_out_of_other_project_user_scope(
    tmp_path, monkeypatch, capsys
):
    project_a, project_b = tmp_path / "a", tmp_path / "b"
    project_a.mkdir()
    project_b.mkdir()
    cli = SuperDevCLI()
    monkeypatch.chdir(project_a)
    assert (
        cli._cmd_onboard(
            cli.parser.parse_args(["onboard", "--host", "dsh", "--yes", "--with-user-surfaces"])
        )
        == 0
    )
    user_paths = [
        UserDirectoryContext.current().dsh_home / "skills" / name / "SKILL.md"
        for name in ("super-dev", "super-dev-seeai")
    ]
    before = {path: path.read_bytes() for path in user_paths}
    monkeypatch.chdir(project_b)
    assert cli._cmd_onboard(cli.parser.parse_args(["onboard", "--host", "dsh", "--yes"])) == 0
    capsys.readouterr()
    assert (
        cli._cmd_uninstall(
            cli.parser.parse_args(["uninstall", "--host", "dsh", "--json", "--dry-run"])
        )
        == 0
    )
    preview = json.loads(capsys.readouterr().out)["targets"][0]
    assert preview["planned_skill_paths"] == []
    assert not any(
        str(UserDirectoryContext.current().dsh_home) in path
        for path in preview["planned_surface_paths"]
    )
    assert cli._cmd_uninstall(cli.parser.parse_args(["uninstall", "--host", "dsh", "--json"])) == 0
    assert all(path.read_bytes() == before[path] for path in user_paths)
    monkeypatch.chdir(project_a)
    assert cli._cmd_uninstall(cli.parser.parse_args(["uninstall", "--host", "dsh", "--json"])) == 0
    assert all(not path.exists() for path in user_paths)


@pytest.mark.parametrize("original", [b"USER\r\n", None, b""])
@pytest.mark.parametrize("retry", ["remove", "setup"])
def test_rework01_deletion_commit_failure_recovers(tmp_path, monkeypatch, original, retry):
    from super_dev.integrations import managed_content

    manager = IntegrationManager(tmp_path)
    rules = tmp_path / "AGENTS.local.md"
    if original is not None:
        rules.write_bytes(original)
    manager.setup(HOST)
    key = f"{rules.absolute()}|{manager.DSH_AGENTS_BEGIN}"
    original_delete = managed_content.delete_record
    injected = False

    def fail_commit(project, record_key):
        nonlocal injected
        if record_key == key and not injected:
            injected = True
            assert rules.read_bytes() == original if original is not None else not rules.exists()
            raise OSError("rework deletion commit failure")
        return original_delete(project, record_key)

    with monkeypatch.context() as context:
        context.setattr(managed_content, "delete_record", fail_commit)
        with pytest.raises(ValueError, match="rework deletion commit failure"):
            manager.remove(HOST)
    if retry == "remove":
        manager.remove(HOST)
    manager.setup(HOST)
    manager.remove(HOST)
    assert rules.read_bytes() == original if original is not None else not rules.exists()
    assert not managed_content.ownership(tmp_path)


def test_rework01_deletion_pending_rejects_external_changes(tmp_path, monkeypatch):
    from super_dev.integrations import managed_content

    manager = IntegrationManager(tmp_path)
    rules = tmp_path / "AGENTS.local.md"
    rules.write_bytes(b"USER\r\n")
    manager.setup(HOST)
    key = f"{rules.absolute()}|{manager.DSH_AGENTS_BEGIN}"
    original_delete = managed_content.delete_record

    def fail_commit(project, record_key):
        if record_key == key:
            raise OSError("pending delete injection")
        return original_delete(project, record_key)

    with monkeypatch.context() as context:
        context.setattr(managed_content, "delete_record", fail_commit)
        with pytest.raises(ValueError, match="pending delete injection"):
            manager.remove(HOST)
    changed = b"USER\r\nEXTERNAL_CHANGE\r\n"
    rules.write_bytes(changed)
    with pytest.raises(ValueError, match="删除待提交"):
        manager.remove(HOST)
    with pytest.raises(ValueError, match="删除待提交"):
        manager.setup(HOST)
    assert rules.read_bytes() == changed


@pytest.mark.parametrize("change", ["user_block", "manifest", "race"])
def test_rework01_shared_update_rejects_changes_and_bad_manifest(tmp_path, monkeypatch, change):
    manager = IntegrationManager(tmp_path)
    rules = tmp_path / "AGENTS.md"
    rules.write_bytes(b"PRIVATE_OUTSIDE\r\n")
    manager.setup("codex")
    snapshot = snapshot_hosts(tmp_path, include_user=False)
    original = rules.read_bytes()
    if change == "user_block":
        rules.write_bytes(
            original.replace(
                manager.CODEX_AGENTS_END.encode(),
                b"USER_EDIT\n" + manager.CODEX_AGENTS_END.encode(),
            )
        )
    elif change == "manifest":
        payload = manager.load_install_manifest()
        payload["content_ownership"][f"{rules.absolute()}|{manager.CODEX_AGENTS_BEGIN}"][
            "sha256"
        ] = ("0" * 64)
        manager.save_install_manifest(payload)
    preserved = rules.read_bytes()
    original_builder = IntegrationManager._build_file_content

    def upgraded(instance, target, relative):
        body = original_builder(instance, target, relative)
        return (
            body + "\nUPGRADE\n"
            if target in {"codex", "codex-cli"} and relative == "AGENTS.md"
            else body
        )

    write_bytes = Path.write_bytes
    mutated = []

    def mutate_before_replace(path, data):
        if (
            change == "race"
            and path.parent == rules.parent
            and path.name.startswith(".super-dev-AGENTS.md-")
        ):
            write_bytes(rules, b"RACING_OUTSIDE\r\n" + preserved)
            mutated.append(True)
        return write_bytes(path, data)

    with monkeypatch.context() as context:
        context.setattr(IntegrationManager, "_build_file_content", upgraded)
        context.setattr(Path, "write_bytes", mutate_before_replace)
        report = refresh_hosts(tmp_path, snapshot, include_user=False)
    assert report["issues"]
    assert str(rules) not in report["changed"]
    expected = b"RACING_OUTSIDE\r\n" + preserved if change == "race" else preserved
    assert rules.read_bytes() == expected
    assert bool(mutated) == (change == "race")


def test_rework01_unowned_full_file_is_not_claimed_by_update(tmp_path, monkeypatch):
    from super_dev.integrations.managed_content import ownership

    IntegrationManager(tmp_path).setup("codex")
    snapshot = snapshot_hosts(tmp_path, include_user=False)
    skill = tmp_path / ".agents/skills/super-dev/SKILL.md"
    original_render = SkillTemplate.render

    def upgraded(template, host):
        return original_render(template, host) + (
            "\nUPDATED\n" if host in {"codex", "codex-cli"} else ""
        )

    monkeypatch.setattr(SkillTemplate, "render", upgraded)
    report = refresh_hosts(tmp_path, snapshot, include_user=False)
    assert not report["issues"]
    assert str(skill) in report["changed"]
    assert str(skill.absolute()) not in ownership(tmp_path)


def test_rework01_partial_user_install_can_be_uninstalled_without_final_target(
    tmp_path, monkeypatch, capsys
):
    from super_dev.integrations import managed_content

    monkeypatch.chdir(tmp_path)
    cli = SuperDevCLI()
    original_write = managed_content.atomic_write

    def fail_after_user_file(path, content, **options):
        original_write(path, content, **options)
        if path == UserDirectoryContext.current().dsh_home / "skills/super-dev/SKILL.md":
            raise OSError("user file committed before target receipt")

    with monkeypatch.context() as context:
        context.setattr(managed_content, "atomic_write", fail_after_user_file)
        assert (
            cli._cmd_onboard(
                cli.parser.parse_args(["onboard", "--host", "dsh", "--yes", "--with-user-surfaces"])
            )
            == 1
        )
    assert HOST not in IntegrationManager(tmp_path).load_install_manifest()["targets"]
    capsys.readouterr()
    assert cli._cmd_uninstall(cli.parser.parse_args(["uninstall", "--host", "dsh", "--json"])) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["error_count"] == 0
    assert not (UserDirectoryContext.current().dsh_home / "skills/super-dev/SKILL.md").exists()
    assert not managed_content.ownership(tmp_path)


@pytest.mark.parametrize("host", REWORK02_LEGACY_HOSTS)
@pytest.mark.parametrize("newline", ["windows", "lf"])
@pytest.mark.parametrize("operation", ["reinstall", "remove"])
def test_rework02_all_legacy_block_consumers(tmp_path, host, newline, operation):
    manager, rules, outside = _rework02_legacy_install(tmp_path, host, newline)
    if operation == "reinstall":
        manager.setup(host, force=True)
    manager.remove(host)
    assert rules.read_bytes() == outside


@pytest.mark.parametrize(
    "host", ["codex", "codex-cli", "claude-code", "opencode", "qoder", "qoder-cli", "droid-cli"]
)
@pytest.mark.parametrize("newline", ["windows", "lf"])
def test_rework02_declared_legacy_user_blocks(tmp_path, host, newline):
    manager, rules, outside = _rework02_legacy_install(tmp_path, host, newline, global_scope=True)
    manager.setup_global_protocol(host, force=True)
    markers = (
        (manager.CLAUDE_RULES_BEGIN, manager.CLAUDE_RULES_END)
        if host == "claude-code"
        else manager._managed_agents_markers(host)
    )
    manager._remove_managed_block(file_path=rules, begin=markers[0], end=markers[1])
    assert rules.read_bytes() == outside


@pytest.mark.parametrize("host", REWORK02_LEGACY_HOSTS)
@pytest.mark.parametrize(
    "invalid", ["modified", "missing_receipt", "family", "scope", "path", "version"]
)
def test_rework02_legacy_proof_is_required(tmp_path, host, invalid):
    manager, rules, outside = _rework02_legacy_install(tmp_path, host)
    manifest_path = tmp_path / ".super-dev/install-manifest.json"
    payload = json.loads(manifest_path.read_bytes())
    if invalid == "modified":
        rules.write_bytes(rules.read_bytes().replace(b"Super Dev", b"User Modified Super Dev", 1))
    elif invalid == "missing_receipt":
        manifest_path.unlink()
    else:
        entry = payload["targets"][host]
        if invalid == "family":
            entry["family"] = "unknown"
        elif invalid == "scope":
            entry["scopes"] = {"project": False, "global": True}
        elif invalid == "path":
            entry["paths"] = [str(tmp_path / "unrelated.md")]
        else:
            payload["version"] = 999
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    before = rules.read_bytes()
    with pytest.raises(ValueError):
        manager.setup(host, force=True)
    with pytest.raises(ValueError):
        manager.remove(host)
    assert rules.read_bytes() == before


@pytest.mark.parametrize("operation", ["reinstall", "remove", "update"])
def test_rework02_windsurf_real_legacy_whole_layout(tmp_path, monkeypatch, operation):
    manager, rules, outside = _rework02_legacy_install(tmp_path, "windsurf")
    assert b"<!-- BEGIN SUPER DEV WINDSURF -->" not in rules.read_bytes()
    if operation == "reinstall":
        manager.setup("windsurf", force=True)
        assert rules.read_bytes().count(b"Super Dev Integration") <= 1
    elif operation == "update":
        snapshot = snapshot_hosts(tmp_path, include_user=False)
        assert not snapshot["issues"]
        original_builder = IntegrationManager._build_file_content

        def upgraded(instance, target, relative):
            body = original_builder(instance, target, relative)
            return (
                body + "\nNEW_WS_VERSION\n"
                if target == "windsurf" and relative == "AGENTS.md"
                else body
            )

        with monkeypatch.context() as context:
            context.setattr(IntegrationManager, "_build_file_content", upgraded)
            result = refresh_hosts(tmp_path, snapshot, include_user=False)
            assert not result["issues"]
            manager.setup("windsurf", force=True)
    manager.remove("windsurf")
    assert not rules.exists() or rules.read_bytes() == outside


@pytest.mark.parametrize(
    "relative", ["AGENTS.md", ".windsurf/rules/super-dev.md", ".windsurf/skills/super-dev/SKILL.md"]
)
def test_rework02_windsurf_modified_legacy_file_is_preserved(tmp_path, relative):
    manager, rules, outside = _rework02_legacy_install(tmp_path, "windsurf")
    modified = tmp_path / relative
    before = modified.read_bytes() + b"USER EDIT\r\n"
    modified.write_bytes(before)
    with pytest.raises(ValueError):
        manager.setup("windsurf", force=True)
    with pytest.raises(ValueError):
        manager.remove("windsurf")
    assert modified.read_bytes() == before


def _rework02_junction(link, target):
    command = Path(os.environ["SYSTEMROOT"]) / "System32/cmd.exe"
    result = subprocess.run(
        [str(command), "/d", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    info = link.lstat()
    assert info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    assert not link.is_symlink()
    return info


def _rework02_unlink_owned_junction(link, info):
    current = link.lstat()
    assert current.st_ino == info.st_ino
    assert current.st_reparse_tag == 0xA0000003
    os.rmdir(link)


@pytest.mark.skipif(os.name != "nt", reason="原生 Windows 目录连接点机制")
@pytest.mark.parametrize(
    "location", ["project_child", "project_root", "user_dsh", "home_root", "manifest", "dangling"]
)
def test_rework02_native_junction_install_is_rejected(tmp_path, location):
    project, target, home = tmp_path / "project", tmp_path / "owned-outside", tmp_path / "home"
    for directory in (project, target, home):
        directory.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_bytes(b"OWNED USER SENTINEL\r\n")
    rules = project / "AGENTS.local.md"
    rules.write_bytes(b"USER RULE BYTES\r\n")
    link = project / ".dsh"
    if location == "project_root":
        link = tmp_path / "project-link"
    elif location == "user_dsh":
        link = home / ".dsh"
    elif location == "home_root":
        link = tmp_path / "home-link"
    elif location == "manifest":
        link = project / ".super-dev"
    info = _rework02_junction(link, target / "missing-target" if location == "dangling" else target)
    try:
        with pytest.raises((ValueError, OSError)):
            if location == "home_root":
                UserDirectoryContext.from_home(link)
            elif location == "user_dsh":
                context = UserDirectoryContext.from_home(home, dsh_home=link)
                SkillManager(project, user_directories=context).install("super-dev", HOST)
            else:
                IntegrationManager(
                    link if location == "project_root" else project,
                    user_directories=UserDirectoryContext.from_home(home),
                ).setup(HOST)
        assert sorted(path.name for path in target.iterdir()) == ["sentinel.txt"]
        assert sentinel.read_bytes() == b"OWNED USER SENTINEL\r\n"
        assert rules.read_bytes() == b"USER RULE BYTES\r\n"
    finally:
        _rework02_unlink_owned_junction(link, info)


@pytest.mark.parametrize("kind", ["directory_reparse", "file_reparse", "symbolic"])
def test_rework02_link_metadata_is_checked_without_following(tmp_path, monkeypatch, kind):
    from super_dev.integrations.managed_content import plain_path

    node = tmp_path / "link-node"
    lstat = Path.lstat
    path_stat = Path.stat
    observed = []

    def metadata(path):
        if path == node:
            observed.append(path)
            return SimpleNamespace(
                st_mode=(
                    stat.S_IFLNK
                    if kind == "symbolic"
                    else (stat.S_IFDIR if kind == "directory_reparse" else stat.S_IFREG)
                ),
                st_file_attributes=0 if kind == "symbolic" else 0x400,
            )
        return lstat(path)

    def forbidden_follow(path, *arguments, **options):
        if path == node or node in path.parents:
            raise AssertionError("must not follow link target")
        return path_stat(path, *arguments, **options)

    with monkeypatch.context() as context:
        context.setattr(Path, "lstat", metadata)
        context.setattr(Path, "stat", forbidden_follow)
        with pytest.raises(ValueError, match="连接点|符号链接"):
            plain_path(node / "missing-child" / "SKILL.md")
    assert observed == [node]


@pytest.mark.skipif(os.name != "nt", reason="原生 Windows 目录连接点机制")
def test_rework02_native_junction_uninstall_preserves_target_and_project(tmp_path):
    project, target = tmp_path / "project", tmp_path / "outside"
    project.mkdir()
    target.mkdir()
    manager = IntegrationManager(project)
    manager.setup(HOST)
    rules = project / "AGENTS.local.md"
    before = rules.read_bytes()
    sentinel = target / "sentinel"
    sentinel.write_bytes(b"USER DATA\r\n")
    (project / ".dsh").rename(project / "original-owned-dsh")
    link = project / ".dsh"
    info = _rework02_junction(link, target)
    try:
        with pytest.raises(ValueError, match="连接点|符号链接"):
            manager.remove(HOST)
        assert rules.read_bytes() == before
        assert sentinel.read_bytes() == b"USER DATA\r\n"
        assert sorted(path.name for path in target.iterdir()) == ["sentinel"]
    finally:
        _rework02_unlink_owned_junction(link, info)


@pytest.mark.skipif(os.name != "nt", reason="原生 Windows 目录连接点机制")
def test_rework02_native_user_junction_update_is_rejected(tmp_path):
    project, target, home = tmp_path / "project", tmp_path / "outside", tmp_path / "home"
    for directory in (project, target, home):
        directory.mkdir()
    context = UserDirectoryContext.from_home(home)
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(UserDirectoryContext, "current", classmethod(lambda cls: context))
        IntegrationManager(project).setup(HOST)
        SkillManager(project).install("super-dev", HOST)
        snapshot = snapshot_hosts(project, include_user=True)
        sentinel = target / "sentinel"
        sentinel.write_bytes(b"USER DATA\r\n")
        context.dsh_home.rename(home / "original-owned-dsh")
        link = context.dsh_home
        info = _rework02_junction(link, target)
        try:
            with pytest.raises(ValueError, match="连接点|符号链接"):
                refresh_hosts(project, snapshot, include_user=True)
            assert sentinel.read_bytes() == b"USER DATA\r\n"
            assert sorted(path.name for path in target.iterdir()) == ["sentinel"]
        finally:
            _rework02_unlink_owned_junction(link, info)


@pytest.mark.skipif(os.name != "nt", reason="原生 Windows 目录连接点机制")
def test_rework02_native_junction_update_is_rejected(tmp_path):
    project, target = tmp_path / "project", tmp_path / "owned-outside"
    project.mkdir()
    target.mkdir()
    manager = IntegrationManager(project)
    manager.setup(HOST)
    snapshot = snapshot_hosts(project, include_user=False)
    for name in ("super-dev", "super-dev-seeai"):
        path = target / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_bytes((project / ".dsh/skills" / name / "SKILL.md").read_bytes())
    (target / "sentinel.txt").write_bytes(b"USER TARGET\r\n")
    before = {
        str(path.relative_to(target)): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }
    (project / ".dsh").rename(project / "original-owned-dsh")
    link = project / ".dsh"
    info = _rework02_junction(link, target)
    try:
        with pytest.raises((ValueError, OSError)):
            refresh_hosts(project, snapshot, include_user=False)
        assert {
            str(path.relative_to(target)): path.read_bytes()
            for path in target.rglob("*")
            if path.is_file()
        } == before
    finally:
        _rework02_unlink_owned_junction(link, info)
