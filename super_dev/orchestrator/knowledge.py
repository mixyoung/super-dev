"""
知识增强模块

将用户输入需求通过「本地知识库 + 联网检索」进行增强，
为后续 PRD / 架构 / UIUX / Spec 生成提供更完整上下文。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]

from ..knowledge_tracker import KnowledgeTracker
from ..utils import get_logger


@dataclass
class KnowledgeItem:
    """知识项"""

    source: str
    title: str
    snippet: str
    link: str = ""
    score: float = 0.0
    evidence_level: str = "community"
    source_domain: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "snippet": self.snippet,
            "link": self.link,
            "score": self.score,
            "evidence_level": self.evidence_level,
            "source_domain": self.source_domain,
        }


# 中英文关键词映射表
KEYWORD_TRANSLATIONS: dict[str, list[str]] = {
    "购物车": ["shopping cart", "cart"],
    "电商": ["ecommerce", "e-commerce", "online shop"],
    "博客": ["blog"],
    "认证": ["authentication", "auth", "login"],
    "支付": ["payment", "checkout"],
    "搜索": ["search"],
    "用户": ["user"],
    "订单": ["order"],
    "商品": ["product", "goods"],
    "库存": ["inventory", "stock"],
    "物流": ["logistics", "shipping"],
    "评论": ["comment", "review"],
    "通知": ["notification"],
    "权限": ["permission", "authorization", "rbac"],
    "缓存": ["cache", "caching"],
    "消息队列": ["message queue", "mq"],
    "微服务": ["microservice", "micro-service"],
    "api": ["接口"],
    "database": ["数据库", "db"],
    "security": ["安全"],
    "performance": ["性能"],
    "testing": ["测试"],
    "docker": ["容器"],
    "kubernetes": ["k8s"],
    "frontend": ["前端"],
    "backend": ["后端"],
    "deployment": ["部署", "deploy"],
    "monitoring": ["监控"],
    "logging": ["日志"],
}


class KnowledgeAugmenter:
    """需求知识增强器"""

    _STOPWORDS = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "from",
        "this",
        "功能",
        "项目",
        "系统",
        "需要",
        "支持",
        "实现",
        "一个",
        "需求",
    }
    _STAGE_ORDER = [
        "research",
        "prd",
        "architecture",
        "uiux",
        "spec",
        "frontend",
        "backend",
        "quality",
        "delivery",
    ]
    _DOMAIN_STAGE_MAP = {
        "product": ["research", "prd", "spec"],
        "design": ["research", "uiux", "frontend"],
        "architecture": ["architecture", "spec", "backend"],
        "development": ["architecture", "spec", "frontend", "backend"],
        "testing": ["quality"],
        "security": ["architecture", "backend", "quality"],
        "cicd": ["quality", "delivery"],
        "operations": ["quality", "delivery"],
        "data": ["architecture", "backend", "quality"],
        "incident": ["quality", "delivery"],
        "ai": ["research", "architecture", "quality", "delivery"],
        "00-governance": ["research", "prd", "architecture", "uiux", "spec", "quality", "delivery"],
        "docs": ["research", "prd", "architecture", "uiux"],
        "specs": ["spec"],
    }

    def __init__(
        self,
        project_dir: Path,
        web_enabled: bool = True,
        allowed_web_domains: list[str] | None = None,
        cache_ttl_seconds: int | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.logger = get_logger("knowledge_augmenter")
        self.web_enabled = web_enabled
        self.docs_dir = self.project_dir / "docs"
        self.knowledge_dir = self.project_dir / "knowledge"
        self.specs_dir = self.project_dir / ".super-dev" / "specs"
        self.data_dir = self.project_dir / "super_dev" / "data"
        self.builtin_data_dir = Path(__file__).resolve().parents[1] / "data"
        env_domains = [
            item.strip().lower()
            for item in os.getenv("SUPER_DEV_KNOWLEDGE_ALLOWED_DOMAINS", "").split(",")
            if item.strip()
        ]
        selected_domains = allowed_web_domains if allowed_web_domains is not None else env_domains
        self.allowed_web_domains = [
            item.strip().lower() for item in selected_domains if item.strip()
        ]
        env_cache_ttl = os.getenv("SUPER_DEV_KNOWLEDGE_CACHE_TTL_SECONDS", "").strip()
        env_cache_ttl_value = int(env_cache_ttl) if env_cache_ttl.isdigit() else 1800
        self.cache_ttl_seconds = (
            cache_ttl_seconds if cache_ttl_seconds is not None else env_cache_ttl_value
        )
        self._last_web_stats: dict[str, Any] = {
            "provider": "none",
            "raw_count": 0,
            "filtered_count": 0,
            "filtered_out_count": 0,
        }

        # 知识引用追踪
        self._tracker: KnowledgeTracker | None = None
        try:
            self._tracker = KnowledgeTracker(str(self.knowledge_dir))
        except Exception:
            pass

    def augment(
        self,
        requirement: str,
        domain: str = "",
        max_local_results: int = 8,
        max_web_results: int = 5,
    ) -> dict[str, Any]:
        """对需求做知识增强"""
        query = requirement.strip()
        keywords = self._extract_keywords(query)

        local_items = self._collect_local_items(
            keywords=keywords,
            max_results=max_local_results,
        )
        web_items = self._collect_web_items(
            query=self._build_web_query(query, domain),
            max_results=max_web_results,
        )

        enriched_requirement = self._compose_enriched_requirement(
            requirement=requirement,
            local_items=local_items,
            web_items=web_items,
        )
        research_summary = self._build_research_summary(
            requirement=requirement,
            domain=domain,
            keywords=keywords,
            local_items=local_items,
            web_items=web_items,
        )
        knowledge_application_plan = self._build_knowledge_application_plan(
            local_items,
            requirement=requirement,
            keywords=keywords,
        )

        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "original_requirement": requirement,
            "domain": domain,
            "keywords": keywords,
            "local_knowledge": [item.to_dict() for item in local_items],
            "web_knowledge": [item.to_dict() for item in web_items],
            "citations": {
                "local": [self._to_citation(item) for item in local_items],
                "web": [self._to_citation(item) for item in web_items],
            },
            "metadata": {
                "web_enabled": self.web_enabled,
                "allowed_web_domains": self.allowed_web_domains,
                "web_stats": self._last_web_stats,
            },
            "research_summary": research_summary,
            "knowledge_application_plan": knowledge_application_plan,
            "enriched_requirement": enriched_requirement,
        }

        # 追加知识引用追踪统计
        if self._tracker:
            try:
                domains_hit: list[str] = []
                seen_domains: set[str] = set()
                for r in self._tracker.references:
                    parts = r.knowledge_file.split("/")
                    if len(parts) > 1:
                        d = parts[1] if parts[0] == "" else parts[0]
                    else:
                        d = ""
                    # 尝试从 knowledge/ 之后取领域名
                    for i, p in enumerate(parts):
                        if p == "knowledge" and i + 1 < len(parts):
                            d = parts[i + 1]
                            break
                    if d and d not in seen_domains:
                        seen_domains.add(d)
                        domains_hit.append(d)
                result["knowledge_tracking"] = {
                    "referenced_files": len(self._tracker.references),
                    "domains_hit": domains_hit,
                }
            except Exception:
                pass

        return result

    def to_markdown(self, bundle: dict[str, Any]) -> str:
        """将增强结果渲染为 Markdown 报告"""
        lines = [
            "# 需求增强报告",
            "",
            f"**原始需求**: {bundle.get('original_requirement', '')}",
            f"**领域**: {bundle.get('domain', 'general') or 'general'}",
            "",
            "## 提取关键词",
            "",
            ", ".join(bundle.get("keywords", [])) or "(none)",
            "",
            "## 本地知识库结果",
            "",
        ]

        local_items = bundle.get("local_knowledge", [])
        if not local_items:
            lines.append("- 未命中本地知识。")
        else:
            for item in local_items:
                title = item.get("title", "unknown")
                snippet = item.get("snippet", "")
                lines.append(f"- **{title}** ({item.get('source', 'local')}): {snippet}")
        lines.append("")

        lines.extend(["## 本地知识应用计划", ""])
        plan = bundle.get("knowledge_application_plan", {}) or {}
        stage_guidance = plan.get("stage_guidance", {}) if isinstance(plan, dict) else {}
        hard_constraints = plan.get("hard_constraints", []) if isinstance(plan, dict) else []
        if isinstance(hard_constraints, list) and hard_constraints:
            lines.append("### 硬约束")
            lines.append("")
            for item in hard_constraints:
                if isinstance(item, str):
                    lines.append(f"- {item}")
            lines.append("")
        if isinstance(stage_guidance, dict) and stage_guidance:
            for stage in self._STAGE_ORDER:
                entries = stage_guidance.get(stage, [])
                lines.extend(
                    self._render_summary_section(
                        f"### {self._stage_label(stage)}",
                        entries if isinstance(entries, list) else [],
                    )
                )
        else:
            lines.append("- 当前未生成阶段化知识应用计划。")
            lines.append("")

        framework_guidance = plan.get("framework_guidance", {}) if isinstance(plan, dict) else {}
        if isinstance(framework_guidance, dict) and framework_guidance:
            lines.extend(
                [
                    "### 跨平台框架专项指引",
                    "",
                    f"- **Framework**: {framework_guidance.get('framework', 'Unknown')}",
                    "",
                    "**关键实现模块**:",
                ]
            )
            for item in framework_guidance.get("critical_modules", []):
                if isinstance(item, str) and item.strip():
                    lines.append(f"- {item}")
            lines.extend(["", "**必须验收的真实场景**:"])
            for item in framework_guidance.get("validation_surfaces", []):
                if isinstance(item, str) and item.strip():
                    lines.append(f"- {item}")
            lines.extend(["", "**交付证据要求**:"])
            for item in framework_guidance.get("delivery_evidence", []):
                if isinstance(item, str) and item.strip():
                    lines.append(f"- {item}")
            lines.append("")

        lines.extend(["## 联网检索结果", ""])
        web_items = bundle.get("web_knowledge", [])
        if not web_items:
            lines.append("- 未获得联网结果（可能网络受限或无匹配结果）。")
        else:
            for item in web_items:
                title = item.get("title", "unknown")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                link_text = f" [{link}]({link})" if link else ""
                lines.append(f"- **{title}**: {snippet}{link_text}")
        lines.append("")

        research_summary = bundle.get("research_summary", {}) or {}
        lines.extend(["## 同类产品研究与机会洞察", ""])
        lines.extend(
            self._render_summary_section(
                "### 1. 对标产品", research_summary.get("benchmark_products", [])
            )
        )
        lines.extend(
            self._render_summary_section(
                "### 2. 共性功能模式", research_summary.get("feature_patterns", [])
            )
        )
        lines.extend(
            self._render_summary_section(
                "### 3. 交互与体验模式", research_summary.get("interaction_patterns", [])
            )
        )
        lines.extend(
            self._render_summary_section(
                "### 4. 信任与商业化信号", research_summary.get("trust_signals", [])
            )
        )
        lines.extend(
            self._render_summary_section(
                "### 5. 差异化机会", research_summary.get("differentiation_opportunities", [])
            )
        )
        lines.extend(
            self._render_summary_section(
                "### 6. 交付建议", research_summary.get("delivery_recommendations", [])
            )
        )
        evidence_distribution = research_summary.get("evidence_distribution", {}) or {}
        lines.extend(
            [
                "### 7. 研究证据与可信度",
                "",
                f"- **研究可信度**: {research_summary.get('research_confidence', 'baseline')}",
                f"- **官方来源**: {evidence_distribution.get('official', 0)} 条",
                f"- **行业来源**: {evidence_distribution.get('industry', 0)} 条",
                f"- **社区来源**: {evidence_distribution.get('community', 0)} 条",
                "",
                "### 8. 实施策略对比",
                "",
                "| 方案 | 适用场景 | 核心策略 | 关键权衡 |",
                "|:---|:---|:---|:---|",
            ]
        )
        implementation_options = research_summary.get("implementation_options", [])
        if isinstance(implementation_options, list) and implementation_options:
            for option in implementation_options:
                if not isinstance(option, dict):
                    continue
                lines.append(
                    f"| {option.get('name', '-')} | {option.get('fit', '-')} | {option.get('strategy', '-')} | {option.get('tradeoff', '-')} |"
                )
        else:
            lines.append("| 稳健商业方案 | 企业级交付 | 组件标准化 + 质量门禁 | 前期规范成本 |")
        lines.extend(["", "### 9. 核心来源域名", ""])
        primary_sources = research_summary.get("primary_sources", [])
        if isinstance(primary_sources, list) and primary_sources:
            for item in primary_sources:
                if isinstance(item, list | tuple) and len(item) >= 2:
                    lines.append(f"- {item[0]}: {item[1]} 次引用")
        else:
            lines.append("- 当前未识别到可统计域名")
        lines.extend(
            [
                "",
                "### 10. 竞品能力矩阵（自动提取）",
                "",
                "| 产品 | 核心能力定位 | 定价信号 | 信任信号 | 证据等级 |",
                "|:---|:---|:---|:---|:---|",
            ]
        )
        competitor_matrix = research_summary.get("competitor_matrix", [])
        if isinstance(competitor_matrix, list) and competitor_matrix:
            for row in competitor_matrix:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"| {row.get('product', '-')} | {row.get('capability', '-')} | {row.get('pricing_signal', '-')} | {row.get('trust_signal', '-')} | {row.get('evidence_level', '-')} |"
                )
        else:
            lines.append("| - | - | - | - | - |")
        lines.append("")

        lines.extend(
            [
                "## 增强后的需求描述",
                "",
                bundle.get("enriched_requirement", bundle.get("original_requirement", "")),
                "",
            ]
        )
        return "\n".join(lines)

    def save_bundle(
        self,
        bundle: dict[str, Any],
        output_dir: Path,
        project_name: str,
        requirement: str | None = None,
        domain: str | None = None,
    ) -> Path:
        cache_dir = Path(output_dir) / "knowledge-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{project_name}-knowledge-bundle.json"
        cached_bundle = dict(bundle)
        cached_bundle.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
        if requirement is not None:
            cached_bundle["cache_signature"] = self._bundle_signature(
                requirement=requirement,
                domain=domain or "",
            )
        cached_bundle["cache_ttl_seconds"] = self.cache_ttl_seconds
        cache_file.write_text(
            json.dumps(cached_bundle, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return cache_file

    def load_cached_bundle(
        self,
        output_dir: Path,
        project_name: str,
        requirement: str,
        domain: str = "",
    ) -> dict[str, Any] | None:
        if self.cache_ttl_seconds <= 0:
            return None

        cache_file = Path(output_dir) / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"
        if not cache_file.exists():
            return None
        try:
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception as e:
            self.logger.warning(f"知识缓存文件解析失败: {cache_file}, 错误: {e}")
            return None
        if not isinstance(payload, dict):
            return None

        generated_at_raw = str(payload.get("generated_at", "")).strip()
        cache_signature = str(payload.get("cache_signature", "")).strip()
        if not generated_at_raw or not cache_signature:
            return None

        expected_signature = self._bundle_signature(requirement=requirement, domain=domain)
        if cache_signature != expected_signature:
            return None

        generated_at = self._parse_datetime(generated_at_raw)
        if generated_at is None:
            return None
        expired_at = generated_at + timedelta(seconds=self.cache_ttl_seconds)
        if expired_at <= datetime.now(timezone.utc):
            return None
        return payload

    def _extract_keywords(self, text: str) -> list[str]:
        lowered = text.lower()
        mixed_tokens = re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]{2,}", lowered)
        expanded: list[str] = []
        for token in mixed_tokens:
            expanded.append(token)
            ascii_parts = re.findall(r"[a-z0-9_]{2,}", token)
            zh_parts = re.findall(r"[\u4e00-\u9fff]{2,}", token)
            expanded.extend(ascii_parts)
            expanded.extend(zh_parts)
            for zh in zh_parts:
                if len(zh) >= 3:
                    for i in range(len(zh) - 1):
                        expanded.append(zh[i : i + 2])

        unique: list[str] = []
        for token in expanded:
            if token in self._STOPWORDS:
                continue
            if token not in unique:
                unique.append(token)

        # 扩展中英文对应词
        try:
            unique = self._expand_keywords(unique)
        except Exception:
            pass

        return unique[:16]

    def _expand_keywords(self, keywords: list[str]) -> list[str]:
        """根据中英文映射表扩展关键词"""
        expanded = list(keywords)
        for kw in keywords:
            kw_lower = kw.lower()
            for cn, en_list in KEYWORD_TRANSLATIONS.items():
                en_lower_list = [e.lower() for e in en_list]
                if kw_lower == cn or kw_lower in en_lower_list:
                    if cn not in expanded:
                        expanded.append(cn)
                    for en in en_list:
                        if en.lower() not in [e.lower() for e in expanded]:
                            expanded.append(en)
        return list(dict.fromkeys(expanded))  # 去重保序

    def _iter_local_files(self) -> list[Path]:
        files: list[Path] = []
        if self.docs_dir.exists():
            files.extend(self.docs_dir.rglob("*.md"))
        if self.knowledge_dir.exists():
            files.extend(self.knowledge_dir.rglob("*.md"))
            files.extend(self.knowledge_dir.rglob("*.txt"))
            files.extend(self.knowledge_dir.rglob("*.yml"))
            files.extend(self.knowledge_dir.rglob("*.yaml"))
        if self.specs_dir.exists():
            files.extend(self.specs_dir.rglob("*.md"))
        if self.data_dir.exists():
            files.extend(self.data_dir.rglob("*.csv"))
        if self.builtin_data_dir.exists() and self.builtin_data_dir != self.data_dir:
            files.extend(self.builtin_data_dir.rglob("*.csv"))
        return files

    def _collect_local_items(
        self, keywords: list[str], max_results: int, current_stage: str = "research"
    ) -> list[KnowledgeItem]:
        if not keywords:
            return []

        items: list[KnowledgeItem] = []
        for file_path in self._iter_local_files():
            content = ""
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                self.logger.warning(f"无法读取文件 {file_path}: {e}")
                content = ""
            if not content:
                continue

            lowered = content.lower()
            score = 0.0
            for keyword in keywords:
                if keyword in lowered:
                    score += 1.0
            if score <= 0:
                continue
            score += self._local_source_boost(file_path)

            snippet = self._first_matching_snippet(content, keywords)
            source_path = self._format_source_path(file_path)
            is_standard = any(
                token in source_path.lower()
                for token in ("standard", "checklist", "baseline", "gate")
            )
            items.append(
                KnowledgeItem(
                    source=source_path,
                    title=file_path.stem,
                    snippet=snippet,
                    score=score,
                )
            )

            # 记录知识引用追踪
            if self._tracker:
                try:
                    # 将 augmenter 阶段名映射到 tracker 有效阶段名
                    tracker_phase = self._map_stage_to_tracker_phase(current_stage)
                    # 归一化 score 到 0-1 区间
                    max_possible = len(keywords) + 1.5  # 关键词数 + 最大 boost
                    normalized_score = min(score / max_possible, 1.0) if max_possible > 0 else 0.5
                    self._tracker.track_reference(
                        knowledge_file=str(file_path),
                        phase=tracker_phase,
                        usage_type="constraint" if is_standard else "reference",
                        relevance_score=normalized_score,
                        excerpt=snippet[:200],
                    )
                except Exception:
                    pass

        items.sort(key=lambda item: item.score, reverse=True)
        return items[:max_results]

    @staticmethod
    def _map_stage_to_tracker_phase(stage: str) -> str:
        """将 augmenter 的阶段名映射到 KnowledgeTracker 的有效阶段名"""
        mapping = {
            "research": "research",
            "prd": "docs",
            "architecture": "docs",
            "uiux": "docs",
            "spec": "spec",
            "frontend": "frontend",
            "backend": "backend",
            "quality": "quality",
            "delivery": "delivery",
        }
        return mapping.get(stage, "research")

    def _local_source_boost(self, file_path: Path) -> float:
        source = self._format_source_path(file_path)
        if source.startswith("knowledge/"):
            return 1.2
        if source.startswith(".super-dev/specs/"):
            return 0.8
        if source.startswith("docs/"):
            return 0.2
        if source.startswith("super_dev/data/") or source.startswith("builtin/"):
            return 0.1
        return 0.0

    def _first_matching_snippet(self, content: str, keywords: list[str]) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        for line in lines:
            lowered = line.lower()
            if any(keyword in lowered for keyword in keywords):
                return line[:220]
        return lines[0][:220] if lines else ""

    def _format_source_path(self, file_path: Path) -> str:
        try:
            return file_path.relative_to(self.project_dir).as_posix()
        except ValueError:
            try:
                return f"builtin/{file_path.relative_to(self.builtin_data_dir).as_posix()}"
            except ValueError:
                return str(file_path)

    def _to_citation(self, item: KnowledgeItem) -> dict[str, str]:
        return {
            "title": item.title,
            "source": item.source,
            "link": item.link,
        }

    def _build_web_query(self, requirement: str, domain: str) -> str:
        benchmark_terms = (
            "similar products competitor analysis benchmark feature patterns "
            "user flow information architecture interaction design ui ux best practices"
        )
        if domain:
            return f"{requirement} {domain} {benchmark_terms}"
        return f"{requirement} {benchmark_terms}"

    def _collect_web_items(self, query: str, max_results: int) -> list[KnowledgeItem]:
        if not self.web_enabled:
            self._last_web_stats = {
                "provider": "disabled",
                "raw_count": 0,
                "filtered_count": 0,
                "filtered_out_count": 0,
            }
            return []

        provider = "ddgs"
        results = self._collect_web_items_ddgs(query=query, max_results=max_results)
        if not results:
            provider = "duckduckgo"
            results = self._collect_web_items_duckduckgo(query=query, max_results=max_results)
        raw_count = len(results)
        filtered = self._filter_web_items(results)[:max_results]
        self._last_web_stats = {
            "provider": provider,
            "raw_count": raw_count,
            "filtered_count": len(filtered),
            "filtered_out_count": max(raw_count - len(filtered), 0),
        }
        return filtered

    def _filter_web_items(self, items: list[KnowledgeItem]) -> list[KnowledgeItem]:
        if not self.allowed_web_domains:
            return items

        filtered: list[KnowledgeItem] = []
        for item in items:
            if not item.link:
                continue
            parsed = urllib.parse.urlparse(item.link)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            if any(
                netloc == domain or netloc.endswith(f".{domain}")
                for domain in self.allowed_web_domains
            ):
                filtered.append(item)
        return filtered

    def _extract_domain(self, link: str) -> str:
        if not link:
            return ""
        try:
            parsed = urllib.parse.urlparse(link)
        except Exception as e:
            self.logger.warning(f"URL 解析失败: {link}, 错误: {e}")
            return ""
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host

    def _infer_evidence_level(self, title: str, snippet: str, link: str) -> str:
        domain = self._extract_domain(link)
        text = f"{title} {snippet} {domain}".lower()
        if any(token in domain for token in ("docs.", "developer.", "api.", "platform.")):
            return "official"
        if any(
            token in text
            for token in (
                "official",
                "documentation",
                "developer",
                "changelog",
                "release notes",
                "pricing",
            )
        ):
            return "official"
        if any(
            token in domain
            for token in (
                "github.com",
                "gitlab.com",
                "stackshare.io",
                "g2.com",
                "capterra.com",
                "producthunt.com",
            )
        ):
            return "industry"
        return "community"

    def _collect_web_items_ddgs(self, query: str, max_results: int) -> list[KnowledgeItem]:
        try:
            from ddgs import DDGS  # type: ignore
        except Exception:
            self.logger.warning("ddgs 库未安装，跳过 DDGS 检索")
            return []

        results: list[KnowledgeItem] = []
        try:
            ddgs = DDGS()
            entries = ddgs.text(query, max_results=max_results)
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                link = str(entry.get("href", "")).strip()
                results.append(
                    KnowledgeItem(
                        source="web",
                        title=str(entry.get("title", "web-result")).strip(),
                        snippet=str(entry.get("body", "")).strip()[:220],
                        link=link,
                        score=float(max_results - index),
                        evidence_level=self._infer_evidence_level(
                            str(entry.get("title", "web-result")),
                            str(entry.get("body", "")),
                            link,
                        ),
                        source_domain=self._extract_domain(link),
                    )
                )
        except Exception as e:
            self.logger.warning(f"DDGS 联网检索异常: {type(e).__name__}: {e}")
            return []

        return results

    def _collect_web_items_duckduckgo(self, query: str, max_results: int) -> list[KnowledgeItem]:
        encoded_query = urllib.parse.quote(query)
        url = (
            "https://api.duckduckgo.com/"
            f"?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
        )

        try:
            response = requests.get(url, timeout=6)
            if response.status_code >= 400:
                return []
            payload = response.text
            data = json.loads(payload)
        except requests.exceptions.Timeout:
            self.logger.warning(f"联网检索超时: {url}")
            return []
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"联网检索连接失败: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.warning(f"联网检索响应解析失败: {e}")
            return []
        except Exception as e:
            self.logger.warning(f"联网检索异常: {type(e).__name__}: {e}")
            return []

        results: list[KnowledgeItem] = []
        abstract = str(data.get("Abstract", "")).strip()
        if abstract:
            abstract_url = str(data.get("AbstractURL", "")).strip()
            results.append(
                KnowledgeItem(
                    source="web",
                    title=str(data.get("Heading", "DuckDuckGo Result")).strip()
                    or "DuckDuckGo Result",
                    snippet=abstract[:220],
                    link=abstract_url,
                    score=float(max_results),
                    evidence_level=self._infer_evidence_level(
                        str(data.get("Heading", "DuckDuckGo Result")),
                        abstract,
                        abstract_url,
                    ),
                    source_domain=self._extract_domain(abstract_url),
                )
            )

        related = data.get("RelatedTopics", [])
        for item in related:
            if len(results) >= max_results:
                break
            if not isinstance(item, dict):
                continue
            if "Topics" in item and isinstance(item.get("Topics"), list):
                sub_topics = item.get("Topics", [])
            else:
                sub_topics = [item]

            for topic in sub_topics:
                if len(results) >= max_results:
                    break
                if not isinstance(topic, dict):
                    continue
                text = str(topic.get("Text", "")).strip()
                if not text:
                    continue
                first_url = str(topic.get("FirstURL", "")).strip()
                results.append(
                    KnowledgeItem(
                        source="web",
                        title=text[:80],
                        snippet=text[:220],
                        link=first_url,
                        score=float(max_results - len(results)),
                        evidence_level=self._infer_evidence_level(text[:80], text[:220], first_url),
                        source_domain=self._extract_domain(first_url),
                    )
                )

        return results[:max_results]

    def _compose_enriched_requirement(
        self,
        requirement: str,
        local_items: list[KnowledgeItem],
        web_items: list[KnowledgeItem],
    ) -> str:
        notes: list[str] = []
        for item in local_items[:3]:
            notes.append(f"本地知识参考: {item.title} - {item.snippet}")
        for item in web_items[:3]:
            notes.append(f"外部最佳实践: {item.title} - {item.snippet}")

        if not notes:
            return requirement

        joined = "；".join(notes)
        return f"{requirement}。请结合以下上下文实现：{joined}"

    def _build_research_summary(
        self,
        requirement: str,
        domain: str,
        keywords: list[str],
        local_items: list[KnowledgeItem],
        web_items: list[KnowledgeItem],
    ) -> dict[str, Any]:
        benchmark_products = []
        evidence_distribution = {"official": 0, "industry": 0, "community": 0}
        source_domains: dict[str, int] = {}
        for item in web_items[:5]:
            benchmark_products.append(self._format_research_item(item, include_link=True))
            level = (
                item.evidence_level if item.evidence_level in evidence_distribution else "community"
            )
            evidence_distribution[level] += 1
            if item.source_domain:
                source_domains[item.source_domain] = source_domains.get(item.source_domain, 0) + 1

        feature_patterns = self._unique_preserve_order(
            [f"围绕“{keyword}”建立清晰功能分区、任务入口与状态反馈。" for keyword in keywords[:4]]
            + [self._format_research_item(item) for item in web_items[:3]]
            + [self._format_research_item(item) for item in local_items[:2]]
        )

        interaction_patterns = self._unique_preserve_order(
            [
                "关键任务链路必须具备明确的下一步、完成反馈与可回退路径。",
                "复杂页面应先给信息架构和优先级，再给具体视觉样式，避免一屏堆满功能。",
                "列表、详情、编辑、确认四类页面应形成统一的交互骨架，降低学习成本。",
            ]
            + [self._interaction_pattern_from_item(item) for item in web_items[:3]]
        )

        trust_signals = self._unique_preserve_order(
            [
                "首页或主工作台优先展示价值主张、能力边界、成功案例或关键数据，避免空泛口号。",
                "涉及数据录入、协作、交易、发布的流程必须提供校验、草稿、撤销或审计提示。",
                "商业产品页面必须体现加载态、空态、错误态和权限态，而不是只做正常态截图。",
            ]
        )

        domain_label = domain or "当前业务领域"
        differentiation_opportunities = self._unique_preserve_order(
            [
                f"把 {domain_label} 场景下最关键的任务路径压缩到更少步骤，并用清晰状态机承载流程进度。",
                "将研究结论沉淀到 PRD / 架构 / UIUX / Spec，确保不是只参考外部产品外观，而是参考其流程与交付标准。",
                "优先做能体现商业级完成度的能力：权限、审计、异常处理、批量操作、搜索筛选、可观测性。",
            ]
        )

        delivery_recommendations = self._unique_preserve_order(
            [
                "在生成 PRD 前先冻结同类产品研究结论，明确借鉴项、禁用项与差异化方向。",
                "UI 产出必须先确定设计方向、字体系统、栅格、组件状态矩阵，再开始页面实现。",
                "实现阶段应先完成信息架构正确的页面框架，再补视觉细节、动效和性能优化。",
            ]
        )

        if not benchmark_products:
            benchmark_products.append(
                "未获取到可靠联网结果时，应由宿主继续使用原生联网能力补充同类产品研究。"
            )

        implementation_options = [
            {
                "name": "稳健商业方案",
                "fit": "企业级交付、审计与可维护优先",
                "strategy": "组件库标准化 + 证据驱动文档 + 质量门禁",
                "tradeoff": "前期规范成本较高，但长期稳定",
            },
            {
                "name": "快速验证方案",
                "fit": "MVP 快速上线、验证 PMF",
                "strategy": "核心路径最小集 + UI 基础组件复用 + 指标埋点先行",
                "tradeoff": "视觉深度与扩展性需要二次迭代",
            },
            {
                "name": "品牌差异化方案",
                "fit": "竞争激烈、强调品牌识别与转化",
                "strategy": "品牌 token 系统 + 页面叙事结构 + 转化实验框架",
                "tradeoff": "设计与内容投入更高",
            },
        ]
        primary_sources = sorted(source_domains.items(), key=lambda item: item[1], reverse=True)[:6]
        competitor_matrix = []
        for item in web_items[:5]:
            content = f"{item.title} {item.snippet}".lower()
            capability = (
                "工作台/协作"
                if any(
                    token in content for token in ("dashboard", "workspace", "platform", "workflow")
                )
                else "垂直功能"
            )
            pricing_signal = (
                "已提及"
                if any(token in content for token in ("pricing", "price", "plan", "套餐"))
                else "未提及"
            )
            trust_signal = "较强" if item.evidence_level in {"official", "industry"} else "基础"
            competitor_matrix.append(
                {
                    "product": item.title or "unknown",
                    "capability": capability,
                    "pricing_signal": pricing_signal,
                    "trust_signal": trust_signal,
                    "evidence_level": item.evidence_level,
                }
            )
        research_confidence = "high" if evidence_distribution["official"] >= 2 else "medium"
        if evidence_distribution["official"] == 0 and evidence_distribution["industry"] <= 1:
            research_confidence = "baseline"

        return {
            "benchmark_products": benchmark_products,
            "feature_patterns": feature_patterns[:6],
            "interaction_patterns": interaction_patterns[:6],
            "trust_signals": trust_signals[:5],
            "differentiation_opportunities": differentiation_opportunities[:5],
            "delivery_recommendations": delivery_recommendations[:5],
            "implementation_options": implementation_options,
            "evidence_distribution": evidence_distribution,
            "primary_sources": primary_sources,
            "competitor_matrix": competitor_matrix,
            "research_confidence": research_confidence,
        }

    def _format_research_item(self, item: KnowledgeItem, include_link: bool = False) -> str:
        snippet = item.snippet.strip().replace("\n", " ")
        snippet = snippet[:140] if snippet else "提供了可参考的行业实践。"
        if include_link and item.link:
            return f"{item.title}: {snippet} [{item.link}]({item.link})"
        return f"{item.title}: {snippet}"

    def _interaction_pattern_from_item(self, item: KnowledgeItem) -> str:
        if not item.snippet:
            return f"参考 {item.title} 的功能组织方式，提炼关键流程和页面层级。"
        return f"参考 {item.title} 的页面与流程组织方式：{item.snippet[:120]}"

    def _render_summary_section(self, title: str, items: list[str]) -> list[str]:
        lines = [title, ""]
        if not items:
            lines.append("- 暂无结论，需要继续补充研究。")
            lines.append("")
            return lines
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
        return lines

    def _unique_preserve_order(self, items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            normalized = item.strip()
            if not normalized or normalized in result:
                continue
            result.append(normalized)
        return result

    def _source_domain(self, item: KnowledgeItem) -> str:
        source = item.source.strip()
        if source.startswith("knowledge/"):
            parts = source.split("/")
            if len(parts) >= 2:
                return parts[1]
        if source.startswith("docs/"):
            return "docs"
        if source.startswith(".super-dev/specs/"):
            return "specs"
        return "general"

    def _constraint_type(self, item: KnowledgeItem) -> str:
        lowered = f"{item.source} {item.title}".lower()
        if any(token in lowered for token in ["checklist", "baseline", "gate", "criteria"]):
            return "hard-gate"
        if any(token in lowered for token in ["template", "catalog", "index", "taxonomy", "map"]):
            return "reference"
        if any(token in lowered for token in ["runbook", "playbook", "policy", "guide"]):
            return "operating-guidance"
        return "knowledge"

    def _infer_framework_guidance(self, *, requirement: str, keywords: list[str]) -> dict[str, Any]:
        normalized = f"{requirement} {' '.join(keywords)}".lower()
        mapping = [
            (
                ("uni-app", "uniapp", "小程序", "微信小程序"),
                {
                    "framework": "uni-app",
                    "critical_modules": [
                        "自定义导航栏、状态栏、安全区与胶囊按钮区域先冻结再实现",
                        "登录/支付/分享 provider 按平台拆分，避免一套逻辑硬跑全端",
                    ],
                    "validation_surfaces": [
                        "微信小程序真机导航/支付/触控与包体策略",
                        "H5 与 App 的 provider、登录态和条件编译差异",
                    ],
                    "delivery_evidence": [
                        "pages.json / 分包 / provider 配置说明",
                        "三端差异与条件编译点清单",
                    ],
                },
            ),
            (
                ("taro",),
                {
                    "framework": "Taro",
                    "critical_modules": [
                        "路由与状态管理先统一，再映射多端页面容器",
                        "小程序/H5 的事件模型、样式隔离与组件能力差异先冻结",
                    ],
                    "validation_surfaces": [
                        "微信小程序与 H5 的滚动、分享、登录与样式差异",
                    ],
                    "delivery_evidence": [
                        "平台条件分支说明",
                        "跨端事件与样式差异验证记录",
                    ],
                },
            ),
            (
                ("react-native", "react native"),
                {
                    "framework": "React Native",
                    "critical_modules": [
                        "导航栈、权限、深链、离线缓存先冻结",
                        "iOS/Android 的原生桥接与安全区差异先单独设计",
                    ],
                    "validation_surfaces": [
                        "iOS 真机导航、推送、权限弹窗",
                        "Android 返回栈、深链与通知恢复",
                    ],
                    "delivery_evidence": [
                        "真机截图与权限矩阵",
                        "导航/深链/离线恢复验收记录",
                    ],
                },
            ),
            (
                ("flutter",),
                {
                    "framework": "Flutter",
                    "critical_modules": [
                        "ThemeData、路由、状态管理和平台感知组件先冻结",
                        "Material/Cupertino 的切换边界和动画策略先明确",
                    ],
                    "validation_surfaces": [
                        "Android 与 iOS 的主题、动画、输入法和返回行为",
                    ],
                    "delivery_evidence": [
                        "ThemeData / 组件映射说明",
                        "双平台主题与动画验收记录",
                    ],
                },
            ),
            (
                ("electron", "tauri", "wails", "桌面"),
                {
                    "framework": "Desktop Web Shell",
                    "critical_modules": [
                        "窗口布局、快捷键、托盘、本地文件与 IPC 边界先冻结",
                        "离线缓存和本地能力调用不能按普通 Web 假设实现",
                    ],
                    "validation_surfaces": [
                        "窗口恢复、快捷键、文件系统与离线恢复",
                    ],
                    "delivery_evidence": [
                        "窗口/快捷键/原生桥接清单",
                        "本地文件流与离线恢复验证记录",
                    ],
                },
            ),
        ]
        for aliases, payload in mapping:
            if any(alias in normalized for alias in aliases):
                return payload
        return {}

    def _build_knowledge_application_plan(
        self,
        local_items: list[KnowledgeItem],
        *,
        requirement: str,
        keywords: list[str],
    ) -> dict[str, Any]:
        stage_guidance: dict[str, list[str]] = {stage: [] for stage in self._STAGE_ORDER}
        hard_constraints: list[str] = []

        for item in local_items:
            domain = self._source_domain(item)
            stages = self._DOMAIN_STAGE_MAP.get(domain, ["research", "prd", "architecture", "spec"])
            snippet = item.snippet.strip() or "将该知识作为当前阶段的约束输入。"
            entry = f"{item.title}（{item.source}）: {snippet[:140]}"
            for stage in stages:
                stage_guidance.setdefault(stage, [])
                if entry not in stage_guidance[stage]:
                    stage_guidance[stage].append(entry)
            if self._constraint_type(item) == "hard-gate":
                hard_rule = f"{item.title}（{item.source}）属于硬门禁/基线，命中后必须进入对应阶段的文档、Spec 或验收。"
                if hard_rule not in hard_constraints:
                    hard_constraints.append(hard_rule)

        normalized_stage_guidance = {
            stage: entries[:5] for stage, entries in stage_guidance.items() if entries
        }
        framework_guidance = self._infer_framework_guidance(
            requirement=requirement,
            keywords=keywords,
        )
        return {
            "hard_constraints": hard_constraints[:8],
            "stage_guidance": normalized_stage_guidance,
            "framework_guidance": framework_guidance,
        }

    def _stage_label(self, stage: str) -> str:
        labels = {
            "research": "Research / 同类产品研究",
            "prd": "PRD / 产品需求文档",
            "architecture": "Architecture / 架构设计",
            "uiux": "UIUX / 交互与视觉规范",
            "spec": "Spec / 变更规范与任务拆解",
            "frontend": "Frontend / 前端实现与运行验证",
            "backend": "Backend / 后端与联调",
            "quality": "Quality / 测试、安全与质量门禁",
            "delivery": "Delivery / 交付、部署与发布",
        }
        return labels.get(stage, stage)

    def _bundle_signature(self, requirement: str, domain: str) -> str:
        normalized_requirement = requirement.strip().lower()
        normalized_domain = domain.strip().lower()
        allowed_domains = ",".join(sorted(self.allowed_web_domains))
        payload = (
            f"{normalized_requirement}|{normalized_domain}|{self.web_enabled}|{allowed_domains}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _parse_datetime(self, value: str) -> datetime | None:
        cleaned = value.strip()
        if not cleaned:
            return None
        normalized = cleaned.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
