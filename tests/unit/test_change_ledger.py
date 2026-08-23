from __future__ import annotations

import copy

import pytest

from super_dev.change_ledger import (
    ADAPTIVE_LEDGER_ENABLED_DEFAULT,
    ChangeIntent,
    ChangeLedger,
    ChangeLedgerError,
    EvidenceReference,
    ScopeAdvisory,
    StageResolution,
    StageScopeRecommendation,
)
from super_dev.scope_advisory import build_scope_advisory
from super_dev.workflow_contract import CANONICAL_NINE_STAGE_IDS


def test_real_change_has_exactly_nine_canonical_stages() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent=ChangeIntent.BUILD,
        governance_depth="commercial",
        work_mode="evolve",
    )

    assert tuple(stage.stage for stage in ledger.stages) == CANONICAL_NINE_STAGE_IDS
    assert ledger.shadow_only is True
    assert ledger.get_stage("docs_confirm").kind == "gate"
    assert ledger.get_stage("docs_confirm").resolution == StageResolution.REQUIRE
    assert ledger.get_stage("backend").kind == "work"
    assert ledger.get_stage("quality").kind == "work_gate"
    assert ADAPTIVE_LEDGER_ENABLED_DEFAULT is False


@pytest.mark.parametrize("intent", [ChangeIntent.CHAT, ChangeIntent.EXPLAIN])
def test_chat_and_explain_do_not_create_change_ledgers(intent: ChangeIntent) -> None:
    with pytest.raises(ChangeLedgerError, match="do not create"):
        ChangeLedger.create(
            change_id="change-1",
            harness_version="2.4.0",
            intent=intent,
            governance_depth="bounded",
            work_mode="evolve",
        )


def test_ledger_round_trip_preserves_contract() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="quick_edit",
        governance_depth="bounded",
        work_mode="patch",
    )
    ledger.get_stage("quality").evidence = [
        EvidenceReference(
            locator="output/quality.json",
            owner="qa",
            captured_at="2026-08-22T00:00:00+00:00",
            candidate_scope=ledger.change_id,
            expires_at="2026-08-23T00:00:00+00:00",
            invalidation_triggers=["source-changed"],
        )
    ]

    restored = ChangeLedger.from_dict(ledger.to_dict())

    assert restored.to_dict() == ledger.to_dict()


def test_missing_stage_is_rejected() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="debug",
        governance_depth="bounded",
        work_mode="patch",
    )
    ledger.stages.pop()

    with pytest.raises(ChangeLedgerError, match="canonical nine-stage order"):
        ledger.validate_stage_roster()


def test_unknown_governance_depth_is_rejected() -> None:
    with pytest.raises(ChangeLedgerError, match="Unsupported governance depth"):
        ChangeLedger.create(
            change_id="change-1",
            harness_version="2.4.0",
            intent="build",
            governance_depth="mystery",
            work_mode="new",
        )


def test_non_shadow_ledger_is_rejected() -> None:
    with pytest.raises(ChangeLedgerError, match="shadow-only"):
        ChangeLedger.create(
            change_id="change-1",
            harness_version="2.4.0",
            intent="build",
            governance_depth="architectural",
            work_mode="evolve",
            shadow_only=False,
        )


def test_illegal_resolution_is_rejected_during_readback() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="build",
        governance_depth="architectural",
        work_mode="evolve",
    )
    payload = ledger.to_dict()
    payload["stages"][0]["resolution"] = "WAIVE"

    with pytest.raises(ChangeLedgerError, match="invalid for work stage"):
        ChangeLedger.from_dict(payload)


def test_shadow_boolean_strings_are_rejected() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="build",
        governance_depth="architectural",
        work_mode="evolve",
    )
    payload = ledger.to_dict()
    payload["shadow_only"] = "false"

    with pytest.raises(ChangeLedgerError, match="must be a boolean"):
        ChangeLedger.from_dict(payload)


def test_foreign_harness_identity_is_rejected() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="build",
        governance_depth="architectural",
        work_mode="evolve",
    )
    payload = ledger.to_dict()
    payload["harness_id"] = "another-harness"

    with pytest.raises(ChangeLedgerError, match="active Super Dev"):
        ChangeLedger.from_dict(payload)


def test_old_ledger_without_scope_advisory_remains_unchanged() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="build",
        governance_depth="bounded",
        work_mode="patch",
    )

    payload = ledger.to_dict()

    assert "scope_advisory" not in payload
    assert ChangeLedger.from_dict(payload).scope_advisory is None


def test_scope_advisory_round_trip_does_not_change_real_stage_resolutions() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="debug",
        governance_depth="bounded",
        work_mode="patch",
    )
    ledger.scope_advisory = build_scope_advisory(
        changed_surfaces={"backend"},
        work_mode=ledger.work_mode,
        governance_depth=ledger.governance_depth,
        scope_complete=True,
        generated_at="2026-08-23T00:00:00+00:00",
    )

    restored = ChangeLedger.from_dict(ledger.to_dict())

    assert restored.to_dict() == ledger.to_dict()
    assert restored.schema_version == 1
    assert restored.scope_advisory is not None
    assert restored.scope_advisory.control_authority == "none"
    assert restored.get_stage("frontend").resolution == StageResolution.EXECUTE
    frontend_recommendation = next(
        item for item in restored.scope_advisory.recommendations if item.stage == "frontend"
    )
    assert frontend_recommendation.recommended_resolution == StageResolution.NOT_APPLICABLE
    assert frontend_recommendation.approval_required is True


def test_incomplete_scope_advisory_must_keep_conservative_full_plan() -> None:
    advisory = build_scope_advisory(
        changed_surfaces=set(),
        work_mode="evolve",
        governance_depth="bounded",
        scope_complete=False,
        generated_at="2026-08-23T00:00:00+00:00",
    )

    assert all(
        item.recommended_resolution
        == (StageResolution.REQUIRE if item.kind == "gate" else StageResolution.EXECUTE)
        for item in advisory.recommendations
    )


def test_scope_advisory_rejects_control_authority_and_unapproved_reduction() -> None:
    with pytest.raises(ChangeLedgerError, match="control authority"):
        ScopeAdvisory(
            generated_at="2026-08-23T00:00:00+00:00",
            scope_complete=True,
            changed_surfaces=[],
            control_authority="gate",
            recommendations=[],
        )

    with pytest.raises(ChangeLedgerError, match="require approval"):
        StageScopeRecommendation(
            stage="frontend",
            kind="work",
            recommended_resolution=StageResolution.NOT_APPLICABLE,
            reason="Not involved",
            approval_required=False,
        )


def test_scope_advisory_rejects_unknown_surface_even_when_scope_is_incomplete() -> None:
    advisory = build_scope_advisory(
        changed_surfaces=set(),
        work_mode="evolve",
        governance_depth="bounded",
        scope_complete=False,
        generated_at="2026-08-23T00:00:00+00:00",
    ).to_dict()
    advisory["changed_surfaces"] = ["unknown-surface"]

    with pytest.raises(ChangeLedgerError, match="Invalid scope advisory object"):
        ScopeAdvisory.from_dict(advisory)


def test_malformed_scope_advisory_is_wrapped_as_change_ledger_error() -> None:
    ledger = ChangeLedger.create(
        change_id="change-1",
        harness_version="2.4.0",
        intent="debug",
        governance_depth="bounded",
        work_mode="patch",
    )
    ledger.scope_advisory = build_scope_advisory(
        changed_surfaces={"backend"},
        work_mode="patch",
        governance_depth="bounded",
        scope_complete=True,
        generated_at="2026-08-23T00:00:00+00:00",
    )
    base = ledger.to_dict()

    malformed_payloads = []
    missing_stage = copy.deepcopy(base)
    missing_stage["scope_advisory"]["recommendations"][0].pop("stage")
    malformed_payloads.append(missing_stage)
    missing_approval = copy.deepcopy(base)
    missing_approval["scope_advisory"]["recommendations"][0].pop(
        "approval_required"
    )
    malformed_payloads.append(missing_approval)
    invalid_resolution = copy.deepcopy(base)
    invalid_resolution["scope_advisory"]["recommendations"][0][
        "recommended_resolution"
    ] = "INVALID"
    malformed_payloads.append(invalid_resolution)
    invalid_recommendations = copy.deepcopy(base)
    invalid_recommendations["scope_advisory"]["recommendations"] = None
    malformed_payloads.append(invalid_recommendations)
    invalid_surfaces = copy.deepcopy(base)
    invalid_surfaces["scope_advisory"]["changed_surfaces"] = None
    malformed_payloads.append(invalid_surfaces)

    for payload in malformed_payloads:
        with pytest.raises(ChangeLedgerError, match="Invalid scope_advisory payload"):
            ChangeLedger.from_dict(payload)


def test_generated_advisory_uses_only_execute_require_or_not_applicable() -> None:
    advisory = build_scope_advisory(
        changed_surfaces={"backend"},
        work_mode="patch",
        governance_depth="bounded",
        scope_complete=True,
        generated_at="2026-08-23T00:00:00+00:00",
    )

    assert {item.recommended_resolution for item in advisory.recommendations} <= {
        StageResolution.EXECUTE,
        StageResolution.REQUIRE,
        StageResolution.NOT_APPLICABLE,
    }
