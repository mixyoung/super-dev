"""
架构决策记录 (ADR) 自动生成器

开发：Excellent（11964948@qq.com）
功能：在生成架构文档时，自动为关键技术选型生成 ADR
作用：受 adr-tools / Log4brains 启发，标准化记录架构决策及其上下文和后果
创建时间：2026-03-28
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ADR 状态常量
STATUS_PROPOSED = "proposed"
STATUS_ACCEPTED = "accepted"
STATUS_DEPRECATED = "deprecated"
STATUS_SUPERSEDED = "superseded"

_VALID_STATUSES = {STATUS_PROPOSED, STATUS_ACCEPTED, STATUS_DEPRECATED, STATUS_SUPERSEDED}

# 内置的技术选型知识库：每个技术类别包含常见方案及其优劣
_BUILTIN_OPTIONS: dict[str, list[dict[str, object]]] = {
    "database": [
        {
            "name": "PostgreSQL",
            "pros": ["ACID 事务", "丰富的扩展生态", "JSON/JSONB 支持", "成熟的社区"],
            "cons": ["水平扩展较复杂", "配置调优门槛较高"],
            "fit_score": 85,
        },
        {
            "name": "MySQL",
            "pros": ["广泛使用", "生态成熟", "读性能优秀"],
            "cons": ["JSON 支持较弱", "存储引擎碎片化"],
            "fit_score": 75,
        },
        {
            "name": "MongoDB",
            "pros": ["灵活 Schema", "水平扩展方便", "文档模型直觉"],
            "cons": ["无原生 ACID（多文档）", "存储开销较大"],
            "fit_score": 70,
        },
    ],
    "frontend": [
        {
            "name": "React",
            "pros": ["巨大生态", "灵活组合", "SSR/SSG 支持好 (Next.js)"],
            "cons": ["无官方全家桶", "学习曲线中等"],
            "fit_score": 85,
        },
        {
            "name": "Vue",
            "pros": ["渐进式", "中文社区活跃", "官方全家桶"],
            "cons": ["TS 集成历史包袱", "大型项目最佳实践较少"],
            "fit_score": 80,
        },
        {
            "name": "Angular",
            "pros": ["企业级全家桶", "强类型", "依赖注入"],
            "cons": ["学习曲线陡", "包体积偏大"],
            "fit_score": 65,
        },
    ],
    "backend": [
        {
            "name": "FastAPI",
            "pros": ["自动文档 (OpenAPI)", "高性能 (async)", "类型提示"],
            "cons": ["生态不如 Django 全面", "ORM 需第三方"],
            "fit_score": 85,
        },
        {
            "name": "Django",
            "pros": ["全栈框架", "ORM/Admin 开箱即用", "安全默认"],
            "cons": ["单体倾向", "异步支持晚"],
            "fit_score": 75,
        },
        {
            "name": "Express (Node.js)",
            "pros": ["极简灵活", "npm 生态", "前后端同语言"],
            "cons": ["缺少约定", "回调地狱（需 async/await）"],
            "fit_score": 75,
        },
    ],
    "deployment": [
        {
            "name": "Kubernetes",
            "pros": ["自动伸缩", "声明式", "生态丰富"],
            "cons": ["运维复杂", "小团队成本高"],
            "fit_score": 80,
        },
        {
            "name": "Docker Compose",
            "pros": ["简单直观", "本地开发友好", "零学习曲线"],
            "cons": ["无编排/自动伸缩", "单机限制"],
            "fit_score": 70,
        },
        {
            "name": "Serverless",
            "pros": ["零运维", "按需付费", "自动扩缩"],
            "cons": ["冷启动", "厂商锁定", "调试困难"],
            "fit_score": 65,
        },
    ],
    "cache": [
        {
            "name": "Redis",
            "pros": ["丰富数据结构", "Pub/Sub", "持久化", "Lua 脚本"],
            "cons": ["单线程瓶颈", "内存成本"],
            "fit_score": 90,
        },
        {
            "name": "Memcached",
            "pros": ["极致简单", "多线程", "内存效率高"],
            "cons": ["仅 KV", "无持久化", "无集群"],
            "fit_score": 60,
        },
    ],
}

# 架构配置字段到 ADR 类别的映射
_CONFIG_KEY_TO_CATEGORY: dict[str, str] = {
    "database": "database",
    "frontend": "frontend",
    "backend": "backend",
    "deployment": "deployment",
    "cache": "cache",
}


@dataclass
class ArchitectureDecisionRecord:
    """架构决策记录 (ADR)。

    Attributes:
        id: ADR 编号，如 ``ADR-001``.
        title: 决策标题，如 "选择 PostgreSQL 作为主数据库".
        status: 决策状态 (proposed/accepted/deprecated/superseded).
        date: 记录日期，ISO 格式.
        context: 决策背景和动机.
        options: 考虑的方案列表，每项包含 name/pros/cons/fit_score.
        decision: 最终选定的方案.
        rationale: 选择该方案的理由.
        consequences: 该决策带来的后果（正面和负面）.
        related_adrs: 相关 ADR 编号列表.
    """

    id: str
    title: str
    status: str
    date: str
    context: str
    options: list[dict] = field(default_factory=list)
    decision: str = ""
    rationale: str = ""
    consequences: str = ""
    related_adrs: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """将 ADR 序列化为 Markdown 格式。

        Returns:
            符合 ADR 标准格式的 Markdown 字符串.
        """
        lines: list[str] = [
            f"# {self.id}: {self.title}",
            "",
            f"**状态**: {self.status}",
            f"**日期**: {self.date}",
            "",
            "## 背景 (Context)",
            "",
            self.context,
            "",
            "## 考虑的方案 (Options)",
            "",
        ]

        for i, opt in enumerate(self.options, 1):
            name = opt.get("name", f"方案 {i}")
            fit = opt.get("fit_score", "N/A")
            lines.append(f"### 方案 {i}: {name} (适配分: {fit})")
            lines.append("")
            pros = opt.get("pros", [])
            if pros:
                lines.append("**优势**:")
                for p in pros:
                    lines.append(f"- {p}")
                lines.append("")
            cons = opt.get("cons", [])
            if cons:
                lines.append("**劣势**:")
                for c in cons:
                    lines.append(f"- {c}")
                lines.append("")

        lines.extend(
            [
                "## 决策 (Decision)",
                "",
                self.decision,
                "",
                "## 理由 (Rationale)",
                "",
                self.rationale,
                "",
                "## 后果 (Consequences)",
                "",
                self.consequences,
                "",
            ]
        )

        if self.related_adrs:
            lines.extend(
                [
                    "## 相关决策",
                    "",
                ]
            )
            for ref in self.related_adrs:
                lines.append(f"- {ref}")
            lines.append("")

        return "\n".join(lines)


class ADRGenerator:
    """架构决策记录生成器。

    自动从项目架构配置中提取关键技术选型，并为每个选型
    生成标准化的 ADR (Architecture Decision Record) 文档。

    Args:
        project_dir: 项目根目录路径.
    """

    def __init__(self, project_dir: Path | str) -> None:
        self.project_dir = Path(project_dir)
        self.adr_dir = self.project_dir / ".super-dev" / "decisions"
        self._next_id: int = 1
        self._sync_next_id()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_from_architecture(self, arch_config: dict) -> list[ArchitectureDecisionRecord]:
        """从架构配置自动生成 ADR 集合。

        为以下选型生成 ADR（如果配置中存在对应字段）:
        - 数据库选型 (PostgreSQL vs MySQL vs MongoDB)
        - 前端框架选型 (React vs Vue vs Angular)
        - 后端框架选型 (FastAPI vs Django vs Express)
        - 部署方式选型 (K8s vs Docker Compose vs Serverless)
        - 缓存选型 (Redis vs Memcached)

        Args:
            arch_config: 架构配置字典，通常来自 ``super-dev.yaml`` 或架构文档解析结果.
                        支持的键: ``database``, ``frontend``, ``backend``,
                        ``deployment``, ``cache``.

        Returns:
            生成的 ADR 列表.
        """
        adrs: list[ArchitectureDecisionRecord] = []

        for config_key, category in _CONFIG_KEY_TO_CATEGORY.items():
            chosen_tech = arch_config.get(config_key)
            if not chosen_tech:
                continue

            # 确保 chosen_tech 是字符串
            if isinstance(chosen_tech, dict):
                chosen_tech = chosen_tech.get("type", chosen_tech.get("name", str(chosen_tech)))
            chosen_tech = str(chosen_tech)

            options = self._get_options_for_category(category)
            if not options:
                continue

            adr = self._generate_category_adr(
                category=category,
                chosen_tech=chosen_tech,
                options=options,
            )
            adrs.append(adr)

        # 标记相关 ADR（数据库和缓存互相关联，前端和后端互相关联）
        self._link_related_adrs(adrs)

        logger.info("从架构配置生成了 %d 个 ADR", len(adrs))
        return adrs

    def generate_adr(
        self,
        title: str,
        context: str,
        options: list[dict],
        decision: str,
        rationale: str,
        consequences: str = "",
        status: str = STATUS_ACCEPTED,
    ) -> ArchitectureDecisionRecord:
        """生成单个 ADR。

        Args:
            title: 决策标题.
            context: 决策背景.
            options: 考虑的方案列表，每项应包含 ``name``, ``pros``, ``cons``.
            decision: 最终决策描述.
            rationale: 决策理由.
            consequences: 决策后果，可选.
            status: ADR 状态，默认 ``accepted``.

        Returns:
            新创建的 ``ArchitectureDecisionRecord``.

        Raises:
            ValueError: 无效的状态值.
        """
        if status not in _VALID_STATUSES:
            raise ValueError(f"无效的 ADR 状态: {status}。有效值: {_VALID_STATUSES}")

        adr_id = self._allocate_id()
        return ArchitectureDecisionRecord(
            id=adr_id,
            title=title,
            status=status,
            date=datetime.now().strftime("%Y-%m-%d"),
            context=context,
            options=options,
            decision=decision,
            rationale=rationale,
            consequences=consequences,
        )

    def save_adr(self, adr: ArchitectureDecisionRecord) -> Path:
        """将 ADR 保存为 Markdown 文件。

        文件名格式: ``ADR-001-title-slug.md``

        Args:
            adr: 要保存的 ADR 实例.

        Returns:
            写入的文件路径.
        """
        self.adr_dir.mkdir(parents=True, exist_ok=True)

        slug = adr.title.lower()
        # 简单 slug 化：中文保留，特殊字符替换为连字符
        safe_chars: list[str] = []
        for ch in slug:
            if ch.isalnum() or ch in ("-", "_") or "\u4e00" <= ch <= "\u9fff":
                safe_chars.append(ch)
            else:
                safe_chars.append("-")
        slug = "".join(safe_chars).strip("-")
        # 压缩连续连字符
        while "--" in slug:
            slug = slug.replace("--", "-")

        filename = f"{adr.id}-{slug}.md"
        filepath = self.adr_dir / filename
        filepath.write_text(adr.to_markdown(), encoding="utf-8")
        logger.info("已保存 ADR: %s -> %s", adr.id, filepath)
        return filepath

    def save_all(self, adrs: list[ArchitectureDecisionRecord]) -> list[Path]:
        """批量保存 ADR 列表。

        Args:
            adrs: ADR 列表.

        Returns:
            写入的文件路径列表.
        """
        return [self.save_adr(adr) for adr in adrs]

    def list_adrs(self) -> list[ArchitectureDecisionRecord]:
        """列出所有已保存的 ADR。

        从磁盘 ``.super-dev/decisions/`` 目录读取所有 ADR Markdown 文件并解析。

        Returns:
            已保存的 ADR 列表（按编号排序）.
        """
        if not self.adr_dir.exists():
            return []

        adrs: list[ArchitectureDecisionRecord] = []
        for md_file in sorted(self.adr_dir.glob("ADR-*.md")):
            try:
                adr = self._parse_adr_file(md_file)
                if adr:
                    adrs.append(adr)
            except Exception:
                logger.exception("解析 ADR 文件失败: %s", md_file)

        return adrs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_next_id(self) -> None:
        """扫描已有 ADR 文件，同步下一个可用编号。"""
        if not self.adr_dir.exists():
            return
        for md_file in self.adr_dir.glob("ADR-*.md"):
            name = md_file.stem  # e.g. "ADR-003-some-title"
            parts = name.split("-", 2)
            if len(parts) >= 2:
                try:
                    num = int(parts[1])
                    if num >= self._next_id:
                        self._next_id = num + 1
                except ValueError:
                    pass

    def _allocate_id(self) -> str:
        """分配下一个 ADR 编号。"""
        adr_id = f"ADR-{self._next_id:03d}"
        self._next_id += 1
        return adr_id

    def _get_options_for_category(self, category: str) -> list[dict]:
        """获取指定类别的内置方案列表。"""
        return [dict(opt) for opt in _BUILTIN_OPTIONS.get(category, [])]

    def _generate_category_adr(
        self,
        category: str,
        chosen_tech: str,
        options: list[dict],
    ) -> ArchitectureDecisionRecord:
        """为一个技术类别生成 ADR。"""
        category_titles: dict[str, str] = {
            "database": "数据库",
            "frontend": "前端框架",
            "backend": "后端框架",
            "deployment": "部署方式",
            "cache": "缓存方案",
        }
        category_cn = category_titles.get(category, category)

        title = f"选择 {chosen_tech} 作为{category_cn}"

        context = (
            f"项目需要选择{category_cn}。"
            f"经过对主流方案的评估，需要在以下方案中做出选择。"
            f"评估维度包括：性能、生态、团队熟悉度、维护成本和长期演进。"
        )

        # 找到选中技术的方案信息
        chosen_option = None
        for opt in options:
            if self._tech_matches(opt.get("name", ""), chosen_tech):
                chosen_option = opt
                break

        if chosen_option:
            pros = chosen_option.get("pros", [])
            pros_text = "、".join(str(p) for p in pros) if pros else "符合项目需求"
            alternatives = [
                opt
                for opt in options
                if str(opt.get("name", "")) != str(chosen_option.get("name", ""))
            ]
            alt_summary = "；".join(
                f"放弃 {opt.get('name', '备选方案')}（短板: {'、'.join(str(c) for c in opt.get('cons', [])[:2]) or '综合适配较低'}）"
                for opt in alternatives[:2]
            )
            decision = f"选择 {chosen_tech} 作为项目的{category_cn}。"
            rationale = f"{chosen_tech} 的主要优势包括: {pros_text}。综合实现复杂度、故障恢复与演进弹性最优。" + (
                f"\n放弃其他备选方案的原因: {alt_summary}。" if alt_summary else ""
            )
            cons = chosen_option.get("cons", [])
            cons_text = "、".join(str(c) for c in cons) if cons else "无明显劣势"
            consequences = (
                f"正面: {pros_text}。\n"
                f"负面/风险: {cons_text}。\n"
                f"适用边界: 仅对关键且难逆的技术选型启用多方案对比，常规局部改动不机械套用。"
            )
        else:
            decision = f"选择 {chosen_tech} 作为项目的{category_cn}。"
            rationale = f"基于项目需求和团队情况，{chosen_tech} 是最合适的选择；常规局部改动豁免额外方案比对。"
            consequences = f"团队需要确保对 {chosen_tech} 有足够的掌握。"

        adr_id = self._allocate_id()
        return ArchitectureDecisionRecord(
            id=adr_id,
            title=title,
            status=STATUS_ACCEPTED,
            date=datetime.now().strftime("%Y-%m-%d"),
            context=context,
            options=options,
            decision=decision,
            rationale=rationale,
            consequences=consequences,
        )

    @staticmethod
    def _tech_matches(option_name: str, chosen_tech: str) -> bool:
        """模糊匹配技术名称。"""
        a = option_name.lower().strip()
        b = chosen_tech.lower().strip()
        return a == b or a.startswith(b) or b.startswith(a) or a in b or b in a

    def _link_related_adrs(self, adrs: list[ArchitectureDecisionRecord]) -> None:
        """为互相关联的 ADR 建立引用关系。"""
        related_groups: list[set[str]] = [
            {"database", "cache"},
            {"frontend", "backend"},
        ]

        # 构建 category -> adr_id 的映射
        category_to_id: dict[str, str] = {}
        for adr in adrs:
            for cat, cn in [
                ("database", "数据库"),
                ("frontend", "前端框架"),
                ("backend", "后端框架"),
                ("deployment", "部署方式"),
                ("cache", "缓存方案"),
            ]:
                if cn in adr.title:
                    category_to_id[cat] = adr.id
                    break

        for adr in adrs:
            adr_cat: str | None = None
            for cat, cn in [
                ("database", "数据库"),
                ("frontend", "前端框架"),
                ("backend", "后端框架"),
                ("deployment", "部署方式"),
                ("cache", "缓存方案"),
            ]:
                if cn in adr.title:
                    adr_cat = cat
                    break

            if not adr_cat:
                continue

            for group in related_groups:
                if adr_cat in group:
                    for other_cat in group:
                        if other_cat != adr_cat and other_cat in category_to_id:
                            ref = category_to_id[other_cat]
                            if ref not in adr.related_adrs:
                                adr.related_adrs.append(ref)

    @staticmethod
    def _parse_adr_file(path: Path) -> ArchitectureDecisionRecord | None:
        """从 Markdown 文件解析 ADR（简单解析）。"""
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")

        if not lines:
            return None

        # 解析标题行: "# ADR-001: 选择 PostgreSQL 作为数据库"
        title_line = lines[0].lstrip("# ").strip()
        parts = title_line.split(":", 1)
        adr_id = (
            parts[0].strip()
            if parts
            else path.stem.split("-", 2)[0] + "-" + path.stem.split("-", 2)[1]
        )
        title = parts[1].strip() if len(parts) > 1 else title_line

        # 解析状态和日期
        status = STATUS_ACCEPTED
        date = ""
        for line in lines[1:10]:
            if line.startswith("**状态**:"):
                status = line.split(":", 1)[1].strip()
            elif line.startswith("**日期**:"):
                date = line.split(":", 1)[1].strip()

        return ArchitectureDecisionRecord(
            id=adr_id,
            title=title,
            status=status,
            date=date,
            context="",  # 简单解析不提取完整正文
        )
