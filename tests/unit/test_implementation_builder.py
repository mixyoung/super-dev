"""
实现骨架生成器测试
"""

import json
from pathlib import Path

import pytest

from super_dev.creators.implementation_builder import ImplementationScaffoldBuilder


class TestImplementationScaffoldBuilder:
    def test_generate_react_node_scaffold(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "typography_preset": {"heading": "IBM Plex Sans", "body": "Public Sans"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        builder = ImplementationScaffoldBuilder(
            project_dir=temp_project_dir,
            name="demo",
            frontend="react",
            backend="node",
        )
        result = builder.generate(
            requirements=[
                {"spec_name": "auth", "req_name": "secure-authentication"},
                {"spec_name": "dashboard", "req_name": "dashboard-insights"},
            ]
        )

        assert len(result["frontend_files"]) > 0
        assert len(result["backend_files"]) > 0
        assert (temp_project_dir / "frontend" / "src" / "App.tsx").exists()
        assert (temp_project_dir / "backend" / "src" / "app.js").exists()
        assert (temp_project_dir / "backend" / "src" / "app.test.js").exists()
        assert (temp_project_dir / "backend" / "src" / "routes" / "auth.route.js").exists()
        assert (temp_project_dir / "backend" / "src" / "services" / "auth.service.js").exists()
        assert (
            temp_project_dir / "backend" / "src" / "repositories" / "auth.repository.js"
        ).exists()
        assert (temp_project_dir / "backend" / "tests" / "auth.service.test.js").exists()
        assert (temp_project_dir / "backend" / "migrations" / "001_create_auth.sql").exists()
        assert (temp_project_dir / "backend" / "API_CONTRACT.md").exists()
        app_tsx = (temp_project_dir / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        assert "IBM Plex Sans" in app_tsx
        assert "Public Sans" in app_tsx

    def test_generate_python_backend_scaffold(self, temp_project_dir: Path):
        builder = ImplementationScaffoldBuilder(
            project_dir=temp_project_dir,
            name="demo",
            frontend="none",
            backend="python",
        )
        result = builder.generate(requirements=[{"spec_name": "core", "req_name": "flow"}])

        assert result["frontend_files"] == []
        assert (temp_project_dir / "backend" / "src" / "app.py").exists()
        assert (temp_project_dir / "backend" / "src" / "routes" / "core_route.py").exists()
        assert (temp_project_dir / "backend" / "src" / "services" / "core_service.py").exists()
        assert (
            temp_project_dir / "backend" / "src" / "repositories" / "core_repository.py"
        ).exists()
        assert (temp_project_dir / "backend" / "requirements.txt").exists()
        assert (temp_project_dir / "backend" / "tests" / "test_smoke.py").exists()
        assert (temp_project_dir / "backend" / "tests" / "test_core_service.py").exists()
        assert (temp_project_dir / "backend" / "migrations" / "001_create_core.sql").exists()

    def test_generate_vue_go_scaffold(self, temp_project_dir: Path):
        builder = ImplementationScaffoldBuilder(
            project_dir=temp_project_dir,
            name="demo",
            frontend="vue",
            backend="go",
        )
        result = builder.generate(requirements=[{"spec_name": "dashboard", "req_name": "insights"}])

        assert len(result["frontend_files"]) > 0
        assert len(result["backend_files"]) > 0
        assert (temp_project_dir / "frontend" / "src" / "App.vue").exists()
        assert (temp_project_dir / "frontend" / "vite.config.js").exists()
        assert (temp_project_dir / "backend" / "src" / "main.go").exists()

    def test_generate_frontend_framework_playbook_file(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-ui-contract.json").write_text(
            json.dumps(
                {
                    "framework_playbook": {
                        "framework": "React Native",
                        "implementation_modules": ["导航、权限、离线缓存先冻结后实现"],
                        "platform_constraints": ["iOS 与 Android 权限弹窗节奏必须分别验收"],
                        "execution_guardrails": ["先接原生能力边界，再扩业务组件"],
                        "native_capabilities": ["push notification / deep link / camera 权限"],
                        "validation_surfaces": ["iOS 真机导航与 Android 返回栈"],
                        "delivery_evidence": ["真机截图与权限矩阵"],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        builder = ImplementationScaffoldBuilder(
            project_dir=temp_project_dir,
            name="demo",
            frontend="react",
            backend="node",
        )

        result = builder.generate(requirements=[{"spec_name": "mobile", "req_name": "workflow"}])

        assert (temp_project_dir / "frontend" / "FRAMEWORK_PLAYBOOK.md").exists()
        content = (temp_project_dir / "frontend" / "FRAMEWORK_PLAYBOOK.md").read_text(
            encoding="utf-8"
        )
        readme = (temp_project_dir / "frontend" / "README.md").read_text(encoding="utf-8")
        assert "React Native" in content
        assert "push notification" in content
        assert "FRAMEWORK_PLAYBOOK.md" in readme
        assert any(path.endswith("FRAMEWORK_PLAYBOOK.md") for path in result["frontend_files"])

    def test_package_names_are_sanitized(self, temp_project_dir: Path):
        builder = ImplementationScaffoldBuilder(
            project_dir=temp_project_dir,
            name="用户认证系统",
            frontend="react",
            backend="node",
        )
        builder.generate(requirements=[{"spec_name": "auth", "req_name": "secure-authentication"}])

        frontend_pkg = (temp_project_dir / "frontend" / "package.json").read_text(encoding="utf-8")
        backend_pkg = (temp_project_dir / "backend" / "package.json").read_text(encoding="utf-8")
        assert '"name": "super-dev-app-frontend"' in frontend_pkg
        assert '"name": "super-dev-app-backend"' in backend_pkg

    @pytest.mark.parametrize(
        ("backend", "expected_files"),
        [
            ("rust", ["backend/Cargo.toml", "backend/src/main.rs"]),
            ("php", ["backend/composer.json", "backend/public/index.php"]),
            ("ruby", ["backend/Gemfile", "backend/app.rb"]),
            ("csharp", ["backend/Program.cs"]),
            (
                "kotlin",
                ["backend/build.gradle.kts", "backend/src/main/kotlin/com/superdev/Application.kt"],
            ),
            ("swift", ["backend/Package.swift", "backend/Sources/App/main.swift"]),
            ("elixir", ["backend/mix.exs", "backend/lib/super_dev_backend.ex"]),
            ("scala", ["backend/build.sbt", "backend/src/main/scala/Main.scala"]),
            ("dart", ["backend/pubspec.yaml", "backend/bin/server.dart"]),
        ],
    )
    def test_generate_extended_backend_scaffold(
        self, temp_project_dir: Path, backend: str, expected_files: list[str]
    ):
        builder = ImplementationScaffoldBuilder(
            project_dir=temp_project_dir,
            name="demo",
            frontend="none",
            backend=backend,
        )
        result = builder.generate(requirements=[{"spec_name": "core", "req_name": "flow"}])

        assert result["frontend_files"] == []
        assert len(result["backend_files"]) > 0
        for relative in expected_files:
            assert (temp_project_dir / relative).exists()

        assert (temp_project_dir / "backend" / "API_CONTRACT.md").exists()
        assert (temp_project_dir / "backend" / "migrations" / "001_create_core.sql").exists()
        if backend == "csharp":
            assert any((temp_project_dir / "backend").glob("*.csproj"))
