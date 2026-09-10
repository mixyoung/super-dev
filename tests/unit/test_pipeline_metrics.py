"""Unit tests for super_dev.metrics.pipeline_metrics"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from super_dev.metrics.pipeline_metrics import (
    PipelineMetricsAnalyzer,
    PipelineMetricsCollector,
    PipelineRunMetrics,
    _ascii_bar_chart,
    _format_duration,
)

# ---------------------------------------------------------------------------
# PipelineRunMetrics
# ---------------------------------------------------------------------------


class TestPipelineRunMetrics:
    def test_default_values(self):
        m = PipelineRunMetrics(run_id="r1", project_name="p", timestamp="2026-01-01T00:00:00")
        assert m.quality_gate_score == 0
        assert m.phase_durations == {}
        assert m.requirement_coverage == 0.0
        assert m.validation_pass_rate == 0.0

    def test_requirement_coverage(self):
        m = PipelineRunMetrics(
            run_id="r1",
            project_name="p",
            timestamp="t",
            spec_requirements_count=10,
            spec_requirements_covered=8,
        )
        assert m.requirement_coverage == pytest.approx(0.8)

    def test_validation_pass_rate(self):
        m = PipelineRunMetrics(
            run_id="r1",
            project_name="p",
            timestamp="t",
            validation_rules_total=20,
            validation_rules_passed=15,
        )
        assert m.validation_pass_rate == pytest.approx(0.75)

    def test_roundtrip_dict(self):
        m = PipelineRunMetrics(
            run_id="r1",
            project_name="test-proj",
            timestamp="2026-01-01T00:00:00",
            quality_gate_score=90,
            quality_gate_passed=True,
            phase_durations={"research": 10.5, "docs": 20.3},
        )
        d = m.to_dict()
        m2 = PipelineRunMetrics.from_dict(d)
        assert m2.run_id == m.run_id
        assert m2.quality_gate_score == 90
        assert m2.phase_durations == {"research": 10.5, "docs": 20.3}

    def test_from_dict_ignores_unknown_fields(self):
        d = {"run_id": "r", "project_name": "p", "timestamp": "t", "unknown_field": 42}
        m = PipelineRunMetrics.from_dict(d)
        assert m.run_id == "r"


# ---------------------------------------------------------------------------
# PipelineMetricsCollector
# ---------------------------------------------------------------------------


class TestPipelineMetricsCollector:
    def test_start_and_finish_run(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        run_id = collector.start_run("my-project")
        assert run_id
        assert collector.current_run is not None

        metrics = collector.finish_run()
        assert metrics.run_id == run_id
        assert metrics.project_name == "my-project"
        assert metrics.total_duration_seconds >= 0
        assert collector.current_run is None

    def test_phase_tracking(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")

        collector.record_phase_start("research")
        time.sleep(0.05)
        collector.record_phase_end("research")

        metrics = collector.finish_run()
        assert "research" in metrics.phase_durations
        assert metrics.phase_durations["research"] >= 0.04

    def test_unfinished_phases_auto_closed(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")
        collector.record_phase_start("docs")
        # finish_run should auto-close "docs"
        metrics = collector.finish_run()
        assert "docs" in metrics.phase_durations

    def test_record_quality_score(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")
        collector.record_quality_score(92, True)
        metrics = collector.finish_run()
        assert metrics.quality_gate_score == 92
        assert metrics.quality_gate_passed is True

    def test_record_redteam_results(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")
        collector.record_redteam_results(5, 1)
        metrics = collector.finish_run()
        assert metrics.redteam_issues_count == 5
        assert metrics.redteam_critical_count == 1

    def test_record_knowledge_usage(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")
        collector.record_knowledge_usage(15, 0.72)
        metrics = collector.finish_run()
        assert metrics.knowledge_files_referenced == 15
        assert metrics.knowledge_hit_rate == pytest.approx(0.72)

    def test_record_spec_coverage(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")
        collector.record_spec_coverage(20, 18)
        metrics = collector.finish_run()
        assert metrics.spec_requirements_count == 20
        assert metrics.spec_requirements_covered == 18

    def test_record_deliverables(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")
        collector.record_deliverables(5, 0.95)
        metrics = collector.finish_run()
        assert metrics.deliverables_count == 5
        assert metrics.proof_pack_completion == pytest.approx(0.95)

    def test_record_validation_results(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")
        collector.record_validation_results(30, 28, 1)
        metrics = collector.finish_run()
        assert metrics.validation_rules_total == 30
        assert metrics.validation_rules_passed == 28
        assert metrics.validation_critical_failures == 1

    def test_save_creates_json_file(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("my-project")
        metrics = collector.finish_run()

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["project_name"] == "my-project"
        assert data["run_id"] == metrics.run_id

    def test_no_active_run_raises(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="No active run"):
            collector.finish_run()
        with pytest.raises(RuntimeError, match="No active run"):
            collector.record_phase_start("x")
        with pytest.raises(RuntimeError, match="No active run"):
            collector.record_quality_score(0, False)

    def test_phase_end_without_start_warns(self, tmp_path: Path):
        collector = PipelineMetricsCollector(metrics_dir=str(tmp_path))
        collector.start_run("proj")
        # Should not raise, just warn
        collector.record_phase_end("nonexistent")
        metrics = collector.finish_run()
        assert "nonexistent" not in metrics.phase_durations


# ---------------------------------------------------------------------------
# PipelineMetricsAnalyzer
# ---------------------------------------------------------------------------


def _write_sample_metrics(metrics_dir: Path, entries: list[dict]) -> None:
    """Helper to write sample metrics JSON files."""
    metrics_dir.mkdir(parents=True, exist_ok=True)
    for i, entry in enumerate(entries):
        filename = f"{entry.get('project_name', 'proj')}_{entry.get('run_id', f'run{i}')}.json"
        (metrics_dir / filename).write_text(json.dumps(entry), encoding="utf-8")


class TestPipelineMetricsAnalyzer:
    def test_load_history_empty(self, tmp_path: Path):
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path / "empty"))
        assert analyzer.load_history() == []

    def test_load_history_basic(self, tmp_path: Path):
        _write_sample_metrics(
            tmp_path,
            [
                {"run_id": "r1", "project_name": "proj", "timestamp": "2026-01-01T00:00:00"},
                {"run_id": "r2", "project_name": "proj", "timestamp": "2026-01-02T00:00:00"},
            ],
        )
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path))
        history = analyzer.load_history()
        assert len(history) == 2
        assert history[0].run_id == "r1"  # sorted by timestamp

    def test_load_history_project_filter(self, tmp_path: Path):
        _write_sample_metrics(
            tmp_path,
            [
                {"run_id": "r1", "project_name": "alpha", "timestamp": "2026-01-01T00:00:00"},
                {"run_id": "r2", "project_name": "beta", "timestamp": "2026-01-02T00:00:00"},
            ],
        )
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path))
        assert len(analyzer.load_history("alpha")) == 1
        assert len(analyzer.load_history("beta")) == 1

    def test_load_history_limit(self, tmp_path: Path):
        entries = [
            {"run_id": f"r{i}", "project_name": "p", "timestamp": f"2026-01-{i+1:02d}T00:00:00"}
            for i in range(10)
        ]
        _write_sample_metrics(tmp_path, entries)
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path))
        assert len(analyzer.load_history(limit=3)) == 3

    def test_get_trend_empty(self, tmp_path: Path):
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path / "none"))
        trend = analyzer.get_trend()
        assert trend["quality_trend"] == []

    def test_get_trend_with_data(self, tmp_path: Path):
        _write_sample_metrics(
            tmp_path,
            [
                {
                    "run_id": "r1",
                    "project_name": "p",
                    "timestamp": "2026-01-01T00:00:00",
                    "quality_gate_score": 80,
                    "total_duration_seconds": 600,
                    "knowledge_hit_rate": 0.3,
                },
                {
                    "run_id": "r2",
                    "project_name": "p",
                    "timestamp": "2026-01-02T00:00:00",
                    "quality_gate_score": 92,
                    "total_duration_seconds": 420,
                    "knowledge_hit_rate": 0.72,
                },
            ],
        )
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path))
        trend = analyzer.get_trend()
        assert trend["quality_trend"] == [80, 92]
        assert trend["duration_trend"] == [600, 420]
        assert (
            "improved" in trend["improvement_summary"].lower()
            or "reduced" in trend["improvement_summary"].lower()
        )

    def test_get_dora_metrics_empty(self, tmp_path: Path):
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path / "none"))
        dora = analyzer.get_dora_metrics()
        assert dora["total_runs"] == 0

    def test_get_dora_metrics_with_data(self, tmp_path: Path):
        _write_sample_metrics(
            tmp_path,
            [
                {
                    "run_id": "r1",
                    "project_name": "p",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "quality_gate_score": 70,
                    "quality_gate_passed": False,
                    "total_duration_seconds": 500,
                },
                {
                    "run_id": "r2",
                    "project_name": "p",
                    "timestamp": "2026-01-02T00:00:00+00:00",
                    "quality_gate_score": 90,
                    "quality_gate_passed": True,
                    "total_duration_seconds": 400,
                },
                {
                    "run_id": "r3",
                    "project_name": "p",
                    "timestamp": "2026-01-08T00:00:00+00:00",
                    "quality_gate_score": 95,
                    "quality_gate_passed": True,
                    "total_duration_seconds": 350,
                },
            ],
        )
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path))
        dora = analyzer.get_dora_metrics()
        assert dora["total_runs"] == 3
        assert dora["deployment_frequency_per_week"] > 0
        assert dora["lead_time_seconds"] == pytest.approx(416.67, rel=0.01)
        assert dora["change_failure_rate"] == pytest.approx(1 / 3, rel=0.01)
        assert dora["mttr_seconds"] > 0  # recovery from r1->r2

    def test_generate_report_empty(self, tmp_path: Path):
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path / "none"))
        report = analyzer.generate_report()
        assert "Pipeline Efficiency Report" in report
        assert "No historical data" in report

    def test_generate_report_with_data(self, tmp_path: Path):
        _write_sample_metrics(
            tmp_path,
            [
                {
                    "run_id": "r1",
                    "project_name": "demo",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "quality_gate_score": 75,
                    "quality_gate_passed": True,
                    "total_duration_seconds": 600,
                    "knowledge_hit_rate": 0.2,
                    "phase_durations": {"research": 120, "docs": 300, "qa": 180},
                    "redteam_critical_count": 2,
                    "spec_requirements_count": 10,
                    "spec_requirements_covered": 6,
                },
            ],
        )
        analyzer = PipelineMetricsAnalyzer(metrics_dir=str(tmp_path))
        report = analyzer.generate_report("demo")
        assert "DORA" in report
        assert "Quality Score Trend" in report
        assert "Phase Duration Breakdown" in report
        assert "Improvement Suggestions" in report
        # Should have suggestions for low quality/knowledge/coverage/critical
        assert "Quality score" in report or "Knowledge hit rate" in report


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


class TestFormatDuration:
    def test_seconds(self):
        assert _format_duration(30) == "30.0s"

    def test_minutes(self):
        assert _format_duration(150) == "2.5m"

    def test_hours(self):
        assert _format_duration(7200) == "2.0h"


class TestAsciiBarChart:
    def test_empty(self):
        lines = _ascii_bar_chart([])
        assert len(lines) == 1
        assert "no data" in lines[0]

    def test_basic(self):
        lines = _ascii_bar_chart([50, 100], max_val=100, width=20)
        assert len(lines) == 2
        # Second bar should be longer than first
        assert lines[1].count("#") >= lines[0].count("#")
