from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..artifact_utils import resolve_current_artifact_prefix
from .repo_map import RepoMapBuilder, RepoMapItem


def _tokenize(text: str) -> set[str]:
    return {token for token in re.split(r"[^a-zA-Z0-9_\-/]+", text.lower()) if token}


@dataclass
class ImpactItem:
    name: str
    path: str
    reason: str
    category: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "reason": self.reason,
            "category": self.category,
            "confidence": self.confidence,
        }


@dataclass
class ImpactAnalysisReport:
    project_name: str
    project_path: str
    description: str
    files: list[str]
    risk_level: str
    summary: str
    affected_modules: list[ImpactItem] = field(default_factory=list)
    affected_entry_points: list[ImpactItem] = field(default_factory=list)
    affected_integration_surfaces: list[ImpactItem] = field(default_factory=list)
    regression_focus: list[str] = field(default_factory=list)
    recommended_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "description": self.description,
            "files": self.files,
            "risk_level": self.risk_level,
            "summary": self.summary,
            "affected_modules": [item.to_dict() for item in self.affected_modules],
            "affected_entry_points": [item.to_dict() for item in self.affected_entry_points],
            "affected_integration_surfaces": [
                item.to_dict() for item in self.affected_integration_surfaces
            ],
            "regression_focus": list(self.regression_focus),
            "recommended_steps": list(self.recommended_steps),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Change Impact Analysis",
            "",
            f"- Project: `{self.project_name}`",
            f"- Path: `{self.project_path}`",
            f"- Risk Level: `{self.risk_level}`",
        ]
        if self.description:
            lines.append(f"- Change: {self.description}")
        if self.files:
            lines.append(f"- Files: {', '.join(f'`{f}`' for f in self.files)}")
        lines.extend(["", self.summary, ""])
        self._append_items(lines, "Affected Modules", self.affected_modules)
        self._append_items(lines, "Affected Entry Points", self.affected_entry_points)
        self._append_items(
            lines, "Affected Integration Surfaces", self.affected_integration_surfaces
        )
        lines.extend(["", "## Regression Focus", ""])
        if self.regression_focus:
            for item in self.regression_focus:
                lines.append(f"- {item}")
        else:
            lines.append("- No explicit regression focus was inferred.")
        lines.extend(["", "## Recommended Steps", ""])
        for item in self.recommended_steps:
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _append_items(lines: list[str], title: str, items: list[ImpactItem]) -> None:
        lines.extend(["", f"## {title}", ""])
        if not items:
            lines.append("- None")
            return
        for item in items:
            lines.append(f"- **{item.name}**: `{item.path}`")
            lines.append(f"  - {item.reason} (confidence={item.confidence:.2f})")


class ImpactAnalyzer:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_name = resolve_current_artifact_prefix(
            self.project_dir,
            fallback_name=self.project_dir.name,
        )
        self.repo_map_builder = RepoMapBuilder(self.project_dir)

    def build(self, description: str = "", files: list[str] | None = None) -> ImpactAnalysisReport:
        files = [file for file in (files or []) if file]
        repo_map = self.repo_map_builder.build()
        description_tokens = _tokenize(description)
        normalized_files = [str(Path(file)).replace("\\", "/") for file in files]

        affected_modules = self._score_repo_items(
            repo_map.top_modules, normalized_files, description_tokens, "module"
        )
        affected_entry_points = self._score_repo_items(
            repo_map.entry_points, normalized_files, description_tokens, "entry-point"
        )
        affected_surfaces = self._score_repo_items(
            repo_map.integration_surfaces,
            normalized_files,
            description_tokens,
            "integration-surface",
        )

        risk_level = self._risk_level(affected_modules, affected_entry_points, affected_surfaces)
        summary = self._summary(
            description,
            normalized_files,
            risk_level,
            affected_modules,
            affected_entry_points,
            affected_surfaces,
        )
        regression_focus = self._regression_focus(
            affected_modules, affected_surfaces, normalized_files
        )
        recommended_steps = self._recommended_steps(
            risk_level, affected_modules, affected_surfaces, normalized_files
        )

        return ImpactAnalysisReport(
            project_name=self.project_name,
            project_path=str(self.project_dir),
            description=description,
            files=normalized_files,
            risk_level=risk_level,
            summary=summary,
            affected_modules=affected_modules,
            affected_entry_points=affected_entry_points,
            affected_integration_surfaces=affected_surfaces,
            regression_focus=regression_focus,
            recommended_steps=recommended_steps,
        )

    def write(self, report: ImpactAnalysisReport) -> dict[str, Path]:
        md_path = self.output_dir / f"{self.project_name}-impact-analysis.md"
        json_path = self.output_dir / f"{self.project_name}-impact-analysis.json"
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}

    def _score_repo_items(
        self,
        items: list[RepoMapItem],
        files: list[str],
        description_tokens: set[str],
        category: str,
    ) -> list[ImpactItem]:
        scored: list[ImpactItem] = []
        for item in items:
            confidence = 0.0
            reasons: list[str] = []
            item_path = item.path.replace("\\", "/").lower()
            item_tokens = _tokenize(f"{item.name} {item.path} {item.summary}")

            for file in files:
                file_lower = file.lower()
                top = file_lower.split("/")[0]
                if (
                    item_path == file_lower
                    or item_path.startswith(file_lower)
                    or file_lower.startswith(item_path)
                ):
                    confidence = max(confidence, 0.95)
                    reasons.append("direct file/path overlap")
                elif item_path == top or item_path.startswith(f"{top}/") or top == item_path:
                    confidence = max(confidence, 0.82)
                    reasons.append("same top-level module as changed file")

            overlap = description_tokens & item_tokens
            if overlap:
                confidence = max(confidence, min(0.75, 0.45 + 0.08 * len(overlap)))
                reasons.append(f"keyword overlap: {', '.join(sorted(list(overlap))[:4])}")

            if confidence > 0:
                scored.append(
                    ImpactItem(
                        name=item.name,
                        path=item.path,
                        reason="; ".join(dict.fromkeys(reasons)),
                        category=category,
                        confidence=round(confidence, 2),
                    )
                )

        scored.sort(key=lambda item: item.confidence, reverse=True)
        return scored[:6]

    @staticmethod
    def _risk_level(
        modules: list[ImpactItem],
        entry_points: list[ImpactItem],
        surfaces: list[ImpactItem],
    ) -> str:
        score = 0
        score += len([item for item in modules if item.confidence >= 0.8]) * 2
        score += len([item for item in entry_points if item.confidence >= 0.7]) * 2
        score += len([item for item in surfaces if item.confidence >= 0.7]) * 3
        if score >= 8:
            return "high"
        if score >= 4:
            return "medium"
        return "low"

    @staticmethod
    def _summary(
        description: str,
        files: list[str],
        risk_level: str,
        modules: list[ImpactItem],
        entry_points: list[ImpactItem],
        surfaces: list[ImpactItem],
    ) -> str:
        subject = description or ("、".join(files[:3]) if files else "this change")
        return (
            f"The requested change `{subject}` is assessed as `{risk_level}` risk. "
            f"The strongest signals point to {len(modules)} affected modules, {len(entry_points)} entry points, "
            f"and {len(surfaces)} integration surfaces that should be reviewed before implementation."
        )

    @staticmethod
    def _regression_focus(
        modules: list[ImpactItem], surfaces: list[ImpactItem], files: list[str]
    ) -> list[str]:
        focus: list[str] = []
        joined_paths = " ".join(
            [item.path.lower() for item in modules + surfaces] + [file.lower() for file in files]
        )
        if any(token in joined_paths for token in ["auth", "login", "session", "permission"]):
            focus.append("Authentication, session, and permission regression checks")
        if any(token in joined_paths for token in ["api", "controller", "route", "router"]):
            focus.append("API contract and route-level regression checks")
        if any(token in joined_paths for token in ["component", "ui", "page", "screen", "view"]):
            focus.append("Critical UI paths, navigation, and state transition checks")
        if any(
            token in joined_paths for token in ["db", "database", "repository", "model", "entity"]
        ):
            focus.append("Data model, persistence, and migration regression checks")
        if not focus:
            focus.append(
                "Smoke test the primary user flow and the modules most likely to be touched"
            )
        return focus

    @staticmethod
    def _recommended_steps(
        risk_level: str,
        modules: list[ImpactItem],
        surfaces: list[ImpactItem],
        files: list[str],
    ) -> list[str]:
        steps = [
            "Read the repo map first to confirm the likely entry points and module boundaries.",
            "Limit edits to the highest-confidence modules before expanding the scope.",
        ]
        if risk_level == "high":
            steps.append(
                "Freeze the affected surface in PRD / Architecture / UIUX or patch docs before coding."
            )
        if surfaces:
            steps.append(
                "Re-test the affected integration surfaces before declaring the change complete."
            )
        if files:
            steps.append(
                "Use the changed file list as the minimum review set, then inspect adjacent modules only if impact expands."
            )
        steps.append("Rerun bugfix/runtime/quality validation after implementation.")
        return steps
