"""Pipeline execution command for the CLI."""

import importlib.util
import json
import subprocess as _subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from super_dev.artifact_utils import ui_contract_filename

from . import __version__
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
from .config import ConfigManager
from .evidence_identity import attach_evidence_identity
from .scope_advisory import resolve_pipeline_scope_declaration

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


class CliPipelineRuntimeMixin:
    def _cmd_pipeline(self, args) -> int:
        """运行完整流水线 - 从想法到部署"""
        self._print_governance_boundary_notice(
            "流水线负责生成研究、文档、门禁与交付产物；实际编码能力仍由宿主 AI 提供。"
        )
        request_mode_override = getattr(args, "mode", "feature")
        if request_mode_override not in {"feature", "bugfix"}:
            request_mode_override = "feature"
        # 确定项目名称
        project_name = args.name
        if not project_name:
            import re

            words = re.findall(r"[\w]+", args.description)
            if words:
                project_name = "-".join(words[:3]).lower()
            else:
                project_name = "my-project"
        project_name = self._sanitize_project_name(project_name)

        tech_stack = {
            "platform": args.platform,
            "frontend": args.frontend,
            "backend": args.backend,
            "domain": args.domain,
        }
        declared_changed_surfaces = getattr(args, "changed_surfaces", None)
        normalized_declared_surfaces = sorted(
            {
                str(item).strip().lower()
                for item in (
                    declared_changed_surfaces
                    if isinstance(declared_changed_surfaces, list | tuple | set | frozenset)
                    else ()
                )
                if str(item).strip()
            }
        )
        declared_governance_depth = str(getattr(args, "governance_depth", "") or "").strip()

        project_dir = Path.cwd()
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        pipeline_config = ConfigManager(project_dir).load()
        if not self._ensure_pipeline_host_ready(project_dir=project_dir, config=pipeline_config):
            return 1
        resume_requested = bool(getattr(args, "resume", False))
        from .policy import PipelinePolicyManager

        policy_manager = PipelinePolicyManager(project_dir)
        policy_violations = policy_manager.validate_pipeline_args(args=args, config=pipeline_config)
        if policy_violations:
            self.console.print("[red]流水线策略校验未通过:[/red]")
            for item in policy_violations:
                self.console.print(f"  - {item}")
            self.console.print(f"[dim]策略文件: {policy_manager.policy_path}[/dim]")
            self.console.print(
                "[dim]请检查 .super-dev/policy.yaml 或 super-dev.yaml 中的当前治理配置[/dim]"
            )
            return 1

        pipeline_args_snapshot: dict[str, Any] = {
            "description": args.description,
            "mode": request_mode_override,
            "platform": args.platform,
            "frontend": args.frontend,
            "backend": args.backend,
            "domain": args.domain,
            "name": args.name,
            "cicd": args.cicd,
            "skip_redteam": bool(args.skip_redteam),
            "skip_scaffold": bool(args.skip_scaffold),
            "skip_quality_gate": bool(args.skip_quality_gate),
            "skip_rehearsal_verify": bool(args.skip_rehearsal_verify),
            "offline": bool(args.offline),
            "quality_threshold": args.quality_threshold,
            "changed_surfaces": normalized_declared_surfaces or None,
            "governance_depth": declared_governance_depth or None,
        }
        pipeline_policy = policy_manager.load()

        self.console.print(f"[cyan]{'=' * 60}[/cyan]")
        self.console.print("[cyan]Super Dev 完整流水线[/cyan]")
        self.console.print(f"[cyan]{'=' * 60}[/cyan]")
        self.console.print(f"[dim]项目: {project_name}[/dim]")
        self.console.print(f"[dim]请求模式: {request_mode_override}[/dim]")
        self.console.print(f"[dim]技术栈: {args.platform} | {args.frontend} | {args.backend}[/dim]")
        self.console.print("")

        from .orchestrator.contracts import PipelineContractReport
        from .orchestrator.telemetry import PipelineTelemetryReport

        telemetry = PipelineTelemetryReport(project_name=project_name)
        contract_report = PipelineContractReport(project_name=project_name)
        pipeline_started_at = time.perf_counter()
        current_stage = ""
        current_stage_title = ""
        stage_started_at = pipeline_started_at
        resume_from_stage: int | None = None
        scenario = ""
        requirements: list[dict[str, Any]] = []
        phases: list[Any] = []
        change_id = ""
        enriched_description = args.description
        scaffold_result: dict[str, list[str]] = {"frontend_files": [], "backend_files": []}
        task_execution_summary = None
        run_state = self._read_pipeline_run_state(project_dir) if resume_requested else None
        metrics_payload = self._load_pipeline_metrics_payload(
            output_dir=output_dir, project_name=project_name
        )
        run_context = self._extract_resume_context(
            run_state=run_state, metrics_payload=metrics_payload
        )

        stored_scenario = run_context.get("scenario")
        if isinstance(stored_scenario, str) and stored_scenario in {"0-1", "1-N+1"}:
            scenario = stored_scenario
        stored_requirements = run_context.get("requirements")
        requirements = self._normalize_requirements_payload(stored_requirements)
        stored_change_id = run_context.get("change_id")
        if isinstance(stored_change_id, str) and stored_change_id.strip():
            change_id = stored_change_id.strip()
        else:
            detected_change = self._detect_latest_change_id(project_dir)
            if detected_change:
                change_id = detected_change
                run_context["change_id"] = detected_change
        stored_enriched_desc = run_context.get("enriched_description")
        if isinstance(stored_enriched_desc, str) and stored_enriched_desc.strip():
            enriched_description = stored_enriched_desc

        research_file = output_dir / f"{project_name}-research.md"
        prd_file = output_dir / f"{project_name}-prd.md"
        arch_file = output_dir / f"{project_name}-architecture.md"
        uiux_file = output_dir / f"{project_name}-uiux.md"
        plan_file = output_dir / f"{project_name}-execution-plan.md"
        frontend_blueprint_file = output_dir / f"{project_name}-frontend-blueprint.md"
        resume_audit_payload: dict[str, Any] | None = None
        resume_audit_files: dict[str, Path] | None = None
        stage_output_evidence: list[str] = []
        stage_execution_state: dict[str, dict[str, Any]] = {}

        def _start_stage(stage: str, title: str) -> None:
            nonlocal current_stage, current_stage_title, stage_started_at
            current_stage = stage
            current_stage_title = title
            stage_started_at = time.perf_counter()

        def _record_stage(success: bool, details: dict[str, Any] | None = None) -> None:
            nonlocal stage_output_evidence, stage_execution_state
            if not current_stage:
                return
            normalized_details = details or {}
            stage_outputs = self._extract_stage_artifacts(normalized_details)
            stage_notes = self._extract_stage_notes(normalized_details)
            stage_execution_state[current_stage] = {
                "success": success,
                "title": current_stage_title,
                "details": normalized_details,
            }
            telemetry.record_stage(
                stage=current_stage,
                title=current_stage_title,
                success=success,
                duration_seconds=time.perf_counter() - stage_started_at,
                details=normalized_details,
            )
            contract_report.record_stage(
                stage=current_stage,
                title=current_stage_title,
                success=success,
                duration_seconds=time.perf_counter() - stage_started_at,
                inputs=list(stage_output_evidence),
                outputs=stage_outputs,
                notes=stage_notes,
            )
            stage_output_evidence = stage_outputs or stage_output_evidence

        def _write_metrics_snapshot() -> Path:
            """写入当前指标快照，供后续发布演练校验读取。"""
            snapshot_file = output_dir / f"{project_name}-pipeline-metrics.json"
            snapshot_payload = telemetry.to_dict()
            snapshot_file.write_text(
                json.dumps(snapshot_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return snapshot_file

        def _finalize_metrics(success: bool, reason: str = "") -> dict[str, Path]:
            telemetry.finalize(
                success=success,
                total_duration_seconds=time.perf_counter() - pipeline_started_at,
                failure_reason=reason,
            )
            return telemetry.write(output_dir=output_dir)

        def _finalize_contract(success: bool, reason: str = "") -> dict[str, Path]:
            contract_report.finalize(success=success, failure_reason=reason)
            return contract_report.write(output_dir=output_dir)

        def _write_contract_snapshot() -> dict[str, Path]:
            """写入当前运行中的契约快照，供发布演练等进行中校验读取。"""
            return contract_report.write(output_dir=output_dir)

        def _persist_run_state(status: str, extra: dict[str, Any] | None = None) -> None:
            payload = {
                "status": status,
                "status_normalized": self._normalize_run_status(status),
                "project_name": project_name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "pipeline_args": pipeline_args_snapshot,
                "context": run_context,
            }
            if extra:
                payload.update(extra)
            self._write_pipeline_run_state(project_dir, payload)

        def _update_run_context(**values: Any) -> None:
            for key, value in values.items():
                if value is None:
                    continue
                run_context[key] = value

        _update_run_context(pipeline_policy=pipeline_policy.__dict__)

        def _should_skip_for_resume(stage_num: int) -> bool:
            return resume_from_stage is not None and stage_num < resume_from_stage

        def _flush_resume_audit(status: str, failure_reason: str = "") -> None:
            nonlocal resume_audit_payload, resume_audit_files
            if not resume_audit_payload:
                return
            resume_audit_payload["status"] = status
            resume_audit_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
            if failure_reason:
                resume_audit_payload["failure_reason"] = failure_reason
            resume_audit_files = self._write_resume_audit(
                output_dir=output_dir,
                project_name=project_name,
                payload=resume_audit_payload,
            )

        try:
            _persist_run_state("running")
            if resume_requested:
                run_status = (
                    str((run_state or {}).get("status", "")).strip().lower()
                    if isinstance(run_state, dict)
                    else ""
                )
                fallback_reasons: list[str] = []
                if run_status in {
                    "waiting_confirmation",
                    "waiting_preview_confirmation",
                    "waiting_ui_revision",
                    "waiting_architecture_revision",
                    "waiting_quality_revision",
                }:
                    failed_stage = None
                    resume_from_stage = None
                    if isinstance(run_state, dict):
                        resume_from_stage = self._coerce_stage_number(
                            run_state.get("resume_from_stage")
                        )
                        if resume_from_stage is None:
                            resume_from_stage = self._coerce_stage_number(
                                run_state.get("next_stage")
                            )
                    if resume_from_stage is None:
                        resume_from_stage = 2
                    initial_resume_stage = resume_from_stage
                    if run_status == "waiting_preview_confirmation":
                        self.console.print(
                            f"[cyan]恢复模式：前端预览确认已通过，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    elif run_status == "waiting_ui_revision":
                        self.console.print(
                            f"[cyan]恢复模式：UI 改版门已通过，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    elif run_status == "waiting_architecture_revision":
                        self.console.print(
                            f"[cyan]恢复模式：架构返工已通过，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    elif run_status == "waiting_quality_revision":
                        self.console.print(
                            f"[cyan]恢复模式：质量返工已通过，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    else:
                        self.console.print(
                            f"[cyan]恢复模式：文档确认已完成，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                else:
                    failed_stage = None
                    if isinstance(run_state, dict):
                        failed_stage = self._coerce_stage_number(run_state.get("failed_stage"))
                    if failed_stage is None:
                        failed_stage = self._detect_failed_stage_from_metrics_payload(
                            metrics_payload
                        )
                    if failed_stage is None:
                        failed_stage = self._detect_failed_stage(
                            output_dir=output_dir, project_name=project_name
                        )

                    resume_from_stage = self._resolve_resume_start_stage(
                        failed_stage=failed_stage,
                        skip_redteam=bool(args.skip_redteam),
                    )
                    initial_resume_stage = resume_from_stage
                    adjusted_resume_stage, fallback_reasons = (
                        self._adjust_resume_stage_for_artifacts(
                            project_dir=project_dir,
                            output_dir=output_dir,
                            project_name=project_name,
                            resume_from_stage=resume_from_stage,
                        )
                    )
                    if (
                        adjusted_resume_stage != resume_from_stage
                        and adjusted_resume_stage is not None
                    ):
                        for reason in fallback_reasons:
                            self.console.print(f"[yellow]恢复校验: {reason}[/yellow]")
                        self.console.print(
                            f"[yellow]恢复起点已自动下调到第 {adjusted_resume_stage} 阶段[/yellow]"
                        )
                    resume_from_stage = adjusted_resume_stage
                    if failed_stage is None:
                        self.console.print(
                            "[yellow]未检测到可恢复的失败记录，将执行完整流水线[/yellow]"
                        )
                    elif resume_from_stage is not None:
                        self.console.print(
                            f"[cyan]恢复模式：检测到上次失败阶段 {failed_stage}，将从第 {resume_from_stage} 阶段继续[/cyan]"
                        )
                    else:
                        self.console.print(
                            f"[yellow]上次失败发生在第 {failed_stage} 阶段，当前将执行完整流水线以确保一致性[/yellow]"
                        )
                _update_run_context(
                    resume_detected_failed_stage=failed_stage,
                    resume_from_stage=resume_from_stage,
                )
                _persist_run_state(
                    "running",
                    {
                        "failed_stage": str(failed_stage) if failed_stage is not None else "",
                        "resume_from_stage": (
                            str(resume_from_stage) if resume_from_stage is not None else ""
                        ),
                    },
                )
                resume_audit_payload = {
                    "project_name": project_name,
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "finished_at": "",
                    "run_state_status": (
                        str((run_state or {}).get("status", ""))
                        if isinstance(run_state, dict)
                        else ""
                    ),
                    "detected_failed_stage": failed_stage,
                    "initial_resume_stage": initial_resume_stage,
                    "final_resume_stage": resume_from_stage,
                    "planned_skipped_stages": (
                        list(range(resume_from_stage)) if resume_from_stage is not None else []
                    ),
                    "fallback_reasons": fallback_reasons,
                }
                resume_audit_files = self._write_resume_audit(
                    output_dir=output_dir,
                    project_name=project_name,
                    payload=resume_audit_payload,
                )
                self.console.print(f"[dim]恢复审计报告: {resume_audit_files['markdown']}[/dim]")

            knowledge_dir = project_dir / "knowledge"
            knowledge_cache_file = (
                output_dir / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"
            )
            knowledge_file_count = 0
            if knowledge_dir.exists():
                knowledge_file_count = sum(
                    1
                    for path in knowledge_dir.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".md", ".txt", ".yaml", ".yml"}
                )
            self.console.print(
                f"[dim]知识库扫描: knowledge 文件 {knowledge_file_count} 条 | "
                f"缓存 {'存在' if knowledge_cache_file.exists() else '不存在'}[/dim]"
            )
            _update_run_context(
                knowledge_file_count=knowledge_file_count,
                knowledge_cache_exists=knowledge_cache_file.exists(),
            )

            # 初始化 resume 跳过时可能未赋值的变量
            knowledge_bundle: dict | None = None
            cicd_files: dict[str, str] = {}
            remediation_outputs: dict = {"env_file": "", "checklist_file": "", "items_count": 0}
            migration_files: dict[str, str] = {}
            delivery_outputs: dict = {
                "manifest_file": "",
                "report_file": "",
                "archive_file": "",
                "status": "skipped",
            }
            task_execution_summary = None

            # ========== 第 0 阶段: 需求增强 ==========
            _start_stage("0", "需求增强")
            if _should_skip_for_resume(0):
                self.console.print("[yellow]第 0 阶段: 需求增强 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
                _update_run_context(enriched_description=enriched_description)
            else:
                self.console.print("[cyan]第 0 阶段: 需求增强 (联网 + 知识库)...[/cyan]")
                import os

                from .orchestrator.knowledge import KnowledgeAugmenter

                disable_web = args.offline or (
                    os.getenv("SUPER_DEV_DISABLE_WEB", "").strip().lower() in {"1", "true", "yes"}
                )
                augmenter = KnowledgeAugmenter(
                    project_dir=project_dir,
                    web_enabled=not disable_web,
                    allowed_web_domains=pipeline_config.knowledge_allowed_domains,
                    cache_ttl_seconds=pipeline_config.knowledge_cache_ttl_seconds,
                )
                knowledge_bundle = augmenter.load_cached_bundle(
                    output_dir=output_dir,
                    project_name=project_name,
                    requirement=args.description,
                    domain=args.domain or "",
                )
                cache_hit = knowledge_bundle is not None
                if knowledge_bundle is None:
                    knowledge_bundle = augmenter.augment(
                        requirement=args.description,
                        domain=args.domain or "",
                    )
                research_file = output_dir / f"{project_name}-research.md"
                research_file.write_text(augmenter.to_markdown(knowledge_bundle), encoding="utf-8")
                if cache_hit:
                    knowledge_cache_file = (
                        output_dir / "knowledge-cache" / f"{project_name}-knowledge-bundle.json"
                    )
                else:
                    knowledge_cache_file = augmenter.save_bundle(
                        bundle=knowledge_bundle,
                        output_dir=output_dir,
                        project_name=project_name,
                        requirement=args.description,
                        domain=args.domain or "",
                    )

                enriched_description = knowledge_bundle.get(
                    "enriched_requirement", args.description
                )
                self.console.print(f"  [green]✓[/green] 需求增强报告: {research_file}")
                self.console.print(f"  [green]✓[/green] 知识缓存: {knowledge_cache_file}")
                self.console.print(f"  [dim]缓存命中: {'yes' if cache_hit else 'no'}[/dim]")
                self.console.print(
                    f"  [dim]本地知识 {len(knowledge_bundle.get('local_knowledge', []))} 条 | "
                    f"联网结果 {len(knowledge_bundle.get('web_knowledge', []))} 条[/dim]"
                )
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "local_knowledge_count": len(knowledge_bundle.get("local_knowledge", [])),
                        "web_knowledge_count": len(knowledge_bundle.get("web_knowledge", [])),
                        "cache_file": str(knowledge_cache_file),
                        "cache_hit": cache_hit,
                        "knowledge_cache_ttl_seconds": pipeline_config.knowledge_cache_ttl_seconds,
                        "knowledge_allowed_domains": pipeline_config.knowledge_allowed_domains,
                        "web_filtered_out_count": (
                            (knowledge_bundle.get("metadata") or {})
                            .get("web_stats", {})
                            .get("filtered_out_count", 0)
                        ),
                    },
                )
                _update_run_context(enriched_description=enriched_description)

            # ========== 第 1 阶段: 生成文档 ==========
            _start_stage("1", "专业文档生成")
            if _should_skip_for_resume(1):
                self.console.print("[yellow]第 1 阶段: 生成专业文档 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 1 阶段: 生成专业文档...[/cyan]")
                from .creators import (
                    DocumentGenerator,
                    RequirementParser,
                )

                parser = RequirementParser()
                scenario = parser.detect_scenario(project_dir)
                request_mode = request_mode_override or parser.detect_request_mode(
                    enriched_description
                )

                doc_generator = DocumentGenerator(
                    name=project_name,
                    description=enriched_description,
                    request_mode=request_mode,
                    platform=args.platform,
                    frontend=args.frontend,
                    backend=args.backend,
                    domain=args.domain,
                    design_inspiration_slug=str(
                        getattr(pipeline_config, "design_inspiration_slug", "") or ""
                    ),
                    language_preferences=pipeline_config.language_preferences,
                    knowledge_summary=(
                        knowledge_bundle.get("research_summary", {})
                        if isinstance(knowledge_bundle, dict)
                        else {}
                    ),
                )

                # 生成文档内容
                prd_content = doc_generator.generate_prd()
                arch_content = doc_generator.generate_architecture()
                uiux_content = doc_generator.generate_uiux()

                # 写入文件
                prd_file = output_dir / f"{project_name}-prd.md"
                arch_file = output_dir / f"{project_name}-architecture.md"
                uiux_file = output_dir / f"{project_name}-uiux.md"

                prd_file.write_text(prd_content, encoding="utf-8")
                arch_file.write_text(arch_content, encoding="utf-8")
                uiux_file.write_text(uiux_content, encoding="utf-8")
                (output_dir / ui_contract_filename(project_name)).write_text(
                    json.dumps(doc_generator.generate_ui_contract(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                plan_file = output_dir / f"{project_name}-execution-plan.md"
                frontend_blueprint_file = output_dir / f"{project_name}-frontend-blueprint.md"
                plan_file.write_text(
                    doc_generator.generate_execution_plan(
                        scenario=scenario,
                        request_mode=request_mode,
                    ),
                    encoding="utf-8",
                )
                frontend_blueprint_file.write_text(
                    doc_generator.generate_frontend_blueprint(), encoding="utf-8"
                )

                self.console.print(f"  [green]✓[/green] PRD: {prd_file}")
                self.console.print(f"  [green]✓[/green] 架构: {arch_file}")
                self.console.print(f"  [green]✓[/green] UI/UX: {uiux_file}")
                self.console.print(f"  [green]✓[/green] 执行路线图: {plan_file}")
                self.console.print(f"  [green]✓[/green] 前端蓝图: {frontend_blueprint_file}")
                self.console.print(f"  [dim]场景识别: {scenario}[/dim]")
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "scenario": scenario,
                        "docs": [
                            str(prd_file),
                            str(arch_file),
                            str(uiux_file),
                            str(plan_file),
                            str(frontend_blueprint_file),
                        ],
                    },
                )

                # 保存技术栈到配置文件（供后续阶段使用）
                self._save_tech_stack_to_config(project_dir, tech_stack, args.description)

                requirements = self._normalize_requirements_payload(
                    doc_generator.extract_requirements()
                )
                phases = parser.build_execution_phases(
                    scenario, requirements, request_mode=request_mode
                )
                _update_run_context(
                    scenario=scenario,
                    request_mode=request_mode,
                    requirements=requirements,
                )

            docs_confirmation = self._get_docs_confirmation_state(project_dir)
            _update_run_context(docs_confirmation=docs_confirmation)
            if not self._docs_confirmation_is_confirmed(project_dir):
                waiting_reason = (
                    "revision_requested"
                    if docs_confirmation["status"] == "revision_requested"
                    else "pending_review"
                )
                self.console.print("[yellow]已完成 research 与三文档，当前进入文档确认门[/yellow]")
                self.console.print(f"  [dim]研究报告: {research_file}[/dim]")
                self.console.print(f"  [dim]PRD: {prd_file}[/dim]")
                self.console.print(f"  [dim]架构: {arch_file}[/dim]")
                self.console.print(f"  [dim]UI/UX: {uiux_file}[/dim]")
                if docs_confirmation["status"] == "revision_requested":
                    self.console.print(
                        "[yellow]当前状态: 用户已要求修改文档，请先修正文档并再次确认。[/yellow]"
                    )
                else:
                    self.console.print(
                        "[yellow]当前状态: 待用户确认三文档，确认前不会创建 Spec 或开始编码。[/yellow]"
                    )
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print(
                    "  1. 在宿主中查看并修订 output/*-prd.md / *-architecture.md / *-uiux.md"
                )
                self.console.print("  2. 在宿主中明确回复：“文档确认，可以继续”")
                self.console.print("  3. 继续留在当前 Super Dev 流程内，不要切回普通聊天")
                metric_files = _finalize_metrics(success=False, reason="waiting_confirmation")
                contract_files = _finalize_contract(success=False, reason="waiting_confirmation")
                _persist_run_state(
                    "waiting_confirmation",
                    {
                        "failure_reason": waiting_reason,
                        "failed_stage": "2",
                        "next_stage": "2",
                        "resume_from_stage": "2",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(status="waiting_confirmation", failure_reason=waiting_reason)
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            ui_revision = self._get_ui_revision_state(project_dir)
            _update_run_context(ui_revision=ui_revision)
            if ui_revision["status"] == "revision_requested":
                self.console.print(
                    "[yellow]当前存在 UI 改版请求，必须先完成 UI 返工后才能继续[/yellow]"
                )
                if ui_revision["comment"]:
                    self.console.print(f"  [dim]备注: {ui_revision['comment']}[/dim]")
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print("  1. 先更新 output/*-uiux.md")
                self.console.print(
                    "  2. 重做前端，并重新执行前端运行验证（frontend runtime）"
                    "和界面审查（UI review）"
                )
                self.console.print("  3. 在宿主中明确回复：“UI 改版已完成，继续当前流程”")
                self.console.print("  4. 继续留在当前 Super Dev 流程内，不要重新开题")
                metric_files = _finalize_metrics(success=False, reason="waiting_ui_revision")
                contract_files = _finalize_contract(success=False, reason="waiting_ui_revision")
                _persist_run_state(
                    "waiting_ui_revision",
                    {
                        "failure_reason": "revision_requested",
                        "failed_stage": "2",
                        "next_stage": "2",
                        "resume_from_stage": "2",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(
                    status="waiting_ui_revision", failure_reason="revision_requested"
                )
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            architecture_revision = self._get_architecture_revision_state(project_dir)
            _update_run_context(architecture_revision=architecture_revision)
            if architecture_revision["status"] == "revision_requested":
                self.console.print(
                    "[yellow]当前存在架构返工请求，必须先完成架构方案修订后才能继续[/yellow]"
                )
                if architecture_revision["comment"]:
                    self.console.print(f"  [dim]备注: {architecture_revision['comment']}[/dim]")
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print("  1. 先更新 output/*-architecture.md")
                self.console.print("  2. 同步调整任务拆解与相关实现方案")
                self.console.print("  3. 在宿主中明确回复：“架构调整已完成，继续当前流程”")
                self.console.print("  4. 继续留在当前 Super Dev 流程内，不要重新开题")
                metric_files = _finalize_metrics(
                    success=False, reason="waiting_architecture_revision"
                )
                contract_files = _finalize_contract(
                    success=False, reason="waiting_architecture_revision"
                )
                _persist_run_state(
                    "waiting_architecture_revision",
                    {
                        "failure_reason": "revision_requested",
                        "failed_stage": "2",
                        "next_stage": "2",
                        "resume_from_stage": "2",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(
                    status="waiting_architecture_revision", failure_reason="revision_requested"
                )
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            quality_revision = self._get_quality_revision_state(project_dir)
            _update_run_context(quality_revision=quality_revision)
            if quality_revision["status"] == "revision_requested":
                self.console.print(
                    "[yellow]当前存在质量返工请求，必须先修复质量/安全问题后才能继续[/yellow]"
                )
                if quality_revision["comment"]:
                    self.console.print(f"  [dim]备注: {quality_revision['comment']}[/dim]")
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print("  1. 先修复质量门禁或安全问题")
                self.console.print(
                    "  2. 重新执行 quality gate，并刷新 proof-pack / readiness 等交付证据"
                )
                self.console.print("  3. 在宿主中明确回复：“质量整改已完成，继续当前流程”")
                self.console.print("  4. 继续留在当前 Super Dev 流程内，不要重新开题")
                metric_files = _finalize_metrics(success=False, reason="waiting_quality_revision")
                contract_files = _finalize_contract(
                    success=False, reason="waiting_quality_revision"
                )
                _persist_run_state(
                    "waiting_quality_revision",
                    {
                        "failure_reason": "revision_requested",
                        "failed_stage": "2",
                        "next_stage": "2",
                        "resume_from_stage": "2",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(
                    status="waiting_quality_revision", failure_reason="revision_requested"
                )
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            # ========== 第 2 阶段: 创建 Spec ==========
            _start_stage("2", "Spec 创建")
            if _should_skip_for_resume(2):
                self.console.print("[yellow]第 2 阶段: 创建 Spec 规范 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 2 阶段: 创建 Spec 规范...[/cyan]")
                from .creators import SpecBuilder

                spec_builder = SpecBuilder(
                    project_dir=project_dir, name=project_name, description=args.description
                )

                scope_input = normalized_declared_surfaces
                if not scope_input and run_context.get("scope_complete") is True:
                    stored_surfaces = run_context.get("changed_surfaces")
                    if isinstance(stored_surfaces, list):
                        scope_input = stored_surfaces
                stored_depth = str(run_context.get("scope_governance_depth", "") or "").strip()
                scope_declaration = resolve_pipeline_scope_declaration(
                    changed_surfaces=scope_input,
                    request_mode=request_mode_override,
                    scenario=scenario,
                    governance_depth=declared_governance_depth or stored_depth or None,
                )
                pipeline_args_snapshot["changed_surfaces"] = (
                    list(scope_declaration.changed_surfaces)
                    if scope_declaration.scope_complete
                    else None
                )
                pipeline_args_snapshot["governance_depth"] = scope_declaration.governance_depth
                _update_run_context(
                    changed_surfaces=list(scope_declaration.changed_surfaces),
                    scope_complete=scope_declaration.scope_complete,
                    scope_work_mode=scope_declaration.work_mode,
                    scope_governance_depth=scope_declaration.governance_depth,
                )
                change_id = spec_builder.create_change(
                    requirements,
                    tech_stack,
                    scenario=scenario,
                    changed_surfaces=(
                        set(scope_declaration.changed_surfaces)
                        if scope_declaration.scope_complete
                        else None
                    ),
                    work_mode=scope_declaration.work_mode,
                    governance_depth=scope_declaration.governance_depth,
                )

                self.console.print(f"  [green]✓[/green] 变更 ID: {change_id}")
                self.console.print(f"  [green]✓[/green] Spec: .super-dev/changes/{change_id}/")
                shadow_result = spec_builder.last_shadow_ledger_result or {}
                if shadow_result.get("status") == "created":
                    self.console.print(
                        "  [green]✓[/green] 九阶段影子账本已建立（只读，不控制门禁）"
                    )
                    if shadow_result.get("scope_advisory_created") is True:
                        self.console.print(
                            "  [green]✓[/green] 阶段范围建议已生成（只读，缩减必须审批）"
                        )
                elif shadow_result.get("status") in {
                    "invalid_existing",
                    "write_failed",
                    "unsafe_path",
                    "missing_change",
                }:
                    self.console.print(
                        "  [yellow]⚠[/yellow] 影子账本未建立；主流程继续，"
                        f"原因: {shadow_result.get('error', '-')}"
                    )
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "change_id": change_id,
                        "shadow_ledger": shadow_result,
                    },
                )
                _update_run_context(change_id=change_id, shadow_ledger=shadow_result)

            # ========== 第 3 阶段: 生成前端实施蓝图 ==========
            _start_stage("3", "前端实施蓝图与预览")
            if _should_skip_for_resume(3):
                self.console.print(
                    "[yellow]第 3 阶段: 生成前端实施蓝图与预览 (resume 跳过)[/yellow]"
                )
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 3 阶段: 生成前端实施蓝图与预览...[/cyan]")
                from .creators import FrontendScaffoldBuilder

                frontend_builder = FrontendScaffoldBuilder(
                    project_dir=project_dir,
                    name=project_name,
                    description=args.description,
                    frontend=args.frontend,
                )
                frontend_files = frontend_builder.generate(
                    requirements=requirements,
                    phases=phases,
                    docs={
                        "prd": str(prd_file),
                        "architecture": str(arch_file),
                        "uiux": str(uiux_file),
                        "plan": str(plan_file),
                        "frontend_blueprint": str(frontend_blueprint_file),
                    },
                )
                self.console.print(f"  [green]✓[/green] 页面: {frontend_files['html']}")
                self.console.print(f"  [green]✓[/green] 样式: {frontend_files['css']}")
                self.console.print(f"  [green]✓[/green] 脚本: {frontend_files['js']}")
                frontend_runtime = self._write_frontend_runtime_validation(
                    project_dir=project_dir,
                    output_dir=output_dir,
                    project_name=project_name,
                )
                self.console.print(
                    f"  [green]✓[/green] 前端运行验证: {frontend_runtime['report_files']['markdown']}"
                )
                if frontend_runtime["preview_file"]:
                    self.console.print(
                        f"  [green]✓[/green] 预览页: {frontend_runtime['preview_file']}"
                    )
                if not frontend_runtime["passed"]:
                    raise RuntimeError("前端运行验证未通过，当前不得进入后端与交付阶段")
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "files": frontend_files,
                        "frontend_runtime_report": frontend_runtime["report_files"]["json"],
                        "preview_file": frontend_runtime["preview_file"],
                    },
                )

            preview_confirmation = self._get_preview_confirmation_state(project_dir)
            _update_run_context(preview_confirmation=preview_confirmation)
            if not self._preview_confirmation_is_confirmed(project_dir):
                waiting_reason = (
                    "revision_requested"
                    if preview_confirmation["status"] == "revision_requested"
                    else "pending_review"
                )
                self.console.print(
                    "[yellow]已完成前端实施蓝图与预览，当前进入前端预览确认门[/yellow]"
                )
                self.console.print(
                    f"  [dim]前端运行验证: {output_dir / f'{project_name}-frontend-runtime.md'}[/dim]"
                )
                preview_file = output_dir.parent / "preview.html"
                if preview_file.exists():
                    self.console.print(f"  [dim]预览页: {preview_file}[/dim]")
                if preview_confirmation["status"] == "revision_requested":
                    self.console.print(
                        "[yellow]当前状态: 用户已要求继续调整前端，请先完成预览返工并再次确认。[/yellow]"
                    )
                else:
                    self.console.print(
                        "[yellow]当前状态: 待用户确认前端预览，确认前不会进入后端、联调、质量与交付阶段。[/yellow]"
                    )
                self.console.print("[cyan]继续方式:[/cyan]")
                self.console.print("  1. 在宿主中查看并修订当前前端预览")
                self.console.print("  2. 在宿主中明确回复：“前端预览确认，可以继续”")
                self.console.print("  3. 继续留在当前 Super Dev 流程内，不要切回普通聊天")
                metric_files = _finalize_metrics(
                    success=False, reason="waiting_preview_confirmation"
                )
                contract_files = _finalize_contract(
                    success=False, reason="waiting_preview_confirmation"
                )
                _persist_run_state(
                    "waiting_preview_confirmation",
                    {
                        "failure_reason": waiting_reason,
                        "failed_stage": "4",
                        "next_stage": "4",
                        "resume_from_stage": "4",
                        "metrics_file": str(metric_files["json"]),
                        "contract_file": str(contract_files["json"]),
                    },
                )
                _flush_resume_audit(
                    status="waiting_preview_confirmation", failure_reason=waiting_reason
                )
                self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                if resume_audit_files:
                    self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                return 0

            # ========== 第 4 阶段: 生成宿主实现参考 ==========
            _start_stage("4", "宿主实现参考与任务执行")
            if _should_skip_for_resume(4):
                self.console.print("[yellow]第 4 阶段: 生成宿主实现参考 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                if not args.skip_scaffold:
                    self.console.print("[cyan]第 4 阶段: 生成宿主实现参考...[/cyan]")
                    from .creators import ImplementationScaffoldBuilder, SpecTaskExecutor

                    frontend_runtime = self._load_frontend_runtime_validation(
                        output_dir=output_dir,
                        project_name=project_name,
                    )
                    if not frontend_runtime.get("passed", False):
                        raise RuntimeError("前端运行验证未通过，禁止进入宿主实现参考与后端阶段")

                    implementation_builder = ImplementationScaffoldBuilder(
                        project_dir=project_dir,
                        name=project_name,
                        frontend=args.frontend,
                        backend=args.backend,
                    )
                    scaffold_result = implementation_builder.generate(requirements=requirements)
                    self.console.print(
                        f"  [green]✓[/green] 前端参考文件: {len(scaffold_result['frontend_files'])} 个"
                    )
                    self.console.print(
                        f"  [green]✓[/green] 后端参考文件: {len(scaffold_result['backend_files'])} 个"
                    )
                    task_executor = SpecTaskExecutor(
                        project_dir=project_dir, project_name=project_name
                    )
                    task_execution_summary = task_executor.execute(
                        change_id=change_id,
                        tech_stack=tech_stack,
                        max_retries=1,
                    )
                    self.console.print(
                        f"  [green]✓[/green] Spec 任务执行: {task_execution_summary.completed_tasks}/{task_execution_summary.total_tasks}"
                    )
                    self.console.print(
                        f"  [green]✓[/green] 任务报告: {task_execution_summary.report_file}"
                    )
                    if task_execution_summary.failed_tasks:
                        self.console.print(
                            f"  [yellow]未完成任务: {', '.join(task_execution_summary.failed_tasks)}[/yellow]"
                        )
                    if task_execution_summary.repaired_actions:
                        self.console.print(
                            f"  [dim]自动修复: {len(task_execution_summary.repaired_actions)} 项[/dim]"
                        )
                    self.console.print("")
                    _record_stage(
                        True,
                        details={
                            "frontend_files": len(scaffold_result["frontend_files"]),
                            "backend_files": len(scaffold_result["backend_files"]),
                            "frontend_runtime_report": str(
                                self._frontend_runtime_report_paths(
                                    output_dir=output_dir, project_name=project_name
                                )["json"]
                            ),
                            "task_completed": (
                                f"{task_execution_summary.completed_tasks}/{task_execution_summary.total_tasks}"
                                if task_execution_summary is not None
                                else "0/0"
                            ),
                            "task_failed_count": (
                                len(task_execution_summary.failed_tasks)
                                if task_execution_summary is not None
                                else 0
                            ),
                        },
                    )
                else:
                    self.console.print("[yellow]第 4 阶段: 生成宿主实现参考 (跳过)[/yellow]")
                    self.console.print("")
                    _record_stage(True, details={"skipped": True})

            # ========== 第 5 阶段: 红队审查 ==========
            _start_stage("5", "红队审查")
            redteam_report = None
            if _should_skip_for_resume(5):
                self.console.print("[yellow]第 5 阶段: 红队审查 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            elif not args.skip_redteam:
                self.console.print("[cyan]第 5 阶段: 红队审查...[/cyan]")
                from .reviewers import RedTeamReviewer

                reviewer = RedTeamReviewer(
                    project_dir=project_dir, name=project_name, tech_stack=tech_stack
                )
                redteam_report = reviewer.review()

                # 保存红队审查报告
                redteam_file = project_dir / "output" / f"{project_name}-redteam.md"
                redteam_json_file = project_dir / "output" / f"{project_name}-redteam.json"
                redteam_file.parent.mkdir(parents=True, exist_ok=True)
                redteam_file.write_text(redteam_report.to_markdown(), encoding="utf-8")
                redteam_json_file.write_text(
                    json.dumps(redteam_report.to_dict(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                self.console.print(
                    f"  [green]✓[/green] 安全问题: {sum(1 for i in redteam_report.security_issues if i.severity in ('critical', 'high'))} high/critical"
                )
                self.console.print(
                    f"  [green]✓[/green] 性能问题: {sum(1 for i in redteam_report.performance_issues if i.severity in ('critical', 'high'))} high/critical"
                )
                self.console.print(
                    f"  [green]✓[/green] 架构问题: {sum(1 for i in redteam_report.architecture_issues if i.severity in ('critical', 'high'))} high/critical"
                )
                self.console.print(f"  [green]✓[/green] 总分: {redteam_report.total_score}/100")
                self.console.print(f"  [green]✓[/green] 报告: {redteam_file}")
                self.console.print(f"  [green]✓[/green] JSON: {redteam_json_file}")
                self.console.print("")

                # 红队未通过时直接阻断，确保“先通过红队，再进入质量门禁”
                if not redteam_report.passed:
                    _record_stage(
                        False,
                        details={
                            "score": redteam_report.total_score,
                            "blocking_reasons": redteam_report.blocking_reasons,
                        },
                    )
                    metric_files = _finalize_metrics(
                        success=False,
                        reason="redteam_failed",
                    )
                    contract_files = _finalize_contract(success=False, reason="redteam_failed")
                    _persist_run_state(
                        "failed",
                        {
                            "failure_reason": "redteam_failed",
                            "failed_stage": "5",
                            "metrics_file": str(metric_files["json"]),
                            "contract_file": str(contract_files["json"]),
                        },
                    )
                    _flush_resume_audit(status="failed", failure_reason="redteam_failed")
                    self.console.print("[red]红队审查未通过，流水线终止[/red]")
                    for reason in redteam_report.blocking_reasons:
                        self.console.print(f"  - {reason}")
                    self.console.print(
                        "[dim]可使用 --skip-redteam 跳过该阶段（不推荐生产使用）[/dim]"
                    )
                    self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                    self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                    if resume_audit_files:
                        self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                    return 1
                _record_stage(
                    True,
                    details={
                        "score": redteam_report.total_score,
                        "critical_count": redteam_report.critical_count,
                        "high_count": redteam_report.high_count,
                    },
                )
            else:
                self.console.print("[yellow]第 5 阶段: 红队审查 (跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True})

            # ========== 第 6 阶段: 质量门禁 ==========
            _start_stage("6", "质量门禁")
            if _should_skip_for_resume(6):
                self.console.print("[yellow]第 6 阶段: 质量门禁检查 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            elif not args.skip_quality_gate:
                self.console.print("[cyan]第 6 阶段: 质量门禁检查...[/cyan]")
                from .reviewers import QualityGateChecker

                gate_checker = QualityGateChecker(
                    project_dir=project_dir,
                    name=project_name,
                    tech_stack=tech_stack,
                    scenario_override=scenario,
                    threshold_override=(
                        args.quality_threshold
                        if args.quality_threshold is not None
                        else pipeline_config.quality_gate
                    ),
                    host_compatibility_min_score_override=pipeline_config.host_compatibility_min_score,
                    host_compatibility_min_ready_hosts_override=pipeline_config.host_compatibility_min_ready_hosts,
                )

                gate_result = gate_checker.check(redteam_report)

                # 显示场景信息
                scenario_label = (
                    "0-1 新建项目" if gate_result.scenario == "0-1" else "1-N+1 增量开发"
                )
                self.console.print(f"  [dim]场景: {scenario_label}[/dim]")

                # 保存质量门禁报告
                gate_file = project_dir / "output" / f"{project_name}-quality-gate.md"
                gate_file.parent.mkdir(parents=True, exist_ok=True)
                if gate_checker.latest_ui_review_report is not None:
                    ui_review_file = project_dir / "output" / f"{project_name}-ui-review.md"
                    ui_review_json_file = project_dir / "output" / f"{project_name}-ui-review.json"
                    alignment_file = (
                        project_dir / "output" / f"{project_name}-ui-contract-alignment.md"
                    )
                    alignment_json_file = (
                        project_dir / "output" / f"{project_name}-ui-contract-alignment.json"
                    )
                    ui_review_file.write_text(
                        gate_checker.latest_ui_review_report.to_markdown(),
                        encoding="utf-8",
                    )
                    ui_review_json_file.write_text(
                        json.dumps(
                            attach_evidence_identity(
                                gate_checker.latest_ui_review_report.to_dict(),
                                project_dir=project_dir,
                                artifact_name="ui-review",
                                dependencies=[
                                    project_dir / "output" / ui_contract_filename(project_name),
                                    project_dir / "output" / f"{project_name}-uiux.md",
                                ],
                            ),
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    alignment_file.write_text(
                        gate_checker.latest_ui_review_report.alignment_markdown(),
                        encoding="utf-8",
                    )
                    alignment_json_file.write_text(
                        json.dumps(
                            attach_evidence_identity(
                                gate_checker.latest_ui_review_report.alignment_summary,
                                project_dir=project_dir,
                                artifact_name="ui-contract-alignment",
                                dependencies=[
                                    project_dir / "output" / ui_contract_filename(project_name),
                                    project_dir / "output" / f"{project_name}-uiux.md",
                                ],
                            ),
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    frontend_index = output_dir / "frontend" / "index.html"
                    if frontend_index.exists():
                        frontend_runtime = self._write_frontend_runtime_validation(
                            project_dir=project_dir,
                            output_dir=output_dir,
                            project_name=project_name,
                        )
                gate_result = gate_checker.check(redteam_report)
                gate_file.write_text(gate_result.to_markdown(), encoding="utf-8")
                gate_json_file = project_dir / "output" / f"{project_name}-quality-gate.json"
                gate_json_file.write_text(
                    json.dumps(
                        attach_evidence_identity(
                            gate_result.to_dict(),
                            project_dir=project_dir,
                            artifact_name="quality-gate",
                            dependencies=[
                                project_dir / "output" / f"{project_name}-ui-review.json",
                                project_dir
                                / "output"
                                / f"{project_name}-ui-contract-alignment.json",
                                project_dir / "output" / f"{project_name}-uiux.md",
                            ],
                        ),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                status = "[green]通过[/green]" if gate_result.passed else "[red]未通过[/red]"
                self.console.print(
                    f"  {status} 门禁分（加权）: {gate_result.gate_score:.1f}/100 "
                    f"(阈值 {gate_result.threshold:g}/100)"
                )
                self.console.print(f"  [dim]{gate_result.executive_summary}[/dim]")
                self.console.print(f"  [green]✓[/green] 报告: {gate_file}")
                if gate_checker.latest_ui_review_report is not None:
                    self.console.print(f"  [green]✓[/green] UI 审查: {ui_review_file}")
                    self.console.print(f"  [green]✓[/green] UI 审查 JSON: {ui_review_json_file}")
                    self.console.print(f"  [green]✓[/green] UI 契约对齐: {alignment_file}")
                self.console.print("")

                # 质量门禁未通过，停止流水线
                if not gate_result.passed:
                    _record_stage(
                        False,
                        details={
                            "score": gate_result.gate_score,
                            "unweighted_score": gate_result.total_score,
                            "critical_failures": gate_result.critical_failures,
                        },
                    )
                    metric_files = _finalize_metrics(
                        success=False,
                        reason="quality_gate_failed",
                    )
                    contract_files = _finalize_contract(success=False, reason="quality_gate_failed")
                    _persist_run_state(
                        "failed",
                        {
                            "failure_reason": "quality_gate_failed",
                            "failed_stage": "6",
                            "metrics_file": str(metric_files["json"]),
                            "contract_file": str(contract_files["json"]),
                        },
                    )
                    _flush_resume_audit(status="failed", failure_reason="quality_gate_failed")
                    self.console.print("[red]质量门禁未通过，流水线终止[/red]")
                    self.console.print("[cyan]请修复以下问题后重新运行:[/cyan]")
                    for failure in gate_result.critical_failures:
                        self.console.print(f"  - {failure}")
                    self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                    self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                    if resume_audit_files:
                        self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                    return 1
                _record_stage(
                    True,
                    details={
                        "score": gate_result.gate_score,
                        "unweighted_score": gate_result.total_score,
                        "scenario": gate_result.scenario,
                    },
                )
            else:
                self.console.print("[yellow]第 6 阶段: 质量门禁检查 (跳过)[/yellow]")
                self.console.print(
                    "[dim]提示: 使用 --skip-quality-gate 跳过了质量门禁检查，建议后续补充测试和质量检查[/dim]"
                )
                self.console.print("")
                _record_stage(True, details={"skipped": True})

            # ========== 第 7 阶段: 代码审查指南 ==========
            _start_stage("7", "代码审查指南")
            if _should_skip_for_resume(7):
                self.console.print("[yellow]第 7 阶段: 代码审查指南 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 7 阶段: 生成代码审查指南...[/cyan]")
                from .reviewers import CodeReviewGenerator

                review_gen = CodeReviewGenerator(
                    project_dir=project_dir, name=project_name, tech_stack=tech_stack
                )

                review_guide = review_gen.generate()
                review_file = project_dir / "output" / f"{project_name}-code-review.md"
                review_file.write_text(review_guide, encoding="utf-8")

                self.console.print(f"  [green]✓[/green] 代码审查指南: {review_file}")
                self.console.print("")
                _record_stage(True, details={"report": str(review_file)})

            # ========== 第 8 阶段: AI 提示词 ==========
            _start_stage("8", "AI 提示词")
            if _should_skip_for_resume(8):
                self.console.print("[yellow]第 8 阶段: AI 提示词 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 8 阶段: 生成 AI 提示词...[/cyan]")
                from .creators import AIPromptGenerator

                prompt_gen = AIPromptGenerator(project_dir=project_dir, name=project_name)

                prompt_content = prompt_gen.generate()
                prompt_file = project_dir / "output" / f"{project_name}-ai-prompt.md"
                prompt_file.write_text(prompt_content, encoding="utf-8")

                self.console.print(f"  [green]✓[/green] AI 提示词: {prompt_file}")
                self.console.print("")
                _record_stage(True, details={"prompt_file": str(prompt_file)})

            # ========== 第 9 阶段: CI/CD 配置 ==========
            _start_stage("9", "CI/CD 配置")
            if _should_skip_for_resume(9):
                self.console.print("[yellow]第 9 阶段: CI/CD 配置 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print(
                    f"[cyan]第 9 阶段: 生成 CI/CD 配置 ({args.cicd.upper()})...[/cyan]"
                )
                from .deployers import CICDGenerator

                cicd_gen = CICDGenerator(
                    project_dir=project_dir,
                    name=project_name,
                    tech_stack=tech_stack,
                    platform=self._normalize_cicd_platform(args.cicd),
                )

                cicd_files = cicd_gen.generate()

                for file_path, content in cicd_files.items():
                    full_path = project_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    self.console.print(f"  [green]✓[/green] {file_path}")

                self.console.print("")
                _record_stage(True, details={"generated_files": len(cicd_files)})

            # ========== 第 10 阶段: 部署修复模板 ==========
            _start_stage("10", "部署修复模板")
            if _should_skip_for_resume(10):
                self.console.print("[yellow]第 10 阶段: 部署修复模板 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 10 阶段: 生成部署修复模板...[/cyan]")
                remediation_outputs = self._export_deploy_remediation_templates(
                    project_dir=project_dir,
                    cicd_platform=args.cicd,
                    only_missing=True,
                )
                self.console.print(
                    f"  [green]✓[/green] 环境模板: {remediation_outputs['env_file']}"
                )
                self.console.print(
                    f"  [green]✓[/green] 检查清单: {remediation_outputs['checklist_file']}"
                )
                self.console.print(
                    f"  [dim]缺失变量条目: {remediation_outputs['items_count']}[/dim]"
                )
                if remediation_outputs.get("per_platform_files"):
                    self.console.print(
                        f"  [green]✓[/green] 平台拆分模板: {len(remediation_outputs['per_platform_files'])} 组"
                    )
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "items_count": remediation_outputs["items_count"],
                        "per_platform_groups": len(
                            remediation_outputs.get("per_platform_files") or []
                        ),
                    },
                )

            # ========== 第 11 阶段: 数据库迁移 + 项目交付包 ==========
            _start_stage("11", "迁移与交付")
            if _should_skip_for_resume(11):
                self.console.print("[yellow]第 11 阶段: 迁移与交付 (resume 跳过)[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "resume"})
            else:
                self.console.print("[cyan]第 11 阶段: 生成数据库迁移脚本 + 项目交付包...[/cyan]")
                from .deployers import DeliveryPackager, MigrationGenerator

                migration_gen = MigrationGenerator(
                    project_dir=project_dir, name=project_name, tech_stack=tech_stack
                )

                migration_files = migration_gen.generate()

                for file_path, content in migration_files.items():
                    full_path = project_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(content, encoding="utf-8")
                    self.console.print(f"  [green]✓[/green] {file_path}")

                packager = DeliveryPackager(
                    project_dir=project_dir,
                    name=project_name,
                    version=__version__,
                )
                delivery_outputs = packager.package(cicd_platform=args.cicd)
                missing_required_raw = delivery_outputs.get("missing_required_count", 0)
                missing_required_count = (
                    missing_required_raw if isinstance(missing_required_raw, int) else 0
                )
                self.console.print(f"  [green]✓[/green] 清单: {delivery_outputs['manifest_file']}")
                self.console.print(f"  [green]✓[/green] 报告: {delivery_outputs['report_file']}")
                self.console.print(f"  [green]✓[/green] 交付包: {delivery_outputs['archive_file']}")
                self.console.print(
                    f"  [dim]状态: {delivery_outputs['status']} | 缺失必需项: {missing_required_count}[/dim]"
                )
                if missing_required_count > 0:
                    self.console.print(
                        "[red]  交付包标记为 incomplete，当前不得进入发布演练验证[/red]"
                    )
                    _record_stage(
                        False,
                        details={
                            "migration_files": len(migration_files),
                            "delivery_status": delivery_outputs["status"],
                            "delivery_missing_required_count": missing_required_count,
                        },
                    )
                    metric_files = _finalize_metrics(
                        success=False, reason="delivery_packaging_incomplete"
                    )
                    contract_files = _finalize_contract(
                        success=False, reason="delivery_packaging_incomplete"
                    )
                    _persist_run_state(
                        "failed",
                        {
                            "failure_reason": "delivery_packaging_incomplete",
                            "failed_stage": "11",
                            "metrics_file": str(metric_files["json"]),
                            "contract_file": str(contract_files["json"]),
                        },
                    )
                    _flush_resume_audit(
                        status="failed", failure_reason="delivery_packaging_incomplete"
                    )
                    self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                    self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                    if resume_audit_files:
                        self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                    return 1
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "migration_files": len(migration_files),
                        "delivery_status": delivery_outputs["status"],
                        "delivery_missing_required_count": missing_required_count,
                    },
                )

            # ========== 第 12 阶段: 发布演练验证 ==========
            _start_stage("12", "发布演练验证")
            self.console.print("[cyan]第 12 阶段: 发布演练文档与验证...[/cyan]")
            from .deployers import LaunchRehearsalGenerator, LaunchRehearsalRunner

            rehearsal_generator = LaunchRehearsalGenerator(
                project_dir=project_dir,
                name=project_name,
                tech_stack=tech_stack,
            )
            rehearsal_files = rehearsal_generator.generate(cicd_platform=args.cicd or "github")
            for relative_path, content in rehearsal_files.items():
                full_path = project_dir / relative_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                self.console.print(f"  [green]✓[/green] {relative_path}")

            if args.skip_rehearsal_verify:
                self.console.print("[yellow]发布演练验证已跳过（--skip-rehearsal-verify）[/yellow]")
                self.console.print("")
                _record_stage(True, details={"skipped": True, "reason": "skip-rehearsal-verify"})
            elif args.skip_redteam or args.skip_quality_gate:
                self.console.print("[yellow]检测到上游门禁被跳过，发布演练验证自动跳过[/yellow]")
                self.console.print("[dim]提示: 建议在不跳过红队/质量门禁时执行完整发布演练[/dim]")
                self.console.print("")
                _record_stage(
                    True,
                    details={
                        "skipped": True,
                        "reason": "prerequisite_skipped",
                        "skip_redteam": bool(args.skip_redteam),
                        "skip_quality_gate": bool(args.skip_quality_gate),
                    },
                )
            else:
                metrics_snapshot_file = _write_metrics_snapshot()
                _write_contract_snapshot()
                runner = LaunchRehearsalRunner(
                    project_dir=project_dir,
                    project_name=project_name,
                    cicd_platform=args.cicd or "github",
                )
                rehearsal_result = runner.run()
                rehearsal_reports = runner.write(rehearsal_result)
                status = "[green]通过[/green]" if rehearsal_result.passed else "[red]未通过[/red]"
                self.console.print(f"  {status} 分数: {rehearsal_result.score}/100")
                self.console.print(f"  [green]✓[/green] 报告: {rehearsal_reports['markdown']}")
                self.console.print(f"  [green]✓[/green] 数据: {rehearsal_reports['json']}")
                self.console.print(f"  [dim]指标快照: {metrics_snapshot_file}[/dim]")
                self.console.print("")

                if not rehearsal_result.passed:
                    _record_stage(
                        False,
                        details={
                            "score": rehearsal_result.score,
                            "failed_checks": [
                                check.name for check in rehearsal_result.failed_checks
                            ],
                        },
                    )
                    metric_files = _finalize_metrics(success=False, reason="rehearsal_failed")
                    contract_files = _finalize_contract(success=False, reason="rehearsal_failed")
                    _persist_run_state(
                        "failed",
                        {
                            "failure_reason": "rehearsal_failed",
                            "failed_stage": "12",
                            "metrics_file": str(metric_files["json"]),
                            "contract_file": str(contract_files["json"]),
                        },
                    )
                    _flush_resume_audit(status="failed", failure_reason="rehearsal_failed")
                    self.console.print("[red]发布演练验证未通过，流水线终止[/red]")
                    for check in rehearsal_result.failed_checks:
                        self.console.print(f"  - {check.name}: {check.detail}")
                    self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
                    self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
                    if resume_audit_files:
                        self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
                    return 1

                _record_stage(
                    True,
                    details={
                        "score": rehearsal_result.score,
                        "failed_checks": len(rehearsal_result.failed_checks),
                    },
                )

            metric_files = _finalize_metrics(success=True)
            contract_files = _finalize_contract(success=True)
            from .analyzer import FeatureChecklistBuilder

            feature_checklist_builder = FeatureChecklistBuilder(project_dir)
            feature_coverage_report = feature_checklist_builder.build()
            feature_checklist_files = feature_checklist_builder.write(feature_coverage_report)
            gate_stage_ids = ("5", "6", "12")
            skipped_gates = [
                stage_execution_state[stage]["title"]
                for stage in gate_stage_ids
                if bool(
                    stage_execution_state.get(stage, {}).get("details", {}).get("skipped", False)
                )
            ]
            full_gate_passed = not skipped_gates
            scope_fully_implemented = feature_coverage_report.status == "ready"
            scope_has_high_priority_gap = feature_coverage_report.high_priority_gap_count > 0
            if full_gate_passed and scope_fully_implemented:
                completion_title = "流程完成（全门禁通过，范围完成）"
                completion_style = "green"
            elif full_gate_passed:
                completion_title = "流程完成（全门禁通过，范围存在缺口）"
                completion_style = "yellow"
            else:
                completion_title = "流程完成（存在跳过门禁）"
                completion_style = "yellow"

            # ========== 完成 ==========
            self.console.print(f"[cyan]{'=' * 60}[/cyan]")
            self.console.print(f"[{completion_style}]✓ {completion_title}[/{completion_style}]")
            self.console.print(f"[cyan]{'=' * 60}[/cyan]")
            self.console.print("")
            if full_gate_passed:
                if scope_fully_implemented:
                    self.console.print(
                        "[green]交付状态: 当前运行已完成，且红队 / 质量 / 演练门禁均已通过，当前范围覆盖率未发现显式缺口。[/green]"
                    )
                else:
                    self.console.print(
                        "[yellow]交付状态: 当前运行已完成，且门禁已通过；但这不等于 PRD 全量范围已实现完成。[/yellow]"
                    )
            else:
                self.console.print(
                    "[yellow]交付状态: 当前运行已完成，但存在跳过门禁；这不等于严格意义上的“全部通过”。[/yellow]"
                )
                self.console.print(f"[yellow]已跳过门禁: {', '.join(skipped_gates)}[/yellow]")
            coverage_text = (
                f"{feature_coverage_report.coverage_rate:.1f}%"
                if feature_coverage_report.coverage_rate is not None
                else "unknown"
            )
            self.console.print(
                f"[cyan]范围覆盖率:[/cyan] {coverage_text} | 状态: {feature_coverage_report.status} | "
                f"高优先级缺口: {feature_coverage_report.high_priority_gap_count}"
            )
            if not scope_fully_implemented or scope_has_high_priority_gap:
                self.console.print(f"[yellow]{feature_coverage_report.summary}[/yellow]")
            self.console.print("")
            self.console.print("[cyan]生成的文件:[/cyan]")
            self.console.print("  文档:")
            self.console.print(f"    - 需求增强报告: output/{project_name}-research.md")
            self.console.print(f"    - PRD: output/{project_name}-prd.md")
            self.console.print(f"    - 架构: output/{project_name}-architecture.md")
            self.console.print(f"    - UI/UX: output/{project_name}-uiux.md")
            self.console.print(f"    - 执行路线图: output/{project_name}-execution-plan.md")
            self.console.print(f"    - 前端蓝图: output/{project_name}-frontend-blueprint.md")
            if not args.skip_redteam:
                self.console.print(f"    - 红队审查: output/{project_name}-redteam.md")
            if not args.skip_quality_gate:
                self.console.print(f"    - 质量门禁: output/{project_name}-quality-gate.md")
            self.console.print(f"    - 代码审查: output/{project_name}-code-review.md")
            self.console.print(f"    - AI 提示词: output/{project_name}-ai-prompt.md")
            self.console.print("")
            self.console.print("  前端演示:")
            self.console.print("    - output/frontend/index.html")
            self.console.print("    - output/frontend/styles.css")
            self.console.print("    - output/frontend/app.js")
            self.console.print("")
            if not args.skip_scaffold:
                self.console.print("  宿主实现参考:")
                self.console.print("    - frontend/src/*")
                self.console.print("    - backend/src/*")
                self.console.print("    - backend/API_CONTRACT.md")
                self.console.print("    - backend/migrations/*.sql")
                if task_execution_summary is not None and task_execution_summary.report_file:
                    rel: Path | str
                    try:
                        rel = Path(str(task_execution_summary.report_file)).relative_to(project_dir)
                    except ValueError:
                        rel = Path(str(task_execution_summary.report_file)).name
                    self.console.print(f"    - {rel}")
                self.console.print("")
            self.console.print("  CI/CD:")
            for file_path in cicd_files.keys():
                self.console.print(f"    - {file_path}")
            self.console.print("")
            if remediation_outputs.get("env_file"):
                self.console.print("  部署修复模板:")
                self.console.print(f"    - {Path(remediation_outputs['env_file']).name}")
                if remediation_outputs.get("checklist_file"):
                    try:
                        self.console.print(
                            f"    - {Path(remediation_outputs['checklist_file']).relative_to(project_dir)}"
                        )
                    except ValueError:
                        self.console.print(
                            f"    - {Path(remediation_outputs['checklist_file']).name}"
                        )
            per_platform_files = remediation_outputs.get("per_platform_files")
            if isinstance(per_platform_files, list):
                for item in per_platform_files:
                    if not isinstance(item, dict):
                        continue
                    checklist_file = item.get("checklist_file")
                    if isinstance(checklist_file, str):
                        self.console.print(f"    - {Path(checklist_file).relative_to(project_dir)}")
                    env_file = item.get("env_file")
                    if isinstance(env_file, str):
                        self.console.print(f"    - {Path(env_file).relative_to(project_dir)}")
            self.console.print("")
            self.console.print("  数据库迁移:")
            for file_path in migration_files.keys():
                self.console.print(f"    - {file_path}")
            self.console.print("")
            self.console.print("  范围覆盖审计:")
            self.console.print(
                f"    - {Path(str(feature_checklist_files['markdown'])).relative_to(project_dir)}"
            )
            self.console.print(
                f"    - {Path(str(feature_checklist_files['json'])).relative_to(project_dir)}"
            )
            self.console.print("")
            self.console.print("  项目交付包:")
            self.console.print(
                f"    - {Path(str(delivery_outputs['manifest_file'])).relative_to(project_dir)}"
            )
            self.console.print(
                f"    - {Path(str(delivery_outputs['report_file'])).relative_to(project_dir)}"
            )
            self.console.print(
                f"    - {Path(str(delivery_outputs['archive_file'])).relative_to(project_dir)}"
            )
            self.console.print("")
            self.console.print("  发布演练:")
            self.console.print(f"    - output/rehearsal/{project_name}-launch-rehearsal.md")
            self.console.print(f"    - output/rehearsal/{project_name}-rollback-playbook.md")
            self.console.print(f"    - output/rehearsal/{project_name}-smoke-checklist.md")
            if (
                not args.skip_rehearsal_verify
                and not args.skip_redteam
                and not args.skip_quality_gate
            ):
                self.console.print(f"    - output/rehearsal/{project_name}-rehearsal-report.md")
                self.console.print(f"    - output/rehearsal/{project_name}-rehearsal-report.json")
            self.console.print("")
            self.console.print("[cyan]下一步:[/cyan]")
            self.console.print("  1. 打开 output/frontend/index.html 评审前端实施蓝图")
            self.console.print("  2. 对照执行路线图按阶段推进开发")
            self.console.print("  3. 使用代码审查指南进行评审和修复")
            self.console.print("  4. 配置 CI/CD 平台 (设置 secrets/credentials)")
            self.console.print("  5. 运行数据库迁移脚本并推送代码触发流水线")
            self.console.print("  6. 执行并保存发布演练报告用于上线审批")
            self.console.print("  7. 使用 output/delivery/* 作为对外交付包")
            self.console.print(
                f"  8. 查看 pipeline 指标: output/{project_name}-pipeline-metrics.md"
            )
            if not full_gate_passed:
                self.console.print(
                    "  9. 若要获得严格意义上的全门禁通过，请重新执行被跳过的红队 / 质量 / 演练阶段"
                )
            elif not scope_fully_implemented:
                self.console.print(
                    "  9. 若要确认 PRD 范围是否真正实现完成，请查看 feature checklist 并补齐高优先级缺口"
                )
            self.console.print("")
            self.console.print("[cyan]可观测性:[/cyan]")
            self.console.print(f"  - 指标 JSON: {metric_files['json']}")
            self.console.print(f"  - 指标 Markdown: {metric_files['markdown']}")
            self.console.print(f"  - 契约 JSON: {contract_files['json']}")
            self.console.print(f"  - 契约 Markdown: {contract_files['markdown']}")
            if "history_json" in metric_files:
                self.console.print(f"  - 历史 JSON: {metric_files['history_json']}")
            if "history_markdown" in metric_files:
                self.console.print(f"  - 历史 Markdown: {metric_files['history_markdown']}")
            self.console.print("")
            _persist_run_state(
                "success",
                {
                    "metrics_file": str(metric_files["json"]),
                    "contract_file": str(contract_files["json"]),
                    "full_gate_passed": full_gate_passed,
                    "skipped_gates": skipped_gates,
                    "scope_coverage_status": feature_coverage_report.status,
                    "scope_coverage_rate": feature_coverage_report.coverage_rate,
                    "scope_gap_count": feature_coverage_report.missing_count
                    + feature_coverage_report.unknown_count,
                    "scope_high_priority_gap_count": feature_coverage_report.high_priority_gap_count,
                    "scope_feature_checklist_file": str(feature_checklist_files["json"]),
                },
            )
            _flush_resume_audit(status="success")
            if resume_audit_files:
                self.console.print("[cyan]恢复审计:[/cyan]")
                self.console.print(f"  - JSON: {resume_audit_files['json']}")
                self.console.print(f"  - Markdown: {resume_audit_files['markdown']}")
                self.console.print("")

        except Exception as e:
            _record_stage(False, details={"error": str(e)})
            metric_files = _finalize_metrics(success=False, reason=str(e))
            contract_files = _finalize_contract(success=False, reason=str(e))
            failed_stage_label = current_stage or "unknown"
            _persist_run_state(
                "failed",
                {
                    "failure_reason": str(e),
                    "failed_stage": failed_stage_label,
                    "metrics_file": str(metric_files["json"]),
                    "contract_file": str(contract_files["json"]),
                },
            )
            _flush_resume_audit(status="failed", failure_reason=str(e))
            self.console.print(f"[red]流水线失败: {e}[/red]")
            import traceback

            self.console.print(traceback.format_exc())
            self.console.print(f"[dim]指标报告: {metric_files['json']}[/dim]")
            self.console.print(f"[dim]契约审计: {contract_files['markdown']}[/dim]")
            if resume_audit_files:
                self.console.print(f"[dim]恢复审计: {resume_audit_files['markdown']}[/dim]")
            return 1

        return 0
