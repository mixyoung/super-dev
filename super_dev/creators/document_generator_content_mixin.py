"""DocumentGenerator content mixin helpers."""

from __future__ import annotations

import json
import logging

from .document_architecture_content_mixin import DocumentArchitectureContentMixin
from .document_delivery_content_mixin import DocumentDeliveryContentMixin
from .document_product_content_mixin import DocumentProductContentMixin
from .document_ui_content_mixin import DocumentUIContentMixin
from .requirement_parser import RequirementParser


class DocumentGeneratorContentMixin(
    DocumentProductContentMixin,
    DocumentArchitectureContentMixin,
    DocumentUIContentMixin,
    DocumentDeliveryContentMixin,
):
    requirement_parser: RequirementParser

    def _get_product_type_desc(self, product_type: str) -> str:
        """获取产品类型描述"""
        descs = {
            "saas": "SaaS 软件服务，需要专业可信的设计",
            "ecommerce": "电商平台，注重转化和购买体验",
            "landing": "营销落地页，强调 CTA 和转化",
            "dashboard": "管理后台，注重数据展示和操作效率",
            "content": "内容平台，注重阅读体验",
            "general": "通用产品",
        }
        return descs.get(product_type, "常规产品")

    def _get_industry_desc(self, industry: str) -> str:
        """获取行业描述"""
        descs = {
            "healthcare": "医疗健康行业，需要传递安全、专业感",
            "fintech": "金融科技，需要信任、安全的设计语言",
            "education": "教育行业，需要亲和力、专业性",
            "legal": "法律服务行业，需要权威、可信和清晰表达",
            "government": "政务/公共服务，需要高可读性与可访问性",
            "beauty": "美业/健康服务，需要品牌感、精致感与转化路径",
            "general": "通用行业",
        }
        return descs.get(industry, "常规行业")

    def _get_style_desc(self, style: str) -> str:
        """获取风格描述"""
        descs = {
            "minimal": "极简风格，去除冗余，突出核心",
            "professional": "专业风格，商务、正式",
            "playful": "活泼风格，有趣、生动",
            "luxury": "奢华风格，高端、精致",
            "modern": "现代风格，时尚、前沿",
        }
        return descs.get(style, "现代风格")

    def _lighten(self, hex_color: str, factor: float) -> str:
        """将颜色变浅"""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{min(r, 255):02X}{min(g, 255):02X}{min(b, 255):02X}"

    def _darken(self, hex_color: str, factor: float) -> str:
        """将颜色加深"""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{max(r, 0):02X}{max(g, 0):02X}{max(b, 0):02X}"

    def _generate_design_principles(self, analysis: dict) -> str:
        """生成领域定制的设计理念"""
        product_type = analysis.get("product_type", "general")

        principles = {
            "landing": [
                ("视觉叙事", "用截图、流程图和数据取代抽象描述，让用户在 5 秒内理解产品价值"),
                ("转化驱动", "每个滚动屏都有明确的信息目标和行动入口，避免空洞的装饰区块"),
                ("信任优先", "客户案例、数据指标、安全标识、合作品牌等信任元素贯穿全页"),
                ("品牌识别", "通过字体、配色、间距和排版节奏建立独特的品牌感，拒绝模板化"),
            ],
            "saas": [
                ("效率至上", "工作台和操作界面以任务完成效率为第一目标，减少页面跳转"),
                ("信息层级", "数据密度适中，关键指标突出，次要信息可折叠，避免信息过载"),
                ("状态透明", "每个操作都有明确的状态反馈（加载、成功、失败、空态），减少用户焦虑"),
                ("渐进展示", "新用户看到引导和简化视图，专业用户可切换到高级功能和密集布局"),
            ],
            "dashboard": [
                ("数据可读", "数据可视化以业务洞察为目标，不追求炫酷图表，确保一眼能读出结论"),
                ("操作直达", "从数据到操作的路径不超过 2 步，关键操作始终可见"),
                ("密度适配", "高密度信息区使用紧凑间距和小字号，操作区保持舒适的点击目标"),
                ("实时感知", "关键数据支持实时/近实时更新，状态变化有视觉提示"),
            ],
            "ecommerce": [
                ("购买信心", "高质量商品图、评价系统、价格对比和配送说明降低购买决策成本"),
                ("转化漏斗", "从浏览到下单的路径清晰顺畅，减少每一步的流失"),
                ("移动优先", "所有购买流程在手机端完整可用，拇指热区布局"),
                ("信任构建", "安全支付标识、退换政策、客服入口等信任元素始终可见"),
            ],
        }

        selected = principles.get(
            product_type,
            [
                (
                    "用户价值",
                    f"围绕{self.description[:30]}的核心场景设计，每个页面都服务于明确的用户目标",
                ),
                ("专业品质", "组件、间距、字体和配色体现成熟商业产品的品质感，拒绝粗糙和模板化"),
                ("一致体验", "跨页面的视觉语言、交互模式和信息架构保持统一"),
                ("渐进增强", "核心功能简洁直观，高级功能按需展开，不同用户有不同的最优体验路径"),
            ],
        )

        lines = []
        for title, desc in selected:
            lines.append(f"- **{title}**: {desc}")

        return "\n".join(lines)

    def _generate_component_library_guide(self, profile: dict) -> str:
        """生成组件库使用指南"""
        lib_name = profile.get("primary_library", {}).get("name", "shadcn/ui")

        if "shadcn" in lib_name.lower():
            return """**必装组件（MVP 基线）**:
```bash
npx shadcn@latest add button card input label select textarea badge avatar
npx shadcn@latest add dialog sheet dropdown-menu command toast sonner
npx shadcn@latest add table tabs separator skeleton scroll-area
```

**组合示例 - 页面头部**:
```tsx
<header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
  <div className="container flex h-14 items-center">
    <nav className="flex items-center space-x-6 text-sm font-medium">
      {/* 使用 cn() 管理条件样式 */}
    </nav>
    <div className="ml-auto flex items-center space-x-4">
      <Button variant="ghost" size="icon"><Bell className="h-4 w-4" /></Button>
      <Avatar><AvatarFallback>UN</AvatarFallback></Avatar>
    </div>
  </div>
</header>
```

**组合示例 - 数据卡片**:
```tsx
<Card className="group hover:shadow-md transition-all duration-200">
  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
    <CardTitle className="text-sm font-medium text-muted-foreground">总用户数</CardTitle>
    <Users className="h-4 w-4 text-muted-foreground" />
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold">12,345</div>
    <p className="text-xs text-muted-foreground">较上月 +12.5%</p>
  </CardContent>
</Card>
```

**组合示例 - 空态**:
```tsx
<div className="flex flex-col items-center justify-center py-12 text-center">
  <Inbox className="h-12 w-12 text-muted-foreground/50 mb-4" />
  <h3 className="text-lg font-medium">暂无数据</h3>
  <p className="text-sm text-muted-foreground mt-1 mb-4">当前没有可显示的内容</p>
  <Button>创建第一个</Button>
</div>
```

**图标库**: 统一使用 Lucide React (`lucide-react`)，禁止 emoji 替代。
**起步约束**: 进入页面实现前必须先锁定图标库，不允许“先用 emoji 顶上后面再换”。
"""
        elif "ant" in lib_name.lower():
            return """**主题定制（必须）**:
```typescript
// theme/index.ts
import type { ThemeConfig } from 'antd';

const theme: ThemeConfig = {
  token: {
    colorPrimary: 'var(--primary-500)',
    borderRadius: 8,
    fontFamily: "'Plus Jakarta Sans', 'Noto Sans SC', sans-serif",
    fontSize: 14,
    colorBgContainer: '#ffffff',
  },
  components: {
    Button: { controlHeight: 40, borderRadius: 8 },
    Card: { borderRadiusLG: 12, paddingLG: 24 },
    Input: { controlHeight: 40 },
  },
};
```

**禁止默认 Ant Design 风格直出**，必须重写 token 体系。
"""
        else:
            return """- 必须在项目初始化时重写 design token（颜色、间距、圆角、字体）
- 不允许使用组件库默认主题直接上线
- 所有交互组件必须有 hover/focus/active/disabled 四态
- 图标统一使用 Lucide / Heroicons，禁止 emoji
- 开始 UI 编码前先声明图标库，不允许临时用 emoji 占位
"""

    def _get_ui_intelligence(self, analysis: dict | None = None) -> dict:
        """获取结构化 UI Intelligence 推荐"""
        analysis = analysis or self._analyze_project_for_design()
        from super_dev.design import UIIntelligenceAdvisor

        advisor = UIIntelligenceAdvisor()
        return advisor.recommend(
            description=self.description,
            frontend=self.frontend,
            product_type=analysis["product_type"],
            industry=analysis["industry"],
            style=analysis["style"],
            ui_library=self.ui_library,
            preferred_design_reference_slug=getattr(self, "design_inspiration_slug", ""),
        )

    def _get_design_system_bundle(self, analysis: dict, profile: dict) -> dict:
        """把设计系统生成器的结果接入 UIUX 文档，而不是只停留在 CLI 里。"""
        try:
            from super_dev.design import DesignSystemGenerator

            generator = DesignSystemGenerator()
            keywords = list(
                dict.fromkeys(
                    [
                        analysis.get("style", "modern"),
                        analysis.get("product_type", "general"),
                        analysis.get("industry", "general"),
                        *profile.get("knowledge_keywords", []),
                    ]
                )
            )[:10]
            design_system = generator.generate(
                product_type=analysis.get("product_type", "general"),
                industry=analysis.get("industry", "general"),
                keywords=keywords,
                platform=self.platform,
            )
            return {
                "design_system": design_system,
                "css_variables_preview": "\n".join(
                    design_system.to_css_variables().splitlines()[:28]
                ),
                "tailwind_preview": json.dumps(
                    design_system.to_tailwind_config(), ensure_ascii=False, indent=2
                ),
            }
        except Exception as exc:
            logging.getLogger(__name__).warning("Design system bundle failed: %s", exc)
            return {"design_system": None, "css_variables_preview": "", "tailwind_preview": ""}

    def _build_ui_contract_payload(
        self, analysis: dict, profile: dict, design_bundle: dict | None = None
    ) -> dict:
        design_bundle = design_bundle or {}
        design_system = design_bundle.get("design_system")
        typography = profile.get("typography_preset", {})
        palette = profile.get("color_palette", {})
        stack = profile.get("component_stack", {})
        primary = profile.get("primary_library", {})
        icon_system = (
            stack.get("icon")
            or stack.get("icons")
            or profile.get("icon_system")
            or profile.get("icon_library")
            or primary.get("icon_system")
            or ""
        )
        screen_recipes = self._build_screen_recipes(analysis=analysis, profile=profile)
        design_context_protocol = self._build_design_context_protocol(
            analysis=analysis,
            profile=profile,
            screen_recipes=screen_recipes,
        )
        tweak_strategy = self._build_tweak_strategy(
            analysis=analysis,
            profile=profile,
            screen_recipes=screen_recipes,
        )
        verification_handoff = self._build_verification_handoff(
            analysis=analysis,
            profile=profile,
            screen_recipes=screen_recipes,
        )
        payload = {
            "analysis": {
                "product_type": analysis.get("product_type", "general"),
                "industry": analysis.get("industry", "general"),
                "style": analysis.get("style", "modern"),
                "platform": self.platform,
                "frontend": self.frontend,
                "design_inspiration_slug": getattr(self, "design_inspiration_slug", ""),
            },
            "style_direction": profile.get("style_direction", {}),
            "surface": profile.get("surface"),
            "information_density": profile.get("information_density"),
            "industry_tone": profile.get("industry_tone"),
            "primary_library": primary,
            "alternative_libraries": list(profile.get("alternative_libraries", [])),
            "component_stack": stack,
            "component_priorities": list(profile.get("component_priorities", [])),
            "design_system_priorities": list(profile.get("design_system_priorities", [])),
            "art_direction_candidates": list(profile.get("art_direction_candidates", [])),
            "design_direction_manifest": dict(profile.get("design_direction_manifest", {})),
            "brand_signal_manifest": dict(profile.get("brand_signal_manifest", {})),
            "proof_composition_rules": dict(profile.get("proof_composition_rules", {})),
            "component_craft_requirements": list(profile.get("component_craft_requirements", [])),
            "layout_tension_rules": list(profile.get("layout_tension_rules", [])),
            "anti_ai_slop_guardrails": dict(profile.get("anti_ai_slop_guardrails", {})),
            "critique_rubric": list(profile.get("critique_rubric", [])),
            "tweak_categories": list(profile.get("tweak_categories", [])),
            "state_requirements": list(profile.get("state_requirements", [])),
            "quality_checklist": list(profile.get("quality_checklist", [])),
            "banned_patterns": list(profile.get("banned_patterns", [])),
            "knowledge_keywords": list(profile.get("knowledge_keywords", [])),
            "design_references": list(profile.get("design_references", [])),
            "selected_design_reference": profile.get("selected_design_reference"),
            "framework_playbook": profile.get("framework_playbook"),
            "color_palette": palette,
            "typography_preset": typography,
            "icon_system": icon_system,
            "emoji_policy": {
                "allowed_in_ui": False,
                "allowed_as_icon": False,
                "allowed_during_development": False,
                "rule": "绝对不允许 emoji 表情作为图标，也不允许在 UI 开发过程中使用 emoji 充当占位、临时装饰或功能按钮。",
                "approved_icon_libraries": [
                    "Lucide",
                    "Heroicons",
                    "Tabler Icons",
                    "官方组件图标库",
                ],
                "enforcement": "system-wide",
            },
            "ui_library_preference": {
                "preferred": (
                    "shadcn/ui + Radix UI + Tailwind CSS"
                    if self.frontend in {"react", "next", "nextjs", "web"}
                    and self.platform in {"web", "desktop", "saas", "landing"}
                    else primary.get("name")
                ),
                "strict": False,
                "decision_rule": (
                    "React/Web 场景优先偏向 shadcn/ui + Radix + Tailwind；"
                    "但若既有设计系统、平台特性、团队生态或页面类型存在更合适方案，应由宿主选择更合适的组件生态，并把最终选择回写到 UIUX 文档。"
                ),
                "final_selected": primary.get("name"),
            },
            "design_tokens": {
                "css_variables": design_bundle.get("css_variables_preview", ""),
                "tailwind_theme": design_bundle.get("tailwind_preview", ""),
            },
            "screen_recipes": screen_recipes,
            "design_context_protocol": design_context_protocol,
            "tweak_strategy": tweak_strategy,
            "verification_handoff": verification_handoff,
        }
        if design_system is not None:
            payload["generated_design_system"] = {
                "name": getattr(design_system, "name", ""),
                "description": getattr(design_system, "description", ""),
                "colors": getattr(design_system, "colors", {}),
                "typography": getattr(design_system, "typography", {}),
                "spacing": getattr(design_system, "spacing", {}),
                "shadows": getattr(design_system, "shadows", {}),
                "radius": getattr(design_system, "radius", {}),
                "animations": getattr(design_system, "animations", {}),
                "components": getattr(design_system, "components", {}),
            }
            aesthetic = getattr(design_system, "aesthetic", None)
            if aesthetic is not None:
                payload["generated_design_system"]["aesthetic"] = {
                    "name": getattr(aesthetic, "name", ""),
                    "description": getattr(aesthetic, "description", ""),
                    "differentiation": getattr(aesthetic, "differentiation", ""),
                    "typography": {
                        "display": getattr(getattr(aesthetic, "typography", None), "display", ""),
                        "body": getattr(getattr(aesthetic, "typography", None), "body", ""),
                    },
                }
        return payload

    def _build_screen_recipes(self, analysis: dict, profile: dict) -> list[dict]:
        product_type = str(analysis.get("product_type") or "general").lower()
        surface = str(profile.get("surface") or "商业级界面")
        density = str(profile.get("information_density") or "medium")
        trust_modules = list(profile.get("trust_modules", []))
        state_requirements = list(profile.get("state_requirements", []))
        component_priorities = list(profile.get("component_priorities", []))
        _direction_manifest_value = profile.get("design_direction_manifest")
        direction_manifest = (
            _direction_manifest_value if isinstance(_direction_manifest_value, dict) else {}
        )
        _anti_guardrails_value = profile.get("anti_ai_slop_guardrails")
        anti_guardrails = _anti_guardrails_value if isinstance(_anti_guardrails_value, dict) else {}
        _tweak_categories_value = profile.get("tweak_categories")
        tweak_categories = (
            _tweak_categories_value if isinstance(_tweak_categories_value, list) else []
        )
        _selected_reference_value = profile.get("selected_design_reference")
        selected_reference = (
            _selected_reference_value if isinstance(_selected_reference_value, dict) else {}
        )
        reference_name = selected_reference.get("name") or "设计参考锚点"
        selected_direction = direction_manifest.get("selected_direction") or "Modern Commercial"
        narrative_mode = direction_manifest.get("narrative_mode") or "先价值、再证明、后功能展开"
        visual_tension = (
            direction_manifest.get("visual_tension") or "通过层级、留白和重点色建立张力"
        )
        density_tempo = direction_manifest.get("density_tempo") or density
        anti_cliches = list(anti_guardrails.get("forbidden_motifs", []))[:3]
        _proof_rules_value = profile.get("proof_composition_rules")
        proof_rules = _proof_rules_value if isinstance(_proof_rules_value, dict) else {}
        _layout_tension_rules_value = profile.get("layout_tension_rules")
        layout_tension_rules = (
            _layout_tension_rules_value if isinstance(_layout_tension_rules_value, list) else []
        )

        def recipe(
            recipe_id: str,
            label: str,
            objective: str,
            section_order: list[str],
            components: list[str],
            trust_slice: list[str],
            states: list[str],
            variation_axes: list[str],
            starter: list[str],
        ) -> dict:
            return {
                "id": recipe_id,
                "label": label,
                "surface": surface,
                "information_density": density,
                "objective": objective,
                "section_order": section_order,
                "component_focus": components,
                "trust_modules": trust_slice,
                "required_states": states,
                "variation_axes": variation_axes,
                "starter_components": starter,
                "design_reference": reference_name,
                "art_direction": selected_direction,
                "narrative_mode": narrative_mode,
                "visual_tension": visual_tension,
                "density_tempo": density_tempo,
                "proof_composition": proof_rules.get("hero_proof_stack", [])[:4],
                "layout_tension_rules": layout_tension_rules[:3],
                "anti_cliche_bans": anti_cliches,
            }

        common_variations = [
            "信息密度（compact / balanced / spacious）",
            "强调方式（editorial headline / product proof / conversion CTA）",
            "品牌质感（neutral / premium / technical accent）",
        ]
        for category in tweak_categories[:2]:
            if not isinstance(category, dict):
                continue
            label = str(category.get("label") or category.get("name") or "").strip()
            if label and label not in common_variations:
                common_variations.append(label)
        common_states = state_requirements[:4] or ["loading", "empty", "error", "success"]
        trust_slice = trust_modules[:4] or ["案例", "安全", "FAQ", "指标"]

        if product_type in {"landing", "saas"}:
            return [
                recipe(
                    "north-star",
                    "North Star Hero",
                    "首屏必须同时讲清价值主张、可信证据与下一步动作，而不是只放大标题。",
                    ["hero", "proof bar", "product visual", "primary CTA"],
                    component_priorities[:4] or ["hero", "cta", "metrics", "feature card"],
                    trust_slice,
                    common_states,
                    common_variations,
                    ["browser-window", "trust-band", "metric-strip"],
                ),
                recipe(
                    "workflow-proof",
                    "Workflow Proof",
                    "用真实流程、模块编排和结果反馈证明产品不是概念图，而是可工作的系统。",
                    ["workflow map", "capability clusters", "before/after", "evidence rail"],
                    component_priorities[1:5] or ["timeline", "panel", "table", "command area"],
                    trust_slice,
                    common_states,
                    [
                        "布局节奏（stacked / split / rail）",
                        "证明方式（截图 / metrics / checklist）",
                    ],
                    ["design-canvas", "browser-window"],
                ),
                recipe(
                    "conversion-closure",
                    "Conversion Closure",
                    "结尾区域要完成 FAQ、案例、合规与 CTA 收口，避免只有功能列表没有转化闭环。",
                    ["case study", "faq", "pricing or offer", "final CTA"],
                    component_priorities[:3] or ["testimonial", "faq", "cta"],
                    trust_modules[:6] or trust_slice,
                    common_states[:2],
                    [
                        "转化风格（soft / assertive）",
                        "信任权重（metrics / testimonial / compliance）",
                    ],
                    ["trust-band", "faq-stack"],
                ),
            ]

        if product_type in {"dashboard", "content"}:
            return [
                recipe(
                    "workspace-overview",
                    "Workspace Overview",
                    "主屏需要先建立导航骨架、关键状态和信息优先级，避免退化成内容堆叠板。",
                    ["navigation shell", "summary row", "primary work area", "secondary rail"],
                    component_priorities[:5]
                    or ["sidebar", "topbar", "table", "chart", "detail panel"],
                    trust_slice,
                    common_states,
                    common_variations,
                    ["app-shell", "metric-strip"],
                ),
                recipe(
                    "detail-flow",
                    "Detail & Action Flow",
                    "详情区要同时支持阅读、编辑和反馈，确保关键任务可以在一个清晰路径里完成。",
                    ["detail header", "tabs or split", "activity trail", "sticky actions"],
                    component_priorities[1:6]
                    or ["detail header", "tabs", "form", "history", "action footer"],
                    trust_slice[:3],
                    common_states,
                    ["详情布局（tabs / split / inspector）", "操作模式（inline / modal / drawer）"],
                    ["app-shell", "detail-rail"],
                ),
                recipe(
                    "operational-proof",
                    "Operational Proof",
                    "用审计、状态矩阵和恢复能力证明系统可靠，而不是只展示好看的卡片。",
                    ["audit summary", "status matrix", "evidence cards", "recovery cues"],
                    component_priorities[:4] or ["status card", "timeline", "badge", "log rail"],
                    trust_modules[:5] or trust_slice,
                    common_states,
                    ["证据强度（light / strong）", "审计密度（compact / expanded）"],
                    ["design-canvas", "audit-rail"],
                ),
            ]

        return [
            recipe(
                "brand-frame",
                "Brand Frame",
                "先建立品牌语气、字体层级与核心页面骨架，避免默认模板化壳层。",
                ["hero", "capability blocks", "proof", "cta"],
                component_priorities[:4] or ["hero", "feature card", "proof", "cta"],
                trust_slice,
                common_states,
                common_variations,
                ["design-canvas", "browser-window"],
            ),
            recipe(
                "core-journey",
                "Core Journey",
                "把最关键的用户旅程拆成 3-4 个高保真步骤，而不是泛化展示一堆功能点。",
                ["entry", "main action", "feedback", "completion"],
                component_priorities[:4] or ["form", "cta", "state", "summary"],
                trust_slice[:3],
                common_states,
                ["流程深度（fast lane / guided）", "反馈强度（minimal / explicit）"],
                ["browser-window", "design-canvas"],
            ),
        ]

    def _build_design_context_protocol(
        self,
        *,
        analysis: dict,
        profile: dict,
        screen_recipes: list[dict],
    ) -> dict:
        frontend = str(analysis.get("frontend") or self.frontend or "web")
        design_references = profile.get("design_references", [])
        _selected_reference_value = profile.get("selected_design_reference")
        selected_reference = (
            _selected_reference_value if isinstance(_selected_reference_value, dict) else {}
        )
        reference_signal = selected_reference.get("name") or (
            design_references[0].get("name") if design_references else "设计参考锚点"
        )
        starter_components = []
        for recipe in screen_recipes:
            for item in recipe.get("starter_components", []):
                if item not in starter_components:
                    starter_components.append(item)

        return {
            "goal": "先吸收真实品牌、代码和组件上下文，再进入页面实现；禁止只凭记忆或截图猜 UI。",
            "required_sources": [
                "output/*-uiux.md",
                "output/*-ui-contract.json",
                "现有代码中的主题 token / 布局骨架 / 组件实现",
                "必要时补充截图、Figma 或真实产品链接",
            ],
            "preferred_import_order": [
                "主题 token / variables / theme 文件",
                "关键页面或组件源码",
                "全局样式与 layout scaffold",
                "补充截图与品牌物料",
            ],
            "github_import_targets": [
                "theme.ts / colors.ts / tokens.css / variables.scss",
                "layout / app shell / navigation components",
                "用户明确点名的页面和模块",
            ],
            "fidelity_rules": [
                f"优先复用 {reference_signal} 的可吸收信号，但必须转化为原创组合，而不是 1:1 复刻。",
                f"实现时必须围绕已选视觉哲学「{profile.get('design_direction_manifest', {}).get('selected_direction', '主方向')}」统一 hero、证据与内容节奏，禁止混搭多个热门风格。",
                "实现时先读真实代码与设计 token，再写页面；禁止只看文件名或只凭经验回忆。",
                "所有页面必须围绕 screen recipes 组织 section order、trust modules 与 state coverage。",
            ],
            "starter_components": starter_components[:5],
            "single_source_rule": "统一以一个主原型 / 主页面承载 Tweaks 和变体，减少多份分叉页面。",
            "frontend_target": frontend,
        }

    def _build_tweak_strategy(
        self,
        *,
        analysis: dict,
        profile: dict,
        screen_recipes: list[dict],
    ) -> dict:
        variation_axes: list[str] = []
        for recipe in screen_recipes:
            for axis in recipe.get("variation_axes", []):
                if axis not in variation_axes:
                    variation_axes.append(axis)
        _tweak_categories_value = profile.get("tweak_categories")
        tweak_categories = (
            _tweak_categories_value if isinstance(_tweak_categories_value, list) else []
        )
        return {
            "mode": "single-source prototype with tweakable variations",
            "panel_title": "Tweaks",
            "preferred_placement": "floating panel or inline handles, hidden in final view",
            "default_controls": variation_axes[:6]
            or [
                "信息密度",
                "标题张力",
                "品牌强调色",
                "CTA 风格",
            ],
            "persistence_rule": "变体默认值应可序列化并持久化，避免每次刷新丢失。",
            "selection_rule": "关键页面至少保留主方案 + 备选方案，不建议把所有变化拆成多份静态文件。",
            "screen_targets": [item.get("label", "") for item in screen_recipes[:3]],
            "categories": tweak_categories[:3],
        }

    def _build_verification_handoff(
        self,
        *,
        analysis: dict,
        profile: dict,
        screen_recipes: list[dict],
    ) -> dict:
        frontend = str(analysis.get("frontend") or self.frontend or "web")
        _critique_rubric_value = profile.get("critique_rubric")
        critique_rubric = _critique_rubric_value if isinstance(_critique_rubric_value, list) else []
        return {
            "verification_order": [
                "preview loads cleanly",
                "design tokens are wired",
                "screen recipes are represented in the preview",
                "375 / 768 / 1440 breakpoint review",
                "ui review + runtime evidence refresh",
            ],
            "required_artifacts": [
                "output/frontend/index.html",
                "output/frontend/styles.css",
                "output/frontend/design-tokens.css",
                "output/*-ui-contract-alignment.json",
                "output/*-frontend-runtime.json",
                "output/*-ui-review.md",
            ],
            "acceptance_checks": [
                "无 emoji 图标与聊天式壳层复刻",
                "关键页面覆盖 trust modules 与 state requirements",
                "主页面结构与 screen recipes 一致",
                "主题入口、导航骨架和组件生态接线清晰",
                "设计哲学、视觉层级、细节工艺、功能性与原创度五维评分均达标",
            ],
            "implementation_handoff": [
                f"frontend={frontend}",
                "冻结后的 ui-contract 作为实现真源",
                "UI review / runtime / quality gate 作为收尾证据链",
            ],
            "screen_targets": [item.get("id", "") for item in screen_recipes],
            "critique_targets": [
                str(item.get("label") or item.get("dimension") or "").strip()
                for item in critique_rubric[:5]
                if isinstance(item, dict)
            ],
        }

    def _get_state_management(self) -> str:
        """获取状态管理方案"""
        mapping = {
            "react": "Redux Toolkit / Zustand",
            "vue": "Pinia",
            "angular": "NgRx",
            "svelte": "Svelte Stores",
        }
        return mapping.get(self.frontend, "Context API")

    def _get_ui_library(self) -> str:
        """获取 UI 库"""
        name = self._get_ui_intelligence()["primary_library"]["name"]
        if not isinstance(name, str):
            raise ValueError("UI 库名称必须是文本")
        return name

    def _get_build_tool(self) -> str:
        """获取构建工具"""
        mapping = {
            "react": "Vite",
            "vue": "Vite",
            "angular": "Angular CLI",
            "svelte": "Vite",
        }
        return mapping.get(self.frontend, "Webpack")

    def _get_backend_framework(self) -> str:
        """获取后端框架"""
        mapping = {
            "node": "Express / Fastify / NestJS",
            "python": "FastAPI / Django",
            "go": "Gin / Echo",
            "java": "Spring Boot",
            "rust": "Actix Web / Axum",
            "php": "Laravel / Symfony",
            "ruby": "Rails / Sinatra",
            "csharp": "ASP.NET Core",
            "kotlin": "Ktor / Spring Boot",
            "swift": "Vapor",
            "elixir": "Phoenix",
            "scala": "Play / Akka HTTP",
            "dart": "Shelf / Dart Frog",
        }
        return mapping.get(self.backend, "Express")

    def _get_database(self) -> str:
        """获取数据库"""
        return "PostgreSQL 14+"

    def _get_orm(self) -> str:
        """获取 ORM"""
        mapping = {
            "node": "Prisma / TypeORM",
            "python": "SQLAlchemy / Django ORM",
            "go": "GORM",
            "java": "Hibernate / JPA",
            "rust": "SeaORM / Diesel",
            "php": "Eloquent / Doctrine",
            "ruby": "Active Record",
            "csharp": "Entity Framework Core",
            "kotlin": "Exposed / Spring Data JPA",
            "swift": "Fluent",
            "elixir": "Ecto",
            "scala": "Slick / Doobie",
            "dart": "Drift / Prisma Client Dart",
        }
        return mapping.get(self.backend, "Prisma")

    def _get_file_storage(self) -> str:
        """获取文件存储"""
        return "AWS S3 / 阿里云 OSS"

    def _generate_ai_ml_stack(self) -> str:
        """生成 AI/ML 技术栈部分"""
        keywords = self._extract_tech_keywords()

        # 检查是否有任何 AI/ML 相关技术
        has_ai_content = any(
            [
                keywords["ai_frameworks"],
                keywords["agent_tools"],
                keywords["ml_libraries"],
                keywords["vector_stores"],
                keywords["orchestration"],
                keywords["other_keywords"],
            ]
        )

        if not has_ai_content:
            return ""  # 如果没有 AI/ML 内容，返回空字符串

        # 构建 AI/ML 技术栈部分
        lines = ["### 2.2.1 AI/ML 技术栈", "", "| 层级 | 技术选型 | 说明 |", "|:---|:---|:---|"]

        # AI 框架
        if keywords["ai_frameworks"]:
            for framework in keywords["ai_frameworks"]:
                lines.append(f"| **AI 框架** | {framework} | Agent 编排与开发 |")

        # Agent 工具
        if keywords["agent_tools"]:
            for tool in keywords["agent_tools"]:
                lines.append(f"| **Agent 工具** | {tool} | Agent 构建与管理 |")

        # ML 库
        if keywords["ml_libraries"]:
            for lib in keywords["ml_libraries"]:
                lines.append(f"| **ML 库** | {lib} | 机器学习模型 |")

        # 向量数据库
        if keywords["vector_stores"]:
            for store in keywords["vector_stores"]:
                lines.append(f"| **向量数据库** | {store} | 向量存储与检索 |")

        # 编排工具
        if keywords["orchestration"]:
            for tool in keywords["orchestration"]:
                lines.append(f"| **编排工具** | {tool} | 工作流编排 |")

        # 其他关键词
        if keywords["other_keywords"]:
            for keyword in keywords["other_keywords"]:
                lines.append(f"| **核心能力** | {keyword} | 关键技术特性 |")

        lines.append("")
        return "\n".join(lines)

    # ========== Architecture Document Methods ==========

    # ========== UI/UX Document Methods ==========
