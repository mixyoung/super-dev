from __future__ import annotations

import json
from pathlib import Path

import yaml

from super_dev.extensions.verification_metrics import (
    REPLAY_MEASUREMENT_SCOPE,
    summarize_verification_metrics,
)


def _write_records(path: Path, records: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n",
        encoding="utf-8",
    )


def _write_replay_contract(
    path: Path,
    scenario_ids: list[str],
    *,
    expected_statuses: dict[str, str] | None = None,
) -> None:
    expected_statuses = expected_statuses or {}
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "scenarios": [
                    {
                        "id": scenario_id,
                        "expected_status": expected_statuses.get(scenario_id, "PASS"),
                    }
                    for scenario_id in scenario_ids
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _complete_replay_record(
    scenario_id: str,
    *,
    expected_status: str = "PASS",
    legacy_status: str | None = None,
    verification_status: str | None = None,
    **overrides: object,
) -> dict:
    legacy_status = legacy_status or expected_status
    verification_status = verification_status or expected_status
    record = {
        "schema_version": 1,
        "record_type": "verification-replay",
        "measurement_scope": REPLAY_MEASUREMENT_SCOPE,
        "scenario_id": scenario_id,
        "replay_run_id": "replay-batch-1",
        "candidate_digest": "candidate-a",
        "legacy_status": legacy_status,
        "verification_status": verification_status,
        "legacy_false_completion": legacy_status == "PASS" and expected_status != "PASS",
        "verification_false_completion": (
            verification_status == "PASS" and expected_status != "PASS"
        ),
        "legacy_false_block": expected_status == "PASS" and legacy_status != "PASS",
        "verification_false_block": (expected_status == "PASS" and verification_status != "PASS"),
        "legacy_time_to_accepted_ms": 100 if legacy_status == expected_status else None,
        "verification_time_to_accepted_ms": (
            90 if verification_status == expected_status else None
        ),
        "safety_regression": False,
    }
    record.update(overrides)
    return record


def _completed_candidate_records() -> list[dict]:
    records: list[dict] = []
    for index in range(3):
        run_id = f"run-{index}"
        sample_id = f"sample-{index}"
        records.extend(
            [
                {
                    "record_type": "verification-candidate-registration",
                    "sample_id": sample_id,
                    "acceptor": "user",
                    "registered_at": "2026-08-25T00:00:00+00:00",
                },
                {
                    "record_type": "verification-run",
                    "run_id": run_id,
                    "started_at": "2026-08-25T00:01:00+00:00",
                },
                {
                    "record_type": "verification-candidate-binding",
                    "sample_id": sample_id,
                    "run_id": run_id,
                },
                {
                    "record_type": "verification-adjudication",
                    "run_id": run_id,
                    "actor": "user",
                    "label": "correct_pass",
                    "safety_regression": False,
                },
            ]
        )
    return records


def test_unreviewed_and_non_user_labels_are_excluded(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    _write_records(
        path,
        [
            {
                "record_type": "verification-run",
                "run_id": "run-1",
                "started_at": "2026-08-25T00:01:00+00:00",
            },
            {
                "record_type": "verification-adjudication",
                "run_id": "run-1",
                "actor": "ai",
                "label": "correct_pass",
            },
        ],
    )

    summary = summarize_verification_metrics(path)

    assert summary.total_runs == 1
    assert summary.adjudicated_runs == 0
    assert summary.unreviewed_runs == 1
    assert summary.recommend_stage_2b is False
    assert any("非用户" in item for item in summary.warnings)


def test_real_candidate_counts_only_when_registered_before_run(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    _write_records(
        path,
        [
            {
                "record_type": "verification-candidate-registration",
                "sample_id": "sample-1",
                "acceptor": "user",
                "registered_at": "2026-08-25T00:00:00+00:00",
            },
            {
                "record_type": "verification-run",
                "run_id": "run-1",
                "started_at": "2026-08-25T00:01:00+00:00",
            },
            {
                "record_type": "verification-candidate-binding",
                "sample_id": "sample-1",
                "run_id": "run-1",
            },
            {
                "record_type": "verification-adjudication",
                "run_id": "run-1",
                "actor": "user",
                "label": "correct_pass",
            },
            {
                "record_type": "verification-candidate-registration",
                "sample_id": "sample-2",
                "acceptor": "user",
                "registered_at": "2026-08-25T00:02:00+00:00",
            },
            {
                "record_type": "verification-candidate-binding",
                "sample_id": "sample-2",
                "run_id": "run-1",
            },
        ],
    )

    summary = summarize_verification_metrics(path)

    assert summary.real_candidates_completed == 1


def test_multiple_samples_bound_to_one_run_count_once(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    records = [
        {
            "record_type": "verification-run",
            "run_id": "run-1",
            "started_at": "2026-08-25T00:01:00+00:00",
        },
        {
            "record_type": "verification-adjudication",
            "run_id": "run-1",
            "actor": "user",
            "label": "correct_pass",
        },
    ]
    for sample_id in ("sample-1", "sample-2"):
        records.extend(
            [
                {
                    "record_type": "verification-candidate-registration",
                    "sample_id": sample_id,
                    "acceptor": "user",
                    "registered_at": "2026-08-25T00:00:00+00:00",
                },
                {
                    "record_type": "verification-candidate-binding",
                    "sample_id": sample_id,
                    "run_id": "run-1",
                },
            ]
        )
    _write_records(path, records)

    summary = summarize_verification_metrics(path)

    assert summary.real_candidates_completed == 1


def test_runtime_metrics_summarize_duration_corrections_and_candidate_changes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metrics.jsonl"
    _write_records(
        path,
        [
            {
                "record_type": "verification-run",
                "run_id": "run-1",
                "candidate_digest": "candidate-a",
                "verification_duration_ms": 100,
                "candidate_changed_during_run": True,
            },
            {
                "record_type": "verification-run",
                "run_id": "run-2",
                "candidate_digest": "candidate-a",
                "verification_duration_ms": 300,
                "candidate_changed_during_run": False,
            },
        ],
    )

    summary = summarize_verification_metrics(path)

    assert summary.verification_duration_median_ms == 200.0
    assert summary.correction_loops == 1
    assert summary.candidate_changed_during_run == 1


def test_contract_definitions_do_not_count_as_executed_replays(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    contract_path = tmp_path / "replay-scenarios.yaml"
    _write_records(path, [])
    _write_replay_contract(contract_path, [f"scenario-{index}" for index in range(10)])

    summary = summarize_verification_metrics(
        path,
        contract_path,
        current_candidate_digest="candidate-a",
    )

    assert summary.replay_scenarios_defined == 10
    assert summary.replay_scenarios == 0
    assert summary.recommend_stage_2b is False
    assert any("缺失 10 条实测回放记录" in item for item in summary.warnings)


def test_unknown_replay_id_is_ignored_when_contract_is_provided(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    contract_path = tmp_path / "replay-scenarios.yaml"
    scenario_ids = [f"scenario-{index}" for index in range(10)]
    _write_replay_contract(contract_path, scenario_ids)
    _write_records(
        path,
        [
            _complete_replay_record(scenario_ids[0]),
            {"record_type": "verification-replay", "scenario_id": "unknown-scenario"},
        ],
    )

    summary = summarize_verification_metrics(path, contract_path)

    assert summary.replay_scenarios_defined == 10
    assert summary.replay_scenarios == 1
    assert any("合同外回放场景已忽略" in item for item in summary.warnings)
    assert summary.recommend_stage_2b is False


def test_contract_counts_only_complete_valid_replays(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    contract_path = tmp_path / "replay-scenarios.yaml"
    scenario_ids = [f"scenario-{index}" for index in range(10)]
    _write_replay_contract(contract_path, scenario_ids)
    records = [_complete_replay_record(scenario_ids[0])]
    records.extend(
        {"record_type": "verification-replay", "scenario_id": scenario_id}
        for scenario_id in scenario_ids[1:8]
    )
    records.extend(
        [
            _complete_replay_record(
                scenario_ids[8],
                verification_false_completion=True,
                legacy_false_block=True,
                verification_false_block=True,
                legacy_time_to_accepted_ms=-1,
            ),
            _complete_replay_record(
                scenario_ids[9],
                safety_regression=True,
                verification_time_to_accepted_ms=True,
            ),
        ]
    )
    _write_records(path, records)

    summary = summarize_verification_metrics(path, contract_path)

    assert summary.replay_scenarios_defined == 10
    assert summary.replay_scenarios == 1
    assert summary.false_completions == 0
    assert summary.false_blocks == 0
    assert summary.safety_regressions == 0
    assert summary.legacy_time_to_accepted_median_ms == 100.0
    assert summary.verification_time_to_accepted_median_ms == 90.0
    assert summary.recommend_stage_2b is False
    assert sum("不完整或非法" in item for item in summary.warnings) == 9


def test_contract_rejects_missing_or_wrong_measurement_scope(tmp_path: Path) -> None:
    contract_path = tmp_path / "replay-scenarios.yaml"
    _write_replay_contract(contract_path, ["scenario-0"])

    for label, scope in (("missing", None), ("wrong", "fresh-verification-only-v0")):
        path = tmp_path / f"{label}.jsonl"
        record = _complete_replay_record("scenario-0")
        if scope is None:
            record.pop("measurement_scope")
        else:
            record["measurement_scope"] = scope
        _write_records(path, [record])

        summary = summarize_verification_metrics(
            path,
            contract_path,
            current_candidate_digest="candidate-a",
        )

        assert summary.replay_scenarios == 0
        assert summary.recommend_stage_2b is False
        assert any("measurement_scope" in item for item in summary.warnings)


def test_invalid_or_duplicate_contract_does_not_fabricate_completion(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    _write_records(
        path,
        [{"record_type": "verification-replay", "scenario_id": "scenario-0"}],
    )
    invalid_contracts = (
        "schema_version: [\n",
        yaml.safe_dump({"schema_version": True, "scenarios": []}),
        yaml.safe_dump({"schema_version": 1.0, "scenarios": []}),
        yaml.safe_dump({"schema_version": 1, "scenarios": {}}),
        yaml.safe_dump(
            {
                "schema_version": 1,
                "scenarios": [{"id": "", "expected_status": "PASS"}],
            }
        ),
        yaml.safe_dump(
            {
                "schema_version": 1,
                "scenarios": [{"id": "scenario-0", "expected_status": "UNKNOWN"}],
            }
        ),
        yaml.safe_dump(
            {
                "schema_version": 1,
                "scenarios": [
                    {"id": "scenario-0", "expected_status": "PASS"},
                    {"id": "scenario-0", "expected_status": "FAIL"},
                ],
            },
            sort_keys=False,
        ),
    )

    for index, content in enumerate(invalid_contracts):
        contract_path = tmp_path / f"invalid-contract-{index}.yaml"
        contract_path.write_text(content, encoding="utf-8")

        summary = summarize_verification_metrics(path, contract_path)

        assert summary.replay_scenarios_defined == 0
        assert summary.replay_scenarios == 0
        assert summary.recommend_stage_2b is False
        assert any("回放合同损坏" in item for item in summary.warnings)


def test_without_contract_keeps_legacy_replay_metrics_but_cannot_recommend(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metrics.jsonl"
    _write_records(
        path,
        [
            {
                "record_type": "verification-replay",
                "scenario_id": "legacy-scenario",
                "legacy_time_to_accepted_ms": 100,
                "verification_time_to_accepted_ms": 90,
            }
        ],
    )

    summary = summarize_verification_metrics(path)

    assert summary.replay_scenarios_defined == 0
    assert summary.replay_scenarios == 1
    assert summary.legacy_time_to_accepted_median_ms == 100.0
    assert summary.verification_time_to_accepted_median_ms == 90.0
    assert summary.recommend_stage_2b is False


def test_wrong_status_requires_null_time_and_correct_status_requires_number(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metrics.jsonl"
    contract_path = tmp_path / "replay-scenarios.yaml"
    scenario_ids = ["wrong-time", "missing-correct-time"]
    expected = {scenario_id: "FAIL" for scenario_id in scenario_ids}
    _write_replay_contract(contract_path, scenario_ids, expected_statuses=expected)
    _write_records(
        path,
        [
            _complete_replay_record(
                scenario_ids[0],
                expected_status="FAIL",
                legacy_status="PASS",
                legacy_time_to_accepted_ms=12,
            ),
            _complete_replay_record(
                scenario_ids[1],
                expected_status="FAIL",
                verification_time_to_accepted_ms=None,
            ),
        ],
    )

    summary = summarize_verification_metrics(
        path,
        contract_path,
        current_candidate_digest="candidate-a",
    )

    assert summary.replay_scenarios == 0
    assert any("错误结论必须为 null" in item for item in summary.warnings)
    assert any("正确结论必须是有限非负数字" in item for item in summary.warnings)


def test_status_derived_boolean_mismatch_rejects_replay(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    contract_path = tmp_path / "replay-scenarios.yaml"
    _write_replay_contract(
        contract_path,
        ["false-completion"],
        expected_statuses={"false-completion": "FAIL"},
    )
    _write_records(
        path,
        [
            _complete_replay_record(
                "false-completion",
                expected_status="FAIL",
                legacy_status="PASS",
                legacy_false_completion=False,
            )
        ],
    )

    summary = summarize_verification_metrics(path, contract_path)

    assert summary.replay_scenarios == 0
    assert any("派生事实不一致" in item for item in summary.warnings)


def test_time_medians_use_only_same_record_pairs(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    contract_path = tmp_path / "replay-scenarios.yaml"
    scenario_ids = ["paired", "legacy-only", "verification-only"]
    _write_replay_contract(contract_path, scenario_ids)
    _write_records(
        path,
        [
            _complete_replay_record(
                "paired",
                legacy_time_to_accepted_ms=100,
                verification_time_to_accepted_ms=200,
            ),
            _complete_replay_record(
                "legacy-only",
                verification_status="FAIL",
                legacy_time_to_accepted_ms=1_000,
            ),
            _complete_replay_record(
                "verification-only",
                legacy_status="BLOCKED",
                verification_time_to_accepted_ms=1,
            ),
        ],
    )

    summary = summarize_verification_metrics(
        path,
        contract_path,
        current_candidate_digest="candidate-a",
    )

    assert summary.replay_scenarios == 3
    assert summary.legacy_correct_replays == 2
    assert summary.verification_correct_replays == 2
    assert summary.timing_comparable_replays == 1
    assert summary.legacy_time_to_accepted_median_ms == 100.0
    assert summary.verification_time_to_accepted_median_ms == 200.0


def test_mixed_replay_batch_or_candidate_rejects_recommendation(tmp_path: Path) -> None:
    contract_path = tmp_path / "replay-scenarios.yaml"
    scenario_ids = [f"scenario-{index}" for index in range(10)]
    _write_replay_contract(contract_path, scenario_ids)

    for changed_field, changed_value, warning_text in (
        ("replay_run_id", "replay-batch-2", "多个 replay_run_id"),
        ("candidate_digest", "candidate-b", "多个 candidate_digest"),
    ):
        path = tmp_path / f"mixed-{changed_field}.jsonl"
        replays = [_complete_replay_record(item) for item in scenario_ids]
        replays[-1][changed_field] = changed_value
        _write_records(path, [*_completed_candidate_records(), *replays])

        summary = summarize_verification_metrics(
            path,
            contract_path,
            current_candidate_digest="candidate-a",
        )

        assert summary.replay_scenarios == 10
        assert summary.recommend_stage_2b is False
        assert any(warning_text in item for item in summary.warnings)


def test_current_candidate_mismatch_rejects_recommendation(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    contract_path = tmp_path / "replay-scenarios.yaml"
    scenario_ids = [f"scenario-{index}" for index in range(10)]
    _write_replay_contract(contract_path, scenario_ids)
    _write_records(
        path,
        [
            *_completed_candidate_records(),
            *[_complete_replay_record(item) for item in scenario_ids],
        ],
    )

    summary = summarize_verification_metrics(
        path,
        contract_path,
        current_candidate_digest="candidate-b",
    )

    assert summary.replay_candidate_matches_current is False
    assert summary.recommend_stage_2b is False
    assert any("与当前代码版本不一致" in item for item in summary.warnings)


def test_stage_2b_is_only_recommended_after_all_thresholds(tmp_path: Path) -> None:
    path = tmp_path / "metrics.jsonl"
    contract_path = tmp_path / "replay-scenarios.yaml"
    scenario_ids = [f"scenario-{index}" for index in range(10)]
    _write_replay_contract(contract_path, scenario_ids)
    records: list[dict] = []
    for index in range(3):
        run_id = f"run-{index}"
        sample_id = f"sample-{index}"
        records.extend(
            [
                {
                    "record_type": "verification-candidate-registration",
                    "sample_id": sample_id,
                    "acceptor": "user",
                    "registered_at": "2026-08-25T00:00:00+00:00",
                },
                {
                    "record_type": "verification-run",
                    "run_id": run_id,
                    "started_at": "2026-08-25T00:01:00+00:00",
                },
                {
                    "record_type": "verification-candidate-binding",
                    "sample_id": sample_id,
                    "run_id": run_id,
                },
                {
                    "record_type": "verification-adjudication",
                    "run_id": run_id,
                    "actor": "user",
                    "label": "correct_pass",
                    "safety_regression": False,
                },
            ]
        )
    for scenario_id in scenario_ids:
        records.append(_complete_replay_record(scenario_id))
    _write_records(path, records)

    summary = summarize_verification_metrics(
        path,
        contract_path,
        current_candidate_digest="candidate-a",
    )

    assert summary.replay_scenarios_defined == 10
    assert summary.replay_scenarios == 10
    assert summary.real_candidates_completed == 3
    assert summary.legacy_false_completions == 0
    assert summary.false_completions == 0
    assert summary.false_block_delta_percent == 0.0
    assert summary.legacy_correct_replays == 10
    assert summary.verification_correct_replays == 10
    assert summary.timing_comparable_replays == 10
    assert summary.replay_run_id == "replay-batch-1"
    assert summary.replay_candidate_digest == "candidate-a"
    assert summary.replay_candidate_matches_current is True
    assert summary.recommend_stage_2b is True
