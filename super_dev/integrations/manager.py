"""
多平台 AI Coding 工具集成管理器
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urljoin, urlparse

from ..catalogs import HOST_TOOL_CATEGORY_MAP, HOST_TOOL_IDS
from ..host_adapters import (
    SpecialAdapterContext,
    build_special_usage_profile,
    get_adapter_mode_override,
    get_competition_smoke_extra_steps,
    get_special_install_surfaces,
)
from ..host_registry import get_display_name, get_protocol_mode, get_protocol_summary
from ..seeai_smoke_scenarios import (
    build_seeai_evidence_template,
    build_seeai_smoke_suite,
    get_seeai_acceptance_gates,
)
from ..user_directories import UserDirectoryContext
from ..workflow_contract import readonly_request_guidance
from .catalog_mixin import IntegrationCatalogMixin
from .manager_content_mixin import IntegrationManagerContentMixin
from .models import HostAdapterProfile, IntegrationTarget


class IntegrationManager(IntegrationCatalogMixin, IntegrationManagerContentMixin):
    """为不同 AI Coding 平台生成集成配置"""

    @classmethod
    def host_family(cls, target: str) -> str:
        return cls.HOST_FAMILY_MAP.get(target, target)

    @classmethod
    def preferred_target_for_family(cls, family: str, candidates: list[str] | None = None) -> str:
        preferred = cls.PREFERRED_FAMILY_TARGETS.get(family, family)
        if candidates and preferred not in candidates:
            return sorted(candidates)[0]
        return preferred

    @classmethod
    def family_targets(cls, family: str) -> list[str]:
        return [
            target
            for target, current_family in cls.HOST_FAMILY_MAP.items()
            if current_family == family
        ]

    @classmethod
    def target_detection_markers(cls, target: str) -> list[str]:
        integration = cls.TARGETS[target]
        markers: list[str] = [
            relative for relative in integration.files if relative not in cls.SHARED_DETECTION_FILES
        ]
        slash_file = cls.SLASH_COMMAND_FILES.get(target)
        if slash_file and slash_file not in markers:
            markers.append(slash_file)
        return markers

    @staticmethod
    def _string_value(value: object, default: str = "") -> str:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or default
        return default

    @staticmethod
    def _bool_value(value: object, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        return default

    @classmethod
    def _string_list(cls, value: object) -> list[str]:
        if not isinstance(value, Iterable) or isinstance(value, str | bytes | dict):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @classmethod
    def _string_dict(cls, value: object) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {str(key): cls._string_value(item) for key, item in value.items()}

    @classmethod
    def _bool_dict(cls, value: object) -> dict[str, bool]:
        if not isinstance(value, dict):
            return {}
        return {str(key): cls._bool_value(item) for key, item in value.items()}

    @classmethod
    def _object_dict(cls, value: object) -> dict[str, object]:
        if not isinstance(value, dict):
            return {}
        return {str(key): item for key, item in value.items()}

    @classmethod
    def _dict_list(cls, value: object) -> list[dict[str, object]]:
        if not isinstance(value, Iterable) or isinstance(value, str | bytes | dict):
            return []
        normalized: list[dict[str, object]] = []
        for item in value:
            if isinstance(item, dict):
                normalized.append({str(key): item_value for key, item_value in item.items()})
        return normalized

    def install_manifest_path(self) -> Path:
        return self.project_dir / ".super-dev" / "install-manifest.json"

    def load_install_manifest(self) -> dict[str, Any]:
        file_path = self.install_manifest_path()
        if not file_path.exists():
            return {"version": 1, "targets": {}, "updated_at": ""}
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return {"version": 1, "targets": {}, "updated_at": ""}
        if not isinstance(payload, dict):
            return {"version": 1, "targets": {}, "updated_at": ""}
        targets = payload.get("targets", {})
        if not isinstance(targets, dict):
            targets = {}
        return {
            "version": int(payload.get("version", 1) or 1),
            "targets": targets,
            "updated_at": str(payload.get("updated_at", "")).strip(),
        }

    def save_install_manifest(self, payload: dict[str, Any]) -> Path:
        current = self.load_install_manifest()
        current.update(payload)
        current["version"] = int(current.get("version", 1) or 1)
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        file_path = self.install_manifest_path()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return file_path

    def __init__(
        self,
        project_dir: Path,
        user_directories: UserDirectoryContext | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.templates_dir = self.project_dir / "templates"
        self.user_directories = user_directories or UserDirectoryContext.current()

    def _flow_contract_markdown_block(self) -> str:
        return (
            "## Super Dev System Flow Contract\n"
            "- SUPER_DEV_FLOW_CONTRACT_V1\n"
            "- PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery\n"
            "- DOC_CONFIRM_GATE: required\n"
            "- PREVIEW_CONFIRM_GATE: required\n"
            "- HOST_PARITY: required\n"
        )

    def _flow_contract_toml_block(self) -> str:
        return (
            "# SUPER_DEV_FLOW_CONTRACT_V1\n"
            "# PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery\n"
            "# DOC_CONFIRM_GATE: required\n"
            "# PREVIEW_CONFIRM_GATE: required\n"
            "# HOST_PARITY: required\n"
        )

    def _append_flow_contract(self, *, content: str, relative: str) -> str:
        normalized = content or ""
        if (
            "SUPER_DEV_FLOW_CONTRACT_V1" in normalized
            or "SUPER_DEV_SEEAI_FLOW_CONTRACT_V1" in normalized
        ):
            return normalized
        if str(relative).endswith(".toml"):
            return f"{normalized.rstrip()}\n\n{self._flow_contract_toml_block()}"
        return f"{normalized.rstrip()}\n\n{self._flow_contract_markdown_block()}"

    def _first_response_contract_zh(self) -> str:
        return (
            "## 首轮响应契约（首次触发必须执行）\n"
            "- 当用户通过宿主支持的 Super Dev 入口触发（例如 `/super-dev ...`、`$super-dev`、`super-dev: ...`、`super-dev：...`、`/super-dev-seeai ...`、`$super-dev-seeai`、`super-dev-seeai: ...` 或 `super-dev-seeai：...`）后，第一轮回复必须明确：已进入对应的 Super Dev 流水线，而不是普通聊天。\n"
            f"- {readonly_request_guidance()}\n"
            "- 已有流程的执行请求接续原活动变更和有效阶段，不按产物数量或创建时间猜任务。\n"
            "- 第一轮回复前，优先读取 `.super-dev/WORKFLOW.md` 与 `output/*-bootstrap.md`（若存在），把其中的初始化契约视为当前仓库的显式 bootstrap 规则。\n"
            "- 对于 new 新流程，第一轮回复必须明确当前阶段是 `research`；其他工作模式按原入口进入。恢复已有流程先读 SESSION_BRIEF 接续原阶段，不得重置为 research；只在研究阶段待完成时读取知识并联网调研。\n"
            "- 标准模式的后续顺序是：research -> 三份核心文档 -> 等待用户确认 -> Spec / tasks -> 适用前端与运行验证 -> 等待用户预览确认 -> 后端 / 测试 / 交付；无 UI 沿用原不适用处理。\n"
            "- SEEAI 模式的后续顺序是：research -> 比赛短版三文档 -> 等待用户确认 -> compact Spec -> full-stack sprint -> polish / handoff。\n"
            "- 两种模式都必须明确承诺：三份核心文档完成后会暂停并等待用户确认；未经确认不会创建 Spec，也不会开始编码。\n\n"
        )

    def _first_response_contract_en(self) -> str:
        return (
            "## First-Response Contract\n"
            "- On the first reply after a host-supported Super Dev entry (for example `/super-dev ...`, `$super-dev`, `super-dev: ...`, `super-dev：...`, `/super-dev-seeai ...`, `$super-dev-seeai`, `super-dev-seeai: ...`, or `super-dev-seeai：...`), explicitly state that the matching Super Dev mode is now active rather than normal chat mode.\n"
            f"- {readonly_request_guidance('en')}\n"
            "- Execution requests resume the explicitly active change and valid phase; artifacts or timestamps alone do not select a task.\n"
            "- Before the first reply, read `.super-dev/WORKFLOW.md` and `output/*-bootstrap.md` when present, and treat them as the explicit bootstrap contract for this repository.\n"
            "- The first reply must report the actual phase: new standard work follows its work-mode entry (new: the current phase is `research`; evolve/variant/patch: baseline), while new SEEAI work starts at research. For resume, read SESSION_BRIEF and continue the recorded phase and pending gates; do not restart. Read knowledge and do research when that stage is pending.\n"
            "- In standard mode, continue pending stages: research -> three core documents -> docs confirmation -> Spec/tasks -> applicable frontend runtime verification -> wait for user preview confirmation -> backend/tests/delivery. Non-UI work keeps the existing not-applicable path.\n"
            "- In SEEAI mode, the next sequence is research -> compact competition docs -> wait for user confirmation -> compact Spec -> full-stack sprint -> polish / handoff.\n"
            "- Both modes must explicitly promise that they will stop after the three core documents and wait for approval before creating Spec or writing code.\n\n"
        )

    @classmethod
    def coverage_gaps(cls) -> dict[str, list[str]]:
        declared = set(HOST_TOOL_IDS)
        target_keys = set(cls.TARGETS)
        slash_keys = set(cls.SLASH_COMMAND_FILES)
        slash_required = declared - cls.NO_SLASH_TARGETS
        docs_keys = set(cls.OFFICIAL_DOCS)
        verified_keys = set(cls.DOCS_VERIFIED_TARGETS)
        declared_with_docs = {item for item, value in cls.OFFICIAL_DOCS.items() if bool(value)}
        return {
            "missing_in_targets": sorted(declared - target_keys),
            "extra_in_targets": sorted(target_keys - declared),
            "missing_in_slash": sorted(slash_required - slash_keys),
            "extra_in_slash": sorted(slash_keys - slash_required),
            "missing_in_docs_map": sorted(declared - docs_keys),
            "extra_in_docs_map": sorted(docs_keys - declared),
            "missing_official_docs_url": sorted(declared - declared_with_docs),
            "unverified_docs": sorted(declared - verified_keys),
        }

    def list_targets(self) -> list[IntegrationTarget]:
        return list(self.TARGETS.values())

    @classmethod
    def required_integration_files(cls, target: str) -> list[str]:
        target_info = cls.TARGETS.get(target)
        if target_info is None:
            return []
        optional = set(target_info.optional_files)
        return [item for item in target_info.files if item not in optional]

    @classmethod
    def optional_integration_files(cls, target: str) -> list[str]:
        target_info = cls.TARGETS.get(target)
        if target_info is None:
            return []
        return list(target_info.optional_files)

    def get_adapter_profile(self, target: str) -> HostAdapterProfile:
        from ..catalogs import HOST_COMMAND_CANDIDATES, host_path_candidates
        from ..skills import SkillManager

        if target not in self.TARGETS:
            raise ValueError(f"Unsupported target: {target}")

        category = HOST_TOOL_CATEGORY_MAP.get(target, "ide")
        integration_files = list(self.required_integration_files(target))
        slash_file = self.SLASH_COMMAND_FILES.get(target, "") if self.supports_slash(target) else ""
        skill_dir = SkillManager.TARGET_PATHS.get(target, "") if self.requires_skill(target) else ""
        docs_references = self._official_docs_references(target)
        docs_url = docs_references[0] if docs_references else ""
        docs_verified = bool(docs_references)
        adapter_mode = self._adapter_mode(
            target=target, category=category, integration_files=integration_files
        )
        usage = dict(self._usage_profile(target=target, category=category))
        if not self._dict_list(usage.get("entry_variants")):
            usage["entry_variants"] = self._default_entry_variants(
                target=target,
                usage=usage,
            )
        certification = self._certification_profile(target)
        smoke = self._smoke_profile(target=target, category=category)
        preconditions = self._precondition_profile(target=target)
        surfaces = self._install_surfaces(target=target)
        protocol = self._protocol_profile(target=target)
        capability_labels = self._capability_labels(target=target)

        return HostAdapterProfile(
            host=target,
            category=category,
            adapter_mode=adapter_mode,
            host_model_provider="host",
            certification_level=self._string_value(certification.get("level"), "experimental"),
            certification_label=self._string_value(
                certification.get("label"), self.CERTIFICATION_LABELS["experimental"]
            ),
            certification_reason=self._string_value(certification.get("reason")),
            certification_evidence=self._string_list(certification.get("evidence")),
            official_docs_url=docs_url,
            docs_verified=docs_verified,
            primary_entry=self._string_value(usage.get("primary_entry")),
            terminal_entry="super-dev",
            terminal_entry_scope="仅用于安装 / 更新 / 卸载；正常开发应回到宿主会话",
            integration_files=integration_files,
            slash_command_file=slash_file,
            skill_dir=skill_dir,
            detection_commands=self._string_list(HOST_COMMAND_CANDIDATES.get(target, [])),
            detection_paths=self._string_list(host_path_candidates(target)),
            notes=self._string_value(usage.get("notes")),
            usage_mode=self._string_value(usage.get("usage_mode")),
            trigger_command=self._string_value(usage.get("trigger_command")),
            entry_variants=[
                self._string_dict(item) for item in self._dict_list(usage.get("entry_variants"))
            ],
            trigger_context=self._string_value(usage.get("trigger_context")),
            usage_location=self._string_value(usage.get("usage_location")),
            requires_restart_after_onboard=self._bool_value(
                usage.get("requires_restart_after_onboard")
            ),
            post_onboard_steps=self._string_list(usage.get("post_onboard_steps")),
            usage_notes=self._string_list(usage.get("usage_notes")),
            smoke_test_prompt=self._string_value(smoke.get("smoke_test_prompt")),
            smoke_test_steps=self._string_list(smoke.get("smoke_test_steps")),
            smoke_success_signal=self._string_value(smoke.get("smoke_success_signal")),
            competition_smoke_test_prompt=self._string_value(
                smoke.get("competition_smoke_test_prompt")
            ),
            competition_smoke_test_steps=self._string_list(
                smoke.get("competition_smoke_test_steps")
            ),
            competition_smoke_success_signal=self._string_value(
                smoke.get("competition_smoke_success_signal")
            ),
            competition_smoke_suite=self._dict_list(smoke.get("competition_smoke_suite")),
            competition_acceptance_gates=self._string_list(
                smoke.get("competition_acceptance_gates")
            ),
            competition_evidence_template=self._object_dict(
                smoke.get("competition_evidence_template")
            ),
            precondition_status=self._string_value(preconditions.get("status")),
            precondition_label=self._string_value(preconditions.get("label")),
            precondition_guidance=self._string_list(preconditions.get("guidance")),
            precondition_signals=self._bool_dict(preconditions.get("signals")),
            precondition_items=self._dict_list(preconditions.get("items")),
            host_protocol_mode=self._string_value(protocol.get("mode")),
            host_protocol_summary=self._string_value(protocol.get("summary")),
            official_project_surfaces=self._string_list(surfaces.get("official_project_surfaces")),
            official_user_surfaces=self._string_list(surfaces.get("official_user_surfaces")),
            optional_project_surfaces=self._string_list(surfaces.get("optional_project_surfaces")),
            optional_user_surfaces=self._string_list(surfaces.get("optional_user_surfaces")),
            observed_compatibility_surfaces=self._string_list(
                surfaces.get("observed_compatibility_surfaces")
            ),
            official_docs_references=docs_references,
            docs_check_status="declared" if docs_references else "missing",
            docs_check_summary=(
                f"declared {len(docs_references)} refs"
                if docs_references
                else "no official docs references"
            ),
            capability_labels=capability_labels,
        )

    def _default_entry_variants(
        self,
        *,
        target: str,
        usage: dict[str, object],
    ) -> list[dict[str, str]]:
        label = get_display_name(target) or target
        trigger = self._string_value(usage.get("trigger_command")) or (
            "/super-dev <需求描述>"
            if self.supports_slash(target)
            else f"{self.TEXT_TRIGGER_PREFIX} <需求描述>"
        )
        variants: list[dict[str, str]] = []
        if self.supports_slash(target):
            variants.append(
                {
                    "surface": "default",
                    "label": label,
                    "entry": trigger,
                    "mode": "native-slash",
                    "priority": "preferred",
                    "notes": "优先使用宿主原生 slash 入口进入当前 Super Dev 流程。",
                }
            )
            variants.append(
                {
                    "surface": "fallback",
                    "label": f"{label} Fallback",
                    "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                    "mode": "rules-natural-language-fallback",
                    "priority": "fallback",
                    "notes": "当 slash 未刷新或当前会话已在恢复路径中时，回退到统一自然语言入口。",
                }
            )
        else:
            variants.append(
                {
                    "surface": "default",
                    "label": label,
                    "entry": trigger,
                    "mode": "rules-natural-language",
                    "priority": "preferred",
                    "notes": "在当前宿主会话中使用统一自然语言入口进入 Super Dev 流程。",
                }
            )
        return variants

    def _certification_profile(self, target: str) -> dict[str, object]:
        raw = self.HOST_CERTIFICATIONS.get(target, {})
        level = str(raw.get("level", "experimental")).strip().lower()
        if level not in self.CERTIFICATION_LABELS:
            level = "experimental"
        normalized_evidence = self._string_list(raw.get("evidence"))
        return {
            "level": level,
            "label": self.CERTIFICATION_LABELS[level],
            "reason": str(raw.get("reason", "")).strip(),
            "evidence": normalized_evidence,
        }

    def list_adapter_profiles(self, targets: list[str] | None = None) -> list[HostAdapterProfile]:
        selected = targets or sorted(self.TARGETS.keys())
        return [self.get_adapter_profile(target) for target in selected]

    def host_hardening_blueprint(
        self,
        target: str,
        *,
        include_user_surfaces: bool = False,
    ) -> dict[str, object]:
        profile = self.get_adapter_profile(target)
        trigger_mode = "slash" if self.supports_slash(target) else "text"
        required_steps = [
            "setup project integration files",
            "inject system flow contract markers",
            "audit surface contract markers",
            "generate host usage profile",
        ]
        if self.supports_slash(target):
            required_steps.append("setup project slash command")
            if include_user_surfaces:
                required_steps.append("setup user-level slash command")
        if self.requires_skill(target):
            required_steps.append("install skill to host skill directory")
        required_user_surfaces = list(profile.official_user_surfaces)
        if include_user_surfaces:
            required_user_surfaces.extend(
                item
                for item in profile.optional_user_surfaces
                if item not in required_user_surfaces
            )
        protocol_mode = str(profile.host_protocol_mode or "")
        if protocol_mode:
            required_steps.append(f"apply host protocol mode: {protocol_mode}")
        return {
            "host": target,
            "trigger_mode": trigger_mode,
            "final_trigger": profile.trigger_command,
            "required_steps": required_steps,
            "required_project_surfaces": list(profile.official_project_surfaces),
            "required_user_surfaces": required_user_surfaces,
            "optional_project_surfaces": list(profile.optional_project_surfaces),
            "optional_user_surfaces": list(profile.optional_user_surfaces),
            "with_user_surfaces": include_user_surfaces,
        }

    def _official_docs_references(self, target: str) -> list[str]:
        references = list(self.OFFICIAL_DOCS_INDEX.get(target, ()))
        return [item.strip() for item in references if isinstance(item, str) and item.strip()]

    def _capability_labels(self, *, target: str) -> dict[str, str]:
        slash_label = "native" if self.supports_slash(target) else "none"
        if target in {"codex", "codex-cli"}:
            slash_label = "skill-list"
        protocol = self._protocol_profile(target=target)
        mode = str(protocol.get("mode", "")).strip().lower()
        if mode in {"official-context", "official-steering"}:
            rules_label = "official"
        elif mode.startswith("official"):
            rules_label = "official"
        else:
            rules_label = "compat"
        if self.requires_skill(target):
            compatibility_skill_targets = {
                "cursor-cli",
                "cursor",
                "gemini-cli",
                "trae",
                "trae-solo",
            }
            skill_label = "compat" if target in compatibility_skill_targets else "official"
        else:
            skill_label = "none"
        trigger_label = "slash" if self.supports_slash(target) else "text"
        return {
            "slash": slash_label,
            "rules": rules_label,
            "skills": skill_label,
            "trigger": trigger_label,
        }

    def verify_official_docs(
        self, target: str, *, timeout_seconds: float = 5.0
    ) -> dict[str, object]:
        references = self._official_docs_references(target)
        if not references:
            return {
                "target": target,
                "status": "missing",
                "checked": 0,
                "reachable": 0,
                "unreachable": 0,
                "details": [],
            }
        details: list[dict[str, object]] = []
        reachable = 0
        for url in references:
            probe = self._probe_official_url(url=url, timeout_seconds=timeout_seconds)
            ok = bool(probe.get("reachable", False))
            code = probe.get("status_code")
            reason = str(probe.get("error", ""))
            if ok:
                reachable += 1
            details.append(
                {
                    "url": url,
                    "reachable": ok,
                    "status_code": code,
                    "error": reason,
                    "method": str(probe.get("method", "")),
                    "tls_mode": str(probe.get("tls_mode", "")),
                }
            )
        checked = len(details)
        status = "verified" if reachable == checked else ("partial" if reachable > 0 else "failed")
        return {
            "target": target,
            "status": status,
            "checked": checked,
            "reachable": reachable,
            "unreachable": checked - reachable,
            "details": details,
        }

    def _fetch_official_doc_excerpt(
        self,
        url: str,
        *,
        timeout_seconds: float = 5.0,
        max_bytes: int = 120000,
    ) -> dict[str, object]:
        probe = self._probe_official_url(
            url=url,
            timeout_seconds=timeout_seconds,
            read_content=True,
            max_bytes=max_bytes,
        )
        return {
            "url": url,
            "reachable": bool(probe.get("reachable", False)),
            "status_code": probe.get("status_code"),
            "error": str(probe.get("error", "")),
            "content": str(probe.get("content", "")),
            "method": str(probe.get("method", "")),
            "tls_mode": str(probe.get("tls_mode", "")),
        }

    def _probe_official_url(
        self,
        *,
        url: str,
        timeout_seconds: float,
        read_content: bool = False,
        max_bytes: int = 120000,
        redirects_remaining: int = 3,
    ) -> dict[str, object]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return {
                "url": url,
                "reachable": False,
                "status_code": None,
                "error": f"unsupported_url_scheme:{parsed.scheme or 'missing'}",
                "content": "",
                "method": "",
                "tls_mode": "strict",
            }
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; super-dev-host-audit/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        attempts: list[tuple[str, bool]]
        if read_content:
            attempts = [("GET", True), ("GET", False)]
        else:
            attempts = [("HEAD", True), ("GET", True), ("GET", False)]
        last_error = ""
        last_status: int | None = None
        for method, strict_tls in attempts:
            try:
                req = urllib_request.Request(url, headers=headers, method=method)
                if not strict_tls:
                    # 不降级到不安全连接，跳过此尝试
                    continue
                with urllib_request.urlopen(req, timeout=timeout_seconds) as resp:  # nosec B310
                    status = int(getattr(resp, "status", 200))
                    content = ""
                    if read_content and method == "GET":
                        content = resp.read(max_bytes).decode("utf-8", errors="ignore")
                    return {
                        "url": url,
                        "reachable": 200 <= status < 400,
                        "status_code": status,
                        "error": "",
                        "content": content,
                        "method": method,
                        "tls_mode": "strict" if strict_tls else "insecure-fallback",
                    }
            except urllib_error.HTTPError as exc:
                status = int(getattr(exc, "code", 0) or 0)
                last_status = status
                last_error = str(exc)
                if status in {301, 302, 303, 307, 308} and redirects_remaining > 0:
                    location = str(exc.headers.get("Location", "")).strip()
                    redirected_url = urljoin(url, location) if location else ""
                    redirected = urlparse(redirected_url) if redirected_url else None
                    if (
                        redirected is not None
                        and redirected.scheme in {"http", "https"}
                        and redirected_url != url
                    ):
                        result = self._probe_official_url(
                            url=redirected_url,
                            timeout_seconds=timeout_seconds,
                            read_content=read_content,
                            max_bytes=max_bytes,
                            redirects_remaining=redirects_remaining - 1,
                        )
                        result["redirected_from"] = url
                        return result
                if method == "HEAD" and status in {401, 403, 405, 406, 429}:
                    continue
                if 200 <= status < 400:
                    return {
                        "url": url,
                        "reachable": True,
                        "status_code": status,
                        "error": str(exc),
                        "content": "",
                        "method": method,
                        "tls_mode": "strict" if strict_tls else "insecure-fallback",
                    }
                if method == "GET" and not strict_tls:
                    break
            except Exception as exc:
                last_error = str(exc)
                if method == "HEAD":
                    continue
                if method == "GET" and strict_tls:
                    continue
                break
        try:
            return {
                "url": url,
                "reachable": False,
                "status_code": last_status,
                "error": last_error,
                "content": "",
                "method": "GET",
                "tls_mode": "strict",
            }
        except Exception:
            return {
                "url": url,
                "reachable": False,
                "status_code": last_status,
                "error": last_error,
                "content": "",
                "method": "GET",
                "tls_mode": "strict",
            }

    def compare_official_capabilities(
        self, target: str, *, timeout_seconds: float = 5.0
    ) -> dict[str, object]:
        references = self._official_docs_references(target)
        expected = self._capability_labels(target=target)
        if not references:
            return {
                "target": target,
                "status": "missing",
                "expected": expected,
                "checked_urls": 0,
                "reachable_urls": 0,
                "checks": {},
                "details": [],
            }
        fetched = [
            self._fetch_official_doc_excerpt(url, timeout_seconds=timeout_seconds)
            for url in references
        ]
        reachable = [item for item in fetched if bool(item.get("reachable", False))]
        corpus = "\n".join(str(item.get("content", "")).lower() for item in reachable)
        checks: dict[str, dict[str, object]] = {}
        keyword_map: dict[str, tuple[str, ...]] = {
            "slash": ("slash", "/super-dev", "commands", "workflow"),
            "rules": ("rules", "instruction", "guideline", "agents.md", "steering", "context"),
            "skills": ("skill", "skills", "subagent", "sub-agents", "agent"),
        }
        required = 0
        passed = 0
        for capability in ("slash", "rules", "skills"):
            label = str(expected.get(capability, "")).strip().lower()
            if label == "none":
                checks[capability] = {
                    "expected": label,
                    "ok": True,
                    "matched_keywords": [],
                    "reason": "not-required",
                }
                continue
            required += 1
            keywords = keyword_map.get(capability, ())
            matched = [item for item in keywords if item in corpus]
            ok = bool(matched) and bool(reachable)
            if ok:
                passed += 1
            checks[capability] = {
                "expected": label,
                "ok": ok,
                "matched_keywords": matched,
                "reason": (
                    "matched"
                    if ok
                    else ("no-reachable-docs" if not reachable else "keyword-mismatch")
                ),
            }
        if not reachable:
            status = "unknown"
        elif required == 0:
            status = "passed"
        elif passed == required:
            status = "passed"
        elif passed > 0:
            status = "partial"
        else:
            status = "failed"
        return {
            "target": target,
            "status": status,
            "expected": expected,
            "checked_urls": len(fetched),
            "reachable_urls": len(reachable),
            "checks": checks,
            "details": [
                {
                    "url": str(item.get("url", "")),
                    "reachable": bool(item.get("reachable", False)),
                    "status_code": item.get("status_code"),
                    "error": str(item.get("error", "")),
                }
                for item in fetched
            ],
        }

    def _codex_home_dir(self) -> Path:
        return self.user_directories.codex_home

    def resolve_global_protocol_path(self, target: str) -> Path | None:
        home = self.user_directories.home
        mapping = {
            "claude": None,
            "claude-code": home / ".claude" / "CLAUDE.md",
            "codebuddy-cli": home / ".codebuddy" / "CODEBUDDY.md",
            "codebuddy": home / ".codebuddy" / "CODEBUDDY.md",
            "codebuddy-cn": home / ".codebuddy" / "CODEBUDDY.md",
            "droid-cli": home / ".factory" / "AGENTS.md",
            "codex": self._codex_home_dir() / "AGENTS.md",
            "codex-cli": self._codex_home_dir() / "AGENTS.md",
            "copilot-cli": home / ".copilot" / "copilot-instructions.md",
            "kiro-cli": home / ".kiro" / "steering" / "super-dev.md",
            "kiro": home / ".kiro" / "steering" / "super-dev.md",
            "gemini-cli": home / ".gemini" / "GEMINI.md",
            "antigravity": home / ".gemini" / "GEMINI.md",
            "opencode": home / ".config" / "opencode" / "AGENTS.md",
            "qoder-cli": home / ".qoder" / "AGENTS.md",
            "qoder": home / ".qoder" / "AGENTS.md",
            "qwen-code": home / ".qwen" / "QWEN.md",
            "trae": home / ".trae" / "user_rules.md",
            "trae-cn": home / ".trae-cn" / "skills" / "super-dev" / "SKILL.md",
        }
        return mapping.get(target)

    def resolve_compatibility_protocol_path(self, target: str) -> Path | None:
        if target in {"trae", "trae-cn"}:
            return self.user_directories.home / ".trae" / "rules.md"
        return None

    def expected_skill_path(
        self,
        target: str,
        skill_name: str = "super-dev",
        project_dir: Path | None = None,
    ) -> Path | None:
        paths = self.expected_skill_paths(
            target=target, skill_name=skill_name, project_dir=project_dir
        )
        return paths[0] if paths else None

    def expected_skill_paths(
        self,
        target: str,
        skill_name: str = "super-dev",
        project_dir: Path | None = None,
    ) -> list[Path]:
        from ..skills import SkillManager

        if not self.requires_skill(target):
            return []
        paths: list[Path] = []
        project_root = Path(project_dir).resolve() if project_dir is not None else None
        surface_kind = SkillManager.target_path_kind(target)
        for name in SkillManager.compatibility_skill_names(target, skill_name):
            if project_root is not None:
                if target in {"codex", "codex-cli"}:
                    paths.append(project_root / ".agents" / "skills" / name / "SKILL.md")
                elif target == "claude-code":
                    paths.append(project_root / ".claude" / "skills" / name / "SKILL.md")
                elif target in {"codebuddy", "codebuddy-cli", "codebuddy-cn"}:
                    paths.append(project_root / ".codebuddy" / "skills" / name / "SKILL.md")
                elif target == "kimi-code":
                    paths.append(project_root / ".kimi" / "skills" / name / "SKILL.md")
                elif target == "qwen-code":
                    paths.append(project_root / ".qwen" / "skills" / name / "SKILL.md")
                elif target == "trae-cn":
                    paths.append(project_root / ".trae" / "skills" / name / "SKILL.md")
                elif target in {"trae-solo", "trae-solocn"}:
                    paths.append(project_root / ".trae" / "skills" / name / "SKILL.md")
            if target not in SkillManager.TARGET_PATHS:
                continue
            target_root = self.user_directories.expanduser(SkillManager.TARGET_PATHS[target])
            if surface_kind == "observed-compatibility-surface" and not target_root.exists():
                continue
            paths.append(target_root / name / "SKILL.md")
            for mirror in SkillManager.COMPATIBILITY_MIRROR_PATHS.get(target, []):
                mirror_root = (
                    self._codex_home_dir() / "skills"
                    if target in {"codex", "codex-cli"}
                    else self.user_directories.expanduser(mirror)
                )
                paths.append(mirror_root / name / "SKILL.md")
        deduped: list[Path] = []
        seen: set[str] = set()
        for item in paths:
            key = str(item)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @classmethod
    def contract_validation_groups(cls, target: str) -> list[tuple[str, tuple[str, ...]]]:
        trigger_group = cls.CONTRACT_TRIGGER_GROUPS[
            "slash" if cls.supports_slash(target) else "text"
        ]
        return [
            ("trigger", trigger_group),
            ("documents", cls.CONTRACT_DOC_GROUP),
            ("confirmation", cls.CONTRACT_CONFIRMATION_GROUP),
            ("artifacts", cls.CONTRACT_ARTIFACT_GROUP),
            ("flow", cls.CONTRACT_FLOW_GROUP),
        ]

    @classmethod
    def audit_contract_text(cls, target: str, content: str) -> list[str]:
        normalized = content or ""
        missing: list[str] = []
        for label, options in cls.contract_validation_groups(target):
            if not any(option in normalized for option in options):
                missing.append(label)
        return missing

    @classmethod
    def contract_validation_groups_for_surface(
        cls,
        target: str,
        surface_key: str,
        surface_path: Path,
    ) -> list[tuple[str, tuple[str, ...]]]:
        groups = cls.contract_validation_groups(target)
        trigger_group = groups[0]
        documents_group = groups[1]
        confirmation_group = groups[2]
        artifacts_group = groups[3]
        flow_group = groups[4]

        normalized = surface_path.as_posix()

        if (
            normalized.endswith("/plugins/marketplace.json")
            or normalized.endswith("/.codex-plugin/plugin.json")
            or normalized.endswith("/.claude-plugin/plugin.json")
            or normalized.endswith("/.claude-plugin/marketplace.json")
        ):
            return []

        if normalized.endswith("/plugins/super-dev-codex/README.md") or normalized.endswith(
            "/plugins/super-dev-claude/README.md"
        ):
            return []

        if (
            "/plugins/super-dev-codex/skills/" in normalized
            or "/plugins/super-dev-claude/skills/" in normalized
        ):
            return []

        if "super-dev-seeai" in normalized:
            if (
                surface_key.startswith("project-slash:")
                or surface_key.startswith("global-slash:")
                or normalized.endswith("/commands/super-dev-seeai.md")
                or normalized.endswith("/commands/super-dev-seeai.toml")
                or normalized.endswith("/workflows/super-dev-seeai.md")
            ):
                return [trigger_group, flow_group]
            if surface_key.startswith("skill:") or "/skills/super-dev-seeai/" in normalized:
                return [trigger_group, flow_group]

        if (
            surface_key.startswith("project-slash:")
            or surface_key.startswith("global-slash:")
            or normalized.endswith("/commands/super-dev.md")
            or normalized.endswith("/commands/super-dev.toml")
        ):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        if surface_key.startswith("skill:"):
            return [trigger_group, documents_group, confirmation_group, artifacts_group, flow_group]

        if surface_key.startswith("compatibility-protocol:"):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        if normalized.endswith(".agent/workflows/super-dev.md"):
            return [documents_group, confirmation_group, flow_group]

        if normalized.endswith("/agents/super-dev.md"):
            return [trigger_group, documents_group, confirmation_group, artifacts_group, flow_group]

        if normalized.endswith("AGENTS.md") and cls._managed_agents_markers(target) is not None:
            return [trigger_group, documents_group, confirmation_group, artifacts_group, flow_group]

        if normalized.endswith("GEMINI.md"):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        if normalized.endswith("/steering/AGENTS.md") or normalized.endswith(
            "/steering/super-dev.md"
        ):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        if (
            normalized.endswith("/rules.md")
            or normalized.endswith("/project_rules.md")
            or normalized.endswith("/rules/super-dev.md")
        ):
            return [trigger_group, documents_group, confirmation_group, flow_group]

        return [documents_group, confirmation_group, flow_group]

    @classmethod
    def audit_surface_contract(
        cls,
        target: str,
        surface_key: str,
        surface_path: Path,
        content: str,
    ) -> list[str]:
        normalized = content or ""
        missing: list[str] = []
        for label, options in cls.contract_validation_groups_for_surface(
            target, surface_key, surface_path
        ):
            if not any(option in normalized for option in options):
                missing.append(label)
        return missing

    def collect_managed_surface_paths(
        self,
        target: str,
        skill_name: str = "super-dev",
        *,
        include_user_surfaces: bool = True,
    ) -> dict[str, Path]:
        if target not in self.TARGETS:
            raise ValueError(f"Unsupported target: {target}")

        surfaces: dict[str, Path] = {}
        for relative in self.TARGETS[target].files:
            surfaces[f"project:{relative}"] = self.project_dir / relative
        for relative in self.managed_competition_project_surfaces(target):
            surfaces[f"project:{relative}"] = self.project_dir / relative

        if include_user_surfaces:
            protocol_path = self.resolve_global_protocol_path(target)
            if protocol_path is not None:
                surfaces[f"global-protocol:{protocol_path}"] = protocol_path
            for surface in self.managed_user_agent_surfaces(target):
                surface_path = self._resolve_surface_declaration(target=target, surface=surface)
                surfaces[f"global-agent:{surface_path}"] = surface_path

        compatibility_protocol_path = self.resolve_compatibility_protocol_path(target)
        if compatibility_protocol_path is not None:
            surfaces[f"compatibility-protocol:{compatibility_protocol_path}"] = (
                compatibility_protocol_path
            )

        if self.supports_slash(target):
            project_slash = self.resolve_slash_command_path(
                target=target,
                scope="project",
                project_dir=self.project_dir,
                user_directories=self.user_directories,
            )
            if project_slash is not None:
                surfaces[f"project-slash:{project_slash}"] = project_slash
            if include_user_surfaces:
                global_slash = self.resolve_slash_command_path(
                    target=target,
                    scope="global",
                    user_directories=self.user_directories,
                )
                if global_slash is not None and global_slash != project_slash:
                    surfaces[f"global-slash:{global_slash}"] = global_slash

        from ..skills import SkillManager

        managed_skill_names = SkillManager.managed_builtin_skill_names(target)
        if skill_name not in managed_skill_names:
            managed_skill_names.append(skill_name)
        for managed_skill_name in managed_skill_names:
            for skill_path in self.expected_skill_paths(
                target=target, skill_name=managed_skill_name
            ):
                surfaces[f"skill:{skill_path}"] = skill_path

        return surfaces

    def _resolve_surface_declaration(self, *, target: str, surface: str) -> Path:
        normalized = str(surface).strip()
        if normalized == "~/.codex/AGENTS.md":
            return self.resolve_global_protocol_path("codex") or self.user_directories.expanduser(
                normalized
            )
        if normalized.startswith("~/"):
            return self.user_directories.expanduser(normalized)
        return self.project_dir / normalized

    def surface_path_groups(
        self,
        *,
        target: str,
    ) -> dict[str, dict[str, Path]]:
        surfaces = self._install_surfaces(target=target)
        groups: dict[str, dict[str, Path]] = {
            "official_project": {},
            "official_user": {},
            "optional_project": {},
            "optional_user": {},
            "compatibility": {},
        }
        mapping = {
            "official_project_surfaces": "official_project",
            "official_user_surfaces": "official_user",
            "optional_project_surfaces": "optional_project",
            "optional_user_surfaces": "optional_user",
            "observed_compatibility_surfaces": "compatibility",
        }
        for source_key, group_key in mapping.items():
            for surface in surfaces.get(source_key, []):
                if not isinstance(surface, str) or not surface.strip():
                    continue
                path = self._resolve_surface_declaration(target=target, surface=surface)
                groups[group_key][surface] = path
        return groups

    def managed_surface_classification(
        self,
        *,
        target: str,
        skill_name: str = "super-dev",
    ) -> dict[str, dict[str, Any]]:
        managed = self.collect_managed_surface_paths(target=target, skill_name=skill_name)
        groups = self.surface_path_groups(target=target)
        group_path_sets = {
            name: {str(path.resolve()) for path in surfaces.values()}
            for name, surfaces in groups.items()
        }
        classified: dict[str, dict[str, Any]] = {}
        for surface_key, surface_path in managed.items():
            resolved = str(surface_path.resolve())
            group = "unclassified"
            for candidate, path_set in group_path_sets.items():
                if resolved in path_set:
                    group = candidate
                    break
            classified[surface_key] = {
                "path": surface_path,
                "group": group,
                "required": group in {"official_project", "official_user"},
            }
        return classified

    def readiness_surface_sets(
        self,
        *,
        target: str,
        skill_name: str = "super-dev",
    ) -> dict[str, list[Path]]:
        groups = self.surface_path_groups(target=target)
        skill_paths = self.expected_skill_paths(
            target=target,
            skill_name=skill_name,
            project_dir=self.project_dir,
        )

        official_skill_paths: list[Path] = []
        optional_skill_paths: list[Path] = []
        compatibility_skill_paths: list[Path] = []
        project_paths = {str(item.resolve()) for item in groups["official_project"].values()}
        user_paths = {str(item.resolve()) for item in groups["official_user"].values()}
        for path in skill_paths:
            resolved = str(path.resolve())
            if resolved in project_paths or (not project_paths and resolved in user_paths):
                official_skill_paths.append(path)
            elif (
                resolved in user_paths
                or resolved in {str(item.resolve()) for item in groups["optional_project"].values()}
                or resolved in {str(item.resolve()) for item in groups["optional_user"].values()}
            ):
                optional_skill_paths.append(path)
            else:
                compatibility_skill_paths.append(path)

        project_slash: Path | None = None
        global_slash: Path | None = None
        if self.supports_slash(target):
            project_slash = self.resolve_slash_command_path(
                target=target,
                scope="project",
                project_dir=self.project_dir,
                user_directories=self.user_directories,
            )
            global_slash = self.resolve_slash_command_path(
                target=target,
                scope="global",
                user_directories=self.user_directories,
            )
        required_slash_paths: list[Path] = []
        optional_slash_paths: list[Path] = []
        compatibility_slash_paths: list[Path] = []
        official_project_resolved = {
            str(item.resolve()) for item in groups["official_project"].values()
        }
        official_user_resolved = {str(item.resolve()) for item in groups["official_user"].values()}
        optional_project_resolved = {
            str(item.resolve()) for item in groups["optional_project"].values()
        }
        optional_user_resolved = {str(item.resolve()) for item in groups["optional_user"].values()}
        require_user_level_slash = not bool(official_project_resolved)
        for slash_path in [project_slash, global_slash]:
            if slash_path is None:
                continue
            resolved = str(slash_path.resolve())
            if resolved in official_project_resolved or (
                require_user_level_slash and resolved in official_user_resolved
            ):
                required_slash_paths.append(slash_path)
            elif (
                resolved in official_user_resolved
                or resolved in optional_project_resolved
                or resolved in optional_user_resolved
            ):
                optional_slash_paths.append(slash_path)
            else:
                compatibility_slash_paths.append(slash_path)

        return {
            "official_project": list(groups["official_project"].values()),
            "official_user": list(groups["official_user"].values()),
            "optional_project": list(groups["optional_project"].values()),
            "optional_user": list(groups["optional_user"].values()),
            "compatibility": list(groups["compatibility"].values()),
            "official_skill": official_skill_paths,
            "optional_skill": optional_skill_paths,
            "compatibility_skill": compatibility_skill_paths,
            "required_slash": required_slash_paths,
            "optional_slash": optional_slash_paths,
            "compatibility_slash": compatibility_slash_paths,
        }

    def remove(self, target: str) -> list[Path]:
        """卸载指定宿主的 Super Dev 集成文件"""
        surfaces = self.collect_managed_surface_paths(target=target)
        removed: list[Path] = []
        for _key, path in surfaces.items():
            if path.exists():
                try:
                    if path.name == "AGENTS.md":
                        markers = self._managed_agents_markers(target)
                        if markers is not None and self._remove_managed_block(
                            file_path=path,
                            begin=markers[0],
                            end=markers[1],
                        ):
                            removed.append(path)
                            continue
                    if target == "claude-code" and path.name == "CLAUDE.md":
                        if self._remove_managed_block(
                            file_path=path,
                            begin=self.CLAUDE_RULES_BEGIN,
                            end=self.CLAUDE_RULES_END,
                        ):
                            removed.append(path)
                            continue
                    path.unlink()
                    removed.append(path)
                    # 清理空父目录
                    parent = path.parent
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                except OSError:
                    pass
        return removed

    def _adapter_mode(self, *, target: str, category: str, integration_files: list[str]) -> str:
        first_file = integration_files[0] if integration_files else ""
        adapter_override = get_adapter_mode_override(target)
        if adapter_override:
            return adapter_override
        if category == "cli":
            return "native-cli-session"
        if category == "assistant":
            return "native-desktop-assistant"
        if first_file.startswith(".super-dev/skills/"):
            return "compat-layer-via-project-skill"
        if target == "vscode-copilot":
            return "native-copilot-instruction-file"
        return "native-ide-rule-file"

    def _usage_profile(self, *, target: str, category: str) -> dict[str, object]:
        usage_location = self.HOST_USAGE_LOCATIONS.get(target, "")
        usage_notes = list(self.HOST_USAGE_NOTES.get(target, []))
        shared_usage_notes = [
            "普通开发尽量留在宿主里，不要把终端里的维护命令当成日常主入口。",
            "已有项目做 evolve / variant / patch 时，先让宿主完成 baseline，再进入差量文档与实现。",
            "窗口关闭、电脑重启或第二天回来时，优先直接在宿主里说“继续当前流程”或使用 resume 入口。",
        ]
        for note in shared_usage_notes:
            if note not in usage_notes:
                usage_notes.append(note)
        special_usage = build_special_usage_profile(
            SpecialAdapterContext(
                target=target,
                category=category,
                usage_location=usage_location,
                usage_notes=tuple(usage_notes),
                text_trigger_prefix=self.TEXT_TRIGGER_PREFIX,
                seeai_text_trigger_prefix=self.SEEAI_TEXT_TRIGGER_PREFIX,
            )
        )
        if special_usage is not None:
            return special_usage
        if target == "codex":
            return {
                "usage_mode": "desktop-skill-and-agents",
                "primary_entry": "Codex App/Desktop 优先从 `/` 列表选择 `super-dev`；自然语言回退入口是 `super-dev: <需求描述>`。",
                "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                "entry_variants": [
                    {
                        "surface": "desktop",
                        "label": "Codex App/Desktop",
                        "entry": "/super-dev",
                        "mode": "enabled-skill-slash-entry",
                        "priority": "preferred",
                        "notes": "在 `/` 列表中直接选择 `super-dev`；这是已启用 Skill 的官方入口。",
                    },
                    {
                        "surface": "all",
                        "label": "Natural Language Fallback",
                        "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                        "mode": "agents-natural-language-fallback",
                        "priority": "fallback",
                        "notes": "由项目 AGENTS.md 驱动的自然语言入口。",
                    },
                ],
                "trigger_context": "Codex App/Desktop 当前会话",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重开 Codex App/Desktop，使项目 AGENTS 与 Skills 生效。",
                    "优先从 `/` 列表选择 `super-dev` 或 `super-dev-seeai`。",
                    "已有项目先 baseline；恢复时优先直接说 `super-dev: 继续当前流程`。",
                ],
                "usage_notes": usage_notes,
                "notes": "Codex App/Desktop 与 Codex CLI 共用 AGENTS.md + Skills 主面，但桌面端以 `/` 列表里的已启用 Skill 入口为第一入口。",
            }
        if target == "codex-cli":
            return {
                "usage_mode": "agents-and-skill",
                "primary_entry": "Codex CLI 优先显式输入 `$super-dev`；回退可用 `super-dev: <需求描述>` 作为 AGENTS 驱动的自然语言入口。",
                "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                "entry_variants": [
                    {
                        "surface": "cli",
                        "label": "Codex CLI",
                        "entry": "$super-dev",
                        "mode": "explicit-skill",
                        "priority": "preferred",
                        "notes": "CLI 中官方显式调用 Skill 的方式，最符合 Codex Skills 文档。",
                    },
                    {
                        "surface": "all",
                        "label": "Codex App/Desktop + CLI",
                        "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                        "mode": "agents-natural-language-fallback",
                        "priority": "fallback",
                        "notes": "默认由项目 AGENTS.md 驱动的自然语言入口；若显式启用 `--with-user-surfaces`，也可跨项目沿用全局 AGENTS 作为统一回退方式。",
                    },
                ],
                "trigger_context": "Codex 当前会话",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重启 codex，使项目根 AGENTS.md、项目级 .agents/skills/super-dev、repo marketplace `.agents/plugins/marketplace.json`、repo plugin `plugins/super-dev-codex/` 与 ~/.agents/skills/super-dev/SKILL.md 生效；如需跨项目用户级协议面，再显式启用 `--with-user-surfaces` 写入 CODEX_HOME/AGENTS.md。",
                    "Codex CLI 优先显式输入 `$super-dev`。",
                    "已有项目做增量迭代、派生版本或缺陷修复时，先让宿主完成 baseline，再继续三文档与实现。",
                    "中断后恢复优先用 `super-dev: 继续当前流程`，需要显式阶段跳转时使用 `super-dev-run: resume`。",
                    "如果你已经在自然语言上下文里继续当前流程，也可以直接说 `super-dev: <需求描述>`。",
                ],
                "usage_notes": usage_notes,
                "notes": "Codex CLI 官方最佳接入面是项目根 AGENTS.md + 分层 `.agents/skills` + 官方用户 skills 目录 ~/.agents/skills；repo 级 `.agents/plugins/marketplace.json` + `plugins/super-dev-codex/.codex-plugin/plugin.json` 作为可选 repo plugin enhancement 保留。CODEX_HOME/AGENTS.md（默认 ~/.codex/AGENTS.md）改成显式 `--with-user-surfaces` 才写入，用于跨项目复用统一宿主心智。Codex CLI 的官方显式入口是 `$super-dev`；`super-dev:` 作为 AGENTS 驱动的自然语言回退入口保留。已有项目的 `evolve / variant / patch` 必须先 baseline；恢复默认按当前 workflow state 继续，而不是重新开题。",
            }
        if target == "claude":
            return {
                "usage_mode": "desktop-projects-manual",
                "primary_entry": "在 Claude Desktop 当前 Project 中直接说 `super-dev: <需求描述>`；比赛模式说 `super-dev-seeai: <比赛需求>`。",
                "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                "entry_variants": [
                    {
                        "surface": "desktop",
                        "label": "Claude Project",
                        "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                        "mode": "projects-natural-language",
                        "priority": "preferred",
                        "notes": "依赖 Claude Project Instructions / Knowledge / extensions 的官方项目面。",
                    }
                ],
                "trigger_context": "Claude Desktop 当前 Project",
                "usage_location": usage_location,
                "requires_restart_after_onboard": False,
                "post_onboard_steps": [
                    "在 Claude 当前 Project 中挂上 Project Instructions、Project Knowledge 与需要的 extensions / local MCP。",
                    "随后直接说 `super-dev: <需求描述>`，不要先开普通闲聊线程。",
                ],
                "usage_notes": usage_notes,
                "notes": "Claude Desktop 当前按 Projects / Instructions / Knowledge / extensions 官方面建模，不依赖仓库 dotfile 自动注入。",
            }
        if target == "claude-code":
            return {
                "usage_mode": "native-slash-and-skill",
                "primary_entry": "在 Claude Code 当前项目会话里优先使用 `/super-dev <需求描述>`；底层由项目根 `CLAUDE.md`、项目级 `.claude/CLAUDE.md`、可选 `.claude/settings*.json`、项目/用户 `.claude/skills/` 与项目/用户 `.claude/agents/` 驱动，`.claude/commands/` 只作为兼容增强面保留。",
                "trigger_command": "/super-dev <需求描述>",
                "entry_variants": [
                    {
                        "surface": "app_cli",
                        "label": "Claude Code",
                        "entry": "/super-dev",
                        "mode": "native-slash",
                        "priority": "preferred",
                        "notes": "Slash 仍是用户最直接的触发入口，但其底层应汇入根 `CLAUDE.md` + skills-first 的同一条 Super Dev 流程。",
                    },
                    {
                        "surface": "all",
                        "label": "Fallback",
                        "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                        "mode": "rules-natural-language-fallback",
                        "priority": "fallback",
                        "notes": "自然语言回退入口仍保留，用于当前会话已在项目上下文中继续当前 Super Dev 流程。",
                    },
                ],
                "trigger_context": "Claude Code 当前项目会话",
                "usage_location": usage_location,
                "requires_restart_after_onboard": False,
                "post_onboard_steps": [
                    "确认项目根 `CLAUDE.md` 与项目级 `.claude/CLAUDE.md` 都已写入 Super Dev 规则块。",
                    "如果需要宿主级配置增强，确认 `.claude/settings.json` / `.claude/settings.local.json` 已包含当前接入所需配置与 hooks。",
                    "确认项目级 `.claude/skills/super-dev/SKILL.md` 与用户级 `~/.claude/skills/super-dev/SKILL.md` 已存在。",
                    "确认项目级 `.claude/agents/super-dev.md` 与用户级 `~/.claude/agents/super-dev.md` 已存在。",
                    "如需兼容命令面，再确认 `.claude/commands/super-dev.md` 已生成。",
                    "若要启用增强层，确认 `.claude-plugin/marketplace.json` 与 `plugins/super-dev-claude/.claude-plugin/plugin.json` 已存在。",
                    "在 Claude Code 当前项目会话里输入 `/super-dev <需求描述>` 触发完整流程。",
                    "已有项目的增量开发先做 baseline；关闭窗口或第二天回来时，优先说“继续当前流程”或显式执行 `/super-dev-run resume`。",
                ],
                "usage_notes": usage_notes,
                "notes": "Claude Code 当前最佳接入面是项目根 `CLAUDE.md` + 项目级 `.claude/CLAUDE.md` + 可选 `.claude/settings*.json` + 项目/用户 `.claude/skills/` + 项目/用户 `.claude/agents/`；`.claude/commands/` 保留为兼容增强面；repo 级 `.claude-plugin/marketplace.json` + `plugins/super-dev-claude/.claude-plugin/plugin.json` 作为可选 plugin enhancement 一并提供。已有项目的 `evolve / variant / patch` 必须先 baseline；恢复是默认场景，不应重新开题。",
            }
        if target == "antigravity":
            return {
                "usage_mode": "native-slash",
                "primary_entry": "在 Antigravity Agent Chat 输入 `/super-dev <需求描述>`（由 GEMINI.md + custom commands 主面承接；`.agent/workflows` 与 `~/.gemini/skills/` 只作为增强层）",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "Antigravity IDE Agent Chat",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重新打开 Antigravity，或至少新开一个 Agent Chat。",
                    "确认项目内已生成 `GEMINI.md`、`.gemini/commands/super-dev.toml` 与 `.agent/workflows/super-dev.md`。",
                    "若当前安装启用了增强层，再确认 `~/.gemini/skills/super-dev/SKILL.md` 已存在；只有显式 `--with-user-surfaces` 时才检查 `~/.gemini/GEMINI.md` 与 `~/.gemini/commands/super-dev.toml`。",
                    "在 Antigravity Agent Chat 输入 `/super-dev <需求描述>` 触发完整流程。",
                    "已有项目先 baseline；恢复时优先说“继续当前流程”。",
                ],
                "usage_notes": usage_notes,
                "notes": "Antigravity 当前按 GEMINI 上下文面 + custom commands 主面接入；`.agent/workflows` 与宿主级 Skill 只保留为当前推荐增强层。",
            }
        if target == "trae":
            return {
                "usage_mode": "rules-and-skill",
                "primary_entry": "在 Trae Agent Chat 输入 `super-dev: <需求描述>`（默认由 .trae/project_rules.md + .trae/rules.md 生效；用户级 ~/.trae/* 仅在显式 `--with-user-surfaces` 时写入；兼容 Skill 若检测到会额外增强）",
                "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                "trigger_context": "Trae Agent Chat",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重新打开 Trae，或至少新开一个 Agent Chat，使新的规则与兼容 Skill（若已安装）一起生效。",
                    "默认确认项目内已生成 `.trae/project_rules.md` 与 `.trae/rules.md`；只有显式 `--with-user-surfaces` 时再检查 `~/.trae/user_rules.md` 与 `~/.trae/rules.md`。",
                    "确保当前项目就是已接入 Super Dev 的工作区。",
                    "输入 `super-dev: <需求描述>` 触发完整流程。",
                    "按 output/* 与 .super-dev/changes/*/tasks.md 执行开发。",
                ],
                "usage_notes": usage_notes,
                "notes": "该宿主当前默认以项目级 `.trae/project_rules.md` 与 `.trae/rules.md` 为核心接入面；用户级 `~/.trae/user_rules.md` / `~/.trae/rules.md` 改成显式 `--with-user-surfaces` 时才写入，若检测到 ~/.trae/skills，则会增强安装 super-dev Skill。",
            }
        if target == "kiro":
            return {
                "usage_mode": "native-slash",
                "primary_entry": "在 Kiro IDE Agent Chat 输入 `/super-dev <需求描述>`（由 `.kiro/steering/super-dev.md` + `.kiro/skills/` / `~/.kiro/steering/` + `~/.kiro/skills/` 生效）",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "Kiro IDE Agent Chat",
                "usage_location": usage_location,
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重新打开 Kiro，或至少新开一个 Agent Chat，使 steering 与 skills 一起生效。",
                    "确保当前项目就是已接入 Super Dev 的工作区。",
                    "优先输入 `/super-dev <需求描述>` 触发完整流程；若当前会话只接受自然语言，再回退到 `super-dev: <需求描述>`。",
                    "已有项目先 baseline；恢复时优先说“继续当前流程”或执行 `/super-dev-run resume`。",
                    "按 output/* 与 .super-dev/changes/*/tasks.md 执行开发。",
                ],
                "usage_notes": usage_notes,
                "notes": "该宿主当前走官方 steering + skills 模式：项目级 `.kiro/steering/super-dev.md` 负责长期行为约束，项目级 `.kiro/skills/` 与 `~/.kiro/skills/` 提供能力增强，`~/.kiro/steering/` 提供全局 steering 记忆。",
            }
        if target == "kiro-cli":
            return {
                "usage_mode": "native-slash",
                "primary_entry": "在 Kiro CLI 会话输入 `/super-dev <需求描述>`（由 `.kiro/steering/super-dev.md` + `.kiro/skills/` / `~/.kiro/steering/` + `~/.kiro/skills/` 生效）",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "Kiro CLI 当前会话",
                "usage_location": usage_location
                or "进入目标项目目录后，重开 Kiro CLI 会话再触发。",
                "requires_restart_after_onboard": True,
                "post_onboard_steps": [
                    "完成接入后重开 Kiro CLI，使 `.kiro/steering/` 与 skills 在新会话里生效。",
                    "确认项目内已生成 `.kiro/steering/super-dev.md` 与 `.kiro/skills/super-dev/SKILL.md`。",
                    "确认用户目录已生成 `~/.kiro/steering/super-dev.md` 与 `~/.kiro/skills/super-dev/SKILL.md`。",
                    "在 Kiro CLI 会话里优先输入 `/super-dev <需求描述>`；若当前会话只接受自然语言，再回退到 `super-dev: <需求描述>`。",
                    "已有项目先 baseline；恢复时优先说“继续当前流程”或显式执行 `/super-dev-run resume`。",
                ],
                "usage_notes": usage_notes,
                "notes": "Kiro CLI 当前按官方 steering + skills 模式触发：steering 负责长期上下文和行为约束，skills 负责让宿主理解完整 Super Dev 流程；slash 入口是否出现应以宿主命令面实际暴露为准。",
            }
        if self.supports_slash(target):
            if category == "cli":
                return {
                    "usage_mode": "native-slash",
                    "primary_entry": "/super-dev <需求描述>（在该 CLI 宿主会话内）",
                    "trigger_command": "/super-dev <需求描述>",
                    "trigger_context": "当前 CLI 宿主会话",
                    "usage_location": usage_location
                    or "在项目目录启动宿主当前 CLI 会话后，直接在同一会话里触发。",
                    "requires_restart_after_onboard": False,
                    "post_onboard_steps": [
                        "保持在宿主当前会话中执行 /super-dev。",
                        "已有项目的 `evolve / variant / patch` 先 baseline，再继续文档和实现。",
                        "中断后恢复优先用 `/super-dev-run resume`，不支持 slash 时使用 `super-dev: 继续当前流程`。",
                        "让宿主先完成同类产品研究，再继续文档与编码阶段。",
                    ],
                    "usage_notes": usage_notes
                    or [
                        "建议在同一会话里连续完成 research、文档、Spec 与编码。",
                        "接入时还会安装宿主级 super-dev Skill，让宿主理解完整流水线契约。",
                    ],
                    "notes": "CLI 宿主建议直接在当前会话执行 slash 命令；slash 负责触发，host skill 负责让宿主理解 Super Dev 流水线协议。已有项目先 baseline，恢复默认回到当前 workflow state。",
                }
            if category == "assistant":
                return {
                    "usage_mode": "desktop-slash",
                    "primary_entry": "/super-dev <需求描述>（在桌面助手当前工作区/会话内）",
                    "trigger_command": "/super-dev <需求描述>",
                    "trigger_context": "桌面助手当前工作区/会话",
                    "usage_location": usage_location
                    or "打开桌面助手当前工作区/会话，并保持目标项目上下文后触发。",
                    "requires_restart_after_onboard": False,
                    "post_onboard_steps": [
                        "在当前桌面助手工作区/会话中直接执行 /super-dev。",
                        "已有项目的 `evolve / variant / patch` 先 baseline，再继续三文档和实现。",
                        "中断后恢复优先说“继续当前流程”或直接回当前工作区/线程续跑。",
                    ],
                    "usage_notes": usage_notes,
                    "notes": "桌面助手优先通过当前工作区/会话触发；slash 负责进入流程，skills / rules / continuity 负责保持连续性。",
                }
            return {
                "usage_mode": "native-slash",
                "primary_entry": "/super-dev <需求描述>（在 IDE Agent Chat 内）",
                "trigger_command": "/super-dev <需求描述>",
                "trigger_context": "IDE Agent Chat",
                "usage_location": usage_location
                or "打开宿主 IDE 的 Agent Chat，在当前项目上下文内触发。",
                "requires_restart_after_onboard": False,
                "post_onboard_steps": [
                    "在 IDE Agent Chat 中执行 /super-dev。",
                    "已有项目的 `evolve / variant / patch` 先 baseline，再继续三文档和实现。",
                    "中断后恢复优先用 `/super-dev-run resume`，不支持 slash 的宿主则直接说“继续当前流程”。",
                    "保持研究、文档、Spec 与编码在同一上下文中连续完成。",
                ],
                "usage_notes": usage_notes
                or [
                    "建议固定在项目级 Agent Chat 中完成整条流水线。",
                    "接入时还会安装宿主级 super-dev Skill，让宿主理解完整流水线契约。",
                ],
                "notes": "IDE 宿主优先通过 Agent Chat 触发；slash 负责触发，host skill 负责让宿主理解 Super Dev 流水线协议。已有项目先 baseline，恢复默认回到当前 workflow state。",
            }
        return {
            "usage_mode": "rules-only",
            "primary_entry": "输入 `super-dev: <需求描述>`（由项目规则生效）",
            "trigger_command": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
            "entry_variants": [
                {
                    "surface": "default",
                    "label": "Default",
                    "entry": f"{self.TEXT_TRIGGER_PREFIX} <需求描述>",
                    "mode": "rules-natural-language",
                    "priority": "preferred",
                    "notes": "由项目规则文件驱动的标准入口。",
                }
            ],
            "trigger_context": "宿主当前会话",
            "usage_location": usage_location
            or (
                "在桌面助手当前会话里触发。"
                if category == "assistant"
                else "在宿主当前项目会话里触发。"
            ),
            "requires_restart_after_onboard": False,
            "post_onboard_steps": [
                "直接在宿主会话输入 `super-dev: <需求描述>`。",
                "已有项目先 baseline；关闭窗口或第二天回来时直接说 `super-dev: 继续当前流程`。",
                "按 output/* 与 tasks.md 继续执行开发流程。",
            ],
            "usage_notes": usage_notes
            or [
                "该宿主当前通过规则文件约束执行流程。",
            ],
            "notes": "该宿主通过项目规则文件约束执行流程。已有项目先 baseline，恢复默认沿用当前 workflow state 与 output 工件。",
        }

    def _smoke_profile(self, *, target: str, category: str) -> dict[str, object]:
        trigger = (
            self.TEXT_TRIGGER_PREFIX
            + " 请先不要开始编码，只回复 SMOKE_OK，并确认已读取当前项目中的 Super Dev 规则。"
        )
        competition_trigger = (
            self.SEEAI_TEXT_TRIGGER_PREFIX
            + " 请先不要开始编码，只回复 SEEAI_SMOKE_OK，并说明你会按半小时比赛链路执行：先 fast research、再 compact 三文档、确认后 compact Spec、然后 full-stack sprint；同时承诺 12 分钟内先跑出第一个可见界面，若初始化失败会立刻切轻量回退栈，且保留下来的模块都必须真实启动并进入主演示路径。"
        )
        if self.supports_slash(target):
            trigger = "/super-dev 请先不要开始编码，只回复 SMOKE_OK，并确认已读取当前项目中的 Super Dev 规则。"
            competition_trigger = "/super-dev-seeai 请先不要开始编码，只回复 SEEAI_SMOKE_OK，并说明你会按半小时比赛链路执行：先 fast research、再 compact 三文档、确认后 compact Spec、然后 full-stack sprint；同时承诺 12 分钟内先跑出第一个可见界面，若初始化失败会立刻切轻量回退栈，且保留下来的模块都必须真实启动并进入主演示路径。"
        if target == "codex":
            steps = [
                "完成接入后先重开 Codex App/Desktop。",
                "进入已接入 Super Dev 的目标项目工作区。",
                f"优先在 Codex App/Desktop 会话输入：{trigger}",
                "如果 `/` 列表里出现 `super-dev`，优先直接选择它。",
            ]
            competition_steps = [
                "完成接入后先重开 Codex App/Desktop。",
                "进入已接入 Super Dev 的目标项目工作区。",
                f"优先在 Codex App/Desktop 会话输入：{competition_trigger}",
                "如果 `/` 列表里出现 `super-dev-seeai`，优先直接选择它。",
            ]
        elif target == "codex-cli":
            steps = [
                "完成接入后先重启 codex。",
                "进入已接入 Super Dev 的项目目录。",
                f"优先在 Codex 会话输入：{trigger}",
                "如果你想显式调用官方 Skill，可输入 `$super-dev`；如果桌面端 `/` 列表里出现 `super-dev`，也可以直接选择它。",
            ]
            competition_steps = [
                "完成接入后先重启 codex。",
                "进入已接入 Super Dev 的项目目录。",
                f"优先在 Codex 会话输入：{competition_trigger}",
                "如果你想显式调用官方 SEEAI Skill，可输入 `$super-dev-seeai`；如果桌面端 `/` 列表里出现 `super-dev-seeai`，也可以直接选择它。",
            ]
        else:
            steps = [
                "进入已接入 Super Dev 的项目目录或工作区。",
                f"在宿主正确的聊天/会话入口输入：{trigger}",
            ]
            competition_steps = [
                "进入已接入 Super Dev 的项目目录或工作区。",
                f"在宿主正确的聊天/会话入口输入：{competition_trigger}",
            ]
        if category == "ide":
            steps.insert(1, "确认当前 Agent Chat/Workflow 绑定的是目标项目。")
            competition_steps.insert(1, "确认当前 Agent Chat/Workflow 绑定的是目标项目。")
        elif category == "assistant":
            steps.insert(1, "确认当前桌面助手会话/工作区绑定的是目标项目。")
            competition_steps.insert(1, "确认当前桌面助手会话/工作区绑定的是目标项目。")
        competition_steps.extend(get_competition_smoke_extra_steps(target))
        competition_suite = build_seeai_smoke_suite(
            "$super-dev-seeai"
            if target == "codex-cli"
            else (
                "/super-dev-seeai"
                if self.supports_slash(target)
                else self.SEEAI_TEXT_TRIGGER_PREFIX
            )
        )
        return {
            "smoke_test_prompt": trigger,
            "smoke_test_steps": steps,
            "smoke_success_signal": "宿主回复 SMOKE_OK，并明确表示已读取当前项目内的 Super Dev 规则/AGENTS/命令映射，且没有直接开始编码。",
            "competition_smoke_test_prompt": competition_trigger,
            "competition_smoke_test_steps": competition_steps,
            "competition_smoke_success_signal": "宿主回复 SEEAI_SMOKE_OK，并在首轮明确给出作品类型、wow 点、P0 主路径、主动放弃项，同时表示将按半小时比赛链路执行：fast research -> compact 三文档 -> docs confirm -> compact Spec -> full-stack sprint；且明确承诺 12 分钟内先跑出首个可见界面，初始化失败会立刻切轻量回退栈，保留下来的模块都必须真实启动并进入主演示路径。",
            "competition_smoke_suite": competition_suite,
            "competition_acceptance_gates": get_seeai_acceptance_gates(),
            "competition_evidence_template": build_seeai_evidence_template(),
        }

    def _precondition_profile(self, *, target: str) -> dict[str, object]:
        guidance = list(self.HOST_PRECONDITION_GUIDANCE.get(target, []))
        items: list[dict[str, object]] = []
        usage = self._usage_profile(
            target=target, category=HOST_TOOL_CATEGORY_MAP.get(target, "ide")
        )

        context_item: dict[str, object] = {
            "status": "project-context-required",
            "label": "需在目标项目/工作区内触发",
            "guidance": [str(usage["usage_location"]).strip()],
            "signals": {
                "project_dir_exists": self.project_dir.exists(),
            },
        }
        if str(usage["usage_location"]).strip():
            items.append(context_item)

        if bool(usage["requires_restart_after_onboard"]):
            items.append(
                {
                    "status": "session-restart-required",
                    "label": "接入后需重开宿主会话",
                    "guidance": [
                        "完成接入或维护修复后，关闭旧会话并新开一个宿主会话，再触发 Super Dev。",
                    ],
                    "signals": {},
                }
            )

        extra = [item for item in guidance if isinstance(item, str) and item.strip()]
        if extra and items:
            first_guidance = self._string_list(items[0].get("guidance"))
            items[0]["guidance"] = list(dict.fromkeys([*first_guidance, *extra]))

        if not items:
            return {
                "status": "none",
                "label": "无额外前置条件",
                "guidance": [],
                "signals": {},
                "items": [],
            }

        priority = {
            "host-auth-required": 0,
            "session-restart-required": 1,
            "project-context-required": 2,
        }
        primary = min(
            items,
            key=lambda item: priority.get(str(item.get("status", "")), 99),
        )
        combined_guidance: list[str] = []
        combined_signals: dict[str, bool] = {}
        for item in items:
            for guidance_item in self._string_list(item.get("guidance")):
                if guidance_item not in combined_guidance:
                    combined_guidance.append(guidance_item)
            for key, value in self._bool_dict(item.get("signals")).items():
                combined_signals[key] = value

        return {
            "status": str(primary.get("status", "none")),
            "label": str(primary.get("label", "无额外前置条件")),
            "guidance": combined_guidance,
            "signals": combined_signals,
            "items": items,
        }

    def _protocol_profile(self, *, target: str) -> dict[str, str]:
        registry_mode = str(get_protocol_mode(target) or "").strip()
        registry_summary = str(get_protocol_summary(target) or "").strip()
        if registry_mode or registry_summary:
            return {
                "mode": registry_mode or "custom",
                "summary": registry_summary or registry_mode or "custom host protocol",
            }

        mapping = {
            "claude-code": {
                "mode": "official-skill",
                "summary": "官方 CLAUDE.md + settings + project/user skills + subagents",
            },
            "antigravity": {
                "mode": "recommended-gemini-workflow",
                "summary": "当前推荐接入模型: GEMINI.md + custom commands + optional workflows",
            },
            "codebuddy-cli": {
                "mode": "official-skill",
                "summary": "官方 CODEBUDDY.md + commands + skills + AGENTS.md compatibility",
            },
            "codebuddy": {
                "mode": "official-subagent",
                "summary": "官方 CODEBUDDY.md + rules + skills + task/workspace continuity",
            },
            "vscode-copilot": {
                "mode": "official-context",
                "summary": "官方 copilot-instructions + AGENTS.md compatibility",
            },
            "cline": {
                "mode": "official-context",
                "summary": "官方 .clinerules + skills + AGENTS.md compatibility",
            },
            "roo-code": {
                "mode": "official-skill",
                "summary": "官方 commands + rules",
            },
            "qoder-cli": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + rules + commands + skills (+ optional agents)",
            },
            "qoder": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + rules + commands + skills (+ optional agents)",
            },
            "windsurf": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + rules + workflows + skills",
            },
            "opencode": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + commands + skills (+ optional agents)",
            },
            "kilo-code": {
                "mode": "official-rules",
                "summary": "官方 rules",
            },
            "kiro": {
                "mode": "official-steering",
                "summary": "官方 AGENTS.md + steering + skills + agent continuity",
            },
            "codex": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + Skills + App/Desktop enabled Skill entry",
            },
            "codex-cli": {
                "mode": "official-skill",
                "summary": "官方 AGENTS.md + Skills + CLI $skill entry",
            },
            "copilot-cli": {
                "mode": "official-context",
                "summary": "官方 copilot-instructions + AGENTS.md + skills + agents",
            },
            "cursor-cli": {
                "mode": "official-context",
                "summary": "官方 AGENTS.md + .cursor/rules + native resume",
            },
            "cursor": {
                "mode": "official-context",
                "summary": "官方 Agent Chat + AGENTS.md + rules (+ beta commands)",
            },
            "gemini-cli": {
                "mode": "official-context",
                "summary": "官方 GEMINI.md + settings + custom commands",
            },
            "kimi-code": {
                "mode": "official-agents-entry",
                "summary": "AGENTS.md + explicit /skill:/flow entries + native session resume",
            },
            "qwen-code": {
                "mode": "official-context",
                "summary": "官方 QWEN.md + settings + commands + skills + agents + /resume",
            },
            "droid-cli": {
                "mode": "official-factory",
                "summary": "官方 AGENTS.md + .factory/rules + skills (+ legacy commands)",
            },
            "kiro-cli": {
                "mode": "official-steering",
                "summary": "官方 AGENTS.md + steering + skills + native resume",
            },
            "trae": {
                "mode": "recommended-project-context",
                "summary": "当前推荐项目上下文模型: project rules + compatibility rules + optional skills",
            },
            "trae-cn": {
                "mode": "recommended-cn-workspace-flow",
                "summary": "当前推荐中文工作区模型: workspace skills + built-in /plan /spec + CN continuity",
            },
            "trae-solo": {
                "mode": "workspace-rules-commands-skills",
                "summary": "当前推荐工作区接入模型: rules + commands + skills + workspace continuity",
            },
            "trae-solocn": {
                "mode": "workspace-mtc-code-skills",
                "summary": "当前推荐中文工作区模型: MTC / Code + skills + built-in /plan /spec + continuity",
            },
            "codebuddy-cn": {
                "mode": "official-subagent",
                "summary": "官方 CODEBUDDY.md + rules + skills + 中文任务/workspace continuity",
            },
            "workbuddy": {
                "mode": "manual-task-workbench-mcp",
                "summary": "当前推荐任务工作台模型: Skills + MCP + task continuity",
            },
        }
        return mapping.get(target, {"mode": "none", "summary": ""})

    def _install_surfaces(self, *, target: str) -> dict[str, list[str]]:
        adapter_surfaces = get_special_install_surfaces(target)
        if adapter_surfaces is not None:
            adapter_surfaces.setdefault("optional_project_surfaces", [])
            adapter_surfaces.setdefault("optional_user_surfaces", [])
            return adapter_surfaces
        by_target: dict[str, dict[str, list[str]]] = {
            "claude": {
                "official_project_surfaces": [],
                "official_user_surfaces": [],
                "optional_project_surfaces": [],
                "optional_user_surfaces": [],
                "observed_compatibility_surfaces": [],
            },
            "claude-code": {
                "official_project_surfaces": [
                    "CLAUDE.md",
                    ".claude/CLAUDE.md",
                    ".claude/skills/super-dev/SKILL.md",
                    ".claude/agents/super-dev.md",
                ],
                "official_user_surfaces": [
                    "~/.claude/skills/super-dev/SKILL.md",
                    "~/.claude/agents/super-dev.md",
                ],
                "optional_project_surfaces": [
                    ".claude/settings.json",
                    ".claude/settings.local.json",
                    ".claude/commands/super-dev.md",
                    ".claude-plugin/marketplace.json",
                    "plugins/super-dev-claude/.claude-plugin/plugin.json",
                    "plugins/super-dev-claude/README.md",
                    "plugins/super-dev-claude/skills/super-dev/SKILL.md",
                ],
                "optional_user_surfaces": [
                    "~/.claude/CLAUDE.md",
                    "~/.claude/settings.json",
                    "~/.claude/commands/super-dev.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "antigravity": {
                "official_project_surfaces": [
                    "GEMINI.md",
                    ".gemini/commands/super-dev.toml",
                ],
                "official_user_surfaces": [],
                "optional_project_surfaces": [
                    ".agent/workflows/super-dev.md",
                ],
                "optional_user_surfaces": [
                    "~/.gemini/GEMINI.md",
                    "~/.gemini/commands/super-dev.toml",
                ],
                "observed_compatibility_surfaces": ["~/.gemini/skills/super-dev/SKILL.md"],
            },
            "vscode-copilot": {
                "official_project_surfaces": [".github/copilot-instructions.md"],
                "official_user_surfaces": [],
                "observed_compatibility_surfaces": ["AGENTS.md"],
            },
            "cline": {
                "official_project_surfaces": [
                    ".clinerules/super-dev.md",
                    ".cline/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": ["~/.cline/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": ["~/Documents/Cline/Rules/super-dev.md"],
                "observed_compatibility_surfaces": ["AGENTS.md"],
            },
            "kilo-code": {
                "official_project_surfaces": [
                    ".kilocode/rules/super-dev.md",
                    ".kilocode/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.kilocode/skills/super-dev/SKILL.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "roo-code": {
                "official_project_surfaces": [
                    ".roo/rules/super-dev.md",
                    ".roo/commands/super-dev.md",
                ],
                "official_user_surfaces": ["~/.roo/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": [
                    "~/.roo/rules/super-dev.md",
                    "~/.roo/commands/super-dev.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "codex-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".agents/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.agents/skills/super-dev/SKILL.md",
                ],
                "optional_project_surfaces": [
                    ".agents/plugins/marketplace.json",
                    "plugins/super-dev-codex/.codex-plugin/plugin.json",
                    "plugins/super-dev-codex/README.md",
                    "plugins/super-dev-codex/skills/super-dev/SKILL.md",
                ],
                "optional_user_surfaces": ["~/.codex/AGENTS.md"],
                "observed_compatibility_surfaces": ["~/.codex/skills/super-dev/SKILL.md"],
            },
            "codex": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".agents/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.agents/skills/super-dev/SKILL.md",
                ],
                "optional_project_surfaces": [
                    ".agents/plugins/marketplace.json",
                    "plugins/super-dev-codex/.codex-plugin/plugin.json",
                    "plugins/super-dev-codex/README.md",
                    "plugins/super-dev-codex/skills/super-dev/SKILL.md",
                ],
                "optional_user_surfaces": ["~/.codex/AGENTS.md"],
                "observed_compatibility_surfaces": [
                    "~/.agents/skills/super-dev/SKILL.md",
                    "~/.codex/skills/super-dev/SKILL.md",
                ],
            },
            "copilot-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".github/copilot-instructions.md",
                    ".github/agents/super-dev.md",
                    ".github/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.copilot/copilot-instructions.md",
                    "~/.copilot/agents/super-dev.md",
                    "~/.copilot/skills/super-dev/SKILL.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "cursor-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".cursor/rules/super-dev.mdc",
                ],
                "official_user_surfaces": [],
                "optional_project_surfaces": ["CLAUDE.md"],
                "observed_compatibility_surfaces": [
                    "~/.cursor/skills/super-dev/SKILL.md",
                ],
            },
            "cursor": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".cursor/rules/super-dev.mdc",
                ],
                "official_user_surfaces": [],
                "optional_project_surfaces": ["CLAUDE.md", ".cursor/commands/super-dev.md"],
                "optional_user_surfaces": ["~/.cursor/commands/super-dev.md"],
                "observed_compatibility_surfaces": [
                    "~/.cursor/skills/super-dev/SKILL.md",
                ],
            },
            "windsurf": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".windsurf/rules/super-dev.md",
                    ".windsurf/workflows/super-dev.md",
                    ".windsurf/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [],
                "optional_user_surfaces": ["~/.codeium/windsurf/skills/super-dev/SKILL.md"],
                "observed_compatibility_surfaces": [],
            },
            "gemini-cli": {
                "official_project_surfaces": ["GEMINI.md", ".gemini/commands/super-dev.toml"],
                "official_user_surfaces": [],
                "optional_project_surfaces": [".gemini/settings.json"],
                "optional_user_surfaces": [
                    "~/.gemini/GEMINI.md",
                    "~/.gemini/settings.json",
                    "~/.gemini/commands/super-dev.toml",
                    "~/.gemini/skills/super-dev/SKILL.md",
                ],
                "observed_compatibility_surfaces": ["~/.gemini/skills/super-dev/SKILL.md"],
            },
            "kiro-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".kiro/steering/super-dev.md",
                    ".kiro/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": ["~/.kiro/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": [
                    "~/.kiro/steering/super-dev.md",
                    "~/.kiro/steering/AGENTS.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "kiro": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".kiro/steering/super-dev.md",
                    ".kiro/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": ["~/.kiro/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": [
                    "~/.kiro/steering/super-dev.md",
                    "~/.kiro/steering/AGENTS.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "opencode": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".opencode/commands/super-dev.md",
                    ".opencode/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.config/opencode/AGENTS.md",
                    "~/.config/opencode/commands/super-dev.md",
                    "~/.config/opencode/skills/super-dev/SKILL.md",
                ],
                "optional_project_surfaces": [".opencode/agents/super-dev.md"],
                "optional_user_surfaces": ["~/.config/opencode/agents/super-dev.md"],
                "observed_compatibility_surfaces": [],
            },
            "qoder-cli": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".qoder/rules/super-dev.md",
                    ".qoder/commands/super-dev.md",
                    ".qoder/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.qoder/AGENTS.md",
                    "~/.qoder/commands/super-dev.md",
                    "~/.qoder/skills/super-dev/SKILL.md",
                ],
                "optional_project_surfaces": [".qoder/agents/super-dev.md"],
                "optional_user_surfaces": ["~/.qoder/agents/super-dev.md"],
                "observed_compatibility_surfaces": [],
            },
            "qoder": {
                "official_project_surfaces": [
                    "AGENTS.md",
                    ".qoder/rules/super-dev.md",
                    ".qoder/commands/super-dev.md",
                    ".qoder/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": [
                    "~/.qoder/AGENTS.md",
                    "~/.qoder/commands/super-dev.md",
                    "~/.qoder/skills/super-dev/SKILL.md",
                ],
                "optional_project_surfaces": [".qoder/agents/super-dev.md"],
                "optional_user_surfaces": ["~/.qoder/agents/super-dev.md"],
                "observed_compatibility_surfaces": [],
            },
            "trae": {
                "official_project_surfaces": [".trae/project_rules.md"],
                "official_user_surfaces": [],
                "optional_user_surfaces": ["~/.trae/user_rules.md"],
                "observed_compatibility_surfaces": [
                    ".trae/rules.md",
                    "~/.trae/rules.md",
                    "~/.trae/skills/super-dev/SKILL.md",
                ],
            },
            "trae-cn": {
                "official_project_surfaces": [
                    ".trae/project_rules.md",
                    ".trae/rules.md",
                    ".trae/skills/super-dev/SKILL.md",
                ],
                "official_user_surfaces": ["~/.trae-cn/skills/super-dev/SKILL.md"],
                "optional_user_surfaces": ["~/.trae/user_rules.md"],
                "observed_compatibility_surfaces": [
                    ".trae/rules.md",
                    "~/.trae/rules.md",
                ],
            },
            "codebuddy-cn": {
                "official_project_surfaces": [
                    "CODEBUDDY.md",
                    ".codebuddy/rules/super-dev/RULE.mdc",
                    ".codebuddy/skills/super-dev/SKILL.md",
                    ".codebuddy/skills/super-dev-seeai/SKILL.md",
                ],
                "official_user_surfaces": ["~/.codebuddy/skills/super-dev/SKILL.md"],
                "optional_project_surfaces": [
                    ".codebuddy/commands/super-dev.md",
                    ".codebuddy/agents/super-dev.md",
                    ".codebuddy/commands/super-dev-seeai.md",
                ],
                "optional_user_surfaces": [
                    "~/.codebuddy/CODEBUDDY.md",
                    "~/.codebuddy/agents/super-dev.md",
                    "~/.codebuddy/commands/super-dev-seeai.md",
                ],
                "observed_compatibility_surfaces": [],
            },
            "qwen-code": {
                "official_project_surfaces": [
                    "QWEN.md",
                    ".qwen/commands/super-dev.md",
                    ".qwen/skills/super-dev/SKILL.md",
                    ".qwen/agents/super-dev.md",
                ],
                "official_user_surfaces": [
                    "~/.qwen/QWEN.md",
                    "~/.qwen/skills/super-dev/SKILL.md",
                    "~/.qwen/commands/super-dev.md",
                    "~/.qwen/agents/super-dev.md",
                ],
                "optional_user_surfaces": [],
                "observed_compatibility_surfaces": [],
            },
        }
        surfaces = by_target.get(
            target,
            {
                "official_project_surfaces": [],
                "official_user_surfaces": [],
                "optional_project_surfaces": [],
                "optional_user_surfaces": [],
                "observed_compatibility_surfaces": [],
            },
        )
        surfaces.setdefault("optional_project_surfaces", [])
        surfaces.setdefault("optional_user_surfaces", [])
        return surfaces

    def setup(self, target: str, force: bool = False) -> list[Path]:
        if target not in self.TARGETS:
            raise ValueError(f"Unsupported target: {target}")

        written_files: list[Path] = []
        integration = self.TARGETS[target]
        for relative in integration.files:
            file_path = self.project_dir / relative
            markers = self._managed_agents_markers(target)
            if relative == "AGENTS.md" and markers is not None:
                block_content = self._append_flow_contract(
                    content=self._build_file_content(target=target, relative=relative),
                    relative=relative,
                )
                updated = self._upsert_managed_block(
                    file_path=file_path,
                    begin=markers[0],
                    end=markers[1],
                    block_content=block_content,
                )
                if updated:
                    written_files.append(file_path)
                continue
            if target == "claude-code" and relative in {"CLAUDE.md", ".claude/CLAUDE.md"}:
                block_content = self._append_flow_contract(
                    content=self._build_file_content(target=target, relative=relative),
                    relative=relative,
                )
                updated = self._upsert_managed_block(
                    file_path=file_path,
                    begin=self.CLAUDE_RULES_BEGIN,
                    end=self.CLAUDE_RULES_END,
                    block_content=block_content,
                )
                if updated:
                    written_files.append(file_path)
                continue
            if file_path.exists() and not force:
                continue
            file_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._append_flow_contract(
                content=self._build_file_content(target=target, relative=relative),
                relative=relative,
            )
            file_path.write_text(content, encoding="utf-8")
            written_files.append(file_path)

        # Auto-install enforcement hooks for supported hosts
        if target == "claude-code":
            try:
                from .._enforcement_bridge import auto_install_enforcement

                enforcement_files = auto_install_enforcement(self.project_dir)
                written_files.extend(enforcement_files)
            except Exception:
                pass  # Graceful degradation — enforcement is optional

        written_files.extend(self._setup_seeai_mode_surfaces(target=target, force=force))

        return written_files

    def _setup_seeai_mode_surfaces(self, *, target: str, force: bool) -> list[Path]:
        written: list[Path] = []
        seen: set[str] = set()

        def _append(path: Path | None) -> None:
            if path is None:
                return
            key = str(path.resolve())
            if key in seen:
                return
            seen.add(key)
            written.append(path)

        if self.supports_slash(target):
            seeai_slash = self.setup_seeai_slash_command(target=target, force=force)
            _append(seeai_slash)

        for relative in self.managed_competition_project_surfaces(target):
            file_path = self.project_dir / relative
            if file_path.exists() and not force:
                continue
            file_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._append_flow_contract(
                content=self._build_file_content(target=target, relative=relative),
                relative=relative,
            )
            file_path.write_text(content, encoding="utf-8")
            _append(file_path)

        return written

    @classmethod
    def managed_competition_project_surfaces(cls, target: str) -> list[str]:
        if target not in cls.TARGETS:
            return []

        candidates: list[str] = []
        if cls.supports_slash(target):
            seeai_slash_relative = cls.SLASH_COMMAND_FILES[target].replace(
                "super-dev",
                "super-dev-seeai",
            )
            if seeai_slash_relative not in candidates:
                candidates.append(seeai_slash_relative)
        project_files = tuple(cls.TARGETS[target].files) + tuple(cls.TARGETS[target].optional_files)
        for relative in project_files:
            normalized = relative.replace("\\", "/")
            if "super-dev-seeai" not in normalized:
                continue
            if relative not in candidates:
                candidates.append(relative)
        for relative in project_files:
            if "/skills/super-dev/SKILL.md" not in relative:
                continue
            candidate = relative.replace(
                "/skills/super-dev/SKILL.md",
                "/skills/super-dev-seeai/SKILL.md",
            )
            if candidate == relative or candidate in project_files or candidate in candidates:
                continue
            candidates.append(candidate)
        return candidates

    @classmethod
    def managed_competition_user_surfaces(cls, target: str) -> list[str]:
        if target not in cls.TARGETS:
            return []

        from ..skills import SkillManager

        supplemental = [
            name
            for name in SkillManager.supplemental_builtin_skills(target)
            if isinstance(name, str) and name.strip()
        ]
        if not supplemental:
            return []

        base = SkillManager.TARGET_PATHS.get(target)
        if not isinstance(base, str) or not base.strip():
            return []
        normalized_base = base.replace("\\", "/").rstrip("/")
        managed: list[str] = []
        for extra_name in supplemental:
            derived = f"{normalized_base}/{extra_name}/SKILL.md"
            if derived not in managed:
                managed.append(derived)
        return managed

    def managed_user_agent_surfaces(
        self,
        target: str,
        *,
        include_optional: bool = True,
    ) -> list[str]:
        if target not in self.TARGETS:
            return []

        declared = self._install_surfaces(target=target)
        surfaces: list[str] = []
        candidate_keys = ["official_user_surfaces"]
        if include_optional:
            candidate_keys.append("optional_user_surfaces")
        for key in candidate_keys:
            for item in declared.get(key, []):
                if not isinstance(item, str):
                    continue
                normalized = item.replace("\\", "/").strip()
                if not normalized.endswith("/agents/super-dev.md"):
                    continue
                if normalized not in surfaces:
                    surfaces.append(normalized)
        return surfaces

    def setup_global_agent_surfaces(self, target: str, force: bool = False) -> list[Path]:
        written: list[Path] = []
        for surface in self.managed_user_agent_surfaces(target):
            surface_path = self._resolve_surface_declaration(target=target, surface=surface)
            if surface_path.exists() and not force:
                continue
            surface_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._append_flow_contract(
                content=self._build_file_content(target=target, relative=surface),
                relative=surface_path.as_posix(),
            )
            surface_path.write_text(content, encoding="utf-8")
            written.append(surface_path)
        return written

    def setup_global_protocol(self, target: str, force: bool = False) -> Path | None:
        protocol_file = self.resolve_global_protocol_path(target)

        markers = self._managed_agents_markers(target)
        if protocol_file is not None and protocol_file.name == "AGENTS.md" and markers is not None:
            content = (
                self._build_codex_agents_content()
                if target in {"codex", "codex-cli"}
                else self._build_content(target)
            )
            block_content = self._append_flow_contract(
                content=content,
                relative=protocol_file.as_posix(),
            )
            updated = self._upsert_managed_block(
                file_path=protocol_file,
                begin=markers[0],
                end=markers[1],
                block_content=block_content,
            )
            return protocol_file if updated or protocol_file.exists() else None

        if target == "claude-code" and protocol_file is not None:
            block_content = self._append_flow_contract(
                content=self._build_file_content(target=target, relative=protocol_file.name),
                relative=protocol_file.as_posix(),
            )
            updated = self._upsert_managed_block(
                file_path=protocol_file,
                begin=self.CLAUDE_RULES_BEGIN,
                end=self.CLAUDE_RULES_END,
                block_content=block_content,
            )
            return protocol_file if updated or protocol_file.exists() else None

        if target in {"codebuddy", "codebuddy-cli", "codebuddy-cn"} and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_content(target),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target in {"kiro", "kiro-cli"} and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_kiro_global_steering_content(),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target in {"gemini-cli", "qwen-code"} and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_content(target),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target == "antigravity" and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_antigravity_context_content(),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target == "opencode" and protocol_file is not None:
            if protocol_file.exists() and not force:
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(
                self._append_flow_contract(
                    content=self._build_content(target),
                    relative=protocol_file.as_posix(),
                ),
                encoding="utf-8",
            )
            return protocol_file

        if target in {"trae", "trae-cn"} and protocol_file is not None:
            compatibility_file = self.resolve_compatibility_protocol_path(target)
            content = self._append_flow_contract(
                content=self._build_content(target),
                relative=protocol_file.as_posix(),
            )
            if protocol_file.exists() and not force:
                if compatibility_file is not None and not compatibility_file.exists():
                    compatibility_file.parent.mkdir(parents=True, exist_ok=True)
                    compatibility_file.write_text(
                        self._append_flow_contract(
                            content=content,
                            relative=compatibility_file.as_posix(),
                        ),
                        encoding="utf-8",
                    )
                return None
            protocol_file.parent.mkdir(parents=True, exist_ok=True)
            protocol_file.write_text(content, encoding="utf-8")
            if compatibility_file is not None:
                compatibility_file.parent.mkdir(parents=True, exist_ok=True)
                compatibility_file.write_text(
                    self._append_flow_contract(
                        content=content,
                        relative=compatibility_file.as_posix(),
                    ),
                    encoding="utf-8",
                )
            return protocol_file

        return None
