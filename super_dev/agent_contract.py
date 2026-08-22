"""Role-aware assignments shared by every Super Dev agent level."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatchcase
from typing import Any


class AgentContractError(ValueError):
    """Raised when an assignment violates the Harness authority hierarchy."""


class AgentLevel(str, Enum):
    ROOT = "root"
    COORDINATOR = "coordinator"
    WRITER = "writer"
    REVIEWER = "reviewer"


_LEVEL_RANK = {
    AgentLevel.ROOT: 0,
    AgentLevel.COORDINATOR: 1,
    AgentLevel.WRITER: 2,
    AgentLevel.REVIEWER: 2,
}


@dataclass(frozen=True)
class AgentAssignment:
    task_id: str
    agent_level: AgentLevel
    role: str
    workspace: str
    placement_owner: str
    result_owner: str
    parent_task_id: str | None = None
    write_scope: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    may_delegate: bool = False
    may_advance_stage: bool = False
    may_approve_skip: bool = False
    may_approve_waiver: bool = False
    may_integrate: bool = False
    read_only: bool = False
    acceptance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        required = {
            "task_id": self.task_id,
            "role": self.role,
            "workspace": self.workspace,
            "placement_owner": self.placement_owner,
            "result_owner": self.result_owner,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise AgentContractError("Missing assignment fields: " + ", ".join(missing))

        if self.agent_level == AgentLevel.ROOT and self.parent_task_id:
            raise AgentContractError("A root assignment cannot have a parent task")
        if self.agent_level != AgentLevel.ROOT and not str(self.parent_task_id or "").strip():
            raise AgentContractError("A non-root assignment requires parent_task_id")

        if self.agent_level in {AgentLevel.WRITER, AgentLevel.REVIEWER}:
            if (
                self.may_advance_stage
                or self.may_approve_skip
                or self.may_approve_waiver
                or self.may_integrate
            ):
                raise AgentContractError(
                    "Writer and reviewer assignments cannot advance, approve, or integrate"
                )
        if self.agent_level == AgentLevel.REVIEWER:
            if not self.read_only:
                raise AgentContractError("Reviewer assignments must be read-only")
            if self.may_delegate:
                raise AgentContractError("Reviewer assignments cannot delegate")
            if self.write_scope:
                raise AgentContractError("Reviewer assignments cannot have a production write scope")
        if self.read_only and self.write_scope:
            raise AgentContractError("Read-only assignments cannot have a write scope")

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "agent_level": self.agent_level.value,
            "role": self.role,
            "workspace": self.workspace,
            "write_scope": list(self.write_scope),
            "forbidden_actions": list(self.forbidden_actions),
            "placement_owner": self.placement_owner,
            "result_owner": self.result_owner,
            "may_delegate": self.may_delegate,
            "may_advance_stage": self.may_advance_stage,
            "may_approve_skip": self.may_approve_skip,
            "may_approve_waiver": self.may_approve_waiver,
            "may_integrate": self.may_integrate,
            "read_only": self.read_only,
            "acceptance": list(self.acceptance),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AgentAssignment:
        try:
            agent_level = AgentLevel(str(payload["agent_level"]))
        except (KeyError, ValueError) as exc:
            raise AgentContractError("Unknown or missing agent_level") from exc
        return cls(
            task_id=str(payload["task_id"]),
            parent_task_id=(
                str(payload["parent_task_id"])
                if payload.get("parent_task_id") is not None
                else None
            ),
            agent_level=agent_level,
            role=str(payload["role"]),
            workspace=str(payload["workspace"]),
            write_scope=tuple(str(item) for item in payload.get("write_scope", [])),
            forbidden_actions=tuple(
                str(item) for item in payload.get("forbidden_actions", [])
            ),
            placement_owner=str(payload["placement_owner"]),
            result_owner=str(payload["result_owner"]),
            may_delegate=_strict_bool(payload.get("may_delegate", False), "may_delegate"),
            may_advance_stage=_strict_bool(
                payload.get("may_advance_stage", False), "may_advance_stage"
            ),
            may_approve_skip=_strict_bool(
                payload.get("may_approve_skip", False), "may_approve_skip"
            ),
            may_approve_waiver=_strict_bool(
                payload.get("may_approve_waiver", False), "may_approve_waiver"
            ),
            may_integrate=_strict_bool(payload.get("may_integrate", False), "may_integrate"),
            read_only=_strict_bool(payload.get("read_only", False), "read_only"),
            acceptance=tuple(str(item) for item in payload.get("acceptance", [])),
        )


def _strict_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise AgentContractError(f"{field_name} must be a boolean")
    return value


def _normalize_scope(value: str) -> str:
    normalized = str(value).strip().replace("\\", "/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.removeprefix("./")


def _scope_is_narrower(parent_scope: tuple[str, ...], child_scope: tuple[str, ...]) -> bool:
    parent_patterns = tuple(_normalize_scope(item) for item in parent_scope)
    if "**" in parent_patterns:
        return True
    for raw_child in child_scope:
        child = _normalize_scope(raw_child)
        if child == "**":
            return False
        if any(marker in child for marker in ("*", "?", "[")):
            if child not in parent_patterns:
                return False
            continue
        if not any(fnmatchcase(child, pattern) for pattern in parent_patterns):
            return False
    return True


def validate_child_assignment(parent: AgentAssignment, child: AgentAssignment) -> None:
    """Reject a child assignment that broadens inherited authority."""

    if child.parent_task_id != parent.task_id:
        raise AgentContractError("Child parent_task_id does not match the parent task")
    if not parent.may_delegate:
        raise AgentContractError("Parent assignment is not allowed to delegate")
    if _LEVEL_RANK[child.agent_level] < _LEVEL_RANK[parent.agent_level]:
        raise AgentContractError("Child assignment cannot move upward in the agent hierarchy")
    if child.workspace != parent.workspace and child.placement_owner != parent.task_id:
        raise AgentContractError("Only the parent placement owner can assign another workspace")
    if not _scope_is_narrower(parent.write_scope, child.write_scope):
        raise AgentContractError("Child write scope exceeds the parent write scope")
    if not set(parent.forbidden_actions).issubset(set(child.forbidden_actions)):
        raise AgentContractError("Child assignment removed an inherited forbidden action")

    inherited_flags = (
        ("may_delegate", parent.may_delegate, child.may_delegate),
        ("may_advance_stage", parent.may_advance_stage, child.may_advance_stage),
        ("may_approve_skip", parent.may_approve_skip, child.may_approve_skip),
        ("may_approve_waiver", parent.may_approve_waiver, child.may_approve_waiver),
        ("may_integrate", parent.may_integrate, child.may_integrate),
    )
    broadened = [name for name, allowed, requested in inherited_flags if requested and not allowed]
    if broadened:
        raise AgentContractError("Child authority exceeds parent: " + ", ".join(broadened))


__all__ = [
    "AgentAssignment",
    "AgentContractError",
    "AgentLevel",
    "validate_child_assignment",
]
