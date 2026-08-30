"""
需求追溯矩阵生成器

开发：Excellent（11964948@qq.com）
功能：将 proposal.md / spec.md 中的 SHALL/MUST/SHOULD/MAY 需求与代码实现、测试关联
作用：生成可审计的追溯矩阵与验收检查清单，受 Gauge/Cucumber BDD 理念启发
创建时间：2025-12-30
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class TracedRequirement:
    """追溯需求条目"""

    id: str  # REQ-001
    text: str  # 原始需求描述
    priority: str  # SHALL/MUST/SHOULD/MAY
    source: str  # 来源文件和行号
    status: str = "uncovered"  # covered/uncovered/partial
    implementations: list[str] = field(default_factory=list)  # 相关代码文件
    tests: list[str] = field(default_factory=list)  # 相关测试文件
    verification: str = ""  # 验证方式

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "priority": self.priority,
            "source": self.source,
            "status": self.status,
            "implementations": self.implementations,
            "tests": self.tests,
            "verification": self.verification,
        }


@dataclass
class TraceabilityMatrix:
    """追溯矩阵"""

    change_id: str
    requirements: list[TracedRequirement] = field(default_factory=list)
    generated_at: str = ""

    @property
    def coverage_rate(self) -> float:
        """需求覆盖率 (0-100)"""
        if not self.requirements:
            return 0.0
        covered = sum(1 for r in self.requirements if r.status == "covered")
        return (covered / len(self.requirements)) * 100

    @property
    def shall_coverage(self) -> float:
        """SHALL/MUST 需求覆盖率 (0-100)"""
        shall_reqs = [r for r in self.requirements if r.priority in ("SHALL", "MUST")]
        if not shall_reqs:
            return 100.0
        covered = sum(1 for r in shall_reqs if r.status == "covered")
        return (covered / len(shall_reqs)) * 100

    @property
    def total_count(self) -> int:
        return len(self.requirements)

    @property
    def covered_count(self) -> int:
        return sum(1 for r in self.requirements if r.status == "covered")

    @property
    def partial_count(self) -> int:
        return sum(1 for r in self.requirements if r.status == "partial")

    @property
    def uncovered_count(self) -> int:
        return sum(1 for r in self.requirements if r.status == "uncovered")

    def to_markdown(self) -> str:
        """生成 Markdown 追溯矩阵"""
        lines: list[str] = []
        lines.append(f"# 需求追溯矩阵: {self.change_id}")
        lines.append("")
        lines.append(f"> 生成时间: {self.generated_at}")
        lines.append("")

        # 总览
        lines.append("## 覆盖率总览")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 总需求数 | {self.total_count} |")
        lines.append(f"| 已覆盖 | {self.covered_count} |")
        lines.append(f"| 部分覆盖 | {self.partial_count} |")
        lines.append(f"| 未覆盖 | {self.uncovered_count} |")
        lines.append(f"| 总覆盖率 | {self.coverage_rate:.1f}% |")
        lines.append(f"| SHALL/MUST 覆盖率 | {self.shall_coverage:.1f}% |")
        lines.append("")

        # 详细矩阵
        lines.append("## 追溯详情")
        lines.append("")
        lines.append("| ID | 优先级 | 需求描述 | 状态 | 实现文件 | 测试文件 |")
        lines.append("|-----|--------|----------|------|----------|----------|")
        for req in self.requirements:
            status_icon = {"covered": "ok", "partial": "~", "uncovered": "--"}.get(req.status, "--")
            impl_str = ", ".join(req.implementations[:3]) or "-"
            test_str = ", ".join(req.tests[:3]) or "-"
            text_short = req.text[:60] + "..." if len(req.text) > 60 else req.text
            lines.append(
                f"| {req.id} | {req.priority} | {text_short} "
                f"| {status_icon} | {impl_str} | {test_str} |"
            )
        lines.append("")

        # 未覆盖需求清单
        uncovered = [r for r in self.requirements if r.status == "uncovered"]
        if uncovered:
            lines.append("## 未覆盖需求")
            lines.append("")
            for req in uncovered:
                lines.append(f"- **{req.id}** [{req.priority}]: {req.text}")
                lines.append(f"  - 来源: {req.source}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "generated_at": self.generated_at,
            "coverage_rate": round(self.coverage_rate, 1),
            "shall_coverage": round(self.shall_coverage, 1),
            "total": self.total_count,
            "covered": self.covered_count,
            "partial": self.partial_count,
            "uncovered": self.uncovered_count,
            "requirements": [r.to_dict() for r in self.requirements],
        }


# 匹配 SHALL/MUST/SHOULD/MAY 句式的正则
_REQUIREMENT_PATTERN = re.compile(
    r"^(.*?)\b(SHALL|MUST|SHOULD|MAY)\b\s+(.+)$",
    re.IGNORECASE,
)

# 匹配 spec 中 Requirement 标题行
_REQ_HEADING_PATTERN = re.compile(
    r"^###\s+Requirement:\s*(.+)$",
)


def _extract_keywords(text: str) -> list[str]:
    """从需求文本中提取搜索关键词"""
    # 去掉常见停用词，提取有意义的词
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "must",
        "can",
        "need",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "and",
        "or",
        "but",
        "not",
        "no",
        "all",
        "any",
        "each",
        "every",
        "that",
        "this",
        "it",
        "its",
        "their",
        "them",
        "they",
        "he",
        "she",
        "we",
        "you",
        "able",
        "when",
        "if",
        "then",
        "than",
        "also",
        "just",
        "only",
        "both",
    }
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower())
    return [w for w in words if w not in stop_words]


class RequirementTracer:
    """需求追溯器"""

    def __init__(self, project_dir: Path | str):
        self.project_dir = Path(project_dir).resolve()
        self.changes_dir = self.project_dir / ".super-dev" / "changes"

    def extract_requirements(self, change_id: str) -> list[TracedRequirement]:
        """从 proposal.md 和 spec.md 提取 SHALL/MUST/SHOULD/MAY 需求"""
        requirements: list[TracedRequirement] = []
        change_dir = self.changes_dir / change_id
        if not change_dir.exists():
            return requirements

        req_counter = 0

        # 从 proposal.md 提取
        proposal_file = change_dir / "proposal.md"
        if proposal_file.exists():
            content = proposal_file.read_text(encoding="utf-8")
            for line_num, line in enumerate(content.splitlines(), 1):
                match = _REQUIREMENT_PATTERN.match(line.strip())
                if match:
                    req_counter += 1
                    priority = match.group(2).upper()
                    text = match.group(3).strip()
                    prefix = match.group(1).strip()
                    full_text = f"{prefix} {text}".strip() if prefix else text
                    requirements.append(
                        TracedRequirement(
                            id=f"REQ-{req_counter:03d}",
                            text=full_text,
                            priority=priority,
                            source=f"proposal.md:{line_num}",
                        )
                    )

        # 从 specs/*.md 提取
        specs_dir = change_dir / "specs"
        if specs_dir.exists():
            for spec_file in sorted(specs_dir.rglob("spec.md")):
                content = spec_file.read_text(encoding="utf-8")
                relative_path = spec_file.relative_to(change_dir).as_posix()
                current_req_name = ""

                for line_num, line in enumerate(content.splitlines(), 1):
                    heading_match = _REQ_HEADING_PATTERN.match(line.strip())
                    if heading_match:
                        current_req_name = heading_match.group(1).strip()

                    match = _REQUIREMENT_PATTERN.match(line.strip())
                    if match:
                        req_counter += 1
                        priority = match.group(2).upper()
                        text = match.group(3).strip()
                        prefix = match.group(1).strip()
                        full_text = f"{prefix} {text}".strip() if prefix else text
                        if current_req_name and current_req_name not in full_text:
                            full_text = f"[{current_req_name}] {full_text}"
                        requirements.append(
                            TracedRequirement(
                                id=f"REQ-{req_counter:03d}",
                                text=full_text,
                                priority=priority,
                                source=f"{relative_path}:{line_num}",
                            )
                        )

        return requirements

    def trace_to_code(self, requirements: list[TracedRequirement]) -> list[TracedRequirement]:
        """将需求追溯到代码实现（基于关键词匹配）"""
        # 收集项目中的 Python/JS/TS 源码文件
        source_files = self._collect_source_files()
        file_contents: dict[str, str] = {}
        for fp in source_files:
            try:
                file_contents[fp.relative_to(self.project_dir).as_posix()] = fp.read_text(
                    encoding="utf-8"
                ).lower()
            except (OSError, UnicodeDecodeError):
                continue

        for req in requirements:
            keywords = _extract_keywords(req.text)
            if not keywords:
                continue
            matched_files: list[str] = []
            for rel_path, content in file_contents.items():
                hits = sum(1 for kw in keywords if kw in content)
                if hits >= max(2, len(keywords) // 3):
                    matched_files.append(rel_path)
            req.implementations = sorted(matched_files)[:10]

        return requirements

    def trace_to_tests(self, requirements: list[TracedRequirement]) -> list[TracedRequirement]:
        """将需求追溯到测试文件"""
        test_files = self._collect_test_files()
        file_contents: dict[str, str] = {}
        for fp in test_files:
            try:
                file_contents[fp.relative_to(self.project_dir).as_posix()] = fp.read_text(
                    encoding="utf-8"
                ).lower()
            except (OSError, UnicodeDecodeError):
                continue

        for req in requirements:
            keywords = _extract_keywords(req.text)
            if not keywords:
                continue
            matched_files: list[str] = []
            for rel_path, content in file_contents.items():
                hits = sum(1 for kw in keywords if kw in content)
                if hits >= max(2, len(keywords) // 3):
                    matched_files.append(rel_path)
            req.tests = sorted(matched_files)[:10]

        return requirements

    def _update_status(self, requirements: list[TracedRequirement]) -> list[TracedRequirement]:
        """根据实现和测试追溯结果更新覆盖状态"""
        for req in requirements:
            has_impl = len(req.implementations) > 0
            has_tests = len(req.tests) > 0
            if has_impl and has_tests:
                req.status = "covered"
                req.verification = "代码实现 + 测试覆盖"
            elif has_impl or has_tests:
                req.status = "partial"
                if has_impl:
                    req.verification = "仅代码实现，缺少测试"
                else:
                    req.verification = "仅测试存在，缺少实现代码"
            else:
                req.status = "uncovered"
                req.verification = "未找到相关实现或测试"
        return requirements

    def generate_matrix(self, change_id: str) -> TraceabilityMatrix:
        """生成完整追溯矩阵"""
        requirements = self.extract_requirements(change_id)
        requirements = self.trace_to_code(requirements)
        requirements = self.trace_to_tests(requirements)
        requirements = self._update_status(requirements)

        return TraceabilityMatrix(
            change_id=change_id,
            requirements=requirements,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

    def generate_acceptance_checklist(self, change_id: str) -> str:
        """从需求自动生成验收检查清单"""
        requirements = self.extract_requirements(change_id)
        if not requirements:
            return f"# 验收检查清单: {change_id}\n\n> 未提取到 SHALL/MUST/SHOULD/MAY 需求。\n"

        lines: list[str] = []
        lines.append(f"# 验收检查清单: {change_id}")
        lines.append("")
        lines.append(
            f"> 自动生成于: " f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append(f"> 总需求数: {len(requirements)}")
        lines.append("")

        # 按优先级分组
        priority_order = ["SHALL", "MUST", "SHOULD", "MAY"]
        for priority in priority_order:
            group = [r for r in requirements if r.priority == priority]
            if not group:
                continue
            lines.append(f"## {priority} 需求 ({len(group)} 项)")
            lines.append("")
            for req in group:
                lines.append(f"- [ ] **{req.id}**: {req.text}")
                lines.append(f"  - 来源: `{req.source}`")
                lines.append("  - 验证方式: _待填写_")
                lines.append("  - 验收结果: _待填写_")
            lines.append("")

        lines.append("## 签核")
        lines.append("")
        lines.append("- [ ] 开发确认所有 SHALL/MUST 需求已实现")
        lines.append("- [ ] 测试确认所有 SHALL/MUST 需求已验证")
        lines.append("- [ ] 产品确认验收通过")
        lines.append("")

        return "\n".join(lines)

    def generate_governance_report(self) -> str:
        """生成治理总报告，汇总所有变更的追溯情况"""
        if not self.changes_dir.exists():
            return "# 治理报告\n\n> 未找到 .super-dev/changes/ 目录。\n"

        lines: list[str] = []
        lines.append("# Super Dev 治理总报告")
        lines.append("")
        lines.append(
            f"> 生成时间: " f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append("")

        change_dirs = sorted(
            [d for d in self.changes_dir.iterdir() if d.is_dir() and not d.name.startswith(".")],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )

        if not change_dirs:
            lines.append("> 暂无活跃变更。")
            return "\n".join(lines)

        lines.append("## 变更总览")
        lines.append("")
        lines.append("| 变更 ID | 需求数 | 覆盖率 | SHALL 覆盖率 | 未覆盖 |")
        lines.append("|---------|--------|--------|-------------|--------|")

        all_matrices: list[TraceabilityMatrix] = []
        for change_dir in change_dirs:
            matrix = self.generate_matrix(change_dir.name)
            all_matrices.append(matrix)
            lines.append(
                f"| {matrix.change_id} | {matrix.total_count} "
                f"| {matrix.coverage_rate:.1f}% "
                f"| {matrix.shall_coverage:.1f}% "
                f"| {matrix.uncovered_count} |"
            )
        lines.append("")

        # 汇总统计
        total_reqs = sum(m.total_count for m in all_matrices)
        total_covered = sum(m.covered_count for m in all_matrices)
        total_uncovered = sum(m.uncovered_count for m in all_matrices)
        overall_rate = (total_covered / total_reqs * 100) if total_reqs > 0 else 0.0

        lines.append("## 汇总")
        lines.append("")
        lines.append(f"- 活跃变更数: {len(all_matrices)}")
        lines.append(f"- 总需求数: {total_reqs}")
        lines.append(f"- 已覆盖: {total_covered}")
        lines.append(f"- 未覆盖: {total_uncovered}")
        lines.append(f"- 整体覆盖率: {overall_rate:.1f}%")
        lines.append("")

        # 高风险条目
        high_risk = []
        for matrix in all_matrices:
            for req in matrix.requirements:
                if req.priority in ("SHALL", "MUST") and req.status == "uncovered":
                    high_risk.append((matrix.change_id, req))

        if high_risk:
            lines.append("## 高风险: 未覆盖的 SHALL/MUST 需求")
            lines.append("")
            for change_id, req in high_risk:
                lines.append(f"- **[{change_id}] {req.id}** [{req.priority}]: {req.text}")
                lines.append(f"  - 来源: `{req.source}`")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _collect_source_files(self) -> list[Path]:
        """收集项目中的源码文件（排除测试和虚拟环境）"""
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}
        exclude_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            ".tox",
            ".mypy_cache",
            ".ruff_cache",
        }
        results: list[Path] = []
        for item in self.project_dir.rglob("*"):
            if not item.is_file():
                continue
            if item.suffix not in extensions:
                continue
            parts = item.relative_to(self.project_dir).parts
            if any(p in exclude_dirs for p in parts):
                continue
            # 排除测试文件
            if any(p.startswith("test") for p in parts):
                continue
            if item.name.startswith("test_") or item.name.endswith("_test.py"):
                continue
            results.append(item)
        return sorted(results)

    def _collect_test_files(self) -> list[Path]:
        """收集项目中的测试文件"""
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx"}
        exclude_dirs = {
            ".git",
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            ".tox",
            ".mypy_cache",
            ".ruff_cache",
        }
        results: list[Path] = []
        for item in self.project_dir.rglob("*"):
            if not item.is_file():
                continue
            if item.suffix not in extensions:
                continue
            parts = item.relative_to(self.project_dir).parts
            if any(p in exclude_dirs for p in parts):
                continue
            # 只收集测试文件
            relative_path = item.relative_to(self.project_dir).as_posix()
            is_test = (
                item.name.startswith("test_")
                or item.name.endswith("_test.py")
                or item.name.endswith(".test.js")
                or item.name.endswith(".test.ts")
                or item.name.endswith(".test.tsx")
                or item.name.endswith(".spec.js")
                or item.name.endswith(".spec.ts")
                or item.name.endswith(".spec.tsx")
                or "tests/" in relative_path
                or "__tests__/" in relative_path
            )
            if is_test:
                results.append(item)
        return sorted(results)
