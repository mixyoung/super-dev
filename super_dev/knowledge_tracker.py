"""
知识引用追踪器

记录 pipeline 执行过程中引用了哪些知识文件，生成知识引用报告。
让知识库从「静态仓库」变成「可追溯治理资产」。

用法:
    tracker = KnowledgeTracker(knowledge_dir="knowledge")
    tracker.track_reference("knowledge/security/01-standards/web-security-complete.md",
                            phase="backend", usage_type="constraint", relevance_score=0.95)
    report = tracker.generate_report("myapp", "run-001")
    tracker.save_report(report, output_dir="output")
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeReference:
    """单条知识引用记录"""

    knowledge_file: str
    """知识文件路径（相对于项目根目录）"""

    phase: str
    """引用阶段: research / docs / spec / frontend / backend / quality / delivery"""

    usage_type: str
    """使用类型: constraint(硬约束) / guidance(指导) / reference(参考)"""

    matched_tags: list[str] = field(default_factory=list)
    """匹配的标签"""

    relevance_score: float = 1.0
    """相关性分数 0‑1"""

    excerpt: str = ""
    """引用的关键内容摘要"""

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    """引用时间戳"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_file": self.knowledge_file,
            "phase": self.phase,
            "usage_type": self.usage_type,
            "matched_tags": self.matched_tags,
            "relevance_score": self.relevance_score,
            "excerpt": self.excerpt,
            "timestamp": self.timestamp,
        }


@dataclass
class KnowledgeTrackingReport:
    """知识引用报告"""

    project_name: str
    pipeline_run_id: str
    timestamp: str
    total_knowledge_files: int
    """知识库总文件数"""

    referenced_files: int
    """引用的文件数（去重）"""

    hit_rate: float
    """命中率 = referenced_files / total_knowledge_files"""

    references: list[KnowledgeReference]
    """所有引用记录"""

    unreferenced_domains: list[str]
    """未引用的领域"""

    coverage_by_domain: dict[str, dict[str, Any]] = field(default_factory=dict)
    """按领域的覆盖率统计"""

    # ------------------------------------------------------------------
    # 输出
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        """生成 Markdown 格式的知识引用报告"""
        lines: list[str] = [
            "# 知识引用追踪报告",
            "",
            f"- **项目**: {self.project_name}",
            f"- **Pipeline Run ID**: {self.pipeline_run_id}",
            f"- **生成时间**: {self.timestamp}",
            "",
            "## 总览",
            "",
            "| 指标 | 值 |",
            "|------|------|",
            f"| 知识库总文件数 | {self.total_knowledge_files} |",
            f"| 引用文件数 | {self.referenced_files} |",
            f"| 命中率 | {self.hit_rate:.1%} |",
            f"| 总引用次数 | {len(self.references)} |",
            "",
        ]

        # 按阶段统计
        phase_counts: dict[str, int] = {}
        for ref in self.references:
            phase_counts[ref.phase] = phase_counts.get(ref.phase, 0) + 1

        if phase_counts:
            lines.append("## 按阶段引用统计")
            lines.append("")
            lines.append("| 阶段 | 引用次数 |")
            lines.append("|------|----------|")
            for phase, count in sorted(phase_counts.items()):
                lines.append(f"| {phase} | {count} |")
            lines.append("")

        # 按使用类型统计
        type_counts: dict[str, int] = {}
        for ref in self.references:
            type_counts[ref.usage_type] = type_counts.get(ref.usage_type, 0) + 1

        if type_counts:
            lines.append("## 按使用类型统计")
            lines.append("")
            lines.append("| 类型 | 引用次数 |")
            lines.append("|------|----------|")
            for utype, count in sorted(type_counts.items()):
                lines.append(f"| {utype} | {count} |")
            lines.append("")

        # 领域覆盖率
        if self.coverage_by_domain:
            lines.append("## 领域覆盖率")
            lines.append("")
            lines.append("| 领域 | 总文件 | 引用文件 | 覆盖率 |")
            lines.append("|------|--------|----------|--------|")
            for domain in sorted(self.coverage_by_domain):
                info = self.coverage_by_domain[domain]
                lines.append(
                    f"| {domain} | {info['total']} | {info['referenced']} | {info['rate']:.0%} |"
                )
            lines.append("")

        # 未引用领域
        if self.unreferenced_domains:
            lines.append("## 未引用领域")
            lines.append("")
            for domain in sorted(self.unreferenced_domains):
                lines.append(f"- {domain}")
            lines.append("")

        # 引用明细
        if self.references:
            lines.append("## 引用明细")
            lines.append("")
            for i, ref in enumerate(self.references, 1):
                lines.append(f"### {i}. {ref.knowledge_file}")
                lines.append("")
                lines.append(f"- **阶段**: {ref.phase}")
                lines.append(f"- **类型**: {ref.usage_type}")
                lines.append(f"- **相关性**: {ref.relevance_score:.2f}")
                if ref.matched_tags:
                    lines.append(f"- **标签**: {', '.join(ref.matched_tags)}")
                if ref.excerpt:
                    lines.append(f"- **摘要**: {ref.excerpt}")
                lines.append("")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """导出 JSON 格式"""
        return {
            "project_name": self.project_name,
            "pipeline_run_id": self.pipeline_run_id,
            "timestamp": self.timestamp,
            "summary": {
                "total_knowledge_files": self.total_knowledge_files,
                "referenced_files": self.referenced_files,
                "hit_rate": round(self.hit_rate, 4),
                "total_references": len(self.references),
            },
            "coverage_by_domain": self.coverage_by_domain,
            "unreferenced_domains": self.unreferenced_domains,
            "references": [ref.to_dict() for ref in self.references],
        }


# ---------------------------------------------------------------------------
# 知识文件索引条目
# ---------------------------------------------------------------------------


@dataclass
class _KnowledgeIndexEntry:
    """内部索引条目"""

    path: str
    """相对路径"""

    domain: str
    """所属领域（顶层目录名）"""

    category: str
    """子类别（如 01-standards, 02-playbooks 等）"""

    title: str
    """从文件名或首行提取的标题"""

    tags: list[str]
    """从文件名与内容提取的标签"""


# ---------------------------------------------------------------------------
# 有效的阶段和使用类型常量
# ---------------------------------------------------------------------------

VALID_PHASES = frozenset(
    {
        "research",
        "docs",
        "spec",
        "frontend",
        "backend",
        "quality",
        "delivery",
    }
)

VALID_USAGE_TYPES = frozenset(
    {
        "constraint",
        "guidance",
        "reference",
    }
)

# 领域 -> 相关阶段映射（用于 find_relevant_knowledge 过滤）
_DOMAIN_PHASE_AFFINITY: dict[str, list[str]] = {
    "product": ["research", "docs", "spec"],
    "design": ["research", "docs", "frontend"],
    "architecture": ["docs", "spec", "backend"],
    "development": ["docs", "spec", "frontend", "backend"],
    "testing": ["quality"],
    "security": ["docs", "backend", "quality"],
    "cicd": ["quality", "delivery"],
    "operations": ["quality", "delivery"],
    "data": ["docs", "backend", "quality"],
    "data-engineering": ["docs", "backend", "quality"],
    "incident": ["quality", "delivery"],
    "ai": ["research", "docs", "quality", "delivery"],
    "00-governance": ["research", "docs", "spec", "quality", "delivery"],
    "frontend": ["frontend", "docs"],
    "backend": ["backend", "docs"],
    "cloud-native": ["backend", "delivery"],
    "devops": ["delivery", "quality"],
    "blockchain": ["backend", "spec"],
    "edge-iot": ["backend", "spec"],
    "industries": ["research", "docs"],
    "low-code": ["frontend", "spec"],
    "mobile": ["frontend", "spec"],
    "quantum": ["research", "spec"],
}


# ---------------------------------------------------------------------------
# KnowledgeTracker
# ---------------------------------------------------------------------------


class KnowledgeTracker:
    """知识引用追踪器

    在 pipeline 执行过程中记录每一次对 knowledge/ 文件的引用，
    最终生成可审计的知识引用报告（Markdown + JSON）。

    Example::

        tracker = KnowledgeTracker("knowledge")
        tracker.track_reference(
            "knowledge/security/01-standards/web-security-complete.md",
            phase="backend",
            usage_type="constraint",
            relevance_score=0.95,
            excerpt="OWASP Top-10 检查清单",
        )
        report = tracker.generate_report("myapp", "run-001")
        tracker.save_report(report)
    """

    def __init__(
        self, knowledge_dir: str = "knowledge", *, project_dir: Path | None = None
    ) -> None:
        self.knowledge_dir = Path(knowledge_dir)
        self._scan_dir = project_dir / self.knowledge_dir if project_dir else self.knowledge_dir
        self.references: list[KnowledgeReference] = []
        self._knowledge_index: dict[str, _KnowledgeIndexEntry] = self._build_index()

    # ------------------------------------------------------------------
    # 索引构建
    # ------------------------------------------------------------------

    def _build_index(self) -> dict[str, _KnowledgeIndexEntry]:
        """构建知识文件索引（路径 -> 索引条目）

        遍历 knowledge_dir 下所有 .md / .txt / .yml / .yaml 文件，
        提取领域、子类别、标题和标签。
        """
        index: dict[str, _KnowledgeIndexEntry] = {}
        if not self._scan_dir.exists():
            return index

        suffixes = {".md", ".txt", ".yml", ".yaml"}
        for filepath in sorted(self._scan_dir.rglob("*")):
            if not filepath.is_file() or filepath.suffix.lower() not in suffixes:
                continue

            relative = filepath.relative_to(self._scan_dir)
            rel_path = str(self.knowledge_dir / relative)
            parts = relative.parts

            domain = parts[0] if len(parts) > 1 else ""
            category = parts[1] if len(parts) > 2 else ""

            title = self._extract_title(filepath)
            tags = self._extract_tags(filepath, domain, category)

            index[rel_path] = _KnowledgeIndexEntry(
                path=rel_path,
                domain=domain,
                category=category,
                title=title,
                tags=tags,
            )

        return index

    @staticmethod
    def _extract_title(filepath: Path) -> str:
        """从文件首行（# 标题）或文件名提取标题"""
        try:
            with open(filepath, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("#"):
                        return line.lstrip("#").strip()
                    if line:
                        return line[:120]
                    break
        except OSError:
            pass
        # fallback: 文件名
        return filepath.stem.replace("-", " ").replace("_", " ").title()

    @staticmethod
    def _extract_tags(filepath: Path, domain: str, category: str) -> list[str]:
        """从文件名和上下文提取标签"""
        tags: list[str] = []
        if domain:
            tags.append(domain)
        if category:
            # 去掉前缀编号 (01-standards -> standards)
            clean_cat = re.sub(r"^\d+-", "", category)
            if clean_cat:
                tags.append(clean_cat)

        # 文件名中的关键词
        stem = filepath.stem.lower()
        for sep in ("-", "_"):
            parts = stem.split(sep)
            tags.extend(p for p in parts if len(p) > 2 and p not in ("complete", "md"))

        return list(dict.fromkeys(tags))  # 去重保序

    # ------------------------------------------------------------------
    # 引用追踪
    # ------------------------------------------------------------------

    def track_reference(
        self,
        knowledge_file: str,
        phase: str,
        usage_type: str,
        relevance_score: float = 1.0,
        excerpt: str = "",
        matched_tags: list[str] | None = None,
    ) -> KnowledgeReference:
        """记录一次知识引用

        Args:
            knowledge_file: 知识文件路径
            phase: 引用阶段（research/docs/spec/frontend/backend/quality/delivery）
            usage_type: 使用类型（constraint/guidance/reference）
            relevance_score: 相关性分数 0‑1
            excerpt: 引用内容摘要
            matched_tags: 匹配的标签（可选，自动推断）

        Returns:
            创建的 KnowledgeReference 实例

        Raises:
            ValueError: 当 phase 或 usage_type 不合法时
        """
        if phase not in VALID_PHASES:
            raise ValueError(f"Invalid phase '{phase}'. Must be one of: {sorted(VALID_PHASES)}")
        if usage_type not in VALID_USAGE_TYPES:
            raise ValueError(
                f"Invalid usage_type '{usage_type}'. Must be one of: {sorted(VALID_USAGE_TYPES)}"
            )
        relevance_score = max(0.0, min(1.0, relevance_score))

        # 自动推断标签
        if matched_tags is None:
            entry = self._knowledge_index.get(knowledge_file)
            matched_tags = list(entry.tags) if entry else []

        ref = KnowledgeReference(
            knowledge_file=knowledge_file,
            phase=phase,
            usage_type=usage_type,
            matched_tags=matched_tags,
            relevance_score=relevance_score,
            excerpt=excerpt,
        )
        self.references.append(ref)
        return ref

    # ------------------------------------------------------------------
    # 知识查找
    # ------------------------------------------------------------------

    def find_relevant_knowledge(
        self,
        query: str,
        phase: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """根据查询和阶段查找相关知识（供 pipeline 使用）

        使用简单的关键词匹配 + 领域-阶段亲和度过滤。

        Args:
            query: 搜索查询文本
            phase: 当前 pipeline 阶段
            top_k: 最多返回条数

        Returns:
            包含 path, title, domain, score, tags 的字典列表，按 score 降序排列
        """
        if not self._knowledge_index:
            return []

        query_lower = query.lower()
        query_tokens = set(re.split(r"\W+", query_lower)) - {"", "the", "and", "for", "with", "a"}

        scored: list[tuple[float, str, _KnowledgeIndexEntry]] = []

        for path, entry in self._knowledge_index.items():
            score = 0.0

            # 1. 关键词匹配（标签 + 标题）
            entry_tokens = set(t.lower() for t in entry.tags)
            entry_tokens.update(re.split(r"\W+", entry.title.lower()))
            overlap = query_tokens & entry_tokens
            if overlap:
                score += len(overlap) / max(len(query_tokens), 1) * 0.6

            # 2. 领域-阶段亲和度
            affinity_phases = _DOMAIN_PHASE_AFFINITY.get(entry.domain, [])
            if phase in affinity_phases:
                score += 0.3

            # 3. 子串匹配 bonus
            for token in query_tokens:
                if len(token) > 3 and token in entry.path.lower():
                    score += 0.1
                    break

            if score > 0:
                scored.append((score, path, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[dict[str, Any]] = []
        for score, path, entry in scored[:top_k]:
            results.append(
                {
                    "path": path,
                    "title": entry.title,
                    "domain": entry.domain,
                    "category": entry.category,
                    "score": round(min(score, 1.0), 4),
                    "tags": entry.tags,
                }
            )
        return results

    # ------------------------------------------------------------------
    # 报告生成
    # ------------------------------------------------------------------

    def generate_report(
        self,
        project_name: str,
        run_id: str | None = None,
    ) -> KnowledgeTrackingReport:
        """生成知识引用报告

        Args:
            project_name: 项目名称
            run_id: Pipeline 运行 ID（不提供则自动生成）

        Returns:
            KnowledgeTrackingReport 实例
        """
        if run_id is None:
            run_id = f"run-{uuid.uuid4().hex[:8]}"

        total_files = len(self._knowledge_index)
        referenced_paths = {ref.knowledge_file for ref in self.references}
        referenced_count = len(referenced_paths)
        hit_rate = referenced_count / total_files if total_files > 0 else 0.0

        # 领域覆盖率
        coverage = self.get_knowledge_coverage()

        # 未引用领域
        unreferenced_domains = [
            domain for domain, info in coverage.items() if info["referenced"] == 0
        ]

        return KnowledgeTrackingReport(
            project_name=project_name,
            pipeline_run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_knowledge_files=total_files,
            referenced_files=referenced_count,
            hit_rate=hit_rate,
            references=list(self.references),
            unreferenced_domains=unreferenced_domains,
            coverage_by_domain=coverage,
        )

    def save_report(
        self,
        report: KnowledgeTrackingReport,
        output_dir: str = "output",
    ) -> tuple[Path, Path]:
        """保存报告到文件

        Markdown 报告存到 output/ 根目录，
        JSON 存到 output/metrics-history/ 用于趋势分析。

        Args:
            report: 报告实例
            output_dir: 输出目录

        Returns:
            (markdown_path, json_path) 两个文件路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        metrics_dir = output_path / "metrics-history"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base_name = f"{report.project_name}-knowledge-tracking"

        # Markdown
        md_path = output_path / f"{base_name}.md"
        md_path.write_text(report.to_markdown(), encoding="utf-8")

        # JSON (带时间戳用于趋势分析)
        json_path = metrics_dir / f"{base_name}-{ts}.json"
        json_path.write_text(
            json.dumps(report.to_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return md_path, json_path

    # ------------------------------------------------------------------
    # 覆盖率统计
    # ------------------------------------------------------------------

    def get_knowledge_coverage(self) -> dict[str, dict[str, Any]]:
        """获取知识覆盖率统计（按领域）

        Returns:
            形如 ``{ "security": {"total": 15, "referenced": 8, "rate": 0.53} }`` 的字典
        """
        domain_total: dict[str, int] = {}
        domain_files: dict[str, set[str]] = {}

        for path, entry in self._knowledge_index.items():
            d = entry.domain or "(root)"
            domain_total[d] = domain_total.get(d, 0) + 1
            if d not in domain_files:
                domain_files[d] = set()

        referenced_paths = {ref.knowledge_file for ref in self.references}

        for path, entry in self._knowledge_index.items():
            d = entry.domain or "(root)"
            if path in referenced_paths:
                domain_files[d].add(path)

        result: dict[str, dict[str, Any]] = {}
        for domain in sorted(domain_total):
            total = domain_total[domain]
            referenced = len(domain_files.get(domain, set()))
            result[domain] = {
                "total": total,
                "referenced": referenced,
                "rate": round(referenced / total, 4) if total > 0 else 0.0,
            }
        return result

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def get_all_domains(self) -> list[str]:
        """获取所有知识领域名称"""
        domains: set[str] = set()
        for entry in self._knowledge_index.values():
            if entry.domain:
                domains.add(entry.domain)
        return sorted(domains)

    def get_reference_count(self) -> int:
        """获取当前引用总数"""
        return len(self.references)

    def clear(self) -> None:
        """清空所有引用记录（保留索引）"""
        self.references.clear()
