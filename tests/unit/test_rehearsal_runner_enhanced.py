# ruff: noqa: I001
"""
发布演练执行器增强测试

测试对象: super_dev.deployers.rehearsal_runner
"""

from super_dev.deployers.rehearsal_runner import RehearsalCheck, RehearsalResult

# ---------------------------------------------------------------------------
# RehearsalCheck
# ---------------------------------------------------------------------------


class TestRehearsalCheck:
    def test_basic_creation(self):
        check = RehearsalCheck(name="CI/CD", passed=True, detail="All pipelines configured")
        assert check.name == "CI/CD"
        assert check.passed is True
        assert check.detail == "All pipelines configured"
        assert check.severity == "medium"

    def test_with_severity(self):
        check = RehearsalCheck(
            name="Security", passed=False, detail="Missing HTTPS", severity="critical"
        )
        assert check.severity == "critical"
        assert check.passed is False

    def test_to_dict(self):
        check = RehearsalCheck(
            name="Database", passed=True, detail="Migrations ready", severity="high"
        )
        d = check.to_dict()
        assert d["name"] == "Database"
        assert d["passed"] is True
        assert d["detail"] == "Migrations ready"
        assert d["severity"] == "high"

    def test_to_dict_all_fields(self):
        check = RehearsalCheck(name="N", passed=False, detail="D", severity="low")
        d = check.to_dict()
        assert set(d.keys()) == {"name", "passed", "detail", "severity"}


# ---------------------------------------------------------------------------
# RehearsalResult
# ---------------------------------------------------------------------------


class TestRehearsalResult:
    def test_empty_result(self):
        result = RehearsalResult(project_name="test")
        assert result.project_name == "test"
        assert result.score == 0
        assert result.passed is False
        assert result.failed_checks == []
        assert result.threshold == 80

    def test_all_passed(self):
        result = RehearsalResult(
            project_name="test",
            checks=[
                RehearsalCheck(name="CI", passed=True, detail="ok", severity="high"),
                RehearsalCheck(name="DB", passed=True, detail="ok", severity="medium"),
                RehearsalCheck(name="Security", passed=True, detail="ok", severity="critical"),
            ],
        )
        assert result.score == 100
        assert result.passed is True
        assert len(result.failed_checks) == 0

    def test_all_failed(self):
        result = RehearsalResult(
            project_name="test",
            checks=[
                RehearsalCheck(name="CI", passed=False, detail="missing", severity="high"),
                RehearsalCheck(name="DB", passed=False, detail="missing", severity="medium"),
            ],
        )
        assert result.score == 0
        assert result.passed is False
        assert len(result.failed_checks) == 2

    def test_partial_pass(self):
        result = RehearsalResult(
            project_name="test",
            checks=[
                RehearsalCheck(name="CI", passed=True, detail="ok", severity="high"),
                RehearsalCheck(name="DB", passed=False, detail="missing", severity="low"),
            ],
        )
        assert 0 < result.score < 100
        assert len(result.failed_checks) == 1
        assert result.failed_checks[0].name == "DB"

    def test_critical_failure_blocks_pass(self):
        result = RehearsalResult(
            project_name="test",
            threshold=50,
            checks=[
                RehearsalCheck(name="CI", passed=True, detail="ok", severity="high"),
                RehearsalCheck(name="Security", passed=False, detail="vuln", severity="critical"),
                RehearsalCheck(name="DB", passed=True, detail="ok", severity="medium"),
                RehearsalCheck(name="Tests", passed=True, detail="ok", severity="medium"),
            ],
        )
        # Even if score > threshold, critical failure should block
        assert result.passed is False

    def test_score_weighting(self):
        # critical=4, high=3, medium=2, low=1
        result = RehearsalResult(
            project_name="test",
            checks=[
                RehearsalCheck(name="Critical", passed=True, detail="ok", severity="critical"),
                RehearsalCheck(name="Low", passed=False, detail="fail", severity="low"),
            ],
        )
        # weight: critical=4, low=1, total=5, passed=4
        assert result.score == 80  # 4/5 * 100

    def test_score_with_unknown_severity(self):
        result = RehearsalResult(
            project_name="test",
            checks=[
                RehearsalCheck(name="Custom", passed=True, detail="ok", severity="unknown"),
            ],
        )
        # Unknown severity defaults to weight 2
        assert result.score == 100

    def test_threshold_custom(self):
        result = RehearsalResult(
            project_name="test",
            threshold=90,
            checks=[
                RehearsalCheck(name="CI", passed=True, detail="ok", severity="medium"),
                RehearsalCheck(name="DB", passed=False, detail="fail", severity="low"),
            ],
        )
        # weight: medium=2+low=1=3, passed=2, score=67
        assert result.score < 90
        assert result.passed is False

    def test_to_dict(self):
        result = RehearsalResult(
            project_name="myapp",
            checks=[
                RehearsalCheck(name="CI", passed=True, detail="ok"),
                RehearsalCheck(name="DB", passed=False, detail="fail"),
            ],
        )
        d = result.to_dict()
        assert d["project_name"] == "myapp"
        assert "score" in d
        assert "passed" in d
        assert "threshold" in d
        assert "failed_checks" in d
        assert "checks" in d
        assert len(d["checks"]) == 2
        assert d["failed_checks"] == ["DB"]

    def test_to_dict_empty(self):
        result = RehearsalResult(project_name="empty")
        d = result.to_dict()
        assert d["score"] == 0
        assert d["passed"] is False
        assert d["failed_checks"] == []
        assert d["checks"] == []

    def test_generated_at_is_set(self):
        result = RehearsalResult(project_name="test")
        assert result.generated_at is not None
        assert "T" in result.generated_at  # ISO format

    def test_many_checks(self):
        checks = [
            RehearsalCheck(
                name=f"check-{i}", passed=(i % 3 != 0), detail=f"detail-{i}", severity="medium"
            )
            for i in range(30)
        ]
        result = RehearsalResult(project_name="big", checks=checks)
        assert 0 <= result.score <= 100

    def test_score_all_critical_passed(self):
        result = RehearsalResult(
            project_name="test",
            checks=[
                RehearsalCheck(name=f"C{i}", passed=True, detail="ok", severity="critical")
                for i in range(5)
            ],
        )
        assert result.score == 100
        assert result.passed is True

    def test_score_all_low_failed(self):
        result = RehearsalResult(
            project_name="test",
            threshold=10,
            checks=[
                RehearsalCheck(name=f"L{i}", passed=False, detail="fail", severity="low")
                for i in range(5)
            ],
        )
        assert result.score == 0
        assert result.passed is False


# ---------------------------------------------------------------------------
# RehearsalResult - severity weight
# ---------------------------------------------------------------------------


class TestSeverityWeight:
    def test_critical_weight(self):
        result = RehearsalResult(project_name="test")
        assert result._weight("critical") == 4

    def test_high_weight(self):
        result = RehearsalResult(project_name="test")
        assert result._weight("high") == 3

    def test_medium_weight(self):
        result = RehearsalResult(project_name="test")
        assert result._weight("medium") == 2

    def test_low_weight(self):
        result = RehearsalResult(project_name="test")
        assert result._weight("low") == 1

    def test_unknown_weight_defaults(self):
        result = RehearsalResult(project_name="test")
        assert result._weight("unknown") == 2

    def test_empty_string_weight(self):
        result = RehearsalResult(project_name="test")
        assert result._weight("") == 2


# ---------------------------------------------------------------------------
# RehearsalResult - failed_checks
# ---------------------------------------------------------------------------


class TestFailedChecks:
    def test_no_failures(self):
        result = RehearsalResult(
            project_name="test",
            checks=[RehearsalCheck(name="OK", passed=True, detail="fine")],
        )
        assert result.failed_checks == []

    def test_all_failures(self):
        result = RehearsalResult(
            project_name="test",
            checks=[
                RehearsalCheck(name="A", passed=False, detail="fail"),
                RehearsalCheck(name="B", passed=False, detail="fail"),
            ],
        )
        assert len(result.failed_checks) == 2

    def test_mixed(self):
        result = RehearsalResult(
            project_name="test",
            checks=[
                RehearsalCheck(name="A", passed=True, detail="ok"),
                RehearsalCheck(name="B", passed=False, detail="fail"),
                RehearsalCheck(name="C", passed=True, detail="ok"),
                RehearsalCheck(name="D", passed=False, detail="fail"),
            ],
        )
        failed_names = [c.name for c in result.failed_checks]
        assert failed_names == ["B", "D"]


# ---------------------------------------------------------------------------
# RehearsalResult - 综合场景
# ---------------------------------------------------------------------------


class TestRehearsalResultScenarios:
    def test_scenario_production_ready(self):
        """Production-ready scenario: all critical/high checks pass"""
        result = RehearsalResult(
            project_name="production",
            threshold=80,
            checks=[
                RehearsalCheck(
                    name="CI/CD Pipeline",
                    passed=True,
                    detail="GitHub Actions configured",
                    severity="critical",
                ),
                RehearsalCheck(
                    name="Health Endpoint",
                    passed=True,
                    detail="/health returns 200",
                    severity="critical",
                ),
                RehearsalCheck(
                    name="Database Migrations",
                    passed=True,
                    detail="All migrations applied",
                    severity="high",
                ),
                RehearsalCheck(
                    name="Security Scan",
                    passed=True,
                    detail="No critical vulnerabilities",
                    severity="high",
                ),
                RehearsalCheck(
                    name="Documentation", passed=True, detail="All docs present", severity="medium"
                ),
                RehearsalCheck(
                    name="Performance Test", passed=True, detail="P99 < 500ms", severity="medium"
                ),
                RehearsalCheck(name="Code Coverage", passed=True, detail="> 80%", severity="low"),
                RehearsalCheck(
                    name="Lint Clean", passed=True, detail="No lint errors", severity="low"
                ),
            ],
        )
        assert result.score == 100
        assert result.passed is True
        assert len(result.failed_checks) == 0

    def test_scenario_critical_failure(self):
        """Critical failure blocks deployment regardless of score"""
        result = RehearsalResult(
            project_name="critical-fail",
            threshold=50,
            checks=[
                RehearsalCheck(
                    name="CI/CD", passed=False, detail="Pipeline broken", severity="critical"
                ),
                RehearsalCheck(name="DB", passed=True, detail="ok", severity="high"),
                RehearsalCheck(name="Docs", passed=True, detail="ok", severity="medium"),
                RehearsalCheck(name="Tests", passed=True, detail="ok", severity="medium"),
                RehearsalCheck(name="Lint", passed=True, detail="ok", severity="low"),
            ],
        )
        assert result.passed is False  # Critical failure blocks

    def test_scenario_low_severity_failures_acceptable(self):
        """Low severity failures may still allow passing"""
        result = RehearsalResult(
            project_name="low-fail",
            threshold=70,
            checks=[
                RehearsalCheck(name="CI", passed=True, detail="ok", severity="critical"),
                RehearsalCheck(name="DB", passed=True, detail="ok", severity="high"),
                RehearsalCheck(name="Security", passed=True, detail="ok", severity="high"),
                RehearsalCheck(name="Docs", passed=False, detail="incomplete", severity="low"),
                RehearsalCheck(name="Style", passed=False, detail="needs work", severity="low"),
            ],
        )
        # critical=4, high=3+3=6, low=1+1=2, total=12, passed=10
        # score = 10/12 * 100 = 83
        assert result.score > 70
        assert result.passed is True

    def test_scenario_borderline_score(self):
        """Score exactly at threshold"""
        result = RehearsalResult(
            project_name="borderline",
            threshold=80,
            checks=[
                RehearsalCheck(name="A", passed=True, detail="ok", severity="critical"),  # 4
                RehearsalCheck(name="B", passed=False, detail="fail", severity="low"),  # 1
            ],
        )
        # total=5, passed=4, score=80
        assert result.score == 80
        assert result.passed is True

    def test_scenario_just_below_threshold(self):
        """Score just below threshold"""
        result = RehearsalResult(
            project_name="below",
            threshold=80,
            checks=[
                RehearsalCheck(name="A", passed=True, detail="ok", severity="high"),  # 3
                RehearsalCheck(name="B", passed=False, detail="fail", severity="medium"),  # 2
            ],
        )
        # total=5, passed=3, score=60
        assert result.score == 60
        assert result.passed is False

    def test_to_dict_comprehensive(self):
        result = RehearsalResult(
            project_name="comprehensive",
            threshold=85,
            checks=[
                RehearsalCheck(name="CI", passed=True, detail="configured", severity="critical"),
                RehearsalCheck(
                    name="DB", passed=False, detail="missing migrations", severity="high"
                ),
                RehearsalCheck(name="Docs", passed=True, detail="complete", severity="low"),
            ],
        )
        d = result.to_dict()
        assert d["project_name"] == "comprehensive"
        assert d["threshold"] == 85
        assert isinstance(d["score"], int)
        assert isinstance(d["passed"], bool)
        assert "DB" in d["failed_checks"]
        assert "CI" not in d["failed_checks"]
        assert len(d["checks"]) == 3
        for check in d["checks"]:
            assert "name" in check
            assert "passed" in check
            assert "detail" in check
            assert "severity" in check
