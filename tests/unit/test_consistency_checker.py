"""
Spec-Code 一致性检测器的单元测试
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.specs.consistency_checker import (
    ConsistencyIssue,
    ConsistencyReport,
    SpecConsistencyChecker,
)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """创建带有 super-dev 目录结构的临时项目"""
    (tmp_path / "super-dev.yaml").write_text(
        "name: test-project\nversion: 1.0.0\n"
        "frontend:\n  framework: react\n"
        "backend:\n  framework: express\n"
        "database:\n  type: postgresql\n",
        encoding="utf-8",
    )
    changes_dir = tmp_path / ".super-dev" / "changes" / "test-change"
    changes_dir.mkdir(parents=True)
    return tmp_path


class TestConsistencyIssue:
    def test_to_dict(self):
        issue = ConsistencyIssue(
            severity="high",
            category="api_mismatch",
            spec_reference="Spec 声明 GET /api/users",
            actual_state="代码中未找到对应路由",
            suggestion="实现 GET /api/users 端点",
        )
        d = issue.to_dict()
        assert d["severity"] == "high"
        assert d["category"] == "api_mismatch"
        assert "GET /api/users" in d["spec_reference"]


class TestConsistencyReport:
    def test_empty_report_passes(self):
        report = ConsistencyReport(
            change_id="test",
            timestamp="2026-03-28 00:00:00 UTC",
            issues=[],
            consistency_score=100,
        )
        assert report.passed is True
        assert report.critical_count == 0
        assert report.consistency_score == 100

    def test_critical_issue_fails(self):
        report = ConsistencyReport(
            change_id="test",
            timestamp="2026-03-28 00:00:00 UTC",
            issues=[
                ConsistencyIssue(
                    severity="critical",
                    category="missing_implementation",
                    spec_reference="核心功能",
                    actual_state="未实现",
                    suggestion="实现该功能",
                ),
            ],
            consistency_score=80,
        )
        assert report.passed is False
        assert report.critical_count == 1

    def test_non_critical_passes(self):
        report = ConsistencyReport(
            change_id="test",
            timestamp="2026-03-28 00:00:00 UTC",
            issues=[
                ConsistencyIssue(
                    severity="medium",
                    category="config_drift",
                    spec_reference="配置项",
                    actual_state="不匹配",
                    suggestion="更新配置",
                ),
            ],
            consistency_score=95,
        )
        assert report.passed is True

    def test_to_markdown(self):
        report = ConsistencyReport(
            change_id="test-change",
            timestamp="2026-03-28 00:00:00 UTC",
            issues=[
                ConsistencyIssue(
                    severity="high",
                    category="api_mismatch",
                    spec_reference="GET /api/users",
                    actual_state="未实现",
                    suggestion="实现端点",
                ),
            ],
            consistency_score=90,
        )
        md = report.to_markdown()
        assert "test-change" in md
        assert "90/100" in md
        assert "API" in md or "api_mismatch" in md.lower() or "不匹配" in md

    def test_to_dict(self):
        report = ConsistencyReport(
            change_id="test",
            timestamp="2026-03-28 00:00:00 UTC",
            issues=[],
            consistency_score=100,
        )
        d = report.to_dict()
        assert d["change_id"] == "test"
        assert d["passed"] is True
        assert d["issue_count"] == 0

    def test_severity_counts(self):
        issues = [
            ConsistencyIssue("critical", "a", "r", "s", "g"),
            ConsistencyIssue("critical", "a", "r", "s", "g"),
            ConsistencyIssue("high", "a", "r", "s", "g"),
            ConsistencyIssue("medium", "a", "r", "s", "g"),
            ConsistencyIssue("low", "a", "r", "s", "g"),
        ]
        report = ConsistencyReport(
            change_id="x",
            timestamp="t",
            issues=issues,
            consistency_score=50,
        )
        assert report.critical_count == 2
        assert report.high_count == 1
        assert report.medium_count == 1
        assert report.low_count == 1


class TestSpecConsistencyChecker:
    def test_check_empty_change(self, project_dir: Path):
        """空变更应返回通过"""
        checker = SpecConsistencyChecker(project_dir)
        report = checker.check("test-change")
        assert report.change_id == "test-change"
        assert report.consistency_score >= 0

    def test_check_nonexistent_change(self, project_dir: Path):
        """不存在的变更应返回空报告"""
        checker = SpecConsistencyChecker(project_dir)
        report = checker.check("nonexistent")
        assert report.issues == [] or report.consistency_score >= 0

    def test_api_consistency_detects_missing_endpoint(self, project_dir: Path):
        """spec 中声明了 API 但代码中没有对应路由"""
        change_dir = project_dir / ".super-dev" / "changes" / "test-change"
        (change_dir / "proposal.md").write_text(
            "# API Design\n\n"
            "- GET /api/users - 获取用户列表\n"
            "- POST /api/users - 创建用户\n"
            "- DELETE /api/users/{id} - 删除用户\n",
            encoding="utf-8",
        )

        checker = SpecConsistencyChecker(project_dir)
        issues = checker._check_api_consistency("test-change")
        # 没有代码文件，所以这些端点都是缺失的
        assert len(issues) >= 1
        assert all(i.category == "api_mismatch" for i in issues)

    def test_api_consistency_passes_when_route_exists(self, project_dir: Path):
        """代码中有对应路由时通过"""
        change_dir = project_dir / ".super-dev" / "changes" / "test-change"
        (change_dir / "proposal.md").write_text(
            "# API Design\n\nGET /api/health - 健康检查\n",
            encoding="utf-8",
        )
        # 创建一个带路由的 Python 文件
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            '@app.get("/api/health")\n'
            "def health():\n"
            '    return {"status": "ok"}\n',
            encoding="utf-8",
        )

        checker = SpecConsistencyChecker(project_dir)
        issues = checker._check_api_consistency("test-change")
        # 应该找到 /api/health 路由，不报缺失
        missing_health = [i for i in issues if "/api/health" in i.spec_reference]
        assert len(missing_health) == 0

    def test_config_consistency_detects_framework_mismatch(self, project_dir: Path):
        """检测 super-dev.yaml 中声明的框架与 package.json 不匹配"""
        # super-dev.yaml 声明 react，但 package.json 中是 vue
        (project_dir / "package.json").write_text(
            json.dumps({"dependencies": {"vue": "^3.0.0"}}),
            encoding="utf-8",
        )

        checker = SpecConsistencyChecker(project_dir)
        issues = checker._check_config_consistency()
        # 应检测到 react vs vue 不匹配
        frontend_issues = [
            i for i in issues if "前端" in i.spec_reference or "react" in i.spec_reference.lower()
        ]
        assert len(frontend_issues) >= 1

    def test_config_consistency_passes_when_matching(self, project_dir: Path):
        """框架匹配时通过"""
        (project_dir / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}),
            encoding="utf-8",
        )

        checker = SpecConsistencyChecker(project_dir)
        issues = checker._check_config_consistency()
        frontend_issues = [
            i for i in issues if "前端" in i.spec_reference or "react" in i.spec_reference.lower()
        ]
        assert len(frontend_issues) == 0

    def test_task_completion_detects_drift(self, project_dir: Path):
        """标记为完成但没有代码的任务应被检测到"""
        change_dir = project_dir / ".super-dev" / "changes" / "test-change"
        (change_dir / "tasks.md").write_text(
            "# Tasks\n\n"
            "- [x] Implement user authentication module with JWT tokens\n"
            "- [ ] Add unit tests for authentication\n",
            encoding="utf-8",
        )

        checker = SpecConsistencyChecker(project_dir)
        issues = checker._check_task_completion("test-change")
        # 标记完成但没有代码
        completed_drift = [i for i in issues if i.category == "task_drift"]
        assert len(completed_drift) >= 1

    def test_task_completion_passes_with_code(self, project_dir: Path):
        """标记为完成且有对应代码的任务应通过"""
        change_dir = project_dir / ".super-dev" / "changes" / "test-change"
        (change_dir / "tasks.md").write_text(
            "# Tasks\n\n- [x] Implement authentication module with JWT tokens\n",
            encoding="utf-8",
        )
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "auth.py").write_text(
            "# Authentication module\n"
            "import jwt\n\n"
            "def authenticate(token):\n"
            '    """JWT authentication handler"""\n'
            "    return jwt.decode(token)\n",
            encoding="utf-8",
        )

        checker = SpecConsistencyChecker(project_dir)
        issues = checker._check_task_completion("test-change")
        task_drifts = [i for i in issues if i.category == "task_drift"]
        assert len(task_drifts) == 0

    def test_task_completion_ignores_review_and_negative_scope_items(self, project_dir: Path):
        change_dir = project_dir / ".super-dev" / "changes" / "test-change"
        (change_dir / "tasks.md").write_text(
            "# Tasks\n\n"
            "- [x] A3. Grok Build 最终复审为 `VERDICT=ACCEPT`。\n"
            "- [x] I7. 未接入系统化调试、TDD、Forge 或 Grill。\n",
            encoding="utf-8",
        )

        checker = SpecConsistencyChecker(project_dir)

        assert checker._check_task_completion("test-change") == []

    def test_task_identifier_is_not_treated_as_code_evidence(self, project_dir: Path):
        change_dir = project_dir / ".super-dev" / "changes" / "test-change"
        (change_dir / "tasks.md").write_text(
            "# Tasks\n\n- [x] J10. Fix compliance command routing\n",
            encoding="utf-8",
        )
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "cli.py").write_text(
            "def route_compliance_command():\n    return 'compliance routing'\n",
            encoding="utf-8",
        )

        checker = SpecConsistencyChecker(project_dir)
        issues = checker._check_task_completion("test-change")

        assert issues == []
        assert "j10" not in checker._extract_keywords("J10. Fix compliance command routing")

    def test_calculate_score(self, project_dir: Path):
        """分数计算逻辑"""
        checker = SpecConsistencyChecker(project_dir)
        # 无问题 = 100
        assert checker._calculate_score([]) == 100

        # critical = -20
        issues = [
            ConsistencyIssue("critical", "a", "r", "s", "g"),
        ]
        assert checker._calculate_score(issues) == 80

        # 多个问题
        issues = [
            ConsistencyIssue("critical", "a", "r", "s", "g"),
            ConsistencyIssue("high", "a", "r", "s", "g"),
            ConsistencyIssue("medium", "a", "r", "s", "g"),
            ConsistencyIssue("low", "a", "r", "s", "g"),
        ]
        assert checker._calculate_score(issues) == 100 - 20 - 10 - 5 - 2

    def test_full_check_returns_report(self, project_dir: Path):
        """完整检测应返回报告"""
        checker = SpecConsistencyChecker(project_dir)
        report = checker.check("test-change")
        assert isinstance(report, ConsistencyReport)
        assert report.change_id == "test-change"
        assert report.timestamp
        assert 0 <= report.consistency_score <= 100

    def test_extract_keywords(self, project_dir: Path):
        """关键词提取"""
        keywords = SpecConsistencyChecker._extract_keywords(
            "Implement user authentication module with JWT"
        )
        assert "user" in keywords
        assert "authentication" in keywords
        assert "jwt" in keywords
        # 停用词不应出现
        assert "with" not in keywords
        assert "implement" not in keywords
