"""Conservative refresh of existing generated text, never a blanket host setup."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .integrations.manager import IntegrationManager
from .skills.skill_template import SkillTemplate


def _plain_path(path: Path) -> None:
    for item in (path, *path.parents):
        if item.is_symlink() or (
            item.exists()
            and getattr(item.stat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError(f"拒绝连接点或符号链接：{path}")


def _surfaces(
    project: Path, include_user: bool
) -> dict[str, tuple[Path, str, tuple[str, str] | None]]:
    """Use existing host declarations/renderers; no installer, cleanup or hook execution."""
    manager = IntegrationManager(project_dir=project)
    surfaces = {}
    for host in manager.TARGETS:
        paths = manager.collect_managed_surface_paths(host, include_user_surfaces=include_user)
        for skill in ("super-dev", "super-dev-seeai"):
            for path in manager.expected_skill_paths(host, skill, project_dir=project):
                paths[f"skill:{path}"] = path
        for key, path in paths.items():
            path = path.absolute()
            if not include_user and not path.is_relative_to(project):
                continue
            if not path.is_file():
                continue  # update never introduces a new integration surface
            if path.suffix not in {".md", ".mdc", ".toml"}:
                continue  # JSON settings/hooks/plugin manifests need their own migration
            markers = None
            relative = (
                path.relative_to(project).as_posix() if path.is_relative_to(project) else path.name
            )
            if path.name == "AGENTS.md":
                markers = manager._managed_agents_markers(host)
            if host == "claude-code" and path.name == "CLAUDE.md":
                markers = (manager.CLAUDE_RULES_BEGIN, manager.CLAUDE_RULES_END)
            if path.name == "SKILL.md" and path.parent.name in {"super-dev", "super-dev-seeai"}:
                content = SkillTemplate.for_builtin(path.parent.name, host).render(host)
            elif "slash:" in key:
                builder = (
                    manager._build_toml_command_content
                    if path.suffix == ".toml"
                    else manager._build_slash_command_content
                )
                content = manager._append_flow_contract(content=builder(host), relative=relative)
            else:
                content = manager._append_flow_contract(
                    content=manager._build_file_content(target=host, relative=relative),
                    relative=relative,
                )
            surfaces[f"{host}|{key}"] = (path, content, markers)
    return surfaces


def _owned(text: str, markers: tuple[str, str] | None) -> tuple[str, int, int]:
    if markers is None:
        return text, 0, len(text)
    begin, end = markers
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError("托管区块缺失或重复，保留原文件")
    start = text.index(begin) + len(begin)
    stop = text.index(end)
    if start >= stop:
        raise ValueError("托管区块顺序无效")
    return text[start:stop], start, stop


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def snapshot_hosts(project: Path, *, include_user: bool) -> dict[str, Any]:
    entries = []
    issues: dict[str, str] = {}
    owned_paths: set[str] = set()
    seen = set()
    for key, (path, expected, markers) in _surfaces(project, include_user).items():
        identity = (str(path), markers)
        if identity in seen:
            continue
        try:
            _plain_path(path)
            actual = path.read_bytes().decode("utf-8")
            old, _, _ = _owned(actual, markers)
            if _normalized(old) != _normalized(expected):
                raise ValueError("内容不等于当前安装版本的模板，保留用户修改并等待手工复核")
        except (OSError, ValueError) as exc:
            issues[str(path)] = str(exc)
            continue
        seen.add(identity)
        owned_paths.add(str(path))
        entries.append({"key": key, "path": str(path), "old": old})
    return {
        "entries": entries,
        "issues": [f"{p}: {v}" for p, v in issues.items() if p not in owned_paths],
    }


def refresh_hosts(project: Path, snapshot: dict[str, Any], *, include_user: bool) -> dict[str, Any]:
    surfaces = _surfaces(project, include_user)
    issues = list(snapshot.get("issues", []))
    changed: list[str] = []
    backup_dir = project / ".super-dev" / "update-backups" / uuid.uuid4().hex
    for entry in snapshot.get("entries", []):
        key = entry["key"]
        try:
            if key not in surfaces or str(surfaces[key][0]) != entry["path"]:
                raise ValueError("新版声明已变化，未自动搬移或删除原文件")
            path, content, markers = surfaces[key]
            _plain_path(path)
            original = path.read_bytes()
            text = original.decode("utf-8")
            owned, start, stop = _owned(text, markers)
            if owned != entry["old"]:
                raise ValueError("安装期间文件发生变化，保留现场")
            replacement = f"\n{content.rstrip()}\n" if markers else content
            if _normalized(owned) == _normalized(replacement):
                continue
            _plain_path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            # Backup only the owned fragment, not surrounding private user instructions.
            (backup_dir / f"{len(changed)}.json").write_text(
                json.dumps(
                    {"path": str(path), "old": owned, "markers": markers}, ensure_ascii=False
                ),
                encoding="utf-8",
            )
            fd, temporary = tempfile.mkstemp(prefix=".super-dev-update-", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write((text[:start] + replacement + text[stop:]).encode("utf-8"))
                _plain_path(path)
                if path.read_bytes() != original:
                    raise ValueError("写入前文件发生变化，保留现场")
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            changed.append(str(path))
        except (OSError, ValueError) as exc:
            issues.append(f"{entry['path']}: {exc}")
    return {"changed": changed, "issues": issues, "backup_dir": str(backup_dir) if changed else ""}
