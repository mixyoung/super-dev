"""完成前验证试点指标的只读汇总。"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

import yaml  # type: ignore[import-untyped]

_ADJUDICATION_LABELS = {
    "correct_block",
    "false_block",
    "correct_pass",
    "escaped_defect",
}
_REPLAY_EXPECTED_STATUSES = {"PASS", "FAIL", "BLOCKED"}
REPLAY_MEASUREMENT_SCOPE = "release-readiness-request-to-report-v1"
_REPLAY_BOOLEAN_FIELDS = (
    "legacy_false_completion",
    "verification_false_completion",
    "legacy_false_block",
    "verification_false_block",
    "safety_regression",
)
_REPLAY_TIME_FIELDS = (
    "legacy_time_to_accepted_ms",
    "verification_time_to_accepted_ms",
)


@dataclass(frozen=True)
class VerificationMetricsSummary:
    total_runs: int
    adjudicated_runs: int
    unreviewed_runs: int
    replay_scenarios_defined: int
    replay_scenarios: int
    real_candidates_completed: int
    legacy_false_completions: int
    false_completions: int
    false_blocks: int
    false_block_delta_percent: float | None
    legacy_correct_replays: int
    verification_correct_replays: int
    timing_comparable_replays: int
    replay_run_id: str | None
    replay_candidate_digest: str | None
    replay_candidate_matches_current: bool
    legacy_time_to_accepted_median_ms: float | None
    verification_time_to_accepted_median_ms: float | None
    verification_duration_median_ms: float | None
    correction_loops: int
    candidate_changed_during_run: int
    safety_regressions: int
    recommend_stage_2b: bool
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        return payload


def _timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _median(values: list[float]) -> float | None:
    finite = [item for item in values if math.isfinite(item) and item >= 0]
    return float(median(finite)) if finite else None


def _load_records(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], []
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"无法读取验证指标: {exc}"]
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            warnings.append(f"验证指标第 {index} 行损坏，已跳过")
            continue
        if not isinstance(payload, dict):
            warnings.append(f"验证指标第 {index} 行不是对象，已跳过")
            continue
        records.append(payload)
    return records, warnings


def _load_replay_contract(path: Path) -> tuple[dict[str, str] | None, list[str]]:
    if not path.exists():
        return None, ["回放合同不存在，已忽略场景定义与回放实测记录"]
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError:
        return None, ["无法读取回放合同，已忽略场景定义与回放实测记录"]
    except (UnicodeError, yaml.YAMLError):
        return None, ["回放合同损坏，已忽略场景定义与回放实测记录"]
    if not isinstance(payload, dict):
        return None, ["回放合同损坏：顶层必须是对象，已忽略场景定义与回放实测记录"]
    schema_version = payload.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        return None, ["回放合同损坏：schema_version 必须严格等于 1，已忽略场景定义与回放实测记录"]
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        return None, ["回放合同损坏：scenarios 必须是列表，已忽略场景定义与回放实测记录"]

    scenario_statuses: dict[str, str] = {}
    for index, scenario in enumerate(scenarios, start=1):
        if not isinstance(scenario, dict):
            return None, [f"回放合同损坏：第 {index} 个场景必须是对象，已忽略定义与实测记录"]
        raw_scenario_id = scenario.get("id")
        if not isinstance(raw_scenario_id, str) or not raw_scenario_id.strip():
            return None, [f"回放合同损坏：第 {index} 个场景缺少非空 id，已忽略定义与实测记录"]
        scenario_id = raw_scenario_id.strip()
        if scenario_id in scenario_statuses:
            return None, [f"回放合同损坏：场景 id {scenario_id} 重复，已忽略定义与实测记录"]
        expected_status = scenario.get("expected_status")
        if not isinstance(expected_status, str) or expected_status not in _REPLAY_EXPECTED_STATUSES:
            return None, [
                f"回放合同损坏：场景 {scenario_id} 的 expected_status 非法，已忽略定义与实测记录"
            ]
        scenario_statuses[scenario_id] = expected_status
    return scenario_statuses, []


def _valid_replay_time(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return bool(value >= 0)


def _derived_false_completion(status: str, expected_status: str) -> bool:
    return status == "PASS" and expected_status != "PASS"


def _derived_false_block(status: str, expected_status: str) -> bool:
    return expected_status == "PASS" and status != "PASS"


def _invalid_replay_fields(
    record: dict[str, Any],
    *,
    expected_status: str,
) -> tuple[str, ...]:
    invalid: list[str] = []
    if record.get("measurement_scope") != REPLAY_MEASUREMENT_SCOPE:
        invalid.append("measurement_scope")
    for field_name in ("replay_run_id", "candidate_digest"):
        value = record.get(field_name)
        if not isinstance(value, str) or not value.strip():
            invalid.append(field_name)

    statuses: dict[str, str] = {}
    for field_name in ("legacy_status", "verification_status"):
        value = record.get(field_name)
        if not isinstance(value, str) or value not in _REPLAY_EXPECTED_STATUSES:
            invalid.append(field_name)
            continue
        statuses[field_name] = value

    for field_name in _REPLAY_BOOLEAN_FIELDS:
        if field_name not in record or not isinstance(record[field_name], bool):
            invalid.append(field_name)

    derived_fields: tuple[tuple[str, str, Any], ...] = (
        (
            "legacy_false_completion",
            "legacy_status",
            _derived_false_completion,
        ),
        (
            "verification_false_completion",
            "verification_status",
            _derived_false_completion,
        ),
        ("legacy_false_block", "legacy_status", _derived_false_block),
        (
            "verification_false_block",
            "verification_status",
            _derived_false_block,
        ),
    )
    for boolean_field, status_field, derive in derived_fields:
        status = statuses.get(status_field)
        if status is None or not isinstance(record.get(boolean_field), bool):
            continue
        if record[boolean_field] is not derive(status, expected_status):
            invalid.append(f"{boolean_field}(与状态派生事实不一致)")

    for status_field, time_field in zip(
        ("legacy_status", "verification_status"),
        _REPLAY_TIME_FIELDS,
        strict=True,
    ):
        if time_field not in record:
            invalid.append(time_field)
            continue
        status = statuses.get(status_field)
        if status is None:
            continue
        value = record[time_field]
        if status == expected_status:
            if not _valid_replay_time(value):
                invalid.append(f"{time_field}(正确结论必须是有限非负数字)")
        elif value is not None:
            invalid.append(f"{time_field}(错误结论必须为 null)")
    return tuple(invalid)


def summarize_verification_metrics(
    path: Path | str,
    replay_contract_path: Path | str | None = None,
    current_candidate_digest: str | None = None,
) -> VerificationMetricsSummary:
    records, warnings = _load_records(Path(path))
    contract_path = Path(replay_contract_path) if replay_contract_path is not None else None
    contract_scenarios: dict[str, str] | None = None
    if contract_path is not None:
        contract_scenarios, contract_warnings = _load_replay_contract(contract_path)
        warnings.extend(contract_warnings)
    contract_scenario_ids = frozenset(contract_scenarios or ())
    runs: dict[str, dict[str, Any]] = {}
    adjudications: dict[str, dict[str, Any]] = {}
    registrations: dict[str, dict[str, Any]] = {}
    bindings: dict[str, str] = {}
    recorded_replays: dict[str, dict[str, Any]] = {}

    for record in records:
        record_type = str(record.get("record_type", ""))
        if record_type == "verification-run":
            run_id = str(record.get("run_id", ""))
            if run_id:
                runs[run_id] = record
        elif record_type == "verification-adjudication":
            run_id = str(record.get("run_id", ""))
            label = str(record.get("label", ""))
            if str(record.get("actor", "")) != "user" or label not in _ADJUDICATION_LABELS:
                warnings.append(f"运行 {run_id or '<missing>'} 的非用户或未知验收标签已忽略")
                continue
            if run_id:
                adjudications[run_id] = record
        elif record_type == "verification-candidate-registration":
            sample_id = str(record.get("sample_id", ""))
            if sample_id and str(record.get("acceptor", "")) == "user":
                registrations[sample_id] = record
        elif record_type == "verification-candidate-binding":
            sample_id = str(record.get("sample_id", ""))
            run_id = str(record.get("run_id", ""))
            if sample_id and run_id:
                bindings[sample_id] = run_id
        elif record_type == "verification-replay":
            raw_scenario_id = record.get("scenario_id")
            scenario_id = raw_scenario_id.strip() if isinstance(raw_scenario_id, str) else ""
            if scenario_id:
                recorded_replays[scenario_id] = record

    if contract_path is None:
        replays = recorded_replays
    elif contract_scenarios is None:
        replays = {}
    else:
        unknown_ids = sorted(set(recorded_replays) - contract_scenario_ids)
        if unknown_ids:
            warnings.append("合同外回放场景已忽略: " + ", ".join(unknown_ids))
        replays = {}
        for scenario_id, record in recorded_replays.items():
            if scenario_id not in contract_scenario_ids:
                continue
            invalid_fields = _invalid_replay_fields(
                record,
                expected_status=contract_scenarios[scenario_id],
            )
            if invalid_fields:
                warnings.append(
                    f"回放场景 {scenario_id} 的实测记录不完整或非法，已忽略: "
                    + ", ".join(invalid_fields)
                )
                continue
            replays[scenario_id] = record
        missing_ids = sorted(contract_scenario_ids - set(replays))
        if missing_ids:
            warnings.append(
                f"回放合同缺失 {len(missing_ids)} 条实测回放记录: " + ", ".join(missing_ids)
            )

    completed_run_ids: set[str] = set()
    for sample_id, run_id in bindings.items():
        registration = registrations.get(sample_id)
        run_record = runs.get(run_id)
        if registration is None or run_record is None or run_id not in adjudications:
            continue
        registered_at = _timestamp(registration.get("registered_at"))
        started_at = _timestamp(run_record.get("started_at"))
        if registered_at is not None and started_at is not None and registered_at < started_at:
            completed_run_ids.add(run_id)
    completed_real = len(completed_run_ids)

    legacy_false_completions = sum(
        1 for record in replays.values() if record.get("legacy_false_completion") is True
    )
    replay_verification_false_completions = sum(
        1
        for record in replays.values()
        if (
            record.get("verification_false_completion") is True
            or (
                "verification_false_completion" not in record
                and record.get("false_completion") is True
            )
        )
    )
    false_completions = (
        sum(1 for record in adjudications.values() if record.get("label") == "escaped_defect")
        + replay_verification_false_completions
    )
    false_blocks = sum(
        1 for record in adjudications.values() if record.get("label") == "false_block"
    ) + sum(1 for record in replays.values() if record.get("verification_false_block") is True)
    legacy_false_blocks = sum(
        1 for record in replays.values() if record.get("legacy_false_block") is True
    )
    replay_verification_false_blocks = sum(
        1 for record in replays.values() if record.get("verification_false_block") is True
    )
    if legacy_false_blocks == 0:
        false_block_delta = 0.0 if replay_verification_false_blocks == 0 else None
    else:
        false_block_delta = (
            (replay_verification_false_blocks - legacy_false_blocks) / legacy_false_blocks * 100.0
        )

    timing_pairs = [
        (
            float(record["legacy_time_to_accepted_ms"]),
            float(record["verification_time_to_accepted_ms"]),
        )
        for record in replays.values()
        if _valid_replay_time(record.get("legacy_time_to_accepted_ms"))
        and _valid_replay_time(record.get("verification_time_to_accepted_ms"))
    ]
    legacy_times = [legacy for legacy, _verification in timing_pairs]
    verification_times = [verification for _legacy, verification in timing_pairs]
    legacy_median = _median(legacy_times)
    verification_median = _median(verification_times)
    if contract_scenarios is None:
        legacy_correct_replays = 0
        verification_correct_replays = 0
    else:
        legacy_correct_replays = sum(
            1
            for scenario_id, record in replays.items()
            if record.get("legacy_status") == contract_scenarios[scenario_id]
        )
        verification_correct_replays = sum(
            1
            for scenario_id, record in replays.items()
            if record.get("verification_status") == contract_scenarios[scenario_id]
        )

    replay_run_ids = {
        str(record.get("replay_run_id", "")).strip()
        for record in replays.values()
        if str(record.get("replay_run_id", "")).strip()
    }
    replay_candidate_digests = {
        str(record.get("candidate_digest", "")).strip()
        for record in replays.values()
        if str(record.get("candidate_digest", "")).strip()
    }
    replay_run_id = next(iter(replay_run_ids)) if len(replay_run_ids) == 1 else None
    replay_candidate_digest = (
        next(iter(replay_candidate_digests)) if len(replay_candidate_digests) == 1 else None
    )
    if contract_path is not None and len(replay_run_ids) > 1:
        warnings.append("回放实测记录混用了多个 replay_run_id，阶段 2B 推荐已拒绝")
    if contract_path is not None and len(replay_candidate_digests) > 1:
        warnings.append("回放实测记录混用了多个 candidate_digest，阶段 2B 推荐已拒绝")
    normalized_current_digest = (
        current_candidate_digest.strip()
        if isinstance(current_candidate_digest, str) and current_candidate_digest.strip()
        else None
    )
    replay_candidate_matches_current = bool(
        replay_candidate_digest
        and normalized_current_digest
        and replay_candidate_digest == normalized_current_digest
    )
    if contract_path is not None and replays and normalized_current_digest is None:
        warnings.append("未提供当前代码版本摘要，阶段 2B 推荐已拒绝")
    elif (
        contract_path is not None
        and replay_candidate_digest is not None
        and normalized_current_digest is not None
        and not replay_candidate_matches_current
    ):
        warnings.append("回放代码版本摘要与当前代码版本不一致，阶段 2B 推荐已拒绝")
    verification_duration_median = _median(
        [
            float(record["verification_duration_ms"])
            for record in runs.values()
            if isinstance(record.get("verification_duration_ms"), int | float)
            and not isinstance(record.get("verification_duration_ms"), bool)
        ]
    )
    candidate_digests = {
        str(record.get("candidate_digest", ""))
        for record in runs.values()
        if str(record.get("candidate_digest", ""))
    }
    candidate_runs = sum(1 for record in runs.values() if record.get("candidate_digest"))
    correction_loops = max(0, candidate_runs - len(candidate_digests))
    candidate_changed = sum(
        1 for record in runs.values() if record.get("candidate_changed_during_run") is True
    )
    safety_regressions = sum(
        1 for record in adjudications.values() if record.get("safety_regression") is True
    ) + sum(1 for record in replays.values() if record.get("safety_regression") is True)
    replay_contract_complete = (
        contract_path is not None
        and contract_scenarios is not None
        and len(contract_scenario_ids) >= 10
        and set(replays) == set(contract_scenario_ids)
    )
    recommend = (
        replay_contract_complete
        and replay_run_id is not None
        and replay_candidate_digest is not None
        and replay_candidate_matches_current
        and verification_correct_replays == len(contract_scenario_ids)
        and len(timing_pairs) >= 1
        and completed_real >= 3
        and false_completions == 0
        and false_block_delta is not None
        and false_block_delta <= 10.0
        and legacy_median is not None
        and verification_median is not None
        and verification_median <= legacy_median
        and safety_regressions == 0
    )
    adjudicated_runs = len(set(runs) & set(adjudications))
    return VerificationMetricsSummary(
        total_runs=len(runs),
        adjudicated_runs=adjudicated_runs,
        unreviewed_runs=max(0, len(runs) - adjudicated_runs),
        replay_scenarios_defined=len(contract_scenario_ids),
        replay_scenarios=len(replays),
        real_candidates_completed=completed_real,
        legacy_false_completions=legacy_false_completions,
        false_completions=false_completions,
        false_blocks=false_blocks,
        false_block_delta_percent=false_block_delta,
        legacy_correct_replays=legacy_correct_replays,
        verification_correct_replays=verification_correct_replays,
        timing_comparable_replays=len(timing_pairs),
        replay_run_id=replay_run_id,
        replay_candidate_digest=replay_candidate_digest,
        replay_candidate_matches_current=replay_candidate_matches_current,
        legacy_time_to_accepted_median_ms=legacy_median,
        verification_time_to_accepted_median_ms=verification_median,
        verification_duration_median_ms=verification_duration_median,
        correction_loops=correction_loops,
        candidate_changed_during_run=candidate_changed,
        safety_regressions=safety_regressions,
        recommend_stage_2b=recommend,
        warnings=tuple(warnings),
    )
