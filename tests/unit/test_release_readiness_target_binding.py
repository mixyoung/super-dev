"""Release checks must use the bound work item, not directory age or legacy names."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from super_dev.artifact_utils import sanitize_artifact_name
from super_dev.release_readiness import (
    ReleaseReadinessCheck,
    ReleaseReadinessEvaluator,
    ReleaseReadinessReport,
)
from super_dev.specs import SpecGenerator, SpecValidator


def _quality_change(project_dir: Path, change_id: str, *, valid: bool = True) -> Path:
    generator = SpecGenerator(project_dir)
    generator.create_change(change_id, "版本信息展示", "保持现有版本信息展示能力")
    generator.scaffold_change_artifacts(change_id)
    change_dir = project_dir / ".super-dev" / "changes" / change_id
    if not valid:
        for spec in (change_dir / "specs").rglob("spec.md"):
            spec.unlink()
    report = SpecValidator(project_dir).assess_change_quality(change_id)
    assert report.passed is valid  # Establish genuine quality, not a mocked report.
    return change_dir


def _bind(project_dir: Path, change_id: str, **overrides: object) -> None:
    payload = {
        "work_item_id": change_id,
        "active_change_id": change_id,
        "artifact_prefix": sanitize_artifact_name(change_id),
        "binding_status": "bound",
        "flow_variant": "standard",
        **overrides,
    }
    state = project_dir / ".super-dev" / "workflow-state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(payload), encoding="utf-8")


def _snapshot(project_dir: Path) -> dict[str, str]:
    return {
        str(path.relative_to(project_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in project_dir.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize("target_valid", [True, False])
@pytest.mark.parametrize("target_newer", [True, False])
def test_spec_quality_uses_bound_target_regardless_of_age(
    tmp_path: Path, target_valid: bool, target_newer: bool
) -> None:
    target = _quality_change(tmp_path, "target-fix", valid=target_valid)
    unrelated = _quality_change(tmp_path, "unrelated-fix", valid=not target_valid)
    _bind(tmp_path, "target-fix")
    old, new = 1_700_000_000, 1_700_010_000
    os.utime(target, (new if target_newer else old,) * 2)
    os.utime(unrelated, (old if target_newer else new,) * 2)
    before = _snapshot(tmp_path)

    check = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)._check_spec_quality()

    assert check.passed is target_valid
    assert "change=target-fix" in check.detail
    assert "unrelated-fix" not in check.detail
    assert _snapshot(tmp_path) == before


def test_unbound_single_valid_change_is_not_selected(tmp_path: Path) -> None:
    _quality_change(tmp_path, "only-change")
    before = _snapshot(tmp_path)
    check = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)._check_spec_quality()
    assert not check.passed
    assert check.severity == "critical"
    assert "目标" in check.detail
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
def test_invalid_binding_does_not_fall_back_to_another_change(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    _quality_change(tmp_path, "target-fix")
    _quality_change(tmp_path, "other-change")
    _bind(tmp_path, "target-fix", **overrides)
    before = _snapshot(tmp_path)
    check = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)._check_spec_quality()
    assert not check.passed
    assert check.severity == "critical"
    assert "绑定" in check.detail
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("removed_before_init", [True, False])
def test_missing_target_directory_does_not_select_valid_unrelated_change(
    tmp_path: Path, removed_before_init: bool
) -> None:
    target = _quality_change(tmp_path, "target-fix")
    _quality_change(tmp_path, "unrelated-fix")
    _bind(tmp_path, "target-fix")
    if removed_before_init:
        shutil.rmtree(target)
    evaluator = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)
    if not removed_before_init:
        shutil.rmtree(target)
    before = _snapshot(tmp_path)

    check = evaluator._check_spec_quality()

    assert not check.passed
    assert check.severity == "critical"
    assert "目录" in check.detail
    assert "unrelated-fix" not in check.detail
    assert _snapshot(tmp_path) == before


def test_missing_target_spec_is_not_replaced_by_an_unrelated_spec(tmp_path: Path) -> None:
    _quality_change(tmp_path, "target-fix", valid=False)
    _quality_change(tmp_path, "unrelated-fix")
    _bind(tmp_path, "target-fix")
    check = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)._check_spec_quality()
    assert not check.passed
    assert "change=target-fix" in check.detail
    assert "spec" in check.detail.lower()


@pytest.mark.parametrize("valid", [True, False])
def test_legacy_release_name_is_assessed_normally(tmp_path: Path, valid: bool) -> None:
    _quality_change(tmp_path, "release-hardening-finalization", valid=valid)
    _bind(tmp_path, "release-hardening-finalization")
    check = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)._check_spec_quality()
    assert check.passed is valid
    assert "change=release-hardening-finalization" in check.detail


def test_missing_target_blocks_an_otherwise_high_scoring_report(tmp_path: Path) -> None:
    _quality_change(tmp_path, "only-change")
    target_check = ReleaseReadinessEvaluator(
        tmp_path, persist_artifacts=False
    )._check_spec_quality()
    other_checks = [
        ReleaseReadinessCheck(f"other-{index}", True, "verified", "critical") for index in range(30)
    ]
    report = ReleaseReadinessReport("demo", checks=[target_check, *other_checks])
    assert report.score >= report.threshold
    assert all(check.passed for check in other_checks)
    assert not report.passed
    assert report.to_dict()["passed"] is False


def test_explicit_latest_quality_query_keeps_its_original_behavior(tmp_path: Path) -> None:
    older = _quality_change(tmp_path, "older-change")
    newer = _quality_change(tmp_path, "newer-change", valid=False)
    _bind(tmp_path, "older-change")
    os.utime(older, (1_700_000_000,) * 2)
    os.utime(newer, (1_700_010_000,) * 2)

    report = SpecValidator(tmp_path).assess_latest_change_quality()

    assert report is not None
    assert report.change_id == "newer-change"
    assert not report.passed


def test_bound_target_check_preserves_check_and_report_payload_shapes(tmp_path: Path) -> None:
    _quality_change(tmp_path, "target-fix")
    _bind(tmp_path, "target-fix")
    check = ReleaseReadinessEvaluator(tmp_path, persist_artifacts=False)._check_spec_quality()
    assert check.passed
    assert set(check.to_dict()) == {
        "name",
        "passed",
        "detail",
        "severity",
        "recommendation",
        "evidence",
    }
    report = ReleaseReadinessReport("demo", checks=[check])
    assert report.to_dict()["passed"]
    assert report.to_dict()["checks"][0]["name"] == "Spec Quality"
    assert "Spec Quality" in report.to_markdown()
