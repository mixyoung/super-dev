"""
Super Dev 配置管理单元测试
"""

from pathlib import Path

import pytest
import yaml

from super_dev.config import ConfigManager, ProjectConfig, get_config_manager


class TestProjectConfig:
    """测试 ProjectConfig"""

    def test_default_config(self):
        """测试默认配置"""
        config = ProjectConfig(name="test")

        assert config.name == "test"
        assert config.platform == "web"
        assert config.frontend == "next"
        assert config.backend == "node"
        assert config.quality_gate == 80
        assert config.host_compatibility_min_score == 80
        assert config.host_compatibility_min_ready_hosts == 1
        assert config.host_profile_targets == []
        assert config.host_profile_enforce_selected is False
        assert config.language_preferences == []
        assert config.knowledge_allowed_domains == []
        assert config.knowledge_cache_ttl_seconds == 1800
        assert config.adaptive_ledger == {
            "enabled": False,
            "auto_create": False,
            "scope_advisory": False,
        }

    def test_config_with_custom_values(self):
        """测试自定义配置"""
        config = ProjectConfig(
            name="custom",
            platform="mobile",
            frontend="vue",
            domain="fintech",
            quality_gate=90,
            host_compatibility_min_score=85,
            host_compatibility_min_ready_hosts=2,
            host_profile_targets=["codex-cli", "claude-code"],
            host_profile_enforce_selected=True,
            language_preferences=["python", "typescript"],
            knowledge_allowed_domains=["openai.com"],
            knowledge_cache_ttl_seconds=600,
        )

        assert config.name == "custom"
        assert config.platform == "mobile"
        assert config.frontend == "vue"
        assert config.domain == "fintech"
        assert config.quality_gate == 90
        assert config.host_compatibility_min_score == 85
        assert config.host_compatibility_min_ready_hosts == 2
        assert config.host_profile_targets == ["codex-cli", "claude-code"]
        assert config.host_profile_enforce_selected is True
        assert config.language_preferences == ["python", "typescript"]
        assert config.knowledge_allowed_domains == ["openai.com"]
        assert config.knowledge_cache_ttl_seconds == 600


class TestConfigManager:
    """测试 ConfigManager"""

    def test_init_without_config(self, temp_project_dir: Path):
        """测试无配置文件时初始化"""
        manager = ConfigManager(temp_project_dir)

        assert not manager.exists()
        assert manager.config.name == "my-project"

    def test_load_from_file(self, temp_project_dir: Path):
        """测试从文件加载配置"""
        config_data = {
            "name": "loaded-project",
            "platform": "desktop",
            "quality_gate": 85
        }
        config_path = temp_project_dir / "super-dev.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        manager = ConfigManager(temp_project_dir)
        config = manager.config

        assert config.name == "loaded-project"
        assert config.platform == "desktop"
        assert config.quality_gate == 85

    def test_load_minimal_file_does_not_emit_schema_warning(self, temp_project_dir: Path, caplog):
        config_data = {
            "name": "minimal-project",
            "platform": "web",
            "frontend": "react",
            "backend": "node",
        }
        config_path = temp_project_dir / "super-dev.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        caplog.clear()
        caplog.set_level("WARNING", logger="super_dev.config")

        manager = ConfigManager(temp_project_dir)
        config = manager.load()

        assert config.name == "minimal-project"
        assert config.quality_gate == 80
        assert not any("Config schema validation warnings" in record.message for record in caplog.records)

    def test_save_config(self, temp_project_dir: Path):
        """测试保存配置"""
        manager = ConfigManager(temp_project_dir)
        config = ProjectConfig(name="saved-project")
        manager.save(config)

        config_path = temp_project_dir / "super-dev.yaml"
        assert config_path.exists()

        with open(config_path) as f:
            data = yaml.safe_load(f)
            assert data["name"] == "saved-project"

    def test_adaptive_ledger_configuration_is_strict(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)

        enabled = manager.create(
            name="adaptive-ledger",
            adaptive_ledger={
                "enabled": True,
                "auto_create": True,
                "scope_advisory": True,
            },
        )

        assert enabled.adaptive_ledger == {
            "enabled": True,
            "auto_create": True,
            "scope_advisory": True,
        }
        with pytest.raises(ValueError, match="auto_create"):
            manager.update(adaptive_ledger={"enabled": False, "auto_create": True})
        with pytest.raises(ValueError, match="必须是布尔值"):
            manager.update(adaptive_ledger={"enabled": "true", "auto_create": "true"})
        with pytest.raises(ValueError, match="scope_advisory"):
            manager.update(
                adaptive_ledger={
                    "enabled": True,
                    "auto_create": False,
                    "scope_advisory": True,
                }
            )

    def test_partial_adaptive_ledger_configuration_merges_safe_defaults(
        self, temp_project_dir: Path
    ):
        config_path = temp_project_dir / "super-dev.yaml"
        config_path.write_text(
            "name: partial\nfrontend: next\nbackend: node\nadaptive_ledger:\n  enabled: true\n",
            encoding="utf-8",
        )

        loaded = ConfigManager(temp_project_dir).load()

        assert loaded.adaptive_ledger == {
            "enabled": True,
            "auto_create": False,
            "scope_advisory": False,
        }

    def test_create_config(self, temp_project_dir: Path):
        """测试创建新配置"""
        manager = ConfigManager(temp_project_dir)
        config = manager.create(
            name="new-project",
            platform="wechat",
            domain="ecommerce"
        )

        assert config.name == "new-project"
        assert config.platform == "wechat"
        assert config.domain == "ecommerce"
        assert manager.exists()

    def test_update_config(self, temp_project_dir: Path):
        """测试更新配置"""
        manager = ConfigManager(temp_project_dir)
        manager.create(name="original")

        updated = manager.update(
            description="Updated description",
            quality_gate=90,
            host_compatibility_min_score=88,
            host_compatibility_min_ready_hosts=1,
        )

        assert updated.description == "Updated description"
        assert updated.quality_gate == 90
        assert updated.host_compatibility_min_score == 88
        assert updated.host_compatibility_min_ready_hosts == 1

    def test_update_knowledge_domains_from_csv(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="original")

        updated = manager.update(knowledge_allowed_domains="openai.com, python.org")
        assert updated.knowledge_allowed_domains == ["openai.com", "python.org"]

    def test_update_host_compatibility_thresholds_from_string(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="original")

        updated = manager.update(
            host_compatibility_min_score="86",
            host_compatibility_min_ready_hosts="2",
        )
        assert updated.host_compatibility_min_score == 86
        assert updated.host_compatibility_min_ready_hosts == 2

    def test_update_host_profile_targets_from_csv(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="original")

        updated = manager.update(
            host_profile_targets="codex-cli, claude-code",
            host_profile_enforce_selected="true",
        )
        assert updated.host_profile_targets == ["codex-cli", "claude-code"]
        assert updated.host_profile_enforce_selected is True

    def test_update_language_preferences_from_csv(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="original")

        updated = manager.update(language_preferences="python, typescript, rust")
        assert updated.language_preferences == ["python", "typescript", "rust"]

    def test_get_config_value(self, temp_project_dir: Path):
        """测试获取配置值"""
        manager = ConfigManager(temp_project_dir)
        manager.create(name="test", quality_gate=85)

        assert manager.get("name") == "test"
        assert manager.get("quality_gate") == 85
        assert manager.get("nonexistent", "default") == "default"

    def test_validate_valid_config(self, temp_project_dir: Path):
        """测试验证有效配置"""
        manager = ConfigManager(temp_project_dir)
        manager.create(
            name="valid",
            platform="web",
            frontend="react",
            backend="node",
            quality_gate=85
        )

        is_valid, errors = manager.validate()
        assert is_valid
        assert len(errors) == 0

    def test_validate_extended_frontend(self, temp_project_dir: Path):
        """测试扩展前端框架校验"""
        manager = ConfigManager(temp_project_dir)
        manager.create(
            name="valid-next",
            platform="web",
            frontend="next",
            backend="node",
            quality_gate=80
        )

        is_valid, errors = manager.validate()
        assert is_valid
        assert len(errors) == 0

    def test_validate_extended_backend(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(
            name="valid-rust",
            platform="web",
            frontend="react",
            backend="rust",
            quality_gate=80,
        )

        is_valid, errors = manager.validate()
        assert is_valid
        assert len(errors) == 0

    def test_validate_invalid_platform(self, temp_project_dir: Path):
        """测试验证无效平台"""
        manager = ConfigManager(temp_project_dir)
        manager.create(name="invalid")
        assert manager._config is not None
        manager._config.platform = "invalid_platform"

        is_valid, errors = manager.validate()
        assert not is_valid
        assert len(errors) > 0

    def test_validate_invalid_quality_gate(self, temp_project_dir: Path):
        """测试验证无效质量门禁"""
        manager = ConfigManager(temp_project_dir)
        manager.create(name="invalid")
        assert manager._config is not None
        manager._config.quality_gate = 150

        is_valid, errors = manager.validate()
        assert not is_valid

    def test_validate_invalid_host_compatibility_score(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="invalid")
        assert manager._config is not None
        manager._config.host_compatibility_min_score = 101

        is_valid, errors = manager.validate()
        assert not is_valid
        assert any("host_compatibility_min_score" in item for item in errors)

    def test_validate_invalid_host_compatibility_ready_hosts(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="invalid")
        assert manager._config is not None
        manager._config.host_compatibility_min_ready_hosts = -1

        is_valid, errors = manager.validate()
        assert not is_valid
        assert any("host_compatibility_min_ready_hosts" in item for item in errors)

    def test_validate_invalid_host_profile_target(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="invalid")
        assert manager._config is not None
        manager._config.host_profile_targets = ["not-exists-host"]

        is_valid, errors = manager.validate()
        assert not is_valid
        assert any("host_profile_targets" in item for item in errors)

    def test_validate_invalid_language_preferences(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="invalid")
        assert manager._config is not None
        manager._config.language_preferences = ["python", ""]

        is_valid, errors = manager.validate()
        assert not is_valid
        assert any("language_preferences" in item for item in errors)

    def test_validate_invalid_knowledge_cache_ttl(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="invalid")
        assert manager._config is not None
        manager._config.knowledge_cache_ttl_seconds = -1

        is_valid, errors = manager.validate()
        assert not is_valid
        assert any("knowledge_cache_ttl_seconds" in item for item in errors)

    def test_create_raises_on_invalid_host_compatibility_threshold(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        with pytest.raises(ValueError):
            manager.create(name="invalid", host_compatibility_min_score=200)

    def test_update_raises_on_invalid_quality_gate(self, temp_project_dir: Path):
        manager = ConfigManager(temp_project_dir)
        manager.create(name="valid")
        with pytest.raises(ValueError):
            manager.update(quality_gate=101)


class TestGlobalConfigManager:
    """测试全局配置管理器"""

    def test_get_config_manager_singleton(self, temp_project_dir: Path):
        """测试单例模式"""
        manager1 = get_config_manager(temp_project_dir)
        manager2 = get_config_manager(temp_project_dir)

        assert manager1 is manager2

    def test_get_config_manager_isolated_by_project(self, temp_project_dir: Path, tmp_path: Path):
        """测试不同项目目录返回不同实例"""
        manager1 = get_config_manager(temp_project_dir)
        manager2 = get_config_manager(tmp_path)

        assert manager1 is not manager2
        assert manager1.project_dir != manager2.project_dir
