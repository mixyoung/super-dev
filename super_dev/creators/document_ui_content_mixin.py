"""UI and experience-content generators."""

from __future__ import annotations

import logging


class DocumentUIContentMixin:
    def _generate_navigation_structure(self) -> str:
        """生成导航结构"""
        return """
### 导航结构

**主导航**:
- 首页
- 功能模块
- 设置
- 帮助

**用户菜单**:
- 个人资料
- 账户安全
- 通知设置
- 退出登录

**面包屑**:
- 显示当前页面路径
- 支持快速返回上级
"""

    def _generate_login_page_design(self) -> str:
        """生成登录页设计"""
        return """
### 登录/注册页

**布局**:
- 居中卡片式设计
- 左侧品牌展示
- 右侧表单区域

**表单元素**:
- 邮箱输入框 (带验证)
- 密码输入框 (带显示/隐藏)
- 记住我复选框
- 忘记密码链接
- 登录按钮 (主操作)
- 注册链接 (次要操作)

**交互**:
- 输入框实时验证
- 登录按钮 Loading 状态
- 错误提示显示在表单顶部
"""

    def _generate_list_page_design(self) -> str:
        """生成列表页设计"""
        return """
### 列表页

**布局**:
- 顶部搜索栏
- 左侧筛选器
- 右侧数据列表
- 底部分页器

**列表项**:
- 卡片式展示
- 显示关键信息
- 操作按钮组
- 状态标签

**交互**:
- 下拉加载更多
- 搜索防抖 (300ms)
- 筛选实时更新
"""

    def _generate_detail_page_design(self) -> str:
        """生成详情页设计"""
        return """
### 详情页

**布局**:
- 顶部导航栏 (返回 + 操作)
- 主要信息区
- 相关信息区
- 操作区

**信息层级**:
- 标题 (H1)
- 摘要
- 详细内容
- 元数据

**交互**:
- 编辑/删除操作
- 相关内容推荐
- 快速导航
"""

    def _generate_form_page_design(self) -> str:
        """生成表单页设计"""
        return """
### 表单页

**布局**:
- 左侧表单
- 右侧预览 (可选)
- 底部操作按钮

**表单元素**:
- 必填项标记 (*)
- 字段提示信息
- 实时验证反馈
- 保存/取消按钮

**交互**:
- 表单验证
- 草稿自动保存
- 提交 Loading 状态
"""

    def _generate_base_components(self) -> str:
        """生成基础组件"""
        return """
### 基础组件库

**按钮 (Button)**:
- 主要按钮
- 次要按钮
- 危险按钮
- 文本按钮

**输入框 (Input)**:
- 文本输入
- 密码输入
- 数字输入
- 日期选择

**数据展示 (Data Display)**:
- 表格
- 卡片
- 列表
- 标签

**反馈 (Feedback)**:
- 消息提示
- 对话框
- 加载状态
- 空状态
"""

    def _generate_business_components(self) -> str:
        """生成业务组件"""
        return """
### 业务组件

**用户相关**:
- 用户头像
- 用户卡片
- 用户选择器

**认证相关**:
- 登录表单
- 注册表单
- 密码修改

**内容相关**:
- 内容卡片
- 内容列表
- 内容编辑器
"""

    def _generate_user_journeys_ui(self) -> str:
        """生成用户旅程 UI"""
        return """
### 用户旅程 UI 设计

**旅程 1: 新用户注册**

关键页面:
1. 访问首页 → CTA 按钮 "开始使用"
2. 注册页 → 简洁表单
3. 邮箱验证页 → 清晰提示
4. 登录页 → 自动跳转
5. 首次登录引导 → 功能介绍

**旅程 2: 日常使用**

关键页面:
1. 登录页 → 快速登录
2. 首页 → 功能概览
3. 功能页 → 核心操作
4. 设置页 → 个人配置

**交互要点**:
- 操作反馈及时
- 错误提示清晰
- 加载状态明确
"""

    def _render_ui_intelligence_summary(self, profile: dict) -> str:
        lib = profile.get("primary_library", {})
        stack = profile.get("component_stack", {})
        typography = profile.get("typography_preset", {})
        palette = profile.get("color_palette", {})
        lines = [
            f"- **界面定位**: {profile.get('surface', 'N/A')}",
            f"- **信息密度**: {profile.get('information_density', 'N/A')}",
            f"- **行业语气**: {profile.get('industry_tone', 'N/A')}",
            f"- **主视觉气质**: {profile.get('style_direction', {}).get('direction', 'N/A')}",
            f"- **视觉哲学主方向**: {profile.get('design_direction_manifest', {}).get('selected_direction', 'N/A')}",
            f"- **品牌信号**: {' / '.join((profile.get('brand_signal_manifest') or {}).get('tone_descriptors', [])[:3]) or 'N/A'}",
            f"- **字体组合**: {typography.get('heading', 'N/A')} / {typography.get('body', 'N/A')}",
            f"- **配色逻辑**: {palette.get('name', 'N/A')}（主色 {palette.get('primary', 'N/A')} / 强调色 {palette.get('accent', 'N/A')}）",
            f"- **图标系统**: {stack.get('icons', 'N/A')}",
            f"- **首选组件生态**: {lib.get('name', 'N/A')}",
            f"- **表单基线**: {stack.get('form', 'N/A')}",
            f"- **数据展示基线**: {stack.get('table', 'N/A')} / {stack.get('chart', 'N/A')}",
            "",
            "**优先原则**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("benchmark_principles", []))
        lines.extend(["", "**明确不建议默认采用**:"])
        lines.extend(f"- {item}" for item in profile.get("banned_patterns", [])[:5])
        lines.extend(["", "**设计知识库关键词**:"])
        lines.append("- " + " / ".join(profile.get("knowledge_keywords", [])))
        candidates = profile.get("art_direction_candidates", [])
        if candidates:
            lines.extend(["", "**视觉方向候选**:"])
            for item in candidates[:3]:
                if not isinstance(item, dict):
                    continue
                lines.append(f"- **{item.get('name', 'N/A')}**: {item.get('philosophy', 'N/A')}")
        proof_rules = profile.get("proof_composition_rules", {})
        if isinstance(proof_rules, dict) and proof_rules:
            lines.extend(["", "**证明构图纪律**:"])
            lines.append(
                f"- Hero 证明栈: {' / '.join(proof_rules.get('hero_proof_stack', [])[:4]) or 'N/A'}"
            )
            lines.append(
                f"- 信任顺序: {' / '.join(proof_rules.get('trust_sequence', [])[:4]) or 'N/A'}"
            )
        return "\n".join(lines)

    def _render_ui_decision_manifest(self, profile: dict, design_bundle: dict | None = None) -> str:
        typography = profile.get("typography_preset", {})
        palette = profile.get("color_palette", {})
        style_direction = profile.get("style_direction", {})
        primary = profile.get("primary_library", {})
        lines = [
            "#### UI 系统冻结决策",
            "",
            "**主方案（默认实现方向）**:",
            f"- **主视觉气质**: {style_direction.get('direction', 'N/A')}",
            f"- **材质/版式逻辑**: {style_direction.get('materials', 'N/A')}",
            f"- **字体组合**: {typography.get('heading', 'N/A')} / {typography.get('body', 'N/A')}",
            f"- **配色逻辑**: {palette.get('name', 'N/A')}（主色 {palette.get('primary', 'N/A')} / 强调色 {palette.get('accent', 'N/A')} / 背景 {palette.get('background', 'N/A')}）",
            f"- **图标系统**: {profile.get('component_stack', {}).get('icons', 'N/A')}",
            f"- **首选组件生态**: {primary.get('name', 'N/A')}",
            f"- **跨平台框架 Playbook**: {(profile.get('framework_playbook') or {}).get('framework', '通用 Web / 原生约束')}",
            f"- **页面定位与密度**: {profile.get('surface', 'N/A')} / {profile.get('information_density', 'N/A')}",
            f"- **叙事方式**: {profile.get('design_direction_manifest', {}).get('narrative_mode', 'N/A')}",
            f"- **视觉张力**: {profile.get('design_direction_manifest', {}).get('visual_tension', 'N/A')}",
            f"- **证明策略**: {profile.get('design_direction_manifest', {}).get('proof_strategy', 'N/A')}",
            "",
            "**设计 token 优先级**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("design_system_priorities", [])[:6])
        lines.extend(["", "**状态矩阵要求**:"])
        lines.extend(f"- {item}" for item in profile.get("state_requirements", [])[:8])

        alternatives = profile.get("alternative_libraries", [])
        if alternatives:
            lines.extend(["", "**备选实现路径**:"])
            for item in alternatives[:3]:
                if not isinstance(item, dict):
                    continue
                lines.append(f"- **{item.get('name', 'N/A')}**: {item.get('rationale', 'N/A')}")
        references = profile.get("design_references", [])
        _selected_reference_value = profile.get("selected_design_reference")
        selected_reference = (
            _selected_reference_value if isinstance(_selected_reference_value, dict) else {}
        )
        selected_slug = str(selected_reference.get("slug", "")).strip()
        if references:
            lines.extend(["", "**设计参考锚点**:"])
            for item in references[:3]:
                if not isinstance(item, dict):
                    continue
                signals = " / ".join(item.get("signals", [])[:3])
                cautions = "；".join(item.get("cautions", [])[:2])
                selected_tag = (
                    "（已选灵感）" if selected_slug and item.get("slug") == selected_slug else ""
                )
                lines.append(
                    f"- **{item.get('name', 'N/A')}{selected_tag}**: {item.get('rationale', 'N/A')} 参考信号：{signals or 'N/A'}。避免：{cautions or 'N/A'}"
                )

        art_direction_candidates = profile.get("art_direction_candidates", [])
        if art_direction_candidates:
            lines.extend(["", "**视觉方向候选（主方案 + 备选方案）**:"])
            for item in art_direction_candidates[:3]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- **{item.get('name', 'N/A')}**: {item.get('philosophy', 'N/A')} | Hero: {item.get('hero_treatment', 'N/A')} | 避免：{'；'.join(item.get('anti_cliches', [])[:2]) or 'N/A'}"
                )

        _brand_signal_manifest_value = profile.get("brand_signal_manifest")
        brand_signal_manifest = (
            _brand_signal_manifest_value if isinstance(_brand_signal_manifest_value, dict) else {}
        )
        if brand_signal_manifest:
            lines.extend(["", "**品牌信号与权威感**:"])
            lines.extend(
                f"- {item}" for item in brand_signal_manifest.get("tone_descriptors", [])[:4]
            )
            lines.extend(
                f"- {item}" for item in brand_signal_manifest.get("credibility_devices", [])[:3]
            )

        _proof_composition_rules_value = profile.get("proof_composition_rules")
        proof_composition_rules = (
            _proof_composition_rules_value
            if isinstance(_proof_composition_rules_value, dict)
            else {}
        )
        if proof_composition_rules:
            lines.extend(["", "**证明构图规则**:"])
            lines.append(
                f"- **Hero 证明栈**: {' / '.join(proof_composition_rules.get('hero_proof_stack', [])[:4]) or 'N/A'}"
            )
            lines.append(
                f"- **信任顺序**: {' / '.join(proof_composition_rules.get('trust_sequence', [])[:4]) or 'N/A'}"
            )
            lines.extend(
                f"- {item}" for item in proof_composition_rules.get("evidence_priority", [])[:3]
            )
            lines.append(
                f"- **密度规则**: {proof_composition_rules.get('proof_density_rule', 'N/A')}"
            )

        component_craft_requirements = profile.get("component_craft_requirements", [])
        if component_craft_requirements:
            lines.extend(["", "**组件工艺要求**:"])
            lines.extend(f"- {item}" for item in component_craft_requirements[:5])

        layout_tension_rules = profile.get("layout_tension_rules", [])
        if layout_tension_rules:
            lines.extend(["", "**布局张力纪律**:"])
            lines.extend(f"- {item}" for item in layout_tension_rules[:4])

        _anti_guardrails_value = profile.get("anti_ai_slop_guardrails")
        anti_guardrails = _anti_guardrails_value if isinstance(_anti_guardrails_value, dict) else {}
        if anti_guardrails:
            lines.extend(["", "**反 AI 味护栏**:"])
            lines.extend(f"- {item}" for item in anti_guardrails.get("forbidden_motifs", [])[:4])
            lines.extend(["", "**原创度与工艺检查**:"])
            lines.extend(f"- {item}" for item in anti_guardrails.get("originality_checks", [])[:3])
            lines.extend(f"- {item}" for item in anti_guardrails.get("craft_checks", [])[:3])

        critique_rubric = profile.get("critique_rubric", [])
        if critique_rubric:
            lines.extend(["", "**设计批评标尺**:"])
            for item in critique_rubric[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- **{item.get('label', 'N/A')}**（阈值 {item.get('pass_threshold', 'N/A')}/10）: {item.get('focus', 'N/A')}"
                )

        lines.extend(["", "**明确不默认采用**:"])
        lines.extend(f"- {item}" for item in profile.get("banned_patterns", [])[:6])
        lines.extend(
            [
                "",
                "**视觉方案输出要求**:",
                "- 每个关键页面至少提供 2 个视觉方向候选（主方案 + 备选方案），并记录为什么不用另一种方向。",
                "- 开始编码前先冻结图标库、token 策略和页面骨架，不允许边写边猜。",
                "- 主方案必须明确引用 2-3 个设计参考锚点，说明吸收哪些信号、舍弃哪些套路。",
                "- 绝对不允许 emoji 表情作为图标，也不允许在开发过程中用 emoji 充当临时占位；从文档冻结到最终交付都必须使用正式图标库。",
            ]
        )

        design_system = (design_bundle or {}).get("design_system")
        if design_system and getattr(design_system, "aesthetic", None):
            lines.extend(
                [
                    "",
                    "**内置设计系统差异化结论**:",
                    f"- **美学方向**: {design_system.aesthetic.name}",
                    f"- **差异化特征**: {design_system.aesthetic.differentiation}",
                    f"- **Display 字体**: {design_system.aesthetic.typography.display}",
                    f"- **Body 字体**: {design_system.aesthetic.typography.body}",
                ]
            )
        return "\n".join(lines)

    def _render_screen_recipe_manifest(self, analysis: dict, profile: dict) -> str:
        recipes = self._build_screen_recipes(analysis=analysis, profile=profile)
        lines = [
            "#### Screen Recipes（页面配方冻结）",
            "",
            "在进入 UI 实现前，必须先冻结每个关键页面的目标、section order、信任模块和状态覆盖，避免页面退化成泛化模板。",
            "",
        ]
        for index, recipe in enumerate(recipes, 1):
            lines.extend(
                [
                    f"**{index}. {recipe.get('label', 'N/A')}**",
                    f"- **目标**: {recipe.get('objective', 'N/A')}",
                    f"- **视觉方向**: {recipe.get('art_direction', 'N/A')}",
                    f"- **叙事方式**: {recipe.get('narrative_mode', 'N/A')}",
                    f"- **视觉张力**: {recipe.get('visual_tension', 'N/A')}",
                    f"- **证明构图**: {' / '.join(recipe.get('proof_composition', [])) or 'N/A'}",
                    f"- **结构顺序**: {' / '.join(recipe.get('section_order', [])) or 'N/A'}",
                    f"- **组件重点**: {' / '.join(recipe.get('component_focus', [])) or 'N/A'}",
                    f"- **信任模块**: {' / '.join(recipe.get('trust_modules', [])) or 'N/A'}",
                    f"- **状态要求**: {' / '.join(recipe.get('required_states', [])) or 'N/A'}",
                    f"- **变体轴**: {' / '.join(recipe.get('variation_axes', [])) or 'N/A'}",
                    f"- **布局张力纪律**: {' / '.join(recipe.get('layout_tension_rules', [])) or 'N/A'}",
                    f"- **反模板禁区**: {' / '.join(recipe.get('anti_cliche_bans', [])) or 'N/A'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _render_design_execution_protocol(self, analysis: dict, profile: dict) -> str:
        recipes = self._build_screen_recipes(analysis=analysis, profile=profile)
        context_protocol = self._build_design_context_protocol(
            analysis=analysis,
            profile=profile,
            screen_recipes=recipes,
        )
        tweak_strategy = self._build_tweak_strategy(
            analysis=analysis,
            profile=profile,
            screen_recipes=recipes,
        )
        verification_handoff = self._build_verification_handoff(
            analysis=analysis,
            profile=profile,
            screen_recipes=recipes,
        )
        _anti_guardrails_value = profile.get("anti_ai_slop_guardrails")
        anti_guardrails = _anti_guardrails_value if isinstance(_anti_guardrails_value, dict) else {}
        _proof_rules_value = profile.get("proof_composition_rules")
        proof_rules = _proof_rules_value if isinstance(_proof_rules_value, dict) else {}
        _component_craft_requirements_value = profile.get("component_craft_requirements")
        component_craft_requirements = (
            _component_craft_requirements_value
            if isinstance(_component_craft_requirements_value, list)
            else []
        )
        _layout_tension_rules_value = profile.get("layout_tension_rules")
        layout_tension_rules = (
            _layout_tension_rules_value if isinstance(_layout_tension_rules_value, list) else []
        )
        lines = [
            "#### Claude-Design 风格执行协议",
            "",
            f"- **上下文目标**: {context_protocol.get('goal', 'N/A')}",
            "- **输入优先级**:",
        ]
        lines.extend(f"  - {item}" for item in context_protocol.get("preferred_import_order", []))
        lines.extend(
            [
                "- **GitHub / 代码导入重点**:",
            ]
        )
        lines.extend(f"  - {item}" for item in context_protocol.get("github_import_targets", []))
        lines.extend(
            [
                f"- **单一真源规则**: {context_protocol.get('single_source_rule', 'N/A')}",
                f"- **Tweaks 模式**: {tweak_strategy.get('mode', 'N/A')}",
                f"- **Tweaks 默认控件**: {' / '.join(tweak_strategy.get('default_controls', [])) or 'N/A'}",
                f"- **持久化规则**: {tweak_strategy.get('persistence_rule', 'N/A')}",
                "- **验证顺序**:",
            ]
        )
        lines.extend(f"  - {item}" for item in verification_handoff.get("verification_order", []))
        lines.extend(
            [
                "- **交付证据**:",
            ]
        )
        lines.extend(f"  - {item}" for item in verification_handoff.get("required_artifacts", []))
        if anti_guardrails:
            lines.extend(
                [
                    "- **反 AI 味护栏**:",
                ]
            )
            lines.extend(f"  - {item}" for item in anti_guardrails.get("hierarchy_rules", [])[:3])
            lines.extend(f"  - {item}" for item in anti_guardrails.get("forbidden_motifs", [])[:3])
        if proof_rules:
            lines.extend(["- **证明构图纪律**:"])
            lines.extend(f"  - {item}" for item in proof_rules.get("hero_proof_stack", [])[:4])
            lines.extend(f"  - {item}" for item in proof_rules.get("evidence_priority", [])[:3])
        if component_craft_requirements:
            lines.extend(["- **组件工艺要求**:"])
            lines.extend(f"  - {item}" for item in component_craft_requirements[:4])
        if layout_tension_rules:
            lines.extend(["- **布局张力纪律**:"])
            lines.extend(f"  - {item}" for item in layout_tension_rules[:4])
        critique_targets = verification_handoff.get("critique_targets", [])
        if critique_targets:
            lines.extend(["- **设计批评维度**:"])
            lines.extend(f"  - {item}" for item in critique_targets)
        return "\n".join(lines)

    def _render_design_token_freeze_output(
        self, profile: dict, design_bundle: dict | None = None
    ) -> str:
        design_system = (design_bundle or {}).get("design_system")
        if not design_system:
            return (
                "#### Design Token 冻结输出\n\n"
                "- 必须冻结 color / typography / spacing / radius / shadow / motion 六类 token。\n"
                "- 实现前先把 token 落到 CSS variables / Tailwind theme / design tokens 文件，禁止边做边写死样式。\n"
            )

        token_rows = [
            (
                "颜色 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.colors.items())[:5]
                ),
            ),
            (
                "字体 token",
                ", ".join(
                    f"{name}={value}"
                    for name, value in list(design_system.typography.items())
                    if value
                ),
            ),
            (
                "间距 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.spacing.items())[:5]
                ),
            ),
            (
                "圆角 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.radius.items())[:4]
                ),
            ),
            (
                "阴影 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.shadows.items())[:4]
                ),
            ),
            (
                "动效 token",
                ", ".join(
                    f"{name}={value}" for name, value in list(design_system.animations.items())[:3]
                ),
            ),
        ]

        lines = [
            "#### Design Token 冻结输出",
            "",
            "| 类型 | 冻结结果 |",
            "|:---|:---|",
        ]
        for token_type, value in token_rows:
            lines.append(f"| {token_type} | {value or 'N/A'} |")

        css_preview = (design_bundle or {}).get("css_variables_preview", "")
        if css_preview:
            lines.extend(
                [
                    "",
                    "**CSS Variables 预览**:",
                    "```css",
                    css_preview,
                    "```",
                ]
            )
        tailwind_preview = (design_bundle or {}).get("tailwind_preview", "")
        if tailwind_preview:
            lines.extend(
                [
                    "",
                    "**Tailwind Theme 预览**:",
                    "```json",
                    "\n".join(tailwind_preview.splitlines()[:22]),
                    "```",
                ]
            )
        lines.extend(
            [
                "",
                "**落地要求**:",
                "- 所有页面必须引用这套 token，禁止重新发明第二套颜色和字号。",
                f"- 图标系统固定为 {profile.get('component_stack', {}).get('icons', 'N/A')}，不得再混入 emoji 或临时占位。",
            ]
        )
        return "\n".join(lines)

    def _render_component_ecosystem(self, profile: dict) -> str:
        primary = profile.get("primary_library", {})
        lines = [
            f"#### 首选方案: {primary.get('name', 'N/A')}",
            "",
            f"**适用原因**: {primary.get('rationale', 'N/A')}",
            "",
            "**核心能力**:",
        ]
        lines.extend(f"- {item}" for item in primary.get("strengths", []))
        lines.extend(
            [
                "",
                "**实现注意事项**:",
            ]
        )
        lines.extend(f"- {item}" for item in primary.get("notes", []))
        lines.extend(
            [
                "",
                "#### 配套技术基线",
                "",
                f"- **表单与验证**: {profile.get('component_stack', {}).get('form', 'N/A')}",
                f"- **图表能力**: {profile.get('component_stack', {}).get('chart', 'N/A')}",
                f"- **表格/数据工作区**: {profile.get('component_stack', {}).get('table', 'N/A')}",
                f"- **图标体系**: {profile.get('component_stack', {}).get('icons', 'N/A')}",
                f"- **动效能力**: {profile.get('component_stack', {}).get('motion', 'N/A')}",
            ]
        )

        alternatives = profile.get("alternative_libraries", [])
        if alternatives:
            lines.extend(["", "#### 可选备选方案", ""])
            for item in alternatives:
                lines.append(f"- **{item.get('name', 'N/A')}**: {item.get('rationale', 'N/A')}")
        matrix = profile.get("ui_library_matrix", [])
        if matrix:
            lines.extend(
                [
                    "",
                    "#### 多场景组件库矩阵",
                    "",
                    "| 场景 | 推荐组合 | 设计重点 |",
                    "|:---|:---|:---|",
                ]
            )
            for item in matrix:
                lines.append(
                    f"| {item.get('scene', '-')} | {item.get('libraries', '-')} | {item.get('focus', '-')} |"
                )
        return "\n".join(lines)

    def _render_cross_platform_strategy(self, profile: dict) -> str:
        lines = [
            "- **WEB**: 优先构建高信息密度布局、可检索信息架构和可见状态反馈。",
            "- **H5**: 保留品牌视觉，但减少重型动画，保证首屏性能与转化路径。",
            "- **微信小程序**: 优先贴合平台导航与触控习惯，表单/支付路径保持平台一致性。",
            "- **APP**: 使用原生交互范式（底部导航、手势、反馈节奏），品牌 token 作为统一层。",
            "- **桌面端**: 强化窗口布局、快捷键、菜单栏和本地能力（文件/通知/离线）交互一致性。",
            "",
            "**多端一致性约束**:",
            "- 核心任务路径保持一致（注册、购买、查询、提交），文案与状态语义统一。",
            "- 视觉品牌保持一致（字体、色彩、图形语言），但交互尊重平台差异。",
            "- 同一业务模块必须共享组件契约，避免 Web/H5/小程序/APP/桌面端 逻辑漂移。",
        ]
        framework_playbook = profile.get("framework_playbook") or {}
        if framework_playbook:
            lines.extend(
                [
                    "",
                    f"**跨平台框架深优化 Playbook（{framework_playbook.get('framework', '当前框架')}）**:",
                    f"- **优化焦点**: {framework_playbook.get('focus', 'N/A')}",
                    f"- **适配理由**: {framework_playbook.get('rationale', 'N/A')}",
                    "- **必须优先落实**:",
                ]
            )
            lines.extend(
                f"- {item}" for item in framework_playbook.get("implementation_modules", [])[:4]
            )
            lines.extend(["", "**平台差异/限制**:"])
            lines.extend(
                f"- {item}" for item in framework_playbook.get("platform_constraints", [])[:4]
            )
            lines.extend(["", "**执行护栏**:"])
            lines.extend(
                f"- {item}" for item in framework_playbook.get("execution_guardrails", [])[:3]
            )
            anti_patterns = framework_playbook.get("anti_patterns", [])
            if anti_patterns:
                lines.extend(["", "**框架级反模式**:"])
                lines.extend(f"- {item}" for item in anti_patterns[:3])
            native_capabilities = framework_playbook.get("native_capabilities", [])
            if native_capabilities:
                lines.extend(["", "**原生能力面**:"])
                lines.extend(f"- {item}" for item in native_capabilities[:4])
            validation_surfaces = framework_playbook.get("validation_surfaces", [])
            if validation_surfaces:
                lines.extend(["", "**必须验收的真实场景**:"])
                lines.extend(f"- {item}" for item in validation_surfaces[:4])
            delivery_evidence = framework_playbook.get("delivery_evidence", [])
            if delivery_evidence:
                lines.extend(["", "**交付证据要求**:"])
                lines.extend(f"- {item}" for item in delivery_evidence[:4])
        keywords = profile.get("knowledge_keywords", [])
        if keywords:
            lines.extend(["", "**设计检索关键词建议**:", "- " + " / ".join(keywords[:10])])
        return "\n".join(lines)

    def _render_ui_quality_gate(self, profile: dict) -> str:
        checks = profile.get("quality_checklist", [])
        if not checks:
            checks = [
                "必须输出 token 并覆盖核心组件",
                "必须覆盖关键状态矩阵",
                "必须通过可访问性与性能审查",
            ]
        lines = ["- [ ] " + check for check in checks]
        lines.extend(
            [
                "",
                "**验收阈值建议**:",
                "- 视觉一致性评分 ≥ 85/100",
                "- 无障碍基础项（对比度/焦点/键盘）通过率 100%",
                "- 首屏可交互时间满足业务基线（Web < 2.5s，H5 < 3s）",
            ]
        )
        critique_rubric = profile.get("critique_rubric", [])
        if critique_rubric:
            lines.extend(["", "**五维设计批评阈值**:"])
            for item in critique_rubric[:5]:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"- {item.get('label', 'N/A')} ≥ {item.get('pass_threshold', 'N/A')}/10：{item.get('focus', 'N/A')}"
                )
        return "\n".join(lines)

    def _render_ui_execution_workflow(self, profile: dict) -> str:
        primary = profile.get("primary_library", {}).get("name", "UI 组件生态")
        alternatives = profile.get("alternative_libraries", [])
        alternative_names = " / ".join(
            item.get("name", "") for item in alternatives[:3] if isinstance(item, dict)
        )
        return (
            "1. **Intent → 目标建模**: 先明确业务目标、目标用户、转化动作、信任模块，禁止直接生成页面。\n"
            "2. **System → 设计系统编译**: 先冻结 token（颜色/字体/间距/圆角/阴影/动效）和页面骨架。\n"
            f"3. **Build → 组件实现**: 默认采用 `{primary}`，根据场景可选 `{alternative_names or '替代生态'}`。\n"
            "4. **Polish → 商业抛光**: 逐页补齐状态矩阵、文案层级、信任模块、可访问性与性能预算。\n"
            "5. **Proof → 证据沉淀**: 输出截图、关键交互说明、运行验证结果，确保宿主可复现而非一次性生成。\n"
            "\n"
            "**强制要求**: 每个页面至少提供 2 个视觉方向候选（主方案 + 备选方案），并记录取舍原因。"
        )

    def _render_component_implementation_manifest(self, profile: dict) -> str:
        matrix = profile.get("ui_library_matrix", [])
        lines = [
            "| 层级 | 推荐组合 | 目标输出 |",
            "|:---|:---|:---|",
            "| Token 层 | Tailwind theme + CSS variables | 颜色/字体/间距/圆角/阴影/动效统一约束 |",
            "| Primitive 层 | Button/Input/Card/Dialog/Nav 等基础组件 | 所有组件具备状态与可访问性 |",
            "| Pattern 层 | 页面骨架（Hero/Feature/Pricing/FAQ 或 Dashboard） | 信息架构先于视觉样式 |",
            "| Surface 层 | Web/H5/小程序/APP/桌面端 对应实现 | 品牌一致 + 平台交互差异化 |",
        ]
        if matrix:
            lines.extend(["", "**场景映射**:"])
            for row in matrix[:5]:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- {row.get('scene', '-')}: {row.get('libraries', '-')}（重点：{row.get('focus', '-')}）"
                )
        lines.extend(
            [
                "",
                "**落地清单**:",
                "- 至少实现 1 套品牌按钮系统（主按钮/次按钮/幽灵按钮/危险按钮）。",
                "- 至少实现 1 套表单体系（字段/校验/错误态/帮助态/成功态）。",
                "- 至少实现 1 套信息展示体系（卡片/表格/图表/筛选栏/空态）。",
                "- 所有关键组件必须提供 Tailwind class 规范与复用示例。",
            ]
        )
        return "\n".join(lines)

    def _render_page_blueprints(self, profile: dict) -> str:
        lines: list[str] = []
        for blueprint in profile.get("page_blueprints", []):
            lines.extend(
                [
                    f"#### {blueprint.get('page', '未命名页面')}",
                    "",
                    "**推荐模块顺序**:",
                ]
            )
            lines.extend(f"- {section}" for section in blueprint.get("sections", []))
            lines.extend(
                [
                    "",
                    f"**设计重点**: {blueprint.get('focus', '无')}",
                    "",
                ]
            )
        return "\n".join(lines).rstrip()

    def _render_visual_assets_strategy(self, profile: dict) -> str:
        lines = [
            f"- **图标库**: {profile.get('component_stack', {}).get('icons', 'Lucide')}，禁止 emoji 代替功能图标。",
            f"- **图表策略**: {profile.get('component_stack', {}).get('chart', 'Recharts')}，图表先服务决策，再考虑视觉装饰。",
            "- **品牌/合作方 Logo**: 统一使用官方 SVG 或可信来源矢量资产，避免猜测版图形。",
            "- **截图策略**: 对外页面优先使用真实产品截图、流程图或数据示意，而不是空洞插画。",
            "",
            "**优先落地的组件模块**:",
        ]
        lines.extend(f"- {item}" for item in profile.get("component_priorities", []))
        lines.extend(["", "**明确禁止**:"])
        lines.extend(f"- {item}" for item in profile.get("banned_patterns", [])[:6])
        return "\n".join(lines)

    def _get_design_recommendations(self) -> dict:
        """获取智能设计推荐"""
        try:
            # 导入设计引擎
            import sys
            from pathlib import Path

            # 添加项目根目录到 Python 路径
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from super_dev.design import (
                DesignIntelligenceEngine,
                get_landing_generator,
                get_ux_guide,
            )

            # 分析项目特征
            analysis = self._analyze_project_for_design()

            # 初始化引擎
            design_engine = DesignIntelligenceEngine()
            landing_gen = get_landing_generator()
            ux_guide = get_ux_guide()

            # 获取推荐
            recommendations = {}

            # 1. 风格推荐
            style_query = f"{analysis['style']} {analysis['product_type']} {analysis['industry']}"
            style_results = design_engine.search(style_query, domain="style", max_results=3)
            recommendations["styles"] = style_results.get("results", [])[:3]

            # 2. 配色推荐
            color_query = (
                f"{analysis['industry']} {analysis['product_type']}"
                if analysis["industry"] != "general"
                else analysis["product_type"]
            )
            color_results = design_engine.search(color_query, domain="color", max_results=1)
            recommendations["colors"] = (color_results.get("results", []) or [None])[0]

            # 3. 字体推荐
            font_query = f"{analysis['style']} professional"
            font_results = design_engine.search(font_query, domain="typography", max_results=2)
            recommendations["fonts"] = font_results.get("results", [])[:2]

            # 4. Landing 页面推荐（如果适用）
            if analysis["product_type"] in ["landing", "saas", "ecommerce"]:
                landing_pattern = landing_gen.recommend(
                    product_type=analysis["product_type"],
                    goal="signup",
                    audience="B2C" if analysis["industry"] == "general" else "B2B",
                )
                recommendations["landing"] = (
                    landing_pattern.to_dict()
                    if landing_pattern and hasattr(landing_pattern, "to_dict")
                    else None
                )
            else:
                recommendations["landing"] = None

            # 5. UX 最佳实践
            ux_quick_wins = ux_guide.get_quick_wins(max_results=5)
            ux_tips = []
            for rec in ux_quick_wins:
                guideline = rec.guideline
                ux_tips.append(
                    {
                        "guideline": {
                            "domain": (
                                guideline.domain.value
                                if hasattr(guideline.domain, "value")
                                else str(guideline.domain)
                            ),
                            "topic": guideline.topic,
                            "best_practice": guideline.best_practice,
                            "anti_pattern": guideline.anti_pattern,
                            "impact": guideline.impact,
                            "complexity": guideline.complexity,
                        },
                        "priority": rec.priority,
                        "implementation_effort": rec.implementation_effort,
                        "user_impact": rec.user_impact,
                    }
                )
            recommendations["ux_tips"] = ux_tips

            return recommendations

        except Exception as e:
            # 如果设计引擎失败，返回空推荐
            logging.getLogger(__name__).warning(f"Design engine failed: {e}")
            return {"styles": [], "colors": None, "fonts": [], "landing": None, "ux_tips": []}
