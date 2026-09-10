"""Main UI review execution path."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from super_dev.artifact_utils import ui_contract_filename

from ..design import UIIntelligenceAdvisor
from ..ui_contract_governance import (
    CLAUDE_DESIGN_RUNTIME_CHECKS,
    required_claude_design_runtime_checks,
)
from .ui_review_models import (
    UIReviewFinding,
    UIReviewReport,
)

_logger = logging.getLogger("super_dev.reviewers.ui_review")


class UIReviewExecutionMixin:
    def review(self) -> UIReviewReport:
        findings: list[UIReviewFinding] = []
        strengths: list[str] = []
        notes: list[str] = []
        score = 100

        config = self._load_project_config()
        description = str(config.get("description") or self.name)
        frontend = str(config.get("frontend") or self.tech_stack.get("frontend") or "react")
        advisor = UIIntelligenceAdvisor()
        profile = advisor.recommend(
            description=description,
            frontend=frontend,
            product_type=self._infer_product_type(description),
            industry=self._infer_industry(description),
            style=self._infer_style(description),
        )

        # 从 UI/UX 专家工具箱提取检查维度
        ui_expert_dimensions = self._collect_expert_review_dimensions("UI", "frontend")
        ux_expert_dimensions = self._collect_expert_review_dimensions("UX", "frontend")

        uiux_path = self.project_dir / "output" / f"{self.name}-uiux.md"
        uiux_content = (
            uiux_path.read_text(encoding="utf-8", errors="ignore") if uiux_path.exists() else ""
        )
        uiux_decisions = self._extract_uiux_decisions(uiux_content)
        ui_contract = self._load_ui_contract()
        frontend_runtime = self._load_frontend_runtime_report()
        runtime_checks = (
            frontend_runtime.get("checks", {})
            if isinstance(frontend_runtime.get("checks"), dict)
            else {}
        )

        source_files = self._collect_frontend_files()
        source_content = "\n".join(
            file_path.read_text(encoding="utf-8", errors="ignore")
            for file_path in source_files[:80]
        )
        preview_path = self._find_preview_file()
        preview_content = (
            preview_path.read_text(encoding="utf-8", errors="ignore") if preview_path else ""
        )
        # 对源码与预览做运行态审查；UIUX 文档本身不应触发 emoji / 反模式扫描。
        combined_visual_content = "\n".join([source_content, preview_content])
        preview_summary = self._inspect_preview_html(preview_content) if preview_content else {}
        screenshot_path = self._capture_preview_screenshot(preview_path) if preview_path else None
        screenshot_metrics = self._analyze_screenshot(screenshot_path) if screenshot_path else {}
        design_tokens_path = self.project_dir / "output" / "frontend" / "design-tokens.css"
        design_tokens_content = (
            design_tokens_path.read_text(encoding="utf-8", errors="ignore")
            if design_tokens_path.exists()
            else ""
        )
        alignment_summary: dict[str, Any] = {
            "ui_contract": {
                "label": "UI 契约文件",
                "passed": bool(ui_contract),
                "expected": "output/*-ui-contract.json",
                "observed": (
                    str(self.project_dir / "output" / ui_contract_filename(self.name))
                    if ui_contract
                    else ""
                ),
            }
        }
        raw_emoji_policy = ui_contract.get("emoji_policy")
        emoji_policy: dict[str, Any] = (
            cast(dict[str, Any], raw_emoji_policy) if isinstance(raw_emoji_policy, dict) else {}
        )
        alignment_summary["emoji_policy"] = {
            "label": "Emoji 禁令",
            "passed": (
                bool(emoji_policy)
                and emoji_policy.get("allowed_in_ui") is False
                and emoji_policy.get("allowed_as_icon") is False
                and emoji_policy.get("allowed_during_development") is False
            ),
            "expected": "UI 与开发过程都禁止 emoji，图标只能来自正式图标库",
            "observed": emoji_policy.get("rule", "") if emoji_policy else "",
        }
        cross_platform_frontend = self._is_cross_platform_frontend(frontend)
        raw_framework_playbook = ui_contract.get("framework_playbook")
        framework_playbook: dict[str, Any] = (
            cast(dict[str, Any], raw_framework_playbook)
            if isinstance(raw_framework_playbook, dict)
            else {}
        )
        raw_screen_recipes = ui_contract.get("screen_recipes")
        screen_recipes: list[dict[str, Any]] = (
            cast(list[dict[str, Any]], raw_screen_recipes)
            if isinstance(raw_screen_recipes, list)
            else []
        )
        raw_design_context_protocol = ui_contract.get("design_context_protocol")
        design_context_protocol: dict[str, Any] = (
            cast(dict[str, Any], raw_design_context_protocol)
            if isinstance(raw_design_context_protocol, dict)
            else {}
        )
        raw_tweak_strategy = ui_contract.get("tweak_strategy")
        tweak_strategy: dict[str, Any] = (
            cast(dict[str, Any], raw_tweak_strategy) if isinstance(raw_tweak_strategy, dict) else {}
        )
        raw_verification_handoff = ui_contract.get("verification_handoff")
        verification_handoff: dict[str, Any] = (
            cast(dict[str, Any], raw_verification_handoff)
            if isinstance(raw_verification_handoff, dict)
            else {}
        )
        raw_art_direction_candidates = ui_contract.get("art_direction_candidates")
        art_direction_candidates: list[dict[str, Any]] = (
            cast(list[dict[str, Any]], raw_art_direction_candidates)
            if isinstance(raw_art_direction_candidates, list)
            else []
        )
        raw_design_direction_manifest = ui_contract.get("design_direction_manifest")
        design_direction_manifest: dict[str, Any] = (
            cast(dict[str, Any], raw_design_direction_manifest)
            if isinstance(raw_design_direction_manifest, dict)
            else {}
        )
        raw_brand_signal_manifest = ui_contract.get("brand_signal_manifest")
        brand_signal_manifest: dict[str, Any] = (
            cast(dict[str, Any], raw_brand_signal_manifest)
            if isinstance(raw_brand_signal_manifest, dict)
            else {}
        )
        raw_proof_composition_rules = ui_contract.get("proof_composition_rules")
        proof_composition_rules: dict[str, Any] = (
            cast(dict[str, Any], raw_proof_composition_rules)
            if isinstance(raw_proof_composition_rules, dict)
            else {}
        )
        raw_component_craft_requirements = ui_contract.get("component_craft_requirements")
        component_craft_requirements: list[str] = (
            cast(list[str], raw_component_craft_requirements)
            if isinstance(raw_component_craft_requirements, list)
            else []
        )
        raw_layout_tension_rules = ui_contract.get("layout_tension_rules")
        layout_tension_rules: list[str] = (
            cast(list[str], raw_layout_tension_rules)
            if isinstance(raw_layout_tension_rules, list)
            else []
        )
        raw_anti_ai_slop_guardrails = ui_contract.get("anti_ai_slop_guardrails")
        anti_ai_slop_guardrails: dict[str, Any] = (
            cast(dict[str, Any], raw_anti_ai_slop_guardrails)
            if isinstance(raw_anti_ai_slop_guardrails, dict)
            else {}
        )
        raw_critique_rubric = ui_contract.get("critique_rubric")
        critique_rubric: list[dict[str, Any]] = (
            cast(list[dict[str, Any]], raw_critique_rubric)
            if isinstance(raw_critique_rubric, list)
            else []
        )
        screen_recipe_passed = bool(screen_recipes) and all(
            isinstance(item, dict)
            and bool(item.get("section_order"))
            and bool(item.get("trust_modules"))
            and bool(item.get("required_states"))
            for item in screen_recipes
        )
        art_direction_candidates_passed = len(art_direction_candidates) >= 2 and all(
            isinstance(item, dict)
            and bool(item.get("name"))
            and bool(item.get("philosophy"))
            and bool(item.get("hero_treatment"))
            for item in art_direction_candidates[:3]
        )
        design_direction_manifest_passed = (
            bool(design_direction_manifest.get("selected_direction"))
            and bool(design_direction_manifest.get("narrative_mode"))
            and bool(design_direction_manifest.get("proof_strategy"))
            and bool(design_direction_manifest.get("visual_tension"))
        )
        brand_signal_manifest_passed = (
            bool(brand_signal_manifest.get("tone_descriptors"))
            and bool(brand_signal_manifest.get("credibility_devices"))
            and bool(brand_signal_manifest.get("premium_surfaces"))
            and bool(brand_signal_manifest.get("authority_markers"))
        )
        proof_composition_rules_passed = (
            bool(proof_composition_rules.get("hero_proof_stack"))
            and bool(proof_composition_rules.get("trust_sequence"))
            and bool(proof_composition_rules.get("evidence_priority"))
            and bool(proof_composition_rules.get("proof_density_rule"))
        )
        component_craft_requirements_passed = len(component_craft_requirements) >= 3
        layout_tension_rules_passed = len(layout_tension_rules) >= 3
        anti_ai_slop_guardrails_passed = (
            bool(anti_ai_slop_guardrails.get("forbidden_motifs"))
            and bool(anti_ai_slop_guardrails.get("hierarchy_rules"))
            and bool(anti_ai_slop_guardrails.get("originality_checks"))
            and bool(anti_ai_slop_guardrails.get("craft_checks"))
        )
        critique_labels = {
            str(item.get("dimension", "")).strip()
            for item in critique_rubric
            if isinstance(item, dict)
        }
        critique_rubric_passed = {
            "philosophy_alignment",
            "visual_hierarchy",
            "brand_authority",
            "craft_quality",
            "functionality",
            "originality",
        }.issubset(critique_labels)
        preferred_import_order = cast(
            list[str], design_context_protocol.get("preferred_import_order", [])
        )
        github_import_targets = cast(
            list[str], design_context_protocol.get("github_import_targets", [])
        )
        default_controls = cast(list[str], tweak_strategy.get("default_controls", []))
        verification_order = cast(list[str], verification_handoff.get("verification_order", []))
        design_context_passed = (
            bool(preferred_import_order)
            and bool(github_import_targets)
            and bool(design_context_protocol.get("single_source_rule"))
        )
        tweak_strategy_passed = (
            bool(tweak_strategy.get("mode"))
            and bool(default_controls)
            and bool(tweak_strategy.get("persistence_rule"))
        )
        verification_handoff_passed = (
            bool(verification_order)
            and bool(verification_handoff.get("required_artifacts"))
            and bool(verification_handoff.get("acceptance_checks"))
        )
        source_protocol_states = self._check_claude_design_protocol_execution(
            ui_contract=ui_contract,
            source_content=source_content,
            preview_content=preview_content,
        )
        framework_playbook_passed = self._framework_playbook_complete(framework_playbook)
        has_native_capabilities = bool(framework_playbook.get("native_capabilities"))
        has_validation_surfaces = bool(framework_playbook.get("validation_surfaces"))
        has_delivery_evidence = bool(framework_playbook.get("delivery_evidence"))
        alignment_summary["screen_recipes"] = {
            "label": "页面配方冻结",
            "passed": screen_recipe_passed,
            "expected": "关键页面需冻结 section order / trust modules / required states",
            "observed": ", ".join(
                str(item.get("label", "")) for item in screen_recipes[:3] if isinstance(item, dict)
            ),
        }
        alignment_summary["art_direction_candidates"] = {
            "label": "视觉方向候选",
            "passed": art_direction_candidates_passed,
            "expected": "至少 2 个可比较的 art direction candidates，包含哲学、hero 与 proof 策略",
            "observed": ", ".join(
                str(item.get("name", ""))
                for item in art_direction_candidates[:3]
                if isinstance(item, dict)
            ),
        }
        alignment_summary["design_direction_manifest"] = {
            "label": "主视觉哲学冻结",
            "passed": design_direction_manifest_passed,
            "expected": "必须冻结 selected direction / narrative mode / proof strategy / visual tension",
            "observed": " | ".join(
                str(item)
                for item in [
                    design_direction_manifest.get("selected_direction", ""),
                    design_direction_manifest.get("narrative_mode", ""),
                    design_direction_manifest.get("proof_strategy", ""),
                ]
                if item
            ),
        }
        alignment_summary["brand_signal_manifest"] = {
            "label": "品牌信号与权威感",
            "passed": brand_signal_manifest_passed,
            "expected": "必须冻结 tone descriptors / credibility devices / premium surfaces / authority markers",
            "observed": ", ".join(brand_signal_manifest.get("tone_descriptors", [])[:4]),
        }
        alignment_summary["proof_composition_rules"] = {
            "label": "证明构图规则",
            "passed": proof_composition_rules_passed,
            "expected": "必须冻结 hero proof stack / trust sequence / evidence priority / proof density rule",
            "observed": ", ".join(proof_composition_rules.get("hero_proof_stack", [])[:4]),
        }
        alignment_summary["component_craft_requirements"] = {
            "label": "组件工艺要求",
            "passed": component_craft_requirements_passed,
            "expected": "必须明确组件品牌化重写、状态矩阵、图标纪律与 token 工艺",
            "observed": ", ".join(component_craft_requirements[:4]),
        }
        alignment_summary["layout_tension_rules"] = {
            "label": "布局张力纪律",
            "passed": layout_tension_rules_passed,
            "expected": "必须冻结页面节奏、收放关系与张力建立规则",
            "observed": ", ".join(layout_tension_rules[:4]),
        }
        alignment_summary["anti_ai_slop_guardrails"] = {
            "label": "反 AI 味护栏",
            "passed": anti_ai_slop_guardrails_passed,
            "expected": "必须冻结 forbidden motifs / hierarchy rules / originality checks / craft checks",
            "observed": ", ".join(list(anti_ai_slop_guardrails.get("forbidden_motifs", []))[:4]),
        }
        alignment_summary["critique_rubric"] = {
            "label": "设计批评标尺",
            "passed": critique_rubric_passed,
            "expected": "philosophy alignment / visual hierarchy / craft quality / functionality / originality",
            "observed": ", ".join(sorted(critique_labels)),
        }
        alignment_summary["design_context_protocol"] = {
            "label": "设计上下文协议",
            "passed": design_context_passed,
            "expected": "必须明确真实代码/主题导入优先级、GitHub 导入目标与单一真源规则",
            "observed": ", ".join(preferred_import_order[:3]),
        }
        alignment_summary["tweak_strategy"] = {
            "label": "Tweaks 变体策略",
            "passed": tweak_strategy_passed,
            "expected": "必须冻结 tweak mode / default controls / persistence rule",
            "observed": ", ".join(default_controls[:4]),
        }
        alignment_summary["verification_handoff"] = {
            "label": "验证与交付协议",
            "passed": verification_handoff_passed,
            "expected": "必须冻结 verification order / required artifacts / acceptance checks",
            "observed": ", ".join(verification_order[:4]),
        }
        protocol_alignment_states = {
            "screen_recipes": screen_recipe_passed,
            "design_context_protocol": design_context_passed,
            "tweak_strategy": tweak_strategy_passed,
            "verification_handoff": verification_handoff_passed,
        }
        required_runtime_checks = required_claude_design_runtime_checks(ui_contract)
        runtime_protocol_missing = [
            check_name for check_name in required_runtime_checks if check_name not in runtime_checks
        ]
        runtime_protocol_failed = [
            check_name
            for check_name in required_runtime_checks
            if check_name in runtime_checks and not bool(runtime_checks.get(check_name, False))
        ]
        runtime_protocol_mismatches = [
            alignment_key
            for check_name, alignment_key in CLAUDE_DESIGN_RUNTIME_CHECKS.items()
            if check_name in required_runtime_checks
            and check_name in runtime_checks
            and bool(runtime_checks.get(check_name, False))
            != bool(source_protocol_states.get(alignment_key, False))
        ]
        runtime_protocol_passed = (
            bool(frontend_runtime)
            and not runtime_protocol_missing
            and not runtime_protocol_failed
            and not runtime_protocol_mismatches
        )
        runtime_protocol_observed_parts: list[str] = []
        if not frontend_runtime:
            runtime_protocol_observed_parts.append("frontend runtime missing")
        if runtime_protocol_missing:
            runtime_protocol_observed_parts.append(
                "missing="
                + ", ".join(
                    CLAUDE_DESIGN_RUNTIME_CHECKS.get(name, name)
                    for name in runtime_protocol_missing
                )
            )
        if runtime_protocol_failed:
            runtime_protocol_observed_parts.append(
                "failed="
                + ", ".join(
                    CLAUDE_DESIGN_RUNTIME_CHECKS.get(name, name) for name in runtime_protocol_failed
                )
            )
        if runtime_protocol_mismatches:
            runtime_protocol_observed_parts.append(
                "mismatch=" + ", ".join(runtime_protocol_mismatches)
            )
        if runtime_protocol_passed:
            runtime_protocol_observed_parts.append("aligned with frontend-runtime")
        alignment_summary["runtime_claude_design_protocol"] = {
            "label": "运行时 Claude-Design 协议一致性",
            "passed": runtime_protocol_passed if required_runtime_checks else True,
            "expected": "frontend-runtime 与 UI review 对同一套 screen recipes / protocol / tweaks / handoff 给出一致结论",
            "observed": (
                " | ".join(runtime_protocol_observed_parts)
                if runtime_protocol_observed_parts
                else "not required"
            ),
        }
        if required_runtime_checks:
            alignment_summary["source_claude_design_protocol"] = {
                "label": "源码/预览 Claude-Design 协议信号",
                "passed": all(
                    bool(source_protocol_states.get(name, False))
                    for name in protocol_alignment_states
                ),
                "expected": "源码或预览中应体现 recipe label / section order / trust modules / protocol / tweaks / handoff 的执行痕迹",
                "observed": ", ".join(
                    name for name, passed in source_protocol_states.items() if passed
                ),
            }
        alignment_summary["framework_playbook"] = {
            "label": "跨平台框架 Playbook",
            "passed": framework_playbook_passed if cross_platform_frontend else True,
            "expected": "跨平台框架需冻结 focus / implementation_modules / platform_constraints / validation_surfaces / delivery_evidence",
            "observed": (
                framework_playbook.get("framework", "")
                if framework_playbook and framework_playbook_passed
                else (
                    framework_playbook.get("framework", "missing")
                    if framework_playbook
                    else ("not required for web-only" if not cross_platform_frontend else "missing")
                )
            ),
        }
        alignment_summary["native_capabilities"] = {
            "label": "原生能力面",
            "passed": has_native_capabilities if cross_platform_frontend else True,
            "expected": "跨平台框架需冻结原生能力面（如 provider / offline / filesystem / push / share）",
            "observed": (
                ", ".join(framework_playbook.get("native_capabilities", [])[:4])
                if framework_playbook
                else ("not required for web-only" if not cross_platform_frontend else "missing")
            ),
        }
        alignment_summary["validation_surfaces"] = {
            "label": "真实验收面",
            "passed": has_validation_surfaces if cross_platform_frontend else True,
            "expected": "跨平台框架需冻结必须验收的真实场景",
            "observed": (
                ", ".join(framework_playbook.get("validation_surfaces", [])[:4])
                if framework_playbook
                else ("not required for web-only" if not cross_platform_frontend else "missing")
            ),
        }
        alignment_summary["delivery_evidence"] = {
            "label": "交付证据要求",
            "passed": has_delivery_evidence if cross_platform_frontend else True,
            "expected": "跨平台框架需冻结交付阶段必须沉淀的证据",
            "observed": (
                ", ".join(framework_playbook.get("delivery_evidence", [])[:4])
                if framework_playbook
                else ("not required for web-only" if not cross_platform_frontend else "missing")
            ),
        }
        product_type = self._infer_product_type(description)
        conversational_product = any(
            token in description.lower()
            for token in ("ai", "chat", "对话", "助手", "agent", "copilot")
        )

        if not uiux_content:
            findings.append(
                UIReviewFinding(
                    level="high",
                    title="缺少 UI/UX 设计文档",
                    description="无法基于设计文档验证组件生态、页面骨架和信任模块。",
                    recommendation="先生成完整的 output/*-uiux.md，再进行 UI 实现和审查。",
                )
            )
            score -= 25
        else:
            if ui_contract and not alignment_summary["emoji_policy"]["passed"]:
                findings.append(
                    UIReviewFinding(
                        level="high",
                        title="UI 契约未冻结 emoji 禁令",
                        description="当前 UI 契约没有把“开发与成品都禁止 emoji 图标”写成正式规则，宿主在实现阶段容易再次回退到 emoji 占位。",
                        recommendation="把 emoji 禁令写入 output/*-ui-contract.json，明确 UI 与开发过程中都绝对不允许使用 emoji 充当图标或临时占位。",
                        evidence=[str(ui_contract.get("emoji_policy", ""))],
                    )
                )
                score -= 12
            if ui_contract and not art_direction_candidates_passed:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 契约缺少可比较的视觉方向候选",
                        description="当前 UI 契约没有冻结至少 2 个可比较的视觉方向候选，宿主容易退回到一版默认模板而没有真正做设计取舍。",
                        recommendation="补齐 art direction candidates，至少为每个候选写明设计哲学、Hero 处理方式、证明策略与反 cliché 禁区。",
                    )
                )
                score -= 8
            elif ui_contract:
                strengths.append("UI 契约已冻结可比较的视觉方向候选。")
            if ui_contract and not design_direction_manifest_passed:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 契约未冻结主视觉哲学",
                        description="当前 UI 契约仍偏向组件与结构说明，没有把主视觉方向、叙事方式、证明策略和视觉张力冻结为一套明确主方案。",
                        recommendation="补齐 design direction manifest，明确 selected direction、narrative mode、visual tension 与 proof strategy。",
                    )
                )
                score -= 8
            elif ui_contract:
                strengths.append("UI 契约已冻结主视觉哲学与叙事方式。")
            if ui_contract and not brand_signal_manifest_passed:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 契约缺少品牌信号与权威感清单",
                        description="当前 UI 契约还没有把品牌语气、可信装置、高级完成面和权威感标记冻结下来，宿主容易做出“能用但不够像大厂产品”的页面。",
                        recommendation="补齐 brand_signal_manifest，明确 tone descriptors、credibility devices、premium surfaces 与 authority markers，让宿主知道页面必须如何建立品牌和权威感。",
                    )
                )
                score -= 8
            elif ui_contract:
                strengths.append("UI 契约已冻结品牌信号与权威感要求。")
            if ui_contract and not proof_composition_rules_passed:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 契约缺少证明构图规则",
                        description="当前 UI 契约没有把 Hero 证明栈、信任顺序、证据优先级和密度规则冻结下来，宿主容易把页面做成只有卖点没有证明的模板页。",
                        recommendation="补齐 proof_composition_rules，让宿主先安排价值主张、真实证据和信任模块的出现顺序，再去铺页面。",
                    )
                )
                score -= 8
            elif ui_contract:
                strengths.append("UI 契约已冻结证明构图与信任顺序。")
            if ui_contract and not component_craft_requirements_passed:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 契约缺少组件工艺要求",
                        description="当前 UI 契约没有把组件状态矩阵、token 工艺和品牌化重写要求冻结下来，宿主容易停留在默认组件库观感。",
                        recommendation="补齐 component_craft_requirements，明确图标纪律、组件状态矩阵、品牌化重写和 token 约束。",
                    )
                )
                score -= 8
            elif ui_contract:
                strengths.append("UI 契约已冻结组件工艺与状态矩阵要求。")
            if ui_contract and not layout_tension_rules_passed:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 契约缺少布局张力纪律",
                        description="当前 UI 契约没有冻结页面的收放关系、密度节奏和张力建立规则，宿主容易把整页做成平均用力的模板布局。",
                        recommendation="补齐 layout_tension_rules，明确哪里展开、哪里压缩、如何用结构建立高级感，而不是靠随机装饰。",
                    )
                )
                score -= 8
            elif ui_contract:
                strengths.append("UI 契约已冻结布局张力与页面节奏纪律。")
            if ui_contract and not anti_ai_slop_guardrails_passed:
                findings.append(
                    UIReviewFinding(
                        level="high",
                        title="UI 契约缺少反 AI 味护栏",
                        description="没有把科技 cliché、层级纪律、原创度检查和工艺约束冻结下来，宿主在实现阶段很容易再次滑向 AI 味过重的通用页面。",
                        recommendation="在 anti_ai_slop_guardrails 中冻结 forbidden motifs、hierarchy rules、originality checks 与 craft checks，并让 UI review 对这些项给出明确结论。",
                    )
                )
                score -= 12
            elif ui_contract:
                strengths.append("UI 契约已明确反 AI 味护栏和原创度检查。")
            if ui_contract and not critique_rubric_passed:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 契约缺少五维设计批评标尺",
                        description="当前 UI 契约没有把哲学一致性、视觉层级、细节工艺、功能性和原创度固化为正式评估维度。",
                        recommendation="补齐 critique_rubric，让设计评审不只判断“能不能用”，还要判断“是否高级、是否原创、是否有工艺”。",
                    )
                )
                score -= 8
            protocol_gaps = []
            if not screen_recipe_passed:
                protocol_gaps.append("screen_recipes")
            if not design_context_passed:
                protocol_gaps.append("design_context_protocol")
            if not tweak_strategy_passed:
                protocol_gaps.append("tweak_strategy")
            if not verification_handoff_passed:
                protocol_gaps.append("verification_handoff")
            if ui_contract and protocol_gaps:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="Claude-Design 风格执行协议未冻结",
                        description="UI 契约还没有完整冻结页面配方、上下文导入协议、Tweaks 变体策略或验证交付协议，宿主容易再次退回到泛化页面生成。",
                        recommendation="补齐 output/*-ui-contract.json 中的 screen_recipes、design_context_protocol、tweak_strategy、verification_handoff，并让前端实现围绕这些冻结字段组织页面。",
                        evidence=protocol_gaps,
                    )
                )
                score -= 10
            if required_runtime_checks and not frontend_runtime:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="frontend runtime 缺少 Claude-Design 协议证据",
                        description="UI 契约已经冻结 Claude-Design 风格执行协议，但还没有 frontend runtime 报告来证明页面配方、上下文协议、Tweaks 和验证交付链已真实进入运行产物。",
                        recommendation="先重新执行 frontend runtime，确保 runtime 报告写出 ui_screen_recipes / ui_design_context_protocol / ui_tweak_strategy / ui_verification_handoff 四项结果。",
                        evidence=[
                            "frontend-runtime missing",
                            *[
                                CLAUDE_DESIGN_RUNTIME_CHECKS.get(item, item)
                                for item in required_runtime_checks
                            ],
                        ],
                    )
                )
                score -= 8
            elif runtime_protocol_mismatches:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI Review 与 frontend runtime 的 Claude-Design 结论不一致",
                        description="源码/预览级 UI review 与 frontend runtime 对同一套 Claude-Design 协议给出了不同结论，这通常意味着 runtime 证据已经过期，或者 UI 改动后没有重新生成运行报告。",
                        recommendation="不要继续沿用旧 runtime 证据；先重新执行 frontend runtime 与 UI review，确认两边对 screen_recipes / protocol / tweaks / handoff 的结论重新对齐。",
                        evidence=runtime_protocol_mismatches,
                    )
                )
                score -= 8
            elif runtime_protocol_failed or runtime_protocol_missing:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="frontend runtime 未证明 Claude-Design 执行协议",
                        description="虽然 UI 契约已经冻结 Claude-Design 风格执行协议，但 frontend runtime 仍未证明页面配方、上下文协议、Tweaks 或验证交付链已经真实进入运行态。",
                        recommendation="按当前 UI 契约修正前端并重新执行 frontend runtime，重点补齐运行时对 screen_recipes / design_context_protocol / tweak_strategy / verification_handoff 的证据。",
                        evidence=[
                            *[
                                CLAUDE_DESIGN_RUNTIME_CHECKS.get(item, item)
                                for item in runtime_protocol_missing
                            ],
                            *[
                                CLAUDE_DESIGN_RUNTIME_CHECKS.get(item, item)
                                for item in runtime_protocol_failed
                            ],
                        ],
                    )
                )
                score -= 8
            if cross_platform_frontend and not framework_playbook_passed:
                findings.append(
                    UIReviewFinding(
                        level="high",
                        title="跨平台框架 Playbook 未冻结",
                        description="当前项目属于跨平台框架，但 UI 契约没有完整冻结框架级实现清单、平台限制、真实验收面和交付证据，宿主很容易退回到泛 Web 实现。",
                        recommendation="在 output/*-ui-contract.json 与 UIUX 文档中补齐 framework_playbook，明确原生能力、平台差异、验证面和交付证据，再继续实现。",
                        evidence=[framework_playbook.get("framework", "missing"), frontend],
                    )
                )
                score -= 14
            elif cross_platform_frontend and framework_playbook:
                strengths.append(
                    f"已冻结 {framework_playbook.get('framework', '跨平台框架')} playbook，框架级约束进入 UI 契约。"
                )
            if (
                cross_platform_frontend
                and framework_playbook
                and (
                    not has_native_capabilities
                    or not has_validation_surfaces
                    or not has_delivery_evidence
                )
            ):
                missing_framework_facets = []
                if not has_native_capabilities:
                    missing_framework_facets.append("原生能力面")
                if not has_validation_surfaces:
                    missing_framework_facets.append("真实验收面")
                if not has_delivery_evidence:
                    missing_framework_facets.append("交付证据要求")
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="跨平台框架治理仍缺少关键面",
                        description="虽然已经识别到跨平台框架，但原生能力、真实验收面或交付证据要求仍未冻结，后续实现与交付容易退回泛化 Web 口径。",
                        recommendation="在 framework_playbook 中补齐原生能力面、必须验收的真实场景和交付证据要求，再继续实现与验收。",
                        evidence=missing_framework_facets,
                    )
                )
                score -= 8

            required_sections = [
                "设计 Intelligence 结论",
                "组件生态与实现基线",
                "页面骨架优先级",
                "图标、图表与内容模块",
                "商业化与信任设计",
            ]
            missing_sections = [item for item in required_sections if item not in uiux_content]
            if missing_sections:
                findings.append(
                    UIReviewFinding(
                        level="high",
                        title="UI/UX 文档缺少关键商业级章节",
                        description="文档没有完整覆盖组件生态、页面骨架或信任设计，宿主难以稳定生成商业级界面。",
                        recommendation="补齐设计 intelligence、组件生态、页面骨架和信任设计章节。",
                        evidence=missing_sections,
                    )
                )
                score -= 18
            else:
                strengths.append("UI/UX 文档已覆盖组件生态、页面骨架与信任设计关键章节。")
            ui_decision_markers = [
                "主视觉气质",
                "字体组合",
                "配色逻辑",
                "图标系统",
                "Design Token 冻结输出",
                "备选实现路径",
                "Screen Recipes（页面配方冻结）",
                "Claude-Design 风格执行协议",
            ]
            missing_decision_markers = [
                item for item in ui_decision_markers if item not in uiux_content
            ]
            if missing_decision_markers:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 系统决策未被完整冻结",
                        description="UI/UX 文档仍像描述性说明，缺少明确的风格、字体、配色、图标和 token 冻结结果，宿主容易回退到模板化默认输出。",
                        recommendation="在 UI/UX 文档里补齐主视觉气质、字体组合、配色逻辑、图标系统、Design Token 冻结输出和备选方案取舍。",
                        evidence=missing_decision_markers[:6],
                    )
                )
                score -= 8
            elif "2 个视觉方向候选" not in uiux_content and "主方案 + 备选方案" not in uiux_content:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI 文档缺少双方案取舍约束",
                        description="文档没有强制记录主方案与备选方案的取舍，宿主容易滑向单一路径并反复输出同一种页面风格。",
                        recommendation="要求关键页面至少提供 2 个视觉方向候选，并写明为什么采用主方案、为什么放弃备选方案。",
                    )
                )
                score -= 6
            else:
                strengths.append("UI/UX 文档已冻结风格决策、token 与备选方案取舍。")
            advanced_sections = [
                "多端适配与平台化设计策略",
                "商业级设计质量门禁",
                "精美 UI 执行工作流（Stitch 范式）",
                "组件落地清单（Tailwind / 生态组件）",
            ]
            missing_advanced = [item for item in advanced_sections if item not in uiux_content]
            if missing_advanced:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="UI/UX 文档缺少高级平台化章节",
                        description="文档缺少多端策略或质量门禁，可能导致 Web/H5/小程序/APP/桌面端 的设计一致性与商业完成度不足。",
                        recommendation="补充多端适配策略、组件库矩阵和商业级设计质量门禁章节。",
                        evidence=missing_advanced,
                    )
                )
                score -= 8
            else:
                strengths.append("UI/UX 文档已覆盖多端策略与商业级质量门禁。")
            required_platform_terms = ("WEB", "H5", "微信小程序", "APP", "桌面端")
            missing_platform_terms = [
                term for term in required_platform_terms if term not in uiux_content
            ]
            if missing_platform_terms:
                findings.append(
                    UIReviewFinding(
                        level="high",
                        title="多端策略未覆盖五端口径",
                        description="UI/UX 文档未同时覆盖 Web/H5/微信小程序/APP/桌面端，平台策略存在缺口。",
                        recommendation="在跨端策略章节补齐五端目标、交互差异与共享组件契约。",
                        evidence=missing_platform_terms,
                    )
                )
                score -= 12
            else:
                strengths.append("UI/UX 文档已覆盖 Web/H5/微信小程序/APP/桌面端 五端口径。")

        selected_library = self._resolve_primary_library(ui_contract, uiux_decisions)
        expected_library = (
            selected_library or profile.get("primary_library", {}).get("name", "")
        ).lower()
        package_json = self._read_package_json()
        dependency_blob = (
            json.dumps(package_json, ensure_ascii=False).lower() if package_json else ""
        )
        if package_json:
            if "shadcn" in expected_library and not any(
                token in dependency_blob
                for token in ("@radix-ui", "tailwindcss", "class-variance-authority")
            ):
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="源码依赖未体现推荐组件生态",
                        description="当前推荐是 shadcn/Radix/Tailwind 体系，但依赖中没有明显对应组件生态。",
                        recommendation="检查是否已初始化推荐组件库，或在 UI/UX 文档中明确采用了替代方案。",
                        evidence=[expected_library],
                    )
                )
                score -= 8
            else:
                strengths.append(
                    f"依赖层已基本匹配推荐组件生态：{selected_library or profile['primary_library']['name']}。"
                )
            frontend_token_expectations = {
                "miniapp": ("tdesign", "taro", "uniapp", "uni-app", "vant-weapp", "nutui"),
                "desktop": ("electron", "tauri", "wails"),
                "react-native": ("react-native", "nativewind", "tamagui"),
                "flutter": ("flutter", "dart"),
                "swiftui": ("swiftui", "xcode"),
            }
            expected_tokens = frontend_token_expectations.get(
                profile.get("normalized_frontend", "")
            )
            if expected_tokens and not any(token in dependency_blob for token in expected_tokens):
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="依赖层未体现目标端生态",
                        description="当前目标端与依赖生态不一致，可能导致交互范式与平台能力无法落地。",
                        recommendation="补齐目标端框架依赖，或在文档中声明跨端桥接方案与边界。",
                        evidence=[profile.get("normalized_frontend", "")],
                    )
                )
                score -= 8
        else:
            notes.append("未检测到 package.json，组件生态一致性仅做文档级审查。")

        if source_files:
            if not any(token in source_content for token in self.TOKEN_KEYWORDS):
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="源码中缺少明显的 design token 痕迹",
                        description="未检测到颜色、间距、字体等 token 命名，存在直接写死视觉样式的风险。",
                        recommendation="将颜色、间距、圆角、阴影和字体统一沉淀为 token / CSS variables / theme config。",
                    )
                )
                score -= 10
            else:
                strengths.append("源码中已出现 design token / CSS variables 痕迹。")

            if self.DEFAULT_FONT_RE.search(source_content) and "--font-" not in source_content:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="字体系统过于默认，品牌辨识度不足",
                        description="源码里出现了 Inter / Arial / system-ui 等默认字体策略，但没有明显的品牌化字体 token 或排版系统。",
                        recommendation="为商业页面定义更明确的字体体系与字号层级，不要只依赖默认 sans-serif 字体栈。",
                    )
                )
                score -= 8
            else:
                strengths.append("源码未暴露明显的默认字体依赖，排版系统更接近品牌化实现。")

            icon_system = self._resolve_contract_or_doc_value(
                contract=ui_contract,
                decisions=uiux_decisions,
                contract_key="icon_system",
                decision_key="icon_system",
            )
            expected_icon_tokens = self._expected_icon_tokens(icon_system)
            if expected_icon_tokens:
                icon_aligned = any(
                    token in dependency_blob or token in source_content.lower()
                    for token in expected_icon_tokens
                )
                alignment_summary["icon_system"] = {
                    "label": "图标系统",
                    "passed": icon_aligned,
                    "expected": icon_system,
                    "observed": ", ".join(expected_icon_tokens),
                }
                if not icon_aligned:
                    findings.append(
                        UIReviewFinding(
                            level="high",
                            title="源码未落实文档冻结的图标系统",
                            description="UI/UX 文档已经冻结图标系统，但源码和依赖里没有对应图标库痕迹，宿主很容易退回 emoji、默认图标或随手混用多个图标来源。",
                            recommendation="把文档里声明的图标库真正接入依赖和组件实现，并删除与该图标系统无关的临时图标写法。",
                            evidence=[icon_system],
                        )
                    )
                    score -= 12
                else:
                    strengths.append(f"源码已体现文档冻结的图标系统：{icon_system}。")

            font_pair = self._resolve_font_pair(ui_contract, uiux_decisions)
            expected_font_tokens = self._expected_font_tokens(font_pair)
            if expected_font_tokens:
                source_visual_content = "\n".join([source_content, preview_content]).lower()
                matched_fonts = [
                    token for token in expected_font_tokens if token in source_visual_content
                ]
                alignment_summary["font_pair"] = {
                    "label": "字体组合",
                    "passed": bool(matched_fonts),
                    "expected": font_pair,
                    "observed": ", ".join(matched_fonts),
                }
                if not matched_fonts and self.DEFAULT_FONT_RE.search(source_content):
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="源码未落实文档冻结的字体组合",
                            description="UI/UX 文档已经冻结字体组合，但源码仍然停留在默认字体或没有接入目标字体，品牌差异化会被宿主默认实现冲掉。",
                            recommendation="在字体导入、CSS variables、Tailwind theme 或全局样式里接入文档声明的字体组合，并消除默认字体兜底对主视觉的影响。",
                            evidence=[font_pair],
                        )
                    )
                    score -= 8

            primary_library = selected_library
            expected_library_tokens = self._expected_library_tokens(primary_library)
            library_aligned = (
                any(
                    token in dependency_blob or token in source_content.lower()
                    for token in expected_library_tokens
                )
                if expected_library_tokens
                else False
            )
            if expected_library_tokens:
                alignment_summary["component_ecosystem"] = {
                    "label": "组件生态",
                    "passed": library_aligned,
                    "expected": primary_library,
                    "observed": ", ".join(expected_library_tokens),
                }
            if expected_library_tokens and not library_aligned:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="源码未落实文档冻结的组件生态",
                        description="UI/UX 文档已经冻结了首选组件生态，但源码和依赖没有体现这条主方案，宿主容易在实现阶段再次漂移到其他 UI 体系。",
                        recommendation="让 package 依赖、组件 import 和实现基线与文档声明的组件生态保持一致；如果改用备选方案，必须先回写 UI/UX 文档。",
                        evidence=[primary_library],
                    )
                )
                score -= 8

            expected_import_tokens = self._expected_component_import_tokens(primary_library)
            import_sources = self._extract_import_sources(source_content)
            matched_imports = [
                token
                for token in import_sources
                if any(expected in token for expected in expected_import_tokens)
            ]
            should_enforce_component_imports = bool(package_json) and bool(expected_import_tokens)
            if expected_import_tokens:
                alignment_summary["component_imports"] = {
                    "label": "组件导入路径",
                    "passed": bool(matched_imports) if should_enforce_component_imports else True,
                    "expected": ", ".join(expected_import_tokens),
                    "observed": (
                        ", ".join(matched_imports[:8])
                        if matched_imports
                        else (
                            "not enforced for static scaffold"
                            if not should_enforce_component_imports
                            else ""
                        )
                    ),
                }
            if should_enforce_component_imports and not matched_imports and source_files:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="源码 import 未落实冻结组件生态",
                        description="依赖层可能已经安装了目标组件生态，但源码导入路径没有体现这条主方案，说明宿主在实现阶段仍可能回退到临时组件或默认 HTML。",
                        recommendation="让页面和组件真正从冻结后的组件生态导入实现；如果改用其他组件体系，先回写 UI/UX 文档和 UI 契约。",
                        evidence=[primary_library, *expected_import_tokens[:4]],
                    )
                )
                score -= 8

            if ui_contract:
                design_token_reference_ready = self._has_design_token_contract_wiring(
                    source_content=source_content,
                    preview_content=preview_content,
                    design_tokens_content=design_tokens_content,
                )
                theme_entry_ready = self._has_theme_entry_contract_wiring(
                    source_content=source_content,
                    preview_content=preview_content,
                    design_tokens_content=design_tokens_content,
                )
                alignment_summary["theme_entry"] = {
                    "label": "主题入口",
                    "passed": theme_entry_ready,
                    "expected": "全局主题入口或 design token 入口已接入",
                    "observed": "theme provider / design tokens wired" if theme_entry_ready else "",
                }
                if not theme_entry_ready:
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="源码缺少主题入口或全局主题接线",
                            description="虽然已经冻结了 UI 契约，但源码里看不到明显的主题入口、ThemeProvider、全局 design token 接线或主题配置，后续页面很容易各写各的。",
                            recommendation="在应用入口或全局 layout 中接入 design-tokens.css、ThemeProvider、Tailwind theme 或等价的主题配置，确保页面共用同一套视觉基线。",
                            evidence=["missing global theme entry / provider / token import"],
                        )
                    )
                    score -= 8
                alignment_summary["design_tokens"] = {
                    "label": "Design Token 接入",
                    "passed": design_token_reference_ready,
                    "expected": str(design_tokens_path),
                    "observed": (
                        "design-tokens.css / CSS variables wired"
                        if design_token_reference_ready
                        else ""
                    ),
                }
                if not design_token_reference_ready:
                    findings.append(
                        UIReviewFinding(
                            level="high",
                            title="源码未把 UI 契约的 Design Token 接入实现",
                            description="虽然已经生成了 UI 契约，但源码和预览页没有明确体现 design-tokens.css 或 CSS variables 的接入，宿主仍可能在实现阶段直接写死视觉样式。",
                            recommendation="确保前端入口显式接入 design-tokens.css，并在组件和样式中优先使用 var(--color-*) / var(--space-*) / var(--font-*) 等 token。",
                            evidence=[
                                (
                                    str(design_tokens_path)
                                    if design_tokens_path.exists()
                                    else "design-tokens.css missing"
                                ),
                                "missing design token reference in source or preview",
                            ],
                        )
                    )
                    score -= 14
                else:
                    strengths.append("源码已显式接入 UI 契约对应的 design tokens。")

                raw_framework_playbook = ui_contract.get("framework_playbook")
                framework_playbook = (
                    cast(dict[str, Any], raw_framework_playbook)
                    if isinstance(raw_framework_playbook, dict)
                    else {}
                )
                if framework_playbook:
                    framework_alignment = self._check_framework_playbook_execution(
                        framework_playbook=framework_playbook,
                        source_content=source_content,
                        preview_content=preview_content,
                        dependency_blob=dependency_blob,
                    )
                    alignment_summary["framework_execution"] = framework_alignment
                    if not framework_alignment.get("passed", False):
                        findings.append(
                            UIReviewFinding(
                                level="high",
                                title="跨平台框架 Playbook 未真正进入实现",
                                description="UI 契约里已经冻结了框架级执行约束，但源码和依赖中没有足够信号证明这些平台能力与差异化策略已经进入实现。",
                                recommendation="按 UI 契约补齐框架级执行信号：原生能力面、平台差异处理、导航/权限/离线/文件等关键能力，以及对应的验收面说明。",
                                evidence=[
                                    str(framework_playbook.get("framework", "")),
                                    str(framework_alignment.get("expected", "")),
                                    str(framework_alignment.get("observed", "")),
                                ],
                            )
                        )
                        score -= 10

                token_variables = self._extract_token_variables(design_tokens_content)
                if token_variables:
                    referenced = [
                        token
                        for token in token_variables
                        if token in source_content or token in preview_content
                    ]
                    alignment_summary["token_usage"] = {
                        "label": "冻结 Token 使用率",
                        "passed": len(referenced) >= min(2, len(token_variables)),
                        "expected": ", ".join(token_variables[:6]),
                        "observed": ", ".join(referenced[:6]),
                    }
                    if len(referenced) < min(2, len(token_variables)):
                        findings.append(
                            UIReviewFinding(
                                level="medium",
                                title="源码对冻结 Token 的实际使用偏弱",
                                description="Design Token 文件虽然存在，但源码里很少看到对应变量被真正使用，说明 UI 系统可能只停留在生成文件层而没有进入组件实现。",
                                recommendation="让布局、标题、卡片、按钮和状态组件优先使用冻结后的 color/space/font token，而不是继续写死数值。",
                                evidence=token_variables[:6],
                            )
                        )
                        score -= 8

                hardcoded_hex_colors = sorted(
                    {item for item in self.HEX_COLOR_RE.findall(source_content)}
                )[:12]
                if (
                    hardcoded_hex_colors
                    and "var(--color-" not in source_content
                    and "--color-" not in design_tokens_content
                ):
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="源码仍以硬编码颜色为主，UI 契约执行不足",
                            description="前端源码里出现了多处硬编码色值，但没有明显的 color token 使用痕迹，UI 系统的颜色策略尚未真正进入实现。",
                            recommendation="将主要颜色迁移到 design-tokens.css / theme 配置，并让组件优先消费 token 变量。",
                            evidence=hardcoded_hex_colors,
                        )
                    )
                    score -= 8

            suspicious_hits = self.SUSPICIOUS_PATTERN_RE.findall(source_content)
            if suspicious_hits:
                findings.append(
                    UIReviewFinding(
                        level="high",
                        title="检测到可疑的 AI 模板化视觉痕迹",
                        description="源码中出现紫粉渐变、emoji 或过度模板化关键词，容易生成 AI 味较重的页面。",
                        recommendation="回到 UI/UX 文档规定的品牌方向，删除渐变堆砌、emoji 图标和无意义装饰。",
                        evidence=sorted({item for item in suspicious_hits})[:10],
                    )
                )
                score -= 18

            emoji_hits = sorted({item for item in self.EMOJI_RE.findall(combined_visual_content)})[
                :10
            ]
            if emoji_hits:
                findings.append(
                    UIReviewFinding(
                        level="critical",
                        title="检测到 emoji 功能图标或表情占位",
                        description="UI 产物中出现 emoji 字符，说明图标系统没有在开始阶段被锁定，已违反 Super Dev 的 UI 硬约束。",
                        recommendation="删除所有 emoji 字符，改用 Lucide / Heroicons / Tabler / 官方组件图标，并在 UI/UX 文档里明确图标库与替换策略。",
                        evidence=emoji_hits,
                    )
                )
                score -= 24

            clone_hits = sorted({item for item in self.CLAUDE_CLONE_RE.findall(source_content)})[
                :10
            ]
            if preview_summary or source_files:
                expected_layout = "非聊天壳层，按产品类型组织导航、主体内容和关键动作"
                observed_layout_parts = []
                nav_markers = self._extract_navigation_shell_markers(source_content)
                if preview_summary:
                    observed_layout_parts.extend(
                        [
                            f"sections={preview_summary['sections']}",
                            f"headings={preview_summary['headings']}",
                            f"nav_links={preview_summary['nav_links']}",
                            f"first_section_cta={preview_summary['first_section_cta']}",
                        ]
                    )
                if nav_markers:
                    observed_layout_parts.append(f"source_nav={', '.join(nav_markers[:6])}")
                if clone_hits and not conversational_product:
                    observed_layout_parts.append("chat-shell pattern detected")
                layout_shell_passed = True
                if clone_hits and not conversational_product:
                    layout_shell_passed = False
                elif preview_summary:
                    if product_type in {"landing", "saas", "ecommerce"}:
                        layout_shell_passed = (
                            preview_summary["sections"] >= 3
                            and preview_summary["nav_links"] >= 2
                            and preview_summary["first_section_cta"] >= 2
                        )
                    else:
                        layout_shell_passed = (
                            preview_summary["sections"] >= 2 and preview_summary["headings"] >= 2
                        )
                alignment_summary["layout_shell"] = {
                    "label": "页面骨架",
                    "passed": layout_shell_passed,
                    "expected": expected_layout,
                    "observed": " | ".join(observed_layout_parts),
                }
                navigation_shell_passed = bool(nav_markers) or bool(
                    preview_summary.get("nav_links", 0)
                )
                if clone_hits and not conversational_product:
                    navigation_shell_passed = False
                elif product_type in {"dashboard", "saas"}:
                    navigation_shell_passed = navigation_shell_passed and (
                        any(
                            marker in nav_markers
                            for marker in (
                                "sidebar",
                                "topbar",
                                "header",
                                "nav",
                                "breadcrumb",
                                "appshell",
                            )
                        )
                        or bool(preview_summary.get("nav_links", 0))
                    )
                alignment_summary["navigation_shell"] = {
                    "label": "导航骨架",
                    "passed": navigation_shell_passed,
                    "expected": "源码或预览中存在导航 / header / sidebar / breadcrumb 等骨架信号",
                    "observed": " | ".join(observed_layout_parts),
                }
                if not navigation_shell_passed:
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="源码缺少稳定的导航骨架",
                            description="源码和预览里没有足够明确的导航、header、sidebar 或 breadcrumb 信号，页面容易退化成只堆内容的单块界面。",
                            recommendation="为当前产品类型补齐稳定的导航骨架，在源码入口明确 header/nav/sidebar/breadcrumb 等结构，而不是只靠内容块临时拼接。",
                            evidence=nav_markers[:6]
                            or [f"preview_nav_links={preview_summary.get('nav_links', 0)}"],
                        )
                    )
                    score -= 8
            if clone_hits and not conversational_product:
                findings.append(
                    UIReviewFinding(
                        level="high",
                        title="检测到 Claude / 聊天式产品骨架复刻痕迹",
                        description="当前产品不是对话式 AI，但源码仍然出现了 Claude/聊天壳层相关模式，容易导致页面同质化成 Claude 风格。",
                        recommendation="回到 UI/UX 文档，重做页面骨架、导航结构、字体组合和品牌配色，不要复用聊天产品外壳。",
                        evidence=clone_hits,
                    )
                )
                score -= 18

            banned_hits = []
            if suspicious_hits:
                banned_hits.extend(sorted({item for item in suspicious_hits}))
            if emoji_hits:
                banned_hits.extend(emoji_hits)
            if clone_hits and not conversational_product:
                banned_hits.extend(clone_hits)
            alignment_summary["banned_patterns"] = {
                "label": "反模式约束",
                "passed": len(banned_hits) == 0,
                "expected": "无 emoji 图标、无 Claude 聊天壳层、无模板化渐变/关键词",
                "observed": ", ".join(banned_hits[:10]),
            }

            missing_state_terms = [
                item for item in self.STATE_KEYWORDS if item not in source_content.lower()
            ]
            if len(missing_state_terms) >= 4:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="源码中缺少关键状态覆盖信号",
                        description="未检测到足够多的 loading / empty / error / success 等状态处理痕迹。",
                        recommendation="补齐列表、表单和关键模块的状态矩阵，不要只实现正常态。",
                        evidence=missing_state_terms[:6],
                    )
                )
                score -= 8
            else:
                strengths.append("源码中已体现出多态状态处理。")

            if any(
                term in description.lower()
                for term in ("官网", "official website", "landing", "营销")
            ):
                marketing_hits = len(
                    [item for item in self.MARKETING_KEYWORDS if item in source_content.lower()]
                )
                if marketing_hits < 2:
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="营销型页面缺少足够的转化与信任模块",
                            description="对外页面没有明显体现案例、FAQ、定价、评价或 social proof 模块。",
                            recommendation="补齐转化和信任模块，不要只有 Hero 和功能列表。",
                        )
                    )
                    score -= 8
                else:
                    strengths.append("营销型页面已体现出转化与信任模块。")
        else:
            notes.append("当前未检测到前端源码，仅完成文档级 UI 审查；实现后建议再次运行。")

        if preview_summary and "layout_shell" not in alignment_summary:
            expected_layout = "非聊天壳层，按产品类型组织导航、主体内容和关键动作"
            nav_markers = self._extract_navigation_shell_markers(source_content)
            clone_hits = sorted({item for item in self.CLAUDE_CLONE_RE.findall(source_content)})[
                :10
            ]
            suspicious_hits = self.SUSPICIOUS_PATTERN_RE.findall(source_content)
            emoji_hits = sorted({item for item in self.EMOJI_RE.findall(combined_visual_content)})[
                :10
            ]
            observed_layout_parts = [
                f"sections={preview_summary['sections']}",
                f"headings={preview_summary['headings']}",
                f"nav_links={preview_summary['nav_links']}",
                f"first_section_cta={preview_summary['first_section_cta']}",
            ]
            if nav_markers:
                observed_layout_parts.append(f"source_nav={', '.join(nav_markers[:6])}")
            if clone_hits and not conversational_product:
                observed_layout_parts.append("chat-shell pattern detected")
            if product_type in {"landing", "saas", "ecommerce"}:
                layout_shell_passed = (
                    preview_summary["sections"] >= 3
                    and preview_summary["nav_links"] >= 1
                    and preview_summary["first_section_cta"] >= 1
                )
            else:
                layout_shell_passed = (
                    preview_summary["sections"] >= 2 and preview_summary["headings"] >= 2
                )
            alignment_summary["layout_shell"] = {
                "label": "页面骨架",
                "passed": layout_shell_passed,
                "expected": expected_layout,
                "observed": " | ".join(observed_layout_parts),
            }
            alignment_summary["navigation_shell"] = {
                "label": "导航骨架",
                "passed": bool(preview_summary.get("nav_links", 0)),
                "expected": "源码或预览中存在导航 / header / sidebar / breadcrumb 等骨架信号",
                "observed": " | ".join(observed_layout_parts),
            }
            banned_hits = []
            if suspicious_hits:
                banned_hits.extend(sorted({item for item in suspicious_hits}))
            if emoji_hits:
                banned_hits.extend(emoji_hits)
            if clone_hits and not conversational_product:
                banned_hits.extend(clone_hits)
            alignment_summary["banned_patterns"] = {
                "label": "反模式约束",
                "passed": len(banned_hits) == 0,
                "expected": "无 emoji 图标、无 Claude 聊天壳层、无模板化渐变/关键词",
                "observed": ", ".join(banned_hits[:10]),
            }

        if preview_summary:
            if preview_summary["sections"] < 3:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="可预览页面结构过于单薄",
                        description="预览页的主结构层级不足，页面更像占位原型而不是商业级成品页面。",
                        recommendation="补齐 Hero 之外的关键模块，至少形成价值、证据、功能和下一步动作的完整结构。",
                        evidence=[
                            f"sections={preview_summary['sections']}",
                            f"headings={preview_summary['headings']}",
                        ],
                    )
                )
                score -= 8
            else:
                strengths.append("预览页已具备基础分区结构。")

            if preview_summary["sections"] >= 3 and preview_summary["headings"] < 3:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="页面层级不足，排版节奏偏平",
                        description="虽然页面已经拆成多个分区，但标题层级不足，信息节奏会更像占位稿而不是商业成品。",
                        recommendation="为关键分区补足 h1/h2/h3 层级与辅助文案，拉开版式节奏。",
                        evidence=[
                            f"sections={preview_summary['sections']}",
                            f"headings={preview_summary['headings']}",
                        ],
                    )
                )
                score -= 6

            if preview_summary["buttons"] + preview_summary["links"] < 3:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="可预览页面缺少明确交互入口",
                        description="可点击 CTA / 链接数量过少，容易形成只可观看、不可推进的静态页面。",
                        recommendation="补充核心 CTA、次级 CTA、导航或下一步动作入口。",
                    )
                )
                score -= 6

            product_type = self._infer_product_type(description)
            if product_type in {"landing", "saas", "ecommerce"}:
                if preview_summary["nav_links"] < 2:
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="导航信息架构不足",
                            description="预览页导航入口过少，用户难以快速理解页面结构与主要去向。",
                            recommendation="为对外页面补齐导航层级，至少明确产品、方案、价格/案例、FAQ 或联系入口。",
                            evidence=[f"nav_links={preview_summary['nav_links']}"],
                        )
                    )
                    score -= 6

                if preview_summary["first_section_cta"] < 2:
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="首屏 CTA 层级不足",
                            description="首屏只有单一动作或几乎没有动作层级，不利于转化和分流。",
                            recommendation="在首屏至少提供主 CTA 和次级 CTA，例如开始使用 + 查看演示 / 联系销售。",
                            evidence=[f"first_section_cta={preview_summary['first_section_cta']}"],
                        )
                    )
                    score -= 8

                if (
                    preview_summary["first_section_text_chars"] < 80
                    and preview_summary["first_section_media"] == 0
                ):
                    findings.append(
                        UIReviewFinding(
                            level="medium",
                            title="首屏信息密度不足",
                            description="首屏文案信息量偏低，且没有产品截图或媒体证据，页面容易像占位稿。",
                            recommendation="补充价值主张、辅助说明和产品证据，让首屏同时承担理解和转化任务。",
                            evidence=[
                                f"first_section_text_chars={preview_summary['first_section_text_chars']}",
                                f"first_section_media={preview_summary['first_section_media']}",
                            ],
                        )
                    )
                    score -= 8

            if preview_summary["media"] == 0 and self._infer_product_type(description) in {
                "landing",
                "saas",
                "ecommerce",
            }:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="可预览页面缺少截图或媒体证据",
                        description="营销/产品型页面没有截图、图片、视频或产品演示区域，信任与理解成本偏高。",
                        recommendation="加入产品截图、流程示意、客户案例图片或短视频演示。",
                    )
                )
                score -= 8

            product_type = self._infer_product_type(description)
            if preview_summary["trust_hits"] < 2 and product_type in {
                "landing",
                "saas",
                "ecommerce",
            }:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="可预览页面信任信号不足",
                        description="预览页文本中缺少明显的案例、客户、评价、安全、FAQ 等信任模块。",
                        recommendation="为对外页面补齐信任区、FAQ、案例或安全说明。",
                        evidence=[f"trust_hits={preview_summary['trust_hits']}"],
                    )
                )
                score -= 8
            elif preview_summary["trust_hits"] >= 2:
                strengths.append("预览页已体现一定的信任/说明信号。")

            if preview_summary["landmarks"] < 3:
                findings.append(
                    UIReviewFinding(
                        level="low",
                        title="页面语义 landmarks 偏少",
                        description="缺少 header/main/nav/footer/section 等结构语义，后续可访问性和结构清晰度会受影响。",
                        recommendation="补充语义化结构标签，提升信息架构和可访问性基线。",
                        evidence=[f"landmarks={preview_summary['landmarks']}"],
                    )
                )
                score -= 4
        else:
            notes.append(
                "未检测到 preview.html 或 output/frontend/index.html，未执行结构级视觉审查。"
            )

        if screenshot_path and screenshot_metrics:
            notes.append(f"已生成预览截图: {screenshot_path}")
            alignment_summary["screenshot_visual_judge"] = {
                "label": "截图级视觉验收",
                "passed": (
                    screenshot_metrics.get("blank_ratio", 1.0) <= 0.78
                    and screenshot_metrics.get("contrast_span", 0.0) >= 0.18
                    and screenshot_metrics.get("dominant_color_ratio", 1.0) <= 0.78
                ),
                "expected": "页面不能过空、过平、过单一，必须有足够的层级与视觉变化",
                "observed": (
                    f"blank={screenshot_metrics.get('blank_ratio', 0):.2f}, "
                    f"contrast={screenshot_metrics.get('contrast_span', 0):.2f}, "
                    f"dominant={screenshot_metrics.get('dominant_color_ratio', 0):.2f}"
                ),
            }
            if screenshot_metrics["blank_ratio"] > 0.78:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="截图显示页面留白过多",
                        description="截图中大面积为空白或浅色区域，页面可能更像占位稿而不是成熟产品页面。",
                        recommendation="补齐信息层级、模块内容和可信证据，避免只有少量文字悬浮在大背景上。",
                        evidence=[f"blank_ratio={screenshot_metrics['blank_ratio']:.2f}"],
                    )
                )
                score -= 8
            else:
                strengths.append("截图层面未出现明显的超高留白占比。")

            if screenshot_metrics["contrast_span"] < 0.18:
                findings.append(
                    UIReviewFinding(
                        level="medium",
                        title="截图明暗层级不足",
                        description="截图整体亮度跨度过窄，界面可能只有一层浅色平面，缺少成熟商业产品应有的视觉起伏与层级反差。",
                        recommendation="增强标题、卡片、分区、背景层和重点模块之间的明暗与材质差异，避免整页像一张平面白板。",
                        evidence=[f"contrast_span={screenshot_metrics['contrast_span']:.2f}"],
                    )
                )
                score -= 6
            else:
                strengths.append("截图具备基础的明暗层级变化。")

            if screenshot_metrics["unique_colors"] < 24:
                findings.append(
                    UIReviewFinding(
                        level="low",
                        title="截图配色层次偏单薄",
                        description="截图中的有效颜色层次较少，界面可能过平、过空或缺少视觉焦点。",
                        recommendation="在保证克制的前提下，补充强调色、模块层级和更清晰的界面节奏。",
                        evidence=[f"unique_colors={screenshot_metrics['unique_colors']}"],
                    )
                )
                score -= 4

            if screenshot_metrics["dominant_color_ratio"] > 0.78:
                findings.append(
                    UIReviewFinding(
                        level="low",
                        title="截图视觉表面过于单一",
                        description="截图中单一颜色表面占比过高，页面可能只有一层背景和少量内容，更像占位稿或 AI 模板，而不是成熟商业界面。",
                        recommendation="增加区块层、内容层、强调层和证明层的视觉切分，让页面形成更清晰的节奏与信息密度。",
                        evidence=[
                            f"dominant_color_ratio={screenshot_metrics['dominant_color_ratio']:.2f}"
                        ],
                    )
                )
                score -= 5
            else:
                strengths.append("截图没有出现单一表面吞没全页的问题。")

            if screenshot_metrics["accent_ratio"] < 0.006:
                findings.append(
                    UIReviewFinding(
                        level="low",
                        title="截图中缺少明显视觉焦点",
                        description="页面整体色彩变化过弱，CTA、重点模块或状态提示不够突出。",
                        recommendation="增强 CTA、标题层级、状态色和关键卡片的强调关系。",
                        evidence=[f"accent_ratio={screenshot_metrics['accent_ratio']:.4f}"],
                    )
                )
                score -= 4
            else:
                strengths.append("截图中存在一定视觉焦点和强调关系。")
        elif preview_path:
            notes.append("存在预览页，但本次未成功生成截图，已回退为结构级审查。")

        # UI/UX 专家视角检查
        expert_perspective_findings = self._run_expert_perspective_checks(
            source_content=source_content,
            preview_content=preview_content,
            uiux_content=uiux_content,
            ui_expert_dimensions=ui_expert_dimensions,
            ux_expert_dimensions=ux_expert_dimensions,
        )
        for epf in expert_perspective_findings:
            findings.append(epf)
            if epf.level == "high":
                score -= 6
            elif epf.level == "medium":
                score -= 4

        return UIReviewReport(
            project_name=self.name,
            score=max(0, min(100, score)),
            findings=findings,
            strengths=strengths,
            notes=notes,
            alignment_summary=alignment_summary,
        )
