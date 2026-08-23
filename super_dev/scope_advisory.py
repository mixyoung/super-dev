"""Build read-only stage recommendations from the production scope rule."""

from __future__ import annotations

from collections.abc import Iterable

from .change_ledger import ScopeAdvisory, StageResolution, StageScopeRecommendation
from .stage_scope import required_stages_for
from .workflow_contract import CANONICAL_NINE_STAGE_IDS, get_phase_kinds


def build_scope_advisory(
    *,
    changed_surfaces: Iterable[str],
    work_mode: str,
    governance_depth: str,
    scope_complete: bool,
    generated_at: str,
) -> ScopeAdvisory:
    surfaces = sorted(
        {str(item).strip().lower() for item in changed_surfaces if str(item).strip()}
    )
    required = (
        set(
            required_stages_for(
                changed_surfaces=surfaces,
                work_mode=work_mode,
                governance_depth=governance_depth,
            )
        )
        if scope_complete
        else set(CANONICAL_NINE_STAGE_IDS)
    )
    kinds = get_phase_kinds("standard")
    recommendations = []
    for stage in CANONICAL_NINE_STAGE_IDS:
        kind = kinds[stage]
        if stage in required:
            resolution = (
                StageResolution.REQUIRE if kind == "gate" else StageResolution.EXECUTE
            )
            reason = (
                "范围尚未完整，建议保留该阶段"
                if not scope_complete
                else "当前改动范围需要保留该阶段"
            )
            approval_required = False
        else:
            resolution = StageResolution.NOT_APPLICABLE
            reason = "当前明确范围不涉及该阶段，建议经审批后标记为不适用"
            approval_required = True
        recommendations.append(
            StageScopeRecommendation(
                stage=stage,
                kind=kind,
                recommended_resolution=resolution,
                reason=reason,
                approval_required=approval_required,
            )
        )
    return ScopeAdvisory(
        generated_at=generated_at,
        scope_complete=scope_complete,
        changed_surfaces=surfaces,
        recommendations=recommendations,
    )


__all__ = ["build_scope_advisory"]
