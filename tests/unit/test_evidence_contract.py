from __future__ import annotations

from datetime import datetime, timezone

import pytest

from super_dev.evidence_contract import (
    EvidenceArtifact,
    EvidenceEnvelope,
    EvidenceStatus,
    EvidenceValidationError,
)
from super_dev.evidence_identity import attach_evidence_identity


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_pass_evidence_requires_current_code_identity() -> None:
    with pytest.raises(EvidenceValidationError, match="candidate_digest"):
        EvidenceEnvelope(
            schema_version=1,
            evidence_id="quality-1",
            evidence_type="quality_gate",
            subject_type="candidate",
            subject_digest="sha256:abc",
            work_item_id="evidence-test",
            candidate_digest="",
            producer="quality_gate",
            run_id="run-1",
            status=EvidenceStatus.PASS,
            observed_at=_now(),
        )


def test_evidence_matches_only_the_bound_candidate() -> None:
    envelope = EvidenceEnvelope(
        schema_version=1,
        evidence_id="fresh-1",
        evidence_type="fresh_verification",
        subject_type="candidate",
        subject_digest="sha256:candidate-a",
        work_item_id="evidence-test",
        candidate_digest="sha256:candidate-a",
        producer="fresh_verification",
        run_id="run-1",
        status=EvidenceStatus.PASS,
        observed_at=_now(),
        artifacts=(EvidenceArtifact(path="output/result.json", digest="sha256:result"),),
    )

    assert envelope.matches_candidate(
        work_item_id="evidence-test", candidate_digest="sha256:candidate-a"
    )
    assert not envelope.matches_candidate(
        work_item_id="evidence-test", candidate_digest="sha256:candidate-b"
    )
    assert EvidenceEnvelope.from_dict(envelope.to_dict()) == envelope


def test_attached_passing_report_gets_candidate_bound_envelope(tmp_path) -> None:
    dependency = tmp_path / "result.json"
    dependency.write_text("{}", encoding="utf-8")

    payload = attach_evidence_identity(
        {"passed": True, "generated_at": _now()},
        project_dir=tmp_path,
        artifact_name="quality-gate",
        dependencies=[dependency],
        run_id="quality-run",
    )

    identity = payload["evidence_identity"]
    envelope = payload["evidence_envelope"]
    assert envelope["status"] == "PASS"
    assert envelope["candidate_digest"] == identity["candidate_digest"]
    assert envelope["work_item_id"] == tmp_path.name
