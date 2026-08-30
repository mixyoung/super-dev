"""
红队审查器测试
"""

from pathlib import Path

from super_dev.reviewers.redteam import ArchitectureIssue, RedTeamReport, RedTeamReviewer


class TestRedTeamReviewer:
    def test_report_passed_property_and_blocking_reasons(self):
        report = RedTeamReport(project_name="demo")
        report.architecture_issues.append(
            ArchitectureIssue(
                severity="high",
                category="可维护性",
                description="缺少测试目录",
                recommendation="补齐测试目录",
            )
        )

        assert report.total_score == 92
        assert report.passed
        assert report.blocking_reasons == []

        report.architecture_issues.append(
            ArchitectureIssue(
                severity="critical",
                category="可靠性",
                description="关键链路无熔断",
                recommendation="补齐熔断机制",
            )
        )
        assert not report.passed
        assert any("critical" in reason for reason in report.blocking_reasons)

    def test_detects_hardcoded_secret_and_shell_true(self, temp_project_dir: Path):
        src_dir = temp_project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "app.py").write_text(
            """
import subprocess

API_KEY = "sk_live_real_secret_123456"

def run_cmd(user_input: str):
    return subprocess.run(f"echo {user_input}", shell=True)
""",
            encoding="utf-8",
        )

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "python", "frontend": "none"},
        )
        report = reviewer.review()

        categories = {i.category for i in report.security_issues}
        assert "硬编码凭据" in categories
        assert "命令执行" in categories
        assert any("app.py:" in i.description for i in report.security_issues)

    def test_ignores_security_signals_inside_test_files(self, temp_project_dir: Path):
        src_dir = temp_project_dir / "src"
        tests_dir = temp_project_dir / "tests"
        src_dir.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)

        (src_dir / "app.py").write_text("def health():\n    return 'ok'\n", encoding="utf-8")
        (tests_dir / "test_vulnerable.py").write_text(
            """
import subprocess

API_KEY = "sk_live_real_secret_123456"

def test_case():
    return subprocess.run("echo test", shell=True)
""",
            encoding="utf-8",
        )

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "python", "frontend": "none"},
        )
        report = reviewer.review()
        categories = {i.category for i in report.security_issues}
        assert "硬编码凭据" not in categories
        assert "命令执行" not in categories

    def test_ignores_placeholder_secrets(self, temp_project_dir: Path):
        src_dir = temp_project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "config.py").write_text(
            """
API_KEY = "your-api-key"
PASSWORD = "placeholder"
""",
            encoding="utf-8",
        )

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "none", "frontend": "none"},
        )
        report = reviewer.review()

        assert not any(i.category == "硬编码凭据" for i in report.security_issues)

    def test_detects_async_requests_and_n_plus_one(self, temp_project_dir: Path):
        src_dir = temp_project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "perf.py").write_text(
            """
import requests

async def fetch_data():
    return requests.get("https://example.com/api")

def load_users(users, db):
    for user in users:
        db.query("select * from orders where user_id=" + str(user.id))
""",
            encoding="utf-8",
        )

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "python", "frontend": "none"},
        )
        report = reviewer.review()

        assert any(
            i.category == "API" and "perf.py:" in i.description for i in report.performance_issues
        )
        assert any(
            i.category == "数据库" and "perf.py:" in i.description
            for i in report.performance_issues
        )

    def test_architecture_flags_missing_tests_ci_and_large_file(self, temp_project_dir: Path):
        src_dir = temp_project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "huge.py").write_text(
            "\n".join(["print('x')"] * 2105),
            encoding="utf-8",
        )

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "python", "frontend": "none"},
        )
        report = reviewer.review()

        assert any("tests 目录" in i.description for i in report.architecture_issues)
        assert any("CI/CD" in i.description for i in report.architecture_issues)
        assert any("超大单体文件" in i.description for i in report.architecture_issues)

    def test_architecture_recognizes_js_test_assets(self, temp_project_dir: Path):
        backend_src = temp_project_dir / "backend" / "src"
        backend_src.mkdir(parents=True, exist_ok=True)
        (backend_src / "app.test.js").write_text("test('ok', () => {})\n", encoding="utf-8")

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "node", "frontend": "react"},
        )
        report = reviewer.review()

        assert not any("tests 目录" in i.description for i in report.architecture_issues)

    def test_fallback_scan_project_root_files(self, temp_project_dir: Path):
        (temp_project_dir / "main.py").write_text(
            'token = "real_token_abcdef123456"\n',
            encoding="utf-8",
        )

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "none", "frontend": "none"},
        )
        report = reviewer.review()

        assert any(i.category == "硬编码凭据" for i in report.security_issues)

    def test_optional_bandit_scan_adds_security_issue(self, temp_project_dir: Path, monkeypatch):
        src_dir = temp_project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "app.py").write_text("print('hello')\n", encoding="utf-8")

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "python", "frontend": "none"},
        )

        monkeypatch.setattr(
            "super_dev.reviewers.redteam.shutil.which",
            lambda cmd: "/usr/bin/bandit" if cmd == "bandit" else None,
        )
        monkeypatch.setattr(
            reviewer,
            "_run_command",
            lambda cmd, timeout=120: {
                "returncode": 1,
                "stdout": (
                    '{"results":[{"filename":"src/app.py","line_number":7,'
                    '"issue_text":"Possible command injection","issue_severity":"HIGH",'
                    '"issue_cwe":{"id":78}}]}'
                ),
                "stderr": "",
                "timed_out": False,
            },
        )
        monkeypatch.setattr(reviewer, "_scan_with_semgrep", lambda: [])
        monkeypatch.setattr(reviewer, "_scan_with_npm_audit", lambda: [])

        report = reviewer.review()
        assert any(i.category == "Bandit" and i.cwe == "CWE-78" for i in report.security_issues)

    def test_optional_npm_audit_adds_dependency_issue(self, temp_project_dir: Path, monkeypatch):
        frontend = temp_project_dir / "frontend"
        frontend.mkdir(parents=True, exist_ok=True)
        (frontend / "package.json").write_text('{"name":"frontend"}', encoding="utf-8")

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"backend": "node", "frontend": "react"},
        )

        monkeypatch.setattr(
            "super_dev.reviewers.redteam.shutil.which",
            lambda cmd: "/usr/bin/npm" if cmd == "npm" else None,
        )
        monkeypatch.setattr(
            reviewer,
            "_run_command",
            lambda cmd, timeout=120: {
                "returncode": 1,
                "stdout": '{"metadata":{"vulnerabilities":{"critical":0,"high":2}}}',
                "stderr": "",
                "timed_out": False,
            },
        )

        issues = reviewer._scan_with_npm_audit()
        assert any(i.category == "依赖漏洞" and i.severity == "high" for i in issues)

    def test_inactive_node_scaffolds_are_outside_python_cli_release_surface(
        self, temp_project_dir: Path, monkeypatch
    ):
        frontend = temp_project_dir / "frontend"
        backend = temp_project_dir / "backend"
        frontend.mkdir(parents=True, exist_ok=True)
        (backend / "src").mkdir(parents=True, exist_ok=True)
        (frontend / "package.json").write_text('{"name":"legacy-frontend"}', encoding="utf-8")
        (frontend / "app.tsx").write_text('const token = "legacy-secret";\n', encoding="utf-8")
        (backend / "package.json").write_text('{"name":"legacy-backend"}', encoding="utf-8")
        (backend / "src" / "app.js").write_text(
            "res.header('Access-Control-Allow-Origin', '*');\n",
            encoding="utf-8",
        )

        reviewer = RedTeamReviewer(
            project_dir=temp_project_dir,
            name="demo",
            tech_stack={"platform": "cli", "backend": "python", "frontend": "none"},
        )
        reviewer.enable_tool_scans = False
        monkeypatch.setattr(
            "super_dev.reviewers.redteam.shutil.which",
            lambda cmd: "/usr/bin/npm" if cmd == "npm" else None,
        )

        def fail_if_npm_runs(cmd, timeout=120):
            raise AssertionError("inactive npm project must not be audited")

        monkeypatch.setattr(reviewer, "_run_command", fail_if_npm_runs)

        assert reviewer._find_package_json_files() == []
        assert reviewer._scan_with_npm_audit() == []
        report = reviewer.review()

        assert report.scanned_files_count == 0
        assert not any(
            issue.category == "CORS 配置" and issue.severity == "high"
            for issue in report.security_issues
        )
        assert not any(issue.category == "硬编码凭据" for issue in report.security_issues)
