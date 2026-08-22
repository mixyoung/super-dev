"""Policy checks for nine-stage ledger decisions and evidence reuse."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .agent_contract import AgentAssignment, AgentLevel
from .change_ledger import (
    ArtifactDepth,
    ChangeLedger,
    EvidenceReference,
    StageLedgerEntry,
    StageResolution,
    StageStatus,
)
from .work_mode import governance_depth_rank, normalize_governance_depth


class StagePolicyError(ValueError):
    """Raised when a stage decision violates the adaptive Harness contract."""


WORK_RESOLUTIONS = {
    StageResolution.EXECUTE,
    StageResolution.REUSE,
    StageResolution.NOT_APPLICABLE,
}
WORK_GATE_RESOLUTIONS = {
    StageResolution.EXECUTE,
    StageResolution.REUSE,
}
GATE_RESOLUTIONS = {
    StageResolution.REQUIRE,
    StageResolution.WAIVE,
    StageResolution.NOT_APPLICABLE,
}
SKIP_LIKE_RESOLUTIONS = {
    StageResolution.REUSE,
    StageResolution.NOT_APPLICABLE,
    StageResolution.WAIVE,
}


@dataclass(frozen=True)
class StagePolicyContext:
    change_id: str
    changed_surfaces: frozenset[str] = field(default_factory=frozenset)
    merge_or_release_candidate: bool = True
    executed_stages: frozenset[str] = field(default_factory=frozenset)


def _parse_timestamp(value: str) -> datetime | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def evidence_is_reusable(
    evidence: EvidenceReference,
    *,
    change_id: str,
    now: datetime | None = None,
) -> bool:
    if not all(
        [
            evidence.locator.strip(),
            evidence.owner.strip(),
            evidence.captured_at.strip(),
            evidence.candidate_scope.strip(),
        ]
    ):
        return False
    if evidence.candidate_scope not in {change_id, "project"}:
        return False
    captured_at = _parse_timestamp(evidence.captured_at)
    if captured_at is None:
        return False
    expires_at = _parse_timestamp(evidence.expires_at)
    reference_time = now or datetime.now(timezone.utc)
    return expires_at is not None and expires_at >= reference_time


def _actor_can_decide_skip(actor: AgentAssignment, resolution: StageResolution) -> bool:
    if actor.agent_level not in {AgentLevel.ROOT, AgentLevel.COORDINATOR}:
        return False
    if resolution == StageResolution.WAIVE:
        return actor.may_approve_waiver
    return actor.may_approve_skip


def validate_stage_resolution(
    entry: StageLedgerEntry,
    *,
    resolution: StageResolution,
    actor: AgentAssignment,
    context: StagePolicyContext,
    evidence: list[EvidenceReference] | None = None,
) -> None:
    legal = (
        WORK_RESOLUTIONS
        if entry.kind == "work"
        else (GATE_RESOLUTIONS if entry.kind == "gate" else WORK_GATE_RESOLUTIONS)
    )
    if resolution not in legal:
        raise StagePolicyError(f"Resolution {resolution.value} is invalid for {entry.kind} stage")
    if actor.agent_level == AgentLevel.REVIEWER:
        raise StagePolicyError("A read-only reviewer cannot decide a stage resolution")
    if entry.kind == "gate" and actor.agent_level not in {
        AgentLevel.ROOT,
        AgentLevel.COORDINATOR,
    }:
        raise StagePolicyError("Only root or coordinator assignments can decide a gate")
    if resolution in SKIP_LIKE_RESOLUTIONS and not _actor_can_decide_skip(actor, resolution):
        raise StagePolicyError("This actor cannot approve reuse, skip, or gate waiver")

    surfaces = context.changed_surfaces
    if entry.stage == "frontend" and resolution == StageResolution.NOT_APPLICABLE:
        if surfaces & {"frontend", "ui", "route", "style", "component"}:
            raise StagePolicyError("Frontend changes cannot skip the frontend stage")
    if entry.stage == "backend" and resolution == StageResolution.NOT_APPLICABLE:
        if surfaces & {"backend", "api", "data", "authorization"}:
            raise StagePolicyError("Backend or contract changes cannot skip the backend stage")
    if entry.stage == "docs" and resolution == StageResolution.NOT_APPLICABLE:
        if surfaces & {"product", "architecture", "uiux", "api", "data", "authorization"}:
            raise StagePolicyError("Contract changes cannot skip the docs stage")
    if entry.stage == "docs_confirm" and surfaces & {
        "product",
        "architecture",
        "uiux",
        "ui",
        "api",
        "data",
        "authorization",
    }:
        if resolution != StageResolution.REQUIRE:
            raise StagePolicyError("Contract changes require docs confirmation")
    if entry.stage == "preview_confirm" and (
        "frontend" in context.executed_stages
        or surfaces
        & {
        "frontend",
        "ui",
        "route",
        "style",
        "component",
        }
    ):
        if resolution != StageResolution.REQUIRE:
            raise StagePolicyError("User-visible frontend changes require preview confirmation")
    if (
        context.merge_or_release_candidate
        and entry.stage in {"quality", "delivery"}
        and resolution == StageResolution.NOT_APPLICABLE
    ):
        raise StagePolicyError("Quality and delivery cannot be not-applicable for a candidate")

    if resolution == StageResolution.REUSE:
        references = evidence or []
        if not references or not all(
            evidence_is_reusable(item, change_id=context.change_id) for item in references
        ):
            raise StagePolicyError("Reused evidence is missing, stale, or out of scope")


def apply_stage_resolution(
    entry: StageLedgerEntry,
    *,
    resolution: StageResolution,
    depth: ArtifactDepth,
    actor: AgentAssignment,
    context: StagePolicyContext,
    reason: str,
    evidence: list[EvidenceReference] | None = None,
) -> None:
    if resolution in SKIP_LIKE_RESOLUTIONS and not reason.strip():
        raise StagePolicyError("Reuse, skip, and waiver decisions require a reason")
    validate_stage_resolution(
        entry,
        resolution=resolution,
        actor=actor,
        context=context,
        evidence=evidence,
    )
    entry.resolution = resolution
    entry.depth = depth
    entry.reason = reason.strip()
    entry.decided_by = actor.task_id
    entry.evidence = list(evidence or [])
    entry.invalidation_triggers = sorted(
        {
            *entry.invalidation_triggers,
            *(trigger for item in entry.evidence for trigger in item.invalidation_triggers),
        }
    )
    entry.status = (
        StageStatus.SATISFIED
        if resolution in SKIP_LIKE_RESOLUTIONS
        else StageStatus.PENDING
    )


def invalidate_ledger(ledger: ChangeLedger, triggers: set[str]) -> list[str]:
    invalidated: list[str] = []
    for entry in ledger.stages:
        if set(entry.invalidation_triggers) & triggers:
            entry.status = StageStatus.INVALIDATED
            invalidated.append(entry.stage)
    return invalidated


def invalidate_expired_reuse(
    ledger: ChangeLedger,
    *,
    now: datetime | None = None,
) -> list[str]:
    invalidated: list[str] = []
    for entry in ledger.stages:
        if entry.resolution != StageResolution.REUSE:
            continue
        if not entry.evidence or not all(
            evidence_is_reusable(item, change_id=ledger.change_id, now=now)
            for item in entry.evidence
        ):
            entry.status = StageStatus.INVALIDATED
            invalidated.append(entry.stage)
    return invalidated


def escalate_governance_depth(ledger: ChangeLedger, target_depth: str) -> bool:
    try:
        target = normalize_governance_depth(target_depth)
    except ValueError as exc:
        raise StagePolicyError(str(exc)) from exc
    if governance_depth_rank(target) < governance_depth_rank(ledger.governance_depth):
        raise StagePolicyError("Governance depth cannot downgrade within one change")
    if target == ledger.governance_depth:
        return False
    ledger.governance_depth = target
    for entry in ledger.stages:
        if entry.resolution in SKIP_LIKE_RESOLUTIONS:
            entry.status = StageStatus.INVALIDATED
    return True


__all__ = [
    "StagePolicyContext",
    "StagePolicyError",
    "apply_stage_resolution",
    "escalate_governance_depth",
    "evidence_is_reusable",
    "invalidate_ledger",
    "invalidate_expired_reuse",
    "validate_stage_resolution",
]
