"""
开发：Excellent（11964948@qq.com）
功能：Hook 执行审计与发布前证据
作用：汇总 hook history，识别失败/阻断结果，生成独立 harness 报告
创建时间：2026-04-06
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .hooks.manager import HookManager


@dataclass
class HookHarnessReport:
    project_name: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enabled: bool = False
    total_events: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    source_files: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.enabled and not self.blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "enabled": self.enabled,
            "total_events": self.total_events,
            "failed_count": self.failed_count,
            "blocked_count": self.blocked_count,
            "recent_events": list(self.recent_events),
            "blockers": list(self.blockers),
            "next_actions": list(self.next_actions),
            "passed": self.passed,
            "source_files": dict(self.source_files),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Hook Harness",
            "",
            f"- Project: `{self.project_name}`",
            f"- Generated at (UTC): {self.generated_at}",
            f"- Enabled: {'yes' if self.enabled else 'no'}",
            f"- Passed: {'yes' if self.passed else 'no'}",
        ]
        if not self.enabled:
            lines.extend(["", "当前项目未检测到 hook 执行历史。", ""])
            return "\n".join(lines)

        lines.extend(
            [
                f"- Total events: {self.total_events}",
                f"- Historical failed: {self.failed_count}",
                f"- Historical blocked: {self.blocked_count}",
                "",
                "## Recent Events",
                "",
            ]
        )
        if self.recent_events:
            for item in self.recent_events:
                lines.append(
                    f"- {item.get('timestamp', '-')}: {item.get('event', '-')} / {item.get('phase') or '-'} / {item.get('hook_name', '-')} / {'blocked' if item.get('blocked') else ('ok' if item.get('success') else 'failed')}"
                )
        else:
            lines.append("- 当前没有可展示的 hook 历史。")

        lines.extend(["", "## Blockers", ""])
        if self.blockers:
            for blocker in self.blockers:
                lines.append(f"- {blocker}")
        else:
            lines.append("- 当前没有 hook 审计阻塞项。")

        lines.extend(["", "## Next Actions", ""])
        if self.next_actions:
            for action in self.next_actions:
                lines.append(f"- {action}")
        else:
            lines.append("- 当前 hook 审计证据已满足发布前要求。")
        return "\n".join(lines).rstrip() + "\n"


class HookHarnessBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.project_name = self.project_dir.name

    def build(self, limit: int = 20) -> HookHarnessReport:
        report = HookHarnessReport(project_name=self.project_name)
        history_path = HookManager.hook_history_file(self.project_dir)
        if not history_path.exists():
            return report

        items = HookManager.load_recent_history(self.project_dir, limit=max(limit, 1))
        report.enabled = True
        report.source_files["hook_history"] = str(history_path)
        report.recent_events = [item.to_dict() for item in items]
        report.total_events = len(
            [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        )
        report.failed_count = sum(1 for item in items if not item.success)
        report.blocked_count = sum(1 for item in items if item.blocked)
        current = HookManager.latest_results(items)
        unresolved_blocked = sum(1 for item in current if item.blocked)
        unresolved_failed = sum(1 for item in current if not item.success)

        if unresolved_blocked:
            report.blockers.append(
                f"同一 Hook/事件/阶段/来源的最近结果中仍有 {unresolved_blocked} 条阻断事件"
            )
        if unresolved_failed and not unresolved_blocked:
            report.blockers.append(
                f"同一 Hook/事件/阶段/来源的最近结果中仍有 {unresolved_failed} 条失败事件"
            )

        if report.blockers:
            report.next_actions.append(
                "处理最近仍未解除的 Hook 阻断后重试；不自动放宽安全策略，不删除历史记录。"
            )
        else:
            report.next_actions.append("当前 Hook 最近结果已通过，历史失败记录仍保留。")
        return report

    def write(self, report: HookHarnessReport) -> dict[str, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base = self.output_dir / f"{self.project_name}-hook-harness"
        md_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}
