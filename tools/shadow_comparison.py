"""Developer-only report generator for representative shadow comparisons."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from super_dev.agent_contract import AgentAssignment, AgentLevel
from super_dev.change_ledger import EvidenceReference
from super_dev.workflow_contract import CANONICAL_NINE_STAGE_IDS
from tests.fixtures.shadow_scenarios import (
    ShadowValidationScenario,
    representative_shadow_scenarios,
)
from tests.support.shadow_plan_harness import (
    ShadowScenarioEvaluation,
    evaluate_shadow_scenario,
    plan_shadow_scenario,
)


def build_coach_summary(
    scenario: ShadowValidationScenario,
    evaluation: ShadowScenarioEvaluation,
) -> str:
    if evaluation.legacy_reductions:
        summary = (
            f"本次为{scenario.label}；保留"
            f"{len(CANONICAL_NINE_STAGE_IDS) - len(evaluation.legacy_reductions)}"
            f"个必要阶段，缩减{len(evaluation.legacy_reductions)}个无关阶段"
        )
    else:
        summary = f"本次为{scenario.label}；按完整九阶段执行"
    if evaluation.reused_stages:
        summary += f"，复用{len(evaluation.reused_stages)}项仍在有效期内的证据"
    if evaluation.user_gate_count:
        summary += f"，需要你完成{evaluation.user_gate_count}次确认"
    else:
        summary += "，不增加中途确认"
    return summary + "。质量验证和交付收口始终保留。"


def build_representative_validation_report(
    *,
    actor: AgentAssignment,
    harness_version: str,
) -> dict[str, Any]:
    scenarios = representative_shadow_scenarios()
    evaluations: list[tuple[ShadowValidationScenario, ShadowScenarioEvaluation]] = []
    now = datetime.now(timezone.utc)
    for scenario in scenarios:
        reusable_evidence = {
            stage: [
                EvidenceReference(
                    locator=f"output/project-{stage}.md",
                    owner="shadow-evaluator",
                    captured_at=now.isoformat(),
                    candidate_scope="project",
                    expires_at=(now + timedelta(hours=1)).isoformat(),
                    invalidation_triggers=["source-evidence-changed"],
                )
            ]
            for stage in scenario.may_reuse_stages
        }
        ledger = plan_shadow_scenario(
            scenario,
            actor=actor,
            harness_version=harness_version,
            reusable_evidence=reusable_evidence or None,
        )
        evaluations.append((scenario, evaluate_shadow_scenario(scenario, ledger)))

    scenario_payloads = []
    for scenario, evaluation in evaluations:
        payload = evaluation.to_dict()
        payload["coach_summary"] = build_coach_summary(scenario, evaluation)
        scenario_payloads.append(payload)
    return {
        "mode": "shadow-comparison",
        "read_only": True,
        "control_authority": "none",
        "production_writes": False,
        "legacy_contract": "all-nine-stages-execute-or-require",
        "scenario_count": len(evaluations),
        "passed_count": sum(item.passed for _, item in evaluations),
        "false_skip_count": sum(len(item.false_skips) for _, item in evaluations),
        "false_block_count": sum(len(item.false_blocks) for _, item in evaluations),
        "evidence_reuse_error_count": sum(
            len(item.evidence_reuse_errors) for _, item in evaluations
        ),
        "reuse_count": sum(len(item.reused_stages) for _, item in evaluations),
        "scope_explanation_count": sum(
            item.scope_explanation_count for _, item in evaluations
        ),
        "scenarios": scenario_payloads,
    }


def main() -> int:
    actor = AgentAssignment(
        task_id="shadow-evaluator",
        parent_task_id="root",
        agent_level=AgentLevel.COORDINATOR,
        role="shadow-evaluator",
        workspace=str(Path.cwd().resolve()),
        write_scope=(".super-dev/changes/**",),
        forbidden_actions=("advance-stage", "merge", "push"),
        placement_owner="root",
        result_owner="root",
        may_approve_skip=True,
        may_approve_waiver=False,
    )
    report = build_representative_validation_report(
        actor=actor,
        harness_version="2.4.0",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_coach_summary", "build_representative_validation_report"]
