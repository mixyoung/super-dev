"""不经过 Shell 的跨平台结构化命令执行器。"""

from __future__ import annotations

import ctypes
import hashlib
import os
import re
import signal
import subprocess  # nosec B404
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .models import CommandExecution, CommandSpec, ExtensionStatus

_BLOCKED_SUFFIXES = {".bat", ".cmd", ".ps1", ".sh", ".bash", ".zsh"}
_SAFE_ENV_KEYS = {
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
    "PYTHONUTF8",
    "PYTHONIOENCODING",
}
_SENSITIVE_RE = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key|credential)\b\s*[:=]\s*([^\s]+)"
)
_WINDOWS_JOB_WRAPPER = (
    "import subprocess,sys; "
    "signal_byte=sys.stdin.buffer.read(1); "
    "raise_code=125 if signal_byte != b'1' else "
    "subprocess.Popen(sys.argv[1:], stdin=subprocess.DEVNULL).wait(); "
    "raise SystemExit(raise_code)"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()}"


def _redact(text: str, explicit_values: tuple[str, ...] = ()) -> str:
    redacted = _SENSITIVE_RE.sub(lambda match: f"{match.group(1)}=***REDACTED***", text)
    for value in explicit_values:
        if value:
            redacted = redacted.replace(value, "***REDACTED***")
    return redacted


def _truncate(text: str, limit_bytes: int) -> str:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit_bytes:
        return text
    suffix = b"\n...[output truncated]"
    keep = max(0, limit_bytes - len(suffix))
    return (encoded[:keep] + suffix).decode("utf-8", errors="replace")


def _kill_process_group(pid: int, sig: int) -> None:
    killpg = getattr(os, "killpg", None)
    if killpg is None:
        raise OSError("当前平台不支持进程组终止")
    killpg(pid, sig)


def _terminate_process_group(pid: int) -> bool:
    try:
        _kill_process_group(pid, int(signal.SIGTERM))
    except ProcessLookupError:
        return True
    except OSError:
        return False
    time.sleep(0.1)
    try:
        _kill_process_group(pid, int(getattr(signal, "SIGKILL", signal.SIGTERM)))
    except ProcessLookupError:
        return True
    except OSError:
        return False
    # A just-killed POSIX process can remain visible as a zombie until its parent
    # is reaped below by ``communicate``.  ``killpg(..., 0)`` therefore reports a
    # false survivor even though SIGKILL has already stopped every group member.
    # Successful group-wide SIGKILL delivery is the portable cleanup guarantee;
    # the caller then reaps the direct child before returning the result.
    return True


class _JobBasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _JobIoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JobExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobBasicLimitInformation),
        ("IoInfo", _JobIoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _WindowsJob:
    _kernel32: ctypes.CDLL
    handle: int | None

    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("Windows Job Object 仅适用于 Windows")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32 = kernel32
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        kernel32.SetInformationJobObject.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint32,
        ]
        kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        kernel32.TerminateJobObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        self.handle = kernel32.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "无法创建 Windows Job Object")
        info = _JobExtendedLimitInformation()
        info.BasicLimitInformation.LimitFlags = self.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            self.handle,
            self.JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            error = ctypes.get_last_error()
            kernel32.CloseHandle(self.handle)
            self.handle = None
            raise OSError(error, "无法配置 Windows Job Object")

    def assign(self, process: subprocess.Popen[str]) -> None:
        if sys.platform != "win32":
            raise OSError("Windows Job Object 仅适用于 Windows")
        process_handle = ctypes.c_void_p(int(process._handle))  # type: ignore[attr-defined]
        if not self._kernel32.AssignProcessToJobObject(self.handle, process_handle):
            raise OSError(ctypes.get_last_error(), "无法把进程加入 Windows Job Object")

    def terminate(self) -> None:
        if self.handle:
            self._kernel32.TerminateJobObject(self.handle, 1)

    def close(self) -> None:
        if self.handle:
            self._kernel32.CloseHandle(self.handle)
            self.handle = None


class StructuredExecutor:
    def __init__(
        self,
        *,
        project_dir: Path,
        allowed_executables: set[Path] | frozenset[Path] | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.allowed_executables = {
            Path(item).resolve()
            for item in (allowed_executables or {Path(sys.executable).resolve()})
        }

    def _validate(self, spec: CommandSpec) -> tuple[Path, Path]:
        executable = Path(spec.executable)
        if executable.suffix.lower() in _BLOCKED_SUFFIXES:
            raise ValueError(f"禁止直接执行脚本类型: {executable.suffix.lower()}")
        if not executable.is_absolute():
            raise ValueError("executable 必须是已经解析的绝对路径")
        resolved_executable = executable.resolve()
        if resolved_executable.suffix.lower() in _BLOCKED_SUFFIXES:
            raise ValueError(f"禁止直接执行脚本类型: {resolved_executable.suffix.lower()}")
        if not resolved_executable.exists() or not resolved_executable.is_file():
            raise FileNotFoundError(f"可执行程序不存在: {resolved_executable}")
        if resolved_executable not in self.allowed_executables:
            raise ValueError(f"可执行程序不在 Core 白名单: {resolved_executable}")
        cwd = (spec.cwd or Path.cwd()).resolve()
        if not cwd.exists() or not cwd.is_dir():
            raise FileNotFoundError(f"工作目录不存在: {cwd}")
        try:
            inside_project = os.path.commonpath(
                [
                    os.path.normcase(str(self.project_dir)),
                    os.path.normcase(str(cwd)),
                ]
            ) == os.path.normcase(str(self.project_dir))
        except ValueError:
            inside_project = False
        if not inside_project:
            raise ValueError("工作目录必须位于当前项目内")
        if not isinstance(spec.timeout_seconds, int) or not (1 <= spec.timeout_seconds <= 3600):
            raise ValueError("timeout_seconds 必须是 1-3600 的整数")
        if spec.output_limit_bytes < 1024:
            raise ValueError("output_limit_bytes 不能小于 1024")
        return resolved_executable, cwd

    @staticmethod
    def _environment(spec: CommandSpec) -> dict[str, str]:
        allowed = _SAFE_ENV_KEYS | set(spec.env_allowlist)
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        for key, value in spec.env.items():
            upper = key.upper()
            if upper not in allowed and not upper.startswith("SUPER_DEV_"):
                raise ValueError(f"环境变量不在白名单: {key}")
            env[key] = value
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        return env

    def run(self, spec: CommandSpec) -> CommandExecution:
        started_at = _utc_now()
        started = time.monotonic()
        executable_label = str(spec.executable)
        cwd_label = str(spec.cwd or self.project_dir)
        try:
            executable, cwd = self._validate(spec)
            env = self._environment(spec)
        except (OSError, ValueError) as exc:
            finished_at = _utc_now()
            return CommandExecution(
                status=ExtensionStatus.BLOCKED,
                executable=executable_label,
                args=tuple(spec.args),
                cwd=cwd_label,
                exit_code=None,
                stdout="",
                stderr="",
                stdout_digest=_digest(""),
                stderr_digest=_digest(""),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=(time.monotonic() - started) * 1000,
                timed_out=False,
                cancelled=False,
                process_tree_clean=True,
                error=str(exc),
            )

        command = [str(executable), *spec.args]
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        process: subprocess.Popen[str] | None = None
        job: _WindowsJob | None = None
        timed_out = False
        cancelled = False
        process_tree_clean = True
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        error = ""
        try:
            if os.name == "nt":
                job = _WindowsJob()
            if os.name == "nt":
                wrapped_command = [
                    sys.executable,
                    "-c",
                    _WINDOWS_JOB_WRAPPER,
                    *command,
                ]
                process = subprocess.Popen(  # nosec B603
                    wrapped_command,
                    cwd=str(cwd),
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=creationflags,
                )
            else:
                process = subprocess.Popen(  # nosec B603
                    command,
                    cwd=str(cwd),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    start_new_session=True,
                )
            if job is not None:
                try:
                    job.assign(process)
                    if process.stdin is None:
                        raise OSError("Windows 受信启动器没有同步输入管道")
                    process.stdin.write("1")
                    process.stdin.flush()
                    process.stdin.close()
                    process.stdin = None
                except OSError:
                    process.kill()
                    process.wait(timeout=5)
                    raise
            deadline = time.monotonic() + spec.timeout_seconds
            while True:
                if spec.cancel_event is not None and spec.cancel_event.is_set():
                    cancelled = True
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                try:
                    stdout, stderr = process.communicate(timeout=min(0.1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            if timed_out or cancelled:
                if job is not None:
                    job.terminate()
                else:
                    process_tree_clean = _terminate_process_group(process.pid)
                try:
                    tail_out, tail_err = process.communicate(timeout=5)
                    stdout = (stdout or "") + (tail_out or "")
                    stderr = (stderr or "") + (tail_err or "")
                except subprocess.TimeoutExpired:
                    process_tree_clean = False
                    process.kill()
                    tail_out, tail_err = process.communicate()
                    stdout = (stdout or "") + (tail_out or "")
                    stderr = (stderr or "") + (tail_err or "")
            exit_code = process.returncode
        except (OSError, ValueError) as exc:
            error = str(exc)
            process_tree_clean = process is None or process.poll() is not None
            if process is not None and process.poll() is None:
                try:
                    if job is not None:
                        job.terminate()
                    else:
                        process_tree_clean = _terminate_process_group(process.pid)
                    process.wait(timeout=5)
                    if job is not None:
                        process_tree_clean = True
                except (OSError, subprocess.TimeoutExpired):
                    process_tree_clean = False
        finally:
            if job is not None:
                job.close()

        sensitive_values = tuple(
            value
            for key, value in spec.env.items()
            if any(token in key.lower() for token in ("token", "secret", "password", "key"))
        )
        raw_stdout = stdout or ""
        raw_stderr = stderr or ""
        safe_stdout = _redact(raw_stdout, sensitive_values)
        safe_stderr = _redact(raw_stderr, sensitive_values)
        finished_at = _utc_now()
        if error or not process_tree_clean:
            status = ExtensionStatus.BLOCKED
        elif timed_out:
            status = ExtensionStatus.BLOCKED
            error = f"命令执行超时 ({spec.timeout_seconds}s)"
        elif cancelled:
            status = ExtensionStatus.BLOCKED
            error = "命令执行已取消，完整进程树已经停止"
        elif exit_code == 0:
            status = ExtensionStatus.PASS
        else:
            status = ExtensionStatus.FAIL
        return CommandExecution(
            status=status,
            executable=str(executable),
            args=tuple(spec.args),
            cwd=str(cwd),
            exit_code=exit_code,
            stdout=_truncate(safe_stdout, spec.output_limit_bytes),
            stderr=_truncate(safe_stderr, spec.output_limit_bytes),
            stdout_digest=_digest(safe_stdout),
            stderr_digest=_digest(safe_stderr),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(time.monotonic() - started) * 1000,
            timed_out=timed_out,
            cancelled=cancelled,
            process_tree_clean=process_tree_clean,
            error=error,
        )
