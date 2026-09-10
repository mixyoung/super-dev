"""Host onboarding, maintenance and cleanup commands."""

import argparse
import contextlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.panel import Panel

from . import __version__
from .catalogs import (
    PRIMARY_HOST_TOOL_IDS,
)
from .config import ConfigManager, get_config_manager
from .integrations.install_manifest import record_install_manifest
from .terminal import output_mode_label, output_mode_reason
from .workflow_state import (
    load_framework_playbook_summary,
)


class CliHostCommandsMixin:
    def _cmd_onboard(self, args) -> int:
        """首次接入向导：宿主选择 + 集成 + skill + slash"""
        from .integrations import IntegrationManager
        from .skills import SkillManager

        if not self._ensure_host_support_matrix():
            return 1
        include_user_surfaces = self._include_user_surfaces(args)
        if self._is_manual_install_host(getattr(args, "host", None)):
            return int(
                self._print_manual_install_host_guidance(
                    target=str(args.host), command_name="onboard"
                )
            )

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        skill_manager = SkillManager(project_dir)
        detail = bool(getattr(args, "detail", False))

        available_targets = self._public_host_targets(integration_manager=integration_manager)
        targets: list[str]
        detected_meta: dict[str, list[str]] = {}

        if args.host:
            targets = [args.host]
        elif args.all:
            targets = available_targets
        elif args.auto:
            targets, detected_meta = self._detect_host_targets(available_targets=available_targets)
            targets = self._deduplicate_host_family(targets)
            if not targets:
                self.console.print("[red]未检测到可用宿主，请改用 --host 指定或使用 --all[/red]")
                self.console.print(f"[dim]{self._custom_host_path_override_hint()}[/dim]")
                return 1
            self.console.print(
                f"[cyan]自动检测到 {len(targets)} 个宿主：{', '.join(self._host_label(target) for target in targets)}[/cyan]"
            )
            for target in targets:
                reasons = ", ".join(
                    self._format_detection_reason(item) for item in detected_meta.get(target, [])
                )
                if reasons:
                    self.console.print(f"[dim]  - {self._host_label(target)}: {reasons}[/dim]")
        else:
            try:
                targets = self._resolve_onboard_targets(
                    available_targets=available_targets,
                    host=args.host,
                    all_targets=bool(args.all),
                    non_interactive=bool(args.yes),
                )
            except ValueError as exc:
                self.console.print(f"[red]{exc}[/red]")
                return 1

        if not targets:
            self.console.print("[red]未选择任何宿主工具[/red]")
            return 1

        if getattr(args, "stable_only", False):
            stable_targets = []
            for t in targets:
                profile = integration_manager.get_adapter_profile(t)
                cert = profile.certification_label.lower()
                if cert.startswith("certified") or cert.startswith("compatible"):
                    stable_targets.append(t)
            if not stable_targets:
                self.console.print("[yellow]未找到 Certified 或 Compatible 级别的宿主[/yellow]")
                return 1
            skipped = set(targets) - set(stable_targets)
            if skipped:
                self.console.print(
                    f"[dim]跳过 Experimental 宿主: {', '.join(self._host_label(target) for target in sorted(skipped))}[/dim]"
                )
            targets = stable_targets

        setattr(args, "_selected_targets", list(targets))

        self.console.print("")
        from rich.panel import Panel
        from rich.rule import Rule

        self.console.print(
            Panel(
                f"[bold cyan]Super Dev Onboard[/bold cyan]\n\n"
                f"  [dim]项目[/dim]      {project_dir.name}\n"
                f"  [dim]目标宿主[/dim]  {len(targets)} 个\n"
                f"  [dim]版本[/dim]      {__version__}",
                border_style="cyan",
                expand=True,
                padding=(1, 2),
            )
        )
        self.console.print("")
        has_error = False
        target_results: list[dict[str, Any]] = []
        for idx, target in enumerate(targets, 1):
            protocol = integration_manager._protocol_profile(target=target)
            protocol_summary = protocol.get("summary", "") if isinstance(protocol, dict) else ""
            self.console.print(
                Rule(
                    f"[bold cyan] {idx}/{len(targets)} [/bold cyan] [bold]{self._host_label(target)}[/bold]  [dim]{protocol_summary}[/dim]",
                    style="dim cyan",
                )
            )
            self.console.print("")

            profile = integration_manager.get_adapter_profile(target)
            manifest_paths: list[str] = []
            has_project_surface = False
            has_global_surface = False
            has_runtime_surface = False
            target_errors: list[str] = []

            if getattr(args, "dry_run", False):
                surfaces = integration_manager.collect_managed_surface_paths(
                    target=target,
                    include_user_surfaces=include_user_surfaces,
                )
                self.console.print("  [dim]将写入以下文件:[/dim]")
                for key, path in surfaces.items():
                    exists = path.exists()
                    status = "[dim]已存在[/dim]" if exists else "[cyan]新建[/cyan]"
                    self.console.print(f"    {status} {path}")
                self.console.print("")
                continue

            # Check whether this host has integration files to write
            target_config = integration_manager.TARGETS.get(target)
            has_integrate_files = bool(target_config and target_config.files)

            if not args.skip_integrate and has_integrate_files:
                try:
                    written_files = integration_manager.setup(target=target, force=args.force)
                    integrate_written_count = len(written_files)
                    if written_files:
                        has_project_surface = True
                        manifest_paths.extend(str(item) for item in written_files)
                    if written_files:
                        if detail:
                            for item in written_files:
                                self.console.print(
                                    f"  [green]✓[/green] 集成规则: {item}",
                                    soft_wrap=True,
                                )
                        else:
                            self.console.print(
                                f"  [green]✓[/green] 集成规则: {integrate_written_count} 项"
                            )
                    else:
                        self.console.print("  [dim]- 集成规则已存在（可加 --force 覆盖）[/dim]")
                    if include_user_surfaces:
                        global_protocol = integration_manager.setup_global_protocol(
                            target=target, force=args.force
                        )
                        if global_protocol is not None:
                            has_global_surface = True
                            manifest_paths.append(str(global_protocol))
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] 宿主协议: {global_protocol}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print("  [green]✓[/green] 宿主协议: 已写入")
                        global_agent_surfaces = integration_manager.setup_global_agent_surfaces(
                            target=target,
                            force=args.force,
                        )
                        if global_agent_surfaces:
                            has_global_surface = True
                            manifest_paths.extend(str(item) for item in global_agent_surfaces)
                            if detail:
                                for item in global_agent_surfaces:
                                    self.console.print(
                                        f"  [green]✓[/green] 用户级 Agent 面: {item}",
                                        soft_wrap=True,
                                    )
                            else:
                                self.console.print(
                                    f"  [green]✓[/green] 用户级 Agent 面: {len(global_agent_surfaces)} 项"
                                )
                except Exception as exc:
                    has_error = True
                    target_errors.append(f"integrate: {exc}")
                    self.console.print(f"  [yellow]⚠[/yellow] 集成规则写入失败: {exc}")
            elif not args.skip_integrate and not has_integrate_files:
                self.console.print("  [dim]- 该宿主无项目级集成文件，跳过集成规则[/dim]")
                # Still attempt global protocol even for hosts without project files
                try:
                    if include_user_surfaces:
                        global_protocol = integration_manager.setup_global_protocol(
                            target=target, force=args.force
                        )
                        if global_protocol is not None:
                            has_global_surface = True
                            manifest_paths.append(str(global_protocol))
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] 宿主协议: {global_protocol}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print("  [green]✓[/green] 宿主协议: 已写入")
                        global_agent_surfaces = integration_manager.setup_global_agent_surfaces(
                            target=target,
                            force=args.force,
                        )
                        if global_agent_surfaces:
                            has_global_surface = True
                            manifest_paths.extend(str(item) for item in global_agent_surfaces)
                            if detail:
                                for item in global_agent_surfaces:
                                    self.console.print(
                                        f"  [green]✓[/green] 用户级 Agent 面: {item}",
                                        soft_wrap=True,
                                    )
                            else:
                                self.console.print(
                                    f"  [green]✓[/green] 用户级 Agent 面: {len(global_agent_surfaces)} 项"
                                )
                except Exception as exc:
                    target_errors.append(f"global integrate: {exc}")
                    self.console.print(f"  [yellow]⚠[/yellow] 宿主协议写入失败: {exc}")

            if not args.skip_skill and IntegrationManager.requires_skill(target):
                try:
                    if not skill_manager.skill_surface_available(target):
                        self.console.print(
                            "  [dim]- 未检测到官方或兼容 Skill 目录，已跳过宿主级 Skill 安装[/dim]"
                        )
                    else:
                        target_skill_name = SkillManager.default_skill_name(target)
                        installed = set(skill_manager.list_installed(target))
                        if target_skill_name in installed and not args.force:
                            self.console.print(
                                f"  [dim]- Skill 已存在: {target_skill_name}（可加 --force 重装）[/dim]"
                            )
                        else:
                            install_result = skill_manager.install(
                                source="super-dev",
                                target=target,
                                name=target_skill_name,
                                force=args.force,
                            )
                            manifest_paths.append(str(install_result.path))
                            if str(install_result.path).startswith(str(Path.home())):
                                has_global_surface = True
                            else:
                                has_project_surface = True
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] Skill: {install_result.path}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print("  [green]✓[/green] Skill: 已安装")
                        legacy_removed = skill_manager.cleanup_legacy_skill_aliases(target)
                        if legacy_removed:
                            self.console.print("  [green]✓[/green] 已清理旧版 Super Dev 技能残留")
                except Exception as exc:
                    has_error = True
                    target_errors.append(f"skill: {exc}")
                    self.console.print(f"  [red]✗[/red] Skill 安装失败: {exc}")
            elif not args.skip_skill:
                self.console.print("  [dim]- 该宿主默认按项目规则运行，已跳过 Skill 安装[/dim]")

            # Clean up legacy skill-alias agent files
            legacy_agent_files: list[Path] = []
            legacy_agent_name = "super-dev" + "-core.md"
            if target == "claude-code":
                legacy_agent_files = [
                    Path.home() / ".claude" / "agents" / legacy_agent_name,
                    project_dir / ".claude" / "agents" / legacy_agent_name,
                ]
            elif target in ("codebuddy", "codebuddy-cli"):
                legacy_agent_files = [
                    project_dir / ".codebuddy" / "agents" / legacy_agent_name,
                    Path.home() / ".codebuddy" / "agents" / legacy_agent_name,
                ]
            for legacy_path in legacy_agent_files:
                if legacy_path.exists():
                    try:
                        legacy_path.unlink()
                        self.console.print(f"  [green]✓[/green] 已清理旧版: {legacy_path.name}")
                    except Exception:
                        pass

            if not args.skip_slash:
                try:
                    if integration_manager.supports_slash(target):
                        slash_file = integration_manager.setup_slash_command(
                            target=target,
                            force=args.force,
                        )
                        if slash_file is None:
                            self.console.print(
                                "  [dim]- /super-dev 映射已存在（可加 --force 覆盖）[/dim]"
                            )
                        else:
                            has_project_surface = True
                            manifest_paths.append(str(slash_file))
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] /super-dev 映射: {slash_file}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print("  [green]✓[/green] /super-dev 映射: 已写入")
                        if include_user_surfaces:
                            global_slash_file = integration_manager.setup_global_slash_command(
                                target=target,
                                force=args.force,
                            )
                            if global_slash_file is None:
                                self.console.print(
                                    "  [dim]- 全局 /super-dev 映射已存在（可加 --force 覆盖）[/dim]"
                                )
                            elif (
                                slash_file is None
                                or global_slash_file.resolve() != slash_file.resolve()
                            ):
                                has_global_surface = True
                                manifest_paths.append(str(global_slash_file))
                                if detail:
                                    self.console.print(
                                        f"  [green]✓[/green] 全局 /super-dev 映射: {global_slash_file}",
                                        soft_wrap=True,
                                    )
                                else:
                                    self.console.print(
                                        "  [green]✓[/green] 全局 /super-dev 映射: 已写入"
                                    )
                        seeai_slash_file = integration_manager.setup_seeai_slash_command(
                            target=target,
                            force=args.force,
                        )
                        if seeai_slash_file is None:
                            self.console.print(
                                "  [dim]- /super-dev-seeai 映射已存在（可加 --force 覆盖）[/dim]"
                            )
                        else:
                            has_project_surface = True
                            manifest_paths.append(str(seeai_slash_file))
                            if detail:
                                self.console.print(
                                    f"  [green]✓[/green] /super-dev-seeai 映射: {seeai_slash_file}",
                                    soft_wrap=True,
                                )
                            else:
                                self.console.print(
                                    "  [green]✓[/green] /super-dev-seeai 映射: 已写入"
                                )
                        if include_user_surfaces:
                            global_seeai_slash_file = (
                                integration_manager.setup_global_seeai_slash_command(
                                    target=target,
                                    force=args.force,
                                )
                            )
                            if global_seeai_slash_file is None:
                                self.console.print(
                                    "  [dim]- 全局 /super-dev-seeai 映射已存在（可加 --force 覆盖）[/dim]"
                                )
                            elif (
                                seeai_slash_file is None
                                or global_seeai_slash_file.resolve() != seeai_slash_file.resolve()
                            ):
                                has_global_surface = True
                                manifest_paths.append(str(global_seeai_slash_file))
                                if detail:
                                    self.console.print(
                                        f"  [green]✓[/green] 全局 /super-dev-seeai 映射: {global_seeai_slash_file}",
                                        soft_wrap=True,
                                    )
                                else:
                                    self.console.print(
                                        "  [green]✓[/green] 全局 /super-dev-seeai 映射: 已写入"
                                    )
                    else:
                        self.console.print(
                            "  [dim]- 该宿主不支持 /super-dev 或 /super-dev-seeai，已跳过 slash 映射[/dim]"
                        )
                except Exception as exc:
                    has_error = True
                    target_errors.append(f"slash: {exc}")
                    self.console.print(f"  [red]✗[/red] slash 映射失败: {exc}")

            self.console.print(f"  [cyan]主入口[/cyan]: {profile.primary_entry}")
            if profile.requires_restart_after_onboard:
                self.console.print("  [yellow]注意[/yellow]: 接入完成后需要重启宿主")
            if detail:
                for step in profile.post_onboard_steps:
                    self.console.print(f"  [dim]- {step}[/dim]")
            elif profile.post_onboard_steps:
                self.console.print(f"  [dim]- {profile.post_onboard_steps[0]}[/dim]")

            contract_failures = self._collect_onboard_contract_failures(
                integration_manager=integration_manager,
                target=target,
                skill_name=args.skill_name,
                skip_skill=bool(args.skip_skill),
                include_user_surfaces=include_user_surfaces,
            )
            if contract_failures and not args.force:
                refreshed = self._refresh_onboard_contract_surfaces(
                    integration_manager=integration_manager,
                    skill_manager=skill_manager,
                    target=target,
                    skill_name=args.skill_name,
                    skip_skill=bool(args.skip_skill),
                    include_user_surfaces=include_user_surfaces,
                )
                if refreshed:
                    self.console.print(
                        f"  [yellow]![/yellow] 检测到旧版接入文件，已自动刷新: {', '.join(refreshed)}"
                    )
                    contract_failures = self._collect_onboard_contract_failures(
                        integration_manager=integration_manager,
                        target=target,
                        skill_name=args.skill_name,
                        skip_skill=bool(args.skip_skill),
                        include_user_surfaces=include_user_surfaces,
                    )
            auto_repair_actions = self._auto_repair_onboard_target(
                project_dir=project_dir,
                target=target,
                skill_name=args.skill_name,
                check_integrate=not args.skip_integrate,
                check_skill=not args.skip_skill,
                check_slash=not args.skip_slash,
                include_user_surfaces=include_user_surfaces,
            )
            if auto_repair_actions:
                action_text = ", ".join(f"{k}={v}" for k, v in auto_repair_actions.items())
                self.console.print(
                    f"  [yellow]![/yellow] 检测到安装残留，已自动修复: {action_text}"
                )
                contract_failures = self._collect_onboard_contract_failures(
                    integration_manager=integration_manager,
                    target=target,
                    skill_name=args.skill_name,
                    skip_skill=bool(args.skip_skill),
                    include_user_surfaces=include_user_surfaces,
                )
            if contract_failures:
                has_error = True
                target_errors.extend(contract_failures)
                self.console.print("  [red]✗[/red] 宿主契约校验失败:")
                for failure in contract_failures[:6]:
                    self.console.print(f"  [dim]- {failure}[/dim]")
            else:
                self.console.print("  [green]✓[/green] 宿主契约校验通过")
                if not manifest_paths:
                    managed_surfaces = integration_manager.collect_managed_surface_paths(
                        target=target,
                        skill_name=args.skill_name,
                        include_user_surfaces=include_user_surfaces,
                    )
                    for surface_path in managed_surfaces.values():
                        if surface_path.exists():
                            manifest_paths.append(str(surface_path))
                            if str(surface_path).startswith(str(Path.home())):
                                has_global_surface = True
                            else:
                                has_project_surface = True
                if target == "claude-code" and any(
                    path.endswith(".claude/settings.local.json")
                    or path.endswith(".claude/settings.json")
                    for path in manifest_paths
                ):
                    has_runtime_surface = True
                try:
                    record_install_manifest(
                        project_dir,
                        host=target,
                        family=integration_manager.host_family(target),
                        scopes={
                            "project": has_project_surface,
                            "global": has_global_surface,
                            "runtime": has_runtime_surface,
                        },
                        paths=manifest_paths,
                    )
                except Exception:
                    pass
            target_results.append(
                {
                    "target": target,
                    "manifest_paths": sorted(set(manifest_paths)),
                    "contract_failures": contract_failures,
                    "auto_repair_actions": auto_repair_actions,
                    "errors": target_errors,
                }
            )

        self.console.print("")
        if args.dry_run:
            self.console.print(
                Panel(
                    "[bold cyan]Dry Run 完成[/bold cyan]\n\n"
                    "  以上为预览，未实际写入任何文件\n"
                    "  去掉 --dry-run 参数执行实际安装",
                    border_style="cyan",
                    expand=True,
                    padding=(1, 2),
                )
            )
            return 0
        smoke_report_paths = self._write_onboard_smoke_report(
            project_dir=project_dir,
            integration_manager=integration_manager,
            include_user_surfaces=include_user_surfaces,
            target_results=target_results,
            status="partial" if has_error else "ok",
        )
        setattr(args, "_smoke_report_paths", smoke_report_paths)
        if has_error:
            self.console.print(
                Panel(
                    "[bold red]Onboard 完成（部分失败）[/bold red]\n\n"
                    "  先不要继续开发，也先不要回宿主里试错。\n"
                    "  先在终端运行 [cyan]super-dev doctor --host <host> --repair --force[/cyan]\n"
                    "  需要看完整落点时再加 [cyan]--detail[/cyan]",
                    border_style="red",
                    expand=True,
                    padding=(1, 2),
                )
            )
            self.console.print(
                f"[dim]接入冒烟验证指南: {smoke_report_paths.get('markdown', '')}[/dim]"
            )
            return 1

        next_steps = self._build_onboard_next_steps(targets=targets)
        steps_text = "\n".join(f"  [green]>[/green] {line}" for line in next_steps)
        resume_lines = (
            self._build_session_resume_card_lines(project_dir=project_dir, target=targets[0])
            if targets
            else []
        )
        resume_text = ""
        if resume_lines:
            resume_text = "\n\n[bold]如果你是在继续已有流程:[/bold]\n\n" + "\n".join(
                f"  [cyan]>[/cyan] {line}" for line in resume_lines
            )
        self.console.print(
            Panel(
                f"[bold green]Onboard 完成[/bold green]\n\n"
                f"[bold]终端到此为止，真正开发回到宿主里。[/bold]\n\n"
                f"[bold]接下来这样用:[/bold]\n\n{steps_text}{resume_text}\n\n"
                f"[dim]冒烟验证指南: {smoke_report_paths.get('markdown', '')}[/dim]\n"
                "[dim]提示: 先看冒烟验证指南中的框架重点、必验场景和交付证据，"
                "再复制第一句。[/dim]\n"
                f"[dim]只有没进入 research -> 三文档 -> 等待确认，才回终端运行 doctor。[/dim]",
                border_style="green",
                expand=True,
                padding=(1, 2),
            )
        )
        self.console.print(f"[dim]接入冒烟验证指南: {smoke_report_paths.get('markdown', '')}[/dim]")
        return 0

    def _collect_onboard_contract_failures(
        self,
        *,
        integration_manager,
        target: str,
        skill_name: str,
        skip_skill: bool,
        include_user_surfaces: bool,
    ) -> list[str]:
        contract_surfaces = integration_manager.collect_managed_surface_paths(
            target=target,
            skill_name=skill_name,
            include_user_surfaces=include_user_surfaces,
        )
        surface_classification = integration_manager.managed_surface_classification(
            target=target,
            skill_name=skill_name,
        )
        contract_failures: list[str] = []
        for surface_key, surface_path in contract_surfaces.items():
            if surface_key.startswith("skill:") and skip_skill:
                continue
            if not surface_path.exists():
                continue
            try:
                content = surface_path.read_text(encoding="utf-8")
            except Exception:
                surface_meta = surface_classification.get(surface_key, {})
                if bool(surface_meta.get("required", False)):
                    contract_failures.append(str(surface_path))
                continue
            missing_markers = integration_manager.audit_surface_contract(
                target, surface_key, surface_path, content
            )
            surface_meta = surface_classification.get(surface_key, {})
            if missing_markers and bool(surface_meta.get("required", False)):
                contract_failures.append(str(surface_path))
        return contract_failures

    def _refresh_onboard_contract_surfaces(
        self,
        *,
        integration_manager,
        skill_manager,
        target: str,
        skill_name: str,
        skip_skill: bool,
        include_user_surfaces: bool,
    ) -> list[str]:
        from .integrations import IntegrationManager

        refreshed: list[str] = []
        integration_manager.setup(target=target, force=True)
        refreshed.append("integrate")
        if include_user_surfaces:
            integration_manager.setup_global_protocol(target=target, force=True)
            if integration_manager.setup_global_agent_surfaces(target=target, force=True):
                refreshed.append("user-agents")
            refreshed.append("user-surfaces")

        if integration_manager.supports_slash(target):
            integration_manager.setup_slash_command(target=target, force=True)
            refreshed.append("slash")
            if include_user_surfaces:
                integration_manager.setup_global_slash_command(target=target, force=True)
                refreshed.append("user-slash")

        if (
            not skip_skill
            and IntegrationManager.requires_skill(target)
            and skill_manager.skill_surface_available(target)
        ):
            skill_manager.install(
                source="super-dev",
                target=target,
                name=skill_name,
                force=True,
            )
            refreshed.append("skill")

        return refreshed

    def _auto_repair_onboard_target(
        self,
        *,
        project_dir: Path,
        target: str,
        skill_name: str,
        check_integrate: bool,
        check_skill: bool,
        check_slash: bool,
        include_user_surfaces: bool,
    ) -> dict[str, str]:
        report = self._collect_host_diagnostics(
            project_dir=project_dir,
            targets=[target],
            skill_name=skill_name,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
        )
        host_report = (report.get("hosts", {}) or {}).get(target, {})
        if not isinstance(host_report, dict) or bool(host_report.get("ready", False)):
            return {}

        repair_actions = self._repair_host_diagnostics(
            project_dir=project_dir,
            report=report,
            skill_name=skill_name,
            force=True,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
            include_user_surfaces=include_user_surfaces,
        )
        return repair_actions.get(target, {}) if isinstance(repair_actions, dict) else {}

    def _cmd_doctor(self, args) -> int:
        """诊断宿主接入状态"""
        from .integrations import IntegrationManager

        if not self._ensure_host_support_matrix():
            return 1

        detail = bool(getattr(args, "detail", False))

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        detected_targets: list[str] = []
        detected_meta: dict[str, list[str]] = {}
        targets: list[str]
        if self._is_manual_install_host(getattr(args, "host", None)):
            targets = [str(args.host)]
        else:
            available_targets = self._public_host_targets(integration_manager=integration_manager)
            detected_targets, detected_meta = self._detect_host_targets(
                available_targets=available_targets
            )
        if args.host:
            targets = [args.host]
        elif args.auto:
            if not detected_targets:
                if not args.json:
                    self.console.print("[yellow]未检测到可用宿主，已回退为诊断全部目标[/yellow]")
                    self.console.print(f"[dim]{self._custom_host_path_override_hint()}[/dim]")
                targets = available_targets
            else:
                targets = detected_targets
                if not args.json:
                    self.console.print(
                        f"[cyan]自动检测到 {len(targets)} 个宿主：{', '.join(self._host_label(target) for target in targets)}[/cyan]"
                    )
                    for target in targets:
                        reasons = ", ".join(
                            self._format_detection_reason(item)
                            for item in detected_meta.get(target, [])
                        )
                        if reasons:
                            self.console.print(
                                f"[dim]  - {self._host_label(target)}: {reasons}[/dim]"
                            )
        elif args.all:
            targets = available_targets
        else:
            targets = available_targets

        report = self._collect_host_diagnostics(
            project_dir=project_dir,
            targets=targets,
            skill_name=args.skill_name,
            check_integrate=not args.skip_integrate,
            check_skill=not args.skip_skill,
            check_slash=not args.skip_slash,
        )
        runtime_health = self._collect_runtime_install_health()
        compatibility = self._build_compatibility_summary(
            report=report,
            targets=targets,
            check_integrate=not args.skip_integrate,
            check_skill=not args.skip_skill,
            check_slash=not args.skip_slash,
        )
        repair_actions: dict[str, dict[str, str]] = {}
        if args.repair:
            repair_actions = self._repair_host_diagnostics(
                project_dir=project_dir,
                report=report,
                skill_name=args.skill_name,
                force=bool(args.force),
                check_integrate=not args.skip_integrate,
                check_skill=not args.skip_skill,
                check_slash=not args.skip_slash,
                include_user_surfaces=self._include_user_surfaces(args),
            )
            report = self._collect_host_diagnostics(
                project_dir=project_dir,
                targets=targets,
                skill_name=args.skill_name,
                check_integrate=not args.skip_integrate,
                check_skill=not args.skip_skill,
                check_slash=not args.skip_slash,
            )
            compatibility = self._build_compatibility_summary(
                report=report,
                targets=targets,
                check_integrate=not args.skip_integrate,
                check_skill=not args.skip_skill,
                check_slash=not args.skip_slash,
            )
            report["repair_actions"] = repair_actions
        decision_card = (
            self._build_detected_host_decision_card(
                project_dir=project_dir,
                integration_manager=integration_manager,
                detected_targets=detected_targets,
                detected_meta=detected_meta,
                preferred_targets=targets if args.host else None,
            )
            if detected_targets
            else self._build_detected_host_decision_card(
                project_dir=project_dir,
                integration_manager=integration_manager,
                detected_targets=[],
                detected_meta=detected_meta,
                preferred_targets=targets if args.host else None,
            )
        )
        workflow_context = (
            dict(decision_card.get("workflow_context", {}))
            if isinstance(decision_card.get("workflow_context", {}), dict)
            else {}
        )
        report["compatibility"] = compatibility
        report["runtime_install_health"] = runtime_health
        report["selected_targets"] = targets
        report["detected_hosts"] = detected_targets
        report["detection_details_pretty"] = self._explain_detection_details(detected_meta)
        report["workflow_context"] = workflow_context
        report["decision_card"] = decision_card
        report["primary_repair_action"] = self._build_primary_repair_action(
            report=report,
            targets=targets,
            decision_card=decision_card,
        )
        report["runtime_governance_summary"] = self._build_runtime_governance_summary(
            project_dir=project_dir,
            targets=targets,
        )
        report["compliance_governance_summary"] = self._build_compliance_governance_summary(
            project_dir=project_dir
        )

        # --fix: auto-repair common issues
        if getattr(args, "fix", False) and not bool(report.get("overall_ready", False)):
            fix_actions: list[str] = []
            claude_code_missing = False
            skill_missing = False
            for target, host_report in report.get("hosts", {}).items():
                checks = host_report.get("checks", {})
                if not checks.get("integrate", {}).get("ok", True):
                    claude_code_missing = True
                if not checks.get("skill", {}).get("ok", True):
                    skill_missing = True
            if claude_code_missing or skill_missing:
                try:
                    setup_args = argparse.Namespace(
                        host=None,
                        target=None,
                        all=True,
                        auto=False,
                        skill_name=args.skill_name,
                        skip_integrate=False,
                        skip_skill=False,
                        skip_slash=False,
                        skip_doctor=True,
                        yes=True,
                        force=True,
                        detail=False,
                    )
                    self._cmd_setup(setup_args)
                    fix_actions.append("setup (集成规则 + Skill 安装)")
                except Exception as exc:
                    fix_actions.append(f"setup 失败: {exc}")

            if fix_actions:
                self.console.print("[cyan]--fix 自动修复执行结果:[/cyan]")
                for action in fix_actions:
                    self.console.print(f"  [green]✓[/green] {action}")
                self.console.print("")
                # Re-collect diagnostics after fix
                report = self._collect_host_diagnostics(
                    project_dir=project_dir,
                    targets=targets,
                    skill_name=args.skill_name,
                    check_integrate=not args.skip_integrate,
                    check_skill=not args.skip_skill,
                    check_slash=not args.skip_slash,
                )
                runtime_health = self._collect_runtime_install_health()
                compatibility = self._build_compatibility_summary(
                    report=report,
                    targets=targets,
                    check_integrate=not args.skip_integrate,
                    check_skill=not args.skip_skill,
                    check_slash=not args.skip_slash,
                )
                report["compatibility"] = compatibility
                report["runtime_install_health"] = runtime_health

        if args.json:
            sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            return 0 if bool(report.get("overall_ready", False)) else 1

        self.console.print("[cyan]Super Dev Doctor[/cyan]")
        self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
        if isinstance(decision_card, dict) and decision_card.get("lines"):
            self.console.print(f"[cyan]{decision_card.get('title', '宿主决策')}[/cyan]")
            self.console.print(f"[dim]{decision_card.get('summary', '')}[/dim]")
            for line in decision_card.get("lines", []):
                self.console.print(f"[dim]- {line}[/dim]")
            self.console.print("")
        self.console.print(
            f"[cyan]兼容性评分: {compatibility['overall_score']:.2f}/100 "
            f"(ready {compatibility['ready_hosts']}/{compatibility['total_hosts']})[/cyan]"
        )
        runtime_governance = report.get("runtime_governance_summary", {})
        if isinstance(runtime_governance, dict) and runtime_governance.get("summary"):
            self.console.print("[yellow]运行治理提示[/yellow]")
            self.console.print(f"[dim]- {runtime_governance.get('summary')}[/dim]")
            next_actions = runtime_governance.get("next_actions", [])
            if isinstance(next_actions, list) and next_actions:
                self.console.print(f"[dim]- 建议先做: {next_actions[0]}[/dim]")
        compliance_governance = report.get("compliance_governance_summary", {})
        if isinstance(compliance_governance, dict) and compliance_governance.get("summary"):
            self.console.print("[yellow]合规治理提示[/yellow]")
            self.console.print(f"[dim]- {compliance_governance.get('summary')}[/dim]")
        if not runtime_health.get("healthy", False):
            self.console.print(
                "[yellow]运行时安装异常[/yellow]: 通常不是必须和 Python 装在同一盘，"
                "而是 `super-dev` 命令与当前 Python 不在同一环境。"
            )
            if not detail:
                self.console.print("[dim]加 --detail 可查看模块路径、残留版本与修复建议[/dim]")
        if detail:
            self.console.print(
                f"[dim]终端输出: {output_mode_label()} ({output_mode_reason()})[/dim]"
            )
            self.console.print(
                f"[cyan]流程一致性: {compatibility.get('flow_consistency_score', 0):.2f}/100 "
                f"({compatibility.get('flow_consistent_hosts', 0)}/{compatibility.get('total_hosts', 0)})[/cyan]"
            )
            certified_count = sum(
                1
                for t in targets
                if integration_manager.get_adapter_profile(t)
                .certification_label.lower()
                .startswith("certified")
            )
            compatible_count = sum(
                1
                for t in targets
                if integration_manager.get_adapter_profile(t)
                .certification_label.lower()
                .startswith("compatible")
            )
            experimental_count = len(targets) - certified_count - compatible_count
            self.console.print(
                f"[cyan]认证分布: Certified {certified_count} / Compatible {compatible_count} / Experimental {experimental_count}[/cyan]"
            )
        self.console.print("")
        if detail:
            self._print_runtime_install_health(runtime_health)
            self.console.print("")
        ready_targets = [
            target
            for target in targets
            if bool((report.get("hosts", {}).get(target) or {}).get("ready", False))
        ]
        if ready_targets:
            self.console.print("[green]终端到此为止，回宿主这样开始[/green]")
            for line in self._build_onboard_next_steps(targets=ready_targets[:3]):
                self.console.print(f"[green]>[/green] {line}")
            self.console.print("[dim]- 先看冒烟验证指南和框架重点，再复制第一句。[/dim]")
            resume_lines = self._build_session_resume_card_lines(
                project_dir=project_dir, target=ready_targets[0]
            )
            if resume_lines:
                self.console.print("[cyan]如果你是在继续已有流程[/cyan]")
                for line in resume_lines:
                    self.console.print(f"[dim]- {line}[/dim]")
            self.console.print("")
        if args.repair:
            self.console.print("[cyan]Repair 模式已执行[/cyan]")
            if repair_actions:
                for target, actions in repair_actions.items():
                    action_text = ", ".join(f"{k}={v}" for k, v in actions.items())
                    self.console.print(f"[dim]- {self._host_label(target)}: {action_text}[/dim]")
            else:
                self.console.print("[dim]- 无需修复或未执行修复动作[/dim]")
            self.console.print("")
        if not detail:
            primary_repair = report.get("primary_repair_action", {})
            if isinstance(primary_repair, dict) and primary_repair.get("command"):
                self.console.print("[cyan]主修复动作[/cyan]")
                self.console.print(f"[dim]- 宿主: {primary_repair.get('host', '-')}[/dim]")
                if primary_repair.get("reason"):
                    self.console.print(f"[dim]- 原因: {primary_repair.get('reason')}[/dim]")
                self.console.print(f"[dim]- 先执行: {primary_repair.get('command')}[/dim]")
                secondary_actions = primary_repair.get("secondary_actions", [])
                if isinstance(secondary_actions, list) and secondary_actions:
                    self.console.print("[dim]- 备选动作:[/dim]")
                    for item in secondary_actions[:2]:
                        self.console.print(f"[dim]  • {item}[/dim]")
                self.console.print("")
            self.console.print("[dim]使用 --detail 查看路径、协议、前置条件与逐项建议[/dim]")
            self.console.print("")
        # 摘要表格
        from rich.table import Table

        summary_table = Table(
            title="宿主接入状态",
            expand=True,
            show_lines=False,
            border_style="dim",
            title_style="bold cyan",
        )
        summary_table.add_column("宿主", style="bold", min_width=18)
        summary_table.add_column("状态", justify="center", min_width=8)
        summary_table.add_column("集成规则", justify="center")
        summary_table.add_column("Skill", justify="center")
        summary_table.add_column("Slash", justify="center")
        summary_table.add_column("认证", justify="center", min_width=12)
        if detail:
            summary_table.add_column("协议", style="dim")

        for target in targets:
            host = report["hosts"][target]
            protocol = integration_manager._protocol_profile(target=target)
            protocol_summary = protocol.get("summary", "") if isinstance(protocol, dict) else ""

            status = "[green]已就绪[/green]" if host["ready"] else "[red]未安装[/red]"

            integrate_ok = bool(host.get("checks", {}).get("integrate", {}).get("ok", True))
            skill_ok = bool(host.get("checks", {}).get("skill", {}).get("ok", True))
            slash_ok = bool(host.get("checks", {}).get("slash", {}).get("ok", True))

            integrate_text = "[green]已安装[/green]" if integrate_ok else "[red]未安装[/red]"
            skill_text = (
                "[green]已安装[/green]"
                if skill_ok
                else (
                    "[dim]不适用[/dim]"
                    if not IntegrationManager.requires_skill(target)
                    else "[red]未安装[/red]"
                )
            )
            slash_text = (
                "[green]已安装[/green]"
                if slash_ok
                else (
                    "[dim]不适用[/dim]"
                    if not integration_manager.supports_slash(target)
                    else "[red]未安装[/red]"
                )
            )

            profile = integration_manager.get_adapter_profile(target)
            cert_label = profile.certification_label
            if "certified" in cert_label.lower():
                cert_text = f"[bold green]{cert_label}[/bold green]"
            elif "compatible" in cert_label.lower():
                cert_text = f"[cyan]{cert_label}[/cyan]"
            else:
                cert_text = f"[yellow]{cert_label}[/yellow]"

            row = [
                self._host_label(target),
                status,
                integrate_text,
                skill_text,
                slash_text,
                cert_text,
            ]
            if detail:
                row.append(protocol_summary)
            summary_table.add_row(*row)

        self.console.print(summary_table)
        self.console.print("")

        for target in targets:
            host = report["hosts"][target]
            if detail:
                if host["ready"]:
                    self.console.print(f"[green]✓ {self._host_label(target)}[/green] 就绪")
                else:
                    self.console.print(f"[red]✗ {self._host_label(target)}[/red] [red]未安装[/red]")
                    for check_name in host.get("missing", []):
                        self.console.print(f"  [red]- 缺失: {check_name}[/red]")
                    for suggestion in host.get("suggestions", []):
                        self.console.print(f"  [dim]建议: {suggestion}[/dim]")
                self._print_host_usage_guidance(
                    integration_manager=integration_manager,
                    target=target,
                    indent="  ",
                )
            elif not host["ready"]:
                missing = ", ".join(host.get("missing", []))
                self.console.print(f"[red]✗ {self._host_label(target)}[/red] 缺失: {missing}")
                diagnosis = host.get("diagnosis", {})
                suggested_command = ""
                if isinstance(diagnosis, dict):
                    blocker_summary = str(diagnosis.get("blocker_summary", "")).strip()
                    certification_reason = str(diagnosis.get("certification_reason", "")).strip()
                    suggested_command = str(diagnosis.get("suggested_command", "")).strip()
                    if blocker_summary:
                        self.console.print(f"[dim]  原因: {blocker_summary}[/dim]")
                    if certification_reason:
                        self.console.print(f"[dim]  适配说明: {certification_reason}[/dim]")
                    if suggested_command:
                        self.console.print(f"[dim]  建议动作: {suggested_command}[/dim]")
                suggestions = host.get("suggestions", [])
                if suggestions:
                    first_suggestion = str(suggestions[0]).strip()
                    if not suggested_command or first_suggestion != suggested_command:
                        self.console.print(f"[dim]  建议: {first_suggestion}[/dim]")

        self.console.print("")
        if bool(report.get("overall_ready", False)):
            self.console.print("[green]✓ Doctor 通过：所有宿主接入完整[/green]")
            return 0
        self.console.print("[red]Doctor 未通过：请按建议修复后重试[/red]")
        return 1

    def _cmd_setup(self, args) -> int:
        """一步接入：onboard + doctor"""
        # 支持 `super-dev setup claude-code` 位置参数
        target = getattr(args, "target", None)
        if target and not getattr(args, "host", None):
            args.host = target
        if self._is_manual_install_host(getattr(args, "host", None)):
            return int(
                self._print_manual_install_host_guidance(
                    target=str(args.host), command_name="setup"
                )
            )
        setup_all = bool(args.all or (bool(args.yes) and not args.host and not args.auto))
        onboard_args = argparse.Namespace(
            host=args.host,
            all=setup_all,
            auto=bool(args.auto and not args.host and not args.all),
            skill_name=args.skill_name,
            skip_integrate=bool(args.skip_integrate),
            skip_skill=bool(args.skip_skill),
            skip_slash=bool(args.skip_slash),
            with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
            yes=bool(args.yes),
            force=bool(args.force),
            dry_run=False,
            stable_only=False,
            detail=bool(getattr(args, "detail", False)),
        )
        onboard_result = self._cmd_onboard(onboard_args)
        if onboard_result != 0:
            return onboard_result
        onboard_smoke_report_paths = getattr(onboard_args, "_smoke_report_paths", None)
        if isinstance(onboard_smoke_report_paths, dict) and onboard_smoke_report_paths:
            setattr(args, "_smoke_report_paths", onboard_smoke_report_paths)

        if args.skip_doctor:
            return 0

        selected_targets = getattr(onboard_args, "_selected_targets", None)
        if isinstance(selected_targets, list) and selected_targets:
            final_code = 0
            for target in selected_targets:
                doctor_args = argparse.Namespace(
                    host=target,
                    all=False,
                    auto=False,
                    skill_name=args.skill_name,
                    skip_integrate=bool(args.skip_integrate),
                    skip_skill=bool(args.skip_skill),
                    skip_slash=bool(args.skip_slash),
                    with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
                    json=False,
                    repair=True,
                    force=bool(args.force),
                    detail=bool(getattr(args, "detail", False)),
                )
                result = self._cmd_doctor(doctor_args)
                if result != 0:
                    final_code = result
            return final_code

        doctor_args = argparse.Namespace(
            host=args.host,
            all=setup_all,
            auto=bool(args.auto and not args.host and not args.all),
            skill_name=args.skill_name,
            skip_integrate=bool(args.skip_integrate),
            skip_skill=bool(args.skip_skill),
            skip_slash=bool(args.skip_slash),
            with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
            json=False,
            repair=True,
            force=bool(args.force),
            detail=bool(getattr(args, "detail", False)),
        )
        return int(self._cmd_doctor(doctor_args))

    def _cmd_install(self, args) -> int:
        """面向 PyPI 用户的一键安装入口"""
        self._render_install_intro(args=args)
        if self._is_manual_install_host(getattr(args, "host", None)):
            return int(
                self._print_manual_install_host_guidance(
                    target=str(args.host), command_name="install"
                )
            )
        setup_args = argparse.Namespace(
            host=args.host,
            all=bool(args.all),
            auto=bool(args.auto),
            skill_name=args.skill_name,
            skip_integrate=bool(args.skip_integrate),
            skip_skill=bool(args.no_skill),
            skip_slash=bool(args.skip_slash),
            with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
            skip_doctor=bool(args.skip_doctor),
            force=bool(args.force),
            yes=bool(args.yes),
        )
        return int(self._cmd_setup(setup_args))

    def _cmd_uninstall(self, args) -> int:
        """面向 PyPI 用户的一键卸载入口。"""
        from .integrations import IntegrationManager
        from .skills import SkillManager

        if not self._ensure_host_support_matrix():
            return 1

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        skill_manager = SkillManager(project_dir)
        dry_run = bool(getattr(args, "dry_run", False))
        available_targets = self._public_host_targets(integration_manager=integration_manager)

        if getattr(args, "host", None):
            targets = [args.host]
        elif getattr(args, "all", False):
            targets = available_targets
        elif getattr(args, "auto", False):
            detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
            targets = self._deduplicate_host_family(detected_targets)
        else:
            try:
                targets = self._resolve_onboard_targets(
                    available_targets=available_targets,
                    host=getattr(args, "host", None),
                    all_targets=bool(getattr(args, "all", False)),
                    non_interactive=bool(getattr(args, "yes", False)),
                )
            except ValueError as exc:
                self.console.print(f"[red]{exc}[/red]")
                return 1

        if not targets:
            message = "未检测到可清理的宿主，请改用 --host 指定或使用 --all。"
            if getattr(args, "json", False):
                sys.stdout.write(
                    json.dumps(
                        {
                            "status": "error",
                            "reason": "no-host-detected",
                            "message": message,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n"
                )
            else:
                self.console.print(f"[yellow]{message}[/yellow]")
            return 1

        cleaned_targets: list[dict[str, Any]] = []
        for target in targets:
            preview = self._collect_uninstall_target_preview(
                integration_manager=integration_manager,
                skill_manager=skill_manager,
                target=target,
            )
            removed_paths: list[str] = []
            removed_skills: list[str] = []
            removed_skill_paths: list[str] = []
            removed_legacy_skill_aliases: list[str] = []
            removed_legacy_skill_paths: list[str] = []
            errors: list[str] = []

            if not dry_run:
                try:
                    removed = integration_manager.remove(target=target)
                    removed_paths.extend(str(item) for item in removed)
                except Exception as exc:
                    errors.append(f"surface cleanup failed: {exc}")

                if skill_manager.skill_surface_available(target):
                    for skill_name in skill_manager.managed_builtin_skill_names(target):
                        existing_paths = self._stringify_existing_paths(
                            skill_manager.managed_skill_cleanup_paths(target, skill_name)
                        )
                        try:
                            skill_manager.uninstall(skill_name, target)
                            removed_skills.append(skill_name)
                            removed_skill_paths.extend(existing_paths)
                        except FileNotFoundError:
                            continue
                        except Exception as exc:
                            errors.append(f"skill {skill_name} cleanup failed: {exc}")
                    legacy_paths = self._stringify_existing_paths(
                        skill_manager.legacy_skill_cleanup_paths(target)
                    )
                    try:
                        removed_legacy_skill_aliases.extend(
                            skill_manager.cleanup_legacy_skill_aliases(target)
                        )
                        if removed_legacy_skill_aliases:
                            removed_legacy_skill_paths.extend(legacy_paths)
                    except Exception as exc:
                        errors.append(f"legacy skill cleanup failed: {exc}")

            target_payload = {
                "target": target,
                "planned_surface_paths": preview["planned_surface_paths"],
                "planned_skill_names": preview["planned_skill_names"],
                "planned_skill_paths": preview["planned_skill_paths"],
                "planned_legacy_skill_aliases": preview["planned_legacy_skill_aliases"],
                "planned_legacy_skill_paths": preview["planned_legacy_skill_paths"],
                "missing_surface_paths": preview["missing_surface_paths"],
                "removed_paths": sorted(set(removed_paths)),
                "removed_skills": removed_skills,
                "removed_skill_paths": sorted(set(removed_skill_paths)),
                "removed_legacy_skill_aliases": removed_legacy_skill_aliases,
                "removed_legacy_skill_paths": sorted(set(removed_legacy_skill_paths)),
                "errors": errors,
            }
            cleaned_targets.append(target_payload)

        removed_path_count = sum(
            len(item["planned_surface_paths"] if dry_run else item["removed_paths"])
            for item in cleaned_targets
        )
        removed_skill_count = sum(
            len(item["planned_skill_names"] if dry_run else item["removed_skills"])
            for item in cleaned_targets
        )
        legacy_skill_count = sum(
            len(
                item["planned_legacy_skill_aliases"]
                if dry_run
                else item["removed_legacy_skill_aliases"]
            )
            for item in cleaned_targets
        )
        error_count = sum(len(item["errors"]) for item in cleaned_targets)
        payload = {
            "status": "preview" if dry_run else ("ok" if error_count == 0 else "partial"),
            "dry_run": dry_run,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "targets": cleaned_targets,
            "removed_path_count": removed_path_count,
            "removed_skill_count": removed_skill_count,
            "removed_legacy_skill_count": legacy_skill_count,
            "error_count": error_count,
            "summary": (
                (
                    f"预演 {len(cleaned_targets)} 个宿主，"
                    f"将清理 {removed_path_count} 个接入面路径，"
                    f"{removed_skill_count} 个技能目录，"
                    f"{legacy_skill_count} 个旧技能别名"
                )
                if dry_run
                else (
                    f"已处理 {len(cleaned_targets)} 个宿主，"
                    f"清理 {removed_path_count} 个接入面路径，"
                    f"{removed_skill_count} 个技能目录，"
                    f"{legacy_skill_count} 个旧技能别名"
                )
            ),
        }
        report_files = self._write_cleanup_report(project_dir=project_dir, payload=payload)
        payload["report_files"] = report_files
        payload["report_path"] = report_files["json"]
        Path(report_files["json"]).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if getattr(args, "json", False):
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0 if error_count == 0 else 1

        style = "green" if error_count == 0 else "yellow"
        self.console.print(f"[{style}]✓ {payload['summary']}[/{style}]")
        for item in cleaned_targets:
            self.console.print(f"  - {self._host_label(item['target'])}")
            surface_count = len(item["planned_surface_paths"] if dry_run else item["removed_paths"])
            skill_names = item["planned_skill_names"] if dry_run else item["removed_skills"]
            legacy_names = (
                item["planned_legacy_skill_aliases"]
                if dry_run
                else item["removed_legacy_skill_aliases"]
            )
            if surface_count:
                self.console.print(
                    f"    {'将清理' if dry_run else '清理'}接入面: {surface_count} 项"
                )
            if skill_names:
                self.console.print(
                    f"    {'将清理' if dry_run else '清理'} Skill: {', '.join(skill_names)}"
                )
            if legacy_names:
                self.console.print(
                    f"    {'将清理' if dry_run else '清理'}旧技能别名: {', '.join(legacy_names)}"
                )
            if item["errors"]:
                for error in item["errors"]:
                    self.console.print(f"    [yellow]⚠ {error}[/yellow]")
        self.console.print(f"[dim]Cleanup report: {report_files['json']}[/dim]")
        self.console.print(f"[dim]Cleanup summary: {report_files['markdown']}[/dim]")
        self.console.print("")
        if dry_run:
            self.console.print(
                Panel(
                    "[bold cyan]卸载预演完成[/bold cyan]\n\n"
                    "  这次只是预演，不会删除任何接入面。\n"
                    "  先看 cleanup report，再决定是否真的清理。",
                    border_style="cyan",
                    expand=True,
                    padding=(1, 2),
                )
            )
        elif error_count == 0:
            self.console.print(
                Panel(
                    "[bold green]卸载完成[/bold green]\n\n"
                    "  当前项目里的 Super Dev 接入面已经清理完成。\n"
                    "  如果之后还要继续用，回到项目目录重新运行 `super-dev` 即可。",
                    border_style="green",
                    expand=True,
                    padding=(1, 2),
                )
            )
        else:
            self.console.print(
                Panel(
                    "[bold yellow]卸载完成（部分异常）[/bold yellow]\n\n"
                    "  大部分接入面已处理，但还有少量清理异常。\n"
                    "  先看 cleanup report；如果要继续排查，再运行 `super-dev uninstall --dry-run` 对照核查。",
                    border_style="yellow",
                    expand=True,
                    padding=(1, 2),
                )
            )
        return 0 if error_count == 0 else 1

    def _cmd_start(self, args) -> int:
        """面向非技术用户的起步入口：自动选宿主、接入并输出最短试用路径。"""
        from .integrations import IntegrationManager

        if not self._ensure_host_support_matrix():
            return 1
        if self._is_manual_install_host(getattr(args, "host", None)):
            return int(
                self._print_manual_install_host_guidance(
                    target=str(args.host), command_name="start"
                )
            )

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        available_targets = self._public_host_targets(integration_manager=integration_manager)
        detected_targets, detected_meta = self._detect_host_targets(
            available_targets=available_targets
        )
        detected_targets = self._deduplicate_host_family(detected_targets)

        target = args.host
        selection_reason = "manual"
        if not target:
            if detected_targets:
                target = self._select_best_start_host(
                    integration_manager=integration_manager,
                    targets=detected_targets,
                )
                selection_reason = "auto-detected"
            else:
                decision_card = self._build_no_host_decision_card(
                    integration_manager=integration_manager
                )
                payload = {
                    "status": "error",
                    "reason": "no-host-detected",
                    "message": "未检测到可用宿主，请先安装受支持宿主后重试。",
                    "path_override_hint": decision_card["path_override_hint"],
                    "recommended_hosts": decision_card["recommended_hosts"],
                    "decision_card": decision_card,
                }
                if args.json:
                    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
                else:
                    self.console.print("[red]未检测到可用宿主[/red]")
                    self.console.print(f"[dim]{decision_card['summary']}[/dim]")
                    for line in decision_card["lines"]:
                        self.console.print(f"[dim]- {line}[/dim]")
                    self.console.print("[cyan]优先建议安装这些宿主:[/cyan]")
                    for host in decision_card["recommended_hosts"]:
                        self.console.print(f"  - {host['name']} [{host['certification_label']}]")
                return 1

        usage = self._build_host_usage_profile(
            integration_manager=integration_manager,
            target=target,
        )
        framework_playbook = load_framework_playbook_summary(project_dir)
        onboard_smoke_report_paths: dict[str, Any] = {}

        onboard_performed = False
        if not bool(args.skip_onboard):
            setup_args = argparse.Namespace(
                host=target,
                all=False,
                auto=False,
                skill_name="super-dev",
                skip_integrate=False,
                skip_skill=False,
                skip_slash=False,
                with_user_surfaces=bool(getattr(args, "with_user_surfaces", False)),
                skip_doctor=False,
                yes=True,
                force=bool(args.force),
            )
            if args.json:
                with contextlib.redirect_stdout(io.StringIO()):
                    onboard_result = self._cmd_setup(setup_args)
            else:
                onboard_result = self._cmd_setup(setup_args)
            onboard_performed = True
            if onboard_result != 0:
                return onboard_result
            if isinstance(getattr(setup_args, "_smoke_report_paths", {}), dict):
                onboard_smoke_report_paths = dict(getattr(setup_args, "_smoke_report_paths", {}))

        profile_saved = False
        profile_save_error = ""
        if not bool(args.no_save_profile):
            try:
                ConfigManager(project_dir).update(
                    host_profile_targets=[target],
                    host_profile_enforce_selected=True,
                )
                profile_saved = True
            except Exception as exc:
                profile_save_error = str(exc)

        session_hint = self._build_workflow_session_hint(project_dir=project_dir, target=target)
        session_resume_card = self._build_session_resume_card(
            project_dir=project_dir, target=target
        )
        decision_card = self._build_detected_host_decision_card(
            project_dir=project_dir,
            integration_manager=integration_manager,
            detected_targets=detected_targets,
            detected_meta=detected_meta,
            preferred_targets=[target],
        )
        quick_start = self._build_host_quick_start_text(
            host_profile=usage,
            host_id=target,
            host_name=self._host_label(target),
            idea=args.idea,
            session_hint=session_hint,
            framework_playbook=framework_playbook,
        )
        payload = {
            "status": "success",
            "project_dir": str(project_dir),
            "selected_host": target,
            "selected_host_name": self._host_label(target),
            "selection_reason": selection_reason,
            "detected_hosts": detected_targets,
            "detection_details": detected_meta,
            "detection_details_pretty": self._explain_detection_details(detected_meta),
            "onboard_performed": onboard_performed,
            "profile_saved": profile_saved,
            "profile_save_error": profile_save_error,
            "usage_profile": usage,
            "selected_host_experience": (
                dict(usage.get("experience_profile", {}))
                if isinstance(usage.get("experience_profile", {}), dict)
                else {}
            ),
            "selected_host_post_onboard_self_check": (
                list(decision_card.get("selected_host_post_onboard_self_check", []))
                if isinstance(
                    decision_card.get("selected_host_post_onboard_self_check", []),
                    list,
                )
                else []
            ),
            "selected_host_start_playbook": (
                list(decision_card.get("selected_host_start_playbook", []))
                if isinstance(decision_card.get("selected_host_start_playbook", []), list)
                else []
            ),
            "selected_host_standard_flow_first_prompt": str(
                decision_card.get("selected_host_standard_flow_first_prompt", "")
            ).strip(),
            "selected_host_competition_flow_first_prompt": str(
                decision_card.get("selected_host_competition_flow_first_prompt", "")
            ).strip(),
            "selected_host_resume_guidance": (
                list(decision_card.get("selected_host_resume_guidance", []))
                if isinstance(decision_card.get("selected_host_resume_guidance", []), list)
                else []
            ),
            "selected_host_injection_closure": (
                dict(decision_card.get("selected_host_injection_closure", {}))
                if isinstance(decision_card.get("selected_host_injection_closure", {}), dict)
                else {}
            ),
            "selected_host_ready_for_standard_flow": bool(
                decision_card.get("selected_host_ready_for_standard_flow", False)
            ),
            "selected_host_ready_for_competition_flow": bool(
                decision_card.get("selected_host_ready_for_competition_flow", False)
            ),
            "selected_host_standard_flow_label": str(
                decision_card.get("selected_host_standard_flow_label", "")
            ).strip(),
            "selected_host_competition_flow_label": str(
                decision_card.get("selected_host_competition_flow_label", "")
            ).strip(),
            "selected_host_official_workflow_checks": (
                list(decision_card.get("selected_host_official_workflow_checks", []))
                if isinstance(
                    decision_card.get("selected_host_official_workflow_checks", []),
                    list,
                )
                else []
            ),
            "selected_host_repair_playbook": str(
                decision_card.get("selected_host_repair_playbook", "")
            ).strip(),
            "selected_host_adaptation": (
                dict(usage.get("adaptation_contract", {}))
                if isinstance(usage.get("adaptation_contract", {}), dict)
                else {}
            ),
            "selected_host_framework_playbook": framework_playbook,
            "session_mode": session_hint.get("session_mode", "fresh_start"),
            "continue_prompt": session_hint.get("continue_prompt", ""),
            "recommended_workflow_command": session_hint.get("recommended_workflow_command", ""),
            "workflow_reason": session_hint.get("workflow_reason", ""),
            "workflow_context": (
                dict(decision_card.get("workflow_context", {}))
                if isinstance(decision_card.get("workflow_context", {}), dict)
                else {}
            ),
            "session_resume_card": session_resume_card,
            "decision_card": decision_card,
            "runtime_install_health": self._collect_runtime_install_health(),
            "recommended_trigger": self._build_host_trigger_example(target=target, idea=args.idea),
            "quick_start": quick_start,
            "onboard_smoke_report_paths": onboard_smoke_report_paths,
        }

        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        profile = integration_manager.get_adapter_profile(target)
        self.console.print("[cyan]Super Dev Start[/cyan]")
        self.console.print(f"[cyan]已选择宿主[/cyan]: {self._host_label(target)}")
        self.console.print(
            f"[cyan]认证等级[/cyan]: {profile.certification_label} ({profile.certification_level})"
        )
        experience = payload.get("selected_host_experience", {})
        if isinstance(experience, dict) and experience:
            self.console.print(
                f"[cyan]宿主画像[/cyan]: {experience.get('label', '-')} / "
                f"{experience.get('best_for', '-')}"
            )
            native_resume = experience.get("native_resume", [])
            if isinstance(native_resume, list) and native_resume:
                self.console.print(
                    f"[dim]推荐恢复: {' / '.join(str(item) for item in native_resume[:2])}[/dim]"
                )
        if isinstance(framework_playbook, dict) and framework_playbook:
            self.console.print(
                f"[cyan]框架教练焦点[/cyan]: {framework_playbook.get('framework', '-')}"
            )
            validation_surfaces = framework_playbook.get("validation_surfaces", [])
            if isinstance(validation_surfaces, list) and validation_surfaces:
                self.console.print(
                    "[dim]必验场景: "
                    + "；".join(str(item) for item in validation_surfaces[:4])
                    + "[/dim]"
                )
        standard_prompt = str(payload.get("selected_host_standard_flow_first_prompt", "")).strip()
        competition_prompt = str(
            payload.get("selected_host_competition_flow_first_prompt", "")
        ).strip()
        if standard_prompt:
            self.console.print(f"[cyan]标准流第一句[/cyan]: {standard_prompt}")
        if competition_prompt:
            self.console.print(f"[cyan]比赛流第一句[/cyan]: {competition_prompt}")
        if selection_reason == "auto-detected":
            reasons = ", ".join(detected_meta.get(target, []))
            if reasons:
                self.console.print(f"[dim]自动选择依据: {reasons}[/dim]")
        if decision_card.get("scenario") == "multi-host-detected":
            self.console.print(f"[cyan]{decision_card.get('title', '已检测到宿主')}[/cyan]")
            self.console.print(f"[dim]{decision_card.get('summary', '')}[/dim]")
            for line in decision_card.get("lines", []):
                self.console.print(f"[dim]- {line}[/dim]")
        self.console.print(f"[dim]{profile.certification_reason}[/dim]")
        if profile_saved:
            self.console.print("[green]✓[/green] 已写入宿主画像到 super-dev.yaml")
        elif profile_save_error:
            self.console.print(f"[yellow]宿主画像写入失败: {profile_save_error}[/yellow]")
        self.console.print("")
        onboard_report_paths = payload.get("onboard_smoke_report_paths", {})
        if isinstance(onboard_report_paths, dict) and onboard_report_paths.get("markdown"):
            self.console.print(f"[dim]接入冒烟验证指南: {onboard_report_paths['markdown']}[/dim]")
        self.console.print(quick_start)
        return 0

    def _cmd_detect(self, args) -> int:
        """宿主探测 + 接入兼容性评分"""
        from .integrations import IntegrationManager

        if not self._ensure_host_support_matrix():
            return 1

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        if self._is_manual_install_host(getattr(args, "host", None)):
            targets = [str(args.host)]
            available_targets = targets
        else:
            available_targets = self._public_host_targets(integration_manager=integration_manager)
        detected_targets, detected_meta = self._detect_host_targets(
            available_targets=available_targets
        )

        if args.host:
            targets = [args.host]
        elif args.all:
            targets = available_targets
        else:
            targets = detected_targets

        report = self._collect_host_diagnostics(
            project_dir=project_dir,
            targets=targets,
            skill_name=args.skill_name,
            check_integrate=not args.skip_integrate,
            check_skill=not args.skip_skill,
            check_slash=not args.skip_slash,
        )
        compatibility = self._build_compatibility_summary(
            report=report,
            targets=targets,
            check_integrate=not args.skip_integrate,
            check_skill=not args.skip_skill,
            check_slash=not args.skip_slash,
        )

        payload: dict[str, Any] = {
            "project_dir": str(project_dir),
            "detected_hosts": detected_targets,
            "detection_details": detected_meta,
            "detection_details_pretty": self._explain_detection_details(detected_meta),
            "selected_targets": targets,
            "decision_card": self._build_detected_host_decision_card(
                project_dir=project_dir,
                integration_manager=integration_manager,
                detected_targets=detected_targets,
                detected_meta=detected_meta,
                preferred_targets=targets if args.host else None,
            ),
            "report": report,
            "compatibility": compatibility,
            "session_resume_cards": {
                target: self._build_session_resume_card(project_dir=project_dir, target=target)
                for target in targets
            },
            "usage_profiles": {
                target: self._build_host_usage_profile(
                    integration_manager=integration_manager,
                    target=target,
                )
                for target in targets
            },
        }
        payload["adaptation_contracts"] = {
            target: dict(usage.get("adaptation_contract", {}))
            for target, usage in payload["usage_profiles"].items()
            if isinstance(usage, dict) and isinstance(usage.get("adaptation_contract", {}), dict)
        }
        payload["experience_profiles"] = {
            target: dict(usage.get("experience_profile", {}))
            for target, usage in payload["usage_profiles"].items()
            if isinstance(usage, dict) and isinstance(usage.get("experience_profile", {}), dict)
        }
        selected_host = str(payload["decision_card"].get("selected_host", "")).strip()
        payload["selected_host_adaptation"] = (
            dict(payload["adaptation_contracts"].get(selected_host, {}))
            if selected_host in payload["adaptation_contracts"]
            else {}
        )
        payload["selected_host_experience"] = (
            dict(payload["experience_profiles"].get(selected_host, {}))
            if selected_host in payload["experience_profiles"]
            else {}
        )
        payload["selected_host_post_onboard_self_check"] = (
            list(payload["decision_card"].get("selected_host_post_onboard_self_check", []))
            if isinstance(
                payload["decision_card"].get("selected_host_post_onboard_self_check", []),
                list,
            )
            else []
        )
        payload["selected_host_start_playbook"] = (
            list(payload["decision_card"].get("selected_host_start_playbook", []))
            if isinstance(payload["decision_card"].get("selected_host_start_playbook", []), list)
            else []
        )
        payload["selected_host_standard_flow_first_prompt"] = str(
            payload["decision_card"].get("selected_host_standard_flow_first_prompt", "")
        ).strip()
        payload["selected_host_competition_flow_first_prompt"] = str(
            payload["decision_card"].get("selected_host_competition_flow_first_prompt", "")
        ).strip()
        payload["selected_host_resume_guidance"] = (
            list(payload["decision_card"].get("selected_host_resume_guidance", []))
            if isinstance(payload["decision_card"].get("selected_host_resume_guidance", []), list)
            else []
        )
        payload["selected_host_injection_closure"] = (
            dict(payload["decision_card"].get("selected_host_injection_closure", {}))
            if isinstance(payload["decision_card"].get("selected_host_injection_closure", {}), dict)
            else {}
        )
        payload["selected_host_ready_for_standard_flow"] = bool(
            payload["decision_card"].get("selected_host_ready_for_standard_flow", False)
        )
        payload["selected_host_ready_for_competition_flow"] = bool(
            payload["decision_card"].get("selected_host_ready_for_competition_flow", False)
        )
        payload["selected_host_standard_flow_label"] = str(
            payload["decision_card"].get("selected_host_standard_flow_label", "")
        ).strip()
        payload["selected_host_competition_flow_label"] = str(
            payload["decision_card"].get("selected_host_competition_flow_label", "")
        ).strip()
        payload["selected_host_official_workflow_checks"] = (
            list(payload["decision_card"].get("selected_host_official_workflow_checks", []))
            if isinstance(
                payload["decision_card"].get("selected_host_official_workflow_checks", []),
                list,
            )
            else []
        )
        payload["selected_host_repair_playbook"] = str(
            payload["decision_card"].get("selected_host_repair_playbook", "")
        ).strip()
        payload["workflow_context"] = (
            dict(payload["decision_card"].get("workflow_context", {}))
            if isinstance(payload["decision_card"].get("workflow_context", {}), dict)
            else {}
        )
        if not bool(args.no_save):
            report_files = self._write_host_compatibility_report(
                project_dir=project_dir, payload=payload
            )
            payload["report_files"] = {name: str(path) for name, path in report_files.items()}

        if bool(args.save_profile):
            try:
                config_manager = ConfigManager(project_dir)
                config_manager.update(
                    host_profile_targets=targets,
                    host_profile_enforce_selected=True,
                )
                payload["host_profile_updated"] = True
            except Exception as exc:
                payload["host_profile_updated"] = False
                payload["host_profile_update_error"] = str(exc)

        if args.json:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0

        self.console.print("[cyan]Super Dev Host Detect[/cyan]")
        self.console.print(f"[dim]项目目录: {project_dir}[/dim]")
        if detected_targets:
            self.console.print(
                f"[cyan]自动检测到 {len(detected_targets)} 个宿主：{', '.join(self._host_label(target) for target in detected_targets)}[/cyan]"
            )
            for target in detected_targets:
                reasons = ", ".join(
                    self._format_detection_reason(item) for item in detected_meta.get(target, [])
                )
                if reasons:
                    self.console.print(f"[dim]  - {self._host_label(target)}: {reasons}[/dim]")
        else:
            self.console.print("[yellow]未检测到宿主（可用 --all 查看全部兼容评分）[/yellow]")
        decision_card = payload.get("decision_card", {})
        if isinstance(decision_card, dict) and decision_card.get("lines"):
            self.console.print("")
            self.console.print(f"[cyan]{decision_card.get('title', '宿主决策')}[/cyan]")
            self.console.print(f"[dim]{decision_card.get('summary', '')}[/dim]")
            for line in decision_card.get("lines", []):
                self.console.print(f"[dim]- {line}[/dim]")

        self.console.print("")
        self.console.print(
            f"[cyan]兼容性评分: {compatibility['overall_score']:.2f}/100 "
            f"(ready {compatibility['ready_hosts']}/{compatibility['total_hosts']})[/cyan]"
        )
        self.console.print(
            f"[cyan]流程一致性: {compatibility.get('flow_consistency_score', 0):.2f}/100 "
            f"({compatibility.get('flow_consistent_hosts', 0)}/{compatibility.get('total_hosts', 0)})[/cyan]"
        )
        for target in targets:
            host_compat = compatibility["hosts"].get(target, {})
            score = host_compat.get("score", 0.0)
            ready = bool(host_compat.get("ready", False))
            badge = "[green]ready[/green]" if ready else "[yellow]not-ready[/yellow]"
            self.console.print(f"  - {self._host_label(target)}: {score:.2f}/100 {badge}")
        if targets:
            guidance_target = self._select_best_start_host(
                integration_manager=integration_manager,
                targets=targets,
            )
            resume_card = self._build_session_resume_card(
                project_dir=project_dir, target=guidance_target
            )
            if bool(resume_card.get("enabled", False)):
                self.console.print("")
                self.console.print("[cyan]如果你是在继续已有流程[/cyan]")
                for line in resume_card.get("lines", []):
                    self.console.print(f"[dim]- {line}[/dim]")
            self._print_host_usage_guidance(
                integration_manager=integration_manager,
                target=guidance_target,
                indent="    ",
            )
        if not bool(args.no_save):
            saved_report_files = payload.get("report_files", {})
            if isinstance(saved_report_files, dict):
                json_file = saved_report_files.get("json")
                md_file = saved_report_files.get("markdown")
                if isinstance(json_file, str) and isinstance(md_file, str):
                    self.console.print(f"[dim]报告: {md_file}[/dim]")
                    self.console.print(f"[dim]数据: {json_file}[/dim]")
        if bool(args.save_profile):
            if bool(payload.get("host_profile_updated", False)):
                self.console.print(
                    "[green]✓[/green] 已更新宿主画像: host_profile_targets + host_profile_enforce_selected"
                )
            else:
                err = payload.get("host_profile_update_error", "")
                self.console.print(f"[yellow]宿主画像更新失败: {err}[/yellow]")

        # --auto: 检测完成后自动安装 skill + rules + hooks 到检测到的主要宿主
        if getattr(args, "auto", False) and detected_targets:
            auto_install_targets = [t for t in detected_targets if t in PRIMARY_HOST_TOOL_IDS]
            if not auto_install_targets:
                auto_install_targets = detected_targets[:3]
            self.console.print("")
            self.console.print("[cyan]自动安装到检测到的宿主...[/cyan]")
            for target in auto_install_targets:
                try:
                    written = integration_manager.setup(target=target, force=True)
                    if written:
                        self.console.print(
                            f"  [green]✓[/green] {self._host_label(target)}: "
                            f"已写入 {len(written)} 个文件"
                        )
                except Exception as exc:
                    self.console.print(f"  [yellow]⚠[/yellow] {self._host_label(target)}: {exc}")
            # 自动安装 enforcement hooks (仅 claude-code)
            try:
                from .enforcement import HostHooksConfigurator

                configurator = HostHooksConfigurator(project_dir)
                for target in auto_install_targets:
                    if target in ("claude-code",):
                        configurator.install_hooks(target)
                        self.console.print(
                            f"  [green]✓[/green] {self._host_label(target)}: "
                            "enforcement hooks 已安装"
                        )
            except Exception:
                pass  # enforcement 模块可选
            self.console.print("[green]自动安装完成[/green]")

        return 0

    def _cmd_clean(self, args) -> int:
        """清理历史产物文件"""
        project_dir = Path.cwd()
        output_dir = project_dir / get_config_manager(project_dir).config.output_dir

        if not output_dir.exists():
            self.console.print("[yellow]output/ 目录不存在，无需清理[/yellow]")
            return 0

        # 收集所有产物文件（按修改时间排序）
        artifact_extensions = {".md", ".json", ".html", ".css", ".js", ".tar.gz", ".zip"}
        all_files: list[Path] = []
        for f in output_dir.rglob("*"):
            if f.is_file() and (f.suffix in artifact_extensions or ".tar" in f.name):
                all_files.append(f)

        if not all_files:
            self.console.print("[green]output/ 目录已是干净状态[/green]")
            return 0

        all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        if args.all:
            files_to_delete = all_files
        else:
            # 按项目名分组，每组保留最近 keep 个文件
            import re as _re
            from collections import defaultdict

            # 已知的产物后缀模式
            artifact_suffixes = [
                "-prd",
                "-architecture",
                "-uiux",
                "-research",
                "-execution-plan",
                "-frontend-blueprint",
                "-redteam",
                "-quality-gate",
                "-code-review",
                "-ai-prompt",
                "-release-readiness",
                "-pipeline-metrics",
                "-ui-review",
                "-proof-pack",
                "-contract-report",
                "-knowledge-bundle",
                "-frontend-runtime",
                "-repo-map",
                "-dependency-graph",
                "-feature-checklist",
                "-resume-audit",
                "-rehearsal-report",
            ]

            groups: dict[str, list[Path]] = defaultdict(list)
            for f in all_files:
                name = f.stem
                matched = False
                for suffix in artifact_suffixes:
                    if name.endswith(suffix):
                        name = name[: -len(suffix)]
                        matched = True
                        break
                if not matched:
                    # 尝试正则提取（处理未知后缀）
                    m = _re.match(r"^(.+?)(?:-[a-z]+-[a-z]+)$", name)
                    if m:
                        name = m.group(1)
                groups[name].append(f)

            files_to_delete = []
            for _group_name, group_files in groups.items():
                group_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                keep_count = args.keep
                if len(group_files) > keep_count:
                    files_to_delete.extend(group_files[keep_count:])

        if not files_to_delete:
            self.console.print(f"[green]无需清理（当前保留最近 {args.keep} 次运行的产物）[/green]")
            return 0

        self.console.print(f"[cyan]将清理 {len(files_to_delete)} 个文件：[/cyan]")
        for f in files_to_delete[:20]:
            try:
                rel: Path | str = f.relative_to(project_dir)
            except ValueError:
                rel = f.name
            self.console.print(f"  [dim]{rel}[/dim]")
        if len(files_to_delete) > 20:
            self.console.print(f"  [dim]... 及其他 {len(files_to_delete) - 20} 个文件[/dim]")

        if args.dry_run:
            self.console.print("[yellow]当前是预演（--dry-run），未实际删除[/yellow]")
            return 0

        deleted = 0
        for f in files_to_delete:
            try:
                f.unlink()
                deleted += 1
            except OSError:
                pass

        # 清理空目录
        for d in sorted(output_dir.rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                try:
                    d.rmdir()
                except OSError:
                    pass

        self.console.print(f"[green]已清理 {deleted} 个文件[/green]")
        return 0

    def _cmd_update(self, args) -> int:
        from .update_runtime import run_update

        return run_update(args, self.console)
