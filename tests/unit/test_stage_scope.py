from __future__ import annotations

import pytest

from super_dev.stage_scope import (
    BACKEND_SURFACES,
    DOCUMENT_SURFACES,
    FRONTEND_SURFACES,
    required_stages_for,
)
from super_dev.workflow_contract import CANONICAL_NINE_STAGE_IDS


def test_bounded_backend_patch_keeps_only_required_delivery_stages() -> None:
    assert required_stages_for(
        changed_surfaces={"backend"},
        work_mode="patch",
        governance_depth="bounded",
    ) == ("spec", "backend", "quality", "delivery")


@pytest.mark.parametrize("surface", sorted(FRONTEND_SURFACES))
def test_user_visible_frontend_surface_requires_docs_preview_and_frontend(
    surface: str,
) -> None:
    stages = required_stages_for(
        changed_surfaces={surface},
        work_mode="evolve",
        governance_depth="bounded",
    )

    assert {"docs", "docs_confirm", "frontend", "preview_confirm"}.issubset(stages)


@pytest.mark.parametrize("surface", sorted(BACKEND_SURFACES))
def test_backend_surface_requires_backend(surface: str) -> None:
    stages = required_stages_for(
        changed_surfaces={surface},
        work_mode="evolve",
        governance_depth="architectural",
    )

    assert "backend" in stages


@pytest.mark.parametrize("surface", sorted(DOCUMENT_SURFACES))
def test_document_surface_requires_docs_and_confirmation(surface: str) -> None:
    stages = required_stages_for(
        changed_surfaces={surface},
        work_mode="evolve",
        governance_depth="bounded",
    )

    assert "docs" in stages
    assert "docs_confirm" in stages


@pytest.mark.parametrize(
    "work_mode,governance_depth",
    [("new", "bounded"), ("evolve", "commercial")],
)
def test_new_or_commercial_change_requires_research_docs_and_confirmation(
    work_mode: str,
    governance_depth: str,
) -> None:
    stages = required_stages_for(
        changed_surfaces=set(),
        work_mode=work_mode,
        governance_depth=governance_depth,
    )

    assert {"research", "docs", "docs_confirm", "spec", "quality", "delivery"}.issubset(stages)


def test_commercial_cross_stack_change_keeps_all_nine_stages() -> None:
    assert (
        required_stages_for(
            changed_surfaces={"product", "frontend", "backend", "api", "data"},
            work_mode="evolve",
            governance_depth="commercial",
        )
        == CANONICAL_NINE_STAGE_IDS
    )


def test_unknown_governance_depth_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported governance depth"):
        required_stages_for(
            changed_surfaces=set(),
            work_mode="evolve",
            governance_depth="mystery",
        )


def test_unknown_changed_surface_is_rejected_instead_of_skipped() -> None:
    with pytest.raises(ValueError, match="Unsupported changed surfaces"):
        required_stages_for(
            changed_surfaces={"mystery-surface"},
            work_mode="evolve",
            governance_depth="bounded",
        )
