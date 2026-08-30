from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..artifact_utils import resolve_current_artifact_prefix
from .analyzer import ProjectAnalyzer

ENTRYPOINT_CANDIDATES = [
    "main.py",
    "app.py",
    "server.py",
    "manage.py",
    "main.go",
    "Program.cs",
    "src/main.ts",
    "src/main.tsx",
    "src/index.ts",
    "src/index.tsx",
    "src/app.tsx",
    "app/page.tsx",
    "pages/index.tsx",
    "package.json",
    "pyproject.toml",
]

INTEGRATION_KEYWORDS = {
    "api": "API boundary",
    "app/api": "API boundary",
    "routes": "Route layer",
    "router": "Route layer",
    "controllers": "Controller layer",
    "services": "Service layer",
    "hooks": "Hook layer",
    "store": "State layer",
    "stores": "State layer",
    "models": "Domain model layer",
    "entities": "Domain model layer",
    "db": "Data access layer",
    "database": "Data access layer",
    "repositories": "Repository layer",
    "components": "UI component layer",
}


@dataclass
class RepoMapItem:
    name: str
    path: str
    summary: str
    score: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "summary": self.summary,
            "score": self.score,
            "details": self.details,
        }


@dataclass
class RepoMapReport:
    project_name: str
    project_path: str
    summary: str
    tech_stack: dict[str, Any]
    entry_points: list[RepoMapItem] = field(default_factory=list)
    top_modules: list[RepoMapItem] = field(default_factory=list)
    integration_surfaces: list[RepoMapItem] = field(default_factory=list)
    key_dependencies: list[RepoMapItem] = field(default_factory=list)
    design_patterns: list[RepoMapItem] = field(default_factory=list)
    risk_points: list[RepoMapItem] = field(default_factory=list)
    recommended_reading_order: list[RepoMapItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "summary": self.summary,
            "tech_stack": self.tech_stack,
            "entry_points": [item.to_dict() for item in self.entry_points],
            "top_modules": [item.to_dict() for item in self.top_modules],
            "integration_surfaces": [item.to_dict() for item in self.integration_surfaces],
            "key_dependencies": [item.to_dict() for item in self.key_dependencies],
            "design_patterns": [item.to_dict() for item in self.design_patterns],
            "risk_points": [item.to_dict() for item in self.risk_points],
            "recommended_reading_order": [
                item.to_dict() for item in self.recommended_reading_order
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Repo Map",
            "",
            f"- Project: `{self.project_name}`",
            f"- Path: `{self.project_path}`",
            "",
            self.summary,
            "",
            "## Tech Stack",
            "",
            f"- Category: `{self.tech_stack.get('category', 'unknown')}`",
            f"- Language: `{self.tech_stack.get('language', 'unknown')}`",
            f"- Framework: `{self.tech_stack.get('framework', 'unknown')}`",
        ]
        if self.tech_stack.get("ui_library"):
            lines.append(f"- UI Library: `{self.tech_stack['ui_library']}`")
        if self.tech_stack.get("state_management"):
            lines.append(f"- State Management: `{self.tech_stack['state_management']}`")
        if self.tech_stack.get("testing_framework"):
            lines.append(f"- Testing: `{self.tech_stack['testing_framework']}`")

        self._append_section(lines, "Likely Entry Points", self.entry_points)
        self._append_section(lines, "Top Modules", self.top_modules)
        self._append_section(lines, "Integration Surfaces", self.integration_surfaces)
        self._append_section(lines, "Key Dependencies", self.key_dependencies)
        self._append_section(lines, "Design Patterns", self.design_patterns)
        self._append_section(lines, "Risk Points", self.risk_points)
        self._append_section(lines, "Recommended Reading Order", self.recommended_reading_order)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _append_section(lines: list[str], title: str, items: list[RepoMapItem]) -> None:
        lines.extend(["", f"## {title}", ""])
        if not items:
            lines.append("- None")
            return
        for item in items:
            lines.append(f"- **{item.name}**: `{item.path}`")
            lines.append(f"  - {item.summary}")


class RepoMapBuilder:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_name = resolve_current_artifact_prefix(
            self.project_dir,
            fallback_name=self.project_dir.name,
        )
        self.analyzer = ProjectAnalyzer(self.project_dir)

    def build(self) -> RepoMapReport:
        report = self.analyzer.analyze()
        tech_stack = report.tech_stack.to_dict()
        entry_points = self._find_entry_points()
        top_modules = self._find_top_modules()
        integration_surfaces = self._find_integration_surfaces()
        key_dependencies = self._collect_dependencies(report)
        design_patterns = self._collect_design_patterns(report)
        risk_points = self._build_risk_points(report, entry_points)
        recommended_reading_order = self._build_reading_order(
            entry_points, top_modules, integration_surfaces
        )

        summary = (
            f"This repository is a `{report.category.value}` codebase built primarily with "
            f"`{tech_stack.get('language', 'unknown')}` and `{tech_stack.get('framework', 'unknown')}`. "
            f"The repo map highlights the most likely entry points, the highest-signal modules, "
            "integration surfaces, and the current risk hotspots before implementation or bugfix work begins."
        )

        return RepoMapReport(
            project_name=self.project_name,
            project_path=str(self.project_dir),
            summary=summary,
            tech_stack=tech_stack,
            entry_points=entry_points,
            top_modules=top_modules,
            integration_surfaces=integration_surfaces,
            key_dependencies=key_dependencies,
            design_patterns=design_patterns,
            risk_points=risk_points,
            recommended_reading_order=recommended_reading_order,
        )

    def write(self, report: RepoMapReport) -> dict[str, Path]:
        md_path = self.output_dir / f"{self.project_name}-repo-map.md"
        json_path = self.output_dir / f"{self.project_name}-repo-map.json"
        md_path.write_text(report.to_markdown(), encoding="utf-8")
        json_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"markdown": md_path, "json": json_path}

    def _find_entry_points(self) -> list[RepoMapItem]:
        items: list[RepoMapItem] = []
        for candidate in ENTRYPOINT_CANDIDATES:
            path = self.project_dir / candidate
            if path.exists():
                items.append(
                    RepoMapItem(
                        name=path.name,
                        path=str(path.relative_to(self.project_dir)),
                        summary="Likely application or build entry point",
                        score=100,
                    )
                )
        return items[:8]

    def _find_top_modules(self) -> list[RepoMapItem]:
        dir_scores: dict[str, int] = defaultdict(int)
        file_counts: dict[str, int] = defaultdict(int)
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if not self.analyzer._should_ignore_dir_name(d)]
            root_path = Path(root)
            if self.analyzer._should_ignore_path(root_path):
                continue
            rel_root = root_path.relative_to(self.project_dir)
            if rel_root == Path("."):
                continue
            bucket = rel_root.parts[0]
            code_files = [
                f
                for f in files
                if Path(f).suffix
                in {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".cs", ".vue"}
            ]
            dir_scores[bucket] += len(code_files)
            file_counts[bucket] += len(code_files)
        ranked = sorted(dir_scores.items(), key=lambda item: item[1], reverse=True)[:8]
        return [
            RepoMapItem(
                name=name,
                path=name,
                summary=f"Top-level module with {file_counts[name]} code files detected",
                score=score,
            )
            for name, score in ranked
        ]

    def _find_integration_surfaces(self) -> list[RepoMapItem]:
        items: list[RepoMapItem] = []
        seen: set[str] = set()
        for root, dirs, _files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if not self.analyzer._should_ignore_dir_name(d)]
            root_path = Path(root)
            if self.analyzer._should_ignore_path(root_path):
                continue
            rel = root_path.relative_to(self.project_dir)
            rel_str = str(rel).replace("\\", "/")
            for keyword, label in INTEGRATION_KEYWORDS.items():
                if rel_str == keyword or rel_str.endswith(f"/{keyword}"):
                    if rel_str in seen:
                        continue
                    seen.add(rel_str)
                    items.append(
                        RepoMapItem(
                            name=rel.name or rel_str,
                            path=rel_str,
                            summary=label,
                            score=len(rel.parts),
                        )
                    )
        return items[:10]

    @staticmethod
    def _collect_dependencies(report) -> list[RepoMapItem]:
        return [
            RepoMapItem(
                name=dep.name,
                path="dependency",
                summary=f"{dep.type} dependency {dep.version or 'unversioned'}",
            )
            for dep in report.tech_stack.dependencies[:12]
        ]

    @staticmethod
    def _collect_design_patterns(report) -> list[RepoMapItem]:
        counter = Counter(pattern.name.value for pattern in report.design_patterns)
        items: list[RepoMapItem] = []
        for pattern in report.design_patterns[:8]:
            items.append(
                RepoMapItem(
                    name=pattern.name.value,
                    path=str(pattern.location),
                    summary=pattern.description
                    or f"Detected {counter[pattern.name.value]} related occurrences",
                    score=int(pattern.confidence * 100),
                )
            )
        return items

    def _build_risk_points(self, report, entry_points: list[RepoMapItem]) -> list[RepoMapItem]:
        risks: list[RepoMapItem] = []
        if not entry_points:
            risks.append(
                RepoMapItem(
                    name="entrypoint-gap",
                    path=".",
                    summary="No obvious application entry point was detected; the host may need manual guidance before implementation.",
                    score=90,
                )
            )
        if report.file_count > 150 and len(report.design_patterns) == 0:
            risks.append(
                RepoMapItem(
                    name="implicit-architecture",
                    path=".",
                    summary="Large codebase with no clear design patterns detected; architecture intent may be implicit rather than documented.",
                    score=80,
                )
            )
        if not any(
            "test" in item.path.lower() or "tests" in item.path.lower()
            for item in entry_points + self._find_top_modules()
        ):
            risks.append(
                RepoMapItem(
                    name="test-coverage-visibility",
                    path="tests/",
                    summary="No obvious test entry surface detected; bugfix and refactor work should verify regression coverage first.",
                    score=75,
                )
            )
        if len(report.tech_stack.dependencies) > 40:
            risks.append(
                RepoMapItem(
                    name="dependency-surface",
                    path="package/requirements manifests",
                    summary="Dependency surface is large; changes may have broader impact than local edits suggest.",
                    score=70,
                )
            )
        return risks[:6]

    @staticmethod
    def _build_reading_order(
        entry_points: list[RepoMapItem],
        top_modules: list[RepoMapItem],
        integration_surfaces: list[RepoMapItem],
    ) -> list[RepoMapItem]:
        ordered: list[RepoMapItem] = []
        ordered.extend(entry_points[:2])
        ordered.extend(top_modules[:3])
        ordered.extend(integration_surfaces[:3])
        deduped: list[RepoMapItem] = []
        seen: set[str] = set()
        for item in ordered:
            if item.path in seen:
                continue
            seen.add(item.path)
            deduped.append(
                RepoMapItem(
                    name=item.name,
                    path=item.path,
                    summary=f"Read early: {item.summary}",
                    score=item.score,
                )
            )
        return deduped[:8]
