"""启动时版本检查（非阻塞，24 小时缓存）。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import __version__
from .release_channel import CHANNEL, latest_release

_CACHE_TTL = 86400  # 24 小时


def _cache_file() -> Path:
    # Resolve per call so an isolated host/test context cannot inherit a real-user path.
    return Path.home() / ".super-dev" / ".version-cache"


def check_for_update() -> str | None:
    """检查本 fork GitHub 稳定发布是否有更新版本。

    返回提示字符串（如有更新）或 None。
    绝不阻塞、绝不抛出异常。
    """
    try:
        cached = _read_cache()
        if cached is not None:
            return _build_hint(cached)

        latest = _fetch_latest()
        if latest is None:
            return None

        _write_cache(latest)
        return _build_hint(latest)
    except Exception:  # pragma: no cover - 绝不失败
        return None


def _read_cache() -> str | None:
    """读取缓存，如果有效则返回最新版本号。"""
    try:
        cache = _cache_file()
        if not cache.exists():
            return None
        data = json.loads(cache.read_text(encoding="utf-8"))
        if data.get("source") == CHANNEL and 0 <= time.time() - data.get("ts", 0) < _CACHE_TTL:
            version = data.get("version")
            return version if isinstance(version, str) else None
    except Exception:
        pass
    return None


def _write_cache(version: str) -> None:
    """写入版本缓存。"""
    try:
        cache = _cache_file()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps({"source": CHANNEL, "version": version, "ts": time.time()}),
            encoding="utf-8",
        )
    except Exception:
        pass


def _fetch_latest() -> str | None:
    """从与 update 相同的固定发布源获取版本号。"""
    try:
        return latest_release(timeout=3).version
    except Exception:
        return None


def _build_hint(latest: str) -> str | None:
    """如果 latest 比当前版本更新，返回提示字符串。"""
    if latest and latest != __version__ and _is_newer(latest, __version__):
        return f"Super Dev {latest} 可用，运行 super-dev update 一键升级"
    return None


def _is_newer(latest: str, current: str) -> bool:
    """简单版本比较（支持 x.y.z 格式）。"""
    try:

        def _parts(v: str) -> tuple[int, ...]:
            return tuple(int(x) for x in v.split(".")[:3])

        return _parts(latest) > _parts(current)
    except Exception:
        return False
