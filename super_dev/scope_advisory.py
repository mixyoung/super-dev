"""Build read-only stage recommendations from the production scope rule."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .change_ledger import ScopeAdvisory, StageResolution, StageScopeRecommendation
from .stage_scope import KNOWN_CHANGE_SURFACES, required_stages_for
from .work_mode import normalize_governance_depth
from .workflow_contract import CANONICAL_NINE_STAGE_IDS, get_phase_kinds


@dataclass(frozen=True)
class StructuredScopeDeclaration:
    """Normalized scope data passed from a pipeline entry into Spec creation."""

    changed_surfaces: tuple[str, ...]
    scope_complete: bool
    work_mode: str
    governance_depth: str


def resolve_pipeline_scope_declaration(
    *,
    changed_surfaces: Iterable[str] | None,
    request_mode: str,
    scenario: str,
    governance_depth: str | None = None,
) -> StructuredScopeDeclaration:
    """Normalize one pipeline declaration without guessing omitted change surfaces."""

    surfaces = tuple(
        sorted(
            {str(item).strip().lower() for item in (changed_surfaces or ()) if str(item).strip()}
        )
    )
    unknown_surfaces = set(surfaces) - KNOWN_CHANGE_SURFACES
    if unknown_surfaces:
        raise ValueError(f"Unsupported changed surfaces: {sorted(unknown_surfaces)}")

    normalized_request_mode = str(request_mode).strip().lower()
    if normalized_request_mode not in {"feature", "bugfix"}:
        normalized_request_mode = "feature"
    work_mode = (
        "new"
        if scenario == "0-1"
        else ("patch" if normalized_request_mode == "bugfix" else "evolve")
    )
    default_depth = (
        "commercial"
        if scenario == "0-1"
        else ("bounded" if normalized_request_mode == "bugfix" else "architectural")
    )
    effective_depth = normalize_governance_depth(governance_depth or default_depth)
    return StructuredScopeDeclaration(
        changed_surfaces=surfaces,
        scope_complete=bool(surfaces),
        work_mode=work_mode,
        governance_depth=effective_depth,
    )


def build_scope_advisory(
    *,
    changed_surfaces: Iterable[str],
    work_mode: str,
    governance_depth: str,
    scope_complete: bool,
    generated_at: str,
) -> ScopeAdvisory:
    surfaces = sorted({str(item).strip().lower() for item in changed_surfaces if str(item).strip()})
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
            resolution = StageResolution.REQUIRE if kind == "gate" else StageResolution.EXECUTE
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


__all__ = [
    "StructuredScopeDeclaration",
    "build_scope_advisory",
    "resolve_pipeline_scope_declaration",
]
