from __future__ import annotations

import pytest

from super_dev.agent_contract import (
    AgentAssignment,
    AgentContractError,
    AgentLevel,
    validate_child_assignment,
)


def _root() -> AgentAssignment:
    return AgentAssignment(
        task_id="root-task",
        agent_level=AgentLevel.ROOT,
        role="lifecycle-owner",
        workspace="E:/repo",
        write_scope=("**",),
        forbidden_actions=("push",),
        placement_owner="root-task",
        result_owner="user",
        may_delegate=True,
        may_advance_stage=True,
        may_approve_skip=True,
        may_approve_waiver=True,
    )


def test_child_assignment_must_narrow_authority() -> None:
    parent = _root()
    child = AgentAssignment(
        task_id="writer-1",
        parent_task_id=parent.task_id,
        agent_level=AgentLevel.WRITER,
        role="backend-writer",
        workspace="E:/repo-worktree",
        write_scope=("super_dev/change_ledger.py",),
        forbidden_actions=("push", "advance-stage"),
        placement_owner="root-task",
        result_owner="root-task",
        acceptance=("targeted tests pass",),
    )

    validate_child_assignment(parent, child)


def test_reviewer_is_always_read_only() -> None:
    with pytest.raises(AgentContractError, match="production write scope"):
        AgentAssignment(
            task_id="review-1",
            parent_task_id="root-task",
            agent_level=AgentLevel.REVIEWER,
            role="reviewer",
            workspace="E:/repo",
            write_scope=("super_dev/**",),
            placement_owner="root-task",
            result_owner="root-task",
            read_only=True,
        )


def test_writer_cannot_approve_its_own_skip() -> None:
    with pytest.raises(AgentContractError, match="cannot advance, approve, or integrate"):
        AgentAssignment(
            task_id="writer-1",
            parent_task_id="root-task",
            agent_level=AgentLevel.WRITER,
            role="writer",
            workspace="E:/repo",
            placement_owner="root-task",
            result_owner="root-task",
            may_approve_skip=True,
        )


def test_parent_without_delegation_cannot_create_child() -> None:
    parent = AgentAssignment(
        task_id="coordinator",
        parent_task_id="root-task",
        agent_level=AgentLevel.COORDINATOR,
        role="coordinator",
        workspace="E:/repo",
        write_scope=("super_dev/**",),
        forbidden_actions=("push",),
        placement_owner="root-task",
        result_owner="root-task",
    )
    child = AgentAssignment(
        task_id="writer",
        parent_task_id=parent.task_id,
        agent_level=AgentLevel.WRITER,
        role="writer",
        workspace="E:/repo",
        write_scope=("super_dev/**",),
        forbidden_actions=("push",),
        placement_owner="root-task",
        result_owner=parent.task_id,
    )

    with pytest.raises(AgentContractError, match="not allowed to delegate"):
        validate_child_assignment(parent, child)


def test_reviewer_cannot_delegate() -> None:
    with pytest.raises(AgentContractError, match="cannot delegate"):
        AgentAssignment(
            task_id="review-1",
            parent_task_id="root-task",
            agent_level=AgentLevel.REVIEWER,
            role="reviewer",
            workspace="E:/repo",
            placement_owner="root-task",
            result_owner="root-task",
            read_only=True,
            may_delegate=True,
        )


def test_glob_scope_and_windows_separators_are_normalized() -> None:
    parent = AgentAssignment(
        task_id="coord",
        parent_task_id="root",
        agent_level=AgentLevel.COORDINATOR,
        role="coordinator",
        workspace="E:/repo",
        write_scope=("super_dev/**",),
        forbidden_actions=("push",),
        placement_owner="root",
        result_owner="root",
        may_delegate=True,
    )
    child = AgentAssignment(
        task_id="writer",
        parent_task_id="coord",
        agent_level=AgentLevel.WRITER,
        role="writer",
        workspace="E:/repo",
        write_scope=("super_dev\\change_ledger.py",),
        forbidden_actions=("push",),
        placement_owner="root",
        result_owner="coord",
    )

    validate_child_assignment(parent, child)


def test_writer_cannot_delegate_upward_to_a_coordinator() -> None:
    parent = AgentAssignment(
        task_id="writer",
        parent_task_id="coord",
        agent_level=AgentLevel.WRITER,
        role="writer",
        workspace="E:/repo",
        write_scope=("super_dev/**",),
        forbidden_actions=("push",),
        placement_owner="coord",
        result_owner="coord",
        may_delegate=True,
    )
    child = AgentAssignment(
        task_id="nested-coordinator",
        parent_task_id="writer",
        agent_level=AgentLevel.COORDINATOR,
        role="coordinator",
        workspace="E:/repo",
        write_scope=("super_dev/**",),
        forbidden_actions=("push",),
        placement_owner="coord",
        result_owner="writer",
    )

    with pytest.raises(AgentContractError, match="cannot move upward"):
        validate_child_assignment(parent, child)


def test_assignment_boolean_strings_are_rejected() -> None:
    payload = _root().to_dict()
    payload["may_delegate"] = "false"

    with pytest.raises(AgentContractError, match="must be a boolean"):
        AgentAssignment.from_dict(payload)


def test_child_cannot_remove_inherited_forbidden_actions() -> None:
    parent = _root()
    child = AgentAssignment(
        task_id="writer",
        parent_task_id=parent.task_id,
        agent_level=AgentLevel.WRITER,
        role="writer",
        workspace="E:/repo",
        write_scope=("super_dev/change_ledger.py",),
        forbidden_actions=(),
        placement_owner=parent.task_id,
        result_owner=parent.task_id,
    )

    with pytest.raises(AgentContractError, match="removed an inherited"):
        validate_child_assignment(parent, child)
