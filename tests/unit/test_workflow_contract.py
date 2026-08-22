from __future__ import annotations

from super_dev.workflow_contract import (
    SEEAI_WORKFLOW_CONTRACT,
    STANDARD_WORKFLOW_CONTRACT,
    get_agent_team,
    get_gate_config,
    get_phase_chain,
    get_phase_kinds,
    get_workflow_contract,
)


def test_standard_workflow_contract_exposes_full_pipeline_contract():
    contract = get_workflow_contract("standard")

    assert contract is STANDARD_WORKFLOW_CONTRACT
    assert contract.flow_variant == "standard"
    assert contract.sprint_horizon_minutes == 240
    assert get_phase_chain("standard") == (
        "research",
        "docs",
        "docs_confirm",
        "spec",
        "frontend",
        "preview_confirm",
        "backend",
        "quality",
        "delivery",
    )
    assert get_gate_config("standard") == {
        "docs_confirm": True,
        "preview_confirm": True,
        "quality": True,
    }
    assert get_phase_kinds("standard")["docs_confirm"] == "gate"
    assert get_phase_kinds("standard")["preview_confirm"] == "gate"
    assert get_phase_kinds("standard")["backend"] == "work"
    assert get_phase_kinds("standard")["quality"] == "work_gate"
    assert get_phase_kinds("standard")["delivery"] == "work"
    assert [agent.key for agent in get_agent_team("standard")] == [
        "researcher",
        "pm",
        "architect",
        "uiux",
        "builder",
        "qa",
    ]
    assert any("预览确认门必须保留" in item for item in contract.quality_floor)


def test_seeai_workflow_contract_exposes_competition_fast_path():
    contract = get_workflow_contract("seeai")

    assert contract is SEEAI_WORKFLOW_CONTRACT
    assert contract.flow_variant == "seeai"
    assert contract.sprint_horizon_minutes == 30
    assert get_phase_chain("seeai") == (
        "research",
        "docs",
        "docs_confirm",
        "spec",
        "build_fullstack",
        "polish",
        "quality",
        "delivery",
    )
    assert get_gate_config("seeai") == {
        "docs_confirm": True,
        "preview_confirm": False,
        "quality": True,
    }
    assert [agent.key for agent in get_agent_team("seeai")] == [
        "rapid_researcher",
        "sprint_pm",
        "fullstack_builder",
        "visual_polish",
        "qa",
    ]
    assert "3 秒内必须让评委看懂主题和亮点" in contract.quality_floor[0]
    assert "30 秒内必须能完整走完一条主演示路径" in contract.quality_floor[1]
    assert "wow 点" in contract.quality_floor[2]
    assert "3 秒第一印象" in contract.judge_checklist[0]
    assert "30 秒主演示路径" in contract.judge_checklist[1]


def test_unknown_variant_falls_back_to_standard_contract():
    contract = get_workflow_contract("anything-else")

    assert contract is STANDARD_WORKFLOW_CONTRACT
    assert get_phase_chain("anything-else") == get_phase_chain("standard")
    assert get_gate_config("anything-else") == get_gate_config("standard")
