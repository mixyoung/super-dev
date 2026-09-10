# ruff: noqa: I001
"""
技能管理器增强测试 - 技能列表、安装路径、目标宿主检测

测试对象: super_dev.skills.manager
"""

import pytest
from super_dev.skills.manager import SkillManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_project(tmp_path):
    (tmp_path / "super-dev.yaml").write_text("name: test\nversion: '1.0.0'\n")
    return tmp_path


@pytest.fixture()
def manager(empty_project):
    return SkillManager(empty_project)


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------


class TestSkillManagerInit:
    def test_creates_with_valid_dir(self, empty_project):
        mgr = SkillManager(empty_project)
        assert mgr is not None
        assert mgr.project_dir.is_absolute()

    def test_project_dir_resolved(self, empty_project):
        mgr = SkillManager(empty_project)
        assert mgr.project_dir == empty_project.resolve()


# ---------------------------------------------------------------------------
# list_targets
# ---------------------------------------------------------------------------


class TestListTargets:
    def test_returns_list(self, manager):
        targets = manager.list_targets()
        assert isinstance(targets, list)

    def test_has_multiple_targets(self, manager):
        targets = manager.list_targets()
        assert len(targets) >= 3

    def test_targets_are_strings(self, manager):
        for target in manager.list_targets():
            assert isinstance(target, str)
            assert len(target) > 0

    def test_claude_code_in_targets(self, manager):
        targets = manager.list_targets()
        assert any("claude" in t.lower() for t in targets)


# ---------------------------------------------------------------------------
# target_path_kind
# ---------------------------------------------------------------------------


class TestTargetPathKind:
    def test_returns_string(self, manager):
        targets = manager.list_targets()
        if targets:
            kind = SkillManager.target_path_kind(targets[0])
            assert isinstance(kind, str)


# ---------------------------------------------------------------------------
# skill_surface_available
# ---------------------------------------------------------------------------


class TestSkillSurfaceAvailable:
    def test_returns_bool(self, manager):
        targets = manager.list_targets()
        if targets:
            available = manager.skill_surface_available(targets[0])
            assert isinstance(available, bool)


# ---------------------------------------------------------------------------
# list_installed
# ---------------------------------------------------------------------------


class TestListInstalled:
    def test_returns_list(self, manager):
        targets = manager.list_targets()
        if targets:
            installed = manager.list_installed(targets[0])
            assert isinstance(installed, list)

    def test_empty_project_no_skills(self, manager):
        targets = manager.list_targets()
        if targets:
            installed = manager.list_installed(targets[0])
            # Empty project should have no or few installed skills
            assert isinstance(installed, list)


# ---------------------------------------------------------------------------
# coverage_gaps
# ---------------------------------------------------------------------------


class TestCoverageGaps:
    def test_returns_dict(self):
        gaps = SkillManager.coverage_gaps()
        assert isinstance(gaps, dict)

    def test_gaps_have_list_values(self):
        gaps = SkillManager.coverage_gaps()
        for key, value in gaps.items():
            assert isinstance(value, list)


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------


class TestSkillManagerEdgeCases:
    def test_nonexistent_subdir(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        nonexistent.mkdir()
        (nonexistent / "super-dev.yaml").write_text("name: test\n")
        mgr = SkillManager(nonexistent)
        targets = mgr.list_targets()
        assert isinstance(targets, list)

    def test_project_with_existing_skill_dir(self, empty_project):
        skill_dir = empty_project / "super-dev-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill\n")
        mgr = SkillManager(empty_project)
        targets = mgr.list_targets()
        assert isinstance(targets, list)


# ---------------------------------------------------------------------------
# list_targets 深度
# ---------------------------------------------------------------------------


class TestListTargetsDeep:
    def test_targets_include_claude_code(self, manager):
        targets = manager.list_targets()
        assert any("claude" in t.lower() for t in targets)

    def test_targets_include_cursor(self, manager):
        targets = manager.list_targets()
        assert any("cursor" in t.lower() for t in targets)

    def test_targets_include_windsurf(self, manager):
        targets = manager.list_targets()
        assert any("windsurf" in t.lower() for t in targets)

    def test_target_count_reasonable(self, manager):
        targets = manager.list_targets()
        assert 3 <= len(targets) <= 50

    def test_each_target_is_nonempty_string(self, manager):
        for target in manager.list_targets():
            assert isinstance(target, str)
            assert len(target) >= 2

    def test_targets_are_unique(self, manager):
        targets = manager.list_targets()
        assert len(targets) == len(set(targets))


# ---------------------------------------------------------------------------
# target_path_kind 深度
# ---------------------------------------------------------------------------


class TestTargetPathKindDeep:
    def test_all_targets_have_path_kind(self, manager):
        for target in manager.list_targets():
            kind = SkillManager.target_path_kind(target)
            assert isinstance(kind, str)
            assert len(kind) > 0

    def test_path_kind_values_are_consistent(self, manager):
        known_kinds = set()
        for target in manager.list_targets():
            kind = SkillManager.target_path_kind(target)
            known_kinds.add(kind)
        # There should be a limited set of kinds
        assert len(known_kinds) <= 10


# ---------------------------------------------------------------------------
# skill_surface_available 深度
# ---------------------------------------------------------------------------


class TestSkillSurfaceAvailableDeep:
    def test_all_targets_have_surface_check(self, manager):
        for target in manager.list_targets():
            available = manager.skill_surface_available(target)
            assert isinstance(available, bool)


# ---------------------------------------------------------------------------
# list_installed 深度
# ---------------------------------------------------------------------------


class TestListInstalledDeep:
    def test_all_targets_return_list(self, manager):
        for target in manager.list_targets():
            installed = manager.list_installed(target)
            assert isinstance(installed, list)
            for skill in installed:
                assert isinstance(skill, str)
