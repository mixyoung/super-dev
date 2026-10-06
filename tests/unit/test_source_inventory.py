from __future__ import annotations

import gc
import glob
import os
import subprocess
import weakref
from pathlib import Path

import pytest

from super_dev.reviewers import architecture_drift, spec_compliance, uiux_compliance
from super_dev.reviewers.source_inventory import (
    SourceInventory,
    SourceScanError,
    inventory_for,
    source_scan_scope,
    write_scan_report,
)
from super_dev.reviewers.validation_rules import _is_path_ignored_for_scan


def put(root: Path, name: str, text: str = "value = 1\n") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("kind", ["spec", "architecture", "uiux"])
def test_selection_equals_original_full_walk(tmp_path, kind):
    for name in [
        "app.py",
        "page.tsx",
        "src/nested/new.py",
        ".hidden/private.py",
        "src/.hidden/page.tsx",
        ".nuxt/generated.py",
        "coverage/report.py",
        ".next/runtime.py",
        "Build/still_checked.py",
        "module.PY",
        "notes.md",
        "node_modules/deep/vendor.py",
        ".venv/lib/tool.py",
        "output/old.py",
        ".super-dev/changes/task/old.py",
        "sample.EGG-INFO/ignored.py",
        "src/build/ignored.py",
        "src/web.html",
    ]:
        put(tmp_path, name)
    if kind == "spec":
        extensions, ignored = spec_compliance._ALL_CODE_EXTENSIONS, spec_compliance._IGNORE_DIRS
    elif kind == "architecture":
        extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}
        ignored = architecture_drift._IGNORE_DIRS
    else:
        extensions, ignored = uiux_compliance._FRONTEND_EXTENSIONS, uiux_compliance._IGNORE_DIRS
    expected = {
        path.resolve()
        for path in tmp_path.rglob("*")
        if path.is_file()
        and path.suffix in extensions
        and not any(
            p in ignored or p.lower().endswith(".egg-info")
            for p in path.relative_to(tmp_path).parts
        )
    }
    assert set(SourceInventory(tmp_path).select(extensions, ignored)) == expected


@pytest.mark.parametrize(
    "pattern",
    [
        "**/*.py",
        "*.py",
        "src/**/*.py",
        "**/test_?.py",
        "src/*/*.py",
        "**/[ab]*.py",
        ".hidden/**/*.py",
        "**/.hidden/*.py",
        "**/*.{py,js}",
        "src/**",
        "src/**/",
        "src/*/",
        "**",
        "**/*",
    ],
)
def test_glob_keeps_python_matching_semantics(tmp_path, pattern):
    for name in [
        "app.py",
        "src/a.py",
        "src/deep/b.py",
        "src/deep/test_x.py",
        ".hidden/secret.py",
        "src/.hidden/secret.py",
        "src/c.js",
    ]:
        put(tmp_path, name)
    expected = {Path(p) for p in glob.glob(str(tmp_path / pattern), recursive=True)}
    expected = {p for p in expected if not _is_path_ignored_for_scan(p, tmp_path)}
    actual = set(SourceInventory(tmp_path).glob(pattern))
    # glob's trailing ** can include the prefix directory itself.
    assert actual == expected


def test_finite_glob_reports_unreadable_directory(tmp_path, monkeypatch):
    put(tmp_path, "src/app.py")
    original = os.scandir

    def deny(path):
        if Path(path) == tmp_path / "src":
            raise PermissionError("test")
        return original(path)

    monkeypatch.setattr(os, "scandir", deny)
    with pytest.raises(SourceScanError, match="src.*无法枚举"):
        SourceInventory(tmp_path).glob("src/*.py")


def test_narrower_policy_cannot_hide_another_consumers_inputs(tmp_path):
    with pytest.raises(SourceScanError, match="排除策略"):
        with source_scan_scope(tmp_path, spec_compliance._IGNORE_DIRS):
            inventory_for(tmp_path, architecture_drift._IGNORE_DIRS)


def test_explicit_glob_cannot_escape_before_discovery(tmp_path, monkeypatch):
    entered = []
    original = os.scandir

    def observe(path):
        entered.append(Path(path))
        return original(path)

    monkeypatch.setattr(os, "scandir", observe)
    with pytest.raises(SourceScanError, match="当前项目"):
        SourceInventory(tmp_path).glob("../*.py")
    assert entered == []


def test_same_scope_shares_but_next_scope_rediscovers(tmp_path):
    first = put(tmp_path, "app.py")
    with source_scan_scope(tmp_path) as inventory:
        assert inventory_for(tmp_path) is inventory
        assert first in inventory.files
        assert inventory_for(tmp_path).files is inventory.files
        assert inventory.discovery_count == 1
    assert inventory.discovery_count == 2
    first.unlink()
    second = put(tmp_path, "renamed.py")
    with source_scan_scope(tmp_path) as later:
        assert later is not inventory
        assert later.files == (second,)


@pytest.mark.parametrize("change", ["add", "delete", "rename", "case_rename", "content"])
def test_mid_scan_change_refuses_publication(tmp_path, change):
    target = put(tmp_path, "app.py")
    report = tmp_path / "output/report.json"
    with pytest.raises(SourceScanError, match="发生变化|无法读取"):
        with source_scan_scope(tmp_path) as inventory:
            assert target in inventory.files
            inventory.track([target])
            write_scan_report(report, '{"passed": true}')
            if change == "add":
                put(tmp_path, "new.py")
            elif change == "delete":
                target.unlink()
            elif change == "rename":
                target.rename(tmp_path / "renamed.py")
            elif change == "case_rename":
                target.rename(tmp_path / "APP.py")
            else:
                previous = target.stat()
                target.write_text("value = 2\n", encoding="utf-8")
                os.utime(target, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    assert not report.exists()


def test_nested_consumers_publish_only_after_outer_validation(tmp_path):
    target = put(tmp_path, "app.py")
    report = tmp_path / "output/report.json"
    with source_scan_scope(tmp_path) as inventory:
        inventory.track([target])
        with source_scan_scope(tmp_path):
            write_scan_report(report, "{}")
        assert not report.exists()
    assert report.read_text() == "{}"


def test_cross_project_inventory_cannot_be_reused(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(SourceScanError, match="跨项目"):
        with source_scan_scope(tmp_path):
            inventory_for(other)


def test_error_even_if_consumer_catches_it_blocks_scope(tmp_path, monkeypatch):
    target = put(tmp_path, "app.py")
    original = Path.read_bytes

    def deny(path):
        if path == target:
            raise PermissionError("test")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", deny)
    with pytest.raises(SourceScanError, match="app.py"):
        with source_scan_scope(tmp_path) as inventory:
            try:
                inventory.track([target])
            except SourceScanError:
                pass


def test_directory_error_blocks_but_excluded_error_is_not_visited(tmp_path, monkeypatch):
    source = put(tmp_path, "src/app.py")
    excluded = put(tmp_path, "node_modules/deep/app.py")
    original = os.scandir
    denied = excluded.parent.parent

    def deny(path):
        if Path(path) == denied:
            raise PermissionError("test")
        return original(path)

    monkeypatch.setattr(os, "scandir", deny)
    assert source in SourceInventory(tmp_path).files
    denied = source.parent
    with pytest.raises(SourceScanError, match="src.*无法枚举"):
        _ = SourceInventory(tmp_path).files


def test_explicit_document_is_read_even_when_source_excludes_output(tmp_path):
    source = put(tmp_path, "app.py")
    document = put(tmp_path, "output/current-prd.md", "# Current requirements")
    with source_scan_scope(tmp_path) as inventory:
        assert inventory.files == (source,)
        assert inventory.read_text(document) == "# Current requirements"


def test_explicit_document_directory_preserves_hidden_and_recursive_inputs(tmp_path):
    document = put(tmp_path, "output/.hidden-prd.md", "# Requirements")
    spec = put(tmp_path, ".super-dev/changes/current/specs/.hidden/core/spec.md", "# Spec")
    inventory = SourceInventory(tmp_path)
    assert inventory.document_paths(tmp_path / "output", "*prd*.md") == [document]
    assert inventory.document_paths(
        tmp_path / ".super-dev/changes/current/specs", "spec.md", recursive=True
    ) == [spec]
    assert inventory.document_paths(tmp_path / "absent", "*.md") == []


def test_necessary_document_directory_errors_are_not_an_empty_selection(tmp_path, monkeypatch):
    directory = tmp_path / "output"
    directory.mkdir()
    original = os.scandir

    def deny(path):
        if Path(path) == directory:
            raise PermissionError("test")
        return original(path)

    monkeypatch.setattr(os, "scandir", deny)
    with pytest.raises(SourceScanError, match="无法枚举必要目录"):
        SourceInventory(tmp_path).document_paths(directory, "*.md")


def test_inventory_is_released_after_scope_even_on_error(tmp_path):
    with pytest.raises(SourceScanError):
        with source_scan_scope(tmp_path) as inventory:
            reference = weakref.ref(inventory)
            inventory.fail(tmp_path, "test")
    del inventory
    gc.collect()
    assert reference() is None


@pytest.mark.skipif(os.name != "nt", reason="Windows 目录连接点专用测试")
def test_windows_junction_is_not_followed(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    junction = tmp_path / "junction"
    created = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert created.returncode == 0, "无法建立测试用的本地目录连接点"
    try:
        with pytest.raises(SourceScanError, match="连接点"):
            _ = SourceInventory(tmp_path).files
    finally:
        # Remove this test's junction, never the target tree.
        junction.rmdir()
    assert target.is_dir()


def test_directory_link_is_not_followed(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    link = source / "loop"
    try:
        link.symlink_to(source, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"本机无法创建目录符号链接：{type(exc).__name__}")
    with pytest.raises(SourceScanError, match="链接|连接点"):
        _ = SourceInventory(tmp_path).files
