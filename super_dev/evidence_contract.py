"""Shared candidate-bound evidence contract for Super Dev 2.6.

Requirement traceability: EVIDENCE-001 defines the unified evidence envelope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceValidationError(ValueError):
    """Raised when evidence is too incomplete to support its claimed status."""


class EvidenceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class EvidenceArtifact:
    path: str
    digest: str = ""
    media_type: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "digest": self.digest,
            "media_type": self.media_type,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EvidenceArtifact:
        return cls(
            path=str(payload.get("path", "")).strip(),
            digest=str(payload.get("digest", "")).strip(),
            media_type=str(payload.get("media_type", "")).strip(),
        )


@dataclass(frozen=True)
class EvidenceEnvelope:
    schema_version: int
    evidence_id: str
    evidence_type: str
    subject_type: str
    subject_digest: str
    work_item_id: str
    candidate_digest: str
    producer: str
    run_id: str
    status: EvidenceStatus
    observed_at: str
    started_at: str = ""
    finished_at: str = ""
    operation: tuple[str, ...] = ()
    environment: dict[str, str] = field(default_factory=dict)
    artifacts: tuple[EvidenceArtifact, ...] = ()
    invalidation_triggers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        required = {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "subject_type": self.subject_type,
            "subject_digest": self.subject_digest,
            "producer": self.producer,
            "run_id": self.run_id,
            "observed_at": self.observed_at,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise EvidenceValidationError("missing evidence fields: " + ", ".join(missing))
        if self.schema_version < 1:
            raise EvidenceValidationError("schema_version must be positive")
        if self.status is EvidenceStatus.PASS:
            if not self.work_item_id.strip():
                raise EvidenceValidationError("PASS evidence requires work_item_id")
            if not self.candidate_digest.strip():
                raise EvidenceValidationError("PASS evidence requires candidate_digest")

    def matches_candidate(self, *, work_item_id: str, candidate_digest: str) -> bool:
        return (
            self.work_item_id == str(work_item_id).strip()
            and self.candidate_digest == str(candidate_digest).strip()
            and bool(self.candidate_digest)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "subject": {
                "type": self.subject_type,
                "digest": self.subject_digest,
            },
            "work_item_id": self.work_item_id,
            "candidate_digest": self.candidate_digest,
            "producer": self.producer,
            "run_id": self.run_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "observed_at": self.observed_at,
            "operation": list(self.operation),
            "environment": dict(self.environment),
            "artifacts": [item.to_dict() for item in self.artifacts],
            "invalidation_triggers": list(self.invalidation_triggers),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EvidenceEnvelope:
        subject = payload.get("subject", {})
        if not isinstance(subject, dict):
            subject = {}
        raw_artifacts = payload.get("artifacts", [])
        artifacts = (
            tuple(
                EvidenceArtifact.from_dict(item) for item in raw_artifacts if isinstance(item, dict)
            )
            if isinstance(raw_artifacts, list | tuple)
            else ()
        )
        raw_operation = payload.get("operation", ())
        operation = (
            tuple(str(item) for item in raw_operation)
            if isinstance(raw_operation, list | tuple)
            else ((str(raw_operation),) if str(raw_operation).strip() else ())
        )
        raw_environment = payload.get("environment", {})
        environment = (
            {str(key): str(value) for key, value in raw_environment.items()}
            if isinstance(raw_environment, dict)
            else {}
        )
        raw_triggers = payload.get("invalidation_triggers", ())
        triggers = (
            tuple(str(item) for item in raw_triggers)
            if isinstance(raw_triggers, list | tuple)
            else ()
        )
        try:
            status = EvidenceStatus(str(payload.get("status", "")))
        except ValueError as exc:
            raise EvidenceValidationError("unknown evidence status") from exc
        return cls(
            schema_version=int(payload.get("schema_version", 1) or 1),
            evidence_id=str(payload.get("evidence_id", "")).strip(),
            evidence_type=str(payload.get("evidence_type", "")).strip(),
            subject_type=str(subject.get("type", "")).strip(),
            subject_digest=str(subject.get("digest", "")).strip(),
            work_item_id=str(payload.get("work_item_id", "")).strip(),
            candidate_digest=str(payload.get("candidate_digest", "")).strip(),
            producer=str(payload.get("producer", "")).strip(),
            run_id=str(payload.get("run_id", "")).strip(),
            status=status,
            started_at=str(payload.get("started_at", "")).strip(),
            finished_at=str(payload.get("finished_at", "")).strip(),
            observed_at=str(payload.get("observed_at", "")).strip(),
            operation=operation,
            environment=environment,
            artifacts=artifacts,
            invalidation_triggers=triggers,
        )


__all__ = [
    "EvidenceArtifact",
    "EvidenceEnvelope",
    "EvidenceStatus",
    "EvidenceValidationError",
]
