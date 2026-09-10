"""
UI 审查器 - 审查商业级 UI/UX 完成度

目标：
1. 检查 UI/UX 文档是否具备商业级设计基线
2. 检查前端源码是否偏离设计基线或出现明显 AI 模板化反模式
3. 输出可追踪的 UI 审查报告，供质量门禁与交付阶段使用
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, cast

from PIL import Image

from super_dev.artifact_utils import ui_contract_filename

from ..design import UIIntelligenceAdvisor
from .ui_review_execution_mixin import UIReviewExecutionMixin
from .ui_review_models import (
    UIReviewFinding,
    UIReviewReport,
    _HTMLSurfaceParser,
    shutil_which,
)

_logger = logging.getLogger("super_dev.reviewers.ui_review")

__all__ = ["UIReviewFinding", "UIReviewReport", "UIReviewReviewer"]


class UIReviewReviewer(UIReviewExecutionMixin):
    """商业级 UI 审查器"""

    MARKETING_KEYWORDS = ("hero", "testimonial", "pricing", "faq", "case study", "social proof")
    STATE_KEYWORDS = ("loading", "empty", "error", "disabled", "focus", "success")
    TOKEN_KEYWORDS = ("--color-", "--space-", "--radius-", "--shadow-", "--font-")
    DEFAULT_FONT_RE = re.compile(
        r"(font-family\s*:\s*['\"]?(inter|arial|system-ui|ui-sans-serif|sans-serif)|fontFamily\s*[:=]\s*['\"]?(Inter|Arial|system-ui))",
        re.IGNORECASE,
    )
    HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    EMOJI_RE = re.compile(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]")
    SUSPICIOUS_PATTERN_RE = re.compile(
        r"(purple-|pink-|bg-gradient|linear-gradient|emoji|🚀|✨|🎨|🔥|💎|🤖)",
        re.IGNORECASE,
    )
    CLAUDE_CLONE_RE = re.compile(
        r"(anthropic|claude|chat-sidebar|conversation-list|thread-list|assistant-message|model-selector|conversation-shell|chat-shell)",
        re.IGNORECASE,
    )

    TRUST_TERMS = (
        "testimonial",
        "case study",
        "customer",
        "clients",
        "security",
        "compliance",
        "faq",
        "review",
        "rating",
        "trusted by",
        "案例",
        "客户",
        "评价",
        "安全",
        "合规",
        "FAQ",
        "信任",
    )

    UIUX_DECISION_PATTERNS = {
        "style_direction": re.compile(r"\*\*主视觉气质\*\*:\s*(.+)"),
        "font_pair": re.compile(r"\*\*字体组合\*\*:\s*(.+)"),
        "color_logic": re.compile(r"\*\*配色逻辑\*\*:\s*(.+)"),
        "icon_system": re.compile(r"\*\*图标系统\*\*:\s*(.+)"),
        "primary_library": re.compile(r"\*\*首选组件生态\*\*:\s*(.+)"),
    }

    def __init__(self, project_dir: Path, name: str, tech_stack: dict[str, Any]):
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.tech_stack = tech_stack

        # 加载 UI / UX 专家工具箱
        try:
            from ..experts.toolkit import load_expert_toolkits

            toolkits = load_expert_toolkits()
            self._ui_toolkit = toolkits.get("UI")
            self._ux_toolkit = toolkits.get("UX")
        except Exception:
            self._ui_toolkit = None
            self._ux_toolkit = None

    # ------------------------------------------------------------------
    # UI/UX 专家视角
    # ------------------------------------------------------------------

    def _collect_expert_review_dimensions(self, role: str, phase: str) -> list[str]:
        """从专家工具箱提取指定角色在指定阶段的审查维度。"""
        toolkit = self._ui_toolkit if role == "UI" else self._ux_toolkit
        if toolkit is None:
            return []
        try:
            return toolkit.get_review_checklist(phase)
        except Exception:
            return []

    def _run_expert_perspective_checks(
        self,
        *,
        source_content: str,
        preview_content: str,
        uiux_content: str,
        ui_expert_dimensions: list[str],
        ux_expert_dimensions: list[str],
    ) -> list[UIReviewFinding]:
        """基于 UI/UX 专家工具箱的检查维度生成额外审查发现。

        UI 专家关注：设计 Token 系统、品牌一致性、组件状态完整性、反 AI 模板感
        UX 专家关注：用户旅程、导航层级、表单设计、可访问性
        """
        findings: list[UIReviewFinding] = []
        combined = "\n".join([source_content, preview_content]).lower()

        if not source_content and not preview_content:
            return findings

        # --- UI 专家维度 ---
        if ui_expert_dimensions:
            # 设计 Token 系统完整性
            token_categories = {
                "color": ("--color-", "color-primary", "color-secondary", "color-accent"),
                "space": ("--space-", "spacing-", "gap-", "padding-"),
                "font": ("--font-", "font-size-", "font-weight-", "line-height-"),
                "radius": ("--radius-", "border-radius-", "rounded-"),
                "shadow": ("--shadow-", "box-shadow-", "shadow-"),
            }
            missing_categories = [
                cat
                for cat, tokens in token_categories.items()
                if not any(t in combined for t in tokens)
            ]
            if len(missing_categories) >= 3:
                findings.append(
                    UIReviewFinding(
                        level="high",
                        title="[UI 专家] Token 体系覆盖不完整",
                        description=(
                            "UI 专家要求 Token 体系覆盖颜色/字体/间距/圆角/阴影五大类，"
                            f"当前缺失 {len(missing_categories)} 类。"
                        ),
                        recommendation="按 UI 专家规范补齐缺失的 Token 类别，确保组件复用同一套视觉变量。",
                        evidence=[f"缺失: {', '.join(missing_categories)}"],
                    )
                )

            # 品牌一致性：检查是否存在多套不一致的视觉系统
            brand_signals = ("brand", "logo", "primary", "accent", "--color-brand", "theme")
            brand_hits = sum(1 for s in brand_signals if s in combined)
            if brand_hits == 0 and source_content:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="[UI 专家] 品牌识别信号缺失",
                        description="源码和预览中缺少品牌色、Logo 引用或主题标识，产品辨识度不足。",
                        recommendation="在全局样式或 Token 层定义品牌主色、辅助色和 Logo 使用规范。",
                    )
                )

            # 组件状态完整性（UI 专家更严格的标准）
            ui_state_keywords = (
                "hover",
                "focus",
                "active",
                "disabled",
                "loading",
                "error",
                "empty",
                "success",
            )
            covered_states = [kw for kw in ui_state_keywords if kw in combined]
            if len(covered_states) < 4 and source_content:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="[UI 专家] 组件状态矩阵不齐全",
                        description=(
                            f"UI 专家要求组件覆盖 hover/focus/loading/empty/error/disabled 等状态，"
                            f"当前仅检测到 {len(covered_states)} 种。"
                        ),
                        recommendation="为核心交互组件补齐状态样式，确保每种状态都有明确的视觉反馈。",
                        evidence=[f"已覆盖: {', '.join(covered_states) or '无'}"],
                    )
                )

            # 反 AI 模板感（UI 专家的补充检查）
            ai_template_signals = (
                "bg-gradient-to-r from-purple",
                "bg-gradient-to-br from-pink",
                "animate-pulse",
                "animate-bounce",
                "backdrop-blur",
            )
            ai_hits = [s for s in ai_template_signals if s in combined]
            if len(ai_hits) >= 2:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="[UI 专家] AI 模板化视觉痕迹偏重",
                        description="检测到多个 AI 常见模板化样式叠加，界面容易失去品牌差异化。",
                        recommendation="删除堆砌的渐变和动画效果，回归设计文档规定的品牌方向。",
                        evidence=ai_hits[:6],
                    )
                )

        # --- UX 专家维度 ---
        if ux_expert_dimensions:
            # 用户旅程：检查核心任务流信号
            journey_signals = (
                "onboarding",
                "wizard",
                "stepper",
                "step-",
                "progress",
                "breadcrumb",
                "flow",
                "funnel",
                "引导",
                "步骤",
                "流程",
            )
            journey_hits = sum(1 for s in journey_signals if s in combined)
            if journey_hits == 0 and source_content:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="[UX 专家] 缺少用户旅程引导信号",
                        description="UX 专家要求核心任务流有清晰的步骤引导，但源码中缺少 onboarding、stepper、progress 等信号。",
                        recommendation="为关键任务流加入步骤指示器、进度条或面包屑导航，降低用户认知负荷。",
                    )
                )

            # 导航层级：检测导航深度
            deep_nav_signals = ("sub-subnav", "nested-dropdown", "三级菜单", "deep-nav")
            has_deep_nav = any(s in combined for s in deep_nav_signals)
            if has_deep_nav:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="[UX 专家] 导航层级可能超过 3 层",
                        description="UX 专家要求导航层级不超过 3 层，检测到深层嵌套导航信号。",
                        recommendation="精简导航结构，将深层页面通过搜索、标签或快捷入口替代多层级嵌套。",
                    )
                )

            # 表单设计：检查表单验证和错误处理
            form_signals = ("form", "<form", "input", "textarea", "select")
            has_forms = any(s in combined for s in form_signals)
            if has_forms:
                validation_signals = (
                    "validation",
                    "validate",
                    "error-message",
                    "field-error",
                    "invalid",
                    "required",
                    "pattern=",
                    "helpertext",
                    "errormessage",
                    "formerror",
                )
                has_validation = any(s in combined for s in validation_signals)
                if not has_validation:
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="[UX 专家] 表单缺少验证与错误恢复机制",
                            description="UX 专家要求表单具备实时验证和错误恢复指引，但未检测到明显的验证逻辑。",
                            recommendation="为表单字段添加实时校验、错误提示和恢复引导，减少用户填写挫败感。",
                        )
                    )

            # 可访问性：检查 WCAG 基础信号
            a11y_signals = (
                "aria-",
                "role=",
                "sr-only",
                "screen-reader",
                "alt=",
                "tabindex",
                "focus-visible",
                "focus-trap",
                "labelledby",
                "describedby",
            )
            a11y_hits = sum(1 for s in a11y_signals if s in combined)
            if a11y_hits < 2 and source_content:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="[UX 专家] 可访问性基线不足",
                        description=(
                            "UX 专家要求满足 WCAG 2.1 AA 标准，但源码中缺少足够的 "
                            "aria 属性、role 标注或 focus 管理信号。"
                        ),
                        recommendation="为交互元素添加 aria-label、role 属性，确保键盘导航和屏幕阅读器可用。",
                        evidence=[f"a11y 信号数: {a11y_hits}"],
                    )
                )

        return findings

    def _collect_frontend_files(self) -> list[Path]:
        allowed_suffixes = {
            ".tsx",
            ".ts",
            ".jsx",
            ".js",
            ".vue",
            ".svelte",
            ".css",
            ".scss",
            ".less",
            ".html",
        }
        excluded_dirs = {
            "node_modules",
            ".git",
            ".venv",
            "venv",
            "dist",
            "build",
            ".next",
            "coverage",
        }
        candidate_roots = [
            self.project_dir / "output" / "frontend",
            self.project_dir / "frontend",
            self.project_dir / "src",
            self.project_dir / "app",
            self.project_dir / "components",
            self.project_dir / "pages",
            self.project_dir / "super-dev-website" / "app",
            self.project_dir / "super-dev-website" / "components",
            self.project_dir / "super-dev-website" / "styles",
            self.project_dir / "super-dev-website" / "lib",
        ]
        files: list[Path] = []
        seen: set[Path] = set()
        for root in candidate_roots:
            if not root.exists():
                continue
            iterator = [root] if root.is_file() else root.rglob("*")
            for path in iterator:
                if not path.is_file():
                    continue
                if path.suffix.lower() not in allowed_suffixes:
                    continue
                if any(part in excluded_dirs for part in path.parts):
                    continue
                if path not in seen:
                    seen.add(path)
                    files.append(path)
        return files

    def _find_preview_file(self) -> Path | None:
        candidates = [
            self.project_dir / "preview.html",
            self.project_dir / "output" / "frontend" / "index.html",
            self.project_dir / "frontend" / "index.html",
            self.project_dir / "super-dev-website" / "out" / "index.html",
            self.project_dir / "index.html",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _capture_preview_screenshot(self, preview_path: Path) -> Path | None:
        if os.getenv("SUPER_DEV_DISABLE_VISUAL_CAPTURE") == "1" or os.getenv("PYTEST_CURRENT_TEST"):
            return None
        if not shutil_which("npx"):
            return None

        artifact_dir = self.project_dir / "output" / "ui-review"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = artifact_dir / f"{self.name}-preview-desktop.png"
        url = preview_path.resolve().as_uri()

        cmd = [
            "npx",
            "-y",
            "playwright",
            "screenshot",
            "--device=Desktop Chrome",
            url,
            str(screenshot_path),
        ]

        try:
            subprocess.run(  # nosec B603
                cmd,
                cwd=str(self.project_dir),
                check=True,
                capture_output=True,
                text=True,
                timeout=45,
            )
        except Exception as e:
            _logger.debug(f"Failed to capture preview screenshot: {e}")
            return None

        return screenshot_path if screenshot_path.exists() else None

    def _analyze_screenshot(
        self, screenshot_path: Path | None
    ) -> dict[str, float] | dict[str, int]:
        if not screenshot_path or not screenshot_path.exists():
            return {}
        try:
            with Image.open(screenshot_path) as image:
                rgb = image.convert("RGB")
                width, height = rgb.size
                sample = rgb.resize((min(220, width), min(220, height)))
                pixels = cast(
                    list[tuple[int, int, int]],
                    list(sample.get_flattened_data()),
                )
        except Exception as e:
            _logger.debug(f"Failed to analyze screenshot: {e}")
            return {}

        if not pixels:
            return {}

        blank_pixels = 0
        accent_pixels = 0
        reduced = []
        brightness_values: list[float] = []
        for r, g, b in pixels:
            brightness = (r + g + b) / 3
            spread = max(r, g, b) - min(r, g, b)
            brightness_values.append(brightness)
            if brightness > 235 and spread < 16:
                blank_pixels += 1
            if spread > 60 and 35 < brightness < 220:
                accent_pixels += 1
            reduced.append((r // 32, g // 32, b // 32))

        total = len(pixels)
        color_histogram: dict[tuple[int, int, int], int] = {}
        for color in reduced:
            color_histogram[color] = color_histogram.get(color, 0) + 1
        dominant_color_ratio = (max(color_histogram.values()) / total) if color_histogram else 1.0
        contrast_span = (
            (max(brightness_values) - min(brightness_values)) / 255 if brightness_values else 0.0
        )
        return {
            "blank_ratio": blank_pixels / total,
            "accent_ratio": accent_pixels / total,
            "unique_colors": len(set(reduced)),
            "dominant_color_ratio": dominant_color_ratio,
            "contrast_span": contrast_span,
        }

    def _read_package_json(self) -> dict[str, Any] | None:
        for candidate in (
            self.project_dir / "package.json",
            self.project_dir / "frontend" / "package.json",
        ):
            if candidate.exists():
                try:
                    payload: object = json.loads(candidate.read_text(encoding="utf-8"))
                    return cast(dict[str, Any], payload) if isinstance(payload, dict) else None
                except (json.JSONDecodeError, OSError):
                    return None
        return None

    def _load_ui_contract(self) -> dict[str, Any]:
        contract_path = self.project_dir / "output" / ui_contract_filename(self.name)
        if not contract_path.exists():
            return {}
        try:
            payload: object = json.loads(contract_path.read_text(encoding="utf-8"))
        except Exception as e:
            _logger.debug(f"Failed to parse UI contract: {e}")
            return {}
        return cast(dict[str, Any], payload) if isinstance(payload, dict) else {}

    def _load_frontend_runtime_report(self) -> dict[str, Any]:
        runtime_path = self.project_dir / "output" / f"{self.name}-frontend-runtime.json"
        if not runtime_path.exists():
            return {}
        try:
            payload: object = json.loads(runtime_path.read_text(encoding="utf-8"))
        except Exception as e:
            _logger.debug(f"Failed to parse frontend runtime report: {e}")
            return {}
        return cast(dict[str, Any], payload) if isinstance(payload, dict) else {}

    def _normalized_contains_any(self, combined: str, candidates: list[str]) -> bool:
        lowered = combined.lower()
        normalized = re.sub(r"[-_/]+", " ", lowered)
        for candidate in candidates:
            token = str(candidate).strip().lower()
            if not token:
                continue
            if "/" in token:
                token = Path(token).name.lower()
            normalized_token = re.sub(r"[-_/]+", " ", token)
            if token in lowered or normalized_token in normalized:
                return True
        return False

    def _check_claude_design_protocol_execution(
        self,
        *,
        ui_contract: dict[str, Any],
        source_content: str,
        preview_content: str,
    ) -> dict[str, bool]:
        combined = "\n".join([source_content, preview_content])
        states: dict[str, bool] = {}
        screen_recipes = (
            ui_contract.get("screen_recipes")
            if isinstance(ui_contract.get("screen_recipes"), list)
            else []
        )
        if screen_recipes:
            labels = [
                str(item.get("label", "")).strip()
                for item in screen_recipes
                if isinstance(item, dict)
            ]
            sections = [
                str(section).strip()
                for item in screen_recipes
                if isinstance(item, dict)
                for section in item.get("section_order", []) or []
            ]
            trust_modules = [
                str(module).strip()
                for item in screen_recipes
                if isinstance(item, dict)
                for module in item.get("trust_modules", []) or []
            ]
            required_states = [
                str(state).strip()
                for item in screen_recipes
                if isinstance(item, dict)
                for state in item.get("required_states", []) or []
            ]
            states["screen_recipes"] = (
                self._normalized_contains_any(combined, labels)
                and self._normalized_contains_any(combined, sections)
                and (
                    self._normalized_contains_any(combined, trust_modules)
                    or self._normalized_contains_any(combined, required_states)
                )
            )

        design_context_protocol = (
            ui_contract.get("design_context_protocol")
            if isinstance(ui_contract.get("design_context_protocol"), dict)
            else {}
        )
        if design_context_protocol:
            states["design_context_protocol"] = self._normalized_contains_any(
                combined,
                [
                    *(
                        str(item).strip()
                        for item in design_context_protocol.get("preferred_import_order", []) or []
                    ),
                    *(
                        str(item).strip()
                        for item in design_context_protocol.get("github_import_targets", []) or []
                    ),
                ],
            ) and self._normalized_contains_any(
                combined,
                [str(design_context_protocol.get("single_source_rule", "")).strip()],
            )

        tweak_strategy = (
            ui_contract.get("tweak_strategy")
            if isinstance(ui_contract.get("tweak_strategy"), dict)
            else {}
        )
        if tweak_strategy:
            states["tweak_strategy"] = (
                self._normalized_contains_any(
                    combined, [str(tweak_strategy.get("mode", "")).strip()]
                )
                and self._normalized_contains_any(
                    combined,
                    [
                        str(item).strip()
                        for item in tweak_strategy.get("default_controls", []) or []
                    ],
                )
                and self._normalized_contains_any(
                    combined, [str(tweak_strategy.get("persistence_rule", "")).strip()]
                )
            )

        verification_handoff = (
            ui_contract.get("verification_handoff")
            if isinstance(ui_contract.get("verification_handoff"), dict)
            else {}
        )
        if verification_handoff:
            states["verification_handoff"] = (
                self._normalized_contains_any(
                    combined,
                    [
                        str(item).strip()
                        for item in verification_handoff.get("verification_order", []) or []
                    ],
                )
                and self._normalized_contains_any(
                    combined,
                    [
                        str(item).strip()
                        for item in verification_handoff.get("required_artifacts", []) or []
                    ],
                )
                and self._normalized_contains_any(
                    combined,
                    [
                        str(item).strip()
                        for item in verification_handoff.get("acceptance_checks", []) or []
                    ],
                )
            )
        return states

    def _load_project_config(self) -> dict[str, Any]:
        config_path = self.project_dir / "super-dev.yaml"
        if not config_path.exists():
            return {}
        try:
            import yaml  # type: ignore[import-untyped]

            return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            _logger.debug(f"Failed to load project config: {e}")
            return {}

    def _infer_product_type(self, description: str) -> str:
        text = description.lower()
        if any(
            word in text for word in ["dashboard", "仪表盘", "后台", "admin", "工作台", "workspace"]
        ):
            return "dashboard"
        if any(
            word in text for word in ["landing", "落地页", "营销页", "官网", "official website"]
        ):
            return "landing"
        if any(word in text for word in ["saas", "平台", "platform", "软件服务"]):
            return "saas"
        if any(word in text for word in ["商城", "电商", "store", "shop", "checkout"]):
            return "ecommerce"
        if any(word in text for word in ["博客", "内容", "blog", "cms", "文档"]):
            return "content"
        return "general"

    def _infer_industry(self, description: str) -> str:
        text = description.lower()
        if any(word in text for word in ["医疗", "健康", "health", "medical", "care"]):
            return "healthcare"
        if any(word in text for word in ["金融", "支付", "bank", "fintech", "结算"]):
            return "fintech"
        if any(word in text for word in ["教育", "培训", "education", "learning"]):
            return "education"
        if any(word in text for word in ["法律", "法务", "legal", "律师"]):
            return "legal"
        if any(word in text for word in ["政务", "government", "public"]):
            return "government"
        if any(word in text for word in ["美容", "美业", "wellness", "beauty", "spa"]):
            return "beauty"
        return "general"

    def _infer_style(self, description: str) -> str:
        text = description.lower()
        if any(word in text for word in ["极简", "minimal", "简约"]):
            return "minimal"
        if any(word in text for word in ["专业", "商务", "professional", "business"]):
            return "professional"
        if any(word in text for word in ["活泼", "playful", "fun"]):
            return "playful"
        if any(word in text for word in ["奢华", "premium", "luxury", "高端"]):
            return "luxury"
        return "modern"

    def _is_cross_platform_frontend(self, frontend: str) -> bool:
        normalized = UIIntelligenceAdvisor.FRONTEND_ALIASES.get(
            frontend.lower().strip(), frontend.lower().strip()
        )
        return normalized in {"miniapp", "react-native", "flutter", "desktop"}

    def _framework_playbook_complete(self, playbook: dict[str, Any]) -> bool:
        if not playbook:
            return False
        required_lists = (
            "implementation_modules",
            "platform_constraints",
            "execution_guardrails",
            "native_capabilities",
            "validation_surfaces",
            "delivery_evidence",
        )
        return bool(playbook.get("framework")) and all(
            isinstance(playbook.get(name), list) and bool(playbook.get(name))
            for name in required_lists
        )

    def _inspect_preview_html(self, html: str) -> dict[str, int]:
        parser = _HTMLSurfaceParser(self.TRUST_TERMS)
        parser.feed(html)
        parser.close()
        return parser.summary()

    def _extract_uiux_decisions(self, uiux_content: str) -> dict[str, str]:
        decisions: dict[str, str] = {}
        for key, pattern in self.UIUX_DECISION_PATTERNS.items():
            match = pattern.search(uiux_content)
            if not match:
                continue
            decisions[key] = match.group(1).strip()
        return decisions

    def _resolve_contract_or_doc_value(
        self,
        *,
        contract: dict[str, Any],
        decisions: dict[str, str],
        contract_key: str,
        decision_key: str,
    ) -> str:
        contract_value = contract.get(contract_key)
        if isinstance(contract_value, str) and contract_value.strip():
            return contract_value.strip()
        if contract_key == "icon_system":
            component_stack = contract.get("component_stack")
            if isinstance(component_stack, dict):
                nested_icon_system = component_stack.get("icon") or component_stack.get("icons")
                if isinstance(nested_icon_system, str) and nested_icon_system.strip():
                    return nested_icon_system.strip()
        return decisions.get(decision_key, "")

    def _resolve_font_pair(self, contract: dict[str, Any], decisions: dict[str, str]) -> str:
        typography = contract.get("typography_preset")
        if isinstance(typography, dict):
            heading = str(typography.get("heading", "")).strip()
            body = str(typography.get("body", "")).strip()
            if heading or body:
                return " / ".join(item for item in [heading, body] if item)
        return decisions.get("font_pair", "")

    def _resolve_primary_library(self, contract: dict[str, Any], decisions: dict[str, str]) -> str:
        preference = contract.get("ui_library_preference")
        if isinstance(preference, dict):
            selected = str(preference.get("final_selected", "")).strip()
            if selected:
                return selected
        primary = contract.get("primary_library")
        if isinstance(primary, dict):
            name = str(primary.get("name", "")).strip()
            if name:
                return name
        return decisions.get("primary_library", "")

    def _has_design_token_contract_wiring(
        self,
        *,
        source_content: str,
        preview_content: str,
        design_tokens_content: str,
    ) -> bool:
        combined = "\n".join([source_content, preview_content]).lower()
        if "design-tokens.css" in combined:
            return True
        if "var(--color-" in combined or "var(--space-" in combined or "var(--font-" in combined:
            return True
        if design_tokens_content and (
            "--color-" in design_tokens_content or "--font-" in design_tokens_content
        ):
            return "var(--" in combined
        return False

    def _has_theme_entry_contract_wiring(
        self,
        *,
        source_content: str,
        preview_content: str,
        design_tokens_content: str,
    ) -> bool:
        combined = "\n".join([source_content, preview_content]).lower()
        theme_signals = (
            "themeprovider",
            "configprovider",
            "cssvarsprovider",
            "chakraprovider",
            "mantineprovider",
            "vuetify",
            "createTheme".lower(),
            "theme=",
            "data-theme",
            "design-tokens.css",
        )
        if any(signal in combined for signal in theme_signals):
            return True
        if "--color-" in design_tokens_content or "--font-" in design_tokens_content:
            return "var(--" in combined
        return False

    def _extract_navigation_shell_markers(self, source_content: str) -> list[str]:
        if not source_content:
            return []
        lowered = source_content.lower()
        candidates = (
            ("<nav", "nav"),
            ("<header", "header"),
            ("<aside", "aside"),
            ("sidebar", "sidebar"),
            ("topbar", "topbar"),
            ("breadcrumb", "breadcrumb"),
            ("appshell", "appshell"),
            ("navigationmenu", "navigationmenu"),
            ("menubar", "menubar"),
        )
        found: list[str] = []
        for needle, label in candidates:
            if needle in lowered and label not in found:
                found.append(label)
        return found

    def _extract_token_variables(self, design_tokens_content: str) -> list[str]:
        if not design_tokens_content:
            return []
        matches = re.findall(
            r"(--(?:color|space|font|radius|shadow)-[a-z0-9-]+)\s*:",
            design_tokens_content,
            flags=re.IGNORECASE,
        )
        ordered = []
        seen: set[str] = set()
        for item in matches:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    def _expected_icon_tokens(self, icon_system: str) -> tuple[str, ...]:
        lowered = icon_system.lower()
        if "lucide" in lowered:
            return ("lucide", "@lucide", "lucide-react", "lucide-vue", "lucide-svelte")
        if "heroicons" in lowered:
            return ("heroicons", "@heroicons")
        if "tabler" in lowered:
            return ("tabler", "@tabler")
        if "phosphor" in lowered:
            return ("phosphor", "@phosphor")
        if "tdesign" in lowered:
            return ("tdesign-icons", "tdesign")
        return ()

    def _expected_font_tokens(self, font_pair: str) -> tuple[str, ...]:
        parts = []
        for item in font_pair.split("/"):
            token = item.strip().lower().replace("  ", " ")
            token = token.replace("-", " ")
            if token:
                parts.append(token)
        return tuple(parts)

    def _expected_library_tokens(self, primary_library: str) -> tuple[str, ...]:
        lowered = primary_library.lower()
        if "shadcn" in lowered or "radix" in lowered:
            return ("@radix-ui", "shadcn", "class-variance-authority", "tailwindcss")
        if "magic ui" in lowered:
            return ("magicui", "magic ui", "motion", "framer-motion")
        if "aceternity" in lowered:
            return ("aceternity", "framer-motion", "motion")
        if "daisyui" in lowered:
            return ("daisyui", "tailwindcss")
        if "headless ui" in lowered:
            return ("@headlessui", "headlessui", "tailwindcss")
        if "nextui" in lowered or "heroui" in lowered:
            return ("@nextui-org", "@heroui", "nextui", "heroui")
        if "tremor" in lowered:
            return ("@tremor", "tremor")
        if "naive ui" in lowered:
            return ("naive-ui",)
        if "tdesign" in lowered:
            return ("tdesign",)
        if "chakra" in lowered:
            return ("@chakra-ui",)
        if "ant design" in lowered or "antd" in lowered:
            return ("antd", "@ant-design")
        if "vuetify" in lowered:
            return ("vuetify",)
        return ()

    def _expected_component_import_tokens(self, primary_library: str) -> tuple[str, ...]:
        lowered = primary_library.lower()
        if "shadcn" in lowered or "radix" in lowered:
            return ("@/components/ui", "/components/ui/", "components/ui/", "@radix-ui")
        if "magic ui" in lowered:
            return (
                "magicui",
                "@/components/magicui",
                "/components/magicui/",
                "components/magicui/",
            )
        if "aceternity" in lowered:
            return ("aceternity", "@/components/ui", "/components/ui/")
        if "daisyui" in lowered:
            return ("daisyui",)
        if "headless ui" in lowered:
            return ("@headlessui",)
        if "nextui" in lowered or "heroui" in lowered:
            return ("@nextui-org", "@heroui")
        if "tremor" in lowered:
            return ("@tremor",)
        if "naive ui" in lowered:
            return ("naive-ui",)
        if "tdesign" in lowered:
            return ("tdesign",)
        if "chakra" in lowered:
            return ("@chakra-ui",)
        if "ant design" in lowered or "antd" in lowered:
            return ("antd", "@ant-design")
        if "vuetify" in lowered:
            return ("vuetify",)
        return ()

    def _expected_framework_tokens(self, framework: str) -> tuple[str, ...]:
        lowered = framework.lower().strip()
        if lowered == "uni-app":
            return (
                "uni.",
                "#ifdef",
                "navigationstyle",
                "statusbarheight",
                "provider",
                "mp-weixin",
                "safe-area",
                "renderjs",
                "wxs",
            )
        if lowered == "taro":
            return (
                "@tarojs",
                "taro.",
                "usedidshow",
                "userachbottom",
                "process.env.taro_env",
                "taro.navigate",
            )
        if lowered == "react native":
            return (
                "react-native",
                "@react-navigation",
                "safeareaview",
                "linking",
                "permissionsandroid",
                "expo-notifications",
                "reanimated",
            )
        if lowered == "flutter":
            return (
                "materialapp",
                "themedata",
                "cupertino",
                "mediaquery",
                "gorouter",
                "navigator",
                "widgetsapp",
            )
        if lowered == "desktop web shell":
            return (
                "electron",
                "tauri",
                "ipc",
                "tray",
                "menu",
                "shortcut",
                "filesystem",
                "offline",
            )
        return ()

    def _check_framework_playbook_execution(
        self,
        *,
        framework_playbook: dict[str, Any],
        source_content: str,
        preview_content: str,
        dependency_blob: str,
    ) -> dict[str, Any]:
        framework = str(framework_playbook.get("framework") or "").strip()
        expected_tokens = self._expected_framework_tokens(framework)
        combined = "\n".join(
            [dependency_blob.lower(), source_content.lower(), preview_content.lower()]
        )
        matched = [token for token in expected_tokens if token and token in combined]
        required_hits = 2 if framework in {"React Native", "Flutter", "Desktop Web Shell"} else 3
        passed = len(matched) >= required_hits if expected_tokens else bool(framework)
        return {
            "label": "框架 Playbook 执行",
            "passed": passed,
            "expected": (
                ", ".join(expected_tokens[:6])
                if expected_tokens
                else framework or "framework signals"
            ),
            "observed": ", ".join(matched[:8]),
        }

    def _extract_import_sources(self, source_content: str) -> list[str]:
        if not source_content:
            return []
        matches = re.findall(
            r"(?:from\s+['\"]([^'\"]+)['\"]|import\s+['\"]([^'\"]+)['\"])", source_content
        )
        imports: list[str] = []
        seen: set[str] = set()
        for left, right in matches:
            value = (left or right or "").strip().lower()
            if not value or value in seen:
                continue
            seen.add(value)
            imports.append(value)
        return imports
