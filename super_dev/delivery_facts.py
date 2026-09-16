"""Independent post-delivery facts and source-bound operational outcomes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class DeliveryFactStatus(str, Enum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    PENDING = "pending"
    REFUTED = "refuted"


def resolve_project_target_version(project_dir: Path, *, configured_version: str = "") -> str:
    """Resolve the reviewed project's version, never the Super Dev package version."""

    root = Path(project_dir).resolve()
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(encoding="utf-8")
        except OSError:
            content = ""
        project_section = re.search(r"(?ms)^\[project\]\s*(.*?)(?=^\[[^]]+\]|\Z)", content)
        if project_section:
            match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', project_section.group(1))
            if match:
                return match.group(1).strip()

    package_json = root / "package.json"
    if package_json.is_file():
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            version = str(payload.get("version", "")).strip()
            if version:
                return version

    cargo = root / "Cargo.toml"
    if cargo.is_file():
        try:
            content = cargo.read_text(encoding="utf-8")
        except OSError:
            content = ""
        package_section = re.search(r"(?ms)^\[package\]\s*(.*?)(?=^\[[^]]+\]|\Z)", content)
        if package_section:
            match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', package_section.group(1))
            if match:
                return match.group(1).strip()

    return str(configured_version).strip()


@dataclass(frozen=True)
class DeliveryFact:
    status: DeliveryFactStatus = DeliveryFactStatus.UNKNOWN
    evidence: tuple[str, ...] = ()
    source: str = ""
    observed_at: str = ""
    target_version: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DeliveryFact:
        raw_status = str(payload.get("status", "unknown")).strip().lower()
        try:
            status = DeliveryFactStatus(raw_status)
        except ValueError:
            status = DeliveryFactStatus.UNKNOWN
        raw_evidence = payload.get("evidence", ())
        evidence = (
            tuple(str(item) for item in raw_evidence if str(item).strip())
            if isinstance(raw_evidence, list | tuple)
            else ()
        )
        source = str(payload.get("source", "")).strip()
        observed_at = str(payload.get("observed_at", "")).strip()
        target_version = str(payload.get("target_version", "")).strip()
        if status is DeliveryFactStatus.VERIFIED and not all(
            (evidence, source, observed_at, target_version)
        ):
            status = DeliveryFactStatus.PENDING
        return cls(
            status=status,
            evidence=evidence,
            source=source,
            observed_at=observed_at,
            target_version=target_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "evidence": list(self.evidence),
            "source": self.source,
            "observed_at": self.observed_at,
            "target_version": self.target_version,
        }


@dataclass(frozen=True)
class DeliveryFacts:
    delivery_ready: DeliveryFact = field(default_factory=DeliveryFact)
    released: DeliveryFact = field(default_factory=DeliveryFact)
    deployed: DeliveryFact = field(default_factory=DeliveryFact)
    operating: DeliveryFact = field(default_factory=DeliveryFact)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DeliveryFacts:
        def fact(name: str) -> DeliveryFact:
            value = payload.get(name, {})
            return DeliveryFact.from_dict(value) if isinstance(value, dict) else DeliveryFact()

        return cls(
            delivery_ready=fact("delivery_ready"),
            released=fact("released"),
            deployed=fact("deployed"),
            operating=fact("operating"),
        )

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {
            "delivery_ready": self.delivery_ready.to_dict(),
            "released": self.released.to_dict(),
            "deployed": self.deployed.to_dict(),
            "operating": self.operating.to_dict(),
        }


def _fact_from_observation(
    observed: bool | None,
    *,
    evidence: tuple[str, ...],
    source: str,
    observed_at: str,
    target_version: str,
) -> DeliveryFact:
    if observed is None:
        status = DeliveryFactStatus.UNKNOWN
    elif observed:
        status = (
            DeliveryFactStatus.VERIFIED
            if all((evidence, source, observed_at, target_version))
            else DeliveryFactStatus.PENDING
        )
    else:
        status = DeliveryFactStatus.REFUTED
    return DeliveryFact(
        status=status,
        evidence=evidence,
        source=source,
        observed_at=observed_at,
        target_version=target_version,
    )


def build_delivery_facts(
    *,
    delivery_ready: bool | None = None,
    released: bool | None = None,
    deployed: bool | None = None,
    operating: bool | None = None,
    evidence: dict[str, str | list[str] | tuple[str, ...]] | None = None,
    sources: dict[str, str] | None = None,
    observed_at: dict[str, str] | None = None,
    target_versions: dict[str, str] | None = None,
) -> DeliveryFacts:
    """Build each fact only from its own observation; never infer neighbouring facts."""

    evidence = evidence or {}
    sources = sources or {}
    observed_at = observed_at or {}
    target_versions = target_versions or {}

    def evidence_items(name: str) -> tuple[str, ...]:
        value = evidence.get(name, ())
        if isinstance(value, str):
            return (value,) if value.strip() else ()
        return tuple(str(item) for item in value if str(item).strip())

    def make(name: str, value: bool | None) -> DeliveryFact:
        return _fact_from_observation(
            value,
            evidence=evidence_items(name),
            source=str(sources.get(name, "")).strip(),
            observed_at=str(observed_at.get(name, "")).strip(),
            target_version=str(target_versions.get(name, "")).strip(),
        )

    return DeliveryFacts(
        delivery_ready=make("delivery_ready", delivery_ready),
        released=make("released", released),
        deployed=make("deployed", deployed),
        operating=make("operating", operating),
    )


@dataclass(frozen=True)
class OperationalOutcome:
    signal: str
    source: str
    observed_at: str
    target_version: str
    evidence: tuple[str, ...]
    confidence: str
    impact: str
    recommended_action: str
    requires_user_decision: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> OperationalOutcome:
        evidence_value = payload.get("evidence", ())
        evidence: tuple[str, ...]
        if isinstance(evidence_value, str):
            evidence = (evidence_value,) if evidence_value.strip() else ()
        elif isinstance(evidence_value, list | tuple):
            evidence = tuple(str(item) for item in evidence_value if str(item).strip())
        else:
            evidence = ()
        confidence = str(payload.get("confidence", "pending")).strip().lower()
        if confidence not in {"verified", "pending", "refuted"}:
            confidence = "pending"
        source = str(payload.get("source", "")).strip()
        observed_at = str(payload.get("observed_at", "")).strip()
        target_version = str(payload.get("target_version", "")).strip()
        if confidence == "verified" and not all((source, observed_at, target_version, evidence)):
            confidence = "pending"
        return cls(
            signal=str(payload.get("signal", "")).strip(),
            source=source,
            observed_at=observed_at,
            target_version=target_version,
            evidence=evidence,
            confidence=confidence,
            impact=str(payload.get("impact", "")).strip(),
            recommended_action=str(payload.get("recommended_action", "")).strip(),
            requires_user_decision=bool(payload.get("requires_user_decision", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "source": self.source,
            "observed_at": self.observed_at,
            "target_version": self.target_version,
            "evidence": list(self.evidence),
            "confidence": self.confidence,
            "impact": self.impact,
            "recommended_action": self.recommended_action,
            "requires_user_decision": self.requires_user_decision,
        }


def normalize_operational_outcomes(
    outcomes: list[OperationalOutcome | dict[str, Any]],
) -> list[OperationalOutcome]:
    return [
        item if isinstance(item, OperationalOutcome) else OperationalOutcome.from_dict(item)
        for item in outcomes
    ]


def merge_preserved_post_delivery_facts(
    current: DeliveryFacts, preserved: dict[str, Any] | None
) -> DeliveryFacts:
    """Recompute readiness while preserving only validated independent later facts."""

    previous = DeliveryFacts.from_dict(preserved or {})

    def preserve_for_current_version(fact: DeliveryFact) -> DeliveryFact:
        current_version = current.delivery_ready.target_version
        if fact.status is DeliveryFactStatus.VERIFIED and (
            not current_version or fact.target_version != current_version
        ):
            return DeliveryFact(
                status=DeliveryFactStatus.PENDING,
                evidence=fact.evidence,
                source=fact.source,
                observed_at=fact.observed_at,
                target_version=fact.target_version,
            )
        return fact

    return DeliveryFacts(
        delivery_ready=current.delivery_ready,
        released=preserve_for_current_version(previous.released),
        deployed=preserve_for_current_version(previous.deployed),
        operating=preserve_for_current_version(previous.operating),
    )


def normalize_report_delivery_facts(
    supplied: DeliveryFacts | dict[str, Any] | None,
    *,
    delivery_ready: bool,
    evidence: tuple[str, ...] | list[str],
    source: str,
    observed_at: str,
    target_version: str,
) -> DeliveryFacts:
    """Recompute report readiness and validate any preserved later facts."""

    current = build_delivery_facts(
        delivery_ready=delivery_ready,
        evidence={"delivery_ready": evidence},
        sources={"delivery_ready": source},
        observed_at={"delivery_ready": observed_at},
        target_versions={"delivery_ready": target_version},
    )
    if isinstance(supplied, DeliveryFacts):
        preserved = supplied.to_dict()
    elif isinstance(supplied, dict):
        preserved = supplied
    else:
        preserved = {}
    return merge_preserved_post_delivery_facts(current, preserved)


__all__ = [
    "DeliveryFact",
    "DeliveryFacts",
    "DeliveryFactStatus",
    "OperationalOutcome",
    "build_delivery_facts",
    "merge_preserved_post_delivery_facts",
    "normalize_operational_outcomes",
    "normalize_report_delivery_facts",
    "resolve_project_target_version",
]
