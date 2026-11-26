"""The DSH companion observes only the bound project's committed Core state."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from super_dev.integrations import IntegrationManager
from super_dev.review_state import save_workflow_state
from super_dev.user_directories import UserDirectoryContext


def _install(project: Path) -> None:
    IntegrationManager(
        project, user_directories=UserDirectoryContext.from_home(project / "unused-home")
    ).setup("deepseek-harness")


def _tree(root: Path) -> dict[str, bytes]:
    return {
        name.relative_to(root).as_posix(): name.read_bytes()
        for name in root.rglob("*")
        if name.is_file()
    }


def _state(project: Path, flow: str, stage: str, *, binding: str = "bound") -> None:
    item = "current-work-item"
    active = item if binding == "bound" else ""
    if active:
        (project / ".super-dev" / "changes" / item).mkdir(parents=True)
    save_workflow_state(
        project,
        {
            "work_item_id": item,
            "artifact_prefix": item,
            "active_change_id": active,
            "binding_status": binding,
            "flow_variant": flow,
            "current_stage": stage,
            "status": "waiting_confirmation" if stage.endswith("_confirm") else "in_progress",
            "current_step_label": "OWNED_NOT_FOR_TOOL_OUTPUT",
            "host_continue_prompt": "OWNED_NOT_FOR_TOOL_OUTPUT",
        },
        expected_revision=0,
    )


@pytest.mark.parametrize(
    ("flow", "stage", "binding", "next_step"),
    [
        ("standard", "docs_confirm", "pre_spec", "review_documents"),
        ("standard", "preview_confirm", "bound", "review_preview"),
        ("seeai", "docs_confirm", "pre_spec", "review_documents"),
        ("seeai", "build_fullstack", "bound", "continue_existing"),
    ],
)
def test_reads_existing_stage_and_waits_without_acting(tmp_path, flow, stage, binding, next_step):
    from super_dev.integrations.dsh_plugin_snapshot import collect_snapshot

    _install(tmp_path)
    _state(tmp_path, flow, stage, binding=binding)
    before = _tree(tmp_path)

    result = collect_snapshot(tmp_path)

    assert result["checks"] == {"standard": "valid", "seeai": "valid", "rules": "valid"}
    assert result["workflow"] == {
        "state": "recorded",
        "flow": flow,
        "stage": stage,
        "work_item": "current-work-item",
        "revision": 1,
        "next": next_step,
    }
    assert "OWNED_NOT_FOR_TOOL_OUTPUT" not in json.dumps(result)
    assert _tree(tmp_path) == before


def test_diagnostic_only_reports_dedicated_project_inputs(tmp_path):
    from super_dev.integrations.dsh_plugin_snapshot import collect_snapshot

    _install(tmp_path)
    skill = tmp_path / ".dsh/skills/super-dev/SKILL.md"
    shared = tmp_path / ".agents/skills/super-dev/SKILL.md"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(skill.read_bytes() + b"OWNED_SHARED")
    skill.unlink()
    seeai = tmp_path / ".dsh/skills/super-dev-seeai/SKILL.md"
    seeai.write_bytes(seeai.read_bytes() + b"OWNED_EDIT")
    rules = tmp_path / "AGENTS.local.md"
    rules.write_bytes(rules.read_bytes().replace(b"END SUPER DEV DSH", b"END SUPER DEV OTHER"))
    before = _tree(tmp_path)

    result = collect_snapshot(tmp_path)

    assert result["outcome"] == "observed"
    assert result["checks"] == {"standard": "missing", "seeai": "modified", "rules": "modified"}
    assert result["workflow"]["state"] == "not_started"
    assert "OWNED_EDIT" not in json.dumps(result)
    assert "OWNED_SHARED" not in json.dumps(result)
    assert _tree(tmp_path) == before


@pytest.mark.parametrize("broken", ["corrupt", "missing"])
def test_does_not_read_old_workflow_when_primary_unavailable(tmp_path, broken):
    from super_dev.artifact_utils import resolve_work_item_identity
    from super_dev.integrations.dsh_plugin_snapshot import collect_snapshot

    _install(tmp_path)
    _state(tmp_path, "standard", "docs_confirm", binding="pre_spec")
    source = tmp_path / ".super-dev/workflow-state.json"
    assert (tmp_path / ".super-dev/workflow-history/latest.json").is_file()
    if broken == "corrupt":
        source.write_bytes(b"{corrupt")
    else:
        source.unlink()
    before = _tree(tmp_path)

    result = collect_snapshot(tmp_path)

    assert result["workflow"]["state"] == "invalid"
    assert not result["workflow"]["work_item"]
    assert not result["workflow"]["next"]
    # The existing Core caller still has its original recovery view. The
    # companion alone declines to display that fallback as the active task.
    assert resolve_work_item_identity(tmp_path).work_item_id == "current-work-item"
    assert _tree(tmp_path) == before


def test_mismatched_work_item_never_gets_resume_guidance(tmp_path):
    from super_dev.integrations.dsh_plugin_snapshot import collect_snapshot

    _state(tmp_path, "standard", "backend")
    source = tmp_path / ".super-dev/workflow-state.json"
    payload = json.loads(source.read_bytes())
    payload["active_change_id"] = "a-different-work-item"
    source.write_text(json.dumps(payload), encoding="utf-8")

    result = collect_snapshot(tmp_path)

    assert result["workflow"]["state"] == "invalid"
    assert not result["workflow"]["next"]


def test_other_directory_is_not_selected_and_unowned_rules_are_not_read(tmp_path):
    from super_dev.integrations.dsh_plugin_snapshot import collect_snapshot

    other = tmp_path / "other"
    other.mkdir()
    _install(other)
    _state(other, "standard", "backend")
    unrelated_rules = tmp_path / "AGENTS.local.md"
    unrelated_rules.write_bytes(b"OWNED_OTHER_RULES")
    before = _tree(tmp_path)

    result = collect_snapshot(tmp_path)

    assert result["outcome"] == "blocked" and result["reason"] == "not_setup"
    assert result["checks"]["rules"] == "unchecked"
    assert "current-work-item" not in json.dumps(result)
    assert _tree(tmp_path) == before


def test_symlink_or_reparse_failure_is_not_treated_as_ready(tmp_path, monkeypatch):
    from super_dev.integrations import dsh_plugin_snapshot as snapshot

    _install(tmp_path)
    original = snapshot.ensure_plain_path
    skill = tmp_path / ".dsh/skills/super-dev/SKILL.md"

    def check(path):
        if path == skill:
            raise ValueError("OWNED_REPARSE_ERROR_NOT_FOR_TOOL_OUTPUT")
        return original(path)

    monkeypatch.setattr(snapshot, "ensure_plain_path", check)
    result = snapshot.collect_snapshot(tmp_path)

    assert result["checks"]["standard"] == "unreadable"
    assert result["checks"]["seeai"] == "valid"
    assert "OWNED_REPARSE_ERROR_NOT_FOR_TOOL_OUTPUT" not in json.dumps(result)


@pytest.mark.skipif(os.name != "nt", reason="uses a real Windows directory junction")
def test_native_junction_does_not_allow_reading_another_projects_skill(tmp_path):
    from super_dev.integrations.dsh_plugin_snapshot import collect_snapshot

    project, other = tmp_path / "p", tmp_path / "q"
    project.mkdir()
    other.mkdir()
    _install(other)
    target = other / ".dsh/skills/super-dev"
    owned_bytes = (target / "SKILL.md").read_bytes()
    junction = project / ".dsh/skills/super-dev"
    junction.parent.mkdir(parents=True)
    command = Path(os.environ["SYSTEMROOT"]) / "System32/cmd.exe"
    result = subprocess.run(
        [str(command), "/d", "/c", "mklink", "/J", str(junction), str(target)],
        check=False,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    try:
        assert getattr(junction.lstat(), "st_file_attributes", 0) & 0x400
        assert collect_snapshot(project)["checks"]["standard"] == "unreadable"
        assert (target / "SKILL.md").read_bytes() == owned_bytes
    finally:
        if getattr(junction.lstat(), "st_file_attributes", 0) & 0x400:
            junction.rmdir()


def test_relative_or_parent_traversal_input_is_rejected(tmp_path):
    from super_dev.integrations.dsh_plugin_snapshot import collect_snapshot

    assert collect_snapshot(Path("not-an-absolute-project"))["reason"] == "workspace"
    assert collect_snapshot(tmp_path / ".." / tmp_path.name)["reason"] == "workspace"
