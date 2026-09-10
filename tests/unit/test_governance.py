"""Tests for PipelineGovernance integration layer."""

from pathlib import Path

import pytest


@pytest.fixture
def governance(tmp_path):
    from super_dev.orchestrator.governance import PipelineGovernance

    (tmp_path / "knowledge").mkdir()
    (tmp_path / "output").mkdir()
    return PipelineGovernance(project_dir=tmp_path)


class TestPipelineGovernance:
    def test_start_returns_run_id(self, governance):
        run_id = governance.start_governance("test-project")
        assert run_id
        assert isinstance(run_id, str)

    def test_enter_exit_phase(self, governance):
        governance.start_governance("test-project")
        governance.enter_phase("research")
        governance.exit_phase("research")

    def test_exit_phase_with_validation(self, governance):
        governance.start_governance("test-project")
        governance.enter_phase("docs")
        governance.exit_phase("docs", context={"project_dir": str(governance.project_dir)})
        # result may be None if no rules match or a ValidationReport
        # either is acceptable in this test

    def test_track_knowledge(self, governance):
        governance.start_governance("test-project")
        governance.enter_phase("research")
        governance.track_knowledge(
            "knowledge/security/01-standards/owasp.md", usage_type="constraint"
        )
        assert len(governance.knowledge_tracker.references) == 1

    def test_record_quality(self, governance):
        governance.start_governance("test-project")
        governance.record_quality(85, True)

    def test_record_rework(self, governance):
        governance.start_governance("test-project")
        governance.record_rework("frontend")

    def test_finish_governance_produces_report(self, governance):
        from super_dev.orchestrator.governance import GovernanceReport

        governance.start_governance("test-project")
        governance.enter_phase("research")
        governance.exit_phase("research")
        governance.record_quality(90, True)
        report = governance.finish_governance()

        assert isinstance(report, GovernanceReport)
        assert report.project_name == "test-project"
        assert report.run_id
        assert report.metrics is not None
        assert report.metrics.quality_gate_score == 90
        assert report.knowledge_report is not None

    def test_report_to_markdown(self, governance):
        governance.start_governance("test-project")
        governance.record_quality(88, True)
        report = governance.finish_governance()
        md = report.to_markdown()
        assert "# Pipeline 治理报告" in md
        assert "test-project" in md

    def test_report_to_dict(self, governance):
        governance.start_governance("test-project")
        report = governance.finish_governance()
        d = report.to_dict()
        assert d["project_name"] == "test-project"
        assert "run_id" in d

    def test_report_save(self, governance):
        governance.start_governance("test-project")
        report = governance.finish_governance()
        path = report.save(str(governance.project_dir / "output"))
        assert Path(path).exists()
        content = Path(path).read_text(encoding="utf-8")
        assert "治理报告" in content

    def test_full_lifecycle(self, governance):
        """完整生命周期测试"""
        governance.start_governance("my-app")

        # research 阶段
        governance.enter_phase("research")
        governance.track_knowledge("knowledge/ai/01-standards/llm.md")
        governance.exit_phase("research")

        # docs 阶段
        governance.enter_phase("docs")
        governance.exit_phase("docs")

        # 记录质量和返工
        governance.record_quality(92, True)
        governance.record_rework("frontend")
        governance.record_knowledge_usage(5, 0.65)

        # 结束
        report = governance.finish_governance()

        assert report.passed
        assert report.metrics.quality_gate_score == 92
        assert report.metrics.rework_count == 1
        assert report.knowledge_report.referenced_files >= 1
