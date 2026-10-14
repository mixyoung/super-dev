"""Keep proof-pack and release spec checks bound to the same real work item."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from super_dev.proof_pack import ProofPackArtifact, ProofPackBuilder, ProofPackReport
from super_dev.release_readiness import ReleaseReadinessCheck, ReleaseReadinessEvaluator
from super_dev.specs import SpecValidator
from tests.unit.test_release_readiness_target_binding import _bind, _quality_change, _snapshot


def _checks(project_dir: Path) -> tuple[ProofPackArtifact, ReleaseReadinessCheck]:
    artifact = ProofPackBuilder(project_dir, persist_artifacts=False)._spec_quality_artifact()
    check = ReleaseReadinessEvaluator(project_dir, persist_artifacts=False)._check_spec_quality()
    return artifact, check


@pytest.mark.parametrize("target_valid", [True, False])
@pytest.mark.parametrize("target_newer", [True, False])
def test_both_spec_entries_use_bound_target_regardless_of_age(
    tmp_path: Path, target_valid: bool, target_newer: bool
) -> None:
    target = _quality_change(tmp_path, "target-fix", valid=target_valid)
    unrelated = _quality_change(tmp_path, "unrelated-fix", valid=not target_valid)
    _bind(tmp_path, "target-fix")
    old, new = 1_700_000_000, 1_700_010_000
    os.utime(target, (new if target_newer else old,) * 2)
    os.utime(unrelated, (old if target_newer else new,) * 2)
    before = _snapshot(tmp_path)

    artifact, check = _checks(tmp_path)

    expected = SpecValidator(tmp_path).assess_change_quality("target-fix")
    assert artifact.status == ("ready" if target_valid else "pending")
    assert check.passed is target_valid
    assert artifact.details == expected.to_dict()
    assert artifact.details["change_id"] == check.evidence["change_id"] == "target-fix"
    assert artifact.path == str(target)
    assert "change=target-fix" in artifact.summary
    assert "unrelated-fix" not in artifact.summary
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("has_change", [False, True])
def test_unbound_spec_item_is_not_ready_even_with_a_single_valid_change(
    tmp_path: Path, has_change: bool
) -> None:
    if has_change:
        _quality_change(tmp_path, "only-change")
    before = _snapshot(tmp_path)

    artifact, check = _checks(tmp_path)

    assert artifact.status == "pending"
    assert not check.passed
    assert "目标" in artifact.summary
    assert artifact.path == ""
    assert artifact.details == check.evidence
    assert artifact.details["reason"] == "missing_active_change"
    assert not (tmp_path / "output").exists()
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "overrides",
    [
        {"active_change_id": "other-change"},
        {"work_item_id": "../outside"},
        {"artifact_prefix": "other-prefix"},
        {"binding_status": "pre_spec"},
    ],
)
def test_invalid_binding_does_not_select_an_unrelated_valid_change(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    _quality_change(tmp_path, "target-fix")
    _quality_change(tmp_path, "other-change")
    _bind(tmp_path, "target-fix", **overrides)
    before = _snapshot(tmp_path)

    artifact, check = _checks(tmp_path)

    assert artifact.status == "pending"
    assert not check.passed
    assert "绑定" in artifact.summary
    assert artifact.path == ""
    assert artifact.details == check.evidence
    assert artifact.details["binding_issues"]
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("removed_before_init", [True, False])
def test_missing_target_directory_does_not_fall_back_to_a_valid_change(
    tmp_path: Path, removed_before_init: bool
) -> None:
    target = _quality_change(tmp_path, "target-fix")
    _quality_change(tmp_path, "unrelated-fix")
    _bind(tmp_path, "target-fix")
    if removed_before_init:
        shutil.rmtree(target)
    builder = ProofPackBuilder(tmp_path, persist_artifacts=False)
    evaluator = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)
    if not removed_before_init:
        shutil.rmtree(target)
    before = _snapshot(tmp_path)

    artifact = builder._spec_quality_artifact()
    check = evaluator._check_spec_quality()

    assert artifact.status == "pending"
    assert not check.passed
    assert "unrelated-fix" not in artifact.summary
    assert "目录" in artifact.summary + json.dumps(artifact.details, ensure_ascii=False)
    assert "目录" in check.detail
    if removed_before_init:
        assert artifact.path == ""
        assert artifact.details == check.evidence
    else:
        assert artifact.details["change_id"] == check.evidence["change_id"] == "target-fix"
    assert _snapshot(tmp_path) == before


def test_target_spec_removed_after_initialization_is_not_replaced(tmp_path: Path) -> None:
    target = _quality_change(tmp_path, "target-fix")
    _quality_change(tmp_path, "unrelated-fix")
    _bind(tmp_path, "target-fix")
    builder = ProofPackBuilder(tmp_path, persist_artifacts=False)
    evaluator = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)
    for spec in (target / "specs").rglob("spec.md"):
        spec.unlink()
    before = _snapshot(tmp_path)

    artifact = builder._spec_quality_artifact()
    check = evaluator._check_spec_quality()

    assert artifact.status == "pending"
    assert not check.passed
    assert artifact.details["change_id"] == check.evidence["change_id"] == "target-fix"
    assert artifact.details["checks"]["spec"]["passed"] is False
    assert "unrelated-fix" not in artifact.summary
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("valid", [True, False])
def test_legacy_release_target_name_is_not_exempt(tmp_path: Path, valid: bool) -> None:
    change_id = "release-hardening-finalization"
    _quality_change(tmp_path, change_id, valid=valid)
    _bind(tmp_path, change_id)
    before = _snapshot(tmp_path)

    artifact, check = _checks(tmp_path)

    assert artifact.status == ("ready" if valid else "pending")
    assert check.passed is valid
    assert artifact.details["change_id"] == check.evidence["change_id"] == change_id
    assert artifact.details == SpecValidator(tmp_path).assess_change_quality(change_id).to_dict()
    assert _snapshot(tmp_path) == before


def test_missing_target_blocks_an_otherwise_ready_proof_pack(tmp_path: Path) -> None:
    _quality_change(tmp_path, "only-change")
    artifact, check = _checks(tmp_path)
    other_artifacts = [
        ProofPackArtifact(f"other-{index}", "ready", "verified") for index in range(30)
    ]
    report = ProofPackReport("demo", artifacts=[artifact, *other_artifacts])

    assert not check.passed
    assert all(item.status == "ready" for item in other_artifacts)
    assert report.status == "incomplete"
    assert report.blockers == [artifact]
    assert report.ready_count == len(other_artifacts)
    assert report.to_dict()["status"] == "incomplete"


def test_explicit_latest_query_remains_independent_of_bound_entries(tmp_path: Path) -> None:
    older = _quality_change(tmp_path, "target-fix")
    newer = _quality_change(tmp_path, "unrelated-fix", valid=False)
    _bind(tmp_path, "target-fix")
    os.utime(older, (1_700_000_000,) * 2)
    os.utime(newer, (1_700_010_000,) * 2)
    before = _snapshot(tmp_path)

    artifact, check = _checks(tmp_path)
    latest = SpecValidator(tmp_path).assess_latest_change_quality()

    assert artifact.status == "ready" and check.passed
    assert artifact.details["change_id"] == check.evidence["change_id"] == "target-fix"
    assert latest is not None and latest.change_id == "unrelated-fix"
    assert not latest.passed
    assert _snapshot(tmp_path) == before


def test_spec_item_payload_stays_compatible_without_claiming_overall_ready(
    tmp_path: Path,
) -> None:
    _quality_change(tmp_path, "target-fix")
    _bind(tmp_path, "target-fix")
    artifact, check = _checks(tmp_path)
    report = ProofPackReport(
        "demo", artifacts=[artifact, ProofPackArtifact("other", "pending", "missing evidence")]
    )

    assert artifact.status == "ready" and check.passed
    assert set(artifact.to_dict()) == {"name", "status", "summary", "path", "details"}
    assert report.status == "incomplete"
    assert report.to_dict()["artifacts"][0] == artifact.to_dict()
    assert set(report.to_dict()) == {
        "project_name",
        "target_version",
        "generated_at",
        "status",
        "ready_count",
        "total_count",
        "completion_percent",
        "summary",
        "blocking_artifacts",
        "key_artifacts",
        "artifacts",
        "evidence_identity",
        "workflow_context",
        "baseline_governance",
        "delivery_facts",
        "operational_outcomes",
    }
