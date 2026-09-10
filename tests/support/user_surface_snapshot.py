"""测试会话对真实用户级接入面的只读保护。"""

from __future__ import annotations

import hashlib
import ntpath
import os
import stat as stat_module
from dataclasses import asdict, dataclass
from pathlib import Path

from super_dev.integrations import IntegrationManager
from super_dev.skills import SkillManager
from super_dev.user_directories import UserDirectoryContext

MAX_DIGEST_BYTES = 1024 * 1024
SENSITIVE_NAME_PARTS = ("credential", "secret", "token", "auth.json", "api_key")


def canonical_path(
    path: Path,
    *,
    windows: bool | None = None,
    follow_links: bool = True,
) -> str:
    """生成稳定比较键；Windows 额外统一分隔符、盘符和大小写。"""

    resolved = (
        Path(path).resolve(strict=False) if follow_links else Path(os.path.abspath(os.fspath(path)))
    )
    is_windows = os.name == "nt" if windows is None else windows
    raw = str(resolved)
    if is_windows:
        return ntpath.normcase(ntpath.normpath(raw)).casefold()
    return os.path.normpath(raw)


def path_is_within(path: Path, root: Path, *, windows: bool | None = None) -> bool:
    """使用路径语义判断包含关系，不使用字符串前缀。"""

    path_key = canonical_path(path, windows=windows)
    root_key = canonical_path(root, windows=windows)
    is_windows = os.name == "nt" if windows is None else windows
    try:
        common = (
            ntpath.commonpath([path_key, root_key])
            if is_windows
            else os.path.commonpath([path_key, root_key])
        )
        return common == root_key
    except ValueError:
        return False


def assert_safe_isolated_home(
    isolated_home: Path,
    *,
    real_home: Path,
    project_dir: Path,
    run_root: Path,
) -> None:
    """拒绝真实用户目录、仓库、磁盘根和运行根之外的隔离目录。"""

    isolated = Path(isolated_home).resolve(strict=False)
    forbidden = {
        canonical_path(real_home),
        canonical_path(project_dir),
        canonical_path(Path(isolated.anchor)),
    }
    if canonical_path(isolated) in forbidden:
        raise ValueError(f"unsafe isolated home: {isolated}")
    if not path_is_within(isolated, run_root):
        raise ValueError(f"isolated home escapes run root: {isolated}")


def collect_user_surface_paths(
    project_dir: Path,
    user_directories: UserDirectoryContext,
) -> list[Path]:
    """从产品现有完整入口生成所有非项目用户级保护位置。"""

    project = Path(project_dir).resolve()
    paths: dict[str, Path] = {}

    def add(path: Path) -> None:
        candidate = Path(path)
        if path_is_within(candidate, project):
            return
        paths.setdefault(canonical_path(candidate, follow_links=False), candidate)

    def add_skill_targets(target: str, root: Path) -> None:
        names = {
            *SkillManager.managed_builtin_skill_names(target),
            *SkillManager.legacy_cleanup_skill_names(),
        }
        for name in names:
            add(root / name)

    for target, raw in SkillManager.OFFICIAL_TARGET_PATHS.items():
        add_skill_targets(target, user_directories.expanduser(raw))
    for target, raw in SkillManager.OBSERVED_TARGET_PATHS.items():
        add_skill_targets(target, user_directories.expanduser(raw))
    for target, mirrors in SkillManager.COMPATIBILITY_MIRROR_PATHS.items():
        for raw in mirrors:
            root = (
                user_directories.codex_home / "skills"
                if target in {"codex", "codex-cli"}
                else user_directories.expanduser(raw)
            )
            add_skill_targets(target, root)

    manager = IntegrationManager(project, user_directories=user_directories)
    for target in manager.TARGETS:
        for path in manager.collect_managed_surface_paths(
            target,
            include_user_surfaces=True,
        ).values():
            add(path)
        groups = manager.surface_path_groups(target=target)
        for group in ("official_user", "optional_user", "compatibility"):
            for path in groups[group].values():
                add(path)
        readiness = manager.readiness_surface_sets(target=target)
        for group in (
            "official_user",
            "optional_user",
            "compatibility",
            "official_skill",
            "optional_skill",
            "compatibility_skill",
            "optional_slash",
            "compatibility_slash",
        ):
            for path in readiness[group]:
                add(path)

    return [paths[key] for key in sorted(paths)]


@dataclass(frozen=True)
class SurfaceState:
    path_key: str
    kind: str
    size: int | None = None
    mtime_ns: int | None = None
    digest: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _is_sensitive(path: Path) -> bool:
    lowered = path.name.casefold()
    return any(part in lowered for part in (*SENSITIVE_NAME_PARTS, ".env", "id_rsa", ".netrc"))


def _is_reparse_or_link(stat_result: os.stat_result) -> bool:
    if stat_module.S_ISLNK(stat_result.st_mode):
        return True
    attributes = int(getattr(stat_result, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def _first_reparse_or_link(path: Path) -> Path | None:
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            stat_result = current.lstat()
        except FileNotFoundError:
            return None
        except OSError:
            return current
        if _is_reparse_or_link(stat_result):
            return current
    return None


def _file_digest(path: Path, size: int) -> str | None:
    if size > MAX_DIGEST_BYTES or _is_sensitive(path):
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture_path(path: Path, states: dict[str, SurfaceState]) -> None:
    try:
        stat = path.lstat()
    except FileNotFoundError:
        key = canonical_path(path, follow_links=False)
        states[key] = SurfaceState(path_key=key, kind="missing")
        return
    except OSError as error:
        key = canonical_path(path, follow_links=False)
        states[key] = SurfaceState(
            path_key=key,
            kind="unreadable",
            error=f"{type(error).__name__}: {error}",
        )
        return

    is_reparse = _is_reparse_or_link(stat)
    key = canonical_path(path, follow_links=not is_reparse)
    if is_reparse:
        states[key] = SurfaceState(
            path_key=key,
            kind="reparse-point",
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
        )
        return
    if path.is_file():
        states[key] = SurfaceState(
            path_key=key,
            kind="file",
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            digest=_file_digest(path, stat.st_size),
        )
        return

    states[key] = SurfaceState(
        path_key=key,
        kind="directory",
        mtime_ns=stat.st_mtime_ns,
    )
    try:
        with os.scandir(path) as entries:
            for entry in sorted(entries, key=lambda item: item.name.casefold()):
                _capture_path(Path(entry.path), states)
    except OSError as error:
        states[key] = SurfaceState(
            path_key=key,
            kind="unreadable",
            mtime_ns=stat.st_mtime_ns,
            error=f"{type(error).__name__}: {error}",
        )


def capture_user_surfaces(paths: list[Path]) -> dict[str, SurfaceState]:
    states: dict[str, SurfaceState] = {}
    for path in paths:
        boundary = _first_reparse_or_link(path)
        _capture_path(boundary or path, states)
    return states


def unsafe_surface_states(states: dict[str, SurfaceState]) -> list[str]:
    return sorted(
        key for key, state in states.items() if state.kind in {"reparse-point", "unreadable"}
    )


def diff_surface_snapshots(
    before: dict[str, SurfaceState],
    after: dict[str, SurfaceState],
) -> dict[str, list[str]]:
    before_keys = set(before)
    after_keys = set(after)
    return {
        "added": sorted(after_keys - before_keys),
        "removed": sorted(before_keys - after_keys),
        "changed": sorted(key for key in before_keys & after_keys if before[key] != after[key]),
    }


def has_surface_changes(diff: dict[str, list[str]]) -> bool:
    return any(diff.values())
