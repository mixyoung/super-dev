"""Project configuration and integration commands for the CLI."""

import importlib.util
import json
import subprocess as _subprocess
import sys
from pathlib import Path
from typing import Any, Literal

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
from .config import ProjectConfig, get_config_manager
from .host_runtime_probe import build_host_runtime_probe

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


class CliIntegrationRuntimeMixin:
    def _cmd_config(self, args) -> int:
        """配置管理"""
        config_manager = get_config_manager()

        if not config_manager.exists():
            self.console.print("[red]未找到项目配置[/red]")
            return 1

        if args.action == "list":
            # 列出所有配置
            config = config_manager.config
            self.console.print("[cyan]项目配置:[/cyan]")
            for key, value in config.__dict__.items():
                if not key.startswith("_"):
                    self.console.print(f"  {key}: {value}")

        elif args.action == "get":
            if not args.key:
                self.console.print("[red]请指定配置键[/red]")
                return 1
            value = config_manager.get(args.key)
            self.console.print(f"{args.key}: {value}")

        elif args.action == "set":
            if not args.key or not args.value:
                self.console.print("[red]请指定配置键和值[/red]")
                return 1
            valid_keys = {
                key
                for key in ProjectConfig.__dataclass_fields__.keys()  # type: ignore[attr-defined]
                if not key.startswith("_")
            }
            if args.key not in valid_keys:
                self.console.print(f"[red]未知配置键: {args.key}[/red]")
                self.console.print(f"[dim]可用配置键: {', '.join(sorted(valid_keys))}[/dim]")
                return 1
            try:
                updated = config_manager.update(**{args.key: args.value})
            except ValueError as e:
                self.console.print(f"[red]{e}[/red]")
                return 1
            actual = getattr(updated, args.key, args.value)
            self.console.print(f"[green]✓[/green] {args.key} = {actual}")

        elif args.action == "validate":
            return self._cmd_config_validate()

        return 0

    def _cmd_config_validate(self) -> int:
        """验证 super-dev.yaml 配置文件是否符合 schema 规范"""
        import yaml

        from .config.schema_validator import validate_config

        config_path = Path.cwd() / "super-dev.yaml"

        if not config_path.exists():
            self.console.print("[red]未找到 super-dev.yaml 配置文件[/red]")
            return 1

        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            self.console.print(f"[red]配置文件解析失败: {exc}[/red]")
            return 1

        errors = validate_config(raw)

        if errors:
            self.console.print("[red]配置验证失败:[/red]")
            for err in errors:
                self.console.print(f"  [red]✗[/red] {err}")
            return 1

        self.console.print("[green]✓ 配置验证通过，super-dev.yaml 格式正确[/green]")
        return 0

    def _cmd_skill(self, args) -> int:
        """Skill 管理"""
        from .skills import SkillManager

        manager = SkillManager(Path.cwd())

        if args.action == "targets":
            self.console.print("[cyan]支持的 Skill 目标平台:[/cyan]")
            for target in manager.list_targets():
                self.console.print(f"  - {target}")
            return 0

        if args.action == "list":
            installed = manager.list_installed(args.target)
            if not installed:
                self.console.print(f"[dim]{args.target} 未安装任何 skill[/dim]")
                return 0

            self.console.print(f"[cyan]{args.target} 已安装 skill:[/cyan]")
            for skill_name in installed:
                self.console.print(f"  - {skill_name}")
            return 0

        if args.action == "install":
            if not args.source_or_name:
                self.console.print("[red]请提供 skill 来源（目录/git/super-dev）[/red]")
                return 1

            try:
                result = manager.install(
                    source=args.source_or_name,
                    target=args.target,
                    name=args.name,
                    force=args.force,
                )
            except Exception as e:
                self.console.print(f"[red]Skill 安装失败: {e}[/red]")
                return 1

            self.console.print("[green]✓ Skill 安装成功[/green]")
            self.console.print(f"  名称: {result.name}")
            self.console.print(f"  目标: {result.target}")
            self.console.print(f"  路径: {result.path}")
            self.console.print(f"  来源: {result.source}")
            return 0

        if args.action == "uninstall":
            if not args.source_or_name:
                self.console.print("[red]请提供要卸载的 skill 名称[/red]")
                return 1

            try:
                removed_path = manager.uninstall(args.source_or_name, args.target)
            except Exception as e:
                self.console.print(f"[red]Skill 卸载失败: {e}[/red]")
                return 1

            self.console.print("[green]✓ Skill 已卸载[/green]")
            self.console.print(f"  路径: {removed_path}")
            return 0

        self.console.print("[yellow]未知 skill 操作[/yellow]")
        return 1

    def _cmd_integrate(self, args) -> int:
        """多平台集成配置"""
        from .integrations import IntegrationManager

        manager = IntegrationManager(Path.cwd())

        if args.action == "list":
            self.console.print("[cyan]支持的集成平台:[/cyan]")
            for integration_target in manager.list_targets():
                self.console.print(
                    f"  - {integration_target.name}: {integration_target.description}"
                )
            return 0

        if args.action == "setup":
            if args.all:
                results = manager.setup_all(force=args.force)
                self.console.print("[green]✓ 已完成所有平台集成配置[/green]")
                for platform, files in results.items():
                    if not files:
                        self.console.print(f"  {platform}: [dim]无变更[/dim]")
                        continue
                    self.console.print(f"  {platform}:")
                    for generated_file in files:
                        self.console.print(f"    - {generated_file}")
                return 0

            if not args.target:
                self.console.print("[red]请通过 --target 指定平台，或使用 --all[/red]")
                return 1

            files = manager.setup(args.target, force=args.force)
            if not files:
                self.console.print("[yellow]配置已存在，无需修改（可加 --force 覆盖）[/yellow]")
                return 0

            self.console.print("[green]✓ 集成配置已生成[/green]")
            for generated_file in files:
                self.console.print(f"  - {generated_file}")
            return 0

        if args.action == "harden":
            from .skills import SkillManager

            project_dir = Path.cwd()
            available_targets = [item.name for item in manager.list_targets()]
            include_user_surfaces = bool(getattr(args, "with_user_surfaces", False))
            hardening_detected_meta: dict[str, list[str]] = {}
            if args.target:
                hardening_targets = [args.target]
            elif args.all:
                hardening_targets = available_targets
            else:
                hardening_targets, hardening_detected_meta = self._detect_host_targets(
                    available_targets=available_targets
                )
                if not hardening_targets:
                    hardening_targets = available_targets
            hardening_results: dict[str, Any] = {}
            skill_manager = SkillManager(project_dir)
            official_compare_enabled = bool(getattr(args, "official_compare", False)) or True
            usage_profiles: dict[str, dict[str, Any]] = {}
            for target in hardening_targets:
                profile = manager.get_adapter_profile(target)
                plan = manager.host_hardening_blueprint(
                    target,
                    include_user_surfaces=include_user_surfaces,
                )
                usage_profiles[target] = self._build_host_usage_profile(
                    integration_manager=manager,
                    target=target,
                )
                written_files = [str(path) for path in manager.setup(target=target, force=True)]
                slash_file = manager.setup_slash_command(target=target, force=True)
                if slash_file is not None:
                    written_files.append(str(slash_file))
                if include_user_surfaces:
                    global_protocol = manager.setup_global_protocol(target=target, force=True)
                    if global_protocol is not None:
                        written_files.append(str(global_protocol))
                    global_slash = manager.setup_global_slash_command(target=target, force=True)
                    if global_slash is not None:
                        written_files.append(str(global_slash))
                skill_install: dict[str, Any] = {
                    "required": manager.requires_skill(target),
                    "installed": False,
                }
                if manager.requires_skill(target):
                    try:
                        skill_path = skill_manager.install(
                            source="super-dev",
                            target=target,
                            name=skill_manager.default_skill_name(target),
                            force=True,
                        ).path
                        skill_install = {
                            "required": True,
                            "installed": True,
                            "path": str(skill_path),
                        }
                    except Exception as exc:
                        skill_install = {
                            "required": True,
                            "installed": False,
                            "error": str(exc),
                        }
                docs_check = (
                    manager.verify_official_docs(target)
                    if bool(getattr(args, "verify_docs", False))
                    else {}
                )
                official_compare = (
                    manager.compare_official_capabilities(target, timeout_seconds=8.0)
                    if official_compare_enabled
                    else {}
                )
                hardening_results[target] = {
                    "host": target,
                    "category": profile.category,
                    "adapter_mode": profile.adapter_mode,
                    "plan": plan,
                    "written_files": written_files,
                    "skill_install": skill_install,
                    "contract": {},
                    "docs_check": docs_check,
                    "official_compare": official_compare,
                }
            report = self._collect_host_diagnostics(
                project_dir=project_dir,
                targets=hardening_targets,
                skill_name="super-dev",
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            compatibility = self._build_compatibility_summary(
                report=report,
                targets=hardening_targets,
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            hosts_report = report.get("hosts", {}) if isinstance(report, dict) else {}
            if isinstance(hosts_report, dict):
                for target in hardening_targets:
                    host_info = hosts_report.get(target, {})
                    checks = host_info.get("checks", {}) if isinstance(host_info, dict) else {}
                    contract = checks.get("contract", {}) if isinstance(checks, dict) else {}
                    item = hardening_results.get(target, {})
                    if isinstance(item, dict):
                        item["contract"] = contract if isinstance(contract, dict) else {}
            payload = {
                "project_dir": str(project_dir),
                "detected_hosts": (
                    hardening_targets
                    if not hardening_detected_meta
                    else list(hardening_detected_meta.keys())
                ),
                "detection_details": hardening_detected_meta,
                "selected_targets": hardening_targets,
                "hardening_results": hardening_results,
                "report": report,
                "compatibility": compatibility,
                "usage_profiles": usage_profiles,
            }
            official_compare_summary = self._build_official_compare_summary(
                hardening_results=hardening_results
            )
            host_parity_summary = self._build_host_parity_summary(usage_profiles=usage_profiles)
            host_gate_summary = self._build_host_gate_summary(
                report=report, targets=hardening_targets
            )
            host_runtime_script_summary = self._build_host_runtime_script_summary(
                usage_profiles=usage_profiles
            )
            host_recovery_summary = self._build_host_recovery_summary(
                targets=hardening_targets,
                usage_profiles=usage_profiles,
            )
            payload["official_compare_summary"] = official_compare_summary
            payload["host_parity_summary"] = host_parity_summary
            payload["host_gate_summary"] = host_gate_summary
            payload["host_runtime_script_summary"] = host_runtime_script_summary
            payload["host_recovery_summary"] = host_recovery_summary
            parity_index = self._build_host_parity_index(
                threshold=float(getattr(args, "parity_threshold", 95.0)),
                official_compare_summary=official_compare_summary,
                host_parity_summary=host_parity_summary,
                host_gate_summary=host_gate_summary,
                host_runtime_script_summary=host_runtime_script_summary,
                host_recovery_summary=host_recovery_summary,
                compatibility=compatibility,
            )
            payload["host_parity_index"] = parity_index
            if not bool(args.no_save):
                report_files = self._write_host_hardening_report(
                    project_dir=project_dir, payload=payload
                )
                payload["report_files"] = {name: str(path) for name, path in report_files.items()}
            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                return (
                    0
                    if bool(report.get("overall_ready", False))
                    and bool(parity_index.get("passed", False))
                    else 1
                )

            self.console.print("[cyan]Super Dev 宿主系统级深适配[/cyan]")
            self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
            self.console.print(
                f"[cyan]兼容性评分: {compatibility['overall_score']:.2f}/100 "
                f"(ready {compatibility['ready_hosts']}/{compatibility['total_hosts']})[/cyan]"
            )
            self.console.print(
                f"[cyan]流程一致性: {compatibility.get('flow_consistency_score', 0):.2f}/100 "
                f"({compatibility.get('flow_consistent_hosts', 0)}/{compatibility.get('total_hosts', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]官方文档对照: {official_compare_summary.get('score', 0):.2f}/100 "
                f"({official_compare_summary.get('passed', 0)}/{official_compare_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]宿主体验一致性: {host_parity_summary.get('score', 0):.2f}/100 "
                f"({host_parity_summary.get('passed', 0)}/{host_parity_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]确认门禁一致性: {host_gate_summary.get('score', 0):.2f}/100 "
                f"({host_gate_summary.get('passed', 0)}/{host_gate_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]真人验收脚本一致性: {host_runtime_script_summary.get('score', 0):.2f}/100 "
                f"({host_runtime_script_summary.get('passed', 0)}/{host_runtime_script_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]失败恢复一致性: {host_recovery_summary.get('score', 0):.2f}/100 "
                f"({host_recovery_summary.get('passed', 0)}/{host_recovery_summary.get('total', 0)})[/cyan]"
            )
            self.console.print(
                f"[cyan]宿主一致性指数: {parity_index.get('score', 0):.2f}/100 "
                f"(阈值 {parity_index.get('threshold', 95.0):.2f}，"
                f"{'通过' if bool(parity_index.get('passed', False)) else '失败'})[/cyan]"
            )
            for target in hardening_targets:
                item = hardening_results.get(target, {})
                contract = item.get("contract", {})
                ok = bool((contract or {}).get("ok", False))
                self.console.print("")
                self.console.print(
                    f"[cyan]- {target}[/cyan] "
                    f"{'[green]契约通过[/green]' if ok else '[yellow]需要复核[/yellow]'}"
                )
                written_files = item.get("written_files", [])
                if isinstance(written_files, list) and written_files:
                    self.console.print("  已更新:")
                    for file_path in written_files:
                        self.console.print(f"    - {file_path}")
                skill_install = item.get("skill_install", {})
                if isinstance(skill_install, dict) and bool(skill_install.get("required", False)):
                    if bool(skill_install.get("installed", False)):
                        self.console.print(
                            f"  Skill 安装: [green]通过[/green] ({skill_install.get('path', '-')})"
                        )
                    else:
                        self.console.print(
                            f"  Skill 安装: [yellow]失败[/yellow] ({skill_install.get('error', '-')})"
                        )
                docs_check = item.get("docs_check", {})
                if isinstance(docs_check, dict) and docs_check:
                    self.console.print(
                        f"  文档在线核验: {docs_check.get('status', 'unknown')} "
                        f"({docs_check.get('reachable', 0)}/{docs_check.get('checked', 0)})"
                    )
                official_compares = payload.get("official_compares", {})
                if isinstance(official_compares, dict):
                    compare = official_compares.get(target, {})
                    if isinstance(compare, dict) and compare:
                        self.console.print(
                            f"  官方对照: {compare.get('status', 'unknown')} "
                            f"({compare.get('reachable_urls', 0)}/{compare.get('checked_urls', 0)})"
                        )
                official_compare = item.get("official_compare", {})
                if isinstance(official_compare, dict) and official_compare:
                    self.console.print(
                        f"  官方对照: {official_compare.get('status', 'unknown')} "
                        f"({official_compare.get('reachable_urls', 0)}/{official_compare.get('checked_urls', 0)})"
                    )
                invalid = (contract or {}).get("invalid_surfaces", {})
                if isinstance(invalid, dict) and invalid:
                    self.console.print("  [yellow]仍有不一致面[/yellow]:")
                    for surface_key in invalid.keys():
                        self.console.print(f"    - {surface_key}")
                else:
                    self.console.print("  [green]✓[/green] 接入面已与系统流程契约对齐")
            if "report_files" in payload:
                report_files = payload["report_files"]
                if isinstance(report_files, dict):
                    self.console.print("")
                    self.console.print("[cyan]深适配报告[/cyan]")
                    for name, path in report_files.items():
                        self.console.print(f"  - {name}: {path}")
            return (
                0
                if bool(report.get("overall_ready", False))
                and bool(parity_index.get("passed", False))
                else 1
            )

        if args.action == "matrix":
            matrix_targets: list[str] | None = [args.target] if args.target else None
            profiles = manager.list_adapter_profiles(targets=matrix_targets)
            docs_checks: dict[str, Any] = {}
            matrix_official_compares: dict[str, Any] = {}
            if bool(getattr(args, "verify_docs", False)):
                for profile in profiles:
                    docs_checks[profile.host] = manager.verify_official_docs(profile.host)
            if bool(getattr(args, "official_compare", False)):
                for profile in profiles:
                    matrix_official_compares[profile.host] = manager.compare_official_capabilities(
                        profile.host
                    )
            if args.json:
                payload = {
                    "profiles": [profile.to_dict() for profile in profiles],
                    "docs_checks": docs_checks,
                    "official_compares": matrix_official_compares,
                }
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                return 0

            self.console.print("[cyan]Super Dev 宿主适配矩阵[/cyan]")
            verified_count = sum(1 for item in profiles if item.docs_verified)
            self.console.print(f"[dim]官方文档核验: {verified_count}/{len(profiles)}[/dim]")
            for profile in profiles:
                self.console.print(f"[cyan]- {profile.host} ({profile.category})[/cyan]")
                self.console.print(f"  适配模式: {profile.adapter_mode}")
                self.console.print(f"  使用模式: {profile.usage_mode}")
                self.console.print(f"  模型提供方: {profile.host_model_provider}")
                docs_badge = "verified" if profile.docs_verified else "pending"
                docs_url = profile.official_docs_url or "-"
                self.console.print(f"  官方文档: {docs_url} ({docs_badge})")
                if profile.official_docs_references:
                    self.console.print(f"  官方参考: {len(profile.official_docs_references)} 条")
                labels = profile.capability_labels or {}
                capability_summary = (
                    ", ".join(f"{key}={value}" for key, value in labels.items()) if labels else "-"
                )
                self.console.print(f"  能力标签: {capability_summary}")
                if profile.host in docs_checks:
                    docs_check = docs_checks[profile.host]
                    self.console.print(
                        f"  文档在线核验: {docs_check.get('status', 'unknown')} "
                        f"({docs_check.get('reachable', 0)}/{docs_check.get('checked', 0)})"
                    )
                if profile.host in matrix_official_compares:
                    compare = matrix_official_compares[profile.host]
                    self.console.print(
                        f"  官方对照: {compare.get('status', 'unknown')} "
                        f"({compare.get('reachable_urls', 0)}/{compare.get('checked_urls', 0)})"
                    )
                self.console.print(f"  主入口: {profile.primary_entry}")
                self.console.print(f"  触发命令: {profile.trigger_command}")
                self.console.print(f"  触发上下文: {profile.trigger_context}")
                self.console.print(f"  触发位置: {profile.usage_location}")
                self.console.print(f"  终端入口: {profile.terminal_entry}")
                self.console.print(f"  终端范围: {profile.terminal_entry_scope}")
                self.console.print(
                    f"  接入后重启: {'是' if profile.requires_restart_after_onboard else '否'}"
                )
                self.console.print(f"  规则文件: {', '.join(profile.integration_files)}")
                self.console.print(f"  Slash 文件: {profile.slash_command_file}")
                self.console.print(f"  Skill 目录: {profile.skill_dir}")
                commands = (
                    ", ".join(profile.detection_commands) if profile.detection_commands else "-"
                )
                paths = ", ".join(profile.detection_paths) if profile.detection_paths else "-"
                self.console.print(f"  探测命令: {commands}")
                self.console.print(f"  探测路径: {paths}")
                if profile.post_onboard_steps:
                    self.console.print("  接入后步骤:")
                    for step in profile.post_onboard_steps:
                        self.console.print(f"    - {step}")
                if profile.usage_notes:
                    self.console.print("  使用提示:")
                    for note in profile.usage_notes:
                        self.console.print(f"    - {note}")
                self.console.print(f"  冒烟验证语句: {profile.smoke_test_prompt}")
                self.console.print(f"  通过标志: {profile.smoke_success_signal}")
                self.console.print(f"  备注: {profile.notes}")
            return 0

        if args.action == "smoke":
            smoke_targets: list[str] = (
                [args.target] if args.target else [item.name for item in manager.list_targets()]
            )
            profiles = manager.list_adapter_profiles(targets=smoke_targets)
            if args.json:
                smoke_payload = [
                    {
                        "host": profile.host,
                        "final_trigger": self._display_final_trigger(profile),
                        "smoke_test_prompt": profile.smoke_test_prompt,
                        "smoke_test_steps": list(profile.smoke_test_steps),
                        "smoke_success_signal": profile.smoke_success_signal,
                    }
                    for profile in profiles
                ]
                sys.stdout.write(json.dumps(smoke_payload, ensure_ascii=False, indent=2) + "\n")
                return 0

            self.console.print("[cyan]Super Dev 宿主冒烟验证[/cyan]")
            for profile in profiles:
                self.console.print(f"[cyan]- {profile.host}[/cyan]")
                self.console.print(f"  最终输入: {self._display_final_trigger(profile)}")
                self.console.print(f"  验收语句: {profile.smoke_test_prompt}")
                self.console.print("  验收步骤:")
                for step in profile.smoke_test_steps:
                    self.console.print(f"    - {step}")
                self.console.print(f"  通过标准: {profile.smoke_success_signal}")
            return 0

        if args.action == "audit":
            project_dir = Path.cwd()
            available_targets = [item.name for item in manager.list_targets()]
            audit_targets: list[str]
            audit_detected_meta: dict[str, list[str]] = {}
            if args.target:
                audit_targets = [args.target]
            elif args.all:
                audit_targets = available_targets
            else:
                audit_targets, audit_detected_meta = self._detect_host_targets(
                    available_targets=available_targets
                )
                if not audit_targets:
                    audit_targets = available_targets

            report = self._collect_host_diagnostics(
                project_dir=project_dir,
                targets=audit_targets,
                skill_name="super-dev",
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            repair_actions: dict[str, dict[str, str]] = {}
            if args.repair:
                repair_actions = self._repair_host_diagnostics(
                    project_dir=project_dir,
                    report=report,
                    skill_name="super-dev",
                    force=bool(args.force),
                    check_integrate=True,
                    check_skill=True,
                    check_slash=True,
                    include_user_surfaces=self._include_user_surfaces(args),
                )
                report = self._collect_host_diagnostics(
                    project_dir=project_dir,
                    targets=audit_targets,
                    skill_name="super-dev",
                    check_integrate=True,
                    check_skill=True,
                    check_slash=True,
                )

            compatibility = self._build_compatibility_summary(
                report=report,
                targets=audit_targets,
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            usage_profiles = {
                host_id: self._build_host_usage_profile(
                    integration_manager=manager,
                    target=host_id,
                )
                for host_id in audit_targets
            }
            payload = {
                "project_dir": str(project_dir),
                "detected_hosts": (
                    audit_targets if not audit_detected_meta else list(audit_detected_meta.keys())
                ),
                "detection_details": audit_detected_meta,
                "selected_targets": audit_targets,
                "report": report,
                "compatibility": compatibility,
                "usage_profiles": usage_profiles,
                "repair_actions": repair_actions,
            }
            payload["host_parity_summary"] = self._build_host_parity_summary(
                usage_profiles=usage_profiles
            )
            payload["host_gate_summary"] = self._build_host_gate_summary(
                report=report, targets=audit_targets
            )
            payload["host_runtime_script_summary"] = self._build_host_runtime_script_summary(
                usage_profiles=usage_profiles
            )
            payload["host_recovery_summary"] = self._build_host_recovery_summary(
                targets=audit_targets,
                usage_profiles=usage_profiles,
            )
            if bool(getattr(args, "verify_docs", False)):
                payload["docs_checks"] = {
                    host_id: manager.verify_official_docs(host_id) for host_id in audit_targets
                }
            if bool(getattr(args, "official_compare", False)):
                audit_official_compares = {
                    host_id: manager.compare_official_capabilities(host_id, timeout_seconds=8.0)
                    for host_id in audit_targets
                }
                payload["official_compares"] = audit_official_compares
                payload["official_compare_summary"] = self._build_official_compare_summary(
                    hardening_results={
                        host_id: {"official_compare": audit_official_compares.get(host_id, {})}
                        for host_id in audit_targets
                    }
                )
            payload["host_parity_index"] = self._build_host_parity_index(
                threshold=float(getattr(args, "parity_threshold", 95.0)),
                official_compare_summary=payload.get("official_compare_summary", {}),
                host_parity_summary=payload.get("host_parity_summary", {}),
                host_gate_summary=payload.get("host_gate_summary", {}),
                host_runtime_script_summary=payload.get("host_runtime_script_summary", {}),
                host_recovery_summary=payload.get("host_recovery_summary", {}),
                compatibility=compatibility,
            )
            if not bool(args.no_save):
                report_files = self._write_host_surface_audit_report(
                    project_dir=project_dir, payload=payload
                )
                payload["report_files"] = {name: str(path) for name, path in report_files.items()}

            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                parity_index = payload.get("host_parity_index", {})
                return (
                    0
                    if bool(report.get("overall_ready", False))
                    and bool((parity_index or {}).get("passed", False))
                    else 1
                )

            self.console.print("[cyan]Super Dev 宿主接入面审计[/cyan]")
            self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
            if audit_detected_meta:
                self.console.print(
                    f"[cyan]自动检测到 {len(audit_detected_meta)} 个宿主："
                    f"{', '.join(self._host_label(host_id) for host_id in audit_detected_meta)}[/cyan]"
                )
            self.console.print(
                f"[cyan]兼容性评分: {compatibility['overall_score']:.2f}/100 "
                f"(ready {compatibility['ready_hosts']}/{compatibility['total_hosts']})[/cyan]"
            )
            self.console.print(
                f"[cyan]流程一致性: {compatibility.get('flow_consistency_score', 0):.2f}/100 "
                f"({compatibility.get('flow_consistent_hosts', 0)}/{compatibility.get('total_hosts', 0)})[/cyan]"
            )
            host_parity = payload.get("host_parity_summary", {})
            if isinstance(host_parity, dict) and host_parity:
                self.console.print(
                    f"[cyan]宿主体验一致性: {host_parity.get('score', 0):.2f}/100 "
                    f"({host_parity.get('passed', 0)}/{host_parity.get('total', 0)})[/cyan]"
                )
            host_gate = payload.get("host_gate_summary", {})
            if isinstance(host_gate, dict) and host_gate:
                self.console.print(
                    f"[cyan]确认门禁一致性: {host_gate.get('score', 0):.2f}/100 "
                    f"({host_gate.get('passed', 0)}/{host_gate.get('total', 0)})[/cyan]"
                )
            host_runtime_script = payload.get("host_runtime_script_summary", {})
            if isinstance(host_runtime_script, dict) and host_runtime_script:
                self.console.print(
                    f"[cyan]真人验收脚本一致性: {host_runtime_script.get('score', 0):.2f}/100 "
                    f"({host_runtime_script.get('passed', 0)}/{host_runtime_script.get('total', 0)})[/cyan]"
                )
            host_recovery = payload.get("host_recovery_summary", {})
            if isinstance(host_recovery, dict) and host_recovery:
                self.console.print(
                    f"[cyan]失败恢复一致性: {host_recovery.get('score', 0):.2f}/100 "
                    f"({host_recovery.get('passed', 0)}/{host_recovery.get('total', 0)})[/cyan]"
                )
            official_summary = payload.get("official_compare_summary", {})
            if isinstance(official_summary, dict) and official_summary:
                self.console.print(
                    f"[cyan]官方文档对照: {official_summary.get('score', 0):.2f}/100 "
                    f"({official_summary.get('passed', 0)}/{official_summary.get('total', 0)})[/cyan]"
                )
            parity_index = payload.get("host_parity_index", {})
            if isinstance(parity_index, dict) and parity_index:
                self.console.print(
                    f"[cyan]宿主一致性指数: {parity_index.get('score', 0):.2f}/100 "
                    f"(阈值 {parity_index.get('threshold', 95.0):.2f}，"
                    f"{'通过' if bool(parity_index.get('passed', False)) else '失败'})[/cyan]"
                )
            if args.repair and repair_actions:
                self.console.print("[cyan]修复动作[/cyan]")
                for host_id, actions in repair_actions.items():
                    action_text = ", ".join(f"{key}={value}" for key, value in actions.items())
                    self.console.print(f"  - {host_id}: {action_text}")
            for host_id in audit_targets:
                host = report["hosts"].get(host_id, {})
                usage = usage_profiles.get(host_id, {})
                ready = bool(host.get("ready", False))
                self.console.print("")
                self.console.print(
                    f"[cyan]- {host_id}[/cyan] "
                    f"{'[green]就绪[/green]' if ready else '[yellow]需要修复[/yellow]'}"
                )
                self.console.print(f"  触发命令: {usage.get('final_trigger', '-')}")
                self.console.print(f"  宿主协议: {usage.get('host_protocol_summary', '-')}")
                checks = host.get("checks", {})
                contract = checks.get("contract", {}) if isinstance(checks, dict) else {}
                invalid_surfaces = (
                    contract.get("invalid_surfaces", {}) if isinstance(contract, dict) else {}
                )
                if isinstance(invalid_surfaces, dict) and invalid_surfaces:
                    self.console.print("  [yellow]过期/缺失的接入面[/yellow]:")
                    for surface_key, surface_info in invalid_surfaces.items():
                        if not isinstance(surface_info, dict):
                            continue
                        missing_markers = surface_info.get("missing_markers", [])
                        marker_text = (
                            ", ".join(str(item) for item in missing_markers)
                            if isinstance(missing_markers, list)
                            else "-"
                        )
                        self.console.print(f"    - {surface_key}")
                        self.console.print(f"      路径: {surface_info.get('path', '-')}")
                        self.console.print(f"      missing: {marker_text}")
                else:
                    self.console.print("  [green]✓[/green] 所有受管接入面契约完整")
                suggestions = host.get("suggestions", [])
                if isinstance(suggestions, list) and suggestions:
                    self.console.print("  建议修复:")
                    for suggestion in suggestions:
                        self.console.print(f"    - {suggestion}")
            if "report_files" in payload:
                report_files = payload["report_files"]
                if isinstance(report_files, dict):
                    self.console.print("")
                    self.console.print("[cyan]审计报告[/cyan]")
                    for name, path in report_files.items():
                        self.console.print(f"  - {name}: {path}")
            return (
                0
                if bool(report.get("overall_ready", False))
                and bool((parity_index or {}).get("passed", False))
                else 1
            )

        if args.action == "validate":
            project_dir = Path.cwd()
            available_targets = [item.name for item in manager.list_targets()]
            validation_detected_meta: dict[str, list[str]] = {}
            competition_evidence: dict[str, object] = {}
            if args.status and not args.target:
                self.console.print("[red]--status 仅可与 --target 一起使用[/red]")
                return 1
            if args.status and args.status not in {"pending", "passed", "failed"}:
                self.console.print("[red]无效的运行时验收状态[/red]")
                return 1
            if args.competition_evidence_json:
                try:
                    parsed_evidence = json.loads(args.competition_evidence_json)
                except json.JSONDecodeError as exc:
                    self.console.print(f"[red]比赛验收证据 JSON 无效:[/red] {exc}")
                    return 1
                if not isinstance(parsed_evidence, dict):
                    self.console.print("[red]比赛验收证据必须是 JSON object[/red]")
                    return 1
                competition_evidence = parsed_evidence
            if args.status and args.target:
                runtime_state, file_path = self._update_host_runtime_validation_state(
                    project_dir=project_dir,
                    target=args.target,
                    status=args.status,
                    comment=args.comment or "",
                    actor=args.actor or "user",
                    competition_evidence=competition_evidence,
                )
                status_label = self._host_runtime_status_label(args.status)
                if args.json:
                    host_entry = runtime_state.get("hosts", {}).get(args.target, {})
                    if not isinstance(host_entry, dict):
                        host_entry = {}
                    repo_probe = build_host_runtime_probe(
                        project_dir,
                        target=args.target,
                        surface_ready=True,
                    )
                    sys.stdout.write(
                        json.dumps(
                            {
                                "status": "success",
                                "host": args.target,
                                "manual_runtime_status": args.status,
                                "manual_runtime_status_label": status_label,
                                "comment": args.comment or "",
                                "actor": args.actor or "user",
                                "file_path": str(file_path),
                                "updated_at": str(host_entry.get("updated_at", "")).strip(),
                                "competition_evidence": host_entry.get("competition_evidence", {}),
                                "competition_evidence_ready": bool(
                                    host_entry.get("competition_evidence_ready", False)
                                ),
                                "competition_evidence_missing": list(
                                    host_entry.get("competition_evidence_missing", [])
                                ),
                                "repo_probe": repo_probe,
                                "runtime_evidence": self._build_runtime_evidence_record(
                                    host_id=args.target,
                                    surface_ready=True,
                                    runtime_entry=host_entry,
                                ),
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                        + "\n"
                    )
                    return 0
                self.console.print(
                    f"[green]已更新宿主真人验收状态[/green] {args.target}: {status_label}"
                )
                if args.comment:
                    self.console.print(f"[dim]备注: {args.comment}[/dim]")
                missing_competition_sections = (
                    runtime_state.get("hosts", {})
                    .get(args.target, {})
                    .get("competition_evidence_missing", [])
                )
                if isinstance(missing_competition_sections, list) and missing_competition_sections:
                    self.console.print(
                        "[yellow]SEEAI 比赛证据仍未补齐[/yellow] "
                        + "、".join(str(item) for item in missing_competition_sections)
                    )
                self.console.print(f"[dim]状态文件: {file_path}[/dim]")
                return 0

            if args.target:
                validation_targets = [args.target]
            elif args.all:
                validation_targets = available_targets
            else:
                validation_targets, validation_detected_meta = self._detect_host_targets(
                    available_targets=available_targets
                )
                if not validation_targets:
                    validation_targets = available_targets

            report = self._collect_host_diagnostics(
                project_dir=project_dir,
                targets=validation_targets,
                skill_name="super-dev",
                check_integrate=True,
                check_skill=True,
                check_slash=True,
            )
            usage_profiles = {
                host_id: self._build_host_usage_profile(
                    integration_manager=manager,
                    target=host_id,
                )
                for host_id in validation_targets
            }
            payload = self._build_host_runtime_validation_payload(
                project_dir=project_dir,
                targets=validation_targets,
                detected_meta=validation_detected_meta,
                report=report,
                usage_profiles=usage_profiles,
            )

            if not bool(args.no_save):
                report_files = self._write_host_runtime_validation_report(
                    project_dir=project_dir, payload=payload
                )
                payload["report_files"] = {name: str(path) for name, path in report_files.items()}

            if args.json:
                sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                return 0

            self.console.print("[cyan]Super Dev 宿主运行时验收矩阵[/cyan]")
            self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
            if validation_detected_meta:
                self.console.print(
                    f"[cyan]自动检测到 {len(validation_detected_meta)} 个宿主："
                    f"{', '.join(self._host_label(host_id) for host_id in validation_detected_meta)}[/cyan]"
                )
            summary = payload.get("summary", {})
            if isinstance(summary, dict):
                self.console.print(
                    f"[cyan]汇总: 完全就绪 {summary.get('fully_ready_count', 0)}/"
                    f"{summary.get('total_hosts', 0)} | 接入面就绪 "
                    f"{summary.get('surface_ready_count', 0)}/{summary.get('total_hosts', 0)} "
                    f"| 已通过 {summary.get('runtime_passed_count', 0)} "
                    f"| 待处理 {summary.get('runtime_pending_count', 0)} "
                    f"| 失败 {summary.get('runtime_failed_count', 0)} "
                    f"| 仓库检查失败 {summary.get('repo_probe_failed_count', 0)}[/cyan]"
                )
            blockers = payload.get("blockers", [])
            if isinstance(blockers, list) and blockers:
                self.console.print("[yellow]当前阻塞项[/yellow]")
                for item in blockers[:8]:
                    if not isinstance(item, dict):
                        continue
                    self.console.print(f"  - {item.get('host', '-')}: {item.get('summary', '-')}")
            for host in payload.get("hosts", []):
                if not isinstance(host, dict):
                    continue
                ready_badge = (
                    "[green]接入面就绪[/green]"
                    if bool(host.get("surface_ready", False))
                    else "[yellow]接入面未就绪[/yellow]"
                )
                self.console.print("")
                self.console.print(f"[cyan]- {host.get('host', '-') }[/cyan] {ready_badge}")
                self.console.print(f"  触发命令: {host.get('final_trigger', '-')}")
                self.console.print(f"  宿主协议: {host.get('host_protocol_summary', '-')}")
                self.console.print(
                    f"  人工验收状态: {host.get('manual_runtime_status_label', '-')}"
                )
                repo_probe = host.get("repo_probe", {})
                if isinstance(repo_probe, dict):
                    self.console.print(
                        f"  仓库检查: {repo_probe.get('status_label', '待补齐仓库检查')}"
                    )
                    repo_probe_summary = str(repo_probe.get("summary", "")).strip()
                    if repo_probe_summary:
                        self.console.print(f"  仓库级摘要: {repo_probe_summary}")
                if host.get("resume_probe_prompt"):
                    self.console.print("  继续当前流程:")
                    self.console.print(f"    - 宿主第一句: {host.get('resume_probe_prompt')}")
                    self.console.print(
                        f"    - 流程状态卡: {self._session_brief_path(Path(payload.get('project_dir', Path.cwd())))}"
                    )
                framework_playbook = host.get("framework_playbook", {})
                if isinstance(framework_playbook, dict) and framework_playbook:
                    self.console.print(
                        f"  跨平台框架专项: {framework_playbook.get('framework', '跨平台框架')}"
                    )
                    native_capabilities = framework_playbook.get("native_capabilities", [])
                    if isinstance(native_capabilities, list) and native_capabilities:
                        self.console.print(
                            "    - 原生能力面: "
                            + "；".join(str(item) for item in native_capabilities[:3])
                        )
                    validation_surfaces = framework_playbook.get("validation_surfaces", [])
                    if isinstance(validation_surfaces, list) and validation_surfaces:
                        self.console.print(
                            "    - 必验场景: "
                            + "；".join(str(item) for item in validation_surfaces[:3])
                        )
                if host.get("blocking_reason"):
                    self.console.print(f"  阻塞原因: {host.get('blocking_reason')}")
                if host.get("recommended_action"):
                    self.console.print(f"  建议动作: {host.get('recommended_action')}")
                if host.get("resume_probe_prompt"):
                    self.console.print(f"  恢复检查语句: {host.get('resume_probe_prompt')}")
                comment = host.get("manual_runtime_comment", "")
                if isinstance(comment, str) and comment.strip():
                    self.console.print(f"  验收备注: {comment.strip()}")
                self.console.print("  运行时检查清单:")
                checklist = host.get("runtime_checklist", [])
                if isinstance(checklist, list):
                    for item in checklist:
                        self.console.print(f"    - {item}")
                self.console.print("  通过标准:")
                criteria = host.get("pass_criteria", [])
                if isinstance(criteria, list):
                    for item in criteria:
                        self.console.print(f"    - {item}")
                resume_checklist = host.get("resume_checklist", [])
                if isinstance(resume_checklist, list) and resume_checklist:
                    self.console.print("  恢复检查清单:")
                    for item in resume_checklist:
                        self.console.print(f"    - {item}")
            if "report_files" in payload:
                report_files = payload["report_files"]
                if isinstance(report_files, dict):
                    self.console.print("")
                    self.console.print("[cyan]验收矩阵报告[/cyan]")
                    for name, path in report_files.items():
                        self.console.print(f"  - {name}: {path}")
            if isinstance(summary, dict):
                next_actions = summary.get("next_actions", [])
                if isinstance(next_actions, list) and next_actions:
                    self.console.print("")
                    self.console.print("[cyan]推荐动作[/cyan]")
                    for item in next_actions[:8]:
                        self.console.print(f"  - {item}")
            return 0

        self.console.print("[yellow]未知 integrate 操作[/yellow]")
        return 1
