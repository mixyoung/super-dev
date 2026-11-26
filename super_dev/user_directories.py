"""可注入的用户目录来源。

正常运行从当前进程环境解析目录；测试可以显式传入隔离目录，避免依赖
平台对 ``HOME``、``USERPROFILE`` 和 ``~`` 的不同解释。
"""

from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


def ensure_plain_path(path: Path) -> None:
    absolute = Path(path).absolute()
    for candidate in (*reversed(absolute.parents), absolute):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError(f"拒绝连接点或符号链接，保留原路径：{path}")


@dataclass(frozen=True)
class UserDirectoryContext:
    """提供当前用户相关目录，不携带测试或业务状态。"""

    home: Path
    codex_home: Path
    xdg_config_home: Path
    dsh_home: Path | None = None

    def __post_init__(self) -> None:
        if self.dsh_home is None:
            object.__setattr__(self, "dsh_home", self.home / ".dsh")

    @classmethod
    def current(cls) -> UserDirectoryContext:
        """按当前进程的真实环境解析目录，保持现有默认行为。"""

        explicit_home = os.getenv("HOME", "").strip()
        home = Path(explicit_home) if explicit_home else Path.home()
        codex_raw = os.getenv("CODEX_HOME", "").strip()
        xdg_raw = os.getenv("XDG_CONFIG_HOME", "").strip()
        dsh_raw = os.getenv("DSH_HOME", "").strip()
        return cls.from_home(
            home,
            codex_home=codex_raw or None,
            xdg_config_home=xdg_raw or None,
            dsh_home=dsh_raw or None,
        )

    @classmethod
    def from_home(
        cls,
        home: Path,
        *,
        codex_home: str | Path | None = None,
        xdg_config_home: str | Path | None = None,
        dsh_home: str | Path | None = None,
    ) -> UserDirectoryContext:
        """从一个明确的用户主目录构造上下文。"""

        ensure_plain_path(Path(home))
        resolved_home = Path(home).resolve()
        context = cls(
            home=resolved_home,
            codex_home=resolved_home / ".codex",
            xdg_config_home=resolved_home / ".config",
        )
        return cls(
            home=resolved_home,
            codex_home=context.expanduser(codex_home) if codex_home else context.codex_home,
            xdg_config_home=(
                context.expanduser(xdg_config_home) if xdg_config_home else context.xdg_config_home
            ),
            dsh_home=context.expanduser(dsh_home) if dsh_home else resolved_home / ".dsh",
        )

    def expanduser(self, value: str | Path) -> Path:
        """只针对当前用户展开 ``~``，不回退到进程的真实主目录。"""

        raw = os.fspath(value)
        if raw == "~":
            return self.home
        if raw.startswith(("~/", "~\\")):
            relative = raw[2:].replace("\\", os.sep).replace("/", os.sep)
            return self.home / relative
        return Path(raw)

    def environment(self, base: Mapping[str, str] | None = None) -> dict[str, str]:
        """返回可传给测试进程的完整隔离环境。"""

        env = dict(os.environ if base is None else base)
        home = str(self.home)
        env.update(
            {
                "HOME": home,
                "USERPROFILE": home,
                "CODEX_HOME": str(self.codex_home),
                "DSH_HOME": str(self.dsh_home),
                "XDG_CONFIG_HOME": str(self.xdg_config_home),
                "XDG_DATA_HOME": str(self.home / ".local" / "share"),
                "XDG_CACHE_HOME": str(self.home / ".cache"),
                "XDG_STATE_HOME": str(self.home / ".local" / "state"),
                "APPDATA": str(self.home / "AppData" / "Roaming"),
                "LOCALAPPDATA": str(self.home / "AppData" / "Local"),
            }
        )
        drive = self.home.drive
        if drive:
            home_path = home[len(drive) :] or os.sep
            env["HOMEDRIVE"] = drive
            env["HOMEPATH"] = home_path
        return env
