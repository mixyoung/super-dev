"""
开发：Excellent（11964948@qq.com）
功能：Super Dev CLI 主入口
作用：提供命令行界面，统一访问所有功能
创建时间：2025-12-30
最后修改：2025-01-29
"""

import argparse
import importlib.util
import json
import os
import subprocess as _subprocess
import sys
import tempfile
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast

from . import __description__, __version__
from .catalogs import (
    CICD_PLATFORM_IDS,
    DOMAIN_IDS,
    FULL_FRONTEND_TEMPLATE_IDS,
    HOST_TOOL_IDS,
    PIPELINE_BACKEND_IDS,
    PIPELINE_FRONTEND_TEMPLATE_IDS,
    PLATFORM_IDS,
    PRIMARY_HOST_TOOL_IDS,
    PRODUCT_HOST_TOOL_IDS,
    SPECIAL_INSTALL_HOST_TOOL_IDS,
)
from .catalogs import (
    host_path_candidates as _host_path_candidates,
)
from .cli_analysis_mixin import CliAnalysisMixin
from .cli_deploy_runtime_mixin import CliDeployRuntimeMixin
from .cli_design_mixin import CliDesignMixin
from .cli_extension_mixin import CliExtensionMixin
from .cli_governance_mixin import CliGovernanceMixin
from .cli_host_ops_mixin import CliHostOpsMixin
from .cli_integration_runtime_mixin import CliIntegrationRuntimeMixin
from .cli_parser_mixin import CliParserMixin
from .cli_pipeline_runtime_mixin import CliPipelineRuntimeMixin
from .cli_release_quality_mixin import CliReleaseQualityMixin
from .cli_spec_mixin import CliSpecMixin
from .cli_workflow_runtime_mixin import CliWorkflowRuntimeMixin
from .config import get_config_manager
from .error_handler import handle_cli_error
from .review_state import (
    architecture_revision_file,
    docs_confirmation_file,
    load_architecture_revision,
    load_docs_confirmation,
    load_preview_confirmation,
    load_quality_revision,
    load_ui_revision,
    preview_confirmation_file,
    quality_revision_file,
    ui_revision_file,
)
from .terminal import (
    create_console,
)
from .utils import get_logger
from .workflow_guard import (
    docs_gate_status,
    preview_gate_status,
)

fcntl: Any = None
try:
    import fcntl as _fcntl

    fcntl = _fcntl
except ImportError:
    pass

RICH_AVAILABLE = importlib.util.find_spec("rich") is not None
host_path_candidates = _host_path_candidates
subprocess = _subprocess

CICDPlatform = Literal["github", "gitlab", "jenkins", "azure", "bitbucket", "all"]

SUPPORTED_PLATFORMS = list(PLATFORM_IDS)
SUPPORTED_PIPELINE_FRONTENDS = list(PIPELINE_FRONTEND_TEMPLATE_IDS)
SUPPORTED_INIT_FRONTENDS = list(FULL_FRONTEND_TEMPLATE_IDS)
SUPPORTED_PIPELINE_BACKENDS = list(PIPELINE_BACKEND_IDS)
SUPPORTED_DOMAINS = list(DOMAIN_IDS)
SUPPORTED_CICD = list(CICD_PLATFORM_IDS)
SUPPORTED_HOST_TOOLS = list(HOST_TOOL_IDS)
PRIMARY_SUPPORTED_HOST_TOOLS = list(PRIMARY_HOST_TOOL_IDS)
PRODUCT_SUPPORTED_HOST_TOOLS = list(PRODUCT_HOST_TOOL_IDS)
SPECIAL_INSTALL_HOST_TOOLS = list(SPECIAL_INSTALL_HOST_TOOL_IDS)


class SuperDevCLI(
    CliWorkflowRuntimeMixin,
    CliPipelineRuntimeMixin,
    CliIntegrationRuntimeMixin,
    CliParserMixin,
    CliAnalysisMixin,
    CliDesignMixin,
    CliExtensionMixin,
    CliReleaseQualityMixin,
    CliDeployRuntimeMixin,
    CliHostOpsMixin,
    CliSpecMixin,
    CliGovernanceMixin,
):
    """Super Dev 命令行接口"""

    @staticmethod
    def _display_final_trigger(profile) -> str:
        if getattr(profile, "host", "") == "codex":
            return "App/Desktop: /super-dev | 回退: super-dev: 你的需求"
        if getattr(profile, "host", "") == "codex-cli":
            return "CLI: $super-dev | 回退: super-dev: 你的需求"
        return str(profile.trigger_command).replace("<需求描述>", "你的需求")

    def __init__(self):
        self.console = create_console()
        self.parser = self._create_parser()
        self.logger = get_logger("cli", level="WARNING")  # CLI只记录WARNING及以上级别

    def _public_host_targets(self, *, integration_manager) -> list[str]:
        available_targets = [item.name for item in integration_manager.list_targets()]
        public_targets = [
            target for target in PRIMARY_SUPPORTED_HOST_TOOLS if target in available_targets
        ]
        return public_targets or available_targets

    def _print_public_help(self) -> None:
        self._print_banner()
        lines = [
            "Super Dev Public Help",
            "",
            "公开终端入口:",
            "  super-dev           打开宿主安装 / 接入引导",
            "  super-dev update    更新到最新版本",
            "  super-dev uninstall 完整清理宿主接入面",
            "",
            "宿主内使用:",
            "  slash 宿主: /super-dev 你的需求",
            "  文本宿主: super-dev: 你的需求",
            "  流程继续: 在宿主里说“继续当前流程”",
            "  查询下一步: 在宿主里说“现在下一步是什么”",
            "  高级维护: /super-dev-work / /super-dev-run / /super-dev-review",
            "",
            "说明:",
            "  默认帮助只展示公开产品入口。",
            "  内部维护 / 治理命令请使用: super-dev --help-all",
        ]
        for line in lines:
            self.console.print(line)

    def run(self, args: list | None = None) -> int:
        """
        运行 CLI

        Args:
            args: 命令行参数

        Returns:
            退出码
        """
        argv = list(args) if args is not None else sys.argv[1:]

        # P1-8: 启动版本检查（非阻塞，缓存 24h，仅在有子命令时检查）
        if argv and not argv[0].startswith("-"):
            try:
                from .version_check import check_for_update

                hint = check_for_update()
                if hint:
                    self.console.print(f"[dim]{hint}[/dim]")
            except Exception:
                pass

        # 兼容 `super-dev help` / `super-dev version` 这类用户习惯输入
        if len(argv) == 1 and argv[0] == "help":
            self._print_public_help()
            return 0
        if len(argv) == 1 and argv[0] in {"--help", "-h"}:
            self._print_public_help()
            return 0
        if len(argv) == 1 and argv[0] in {"--help-all", "help-all"}:
            self._print_banner()
            self.console.print("Super Dev Internal Command Index")
            self.console.print(
                "以下命令属于内部维护 / 治理 / 高级用法，不属于普通用户公开终端入口。"
            )
            self.console.print(
                "普通用户公开终端入口仍然只有 super-dev / super-dev update / super-dev uninstall。"
            )
            self.console.print("")
            help_text = self.parser.format_help()
            filtered_help = "\n".join(
                line for line in help_text.splitlines() if "==SUPPRESS==" not in line
            )
            self.console.print(filtered_help.rstrip())
            return 0
        if len(argv) == 1 and argv[0] == "version":
            self.console.print(f"super-dev {__version__}")
            return 0

        # 未知单词命令 → 显示错误和建议
        if self._is_unknown_command(argv):
            unknown = argv[0]
            suggestions = self._suggest_commands(unknown)
            self.console.print(f"[red]未知命令: '{unknown}'[/red]")
            self.console.print(f"你是否想输入: {', '.join(suggestions)}?")
            self.console.print(
                "运行 'super-dev --help' 查看公开入口，运行 'super-dev --help-all' 查看内部维护命令。"
            )
            return 2

        # 直达入口：`super-dev <需求描述>`
        if self._is_direct_requirement_input(argv):
            try:
                description, direct_overrides = self._parse_direct_requirement_args(argv)
            except ValueError as exc:
                self.console.print(f"[red]{exc}[/red]")
                return 2
            return self._run_direct_requirement(description, direct_overrides)

        parsed_args = self.parser.parse_args(argv)

        # 根据 -v/--verbose / --quiet 调整日志级别
        if getattr(parsed_args, "quiet", False):
            from .utils.structured_logging import setup_structured_logging

            setup_structured_logging(level="ERROR")
        elif getattr(parsed_args, "verbose", 0) >= 2:
            from .utils.structured_logging import setup_structured_logging

            setup_structured_logging(level="DEBUG")
        elif getattr(parsed_args, "verbose", 0) >= 1:
            from .utils.structured_logging import setup_structured_logging

            setup_structured_logging(level="INFO")

        if parsed_args.command is None:
            install_args = argparse.Namespace(
                host=None,
                all=False,
                auto=False,
                skill_name="super-dev",
                no_skill=False,
                skip_integrate=False,
                skip_slash=False,
                skip_doctor=False,
                force=False,
                yes=False,
            )
            return self._cmd_install(install_args)

        # 路由到对应命令
        command_name = str(parsed_args.command).replace("-", "_")
        command_handler = getattr(self, f"_cmd_{command_name}", None)
        if command_handler is None or not callable(command_handler):
            self.console.print(f"[red]未知命令: {parsed_args.command}[/red]")
            return 1

        try:
            handler = cast(Callable[[Any], int], command_handler)
            return int(handler(parsed_args))

        except Exception as e:
            # 统一错误处理 — 不向终端用户暴露 traceback
            cmd_name = str(getattr(parsed_args, "command", ""))

            # 调试模式下仍然打印 traceback
            if "--debug" in sys.argv or "-d" in sys.argv:
                self.console.print(traceback.format_exc())

            return handle_cli_error(e, command=cmd_name)

    # ==================== 命令处理器 ====================

    # 阶段编号映射表
    STAGE_NUMBER_MAP: dict[str, str] = {
        "1": "research",
        "2": "prd",
        "3": "architecture",
        "4": "uiux",
        "5": "spec",
        "6": "frontend",
        "7": "backend",
        "8": "quality",
        "9": "delivery",
    }

    STAGE_LABELS: dict[str, str] = {
        "research": "同类产品研究",
        "prd": "产品需求文档",
        "architecture": "架构设计",
        "uiux": "UI/UX 设计",
        "spec": "规范与任务分解",
        "frontend": "前端开发",
        "backend": "后端开发",
        "quality": "质量检查",
        "delivery": "交付打包",
    }

    # 每个环节对应的专家角色和职责
    STAGE_EXPERTS: dict[str, dict[str, str]] = {
        "research": {
            "role": "PM + ARCHITECT",
            "title": "产品经理 + 架构师",
            "duty": "需求解析、知识库增强、同类产品研究",
        },
        "prd": {
            "role": "PM",
            "title": "产品经理",
            "duty": "需求分析、PRD 编写、用户故事、验收标准",
        },
        "architecture": {
            "role": "ARCHITECT",
            "title": "架构师",
            "duty": "系统设计、技术选型、API 设计、数据库建模",
        },
        "uiux": {
            "role": "UI + UX",
            "title": "UI/UX 设计师",
            "duty": "视觉设计、设计系统、组件规范、交互设计",
        },
        "spec": {
            "role": "PM + CODE",
            "title": "产品经理 + 代码专家",
            "duty": "需求拆解、任务分解、优先级排序",
        },
        "frontend": {
            "role": "CODE + UI",
            "title": "代码专家 + UI 设计师",
            "duty": "前端实现、组件开发、页面搭建",
        },
        "backend": {
            "role": "CODE + DBA",
            "title": "代码专家 + 数据库专家",
            "duty": "后端实现、API 开发、数据库迁移",
        },
        "quality": {
            "role": "QA + SECURITY",
            "title": "QA 专家 + 安全专家",
            "duty": "质量门禁、红队审查、测试验证",
        },
        "delivery": {
            "role": "DEVOPS + QA",
            "title": "DevOps + QA 专家",
            "duty": "CI/CD 配置、发布演练、交付打包",
        },
    }

    _KNOWN_COMMANDS = {
        "init",
        "quality",
        "design",
        "spec",
        "task",
        "pipeline",
        "run",
        "config",
        "skill",
        "integrate",
        "onboard",
        "doctor",
        "setup",
        "install",
        "uninstall",
        "start",
        "detect",
        "update",
        "review",
        "release",
        "product-audit",
        "status",
        "next",
        "continue",
        "resume",
        "jump",
        "confirm",
        "clean",
        "generate",
        "enforce",
        "extension",
        "completion",
        "feedback",
        "migrate",
        "compliance",
    }

    _SUGGESTIBLE_COMMANDS = {
        "update",
        "uninstall",
        "help",
        "version",
    }

    def _is_direct_requirement_input(self, argv: list[str]) -> bool:
        """判断是否为直达需求输入（非子命令模式）"""
        if not argv:
            return False

        first = argv[0]
        if first.startswith("-"):
            return False

        if first in self._KNOWN_COMMANDS:
            return False

        # Single ASCII-only bare word without spaces/colons looks like a mistyped
        # command, not a requirement description.  Requirement mode requires either:
        # - multiple non-flag tokens, or
        # - the text contains `:` / `：` (host trigger prefix), or
        # - the first token contains non-ASCII characters (e.g. Chinese text).
        joined = " ".join(argv)
        if ":" in joined or "：" in joined:
            return True
        # If there are extra flag-style args (--offline etc.), still treat as requirement
        non_flag_tokens = [t for t in argv if not t.startswith("-")]
        if len(non_flag_tokens) >= 2:
            return True
        # Single bare ASCII-only word → likely a mistyped command, not a requirement
        if (
            len(non_flag_tokens) == 1
            and non_flag_tokens[0].isascii()
            and non_flag_tokens[0].isidentifier()
        ):
            return False
        # Fallback: treat as requirement (includes non-ASCII single tokens)
        return True

    def _is_unknown_command(self, argv: list[str]) -> bool:
        """判断是否为未知的单词命令（非需求直达，非已知命令）"""
        if not argv:
            return False
        first = argv[0]
        if first.startswith("-"):
            return False
        if first in self._KNOWN_COMMANDS:
            return False
        # Single bare ASCII-only word that looks like a command name
        non_flag_tokens = [t for t in argv if not t.startswith("-")]
        if (
            len(non_flag_tokens) == 1
            and non_flag_tokens[0].isascii()
            and non_flag_tokens[0].isidentifier()
        ):
            return True
        return False

    def _suggest_commands(self, unknown: str) -> list[str]:
        """为未知命令提供建议（简单前缀 + 编辑距离匹配）"""
        suggestions: list[str] = []
        for cmd in sorted(self._SUGGESTIBLE_COMMANDS):
            if cmd.startswith(unknown[:2]) or unknown.startswith(cmd[:2]):
                suggestions.append(cmd)
        # Always include the most common commands as fallback
        primary = ["update", "uninstall", "help", "version"]
        if not suggestions:
            suggestions = primary
        return suggestions[:6]

    def _parse_direct_requirement_args(self, argv: list[str]) -> tuple[str, dict[str, Any]]:
        """
        解析直达模式参数。

        支持写法：
        - super-dev
        - super-dev --offline
        """
        value_flags = {
            "-p": "platform",
            "--platform": "platform",
            "-f": "frontend",
            "--frontend": "frontend",
            "-b": "backend",
            "--backend": "backend",
            "-d": "domain",
            "--domain": "domain",
            "--name": "name",
            "--cicd": "cicd",
            "--quality-threshold": "quality_threshold",
        }
        bool_flags = {
            "--skip-redteam": "skip_redteam",
            "--skip-scaffold": "skip_scaffold",
            "--skip-quality-gate": "skip_quality_gate",
            "--skip-rehearsal-verify": "skip_rehearsal_verify",
            "--offline": "offline",
        }

        description_tokens: list[str] = []
        overrides: dict[str, Any] = {}
        index = 0
        while index < len(argv):
            token = argv[index]

            if token in bool_flags:
                overrides[bool_flags[token]] = True
                index += 1
                continue

            if token in value_flags:
                if index + 1 >= len(argv):
                    raise ValueError(f"参数 {token} 缺少取值")
                raw_value = argv[index + 1]
                key = value_flags[token]
                if key == "quality_threshold":
                    if not raw_value.isdigit():
                        raise ValueError("--quality-threshold 需要整数值")
                    overrides[key] = int(raw_value)
                else:
                    overrides[key] = raw_value
                index += 2
                continue

            description_tokens.append(token)
            index += 1

        description = " ".join(description_tokens).strip()
        if not description:
            raise ValueError("请提供需求描述")
        return description, overrides

    def _review_status_label(self, status: str, *, review_type: str = "docs") -> str:
        if status == "confirmed":
            return (
                "已通过"
                if review_type in {"preview", "ui", "architecture", "quality"}
                else "已确认"
            )
        if status == "revision_requested":
            if review_type == "preview":
                return "需继续修改"
            if review_type == "ui":
                return "需改版"
            if review_type == "architecture":
                return "需返工"
            if review_type == "quality":
                return "需整改"
            return "需修改"
        return "待确认"

    def _docs_confirmation_label(self, status: str) -> str:
        return self._review_status_label(status, review_type="docs")

    def _get_docs_confirmation_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_docs_confirmation(project_dir) or {}
        gate_state = docs_gate_status(project_dir)
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(docs_confirmation_file(project_dir)),
            "confirmed": bool(gate_state.get("confirmed", False)),
            "binding_matches_current": bool(gate_state.get("binding_matches_current", False)),
        }

    def _docs_confirmation_is_confirmed(self, project_dir: Path) -> bool:
        return bool(self._get_docs_confirmation_state(project_dir)["confirmed"])

    def _get_ui_revision_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_ui_revision(project_dir) or {}
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(ui_revision_file(project_dir)),
        }

    def _ui_revision_is_clear(self, project_dir: Path) -> bool:
        return bool(self._get_ui_revision_state(project_dir)["status"] != "revision_requested")

    def _get_preview_confirmation_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_preview_confirmation(project_dir) or {}
        gate_state = preview_gate_status(project_dir)
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(preview_confirmation_file(project_dir)),
            "confirmed": bool(gate_state.get("confirmed", False)),
            "binding_matches_current": bool(gate_state.get("binding_matches_current", False)),
        }

    def _preview_confirmation_is_confirmed(self, project_dir: Path) -> bool:
        return bool(self._get_preview_confirmation_state(project_dir)["confirmed"])

    def _get_architecture_revision_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_architecture_revision(project_dir) or {}
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(architecture_revision_file(project_dir)),
        }

    def _architecture_revision_is_clear(self, project_dir: Path) -> bool:
        return bool(
            self._get_architecture_revision_state(project_dir)["status"] != "revision_requested"
        )

    def _get_quality_revision_state(self, project_dir: Path) -> dict[str, Any]:
        payload = load_quality_revision(project_dir) or {}
        return {
            "status": str(payload.get("status", "")).strip() or "pending_review",
            "comment": str(payload.get("comment", "")).strip(),
            "actor": str(payload.get("actor", "")).strip(),
            "run_id": str(payload.get("run_id", "")).strip(),
            "updated_at": str(payload.get("updated_at", "")).strip(),
            "exists": bool(payload),
            "file_path": str(quality_revision_file(project_dir)),
        }

    def _quality_revision_is_clear(self, project_dir: Path) -> bool:
        return bool(self._get_quality_revision_state(project_dir)["status"] != "revision_requested")

    def _has_core_docs(self, project_dir: Path) -> bool:
        output_dir = project_dir / "output"
        if not output_dir.exists():
            return False
        return (
            any(output_dir.glob("*-prd.md"))
            and any(output_dir.glob("*-architecture.md"))
            and any(output_dir.glob("*-uiux.md"))
        )

    def _ensure_docs_confirmation_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        if not self._has_core_docs(project_dir):
            return True
        if self._docs_confirmation_is_confirmed(project_dir):
            return True

        current = self._get_docs_confirmation_state(project_dir)
        self.console.print(f"[red]{action_label}前，必须先完成三文档确认[/red]")
        self.console.print(
            f"[dim]当前状态: {self._docs_confirmation_label(current['status'])}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print("[dim]先查看 output/*-prd.md、*-architecture.md、*-uiux.md[/dim]")
        self.console.print("[dim]然后回到宿主里明确回复：“文档确认，可以继续”[/dim]")
        return False

    def _ensure_ui_revision_clear_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        current = self._get_ui_revision_state(project_dir)
        if current["status"] != "revision_requested":
            return True

        self.console.print(f"[red]{action_label}前，必须先完成 UI 改版返工[/red]")
        self.console.print(
            f"[dim]当前状态: {self._review_status_label(current['status'], review_type='ui')}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print(
            "[dim]先更新 output/*-uiux.md，再重做前端，并重新执行 frontend runtime 与 UI review[/dim]"
        )
        self.console.print("[dim]完成后回到宿主里明确回复：“UI 改版已完成，继续当前流程”[/dim]")
        return False

    def _ensure_preview_confirmation_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        output_dir = project_dir / "output"
        frontend_ready = any(output_dir.glob("*-frontend-runtime.json"))
        if not frontend_ready:
            return True
        if self._preview_confirmation_is_confirmed(project_dir):
            return True

        current = self._get_preview_confirmation_state(project_dir)
        self.console.print(f"[red]{action_label}前，必须先完成前端预览确认[/red]")
        self.console.print(
            f"[dim]当前状态: {self._review_status_label(current['status'], review_type='preview')}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print(
            "[dim]先评审当前前端预览；若需要继续修改，完成前端返工并重跑 frontend runtime 后再确认[/dim]"
        )
        self.console.print("[dim]完成后回到宿主里明确回复：“前端预览确认，可以继续”[/dim]")
        return False

    def _ensure_architecture_revision_clear_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        current = self._get_architecture_revision_state(project_dir)
        if current["status"] != "revision_requested":
            return True

        self.console.print(f"[red]{action_label}前，必须先完成架构返工[/red]")
        self.console.print(
            f"[dim]当前状态: {self._review_status_label(current['status'], review_type='architecture')}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print(
            "[dim]先更新 output/*-architecture.md，再同步调整实现方案与相关任务拆解[/dim]"
        )
        self.console.print("[dim]完成后回到宿主里明确回复：“架构调整已完成，继续当前流程”[/dim]")
        return False

    def _ensure_quality_revision_clear_for_execution(
        self, project_dir: Path, *, action_label: str
    ) -> bool:
        current = self._get_quality_revision_state(project_dir)
        if current["status"] != "revision_requested":
            return True

        self.console.print(f"[red]{action_label}前，必须先完成质量返工[/red]")
        self.console.print(
            f"[dim]当前状态: {self._review_status_label(current['status'], review_type='quality')}[/dim]"
        )
        if current["comment"]:
            self.console.print(f"[dim]备注: {current['comment']}[/dim]")
        self.console.print("[dim]先修复质量/安全问题，重新执行 quality gate，并刷新交付证据[/dim]")
        self.console.print("[dim]完成后回到宿主里明确回复：“质量整改已完成，继续当前流程”[/dim]")
        return False

    def _ensure_execution_gates(self, project_dir: Path, *, action_label: str) -> bool:
        return (
            self._ensure_docs_confirmation_for_execution(project_dir, action_label=action_label)
            and self._ensure_preview_confirmation_for_execution(
                project_dir, action_label=action_label
            )
            and self._ensure_ui_revision_clear_for_execution(project_dir, action_label=action_label)
            and self._ensure_architecture_revision_clear_for_execution(
                project_dir, action_label=action_label
            )
            and self._ensure_quality_revision_clear_for_execution(
                project_dir, action_label=action_label
            )
        )

    def _cmd_task(self, args) -> int:
        """Spec 任务执行与状态查看"""
        from .creators import SpecTaskExecutor
        from .specs import ChangeManager

        project_dir = Path.cwd()
        manager = ChangeManager(project_dir)

        if args.action == "list":
            changes = manager.list_changes()
            if not changes:
                self.console.print("[dim]没有找到变更[/dim]")
                return 0
            self.console.print("[cyan]变更任务概览:[/cyan]")
            for change in changes:
                completed = sum(1 for task in change.tasks if task.status.value == "completed")
                total = len(change.tasks)
                self.console.print(
                    f"  - {change.id}: {change.status.value} | 任务 {completed}/{total}"
                )
            return 0

        if not args.change_id:
            self.console.print("[red]请提供 change_id[/red]")
            return 1

        loaded_change = manager.load_change(args.change_id)
        if not loaded_change:
            self.console.print(f"[red]变更不存在: {args.change_id}[/red]")
            return 1

        if args.action == "status":
            completed = sum(1 for task in loaded_change.tasks if task.status.value == "completed")
            in_progress = sum(
                1 for task in loaded_change.tasks if task.status.value == "in_progress"
            )
            pending = sum(1 for task in loaded_change.tasks if task.status.value == "pending")
            self.console.print(f"[cyan]任务状态: {loaded_change.id}[/cyan]")
            self.console.print(f"  标题: {loaded_change.title}")
            self.console.print(f"  状态: {loaded_change.status.value}")
            self.console.print(f"  已完成: {completed}")
            self.console.print(f"  进行中: {in_progress}")
            self.console.print(f"  待处理: {pending}")
            for task in loaded_change.tasks:
                marker = (
                    "[x]"
                    if task.status.value == "completed"
                    else "[~]" if task.status.value == "in_progress" else "[ ]"
                )
                self.console.print(f"  {marker} {task.id} {task.title}")
            return 0

        config_manager = get_config_manager()
        config_exists = config_manager.exists()
        config = config_manager.config

        tech_stack = {
            "platform": args.platform or (config.platform if config_exists else "web"),
            "frontend": args.frontend
            or (self._normalize_pipeline_frontend(config.frontend) if config_exists else "react"),
            "backend": args.backend or (config.backend if config_exists else "node"),
            "domain": (
                args.domain if args.domain is not None else (config.domain if config_exists else "")
            ),
        }

        project_name = args.project_name or (
            config.name if config_exists and config.name else args.change_id
        )

        if not self._ensure_execution_gates(project_dir, action_label="执行 Spec 任务"):
            return 1

        executor = SpecTaskExecutor(project_dir=project_dir, project_name=project_name)
        summary = executor.execute(
            change_id=args.change_id,
            tech_stack=tech_stack,
            max_retries=max(0, int(args.max_retries)),
        )

        self.console.print("[green]✓ Spec 任务执行完成[/green]")
        self.console.print(f"  变更: {summary.change_id}")
        self.console.print(f"  完成: {summary.completed_tasks}/{summary.total_tasks}")
        self.console.print(f"  报告: {summary.report_file}")
        if summary.repaired_actions:
            self.console.print(f"  自动修复: {len(summary.repaired_actions)} 项")
        if summary.failed_tasks:
            self.console.print(f"  [yellow]未完成任务: {', '.join(summary.failed_tasks)}[/yellow]")
            return 1
        return 0

    def _normalize_pipeline_frontend(self, frontend: str) -> str:
        """将 init 的前端框架映射到 pipeline 可接受值"""
        mapping = {
            "next": "react",
            "remix": "react",
            "react-vite": "react",
            "gatsby": "react",
            "nuxt": "vue",
            "vue-vite": "vue",
            "sveltekit": "svelte",
            "astro": "react",
            "solid": "react",
            "qwik": "react",
        }
        if frontend in set(SUPPORTED_PIPELINE_FRONTENDS):
            return frontend
        return mapping.get(frontend, "react")

    def _normalize_cicd_platform(self, value: str) -> CICDPlatform:
        valid = set(SUPPORTED_CICD)
        normalized = (value or "github").lower()
        if normalized not in valid:
            raise ValueError(f"不支持的 CI/CD 平台: {value}")
        return cast(CICDPlatform, normalized)

    def _validate_host_support_matrix(self) -> list[str]:
        from .integrations import IntegrationManager
        from .skills import SkillManager

        issues: list[str] = []
        integration_gaps = IntegrationManager.coverage_gaps()
        if integration_gaps.get("missing_in_targets"):
            issues.append(
                "IntegrationManager.TARGETS 缺失宿主: "
                + ", ".join(integration_gaps["missing_in_targets"])
            )
        if integration_gaps.get("extra_in_targets"):
            issues.append(
                "IntegrationManager.TARGETS 存在未声明宿主: "
                + ", ".join(integration_gaps["extra_in_targets"])
            )
        if integration_gaps.get("missing_in_slash"):
            issues.append(
                "IntegrationManager.SLASH_COMMAND_FILES 缺失宿主: "
                + ", ".join(integration_gaps["missing_in_slash"])
            )
        if integration_gaps.get("extra_in_slash"):
            issues.append(
                "IntegrationManager.SLASH_COMMAND_FILES 存在未声明宿主: "
                + ", ".join(integration_gaps["extra_in_slash"])
            )
        if integration_gaps.get("missing_in_docs_map"):
            issues.append(
                "IntegrationManager.OFFICIAL_DOCS 缺失宿主: "
                + ", ".join(integration_gaps["missing_in_docs_map"])
            )
        if integration_gaps.get("extra_in_docs_map"):
            issues.append(
                "IntegrationManager.OFFICIAL_DOCS 存在未声明宿主: "
                + ", ".join(integration_gaps["extra_in_docs_map"])
            )

        skill_gaps = SkillManager.coverage_gaps()
        if skill_gaps.get("missing_in_skill_targets"):
            issues.append(
                "SkillManager.TARGET_PATHS 缺失宿主: "
                + ", ".join(skill_gaps["missing_in_skill_targets"])
            )
        if skill_gaps.get("extra_in_skill_targets"):
            issues.append(
                "SkillManager.TARGET_PATHS 存在未声明宿主: "
                + ", ".join(skill_gaps["extra_in_skill_targets"])
            )
        return issues

    def _ensure_host_support_matrix(self) -> bool:
        issues = self._validate_host_support_matrix()
        if not issues:
            return True
        self.console.print("[red]宿主支持矩阵配置不一致，请先修复后再执行[/red]")
        for item in issues:
            self.console.print(f"  - {item}")
        return False

    def _sanitize_project_name(self, name: str) -> str:
        """清理项目名，避免路径非法字符"""
        import re

        cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", name.strip())
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
        return cleaned or "my-project"

    def _pipeline_run_state_path(self, project_dir: Path) -> Path:
        return project_dir / ".super-dev" / "runs" / "last-pipeline.json"

    def _normalize_run_status(self, status: Any) -> str:
        normalized = str(status or "").strip().lower()
        if normalized in {"success", "completed"}:
            return "completed"
        if normalized in {"failed"}:
            return "failed"
        if normalized in {"cancelled"}:
            return "cancelled"
        if normalized in {
            "running",
            "cancelling",
            "waiting_confirmation",
            "waiting_preview_confirmation",
            "waiting_ui_revision",
            "waiting_architecture_revision",
            "waiting_quality_revision",
        }:
            return "running"
        if normalized in {"queued"}:
            return "queued"
        return "unknown"

    def _write_pipeline_run_state(self, project_dir: Path, payload: dict[str, Any]) -> None:
        state_file = self._pipeline_run_state_path(project_dir)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        payload_with_normalized = dict(payload)
        payload_with_normalized["status_normalized"] = self._normalize_run_status(
            payload_with_normalized.get("status")
        )
        lock_file = state_file.parent / ".runs.lock"
        lock_handle = lock_file.open("a+", encoding="utf-8")
        try:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=state_file.parent,
                prefix=".last-pipeline.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(json.dumps(payload_with_normalized, ensure_ascii=False, indent=2))
                temp_path = Path(temp_file.name)
            os.replace(temp_path, state_file)
        finally:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()
        try:
            if self._project_has_super_dev_context(project_dir):
                self._write_session_brief(
                    project_dir=project_dir, payload=self._build_next_step_payload(project_dir)
                )
        except Exception:
            pass

    def _read_pipeline_run_state(self, project_dir: Path) -> dict[str, Any] | None:
        state_file = self._pipeline_run_state_path(project_dir)
        if not state_file.exists():
            return None
        try:
            raw = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(raw, dict):
            return None
        return raw

    def _resume_audit_paths(self, output_dir: Path, project_name: str) -> dict[str, Path]:
        return {
            "json": output_dir / f"{project_name}-resume-audit.json",
            "markdown": output_dir / f"{project_name}-resume-audit.md",
        }

    def _render_resume_audit_markdown(self, payload: dict[str, Any]) -> str:
        detected_stage = payload.get("detected_failed_stage", "")
        initial_stage = payload.get("initial_resume_stage", "")
        final_stage = payload.get("final_resume_stage", "")
        planned_skips = payload.get("planned_skipped_stages", [])
        if isinstance(planned_skips, list):
            skip_text = ", ".join(str(item) for item in planned_skips) if planned_skips else "-"
        else:
            skip_text = "-"

        lines = [
            "# Resume Audit",
            "",
            f"- Project: `{payload.get('project_name', '')}`",
            f"- Status: `{payload.get('status', '')}`",
            f"- Run state status: `{payload.get('run_state_status', '')}`",
            f"- Detected failed stage: `{detected_stage}`",
            f"- Initial resume stage: `{initial_stage}`",
            f"- Final resume stage: `{final_stage}`",
            f"- Planned skipped stages: `{skip_text}`",
            f"- Started at (UTC): `{payload.get('started_at', '')}`",
            f"- Finished at (UTC): `{payload.get('finished_at', '')}`",
        ]
        failure_reason = str(payload.get("failure_reason", "")).strip()
        if failure_reason:
            lines.append(f"- Failure reason: `{failure_reason}`")

        reasons = payload.get("fallback_reasons", [])
        lines.extend(["", "## Fallback Reasons", ""])
        if isinstance(reasons, list) and reasons:
            lines.extend([f"- {str(item)}" for item in reasons])
        else:
            lines.append("- None")

        return "\n".join(lines) + "\n"

    def _write_resume_audit(
        self,
        *,
        output_dir: Path,
        project_name: str,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        files = self._resume_audit_paths(output_dir=output_dir, project_name=project_name)
        files["json"].parent.mkdir(parents=True, exist_ok=True)
        files["json"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        files["markdown"].write_text(self._render_resume_audit_markdown(payload), encoding="utf-8")
        return files

    def _coerce_stage_number(self, raw_stage: Any) -> int | None:
        text = str(raw_stage).strip()
        if not text.isdigit():
            return None
        return int(text)

    def _load_pipeline_metrics_payload(
        self, output_dir: Path, project_name: str
    ) -> dict[str, Any] | None:
        metrics_file = output_dir / f"{project_name}-pipeline-metrics.json"
        if not metrics_file.exists():
            return None
        try:
            payload = json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _extract_metrics_stage_details(
        self,
        metrics_payload: dict[str, Any] | None,
        stage: str,
    ) -> dict[str, Any]:
        if not isinstance(metrics_payload, dict):
            return {}
        stages = metrics_payload.get("stages", [])
        if not isinstance(stages, list):
            return {}
        for item in stages:
            if not isinstance(item, dict):
                continue
            if str(item.get("stage", "")).strip() != stage:
                continue
            details = item.get("details", {})
            if isinstance(details, dict):
                return details
            return {}
        return {}

    def _resolve_resume_start_stage(
        self, failed_stage: int | None, skip_redteam: bool
    ) -> int | None:
        """
        将失败阶段映射为安全恢复起点。

        - 0-4: 仍执行全量重跑（需要重建上下文，避免不一致）
        - 5: 直接从红队继续
        - 6: 默认回退到 5（需要 redteam_report 输入）；若本次跳过红队则可从 6 开始
        - 7-8: 直接从失败阶段恢复
        - 9-12: 统一从 9 恢复，保证后续汇总变量完整
        """
        if failed_stage is None:
            return None
        if failed_stage < 5:
            return None
        if failed_stage >= 9:
            return 9
        if failed_stage == 8:
            return 8
        if failed_stage == 7:
            return 7
        if failed_stage == 6:
            return 6 if skip_redteam else 5
        return 5

    def _stage_one_artifact_paths(self, output_dir: Path, project_name: str) -> dict[str, Path]:
        return {
            "research": output_dir / f"{project_name}-research.md",
            "prd": output_dir / f"{project_name}-prd.md",
            "architecture": output_dir / f"{project_name}-architecture.md",
            "uiux": output_dir / f"{project_name}-uiux.md",
            "execution_plan": output_dir / f"{project_name}-execution-plan.md",
            "frontend_blueprint": output_dir / f"{project_name}-frontend-blueprint.md",
        }

    def _adjust_resume_stage_for_artifacts(
        self,
        *,
        project_dir: Path,
        output_dir: Path,
        project_name: str,
        resume_from_stage: int | None,
    ) -> tuple[int | None, list[str]]:
        if resume_from_stage is None:
            return None, []

        adjusted = resume_from_stage
        reasons: list[str] = []

        # 中后段恢复依赖前置文档产物，缺失时回退到第 1 阶段重建上下文。
        if adjusted in {5, 6, 7, 8}:
            required_docs = self._stage_one_artifact_paths(
                output_dir=output_dir, project_name=project_name
            )
            missing_docs = [name for name, path in required_docs.items() if not path.exists()]
            if missing_docs:
                adjusted = 1
                reasons.append(f"缺少前置文档产物: {', '.join(missing_docs)}")

        if adjusted in {4, 5, 6, 7, 8} and not self._detect_latest_change_id(project_dir):
            adjusted = 2
            reasons.append("未检测到可用 Spec 变更目录")

        if adjusted in {4, 5, 6, 7, 8}:
            frontend_runtime_report = output_dir / f"{project_name}-frontend-runtime.json"
            if not frontend_runtime_report.exists():
                adjusted = 3
                reasons.append("缺少前端运行验证报告")

        return adjusted, reasons

    def _detect_latest_change_id(self, project_dir: Path) -> str:
        changes_dir = project_dir / ".super-dev" / "changes"
        if not changes_dir.exists():
            return ""
        change_dirs = [item for item in changes_dir.iterdir() if item.is_dir()]
        if not change_dirs:
            return ""
        latest = max(change_dirs, key=lambda item: item.stat().st_mtime)
        return latest.name

    def _extract_resume_context(
        self,
        run_state: dict[str, Any] | None,
        metrics_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if isinstance(run_state, dict):
            stored_context = run_state.get("context")
            if isinstance(stored_context, dict):
                context.update(stored_context)

        stage1_details = self._extract_metrics_stage_details(metrics_payload, "1")
        scenario = stage1_details.get("scenario")
        if "scenario" not in context and isinstance(scenario, str) and scenario in {"0-1", "1-N+1"}:
            context["scenario"] = scenario

        stage3_details = self._extract_metrics_stage_details(metrics_payload, "3")
        change_id = stage3_details.get("change_id")
        if "change_id" not in context and isinstance(change_id, str) and change_id.strip():
            context["change_id"] = change_id.strip()

        return context

    def _normalize_requirements_payload(self, raw: Any) -> list[dict[str, Any]]:
        import re

        if not isinstance(raw, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                spec_name = str(item.get("spec_name", "core")).strip() or "core"
                req_name = (
                    str(item.get("req_name") or item.get("name") or "requirement").strip()
                    or "requirement"
                )
                description = str(item.get("description", "")).strip() or req_name
                scenarios = item.get("scenarios", [])
                if not isinstance(scenarios, list):
                    scenarios = []
                normalized.append(
                    {
                        "spec_name": spec_name,
                        "req_name": req_name,
                        "description": description,
                        "scenarios": scenarios,
                    }
                )
                continue

            if isinstance(item, str):
                text = item.strip()
                if not text:
                    continue
                safe_name = re.sub(r"[^a-z0-9_]+", "-", text.lower()).strip("-") or "requirement"
                normalized.append(
                    {
                        "spec_name": "core",
                        "req_name": safe_name,
                        "description": text,
                        "scenarios": [],
                    }
                )

        return normalized

    def _extract_stage_artifacts(self, details: dict[str, Any]) -> list[str]:
        artifacts: list[str] = []
        seen: set[str] = set()

        def _append_if_path(value: str) -> None:
            candidate = value.strip()
            if not candidate:
                return
            path = Path(candidate)
            if not path.is_absolute():
                path = (Path.cwd() / path).resolve()
            if not path.exists():
                return
            try:
                rel = str(path.relative_to(Path.cwd()))
            except ValueError:
                rel = str(path)
            if rel in seen:
                return
            seen.add(rel)
            artifacts.append(rel)

        def _walk(value: Any) -> None:
            if isinstance(value, str):
                _append_if_path(value)
                return
            if isinstance(value, Path):
                _append_if_path(str(value))
                return
            if isinstance(value, dict):
                for item in value.values():
                    _walk(item)
                return
            if isinstance(value, list | tuple | set):
                for item in value:
                    _walk(item)

        _walk(details)
        return artifacts

    def _extract_stage_notes(self, details: dict[str, Any]) -> list[str]:
        notes: list[str] = []
        if bool(details.get("skipped", False)):
            reason = str(details.get("reason", "manual")).strip() or "manual"
            notes.append(f"skipped:{reason}")
        if "score" in details:
            notes.append(f"score={details.get('score')}")
        if "scenario" in details:
            notes.append(f"scenario={details.get('scenario')}")
        if "critical_failures" in details and isinstance(details["critical_failures"], list):
            notes.append(f"critical_failures={len(details['critical_failures'])}")
        return notes

    def _detect_failed_stage_from_metrics_payload(
        self, metrics_payload: dict[str, Any] | None
    ) -> int | None:
        if not isinstance(metrics_payload, dict):
            return None
        if bool(metrics_payload.get("success", False)):
            return None
        stages = metrics_payload.get("stages", [])
        if not isinstance(stages, list):
            return None
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            if bool(stage.get("success", False)):
                continue
            parsed = self._coerce_stage_number(stage.get("stage"))
            if parsed is not None:
                return parsed
        return None

    def _detect_failed_stage(self, output_dir: Path, project_name: str) -> int | None:
        payload = self._load_pipeline_metrics_payload(
            output_dir=output_dir, project_name=project_name
        )
        return self._detect_failed_stage_from_metrics_payload(payload)

    def _run_direct_requirement(
        self, description: str, direct_overrides: dict[str, Any] | None = None
    ) -> int:
        """将 `super-dev <需求描述>` 直达路由到完整流水线"""
        if not description:
            self.console.print("[red]请提供需求描述[/red]")
            return 1

        direct_overrides = direct_overrides or {}
        config_manager = get_config_manager()
        config_exists = config_manager.exists()
        config = config_manager.config

        platform = str(
            direct_overrides.get("platform") or (config.platform if config_exists else "web")
        )
        frontend = str(
            direct_overrides.get("frontend")
            or (self._normalize_pipeline_frontend(config.frontend) if config_exists else "react")
        )
        backend = str(
            direct_overrides.get("backend") or (config.backend if config_exists else "node")
        )
        domain = str(direct_overrides.get("domain") or (config.domain if config_exists else ""))
        cicd = str(direct_overrides.get("cicd") or "all")

        if platform not in SUPPORTED_PLATFORMS:
            self.console.print(f"[red]不支持的平台: {platform}[/red]")
            return 2
        if frontend not in SUPPORTED_PIPELINE_FRONTENDS:
            self.console.print(f"[red]不支持的前端框架: {frontend}[/red]")
            return 2
        if backend not in SUPPORTED_PIPELINE_BACKENDS:
            self.console.print(f"[red]不支持的后端框架: {backend}[/red]")
            return 2
        if domain not in SUPPORTED_DOMAINS:
            self.console.print(f"[red]不支持的业务领域: {domain}[/red]")
            return 2
        if cicd not in SUPPORTED_CICD:
            self.console.print(f"[red]不支持的 CI/CD 平台: {cicd}[/red]")
            return 2

        args = argparse.Namespace(
            description=description,
            platform=platform,
            frontend=frontend,
            backend=backend,
            domain=domain,
            name=direct_overrides.get("name"),
            cicd=cicd,
            mode=direct_overrides.get("mode", "feature"),
            skip_redteam=bool(direct_overrides.get("skip_redteam", False)),
            skip_scaffold=bool(direct_overrides.get("skip_scaffold", False)),
            skip_quality_gate=bool(direct_overrides.get("skip_quality_gate", False)),
            skip_rehearsal_verify=bool(direct_overrides.get("skip_rehearsal_verify", False)),
            offline=bool(direct_overrides.get("offline", False)),
            quality_threshold=direct_overrides.get("quality_threshold"),
            changed_surfaces=None,
            governance_depth=None,
            resume=False,
        )

        self.console.print("[cyan]需求直达模式：自动执行治理流水线[/cyan]")
        self._print_governance_boundary_notice(
            "该入口只负责生成治理产物与流程约束，实际编码应在宿主会话内完成。"
        )
        return self._cmd_pipeline(args)

    def _save_tech_stack_to_config(
        self, project_dir: Path, tech_stack: dict, description: str
    ) -> None:
        """保存技术栈到项目配置文件"""
        import yaml  # type: ignore[import-untyped]

        config_file = project_dir / "super-dev.yaml"

        # 读取现有配置（如果有）
        config: dict[str, Any] = {}
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        # 更新配置
        config["platform"] = tech_stack.get("platform", "web")
        config["frontend"] = tech_stack.get("frontend", "react")
        config["backend"] = tech_stack.get("backend", "node")
        config["domain"] = tech_stack.get("domain", "")
        config["description"] = description

        # 保存配置
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def _export_deploy_remediation_templates(
        self,
        project_dir: Path,
        cicd_platform: str,
        only_missing: bool = True,
    ) -> dict:
        """导出部署修复模板：环境变量示例 + secrets 检查清单。"""
        env_hints_map = {
            "github": [
                {"name": "DOCKER_USERNAME", "description": "Docker 镜像仓库用户名"},
                {"name": "DOCKER_PASSWORD", "description": "Docker 镜像仓库密码/Token"},
                {"name": "KUBE_CONFIG_DEV", "description": "开发环境 Kubernetes kubeconfig"},
                {"name": "KUBE_CONFIG_PROD", "description": "生产环境 Kubernetes kubeconfig"},
            ],
            "gitlab": [
                {"name": "CI_REGISTRY_USER", "description": "GitLab Registry 用户名"},
                {"name": "CI_REGISTRY_PASSWORD", "description": "GitLab Registry 密码/Token"},
                {"name": "KUBE_CONTEXT_DEV", "description": "开发环境 K8s 上下文"},
                {"name": "KUBE_CONTEXT_PROD", "description": "生产环境 K8s 上下文"},
            ],
            "azure": [
                {"name": "AZURE_ACR_SERVICE_CONNECTION", "description": "Azure ACR 服务连接标识"},
                {"name": "AZURE_DEV_K8S_CONNECTION", "description": "开发环境 AKS 服务连接标识"},
                {"name": "AZURE_PROD_K8S_CONNECTION", "description": "生产环境 AKS 服务连接标识"},
            ],
            "bitbucket": [
                {"name": "REGISTRY_URL", "description": "镜像仓库地址"},
                {"name": "KUBE_CONFIG_DEV", "description": "开发环境 Kubernetes kubeconfig"},
                {"name": "KUBE_CONFIG_PROD", "description": "生产环境 Kubernetes kubeconfig"},
            ],
        }
        manual_hints_map = {
            "jenkins": [
                "Jenkins Credentials: docker-credentials",
                "Jenkins Credentials: kubeconfig-dev",
                "Jenkins Credentials: kubeconfig-prod",
            ]
        }
        platform_guidance_map = {
            "github": [
                "在 GitHub Settings > Secrets and variables > Actions 配置变量。",
                "按 dev/prod 环境拆分敏感变量。",
            ],
            "gitlab": [
                "在 GitLab Settings > CI/CD > Variables 中配置变量并启用 Masked。",
            ],
            "jenkins": [
                "在 Jenkins Credentials 中创建与流水线一致的凭据 ID。",
            ],
            "azure": [
                "在 Azure DevOps 配置 Service Connection 和 Variable Group。",
            ],
            "bitbucket": [
                "在 Bitbucket Repository variables 中配置密钥。",
            ],
        }

        def _resolve_env_hints(platform: str) -> list[dict]:
            if platform == "all":
                merged = []
                seen = set()
                for item_platform in ("github", "gitlab", "azure", "bitbucket"):
                    for item in env_hints_map.get(item_platform, []):
                        if item["name"] in seen:
                            continue
                        seen.add(item["name"])
                        merged.append(item)
                return merged
            return list(env_hints_map.get(platform, []))

        def _resolve_manual_hints(platform: str) -> list[str]:
            if platform == "all":
                return list(manual_hints_map.get("jenkins", []))
            return list(manual_hints_map.get(platform, []))

        def _resolve_guidance(platform: str) -> list[str]:
            if platform == "all":
                merged = []
                seen = set()
                for item_platform in ("github", "gitlab", "jenkins", "azure", "bitbucket"):
                    for item in platform_guidance_map.get(item_platform, []):
                        if item in seen:
                            continue
                        seen.add(item)
                        merged.append(item)
                return merged
            return list(platform_guidance_map.get(platform, []))

        def _collect_items(platform: str) -> list[dict]:
            env_hints = _resolve_env_hints(platform)
            items = []
            for item in env_hints:
                name = item["name"]
                present = bool(os.getenv(name, "").strip())
                if only_missing and present:
                    continue
                items.append(
                    {
                        "name": name,
                        "description": item["description"],
                        "present": present,
                        "template": f'{name}="<value>"',
                    }
                )
            return items

        def _write_env_example(file_path: Path, platform: str, items: list[dict]) -> None:
            lines = [
                "# Super Dev Deployment Environment Template",
                f"# Platform: {platform}",
                f"# only_missing: {str(only_missing).lower()}",
                "",
            ]
            if not items:
                lines.append("# No variables to export for current filter.")
            else:
                for item in items:
                    lines.append(f"# {item['description']}")
                    lines.append(item["template"])
                    lines.append("")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        def _write_checklist(
            file_path: Path,
            platform: str,
            items: list[dict],
            manual_hints: list[str],
            platform_guidance: list[str],
        ) -> None:
            lines = [
                "# Deploy Remediation Checklist",
                "",
                f"- Platform: `{platform}`",
                f"- only_missing: `{str(only_missing).lower()}`",
                "",
                "## Environment Variables",
                "",
                "| Name | Status | Description | Template |",
                "|:---|:---:|:---|:---|",
            ]
            if items:
                for item in items:
                    status = "present" if item["present"] else "missing"
                    lines.append(
                        f"| `{item['name']}` | `{status}` | {item['description']} | `{item['template']}` |"
                    )
            else:
                lines.append("| - | - | No variables in current filter | - |")

            lines.extend(["", "## Platform Guidance", ""])
            if platform_guidance:
                lines.extend([f"- {line}" for line in platform_guidance])
            else:
                lines.append("- No guidance available.")

            lines.extend(["", "## Manual Requirements", ""])
            if manual_hints:
                lines.extend([f"- {line}" for line in manual_hints])
            else:
                lines.append("- No manual requirements.")

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

        output_dir = project_dir / "output" / "deploy"
        output_dir.mkdir(parents=True, exist_ok=True)

        aggregate_items = _collect_items(cicd_platform)
        env_path = project_dir / ".env.deploy.example"
        checklist_path = output_dir / f"{cicd_platform}-secrets-checklist.md"
        _write_env_example(env_path, cicd_platform, aggregate_items)
        _write_checklist(
            checklist_path,
            cicd_platform,
            aggregate_items,
            _resolve_manual_hints(cicd_platform),
            _resolve_guidance(cicd_platform),
        )

        per_platform_files = []
        if cicd_platform == "all":
            platform_dir = output_dir / "platforms"
            for platform in ("github", "gitlab", "jenkins", "azure", "bitbucket"):
                platform_items = _collect_items(platform)
                platform_env = platform_dir / f".env.deploy.{platform}.example"
                platform_checklist = platform_dir / f"{platform}-secrets-checklist.md"
                _write_env_example(platform_env, platform, platform_items)
                _write_checklist(
                    platform_checklist,
                    platform,
                    platform_items,
                    _resolve_manual_hints(platform),
                    _resolve_guidance(platform),
                )
                per_platform_files.append(
                    {
                        "platform": platform,
                        "env_file": str(platform_env),
                        "checklist_file": str(platform_checklist),
                        "items_count": len(platform_items),
                    }
                )

        return {
            "env_file": str(env_path),
            "checklist_file": str(checklist_path),
            "items_count": len(aggregate_items),
            "per_platform_files": per_platform_files,
        }

    def _print_banner(self) -> None:
        """打印欢迎横幅"""
        if self.console:
            from rich.panel import Panel
            from rich.text import Text

            banner = Text()
            banner.append("Super Dev ", style="bold cyan")
            banner.append(f"v{__version__}\n", style="dim")
            banner.append(__description__, style="white")
            banner.append("\n宿主负责编码，Super Dev 负责治理与交付标准", style="dim")

            self.console.print(Panel.fit(banner, title="Super Dev", border_style="cyan"))

    def _print_governance_boundary_notice(self, message: str) -> None:
        if not self.console:
            return
        self.console.print(f"[dim]治理边界: {message} 宿主负责模型调用、工具使用与代码产出。[/dim]")


def main() -> int:
    """主入口"""
    from .utils.structured_logging import setup_structured_logging

    setup_structured_logging()
    cli = SuperDevCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
