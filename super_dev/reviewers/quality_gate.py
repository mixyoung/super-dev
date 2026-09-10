"""
质量门禁检查器 - 确保交付物达到质量标准

开发：Excellent（11964948@qq.com）
功能：多维度质量评分和门禁检查
作用：按场景阈值（或自定义阈值）评估是否通过质量门禁
创建时间：2025-12-30
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..artifact_utils import (
    resolve_active_change_id,
    resolve_current_artifact_prefix,
)
from ..baseline_governance import inspect_baseline_governance
from ..config import ConfigManager
from ..host_runtime_governance import collect_layered_runtime_governance_gap
from ..host_workflow_context import build_host_workflow_context
from ..workflow_guard import docs_gate_status
from .fresh_verification_evidence import (
    FreshVerificationEvidence,
    fresh_verification_required,
    inspect_current_fresh_verification,
    quality_evidence_dependency_paths,
    quality_fresh_binding_matches,
    stored_quality_evidence_dependencies,
)
from .quality_gate_evidence_mixin import QualityGateEvidenceMixin
from .quality_gate_models import CheckStatus, HostProfileMetrics, QualityCheck
from .redteam import RedTeamReport
from .validation_rules import ValidationRuleEngine

__all__ = [
    "CheckStatus",
    "FreshVerificationEvidence",
    "HostProfileMetrics",
    "QualityCheck",
    "QualityGateChecker",
    "QualityGateResult",
    "fresh_verification_required",
    "inspect_current_fresh_verification",
    "quality_evidence_dependency_paths",
    "quality_fresh_binding_matches",
    "stored_quality_evidence_dependencies",
]

try:
    from .review_agents import build_parallel_review_prompt

    REVIEW_AGENTS_AVAILABLE = True
except ImportError:
    REVIEW_AGENTS_AVAILABLE = False


@dataclass
class QualityGateResult:
    """质量门禁结果"""

    passed: bool
    total_score: int
    weighted_score: float
    checks: list[QualityCheck] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    scenario: str = "1-N+1"  # 场景类型: "0-1" 或 "1-N+1"
    threshold: float = 80.0
    summary_context: dict[str, str] = field(default_factory=dict)

    @property
    def gate_score(self) -> float:
        """返回用于阈值判定的加权门禁分。"""

        return self.weighted_score

    @property
    def passed_checks(self) -> list[QualityCheck]:
        return [c for c in self.checks if c.status == CheckStatus.PASSED]

    @property
    def failed_checks(self) -> list[QualityCheck]:
        return [c for c in self.checks if c.status == CheckStatus.FAILED]

    @property
    def warning_checks(self) -> list[QualityCheck]:
        return [c for c in self.checks if c.status == CheckStatus.WARNING]

    @property
    def executive_summary(self) -> str:
        layered_runtime_text = str(self.summary_context.get("host_runtime_layered_gap", "")).strip()
        compliance_text = str(self.summary_context.get("compliance_signal_summary", "")).strip()
        workflow_text = str(self.summary_context.get("workflow_signal_summary", "")).strip()
        baseline_text = str(self.summary_context.get("baseline_signal_summary", "")).strip()
        if self.passed:
            return (
                f"质量门禁已通过，门禁分（加权）{self.gate_score:.1f}/100，"
                f"阈值 {self.threshold:g}/100；未加权平均分 {self.total_score}/100。"
                f"{workflow_text}{baseline_text}{layered_runtime_text}{compliance_text}"
            )
        priority_checks = self.failed_checks or sorted(
            self.warning_checks,
            key=lambda check: check.score,
        )
        priority_names = "、".join(check.name for check in priority_checks[:3])
        if not priority_names:
            priority_names = "提升低分检查项"
        return (
            f"质量门禁未通过，门禁分（加权）{self.gate_score:.1f}/100，"
            f"阈值 {self.threshold:g}/100；未加权平均分 {self.total_score}/100。"
            f"优先修复：{priority_names}。{workflow_text}{baseline_text}{layered_runtime_text}{compliance_text}"
        )

    @property
    def expert_summary(self) -> dict[str, dict]:
        """按专家角色汇总检查结果"""
        try:
            rule_to_expert = {
                "documentation": "PM",
                "security": "SECURITY",
                "performance": "DEVOPS",
                "testing": "QA",
                "code_quality": "CODE",
                "validation_rules": "QA",
                "accessibility": "CODE",
                "ui_quality": "UI",
                "schema_drift": "CODE",
                "spec_compliance": "ARCHITECT",
                "architecture_drift": "ARCHITECT",
                "uiux_compliance": "UI",
            }

            expert_results: dict[str, dict] = {}
            for check in self.checks:
                expert = rule_to_expert.get(check.category, "CODE")
                if expert not in expert_results:
                    expert_results[expert] = {"passed": 0, "failed": 0, "score": 0, "checks": []}
                expert_results[expert]["checks"].append(check)
                if check.status == CheckStatus.PASSED:
                    expert_results[expert]["passed"] += 1
                else:
                    expert_results[expert]["failed"] += 1

            # 计算每个专家的平均分
            for expert, data in expert_results.items():
                total = data["passed"] + data["failed"]
                if total > 0:
                    data["score"] = int(sum(c.score for c in data["checks"]) / total)

            return expert_results
        except Exception:
            return {}

    def to_markdown(self) -> str:
        """生成 Markdown 报告"""
        status_icon = "通过" if self.passed else "未通过"
        status_color = "green" if self.passed else "red"

        lines = [
            "# 质量门禁报告",
            "",
            f"**场景**: {self.scenario} ({'0-1 新建项目' if self.scenario == '0-1' else '1-N+1 增量开发'})",
            f"**状态**: <span style='color:{status_color}'>{status_icon}</span>",
            f"**未加权平均分**: {self.total_score}/100",
            f"**门禁分（加权）**: {self.gate_score:.1f}/100",
            f"**门禁阈值**: {self.threshold:g}/100",
            "",
            "---",
            "",
            "## 执行摘要",
            "",
            self.executive_summary,
            "",
            "## 检查结果摘要",
            "",
            f"- 通过: {len(self.passed_checks)} 项",
            f"- 警告: {len(self.warning_checks)} 项",
            f"- 失败: {len(self.failed_checks)} 项",
            "",
        ]

        if self.critical_failures:
            lines.extend(
                [
                    "## 关键失败项",
                    "",
                ]
            )
            for failure in self.critical_failures:
                lines.append(f"- {failure}")
            lines.append("")

        # 按类别分组展示
        categories: dict[str, list[QualityCheck]] = {}
        for check in self.checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check)

        lines.extend(
            [
                "## 详细检查结果",
                "",
            ]
        )

        for category, checks in categories.items():
            lines.extend(
                [
                    f"### {category}",
                    "",
                    "| 检查项 | 状态 | 得分 | 说明 |",
                    "|:---|:---:|:---:|:---|",
                ]
            )

            for check in checks:
                status_icon = (
                    "✓"
                    if check.status == CheckStatus.PASSED
                    else "⚠" if check.status == CheckStatus.WARNING else "✗"
                )
                lines.append(
                    f"| {check.name} | {status_icon} | {check.score}/100 | {check.description} |"
                )

            lines.append("")

        # 验证规则专属区域
        rule_checks = [c for c in self.checks if c.category == "validation_rules"]
        if rule_checks:
            lines.extend(
                [
                    "## 可编程验证规则结果",
                    "",
                    f"共触发 {len(rule_checks)} 条规则违反：",
                    "",
                    "| 规则 | 状态 | 严重程度 | 描述 | 修复建议 |",
                    "|:---|:---:|:---:|:---|:---|",
                ]
            )
            for check in rule_checks:
                status_icon = "✗" if check.status == CheckStatus.FAILED else "⚠"
                severity = "critical" if check.weight >= 1.5 else "non-critical"
                fix = check.details if check.details else "-"
                lines.append(
                    f"| {check.name} | {status_icon} | {severity} | {check.description} | {fix} |"
                )
            lines.append("")

        # 专家视角总结
        try:
            expert_data = self.expert_summary
            if expert_data:
                lines.extend(
                    [
                        "## 专家视角总结",
                        "",
                        "| 专家 | 通过 | 失败 | 平均分 | 评价 |",
                        "|------|------|------|--------|------|",
                    ]
                )

                for expert, data in expert_data.items():
                    rating = (
                        "优秀"
                        if data["score"] >= 80
                        else "需改进" if data["score"] >= 60 else "不合格"
                    )
                    lines.append(
                        f"| {expert} | {data['passed']} | {data['failed']} | {data['score']} | {rating} |"
                    )

                lines.append("")
        except Exception:
            pass

        # 改进建议
        if self.recommendations:
            lines.extend(
                [
                    "## 改进建议",
                    "",
                ]
            )
            for idx, rec in enumerate(self.recommendations, 1):
                lines.append(f"{idx}. {rec}")
            lines.append("")

        # 质量顾问建议
        try:
            from .quality_advisor import QualityAdvisor

            advisor = QualityAdvisor(Path.cwd())
            advisor_report = advisor.analyze(self)
            if advisor_report.advices:
                lines.extend(
                    [
                        "## 质量顾问建议",
                        "",
                        f"共 {len(advisor_report.advices)} 条建议"
                        f"（关键 {len(advisor_report.critical_advices)}、"
                        f"Quick Win {len(advisor_report.quick_wins)}）",
                        "",
                    ]
                )
                if advisor_report.quick_wins:
                    lines.append("### Quick Wins（高收益低成本）")
                    lines.append("")
                    for advice in advisor_report.quick_wins:
                        lines.append(
                            f"- **[{advice.priority.upper()}]** " f"{advice.title}: {advice.action}"
                        )
                    lines.append("")
                if advisor_report.critical_advices:
                    lines.append("### 关键问题（必须修复）")
                    lines.append("")
                    for advice in advisor_report.critical_advices:
                        lines.append(
                            f"- **{advice.title}** ({advice.category}): "
                            f"{advice.description} → {advice.action}"
                        )
                    lines.append("")
                remaining = [
                    a
                    for a in advisor_report.advices
                    if a.priority not in {"critical"}
                    and not (a.impact == "high" and a.effort == "small")
                ]
                if remaining:
                    lines.append("### 其他建议")
                    lines.append("")
                    for advice in remaining:
                        lines.append(
                            f"- [{advice.priority.upper()}] **{advice.title}** "
                            f"({advice.category}): {advice.description} "
                            f"[工作量: {advice.effort}, 影响: {advice.impact}]"
                        )
                    lines.append("")
        except Exception:
            pass

        # 下一步行动
        lines.extend(
            [
                "---",
                "",
                "## 下一步行动",
                "",
            ]
        )

        if self.passed:
            lines.extend(
                [
                    "[通过] 质量门禁已通过，可以继续下一步：",
                    "",
                    "1. 开始编码实现",
                    "2. 设置 CI/CD 流水线",
                    "3. 部署到测试环境",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "[未通过] 质量门禁未通过，请完成以下操作后重新检查：",
                    "",
                ]
            )

            failed_items = [f"- {c.description}" for c in self.failed_checks]
            lines.extend(failed_items)
            lines.extend(
                [
                    "",
                    "修复后运行: `super-dev quality --type all`",
                    "",
                ]
            )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "total_score": self.total_score,
            "weighted_score": self.weighted_score,
            "gate_score": self.gate_score,
            "threshold": self.threshold,
            "critical_failures": list(self.critical_failures),
            "recommendations": list(self.recommendations),
            "scenario": self.scenario,
            "summary": {
                "executive_summary": self.executive_summary,
                "summary_context": dict(self.summary_context),
            },
            "checks": [
                {
                    "name": check.name,
                    "category": check.category,
                    "description": check.description,
                    "status": check.status.value,
                    "score": check.score,
                    "weight": check.weight,
                    "details": check.details,
                }
                for check in self.checks
            ],
        }


class QualityGateChecker(QualityGateEvidenceMixin):
    """质量门禁检查器"""

    # 质量门禁阈值
    PASS_THRESHOLD = 80
    WARNING_THRESHOLD = 60
    # 0-1 场景与增量场景统一使用 80+ 标准
    PASS_THRESHOLD_ZERO_TO_ONE = 80
    HOST_COMPAT_MIN_SCORE = 80
    HOST_COMPAT_MIN_READY_HOSTS = 1

    # 检查项配置
    CHECKS_CONFIG = {
        "documentation": {
            "weight": 1.0,
            "required": True,
        },
        "security": {
            "weight": 1.5,  # 安全更重要
            "required": True,
        },
        "performance": {
            "weight": 1.2,
            "required": True,
        },
        "testing": {
            "weight": 1.3,
            "required": True,
        },
        "code_quality": {
            "weight": 1.0,
            "required": False,
        },
        "accessibility": {
            "weight": 0.8,
            "required": False,
        },
        "ui_quality": {
            "weight": 1.2,
            "required": True,
        },
        "schema_drift": {
            "weight": 0.8,
            "required": False,
        },
        "spec_compliance": {
            "weight": 2.0,
            "required": True,
        },
        "architecture_drift": {
            "weight": 2.5,
            "required": True,
        },
        "uiux_compliance": {
            "weight": 2.0,
            "required": False,
        },
    }

    def __init__(
        self,
        project_dir: Path,
        name: str,
        tech_stack: dict,
        scenario_override: str | None = None,
        threshold_override: int | None = None,
        host_compatibility_min_score_override: int | None = None,
        host_compatibility_min_ready_hosts_override: int | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.name = resolve_current_artifact_prefix(
            self.project_dir,
            configured_name=name,
            fallback_name=self.project_dir.name,
        )
        self.tech_stack = tech_stack
        self.latest_ui_review_report: Any = None
        self.latest_fresh_verification_dependencies: list[Path] = []
        self.threshold_override = threshold_override
        config = ConfigManager(self.project_dir).load()
        self.platform = (
            str(self.tech_stack.get("platform") or config.platform or "").strip().lower()
        )
        self.database = str(config.database or "").strip().lower()
        frontend = str(config.frontend or "").strip().lower()
        self.frontend_required = bool(frontend and frontend != "none")
        self.fresh_verification_required = fresh_verification_required(config)
        self.host_profile_targets = [
            item.strip()
            for item in getattr(config, "host_profile_targets", [])
            if isinstance(item, str) and item.strip()
        ]
        self.host_profile_enforce_selected = bool(
            getattr(config, "host_profile_enforce_selected", False)
        )
        self.host_compatibility_min_score = self._coerce_host_compat_score(
            host_compatibility_min_score_override
            if host_compatibility_min_score_override is not None
            else config.host_compatibility_min_score
        )
        self.host_compatibility_min_ready_hosts = self._coerce_host_compat_ready_hosts(
            host_compatibility_min_ready_hosts_override
            if host_compatibility_min_ready_hosts_override is not None
            else config.host_compatibility_min_ready_hosts
        )
        if scenario_override in {"0-1", "1-N+1"}:
            self.is_zero_to_one = scenario_override == "0-1"
        else:
            self.is_zero_to_one = self._detect_zero_to_one_scenario()

        # 可编程验证规则引擎（加载失败不影响主流程）
        self._rule_engine: ValidationRuleEngine | None = None
        try:
            self._rule_engine = ValidationRuleEngine(Path.cwd())
        except Exception:
            pass

    def _build_review_agent_prompts(self, context: dict) -> dict[str, str] | None:
        """Build parallel review agent prompts for the quality gate."""
        if not REVIEW_AGENTS_AVAILABLE:
            return None
        try:
            prompts: dict[str, str] = build_parallel_review_prompt(
                change_description=context.get("description", ""),
                files_changed=context.get("files_changed", []),
            )
            return prompts
        except Exception:
            return None

    def _coerce_host_compat_score(self, value: object) -> int:
        score = self._coerce_int(value, default=self.HOST_COMPAT_MIN_SCORE)
        return max(0, min(100, score))

    def _coerce_host_compat_ready_hosts(self, value: object) -> int:
        ready_hosts = self._coerce_int(value, default=self.HOST_COMPAT_MIN_READY_HOSTS)
        return max(0, ready_hosts)

    def _coerce_float(self, value: object, default: float) -> float:
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return default
            try:
                return float(text)
            except ValueError:
                return default
        return default

    def _coerce_int(self, value: object, default: int) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return default
            try:
                return int(text)
            except ValueError:
                return default
        return default

    def _detect_zero_to_one_scenario(self) -> bool:
        """
        检测是否为 0-1 场景（空项目/新建项目）

        0-1 场景特征：
        - 没有源代码目录（src/, lib/, app/, server/, client/ 等）
        - 没有配置文件（package.json, requirements.txt, go.mod 等）
        - 只有 output/ 目录（刚生成的文档）

        Returns:
            bool: True 表示 0-1 场景，False 表示 1-N+1 场景
        """
        # 检查常见的源代码目录
        source_dirs = [
            "src",
            "lib",
            "app",
            "server",
            "client",
            "backend",
            "frontend",
            "api",
            "handlers",
            "models",
            "views",
            "controllers",
            "services",
        ]

        has_source_code = any((self.project_dir / d).exists() for d in source_dirs)

        # 检查是否有项目配置文件（表明这不是空项目）
        config_files = [
            "package.json",
            "requirements.txt",
            "go.mod",
            "Cargo.toml",
            "pom.xml",
            "build.gradle",
        ]

        has_project_config = any((self.project_dir / f).exists() for f in config_files)

        # 如果有源代码或有项目配置，说明不是 0-1 场景
        return not (has_source_code or has_project_config)

    def check(self, redteam_report: Optional["RedTeamReport"] = None) -> QualityGateResult:
        """执行质量门禁检查"""
        checks: list[QualityCheck] = []

        # 1. 文档质量检查
        checks.extend(self._check_documentation())

        # 2. 安全检查 (基于红队报告)
        checks.extend(self._check_security(redteam_report))

        # 3. 性能检查 (基于红队报告)
        checks.extend(self._check_performance(redteam_report))

        # 4. 测试检查
        checks.extend(self._check_testing())

        # 5. 代码质量检查
        checks.extend(self._check_code_quality())

        if self.frontend_required:
            # 5.5 无障碍性检查
            checks.extend(self._check_accessibility())

            # 5.6 前端性能预算检查
            checks.extend(self._check_performance_budget())

            # 5.7 UI 契约执行检查
            checks.append(self._check_ui_contract_execution())

            # 6. UI 审查
            checks.append(self._check_ui_review())

        # 7. 执行可编程验证规则
        if self._rule_engine:
            try:
                context = {
                    "project_dir": str(self.project_dir),
                    "name": self.name,
                    "tech_stack": self.tech_stack,
                    "scenario": "0-1" if self.is_zero_to_one else "1-N+1",
                    "frontend_required": self.frontend_required,
                }
                rule_report = self._rule_engine.validate("quality", context)
                for result in rule_report.results:
                    if not result.passed:
                        checks.append(
                            QualityCheck(
                                name=f"Rule: {result.rule_id}",
                                category="validation_rules",
                                description=result.message,
                                status=(
                                    CheckStatus.FAILED
                                    if result.severity == "critical"
                                    else CheckStatus.WARNING
                                ),
                                score=0,
                                weight=1.5 if result.severity == "critical" else 1.0,
                                details=result.fix_suggestion,
                            )
                        )
            except Exception:
                pass

        # 8. 加载专家特定的验证规则（如果专家工具箱可用）
        try:
            from ..experts.toolkit import load_expert_toolkits

            toolkits = load_expert_toolkits()
            for expert_id, toolkit in toolkits.items():
                if hasattr(toolkit, "rules") and hasattr(toolkit.rules, "validation_rule_ids"):
                    for rule_id in toolkit.rules.validation_rule_ids:
                        # 检查该规则是否已在 rule_engine 中注册
                        if self._rule_engine:
                            matching = [r for r in self._rule_engine.rules if r.id == rule_id]
                            if not matching:
                                checks.append(
                                    QualityCheck(
                                        name=f"Expert Rule Gap: {rule_id}",
                                        category="validation_rules",
                                        description=(
                                            f"专家 {expert_id} 声明了规则 {rule_id}，"
                                            f"但该规则不在验证引擎中"
                                        ),
                                        status=CheckStatus.WARNING,
                                        score=50,
                                        weight=0.5,
                                    )
                                )
        except Exception:
            pass

        # 9. 收集外部审查结果 (CodeRabbit / Qodo / GitHub PR / Custom)
        try:
            from .external_reviews import ExternalReviewCollector

            collector = ExternalReviewCollector(self.project_dir)
            external = collector.collect_all()
            for review in external:
                checks.append(
                    QualityCheck(
                        name=f"External Review: {review.source}",
                        category="external_review",
                        description=review.summary,
                        status=(CheckStatus.PASSED if review.passed else CheckStatus.WARNING),
                        score=review.score,
                    )
                )
        except Exception:
            pass

        # 10. 交叉审查协议——多专家规则引擎验证
        try:
            from ..experts.review_protocol import CrossReviewEngine
            from ..experts.toolkit import load_expert_toolkits

            toolkits = load_expert_toolkits()
            review_engine = CrossReviewEngine(toolkits)
            output_dir = self.project_dir / "output"

            if self.frontend_required:
                # 对 UIUX 文档执行交叉审查
                uiux_path = output_dir / f"{self.name}-uiux.md"
                if uiux_path.exists():
                    uiux_content = uiux_path.read_text(encoding="utf-8", errors="replace")
                    cross_report = review_engine.validate_artifact(uiux_content, "docs")
                    for finding in cross_report.findings:
                        if not finding.passed:
                            checks.append(
                                QualityCheck(
                                    name=(
                                        f"Cross-Review: {finding.expert_id} → "
                                        f"{finding.dimension}"
                                    ),
                                    category="cross_review",
                                    description=finding.detail,
                                    status=CheckStatus.WARNING,
                                    score=60,
                                    weight=0.8,
                                )
                            )

            # 对架构文档执行交叉审查
            arch_path = output_dir / f"{self.name}-architecture.md"
            if arch_path.exists():
                arch_content = arch_path.read_text(encoding="utf-8", errors="replace")
                cross_report = review_engine.validate_artifact(arch_content, "docs")
                for finding in cross_report.findings:
                    if not finding.passed:
                        checks.append(
                            QualityCheck(
                                name=f"Cross-Review: {finding.expert_id} → {finding.dimension}",
                                category="cross_review",
                                description=finding.detail,
                                status=CheckStatus.WARNING,
                                score=60,
                                weight=0.8,
                            )
                        )
        except Exception:
            pass

        # 11. 知识推送引擎约束检查
        try:
            from ..orchestrator.knowledge_pusher import KnowledgePusher

            knowledge_dir = self.project_dir / "knowledge"
            if knowledge_dir.is_dir():
                pusher = KnowledgePusher(
                    knowledge_dir=knowledge_dir,
                    tech_stack=self.tech_stack or {},
                )
                kb_constraints, kb_antipatterns = pusher.get_quality_constraints()
                if kb_constraints:
                    checks.append(
                        QualityCheck(
                            name="Knowledge Constraints",
                            category="knowledge_base",
                            description=(
                                f"知识库推送了 {len(kb_constraints)} 条硬约束 "
                                f"和 {len(kb_antipatterns)} 条反模式。"
                                f"请确保已遵守所有约束。"
                            ),
                            status=CheckStatus.PASSED,
                            score=80,
                            weight=0.8,
                            details="; ".join(kb_constraints[:5]),
                        )
                    )
                if kb_antipatterns:
                    checks.append(
                        QualityCheck(
                            name="Knowledge Anti-patterns",
                            category="knowledge_base",
                            description=(
                                f"知识库包含 {len(kb_antipatterns)} 条反模式警告，"
                                f"需确认项目未触犯。"
                            ),
                            status=CheckStatus.WARNING,
                            score=70,
                            weight=0.6,
                            details="; ".join(kb_antipatterns[:5]),
                        )
                    )
        except Exception:
            pass

        # 12. 规范/架构/UIUX 合规检查
        checks.extend(self._check_compliance_artifacts())

        # 计算总分和加权分
        total_score = self._calculate_total_score(checks)
        weighted_score = self._calculate_weighted_score(checks)

        # 根据场景选择阈值
        threshold = (
            self.threshold_override
            if self.threshold_override is not None
            else (self.PASS_THRESHOLD_ZERO_TO_ONE if self.is_zero_to_one else self.PASS_THRESHOLD)
        )

        # 收集关键失败项
        critical_failures = []
        for check in checks:
            config = self.CHECKS_CONFIG.get(check.category, {})
            if config.get("required", False) and check.status == CheckStatus.FAILED:
                critical_failures.append(f"[{check.category}] {check.description}")

        # 检查是否通过：加权分必须达到阈值，且必检项不能失败。
        # CHECKS_CONFIG 为高风险维度声明了更高权重；门禁判定必须与该模型一致。
        passed = weighted_score >= threshold and not critical_failures

        # Webhook notification on quality gate failure
        if not passed:
            try:
                from ..webhooks import send_webhook

                send_webhook(
                    "quality_fail",
                    {
                        "score": weighted_score,
                        "threshold": threshold,
                        "critical_failures": critical_failures,
                        "scenario": "0-1" if self.is_zero_to_one else "1-N+1",
                        "project": self.name,
                    },
                )
            except Exception:
                pass

        # 生成改进建议
        recommendations = self._generate_recommendations(checks)
        host_runtime_layered_gap = self._host_runtime_layered_gap_summary()
        workflow_signal_summary = self._workflow_signal_summary()
        baseline_signal_summary = self._baseline_signal_summary()

        # 确定场景类型
        scenario = "0-1" if self.is_zero_to_one else "1-N+1"

        return QualityGateResult(
            passed=passed,
            total_score=total_score,
            weighted_score=weighted_score,
            checks=checks,
            critical_failures=critical_failures,
            recommendations=recommendations,
            scenario=scenario,
            threshold=float(threshold),
            summary_context={
                "workflow_signal_summary": workflow_signal_summary,
                "baseline_signal_summary": baseline_signal_summary,
                "host_runtime_layered_gap": host_runtime_layered_gap,
                "compliance_signal_summary": self._compliance_signal_summary(checks),
            },
        )

    def _workflow_signal_summary(self) -> str:
        context = build_host_workflow_context(self.project_dir)
        status = str(context.get("workflow_status", "")).strip()
        gate = str(context.get("blocking_gate", "")).strip()
        next_action = str(context.get("recommended_host_action", "")).strip()
        if not status:
            return ""
        if gate:
            action_text = f" 下一步：{next_action}。" if next_action else ""
            return f" 当前流程状态为 {status}，入口 gate={gate}。{action_text}"
        return f" 当前流程状态为 {status}，主入口 gate 已闭环。"

    def _baseline_signal_summary(self) -> str:
        baseline = inspect_baseline_governance(self.project_dir)
        status = str(baseline.get("status", "")).strip()
        entry_gate = str(baseline.get("entry_gate", "")).strip()
        next_action = str(baseline.get("next_host_action", "")).strip()
        if status == "missing_audit":
            return " 当前是已有项目模式，但 baseline audit 还没生成。"
        if entry_gate == "waiting_baseline_confirmation":
            action_text = f" 下一步：{next_action}。" if next_action else ""
            return " 当前是已有项目模式，但 baseline 还没确认。" + action_text
        if entry_gate == "waiting_resume_gate":
            action_text = f" 下一步：{next_action}。" if next_action else ""
            return " 当前先处理 resume gate，再继续已有项目差量链路。" + action_text
        return ""

    def _host_runtime_layered_gap_summary(self) -> str:
        governance_gap = collect_layered_runtime_governance_gap(self.project_dir)
        summary = str(governance_gap.get("summary", "")).strip() if governance_gap else ""
        if not summary:
            return ""
        impacted_hosts = governance_gap.get("impacted_hosts", [])
        if isinstance(impacted_hosts, list) and impacted_hosts:
            return (
                " 宿主验收存在分层差异："
                + "、".join(str(item) for item in impacted_hosts[:3])
                + " 已人工通过，但仓库级 continuity / harness / runtime 证据仍未闭环。"
            )
        return f" {summary}。"

    def _compliance_signal_summary(self, checks: list[QualityCheck]) -> str:
        compliance_checks = [
            check
            for check in checks
            if check.category in {"spec_compliance", "architecture_drift", "uiux_compliance"}
        ]
        if not compliance_checks:
            return ""
        source_issues: list[str] = []
        content_issues: list[str] = []
        for check in compliance_checks:
            match = re.search(r"Source:\s*([a-z_]+)", check.description)
            source_state = match.group(1) if match else ""
            if source_state and source_state != "ready":
                source_issues.append(f"{check.name}={source_state}")
            if check.status != CheckStatus.PASSED:
                content_issues.append(check.name)
        if source_issues:
            return " 合规链当前优先卡在证据状态：" + "、".join(source_issues[:3]) + "。"
        if content_issues:
            return " 合规链证据已齐，但内容仍未达标：" + "、".join(content_issues[:3]) + "。"
        return " 合规链证据与内容检查当前均已闭环。"

    def _check_compliance_artifacts(self) -> list[QualityCheck]:
        checks: list[QualityCheck] = []
        output_dir = self.project_dir / "output"

        try:
            from .spec_compliance import inspect_spec_compliance_artifact, run_spec_compliance

            inspection = inspect_spec_compliance_artifact(self.project_dir, output_dir)
            spec_report = run_spec_compliance(self.project_dir, output_dir)
            if spec_report.total_requirements > 0:
                score = spec_report.score
                status = (
                    CheckStatus.PASSED
                    if score >= 80
                    else (CheckStatus.WARNING if score >= 50 else CheckStatus.FAILED)
                )
                checks.append(
                    QualityCheck(
                        name="Spec Compliance (Requirement Traceability)",
                        category="spec_compliance",
                        description=(
                            f"Source: {inspection['status']}; "
                            f"Coverage: {spec_report.coverage_percent}% "
                            f"({spec_report.total_requirements} requirements)"
                        ),
                        status=status,
                        score=score,
                        weight=2.0,
                    )
                )
        except Exception:
            pass

        try:
            from .architecture_drift import (
                inspect_architecture_drift_artifact,
                run_architecture_drift,
            )

            inspection = inspect_architecture_drift_artifact(self.project_dir, output_dir)
            architecture_report = run_architecture_drift(self.project_dir, output_dir)
            if architecture_report.total_drifts > 0 or architecture_report.declared_tech_stack:
                score = architecture_report.score
                status = (
                    CheckStatus.PASSED
                    if score >= 80
                    else (CheckStatus.WARNING if score >= 50 else CheckStatus.FAILED)
                )
                checks.append(
                    QualityCheck(
                        name="Architecture Drift Detection",
                        category="architecture_drift",
                        description=(
                            f"Source: {inspection['status']}; "
                            f"Drifts: {architecture_report.total_drifts} "
                            f"(Critical: {architecture_report.critical_count})"
                        ),
                        status=status,
                        score=score,
                        weight=2.5,
                    )
                )
        except Exception:
            pass

        if self.frontend_required:
            try:
                from .uiux_compliance import (
                    inspect_uiux_compliance_artifact,
                    run_uiux_compliance,
                )

                inspection = inspect_uiux_compliance_artifact(self.project_dir, output_dir)
                uiux_report = run_uiux_compliance(self.project_dir, output_dir)
                if uiux_report.files_scanned > 0:
                    score = uiux_report.score
                    status = (
                        CheckStatus.PASSED
                        if score >= 80
                        else (CheckStatus.WARNING if score >= 50 else CheckStatus.FAILED)
                    )
                    checks.append(
                        QualityCheck(
                            name="UIUX Compliance (Icon/Token/Typography)",
                            category="uiux_compliance",
                            description=(
                                f"Source: {inspection['status']}; "
                                f"Violations: {uiux_report.total_violations} "
                                f"across {uiux_report.files_scanned} files"
                            ),
                            status=status,
                            score=score,
                            weight=2.0,
                        )
                    )
            except Exception:
                pass

        return checks

    # ------------------------------------------------------------------
    # 文档内容深度检查（防止空壳文档自动满分）
    # ------------------------------------------------------------------

    # 各文档类型的最低非空行数
    _DOC_MIN_LINES: dict[str, int] = {"prd": 100, "architecture": 80, "uiux": 80}
    # 各文档类型的最低二级标题数
    _DOC_MIN_SECTIONS: dict[str, int] = {"prd": 5, "architecture": 4, "uiux": 4}

    def _check_document_depth(self, content: str, doc_type: str) -> tuple[int, list[str]]:
        """检查文档内容深度，而非仅检查关键词存在。

        Returns:
            (扣分后的得分 0-100, 问题列表)
        """
        issues: list[str] = []
        score = 100

        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # 1. 最小行数要求
        min_lines = self._DOC_MIN_LINES.get(doc_type, 50)
        if len(non_empty_lines) < min_lines:
            score -= 30
            issues.append(
                f"{doc_type} 文档内容过短 ({len(non_empty_lines)} 行，最低要求 {min_lines} 行)"
            )

        # 2. 章节数量要求（## 标题）
        h2_count = sum(1 for line in lines if line.startswith("## "))
        min_sections = self._DOC_MIN_SECTIONS.get(doc_type, 3)
        if h2_count < min_sections:
            score -= 20
            issues.append(
                f"{doc_type} 文档章节不足 ({h2_count} 个二级标题，最低要求 {min_sections} 个)"
            )

        # 3. 架构文档必须包含代码/配置示例
        if doc_type == "architecture":
            code_blocks = content.count("```")
            if code_blocks < 2:
                score -= 15
                issues.append("架构文档缺少代码/配置示例")

        # 4. PRD 必须包含验收标准
        if doc_type == "prd":
            has_acceptance_detail = (
                "Given" in content
                or "When" in content
                or "验收标准" in content
                or "acceptance criteria" in content.lower()
            )
            if not has_acceptance_detail:
                score -= 15
                issues.append("PRD 缺少验收标准（Given-When-Then 或明确的验收条件）")

        # 5. UIUX 必须包含 Design Token 定义
        if doc_type == "uiux" and self.frontend_required:
            token_keywords = ["color", "font", "spacing", "token", "颜色", "字体", "间距"]
            token_hits = sum(1 for kw in token_keywords if kw in content.lower())
            if token_hits < 3:
                score -= 20
                issues.append("UIUX 文档缺少设计 Token 定义（颜色/字体/间距）")

            # 反模式规则
            has_antipattern_rules = (
                "emoji" in content.lower()
                or "渐变" in content
                or "anti-pattern" in content.lower()
                or "反模式" in content
            )
            if not has_antipattern_rules:
                score -= 10
                issues.append("UIUX 文档缺少 UI 反模式红线规则")

        return max(score, 0), issues

    def _check_documentation(self) -> list[QualityCheck]:
        """检查文档质量"""
        checks = []

        # 0-1 场景下文档是唯一可检查的产物，权重加倍
        doc_weight = self.CHECKS_CONFIG["documentation"]["weight"]
        if self.is_zero_to_one:
            doc_weight *= 2.0

        # 检查 PRD 是否存在
        prd_path = self.project_dir / "output" / f"{self.name}-prd.md"
        if prd_path.exists():
            content = prd_path.read_text(encoding="utf-8", errors="ignore")
            # 关键词存在性（基础分）
            has_vision = "产品愿景" in content or "vision" in content.lower()
            has_features = "功能需求" in content or "features" in content.lower()
            has_acceptance = "验收标准" in content or "acceptance" in content.lower()

            keyword_score = 100 if has_vision and has_features and has_acceptance else 70

            # 内容深度检查
            depth_score, depth_issues = self._check_document_depth(content, "prd")

            # 综合评分：关键词 40% + 深度 60%
            score = int(keyword_score * 0.4 + depth_score * 0.6)
            detail_parts = []
            if has_vision and has_features and has_acceptance:
                detail_parts.append("包含产品愿景、功能需求和验收标准")
            else:
                detail_parts.append("缺少关键章节（产品愿景/功能需求/验收标准）")
            detail_parts.extend(depth_issues)

            status = (
                CheckStatus.PASSED
                if score >= 80
                else CheckStatus.WARNING if score >= 60 else CheckStatus.FAILED
            )

            checks.append(
                QualityCheck(
                    name="PRD 文档",
                    category="documentation",
                    description="产品需求文档完整性",
                    status=status,
                    score=score,
                    weight=doc_weight,
                    details="; ".join(detail_parts),
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="PRD 文档",
                    category="documentation",
                    description="产品需求文档存在性",
                    status=CheckStatus.FAILED,
                    score=0,
                    weight=doc_weight,
                    details="PRD 文档不存在",
                )
            )

        # 检查架构文档是否存在
        arch_path = self.project_dir / "output" / f"{self.name}-architecture.md"
        if arch_path.exists():
            content = arch_path.read_text(encoding="utf-8", errors="ignore")
            has_tech_stack = "技术栈" in content or "tech stack" in content.lower()
            has_database = "数据库" in content or "database" in content.lower()
            has_api = "API" in content

            keyword_score = 100 if has_tech_stack and has_database and has_api else 70

            # 内容深度检查
            depth_score, depth_issues = self._check_document_depth(content, "architecture")

            # 综合评分：关键词 40% + 深度 60%
            score = int(keyword_score * 0.4 + depth_score * 0.6)
            detail_parts = []
            if has_tech_stack and has_database and has_api:
                detail_parts.append("包含技术栈、数据库设计和 API 设计")
            else:
                detail_parts.append("缺少关键章节（技术栈/数据库/API）")
            detail_parts.extend(depth_issues)

            status = (
                CheckStatus.PASSED
                if score >= 80
                else CheckStatus.WARNING if score >= 60 else CheckStatus.FAILED
            )

            checks.append(
                QualityCheck(
                    name="架构文档",
                    category="documentation",
                    description="架构设计文档完整性",
                    status=status,
                    score=score,
                    weight=doc_weight,
                    details="; ".join(detail_parts),
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="架构文档",
                    category="documentation",
                    description="架构设计文档存在性",
                    status=CheckStatus.FAILED,
                    score=0,
                    weight=doc_weight,
                    details="架构文档不存在",
                )
            )

        # 前端项目检查 UI/UX；无前端项目保留同一核心文件作为使用体验文档。
        uiux_path = self.project_dir / "output" / f"{self.name}-uiux.md"
        if uiux_path.exists():
            content = uiux_path.read_text(encoding="utf-8", errors="ignore")

            # 内容深度检查
            depth_score, depth_issues = self._check_document_depth(content, "uiux")

            detail_parts = []
            if depth_score >= 80:
                detail_parts.append("UI/UX 文档内容充实")
            else:
                detail_parts.append("UI/UX 文档内容深度不足")
            detail_parts.extend(depth_issues)

            status = (
                CheckStatus.PASSED
                if depth_score >= 80
                else CheckStatus.WARNING if depth_score >= 60 else CheckStatus.FAILED
            )

            checks.append(
                QualityCheck(
                    name="UI/UX 文档" if self.frontend_required else "使用体验文档",
                    category="documentation",
                    description=(
                        "UI/UX 设计文档完整性"
                        if self.frontend_required
                        else "无前端项目的使用体验文档完整性"
                    ),
                    status=status,
                    score=depth_score,
                    weight=doc_weight,
                    details="; ".join(detail_parts),
                )
            )
        else:
            checks.append(
                QualityCheck(
                    name="UI/UX 文档" if self.frontend_required else "使用体验文档",
                    category="documentation",
                    description=(
                        "UI/UX 设计文档存在性"
                        if self.frontend_required
                        else "无前端项目的使用体验文档存在性"
                    ),
                    status=CheckStatus.FAILED,
                    score=0,
                    weight=doc_weight,
                    details=(
                        "UI/UX 文档不存在（必需）"
                        if self.frontend_required
                        else "使用体验文档不存在（核心文档必需）"
                    ),
                )
            )

        checks.append(
            self._check_document_consistency(
                prd_path=prd_path, arch_path=arch_path, uiux_path=uiux_path
            )
        )

        return checks

    def _check_document_consistency(
        self, *, prd_path: Path, arch_path: Path, uiux_path: Path
    ) -> QualityCheck:
        if resolve_active_change_id(self.project_dir):
            gate = docs_gate_status(self.project_dir)
            confirmed = bool(gate.get("confirmed", False))
            binding_matches = bool(gate.get("binding_matches_current", False))
            core_complete = bool(gate.get("core_complete", False))
            binding = gate.get("artifact_binding", {})
            file_count = int(binding.get("file_count", 0) or 0) if isinstance(binding, dict) else 0
            detail = (
                f"当前文档绑定: files={file_count}, status={gate.get('status')}, "
                f"binding_matches_current={binding_matches}, core_complete={core_complete}"
            )
            return QualityCheck(
                name="三文档一致性",
                category="documentation",
                description="当前 PRD/Architecture/使用体验文档绑定与确认状态",
                status=CheckStatus.PASSED if confirmed else CheckStatus.FAILED,
                score=100 if confirmed else 0,
                weight=self.CHECKS_CONFIG["documentation"]["weight"],
                details=detail,
            )

        if not (prd_path.exists() and arch_path.exists() and uiux_path.exists()):
            return QualityCheck(
                name="三文档一致性",
                category="documentation",
                description="PRD/Architecture/UIUX 决策与证据闭环",
                status=CheckStatus.WARNING,
                score=60,
                weight=self.CHECKS_CONFIG["documentation"]["weight"],
                details="三文档未全部存在，无法进行一致性检查",
            )

        prd_content = prd_path.read_text(encoding="utf-8", errors="ignore")
        arch_content = arch_path.read_text(encoding="utf-8", errors="ignore")
        uiux_content = uiux_path.read_text(encoding="utf-8", errors="ignore")
        requirements = [
            ("PRD 证据章节", "联网研究证据与方案对比" in prd_content),
            ("PRD 决策账本", "关键决策账本" in prd_content),
            ("PRD 用户统一协议", "用户到专业交付统一协议" in prd_content),
            ("架构证据链", "架构选型取舍与证据链" in arch_content),
            ("架构决策账本", "架构决策账本" in arch_content),
            ("架构全端流水线", "Agent 执行流水线（全端）" in arch_content),
        ]
        if self.frontend_required:
            requirements.extend(
                [
                    ("UI 多端策略", "多端适配与平台化设计策略" in uiux_content),
                    ("UI 质量门禁", "商业级设计质量门禁" in uiux_content),
                    (
                        "UI 五端覆盖",
                        all(
                            term in uiux_content
                            for term in ("WEB", "H5", "微信小程序", "APP", "桌面端")
                        ),
                    ),
                    (
                        "UI 风格决策冻结",
                        all(
                            term in uiux_content
                            for term in ("主视觉气质", "字体组合", "配色逻辑", "图标系统")
                        ),
                    ),
                    (
                        "UI 备选与取舍",
                        ("备选实现路径" in uiux_content or "可选备选方案" in uiux_content)
                        and (
                            "明确不默认采用" in uiux_content or "明确不建议默认采用" in uiux_content
                        ),
                    ),
                    (
                        "UI Token 冻结输出",
                        "Design Token 冻结输出" in uiux_content or "Token 冻结输出" in uiux_content,
                    ),
                    (
                        "UI 双方案约束",
                        "2 个视觉方向候选" in uiux_content or "主方案 + 备选方案" in uiux_content,
                    ),
                ]
            )
        else:
            requirements.append(("使用体验文档", bool(uiux_content.strip())))
        passed_count = sum(1 for _, ok in requirements if ok)
        total = len(requirements)
        missing = [name for name, ok in requirements if not ok]
        score = int((passed_count / total) * 100) if total else 100
        if self.frontend_required and "UI 五端覆盖" in missing:
            status = CheckStatus.FAILED
            score = min(score, 59)
        elif score >= 85:
            status = CheckStatus.PASSED
        elif score >= 60:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.FAILED
        detail = f"命中 {passed_count}/{total}"
        if missing:
            detail += f"，缺失: {', '.join(missing)}"
        return QualityCheck(
            name="三文档一致性",
            category="documentation",
            description="PRD/Architecture/UIUX 决策与证据闭环",
            status=status,
            score=score,
            weight=self.CHECKS_CONFIG["documentation"]["weight"],
            details=detail,
        )

    def _check_accessibility(self) -> list[QualityCheck]:
        """检查前端无障碍性（A11y / WCAG 2.1）"""
        checks: list[QualityCheck] = []

        # 扫描前端源文件
        source_dirs = ["frontend", "src", "app", "client", "pages", "components"]
        extensions = {".html", ".tsx", ".jsx", ".vue", ".svelte"}
        skip_dirs = {"node_modules", ".git", "dist", "build", "__pycache__", ".next", ".nuxt"}

        files_scanned = 0
        issues: dict[str, int] = {
            "missing_alt": 0,
            "missing_label": 0,
            "click_no_keyboard": 0,
            "div_click_handler": 0,
        }
        has_landmarks = False

        for src_dir_name in source_dirs:
            src_dir = self.project_dir / src_dir_name
            if not src_dir.exists():
                continue
            for file_path in src_dir.rglob("*"):
                if file_path.suffix not in extensions:
                    continue
                if any(skip in file_path.parts for skip in skip_dirs):
                    continue
                files_scanned += 1
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                # 检查图片是否缺少 alt 属性
                img_tags = re.findall(r"<img\b[^>]*>", content, re.IGNORECASE)
                for tag in img_tags:
                    if "alt=" not in tag.lower() and "alt =" not in tag.lower():
                        issues["missing_alt"] += 1

                # 检查输入框是否缺少 label 关联
                input_tags = re.findall(r"<input\b[^>]*>", content, re.IGNORECASE)
                for tag in input_tags:
                    tag_lower = tag.lower()
                    if (
                        "aria-label" not in tag_lower
                        and "aria-labelledby" not in tag_lower
                        and "id=" not in tag_lower
                    ):
                        issues["missing_label"] += 1

                # 检查 onClick 是否缺少键盘事件处理
                onclick_count = len(re.findall(r"onClick\s*[={]", content))
                keyboard_count = len(
                    re.findall(
                        r"on(?:Key(?:Down|Up|Press)|keydown|keyup|keypress)\s*[={]",
                        content,
                    )
                )
                if onclick_count > keyboard_count:
                    issues["click_no_keyboard"] += onclick_count - keyboard_count

                # 检查 div 是否使用了 click handler（应使用 button）
                div_clicks = len(re.findall(r"<div\b[^>]*onClick", content))
                issues["div_click_handler"] += div_clicks

                # 检查 ARIA landmarks 或语义化标签
                if re.search(r"(?:role\s*=|<(?:main|nav|header|footer|aside)\b)", content):
                    has_landmarks = True

        if files_scanned == 0:
            checks.append(
                QualityCheck(
                    name="无障碍性检查",
                    category="accessibility",
                    description="前端文件无障碍性 (WCAG 2.1)",
                    status=CheckStatus.WARNING,
                    score=80,
                    weight=0.8,
                    details="未找到前端源文件，跳过无障碍性检查",
                )
            )
            return checks

        score = 100
        details_parts: list[str] = []

        if issues["missing_alt"] > 0:
            score -= 15
            details_parts.append(f"发现 {issues['missing_alt']} 个 <img> 缺少 alt 属性")

        if issues["missing_label"] > 0:
            score -= 15
            details_parts.append(f"发现 {issues['missing_label']} 个 <input> 缺少 label/aria-label")

        if issues["click_no_keyboard"] > 0:
            score -= 15
            details_parts.append(f"发现 {issues['click_no_keyboard']} 个 onClick 缺少键盘事件处理")

        if issues["div_click_handler"] > 0:
            score -= 15
            details_parts.append(
                f"发现 {issues['div_click_handler']} 个 <div> 使用 onClick（应使用 <button>）"
            )

        if not has_landmarks:
            score -= 10
            details_parts.append("未检测到 ARIA landmarks 或语义化标签")

        score = max(0, score)

        if score >= 80:
            status = CheckStatus.PASSED
        elif score >= 60:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.FAILED

        details = "; ".join(details_parts) if details_parts else "无障碍性检查通过"

        checks.append(
            QualityCheck(
                name="无障碍性检查",
                category="accessibility",
                description="前端文件无障碍性 (WCAG 2.1)",
                status=status,
                score=score,
                weight=0.8,
                details=f"扫描 {files_scanned} 个文件 - {details}",
            )
        )

        return checks

    def _check_performance_budget(self) -> list[QualityCheck]:
        """检查性能预算（bundle size、依赖数量）"""
        checks: list[QualityCheck] = []
        score = 100
        details_parts: list[str] = []

        # 检查前端 bundle 产物大小
        dist_dirs = ["dist", "build", ".next", ".output", "out"]
        total_bundle_kb = 0.0
        bundle_dir_found = False

        for dist_name in dist_dirs:
            dist_dir = self.project_dir / "frontend" / dist_name
            if not dist_dir.exists():
                dist_dir = self.project_dir / dist_name
            if not dist_dir.exists():
                continue
            bundle_dir_found = True
            for f in dist_dir.rglob("*"):
                if f.is_file() and f.suffix in {".js", ".css", ".mjs"}:
                    total_bundle_kb += f.stat().st_size / 1024

        if bundle_dir_found:
            if total_bundle_kb > 2048:  # > 2MB
                score -= 25
                details_parts.append(f"前端 bundle 总量 {total_bundle_kb:.0f}KB（超过 2MB 预算）")
            elif total_bundle_kb > 1024:  # > 1MB
                score -= 10
                details_parts.append(f"前端 bundle 总量 {total_bundle_kb:.0f}KB（接近 1MB 预算）")
            else:
                details_parts.append(f"前端 bundle 总量 {total_bundle_kb:.0f}KB（在预算内）")

        # 检查 npm 依赖数量
        pkg_json = self.project_dir / "frontend" / "package.json"
        if not pkg_json.exists():
            pkg_json = self.project_dir / "package.json"

        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                dep_count = len(pkg.get("dependencies", {}))

                if dep_count > 40:
                    score -= 15
                    details_parts.append(f"生产依赖 {dep_count} 个（超过 40 个上限）")
                elif dep_count > 25:
                    score -= 5
                    details_parts.append(f"生产依赖 {dep_count} 个（较多）")
                else:
                    details_parts.append(f"生产依赖 {dep_count} 个")
            except (json.JSONDecodeError, OSError):
                pass

        # 检查大文件（潜在性能问题）
        large_files = 0
        for src_dir_name in ["frontend/src", "src", "app"]:
            src_dir = self.project_dir / src_dir_name
            if not src_dir.exists():
                continue
            for f in src_dir.rglob("*"):
                if (
                    f.is_file()
                    and f.suffix in {".ts", ".tsx", ".js", ".jsx", ".vue"}
                    and f.stat().st_size > 50 * 1024
                ):
                    large_files += 1

        if large_files > 0:
            score -= min(15, large_files * 5)
            details_parts.append(f"{large_files} 个前端文件超过 50KB（影响代码分割）")

        score = max(0, score)

        if score >= 80:
            status = CheckStatus.PASSED
        elif score >= 60:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.FAILED

        details = "; ".join(details_parts) if details_parts else "未检测到前端构建产物"

        checks.append(
            QualityCheck(
                name="性能预算检查",
                category="performance",
                description="前端性能预算（bundle size、依赖数量）",
                status=status,
                score=score,
                weight=1.0,
                details=details,
            )
        )

        return checks
