"""
开发：Excellent（11964948@qq.com）
功能：跨平台框架专项验证与交付证据
作用：汇总 framework playbook、运行时执行与对齐结果，生成独立 harness 报告
创建时间：2026-04-05
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifact_utils import resolve_current_artifact_prefix
from .config import ConfigManager
from .frameworks import framework_playbook_complete, is_cross_platform_frontend
from .reviewers.ui_review_evidence import RUNTIME, UIReviewEvidence, ui_result_details, ui_status_ok


def _is_stale(path: Path | None, *, dependencies: list[Path | None]) -> bool:
    if path is None or not path.exists():
        return False
    try:
        artifact_mtime = path.stat().st_mtime
    except OSError:
        return False
    for dependency in dependencies:
        if dependency is None or not dependency.exists():
            continue
        try:
            if dependency.stat().st_mtime > artifact_mtime:
                return True
        except OSError:
            continue
    return False


@dataclass
class FrameworkHarnessReport:
    project_name: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enabled: bool = False
    framework: str = ""
    implementation_modules: list[str] = field(default_factory=list)
    native_capabilities: list[str] = field(default_factory=list)
    validation_surfaces: list[str] = field(default_factory=list)
    delivery_evidence: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    source_files: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return (
            self.enabled and not self.blockers and all(self.checks.values())
            if self.checks
            else self.enabled and not self.blockers
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "enabled": self.enabled,
            "framework": self.framework,
            "implementation_modules": list(self.implementation_modules),
            "native_capabilities": list(self.native_capabilities),
            "validation_surfaces": list(self.validation_surfaces),
            "delivery_evidence": list(self.delivery_evidence),
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "next_actions": list(self.next_actions),
            "passed": self.passed,
            "source_files": dict(self.source_files),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Framework Harness",
            "",
            f"- Project: `{self.project_name}`",
            f"- Generated at (UTC): {self.generated_at}",
            f"- Enabled: {'yes' if self.enabled else 'no'}",
            f"- Passed: {'yes' if self.passed else 'no'}",
        ]
        if not self.enabled:
            lines.extend(["", "当前项目未检测到跨平台 framework playbook。", ""])
            return "\n".join(lines)

        lines.extend(
            [
                f"- Framework: `{self.framework or '-'}`",
                "",
                "## Framework Playbook",
                "",
                "- Implementation Modules: "
                + ("；".join(self.implementation_modules) if self.implementation_modules else "-"),
                "- Native Capabilities: "
                + ("；".join(self.native_capabilities) if self.native_capabilities else "-"),
                "- Validation Surfaces: "
                + ("；".join(self.validation_surfaces) if self.validation_surfaces else "-"),
                "- Delivery Evidence: "
                + ("；".join(self.delivery_evidence) if self.delivery_evidence else "-"),
                "",
                "## Checks",
                "",
            ]
        )
        for name, passed in self.checks.items():
            lines.append(f"- {name}: {'pass' if passed else 'fail'}")
        lines.extend(["", "## Blockers", ""])
        if self.blockers:
            for item in self.blockers:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前没有跨平台框架阻塞项。")
        lines.extend(["", "## Next Actions", ""])
        if self.next_actions:
            for item in self.next_actions:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前跨平台框架专项证据已经齐全。")
        return "\n".join(lines).rstrip() + "\n"


class FrameworkHarnessBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.project_name = self.project_dir.name

    def build(self) -> FrameworkHarnessReport:
        report = FrameworkHarnessReport(project_name=self.project_name)
        config = ConfigManager(self.project_dir).load()
        if str(config.frontend or "").strip().lower() in {"", "none"}:
            return report
        prefix = resolve_current_artifact_prefix(self.project_dir, configured_name=config.name)
        evidence = UIReviewEvidence(self.project_dir, prefix)
        ui_contract_file = evidence.contract
        if not ui_contract_file.is_file():
            return report

        try:
            payload = json.loads(ui_contract_file.read_text(encoding="utf-8"))
        except Exception:
            return report
        if not isinstance(payload, dict):
            return report

        analysis = payload.get("analysis", {}) if isinstance(payload.get("analysis"), dict) else {}
        frontend_value = str(analysis.get("frontend") or "").lower().strip()
        framework_playbook_payload = payload.get("framework_playbook")
        framework_playbook: dict[str, Any] = (
            framework_playbook_payload if isinstance(framework_playbook_payload, dict) else {}
        )
        framework_name = str(framework_playbook.get("framework") or "").strip()
        enabled = is_cross_platform_frontend(frontend_value) or bool(framework_name)
        if not enabled:
            return report

        report.enabled = True
        report.framework = framework_name or frontend_value or "cross-platform"
        report.implementation_modules = [
            str(item)
            for item in framework_playbook.get("implementation_modules", [])
            if str(item).strip()
        ]
        report.native_capabilities = [
            str(item)
            for item in framework_playbook.get("native_capabilities", [])
            if str(item).strip()
        ]
        report.validation_surfaces = [
            str(item)
            for item in framework_playbook.get("validation_surfaces", [])
            if str(item).strip()
        ]
        report.delivery_evidence = [
            str(item)
            for item in framework_playbook.get("delivery_evidence", [])
            if str(item).strip()
        ]
        report.source_files["ui_contract"] = str(ui_contract_file)

        report.checks["ui_contract_framework_playbook"] = framework_playbook_complete(
            framework_playbook
        )
        if not report.checks["ui_contract_framework_playbook"]:
            report.blockers.append(
                f"{report.framework} framework playbook 尚未完整冻结到 output/*-ui-contract.json"
            )

        runtime = evidence.result(RUNTIME)
        if runtime.path is not None:
            report.source_files["frontend_runtime"] = str(runtime.path)
        report.checks["frontend_runtime_framework_execution"] = ui_status_ok(runtime.status)
        if not report.checks["frontend_runtime_framework_execution"]:
            report.blockers.append(ui_result_details([runtime]))

        alignment_file = self.output_dir / f"{evidence.prefix}-ui-contract-alignment.json"
        if alignment_file.is_file():
            report.source_files["ui_contract_alignment"] = str(alignment_file)
            if _is_stale(alignment_file, dependencies=[ui_contract_file]):
                report.checks["ui_contract_alignment_framework_execution"] = False
                report.blockers.append(
                    f"{report.framework} UI 契约对齐报告已过期，需要基于最新 UI 契约重新生成"
                )
            else:
                try:
                    alignment_payload = json.loads(alignment_file.read_text(encoding="utf-8"))
                except Exception:
                    alignment_payload = {}
                framework_execution = (
                    alignment_payload.get("framework_execution")
                    if isinstance(alignment_payload, dict)
                    else {}
                )
                report.checks["ui_contract_alignment_framework_execution"] = bool(
                    isinstance(framework_execution, dict)
                    and framework_execution.get("passed", False)
                )
                if not report.checks["ui_contract_alignment_framework_execution"]:
                    report.blockers.append(
                        f"{report.framework} UI 契约对齐报告未证明 framework execution 通过"
                    )
        else:
            report.checks["ui_contract_alignment_framework_execution"] = False
            report.blockers.append(f"{report.framework} UI 契约对齐报告缺失")

        if (
            "ui_contract_framework_playbook" in report.checks
            and not report.checks["ui_contract_framework_playbook"]
        ):
            report.next_actions.append(
                "先补齐 framework playbook：implementation modules、platform constraints、execution guardrails、native capabilities、validation surfaces、delivery evidence。"
            )
        if not report.checks.get("frontend_runtime_framework_execution", False):
            report.next_actions.append(
                "在实际目标界面完成导航与交互，并导入当前浏览器运行证据；源码对齐另行检查。"
            )
        if not report.checks.get("ui_contract_alignment_framework_execution", False):
            report.next_actions.append("重新执行 UI review，确认 framework_execution 对齐项通过。")
        if not report.next_actions:
            report.next_actions.append("当前跨平台 framework harness 已满足发布前证据要求。")
        return report

    def write(self, report: FrameworkHarnessReport) -> dict[str, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base = self.output_dir / f"{self.project_name}-framework-harness"
        md_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}
