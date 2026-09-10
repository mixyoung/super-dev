"""Typography, stack, component and interaction catalogs."""

from __future__ import annotations

from .ui_intelligence_models import (
    LibraryRecommendation,
)


class UIIntelligenceStackCatalogMixin:
    PRODUCT_TYPOGRAPHY_PRESETS: dict[str, dict[str, str]] = {
        "saas": {
            "heading": "Manrope",
            "body": "Source Sans 3",
            "mood": "professional, clear, product-focused",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Manrope:wght@500;600;700;800&family=Source+Sans+3:wght@400;500;600&display=swap');",
        },
        "ecommerce": {
            "heading": "DM Sans",
            "body": "Inter",
            "mood": "friendly, approachable, trustworthy",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=DM+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');",
        },
        "ecommerce-luxury": {
            "heading": "Cormorant Garamond",
            "body": "Montserrat",
            "mood": "elegant, luxury, sophisticated",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Montserrat:wght@300;400;500;600&display=swap');",
        },
        "fintech": {
            "heading": "Space Grotesk",
            "body": "IBM Plex Sans",
            "mood": "technical, trustworthy, precise",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');",
        },
        "healthcare": {
            "heading": "Plus Jakarta Sans",
            "body": "Nunito Sans",
            "mood": "calming, professional, accessible",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Nunito+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');",
        },
        "education": {
            "heading": "Outfit",
            "body": "Source Sans 3",
            "mood": "clear, friendly, encouraging",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Outfit:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600&display=swap');",
        },
        "gaming": {
            "heading": "Rajdhani",
            "body": "Exo 2",
            "mood": "bold, energetic, futuristic",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Exo+2:wght@400;500;600;700&family=Rajdhani:wght@500;600;700&display=swap');",
        },
        "beauty-spa": {
            "heading": "Cormorant Garamond",
            "body": "Montserrat",
            "mood": "elegant, calming, sophisticated",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Montserrat:wght@300;400;500;600&display=swap');",
        },
        "content": {
            "heading": "Merriweather",
            "body": "Source Sans 3",
            "mood": "readable, editorial, classic",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Merriweather:wght@400;700&family=Source+Sans+3:wght@400;500;600&display=swap');",
        },
        "dashboard": {
            "heading": "IBM Plex Sans",
            "body": "Public Sans",
            "mood": "dense, operational, precise",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=IBM+Plex+Sans:wght@500;600;700&family=Public+Sans:wght@400;500;600&display=swap');",
        },
        "portfolio": {
            "heading": "Space Grotesk",
            "body": "Inter",
            "mood": "creative, distinctive, modern",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');",
        },
        "landing": {
            "heading": "Space Grotesk",
            "body": "DM Sans",
            "mood": "confident, distinctive, conversion-focused",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=DM+Sans:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');",
        },
        "social-media": {
            "heading": "Poppins",
            "body": "Open Sans",
            "mood": "modern, friendly, social",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Open+Sans:wght@400;500;600&family=Poppins:wght@400;500;600;700&display=swap');",
        },
        "restaurant": {
            "heading": "Playfair Display",
            "body": "Lato",
            "mood": "warm, appetizing, inviting",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Lato:wght@400;700&family=Playfair+Display:wght@400;500;600;700&display=swap');",
        },
        "real-estate": {
            "heading": "DM Serif Display",
            "body": "DM Sans",
            "mood": "premium, trustworthy, established",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');",
        },
        "legal": {
            "heading": "EB Garamond",
            "body": "Source Sans 3",
            "mood": "authoritative, traditional, trustworthy",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=EB+Garamond:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600&display=swap');",
        },
        "general": {
            "heading": "Manrope",
            "body": "Source Sans 3",
            "mood": "modern, professional, adaptable",
            "css_import": "@import url('https://fonts.googleapis.cn/css2?family=Manrope:wght@500;600;700;800&family=Source+Sans+3:wght@400;500;600&display=swap');",
        },
    }

    PRE_DELIVERY_CHECKLIST: list[str] = [
        "SVG 图标替代所有 emoji（使用 Lucide/Heroicons/Tabler）",
        "所有可点击元素具有 cursor-pointer",
        "hover 状态使用 150-300ms 平滑过渡",
        "浅色模式文字对比度至少 4.5:1（WCAG AA）",
        "focus 状态对键盘导航可见",
        "尊重 prefers-reduced-motion 偏好设置",
        "响应式断点覆盖：375px / 768px / 1024px / 1440px",
        "深色模式文字对比度至少 4.5:1（如适用）",
        "按钮和输入框高度一致（40px 基线）",
        "卡片圆角统一（8-12px）",
        "loading/empty/error/disabled 状态完整",
        "品牌字体已加载，无系统字体回退直出",
    ]

    STACK_RECOMMENDATIONS: dict[str, list[LibraryRecommendation]] = {
        "react": [
            LibraryRecommendation(
                name="shadcn/ui + Radix UI + Tailwind CSS",
                category="Primary",
                rationale="适合需要现代品牌感、可定制组件和商业级页面控制力的 React/Next 项目。",
                strengths=[
                    "组件骨架成熟，适合快速搭建高质量产品界面",
                    "与设计 token、主题系统、品牌定制兼容性强",
                    "便于结合 TanStack Table、React Hook Form、Zod 形成完整前端基线",
                    "可与 Aceternity UI / Magic UI 的视觉模块组合，提升品牌差异化表现",
                ],
                notes=[
                    "必须先定义 token、容器、字重和信息密度，再批量生成组件",
                    "表单建议配合 React Hook Form + Zod",
                    "视觉特效组件仅用于首屏叙事与反馈，避免影响可读性和性能",
                ],
            ),
            LibraryRecommendation(
                name="Ant Design",
                category="Alternative",
                rationale="适合 B 端后台、运营系统和高密度表格工作台。",
                strengths=[
                    "表格、表单、数据录入和后台模式成熟",
                    "适合中后台快速交付和复杂管理流程",
                ],
                notes=[
                    "品牌化和高级感需要额外主题定制，避免默认 Ant 风格直出",
                ],
            ),
            LibraryRecommendation(
                name="DaisyUI + Tailwind CSS",
                category="Alternative",
                rationale="适合多主题业务和快速产出高一致性视觉。",
                strengths=[
                    "主题切换能力强，适合白标与多品牌场景",
                    "与 Tailwind 兼容，开发效率高",
                ],
                notes=[
                    "需要补充高级组件与版式体系，避免默认主题观感",
                ],
            ),
            LibraryRecommendation(
                name="Aceternity UI / Magic UI",
                category="Alternative",
                rationale="适合官网、品牌页和叙事型 landing，增强视觉张力。",
                strengths=[
                    "高质量视觉模块与动效资源丰富",
                    "可快速构建有辨识度的商业首屏",
                ],
                notes=[
                    "必须设置性能预算并搭配可读性审查，避免炫技化",
                ],
            ),
            LibraryRecommendation(
                name="NextUI + Tailwind CSS",
                category="Alternative",
                rationale="适合需要现代感与动效且开发效率优先的 React/Next 项目。",
                strengths=[
                    "内置 Framer Motion 动效，开箱即用的过渡与微交互",
                    "组件视觉精美，深色模式支持优秀",
                    "与 Tailwind CSS 深度集成，定制灵活",
                ],
                notes=[
                    "组件库仍在快速迭代中，注意版本兼容",
                    "大型表格和复杂表单场景需要补充 TanStack Table 等",
                ],
            ),
            LibraryRecommendation(
                name="MUI (Material UI)",
                category="Alternative",
                rationale="适合大型企业应用和需要完整组件覆盖的 React 项目。",
                strengths=[
                    "组件覆盖最全（60+），文档完善，社区庞大",
                    "Material Design 3 主题系统成熟，token 化能力强",
                    "Data Grid、Date Picker 等高级组件企业级可用",
                ],
                notes=[
                    "包体较大，需要 tree-shaking 优化",
                    "默认 Material 风格强烈，品牌化需要大量主题覆盖",
                ],
            ),
            LibraryRecommendation(
                name="Mantine",
                category="Alternative",
                rationale="适合全栈 React 项目和需要丰富 hooks 与工具库的场景。",
                strengths=[
                    "100+ 组件 + 50+ hooks，功能覆盖极广",
                    "内置表单管理、通知系统、富文本编辑器",
                    "深色模式和主题定制体验优秀",
                ],
                notes=[
                    "样式方案与 Tailwind 并行使用时需要协调",
                    "更新频率高，大版本升级需关注 breaking changes",
                ],
            ),
            LibraryRecommendation(
                name="Chakra UI",
                category="Alternative",
                rationale="适合重视可访问性和开发体验的 React 项目。",
                strengths=[
                    "无障碍性（A11y）开箱即用，符合 WAI-ARIA",
                    "Style Props 系统直观，开发效率高",
                    "主题系统灵活，支持语义化 token",
                ],
                notes=[
                    "运行时 CSS-in-JS 有性能开销，SSR 场景需注意",
                    "组件视觉相对朴素，品牌化需要额外设计投入",
                ],
            ),
            LibraryRecommendation(
                name="Headless UI + Tailwind CSS",
                category="Alternative",
                rationale="适合对视觉完全自主控制、不想受组件库风格限制的项目。",
                strengths=[
                    "完全无样式的交互组件，视觉 100% 由开发者定义",
                    "由 Tailwind Labs 官方维护，与 Tailwind 完美集成",
                    "无障碍性内置，键盘导航和 ARIA 支持完善",
                ],
                notes=[
                    "组件数量有限（~15 个），复杂场景需要自建组件",
                    "适合有设计能力的团队，纯开发团队上手成本较高",
                ],
            ),
            LibraryRecommendation(
                name="Tremor + Tailwind CSS",
                category="Alternative",
                rationale="适合数据仪表板和 KPI 展示型产品，开箱即用的图表与指标组件。",
                strengths=[
                    "专为 Dashboard 设计，KPI 卡片/图表/列表组件即开即用",
                    "与 Recharts 深度集成，数据可视化能力强",
                    "Tailwind 原生，主题定制简单",
                ],
                notes=[
                    "仅适合数据展示场景，不适合通用 UI",
                    "组件数量有限，营销页和表单场景需要搭配其他库",
                ],
            ),
            LibraryRecommendation(
                name="Park UI + Ark UI",
                category="Alternative",
                rationale="适合需要跨框架一致性（React/Vue/Solid）的设计系统项目。",
                strengths=[
                    "基于 Ark UI 的 headless 层，支持 React/Vue/Solid 三框架",
                    "预设主题精美，视觉质量高",
                    "Panda CSS 集成，token 化设计系统",
                ],
                notes=[
                    "生态相对新，社区资源不如 shadcn/MUI 丰富",
                    "需要了解 Panda CSS 的工作方式",
                ],
            ),
            LibraryRecommendation(
                name="Arco Design React",
                category="Alternative",
                rationale="适合追求现代感中后台的 React 项目，字节跳动出品。",
                strengths=[
                    "60+ 组件覆盖，视觉比 Ant Design 更现代精致",
                    "暗色模式和主题定制开箱即用",
                    "IconBox 和插画资源丰富",
                ],
                notes=[
                    "社区不如 Ant Design 庞大，但组件质量高",
                ],
            ),
            LibraryRecommendation(
                name="Ant Design Mobile",
                category="Alternative",
                rationale="适合 H5 移动端和混合 APP 的 React 项目。",
                strengths=[
                    "移动端交互模式成熟（下拉刷新、滑动、手势）",
                    "与 Ant Design 桌面版设计语言统一",
                    "高性能虚拟列表和懒加载内置",
                ],
                notes=[
                    "仅适合移动端/H5，不适合桌面端",
                ],
            ),
            LibraryRecommendation(
                name="Semi Design",
                category="Alternative",
                rationale="适合追求设计工程化和主题定制的 React 项目，抖音出品。",
                strengths=[
                    "DSM（Design to Code）设计工程化能力强",
                    "2800+ Design Token，主题定制粒度极细",
                    "A11y 优先，WAI-ARIA 支持完善",
                ],
                notes=[
                    "国际化社区较小，中文生态为主",
                ],
            ),
            LibraryRecommendation(
                name="TDesign React",
                category="Alternative",
                rationale="适合遵循腾讯设计规范的 React 项目。",
                strengths=[
                    "腾讯官方设计系统，组件覆盖完整",
                    "与 TDesign 小程序版设计语言统一，适合跨端一致性",
                    "Starter Kit 开箱即用",
                ],
                notes=[
                    "主要面向腾讯生态，外部社区较小",
                ],
            ),
        ],
        "vue": [
            LibraryRecommendation(
                name="Naive UI + Tailwind CSS",
                category="Primary",
                rationale="适合现代 Vue 商业产品，兼顾组件成熟度与品牌化能力。",
                strengths=[
                    "适合 SaaS、工作台和中后台混合场景",
                    "主题覆盖能力较好",
                ],
                notes=[
                    "信息密度和主题层级要先定，不要直接套默认皮肤",
                ],
            ),
            LibraryRecommendation(
                name="Element Plus",
                category="Alternative",
                rationale="适合中文团队和中后台交付效率场景。",
                strengths=[
                    "表单、表格、弹窗、树形控件成熟",
                    "适合高频业务录入流程",
                ],
                notes=[
                    "默认视觉较强，需要定制字体、间距和色彩来避免模板感",
                ],
            ),
            LibraryRecommendation(
                name="Ant Design Vue",
                category="Alternative",
                rationale="适合中后台系统和中文团队的 Vue 项目，Ant Design 生态的 Vue 实现。",
                strengths=[
                    "与 Ant Design React 版保持一致的设计语言和组件覆盖",
                    "表格、表单、树形、日期选择等 B 端核心组件成熟",
                    "中文文档完善，国内社区活跃",
                ],
                notes=[
                    "默认 Ant 风格强烈，品牌化需要通过 ConfigProvider 做主题覆盖",
                    "包体较大，建议按需引入",
                ],
            ),
            LibraryRecommendation(
                name="Arco Design Vue",
                category="Alternative",
                rationale="适合需要更现代感的中后台与数据工作台。",
                strengths=[
                    "组件层次清晰，视觉更现代",
                    "适合 dashboard 场景",
                ],
                notes=[
                    "仍需针对品牌感与信息密度做定制",
                ],
            ),
            LibraryRecommendation(
                name="Vuetify 3",
                category="Alternative",
                rationale="适合遵循 Material Design 3 规范的 Vue 项目。",
                strengths=[
                    "Material Design 3 官方级实现，组件覆盖 70+",
                    "内置网格系统、主题引擎和无障碍支持",
                    "企业级组件（Data Table、Treeview）成熟",
                ],
                notes=[
                    "包体较大，需要按需引入优化",
                    "视觉强绑定 Material，品牌化需要大量 token 覆盖",
                ],
            ),
            LibraryRecommendation(
                name="PrimeVue",
                category="Alternative",
                rationale="适合需要完整组件覆盖和多主题支持的 Vue 企业项目。",
                strengths=[
                    "90+ 组件覆盖，含 DataTable、Chart、Editor 等高级组件",
                    "多种预设主题（Lara/Aura/Nora），无障碍优先设计",
                    "支持 unstyled 模式，可完全自定义视觉",
                ],
                notes=[
                    "预设主题风格独特，品牌化需要主题定制",
                ],
            ),
            LibraryRecommendation(
                name="Radix Vue + Tailwind CSS",
                category="Alternative",
                rationale="适合追求 Vue 版 shadcn 级别控制力的项目。",
                strengths=[
                    "headless 组件，视觉完全由 Tailwind 控制",
                    "无障碍内置，与 shadcn-vue 配合使用",
                ],
                notes=[
                    "生态较新，需要自建部分业务组件",
                ],
            ),
            LibraryRecommendation(
                name="TDesign Vue Next",
                category="Alternative",
                rationale="适合遵循腾讯设计规范的 Vue 3 项目，与小程序端保持统一。",
                strengths=[
                    "腾讯官方 Vue 3 组件库，与 TDesign 小程序设计语言统一",
                    "适合需要 Web + 小程序跨端一致性的项目",
                    "Starter Kit 和模板项目开箱即用",
                ],
                notes=[
                    "主要面向腾讯生态，外部社区相对较小",
                ],
            ),
            LibraryRecommendation(
                name="Vant 4",
                category="Alternative",
                rationale="适合 H5 移动端的 Vue 3 项目，有赞出品。",
                strengths=[
                    "70+ 移动端组件，触控交互和手势支持成熟",
                    "轻量高性能，按需引入后包体小",
                    "多语言和多主题支持",
                ],
                notes=[
                    "仅适合移动端/H5，不适合桌面端中后台",
                ],
            ),
        ],
        "angular": [
            LibraryRecommendation(
                name="Angular Material + CDK",
                category="Primary",
                rationale="适合流程型企业应用和可维护性优先的 Angular 项目。",
                strengths=[
                    "无障碍、表单、Overlay 和 CDK 能力成熟",
                    "适合强约束组件体系",
                ],
                notes=[
                    "必须做主题和排版升级，不能直接 Material 默认观感交付",
                ],
            ),
            LibraryRecommendation(
                name="PrimeNG",
                category="Alternative",
                rationale="适合需要丰富组件和企业级功能的 Angular 项目。",
                strengths=[
                    "80+ 组件覆盖，含 TreeTable、Schedule、Editor 等高级组件",
                    "多主题预设（Lara/Aura），支持深色模式",
                    "社区活跃，商业支持可用",
                ],
                notes=[
                    "默认主题风格偏传统，品牌化需定制",
                ],
            ),
            LibraryRecommendation(
                name="NG-ZORRO (Ant Design of Angular)",
                category="Alternative",
                rationale="适合中后台和中文团队的 Angular 项目。",
                strengths=[
                    "Ant Design 规范的 Angular 实现，组件覆盖完整",
                    "中文文档完善，国内社区活跃",
                    "表格、表单、树形等 B 端核心组件成熟",
                ],
                notes=[
                    "与 Ant Design React 版保持视觉一致，品牌化需额外投入",
                ],
            ),
            LibraryRecommendation(
                name="Spartan UI + Tailwind CSS",
                category="Alternative",
                rationale="适合追求 Angular 版 shadcn 体验的项目。",
                strengths=[
                    "shadcn/ui 的 Angular 移植版，headless + Tailwind 组合",
                    "完全可定制，品牌控制力强",
                ],
                notes=[
                    "生态较新，组件数量持续增长中",
                ],
            ),
        ],
        "svelte": [
            LibraryRecommendation(
                name="shadcn-svelte + Bits UI + Tailwind CSS",
                category="Primary",
                rationale="适合追求现代商业观感和高定制性的 Svelte 项目。",
                strengths=[
                    "组件控制力高，适合品牌型产品界面",
                    "与 token 和 Tailwind 生态配合良好",
                ],
                notes=[
                    "优先建立页面骨架和 token，再补动画与局部质感",
                ],
            ),
            LibraryRecommendation(
                name="Skeleton UI",
                category="Alternative",
                rationale="适合快速起步的 Svelte 产品。",
                strengths=[
                    "上手快，组件较全",
                ],
                notes=[
                    "默认风格需要品牌化重写",
                ],
            ),
        ],
        "mobile": [
            LibraryRecommendation(
                name="平台原生设计系统 + 自定义 Token",
                category="Primary",
                rationale="移动端优先保留原生交互可信度，再叠加品牌 token。",
                strengths=[
                    "符合平台交互预期",
                    "更适合高频任务流和触控体验",
                ],
                notes=[
                    "少做网页式 Hero，多做任务型布局和底部操作结构",
                ],
            )
        ],
        "desktop": [
            LibraryRecommendation(
                name="Electron / Tauri + React/Vue + Tailwind + 桌面组件库",
                category="Primary",
                rationale="适合跨平台桌面应用，兼顾 Web 技术效率与桌面系统能力。",
                strengths=[
                    "可复用现有 Web 组件体系与设计 token",
                    "便于集成文件系统、托盘、通知、离线缓存等桌面能力",
                ],
                notes=[
                    "窗口布局、快捷键、菜单栏、深色模式需按桌面范式设计",
                    "避免把桌面端做成纯网页壳，需补齐本地能力交互",
                ],
            ),
            LibraryRecommendation(
                name="Wails / Tauri + 原生壳层",
                category="Alternative",
                rationale="适合更轻量、资源占用更低的桌面客户端。",
                strengths=[
                    "包体更轻，启动性能更好",
                ],
                notes=[
                    "需要明确前后端通信契约与本地权限边界",
                ],
            ),
        ],
        "react-native": [
            LibraryRecommendation(
                name="React Native + NativeWind + Tamagui / React Native Paper",
                category="Primary",
                rationale="适合 AI Coding 场景快速落地跨端 APP，同时保持可控品牌系统。",
                strengths=[
                    "跨平台组件复用效率高",
                    "可通过 token 保持与 Web/H5 品牌一致",
                ],
                notes=[
                    "导航、手势、系统权限优先按原生范式设计",
                    "避免直接照搬 Web 布局和交互节奏",
                ],
            )
        ],
        "flutter": [
            LibraryRecommendation(
                name="Flutter + Material 3 / Cupertino + FlexColorScheme",
                category="Primary",
                rationale="适合高性能跨端 APP 与复杂动画场景。",
                strengths=[
                    "渲染一致性高，组件体系完整",
                    "动画和复杂交互实现能力强",
                ],
                notes=[
                    "必须先定义主题和组件状态映射，避免默认 Material 风格直出",
                ],
            )
        ],
        "swiftui": [
            LibraryRecommendation(
                name="SwiftUI + Design Tokens + SF Symbols",
                category="Primary",
                rationale="适合 iOS 原生体验优先的商业 APP。",
                strengths=[
                    "原生体验、动效和无障碍能力优秀",
                    "便于与 iOS 设计规范对齐",
                ],
                notes=[
                    "遵循 Human Interface Guidelines，避免网页式信息堆叠",
                ],
            )
        ],
        "miniapp": [
            LibraryRecommendation(
                name="TDesign 小程序 + Taro / UniApp + Tailwind(TW 适配)",
                category="Primary",
                rationale="适合微信小程序商业场景，兼顾腾讯生态组件规范与跨端复用。",
                strengths=[
                    "符合微信生态交互习惯，组件成熟",
                    "支持表单、弹层、列表、导航等高频业务组件快速搭建",
                ],
                notes=[
                    "小程序端优先使用 TDesign 组件与交互模式",
                    "触控区域、性能包体、分包策略需前置约束",
                ],
            ),
            LibraryRecommendation(
                name="Vant Weapp / NutUI(小程序)",
                category="Alternative",
                rationale="适合轻量业务与已有技术栈迁移。",
                strengths=[
                    "上手成本低，社区资料丰富",
                ],
                notes=[
                    "需要额外做品牌 token 重写，避免默认风格模板化",
                ],
            ),
        ],
        "default": [
            LibraryRecommendation(
                name="Tailwind CSS + Headless Patterns",
                category="Primary",
                rationale="适合未知前端栈时先建立 token、栅格和组件骨架。",
                strengths=[
                    "轻量、灵活",
                    "便于逐步落地品牌化设计系统",
                ],
                notes=[
                    "必须定义组件规范，避免 utility-class 随意散落",
                ],
            )
        ],
    }

    COMPONENT_LIBRARIES = STACK_RECOMMENDATIONS

    ICON_RECOMMENDATIONS = {
        "default": "Lucide",
        "brand": "Lucide + Simple Icons（仅品牌/合作方标识）",
        "dense": "Lucide / Tabler",
    }

    CHART_RECOMMENDATIONS = {
        "react": {
            "default": "Recharts",
            "dense": "ECharts / Visx",
        },
        "vue": {
            "default": "ECharts",
            "dense": "ECharts / AntV",
        },
        "angular": {
            "default": "ECharts / ngx-charts",
            "dense": "ECharts",
        },
        "svelte": {
            "default": "LayerCake / ECharts",
            "dense": "ECharts",
        },
        "miniapp": {
            "default": "F2 / ECharts 小程序版",
            "dense": "F2 + 自定义业务图层",
        },
        "react-native": {
            "default": "Victory Native / React Native Skia Charts",
            "dense": "Skia-based custom charts",
        },
        "flutter": {
            "default": "fl_chart / Syncfusion Flutter Charts",
            "dense": "Syncfusion / CustomPainter charts",
        },
        "swiftui": {
            "default": "Swift Charts",
            "dense": "Swift Charts + custom marks",
        },
        "desktop": {
            "default": "ECharts / Plotly（桌面高密度分析）",
            "dense": "ECharts + AG Grid integrated charts",
        },
        "default": {
            "default": "ECharts",
            "dense": "ECharts",
        },
    }

    FORM_STACK = {
        "react": "React Hook Form + Zod",
        "vue": "vee-validate + Zod / Valibot",
        "angular": "Angular Reactive Forms",
        "svelte": "sveltekit-superforms + Zod",
        "miniapp": "TDesign Form + 小程序原生校验",
        "react-native": "React Hook Form + Zod + controlled inputs",
        "flutter": "Form + Validator + Riverpod/BLoC",
        "swiftui": "SwiftUI Form + Observable validation",
        "desktop": "Schema Form + local persistence + shortcut actions",
        "default": "Schema-driven validation + typed DTO",
    }

    MOTION_STACK = {
        "react": "Framer Motion（营销/品牌页） + CSS transitions（工作台）",
        "vue": "VueUse Motion / Motion One + CSS transitions",
        "angular": "Angular Animations + CSS transitions",
        "svelte": "Svelte transitions + Motion One",
        "miniapp": "小程序原生动画 + 轻量过渡（避免重动画）",
        "react-native": "Reanimated / Moti + native transitions",
        "flutter": "Implicit animations + Motion spec",
        "swiftui": "SwiftUI animation + spring transitions",
        "desktop": "Micro-interaction transitions + window state animations",
        "default": "Meaningful CSS transitions only",
    }
