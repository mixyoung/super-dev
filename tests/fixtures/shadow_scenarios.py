"""Frozen scenario inputs and independent expected answers for shadow comparison."""

from __future__ import annotations

from dataclasses import dataclass

from super_dev.change_ledger import ChangeIntent
from super_dev.workflow_contract import CANONICAL_NINE_STAGE_IDS


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


__all__ = ["ShadowValidationScenario", "representative_shadow_scenarios"]
