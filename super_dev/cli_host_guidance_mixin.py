"""Host selection, usage guidance and report output."""

from pathlib import Path
from typing import Any, cast

from .catalogs import (
    host_path_override_guide,
)
from .cli_host_report_renderers import (
    render_host_compatibility_markdown,
    render_host_hardening_markdown,
    render_host_parity_onepage_markdown,
    render_host_runtime_validation_markdown,
    render_host_surface_audit_markdown,
    write_host_compatibility_report,
    write_host_hardening_report,
    write_host_runtime_validation_report,
    write_host_surface_audit_report,
)
from .config import ConfigManager
from .host_entry_decisions import (
    build_detected_host_decision_card,
    build_host_start_guidance,
    build_no_host_decision_card,
    build_primary_repair_action,
    host_selection_reason,
    rank_host_targets,
)
from .host_experience_profile import (
    build_host_competition_first_prompt,
    build_host_post_onboard_self_check,
    build_host_standard_first_prompt,
)
from .host_runtime_validation import (
    build_host_runtime_validation_payload,
    build_runtime_evidence_record,
    host_runtime_status_label,
    load_host_runtime_validation_state,
    update_host_runtime_validation_state,
)
from .host_session_resume import build_session_resume_card
from .host_usage_profile import serialize_host_usage_profile
from .host_workflow_context import build_host_workflow_context
from .workflow_state import (
    detect_flow_variant,
)


class CliHostGuidanceMixin:
    def _is_version_newer(self, latest: str, current: str) -> bool:
        return self._version_key(latest) > self._version_key(current)

    def _version_key(self, version: str) -> tuple[int, ...]:
        parts = []
        for part in version.replace("-", ".").split("."):
            digits = "".join(ch for ch in part if ch.isdigit())
            parts.append(int(digits or 0))
        return tuple(parts)

    def _print_host_usage_guidance(
        self,
        *,
        integration_manager,
        target: str,
        indent: str = "",
    ) -> None:
        usage = self._build_host_usage_profile(
            integration_manager=integration_manager,
            target=target,
        )
        self.console.print(f"{indent}[cyan]主入口[/cyan]: {usage['primary_entry']}")
        self.console.print(
            f"{indent}认证等级: {usage['certification_label']} ({usage['certification_level']})"
        )
        self.console.print(f"{indent}使用模式: {usage['usage_mode']}")
        adaptation = usage.get("adaptation_contract", {})
        if isinstance(adaptation, dict) and adaptation:
            score = adaptation.get("score", 0)
            level = adaptation.get("level", "")
            self.console.print(f"{indent}适配成熟度: {score}/100 ({level})")
            official_alignment = adaptation.get("official_alignment", {})
            if isinstance(official_alignment, dict) and official_alignment:
                alignment_label = str(official_alignment.get("label", "")).strip()
                alignment_summary = str(official_alignment.get("summary", "")).strip()
                if alignment_label or alignment_summary:
                    text = " / ".join(item for item in [alignment_label, alignment_summary] if item)
                    self.console.print(f"{indent}官方对齐: {text}")
            dimensions = adaptation.get("dimensions", {})
            if isinstance(dimensions, dict) and dimensions:
                dimension_summary = ", ".join(
                    f"{name}={str(info.get('status', 'missing')).strip()}"
                    for name, info in dimensions.items()
                    if isinstance(info, dict)
                )
                if dimension_summary:
                    self.console.print(f"{indent}适配维度: {dimension_summary}")
                gaps = [
                    str(gap).strip()
                    for info in dimensions.values()
                    if isinstance(info, dict)
                    for gap in info.get("gaps", [])
                    if str(gap).strip()
                ]
                if gaps:
                    self.console.print(f"{indent}主要缺口: {'; '.join(gaps[:3])}")
        experience = usage.get("experience_profile", {})
        if isinstance(experience, dict) and experience:
            self.console.print(
                f"{indent}宿主画像: {experience.get('label', '-')} / {experience.get('best_for', '-')}"
            )
            resume_style = str(experience.get("resume_style", "")).strip()
            if resume_style:
                self.console.print(f"{indent}恢复风格: {resume_style}")
            strengths = experience.get("strengths", [])
            if isinstance(strengths, list) and strengths:
                self.console.print(
                    f"{indent}宿主强项: {' / '.join(str(item) for item in strengths[:3])}"
                )
            preferred_entries = experience.get("preferred_entries", [])
            if isinstance(preferred_entries, list) and preferred_entries:
                self.console.print(
                    f"{indent}推荐入口变体: {' / '.join(str(item) for item in preferred_entries[:2])}"
                )
            native_resume = experience.get("native_resume", [])
            if isinstance(native_resume, list) and native_resume:
                self.console.print(
                    f"{indent}推荐恢复方式: {' / '.join(str(item) for item in native_resume[:2])}"
                )
        protocol_mode = str(usage.get("host_protocol_mode", "")).strip()
        protocol_summary = str(usage.get("host_protocol_summary", "")).strip()
        if protocol_mode or protocol_summary:
            protocol_text = protocol_summary or protocol_mode
            if protocol_mode and protocol_summary and protocol_mode != protocol_summary:
                protocol_text = f"{protocol_summary} ({protocol_mode})"
            self.console.print(f"{indent}宿主协议: {protocol_text}")
        self.console.print(f"{indent}触发命令: {usage['trigger_command']}")
        self.console.print(f"{indent}触发上下文: {usage['trigger_context']}")
        self.console.print(f"{indent}触发位置: {usage['usage_location']}")
        self.console.print(f"{indent}接入后重启: {usage['restart_required_label']}")
        precondition_label = usage.get("precondition_label", "")
        if isinstance(precondition_label, str) and precondition_label.strip():
            self.console.print(f"{indent}宿主前置条件: {precondition_label}")
        precondition_items = usage.get("precondition_items", [])
        if isinstance(precondition_items, list) and precondition_items:
            self.console.print(f"{indent}前置条件项:")
            for item in precondition_items:
                if not isinstance(item, dict):
                    continue
                item_label = str(item.get("label", "")).strip()
                item_status = str(item.get("status", "")).strip()
                item_text = item_label or item_status
                if item_text:
                    self.console.print(f"{indent}  - {item_text}")
        precondition_guidance = usage.get("precondition_guidance", [])
        if isinstance(precondition_guidance, list) and precondition_guidance:
            self.console.print(f"{indent}前置条件说明:")
            for item in precondition_guidance:
                self.console.print(f"{indent}  - {item}")
        if usage.get("certification_reason"):
            self.console.print(f"{indent}认证说明: {usage['certification_reason']}")
        official_project = usage.get("official_project_surfaces", [])
        if isinstance(official_project, list) and official_project:
            self.console.print(f"{indent}官方项目级接入面:")
            for item in official_project:
                self.console.print(f"{indent}  - {item}")
        official_user = usage.get("official_user_surfaces", [])
        if isinstance(official_user, list) and official_user:
            self.console.print(f"{indent}默认用户级 Skill 面:")
            for item in official_user:
                self.console.print(f"{indent}  - {item}")
        optional_project = usage.get("optional_project_surfaces", [])
        if isinstance(optional_project, list) and optional_project:
            self.console.print(f"{indent}可选项目增强面:")
            for item in optional_project:
                self.console.print(f"{indent}  - {item}")
        optional_user = usage.get("optional_user_surfaces", [])
        if isinstance(optional_user, list) and optional_user:
            self.console.print(f"{indent}显式用户级增强面 (--with-user-surfaces):")
            for item in optional_user:
                self.console.print(f"{indent}  - {item}")
        observed_surfaces = usage.get("observed_compatibility_surfaces", [])
        if isinstance(observed_surfaces, list) and observed_surfaces:
            self.console.print(f"{indent}兼容增强路径:")
            for item in observed_surfaces:
                self.console.print(f"{indent}  - {item}")
        steps = usage.get("post_onboard_steps", [])
        if isinstance(steps, list) and steps:
            self.console.print(f"{indent}接入后步骤:")
            for step in steps:
                self.console.print(f"{indent}  - {step}")
        notes = usage.get("usage_notes", [])
        if isinstance(notes, list) and notes:
            self.console.print(f"{indent}使用提示:")
            for note in notes:
                self.console.print(f"{indent}  - {note}")
        smoke_prompt = usage.get("smoke_test_prompt", "")
        if isinstance(smoke_prompt, str) and smoke_prompt:
            self.console.print(f"{indent}冒烟验证语句: {smoke_prompt}")
        smoke_steps = usage.get("smoke_test_steps", [])
        if isinstance(smoke_steps, list) and smoke_steps:
            self.console.print(f"{indent}冒烟验证步骤:")
            for step in smoke_steps:
                self.console.print(f"{indent}  - {step}")
        smoke_signal = usage.get("smoke_success_signal", "")
        if isinstance(smoke_signal, str) and smoke_signal:
            self.console.print(f"{indent}冒烟验证通过标准: {smoke_signal}")

    def _host_certification_rank(self, level: str) -> int:
        order = {"certified": 0, "compatible": 1, "experimental": 2}
        return order.get(level, 3)

    def _host_selection_sort_key(
        self, *, integration_manager, target: str
    ) -> tuple[int, int, int, str]:
        profile = integration_manager.get_adapter_profile(target)
        return (
            self._host_certification_rank(profile.certification_level),
            0 if integration_manager.supports_slash(target) else 1,
            0 if profile.category == "cli" else 1,
            target,
        )

    def _rank_host_targets(self, *, integration_manager, targets: list[str]) -> list[str]:
        return rank_host_targets(integration_manager=integration_manager, targets=targets)

    def _select_best_start_host(self, *, integration_manager, targets: list[str]) -> str:
        deduplicated = self._deduplicate_host_family(targets)
        return self._rank_host_targets(
            integration_manager=integration_manager,
            targets=deduplicated,
        )[0]

    def _recommended_start_hosts(self, *, integration_manager) -> list[dict[str, str]]:
        from .integrations import IntegrationManager

        items: list[dict[str, str]] = []
        for target in sorted(IntegrationManager.TARGETS):
            profile = integration_manager.get_adapter_profile(target)
            if profile.certification_level != "certified":
                continue
            items.append(
                {
                    "id": target,
                    "name": self._host_label(target),
                    "certification_label": profile.certification_label,
                    "path_override_env": str(host_path_override_guide(target).get("env_key", "")),
                }
            )
        return items

    def _build_no_host_decision_card(self, *, integration_manager) -> dict[str, Any]:
        recommended_hosts = self._recommended_start_hosts(integration_manager=integration_manager)
        action_examples = ["先装 Codex", "我先用 Claude Code", "先把宿主接好再开始"]
        next_actions = [
            "先安装一个受支持宿主，优先 Claude Code 或 Codex。",
            "如果宿主装在自定义目录，先设置对应的 SUPER_DEV_HOST_PATH_* 环境变量。",
            "安装后重新运行 super-dev，完成接入后直接回宿主里触发 /super-dev 或 super-dev:。",
        ]
        first_action = next_actions[0]
        return build_no_host_decision_card(
            workflow_mode_label=self._workflow_mode_label("start"),
            action_examples=action_examples,
            first_action=first_action,
            secondary_actions=next_actions[1:],
            path_override_hint=self._custom_host_path_override_hint(),
            path_override_examples=[
                {
                    "id": item["id"],
                    "name": item["name"],
                    "env_key": str(host_path_override_guide(item["id"]).get("env_key", "")),
                    "unix_example": str(
                        host_path_override_guide(item["id"]).get("unix_example", "")
                    ),
                    "windows_example": str(
                        host_path_override_guide(item["id"]).get("windows_example", "")
                    ),
                }
                for item in recommended_hosts[:2]
            ],
            recommended_hosts=recommended_hosts,
            lines=[
                f"先做这一步: {first_action}",
                "当前机器上未命中受支持宿主。",
                self._custom_host_path_override_hint(),
                "优先安装 Claude Code 或 Codex；接入完成后普通开发直接回宿主，不要停留在终端维护命令里。",
            ],
        )

    def _host_selection_reason(self, *, integration_manager, target: str) -> str:
        return host_selection_reason(integration_manager=integration_manager, target=target)

    def _build_detected_host_decision_card(
        self,
        *,
        project_dir: Path,
        integration_manager,
        detected_targets: list[str],
        detected_meta: dict[str, list[str]],
        preferred_targets: list[str] | None = None,
    ) -> dict[str, Any]:
        return build_detected_host_decision_card(
            project_dir=project_dir,
            integration_manager=integration_manager,
            detected_targets=detected_targets,
            detected_meta=detected_meta,
            preferred_targets=preferred_targets,
            usage_profile_fn=lambda target: self._build_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            ),
            session_resume_card_fn=(
                lambda current_project_dir, target: self._build_session_resume_card(
                    project_dir=current_project_dir,
                    target=target,
                )
            ),
            explain_detection_details_fn=self._explain_detection_details,
            workflow_mode_label_fn=self._workflow_mode_label,
            candidate_trigger_fn=lambda target, usage, _profile: build_host_start_guidance(
                target=target,
                usage=usage,
                include_resume_hint=False,
            ),
            first_action_fn=(
                lambda target, usage, profile, session_resume_card: (
                    str(
                        session_resume_card.get("workflow_context", {}).get(
                            "recommended_host_action", ""
                        )
                    ).strip()
                    if session_resume_card.get("enabled")
                    and isinstance(session_resume_card.get("workflow_context", {}), dict)
                    and str(
                        session_resume_card.get("workflow_context", {}).get("blocking_gate", "")
                    ).strip()
                    in {
                        "waiting_baseline_confirmation",
                        "missing_baseline",
                        "waiting_resume_gate",
                    }
                    and str(
                        session_resume_card.get("workflow_context", {}).get(
                            "recommended_host_action", ""
                        )
                    ).strip()
                    else (
                        f"重开后第一句直接复制 {session_resume_card.get('host_first_sentence')}"
                        if session_resume_card.get("enabled")
                        else build_host_start_guidance(
                            target=target,
                            usage=usage,
                            include_resume_hint=False,
                        )
                    )
                )
            ),
            first_suggestion_text_fn=lambda _selected_host, candidates: str(
                candidates[0]["trigger"]
            ),
            default_action_examples=[
                "在宿主里开始这个项目",
                "在宿主里说“继续当前流程”",
                "在宿主里说“现在下一步是什么”",
            ],
            no_host_card_fn=lambda: self._build_no_host_decision_card(
                integration_manager=integration_manager
            ),
        )

    def _build_primary_repair_action(
        self,
        *,
        report: dict[str, Any],
        targets: list[str],
        decision_card: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from .integrations import IntegrationManager

        integration_manager = IntegrationManager(Path.cwd())
        action = build_primary_repair_action(
            report=report,
            targets=targets,
            host_label_fn=self._host_label,
            usage_profile_fn=(
                lambda target: self._build_host_usage_profile(
                    integration_manager=integration_manager,
                    target=target,
                )
            ),
            decision_card=decision_card,
        )
        if action.get("command"):
            return action
        runtime_health = report.get("runtime_install_health", {})
        if isinstance(runtime_health, dict) and not bool(runtime_health.get("healthy", True)):
            remediation = runtime_health.get("remediation", [])
            primary = ""
            secondary_actions: list[str] = []
            if isinstance(remediation, list):
                for item in remediation:
                    text = str(item).strip()
                    if not text:
                        continue
                    if not primary:
                        primary = text
                    elif text not in secondary_actions:
                        secondary_actions.append(text)
                    if len(secondary_actions) >= 2:
                        break
            if primary:
                warnings = runtime_health.get("warnings", [])
                reason = ""
                if isinstance(warnings, list):
                    reason = "；".join(str(item).strip() for item in warnings if str(item).strip())
                return {
                    "host": "当前运行时",
                    "reason": reason,
                    "command": primary,
                    "secondary_actions": secondary_actions,
                }
        return {"host": "", "reason": "", "command": "", "secondary_actions": []}

    def _build_host_trigger_example(self, *, target: str, idea: str | None) -> str:
        from .integrations import IntegrationManager

        if not idea:
            return ""
        if target == "codex":
            return f"/super-dev {idea}"
        if target == "codex-cli":
            return f"/super-dev {idea}"
        if target == "trae":
            return f"{IntegrationManager.TEXT_TRIGGER_PREFIX} {idea}"
        if IntegrationManager.supports_slash(target):
            return f"/super-dev {idea}"
        return f"{IntegrationManager.TEXT_TRIGGER_PREFIX} {idea}"

    def _build_onboard_next_steps(self, *, targets: list[str]) -> list[str]:
        from .integrations import IntegrationManager

        project_dir = Path.cwd()
        integration_manager = IntegrationManager(project_dir)
        lines: list[str] = []
        for target in targets:
            profile = integration_manager.get_adapter_profile(target)
            usage = self._build_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            )
            session_hint = self._build_workflow_session_hint(project_dir=project_dir, target=target)
            continue_prompt = str(session_hint.get("continue_prompt", "") or "").strip()
            continue_mode = str(session_hint.get("session_mode", "") or "") == "continue_super_dev"
            if continue_mode and continue_prompt:
                line = f"{self._host_label(target)}: 重开后第一句直接复制 {continue_prompt}"
            else:
                standard_prompt = build_host_standard_first_prompt(target)
                competition_prompt = build_host_competition_first_prompt(target)
                self_check = build_host_post_onboard_self_check(target, usage)
                prompt_summary = (
                    f"标准流第一句：{standard_prompt}；比赛流第一句：{competition_prompt}"
                )
                if self_check:
                    line = (
                        f"{self._host_label(target)}: 回宿主到 {usage.get('trigger_context', '-')}；"
                        f"{prompt_summary}；先做：{' / '.join(self_check[:2])}；"
                        "再按冒烟验证指南检查"
                    )
                else:
                    line = (
                        f"{self._host_label(target)}: 回宿主到 {usage.get('trigger_context', '-')}；"
                        f"{prompt_summary}；再按冒烟验证指南检查"
                    )
            if profile.requires_restart_after_onboard:
                line += "（先重启宿主）"
            lines.append(line)
        return lines

    def _build_session_resume_card_lines(self, *, project_dir: Path, target: str) -> list[str]:
        card = self._build_session_resume_card(project_dir=project_dir, target=target)
        lines = card.get("lines", []) if isinstance(card, dict) else []
        return [str(line) for line in lines] if isinstance(lines, list) else []

    def _build_session_resume_card(self, *, project_dir: Path, target: str) -> dict[str, Any]:
        session_hint = self._build_workflow_session_hint(project_dir=project_dir, target=target)
        continue_prompt = str(session_hint.get("continue_prompt", "") or "").strip()
        continue_instruction = str(session_hint.get("continue_instruction", "") or "").strip()
        continue_mode = str(session_hint.get("session_mode", "") or "") == "continue_super_dev"
        enabled = bool(continue_mode and continue_prompt)
        workflow_mode = str(session_hint.get("workflow_mode", "") or "").strip()
        workflow_context = (
            dict(session_hint.get("workflow_context", {}))
            if isinstance(session_hint.get("workflow_context", {}), dict)
            else (
                build_host_workflow_context(
                    project_dir,
                    entry_mode="continue" if continue_mode else "start",
                    target=target,
                )
                if enabled
                else {}
            )
        )
        return build_session_resume_card(
            project_dir=project_dir,
            target=target,
            enabled=enabled,
            host_first_sentence=continue_prompt,
            line_host_first_sentence=continue_prompt,
            continue_instruction=continue_instruction or continue_prompt,
            workflow_mode=workflow_mode,
            workflow_mode_label=self._workflow_mode_label(workflow_mode) if workflow_mode else "",
            action_title=str(session_hint.get("action_title", "") or "").strip(),
            action_examples=(
                session_hint.get("action_examples")
                if isinstance(session_hint.get("action_examples"), list)
                else []
            ),
            user_action_shortcuts=(
                session_hint.get("user_action_shortcuts")
                if isinstance(session_hint.get("user_action_shortcuts"), list)
                else []
            ),
            scenario_cards=(
                session_hint.get("scenario_cards")
                if isinstance(session_hint.get("scenario_cards"), list)
                else []
            ),
            specific_rules=(
                session_hint.get("continuity_rules")
                if isinstance(session_hint.get("continuity_rules"), list)
                else []
            ),
            recommended_workflow_command=str(
                session_hint.get("recommended_workflow_command", "") or ""
            ).strip(),
            supports_slash=self._supports_slash_for_prompt(target),
            flow_variant=detect_flow_variant(project_dir),
            workflow_context=workflow_context,
            include_entry_prompt_lines=True,
            prefer_payload_entry_prompt=True,
        )

    def _build_host_quick_start_text(
        self,
        *,
        host_profile: dict[str, Any],
        host_id: str,
        host_name: str,
        idea: str | None,
        session_hint: dict[str, Any] | None = None,
        framework_playbook: dict[str, Any] | None = None,
    ) -> str:
        trigger_text = self._build_host_trigger_example(target=host_id, idea=idea)
        if not trigger_text:
            trigger_text = str(
                host_profile.get("final_trigger", "") or host_profile.get("primary_entry", "-")
            )
        experience = (
            dict(host_profile.get("experience_profile", {}))
            if isinstance(host_profile.get("experience_profile", {}), dict)
            else {}
        )
        preferred_entries = [
            str(item).strip()
            for item in experience.get("preferred_entries", [])
            if str(item).strip()
        ]
        native_resume = [
            str(item).strip() for item in experience.get("native_resume", []) if str(item).strip()
        ]
        if host_id == "codex":
            trigger_text = (
                "App/Desktop 从 `/` 列表选 super-dev；自然语言回退是 `super-dev: 你的需求`"
            )
        elif host_id == "codex-cli":
            trigger_text = "App/Desktop 从 `/` 列表选 super-dev；CLI 输入 `$super-dev`；自然语言回退是 `super-dev: 你的需求`"
        elif host_id == "claude-code":
            trigger_text = "优先 `/super-dev 你的需求`；需要文本回退时用 `super-dev: 你的需求`"
        elif host_id == "kimi-code":
            trigger_text = "优先 `/skill:super-dev 你的需求`；也可 `/flow:super-dev 你的需求`；文本回退是 `super-dev: 你的需求`"
        elif host_id == "droid-cli":
            trigger_text = '优先 `/super-dev 你的需求`；headless 续跑用 `droid exec --session-id <id> "continue with next steps"`；文本回退是 `super-dev: 你的需求`'
        elif host_id == "trae-solo":
            trigger_text = "当前工作区优先 `/super-dev 你的需求`；文本回退是 `super-dev: 你的需求`"
        elif host_id == "trae-solocn":
            trigger_text = (
                "当前工作区优先 `super-dev: 你的需求`；比赛模式用 `super-dev-seeai: 比赛需求`"
            )
        session_hint = session_hint or {}
        continue_prompt = str(session_hint.get("continue_prompt", "") or "").strip()
        continue_mode = str(session_hint.get("session_mode", "") or "") == "continue_super_dev"
        workflow_reason = str(session_hint.get("workflow_reason", "") or "").strip()
        recommended_workflow_command = str(
            session_hint.get("recommended_workflow_command", "") or ""
        ).strip()
        standard_first_prompt = build_host_standard_first_prompt(host_id)
        competition_first_prompt = build_host_competition_first_prompt(host_id)
        framework_playbook = (
            dict(framework_playbook) if isinstance(framework_playbook, dict) else {}
        )
        framework_name = str(framework_playbook.get("framework", "")).strip()
        framework_validation = (
            list(framework_playbook.get("validation_surfaces", []))
            if isinstance(framework_playbook.get("validation_surfaces", []), list)
            else []
        )
        framework_evidence = (
            list(framework_playbook.get("delivery_evidence", []))
            if isinstance(framework_playbook.get("delivery_evidence", []), list)
            else []
        )

        if host_id in {
            "codex",
            "codex-cli",
            "opencode",
            "claude-code",
            "kimi-code",
            "droid-cli",
            "trae-solo",
            "trae-solocn",
        }:
            entry_variants = host_profile.get("entry_variants", [])
            variant_lines: list[str] = []
            if host_id in {"codex", "codex-cli"} and isinstance(entry_variants, list):
                for item in entry_variants:
                    if not isinstance(item, dict):
                        continue
                    label = str(item.get("label", "")).strip()
                    entry = str(item.get("entry", "")).strip()
                    notes = str(item.get("notes", "")).strip()
                    if not label or not entry:
                        continue
                    line = f"{label}: {entry}"
                    if notes:
                        line += f"；{notes}"
                    variant_lines.append(line)
            if preferred_entries:
                variant_lines.extend(f"推荐入口: {entry}" for entry in preferred_entries[:3])
            if continue_mode and native_resume:
                variant_lines.extend(f"恢复方式: {entry}" for entry in native_resume[:2])
            lines = [
                f"{host_name} 最短路径",
                "",
                "终端到此为止，真正开发回到宿主里。",
                (
                    "当前会话目标：继续仓库里已有的 Super Dev 流程"
                    if continue_mode
                    else "当前会话目标：启动一次新的 Super Dev 流程"
                ),
                "",
                "现在只做这四步",
                f"1. 进入这里：{host_profile.get('trigger_context', '-')}",
                (
                    f"2. 重开宿主后第一句直接复制：{continue_prompt}"
                    if continue_mode and continue_prompt
                    else f"2. 直接复制第一句：{trigger_text}"
                ),
                "3. 先看冒烟验证指南；如果其中有框架重点、必验场景和交付证据，先按它执行",
                "4. 按冒烟验证指南检查，确认宿主进入 research -> 三文档 -> 等待确认",
                "",
                f"标准流第一句：{standard_first_prompt}",
                f"比赛流第一句：{competition_first_prompt}",
                "已有项目先 baseline，并确认 baseline 后再继续；窗口关闭或第二天回来时默认先 resume。",
            ]
            if framework_name:
                lines.extend(
                    [
                        "",
                        f"当前项目框架焦点：{framework_name}",
                    ]
                )
                if framework_validation:
                    lines.append(
                        "必验场景：" + "；".join(str(item) for item in framework_validation[:4])
                    )
                if framework_evidence:
                    lines.append(
                        "交付证据：" + "；".join(str(item) for item in framework_evidence[:4])
                    )
            lines.extend(
                [
                    "验收重点：先看框架重点，再按冒烟验证指南中的必验场景走一遍。",
                    "只有宿主真的进入 research -> 三文档 -> 等待确认，才算接入成功。",
                ]
            )
            if variant_lines:
                lines.extend(["", "官方入口"])
                lines.extend(f"- {line}" for line in variant_lines)
            if continue_mode:
                lines.extend(
                    [
                        "流程状态卡：.super-dev/SESSION_BRIEF.md",
                        "继续规则：用户继续修改、补充或确认时，仍留在当前 Super Dev 流程。",
                        "退出条件：只有用户明确说取消当前流程、重新开始或切回普通聊天，才允许离开流程。",
                    ]
                )
            lines.extend(
                [
                    "",
                    "成功标志",
                    "1. 第一轮回复明确说当前阶段是 research",
                    "2. 会先读 knowledge/ 与 knowledge bundle，再做同类产品研究",
                    "3. 三份核心文档完成后会停下来等你确认",
                ]
            )
            if continue_mode and workflow_reason:
                lines.extend(["", f"当前流程说明：{workflow_reason}"])
            if continue_mode and recommended_workflow_command:
                lines.extend(["", f"机器侧对应动作：{recommended_workflow_command}"])
            priority_notes = self._build_host_priority_notes(host_id=host_id)
            if priority_notes:
                lines.extend(["", "最关键的提醒"])
                for index, note in enumerate(priority_notes, start=1):
                    lines.append(f"{index}. {note}")
            lines.extend(
                [
                    "",
                    "如果没进入正确流程，再回终端",
                    f"super-dev setup --host {host_id} --force --yes",
                    f"super-dev doctor --host {host_id} --repair --force",
                ]
            )
            return "\n".join(lines)

        lines = [
            f"{host_name} 最短路径",
            "",
            "终端到此为止，真正开发回到宿主里。",
            (
                "当前会话目标：继续已有流程"
                if continue_mode
                else "当前会话目标：启动新的 Super Dev 流程"
            ),
            "",
            "现在只做这四步",
            "1. 确认当前会话就在目标项目里。",
            f"2. {'先重启宿主，再' if host_profile.get('restart_required_label', '-') == '是' else ''}打开正确入口：{host_profile.get('trigger_context', '-')}",
            f"3. {'重开宿主后第一句直接复制' if continue_mode and continue_prompt else '直接复制第一句'}：{continue_prompt if continue_mode and continue_prompt else trigger_text}",
            "4. 先看冒烟验证指南；如果其中有框架重点、必验场景和交付证据，先按它执行",
            "",
            f"标准流第一句：{standard_first_prompt}",
            f"比赛流第一句：{competition_first_prompt}",
            "已有项目先 baseline，并确认 baseline 后再继续；窗口关闭或第二天回来时默认先 resume。",
        ]
        next_index = 5
        if framework_name:
            lines.append(f"{next_index}. 当前项目框架焦点：{framework_name}")
            next_index += 1
            lines.append(
                (
                    f"{next_index}. 必验场景："
                    + "；".join(str(item) for item in framework_validation[:4])
                )
                if framework_validation
                else f"{next_index}. 必验场景：按宿主冒烟验证指南和框架重点执行。"
            )
            next_index += 1
            if framework_evidence:
                lines.append(
                    f"{next_index}. 交付证据："
                    + "；".join(str(item) for item in framework_evidence[:4])
                )
                next_index += 1
        lines.extend(
            [
                f"{next_index}. 验收重点：按冒烟验证指南确认宿主进入 research -> 三文档 -> 等待确认。",
                f"{next_index + 1}. 只有这条主线成立，才开始真实需求。",
            ]
        )
        next_index += 2
        if continue_mode:
            lines.extend(
                [
                    f"{next_index}. 流程状态卡：.super-dev/SESSION_BRIEF.md",
                    f"{next_index + 1}. 用户继续修改、补充或确认时，仍留在当前 Super Dev 流程。",
                    f"{next_index + 2}. 只有用户明确说取消当前流程、重新开始或切回普通聊天，才允许离开流程。",
                ]
            )
        lines.extend(
            [
                "",
                "看到下面两点就算接入成功：",
                "1. 第一轮回复明确说当前阶段是 research",
                "2. 会先读 knowledge/ 与 knowledge bundle，再做同类产品研究",
                "3. 三份核心文档完成后会停下来等你确认",
                "",
                f"认证等级：{host_profile.get('certification_label', '-')}"
                f" ({host_profile.get('certification_level', '-')})",
                f"主入口：{host_profile.get('primary_entry', '-')}",
                f"使用模式：{host_profile.get('usage_mode', '-')}",
            ]
        )
        priority_notes = self._build_host_priority_notes(host_id=host_id)
        if priority_notes:
            lines.extend(["", "这个宿主最关键的提醒"])
            for index, note in enumerate(priority_notes, start=1):
                lines.append(f"{index}. {note}")
        reason = host_profile.get("certification_reason", "")
        if isinstance(reason, str) and reason.strip():
            lines.extend(["", "为什么推荐这个宿主", reason])
        if continue_mode and workflow_reason:
            lines.extend(["", "当前流程说明", workflow_reason])
        if continue_mode and recommended_workflow_command:
            lines.extend(["", f"机器侧对应动作：{recommended_workflow_command}"])
        steps = host_profile.get("post_onboard_steps", [])
        if isinstance(steps, list) and steps:
            lines.extend(["", "如果还是没生效，按这个顺序排查"])
            for index, step in enumerate(steps, start=1):
                lines.append(f"{index}. {step}")
        lines.extend(
            [
                "",
                "如果没进入正确流程，再回终端",
                f"super-dev setup --host {host_id} --force --yes",
                f"super-dev doctor --host {host_id} --repair --force",
            ]
        )
        return "\n".join(lines)

    def _build_host_priority_notes(self, *, host_id: str) -> list[str]:
        if host_id == "codex":
            return [
                "Codex App/Desktop 优先从 `/` 列表选择 `super-dev`；这是已启用 Skill 的官方入口。",
                "如果你已经在自然语言上下文里继续当前流程，也可以直接输入 `super-dev: 你的需求`。",
                "接入完成后建议彻底重开 Codex App/Desktop，会话才会重新加载 AGENTS.md 和 Skill。",
                "先确认当前会话已经绑定到目标项目，再开始新流程。",
            ]
        if host_id == "codex-cli":
            return [
                "Codex App/Desktop 优先从 `/` 列表选择 `super-dev`；这是已启用 Skill 的官方入口。",
                "Codex CLI 优先显式输入 `$super-dev`。",
                "如果你已经在自然语言上下文里继续当前流程，也可以直接输入 `super-dev: 你的需求`。",
                "接入完成后必须彻底重开 `codex`，旧会话不会重新加载 AGENTS.md 和 Skill。",
                "先确认当前终端就在目标项目目录里，再开始新会话。",
            ]
        if host_id == "claude-code":
            return [
                "Claude Code 优先直接用 `/super-dev`，不要先普通聊天开题。",
                "如果 slash 刷新异常，再回退到 `super-dev: 你的需求`。",
                "重开窗口后先说“继续当前流程”，不要重新描述项目背景。",
            ]
        if host_id == "kimi-code":
            return [
                "Kimi Code 优先走 `/skill:super-dev`，这样最稳定。",
                "如果你在 Flow 入口里组织多阶段工作，可以改用 `/flow:super-dev`。",
                "中断恢复优先 `kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume`，再回到当前流程。",
            ]
        if host_id == "droid-cli":
            return [
                "Droid CLI 优先在当前 session 用 `/super-dev` 开始，不要先普通对话探路。",
                '需要 headless 续跑时，优先 `droid exec --session-id <id> "continue with next steps"`。',
                "Factory rules / skills 更新后，先重开当前 session 再继续；`.factory/commands/` 只作为 legacy compatibility 排查。",
            ]
        if host_id == "trae-solo":
            return [
                "Trae SOLO 优先在当前 workspace 用 `/super-dev` 开题。",
                "确保当前 workspace 就是目标项目，别在错误目录里继续流程。",
                "slash 和文本回退都要汇入同一条 Super Dev 流程，不要分成两套会话。",
            ]
        if host_id == "trae-solocn":
            return [
                "Trae SOLOCN 当前默认以自然语言入口 `super-dev:` 最稳。",
                "如果你在用内建 `/plan` / `/spec`，要确保它们仍围绕同一条 Super Dev 流程服务。",
                "恢复时先回当前工作区，再说“继续当前流程”，不要重新开题。",
            ]
        if host_id == "opencode":
            return [
                "直接在 OpenCode 会话里输入 `/super-dev 你的需求`。",
                "通常不需要重启；如果命令列表没有刷新，关掉当前会话再重开一次。",
                "优先保留项目级 `.opencode/commands/super-dev.md`，不要只依赖全局命令目录。",
            ]
        return []

    def _build_host_usage_profile(
        self,
        *,
        integration_manager,
        target: str,
    ) -> dict[str, Any]:
        profile = integration_manager.get_adapter_profile(target)
        return serialize_host_usage_profile(
            profile=profile,
            target=target,
            final_trigger=self._display_final_trigger_for_profile(profile),
            managed_competition_project_surfaces=integration_manager.managed_competition_project_surfaces(
                target
            ),
            managed_competition_user_surfaces=integration_manager.managed_competition_user_surfaces(
                target
            ),
            host_value=self._host_label(profile.host),
            include_host_id=True,
            include_capability_labels=True,
            include_docs_fields=True,
            skill_slash_entry_host_id=profile.host,
            skill_slash_entry_note=(
                "表示 Codex App/Desktop `/` 列表里的已启用 Skill 入口，不代表项目支持自定义 slash 文件。"
            ),
            flow_host_id=profile.host,
        )

    def _load_host_runtime_validation_state(self, *, project_dir: Path) -> dict[str, Any]:
        return load_host_runtime_validation_state(project_dir=project_dir)

    def _host_runtime_status_label(self, status: str) -> str:
        return host_runtime_status_label(status)

    def _build_runtime_evidence_record(
        self,
        *,
        host_id: str,
        surface_ready: bool,
        runtime_entry: dict[str, Any],
    ) -> dict[str, Any]:
        return build_runtime_evidence_record(
            host_id=host_id,
            surface_ready=surface_ready,
            runtime_entry=runtime_entry,
        )

    def _update_host_runtime_validation_state(
        self,
        *,
        project_dir: Path,
        target: str,
        status: str,
        comment: str,
        actor: str,
        competition_evidence: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Path]:
        return update_host_runtime_validation_state(
            project_dir=project_dir,
            host=target,
            status=status,
            comment=comment,
            actor=actor,
            competition_evidence=competition_evidence,
        )

    def _resolve_report_project_name(self, project_dir: Path) -> str:
        try:
            config = ConfigManager(project_dir).load()
            raw = config.name or project_dir.name
        except Exception:
            raw = project_dir.name
        return str(self._sanitize_project_name(raw))

    def _render_host_compatibility_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_compatibility_markdown(payload, host_label_fn=self._host_label)

    def _render_host_surface_audit_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_surface_audit_markdown(payload, host_label_fn=self._host_label)

    def _build_host_runtime_validation_payload(
        self,
        *,
        project_dir: Path,
        targets: list[str],
        detected_meta: dict[str, list[str]],
        report: dict[str, Any],
        usage_profiles: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return build_host_runtime_validation_payload(
            project_dir=project_dir,
            targets=targets,
            detected_meta=detected_meta,
            report=report,
            usage_profiles=usage_profiles,
            explain_detection_details_fn=self._explain_detection_details,
            runtime_checklist_fn=(
                lambda target, usage, project_dir: self._host_runtime_checklist(
                    target=target,
                    usage=usage,
                    project_dir=project_dir,
                )
            ),
            pass_criteria_fn=(
                lambda target, usage, project_dir: self._host_runtime_pass_criteria(
                    target=target,
                    usage=usage,
                    project_dir=project_dir,
                )
            ),
            resume_probe_prompt_fn=(
                lambda target, usage, project_dir: self._host_resume_probe_prompt(
                    project_dir=project_dir,
                    target=target,
                )
            ),
            resume_checklist_fn=(
                lambda target, project_dir: self._host_resume_checklist(
                    target=target,
                    project_dir=project_dir,
                )
            ),
            entry_enricher_fn=(
                lambda target, host, usage, runtime_entry: {
                    "checks": (
                        host.get("checks", {}) if isinstance(host.get("checks", {}), dict) else {}
                    ),
                }
            ),
        )

    def _render_host_runtime_validation_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_runtime_validation_markdown(payload, host_label_fn=self._host_label)

    def _write_host_report(
        self,
        *,
        writer,
        project_dir: Path,
        payload: dict[str, Any],
        renderers: dict[str, Any],
    ) -> dict[str, Path]:
        return cast(
            dict[str, Path],
            writer(
                project_dir=project_dir,
                payload=payload,
                resolve_project_name_fn=self._resolve_report_project_name,
                **renderers,
            ),
        )

    def _write_host_surface_audit_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        return self._write_host_report(
            writer=write_host_surface_audit_report,
            project_dir=project_dir,
            payload=payload,
            renderers={
                "render_surface_audit_fn": self._render_host_surface_audit_markdown,
            },
        )

    def _render_host_hardening_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_hardening_markdown(payload, host_label_fn=self._host_label)

    def _render_host_parity_onepage_markdown(self, payload: dict[str, Any]) -> str:
        return render_host_parity_onepage_markdown(payload, host_label_fn=self._host_label)

    def _write_host_hardening_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        return self._write_host_report(
            writer=write_host_hardening_report,
            project_dir=project_dir,
            payload=payload,
            renderers={
                "render_hardening_fn": self._render_host_hardening_markdown,
                "render_parity_onepage_fn": self._render_host_parity_onepage_markdown,
            },
        )

    def _write_host_runtime_validation_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        return self._write_host_report(
            writer=write_host_runtime_validation_report,
            project_dir=project_dir,
            payload=payload,
            renderers={
                "render_runtime_validation_fn": self._render_host_runtime_validation_markdown,
            },
        )

    def _write_host_compatibility_report(
        self,
        *,
        project_dir: Path,
        payload: dict[str, Any],
    ) -> dict[str, Path]:
        return self._write_host_report(
            writer=write_host_compatibility_report,
            project_dir=project_dir,
            payload=payload,
            renderers={
                "render_compatibility_fn": self._render_host_compatibility_markdown,
            },
        )
