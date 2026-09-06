"""Resolve the Bash runtime used by existing Bash command contracts."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def resolve_bash() -> str:
    """Prefer native Git Bash on Windows, never the WSL launcher shim."""
    if sys.platform == "win32":
        git = shutil.which("git")
        if git:
            for root in list(Path(git).resolve().parents)[:3]:
                for relative in ("bin/bash.exe", "usr/bin/bash.exe"):
                    candidate = root / relative
                    if candidate.is_file():
                        return str(candidate)
    bash = shutil.which("bash")
    if bash and not (
        sys.platform == "win32" and Path(bash).parent.name.lower() in {"system32", "sysnative"}
    ):
        return bash
    raise FileNotFoundError("未找到可用的 Bash；Windows 的 Bash 命令需要 Git Bash")
