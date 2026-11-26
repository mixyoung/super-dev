"""Byte-preserving writes using the existing integration ownership manifest."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from ..user_directories import UserDirectoryContext, ensure_plain_path
from .catalog_mixin import LEGACY_260_RULE_SURFACES
from .install_manifest import install_manifest_path, load_install_manifest, save_install_manifest


def plain_path(path: Path) -> None:
    ensure_plain_path(path)


def _current_bytes(path: Path) -> bytes | None:
    plain_path(path)
    return path.read_bytes() if path.exists() else None


def _assert_current(path: Path, expected: bytes | None) -> None:
    if _current_bytes(path) != expected:
        raise ValueError(f"写入前文件发生变化，保留现场：{path}")


def atomic_write(
    path: Path, content: bytes, *, expected: bytes | None = None, check_current: bool = False
) -> None:
    plain_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".super-dev-{path.name}-{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(content)
        plain_path(path)
        if check_current:
            _assert_current(path, expected)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def ownership(project: Path) -> dict[str, Any]:
    path = install_manifest_path(project)
    plain_path(path)
    if path.exists():
        try:
            payload = json.loads(path.read_bytes().decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("targets", {}), dict):
                raise ValueError("invalid manifest")
        except (UnicodeError, ValueError) as exc:
            raise ValueError(f"安装归属清单损坏，保留现场：{path}") from exc
    payload = load_install_manifest(project)
    records = payload.get("content_ownership", {})
    if not isinstance(records, dict):
        raise ValueError("安装内容归属记录损坏，保留现场")
    return records


def save_record(project: Path, key: str, record: dict[str, Any]) -> None:
    records = ownership(project)
    records[key] = record
    save_install_manifest(project, {"content_ownership": records})


def delete_record(project: Path, key: str) -> None:
    records = ownership(project)
    if key in records:
        del records[key]
        save_install_manifest(project, {"content_ownership": records})


def _record(project: Path, key: str) -> dict[str, Any]:
    record = ownership(project).get(key, {})
    if not isinstance(record, dict):
        raise ValueError("安装内容归属记录损坏，保留现场")
    return record


def _finish_deletion(
    project: Path, path: Path, key: str, record: dict[str, Any], actual: bytes | None
) -> bool:
    pending = record.get("pending_delete")
    if pending is None:
        return False
    if not isinstance(pending, dict) or type(pending.get("after_exists")) is not bool:
        raise ValueError("删除待提交记录损坏，保留现场")
    after_matches = (
        actual is not None and digest(actual) == pending.get("after_sha256")
        if pending["after_exists"]
        else actual is None
    )
    if after_matches:
        delete_record(project, key)
        return True
    if actual is not None and digest(actual) == pending.get("before_sha256"):
        return False
    raise ValueError(f"删除待提交记录与文件字节不匹配，保留现场：{path}")


def _deletion_record(record: dict[str, Any], before: bytes, after: bytes | None) -> dict[str, Any]:
    return {
        **record,
        "pending_delete": {
            "before_sha256": digest(before),
            "after_exists": after is not None,
            "after_sha256": digest(after) if after is not None else "",
        },
    }


def verified_block_record(
    project: Path,
    path: Path,
    begin: str,
    original: bytes,
    span: tuple[int, int],
    directories: UserDirectoryContext | None = None,
) -> tuple[dict[str, Any], bool]:
    key = f"{path.absolute()}|{begin}"
    records = ownership(project)
    fragment_hash = digest(original[span[0] : span[1]])
    if key in records:
        record = _record(project, key)
        if fragment_hash not in {record.get("sha256"), record.get("pending_sha256")}:
            raise ValueError(f"保留用户修改或归属不明的托管块：{path}")
        return record, False
    return (
        verified_legacy_surface(
            project, path, fragment_hash, "block", directories=directories, begin=begin
        ),
        True,
    )


def verified_legacy_surface(
    project: Path,
    path: Path,
    content_hash: str,
    layout: str,
    *,
    directories: UserDirectoryContext | None = None,
    begin: str | None = None,
    host: str | None = None,
) -> dict[str, Any]:
    ownership(project)
    legacy_path = install_manifest_path(project)
    if not legacy_path.exists():
        raise ValueError("缺少可核实的历史安装清单，保留现场")
    payload = json.loads(legacy_path.read_bytes().decode("utf-8"))
    if type(payload.get("version")) is not int or payload["version"] != 1:
        raise ValueError("无法核实历史安装清单版本，保留现场")
    context = directories or UserDirectoryContext.current()
    for surface in LEGACY_260_RULE_SURFACES:
        if surface.layout != layout or begin is not None and surface.begin != begin:
            continue
        if host is not None and surface.host != host:
            continue
        base = project if surface.base == "project" else getattr(context, surface.base)
        if (
            path.absolute() != (base / surface.path).absolute()
            or content_hash not in surface.hashes
        ):
            continue
        target = payload.get("targets", {}).get(surface.host)
        if (
            not isinstance(target, dict)
            or target.get("host") != surface.host
            or target.get("family") != surface.family
        ):
            continue
        scope = "project" if surface.base == "project" else "global"
        scopes, paths = target.get("scopes"), target.get("paths")
        if not scope or not isinstance(scopes, dict) or scopes.get(scope) is not True:
            continue
        if not isinstance(paths, list) or not any(
            isinstance(item, str) and Path(item).is_absolute() and Path(item) == path.absolute()
            for item in paths
        ):
            continue
        return {
            "sha256": content_hash,
            "prefix_hex": "",
            "original_exists": True,
            "legacy_content_version": "2.6.0",
            "legacy_layout": layout,
        }
    raise ValueError(f"无法核实历史安装的路径或作用域，保留原文件：{path}")


def legacy_whole_block_record(
    project: Path,
    path: Path,
    begin: str,
    original: bytes,
    directories: UserDirectoryContext | None = None,
) -> dict[str, Any] | None:
    surfaces = [
        surface
        for surface in LEGACY_260_RULE_SURFACES
        if surface.layout == "whole" and surface.begin == begin
    ]
    if not surfaces:
        return None
    payload = load_install_manifest(project)
    known_hash = any(digest(original) in surface.hashes for surface in surfaces)
    has_receipt = any(
        isinstance(payload.get("targets", {}).get(surface.host), dict)
        and payload["targets"][surface.host].get("scopes", {}).get("project") is True
        for surface in surfaces
    )
    if not known_hash and not has_receipt:
        return None
    return verified_legacy_surface(
        project, path, digest(original), "whole", directories=directories, begin=begin
    )


def reconcile_dsh_installation(project: Path, directories: UserDirectoryContext) -> None:
    from .manager import IntegrationManager

    records = ownership(project)
    payload = load_install_manifest(project)
    targets = payload.get("targets", {})
    host = "deepseek-harness"
    target = targets.get(host)
    if not isinstance(target, dict):
        return
    manager = IntegrationManager(project, user_directories=directories)
    remaining: dict[str, Path] = {}
    for surface, path in manager.collect_managed_surface_paths(host).items():
        key = str(path.absolute())
        if path == project / "AGENTS.local.md":
            key += f"|{manager.DSH_AGENTS_BEGIN}"
        if key in records:
            remaining[surface] = path
    if remaining:
        target["paths"] = sorted({str(path) for path in remaining.values()})
        target["scopes"] = {
            "project": any(surface.startswith("project:") for surface in remaining),
            "global": any(surface.startswith("skill:") for surface in remaining),
            "runtime": False,
        }
    else:
        del targets[host]
    save_install_manifest(project, {"targets": targets})


def reconcile_windsurf_project_removal(project: Path) -> None:
    ownership(project)
    payload = load_install_manifest(project)
    targets = payload.get("targets", {})
    target = targets.get("windsurf")
    if not isinstance(target, dict):
        return
    scopes = target.get("scopes", {})
    if isinstance(scopes, dict) and scopes.get("global") is True:
        target["scopes"] = {**scopes, "project": False}
        target["paths"] = [
            item
            for item in target.get("paths", [])
            if isinstance(item, str) and not Path(item).is_relative_to(project)
        ]
    else:
        del targets["windsurf"]
    save_install_manifest(project, {"targets": targets})


def write_owned_file(
    project: Path,
    path: Path,
    content: bytes,
    *,
    legacy_host: str | None = None,
    expected_current: bytes | None = None,
) -> bool:
    plain_path(path)
    key = str(path.absolute())
    previous = ownership(project).get(key, {})
    actual = path.read_bytes() if path.exists() else None
    if expected_current is not None and actual != expected_current:
        raise ValueError(f"写入前文件发生变化，保留现场：{path}")
    adopted = False
    if actual is not None and not previous and legacy_host is not None:
        previous = verified_legacy_surface(project, path, digest(actual), "whole", host=legacy_host)
        adopted = True
    if actual is not None and legacy_host is not None and b"\r\n" in actual:
        content = content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if actual is not None and digest(actual) not in {
        previous.get("sha256"),
        previous.get("pending_sha256"),
    }:
        raise ValueError(f"保留用户修改或归属不明的文件：{path}")
    if actual == content:
        if adopted or previous.get("pending_sha256"):
            save_record(project, key, {"sha256": digest(content)})
        return False
    record = {
        "sha256": digest(actual) if actual is not None else "",
        "pending_sha256": digest(content),
    }
    save_record(project, key, record)
    atomic_write(path, content, expected=actual, check_current=True)
    save_record(project, key, {"sha256": digest(content)})
    return True


def remove_owned_file(
    project: Path,
    path: Path,
    *,
    legacy_host: str | None = None,
) -> bool:
    plain_path(path)
    key = str(path.absolute())
    actual = _current_bytes(path)
    record = _record(project, key)
    if _finish_deletion(project, path, key, record, actual):
        return True
    if actual is None:
        delete_record(project, key)
        return False
    if not record and legacy_host is not None:
        record = verified_legacy_surface(project, path, digest(actual), "whole", host=legacy_host)
    if digest(actual) not in {record.get("sha256"), record.get("pending_sha256")}:
        raise ValueError(f"保留用户修改或归属不明的文件：{path}")
    save_record(project, key, _deletion_record(record, actual, None))
    _assert_current(path, actual)
    path.unlink()
    delete_record(project, key)
    if not any(path.parent.iterdir()):
        path.parent.rmdir()
    return True


def block_span(content: bytes, begin: str, end: str) -> tuple[int, int] | None:
    begin_bytes, end_bytes = begin.encode(), end.encode()
    tokens = re.finditer(
        re.escape(begin_bytes)
        + b"|"
        + re.escape(end_bytes)
        + rb"|<!-- (?:BEGIN|END) SUPER DEV [^>]+ -->",
        content,
    )
    active = b""
    seen: set[bytes] = set()
    for token in tokens:
        value = token.group()
        is_begin = value == begin_bytes or value.startswith(b"<!-- BEGIN SUPER DEV ")
        if is_begin:
            if value in seen:
                raise ValueError("托管块边界重复，保留原文件")
            seen.add(value)
            if active:
                raise ValueError("托管块边界重叠，保留原文件")
            active = value
        else:
            expected = end_bytes if active == begin_bytes else active.replace(b"BEGIN", b"END", 1)
            if not active or value != expected:
                raise ValueError("托管块边界不配对，保留原文件")
            active = b""
    if active:
        raise ValueError("托管块边界不配对，保留原文件")
    if begin_bytes not in content and end_bytes not in content:
        return None
    if content.count(begin_bytes) != 1 or content.count(end_bytes) != 1:
        raise ValueError("托管块边界缺失或重复，保留原文件")
    start, stop = content.index(begin_bytes), content.index(end_bytes)
    if start >= stop:
        raise ValueError("托管块边界顺序错误，保留原文件")
    stop += len(end_bytes)
    if content[stop : stop + 2] == b"\r\n":
        stop += 2
    elif content[stop : stop + 1] == b"\n":
        stop += 1
    return start, stop


def upsert_block(
    project: Path,
    path: Path,
    begin: str,
    end: str,
    body: str,
    *,
    directories: UserDirectoryContext | None = None,
    expected_current: bytes | None = None,
) -> bool:
    plain_path(path)
    existed = path.exists()
    original = path.read_bytes() if existed else b""
    expected_before = original if existed else None
    if expected_current is not None and original != expected_current:
        raise ValueError(f"写入前文件发生变化，保留现场：{path}")
    key = f"{path.absolute()}|{begin}"
    record = _record(project, key)
    recovered_delete = _finish_deletion(project, path, key, record, original if existed else None)
    if recovered_delete:
        record = {}
    span = block_span(original, begin, end)
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    managed = newline.join(
        [
            begin.encode(),
            body.rstrip().replace("\r\n", "\n").replace("\n", newline.decode()).encode(),
            end.encode(),
            b"",
        ]
    )
    if span is None and record.get("sha256"):
        raise ValueError(f"已登记托管块的边界缺失，保留原文件：{path}")
    whole = None
    if (
        span is None
        and not recovered_delete
        and (not record or record.get("legacy_whole_before_sha256"))
    ):
        if (
            record.get("legacy_whole_before_sha256")
            and digest(original) != record["legacy_whole_before_sha256"]
        ):
            raise ValueError("历史整文件转换记录与当前字节不匹配，保留现场")
        whole = legacy_whole_block_record(project, path, begin, original, directories)
    if span is not None:
        start, stop = span
        record, adopted = verified_block_record(project, path, begin, original, span, directories)
        prefix = bytes.fromhex(record.get("prefix_hex", ""))
        existed = bool(record.get("original_exists", True))
        updated = original[:start] + managed + original[stop:]
    else:
        adopted = whole is not None
        prefix = b"" if whole or not original or original.endswith(b"\n") else newline
        updated = managed if whole else original + prefix + managed
        if whole:
            existed = True
    if updated == original:
        if adopted or record.get("pending_sha256") or record.get("pending_delete"):
            _assert_current(path, original)
            final = {**record, "sha256": digest(managed), "pending_sha256": ""}
            final.pop("pending_delete", None)
            save_record(project, key, final)
        return False
    pending = {
        "sha256": digest(original[span[0] : span[1]]) if span else "",
        "pending_sha256": digest(managed),
        "prefix_hex": prefix.hex(),
        "original_exists": existed,
    }
    if whole:
        pending["legacy_whole_before_sha256"] = digest(original)
    save_record(project, key, pending)
    atomic_write(path, updated, expected=expected_before, check_current=True)
    save_record(project, key, {**pending, "sha256": digest(managed), "pending_sha256": ""})
    return True


def remove_block(
    project: Path,
    path: Path,
    begin: str,
    end: str,
    *,
    directories: UserDirectoryContext | None = None,
) -> bool:
    plain_path(path)
    key = f"{path.absolute()}|{begin}"
    actual = _current_bytes(path)
    record = _record(project, key)
    if _finish_deletion(project, path, key, record, actual):
        return True
    if actual is None:
        delete_record(project, key)
        return False
    original = actual
    span = block_span(original, begin, end)
    if span is None:
        if record.get("sha256"):
            raise ValueError(f"已登记托管块的边界缺失，保留原文件：{path}")
        whole = legacy_whole_block_record(project, path, begin, original, directories)
        if whole:
            save_record(project, key, _deletion_record(whole, original, b""))
            atomic_write(path, b"", expected=original, check_current=True)
            delete_record(project, key)
            return True
        delete_record(project, key)
        return False
    start, stop = span
    record, _adopted = verified_block_record(project, path, begin, original, span, directories)
    prefix = bytes.fromhex(record.get("prefix_hex", ""))
    if prefix and original[max(0, start - len(prefix)) : start] != prefix:
        raise ValueError(f"托管块前的用户内容已变化，保留原文件：{path}")
    updated = original[: start - len(prefix)] + original[stop:]
    after = None if not updated and not record.get("original_exists", True) else updated
    save_record(project, key, _deletion_record(record, original, after))
    if after is None:
        _assert_current(path, original)
        path.unlink()
    else:
        atomic_write(path, updated, expected=original, check_current=True)
    delete_record(project, key)
    return True
