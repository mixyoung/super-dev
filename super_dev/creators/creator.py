"""
项目创建器 - 核心协调器

开发：Excellent（11964948@qq.com）
功能：从一句话描述到完整项目规范
作用：协调文档生成、Spec 创建和 AI 提示词生成
创建时间：2025-12-30
"""

import json
from pathlib import Path

from super_dev.artifact_utils import ui_contract_filename

from .document_generator import DocumentGenerator
from .prompt_generator import AIPromptGenerator
from .spec_builder import SpecBuilder


class ProjectCreator:
    """项目创建器 - 一键从想法到规范"""

    def __init__(
        self,
        project_dir: Path,
        name: str,
        description: str,
        request_mode: str = "feature",
        platform: str = "web",
        frontend: str = "next",
        backend: str = "node",
        domain: str = "",
        ui_library: str | None = None,
        style_solution: str | None = None,
        state_management: list[str] | None = None,
        testing_frameworks: list[str] | None = None,
        language_preferences: list[str] | None = None,
        knowledge_summary: dict | None = None,
    ):
        """初始化项目创建器"""
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.description = description
        self.request_mode = request_mode if request_mode in {"feature", "bugfix"} else "feature"
        self.platform = platform
        self.frontend = frontend
        self.backend = backend
        self.domain = domain
        self.ui_library = ui_library
        self.style_solution = style_solution
        self.state_management = state_management or []
        self.testing_frameworks = testing_frameworks or []
        self.language_preferences = language_preferences or []

        # 确保输出目录存在
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(exist_ok=True)

        # 初始化子模块
        self.doc_generator = DocumentGenerator(
            name=name,
            description=description,
            request_mode=self.request_mode,
            platform=platform,
            frontend=frontend,
            backend=backend,
            domain=domain,
            ui_library=ui_library,
            style_solution=style_solution,
            state_management=state_management,
            testing_frameworks=testing_frameworks,
            language_preferences=language_preferences,
            knowledge_summary=knowledge_summary,
        )
        self.spec_builder = SpecBuilder(
            project_dir=self.project_dir, name=name, description=description
        )
        self.prompt_generator = AIPromptGenerator(project_dir=self.project_dir, name=name)

    def generate_documents(self) -> dict:
        """生成所有文档 (PRD, 架构, UI/UX)"""
        docs = {}

        # 1. PRD
        prd_path = self.output_dir / f"{self.name}-prd.md"
        prd_content = self.doc_generator.generate_prd()
        prd_path.write_text(prd_content, encoding="utf-8")
        docs["prd"] = str(prd_path)

        # 2. 架构文档
        arch_path = self.output_dir / f"{self.name}-architecture.md"
        arch_content = self.doc_generator.generate_architecture()
        arch_path.write_text(arch_content, encoding="utf-8")
        docs["architecture"] = str(arch_path)

        # 3. UI/UX 文档
        uiux_path = self.output_dir / f"{self.name}-uiux.md"
        uiux_content = self.doc_generator.generate_uiux()
        uiux_path.write_text(uiux_content, encoding="utf-8")
        docs["uiux"] = str(uiux_path)

        ui_contract_path = self.output_dir / ui_contract_filename(self.name)
        ui_contract_path.write_text(
            json.dumps(self.doc_generator.generate_ui_contract(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        docs["ui_contract"] = str(ui_contract_path)

        # 4. 执行路线图
        scenario = self.doc_generator.requirement_parser.detect_scenario(self.project_dir)
        request_mode = (
            self.request_mode
            or self.doc_generator.requirement_parser.detect_request_mode(self.description)
        )
        plan_path = self.output_dir / f"{self.name}-execution-plan.md"
        plan_content = self.doc_generator.generate_execution_plan(
            scenario=scenario,
            request_mode=request_mode,
        )
        plan_path.write_text(plan_content, encoding="utf-8")
        docs["plan"] = str(plan_path)

        # 5. 前端蓝图
        frontend_blueprint_path = self.output_dir / f"{self.name}-frontend-blueprint.md"
        frontend_blueprint_content = self.doc_generator.generate_frontend_blueprint()
        frontend_blueprint_path.write_text(frontend_blueprint_content, encoding="utf-8")
        docs["frontend_blueprint"] = str(frontend_blueprint_path)

        return docs

    def create_spec(self) -> str:
        """创建 Spec 规范"""
        # 生成需求列表
        requirements = self.doc_generator.extract_requirements()

        # 创建 Spec 变更提案
        change_id = self.spec_builder.create_change(
            requirements=requirements,
            tech_stack={
                "platform": self.platform,
                "frontend": self.frontend,
                "backend": self.backend,
                "domain": self.domain,
            },
        )

        return change_id

    def generate_ai_prompt(self) -> str:
        """生成 AI 提示词"""
        prompt_file = self.output_dir / f"{self.name}-ai-prompt.md"
        prompt_content = self.prompt_generator.generate()
        prompt_file.write_text(prompt_content, encoding="utf-8")
        return str(prompt_file)
