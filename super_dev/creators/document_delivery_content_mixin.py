"""Execution, delivery and supporting-content generators."""

from __future__ import annotations

from datetime import datetime


class DocumentDeliveryContentMixin:
    def extract_requirements(self) -> list:
        """从描述提取需求列表"""
        return list(self.requirement_parser.parse_requirements(self.description))

    def generate_execution_plan(
        self, scenario: str = "0-1", request_mode: str | None = None
    ) -> str:
        """生成分阶段执行路线图（支持 0-1 / 1-N+1）"""
        requirements = self.extract_requirements()
        mode = request_mode or self.requirement_parser.detect_request_mode(self.description)
        phases = self.requirement_parser.build_execution_phases(
            scenario, requirements, request_mode=mode
        )

        lines = [
            f"# {self.name} - 执行路线图",
            "",
            f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> **场景**: {scenario}",
            f"> **请求模式**: {mode}",
            "> **策略**: 先前端可视化，再系统能力闭环",
            "",
            "---",
            "",
            "## 1. 需求范围",
            "",
            "| 模块 | 需求 | 说明 |",
            "|:---|:---|:---|",
        ]

        for req in requirements:
            lines.append(
                f"| {req.get('spec_name', 'core')} | {req.get('req_name', 'n/a')} | {req.get('description', '')} |"
            )

        lines.extend(
            [
                "",
                "## 2. 分阶段计划",
                "",
            ]
        )

        for idx, phase in enumerate(phases, 1):
            lines.extend(
                [
                    f"### Phase {idx}: {phase['title']}",
                    "",
                    f"**目标**: {phase['objective']}",
                    "",
                    "**交付物**:",
                ]
            )
            for item in phase["deliverables"]:
                lines.append(f"- {item}")
            host_playbook = phase.get("host_playbook", [])
            if host_playbook:
                lines.extend(["", "**宿主执行打法**:"])
                for item in host_playbook:
                    lines.append(f"- {item}")
            hard_gates = phase.get("hard_gates", [])
            if hard_gates:
                lines.extend(["", "**阶段硬门禁**:"])
                for item in hard_gates:
                    lines.append(f"- {item}")
            lines.append("")

        lines.extend(
            [
                "## 3. 风险与控制",
                "",
                "- 需求漂移: 每个 Phase 完成后冻结版本并复核。",
                "- 前后端脱节: 在 Phase 2 开始前产出 API 契约草案。",
                "- 质量不足: 每个阶段结束前执行红队审查和质量门禁。",
                "",
                "## 4. 完成定义",
                "",
                "- 所有核心需求存在可验收场景并被实现。",
                "- 前端模块与文档一致，关键链路可演示。",
                "- 质量门禁通过，具备交付上线条件。",
                "",
            ]
        )

        return "\n".join(lines)

    def generate_frontend_blueprint(self) -> str:
        """生成前端先行的模块蓝图"""
        requirements = self.extract_requirements()
        modules = self.requirement_parser.build_frontend_modules(requirements)

        lines = [
            f"# {self.name} - 前端蓝图",
            "",
            f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> **前端框架**: {self.frontend}",
            "> **设计重点**: 先可视化业务流程，再补齐系统深度能力",
            "",
            "---",
            "",
            "## 1. 体验目标",
            "",
            "- 一次进入即可理解产品价值和关键流程。",
            "- 文档和执行状态可追踪，避免信息散落。",
            "- 关键任务路径操作链路最短、反馈明确。",
            "",
            "## 2. 模块拆分",
            "",
        ]

        for index, module in enumerate(modules, 1):
            lines.extend(
                [
                    f"### {index}. {module['name']}",
                    "",
                    f"**目标**: {module['goal']}",
                    "",
                    "**核心元素**:",
                ]
            )
            for element in module["core_elements"]:
                lines.append(f"- {element}")
            lines.append("")

        lines.extend(
            [
                "## 3. 开发顺序",
                "",
                "1. 先实现 `需求总览面板` + `文档工作台`，确保信息结构完整。",
                "2. 再实现业务模块页面，覆盖每条核心需求的主路径。",
                "3. 最后统一交互细节、动效和可访问性。",
                "",
                "## 4. 前后端契约建议",
                "",
                "- 页面只消费稳定 DTO，避免直接绑定数据库结构。",
                "- API 响应必须包含状态码、业务码和可读错误信息。",
                "- 对列表页统一分页/筛选参数结构，减少重复实现。",
                "",
            ]
        )

        return "\n".join(lines)

    def _generate_market_context(self) -> str:
        if self._request_mode() == "bugfix":
            return (
                "- 复用已确认的项目目标；本次只核对缺陷与预期行为，不重新开展立项论证。\n"
                "- 记录受影响的用户结果及修复依据，未知项明确标为待核实。"
            )
        return (
            f"- 当前需求聚焦于“{self.description}”，先复用已有调研；新判断缺少证据时再补充相关研究。\n"
            "- 先复用已有目标和证据；价值不清时比较人工、现成工具与自主开发的收益和维护成本。\n"
            "- 商业项目看客户与收益，内部工具看效率与错误成本，学习项目看学习目标；不统一要求盈利证明。\n"
            "- 分开记录事实、假设和未决问题；必要时提出能改变判断的低成本验证，未执行的实验不能写成已验证。\n"
            "- 结论可为推进、先验证、缩小或建议暂缓，说明依据并由用户决定；本节引用当前调研，不生成另一套报告。\n"
            "- Forge 按本轮需要澄清、检验或改进中心主张；收到新事实后修正假设和方案，保留采用/放弃选项的理由。\n"
            "- 获授权后将结论定向写回原调研并回读，待验证项不可写成实证，方法结束不代表文档确认通过。"
        )

    def _generate_research_evidence_brief(self) -> str:
        summary = self.knowledge_summary or {}
        evidence = summary.get("evidence_distribution", {}) if isinstance(summary, dict) else {}
        confidence = (
            summary.get("research_confidence", "baseline")
            if isinstance(summary, dict)
            else "baseline"
        )
        benchmark = summary.get("benchmark_products", []) if isinstance(summary, dict) else []
        sources = summary.get("primary_sources", []) if isinstance(summary, dict) else []
        lines = [
            f"- **研究可信度**: {confidence}",
            f"- **官方来源**: {evidence.get('official', 0)} 条 / **行业来源**: {evidence.get('industry', 0)} 条 / **社区来源**: {evidence.get('community', 0)} 条",
            "- **研究要求**: 所有关键决策需可追溯到联网研究证据与本地知识约束。",
            "",
            "**对标产品摘要**:",
        ]
        if isinstance(benchmark, list) and benchmark:
            lines.extend(f"- {item}" for item in benchmark[:4])
        else:
            lines.append("- 当前未命中有效对标产品，需由宿主继续联网补齐。")
        lines.extend(["", "**核心来源域名**:"])
        if isinstance(sources, list) and sources:
            for item in sources[:5]:
                if isinstance(item, list | tuple) and len(item) >= 2:
                    lines.append(f"- {item[0]}: {item[1]} 次引用")
        else:
            lines.append("- 暂无可统计域名数据")
        return "\n".join(lines)

    def _generate_knowledge_constraints_section(self) -> str:
        """生成知识约束章节（从 KnowledgePusher 推送的数据）"""
        summary = self.knowledge_summary or {}
        if not isinstance(summary, dict):
            return ""
        constraints = summary.get("pushed_constraints", [])
        antipatterns = summary.get("pushed_antipatterns", [])
        knowledge_files = summary.get("pushed_knowledge_files", [])
        if not constraints and not antipatterns and not knowledge_files:
            return ""

        lines = ["### 知识库硬约束（自动注入）", ""]
        if constraints:
            lines.append("**必须遵循：**")
            for c in constraints[:15]:
                lines.append(f"- {c}")
            lines.append("")
        if antipatterns:
            lines.append("**必须避免：**")
            for a in antipatterns[:10]:
                lines.append(f"- {a}")
            lines.append("")
        if knowledge_files:
            lines.append("**参考知识文件：**")
            for f in knowledge_files[:10]:
                if isinstance(f, dict):
                    lines.append(f"- `{f.get('path', f.get('file', str(f)))}`")
                else:
                    lines.append(f"- `{f}`")
            lines.append("")
        return "\n".join(lines)

    def _generate_solution_tradeoffs(self) -> str:
        summary = self.knowledge_summary or {}
        options = summary.get("implementation_options", []) if isinstance(summary, dict) else []
        lines = [
            "| 方案 | 适用场景 | 核心策略 | 关键权衡 |",
            "|:---|:---|:---|:---|",
        ]
        if isinstance(options, list) and options:
            for option in options:
                if not isinstance(option, dict):
                    continue
                lines.append(
                    f"| {option.get('name', '-')} | {option.get('fit', '-')} | {option.get('strategy', '-')} | {option.get('tradeoff', '-')} |"
                )
        else:
            lines.append("| 稳健商业方案 | 企业级交付 | 组件标准化 + 质量门禁 | 前期规范成本更高 |")
            lines.append(
                "| 快速验证方案 | MVP 上线 | 核心路径最小化 + 埋点先行 | 视觉与扩展能力后补 |"
            )
            lines.append(
                "| 品牌差异化方案 | 竞争市场 | 品牌 token + 叙事页面 + 转化实验 | 设计与内容投入更高 |"
            )
        return "\n".join(lines)

    def _generate_decision_ledger(self) -> str:
        return (
            "| 决策主题 | 选择结论 | 核心证据 | 放弃项 | 后续验证 |\n"
            "|:---|:---|:---|:---|:---|\n"
            "| 研究策略 | 证据分层（official/industry/community） | 联网来源可信度统计 | 无证据直接结论 | 在每次迭代复核证据比例 |\n"
            f"| 交付范围 | 围绕“{self.description}”优先主任务路径 | 需求澄清问题与用户分层矩阵 | 全量功能一次性上线 | 通过 MVP 指标验证范围是否过宽 |\n"
            "| 设计策略 | 先信息架构与组件状态矩阵，再视觉抛光 | UI/UX 质量门禁章节 | 先做视觉特效 | 通过 UI Review 与转化数据复盘 |\n"
            "| 工程策略 | 前端先行并保留可演示任务流 | 执行路线图与前端蓝图 | 只交静态壳子 | 通过运行验证和质量门禁确认 |"
        )

    def _generate_user_to_pro_protocol(self) -> str:
        return (
            "| 阶段 | 用户输入 | Agent 专业动作 | 产出结果 |\n"
            "|:---|:---|:---|:---|\n"
            "| 需求表达 | 一句话描述目标 | 顺位思考 + 联网研究 + 竞品拆解 | 研究报告与问题澄清清单 |\n"
            "| 方案定义 | 无技术细节也可继续 | 自动生成 PRD/UIUX/架构并给出方案取舍 | 三文档与决策账本 |\n"
            "| 实现执行 | 用户无需指定技术实现 | 按技术栈规范生成代码、测试、验证链路 | 可运行版本与验证证据 |\n"
            "| 交付上线 | 用户仅确认业务目标 | 质量门禁、演练、回滚、证据包自动化 | 可审计交付与上线准备 |\n"
            "\n"
            "- **核心原则**: 同一套交互对所有用户生效，用户负责业务目标，Agent 负责专业流程与交付闭环。"
        )

    def _generate_clarification_questions(self) -> str:
        mode = self._request_mode()
        if mode == "bugfix":
            return (
                "先引用已有缺陷记录和预期行为，只澄清阻碍本次修复的未决项，不重复询问已知事实。\n\n"
                "1. **实际症状**：当前报错、异常现象或错误行为是什么？\n"
                "2. **复现条件**：在哪个页面、接口、角色或环境下可以稳定复现？\n"
                "3. **期望行为**：修复后应该恢复成什么结果，是否有历史正确行为可对照？\n"
                "4. **影响范围**：受影响的是单一路径还是多个模块，是否涉及数据修复或兼容性问题？\n"
                "5. **回归风险**：这次修复最需要补哪类验证，避免把别的链路一起带坏？\n\n"
                "每个发现引用原缺陷或需求位置，说明影响；获授权后定向更新原文与验收，"
                "保持编号和无关内容，再回读核对已解决项与待实现差异。"
            )
        return (
            "以下是审查维度，不是必须逐题回答的问卷。先读现有资料，只保留影响本轮实现的未决项；"
            "已回答的内容直接引用，关键歧义解决后结束追问。\n\n"
            "1. **核心用户**：第一批真正会使用这个产品的人是谁？\n"
            "2. **主任务路径**：用户进入后最重要的一条路径是什么，需要几步完成？\n"
            "3. **范围边界**：MVP 必须交付什么，哪些能力明确不进入第一阶段？\n"
            "4. **依赖约束**：是否依赖现有系统、第三方服务、数据源、权限体系或组织流程？\n"
            "5. **成功标准**：用什么可观察结果验收本轮目标，包括异常和越权情况？\n"
            "6. **业务含义**：关键用词是否与现有词表、架构和代码一致？用具体场景解释冲突，勿机械改名。\n\n"
            "审查闭环：按原需求编号或章节对照本轮验收及已存在的设计/任务；每个发现注明"
            "来源、影响和建议。收到决定并获修改授权后定向写回，保留编号和无关内容，"
            "再逐项复核矛盾与引用。可选优化不冒充阻断；尚未进入 Spec 时不提前创建任务。"
        )

    def _generate_user_segment_matrix(self) -> str:
        return (
            "| 用户分层 | 主要目标 | 关键诉求 | 设计重点 |\n"
            "|:---|:---|:---|:---|\n"
            "| 核心操作者 | 高效完成主流程 | 速度、稳定性、可追踪 | 缩短操作路径、强化状态反馈 |\n"
            "| 协作/审批角色 | 快速理解上下文并做决策 | 信息完整、风险可见 | 强化摘要、差异对比、审批反馈 |\n"
            "| 管理角色 | 掌握全局进度与质量 | 透明度、可审计性 | 仪表盘、过滤、导出、审计记录 |\n"
            "| 新用户/访客 | 理解产品价值与使用方式 | 上手门槛低、信任感强 | 首屏表达清晰、引导明确、案例可信 |"
        )

    def _generate_scope_priorities(self) -> str:
        return (
            "1. **P0 必做**: 主业务流程、关键页面、权限与状态闭环、错误处理、基础审计与测试。\n"
            "2. **P1 应做**: 搜索筛选、批量操作、运营/管理视图、埋点、性能优化、可观测性。\n"
            "3. **P2 可延后**: 高级自动化、复杂可视化、生态集成、个性化配置。\n"
            "4. **明确不在 MVP**: 任何没有用户价值验证、没有交付必要性的炫技功能不进入第一阶段。"
        )

    def _generate_edge_cases(self) -> str:
        return (
            "- 权限不足时必须提供可读解释与引导动作，而不是静默失败。\n"
            "- 异步任务、长流程、批量操作必须可见进度、可取消、可重试。\n"
            "- 网络异常、数据为空、外部依赖不可用时，页面需保留结构稳定和恢复路径。\n"
            "- 表单提交、发布、删除、审批等高风险动作必须有二次确认、撤回或审计记录。"
        )

    def _generate_delivery_requirements(self) -> str:
        if str(self.frontend or "").strip().lower() == "none":
            return (
                "- 按当前交付形态验证安装/启动、主要输入输出及适用的失败恢复路径。\n"
                "- 需求、设计与实际验证相互对应；文档或测试计划不等于已运行的证据。\n"
                "- 无前端时不强制页面演示；部署和运维检查按实际范围适用，原质量与确认门保持不变。"
            )
        return (
            "- 所有核心页面必须覆盖正常态、加载态、空态、错误态、禁用态和权限态。\n"
            "- 交付包必须可审计，文档、Spec、任务状态、测试结果与发布配置需要相互对应。\n"
            "- 前端先行，但不能只做静态壳子，至少要能演示真实任务流和关键反馈。\n"
            "- UI 必须达到商业产品完成度：有品牌感、信息层级、组件一致性和可访问性。\n"
            "- 各项结论引用当前范围的实际证据，未知或尚未执行的验证明确保留，不能因报告生成而判通过。"
        )

    def _generate_acceptance_matrix(self) -> str:
        lines = [
            "按已确认范围选择适用维度；下表是验收要求，不是已通过记录。",
            "| 验收维度 | 必达标准 | 验证方式 |",
            "|:---|:---|:---|",
            "| 核心业务流程 | 主路径与关键失败行为符合需求 | 适用的业务测试与运行检查 |",
            "| 权限与审计 | 涉及权限时验证归属、拒绝及审计 | 用例测试与相关日志 |",
        ]
        if str(self.frontend or "").strip().lower() != "none":
            lines.append(
                "| UI/UX 完成度 | 页面层级、状态、品牌与可访问性符合设计 | 设计与运行走查 |"
            )
        lines.extend(
            [
                "| 工程质量 | 项目既有 Lint/Test/Build 要求满足 | CI 或本地原始证据 |",
                "| 交付准备 | 安装、部署或恢复符合实际交付范围 | 适用的交付检查 |",
                "",
                "沿用原需求编号逐项补充追溯，不虚构编号、任务或测试结果。未进入相应阶段的项记为待设计/待验证。",
                "| 需求/缺陷/不变量 | 验收场景 | 已有设计或接口 | 计划/实际验证与环境 | 结果与证据位置 |",
                "|:---|:---|:---|:---|:---|",
            ]
        )
        return "\n".join(lines)

    def _generate_business_kpis(self) -> str:
        return (
            "- **激活指标**: 首次完成核心流程的用户占比。\n"
            "- **效率指标**: 用户完成关键任务所需时间、步骤数与中断率。\n"
            "- **质量指标**: 错误率、异常恢复率、关键页面交互成功率。\n"
            "- **经营指标**: 试用到付费、线索到转化、复购或活跃留存。"
        )

    def _generate_launch_dependencies(self) -> str:
        return (
            "- 研究报告、PRD、架构、UIUX 与 tasks.md 版本一致。\n"
            "- 测试、质量门禁、发布配置、监控告警和回滚策略已验证。\n"
            "- 数据结构与迁移脚本已评审，关键风险有兜底方案。\n"
            "- 核心路径可现场演示，不依赖口头解释才能成立。"
        )

    def _generate_architecture_fit(self) -> str:
        return (
            "- 架构设计必须回到研究报告和 PRD 的关键流程，不能脱离实际需求做空泛微服务模板。\n"
            "- 技术选型应优先服务于当前阶段交付速度、稳定性、可维护性和团队认知成本。\n"
            "- 对高频路径优先做低延迟设计，对高风险路径优先做权限、审计、幂等和回滚设计。\n"
            "- 前后端契约应围绕页面与任务流定义，而不是围绕数据库表结构反推。"
        )

    def _generate_architecture_decision_matrix(self) -> str:
        return (
            "| 决策维度 | 主方案 | 备选方案 | 选型依据 |\n"
            "|:---|:---|:---|:---|\n"
            "| 服务形态 | 模块化单体 / 分层服务 | 早期微服务 | 优先交付速度与可维护性，避免过度拆分 |\n"
            f"| 前端生态 | {self._get_ui_library()} + Token 系统 | 纯组件库默认样式 | 必须满足商业级品牌表达与一致性 |\n"
            "| 数据策略 | 主库 + 缓存 + 搜索 | 单库直连 | 兼顾读写性能、查询能力与扩展空间 |\n"
            "| 可观测性 | 指标 + 日志 + 链路追踪 | 仅日志 | 发布演练和问题定位需要完整证据链 |\n"
            "| 发布策略 | 灰度/回滚预案 | 一次性全量发布 | 降低高风险变更对线上影响 |\n"
            "\n"
            "- 任何架构决策若无法映射到研究证据、业务目标和交付约束，则不应进入首版实现。"
        )

    def _generate_architecture_ledger(self) -> str:
        return (
            "| 架构决策 | 结论 | 备选方案 | 风险预算与补偿 |\n"
            "|:---|:---|:---|:---|\n"
            "| 服务边界 | 以业务域拆分并保持契约稳定 | 单体全集成 | 用 DTO + 版本策略降低耦合风险 |\n"
            "| 数据一致性 | 核心写路径幂等 + 审计 | 仅依赖数据库约束 | 失败补偿与手工修复入口 |\n"
            "| 发布策略 | 灰度 + 回滚预案 | 一次性全量 | 发布前演练与证据包校验 |\n"
            "| 可观测性 | 指标/日志/追踪一体 | 仅日志 | 高风险路径强制埋点与告警阈值 |\n"
        )

    def _generate_agent_delivery_pipeline(self) -> str:
        return (
            "1. **Intent Intake**: 接收用户自然语言目标并抽取业务意图与边界。\n"
            "2. **Research Engine**: 联网研究 + 本地知识命中 + 竞品能力矩阵。\n"
            "3. **Tri-Doc Compiler**: 自动生成 PRD、UIUX、架构并建立决策账本。\n"
            "4. **Stack Router**: 按 Web/H5/小程序/APP 路由到对应组件生态（含 TDesign 小程序）。\n"
            "5. **Execution & Verification**: 生成实现方案、测试方案与质量门禁结果。\n"
            "6. **Delivery Proof**: 输出可审计交付包、发布演练与回滚策略。"
        )

    def _generate_sequence_diagram(self) -> str:
        mode = self._request_mode()
        if mode == "bugfix":
            return (
                "```mermaid\n"
                "sequenceDiagram\n"
                '    participant U as "User"\n'
                '    participant H as "Host AI"\n'
                '    participant R as "Research & Docs"\n'
                '    participant C as "Code / Tests"\n'
                "    U->>H: 提交缺陷修复需求\n"
                "    H->>R: 先复现问题并更新补丁文档\n"
                "    R-->>U: 输出轻量 PRD / Architecture / UIUX 补丁说明\n"
                "    U->>H: 确认修复边界\n"
                "    H->>C: 实施定点修复与回归测试\n"
                "    C-->>U: 返回修复结果、验证证据与剩余风险\n"
                "```\n"
            )
        return (
            "```mermaid\n"
            "sequenceDiagram\n"
            '    participant U as "User"\n'
            '    participant F as "Frontend"\n'
            '    participant A as "API Gateway"\n'
            '    participant S as "Service"\n'
            '    participant D as "Database"\n'
            "    U->>F: 发起核心业务操作\n"
            "    F->>A: 提交请求与上下文\n"
            "    A->>S: 路由、鉴权、校验\n"
            "    S->>D: 读取 / 写入业务数据\n"
            "    D-->>S: 返回结果\n"
            "    S-->>A: 产出稳定 DTO 与状态\n"
            "    A-->>F: 返回业务结果\n"
            "    F-->>U: 展示反馈、下一步动作与状态变化\n"
            "```\n"
        )

    def _generate_domain_boundaries(self) -> str:
        return (
            "- 认证授权、用户与组织、核心业务流程、通知与异步任务、审计日志应作为明确边界拆分。\n"
            "- 每个边界需要定义输入输出 DTO、权限要求、状态流转与失败补偿策略。\n"
            "- 共享能力只沉淀稳定基础设施，不把业务细节塞进“common utils”。\n"
            "- 高变化模块优先与低变化模块解耦，降低后续迭代成本。"
        )

    def _generate_integration_contracts(self) -> str:
        return (
            "- API 必须有版本策略，避免前端页面被无意破坏。\n"
            "- 外部依赖需定义超时、重试、降级、熔断与错误映射规则。\n"
            "- DTO 应稳定、可验证、可测试，避免把数据库内部字段直接暴露给前端。\n"
            "- Webhook、消息、回调类接口要有幂等键与审计记录。"
        )

    def _generate_failure_strategy(self) -> str:
        return (
            "- 关键写操作采用幂等机制，防止重复提交。\n"
            "- 第三方依赖异常时优先降级核心功能而不是整体瘫痪。\n"
            "- 任务流中断后应支持恢复、补偿或人工处理入口。\n"
            "- 前端异常要给出可执行的下一步，不允许只显示技术报错。"
        )

    def _generate_audit_strategy(self) -> str:
        return (
            "- 对登录、权限变更、关键数据修改、批量操作、发布/审批动作保留审计轨迹。\n"
            "- 日志结构需支持按用户、资源、请求链路、时间窗口检索。\n"
            "- 前后端共享 trace/request id，确保问题能跨层定位。\n"
            "- 质量门禁输出应沉淀为可回溯产物，而不是一次性终端信息。"
        )

    def _generate_release_strategy(self) -> str:
        return (
            "- 使用分环境发布策略，至少区分本地、测试、预发布、生产。\n"
            "- 高风险变更建议灰度、特性开关或分批发布。\n"
            "- 发布说明需包含数据库变更、兼容性影响、回滚步骤与监控关注项。\n"
            "- 回滚方案必须在上线前验证，不接受“出问题再看”。"
        )

    def _generate_ui_strategy(self, profile: dict | None = None) -> str:
        profile = profile or self._get_ui_intelligence()
        return (
            "- UI 的首要目标不是“好看”，而是让用户快速理解产品价值、任务状态与下一步动作。\n"
            "- 所有页面都应体现商业级完成度：品牌感、层级感、信息密度、状态完整度与信任表达。\n"
            f"- 当前项目应以“{profile.get('surface', 'Web')}”为第一交付目标，并采用 {profile.get('information_density', '中等')} 密度策略组织信息。\n"
            "- 先解决页面结构、CTA、数据层级和组件一致性，再打磨视觉细节。\n"
            "- 对外页面强调品牌、信任与转化，对内页面强调效率、清晰度和低认知负担。"
        )

    def _generate_visual_direction(self) -> str:
        return (
            "- 视觉方向应基于产品定位建立明确气质：可信、克制、现代，而不是依赖泛滥渐变制造“高级感”。\n"
            "- 优先使用有辨识度的字体组合、清晰的字号节奏、稳定的留白和克制的强调色。\n"
            "- 图形、图标、插画、卡片阴影和分隔线应来自同一视觉系统，避免拼装感。\n"
            "- 页面应在首屏就体现主价值、核心证据、下一步 CTA 和品牌记忆点。"
        )

    def _generate_layout_system(self, profile: dict | None = None) -> str:
        profile = profile or self._get_ui_intelligence()
        return (
            "- 桌面端使用明确的 12 栏或等价栅格系统，控制内容宽度与节奏。\n"
            f"- 当前项目采用 {profile.get('information_density', '中等')} 信息密度，按页面目标决定视觉节奏与操作密度。\n"
            "- 控制不同页面的密度等级，避免同一产品里既过空又过挤。\n"
            "- 侧边栏、头部、主体区、辅助区、底部应有稳定布局规则。"
        )

    def _generate_component_state_matrix(self) -> str:
        return (
            "| 组件类型 | 必备状态 | 说明 |\n"
            "|:---|:---|:---|\n"
            "| 按钮 | 默认 / hover / active / disabled / loading | 强调动作反馈与禁用原因 |\n"
            "| 输入控件 | 默认 / focus / error / success / readonly | 错误文案与引导动作要清晰 |\n"
            "| 列表与表格 | loading / empty / normal / error / bulk-selected | 支持筛选、排序、批量动作 |\n"
            "| 卡片与模块 | default / hover / selected / warning / permission-limited | 用于强调优先级、状态变化和权限边界 |\n"
            "| 弹窗抽屉 | enter / exit / confirm / pending / failure | 需要防误操作和恢复路径 |"
        )

    def _generate_motion_system(self, profile: dict | None = None) -> str:
        profile = profile or self._get_ui_intelligence()
        return (
            "- 动效只服务于层级切换、状态反馈、焦点引导，不用作廉价装饰。\n"
            f"- 推荐实现基线: {profile.get('component_stack', {}).get('motion', 'framer-motion')}。\n"
            "- 列表进入、面板展开、Toast 反馈、模态切换应采用统一时长与缓动曲线。\n"
            "- 对关键提交动作提供即时反馈，对长操作提供进度提示。\n"
            "- 必须兼容 reduced-motion，必要时降级为无动画但保留状态反馈。"
        )

    def _generate_trust_and_conversion_rules(self, profile: dict | None = None) -> str:
        profile = profile or self._get_ui_intelligence()
        lines = [
            "- 对外页面应优先展示价值主张、能力边界、案例证明、客户证言、数据指标或合规信息。",
            "- CTA 不应只在 hero 区出现，关键转化节点要有连续但不过度打扰的引导。",
            "- 对内工作台则应突出当前任务、风险提示、审批状态、待办优先级和最近操作。",
            "- 所有高价值页面都应体现“用户为什么相信并继续使用这个产品”。",
            "",
            "**当前项目必须优先出现的信任/转化模块**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("trust_modules", [])[:8])
        return "\n".join(lines)
