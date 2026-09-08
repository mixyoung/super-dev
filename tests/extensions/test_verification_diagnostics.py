from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from rich.console import Console

from super_dev.cli_release_quality_mixin import CliReleaseQualityMixin
from super_dev.extensions.evidence import build_candidate_identity
from super_dev.extensions.models import ExtensionStatus
from super_dev.extensions.service import ExtensionService
from tests.extensions.test_evidence import _repo
from tests.extensions.test_fresh_verification_service import _configure


@pytest.mark.parametrize("use_git", [True, False])
def test_only_owned_knowledge_database_files_are_runtime_state(tmp_path, use_git):
    project = _repo(tmp_path) if use_git else tmp_path
    before = build_candidate_identity(project)
    state_dir = project / ".super-dev"
    state_dir.mkdir(exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        (state_dir / f"knowledge-stats.db{suffix}").write_bytes(b"runtime data")
    files = {}
    after = build_candidate_identity(project, file_manifest=files)
    assert after.to_dict() == before.to_dict()
    assert not any("knowledge-stats.db" in path for path in files)

    (state_dir / "customer.db-wal").write_bytes(b"business data")
    (project / "source.tmp").write_text("new source", encoding="utf-8")
    changed = build_candidate_identity(project, file_manifest=files)
    assert changed.candidate_digest != before.candidate_digest
    assert ".super-dev/customer.db-wal" in files
    assert "source.tmp" in files


@pytest.mark.parametrize("use_git", [True, False])
def test_file_inventory_uses_same_read_without_changing_identity(tmp_path, monkeypatch, use_git):
    project = _repo(tmp_path) if use_git else tmp_path
    target = project / "new.py"
    target.write_bytes(b"before\n")
    expected = build_candidate_identity(project)
    original_read = Path.read_bytes
    reads = []

    def read_then_change(path):
        content = original_read(path)
        if path == target:
            reads.append(path)
            path.write_bytes(b"after\n")
        return content

    monkeypatch.setattr(Path, "read_bytes", read_then_change)
    files = {}
    captured = build_candidate_identity(project, file_manifest=files)
    assert captured.to_dict() == expected.to_dict()
    assert files["new.py"] == "sha256:" + hashlib.sha256(b"before\n").hexdigest()
    assert reads == [target]


@pytest.mark.parametrize("use_git", [True, False])
def test_verification_reports_added_removed_and_modified_files(tmp_path, use_git):
    project = _repo(tmp_path) if use_git else tmp_path
    _configure(project, args=["-q", "test_changes.py"])
    (project / "old.txt").write_text("before", encoding="utf-8")
    (project / "gone.txt").write_text("remove me", encoding="utf-8")
    (project / "test_changes.py").write_text(
        "from pathlib import Path\n"
        "def test_changes():\n"
        "    Path('new [file].py').write_text('new', encoding='utf-8')\n"
        "    Path('old.txt').write_text('after', encoding='utf-8')\n"
        "    Path('gone.txt').unlink()\n",
        encoding="utf-8",
    )
    outcome = ExtensionService(project).run_fresh_verification()
    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.candidate_changed is True
    expected = {"added": ["new [file].py"], "removed": ["gone.txt"], "modified": ["old.txt"]}
    assert outcome.file_changes == expected
    payload = json.loads((outcome.result_path.parent / "pytest-summary.json").read_text("utf-8"))
    assert payload["file_changes"] == expected
    assert "gone.txt" in payload["file_manifest_before"]
    assert "gone.txt" not in payload["file_manifest_after"]
    assert payload["file_manifest_before"]["old.txt"] != payload["file_manifest_after"]["old.txt"]

    display = io.StringIO()
    renderer = CliReleaseQualityMixin()
    renderer.console = Console(file=display, color_system=None)
    check = renderer._completion_verification_check(outcome)
    assert check.evidence["file_changes"] == expected
    renderer._verification_summary(outcome, check)
    assert '"new [file].py"' in display.getvalue()
    assert "gone.txt" in display.getvalue()
    assert "old.txt" in display.getvalue()


def test_verification_runtime_reports_do_not_invalidate_source(tmp_path):
    _configure(tmp_path, args=["-q", "test_report.py"])
    (tmp_path / "test_report.py").write_text(
        "from pathlib import Path\n"
        "def test_report():\n"
        "    for name in ('output/report.txt', '.super-dev/extensions/scratch/report.txt'):\n"
        "        path = Path(name)\n"
        "        path.parent.mkdir(parents=True, exist_ok=True)\n"
        "        path.write_text('report', encoding='utf-8')\n",
        encoding="utf-8",
    )
    outcome = ExtensionService(tmp_path).run_fresh_verification()
    assert outcome.status == ExtensionStatus.PASS
    assert outcome.file_changes == {"added": [], "removed": [], "modified": []}
    payload = json.loads((outcome.result_path.parent / "pytest-summary.json").read_text("utf-8"))
    assert not any(
        path.startswith(("output/", ".super-dev/extensions/"))
        for path in payload["file_manifest_after"]
    )


def test_timeout_reports_incomplete_execution_not_bad_code(tmp_path):
    _configure(tmp_path, args=["-q", "test_wait.py"], timeout=1)
    (tmp_path / "test_wait.py").write_text(
        "import time\ndef test_wait():\n    time.sleep(5)\n", encoding="utf-8"
    )
    outcome = ExtensionService(tmp_path).run_fresh_verification()
    assert outcome.status == ExtensionStatus.BLOCKED
    assert outcome.result.process_tree_clean
    assert outcome.result.commands[0].timed_out
    assert "测试未完成" in outcome.message
    assert "不代表代码质量不合格" in outcome.message
    check = CliReleaseQualityMixin._completion_verification_check(outcome)
    assert not check.passed
    assert "运行预算" in check.recommendation
