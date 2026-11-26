from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from super_dev.config import ConfigManager
from super_dev.orchestrator import engine as engine_module
from super_dev.orchestrator.engine import Phase, PhaseResult, WorkflowContext, WorkflowEngine
from super_dev.review_state import (
    load_workflow_state,
    save_docs_confirmation,
    save_preview_confirmation,
    save_workflow_state,
)
from super_dev.state_store import StateStore, StateStoreError
from super_dev.work_item_identity import start_standard_work_item
from super_dev.workflow_guard import (
    WorkflowGateError,
    collect_docs_artifact_binding,
    collect_preview_artifact_binding,
    docs_gate_status,
    load_stage_ledger,
    preview_gate_status,
    require_docs_confirmation,
    require_preview_confirmation,
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)
from super_dev.workflow_state import detect_flow_variant, detect_pipeline_summary
from tests.support.workflow_reliability import prepare_work_item as _prepare_work_item


@pytest.fixture
def isolated_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[], WorkflowEngine]:
    for flag in (
        "GOVERNANCE_AVAILABLE",
        "KNOWLEDGE_PUSHER_AVAILABLE",
        "HOOKS_AVAILABLE",
        "COMPACT_AVAILABLE",
        "MEMORY_AVAILABLE",
        "COST_TRACKER_AVAILABLE",
        "PLAN_EXECUTOR_AVAILABLE",
        "OVERSEER_AVAILABLE",
    ):
        monkeypatch.setattr(engine_module, flag, False)
    monkeypatch.setattr(
        engine_module, "get_logger", lambda *args, **kwargs: logging.getLogger(__name__)
    )
    monkeypatch.setattr("super_dev.webhooks.send_webhook", lambda *args, **kwargs: None)

    def create() -> WorkflowEngine:
        engine = WorkflowEngine(tmp_path)
        engine.console = None
        monkeypatch.setattr(engine, "_calculate_quality_score", lambda *args: 95.0)
        return engine

    return create


@pytest.mark.asyncio
@pytest.mark.parametrize("default_phases", [False, True])
async def test_confirmation_is_rechecked_after_document_generation(
    tmp_path: Path,
    isolated_engine: Callable[[], WorkflowEngine],
    default_phases: bool,
) -> None:
    output = _prepare_work_item(tmp_path)
    engine = isolated_engine()
    engine.config_manager.config.phases = ["drafting", "redteam"]
    calls: list[str] = []

    async def draft(context):
        calls.append("drafting")
        (output / "current-prd.md").write_text("changed requirements", encoding="utf-8")
        return {"generated": True}

    async def redteam(context):
        calls.append("redteam")
        return {"passed": True}

    engine.register_phase_handler(Phase.DRAFTING, draft)
    engine.register_phase_handler(Phase.REDTEAM, redteam)
    with pytest.raises(WorkflowGateError) as blocked:
        await engine.run(phases=None if default_phases else [Phase.DRAFTING, Phase.REDTEAM])

    assert blocked.value.gate == "docs_confirmation"
    assert calls == ["drafting"]
    assert not (tmp_path / ".super-dev" / "checkpoints" / "redteam.json").exists()


@pytest.mark.parametrize("phase", ["backend", "quality", "delivery"])
def test_ui_without_preview_evidence_is_blocked(tmp_path: Path, phase: str) -> None:
    _prepare_work_item(tmp_path, frontend="react")

    with pytest.raises(WorkflowGateError) as blocked:
        require_preview_confirmation(
            tmp_path, action="regression", requested_phases=[phase], require_context=True
        )

    assert blocked.value.gate == "preview_confirmation"
    assert preview_gate_status(tmp_path)["confirmed"] is False


@pytest.mark.parametrize("frontend,variant", [("none", "standard"), ("react", "seeai")])
def test_explicit_preview_exemptions_remain_usable(
    tmp_path: Path, frontend: str, variant: str
) -> None:
    _prepare_work_item(tmp_path, frontend=frontend)
    if variant == "seeai":
        save_workflow_state(tmp_path, {**load_workflow_state(tmp_path), "flow_variant": variant})

    require_preview_confirmation(
        tmp_path, action="regression", requested_phases=["backend"], require_context=True
    )


@pytest.mark.parametrize(
    "runtime",
    [None, '{"passed": false}', "{}", '{"passed": "false"}', "{broken", "[]"],
)
def test_unready_runtime_cannot_be_confirmed(tmp_path: Path, runtime: str | None) -> None:
    output = _prepare_work_item(tmp_path, frontend="react")
    if runtime is not None:
        (output / "current-frontend-runtime.json").write_text(runtime, encoding="utf-8")

    with pytest.raises(WorkflowGateError) as blocked:
        save_bound_preview_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})

    assert blocked.value.gate == "preview_confirmation"
    assert preview_gate_status(tmp_path)["confirmed"] is False
    assert not (tmp_path / ".super-dev/review-state/preview-confirmation.json").exists()


def test_previously_confirmed_failed_runtime_cannot_allow_backend(tmp_path: Path) -> None:
    output = _prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": false}', encoding="utf-8")
    save_preview_confirmation(
        tmp_path,
        {
            "status": "confirmed",
            "work_item_id": "current",
            "artifact_binding": collect_preview_artifact_binding(tmp_path),
        },
    )

    assert preview_gate_status(tmp_path)["confirmed"] is False
    with pytest.raises(WorkflowGateError):
        require_preview_confirmation(tmp_path, action="regression", requested_phases=["backend"])


def test_passed_current_runtime_can_be_confirmed(tmp_path: Path) -> None:
    output = _prepare_work_item(tmp_path, frontend="react")
    report = output / "current-frontend-runtime.json"
    report.write_text('{"passed": true}', encoding="utf-8")
    save_bound_preview_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})

    assert preview_gate_status(tmp_path)["confirmed"] is True
    require_preview_confirmation(tmp_path, action="regression", requested_phases=["backend"])
    report.write_text('{"passed": true, "updated": true}', encoding="utf-8")
    with pytest.raises(WorkflowGateError):
        require_preview_confirmation(tmp_path, action="regression", requested_phases=["backend"])


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [Phase.REDTEAM, Phase.QA])
@pytest.mark.parametrize("malformed_session", [False, True])
async def test_failed_acceptance_does_not_leave_a_success_checkpoint(
    tmp_path: Path,
    isolated_engine: Callable[[], WorkflowEngine],
    phase: Phase,
    malformed_session: bool,
) -> None:
    _prepare_work_item(tmp_path)
    if malformed_session:
        session_path = tmp_path / ".super-dev/checkpoints/sessions/latest.json"
        session_path.parent.mkdir(parents=True)
        session_path.write_text('{"completed_phases": null}', encoding="utf-8")
    calls: list[str] = []
    following = Phase.QA if phase == Phase.REDTEAM else Phase.DELIVERY

    async def fail(context):
        calls.append(phase.value)
        if phase == Phase.REDTEAM:
            return {"passed": False, "score": 52, "blocking_reasons": ["regression"]}
        return PhaseResult(phase=phase, success=True, duration=0.01, quality_score=85)

    async def later(context):
        calls.append(following.value)
        return {"passed": True}

    for resume in (False, True):
        engine = isolated_engine()
        engine.register_phase_handler(phase, fail)
        engine.register_phase_handler(following, later)
        results = await engine.run(phases=[phase, following], resume=resume)
        assert results[phase].success is False
        assert following not in results
        checkpoint = engine._load_checkpoint(phase)
        assert checkpoint is None or checkpoint["success"] is False
        assert load_stage_ledger(tmp_path)["quality"]["status"] != "completed"
        session_path = tmp_path / ".super-dev/checkpoints/sessions/latest.json"
        if session_path.exists():
            assert phase.value not in json.loads(session_path.read_text())["completed_phases"]

    assert calls == [phase.value, phase.value]


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [Phase.REDTEAM, Phase.QA])
async def test_legacy_quality_checkpoint_without_acceptance_is_rerun(
    tmp_path: Path, isolated_engine: Callable[[], WorkflowEngine], phase: Phase
) -> None:
    _prepare_work_item(tmp_path)
    engine = isolated_engine()
    engine._checkpoint_dir.mkdir(parents=True)
    (engine._checkpoint_dir / f"{phase.value}.json").write_text(
        json.dumps(
            {"phase": phase.value, "success": True, "quality_score": 95, "project": "current"}
        ),
        encoding="utf-8",
    )
    calls: list[Phase] = []

    async def handler(context):
        calls.append(phase)
        return {"passed": True}

    engine.register_phase_handler(phase, handler)
    results = await engine.run(phases=[phase], resume=True)

    assert calls == [phase]
    assert results[phase].success is True


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [Phase.REDTEAM, Phase.QA])
async def test_accepted_quality_checkpoint_can_be_resumed(
    tmp_path: Path, isolated_engine: Callable[[], WorkflowEngine], phase: Phase
) -> None:
    _prepare_work_item(tmp_path)
    calls: list[Phase] = []

    async def handler(context):
        calls.append(phase)
        return {"passed": True}

    for resume in (False, True):
        engine = isolated_engine()
        engine.register_phase_handler(phase, handler)
        results = await engine.run(phases=[phase], resume=resume)
        assert results[phase].success is True

    assert calls == [phase]


@pytest.mark.parametrize("invalid", ["{broken", "[]", "null", '"state"', "42", "true", "false"])
@pytest.mark.parametrize("wrapper", [False, True, "automatic"])
def test_all_invalid_primary_states_block_ordinary_writes(
    tmp_path: Path, invalid: str, wrapper: bool | str
) -> None:
    store = StateStore(tmp_path)
    store.commit_workflow({"status": "docs_confirm"})
    store.workflow_path.write_text(invalid, encoding="utf-8")
    before = {
        path.relative_to(store.state_dir): path.read_bytes()
        for path in store.state_dir.rglob("*")
        if path.is_file()
    }
    recovered = load_workflow_state(tmp_path)
    assert recovered is not None
    assert recovered["status"] == "docs_confirm"
    assert store.workflow_health()["status"] == "corrupt"
    assert store.prepare_recovery() is not None

    with pytest.raises(StateStoreError, match="损坏"):
        if wrapper:
            update = {**recovered, "status": "quality"}
            if wrapper == "automatic":
                update.pop("revision", None)
            save_workflow_state(tmp_path, update)
        else:
            store.commit_workflow({**recovered, "status": "quality"})

    after = {
        path.relative_to(store.state_dir): path.read_bytes()
        for path in store.state_dir.rglob("*")
        if path.is_file()
    }
    assert after == before


@pytest.mark.parametrize(
    "files",
    [
        ["example-prd.md"],
        ["example-prd.md", "example-architecture.md"],
        ["example-prd.md", "other-architecture.md", "other-uiux.md"],
    ],
)
def test_legacy_incomplete_or_mixed_docs_cannot_allow_spec(
    tmp_path: Path, files: list[str]
) -> None:
    ConfigManager(tmp_path).create(name="example", platform="cli", frontend="none")
    output = tmp_path / "output"
    output.mkdir()
    for name in files:
        (output / name).write_text(name, encoding="utf-8")
    with pytest.raises(WorkflowGateError):
        save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    # 旧版本可能已经保存了非法确认；读取和执行也必须拒绝。
    save_docs_confirmation(
        tmp_path,
        {"status": "confirmed", "artifact_binding": collect_docs_artifact_binding(tmp_path)},
    )

    assert docs_gate_status(tmp_path)["core_complete"] is False
    with pytest.raises(WorkflowGateError):
        require_docs_confirmation(
            tmp_path, action="regression", requested_phases=["spec"], require_context=False
        )


def test_complete_legacy_core_docs_remain_confirmable(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    for suffix in ("prd", "architecture", "uiux"):
        (output / f"example-{suffix}.md").write_text(suffix, encoding="utf-8")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})

    assert docs_gate_status(tmp_path)["core_complete"] is True
    require_docs_confirmation(
        tmp_path, action="regression", requested_phases=["spec"], require_context=False
    )


def test_pre_spec_summary_does_not_inherit_old_work_item_artifacts(tmp_path: Path) -> None:
    output = _prepare_work_item(tmp_path, frontend="react", work_item_id="old")
    (output / "old-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    (output / "old-quality-gate.md").write_text("old quality", encoding="utf-8")
    delivery = output / "delivery"
    delivery.mkdir()
    (delivery / "old-delivery-manifest.json").write_text('{"status": "ready"}', encoding="utf-8")
    save_workflow_state(tmp_path, {**load_workflow_state(tmp_path), "status": "completed"})
    start_standard_work_item(tmp_path, "new")

    summary = detect_pipeline_summary(tmp_path)

    assert summary["artifact_prefix"] == "new"
    assert summary["active_change_id"] == ""
    assert summary["workflow_status"] == "missing_research"
    assert summary["current_stage_canonical_id"] == "research"
    for key in (
        "research",
        "prd",
        "architecture",
        "uiux",
        "spec",
        "frontend",
        "quality",
        "delivery",
    ):
        assert summary["artifacts"][key] is False, key
    assert all(stage["status"] == "pending" for stage in summary["stages"][:4])


def test_summary_cannot_infer_docs_confirmation_from_existing_spec(tmp_path: Path) -> None:
    _prepare_work_item(tmp_path)
    save_bound_docs_confirmation(tmp_path, {"status": "pending_review", "actor": "user"})

    summary = detect_pipeline_summary(tmp_path)
    stages = {stage["canonical_id"]: stage["status"] for stage in summary["stages"]}

    assert stages["docs_confirm"] == "waiting"
    assert summary["workflow_status"] == "waiting_docs_confirmation"


def test_summary_cannot_infer_preview_confirmation_from_existing_backend(tmp_path: Path) -> None:
    output = _prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    (tmp_path / "backend" / "src").mkdir(parents=True)

    summary = detect_pipeline_summary(tmp_path)
    stages = {stage["canonical_id"]: stage["status"] for stage in summary["stages"]}

    assert stages["preview_confirm"] == "waiting"
    assert summary["workflow_status"] == "waiting_preview_confirmation"


@pytest.mark.parametrize("suffix", ["ui-review.json", "ui-review.md", "ui-contract-alignment.json"])
def test_quality_report_refresh_does_not_require_a_second_preview(
    tmp_path: Path, suffix: str
) -> None:
    output = _prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    report = output / f"current-{suffix}"
    report.write_text("initial review", encoding="utf-8")
    save_bound_preview_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    report.write_text("refreshed by QA", encoding="utf-8")

    assert preview_gate_status(tmp_path)["confirmed"] is True
    require_preview_confirmation(tmp_path, action="regression", requested_phases=["delivery"])


def test_changed_ui_contract_invalidates_preview_confirmation(tmp_path: Path) -> None:
    output = _prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    contract = output / "current-ui-contract.json"
    contract.write_text('{"version": 1}', encoding="utf-8")
    save_bound_preview_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    contract.write_text('{"version": 2}', encoding="utf-8")

    assert preview_gate_status(tmp_path)["confirmed"] is False
    with pytest.raises(WorkflowGateError):
        require_preview_confirmation(tmp_path, action="regression", requested_phases=["backend"])


@pytest.mark.asyncio
async def test_recheck_happens_before_skipping_a_cached_later_phase(
    tmp_path: Path, isolated_engine: Callable[[], WorkflowEngine]
) -> None:
    output = _prepare_work_item(tmp_path)
    calls: list[str] = []

    async def redteam(context):
        calls.append("redteam")
        return {"passed": True}

    engine = isolated_engine()
    engine.register_phase_handler(Phase.REDTEAM, redteam)
    await engine.run(phases=[Phase.REDTEAM])

    async def draft(context):
        calls.append("drafting")
        (output / "current-prd.md").write_text("new document", encoding="utf-8")
        return {"generated": True}

    engine = isolated_engine()
    engine.register_phase_handler(Phase.DRAFTING, draft)
    engine.register_phase_handler(Phase.REDTEAM, redteam)
    with pytest.raises(WorkflowGateError):
        await engine.run(phases=[Phase.DRAFTING, Phase.REDTEAM], resume=True)

    assert calls == ["redteam", "drafting"]


@pytest.mark.asyncio
@pytest.mark.parametrize("early_error", [False, True])
async def test_failed_handlers_preserve_results_and_do_not_emit_success(
    tmp_path: Path,
    isolated_engine: Callable[[], WorkflowEngine],
    early_error: bool,
) -> None:
    from types import SimpleNamespace

    from super_dev.exceptions import QualityGateError

    _prepare_work_item(tmp_path)
    engine = isolated_engine()
    notifications: list[dict] = []
    compacted: list[str] = []
    engine.hook_manager = SimpleNamespace(
        execute=lambda event, **kwargs: notifications.append(kwargs["context"]) or [],
        has_blocking_result=lambda results: False,
    )
    engine.compact_engine = SimpleNamespace(
        compact_phase_output=lambda *args: compacted.append("success"),
        save_compact=lambda summary: None,
    )

    async def fail(context):
        if early_error:
            raise QualityGateError(score=52, threshold=90, details={"report_path": "report.md"})
        return PhaseResult(
            phase=Phase.QA,
            success=False,
            duration=0.01,
            quality_score=52,
            output={"report_path": "report.md"},
            errors=["rejected"],
        )

    engine.register_phase_handler(Phase.QA, fail)
    results = await engine.run(phases=[Phase.QA])

    assert results[Phase.QA].success is False
    assert results[Phase.QA].output["report_path"] == "report.md"
    assert results[Phase.QA].quality_score == 52
    assert results[Phase.QA].errors
    assert notifications[-1]["success"] == "False"
    assert not any(event.get("success") == "True" for event in notifications)
    assert compacted == []
    assert engine._load_checkpoint(Phase.QA) is None
    assert load_workflow_state(tmp_path)["pipeline_run_state"]["status"] == "failed"


def test_valid_empty_primary_object_is_not_replaced_by_history(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.commit_workflow({"status": "docs_confirm"})
    store.workflow_path.write_text("{}", encoding="utf-8")

    assert store.load_workflow() == {}
    assert store.workflow_health()["status"] == "ok"
    assert store.workflow_path.read_text(encoding="utf-8") == "{}"


def test_unconditional_save_cannot_bypass_corrupt_state(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    store.commit_workflow({"status": "docs_confirm"})
    store.workflow_path.write_text("[]", encoding="utf-8")

    with pytest.raises(StateStoreError, match="损坏"):
        store.commit_workflow({"status": "quality"}, allow_unconditional=True)
    assert store.workflow_path.read_text(encoding="utf-8") == "[]"


@pytest.mark.asyncio
async def test_corrupt_state_stops_engine_before_phase_dispatch(
    tmp_path: Path, isolated_engine: Callable[[], WorkflowEngine]
) -> None:
    _prepare_work_item(tmp_path)
    state = tmp_path / ".super-dev" / "workflow-state.json"
    state.write_text("null", encoding="utf-8")
    calls: list[str] = []

    async def handler(context):
        calls.append("qa")
        return {"passed": True}

    engine = isolated_engine()
    engine.register_phase_handler(Phase.QA, handler)
    with pytest.raises(WorkflowGateError) as blocked:
        await engine.run(phases=[Phase.QA])

    assert blocked.value.gate == "workflow_recovery"
    assert calls == []
    assert state.read_text(encoding="utf-8") == "null"


def test_invalid_explicit_identity_never_scans_other_work_items(tmp_path: Path) -> None:
    _prepare_work_item(tmp_path, frontend="react", work_item_id="old")
    state = tmp_path / ".super-dev" / "workflow-state.json"
    state.write_text(
        json.dumps({"work_item_id": "../invalid", "binding_status": "pre_spec"}), encoding="utf-8"
    )
    before = state.read_bytes()

    summary = detect_pipeline_summary(tmp_path)

    assert summary["workflow_status"] == "invalid_work_item_identity"
    assert summary["current_stage_canonical_id"] == "research"
    assert summary["artifacts"]["research"] is False
    assert summary["artifacts"]["spec"] is False
    assert state.read_bytes() == before


@pytest.mark.asyncio
async def test_reconfirmed_changed_documents_invalidate_cached_quality_acceptance(
    tmp_path: Path, isolated_engine: Callable[[], WorkflowEngine]
) -> None:
    output = _prepare_work_item(tmp_path)
    calls: list[str] = []

    async def qa(context):
        calls.append("qa")
        return {"passed": True}

    engine = isolated_engine()
    engine.register_phase_handler(Phase.QA, qa)
    await engine.run(phases=[Phase.QA])
    (output / "current-prd.md").write_text("new confirmed requirements", encoding="utf-8")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    engine = isolated_engine()
    engine.register_phase_handler(Phase.QA, qa)
    await engine.run(phases=[Phase.QA], resume=True)

    assert calls == ["qa", "qa"]


@pytest.mark.asyncio
async def test_quality_checkpoint_is_not_shared_by_different_work_items(
    tmp_path: Path, isolated_engine: Callable[[], WorkflowEngine]
) -> None:
    _prepare_work_item(tmp_path)
    ConfigManager(tmp_path).update(name="same-project")
    calls: list[str] = []

    async def qa(context):
        calls.append("qa")
        return {"passed": True}

    engine = isolated_engine()
    engine.register_phase_handler(Phase.QA, qa)
    await engine.run(phases=[Phase.QA])
    save_workflow_state(tmp_path, {**load_workflow_state(tmp_path), "status": "completed"})
    _prepare_work_item(tmp_path, work_item_id="second")
    ConfigManager(tmp_path).update(name="same-project")
    engine = isolated_engine()
    engine.register_phase_handler(Phase.QA, qa)
    await engine.run(phases=[Phase.QA], resume=True)

    assert calls == ["qa", "qa"]


@pytest.mark.parametrize("keep_latest", [False, True])
@pytest.mark.parametrize("writer", ["direct", "wrapper", "automatic", "unconditional"])
def test_missing_primary_with_history_requires_explicit_recovery(
    tmp_path: Path, keep_latest: bool, writer: str
) -> None:
    store = StateStore(tmp_path)
    first = store.commit_workflow({"status": "docs_confirm"})
    store.workflow_path.unlink()
    if not keep_latest:
        store.latest_path.unlink()
    before = {
        path.relative_to(store.state_dir): path.read_bytes()
        for path in store.state_dir.rglob("*")
        if path.is_file()
    }
    assert store.workflow_health()["status"] == "missing_current"
    payload = {**first.payload, "status": "quality"}
    with pytest.raises(StateStoreError, match="缺失"):
        if writer in {"wrapper", "automatic"}:
            if writer == "automatic":
                payload.pop("revision")
            save_workflow_state(tmp_path, payload)
        elif writer == "unconditional":
            store.commit_workflow(payload, allow_unconditional=True)
        else:
            store.commit_workflow(payload)
    after = {
        path.relative_to(store.state_dir): path.read_bytes()
        for path in store.state_dir.rglob("*")
        if path.is_file()
    }
    assert after == before
    candidate = store.prepare_recovery()
    assert candidate is not None
    store.apply_recovery(candidate)
    recovered = store.load_workflow()
    assert recovered["revision"] == first.revision
    committed = store.commit_workflow({**recovered, "status": "quality"})
    assert committed.revision == first.revision + 1


@pytest.mark.parametrize(
    "variant_key", ["entry_variant", "pipeline_variant", "mode_variant", "current_step_label"]
)
def test_legacy_seeai_mode_keeps_its_existing_preview_exemption(
    tmp_path: Path, variant_key: str
) -> None:
    output = _prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    legacy = dict(load_workflow_state(tmp_path))
    for key in ("work_item_id", "flow_variant", "binding_status", "document_binding_digest"):
        legacy.pop(key, None)
    legacy[variant_key] = (
        "SEEAI full-stack sprint" if variant_key == "current_step_label" else "seeai"
    )
    save_workflow_state(tmp_path, legacy)

    assert detect_flow_variant(tmp_path) == "seeai"
    assert preview_gate_status(tmp_path)["required"] is False
    require_preview_confirmation(tmp_path, action="regression", requested_phases=["backend"])
    summary = detect_pipeline_summary(tmp_path)
    preview = next(
        stage for stage in summary["stages"] if stage["canonical_id"] == "preview_confirm"
    )
    assert preview["status"] == "not_applicable"
    assert summary["workflow_status"] == "missing_backend"


def test_explicit_standard_mode_is_not_overridden_by_legacy_seeai_labels(tmp_path: Path) -> None:
    output = _prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    save_workflow_state(
        tmp_path,
        {
            **load_workflow_state(tmp_path),
            "flow_variant": "standard",
            "entry_variant": "seeai",
            "current_step_label": "SEEAI is historical",
        },
    )

    assert detect_flow_variant(tmp_path) == "standard"
    assert preview_gate_status(tmp_path)["required"] is True
    with pytest.raises(WorkflowGateError):
        require_preview_confirmation(tmp_path, action="regression", requested_phases=["backend"])


@pytest.mark.parametrize(
    "history_name", ["workflow-state-r00000001-broken.json", "workflow-state-20260917.json"]
)
@pytest.mark.parametrize("invalid", ["[]", "{broken"])
@pytest.mark.parametrize("writer", ["direct", "wrapper", "unconditional"])
def test_unrecoverable_history_is_not_treated_as_a_new_workflow(
    tmp_path: Path, history_name: str, invalid: str, writer: str
) -> None:
    store = StateStore(tmp_path)
    store.commit_workflow({"status": "docs_confirm"})
    store.workflow_path.unlink()
    store.latest_path.unlink()
    snapshot = next(store.history_dir.glob("workflow-state-*.json"))
    snapshot.write_text(invalid, encoding="utf-8")
    snapshot.rename(store.history_dir / history_name)
    assert store.prepare_recovery() is None
    before = {
        path.relative_to(store.state_dir): path.read_bytes()
        for path in store.state_dir.rglob("*")
        if path.is_file()
    }

    with pytest.raises(StateStoreError, match="缺失"):
        if writer == "wrapper":
            save_workflow_state(tmp_path, {"status": "quality"})
        else:
            store.commit_workflow(
                {"status": "quality"}, allow_unconditional=writer == "unconditional"
            )

    assert store.workflow_health()["status"] == "missing_current"
    assert store.workflow_health()["candidates"] == []
    after = {
        path.relative_to(store.state_dir): path.read_bytes()
        for path in store.state_dir.rglob("*")
        if path.is_file()
    }
    assert after == before


@pytest.mark.asyncio
@pytest.mark.parametrize("override_display_name", [False, True])
async def test_real_drafting_uses_document_owner_not_product_display_name(
    tmp_path: Path,
    isolated_engine: Callable[[], WorkflowEngine],
    monkeypatch: pytest.MonkeyPatch,
    override_display_name: bool,
) -> None:
    from types import SimpleNamespace

    output = _prepare_work_item(tmp_path)
    ConfigManager(tmp_path).update(name="display-app")
    seen_names: list[str] = []
    downstream: list[str] = []

    async def generate(**kwargs):
        seen_names.append(kwargs["name"])
        return SimpleNamespace(
            outputs=[
                SimpleNamespace(document_type=kind, content=f"new {kind}")
                for kind in ("prd", "architecture", "uiux")
            ],
            total_score=95,
            summary="generated",
        )

    monkeypatch.setattr(
        "super_dev.orchestrator.experts.ExpertDispatcher",
        lambda project_dir: SimpleNamespace(dispatch_document_generation_async=generate),
    )
    monkeypatch.setattr(
        "super_dev.creators.prompt_generator.AIPromptGenerator",
        lambda *args: SimpleNamespace(generate=lambda: "prompt"),
    )
    engine = isolated_engine()

    async def redteam(context):
        downstream.append("redteam")
        return {"passed": True}

    engine.register_phase_handler(Phase.REDTEAM, redteam)
    context = WorkflowContext(
        project_dir=tmp_path,
        config=engine.config_manager,
        user_input={"name": "display-override"} if override_display_name else {},
    )
    with pytest.raises(WorkflowGateError):
        await engine.run(phases=[Phase.DRAFTING, Phase.REDTEAM], context=context)

    assert downstream == []
    assert seen_names == ["display-override" if override_display_name else "display-app"]
    assert (output / "current-prd.md").read_text(encoding="utf-8") == "new prd"
    assert (output / "current-ai-prompt.md").is_file()
    assert not (output / "display-app-prd.md").exists()
    assert not (output / "display-override-prd.md").exists()
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    resumed_context = WorkflowContext(project_dir=tmp_path, config=engine.config_manager)
    await isolated_engine().run(phases=[Phase.DRAFTING], context=resumed_context, resume=True)
    assert resumed_context.documents["prd"] == "new prd"
    assert len(seen_names) == 1


@pytest.mark.parametrize("work_mode", ["new", "evolve", "patch", "variant"])
def test_summary_keeps_required_baseline_before_later_docs_confirmation(
    tmp_path: Path, work_mode: str
) -> None:
    _prepare_work_item(tmp_path)
    save_bound_docs_confirmation(tmp_path, {"status": "pending_review", "actor": "user"})
    save_workflow_state(tmp_path, {**load_workflow_state(tmp_path), "work_mode": work_mode})

    summary = detect_pipeline_summary(tmp_path)

    if work_mode == "new":
        assert summary["workflow_status"] == "waiting_docs_confirmation"
        assert summary["current_stage_canonical_id"] == "docs_confirm"
    else:
        assert summary["workflow_status"] == "missing_baseline"
        assert summary["current_stage_canonical_id"] == "baseline"
