# ruff: noqa: I001
"""
红队审查器增强测试 - 覆盖依赖安全、API 安全、密钥泄漏、声明式规则、0 文件场景

测试对象: super_dev.reviewers.redteam
"""

import json
import textwrap
from pathlib import Path

import pytest
from super_dev.reviewers.redteam import (
    ArchitectureIssue,
    PerformanceIssue,
    RedTeamReport,
    RedTeamReviewer,
    SecurityIssue,
    load_persisted_redteam_report,
    load_redteam_evidence,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_project(tmp_path):
    """一个空项目目录（无源码文件）"""
    (tmp_path / "super-dev.yaml").write_text("name: empty\nversion: '1.0.0'\n")
    return tmp_path


@pytest.fixture()
def basic_project(tmp_path):
    """包含基本源码文件的项目目录"""
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text(textwrap.dedent("""\
        from fastapi import FastAPI

        app = FastAPI()

        @app.get("/health")
        def health():
            return {"status": "ok"}
    """))
    (tmp_path / "super-dev.yaml").write_text("name: basic\nversion: '1.0.0'\n")
    return tmp_path


@pytest.fixture()
def insecure_project(tmp_path):
    """包含安全问题的项目目录"""
    src = tmp_path / "backend"
    src.mkdir()
    (src / "app.py").write_text(textwrap.dedent("""\
        import subprocess
        import os

        API_KEY = "sk-hardcoded-secret-value-1234567890"

        def run_cmd(user_input):
            subprocess.run(user_input, shell=True)

        def execute(code):
            result = eval(code)
            return result

        def get_user(name):
            query = "select * from users where name = '" + name + "'"
            return query
    """))
    (tmp_path / "super-dev.yaml").write_text("name: insecure\nversion: '1.0.0'\n")
    return tmp_path


@pytest.fixture()
def fintech_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('fintech app')\n")
    return tmp_path


@pytest.fixture()
def medical_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('medical app')\n")
    return tmp_path


def _make_reviewer(project_dir, name="test", **overrides):
    tech_stack = {
        "platform": "web",
        "frontend": "react",
        "backend": "node",
        "domain": "",
    }
    tech_stack.update(overrides)
    reviewer = RedTeamReviewer(project_dir, name, tech_stack)
    reviewer.enable_tool_scans = False
    return reviewer


# ---------------------------------------------------------------------------
# SecurityIssue / PerformanceIssue / ArchitectureIssue 数据类
# ---------------------------------------------------------------------------


class TestSecurityIssueDataclass:
    def test_to_dict_and_from_dict_roundtrip(self):
        issue = SecurityIssue(
            severity="high",
            category="injection",
            description="SQL injection detected",
            recommendation="Use parameterized queries",
            cwe="CWE-89",
            file_path="/app/src/db.py",
            line=42,
        )
        d = issue.to_dict()
        restored = SecurityIssue.from_dict(d)
        assert restored.severity == "high"
        assert restored.cwe == "CWE-89"
        assert restored.line == 42

    def test_from_dict_handles_missing_optional_fields(self):
        issue = SecurityIssue.from_dict({"severity": "low", "category": "xss"})
        assert issue.cwe is None
        assert issue.file_path is None
        assert issue.line is None

    def test_from_dict_handles_none_values(self):
        issue = SecurityIssue.from_dict(
            {
                "severity": "medium",
                "category": "auth",
                "description": "weak auth",
                "recommendation": "fix",
                "cwe": None,
                "file_path": None,
                "line": None,
            }
        )
        assert issue.cwe is None
        assert issue.file_path is None


class TestPerformanceIssueDataclass:
    def test_roundtrip(self):
        issue = PerformanceIssue(
            severity="high",
            category="database",
            description="N+1 query",
            recommendation="Use eager loading",
            impact="Slow response",
            file_path="/app/models.py",
            line=10,
        )
        d = issue.to_dict()
        restored = PerformanceIssue.from_dict(d)
        assert restored.impact == "Slow response"
        assert restored.line == 10

    def test_default_impact_is_empty_string(self):
        issue = PerformanceIssue(
            severity="low", category="api", description="d", recommendation="r"
        )
        assert issue.impact == ""


class TestArchitectureIssueDataclass:
    def test_roundtrip(self):
        issue = ArchitectureIssue(
            severity="critical",
            category="scalability",
            description="Monolith",
            recommendation="Split services",
            adr_needed=True,
            file_path="/app/main.py",
            line=1,
        )
        d = issue.to_dict()
        restored = ArchitectureIssue.from_dict(d)
        assert restored.adr_needed is True


# ---------------------------------------------------------------------------
# RedTeamReport 属性和方法
# ---------------------------------------------------------------------------


class TestRedTeamReport:
    def test_empty_report_scores_100(self):
        report = RedTeamReport(project_name="test")
        assert report.total_score == 100
        assert report.critical_count == 0
        assert report.passed is True

    def test_critical_security_issue_deducts_20(self):
        report = RedTeamReport(
            project_name="test",
            security_issues=[SecurityIssue("critical", "injection", "desc", "rec")],
        )
        assert report.total_score == 80
        assert report.critical_count == 1
        assert report.passed is False

    def test_high_security_issue_deducts_10(self):
        report = RedTeamReport(
            project_name="test",
            security_issues=[SecurityIssue("high", "xss", "desc", "rec")],
        )
        assert report.total_score == 90

    def test_medium_security_deducts_5(self):
        report = RedTeamReport(
            project_name="test",
            security_issues=[SecurityIssue("medium", "csrf", "desc", "rec")],
        )
        assert report.total_score == 95

    def test_low_security_deducts_2(self):
        report = RedTeamReport(
            project_name="test",
            security_issues=[SecurityIssue("low", "misc", "desc", "rec")],
        )
        assert report.total_score == 98

    def test_repeated_low_heuristics_have_bounded_score_impact(self):
        report = RedTeamReport(
            project_name="test",
            security_issues=[
                SecurityIssue("low", "version-range", f"desc-{index}", "rec") for index in range(20)
            ],
            performance_issues=[
                PerformanceIssue("low", "n-plus-one", f"desc-{index}", "rec") for index in range(20)
            ],
        )

        assert len(report.security_issues) == 20
        assert len(report.performance_issues) == 20
        assert report.total_score == 91

    def test_performance_deduction_scales(self):
        report = RedTeamReport(
            project_name="test",
            performance_issues=[
                PerformanceIssue("critical", "db", "d", "r"),
                PerformanceIssue("high", "api", "d", "r"),
                PerformanceIssue("medium", "fe", "d", "r"),
                PerformanceIssue("low", "infra", "d", "r"),
            ],
        )
        assert report.total_score == 100 - 15 - 8 - 4 - 1

    def test_architecture_deduction_scales(self):
        report = RedTeamReport(
            project_name="test",
            architecture_issues=[
                ArchitectureIssue("critical", "scale", "d", "r"),
                ArchitectureIssue("high", "maintain", "d", "r"),
                ArchitectureIssue("medium", "reliability", "d", "r"),
                ArchitectureIssue("low", "style", "d", "r"),
            ],
        )
        assert report.total_score == 100 - 15 - 8 - 4 - 1

    def test_score_floors_at_zero(self):
        issues = [SecurityIssue("critical", "cat", "d", "r") for _ in range(10)]
        report = RedTeamReport(project_name="test", security_issues=issues)
        assert report.total_score == 0

    def test_passed_requires_no_critical_and_threshold(self):
        report = RedTeamReport(
            project_name="test",
            pass_threshold=90,
            security_issues=[
                SecurityIssue("high", "xss", "d", "r"),
                SecurityIssue("high", "csrf", "d", "r"),
            ],
        )
        assert report.total_score == 80
        assert report.passed is False

    def test_blocking_reasons_lists_critical_and_score(self):
        report = RedTeamReport(
            project_name="test",
            pass_threshold=90,
            security_issues=[SecurityIssue("critical", "cat", "d", "r")],
        )
        reasons = report.blocking_reasons
        assert len(reasons) == 2

    def test_to_markdown_contains_key_sections(self):
        report = RedTeamReport(
            project_name="test-project",
            security_issues=[
                SecurityIssue("high", "injection", "SQL injection found", "Fix it", cwe="CWE-89")
            ],
            performance_issues=[
                PerformanceIssue("medium", "db", "Slow query", "Add index", "500ms p99")
            ],
            architecture_issues=[
                ArchitectureIssue("low", "style", "Code smells", "Refactor", adr_needed=True)
            ],
        )
        md = report.to_markdown()
        assert "test-project" in md
        assert "安全审查" in md
        assert "性能审查" in md
        assert "架构审查" in md
        assert "CWE-89" in md

    def test_to_markdown_zero_files_shows_baseline_message(self):
        report = RedTeamReport(project_name="empty", scanned_files_count=0)
        md = report.to_markdown()
        assert "待代码实现后重新审查" in md

    def test_to_markdown_declarative_rules_section(self):
        report = RedTeamReport(
            project_name="test",
            security_issues=[
                SecurityIssue(
                    "high",
                    "hardcoded",
                    "[RT-SEC-001] Hardcoded secret found: app.py:5",
                    "Use env vars",
                    cwe="CWE-798",
                )
            ],
        )
        md = report.to_markdown()
        assert "声明式规则检测结果" in md
        assert "RT-SEC-001" in md

    def test_to_dict_and_from_dict_roundtrip(self):
        report = RedTeamReport(
            project_name="roundtrip",
            pass_threshold=80,
            scanned_files_count=42,
            security_issues=[SecurityIssue("high", "cat", "d", "r")],
            performance_issues=[PerformanceIssue("medium", "db", "d", "r")],
            architecture_issues=[ArchitectureIssue("low", "m", "d", "r")],
        )
        d = report.to_dict()
        restored = RedTeamReport.from_dict(d)
        assert restored.project_name == "roundtrip"
        assert restored.pass_threshold == 80
        assert restored.scanned_files_count == 42
        assert len(restored.security_issues) == 1

    def test_from_dict_skips_non_dict_issues(self):
        payload = {
            "project_name": "test",
            "security_issues": [
                {"severity": "low", "category": "a", "description": "b", "recommendation": "c"},
                "invalid",
            ],
            "performance_issues": [],
            "architecture_issues": [],
        }
        report = RedTeamReport.from_dict(payload)
        assert len(report.security_issues) == 1

    def test_from_dict_default_values(self):
        report = RedTeamReport.from_dict({})
        assert report.project_name == ""
        assert report.pass_threshold == 70

    def test_markdown_conditional_pass(self):
        # Score 75: 100 - 10 - 10 - 5 = 75, which is < 80 -> conditional pass
        report = RedTeamReport(
            project_name="conditional",
            security_issues=[
                SecurityIssue("high", "xss", "XSS found", "Fix"),
                SecurityIssue("high", "auth", "Weak", "Fix"),
                SecurityIssue("medium", "csrf", "CSRF", "Fix"),
            ],
        )
        md = report.to_markdown()
        assert report.total_score == 75
        assert "有条件通过" in md

    def test_markdown_with_p1_issues(self):
        report = RedTeamReport(
            project_name="p1-test",
            security_issues=[SecurityIssue("medium", "csrf", "CSRF missing", "Add token")],
        )
        md = report.to_markdown()
        assert "P1" in md

    def test_markdown_with_only_low_issues(self):
        report = RedTeamReport(
            project_name="low-only",
            security_issues=[SecurityIssue("low", "misc", "Minor issue", "Consider fixing")],
        )
        md = report.to_markdown()
        assert "无 P0" in md


# ---------------------------------------------------------------------------
# 密钥泄漏深度扫描
# ---------------------------------------------------------------------------


class TestSecretLeakDetection:
    def test_detects_hardcoded_api_key(self, insecure_project):
        reviewer = _make_reviewer(insecure_project, name="insecure")
        issues = reviewer._review_security()
        secret_issues = [i for i in issues if "硬编码" in i.category or "硬编码" in i.description]
        assert len(secret_issues) >= 1

    def test_ignores_placeholder_values(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "config.py").write_text('API_KEY = "your_api_key_here"\nSECRET = "change_me"\n')
        reviewer = _make_reviewer(tmp_path)
        issues = reviewer._review_security()
        secret_issues = [i for i in issues if "硬编码" in i.category]
        assert len(secret_issues) == 0

    def test_color_parser_token_is_not_reported_as_credential(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "colors.py").write_text(textwrap.dedent("""\
                def dart_color(hex_color):
                    token = str(hex_color).lstrip("#")
                    if len(token) != 6:
                        token = "0F7CFA"
                    return f"0xFF{token.upper()}"
                """))
        (src / "config.py").write_text('token = "A1B2C3"\n')
        reviewer = _make_reviewer(tmp_path)

        issues = reviewer._review_security()
        credential_paths = {
            Path(issue.file_path).name
            for issue in issues
            if issue.category == "硬编码凭据" and issue.file_path
        }

        assert "colors.py" not in credential_paths
        assert "config.py" in credential_paths

    def test_detects_eval_usage(self, insecure_project):
        reviewer = _make_reviewer(insecure_project, name="insecure")
        issues = reviewer._review_security()
        eval_issues = [i for i in issues if "动态执行" in i.category]
        assert len(eval_issues) >= 1

    def test_detects_shell_true(self, insecure_project):
        reviewer = _make_reviewer(insecure_project, name="insecure")
        issues = reviewer._review_security()
        cmd_issues = [i for i in issues if "命令执行" in i.category]
        assert len(cmd_issues) >= 1

    def test_detects_sql_injection_pattern(self, insecure_project):
        reviewer = _make_reviewer(insecure_project, name="insecure")
        issues = reviewer._review_security()
        sql_issues = [i for i in issues if "SQL" in i.category]
        assert len(sql_issues) >= 1


# ---------------------------------------------------------------------------
# API 安全扫描
# ---------------------------------------------------------------------------


class TestAPISecurityScan:
    def test_backend_gets_auth_baseline(self, basic_project):
        reviewer = _make_reviewer(basic_project, backend="fastapi")
        issues = reviewer._review_security()
        auth_issues = [i for i in issues if i.category == "认证"]
        assert len(auth_issues) >= 1

    def test_backend_gets_rate_limit(self, basic_project):
        reviewer = _make_reviewer(basic_project, backend="node")
        issues = reviewer._review_security()
        rate_issues = [i for i in issues if "速率限制" in i.category]
        assert len(rate_issues) >= 1

    def test_no_backend_skips_baseline(self, basic_project):
        reviewer = _make_reviewer(basic_project, backend="none")
        issues = reviewer._review_security()
        auth_issues = [i for i in issues if i.category == "认证"]
        assert len(auth_issues) == 0

    def test_fintech_adds_pci_dss(self, fintech_project):
        reviewer = _make_reviewer(fintech_project, domain="fintech")
        issues = reviewer._review_security()
        pci_issues = [i for i in issues if "PCI" in i.category]
        assert len(pci_issues) >= 1

    def test_fintech_adds_audit(self, fintech_project):
        reviewer = _make_reviewer(fintech_project, domain="fintech")
        issues = reviewer._review_security()
        audit_issues = [i for i in issues if "审计" in i.category]
        assert len(audit_issues) >= 1

    def test_medical_adds_hipaa(self, medical_project):
        reviewer = _make_reviewer(medical_project, domain="medical")
        issues = reviewer._review_security()
        hipaa_issues = [i for i in issues if "HIPAA" in i.category]
        assert len(hipaa_issues) >= 1


# ---------------------------------------------------------------------------
# 声明式规则
# ---------------------------------------------------------------------------


class TestDeclarativeRules:
    def test_scan_returns_empty_when_no_rules(self, basic_project):
        reviewer = _make_reviewer(basic_project)
        reviewer._redteam_rules = []
        sec, perf, arch = reviewer._scan_declarative_rules()
        assert sec == [] and perf == [] and arch == []

    def test_scan_matches_security_pattern(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("password = 'hardcoded123'\n")
        reviewer = _make_reviewer(tmp_path)
        reviewer._redteam_rules = [
            {
                "id": "RT-SEC-TEST",
                "name": "Test Secret Rule",
                "severity": "high",
                "category": "security",
                "description": "Test hardcoded password",
                "recommendation": "Use env vars",
                "patterns": [r"password\s*=\s*['\"]"],
                "cwe": "CWE-798",
            }
        ]
        sec, perf, arch = reviewer._scan_declarative_rules()
        assert len(sec) >= 1
        assert "RT-SEC-TEST" in sec[0].description

    def test_scan_matches_performance_category(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "worker.py").write_text("import time\ntime.sleep(60)\n")
        reviewer = _make_reviewer(tmp_path)
        reviewer._redteam_rules = [
            {
                "id": "RT-PERF-001",
                "name": "Long sleep",
                "severity": "medium",
                "category": "performance",
                "description": "Long sleep detected",
                "recommendation": "Use async timers",
                "patterns": [r"time\.sleep\(\d{2,}\)"],
            }
        ]
        sec, perf, arch = reviewer._scan_declarative_rules()
        assert len(perf) >= 1

    def test_scan_matches_architecture_category(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "god_class.py").write_text("class GodObject:\n    pass\n")
        reviewer = _make_reviewer(tmp_path)
        reviewer._redteam_rules = [
            {
                "id": "RT-ARCH-001",
                "name": "God class",
                "severity": "medium",
                "category": "architecture",
                "description": "God class detected",
                "recommendation": "Split class",
                "patterns": [r"class GodObject"],
            }
        ]
        sec, perf, arch = reviewer._scan_declarative_rules()
        assert len(arch) >= 1

    def test_file_line_count_check_type(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "big.py").write_text("\n".join([f"line_{i} = {i}" for i in range(600)]))
        reviewer = _make_reviewer(tmp_path)
        reviewer._redteam_rules = [
            {
                "id": "RT-ARCH-SIZE",
                "name": "File too large",
                "severity": "medium",
                "category": "architecture",
                "description": "File exceeds max lines",
                "recommendation": "Split file",
                "check_type": "file_line_count",
                "check_config": {"max_lines": 500},
            }
        ]
        sec, perf, arch = reviewer._scan_declarative_rules()
        assert len(arch) >= 1

    def test_expert_rules_filter_active_rule_ids(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("eval('code')\n")
        reviewer = _make_reviewer(tmp_path)
        reviewer._redteam_rules = [
            {
                "id": "RT-SEC-ACTIVE",
                "name": "Active",
                "severity": "high",
                "category": "security",
                "description": "Active",
                "recommendation": "Fix",
                "patterns": [r"eval\("],
            },
            {
                "id": "RT-SEC-INACTIVE",
                "name": "Inactive",
                "severity": "high",
                "category": "security",
                "description": "Inactive",
                "recommendation": "Fix",
                "patterns": [r"eval\("],
            },
        ]
        reviewer._expert_rules = ["RT-SEC-ACTIVE"]
        sec, perf, arch = reviewer._scan_declarative_rules()
        assert all("RT-SEC-ACTIVE" in i.description for i in sec)

    def test_invalid_regex_skipped_gracefully(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("some code\n")
        reviewer = _make_reviewer(tmp_path)
        reviewer._redteam_rules = [
            {
                "id": "RT-BAD",
                "name": "Bad regex",
                "severity": "low",
                "category": "security",
                "description": "Bad",
                "recommendation": "Fix",
                "patterns": ["[invalid(regex"],
            }
        ]
        sec, perf, arch = reviewer._scan_declarative_rules()
        assert sec == []

    def test_each_rule_reported_once_per_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("eval('a')\neval('b')\neval('c')\n")
        reviewer = _make_reviewer(tmp_path)
        reviewer._redteam_rules = [
            {
                "id": "RT-DEDUP",
                "name": "Dedup test",
                "severity": "high",
                "category": "security",
                "description": "Dedup",
                "recommendation": "Fix",
                "patterns": [r"eval\("],
            }
        ]
        sec, _, _ = reviewer._scan_declarative_rules()
        assert len(sec) == 1


# ---------------------------------------------------------------------------
# 0 文件场景
# ---------------------------------------------------------------------------


class TestZeroFilesScenario:
    def test_empty_project_produces_report(self, empty_project):
        reviewer = _make_reviewer(empty_project, name="empty")
        report = reviewer.review()
        assert isinstance(report, RedTeamReport)
        assert report.scanned_files_count == 0

    def test_empty_project_markdown_mentions_no_source(self, empty_project):
        reviewer = _make_reviewer(empty_project, name="empty")
        report = reviewer.review()
        md = report.to_markdown()
        assert "待代码实现后重新审查" in md

    def test_empty_project_score_reflects_baseline_only(self, empty_project):
        reviewer = _make_reviewer(empty_project, name="empty", backend="none")
        report = reviewer.review()
        assert report.total_score >= 80


# ---------------------------------------------------------------------------
# 完整审查流程
# ---------------------------------------------------------------------------


class TestFullReview:
    def test_review_returns_all_issue_categories(self, basic_project):
        reviewer = _make_reviewer(basic_project, name="basic")
        report = reviewer.review()
        assert isinstance(report.security_issues, list)
        assert isinstance(report.performance_issues, list)
        assert isinstance(report.architecture_issues, list)

    def test_review_detects_missing_tests(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')\n")
        reviewer = _make_reviewer(tmp_path)
        report = reviewer.review()
        test_issues = [
            i
            for i in report.architecture_issues
            if "tests" in i.description.lower() or "测试" in i.description
        ]
        assert len(test_issues) >= 1

    def test_review_detects_missing_ci(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')\n")
        reviewer = _make_reviewer(tmp_path)
        report = reviewer.review()
        ci_issues = [i for i in report.architecture_issues if "CI" in i.description]
        assert len(ci_issues) >= 1

    def test_review_with_ci_present(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')\n")
        gh = tmp_path / ".github" / "workflows"
        gh.mkdir(parents=True)
        (gh / "ci.yml").write_text("name: CI\n")
        reviewer = _make_reviewer(tmp_path)
        report = reviewer.review()
        ci_issues = [i for i in report.architecture_issues if "CI/CD" in i.description]
        assert len(ci_issues) == 0

    def test_large_file_detected(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "huge.py").write_text("\n".join([f"x_{i} = {i}" for i in range(2500)]))
        reviewer = _make_reviewer(tmp_path)
        report = reviewer.review()
        large_issues = [
            i
            for i in report.architecture_issues
            if "超大" in i.description or "大文件" in i.description
        ]
        assert len(large_issues) >= 1


# ---------------------------------------------------------------------------
# 持久化加载
# ---------------------------------------------------------------------------


class TestPersistedRedteamReport:
    def test_load_from_json(self, tmp_path):
        output = tmp_path / "output"
        output.mkdir()
        report = RedTeamReport(project_name="test", pass_threshold=70)
        (output / "test-redteam.json").write_text(json.dumps(report.to_dict(), ensure_ascii=False))
        result = load_persisted_redteam_report(tmp_path, "test")
        assert result is not None
        _, loaded = result
        assert loaded.project_name == "test"

    def test_load_returns_none_when_missing(self, tmp_path):
        (tmp_path / "output").mkdir()
        assert load_persisted_redteam_report(tmp_path, "nonexistent") is None

    def test_load_returns_none_for_invalid_json(self, tmp_path):
        output = tmp_path / "output"
        output.mkdir()
        (output / "broken-redteam.json").write_text("not json")
        assert load_persisted_redteam_report(tmp_path, "broken") is None


class TestRedTeamEvidence:
    def test_load_evidence_from_json(self, tmp_path):
        output = tmp_path / "output"
        output.mkdir()
        report = RedTeamReport(project_name="ev", pass_threshold=70)
        (output / "ev-redteam.json").write_text(json.dumps(report.to_dict(), ensure_ascii=False))
        evidence = load_redteam_evidence(tmp_path, "ev")
        assert evidence is not None
        assert evidence.passed is True
        assert evidence.source_format == "json"

    def test_load_evidence_from_markdown(self, tmp_path):
        output = tmp_path / "output"
        output.mkdir()
        md = textwrap.dedent("""\
            # test - 红队审查报告
            > **总分**: 85/100
            > **通过阈值**: 70
            - **Critical 问题**: 0
            - **High 问题**: 1
            **状态**: 有条件通过 - 建议修复 High 级别问题
        """)
        (output / "test-redteam.md").write_text(md, encoding="utf-8")
        evidence = load_redteam_evidence(tmp_path, "test")
        assert evidence is not None
        assert evidence.total_score == 85
        assert evidence.source_format == "markdown"

    def test_load_evidence_returns_none(self, tmp_path):
        (tmp_path / "output").mkdir()
        assert load_redteam_evidence(tmp_path, "missing") is None


# ---------------------------------------------------------------------------
# Performance review
# ---------------------------------------------------------------------------


class TestPerformanceReview:
    def test_detects_sync_http_in_async(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "worker.py").write_text(textwrap.dedent("""\
            import requests
            async def fetch_data():
                response = requests.get("https://api.example.com")
                return response.json()
        """))
        reviewer = _make_reviewer(tmp_path)
        report = reviewer.review()
        async_issues = [
            i
            for i in report.performance_issues
            if "同步 HTTP" in i.description or "异步" in i.description
        ]
        assert len(async_issues) >= 1

    def test_baseline_db_recommendation(self, basic_project):
        reviewer = _make_reviewer(basic_project, backend="node")
        issues = reviewer._review_performance()
        db_baseline = [i for i in issues if "索引" in i.description or "慢查询" in i.description]
        assert len(db_baseline) >= 1

    def test_baseline_frontend_recommendation(self, basic_project):
        reviewer = _make_reviewer(basic_project, frontend="react")
        issues = reviewer._review_performance()
        fe_baseline = [i for i in issues if "代码分割" in i.description or "缓存" in i.description]
        assert len(fe_baseline) >= 1

    def test_no_frontend_no_fe_recommendation(self, basic_project):
        reviewer = _make_reviewer(basic_project, frontend="none")
        issues = reviewer._review_performance()
        fe_baseline = [i for i in issues if "代码分割" in i.description]
        assert len(fe_baseline) == 0


# ---------------------------------------------------------------------------
# 文件扫描辅助方法
# ---------------------------------------------------------------------------


class TestFileScanningHelpers:
    def test_should_skip_git_dir(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._should_skip_dir(".git") is True

    def test_should_skip_node_modules(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._should_skip_dir("node_modules") is True

    def test_should_not_skip_src(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._should_skip_dir("src") is False

    def test_should_not_skip_github(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._should_skip_dir(".github") is False

    def test_is_scannable_file_py(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._is_scannable_file(Path("app.py")) is True

    def test_is_scannable_file_ts(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._is_scannable_file(Path("app.ts")) is True

    def test_is_not_scannable_file_md(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._is_scannable_file(Path("README.md")) is False

    def test_is_yaml_file(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._is_yaml_file(Path("config.yml")) is True
        assert reviewer._is_yaml_file(Path("app.py")) is False

    def test_is_test_file_python(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._is_test_file(Path("test_main.py")) is True
        assert reviewer._is_test_file(Path("main.py")) is False

    def test_is_test_file_js(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._is_test_file(Path("app.test.ts")) is True
        assert reviewer._is_test_file(Path("app.spec.tsx")) is True

    def test_looks_like_placeholder(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._looks_like_placeholder("your-api-key-here") is True
        assert reviewer._looks_like_placeholder("example-key") is True
        assert reviewer._looks_like_placeholder("changeme") is True
        assert reviewer._looks_like_placeholder("TODO") is True
        assert reviewer._looks_like_placeholder("sk-1234567890abcdef") is False

    def test_line_number_from_offset(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        content = "line1\nline2\nline3\n"
        assert reviewer._line_number_from_offset(content, 0) == 1
        assert reviewer._line_number_from_offset(content, 6) == 2

    def test_iter_source_files_caches_result(self, basic_project):
        reviewer = _make_reviewer(basic_project)
        files1 = reviewer._iter_source_files_with_content()
        files2 = reviewer._iter_source_files_with_content()
        assert files1 is files2

    def test_has_test_assets_with_tests_dir(self, tmp_path):
        (tmp_path / "tests").mkdir()
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._has_test_assets([]) is True

    def test_has_test_assets_without_tests(self, tmp_path):
        reviewer = _make_reviewer(tmp_path)
        assert reviewer._has_test_assets([]) is False


# ---------------------------------------------------------------------------
# Architecture review edge cases
# ---------------------------------------------------------------------------


class TestArchitectureReviewEdgeCases:
    def test_detect_no_health_endpoint(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("print('no health')\n")
        reviewer = _make_reviewer(tmp_path, backend="fastapi")
        report = reviewer.review()
        health_issues = [i for i in report.architecture_issues if "健康检查" in i.description]
        assert len(health_issues) >= 1

    def test_detect_health_endpoint_present(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text('@app.get("/health")\ndef health(): return {"status": "ok"}\n')
        reviewer = _make_reviewer(tmp_path, backend="fastapi")
        report = reviewer.review()
        health_issues = [i for i in report.architecture_issues if "健康检查" in i.description]
        assert len(health_issues) == 0

    def test_no_backend_no_health_issue(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.js").write_text("console.log('frontend only');\n")
        reviewer = _make_reviewer(tmp_path, backend="none")
        report = reviewer.review()
        health_issues = [i for i in report.architecture_issues if "健康检查" in i.description]
        assert len(health_issues) == 0

    def test_tool_scans_env_var(self, basic_project, monkeypatch):
        monkeypatch.setenv("SUPER_DEV_ENABLE_TOOL_SCANS", "0")
        reviewer = RedTeamReviewer(
            basic_project,
            "test",
            {
                "platform": "web",
                "frontend": "react",
                "backend": "node",
            },
        )
        assert reviewer.enable_tool_scans is False

    def test_review_with_multiple_source_files(self, tmp_path):
        src = tmp_path / "backend"
        src.mkdir()
        for i in range(10):
            (src / f"module_{i}.py").write_text(f"def func_{i}(): pass\n")
        reviewer = _make_reviewer(tmp_path)
        report = reviewer.review()
        assert report.scanned_files_count >= 10
