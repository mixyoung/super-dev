from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.state_store import (
    PipelineStateMigrationError,
    StateConflictError,
    StateStore,
)


def test_state_store_commits_revision_history_and_event(tmp_path: Path) -> None:
    store = StateStore(tmp_path)

    first = store.commit_workflow(
        {
            "work_item_id": "state-test",
            "artifact_prefix": "state-test",
            "binding_status": "pre_spec",
            "active_change_id": "",
            "status": "research",
        }
    )
    second = store.commit_workflow(
        {**first.payload, "status": "docs"},
        expected_revision=first.revision,
    )

    assert first.revision == 1
    assert second.revision == 2
    assert store.load_workflow()["revision"] == 2
    assert (tmp_path / ".super-dev" / "workflow-history" / "latest.json").is_file()
    brief = (tmp_path / ".super-dev" / "SESSION_BRIEF.md").read_text(encoding="utf-8")
    assert "来源工作项: state-test" in brief
    assert "状态修订: 2" in brief
    assert store.session_brief_health()["current"] is True
    events = (tmp_path / ".super-dev" / "workflow-events.jsonl").read_text(encoding="utf-8")
    assert '"revision": 2' in events


def test_state_store_rejects_stale_expected_revision(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    current = store.commit_workflow({"status": "research"})
    store.commit_workflow({**current.payload, "status": "docs"})

    with pytest.raises(StateConflictError, match="expected revision 1"):
        store.commit_workflow(
            {**current.payload, "status": "quality"},
            expected_revision=1,
        )

    assert store.load_workflow()["status"] == "docs"


def test_state_store_migrates_and_removes_legacy_pipeline_state(tmp_path: Path) -> None:
    superdev = tmp_path / ".super-dev"
    superdev.mkdir()
    legacy = superdev / "pipeline-state.json"
    legacy.write_text(
        json.dumps(
            {
                "current_phase": "qa",
                "canonical_phase": "quality",
                "phase_index": 5,
                "total_phases": 7,
                "phases_completed": ["discovery", "intelligence", "drafting", "redteam"],
                "phases_remaining": ["qa", "delivery", "deployment"],
                "canonical_phases_completed": ["research", "docs", "quality"],
                "canonical_phases_remaining": ["quality", "delivery"],
                "active_experts": ["QA", "SECURITY"],
            }
        ),
        encoding="utf-8",
    )

    result = StateStore(tmp_path).commit_workflow(
        {
            "work_item_id": "migration-test",
            "artifact_prefix": "migration-test",
            "binding_status": "pre_spec",
            "active_change_id": "",
            "status": "quality",
            "current_stage": "quality",
        }
    )

    assert not legacy.exists()
    assert result.payload["engine_progress"]["current_phase"] == "qa"
    receipts = list((superdev / "workflow-history").glob("pipeline-state-migration-*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert receipt["status"] == "migrated"
    assert receipt["source_sha256"]


def test_state_store_does_not_delete_invalid_pipeline_state(tmp_path: Path) -> None:
    superdev = tmp_path / ".super-dev"
    superdev.mkdir()
    legacy = superdev / "pipeline-state.json"
    legacy.write_text("{broken", encoding="utf-8")

    with pytest.raises(PipelineStateMigrationError):
        StateStore(tmp_path).commit_workflow({"status": "research"})

    assert legacy.exists()
    assert not (superdev / "workflow-state.json").exists()


def test_state_store_falls_back_to_latest_snapshot_for_read(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    committed = store.commit_workflow({"status": "docs_confirm"})
    (tmp_path / ".super-dev" / "workflow-state.json").write_text("{broken", encoding="utf-8")

    recovered = store.load_workflow()

    assert recovered["status"] == "docs_confirm"
    assert recovered["revision"] == committed.revision


def test_session_brief_health_repairs_stale_summary(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    committed = store.commit_workflow({"work_item_id": "repair-test", "status": "research"})
    store.session_brief_path.write_text(
        "# Super Dev Session Brief\n\n- 来源工作项: old\n- 状态修订: 0\n",
        encoding="utf-8",
    )

    health = store.session_brief_health(repair=True)

    assert health["status"] == "repaired"
    assert health["current"] is True
    brief = store.session_brief_path.read_text(encoding="utf-8")
    assert "来源工作项: repair-test" in brief
    assert f"状态修订: {committed.revision}" in brief
