"""
开发：Excellent（11964948@qq.com）
功能：商业级 UI Intelligence 推荐引擎
作用：基于产品类型、行业和前端栈推荐 UI 方案，提供配色、字体、组件库和设计治理知识库
创建时间：2025-12-30
最后修改：2026-03-21
"""

from __future__ import annotations

from typing import Any

from .ui_intelligence_foundation_catalog import UIIntelligenceFoundationCatalogMixin
from .ui_intelligence_models import (
    DesignReference,
    FrameworkPlaybook,
    LibraryRecommendation,
)
from .ui_intelligence_stack_catalog import UIIntelligenceStackCatalogMixin


class UIIntelligenceAdvisor(
    UIIntelligenceFoundationCatalogMixin,
    UIIntelligenceStackCatalogMixin,
):
    """商业级 UI/UX 推荐引擎"""

    # 向后兼容：旧测试和外部调用仍可能使用 COMPONENT_LIBRARIES 这个名字。

    @staticmethod
    def generate_dark_variant(palette: dict[str, str]) -> dict[str, str]:
        """从浅色配色方案自动生成暗色变体"""
        bg = palette.get("background", "#FFFFFF")

        # If already dark (background is dark), return as-is
        bg_hex = bg.lstrip("#")
        if len(bg_hex) == 6:
            r, g, b = int(bg_hex[:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            if luminance < 0.4:
                return dict(palette)  # Already dark

        # Generate dark variant
        return {
            "primary": palette.get("primary", "#2563EB"),
            "secondary": palette.get("secondary", "#3B82F6"),
            "accent": palette.get("accent", "#EA580C"),
            "background": "#0F172A",
            "text": "#F8FAFC",
            "card": "#1E293B",
            "muted": "#334155",
            "border": "#475569",
            "name": palette.get("name", "Dark") + " Dark",
        }

    def recommend(
        self,
        *,
        description: str,
        frontend: str,
        product_type: str,
        industry: str,
        style: str,
        ui_library: str | None = None,
        preferred_design_reference_slug: str | None = None,
    ) -> dict[str, Any]:
        """生成 UI intelligence 推荐"""
        raw_frontend = frontend.lower().strip()
        normalized_frontend = self.FRONTEND_ALIASES.get(raw_frontend, raw_frontend)
        profile = self.PRODUCT_PROFILES.get(product_type, self.PRODUCT_PROFILES["general"])
        industry_rules = self.INDUSTRY_TRUST_RULES.get(
            industry, self.INDUSTRY_TRUST_RULES["general"]
        )
        library_options = self.STACK_RECOMMENDATIONS.get(
            normalized_frontend, self.STACK_RECOMMENDATIONS["default"]
        )

        primary_library = library_options[0]
        if ui_library:
            primary_library = LibraryRecommendation(
                name=ui_library,
                category="User Selected",
                rationale="用户在项目初始化时显式指定，作为实现基线保留。",
                strengths=[
                    "与项目已有约束保持一致",
                    "避免在中途切换组件生态带来重构成本",
                ],
                notes=[
                    "仍需结合 token、排版和页面骨架进行品牌化重写",
                ],
            )

        density = profile["information_density"]
        chart_key = "dense" if density == "high" else "default"
        chart_library = self.CHART_RECOMMENDATIONS.get(
            normalized_frontend, self.CHART_RECOMMENDATIONS["default"]
        )[chart_key]

        icon_library = self.ICON_RECOMMENDATIONS["dense" if density == "high" else "brand"]

        design_system_priorities = [
            "先冻结颜色、字体、间距、圆角、阴影、边框和动效 token",
            "先定义桌面/平板/移动端栅格与容器宽度，再生成页面",
            "先定义全局组件状态矩阵，再进入页面抛光",
            "优先做页面结构、业务路径和信任表达，再做视觉特效",
        ]

        benchmark_principles = [
            "优先输出完整设计系统和页面骨架，而不是直接铺满页面装饰",
            "页面需要像成熟商业产品，具备截图、案例、信任、状态、流程和数据层级",
            "组件库只负责加速，不负责品牌感，必须做 token 和排版层重写",
            "对营销页、产品页、工作台分别使用不同的信息密度和交互策略",
            "同一产品在 Web/H5/小程序/APP 需保持品牌一致，同时保留平台原生交互习惯",
        ]

        trust_modules = list(industry_rules["trust_modules"]) + list(profile["conversion_modules"])
        banned_patterns = (
            list(profile["banned_patterns"])
            + list(industry_rules["banned_patterns"])
            + [
                "emoji 充当功能图标或临时占位图标",
                "Claude / ChatGPT 同款侧栏聊天骨架与窄中栏对话壳层",
                "以灰黑中性色为主、几乎无品牌辨识度的聊天式产品外壳",
            ]
        )

        state_requirements = [
            "normal",
            "hover",
            "active",
            "focus-visible",
            "loading",
            "empty",
            "error",
            "disabled",
            "success-feedback",
            "permission-limited",
        ]

        component_stack = {
            "form": self.FORM_STACK.get(normalized_frontend, self.FORM_STACK["default"]),
            "table": self._table_strategy(normalized_frontend, density),
            "chart": chart_library,
            "motion": self.MOTION_STACK.get(normalized_frontend, self.MOTION_STACK["default"]),
            "icons": icon_library,
        }
        ui_library_matrix = [
            {
                "scene": "Web 工作台",
                "libraries": "shadcn/ui + Radix + Tailwind",
                "focus": "高密度任务与状态可见性",
            },
            {
                "scene": "品牌官网/H5",
                "libraries": "Tailwind + Aceternity UI / Magic UI",
                "focus": "叙事转化与视觉识别",
            },
            {
                "scene": "多主题业务",
                "libraries": "Tailwind + DaisyUI",
                "focus": "主题系统与快速迭代",
            },
            {
                "scene": "微信小程序",
                "libraries": "TDesign 小程序 + Taro / UniApp",
                "focus": "腾讯生态规范、触控效率与性能包体",
            },
            {
                "scene": "APP",
                "libraries": "React Native / Flutter / SwiftUI",
                "focus": "手势、反馈、导航与原生体验一致性",
            },
            {
                "scene": "桌面端",
                "libraries": "Electron / Tauri + React/Vue + Tailwind",
                "focus": "窗口范式、快捷键与本地能力集成",
            },
        ]
        quality_checklist = [
            "必须提供 token（color/typography/spacing/radius/shadow/motion）并可复用",
            "必须覆盖关键状态（loading/empty/error/success/permission）",
            "必须具备商业信任模块（案例、指标、定价、FAQ、合规）",
            "必须通过可访问性检查（对比度、键盘、focus、reduced motion）",
            "必须通过品牌差异化检查（字体层级、配色节奏、图形语言）",
            "必须通过反 AI 味检查（拒绝科技 cliché、聊天壳模板和无意义炫技）",
            "关键页面必须保留至少 2 个视觉方向候选与取舍理由",
        ]

        style_direction = self._build_style_direction(
            style=style, product_type=product_type, industry=industry
        )
        database_keywords = self._knowledge_keywords(
            description=description,
            product_type=product_type,
            industry=industry,
            frontend=normalized_frontend,
        )

        # Find matching palette
        palette_key = product_type
        if palette_key not in self.PRODUCT_COLOR_PALETTES:
            # Try industry match
            palette_key = industry if industry in self.PRODUCT_COLOR_PALETTES else "general"
        color_palette = self.PRODUCT_COLOR_PALETTES.get(
            palette_key, self.PRODUCT_COLOR_PALETTES["general"]
        )

        # Find matching typography
        typo_key = product_type
        if typo_key not in self.PRODUCT_TYPOGRAPHY_PRESETS:
            typo_key = industry if industry in self.PRODUCT_TYPOGRAPHY_PRESETS else "general"
        typography_preset = self.PRODUCT_TYPOGRAPHY_PRESETS.get(
            typo_key, self.PRODUCT_TYPOGRAPHY_PRESETS["general"]
        )
        selected_reference = self.get_design_reference(preferred_design_reference_slug)
        design_reference_items = self._select_design_references(
            product_type=product_type,
            industry=industry,
            style=style,
            frontend=normalized_frontend,
            preferred_slug=selected_reference.slug if selected_reference else None,
        )
        design_references = [item.to_dict() for item in design_reference_items]
        framework_playbook = self._select_framework_playbook(
            raw_frontend=raw_frontend,
            normalized_frontend=normalized_frontend,
        )
        art_direction_candidates = self._select_art_direction_candidates(
            product_type=product_type,
            industry=industry,
            style=style,
            frontend=normalized_frontend,
            selected_reference_slug=selected_reference.slug if selected_reference else None,
        )
        design_direction_manifest = self._build_design_direction_manifest(
            description=description,
            density=density,
            art_direction_candidates=art_direction_candidates,
            selected_reference=selected_reference.to_dict() if selected_reference else None,
        )
        brand_signal_manifest = self._build_brand_signal_manifest(
            product_type=product_type,
            industry=industry,
            style=style,
            design_direction_manifest=design_direction_manifest,
        )
        proof_composition_rules = self._build_proof_composition_rules(
            product_type=product_type,
            density=density,
            trust_modules=trust_modules,
            design_direction_manifest=design_direction_manifest,
        )
        component_craft_requirements = self._build_component_craft_requirements(
            density=density,
            icon_library=icon_library,
            primary_library=primary_library.name,
        )
        layout_tension_rules = self._build_layout_tension_rules(
            density=density,
            design_direction_manifest=design_direction_manifest,
            product_type=product_type,
        )
        anti_ai_slop_guardrails = self._build_anti_ai_slop_guardrails(
            art_direction_candidates=art_direction_candidates,
            product_type=product_type,
        )
        critique_rubric = self._build_critique_rubric()
        tweak_categories = self._build_tweak_categories(
            art_direction_candidates=art_direction_candidates,
            density=density,
        )

        return {
            "frontend_variant": raw_frontend,
            "normalized_frontend": normalized_frontend,
            "surface": profile["surface"],
            "information_density": density,
            "experience_goals": list(profile["experience_goals"]),
            "page_blueprints": list(profile["page_blueprints"]),
            "component_priorities": list(profile["component_priorities"]),
            "design_system_priorities": design_system_priorities,
            "benchmark_principles": benchmark_principles,
            "art_direction_candidates": art_direction_candidates,
            "design_direction_manifest": design_direction_manifest,
            "brand_signal_manifest": brand_signal_manifest,
            "proof_composition_rules": proof_composition_rules,
            "component_craft_requirements": component_craft_requirements,
            "layout_tension_rules": layout_tension_rules,
            "anti_ai_slop_guardrails": anti_ai_slop_guardrails,
            "critique_rubric": critique_rubric,
            "tweak_categories": tweak_categories,
            "trust_modules": trust_modules,
            "banned_patterns": banned_patterns,
            "state_requirements": state_requirements,
            "primary_library": primary_library.to_dict(),
            "alternative_libraries": [item.to_dict() for item in library_options[1:3]],
            "component_stack": component_stack,
            "style_direction": style_direction,
            "industry_tone": industry_rules["tone"],
            "knowledge_keywords": database_keywords,
            "ui_library_matrix": ui_library_matrix,
            "quality_checklist": quality_checklist,
            "color_palette": color_palette,
            "color_palette_dark": self.generate_dark_variant(color_palette),
            "typography_preset": typography_preset,
            "design_references": design_references,
            "selected_design_reference": (
                selected_reference.to_dict() if selected_reference else None
            ),
            "framework_playbook": framework_playbook.to_dict() if framework_playbook else None,
            "pre_delivery_checklist": list(self.PRE_DELIVERY_CHECKLIST),
        }

    def _select_art_direction_candidates(
        self,
        *,
        product_type: str,
        industry: str,
        style: str,
        frontend: str,
        selected_reference_slug: str | None = None,
    ) -> list[dict[str, Any]]:
        reference_bias = {
            "linear.app": {"precision-workspace"},
            "raycast": {"precision-workspace"},
            "vercel": {"editorial-swiss"},
            "stripe": {"warm-trust", "quiet-luxury"},
            "figma": {"playful-modular"},
            "intercom": {"warm-trust"},
            "airbnb": {"warm-trust"},
            "supabase": {"precision-workspace", "cinematic-product"},
        }
        scored: list[tuple[int, dict[str, Any]]] = []
        for candidate in self.ART_DIRECTION_LIBRARY:
            score = 0
            if product_type in candidate.get("fit_product_types", ()):
                score += 4
            if style in candidate.get("fit_styles", ()):
                score += 3
            if industry in candidate.get("fit_industries", ()):
                score += 2
            if frontend in {"desktop", "react-native"} and candidate["id"] == "precision-workspace":
                score += 1
            if frontend == "miniapp" and candidate["id"] == "warm-trust":
                score += 1
            if selected_reference_slug and candidate["id"] in reference_bias.get(
                selected_reference_slug, set()
            ):
                score += 2
            if style == "luxury" and candidate["id"] == "quiet-luxury":
                score += 2
            if product_type == "dashboard" and candidate["id"] == "precision-workspace":
                score += 2
            if product_type == "landing" and candidate["id"] in {
                "editorial-swiss",
                "warm-trust",
                "cinematic-product",
            }:
                score += 1
            scored.append((score, candidate))

        ordered = [
            dict(item)
            for _, item in sorted(
                scored,
                key=lambda entry: (
                    -entry[0],
                    entry[1]["name"],
                ),
            )[:3]
        ]
        return ordered

    def _build_design_direction_manifest(
        self,
        *,
        description: str,
        density: str,
        art_direction_candidates: list[dict[str, Any]],
        selected_reference: dict[str, Any] | None,
    ) -> dict[str, Any]:
        primary = art_direction_candidates[0] if art_direction_candidates else {}
        alternatives = art_direction_candidates[1:3]
        return {
            "selected_direction": primary.get("name", "Modern Commercial"),
            "direction_id": primary.get("id", "modern-commercial"),
            "philosophy": primary.get("philosophy", "先锁定视觉哲学，再组织层级、证明和交互。"),
            "hero_treatment": primary.get(
                "hero_treatment", "首屏同时承担价值主张、证据和行动入口。"
            ),
            "narrative_mode": primary.get("narrative_mode", "先建立理解，再展示能力与证据。"),
            "visual_tension": primary.get(
                "visual_tension", "通过排版、留白和重点色建立张力，而不是依赖炫技。"
            ),
            "density_tempo": primary.get("density_tempo", density),
            "proof_strategy": primary.get("proof_strategy", "优先使用截图、案例、数据和流程证明。"),
            "palette_strategy": primary.get(
                "palette_strategy", "先控制颜色数量，再决定强调色位置。"
            ),
            "reference_anchor": (selected_reference or {}).get("name", ""),
            "reference_translation_rule": "吸收参考信号，但必须重组为原创组合，禁止 1:1 复刻。",
            "why_this_direction": (
                f"当前产品描述为“{description[:60]}”，所选方向需要同时兼顾商业说服力、品牌辨识度和可实现性。"
            ),
            "alternatives": [
                {
                    "name": item.get("name", ""),
                    "why_not_primary": "可作为备选方向，但在当前业务语境下不如主方向稳定。",
                }
                for item in alternatives
            ],
        }

    def _build_brand_signal_manifest(
        self,
        *,
        product_type: str,
        industry: str,
        style: str,
        design_direction_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        direction = str(design_direction_manifest.get("selected_direction") or "Modern Commercial")
        proof_strategy = str(
            design_direction_manifest.get("proof_strategy") or "优先使用真实截图、案例和数据证明。"
        )
        tone_descriptors = [
            direction,
            "商业可信",
            "执行专业",
            "不是模板页",
        ]
        if style == "luxury":
            tone_descriptors.extend(["克制高级", "高单价感"])
        if product_type in {"dashboard", "saas"}:
            tone_descriptors.extend(["专业工作台", "效率优先"])
        if industry in {"finance", "legal", "government"}:
            tone_descriptors.extend(["合规权威", "风险可见"])
        credibility_devices = [
            "真实界面截图或高保真流程示意，而不是抽象插画占位",
            "关键指标、客户/案例、合规/安全与能力边界要同屏出现",
            "Hero 下方第一屏必须出现证据，而不是拖到页面底部",
        ]
        premium_surfaces = [
            "Hero 价值主张与证明层同时出现",
            "模块分区的节奏、边界、留白和标题尺度被明确设计",
            "关键 CTA、信任条和案例区形成自然转化闭环",
        ]
        authority_markers = [
            proof_strategy,
            "标题、正文、说明文案具备明显层级和语气控制",
            "品牌色只在关键证明和行动点上承担强调职责",
        ]
        return {
            "tone_descriptors": tone_descriptors,
            "credibility_devices": credibility_devices,
            "premium_surfaces": premium_surfaces,
            "authority_markers": authority_markers,
        }

    def _build_proof_composition_rules(
        self,
        *,
        product_type: str,
        density: str,
        trust_modules: list[str],
        design_direction_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        default_trust_sequence = trust_modules[:4] or ["客户案例", "关键指标", "安全/合规", "FAQ"]
        hero_proof_stack = [
            "价值主张",
            "一句业务结果证明",
            default_trust_sequence[0],
            "主 CTA",
        ]
        if product_type in {"dashboard", "saas"}:
            hero_proof_stack = ["价值主张", "状态/结果截图", default_trust_sequence[0], "主 CTA"]
        evidence_priority = [
            str(design_direction_manifest.get("proof_strategy") or "真实截图与数据优先"),
            "真实工作流/操作路径优先于抽象卖点",
            "用户在首屏和次屏必须看到至少两类不同证据",
        ]
        return {
            "hero_proof_stack": hero_proof_stack,
            "trust_sequence": default_trust_sequence,
            "evidence_priority": evidence_priority,
            "proof_density_rule": (
                "高密度产品每个关键页面至少出现 2 个证明模块，低密度产品至少出现 1 个强证明模块。"
                if density == "high"
                else "每个关键页面至少出现 1 个强证明模块，并在收尾区域补齐 FAQ / 案例 / 合规。"
            ),
        }

    def _build_component_craft_requirements(
        self,
        *,
        density: str,
        icon_library: str,
        primary_library: str,
    ) -> list[str]:
        requirements = [
            f"图标统一来自 {icon_library}，禁止混入 emoji、插画风小图标和多套图标来源。",
            f"核心组件必须围绕 {primary_library} 做品牌化重写，不能只保留默认视觉。",
            "主按钮、输入框、卡片、表格、导航、空状态至少覆盖 normal/hover/focus/loading/error/disabled。",
            "圆角、阴影、边框和间距必须服从同一套 token，不允许页面级临时发挥。",
        ]
        if density == "high":
            requirements.append(
                "高密度工作台必须控制信息噪音，优先让标题、数据、状态和动作一眼分层。"
            )
        else:
            requirements.append(
                "低密度品牌页必须用更强的标题尺度、节奏和证明层来建立高级感，不能只靠大留白。"
            )
        return requirements

    def _build_layout_tension_rules(
        self,
        *,
        density: str,
        design_direction_manifest: dict[str, Any],
        product_type: str,
    ) -> list[str]:
        rules = [
            str(
                design_direction_manifest.get("visual_tension")
                or "通过排版尺度、区块边界、色彩控制和留白节奏建立张力。"
            ),
            "至少要有一个显式压缩区和一个显式展开区，避免整页密度完全均匀。",
            "关键信息、证明和 CTA 之间要形成先后关系，而不是所有卡片同权平铺。",
        ]
        if product_type in {"dashboard", "content"}:
            rules.append(
                "工作台不要把所有信息塞进第一屏；要用 summary -> workspace -> detail 的层级收放。"
            )
        else:
            rules.append(
                "品牌页要把氛围、产品证明和转化动作做成连续节奏，避免只有大标题和功能列表。"
            )
        if density == "high":
            rules.append("高密度页面用分区、容器和对齐建立秩序，不用大面积装饰来制造存在感。")
        return rules

    def _build_anti_ai_slop_guardrails(
        self,
        *,
        art_direction_candidates: list[dict[str, Any]],
        product_type: str,
    ) -> dict[str, Any]:
        forbidden_motifs = [
            "紫粉赛博霓虹、渐变圆球、数字雨、电路板、发光脑图",
            "只有一句 slogan 的空洞 Hero",
            "默认灰黑聊天壳层、窄中栏对话布局、模型切换器 UI",
            "过量玻璃拟态、模糊背景和无意义粒子动画",
            "只有卡片墙没有清晰层级与功能路径",
        ]
        hierarchy_rules = [
            "标题与正文至少建立 3 级明显层级，首屏标题与正文建议保持 2.5x 以上尺寸对比。",
            "颜色数量保持受控，主色/辅色/强调色/中性色要有明确职责。",
            "关键页面必须先出现证据和 CTA，再出现次级装饰。",
        ]
        originality_checks = [
            "至少提供 2 个视觉方向候选，并明确写下为什么不用另一个方向。",
            "任何设计参考都只能借信号，不能复制具体构图和组件拼法。",
            "界面必须能说出自己的品牌语气，而不是只像某个流行 AI 产品。",
        ]
        craft_checks = [
            "必须使用统一间距系统与 token，不允许随手写多个零散尺寸。",
            "核心组件必须覆盖 hover/focus/loading/empty/error/disabled。",
            "图标只能来自正式图标库，不允许 emoji 和混杂图标来源。",
        ]
        if product_type in {"dashboard", "saas"}:
            hierarchy_rules.append("后台/工作台禁止 oversized hero 占用主要工作区。")
        return {
            "positioning": "先建立清晰设计哲学、结构层级和证明方式，再决定视觉特效。",
            "forbidden_motifs": forbidden_motifs,
            "hierarchy_rules": hierarchy_rules,
            "originality_checks": originality_checks,
            "craft_checks": craft_checks,
            "candidate_anti_cliches": [
                item
                for candidate in art_direction_candidates
                for item in candidate.get("anti_cliches", [])[:2]
            ][:6],
        }

    def _build_critique_rubric(self) -> list[dict[str, Any]]:
        return [
            {
                "dimension": "philosophy_alignment",
                "label": "哲学一致性",
                "focus": "设计是否真正体现选定视觉哲学，而不是只停留在表面元素。",
                "pass_threshold": 8,
            },
            {
                "dimension": "visual_hierarchy",
                "label": "视觉层级",
                "focus": "用户是否能自然沿层级理解价值主张、证据和下一步动作。",
                "pass_threshold": 8,
            },
            {
                "dimension": "brand_authority",
                "label": "品牌权威感",
                "focus": "页面是否像成熟商业产品，具备可信品牌语气、证明构图与高级完成度。",
                "pass_threshold": 8,
            },
            {
                "dimension": "craft_quality",
                "label": "细节工艺",
                "focus": "对齐、间距、颜色、字体与状态矩阵是否足够精确、克制且统一。",
                "pass_threshold": 8,
            },
            {
                "dimension": "functionality",
                "label": "功能性",
                "focus": "每个模块是否服务业务路径与交互目标，而不是为了装饰存在。",
                "pass_threshold": 8,
            },
            {
                "dimension": "originality",
                "label": "原创度",
                "focus": "是否摆脱 AI cliché、模板化聊天壳和同质化科技视觉。",
                "pass_threshold": 8,
            },
        ]

    def _build_tweak_categories(
        self, *, art_direction_candidates: list[dict[str, Any]], density: str
    ) -> list[dict[str, Any]]:
        primary = art_direction_candidates[0] if art_direction_candidates else {}
        return [
            {
                "name": "Direction",
                "label": "视觉方向切换",
                "controls": [item.get("name", "") for item in art_direction_candidates[:3]],
            },
            {
                "name": "Density",
                "label": "信息密度",
                "controls": [density, "compact", "balanced", "spacious"],
            },
            {
                "name": "Emphasis",
                "label": "重点表达",
                "controls": primary.get("tweak_axes", ["标题张力", "CTA 强度", "证据密度"])[:4],
            },
        ]

    def list_design_references(
        self,
        *,
        product_type: str | None = None,
        industry: str | None = None,
        style: str | None = None,
        frontend: str | None = None,
        limit: int | None = None,
    ) -> list[DesignReference]:
        normalized_frontend = ""
        if frontend:
            raw_frontend = frontend.lower().strip()
            normalized_frontend = self.FRONTEND_ALIASES.get(raw_frontend, raw_frontend)

        scored: list[tuple[int, DesignReference]] = []
        for item in self.DESIGN_REFERENCES:
            if product_type and product_type not in item.fit_product_types:
                continue
            if industry and industry not in item.fit_industries:
                continue
            if style and style not in item.fit_styles:
                continue
            if normalized_frontend and normalized_frontend not in item.fit_frontends:
                continue
            score = item.priority
            if product_type:
                score += 5
            if industry:
                score += 3
            if style:
                score += 2
            if normalized_frontend:
                score += 2
            scored.append((score, item))

        if not scored:
            scored = [(item.priority, item) for item in self.DESIGN_REFERENCES]

        scored.sort(key=lambda pair: pair[0], reverse=True)
        items = [item for _, item in scored]
        if limit is not None:
            return items[: max(limit, 0)]
        return items

    def get_design_reference(self, slug_or_name: str | None) -> DesignReference | None:
        token = str(slug_or_name or "").strip().lower()
        if not token:
            return None

        for item in self.DESIGN_REFERENCES:
            aliases = {
                item.slug.lower(),
                item.slug.lower().replace(".", "-"),
                item.slug.lower().split(".")[0],
                item.name.lower(),
                item.name.lower().replace(" ", "-"),
            }
            if token in aliases:
                return item
        return None

    def _select_design_references(
        self,
        *,
        product_type: str,
        industry: str,
        style: str,
        frontend: str,
        limit: int = 3,
        preferred_slug: str | None = None,
    ) -> list[DesignReference]:
        scored: list[tuple[int, DesignReference]] = []
        for item in self.DESIGN_REFERENCES:
            score = item.priority
            if product_type in item.fit_product_types:
                score += 5
            if industry in item.fit_industries:
                score += 3
            if style in item.fit_styles:
                score += 2
            if frontend in item.fit_frontends:
                score += 2
            if product_type == "dashboard" and "dashboard" in item.rationale.lower():
                score += 1
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)

        picked: list[DesignReference] = []
        seen: set[str] = set()
        preferred = self.get_design_reference(preferred_slug)
        if preferred is not None:
            picked.append(preferred)
            seen.add(preferred.slug)
        for _, item in scored:
            if item.slug in seen:
                continue
            picked.append(item)
            seen.add(item.slug)
            if len(picked) >= limit:
                break
        return picked

    def _select_framework_playbook(
        self,
        *,
        raw_frontend: str,
        normalized_frontend: str,
    ) -> FrameworkPlaybook | None:
        if raw_frontend in self.FRAMEWORK_PLAYBOOKS:
            return self.FRAMEWORK_PLAYBOOKS[raw_frontend]
        if normalized_frontend == "miniapp":
            return self.FRAMEWORK_PLAYBOOKS["uni-app"]
        if normalized_frontend in self.FRAMEWORK_PLAYBOOKS:
            return self.FRAMEWORK_PLAYBOOKS[normalized_frontend]
        return None

    def _table_strategy(self, frontend: str, density: str) -> str:
        if density == "high":
            if frontend == "react":
                return "TanStack Table + virtualized rows"
            if frontend == "vue":
                return "Naive UI DataTable / vxe-table（按复杂度选择）"
            if frontend == "angular":
                return "CDK Table / AG Grid（复杂后台）"
            if frontend == "svelte":
                return "TanStack Table core + custom renderers"
            if frontend == "miniapp":
                return "TDesign Table / 虚拟列表 + 分页筛选"
            if frontend in {"react-native", "flutter", "swiftui"}:
                return "Virtualized List + Filter Chips + Sticky Header"
            if frontend == "desktop":
                return "AG Grid / Naive DataTable + Split View + Local Index"
        return "Semantic table + lightweight sorting/filtering"

    def _build_style_direction(
        self, *, style: str, product_type: str, industry: str
    ) -> dict[str, str]:
        mappings = {
            "minimal": {
                "direction": "克制、清晰、减少装饰噪音",
                "materials": "高质量排版、细边框、低饱和背景层",
            },
            "professional": {
                "direction": "可信、稳定、业务优先",
                "materials": "中性色基底 + 单一强调色 + 稳定阴影",
            },
            "playful": {
                "direction": "友好、活跃，但仍保持产品成熟度",
                "materials": "高识别主色 + 更开放的圆角和插图节奏",
            },
            "luxury": {
                "direction": "高级、克制、重材质与排版节奏",
                "materials": "高对比色、精致留白、受控动效",
            },
            "modern": {
                "direction": "现代商业产品基线，品牌感与效率并重",
                "materials": "干净背景、明确层级、局部强调而非全屏特效",
            },
        }
        result = mappings.get(style, mappings["modern"]).copy()
        if product_type == "dashboard":
            result["materials"] += "；在高密度工作台中控制装饰层，优先数据可读性。"
        if industry in {"healthcare", "fintech"}:
            result["direction"] += "，降低风险感和不确定感。"
        return result

    def _knowledge_keywords(
        self,
        *,
        description: str,
        product_type: str,
        industry: str,
        frontend: str,
    ) -> list[str]:
        words = [
            product_type,
            industry,
            frontend,
            "design tokens",
            "component states",
            "commercial ui",
            "trust design",
        ]
        lowered = description.lower()
        if any(
            token in lowered for token in ["dashboard", "后台", "仪表盘", "workbench", "工作台"]
        ):
            words.extend(["data table", "filter bar", "audit trail", "dense workspace"])
        if any(
            token in lowered
            for token in ["landing", "官网", "marketing", "official website", "落地页"]
        ):
            words.extend(["hero", "social proof", "pricing", "conversion"])
        if any(token in lowered for token in ["checkout", "支付", "billing", "order", "cart"]):
            words.extend(["checkout", "trust badges", "payment status"])
        return words

    # ------------------------------------------------------------------
    # Responsive Design Validation
    # ------------------------------------------------------------------

    def _check_responsive_design(self, css_content: str, html_content: str = "") -> dict[str, Any]:
        """
        检查响应式设计实现质量。

        分析 CSS 中的媒体查询、响应式单位使用情况，以及是否存在不推荐的固定像素宽度。

        Args:
            css_content: CSS 文件内容
            html_content: 可选的 HTML 内容，用于检查 viewport meta

        Returns:
            包含响应式设计评估结果的字典
        """
        import re

        issues: list[dict[str, str]] = []
        suggestions: list[str] = []
        score = 100

        # 1. Check for media queries
        media_queries = re.findall(r"@media\s*\([^)]+\)", css_content)
        media_breakpoints: list[str] = []
        for mq in media_queries:
            bp_match = re.search(r"(\d+)px", mq)
            if bp_match:
                media_breakpoints.append(bp_match.group(1))

        standard_breakpoints = {"375", "480", "640", "768", "1024", "1280", "1440"}
        covered_breakpoints = set(media_breakpoints) & standard_breakpoints
        missing_breakpoints = standard_breakpoints - set(media_breakpoints)

        if not media_queries:
            issues.append(
                {
                    "severity": "high",
                    "message": "CSS 中未发现任何媒体查询（@media），页面可能无法在不同屏幕尺寸下正常显示",
                    "fix": "添加至少 3 个断点的媒体查询：768px（平板）、1024px（小桌面）、1440px（大桌面）",
                }
            )
            score -= 30
        elif len(media_queries) < 3:
            issues.append(
                {
                    "severity": "medium",
                    "message": f"仅发现 {len(media_queries)} 个媒体查询，建议覆盖更多断点",
                    "fix": "建议至少覆盖 375px / 768px / 1024px / 1440px 四个常用断点",
                }
            )
            score -= 15

        # 2. Check for responsive units usage
        responsive_units = {
            "rem": len(re.findall(r"[\d.]+rem", css_content)),
            "em": len(re.findall(r"[\d.]+em(?!s)", css_content)),
            "%": len(re.findall(r"[\d.]+%", css_content)),
            "vw": len(re.findall(r"[\d.]+vw", css_content)),
            "vh": len(re.findall(r"[\d.]+vh", css_content)),
            "vmin": len(re.findall(r"[\d.]+vmin", css_content)),
            "vmax": len(re.findall(r"[\d.]+vmax", css_content)),
            "clamp": len(re.findall(r"clamp\(", css_content)),
            "min()": len(re.findall(r"min\(", css_content)),
            "max()": len(re.findall(r"max\(", css_content)),
        }
        total_responsive_units = sum(responsive_units.values())
        total_px_units = len(re.findall(r"[\d.]+px", css_content))

        if total_responsive_units == 0:
            issues.append(
                {
                    "severity": "high",
                    "message": "未使用任何响应式单位（rem/em/%/vw/vh/clamp），全部使用固定像素",
                    "fix": "字体建议使用 rem，容器宽度建议使用 % 或 max-width，间距建议使用 rem 或 em",
                }
            )
            score -= 25
        elif (
            total_px_units > 0
            and total_responsive_units / (total_px_units + total_responsive_units) < 0.3
        ):
            issues.append(
                {
                    "severity": "medium",
                    "message": f"响应式单位占比偏低（{total_responsive_units}/{total_px_units + total_responsive_units}），大量使用固定像素",
                    "fix": "建议将字体、间距和容器尺寸逐步迁移到 rem/% 等响应式单位",
                }
            )
            score -= 10

        # 3. Check for hardcoded pixel widths (anti-pattern)
        hardcoded_width_pattern = re.compile(r"(?:^|\s|;)width\s*:\s*(\d+)px", re.MULTILINE)
        hardcoded_widths = hardcoded_width_pattern.findall(css_content)
        problematic_widths = [w for w in hardcoded_widths if int(w) > 320]

        if problematic_widths:
            issues.append(
                {
                    "severity": "medium",
                    "message": f"发现 {len(problematic_widths)} 个硬编码的大像素宽度值：{', '.join(problematic_widths[:5])}px",
                    "fix": "使用 max-width 代替 width，或使用百分比和 min()/max()/clamp() 函数",
                }
            )
            score -= min(len(problematic_widths) * 3, 15)

        # 4. Check for hardcoded pixel heights on containers
        hardcoded_height_pattern = re.compile(r"(?:^|\s|;)height\s*:\s*(\d+)px", re.MULTILINE)
        hardcoded_heights = hardcoded_height_pattern.findall(css_content)
        large_fixed_heights = [h for h in hardcoded_heights if int(h) > 200]
        if large_fixed_heights:
            issues.append(
                {
                    "severity": "low",
                    "message": f"发现 {len(large_fixed_heights)} 个大的固定高度值，可能导致内容溢出",
                    "fix": "考虑使用 min-height 代替 height，或使用 auto/fit-content",
                }
            )
            score -= 5

        # 5. Check for flexible layout usage
        flexbox_count = len(re.findall(r"display\s*:\s*flex", css_content))
        grid_count = len(re.findall(r"display\s*:\s*grid", css_content))
        if flexbox_count == 0 and grid_count == 0:
            issues.append(
                {
                    "severity": "high",
                    "message": "未使用 Flexbox 或 Grid 布局，可能依赖过时的浮动或定位布局",
                    "fix": "优先使用 CSS Grid 进行页面布局，Flexbox 进行组件内部布局",
                }
            )
            score -= 20

        # 6. Check viewport meta in HTML
        has_viewport_meta = False
        if html_content:
            has_viewport_meta = "viewport" in html_content and "width=device-width" in html_content
            if not has_viewport_meta:
                issues.append(
                    {
                        "severity": "high",
                        "message": "HTML 缺少正确的 viewport meta 标签",
                        "fix": '添加 <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
                    }
                )
                score -= 15

        # 7. Check for container queries (modern CSS)
        container_queries = len(re.findall(r"@container", css_content))

        # 8. Check for overflow handling
        overflow_hidden_count = len(re.findall(r"overflow\s*:\s*hidden", css_content))
        overflow_auto_count = len(
            re.findall(r"overflow(?:-[xy])?\s*:\s*(?:auto|scroll)", css_content)
        )
        text_overflow_count = len(re.findall(r"text-overflow\s*:\s*ellipsis", css_content))

        # Generate suggestions
        if not container_queries:
            suggestions.append(
                "考虑使用 @container 查询实现组件级响应式设计（现代浏览器已广泛支持）"
            )
        if responsive_units.get("clamp", 0) == 0:
            suggestions.append(
                "建议使用 clamp() 实现流畅的字体和间距缩放，例如 font-size: clamp(1rem, 2.5vw, 2rem)"
            )
        if not text_overflow_count:
            suggestions.append("建议为文本内容添加 text-overflow: ellipsis 处理溢出场景")
        if len(covered_breakpoints) < 3:
            suggestions.append(
                f"建议补充以下断点的媒体查询：{', '.join(sorted(missing_breakpoints)[:3])}px"
            )

        score = max(0, min(100, score))

        return {
            "score": score,
            "grade": (
                "A"
                if score >= 90
                else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
            ),
            "media_queries": {
                "count": len(media_queries),
                "breakpoints_found": sorted(set(media_breakpoints)),
                "standard_covered": sorted(covered_breakpoints),
                "standard_missing": sorted(missing_breakpoints),
            },
            "unit_usage": {
                "responsive_units": {k: v for k, v in responsive_units.items() if v > 0},
                "fixed_px_count": total_px_units,
                "responsive_ratio": round(
                    total_responsive_units / max(total_px_units + total_responsive_units, 1), 2
                ),
            },
            "layout": {
                "flexbox_usage": flexbox_count,
                "grid_usage": grid_count,
                "container_queries": container_queries,
            },
            "overflow_handling": {
                "overflow_hidden": overflow_hidden_count,
                "overflow_auto_scroll": overflow_auto_count,
                "text_overflow_ellipsis": text_overflow_count,
            },
            "hardcoded_widths": [f"{w}px" for w in problematic_widths[:10]],
            "has_viewport_meta": has_viewport_meta if html_content else "N/A",
            "issues": issues,
            "suggestions": suggestions,
        }

    # ------------------------------------------------------------------
    # Accessibility Depth Check
    # ------------------------------------------------------------------

    def _check_accessibility_depth(
        self, html_content: str, css_content: str = ""
    ) -> dict[str, Any]:
        """
        深度检查无障碍（A11y）合规性。

        覆盖图片 alt 属性、表单 label 关联、颜色对比度、skip navigation、
        ARIA 属性和键盘导航支持等。

        Args:
            html_content: HTML 文件内容
            css_content: CSS 文件内容（可选，用于提取颜色变量计算对比度）

        Returns:
            包含无障碍评估结果的字典
        """
        import re

        issues: list[dict[str, str]] = []
        passes: list[str] = []
        score = 100

        # 1. Check images for alt attributes
        img_tags = re.findall(r"<img\b[^>]*>", html_content, re.IGNORECASE)
        imgs_without_alt: list[str] = []
        imgs_with_empty_alt = 0
        imgs_with_alt = 0

        for img in img_tags:
            if "alt=" not in img.lower():
                src_match = re.search(r'src\s*=\s*["\']([^"\']*)', img)
                imgs_without_alt.append(src_match.group(1) if src_match else "(unknown)")
            elif re.search(r'alt\s*=\s*["\'][\s]*["\']', img):
                imgs_with_empty_alt += 1
            else:
                imgs_with_alt += 1

        if imgs_without_alt:
            issues.append(
                {
                    "severity": "high",
                    "message": f"{len(imgs_without_alt)} 个图片缺少 alt 属性：{', '.join(imgs_without_alt[:5])}",
                    "fix": '为所有 <img> 标签添加描述性 alt 属性。纯装饰图片使用 alt=""',
                    "wcag": "WCAG 2.1 SC 1.1.1 Non-text Content (Level A)",
                }
            )
            score -= min(len(imgs_without_alt) * 5, 20)
        else:
            passes.append("所有图片均包含 alt 属性")

        # 2. Check forms for label associations
        input_tags = re.findall(r"<(?:input|select|textarea)\b[^>]*>", html_content, re.IGNORECASE)
        inputs_without_label: list[str] = []
        label_for_ids = set(
            re.findall(r'<label\b[^>]*for\s*=\s*["\']([^"\']+)', html_content, re.IGNORECASE)
        )
        aria_labelled_ids = set()

        for inp in input_tags:
            # Skip hidden inputs and submit buttons
            if re.search(r'type\s*=\s*["\'](?:hidden|submit|button)["\']', inp, re.IGNORECASE):
                continue
            inp_id_match = re.search(r'id\s*=\s*["\']([^"\']+)', inp)
            has_aria_label = "aria-label=" in inp.lower() or "aria-labelledby=" in inp.lower()
            if inp_id_match:
                inp_id = inp_id_match.group(1)
                if inp_id in label_for_ids or has_aria_label:
                    aria_labelled_ids.add(inp_id)
                    continue

            if not has_aria_label:
                name_match = re.search(r'name\s*=\s*["\']([^"\']+)', inp)
                inputs_without_label.append(name_match.group(1) if name_match else "(unnamed)")

        if inputs_without_label:
            issues.append(
                {
                    "severity": "high",
                    "message": f"{len(inputs_without_label)} 个表单元素缺少关联的 <label> 或 aria-label",
                    "fix": '使用 <label for="id"> 或 aria-label / aria-labelledby 关联表单控件',
                    "wcag": "WCAG 2.1 SC 1.3.1 Info and Relationships (Level A)",
                }
            )
            score -= min(len(inputs_without_label) * 5, 20)
        elif input_tags:
            passes.append("所有表单元素均有正确的 label 关联")

        # 3. Color contrast check (extract CSS variables and calculate)
        color_contrast_issues: list[dict[str, str]] = []
        if css_content:
            # Extract CSS custom properties (color values)
            color_vars: dict[str, str] = {}
            var_pattern = re.compile(
                r"--([a-zA-Z0-9_-]+)\s*:\s*(#[0-9a-fA-F]{3,8}|rgb[a]?\([^)]+\))"
            )
            for match in var_pattern.finditer(css_content):
                color_vars[match.group(1)] = match.group(2)

            # Check text/background contrast pairs
            text_keys = [
                k for k in color_vars if any(t in k.lower() for t in ["text", "foreground", "fg"])
            ]
            bg_keys = [
                k
                for k in color_vars
                if any(t in k.lower() for t in ["background", "bg", "surface"])
            ]

            for text_key in text_keys:
                for bg_key in bg_keys:
                    text_color = color_vars[text_key]
                    bg_color = color_vars[bg_key]
                    contrast = self._calculate_contrast_ratio(text_color, bg_color)
                    if contrast is not None and contrast < 4.5:
                        color_contrast_issues.append(
                            {
                                "text_var": f"--{text_key}",
                                "bg_var": f"--{bg_key}",
                                "text_color": text_color,
                                "bg_color": bg_color,
                                "ratio": f"{contrast:.2f}:1",
                                "required": "4.5:1 (WCAG AA)",
                            }
                        )

            if color_contrast_issues:
                issues.append(
                    {
                        "severity": "high",
                        "message": f"{len(color_contrast_issues)} 对文字/背景色对比度不满足 WCAG AA (4.5:1)",
                        "fix": "调整颜色变量确保文字与背景的对比度至少为 4.5:1（大文字至少 3:1）",
                        "wcag": "WCAG 2.1 SC 1.4.3 Contrast (Minimum) (Level AA)",
                    }
                )
                score -= min(len(color_contrast_issues) * 5, 20)
            elif color_vars:
                passes.append("CSS 变量中的颜色对比度满足 WCAG AA 标准")

        # 4. Check for skip navigation link
        has_skip_nav = bool(
            re.search(
                r'<a\b[^>]*href\s*=\s*["\']#(?:main|content|maincontent)["\'][^>]*>',
                html_content,
                re.IGNORECASE,
            )
        )
        skip_nav_class = bool(
            re.search(
                r"(?:skip[-_]?nav|skip[-_]?to[-_]?(?:main|content))",
                html_content,
                re.IGNORECASE,
            )
        )

        if not has_skip_nav and not skip_nav_class:
            issues.append(
                {
                    "severity": "medium",
                    "message": "未发现 Skip Navigation 链接",
                    "fix": '在页面顶部添加 <a href="#main" class="skip-nav">跳到主内容</a>',
                    "wcag": "WCAG 2.1 SC 2.4.1 Bypass Blocks (Level A)",
                }
            )
            score -= 10
        else:
            passes.append("页面包含 Skip Navigation 链接")

        # 5. Check ARIA landmarks
        has_main = bool(
            re.search(r'<main\b|role\s*=\s*["\']main["\']', html_content, re.IGNORECASE)
        )
        has_nav = bool(
            re.search(r'<nav\b|role\s*=\s*["\']navigation["\']', html_content, re.IGNORECASE)
        )
        has_banner = bool(
            re.search(r'<header\b|role\s*=\s*["\']banner["\']', html_content, re.IGNORECASE)
        )

        landmark_coverage = sum([has_main, has_nav, has_banner])
        if not has_main:
            issues.append(
                {
                    "severity": "medium",
                    "message": '缺少 <main> 元素或 role="main" 标记',
                    "fix": "使用 <main> 语义元素包裹页面主要内容区域",
                    "wcag": "WCAG 2.1 SC 1.3.1 Info and Relationships (Level A)",
                }
            )
            score -= 8

        # 6. Check for focus styles
        has_focus_visible = bool(re.search(r":focus-visible", css_content or ""))
        has_focus = bool(re.search(r":focus(?!-)", css_content or ""))
        has_outline_none = bool(re.search(r"outline\s*:\s*(?:none|0)", css_content or ""))

        if has_outline_none and not has_focus_visible and not has_focus:
            issues.append(
                {
                    "severity": "high",
                    "message": "移除了 outline 但未提供替代的 focus 样式",
                    "fix": "如果移除 outline，必须使用 :focus-visible 提供替代的焦点指示器",
                    "wcag": "WCAG 2.1 SC 2.4.7 Focus Visible (Level AA)",
                }
            )
            score -= 15

        if has_focus_visible:
            passes.append("使用了 :focus-visible 伪类提供键盘焦点样式")

        # 7. Check for reduced motion preference
        has_reduced_motion = bool(
            re.search(
                r"prefers-reduced-motion",
                css_content or "",
            )
        )
        if (
            not has_reduced_motion
            and css_content
            and ("animation" in css_content or "transition" in css_content)
        ):
            issues.append(
                {
                    "severity": "medium",
                    "message": "页面包含动画/过渡效果但未处理 prefers-reduced-motion 偏好",
                    "fix": "添加 @media (prefers-reduced-motion: reduce) { * { animation-duration: 0s; transition-duration: 0s; } }",
                    "wcag": "WCAG 2.1 SC 2.3.3 Animation from Interactions (Level AAA)",
                }
            )
            score -= 8
        elif has_reduced_motion:
            passes.append("尊重 prefers-reduced-motion 用户偏好设置")

        # 8. Check heading hierarchy
        headings = re.findall(r"<h([1-6])\b", html_content, re.IGNORECASE)
        heading_levels = [int(h) for h in headings]
        heading_issues: list[str] = []

        if heading_levels:
            if heading_levels[0] != 1:
                heading_issues.append(f"页面首个标题是 h{heading_levels[0]}，应该从 h1 开始")
            for i in range(1, len(heading_levels)):
                if heading_levels[i] > heading_levels[i - 1] + 1:
                    heading_issues.append(
                        f"标题层级从 h{heading_levels[i-1]} 跳到 h{heading_levels[i]}，跳过了中间层级"
                    )
                    break

        if heading_issues:
            issues.append(
                {
                    "severity": "medium",
                    "message": "标题层级结构不正确：" + "；".join(heading_issues),
                    "fix": "确保标题层级从 h1 开始且不跳级（h1 > h2 > h3 ...）",
                    "wcag": "WCAG 2.1 SC 1.3.1 Info and Relationships (Level A)",
                }
            )
            score -= 8

        # 9. Check lang attribute
        has_lang = bool(
            re.search(r'<html\b[^>]*\blang\s*=\s*["\'][^"\']+["\']', html_content, re.IGNORECASE)
        )
        if not has_lang:
            issues.append(
                {
                    "severity": "medium",
                    "message": "HTML 标签缺少 lang 属性",
                    "fix": '在 <html> 标签添加 lang 属性，如 <html lang="zh-CN">',
                    "wcag": "WCAG 2.1 SC 3.1.1 Language of Page (Level A)",
                }
            )
            score -= 5
        else:
            passes.append("HTML 标签包含 lang 属性")

        # 10. Check for button accessibility
        buttons_without_text = re.findall(
            r"<button\b[^>]*>\s*<(?:img|svg|i|span)\b[^>]*/?>\s*</button>",
            html_content,
            re.IGNORECASE,
        )
        icon_buttons_without_label = [
            btn
            for btn in buttons_without_text
            if "aria-label" not in btn.lower() and "title" not in btn.lower()
        ]
        if icon_buttons_without_label:
            issues.append(
                {
                    "severity": "medium",
                    "message": f"{len(icon_buttons_without_label)} 个图标按钮缺少 aria-label 或 title",
                    "fix": "为仅包含图标的按钮添加 aria-label 描述其功能",
                    "wcag": "WCAG 2.1 SC 4.1.2 Name, Role, Value (Level A)",
                }
            )
            score -= min(len(icon_buttons_without_label) * 3, 10)

        score = max(0, min(100, score))

        return {
            "score": score,
            "grade": (
                "A"
                if score >= 90
                else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
            ),
            "wcag_level": "AA" if score >= 75 else "A" if score >= 50 else "Fail",
            "images": {
                "total": len(img_tags),
                "with_alt": imgs_with_alt,
                "with_empty_alt": imgs_with_empty_alt,
                "missing_alt": imgs_without_alt[:10],
            },
            "forms": {
                "total_inputs": len(input_tags),
                "properly_labelled": len(aria_labelled_ids),
                "missing_labels": inputs_without_label[:10],
            },
            "color_contrast": {
                "issues_found": len(color_contrast_issues),
                "details": color_contrast_issues[:5],
            },
            "navigation": {
                "has_skip_nav": has_skip_nav or skip_nav_class,
                "landmarks": {
                    "main": has_main,
                    "nav": has_nav,
                    "banner": has_banner,
                    "coverage": f"{landmark_coverage}/3",
                },
            },
            "focus": {
                "has_focus_visible": has_focus_visible,
                "has_focus_styles": has_focus,
                "outline_removed": has_outline_none,
            },
            "motion": {
                "respects_reduced_motion": has_reduced_motion,
            },
            "heading_hierarchy": {
                "levels_found": heading_levels,
                "issues": heading_issues,
            },
            "has_lang_attribute": has_lang,
            "issues": issues,
            "passes": passes,
        }

    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float | None:
        """
        计算两个颜色之间的对比度比率（WCAG 2.1 算法）。

        Args:
            color1: 第一个颜色值（#hex 或 rgb()/rgba()）
            color2: 第二个颜色值（#hex 或 rgb()/rgba()）

        Returns:
            对比度比率，如果无法解析颜色则返回 None
        """
        import re

        def hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
            hex_str = hex_str.lstrip("#")
            if len(hex_str) == 3:
                hex_str = "".join(c * 2 for c in hex_str)
            if len(hex_str) == 6:
                return (
                    int(hex_str[0:2], 16),
                    int(hex_str[2:4], 16),
                    int(hex_str[4:6], 16),
                )
            if len(hex_str) == 8:
                return (
                    int(hex_str[0:2], 16),
                    int(hex_str[2:4], 16),
                    int(hex_str[4:6], 16),
                )
            return None

        def parse_rgb(color_str: str) -> tuple[int, int, int] | None:
            match = re.match(
                r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)",
                color_str,
            )
            if match:
                return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return None

        def parse_color(color_str: str) -> tuple[int, int, int] | None:
            color_str = color_str.strip()
            if color_str.startswith("#"):
                return hex_to_rgb(color_str)
            if color_str.startswith("rgb"):
                return parse_rgb(color_str)
            return None

        def relative_luminance(r: int, g: int, b: int) -> float:
            def srgb(c: int) -> float:
                s: float = c / 255.0
                if s <= 0.04045:
                    value = s / 12.92
                else:
                    value = ((s + 0.055) / 1.055) ** 2.4
                return float(value)

            return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)

        rgb1 = parse_color(color1)
        rgb2 = parse_color(color2)
        if rgb1 is None or rgb2 is None:
            return None

        l1 = relative_luminance(*rgb1)
        l2 = relative_luminance(*rgb2)
        lighter = max(l1, l2)
        darker = min(l1, l2)

        return round((lighter + 0.05) / (darker + 0.05), 2)

    # ------------------------------------------------------------------
    # Design Token Consistency Check
    # ------------------------------------------------------------------

    def _check_token_consistency(
        self,
        css_content: str,
        source_files: list[str] | None = None,
        tailwind_config: str = "",
    ) -> dict[str, Any]:
        """
        检查设计 Token 一致性：从 CSS 变量和 Tailwind 配置中提取 Token 定义，
        然后检查源代码中是否存在未使用 Token 的硬编码值。

        Args:
            css_content: CSS 文件内容（包含 :root 变量定义）
            source_files: 源文件内容列表（HTML/JSX/TSX/Vue 等）
            tailwind_config: tailwind.config.js/ts 文件内容（可选）

        Returns:
            包含 Token 一致性分析结果的字典
        """
        import re

        source_files = source_files or []
        issues: list[dict[str, str]] = []
        suggestions: list[str] = []

        # 1. Extract CSS custom property tokens
        css_tokens: dict[str, dict[str, str]] = {}
        var_pattern = re.compile(r"--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);")
        for match in var_pattern.finditer(css_content):
            name = match.group(1).strip()
            value = match.group(2).strip()
            category = self._categorize_token(name, value)
            css_tokens[name] = {"value": value, "category": category}

        # Categorize tokens
        color_tokens = {k: v for k, v in css_tokens.items() if v["category"] == "color"}
        spacing_tokens = {k: v for k, v in css_tokens.items() if v["category"] == "spacing"}
        typography_tokens = {k: v for k, v in css_tokens.items() if v["category"] == "typography"}
        radius_tokens = {k: v for k, v in css_tokens.items() if v["category"] == "radius"}
        shadow_tokens = {k: v for k, v in css_tokens.items() if v["category"] == "shadow"}
        other_tokens = {k: v for k, v in css_tokens.items() if v["category"] == "other"}

        # 2. Extract Tailwind config tokens
        tailwind_tokens: dict[str, list[str]] = {
            "colors": [],
            "spacing": [],
            "fontSize": [],
            "borderRadius": [],
            "boxShadow": [],
        }
        if tailwind_config:
            for category in tailwind_tokens:
                # Simple extraction from JS/TS config
                cat_pattern = re.compile(
                    rf"{category}\s*:\s*\{{([^}}]+)\}}",
                    re.DOTALL,
                )
                cat_match = cat_pattern.search(tailwind_config)
                if cat_match:
                    block = cat_match.group(1)
                    keys = re.findall(r"['\"]?([a-zA-Z0-9_-]+)['\"]?\s*:", block)
                    tailwind_tokens[category] = keys

        # 3. Check for hardcoded values in source files
        hardcoded_colors: list[dict[str, str]] = []
        hardcoded_fonts: list[dict[str, str]] = []
        hardcoded_spacing: list[dict[str, str]] = []
        hardcoded_radius: list[dict[str, str]] = []

        all_source = "\n".join(source_files)

        if all_source:
            # Check for inline hex colors not using tokens
            inline_hex = re.findall(
                r'(?:color|background|border|fill|stroke)\s*[:=]\s*["\']?(#[0-9a-fA-F]{3,8})',
                all_source,
            )
            token_color_values = {v["value"].lower() for v in color_tokens.values()}
            for hex_val in inline_hex:
                if hex_val.lower() not in token_color_values:
                    hardcoded_colors.append(
                        {
                            "value": hex_val,
                            "suggestion": self._find_closest_token(hex_val, color_tokens),
                        }
                    )

            # Check for inline font-family not using tokens
            inline_fonts = re.findall(
                r'font-?[Ff]amily\s*[:=]\s*["\']([^"\']+)',
                all_source,
            )
            for font in inline_fonts:
                if "var(--" not in font:
                    hardcoded_fonts.append({"value": font})

            # Check for inline pixel spacing not using tokens
            inline_spacing = re.findall(
                r'(?:margin|padding|gap)\s*[:=]\s*["\']?(\d+px)',
                all_source,
            )
            for sp in inline_spacing:
                hardcoded_spacing.append({"value": sp})

            # Check for inline border-radius
            inline_radius = re.findall(
                r'border-?[Rr]adius\s*[:=]\s*["\']?(\d+px)',
                all_source,
            )
            for rd in inline_radius:
                hardcoded_radius.append({"value": rd})

        if hardcoded_colors:
            issues.append(
                {
                    "severity": "medium",
                    "message": f"发现 {len(hardcoded_colors)} 个硬编码颜色值未使用 Token",
                    "fix": "将硬编码颜色替换为 var(--token-name) 或 Tailwind 语义类",
                }
            )
        if hardcoded_fonts:
            issues.append(
                {
                    "severity": "medium",
                    "message": f"发现 {len(hardcoded_fonts)} 个硬编码字体声明未使用 Token",
                    "fix": "将字体声明统一使用 var(--font-heading) / var(--font-body) Token",
                }
            )
        if hardcoded_spacing and spacing_tokens:
            issues.append(
                {
                    "severity": "low",
                    "message": f"发现 {len(hardcoded_spacing)} 个硬编码间距值，建议使用 Token 或 Tailwind 预设类",
                    "fix": "定义间距 Token 并统一引用",
                }
            )

        # 4. Token coverage analysis
        total_token_count = len(css_tokens)
        total_hardcoded = (
            len(hardcoded_colors)
            + len(hardcoded_fonts)
            + len(hardcoded_spacing)
            + len(hardcoded_radius)
        )
        token_usage_count = (
            len(re.findall(r"var\(--[a-zA-Z0-9_-]+\)", all_source)) if all_source else 0
        )
        coverage_ratio = round(
            token_usage_count / max(token_usage_count + total_hardcoded, 1),
            2,
        )

        # 5. Check token naming convention
        naming_issues: list[str] = []
        for token_name in css_tokens:
            # Check for semantic naming
            if re.match(r"^(color|bg|text|border|font|spacing|radius|shadow)-", token_name):
                continue  # Good semantic prefix
            if re.match(
                r"^(primary|secondary|accent|muted|surface|foreground|background|card|destructive|ring|input|chart)-?",
                token_name,
            ):
                continue  # Good semantic name
            if re.match(r"^(--)?[a-z]+-\d+$", token_name):
                naming_issues.append(f"--{token_name} 使用了数字后缀命名，建议使用语义化名称")

        if naming_issues:
            suggestions.append(
                f"发现 {len(naming_issues)} 个 Token 使用了非语义化命名，"
                "建议使用如 --color-primary、--spacing-lg 等语义前缀"
            )

        # 6. Check required token categories
        required_categories = {
            "color": "颜色 Token（primary/secondary/accent/background/text）",
            "typography": "字体 Token（font-family/font-size/font-weight/line-height）",
            "spacing": "间距 Token（spacing/gap/padding/margin 系列）",
            "radius": "圆角 Token（border-radius 系列）",
            "shadow": "阴影 Token（box-shadow 系列）",
        }
        missing_categories: list[str] = []
        for cat, desc in required_categories.items():
            count = len([v for v in css_tokens.values() if v["category"] == cat])
            if count == 0:
                missing_categories.append(desc)

        if missing_categories:
            issues.append(
                {
                    "severity": "medium",
                    "message": f"缺少以下类别的 Token 定义：{'、'.join(missing_categories)}",
                    "fix": "补充完整的设计 Token 体系，确保颜色、字体、间距、圆角、阴影全部覆盖",
                }
            )

        score = 100
        score -= min(len(hardcoded_colors) * 2, 20)
        score -= min(len(hardcoded_fonts) * 3, 15)
        score -= min(len(missing_categories) * 8, 24)
        score -= min(len(naming_issues) * 1, 10)
        score = max(0, min(100, score))

        return {
            "score": score,
            "grade": (
                "A"
                if score >= 90
                else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
            ),
            "token_inventory": {
                "total": total_token_count,
                "by_category": {
                    "color": len(color_tokens),
                    "typography": len(typography_tokens),
                    "spacing": len(spacing_tokens),
                    "radius": len(radius_tokens),
                    "shadow": len(shadow_tokens),
                    "other": len(other_tokens),
                },
            },
            "tailwind_tokens": {k: len(v) for k, v in tailwind_tokens.items() if v},
            "coverage": {
                "token_usage_count": token_usage_count,
                "hardcoded_value_count": total_hardcoded,
                "coverage_ratio": coverage_ratio,
            },
            "hardcoded_values": {
                "colors": hardcoded_colors[:10],
                "fonts": hardcoded_fonts[:10],
                "spacing": hardcoded_spacing[:10],
                "radius": hardcoded_radius[:10],
            },
            "missing_categories": missing_categories,
            "naming_issues": naming_issues[:10],
            "issues": issues,
            "suggestions": suggestions,
        }

    def _categorize_token(self, name: str, value: str) -> str:
        """根据 Token 名称和值推断其类别"""
        name_lower = name.lower()
        value_lower = value.lower().strip()

        # Color detection
        if any(
            kw in name_lower
            for kw in [
                "color",
                "primary",
                "secondary",
                "accent",
                "background",
                "bg",
                "foreground",
                "fg",
                "text",
                "muted",
                "border",
                "surface",
                "card",
                "destructive",
                "ring",
                "input",
                "chart",
                "stroke",
                "fill",
            ]
        ):
            return "color"
        if (
            value_lower.startswith("#")
            or value_lower.startswith("rgb")
            or value_lower.startswith("hsl")
        ):
            return "color"

        # Typography detection
        if any(
            kw in name_lower
            for kw in ["font", "text-size", "line-height", "letter-spacing", "heading", "body"]
        ):
            return "typography"

        # Spacing detection
        if any(
            kw in name_lower for kw in ["spacing", "gap", "padding", "margin", "space", "inset"]
        ):
            return "spacing"

        # Radius detection
        if any(kw in name_lower for kw in ["radius", "rounded", "corner"]):
            return "radius"

        # Shadow detection
        if any(kw in name_lower for kw in ["shadow", "elevation"]):
            return "shadow"

        return "other"

    def _find_closest_token(self, hex_color: str, color_tokens: dict[str, dict[str, str]]) -> str:
        """查找最接近的颜色 Token"""
        hex_color = hex_color.lstrip("#").lower()
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        if len(hex_color) != 6:
            return "(无法匹配)"

        r1, g1, b1 = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        best_name = ""
        best_distance = float("inf")

        for name, info in color_tokens.items():
            val = info["value"].lstrip("#").lower()
            if len(val) == 3:
                val = "".join(c * 2 for c in val)
            if len(val) != 6:
                continue
            r2, g2, b2 = int(val[:2], 16), int(val[2:4], 16), int(val[4:6], 16)
            distance = ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5
            if distance < best_distance:
                best_distance = distance
                best_name = name

        if best_name and best_distance < 80:
            return f"建议使用 var(--{best_name})"
        return "(无匹配 Token，请新建)"
