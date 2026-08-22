from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from super_dev.change_ledger import StageStatus
from super_dev.config import ConfigManager, ProjectConfig
from super_dev.creators import SpecBuilder
from super_dev.shadow_ledger_lifecycle import (
    adaptive_ledger_auto_create_enabled,
    ensure_shadow_change_ledger,
)
from super_dev.shadow_ledger_store import load_shadow_ledger


def _change_dir(project_dir: Path, change_id: str = "change-1") -> Path:
    change_dir = project_dir / ".super-dev" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    return change_dir


def _ensure(project_dir: Path, change_id: str = "change-1", **overrides):
    payload = {
        "change_id": change_id,
        "harness_version": "2.4.0",
        "intent": "build",
        "governance_depth": "commercial",
        "work_mode": "new",
        "enabled": True,
        "satisfied_stages": {"spec"},
    }
    payload.update(overrides)
    return ensure_shadow_change_ledger(project_dir, **payload)


def test_disabled_auto_creation_does_not_touch_change_directory(temp_project_dir: Path) -> None:
    change_dir = _change_dir(temp_project_dir)

    result = _ensure(temp_project_dir, enabled=False)

    assert result.status == "disabled"
    assert result.succeeded is True
    assert list(change_dir.iterdir()) == []


def test_create_shadow_ledger_marks_only_observed_stages_satisfied(
    temp_project_dir: Path,
) -> None:
    change_dir = _change_dir(temp_project_dir)

    result = _ensure(
        temp_project_dir,
        satisfied_stages={"research", "docs", "docs_confirm", "spec"},
    )

    assert result.status == "created"
    assert result.read_only is True
    assert result.control_authority == "none"
    record = load_shadow_ledger(temp_project_dir, change_dir / "ledger.json")
    assert record.ledger.shadow_only is True
    assert record.ledger.get_stage("research").status == StageStatus.SATISFIED
    assert record.ledger.get_stage("spec").status == StageStatus.SATISFIED
    assert record.ledger.get_stage("frontend").status == StageStatus.PENDING


def test_repeated_creation_is_idempotent_and_does_not_overwrite(temp_project_dir: Path) -> None:
    change_dir = _change_dir(temp_project_dir)
    first = _ensure(temp_project_dir)
    ledger_path = change_dir / "ledger.json"
    original = ledger_path.read_bytes()

    second = _ensure(temp_project_dir, satisfied_stages={"delivery"})

    assert first.status == "created"
    assert second.status == "existing"
    assert ledger_path.read_bytes() == original
    assert load_shadow_ledger(temp_project_dir, ledger_path).ledger.get_stage(
        "delivery"
    ).status == StageStatus.PENDING
    assert b"\r\n" not in original


def test_invalid_existing_ledger_is_preserved_and_never_blocks_main_change(
    temp_project_dir: Path,
) -> None:
    change_dir = _change_dir(temp_project_dir)
    ledger_path = change_dir / "ledger.json"
    ledger_path.write_text("{broken", encoding="utf-8")
    original = ledger_path.read_bytes()

    result = _ensure(temp_project_dir)

    assert result.status == "invalid_existing"
    assert result.succeeded is False
    assert ledger_path.read_bytes() == original


def test_existing_ledger_with_wrong_change_id_is_preserved(temp_project_dir: Path) -> None:
    change_dir = _change_dir(temp_project_dir)
    other_dir = _change_dir(temp_project_dir, "other-change")
    assert _ensure(temp_project_dir, change_id="other-change").status == "created"
    ledger_path = change_dir / "ledger.json"
    ledger_path.write_bytes((other_dir / "ledger.json").read_bytes())
    original = ledger_path.read_bytes()

    result = _ensure(temp_project_dir)

    assert result.status == "invalid_existing"
    assert "does not match" in result.error
    assert ledger_path.read_bytes() == original


def test_missing_or_unsafe_change_path_is_not_created(temp_project_dir: Path) -> None:
    missing = _ensure(temp_project_dir, change_id="missing")
    escaped = _ensure(temp_project_dir, change_id="../escape")

    assert missing.status == "missing_change"
    assert escaped.status == "unsafe_path"
    assert not (temp_project_dir / ".super-dev" / "changes" / "missing").exists()


def test_orphan_temp_file_does_not_block_recovery(temp_project_dir: Path) -> None:
    change_dir = _change_dir(temp_project_dir)
    orphan = change_dir / ".ledger-crashed.tmp"
    orphan.write_text("partial", encoding="utf-8")

    result = _ensure(temp_project_dir)

    assert result.status == "created"
    assert (change_dir / "ledger.json").is_file()


def test_atomic_create_allows_only_one_concurrent_writer(temp_project_dir: Path) -> None:
    change_dir = _change_dir(temp_project_dir)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: _ensure(temp_project_dir), range(2)))

    assert sorted(item.status for item in results) == ["created", "existing"]
    assert load_shadow_ledger(temp_project_dir, change_dir / "ledger.json").ledger.change_id == (
        "change-1"
    )


def test_hard_link_failure_uses_exclusive_no_overwrite_fallback(
    temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change_dir = _change_dir(temp_project_dir)

    def _fail_link(_source, _destination):
        raise OSError("simulated link failure")

    monkeypatch.setattr("super_dev.shadow_ledger_lifecycle.os.link", _fail_link)

    result = _ensure(temp_project_dir)

    assert result.status == "created"
    assert load_shadow_ledger(temp_project_dir, change_dir / "ledger.json").ledger.change_id == (
        "change-1"
    )


def test_write_failure_is_reported_without_partial_final_file(
    temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    change_dir = _change_dir(temp_project_dir)

    def _fail_link(_source, _destination):
        raise OSError("simulated link failure")

    def _fail_fallback(_destination, _serialized):
        raise OSError("simulated fallback failure")

    monkeypatch.setattr("super_dev.shadow_ledger_lifecycle.os.link", _fail_link)
    monkeypatch.setattr(
        "super_dev.shadow_ledger_lifecycle._write_exclusive_fallback",
        _fail_fallback,
    )

    result = _ensure(temp_project_dir)

    assert result.status == "write_failed"
    assert not (change_dir / "ledger.json").exists()
    assert list(change_dir.glob(".ledger-*.tmp")) == []


def test_feature_switch_requires_two_strict_boolean_flags() -> None:
    assert adaptive_ledger_auto_create_enabled(ProjectConfig(name="default")) is False
    assert (
        adaptive_ledger_auto_create_enabled(
            ProjectConfig(
                name="enabled",
                adaptive_ledger={"enabled": True, "auto_create": True},
            )
        )
        is True
    )
    assert (
        adaptive_ledger_auto_create_enabled(
            ProjectConfig(
                name="string-flags",
                adaptive_ledger={"enabled": "true", "auto_create": "true"},
            )
        )
        is False
    )


def test_spec_builder_is_the_single_enabled_auto_creation_entry(
    temp_project_dir: Path,
) -> None:
    ConfigManager(temp_project_dir).create(
        name="auto-ledger-demo",
        adaptive_ledger={"enabled": True, "auto_create": True},
    )
    builder = SpecBuilder(
        project_dir=temp_project_dir,
        name="auto-ledger-demo",
        description="create a demo change",
    )

    change_id = builder.create_change(
        requirements=[
            {
                "spec_name": "demo",
                "req_name": "demo-requirement",
                "description": "demo requirement",
                "scenarios": [],
            }
        ],
        tech_stack={"platform": "web", "frontend": "react", "backend": "node"},
        scenario="0-1",
    )

    ledger_path = temp_project_dir / ".super-dev" / "changes" / change_id / "ledger.json"
    assert builder.last_shadow_ledger_result["status"] == "created"
    record = load_shadow_ledger(temp_project_dir, ledger_path)
    assert record.ledger.get_stage("spec").status == StageStatus.SATISFIED
    assert record.ledger.get_stage("quality").status == StageStatus.PENDING


def test_historical_project_outputs_do_not_mark_new_change_satisfied(
    temp_project_dir: Path,
) -> None:
    ConfigManager(temp_project_dir).create(
        name="historical-output-demo",
        adaptive_ledger={"enabled": True, "auto_create": True},
    )
    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "old-research.md").write_text("old", encoding="utf-8")
    builder = SpecBuilder(
        project_dir=temp_project_dir,
        name="historical-output-demo",
        description="create a new change after old research",
    )

    change_id = builder.create_change(
        requirements=[],
        tech_stack={"platform": "web", "frontend": "none", "backend": "node"},
        scenario="1-N+1",
    )

    record = load_shadow_ledger(
        temp_project_dir,
        temp_project_dir / ".super-dev" / "changes" / change_id / "ledger.json",
    )
    assert record.ledger.get_stage("research").status == StageStatus.PENDING
    assert record.ledger.get_stage("docs").status == StageStatus.PENDING
    assert record.ledger.get_stage("spec").status == StageStatus.SATISFIED


def test_spec_builder_default_disabled_path_creates_no_ledger(temp_project_dir: Path) -> None:
    builder = SpecBuilder(
        project_dir=temp_project_dir,
        name="disabled-ledger-demo",
        description="create a demo change",
    )

    change_id = builder.create_change(
        requirements=[],
        tech_stack={"platform": "web", "frontend": "none", "backend": "none"},
        scenario="0-1",
    )

    ledger_path = temp_project_dir / ".super-dev" / "changes" / change_id / "ledger.json"
    assert builder.last_shadow_ledger_result["status"] == "disabled"
    assert not ledger_path.exists()


def test_invalid_existing_ledger_does_not_fail_spec_creation(temp_project_dir: Path) -> None:
    ConfigManager(temp_project_dir).create(
        name="preserve-invalid",
        adaptive_ledger={"enabled": True, "auto_create": True},
    )
    change_dir = _change_dir(temp_project_dir, "preserve-invalid")
    ledger_path = change_dir / "ledger.json"
    ledger_path.write_text(json.dumps({"broken": True}), encoding="utf-8")
    original = ledger_path.read_bytes()
    builder = SpecBuilder(
        project_dir=temp_project_dir,
        name="preserve-invalid",
        description="preserve invalid shadow evidence",
    )

    change_id = builder.create_change(
        requirements=[],
        tech_stack={"platform": "web", "frontend": "none", "backend": "none"},
        scenario="1-N+1",
    )

    assert change_id == "preserve-invalid"
    assert builder.last_shadow_ledger_result["status"] == "invalid_existing"
    assert ledger_path.read_bytes() == original


def test_unexpected_shadow_error_after_tasks_does_not_fail_spec_creation(
    temp_project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ConfigManager(temp_project_dir).create(
        name="isolated-error",
        adaptive_ledger={"enabled": True, "auto_create": True},
    )
    builder = SpecBuilder(
        project_dir=temp_project_dir,
        name="isolated-error",
        description="isolate an unexpected shadow failure",
    )

    def _raise_unexpected(*_args, **_kwargs):
        raise RuntimeError("unexpected shadow failure")

    monkeypatch.setattr(
        "super_dev.creators.spec_builder.ensure_shadow_change_ledger",
        _raise_unexpected,
    )

    change_id = builder.create_change(
        requirements=[],
        tech_stack={"platform": "web", "frontend": "none", "backend": "node"},
        scenario="1-N+1",
    )

    assert change_id == "isolated-error"
    assert builder.last_shadow_ledger_result["status"] == "write_failed"
    assert "unexpected shadow failure" in builder.last_shadow_ledger_result["error"]
    assert (
        temp_project_dir / ".super-dev" / "changes" / change_id / "tasks.md"
    ).is_file()
