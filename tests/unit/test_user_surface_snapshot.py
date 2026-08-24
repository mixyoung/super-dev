import os
import subprocess
from pathlib import Path

import pytest

from super_dev.user_directories import UserDirectoryContext
from tests.support.user_surface_snapshot import (
    assert_safe_isolated_home,
    canonical_path,
    capture_user_surfaces,
    collect_user_surface_paths,
    diff_surface_snapshots,
    has_surface_changes,
    path_is_within,
    unsafe_surface_states,
)


def test_windows_canonical_path_folds_case_and_separators(tmp_path: Path):
    path = tmp_path / "Folder" / "File.txt"
    first = canonical_path(path, windows=True)
    second = canonical_path(Path(str(path).upper()), windows=True)

    assert first == second


def test_path_containment_rejects_sibling_prefix(tmp_path: Path):
    root = tmp_path / "safe"
    sibling = tmp_path / "safe-other"

    assert path_is_within(root / "child", root)
    assert not path_is_within(sibling, root)


@pytest.mark.skipif(os.name != "nt", reason="Windows drive semantics")
def test_path_containment_rejects_different_windows_drive():
    assert not path_is_within(Path("D:/outside"), Path("C:/safe"), windows=True)


def test_safe_home_must_stay_inside_run_root(tmp_path: Path):
    run_root = tmp_path / "run"
    run_root.mkdir()
    isolated = run_root / "home"
    real_home = tmp_path / "real-home"
    project = tmp_path / "project"

    assert_safe_isolated_home(
        isolated,
        real_home=real_home,
        project_dir=project,
        run_root=run_root,
    )
    with pytest.raises(ValueError):
        assert_safe_isolated_home(
            real_home,
            real_home=real_home,
            project_dir=project,
            run_root=run_root,
        )


def test_snapshot_detects_creation_and_content_change(tmp_path: Path):
    protected = tmp_path / "protected"
    before = capture_user_surfaces([protected])
    protected.mkdir()
    file_path = protected / "SKILL.md"
    file_path.write_text("first", encoding="utf-8")
    after_create = capture_user_surfaces([protected])

    create_diff = diff_surface_snapshots(before, after_create)
    assert has_surface_changes(create_diff)
    assert canonical_path(file_path) in create_diff["added"]

    file_path.write_text("second", encoding="utf-8")
    after_change = capture_user_surfaces([protected])
    content_diff = diff_surface_snapshots(after_create, after_change)
    assert canonical_path(file_path) in content_diff["changed"]

    file_path.unlink()
    after_delete = capture_user_surfaces([protected])
    delete_diff = diff_surface_snapshots(after_change, after_delete)
    assert canonical_path(file_path) in delete_diff["removed"]


def test_snapshot_does_not_follow_directory_symlink(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "secret.txt").write_text("not traversed", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink unavailable: {error}")

    states = capture_user_surfaces([link])
    assert len(states) == 1
    assert next(iter(states.values())).kind == "reparse-point"
    assert unsafe_surface_states(states)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction semantics")
def test_snapshot_does_not_follow_windows_junction(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "outside.txt").write_text("not traversed", encoding="utf-8")
    junction = tmp_path / "junction"
    completed = subprocess.run(  # nosec B603
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"junction unavailable: {completed.stderr or completed.stdout}")
    try:
        states = capture_user_surfaces([junction])
        assert len(states) == 1
        state = next(iter(states.values()))
        assert state.kind == "reparse-point"
        assert state.path_key == canonical_path(junction, follow_links=False)
    finally:
        junction.rmdir()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction semantics")
def test_snapshot_stops_at_junction_ancestor_when_target_is_missing(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    junction = tmp_path / "junction"
    completed = subprocess.run(  # nosec B603
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"junction unavailable: {completed.stderr or completed.stdout}")
    target.rmdir()
    try:
        states = capture_user_surfaces([junction / "nested" / "SKILL.md"])
        assert len(states) == 1
        state = next(iter(states.values()))
        assert state.kind == "reparse-point"
        assert state.path_key == canonical_path(junction, follow_links=False)
        assert unsafe_surface_states(states) == [state.path_key]
    finally:
        junction.rmdir()


def test_complete_surface_collection_includes_agents_and_external_codex(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    context = UserDirectoryContext.from_home(
        tmp_path / "home",
        codex_home=tmp_path / "external-codex",
    )

    paths = collect_user_surface_paths(project, context)
    keys = {canonical_path(path) for path in paths}

    assert canonical_path(context.codex_home / "AGENTS.md") in keys
    assert canonical_path(context.home / ".qoder" / "agents" / "super-dev.md") in keys
    assert canonical_path(context.home / "Documents" / "Cline" / "Rules" / "super-dev.md") in keys
    assert all(not path_is_within(path, project) for path in paths)
