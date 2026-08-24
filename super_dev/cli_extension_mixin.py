"""最小扩展平台维护命令。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .extensions.evidence import EvidenceStore
from .extensions.manifest import ManifestValidationError
from .extensions.models import ExtensionStatus
from .extensions.ownership import evaluate_ownership
from .extensions.service import ExtensionService


class CliExtensionMixin:
    console: Any

    _EXTENSION_EXIT_CODES = {
        ExtensionStatus.PASS: 0,
        ExtensionStatus.BLOCKED: 2,
        ExtensionStatus.NOT_APPLICABLE: 3,
        ExtensionStatus.FAIL: 4,
    }

    def _extension_json_or_print(self, args, payload: dict[str, Any]) -> None:
        if getattr(args, "json", False):
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return
        self.console.print(
            f"[bold]{payload.get('title', '扩展检查')}[/bold]: {payload.get('status', '')}"
        )
        message = str(payload.get("message", "")).strip()
        if message:
            self.console.print(f"  {message}")
        for item in payload.get("details", []):
            self.console.print(f"  - {item}")
        result_path = str(payload.get("result_path", "")).strip()
        if result_path:
            self.console.print(f"  证据: {result_path}")

    def _cmd_extension(self, args) -> int:
        project_dir = Path.cwd()
        service = ExtensionService(project_dir)
        action = getattr(args, "extension_action", "")

        if action in {"validate", "inspect", "verify-source"}:
            try:
                manifest = service.load(Path(args.manifest))
            except ManifestValidationError as exc:
                self._extension_json_or_print(
                    args,
                    {
                        "title": "扩展清单检查",
                        "status": "未通过",
                        "message": "扩展没有运行，也没有修改项目文件。",
                        "details": list(exc.errors),
                    },
                )
                return 2

            if action == "validate":
                self._extension_json_or_print(
                    args,
                    {
                        "title": "扩展清单检查",
                        "status": "通过",
                        "message": "格式和边界有效；这不代表来源可信或已经取得执行权限。",
                        "details": [
                            f"扩展: {manifest.id} {manifest.version}",
                            f"来源类型: {manifest.source.kind}",
                            f"允许阶段: {', '.join(manifest.trigger.allowed_stages)}",
                        ],
                        "manifest": manifest.to_dict(),
                    },
                )
                return 0

            if action == "inspect":
                decision = evaluate_ownership(
                    manifest,
                    trusted_capabilities=set(manifest.required_capabilities),
                )
                self._extension_json_or_print(
                    args,
                    {
                        "title": "扩展边界检查",
                        "status": (
                            "已阻止"
                            if decision.status == ExtensionStatus.BLOCKED
                            else "通过"
                        ),
                        "message": "这里只展示申请边界，不执行扩展。",
                        "details": [
                            f"扩展: {manifest.id} {manifest.version}",
                            "所需能力: "
                            + (
                                ", ".join(
                                    item.value for item in manifest.required_capabilities
                                )
                                or "无"
                            ),
                            f"所有权边界: {decision.status.value}",
                            "执行能力: 本命令不探测、不授予",
                            f"允许写入: {', '.join(manifest.writes.allowed) or '无'}",
                        ],
                        "manifest": manifest.to_dict(),
                        "ownership": {
                            "status": decision.status.value,
                            "findings": list(decision.findings),
                        },
                    },
                )
                return 2 if decision.status == ExtensionStatus.BLOCKED else 0

            verification = service.verify_source(manifest)
            self._extension_json_or_print(
                args,
                {
                    "title": "扩展来源检查",
                    "status": "通过" if verification.passed else "已阻止",
                    "message": (
                        "来源锁和本地内容摘要一致；这不授予执行权限。"
                        if verification.passed
                        else "来源不一致，本次扩展没有运行。"
                    ),
                    "details": list(verification.errors),
                    "source": verification.to_dict(),
                },
            )
            return 0 if verification.passed else 2

        if action == "probe-contract":
            outcome = service.probe_contract(
                stage=getattr(args, "stage", "quality"), actor="super-dev-cli"
            )
            self._extension_json_or_print(
                args,
                {
                    "title": "扩展合同探针",
                    "status": outcome.status.value,
                    "message": outcome.message,
                    "details": [
                        "项目阶段没有由扩展修改。",
                        "合同探针没有接入真实外部方法。",
                    ],
                    "result_path": str(outcome.result_path or ""),
                    "result": outcome.result.to_dict() if outcome.result else None,
                },
            )
            return self._EXTENSION_EXIT_CODES.get(outcome.status, 5)

        if action == "history":
            history = EvidenceStore(project_dir).load_recent(limit=args.limit)
            self._extension_json_or_print(
                args,
                {
                    "title": "扩展运行历史",
                    "status": "可读取" if not history.warnings else "部分记录已跳过",
                    "message": (
                        "还没有扩展运行记录。"
                        if not history.events
                        else f"最近 {len(history.events)} 条记录"
                    ),
                    "details": list(history.warnings),
                    "events": list(history.events),
                },
            )
            if not getattr(args, "json", False):
                for event in history.events:
                    self.console.print(
                        "  - "
                        f"{event.get('timestamp', '-')} / {event.get('event', '-')} / "
                        f"{event.get('extension_id', '-')}"
                    )
            return 0

        self.console.print("[yellow]未知 extension 操作[/yellow]")
        return 5
