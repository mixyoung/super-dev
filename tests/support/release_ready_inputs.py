"""Honest release-ready inputs: bind and prepare specs before evidence hydration.

Write inputs before evidence_identity is built, then record fixture confirmations
against the final documents and preview artifacts. These synthetic inputs are not
real human acceptance or production release evidence.
"""

from __future__ import annotations

from pathlib import Path

from super_dev.artifact_utils import resolve_active_change_id, sanitize_artifact_name
from super_dev.host_runtime_validation import update_host_runtime_validation_state
from super_dev.review_state import load_workflow_state, save_workflow_state
from super_dev.specs import SpecGenerator
from super_dev.workflow_guard import (
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)


def write_release_ready_docs(
    project_dir: Path,
    *,
    change_id: str | None = None,
    artifact_prefix: str | None = None,
) -> None:
    project_dir = Path(project_dir)
    target = (
        change_id
        or resolve_active_change_id(project_dir)
        or sanitize_artifact_name(artifact_prefix or project_dir.name)
    )
    name = artifact_prefix or sanitize_artifact_name(target)
    generator = SpecGenerator(project_dir)
    generator.create_change(target, "版本信息展示", "README 与包内版本信息保持一致")
    artifacts = generator.scaffold_change_artifacts(target)
    current = load_workflow_state(project_dir) or {}
    save_workflow_state(
        project_dir,
        {
            **current,
            "active_change_id": target,
            "artifact_prefix": name,
            "status": current.get("status", "delivery"),
            "current_step_label": current.get("current_step_label", "交付证据已就绪"),
        },
    )
    output = project_dir / "output"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{name}-prd.md").write_text(
        "# PRD\n\n## 2. 功能需求\n\n### 版本信息展示\n\n在 README 与包内元数据中展示当前版本号。\n",
        encoding="utf-8",
    )
    for doc in ("architecture", "uiux"):
        path = output / f"{name}-{doc}.md"
        if not path.exists():
            path.write_text(f"# {doc}\n", encoding="utf-8")
    change_dir = project_dir / ".super-dev" / "changes" / target
    artifacts["spec.md"].write_text(
        "# 版本信息展示\n\n## ADDED Requirements\n\n"
        "### Requirement: package-version\n"
        "The system SHALL expose the current package version in README and package metadata.\n\n"
        "#### Scenario: Version agreement\n"
        "- GIVEN the installed package version\n"
        "- WHEN README and package metadata are inspected\n"
        "- THEN both display the same current version\n",
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n- [x] 版本信息展示：README 与包内版本一致\n",
        encoding="utf-8",
    )


def record_release_ready_acceptance(
    project_dir: Path,
    *,
    change_id: str | None = None,
) -> None:
    """Bind synthetic confirmations to final inputs; never claim real acceptance."""
    project_dir = Path(project_dir)
    target = resolve_active_change_id(project_dir)
    if not target:
        write_release_ready_docs(project_dir, change_id=change_id)
    elif change_id and target != change_id:
        raise ValueError("Release-ready fixture acceptance must match its bound target")
    save_bound_docs_confirmation(
        project_dir,
        {"status": "confirmed", "actor": "fixture", "comment": "release-ready fixture"},
    )
    save_bound_preview_confirmation(
        project_dir,
        {"status": "confirmed", "actor": "fixture", "comment": "release-ready fixture"},
    )
    update_host_runtime_validation_state(
        project_dir=project_dir,
        host="codex-cli",
        status="passed",
        comment="release-ready fixture",
        actor="fixture",
    )


def hydrate_release_ready_inputs(
    project_dir: Path,
    *,
    change_id: str | None = None,
) -> None:
    write_release_ready_docs(project_dir, change_id=change_id)
    record_release_ready_acceptance(project_dir, change_id=change_id)
