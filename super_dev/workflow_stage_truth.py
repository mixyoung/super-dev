from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Mapping
from types import MappingProxyType

from .workflow_contract import CANONICAL_NINE_STAGE_IDS

CANONICAL_WORKFLOW_STAGE_CHAIN: tuple[str, ...] = (
    "baseline",
    *CANONICAL_NINE_STAGE_IDS,
)

SEEAI_WORKFLOW_STAGE_CHAIN: tuple[str, ...] = (
    "research",
    "docs",
    "docs_confirm",
    "spec",
    "build_fullstack",
    "polish",
    "quality",
    "delivery",
)

_CANONICAL_STAGE_ALIASES: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    [
        ("baseline", ("baseline", "current_state_audit")),
        ("research", ("research", "discovery", "intelligence")),
        ("docs", ("docs", "drafting")),
        ("docs_confirm", ("docs_confirm",)),
        ("spec", ("spec",)),
        ("frontend", ("frontend",)),
        ("preview_confirm", ("preview_confirm",)),
        ("backend", ("backend",)),
        ("quality", ("quality", "redteam", "qa")),
        ("delivery", ("delivery", "deployment")),
        ("build_fullstack", ("build_fullstack",)),
        ("polish", ("polish",)),
    ]
)

_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical for canonical, aliases in _CANONICAL_STAGE_ALIASES.items() for alias in aliases
}

_ENGINE_PHASE_SEQUENCE: OrderedDict[str, tuple[str, ...]] = OrderedDict(
    [
        ("discovery", ("discovery",)),
        ("intelligence", ("intelligence",)),
        ("drafting", ("drafting",)),
        ("redteam", ("redteam",)),
        ("qa", ("qa",)),
        ("delivery", ("delivery",)),
        ("deployment", ("deployment",)),
        ("research", ("discovery", "intelligence")),
        ("docs", ("drafting",)),
        ("quality", ("redteam", "qa")),
        ("delivery_closure", ("delivery", "deployment")),
        ("delivery_full", ("delivery", "deployment")),
        ("delivery_bundle", ("deployment",)),
    ]
)

_ENGINE_PHASE_TO_CANONICAL_STAGE: dict[str, str] = {
    "discovery": "research",
    "intelligence": "research",
    "drafting": "docs",
    "redteam": "quality",
    "qa": "quality",
    "delivery": "delivery",
    "deployment": "delivery",
}

_DOCS_CONFIRM_LATE_STAGES = {
    "spec",
    "frontend",
    "preview_confirm",
    "backend",
    "quality",
    "delivery",
}
_PREVIEW_CONFIRM_LATE_STAGES = {"backend", "quality", "delivery"}

_WORKFLOW_STAGE_EXPERTS: dict[str, tuple[str, ...]] = {
    "baseline": ("PRODUCT", "ARCHITECT", "CODE"),
    "research": ("PM", "PRODUCT", "ARCHITECT"),
    "docs": ("PM", "ARCHITECT", "UI", "UX"),
    "docs_confirm": ("PRODUCT", "PM"),
    "spec": ("PM", "ARCHITECT", "CODE"),
    "frontend": ("UI", "UX", "CODE", "QA"),
    "preview_confirm": ("PRODUCT", "UI", "UX"),
    "backend": ("ARCHITECT", "CODE", "DBA", "QA"),
    "quality": ("QA", "SECURITY", "RCA", "PRODUCT"),
    "delivery": ("DEVOPS", "QA", "PRODUCT"),
    "build_fullstack": ("PM", "ARCHITECT", "UI", "CODE", "QA"),
    "polish": ("PRODUCT", "UI", "UX", "QA"),
}

# One canonical, immutable stage-to-expert source for standard and existing SEEAI stages.
WORKFLOW_STAGE_EXPERTS: Mapping[str, tuple[str, ...]] = MappingProxyType(_WORKFLOW_STAGE_EXPERTS)


def normalize_stage_key(stage: str) -> str:
    normalized = str(stage).strip().lower()
    return _ALIAS_TO_CANONICAL.get(normalized, normalized)


def canonical_stage_for_engine_phase(stage: str) -> str:
    normalized = str(stage).strip().lower()
    return _ENGINE_PHASE_TO_CANONICAL_STAGE.get(normalized, normalize_stage_key(normalized))


def resolve_engine_phase_names(requested_stages: list[str] | None) -> list[str]:
    if not requested_stages:
        return []
    resolved: list[str] = []
    seen: set[str] = set()
    for raw_stage in requested_stages:
        normalized = str(raw_stage).strip().lower()
        phase_names = _ENGINE_PHASE_SEQUENCE.get(normalized, (normalized,))
        for phase_name in phase_names:
            if phase_name in seen:
                continue
            seen.add(phase_name)
            resolved.append(phase_name)
    return resolved


def stages_require_docs_confirmation(requested_stages: list[str] | None) -> bool:
    if not requested_stages:
        return False
    normalized = {normalize_stage_key(item) for item in requested_stages if str(item).strip()}
    return bool(normalized & _DOCS_CONFIRM_LATE_STAGES)


def stages_require_preview_confirmation(requested_stages: list[str] | None) -> bool:
    if not requested_stages:
        return False
    normalized = {normalize_stage_key(item) for item in requested_stages if str(item).strip()}
    return bool(normalized & _PREVIEW_CONFIRM_LATE_STAGES)


def active_experts_for_stage(stage: str) -> tuple[str, ...]:
    return WORKFLOW_STAGE_EXPERTS.get(normalize_stage_key(stage), ())


def applicable_experts_for_stage(
    stage: str,
    *,
    changed_surfaces: Iterable[str] = (),
    frontend: str = "",
    database: str = "",
) -> tuple[str, ...]:
    """Filter canonical candidates only when concrete applicability facts are known."""

    normalized_stage = normalize_stage_key(stage)
    candidates = list(active_experts_for_stage(normalized_stage))
    if normalized_stage in {"build_fullstack", "polish"}:
        return tuple(candidates)
    surfaces = {str(item).strip().lower() for item in changed_surfaces if str(item).strip()}
    frontend_value = str(frontend).strip().lower()
    database_value = str(database).strip().lower()
    has_context = bool(surfaces or frontend_value or database_value)
    if not has_context:
        return tuple(candidates)

    if surfaces:
        data_relevant = bool(surfaces & {"data", "database", "migration"})
        ui_relevant = bool(surfaces & {"frontend", "ui", "uiux", "route", "style", "component"})
    else:
        data_relevant = database_value not in {"", "none"}
        ui_relevant = frontend_value not in {"", "none"}
    if not data_relevant:
        candidates = [role for role in candidates if role != "DBA"]
    if not ui_relevant:
        candidates = [role for role in candidates if role not in {"UI", "UX"}]
    return tuple(candidates)
