from __future__ import annotations

import json
from pathlib import Path

from super_dev.review_state import load_docs_confirmation
from super_dev.workflow_guard import (
    collect_docs_artifact_binding,
    collect_preview_artifact_binding,
    docs_gate_status,
    save_bound_docs_confirmation,
)


def _write_active_change(project_dir: Path, change_id: str) -> None:
    state_file = project_dir / ".super-dev" / "workflow-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"active_change_id": change_id}), encoding="utf-8")


def test_docs_and_preview_bindings_include_only_active_change_artifacts(
    temp_project_dir: Path,
) -> None:
    output_dir = temp_project_dir / "output"
    output_dir.mkdir()
    for change_id in ("first-change", "active-change", "third-change"):
        (temp_project_dir / ".super-dev" / "changes" / change_id).mkdir(
            parents=True,
            exist_ok=True,
        )
        for suffix in ("research.md", "prd.md", "architecture.md", "uiux.md"):
            (output_dir / f"{change_id}-{suffix}").write_text(suffix, encoding="utf-8")
        for suffix in (
            "frontend-runtime.json",
            "ui-review.json",
            "ui-contract.json",
        ):
            (output_dir / f"{change_id}-{suffix}").write_text("{}", encoding="utf-8")

    _write_active_change(temp_project_dir, "active-change")

    docs_binding = collect_docs_artifact_binding(temp_project_dir)
    preview_binding = collect_preview_artifact_binding(temp_project_dir)

    assert docs_binding["active_change_id"] == "active-change"
    assert docs_binding["file_count"] == 4
    assert docs_binding["core_file_count"] == 3
    assert docs_binding["core_complete"] is True
    assert {Path(path).name for path in docs_binding["files"]} == {
        "active-change-research.md",
        "active-change-prd.md",
        "active-change-architecture.md",
        "active-change-uiux.md",
    }
    assert {Path(path).name for path in preview_binding["files"]} == {
        "active-change-frontend-runtime.json",
        "active-change-ui-review.json",
        "active-change-ui-contract.json",
    }

    save_bound_docs_confirmation(
        temp_project_dir,
        {"status": "confirmed", "actor": "pytest"},
    )
    confirmation = load_docs_confirmation(temp_project_dir) or {}
    assert docs_gate_status(temp_project_dir)["confirmed"] is True
    assert all(
        "active-change-" in Path(path).name for path in confirmation["artifact_binding"]["files"]
    )

    _write_active_change(temp_project_dir, "third-change")
    assert docs_gate_status(temp_project_dir)["confirmed"] is False


def test_active_docs_gate_requires_all_three_core_documents(temp_project_dir: Path) -> None:
    change_id = "active-change"
    (temp_project_dir / ".super-dev" / "changes" / change_id).mkdir(
        parents=True,
        exist_ok=True,
    )
    output_dir = temp_project_dir / "output"
    output_dir.mkdir()
    (output_dir / f"{change_id}-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / f"{change_id}-architecture.md").write_text("architecture", encoding="utf-8")
    _write_active_change(temp_project_dir, change_id)

    save_bound_docs_confirmation(
        temp_project_dir,
        {"status": "confirmed", "actor": "pytest"},
    )
    gate = docs_gate_status(temp_project_dir)

    assert gate["artifact_binding"]["core_file_count"] == 2
    assert gate["core_complete"] is False
    assert gate["confirmed"] is False
