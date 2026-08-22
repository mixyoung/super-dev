from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from super_dev.agent_contract import AgentAssignment, AgentLevel
from super_dev.change_ledger import EvidenceReference, StageResolution
from super_dev.shadow_validation import (
    build_representative_validation_report,
    evaluate_shadow_scenario,
    plan_shadow_scenario,
    representative_shadow_scenarios,
)
from super_dev.stage_policy import StagePolicyError
from super_dev.workflow_contract import CANONICAL_NINE_STAGE_IDS


def _coordinator() -> AgentAssignment:
    return AgentAssignment(
        task_id="shadow-evaluator",
        parent_task_id="root",
        agent_level=AgentLevel.COORDINATOR,
        role="shadow-evaluator",
        workspace="E:/shadow-validation",
        write_scope=(".super-dev/changes/**",),
        forbidden_actions=("advance-stage", "merge", "push"),
        placement_owner="root",
        result_owner="root",
        may_approve_skip=True,
        may_approve_waiver=False,
    )


def _writer() -> AgentAssignment:
    return AgentAssignment(
        task_id="writer",
        parent_task_id="shadow-evaluator",
        agent_level=AgentLevel.WRITER,
        role="writer",
        workspace="E:/shadow-validation",
        write_scope=("super_dev/**",),
        forbidden_actions=("advance-stage", "merge", "push"),
        placement_owner="shadow-evaluator",
        result_owner="shadow-evaluator",
    )


def test_representative_scenarios_cover_bounded_architectural_and_commercial() -> None:
    scenarios = representative_shadow_scenarios()

    assert tuple(item.scenario_id for item in scenarios) == (
        "bounded-backend-patch",
        "bounded-ui-change",
        "api-contract-change",
        "commercial-cross-stack",
    )
    assert {item.governance_depth for item in scenarios} == {
        "bounded",
        "architectural",
        "commercial",
    }


@pytest.mark.parametrize("scenario", representative_shadow_scenarios())
def test_representative_shadow_plan_has_no_false_skip_or_block(scenario) -> None:
    ledger = plan_shadow_scenario(
        scenario,
        actor=_coordinator(),
        harness_version="2.4.0",
    )
    evaluation = evaluate_shadow_scenario(scenario, ledger)

    assert tuple(entry.stage for entry in ledger.stages) == CANONICAL_NINE_STAGE_IDS
    assert ledger.shadow_only is True
    assert evaluation.passed is True
    assert evaluation.false_skips == ()
    assert evaluation.false_blocks == ()
    assert evaluation.evidence_reuse_errors == ()
    assert evaluation.reused_stages == ()


def test_bounded_backend_patch_records_legacy_overreach_without_hiding_quality() -> None:
    scenario = representative_shadow_scenarios()[0]
    ledger = plan_shadow_scenario(
        scenario,
        actor=_coordinator(),
        harness_version="2.4.0",
    )
    evaluation = evaluate_shadow_scenario(scenario, ledger)

    assert evaluation.legacy_reductions == (
        "research",
        "docs",
        "docs_confirm",
        "frontend",
        "preview_confirm",
    )
    assert ledger.get_stage("quality").resolution == StageResolution.EXECUTE
    assert ledger.get_stage("delivery").resolution == StageResolution.EXECUTE
    assert evaluation.user_gate_count == 0


def test_commercial_cross_stack_keeps_full_legacy_depth() -> None:
    scenario = representative_shadow_scenarios()[-1]
    ledger = plan_shadow_scenario(
        scenario,
        actor=_coordinator(),
        harness_version="2.4.0",
    )
    evaluation = evaluate_shadow_scenario(scenario, ledger)

    assert evaluation.legacy_reductions == ()
    assert evaluation.scope_explanation_count == 0
    assert evaluation.user_gate_count == 2


def test_evaluator_detects_false_skip_false_block_and_bad_reuse() -> None:
    scenario = representative_shadow_scenarios()[0]
    ledger = plan_shadow_scenario(
        scenario,
        actor=_coordinator(),
        harness_version="2.4.0",
    )
    ledger.get_stage("backend").resolution = StageResolution.NOT_APPLICABLE
    ledger.get_stage("frontend").resolution = StageResolution.EXECUTE
    now = datetime.now(timezone.utc)
    ledger.get_stage("research").resolution = StageResolution.REUSE
    ledger.get_stage("research").evidence = [
        EvidenceReference(
            locator="output/old-research.md",
            owner="researcher",
            captured_at=now.isoformat(),
            candidate_scope="another-change",
            expires_at=(now + timedelta(hours=1)).isoformat(),
        )
    ]

    evaluation = evaluate_shadow_scenario(scenario, ledger)

    assert evaluation.false_skips == ("backend",)
    assert evaluation.false_blocks == ("frontend",)
    assert evaluation.evidence_reuse_errors == ("research",)
    assert evaluation.passed is False


def test_valid_but_undeclared_reuse_is_rejected_before_planning() -> None:
    scenario = representative_shadow_scenarios()[0]
    now = datetime.now(timezone.utc)
    evidence = EvidenceReference(
        locator="output/backend-proof.json",
        owner="backend-reviewer",
        captured_at=now.isoformat(),
        candidate_scope=scenario.scenario_id,
        expires_at=(now + timedelta(hours=1)).isoformat(),
    )

    with pytest.raises(ValueError, match="not approved"):
        plan_shadow_scenario(
            scenario,
            actor=_coordinator(),
            harness_version="2.4.0",
            reusable_evidence={"backend": [evidence]},
        )


@pytest.mark.parametrize("candidate_scope,expires_delta", [("other-change", 1), ("project", -1)])
def test_planner_rejects_out_of_scope_or_expired_reuse(
    candidate_scope: str,
    expires_delta: int,
) -> None:
    scenario = representative_shadow_scenarios()[2]
    now = datetime.now(timezone.utc)
    evidence = EvidenceReference(
        locator="output/research.md",
        owner="researcher",
        captured_at=now.isoformat(),
        candidate_scope=candidate_scope,
        expires_at=(now + timedelta(hours=expires_delta)).isoformat(),
    )

    with pytest.raises(StagePolicyError, match="stale|out of scope"):
        plan_shadow_scenario(
            scenario,
            actor=_coordinator(),
            harness_version="2.4.0",
            reusable_evidence={"research": [evidence]},
        )


def test_planner_is_independent_from_the_frozen_expected_answer() -> None:
    scenario = replace(
        representative_shadow_scenarios()[0],
        mandatory_stages=("spec", "frontend", "backend", "quality", "delivery"),
    )
    ledger = plan_shadow_scenario(
        scenario,
        actor=_coordinator(),
        harness_version="2.4.0",
    )

    evaluation = evaluate_shadow_scenario(scenario, ledger)

    assert evaluation.false_skips == ("frontend",)
    assert evaluation.passed is False


def test_writer_cannot_plan_shortcuts_for_a_scenario() -> None:
    with pytest.raises(StagePolicyError, match="cannot approve"):
        plan_shadow_scenario(
            representative_shadow_scenarios()[0],
            actor=_writer(),
            harness_version="2.4.0",
        )


def test_representative_report_is_read_only_and_all_scenarios_pass() -> None:
    report = build_representative_validation_report(
        actor=_coordinator(),
        harness_version="2.4.0",
    )

    assert report["read_only"] is True
    assert report["control_authority"] == "none"
    assert report["production_writes"] is False
    assert report["scenario_count"] == 4
    assert report["passed_count"] == 4
    assert report["false_skip_count"] == 0
    assert report["false_block_count"] == 0
    assert report["evidence_reuse_error_count"] == 0
    assert report["reuse_count"] == 1
    assert report["scope_explanation_count"] == 10
    api_scenario = next(
        item for item in report["scenarios"] if item["scenario_id"] == "api-contract-change"
    )
    assert api_scenario["reused_stages"] == ["research"]
    assert "复用1项" in api_scenario["coach_summary"]
    assert "质量验证和交付收口始终保留" in api_scenario["coach_summary"]
