from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.artifact_utils import (
    normalize_work_item_id,
    resolve_active_change_id,
    resolve_current_artifact_prefix,
    resolve_work_item_identity,
)
from super_dev.review_state import (
    load_quality_revision,
    load_workflow_state,
    save_quality_revision,
    save_workflow_state,
)
from super_dev.work_item_identity import bind_standard_work_item, start_standard_work_item
from super_dev.workflow_guard import (
    WorkflowGateError,
    collect_docs_artifact_binding,
    require_spec_work_item_binding,
)


def _write_docs(project_dir: Path, prefix: str, marker: str) -> None:
    output = project_dir / "output"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{prefix}-research.md").write_text(f"research {marker}", encoding="utf-8")
    (output / f"{prefix}-prd.md").write_text(f"prd {marker}", encoding="utf-8")
    (output / f"{prefix}-architecture.md").write_text(f"arch {marker}", encoding="utf-8")
    (output / f"{prefix}-uiux.md").write_text(f"uiux {marker}", encoding="utf-8")


def test_pre_spec_work_item_hides_old_delivery_ready_change(tmp_path: Path) -> None:
    old_change = tmp_path / ".super-dev" / "changes" / "old-delivery"
    old_change.mkdir(parents=True)
    _write_docs(tmp_path, "old-delivery", "old")
    save_workflow_state(
        tmp_path,
        {"active_change_id": "old-delivery", "status": "delivery_ready"},
    )

    state = start_standard_work_item(tmp_path, "new-research")
    _write_docs(tmp_path, "new-research", "new")

    assert state["work_item_id"] == "new-research"
    assert state["artifact_prefix"] == "new-research"
    assert state["binding_status"] == "pre_spec"
    assert resolve_active_change_id(tmp_path) == ""
    assert resolve_current_artifact_prefix(tmp_path) == "new-research"
    assert collect_docs_artifact_binding(tmp_path)["work_item_id"] == "new-research"


def test_mismatched_work_item_and_change_fails_closed(tmp_path: Path) -> None:
    start_standard_work_item(tmp_path, "expected-change")
    _write_docs(tmp_path, "expected-change", "current")

    with pytest.raises(WorkflowGateError, match="工作项身份"):
        require_spec_work_item_binding(tmp_path, "wrong-change")
    assert resolve_work_item_identity(tmp_path).binding_status == "pre_spec"


def test_binding_requires_matching_confirmed_document_digest(tmp_path: Path) -> None:
    from super_dev.workflow_guard import save_bound_docs_confirmation

    start_standard_work_item(tmp_path, "right-change")
    _write_docs(tmp_path, "right-change", "v1")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    (tmp_path / "output" / "right-change-prd.md").write_text("prd v2", encoding="utf-8")

    with pytest.raises(WorkflowGateError, match="文档绑定"):
        require_spec_work_item_binding(tmp_path, "right-change")


def test_binding_transitions_same_identity_without_guessing(tmp_path: Path) -> None:
    from super_dev.workflow_guard import save_bound_docs_confirmation

    start_standard_work_item(tmp_path, "right-change")
    _write_docs(tmp_path, "right-change", "v1")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    require_spec_work_item_binding(tmp_path, "right-change")
    (tmp_path / ".super-dev" / "changes" / "right-change").mkdir(parents=True)

    state = bind_standard_work_item(tmp_path, "right-change")
    assert state["active_change_id"] == "right-change"
    assert state["binding_status"] == "bound"
    assert resolve_active_change_id(tmp_path) == "right-change"


def test_legacy_state_without_identity_remains_readable(tmp_path: Path) -> None:
    change = tmp_path / ".super-dev" / "changes" / "legacy-change"
    change.mkdir(parents=True)
    state_file = tmp_path / ".super-dev" / "workflow-state.json"
    state_file.write_text(
        json.dumps({"active_change_id": "legacy-change", "status": "delivery_ready"}),
        encoding="utf-8",
    )

    identity = resolve_work_item_identity(tmp_path)
    assert identity.legacy is True
    assert identity.work_item_id == "legacy-change"
    assert identity.binding_status == "bound"
    assert resolve_active_change_id(tmp_path) == "legacy-change"


def test_workflow_state_write_is_atomic_and_does_not_leave_temp_files(tmp_path: Path) -> None:
    path = save_workflow_state(tmp_path, {"status": "research", "work_item_id": "atomic"})
    assert load_workflow_state(tmp_path)["work_item_id"] == "atomic"
    assert load_workflow_state(tmp_path)["artifact_prefix"] == "atomic"
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))


def test_workflow_state_writer_rejects_a_second_identity_prefix(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="derived"):
        save_workflow_state(
            tmp_path,
            {"work_item_id": "one-identity", "artifact_prefix": "another-identity"},
        )


def test_workflow_state_writer_normalizes_unicode_identity_fields(tmp_path: Path) -> None:
    save_workflow_state(tmp_path, {"work_item_id": "ＡＢＣ-change"})
    state = load_workflow_state(tmp_path)
    assert state is not None
    assert state["work_item_id"] == "ABC-change"
    assert state["artifact_prefix"] == "abc-change"


def test_workflow_state_writer_rejects_pre_spec_with_an_active_change(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="pre_spec"):
        save_workflow_state(
            tmp_path,
            {
                "work_item_id": "contradictory",
                "binding_status": "pre_spec",
                "active_change_id": "contradictory",
            },
        )


def test_revision_state_from_another_work_item_is_not_inherited(tmp_path: Path) -> None:
    start_standard_work_item(tmp_path, "first-item")
    save_quality_revision(
        tmp_path,
        {"status": "revision_requested", "comment": "first item only"},
    )
    assert load_quality_revision(tmp_path)["work_item_id"] == "first-item"

    start_standard_work_item(tmp_path, "second-item")

    assert load_quality_revision(tmp_path) is None


def test_safe_chinese_work_item_identity_is_supported(tmp_path: Path) -> None:
    state = start_standard_work_item(tmp_path, "构建登录看板")
    assert state["work_item_id"] == "构建登录看板"
    assert state["artifact_prefix"] == "构建登录看板"


def test_work_item_identity_uses_nfkc_normalization() -> None:
    assert normalize_work_item_id("ＡＢＣ-change") == "ABC-change"
    assert normalize_work_item_id(normalize_work_item_id("ＡＢＣ-change")) == "ABC-change"


def test_spec_propose_binds_the_confirmed_pre_spec_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from super_dev.cli import SuperDevCLI
    from super_dev.workflow_guard import save_bound_docs_confirmation

    start_standard_work_item(tmp_path, "confirmed-change")
    _write_docs(tmp_path, "confirmed-change", "v1")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    monkeypatch.chdir(tmp_path)

    result = SuperDevCLI().run(
        [
            "spec",
            "propose",
            "confirmed-change",
            "--title",
            "Confirmed change",
            "--description",
            "Bind the confirmed documents",
            "--changed-surfaces",
            "backend",
        ]
    )

    assert result == 0
    state = load_workflow_state(tmp_path)
    assert state is not None
    assert state["binding_status"] == "bound"
    assert state["active_change_id"] == "confirmed-change"
    assert (tmp_path / ".super-dev" / "changes" / "confirmed-change" / "proposal.md").is_file()


def test_spec_builder_preserves_the_explicit_work_item_case(tmp_path: Path) -> None:
    from super_dev.creators.spec_builder import SpecBuilder
    from super_dev.workflow_guard import save_bound_docs_confirmation

    start_standard_work_item(tmp_path, "ABC-change")
    _write_docs(tmp_path, "abc-change", "v1")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})

    change_id = SpecBuilder(tmp_path, "ABC-change", "Keep the canonical identity").create_change(
        [],
        {"backend": "python"},
        scenario="1-N+1",
        changed_surfaces={"backend"},
    )

    assert change_id == "ABC-change"
    assert (tmp_path / ".super-dev" / "changes" / "ABC-change").is_dir()


def test_seeai_identity_and_binding_path_remains_legacy_compatible(tmp_path: Path) -> None:
    change = tmp_path / ".super-dev" / "changes" / "seeai-change"
    change.mkdir(parents=True)
    state_file = tmp_path / ".super-dev" / "workflow-state.json"
    state_file.write_text(
        json.dumps(
            {
                "flow_variant": "seeai",
                "work_item_id": "ignored-by-standard-binding",
                "active_change_id": "seeai-change",
            }
        ),
        encoding="utf-8",
    )

    identity = resolve_work_item_identity(tmp_path)
    assert identity.legacy is True
    assert resolve_active_change_id(tmp_path) == "seeai-change"


def test_start_does_not_downgrade_the_same_bound_work_item(tmp_path: Path) -> None:
    from super_dev.workflow_guard import save_bound_docs_confirmation

    start_standard_work_item(tmp_path, "bound-change")
    _write_docs(tmp_path, "bound-change", "v1")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    (tmp_path / ".super-dev" / "changes" / "bound-change").mkdir(parents=True)
    bound = bind_standard_work_item(tmp_path, "bound-change")

    resumed = start_standard_work_item(tmp_path, "bound-change")

    assert resumed["binding_status"] == "bound"
    assert resumed["active_change_id"] == "bound-change"
    assert resumed["updated_at"] == bound["updated_at"]


def test_start_does_not_reset_the_same_pre_spec_work_item(tmp_path: Path) -> None:
    original = start_standard_work_item(tmp_path, "pre-spec-change")
    original["document_binding_digest"] = "docs-digest"
    original["status"] = "waiting_docs_confirmation"
    save_workflow_state(tmp_path, original)
    before = load_workflow_state(tmp_path)

    resumed = start_standard_work_item(tmp_path, "pre-spec-change")

    assert before is not None
    assert resumed["binding_status"] == "pre_spec"
    assert resumed["document_binding_digest"] == "docs-digest"
    assert resumed["status"] == "waiting_docs_confirmation"
    assert resumed["updated_at"] == before["updated_at"]


def test_standard_start_refuses_to_overwrite_active_seeai_state(tmp_path: Path) -> None:
    change = tmp_path / ".super-dev" / "changes" / "seeai-active"
    change.mkdir(parents=True)
    save_workflow_state(
        tmp_path,
        {
            "flow_variant": "seeai",
            "active_change_id": "seeai-active",
            "status": "build_fullstack",
        },
    )

    with pytest.raises(ValueError, match="SEEAI"):
        start_standard_work_item(tmp_path, "standard-change")
