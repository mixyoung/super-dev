from __future__ import annotations

import pytest

from super_dev.change_ledger import (
    ADAPTIVE_LEDGER_ENABLED_DEFAULT,
    ChangeIntent,
    ChangeLedger,
    ChangeLedgerError,
    EvidenceReference,
    StageResolution,
)
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
