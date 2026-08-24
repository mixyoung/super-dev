"""最小扩展平台的数据合同。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from threading import Event
from typing import Any


class ExtensionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Capability(str, Enum):
    READ_FILES = "read_files"
    RUN_COMMANDS = "run_commands"
    WRITE_EVIDENCE = "write_evidence"


class ExtensionEventType(str, Enum):
    REQUESTED = "ExtensionRequested"
    STARTED = "ExtensionStarted"
    COMPLETED = "ExtensionCompleted"
    BLOCKED = "ExtensionBlocked"
    EVIDENCE_INVALIDATED = "ExtensionEvidenceInvalidated"


@dataclass(frozen=True)
class SourceSpec:
    kind: str
    path: str
    content_digest: str
    upstream_repository: str = ""
    upstream_commit: str = ""
    upstream_path: str = ""
    upstream_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value != ""}


@dataclass(frozen=True)
class TriggerSpec:
    mode: str
    allowed_stages: tuple[str, ...]


@dataclass(frozen=True)
class OwnershipSpec:
    lifecycle: bool
    orchestration: bool
    production_writer: bool
    placement: bool
    may_spawn_subworkers: bool


@dataclass(frozen=True)
class WriteSpec:
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]


@dataclass(frozen=True)
class AuthoritySpec:
    commit: bool
    merge: bool
    push: bool
    pull_request: bool
    deploy: bool
    external_write: bool
    global_install: bool


@dataclass(frozen=True)
class ExecutionSpec:
    executor: str
    entrypoint: str
    timeout_seconds: int


@dataclass(frozen=True)
class ExtensionManifest:
    schema_version: int
    id: str
    version: str
    kind: str
    source: SourceSpec
    trigger: TriggerSpec
    required_capabilities: tuple[Capability, ...]
    ownership: OwnershipSpec
    writes: WriteSpec
    authority: AuthoritySpec
    execution: ExecutionSpec
    result_schema: str
    manifest_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "id": self.id,
            "version": self.version,
            "kind": self.kind,
            "source": self.source.to_dict(),
            "trigger": {
                "mode": self.trigger.mode,
                "allowed_stages": list(self.trigger.allowed_stages),
            },
            "capabilities": {
                "required": [item.value for item in self.required_capabilities]
            },
            "ownership": asdict(self.ownership),
            "writes": {
                "allowed": list(self.writes.allowed),
                "forbidden": list(self.writes.forbidden),
            },
            "authority": asdict(self.authority),
            "execution": asdict(self.execution),
            "result": {"schema": self.result_schema},
        }
        if self.manifest_path is not None:
            payload["manifest_path"] = str(self.manifest_path)
        return payload


@dataclass(frozen=True)
class CandidateIdentity:
    repository: str
    base_sha: str
    head_sha: str
    dirty_diff_digest: str
    staged_digest: str
    untracked_manifest_digest: str
    worktree_identity: str
    candidate_digest: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CommandSpec:
    executable: Path
    args: tuple[str, ...] = ()
    cwd: Path | None = None
    timeout_seconds: int = 30
    env_allowlist: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    output_limit_bytes: int = 64 * 1024
    cancel_event: Event | None = None


@dataclass(frozen=True)
class CommandExecution:
    status: ExtensionStatus
    executable: str
    args: tuple[str, ...]
    cwd: str
    exit_code: int | None
    stdout: str
    stderr: str
    stdout_digest: str
    stderr_digest: str
    started_at: str
    finished_at: str
    duration_ms: float
    timed_out: bool
    cancelled: bool
    process_tree_clean: bool
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["args"] = list(self.args)
        return payload


@dataclass(frozen=True)
class ExtensionEvent:
    schema_version: int
    event: ExtensionEventType
    run_id: str
    extension_id: str
    canonical_stage: str
    actor: str
    timestamp: str
    source_digest: str = ""
    candidate_digest: str = ""
    result_artifact: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event"] = self.event.value
        return payload


@dataclass
class ExtensionResult:
    schema_version: int
    run_id: str
    extension_id: str
    extension_version: str
    status: ExtensionStatus
    canonical_stage: str
    source_digest: str
    candidate: CandidateIdentity
    commands: list[CommandExecution] = field(default_factory=list)
    writes: list[str] = field(default_factory=list)
    blocking_findings: list[str] = field(default_factory=list)
    advisory_findings: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float = 0.0
    process_tree_clean: bool = True
    next_action: str = "return-control-to-super-dev"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "extension_id": self.extension_id,
            "extension_version": self.extension_version,
            "status": self.status.value,
            "canonical_stage": self.canonical_stage,
            "source_digest": self.source_digest,
            "candidate": self.candidate.to_dict(),
            "commands": [item.to_dict() for item in self.commands],
            "writes": list(self.writes),
            "blocking_findings": list(self.blocking_findings),
            "advisory_findings": list(self.advisory_findings),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "process_tree_clean": self.process_tree_clean,
            "next_action": self.next_action,
        }
