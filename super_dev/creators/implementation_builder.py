"""
宿主实现参考生成器

根据结构化需求生成前端/后端实现参考模板，帮助宿主从文档阶段稳定进入实现阶段。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from super_dev.artifact_utils import ui_contract_filename

from .implementation_project_templates_mixin import ImplementationProjectTemplatesMixin


class ImplementationScaffoldBuilder(ImplementationProjectTemplatesMixin):
    """项目宿主实现参考生成器"""

    def __init__(
        self,
        project_dir: Path,
        name: str,
        frontend: str,
        backend: str,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.frontend = frontend
        self.backend = backend
        self.package_name = self._sanitize_package_name(name)
        self.ui_contract = self._load_ui_contract()

    def _sanitize_package_name(self, value: str) -> str:
        cleaned = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
        cleaned = re.sub(r"-{2,}", "-", cleaned)
        return cleaned or "super-dev-app"

    def _load_ui_contract(self) -> dict[str, Any]:
        contract_path = self.project_dir / "output" / ui_contract_filename(self.name)
        if contract_path.exists():
            try:
                payload = json.loads(contract_path.read_text(encoding="utf-8"))
                return payload if isinstance(payload, dict) else {}
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _font_stack(self) -> str:
        typography = self.ui_contract.get("typography_preset", {})
        heading = str(typography.get("heading") or "").strip()
        body = str(typography.get("body") or "").strip()
        fonts = [
            font
            for font in (heading, body, "Noto Sans SC", "PingFang SC", "Segoe UI", "sans-serif")
            if font
        ]
        quoted = [f"'{font}'" if " " in font and font != "sans-serif" else font for font in fonts]
        return ",".join(quoted)

    def _framework_playbook(self) -> dict:
        playbook = self.ui_contract.get("framework_playbook")
        return playbook if isinstance(playbook, dict) else {}

    def _render_framework_playbook_markdown(self) -> str:
        playbook = self._framework_playbook()
        if not playbook:
            return ""
        sections = [
            "# Framework Playbook",
            "",
            f"- Framework: {playbook.get('framework', 'Unknown')}",
            "",
            "## Implementation Modules",
        ]
        for item in playbook.get("implementation_modules", []):
            sections.append(f"- {item}")
        sections.extend(["", "## Platform Constraints"])
        for item in playbook.get("platform_constraints", []):
            sections.append(f"- {item}")
        sections.extend(["", "## Execution Guardrails"])
        for item in playbook.get("execution_guardrails", []):
            sections.append(f"- {item}")
        sections.extend(["", "## Native Capabilities"])
        for item in playbook.get("native_capabilities", []):
            sections.append(f"- {item}")
        sections.extend(["", "## Validation Surfaces"])
        for item in playbook.get("validation_surfaces", []):
            sections.append(f"- {item}")
        sections.extend(["", "## Delivery Evidence"])
        for item in playbook.get("delivery_evidence", []):
            sections.append(f"- {item}")
        sections.append("")
        return "\n".join(sections)

    def generate(self, requirements: list[dict]) -> dict:
        """生成前后端实现参考模板"""
        module_requirements = self._build_module_requirements(requirements)
        result: dict[str, list[str]] = {
            "frontend_files": [],
            "backend_files": [],
        }

        if self.frontend != "none":
            result["frontend_files"] = self._generate_frontend(module_requirements)

        if self.backend != "none":
            result["backend_files"] = self._generate_backend(module_requirements)

        return result

    def _generate_frontend(self, module_requirements: dict[str, list[str]]) -> list[str]:
        frontend_dir = self.project_dir / "frontend"
        src_dir = frontend_dir / "src"
        modules_dir = src_dir / "modules"
        modules_dir.mkdir(parents=True, exist_ok=True)

        unique_modules = list(module_requirements.keys())

        files: list[str] = []

        frontend_kind = self.frontend.lower()
        if frontend_kind == "react":
            files.extend(
                self._generate_react_frontend(
                    frontend_dir,
                    src_dir,
                    modules_dir,
                    unique_modules,
                    module_requirements,
                )
            )
        elif frontend_kind == "vue":
            files.extend(
                self._generate_vue_frontend(
                    frontend_dir,
                    src_dir,
                    modules_dir,
                    unique_modules,
                    module_requirements,
                )
            )
        elif frontend_kind == "svelte":
            files.extend(
                self._generate_svelte_frontend(
                    frontend_dir,
                    src_dir,
                    modules_dir,
                    unique_modules,
                    module_requirements,
                )
            )
        elif frontend_kind == "angular":
            files.extend(
                self._generate_angular_frontend(
                    frontend_dir,
                    src_dir,
                    unique_modules,
                    module_requirements,
                )
            )
        else:
            # 默认回落到 React
            files.extend(
                self._generate_react_frontend(
                    frontend_dir,
                    src_dir,
                    modules_dir,
                    unique_modules,
                    module_requirements,
                )
            )

        readme_file = frontend_dir / "README.md"
        readme_sections = [
            "# Frontend Scaffold",
            "",
            "## Run",
            "",
            "```bash",
            "npm install",
            "npm run dev",
            "```",
            "",
        ]
        playbook = self._framework_playbook()
        if playbook:
            readme_sections.extend(
                [
                    "## Framework Playbook",
                    "",
                    f"- Framework: {playbook.get('framework', 'Unknown')}",
                    f"- Native capabilities: {', '.join(playbook.get('native_capabilities', [])[:3]) or 'n/a'}",
                    f"- Validation surfaces: {', '.join(playbook.get('validation_surfaces', [])[:3]) or 'n/a'}",
                    "",
                    "Implement the frontend against `FRAMEWORK_PLAYBOOK.md` before expanding business modules.",
                    "",
                ]
            )
        readme_file.write_text("\n".join(readme_sections), encoding="utf-8")
        files.append(str(readme_file))

        playbook_content = self._render_framework_playbook_markdown()
        if playbook_content:
            playbook_file = frontend_dir / "FRAMEWORK_PLAYBOOK.md"
            playbook_file.write_text(playbook_content, encoding="utf-8")
            files.append(str(playbook_file))

        return files

    def _generate_backend(self, module_requirements: dict[str, list[str]]) -> list[str]:
        backend_dir = self.project_dir / "backend"
        src_dir = backend_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        unique_modules = list(module_requirements.keys())

        files: list[str] = []
        backend_kind = self.backend.lower()
        if backend_kind == "python":
            files.extend(self._generate_python_backend(backend_dir, src_dir, module_requirements))
        elif backend_kind == "node":
            files.extend(self._generate_node_backend(backend_dir, src_dir, module_requirements))
        elif backend_kind == "go":
            app_file = src_dir / "main.go"
            app_file.write_text(self._build_go_app(unique_modules), encoding="utf-8")
            files.append(str(app_file))
        elif backend_kind == "java":
            app_file = (
                backend_dir / "src" / "main" / "java" / "com" / "superdev" / "Application.java"
            )
            app_file.parent.mkdir(parents=True, exist_ok=True)
            app_file.write_text(self._build_java_app(), encoding="utf-8")
            files.append(str(app_file))

            pom_file = backend_dir / "pom.xml"
            pom_file.write_text(self._build_java_pom(), encoding="utf-8")
            files.append(str(pom_file))
        elif backend_kind == "rust":
            files.extend(self._generate_rust_backend(backend_dir, src_dir, unique_modules))
        elif backend_kind == "php":
            files.extend(self._generate_php_backend(backend_dir, unique_modules))
        elif backend_kind == "ruby":
            files.extend(self._generate_ruby_backend(backend_dir, unique_modules))
        elif backend_kind == "csharp":
            files.extend(self._generate_csharp_backend(backend_dir, unique_modules))
        elif backend_kind == "kotlin":
            files.extend(self._generate_kotlin_backend(backend_dir, unique_modules))
        elif backend_kind == "swift":
            files.extend(self._generate_swift_backend(backend_dir, unique_modules))
        elif backend_kind == "elixir":
            files.extend(self._generate_elixir_backend(backend_dir, unique_modules))
        elif backend_kind == "scala":
            files.extend(self._generate_scala_backend(backend_dir, unique_modules))
        elif backend_kind == "dart":
            files.extend(self._generate_dart_backend(backend_dir, unique_modules))
        else:
            # 未知后端类型，回落到 node
            files.extend(self._generate_node_backend(backend_dir, src_dir, module_requirements))

        api_contract = backend_dir / "API_CONTRACT.md"
        api_contract.write_text(self._build_api_contract(unique_modules), encoding="utf-8")
        files.append(str(api_contract))
        files.extend(self._generate_sql_migrations(backend_dir, unique_modules))

        return files

    def _generate_python_backend(
        self,
        backend_dir: Path,
        src_dir: Path,
        module_requirements: dict[str, list[str]],
    ) -> list[str]:
        files: list[str] = []
        files.extend(self._generate_python_feature_pack(src_dir, module_requirements))

        app_file = src_dir / "app.py"
        app_file.write_text(self._build_fastapi_app(module_requirements), encoding="utf-8")
        files.append(str(app_file))

        requirements_file = backend_dir / "requirements.txt"
        requirements_file.write_text(
            "fastapi>=0.110.0\nuvicorn>=0.27.0\npytest>=7.0.0\npydantic>=2.0.2\n",
            encoding="utf-8",
        )
        files.append(str(requirements_file))

        tests_dir = backend_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        smoke_test = tests_dir / "test_smoke.py"
        smoke_test.write_text(
            ("def test_backend_scaffold_smoke() -> None:\n" "    assert True\n"),
            encoding="utf-8",
        )
        files.append(str(smoke_test))
        files.extend(self._generate_python_tests(tests_dir, module_requirements))
        return files

    def _generate_node_backend(
        self,
        backend_dir: Path,
        src_dir: Path,
        module_requirements: dict[str, list[str]],
    ) -> list[str]:
        files: list[str] = []
        files.extend(self._generate_node_feature_pack(src_dir, module_requirements))

        package_json = {
            "name": f"{self.package_name}-backend",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "node src/app.js",
                "start": "node src/app.js",
                "test": "node --test",
            },
            "dependencies": {
                "express": "^4.19.0",
            },
        }
        package_file = backend_dir / "package.json"
        package_file.write_text(
            json.dumps(package_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        files.append(str(package_file))

        app_file = src_dir / "app.js"
        app_file.write_text(self._build_express_app(module_requirements), encoding="utf-8")
        files.append(str(app_file))

        test_file = src_dir / "app.test.js"
        test_file.write_text(
            (
                "const test = require('node:test');\n"
                "const assert = require('node:assert/strict');\n\n"
                "test('backend scaffold smoke', () => {\n"
                "  assert.equal(1 + 1, 2);\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files.append(str(test_file))
        tests_dir = backend_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        files.extend(self._generate_node_tests(tests_dir, module_requirements))
        return files

    def _generate_rust_backend(
        self, backend_dir: Path, src_dir: Path, modules: list[str]
    ) -> list[str]:
        files: list[str] = []
        route_lines = [
            (
                f'        .route("/api/{self._safe_route_segment(module_name)}", '
                f"get({self._safe_identifier(module_name)}_handler))"
            )
            for module_name in modules
        ]
        handler_lines = []
        for module_name in modules:
            handler = self._safe_identifier(module_name)
            handler_lines.extend(
                [
                    f"async fn {handler}_handler() -> Json<Value> {{",
                    f'    Json(json!({{"module": "{module_name}", "status": "todo"}}))',
                    "}",
                    "",
                ]
            )

        cargo_file = backend_dir / "Cargo.toml"
        cargo_file.write_text(
            (
                "[package]\n"
                f'name = "{self.package_name}-backend"\n'
                'version = "0.1.0"\n'
                'edition = "2021"\n\n'
                "[dependencies]\n"
                'axum = "0.7"\n'
                'tokio = { version = "1", features = ["full"] }\n'
                'serde_json = "1"\n'
            ),
            encoding="utf-8",
        )
        files.append(str(cargo_file))

        main_file = src_dir / "main.rs"
        main_file.write_text(
            (
                "use axum::{routing::get, Json, Router};\n"
                "use serde_json::{json, Value};\n"
                "use std::net::SocketAddr;\n\n"
                "async fn health_handler() -> Json<Value> {\n"
                '    Json(json!({"status": "ok"}))\n'
                "}\n\n" + "\n".join(handler_lines) + "\n"
                "#[tokio::main]\n"
                "async fn main() {\n"
                "    let app = Router::new()\n"
                '        .route("/health", get(health_handler))\n'
                + ("\n".join(route_lines) + "\n" if route_lines else "")
                + "        ;\n\n"
                "    let addr = SocketAddr::from(([0, 0, 0, 0], 3001));\n"
                '    println!("Backend scaffold running on http://{}", addr);\n'
                '    let listener = tokio::net::TcpListener::bind(addr).await.expect("bind failed");\n'
                '    axum::serve(listener, app).await.expect("server failed");\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(main_file))
        return files

    def _generate_php_backend(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        route_blocks = [
            (
                f"if ($path === '/api/{self._safe_route_segment(module_name)}') {{\n"
                f"    echo json_encode(['module' => '{module_name}', 'status' => 'todo']);\n"
                "    return;\n"
                "}\n"
            )
            for module_name in modules
        ]

        composer_file = backend_dir / "composer.json"
        composer_file.write_text(
            json.dumps(
                {
                    "name": f"{self.package_name}/backend",
                    "type": "project",
                    "require": {"php": "^8.2"},
                    "scripts": {"serve": "php -S 0.0.0.0:3001 -t public"},
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        files.append(str(composer_file))

        public_dir = backend_dir / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        index_file = public_dir / "index.php"
        index_file.write_text(
            (
                "<?php\n"
                "header('Content-Type: application/json');\n"
                "$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);\n\n"
                "if ($path === '/health') {\n"
                "    echo json_encode(['status' => 'ok']);\n"
                "    return;\n"
                "}\n\n" + "".join(route_blocks) + "\n"
                "http_response_code(404);\n"
                "echo json_encode(['error' => 'not-found']);\n"
            ),
            encoding="utf-8",
        )
        files.append(str(index_file))
        return files

    def _generate_ruby_backend(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        route_blocks = [
            (
                f"get '/api/{self._safe_route_segment(module_name)}' do\n"
                f"  {{ module: '{module_name}', status: 'todo' }}.to_json\n"
                "end\n\n"
            )
            for module_name in modules
        ]

        gem_file = backend_dir / "Gemfile"
        gem_file.write_text(
            ("source 'https://rubygems.org'\n\n" "gem 'sinatra'\n" "gem 'json'\n"),
            encoding="utf-8",
        )
        files.append(str(gem_file))

        app_file = backend_dir / "app.rb"
        app_file.write_text(
            (
                "require 'sinatra'\n"
                "require 'json'\n\n"
                "set :bind, '0.0.0.0'\n"
                "set :port, 3001\n\n"
                "before do\n"
                "  content_type :json\n"
                "end\n\n"
                "get '/health' do\n"
                "  { status: 'ok' }.to_json\n"
                "end\n\n" + "".join(route_blocks) + "not_found do\n"
                "  status 404\n"
                "  { error: 'not-found' }.to_json\n"
                "end\n"
            ),
            encoding="utf-8",
        )
        files.append(str(app_file))
        return files

    def _generate_csharp_backend(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        route_lines = [
            (
                f'app.MapGet("/api/{self._safe_route_segment(module_name)}", '
                f'() => Results.Json(new {{ module = "{module_name}", status = "todo" }}));'
            )
            for module_name in modules
        ]

        csproj_file = backend_dir / f"{self.package_name}.csproj"
        csproj_file.write_text(
            (
                '<Project Sdk="Microsoft.NET.Sdk.Web">\n'
                "  <PropertyGroup>\n"
                "    <TargetFramework>net8.0</TargetFramework>\n"
                "    <Nullable>enable</Nullable>\n"
                "    <ImplicitUsings>enable</ImplicitUsings>\n"
                "  </PropertyGroup>\n"
                "</Project>\n"
            ),
            encoding="utf-8",
        )
        files.append(str(csproj_file))

        app_file = backend_dir / "Program.cs"
        app_file.write_text(
            (
                "var builder = WebApplication.CreateBuilder(args);\n"
                "var app = builder.Build();\n\n"
                'app.MapGet("/health", () => Results.Json(new { status = "ok" }));\n'
                + "\n".join(route_lines)
                + "\n\n"
                'app.Run("http://0.0.0.0:3001");\n'
            ),
            encoding="utf-8",
        )
        files.append(str(app_file))
        return files

    def _generate_kotlin_backend(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        route_lines = [
            (
                f'        get("/api/{self._safe_route_segment(module_name)}") {{\n'
                f'            call.respond(mapOf("module" to "{module_name}", "status" to "todo"))\n'
                "        }\n"
            )
            for module_name in modules
        ]

        gradle_file = backend_dir / "build.gradle.kts"
        gradle_file.write_text(
            (
                "plugins {\n"
                '    kotlin("jvm") version "1.9.22"\n'
                "    application\n"
                "}\n\n"
                "repositories {\n"
                "    mavenCentral()\n"
                "}\n\n"
                "dependencies {\n"
                '    implementation("io.ktor:ktor-server-core:2.3.7")\n'
                '    implementation("io.ktor:ktor-server-cio:2.3.7")\n'
                '    implementation("io.ktor:ktor-server-content-negotiation:2.3.7")\n'
                '    implementation("io.ktor:ktor-serialization-kotlinx-json:2.3.7")\n'
                '    implementation("ch.qos.logback:logback-classic:1.4.14")\n'
                "}\n\n"
                "application {\n"
                '    mainClass.set("com.superdev.ApplicationKt")\n'
                "}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(gradle_file))

        settings_file = backend_dir / "settings.gradle.kts"
        settings_file.write_text(
            f'rootProject.name = "{self.package_name}-backend"\n', encoding="utf-8"
        )
        files.append(str(settings_file))

        app_file = backend_dir / "src" / "main" / "kotlin" / "com" / "superdev" / "Application.kt"
        app_file.parent.mkdir(parents=True, exist_ok=True)
        app_file.write_text(
            (
                "package com.superdev\n\n"
                "import io.ktor.serialization.kotlinx.json.*\n"
                "import io.ktor.server.application.*\n"
                "import io.ktor.server.engine.*\n"
                "import io.ktor.server.cio.*\n"
                "import io.ktor.server.plugins.contentnegotiation.*\n"
                "import io.ktor.server.response.*\n"
                "import io.ktor.server.routing.*\n\n"
                "fun main() {\n"
                '    embeddedServer(CIO, port = 3001, host = "0.0.0.0") {\n'
                "        install(ContentNegotiation) { json() }\n"
                "        routing {\n"
                '            get("/health") { call.respond(mapOf("status" to "ok")) }\n'
                + "".join(route_lines)
                + "        }\n"
                "    }.start(wait = true)\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(app_file))
        return files

    def _generate_swift_backend(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        route_lines = [
            (
                f'app.get("api", "{self._safe_route_segment(module_name)}") {{ _ in\n'
                f'    ["module": "{module_name}", "status": "todo"]\n'
                "}\n\n"
            )
            for module_name in modules
        ]

        package_file = backend_dir / "Package.swift"
        package_file.write_text(
            (
                "// swift-tools-version:5.9\n"
                "import PackageDescription\n\n"
                "let package = Package(\n"
                f'    name: "{self.package_name}-backend",\n'
                "    platforms: [.macOS(.v13)],\n"
                "    dependencies: [\n"
                '        .package(url: "https://github.com/vapor/vapor.git", from: "4.92.0")\n'
                "    ],\n"
                "    targets: [\n"
                "        .executableTarget(\n"
                '            name: "App",\n'
                '            dependencies: [.product(name: "Vapor", package: "vapor")]\n'
                "        )\n"
                "    ]\n"
                ")\n"
            ),
            encoding="utf-8",
        )
        files.append(str(package_file))

        main_file = backend_dir / "Sources" / "App" / "main.swift"
        main_file.parent.mkdir(parents=True, exist_ok=True)
        main_file.write_text(
            (
                "import Vapor\n\n"
                "let app = Application(.development)\n"
                "defer { app.shutdown() }\n\n"
                'app.get("health") { _ in ["status": "ok"] }\n'
                + "".join(route_lines)
                + 'app.http.server.configuration.hostname = "0.0.0.0"\n'
                "app.http.server.configuration.port = 3001\n"
                "try app.run()\n"
            ),
            encoding="utf-8",
        )
        files.append(str(main_file))
        return files

    def _generate_elixir_backend(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        route_lines = [
            (
                f'    get "/api/{self._safe_route_segment(module_name)}" do\n'
                f'      send_resp(conn, 200, Jason.encode!(%{{module: "{module_name}", status: "todo"}}))\n'
                "    end\n"
            )
            for module_name in modules
        ]

        mix_file = backend_dir / "mix.exs"
        mix_file.write_text(
            (
                "defmodule SuperDevBackend.MixProject do\n"
                "  use Mix.Project\n\n"
                "  def project do\n"
                "    [\n"
                "      app: :super_dev_backend,\n"
                '      version: "0.1.0",\n'
                '      elixir: "~> 1.16",\n'
                "      start_permanent: Mix.env() == :prod,\n"
                "      deps: deps()\n"
                "    ]\n"
                "  end\n\n"
                "  def application do\n"
                "    [extra_applications: [:logger], mod: {SuperDevBackend.Application, []}]\n"
                "  end\n\n"
                "  defp deps do\n"
                "    [\n"
                '      {:plug_cowboy, "~> 2.7"},\n'
                '      {:jason, "~> 1.4"}\n'
                "    ]\n"
                "  end\n"
                "end\n"
            ),
            encoding="utf-8",
        )
        files.append(str(mix_file))

        app_file = backend_dir / "lib" / "super_dev_backend.ex"
        app_file.parent.mkdir(parents=True, exist_ok=True)
        app_file.write_text(
            (
                "defmodule SuperDevBackend.Router do\n"
                "  use Plug.Router\n\n"
                "  plug :match\n"
                "  plug :dispatch\n\n"
                '  get "/health" do\n'
                '    send_resp(conn, 200, Jason.encode!(%{status: "ok"}))\n'
                "  end\n\n" + "".join(route_lines) + "\n"
                "  match _ do\n"
                '    send_resp(conn, 404, Jason.encode!(%{error: "not-found"}))\n'
                "  end\n"
                "end\n\n"
                "defmodule SuperDevBackend.Application do\n"
                "  use Application\n\n"
                "  def start(_type, _args) do\n"
                "    children = [\n"
                "      {Plug.Cowboy, scheme: :http, plug: SuperDevBackend.Router, options: [port: 3001, ip: {0, 0, 0, 0}]}\n"
                "    ]\n\n"
                "    opts = [strategy: :one_for_one, name: SuperDevBackend.Supervisor]\n"
                "    Supervisor.start_link(children, opts)\n"
                "  end\n"
                "end\n"
            ),
            encoding="utf-8",
        )
        files.append(str(app_file))
        return files

    def _generate_scala_backend(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        route_lines = [
            (
                f'      path("api" / "{self._safe_route_segment(module_name)}") {{\n'
                f"        complete(HttpEntity(ContentTypes.`application/json`, "
                f'"{{\\"module\\":\\"{module_name}\\",\\"status\\":\\"todo\\"}}"))\n'
                "      }\n"
            )
            for module_name in modules
        ]

        sbt_file = backend_dir / "build.sbt"
        sbt_file.write_text(
            (
                f'name := "{self.package_name}-backend"\n'
                'version := "0.1.0"\n'
                'scalaVersion := "2.13.13"\n\n'
                "libraryDependencies ++= Seq(\n"
                '  "com.typesafe.akka" %% "akka-http" % "10.5.3",\n'
                '  "com.typesafe.akka" %% "akka-stream" % "2.8.5",\n'
                '  "com.typesafe.akka" %% "akka-actor-typed" % "2.8.5"\n'
                ")\n"
            ),
            encoding="utf-8",
        )
        files.append(str(sbt_file))

        app_file = backend_dir / "src" / "main" / "scala" / "Main.scala"
        app_file.parent.mkdir(parents=True, exist_ok=True)
        app_file.write_text(
            (
                "import akka.actor.typed.ActorSystem\n"
                "import akka.actor.typed.scaladsl.Behaviors\n"
                "import akka.http.scaladsl.Http\n"
                "import akka.http.scaladsl.model._\n"
                "import akka.http.scaladsl.server.Directives._\n"
                "import scala.concurrent.ExecutionContextExecutor\n\n"
                "object Main {\n"
                "  def main(args: Array[String]): Unit = {\n"
                '    implicit val system: ActorSystem[Nothing] = ActorSystem(Behaviors.empty, "super-dev-backend")\n'
                "    implicit val executionContext: ExecutionContextExecutor = system.executionContext\n\n"
                "    val route = concat(\n"
                '      path("health") {\n'
                '        complete(HttpEntity(ContentTypes.`application/json`, "{\\"status\\":\\"ok\\"}"))\n'
                "      },\n" + ",\n".join(route_lines) + "\n"
                "    )\n\n"
                '    Http().newServerAt("0.0.0.0", 3001).bind(route)\n'
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(app_file))
        return files

    def _generate_dart_backend(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        case_lines = [
            (
                f"    case '/api/{self._safe_route_segment(module_name)}':\n"
                f"      return _json({{'module': '{module_name}', 'status': 'todo'}});\n"
            )
            for module_name in modules
        ]

        pubspec_file = backend_dir / "pubspec.yaml"
        pubspec_file.write_text(
            (
                f"name: {self.package_name.replace('-', '_')}_backend\n"
                "description: Super Dev generated backend scaffold\n"
                "version: 0.1.0\n"
                "environment:\n"
                "  sdk: '>=3.3.0 <4.0.0'\n"
                "dependencies:\n"
                "  shelf: ^1.4.1\n"
                "  shelf_router: ^1.1.4\n"
            ),
            encoding="utf-8",
        )
        files.append(str(pubspec_file))

        server_file = backend_dir / "bin" / "server.dart"
        server_file.parent.mkdir(parents=True, exist_ok=True)
        server_file.write_text(
            (
                "import 'dart:convert';\n"
                "import 'dart:io';\n\n"
                "Response _json(Map<String, Object> payload, {int code = 200}) {\n"
                "  return Response(code,\n"
                "      body: jsonEncode(payload),\n"
                "      headers: {'content-type': 'application/json'});\n"
                "}\n\n"
                "class Response {\n"
                "  Response(this.statusCode, {required this.body, required this.headers});\n"
                "  final int statusCode;\n"
                "  final String body;\n"
                "  final Map<String, String> headers;\n"
                "}\n\n"
                "Future<void> main() async {\n"
                "  final server = await HttpServer.bind(InternetAddress.anyIPv4, 3001);\n"
                "  print('Backend scaffold running on http://0.0.0.0:3001');\n"
                "  await for (final request in server) {\n"
                "    final path = request.uri.path;\n"
                "    Response response;\n"
                "    switch (path) {\n"
                "      case '/health':\n"
                "        response = _json({'status': 'ok'});\n"
                "        break;\n" + "".join(case_lines) + "      default:\n"
                "        response = _json({'error': 'not-found'}, code: 404);\n"
                "    }\n"
                "    request.response.statusCode = response.statusCode;\n"
                "    response.headers.forEach(request.response.headers.set);\n"
                "    request.response.write(response.body);\n"
                "    await request.response.close();\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(server_file))
        return files

    def _generate_react_frontend(
        self,
        frontend_dir: Path,
        src_dir: Path,
        modules_dir: Path,
        unique_modules: list[str],
        module_requirements: dict[str, list[str]],
    ) -> list[str]:
        files: list[str] = []
        package_json = {
            "name": f"{self.package_name}-frontend",
            "version": "0.1.0",
            "private": True,
            "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
            "dependencies": {"react": "^18.3.0", "react-dom": "^18.3.0"},
            "devDependencies": {
                "vite": "^5.0.0",
                "@types/react": "^18.2.0",
                "@types/react-dom": "^18.2.0",
                "typescript": "^5.0.0",
            },
        }
        package_file = frontend_dir / "package.json"
        package_file.write_text(
            json.dumps(package_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        files.append(str(package_file))

        component_dir = src_dir / "components" / "ui"
        component_dir.mkdir(parents=True, exist_ok=True)
        button_file = component_dir / "button.tsx"
        button_file.write_text(self._build_react_button_component(), encoding="utf-8")
        files.append(str(button_file))

        app_file = src_dir / "App.tsx"
        app_file.write_text(self._build_react_app(unique_modules), encoding="utf-8")
        files.append(str(app_file))

        main_file = src_dir / "main.tsx"
        main_file.write_text(
            (
                "import React from 'react';\n"
                "import ReactDOM from 'react-dom/client';\n"
                "import App from './App';\n\n"
                "ReactDOM.createRoot(document.getElementById('root')!).render(\n"
                "  <React.StrictMode>\n"
                "    <App />\n"
                "  </React.StrictMode>\n"
                ");\n"
            ),
            encoding="utf-8",
        )
        files.append(str(main_file))

        index_file = frontend_dir / "index.html"
        index_file.write_text(self._build_index_html("root", "/src/main.tsx"), encoding="utf-8")
        files.append(str(index_file))

        for module_name in unique_modules:
            module_file = modules_dir / f"{module_name}.tsx"
            module_file.write_text(
                self._build_module_component(module_name, module_requirements.get(module_name, [])),
                encoding="utf-8",
            )
            files.append(str(module_file))

        return files

    def _generate_vue_frontend(
        self,
        frontend_dir: Path,
        src_dir: Path,
        modules_dir: Path,
        unique_modules: list[str],
        module_requirements: dict[str, list[str]],
    ) -> list[str]:
        files: list[str] = []
        package_json = {
            "name": f"{self.package_name}-frontend",
            "version": "0.1.0",
            "private": True,
            "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
            "dependencies": {"vue": "^3.4.0"},
            "devDependencies": {"vite": "^5.0.0", "@vitejs/plugin-vue": "^5.0.0"},
        }
        package_file = frontend_dir / "package.json"
        package_file.write_text(
            json.dumps(package_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        files.append(str(package_file))

        vite_file = frontend_dir / "vite.config.js"
        vite_file.write_text(
            (
                "import { defineConfig } from 'vite';\n"
                "import vue from '@vitejs/plugin-vue';\n\n"
                "export default defineConfig({\n"
                "  plugins: [vue()],\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files.append(str(vite_file))

        app_file = src_dir / "App.vue"
        app_file.write_text(self._build_vue_app(unique_modules), encoding="utf-8")
        files.append(str(app_file))

        main_file = src_dir / "main.js"
        main_file.write_text(
            (
                "import { createApp } from 'vue';\n"
                "import App from './App.vue';\n\n"
                "createApp(App).mount('#app');\n"
            ),
            encoding="utf-8",
        )
        files.append(str(main_file))

        index_file = frontend_dir / "index.html"
        index_file.write_text(self._build_index_html("app", "/src/main.js"), encoding="utf-8")
        files.append(str(index_file))

        for module_name in unique_modules:
            module_file = modules_dir / f"{module_name}.vue"
            module_file.write_text(
                self._build_vue_module(module_name, module_requirements.get(module_name, [])),
                encoding="utf-8",
            )
            files.append(str(module_file))

        return files

    def _generate_svelte_frontend(
        self,
        frontend_dir: Path,
        src_dir: Path,
        modules_dir: Path,
        unique_modules: list[str],
        module_requirements: dict[str, list[str]],
    ) -> list[str]:
        files: list[str] = []
        package_json = {
            "name": f"{self.package_name}-frontend",
            "version": "0.1.0",
            "private": True,
            "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
            "dependencies": {"svelte": "^4.2.0"},
            "devDependencies": {"vite": "^5.0.0", "@sveltejs/vite-plugin-svelte": "^3.0.0"},
        }
        package_file = frontend_dir / "package.json"
        package_file.write_text(
            json.dumps(package_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        files.append(str(package_file))

        vite_file = frontend_dir / "vite.config.js"
        vite_file.write_text(
            (
                "import { defineConfig } from 'vite';\n"
                "import { svelte } from '@sveltejs/vite-plugin-svelte';\n\n"
                "export default defineConfig({\n"
                "  plugins: [svelte()],\n"
                "});\n"
            ),
            encoding="utf-8",
        )
        files.append(str(vite_file))

        app_file = src_dir / "App.svelte"
        app_file.write_text(self._build_svelte_app(unique_modules), encoding="utf-8")
        files.append(str(app_file))

        main_file = src_dir / "main.js"
        main_file.write_text(
            (
                "import App from './App.svelte';\n\n"
                "const app = new App({\n"
                "  target: document.getElementById('app')\n"
                "});\n\n"
                "export default app;\n"
            ),
            encoding="utf-8",
        )
        files.append(str(main_file))

        index_file = frontend_dir / "index.html"
        index_file.write_text(self._build_index_html("app", "/src/main.js"), encoding="utf-8")
        files.append(str(index_file))

        for module_name in unique_modules:
            module_file = modules_dir / f"{module_name}.svelte"
            module_file.write_text(
                self._build_svelte_module(module_name, module_requirements.get(module_name, [])),
                encoding="utf-8",
            )
            files.append(str(module_file))

        return files

    def _generate_angular_frontend(
        self,
        frontend_dir: Path,
        src_dir: Path,
        unique_modules: list[str],
        module_requirements: dict[str, list[str]],
    ) -> list[str]:
        files: list[str] = []
        package_json = {
            "name": f"{self.package_name}-frontend",
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "start": "ng serve",
                "build": "ng build",
                "test": "ng test",
            },
            "dependencies": {
                "@angular/animations": "^17.0.0",
                "@angular/common": "^17.0.0",
                "@angular/compiler": "^17.0.0",
                "@angular/core": "^17.0.0",
                "@angular/forms": "^17.0.0",
                "@angular/platform-browser": "^17.0.0",
                "@angular/platform-browser-dynamic": "^17.0.0",
                "@angular/router": "^17.0.0",
                "rxjs": "^7.8.0",
                "zone.js": "^0.14.0",
            },
            "devDependencies": {
                "@angular/cli": "^17.0.0",
                "@angular/compiler-cli": "^17.0.0",
                "typescript": "^5.0.0",
            },
        }
        package_file = frontend_dir / "package.json"
        package_file.write_text(
            json.dumps(package_json, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        files.append(str(package_file))

        app_dir = src_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        component_file = app_dir / "app.component.ts"
        component_file.write_text(
            self._build_angular_component(unique_modules, module_requirements),
            encoding="utf-8",
        )
        files.append(str(component_file))

        module_file = app_dir / "app.module.ts"
        module_file.write_text(
            (
                "import { NgModule } from '@angular/core';\n"
                "import { BrowserModule } from '@angular/platform-browser';\n"
                "import { AppComponent } from './app.component';\n\n"
                "@NgModule({\n"
                "  declarations: [AppComponent],\n"
                "  imports: [BrowserModule],\n"
                "  bootstrap: [AppComponent],\n"
                "})\n"
                "export class AppModule {}\n"
            ),
            encoding="utf-8",
        )
        files.append(str(module_file))

        main_file = src_dir / "main.ts"
        main_file.write_text(
            (
                "import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';\n"
                "import { AppModule } from './app/app.module';\n\n"
                "platformBrowserDynamic()\n"
                "  .bootstrapModule(AppModule)\n"
                "  .catch(err => console.error(err));\n"
            ),
            encoding="utf-8",
        )
        files.append(str(main_file))

        index_file = frontend_dir / "index.html"
        index_file.write_text(self._build_index_html("app-root", "/src/main.ts"), encoding="utf-8")
        files.append(str(index_file))

        return files

    def _build_react_app(self, modules: list[str]) -> str:
        safe_name = (
            self.name.replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("{", "&#123;")
            .replace("}", "&#125;")
        )
        imports = [
            f"import {self._to_component(module)} from './modules/{module}';" for module in modules
        ]
        imports.append("import { Button } from './components/ui/button';")
        cards = [
            (
                f"        <section style={{border: '1px solid #e5e7eb', borderRadius: 12, padding: 16}}>\n"
                f"          <h3>{self._to_component(module)}</h3>\n"
                f"          <{self._to_component(module)} />\n"
                "        </section>"
            )
            for module in modules
        ]

        return (
            "import React from 'react';\n" + "\n".join(imports) + "\n\n"
            "export default function App() {\n"
            "  return (\n"
            f"    <main style={{maxWidth: 960, margin: '40px auto', fontFamily: \"{self._font_stack()}\"}}>\n"
            f"      <h1>{safe_name} 实现参考模板</h1>\n"
            "      <p>该页面由 Super Dev 生成作为宿主实施参考，按模块分区承接需求实现。</p>\n"
            "      <div style={{display: 'flex', gap: 12, margin: '16px 0 24px', flexWrap: 'wrap'}}>\n"
            "        <Button>查看核心文档</Button>\n"
            '        <Button variant="secondary">进入模块实现</Button>\n'
            "      </div>\n"
            "      <div style={{display: 'grid', gap: 12}}>\n" + "\n".join(cards) + "\n"
            "      </div>\n"
            "    </main>\n"
            "  );\n"
            "}\n"
        )

    def _build_react_button_component(self) -> str:
        return (
            "import React from 'react';\n\n"
            "type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {\n"
            "  variant?: 'primary' | 'secondary';\n"
            "};\n\n"
            "const baseStyle: React.CSSProperties = {\n"
            "  minHeight: 40,\n"
            "  padding: '0 16px',\n"
            "  borderRadius: 12,\n"
            "  border: '1px solid transparent',\n"
            "  fontWeight: 700,\n"
            "  cursor: 'pointer',\n"
            "};\n\n"
            "const variants: Record<'primary' | 'secondary', React.CSSProperties> = {\n"
            "  primary: {\n"
            "    background: 'var(--color-primary, #0f172a)',\n"
            "    color: '#ffffff',\n"
            "  },\n"
            "  secondary: {\n"
            "    background: 'var(--color-surface, #ffffff)',\n"
            "    color: 'var(--color-text, #0f172a)',\n"
            "    borderColor: 'var(--color-border, #cbd5e1)',\n"
            "  },\n"
            "};\n\n"
            "export function Button({ variant = 'primary', style, ...props }: ButtonProps) {\n"
            "  return <button {...props} style={{ ...baseStyle, ...variants[variant], ...style }} />;\n"
            "}\n"
        )

    def _build_module_component(self, module_name: str, req_names: list[str]) -> str:
        component = self._to_component(module_name)
        checklist = (
            "\n".join(f"        <li>{req}</li>" for req in req_names)
            or "        <li>待补充需求</li>"
        )
        return (
            "import React from 'react';\n\n"
            f"export default function {component}() {{\n"
            "  return (\n"
            "    <div>\n"
            f"      <p>{module_name} 模块初始实现参考已创建，可在此实现业务逻辑。</p>\n"
            "      <ul>\n"
            f"{checklist}\n"
            "      </ul>\n"
            "    </div>\n"
            "  );\n"
            "}\n"
        )

    def _build_express_app(self, module_requirements: dict[str, list[str]]) -> str:
        imports = []
        mount_lines = []
        for module_name in module_requirements:
            route_segment = self._safe_route_segment(module_name)
            variable = f"{self._safe_identifier(module_name)}Router"
            imports.append(f"const {variable} = require('./routes/{route_segment}.route');")
            mount_lines.append(f"app.use('/api/{route_segment}', {variable});")

        return (
            "const express = require('express');\n\n" + "\n".join(imports) + "\n\n"
            "const app = express();\n"
            "app.use(express.json());\n\n"
            "app.get('/health', (_req, res) => {\n"
            "  res.json({ status: 'ok' });\n"
            "});\n\n" + "\n".join(mount_lines) + "\n\n"
            "const port = process.env.PORT || 3001;\n"
            "app.listen(port, () => {\n"
            "  console.log(`Backend scaffold is running on http://localhost:${port}`);\n"
            "});\n"
        )

    def _build_fastapi_app(self, module_requirements: dict[str, list[str]]) -> str:
        imports = []
        include_routes = []
        for module_name in module_requirements:
            route_segment = self._safe_route_segment(module_name)
            variable = f"{self._safe_identifier(module_name)}_router"
            imports.append(f"from .routes.{route_segment}_route import router as {variable}")
            include_routes.append(f"app.include_router({variable})")

        return (
            "from fastapi import FastAPI\n" + "\n".join(imports) + "\n\n"
            "app = FastAPI(title='Super Dev Backend Scaffold')\n\n"
            "@app.get('/health')\n"
            "def health():\n"
            "    return {'status': 'ok'}\n\n" + "\n".join(include_routes) + "\n"
        )

    def _build_api_contract(self, modules: list[str]) -> str:
        lines = [
            "# API Contract (Scaffold)",
            "",
            "以下接口由 Super Dev 根据需求模块生成，后续请补充字段和鉴权细节。",
            "",
            "| Module | Method | Path | Purpose |",
            "|:---|:---|:---|:---|",
        ]
        for module_name in modules:
            route_segment = self._safe_route_segment(module_name)
            lines.append(
                f"| {module_name} | GET | /api/{route_segment} | 获取 {module_name} 模块初始数据 |"
            )
            lines.append(
                f"| {module_name} | POST | /api/{route_segment} | 创建 {module_name} 模块初始数据 |"
            )
        lines.append("")
        return "\n".join(lines)

    def _generate_node_feature_pack(
        self, src_dir: Path, module_requirements: dict[str, list[str]]
    ) -> list[str]:
        files: list[str] = []
        routes_dir = src_dir / "routes"
        services_dir = src_dir / "services"
        repositories_dir = src_dir / "repositories"
        routes_dir.mkdir(parents=True, exist_ok=True)
        services_dir.mkdir(parents=True, exist_ok=True)
        repositories_dir.mkdir(parents=True, exist_ok=True)

        for module_name in module_requirements:
            route_segment = self._safe_route_segment(module_name)
            identifier = self._safe_identifier(module_name)
            title = self._to_component(module_name)

            repository_file = repositories_dir / f"{route_segment}.repository.js"
            repository_file.write_text(
                (
                    f"const {identifier}Store = [];\n\n"
                    f"function list{title}() {{\n"
                    f"  return {identifier}Store;\n"
                    "}\n\n"
                    f"function create{title}(payload) {{\n"
                    f"  const record = {{ id: {identifier}Store.length + 1, ...payload }};\n"
                    f"  {identifier}Store.push(record);\n"
                    "  return record;\n"
                    "}\n\n"
                    f"module.exports = {{ list{title}, create{title} }};\n"
                ),
                encoding="utf-8",
            )
            files.append(str(repository_file))

            service_file = services_dir / f"{route_segment}.service.js"
            service_file.write_text(
                (
                    f"const repository = require('../repositories/{route_segment}.repository');\n\n"
                    f"function list{title}Items() {{\n"
                    f"  return repository.list{title}();\n"
                    "}\n\n"
                    f"function create{title}Item(payload) {{\n"
                    f"  return repository.create{title}(payload);\n"
                    "}\n\n"
                    f"module.exports = {{ list{title}Items, create{title}Item }};\n"
                ),
                encoding="utf-8",
            )
            files.append(str(service_file))

            route_file = routes_dir / f"{route_segment}.route.js"
            route_file.write_text(
                (
                    "const express = require('express');\n"
                    f"const service = require('../services/{route_segment}.service');\n\n"
                    "const router = express.Router();\n\n"
                    "router.get('/', (_req, res) => {\n"
                    "  res.json({\n"
                    f"    module: '{module_name}',\n"
                    f"    items: service.list{title}Items()\n"
                    "  });\n"
                    "});\n\n"
                    "router.post('/', (req, res) => {\n"
                    f"  const item = service.create{title}Item(req.body || {{ module: '{module_name}' }});\n"
                    "  res.status(201).json(item);\n"
                    "});\n\n"
                    "module.exports = router;\n"
                ),
                encoding="utf-8",
            )
            files.append(str(route_file))

        return files

    def _generate_node_tests(
        self, tests_dir: Path, module_requirements: dict[str, list[str]]
    ) -> list[str]:
        files: list[str] = []
        for module_name in module_requirements:
            route_segment = self._safe_route_segment(module_name)
            title = self._to_component(module_name)
            test_file = tests_dir / f"{route_segment}.service.test.js"
            test_file.write_text(
                (
                    "const test = require('node:test');\n"
                    "const assert = require('node:assert/strict');\n"
                    f"const service = require('../src/services/{route_segment}.service');\n\n"
                    f"test('{module_name} service scaffold', () => {{\n"
                    f"  const created = service.create{title}Item({{ name: 'sample' }});\n"
                    "  assert.equal(created.id > 0, true);\n"
                    f"  const items = service.list{title}Items();\n"
                    "  assert.equal(Array.isArray(items), true);\n"
                    "});\n"
                ),
                encoding="utf-8",
            )
            files.append(str(test_file))
        return files

    def _generate_python_feature_pack(
        self, src_dir: Path, module_requirements: dict[str, list[str]]
    ) -> list[str]:
        files: list[str] = []
        init_file = src_dir / "__init__.py"
        init_file.write_text("", encoding="utf-8")
        files.append(str(init_file))

        routes_dir = src_dir / "routes"
        services_dir = src_dir / "services"
        repositories_dir = src_dir / "repositories"
        routes_dir.mkdir(parents=True, exist_ok=True)
        services_dir.mkdir(parents=True, exist_ok=True)
        repositories_dir.mkdir(parents=True, exist_ok=True)
        for package_dir in (routes_dir, services_dir, repositories_dir):
            pkg_init = package_dir / "__init__.py"
            pkg_init.write_text("", encoding="utf-8")
            files.append(str(pkg_init))

        for module_name in module_requirements:
            route_segment = self._safe_route_segment(module_name)
            identifier = self._safe_identifier(module_name)
            title = self._to_component(module_name)

            repository_file = repositories_dir / f"{route_segment}_repository.py"
            repository_file.write_text(
                (
                    "from __future__ import annotations\n\n"
                    f"{identifier}_store: list[dict] = []\n\n"
                    f"def list_{identifier}() -> list[dict]:\n"
                    f"    return {identifier}_store\n\n"
                    f"def create_{identifier}(payload: dict) -> dict:\n"
                    f"    record = {{'id': len({identifier}_store) + 1, **payload}}\n"
                    f"    {identifier}_store.append(record)\n"
                    "    return record\n"
                ),
                encoding="utf-8",
            )
            files.append(str(repository_file))

            service_file = services_dir / f"{route_segment}_service.py"
            service_file.write_text(
                (
                    "from __future__ import annotations\n\n"
                    f"from ..repositories.{route_segment}_repository import create_{identifier}, list_{identifier}\n\n"
                    f"def list_{identifier}_items() -> list[dict]:\n"
                    f"    return list_{identifier}()\n\n"
                    f"def create_{identifier}_item(payload: dict) -> dict:\n"
                    f"    return create_{identifier}(payload)\n"
                ),
                encoding="utf-8",
            )
            files.append(str(service_file))

            route_file = routes_dir / f"{route_segment}_route.py"
            route_file.write_text(
                (
                    "from __future__ import annotations\n\n"
                    "from fastapi import APIRouter\n"
                    "from pydantic import BaseModel\n\n"
                    f"from ..services.{route_segment}_service import create_{identifier}_item, list_{identifier}_items\n\n"
                    f"class {title}CreateRequest(BaseModel):\n"
                    "    name: str = 'sample'\n\n"
                    f"router = APIRouter(prefix='/api/{route_segment}', tags=['{module_name}'])\n\n"
                    "@router.get('')\n"
                    f"def get_{identifier}_items() -> dict:\n"
                    "    return {\n"
                    f"        'module': '{module_name}',\n"
                    f"        'items': list_{identifier}_items(),\n"
                    "    }\n\n"
                    "@router.post('', status_code=201)\n"
                    f"def post_{identifier}_item(payload: {title}CreateRequest) -> dict:\n"
                    f"    return create_{identifier}_item(payload.model_dump())\n"
                ),
                encoding="utf-8",
            )
            files.append(str(route_file))

        return files

    def _generate_python_tests(
        self, tests_dir: Path, module_requirements: dict[str, list[str]]
    ) -> list[str]:
        files: list[str] = []
        for module_name in module_requirements:
            route_segment = self._safe_route_segment(module_name)
            identifier = self._safe_identifier(module_name)
            test_file = tests_dir / f"test_{route_segment}_service.py"
            test_file.write_text(
                (
                    "from pathlib import Path\n"
                    "import sys\n\n"
                    "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n\n"
                    f"from src.services.{route_segment}_service import create_{identifier}_item, list_{identifier}_items\n\n"
                    f"def test_{identifier}_service_scaffold() -> None:\n"
                    f"    created = create_{identifier}_item({{'name': 'sample'}})\n"
                    "    assert created['id'] > 0\n"
                    f"    items = list_{identifier}_items()\n"
                    "    assert isinstance(items, list)\n"
                ),
                encoding="utf-8",
            )
            files.append(str(test_file))
        return files

    def _generate_sql_migrations(self, backend_dir: Path, modules: list[str]) -> list[str]:
        files: list[str] = []
        migrations_dir = backend_dir / "migrations"
        migrations_dir.mkdir(parents=True, exist_ok=True)
        for index, module_name in enumerate(modules, start=1):
            route_segment = self._safe_route_segment(module_name)
            file_path = migrations_dir / f"{index:03d}_create_{route_segment}.sql"
            file_path.write_text(
                (
                    f"-- Super Dev scaffold migration for module: {module_name}\n"
                    f"CREATE TABLE IF NOT EXISTS {route_segment}_items (\n"
                    "  id INTEGER PRIMARY KEY,\n"
                    "  name VARCHAR(255) NOT NULL,\n"
                    "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
                    ");\n"
                ),
                encoding="utf-8",
            )
            files.append(str(file_path))
        return files

    def _build_go_app(self, modules: list[str]) -> str:
        handlers = []
        for module_name in modules:
            handler = self._safe_identifier(module_name)
            handlers.append(
                f"func {handler}Handler(w http.ResponseWriter, _ *http.Request) {{\n"
                '    w.Header().Set("Content-Type", "application/json")\n'
                f'    w.Write([]byte(`{{"module":"{module_name}","status":"todo"}}`))\n'
                "}\n"
            )

        routes = [
            f'    http.HandleFunc("/api/{self._safe_route_segment(module_name)}", {self._safe_identifier(module_name)}Handler)'
            for module_name in modules
        ]

        return (
            "package main\n\n"
            "import (\n"
            '    "log"\n'
            '    "net/http"\n'
            ")\n\n" + "\n".join(handlers) + "\n"
            "func healthHandler(w http.ResponseWriter, _ *http.Request) {\n"
            '    w.Header().Set("Content-Type", "application/json")\n'
            '    w.Write([]byte(`{"status":"ok"}`))\n'
            "}\n\n"
            "func main() {\n"
            '    http.HandleFunc("/health", healthHandler)\n' + "\n".join(routes) + "\n"
            '    log.Println("Backend scaffold running on :3001")\n'
            '    log.Fatal(http.ListenAndServe(":3001", nil))\n'
            "}\n"
        )

    def _build_java_app(self) -> str:
        return (
            "package com.superdev;\n\n"
            "import org.springframework.boot.SpringApplication;\n"
            "import org.springframework.boot.autoconfigure.SpringBootApplication;\n\n"
            "@SpringBootApplication\n"
            "public class Application {\n"
            "    public static void main(String[] args) {\n"
            "        SpringApplication.run(Application.class, args);\n"
            "    }\n"
            "}\n"
        )

    def _build_java_pom(self) -> str:
        return (
            '<project xmlns="http://maven.apache.org/POM/4.0.0" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 '
            'http://maven.apache.org/xsd/maven-4.0.0.xsd">\n'
            "  <modelVersion>4.0.0</modelVersion>\n"
            "  <groupId>com.superdev</groupId>\n"
            f"  <artifactId>{xml_escape(self.name)}-backend</artifactId>\n"
            "  <version>0.1.0</version>\n"
            "  <parent>\n"
            "    <groupId>org.springframework.boot</groupId>\n"
            "    <artifactId>spring-boot-starter-parent</artifactId>\n"
            "    <version>3.2.0</version>\n"
            "    <relativePath/>\n"
            "  </parent>\n"
            "  <properties>\n"
            "    <java.version>17</java.version>\n"
            "  </properties>\n"
            "  <dependencies>\n"
            "    <dependency>\n"
            "      <groupId>org.springframework.boot</groupId>\n"
            "      <artifactId>spring-boot-starter-web</artifactId>\n"
            "    </dependency>\n"
            "  </dependencies>\n"
            "</project>\n"
        )

    def _build_index_html(self, mount_id: str, entry_path: str) -> str:
        return (
            "<!doctype html>\n"
            '<html lang="zh-CN">\n'
            "  <head>\n"
            '    <meta charset="UTF-8" />\n'
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
            f"    <title>{self.name} Frontend</title>\n"
            "  </head>\n"
            "  <body>\n"
            f'    <div id="{mount_id}"></div>\n'
            f'    <script type="module" src="{entry_path}"></script>\n'
            "  </body>\n"
            "</html>\n"
        )

    def _build_vue_app(self, modules: list[str]) -> str:
        safe_name = (
            self.name.replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("{", "&#123;")
            .replace("}", "&#125;")
        )
        imports = [
            f"import {self._to_component(module)} from './modules/{module}.vue';"
            for module in modules
        ]
        cards = [
            (
                f'      <section class="card">\n'
                f"        <h3>{self._to_component(module)}</h3>\n"
                f"        <{self._to_component(module)} />\n"
                "      </section>"
            )
            for module in modules
        ]
        return (
            "<template>\n"
            '  <main class="shell">\n'
            f"    <h1>{safe_name} 实现参考模板</h1>\n"
            '    <div class="grid">\n' + "\n".join(cards) + "\n"
            "    </div>\n"
            "  </main>\n"
            "</template>\n\n"
            "<script setup>\n" + "\n".join(imports) + "\n"
            "</script>\n\n"
            "<style>\n"
            f".shell {{ max-width: 960px; margin: 40px auto; font-family: {self._font_stack()}; }}\n"
            ".grid { display: grid; gap: 12px; }\n"
            ".card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; }\n"
            "</style>\n"
        )

    def _build_vue_module(self, module_name: str, req_names: list[str]) -> str:
        list_items = "\n".join(f"  <li>{req}</li>" for req in req_names) or "  <li>待补充需求</li>"
        return (
            "<template>\n"
            f"  <p>{module_name} 模块初始实现参考已创建，可在此实现业务逻辑。</p>\n"
            "  <ul>\n"
            f"{list_items}\n"
            "  </ul>\n"
            "</template>\n"
        )

    def _build_svelte_app(self, modules: list[str]) -> str:
        safe_name = (
            self.name.replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("{", "&#123;")
            .replace("}", "&#125;")
        )
        imports = [
            f"import {self._to_component(module)} from './modules/{module}.svelte';"
            for module in modules
        ]
        cards = [
            (
                '  <section class="card">\n'
                f"    <h3>{self._to_component(module)}</h3>\n"
                f"    <{self._to_component(module)} />\n"
                "  </section>"
            )
            for module in modules
        ]
        return (
            "\n".join(imports) + "\n\n"
            f'<main class="shell">\n'
            f"  <h1>{safe_name} 实现参考模板</h1>\n"
            '  <div class="grid">\n' + "\n".join(cards) + "\n"
            "  </div>\n"
            "</main>\n\n"
            "<style>\n"
            f".shell {{ max-width: 960px; margin: 40px auto; font-family: {self._font_stack()}; }}\n"
            ".grid { display: grid; gap: 12px; }\n"
            ".card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; }\n"
            "</style>\n"
        )

    def _build_svelte_module(self, module_name: str, req_names: list[str]) -> str:
        items = "\n".join(f"<li>{req}</li>" for req in req_names) or "<li>待补充需求</li>"
        return (
            f"<p>{module_name} 模块初始实现参考已创建，可在此实现业务逻辑。</p>\n"
            "<ul>\n"
            f"{items}\n"
            "</ul>\n"
        )

    def _build_angular_component(
        self, modules: list[str], module_requirements: dict[str, list[str]]
    ) -> str:
        safe_name = (
            self.name.replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("{", "&#123;")
            .replace("}", "&#125;")
        )
        sections = []
        for module_name in modules:
            req_items = (
                "".join(f"  <li>{req}</li>" for req in module_requirements.get(module_name, []))
                or "  <li>待补充需求</li>"
            )
            sections.append(
                '<section style="border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:8px 0;">\n'
                f"  <h3>{self._to_component(module_name)}</h3>\n"
                f"  <p>{module_name} 模块初始实现参考已创建，可在此实现业务逻辑。</p>\n"
                "  <ul>\n"
                f"{req_items}\n"
                "  </ul>\n"
                "</section>"
            )
        return (
            "import { Component } from '@angular/core';\n\n"
            "@Component({\n"
            "  selector: 'app-root',\n"
            "  template: `\n"
            f'    <main style="max-width:960px;margin:40px auto;font-family:{self._font_stack()};">\n'
            f"      <h1>{safe_name} 实现参考模板</h1>\n"
            f"{' '.join(sections)}\n"
            "    </main>\n"
            "  `,\n"
            "})\n"
            "export class AppComponent {}\n"
        )

    def _build_module_requirements(self, requirements: list[dict]) -> dict[str, list[str]]:
        module_requirements: dict[str, list[str]] = {}
        for item in requirements:
            module = str(item.get("spec_name", "core")).strip() or "core"
            req_name = str(item.get("req_name", "todo")).strip() or "todo"
            existing = module_requirements.setdefault(module, [])
            if req_name not in existing:
                existing.append(req_name)
        if not module_requirements:
            module_requirements["core"] = ["core-flow"]
        return module_requirements

    def _safe_identifier(self, name: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else "_" for ch in name.lower())
        if not cleaned:
            return "module"
        if cleaned[0].isdigit():
            cleaned = f"m_{cleaned}"
        return cleaned

    def _safe_route_segment(self, name: str) -> str:
        cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in name.lower())
        cleaned = cleaned.strip("-_")
        return cleaned or "module"

    def _to_component(self, name: str) -> str:
        cleaned = "".join(ch if ch.isalnum() else "-" for ch in name)
        parts = [part for part in cleaned.split("-") if part]
        if not parts:
            return "Module"
        return "".join(part[:1].upper() + part[1:] for part in parts)

    # ------------------------------------------------------------------
    # Extended Backend Framework Scaffolds
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Database Migration Script Generation
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Docker Development Environment
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Environment Variable Management
    # ------------------------------------------------------------------
