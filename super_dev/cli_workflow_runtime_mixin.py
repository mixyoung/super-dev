"""Workflow and session-continuity commands for the CLI."""

import argparse
import importlib.util
import json
import subprocess as _subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast

from super_dev.artifact_utils import ui_contract_filename

from . import __version__
from .artifact_utils import resolve_active_change_id, resolve_current_artifact_prefix
from .baseline_governance import inspect_baseline_governance
from .catalogs import (
    CICD_PLATFORM_IDS,
    DOMAIN_IDS,
    FULL_FRONTEND_TEMPLATE_IDS,
    HOST_TOOL_IDS,
    PIPELINE_BACKEND_IDS,
    PIPELINE_FRONTEND_TEMPLATE_IDS,
    PLATFORM_IDS,
    PRIMARY_HOST_TOOL_IDS,
    PRODUCT_HOST_TOOL_IDS,
    SPECIAL_INSTALL_HOST_TOOL_IDS,
    host_display_name,
)
from .catalogs import (
    host_path_candidates as _host_path_candidates,
)
from .config import get_config_manager
from .harness_registry import derive_operational_focus, summarize_operational_harnesses
from .hooks.manager import HookManager
from .host_workflow_context import build_host_workflow_context
from .review_state import (
    architecture_revision_file,
    baseline_confirmation_file,
    describe_workflow_event,
    docs_confirmation_file,
    latest_workflow_snapshot_file,
    load_architecture_revision,
    load_baseline_confirmation,
    load_docs_confirmation,
    load_preview_confirmation,
    load_quality_revision,
    load_recent_operational_timeline,
    load_recent_workflow_events,
    load_recent_workflow_snapshots,
    load_ui_revision,
    load_workflow_state,
    preview_confirmation_file,
    quality_revision_file,
    save_architecture_revision,
    save_baseline_confirmation,
    save_docs_confirmation,
    save_preview_confirmation,
    save_quality_revision,
    save_ui_revision,
    save_workflow_state,
    ui_revision_file,
    workflow_event_log_file,
    workflow_state_file,
)
from .shadow_ledger_store import build_shadow_ledger_summary
from .workflow_guard import (
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)
from .workflow_state import (
    build_host_entry_prompts,
    detect_pipeline_summary,
    load_framework_playbook_summary,
    workflow_continuity_rules,
    workflow_mode_label,
    workflow_mode_shortcuts,
)

RICH_AVAILABLE = importlib.util.find_spec("rich") is not None
host_path_candidates = _host_path_candidates
subprocess = _subprocess

CICDPlatform = Literal["github", "gitlab", "jenkins", "azure", "bitbucket", "all"]

SUPPORTED_PLATFORMS = list(PLATFORM_IDS)
SUPPORTED_PIPELINE_FRONTENDS = list(PIPELINE_FRONTEND_TEMPLATE_IDS)
SUPPORTED_INIT_FRONTENDS = list(FULL_FRONTEND_TEMPLATE_IDS)
SUPPORTED_PIPELINE_BACKENDS = list(PIPELINE_BACKEND_IDS)
SUPPORTED_DOMAINS = list(DOMAIN_IDS)
SUPPORTED_CICD = list(CICD_PLATFORM_IDS)
SUPPORTED_HOST_TOOLS = list(HOST_TOOL_IDS)
PRIMARY_SUPPORTED_HOST_TOOLS = list(PRIMARY_HOST_TOOL_IDS)
PRODUCT_SUPPORTED_HOST_TOOLS = list(PRODUCT_HOST_TOOL_IDS)
SPECIAL_INSTALL_HOST_TOOLS = list(SPECIAL_INSTALL_HOST_TOOL_IDS)


def _dict_value(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _list_value(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


class CliWorkflowRuntimeMixin:
    def _cmd_review(self, args) -> int:
        """查看或更新评审状态"""
        payload: dict[str, Any]
        review_specs = {
            "baseline": {
                "title": "当前项目基线确认状态",
                "load": load_baseline_confirmation,
                "save": save_baseline_confirmation,
                "file": baseline_confirmation_file,
                "type": "baseline",
            },
            "docs": {
                "title": "三文档确认状态",
                "load": load_docs_confirmation,
                "save": save_docs_confirmation,
                "file": docs_confirmation_file,
                "type": "docs",
            },
            "ui": {
                "title": "UI 改版状态",
                "load": load_ui_revision,
                "save": save_ui_revision,
                "file": ui_revision_file,
                "type": "ui",
            },
            "preview": {
                "title": "前端预览确认状态",
                "load": load_preview_confirmation,
                "save": save_preview_confirmation,
                "file": preview_confirmation_file,
                "type": "preview",
            },
            "architecture": {
                "title": "架构返工状态",
                "load": load_architecture_revision,
                "save": save_architecture_revision,
                "file": architecture_revision_file,
                "type": "architecture",
            },
            "quality": {
                "title": "质量返工状态",
                "load": load_quality_revision,
                "save": save_quality_revision,
                "file": quality_revision_file,
                "type": "quality",
            },
        }
        if args.review_command not in review_specs:
            self.console.print(
                "[yellow]请指定 review 子命令，例如 `super-dev review baseline`、`super-dev review docs`、`super-dev review preview`、`super-dev review ui`、`super-dev review architecture` 或 `super-dev review quality`[/yellow]"
            )
            return 1

        project_dir = Path.cwd()
        spec = review_specs[args.review_command]
        review_type = str(spec["type"])
        current = cast(Callable[[Path], dict[str, Any] | None], spec["load"])(project_dir) or {}
        state_file = cast(Callable[[Path], Path], spec["file"])(project_dir)
        title = str(spec["title"])

        if review_type == "baseline" and getattr(args, "prepare", False):
            if args.status:
                self.console.print(
                    "[red]`super-dev review baseline --prepare` 不能与 `--status` 同时使用。[/red]"
                )
                return 1
            from .analyzer import BaselineAuditBuilder

            builder = BaselineAuditBuilder(project_dir)
            report = builder.build()
            files = builder.write(report)
            payload = {
                "status": "prepared",
                "project_name": report.project_name,
                "work_mode": report.work_mode,
                "work_mode_label": report.work_mode_label,
                "summary": report.summary,
                "file_path": str(files["markdown"]),
                "json_file_path": str(files["json"]),
                "next_host_action": "回到宿主里说“baseline 确认，可以继续当前流程”",
            }
            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            else:
                self.console.print("[cyan]基线审查草稿已生成[/cyan]")
                self.console.print(f"  模式: {report.work_mode} ({report.work_mode_label})")
                self.console.print(f"  摘要: {report.summary}")
                self.console.print(f"  Markdown: {files['markdown']}")
                self.console.print(f"  JSON: {files['json']}")
                self.console.print("  下一步: 回到宿主里说“基线确认，可以继续当前流程”")
            return 0

        if not args.status:
            payload = {
                "status": str(current.get("status", "")).strip() or "pending_review",
                "comment": str(current.get("comment", "")).strip(),
                "actor": str(current.get("actor", "")).strip(),
                "run_id": str(current.get("run_id", "")).strip(),
                "updated_at": str(current.get("updated_at", "")).strip(),
                "exists": bool(current),
                "file_path": str(state_file),
            }
            if review_type == "baseline":
                baseline_governance = inspect_baseline_governance(project_dir)
                payload["baseline_governance"] = baseline_governance
            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            else:
                self.console.print(f"[cyan]{title}[/cyan]")
                self.console.print(
                    f"  状态: {self._review_status_label(payload['status'], review_type=review_type)}"
                )
                self.console.print(f"  备注: {payload['comment'] or '-'}")
                self.console.print(f"  操作者: {payload['actor'] or '-'}")
                self.console.print(f"  关联运行编号: {payload['run_id'] or '-'}")
                self.console.print(f"  更新时间: {payload['updated_at'] or '-'}")
                self.console.print(
                    f"  文件: {payload['file_path']}",
                    markup=False,
                    soft_wrap=True,
                )
                if review_type == "baseline":
                    baseline_governance = cast(dict[str, Any], payload["baseline_governance"])
                    self.console.print(
                        f"  基线审查: {baseline_governance.get('audit_path') or '-'}"
                    )
                    self.console.print(f"  进入条件: {baseline_governance.get('entry_gate', '-')}")
                    self.console.print(
                        f"  下一步: {baseline_governance.get('next_host_action', '-')}"
                    )
            return 0

        save_fn = cast(Callable[[Path, dict[str, Any]], Path], spec["save"])
        load_fn = cast(Callable[[Path], dict[str, Any] | None], spec["load"])
        review_payload = {
            "status": args.status,
            "comment": args.comment.strip(),
            "actor": args.actor.strip() or "user",
            "run_id": args.run_id.strip(),
        }
        if review_type == "docs" and args.status == "confirmed":
            file_path, _ = save_bound_docs_confirmation(project_dir, review_payload)
        elif review_type == "preview" and args.status == "confirmed":
            file_path, _ = save_bound_preview_confirmation(project_dir, review_payload)
        else:
            file_path = save_fn(project_dir, review_payload)
        payload = load_fn(project_dir) or {}
        self._write_session_brief(
            project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
        )
        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        else:
            if review_type == "ui":
                action = (
                    "已确认 UI 改版通过"
                    if args.status == "confirmed"
                    else (
                        "已记录 UI 改版请求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            elif review_type == "preview":
                action = (
                    "已确认前端预览通过"
                    if args.status == "confirmed"
                    else (
                        "已记录预览返工请求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            elif review_type == "architecture":
                action = (
                    "已确认架构返工通过"
                    if args.status == "confirmed"
                    else (
                        "已记录架构返工请求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            elif review_type == "quality":
                action = (
                    "已确认质量返工通过"
                    if args.status == "confirmed"
                    else (
                        "已记录质量返工请求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            else:
                action = (
                    "已确认三文档"
                    if args.status == "confirmed"
                    else (
                        "已记录文档修改要求"
                        if args.status == "revision_requested"
                        else "已重置为待确认"
                    )
                )
            self.console.print(f"[green]✓[/green] {action}")
            self.console.print(
                f"  状态: {self._review_status_label(args.status, review_type=review_type)}"
            )
            self.console.print(f"  备注: {payload.get('comment', '') or '-'}")
            self.console.print(f"  操作者: {payload.get('actor', '') or '-'}")
            self.console.print(f"  关联运行编号: {payload.get('run_id', '') or '-'}")
            self.console.print(f"  文件: {file_path}")
            if review_type == "ui" and args.status == "revision_requested":
                self.console.print(
                    "[dim]下一步: 先更新 output/*-uiux.md，再重做前端，并重新执行 frontend runtime 与 UI review[/dim]"
                )
            elif review_type == "preview" and args.status == "revision_requested":
                self.console.print(
                    "[dim]下一步: 继续修改前端预览，重新生成 frontend runtime 与预览页，再次提交预览确认[/dim]"
                )
            elif review_type == "architecture" and args.status == "revision_requested":
                self.console.print(
                    "[dim]下一步: 先更新 output/*-architecture.md，再调整技术方案与实现，并重新通过相关质量门禁[/dim]"
                )
            elif review_type == "quality" and args.status == "revision_requested":
                self.console.print(
                    "[dim]下一步: 先修复质量/安全问题，重新执行 quality gate，并刷新交付证据后再继续后续动作[/dim]"
                )
        return 0

        return 0

    def _cmd_run(self, args) -> int:
        """跳转到任意环节执行/重做（支持名称或数字 1-9）"""
        if getattr(args, "status", False):
            return self._cmd_run_status(args)

        if getattr(args, "resume", False):
            return self._cmd_run_resume(args)

        confirm_phase = str(getattr(args, "confirm_phase", "") or "").strip()
        if confirm_phase:
            return self._cmd_run_confirm_phase(
                phase_name=confirm_phase,
                comment=str(getattr(args, "comment", "") or ""),
                actor=str(getattr(args, "actor", "") or "cli-user"),
            )
        jump_stage = str(getattr(args, "jump", "") or "").strip()
        if jump_stage:
            return self._cmd_run_from_stage(stage_selector=jump_stage, show_impact=True)
        phase_stage = str(getattr(args, "phase", "") or "").strip()
        if phase_stage:
            return self._cmd_run_from_stage(stage_selector=phase_stage, show_impact=False)

        stage_selector = str(getattr(args, "stage_selector", "") or "").strip()

        # 数字映射：super-dev run 1 → research, super-dev run 4 → uiux
        if stage_selector in self.STAGE_NUMBER_MAP:
            stage_selector = self.STAGE_NUMBER_MAP[stage_selector]

        if stage_selector:
            normalized = stage_selector.lower()
            label = self.STAGE_LABELS.get(normalized, normalized)

            # 专家角色映射
            expert_map = {
                "research": ("PM + ARCHITECT", "产品经理 + 架构师"),
                "prd": ("PM", "产品经理"),
                "architecture": ("ARCHITECT", "架构师"),
                "uiux": ("UI + UX", "UI/UX 设计师"),
                "spec": ("PM + CODE", "产品经理 + 代码专家"),
                "frontend": ("CODE + UI", "代码专家 + UI 设计师"),
                "backend": ("CODE + DBA", "代码专家 + 数据库专家"),
                "quality": ("QA + SECURITY", "QA 专家 + 安全专家"),
                "delivery": ("DEVOPS + QA", "DevOps + QA 专家"),
            }
            expert_role, expert_title = expert_map.get(normalized, ("CODE", "代码专家"))

            self.console.print("")
            if RICH_AVAILABLE:
                from rich.panel import Panel

                self.console.print(
                    Panel(
                        f"[bold cyan]Super Dev Run[/bold cyan]\n\n"
                        f"  [dim]环节[/dim]    {normalized} ({label})\n"
                        f"  [dim]专家[/dim]    [bold]{expert_role}[/bold] - {expert_title}",
                        border_style="cyan",
                        expand=True,
                        padding=(1, 2),
                    )
                )
            else:
                self.console.print(
                    f"Super Dev Run: {normalized} ({label}) | {expert_role} - {expert_title}"
                )
            self.console.print("")

            if normalized in {"research", "prd", "architecture", "uiux"}:
                return self._cmd_run_targeted_refresh(normalized)
            return self._cmd_run_from_stage(stage_selector=normalized, show_impact=False)

        # 没有指定阶段，显示环节菜单
        from rich.panel import Panel
        from rich.table import Table

        self.console.print("")
        table = Table(title="可用环节", expand=True, border_style="dim", title_style="bold cyan")
        table.add_column("编号", style="bold cyan", min_width=4, max_width=6, justify="center")
        table.add_column("专家", style="bold", min_width=12, ratio=1)
        table.add_column("环节", style="bold", ratio=1)
        table.add_column("说明", style="dim", ratio=3, overflow="fold")

        expert_short = {
            "research": "PM + ARCHITECT",
            "prd": "PM",
            "architecture": "ARCHITECT",
            "uiux": "UI + UX",
            "spec": "PM + CODE",
            "frontend": "CODE + UI",
            "backend": "CODE + DBA",
            "quality": "QA + SECURITY",
            "delivery": "DEVOPS + QA",
        }
        for num, name in sorted(self.STAGE_NUMBER_MAP.items()):
            table.add_row(num, expert_short.get(name, ""), name, self.STAGE_LABELS.get(name, ""))
        self.console.print(table)
        self.console.print("")
        self.console.print("[cyan]用法示例:[/cyan]")
        self.console.print("  super-dev run 4          UI/UX 设计师重新生成设计文档")
        self.console.print("  super-dev run uiux       同上")
        self.console.print("  super-dev run --resume   从上次中断处继续")
        self.console.print("  super-dev run --status   查看流程状态")
        self.console.print("")
        return 0

    def _cmd_status(self, args) -> int:
        """快捷别名：查看当前流程状态"""
        return self._cmd_run_status(args)

    def _cmd_next(self, args) -> int:
        """统一的下一步路由入口"""
        project_dir = Path.cwd()
        payload = self._build_next_step_payload(project_dir)
        self._write_session_brief(project_dir=project_dir, payload=payload)
        payload = dict(payload)
        payload["recent_snapshots"] = load_recent_workflow_snapshots(project_dir, limit=3)
        if getattr(args, "json", False):
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        self._render_next_step_payload(payload, title="Super Dev Next")
        return 0

    def _cmd_continue(self, args) -> int:
        """更自然的继续入口"""
        project_dir = Path.cwd()
        payload = self._build_next_step_payload(project_dir)
        self._write_session_brief(project_dir=project_dir, payload=payload)
        payload = dict(payload)
        payload["recent_snapshots"] = load_recent_workflow_snapshots(project_dir, limit=3)
        if getattr(args, "json", False):
            payload["entrypoint"] = "continue"
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        self._render_next_step_payload(payload, title="Super Dev Continue")
        return 0

    def _cmd_resume(self, args) -> int:
        """更符合真实恢复场景的继续入口"""
        project_dir = Path.cwd()
        payload = self._build_next_step_payload(project_dir)
        self._write_session_brief(project_dir=project_dir, payload=payload)
        payload = dict(payload)
        payload["recent_snapshots"] = load_recent_workflow_snapshots(project_dir, limit=3)
        if getattr(args, "json", False):
            payload["entrypoint"] = "resume"
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        self._render_next_step_payload(payload, title="Super Dev Resume")
        return 0

    def _render_next_step_payload(self, payload: dict[str, Any], *, title: str) -> None:
        action_card = _dict_value(payload.get("action_card"))
        self.console.print(f"[cyan]{title}[/cyan]")
        workflow_mode = str(payload.get("workflow_mode", "")).strip()
        if workflow_mode:
            self.console.print(f"  动作类型: {self._workflow_mode_label(workflow_mode)}")
        self.console.print(
            f"  当前步骤: {payload.get('current_step_label', payload.get('status', '-'))}"
        )
        self.console.print(
            f"  用户下一步: {payload.get('user_next_action', payload.get('recommended_command', '-'))}"
        )
        user_action_shortcuts = (
            payload.get("user_action_shortcuts")
            if isinstance(payload.get("user_action_shortcuts"), list)
            else []
        )
        if user_action_shortcuts:
            self.console.print(
                f"  你现在可以直接说: {' / '.join(str(item) for item in user_action_shortcuts[:4])}"
            )
        preferred_host_name = str(payload.get("preferred_host_name", "")).strip()
        host_continue_prompt = str(payload.get("host_continue_prompt", "")).strip()
        if preferred_host_name and host_continue_prompt:
            self.console.print(f"  宿主第一句 ({preferred_host_name}): {host_continue_prompt}")
        host_entry_prompts = _dict_value(payload.get("host_continue_entry_prompts"))
        host_entry_labels = _dict_value(payload.get("host_continue_entry_labels"))
        if host_entry_prompts:
            preferred_entry_label = str(
                payload.get("host_continue_preferred_entry_label", "")
            ).strip()
            if preferred_entry_label:
                self.console.print(f"  推荐入口: {preferred_entry_label}")
            for key, prompt in host_entry_prompts.items():
                prompt_text = str(prompt).strip()
                if not prompt_text:
                    continue
                label = str(host_entry_labels.get(key, key)).strip() or key
                suffix = "恢复入口" if key != "fallback" else "回退恢复入口"
                self.console.print(f"  {label} {suffix}: {prompt_text}")
        self.console.print(f"  系统建议动作: {payload.get('recommended_command', '-')}")
        examples = (
            action_card.get("examples") if isinstance(action_card.get("examples"), list) else []
        )
        if examples:
            self.console.print(f"  自然语言示例: {', '.join(str(item) for item in examples[:3])}")
        scenario_cards = _list_value(payload.get("scenario_cards"))
        for item in scenario_cards[:4]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            command = str(item.get("cli_command", "")).strip()
            if title and command:
                self.console.print(f"  真实场景: {title} -> {command}")
        self.console.print(f"  当前状态: {payload.get('status', '-')}")
        self.console.print(f"  原因: {payload.get('reason', '-')}")
        if payload.get("session_brief_path"):
            self.console.print(f"  流程状态卡: {payload.get('session_brief_path')}")
        recent_snapshots = (
            payload.get("recent_snapshots")
            if isinstance(payload.get("recent_snapshots"), list)
            else []
        )
        if recent_snapshots and isinstance(recent_snapshots[0], dict):
            first = recent_snapshots[0]
            step = (
                str(first.get("current_step_label", "")).strip()
                or str(first.get("status", "")).strip()
            )
            updated_at = str(first.get("updated_at", "")).strip() or "-"
            self.console.print(f"  最近快照: {updated_at} · {step}")
        if payload.get("evidence"):
            self.console.print(f"  依据: {payload['evidence']}")
        shadow_ledger = payload.get("shadow_ledger", {})
        if (
            isinstance(shadow_ledger, dict)
            and shadow_ledger.get("present")
            and str(shadow_ledger.get("summary", "")).strip()
        ):
            self.console.print(
                f"  九阶段影子账本（只读观察，不改变门禁）: {shadow_ledger['summary']}"
            )
            if str(shadow_ledger.get("scope_advisory_summary", "")).strip():
                self.console.print(
                    "  阶段范围建议（只读，缩减必须审批）: "
                    f"{shadow_ledger['scope_advisory_summary']}"
                )

    def _workflow_mode_label(self, workflow_mode: str) -> str:
        return workflow_mode_label(workflow_mode)

    def _workflow_mode_shortcuts(
        self, workflow_mode: str, *, action_card: dict[str, Any] | None = None
    ) -> list[str]:
        if isinstance(action_card, dict):
            raw_shortcuts = action_card.get("shortcuts")
            if isinstance(raw_shortcuts, list):
                shortcuts = [str(item).strip() for item in raw_shortcuts if str(item).strip()]
                if shortcuts:
                    return shortcuts
            raw_examples = action_card.get("examples")
            examples = (
                [str(item).strip() for item in raw_examples if str(item).strip()]
                if isinstance(raw_examples, list)
                else []
            )
        else:
            examples = []
        return workflow_mode_shortcuts(workflow_mode, examples=examples)

    def _cmd_jump(self, args) -> int:
        """快捷别名：跳转到指定阶段"""
        stage = str(getattr(args, "stage", "") or "").strip()
        if not stage:
            self.console.print("[red]请指定目标阶段，例如: super-dev jump frontend[/red]")
            return 1
        return self._cmd_run_from_stage(stage_selector=stage, show_impact=True)

    def _cmd_confirm(self, args) -> int:
        """快捷别名：确认指定阶段"""
        phase_name = str(getattr(args, "phase", "") or "").strip()
        if not phase_name:
            self.console.print("[red]请指定要确认的阶段，例如: super-dev confirm docs[/red]")
            return 1
        return self._cmd_run_confirm_phase(
            phase_name=phase_name,
            comment=str(getattr(args, "comment", "") or ""),
            actor=str(getattr(args, "actor", "") or "cli-user"),
        )

    def _cmd_run_resume(self, args) -> int:
        """恢复最近一次 pipeline 运行"""

        project_dir = Path.cwd()
        run_state = self._read_pipeline_run_state(project_dir)
        if not run_state:
            self.console.print("[red]未找到最近一次 pipeline 运行记录[/red]")
            self.console.print(
                "[dim]请先运行 `super-dev` 完成宿主接入，再在宿主里用 `/super-dev` 或 `super-dev:` 启动流程[/dim]"
            )
            return 1

        status = str(run_state.get("status", "")).strip().lower()
        if status == "success":
            self.console.print("[yellow]最近一次 pipeline 已成功完成，无需恢复[/yellow]")
            return 1
        if status == "waiting_confirmation":
            if not self._docs_confirmation_is_confirmed(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在文档确认门，请先确认三文档后再恢复[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“文档确认，可以继续”[/dim]")
                return 1
            if any(
                (project_dir / "output").glob("*-frontend-runtime.json")
            ) and not self._preview_confirmation_is_confirmed(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 还缺前端预览确认，请先确认预览后再恢复[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“前端预览确认，可以继续”[/dim]")
                return 1
            if not self._ui_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 存在待处理 UI 改版请求，请先完成 UI 返工再恢复[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“UI 改版已完成，继续当前流程”[/dim]")
                return 1
            if not self._architecture_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 存在待处理架构返工请求，请先完成架构修订再恢复[/yellow]"
                )
                self.console.print(
                    "[dim]请回到宿主里明确回复：“架构调整已完成，继续当前流程”[/dim]"
                )
                return 1
            if not self._quality_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 存在待处理质量返工请求，请先完成质量整改再恢复[/yellow]"
                )
                self.console.print(
                    "[dim]请回到宿主里明确回复：“质量整改已完成，继续当前流程”[/dim]"
                )
                return 1
        elif status == "waiting_preview_confirmation":
            if not self._preview_confirmation_is_confirmed(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在前端预览确认门，请先确认预览或继续完成前端返工[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“前端预览确认，可以继续”[/dim]")
                return 1
        elif status == "waiting_ui_revision":
            if not self._ui_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在 UI 改版门，请先完成 UIUX 更新、前端返工与 UI review[/yellow]"
                )
                self.console.print("[dim]请回到宿主里明确回复：“UI 改版已完成，继续当前流程”[/dim]")
                return 1
        elif status == "waiting_architecture_revision":
            if not self._architecture_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在架构返工门，请先完成 output/*-architecture.md 修订和实现同步[/yellow]"
                )
                self.console.print(
                    "[dim]请回到宿主里明确回复：“架构调整已完成，继续当前流程”[/dim]"
                )
                return 1
        elif status == "waiting_quality_revision":
            if not self._quality_revision_is_clear(project_dir):
                self.console.print(
                    "[yellow]最近一次 pipeline 已停在质量返工门，请先完成质量整改并重新执行 quality gate[/yellow]"
                )
                self.console.print(
                    "[dim]请回到宿主里明确回复：“质量整改已完成，继续当前流程”[/dim]"
                )
                return 1
        elif status not in {"failed", "running"}:
            self.console.print("[yellow]最近一次 pipeline 状态不支持恢复[/yellow]")
            return 1

        raw_args = run_state.get("pipeline_args", {})
        if not isinstance(raw_args, dict):
            self.console.print("[red]运行记录损坏：缺少 pipeline 参数[/red]")
            return 1

        pipeline_args = argparse.Namespace(
            description=str(raw_args.get("description", "")).strip(),
            mode=str(raw_args.get("mode", "feature")),
            platform=str(raw_args.get("platform", "web")),
            frontend=str(raw_args.get("frontend", "react")),
            backend=str(raw_args.get("backend", "node")),
            domain=str(raw_args.get("domain", "")),
            name=raw_args.get("name"),
            cicd=str(raw_args.get("cicd", "all")),
            skip_redteam=bool(raw_args.get("skip_redteam", False)),
            skip_scaffold=bool(raw_args.get("skip_scaffold", False)),
            skip_quality_gate=bool(raw_args.get("skip_quality_gate", False)),
            skip_rehearsal_verify=bool(raw_args.get("skip_rehearsal_verify", False)),
            offline=bool(raw_args.get("offline", False)),
            quality_threshold=raw_args.get("quality_threshold"),
            changed_surfaces=raw_args.get("changed_surfaces"),
            governance_depth=raw_args.get("governance_depth"),
            resume=True,
        )

        if not pipeline_args.description:
            self.console.print("[red]运行记录缺少 description，无法恢复[/red]")
            return 1

        if status == "running":
            self.console.print("[yellow]检测到最近一次仍在运行，按中断恢复处理[/yellow]")
        self.console.print("[cyan]恢复最近一次失败/中断的 pipeline 运行...[/cyan]")
        self.console.print(f"[dim]需求: {pipeline_args.description}[/dim]")
        return int(self._cmd_pipeline(pipeline_args))

    def _cmd_run_status(self, args) -> int:
        project_dir = Path.cwd()
        payload: dict[str, Any]
        run_state = self._read_pipeline_run_state(project_dir) or {}
        if not run_state and not self._project_has_super_dev_context(project_dir):
            if getattr(args, "json", False):
                payload = {
                    "status": "not_initialized",
                    "recommended_next": "super-dev init <项目名>",
                }
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                return 0
            self.console.print("[cyan]Super Dev 流程状态: 尚未开始[/cyan]")
            self.console.print("  运行 'super-dev init <项目名>' 初始化项目")
            return 0
        # Initialized (super-dev.yaml exists) but no pipeline run yet
        if not run_state:
            try:
                cfg = get_config_manager(project_dir).config
                recent_snapshots = load_recent_workflow_snapshots(project_dir, limit=3)
                if not recent_snapshots:
                    current_snapshot = load_workflow_state(project_dir)
                    if isinstance(current_snapshot, dict) and current_snapshot:
                        recent_snapshots = [current_snapshot]
                if not recent_snapshots:
                    pipeline_summary = detect_pipeline_summary(
                        project_dir, include_shadow_ledger=True
                    )
                    if isinstance(pipeline_summary, dict) and pipeline_summary:
                        recent_snapshots = [pipeline_summary]
                recent_events = load_recent_workflow_events(project_dir, limit=3)
                if not recent_events and recent_snapshots:
                    first_snapshot = (
                        recent_snapshots[0] if isinstance(recent_snapshots[0], dict) else {}
                    )
                    recent_events = [
                        {
                            "event": "workflow_context_detected",
                            "phase": str(first_snapshot.get("workflow_mode", "")).strip()
                            or "continue",
                            "timestamp": str(first_snapshot.get("updated_at", "")).strip()
                            or datetime.now(timezone.utc).isoformat(),
                            "status": str(first_snapshot.get("status", "")).strip()
                            or "initialized_waiting",
                            "current_step_label": str(
                                first_snapshot.get("current_step_label", "")
                            ).strip(),
                        }
                    ]
                initialized_payload = {
                    "status": "initialized_waiting",
                    "project": cfg.name or project_dir.name,
                    "frontend": cfg.frontend or "-",
                    "backend": cfg.backend or "-",
                    "recommended_next": "在宿主中输入 /super-dev <你的需求> 开始",
                    "framework_playbook": load_framework_playbook_summary(project_dir),
                    "recent_snapshots": recent_snapshots,
                    "recent_events": recent_events,
                    "recent_hook_events": [
                        item.to_dict()
                        for item in HookManager.load_recent_history(project_dir, limit=3)
                    ],
                    "operational_harnesses": summarize_operational_harnesses(
                        project_dir, write_reports=False
                    ),
                    "operational_focus": derive_operational_focus(project_dir),
                    "shadow_ledger": build_shadow_ledger_summary(project_dir),
                }
                if getattr(args, "json", False):
                    sys.stdout.write(
                        json.dumps(initialized_payload, ensure_ascii=False, indent=2) + "\n"
                    )
                    return 0
                self.console.print("[cyan]Super Dev 流程状态: 已初始化，等待开始[/cyan]")
                self.console.print(f"  项目: {initialized_payload['project']}")
                self.console.print(f"  前端: {initialized_payload['frontend']}")
                self.console.print(f"  后端: {initialized_payload['backend']}")
                framework_playbook = initialized_payload.get("framework_playbook", {})
                if isinstance(framework_playbook, dict) and framework_playbook:
                    self.console.print(f"  跨平台框架: {framework_playbook.get('framework', '-')}")
                rendered_snapshots = _list_value(initialized_payload.get("recent_snapshots"))
                if rendered_snapshots:
                    first = rendered_snapshots[0] if isinstance(rendered_snapshots[0], dict) else {}
                    step = (
                        str(first.get("current_step_label", "")).strip()
                        or str(first.get("status", "")).strip()
                    )
                    updated_at = str(first.get("updated_at", "")).strip() or "-"
                    self.console.print(f"  最近快照: {updated_at} · {step}")
                harnesses = initialized_payload.get("operational_harnesses", [])
                if isinstance(harnesses, list) and harnesses:
                    self.console.print("  运行验证:")
                    for item in harnesses[:3]:
                        if not isinstance(item, dict):
                            continue
                        label = (
                            str(item.get("label", "")).strip() or str(item.get("kind", "")).strip()
                        )
                        passed = bool(item.get("all_passed", False))
                        blocker = str(item.get("first_blocker", "")).strip()
                        line = f"    - {label}: {'ok' if passed else 'needs attention'}"
                        if blocker:
                            line += f" · {blocker}"
                        self.console.print(line)
                focus = initialized_payload.get("operational_focus", {})
                if isinstance(focus, dict) and str(focus.get("summary", "")).strip():
                    self.console.print(f"  当前治理焦点: {focus.get('summary')}")
                shadow_ledger = initialized_payload.get("shadow_ledger", {})
                if (
                    isinstance(shadow_ledger, dict)
                    and shadow_ledger.get("present")
                    and str(shadow_ledger.get("summary", "")).strip()
                ):
                    self.console.print(
                        f"  九阶段影子账本（只读观察，不改变门禁）: {shadow_ledger['summary']}"
                    )
                    if str(shadow_ledger.get("scope_advisory_summary", "")).strip():
                        self.console.print(
                            "  阶段范围建议（只读，缩减必须审批）: "
                            f"{shadow_ledger['scope_advisory_summary']}"
                        )
                self.console.print("")
                self.console.print("  下一步: 在宿主中输入 /super-dev <你的需求> 开始")
                return 0
            except Exception:
                pass
        docs_state = self._get_docs_confirmation_state(project_dir)
        preview_state = self._get_preview_confirmation_state(project_dir)
        ui_state = self._get_ui_revision_state(project_dir)
        architecture_state = self._get_architecture_revision_state(project_dir)
        quality_state = self._get_quality_revision_state(project_dir)
        effective_status = self._effective_run_status(
            run_state=run_state,
            docs_state=docs_state,
            ui_state=ui_state,
            architecture_state=architecture_state,
            quality_state=quality_state,
        )
        phase_confirmations = {}
        if isinstance(run_state.get("phase_confirmations"), dict):
            phase_confirmations = dict(run_state.get("phase_confirmations") or {})
        payload = {
            "run_state_exists": bool(run_state),
            "status": effective_status,
            "description": str(
                (run_state.get("pipeline_args") or {}).get("description", "")
            ).strip(),
            "failed_stage": str(run_state.get("failed_stage", "")).strip(),
            "resume_from_stage": str(run_state.get("resume_from_stage", "")).strip(),
            "full_gate_passed": bool(run_state.get("full_gate_passed", False)),
            "skipped_gates": list(run_state.get("skipped_gates") or []),
            "scope_coverage_status": str(run_state.get("scope_coverage_status", "")).strip()
            or "unknown",
            "scope_coverage_rate": run_state.get("scope_coverage_rate"),
            "scope_gap_count": int(run_state.get("scope_gap_count", 0) or 0),
            "scope_high_priority_gap_count": int(
                run_state.get("scope_high_priority_gap_count", 0) or 0
            ),
            "docs_confirmation": docs_state,
            "preview_confirmation": preview_state,
            "ui_revision": ui_state,
            "architecture_revision": architecture_state,
            "quality_revision": quality_state,
            "phase_confirmations": phase_confirmations,
            "recommended_next": self._run_status_recommendation(
                run_state=run_state,
                docs_state=docs_state,
                preview_state=preview_state,
                ui_state=ui_state,
                architecture_state=architecture_state,
                quality_state=quality_state,
            ),
            "framework_playbook": load_framework_playbook_summary(project_dir),
            "recent_snapshots": load_recent_workflow_snapshots(project_dir, limit=3),
            "recent_events": load_recent_workflow_events(project_dir, limit=3),
            "recent_hook_events": [
                item.to_dict() for item in HookManager.load_recent_history(project_dir, limit=3)
            ],
            "operational_harnesses": summarize_operational_harnesses(
                project_dir, write_reports=False
            ),
            "operational_focus": derive_operational_focus(project_dir),
            "shadow_ledger": build_shadow_ledger_summary(project_dir),
        }
        if getattr(args, "json", False):
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0
        self.console.print("[cyan]Super Dev 流程状态[/cyan]")
        self.console.print(f"  运行状态: {payload['status']}")
        self.console.print(f"  当前需求: {payload['description'] or '-'}")
        self.console.print(f"  失败阶段: {payload['failed_stage'] or '-'}")
        self.console.print(f"  恢复起点: {payload['resume_from_stage'] or '-'}")
        self.console.print(f"  全门禁通过: {'是' if payload['full_gate_passed'] else '否'}")
        self.console.print(
            "  跳过门禁: "
            + (", ".join(payload["skipped_gates"]) if payload["skipped_gates"] else "-")
        )
        scope_rate = payload["scope_coverage_rate"]
        scope_rate_text = (
            f"{float(scope_rate):.1f}%" if isinstance(scope_rate, int | float) else "-"
        )
        self.console.print(f"  范围覆盖状态: {payload['scope_coverage_status']}")
        self.console.print(f"  范围覆盖率: {scope_rate_text}")
        self.console.print(f"  范围缺口: {payload['scope_gap_count']}")
        self.console.print(f"  高优先级缺口: {payload['scope_high_priority_gap_count']}")
        self.console.print(f"  文档确认: {self._docs_confirmation_label(docs_state['status'])}")
        self.console.print(
            f"  UI 改版: {self._review_status_label(ui_state['status'], review_type='ui')}"
        )
        self.console.print(
            f"  架构返工: {self._review_status_label(architecture_state['status'], review_type='architecture')}"
        )
        self.console.print(
            f"  质量返工: {self._review_status_label(quality_state['status'], review_type='quality')}"
        )
        framework_playbook = payload.get("framework_playbook", {})
        if isinstance(framework_playbook, dict) and framework_playbook:
            self.console.print(f"  跨平台框架: {framework_playbook.get('framework', '-')}")
            native = framework_playbook.get("native_capabilities", [])
            validation = framework_playbook.get("validation_surfaces", [])
            if native:
                self.console.print(f"  原生能力面: {' / '.join(str(item) for item in native[:3])}")
            if validation:
                self.console.print(
                    f"  必验场景: {' / '.join(str(item) for item in validation[:3])}"
                )
        if phase_confirmations:
            self.console.print("  阶段确认:")
            for phase, item in sorted(phase_confirmations.items()):
                status = str((item or {}).get("status", "")).strip() or "pending_review"
                actor = str((item or {}).get("actor", "")).strip() or "-"
                self.console.print(f"    - {phase}: {self._review_status_label(status)} | {actor}")
        focus = payload.get("operational_focus", {})
        if isinstance(focus, dict) and str(focus.get("summary", "")).strip():
            self.console.print(f"  当前治理焦点: {focus.get('summary')}")
            action = str(focus.get("recommended_action", "")).strip()
            if action:
                self.console.print(f"  建议先做: {action}")
        shadow_ledger = payload.get("shadow_ledger", {})
        if (
            isinstance(shadow_ledger, dict)
            and shadow_ledger.get("present")
            and str(shadow_ledger.get("summary", "")).strip()
        ):
            self.console.print(
                f"  九阶段影子账本（只读观察，不改变门禁）: {shadow_ledger['summary']}"
            )
            if str(shadow_ledger.get("scope_advisory_summary", "")).strip():
                self.console.print(
                    "  阶段范围建议（只读，缩减必须审批）: "
                    f"{shadow_ledger['scope_advisory_summary']}"
                )
        rendered_snapshots = _list_value(payload.get("recent_snapshots"))
        if rendered_snapshots:
            first = rendered_snapshots[0] if isinstance(rendered_snapshots[0], dict) else {}
            step = (
                str(first.get("current_step_label", "")).strip()
                or str(first.get("status", "")).strip()
            )
            updated_at = str(first.get("updated_at", "")).strip() or "-"
            self.console.print(f"  最近快照: {updated_at} · {step}")
        rendered_events = _list_value(payload.get("recent_events"))
        if rendered_events:
            first_event = rendered_events[0] if isinstance(rendered_events[0], dict) else {}
            event_time = str(first_event.get("timestamp", "")).strip() or "-"
            self.console.print(f"  最近事件: {event_time} · {describe_workflow_event(first_event)}")
        rendered_hook_events = _list_value(payload.get("recent_hook_events"))
        if rendered_hook_events:
            first_hook = (
                rendered_hook_events[0] if isinstance(rendered_hook_events[0], dict) else {}
            )
            blocked = bool(first_hook.get("blocked", False))
            success = bool(first_hook.get("success", False))
            hook_status = "blocked" if blocked else ("ok" if success else "failed")
            self.console.print(
                "  最近 Hook: "
                f"{str(first_hook.get('timestamp', '')).strip() or '-'} · "
                f"{str(first_hook.get('event', '')).strip() or '-'} / "
                f"{str(first_hook.get('phase', '')).strip() or '-'} / "
                f"{str(first_hook.get('hook_name', '')).strip() or '-'} / {hook_status}"
            )
        harnesses = payload.get("operational_harnesses", [])
        if isinstance(harnesses, list) and harnesses:
            self.console.print("  运行验证:")
            for item in harnesses[:3]:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label", "")).strip() or str(item.get("kind", "")).strip()
                status = "pass" if item.get("passed") else "fail"
                line = f"    - {label}: {status}"
                blocker = str(item.get("first_blocker", "")).strip()
                if blocker:
                    line += f" | {blocker}"
                self.console.print(line)
        self.console.print(f"  下一步: {payload['recommended_next']}")
        return 0

    def _cmd_run_confirm_phase(self, *, phase_name: str, comment: str, actor: str) -> int:
        project_dir = Path.cwd()
        normalized = phase_name.strip().lower()

        def _persist_phase_confirmation(phase_key: str) -> None:
            run_state = self._read_pipeline_run_state(project_dir) or {}
            phase_confirmations = run_state.get("phase_confirmations")
            if not isinstance(phase_confirmations, dict):
                phase_confirmations = {}
            if not str(run_state.get("status", "")).strip():
                run_state["status"] = "running"
            phase_confirmations[phase_key] = {
                "status": "confirmed",
                "comment": comment or f"{phase_key} 阶段确认通过",
                "actor": actor,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            run_state["phase_confirmations"] = phase_confirmations
            run_state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_pipeline_run_state(project_dir, run_state)

        if normalized in {"docs", "document", "documents"}:
            path, _ = save_bound_docs_confirmation(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "三文档确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation("docs")
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 docs 阶段: {path}")
            return 0
        if normalized in {"preview", "frontend", "frontend-preview"}:
            path, _ = save_bound_preview_confirmation(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "前端预览确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation(normalized)
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 preview 阶段: {path}")
            return 0
        if normalized in {"ui", "frontend-ui"}:
            path = save_ui_revision(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "UI 阶段确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation("ui")
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 ui 阶段: {path}")
            return 0
        if normalized in {"architecture", "arch"}:
            path = save_architecture_revision(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "架构阶段确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation("architecture")
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 architecture 阶段: {path}")
            return 0
        if normalized in {"quality", "qa"}:
            path = save_quality_revision(
                project_dir,
                {
                    "status": "confirmed",
                    "comment": comment or "质量阶段确认通过",
                    "actor": actor,
                    "run_id": "",
                },
            )
            _persist_phase_confirmation("quality")
            self._write_session_brief(
                project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
            )
            self.console.print(f"[green]✓[/green] 已确认 quality 阶段: {path}")
            return 0
        _persist_phase_confirmation(normalized)
        self._write_session_brief(
            project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
        )
        self.console.print(f"[green]✓[/green] 已确认阶段: {normalized}")
        return 0

    def _cmd_run_targeted_refresh(self, target: str) -> int:
        project_dir = Path.cwd()
        config = get_config_manager(project_dir).config
        project_name = self._sanitize_project_name(config.name or project_dir.name)
        output_dir = project_dir / str(config.output_dir or "output")
        output_dir.mkdir(parents=True, exist_ok=True)
        run_state = self._read_pipeline_run_state(project_dir) or {}
        pipeline_args = run_state.get("pipeline_args") if isinstance(run_state, dict) else {}
        if not isinstance(pipeline_args, dict):
            pipeline_args = {}
        description = (
            str(pipeline_args.get("description", "")).strip()
            or str(config.description or "").strip()
            or project_name
        )
        domain = str(pipeline_args.get("domain", "")).strip() or str(config.domain or "")
        frontend = str(
            pipeline_args.get("frontend", "")
        ).strip() or self._normalize_pipeline_frontend(config.frontend)
        backend = str(pipeline_args.get("backend", "")).strip() or str(config.backend or "node")
        request_mode = (
            str((run_state.get("context") or {}).get("request_mode", "")).strip() or "feature"
        )

        if target == "research":
            import os

            from .orchestrator.knowledge import KnowledgeAugmenter

            disable_web = os.getenv("SUPER_DEV_DISABLE_WEB", "").strip().lower() in {
                "1",
                "true",
                "yes",
            }
            augmenter = KnowledgeAugmenter(
                project_dir=project_dir,
                web_enabled=not disable_web,
                allowed_web_domains=config.knowledge_allowed_domains,
                cache_ttl_seconds=config.knowledge_cache_ttl_seconds,
            )
            bundle = augmenter.augment(requirement=description, domain=domain)
            research_file = output_dir / f"{project_name}-research.md"
            research_file.write_text(augmenter.to_markdown(bundle), encoding="utf-8")
            cache_file = augmenter.save_bundle(
                bundle=bundle,
                output_dir=output_dir,
                project_name=project_name,
                requirement=description,
                domain=domain,
            )
            self.console.print(f"[green]✓[/green] 已重跑 research: {research_file}")
            self.console.print(f"[green]✓[/green] 知识缓存: {cache_file}")
            return 0

        from .creators import DocumentGenerator

        knowledge_summary = {}
        bundle_path = output_dir / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"
        if bundle_path.exists():
            try:
                knowledge_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
                if isinstance(knowledge_payload, dict):
                    knowledge_summary = dict(knowledge_payload.get("research_summary") or {})
                    enriched = str(knowledge_payload.get("enriched_requirement", "")).strip()
                    if enriched:
                        description = enriched
            except Exception:
                pass

        generator = DocumentGenerator(
            name=project_name,
            description=description,
            request_mode=request_mode,
            platform=str(config.platform or "web"),
            frontend=frontend,
            backend=backend,
            domain=domain,
            ui_library=config.ui_library,
            style_solution=config.style_solution,
            state_management=list(config.state_management or []),
            testing_frameworks=list(config.testing_frameworks or []),
            design_inspiration_slug=str(getattr(config, "design_inspiration_slug", "") or ""),
            language_preferences=list(config.language_preferences or []),
            knowledge_summary=knowledge_summary,
        )

        target_map = {
            "prd": (
                output_dir / f"{project_name}-prd.md",
                generator.generate_prd,
            ),
            "architecture": (
                output_dir / f"{project_name}-architecture.md",
                generator.generate_architecture,
            ),
            "uiux": (
                output_dir / f"{project_name}-uiux.md",
                generator.generate_uiux,
            ),
        }
        file_path, factory = target_map[target]
        file_path.write_text(factory(), encoding="utf-8")
        if target == "uiux":
            contract_path = output_dir / ui_contract_filename(project_name)
            contract_path.write_text(
                json.dumps(generator.generate_ui_contract(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        self.console.print(f"[green]✓[/green] 已重跑 {target}: {file_path}")
        return 0

    def _cmd_run_from_stage(self, *, stage_selector: str, show_impact: bool) -> int:
        project_dir = Path.cwd()
        run_state = self._read_pipeline_run_state(project_dir)
        if not run_state:
            self.console.print("[red]未找到可恢复运行记录，无法按阶段继续[/red]")
            self.console.print(
                "[dim]请先运行一次 super-dev 完成宿主接入，然后回到宿主里触发 Super Dev 流程。[/dim]"
            )
            return 1
        stage_number = self._resolve_pipeline_stage_selector(stage_selector)
        if stage_number is None:
            self.console.print(f"[red]无法识别阶段: {stage_selector}[/red]")
            self.console.print(
                "[dim]可用阶段: research/docs/spec/frontend/backend/quality/delivery/rehearsal[/dim]"
            )
            return 1
        if show_impact:
            impact_lines = self._stage_jump_impact(stage_number)
            self.console.print(
                f"[cyan]阶段回跳影响分析（目标: {stage_selector} / 第 {stage_number} 阶段）[/cyan]"
            )
            for line in impact_lines:
                self.console.print(f"  - {line}")
        run_state["status"] = "failed"
        run_state["failed_stage"] = str(stage_number)
        run_state["resume_from_stage"] = str(stage_number)
        run_state["next_stage"] = str(stage_number)
        run_state["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_pipeline_run_state(project_dir, run_state)
        self.console.print(f"[cyan]将从第 {stage_number} 阶段继续执行...[/cyan]")
        return self._cmd_run_resume(argparse.Namespace(resume=True))

    def _effective_run_status(
        self,
        *,
        run_state: dict[str, Any],
        docs_state: dict[str, Any],
        ui_state: dict[str, Any],
        architecture_state: dict[str, Any],
        quality_state: dict[str, Any],
    ) -> str:
        explicit_status = str(run_state.get("status", "")).strip().lower()
        if explicit_status:
            return explicit_status

        normalized_status = str(run_state.get("status_normalized", "")).strip().lower()
        if normalized_status and normalized_status != "unknown":
            return normalized_status

        phase_confirmations = run_state.get("phase_confirmations")
        has_phase_confirmations = isinstance(phase_confirmations, dict) and bool(
            phase_confirmations
        )
        review_states = (docs_state, ui_state, architecture_state, quality_state)
        has_review_evidence = any(
            bool(state.get("exists"))
            or str(state.get("status", "")).strip() not in {"", "pending_review"}
            for state in review_states
        )
        if has_phase_confirmations or has_review_evidence:
            return "running"
        return "unknown"

    def _run_status_recommendation(
        self,
        *,
        run_state: dict[str, Any],
        docs_state: dict[str, Any],
        preview_state: dict[str, Any],
        ui_state: dict[str, Any],
        architecture_state: dict[str, Any],
        quality_state: dict[str, Any],
    ) -> str:
        if docs_state.get("status") != "confirmed":
            return "在宿主里确认三文档；如果通过，直接说“文档确认，可以继续”"
        if preview_state.get("status") == "revision_requested":
            return "在宿主里继续修改前端；确认后直接说“前端预览确认，可以继续”"
        if ui_state.get("status") == "revision_requested":
            return "在宿主里完成 UI 改版后直接说“UI 改版已完成，继续当前流程”"
        if architecture_state.get("status") == "revision_requested":
            return "在宿主里完成架构返工后直接说“架构调整已完成，继续当前流程”"
        if quality_state.get("status") == "revision_requested":
            return "在宿主里完成质量整改后直接说“质量整改已完成，继续当前流程”"
        status = self._effective_run_status(
            run_state=run_state,
            docs_state=docs_state,
            ui_state=ui_state,
            architecture_state=architecture_state,
            quality_state=quality_state,
        )
        skipped_gates = list(run_state.get("skipped_gates") or [])
        scope_status = str(run_state.get("scope_coverage_status", "")).strip().lower() or "unknown"
        high_priority_scope_gaps = int(run_state.get("scope_high_priority_gap_count", 0) or 0)
        if scope_status in {"partial", "unknown"} or high_priority_scope_gaps > 0:
            return "在宿主里继续当前流程，并优先补齐缺失范围与高优先级功能项"
        if status == "success" and skipped_gates:
            return "按当前策略补跑被跳过的红队 / 质量 / 发布演练门禁"
        if status in {
            "failed",
            "running",
            "waiting_confirmation",
            "waiting_preview_confirmation",
            "waiting_ui_revision",
            "waiting_architecture_revision",
            "waiting_quality_revision",
        }:
            return "在宿主里说“继续当前流程，不要重新开题”"
        return "在宿主里说“继续当前流程，进入前端实现与运行验证”"

    def _current_workflow_description(self, project_dir: Path) -> str:
        run_state = self._read_pipeline_run_state(project_dir) or {}
        pipeline_args = run_state.get("pipeline_args") if isinstance(run_state, dict) else {}
        if isinstance(pipeline_args, dict):
            description = str(pipeline_args.get("description", "")).strip()
            if description:
                return description
        config = get_config_manager(project_dir).config
        return str(config.description or "").strip()

    def _session_brief_path(self, project_dir: Path) -> Path:
        return Path(project_dir).resolve() / ".super-dev" / "SESSION_BRIEF.md"

    def _workflow_state_path(self, project_dir: Path) -> Path:
        return workflow_state_file(project_dir)

    def _write_workflow_state(self, *, project_dir: Path, payload: dict[str, Any]) -> Path:
        project_dir = Path(project_dir).resolve()
        run_state = self._read_pipeline_run_state(project_dir) or {}
        docs_state = self._get_docs_confirmation_state(project_dir)
        preview_state = self._get_preview_confirmation_state(project_dir)
        ui_state = self._get_ui_revision_state(project_dir)
        architecture_state = self._get_architecture_revision_state(project_dir)
        quality_state = self._get_quality_revision_state(project_dir)
        workflow_payload = {
            "active_change_id": str(payload.get("active_change_id", "")).strip(),
            "artifact_prefix": str(payload.get("artifact_prefix", "")).strip(),
            "status": str(payload.get("status", "")).strip(),
            "current_step_label": str(payload.get("current_step_label", "")).strip(),
            "user_next_action": str(payload.get("user_next_action", "")).strip(),
            "recommended_command": str(payload.get("recommended_command", "")).strip(),
            "reason": str(payload.get("reason", "")).strip(),
            "evidence": str(payload.get("evidence", "")).strip(),
            "preferred_host": str(payload.get("preferred_host", "")).strip(),
            "preferred_host_name": str(payload.get("preferred_host_name", "")).strip(),
            "host_continue_prompt": str(payload.get("host_continue_prompt", "")).strip(),
            "session_brief_path": self._session_brief_path(project_dir).resolve().as_posix(),
            "framework_playbook": load_framework_playbook_summary(project_dir),
            "continuity_rules": list(payload.get("continuity_rules") or []),
            "gates": {
                "docs_confirmation": {
                    "status": str(docs_state.get("status", "")).strip(),
                    "comment": str(docs_state.get("comment", "")).strip(),
                },
                "preview_confirmation": {
                    "status": str(preview_state.get("status", "")).strip(),
                    "comment": str(preview_state.get("comment", "")).strip(),
                },
                "ui_revision": {
                    "status": str(ui_state.get("status", "")).strip(),
                    "comment": str(ui_state.get("comment", "")).strip(),
                },
                "architecture_revision": {
                    "status": str(architecture_state.get("status", "")).strip(),
                    "comment": str(architecture_state.get("comment", "")).strip(),
                },
                "quality_revision": {
                    "status": str(quality_state.get("status", "")).strip(),
                    "comment": str(quality_state.get("comment", "")).strip(),
                },
            },
            "pipeline_run_state": {
                "status": str(run_state.get("status", "")).strip(),
                "current_stage": str(run_state.get("current_stage", "")).strip(),
                "current_stage_title": str(run_state.get("current_stage_title", "")).strip(),
                "scope_coverage_status": str(run_state.get("scope_coverage_status", "")).strip(),
                "scope_high_priority_gap_count": int(
                    run_state.get("scope_high_priority_gap_count", 0) or 0
                ),
                "skipped_gates": list(run_state.get("skipped_gates") or []),
            },
        }
        return save_workflow_state(project_dir, workflow_payload)

    def _build_session_continuity_rules(self, *, status: str) -> list[str]:
        return workflow_continuity_rules(status)

    def _build_continue_interaction_clause(self, *, status: str, current_step_label: str) -> str:
        rules = self._build_session_continuity_rules(status=status)
        leading = f"当前步骤是“{current_step_label}”。" if current_step_label else ""
        return leading + "".join(rules)

    def _write_session_brief(self, *, project_dir: Path, payload: dict[str, Any]) -> Path:
        project_dir = Path(project_dir).resolve()
        brief_path = self._session_brief_path(project_dir)
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        preferred_host_name = str(
            payload.get("preferred_host_name", "")
        ).strip() or host_display_name(
            str(payload.get("preferred_host", "")).strip()
            or self._preferred_host_target_for_project(project_dir)
        )
        host_prompt = str(payload.get("host_continue_prompt", "")).strip()
        continuity_rules = payload.get("continuity_rules") or []
        action_card = _dict_value(payload.get("action_card"))
        if not isinstance(continuity_rules, list):
            continuity_rules = []
        lines = [
            "# Super Dev Session Brief",
            "",
            f"- 动作类型: {self._workflow_mode_label(str(payload.get('workflow_mode', '')).strip())}",
            f"- 当前步骤: {payload.get('current_step_label', payload.get('status', '-'))}",
            f"- 当前状态: {payload.get('status', '-')}",
            f"- 用户下一步: {payload.get('user_next_action', payload.get('recommended_command', '-'))}",
            f"- 系统建议动作: {payload.get('recommended_command', '-')}",
            f"- 推荐宿主: {preferred_host_name or '-'}",
            "- 工作流状态 JSON: " f"{self._workflow_state_path(project_dir).resolve().as_posix()}",
            "- 最新历史快照: " f"{latest_workflow_snapshot_file(project_dir).resolve().as_posix()}",
            f"- 事件日志: {workflow_event_log_file(project_dir).resolve().as_posix()}",
            f"- Hook 审计日志: {HookManager.hook_history_file(project_dir).resolve().as_posix()}",
        ]
        recent_snapshots = (
            payload.get("recent_snapshots")
            if isinstance(payload.get("recent_snapshots"), list)
            else []
        )
        framework_playbook = load_framework_playbook_summary(project_dir)
        if framework_playbook:
            lines.append(f"- 跨平台框架: {framework_playbook.get('framework', '-')}")
            native = framework_playbook.get("native_capabilities", [])
            validation = framework_playbook.get("validation_surfaces", [])
            if native:
                lines.append(f"- 原生能力面: {' / '.join(str(item) for item in native[:3])}")
            if validation:
                lines.append(f"- 必验场景: {' / '.join(str(item) for item in validation[:3])}")
        harness_summaries = summarize_operational_harnesses(project_dir, write_reports=False)
        if harness_summaries:
            lines.extend(["", "## 运行验证摘要"])
            for harness_summary in harness_summaries[:3]:
                label = (
                    str(harness_summary.get("label", "")).strip()
                    or str(harness_summary.get("kind", "")).strip()
                )
                if not harness_summary.get("enabled"):
                    status = "不适用"
                else:
                    status = "通过" if harness_summary.get("passed") else "失败"
                line = f"- {label}: {status}"
                blocker = str(harness_summary.get("first_blocker", "")).strip()
                if blocker:
                    line += f" · {blocker}"
                lines.append(line)
        user_action_shortcuts = (
            payload.get("user_action_shortcuts")
            if isinstance(payload.get("user_action_shortcuts"), list)
            else []
        )
        if user_action_shortcuts:
            lines.append(
                f"- 你现在可以直接说: {' / '.join(str(item) for item in user_action_shortcuts[:4])}"
            )
        action_examples = (
            action_card.get("examples") if isinstance(action_card.get("examples"), list) else []
        )
        if action_examples:
            lines.append(f"- 自然语言示例: {', '.join(str(item) for item in action_examples[:3])}")
        scenario_cards = (
            payload.get("scenario_cards") if isinstance(payload.get("scenario_cards"), list) else []
        )
        if scenario_cards:
            lines.extend(["", "## 现实场景怎么做"])
            for item in scenario_cards[:4]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "")).strip()
                command = str(item.get("cli_command", "")).strip()
                description = str(item.get("description", "")).strip()
                if title and command:
                    line = f"- {title}: `{command}`"
                    if description:
                        line += f" · {description}"
                    lines.append(line)
        if host_prompt:
            lines.append(f"- 宿主第一句: {host_prompt}")
        if payload.get("reason"):
            lines.append(f"- 原因: {payload.get('reason')}")
        if payload.get("evidence"):
            lines.append(f"- 依据: {payload.get('evidence')}")
        if continuity_rules:
            lines.extend(["", "## 会话连续性规则"])
            for item in continuity_rules:
                lines.append(f"- {item}")
        self._write_workflow_state(project_dir=project_dir, payload=payload)
        recent_snapshots = load_recent_workflow_snapshots(project_dir, limit=3)
        if recent_snapshots:
            lines.extend(["", "## 最近流程快照"])
            for item in recent_snapshots[:3]:
                if not isinstance(item, dict):
                    continue
                step = (
                    str(item.get("current_step_label", "")).strip()
                    or str(item.get("status", "")).strip()
                )
                updated_at = str(item.get("updated_at", "")).strip() or "-"
                lines.append(f"- {updated_at} · {step}")
        recent_events = load_recent_workflow_events(project_dir, limit=3)
        if recent_events:
            lines.extend(["", "## 最近状态事件"])
            for item in recent_events:
                updated_at = str(item.get("timestamp", "")).strip() or "-"
                lines.append(f"- {updated_at} · {describe_workflow_event(item)}")
        recent_hook_events = HookManager.load_recent_history(project_dir, limit=3)
        if recent_hook_events:
            lines.extend(["", "## 最近 Hook 事件"])
            for hook_event in recent_hook_events:
                status = (
                    "受阻" if hook_event.blocked else ("通过" if hook_event.success else "失败")
                )
                lines.append(
                    f"- {hook_event.timestamp} · {hook_event.event} / "
                    f"{hook_event.phase or '-'} / {hook_event.hook_name} / {status}"
                )
        recent_timeline = load_recent_operational_timeline(project_dir, limit=5)
        if recent_timeline:
            lines.extend(["", "## 最近关键时间线"])
            for item in recent_timeline:
                title = str(item.get("title", "")).strip() or str(item.get("kind", "")).strip()
                message = str(item.get("message", "")).strip() or "-"
                updated_at = str(item.get("timestamp", "")).strip() or "-"
                lines.append(f"- {updated_at} · {title} · {message}")
        lines.extend(
            [
                "",
                "## 离开当前流程的唯一条件",
                "- 用户明确说要取消当前流程。",
                "- 用户明确说要重新开始一条新的流程。",
                "- 用户明确说要切回普通聊天，而不是继续 Super Dev。",
                "",
                "## 下次回来怎么继续",
                "- 回到宿主后，直接说“继续当前流程”。",
                "- 如果只想知道现在先做什么，就在宿主里说“现在下一步是什么”。",
            ]
        )
        brief_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return brief_path

    def _build_host_continue_prompt(
        self,
        *,
        project_dir: Path,
        target: str,
        next_payload: dict[str, Any] | None = None,
    ) -> str:
        instruction = self._build_host_continue_instruction(
            project_dir=project_dir,
            next_payload=next_payload,
        )
        entry_prompts = build_host_entry_prompts(
            target=target,
            instruction=instruction,
            supports_slash=self._supports_slash_for_prompt(target),
        )
        preferred_entry = str(entry_prompts.get("preferred_entry", "")).strip()
        prompts = entry_prompts.get("entry_prompts", {})
        if isinstance(prompts, dict) and preferred_entry:
            prompt = str(prompts.get(preferred_entry, "")).strip()
            if prompt:
                return prompt
        return str(self._build_host_trigger_example(target=target, idea=instruction))

    def _build_host_continue_instruction(
        self,
        *,
        project_dir: Path,
        next_payload: dict[str, Any] | None = None,
    ) -> str:
        next_payload = dict(next_payload or {})
        status = str(next_payload.get("status", "")).strip()
        current_step_label = str(next_payload.get("current_step_label", "")).strip()
        continuity_clause = self._build_continue_interaction_clause(
            status=status,
            current_step_label=current_step_label,
        )
        description = self._current_workflow_description(project_dir)
        if description:
            instruction = (
                f"继续当前项目“{description}”的 Super Dev 流程，不要当作普通聊天。"
                "先读取 .super-dev/SESSION_BRIEF.md、.super-dev/workflow-state.json、.super-dev/WORKFLOW.md、output/*、.super-dev/review-state/* 和最近的 tasks.md。"
                f"{continuity_clause}"
            )
        else:
            return (
                "继续当前项目的 Super Dev 流程，不要当作普通聊天。"
                "先读取 .super-dev/SESSION_BRIEF.md、.super-dev/workflow-state.json、.super-dev/WORKFLOW.md、output/*、.super-dev/review-state/* 和最近的 tasks.md。"
                f"{continuity_clause}"
            )
        return instruction

    def _build_host_start_prompt(self, *, project_dir: Path, target: str) -> str:
        description = self._current_workflow_description(project_dir)
        if description:
            instruction = (
                f"请用 Super Dev 流程开始处理当前项目“{description}”，不要当作普通聊天。"
                "先做 research，再产出 PRD、Architecture、UIUX 三文档，完成后停下来等我确认。"
            )
        else:
            instruction = (
                "请用 Super Dev 流程开始处理当前需求，不要当作普通聊天。"
                "先做 research，再产出 PRD、Architecture、UIUX 三文档，完成后停下来等我确认。"
            )
        return str(self._build_host_trigger_example(target=target, idea=instruction))

    def _supports_slash_for_prompt(self, target: str) -> bool:
        from .integrations import IntegrationManager

        return IntegrationManager.supports_slash(target)

    def _build_workflow_session_hint(self, *, project_dir: Path, target: str) -> dict[str, Any]:
        if not self._project_has_super_dev_context(project_dir):
            return {
                "session_mode": "fresh_start",
                "continue_prompt": "",
                "recommended_workflow_command": "",
                "workflow_reason": "",
                "continuity_rules": [],
                "workflow_context": {},
            }
        next_payload = self._build_next_step_payload(project_dir)
        self._write_session_brief(project_dir=project_dir, payload=next_payload)
        action_card = _dict_value(next_payload.get("action_card"))
        continue_prompt = self._build_host_continue_prompt(
            project_dir=project_dir, target=target, next_payload=next_payload
        )
        recommended_workflow_command = str(next_payload.get("recommended_command", "")).strip()
        return {
            "session_mode": "continue_super_dev",
            "continue_instruction": self._build_host_continue_instruction(
                project_dir=project_dir,
                next_payload=next_payload,
            ),
            "continue_prompt": continue_prompt,
            "recommended_workflow_command": recommended_workflow_command,
            "workflow_reason": str(next_payload.get("reason", "")).strip(),
            "workflow_status": str(next_payload.get("status", "")).strip(),
            "workflow_mode": str(next_payload.get("workflow_mode", "")).strip(),
            "action_title": str(action_card.get("title", "")).strip()
            or str(next_payload.get("current_step_label", "")).strip(),
            "action_examples": _list_value(action_card.get("examples")),
            "user_action_shortcuts": _list_value(next_payload.get("user_action_shortcuts")),
            "scenario_cards": _list_value(next_payload.get("scenario_cards")),
            "continuity_rules": _list_value(
                next_payload.get("continuity_rules") or action_card.get("continuity_rules")
            ),
            "framework_playbook": load_framework_playbook_summary(project_dir),
            "workflow_context": build_host_workflow_context(
                project_dir,
                entry_mode="continue",
                target=target,
            ),
        }

    def _auto_migrate_if_needed(self, project_dir: Path) -> None:
        """检测项目配置版本，如果低于当前 CLI 版本则自动迁移。"""
        try:
            config_path = project_dir / "super-dev.yaml"
            if not config_path.exists():
                return
            import yaml

            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            project_version = data.get("version", "")
            if project_version == __version__:
                return
            self.console.print(
                f"[yellow]检测到项目配置版本 {project_version or '未知'}，"
                f"当前 CLI 版本 {__version__}，正在自动迁移...[/yellow]"
            )
            from .migrate import migrate_project

            changes = migrate_project(project_dir)
            for change in changes:
                self.console.print(f"  [green]✓[/green] {change}")
            self.console.print("")
        except Exception:
            pass

    def _project_has_super_dev_context(self, project_dir: Path) -> bool:
        """只有当前目录有 super-dev.yaml 且不是家目录才算 Super Dev 项目。"""
        project_dir = Path(project_dir).resolve()
        if project_dir == Path.home().resolve():
            return False
        return (project_dir / "super-dev.yaml").exists()

    def _preferred_host_target_for_project(self, project_dir: Path) -> str:
        from .integrations import IntegrationManager

        project_dir = Path(project_dir).resolve()
        config = get_config_manager(project_dir).config
        available_targets = [item.name for item in IntegrationManager(project_dir).list_targets()]
        preferred_order = list(
            dict.fromkeys(
                ("codex", "codex-cli", "claude-code", "claude", "opencode", *PRIMARY_HOST_TOOL_IDS)
            )
        )

        def _pick_best(candidates: list[str]) -> str | None:
            for host_id in preferred_order:
                if host_id in candidates:
                    return host_id
            return candidates[0] if candidates else None

        configured_targets = [
            item for item in config.host_profile_targets if item in available_targets
        ]
        if configured_targets:
            best = _pick_best(configured_targets)
            if best:
                return best

        configured_surfaces = self._collect_configured_host_targets(
            project_dir=project_dir,
            available_targets=available_targets,
        )
        if configured_surfaces:
            best = _pick_best(configured_surfaces)
            if best:
                return best

        detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
        if detected_targets:
            best = _pick_best(detected_targets)
            if best:
                return best
        return "codex"

    def _describe_next_step(self, *, status: str, recommended_command: str) -> tuple[str, str]:
        status_map = {
            "not_initialized": (
                "还没完成宿主接入",
                "先把 Super Dev 装进一个宿主，并确认可以触发。",
            ),
            "missing_core_docs": (
                "三文档还没补齐",
                "先让宿主按 Super Dev 流程补齐 PRD、Architecture、UIUX 三文档。",
            ),
            "waiting_docs_confirmation": (
                "等待三文档确认",
                "先确认 PRD、Architecture、UIUX 三文档，再继续后续阶段。",
            ),
            "waiting_confirmation": (
                "等待流程确认门",
                "先处理当前确认门，再继续恢复当前流水线。",
            ),
            "waiting_ui_revision": (
                "等待 UI 改版闭环",
                "先更新 UIUX 文档并完成前端返工，再恢复流程。",
            ),
            "waiting_preview_confirmation": (
                "等待前端预览确认",
                "先评审并确认当前前端预览，再决定是否进入后端和后续阶段。",
            ),
            "waiting_architecture_revision": (
                "等待架构返工闭环",
                "先更新架构文档并同步实现，再恢复流程。",
            ),
            "waiting_quality_revision": (
                "等待质量整改闭环",
                "先完成质量整改并重新过门禁，再恢复流程。",
            ),
            "delivery_closure_incomplete": (
                "交付证据还没闭环",
                "先补齐质量与发布证据，再进入交付。",
            ),
            "product_revision_required": (
                "产品审查要求修订",
                "先处理产品审查里的高优先级问题。",
            ),
            "proof_pack_incomplete": (
                "proof-pack 还没补齐",
                "先重新生成交付证据包。",
            ),
            "ready": (
                "当前流程可以继续推进",
                "先打开状态面板确认当前阶段，再继续执行。",
            ),
            "delivery_ready": (
                "交付证据已就绪",
                "当前验证工作已完成，等待用户决定是否合并或发布。",
            ),
        }
        if status in status_map:
            return status_map[status]

        command_map = {
            "在宿主里说“继续当前流程，不要重新开题”": (
                "当前流程可从中断点恢复",
                "先从上次中断的位置继续，不要重新开一轮。",
            ),
            "在宿主里说“继续当前流程”": (
                "当前流程需要先看状态面板",
                "先看状态面板，确认当前卡在哪一步。",
            ),
            "在宿主里继续当前流程，并补齐交付闭环与发布证据": (
                "当前卡在质量/交付闭环",
                "先跑完整质量门禁，补齐交付闭环。",
            ),
            "在宿主里先处理产品审查要求的修订项，再继续当前流程": (
                "当前卡在产品审查",
                "先重新执行产品审查并处理要求修订项。",
            ),
        }
        return command_map.get(
            recommended_command,
            ("当前流程存在待处理项", "先按推荐动作继续当前流程，不要另起一轮普通聊天。"),
        )

    def _finalize_next_step_payload(
        self, *, project_dir: Path, payload: dict[str, Any]
    ) -> dict[str, Any]:
        project_dir = Path(project_dir).resolve()
        preferred_host = self._preferred_host_target_for_project(project_dir)
        preferred_host_name = (
            "Codex" if preferred_host == "codex-cli" else host_display_name(preferred_host)
        )
        action_card = _dict_value(payload.get("action_card"))
        current_step_label = str(action_card.get("title", "")).strip()
        user_next_action = str(action_card.get("user_action", "")).strip()
        if not current_step_label or not user_next_action:
            current_step_label, user_next_action = self._describe_next_step(
                status=str(payload.get("status", "")).strip(),
                recommended_command=str(payload.get("recommended_command", "")).strip(),
            )
        if self._project_has_super_dev_context(project_dir):
            continue_instruction = self._build_host_continue_instruction(
                project_dir=project_dir,
                next_payload={
                    **payload,
                    "current_step_label": current_step_label,
                    "user_next_action": user_next_action,
                },
            )
            host_continue_prompt = self._build_host_continue_prompt(
                project_dir=project_dir,
                target=preferred_host,
                next_payload={
                    **payload,
                    "current_step_label": current_step_label,
                    "user_next_action": user_next_action,
                },
            )
        else:
            continue_instruction = ""
            host_continue_prompt = self._build_host_start_prompt(
                project_dir=project_dir, target=preferred_host
            )
        host_entry_bundle = build_host_entry_prompts(
            target=preferred_host,
            instruction=continue_instruction or host_continue_prompt,
            supports_slash=self._supports_slash_for_prompt(preferred_host),
        )
        enriched = dict(payload)
        active_change_id = str(payload.get("active_change_id", "")).strip() or (
            resolve_active_change_id(project_dir)
        )
        artifact_prefix = str(payload.get("artifact_prefix", "")).strip() or (
            resolve_current_artifact_prefix(project_dir, fallback_name=project_dir.name)
        )
        shadow_ledger = (
            payload.get("shadow_ledger")
            if isinstance(payload.get("shadow_ledger"), dict)
            else build_shadow_ledger_summary(project_dir)
        )
        enriched.update(
            {
                "active_change_id": active_change_id,
                "artifact_prefix": artifact_prefix,
                "current_step_label": current_step_label,
                "user_next_action": user_next_action,
                "preferred_host": preferred_host,
                "preferred_host_name": preferred_host_name,
                "host_continue_prompt": host_continue_prompt,
                "host_continue_entry_prompts": (
                    host_entry_bundle.get("entry_prompts", {})
                    if isinstance(host_entry_bundle.get("entry_prompts", {}), dict)
                    else {}
                ),
                "host_continue_entry_labels": (
                    host_entry_bundle.get("entry_labels", {})
                    if isinstance(host_entry_bundle.get("entry_labels", {}), dict)
                    else {}
                ),
                "host_continue_preferred_entry": str(
                    host_entry_bundle.get("preferred_entry", "")
                ).strip(),
                "host_continue_preferred_entry_label": str(
                    host_entry_bundle.get("preferred_entry_label", "")
                ).strip(),
                "session_brief_path": self._session_brief_path(project_dir).resolve().as_posix(),
                "workflow_state_path": self._workflow_state_path(project_dir).resolve().as_posix(),
                "continuity_rules": self._build_session_continuity_rules(
                    status=str(payload.get("status", "")).strip()
                ),
                "workflow_mode": str(
                    action_card.get("mode", payload.get("workflow_mode", ""))
                ).strip()
                or "continue",
                "action_card": action_card,
                "user_action_shortcuts": self._workflow_mode_shortcuts(
                    str(action_card.get("mode", payload.get("workflow_mode", ""))).strip()
                    or "continue",
                    action_card=action_card,
                ),
                "recent_snapshots": load_recent_workflow_snapshots(project_dir, limit=3),
                "shadow_ledger": shadow_ledger,
            }
        )
        return enriched

    def _build_next_step_payload(self, project_dir: Path) -> dict[str, Any]:
        project_dir = Path(project_dir).resolve()
        if not self._project_has_super_dev_context(project_dir):
            return self._finalize_next_step_payload(
                project_dir=project_dir,
                payload={
                    "status": "not_initialized",
                    "reason": "当前目录还没有进入 Super Dev 工作流。",
                    "recommended_command": "super-dev",
                    "evidence": "未检测到 super-dev.yaml / .super-dev/WORKFLOW.md / output 基础产物",
                },
            )

        summary = detect_pipeline_summary(
            project_dir,
            self._read_pipeline_run_state(project_dir) or {},
            include_shadow_ledger=True,
        )
        checkpoint_status = str(summary.get("workflow_status", "")).strip() or "ready"
        recommended_command = (
            str(summary.get("recommended_command", "")).strip() or "在宿主里说“继续当前流程”"
        )
        blocker = str(summary.get("blocker", "")).strip()
        evidence = str(summary.get("evidence", "")).strip()

        if checkpoint_status not in {"ready", "missing_quality", "missing_delivery"}:
            return self._finalize_next_step_payload(
                project_dir=project_dir,
                payload={
                    "status": checkpoint_status,
                    "reason": blocker
                    or "当前仓库存在运行态、确认门或范围门禁，需要先沿当前流程继续。",
                    "recommended_command": recommended_command,
                    "evidence": evidence or f"workflow_status={checkpoint_status}",
                    "workflow_mode": str(summary.get("workflow_mode", "")).strip(),
                    "action_card": summary.get("action_card"),
                    "scenario_cards": summary.get("scenario_cards"),
                },
            )

        artifact_prefix = resolve_current_artifact_prefix(project_dir)
        readiness_passed = False
        readiness_path = project_dir / "output" / f"{artifact_prefix}-release-readiness.json"
        if readiness_path.exists():
            try:
                readiness_payload = json.loads(readiness_path.read_text(encoding="utf-8"))
            except Exception:
                readiness_payload = {}
            failed_checks = (
                list(readiness_payload.get("failed_checks") or [])
                if isinstance(readiness_payload, dict)
                else []
            )
            readiness_passed = bool(readiness_payload.get("passed")) and not failed_checks
            if "Delivery Closure" in failed_checks:
                return self._finalize_next_step_payload(
                    project_dir=project_dir,
                    payload={
                        "status": "delivery_closure_incomplete",
                        "reason": "发布闭环证据还没有齐。",
                        "recommended_command": "在宿主里继续当前流程，并补齐交付闭环与发布证据",
                        "evidence": "release readiness failed_checks 包含 Delivery Closure",
                    },
                )

        product_audit_path = project_dir / "output" / f"{artifact_prefix}-product-audit.json"
        if product_audit_path.exists():
            try:
                product_audit_payload = json.loads(product_audit_path.read_text(encoding="utf-8"))
            except Exception:
                product_audit_payload = {}
            product_status = str(product_audit_payload.get("status", "")).strip()
            if product_status == "revision_required":
                return self._finalize_next_step_payload(
                    project_dir=project_dir,
                    payload={
                        "status": "product_revision_required",
                        "reason": "产品审查仍然要求修订。",
                        "recommended_command": "在宿主里先处理产品审查要求的修订项，再继续当前流程",
                        "evidence": f"product_audit.status={product_status}",
                    },
                )

        proof_pack_path = project_dir / "output" / f"{artifact_prefix}-proof-pack.json"
        proof_pack_status = ""
        if proof_pack_path.exists():
            try:
                proof_pack_payload = json.loads(proof_pack_path.read_text(encoding="utf-8"))
            except Exception:
                proof_pack_payload = {}
            proof_pack_status = str(proof_pack_payload.get("status", "")).strip()
            if proof_pack_status == "incomplete":
                return self._finalize_next_step_payload(
                    project_dir=project_dir,
                    payload={
                        "status": "proof_pack_incomplete",
                        "reason": "当前交付证据包还没有齐。",
                        "recommended_command": "在宿主里继续当前流程，并补齐 proof-pack 依赖证据",
                        "evidence": f"proof_pack.status={proof_pack_status}",
                    },
                )

        if readiness_passed and proof_pack_status == "ready":
            return self._finalize_next_step_payload(
                project_dir=project_dir,
                payload={
                    "status": "delivery_ready",
                    "reason": (
                        "当前代码版本的质量门禁、发布就绪检查和交付证据包均已通过；"
                        "尚未获得合并或发布授权。"
                    ),
                    "recommended_command": "等待用户决定是否合并或发布",
                    "evidence": "release-readiness.passed=true; proof-pack.status=ready",
                    "workflow_mode": "release",
                    "action_card": {
                        "mode": "release",
                        "title": "交付证据已就绪",
                        "user_action": "查看验证结果，并决定是否合并或发布。",
                        "examples": [
                            "查看验证结果",
                            "查看交付证据包",
                            "决定是否合并",
                            "决定是否发布",
                        ],
                    },
                },
            )

        return self._finalize_next_step_payload(
            project_dir=project_dir,
            payload={
                "status": "ready",
                "reason": blocker or "当前没有检测到待恢复的流程门禁，建议从状态面板继续。",
                "recommended_command": "在宿主里说“继续当前流程”",
                "evidence": evidence or "未检测到更高优先级阻断项",
                "workflow_mode": str(summary.get("workflow_mode", "")).strip(),
                "action_card": summary.get("action_card"),
                "scenario_cards": summary.get("scenario_cards"),
            },
        )

    def _resolve_pipeline_stage_selector(self, value: str) -> int | None:
        normalized = str(value).strip().lower()
        stage_map = {
            "research": 0,
            "discovery": 0,
            "docs": 1,
            "document": 1,
            "documents": 1,
            "prd": 1,
            "architecture": 1,
            "uiux": 1,
            "spec": 2,
            "frontend": 3,
            "ui": 3,
            "backend": 4,
            "implementation": 4,
            "redteam": 5,
            "quality": 6,
            "qa": 6,
            "review": 7,
            "prompt": 8,
            "cicd": 9,
            "deploy-fix": 10,
            "delivery": 11,
            "rehearsal": 12,
        }
        if normalized.isdigit():
            stage_number = int(normalized)
            if 0 <= stage_number <= 12:
                return stage_number
            return None
        return stage_map.get(normalized)

    def _stage_jump_impact(self, stage_number: int) -> list[str]:
        if stage_number <= 1:
            return [
                "将重做 research / PRD / Architecture / UIUX",
                "会使 Spec 与任务拆解重新计算",
                "后续实现与质量验证需要全量重跑",
            ]
        if stage_number == 2:
            return [
                "将重算 Spec 与 tasks",
                "前后端实现任务依赖会刷新",
                "建议在继续前确认三文档未变更",
            ]
        if stage_number == 3:
            return [
                "将重做前端实施蓝图与预览验证",
                "可能触发 UI 改版门重新确认",
            ]
        if stage_number == 4:
            return [
                "将重做宿主实现参考与任务执行",
                "后续红队与质量门禁会重新执行",
            ]
        if stage_number >= 5:
            return [
                "将从质量/交付后段开始重跑",
                "不会重建前置文档与 spec，除非门禁判定需要回退",
            ]
        return ["将按目标阶段继续执行并自动校验前置门禁"]
