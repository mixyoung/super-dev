"""Single source of truth for stages required by a change scope."""

from __future__ import annotations

from collections.abc import Iterable

from .work_mode import normalize_governance_depth, normalize_work_mode
from .workflow_contract import CANONICAL_NINE_STAGE_IDS

FRONTEND_SURFACES = frozenset({"frontend", "ui", "route", "style", "component"})
BACKEND_SURFACES = frozenset({"backend", "api", "data", "authorization"})
DOCUMENT_SURFACES = frozenset(
    {
        "product",
        "architecture",
        "uiux",
        *FRONTEND_SURFACES,
        "api",
        "data",
        "authorization",
    }
)
ALWAYS_REQUIRED_STAGES = frozenset({"spec", "quality", "delivery"})


def required_stages_for(
    *,
    changed_surfaces: Iterable[str] = (),
    work_mode: str,
    governance_depth: str,
) -> tuple[str, ...]:
    """Return required stages in canonical order without changing workflow state."""

    normalized_mode = normalize_work_mode(work_mode)
    normalized_depth = normalize_governance_depth(governance_depth)
    surfaces = frozenset(
        str(item).strip().lower() for item in changed_surfaces if str(item).strip()
    )
    required = set(ALWAYS_REQUIRED_STAGES)
    if normalized_mode == "new" or normalized_depth == "commercial":
        required.update({"research", "docs", "docs_confirm"})
    if surfaces & DOCUMENT_SURFACES:
        required.update({"docs", "docs_confirm"})
    if surfaces & FRONTEND_SURFACES:
        required.update({"frontend", "preview_confirm"})
    if surfaces & BACKEND_SURFACES:
        required.add("backend")
    return tuple(stage for stage in CANONICAL_NINE_STAGE_IDS if stage in required)


__all__ = [
    "ALWAYS_REQUIRED_STAGES",
    "BACKEND_SURFACES",
    "DOCUMENT_SURFACES",
    "FRONTEND_SURFACES",
    "required_stages_for",
]
