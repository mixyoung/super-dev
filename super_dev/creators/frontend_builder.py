"""
前端实施蓝图生成器 - 先冻结宿主可执行的前端参考面
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from super_dev.artifact_utils import ui_contract_filename

from .frontend_framework_projects_mixin import FrontendFrameworkProjectsMixin
from .frontend_quality_config_mixin import FrontendQualityConfigMixin


class FrontendScaffoldBuilder(FrontendFrameworkProjectsMixin, FrontendQualityConfigMixin):
    """生成宿主可直接评审和继续实现的前端实施参考页"""

    def __init__(
        self,
        project_dir: Path,
        name: str,
        description: str,
        frontend: str = "react",
    ):
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.description = description
        self.frontend = frontend

    def generate(
        self,
        requirements: list[dict],
        phases: list[dict],
        docs: dict,
    ) -> dict:
        """写入前端实施参考文件并返回路径"""
        output_dir = self.project_dir / "output" / "frontend"
        output_dir.mkdir(parents=True, exist_ok=True)

        html_path = output_dir / "index.html"
        css_path = output_dir / "styles.css"
        tokens_path = output_dir / "design-tokens.css"
        js_path = output_dir / "app.js"
        ui_contract = self._load_ui_contract()

        html_path.write_text(self._build_html(ui_contract), encoding="utf-8")
        css_path.write_text(self._build_css(ui_contract), encoding="utf-8")
        tokens_path.write_text(
            ui_contract.get("design_tokens", {}).get("css_variables") or ":root {}\n",
            encoding="utf-8",
        )
        js_path.write_text(
            self._build_js(requirements, phases, docs, ui_contract), encoding="utf-8"
        )

        result: dict[str, str | dict] = {
            "html": str(html_path),
            "css": str(css_path),
            "tokens": str(tokens_path),
            "js": str(js_path),
        }
        framework_scaffold = self._generate_framework_scaffold(ui_contract)
        if framework_scaffold:
            result["framework_scaffold"] = framework_scaffold
        return result

    def _resolve_direction_profile(self, ui_contract: dict) -> dict:
        _art_direction_candidates_value = ui_contract.get("art_direction_candidates")
        art_direction_candidates = (
            _art_direction_candidates_value
            if isinstance(_art_direction_candidates_value, list)
            else []
        )
        _design_direction_manifest_value = ui_contract.get("design_direction_manifest")
        design_direction_manifest = (
            _design_direction_manifest_value
            if isinstance(_design_direction_manifest_value, dict)
            else {}
        )
        _anti_slop_guardrails_value = ui_contract.get("anti_ai_slop_guardrails")
        anti_slop_guardrails = (
            _anti_slop_guardrails_value if isinstance(_anti_slop_guardrails_value, dict) else {}
        )
        primary = art_direction_candidates[0] if art_direction_candidates else {}
        direction_id = (
            design_direction_manifest.get("direction_id")
            or primary.get("id")
            or "modern-commercial"
        )
        selected = next(
            (item for item in art_direction_candidates if item.get("id") == direction_id),
            primary,
        )
        anti_cliches = list(selected.get("anti_cliches", [])[:3]) or list(
            anti_slop_guardrails.get("candidate_anti_cliches", [])[:3]
        )
        return {
            "direction_id": direction_id,
            "name": (
                design_direction_manifest.get("selected_direction")
                or selected.get("name")
                or "Frozen UI Contract"
            ),
            "philosophy": (
                design_direction_manifest.get("philosophy")
                or selected.get("philosophy")
                or "先锁定视觉哲学，再组织层级、证明和交互。"
            ),
            "hero_treatment": (
                design_direction_manifest.get("hero_treatment")
                or selected.get("hero_treatment")
                or "首屏同时承担价值主张、证据和行动入口。"
            ),
            "proof_strategy": (
                design_direction_manifest.get("proof_strategy")
                or selected.get("proof_strategy")
                or "优先使用截图、案例、数据和流程证明。"
            ),
            "visual_tension": (
                design_direction_manifest.get("visual_tension")
                or selected.get("visual_tension")
                or "通过排版、留白和重点色建立张力。"
            ),
            "narrative_mode": (
                design_direction_manifest.get("narrative_mode")
                or selected.get("narrative_mode")
                or "先理解价值，再进入证明和能力模块。"
            ),
            "palette_strategy": (
                design_direction_manifest.get("palette_strategy")
                or selected.get("palette_strategy")
                or "先控制颜色数量，再决定强调色位置。"
            ),
            "why_this_direction": design_direction_manifest.get("why_this_direction") or "",
            "reference_anchor": design_direction_manifest.get("reference_anchor") or "",
            "anti_cliches": anti_cliches,
            "tweak_axes": list(selected.get("tweak_axes", [])[:4]),
            "density": (
                ui_contract.get("information_density")
                or design_direction_manifest.get("density_tempo")
                or "medium"
            ),
        }

    def _framework_ui_profile(self, ui_contract: dict) -> dict:
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})
        generated = ui_contract.get("generated_design_system", {})
        radius = generated.get("radius", {}) if isinstance(generated, dict) else {}
        return {
            "colors": {
                "primary": palette.get("primary", "#0f7cfa"),
                "accent": palette.get("accent", "#f65f22"),
                "background": palette.get("background", "#f5f8ff"),
                "foreground": palette.get("text", "#172133"),
                "border": palette.get("border", "#dfe7f3"),
                "muted": self._lighten(palette.get("background", "#f5f8ff"), 0.04),
                "muted_foreground": self._darken(palette.get("text", "#172133"), 0.62),
                "secondary": self._lighten(palette.get("primary", "#0f7cfa"), 0.45),
                "ring": palette.get("primary", "#0f7cfa"),
            },
            "fonts": {
                "sans": typography.get("body", "Inter"),
                "mono": "JetBrains Mono",
            },
            "radius": {
                "lg": radius.get("lg", "18px"),
                "md": radius.get("md", "12px"),
                "sm": radius.get("sm", "8px"),
            },
        }

    def _generate_framework_scaffold(self, ui_contract: dict) -> dict | None:
        frontend = str(self.frontend or "react").strip().lower()
        if frontend in {"next", "nextjs"}:
            from super_dev.creators.nextjs_scaffold import NextjsScaffoldGenerator

            nextjs_files = NextjsScaffoldGenerator().generate(
                self.project_dir,
                self.name,
                ui_profile=self._framework_ui_profile(ui_contract),
            )
            root = self.project_dir / "output" / "nextjs-scaffold"
            return {
                "kind": "nextjs-app-router",
                "root": str(root),
                "files": [str(path) for path in nextjs_files],
            }
        if frontend in {"vue", "vue3", "nuxt", "vue-vite"}:
            files = self.generate_vue3_project()
            root = self.project_dir / "output" / "frontend-vue3"
            return {"kind": "vue3-vite", "root": str(root), "files": list(files.values())}
        if frontend in {"angular"}:
            files = self.generate_angular_project()
            root = self.project_dir / "output" / "frontend-angular"
            return {"kind": "angular", "root": str(root), "files": list(files.values())}
        if frontend in {"svelte", "sveltekit"}:
            files = self.generate_svelte_project()
            root = self.project_dir / "output" / "frontend-svelte"
            return {"kind": "sveltekit", "root": str(root), "files": list(files.values())}
        if frontend in {"react", "react-vite", "remix", "gatsby"}:
            files = self.generate_react_vite_project(ui_contract)
            root = self.project_dir / "output" / "frontend-react"
            kind = "react-vite"
            if frontend == "remix":
                kind = "remix-family-preview"
            elif frontend == "gatsby":
                kind = "gatsby-family-preview"
            return {"kind": kind, "root": str(root), "files": list(files.values())}
        if frontend in {"expo", "react-native"}:
            files = self.generate_expo_project(ui_contract, flavor=frontend)
            root = self.project_dir / "output" / "frontend-expo"
            kind = "expo-managed" if frontend == "expo" else "react-native-expo"
            return {"kind": kind, "root": str(root), "files": list(files.values())}
        if frontend in {"flutter"}:
            files = self.generate_flutter_project(ui_contract)
            root = self.project_dir / "output" / "frontend-flutter"
            return {"kind": "flutter", "root": str(root), "files": list(files.values())}
        if frontend in {"uni-app", "uniapp", "taro"}:
            files = self.generate_miniapp_project(ui_contract, flavor=frontend)
            root = self.project_dir / "output" / "frontend-miniapp"
            kind = "uni-app" if frontend in {"uni-app", "uniapp"} else "taro-family-preview"
            return {"kind": kind, "root": str(root), "files": list(files.values())}
        if frontend in {"tauri", "electron", "wails"}:
            files = self.generate_desktop_shell_project(ui_contract, flavor=frontend)
            root = self.project_dir / "output" / "frontend-desktop-shell"
            return {
                "kind": f"{frontend}-desktop-shell",
                "root": str(root),
                "files": list(files.values()),
            }
        if frontend in {"ionic", "capacitor"}:
            files = self.generate_hybrid_shell_project(ui_contract, flavor=frontend)
            root = self.project_dir / "output" / "frontend-hybrid-shell"
            return {
                "kind": f"{frontend}-hybrid-shell",
                "root": str(root),
                "files": list(files.values()),
            }
        return None

    def _build_html(self, ui_contract: dict) -> str:
        typography = ui_contract.get("typography_preset", {})
        style_direction = ui_contract.get("style_direction", {})
        _framework_playbook_value = ui_contract.get("framework_playbook")
        framework_playbook = (
            _framework_playbook_value if isinstance(_framework_playbook_value, dict) else {}
        )
        _component_stack_value = ui_contract.get("component_stack")
        component_stack = _component_stack_value if isinstance(_component_stack_value, dict) else {}
        icon_system = (
            ui_contract.get("icon_system")
            or component_stack.get("icon")
            or component_stack.get("icons")
            or "Lucide Icons"
        )
        preference = ui_contract.get("ui_library_preference", {})
        primary_library = (
            preference.get("final_selected")
            or ui_contract.get("primary_library", {}).get("name")
            or preference.get("preferred")
            or "shadcn/ui + Radix UI + Tailwind CSS"
        )
        _screen_recipes_value = ui_contract.get("screen_recipes")
        screen_recipes = _screen_recipes_value if isinstance(_screen_recipes_value, list) else []
        direction_profile = self._resolve_direction_profile(ui_contract)
        primary_recipe = screen_recipes[0] if screen_recipes else {}
        _verification_handoff_value = ui_contract.get("verification_handoff")
        verification_handoff = (
            _verification_handoff_value if isinstance(_verification_handoff_value, dict) else {}
        )
        _selected_reference_value = ui_contract.get("selected_design_reference")
        selected_reference = (
            _selected_reference_value if isinstance(_selected_reference_value, dict) else {}
        )
        reference_name = selected_reference.get("name") or "Frozen UI Contract"
        hero_panel_title = primary_recipe.get("label") or "Design Execution Blueprint"
        hero_panel_copy = (
            primary_recipe.get("objective")
            or "把页面配方、设计上下文、Tweaks 和交付证据锁进同一条 UI 闭环。"
        )
        trust_module_count = len(primary_recipe.get("trust_modules", []))
        verification_count = len(verification_handoff.get("verification_order", []))
        direction_name = direction_profile["name"]
        anti_cliche_markup = "\n".join(
            f"              <li>{html.escape(item)}</li>"
            for item in direction_profile["anti_cliches"][:3]
        )
        axis_markup = "\n".join(
            f"              <span>{html.escape(item)}</span>"
            for item in direction_profile["tweak_axes"][:4]
        )
        return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(self.name)} · Frontend Blueprint</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="{self._build_google_fonts_url(typography)}" rel="stylesheet" />
    <link rel="stylesheet" href="./design-tokens.css" />
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body data-direction="{html.escape(str(direction_profile['direction_id']))}" data-density="{html.escape(str(direction_profile['density']))}">
    <div class="bg-layer"></div>
    <main class="shell">
      <nav class="topbar">
        <div class="brand">
          <span class="brand-mark">SD</span>
          <span>{html.escape(self.name)}</span>
        </div>
        <div class="top-actions">
          <a href="#trust">客户证明</a>
          <a href="#recipe-map">页面配方</a>
          <a href="#design-directions">视觉方向</a>
          <a href="#workspace">交付路径</a>
          <a class="primary-link" href="#doc-links">查看文档</a>
        </div>
      </nav>

      <section class="hero" aria-labelledby="hero-title">
        <div class="hero-copy">
          <p class="eyebrow">Super Dev Frontend First Delivery</p>
          <h1 id="hero-title">{html.escape(self.name)}</h1>
          <p class="summary">{html.escape(self.description)}</p>
          <p class="style-direction">{html.escape(style_direction.get('direction', ''))}</p>
          <div class="meta">
            <span>Framework: {html.escape(self.frontend)}</span>
            <span>Mode: 需求文档驱动</span>
            <span>Icons: {html.escape(icon_system)}</span>
            <span>UI: {html.escape(primary_library)}</span>
            <span>Direction: {html.escape(str(direction_name))}</span>
            <span>Reference: {html.escape(reference_name)}</span>
          </div>
          <div class="hero-actions">
            <a class="button button-primary" href="#doc-links">打开核心文档</a>
            <a class="button button-secondary" href="#recipe-map">查看页面配方</a>
          </div>
          <ul class="trust-strip">
            <li>商业级流程治理</li>
            <li>研究报告与 UI/UX 规范先行</li>
            <li>Screen recipes / Tweaks / Runtime evidence 全链闭环</li>
          </ul>
        </div>
        <div class="hero-panel" aria-label="产品演示摘要">
          <div class="panel-card">
            <p class="panel-label">Preview Snapshot</p>
            <h2>{html.escape(hero_panel_title)}</h2>
            <p>{html.escape(hero_panel_copy)}</p>
            <div class="metric-grid">
              <div><strong>{len(screen_recipes) or 1}</strong><span>页面配方</span></div>
              <div><strong>{trust_module_count or 3}</strong><span>信任模块</span></div>
              <div><strong>{verification_count or 4}</strong><span>验证节点</span></div>
            </div>
          </div>
        </div>
      </section>

      <section class="card direction-stage" aria-labelledby="direction-stage-title">
        <div class="direction-stage-copy">
          <p class="eyebrow">Signature Art Direction</p>
          <h2 id="direction-stage-title">{html.escape(direction_name)}</h2>
          <p class="direction-philosophy">{html.escape(str(direction_profile["philosophy"]))}</p>
          <p class="direction-why">{html.escape(str(direction_profile["why_this_direction"]))}</p>
          <div class="direction-signals">
            <span>Hero: {html.escape(str(direction_profile["hero_treatment"]))}</span>
            <span>Proof: {html.escape(str(direction_profile["proof_strategy"]))}</span>
            <span>Tension: {html.escape(str(direction_profile["visual_tension"]))}</span>
          </div>
          <div class="direction-axes">
{axis_markup or '              <span>信息密度</span>'}
          </div>
        </div>
        <div class="direction-stage-proof">
          <article class="signature-proof">
            <p class="panel-label">Narrative Mode</p>
            <h3>{html.escape(str(direction_profile["narrative_mode"]))}</h3>
            <p>{html.escape(str(direction_profile["palette_strategy"]))}</p>
          </article>
          <article class="signature-proof anti-cliche-proof">
            <p class="panel-label">Anti-Cliche Guardrails</p>
            <ul class="delivery-list">
{anti_cliche_markup or '              <li>禁止流行 AI 模板化视觉。</li>'}
            </ul>
          </article>
        </div>
      </section>

      <section id="trust" class="card trust-band">
        <div class="section-head">
          <h2>可信交付信号</h2>
          <p>不是只生成页面，而是确保需求、规范、状态、质量和上线准备全部可追踪。</p>
        </div>
        <div class="trust-grid">
          <article class="trust-item">
            <h3>Research First</h3>
            <p>先研究同类产品、页面结构与商业表达，再写文档和代码。</p>
          </article>
          <article class="trust-item">
            <h3>UI/UX Baseline</h3>
            <p>先冻结组件生态、设计 token、页面骨架和状态矩阵，再实现页面。</p>
          </article>
          <article class="trust-item">
            <h3>Quality Gate</h3>
            <p>红队审查、UI 审查、质量门禁和发布演练共同保证可交付性。</p>
          </article>
        </div>
      </section>

      <section class="card doc-hub">
        <div class="section-head">
          <h2>核心文档</h2>
          <p>先完成文档，再以文档驱动实现。</p>
        </div>
        <div id="doc-links" class="doc-grid"></div>
      </section>

      <section id="workspace" class="card split">
        <div>
          <div class="section-head">
            <h2>需求模块</h2>
            <p>按需求生成页面和能力模块。</p>
          </div>
          <div id="requirements" class="chips"></div>
        </div>
        <div>
          <div class="section-head">
            <h2>执行路线</h2>
            <p>从 0-1 到 1-N+1 的阶段推进。</p>
          </div>
          <ol id="timeline" class="timeline"></ol>
        </div>
      </section>

      <section id="recipe-map" class="card">
        <div class="section-head">
          <h2>页面配方</h2>
          <p>先冻结关键页面的结构顺序、组件重点、信任模块和状态要求，再开始写页面。</p>
        </div>
        <div id="recipe-grid" class="recipe-grid"></div>
      </section>

      <section id="design-directions" class="card split">
        <div>
          <div class="section-head">
            <h2>视觉方向候选</h2>
            <p>先在 2-3 个明确设计哲学之间做选择，而不是直接输出一版模板页。</p>
          </div>
          <div id="direction-grid" class="recipe-grid"></div>
        </div>
        <div>
          <div class="section-head">
            <h2>反 AI 味护栏</h2>
            <p>禁止科技 cliché、聊天壳模板和无意义炫技，用层级、证据和工艺建立高级感。</p>
          </div>
          <ul id="anti-slop-list" class="delivery-list"></ul>
          <div class="sub-card">
            <p class="panel-label">Critique Rubric</p>
            <ul id="critique-rubric" class="delivery-list"></ul>
          </div>
        </div>
      </section>

      <section class="card split preview-proof">
        <div>
          <div class="section-head">
            <h2>页面骨架</h2>
            <p>对外页面要有价值表达、信任证明、能力模块和明确 CTA，内部工作台要有导航、状态与操作路径。</p>
          </div>
          <ul class="delivery-list">
            <li>Hero + 价值主张 + CTA</li>
            <li>真实截图/演示摘要</li>
            <li>案例 / 安全 / FAQ / 证明</li>
            <li>功能分区与下一步转化入口</li>
          </ul>
        </div>
        <div>
          <div class="section-head">
            <h2>交付证明</h2>
            <p>适用于官网、产品页、工作台和商业级 MVP 验证。</p>
          </div>
          <div class="proof-card">
            <strong>Case Study Ready</strong>
            <p>支持把页面、文档、任务状态和质量报告一起用于内部评审或商业验证。</p>
            <a class="inline-link" href="#faq">查看 FAQ</a>
          </div>
        </div>
      </section>

      <section class="card split execution-protocol">
        <div>
          <div class="section-head">
            <h2>上下文与 Tweaks 协议</h2>
            <p>优先吸收真实代码与设计上下文，用单一主原型承载变体，而不是分叉出多份页面。</p>
          </div>
          <ul id="context-protocol" class="delivery-list"></ul>
          <div class="sub-card">
            <p class="panel-label">Tweaks</p>
            <ul id="tweak-controls" class="delivery-list"></ul>
          </div>
        </div>
        <div>
          <div class="section-head">
            <h2>验证与交付</h2>
            <p>把 preview、runtime、UI review 和最终交付证据放进同一条前端闭环，而不是只看页面能否打开。</p>
          </div>
          <ul id="verification-steps" class="delivery-list"></ul>
          <div class="sub-card">
            <p class="panel-label">Handoff</p>
            <ul id="handoff-artifacts" class="delivery-list"></ul>
          </div>
        </div>
      </section>

      <section class="card framework-playbook" {'' if framework_playbook else 'hidden'}>
        <div class="section-head">
          <h2>跨平台框架执行护栏</h2>
          <p>跨平台项目要先冻结框架专项能力、平台差异、验收面和交付证据，再进入实现。</p>
        </div>
        <div class="split">
          <div>
            <p class="eyebrow">Framework Playbook</p>
            <h3>{html.escape(str(framework_playbook.get("framework") or "跨平台框架"))}</h3>
            <ul id="framework-modules" class="delivery-list"></ul>
          </div>
          <div>
            <p class="eyebrow">Native & Validation</p>
            <ul id="framework-native" class="delivery-list"></ul>
            <ul id="framework-validation" class="delivery-list"></ul>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="section-head">
          <h2>交付清单</h2>
          <p>前端先行，随后进入系统化交付。</p>
        </div>
        <ul class="delivery-list">
          <li>阶段 1: PRD / 架构 / UIUX 文档</li>
          <li>阶段 2: 前端实施蓝图与核心页面</li>
          <li>阶段 3: 后端与数据库能力</li>
          <li>阶段 4: 联调、测试、质量门禁</li>
          <li>阶段 5: 发布、监控与迭代</li>
        </ul>
      </section>

      <section id="faq" class="card">
        <div class="section-head">
          <h2>FAQ</h2>
          <p>快速回答“为什么不是直接写代码”的问题。</p>
        </div>
        <div class="faq-list">
          <article>
            <h3>为什么先做文档？</h3>
            <p>因为商业级交付不只是把页面写出来，而是让需求、架构、UI/UX 和质量口径可审计。</p>
          </article>
          <article>
            <h3>为什么要看质量门禁？</h3>
            <p>为了尽早识别风险、状态缺失、UI 模板化和交付短板，而不是等上线前才返工。</p>
          </article>
        </div>
      </section>
    </main>
    <script src="./app.js"></script>
  </body>
</html>
"""

    def _build_css(self, ui_contract: dict) -> str:
        palette = ui_contract.get("color_palette", {})
        typography = ui_contract.get("typography_preset", {})
        primary = palette.get("primary", "#0f7cfa")
        accent = palette.get("accent", "#f65f22")
        background = palette.get("background", "#f5f8ff")
        text = palette.get("text", "#172133")
        border = palette.get("border", "#dfe7f3")
        generated = ui_contract.get("generated_design_system", {})
        radius = generated.get("radius", {}).get("lg", "18px")
        shadow = generated.get("shadows", {}).get("lg", "0 18px 40px rgba(13, 33, 57, 0.09)")
        heading_font = typography.get("heading", "Manrope")
        body_font = typography.get("body", "Source Sans 3")
        template = """
:root {
  --bg-0: __BG0__;
  --bg-1: __BG1__;
  --surface: rgba(255, 255, 255, 0.86);
  --surface-strong: rgba(255, 255, 255, 0.96);
  --panel-surface: rgba(255, 255, 255, 0.98);
  --stroke: __STROKE__;
  --text: __TEXT__;
  --muted: __MUTED__;
  --primary: __PRIMARY__;
  --accent: __ACCENT__;
  --radius: __RADIUS__;
  --shadow: __SHADOW__;
  --shell-width: 1120px;
  --hero-grid-left: 1.4fr;
  --hero-grid-right: 0.9fr;
  --hero-padding: 28px 28px 26px;
  --hero-surface: var(--surface);
  --hero-outline: none;
  --hero-radius: var(--radius);
  --section-gap: 18px;
  --recipe-surface: __PRIMARY_ALPHA_06__;
  --chip-surface: __ACCENT_ALPHA_10__;
  --panel-highlight: __PRIMARY_ALPHA_08__;
  --direction-stage-surface: rgba(255, 255, 255, 0.92);
  --display-letter-spacing: -0.03em;
  --font-heading: "__HEADING_FONT__", sans-serif;
  --font-body: "__BODY_FONT__", system-ui, sans-serif;
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  color: var(--text);
  font-family: var(--font-body);
  background: var(--bg-0);
}

.bg-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image: radial-gradient(circle at 8% 10%, __PRIMARY_ALPHA_20__, transparent 35%),
    radial-gradient(circle at 85% 12%, __ACCENT_ALPHA_20__, transparent 28%),
    radial-gradient(circle at 50% 100%, __PRIMARY_ALPHA_12__, transparent 34%);
}

.shell {
  max-width: var(--shell-width);
  margin: 0 auto;
  padding: 40px 20px 64px;
  position: relative;
  z-index: 1;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: #172133;
  color: #ffffff;
  font-size: 13px;
}

.top-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.top-actions a {
  color: var(--text);
  text-decoration: none;
  font-weight: 700;
}

.top-actions .primary-link {
  color: var(--primary);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, var(--hero-grid-left)) minmax(280px, var(--hero-grid-right));
  gap: var(--section-gap);
  padding: var(--hero-padding);
  border: 1px solid var(--stroke);
  border-radius: var(--hero-radius);
  background: var(--hero-surface);
  box-shadow: var(--shadow);
  backdrop-filter: blur(6px);
  outline: var(--hero-outline);
  outline-offset: -1px;
}

.eyebrow {
  margin: 0;
  color: var(--primary);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 12px;
}

.hero h1 {
  margin: 10px 0 8px;
  font-family: var(--font-heading);
  font-size: clamp(28px, 4vw, 48px);
  letter-spacing: var(--display-letter-spacing);
}

.summary {
  margin: 0 0 14px;
  color: var(--muted);
}

.style-direction {
  margin: 0 0 14px;
  color: var(--text);
  opacity: 0.8;
  max-width: 58ch;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 18px 0 18px;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 16px;
  border-radius: 12px;
  font-weight: 800;
  text-decoration: none;
}

.button-primary {
  background: var(--primary);
  color: #ffffff;
}

.button-secondary {
  background: __PRIMARY_ALPHA_08__;
  color: __PRIMARY_DARK_62__;
}

.meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.meta span {
  border-radius: 999px;
  padding: 8px 12px;
  background: __PRIMARY_ALPHA_08__;
  color: __PRIMARY_DARK_62__;
  font-size: 13px;
  font-weight: 700;
}

.trust-strip {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.trust-strip li {
  color: var(--muted);
}

.hero-panel {
  display: flex;
}

.panel-card,
.proof-card {
  width: 100%;
  border-radius: 18px;
  border: 1px solid rgba(23, 33, 51, 0.08);
  background: var(--panel-surface);
  padding: 20px;
}

.direction-stage {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.9fr);
  gap: var(--section-gap);
  background: var(--direction-stage-surface);
}

.direction-stage-copy {
  display: grid;
  align-content: start;
  gap: 14px;
}

.direction-stage-copy h2 {
  margin: 0;
  font-size: clamp(24px, 3vw, 38px);
  font-family: var(--font-heading);
  letter-spacing: var(--display-letter-spacing);
}

.direction-philosophy,
.direction-why {
  margin: 0;
  color: var(--muted);
  max-width: 60ch;
}

.direction-signals,
.direction-axes {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.direction-signals span,
.direction-axes span {
  border-radius: 999px;
  padding: 8px 12px;
  background: var(--panel-highlight);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.direction-stage-proof {
  display: grid;
  gap: 12px;
}

.signature-proof {
  border-radius: 18px;
  padding: 18px;
  border: 1px solid rgba(23, 33, 51, 0.08);
  background: var(--panel-surface);
}

.panel-label {
  margin: 0 0 8px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.panel-card h2,
.proof-card strong {
  display: block;
  margin: 0 0 8px;
  font-family: var(--font-heading);
}

.metric-grid,
.trust-grid,
.recipe-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric-grid div,
.trust-item,
.recipe-card {
  border-radius: 14px;
  padding: 14px;
  background: var(--recipe-surface);
}

.metric-grid strong {
  display: block;
  font-size: 24px;
  font-family: var(--font-heading);
}

.metric-grid span {
  color: var(--muted);
  font-size: 13px;
}

.recipe-card h3 {
  margin: 0 0 10px;
  font-family: var(--font-heading);
}

.recipe-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.recipe-meta span {
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.card {
  margin-top: 18px;
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
  padding: 22px;
}

.section-head h2 {
  margin: 0;
  font-size: 22px;
  font-family: var(--font-heading);
}

.section-head p {
  margin: 6px 0 16px;
  color: var(--muted);
}

.doc-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.doc-item {
  display: block;
  text-decoration: none;
  color: inherit;
  border: 1px solid rgba(23, 33, 51, 0.1);
  border-radius: 14px;
  padding: 14px;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
  background: #ffffff;
}

.doc-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(16, 34, 61, 0.12);
}

.doc-item b {
  display: block;
  margin-bottom: 8px;
}

.split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 13px;
  background: var(--chip-surface);
  color: __ACCENT_DARK_60__;
  border: 1px solid __ACCENT_ALPHA_14__;
}

.timeline {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 10px;
}

.timeline li {
  padding-left: 4px;
}

.timeline b {
  display: block;
}

.timeline p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 14px;
}

.delivery-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

.inline-link {
  color: var(--primary);
  font-weight: 700;
  text-decoration: none;
}

.sub-card {
  margin-top: 14px;
  border-radius: 16px;
  border: 1px solid rgba(23, 33, 51, 0.08);
  background: rgba(255, 255, 255, 0.78);
  padding: 16px;
}

.faq-list {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.faq-list article {
  border-radius: 14px;
  border: 1px solid rgba(23, 33, 51, 0.08);
  padding: 16px;
  background: #ffffff;
}

.faq-list h3 {
  margin: 0 0 8px;
  font-size: 17px;
}

.faq-list p,
.trust-item p,
.proof-card p {
  margin: 0;
  color: var(--muted);
}

body[data-direction="editorial-swiss"] {
  --shell-width: 1180px;
  --hero-grid-left: 1.68fr;
  --hero-grid-right: 0.78fr;
  --hero-padding: 34px 34px 30px;
  --hero-radius: 14px;
  --hero-outline: 1px solid rgba(23, 33, 51, 0.12);
  --recipe-surface: rgba(23, 33, 51, 0.035);
  --panel-highlight: rgba(23, 33, 51, 0.045);
  --display-letter-spacing: -0.05em;
}

body[data-direction="editorial-swiss"] .topbar {
  margin-bottom: 28px;
}

body[data-direction="editorial-swiss"] .hero h1,
body[data-direction="editorial-swiss"] .direction-stage-copy h2 {
  text-transform: uppercase;
  max-width: 12ch;
}

body[data-direction="editorial-swiss"] .trust-strip {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

body[data-direction="precision-workspace"] {
  --shell-width: 1240px;
  --hero-grid-left: 1fr;
  --hero-grid-right: 1.08fr;
  --hero-padding: 24px;
  --hero-radius: 16px;
  --hero-surface: rgba(246, 249, 255, 0.92);
  --direction-stage-surface: rgba(246, 249, 255, 0.94);
  --recipe-surface: rgba(15, 124, 250, 0.045);
}

body[data-direction="precision-workspace"] .metric-grid,
body[data-direction="precision-workspace"] .recipe-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

body[data-direction="warm-trust"] {
  --hero-grid-left: 1.26fr;
  --hero-grid-right: 0.94fr;
  --hero-radius: 28px;
  --radius: 24px;
  --hero-surface: linear-gradient(135deg, rgba(255, 250, 245, 0.96), rgba(255, 255, 255, 0.92));
  --direction-stage-surface: rgba(255, 251, 247, 0.95);
  --recipe-surface: rgba(246, 95, 34, 0.07);
  --chip-surface: rgba(246, 95, 34, 0.12);
}

body[data-direction="cinematic-product"] {
  --bg-0: #081019;
  --surface: rgba(10, 17, 26, 0.82);
  --panel-surface: rgba(11, 20, 31, 0.92);
  --text: #eef4fb;
  --muted: rgba(238, 244, 251, 0.72);
  --stroke: rgba(140, 168, 199, 0.18);
  --hero-grid-left: 1.3fr;
  --hero-grid-right: 0.98fr;
  --hero-padding: 32px 32px 30px;
  --hero-radius: 24px;
  --hero-surface: linear-gradient(145deg, rgba(9, 18, 30, 0.96), rgba(12, 28, 43, 0.82));
  --direction-stage-surface: linear-gradient(145deg, rgba(9, 18, 30, 0.92), rgba(12, 23, 37, 0.82));
  --recipe-surface: rgba(255, 255, 255, 0.05);
  --panel-highlight: rgba(15, 124, 250, 0.16);
  --display-letter-spacing: -0.045em;
}

body[data-direction="cinematic-product"] .brand-mark {
  background: linear-gradient(145deg, var(--accent), var(--primary));
  color: #081019;
}

body[data-direction="quiet-luxury"] {
  --hero-grid-left: 1.18fr;
  --hero-grid-right: 0.84fr;
  --section-gap: 24px;
  --hero-padding: 38px 38px 34px;
  --hero-radius: 26px;
  --radius: 20px;
  --direction-stage-surface: rgba(252, 249, 244, 0.96);
  --recipe-surface: rgba(23, 33, 51, 0.03);
}

body[data-direction="playful-modular"] {
  --hero-grid-left: 1.24fr;
  --hero-grid-right: 0.92fr;
  --hero-radius: 32px;
  --radius: 28px;
  --direction-stage-surface: rgba(247, 251, 255, 0.96);
  --recipe-surface: rgba(15, 124, 250, 0.06);
  --chip-surface: rgba(246, 95, 34, 0.14);
}

body[data-direction="playful-modular"] .recipe-card,
body[data-direction="playful-modular"] .trust-item,
body[data-direction="playful-modular"] .faq-list article {
  border-radius: 22px;
}

@media (max-width: 860px) {
  .topbar,
  .hero,
  .direction-stage {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: flex-start;
  }

  .doc-grid {
    grid-template-columns: 1fr;
  }

  .split {
    grid-template-columns: 1fr;
  }

  .metric-grid,
  .trust-grid,
  .recipe-grid,
  .faq-list {
    grid-template-columns: 1fr;
  }
}
"""
        return (
            template.replace("__BG0__", self._lighten(background, 0.08))
            .replace("__BG1__", self._lighten(accent, 0.9))
            .replace("__STROKE__", self._alpha(border, 0.78))
            .replace("__TEXT__", text)
            .replace("__MUTED__", self._darken(text, 0.62))
            .replace("__PRIMARY__", primary)
            .replace("__ACCENT__", accent)
            .replace("__RADIUS__", radius)
            .replace("__SHADOW__", shadow)
            .replace("__HEADING_FONT__", heading_font)
            .replace("__BODY_FONT__", body_font)
            .replace("__PRIMARY_ALPHA_20__", self._alpha(primary, 0.2))
            .replace("__ACCENT_ALPHA_20__", self._alpha(accent, 0.2))
            .replace("__PRIMARY_ALPHA_12__", self._alpha(primary, 0.12))
            .replace("__PRIMARY_ALPHA_08__", self._alpha(primary, 0.08))
            .replace("__PRIMARY_ALPHA_06__", self._alpha(primary, 0.06))
            .replace("__PRIMARY_DARK_62__", self._darken(primary, 0.62))
            .replace("__ACCENT_ALPHA_10__", self._alpha(accent, 0.1))
            .replace("__ACCENT_ALPHA_14__", self._alpha(accent, 0.14))
            .replace("__ACCENT_DARK_60__", self._darken(accent, 0.6))
        )

    def _build_js(
        self, requirements: list[dict], phases: list[dict], docs: dict, ui_contract: dict
    ) -> str:
        payload = {
            "requirements": requirements,
            "phases": phases,
            "docs": docs,
            "ui_contract": {
                "ui_library_preference": ui_contract.get("ui_library_preference"),
                "icon_system": (
                    ui_contract.get("icon_system")
                    or (
                        ui_contract.get("component_stack", {}).get("icon")
                        if isinstance(ui_contract.get("component_stack"), dict)
                        else None
                    )
                    or (
                        ui_contract.get("component_stack", {}).get("icons")
                        if isinstance(ui_contract.get("component_stack"), dict)
                        else None
                    )
                ),
                "surface": ui_contract.get("surface"),
                "information_density": ui_contract.get("information_density"),
                "framework_playbook": ui_contract.get("framework_playbook"),
                "art_direction_candidates": ui_contract.get("art_direction_candidates"),
                "design_direction_manifest": ui_contract.get("design_direction_manifest"),
                "anti_ai_slop_guardrails": ui_contract.get("anti_ai_slop_guardrails"),
                "critique_rubric": ui_contract.get("critique_rubric"),
                "screen_recipes": ui_contract.get("screen_recipes"),
                "design_context_protocol": ui_contract.get("design_context_protocol"),
                "tweak_strategy": ui_contract.get("tweak_strategy"),
                "verification_handoff": ui_contract.get("verification_handoff"),
            },
        }
        payload_str = json.dumps(payload, ensure_ascii=False, indent=2)
        payload_str = payload_str.replace("</", "<\\/")
        return f"""const DATA = {payload_str};

const docContainer = document.getElementById("doc-links");
const reqContainer = document.getElementById("requirements");
const timelineContainer = document.getElementById("timeline");
const frameworkModules = document.getElementById("framework-modules");
const frameworkNative = document.getElementById("framework-native");
const frameworkValidation = document.getElementById("framework-validation");
const recipeGrid = document.getElementById("recipe-grid");
const directionGrid = document.getElementById("direction-grid");
const antiSlopList = document.getElementById("anti-slop-list");
const critiqueRubric = document.getElementById("critique-rubric");
const contextProtocol = document.getElementById("context-protocol");
const tweakControls = document.getElementById("tweak-controls");
const verificationSteps = document.getElementById("verification-steps");
const handoffArtifacts = document.getElementById("handoff-artifacts");

const docList = [
  {{ title: "PRD 文档", desc: "产品目标、需求边界、验收标准", path: DATA.docs.prd }},
  {{ title: "架构文档", desc: "模块划分、接口契约、部署策略", path: DATA.docs.architecture }},
  {{ title: "UI/UX 文档", desc: "视觉系统、交互规则、页面结构", path: DATA.docs.uiux }},
  {{ title: "执行路线图", desc: "0-1 与 1-N+1 的分阶段推进", path: DATA.docs.plan }},
  {{ title: "前端蓝图", desc: "前端模块拆分与先行交付策略", path: DATA.docs.frontend_blueprint }},
];

for (const doc of docList) {{
  if (!doc.path) continue;
  const link = document.createElement("a");
  link.className = "doc-item";
  link.href = relativePath(doc.path);
  link.target = "_blank";
  link.rel = "noreferrer";
  link.innerHTML = `<b>${{doc.title}}</b><span>${{doc.desc}}</span>`;
  docContainer.appendChild(link);
}}

for (const req of DATA.requirements) {{
  const chip = document.createElement("span");
  chip.className = "chip";
  chip.textContent = `${{req.spec_name}} · ${{req.req_name}}`;
  reqContainer.appendChild(chip);
}}

for (const phase of DATA.phases) {{
  const li = document.createElement("li");
  li.innerHTML = `<b>${{phase.title}}</b><p>${{phase.objective}}</p>`;
  timelineContainer.appendChild(li);
}}

for (const recipe of DATA.ui_contract.screen_recipes || []) {{
  if (!recipeGrid) break;
  const article = document.createElement("article");
  article.className = "recipe-card";
  const sections = (recipe.section_order || []).slice(0, 4).join(" / ");
  const trustCount = (recipe.trust_modules || []).length;
  const stateCount = (recipe.required_states || []).length;
  article.innerHTML = `
    <h3>${{recipe.label || "Screen Recipe"}}</h3>
    <p>${{recipe.objective || ""}}</p>
    <p><b>方向</b>: ${{recipe.art_direction || "-"}}</p>
    <p><b>结构</b>: ${{sections || "-"}}</p>
    <div class="recipe-meta">
      <span>${{recipe.surface || "-"}}</span>
      <span>Trust ${{trustCount}}</span>
      <span>States ${{stateCount}}</span>
    </div>
  `;
  recipeGrid.appendChild(article);
}}

for (const direction of DATA.ui_contract.art_direction_candidates || []) {{
  if (!directionGrid) break;
  const article = document.createElement("article");
  article.className = "recipe-card";
  article.innerHTML = `
    <h3>${{direction.name || "Art Direction"}}</h3>
    <p>${{direction.philosophy || ""}}</p>
    <p><b>Hero</b>: ${{direction.hero_treatment || "-"}}</p>
    <p><b>Proof</b>: ${{direction.proof_strategy || "-"}}</p>
  `;
  directionGrid.appendChild(article);
}}

for (const item of DATA.ui_contract.anti_ai_slop_guardrails?.forbidden_motifs || []) {{
  if (!antiSlopList) break;
  const li = document.createElement("li");
  li.textContent = item;
  antiSlopList.appendChild(li);
}}

for (const item of DATA.ui_contract.critique_rubric || []) {{
  if (!critiqueRubric) break;
  const li = document.createElement("li");
  li.textContent = `${{item.label || item.dimension || "Criterion"}} ≥ ${{item.pass_threshold || "-"}}/10`;
  critiqueRubric.appendChild(li);
}}

for (const item of DATA.ui_contract.design_context_protocol?.preferred_import_order || []) {{
  if (!contextProtocol) break;
  const li = document.createElement("li");
  li.textContent = item;
  contextProtocol.appendChild(li);
}}

for (const item of DATA.ui_contract.tweak_strategy?.default_controls || []) {{
  if (!tweakControls) break;
  const li = document.createElement("li");
  li.textContent = item;
  tweakControls.appendChild(li);
}}

for (const item of DATA.ui_contract.verification_handoff?.verification_order || []) {{
  if (!verificationSteps) break;
  const li = document.createElement("li");
  li.textContent = item;
  verificationSteps.appendChild(li);
}}

for (const item of DATA.ui_contract.verification_handoff?.required_artifacts || []) {{
  if (!handoffArtifacts) break;
  const li = document.createElement("li");
  li.textContent = item;
  handoffArtifacts.appendChild(li);
}}

const frameworkPlaybook = DATA.ui_contract.framework_playbook || null;
if (frameworkPlaybook && frameworkModules && frameworkNative && frameworkValidation) {{
  for (const item of frameworkPlaybook.implementation_modules || []) {{
    const li = document.createElement("li");
    li.textContent = item;
    frameworkModules.appendChild(li);
  }}
  for (const item of frameworkPlaybook.native_capabilities || []) {{
    const li = document.createElement("li");
    li.textContent = item;
    frameworkNative.appendChild(li);
  }}
  for (const item of frameworkPlaybook.validation_surfaces || []) {{
    const li = document.createElement("li");
    li.textContent = item;
    frameworkValidation.appendChild(li);
  }}
}}

function relativePath(path) {{
  if (!path) return "#";
  const normalized = String(path).replace(/\\\\/g, "/");
  const marker = "/output/";
  const index = normalized.lastIndexOf(marker);
  if (index >= 0) {{
    return ".." + normalized.slice(index + marker.length - 1);
  }}
  return "#";
}}
"""

    def _load_ui_contract(self) -> dict:
        contract_path = self.project_dir / "output" / ui_contract_filename(self.name)
        if contract_path.exists():
            try:
                payload = json.loads(contract_path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("UI 契约必须是 JSON 对象")
                return payload
            except (json.JSONDecodeError, OSError):
                pass

        from super_dev.creators.document_generator import DocumentGenerator

        generator = DocumentGenerator(
            name=self.name,
            description=self.description,
            platform="web",
            frontend=self.frontend,
            backend="node",
        )
        contract = generator.generate_ui_contract()
        if isinstance(contract, dict):
            contract.setdefault(
                "_artifact_meta",
                {
                    "generated_by": "FrontendScaffoldBuilder._load_ui_contract",
                    "reason": "ui-contract artifact was missing and has been materialized for downstream stages",
                },
            )
            contract_path.parent.mkdir(parents=True, exist_ok=True)
            contract_path.write_text(
                json.dumps(contract, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return contract

    def _build_google_fonts_url(self, typography: dict) -> str:
        families: list[str] = []
        for font in (typography.get("heading"), typography.get("body")):
            token = str(font or "").strip()
            if not token:
                continue
            family = token.replace(" ", "+")
            query = f"family={family}:wght@400;500;600;700;800"
            if query not in families:
                families.append(query)
        if not families:
            families = [
                "family=Manrope:wght@400;500;600;700;800",
                "family=Source+Sans+3:wght@400;500;600;700",
            ]
        return "https://fonts.googleapis.com/css2?" + "&".join(families) + "&display=swap"

    def _lighten(self, hex_color: str, factor: float) -> str:
        hex_color = str(hex_color).lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{min(r, 255):02X}{min(g, 255):02X}{min(b, 255):02X}"

    def _darken(self, hex_color: str, factor: float) -> str:
        hex_color = str(hex_color).lstrip("#")
        if len(hex_color) != 6:
            return f"#{hex_color}"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{max(r, 0):02X}{max(g, 0):02X}{max(b, 0):02X}"

    def _alpha(self, hex_color: str, alpha: float) -> str:
        hex_color = str(hex_color).lstrip("#")
        if len(hex_color) != 6:
            return "rgba(0, 0, 0, 0.08)"
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha:.2f})"

    # ------------------------------------------------------------------
    # React + Vite Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Expo / React Native Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Flutter Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # MiniApp Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Desktop Shell Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Hybrid Shell Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Vue 3 Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Angular Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Svelte Project Template
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Design System Scaffold
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Test Configuration Generation
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Performance Optimization Configuration
    # ------------------------------------------------------------------
