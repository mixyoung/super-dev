"""Tests for PlanExecutor – plan creation, topological sorting, step transitions,
verify gates, codex review, failure handling, persistence, and report generation."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from super_dev.orchestrator.plan_executor import (
    ExecutionPlan,
    PlanExecutor,
    PlanStep,
    StepStatus,
    VerifyGate,
    _deserialize_datetime,
    _extract_json_object,
    _json_default,
    _serialize_datetime,
    _truncate_output,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def executor(temp_project_dir: Path) -> PlanExecutor:
    """Create a PlanExecutor pointing at a temporary project directory."""
    return PlanExecutor(project_dir=temp_project_dir)


def _make_step(
    step_id: str = "s1",
    label: str = "Step 1",
    description: str = "Do something",
    phase: str = "frontend",
    executor: str = "claude-code",
    depends_on: list[str] | None = None,
    verify_gates: list[VerifyGate] | None = None,
    failure_budget: int = 3,
) -> PlanStep:
    return PlanStep(
        id=step_id,
        label=label,
        description=description,
        phase=phase,
        executor=executor,
        depends_on=depends_on or [],
        verify_gates=verify_gates or [],
        failure_budget=failure_budget,
    )


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


class TestPlanExecutorInit:
    def test_creates_plans_directory(self, temp_project_dir: Path) -> None:
        executor = PlanExecutor(project_dir=temp_project_dir)
        assert executor.plans_dir.exists()
        assert executor.plans_dir == (temp_project_dir / ".super-dev" / "plans").resolve()

    def test_accepts_string_path(self, temp_project_dir: Path) -> None:
        executor = PlanExecutor(project_dir=str(temp_project_dir))
        assert executor.project_dir == temp_project_dir.resolve()

    def test_accepts_path_object(self, temp_project_dir: Path) -> None:
        executor = PlanExecutor(project_dir=temp_project_dir)
        assert executor.project_dir == temp_project_dir.resolve()


# ---------------------------------------------------------------------------
# PlanStep tests
# ---------------------------------------------------------------------------


class TestPlanStep:
    def test_default_status_is_pending(self) -> None:
        step = _make_step()
        assert step.status == StepStatus.PENDING

    def test_invalid_executor_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported executor"):
            PlanStep(
                id="s1",
                label="Bad",
                description="",
                phase="frontend",
                executor="invalid-executor",
            )

    def test_zero_failure_budget_raises(self) -> None:
        with pytest.raises(ValueError, match="failure_budget must be at least 1"):
            PlanStep(
                id="s1",
                label="Bad",
                description="",
                phase="frontend",
                failure_budget=0,
            )

    def test_to_dict_roundtrip(self) -> None:
        step = _make_step(
            step_id="s1",
            depends_on=["s0"],
            verify_gates=[VerifyGate(command="echo ok", gate="smoke", required=True, timeout_seconds=30)],
        )
        d = step.to_dict()
        assert d["id"] == "s1"
        assert d["depends_on"] == ["s0"]
        assert len(d["verify_gates"]) == 1
        assert d["verify_gates"][0]["gate"] == "smoke"
        assert d["status"] == "pending"


# ---------------------------------------------------------------------------
# StepStatus transition tests
# ---------------------------------------------------------------------------


class TestStepStatusTransitions:
    def test_pending_to_queued(self) -> None:
        assert StepStatus.PENDING.can_transition_to(StepStatus.QUEUED)

    def test_pending_to_blocked(self) -> None:
        assert StepStatus.PENDING.can_transition_to(StepStatus.BLOCKED)

    def test_pending_to_skipped(self) -> None:
        assert StepStatus.PENDING.can_transition_to(StepStatus.SKIPPED)

    def test_queued_to_running(self) -> None:
        assert StepStatus.QUEUED.can_transition_to(StepStatus.RUNNING)

    def test_running_to_completed(self) -> None:
        assert StepStatus.RUNNING.can_transition_to(StepStatus.COMPLETED)

    def test_running_to_failed(self) -> None:
        assert StepStatus.RUNNING.can_transition_to(StepStatus.FAILED)

    def test_running_to_verifying(self) -> None:
        assert StepStatus.RUNNING.can_transition_to(StepStatus.VERIFYING)

    def test_verifying_to_completed(self) -> None:
        assert StepStatus.VERIFYING.can_transition_to(StepStatus.COMPLETED)

    def test_verifying_to_failed(self) -> None:
        assert StepStatus.VERIFYING.can_transition_to(StepStatus.FAILED)

    def test_failed_to_queued(self) -> None:
        assert StepStatus.FAILED.can_transition_to(StepStatus.QUEUED)

    def test_completed_cannot_transition(self) -> None:
        assert StepStatus.COMPLETED.can_transition_to(StepStatus.RUNNING) is False

    def test_skipped_cannot_transition(self) -> None:
        assert StepStatus.SKIPPED.can_transition_to(StepStatus.RUNNING) is False

    def test_invalid_transition_pending_to_running(self) -> None:
        assert StepStatus.PENDING.can_transition_to(StepStatus.RUNNING) is False


# ---------------------------------------------------------------------------
# ExecutionPlan tests
# ---------------------------------------------------------------------------


class TestExecutionPlan:
    def test_get_step_found(self) -> None:
        step = _make_step(step_id="s1")
        plan = ExecutionPlan(plan_id="p1", phase="frontend", steps=[step])
        assert plan.get_step("s1") is step

    def test_get_step_not_found(self) -> None:
        plan = ExecutionPlan(plan_id="p1", phase="frontend", steps=[])
        assert plan.get_step("nonexistent") is None

    def test_progress_all_pending(self) -> None:
        steps = [_make_step(step_id=f"s{i}") for i in range(3)]
        plan = ExecutionPlan(plan_id="p1", phase="frontend", steps=steps)
        progress = plan.progress
        assert progress["total"] == 3
        assert progress["completed"] == 0
        assert progress["failed"] == 0

    def test_progress_mixed(self) -> None:
        s1 = _make_step(step_id="s1")
        s2 = _make_step(step_id="s2")
        s2.status = StepStatus.COMPLETED
        s3 = _make_step(step_id="s3")
        s3.status = StepStatus.FAILED
        plan = ExecutionPlan(plan_id="p1", phase="frontend", steps=[s1, s2, s3])
        progress = plan.progress
        assert progress["completed"] == 1
        assert progress["failed"] == 1
        assert progress["running"] == 0

    def test_all_completed_false(self) -> None:
        steps = [_make_step(step_id=f"s{i}") for i in range(2)]
        plan = ExecutionPlan(plan_id="p1", phase="frontend", steps=steps)
        assert plan.all_completed is False

    def test_all_completed_true(self) -> None:
        steps = [_make_step(step_id=f"s{i}") for i in range(2)]
        for s in steps:
            s.status = StepStatus.COMPLETED
        plan = ExecutionPlan(plan_id="p1", phase="frontend", steps=steps)
        assert plan.all_completed is True

    def test_all_completed_with_skipped(self) -> None:
        s1 = _make_step(step_id="s1")
        s1.status = StepStatus.COMPLETED
        s2 = _make_step(step_id="s2")
        s2.status = StepStatus.SKIPPED
        plan = ExecutionPlan(plan_id="p1", phase="frontend", steps=[s1, s2])
        assert plan.all_completed is True

    def test_to_dict(self) -> None:
        steps = [_make_step(step_id="s1")]
        plan = ExecutionPlan(
            plan_id="p1",
            phase="frontend",
            steps=steps,
            waves=[["s1"]],
            metadata={"key": "value"},
        )
        d = plan.to_dict()
        assert d["plan_id"] == "p1"
        assert d["phase"] == "frontend"
        assert len(d["steps"]) == 1
        assert d["waves"] == [["s1"]]
        assert d["metadata"] == {"key": "value"}


# ---------------------------------------------------------------------------
# Plan creation tests
# ---------------------------------------------------------------------------


class TestCreatePlan:
    def test_create_simple_plan(self, executor: PlanExecutor) -> None:
        steps = [_make_step(step_id="s1")]
        plan = executor.create_plan(phase="frontend", steps=steps)

        assert plan.phase == "frontend"
        assert len(plan.steps) == 1
        assert plan.steps[0].id == "s1"
        assert plan.waves == [["s1"]]

    def test_create_plan_with_dict_steps(self, executor: PlanExecutor) -> None:
        raw_steps: list[dict[str, Any]] = [
            {"id": "s1", "label": "Step 1", "description": "Do stuff"},
            {"id": "s2", "label": "Step 2", "description": "More stuff", "depends_on": ["s1"]},
        ]
        plan = executor.create_plan(phase="backend", steps=raw_steps)

        assert len(plan.steps) == 2
        assert plan.steps[1].depends_on == ["s1"]
        assert plan.waves == [["s1"], ["s2"]]

    def test_create_plan_with_metadata(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(
            phase="frontend",
            steps=[_make_step()],
            metadata={"priority": "high"},
        )
        assert plan.metadata == {"priority": "high"}

    def test_create_plan_saves_to_disk(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step()])

        plan_path = executor.plans_dir / f"{plan.plan_id}.json"
        assert plan_path.exists()
        data = json.loads(plan_path.read_text(encoding="utf-8"))
        assert data["plan_id"] == plan.plan_id
        assert len(data["steps"]) == 1

    def test_duplicate_step_ids_raises(self, executor: PlanExecutor) -> None:
        steps = [_make_step(step_id="s1"), _make_step(step_id="s1")]
        with pytest.raises(ValueError, match="Duplicate step ids"):
            executor.create_plan(phase="frontend", steps=steps)

    def test_unknown_dependency_raises(self, executor: PlanExecutor) -> None:
        steps = [
            _make_step(step_id="s1", depends_on=["nonexistent"]),
        ]
        with pytest.raises(ValueError, match="Unknown dependency"):
            executor.create_plan(phase="frontend", steps=steps)


# ---------------------------------------------------------------------------
# Topological sort tests
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    def test_single_step(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        assert plan.waves == [["s1"]]

    def test_independent_steps_single_wave(self, executor: PlanExecutor) -> None:
        steps = [_make_step(step_id=f"s{i}") for i in range(3)]
        plan = executor.create_plan(phase="frontend", steps=steps)
        assert len(plan.waves) == 1
        assert set(plan.waves[0]) == {"s0", "s1", "s2"}

    def test_linear_chain(self, executor: PlanExecutor) -> None:
        s1 = _make_step(step_id="s1")
        s2 = _make_step(step_id="s2", depends_on=["s1"])
        s3 = _make_step(step_id="s3", depends_on=["s2"])
        plan = executor.create_plan(phase="frontend", steps=[s1, s2, s3])

        assert plan.waves == [["s1"], ["s2"], ["s3"]]

    def test_diamond_dependency(self, executor: PlanExecutor) -> None:
        s1 = _make_step(step_id="s1")
        s2 = _make_step(step_id="s2", depends_on=["s1"])
        s3 = _make_step(step_id="s3", depends_on=["s1"])
        s4 = _make_step(step_id="s4", depends_on=["s2", "s3"])
        plan = executor.create_plan(phase="frontend", steps=[s1, s2, s3, s4])

        assert plan.waves[0] == ["s1"]
        assert set(plan.waves[1]) == {"s2", "s3"}
        assert plan.waves[2] == ["s4"]

    def test_cycle_raises(self, executor: PlanExecutor) -> None:
        # Can't easily create with PlanStep depends_on validation, so test directly
        s1 = _make_step(step_id="s1", depends_on=["s2"])
        s2 = _make_step(step_id="s2", depends_on=["s1"])
        with pytest.raises(ValueError, match="Cycle detected"):
            executor.create_plan(phase="frontend", steps=[s1, s2])


# ---------------------------------------------------------------------------
# Step transition tests
# ---------------------------------------------------------------------------


class TestTransitionStep:
    def test_valid_transition(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        step = plan.get_step("s1")

        # PENDING -> QUEUED
        assert executor.transition_step(plan, "s1", StepStatus.QUEUED) is True
        assert step.status == StepStatus.QUEUED

        # QUEUED -> RUNNING
        assert executor.transition_step(plan, "s1", StepStatus.RUNNING) is True
        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None

        # RUNNING -> COMPLETED
        assert executor.transition_step(plan, "s1", StepStatus.COMPLETED) is True
        assert step.status == StepStatus.COMPLETED
        assert step.completed_at is not None
        assert step.duration_seconds is not None

    def test_invalid_transition_returns_false(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])

        # PENDING -> RUNNING (invalid: must go through QUEUED first)
        assert executor.transition_step(plan, "s1", StepStatus.RUNNING) is False
        assert plan.get_step("s1").status == StepStatus.PENDING

    def test_unknown_step_returns_false(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        assert executor.transition_step(plan, "nonexistent", StepStatus.QUEUED) is False

    def test_running_sets_started_at(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        executor.transition_step(plan, "s1", StepStatus.QUEUED)
        executor.transition_step(plan, "s1", StepStatus.RUNNING)
        assert plan.get_step("s1").started_at is not None

    def test_completed_sets_duration(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        executor.transition_step(plan, "s1", StepStatus.QUEUED)
        executor.transition_step(plan, "s1", StepStatus.RUNNING)
        executor.transition_step(plan, "s1", StepStatus.COMPLETED)
        step = plan.get_step("s1")
        assert step.duration_seconds is not None
        assert step.duration_seconds >= 0

    def test_failure_then_requeue_resets_timestamps(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        executor.transition_step(plan, "s1", StepStatus.QUEUED)
        executor.transition_step(plan, "s1", StepStatus.RUNNING)

        step = plan.get_step("s1")
        executor.handle_step_failure(plan, step, "test error")

        # After failure + retry, timestamps should be cleared
        assert step.started_at is None
        assert step.completed_at is None
        assert step.duration_seconds is None

    def test_transition_persists_to_disk(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        executor.transition_step(plan, "s1", StepStatus.QUEUED)

        plan_path = executor.plans_dir / f"{plan.plan_id}.json"
        data = json.loads(plan_path.read_text(encoding="utf-8"))
        assert data["steps"][0]["status"] == "queued"


# ---------------------------------------------------------------------------
# get_next_ready_steps tests
# ---------------------------------------------------------------------------


class TestGetNextReadySteps:
    def test_no_deps_all_ready(self, executor: PlanExecutor) -> None:
        steps = [_make_step(step_id=f"s{i}") for i in range(3)]
        plan = executor.create_plan(phase="frontend", steps=steps)

        ready = executor.get_next_ready_steps(plan)
        assert len(ready) == 3

    def test_dependent_steps_only_ready_after_completion(self, executor: PlanExecutor) -> None:
        s1 = _make_step(step_id="s1")
        s2 = _make_step(step_id="s2", depends_on=["s1"])
        plan = executor.create_plan(phase="frontend", steps=[s1, s2])

        ready = executor.get_next_ready_steps(plan)
        assert len(ready) == 1
        assert ready[0].id == "s1"

        # Complete s1
        executor.transition_step(plan, "s1", StepStatus.QUEUED)
        executor.transition_step(plan, "s1", StepStatus.RUNNING)
        executor.transition_step(plan, "s1", StepStatus.COMPLETED)

        ready = executor.get_next_ready_steps(plan)
        assert len(ready) == 1
        assert ready[0].id == "s2"

    def test_completed_steps_not_ready(self, executor: PlanExecutor) -> None:
        s1 = _make_step(step_id="s1")
        plan = executor.create_plan(phase="frontend", steps=[s1])
        executor.transition_step(plan, "s1", StepStatus.QUEUED)
        executor.transition_step(plan, "s1", StepStatus.RUNNING)
        executor.transition_step(plan, "s1", StepStatus.COMPLETED)

        ready = executor.get_next_ready_steps(plan)
        assert len(ready) == 0

    def test_failed_dependency_blocks_dependent(self, executor: PlanExecutor) -> None:
        s1 = _make_step(step_id="s1")
        s2 = _make_step(step_id="s2", depends_on=["s1"])
        plan = executor.create_plan(phase="frontend", steps=[s1, s2])

        # Transition s1 to FAILED (need to go through states)
        executor.transition_step(plan, "s1", StepStatus.QUEUED)
        executor.transition_step(plan, "s1", StepStatus.RUNNING)
        executor.handle_step_failure(plan, plan.get_step("s1"), "error")

        # After failure with retry budget, s1 should be re-queued, not completed
        # so s2 should NOT be ready
        ready = executor.get_next_ready_steps(plan)
        ready_ids = [s.id for s in ready]
        assert "s2" not in ready_ids


# ---------------------------------------------------------------------------
# Verify gates tests
# ---------------------------------------------------------------------------


class TestVerifyGates:
    def test_successful_gate(self, executor: PlanExecutor) -> None:
        step = _make_step(
            step_id="s1",
            verify_gates=[VerifyGate(command="echo ok", gate="smoke", required=True)],
        )
        all_passed, results = executor.run_verify_gates(step)
        assert all_passed is True
        assert len(results) == 1
        assert results[0]["passed"] is True
        assert results[0]["gate"] == "smoke"

    def test_failing_required_gate(self, executor: PlanExecutor) -> None:
        step = _make_step(
            step_id="s1",
            verify_gates=[VerifyGate(command="exit 1", gate="lint", required=True)],
        )
        all_passed, results = executor.run_verify_gates(step)
        assert all_passed is False
        assert results[0]["passed"] is False

    def test_failing_optional_gate_still_passes(self, executor: PlanExecutor) -> None:
        step = _make_step(
            step_id="s1",
            verify_gates=[VerifyGate(command="exit 1", gate="style", required=False)],
        )
        all_passed, results = executor.run_verify_gates(step)
        assert all_passed is True
        assert results[0]["passed"] is False

    def test_multiple_gates_one_fails(self, executor: PlanExecutor) -> None:
        step = _make_step(
            step_id="s1",
            verify_gates=[
                VerifyGate(command="echo ok", gate="smoke", required=True),
                VerifyGate(command="exit 1", gate="lint", required=True),
            ],
        )
        all_passed, results = executor.run_verify_gates(step)
        assert all_passed is False
        assert len(results) == 2

    @patch("super_dev.orchestrator.plan_executor.subprocess.run")
    def test_timeout_expired(self, mock_run: MagicMock, executor: PlanExecutor) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep", timeout=1)
        step = _make_step(
            step_id="s1",
            verify_gates=[VerifyGate(command="sleep 10", gate="slow", required=True, timeout_seconds=1)],
        )
        all_passed, results = executor.run_verify_gates(step)
        assert all_passed is False
        assert "Timed out" in results[0]["error"]

    @patch("super_dev.orchestrator.plan_executor.subprocess.run")
    def test_os_error(self, mock_run: MagicMock, executor: PlanExecutor) -> None:
        mock_run.side_effect = OSError("Command not found")
        step = _make_step(
            step_id="s1",
            verify_gates=[VerifyGate(command="bad_cmd", gate="test", required=True)],
        )
        all_passed, results = executor.run_verify_gates(step)
        assert all_passed is False
        assert "Command not found" in results[0]["error"]


# ---------------------------------------------------------------------------
# Codex review tests
# ---------------------------------------------------------------------------


class TestCodexReview:
    @patch("super_dev.orchestrator.plan_executor.subprocess.run")
    def test_codex_cli_not_found(self, mock_run: MagicMock, executor: PlanExecutor) -> None:
        mock_run.side_effect = FileNotFoundError("codex not found")
        step = _make_step(step_id="s1")
        result = executor.request_codex_review(step, "some context")
        assert result["requested"] is True
        assert result["available"] is False
        assert result["passed"] is True

    @patch("super_dev.orchestrator.plan_executor.subprocess.run")
    def test_codex_timeout(self, mock_run: MagicMock, executor: PlanExecutor) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="codex", timeout=300)
        step = _make_step(step_id="s1")
        result = executor.request_codex_review(step, "some context")
        assert result["requested"] is True
        assert result["available"] is True
        assert "timed out" in result["error"]

    @patch("super_dev.orchestrator.plan_executor.subprocess.run")
    def test_codex_os_error(self, mock_run: MagicMock, executor: PlanExecutor) -> None:
        mock_run.side_effect = OSError("OS error")
        step = _make_step(step_id="s1")
        result = executor.request_codex_review(step, "context")
        assert result["error"] == "OS error"

    @patch("super_dev.orchestrator.plan_executor.subprocess.run")
    def test_codex_returns_valid_json(self, mock_run: MagicMock, executor: PlanExecutor) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"passed": true, "severity": "none", "issues": [], "summary": "OK"}',
            stderr="",
        )
        step = _make_step(step_id="s1")
        result = executor.request_codex_review(step, "context")
        assert result["passed"] is True
        assert result["severity"] == "none"
        assert "parsed" in result

    @patch("super_dev.orchestrator.plan_executor.subprocess.run")
    def test_codex_returns_non_json(self, mock_run: MagicMock, executor: PlanExecutor) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="This is not JSON",
            stderr="",
        )
        step = _make_step(step_id="s1")
        result = executor.request_codex_review(step, "context")
        # Falls back to exit code based pass
        assert result["passed"] is True
        assert result["severity"] == "unknown"


# ---------------------------------------------------------------------------
# Failure handling tests
# ---------------------------------------------------------------------------


class TestHandleStepFailure:
    def test_first_failure_retries(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1", failure_budget=3)])
        step = plan.get_step("s1")
        result = executor.handle_step_failure(plan, step, "test error")

        assert result == "retry"
        assert step.failure_count == 1
        assert step.status == StepStatus.QUEUED
        assert "test error" in step.errors

    def test_exhausted_budget_needs_human(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1", failure_budget=1)])
        step = plan.get_step("s1")
        result = executor.handle_step_failure(plan, step, "fatal error")

        assert result == "needs_human"
        assert step.failure_count == 1
        assert step.status == StepStatus.FAILED

    def test_failure_increments_count(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1", failure_budget=3)])
        step = plan.get_step("s1")

        executor.handle_step_failure(plan, step, "error 1")
        assert step.failure_count == 1

        executor.handle_step_failure(plan, step, "error 2")
        assert step.failure_count == 2

        executor.handle_step_failure(plan, step, "error 3")
        assert step.failure_count == 3
        assert step.status == StepStatus.FAILED

    def test_failure_persists_to_disk(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1", failure_budget=1)])
        step = plan.get_step("s1")
        executor.handle_step_failure(plan, step, "persist test")

        plan_path = executor.plans_dir / f"{plan.plan_id}.json"
        data = json.loads(plan_path.read_text(encoding="utf-8"))
        assert data["steps"][0]["failure_count"] == 1
        assert data["steps"][0]["status"] == "failed"


# ---------------------------------------------------------------------------
# Load & list plan tests
# ---------------------------------------------------------------------------


class TestLoadAndListPlans:
    def test_load_existing_plan(self, executor: PlanExecutor) -> None:
        original = executor.create_plan(
            phase="frontend",
            steps=[_make_step(step_id="s1")],
            metadata={"key": "val"},
        )
        loaded = executor.load_plan(original.plan_id)
        assert loaded is not None
        assert loaded.plan_id == original.plan_id
        assert loaded.phase == "frontend"
        assert len(loaded.steps) == 1

    def test_load_nonexistent_plan_returns_none(self, executor: PlanExecutor) -> None:
        assert executor.load_plan("nonexistent") is None

    def test_list_plans_empty(self, executor: PlanExecutor) -> None:
        plans = executor.list_plans()
        assert plans == []

    def test_list_plans_returns_created(self, executor: PlanExecutor) -> None:
        executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        executor.create_plan(phase="backend", steps=[_make_step(step_id="s1")])

        plans = executor.list_plans()
        assert len(plans) == 2
        phases = {p["phase"] for p in plans}
        assert phases == {"frontend", "backend"}

    @patch("super_dev.orchestrator.plan_executor.Path.read_text")
    def test_load_corrupted_json_returns_none(
        self, mock_read: MagicMock, executor: PlanExecutor
    ) -> None:
        # Create a plan first so the file exists
        plan = executor.create_plan(phase="frontend", steps=[_make_step()])
        # Now mock corrupted content
        mock_read.return_value = "not valid json {{{{"
        result = executor.load_plan(plan.plan_id)
        assert result is None


# ---------------------------------------------------------------------------
# Plan report tests
# ---------------------------------------------------------------------------


class TestPlanReport:
    def test_generate_report_contains_plan_id(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        report = executor.generate_plan_report(plan)
        assert plan.plan_id in report
        assert "frontend" in report

    def test_generate_report_shows_step_status(self, executor: PlanExecutor) -> None:
        plan = executor.create_plan(phase="frontend", steps=[_make_step(step_id="s1")])
        executor.transition_step(plan, "s1", StepStatus.QUEUED)
        executor.transition_step(plan, "s1", StepStatus.RUNNING)
        executor.transition_step(plan, "s1", StepStatus.COMPLETED)

        report = executor.generate_plan_report(plan)
        assert "completed" in report.lower()

    def test_generate_report_shows_waves(self, executor: PlanExecutor) -> None:
        s1 = _make_step(step_id="s1")
        s2 = _make_step(step_id="s2", depends_on=["s1"])
        plan = executor.create_plan(phase="frontend", steps=[s1, s2])

        report = executor.generate_plan_report(plan)
        assert "Wave 1" in report
        assert "Wave 2" in report


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------


class TestUtilityFunctions:
    def test_truncate_output_none(self) -> None:
        assert _truncate_output(None) == ""

    def test_truncate_output_string(self) -> None:
        assert _truncate_output("hello") == "hello"

    def test_truncate_output_bytes(self) -> None:
        assert _truncate_output(b"hello") == "hello"

    def test_truncate_output_long_string(self) -> None:
        long_str = "a" * 3000
        result = _truncate_output(long_str, limit=100)
        assert len(result) == 100

    def test_extract_json_object_valid(self) -> None:
        result = _extract_json_object('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_object_embedded(self) -> None:
        result = _extract_json_object('Some text {"key": "value"} more text')
        assert result == {"key": "value"}

    def test_extract_json_object_empty(self) -> None:
        assert _extract_json_object("") is None

    def test_extract_json_object_no_braces(self) -> None:
        assert _extract_json_object("no json here") is None

    def test_extract_json_object_returns_non_dict(self) -> None:
        # Array is not a dict
        assert _extract_json_object('[1, 2, 3]') is None

    def test_json_default_datetime(self) -> None:
        dt = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)
        result = _json_default(dt)
        assert "2026-04-11" in result

    def test_json_default_path(self) -> None:
        result = _json_default(Path("/tmp/test"))
        assert result == str(Path("/tmp/test"))

    def test_json_default_enum(self) -> None:
        result = _json_default(StepStatus.RUNNING)
        assert result == "running"

    def test_json_default_unsupported_raises(self) -> None:
        with pytest.raises(TypeError, match="not JSON serializable"):
            _json_default(set())

    def test_serialize_datetime_none(self) -> None:
        assert _serialize_datetime(None) is None

    def test_serialize_datetime_value(self) -> None:
        dt = datetime(2026, 4, 11, tzinfo=timezone.utc)
        result = _serialize_datetime(dt)
        assert "2026-04-11" in result

    def test_deserialize_datetime_none(self) -> None:
        assert _deserialize_datetime(None) is None

    def test_deserialize_datetime_string(self) -> None:
        result = _deserialize_datetime("2026-04-11T00:00:00+00:00")
        assert isinstance(result, datetime)
        assert result.year == 2026

    def test_deserialize_datetime_already_datetime(self) -> None:
        dt = datetime(2026, 4, 11, tzinfo=timezone.utc)
        result = _deserialize_datetime(dt)
        assert result is dt
