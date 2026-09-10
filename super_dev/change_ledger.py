"""Shadow-only nine-stage change ledger for the adaptive Super Dev Harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .stage_scope import KNOWN_CHANGE_SURFACES
from .work_mode import normalize_governance_depth, normalize_work_mode
from .workflow_contract import CANONICAL_NINE_STAGE_IDS, get_phase_kinds

ADAPTIVE_LEDGER_ENABLED_DEFAULT = False


class ChangeLedgerError(ValueError):
    """Raised when a ledger cannot satisfy the canonical Harness contract."""


class ChangeIntent(str, Enum):
    CHAT = "chat"
    EXPLAIN = "explain"
    QUICK_EDIT = "quick_edit"
    DEBUG = "debug"
    BUILD = "build"


class StageResolution(str, Enum):
    EXECUTE = "EXECUTE"
    REUSE = "REUSE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REQUIRE = "REQUIRE"
    WAIVE = "WAIVE"


class StageStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SATISFIED = "SATISFIED"
    BLOCKED = "BLOCKED"
    INVALIDATED = "INVALIDATED"


class ArtifactDepth(str, Enum):
    NONE = "none"
    PROBE = "probe"
    IN_CHAT = "in_chat"
    ARTIFACT = "artifact"
    FULL = "full"


def _legal_resolutions(kind: str) -> set[StageResolution]:
    if kind == "work":
        return {
            StageResolution.EXECUTE,
            StageResolution.REUSE,
            StageResolution.NOT_APPLICABLE,
        }
    if kind == "gate":
        return {
            StageResolution.REQUIRE,
            StageResolution.WAIVE,
            StageResolution.NOT_APPLICABLE,
        }
    if kind == "work_gate":
        return {StageResolution.EXECUTE, StageResolution.REUSE}
    return set()


@dataclass
class StageScopeRecommendation:
    stage: str
    kind: str
    recommended_resolution: StageResolution
    reason: str
    approval_required: bool = False

    def __post_init__(self) -> None:
        if self.recommended_resolution not in _legal_resolutions(self.kind):
            raise ChangeLedgerError(
                f"Recommended resolution {self.recommended_resolution.value} "
                f"is invalid for {self.kind} stage"
            )
        if not isinstance(self.approval_required, bool):
            raise ChangeLedgerError("approval_required must be a boolean")
        if (
            self.recommended_resolution
            in {
                StageResolution.REUSE,
                StageResolution.NOT_APPLICABLE,
                StageResolution.WAIVE,
            }
            and not self.approval_required
        ):
            raise ChangeLedgerError("Advisory reductions and reuse require approval")
        if not self.reason.strip():
            raise ChangeLedgerError("Scope recommendation reason is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "kind": self.kind,
            "recommended_resolution": self.recommended_resolution.value,
            "reason": self.reason,
            "approval_required": self.approval_required,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StageScopeRecommendation:
        try:
            return cls(
                stage=str(payload["stage"]),
                kind=str(payload["kind"]),
                recommended_resolution=StageResolution(str(payload["recommended_resolution"])),
                reason=str(payload["reason"]),
                approval_required=_strict_bool(payload["approval_required"], "approval_required"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ChangeLedgerError("Invalid stage scope recommendation payload") from exc


@dataclass
class ScopeAdvisory:
    generated_at: str
    scope_complete: bool
    changed_surfaces: list[str]
    recommendations: list[StageScopeRecommendation]
    source: str = "stage_scope_v1"
    control_authority: str = "none"

    def __post_init__(self) -> None:
        if self.source != "stage_scope_v1":
            raise ChangeLedgerError("Unsupported scope advisory source")
        if self.control_authority != "none":
            raise ChangeLedgerError("Scope advisory cannot have workflow control authority")
        if not isinstance(self.scope_complete, bool):
            raise ChangeLedgerError("scope_complete must be a boolean")
        if not self.generated_at.strip():
            raise ChangeLedgerError("Scope advisory generated_at is required")
        normalized_surfaces = sorted(
            {str(item).strip().lower() for item in self.changed_surfaces if str(item).strip()}
        )
        if self.changed_surfaces != normalized_surfaces:
            raise ChangeLedgerError("Scope advisory surfaces must be sorted and unique")
        unknown_surfaces = set(self.changed_surfaces) - KNOWN_CHANGE_SURFACES
        if unknown_surfaces:
            raise ChangeLedgerError(f"Unsupported advisory surfaces: {sorted(unknown_surfaces)}")
        stage_ids = tuple(item.stage for item in self.recommendations)
        if stage_ids != CANONICAL_NINE_STAGE_IDS:
            raise ChangeLedgerError(
                "Scope advisory recommendations must match the canonical nine-stage order"
            )
        expected_kinds = get_phase_kinds("standard")
        for item in self.recommendations:
            if item.kind != expected_kinds[item.stage]:
                raise ChangeLedgerError(f"Incorrect advisory kind for stage {item.stage}")
            if not self.scope_complete:
                expected = (
                    StageResolution.REQUIRE if item.kind == "gate" else StageResolution.EXECUTE
                )
                if item.recommended_resolution != expected:
                    raise ChangeLedgerError(
                        "Incomplete scope advisory must keep the conservative full plan"
                    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "generated_at": self.generated_at,
            "scope_complete": self.scope_complete,
            "changed_surfaces": list(self.changed_surfaces),
            "control_authority": self.control_authority,
            "recommendations": [item.to_dict() for item in self.recommendations],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ScopeAdvisory:
        try:
            changed_surfaces = payload["changed_surfaces"]
            recommendations = payload["recommendations"]
            if not isinstance(changed_surfaces, list):
                raise TypeError("changed_surfaces must be a list")
            if not isinstance(recommendations, list):
                raise TypeError("recommendations must be a list")
            return cls(
                source=str(payload["source"]),
                generated_at=str(payload["generated_at"]),
                scope_complete=_strict_bool(payload["scope_complete"], "scope_complete"),
                changed_surfaces=[str(item) for item in changed_surfaces],
                control_authority=str(payload["control_authority"]),
                recommendations=[
                    StageScopeRecommendation.from_dict(dict(item)) for item in recommendations
                ],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ChangeLedgerError("Invalid scope advisory object") from exc


@dataclass
class EvidenceReference:
    locator: str
    owner: str
    captured_at: str
    candidate_scope: str
    digest: str = ""
    expires_at: str = ""
    invalidation_triggers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "locator": self.locator,
            "owner": self.owner,
            "captured_at": self.captured_at,
            "candidate_scope": self.candidate_scope,
            "digest": self.digest,
            "expires_at": self.expires_at,
            "invalidation_triggers": list(self.invalidation_triggers),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EvidenceReference:
        return cls(
            locator=str(payload.get("locator", "")),
            owner=str(payload.get("owner", "")),
            captured_at=str(payload.get("captured_at", "")),
            candidate_scope=str(payload.get("candidate_scope", "")),
            digest=str(payload.get("digest", "")),
            expires_at=str(payload.get("expires_at", "")),
            invalidation_triggers=[str(item) for item in payload.get("invalidation_triggers", [])],
        )


@dataclass
class StageLedgerEntry:
    stage: str
    kind: str
    resolution: StageResolution
    status: StageStatus = StageStatus.PENDING
    depth: ArtifactDepth = ArtifactDepth.NONE
    reason: str = ""
    decided_by: str = ""
    evidence: list[EvidenceReference] = field(default_factory=list)
    invalidation_triggers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "kind": self.kind,
            "resolution": self.resolution.value,
            "status": self.status.value,
            "depth": self.depth.value,
            "reason": self.reason,
            "decided_by": self.decided_by,
            "evidence": [item.to_dict() for item in self.evidence],
            "invalidation_triggers": list(self.invalidation_triggers),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StageLedgerEntry:
        return cls(
            stage=str(payload["stage"]),
            kind=str(payload["kind"]),
            resolution=StageResolution(str(payload["resolution"])),
            status=StageStatus(str(payload.get("status", StageStatus.PENDING.value))),
            depth=ArtifactDepth(str(payload.get("depth", ArtifactDepth.NONE.value))),
            reason=str(payload.get("reason", "")),
            decided_by=str(payload.get("decided_by", "")),
            evidence=[
                EvidenceReference.from_dict(dict(item)) for item in payload.get("evidence", [])
            ],
            invalidation_triggers=[str(item) for item in payload.get("invalidation_triggers", [])],
        )


def should_create_change_ledger(intent: ChangeIntent | str) -> bool:
    normalized = intent if isinstance(intent, ChangeIntent) else ChangeIntent(str(intent))
    return normalized not in {ChangeIntent.CHAT, ChangeIntent.EXPLAIN}


@dataclass
class ChangeLedger:
    change_id: str
    harness_version: str
    intent: ChangeIntent
    governance_depth: str
    work_mode: str
    stages: list[StageLedgerEntry]
    schema_version: int = 1
    harness_id: str = "super-dev"
    shadow_only: bool = True
    scope_advisory: ScopeAdvisory | None = None

    def __post_init__(self) -> None:
        if not self.change_id.strip():
            raise ChangeLedgerError("change_id is required")
        if self.schema_version != 1:
            raise ChangeLedgerError("Unsupported change-ledger schema_version")
        if self.harness_id != "super-dev" or not self.harness_version.strip():
            raise ChangeLedgerError("Ledger must identify the active Super Dev Harness")
        if not should_create_change_ledger(self.intent):
            raise ChangeLedgerError("Chat and explain intents do not create a change ledger")
        if not self.shadow_only:
            raise ChangeLedgerError("The first-slice ledger must remain shadow-only")
        try:
            self.governance_depth = normalize_governance_depth(self.governance_depth)
        except ValueError as exc:
            raise ChangeLedgerError(str(exc)) from exc
        self.work_mode = normalize_work_mode(self.work_mode)
        self.validate_stage_roster()
        if self.scope_advisory is not None and not self.shadow_only:
            raise ChangeLedgerError("Scope advisory is only valid on a shadow ledger")

    @classmethod
    def create(
        cls,
        *,
        change_id: str,
        harness_version: str,
        intent: ChangeIntent | str,
        governance_depth: str,
        work_mode: str,
        shadow_only: bool = True,
    ) -> ChangeLedger:
        normalized_intent = (
            intent if isinstance(intent, ChangeIntent) else ChangeIntent(str(intent))
        )
        if not should_create_change_ledger(normalized_intent):
            raise ChangeLedgerError("Chat and explain intents do not create a change ledger")
        phase_kinds = get_phase_kinds("standard")
        stages = [
            StageLedgerEntry(
                stage=stage,
                kind=phase_kinds[stage],
                resolution=(
                    StageResolution.REQUIRE
                    if phase_kinds[stage] == "gate"
                    else StageResolution.EXECUTE
                ),
            )
            for stage in CANONICAL_NINE_STAGE_IDS
        ]
        return cls(
            change_id=change_id,
            harness_version=harness_version,
            intent=normalized_intent,
            governance_depth=governance_depth,
            work_mode=work_mode,
            stages=stages,
            shadow_only=shadow_only,
        )

    def validate_stage_roster(self) -> None:
        stage_ids = tuple(entry.stage for entry in self.stages)
        if stage_ids != CANONICAL_NINE_STAGE_IDS:
            raise ChangeLedgerError(
                "Ledger stages must match the canonical nine-stage order exactly"
            )
        if len(set(stage_ids)) != len(stage_ids):
            raise ChangeLedgerError("Ledger contains duplicate stage IDs")
        expected_kinds = get_phase_kinds("standard")
        for entry in self.stages:
            if entry.kind != expected_kinds[entry.stage]:
                raise ChangeLedgerError(f"Incorrect kind for stage {entry.stage}")
            legal = _legal_resolutions(entry.kind)
            if entry.resolution not in legal:
                raise ChangeLedgerError(
                    f"Resolution {entry.resolution.value} is invalid for {entry.kind} stage"
                )

    def get_stage(self, stage: str) -> StageLedgerEntry:
        for entry in self.stages:
            if entry.stage == stage:
                return entry
        raise KeyError(stage)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
            "change_id": self.change_id,
            "intent": self.intent.value,
            "governance_depth": self.governance_depth,
            "work_mode": self.work_mode,
            "shadow_only": self.shadow_only,
            "stages": [entry.to_dict() for entry in self.stages],
        }
        if self.scope_advisory is not None:
            payload["scope_advisory"] = self.scope_advisory.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ChangeLedger:
        try:
            intent = ChangeIntent(str(payload["intent"]))
        except (KeyError, ValueError) as exc:
            raise ChangeLedgerError("Unknown or missing intent") from exc
        try:
            stages = [StageLedgerEntry.from_dict(dict(item)) for item in payload["stages"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise ChangeLedgerError("Invalid stage payload") from exc
        advisory_payload = payload.get("scope_advisory")
        if advisory_payload is not None and not isinstance(advisory_payload, dict):
            raise ChangeLedgerError("scope_advisory must be an object")
        try:
            scope_advisory = (
                ScopeAdvisory.from_dict(advisory_payload)
                if isinstance(advisory_payload, dict)
                else None
            )
        except (ChangeLedgerError, KeyError, TypeError, ValueError) as exc:
            raise ChangeLedgerError("Invalid scope_advisory payload") from exc
        return cls(
            schema_version=int(payload.get("schema_version", 1)),
            harness_id=str(payload.get("harness_id", "super-dev")),
            harness_version=str(payload["harness_version"]),
            change_id=str(payload["change_id"]),
            intent=intent,
            governance_depth=str(payload["governance_depth"]),
            work_mode=str(payload["work_mode"]),
            shadow_only=_strict_bool(payload.get("shadow_only", True), "shadow_only"),
            stages=stages,
            scope_advisory=scope_advisory,
        )


def _strict_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ChangeLedgerError(f"{field_name} must be a boolean")
    return value


__all__ = [
    "ArtifactDepth",
    "ADAPTIVE_LEDGER_ENABLED_DEFAULT",
    "ChangeIntent",
    "ChangeLedger",
    "ChangeLedgerError",
    "EvidenceReference",
    "ScopeAdvisory",
    "StageLedgerEntry",
    "StageResolution",
    "StageScopeRecommendation",
    "StageStatus",
    "should_create_change_ledger",
]
