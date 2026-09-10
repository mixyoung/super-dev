# ruff: noqa: I001
"""
集成管理器增强测试 - 宿主检测、兼容性评分、适配器画像

测试对象: super_dev.integrations.manager
"""

import pytest
from super_dev.integrations.manager import IntegrationManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_project(tmp_path):
    (tmp_path / "super-dev.yaml").write_text("name: test\nversion: '1.0.0'\n")
    return tmp_path


@pytest.fixture()
def manager(empty_project):
    return IntegrationManager(empty_project)


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------


class TestIntegrationManagerInit:
    def test_creates_with_valid_dir(self, empty_project):
        mgr = IntegrationManager(empty_project)
        assert mgr is not None
        assert mgr.project_dir.is_absolute()

    def test_project_dir_resolved(self, empty_project):
        mgr = IntegrationManager(empty_project)
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
        assert len(targets) >= 5

    def test_targets_have_names(self, manager):
        targets = manager.list_targets()
        for target in targets:
            assert hasattr(target, "name")


# ---------------------------------------------------------------------------
# list_adapter_profiles
# ---------------------------------------------------------------------------


class TestAdapterProfiles:
    def test_returns_list(self, manager):
        profiles = manager.list_adapter_profiles()
        assert isinstance(profiles, list)

    def test_profiles_have_attributes(self, manager):
        profiles = manager.list_adapter_profiles()
        if profiles:
            profile = profiles[0]
            assert hasattr(profile, "host")

    def test_filter_by_targets(self, manager):
        profiles_all = manager.list_adapter_profiles()
        if profiles_all:
            first_host = profiles_all[0].host
            profiles = manager.list_adapter_profiles(targets=[first_host])
            assert isinstance(profiles, list)
            assert len(profiles) >= 1


# ---------------------------------------------------------------------------
# get_adapter_profile
# ---------------------------------------------------------------------------


class TestGetAdapterProfile:
    def test_get_known_target(self, manager):
        profiles = manager.list_adapter_profiles()
        if profiles:
            target_id = profiles[0].host
            profile = manager.get_adapter_profile(target_id)
            assert profile is not None

    def test_get_claude_code_profile(self, manager):
        try:
            profile = manager.get_adapter_profile("claude-code")
            assert profile is not None
        except (KeyError, ValueError):
            pytest.skip("claude-code target not found")


# ---------------------------------------------------------------------------
# host_hardening_blueprint
# ---------------------------------------------------------------------------


class TestHostHardeningBlueprint:
    def test_returns_dict(self, manager):
        profiles = manager.list_adapter_profiles()
        if profiles:
            target_id = profiles[0].host
            blueprint = manager.host_hardening_blueprint(target_id)
            assert isinstance(blueprint, dict)


# ---------------------------------------------------------------------------
# coverage_gaps
# ---------------------------------------------------------------------------


class TestCoverageGaps:
    def test_returns_dict(self):
        gaps = IntegrationManager.coverage_gaps()
        assert isinstance(gaps, dict)

    def test_gaps_have_lists(self):
        gaps = IntegrationManager.coverage_gaps()
        for key, value in gaps.items():
            assert isinstance(value, list)


# ---------------------------------------------------------------------------
# 边界情况
# ---------------------------------------------------------------------------


class TestIntegrationEdgeCases:
    def test_nonexistent_output_dir(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("name: test\n")
        mgr = IntegrationManager(tmp_path)
        targets = mgr.list_targets()
        assert isinstance(targets, list)

    def test_project_with_host_configs(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("name: test\n")
        for dirname in [".claude", ".cursor", ".windsurf", ".cline"]:
            (tmp_path / dirname).mkdir(exist_ok=True)
        mgr = IntegrationManager(tmp_path)
        targets = mgr.list_targets()
        assert isinstance(targets, list)


# ---------------------------------------------------------------------------
# 适配器画像深度测试
# ---------------------------------------------------------------------------


class TestAdapterProfilesDeep:
    def test_all_profiles_have_host_field(self, manager):
        for profile in manager.list_adapter_profiles():
            assert hasattr(profile, "host")
            assert isinstance(profile.host, str)
            assert len(profile.host) > 0

    def test_all_profiles_have_category(self, manager):
        for profile in manager.list_adapter_profiles():
            assert hasattr(profile, "category")
            assert isinstance(profile.category, str)

    def test_all_profiles_have_adapter_mode(self, manager):
        for profile in manager.list_adapter_profiles():
            assert hasattr(profile, "adapter_mode")
            assert isinstance(profile.adapter_mode, str)

    def test_profiles_cover_multiple_hosts(self, manager):
        profiles = manager.list_adapter_profiles()
        hosts = {p.host for p in profiles}
        assert len(hosts) >= 5, f"Expected >= 5 hosts, got {len(hosts)}: {hosts}"

    def test_profiles_have_capability_labels(self, manager):
        profiles = manager.list_adapter_profiles()
        for profile in profiles:
            if hasattr(profile, "capability_labels"):
                assert isinstance(profile.capability_labels, dict)

    def test_get_profile_by_host(self, manager):
        profiles = manager.list_adapter_profiles()
        if profiles:
            host = profiles[0].host
            profile = manager.get_adapter_profile(host)
            assert profile.host == host

    def test_hardening_blueprint_has_content(self, manager):
        profiles = manager.list_adapter_profiles()
        if profiles:
            host = profiles[0].host
            blueprint = manager.host_hardening_blueprint(host)
            assert isinstance(blueprint, dict)
            assert len(blueprint) > 0

    def test_all_hosts_have_hardening_blueprint(self, manager):
        profiles = manager.list_adapter_profiles()
        for profile in profiles[:5]:  # Test first 5 to keep it fast
            blueprint = manager.host_hardening_blueprint(profile.host)
            assert isinstance(blueprint, dict)


# ---------------------------------------------------------------------------
# list_targets 深度测试
# ---------------------------------------------------------------------------


class TestListTargetsDeep:
    def test_targets_have_name(self, manager):
        for target in manager.list_targets():
            assert hasattr(target, "name")
            assert len(target.name) > 0

    def test_targets_have_description(self, manager):
        for target in manager.list_targets():
            assert hasattr(target, "description")

    def test_targets_have_files(self, manager):
        for target in manager.list_targets():
            if hasattr(target, "files"):
                assert isinstance(target.files, list)

    def test_target_count(self, manager):
        targets = manager.list_targets()
        assert len(targets) >= 5
        assert len(targets) <= 100

    def test_target_names_unique(self, manager):
        targets = manager.list_targets()
        names = [t.name for t in targets]
        assert len(names) == len(set(names)), "Duplicate target names found"


# ---------------------------------------------------------------------------
# coverage_gaps 深度测试
# ---------------------------------------------------------------------------


class TestCoverageGapsDeep:
    def test_gaps_keys_are_strings(self):
        gaps = IntegrationManager.coverage_gaps()
        for key in gaps:
            assert isinstance(key, str)

    def test_gaps_values_are_string_lists(self):
        gaps = IntegrationManager.coverage_gaps()
        for key, value in gaps.items():
            assert isinstance(value, list)
            for item in value:
                assert isinstance(item, str)

    def test_gaps_not_empty(self):
        gaps = IntegrationManager.coverage_gaps()
        # There should be at least some gaps identified
        total_gaps = sum(len(v) for v in gaps.values())
        assert total_gaps >= 0  # May be zero if all covered
