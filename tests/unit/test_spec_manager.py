"""
Spec 管理器测试
"""

from pathlib import Path

from super_dev.specs.generator import SpecGenerator
from super_dev.specs.manager import ChangeManager
from super_dev.specs.models import Task, TaskStatus
from super_dev.specs.validator import SpecValidator


class TestSpecManager:
    def test_proposal_roundtrip_is_parsed(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()
        change = generator.create_change(
            change_id="add-search",
            title="Add Search",
            description="支持搜索",
            motivation="提升效率",
            impact="core module",
        )

        manager = ChangeManager(temp_project_dir)
        loaded = manager.load_change(change.id)
        assert loaded is not None
        assert loaded.proposal is not None
        assert loaded.proposal.description == "支持搜索"
        assert loaded.proposal.motivation == "提升效率"

    def test_change_spec_requirements_persist_after_reload_and_save(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()

        change = generator.create_change(
            change_id="add-auth-flow",
            title="Add Auth Flow",
            description="认证流程",
        )
        generator.add_requirement_to_change(
            change_id=change.id,
            spec_name="auth",
            requirement_name="secure-authentication",
            description="系统 SHALL 支持安全认证与会话管理。",
            scenarios=[{"given": "用户未登录", "when": "提交凭据", "then": "建立会话"}],
        )
        generator.add_requirement_to_change(
            change_id=change.id,
            spec_name="auth",
            requirement_name="password-reset",
            description="系统 SHALL 支持密码重置。",
        )

        manager = ChangeManager(temp_project_dir)
        loaded = manager.load_change(change.id)
        assert loaded is not None
        assert loaded.spec_deltas
        assert loaded.spec_deltas[0].requirements
        assert any(
            req.name == "secure-authentication" for req in loaded.spec_deltas[0].requirements
        )

        # 模拟后续任务更新再次保存，需求不应丢失
        manager.save_change(loaded)
        reloaded = manager.load_change(change.id)
        assert reloaded is not None
        assert reloaded.spec_deltas
        assert reloaded.spec_deltas[0].requirements
        assert any(req.name == "password-reset" for req in reloaded.spec_deltas[0].requirements)

    def test_change_task_metadata_persist_after_reload_and_save(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()
        change = generator.create_change(
            change_id="add-task-meta",
            title="Add Task Meta",
            description="任务元数据持久化",
        )

        manager = ChangeManager(temp_project_dir)
        loaded = manager.load_change(change.id)
        assert loaded is not None

        loaded.tasks = [
            Task(
                id="2.1",
                title="实现 auth 前端模块",
                description="完成登录页面与校验规则",
                status=TaskStatus.IN_PROGRESS,
                assigned_to="frontend-team",
                dependencies=["1.2"],
                spec_refs=["auth::*", "session::login-flow"],
            ),
            Task(
                id="3.1",
                title="实现 auth 后端能力",
                description="提供登录 API 与会话管理",
                status=TaskStatus.PENDING,
                dependencies=["2.1"],
                spec_refs=["auth::*"],
            ),
        ]
        manager.save_change(loaded)

        reloaded = manager.load_change(change.id)
        assert reloaded is not None
        assert len(reloaded.tasks) == 2

        task = reloaded.tasks[0]
        assert task.id == "2.1"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.description == "完成登录页面与校验规则"
        assert task.assigned_to == "frontend-team"
        assert task.dependencies == ["1.2"]
        assert task.spec_refs == ["auth::*", "session::login-flow"]

    def test_list_changes_handles_mixed_timezone_created_at(self, temp_project_dir: Path):
        manager = ChangeManager(temp_project_dir)
        (temp_project_dir / ".super-dev" / "changes" / "naive").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".super-dev" / "changes" / "aware").mkdir(parents=True, exist_ok=True)

        (temp_project_dir / ".super-dev" / "changes" / "naive" / "change.yaml").write_text(
            (
                "id: naive\n"
                "title: Naive\n"
                "status: proposed\n"
                "created_at: 2026-03-19T12:00:00\n"
                "updated_at: 2026-03-19T12:00:00\n"
            ),
            encoding="utf-8",
        )
        (temp_project_dir / ".super-dev" / "changes" / "aware" / "change.yaml").write_text(
            (
                "id: aware\n"
                "title: Aware\n"
                "status: proposed\n"
                "created_at: 2026-03-19T12:00:01+00:00\n"
                "updated_at: 2026-03-19T12:00:01+00:00\n"
            ),
            encoding="utf-8",
        )

        changes = manager.list_changes()
        ids = {change.id for change in changes}
        assert "aware" in ids
        assert "naive" in ids

    def test_scaffold_creates_spec_four_piece_set(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()
        change = generator.create_change(
            change_id="add-notify",
            title="Add Notify",
            description="通知能力",
        )
        generated = generator.scaffold_change_artifacts(change.id)

        assert "plan.md" in generated
        assert "tasks.md" in generated
        assert "checklist.md" in generated
        spec_path = generated.get("spec.md")
        assert spec_path is not None
        assert spec_path.exists()
        content = spec_path.read_text(encoding="utf-8")
        assert "## ADDED Requirements" in content
        assert "## Acceptance Checklist" in content

    def test_validator_accepts_simple_task_checklist_style(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()
        change = generator.create_change(
            change_id="add-batch",
            title="Add Batch",
            description="批处理能力",
        )
        change_dir = temp_project_dir / ".super-dev" / "changes" / change.id
        (change_dir / "tasks.md").write_text(
            "# Tasks\n\n## 1. Group\n- [ ] 1.1 do thing\n",
            encoding="utf-8",
        )
        (change_dir / "plan.md").write_text("# Plan\n\n## Context\nok\n", encoding="utf-8")
        (change_dir / "checklist.md").write_text("# Checklist\n\n- [ ] item\n", encoding="utf-8")
        validator = SpecValidator(temp_project_dir)
        result = validator.validate_change(change.id)
        assert result.is_valid

    def test_quality_report_scores_high_for_scaffolded_change(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()
        change = generator.create_change(
            change_id="add-quality",
            title="Add Quality",
            description="质量评估",
        )
        generator.scaffold_change_artifacts(change.id)
        validator = SpecValidator(temp_project_dir)
        report = validator.assess_change_quality(change.id)
        assert report.score >= 75
        assert report.level in {"excellent", "good"}
        assert "spec" in report.checks
        assert report.checks["spec"]["passed"] is True

    def test_quality_report_detects_missing_artifacts(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()
        change = generator.create_change(
            change_id="add-weak-spec",
            title="Add Weak Spec",
            description="弱规格",
        )
        change_dir = temp_project_dir / ".super-dev" / "changes" / change.id
        (change_dir / "tasks.md").write_text("# Tasks\n\n", encoding="utf-8")
        validator = SpecValidator(temp_project_dir)
        report = validator.assess_change_quality(change.id)
        assert report.score < 75
        assert report.blockers
        assert any("spec" in blocker for blocker in report.blockers)
        assert report.action_plan
        assert any(item.get("priority") == "P0" for item in report.action_plan)

    def test_quality_report_to_dict_contains_serializable_fields(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()
        change = generator.create_change(
            change_id="add-json-quality",
            title="Add Json Quality",
            description="json输出",
        )
        validator = SpecValidator(temp_project_dir)
        report = validator.assess_change_quality(change.id)
        payload = report.to_dict()
        assert payload["change_id"] == change.id
        assert "score" in payload
        assert "checks" in payload
        assert isinstance(payload["blockers"], list)
        assert isinstance(payload["action_plan"], list)

    def test_validator_can_pick_latest_change_quality(self, temp_project_dir: Path):
        generator = SpecGenerator(temp_project_dir)
        generator.init_sdd()
        older = generator.create_change(
            change_id="older-change",
            title="Older Change",
            description="older",
        )
        generator.scaffold_change_artifacts(older.id)

        newer = generator.create_change(
            change_id="newer-change",
            title="Newer Change",
            description="newer",
        )
        generator.scaffold_change_artifacts(newer.id)

        validator = SpecValidator(temp_project_dir)
        latest = validator.assess_latest_change_quality()
        assert latest is not None
        assert latest.change_id == newer.id
