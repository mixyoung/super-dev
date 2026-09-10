"""知识演化引擎单元测试"""

from __future__ import annotations

import pytest

from super_dev.knowledge_evolution import (
    EvolutionReport,
    EvolutionSuggestion,
    KnowledgeEvolutionAnalyzer,
    KnowledgeFileStats,
    KnowledgeStatsDB,
    _short_path,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a KnowledgeStatsDB in a temp directory."""
    db = KnowledgeStatsDB(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture()
def project_with_knowledge(tmp_path):
    """Create a minimal project with knowledge files."""
    (tmp_path / ".super-dev").mkdir()
    knowledge_dir = tmp_path / "knowledge"

    # Create a few knowledge files
    for domain, category, filename, content in [
        (
            "security",
            "01-standards",
            "web-security.md",
            "# Web Security\nUse HTTPS everywhere.\n## Agent Checklist\n- [ ] Use HTTPS\n- [ ] Sanitize input\n",
        ),
        ("security", "03-checklists", "owasp-top10.md", "# OWASP Top 10\nCheck all OWASP items.\n"),
        (
            "design",
            "01-standards",
            "ui-design.md",
            "# UI Design Standards\nFollow design system tokens.\n",
        ),
        (
            "development",
            "01-standards",
            "python-best-practices.md",
            "# Python Best Practices\nUse type hints everywhere.\n",
        ),
        (
            "testing",
            "04-antipatterns",
            "testing-antipatterns.md",
            "# Testing Anti-patterns\n### Flaky Tests\nAvoid flaky tests.\n### No Assertions\nAlways assert.\n",
        ),
    ]:
        d = knowledge_dir / domain / category
        d.mkdir(parents=True, exist_ok=True)
        (d / filename).write_text(content, encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# KnowledgeFileStats tests
# ---------------------------------------------------------------------------


class TestKnowledgeFileStats:
    def test_compliance_rate_no_data(self):
        stats = KnowledgeFileStats(file_path="test.md")
        assert stats.compliance_rate == 0.0

    def test_compliance_rate_all_followed(self):
        stats = KnowledgeFileStats(
            file_path="test.md",
            constraints_followed=10,
            constraints_violated=0,
        )
        assert stats.compliance_rate == 1.0

    def test_compliance_rate_mixed(self):
        stats = KnowledgeFileStats(
            file_path="test.md",
            constraints_followed=7,
            constraints_violated=3,
        )
        assert stats.compliance_rate == pytest.approx(0.7)

    def test_to_dict(self):
        stats = KnowledgeFileStats(
            file_path="knowledge/security/test.md",
            domain="security",
            category="01-standards",
            total_references=5,
            effectiveness_score=0.85,
        )
        d = stats.to_dict()
        assert d["file_path"] == "knowledge/security/test.md"
        assert d["total_references"] == 5
        assert d["effectiveness_score"] == 0.85


# ---------------------------------------------------------------------------
# KnowledgeStatsDB tests
# ---------------------------------------------------------------------------


class TestKnowledgeStatsDB:
    def test_record_and_get_usage(self, tmp_db):
        tmp_db.record_usage("file_a.md", "backend", "run-001", "security", "01-standards")
        tmp_db.record_usage("file_a.md", "quality", "run-001", "security", "01-standards")

        stats = tmp_db.get_file_stats("file_a.md")
        assert stats is not None
        assert stats.total_references == 2
        assert stats.domain == "security"

    def test_record_constraint_results(self, tmp_db):
        tmp_db.record_usage("file_a.md", "backend", "run-001")
        tmp_db.record_constraint_result("file_a.md", "Use HTTPS", True, "run-001")
        tmp_db.record_constraint_result("file_a.md", "Sanitize input", False, "run-001")

        stats = tmp_db.get_file_stats("file_a.md")
        assert stats is not None
        assert stats.constraints_followed == 1
        assert stats.constraints_violated == 1

    def test_update_effectiveness_scores(self, tmp_db):
        tmp_db.record_usage("file_a.md", "backend", "run-001")
        tmp_db.record_usage("file_a.md", "quality", "run-002")
        tmp_db.record_constraint_result("file_a.md", "Rule 1", True, "run-001")
        tmp_db.record_constraint_result("file_a.md", "Rule 2", True, "run-002")

        tmp_db.update_effectiveness_scores()

        stats = tmp_db.get_file_stats("file_a.md")
        assert stats is not None
        assert stats.effectiveness_score > 0

    def test_get_top_effective(self, tmp_db):
        # Create files with different effectiveness
        for i in range(5):
            fp = f"file_{i}.md"
            for _ in range(i + 1):
                tmp_db.record_usage(fp, "backend", f"run-{i}")
            for _ in range(i + 1):
                tmp_db.record_constraint_result(fp, f"Rule-{i}", True, f"run-{i}")

        tmp_db.update_effectiveness_scores()
        top = tmp_db.get_top_effective(3)
        assert len(top) == 3
        # The file with most references should be first
        assert top[0].total_references >= top[1].total_references

    def test_get_least_effective(self, tmp_db):
        tmp_db.record_usage("good.md", "backend", "run-001")
        tmp_db.record_constraint_result("good.md", "Rule", True, "run-001")
        tmp_db.record_usage("bad.md", "backend", "run-001")
        tmp_db.record_constraint_result("bad.md", "Rule", False, "run-001")

        tmp_db.update_effectiveness_scores()
        least = tmp_db.get_least_effective(5)
        assert len(least) == 2

    def test_get_never_used(self, tmp_db):
        tmp_db.record_usage("used.md", "backend", "run-001")

        all_files = ["used.md", "unused_1.md", "unused_2.md"]
        never = tmp_db.get_never_used(all_files)
        assert set(never) == {"unused_1.md", "unused_2.md"}

    def test_get_never_used_without_all_files(self, tmp_db):
        # Insert a file with 0 references
        conn = tmp_db._get_conn()
        conn.execute(
            "INSERT INTO knowledge_stats (file_path, total_references) VALUES (?, ?)",
            ("zero.md", 0),
        )
        conn.commit()

        never = tmp_db.get_never_used()
        assert "zero.md" in never

    def test_get_high_violation_constraints(self, tmp_db):
        tmp_db.record_usage("file_a.md", "backend", "run-001")
        for _ in range(5):
            tmp_db.record_constraint_result("file_a.md", "Bad Rule", False, "run-001")
        tmp_db.record_constraint_result("file_a.md", "Bad Rule", True, "run-001")

        violations = tmp_db.get_high_violation_constraints()
        assert len(violations) == 1
        assert violations[0]["violated"] == 5
        assert violations[0]["followed"] == 1

    def test_get_total_pipeline_runs(self, tmp_db):
        tmp_db.record_usage("f.md", "b", "run-001")
        tmp_db.record_usage("f.md", "b", "run-002")
        tmp_db.record_usage("f.md", "b", "run-002")  # duplicate run_id

        assert tmp_db.get_total_pipeline_runs() == 2

    def test_get_tracked_file_count(self, tmp_db):
        tmp_db.record_usage("a.md", "b", "run-001")
        tmp_db.record_usage("b.md", "b", "run-001")

        assert tmp_db.get_tracked_file_count() == 2

    def test_save_and_get_suggestions(self, tmp_db):
        sug = EvolutionSuggestion(
            suggestion_type="boost",
            file_path="good.md",
            reason="High effectiveness",
            priority=3,
        )
        tmp_db.save_suggestion(sug, "run-001")

        recent = tmp_db.get_recent_suggestions(5)
        assert len(recent) == 1
        assert recent[0].suggestion_type == "boost"
        assert recent[0].file_path == "good.md"

    def test_record_constraints_pushed(self, tmp_db):
        tmp_db.record_usage("f.md", "backend", "run-001")
        tmp_db.record_constraints_pushed("f.md", 5)

        stats = tmp_db.get_file_stats("f.md")
        assert stats is not None
        assert stats.total_constraints_pushed == 5

    def test_db_failure_graceful(self, tmp_path):
        """DB operations should not raise even on failure."""
        db = KnowledgeStatsDB(tmp_path / "nonexistent" / "deep" / "db.db")
        # These should all silently fail or return defaults
        db.record_usage("f.md", "b", "r")
        stats = db.get_file_stats("f.md")
        assert stats is None or isinstance(stats, KnowledgeFileStats)
        db.close()

    def test_get_file_stats_nonexistent(self, tmp_db):
        assert tmp_db.get_file_stats("nonexistent.md") is None


# ---------------------------------------------------------------------------
# KnowledgeEvolutionAnalyzer tests
# ---------------------------------------------------------------------------


class TestKnowledgeEvolutionAnalyzer:
    def test_analyze_pipeline_run(self, project_with_knowledge):
        analyzer = KnowledgeEvolutionAnalyzer(project_with_knowledge)
        knowledge_dir = project_with_knowledge / "knowledge"

        result = analyzer.analyze_pipeline_run(
            "run-001",
            knowledge_push_data={
                "backend": {
                    "files": [
                        {
                            "path": str(knowledge_dir / "security/01-standards/web-security.md"),
                            "domain": "security",
                            "category": "01-standards",
                        }
                    ],
                    "constraints": ["Use HTTPS", "Sanitize input"],
                },
            },
            quality_result={
                "score": 90,
                "passed": True,
                "violations": [
                    {
                        "source_file": str(knowledge_dir / "security/01-standards/web-security.md"),
                        "constraint": "Use HTTPS",
                        "followed": True,
                    },
                ],
            },
        )

        assert result["files_pushed"] == 1
        assert result["constraints_pushed"] == 2
        assert result["constraints_evaluated"] == 1
        analyzer.db.close()

    def test_analyze_with_none_data(self, project_with_knowledge):
        analyzer = KnowledgeEvolutionAnalyzer(project_with_knowledge)
        result = analyzer.analyze_pipeline_run("run-empty")
        assert result["files_pushed"] == 0
        analyzer.db.close()

    def test_generate_evolution_report(self, project_with_knowledge):
        analyzer = KnowledgeEvolutionAnalyzer(project_with_knowledge)
        knowledge_dir = project_with_knowledge / "knowledge"

        # Seed some data
        fp = str(knowledge_dir / "security/01-standards/web-security.md")
        for i in range(5):
            analyzer.db.record_usage(fp, "backend", f"run-{i}", "security", "01-standards")
            analyzer.db.record_constraint_result(fp, "Use HTTPS", True, f"run-{i}")
        analyzer.db.update_effectiveness_scores()

        report = analyzer.generate_evolution_report()
        assert isinstance(report, EvolutionReport)
        assert report.total_knowledge_files > 0
        assert report.tracked_files >= 1
        assert report.total_pipeline_runs >= 1

        md = report.to_markdown()
        assert "# 知识演化报告" in md
        assert "最有效的知识文件" in md

        d = report.to_dict()
        assert "top_effective" in d
        analyzer.db.close()

    def test_save_evolution_report(self, project_with_knowledge):
        analyzer = KnowledgeEvolutionAnalyzer(project_with_knowledge)
        report = analyzer.generate_evolution_report()

        output_dir = project_with_knowledge / "output"
        saved = analyzer.save_evolution_report(report, str(output_dir))
        assert saved.exists()
        assert (output_dir / "knowledge-evolution-report.json").exists()
        analyzer.db.close()

    def test_suggest_knowledge_weights(self, project_with_knowledge):
        analyzer = KnowledgeEvolutionAnalyzer(project_with_knowledge)
        knowledge_dir = project_with_knowledge / "knowledge"

        fp = str(knowledge_dir / "security/01-standards/web-security.md")
        # Many uses and high compliance -> should get boosted
        for i in range(10):
            analyzer.db.record_usage(fp, "backend", f"run-{i}")
            analyzer.db.record_constraint_result(fp, "Rule", True, f"run-{i}")
        analyzer.db.update_effectiveness_scores()

        weights = analyzer.suggest_knowledge_weights()
        assert isinstance(weights, dict)
        # The heavily-used file should get a boost
        if fp in weights:
            assert weights[fp] >= 1.0
        analyzer.db.close()

    def test_get_weight_for_file(self, project_with_knowledge):
        analyzer = KnowledgeEvolutionAnalyzer(project_with_knowledge)

        # No data -> default weight
        w = analyzer.get_weight_for_file("nonexistent.md")
        assert w == 1.0
        analyzer.db.close()

    def test_get_weight_for_file_low_samples(self, project_with_knowledge):
        analyzer = KnowledgeEvolutionAnalyzer(project_with_knowledge)
        analyzer.db.record_usage("few.md", "backend", "run-1")
        analyzer.db.update_effectiveness_scores()

        w = analyzer.get_weight_for_file("few.md")
        assert w == 1.0  # < 3 samples, no adjustment
        analyzer.db.close()


# ---------------------------------------------------------------------------
# EvolutionSuggestion tests
# ---------------------------------------------------------------------------


class TestEvolutionSuggestion:
    def test_to_dict(self):
        sug = EvolutionSuggestion(
            suggestion_type="boost",
            file_path="good.md",
            reason="Very effective",
            priority=4,
            data={"score": 0.95},
        )
        d = sug.to_dict()
        assert d["type"] == "boost"
        assert d["priority"] == 4
        assert d["data"]["score"] == 0.95


# ---------------------------------------------------------------------------
# EvolutionReport tests
# ---------------------------------------------------------------------------


class TestEvolutionReport:
    def test_empty_report_markdown(self):
        report = EvolutionReport(generated_at="2026-03-28T00:00:00Z")
        md = report.to_markdown()
        assert "# 知识演化报告" in md
        assert "2026-03-28" in md

    def test_report_with_data_markdown(self):
        report = EvolutionReport(
            generated_at="2026-03-28T00:00:00Z",
            total_knowledge_files=50,
            tracked_files=20,
            total_pipeline_runs=5,
            top_effective=[
                KnowledgeFileStats(
                    file_path="knowledge/security/01-standards/web.md",
                    total_references=15,
                    effectiveness_score=0.9,
                    constraints_followed=10,
                    constraints_violated=1,
                )
            ],
            never_used=["knowledge/unused/file.md"],
            suggestions=[EvolutionSuggestion("boost", "good.md", "Very effective", 3)],
            weight_adjustments={"good.md": 1.5, "bad.md": 0.5},
        )
        md = report.to_markdown()
        assert "最有效的知识文件" in md
        assert "从未使用的知识文件" in md
        assert "改进建议" in md
        assert "知识权重调整建议" in md

    def test_report_to_dict(self):
        report = EvolutionReport(
            generated_at="2026-03-28T00:00:00Z",
            total_knowledge_files=10,
        )
        d = report.to_dict()
        assert d["total_knowledge_files"] == 10
        assert isinstance(d["top_effective"], list)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestShortPath:
    def test_with_knowledge_prefix(self):
        result = _short_path("knowledge/security/01-standards/web.md")
        assert result == "knowledge/security/01-standards/web.md"

    def test_with_full_path(self):
        result = _short_path("/home/user/project/knowledge/security/web.md")
        assert "knowledge" in result

    def test_short_path(self):
        result = _short_path("a/b.md")
        assert result == "a/b.md"

    def test_deep_path_without_knowledge(self):
        result = _short_path("/a/b/c/d/e/f.md")
        assert "..." in result
