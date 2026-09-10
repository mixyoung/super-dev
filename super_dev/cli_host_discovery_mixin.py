"""Host discovery, diagnostics and onboarding preparation."""

import glob
import importlib.metadata
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from rich.console import Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from . import __version__
from .catalogs import (
    HOST_COMMAND_CANDIDATES,
    host_detection_path_candidates,
    host_display_name,
    host_path_override_guide,
    host_runtime_validation_overrides,
)
from .compliance_governance import collect_compliance_governance_signal
from .config import ProjectConfig
from .host_adapters import render_manual_install_guidance
from .host_diagnostics import build_host_compatibility_summary, collect_host_diagnostics
from .host_entry_decisions import (
    build_host_start_guidance,
)
from .host_experience_profile import (
    build_host_competition_first_prompt,
    build_host_official_pass_criteria,
    build_host_official_workflow_checks,
    build_host_post_onboard_self_check,
    build_host_resume_guidance,
    build_host_standard_first_prompt,
    build_host_start_playbook,
)
from .host_registry import HostInstallMode, get_install_mode
from .host_runtime_governance import collect_layered_runtime_governance_gap
from .terminal import normalize_terminal_text
from .workflow_state import (
    build_host_entry_prompts,
    load_framework_playbook_summary,
)


class CliHostDiscoveryMixin:
    @staticmethod
    def _cleanup_report_paths(project_dir: Path) -> dict[str, Path]:
        report_dir = project_dir / "output" / "maintenance"
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        base = report_dir / f"host-cleanup-{stamp}"
        return {
            "json": base.with_suffix(".json"),
            "markdown": base.with_suffix(".md"),
        }

    @staticmethod
    def _onboard_smoke_report_paths(project_dir: Path) -> dict[str, Path]:
        report_dir = project_dir / "output" / "maintenance"
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        base = report_dir / f"host-onboard-smoke-{stamp}"
        return {
            "json": base.with_suffix(".json"),
            "markdown": base.with_suffix(".md"),
        }

    @staticmethod
    def _stringify_existing_paths(paths: list[Path]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for path in paths:
            key = str(path)
            if key in seen or not path.exists():
                continue
            seen.add(key)
            deduped.append(key)
        return sorted(deduped)

    def _collect_uninstall_target_preview(
        self,
        *,
        integration_manager,
        skill_manager,
        target: str,
    ) -> dict[str, Any]:
        managed_surfaces = integration_manager.collect_managed_surface_paths(target=target)
        planned_surface_paths = self._stringify_existing_paths(list(managed_surfaces.values()))
        missing_surface_paths = sorted(
            {str(path) for path in managed_surfaces.values() if not path.exists()}
        )

        planned_skill_names: list[str] = []
        planned_skill_paths: list[str] = []
        planned_legacy_skill_aliases: list[str] = []
        planned_legacy_skill_paths: list[str] = []
        if skill_manager.skill_surface_available(target):
            for skill_name in skill_manager.managed_builtin_skill_names(target):
                existing_paths = self._stringify_existing_paths(
                    skill_manager.managed_skill_cleanup_paths(target, skill_name)
                )
                if not existing_paths:
                    continue
                planned_skill_names.append(skill_name)
                planned_skill_paths.extend(existing_paths)

            legacy_paths = self._stringify_existing_paths(
                skill_manager.legacy_skill_cleanup_paths(target)
            )
            if legacy_paths:
                planned_legacy_skill_aliases = skill_manager.legacy_cleanup_skill_names()
                planned_legacy_skill_paths = legacy_paths

        return {
            "target": target,
            "planned_surface_paths": planned_surface_paths,
            "planned_skill_names": planned_skill_names,
            "planned_skill_paths": sorted(set(planned_skill_paths)),
            "planned_legacy_skill_aliases": planned_legacy_skill_aliases,
            "planned_legacy_skill_paths": planned_legacy_skill_paths,
            "missing_surface_paths": missing_surface_paths,
        }

    def _write_onboard_smoke_report(
        self,
        *,
        project_dir: Path,
        integration_manager,
        include_user_surfaces: bool,
        target_results: list[dict[str, Any]],
        status: str,
    ) -> dict[str, str]:
        report_paths = self._onboard_smoke_report_paths(project_dir)
        generated_at = datetime.now(timezone.utc).isoformat()
        targets_payload: list[dict[str, Any]] = []
        markdown_lines = [
            "# 宿主接入冒烟验证指南",
            "",
            f"- Generated At: {generated_at}",
            f"- Project: {project_dir}",
            f"- Install Scope: {'project + user surfaces' if include_user_surfaces else 'project surfaces only'}",
            f"- Status: {status}",
            "",
        ]
        framework_playbook = load_framework_playbook_summary(project_dir)
        if isinstance(framework_playbook, dict) and framework_playbook:
            markdown_lines.extend(
                [
                    "## 框架焦点（Framework Coaching Focus）",
                    "",
                    f"- Framework: {framework_playbook.get('framework', '-')}",
                ]
            )
            modules = framework_playbook.get("implementation_modules", [])
            if isinstance(modules, list) and modules:
                markdown_lines.append(
                    "- Implementation Modules: " + "；".join(str(item) for item in modules[:4])
                )
            native_capabilities = framework_playbook.get("native_capabilities", [])
            if isinstance(native_capabilities, list) and native_capabilities:
                markdown_lines.append(
                    "- Native Capabilities: "
                    + "；".join(str(item) for item in native_capabilities[:4])
                )
            validation_surfaces = framework_playbook.get("validation_surfaces", [])
            if isinstance(validation_surfaces, list) and validation_surfaces:
                markdown_lines.append(
                    "- Validation Surfaces: "
                    + "；".join(str(item) for item in validation_surfaces[:4])
                )
            delivery_evidence = framework_playbook.get("delivery_evidence", [])
            if isinstance(delivery_evidence, list) and delivery_evidence:
                markdown_lines.append(
                    "- Delivery Evidence: " + "；".join(str(item) for item in delivery_evidence[:4])
                )
            markdown_lines.append("")
        for item in target_results:
            target = str(item.get("target", "")).strip()
            if not target:
                continue
            usage = self._build_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            )
            standard_first_prompt = build_host_standard_first_prompt(target)
            competition_first_prompt = build_host_competition_first_prompt(target)
            post_onboard_self_check = build_host_post_onboard_self_check(target, usage)
            official_workflow_checks = build_host_official_workflow_checks(target, usage)
            official_pass_criteria = build_host_official_pass_criteria(target, usage)
            start_playbook = build_host_start_playbook(target)
            resume_guidance = build_host_resume_guidance(target)
            adaptation_contract = (
                dict(usage.get("adaptation_contract", {}))
                if isinstance(usage.get("adaptation_contract", {}), dict)
                else {}
            )
            target_payload: dict[str, Any] = {
                "target": target,
                "host_name": self._host_label(target),
                "status": "ready" if not item.get("errors") else "partial",
                "include_user_surfaces": include_user_surfaces,
                "standard_flow_first_prompt": standard_first_prompt,
                "competition_flow_first_prompt": competition_first_prompt,
                "post_onboard_self_check": post_onboard_self_check,
                "official_workflow_checks": official_workflow_checks,
                "official_pass_criteria": official_pass_criteria,
                "start_playbook": start_playbook,
                "resume_guidance": resume_guidance,
                "repair_playbook": str(usage.get("repair_playbook", "")).strip(),
                "managed_competition_project_surfaces": (
                    list(usage.get("managed_competition_project_surfaces", []))
                    if isinstance(usage.get("managed_competition_project_surfaces", []), list)
                    else []
                ),
                "managed_competition_user_surfaces": (
                    list(usage.get("managed_competition_user_surfaces", []))
                    if isinstance(usage.get("managed_competition_user_surfaces", []), list)
                    else []
                ),
                "framework_playbook": (
                    framework_playbook if isinstance(framework_playbook, dict) else {}
                ),
                "manifest_paths": list(item.get("manifest_paths", [])),
                "contract_failures": list(item.get("contract_failures", [])),
                "auto_repair_actions": (
                    dict(item.get("auto_repair_actions", {}))
                    if isinstance(item.get("auto_repair_actions", {}), dict)
                    else {}
                ),
                "adaptation_contract": adaptation_contract,
            }
            targets_payload.append(target_payload)

            markdown_lines.extend(
                [
                    f"## {self._host_label(target)}",
                    "",
                    f"- Status: {target_payload['status']}",
                    f"- Standard Flow First Prompt: `{standard_first_prompt}`",
                    f"- Competition Flow First Prompt: `{competition_first_prompt}`",
                    f"- Install Scope: {'project + user surfaces' if include_user_surfaces else 'project surfaces only'}",
                    "",
                    "### Start Playbook",
                ]
            )
            if start_playbook:
                markdown_lines.extend(f"- {line}" for line in start_playbook)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Post-Onboard Self-Check"])
            if post_onboard_self_check:
                markdown_lines.extend(f"- {line}" for line in post_onboard_self_check)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Official Workflow Checks"])
            if official_workflow_checks:
                markdown_lines.extend(f"- {line}" for line in official_workflow_checks)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Official Pass Criteria"])
            if official_pass_criteria:
                markdown_lines.extend(f"- {line}" for line in official_pass_criteria)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Resume Guidance"])
            if resume_guidance:
                markdown_lines.extend(f"- {line}" for line in resume_guidance)
            else:
                markdown_lines.append("- -")
            markdown_lines.extend(["", "### Repair Playbook"])
            repair_playbook = target_payload["repair_playbook"]
            markdown_lines.append(repair_playbook or "-")
            if target_payload["managed_competition_project_surfaces"]:
                markdown_lines.extend(["", "### SEEAI Project Supplements"])
                markdown_lines.extend(
                    f"- `{line}`" for line in target_payload["managed_competition_project_surfaces"]
                )
            if target_payload["managed_competition_user_surfaces"]:
                markdown_lines.extend(["", "### SEEAI User Supplements"])
                markdown_lines.extend(
                    f"- `{line}`" for line in target_payload["managed_competition_user_surfaces"]
                )
            if (
                isinstance(target_payload["framework_playbook"], dict)
                and target_payload["framework_playbook"]
            ):
                markdown_lines.extend(["", "### Framework Coaching"])
                markdown_lines.append(
                    f"- Framework: {target_payload['framework_playbook'].get('framework', '-')}"
                )
                modules = target_payload["framework_playbook"].get("implementation_modules", [])
                if isinstance(modules, list) and modules:
                    markdown_lines.append(
                        "- Implementation Modules: " + "；".join(str(line) for line in modules[:4])
                    )
                validation = target_payload["framework_playbook"].get("validation_surfaces", [])
                if isinstance(validation, list) and validation:
                    markdown_lines.append(
                        "- Validation Surfaces: " + "；".join(str(line) for line in validation[:4])
                    )
                evidence = target_payload["framework_playbook"].get("delivery_evidence", [])
                if isinstance(evidence, list) and evidence:
                    markdown_lines.append(
                        "- Delivery Evidence: " + "；".join(str(line) for line in evidence[:4])
                    )
            if target_payload["manifest_paths"]:
                markdown_lines.extend(["", "### Written Surfaces"])
                markdown_lines.extend(f"- `{line}`" for line in target_payload["manifest_paths"])
            if target_payload["contract_failures"]:
                markdown_lines.extend(["", "### Contract Failures"])
                markdown_lines.extend(f"- {line}" for line in target_payload["contract_failures"])
            markdown_lines.append("")

        payload = {
            "generated_at": generated_at,
            "project_dir": str(project_dir),
            "status": status,
            "install_scope": "project+user-surfaces" if include_user_surfaces else "project-only",
            "framework_playbook": (
                framework_playbook if isinstance(framework_playbook, dict) else {}
            ),
            "targets": targets_payload,
            "report_files": {name: str(path) for name, path in report_paths.items()},
        }
        report_paths["json"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report_paths["markdown"].write_text(
            "\n".join(markdown_lines).rstrip() + "\n", encoding="utf-8"
        )
        return {name: str(path) for name, path in report_paths.items()}

    def _write_cleanup_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, str]:
        report_paths = self._cleanup_report_paths(project_dir)
        report_paths["json"].write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        markdown_lines = [
            "# Host Cleanup Report",
            "",
            f"- Generated At: {payload.get('timestamp', '-')}",
            f"- Status: {payload.get('status', '-')}",
            f"- Dry Run: {'yes' if payload.get('dry_run', False) else 'no'}",
            f"- Summary: {payload.get('summary', '-')}",
            "",
        ]
        for item in payload.get("targets", []):
            if not isinstance(item, dict):
                continue
            target = str(item.get("target", "")).strip() or "-"
            markdown_lines.extend([f"## {self._host_label(target)}", ""])
            planned_surface_paths = list(item.get("planned_surface_paths", []))
            planned_skill_names = list(item.get("planned_skill_names", []))
            planned_legacy_skill_aliases = list(item.get("planned_legacy_skill_aliases", []))
            removed_paths = list(item.get("removed_paths", []))
            removed_skills = list(item.get("removed_skills", []))
            removed_legacy_skill_aliases = list(item.get("removed_legacy_skill_aliases", []))
            missing_surface_paths = list(item.get("missing_surface_paths", []))
            errors = list(item.get("errors", []))
            if payload.get("dry_run", False):
                markdown_lines.append(f"- Planned Surface Cleanup: {len(planned_surface_paths)}")
                markdown_lines.append(
                    f"- Planned Skill Cleanup: {', '.join(planned_skill_names) or '-'}"
                )
                markdown_lines.append(
                    f"- Planned Legacy Alias Cleanup: {', '.join(planned_legacy_skill_aliases) or '-'}"
                )
            else:
                markdown_lines.append(f"- Removed Surface Paths: {len(removed_paths)}")
                markdown_lines.append(f"- Removed Skills: {', '.join(removed_skills) or '-'}")
                markdown_lines.append(
                    f"- Removed Legacy Aliases: {', '.join(removed_legacy_skill_aliases) or '-'}"
                )
            if planned_surface_paths:
                markdown_lines.extend(["", "### Planned Surface Paths"])
                markdown_lines.extend(f"- `{line}`" for line in planned_surface_paths)
            if item.get("planned_skill_paths"):
                markdown_lines.extend(["", "### Planned Skill Paths"])
                markdown_lines.extend(f"- `{line}`" for line in item["planned_skill_paths"])
            if item.get("planned_legacy_skill_paths"):
                markdown_lines.extend(["", "### Planned Legacy Skill Paths"])
                markdown_lines.extend(f"- `{line}`" for line in item["planned_legacy_skill_paths"])
            if removed_paths:
                markdown_lines.extend(["", "### Removed Surface Paths"])
                markdown_lines.extend(f"- `{line}`" for line in removed_paths)
            if item.get("removed_skill_paths"):
                markdown_lines.extend(["", "### Removed Skill Paths"])
                markdown_lines.extend(f"- `{line}`" for line in item["removed_skill_paths"])
            if item.get("removed_legacy_skill_paths"):
                markdown_lines.extend(["", "### Removed Legacy Skill Paths"])
                markdown_lines.extend(f"- `{line}`" for line in item["removed_legacy_skill_paths"])
            if missing_surface_paths:
                markdown_lines.extend(["", "### Missing Surface Paths"])
                markdown_lines.extend(f"- `{line}`" for line in missing_surface_paths)
            if errors:
                markdown_lines.extend(["", "### Errors"])
                markdown_lines.extend(f"- {line}" for line in errors)
            markdown_lines.append("")
        report_paths["markdown"].write_text(
            "\n".join(markdown_lines).rstrip() + "\n",
            encoding="utf-8",
        )
        return {name: str(path) for name, path in report_paths.items()}

    @staticmethod
    def _include_user_surfaces(args) -> bool:
        return bool(getattr(args, "with_user_surfaces", False))

    @staticmethod
    def _display_final_trigger_for_profile(profile) -> str:
        if getattr(profile, "host", "") == "codex":
            return "App/Desktop: /super-dev | 回退: super-dev: 你的需求"
        if getattr(profile, "host", "") == "codex-cli":
            return "CLI: $super-dev | 回退: super-dev: 你的需求"
        return str(profile.trigger_command).replace("<需求描述>", "你的需求")

    def _is_manual_install_host(self, target: str | None) -> bool:
        return target is not None and get_install_mode(target) == HostInstallMode.MANUAL

    def _print_manual_install_host_guidance(self, *, target: str, command_name: str) -> int:
        from .integrations import IntegrationManager

        integration_manager = IntegrationManager(Path.cwd())
        docs = list(getattr(integration_manager, "OFFICIAL_DOCS_INDEX", {}).get(target, ()))
        host_name = self._host_label(target)
        guidance = render_manual_install_guidance(
            host_id=target,
            command_name=command_name,
            docs=docs,
        )
        if guidance is None:
            return 0
        if not RICH_AVAILABLE:
            self.console.print(f"{host_name} 不走 super-dev {command_name} 统一安装流。")
            plain = str(guidance.get("plain_fallback", "")).strip()
            if plain:
                self.console.print(plain)
            return 0
        panel_kwargs: dict[str, Any] = {
            "title": str(guidance.get("title", f"{host_name} 手动安装")),
            "border_style": str(guidance.get("border_style", "yellow")),
        }
        self.console.print(
            Panel(
                "\n".join(guidance.get("lines", [])),
                **panel_kwargs,
            )
        )
        return 0

    def _collect_runtime_install_health(self) -> dict[str, Any]:
        package_file = getattr(sys.modules[__name__.rsplit(".", 1)[0]], "__file__", None)
        current_module_path = Path(package_file or __file__).resolve()
        installed_dist_version = ""
        metadata_error = ""
        try:
            installed_dist_version = importlib.metadata.version("super-dev")
        except importlib.metadata.PackageNotFoundError:
            installed_dist_version = ""
        except Exception as exc:
            metadata_error = str(exc)

        site_packages_entries = [
            Path(entry).resolve()
            for entry in sys.path
            if isinstance(entry, str) and "site-packages" in entry
        ]
        stale_package_dirs: list[str] = []
        dist_info_versions: list[str] = []
        editable_versions: list[str] = []
        dist_info_pattern = re.compile(r"super_dev-(?P<version>.+)\.dist-info$")
        editable_pattern = re.compile(r"__editable__\.super_dev-(?P<version>.+)\.pth$")
        for site_packages in site_packages_entries:
            package_dir = site_packages / "super_dev"
            if package_dir.exists():
                init_file = package_dir / "__init__.py"
                if init_file.exists() and init_file.resolve() != current_module_path:
                    stale_package_dirs.append(str(package_dir))
            for dist_info in site_packages.glob("super_dev-*.dist-info"):
                match = dist_info_pattern.search(dist_info.name)
                if match:
                    dist_info_versions.append(match.group("version"))
            for editable in site_packages.glob("__editable__.super_dev-*.pth"):
                match = editable_pattern.search(editable.name)
                if match:
                    editable_versions.append(match.group("version"))

        dist_info_versions = sorted(set(dist_info_versions))
        editable_versions = sorted(set(editable_versions))
        warnings: list[str] = []
        remediation: list[str] = []

        if stale_package_dirs:
            warnings.append("检测到 site-packages 中残留的 super_dev 实体目录，可能覆盖当前版本。")
            remediation.append("删除旧的 site-packages/super_dev 目录后重新执行 pip install -e .")
        if len(dist_info_versions) > 1:
            warnings.append(
                "检测到多个 super-dev dist-info 版本并存: " + ", ".join(dist_info_versions)
            )
            remediation.append("清理旧的 super_dev-*.dist-info 残留，只保留当前版本。")
        if len(editable_versions) > 1:
            warnings.append("检测到多个 editable 安装记录并存: " + ", ".join(editable_versions))
            remediation.append("清理旧的 __editable__.super_dev-*.pth 和 finder 文件后重新安装。")
        if installed_dist_version and installed_dist_version != __version__:
            warnings.append(
                f"包元数据版本 {installed_dist_version} 与当前运行版本 {__version__} 不一致。"
            )
            remediation.append("重新安装 super-dev，确保脚本与导入版本一致。")
        if metadata_error:
            warnings.append(f"读取安装元数据失败: {metadata_error}")

        return {
            "healthy": not warnings,
            "current_version": __version__,
            "current_module_path": str(current_module_path),
            "installed_dist_version": installed_dist_version,
            "stale_package_dirs": stale_package_dirs,
            "dist_info_versions": dist_info_versions,
            "editable_versions": editable_versions,
            "warnings": warnings,
            "remediation": remediation,
        }

    def _print_runtime_install_health(
        self, runtime_health: dict[str, Any], *, indent: str = ""
    ) -> None:
        status = (
            "[green]正常[/green]"
            if runtime_health.get("healthy", False)
            else "[yellow]异常[/yellow]"
        )
        self.console.print(
            f"{indent}[cyan]运行时安装[/cyan]: {status} 版本 {runtime_health.get('current_version', '-')}"
        )
        self.console.print(
            f"{indent}[dim]模块路径: {runtime_health.get('current_module_path', '-')}[/dim]"
        )
        installed_dist_version = runtime_health.get("installed_dist_version", "")
        if installed_dist_version:
            self.console.print(f"{indent}[dim]安装元数据版本: {installed_dist_version}[/dim]")
        for warning in runtime_health.get("warnings", []):
            self.console.print(f"{indent}[yellow]- {warning}[/yellow]")
        for action in runtime_health.get("remediation", []):
            self.console.print(f"{indent}[dim]修复: {action}[/dim]")

    def _auto_fix_runtime_install(self, runtime_health: dict[str, Any]) -> None:
        """自动清理旧版本残留并重新安装。"""
        import shutil

        fixed: list[str] = []
        failed: list[str] = []
        current_version = runtime_health.get("current_version", __version__)

        # 1. 删除旧的 super_dev 实体目录
        for stale_dir in runtime_health.get("stale_package_dirs", []):
            try:
                shutil.rmtree(stale_dir)
                fixed.append(f"已删除残留目录: {stale_dir}")
            except Exception as exc:
                failed.append(f"无法删除 {stale_dir}: {exc}")

        # 2. 清理多余的 editable pth 文件（只保留当前版本）
        editable_versions = runtime_health.get("editable_versions", [])
        if len(editable_versions) > 1:
            site_packages_entries = [
                Path(entry).resolve()
                for entry in sys.path
                if isinstance(entry, str) and "site-packages" in entry
            ]
            for site_packages in site_packages_entries:
                for pth_file in site_packages.glob("__editable__.super_dev-*.pth"):
                    if current_version not in pth_file.name:
                        try:
                            pth_file.unlink()
                            fixed.append(f"已删除旧 pth: {pth_file.name}")
                        except Exception as exc:
                            failed.append(f"无法删除 {pth_file.name}: {exc}")

        # 3. 清理多余的 dist-info（只保留当前版本）
        dist_info_versions = runtime_health.get("dist_info_versions", [])
        if len(dist_info_versions) > 1:
            site_packages_entries = [
                Path(entry).resolve()
                for entry in sys.path
                if isinstance(entry, str) and "site-packages" in entry
            ]
            for site_packages in site_packages_entries:
                for dist_info in site_packages.glob("super_dev-*.dist-info"):
                    if current_version not in dist_info.name:
                        try:
                            shutil.rmtree(dist_info)
                            fixed.append(f"已删除旧 dist-info: {dist_info.name}")
                        except Exception as exc:
                            failed.append(f"无法删除 {dist_info.name}: {exc}")

        if fixed:
            for msg in fixed:
                self.console.print(f"  [green]✓[/green] {msg}")
        if failed:
            for msg in failed:
                self.console.print(f"  [red]✗[/red] {msg}")
        if not fixed and not failed:
            self.console.print("  [dim]未发现需要清理的文件。[/dim]")
        elif fixed and not failed:
            self.console.print("  [green]修复完成。[/green]")

    def _host_label(self, target: str) -> str:
        return host_display_name(target)

    def _host_path_override_key(self, target: str) -> str:
        return str(host_path_override_guide(target).get("env_key", ""))

    def _custom_host_path_override_hint(self, target: str | None = None) -> str:
        if target:
            return str(host_path_override_guide(target).get("hint", ""))
        return str(host_path_override_guide("codex-cli").get("hint", ""))

    def _format_detection_reason(self, reason: str) -> str:
        source, _, value = str(reason).partition(":")
        source_labels = {
            "cmd": "命令命中",
            "path": "默认安装路径",
            "env": "自定义路径覆盖",
            "registry": "Windows 注册信息",
            "shim": "Windows shim / 包管理器目录",
        }
        label = source_labels.get(source, source or "检测来源")
        return f"{label}: {value}" if value else label

    def _explain_detection_details(
        self, detected_meta: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        explained: dict[str, list[str]] = {}
        for host, reasons in detected_meta.items():
            explained[host] = [self._format_detection_reason(item) for item in reasons]
        return explained

    def _host_runtime_checklist(
        self, *, target: str, usage: dict[str, Any], project_dir: Path | None = None
    ) -> list[str]:
        lead = [
            build_host_start_guidance(target=target, usage=usage, include_resume_hint=False),
            *build_host_start_playbook(target),
            *build_host_official_workflow_checks(target, usage),
        ]
        trigger = str(usage.get("final_trigger", "")).strip() or "-"
        common = [
            f"在宿主中使用最终触发命令进入 Super Dev 流水线：{trigger}",
            "确认首轮响应明确进入 research，而不是直接开始编码。",
            "确认真实写入 output/*-research.md、output/*-prd.md、output/*-architecture.md、output/*-uiux.md。",
            "确认三文档完成后暂停等待用户确认，而不是直接继续实现。",
            "确认文档确认后能继续进入 Spec、前端运行验证、后端与交付阶段。",
        ]
        if project_dir is not None:
            framework_playbook = load_framework_playbook_summary(project_dir)
            if framework_playbook:
                common.extend(
                    [
                        f"确认当前项目按 {framework_playbook.get('framework', '跨平台框架')} playbook 执行，而不是按普通 Web 假设实现。",
                        "确认宿主已落实框架专项原生能力面，而不是只完成通用页面实现。",
                        "确认宿主已按框架专项必验场景完成真实验证，并沉淀交付证据。",
                    ]
                )
        overrides = host_runtime_validation_overrides(target)
        return [*lead, *overrides.get("runtime_checklist", []), *common]

    def _host_runtime_pass_criteria(
        self, *, target: str, usage: dict[str, Any], project_dir: Path | None = None
    ) -> list[str]:
        common = [
            "首轮响应符合 Super Dev 首轮契约。",
            "关键文档真实落盘到项目目录。",
            "确认门真实生效。",
            "后续恢复路径可用。",
        ]
        if project_dir is not None and load_framework_playbook_summary(project_dir):
            common.append("跨平台框架专项能力、必验场景与交付证据均已通过真人验收。")
        overrides = host_runtime_validation_overrides(target)
        return [
            *build_host_official_pass_criteria(target, usage),
            *overrides.get("pass_criteria", []),
            *common,
        ]

    def _host_resume_checklist(self, *, target: str, project_dir: Path | None = None) -> list[str]:
        common = [
            "重开宿主或新开会话后，使用恢复探针而不是普通闲聊进入当前流程。",
            "确认宿主先读取 `.super-dev/SESSION_BRIEF.md`，并继续当前流程而不是重新开始。",
            "确认用户继续说“改一下 / 补充 / 继续改 / 确认 / 通过”时，宿主仍然留在当前 Super Dev 流程内。",
        ]
        if project_dir is not None:
            framework_playbook = load_framework_playbook_summary(project_dir)
            if framework_playbook:
                common.append(
                    f"恢复后继续实现或返工时，仍然遵守 {framework_playbook.get('framework', '跨平台框架')} 的专项 playbook。"
                )
        overrides = host_runtime_validation_overrides(target)
        return [
            *build_host_resume_guidance(target),
            *overrides.get("resume_checklist", []),
            *common,
        ]

    def _host_resume_probe_prompt(self, *, project_dir: Path, target: str) -> str:
        if not self._project_has_super_dev_context(project_dir):
            return ""
        return str(self._build_host_continue_prompt(project_dir=project_dir, target=target))

    def _resolve_onboard_targets(
        self,
        *,
        available_targets: list[str],
        host: str | None,
        all_targets: bool,
        non_interactive: bool,
    ) -> list[str]:
        targets: list[str] = []
        if all_targets:
            return available_targets
        if host:
            return [host]
        if non_interactive:
            return available_targets

        interactive_targets = self._interactive_host_selector(available_targets=available_targets)
        if interactive_targets is not None:
            return interactive_targets

        self._render_host_selection_guide(available_targets=available_targets)
        raw = input("宿主选择: ").strip()
        if not raw:
            return available_targets
        try:
            selected_indices = [int(item.strip()) for item in raw.split(",") if item.strip()]
        except ValueError:
            raise ValueError("输入无效，请输入数字编号（如 1,3）")
        for index in selected_indices:
            if index < 1 or index > len(available_targets):
                raise ValueError(f"编号超出范围: {index}")

        seen = set()
        for index in selected_indices:
            target = available_targets[index - 1]
            if target in seen:
                continue
            seen.add(target)
            targets.append(target)
        return targets

    def _super_dev_ascii_banner(self) -> str:
        return (
            "  ____                        ____             \n"
            " / ___| _   _ _ __   ___ _ __|  _ \\  _____   __\n"
            " \\___ \\| | | | '_ \\ / _ \\ '__| | | |/ _ \\ \\ / /\n"
            "  ___) | |_| | |_) |  __/ |  | |_| |  __/\\ V / \n"
            " |____/ \\__,_| .__/ \\___|_|  |____/ \\___| \\_/  \n"
            "             |_|                               "
        )

    def _read_single_key(self) -> str:
        if os.name == "nt":
            import msvcrt

            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                special = msvcrt.getwch()
                return {
                    "H": "UP",
                    "P": "DOWN",
                }.get(special, special)
            if key == "\r":
                return "ENTER"
            if key == " ":
                return "SPACE"
            if key == "\x1b":
                return "ESC"
            return key

        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            first = sys.stdin.read(1)
            if first == "\x1b":
                second = sys.stdin.read(1)
                if second == "[":
                    third = sys.stdin.read(1)
                    return {
                        "A": "UP",
                        "B": "DOWN",
                    }.get(third, "ESC")
                return "ESC"
            if first in ("\r", "\n"):
                return "ENTER"
            if first == " ":
                return "SPACE"
            return first
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _interactive_host_selector(self, *, available_targets: list[str]) -> list[str] | None:
        from .integrations import IntegrationManager

        if not RICH_AVAILABLE:
            return None
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return None

        integration_manager = IntegrationManager(Path.cwd())
        detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
        selected: set[str] = set(detected_targets)
        cursor = 0
        status_message = ""

        def renderable() -> Group:
            # 获取终端高度，计算可显示的行数
            try:
                term_height = self.console.size.height
            except Exception:
                term_height = 24
            try:
                term_width = self.console.size.width
            except Exception:
                term_width = 80
            max_visible = max(5, term_height - 10)
            compact = term_width < 100

            subtitle = "Space 勾选  Enter 安装  U 卸载  ↑↓ 移动  A 全选  R 清空  Esc 取消"
            header = Panel(
                normalize_terminal_text(subtitle),
                title="Super Dev",
                expand=True,
                padding=(0, 1),
            )

            table = Table(show_header=True, header_style="bold cyan", expand=True, padding=(0, 1))
            table.add_column("", max_width=3, justify="center")
            table.add_column("#", max_width=3, style="cyan", justify="center")
            table.add_column("宿主", style="bold", ratio=3)
            table.add_column("认证", ratio=2)
            if not compact:
                table.add_column("触发", ratio=2)

            # 滚动窗口：只显示光标附��的 max_visible 行
            total = len(available_targets)
            if total <= max_visible:
                start, end = 0, total
            else:
                half = max_visible // 2
                start = max(0, cursor - half)
                end = start + max_visible
                if end > total:
                    end = total
                    start = max(0, end - max_visible)

            for idx in range(start, end):
                target = available_targets[idx]
                profile = integration_manager.get_adapter_profile(target)
                is_manual = self._is_manual_install_host(target)
                selected_mark = "[✓]" if target in selected else "[○]"
                pointer = " > " if idx == cursor else "   "
                host_label = Text()
                host_label.append(
                    f"{selected_mark} ", style="green" if target in selected else "dim"
                )
                display_name = self._host_label(target)
                if is_manual:
                    display_name += " (手动)"
                host_label.append(display_name, style="bold white" if idx == cursor else "bold")
                row: list[Any] = [pointer, str(idx + 1), host_label, profile.certification_label]
                if not compact:
                    trigger = (
                        "/super-dev" if integration_manager.supports_slash(target) else "super-dev:"
                    )
                    row.append(trigger)
                table.add_row(*row)

            # 滚动指示器
            scroll_info = ""
            if total > max_visible:
                if start > 0:
                    scroll_info += f"  ↑ {start}"
                if end < total:
                    scroll_info += f"  ↓ {total - end}"

            selected_names = [self._host_label(t) for t in available_targets if t in selected]
            selected_text = ", ".join(selected_names) if selected_names else "未选择"
            footer = Text()
            footer.append(f"已选 ({len(selected)}/{total}): ", style="cyan")
            footer.append(selected_text, style="bold white")
            if scroll_info:
                footer.append(scroll_info, style="dim")

            parts: list[Any] = [header, table, footer]
            if status_message:
                parts.append(Text(status_message, style="yellow"))
            return Group(*parts)

        with Live(
            renderable(),
            console=self.console,
            refresh_per_second=8,
            transient=True,
            auto_refresh=False,
        ) as live:
            while True:
                key = self._read_single_key()
                status_message = ""
                if key == "UP":
                    cursor = (cursor - 1) % len(available_targets)
                    live.update(renderable(), refresh=True)
                    continue
                if key == "DOWN":
                    cursor = (cursor + 1) % len(available_targets)
                    live.update(renderable(), refresh=True)
                    continue
                if key == "SPACE":
                    target = available_targets[cursor]
                    if target in selected:
                        selected.remove(target)
                    else:
                        selected.add(target)
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("a", "A"):
                    selected = set(available_targets)
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("c", "C"):
                    selected = {
                        target
                        for target in available_targets
                        if integration_manager.get_adapter_profile(target).category == "cli"
                    }
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("i", "I"):
                    selected = {
                        target
                        for target in available_targets
                        if integration_manager.get_adapter_profile(target).category == "ide"
                    }
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("r", "R"):
                    selected.clear()
                    live.update(renderable(), refresh=True)
                    continue
                if key in ("u", "U"):
                    if not selected:
                        status_message = "请先选中要卸载的宿主"
                        live.update(renderable(), refresh=True)
                        continue
                    # 卸载选中宿主的 super-dev 集成
                    from .skills import SkillManager

                    skill_manager = SkillManager(Path.cwd())
                    uninstalled_count = 0
                    for target in sorted(selected):
                        try:
                            removed = integration_manager.remove(target=target)
                            if removed:
                                uninstalled_count += len(removed)
                        except Exception:
                            pass
                        try:
                            if skill_manager.skill_surface_available(target):
                                for skill_name in skill_manager.managed_builtin_skill_names(target):
                                    try:
                                        skill_manager.uninstall(skill_name, target)
                                        uninstalled_count += 1
                                    except FileNotFoundError:
                                        continue
                                uninstalled_count += len(
                                    skill_manager.cleanup_legacy_skill_aliases(target)
                                )
                        except Exception:
                            pass
                    status_message = (
                        f"已从 {len(selected)} 个宿主卸载 Super Dev（{uninstalled_count} 个文件）"
                    )
                    selected.clear()
                    live.update(renderable(), refresh=True)
                    continue
                if key == "ENTER":
                    chosen = [target for target in available_targets if target in selected]
                    if chosen:
                        return chosen
                    status_message = "请至少选择一个宿主"
                    live.update(renderable(), refresh=True)
                    continue
                if key == "ESC":
                    raise ValueError("已取消宿主选择")
                live.update(renderable(), refresh=True)

    def _build_install_summary(self, *, available_targets: list[str]) -> str:
        from .integrations import IntegrationManager

        integration_manager = IntegrationManager(Path.cwd())
        codex_hosts = [target for target in available_targets if target in {"codex", "codex-cli"}]
        slash_hosts = [
            target
            for target in available_targets
            if integration_manager.supports_slash(target) and target not in codex_hosts
        ]
        text_hosts = [
            target
            for target in available_targets
            if not integration_manager.supports_slash(target) and target not in codex_hosts
        ]
        parts: list[str] = []
        if slash_hosts:
            parts.append(
                f"slash 宿主 ({len(slash_hosts)}): "
                + ", ".join(self._host_label(target) for target in slash_hosts)
            )
        if codex_hosts:
            parts.append(
                f"Codex skill 宿主 ({len(codex_hosts)}): "
                + ", ".join(self._host_label(target) for target in codex_hosts)
                + "（App/Desktop 用 `/super-dev`，CLI 用 `$super-dev`）"
            )
        if text_hosts:
            parts.append(
                f"text 宿主 ({len(text_hosts)}): "
                + ", ".join(self._host_label(target) for target in text_hosts)
            )
        return "\n".join(parts)

    def _render_host_selection_guide(self, *, available_targets: list[str]) -> None:
        from .integrations import IntegrationManager

        if not RICH_AVAILABLE:
            self.console.print("[cyan]请选择宿主 AI Coding 工具（可多选）:[/cyan]")
            for idx, target in enumerate(available_targets, 1):
                self.console.print(f"  {idx}. {self._host_label(target)}")
            self.console.print("[dim]输入编号（逗号分隔），直接回车表示全部[/dim]")
            return

        integration_manager = IntegrationManager(Path.cwd())
        detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
        width = self.console.width
        narrow = width < 60
        compact = width < 100

        intro = (
            f"当前版本内置 {len(available_targets)} 个宿主适配。\n"
            "slash 宿主: /super-dev  |  text 宿主: super-dev:  |  Codex: $super-dev"
        )
        self.console.print(Panel(intro, title="Super Dev 安装向导", padding=(0, 1), expand=True))

        table = Table(show_header=True, header_style="bold cyan", expand=True, padding=(0, 1))
        table.add_column("#", style="cyan", max_width=3, justify="center")
        table.add_column("宿主", style="bold", ratio=3)
        table.add_column("认证", ratio=2)
        if not narrow:
            table.add_column("触发", ratio=2)
        if not compact:
            table.add_column("检测", max_width=6, justify="center")

        for idx, target in enumerate(available_targets, 1):
            profile = integration_manager.get_adapter_profile(target)
            is_manual = self._is_manual_install_host(target)
            if target == "codex-cli":
                trigger = "$super-dev"
            elif target == "codex":
                trigger = "/super-dev"
            else:
                trigger = (
                    "/super-dev" if integration_manager.supports_slash(target) else "super-dev:"
                )
            label = self._host_label(target)
            if is_manual:
                label = f"{label} [yellow](手动)[/yellow]"
            row: list[str] = [str(idx), label, profile.certification_label]
            if not narrow:
                row.append(trigger)
            if not compact:
                detected = "✓" if target in detected_targets else ""
                row.append(detected)
            table.add_row(*row)
        self.console.print(table)
        self.console.print("[dim]输入编号（逗号分隔），直接回车表示全部[/dim]")

    def _render_install_intro(self, *, args) -> None:
        from .integrations import IntegrationManager

        runtime_health = self._collect_runtime_install_health()
        if not RICH_AVAILABLE:
            self.console.print("[cyan]Super Dev 安装入口[/cyan]")
            self.console.print("宿主负责编码与模型调用；Super Dev 负责流程、门禁、审计与交付标准。")
            self.console.print("终端只负责接入；真正开发回宿主里，复制第一句并按冒烟验证指南检查。")
            self.console.print(
                "接入完成后，slash 宿主优先输入 /super-dev；非 slash 宿主输入 super-dev: 或 super-dev："
            )
            self.console.print(
                "默认只写当前项目内接入面；如需用户级协议面，请显式加 --with-user-surfaces。"
            )
            if not runtime_health.get("healthy", False):
                self.console.print(
                    "[yellow]检测到 super-dev 运行时安装残留，建议先执行 doctor 检查。[/yellow]"
                )
            return

        integration_manager = IntegrationManager(Path.cwd())
        available_targets = self._public_host_targets(integration_manager=integration_manager)
        lines = [
            "[bold]标准模式[/bold]  /super-dev 你的需求  |  super-dev: 你的需求",
            "[bold]赛事模式[/bold]  /super-dev-seeai 你的需求  |  super-dev-seeai: 你的需求",
            "",
            self._build_install_summary(available_targets=available_targets),
            "终端只负责接入；真正开发回宿主里，复制第一句并按冒烟验证指南检查。",
            "默认只写当前项目内接入面；如需跨项目共用用户级协议面，再显式加 --with-user-surfaces。",
        ]
        if getattr(args, "auto", False):
            lines.append("当前模式: 自动检测宿主。")
        elif getattr(args, "host", None):
            lines.append(f"当前模式: 仅接入 {self._host_label(args.host)}。")
        elif getattr(args, "all", False):
            lines.append("当前模式: 接入全部宿主。")
        self.console.print(Panel("\n".join(lines), title="Super Dev", padding=(1, 1), expand=True))
        if not runtime_health.get("healthy", False):
            self.console.print("[yellow]检测到旧版本残留，正在自动清理...[/yellow]")
            self._auto_fix_runtime_install(runtime_health)
            self.console.print("")

        # After runtime health fix, clean up legacy skills globally + refresh outdated
        try:
            from .skills import SkillManager

            cleaned = SkillManager.cleanup_all_legacy()
            if cleaned:
                for path in cleaned:
                    self.console.print(f"  [green]✓[/green] 已清理旧 Skill: {path}")
        except Exception:
            pass
        self._auto_refresh_outdated_skills()

    def _auto_refresh_outdated_skills(self) -> None:
        """Silently refresh any installed skills that have outdated versions."""
        from .skills import SkillManager

        try:
            skill_manager = SkillManager(Path.cwd())
            for target, path_str in {
                **SkillManager.OFFICIAL_TARGET_PATHS,
                **SkillManager.OBSERVED_TARGET_PATHS,
            }.items():
                target_path = Path(path_str).expanduser()
                skill_md = target_path / "super-dev" / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text(encoding="utf-8")
                    if f"version: {__version__}" not in content:
                        try:
                            skill_manager.install(source="super-dev", target=target, force=True)
                        except Exception:
                            pass
        except Exception:
            pass

    def _detect_host_targets(
        self,
        *,
        available_targets: list[str],
    ) -> tuple[list[str], dict[str, list[str]]]:
        detected: list[str] = []
        details: dict[str, list[str]] = {}

        for target in available_targets:
            reasons: list[str] = []

            for command in HOST_COMMAND_CANDIDATES.get(target, []):
                if shutil.which(command):
                    reasons.append(f"cmd:{command}")
                    break

            for source, candidate in host_detection_path_candidates(target):
                if glob.glob(candidate):
                    reasons.append(f"{source}:{candidate}")
                    break

            if reasons:
                detected.append(target)
                details[target] = reasons

        return detected, details

    def _deduplicate_host_family(self, detected: list[str]) -> list[str]:
        """When both CLI and IDE variants of the same host are detected, keep only CLI."""
        result = list(detected)
        for cli_variant, ide_variant in self._HOST_FAMILIES:
            if cli_variant in result and ide_variant in result:
                result.remove(ide_variant)
        return result

    def _collect_configured_host_targets(
        self,
        *,
        project_dir: Path,
        available_targets: list[str],
    ) -> list[str]:
        from .integrations import IntegrationManager
        from .skills import SkillManager

        configured: list[str] = []
        skill_manager = SkillManager(project_dir)
        for target in available_targets:
            integration_files = IntegrationManager.TARGETS[target].files

            has_integration = any(
                (project_dir / relative).exists() for relative in integration_files
            )
            if IntegrationManager.supports_slash(target):
                project_slash_exists = IntegrationManager.resolve_slash_command_path(
                    target=target,
                    scope="project",
                    project_dir=project_dir,
                ).exists()
                global_slash_exists = IntegrationManager.resolve_slash_command_path(
                    target=target,
                    scope="global",
                ).exists()
            else:
                project_slash_exists = False
                global_slash_exists = False
            has_slash = project_slash_exists or global_slash_exists
            has_skill = False
            if IntegrationManager.requires_skill(target):
                try:
                    installed = set(skill_manager.list_installed(target))
                    managed = set(skill_manager.managed_builtin_skill_names(target))
                    has_skill = bool(installed & managed)
                except ValueError:
                    has_skill = False
            if has_integration or has_slash or has_skill:
                configured.append(target)
        return configured

    def _is_env_truthy(self, key: str) -> bool:
        value = os.getenv(key, "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _ensure_pipeline_host_ready(self, *, project_dir: Path, config: ProjectConfig) -> bool:
        from .integrations import IntegrationManager

        if self._is_env_truthy("SUPER_DEV_ALLOW_NO_HOST"):
            self.console.print("[dim]检测到 SUPER_DEV_ALLOW_NO_HOST=1，跳过宿主硬门禁[/dim]")
            return True

        available_targets = [item.name for item in IntegrationManager(project_dir).list_targets()]
        detected_targets, _ = self._detect_host_targets(available_targets=available_targets)
        configured_targets = self._collect_configured_host_targets(
            project_dir=project_dir,
            available_targets=available_targets,
        )

        if config.host_profile_enforce_selected and config.host_profile_targets:
            candidate_targets = [
                item for item in config.host_profile_targets if item in available_targets
            ]
        else:
            candidate_targets = sorted(set(configured_targets))

        candidate_targets = [
            target for target in candidate_targets if not self._is_manual_install_host(target)
        ]

        if not candidate_targets:
            self.console.print("[red]流水线宿主校验失败：未检测到可用宿主[/red]")
            self.console.print("[dim]请先执行: super-dev install --auto --force --yes[/dim]")
            self.console.print(
                "[dim]或手动接入: super-dev setup --host codex-cli --force --yes[/dim]"
            )
            return False

        report = self._collect_host_diagnostics(
            project_dir=project_dir,
            targets=candidate_targets,
            skill_name="super-dev",
            check_integrate=True,
            check_skill=True,
            check_slash=True,
        )
        compatibility = self._build_compatibility_summary(
            report=report,
            targets=candidate_targets,
            check_integrate=True,
            check_skill=True,
            check_slash=True,
        )

        host_scores = compatibility.get("hosts", {})
        if not isinstance(host_scores, dict):
            host_scores = {}
        ready_targets = [
            target
            for target in candidate_targets
            if bool((host_scores.get(target) or {}).get("ready", False))
        ]
        ready_detected_targets = [target for target in ready_targets if target in detected_targets]

        if ready_detected_targets:
            self.console.print(
                "[dim]宿主硬门禁通过: "
                + ", ".join(self._host_label(target) for target in ready_detected_targets)
                + "[/dim]"
            )
            return True

        self.console.print("[red]流水线宿主校验失败：未找到 ready 的已检测宿主[/red]")
        if ready_targets:
            self.console.print(
                "[yellow]检测到已接入宿主但未识别到本机可执行宿主: "
                + ", ".join(self._host_label(target) for target in ready_targets)
                + "[/yellow]"
            )

        hosts_report = report.get("hosts", {})
        if isinstance(hosts_report, dict):
            for target in candidate_targets:
                host = hosts_report.get(target, {})
                if not isinstance(host, dict):
                    continue
                suggestions = host.get("suggestions", [])
                if isinstance(suggestions, list):
                    for item in suggestions:
                        self.console.print(f"[dim]- {item}[/dim]")

        self.console.print("[dim]建议先执行: super-dev detect --auto --save-profile[/dim]")
        return False

    def _collect_host_diagnostics(
        self,
        *,
        project_dir: Path,
        targets: list[str],
        skill_name: str,
        check_integrate: bool,
        check_skill: bool,
        check_slash: bool,
    ) -> dict[str, Any]:
        from .skills import SkillManager

        skill_manager = SkillManager(project_dir)
        return collect_host_diagnostics(
            project_dir=project_dir,
            targets=targets,
            skill_name=skill_name,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
            build_usage_profile_fn=(
                lambda integration_manager, target: self._build_host_usage_profile(
                    integration_manager=integration_manager,
                    target=target,
                )
            ),
            build_diagnosis_fn=(
                lambda target, host_report, integration_manager: self._build_host_diagnosis(
                    target=target,
                    host_report=host_report,
                    integration_manager=integration_manager,
                )
            ),
            skill_primary_file_fn=(
                lambda target, skill_files, optional_skill_files, compatibility_skill_files: (
                    (skill_files or optional_skill_files or compatibility_skill_files)[0]
                    if (skill_files or optional_skill_files or compatibility_skill_files)
                    else (skill_manager._target_dir(target) / skill_name / "SKILL.md")
                )
            ),
            integrate_no_project_note="no project files for this host",
        )

    def _build_compatibility_summary(
        self,
        *,
        report: dict[str, Any],
        targets: list[str],
        check_integrate: bool,
        check_skill: bool,
        check_slash: bool,
    ) -> dict[str, Any]:
        return build_host_compatibility_summary(
            report=report,
            targets=targets,
            check_integrate=check_integrate,
            check_skill=check_skill,
            check_slash=check_slash,
            include_flow_metrics=True,
        )

    def _build_host_diagnosis(
        self,
        *,
        target: str,
        host_report: dict[str, Any],
        integration_manager,
    ) -> dict[str, str]:
        profile = integration_manager.get_adapter_profile(target)
        missing = host_report.get("missing", [])
        preconditions = (
            host_report.get("preconditions", {}) if isinstance(host_report, dict) else {}
        )
        precondition_status = str(preconditions.get("status", "")).strip()
        precondition_label = str(preconditions.get("label", "")).strip()
        suggestions = host_report.get("suggestions", [])
        suggested_command = ""
        if isinstance(suggestions, list):
            for item in suggestions:
                if isinstance(item, str) and item.strip():
                    suggested_command = item
                    break
        if not suggested_command and suggestions:
            first = suggestions[0]
            if isinstance(first, str):
                suggested_command = first

        primary_reason = str(profile.certification_reason or "").strip()
        blocker_summary = "当前还缺少关键接入项。"

        if "contract" in missing:
            blocker_summary = "已存在宿主接入文件，但内容版本过旧或缺少当前流水线契约。"
            if not suggested_command:
                suggested_command = "重新运行 super-dev，补齐并刷新当前宿主接入面。"
        elif "integrate" in missing:
            blocker_summary = "当前项目里还没有写入该宿主需要的接入文件。"
            if not suggested_command:
                suggested_command = "重新运行 super-dev，把当前项目需要的宿主接入文件补齐。"
        elif "skill" in missing:
            blocker_summary = "宿主级 Skill 目录存在，但 Super Dev Skill 还没装进去。"
            if not suggested_command:
                suggested_command = (
                    "重新运行 super-dev，确保当前宿主需要的 Skill 已安装到用户目录。"
                )
        elif "slash" in missing:
            blocker_summary = "宿主命令映射还没写入，所以宿主里还不能直接触发 `/super-dev`。"
            if not suggested_command:
                suggested_command = "重新运行 super-dev，确保当前宿主可直接触发 /super-dev。"
        elif precondition_status == "host-auth-required":
            blocker_summary = precondition_label or "宿主鉴权还没完成。"
        elif precondition_status == "session-restart-required":
            blocker_summary = precondition_label or "接入完成后还需要重开宿主会话。"
        elif precondition_status == "project-context-required":
            blocker_summary = precondition_label or "当前会话还没绑定到目标项目。"

        return {
            "certification_reason": primary_reason,
            "blocker_summary": blocker_summary,
            "suggested_command": suggested_command,
        }

    def _build_runtime_governance_summary(
        self,
        *,
        project_dir: Path,
        targets: list[str],
    ) -> dict[str, Any]:
        return collect_layered_runtime_governance_gap(project_dir, targets=targets)

    def _build_compliance_governance_summary(self, *, project_dir: Path) -> dict[str, Any]:
        return collect_compliance_governance_signal(project_dir, output_dir=project_dir / "output")

    def _build_official_compare_summary(
        self, *, hardening_results: dict[str, Any]
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        partial = 0
        unknown = 0
        failed = 0
        per_host: dict[str, str] = {}
        for host, item in hardening_results.items():
            total += 1
            status = "unknown"
            if isinstance(item, dict):
                official_compare = item.get("official_compare", {})
                if isinstance(official_compare, dict):
                    status = str(official_compare.get("status", "unknown")).strip() or "unknown"
            per_host[str(host)] = status
            if status == "passed":
                passed += 1
            elif status == "partial":
                partial += 1
            elif status == "failed":
                failed += 1
            else:
                unknown += 1
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "unknown": unknown,
            "score": score,
            "hosts": per_host,
        }

    def _build_host_parity_summary(
        self, *, usage_profiles: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        per_host: dict[str, dict[str, Any]] = {}
        required_keys = ("slash", "rules", "skills", "trigger")
        for host, usage in usage_profiles.items():
            total += 1
            labels = usage.get("capability_labels", {}) if isinstance(usage, dict) else {}
            trigger_command = (
                str(usage.get("trigger_command", "")) if isinstance(usage, dict) else ""
            )
            smoke_prompt = (
                str(usage.get("smoke_test_prompt", "")) if isinstance(usage, dict) else ""
            )
            smoke_signal = (
                str(usage.get("smoke_success_signal", "")) if isinstance(usage, dict) else ""
            )
            protocol_mode = (
                str(usage.get("host_protocol_mode", "")).strip() if isinstance(usage, dict) else ""
            )
            slash_label = str((labels or {}).get("slash", "")).strip()
            trigger_ok = (
                trigger_command.startswith("/super-dev")
                if slash_label == "native"
                else trigger_command.startswith("super-dev:")
            )
            checks = {
                "trigger": trigger_ok,
                "smoke_prompt": "SMOKE_OK" in smoke_prompt,
                "smoke_signal": "SMOKE_OK" in smoke_signal,
                "protocol_mode": bool(protocol_mode),
                "capability_labels": all(key in labels for key in required_keys),
            }
            check_total = len(checks)
            check_passed = sum(1 for item in checks.values() if bool(item))
            host_pass = check_passed == check_total
            if host_pass:
                passed += 1
            per_host[str(host)] = {
                "passed": host_pass,
                "score": round((check_passed / check_total) * 100, 2) if check_total else 100.0,
                "checks": checks,
            }
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "score": score,
            "hosts": per_host,
        }

    def _build_host_recovery_summary(
        self,
        *,
        targets: list[str],
        usage_profiles: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        hosts: dict[str, dict[str, Any]] = {}
        for target in targets:
            total += 1
            usage = usage_profiles.get(target, {}) if isinstance(usage_profiles, dict) else {}
            preferred_prompt = ""
            if isinstance(usage, dict):
                entry_bundle = build_host_entry_prompts(
                    target=target,
                    instruction="继续当前流程",
                    supports_slash=bool(usage.get("supports_slash", False)),
                    flow_variant="standard",
                )
                preferred_key = str(entry_bundle.get("preferred_entry", "")).strip()
                entry_prompts = entry_bundle.get("entry_prompts", {})
                if isinstance(entry_prompts, dict):
                    preferred_prompt = str(entry_prompts.get(preferred_key, "")).strip()
                    if not preferred_prompt:
                        preferred_prompt = next(
                            (
                                str(value).strip()
                                for value in entry_prompts.values()
                                if str(value).strip()
                            ),
                            "",
                        )
            commands = ["super-dev", "super-dev update"]
            if preferred_prompt:
                commands.append(preferred_prompt)
            if isinstance(usage, dict):
                entry_prompts = entry_bundle.get("entry_prompts", {})
                fallback_prompt = ""
                if isinstance(entry_prompts, dict):
                    fallback_prompt = str(entry_prompts.get("fallback", "")).strip()
                if fallback_prompt and fallback_prompt not in commands:
                    commands.append(fallback_prompt)
            actions = [
                "先运行 `super-dev`，补齐当前宿主的接入面并刷新安装注入状态。",
                "如果宿主规则或 Skill 模板需要同步到最新版本，再运行 `super-dev update`。",
            ]
            if preferred_prompt:
                actions.append(
                    f"修复完成后回到宿主里继续，第一句优先直接使用 `{preferred_prompt}`。"
                )
            else:
                actions.append("修复完成后回到宿主里继续当前流程。")
            checks = {
                "has_primary_repair": commands[0] == "super-dev",
                "has_update_path": any(cmd == "super-dev update" for cmd in commands),
                "has_host_resume_prompt": bool(preferred_prompt),
                "avoids_retired_low_level_commands": not any(
                    any(
                        marker in cmd
                        for marker in ("integrate ", "skill install", "onboard --host")
                    )
                    for cmd in commands
                ),
            }
            host_pass = all(bool(item) for item in checks.values())
            if host_pass:
                passed += 1
            hosts[target] = {
                "passed": host_pass,
                "checks": checks,
                "recommended_commands": commands,
                "recommended_actions": actions,
            }
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "score": score,
            "hosts": hosts,
        }

    def _build_host_gate_summary(
        self, *, report: dict[str, Any], targets: list[str]
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        hosts: dict[str, dict[str, Any]] = {}
        report_hosts = report.get("hosts", {}) if isinstance(report, dict) else {}
        if not isinstance(report_hosts, dict):
            report_hosts = {}
        for target in targets:
            total += 1
            host = report_hosts.get(target, {})
            checks = host.get("checks", {}) if isinstance(host, dict) else {}
            contract = checks.get("contract", {}) if isinstance(checks, dict) else {}
            surfaces = contract.get("surfaces", {}) if isinstance(contract, dict) else {}
            docs_confirm_ok = True
            preview_confirm_ok = True
            if isinstance(surfaces, dict):
                for surface in surfaces.values():
                    if not isinstance(surface, dict):
                        continue
                    if not bool(surface.get("exists", False)):
                        continue
                    missing = surface.get("missing_markers", [])
                    if not isinstance(missing, list):
                        continue
                    if "confirmation" in missing:
                        docs_confirm_ok = False
                    if "flow" in missing:
                        preview_confirm_ok = False
            host_pass = docs_confirm_ok and preview_confirm_ok
            if host_pass:
                passed += 1
            hosts[target] = {
                "passed": host_pass,
                "checks": {
                    "docs_confirm_gate": docs_confirm_ok,
                    "preview_confirm_gate": preview_confirm_ok,
                },
            }
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "score": score,
            "hosts": hosts,
        }

    def _build_host_runtime_script_summary(
        self, *, usage_profiles: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        total = 0
        passed = 0
        hosts: dict[str, dict[str, Any]] = {}
        for host, usage in usage_profiles.items():
            total += 1
            if not isinstance(usage, dict):
                usage = {}
            smoke_steps = usage.get("smoke_test_steps", [])
            competition_smoke_steps = usage.get("competition_smoke_test_steps", [])
            post_steps = usage.get("post_onboard_steps", [])
            checks = {
                "has_final_trigger": bool(str(usage.get("final_trigger", "")).strip()),
                "has_smoke_prompt": "SMOKE_OK" in str(usage.get("smoke_test_prompt", "")),
                "has_smoke_signal": "SMOKE_OK" in str(usage.get("smoke_success_signal", "")),
                "has_smoke_steps": isinstance(smoke_steps, list) and len(smoke_steps) > 0,
                "has_competition_smoke_prompt": "SEEAI_SMOKE_OK"
                in str(usage.get("competition_smoke_test_prompt", "")),
                "has_competition_smoke_signal": "SEEAI_SMOKE_OK"
                in str(usage.get("competition_smoke_success_signal", "")),
                "has_competition_smoke_steps": isinstance(competition_smoke_steps, list)
                and len(competition_smoke_steps) > 0,
                "has_post_onboard_steps": isinstance(post_steps, list) and len(post_steps) > 0,
            }
            host_pass = all(bool(item) for item in checks.values())
            if host_pass:
                passed += 1
            hosts[str(host)] = {
                "passed": host_pass,
                "checks": checks,
            }
        score = round((passed / total) * 100, 2) if total else 100.0
        return {
            "total": total,
            "passed": passed,
            "score": score,
            "hosts": hosts,
        }

    def _build_host_parity_index(
        self,
        *,
        threshold: float,
        official_compare_summary: dict[str, Any] | None,
        host_parity_summary: dict[str, Any] | None,
        host_gate_summary: dict[str, Any] | None,
        host_runtime_script_summary: dict[str, Any] | None,
        host_recovery_summary: dict[str, Any] | None,
        compatibility: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metrics: dict[str, float] = {}
        mapping: list[tuple[str, dict[str, Any] | None]] = [
            ("official_compare", official_compare_summary),
            ("host_parity", host_parity_summary),
            ("host_gate", host_gate_summary),
            ("runtime_script", host_runtime_script_summary),
            ("host_recovery", host_recovery_summary),
        ]
        for name, summary in mapping:
            if isinstance(summary, dict):
                if name == "official_compare":
                    total = int(summary.get("total", 0) or 0)
                    passed = int(summary.get("passed", 0) or 0)
                    partial = int(summary.get("partial", 0) or 0)
                    failed = int(summary.get("failed", 0) or 0)
                    if total <= 0 or (passed + partial + failed) <= 0:
                        continue
                try:
                    metrics[name] = float(summary.get("score", 0))
                except Exception:
                    metrics[name] = 0.0
        if isinstance(compatibility, dict):
            try:
                metrics["flow_consistency"] = float(compatibility.get("flow_consistency_score", 0))
            except Exception:
                metrics["flow_consistency"] = 0.0
        if metrics:
            score = round(sum(metrics.values()) / len(metrics), 2)
        else:
            score = 0.0
        limit = float(threshold)
        return {
            "score": score,
            "threshold": limit,
            "passed": score >= limit,
            "metrics": metrics,
        }

    def _repair_host_diagnostics(
        self,
        *,
        project_dir: Path,
        report: dict[str, Any],
        skill_name: str,
        force: bool,
        check_integrate: bool,
        check_skill: bool,
        check_slash: bool,
        include_user_surfaces: bool,
    ) -> dict[str, dict[str, str]]:
        from .integrations import IntegrationManager
        from .skills import SkillManager

        integration_manager = IntegrationManager(project_dir)
        skill_manager = SkillManager(project_dir)
        actions: dict[str, dict[str, str]] = {}

        hosts = report.get("hosts", {})
        if not isinstance(hosts, dict):
            return actions

        for target, host in hosts.items():
            if not isinstance(target, str) or not isinstance(host, dict):
                continue
            missing = host.get("missing", [])
            if not isinstance(missing, list):
                continue

            host_actions: dict[str, str] = {}
            contract_needs_repair = "contract" in missing
            user_surfaces_need_repair = include_user_surfaces and "user_surfaces" in missing
            effective_skill_name = SkillManager.default_skill_name(target)

            if contract_needs_repair:
                try:
                    integration_manager.setup(target=target, force=True)
                    if include_user_surfaces:
                        integration_manager.setup_global_protocol(target=target, force=True)
                        integration_manager.setup_global_agent_surfaces(target=target, force=True)
                    if integration_manager.supports_slash(target):
                        integration_manager.setup_slash_command(target=target, force=True)
                        if include_user_surfaces:
                            integration_manager.setup_global_slash_command(
                                target=target, force=True
                            )
                    if (
                        check_skill
                        and IntegrationManager.requires_skill(target)
                        and skill_manager.skill_surface_available(target)
                    ):
                        skill_manager.install(
                            source="super-dev",
                            target=target,
                            name=effective_skill_name,
                            force=True,
                        )
                    host_actions["contract"] = "refreshed"
                except Exception as exc:
                    host_actions["contract"] = f"failed: {exc}"

            try:
                if check_integrate and "integrate" in missing and not contract_needs_repair:
                    integration_manager.setup(target=target, force=force)
                    host_actions["integrate"] = "fixed"
            except Exception as exc:
                host_actions["integrate"] = f"failed: {exc}"

            try:
                if user_surfaces_need_repair and not contract_needs_repair:
                    repaired_any = False
                    if integration_manager.resolve_global_protocol_path(target) is not None:
                        integration_manager.setup_global_protocol(target=target, force=True)
                        repaired_any = True
                    if integration_manager.managed_user_agent_surfaces(target):
                        integration_manager.setup_global_agent_surfaces(target=target, force=True)
                        repaired_any = True
                    if (
                        check_skill
                        and IntegrationManager.requires_skill(target)
                        and skill_manager.skill_surface_available(target)
                    ):
                        skill_manager.install(
                            source="super-dev",
                            target=target,
                            name=effective_skill_name,
                            force=True,
                        )
                        repaired_any = True
                    if repaired_any:
                        host_actions["user_surfaces"] = "fixed"
            except Exception as exc:
                host_actions["user_surfaces"] = f"failed: {exc}"

            try:
                if (
                    check_skill
                    and IntegrationManager.requires_skill(target)
                    and "skill" in missing
                    and not contract_needs_repair
                ):
                    skill_manager.install(
                        source="super-dev",
                        target=target,
                        name=effective_skill_name,
                        force=force,
                    )
                    host_actions["skill"] = "fixed"
            except Exception as exc:
                host_actions["skill"] = f"failed: {exc}"

            try:
                if (
                    check_slash
                    and integration_manager.supports_slash(target)
                    and not contract_needs_repair
                ):
                    integration_manager.setup_slash_command(target=target, force=force)
                    if include_user_surfaces:
                        integration_manager.setup_global_slash_command(target=target, force=force)
                    if "slash" in missing:
                        host_actions["slash"] = "fixed"
            except Exception as exc:
                host_actions["slash"] = f"failed: {exc}"

            if host_actions:
                actions[target] = host_actions

        return actions

    _HOST_FAMILIES: list[tuple[str, str]] = [
        ("cursor-cli", "cursor"),
        ("kiro-cli", "kiro"),
        ("qoder-cli", "qoder"),
        ("codebuddy-cli", "codebuddy"),
    ]
