from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from super_dev.change_ledger import ChangeLedger
from super_dev.shadow_ledger_store import (
    ShadowLedgerReadError,
    build_shadow_ledger_summary,
    list_shadow_ledger_paths,
    load_shadow_ledger,
)


def _write_ledger(project_dir: Path, change_id: str) -> Path:
    ledger = ChangeLedger.create(
        change_id=change_id,
        harness_version="2.4.0",
        intent="build",
        governance_depth="commercial",
        work_mode="evolve",
    )
    ledger_path = project_dir / ".super-dev" / "changes" / change_id / "ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(ledger.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ledger_path


def test_summary_is_quiet_when_no_shadow_ledger_exists(temp_project_dir: Path) -> None:
    summary = build_shadow_ledger_summary(temp_project_dir)

    assert summary["present"] is False
    assert summary["read_only"] is True
    assert summary["control_authority"] == "none"
    assert summary["summary"] == "未检测到影子九阶段账本"


def test_summary_reads_valid_canonical_ledger_without_control_authority(
    temp_project_dir: Path,
) -> None:
    ledger_path = _write_ledger(temp_project_dir, "change-1")

    summary = build_shadow_ledger_summary(temp_project_dir)

    assert summary["present"] is True
    assert summary["read_only"] is True
    assert summary["control_authority"] == "none"
    assert summary["valid_count"] == 1
    assert summary["invalid_count"] == 0
    assert summary["active_change_id"] == "change-1"
    assert summary["ledger_path"] == ".super-dev/changes/change-1/ledger.json"
    assert summary["resolution_counts"] == {"EXECUTE": 7, "REQUIRE": 2}
    assert summary["status_counts"] == {"PENDING": 9}
    assert load_shadow_ledger(temp_project_dir, ledger_path).ledger.change_id == "change-1"


def test_invalid_json_is_reported_without_breaking_status_reads(temp_project_dir: Path) -> None:
    ledger_path = temp_project_dir / ".super-dev" / "changes" / "broken" / "ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("{broken", encoding="utf-8")

    summary = build_shadow_ledger_summary(temp_project_dir)

    assert summary["present"] is True
    assert summary["valid_count"] == 0
    assert summary["invalid_count"] == 1
    assert summary["errors"][0]["path"] == ".super-dev/changes/broken/ledger.json"
    assert "未通过校验" in summary["summary"]


def test_discovery_is_limited_to_one_change_directory_level(temp_project_dir: Path) -> None:
    nested = temp_project_dir / ".super-dev" / "changes" / "change-1" / "nested" / "ledger.json"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("{}", encoding="utf-8")

    assert list_shadow_ledger_paths(temp_project_dir) == []
    assert build_shadow_ledger_summary(temp_project_dir)["present"] is False


def test_direct_reader_rejects_paths_outside_changes_root(temp_project_dir: Path) -> None:
    outside = temp_project_dir / "ledger.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ShadowLedgerReadError, match="escapes"):
        load_shadow_ledger(temp_project_dir, outside)


def test_oversized_ledger_is_reported_as_invalid(
    temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_ledger(temp_project_dir, "too-large")
    monkeypatch.setattr("super_dev.shadow_ledger_store.MAX_LEDGER_BYTES", 16)

    summary = build_shadow_ledger_summary(temp_project_dir)

    assert summary["valid_count"] == 0
    assert summary["invalid_count"] == 1
    assert summary["errors"][0]["error"] == "Ledger file exceeds the read-only size limit"


def test_discovery_reports_when_directory_entry_limit_is_reached(
    temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_ledger(temp_project_dir, "change-1")
    _write_ledger(temp_project_dir, "change-2")
    monkeypatch.setattr("super_dev.shadow_ledger_store.MAX_LEDGER_FILES", 1)

    summary = build_shadow_ledger_summary(temp_project_dir)

    assert summary["discovery_truncated"] is True
    assert summary["valid_count"] == 1
    assert summary["active_change_id"] == ""
    assert "未选择当前账本" in summary["summary"]


def test_symlink_to_ledger_outside_project_is_ignored(temp_project_dir: Path) -> None:
    outside_dir = temp_project_dir.parent / f"{temp_project_dir.name}-outside-ledger"
    try:
        outside_dir.mkdir(parents=True, exist_ok=True)
        outside_ledger = _write_ledger(outside_dir, "outside")
        link_path = temp_project_dir / ".super-dev" / "changes" / "linked" / "ledger.json"
        link_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(outside_ledger, link_path)
        except OSError as exc:
            pytest.skip(f"当前 Windows 环境不允许创建测试符号链接: {exc}")

        assert list_shadow_ledger_paths(temp_project_dir) == []
        assert build_shadow_ledger_summary(temp_project_dir)["present"] is False
    finally:
        shutil.rmtree(outside_dir, ignore_errors=True)


def test_non_shadow_ledger_is_reported_as_invalid(temp_project_dir: Path) -> None:
    ledger_path = _write_ledger(temp_project_dir, "not-shadow")
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    payload["shadow_only"] = False
    ledger_path.write_text(json.dumps(payload), encoding="utf-8")

    summary = build_shadow_ledger_summary(temp_project_dir)

    assert summary["valid_count"] == 0
    assert summary["invalid_count"] == 1
    assert "shadow-only" in summary["errors"][0]["error"]
