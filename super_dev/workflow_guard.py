from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .artifact_utils import (
    resolve_active_change_id,
    resolve_work_item_identity,
    sanitize_artifact_name,
)
from .atomic_io import atomic_write_text
from .config.manager import ConfigManager
from .review_state import (
    load_docs_confirmation,
    load_preview_confirmation,
    load_workflow_state,
    review_state_dir,
    save_docs_confirmation,
    save_preview_confirmation,
)
from .state_store import StateStore
from .workflow_contract import (
    ContentEffect,
    ControlSource,
    ensure_control_effect_allowed,
    get_gate_config,
)
from .workflow_stage_truth import (
    active_experts_for_stage,
    normalize_stage_key,
    resolve_flow_variant,
    stages_require_docs_confirmation,
    stages_require_preview_confirmation,
)

_DOC_PATTERNS = ("*-prd.md", "*-architecture.md", "*-uiux.md")
_ACTIVE_DOC_PATTERNS = ("*-research.md", *_DOC_PATTERNS)
_PREVIEW_PATTERNS = (
    "*-frontend-runtime.json",
    "*-ui-review.md",
    "*-ui-review.json",
    "*-ui-contract.json",
    "*-ui-contract-alignment.json",
)


class WorkflowGateError(RuntimeError):
    """Raised when a workflow gate is bypassed."""

    def __init__(
        self,
        message: str,
        *,
        gate: str,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.gate = gate
        self.action = action
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": str(self),
            "gate": self.gate,
            "action": self.action,
            "details": self.details,
        }


def _require_authoritative_workflow(project_dir: Path, *, action: str) -> None:
    health = StateStore(project_dir).workflow_health()
    if health["status"] in {"corrupt", "missing_current"}:
        raise WorkflowGateError(
            "当前工作流状态损坏或缺失，必须先核对恢复候选并明确恢复，不能继续执行。",
            gate="workflow_recovery",
            action=action,
            details=health,
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stage_ledger_file(project_dir: Path) -> Path:
    return Path(review_state_dir(project_dir)) / "stage-ledger.json"


def load_stage_ledger(project_dir: Path) -> dict[str, Any]:
    file_path = stage_ledger_file(project_dir)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_stage_ledger(project_dir: Path, payload: dict[str, Any]) -> Path:
    state_dir = review_state_dir(project_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    file_path = stage_ledger_file(project_dir)
    atomic_write_text(file_path, json.dumps(payload, ensure_ascii=False, indent=2))
    return file_path


def _artifact_files(
    project_dir: Path,
    patterns: tuple[str, ...],
    *,
    artifact_prefix: str = "",
    strict_prefix: bool = False,
) -> list[Path]:
    output_dir = Path(project_dir).resolve() / "output"
    if not output_dir.exists() or (strict_prefix and not artifact_prefix):
        return []
    files: list[Path] = []
    for pattern in patterns:
        if artifact_prefix and pattern.startswith("*"):
            candidate = output_dir / f"{artifact_prefix}{pattern[1:]}"
            if candidate.is_file():
                files.append(candidate)
        else:
            files.extend(output_dir.glob(pattern))
    return sorted({path.resolve() for path in files if path.is_file()})


def _binding_digest(files: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in files:
        rel_path = path.name
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(b"\0")
        try:
            hasher.update(path.read_bytes())
        except Exception:
            hasher.update(b"<unreadable>")
        hasher.update(b"\0")
    return hasher.hexdigest()


def _artifact_binding(
    project_dir: Path,
    *,
    stage: str,
    patterns: tuple[str, ...],
    active_change_id: str = "",
    work_item_id: str = "",
    binding_status: str = "",
    artifact_prefix: str = "",
    strict_prefix: bool = False,
) -> dict[str, Any]:
    artifact_prefix = artifact_prefix or sanitize_artifact_name(work_item_id or active_change_id)
    files = _artifact_files(
        project_dir, patterns, artifact_prefix=artifact_prefix, strict_prefix=strict_prefix
    )
    return {
        "stage": stage,
        "file_count": len(files),
        "files": [str(path) for path in files],
        "digest": _binding_digest(files) if files else "",
        "generated_at": _utc_now(),
        **({"active_change_id": active_change_id} if active_change_id else {}),
        **({"work_item_id": work_item_id} if work_item_id else {}),
        **({"binding_status": binding_status} if binding_status else {}),
        **({"artifact_prefix": artifact_prefix} if artifact_prefix else {}),
    }


def _legacy_artifact_prefix(
    project_dir: Path, patterns: tuple[str, ...]
) -> tuple[str, list[str], int]:
    files = _artifact_files(project_dir, patterns)
    prefixes = {
        path.name[: -len(pattern[1:])]
        for path in files
        for pattern in patterns
        if path.name.endswith(pattern[1:])
    }
    if len(prefixes) == 1:
        return next(iter(prefixes)), [], len(files)
    try:
        configured = sanitize_artifact_name(ConfigManager(project_dir).load().name)
    except Exception:
        configured = ""
    for preferred in (configured, sanitize_artifact_name(Path(project_dir).name)):
        if preferred and preferred in prefixes:
            return preferred, [], len(files)
    return "", sorted(prefixes), len(files)


def collect_docs_artifact_binding(project_dir: Path) -> dict[str, Any]:
    identity = resolve_work_item_identity(project_dir)
    active_change_id = resolve_active_change_id(project_dir)
    work_item_id = identity.work_item_id if not identity.legacy else active_change_id
    artifact_owner_id = work_item_id or active_change_id
    artifact_prefix = sanitize_artifact_name(artifact_owner_id)
    ambiguous_prefixes: list[str] = []
    discovered_count = 0
    if identity.legacy and not artifact_owner_id:
        artifact_prefix, ambiguous_prefixes, discovered_count = _legacy_artifact_prefix(
            project_dir, _DOC_PATTERNS
        )
    binding = _artifact_binding(
        project_dir,
        stage="docs",
        patterns=_ACTIVE_DOC_PATTERNS if artifact_owner_id else _DOC_PATTERNS,
        active_change_id=active_change_id,
        work_item_id=work_item_id,
        binding_status=identity.binding_status,
        artifact_prefix=artifact_prefix,
        strict_prefix=True,
    )
    output_dir = Path(project_dir).resolve() / "output"
    core_file_count = (
        sum((output_dir / f"{artifact_prefix}{pattern[1:]}").is_file() for pattern in _DOC_PATTERNS)
        if artifact_prefix
        else 0
    )
    binding.update(
        {
            "core_file_count": core_file_count,
            "required_core_file_count": len(_DOC_PATTERNS),
            "core_complete": identity.valid and core_file_count == len(_DOC_PATTERNS),
            "discovered_file_count": max(discovered_count, int(binding["file_count"])),
            "ambiguous_prefixes": ambiguous_prefixes,
        }
    )
    return binding


def collect_preview_artifact_binding(project_dir: Path) -> dict[str, Any]:
    identity = resolve_work_item_identity(project_dir)
    active_change_id = resolve_active_change_id(project_dir)
    work_item_id = identity.work_item_id if not identity.legacy else active_change_id
    artifact_prefix = sanitize_artifact_name(work_item_id or active_change_id)
    if identity.legacy and not artifact_prefix:
        artifact_prefix, _, _ = _legacy_artifact_prefix(project_dir, _PREVIEW_PATTERNS)
    binding = _artifact_binding(
        project_dir,
        stage="preview",
        patterns=_PREVIEW_PATTERNS,
        active_change_id=active_change_id,
        work_item_id=work_item_id,
        binding_status=identity.binding_status,
        artifact_prefix=artifact_prefix,
        strict_prefix=True,
    )
    # QA 会刷新评审附件；人工预览确认绑定运行目标和 UI 契约，而非这些附件的生成时间。
    target_files = [
        Path(path)
        for path in binding["files"]
        if str(path).endswith(("-frontend-runtime.json", "-ui-contract.json"))
    ]
    binding["preview_target_schema_version"] = 1
    binding["preview_target_files"] = [str(path) for path in target_files]
    binding["preview_target_digest"] = _binding_digest(target_files) if target_files else ""
    return binding


def _preview_preconditions(
    project_dir: Path,
    binding: dict[str, Any],
    *,
    tech_stack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .deployers.delivery import derive_delivery_applicability
    from .evidence_identity import load_json_payload

    identity = resolve_work_item_identity(project_dir)
    payload = load_workflow_state(project_dir) or {}
    flow_variant = resolve_flow_variant(payload)
    required = True
    applicability = "unknown"
    reason = "无法确定预览适用性，不能按不适用放行。"
    try:
        config = ConfigManager(project_dir).load()
        overrides = tech_stack or {}
        effective = SimpleNamespace(
            **{
                key: overrides[key] if overrides.get(key) is not None else getattr(config, key, "")
                for key in ("platform", "frontend", "backend", "database")
            }
        )
        frontend_required = bool(derive_delivery_applicability(effective)["frontend_required"])
        required = frontend_required and get_gate_config(flow_variant)["preview_confirm"]
        applicability = "required" if required else "not_applicable"
        reason = (
            "当前界面项目需要有效运行证据及用户预览确认。"
            if required
            else (
                "当前模式不设中途预览确认门。"
                if frontend_required
                else "当前有效技术栈没有前端，预览确认不适用。"
            )
        )
    except Exception:
        pass
    if not identity.valid:
        required = True
        applicability = "unknown"
        reason = "工作项身份无效，不能推进预览确认后的阶段。"
    runtime_files = [
        Path(path)
        for path in binding.get("files", [])
        if str(path).endswith("-frontend-runtime.json")
    ]
    runtime_payload = load_json_payload(runtime_files[0]) if len(runtime_files) == 1 else {}
    runtime_ready = len(runtime_files) == 1 and runtime_payload.get("passed") is True
    runtime_status = (
        "passed"
        if runtime_ready
        else (
            "missing"
            if not runtime_files
            else "failed" if runtime_payload.get("passed") is False else "invalid"
        )
    )
    return {
        "required": required,
        "applicability": applicability,
        "reason": reason,
        "identity_valid": identity.valid,
        "runtime_ready": runtime_ready,
        "runtime_status": runtime_status,
        "runtime_files": [str(path) for path in runtime_files],
    }


def require_spec_work_item_binding(project_dir: Path, change_id: str) -> dict[str, Any]:
    """Require the formal Spec id to match the explicit pre-Spec identity and docs."""

    identity = resolve_work_item_identity(project_dir)
    if identity.legacy:
        return require_docs_confirmation(
            project_dir,
            action="spec_work_item_binding",
            require_context=True,
        )
    if not identity.valid:
        raise WorkflowGateError(
            "工作项身份无效，不能创建或绑定 Spec。",
            gate="work_item_identity",
            action="spec_work_item_binding",
            details={"issues": list(identity.issues), "change_id": change_id},
        )
    if str(change_id).strip() != identity.work_item_id:
        raise WorkflowGateError(
            "工作项身份与正式 change 不一致，不能自动选择或改写。",
            gate="work_item_identity",
            action="spec_work_item_binding",
            details={
                "work_item_id": identity.work_item_id,
                "change_id": str(change_id).strip(),
            },
        )

    gate_state = docs_gate_status(project_dir)
    confirmed_binding = gate_state.get("confirmed_artifact_binding", {})
    confirmed_work_item = (
        str(confirmed_binding.get("work_item_id", "")).strip()
        if isinstance(confirmed_binding, dict)
        else ""
    )
    if not gate_state.get("confirmed") or confirmed_work_item != identity.work_item_id:
        raise WorkflowGateError(
            "当前文档绑定与工作项身份不一致，不能创建或绑定 Spec。",
            gate="docs_confirmation",
            action="spec_work_item_binding",
            details={
                "work_item_id": identity.work_item_id,
                "confirmed_work_item_id": confirmed_work_item,
                "binding_matches_current": bool(gate_state.get("binding_matches_current")),
                "current_binding": gate_state.get("artifact_binding", {}),
                "confirmed_binding": confirmed_binding,
            },
        )
    return gate_state


def require_bound_work_item(project_dir: Path, change_id: str, *, action: str) -> dict[str, Any]:
    """Block post-Spec execution when an explicit identity is not formally bound."""

    identity = resolve_work_item_identity(project_dir)
    if identity.legacy:
        return require_docs_confirmation(project_dir, action=action, require_context=True)
    if (
        not identity.valid
        or identity.binding_status != "bound"
        or identity.active_change_id != str(change_id).strip()
    ):
        raise WorkflowGateError(
            "工作项尚未与当前正式 change 绑定，不能进入 Spec 后执行。",
            gate="work_item_identity",
            action=action,
            details={
                "work_item_id": identity.work_item_id,
                "active_change_id": identity.active_change_id,
                "change_id": str(change_id).strip(),
                "binding_status": identity.binding_status,
                "issues": list(identity.issues),
            },
        )
    return require_docs_confirmation(project_dir, action=action, require_context=True)


def _update_stage_ledger(
    project_dir: Path,
    *,
    stage: str,
    status: str,
    run_id: str = "",
    actor: str = "",
    artifact_binding: dict[str, Any] | None = None,
    active_experts: list[str] | tuple[str, ...] | None = None,
    details: dict[str, Any] | None = None,
    source: str = "",
    comment: str = "",
) -> dict[str, Any]:
    source_key = str(source).strip().lower()
    content_sources = {
        "knowledge": ControlSource.KNOWLEDGE,
        "external": ControlSource.EXTERNAL,
        "generated": ControlSource.GENERATED,
        "tool_output": ControlSource.TOOL_OUTPUT,
        "reviewed_instruction": ControlSource.REVIEWED_INSTRUCTION,
    }
    ensure_control_effect_allowed(
        content_sources.get(source_key, ControlSource.SYSTEM_CONTRACT),
        ContentEffect.PHASE,
    )
    ledger = load_stage_ledger(project_dir)
    artifact_binding = artifact_binding or {}
    normalized_stage = normalize_stage_key(stage)
    entry = {
        "stage": normalized_stage,
        "status": status,
        "run_id": run_id.strip(),
        "actor": actor.strip(),
        "comment": comment.strip(),
        "source": source.strip(),
        "artifact_binding": artifact_binding,
        "active_experts": [
            str(item).strip() for item in (active_experts or []) if str(item).strip()
        ],
        "details": details if isinstance(details, dict) else {},
        "updated_at": _utc_now(),
    }
    ledger[normalized_stage] = entry
    ledger["updated_at"] = entry["updated_at"]
    save_stage_ledger(project_dir, ledger)
    return entry


def record_docs_generated(
    project_dir: Path, *, run_id: str = "", source: str = "drafting"
) -> dict[str, Any]:
    binding = collect_docs_artifact_binding(project_dir)
    return _update_stage_ledger(
        project_dir,
        stage="docs",
        status="generated",
        run_id=run_id,
        actor="system",
        artifact_binding=binding,
        active_experts=active_experts_for_stage("docs"),
        source=source,
    )


def record_stage_progress(
    project_dir: Path,
    *,
    stage: str,
    status: str,
    run_id: str = "",
    actor: str = "system",
    source: str = "pipeline_state",
    comment: str = "",
    artifact_binding: dict[str, Any] | None = None,
    active_experts: list[str] | tuple[str, ...] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_stage = normalize_stage_key(stage)
    experts = (
        [str(item).strip() for item in active_experts if str(item).strip()]
        if active_experts is not None
        else list(active_experts_for_stage(normalized_stage))
    )
    return _update_stage_ledger(
        project_dir,
        stage=normalized_stage,
        status=status,
        run_id=run_id,
        actor=actor,
        artifact_binding=artifact_binding,
        active_experts=experts,
        details=details,
        source=source,
        comment=comment,
    )


def save_bound_docs_confirmation(
    project_dir: Path, payload: dict[str, Any]
) -> tuple[Path, dict[str, Any]]:
    identity = resolve_work_item_identity(project_dir)
    if not identity.legacy and not identity.valid:
        raise WorkflowGateError(
            "工作项身份无效，不能写入文档确认。",
            gate="work_item_identity",
            action="save_docs_confirmation",
            details={"issues": list(identity.issues)},
        )
    # 账本/确认文件/事件必须在同一把项目状态锁内写入；校验失败时不产生确认副作用。
    with StateStore(project_dir).exclusive_commit():
        _require_authoritative_workflow(project_dir, action="save_docs_confirmation")
        binding = collect_docs_artifact_binding(project_dir)
        if str(payload.get("status", "")).strip() == "confirmed" and not binding["core_complete"]:
            raise WorkflowGateError(
                "三份核心文档不完整或归属不明确，不能保存文档确认。",
                gate="docs_confirmation",
                action="save_docs_confirmation",
                details={"artifact_binding": binding},
            )
        normalized = dict(payload)
        if not identity.legacy and identity.work_item_id:
            normalized["work_item_id"] = identity.work_item_id
        normalized["artifact_binding"] = binding
        ledger_entry = _update_stage_ledger(
            project_dir,
            stage="docs_confirm",
            status=str(normalized.get("status", "")).strip() or "pending_review",
            run_id=str(normalized.get("run_id", "")).strip(),
            actor=str(normalized.get("actor", "")).strip(),
            artifact_binding=binding,
            active_experts=active_experts_for_stage("docs_confirm"),
            source="docs_confirmation",
            comment=str(normalized.get("comment", "")).strip(),
        )
        file_path = save_docs_confirmation(project_dir, normalized)
    return file_path, ledger_entry


def save_bound_preview_confirmation(
    project_dir: Path, payload: dict[str, Any]
) -> tuple[Path, dict[str, Any]]:
    identity = resolve_work_item_identity(project_dir)
    if not identity.valid:
        raise WorkflowGateError(
            "工作项身份无效，不能写入预览确认。",
            gate="work_item_identity",
            action="save_preview_confirmation",
            details={"issues": list(identity.issues)},
        )
    # 与文档确认相同的统一锁与顺序：先检查运行前提，再写账本和确认文件。
    with StateStore(project_dir).exclusive_commit():
        _require_authoritative_workflow(project_dir, action="save_preview_confirmation")
        binding = collect_preview_artifact_binding(project_dir)
        preconditions = _preview_preconditions(project_dir, binding)
        if (
            str(payload.get("status", "")).strip() == "confirmed"
            and preconditions["required"]
            and not preconditions["runtime_ready"]
        ):
            raise WorkflowGateError(
                "当前前端运行验证未通过，不能保存预览确认。",
                gate="preview_confirmation",
                action="save_preview_confirmation",
                details={**preconditions, "artifact_binding": binding},
            )
        normalized = dict(payload)
        if not identity.legacy and identity.work_item_id:
            normalized["work_item_id"] = identity.work_item_id
        normalized["artifact_binding"] = binding
        ledger_entry = _update_stage_ledger(
            project_dir,
            stage="preview_confirm",
            status=str(normalized.get("status", "")).strip() or "pending_review",
            run_id=str(normalized.get("run_id", "")).strip(),
            actor=str(normalized.get("actor", "")).strip(),
            artifact_binding=binding,
            active_experts=active_experts_for_stage("preview_confirm"),
            source="preview_confirmation",
            comment=str(normalized.get("comment", "")).strip(),
        )
        file_path = save_preview_confirmation(project_dir, normalized)
    return file_path, ledger_entry


def requested_phases_require_docs_confirmation(requested_phases: list[str] | None) -> bool:
    return bool(stages_require_docs_confirmation(requested_phases))


def requested_phases_require_preview_confirmation(requested_phases: list[str] | None) -> bool:
    return bool(stages_require_preview_confirmation(requested_phases))


def docs_gate_status(project_dir: Path) -> dict[str, Any]:
    binding = collect_docs_artifact_binding(project_dir)
    confirmation = load_docs_confirmation(project_dir) or {}
    ledger = load_stage_ledger(project_dir)
    ledger_entry = ledger.get("docs_confirm", {})
    if not isinstance(ledger_entry, dict) or not ledger_entry:
        legacy_entry = ledger.get("docs", {})
        ledger_entry = legacy_entry if isinstance(legacy_entry, dict) else {}
    has_context = bool(binding.get("discovered_file_count", binding.get("file_count", 0))) or bool(
        ledger_entry
    )
    status = str(confirmation.get("status", "")).strip() or "pending_review"
    confirmed_binding = confirmation.get("artifact_binding", {})
    if not isinstance(confirmed_binding, dict):
        confirmed_binding = {}
    if not confirmed_binding:
        confirmed_binding = ledger_entry.get("artifact_binding", {})
        if not isinstance(confirmed_binding, dict):
            confirmed_binding = {}
    stored_digest = str(confirmed_binding.get("digest", "")).strip()
    current_digest = str(binding.get("digest", "")).strip()
    binding_matches_current = bool(stored_digest) and stored_digest == current_digest
    core_complete = bool(binding.get("core_complete", False))
    confirmed = status == "confirmed" and binding_matches_current and core_complete
    return {
        "has_context": has_context,
        "confirmed": confirmed,
        "status": status,
        "artifact_binding": binding,
        "confirmed_artifact_binding": confirmed_binding,
        "binding_matches_current": binding_matches_current,
        "core_complete": core_complete,
        "confirmation": confirmation,
        "ledger_entry": ledger_entry,
    }


def preview_gate_status(
    project_dir: Path, *, tech_stack: dict[str, Any] | None = None
) -> dict[str, Any]:
    binding = collect_preview_artifact_binding(project_dir)
    preconditions = _preview_preconditions(project_dir, binding, tech_stack=tech_stack)
    confirmation = load_preview_confirmation(project_dir) or {}
    ledger = load_stage_ledger(project_dir)
    ledger_entry = ledger.get("preview_confirm", {})
    if not isinstance(ledger_entry, dict) or not ledger_entry:
        legacy_entry = ledger.get("preview", {})
        ledger_entry = legacy_entry if isinstance(legacy_entry, dict) else {}
    status = str(confirmation.get("status", "")).strip() or "pending_review"
    confirmed_binding = confirmation.get("artifact_binding", {})
    if not isinstance(confirmed_binding, dict):
        confirmed_binding = {}
    if not confirmed_binding:
        confirmed_binding = ledger_entry.get("artifact_binding", {})
        if not isinstance(confirmed_binding, dict):
            confirmed_binding = {}
    digest_key = (
        "preview_target_digest"
        if confirmed_binding.get("preview_target_schema_version") == 1
        else "digest"
    )
    stored_digest = str(confirmed_binding.get(digest_key, "")).strip()
    current_digest = str(binding.get(digest_key, "")).strip()
    binding_matches_current = bool(stored_digest) and stored_digest == current_digest
    return {
        **preconditions,
        "has_context": bool(binding.get("file_count", 0)) or bool(ledger_entry),
        "confirmed": (
            status == "confirmed"
            and binding_matches_current
            and preconditions["runtime_ready"]
            and preconditions["identity_valid"]
        ),
        "status": status,
        "artifact_binding": binding,
        "confirmed_artifact_binding": confirmed_binding,
        "binding_matches_current": binding_matches_current,
        "confirmation": confirmation,
        "ledger_entry": ledger_entry,
    }


def require_docs_confirmation(
    project_dir: Path,
    *,
    action: str,
    requested_phases: list[str] | None = None,
    require_context: bool = True,
) -> dict[str, Any]:
    identity = resolve_work_item_identity(project_dir)
    if not identity.legacy and not identity.valid:
        raise WorkflowGateError(
            "工作项身份无效，不能推进文档确认后的阶段。",
            gate="work_item_identity",
            action=action,
            details={"issues": list(identity.issues)},
        )
    requested = {
        normalize_stage_key(item) for item in (requested_phases or []) if str(item).strip()
    }
    if (
        not identity.legacy
        and identity.binding_status == "pre_spec"
        and requested & {"frontend", "preview_confirm", "backend", "quality", "delivery"}
    ):
        raise WorkflowGateError(
            "工作项仍处于 pre_spec，不能进入 Spec 之后的执行阶段。",
            gate="work_item_identity",
            action=action,
            details={"work_item_id": identity.work_item_id, "requested_phases": sorted(requested)},
        )
    gate_state = docs_gate_status(project_dir)
    if requested_phases is not None and not requested_phases_require_docs_confirmation(
        requested_phases
    ):
        return gate_state
    _require_authoritative_workflow(project_dir, action=action)
    if require_context and not gate_state["has_context"]:
        return gate_state
    if gate_state["confirmed"]:
        return gate_state
    raise WorkflowGateError(
        "三份核心文档尚未确认，不能跳过 docs_confirm 直接进入后续阶段。",
        gate="docs_confirmation",
        action=action,
        details={
            "status": gate_state["status"],
            "requested_phases": list(requested_phases or []),
            "artifact_binding": gate_state["artifact_binding"],
            "confirmed_artifact_binding": gate_state["confirmed_artifact_binding"],
            "binding_matches_current": gate_state["binding_matches_current"],
        },
    )


def require_preview_confirmation(
    project_dir: Path,
    *,
    action: str,
    requested_phases: list[str] | None = None,
    require_context: bool = True,
    tech_stack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate_state = preview_gate_status(project_dir, tech_stack=tech_stack)
    if requested_phases is not None and not requested_phases_require_preview_confirmation(
        requested_phases
    ):
        return gate_state
    _require_authoritative_workflow(project_dir, action=action)
    if not gate_state["identity_valid"]:
        raise WorkflowGateError(
            "工作项身份无效，不能推进预览确认后的阶段。",
            gate="work_item_identity",
            action=action,
        )
    # require_context 保留调用兼容；缺少证据不能取消实际适用的确认门。
    if not gate_state["required"]:
        return gate_state
    if gate_state["confirmed"]:
        return gate_state
    raise WorkflowGateError(
        "前端预览尚未确认或当前运行验证未通过，不能跳过 preview_confirm 直接进入后续阶段。",
        gate="preview_confirmation",
        action=action,
        details={
            "status": gate_state["status"],
            "requested_phases": list(requested_phases or []),
            "artifact_binding": gate_state["artifact_binding"],
            "confirmed_artifact_binding": gate_state["confirmed_artifact_binding"],
            "binding_matches_current": gate_state["binding_matches_current"],
            "applicability": gate_state["applicability"],
            "runtime_status": gate_state["runtime_status"],
            "reason": gate_state["reason"],
        },
    )
