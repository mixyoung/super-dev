"""Tests for Overseer agent – phase/step checkpoint review, deviation tracking, and report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.orchestrator.overseer import (
    CheckpointReport,
    CheckpointVerdict,
    Deviation,
    DeviationSeverity,
    Overseer,
    OverseerReport,
    _escape_markdown_cell,
    _now_iso,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def overseer(temp_project_dir: Path) -> Overseer:
    """Create an Overseer instance pointing at a temporary project directory."""
    return Overseer(
        project_dir=temp_project_dir,
        project_name="test-project",
        quality_threshold=80.0,
        halt_on_critical=True,
    )


@pytest.fixture
def overseer_no_halt(temp_project_dir: Path) -> Overseer:
    """Create an Overseer instance that does NOT halt on critical deviations."""
    return Overseer(
        project_dir=temp_project_dir,
        project_name="test-project",
        quality_threshold=80.0,
        halt_on_critical=False,
    )


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


class TestOverseerInit:
    def test_creates_overseer_directory(self, temp_project_dir: Path) -> None:
        overseer = Overseer(
            project_dir=temp_project_dir,
            project_name="init-test",
        )
        assert overseer.overseer_dir.exists()
        assert overseer.overseer_dir == (temp_project_dir / ".super-dev" / "overseer").resolve()

    def test_default_quality_threshold(self, temp_project_dir: Path) -> None:
        overseer = Overseer(
            project_dir=temp_project_dir,
            project_name="init-test",
        )
        assert overseer.quality_threshold == 80.0

    def test_custom_quality_threshold(self, temp_project_dir: Path) -> None:
        overseer = Overseer(
            project_dir=temp_project_dir,
            project_name="init-test",
            quality_threshold=95.0,
        )
        assert overseer.quality_threshold == 95.0

    def test_project_name_stored(self, overseer: Overseer) -> None:
        assert overseer.project_name == "test-project"

    def test_initial_report_has_no_checkpoints(self, overseer: Overseer) -> None:
        report = overseer.get_report()
        assert report.project_name == "test-project"
        assert report.checkpoints == []
        assert report.total_deviations == 0
        assert report.overall_verdict == CheckpointVerdict.PASS

    def test_report_json_written_after_checkpoint(self, overseer: Overseer) -> None:
        # _save_report is called by checkpoint methods, not during init
        overseer.checkpoint_phase("research", quality_score=90.0)
        report_path = overseer.overseer_dir / "report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["project_name"] == "test-project"

    def test_path_accepts_string(self, temp_project_dir: Path) -> None:
        overseer = Overseer(
            project_dir=str(temp_project_dir),
            project_name="str-path",
        )
        assert overseer.project_dir == temp_project_dir.resolve()


# ---------------------------------------------------------------------------
# Checkpoint phase tests
# ---------------------------------------------------------------------------


class TestCheckpointPhase:
    def test_clean_phase_passes(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=90.0,
        )
        assert report.verdict == CheckpointVerdict.PASS
        assert len(report.deviations) == 0

    def test_low_quality_creates_deviation(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=70.0,
        )
        assert len(report.deviations) == 1
        assert report.deviations[0].category == "quality-drop"
        # Gap is 10 (80 - 70), which is < 20, so it's WARNING
        assert report.deviations[0].severity == DeviationSeverity.WARNING

    def test_very_low_quality_creates_high_severity(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=50.0,
        )
        # Gap is 30 (80 - 50), which is >= 20, so it's HIGH
        assert report.deviations[0].severity == DeviationSeverity.HIGH

    def test_moderate_quality_creates_warning(self, overseer: Overseer) -> None:
        # Gap < 20 → WARNING
        overseer.quality_threshold = 80.0
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=65.0,
        )
        assert report.deviations[0].severity == DeviationSeverity.WARNING

    def test_quality_exactly_at_threshold_passes(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=80.0,
        )
        assert report.verdict == CheckpointVerdict.PASS
        assert len(report.deviations) == 0

    def test_verdict_hold_with_high_severity(self, overseer: Overseer) -> None:
        # Gap >= 20 → HIGH → HOLD verdict
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=50.0,
        )
        assert report.verdict == CheckpointVerdict.HOLD

    def test_verdict_warn_with_warning_severity(self, overseer: Overseer) -> None:
        overseer.quality_threshold = 80.0
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=65.0,
        )
        assert report.verdict == CheckpointVerdict.WARN

    def test_codex_review_critical_creates_deviation(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="backend",
            quality_score=90.0,
            codex_reviews=[
                {"severity": "critical", "issue": "Security vulnerability found."},
            ],
        )
        assert any(d.category == "codex-unresolved" for d in report.deviations)
        assert any(d.severity == DeviationSeverity.CRITICAL for d in report.deviations)

    def test_codex_review_high_creates_deviation(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="backend",
            quality_score=90.0,
            codex_reviews=[
                {"severity": "high", "issue": "Logic error in module X."},
            ],
        )
        assert any(d.category == "codex-unresolved" for d in report.deviations)

    def test_codex_review_low_severity_ignored(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="backend",
            quality_score=90.0,
            codex_reviews=[
                {"severity": "low", "issue": "Minor style issue."},
            ],
        )
        assert len(report.deviations) == 0

    def test_pipeline_halts_on_critical_when_enabled(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase(
            phase="backend",
            quality_score=90.0,
            codex_reviews=[
                {"severity": "critical", "issue": "Critical issue."},
            ],
        )
        assert overseer.should_halt() is True
        report = overseer.get_report()
        assert report.pipeline_halted is True
        assert "backend" in report.halt_reason

    def test_pipeline_does_not_halt_on_critical_when_disabled(
        self, overseer_no_halt: Overseer
    ) -> None:
        overseer_no_halt.checkpoint_phase(
            phase="backend",
            quality_score=90.0,
            codex_reviews=[
                {"severity": "critical", "issue": "Critical issue."},
            ],
        )
        assert overseer_no_halt.should_halt() is False


# ---------------------------------------------------------------------------
# Plan alignment tests
# ---------------------------------------------------------------------------


class TestPlanAlignment:
    def test_missing_expected_output_file_creates_deviation(self, overseer: Overseer) -> None:
        # _check_plan_alignment is only called when both plan_data and actual_output are truthy
        plan_data = {
            "expected_outputs": ["/nonexistent/deeply/nested/output.md"],
            "required_keys": [],
        }
        report = overseer.checkpoint_phase(
            phase="docs",
            quality_score=90.0,
            plan_data=plan_data,
            actual_output={"some": "data"},  # must be non-empty dict
        )
        assert any(d.category == "spec-drift" for d in report.deviations)
        assert any("output.md" in d.description for d in report.deviations)

    def test_missing_required_key_creates_deviation(self, overseer: Overseer) -> None:
        plan_data = {
            "expected_outputs": [],
            "required_keys": ["architecture", "prd"],
        }
        report = overseer.checkpoint_phase(
            phase="docs",
            quality_score=90.0,
            plan_data=plan_data,
            actual_output={"architecture": "some doc"},
        )
        spec_drifts = [d for d in report.deviations if d.category == "spec-drift"]
        assert len(spec_drifts) == 1
        assert "prd" in spec_drifts[0].description

    def test_all_keys_present_no_deviations(self, overseer: Overseer) -> None:
        plan_data = {
            "expected_outputs": [],
            "required_keys": ["architecture", "prd"],
        }
        report = overseer.checkpoint_phase(
            phase="docs",
            quality_score=90.0,
            plan_data=plan_data,
            actual_output={"architecture": "doc", "prd": "doc"},
        )
        spec_drifts = [d for d in report.deviations if d.category == "spec-drift"]
        assert len(spec_drifts) == 0


# ---------------------------------------------------------------------------
# Checkpoint step tests
# ---------------------------------------------------------------------------


class TestCheckpointStep:
    def test_clean_step_passes(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_step(
            phase="frontend",
            step_id="step-1",
            step_label="Build components",
            actual_output={"files": ["Button.tsx"]},
        )
        assert report.verdict == CheckpointVerdict.PASS
        assert len(report.deviations) == 0

    def test_missing_output_creates_warning(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_step(
            phase="frontend",
            step_id="step-1",
            step_label="Build components",
        )
        assert len(report.deviations) == 1
        assert report.deviations[0].category == "data-gap"

    def test_empty_output_creates_warning(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_step(
            phase="frontend",
            step_id="step-1",
            step_label="Build components",
            actual_output={},
        )
        assert len(report.deviations) == 1
        assert report.deviations[0].category == "data-gap"

    def test_failed_required_verify_gate_creates_deviation(self, overseer: Overseer) -> None:
        verify_results = [
            {"gate": "lint", "required": True, "passed": False},
            {"gate": "typecheck", "required": True, "passed": True},
        ]
        report = overseer.checkpoint_step(
            phase="frontend",
            step_id="step-1",
            step_label="Build components",
            actual_output={"files": ["App.tsx"]},
            verify_results=verify_results,
        )
        assert any(d.category == "behavior-anomaly" for d in report.deviations)
        assert any("lint" in d.description for d in report.deviations)

    def test_passed_required_verify_gate_no_deviation(self, overseer: Overseer) -> None:
        verify_results = [
            {"gate": "lint", "required": True, "passed": True},
        ]
        report = overseer.checkpoint_step(
            phase="frontend",
            step_id="step-1",
            step_label="Build components",
            actual_output={"files": ["App.tsx"]},
            verify_results=verify_results,
        )
        assert len(report.deviations) == 0

    def test_optional_failed_gate_no_deviation(self, overseer: Overseer) -> None:
        verify_results = [
            {"gate": "style-check", "required": False, "passed": False},
        ]
        report = overseer.checkpoint_step(
            phase="frontend",
            step_id="step-1",
            step_label="Build components",
            actual_output={"files": ["App.tsx"]},
            verify_results=verify_results,
        )
        assert len(report.deviations) == 0

    def test_codex_review_critical_on_step(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_step(
            phase="backend",
            step_id="step-2",
            step_label="Implement API",
            actual_output={"files": ["api.py"]},
            codex_review={"severity": "critical", "issue": "SQL injection risk."},
        )
        assert any(d.severity == DeviationSeverity.CRITICAL for d in report.deviations)
        assert report.codex_review_processed is True

    def test_codex_review_low_severity_no_deviation(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_step(
            phase="backend",
            step_id="step-2",
            step_label="Implement API",
            actual_output={"files": ["api.py"]},
            codex_review={"severity": "info", "issue": "Minor suggestion."},
        )
        assert len(report.deviations) == 0
        assert report.codex_review_processed is True

    def test_no_codex_review_means_not_processed(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_step(
            phase="backend",
            step_id="step-2",
            step_label="Implement API",
            actual_output={"files": ["api.py"]},
        )
        assert report.codex_review_processed is False


# ---------------------------------------------------------------------------
# Report summary & tracking tests
# ---------------------------------------------------------------------------


class TestReportSummary:
    def test_multiple_checkpoints_update_summary(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase("research", quality_score=90.0)
        overseer.checkpoint_phase("docs", quality_score=50.0)  # gap >= 20 → HIGH

        report = overseer.get_report()
        assert len(report.checkpoints) == 2
        assert report.total_deviations == 1
        assert report.high_count == 1

    def test_overall_verdict_reflects_worst_checkpoint(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase("research", quality_score=90.0)
        overseer.checkpoint_phase("docs", quality_score=50.0)  # HIGH → HOLD

        report = overseer.get_report()
        assert report.overall_verdict == CheckpointVerdict.HOLD

    def test_overall_verdict_pass_when_all_pass(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase("research", quality_score=90.0)
        overseer.checkpoint_phase("docs", quality_score=85.0)

        report = overseer.get_report()
        assert report.overall_verdict == CheckpointVerdict.PASS


# ---------------------------------------------------------------------------
# Deviation resolution tests
# ---------------------------------------------------------------------------


class TestDeviationResolution:
    def test_mark_deviation_resolved(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase("research", quality_score=70.0)
        deviation_id = overseer.get_report().checkpoints[0].deviations[0].id

        result = overseer.mark_deviation_resolved(deviation_id, "Fixed quality issues")
        assert result is True

        deviation = overseer.get_report().checkpoints[0].deviations[0]
        assert deviation.resolved is True
        assert deviation.resolution == "Fixed quality issues"

    def test_mark_nonexistent_deviation_returns_false(self, overseer: Overseer) -> None:
        result = overseer.mark_deviation_resolved(99999, "Doesn't exist")
        assert result is False

    def test_resolution_persists_to_disk(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase("research", quality_score=70.0)
        deviation_id = overseer.get_report().checkpoints[0].deviations[0].id

        overseer.mark_deviation_resolved(deviation_id, "Fixed")

        report_path = overseer.overseer_dir / "report.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        dev = data["checkpoints"][0]["deviations"][0]
        assert dev["resolved"] is True


# ---------------------------------------------------------------------------
# Finalize tests
# ---------------------------------------------------------------------------


class TestFinalize:
    def test_finalize_writes_markdown_report(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase("research", quality_score=90.0)
        overseer.finalize()

        md_path = overseer.overseer_dir / "report.md"
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "# Super Dev Overseer Report" in content
        assert "test-project" in content

    def test_finalize_returns_overseer_report(self, overseer: Overseer) -> None:
        report = overseer.finalize()
        assert isinstance(report, OverseerReport)


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_deviation_to_dict(self) -> None:
        dev = Deviation(
            id=1,
            severity=DeviationSeverity.HIGH,
            category="quality-drop",
            description="Score below threshold",
            expected=">= 80",
            actual="70",
            recommendation="Improve quality",
            phase="research",
            step_id="",
        )
        d = dev.to_dict()
        assert d["id"] == 1
        assert d["severity"] == "HIGH"
        assert d["category"] == "quality-drop"
        assert d["resolved"] is False

    def test_checkpoint_report_to_dict(self) -> None:
        report = CheckpointReport(
            checkpoint_id="phase-research",
            phase="research",
            step_id="",
            verdict=CheckpointVerdict.PASS,
            timestamp=_now_iso(),
        )
        d = report.to_dict()
        assert d["checkpoint_id"] == "phase-research"
        assert d["verdict"] == "PASS"
        assert d["deviations"] == []

    def test_overseer_report_to_dict(self) -> None:
        report = OverseerReport(
            project_name="my-project",
            report_id="abc123",
            created_at=_now_iso(),
        )
        d = report.to_dict()
        assert d["project_name"] == "my-project"
        assert d["report_id"] == "abc123"

    def test_overseer_report_to_markdown(self) -> None:
        report = OverseerReport(
            project_name="my-project",
            report_id="abc123",
            created_at="2026-04-11T00:00:00+00:00",
            total_deviations=2,
            critical_count=1,
            high_count=0,
            warning_count=1,
            overall_verdict=CheckpointVerdict.FAIL,
            pipeline_halted=True,
            halt_reason="Critical deviation detected",
        )
        md = report.to_markdown()
        assert "# Super Dev Overseer Report" in md
        assert "my-project" in md
        assert "FAIL" in md
        assert "Critical deviation detected" in md

    def test_overseer_report_markdown_with_checkpoints(self) -> None:
        dev = Deviation(
            id=1,
            severity=DeviationSeverity.WARNING,
            category="quality-drop",
            description="Low score",
            expected=">= 80",
            actual="70",
            recommendation="Improve",
            phase="research",
            step_id="",
        )
        checkpoint = CheckpointReport(
            checkpoint_id="phase-research",
            phase="research",
            step_id="",
            verdict=CheckpointVerdict.WARN,
            timestamp="2026-04-11T00:00:00+00:00",
            deviations=[dev],
            quality_score=70.0,
            notes="Needs improvement",
        )
        report = OverseerReport(
            project_name="test-proj",
            report_id="r1",
            created_at="2026-04-11T00:00:00+00:00",
            checkpoints=[checkpoint],
            total_deviations=1,
            warning_count=1,
            overall_verdict=CheckpointVerdict.WARN,
        )
        md = report.to_markdown()
        assert "phase-research" in md
        assert "WARN" in md
        assert "quality-drop" in md
        assert "Needs improvement" in md

    def test_escape_markdown_cell(self) -> None:
        assert _escape_markdown_cell("a|b") == r"a\|b"
        assert _escape_markdown_cell("line1\nline2") == "line1<br/>line2"

    def test_report_json_persists_across_checkpoints(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase("research", quality_score=90.0)
        overseer.checkpoint_phase("docs", quality_score=85.0)

        report_path = overseer.overseer_dir / "report.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert len(data["checkpoints"]) == 2


# ---------------------------------------------------------------------------
# should_halt tests
# ---------------------------------------------------------------------------


class TestShouldHalt:
    def test_initially_not_halted(self, overseer: Overseer) -> None:
        assert overseer.should_halt() is False

    def test_halted_after_critical_deviation(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase(
            phase="backend",
            quality_score=90.0,
            codex_reviews=[{"severity": "critical", "issue": "Bad"}],
        )
        assert overseer.should_halt() is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_codex_reviews_list(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=90.0,
            codex_reviews=[],
        )
        assert report.codex_review_processed is True
        assert len(report.deviations) == 0

    def test_none_plan_data_no_error(self, overseer: Overseer) -> None:
        report = overseer.checkpoint_phase(
            phase="research",
            quality_score=90.0,
            plan_data=None,
            actual_output=None,
        )
        assert report.verdict == CheckpointVerdict.PASS

    def test_multiple_deviation_ids_increment(self, overseer: Overseer) -> None:
        overseer.checkpoint_phase("research", quality_score=70.0)
        overseer.checkpoint_step(
            phase="research",
            step_id="s1",
            step_label="Do thing",
        )
        report = overseer.get_report()
        all_ids = [d.id for cp in report.checkpoints for d in cp.deviations]
        assert len(set(all_ids)) == len(all_ids)  # all unique
