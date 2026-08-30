"""
Super Dev 分析器数据模型
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal


class ProjectCategory(Enum):
    """项目分类"""

    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    SERVERLESS = "serverless"
    UNKNOWN = "unknown"


class FrameworkType(Enum):
    """框架类型"""

    # 前端框架
    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"
    NEXTJS = "nextjs"
    NUXT = "nuxt"
    REMIX = "remix"

    # 后端框架
    EXPRESS = "express"
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    SPRING = "spring"
    RAILS = "rails"
    GIN = "gin"
    ECHO = "echo"

    # 移动框架
    REACT_NATIVE = "react_native"
    FLUTTER = "flutter"
    IONIC = "ionic"

    # 桌面框架
    ELECTRON = "electron"
    TAURI = "tauri"

    UNKNOWN = "unknown"


@dataclass
class Dependency:
    """依赖信息"""

    name: str
    version: str = ""
    type: Literal["prod", "dev", "peer"] = "prod"
    description: str = ""
    homepage: str = ""
    licenses: str = ""

    def __str__(self) -> str:
        if self.version:
            return f"{self.name}@{self.version}"
        return self.name


@dataclass
class TechStack:
    """技术栈信息"""

    category: ProjectCategory
    language: str
    framework: FrameworkType | str
    ui_library: str = ""
    state_management: str = ""
    build_tool: str = ""
    testing_framework: str = ""
    dependencies: list[Dependency] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        # 处理 framework 可能是字符串或枚举
        framework_value = (
            self.framework.value if isinstance(self.framework, FrameworkType) else self.framework
        )

        return {
            "category": self.category.value,
            "language": self.language,
            "framework": framework_value,
            "ui_library": self.ui_library,
            "state_management": self.state_management,
            "build_tool": self.build_tool,
            "testing_framework": self.testing_framework,
            "dependencies": [str(d) for d in self.dependencies],
        }


class PatternType(Enum):
    """设计模式类型"""

    # 创建型模式
    SINGLETON = "singleton"
    FACTORY = "factory"
    BUILDER = "builder"
    PROTOTYPE = "prototype"

    # 结构型模式
    ADAPTER = "adapter"
    DECORATOR = "decorator"
    FACADE = "facade"
    PROXY = "proxy"
    COMPOSITE = "composite"
    BRIDGE = "bridge"
    FLYWEIGHT = "flyweight"

    # 行为型模式
    STRATEGY = "strategy"
    OBSERVER = "observer"
    COMMAND = "command"
    TEMPLATE_METHOD = "template_method"
    CHAIN_OF_RESPONSIBILITY = "chain_of_responsibility"
    ITERATOR = "iterator"
    MEDIATOR = "mediator"
    MEMENTO = "memento"
    STATE = "state"
    VISITOR = "visitor"


class ArchitecturePattern(Enum):
    """架构模式"""

    LAYERED = "layered"  # 分层架构
    MVC = "mvc"  # MVC
    MVP = "mvp"  # MVP
    MVVM = "mvvm"  # MVVM
    CLEAN_ARCHITECTURE = "clean_architecture"  # 整洁架构
    HEXAGONAL = "hexagonal"  # 六边形架构
    MICROSERVICES = "microservices"  # 微服务
    SERVERLESS = "serverless"  # 无服务器
    EVENT_DRIVEN = "event_driven"  # 事件驱动
    PLUGIN = "plugin"  # 插件架构


@dataclass
class DesignPattern:
    """设计模式信息"""

    name: PatternType
    location: Path  # 使用该模式的文件路径
    description: str = ""
    confidence: float = 1.0  # 识别置信度 0-1

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name.value,
            "location": self.location.as_posix(),
            "description": self.description,
            "confidence": self.confidence,
        }


@dataclass
class ArchitectureReport:
    """架构分析报告"""

    project_path: Path
    category: ProjectCategory
    tech_stack: TechStack
    architecture_pattern: ArchitecturePattern | None = None
    design_patterns: list[DesignPattern] = field(default_factory=list)
    directory_structure: dict = field(default_factory=dict)
    file_count: int = 0
    total_lines: int = 0
    languages_used: dict[str, int] = field(default_factory=dict)  # 语言 -> 行数

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "project_path": self.project_path.as_posix(),
            "category": self.category.value,
            "tech_stack": self.tech_stack.to_dict(),
            "architecture_pattern": (
                self.architecture_pattern.value if self.architecture_pattern else None
            ),
            "design_patterns": [p.to_dict() for p in self.design_patterns],
            "directory_structure": self.directory_structure,
            "file_count": self.file_count,
            "total_lines": self.total_lines,
            "languages_used": self.languages_used,
        }

    def to_markdown(self) -> str:
        """生成 Markdown 报告"""
        # 处理 framework 可能是字符串或枚举
        framework_value = (
            self.tech_stack.framework.value
            if isinstance(self.tech_stack.framework, FrameworkType)
            else self.tech_stack.framework
        )

        lines = [
            "# 项目架构分析报告",
            "",
            f"**项目路径**: `{self.project_path}`",
            f"**项目类型**: {self.category.value}",
            "",
            "## 技术栈",
            "",
            f"- **编程语言**: {self.tech_stack.language}",
            f"- **框架**: {framework_value}",
        ]

        if self.tech_stack.ui_library:
            lines.append(f"- **UI 库**: {self.tech_stack.ui_library}")
        if self.tech_stack.state_management:
            lines.append(f"- **状态管理**: {self.tech_stack.state_management}")
        if self.tech_stack.build_tool:
            lines.append(f"- **构建工具**: {self.tech_stack.build_tool}")
        if self.tech_stack.testing_framework:
            lines.append(f"- **测试框架**: {self.tech_stack.testing_framework}")

        if self.architecture_pattern:
            lines.extend(
                [
                    "",
                    "## 架构模式",
                    "",
                    f"识别到: **{self.architecture_pattern.value}**",
                ]
            )

        if self.design_patterns:
            lines.extend(
                [
                    "",
                    "## 设计模式",
                    "",
                ]
            )
            for pattern in self.design_patterns:
                lines.append(f"- **{pattern.name.value}**: `{pattern.location}`")
                if pattern.description:
                    lines.append(f"  - {pattern.description}")

        lines.extend(
            [
                "",
                "## 项目统计",
                "",
                f"- **文件数量**: {self.file_count}",
                f"- **代码行数**: {self.total_lines:,}",
            ]
        )

        if self.languages_used:
            lines.append("- **语言分布**:")
            for lang, count in sorted(
                self.languages_used.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / self.total_lines * 100) if self.total_lines else 0
                lines.append(f"  - {lang}: {count:,} 行 ({percentage:.1f}%)")

        if self.tech_stack.dependencies:
            lines.extend(
                [
                    "",
                    f"## 主要依赖 ({len(self.tech_stack.dependencies)})",
                    "",
                ]
            )
            for dep in self.tech_stack.dependencies[:20]:  # 只显示前20个
                lines.append(f"- {dep}")

            if len(self.tech_stack.dependencies) > 20:
                lines.append(f"- ... 还有 {len(self.tech_stack.dependencies) - 20} 个依赖")

        lines.append("")
        return "\n".join(lines)


# 项目类型别名（向后兼容）
ProjectType = ProjectCategory
