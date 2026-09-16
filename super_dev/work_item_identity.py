"""Standard-flow identity transitions before and after a formal Spec change."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_utils import (
    WORK_ITEM_IDENTITY_SCHEMA_VERSION,
    normalize_work_item_id,
    resolve_work_item_identity,
    sanitize_artifact_name,
)
from .review_state import load_docs_confirmation, load_workflow_state, save_workflow_state


def _validated_work_item_id(value: str) -> str:
    work_item_id = normalize_work_item_id(value)
    if not work_item_id:
        raise ValueError(f"invalid work_item_id: {value!r}")
    return work_item_id


def start_standard_work_item(project_dir: Path, work_item_id: str) -> dict[str, Any]:
    """Start a recoverable pre-Spec identity while leaving old changes read-only."""

    project_path = Path(project_dir).resolve()
    identity = _validated_work_item_id(work_item_id)
    previous = load_workflow_state(project_path) or {}
    previous_status = str(previous.get("status", "")).strip().lower()
    previous_flow = str(previous.get("flow_variant", "standard")).strip().lower()
    previous_identity = resolve_work_item_identity(project_path)
    terminal_statuses = {"delivery_ready", "completed", "archived", "closed"}
    if previous_flow == "seeai" and previous_status not in terminal_statuses:
        raise ValueError(
            "active SEEAI workflow must be resumed or explicitly closed before standard work"
        )
    if (
        not previous_identity.legacy
        and previous_identity.work_item_id == identity
        and previous_identity.binding_status in {"pre_spec", "bound"}
    ):
        return previous
    if previous_identity.active_change_id and previous_status not in terminal_statuses:
        raise ValueError("active bound work item must be resumed or explicitly closed")
    payload = {
        **previous,
        "workflow_state_schema_version": WORK_ITEM_IDENTITY_SCHEMA_VERSION,
        "flow_variant": "standard",
        "work_item_id": identity,
        "artifact_prefix": sanitize_artifact_name(identity),
        "active_change_id": "",
        "binding_status": "pre_spec",
        "document_binding_digest": "",
        "status": "research",
        "current_step_label": "同类产品研究",
        "reason": "标准流程工作项已建立；正式 change 只能在当前文档确认后绑定同一身份。",
        "evidence": f"work_item_id={identity}; binding_status=pre_spec",
        "pipeline_run_state": {
            "status": "research",
            "current_stage": "research",
            "current_stage_title": "同类产品研究",
            "scope_coverage_status": "",
            "scope_high_priority_gap_count": 0,
            "skipped_gates": [],
        },
    }
    save_workflow_state(project_path, payload)
    return load_workflow_state(project_path) or payload


def bind_standard_work_item(project_dir: Path, change_id: str) -> dict[str, Any]:
    """Bind a formal change only after identity and current document digest agree."""

    project_path = Path(project_dir).resolve()
    normalized_change = _validated_work_item_id(change_id)
    from .workflow_guard import require_spec_work_item_binding

    require_spec_work_item_binding(project_path, normalized_change)
    identity = resolve_work_item_identity(project_path)
    if identity.legacy:
        return load_workflow_state(project_path) or {}
    change_dir = project_path / ".super-dev" / "changes" / normalized_change
    if not change_dir.is_dir():
        raise FileNotFoundError(f"formal change does not exist: {normalized_change}")

    confirmation = load_docs_confirmation(project_path) or {}
    binding = confirmation.get("artifact_binding", {})
    digest = str(binding.get("digest", "")).strip() if isinstance(binding, dict) else ""
    payload = {
        **(load_workflow_state(project_path) or {}),
        "workflow_state_schema_version": WORK_ITEM_IDENTITY_SCHEMA_VERSION,
        "flow_variant": "standard",
        "work_item_id": identity.work_item_id,
        "artifact_prefix": identity.artifact_prefix,
        "active_change_id": normalized_change,
        "binding_status": "bound",
        "document_binding_digest": digest,
        "status": "spec",
        "current_step_label": "Spec 与任务清单",
        "reason": "正式 change 已与同一 work item 及已确认文档摘要绑定。",
        "evidence": f"work_item_id={identity.work_item_id}; docs_digest={digest}",
    }
    save_workflow_state(project_path, payload)
    return load_workflow_state(project_path) or payload


__all__ = ["bind_standard_work_item", "start_standard_work_item"]
