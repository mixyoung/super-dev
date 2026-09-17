from __future__ import annotations

from pathlib import Path

from super_dev.config import ConfigManager
from super_dev.expert_stage_governance import collect_expert_stage_governance
from super_dev.orchestrator.engine import Phase, WorkflowEngine
from super_dev.review_state import load_workflow_state


def test_engine_records_progress_without_pipeline_state_file(tmp_path: Path) -> None:
    ConfigManager(tmp_path).create(name="engine-state-test")
    engine = WorkflowEngine(tmp_path)

    engine._record_engine_progress("discovery", [Phase.DISCOVERY, Phase.DRAFTING], {})

    assert not (tmp_path / ".super-dev" / "pipeline-state.json").exists()
    state = load_workflow_state(tmp_path) or {}
    assert state["current_stage"] == "research"
    assert state["engine_progress"]["current_phase"] == "discovery"
    assert state["engine_progress"]["canonical_phase"] == "research"


def test_expert_governance_reads_current_stage_from_workflow_state(tmp_path: Path) -> None:
    ConfigManager(tmp_path).create(name="expert-state-test")
    engine = WorkflowEngine(tmp_path)
    engine._record_engine_progress("qa", [Phase.QA], {})

    report = collect_expert_stage_governance(
        tmp_path,
        stage_statuses={"quality": "running"},
    )

    assert report["current_stage"] == "quality"
    quality = next(item for item in report["stages"] if item["stage"] == "quality")
    assert set(quality["recorded_experts"]) >= {"QA", "SECURITY"}
