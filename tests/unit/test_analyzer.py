"""
Super Dev 分析器单元测试
"""

import json
from pathlib import Path

import pytest

from super_dev.analyzer import (
    ArchitectureReport,
    Dependency,
    DependencyGraphBuilder,
    DesignPattern,
    FeatureChecklistBuilder,
    ImpactAnalyzer,
    PatternType,
    ProjectAnalyzer,
    ProjectCategory,
    RegressionGuardBuilder,
    RepoMapBuilder,
    TechStack,
    detect_project_type,
    detect_tech_stack,
)
from super_dev.artifact_utils import sanitize_artifact_name


class TestProjectCategory:
    """测试项目分类枚举"""

    def test_category_values(self):
        """测试分类值"""
        assert ProjectCategory.FRONTEND.value == "frontend"
        assert ProjectCategory.BACKEND.value == "backend"
        assert ProjectCategory.FULLSTACK.value == "fullstack"
        assert ProjectCategory.MOBILE.value == "mobile"
        assert ProjectCategory.DESKTOP.value == "desktop"
        assert ProjectCategory.SERVERLESS.value == "serverless"
        assert ProjectCategory.UNKNOWN.value == "unknown"


class TestDependency:
    """测试依赖模型"""

    def test_dependency_creation(self):
        """测试依赖创建"""
        dep = Dependency(name="react", version="18.0.0", type="prod")

        assert dep.name == "react"
        assert dep.version == "18.0.0"
        assert dep.type == "prod"

    def test_dependency_str(self):
        """测试依赖字符串表示"""
        dep = Dependency(name="react", version="18.0.0")
        assert str(dep) == "react@18.0.0"

        dep_no_version = Dependency(name="vue")
        assert str(dep_no_version) == "vue"


class TestDesignPattern:
    """测试设计模式模型"""

    def test_pattern_creation(self):
        """测试模式创建"""
        pattern = DesignPattern(
            name=PatternType.SINGLETON,
            location=Path("/test/file.py"),
            description="单例模式实现",
            confidence=0.9,
        )

        assert pattern.name == PatternType.SINGLETON
        assert pattern.location == Path("/test/file.py")
        assert pattern.description == "单例模式实现"
        assert pattern.confidence == 0.9

    def test_pattern_to_dict(self):
        """测试模式转换为字典"""
        pattern = DesignPattern(
            name=PatternType.OBSERVER,
            location=Path("/test/observer.py"),
            description="观察者模式",
            confidence=0.8,
        )

        result = pattern.to_dict()

        assert result["name"] == "observer"
        assert result["location"] == "/test/observer.py"
        assert result["description"] == "观察者模式"
        assert result["confidence"] == 0.8


class TestTechStack:
    """测试技术栈模型"""

    def test_tech_stack_creation(self):
        """测试技术栈创建"""
        from super_dev.analyzer import FrameworkType

        stack = TechStack(
            category=ProjectCategory.FRONTEND,
            language="typescript",
            framework=FrameworkType.REACT,
            ui_library="@mui/material",
            state_management="zustand",
            dependencies=[],
        )

        assert stack.category == ProjectCategory.FRONTEND
        assert stack.language == "typescript"
        assert stack.ui_library == "@mui/material"

    def test_tech_stack_to_dict(self):
        """测试技术栈转换为字典"""
        stack = TechStack(
            category=ProjectCategory.FULLSTACK,
            language="javascript",
            framework="react",
            ui_library="antd",
            dependencies=[
                Dependency(name="react", version="18.0.0"),
                Dependency(name="antd", version="5.0.0"),
            ],
        )

        result = stack.to_dict()

        assert result["category"] == "fullstack"
        assert result["language"] == "javascript"
        assert result["framework"] == "react"
        assert result["ui_library"] == "antd"
        assert len(result["dependencies"]) == 2


class TestArchitectureReport:
    """测试架构报告模型"""

    def test_report_creation(self):
        """测试报告创建"""
        from super_dev.analyzer import FrameworkType

        report = ArchitectureReport(
            project_path=Path("/test/project"),
            category=ProjectCategory.BACKEND,
            tech_stack=TechStack(
                category=ProjectCategory.BACKEND,
                language="python",
                framework=FrameworkType.UNKNOWN,
                dependencies=[],
            ),
            file_count=100,
            total_lines=5000,
            languages_used={"Python": 5000},
        )

        assert report.project_path == Path("/test/project")
        assert report.category == ProjectCategory.BACKEND
        assert report.file_count == 100
        assert report.total_lines == 5000

    def test_report_to_dict(self):
        """测试报告转换为字典"""
        report = ArchitectureReport(
            project_path=Path("/test/project"),
            category=ProjectCategory.FRONTEND,
            tech_stack=TechStack(
                category=ProjectCategory.FRONTEND,
                language="typescript",
                framework="react",
                dependencies=[],
            ),
            file_count=50,
            total_lines=2500,
            languages_used={"TypeScript": 2000, "CSS": 500},
        )

        result = report.to_dict()

        assert result["project_path"] == "/test/project"
        assert result["category"] == "frontend"
        assert result["file_count"] == 50
        assert result["total_lines"] == 2500
        assert result["languages_used"]["TypeScript"] == 2000

    def test_report_to_markdown(self):
        """测试报告生成 Markdown"""
        report = ArchitectureReport(
            project_path=Path("/test/project"),
            category=ProjectCategory.FULLSTACK,
            tech_stack=TechStack(
                category=ProjectCategory.FULLSTACK,
                language="typescript",
                framework="react",
                ui_library="antd",
                state_management="zustand",
                testing_framework="jest",
                dependencies=[],
            ),
            file_count=200,
            total_lines=10000,
            languages_used={"TypeScript": 8000, "CSS": 2000},
        )

        markdown = report.to_markdown()

        assert "# 项目架构分析报告" in markdown
        assert "frontend" in markdown or "fullstack" in markdown
        assert "typescript" in markdown.lower()
        assert "200" in markdown  # 文件数量
        assert "10,000" in markdown or "10000" in markdown  # 代码行数


class TestDetectProjectType:
    """测试项目类型检测"""

    def test_detect_react_project(self, temp_project_dir: Path):
        """测试检测 React 项目"""
        # 创建 package.json
        package_json = temp_project_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "test-react-app",
                    "dependencies": {
                        "react": "^18.0.0",
                        "react-dom": "^18.0.0",
                    },
                }
            )
        )

        category = detect_project_type(temp_project_dir)
        assert category == ProjectCategory.FRONTEND

    def test_detect_fullstack_project(self, temp_project_dir: Path):
        """测试检测全栈项目"""
        package_json = temp_project_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "test-fullstack",
                    "dependencies": {
                        "react": "^18.0.0",
                        "express": "^4.18.0",
                    },
                }
            )
        )

        category = detect_project_type(temp_project_dir)
        assert category == ProjectCategory.FULLSTACK

    def test_detect_python_project(self, temp_project_dir: Path):
        """测试检测 Python 项目"""
        requirements_txt = temp_project_dir / "requirements.txt"
        requirements_txt.write_text("fastapi==0.100.0\nuvicorn==0.23.0\n")

        category = detect_project_type(temp_project_dir)
        assert category == ProjectCategory.BACKEND

    def test_detect_unknown_project(self, temp_project_dir: Path):
        """测试检测未知项目"""
        category = detect_project_type(temp_project_dir)
        assert category == ProjectCategory.UNKNOWN


class TestDetectTechStack:
    """测试技术栈检测"""

    def test_detect_react_stack(self, temp_project_dir: Path):
        """测试检测 React 技术栈"""
        package_json = temp_project_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "test",
                    "dependencies": {
                        "react": "^18.0.0",
                        "react-dom": "^18.0.0",
                        "antd": "^5.0.0",
                        "zustand": "^4.0.0",
                    },
                    "devDependencies": {
                        "vite": "^4.0.0",
                        "jest": "^29.0.0",
                    },
                }
            )
        )

        stack = detect_tech_stack(temp_project_dir)

        assert stack.language in ["javascript", "typescript"]
        assert stack.framework.value in ["react"]
        assert stack.ui_library == "antd"
        assert stack.state_management == "zustand"
        assert stack.build_tool == "vite"
        assert stack.testing_framework == "jest"

    def test_detect_python_stack(self, temp_project_dir: Path):
        """测试检测 Python 技术栈"""
        requirements_txt = temp_project_dir / "requirements.txt"
        requirements_txt.write_text("fastapi==0.100.0\n" "uvicorn==0.23.0\n" "pytest==7.4.0\n")

        stack = detect_tech_stack(temp_project_dir)

        assert stack.language == "python"
        assert stack.framework.value in ["fastapi", "unknown"]
        assert stack.testing_framework == "pytest"


class TestProjectAnalyzer:
    """测试项目分析器"""

    def test_analyzer_initialization(self, temp_project_dir: Path):
        """测试分析器初始化"""
        analyzer = ProjectAnalyzer(temp_project_dir)
        # 使用 resolve() 来处理 macOS 的 /var 软链接
        assert analyzer.project_path == temp_project_dir.resolve()

    def test_analyzer_nonexistent_path(self):
        """测试分析器处理不存在的路径"""
        with pytest.raises(FileNotFoundError):
            ProjectAnalyzer("/nonexistent/path")

    def test_analyze_simple_project(self, temp_project_dir: Path):
        """测试分析简单项目"""
        # 创建 package.json
        package_json = temp_project_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "test-app",
                    "dependencies": {
                        "react": "^18.0.0",
                    },
                }
            )
        )

        # 创建一些源文件
        src_dir = temp_project_dir / "src"
        src_dir.mkdir()

        (src_dir / "App.tsx").write_text("""
export function App() {
    return <div>Hello</div>;
}
""")

        (src_dir / "index.tsx").write_text("""
import { App } from './App';
console.log(App);
""")

        analyzer = ProjectAnalyzer(temp_project_dir)
        report = analyzer.analyze()

        assert report.category == ProjectCategory.FRONTEND
        assert report.file_count >= 2
        assert report.total_lines > 0
        assert len(report.languages_used) > 0

    def test_analyze_python_project(self, temp_project_dir: Path):
        """测试分析 Python 项目"""
        requirements_txt = temp_project_dir / "requirements.txt"
        requirements_txt.write_text("fastapi==0.100.0\n")

        src_dir = temp_project_dir / "src"
        src_dir.mkdir()

        (src_dir / "main.py").write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
""")

        analyzer = ProjectAnalyzer(temp_project_dir)
        report = analyzer.analyze()

        assert report.category == ProjectCategory.BACKEND
        assert "Python" in report.languages_used

    def test_analyzer_get_summary(self, temp_project_dir: Path):
        """测试获取项目摘要"""
        package_json = temp_project_dir / "package.json"
        package_json.write_text(json.dumps({"name": "test", "dependencies": {"react": "^18.0.0"}}))

        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("console.log('test');")

        analyzer = ProjectAnalyzer(temp_project_dir)
        summary = analyzer.get_summary()

        assert "项目类型:" in summary
        assert "编程语言:" in summary
        assert "框架:" in summary
        assert "文件数量:" in summary

    def test_analyzer_get_dependencies(self, temp_project_dir: Path):
        """测试获取依赖列表"""
        package_json = temp_project_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "test",
                    "dependencies": {
                        "react": "^18.0.0",
                        "antd": "^5.0.0",
                    },
                    "devDependencies": {
                        "jest": "^29.0.0",
                    },
                }
            )
        )

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.analyze()

        deps = analyzer.get_dependencies()

        assert len(deps) == 2
        dep_names = [d.name for d in deps]
        assert "react" in dep_names
        assert "antd" in dep_names

    def test_analyzer_get_language_distribution(self, temp_project_dir: Path):
        """测试获取语言分布"""
        package_json = temp_project_dir / "package.json"
        package_json.write_text(json.dumps({"name": "test", "dependencies": {"react": "^18.0.0"}}))

        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("console.log('test');\n" * 10)
        (src_dir / "styles.css").write_text(".test { color: red; }\n" * 10)

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.analyze()

        distribution = analyzer.get_language_distribution()

        assert len(distribution) > 0
        # 检查百分比总和约等于100
        total_percentage = sum(distribution.values())
        assert abs(total_percentage - 100.0) < 1.0  # 允许1%误差

    def test_analyzer_directory_structure(self, temp_project_dir: Path):
        """测试目录结构分析"""
        package_json = temp_project_dir / "package.json"
        package_json.write_text(json.dumps({"name": "test"}))

        # 创建目录结构和代码文件
        (temp_project_dir / "src").mkdir()
        (temp_project_dir / "src" / "components").mkdir()
        (temp_project_dir / "src" / "utils").mkdir()
        (temp_project_dir / "public").mkdir()

        # 创建代码文件（只有包含代码文件的目录才会被分析）
        (temp_project_dir / "src" / "App.tsx").write_text("export default function App() {}")
        (temp_project_dir / "src" / "components" / "Button.tsx").write_text(
            "export default function Button() {}"
        )
        (temp_project_dir / "src" / "utils" / "helper.ts").write_text("export function helper() {}")
        (temp_project_dir / "public" / "index.html").write_text("<html></html>")

        analyzer = ProjectAnalyzer(temp_project_dir)
        report = analyzer.analyze()

        # 检查目录结构
        assert "src" in report.directory_structure
        # src 应该有子目录
        assert "components" in report.directory_structure.get("src", {})
        assert "utils" in report.directory_structure.get("src", {})

    def test_analyzer_ignores_virtualenv_site_packages_for_patterns(self, temp_project_dir: Path):
        """设计模式分析不应扫描 .venv/site-packages。"""
        (temp_project_dir / "requirements.txt").write_text("fastapi==0.100.0\n", encoding="utf-8")
        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        (src_dir / "event_publisher.py").write_text(
            "def subscribe(observer):\n    return observer\n",
            encoding="utf-8",
        )

        venv_pkg = temp_project_dir / ".venv" / "Lib" / "site-packages"
        venv_pkg.mkdir(parents=True)
        (venv_pkg / "mypy_extensions.py").write_text(
            "class _TypedDictMeta:\n    _instance = None\n",
            encoding="utf-8",
        )

        analyzer = ProjectAnalyzer(temp_project_dir)
        report = analyzer.analyze()

        locations = {str(pattern.location) for pattern in report.design_patterns}
        assert any("event_publisher.py" in location for location in locations)
        assert not any("site-packages" in location or ".venv" in location for location in locations)


class TestRepoMapBuilder:
    def test_build_repo_map_for_python_project(self, temp_project_dir: Path):
        (temp_project_dir / "app").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "services").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "tests").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "pyproject.toml").write_text(
            "[project]\nname='demo'\n", encoding="utf-8"
        )
        (temp_project_dir / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (temp_project_dir / "app" / "server.py").write_text(
            "def run():\n    return True\n", encoding="utf-8"
        )
        (temp_project_dir / "services" / "billing.py").write_text(
            "class BillingService:\n    pass\n", encoding="utf-8"
        )
        (temp_project_dir / "tests" / "test_main.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8"
        )

        builder = RepoMapBuilder(temp_project_dir)
        report = builder.build()
        files = builder.write(report)

        assert report.project_name == sanitize_artifact_name(temp_project_dir.name)
        assert any(item.path == "main.py" for item in report.entry_points)
        assert any(item.path == "app" for item in report.top_modules)
        assert files["markdown"].exists()
        assert files["json"].exists()
        markdown = files["markdown"].read_text(encoding="utf-8")
        assert "# Repo Map" in markdown
        assert "Likely Entry Points" in markdown

    def test_codebase_intelligence_artifacts_use_active_change_prefix(
        self,
        temp_project_dir: Path,
    ) -> None:
        state_dir = temp_project_dir / ".super-dev"
        state_dir.mkdir(parents=True, exist_ok=True)
        change_dir = state_dir / "changes" / "Current_Change"
        change_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "workflow-state.json").write_text(
            json.dumps({"active_change_id": "Current_Change"}),
            encoding="utf-8",
        )
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "current-change-prd.md").write_text("# PRD\n", encoding="utf-8")
        (temp_project_dir / "pyproject.toml").write_text(
            "[project]\nname='demo'\n",
            encoding="utf-8",
        )
        (temp_project_dir / "main.py").write_text("print('hello')\n", encoding="utf-8")

        repo_map = RepoMapBuilder(temp_project_dir)
        dependency_graph = DependencyGraphBuilder(temp_project_dir)
        impact = ImpactAnalyzer(temp_project_dir)
        regression = RegressionGuardBuilder(temp_project_dir)

        assert {
            repo_map.project_name,
            dependency_graph.project_name,
            impact.project_name,
            regression.project_name,
        } == {"current-change"}
        written = [
            repo_map.write(repo_map.build()),
            dependency_graph.write(dependency_graph.build()),
            impact.write(impact.build(description="current change", files=["main.py"])),
            regression.write(regression.build(description="current change", files=["main.py"])),
        ]
        assert all(
            path.name.startswith("current-change-")
            for artifact_files in written
            for path in artifact_files.values()
        )


class TestFeatureChecklistBuilder:
    def test_build_feature_checklist_with_explicit_gap(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{temp_project_dir.name}-prd.md").write_text(
            "\n".join(
                [
                    "# PRD",
                    "",
                    "## 2. 功能范围",
                    "",
                    "### 用户登录",
                    "- 支持邮箱密码登录",
                    "",
                    "### 数据看板",
                    "- 提供运营数据面板",
                ]
            ),
            encoding="utf-8",
        )
        change_dir = temp_project_dir / ".super-dev" / "changes" / "demo-change"
        change_dir.mkdir(parents=True, exist_ok=True)
        (change_dir / "tasks.md").write_text(
            "\n".join(
                [
                    "# Tasks",
                    "",
                    "- [x] 用户登录",
                    "- [ ] 数据看板",
                ]
            ),
            encoding="utf-8",
        )
        (output_dir / f"{temp_project_dir.name}-research.md").write_text(
            "| 优先级 | 事项 | 说明 |\n|:---:|:---|:---|\n| P1 | 数据看板 | 未实现 |\n",
            encoding="utf-8",
        )

        builder = FeatureChecklistBuilder(temp_project_dir)
        report = builder.build()
        files = builder.write(report)

        assert report.status == "partial"
        assert report.high_priority_gap_count == 1
        assert report.missing_count >= 1
        assert report.total_features >= 2
        assert files["markdown"].exists()
        assert files["json"].exists()
        markdown = files["markdown"].read_text(encoding="utf-8")
        assert "# Feature Checklist" in markdown
        assert "数据看板" in markdown

    def test_feature_checklist_ignores_host_runtime_validation_noise(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{temp_project_dir.name}-prd.md").write_text(
            "\n".join(
                [
                    "# PRD",
                    "",
                    "## 2. 功能需求",
                    "",
                    "### 用户登录",
                    "- 支持邮箱密码登录",
                ]
            ),
            encoding="utf-8",
        )
        change_dir = temp_project_dir / ".super-dev" / "changes" / "demo-change"
        change_dir.mkdir(parents=True, exist_ok=True)
        (change_dir / "tasks.md").write_text(
            "# Tasks\n\n- [x] 支持邮箱密码登录\n", encoding="utf-8"
        )
        (output_dir / f"{temp_project_dir.name}-host-runtime-validation.md").write_text(
            "# Host Runtime Validation Matrix\n\n## Current Blockers\n\n- **trae** (validation) 宿主尚未完成真人运行时验收\n",
            encoding="utf-8",
        )

        builder = FeatureChecklistBuilder(temp_project_dir)
        report = builder.build()

        assert report.status == "ready"
        assert report.high_priority_gap_count == 0
        assert not any("真人运行时验收" in item.title for item in report.items)

    def test_feature_checklist_uses_only_active_change_inputs(self, temp_project_dir: Path) -> None:
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True)
        changes_dir = temp_project_dir / ".super-dev" / "changes"
        current_dir = changes_dir / "current-change"
        historical_dir = changes_dir / "historical"
        current_dir.mkdir(parents=True)
        historical_dir.mkdir(parents=True)
        (temp_project_dir / ".super-dev" / "workflow-state.json").write_text(
            json.dumps({"active_change_id": "current-change"}),
            encoding="utf-8",
        )
        (output_dir / "current-change-prd.md").write_text(
            "# PRD\n\n## 2. 功能需求\n\n### Current capability\n- Current behavior\n",
            encoding="utf-8",
        )
        (output_dir / "historical-prd.md").write_text(
            "# PRD\n\n## 2. 功能需求\n\n### Historical capability\n- Legacy behavior\n",
            encoding="utf-8",
        )
        (current_dir / "tasks.md").write_text(
            "# Tasks\n\n- [x] Current behavior\n",
            encoding="utf-8",
        )
        (historical_dir / "tasks.md").write_text(
            "# Tasks\n\n- [ ] Historical capability\n",
            encoding="utf-8",
        )
        (output_dir / "historical-research.md").write_text(
            "| Priority | Item | Status |\n|:--:|:--|:--|\n| P1 | Historical capability | missing |\n",
            encoding="utf-8",
        )

        builder = FeatureChecklistBuilder(temp_project_dir)
        report = builder.build()
        files = builder.write(report)

        assert report.project_name == "current-change"
        assert report.status == "ready"
        assert report.total_features == 1
        assert report.high_priority_gap_count == 0
        assert files["json"].name == "current-change-feature-checklist.json"
        assert all("Historical" not in item.title for item in report.items)


class TestImpactAnalyzer:
    def test_build_impact_analysis_from_description_and_files(self, temp_project_dir: Path):
        (temp_project_dir / "pyproject.toml").write_text(
            "[project]\nname='demo'\n", encoding="utf-8"
        )
        (temp_project_dir / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (temp_project_dir / "services").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "services" / "auth.py").write_text(
            "class AuthService:\n    def login(self):\n        return True\n",
            encoding="utf-8",
        )
        (temp_project_dir / "api").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "api" / "routes.py").write_text(
            "def login_route():\n    return {'ok': True}\n",
            encoding="utf-8",
        )

        analyzer = ImpactAnalyzer(temp_project_dir)
        report = analyzer.build(description="修改登录流程", files=["services/auth.py"])
        files = analyzer.write(report)

        assert report.risk_level in {"medium", "high"}
        assert report.affected_modules
        assert any(
            item.path.lower() in {"services", "services/auth.py"} or "auth" in item.path.lower()
            for item in report.affected_modules
        )
        assert any("Authentication" in item for item in report.regression_focus)
        assert files["markdown"].exists()
        assert files["json"].exists()


class TestRegressionGuardBuilder:
    def test_build_regression_guard_from_description_and_files(self, temp_project_dir: Path):
        (temp_project_dir / "pyproject.toml").write_text(
            "[project]\nname='demo'\n", encoding="utf-8"
        )
        (temp_project_dir / "services").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "services" / "auth.py").write_text(
            "class AuthService:\n    def login(self):\n        return True\n",
            encoding="utf-8",
        )
        (temp_project_dir / "api").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / "api" / "routes.py").write_text(
            "def login_route():\n    return {'ok': True}\n",
            encoding="utf-8",
        )

        builder = RegressionGuardBuilder(temp_project_dir)
        report = builder.build(description="修改登录流程", files=["services/auth.py"])
        files = builder.write(report)

        assert report.risk_level in {"medium", "high"}
        assert (
            report.high_priority_checks or report.medium_priority_checks or report.supporting_checks
        )
        assert report.recommended_commands
        assert files["markdown"].exists()
        assert files["json"].exists()
        markdown = files["markdown"].read_text(encoding="utf-8")
        assert "# Regression Guard" in markdown
        assert "Recommended Commands" in markdown
