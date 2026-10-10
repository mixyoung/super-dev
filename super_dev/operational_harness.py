"""
开发：Excellent（11964948@qq.com）
功能：统一运行时 harness 聚合报告
作用：汇总 workflow / framework / hooks 三类 harness，生成单一交付与恢复真源
创建时间：2026-04-06
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .harness_registry import build_operational_harness_payload


@dataclass
class OperationalHarnessReport:
    project_name: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    all_passed: bool = True
    enabled_count: int = 0
    passed_count: int = 0
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    recent_timeline: list[dict[str, Any]] = field(default_factory=list)
    harnesses: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return self.enabled_count > 0

    @property
    def passed(self) -> bool:
        return self.all_passed if self.enabled else True

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "enabled": self.enabled,
            "all_passed": self.all_passed,
            "enabled_count": self.enabled_count,
            "passed_count": self.passed_count,
            "blockers": list(self.blockers),
            "next_actions": list(self.next_actions),
            "recent_timeline": list(self.recent_timeline),
            "harnesses": dict(self.harnesses),
            "passed": self.passed,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Operational Harness",
            "",
            f"- Project: `{self.project_name}`",
            f"- Generated at (UTC): {self.generated_at}",
            f"- Enabled Harnesses: {self.enabled_count}",
            f"- Passed Harnesses: {self.passed_count}/{self.enabled_count}",
            f"- Passed: {'yes' if self.passed else 'no'}",
            "",
            "## Harnesses",
            "",
            "| Harness | Enabled | Passed | Summary |",
            "|:---|:---:|:---:|:---|",
        ]
        for key in ("workflow", "framework", "hooks"):
            item = self.harnesses.get(key, {})
            label = str(item.get("label", key))
            summary = str(item.get("summary", "")).strip() or "-"
            lines.append(
                f"| {label} | {'yes' if item.get('enabled') else 'no'} | {'yes' if item.get('passed') else 'no'} | {summary} |"
            )
        lines.extend(["", "## Blockers", ""])
        if self.blockers:
            for blocker in self.blockers:
                lines.append(f"- {blocker}")
        else:
            lines.append("- 当前没有运行时 harness 阻塞项。")
        lines.extend(["", "## Next Actions", ""])
        if self.next_actions:
            for action in self.next_actions:
                lines.append(f"- {action}")
        else:
            lines.append("- 当前 workflow / framework / hook harness 已形成统一交付证据。")
        if self.recent_timeline:
            lines.extend(["", "## Recent Operational Timeline", ""])
            for item in self.recent_timeline:
                timestamp = str(item.get("timestamp", "")).strip() or "-"
                title = str(item.get("title", "")).strip() or str(item.get("kind", "")).strip()
                message = str(item.get("message", "")).strip() or "-"
                lines.append(f"- {timestamp} · {title} · {message}")
        return "\n".join(lines).rstrip() + "\n"


class OperationalHarnessBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.project_name = self.project_dir.name

    def build(
        self, *, hook_limit: int = 20, write_reports: bool = True
    ) -> OperationalHarnessReport:
        payload = build_operational_harness_payload(
            self.project_dir,
            hook_limit=max(hook_limit, 1),
            write_reports=write_reports,
        )
        harnesses = payload.get("harnesses", {}) if isinstance(payload, dict) else {}
        if not isinstance(harnesses, dict):
            harnesses = {}

        report = OperationalHarnessReport(project_name=self.project_name)
        report.all_passed = (
            bool(payload.get("all_passed", True)) if isinstance(payload, dict) else True
        )
        report.recent_timeline = (
            list(payload.get("recent_timeline", [])) if isinstance(payload, dict) else []
        )

        for key in ("workflow", "framework", "hooks"):
            item = harnesses.get(key, {})
            if not isinstance(item, dict):
                continue
            summary = str(item.get("summary", "")).strip()
            if not summary:
                blockers = item.get("blockers")
                if isinstance(blockers, list) and blockers:
                    summary = "；".join(
                        str(part).strip() for part in blockers[:2] if str(part).strip()
                    )
            report.harnesses[key] = {
                "kind": str(item.get("kind", key)),
                "label": str(item.get("label", key)),
                "enabled": bool(item.get("enabled", False)),
                "passed": bool(item.get("passed", False)),
                "summary": summary or ("未启用" if not item.get("enabled") else "已通过"),
                "json_file": str(item.get("json_file", "")).strip(),
                "report_file": str(item.get("report_file", "")).strip(),
                "blockers": (
                    list(item.get("blockers", [])) if isinstance(item.get("blockers"), list) else []
                ),
                "next_actions": (
                    list(item.get("next_actions", []))
                    if isinstance(item.get("next_actions"), list)
                    else []
                ),
            }
            if item.get("enabled"):
                report.enabled_count += 1
            if item.get("enabled") and item.get("passed"):
                report.passed_count += 1
            if item.get("enabled") and not item.get("passed"):
                blockers = item.get("blockers")
                if isinstance(blockers, list):
                    report.blockers.extend(
                        str(blocker).strip() for blocker in blockers if str(blocker).strip()
                    )
                next_actions = item.get("next_actions")
                if isinstance(next_actions, list):
                    report.next_actions.extend(
                        str(action).strip() for action in next_actions if str(action).strip()
                    )

        if not report.next_actions and report.enabled:
            report.next_actions.append(
                "当前三个运行时 harness 已统一通过，可直接作为恢复与发布摘要真源。"
            )
        report.blockers = list(dict.fromkeys(report.blockers))
        report.next_actions = list(dict.fromkeys(report.next_actions))
        return report

    def write(self, report: OperationalHarnessReport) -> dict[str, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base = self.output_dir / f"{self.project_name}-operational-harness"
        md_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"markdown": md_path, "json": json_path}
