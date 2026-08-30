"""扩展写入路径守卫。"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path

from ..user_directories import UserDirectoryContext
from .models import ExtensionStatus, WriteSpec


def _identity(path: Path) -> str:
    identity = os.path.normcase(os.path.normpath(str(path.resolve(strict=False))))
    return identity.casefold() if os.name == "nt" else identity


def _within(root: Path, candidate: Path) -> bool:
    try:
        return os.path.commonpath([_identity(root), _identity(candidate)]) == _identity(root)
    except ValueError:
        return False


def _static_prefix(pattern: str) -> str:
    parts: list[str] = []
    for part in pattern.split("/"):
        if any(char in part for char in "*?["):
            break
        parts.append(part)
    return "/".join(parts)


def _relative_label(root: Path, candidate: Path) -> str | None:
    try:
        if os.name == "nt":
            relative = os.path.relpath(str(candidate), str(root))
            if relative == os.pardir or relative.startswith(os.pardir + os.sep):
                return None
            return relative.replace("\\", "/")
        return candidate.relative_to(root).as_posix()
    except ValueError:
        return None


@dataclass(frozen=True)
class PathDecision:
    status: ExtensionStatus
    resolved_path: Path
    reason: str

    @property
    def allowed(self) -> bool:
        return self.status == ExtensionStatus.PASS


class PathGuard:
    def __init__(
        self,
        project_dir: Path,
        writes: WriteSpec,
        *,
        user_directories: UserDirectoryContext | None = None,
        protected_user_surfaces: tuple[Path, ...] = (),
    ):
        self.project_dir = Path(project_dir).resolve()
        self.writes = writes
        self.user_directories = user_directories or UserDirectoryContext.current()
        defaults = (
            self.user_directories.codex_home,
            self.user_directories.xdg_config_home,
            self.user_directories.home / ".agents",
            self.user_directories.home / ".claude",
        )
        self.protected_user_surfaces = tuple(
            Path(item).resolve(strict=False) for item in (*defaults, *protected_user_surfaces)
        )
        self.permanent_forbidden = (
            self.project_dir / ".git",
            self.project_dir / ".super-dev" / "workflow-state.json",
        )

    def check_write(self, value: Path | str) -> PathDecision:
        raw = Path(value)
        candidate = (raw if raw.is_absolute() else self.project_dir / raw).resolve(strict=False)
        if not _within(self.project_dir, candidate):
            return PathDecision(ExtensionStatus.BLOCKED, candidate, "写入路径位于项目目录外")
        for forbidden in self.permanent_forbidden:
            if _within(forbidden, candidate):
                return PathDecision(ExtensionStatus.BLOCKED, candidate, "写入命中永久禁止路径")
        for surface in self.protected_user_surfaces:
            if _within(surface, candidate):
                return PathDecision(ExtensionStatus.BLOCKED, candidate, "写入命中用户级受保护位置")

        relative = _relative_label(self.project_dir, candidate)
        if relative is None:
            return PathDecision(
                ExtensionStatus.BLOCKED,
                candidate,
                "无法把写入路径安全地映射到项目相对路径",
            )
        match_relative = relative.casefold() if os.name == "nt" else relative
        for pattern in self.writes.forbidden:
            if pattern == "$USER_SURFACES/**":
                continue
            prefix = _static_prefix(pattern)
            if prefix and _within(self.project_dir / prefix, candidate):
                return PathDecision(
                    ExtensionStatus.BLOCKED, candidate, f"写入命中禁止范围: {pattern}"
                )
            match_pattern = pattern.casefold() if os.name == "nt" else pattern
            if fnmatch.fnmatchcase(match_relative, match_pattern):
                return PathDecision(
                    ExtensionStatus.BLOCKED, candidate, f"写入命中禁止范围: {pattern}"
                )

        for pattern in self.writes.allowed:
            prefix = _static_prefix(pattern)
            match_pattern = pattern.casefold() if os.name == "nt" else pattern
            if (
                prefix
                and _within(self.project_dir / prefix, candidate)
                and fnmatch.fnmatchcase(match_relative, match_pattern)
            ):
                return PathDecision(ExtensionStatus.PASS, candidate, "写入位于允许范围")
        return PathDecision(ExtensionStatus.BLOCKED, candidate, "写入不在清单允许范围")
