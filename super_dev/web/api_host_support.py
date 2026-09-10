"""Host discovery, guidance and validation helpers for the Web API."""

import glob
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from super_dev.catalogs import (
    HOST_COMMAND_CANDIDATES,
    HOST_TOOL_CATALOG,
    HOST_TOOL_CATEGORY_MAP,
    PRIMARY_HOST_TOOL_IDS,
    host_detection_path_candidates,
    host_path_override_guide,
    host_runtime_validation_overrides,
)
from super_dev.host_adaptation_contract import build_host_adaptation_contract
from super_dev.host_diagnostics import (
    build_host_compatibility_summary,
    collect_host_diagnostics,
)
from super_dev.host_entry_decisions import (
    build_detected_host_decision_card,
    build_host_start_guidance,
    build_no_host_decision_card,
    build_primary_repair_action,
)
from super_dev.host_experience_profile import (
    build_host_competition_first_prompt,
    build_host_official_pass_criteria,
    build_host_official_workflow_checks,
    build_host_post_onboard_self_check,
    build_host_repair_guidance,
    build_host_resume_guidance,
    build_host_standard_first_prompt,
    build_host_start_playbook,
)
from super_dev.host_registry import get_install_mode
from super_dev.host_runtime_validation import (
    build_host_runtime_validation_payload,
    build_runtime_evidence_record,
    host_runtime_status_label,
    load_host_runtime_validation_state,
    update_host_runtime_validation_state,
)
from super_dev.host_session_resume import build_session_resume_card
from super_dev.host_usage_profile import serialize_host_usage_profile
from super_dev.host_workflow_context import build_host_workflow_context
from super_dev.integrations.manager import IntegrationManager
from super_dev.seeai_design_system import (
    SEEAI_ARCHETYPE_DETECTION_HINTS,
    SEEAI_COMPACT_DOC_SECTIONS,
    SEEAI_COMPLEXITY_PATTERNS,
    SEEAI_COMPLEXITY_REDUCTION_RULES,
    SEEAI_DEGRADE_RULE,
    SEEAI_EXECUTION_GUARDRAILS,
    SEEAI_FAILURE_PROTOCOL,
    SEEAI_FIRST_RESPONSE_TEMPLATE,
    SEEAI_MODULE_TRUTH_RULES,
    SEEAI_RESEARCH_PRIORITIES,
    SEEAI_SCOPE_RULE,
    SEEAI_SEARCH_QUERIES,
    SEEAI_TIMEBOX_BREAKDOWN,
    get_seeai_archetype_playbook_map,
    get_seeai_design_pack_map,
)
from super_dev.seeai_smoke_scenarios import (
    get_seeai_acceptance_gates,
    get_seeai_smoke_scenarios,
)
from super_dev.skills import SkillManager
from super_dev.workflow_contract import get_agent_team, get_workflow_contract
from super_dev.workflow_state import (
    build_host_entry_prompts,
    build_host_flow_contract,
    build_host_flow_probe,
    detect_flow_variant,
    detect_pipeline_summary,
    load_framework_playbook_summary,
    workflow_continuity_rules,
    workflow_mode_label,
    workflow_mode_shortcuts,
)

_api_logger = logging.getLogger("super_dev.web.api")


def _validate_project_dir(project_dir: str) -> Path:
    """验证项目目录路径，防止路径遍历攻击"""
    segments = project_dir.replace("\\", "/").split("/")
    if ".." in segments:
        raise HTTPException(status_code=400, detail="project_dir 不允许包含 .. 路径遍历")
    normalized = Path(project_dir).resolve()
    return normalized


def _public_host_targets(*, integration_manager: IntegrationManager) -> list[str]:
    available_targets = [item.name for item in integration_manager.list_targets()]
    public_targets = [target for target in PRIMARY_HOST_TOOL_IDS if target in available_targets]
    return public_targets or available_targets


def _detect_pipeline_summary(
    project_dir: Path, run: dict[str, Any] | None = None
) -> dict[str, Any]:
    return detect_pipeline_summary(project_dir, run)


def _sanitize_project_name(name: str) -> str:
    sanitized = re.sub(r"[^0-9a-zA-Z_-]+", "-", (name or "").strip()).strip("-")
    return sanitized.lower() or "my-project"


def _display_final_trigger(profile) -> str:
    if getattr(profile, "host", "") == "codex":
        return "App/Desktop: /super-dev | 回退: super-dev: 你的需求"
    if getattr(profile, "host", "") == "codex-cli":
        return "CLI: $super-dev | 回退: super-dev: 你的需求"
    return str(profile.trigger_command).replace("<需求描述>", "你的需求")


def _default_host_commands(host_id: str, *, supports_slash: bool) -> dict[str, str]:
    profile = IntegrationManager(Path.cwd()).get_adapter_profile(host_id)
    trigger = _display_final_trigger(profile)
    host_work_entry = (
        "super-dev: 修复当前项目中的关键问题并补充回归验证"
        if host_id in {"codex", "codex-cli"}
        else (
            "/super-dev 修复当前项目中的关键问题并补充回归验证"
            if supports_slash
            else "super-dev: 修复当前项目中的关键问题并补充回归验证"
        )
    )
    host_resume_entry = (
        "super-dev: 继续当前流程"
        if host_id in {"codex", "codex-cli"}
        else ("/super-dev 继续当前流程" if supports_slash else "super-dev: 继续当前流程")
    )
    host_status_entry = (
        "super-dev: 现在下一步是什么"
        if host_id in {"codex", "codex-cli"}
        else ("/super-dev 现在下一步是什么" if supports_slash else "super-dev: 现在下一步是什么")
    )
    host_review_entry = (
        "super-dev: 文档确认，可以继续当前流程"
        if host_id in {"codex", "codex-cli"}
        else (
            "/super-dev 文档确认，可以继续当前流程"
            if supports_slash
            else "super-dev: 文档确认，可以继续当前流程"
        )
    )
    commands = {
        "run": trigger,
        "work": host_work_entry,
        "review": host_review_entry,
        "resume": host_resume_entry,
        "status": host_status_entry,
        "slash": "/super-dev 你的需求" if supports_slash else "",
        "seeai_slash": "/super-dev-seeai 比赛需求" if supports_slash else "",
        "skill_slash": "/super-dev" if host_id == "codex" else "",
        "seeai_skill_slash": "/super-dev-seeai" if host_id == "codex" else "",
        "skill": "$super-dev" if host_id == "codex-cli" else "",
        "seeai_skill": "$super-dev-seeai" if host_id == "codex-cli" else "",
        "trigger": trigger,
        "seeai_trigger": (
            "CLI: $super-dev-seeai | 回退: super-dev-seeai: 比赛需求"
            if host_id == "codex-cli"
            else (
                "App/Desktop: /super-dev-seeai | 回退: super-dev-seeai: 比赛需求"
                if host_id == "codex"
                else (
                    "/super-dev-seeai 比赛需求" if supports_slash else "super-dev-seeai: 比赛需求"
                )
            )
        ),
    }
    return commands


def _default_host_maintenance_commands(host_id: str, *, skill_name: str) -> dict[str, str]:
    return {
        "setup": f"super-dev setup --host {host_id} --force --yes",
        "onboard": f"super-dev onboard --host {host_id} --force --yes",
        "doctor": f"super-dev doctor --host {host_id} --repair --force",
        "audit": f"super-dev integrate audit --target {host_id}",
        "smoke": f"super-dev integrate smoke --target {host_id}",
        "skill_install": (
            f"super-dev skill install super-dev --target {host_id} --name {skill_name} --force"
            if skill_name
            else ""
        ),
    }


def _competition_mode_payload(host_id: str, *, supports_slash: bool) -> dict[str, Any]:
    contract = get_workflow_contract("seeai")
    if host_id == "codex-cli":
        trigger = "App/Desktop: /super-dev-seeai | CLI: $super-dev-seeai | 回退: super-dev-seeai: 比赛需求"
    elif host_id == "codex":
        trigger = "App/Desktop: /super-dev-seeai | 回退: super-dev-seeai: 比赛需求"
    elif supports_slash:
        trigger = "/super-dev-seeai 比赛需求"
    else:
        trigger = "super-dev-seeai: 比赛需求"

    payload: dict[str, Any] = {
        "enabled": True,
        "name": "SEEAI",
        "timebox_minutes": contract.sprint_horizon_minutes,
        "trigger": trigger,
        "phase_chain": [phase.key for phase in contract.phase_chain],
        "agent_team": [agent.key for agent in get_agent_team("seeai")],
        "summary": "比赛快链路：保留 research/三文档/spec，但压缩成半小时内可展示的成品交付。",
        "scope_rule": SEEAI_SCOPE_RULE,
        "degrade_rule": SEEAI_DEGRADE_RULE,
        "research_priorities": list(SEEAI_RESEARCH_PRIORITIES),
        "default_search_queries": list(SEEAI_SEARCH_QUERIES),
        "first_response_template": list(SEEAI_FIRST_RESPONSE_TEMPLATE),
        "timebox_breakdown": list(SEEAI_TIMEBOX_BREAKDOWN),
        "archetype_detection_hints": list(SEEAI_ARCHETYPE_DETECTION_HINTS),
        "compact_doc_sections": {
            key: list(value) for key, value in SEEAI_COMPACT_DOC_SECTIONS.items()
        },
        "quality_floor": list(contract.quality_floor),
        "judge_checklist": list(contract.judge_checklist),
        "execution_guardrails": list(SEEAI_EXECUTION_GUARDRAILS),
        "module_truth_rules": list(SEEAI_MODULE_TRUTH_RULES),
        "complexity_reduction_rules": list(SEEAI_COMPLEXITY_REDUCTION_RULES),
        "complexity_patterns": list(SEEAI_COMPLEXITY_PATTERNS),
        "failure_protocol": list(SEEAI_FAILURE_PROTOCOL),
        "design_packs": get_seeai_design_pack_map(),
        "archetype_playbooks": get_seeai_archetype_playbook_map(),
        "module_activation_gate": "仅保留真实启动、真实交互、真实进入主演示路径的模块；未接入主路径的模块默认删除。",
        "smoke_scenarios": get_seeai_smoke_scenarios(),
        "acceptance_gates": get_seeai_acceptance_gates(),
        "host_tips": [],
    }

    if host_id in {"codebuddy", "codebuddy-cli"}:
        payload["host_tips"] = [
            "固定在同一个项目上下文会话里完成比赛冲刺，减少子会话切换。",
            "如果 slash 列表刷新慢，直接回退到 super-dev-seeai: 继续。",
            "按 P0/P1/P2 控制范围，先保住主演示路径。",
        ]
    elif host_id == "droid-cli":
        payload["host_tips"] = [
            "优先固定在同一个 Droid session 里完成比赛冲刺，减少重开会话带来的上下文漂移。",
            "如果 /super-dev-seeai 尚未出现在命令面板，直接使用 super-dev-seeai:。",
            '如需 headless 续跑，优先使用 droid exec --session-id <id> "continue with next steps"。',
        ]
    else:
        payload["host_tips"] = [
            "先保住一个可演示主路径，再补一个明显 wow 点。",
            "真实后端来不及时，优先用 mock / 本地数据保持演示完整。",
        ]

    return payload


def _build_host_tool_catalog_payload() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for item in HOST_TOOL_CATALOG:
        host_id = item["id"]
        target = IntegrationManager.TARGETS.get(host_id)
        supports_slash = IntegrationManager.supports_slash(host_id)
        profile = IntegrationManager(Path.cwd()).get_adapter_profile(host_id)
        final_trigger = _display_final_trigger(profile)
        install_mode = get_install_mode(host_id)
        managed_competition_project_surfaces = (
            IntegrationManager.managed_competition_project_surfaces(host_id)
        )
        managed_competition_user_surfaces = IntegrationManager.managed_competition_user_surfaces(
            host_id
        )
        usage_context = {
            "host": item["name"],
            "host_protocol_mode": profile.host_protocol_mode,
            "official_project_surfaces": list(profile.official_project_surfaces),
            "official_user_surfaces": list(profile.official_user_surfaces),
            "managed_competition_project_surfaces": managed_competition_project_surfaces,
            "managed_competition_user_surfaces": managed_competition_user_surfaces,
        }
        payload.append(
            {
                "id": host_id,
                "name": item["name"],
                "default_install_scope": "project-first",
                "default_install_summary": (
                    "默认只写当前项目和默认 Skill 面；如需跨项目共享统一宿主心智，再显式加 --with-user-surfaces。"
                    if profile.optional_user_surfaces
                    else "默认只写当前项目和默认 Skill 面。"
                ),
                "user_surface_opt_in_flag": (
                    "--with-user-surfaces" if profile.optional_user_surfaces else ""
                ),
                "user_surface_opt_in_available": bool(profile.optional_user_surfaces),
                "category": HOST_TOOL_CATEGORY_MAP.get(host_id, "ide"),
                "install_mode": install_mode.value if install_mode is not None else "",
                "certification_level": profile.certification_level,
                "certification_label": profile.certification_label,
                "certification_reason": profile.certification_reason,
                "certification_evidence": list(profile.certification_evidence),
                "host_protocol_mode": profile.host_protocol_mode,
                "host_protocol_summary": profile.host_protocol_summary,
                "official_docs_url": profile.official_docs_url,
                "docs_verified": profile.docs_verified,
                "integration_files": list(target.files) if target else [],
                "official_project_surfaces": list(profile.official_project_surfaces),
                "official_user_surfaces": list(profile.official_user_surfaces),
                "optional_project_surfaces": list(profile.optional_project_surfaces),
                "optional_user_surfaces": list(profile.optional_user_surfaces),
                "managed_competition_project_surfaces": managed_competition_project_surfaces,
                "managed_competition_user_surfaces": managed_competition_user_surfaces,
                "observed_compatibility_surfaces": list(profile.observed_compatibility_surfaces),
                "slash_command_file": (
                    IntegrationManager.SLASH_COMMAND_FILES.get(host_id, "")
                    if supports_slash
                    else ""
                ),
                "supports_slash": supports_slash,
                "usage_mode": profile.usage_mode,
                "primary_entry": profile.primary_entry,
                "final_trigger": final_trigger,
                "entry_variants": list(profile.entry_variants),
                "trigger_context": profile.trigger_context,
                "usage_location": profile.usage_location,
                "requires_restart_after_onboard": profile.requires_restart_after_onboard,
                "post_onboard_steps": list(profile.post_onboard_steps),
                "usage_notes": list(profile.usage_notes),
                "smoke_test_prompt": profile.smoke_test_prompt,
                "smoke_test_steps": list(profile.smoke_test_steps),
                "smoke_success_signal": profile.smoke_success_signal,
                "competition_smoke_test_prompt": profile.competition_smoke_test_prompt,
                "competition_smoke_test_steps": list(profile.competition_smoke_test_steps),
                "competition_smoke_success_signal": profile.competition_smoke_success_signal,
                "competition_smoke_suite": list(profile.competition_smoke_suite),
                "competition_acceptance_gates": list(profile.competition_acceptance_gates),
                "competition_evidence_template": dict(profile.competition_evidence_template),
                "standard_flow_first_prompt": build_host_standard_first_prompt(host_id),
                "competition_flow_first_prompt": build_host_competition_first_prompt(host_id),
                "host_start_playbook": build_host_start_playbook(host_id),
                "host_resume_guidance": build_host_resume_guidance(host_id),
                "post_onboard_self_check": build_host_post_onboard_self_check(
                    host_id, usage_context
                ),
                "official_workflow_checks": build_host_official_workflow_checks(
                    host_id, usage_context
                ),
                "official_pass_criteria": build_host_official_pass_criteria(host_id, usage_context),
                "host_repair_playbook": build_host_repair_guidance(host_id).strip(),
                "supports_skill_slash_entry": host_id in {"codex", "kimi-code"},
                "skill_slash_entry_command": (
                    "/super-dev"
                    if host_id == "codex"
                    else "/skill:super-dev" if host_id == "kimi-code" else ""
                ),
                "skill_slash_entry_note": (
                    "Indicates the enabled Skill entry shown in the Codex app slash list, not a project-level custom slash command."
                    if host_id == "codex"
                    else (
                        "Indicates Kimi Code's current built-in Skill entry, not a project-level custom slash command."
                        if host_id == "kimi-code"
                        else ""
                    )
                ),
                "flow_contract": build_host_flow_contract(host_id),
                "flow_probe": build_host_flow_probe(host_id),
                "adaptation_contract": build_host_adaptation_contract(
                    profile,
                    host_id=host_id,
                    supports_slash=supports_slash,
                ),
                "competition_mode": _competition_mode_payload(
                    host_id, supports_slash=supports_slash
                ),
                "notes": profile.notes,
                "commands": _default_host_commands(host_id, supports_slash=supports_slash),
                "maintenance_commands": _default_host_maintenance_commands(
                    host_id,
                    skill_name=(
                        SkillManager.default_skill_name(host_id)
                        if IntegrationManager.requires_skill(host_id)
                        else ""
                    ),
                ),
            }
        )
    return payload


def _detect_host_targets(available_targets: list[str]) -> tuple[list[str], dict[str, list[str]]]:
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


def _format_detection_reason(reason: str) -> str:
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


def _explain_detection_details(detected_meta: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        host: [_format_detection_reason(item) for item in reasons]
        for host, reasons in detected_meta.items()
    }


def _host_runtime_checklist(
    target: str, usage: dict[str, Any], project_dir: Path | None = None
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
    target: str, usage: dict[str, Any], project_dir: Path | None = None
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


def _project_has_super_dev_context(project_dir: Path) -> bool:
    project_dir = Path(project_dir).resolve()
    return any(
        path.exists()
        for path in (
            project_dir / "super-dev.yaml",
            project_dir / ".super-dev" / "WORKFLOW.md",
            project_dir / "output" / f"{project_dir.name}-prd.md",
            project_dir / "output" / f"{project_dir.name}-architecture.md",
            project_dir / "output" / f"{project_dir.name}-proof-pack.json",
        )
    )


def _build_resume_probe_instruction(project_dir: Path) -> str:
    if not _project_has_super_dev_context(project_dir):
        return ""
    return (
        "继续当前项目的 Super Dev 流程，不要当作普通聊天。"
        "先读取 .super-dev/SESSION_BRIEF.md、.super-dev/workflow-state.json、.super-dev/WORKFLOW.md、output/*、.super-dev/review-state/* 和最近的 tasks.md。"
        "如果这是已有项目的增量迭代、派生版本或缺陷修复，先按 baseline -> baseline confirmation -> delta research -> docs 继续。"
    )


def _build_resume_probe_prompt(project_dir: Path, target: str, usage: dict[str, Any]) -> str:
    instruction = _build_resume_probe_instruction(project_dir)
    if not instruction:
        return ""
    trigger = str(usage.get("trigger_command", "")).strip()
    flow_variant = detect_flow_variant(project_dir)
    entry_bundle = build_host_entry_prompts(
        target=target,
        instruction=instruction,
        supports_slash=bool("/super-dev" in trigger),
        flow_variant=flow_variant,
    )
    preferred_entry = str(entry_bundle.get("preferred_entry", "")).strip()
    prompts = entry_bundle.get("entry_prompts", {})
    if isinstance(prompts, dict) and preferred_entry:
        prompt = str(prompts.get(preferred_entry, "")).strip()
        if prompt:
            return prompt
    return f"super-dev: {instruction}"


def _host_resume_checklist(target: str, project_dir: Path | None = None) -> list[str]:
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


def _build_session_resume_card(
    project_dir: Path, target: str, usage: dict[str, Any]
) -> dict[str, Any]:
    host_first_sentence = _build_resume_probe_prompt(project_dir, target, usage)
    instruction = _build_resume_probe_instruction(project_dir)
    enabled = bool(host_first_sentence)
    workflow_mode = ""
    workflow_mode_display = ""
    action_title = ""
    action_examples: list[str] = []
    rules: list[str] = []
    recommended_workflow_command = ""
    summary: dict[str, Any] = {}
    if enabled:
        summary = _detect_pipeline_summary(project_dir)
        recommended_workflow_command = (
            str(summary.get("recommended_command", "")).strip() or "在宿主里说“继续当前流程”"
        )
        workflow_mode = str(summary.get("workflow_mode", "")).strip()
        if workflow_mode:
            workflow_mode_display = workflow_mode_label(workflow_mode)
        action_card = summary.get("action_card")
        if isinstance(action_card, dict):
            action_title = str(action_card.get("title", "")).strip()
            raw_examples = action_card.get("examples")
            if isinstance(raw_examples, list):
                action_examples = [str(item).strip() for item in raw_examples if str(item).strip()]
            raw_rules = action_card.get("continuity_rules")
            if isinstance(raw_rules, list):
                rules = [str(item).strip() for item in raw_rules if str(item).strip()]
            raw_shortcuts = action_card.get("shortcuts")
            if isinstance(raw_shortcuts, list):
                user_action_shortcuts = [
                    str(item).strip() for item in raw_shortcuts if str(item).strip()
                ]
            else:
                user_action_shortcuts = workflow_mode_shortcuts(
                    workflow_mode, examples=action_examples
                )
        else:
            user_action_shortcuts = workflow_mode_shortcuts(workflow_mode)
        if not rules:
            rules = workflow_continuity_rules(str(summary.get("workflow_status", "")).strip())
    else:
        user_action_shortcuts = []
    scenario_cards = list(summary.get("scenario_cards") or []) if enabled else []
    card = build_session_resume_card(
        project_dir=project_dir,
        target=target,
        enabled=enabled,
        host_first_sentence=host_first_sentence,
        line_host_first_sentence=host_first_sentence,
        continue_instruction=instruction,
        workflow_mode=workflow_mode,
        workflow_mode_label=workflow_mode_display,
        action_title=action_title,
        action_examples=action_examples,
        user_action_shortcuts=user_action_shortcuts,
        scenario_cards=scenario_cards,
        specific_rules=rules,
        recommended_workflow_command=recommended_workflow_command,
        supports_slash=bool("/super-dev" in str(usage.get("trigger_command", "")).strip()),
        flow_variant=str(summary.get("flow_variant", "")).strip()
        or detect_flow_variant(project_dir),
        workflow_context=(
            build_host_workflow_context(
                project_dir,
                summary=summary,
                entry_mode="continue",
                target=target,
            )
            if enabled
            else {}
        ),
        include_workflow_state_line=True,
    )
    card["flow_variant"] = str(summary.get("flow_variant", "")).strip() if enabled else ""
    return card


def _build_no_host_decision_card() -> dict[str, Any]:
    action_examples = ["先装 Codex", "我先用 Claude Code", "先把宿主接好再开始"]
    next_actions = [
        "先安装一个受支持宿主，优先 Claude Code 或 Codex。",
        "如果宿主装在自定义目录，先设置对应的 SUPER_DEV_HOST_PATH_* 环境变量。",
        "安装后重新运行 super-dev，完成接入后直接回宿主主路径。",
    ]
    first_action = next_actions[0]
    return build_no_host_decision_card(
        workflow_mode_label=workflow_mode_label("start"),
        action_examples=action_examples,
        first_action=first_action,
        secondary_actions=next_actions[1:],
        path_override_hint="如果装在自定义目录，先设置 `SUPER_DEV_HOST_PATH_CODEX_CLI=<安装路径>` 这类环境变量再重试。",
        path_override_examples=[
            {
                "id": host_id,
                "name": host_display,
                "env_key": str(host_path_override_guide(host_id).get("env_key", "")),
                "unix_example": str(host_path_override_guide(host_id).get("unix_example", "")),
                "windows_example": str(
                    host_path_override_guide(host_id).get("windows_example", "")
                ),
            }
            for host_id, host_display in (("claude-code", "Claude Code"), ("codex-cli", "Codex"))
        ],
        user_action_shortcuts=workflow_mode_shortcuts("start", examples=action_examples),
        lines=[
            f"动作类型: {workflow_mode_label('start')}",
            "当前动作: 先完成宿主安装与接入",
            f"先做这一步: {first_action}",
            "当前机器上未命中受支持宿主。",
            "如果装在自定义目录，先设置 `SUPER_DEV_HOST_PATH_CODEX_CLI=<安装路径>` 这类环境变量再重试。",
            "自然语言示例: 先装 Codex, 我先用 Claude Code, 先把宿主接好再开始",
            "接入完成后普通开发直接回宿主；已有项目先 baseline 并确认 baseline，中断后默认先 resume。",
        ],
    )


def _build_detected_host_decision_card(
    *,
    project_dir: Path,
    integration_manager: IntegrationManager,
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
        usage_profile_fn=lambda target: _serialize_host_usage_profile(
            integration_manager=integration_manager,
            target=target,
        ),
        session_resume_card_fn=(
            lambda current_project_dir, target: _build_session_resume_card(
                current_project_dir,
                target,
                _serialize_host_usage_profile(
                    integration_manager=integration_manager,
                    target=target,
                ),
            )
        ),
        explain_detection_details_fn=_explain_detection_details,
        workflow_mode_label_fn=workflow_mode_label,
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
        first_suggestion_text_fn=lambda _selected_host, candidates: str(candidates[0]["trigger"]),
        default_action_examples=[
            "开始这个项目",
            "做一个商业级官网",
            "用 Super Dev 开始处理当前需求",
        ],
        user_action_shortcuts_fn=lambda mode, examples: workflow_mode_shortcuts(
            mode,
            examples=examples,
        ),
        no_host_card_fn=_build_no_host_decision_card,
    )


def _build_primary_repair_action(
    *,
    report: dict[str, Any],
    targets: list[str],
    integration_manager: IntegrationManager,
    decision_card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_primary_repair_action(
        report=report,
        targets=targets,
        host_label_fn=(
            lambda target: _serialize_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            )["host"]
        ),
        usage_profile_fn=(
            lambda target: _serialize_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            )
        ),
        decision_card=decision_card,
    )


def _collect_host_diagnostics(
    *,
    project_dir: Path,
    targets: list[str],
    skill_name: str,
    check_integrate: bool,
    check_skill: bool,
    check_slash: bool,
) -> dict[str, Any]:
    return collect_host_diagnostics(
        project_dir=project_dir,
        targets=targets,
        skill_name=skill_name,
        check_integrate=check_integrate,
        check_skill=check_skill,
        check_slash=check_slash,
        build_usage_profile_fn=(
            lambda integration_manager, target: _serialize_host_usage_profile(
                integration_manager=integration_manager,
                target=target,
            )
        ),
    )


def _serialize_host_usage_profile(
    *,
    integration_manager: IntegrationManager,
    target: str,
) -> dict[str, Any]:
    profile = integration_manager.get_adapter_profile(target)
    return serialize_host_usage_profile(
        profile=profile,
        target=target,
        final_trigger=_display_final_trigger(profile),
        managed_competition_project_surfaces=integration_manager.managed_competition_project_surfaces(
            target
        ),
        managed_competition_user_surfaces=integration_manager.managed_competition_user_surfaces(
            target
        ),
        include_host_id=True,
        include_capability_labels=True,
        include_docs_fields=True,
        skill_slash_entry_host_id=target,
        skill_slash_entry_note=(
            "Indicates the enabled Skill entry shown in the Codex app slash list, not a project-level custom slash command."
        ),
        flow_host_id=target,
    )


def _load_host_runtime_validation_state(*, project_dir: Path) -> dict[str, Any]:
    return load_host_runtime_validation_state(project_dir=project_dir)


def _host_runtime_status_label(status: str) -> str:
    return host_runtime_status_label(status)


def _build_runtime_evidence_record(
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
    *,
    project_dir: Path,
    host: str,
    status: str,
    comment: str,
    actor: str,
    competition_evidence: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    return update_host_runtime_validation_state(
        project_dir=project_dir,
        host=host,
        status=status,
        comment=comment,
        actor=actor,
        competition_evidence=competition_evidence,
    )


def _build_host_runtime_validation_payload(
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
        explain_detection_details_fn=_explain_detection_details,
        runtime_checklist_fn=_host_runtime_checklist,
        pass_criteria_fn=_host_runtime_pass_criteria,
        resume_probe_prompt_fn=(
            lambda target, usage, project_dir: _build_resume_probe_prompt(
                project_dir,
                target,
                usage,
            )
        ),
        resume_checklist_fn=_host_resume_checklist,
        entry_enricher_fn=(
            lambda target, host, usage, runtime_entry: {
                "checks": (
                    host.get("checks", {}) if isinstance(host.get("checks", {}), dict) else {}
                ),
                "missing": (
                    host.get("missing", []) if isinstance(host.get("missing", []), list) else []
                ),
                "suggestions": (
                    host.get("suggestions", [])
                    if isinstance(host.get("suggestions", []), list)
                    else []
                ),
            }
        ),
    )


def _build_host_compatibility_summary(
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
    )


def _repair_host_diagnostics(
    *,
    project_dir: Path,
    report: dict[str, Any],
    skill_name: str,
    force: bool,
    check_integrate: bool,
    check_skill: bool,
    check_slash: bool,
) -> dict[str, dict[str, str]]:
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
        try:
            if check_integrate and "integrate" in missing:
                integration_manager.setup(target=target, force=force)
                host_actions["integrate"] = "fixed"
        except Exception as exc:
            host_actions["integrate"] = f"failed: {exc}"

        try:
            if check_skill and IntegrationManager.requires_skill(target) and "skill" in missing:
                skill_manager.install(
                    source="super-dev",
                    target=target,
                    name=skill_name,
                    force=force,
                )
                host_actions["skill"] = "fixed"
        except Exception as exc:
            host_actions["skill"] = f"failed: {exc}"

        try:
            if check_slash and integration_manager.supports_slash(target):
                integration_manager.setup_slash_command(target=target, force=force)
                integration_manager.setup_global_slash_command(target=target, force=force)
                if "slash" in missing:
                    host_actions["slash"] = "fixed"
        except Exception as exc:
            host_actions["slash"] = f"failed: {exc}"

        if host_actions:
            actions[target] = host_actions

    return actions
