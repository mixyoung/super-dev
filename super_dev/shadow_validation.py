"""In-memory comparison lab for adaptive nine-stage shadow decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .agent_contract import AgentAssignment
from .change_ledger import (
    ArtifactDepth,
    ChangeIntent,
    ChangeLedger,
    EvidenceReference,
    StageResolution,
)
from .stage_policy import (
    StagePolicyContext,
    apply_stage_resolution,
    evidence_is_reusable,
)
from .workflow_contract import CANONICAL_NINE_STAGE_IDS


@dataclass(frozen=True)
class ShadowValidationScenario:
    scenario_id: str
    label: str
    intent: ChangeIntent
    governance_depth: str
    work_mode: str
    changed_surfaces: frozenset[str]
    mandatory_stages: tuple[str, ...]
    may_reuse_stages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id.strip() or not self.label.strip():
            raise ValueError("Scenario identity and label are required")
        mandatory = set(self.mandatory_stages)
        unknown = mandatory - set(CANONICAL_NINE_STAGE_IDS)
        if unknown:
            raise ValueError(f"Unknown mandatory stages: {sorted(unknown)}")
        expected_order = tuple(stage for stage in CANONICAL_NINE_STAGE_IDS if stage in mandatory)
        if self.mandatory_stages != expected_order:
            raise ValueError("Mandatory stages must follow the canonical nine-stage order")
        if not {"quality", "delivery"}.issubset(mandatory):
            raise ValueError("Every delivery scenario must retain quality and delivery")
        may_reuse = set(self.may_reuse_stages)
        unknown_reuse = may_reuse - set(CANONICAL_NINE_STAGE_IDS)
        if unknown_reuse:
            raise ValueError(f"Unknown reusable stages: {sorted(unknown_reuse)}")
        expected_reuse_order = tuple(
            stage for stage in CANONICAL_NINE_STAGE_IDS if stage in may_reuse
        )
        if self.may_reuse_stages != expected_reuse_order:
            raise ValueError("Reusable stages must follow the canonical nine-stage order")
        if may_reuse & {"docs_confirm", "preview_confirm"}:
            raise ValueError("Confirmation gates cannot reuse work evidence")


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
    coach_summary: str

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
            "coach_summary": self.coach_summary,
        }


def representative_shadow_scenarios() -> tuple[ShadowValidationScenario, ...]:
    return (
        ShadowValidationScenario(
            scenario_id="bounded-backend-patch",
            label="边界清楚的后端缺陷修复",
            intent=ChangeIntent.DEBUG,
            governance_depth="bounded",
            work_mode="patch",
            changed_surfaces=frozenset({"backend"}),
            mandatory_stages=("spec", "backend", "quality", "delivery"),
        ),
        ShadowValidationScenario(
            scenario_id="bounded-ui-change",
            label="用户可见的局部界面改动",
            intent=ChangeIntent.QUICK_EDIT,
            governance_depth="bounded",
            work_mode="evolve",
            changed_surfaces=frozenset({"frontend", "ui"}),
            mandatory_stages=(
                "docs",
                "docs_confirm",
                "spec",
                "frontend",
                "preview_confirm",
                "quality",
                "delivery",
            ),
        ),
        ShadowValidationScenario(
            scenario_id="api-contract-change",
            label="接口或数据合同调整",
            intent=ChangeIntent.BUILD,
            governance_depth="architectural",
            work_mode="evolve",
            changed_surfaces=frozenset({"backend", "api", "data"}),
            mandatory_stages=(
                "docs",
                "docs_confirm",
                "spec",
                "backend",
                "quality",
                "delivery",
            ),
            may_reuse_stages=("research",),
        ),
        ShadowValidationScenario(
            scenario_id="commercial-cross-stack",
            label="跨前后端的商业交付改动",
            intent=ChangeIntent.BUILD,
            governance_depth="commercial",
            work_mode="evolve",
            changed_surfaces=frozenset(
                {"product", "architecture", "frontend", "ui", "backend", "api", "data"}
            ),
            mandatory_stages=CANONICAL_NINE_STAGE_IDS,
        ),
    )


def _infer_planned_mandatory_stages(
    scenario: ShadowValidationScenario,
) -> tuple[str, ...]:
    """Infer a plan from scope signals without reading the frozen expected answer."""

    surfaces = scenario.changed_surfaces
    mandatory = {"spec", "quality", "delivery"}
    if scenario.work_mode == "new" or scenario.governance_depth == "commercial":
        mandatory.add("research")
    if surfaces & {
        "product",
        "architecture",
        "uiux",
        "ui",
        "frontend",
        "route",
        "style",
        "component",
        "api",
        "data",
        "authorization",
    }:
        mandatory.update({"docs", "docs_confirm"})
    if surfaces & {"frontend", "ui", "route", "style", "component"}:
        mandatory.update({"frontend", "preview_confirm"})
    if surfaces & {"backend", "api", "data", "authorization"}:
        mandatory.add("backend")
    return tuple(stage for stage in CANONICAL_NINE_STAGE_IDS if stage in mandatory)


def plan_shadow_scenario(
    scenario: ShadowValidationScenario,
    *,
    actor: AgentAssignment,
    harness_version: str,
    reusable_evidence: dict[str, list[EvidenceReference]] | None = None,
) -> ChangeLedger:
    """Create an in-memory shadow plan; this function never persists a ledger."""

    ledger = ChangeLedger.create(
        change_id=scenario.scenario_id,
        harness_version=harness_version,
        intent=scenario.intent,
        governance_depth=scenario.governance_depth,
        work_mode=scenario.work_mode,
    )
    planned_mandatory = _infer_planned_mandatory_stages(scenario)
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
        merge_or_release_candidate=True,
        executed_stages=frozenset(
            stage
            for stage in planned_mandatory
            if ledger.get_stage(stage).kind != "gate"
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
            if entry.stage not in may_reuse or not entry.evidence or not all(
                evidence_is_reusable(item, change_id=ledger.change_id)
                for item in entry.evidence
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

    user_gate_count = sum(
        entry.resolution == StageResolution.REQUIRE for entry in ledger.stages
    )
    coach_summary = _build_coach_summary(
        scenario=scenario,
        legacy_reductions=legacy_reductions,
        reused_stages=reused_stages,
        user_gate_count=user_gate_count,
    )
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
        coach_summary=coach_summary,
    )


def _build_coach_summary(
    *,
    scenario: ShadowValidationScenario,
    legacy_reductions: list[str],
    reused_stages: list[str],
    user_gate_count: int,
) -> str:
    if legacy_reductions:
        summary = (
            f"本次为{scenario.label}；保留{len(CANONICAL_NINE_STAGE_IDS) - len(legacy_reductions)}"
            f"个必要阶段，缩减{len(legacy_reductions)}个无关阶段"
        )
    else:
        summary = f"本次为{scenario.label}；按完整九阶段执行"
    if reused_stages:
        summary += f"，复用{len(reused_stages)}项仍在有效期内的证据"
    if user_gate_count:
        summary += f"，需要你完成{user_gate_count}次确认"
    else:
        summary += "，不增加中途确认"
    return summary + "。质量验证和交付收口始终保留。"


def build_representative_validation_report(
    *,
    actor: AgentAssignment,
    harness_version: str,
) -> dict[str, Any]:
    evaluations = []
    now = datetime.now(timezone.utc)
    for scenario in representative_shadow_scenarios():
        reusable_evidence = {
            stage: [
                EvidenceReference(
                    locator=f"output/project-{stage}.md",
                    owner="shadow-evaluator",
                    captured_at=now.isoformat(),
                    candidate_scope="project",
                    expires_at=(now + timedelta(hours=1)).isoformat(),
                    invalidation_triggers=["source-evidence-changed"],
                )
            ]
            for stage in scenario.may_reuse_stages
        }
        ledger = plan_shadow_scenario(
            scenario,
            actor=actor,
            harness_version=harness_version,
            reusable_evidence=reusable_evidence or None,
        )
        evaluations.append(evaluate_shadow_scenario(scenario, ledger))
    return {
        "mode": "shadow-comparison",
        "read_only": True,
        "control_authority": "none",
        "production_writes": False,
        "legacy_contract": "all-nine-stages-execute-or-require",
        "scenario_count": len(evaluations),
        "passed_count": sum(item.passed for item in evaluations),
        "false_skip_count": sum(len(item.false_skips) for item in evaluations),
        "false_block_count": sum(len(item.false_blocks) for item in evaluations),
        "evidence_reuse_error_count": sum(
            len(item.evidence_reuse_errors) for item in evaluations
        ),
        "reuse_count": sum(len(item.reused_stages) for item in evaluations),
        "scope_explanation_count": sum(
            item.scope_explanation_count for item in evaluations
        ),
        "scenarios": [item.to_dict() for item in evaluations],
    }


__all__ = [
    "ShadowScenarioEvaluation",
    "ShadowValidationScenario",
    "build_representative_validation_report",
    "evaluate_shadow_scenario",
    "plan_shadow_scenario",
    "representative_shadow_scenarios",
]
