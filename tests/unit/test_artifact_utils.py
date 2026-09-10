from __future__ import annotations

import json
from pathlib import Path

from super_dev import artifact_utils
from super_dev.artifact_utils import (
    latest_artifact,
    resolve_active_change_id,
    resolve_current_artifact_prefix,
    sanitize_artifact_name,
)
from super_dev.evidence_identity import build_evidence_identity
from super_dev.proof_pack import ProofPackBuilder
from super_dev.release_readiness import ReleaseReadinessEvaluator
from super_dev.reviewers.quality_gate import QualityGateChecker


def _create_change(project_dir: Path, change_id: str) -> Path:
    change_dir = project_dir / ".super-dev" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    return change_dir


def _write_workflow_state(project_dir: Path, payload: dict[str, object]) -> None:
    state_file = project_dir / ".super-dev" / "workflow-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload), encoding="utf-8")


def test_resolve_active_change_prefers_explicit_nested_workflow_state(
    temp_project_dir: Path,
    monkeypatch,
) -> None:
    _create_change(temp_project_dir, "workflow-change")
    _create_change(temp_project_dir, "branch-change")
    _write_workflow_state(
        temp_project_dir,
        {"pipeline_run_state": {"active_change_id": " workflow-change "}},
    )
    monkeypatch.setattr(
        artifact_utils,
        "_current_git_branch",
        lambda _project_dir: "feature/branch-change",
    )

    assert resolve_active_change_id(temp_project_dir) == "workflow-change"


def test_resolve_active_change_falls_back_to_supported_git_branch(
    temp_project_dir: Path,
    monkeypatch,
) -> None:
    _create_change(temp_project_dir, "branch-change")
    _write_workflow_state(temp_project_dir, {})
    monkeypatch.setattr(
        artifact_utils,
        "_current_git_branch",
        lambda _project_dir: "fix/topic/branch-change",
    )

    assert resolve_active_change_id(temp_project_dir) == "branch-change"


def test_resolve_active_change_accepts_nested_change_id(temp_project_dir: Path) -> None:
    _create_change(temp_project_dir, "nested-change")
    _write_workflow_state(
        temp_project_dir,
        {"run_context": {"change_id": "nested-change"}},
    )

    assert resolve_active_change_id(temp_project_dir) == "nested-change"


def test_resolve_active_change_rejects_unsafe_and_missing_changes(
    temp_project_dir: Path,
    monkeypatch,
) -> None:
    _write_workflow_state(
        temp_project_dir,
        {"active_change_id": "../escape", "change_id": "missing-change"},
    )
    monkeypatch.setattr(
        artifact_utils,
        "_current_git_branch",
        lambda _project_dir: "feature/also-missing",
    )

    assert resolve_active_change_id(temp_project_dir) == ""


def test_current_artifact_prefix_prefers_active_change_with_core_artifact(
    temp_project_dir: Path,
) -> None:
    _create_change(temp_project_dir, "active-change")
    _write_workflow_state(temp_project_dir, {"active_change_id": "active-change"})
    output_dir = temp_project_dir / "output"
    output_dir.mkdir()
    for suffix in ("research.md", "prd.md", "architecture.md", "uiux.md"):
        (output_dir / f"legacy-project-{suffix}").write_text(suffix, encoding="utf-8")
    (output_dir / "legacy-project-quality-gate.json").write_text(
        json.dumps({"passed": True}),
        encoding="utf-8",
    )
    active_prd = output_dir / "active-change-prd.md"
    active_prd.write_text("active", encoding="utf-8")

    assert resolve_current_artifact_prefix(temp_project_dir) == "active-change"

    active_prd.unlink()
    assert resolve_current_artifact_prefix(temp_project_dir) == "legacy-project"


def test_quality_release_and_proof_pack_share_active_change_prefix(
    temp_project_dir: Path,
) -> None:
    _create_change(temp_project_dir, "active-change")
    _write_workflow_state(temp_project_dir, {"active_change_id": "active-change"})
    output_dir = temp_project_dir / "output"
    output_dir.mkdir()
    (output_dir / "active-change-prd.md").write_text("active", encoding="utf-8")
    for suffix in ("research.md", "prd.md", "architecture.md", "uiux.md"):
        (output_dir / f"legacy-project-{suffix}").write_text(suffix, encoding="utf-8")
    (output_dir / "legacy-project-quality-gate.json").write_text(
        json.dumps({"passed": True}),
        encoding="utf-8",
    )
    (temp_project_dir / "super-dev.yaml").write_text(
        "name: configured-project\nfrontend: none\nbackend: none\n",
        encoding="utf-8",
    )

    quality = QualityGateChecker(
        project_dir=temp_project_dir,
        name="configured-project",
        tech_stack={"frontend": "none", "backend": "none"},
    )
    release = ReleaseReadinessEvaluator(temp_project_dir)
    proof_pack = ProofPackBuilder(temp_project_dir)

    assert quality.name == "active-change"
    assert release.project_name == "active-change"
    assert proof_pack.project_name == "active-change"
    assert release._latest("*-quality-gate.json") is None
    assert proof_pack._latest("*-quality-gate.json") is None
    assert (
        build_evidence_identity(
            temp_project_dir,
            artifact_name="quality-gate",
            dependencies=[],
        )["project_name"]
        == "active-change"
    )


def test_latest_artifact_accepts_legacy_underscore_and_mainland_chinese_prefixes(
    temp_project_dir: Path,
) -> None:
    output_dir = temp_project_dir / "output"
    output_dir.mkdir()
    underscore = output_dir / "demo_project-quality-gate.json"
    chinese = output_dir / "中文项目-quality-gate.json"
    underscore.write_text("{}", encoding="utf-8")
    chinese.write_text("{}", encoding="utf-8")

    assert (
        latest_artifact(
            output_dir,
            "*-quality-gate.json",
            preferred_prefix="demo_project",
            strict_prefix=True,
        )
        == underscore
    )
    assert (
        latest_artifact(
            output_dir,
            "*-quality-gate.json",
            preferred_prefix="中文项目",
            strict_prefix=True,
        )
        == chinese
    )


def test_sanitize_artifact_name_removes_windows_unsafe_characters() -> None:
    assert sanitize_artifact_name(' 项目_A<>:"/\\|?* 版本 ') == "项目-a-版本"
    assert sanitize_artifact_name("") == ""
