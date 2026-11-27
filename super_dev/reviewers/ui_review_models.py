"""UI review reports and HTML inspection helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from ..evidence_contract import EvidenceStatus
from .ui_review_evidence import (
    LABELS,
    STATUS_LABELS,
    UIResult,
    aggregate_ui_status,
    ui_result_details,
    ui_status_ok,
)


@dataclass
class UIReviewFinding:
    level: str
    title: str
    description: str
    recommendation: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "evidence": list(self.evidence),
        }


@dataclass
class UIReviewReport:
    project_name: str
    score: int
    findings: list[UIReviewFinding] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    alignment_summary: dict[str, Any] = field(default_factory=dict)
    results: tuple[UIResult, ...] = ()
    source_inputs: tuple[Path, ...] = ()
    source_complete: bool = False

    @property
    def status(self) -> EvidenceStatus:
        return aggregate_ui_status(self.results)

    @property
    def source_status(self) -> EvidenceStatus:
        if self.critical_count:
            return EvidenceStatus.FAIL
        if not self.source_complete:
            return EvidenceStatus.BLOCKED
        gaps = (
            "ui_contract",
            "emoji_policy",
            "banned_patterns",
            "design_tokens",
            "theme_entry",
            "navigation_shell",
            "component_imports",
            "icon_system",
            "font_pair",
            "component_ecosystem",
            "source_claude_design_protocol",
            "screen_recipes",
            "design_context_protocol",
            "tweak_strategy",
            "verification_handoff",
            "framework_playbook",
            "framework_execution",
            "brand_signal_manifest",
            "proof_composition_rules",
            "component_craft_requirements",
            "layout_tension_rules",
        )
        if self.score < 80 or any(
            self.alignment_summary.get(key, {}).get("passed") is False for key in gaps
        ):
            return EvidenceStatus.FAIL
        return EvidenceStatus.PASS

    @property
    def critical_count(self) -> int:
        return sum(1 for item in self.findings if item.level == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for item in self.findings if item.level == "high")

    @property
    def medium_count(self) -> int:
        return sum(1 for item in self.findings if item.level == "medium")

    @property
    def passed(self) -> bool:
        return ui_status_ok(self.status)

    @property
    def executive_summary(self) -> str:
        summary = ui_result_details(self.results) or "未取得当前的三份独立结果。"
        return f"UI 验收：{STATUS_LABELS[self.status]}。{summary} 用户预览确认另行记录。"

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "score": self.score,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "passed": self.passed,
            "status": self.status.value,
            "schema_version": 1,
            "results": {result.kind: result.summary() for result in self.results},
            "strengths": list(self.strengths),
            "notes": list(self.notes),
            "alignment_summary": dict(self.alignment_summary),
            "findings": [item.to_dict() for item in self.findings],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# {self.project_name} - UI 审查报告",
            "",
            (
                f"- **源码规则分**: {self.score}/100（不代表视觉评审）"
                if self.status is not EvidenceStatus.NOT_APPLICABLE
                else "- **源码规则分**: 不适用"
            ),
            f"- **结论**: {STATUS_LABELS[self.status]}",
            "",
            "---",
            "",
            "## 高层判断",
            "",
            self.executive_summary,
            "",
            "## 优点",
            "",
        ]
        for result in self.results:
            if result.path:
                lines.append(f"- {LABELS[result.kind]}独立结果：`{result.path.name}`")
            if result.payload.get("uncovered"):
                lines.append(f"- {LABELS[result.kind]}未覆盖：{result.payload['uncovered']}")
            if result.kind == "ui-visual-review":
                for finding in result.payload.get("findings", []):
                    lines.append(
                        f"- 视觉发现｜截图 `{finding['screenshot_id']}`｜{finding['location']}：{finding['observation']}；建议：{finding['recommendation']}"
                    )
        if self.strengths:
            lines.extend(f"- {strength}" for strength in self.strengths)
        else:
            lines.append("- 暂无显著优势记录。")

        lines.extend(["", "## 发现的问题", ""])
        if not self.findings:
            lines.append("- 源码检查未报告额外问题；不代表页面已完成视觉验证。")
        else:
            for index, finding in enumerate(self.findings, 1):
                lines.extend(
                    [
                        f"### {index}. [{finding.level.upper()}] {finding.title}",
                        "",
                        f"**问题**: {finding.description}",
                        "",
                        f"**建议**: {finding.recommendation}",
                    ]
                )
                if finding.evidence:
                    lines.extend(["", "**证据**:"])
                    lines.extend(f"- {item}" for item in finding.evidence)
                lines.append("")

        lines.extend(["## 备注", ""])
        if self.notes:
            lines.extend(f"- {item}" for item in self.notes)
        else:
            lines.append("- 无额外备注。")

        if self.alignment_summary:
            lines.extend(["", "## UI 契约对齐摘要", ""])
            for item in self._alignment_markdown_lines():
                lines.append(f"- {item}")

        # UI/UX 专家视角章节
        expert_findings = [
            f
            for f in self.findings
            if f.title.startswith("[UI 专家]") or f.title.startswith("[UX 专家]")
        ]
        if expert_findings:
            lines.extend(["", "## UI/UX 专家视角", ""])
            ui_items = [f for f in expert_findings if f.title.startswith("[UI 专家]")]
            ux_items = [f for f in expert_findings if f.title.startswith("[UX 专家]")]
            if ui_items:
                lines.append("### UI 专家 (设计Token/品牌一致性/组件状态/反AI模板)")
                lines.append("")
                for finding in ui_items:
                    marker = finding.level.upper()
                    lines.append(
                        f"- [{marker}] {finding.title.replace('[UI 专家] ', '')}: {finding.description}"
                    )
                lines.append("")
            if ux_items:
                lines.append("### UX 专家 (用户旅程/导航层级/表单设计/可访问性)")
                lines.append("")
                for finding in ux_items:
                    marker = finding.level.upper()
                    lines.append(
                        f"- [{marker}] {finding.title.replace('[UX 专家] ', '')}: {finding.description}"
                    )
                lines.append("")

        return "\n".join(lines)

    def alignment_markdown(self) -> str:
        lines = [
            f"# {self.project_name} - UI 契约对齐报告",
            "",
        ]
        for item in self._alignment_markdown_lines():
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)

    def _alignment_markdown_lines(self) -> list[str]:
        items: list[str] = []
        for key, value in self.alignment_summary.items():
            if isinstance(value, dict):
                passed = value.get("passed")
                expected = value.get("expected")
                observed = value.get("observed")
                label = value.get("label", key)
                status = "ok" if passed else "gap"
                if expected or observed:
                    items.append(
                        f"{label}: {status} | expected={expected or '-'} | observed={observed or '-'}"
                    )
                else:
                    items.append(f"{label}: {status}")
            else:
                items.append(f"{key}: {value}")
        return items


class _HTMLSurfaceParser(HTMLParser):
    """轻量 HTML 结构审查器"""

    def __init__(self, trust_terms: tuple[str, ...]):
        super().__init__()
        self.trust_terms = tuple(item.lower() for item in trust_terms)
        self.sections = 0
        self.headings = 0
        self.buttons = 0
        self.links = 0
        self.media = 0
        self.landmarks = 0
        self.nav_links = 0
        self._nav_depth = 0
        self._section_index = 0
        self._section_depth = 0
        self.first_section_text_chars = 0
        self.first_section_cta = 0
        self.first_section_media = 0
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered_tag = tag.lower()
        if lowered_tag in {"section", "article", "aside"}:
            self.sections += 1
            self._section_depth += 1
            if self._section_depth == 1:
                self._section_index += 1
        if lowered_tag in {"h1", "h2", "h3"}:
            self.headings += 1
        if lowered_tag == "button":
            self.buttons += 1
            if self._section_index == 1:
                self.first_section_cta += 1
        if lowered_tag == "a":
            self.links += 1
            if self._nav_depth > 0:
                self.nav_links += 1
            if self._section_index == 1:
                self.first_section_cta += 1
        if lowered_tag in {"img", "picture", "video", "figure", "svg"}:
            self.media += 1
            if self._section_index == 1:
                self.first_section_media += 1
        if lowered_tag in {"header", "main", "nav", "footer", "section"}:
            self.landmarks += 1
        if lowered_tag == "nav":
            self._nav_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lowered_tag = tag.lower()
        if lowered_tag in {"section", "article", "aside"} and self._section_depth > 0:
            self._section_depth -= 1
            if self._section_depth == 0 and self._section_index == 1:
                self._section_index = 99
        if lowered_tag == "nav" and self._nav_depth > 0:
            self._nav_depth -= 1

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._text_parts.append(text.lower())
            if self._section_index == 1:
                self.first_section_text_chars += len(text)

    def summary(self) -> dict[str, int]:
        text_blob = " ".join(self._text_parts)
        trust_hits = sum(1 for item in self.trust_terms if item in text_blob)
        return {
            "sections": self.sections,
            "headings": self.headings,
            "buttons": self.buttons,
            "links": self.links,
            "media": self.media,
            "landmarks": self.landmarks,
            "nav_links": self.nav_links,
            "first_section_text_chars": self.first_section_text_chars,
            "first_section_cta": self.first_section_cta,
            "first_section_media": self.first_section_media,
            "trust_hits": trust_hits,
        }
