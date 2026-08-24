"""可注入的用户目录来源。

正常运行从当前进程环境解析目录；测试可以显式传入隔离目录，避免依赖
平台对 ``HOME``、``USERPROFILE`` 和 ``~`` 的不同解释。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserDirectoryContext:
    """提供当前用户相关目录，不携带测试或业务状态。"""

    home: Path
    codex_home: Path
    xdg_config_home: Path

    @classmethod
    def current(cls) -> UserDirectoryContext:
        """按当前进程的真实环境解析目录，保持现有默认行为。"""

        home = Path.home()
        codex_raw = os.getenv("CODEX_HOME", "").strip()
        xdg_raw = os.getenv("XDG_CONFIG_HOME", "").strip()
        return cls.from_home(
            home,
            codex_home=codex_raw or None,
            xdg_config_home=xdg_raw or None,
        )

    @classmethod
    def from_home(
        cls,
        home: Path,
        *,
        codex_home: str | Path | None = None,
        xdg_config_home: str | Path | None = None,
    ) -> UserDirectoryContext:
        """从一个明确的用户主目录构造上下文。"""

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
                context.expanduser(xdg_config_home)
                if xdg_config_home
                else context.xdg_config_home
            ),
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
