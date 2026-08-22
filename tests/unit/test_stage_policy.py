from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from super_dev.agent_contract import AgentAssignment, AgentLevel
from super_dev.change_ledger import (
    ArtifactDepth,
    ChangeLedger,
    EvidenceReference,
    StageResolution,
    StageStatus,
)
from super_dev.stage_policy import (
    StagePolicyContext,
    StagePolicyError,
    apply_stage_resolution,
    escalate_governance_depth,
    invalidate_expired_reuse,
    invalidate_ledger,
)


def _coordinator() -> AgentAssignment:
    return AgentAssignment(
        task_id="coord-1",
        parent_task_id="root-1",
        agent_level=AgentLevel.COORDINATOR,
        role="coordinator",
        workspace="E:/repo",
        write_scope=("**",),
        forbidden_actions=("push",),
        placement_owner="root-1",
        result_owner="root-1",
        may_delegate=True,
        may_approve_skip=True,
        may_approve_waiver=True,
    )


def _writer() -> AgentAssignment:
    return AgentAssignment(
        task_id="writer-1",
        parent_task_id="coord-1",
        agent_level=AgentLevel.WRITER,
        role="writer",
        workspace="E:/repo",
        write_scope=("super_dev/**",),
        forbidden_actions=("push", "advance-stage"),
        placement_owner="coord-1",
        result_owner="coord-1",
    )


def _ledger(depth: str = "bounded") -> ChangeLedger:
    return ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="quick_edit",
        governance_depth=depth,
        work_mode="evolve",
    )


def test_frontend_change_cannot_skip_frontend_or_preview_gate() -> None:
    ledger = _ledger()
    context = StagePolicyContext(
        change_id=ledger.change_id,
        changed_surfaces=frozenset({"frontend"}),
    )

    with pytest.raises(StagePolicyError, match="cannot skip"):
        apply_stage_resolution(
            ledger.get_stage("frontend"),
            resolution=StageResolution.NOT_APPLICABLE,
            depth=ArtifactDepth.NONE,
            actor=_coordinator(),
            context=context,
            reason="No frontend impact",
        )
    with pytest.raises(StagePolicyError, match="require preview"):
        apply_stage_resolution(
            ledger.get_stage("preview_confirm"),
            resolution=StageResolution.WAIVE,
            depth=ArtifactDepth.NONE,
            actor=_coordinator(),
            context=context,
            reason="Small UI change",
        )


@pytest.mark.parametrize("stage", ["quality", "delivery"])
def test_quality_and_delivery_cannot_be_not_applicable(stage: str) -> None:
    ledger = _ledger()
    expected = "invalid for work_gate" if stage == "quality" else "cannot be not-applicable"
    with pytest.raises(StagePolicyError, match=expected):
        apply_stage_resolution(
            ledger.get_stage(stage),
            resolution=StageResolution.NOT_APPLICABLE,
            depth=ArtifactDepth.NONE,
            actor=_coordinator(),
            context=StagePolicyContext(change_id=ledger.change_id),
            reason="Small change",
        )


def test_reused_evidence_must_be_fresh_and_in_scope() -> None:
    ledger = _ledger()
    stale = EvidenceReference(
        locator="output/old-quality.json",
        owner="qa",
        captured_at=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        candidate_scope=ledger.change_id,
        expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    )

    with pytest.raises(StagePolicyError, match="stale"):
        apply_stage_resolution(
            ledger.get_stage("quality"),
            resolution=StageResolution.REUSE,
            depth=ArtifactDepth.ARTIFACT,
            actor=_coordinator(),
            context=StagePolicyContext(change_id=ledger.change_id),
            reason="Reuse old quality result",
            evidence=[stale],
        )


def test_reused_evidence_requires_expiry_and_is_invalidated_after_expiry() -> None:
    ledger = _ledger()
    now = datetime.now(timezone.utc)
    evidence = EvidenceReference(
        locator="output/quality.json",
        owner="qa",
        captured_at=now.isoformat(),
        candidate_scope=ledger.change_id,
        expires_at=(now + timedelta(minutes=5)).isoformat(),
        invalidation_triggers=["source-changed"],
    )
    apply_stage_resolution(
        ledger.get_stage("quality"),
        resolution=StageResolution.REUSE,
        depth=ArtifactDepth.ARTIFACT,
        actor=_coordinator(),
        context=StagePolicyContext(change_id=ledger.change_id),
        reason="Fresh quality evidence",
        evidence=[evidence],
    )

    assert ledger.get_stage("quality").status == StageStatus.SATISFIED
    assert ledger.get_stage("quality").invalidation_triggers == ["source-changed"]
    assert invalidate_expired_reuse(
        ledger, now=now + timedelta(minutes=10)
    ) == ["quality"]
    assert ledger.get_stage("quality").status == StageStatus.INVALIDATED


def test_hidden_complexity_only_escalates_depth_and_invalidates_evidence() -> None:
    ledger = _ledger()
    ledger.get_stage("docs").invalidation_triggers = ["architecture-changed"]

    assert escalate_governance_depth(ledger, "architectural") is True
    assert invalidate_ledger(ledger, {"architecture-changed"}) == ["docs"]
    assert ledger.get_stage("docs").status == StageStatus.INVALIDATED

    with pytest.raises(StagePolicyError, match="cannot downgrade"):
        escalate_governance_depth(ledger, "bounded")


def test_writer_cannot_decide_gate_requirement() -> None:
    ledger = _ledger()
    with pytest.raises(StagePolicyError, match="Only root or coordinator"):
        apply_stage_resolution(
            ledger.get_stage("docs_confirm"),
            resolution=StageResolution.REQUIRE,
            depth=ArtifactDepth.NONE,
            actor=_writer(),
            context=StagePolicyContext(change_id=ledger.change_id),
            reason="",
        )


def test_executed_frontend_requires_preview_even_without_surface_hints() -> None:
    ledger = _ledger()
    with pytest.raises(StagePolicyError, match="require preview"):
        apply_stage_resolution(
            ledger.get_stage("preview_confirm"),
            resolution=StageResolution.WAIVE,
            depth=ArtifactDepth.NONE,
            actor=_coordinator(),
            context=StagePolicyContext(
                change_id=ledger.change_id,
                executed_stages=frozenset({"frontend"}),
            ),
            reason="No preview needed",
        )


def test_ui_contract_change_requires_docs_confirmation() -> None:
    ledger = _ledger()
    with pytest.raises(StagePolicyError, match="require docs confirmation"):
        apply_stage_resolution(
            ledger.get_stage("docs_confirm"),
            resolution=StageResolution.WAIVE,
            depth=ArtifactDepth.NONE,
            actor=_coordinator(),
            context=StagePolicyContext(
                change_id=ledger.change_id,
                changed_surfaces=frozenset({"ui"}),
            ),
            reason="Small visual change",
        )


def test_depth_upgrade_invalidates_shortcut_decisions() -> None:
    ledger = _ledger()
    apply_stage_resolution(
        ledger.get_stage("frontend"),
        resolution=StageResolution.NOT_APPLICABLE,
        depth=ArtifactDepth.NONE,
        actor=_coordinator(),
        context=StagePolicyContext(change_id=ledger.change_id),
        reason="Backend-only change",
    )

    assert escalate_governance_depth(ledger, "architectural") is True
    assert ledger.get_stage("frontend").status == StageStatus.INVALIDATED


def test_bounded_backend_change_retains_nine_stages_with_scaled_resolutions() -> None:
    ledger = _ledger()
    context = StagePolicyContext(
        change_id=ledger.change_id,
        changed_surfaces=frozenset({"backend"}),
    )
    apply_stage_resolution(
        ledger.get_stage("frontend"),
        resolution=StageResolution.NOT_APPLICABLE,
        depth=ArtifactDepth.NONE,
        actor=_coordinator(),
        context=context,
        reason="Backend-only change",
    )
    apply_stage_resolution(
        ledger.get_stage("preview_confirm"),
        resolution=StageResolution.NOT_APPLICABLE,
        depth=ArtifactDepth.NONE,
        actor=_coordinator(),
        context=context,
        reason="No user-visible frontend change",
    )

    assert len(ledger.stages) == 9
    assert ledger.get_stage("backend").resolution == StageResolution.EXECUTE
    assert ledger.get_stage("quality").resolution == StageResolution.EXECUTE
    assert ledger.get_stage("delivery").resolution == StageResolution.EXECUTE


def test_architectural_change_cannot_skip_docs_or_confirmation() -> None:
    ledger = _ledger("architectural")
    context = StagePolicyContext(
        change_id=ledger.change_id,
        changed_surfaces=frozenset({"architecture"}),
    )
    with pytest.raises(StagePolicyError, match="cannot skip the docs"):
        apply_stage_resolution(
            ledger.get_stage("docs"),
            resolution=StageResolution.NOT_APPLICABLE,
            depth=ArtifactDepth.NONE,
            actor=_coordinator(),
            context=context,
            reason="No docs needed",
        )
    with pytest.raises(StagePolicyError, match="require docs confirmation"):
        apply_stage_resolution(
            ledger.get_stage("docs_confirm"),
            resolution=StageResolution.WAIVE,
            depth=ArtifactDepth.NONE,
            actor=_coordinator(),
            context=context,
            reason="Waive docs review",
        )


def test_reused_evidence_from_another_change_is_rejected() -> None:
    ledger = _ledger()
    now = datetime.now(timezone.utc)
    evidence = EvidenceReference(
        locator="output/quality.json",
        owner="qa",
        captured_at=now.isoformat(),
        candidate_scope="another-change",
        expires_at=(now + timedelta(hours=1)).isoformat(),
    )
    with pytest.raises(StagePolicyError, match="out of scope"):
        apply_stage_resolution(
            ledger.get_stage("quality"),
            resolution=StageResolution.REUSE,
            depth=ArtifactDepth.ARTIFACT,
            actor=_coordinator(),
            context=StagePolicyContext(change_id=ledger.change_id),
            reason="Reuse evidence",
            evidence=[evidence],
        )
