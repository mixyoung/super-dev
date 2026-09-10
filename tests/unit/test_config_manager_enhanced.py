# ruff: noqa: I001
"""
配置管理器增强测试

测试对象: super_dev.config.manager
"""

import textwrap
import yaml
from super_dev import __version__
from super_dev.config.manager import ConfigManager, ProjectConfig

# ---------------------------------------------------------------------------
# ProjectConfig 数据类
# ---------------------------------------------------------------------------


class TestProjectConfig:
    def test_default_values(self):
        config = ProjectConfig(name="test")
        assert config.name == "test"
        assert config.description == ""
        assert config.version == __version__
        assert config.platform == "web"
        assert config.frontend == "next"
        assert config.backend == "node"
        assert config.database == "postgresql"
        assert config.quality_gate == 80
        assert config.output_dir == "output"

    def test_custom_values(self):
        config = ProjectConfig(
            name="myapp",
            description="My application",
            version="3.0.0",
            platform="mobile",
            frontend="react-native",
            backend="python",
            database="mongodb",
            domain="fintech",
            quality_gate=95,
        )
        assert config.name == "myapp"
        assert config.platform == "mobile"
        assert config.frontend == "react-native"
        assert config.backend == "python"
        assert config.domain == "fintech"
        assert config.quality_gate == 95

    def test_default_phases(self):
        config = ProjectConfig(name="test")
        expected_phases = [
            "discovery",
            "intelligence",
            "drafting",
            "redteam",
            "qa",
            "delivery",
            "deployment",
        ]
        assert config.phases == expected_phases

    def test_default_experts(self):
        config = ProjectConfig(name="test")
        assert "PM" in config.experts
        assert "ARCHITECT" in config.experts
        assert "SECURITY" in config.experts

    def test_empty_lists_default(self):
        config = ProjectConfig(name="test")
        assert config.state_management == []
        assert config.testing_frameworks == []
        assert config.language_preferences == []
        assert config.knowledge_allowed_domains == []
        assert config.host_profile_targets == []

    def test_optional_fields(self):
        config = ProjectConfig(name="test")
        assert config.ui_library is None
        assert config.style_solution is None
        assert config.author == ""
        assert config.license == "MIT"

    def test_custom_phases(self):
        config = ProjectConfig(name="test", phases=["discovery", "delivery"])
        assert len(config.phases) == 2

    def test_custom_experts(self):
        config = ProjectConfig(name="test", experts=["PM", "CODE"])
        assert len(config.experts) == 2

    def test_knowledge_cache_ttl(self):
        config = ProjectConfig(name="test")
        assert config.knowledge_cache_ttl_seconds == 1800

    def test_host_compatibility_defaults(self):
        config = ProjectConfig(name="test")
        assert config.host_compatibility_min_score == 80
        assert config.host_compatibility_min_ready_hosts == 1
        assert config.host_profile_enforce_selected is False

    def test_cli_defaults_to_empty_dict(self):
        config = ProjectConfig(name="test")
        assert config.cli == {}


# ---------------------------------------------------------------------------
# ConfigManager - 文件操作
# ---------------------------------------------------------------------------


class TestConfigManagerFileOps:
    def test_load_from_valid_yaml(self, tmp_path):
        config_content = textwrap.dedent("""\
            name: my-project
            description: Test project
            version: "1.0.0"
            platform: web
            frontend: react
            backend: node
            database: postgresql
            domain: fintech
            quality_gate: 90
        """)
        (tmp_path / "super-dev.yaml").write_text(config_content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.name == "my-project"
        assert config.platform == "web"
        assert config.frontend == "react"
        assert config.domain == "fintech"
        assert config.quality_gate == 90

    def test_load_creates_default_if_missing(self, tmp_path):
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config is not None
        assert config.name != ""

    def test_save_creates_file(self, tmp_path):
        manager = ConfigManager(tmp_path)
        config = ProjectConfig(name="saved-project", version="2.0.0")
        manager.save(config)
        config_file = tmp_path / "super-dev.yaml"
        assert config_file.exists()
        data = yaml.safe_load(config_file.read_text())
        assert data["name"] == "saved-project"

    def test_save_and_reload(self, tmp_path):
        manager = ConfigManager(tmp_path)
        config = ProjectConfig(
            name="roundtrip",
            version="1.5.0",
            platform="mobile",
            frontend="flutter",
            backend="go",
            domain="education",
        )
        manager.save(config)
        loaded = manager.load()
        assert loaded.name == "roundtrip"
        assert loaded.platform == "mobile"
        assert loaded.frontend == "flutter"

    def test_load_partial_yaml(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("name: minimal\n")
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.name == "minimal"
        # Default values should apply
        assert config.platform == "web"
        assert config.backend == "node"

    def test_load_with_extra_fields(self, tmp_path):
        config_content = textwrap.dedent("""\
            name: extra-fields
            unknown_field: should_be_ignored
            another_unknown: true
        """)
        (tmp_path / "super-dev.yaml").write_text(config_content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.name == "extra-fields"

    def test_load_with_list_fields(self, tmp_path):
        config_content = textwrap.dedent("""\
            name: list-test
            experts:
              - PM
              - ARCHITECT
              - SECURITY
              - CODE
            state_management:
              - zustand
              - react-query
            testing_frameworks:
              - jest
              - playwright
        """)
        (tmp_path / "super-dev.yaml").write_text(config_content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert "zustand" in config.state_management
        assert "jest" in config.testing_frameworks


# ---------------------------------------------------------------------------
# ConfigManager - 验证
# ---------------------------------------------------------------------------


class TestConfigManagerValidation:
    def test_valid_platform_ids(self, tmp_path):
        for platform in ["web", "mobile", "wechat", "desktop"]:
            config_content = f"name: test\nplatform: {platform}\n"
            (tmp_path / "super-dev.yaml").write_text(config_content)
            manager = ConfigManager(tmp_path)
            config = manager.load()
            assert config.platform == platform

    def test_valid_backend_ids(self, tmp_path):
        for backend in ["node", "python", "go", "java", "rust"]:
            config_content = f"name: test\nbackend: {backend}\n"
            (tmp_path / "super-dev.yaml").write_text(config_content)
            manager = ConfigManager(tmp_path)
            config = manager.load()
            assert config.backend == backend

    def test_quality_gate_integer(self, tmp_path):
        config_content = "name: test\nquality_gate: 95\n"
        (tmp_path / "super-dev.yaml").write_text(config_content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.quality_gate == 95
        assert isinstance(config.quality_gate, int)


# ---------------------------------------------------------------------------
# ConfigManager - Singleton 行为
# ---------------------------------------------------------------------------


class TestConfigManagerSingleton:
    def test_same_dir_returns_consistent_config(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("name: singleton-test\n")
        m1 = ConfigManager(tmp_path)
        m2 = ConfigManager(tmp_path)
        c1 = m1.load()
        c2 = m2.load()
        assert c1.name == c2.name

    def test_different_dirs_independent(self, tmp_path):
        dir1 = tmp_path / "project1"
        dir2 = tmp_path / "project2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "super-dev.yaml").write_text("name: project1\n")
        (dir2 / "super-dev.yaml").write_text("name: project2\n")
        c1 = ConfigManager(dir1).load()
        c2 = ConfigManager(dir2).load()
        assert c1.name == "project1"
        assert c2.name == "project2"


# ---------------------------------------------------------------------------
# ConfigManager - 技术栈获取
# ---------------------------------------------------------------------------


class TestConfigManagerTechStack:
    def test_get_tech_stack_dict(self, tmp_path):
        config_content = textwrap.dedent("""\
            name: stack-test
            platform: web
            frontend: react
            backend: python
            database: postgresql
            domain: fintech
        """)
        (tmp_path / "super-dev.yaml").write_text(config_content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        tech_stack = {
            "platform": config.platform,
            "frontend": config.frontend,
            "backend": config.backend,
            "database": config.database,
            "domain": config.domain,
        }
        assert tech_stack["platform"] == "web"
        assert tech_stack["frontend"] == "react"
        assert tech_stack["backend"] == "python"
        assert tech_stack["domain"] == "fintech"

    def test_default_tech_stack(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("name: default-stack\n")
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.platform == "web"
        assert config.frontend == "next"
        assert config.backend == "node"
        assert config.database == "postgresql"


# ---------------------------------------------------------------------------
# ConfigManager - Edge cases
# ---------------------------------------------------------------------------


class TestConfigManagerEdgeCases:
    def test_empty_yaml_file(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("")
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config is not None

    def test_yaml_with_only_comments(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("# This is a comment\n# Another comment\n")
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config is not None

    def test_yaml_with_null_values(self, tmp_path):
        config_content = textwrap.dedent("""\
            name: null-test
            description: null
            domain: null
        """)
        (tmp_path / "super-dev.yaml").write_text(config_content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.name == "null-test"

    def test_unicode_in_config(self, tmp_path):
        config_content = textwrap.dedent("""\
            name: 中文项目名
            description: 这是一个测试项目
        """)
        (tmp_path / "super-dev.yaml").write_text(config_content, encoding="utf-8")
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.name == "中文项目名"

    def test_numeric_name(self, tmp_path):
        (tmp_path / "super-dev.yaml").write_text("name: 12345\n")
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.name == "12345" or config.name == 12345


# ---------------------------------------------------------------------------
# ProjectConfig - 深入字段测试
# ---------------------------------------------------------------------------


class TestProjectConfigFields:
    def test_all_supported_platforms(self):
        for platform in ["web", "mobile", "wechat", "desktop"]:
            config = ProjectConfig(name="test", platform=platform)
            assert config.platform == platform

    def test_all_supported_backends(self):
        for backend in [
            "node",
            "python",
            "go",
            "java",
            "rust",
            "php",
            "ruby",
            "csharp",
            "kotlin",
            "swift",
            "elixir",
            "scala",
            "dart",
        ]:
            config = ProjectConfig(name="test", backend=backend)
            assert config.backend == backend

    def test_all_supported_databases(self):
        for db in ["postgresql", "mysql", "mongodb", "redis"]:
            config = ProjectConfig(name="test", database=db)
            assert config.database == db

    def test_all_supported_domains(self):
        for domain in ["fintech", "ecommerce", "medical", "social", "iot", "education", ""]:
            config = ProjectConfig(name="test", domain=domain)
            assert config.domain == domain

    def test_quality_gate_range(self):
        for qg in [0, 50, 80, 90, 100]:
            config = ProjectConfig(name="test", quality_gate=qg)
            assert config.quality_gate == qg

    def test_version_format(self):
        config = ProjectConfig(name="test", version="1.2.3")
        assert config.version == "1.2.3"

    def test_host_profile_targets_list(self):
        config = ProjectConfig(name="test", host_profile_targets=["claude-code", "cursor"])
        assert "claude-code" in config.host_profile_targets
        assert "cursor" in config.host_profile_targets

    def test_host_profile_enforce_selected(self):
        config = ProjectConfig(name="test", host_profile_enforce_selected=True)
        assert config.host_profile_enforce_selected is True

    def test_knowledge_cache_ttl_custom(self):
        config = ProjectConfig(name="test", knowledge_cache_ttl_seconds=3600)
        assert config.knowledge_cache_ttl_seconds == 3600

    def test_cli_dict(self):
        config = ProjectConfig(name="test", cli={"auto_approve": True, "verbose": False})
        assert config.cli["auto_approve"] is True

    def test_output_dir_custom(self):
        config = ProjectConfig(name="test", output_dir="custom-output")
        assert config.output_dir == "custom-output"


# ---------------------------------------------------------------------------
# ConfigManager - YAML 格式兼容性
# ---------------------------------------------------------------------------


class TestYAMLCompatibility:
    def test_boolean_values(self, tmp_path):
        content = "name: test\nhost_profile_enforce_selected: true\n"
        (tmp_path / "super-dev.yaml").write_text(content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.host_profile_enforce_selected is True

    def test_integer_values(self, tmp_path):
        content = "name: test\nquality_gate: 95\nknowledge_cache_ttl_seconds: 7200\n"
        (tmp_path / "super-dev.yaml").write_text(content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.quality_gate == 95
        assert config.knowledge_cache_ttl_seconds == 7200

    def test_nested_cli_dict(self, tmp_path):
        import textwrap

        content = textwrap.dedent("""\
            name: test
            cli:
              auto_approve: true
              verbose: false
              output_format: json
        """)
        (tmp_path / "super-dev.yaml").write_text(content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.cli.get("auto_approve") is True

    def test_multiline_description(self, tmp_path):
        import textwrap

        content = textwrap.dedent("""\
            name: test
            description: |
              This is a multiline
              description for the project.
        """)
        (tmp_path / "super-dev.yaml").write_text(content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert "multiline" in config.description

    def test_quoted_version(self, tmp_path):
        content = 'name: test\nversion: "2.0.0"\n'
        (tmp_path / "super-dev.yaml").write_text(content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.version == "2.0.0"

    def test_all_fields_roundtrip(self, tmp_path):
        import textwrap

        content = textwrap.dedent("""\
            name: roundtrip-test
            description: Full roundtrip
            version: "3.0.0"
            platform: mobile
            frontend: flutter
            backend: go
            database: mongodb
            domain: education
            quality_gate: 95
            output_dir: my-output
            experts:
              - PM
              - ARCHITECT
              - CODE
            phases:
              - discovery
              - delivery
        """)
        (tmp_path / "super-dev.yaml").write_text(content)
        manager = ConfigManager(tmp_path)
        config = manager.load()
        assert config.name == "roundtrip-test"
        assert config.platform == "mobile"
        assert config.frontend == "flutter"
        assert config.backend == "go"
        assert config.database == "mongodb"
        assert config.domain == "education"
        assert config.quality_gate == 95
        assert "PM" in config.experts
