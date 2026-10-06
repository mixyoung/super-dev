from __future__ import annotations

import gc
import glob
import json
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
    load_scan_report,
    scan_report_exists,
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


def native_short_path(path: Path) -> Path:
    import ctypes
    from ctypes import wintypes

    function = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
    function.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    function.restype = wintypes.DWORD
    required = function(str(path), None, 0)
    if not required:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_unicode_buffer(required)
    written = function(str(path), buffer, required)
    assert 0 < written < required
    return Path(buffer.value)


@pytest.fixture
def native_path_pair(tmp_path):
    if os.name != "nt":
        pytest.skip("Windows 原生短路径专用测试")
    root = tmp_path / "project with a long directory name"
    root.mkdir()
    root = root.resolve()
    short = native_short_path(root)
    if short == root:
        pytest.skip("当前文件系统未提供 8.3 短路径别名")
    assert short.samefile(root)
    return root, short


@pytest.mark.parametrize("root_form", ["long", "short"])
def test_native_path_forms_share_canonical_inputs_and_reports(native_path_pair, root_form):
    root, short = native_path_pair
    source = put(root, "source-file-name.py")
    document = put(root, "output/current-prd.md", "# Requirements")
    selected_root = root if root_form == "long" else short
    with source_scan_scope(selected_root) as inventory:
        assert inventory_for(short) is inventory
        assert inventory.document_paths(short / "output", "*-prd.md") == [document]
        assert inventory.document_paths(short / "not-created/specs", "spec.md") == []
        assert inventory.glob(str(short / "*.py")) == [source]
        assert inventory.glob("*.py") == [source]
        assert len(inventory._glob_results) == 1
        assert inventory.read_text(native_short_path(source)) == "value = 1\n"
        inventory.track([source])
        assert list(inventory._digests) == [source]
        inventory.watch_selection("source", [native_short_path(source)], lambda: [source])
        inventory.watch_selection("source", [source], lambda: [native_short_path(source)])
        report = root / "output/report.json"
        write_scan_report(short / "output/report.json", '{"score": 100}')
        assert list(inventory._writes) == [report]
        assert scan_report_exists(report)
        assert load_scan_report(report) == {"score": 100}
        assert not report.exists()
    assert json.loads(report.read_text(encoding="utf-8")) == {"score": 100}


@pytest.mark.parametrize("module", [spec_compliance, architecture_drift, uiux_compliance])
@pytest.mark.parametrize("with_specs", [False, True])
def test_dependency_consumers_accept_native_short_roots(native_path_pair, module, with_specs):
    root, short = native_path_pair
    put(root, "super-dev.yaml", "name: demo\nplatform: cli\nfrontend: none\nbackend: python\n")
    put(root, ".super-dev/workflow-state.json", '{"active_change_id": "current-change"}')
    (root / ".super-dev/changes/current-change").mkdir(parents=True)
    for suffix in ("prd", "architecture", "uiux"):
        put(root, f"output/current-change-{suffix}.md", "# Current document\n")
    if with_specs:
        put(root, ".super-dev/changes/current-change/specs/core/spec.md", "# Current spec\n")
    put(root, "app.py")
    expected = module._report_dependencies(root, root / "output")
    with source_scan_scope(root):
        actual = module._report_dependencies(short, short / "output")
    assert [str(path) for path in actual] == [str(path) for path in expected]


def test_relative_inputs_are_canonical_before_cwd_changes(tmp_path, monkeypatch):
    root = tmp_path / "project"
    source = put(root, "app.py")
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(root)
    report = root / "output/report.json"
    with source_scan_scope(root) as inventory:
        assert inventory.read_text(Path("app.py")) == "value = 1\n"
        inventory.track([source])
        assert list(inventory._digests) == [source]
        write_scan_report(Path("output/report.json"), '{"score": 100}')
        assert scan_report_exists(report)
        assert load_scan_report(report) == {"score": 100}
        assert list(inventory._writes) == [report]
        monkeypatch.chdir(other)
    assert json.loads(report.read_text(encoding="utf-8")) == {"score": 100}
    assert not (other / "output").exists()


@pytest.mark.parametrize("outside", [False, True])
@pytest.mark.parametrize(
    "operation",
    [
        "documents",
        "read",
        "pattern",
        "report",
        "missing-documents",
        "report-read",
        "report-exists",
        "parent-hop",
    ],
)
def test_path_normalization_preserves_link_checks(tmp_path, outside, operation):
    root = tmp_path / "project"
    put(root, "input.py")
    put(tmp_path, "input.py")
    target = tmp_path / "outside" if outside else root / "inside"
    put(target, "input.py")
    link = root / "link"
    if os.name == "nt":
        created = subprocess.run(
            ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert created.returncode == 0
    else:
        link.symlink_to(target, target_is_directory=True)
    try:
        with pytest.raises(SourceScanError, match="链接|连接点"):
            with source_scan_scope(root) as inventory:
                if operation == "documents":
                    inventory.document_paths(link, "*.py")
                elif operation == "read":
                    inventory.read_text(link / "input.py")
                elif operation == "pattern":
                    inventory.glob("link/*.py")
                elif operation == "report":
                    write_scan_report(link / "report.json", "{}")
                elif operation == "missing-documents":
                    inventory.document_paths(link / "missing/child", "*.md")
                elif operation == "report-read":
                    load_scan_report(link / "missing/report.json")
                elif operation == "report-exists":
                    scan_report_exists(link / "missing/report.json")
                else:
                    inventory.read_text(link / ".." / "input.py")
        assert not (target / "report.json").exists()
    finally:
        if os.name == "nt":
            link.rmdir()
        else:
            link.unlink()
    assert target.is_dir()


def test_existing_report_alias_uses_the_same_pending_slot(native_path_pair):
    root, short = native_path_pair
    report = put(root, "output/existing-report-with-long-name.json", '{"score": 10}')
    alias = native_short_path(report)
    with source_scan_scope(root) as inventory:
        assert load_scan_report(alias) == {"score": 10}
        write_scan_report(alias, '{"score": 20}')
        write_scan_report(report, '{"score": 30}')
        assert list(inventory._writes) == [report]
        assert load_scan_report(alias) == {"score": 30}
        assert load_scan_report(short / "output" / report.name) == {"score": 30}
        assert json.loads(report.read_text(encoding="utf-8")) == {"score": 10}
    assert json.loads(report.read_text(encoding="utf-8")) == {"score": 30}


def test_glob_treats_the_project_root_as_literal(tmp_path):
    root = tmp_path / "project[1]"
    source = put(root, "src/app.py")
    inventory = SourceInventory(root)
    assert inventory.glob("src/*.py") == [source]
    assert inventory.glob(str(root / "src/*.py")) == [source]
    assert len(inventory._glob_results) == 1
    inventory.verify()


def test_document_read_accepts_safe_parent_components(tmp_path):
    source = put(tmp_path, "src/app.py")
    (tmp_path / "src/child").mkdir()
    inventory = SourceInventory(tmp_path)
    assert inventory.read_text(tmp_path / "src/child/../app.py") == "value = 1\n"
    assert list(inventory._digests) == [source]


def test_report_parent_becoming_a_link_blocks_all_publication(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    link = root / "output"
    try:
        with pytest.raises(SourceScanError, match="链接|连接点"):
            with source_scan_scope(root):
                write_scan_report(root / "safe/report.json", "{}")
                write_scan_report(link / "report.json", "{}")
                if os.name == "nt":
                    created = subprocess.run(
                        ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
                        capture_output=True,
                        timeout=10,
                        check=False,
                    )
                    assert created.returncode == 0
                else:
                    link.symlink_to(target, target_is_directory=True)
        assert not (root / "safe").exists()
        assert list(target.iterdir()) == []
    finally:
        if os.name == "nt":
            if link.exists():
                link.rmdir()
        elif link.is_symlink():
            link.unlink()


def test_tracked_input_case_rename_blocks_even_without_discovery(tmp_path):
    source = put(tmp_path, "input.py")
    with pytest.raises(SourceScanError, match="发生变化|无法读取"):
        with source_scan_scope(tmp_path) as inventory:
            inventory.track([source])
            source.rename(tmp_path / "INPUT.py")
            write_scan_report(tmp_path / "output/report.json", "{}")
    assert not (tmp_path / "output/report.json").exists()


def test_normalized_parent_segments_cannot_escape_project(tmp_path):
    root = tmp_path / "project"
    (root / "child").mkdir(parents=True)
    put(tmp_path, "outside.py")
    inventory = SourceInventory(root)
    with pytest.raises(SourceScanError, match="超出当前项目"):
        inventory.read_text(root / "child/../../outside.py")


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
