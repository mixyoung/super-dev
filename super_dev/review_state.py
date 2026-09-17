from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifact_utils import (
    normalize_work_item_id,
    resolve_work_item_identity,
    sanitize_artifact_name,
)
from .atomic_io import atomic_write_text
from .state_store import StateStore
from .workflow_contract import ContentEffect, ControlSource, ensure_control_effect_allowed

_WORKFLOW_EVENT_LABELS = {
    "workflow_state_saved": "流程状态已保存",
    "baseline_confirmation_saved": "基线确认状态已更新",
    "docs_confirmation_saved": "三文档确认状态已更新",
    "resume_gate_saved": "恢复门状态已更新",
    "ui_revision_saved": "UI 改版状态已更新",
    "preview_confirmation_saved": "前端预览确认状态已更新",
    "architecture_revision_saved": "架构改版状态已更新",
    "quality_revision_saved": "质量返工状态已更新",
    "host_runtime_validation_saved": "宿主运行时验证状态已更新",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _control_source(payload: dict[str, Any]) -> tuple[ControlSource, bool]:
    raw_source = str(payload.get("_control_source", "system_contract")).strip().lower()
    try:
        source = ControlSource(raw_source)
    except ValueError as exc:
        raise PermissionError(f"unknown control source: {raw_source}") from exc
    return source, bool(payload.get("_explicit_user_authority", False))


def _normalize_controlled_payload(
    payload: dict[str, Any], *, effect: ContentEffect
) -> dict[str, Any]:
    normalized = dict(payload)
    source, explicit_user_authority = _control_source(normalized)
    ensure_control_effect_allowed(
        source,
        effect,
        explicit_user_authority=explicit_user_authority,
    )
    normalized.pop("_control_source", None)
    normalized.pop("_explicit_user_authority", None)
    return normalized


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> Path:
    return Path(atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2)))


def _bind_current_work_item(project_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    identity = resolve_work_item_identity(project_dir)
    if not identity.legacy and identity.work_item_id:
        normalized["work_item_id"] = identity.work_item_id
    return normalized


def _only_for_current_work_item(
    project_dir: Path, payload: dict[str, Any] | None
) -> dict[str, Any] | None:
    if payload is None:
        return None
    identity = resolve_work_item_identity(project_dir)
    if identity.legacy:
        return payload
    if not identity.valid or not identity.work_item_id:
        return None
    return (
        payload if str(payload.get("work_item_id", "")).strip() == identity.work_item_id else None
    )


def _normalize_work_item_fields(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if str(normalized.get("flow_variant", "standard")).strip().lower() == "seeai":
        return normalized
    if "work_item_id" not in normalized:
        return normalized
    work_item_id = normalize_work_item_id(normalized.get("work_item_id", ""))
    if not work_item_id:
        raise ValueError("work_item_id cannot be empty when the field is present")
    normalized["work_item_id"] = work_item_id
    expected_prefix = sanitize_artifact_name(work_item_id)
    stored_prefix = str(normalized.get("artifact_prefix", "")).strip()
    if stored_prefix and stored_prefix != expected_prefix:
        raise ValueError("artifact_prefix must be derived from work_item_id")
    normalized["artifact_prefix"] = expected_prefix
    binding_status = str(normalized.get("binding_status", "")).strip().lower()
    raw_active_change_id = str(normalized.get("active_change_id", "")).strip()
    active_change_id = normalize_work_item_id(raw_active_change_id) if raw_active_change_id else ""
    if raw_active_change_id and not active_change_id:
        raise ValueError("active_change_id is invalid")
    if active_change_id:
        normalized["active_change_id"] = active_change_id
    if not binding_status:
        binding_status = "bound" if active_change_id else "pre_spec"
    if binding_status == "pre_spec" and active_change_id:
        raise ValueError("pre_spec work item cannot have active_change_id")
    if binding_status == "bound" and active_change_id != work_item_id:
        raise ValueError("bound active_change_id must equal work_item_id")
    if binding_status not in {"pre_spec", "bound"}:
        raise ValueError("binding_status must be pre_spec or bound")
    normalized["binding_status"] = binding_status
    return normalized


def review_state_dir(project_dir: Path) -> Path:
    return Path(project_dir).resolve() / ".super-dev" / "review-state"


def docs_confirmation_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "document-confirmation.json"


def baseline_confirmation_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "baseline-confirmation.json"


def resume_gate_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "resume-gate.json"


def ui_revision_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "ui-revision.json"


def preview_confirmation_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "preview-confirmation.json"


def architecture_revision_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "architecture-revision.json"


def quality_revision_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "quality-revision.json"


def host_runtime_validation_file(project_dir: Path) -> Path:
    return review_state_dir(project_dir) / "host-runtime-validation.json"


def workflow_state_file(project_dir: Path) -> Path:
    return Path(project_dir).resolve() / ".super-dev" / "workflow-state.json"


def workflow_state_history_dir(project_dir: Path) -> Path:
    return Path(project_dir).resolve() / ".super-dev" / "workflow-history"


def latest_workflow_snapshot_file(project_dir: Path) -> Path:
    return workflow_state_history_dir(project_dir) / "latest.json"


def workflow_event_log_file(project_dir: Path) -> Path:
    return Path(project_dir).resolve() / ".super-dev" / "workflow-events.jsonl"


def _append_workflow_event(
    project_dir: Path,
    *,
    event: str,
    payload: dict[str, Any],
    source_path: Path,
    extra: dict[str, Any] | None = None,
) -> None:
    event_log = workflow_event_log_file(project_dir)
    event_log.parent.mkdir(parents=True, exist_ok=True)
    normalized = dict(payload)
    record = {
        "timestamp": str(normalized.get("updated_at", "")).strip() or _utc_now(),
        "event": event,
        "status": str(normalized.get("status", "")).strip()
        or str(normalized.get("workflow_status", "")).strip(),
        "workflow_mode": str(normalized.get("workflow_mode", "")).strip(),
        "current_step_label": str(normalized.get("current_step_label", "")).strip()
        or str(normalized.get("title", "")).strip(),
        "source_path": str(source_path),
    }
    if extra:
        record.update(extra)
    with event_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    try:
        from .hooks.manager import HookManager

        HookManager.dispatch_workflow_event(project_dir, record)
    except Exception:
        # Workflow event hooks are optional and must never break state persistence.
        pass


def load_recent_workflow_snapshots(
    project_dir: Path,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    history_dir = workflow_state_history_dir(project_dir)
    if not history_dir.exists():
        return []
    files = sorted(
        history_dir.glob("workflow-state-*.json"), key=lambda path: path.name, reverse=True
    )
    if not files:
        latest_file = latest_workflow_snapshot_file(project_dir)
        files = [latest_file] if latest_file.exists() else []

    snapshots: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for file_path in files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        status = str(payload.get("status", "") or payload.get("workflow_status", "")).strip()
        action_card = payload.get("action_card", {})
        if not isinstance(action_card, dict):
            action_card = {}
        current_step = (
            str(payload.get("current_step_label", "")).strip()
            or str(action_card.get("title", "")).strip()
            or status
        )
        updated_at = str(payload.get("updated_at", "")).strip()
        workflow_mode = str(payload.get("workflow_mode", "")).strip()
        dedupe_key = (updated_at, status, current_step)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        snapshots.append(
            {
                "path": str(file_path),
                "updated_at": updated_at,
                "status": status,
                "workflow_mode": workflow_mode,
                "current_step_label": current_step,
                "recommended_command": str(payload.get("recommended_command", "")).strip(),
            }
        )
        if len(snapshots) >= max(limit, 0):
            break
    return snapshots


def load_recent_workflow_events(
    project_dir: Path,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    log_file = workflow_event_log_file(project_dir)
    if not log_file.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        lines = log_file.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for raw in reversed(lines):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        if isinstance(payload, dict):
            events.append(payload)
        if len(events) >= max(limit, 0):
            break
    return events


def describe_workflow_event(payload: dict[str, Any]) -> str:
    event_name = str(payload.get("event", "")).strip()
    label = _WORKFLOW_EVENT_LABELS.get(event_name, event_name or "workflow event")
    step = (
        str(payload.get("current_step_label", "")).strip() or str(payload.get("status", "")).strip()
    )
    if step:
        return f"{label} · {step}"
    return label


def describe_hook_event(payload: dict[str, Any]) -> str:
    hook_name = str(payload.get("hook_name", "")).strip() or "hook"
    event = str(payload.get("event", "")).strip() or "event"
    phase = str(payload.get("phase", "")).strip() or "-"
    blocked = bool(payload.get("blocked", False))
    success = bool(payload.get("success", False))
    status = "blocked" if blocked else ("ok" if success else "failed")
    return f"Hook {hook_name} · {event} / {phase} / {status}"


def load_recent_operational_timeline(
    project_dir: Path,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    max_items = max(limit, 0)
    for item in load_recent_workflow_snapshots(project_dir, limit=max_items):
        timestamp = str(item.get("updated_at", "")).strip() or _utc_now()
        step = (
            str(item.get("current_step_label", "")).strip() or str(item.get("status", "")).strip()
        )
        timeline.append(
            {
                "timestamp": timestamp,
                "kind": "workflow_snapshot",
                "title": "流程快照",
                "message": step or "workflow snapshot",
                "source": str(item.get("path", "")).strip(),
                "payload": item,
            }
        )
    for item in load_recent_workflow_events(project_dir, limit=max_items):
        timestamp = str(item.get("timestamp", "")).strip() or _utc_now()
        timeline.append(
            {
                "timestamp": timestamp,
                "kind": "workflow_event",
                "title": "流程事件",
                "message": describe_workflow_event(item),
                "source": str(item.get("source_path", "")).strip(),
                "payload": item,
            }
        )
    try:
        from .hooks.manager import HookManager

        hook_items = HookManager.load_recent_history(project_dir, limit=max_items)
    except Exception:
        hook_items = []
    for hook_item in hook_items:
        payload = hook_item.to_dict()
        timestamp = str(payload.get("timestamp", "")).strip() or _utc_now()
        timeline.append(
            {
                "timestamp": timestamp,
                "kind": "hook_event",
                "title": "Hook 事件",
                "message": describe_hook_event(payload),
                "source": str(payload.get("source", "")).strip(),
                "payload": payload,
            }
        )
    timeline.sort(key=lambda entry: str(entry.get("timestamp", "")), reverse=True)
    return timeline[:max_items]


def load_docs_confirmation(project_dir: Path) -> dict[str, Any] | None:
    file_path = docs_confirmation_file(project_dir)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _only_for_current_work_item(project_dir, payload if isinstance(payload, dict) else None)


def load_baseline_confirmation(project_dir: Path) -> dict[str, Any] | None:
    file_path = baseline_confirmation_file(project_dir)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def load_resume_gate(project_dir: Path) -> dict[str, Any] | None:
    file_path = resume_gate_file(project_dir)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _only_for_current_work_item(project_dir, payload if isinstance(payload, dict) else None)


def load_ui_revision(project_dir: Path) -> dict[str, Any] | None:
    file_path = ui_revision_file(project_dir)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _only_for_current_work_item(project_dir, payload if isinstance(payload, dict) else None)


def load_preview_confirmation(project_dir: Path) -> dict[str, Any] | None:
    file_path = preview_confirmation_file(project_dir)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _only_for_current_work_item(project_dir, payload if isinstance(payload, dict) else None)


def load_architecture_revision(project_dir: Path) -> dict[str, Any] | None:
    file_path = architecture_revision_file(project_dir)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _only_for_current_work_item(project_dir, payload if isinstance(payload, dict) else None)


def load_quality_revision(project_dir: Path) -> dict[str, Any] | None:
    file_path = quality_revision_file(project_dir)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _only_for_current_work_item(project_dir, payload if isinstance(payload, dict) else None)


def load_host_runtime_validation(project_dir: Path) -> dict[str, Any] | None:
    file_path = host_runtime_validation_file(project_dir)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _only_for_current_work_item(project_dir, payload if isinstance(payload, dict) else None)


def load_workflow_state(project_dir: Path) -> dict[str, Any] | None:
    payload = StateStore(Path(project_dir)).load_workflow()
    return payload or None


def save_docs_confirmation(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_controlled_payload(payload, effect=ContentEffect.CONFIRMATION)
    normalized["updated_at"] = _utc_now()
    file_path = docs_confirmation_file(project_dir)
    _atomic_write_json(file_path, normalized)
    _append_workflow_event(
        project_dir,
        event="docs_confirmation_saved",
        payload=normalized,
        source_path=file_path,
        extra={"review_type": "docs_confirmation"},
    )
    return file_path


def save_baseline_confirmation(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_controlled_payload(payload, effect=ContentEffect.CONFIRMATION)
    normalized["updated_at"] = _utc_now()
    file_path = baseline_confirmation_file(project_dir)
    _atomic_write_json(file_path, normalized)
    _append_workflow_event(
        project_dir,
        event="baseline_confirmation_saved",
        payload=normalized,
        source_path=file_path,
        extra={"review_type": "baseline_confirmation"},
    )
    return file_path


def save_resume_gate(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    normalized = _bind_current_work_item(
        project_dir, _normalize_controlled_payload(payload, effect=ContentEffect.PHASE)
    )
    normalized["updated_at"] = _utc_now()
    file_path = resume_gate_file(project_dir)
    _atomic_write_json(file_path, normalized)
    _append_workflow_event(
        project_dir,
        event="resume_gate_saved",
        payload=normalized,
        source_path=file_path,
        extra={"review_type": "resume_gate"},
    )
    return file_path


def save_ui_revision(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    normalized = _bind_current_work_item(
        project_dir, _normalize_controlled_payload(payload, effect=ContentEffect.PHASE)
    )
    normalized["updated_at"] = _utc_now()
    file_path = ui_revision_file(project_dir)
    _atomic_write_json(file_path, normalized)
    _append_workflow_event(
        project_dir,
        event="ui_revision_saved",
        payload=normalized,
        source_path=file_path,
        extra={"review_type": "ui_revision"},
    )
    return file_path


def save_preview_confirmation(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_controlled_payload(payload, effect=ContentEffect.CONFIRMATION)
    normalized["updated_at"] = _utc_now()
    file_path = preview_confirmation_file(project_dir)
    _atomic_write_json(file_path, normalized)
    _append_workflow_event(
        project_dir,
        event="preview_confirmation_saved",
        payload=normalized,
        source_path=file_path,
        extra={"review_type": "preview_confirmation"},
    )
    return file_path


def save_architecture_revision(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    normalized = _bind_current_work_item(
        project_dir, _normalize_controlled_payload(payload, effect=ContentEffect.PHASE)
    )
    normalized["updated_at"] = _utc_now()
    file_path = architecture_revision_file(project_dir)
    _atomic_write_json(file_path, normalized)
    _append_workflow_event(
        project_dir,
        event="architecture_revision_saved",
        payload=normalized,
        source_path=file_path,
        extra={"review_type": "architecture_revision"},
    )
    return file_path


def save_quality_revision(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    normalized = _bind_current_work_item(
        project_dir, _normalize_controlled_payload(payload, effect=ContentEffect.PHASE)
    )
    normalized["updated_at"] = _utc_now()
    file_path = quality_revision_file(project_dir)
    _atomic_write_json(file_path, normalized)
    _append_workflow_event(
        project_dir,
        event="quality_revision_saved",
        payload=normalized,
        source_path=file_path,
        extra={"review_type": "quality_revision"},
    )
    return file_path


def save_host_runtime_validation(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    normalized = _bind_current_work_item(
        project_dir, _normalize_controlled_payload(payload, effect=ContentEffect.PHASE)
    )
    normalized["updated_at"] = _utc_now()
    file_path = host_runtime_validation_file(project_dir)
    _atomic_write_json(file_path, normalized)
    _append_workflow_event(
        project_dir,
        event="host_runtime_validation_saved",
        payload=normalized,
        source_path=file_path,
        extra={"review_type": "host_runtime_validation"},
    )
    return file_path


def save_workflow_state(project_dir: Path, payload: dict[str, Any]) -> Path:
    normalized = _normalize_work_item_fields(
        _normalize_controlled_payload(payload, effect=ContentEffect.PHASE)
    )
    result = StateStore(Path(project_dir)).commit_workflow(normalized)
    try:
        from .hooks.manager import HookManager

        HookManager.dispatch_workflow_event(
            project_dir,
            {
                "timestamp": str(result.payload.get("updated_at", "")).strip(),
                "event": "workflow_state_saved",
                "revision": result.revision,
                "work_item_id": str(result.payload.get("work_item_id", "")).strip(),
                "status": str(result.payload.get("status", "")).strip(),
                "current_step_label": str(result.payload.get("current_step_label", "")).strip(),
                "source_path": str(result.path),
            },
        )
    except Exception:
        pass
    return result.path
