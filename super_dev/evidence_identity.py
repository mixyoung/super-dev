"""Candidate identity and invalidation checks for critical evidence.

Requirement traceability: EVIDENCE-002 invalidates stale evidence after identity changes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifact_utils import resolve_current_artifact_prefix, resolve_work_item_identity
from .evidence_contract import EvidenceArtifact, EvidenceEnvelope, EvidenceStatus
from .extensions.evidence import build_candidate_identity
from .workflow_guard import load_stage_ledger


def _relative_label(project_dir: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_dir.resolve()))
    except Exception:
        return str(path.resolve())


def _digest_files(project_dir: Path, dependencies: Sequence[Path | None]) -> tuple[str, list[str]]:
    hasher = hashlib.sha256()
    labels: list[str] = []
    seen: set[str] = set()
    for dependency in dependencies:
        if dependency is None:
            continue
        path = Path(dependency).resolve()
        if not path.exists() or not path.is_file():
            continue
        label = _relative_label(project_dir, path)
        if label in seen:
            continue
        seen.add(label)
        labels.append(label)
        hasher.update(label.encode("utf-8"))
        hasher.update(b"\0")
        try:
            hasher.update(path.read_bytes())
        except Exception:
            hasher.update(b"<unreadable>")
        hasher.update(b"\0")
    return (hasher.hexdigest() if labels else "", labels)


def current_evidence_run_id(project_dir: Path) -> str:
    ledger = load_stage_ledger(project_dir)
    if not isinstance(ledger, dict):
        return ""
    for stage in ("preview", "docs"):
        entry = ledger.get(stage, {})
        if not isinstance(entry, dict):
            continue
        run_id = str(entry.get("run_id", "")).strip()
        if run_id:
            return run_id
    return ""


def build_evidence_identity(
    project_dir: Path,
    *,
    artifact_name: str,
    dependencies: Sequence[Path | None],
    run_id: str = "",
) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    digest, labels = _digest_files(project_dir, dependencies)
    work_item = resolve_work_item_identity(project_dir)
    candidate = build_candidate_identity(project_dir)
    return {
        "artifact_name": artifact_name,
        "project_name": resolve_current_artifact_prefix(
            project_dir,
            fallback_name=project_dir.name,
        ),
        "run_id": run_id.strip() or current_evidence_run_id(project_dir),
        "work_item_id": (
            work_item.work_item_id
            if work_item.valid and work_item.work_item_id
            else project_dir.name
        ),
        "candidate_digest": candidate.candidate_digest,
        "inputs_digest": digest,
        "dependency_count": len(labels),
        "dependencies": labels,
    }


def attach_evidence_identity(
    payload: dict[str, Any],
    *,
    project_dir: Path,
    artifact_name: str,
    dependencies: Sequence[Path | None],
    run_id: str = "",
) -> dict[str, Any]:
    normalized = dict(payload)
    identity = build_evidence_identity(
        project_dir,
        artifact_name=artifact_name,
        dependencies=dependencies,
        run_id=run_id,
    )
    normalized["evidence_identity"] = identity
    evidence_status = _result_status(normalized)
    if evidence_status is not None:
        observed_at = (
            str(normalized.get("observed_at", "")).strip()
            or str(normalized.get("generated_at", "")).strip()
            or datetime.now(timezone.utc).isoformat()
        )
        effective_run_id = str(identity.get("run_id", "")).strip() or (
            f"{artifact_name}-{str(identity.get('candidate_digest', ''))[-12:]}"
        )
        envelope = EvidenceEnvelope(
            schema_version=1,
            evidence_id=f"{artifact_name}-{effective_run_id}",
            evidence_type=artifact_name,
            subject_type="candidate",
            subject_digest=str(identity.get("candidate_digest", "")).strip(),
            work_item_id=str(identity.get("work_item_id", "")).strip()
            or Path(project_dir).resolve().name,
            candidate_digest=str(identity.get("candidate_digest", "")).strip(),
            producer=artifact_name,
            run_id=effective_run_id,
            status=evidence_status,
            observed_at=observed_at,
            artifacts=tuple(
                EvidenceArtifact(path=str(item)) for item in identity.get("dependencies", [])
            ),
            invalidation_triggers=(
                "candidate_changed",
                "inputs_changed",
                "work_item_changed",
            ),
        )
        normalized["evidence_envelope"] = envelope.to_dict()
    return normalized


def _result_status(payload: dict[str, Any]) -> EvidenceStatus | None:
    if isinstance(payload.get("passed"), bool):
        return EvidenceStatus.PASS if payload["passed"] else EvidenceStatus.FAIL
    raw = str(payload.get("status", "")).strip().lower()
    mapping = {
        "pass": EvidenceStatus.PASS,
        "passed": EvidenceStatus.PASS,
        "ready": EvidenceStatus.PASS,
        "success": EvidenceStatus.PASS,
        "completed": EvidenceStatus.PASS,
        "fail": EvidenceStatus.FAIL,
        "failed": EvidenceStatus.FAIL,
        "blocked": EvidenceStatus.BLOCKED,
        "not_applicable": EvidenceStatus.NOT_APPLICABLE,
    }
    return mapping.get(raw)


def load_json_payload(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def evidence_identity_matches(
    payload: dict[str, Any] | None,
    *,
    expected: dict[str, Any],
) -> tuple[bool, str]:
    payload = payload or {}
    identity = payload.get("evidence_identity", {})
    if not isinstance(identity, dict):
        identity = {}
    expected_digest = str(expected.get("inputs_digest", "")).strip()
    actual_digest = str(identity.get("inputs_digest", "")).strip()
    if not actual_digest:
        return False, "missing"
    if expected_digest != actual_digest:
        return False, "digest_mismatch"
    expected_work_item = str(expected.get("work_item_id", "")).strip()
    actual_work_item = str(identity.get("work_item_id", "")).strip()
    if expected_work_item and actual_work_item != expected_work_item:
        return False, "work_item_mismatch"
    expected_candidate = str(expected.get("candidate_digest", "")).strip()
    actual_candidate = str(identity.get("candidate_digest", "")).strip()
    if expected_candidate and actual_candidate != expected_candidate:
        return False, "candidate_mismatch"
    return True, "matched"
