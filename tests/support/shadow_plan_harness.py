"""Test-only assembly and evaluation harness for shadow stage plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from super_dev.agent_contract import AgentAssignment
from super_dev.change_ledger import (
    ArtifactDepth,
    ChangeLedger,
    EvidenceReference,
    StageResolution,
)
from super_dev.stage_policy import (
    StagePolicyContext,
    apply_stage_resolution,
    evidence_is_reusable,
)
from super_dev.stage_scope import required_stages_for
from super_dev.workflow_contract import CANONICAL_NINE_STAGE_IDS
from tests.fixtures.shadow_scenarios import ShadowValidationScenario


@dataclass(frozen=True)
class ShadowScenarioEvaluation:
    scenario_id: str
    label: str
    false_skips: tuple[str, ...]
    false_blocks: tuple[str, ...]
    evidence_reuse_errors: tuple[str, ...]
    reused_stages: tuple[str, ...]
    legacy_reductions: tuple[str, ...]
    scope_explanation_count: int
    user_summary_required: bool
    user_gate_count: int

    @property
    def passed(self) -> bool:
        return not (self.false_skips or self.false_blocks or self.evidence_reuse_errors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "label": self.label,
            "passed": self.passed,
            "false_skips": list(self.false_skips),
            "false_blocks": list(self.false_blocks),
            "evidence_reuse_errors": list(self.evidence_reuse_errors),
            "reused_stages": list(self.reused_stages),
            "legacy_reductions": list(self.legacy_reductions),
            "scope_explanation_count": self.scope_explanation_count,
            "user_summary_required": self.user_summary_required,
            "user_gate_count": self.user_gate_count,
        }


def plan_shadow_scenario(
    scenario: ShadowValidationScenario,
    *,
    actor: AgentAssignment,
    harness_version: str,
    reusable_evidence: dict[str, list[EvidenceReference]] | None = None,
) -> ChangeLedger:
    """Assemble an in-memory test plan; this function never persists a ledger."""

    ledger = ChangeLedger.create(
        change_id=scenario.scenario_id,
        harness_version=harness_version,
        intent=scenario.intent,
        governance_depth=scenario.governance_depth,
        work_mode=scenario.work_mode,
    )
    planned_mandatory = required_stages_for(
        changed_surfaces=scenario.changed_surfaces,
        work_mode=scenario.work_mode,
        governance_depth=scenario.governance_depth,
    )
    mandatory = set(planned_mandatory)
    evidence_by_stage = reusable_evidence or {}
    unknown_evidence_stages = set(evidence_by_stage) - set(CANONICAL_NINE_STAGE_IDS)
    if unknown_evidence_stages:
        raise ValueError(f"Unknown evidence stages: {sorted(unknown_evidence_stages)}")
    gate_evidence_stages = {
        stage for stage in evidence_by_stage if ledger.get_stage(stage).kind == "gate"
    }
    if gate_evidence_stages:
        raise ValueError(f"Gate stages cannot reuse work evidence: {sorted(gate_evidence_stages)}")
    undeclared_reuse_stages = set(evidence_by_stage) - set(scenario.may_reuse_stages)
    if undeclared_reuse_stages:
        raise ValueError(
            f"Evidence reuse is not approved for stages: {sorted(undeclared_reuse_stages)}"
        )
    context = StagePolicyContext(
        change_id=ledger.change_id,
        changed_surfaces=scenario.changed_surfaces,
        work_mode=scenario.work_mode,
        governance_depth=scenario.governance_depth,
        merge_or_release_candidate=True,
        executed_stages=frozenset(
            stage for stage in planned_mandatory if ledger.get_stage(stage).kind != "gate"
        ),
    )
    for entry in ledger.stages:
        evidence = evidence_by_stage.get(entry.stage, [])
        if evidence:
            resolution = StageResolution.REUSE
            depth = ArtifactDepth.ARTIFACT
            reason = f"{scenario.label}复用仍在有效期内的{entry.stage}证据"
        elif entry.stage in mandatory:
            resolution = (
                StageResolution.REQUIRE if entry.kind == "gate" else StageResolution.EXECUTE
            )
            depth = ArtifactDepth.NONE if entry.kind == "gate" else ArtifactDepth.ARTIFACT
            reason = f"{scenario.label}需要完成{entry.stage}"
        else:
            resolution = StageResolution.NOT_APPLICABLE
            depth = ArtifactDepth.NONE
            reason = f"{scenario.label}的范围不涉及{entry.stage}"
        apply_stage_resolution(
            entry,
            resolution=resolution,
            depth=depth,
            actor=actor,
            context=context,
            reason=reason,
            evidence=evidence,
        )
    return ledger


def evaluate_shadow_scenario(
    scenario: ShadowValidationScenario,
    ledger: ChangeLedger,
) -> ShadowScenarioEvaluation:
    mandatory = set(scenario.mandatory_stages)
    may_reuse = set(scenario.may_reuse_stages)
    false_skips: list[str] = []
    false_blocks: list[str] = []
    reuse_errors: list[str] = []
    reused_stages: list[str] = []
    legacy_reductions: list[str] = []

    for entry in ledger.stages:
        legacy_resolution = (
            StageResolution.REQUIRE if entry.kind == "gate" else StageResolution.EXECUTE
        )
        if entry.resolution != legacy_resolution:
            legacy_reductions.append(entry.stage)
        if entry.resolution == StageResolution.REUSE:
            reused_stages.append(entry.stage)
            if (
                entry.stage not in may_reuse
                or not entry.evidence
                or not all(
                    evidence_is_reusable(item, change_id=ledger.change_id)
                    for item in entry.evidence
                )
            ):
                reuse_errors.append(entry.stage)
        if entry.stage in mandatory:
            required_resolution = (
                {StageResolution.REQUIRE}
                if entry.kind == "gate"
                else (
                    {StageResolution.EXECUTE, StageResolution.REUSE}
                    if entry.stage in may_reuse
                    else {StageResolution.EXECUTE}
                )
            )
            if entry.resolution not in required_resolution:
                false_skips.append(entry.stage)
        elif entry.resolution in {StageResolution.EXECUTE, StageResolution.REQUIRE}:
            false_blocks.append(entry.stage)

    user_gate_count = sum(entry.resolution == StageResolution.REQUIRE for entry in ledger.stages)
    return ShadowScenarioEvaluation(
        scenario_id=scenario.scenario_id,
        label=scenario.label,
        false_skips=tuple(false_skips),
        false_blocks=tuple(false_blocks),
        evidence_reuse_errors=tuple(reuse_errors),
        reused_stages=tuple(reused_stages),
        legacy_reductions=tuple(legacy_reductions),
        scope_explanation_count=len(legacy_reductions),
        user_summary_required=bool(legacy_reductions),
        user_gate_count=user_gate_count,
    )


__all__ = [
    "ShadowScenarioEvaluation",
    "evaluate_shadow_scenario",
    "plan_shadow_scenario",
]
