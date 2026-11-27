"""Shared writer for UI review outputs. Not used by read-only consumers."""

from __future__ import annotations

import json
from pathlib import Path

from ..evidence_contract import EvidenceStatus
from ..evidence_identity import build_evidence_identity
from .ui_review_evidence import SOURCE, UIReviewEvidence
from .ui_review_models import UIReviewReport


def write_ui_review_artifacts(
    project_dir: Path, prefix: str, report: UIReviewReport
) -> dict[str, Path]:
    evidence = UIReviewEvidence(
        project_dir, prefix, required=report.status is not EvidenceStatus.NOT_APPLICABLE
    )
    source = next((item for item in report.results if item.kind == SOURCE), None)
    if source is not None:
        evidence.save_source(source)
    base = evidence.output / evidence.prefix
    paths = {
        "markdown": base.with_name(f"{base.name}-ui-review.md"),
        "json": base.with_name(f"{base.name}-ui-review.json"),
        "alignment": base.with_name(f"{base.name}-ui-contract-alignment.md"),
        "alignment_json": base.with_name(f"{base.name}-ui-contract-alignment.json"),
    }
    summary = report.to_dict()
    alignment = dict(report.alignment_summary)
    if source is not None and source.dependencies:
        alignment["evidence_identity"] = build_evidence_identity(
            project_dir,
            artifact_name="ui-contract-alignment",
            dependencies=[evidence.contract, evidence.uiux],
        )
    evidence.write_artifact(paths["markdown"], report.to_markdown())
    evidence.write_artifact(paths["json"], json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    if evidence.required:
        evidence.write_artifact(paths["alignment"], report.alignment_markdown())
        evidence.write_artifact(
            paths["alignment_json"], json.dumps(alignment, ensure_ascii=False, indent=2) + "\n"
        )
    return paths
