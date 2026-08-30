from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from super_dev.extensions.evidence import (
    EvidenceStore,
    build_candidate_identity,
    candidate_matches,
    utc_now,
)
from super_dev.extensions.models import (
    ExtensionEvent,
    ExtensionEventType,
    ExtensionResult,
    ExtensionStatus,
)


def _git(project: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    project = tmp_path / "repo"
    project.mkdir()
    _git(project, "init")
    _git(project, "config", "user.email", "tests@example.com")
    _git(project, "config", "user.name", "Tests")
    (project / "tracked.txt").write_text("one\n", encoding="utf-8")
    _git(project, "add", "tracked.txt")
    _git(project, "commit", "-m", "initial")
    return project


def test_candidate_digest_changes_for_dirty_staged_and_untracked_content(tmp_path: Path) -> None:
    project = _repo(tmp_path)
    clean = build_candidate_identity(project)

    (project / "tracked.txt").write_text("two\n", encoding="utf-8")
    dirty = build_candidate_identity(project)
    _git(project, "add", "tracked.txt")
    staged = build_candidate_identity(project)
    (project / "new.txt").write_text("alpha\n", encoding="utf-8")
    untracked = build_candidate_identity(project)
    (project / "new.txt").write_text("beta\n", encoding="utf-8")
    untracked_changed = build_candidate_identity(project)

    digests = {
        clean.candidate_digest,
        dirty.candidate_digest,
        staged.candidate_digest,
        untracked.candidate_digest,
        untracked_changed.candidate_digest,
    }
    assert len(digests) == 5


def test_candidate_digest_changes_when_git_index_is_unreadable(tmp_path: Path) -> None:
    project = _repo(tmp_path)
    (project / ".git" / "index").write_bytes(b"corrupt index")

    before = build_candidate_identity(project)
    (project / "tracked.txt").write_text("two\n", encoding="utf-8")
    after = build_candidate_identity(project)

    assert before.head_sha
    assert before.candidate_digest != after.candidate_digest


def test_result_is_invalid_after_candidate_changes(tmp_path: Path) -> None:
    project = _repo(tmp_path)
    current = build_candidate_identity(project)
    payload = {"candidate": current.to_dict()}

    assert candidate_matches(payload, current) is True

    (project / "tracked.txt").write_text("changed\n", encoding="utf-8")
    assert candidate_matches(payload, build_candidate_identity(project)) is False


def test_evidence_store_writes_atomically_and_skips_bad_history(tmp_path: Path) -> None:
    project = _repo(tmp_path)
    store = EvidenceStore(project)
    candidate = build_candidate_identity(project)
    result = ExtensionResult(
        schema_version=1,
        run_id="run-1",
        extension_id="contract-probe",
        extension_version="0.1.0",
        status=ExtensionStatus.PASS,
        canonical_stage="quality",
        source_digest="sha256:" + "0" * 64,
        candidate=candidate,
    )

    path = store.write_result(result)
    store.append_event(
        ExtensionEvent(
            schema_version=1,
            event=ExtensionEventType.COMPLETED,
            run_id="run-1",
            extension_id="contract-probe",
            canonical_stage="quality",
            actor="pytest",
            timestamp=utc_now(),
        )
    )
    with store.history_path.open("a", encoding="utf-8") as stream:
        stream.write("not-json\n")

    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "PASS"
    history = store.load_recent(limit=5)
    assert len(history.events) == 1
    assert history.warnings


def test_evidence_store_rejects_symlinked_base_outside_project(tmp_path: Path) -> None:
    project = _repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    super_dev_dir = project / ".super-dev"
    super_dev_dir.mkdir()
    link = super_dev_dir / "extensions"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"当前环境不能创建目录符号链接: {exc}")

    with pytest.raises(ValueError, match="越出项目目录"):
        EvidenceStore(project)
    assert list(outside.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows 目录联接回归测试")
def test_evidence_store_rejects_junctioned_base_outside_project(tmp_path: Path) -> None:
    project = _repo(tmp_path)
    outside = tmp_path / "junction-outside"
    outside.mkdir()
    super_dev_dir = project / ".super-dev"
    super_dev_dir.mkdir()
    link = super_dev_dir / "extensions"
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        pytest.skip(f"当前环境不能创建目录联接: {completed.stderr or completed.stdout}")

    with pytest.raises(ValueError, match="越出项目目录"):
        EvidenceStore(project)
    assert list(outside.iterdir()) == []
