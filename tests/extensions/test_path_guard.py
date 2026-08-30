from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from super_dev.extensions.models import ExtensionStatus, WriteSpec
from super_dev.extensions.path_guard import PathGuard
from super_dev.user_directories import UserDirectoryContext


def _guard(tmp_path: Path) -> PathGuard:
    project = tmp_path / "project"
    project.mkdir()
    user = UserDirectoryContext.from_home(tmp_path / "isolated-user")
    return PathGuard(
        project,
        WriteSpec(
            allowed=(".super-dev/extensions/runs/**",),
            forbidden=(".git/**", ".super-dev/workflow-state.json", "$USER_SURFACES/**"),
        ),
        user_directories=user,
    )


def test_allows_only_extension_run_evidence(tmp_path: Path) -> None:
    guard = _guard(tmp_path)

    allowed = guard.check_write(".super-dev/extensions/runs/abc/result.json")
    denied = guard.check_write("src/production.py")

    assert allowed.status == ExtensionStatus.PASS
    assert denied.status == ExtensionStatus.BLOCKED


def test_allows_chinese_and_space_in_run_path(tmp_path: Path) -> None:
    project = tmp_path / "项目 空格"
    project.mkdir()
    user = UserDirectoryContext.from_home(tmp_path / "isolated-user")
    guard = PathGuard(
        project,
        WriteSpec(
            allowed=(".super-dev/extensions/runs/**",),
            forbidden=(".git/**", ".super-dev/workflow-state.json"),
        ),
        user_directories=user,
    )

    decision = guard.check_write(".super-dev/extensions/runs/中文 记录/result.json")

    assert decision.status == ExtensionStatus.PASS


def test_rejects_project_escape_and_permanent_paths(tmp_path: Path) -> None:
    guard = _guard(tmp_path)

    assert guard.check_write("../outside.txt").status == ExtensionStatus.BLOCKED
    assert guard.check_write(".git/config").status == ExtensionStatus.BLOCKED
    assert guard.check_write(".super-dev/workflow-state.json").status == ExtensionStatus.BLOCKED


def test_rejects_symlink_escape_when_supported(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    runs = guard.project_dir / ".super-dev" / "extensions" / "runs"
    runs.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = runs / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        return

    decision = guard.check_write(link / "result.json")

    assert decision.status == ExtensionStatus.BLOCKED


@pytest.mark.skipif(os.name != "nt", reason="Windows junction semantics")
def test_rejects_windows_junction_escape(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    runs = guard.project_dir / ".super-dev" / "extensions" / "runs"
    runs.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    junction = runs / "junction"
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"junction unavailable: {completed.stderr or completed.stdout}")
    try:
        assert guard.check_write(junction / "result.json").status == ExtensionStatus.BLOCKED
    finally:
        junction.rmdir()


@pytest.mark.skipif(os.name != "nt", reason="Windows UNC and drive semantics")
@pytest.mark.parametrize("path", [r"\\server\share\result.json", r"Z:\outside\result.json"])
def test_rejects_unc_and_different_drive(tmp_path: Path, path: str) -> None:
    guard = _guard(tmp_path)

    assert guard.check_write(path).status == ExtensionStatus.BLOCKED


@pytest.mark.skipif(os.name != "nt", reason="Windows case-insensitive paths")
def test_windows_case_variant_does_not_raise(tmp_path: Path) -> None:
    guard = _guard(tmp_path)
    target = guard.project_dir / ".super-dev" / "extensions" / "runs" / "abc" / "result.json"
    case_variant = Path(str(target).swapcase())

    decision = guard.check_write(case_variant)

    assert decision.status == ExtensionStatus.PASS
