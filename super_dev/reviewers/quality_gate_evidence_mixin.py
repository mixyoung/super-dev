"""Runtime, evidence and scoring checks for the quality gate."""

import json
import re
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from defusedxml import ElementTree

from super_dev.artifact_utils import ui_contract_filename

from ..artifact_utils import (
    latest_artifact,
    resolve_active_change_id,
)
from ..frameworks import framework_playbook_complete, is_cross_platform_frontend
from ..ui_contract_governance import (
    CLAUDE_DESIGN_RUNTIME_CHECKS,
    required_claude_design_runtime_checks,
)
from .fresh_verification_evidence import (
    inspect_current_fresh_verification,
)
from .quality_gate_models import CheckStatus, HostProfileMetrics, QualityCheck
from .redteam import RedTeamReport


class QualityGateEvidenceMixin:
    def _check_ui_contract_execution(self) -> QualityCheck:
        """检查 UI 契约、Design Token 与前端 runtime 是否闭环"""
        output_dir = self.project_dir / "output"
        ui_contract_path = output_dir / ui_contract_filename(self.name)
        frontend_dir = output_dir / "frontend"
        design_tokens_path = frontend_dir / "design-tokens.css"
        runtime_path = output_dir / f"{self.name}-frontend-runtime.json"
        alignment_path = output_dir / f"{self.name}-ui-contract-alignment.json"
        ui_review_path = output_dir / f"{self.name}-ui-review.json"

        if (
            not ui_contract_path.exists()
            and not frontend_dir.exists()
            and not runtime_path.exists()
        ):
            warning_score = 70 if self.is_zero_to_one else 50
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="尚未检测到前端实现阶段证据，暂无法验证 UI 契约执行闭环",
            )

        if not ui_contract_path.exists():
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=20,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="缺少 output/*-ui-contract.json，UI 系统决策尚未冻结成正式契约",
            )

        try:
            payload = json.loads(ui_contract_path.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=20,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="UI 契约 JSON 不可解析",
            )

        if not isinstance(payload, dict):
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=20,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="UI 契约必须是 JSON object",
            )

        component_stack_value = payload.get("component_stack")
        component_stack = component_stack_value if isinstance(component_stack_value, dict) else {}
        analysis_value = payload.get("analysis")
        analysis = analysis_value if isinstance(analysis_value, dict) else {}
        frontend_value = str(analysis.get("frontend") or "").lower().strip()
        cross_platform_frontend = is_cross_platform_frontend(frontend_value)
        emoji_policy_value = payload.get("emoji_policy")
        emoji_policy = emoji_policy_value if isinstance(emoji_policy_value, dict) else {}
        framework_playbook_value = payload.get("framework_playbook")
        framework_playbook = (
            framework_playbook_value if isinstance(framework_playbook_value, dict) else {}
        )
        screen_recipes_value = payload.get("screen_recipes")
        screen_recipes = (
            [item for item in screen_recipes_value if isinstance(item, dict)]
            if isinstance(screen_recipes_value, list)
            else []
        )
        design_context_value = payload.get("design_context_protocol")
        design_context_protocol = (
            design_context_value if isinstance(design_context_value, dict) else {}
        )
        tweak_strategy_value = payload.get("tweak_strategy")
        tweak_strategy = tweak_strategy_value if isinstance(tweak_strategy_value, dict) else {}
        verification_handoff_value = payload.get("verification_handoff")
        verification_handoff = (
            verification_handoff_value if isinstance(verification_handoff_value, dict) else {}
        )
        icon_system = (
            payload.get("icon_system")
            or component_stack.get("icon")
            or component_stack.get("icons")
            or ""
        )
        screen_recipe_ready = bool(screen_recipes) and all(
            isinstance(item, dict)
            and bool(item.get("section_order"))
            and bool(item.get("trust_modules"))
            and bool(item.get("required_states"))
            for item in screen_recipes
        )
        design_context_ready = (
            bool(design_context_protocol.get("preferred_import_order"))
            and bool(design_context_protocol.get("github_import_targets"))
            and bool(design_context_protocol.get("single_source_rule"))
        )
        tweak_strategy_ready = (
            bool(tweak_strategy.get("mode"))
            and bool(tweak_strategy.get("default_controls"))
            and bool(tweak_strategy.get("persistence_rule"))
        )
        verification_handoff_ready = (
            bool(verification_handoff.get("verification_order"))
            and bool(verification_handoff.get("required_artifacts"))
            and bool(verification_handoff.get("acceptance_checks"))
        )
        required_sections = {
            "style_direction": bool(payload.get("style_direction")),
            "typography": (
                (isinstance(payload.get("typography"), dict) and bool(payload.get("typography")))
                or (
                    isinstance(payload.get("typography_preset"), dict)
                    and bool(payload.get("typography_preset"))
                )
            ),
            "icon_system": bool(icon_system),
            "emoji_policy": (
                bool(emoji_policy)
                and emoji_policy.get("allowed_in_ui") is False
                and emoji_policy.get("allowed_as_icon") is False
                and emoji_policy.get("allowed_during_development") is False
            ),
            "ui_library_preference": isinstance(payload.get("ui_library_preference"), dict)
            and bool(payload.get("ui_library_preference")),
            "design_tokens": isinstance(payload.get("design_tokens"), dict)
            and bool(payload.get("design_tokens")),
            "screen_recipes": screen_recipe_ready,
            "design_context_protocol": design_context_ready,
            "tweak_strategy": tweak_strategy_ready,
            "verification_handoff": verification_handoff_ready,
        }
        if cross_platform_frontend:
            required_sections["framework_playbook"] = framework_playbook_complete(
                framework_playbook
            )
        missing_sections = [name for name, present in required_sections.items() if not present]
        if missing_sections:
            if cross_platform_frontend and "framework_playbook" in missing_sections:
                framework_name = str(
                    framework_playbook.get("framework") or frontend_value or "cross-platform"
                ).strip()
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=30,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details=(
                        f"{framework_name} 跨平台框架 playbook 缺少冻结字段: "
                        + ", ".join(missing_sections)
                    ),
                )
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details=f"UI 契约缺少冻结字段: {', '.join(missing_sections)}",
            )

        if frontend_dir.exists() and not design_tokens_path.exists():
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="前端产物存在，但缺少 output/frontend/design-tokens.css",
            )

        if not runtime_path.exists():
            if frontend_dir.exists():
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=35,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details="前端产物已生成，但 frontend runtime 报告缺失，无法证明运行时已接入",
                )
            warning_score = 75 if self.is_zero_to_one else 55
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="已冻结 UI 契约，但尚未检测到 frontend runtime 报告，无法确认运行时已接入",
            )

        if not alignment_path.exists():
            if frontend_dir.exists():
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=35,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details="前端产物和 runtime 已存在，但 UI 契约对齐报告缺失，无法证明源码已真正遵守 UI 契约",
                )
            warning_score = 80 if self.is_zero_to_one else 60
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="UI 契约和 frontend runtime 已存在，但 UI 契约对齐报告尚未生成，建议完成 UI review 后重新验证",
            )

        try:
            runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="frontend runtime JSON 不可解析",
            )

        if not isinstance(runtime_payload, dict):
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details="frontend runtime 必须是 JSON object",
            )

        checks = runtime_payload.get("checks", {})
        required_runtime_checks = required_claude_design_runtime_checks(payload)
        runtime_ready = (
            isinstance(checks, dict)
            and bool(runtime_payload.get("passed", False))
            and bool(checks.get("ui_contract_json", False))
            and bool(checks.get("output_frontend_design_tokens", False))
            and bool(checks.get("ui_contract_alignment", False))
            and bool(checks.get("ui_theme_entry", False))
            and bool(checks.get("ui_navigation_shell", False))
            and bool(checks.get("ui_component_imports", False))
            and bool(checks.get("ui_banned_patterns", False))
            and bool(checks.get("ui_framework_playbook", True))
            and bool(checks.get("ui_framework_execution", True))
            and all(bool(checks.get(name, False)) for name in required_runtime_checks)
        )
        if not runtime_ready:
            missing_protocol_checks = [
                CLAUDE_DESIGN_RUNTIME_CHECKS.get(name, name)
                for name in required_runtime_checks
                if not bool(checks.get(name, False))
            ]
            if cross_platform_frontend:
                framework_name = str(
                    framework_playbook.get("framework") or frontend_value or "cross-platform"
                ).strip()
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=35,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details=(
                        f"frontend runtime 未证明 {framework_name} 跨平台框架 playbook 与专项执行已真实接入前端"
                        + (
                            f"；Claude-Design 协议缺口: {', '.join(missing_protocol_checks)}"
                            if missing_protocol_checks
                            else ""
                        )
                    ),
                )
            return QualityCheck(
                name="UI 契约执行",
                category="ui_quality",
                description="UI 契约、Design Token 与运行时验证闭环",
                status=CheckStatus.FAILED,
                score=35,
                weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                details=(
                    "frontend runtime 未证明 UI 契约文件、Design Token 与跨平台框架 playbook 已真实接入前端"
                    + (
                        f"；Claude-Design 协议缺口: {', '.join(missing_protocol_checks)}"
                        if missing_protocol_checks
                        else ""
                    )
                ),
            )

        ui_review_payload: dict[str, Any] = {}
        if ui_review_path.exists():
            try:
                loaded_ui_review = json.loads(ui_review_path.read_text(encoding="utf-8"))
                if isinstance(loaded_ui_review, dict):
                    ui_review_payload = loaded_ui_review
            except Exception:
                ui_review_payload = {}
        alignment_value = ui_review_payload.get("alignment_summary")
        alignment_summary = alignment_value if isinstance(alignment_value, dict) else {}
        runtime_alignment_value = alignment_summary.get("runtime_claude_design_protocol")
        runtime_protocol_alignment = (
            runtime_alignment_value if isinstance(runtime_alignment_value, dict) else {}
        )
        source_alignment_value = alignment_summary.get("source_claude_design_protocol")
        source_protocol_alignment = (
            source_alignment_value if isinstance(source_alignment_value, dict) else {}
        )
        screenshot_judge_value = alignment_summary.get("screenshot_visual_judge")
        screenshot_visual_judge = (
            screenshot_judge_value if isinstance(screenshot_judge_value, dict) else {}
        )
        premium_ui_contract_keys = [
            ("brand_signal_manifest", "品牌信号与权威感"),
            ("proof_composition_rules", "证明构图规则"),
            ("component_craft_requirements", "组件工艺要求"),
            ("layout_tension_rules", "布局张力纪律"),
        ]
        if required_runtime_checks and ui_review_payload:
            if runtime_protocol_alignment and not bool(
                runtime_protocol_alignment.get("passed", False)
            ):
                observed = str(runtime_protocol_alignment.get("observed", "")).strip()
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=35,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details=(
                        "UI review 与 frontend runtime 的 Claude-Design 协议证据未闭环"
                        + (f"；{observed}" if observed else "")
                    ),
                )
            if source_protocol_alignment and not bool(
                source_protocol_alignment.get("passed", False)
            ):
                observed = str(source_protocol_alignment.get("observed", "")).strip()
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=35,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details=(
                        "UI review 未在源码/预览中看到 Claude-Design 协议落地信号"
                        + (f"；observed={observed}" if observed else "")
                    ),
                )
            if screenshot_visual_judge and not bool(screenshot_visual_judge.get("passed", False)):
                observed = str(screenshot_visual_judge.get("observed", "")).strip()
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=40,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details=(
                        "UI review 截图级视觉验收未通过，页面仍然过平、过空或过于单一"
                        + (f"；{observed}" if observed else "")
                    ),
                )
        if ui_review_payload:
            failed_premium_contracts: list[str] = []
            for key, label in premium_ui_contract_keys:
                contract_result = alignment_summary.get(key)
                if isinstance(contract_result, dict) and contract_result.get("passed") is False:
                    failed_premium_contracts.append(label)
            if failed_premium_contracts:
                return QualityCheck(
                    name="UI 契约执行",
                    category="ui_quality",
                    description="UI 契约、Design Token 与运行时验证闭环",
                    status=CheckStatus.FAILED,
                    score=42,
                    weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
                    details=(
                        "UI review 已指出高阶设计合同仍未冻结："
                        + "、".join(failed_premium_contracts)
                        + "；宿主还没有拿到足够强的品牌/证明/工艺/布局图纸。"
                    ),
                )

        library = payload.get("ui_library_preference", {}).get("final_selected", "-")
        return QualityCheck(
            name="UI 契约执行",
            category="ui_quality",
            description="UI 契约、Design Token 与运行时验证闭环",
            status=CheckStatus.PASSED,
            score=100,
            weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
            details=(
                "UI 契约已冻结并接入 runtime；"
                f"library={library}; icon={icon_system or '-'}; "
                "emoji_policy=forbidden"
            ),
        )

    def _check_ui_review(self) -> QualityCheck:
        """检查商业级 UI 基线和实现一致性"""
        from .ui_review import UIReviewReviewer

        reviewer = UIReviewReviewer(
            project_dir=self.project_dir,
            name=self.name,
            tech_stack=self.tech_stack,
        )
        report = reviewer.review()
        self.latest_ui_review_report = report

        blocking_titles = {
            "UI 系统决策未被完整冻结",
            "源码未落实文档冻结的图标系统",
            "源码未落实文档冻结的字体组合",
            "源码未落实文档冻结的组件生态",
        }
        has_blocking_alignment_gap = any(item.title in blocking_titles for item in report.findings)

        if report.critical_count > 0 or has_blocking_alignment_gap:
            status = CheckStatus.FAILED
        elif report.high_count > 0 or report.score < 80:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.PASSED

        detail_prefix = (
            f"score={report.score}, critical={report.critical_count}, "
            f"high={report.high_count}, medium={report.medium_count}"
        )
        if report.findings:
            details = f"{detail_prefix}; top issue: {report.findings[0].title}"
        else:
            details = f"{detail_prefix}; 未发现明显 UI 商业级违例"

        from ..design.ui_intelligence import UIIntelligenceAdvisor

        checklist = UIIntelligenceAdvisor.PRE_DELIVERY_CHECKLIST
        details += f" | 交付检查清单 ({len(checklist)} 项): " + "; ".join(checklist[:3]) + "..."

        return QualityCheck(
            name="UI 商业完成度",
            category="ui_quality",
            description="UI 设计基线、实现一致性与反模式扫描",
            status=status,
            score=report.score,
            weight=self.CHECKS_CONFIG["ui_quality"]["weight"],
            details=details,
        )

    def _check_security(self, redteam_report: RedTeamReport | None) -> list[QualityCheck]:
        """检查安全性"""
        checks: list[QualityCheck] = []

        if redteam_report:
            critical_count = sum(
                1 for i in redteam_report.security_issues if i.severity == "critical"
            )
            high_count = sum(1 for i in redteam_report.security_issues if i.severity == "high")

            if critical_count > 0:
                score = max(0, 100 - critical_count * 30)
                status = CheckStatus.FAILED
            elif high_count > 2:
                score = max(0, 100 - high_count * 15)
                status = CheckStatus.WARNING
            else:
                score = 100
                status = CheckStatus.PASSED

            checks.append(
                QualityCheck(
                    name="安全审查",
                    category="security",
                    description=f"安全检查 ({critical_count} critical, {high_count} high)",
                    status=status,
                    score=score,
                    weight=self.CHECKS_CONFIG["security"]["weight"],
                    details=(
                        f"发现 {critical_count} 个严重问题和 {high_count} 个高危问题"
                        if critical_count + high_count > 0
                        else "未发现严重安全问题"
                    ),
                )
            )
        else:
            # 未进行红队审查，给警告
            checks.append(
                QualityCheck(
                    name="安全审查",
                    category="security",
                    description="安全检查状态",
                    status=CheckStatus.WARNING,
                    score=50,
                    weight=self.CHECKS_CONFIG["security"]["weight"],
                    details="未进行红队安全审查",
                )
            )

        return checks

    def _check_performance(self, redteam_report: RedTeamReport | None) -> list[QualityCheck]:
        """检查性能"""
        checks: list[QualityCheck] = []

        if redteam_report:
            critical_count = sum(
                1 for i in redteam_report.performance_issues if i.severity == "critical"
            )
            high_count = sum(1 for i in redteam_report.performance_issues if i.severity == "high")

            if critical_count > 0:
                score = max(0, 100 - critical_count * 25)
                status = CheckStatus.FAILED
            elif high_count > 2:
                score = max(0, 100 - high_count * 10)
                status = CheckStatus.WARNING
            else:
                score = 100
                status = CheckStatus.PASSED

            checks.append(
                QualityCheck(
                    name="性能审查",
                    category="performance",
                    description=f"性能检查 ({critical_count} critical, {high_count} high)",
                    status=status,
                    score=score,
                    weight=self.CHECKS_CONFIG["performance"]["weight"],
                    details=(
                        f"发现 {critical_count} 个严重问题和 {high_count} 个高危问题"
                        if critical_count + high_count > 0
                        else "未发现严重性能问题"
                    ),
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="性能审查",
                    category="performance",
                    description="性能检查状态",
                    status=CheckStatus.WARNING,
                    score=50,
                    weight=self.CHECKS_CONFIG["performance"]["weight"],
                    details="未进行红队性能审查",
                )
            )

        return checks

    def _check_fresh_verification_evidence(self) -> QualityCheck:
        evidence = inspect_current_fresh_verification(self.project_dir)
        self.latest_fresh_verification_dependencies = list(evidence.dependencies)

        def failed(details: str) -> QualityCheck:
            return QualityCheck(
                name="测试执行",
                category="testing",
                description="当前代码版本的完成前验证证据",
                status=CheckStatus.FAILED,
                score=0,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details=details,
            )

        if not evidence.passed:
            return failed(evidence.detail)
        return QualityCheck(
            name="测试执行",
            category="testing",
            description="当前代码版本的完成前验证证据",
            status=CheckStatus.PASSED,
            score=100,
            weight=self.CHECKS_CONFIG["testing"]["weight"],
            details=evidence.detail,
        )

    def _append_testing_evidence_checks(self, checks: list[QualityCheck]) -> None:
        checks.append(self._check_spec_task_completion())
        checks.append(self._check_spec_code_consistency())
        checks.append(self._check_task_execution_review_trace())

        coverage_percent = self._read_coverage_percent()
        if coverage_percent is None:
            warning_score = 70 if self.is_zero_to_one else 50
            checks.append(
                QualityCheck(
                    name="测试覆盖率",
                    category="testing",
                    description="覆盖率报告",
                    status=CheckStatus.WARNING,
                    score=warning_score,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details="未检测到 coverage.xml 报告",
                )
            )
        elif coverage_percent >= 80:
            checks.append(
                QualityCheck(
                    name="测试覆盖率",
                    category="testing",
                    description="覆盖率报告",
                    status=CheckStatus.PASSED,
                    score=coverage_percent,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details=f"覆盖率 {coverage_percent}%",
                )
            )
        elif coverage_percent >= 60:
            checks.append(
                QualityCheck(
                    name="测试覆盖率",
                    category="testing",
                    description="覆盖率报告",
                    status=CheckStatus.WARNING,
                    score=coverage_percent,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details=f"覆盖率 {coverage_percent}%（建议提升到 80%+）",
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="测试覆盖率",
                    category="testing",
                    description="覆盖率报告",
                    status=CheckStatus.FAILED,
                    score=coverage_percent,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details=f"覆盖率 {coverage_percent}%（低于最低建议）",
                )
            )

    def _check_testing(self) -> list[QualityCheck]:
        """检查测试策略"""
        checks: list[QualityCheck] = []

        # 检查是否有测试配置
        has_jest = self._has_js_test_script()
        has_pytest = self._has_pytest_config()

        if has_jest or has_pytest:
            checks.append(
                QualityCheck(
                    name="测试框架",
                    category="testing",
                    description="测试框架配置",
                    status=CheckStatus.PASSED,
                    score=100,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details="测试框架已配置",
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="测试框架",
                    category="testing",
                    description="测试框架配置",
                    status=CheckStatus.WARNING,
                    score=50,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details="测试框架未配置",
                )
            )

        if self.fresh_verification_required:
            checks.append(self._check_fresh_verification_evidence())
            self._append_testing_evidence_checks(checks)
            return checks

        python_tests = self._discover_python_tests()
        js_test_targets = self._discover_js_test_targets()

        # 真实测试执行检查（优先 Python）
        if python_tests:
            pytest_executable = shutil.which("pytest")
            if pytest_executable:
                result = self._run_command(
                    [pytest_executable, "-q", "--maxfail=1"],
                    timeout=180,
                )
                if result["timed_out"]:
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.WARNING,
                            score=40,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details="pytest 执行超时，建议拆分测试或优化测试速度",
                        )
                    )
                elif result["returncode"] == 0:
                    summary = self._extract_test_summary(str(result["stdout"]))
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.PASSED,
                            score=100,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=summary or "pytest 执行通过",
                        )
                    )
                else:
                    summary = self._extract_test_summary(str(result["stdout"] or result["stderr"]))
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.FAILED,
                            score=20,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=summary or "pytest 执行失败",
                        )
                    )
            else:
                checks.append(
                    QualityCheck(
                        name="测试执行",
                        category="testing",
                        description="自动化测试执行结果",
                        status=CheckStatus.WARNING,
                        score=40,
                        weight=self.CHECKS_CONFIG["testing"]["weight"],
                        details="检测到 Python 测试，但未找到 pytest 可执行文件",
                    )
                )
        elif js_test_targets:
            npm_executable = shutil.which("npm")
            if not npm_executable:
                checks.append(
                    QualityCheck(
                        name="测试执行",
                        category="testing",
                        description="自动化测试执行结果",
                        status=CheckStatus.WARNING,
                        score=40,
                        weight=self.CHECKS_CONFIG["testing"]["weight"],
                        details="检测到 JS 测试脚本，但未找到 npm 可执行文件",
                    )
                )
            else:
                timed_out_targets: list[str] = []
                failed_targets: list[str] = []
                passed_targets: list[str] = []
                for target in js_test_targets:
                    rel = "."
                    if target != self.project_dir:
                        rel = str(target.relative_to(self.project_dir))
                    result = self._run_command(
                        [
                            npm_executable,
                            "--prefix",
                            str(target),
                            "run",
                            "test",
                            "--if-present",
                        ],
                        timeout=240,
                    )
                    if result["timed_out"]:
                        timed_out_targets.append(rel)
                    elif result["returncode"] == 0:
                        passed_targets.append(rel)
                    else:
                        failed_targets.append(rel)

                if failed_targets:
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.FAILED,
                            score=20,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=f"JS 测试失败: {', '.join(failed_targets)}",
                        )
                    )
                elif timed_out_targets:
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.WARNING,
                            score=40,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=f"JS 测试超时: {', '.join(timed_out_targets)}",
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name="测试执行",
                            category="testing",
                            description="自动化测试执行结果",
                            status=CheckStatus.PASSED,
                            score=100,
                            weight=self.CHECKS_CONFIG["testing"]["weight"],
                            details=f"JS 测试通过: {', '.join(passed_targets)}",
                        )
                    )
        else:
            warning_score = 70 if self.is_zero_to_one else 40
            checks.append(
                QualityCheck(
                    name="测试执行",
                    category="testing",
                    description="自动化测试执行结果",
                    status=CheckStatus.WARNING,
                    score=warning_score,
                    weight=self.CHECKS_CONFIG["testing"]["weight"],
                    details="未检测到可执行测试用例",
                )
            )

        self._append_testing_evidence_checks(checks)

        return checks

    def _check_task_execution_review_trace(self) -> QualityCheck:
        """检查任务执行报告是否包含最小自检轨迹"""
        output_dir = self.project_dir / "output"
        active_change_id = resolve_active_change_id(self.project_dir)
        latest_report = latest_artifact(
            output_dir,
            "*-task-execution.md",
            preferred_prefix=self.name,
            strict_prefix=bool(active_change_id),
        )
        if latest_report is None:
            warning_score = 70 if self.is_zero_to_one else 50
            return QualityCheck(
                name="任务执行自检轨迹",
                category="testing",
                description="任务执行报告中的最小自检记录",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details="未发现 output/*-task-execution.md",
            )

        content = latest_report.read_text(encoding="utf-8", errors="ignore")
        required_markers = [
            "## 执行期验证摘要",
            "## 宿主补充自检（交付前必做）",
            "build / compile / type-check / test / runtime smoke",
            "新增函数、方法、字段、模块都已接入真实调用链",
            "新增 warning",
            "对本次 diff 做最小自审",
        ]
        missing_markers = [marker for marker in required_markers if marker not in content]
        if missing_markers:
            return QualityCheck(
                name="任务执行自检轨迹",
                category="testing",
                description="任务执行报告中的最小自检记录",
                status=CheckStatus.WARNING,
                score=60 if self.is_zero_to_one else 50,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details=f"任务执行报告缺少自检字段: {', '.join(missing_markers)}",
            )

        return QualityCheck(
            name="任务执行自检轨迹",
            category="testing",
            description="任务执行报告中的最小自检记录",
            status=CheckStatus.PASSED,
            score=100,
            weight=self.CHECKS_CONFIG["testing"]["weight"],
            details=f"已记录最小自检轨迹（{latest_report.name}）",
        )

    def _check_spec_task_completion(self) -> QualityCheck:
        """检查 Spec 任务完成度"""
        changes_dir = self.project_dir / ".super-dev" / "changes"
        active_change_id = resolve_active_change_id(self.project_dir)
        if active_change_id:
            active_tasks = changes_dir / active_change_id / "tasks.md"
            task_files = [active_tasks] if active_tasks.is_file() else []
        else:
            task_files = list(changes_dir.glob("*/tasks.md"))
        if not task_files:
            warning_score = 70 if self.is_zero_to_one else 50
            return QualityCheck(
                name="Spec任务完成度",
                category="testing",
                description="Spec 任务闭环状态",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details="未发现 .super-dev/changes/*/tasks.md",
            )

        latest_task_file = max(task_files, key=lambda path: path.stat().st_mtime)
        total = 0
        completed = 0
        in_progress = 0
        for line in latest_task_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ["):
                continue
            marker = stripped[2:5]
            if not re.match(r"^\[[ x~_]\]$", marker):
                continue
            total += 1
            if marker == "[x]":
                completed += 1
            elif marker == "[~]":
                in_progress += 1

        if total == 0:
            warning_score = 70 if self.is_zero_to_one else 50
            return QualityCheck(
                name="Spec任务完成度",
                category="testing",
                description="Spec 任务闭环状态",
                status=CheckStatus.WARNING,
                score=warning_score,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details="发现 tasks.md 但未解析到任务项",
            )

        pending = total - completed
        completion_rate = int((completed / total) * 100) if total else 0
        if pending == 0 and in_progress == 0:
            return QualityCheck(
                name="Spec任务完成度",
                category="testing",
                description="Spec 任务闭环状态",
                status=CheckStatus.PASSED,
                score=100,
                weight=self.CHECKS_CONFIG["testing"]["weight"],
                details=f"任务完成 {completed}/{total}（{latest_task_file.parent.name}）",
            )

        score = max(20, completion_rate)
        check_status = CheckStatus.FAILED if completion_rate < 80 else CheckStatus.WARNING
        return QualityCheck(
            name="Spec任务完成度",
            category="testing",
            description="Spec 任务闭环状态",
            status=check_status,
            score=score,
            weight=self.CHECKS_CONFIG["testing"]["weight"],
            details=f"任务完成 {completed}/{total}，未完成 {pending}（{latest_task_file.parent.name}）",
        )

    def _check_spec_code_consistency(self) -> QualityCheck:
        """检查 Spec-Code 一致性（可选维度，失败不阻塞门禁）"""
        try:
            from ..specs.consistency_checker import SpecConsistencyChecker

            changes_dir = self.project_dir / ".super-dev" / "changes"
            if not changes_dir.exists():
                return QualityCheck(
                    name="Spec-Code一致性",
                    category="code_quality",
                    description="Spec 与代码实现一致性检测",
                    status=CheckStatus.WARNING,
                    score=70 if self.is_zero_to_one else 50,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details="未找到 .super-dev/changes/ 目录",
                )

            active_change_id = resolve_active_change_id(self.project_dir)
            if active_change_id:
                latest = changes_dir / active_change_id
                change_dirs = [latest] if latest.is_dir() else []
            else:
                change_dirs = [
                    d for d in changes_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
                ]
                latest = (
                    max(change_dirs, key=lambda d: d.stat().st_mtime)
                    if change_dirs
                    else changes_dir
                )
            if not change_dirs:
                return QualityCheck(
                    name="Spec-Code一致性",
                    category="code_quality",
                    description="Spec 与代码实现一致性检测",
                    status=CheckStatus.WARNING,
                    score=70 if self.is_zero_to_one else 50,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details="无活跃变更",
                )

            checker = SpecConsistencyChecker(self.project_dir)
            report = checker.check(latest.name)

            if report.consistency_score >= 90:
                return QualityCheck(
                    name="Spec-Code一致性",
                    category="code_quality",
                    description="Spec 与代码实现一致性检测",
                    status=CheckStatus.PASSED,
                    score=report.consistency_score,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details=f"一致性分数 {report.consistency_score}/100（{latest.name}）",
                )

            status = CheckStatus.WARNING if report.consistency_score >= 60 else CheckStatus.FAILED
            return QualityCheck(
                name="Spec-Code一致性",
                category="code_quality",
                description="Spec 与代码实现一致性检测",
                status=status,
                score=report.consistency_score,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=(
                    f"一致性分数 {report.consistency_score}/100，"
                    f"问题 {len(report.issues)} 项（{latest.name}）"
                ),
            )
        except Exception:
            return QualityCheck(
                name="Spec-Code一致性",
                category="code_quality",
                description="Spec 与代码实现一致性检测",
                status=CheckStatus.WARNING,
                score=50,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="一致性检测执行异常，已跳过",
            )

    def _check_code_quality(self) -> list[QualityCheck]:
        """检查代码质量工具"""
        checks: list[QualityCheck] = []

        # 检查 Linter
        has_eslint = (self.project_dir / ".eslintrc.js").exists() or (
            self.project_dir / ".eslintrc.json"
        ).exists()
        has_pylint = (self.project_dir / "pylint.ini").exists()
        try:
            has_black = (self.project_dir / "pyproject.toml").exists() and "black" in (
                self.project_dir / "pyproject.toml"
            ).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            has_black = False

        if has_eslint or has_pylint or has_black:
            checks.append(
                QualityCheck(
                    name="Linter",
                    category="code_quality",
                    description="代码静态检查工具",
                    status=CheckStatus.PASSED,
                    score=100,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details="Linter 已配置",
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="Linter",
                    category="code_quality",
                    description="代码静态检查工具",
                    status=CheckStatus.WARNING,
                    score=50,
                    weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                    details="Linter 未配置",
                )
            )

        python_roots = self._discover_python_source_roots()
        if python_roots:
            python_exec = shutil.which("python3") or shutil.which("python")
            if python_exec:
                cmd = [python_exec, "-m", "compileall", "-q", *[str(p) for p in python_roots]]
                result = self._run_command(cmd, timeout=120)
                if result["timed_out"]:
                    checks.append(
                        QualityCheck(
                            name="Python 语法检查",
                            category="code_quality",
                            description="compileall 语法检查",
                            status=CheckStatus.WARNING,
                            score=50,
                            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                            details="compileall 执行超时",
                        )
                    )
                elif result["returncode"] == 0:
                    checks.append(
                        QualityCheck(
                            name="Python 语法检查",
                            category="code_quality",
                            description="compileall 语法检查",
                            status=CheckStatus.PASSED,
                            score=100,
                            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                            details="Python 语法检查通过",
                        )
                    )
                else:
                    checks.append(
                        QualityCheck(
                            name="Python 语法检查",
                            category="code_quality",
                            description="compileall 语法检查",
                            status=CheckStatus.FAILED,
                            score=20,
                            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                            details="Python 语法检查失败",
                        )
                    )
            else:
                checks.append(
                    QualityCheck(
                        name="Python 语法检查",
                        category="code_quality",
                        description="compileall 语法检查",
                        status=CheckStatus.WARNING,
                        score=50,
                        weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                        details="未找到 python 解释器，跳过语法检查",
                    )
                )

        checks.append(self._check_pipeline_observability())
        checks.append(self._check_host_compatibility())
        checks.append(self._check_knowledge_governance())
        checks.append(self._check_launch_rehearsal())
        checks.append(self._check_rehearsal_verification_report())

        # Schema drift 检测
        checks.append(self._check_schema_drift())

        return checks

    def _check_pipeline_observability(self) -> QualityCheck:
        output_dir = self.project_dir / "output"
        metric_files = (
            sorted(output_dir.glob("*-pipeline-metrics.json")) if output_dir.exists() else []
        )
        if not metric_files:
            return QualityCheck(
                name="Pipeline 可观测性",
                category="code_quality",
                description="流水线指标报告",
                status=CheckStatus.WARNING,
                score=60 if self.is_zero_to_one else 50,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="未发现 output/*-pipeline-metrics.json",
            )

        latest = max(metric_files, key=lambda path: path.stat().st_mtime)
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="Pipeline 可观测性",
                category="code_quality",
                description="流水线指标报告",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"指标文件不可解析: {latest.name}",
            )

        success = bool(payload.get("success", False))
        success_rate = float(payload.get("success_rate", 0))
        if success and success_rate >= 90:
            status = CheckStatus.PASSED
            score = 100
        elif success:
            status = CheckStatus.WARNING
            score = 80
        else:
            status = CheckStatus.FAILED
            score = 40

        return QualityCheck(
            name="Pipeline 可观测性",
            category="code_quality",
            description="流水线指标报告",
            status=status,
            score=score,
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details=f"{latest.name} | success_rate={success_rate:.1f}%",
        )

    def _check_host_compatibility(self) -> QualityCheck:
        min_score = float(self.host_compatibility_min_score)
        min_ready_hosts = self.host_compatibility_min_ready_hosts
        warning_threshold = max(40.0, min_score - 20.0)

        output_dir = self.project_dir / "output"
        reports = (
            sorted(output_dir.glob("*-host-compatibility.json")) if output_dir.exists() else []
        )
        if not reports:
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.WARNING,
                score=70 if self.is_zero_to_one else 60,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=(
                    "未发现 output/*-host-compatibility.json "
                    f"(目标阈值: score>={min_score:.0f}, ready_hosts>={min_ready_hosts})"
                ),
            )

        latest = max(reports, key=lambda path: path.stat().st_mtime)
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"兼容性报告不可解析: {latest.name}",
            )

        compatibility = payload.get("compatibility", {}) if isinstance(payload, dict) else {}
        if not isinstance(compatibility, dict):
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"兼容性报告结构非法: {latest.name}",
            )

        try:
            overall_score = float(compatibility.get("overall_score", 0))
        except (TypeError, ValueError):
            overall_score = 0.0
        try:
            ready_hosts = int(compatibility.get("ready_hosts", 0))
        except (TypeError, ValueError):
            ready_hosts = 0
        try:
            total_hosts = int(compatibility.get("total_hosts", 0))
        except (TypeError, ValueError):
            total_hosts = 0

        bounded_score = max(0, min(100, int(round(overall_score))))
        details = (
            f"{latest.name} | overall={overall_score:.2f} | " f"ready={ready_hosts}/{total_hosts}"
        )

        profile = self._host_profile_metrics(compatibility)
        if profile is not None:
            overall_score = self._coerce_float(profile.get("overall_score"), default=0.0)
            ready_hosts = self._coerce_int(profile.get("ready_hosts"), default=0)
            total_hosts = self._coerce_int(profile.get("total_hosts"), default=0)
            bounded_score = self._coerce_int(profile.get("bounded_score"), default=0)
            details = (
                f"{latest.name} | profile={profile.get('label', 'unknown')} | overall={overall_score:.2f} | "
                f"ready={ready_hosts}/{total_hosts}"
            )

        if overall_score >= min_score and ready_hosts >= min_ready_hosts:
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.PASSED,
                score=bounded_score,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=details,
            )

        if overall_score >= warning_threshold:
            return QualityCheck(
                name="宿主兼容性",
                category="code_quality",
                description="AI Coding 宿主接入兼容性报告",
                status=CheckStatus.WARNING,
                score=bounded_score,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=(
                    f"{details}（建议至少 {min_score:.0f} 分且 "
                    f"ready host >= {min_ready_hosts}）"
                ),
            )

        return QualityCheck(
            name="宿主兼容性",
            category="code_quality",
            description="AI Coding 宿主接入兼容性报告",
            status=CheckStatus.FAILED,
            score=max(20, bounded_score),
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details=f"{details}（低于最低建议阈值）",
        )

    def _host_profile_metrics(self, compatibility: dict[str, object]) -> HostProfileMetrics | None:
        if not self.host_profile_enforce_selected or not self.host_profile_targets:
            return None

        hosts_obj = compatibility.get("hosts", {})
        hosts = hosts_obj if isinstance(hosts_obj, dict) else {}
        selected = [item for item in self.host_profile_targets if item in hosts]
        if not selected:
            return HostProfileMetrics(
                label=",".join(self.host_profile_targets),
                overall_score=0.0,
                ready_hosts=0,
                total_hosts=len(self.host_profile_targets),
                bounded_score=0,
            )

        score_values: list[float] = []
        ready_hosts = 0
        for target in selected:
            host_data = hosts.get(target, {})
            if isinstance(host_data, dict):
                try:
                    score_values.append(float(host_data.get("score", 0.0)))
                except (TypeError, ValueError):
                    score_values.append(0.0)
                if bool(host_data.get("ready", False)):
                    ready_hosts += 1
            else:
                score_values.append(0.0)

        overall_score = sum(score_values) / len(score_values) if score_values else 0.0
        bounded_score = max(0, min(100, int(round(overall_score))))
        return {
            "label": ",".join(selected),
            "overall_score": overall_score,
            "ready_hosts": ready_hosts,
            "total_hosts": len(selected),
            "bounded_score": bounded_score,
        }

    def _check_knowledge_governance(self) -> QualityCheck:
        config_file = self.project_dir / "super-dev.yaml"
        config_domains: list[str] = []
        config_ttl = 1800
        if config_file.exists():
            try:
                raw_config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
                if isinstance(raw_config, dict):
                    domains_raw = raw_config.get("knowledge_allowed_domains", [])
                    if isinstance(domains_raw, list):
                        config_domains = [
                            str(item).strip().lower() for item in domains_raw if str(item).strip()
                        ]
                    ttl_raw = raw_config.get("knowledge_cache_ttl_seconds", 1800)
                    if isinstance(ttl_raw, int):
                        config_ttl = ttl_raw
                    elif isinstance(ttl_raw, str) and ttl_raw.strip().isdigit():
                        config_ttl = int(ttl_raw.strip())
            except Exception:
                pass

        cache_dir = self.project_dir / "output" / "knowledge-cache"
        bundles = sorted(cache_dir.glob("*-knowledge-bundle.json")) if cache_dir.exists() else []
        if not bundles:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.WARNING,
                score=70 if self.is_zero_to_one else 60,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="未发现 output/knowledge-cache/*-knowledge-bundle.json",
            )

        latest = max(bundles, key=lambda path: path.stat().st_mtime)
        try:
            bundle = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"知识缓存不可解析: {latest.name}",
            )
        if not isinstance(bundle, dict):
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details=f"知识缓存结构非法: {latest.name}",
            )

        signature = str(bundle.get("cache_signature", "")).strip()
        if not signature:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.FAILED,
                score=30,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="知识缓存缺少 cache_signature",
            )

        ttl_value = bundle.get("cache_ttl_seconds", config_ttl)
        bundle_ttl = ttl_value if isinstance(ttl_value, int) else config_ttl
        metadata = bundle.get("metadata", {})
        metadata_dict = metadata if isinstance(metadata, dict) else {}
        web_enabled = bool(metadata_dict.get("web_enabled", False))
        bundle_domains_raw = metadata_dict.get("allowed_web_domains", [])
        bundle_domains = (
            [str(item).strip().lower() for item in bundle_domains_raw if str(item).strip()]
            if isinstance(bundle_domains_raw, list)
            else []
        )
        web_stats = metadata_dict.get("web_stats", {})
        filtered_out_count = 0
        if isinstance(web_stats, dict):
            raw_filtered = web_stats.get("filtered_out_count", 0)
            if isinstance(raw_filtered, int):
                filtered_out_count = raw_filtered

        if bundle_ttl <= 0:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.WARNING,
                score=70,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="knowledge_cache_ttl_seconds <= 0，缓存治理策略关闭",
            )

        if web_enabled and not bundle_domains:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.WARNING,
                score=75,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="联网知识未配置白名单域名",
            )

        config_domain_set = set(config_domains)
        bundle_domain_set = set(bundle_domains)
        if config_domain_set and bundle_domain_set and config_domain_set != bundle_domain_set:
            return QualityCheck(
                name="知识增强治理",
                category="code_quality",
                description="知识来源白名单与缓存可审计性",
                status=CheckStatus.WARNING,
                score=80,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="缓存白名单与项目配置不一致",
            )

        details = (
            f"{latest.name} | ttl={bundle_ttl}s | "
            f"domains={len(bundle_domains)} | filtered_out={filtered_out_count}"
        )
        return QualityCheck(
            name="知识增强治理",
            category="code_quality",
            description="知识来源白名单与缓存可审计性",
            status=CheckStatus.PASSED,
            score=100,
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details=details,
        )

    def _check_launch_rehearsal(self) -> QualityCheck:
        if self.platform == "cli":
            return QualityCheck(
                name="发布演练准备",
                category="code_quality",
                description="发布演练与回滚手册",
                status=CheckStatus.PASSED,
                score=100,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="CLI 项目不适用服务部署演练，发布闭环由 release readiness 与 proof-pack 验证",
            )
        rehearsal_dir = self.project_dir / "output" / "rehearsal"
        required_patterns = [
            "*-launch-rehearsal.md",
            "*-rollback-playbook.md",
            "*-smoke-checklist.md",
        ]
        found = 0
        if rehearsal_dir.exists():
            for pattern in required_patterns:
                if any(rehearsal_dir.glob(pattern)):
                    found += 1

        if found == len(required_patterns):
            return QualityCheck(
                name="发布演练准备",
                category="code_quality",
                description="发布演练与回滚手册",
                status=CheckStatus.PASSED,
                score=100,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="发布演练文档齐全",
            )
        if found == 0:
            return QualityCheck(
                name="发布演练准备",
                category="code_quality",
                description="发布演练与回滚手册",
                status=CheckStatus.WARNING,
                score=60 if self.is_zero_to_one else 50,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="未发现 output/rehearsal/* 发布演练文档",
            )
        return QualityCheck(
            name="发布演练准备",
            category="code_quality",
            description="发布演练与回滚手册",
            status=CheckStatus.WARNING,
            score=75,
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details=f"发布演练文档不完整 ({found}/{len(required_patterns)})",
        )

    def _check_rehearsal_verification_report(self) -> QualityCheck:
        if self.platform == "cli":
            return QualityCheck(
                name="发布演练验证报告",
                category="code_quality",
                description="发布演练验证结果",
                status=CheckStatus.PASSED,
                score=100,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="CLI 项目不适用服务部署演练，发布闭环由 release readiness 与 proof-pack 验证",
            )
        rehearsal_dir = self.project_dir / "output" / "rehearsal"
        if not rehearsal_dir.exists():
            return QualityCheck(
                name="发布演练验证报告",
                category="code_quality",
                description="发布演练验证结果",
                status=CheckStatus.WARNING,
                score=60 if self.is_zero_to_one else 50,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="未发现 output/rehearsal 目录",
            )

        has_md = any(rehearsal_dir.glob("*-rehearsal-report.md"))
        has_json = any(rehearsal_dir.glob("*-rehearsal-report.json"))
        if has_md and has_json:
            return QualityCheck(
                name="发布演练验证报告",
                category="code_quality",
                description="发布演练验证结果",
                status=CheckStatus.PASSED,
                score=100,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="已生成 rehearsal markdown + json 报告",
            )
        if has_md or has_json:
            return QualityCheck(
                name="发布演练验证报告",
                category="code_quality",
                description="发布演练验证结果",
                status=CheckStatus.WARNING,
                score=80,
                weight=self.CHECKS_CONFIG["code_quality"]["weight"],
                details="发布演练报告格式不完整（需同时包含 md 与 json）",
            )
        return QualityCheck(
            name="发布演练验证报告",
            category="code_quality",
            description="发布演练验证结果",
            status=CheckStatus.WARNING,
            score=70 if self.is_zero_to_one else 60,
            weight=self.CHECKS_CONFIG["code_quality"]["weight"],
            details="未发现 output/rehearsal/*-rehearsal-report.(md|json)",
        )

    def _check_schema_drift(self) -> QualityCheck:
        """检测 ORM 模型文件是否比最新迁移文件更新（schema drift）"""
        weight = self.CHECKS_CONFIG["schema_drift"]["weight"]
        if self.database in {"", "none"}:
            return QualityCheck(
                name="Schema Drift 检测",
                category="schema_drift",
                description="ORM 模型与数据库迁移文件一致性",
                status=CheckStatus.PASSED,
                score=100,
                weight=weight,
                details="项目未配置数据库，Schema Drift 检测不适用",
            )

        model_patterns = [
            "**/models.py",
            "**/models/*.py",
            "**/schema.py",
            "**/entities/*.py",
            "**/*.entity.ts",
            "**/prisma/schema.prisma",
        ]
        migration_patterns = [
            "**/migrations/**",
            "**/alembic/**",
            "**/prisma/migrations/**",
            "**/drizzle/**",
        ]

        # Collect model files with their latest mtime
        model_files: list[Path] = []
        for pattern in model_patterns:
            model_files.extend(self.project_dir.glob(pattern))

        # Filter out __pycache__, node_modules, .git, and migration dirs themselves
        skip_segments = {"__pycache__", "node_modules", ".git", "migrations", "alembic"}
        model_files = [f for f in model_files if f.is_file() and not (skip_segments & set(f.parts))]

        if not model_files:
            return QualityCheck(
                name="Schema Drift 检测",
                category="schema_drift",
                description="ORM 模型与数据库迁移文件一致性",
                status=CheckStatus.PASSED,
                score=100,
                weight=weight,
                details="未发现 ORM 模型文件，跳过检测",
            )

        latest_model_mtime = max(f.stat().st_mtime for f in model_files)

        # Collect migration files
        migration_files: list[Path] = []
        for pattern in migration_patterns:
            migration_files.extend(f for f in self.project_dir.glob(pattern) if f.is_file())
        migration_files = [
            f
            for f in migration_files
            if not ({"__pycache__", "node_modules", ".git"} & set(f.parts))
        ]

        if not migration_files:
            # Models exist but no migrations at all — warn
            model_names = ", ".join(sorted(f.name for f in model_files[:5]))
            suffix = "..." if len(model_files) > 5 else ""
            return QualityCheck(
                name="Schema Drift 检测",
                category="schema_drift",
                description="ORM 模型与数据库迁移文件一致性",
                status=CheckStatus.WARNING,
                score=60,
                weight=weight,
                details=(
                    f"发现 {len(model_files)} 个模型文件 ({model_names}{suffix}) "
                    "但未找到任何迁移文件，可能存在 schema drift"
                ),
            )

        latest_migration_mtime = max(f.stat().st_mtime for f in migration_files)

        if latest_model_mtime > latest_migration_mtime:
            # Find which model files are newer than latest migration
            drifted = [f for f in model_files if f.stat().st_mtime > latest_migration_mtime]
            drifted_names = ", ".join(
                sorted(str(f.relative_to(self.project_dir)) for f in drifted[:5])
            )
            suffix = "..." if len(drifted) > 5 else ""
            return QualityCheck(
                name="Schema Drift 检测",
                category="schema_drift",
                description="ORM 模型与数据库迁移文件一致性",
                status=CheckStatus.WARNING,
                score=65,
                weight=weight,
                details=(
                    f"模型文件 ({drifted_names}{suffix}) 比最新迁移文件更新，"
                    "可能需要生成新的数据库迁移"
                ),
            )

        return QualityCheck(
            name="Schema Drift 检测",
            category="schema_drift",
            description="ORM 模型与数据库迁移文件一致性",
            status=CheckStatus.PASSED,
            score=100,
            weight=weight,
            details="模型文件与迁移文件时间戳一致，未检测到 schema drift",
        )

    def _calculate_total_score(self, checks: list[QualityCheck]) -> int:
        """计算总分"""
        score_checks = self._score_bearing_checks(checks)
        if not score_checks:
            return 0

        return round(sum(c.score for c in score_checks) / len(score_checks))

    def _calculate_weighted_score(self, checks: list[QualityCheck]) -> float:
        """计算加权分"""
        score_checks = self._score_bearing_checks(checks)
        if not score_checks:
            return 0.0

        total_weight = sum(c.weight for c in score_checks)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(c.score * c.weight for c in score_checks)
        return weighted_sum / total_weight

    def _score_bearing_checks(self, checks: list[QualityCheck]) -> list[QualityCheck]:
        """返回参与门禁总分计算的检查项。

        advisory 型交叉审查和非阻断验证规则仍然保留在报告里，
        但不应把默认 0-1 流水线直接压成失败。
        """
        filtered: list[QualityCheck] = []
        for check in checks:
            if check.category == "cross_review":
                continue
            if check.category == "validation_rules" and check.status != CheckStatus.FAILED:
                continue
            filtered.append(check)
        return filtered

    def _generate_recommendations(self, checks: list[QualityCheck]) -> list[str]:
        """生成改进建议"""
        recommendations: list[str] = []

        fix_command_map = [
            ("PRD 文档", "运行 `super-dev run` 生成文档"),
            ("架构文档", "运行 `super-dev run` 生成文档"),
            ("UI/UX 文档", "运行 `super-dev run` 生成文档"),
            ("安全", "运行 `super-dev quality --type security` 查看详情"),
            ("测试", "运行 `pytest` 执行测试"),
            ("Spec 任务", "查看当前 change 的 `tasks.md` 与 Spec 状态，确认待实现任务是否仍未闭环"),
            ("宿主兼容性", "运行 `super-dev doctor --repair` 修复"),
            ("演练", "运行 `super-dev release readiness` 检查"),
            ("UI 质量", "运行 `super-dev review ui` 查看 UI 审查报告"),
        ]

        for check in checks:
            if check.status == CheckStatus.FAILED:
                prefix = "修复"
            elif check.status == CheckStatus.WARNING:
                prefix = "建议"
            else:
                continue

            description = check.description
            fix_hint = ""
            for keyword, command in fix_command_map:
                if keyword in description:
                    fix_hint = f" [修复: {command}]"
                    break

            recommendations.append(f"{prefix}: {description}{fix_hint}")

        return recommendations

    def _discover_python_tests(self) -> list[Path]:
        roots = [self.project_dir / "tests", self.project_dir / "backend" / "tests"]
        files: list[Path] = []
        for tests_dir in roots:
            if not tests_dir.exists():
                continue
            files.extend(list(tests_dir.rglob("test_*.py")))
            files.extend(list(tests_dir.rglob("*_test.py")))
        return files

    def _has_pytest_config(self) -> bool:
        if (self.project_dir / "pytest.ini").exists():
            return True

        setup_cfg = self.project_dir / "setup.cfg"
        if setup_cfg.exists():
            content = setup_cfg.read_text(encoding="utf-8", errors="ignore")
            if "[tool:pytest]" in content:
                return True

        tox_ini = self.project_dir / "tox.ini"
        if tox_ini.exists():
            content = tox_ini.read_text(encoding="utf-8", errors="ignore")
            if "[pytest]" in content:
                return True

        pyproject = self.project_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            if "pytest.ini_options" in content:
                return True

        backend_pyproject = self.project_dir / "backend" / "pyproject.toml"
        if backend_pyproject.exists():
            content = backend_pyproject.read_text(encoding="utf-8", errors="ignore")
            if "pytest.ini_options" in content:
                return True

        return False

    def _discover_python_source_roots(self) -> list[Path]:
        roots: list[Path] = []
        candidates = ["super_dev", "src", "app", "backend", "server", "api", "services", "lib"]
        for name in candidates:
            path = self.project_dir / name
            if path.exists() and path.is_dir():
                roots.append(path)

        top_level_py = list(self.project_dir.glob("*.py"))
        roots.extend(top_level_py)

        # 去重并限制数量，避免无界扫描
        unique: list[Path] = []
        seen = set()
        for path in roots:
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            unique.append(path)
        return unique[:8]

    def _discover_js_test_targets(self) -> list[Path]:
        targets: list[Path] = []
        for root in (self.project_dir, self.project_dir / "frontend", self.project_dir / "backend"):
            package_json = root / "package.json"
            if not package_json.exists():
                continue
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception:
                continue
            scripts = data.get("scripts", {})
            test_script = str(scripts.get("test", "")).strip()
            if not test_script:
                continue
            if test_script == 'echo "Error: no test specified" && exit 1':
                continue
            targets.append(root)
        return targets

    def _has_js_test_script(self) -> bool:
        return bool(self._discover_js_test_targets())

    def _extract_test_summary(self, output: str) -> str:
        if not output:
            return ""
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for line in reversed(lines):
            if "passed" in line or "failed" in line or "error" in line:
                return line[:240]
        return lines[-1][:240] if lines else ""

    def _read_coverage_percent(self) -> int | None:
        coverage_candidates = [
            self.project_dir / "coverage.xml",
            self.project_dir / "backend" / "coverage.xml",
            self.project_dir / "frontend" / "coverage.xml",
            self.project_dir / "coverage" / "cobertura-coverage.xml",
            self.project_dir / "frontend" / "coverage" / "cobertura-coverage.xml",
            self.project_dir / "backend" / "coverage" / "cobertura-coverage.xml",
        ]

        parsed_values: list[int] = []
        for coverage_xml in coverage_candidates:
            if not coverage_xml.exists():
                continue
            try:
                root = ElementTree.fromstring(coverage_xml.read_text(encoding="utf-8"))
                line_rate = root.attrib.get("line-rate")
                if line_rate is not None:
                    parsed_values.append(max(0, min(100, int(round(float(line_rate) * 100)))))
                    continue

                lines_covered = root.attrib.get("lines-covered")
                lines_valid = root.attrib.get("lines-valid")
                if lines_covered and lines_valid and float(lines_valid) > 0:
                    percent = (float(lines_covered) / float(lines_valid)) * 100
                    parsed_values.append(max(0, min(100, int(round(percent)))))
            except Exception:
                continue

        if not parsed_values:
            return None
        return max(parsed_values)

    def _run_command(self, cmd: list[str], timeout: int = 120) -> dict[str, object]:
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )  # nosec B603
            return {
                "returncode": completed.returncode,
                "stdout": completed.stdout or "",
                "stderr": completed.stderr or "",
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as e:
            return {
                "returncode": -1,
                "stdout": (e.stdout or ""),
                "stderr": (e.stderr or ""),
                "timed_out": True,
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "timed_out": False,
            }
