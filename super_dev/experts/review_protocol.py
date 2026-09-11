"""
交叉审查协议引擎 (Cross-Review Protocol Engine)
实现专家之间的交叉审查矩阵，生成结构化的多专家审查报告。

核心能力：
  1. 审查矩阵——自动从 ExpertToolkit.protocol 中提取 reviews/reviewed_by 关系
  2. 多专家审查 Prompt 生成——将当前阶段所有激活专家的检查清单合并为结构化指令
  3. 规则引擎验证——不调用模型，用关键词/模式匹配检查交付物

开发：Excellent（11964948@qq.com）
创建时间：2026-03-28
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .toolkit import (
    ExpertToolkit,
    get_active_toolkits_for_phase,
    get_all_toolkits,
)

# ===================================================================
# 数据结构
# ===================================================================


@dataclass
class ReviewFinding:
    """单条审查发现。"""

    expert_id: str
    """发现者（专家角色 ID）"""

    dimension: str
    """审查维度名称"""

    item: str
    """检查项描述"""

    passed: bool
    """是否通过"""

    detail: str = ""
    """补充说明"""


@dataclass
class CrossReviewReport:
    """交叉审查汇总报告。"""

    phase: str
    """审查阶段"""

    artifact_type: str
    """交付物类型（prd / architecture / uiux / code / ...）"""

    findings: list[ReviewFinding] = field(default_factory=list)
    """全部审查发现"""

    @property
    def passed_count(self) -> int:
        return sum(1 for f in self.findings if f.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for f in self.findings if not f.passed)

    @property
    def total_count(self) -> int:
        return len(self.findings)

    @property
    def pass_rate(self) -> float:
        if not self.findings:
            return 0.0
        return self.passed_count / self.total_count * 100

    @property
    def overall_passed(self) -> bool:
        """无失败项时视为通过。"""
        return self.failed_count == 0

    def to_markdown(self) -> str:
        """渲染为 Markdown 报告。"""
        lines: list[str] = [
            f"# 交叉审查报告 — {self.phase} / {self.artifact_type}",
            "",
            f"- 总检查项: {self.total_count}",
            f"- 通过: {self.passed_count}",
            f"- 未通过: {self.failed_count}",
            f"- 通过率: {self.pass_rate:.1f}%",
            f"- 总体结论: {'PASS' if self.overall_passed else 'FAIL'}",
            "",
        ]

        if self.findings:
            lines.append("## 详细发现")
            lines.append("")
            lines.append("| 专家 | 维度 | 检查项 | 结果 | 说明 |")
            lines.append("|------|------|--------|------|------|")
            for f in self.findings:
                status = "PASS" if f.passed else "FAIL"
                lines.append(
                    f"| {f.expert_id} | {f.dimension} | {f.item} | {status} | {f.detail} |"
                )
            lines.append("")

        return "\n".join(lines)


# ===================================================================
# 交叉审查引擎
# ===================================================================


class CrossReviewEngine:
    """交叉审查引擎——编排多专家对同一交付物的结构化审查。

    引擎本身 **不调用模型**，而是：
      - 生成可注入宿主的多专家审查 Prompt
      - 用规则引擎（关键词 + 正则）对交付物做基本合规检查
    """

    def __init__(self, toolkits: dict[str, ExpertToolkit] | None = None):
        self.toolkits: dict[str, ExpertToolkit] = toolkits or get_all_toolkits()

    # ------------------------------------------------------------------
    # 审查矩阵
    # ------------------------------------------------------------------

    def get_review_matrix(self) -> dict[str, dict[str, list[str]]]:
        """获取完整的交叉审查矩阵。

        Returns:
            形如 ``{expert_id: {"reviews": [...], "reviewed_by": [...]}}`` 的字典。
        """
        matrix: dict[str, dict[str, list[str]]] = {}
        for role, tk in self.toolkits.items():
            matrix[role] = {
                "reviews": list(tk.protocol.reviews_output_of),
                "reviewed_by": list(tk.protocol.reviewed_by),
            }
        return matrix

    def get_reviewers_for(self, target_expert: str) -> list[str]:
        """获取审查指定专家输出的所有审查者。

        Args:
            target_expert: 被审查的专家角色 ID。

        Returns:
            审查者角色 ID 列表。
        """
        reviewers: list[str] = []
        for role, tk in self.toolkits.items():
            if target_expert in tk.protocol.reviews_output_of:
                reviewers.append(role)
        # 加上该专家自己声明的 reviewed_by
        target_tk = self.toolkits.get(target_expert)
        if target_tk:
            for rb in target_tk.protocol.reviewed_by:
                if rb not in reviewers:
                    reviewers.append(rb)
        return reviewers

    # ------------------------------------------------------------------
    # Prompt 生成
    # ------------------------------------------------------------------

    def generate_review_prompt(self, phase: str, artifact_type: str) -> str:
        """生成多专家审查 Prompt（注入宿主）。

        将当前阶段所有激活专家的系统指令和检查清单合并为一个结构化的审查指令块。

        Args:
            phase: 当前阶段名。
            artifact_type: 交付物类型描述。

        Returns:
            可直接注入 Prompt 的多专家审查指令文本。
        """
        active = get_active_toolkits_for_phase(phase)
        if not active:
            return ""

        lines: list[str] = [
            f"# 多专家交叉审查指令 — {phase} / {artifact_type}",
            "",
            f"以下 {len(active)} 类专业视角提供本阶段的候选检查项。",
            "先按本轮范围选择适用项，同一宿主切换角色不代表独立评审已完成。",
            "只读审查报告具体发现及依据，修复和外部操作遵循已有授权。",
            "示例阈值不覆盖项目配置，文件或关键词存在不能证明内容正确。",
            "",
        ]

        for role, tk in active.items():
            lines.append(f"## {tk.name}（{role}）")
            lines.append("")
            lines.append(tk.get_prompt_injection(phase))
            lines.append("")

            checklist = tk.get_review_checklist(phase)
            if checklist:
                lines.append("**检查清单：**")
                for idx, item in enumerate(checklist, 1):
                    lines.append(f"  {idx}. {item}")
                lines.append("")

        # 交叉审查关系提示
        lines.append("## 交叉审查关系")
        lines.append("")
        for role, tk in active.items():
            targets = tk.protocol.reviews_output_of
            if targets:
                target_names = ", ".join(targets)
                lines.append(f"- **{role}** 需审查 {target_names} 的输出")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 规则引擎验证
    # ------------------------------------------------------------------

    def validate_artifact(
        self,
        artifact_content: str,
        phase: str,
        artifact_type: str = "",
    ) -> CrossReviewReport:
        """用多个专家视角验证一个交付物。

        **不调用模型**，使用关键词/正则规则引擎检查。

        Args:
            artifact_content: 交付物文本内容。
            phase: 当前阶段。
            artifact_type: 交付物类型（可选，用于报告标注）。

        Returns:
            :class:`CrossReviewReport` 实例。
        """
        report = CrossReviewReport(phase=phase, artifact_type=artifact_type or phase)
        active = get_active_toolkits_for_phase(phase)

        for role, tk in active.items():
            for dim in tk.protocol.review_dimensions:
                dimension_name = str(dim.get("dimension", ""))
                checklist = dim.get("checklist", [])
                if not isinstance(checklist, list):
                    continue
                for item in checklist:
                    if not isinstance(item, str):
                        continue
                    passed, detail = self._check_item(artifact_content, item)
                    report.findings.append(
                        ReviewFinding(
                            expert_id=role,
                            dimension=dimension_name,
                            item=item,
                            passed=passed,
                            detail=detail,
                        )
                    )

        return report

    # ------------------------------------------------------------------
    # 内部：关键词规则引擎
    # ------------------------------------------------------------------

    # 检查项关键词映射：检查项文本片段 -> 交付物中应出现的关键词列表
    _KEYWORD_RULES: dict[str, list[str]] = {
        "OWASP": ["OWASP", "owasp", "安全"],
        "认证授权": ["认证", "授权", "auth", "JWT", "OAuth", "token"],
        "输入验证": ["输入验证", "校验", "validation", "sanitize"],
        "加密": ["加密", "encrypt", "TLS", "HTTPS", "hash"],
        "漏洞": ["漏洞", "CVE", "vulnerability", "依赖扫描", "audit"],
        "ADR": ["ADR", "架构决策", "decision record"],
        "RESTful": ["REST", "API", "端点", "endpoint"],
        "数据流": ["数据流", "data flow", "流图", "序列图"],
        "扩展性": ["扩展", "scaling", "弹性", "水平扩展", "分片"],
        "Token 体系": ["token", "Token", "设计变量", "色彩", "间距", "字体"],
        "组件状态": ["hover", "focus", "loading", "empty", "error", "disabled", "状态"],
        "AI 模板": ["紫色渐变", "emoji 图标", "模板化"],
        "信息层级": ["层级", "hierarchy", "权重", "视觉重量"],
        "N+1": ["N+1", "n+1", "预加载", "eager", "批量查询"],
        "ER 图": ["ER 图", "ER图", "实体关系", "entity"],
        "索引": ["索引", "index", "INDEX"],
        "回滚": ["回滚", "rollback", "ROLLBACK"],
        "质量门禁": ["质量门禁", "quality gate", "质量分"],
        "测试覆盖": ["测试覆盖", "coverage", "覆盖率"],
        "CI/CD": ["CI/CD", "ci/cd", "GitHub Actions", "流水线", "pipeline"],
        "Docker": ["Docker", "docker", "容器", "container"],
        "健康检查": ["健康检查", "health", "healthcheck", "liveness", "readiness"],
        "监控告警": ["监控", "告警", "monitoring", "alerting", "Prometheus", "Grafana"],
        "目标用户": ["目标用户", "用户画像", "persona", "用户分层"],
        "核心场景": ["核心场景", "用户故事", "user story", "使用场景"],
        "验收标准": ["验收标准", "acceptance criteria", "Given-When-Then"],
        "优先级": ["优先级", "P0", "P1", "P2", "MUST", "SHOULD"],
        "导航": ["导航", "navigation", "nav"],
        "WCAG": ["WCAG", "可访问", "accessibility", "a11y"],
        "根因": ["根因", "root cause", "5 Why", "鱼骨图"],
        "首次上手": ["首次上手", "onboarding", "快速开始", "quickstart"],
    }

    def _check_item(self, content: str, item: str) -> tuple[bool, str]:
        """检查单条审查项是否在交付物中有体现。

        Args:
            content: 交付物文本。
            item: 检查项描述。

        Returns:
            ``(passed, detail)`` 元组。
        """
        if not content:
            return False, "交付物内容为空"

        # 尝试从 _KEYWORD_RULES 中匹配
        matched_rule_key = ""
        for rule_key in self._KEYWORD_RULES:
            if rule_key in item:
                matched_rule_key = rule_key
                break

        if matched_rule_key:
            keywords = self._KEYWORD_RULES[matched_rule_key]
            found = [kw for kw in keywords if kw.lower() in content.lower()]
            if found:
                return True, f"匹配关键词: {', '.join(found[:3])}"
            return False, f"未找到关键词: {', '.join(keywords[:3])}"

        # 回退：从检查项中提取中文/英文短语做模糊匹配
        fragments = self._extract_check_fragments(item)
        if fragments:
            found = [f for f in fragments if f.lower() in content.lower()]
            if found:
                return True, f"匹配片段: {', '.join(found[:3])}"
            return False, "未匹配到相关内容"

        # 无法检测的项默认通过（需要人工或模型审查）
        return True, "规则引擎无法自动检测，建议人工审查"

    @staticmethod
    def _extract_check_fragments(item: str) -> list[str]:
        """从检查项描述中提取可搜索的文本片段。"""
        fragments: list[str] = []

        # 提取中文短语（2-8 字）
        zh_matches = re.findall(r"[\u4e00-\u9fff]{2,8}", item)
        fragments.extend(zh_matches)

        # 提取英文单词/短语
        en_matches = re.findall(r"[A-Za-z][\w\-]{2,}", item)
        fragments.extend(en_matches)

        return fragments
