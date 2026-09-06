from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from super_dev.extensions.executor import StructuredExecutor
from super_dev.extensions.models import CommandSpec, ExtensionStatus


def test_windows_job_rejects_other_platforms_before_loading_native_api(monkeypatch) -> None:
    from super_dev.extensions import executor

    monkeypatch.setattr(executor, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(OSError, match="仅适用于 Windows"):
        executor._WindowsJob()
    job = object.__new__(executor._WindowsJob)
    with pytest.raises(OSError, match="仅适用于 Windows"):
        job.assign(Mock())


def test_shell_characters_remain_plain_arguments(tmp_path: Path) -> None:
    result = StructuredExecutor(project_dir=tmp_path).run(
        CommandSpec(
            executable=Path(sys.executable),
            args=("-c", "import sys; print(sys.argv[1])", "a | b > c"),
            cwd=tmp_path,
        )
    )

    assert result.status == ExtensionStatus.PASS
    assert result.stdout.strip() == "a | b > c"


def test_blocked_script_suffix_is_not_executed(tmp_path: Path) -> None:
    script = tmp_path / "danger.cmd"
    script.write_text("echo bad", encoding="utf-8")

    result = StructuredExecutor(project_dir=tmp_path).run(
        CommandSpec(executable=script.resolve(), cwd=tmp_path)
    )

    assert result.status == ExtensionStatus.BLOCKED
    assert "禁止直接执行" in result.error


def test_working_directory_must_stay_inside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    result = StructuredExecutor(project_dir=project).run(
        CommandSpec(executable=Path(sys.executable), cwd=outside)
    )

    assert result.status == ExtensionStatus.BLOCKED
    assert "工作目录" in result.error


def test_output_is_redacted_and_truncated(tmp_path: Path) -> None:
    result = StructuredExecutor(project_dir=tmp_path).run(
        CommandSpec(
            executable=Path(sys.executable),
            args=("-c", "print('token=abc ' + 'x' * 4000)"),
            cwd=tmp_path,
            output_limit_bytes=1024,
        )
    )

    assert result.status == ExtensionStatus.PASS
    assert "abc" not in result.stdout
    assert "REDACTED" in result.stdout
    assert "output truncated" in result.stdout


def test_timeout_cleans_child_process_tree(tmp_path: Path) -> None:
    marker = tmp_path / "child-survived.txt"
    child_code = f"import time; time.sleep(1.5); open(r'{marker}', 'w').write('bad')"
    parent_code = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "time.sleep(10)"
    )
    result = StructuredExecutor(project_dir=tmp_path).run(
        CommandSpec(
            executable=Path(sys.executable),
            args=("-c", parent_code),
            cwd=tmp_path,
            timeout_seconds=1,
        )
    )
    time.sleep(1.0)

    assert result.status == ExtensionStatus.BLOCKED
    assert result.timed_out is True
    assert result.process_tree_clean is True
    assert not marker.exists()


def test_cancellation_cleans_process_tree(tmp_path: Path) -> None:
    cancel = threading.Event()
    timer = threading.Timer(0.2, cancel.set)
    timer.start()
    try:
        result = StructuredExecutor(project_dir=tmp_path).run(
            CommandSpec(
                executable=Path(sys.executable),
                args=("-c", "import time; time.sleep(10)"),
                cwd=tmp_path,
                timeout_seconds=5,
                cancel_event=cancel,
            )
        )
    finally:
        timer.cancel()

    assert result.status == ExtensionStatus.BLOCKED
    assert result.cancelled is True
    assert result.process_tree_clean is True


@pytest.mark.skipif(os.name == "nt", reason="POSIX signal semantics")
def test_posix_stubborn_grandchild_is_force_killed(tmp_path: Path) -> None:
    marker = tmp_path / "stubborn-child-survived.txt"
    child_code = (
        "import signal,time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"time.sleep(1.5); open(r'{marker}', 'w').write('bad')"
    )
    parent_code = (
        "import subprocess,sys,time; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "time.sleep(10)"
    )

    result = StructuredExecutor(project_dir=tmp_path).run(
        CommandSpec(
            executable=Path(sys.executable),
            args=("-c", parent_code),
            cwd=tmp_path,
            timeout_seconds=1,
        )
    )
    time.sleep(1.0)

    assert result.status == ExtensionStatus.BLOCKED
    assert result.process_tree_clean is True
    assert not marker.exists()
