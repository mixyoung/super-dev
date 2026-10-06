"""Invocation-local file discovery for quality checks, never a quality-result cache."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import stat
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from typing import Any, Concatenate, NoReturn, ParamSpec, TypeVar

# Only the intersection of the consumers' exclusions may be pruned globally.
# In particular .next, .nuxt and coverage still belong to some consumers.
_COMMON_EXCLUDED = frozenset(
    {
        ".git",
        ".super-dev",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "build",
        "dist",
        "output",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
)


def _path_names(paths: Iterable[Path]) -> set[str]:
    # WindowsPath equality folds case; spelling changes still invalidate evidence.
    return {str(path) for path in paths}


class SourceScanError(RuntimeError):
    """Required input could not be inspected completely or consistently."""


class SourceInventory:
    def __init__(self, project_dir: Path, ignored_dirs: frozenset[str] | None = None):
        self._input_root = Path(project_dir).absolute()
        self.project_dir = self._input_root
        self.errors: list[str] = []
        try:
            self.project_dir = self._input_root.resolve()
        except (OSError, RuntimeError) as exc:
            self.fail(self._input_root, f"无法规范化项目根（{type(exc).__name__}）")
        self.ignored_dirs = _COMMON_EXCLUDED if ignored_dirs is None else ignored_dirs
        self._files: tuple[Path, ...] | None = None
        self._directories: tuple[Path, ...] = ()
        self._digests: dict[Path, str] = {}
        self._writes: dict[Path, str] = {}
        self._glob_results: dict[tuple[tuple[str, ...], bool], tuple[Path, ...]] = {}
        self._selections: dict[str, tuple[tuple[Path, ...], Callable[[], list[Path]]]] = {}
        self._candidate_digest: str | None = None
        self.discovery_count = 0

    def fail(self, path: Path, reason: str) -> NoReturn:
        try:
            label = path.relative_to(self.project_dir).as_posix() or "."
        except ValueError:
            label = "<项目外路径>"
        message = f"受阻（BLOCKED）：扫描未完成；{label}：{reason}"
        if message not in self.errors:
            self.errors.append(message)
        raise SourceScanError(message)

    def _safe_path(self, path: Path, *, allow_missing: bool = False) -> Path:
        path = Path(path).absolute()
        anchor = next(
            (root for root in (self.project_dir, self._input_root) if path.is_relative_to(root)),
            Path(path.anchor),
        )
        current = anchor
        # Walk from the trusted root (or drive for an alias) before resolving:
        # checking a leaf first would already follow links in its parents.
        for part in ("", *path.relative_to(anchor).parts):
            current = current.parent if part == ".." else current / part
            try:
                metadata = current.lstat()
            except FileNotFoundError as exc:
                if allow_missing:
                    continue
                self.fail(current, f"无法读取路径信息（{type(exc).__name__}）")
            except OSError as exc:
                self.fail(current, f"无法读取路径信息（{type(exc).__name__}）")
            if stat.S_ISLNK(metadata.st_mode) or (
                getattr(metadata, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            ):
                self.fail(current, "不跟随符号链接或目录连接点")
        try:
            resolved = current.resolve()
        except (OSError, RuntimeError) as exc:
            self.fail(current, f"无法规范化路径（{type(exc).__name__}）")
        if not resolved.is_relative_to(self.project_dir):
            self.fail(resolved, "路径超出当前项目")
        return resolved

    def _discover(self) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
        self.discovery_count += 1
        files: list[Path] = []
        directories: list[Path] = []
        pending = [self.project_dir]
        while pending:
            directory = self._safe_path(pending.pop())
            try:
                with os.scandir(directory) as stream:
                    entries = list(stream)
            except OSError as exc:
                self.fail(directory, f"无法枚举目录（{type(exc).__name__}）")
            children: list[Path] = []
            for entry in entries:
                path = Path(entry.path)
                try:
                    is_directory = entry.is_dir(follow_symlinks=False)
                except OSError as exc:
                    self.fail(path, f"无法识别文件类型（{type(exc).__name__}）")
                if (is_directory or entry.is_symlink()) and (
                    entry.name in self.ignored_dirs or entry.name.lower().endswith(".egg-info")
                ):
                    continue
                path = self._safe_path(path)
                try:
                    if is_directory:
                        directories.append(path)
                        children.append(path)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(path)
                except OSError as exc:
                    self.fail(path, f"无法识别文件类型（{type(exc).__name__}）")
            pending.extend(reversed(children))
        return tuple(files), tuple(directories)

    @property
    def files(self) -> tuple[Path, ...]:
        if self._files is None:
            self._files, self._directories = self._discover()
        return self._files

    def select(self, extensions: set[str] | frozenset[str], ignored: frozenset[str]) -> list[Path]:
        return [
            path
            for path in self.files
            if path.suffix in extensions
            and not any(
                part in ignored or part.lower().endswith(".egg-info")
                for part in path.relative_to(self.project_dir).parts
            )
        ]

    def _digest(self, path: Path) -> tuple[Path, str]:
        path = self._safe_path(path)
        try:
            if not stat.S_ISREG(path.lstat().st_mode):
                self.fail(path, "应检输入不是普通文件")
            return path, hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            self.fail(path, f"无法读取应检文件（{type(exc).__name__}）")
        raise AssertionError("unreachable")

    def track(self, paths: list[Path]) -> None:
        for path in paths:
            path, digest = self._digest(path)
            if path in self._digests and self._digests[path] != digest:
                self.fail(path, "检查期间文件内容发生变化")
            self._digests[path] = digest

    def read_text(self, path: Path, *, errors: str = "ignore") -> str:
        path = self._safe_path(path)
        self.track([path])
        try:
            content = path.read_text(encoding="utf-8", errors=errors)
        except (OSError, UnicodeError) as exc:
            self.fail(path, f"无法读取应检文件（{type(exc).__name__}）")
        self.track([path])
        return content

    def _direct_glob(self, parts: tuple[str, ...], *, directories_only: bool) -> list[Path]:
        matches = [self.project_dir]
        for index, pattern in enumerate(parts):
            next_matches: list[Path] = []
            for directory in matches:
                directory = self._safe_path(directory)
                try:
                    with os.scandir(directory) as stream:
                        entries = list(stream)
                except OSError as exc:
                    self.fail(directory, f"无法枚举必要目录（{type(exc).__name__}）")
                for entry in entries:
                    if not _glob_match((entry.name,), (pattern,)):
                        continue
                    path = self._safe_path(Path(entry.path))
                    try:
                        if index < len(parts) - 1 or directories_only:
                            if not entry.is_dir(follow_symlinks=False):
                                continue
                    except OSError as exc:
                        self.fail(path, f"无法识别文件类型（{type(exc).__name__}）")
                    next_matches.append(path)
            matches = next_matches
        return matches

    def _pattern(self, pattern: str) -> tuple[tuple[str, ...], bool]:
        absolute = self.project_dir / pattern
        if ".." in absolute.parts:
            self.fail(absolute, "文件模式必须位于当前项目内")
        anchor = next(
            (
                root
                for root in (self.project_dir, self._input_root)
                if absolute.is_relative_to(root)
            ),
            Path(absolute.anchor),
        )
        relative_parts = absolute.relative_to(anchor).parts
        split = next(
            (index for index, part in enumerate(relative_parts) if any(c in part for c in "*?[")),
            len(relative_parts),
        )
        prefix = self._safe_path(anchor.joinpath(*relative_parts[:split]), allow_missing=True)
        parts = (*prefix.relative_to(self.project_dir).parts, *relative_parts[split:])
        # Existing callers pass str(project_dir / pattern) to glob; Path strips
        # trailing separators before glob sees them. Keep that exact behavior.
        return parts, str(absolute).endswith(("/", os.sep))

    def glob(self, pattern: str) -> list[Path]:
        key = self._pattern(pattern)
        if key not in self._glob_results:
            parts, directories_only = key
            if "**" not in parts:
                # Explicit documents/configs use bounded, error-aware directory queries.
                paths = self._direct_glob(parts, directories_only=directories_only)
            else:
                files = self.files
                candidates = (
                    (self.project_dir, *self._directories)
                    if directories_only
                    else (self.project_dir, *files, *self._directories)
                )
                paths = [
                    path
                    for path in candidates
                    if _glob_match(path.relative_to(self.project_dir).parts, parts)
                ]
            self._glob_results[key] = tuple(paths)
        return list(self._glob_results[key])

    def document_paths(
        self, directory: Path, pattern: str, *, recursive: bool = False
    ) -> list[Path]:
        """Inspect an explicitly selected document directory, outside source exclusions."""
        directory = self._safe_path(directory, allow_missing=True)
        try:
            directory.lstat()
        except FileNotFoundError:
            return []
        except OSError as exc:
            self.fail(directory, f"无法读取必要目录（{type(exc).__name__}）")
        paths: list[Path] = []
        pending = [directory]
        while pending:
            current = self._safe_path(pending.pop())
            try:
                with os.scandir(current) as stream:
                    entries = list(stream)
                for entry in entries:
                    path = Path(entry.path)
                    if fnmatch.fnmatch(entry.name, pattern):
                        paths.append(self._safe_path(path))
                    if recursive and (entry.is_dir(follow_symlinks=False) or entry.is_symlink()):
                        pending.append(self._safe_path(path))
            except OSError as exc:
                self.fail(current, f"无法枚举必要目录（{type(exc).__name__}）")
        return paths

    def watch_selection(
        self, key: str, paths: list[Path], discover: Callable[[], list[Path]]
    ) -> None:
        paths = [self._safe_path(path) for path in paths]
        if key in self._selections and _path_names(self._selections[key][0]) != _path_names(paths):
            self.fail(self.project_dir, "检查期间必要输入清单发生变化")
        self._selections[key] = (tuple(paths), discover)

    def watch_candidate(self, digest: str) -> None:
        if self._candidate_digest is not None and self._candidate_digest != digest:
            self.fail(self.project_dir, "检查期间当前代码版本发生变化")
        self._candidate_digest = digest

    def verify(self) -> None:
        if self.errors:
            raise SourceScanError("；".join(self.errors))
        if self._files is not None:
            files, directories = self._discover()
            if _path_names(files) != _path_names(self._files) or _path_names(
                directories
            ) != _path_names(self._directories):
                self.fail(self.project_dir, "检查期间文件清单发生变化，请结束修改后重跑")
        for expected_paths, discover in self._selections.values():
            actual_paths = [self._safe_path(path) for path in discover()]
            if _path_names(actual_paths) != _path_names(expected_paths):
                self.fail(self.project_dir, "检查期间必要输入清单发生变化")
        for (parts, directories_only), expected_paths in self._glob_results.items():
            if "**" not in parts:
                actual = self._direct_glob(parts, directories_only=directories_only)
                if _path_names(actual) != _path_names(expected_paths):
                    self.fail(self.project_dir, "检查期间必要输入清单发生变化")
        for path, expected in self._digests.items():
            actual_path, digest = self._digest(path)
            if str(actual_path) != str(path):
                self.fail(path, "检查期间文件路径发生变化")
            if digest != expected:
                self.fail(path, "检查期间文件内容发生变化")
        for path in self._writes:
            self._safe_path(path, allow_missing=True)
        if self._candidate_digest is not None:
            from ..extensions.evidence import build_candidate_identity

            if (
                build_candidate_identity(self.project_dir).candidate_digest
                != self._candidate_digest
            ):
                self.fail(self.project_dir, "检查期间当前代码版本发生变化")

    def publish(self) -> None:
        self.verify()
        for path, content in self._writes.items():
            path = self._safe_path(path, allow_missing=True)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path = self._safe_path(path, allow_missing=True)
                path.write_text(content, encoding="utf-8")
            except OSError as exc:
                self.fail(path, f"无法发布检查报告（{type(exc).__name__}）")


def _glob_match(parts: tuple[str, ...], patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return not parts
    pattern = patterns[0]
    if pattern == "**":
        return _glob_match(parts, patterns[1:]) or bool(
            parts and not parts[0].startswith(".") and _glob_match(parts[1:], patterns)
        )
    if not parts or (parts[0].startswith(".") and not pattern.startswith(".")):
        return False
    return fnmatch.fnmatch(parts[0], pattern) and _glob_match(parts[1:], patterns[1:])


_CURRENT: ContextVar[SourceInventory | None] = ContextVar("quality_source_inventory", default=None)


def inventory_for(project_dir: Path, ignored_dirs: frozenset[str] | None = None) -> SourceInventory:
    current = _CURRENT.get()
    if current is None:
        return SourceInventory(project_dir, ignored_dirs)
    if current._safe_path(project_dir) != current.project_dir:
        current.fail(Path(project_dir), "拒绝跨项目复用来源清单")
    if ignored_dirs is not None and not current.ignored_dirs <= ignored_dirs:
        current.fail(current.project_dir, "来源清单的排除策略不兼容")
    return current


@contextmanager
def source_scan_scope(
    project_dir: Path, ignored_dirs: frozenset[str] | None = None
) -> Iterator[SourceInventory]:
    existing = _CURRENT.get()
    if existing is not None:
        yield inventory_for(project_dir, ignored_dirs)
        return
    inventory = SourceInventory(project_dir, ignored_dirs)
    token = _CURRENT.set(inventory)
    try:
        yield inventory
        inventory.publish()
    finally:
        _CURRENT.reset(token)


_P = ParamSpec("_P")
_R = TypeVar("_R")


def source_scan(
    ignored_dirs: frozenset[str],
) -> Callable[[Callable[Concatenate[Path, _P], _R]], Callable[Concatenate[Path, _P], _R]]:
    def decorate(
        function: Callable[Concatenate[Path, _P], _R],
    ) -> Callable[Concatenate[Path, _P], _R]:
        @wraps(function)
        def wrapped(project_dir: Path, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            with source_scan_scope(project_dir, ignored_dirs):
                return function(project_dir, *args, **kwargs)

        return wrapped

    return decorate


def scan_report_exists(path: Path) -> bool:
    inventory = _CURRENT.get()
    if inventory is not None:
        path = inventory._safe_path(path, allow_missing=True)
    return (inventory is not None and path in inventory._writes) or path.exists()


def load_scan_report(path: Path) -> dict[str, Any]:
    """Read this invocation's pending report before falling back to disk."""
    from ..evidence_identity import load_json_payload

    inventory = _CURRENT.get()
    if inventory is not None:
        path = inventory._safe_path(path, allow_missing=True)
    if inventory is None or path not in inventory._writes:
        return load_json_payload(path)
    try:
        payload = json.loads(inventory._writes[path])
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_scan_report(path: Path, content: str) -> None:
    inventory = _CURRENT.get()
    if inventory is None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    else:
        path = inventory._safe_path(path, allow_missing=True)
        inventory._writes[path] = content
