import pytest

from super_dev.experts.toolkit import PHASE_EXPERT_MAP
from super_dev.workflow_contract import CANONICAL_NINE_STAGE_IDS
from super_dev.workflow_stage_truth import (
    CANONICAL_WORKFLOW_STAGE_CHAIN,
    WORKFLOW_STAGE_EXPERTS,
    active_experts_for_stage,
    canonical_stage_for_engine_phase,
    normalize_stage_key,
    resolve_engine_phase_names,
    stages_require_docs_confirmation,
    stages_require_preview_confirmation,
)


def test_stage_truth_uses_the_canonical_nine_stage_roster() -> None:
    assert CANONICAL_WORKFLOW_STAGE_CHAIN == ("baseline", *CANONICAL_NINE_STAGE_IDS)


def test_normalize_stage_key_maps_legacy_aliases() -> None:
    assert normalize_stage_key("discovery") == "research"
    assert normalize_stage_key("intelligence") == "research"
    assert normalize_stage_key("drafting") == "docs"
    assert normalize_stage_key("redteam") == "quality"
    assert normalize_stage_key("qa") == "quality"
    assert normalize_stage_key("deployment") == "delivery"


def test_resolve_engine_phase_names_accepts_canonical_stage_requests() -> None:
    assert resolve_engine_phase_names(["research"]) == ["discovery", "intelligence"]
    assert resolve_engine_phase_names(["docs"]) == ["drafting"]
    assert resolve_engine_phase_names(["quality"]) == ["redteam", "qa"]
    assert resolve_engine_phase_names(["delivery"]) == ["delivery"]
    assert resolve_engine_phase_names(["delivery_full"]) == ["delivery", "deployment"]


def test_gate_stage_requirements_use_canonical_stage_truth() -> None:
    assert stages_require_docs_confirmation(["spec"]) is True
    assert stages_require_docs_confirmation(["frontend"]) is True
    assert stages_require_docs_confirmation(["quality"]) is True
    assert stages_require_docs_confirmation(["research"]) is False

    assert stages_require_preview_confirmation(["backend"]) is True
    assert stages_require_preview_confirmation(["quality"]) is True
    assert stages_require_preview_confirmation(["delivery"]) is True
    assert stages_require_preview_confirmation(["docs"]) is False


def test_engine_phase_exposes_canonical_stage_and_experts() -> None:
    assert canonical_stage_for_engine_phase("discovery") == "research"
    assert canonical_stage_for_engine_phase("drafting") == "docs"
    assert canonical_stage_for_engine_phase("redteam") == "quality"
    assert active_experts_for_stage("quality") == ("QA", "SECURITY", "RCA", "PRODUCT")


def test_legacy_phase_expert_map_is_readonly_view_of_canonical_truth() -> None:
    assert dict(PHASE_EXPERT_MAP) == dict(WORKFLOW_STAGE_EXPERTS)
    with pytest.raises(TypeError):
        PHASE_EXPERT_MAP["quality"] = ("QA",)  # type: ignore[index]


def test_readme_expert_stage_table_matches_canonical_truth() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    for readme_name in ("README.md", "README_EN.md"):
        readme = (root / readme_name).read_text(encoding="utf-8")
        for role in (
            "PRODUCT",
            "PM",
            "ARCHITECT",
            "UI",
            "UX",
            "SECURITY",
            "CODE",
            "DBA",
            "QA",
            "DEVOPS",
            "RCA",
        ):
            expected = ", ".join(
                stage for stage, experts in WORKFLOW_STAGE_EXPERTS.items() if role in experts
            )
            assert any(
                line.startswith(f"| {role} |") and expected in line for line in readme.splitlines()
            )
