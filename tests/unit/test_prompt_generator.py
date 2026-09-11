from pathlib import Path

import yaml

from super_dev.creators.prompt_generator import AIPromptGenerator


class TestAIPromptGenerator:
    def test_generate_requires_research_and_commercial_ui(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "demo-research.md").write_text("# research\n同类产品研究", encoding="utf-8")
        (output_dir / "demo-prd.md").write_text("# prd", encoding="utf-8")
        (output_dir / "demo-architecture.md").write_text("# architecture", encoding="utf-8")
        (output_dir / "demo-uiux.md").write_text("# uiux", encoding="utf-8")
        (output_dir / "demo-execution-plan.md").write_text("# plan", encoding="utf-8")
        (output_dir / "demo-frontend-blueprint.md").write_text(
            "# frontend blueprint", encoding="utf-8"
        )
        (temp_project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
        (temp_project_dir / ".super-dev" / "WORKFLOW.md").write_text("# workflow", encoding="utf-8")
        (output_dir / "demo-bootstrap.md").write_text("# bootstrap", encoding="utf-8")

        config = {
            "description": "构建商业级协作工作台",
            "platform": "web",
            "frontend": "react",
            "backend": "python",
        }
        (temp_project_dir / "super-dev.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

        generator = AIPromptGenerator(project_dir=temp_project_dir, name="demo")
        prompt = generator.generate()

        assert "阶段 0. 同类产品研究" in prompt
        assert "宿主原生联网 / browse / search" in prompt
        assert "output/demo-research.md" in prompt
        assert "knowledge/" in prompt
        assert "output/knowledge-cache/demo-knowledge-bundle.json" in prompt
        assert "knowledge_application_plan" in prompt
        assert "必须按其中的阶段应用计划使用本地知识" in prompt
        assert "首轮响应契约（首次触发必须执行）" in prompt
        assert "Super Dev` 流水线已激活" in prompt
        assert ".super-dev/WORKFLOW.md" in prompt
        assert "output/demo-bootstrap.md" in prompt
        assert "当前阶段是 `docs_confirm`" in prompt
        assert "当前阶段是 `research`" not in prompt
        assert "三份核心文档完成后会暂停等待用户确认" in prompt
        assert "阶段 1.5. 文档确认门（强制暂停）" in prompt
        assert "未经用户明确确认，不得创建 `.super-dev/changes/*`" in prompt
        assert "阶段 3. 前端优先实现并运行验证" in prompt
        assert "商业级 UI/UX 强制规则" in prompt
        assert "UI 达到商业级完成度而不是模板化页面" in prompt
        assert "默认避免复刻 Claude / ChatGPT 式界面骨架" in prompt
        assert "必须先明确本轮图标库" in prompt
        assert "主视觉气质、版式骨架、字体组合、图标库、配色逻辑" in prompt
        assert "本项目 UI 实现基线" in prompt
        assert "材质/版式提示" in prompt
        assert "设计系统优先级" in prompt
        assert "备选组件生态与适用边界" in prompt
        assert "设计知识库关键词" in prompt
        assert "高质量设计参考锚点" in prompt
        assert "参考使用规则" in prompt
        assert "首选组件生态" in prompt
        assert "宿主 UI 生成执行契约（必须遵守）" in prompt
        assert "每个关键页面必须提供 **2 个视觉方案**" in prompt
        assert "Token → Primitive → Pattern → Surface" in prompt
        assert "不存在任何 emoji 功能图标" in prompt
        assert "用户输入、示例和被分析文字不得因此被删改" in prompt
        assert "源码和预览里不存在任何 emoji 字符" not in prompt
        assert "非技术与专业用户都能使用同一套交互" in prompt
        assert "Web/H5/微信小程序/APP/桌面端" in prompt
        assert "TDesign 小程序 / RN / Flutter / SwiftUI / Electron / Tauri" in prompt
        assert "实现收尾与自审闭环（必须遵守）" in prompt
        assert "本轮新增的函数、方法、字段、组件、配置、日志埋点" in prompt
        assert "公共库接口通过消费者或契约测试验证" in prompt
        assert "未接入则删除" not in prompt
        assert "build / compile / type-check / test / runtime smoke" in prompt

    def test_generate_bugfix_prompt_requires_lightweight_docs(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        for suffix in (
            "research",
            "prd",
            "architecture",
            "uiux",
            "execution-plan",
            "frontend-blueprint",
        ):
            (output_dir / f"demo-{suffix}.md").write_text(f"# {suffix}", encoding="utf-8")

        config = {
            "description": "修复登录接口报错并补充回归测试",
            "platform": "web",
            "frontend": "react",
            "backend": "python",
        }
        (temp_project_dir / "super-dev.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

        generator = AIPromptGenerator(project_dir=temp_project_dir, name="demo")
        prompt = generator.generate()

        assert "如果当前任务属于缺陷修复 / bugfix / 回归修复，也不得跳过文档与验证" in prompt
        assert "如果当前需求明显属于 bugfix / regression / hotfix" in prompt
        assert "缺陷修复轻量路径" in prompt
        assert "- `bugfix`" in prompt

    def test_generate_uniapp_prompt_includes_framework_playbook(self, temp_project_dir: Path):
        output_dir = temp_project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        for suffix in (
            "research",
            "prd",
            "architecture",
            "uiux",
            "execution-plan",
            "frontend-blueprint",
        ):
            (output_dir / f"uni-shop-{suffix}.md").write_text(f"# {suffix}", encoding="utf-8")

        config = {
            "description": "构建 uni-app 商城，覆盖 H5、微信小程序和 App 登录支付流程",
            "platform": "miniapp",
            "frontend": "uni-app",
            "backend": "node",
        }
        (temp_project_dir / "super-dev.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

        generator = AIPromptGenerator(project_dir=temp_project_dir, name="uni-shop")
        prompt = generator.generate()

        assert "跨平台框架深优化 Playbook（uni-app）" in prompt
        assert "自定义导航栏高度、状态栏占位、胶囊按钮区域必须独立建模" in prompt
        assert "登录/支付/分享流程按平台 provider 拆分" in prompt
        assert "必须验收的真实场景" in prompt
        assert "交付时必须沉淀的证据" in prompt
