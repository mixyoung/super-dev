from __future__ import annotations

from pathlib import Path

import yaml


def test_replay_contract_has_ten_unique_answered_scenarios() -> None:
    path = (
        Path(__file__).parents[2]
        / ".super-dev"
        / "changes"
        / "completion-verification"
        / "replay-scenarios.yaml"
    )
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    scenarios = payload["scenarios"]

    assert payload["schema_version"] == 1
    assert len(scenarios) == 10
    assert all(isinstance(item["id"], str) and item["id"].strip() for item in scenarios)
    assert len({item["id"] for item in scenarios}) == 10
    assert all(item["expected_status"] in {"PASS", "FAIL", "BLOCKED"} for item in scenarios)
    assert sum(item["category"] == "current-pass" for item in scenarios) == 3
    assert sum(item["category"] == "old-evidence" for item in scenarios) == 2
    assert sum(item["category"] == "current-fail" for item in scenarios) == 2
    old_evidence = [item for item in scenarios if item["category"] == "old-evidence"]
    assert all(item.get("expected_new_run") is True for item in old_evidence)
