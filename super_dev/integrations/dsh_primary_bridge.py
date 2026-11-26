"""Bound Core operations for the opt-in DSH native command bundle."""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

from ..artifact_utils import resolve_work_item_identity
from ..review_state import save_workflow_state
from ..skills.skill_template import SkillTemplate
from ..specs import SpecGenerator
from ..state_store import StateStore
from ..user_directories import ensure_plain_path
from ..work_item_identity import bind_dsh_primary_work_item, start_dsh_primary_work_item
from ..workflow_guard import (
    WorkflowGateError,
    collect_baseline_artifact_binding,
    require_docs_confirmation,
    require_preview_confirmation,
    require_spec_work_item_binding,
    save_bound_docs_confirmation,
    save_bound_dsh_baseline_confirmation,
    save_bound_preview_confirmation,
)
from ..workflow_state import detect_pipeline_summary
from .dsh_plugin_snapshot import _local_project, _read_file

PROTOCOL = "dsh-primary-v1"
OPS = {
    "start",
    "inspect",
    "instructions",
    "spec",
    "confirm-baseline",
    "confirm-docs",
    "confirm-preview",
}
BASELINE_SUFFIXES = ("baseline-audit.md", "baseline-audit.json")
DOC_SUFFIXES = ("prd.md", "architecture.md", "uiux.md")
OUTPUT_SUFFIXES = (*BASELINE_SUFFIXES, "research.md", *DOC_SUFFIXES)
PREVIEW_SUFFIXES = (
    "frontend-runtime.json",
    "ui-review.md",
    "ui-review.json",
    "ui-contract.json",
    "ui-contract-alignment.json",
)
IMPLEMENT_STAGES = {"backend", "build_fullstack", "polish", "quality", "delivery"}
SPEC_INTENT = "dsh_primary_spec_intent"


class UnownedSessionError(ValueError):
    """The current task is definitively bound to a different origin."""


def _state(project: Path) -> dict[str, Any] | None:
    store = StateStore(project)
    raw = _read_file(store.workflow_path)
    if raw is None:
        ensure_plain_path(store.history_dir)
        if store.history_dir.exists():
            raise ValueError("主状态缺失；请在 Core 中核对恢复，不使用历史任务代替。")
        return None
    payload = json.loads(raw)
    if (
        not isinstance(payload, dict)
        or type(payload.get("revision")) is not int
        or payload["revision"] <= 0
    ):
        raise ValueError("主状态无效；不会创建替代任务。")
    return payload


def _bound(
    project: Path, state: dict[str, Any], mode: str, session: str, expected_item: str
) -> str:
    owner = state.get("dsh_primary_binding")
    item = state.get("work_item_id")
    if (
        not isinstance(owner, dict)
        or owner.get("protocol") != PROTOCOL
        or owner.get("session_id") != session
    ):
        raise UnownedSessionError("当前项目的任务不属于这个 DSH 会话；没有替换原任务。")
    if (
        owner.get("work_item_id") != item
        or state.get("flow_variant") != mode
        or not isinstance(item, str)
        or not re.fullmatch(r"dsh-[0-9a-f]{20}", item)
        or (expected_item and item != expected_item)
    ):
        raise ValueError("当前项目的任务不属于这个 DSH 会话或模式；没有替换原任务。")
    ensure_plain_path(project / ".super-dev" / "changes" / item)
    identity = resolve_work_item_identity(project)
    if identity.legacy or not identity.valid or identity.work_item_id != item:
        raise ValueError("当前任务的 Core 身份或变更绑定无效。")
    return item


def _summary(project: Path, item: str, mode: str) -> dict[str, Any]:
    # Only the artifacts used by the explicit work item are permitted to supply approvals.
    for name in (*OUTPUT_SUFFIXES, *PREVIEW_SUFFIXES):
        ensure_plain_path(project / "output" / f"{item}-{name}")
    for name in ("proposal.md", "tasks.md", "design.md", "review.md", "adoption.md"):
        ensure_plain_path(project / ".super-dev" / "changes" / item / name)
    for name in (
        "baseline-confirmation.json",
        "document-confirmation.json",
        "preview-confirmation.json",
        "resume-gate.json",
        "ui-revision.json",
        "architecture-revision.json",
        "quality-revision.json",
        "stage-ledger.json",
    ):
        ensure_plain_path(project / ".super-dev" / "review-state" / name)
    summary = detect_pipeline_summary(project)
    if summary.get("artifact_prefix") != item or summary.get("flow_variant") != mode:
        raise ValueError("Core 解析出的工作项或模式不匹配。")
    health = summary.get("workflow_health")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise ValueError("当前 Core 状态不可验证。")
    return summary


def _digest(gate: dict[str, Any]) -> str:
    binding = gate["artifact_binding"]
    key = "preview_target_digest" if binding.get("preview_target_schema_version") == 1 else "digest"
    return str(binding.get(key) or "")


def _result(project: Path, item: str, mode: str, summary: dict[str, Any]) -> dict[str, Any]:
    stage = summary["current_stage_canonical_id"]
    docs = summary["docs_gate"]
    preview = summary["preview_gate"]
    policy = "wait"
    artifact_suffixes: tuple[str, ...] = ()
    baseline_digest = ""
    if stage == "baseline":
        if summary.get("workflow_status") == "missing_baseline":
            policy, artifact_suffixes = "draft", BASELINE_SUFFIXES
        elif summary.get("workflow_status") == "waiting_baseline_confirmation":
            baseline_digest = str(collect_baseline_artifact_binding(project, item)["digest"])
    elif stage == "research":
        policy, artifact_suffixes = "draft", ("research.md",)
    elif stage == "docs" and not docs.get("core_complete"):
        policy, artifact_suffixes = "draft", DOC_SUFFIXES
    elif stage in {"frontend", *IMPLEMENT_STAGES}:
        require_docs_confirmation(
            project,
            action="native DSH implementation",
            requested_phases=["spec"],
            require_context=False,
        )
        if stage == "frontend" and mode == "standard":
            policy = "frontend"
        else:
            require_preview_confirmation(
                project,
                action="native DSH implementation",
                requested_phases=[stage],
                require_context=False,
            )
            policy = "implement"
    return {
        "ok": True,
        "protocol": PROTOCOL,
        "item": item,
        "mode": mode,
        "stage": stage,
        "policy": policy,
        "baseline_digest": baseline_digest,
        "docs_digest": _digest(docs) if docs.get("core_complete") else "",
        "preview_digest": (
            _digest(preview) if preview.get("required") and preview.get("runtime_ready") else ""
        ),
        "artifacts": [f"output/{item}-{name}" for name in artifact_suffixes],
    }


def _spec_identity(item: str, session: str, summary: dict[str, Any]) -> dict[str, str]:
    return {"item": item, "session": session, "docs_digest": _digest(summary["docs_gate"])}


def _spec_intent_matches(project: Path, item: str, session: str, summary: dict[str, Any]) -> bool:
    current = _state(project)
    return current is not None and current.get(SPEC_INTENT) == _spec_identity(
        item, session, summary
    )


def _create_or_resume_spec(
    project: Path, item: str, session: str, summary: dict[str, Any], *, resume: bool
) -> None:
    change = project / ".super-dev" / "changes" / item
    intent = _spec_identity(item, session, summary)
    state = _state(project)
    if not state or _bound(project, state, str(state.get("flow_variant")), session, item) != item:
        raise ValueError("当前 Spec 不属于这个会话。")
    if not resume:
        if state.get(SPEC_INTENT) is not None or change.exists():
            raise ValueError("已有 Spec 尝试的绑定不符；不会自动覆盖或接管。")
        save_workflow_state(
            project, {**state, SPEC_INTENT: intent}, expected_revision=state["revision"]
        )
    elif state.get(SPEC_INTENT) != intent:
        raise ValueError("Spec 的工作项或已确认文档已改变。")

    # An intent is durable before the public generator can write the directory.
    # Preserve every complete existing file; an unknown directory is never adopted.
    for relative in (
        "change.yaml",
        "proposal.md",
        "tasks.md",
        "plan.md",
        "checklist.md",
        f"specs/{item}/spec.md",
    ):
        ensure_plain_path(change / relative)
    generator = SpecGenerator(project)
    title = f"DSH {item}"
    description = "依据此工作项已确认的三份文档编制。"
    proposal = change / "proposal.md"
    if not proposal.exists():
        if change.exists() and any(change.iterdir()):
            raise ValueError("首次生成的提案缺失，已有文件需要人工核对；不会覆盖。")
        generator.create_change(change_id=item, title=title, description=description)
    elif not proposal.is_file() or not _read_file(proposal):
        raise ValueError("中断后已有提案不完整，需要人工核对。")
    generator.scaffold_change_artifacts(item, force=False)
    require_spec_work_item_binding(project, item)
    saved = bind_dsh_primary_work_item(project, item, session_id=session)
    if SPEC_INTENT in saved:
        save_workflow_state(
            project,
            {k: v for k, v in saved.items() if k != SPEC_INTENT},
            expected_revision=saved["revision"],
        )


def apply_request(request: dict[str, Any]) -> dict[str, Any]:
    if set(request) - {"op", "project", "session", "mode", "item", "digest"}:
        raise ValueError("不支持的 Core 桥参数。")
    op = request.get("op")
    mode, session = request.get("mode"), request.get("session")
    expected_item, digest = request.get("item", ""), request.get("digest", "")
    if (
        not isinstance(op, str)
        or op not in OPS
        or mode not in ("standard", "seeai")
        or not isinstance(session, str)
        or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", session)
        or not isinstance(expected_item, str)
        or not isinstance(digest, str)
        or not isinstance(request.get("project"), str)
    ):
        raise ValueError("无效的 DSH 会话请求。")
    project = _local_project(Path(request["project"]))
    for relative in (
        ".super-dev",
        ".super-dev/review-state",
        ".super-dev/workflow-history",
        "output",
        "super-dev.yaml",
    ):
        ensure_plain_path(project / relative)

    state = _state(project)
    if state is None:
        if op != "start" or expected_item:
            raise ValueError("没有已绑定的工作项。")
        state = start_dsh_primary_work_item(
            project, f"dsh-{uuid.uuid4().hex[:20]}", flow_variant=mode, session_id=session
        )
    item = _bound(project, state, mode, session, expected_item)
    if op not in {"start", "inspect", "instructions"} and not expected_item:
        raise ValueError("操作必须显式绑定到当前任务。")
    summary = _summary(project, item, mode)
    stage = summary["current_stage_canonical_id"]

    if op in {"confirm-baseline", "confirm-docs", "confirm-preview"}:
        if not re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", digest):
            raise ValueError("请先查看当前产物，再在原生命令中提供该版本的完整摘要。")
        target = (item, session, digest)
        payload = {"status": "confirmed", "actor": "user", "comment": "DSH native confirmation"}
        if op == "confirm-baseline":
            if (
                stage != "baseline"
                or summary.get("workflow_status") != "waiting_baseline_confirmation"
            ):
                raise ValueError("当前阶段不在基线确认门。")
            save_bound_dsh_baseline_confirmation(project, payload, expected_binding=target)
        elif op == "confirm-docs":
            if stage != "docs_confirm":
                raise ValueError("当前阶段不在文档确认门。")
            save_bound_docs_confirmation(project, payload, expected_binding=target)
        else:
            if stage != "preview_confirm" or not summary["preview_gate"].get("required"):
                raise ValueError("当前阶段不在适用的预览确认门。")
            require_docs_confirmation(
                project,
                action="native DSH preview",
                requested_phases=["frontend"],
                require_context=False,
            )
            save_bound_preview_confirmation(project, payload, expected_binding=target)
        summary = _summary(project, item, mode)
    elif op == "spec":
        if stage != "spec":
            raise ValueError("Core 当前未要求创建 Spec。")
        require_docs_confirmation(
            project, action="native DSH Spec", requested_phases=["spec"], require_context=False
        )
        require_spec_work_item_binding(project, item)
        owns_attempt = _spec_intent_matches(project, item, session, summary)
        if (project / ".super-dev" / "changes" / item).exists() and not owns_attempt:
            raise ValueError("当前任务已存在变更目录；不会自动覆盖或接管。")
        _create_or_resume_spec(project, item, session, summary, resume=owns_attempt)
        summary = _summary(project, item, mode)

    result = _result(project, item, mode, summary)
    if op in {"start", "instructions", "spec"}:
        name = "super-dev-seeai" if mode == "seeai" else "super-dev"
        result["instructions"] = SkillTemplate.for_builtin(
            name, "deepseek-harness"
        ).content.render_dsh_plugin_body()
    return result


def _restrict_worker(root: Path, *, writable: bool) -> None:
    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event.startswith("socket.") or event in {
            "subprocess.Popen",
            "os.system",
            "os.startfile",
            "os.startfile/2",
            "os.exec",
        }:
            raise PermissionError("Core bridge is local only")
        locations: tuple[Any, ...] = ()
        if event == "open":
            name, mode, flags = args
            if (mode and set(mode) & set("wax+")) or flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            ):
                # Core opens a checked temporary path, then wraps that already
                # opened descriptor with fdopen. No files are passed by the caller.
                if writable and type(name) is int and name > 2:
                    return
                locations = (name,)
        elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.utime"}:
            locations = args[:1]
        elif event == "os.rename":
            locations = args[:2]
        for location in locations:
            if not isinstance(location, (str, bytes, os.PathLike)) or not writable:
                raise PermissionError("Core bridge does not authorize that write")
            path = Path(os.path.abspath(os.fsdecode(location)))
            if not path.is_relative_to(root):
                raise PermissionError("Core bridge does not authorize an external write")
            ensure_plain_path(path)

    sys.addaudithook(audit)


def main() -> int:
    try:
        if (
            not sys.flags.isolated
            or not sys.dont_write_bytecode
            or len(sys.argv) != 2
            or len(sys.argv[1]) > 4096
        ):
            raise ValueError("无效的 Core 调用。")
        payload = json.loads(sys.argv[1])
        if not isinstance(payload, dict) or not isinstance(payload.get("project"), str):
            raise ValueError("无效的项目请求。")
        project = _local_project(Path(payload["project"]))
        _restrict_worker(
            project,
            writable=payload.get("op")
            in ("start", "confirm-baseline", "confirm-docs", "confirm-preview", "spec"),
        )
        result = apply_request(payload)
    except UnownedSessionError:
        result = {"ok": False, "protocol": PROTOCOL, "binding": "unowned"}
    except (OSError, ValueError, RuntimeError) as error:
        safe = (
            str(error)
            if isinstance(error, WorkflowGateError)
            else "当前 DSH 会话或 Core 权威状态不可验证。"
        )
        result = {"ok": False, "protocol": PROTOCOL, "reason": safe}
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
