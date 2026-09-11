"""
专家工具箱 (Expert Toolkit)
将专家从"角色标签"升级为"武装治理视角"。

每个专家拥有四层能力：
  Layer 1: Profile — 角色描述（现有 ExpertProfile，来自 orchestrator.experts）
  Layer 2: Knowledge — 自动绑定的知识文件和行业知识
  Layer 3: Rules — 该专家负责的验证规则和红队规则
  Layer 4: Protocol — 交叉审查协议和 Prompt 注入指令

开发：Excellent（11964948@qq.com）
创建时间：2026-03-28
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..orchestrator.experts import ExpertRole

# ===================================================================
# Layer 2: Knowledge
# ===================================================================


@dataclass
class ExpertKnowledge:
    """专家知识武器库——将知识目录映射到专家角色。"""

    domains: list[str]
    """关联的知识领域，如 ``["security", "architecture"]``。"""

    key_files: list[str]
    """核心知识文件相对路径（相对于 ``knowledge/`` 根目录）。"""

    industry_aware: bool = False
    """是否在运行时加载行业知识（``knowledge/industries/``）。"""

    _resolved_files: list[str] = field(default_factory=list, repr=False)
    """运行时解析后的完整文件列表（绝对路径）。"""

    def resolve(self, knowledge_dir: Path, industry: str = "") -> list[str]:
        """解析实际存在的知识文件，返回绝对路径列表。

        Args:
            knowledge_dir: ``knowledge/`` 目录的绝对路径。
            industry: 行业标识，如 ``"fintech"``。仅当 *industry_aware* 为 True 时使用。

        Returns:
            已解析且存在于磁盘上的文件绝对路径列表。
        """
        resolved: list[str] = []

        # 1. 解析 key_files
        for rel in self.key_files:
            full = knowledge_dir / rel
            if full.exists():
                resolved.append(str(full.resolve()))

        # 2. 按 domain 扫描 01-standards / 04-antipatterns / 03-checklists
        for domain in self.domains:
            domain_dir = knowledge_dir / domain
            if not domain_dir.is_dir():
                continue
            for sub in ("01-standards", "04-antipatterns", "03-checklists"):
                sub_dir = domain_dir / sub
                if sub_dir.is_dir():
                    for md in sorted(sub_dir.glob("*.md")):
                        path_str = str(md.resolve())
                        if path_str not in resolved:
                            resolved.append(path_str)

        # 3. 行业知识（可选）
        if self.industry_aware and industry:
            ind_dir = knowledge_dir / "industries" / industry
            if ind_dir.is_dir():
                for md in sorted(ind_dir.rglob("*.md")):
                    path_str = str(md.resolve())
                    if path_str not in resolved:
                        resolved.append(path_str)

        self._resolved_files = resolved
        return resolved


# ===================================================================
# Layer 3: Rules
# ===================================================================


@dataclass
class ExpertRules:
    """专家验证规则集——绑定质量门禁和红队规则到专家。"""

    validation_rule_ids: list[str]
    """验证规则 ID 列表，如 ``["SEC-001", "SEC-002"]``。"""

    redteam_rule_ids: list[str] = field(default_factory=list)
    """红队规则 ID 列表，如 ``["RT-SEC-001"]``。"""

    quality_dimensions: list[dict[str, object]] = field(default_factory=list)
    """质量维度定义，每项含 *name* / *weight* / *min_score*。

    示例::

        [{"name": "安全", "weight": 1.5, "min_score": 80}]
    """


# ===================================================================
# Layer 4: Protocol
# ===================================================================


@dataclass
class ExpertReviewProtocol:
    """交叉审查协议——定义专家间的审查关系。"""

    reviews_output_of: list[str]
    """本专家审查哪些专家的输出，如 ``["ARCHITECT", "CODE"]``。"""

    reviewed_by: list[str]
    """本专家的输出被哪些专家审查，如 ``["QA", "SECURITY"]``。"""

    review_dimensions: list[dict[str, object]] = field(default_factory=list)
    """审查维度定义。

    示例::

        [{"dimension": "安全合规", "checklist": ["OWASP Top 10 覆盖", "输入验证"]}]
    """


# ===================================================================
# ExpertToolkit — 完整四层能力
# ===================================================================


@dataclass
class ExpertToolkit:
    """完整的专家工具箱，聚合四层能力。

    同时保留与旧版接口的兼容属性（``expert_id``, ``name``, ``description``,
    ``playbook``, ``phase_checklists``），以便下游消费者无感迁移。
    """

    role: str
    """ExpertRole.value，如 ``"PM"`` / ``"SECURITY"``。"""

    knowledge: ExpertKnowledge
    rules: ExpertRules
    protocol: ExpertReviewProtocol

    system_prompt_injection: str
    """注入宿主的专家级系统指令。"""

    phase_prompts: dict[str, str] = field(default_factory=dict)
    """各阶段的专门指令，key 为阶段名
    (``research`` / ``docs`` / ``spec`` / ``frontend`` / ``backend`` / ``quality`` / ``delivery``)。
    """

    # -- 兼容旧版属性 --------------------------------------------------
    expert_id: str = ""
    """兼容旧版：等同于 *role*。"""

    name: str = ""
    """兼容旧版：专家中文名称。"""

    description: str = ""
    """兼容旧版：专家简短描述。"""

    playbook: list[str] = field(default_factory=list)
    """兼容旧版：专家方法论条目。"""

    phase_checklists: dict[str, list[str]] = field(default_factory=dict)
    """兼容旧版：各阶段检查清单（从新 ``protocol`` 和 ``phase_prompts`` 生成）。"""

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def get_knowledge_context(
        self,
        knowledge_dir: Path,
        industry: str = "",
        phase: str = "",
    ) -> str:
        """获取该专家的知识上下文（用于注入 Prompt）。

        Args:
            knowledge_dir: ``knowledge/`` 目录绝对路径。
            industry: 行业标识。
            phase: 当前阶段名。

        Returns:
            拼接后的知识上下文字符串。
        """
        files = self.knowledge.resolve(knowledge_dir, industry)
        if not files:
            return ""

        sections: list[str] = [
            f"## {self.role} 专家知识上下文",
            "",
        ]

        if phase:
            sections.append(f"当前阶段: {phase}")
            sections.append("")

        sections.append(f"找到 {len(files)} 个候选知识文件，可按当前问题读取:")
        for f in files:
            sections.append(f"  - {f}")
        sections.append("")

        return "\n".join(sections)

    def get_review_checklist(self, phase: str) -> list[str]:
        """获取该阶段的审查清单。

        合并三个来源：*protocol.review_dimensions* 中的 checklist、
        *rules.quality_dimensions* 中的阈值要求、*phase_prompts* 中的阶段指令。

        Args:
            phase: 阶段名称。

        Returns:
            审查检查项列表。
        """
        items: list[str] = []

        # 1. 来自 review_dimensions
        for dim in self.protocol.review_dimensions:
            checklist = dim.get("checklist", [])
            if isinstance(checklist, list):
                for item in checklist:
                    if isinstance(item, str):
                        items.append(item)

        # 2. 来自 quality_dimensions
        for qdim in self.rules.quality_dimensions:
            dim_name = qdim.get("name", "")
            min_score = qdim.get("min_score", 0)
            if dim_name:
                items.append(
                    f"{dim_name} 维度按项目已确认阈值检查（内置参考 {min_score} 不覆盖项目配置）"
                )

        # 3. 来自 phase_prompts
        phase_prompt = self.phase_prompts.get(phase, "")
        if phase_prompt:
            items.append(f"[阶段指令] {phase_prompt}")

        return items

    def get_prompt_injection(self, phase: str) -> str:
        """获取该阶段的 Prompt 注入内容。

        Args:
            phase: 阶段名称。

        Returns:
            完整的注入文本（``system_prompt_injection`` + ``phase_prompts[phase]``）。
        """
        parts: list[str] = [self.system_prompt_injection]
        phase_prompt = self.phase_prompts.get(phase, "")
        if phase_prompt:
            parts.append(f"\n[{phase} 阶段补充指令] {phase_prompt}")
        return "\n".join(parts)


# ===================================================================
# 阶段 → 专家映射（保留旧版常量供下游引用）
# ===================================================================

PHASE_EXPERT_MAP: dict[str, list[str]] = {
    "research": ["PRODUCT", "PM", "ARCHITECT"],
    "docs": ["PM", "ARCHITECT", "UI", "UX", "SECURITY"],
    "spec": ["PM", "ARCHITECT", "CODE", "DBA"],
    "frontend": ["UI", "UX", "CODE", "SECURITY"],
    "backend": ["ARCHITECT", "CODE", "DBA", "SECURITY"],
    "quality": ["QA", "SECURITY", "DEVOPS"],
    "delivery": ["DEVOPS", "QA", "RCA"],
}


# ===================================================================
# 11 位专家的完整工具箱定义
# ===================================================================

_EXPERT_TOOLKITS: dict[str, ExpertToolkit] = {
    # ---------------------------------------------------------------
    # PRODUCT — 产品负责人
    # ---------------------------------------------------------------
    "PRODUCT": ExpertToolkit(
        role="PRODUCT",
        expert_id="PRODUCT",
        name="产品负责人",
        description="产品闭环、功能缺口、体验总审查、优先级取舍",
        knowledge=ExpertKnowledge(
            domains=["product"],
            key_files=[
                "product/01-standards/product-management-complete.md",
            ],
            industry_aware=True,
        ),
        rules=ExpertRules(
            validation_rule_ids=["PROD-001"],
            quality_dimensions=[
                {"name": "产品完整性", "weight": 1.5, "min_score": 80},
                {"name": "首次上手路径", "weight": 1.2, "min_score": 75},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=[],
            reviewed_by=["PM", "QA"],
            review_dimensions=[
                {
                    "dimension": "产品闭环",
                    "checklist": [
                        "首次上手路径是否清晰",
                        "确认门/返工门/发布门是否串联",
                        "缺口是否可转化为行动项",
                        "证据链是否一致",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以产品负责人视角审查：\n"
            "1) 首次上手路径是否明确（用户知道第一步做什么）\n"
            "2) 功能闭环是否完整（发现->执行->恢复）\n"
            "3) 确认门/返工门/发布门之间是否断链\n"
            "4) 缺口是否可转化为下一步行动\n"
            "5) 优先级是否对齐商业目标"
        ),
        phase_prompts={
            "research": "聚焦同类产品的首次上手路径和功能缺口分析",
            "docs": "确保 PRD 中每项能力有发现路径、执行路径和恢复路径",
            "quality": "检查产品审查报告的问题分级和行动项完整性",
        },
        playbook=[
            "先看首次上手路径、成功标志和失败恢复是否清晰，再看实现细节。",
            "从产品完整性角度盘点缺失能力、断链流程和交付证据缺口。",
            "把问题按'阻断首次使用/影响闭环/可延后优化'分层，优先修阻断项。",
        ],
        phase_checklists={
            "research": [
                "目标用户和核心场景是否明确",
                "北极星指标是否定义",
                "竞品差异化方向是否清晰",
            ],
            "quality": [
                "首次上手路径是否可走通",
                "功能闭环是否完整，无断链",
                "交付证据链是否齐全",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # PM — 产品经理
    # ---------------------------------------------------------------
    "PM": ExpertToolkit(
        role="PM",
        expert_id="PM",
        name="产品经理",
        description="需求分析、PRD 编写、用户故事、业务规则",
        knowledge=ExpertKnowledge(
            domains=["product"],
            key_files=[
                "product/01-standards/product-management-complete.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["DOC-001"],
            quality_dimensions=[
                {"name": "需求完整性", "weight": 1.5, "min_score": 80},
                {"name": "验收标准可测试性", "weight": 1.3, "min_score": 75},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=[],
            reviewed_by=["ARCHITECT", "QA", "SECURITY"],
            review_dimensions=[
                {
                    "dimension": "需求质量",
                    "checklist": [
                        "目标用户是否明确",
                        "核心场景是否覆盖",
                        "验收标准是否可测试",
                        "非功能需求是否完整",
                        "优先级是否合理",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以资深 PM 视角审查：\n"
            "1) 目标用户是否明确\n"
            "2) 核心场景是否覆盖\n"
            "3) 验收标准是否可测试\n"
            "4) 非功能需求是否完整\n"
            "5) 优先级是否合理"
        ),
        phase_prompts={
            "research": "对标竞品功能矩阵，识别差异化点和 MVP 边界",
            "docs": "确保 PRD 有本轮角色、行为与可观察验收结果；Given-When-Then 为可选表达",
            "spec": "检查 Spec 中 SHALL/MUST 需求是否覆盖 PRD 的 P0 功能",
        },
        playbook=[
            "明确目标用户、核心场景与北极星指标。",
            "将需求拆分为 MUST/SHOULD/COULD，并定义验收标准。",
            "补充边界条件与失败场景，避免需求歧义。",
        ],
        phase_checklists={
            "research": [
                "有市场判断需求时比较相关替代方案，数量以决策需要为准",
                "共性功能模块已提取",
                "关键用户流程已梳理",
            ],
            "docs": [
                "需求已按 MUST/SHOULD/COULD 分级",
                "每条需求有可测试验收标准",
                "边界条件和失败场景已补充",
            ],
            "spec": [
                "任务粒度适中，可在 1-2 小时内完成",
                "任务间依赖关系已标注",
                "优先级排序与 PRD 一致",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # ARCHITECT — 架构师
    # ---------------------------------------------------------------
    "ARCHITECT": ExpertToolkit(
        role="ARCHITECT",
        expert_id="ARCHITECT",
        name="架构师",
        description="系统设计、技术选型、架构文档、API 设计",
        knowledge=ExpertKnowledge(
            domains=["architecture", "cloud-native"],
            key_files=[
                "architecture/01-standards/microservices-patterns.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["ARCH-001", "ARCH-002"],
            quality_dimensions=[
                {"name": "架构合理性", "weight": 1.5, "min_score": 80},
                {"name": "API 设计", "weight": 1.2, "min_score": 75},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["PM"],
            reviewed_by=["SECURITY", "CODE"],
            review_dimensions=[
                {
                    "dimension": "架构质量",
                    "checklist": [
                        "系统分层是否清晰",
                        "技术选型是否有 ADR",
                        "API 设计是否 RESTful",
                        "数据流是否完整",
                        "扩展性是否考虑",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以架构师视角审查：\n"
            "1) 系统分层是否清晰\n"
            "2) 技术选型是否有 ADR（架构决策记录）\n"
            "3) API 设计是否 RESTful\n"
            "4) 数据流是否完整\n"
            "5) 扩展性是否考虑"
        ),
        phase_prompts={
            "docs": "架构说明本轮边界和数据流，只有重要且难逆的取舍才记录 ADR",
            "spec": "验证 Spec 的技术方案与架构文档一致",
            "backend": "检查实现是否遵循架构文档中的模块边界和通信契约",
        },
        playbook=[
            "先定义系统边界与模块职责，再确定通信契约。",
            "有容量或扩展需求时估算关键链路，按瓶颈选择缓存、队列等方案。",
            "沉淀可演进架构决策记录（ADR），降低后续返工风险。",
        ],
        phase_checklists={
            "research": [
                "关键技术方案可行性已评估",
                "性能瓶颈和扩展策略已分析",
            ],
            "docs": [
                "系统边界与模块职责已定义",
                "通信契约（API/消息）已规范",
                "架构决策记录（ADR）已沉淀",
            ],
            "spec": [
                "技术选型与架构文档一致",
                "接口契约在 Spec 中可追溯",
            ],
            "backend": [
                "关键链路容量估算已完成",
                "缓存/队列/分片策略已明确",
                "容错与降级方案已设计",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # UI — UI 设计师
    # ---------------------------------------------------------------
    "UI": ExpertToolkit(
        role="UI",
        expert_id="UI",
        name="UI 设计师",
        description="视觉设计、设计规范、组件库、品牌一致性",
        knowledge=ExpertKnowledge(
            domains=["design", "frontend"],
            key_files=[
                "design/01-standards/design-system-complete.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["UI-001"],
            quality_dimensions=[
                {"name": "视觉一致性", "weight": 1.3, "min_score": 75},
                {"name": "品牌识别度", "weight": 1.2, "min_score": 70},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["UX"],
            reviewed_by=["UX", "QA"],
            review_dimensions=[
                {
                    "dimension": "视觉设计",
                    "checklist": [
                        "Token 体系是否完整（颜色/字体/间距/圆角/阴影）",
                        "组件状态是否齐全（hover/focus/loading/empty/error/disabled）",
                        "是否避免 AI 模板化视觉（紫色渐变/emoji 图标）",
                        "信息层级和视觉重量是否合理",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以 UI 设计师视角审查：\n"
            "1) Token 体系是否完整定义\n"
            "2) 组件状态矩阵是否齐全\n"
            "3) 是否避免 AI 模板化视觉（紫色渐变、emoji 图标、系统字体直出）\n"
            "4) 信息层级是否清晰\n"
            "5) 品牌识别度是否足够"
        ),
        phase_prompts={
            "docs": "UIUX 文档必须先定义 Token 再设计组件",
            "frontend": "实现时先冻结 Token 再搭建页面，禁止跳过 Token 直接写样式",
        },
        playbook=[
            "统一设计 token（颜色、间距、字体）并固化到组件层。",
            "优先实现高频核心页面，保证视觉一致性和可读性。",
            "在桌面与移动端分别验证层级、对比度和可触达性。",
        ],
        phase_checklists={
            "docs": [
                "设计 token（颜色/间距/字体）已定义",
                "组件规范已统一",
            ],
            "frontend": [
                "视觉一致性已验证",
                "高频核心页面已优先实现",
                "桌面与移动端层级、对比度已检查",
                "无 emoji 功能图标",
                "图标库已声明且统一使用",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # UX — UX 设计师
    # ---------------------------------------------------------------
    "UX": ExpertToolkit(
        role="UX",
        expert_id="UX",
        name="UX 设计师",
        description="交互设计、用户体验、信息架构、可用性测试",
        knowledge=ExpertKnowledge(
            domains=["design"],
            key_files=[
                "design/01-standards/design-system-complete.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["UX-001"],
            quality_dimensions=[
                {"name": "交互流畅度", "weight": 1.3, "min_score": 75},
                {"name": "可访问性", "weight": 1.0, "min_score": 70},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["UI", "PM"],
            reviewed_by=["QA"],
            review_dimensions=[
                {
                    "dimension": "交互体验",
                    "checklist": [
                        "核心任务流步骤数是否合理",
                        "导航层级是否便于目标用户完成当前任务",
                        "错误状态是否提供恢复指引",
                        "加载/空/错误状态是否完整",
                        "WCAG 2.1 AA 是否满足",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以 UX 设计师视角审查：\n"
            "1) 用户旅程是否覆盖主路径和异常路径\n"
            "2) 导航结构是否符合当前信息量和用户任务\n"
            "3) 表单是否按场景选择提交、失焦或必要的即时验证，并能恢复错误\n"
            "4) 关键操作是否按后果与可逆性选择确认、撤销或恢复\n"
            "5) 可访问性（WCAG 2.1 AA）是否满足"
        ),
        phase_prompts={
            "docs": "UIUX 文档说明本轮任务流程和必要页面层级；复杂关系按需用图解释",
            "frontend": "验证核心任务流步骤数不超过设计规范上限",
        },
        playbook=[
            "梳理关键任务流并减少不必要步骤。",
            "定义空状态、错误态与加载态，避免流程中断。",
            "有量化使用分析需求时安排适用埋点；其他任务用操作场景验证。",
        ],
        phase_checklists={
            "docs": [
                "关键任务流已梳理，步骤已精简",
                "空状态/错误态/加载态已定义",
            ],
            "frontend": [
                "转化漏斗路径无断链",
                "可观测埋点已规划",
                "交互反馈（成功/失败/加载）已覆盖",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # SECURITY — 安全专家
    # ---------------------------------------------------------------
    "SECURITY": ExpertToolkit(
        role="SECURITY",
        expert_id="SECURITY",
        name="安全专家",
        description="安全审查、漏洞检测、威胁建模、合规",
        knowledge=ExpertKnowledge(
            domains=["security"],
            key_files=[
                "security/01-standards/owasp-top10-complete.md",
                "security/04-antipatterns/security-coding-antipatterns.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["SEC-001", "SEC-002", "SEC-003"],
            redteam_rule_ids=["RT-SEC-001", "RT-SEC-002", "RT-SEC-003"],
            quality_dimensions=[
                {"name": "安全", "weight": 1.5, "min_score": 80},
                {"name": "认证授权", "weight": 1.3, "min_score": 80},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["ARCHITECT", "CODE"],
            reviewed_by=["QA"],
            review_dimensions=[
                {
                    "dimension": "安全合规",
                    "checklist": [
                        "OWASP Top 10 是否覆盖",
                        "认证授权是否完整",
                        "输入验证是否充分",
                        "敏感数据是否加密",
                        "依赖是否有已知漏洞",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以安全专家视角审查：\n"
            "1) OWASP Top 10 是否覆盖\n"
            "2) 认证授权是否完整\n"
            "3) 输入验证是否充分\n"
            "4) 敏感数据是否加密\n"
            "5) 依赖是否有已知漏洞"
        ),
        phase_prompts={
            "docs": "架构文档须包含威胁模型和安全边界定义",
            "backend": "检查每个 API 端点的认证/授权/输入验证",
            "quality": "确认红队报告中无 Critical 级未修复问题",
        },
        playbook=[
            "建立威胁模型并优先修复高危攻击面。",
            "对认证、授权、输入校验和密钥管理做最小权限设计。",
            "将 SAST/依赖漏洞扫描纳入 CI 阶段阻断高风险变更。",
        ],
        phase_checklists={
            "docs": [
                "威胁模型已建立",
                "高危攻击面已识别",
            ],
            "frontend": [
                "XSS 防护已验证",
                "敏感数据未暴露到前端",
            ],
            "backend": [
                "认证授权采用最小权限",
                "输入校验覆盖所有入口",
                "密钥管理无硬编码",
                "SAST/依赖漏洞扫描已纳入 CI",
            ],
            "quality": [
                "安全审查报告已输出",
                "高危漏洞修复已验证",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # CODE — 代码专家
    # ---------------------------------------------------------------
    "CODE": ExpertToolkit(
        role="CODE",
        expert_id="CODE",
        name="代码专家",
        description="代码实现、最佳实践、代码审查、性能优化",
        knowledge=ExpertKnowledge(
            domains=["development", "testing"],
            key_files=[
                "development/04-antipatterns/code-smell-antipatterns.md",
                "testing/01-standards/testing-strategy-complete.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["CQ-001", "CQ-002", "TEST-001"],
            quality_dimensions=[
                {"name": "代码质量", "weight": 1.3, "min_score": 80},
                {"name": "测试覆盖", "weight": 1.2, "min_score": 75},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["ARCHITECT"],
            reviewed_by=["SECURITY", "QA"],
            review_dimensions=[
                {
                    "dimension": "代码工程",
                    "checklist": [
                        "函数职责是否单一",
                        "异常处理是否完整（不吞异常）",
                        "命名是否清晰见名知意",
                        "Linter 是否零警告",
                        "核心逻辑是否有测试覆盖",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以代码专家视角审查：\n"
            "1) 函数职责和耦合是否清晰，避免机械按行数拆分\n"
            "2) 异常处理是否完整\n"
            "3) 命名是否清晰\n"
            "4) Linter 是否零警告\n"
            "5) 核心逻辑是否有测试覆盖"
        ),
        phase_prompts={
            "frontend": "检查组件拆分、状态管理和边界条件处理",
            "backend": "检查模块边界、错误处理链和日志规范",
            "quality": "确认代码审查无遗留 TODO/FIXME",
        },
        playbook=[
            "保持单一职责与清晰边界，减少隐式耦合。",
            "核心逻辑补充单元测试和回归测试用例。",
            "对异常处理、日志与可观测性做统一约束。",
        ],
        phase_checklists={
            "spec": [
                "实现方案与架构文档一致",
                "核心模块职责清晰，无隐式耦合",
            ],
            "frontend": [
                "组件单一职责，可复用",
                "状态管理方案统一",
                "异常处理与日志规范一致",
            ],
            "backend": [
                "API 实现与契约一致",
                "核心逻辑有单元测试",
                "异常处理和日志统一约束",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # DBA — 数据库专家
    # ---------------------------------------------------------------
    "DBA": ExpertToolkit(
        role="DBA",
        expert_id="DBA",
        name="数据库专家",
        description="数据库设计、SQL 优化、数据建模、迁移策略",
        knowledge=ExpertKnowledge(
            domains=["data", "data-engineering"],
            key_files=[
                "data/01-standards/postgresql-complete.md",
                "data/04-antipatterns/database-antipatterns.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["DB-001"],
            quality_dimensions=[
                {"name": "数据模型", "weight": 1.3, "min_score": 75},
                {"name": "查询性能", "weight": 1.2, "min_score": 75},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["ARCHITECT"],
            reviewed_by=["CODE", "SECURITY"],
            review_dimensions=[
                {
                    "dimension": "数据层",
                    "checklist": [
                        "ER 图是否完整",
                        "索引策略是否合理",
                        "迁移是否有与数据兼容的恢复方案",
                        "敏感字段是否标记加密",
                        "是否有 N+1 查询风险",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以数据库专家视角审查：\n"
            "1) 数据模型是否规范（ER 图完整）\n"
            "2) 索引策略是否合理\n"
            "3) 迁移是否有与数据兼容的恢复方案\n"
            "4) 敏感数据是否加密存储\n"
            "5) 是否有 N+1 查询风险"
        ),
        phase_prompts={
            "docs": "架构文档须包含 ER 图和索引策略",
            "backend": "检查 ORM 查询是否有 N+1 问题，迁移是否有适用恢复方案",
        },
        playbook=[
            "先建模实体关系，再补充索引和约束策略。",
            "对高频查询设计覆盖索引并验证执行计划。",
            "涉及迁移时核对兼容和恢复；发布策略依据运行形态与已有授权选择。",
        ],
        phase_checklists={
            "spec": [
                "实体关系已建模",
                "索引策略已规划",
            ],
            "backend": [
                "高频查询有覆盖索引",
                "执行计划已验证",
                "迁移的恢复方案与限制已明确",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # QA — 质量保证专家
    # ---------------------------------------------------------------
    "QA": ExpertToolkit(
        role="QA",
        expert_id="QA",
        name="QA 专家",
        description="质量保证、测试策略、自动化测试、质量门禁",
        knowledge=ExpertKnowledge(
            domains=["testing"],
            key_files=[
                "testing/01-standards/testing-strategy-complete.md",
                "testing/04-antipatterns/testing-antipatterns.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["TEST-001", "TEST-002"],
            quality_dimensions=[
                {"name": "测试覆盖", "weight": 1.5, "min_score": 80},
                {"name": "质量门禁", "weight": 1.3, "min_score": 80},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["PM", "CODE", "SECURITY"],
            reviewed_by=[],
            review_dimensions=[
                {
                    "dimension": "质量保障",
                    "checklist": [
                        "质量门禁评分是否满足项目已确认阈值",
                        "无 Critical 级失败项",
                        "测试覆盖是否满足项目既有要求和本轮风险",
                        "相关关键 API 是否覆盖正常与失败路径",
                        "交付证据是否完整",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以 QA 专家视角审查：\n"
            "1) 质量门禁评分是否满足项目已确认阈值\n"
            "2) 无 Critical 级失败项\n"
            "3) 核心逻辑的测试覆盖满足项目既有要求\n"
            "4) 相关关键 API 有对应验证\n"
            "5) 交付证据链完整"
        ),
        phase_prompts={
            "spec": "验证 Spec 中每个 SHALL 需求都有对应的测试策略",
            "quality": "运行全量质量门禁并生成审计证据",
            "delivery": "确认 proof-pack 和 release readiness 引用同一套证据",
        },
        playbook=[
            "按风险优先级制定测试策略（冒烟/回归/性能）。",
            "建立关键路径自动化测试并接入质量门禁。",
            "输出缺陷分级和修复 SLA，形成闭环。",
        ],
        phase_checklists={
            "quality": [
                "冒烟/回归/性能测试策略已制定",
                "关键路径自动化测试已接入",
                "质量门禁阈值已达标",
                "缺陷分级和修复 SLA 已输出",
            ],
            "delivery": [
                "测试报告完整且可追溯",
                "回归测试全部通过",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # DEVOPS — DevOps 工程师
    # ---------------------------------------------------------------
    "DEVOPS": ExpertToolkit(
        role="DEVOPS",
        expert_id="DEVOPS",
        name="DevOps 工程师",
        description="部署、CI/CD、容器化、监控告警",
        knowledge=ExpertKnowledge(
            domains=["devops", "cicd", "operations"],
            key_files=[
                "devops/01-standards/docker-complete.md",
                "cicd/01-standards/github-actions-complete.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["PERF-001"],
            quality_dimensions=[
                {"name": "部署可靠性", "weight": 1.3, "min_score": 75},
                {"name": "可观测性", "weight": 1.0, "min_score": 70},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["ARCHITECT"],
            reviewed_by=["SECURITY"],
            review_dimensions=[
                {
                    "dimension": "运维就绪",
                    "checklist": [
                        "CI/CD 流水线是否完整",
                        "Docker 构建是否可复现",
                        "部署是否有回滚方案",
                        "健康检查端点是否定义",
                        "监控告警是否配置",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以 DevOps 工程师视角审查：\n"
            "1) CI/CD 流水线是否完整\n"
            "2) 构建是否可复现（Docker 多阶段构建）\n"
            "3) 部署是否有回滚方案\n"
            "4) 健康检查端点是否定义\n"
            "5) 监控告警是否覆盖关键指标"
        ),
        phase_prompts={
            "docs": "架构文档须包含部署拓扑和环境配置",
            "delivery": "生成 CI/CD 配置并验证构建可复现",
        },
        playbook=[
            "统一环境配置与密钥管理，减少环境漂移。",
            "构建 CI/CD 流水线并开启发布审计与回滚策略。",
            "完善监控告警与容量基线，保障上线稳定性。",
        ],
        phase_checklists={
            "quality": [
                "环境配置统一，无漂移",
                "密钥管理规范化",
            ],
            "delivery": [
                "CI/CD 流水线可用且有审计",
                "回滚策略已验证",
                "监控告警与容量基线已设置",
            ],
        },
    ),
    # ---------------------------------------------------------------
    # RCA — 根因分析专家
    # ---------------------------------------------------------------
    "RCA": ExpertToolkit(
        role="RCA",
        expert_id="RCA",
        name="根因分析专家",
        description="根因分析、故障复盘、风险识别、改进建议",
        knowledge=ExpertKnowledge(
            domains=["operations"],
            key_files=[
                "operations/01-standards/incident-management-complete.md",
            ],
        ),
        rules=ExpertRules(
            validation_rule_ids=["RCA-001"],
            quality_dimensions=[
                {"name": "根因准确度", "weight": 1.5, "min_score": 80},
                {"name": "防复发有效性", "weight": 1.2, "min_score": 75},
            ],
        ),
        protocol=ExpertReviewProtocol(
            reviews_output_of=["CODE", "DEVOPS"],
            reviewed_by=["QA"],
            review_dimensions=[
                {
                    "dimension": "根因分析",
                    "checklist": [
                        "根因是否是真正的根因（非症状）",
                        "修复方案是否有回归测试",
                        "影响范围是否评估完整",
                        "防复发措施是否记录到知识库",
                    ],
                },
            ],
        ),
        system_prompt_injection=(
            "以根因分析专家视角审查：\n"
            "1) 根因是否已明确（非症状层面）\n"
            "2) 修复方案是否有回归测试覆盖\n"
            "3) 影响范围是否已完整评估\n"
            "4) 防复发措施是否记录\n"
            "5) 经验是否已写回知识库"
        ),
        phase_prompts={
            "quality": "检查质量报告中的问题是否追溯到根因",
        },
        playbook=[
            "先确认用户影响范围，再聚焦首个异常时间点。",
            "使用时间线 + 5 Whys 还原根因链路。",
            "输出可执行改进项并设置验证指标防止复发。",
        ],
        phase_checklists={
            "delivery": [
                "已知风险已记录并有缓解方案",
                "改进项可执行且有验证指标",
            ],
        },
    ),
}


# ===================================================================
# 便捷函数
# ===================================================================


def get_toolkit(role: str | ExpertRole) -> ExpertToolkit:
    """按角色获取工具箱。

    Args:
        role: ``ExpertRole`` 枚举或其字符串 value。

    Returns:
        对应的 ``ExpertToolkit`` 实例。

    Raises:
        KeyError: 角色不存在。
    """
    key = role.value if isinstance(role, ExpertRole) else role.upper()
    return _EXPERT_TOOLKITS[key]


def get_all_toolkits() -> dict[str, ExpertToolkit]:
    """返回全部专家工具箱字典（引用，非副本）。"""
    return _EXPERT_TOOLKITS


def get_active_toolkits_for_phase(phase: str) -> dict[str, ExpertToolkit]:
    """返回在指定阶段有激活角色的工具箱子集。

    优先使用 ``PHASE_EXPERT_MAP`` 中的显式映射，回退到 ``phase_prompts`` 检测。

    Args:
        phase: 阶段名称
            (``research`` / ``docs`` / ``spec`` / ``frontend`` / ``backend`` /
            ``quality`` / ``delivery``)。

    Returns:
        ``{role: toolkit}`` 字典。
    """
    expert_ids = PHASE_EXPERT_MAP.get(phase, [])
    if expert_ids:
        return {eid: _EXPERT_TOOLKITS[eid] for eid in expert_ids if eid in _EXPERT_TOOLKITS}
    # 回退：有 phase_prompts 条目的专家视为该阶段激活
    return {role: tk for role, tk in _EXPERT_TOOLKITS.items() if phase in tk.phase_prompts}


def load_expert_toolkits() -> dict[str, ExpertToolkit]:
    """加载所有专家工具箱。

    保留此函数签名以兼容下游调用方
    (``prompt_generator.py``, ``quality_gate.py``)。
    新代码建议直接使用 :func:`get_all_toolkits`。
    """
    return _EXPERT_TOOLKITS
