"""扩展来源锁和稳定内容摘要。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .models import ExtensionManifest, ExtensionStatus

_IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def _stable_file_bytes(path: Path) -> bytes:
    """Return cross-platform bytes for content identity.

    Git may materialize the same committed UTF-8 text with LF or CRLF depending
    on the checkout.  Text sources therefore use LF for hashing, while binary
    sources retain their exact bytes.
    """

    payload = path.read_bytes()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_source_path(source_root: Path, relative_path: str) -> Path:
    root = source_root.resolve()
    candidate = (root / relative_path).resolve(strict=False)
    if not _inside(root, candidate):
        raise ValueError("来源路径越出允许根目录")
    return candidate


def stable_content_digest(path: Path) -> str:
    target = Path(path).resolve()
    hasher = hashlib.sha256()
    if target.is_file():
        hasher.update(_stable_file_bytes(target))
        return f"sha256:{hasher.hexdigest()}"
    if not target.is_dir():
        raise FileNotFoundError(f"来源不存在: {target}")

    files: list[Path] = []
    for item in target.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"来源目录不允许符号链接: {item}")
        if not item.is_file() or any(part in _IGNORED_PARTS for part in item.parts):
            continue
        files.append(item)
    for item in sorted(files, key=lambda entry: entry.relative_to(target).as_posix()):
        label = item.relative_to(target).as_posix()
        hasher.update(label.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(_stable_file_bytes(item))
        hasher.update(b"\0")
    return f"sha256:{hasher.hexdigest()}"


@dataclass(frozen=True)
class SourceVerification:
    status: ExtensionStatus
    expected_digest: str
    actual_digest: str
    identity_digest: str
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == ExtensionStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "expected_digest": self.expected_digest,
            "actual_digest": self.actual_digest,
            "identity_digest": self.identity_digest,
            "errors": list(self.errors),
        }


class SourceLockVerifier:
    def __init__(self, *, source_root: Path, lock_path: Path):
        self.source_root = Path(source_root).resolve()
        self.lock_path = Path(lock_path).resolve()

    def _load_lock(self) -> tuple[dict[str, Any], list[str]]:
        try:
            raw = yaml.safe_load(self.lock_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            return {}, [f"无法读取来源锁: {exc}"]
        if not isinstance(raw, dict):
            return {}, ["来源锁必须是对象"]
        unknown = sorted(set(raw) - {"schema_version", "sources"})
        errors: list[str] = []
        if unknown:
            errors.append(f"来源锁包含未知字段: {unknown}")
        if raw.get("schema_version") != 1:
            errors.append("来源锁 schema_version 仅支持 1")
        sources = raw.get("sources")
        if not isinstance(sources, dict):
            errors.append("来源锁 sources 必须是对象")
            sources = {}
        return sources, errors

    def verify(self, manifest: ExtensionManifest) -> SourceVerification:
        sources, errors = self._load_lock()
        locked = sources.get(manifest.id)
        if not isinstance(locked, dict):
            errors.append(f"来源锁没有扩展 {manifest.id}")
            locked = {}
        expected = manifest.source.to_dict()
        lock_keys = set(locked) - {"reviewed_at", "manifest_digest"}
        unknown = sorted(lock_keys - set(expected))
        missing = sorted(set(expected) - lock_keys)
        if unknown:
            errors.append(f"来源 {manifest.id} 包含未知锁字段: {unknown}")
        if missing:
            errors.append(f"来源 {manifest.id} 缺少锁字段: {missing}")
        for key, expected_value in expected.items():
            if locked.get(key) != expected_value:
                errors.append(f"来源锁字段不一致: {manifest.id}.{key}")

        if manifest.manifest_path is not None:
            expected_manifest_digest = str(locked.get("manifest_digest", "")).strip()
            if not expected_manifest_digest:
                errors.append(f"来源 {manifest.id} 缺少 manifest_digest")
            else:
                try:
                    actual_manifest_digest = stable_content_digest(manifest.manifest_path)
                except OSError as exc:
                    errors.append(f"无法计算清单摘要: {exc}")
                else:
                    if actual_manifest_digest != expected_manifest_digest:
                        errors.append("扩展清单内容与来源锁摘要不一致")

        actual_digest = ""
        try:
            source_path = resolve_source_path(self.source_root, manifest.source.path)
            actual_digest = stable_content_digest(source_path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
        if actual_digest and actual_digest != manifest.source.content_digest:
            errors.append("本地扩展内容与清单摘要不一致")

        identity_payload = {
            "source": expected,
            "manifest_digest": str(locked.get("manifest_digest", "")).strip(),
        }
        identity_digest = (
            "sha256:"
            + hashlib.sha256(
                json.dumps(
                    identity_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )

        return SourceVerification(
            status=ExtensionStatus.PASS if not errors else ExtensionStatus.BLOCKED,
            expected_digest=manifest.source.content_digest,
            actual_digest=actual_digest,
            identity_digest=identity_digest,
            errors=tuple(errors),
        )
