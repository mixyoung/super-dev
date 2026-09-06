"""
Pipeline 治理集成层

将验证规则、知识追踪、Prompt 版本化、ADR、效能度量统一接入 pipeline。
在 pipeline 各阶段调用，生成治理总报告。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..knowledge_tracker import KnowledgeTracker, KnowledgeTrackingReport
from ..metrics.pipeline_metrics import PipelineMetricsCollector, PipelineRunMetrics
from ..reviewers.validation_rules import ValidationReport, ValidationRuleEngine

_logger = logging.getLogger("super_dev.governance")


@dataclass
class GovernanceReport:
    """治理总报告 — pipeline 执行结束时生成"""

    project_name: str
    run_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    validation_report: ValidationReport | None = None
    knowledge_report: KnowledgeTrackingReport | None = None
    metrics: PipelineRunMetrics | None = None
    adr_count: int = 0
    prompt_template_versions: dict[str, str] = field(default_factory=dict)
    phase_validations: dict[str, ValidationReport] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        if self.validation_report and not self.validation_report.passed:
            return False
        for vr in self.phase_validations.values():
            if not vr.passed:
                return False
        return True

    @property
    def quality_score(self) -> int:
        if self.metrics:
            return self.metrics.quality_gate_score
        return 0

    def to_markdown(self) -> str:
        ts = self.timestamp[:19]
        status = "PASSED" if self.passed else "FAILED"
        lines = [
            "# Pipeline 治理报告",
            "",
            f"**项目**: {self.project_name}",
            f"**Run ID**: {self.run_id}",
            f"**时间**: {ts}",
            f"**状态**: {status}",
            "",
            "---",
            "",
            "## 执行摘要",
            "",
        ]

        if self.metrics:
            m = self.metrics
            lines.append(f"- **总耗时**: {m.total_duration_seconds:.0f}s")
            lines.append(f"- **质量门禁分数**: {m.quality_gate_score}/100")
            lines.append(f"- **返工次数**: {m.rework_count}")
            if m.phase_durations:
                phases_str = ", ".join(f"{p}={d:.0f}s" for p, d in m.phase_durations.items())
                lines.append(f"- **各阶段耗时**: {phases_str}")
            lines.append("")

        if self.knowledge_report:
            kr = self.knowledge_report
            lines.append("## 知识引用")
            lines.append("")
            lines.append(f"- **引用文件数**: {kr.referenced_files}/{kr.total_knowledge_files}")
            lines.append(f"- **命中率**: {kr.hit_rate:.1%}")
            if kr.unreferenced_domains:
                lines.append(f"- **未引用领域**: {', '.join(kr.unreferenced_domains)}")
            lines.append("")

        if self.phase_validations:
            lines.append("## 阶段验证结果")
            lines.append("")
            lines.append("| 阶段 | 通过 | 分数 | 关键失败 |")
            lines.append("|------|------|------|----------|")
            for phase, vr in self.phase_validations.items():
                p = "Y" if vr.passed else "N"
                critical = sum(1 for r in vr.results if not r.passed and r.severity == "critical")
                lines.append(f"| {phase} | {p} | {vr.score} | {critical} |")
            lines.append("")

        if self.adr_count > 0:
            lines.append(f"## 架构决策记录: {self.adr_count} 个 ADR 已生成")
            lines.append("")

        if self.prompt_template_versions:
            lines.append("## Prompt 模板版本")
            lines.append("")
            for tid, ver in self.prompt_template_versions.items():
                lines.append(f"- {tid}: v{ver}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "quality_score": self.quality_score,
            "adr_count": self.adr_count,
            "prompt_template_versions": self.prompt_template_versions,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "knowledge": self.knowledge_report.to_json() if self.knowledge_report else None,
        }

    def save(self, output_dir: str = "output") -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"governance-report-{self.run_id}.md"
        path.write_text(self.to_markdown(), encoding="utf-8")
        _logger.info("Governance report saved to %s", path)
        return path


class PipelineGovernance:
    """Pipeline 治理引擎 — 统一管理所有治理能力"""

    def __init__(self, project_dir: Path | str = "."):
        self.project_dir = Path(project_dir).resolve()
        self.rule_engine = ValidationRuleEngine(self.project_dir)
        self.knowledge_tracker = KnowledgeTracker(project_dir=self.project_dir)
        self.metrics_collector = PipelineMetricsCollector(
            metrics_dir=str(self.project_dir / "output" / "metrics-history")
        )
        self._current_phase: str | None = None
        self._phase_validations: dict[str, ValidationReport] = {}
        self._run_id: str | None = None
        self._project_name: str | None = None

    # ── lifecycle ─────────────────────────────────────────────

    def start_governance(self, project_name: str) -> str:
        """pipeline 开始时调用，返回 run_id"""
        self._project_name = project_name
        self._run_id = self.metrics_collector.start_run(project_name)
        _logger.info("Governance started for %s (run=%s)", project_name, self._run_id)
        return self._run_id

    def enter_phase(self, phase: str) -> None:
        """进入阶段"""
        self._current_phase = phase
        self.metrics_collector.record_phase_start(phase)
        _logger.info("Entered phase: %s", phase)

    def exit_phase(
        self, phase: str, context: dict[str, Any] | None = None
    ) -> ValidationReport | None:
        """退出阶段，执行该阶段的验证规则"""
        self.metrics_collector.record_phase_end(phase)
        self._current_phase = None
        if context:
            report = self.rule_engine.validate(phase, context)
            self._phase_validations[phase] = report
            _logger.info(
                "Phase %s validation: passed=%s score=%s",
                phase,
                report.passed,
                report.score,
            )
            return report
        return None

    # ── knowledge tracking ────────────────────────────────────

    def track_knowledge(
        self,
        knowledge_file: str,
        usage_type: str = "reference",
        relevance: float = 1.0,
        excerpt: str = "",
    ) -> None:
        """记录知识引用"""
        phase = self._current_phase or "unknown"
        self.knowledge_tracker.track_reference(
            knowledge_file=knowledge_file,
            phase=phase,
            usage_type=usage_type,
            relevance_score=relevance,
            excerpt=excerpt,
        )

    def find_knowledge(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """查找相关知识"""
        phase = self._current_phase or "all"
        return self.knowledge_tracker.find_relevant_knowledge(query, phase, top_k)

    # ── quality & rework ──────────────────────────────────────

    def record_quality(self, score: int, passed: bool) -> None:
        self.metrics_collector.record_quality_score(score, passed)

    def record_rework(self, phase: str) -> None:
        self.metrics_collector.record_rework(phase)

    def record_knowledge_usage(self, files_referenced: int, hit_rate: float) -> None:
        self.metrics_collector.record_knowledge_usage(files_referenced, hit_rate)

    # ── finish ────────────────────────────────────────────────

    def finish_governance(self) -> GovernanceReport:
        """pipeline 结束，生成治理总报告"""
        project_name = self._project_name or "unknown"
        metrics = self.metrics_collector.finish_run()
        output_dir = self.project_dir / "output"

        kr = self.knowledge_tracker.generate_report(project_name, metrics.run_id)
        self.knowledge_tracker.save_report(kr, output_dir=str(output_dir))

        # 收集 prompt 模板版本
        template_versions: dict[str, str] = {}
        try:
            from ..creators.prompt_templates import PromptTemplateManager

            mgr = PromptTemplateManager()
            for t in mgr.list_templates():
                template_versions[t.id] = t.version
        except Exception:
            pass

        # 统计 ADR
        adr_count = 0
        adr_dir = self.project_dir / ".super-dev" / "decisions"
        if adr_dir.exists():
            adr_count = sum(1 for f in adr_dir.glob("*.md"))

        report = GovernanceReport(
            project_name=project_name,
            run_id=metrics.run_id,
            validation_report=None,
            knowledge_report=kr,
            metrics=metrics,
            adr_count=adr_count,
            prompt_template_versions=template_versions,
            phase_validations=self._phase_validations,
        )
        report.save(output_dir=str(output_dir))

        # pipeline 结束后触发知识演化分析
        try:
            from ..knowledge_evolution import KnowledgeEvolutionAnalyzer

            analyzer = KnowledgeEvolutionAnalyzer(self.project_dir)
            knowledge_push_data: dict = {}
            if kr:
                # 将知识引用报告转为推送数据格式
                for ref in kr.references:
                    phase = ref.phase
                    if phase not in knowledge_push_data:
                        knowledge_push_data[phase] = {"files": [], "constraints": []}
                    knowledge_push_data[phase]["files"].append(
                        {
                            "path": ref.knowledge_file,
                            "domain": "",
                            "category": "",
                        }
                    )
            quality_result: dict = {}
            if metrics:
                quality_result["score"] = metrics.quality_gate_score
                quality_result["passed"] = report.passed
            analyzer.analyze_pipeline_run(
                run_id=metrics.run_id,
                knowledge_push_data=knowledge_push_data,
                quality_result=quality_result,
            )
            _logger.info("知识演化分析已完成 (run=%s)", metrics.run_id)
        except Exception as exc:
            _logger.debug("知识演化分析跳过: %s", exc)

        _logger.info("Governance finished. Passed=%s", report.passed)
        return report
