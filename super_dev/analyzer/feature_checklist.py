from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..artifact_utils import (
    latest_artifact,
    resolve_active_change_id,
    resolve_current_artifact_prefix,
)


def _normalize_text(value: str) -> str:
    return re.sub(r"[\s`*_#>|:：,，.。/\\\\\\-]+", "", value.strip().lower())


def _tokenize(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-zA-Z0-9_\u4e00-\u9fff]+", value.lower()) if token}


FEATURE_SECTION_KEYWORDS = ("功能", "需求", "feature", "requirement", "scope", "模块", "能力")
GAP_KEYWORDS = ("未实现", "待实现", "未完成", "missing", "not implemented", "todo", "gap")
PRIORITY_PATTERN = re.compile(r"\b(P[0-3])\b", re.IGNORECASE)
EXPLICIT_GAP_SOURCE_KEYWORDS = ("gap", "research", "execution-plan", "coverage", "compare")
EXPLICIT_GAP_SECTION_KEYWORDS = ("missing", "gap", "未实现", "待实现", "差距", "缺口", "coverage")
FEATURE_GROUP_HEADING_KEYWORDS = (
    "核心功能",
    "扩展功能",
    "高级功能",
    "功能模块",
    "核心模块",
    "mvp",
    "phase",
)
NON_FEATURE_HEADING_KEYWORDS = (
    "用户故事",
    "优先级",
    "范围边界",
    "边界场景",
    "异常路径",
    "实施方案",
    "性能要求",
    "安全要求",
    "可用性要求",
    "兼容性要求",
    "商业交付要求",
    "产品概述",
    "市场",
    "澄清",
    "决策",
    "协议",
)


@dataclass
class FeatureChecklistItem:
    title: str
    status: str
    priority: str = ""
    source: str = ""
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "source": self.source,
            "evidence": self.evidence,
        }


@dataclass
class FeatureCoverageReport:
    project_name: str
    project_path: str
    status: str
    summary: str
    prd_path: str = ""
    total_features: int = 0
    covered_count: int = 0
    planned_count: int = 0
    missing_count: int = 0
    unknown_count: int = 0
    high_priority_gap_count: int = 0
    coverage_rate: float | None = None
    items: list[FeatureChecklistItem] = field(default_factory=list)
    explicit_gaps: list[FeatureChecklistItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "status": self.status,
            "summary": self.summary,
            "prd_path": self.prd_path,
            "total_features": self.total_features,
            "covered_count": self.covered_count,
            "planned_count": self.planned_count,
            "missing_count": self.missing_count,
            "unknown_count": self.unknown_count,
            "high_priority_gap_count": self.high_priority_gap_count,
            "coverage_rate": self.coverage_rate,
            "items": [item.to_dict() for item in self.items],
            "explicit_gaps": [item.to_dict() for item in self.explicit_gaps],
        }

    def to_markdown(self) -> str:
        coverage_text = (
            f"{self.coverage_rate:.1f}%" if self.coverage_rate is not None else "unknown"
        )
        lines = [
            "# Feature Checklist",
            "",
            f"- Project: `{self.project_name}`",
            f"- Path: `{self.project_path}`",
            f"- Status: `{self.status}`",
            f"- Coverage: `{coverage_text}`",
            f"- Total features: {self.total_features}",
            f"- Covered: {self.covered_count}",
            f"- Planned: {self.planned_count}",
            f"- Missing: {self.missing_count}",
            f"- Unknown: {self.unknown_count}",
            f"- High priority gaps: {self.high_priority_gap_count}",
            "",
            self.summary,
            "",
            "## Feature Matrix",
            "",
            "| Feature | Status | Priority | Source |",
            "|:---|:---:|:---:|:---|",
        ]
        if self.items:
            for item in self.items:
                lines.append(
                    f"| {item.title} | {item.status} | {item.priority or '-'} | {item.source or '-'} |"
                )
        else:
            lines.append("| - | unknown | - | - |")

        lines.extend(["", "## Explicit Gaps", ""])
        if self.explicit_gaps:
            for item in self.explicit_gaps:
                detail = f"{item.priority} " if item.priority else ""
                lines.append(f"- **{detail}{item.title}** ({item.source})")
                if item.evidence:
                    lines.append(f"  - {item.evidence}")
        else:
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)


class FeatureChecklistBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.active_change_id = resolve_active_change_id(self.project_dir)
        self.project_name = resolve_current_artifact_prefix(
            self.project_dir,
            fallback_name=self.project_dir.name,
        )

    def build(self) -> FeatureCoverageReport:
        prd_path = self._latest("*-prd.md")
        task_path = self._latest("tasks.md", self.project_dir / ".super-dev" / "changes")
        markdown_sources = [
            path
            for path in self.output_dir.glob("*.md")
            if path.name.endswith(".md")
            and (not self.active_change_id or path.name.startswith(f"{self.project_name}-"))
            and "feature-checklist" not in path.name
            and "proof-pack" not in path.name
            and "release-readiness" not in path.name
            and self._is_gap_source(path)
        ]

        features = self._extract_prd_features(prd_path)
        task_states = self._extract_task_states(task_path)
        explicit_gaps = self._extract_explicit_gaps(markdown_sources)

        items = self._merge_feature_states(features, task_states, explicit_gaps)
        covered_count = sum(1 for item in items if item.status == "covered")
        planned_count = sum(1 for item in items if item.status == "planned")
        missing_count = sum(1 for item in items if item.status == "missing")
        unknown_count = sum(1 for item in items if item.status == "unknown")
        high_priority_gap_count = sum(
            1 for item in explicit_gaps if item.priority.upper() in {"P0", "P1"}
        )

        total_features = len(items)
        coverage_rate = (
            None if total_features == 0 else round((covered_count / total_features) * 100, 1)
        )
        if explicit_gaps:
            status = "partial"
        elif total_features == 0:
            status = "unknown"
        elif covered_count == total_features:
            status = "ready"
        else:
            status = "partial"

        summary = self._summary(
            status, coverage_rate, explicit_gaps, total_features, covered_count, unknown_count
        )
        return FeatureCoverageReport(
            project_name=self.project_name,
            project_path=str(self.project_dir),
            status=status,
            summary=summary,
            prd_path=str(prd_path) if prd_path else "",
            total_features=total_features,
            covered_count=covered_count,
            planned_count=planned_count,
            missing_count=missing_count,
            unknown_count=unknown_count,
            high_priority_gap_count=high_priority_gap_count,
            coverage_rate=coverage_rate,
            items=items,
            explicit_gaps=explicit_gaps,
        )

    def write(self, report: FeatureCoverageReport) -> dict[str, Path]:
        md_path = self.output_dir / f"{self.project_name}-feature-checklist.md"
        json_path = self.output_dir / f"{self.project_name}-feature-checklist.json"
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}

    def _latest(self, pattern: str, base_dir: Path | None = None) -> Path | None:
        directory = base_dir or self.output_dir
        if not directory.exists():
            return None
        if pattern == "tasks.md":
            if self.active_change_id:
                active_tasks = directory / self.active_change_id / "tasks.md"
                return active_tasks if active_tasks.is_file() else None
            candidates = [path for path in directory.glob("*/tasks.md") if path.is_file()]
            return max(candidates, key=lambda item: item.stat().st_mtime) if candidates else None
        return latest_artifact(
            directory,
            pattern,
            preferred_prefix=self.project_name,
            strict_prefix=bool(self.active_change_id),
        )

    def _extract_prd_features(self, prd_path: Path | None) -> list[FeatureChecklistItem]:
        if prd_path is None or not prd_path.exists():
            return []
        lines = prd_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        in_feature_section = False
        in_scope_subsection = False
        heading_items: list[FeatureChecklistItem] = []
        bullet_items: list[FeatureChecklistItem] = []
        seen: set[str] = set()
        for raw in lines:
            line = raw.strip()
            heading = re.match(r"^(#{2,4})\s+(.+)$", line)
            if heading:
                level = len(heading.group(1))
                title = heading.group(2).strip()
                normalized_title = _normalize_text(title)
                if level == 2:
                    in_feature_section = title.startswith("2.") or any(
                        keyword in title.lower() for keyword in FEATURE_SECTION_KEYWORDS
                    )
                    in_scope_subsection = False
                    continue
                if in_feature_section and level == 3:
                    title_lower = title.lower()
                    if any(keyword in title for keyword in NON_FEATURE_HEADING_KEYWORDS):
                        in_scope_subsection = False
                        continue
                    in_scope_subsection = True
                    if (
                        normalized_title
                        and normalized_title not in seen
                        and not any(
                            keyword in title_lower for keyword in FEATURE_GROUP_HEADING_KEYWORDS
                        )
                    ):
                        seen.add(normalized_title)
                        heading_items.append(
                            FeatureChecklistItem(
                                title=title,
                                status="unknown",
                                source=str(prd_path.relative_to(self.project_dir)),
                            )
                        )
                elif level >= 3:
                    in_scope_subsection = False
                continue

            if not in_feature_section or not in_scope_subsection:
                continue

            bullet = re.match(r"^(?:[-*]|\d+\.)\s+(?:\*\*)?(.+?)(?:\*\*)?$", line)
            if not bullet:
                continue
            title = bullet.group(1).strip().strip("`")
            normalized_title = _normalize_text(title)
            if len(normalized_title) < 4 or normalized_title in seen:
                continue
            seen.add(normalized_title)
            bullet_items.append(
                FeatureChecklistItem(
                    title=title,
                    status="unknown",
                    source=str(prd_path.relative_to(self.project_dir)),
                )
            )
        return bullet_items or heading_items

    def _extract_task_states(self, task_path: Path | None) -> list[tuple[str, str]]:
        if task_path is None or not task_path.exists():
            return []
        states: list[tuple[str, str]] = []
        for raw in task_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = re.match(r"^[-*]\s+\[(x|X| )\]\s+(.+)$", raw.strip())
            if not match:
                continue
            status = "covered" if match.group(1).lower() == "x" else "planned"
            title = match.group(2).strip()
            states.append((status, title))
        return states

    def _extract_explicit_gaps(self, markdown_sources: list[Path]) -> list[FeatureChecklistItem]:
        items: list[FeatureChecklistItem] = []
        seen: set[tuple[str, str]] = set()
        for file_path in markdown_sources:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            in_gap_section = False
            for raw in lines:
                line = raw.strip()
                if not line:
                    continue
                heading = re.match(r"^(#{2,4})\s+(.+)$", line)
                if heading:
                    in_gap_section = any(
                        keyword in heading.group(2).lower()
                        for keyword in EXPLICIT_GAP_SECTION_KEYWORDS
                    )
                    continue
                priority_match = PRIORITY_PATTERN.search(line)
                has_gap_keyword = any(keyword in line.lower() for keyword in GAP_KEYWORDS) or bool(
                    priority_match
                )
                if not in_gap_section and not priority_match:
                    continue
                if not has_gap_keyword:
                    continue
                candidate = self._extract_gap_title(line)
                if not candidate:
                    continue
                priority = priority_match.group(1).upper() if priority_match else ""
                key = (file_path.name, _normalize_text(candidate))
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    FeatureChecklistItem(
                        title=candidate,
                        status="missing",
                        priority=priority,
                        source=str(file_path.relative_to(self.project_dir)),
                        evidence=line,
                    )
                )
        return items

    def _is_gap_source(self, file_path: Path) -> bool:
        name = file_path.name.lower()
        return any(keyword in name for keyword in EXPLICIT_GAP_SOURCE_KEYWORDS)

    def _extract_gap_title(self, line: str) -> str:
        table_cells = [cell.strip() for cell in line.strip("|").split("|") if cell.strip()]
        if len(table_cells) >= 2 and PRIORITY_PATTERN.fullmatch(table_cells[0].strip()):
            return table_cells[1]
        cleaned = re.sub(r"^[\-\*\d\.\s]+", "", line)
        cleaned = PRIORITY_PATTERN.sub("", cleaned, count=1).strip(" -:：|")
        for keyword in GAP_KEYWORDS:
            cleaned = cleaned.replace(keyword, "").strip(" -:：|")
        return cleaned[:120].strip()

    def _merge_feature_states(
        self,
        features: list[FeatureChecklistItem],
        task_states: list[tuple[str, str]],
        explicit_gaps: list[FeatureChecklistItem],
    ) -> list[FeatureChecklistItem]:
        if not features and explicit_gaps:
            return explicit_gaps

        result: list[FeatureChecklistItem] = []
        for feature in features:
            state = "unknown"
            priority = ""
            for gap in explicit_gaps:
                if self._is_related(feature.title, gap.title):
                    state = "missing"
                    priority = gap.priority
                    break
            if state == "unknown":
                for task_status, task_title in task_states:
                    if self._is_related(feature.title, task_title):
                        state = task_status
                        break
            result.append(
                FeatureChecklistItem(
                    title=feature.title,
                    status=state,
                    priority=priority,
                    source=feature.source,
                )
            )
        for gap in explicit_gaps:
            if not any(self._is_related(item.title, gap.title) for item in result):
                result.append(gap)
        return result

    def _is_related(self, left: str, right: str) -> bool:
        left_normalized = _normalize_text(left)
        right_normalized = _normalize_text(right)
        if not left_normalized or not right_normalized:
            return False
        if left_normalized in right_normalized or right_normalized in left_normalized:
            return True
        left_tokens = _tokenize(left)
        right_tokens = _tokenize(right)
        overlap = left_tokens & right_tokens
        return len(overlap) >= 2

    def _summary(
        self,
        status: str,
        coverage_rate: float | None,
        explicit_gaps: list[FeatureChecklistItem],
        total_features: int,
        covered_count: int,
        unknown_count: int,
    ) -> str:
        if status == "unknown":
            return "当前没有足够的 PRD / gap 证据来判断范围覆盖率。"
        if status == "ready":
            return (
                f"当前已识别 {total_features} 个功能项，其中 {covered_count} 个已覆盖，"
                "未发现明确的高优先级范围缺口。"
            )
        priorities = [item.priority for item in explicit_gaps if item.priority]
        priority_text = "、".join(sorted(dict.fromkeys(priorities))) if priorities else "未分级"
        coverage_text = f"{coverage_rate:.1f}%" if coverage_rate is not None else "unknown"
        return (
            f"当前范围覆盖率约为 {coverage_text}。已识别 {len(explicit_gaps)} 个明确缺口"
            f"（优先级：{priority_text}），且仍有 {unknown_count} 个功能项未获得足够实现证据。"
        )
