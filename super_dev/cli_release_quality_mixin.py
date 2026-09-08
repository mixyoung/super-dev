"""CLI release/quality mixin helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from super_dev.artifact_utils import ui_contract_filename

from .artifact_utils import (
    resolve_active_change_id,
    resolve_current_artifact_prefix,
    sanitize_artifact_name,
)
from .config import ConfigManager
from .evidence_identity import attach_evidence_identity
from .extensions.models import ExtensionStatus, PytestVerificationPlan
from .extensions.service import ExtensionService, ProbeOutcome
from .proof_pack import ProofPackBuilder
from .release_readiness import (
    ReleaseReadinessCheck,
    ReleaseReadinessEvaluator,
    ReleaseReadinessReport,
)


class CliReleaseQualityMixin:
    def _verification_start(self, plan: PytestVerificationPlan | None, *, verbose: bool) -> None:
        self.console.print("正在进行完成前验证", style="cyan")
        self.console.print("原因：发布就绪判断需要对应当前代码的新测试证据。")
        self.console.print(f"测试计划：{plan.plan_id if plan else '配置待校验'}", markup=False)
        scope = "、".join(arg for arg in plan.args if not arg.startswith("-")) if plan else "未确定"
        self.console.print(f"测试范围：{scope[:160]}", markup=False)
        self.console.print("允许写入：本次验证证据目录（测试使用隔离用户目录）。")
        self.console.print("不会执行：提交、推送、部署、推进项目阶段或修改用户级配置。")
        if plan:
            self.console.print(
                f"运行保护时限：{plan.timeout_seconds} 秒（项目配置，不是性能合格线）。"
            )
        if verbose and plan:
            self.console.print(
                f"计划参数：{list(plan.args)}；运行保护时限：{plan.timeout_seconds} 秒",
                markup=False,
            )

    def _verification_summary(self, outcome: ProbeOutcome, check: ReleaseReadinessCheck) -> None:
        label = {ExtensionStatus.PASS: "通过（PASS）", ExtensionStatus.FAIL: "失败（FAIL）"}.get(
            outcome.status,
            "受阻（BLOCKED）",
        )
        if outcome.status == ExtensionStatus.PASS and not check.passed:
            label = "受阻（BLOCKED）"
        self.console.print(f"完成前验证：{label}")
        self.console.print(check.detail.replace(str(Path.cwd()), "项目")[:220], markup=False)
        if outcome.summary is not None:
            counts = outcome.summary
            self.console.print(
                f"测试：{counts.tests}；实际执行：{counts.executed}；跳过：{counts.skipped}；"
                f"失败：{counts.failures}；错误：{counts.errors}。"
            )
        result = outcome.result
        if result is not None:
            cleanup = "已确认" if result.process_tree_clean else "未确认"
            if not result.commands and result.process_tree_clean:
                cleanup = "未启动测试，无需清理"
            changed = {True: "是", False: "否", None: "未确认"}[outcome.candidate_changed]
            self.console.print(f"耗时：{result.duration_ms / 1000:.2f} 秒；进程清理：{cleanup}。")
            self.console.print(f"代码在验证期间变化：{changed}；Super Dev 未推进项目阶段。")
        if outcome.file_changes and any(outcome.file_changes.values()):
            changes = outcome.file_changes
            self.console.print(
                f"文件变化：新增 {len(changes['added'])}；删除 {len(changes['removed'])}；"
                f"修改 {len(changes['modified'])}。"
            )
            for kind, title in (("added", "新增"), ("removed", "删除"), ("modified", "修改")):
                for path in changes[kind][:5]:
                    self.console.print(
                        f"  {title}：{json.dumps(path, ensure_ascii=False)}", markup=False
                    )
            self.console.print("完整文件明细见本次 pytest-summary.json；旧校验值不会被替换。")
        if check.passed:
            self.console.print("影响：仅本次验证通过，不等于项目完成；仍需满足其他发布条件。")
        else:
            self.console.print("影响：当前不能判定发布就绪。")
        if outcome.advisories:
            self.console.print("提醒：意外通过可能表示预期失败标记已过期，请复核该标记。")
        self.console.print(f"下一步：{check.recommendation}", markup=False)
        self.console.print(
            "证据：已保存，可用 --verbose 或 --json 展开（再次调用会重新验证）。"
            if outcome.result_path
            else "证据：结果未落盘，不能作为完整发布证据。"
        )

    @staticmethod
    def _completion_verification_check(outcome: ProbeOutcome) -> ReleaseReadinessCheck:
        summary = outcome.summary
        evidence: dict[str, Any] = {
            "run_id": outcome.run_id,
            "status": outcome.status.value,
            "candidate_digest": (
                outcome.result.candidate.candidate_digest if outcome.result is not None else ""
            ),
            "result_path": str(outcome.result_path or ""),
            "pytest_summary": summary.to_dict() if summary is not None else None,
            "advisories": [item.to_dict() for item in outcome.advisories],
            "plan": outcome.plan.to_dict() if outcome.plan is not None else None,
            "candidate_changed": outcome.candidate_changed,
            "duration_ms": outcome.result.duration_ms if outcome.result else None,
            "process_tree_clean": outcome.result.process_tree_clean if outcome.result else None,
            "file_changes": outcome.file_changes,
        }
        if outcome.status == ExtensionStatus.PASS:
            recommendation = (
                "检查已经过期的预期失败标记。" if outcome.advisories else "继续检查其他发布条件。"
            )
        elif outcome.status == ExtensionStatus.FAIL:
            recommendation = "修复失败测试后，重新执行 `super-dev release readiness`。"
        elif outcome.result and any(command.timed_out for command in outcome.result.commands):
            recommendation = "核查测试进度和项目运行预算，安排完整重跑；未完成的测试不能算通过。"
        else:
            recommendation = "按阻断原因恢复环境或证据后，重新执行发布就绪检查。"
        return ReleaseReadinessCheck(
            name="完成前验证（Fresh Verification）",
            passed=outcome.status == ExtensionStatus.PASS,
            detail=outcome.message,
            severity="critical",
            recommendation=recommendation,
            evidence=evidence,
        )

    def _cmd_release(self, args) -> int:
        """发布就绪度检查"""
        if args.release_command == "proof-pack":
            project_dir = Path.cwd()
            builder = ProofPackBuilder(project_dir)
            proof_report = builder.build(verify_tests=bool(args.verify_tests))
            proof_files = builder.write(proof_report)
            payload = proof_report.to_dict()
            payload["report_file"] = str(proof_files["markdown"])
            payload["json_file"] = str(proof_files["json"])
            payload["summary_file"] = str(proof_files["summary"])

            if args.json:
                self.console.print(json.dumps(payload, ensure_ascii=False, indent=2))
                return 0 if proof_report.status == "ready" else 1

            status = (
                "[green]通过（PASS）[/green]"
                if proof_report.status == "ready"
                else "[red]失败（FAIL）[/red]"
            )
            self.console.print(
                f"[cyan]Proof Pack[/cyan] {status} 证据就绪: {proof_report.ready_count}/{proof_report.total_count}"
            )
            self.console.print(f"  [green]✓[/green] Markdown: {proof_files['markdown']}")
            self.console.print(f"  [green]✓[/green] JSON: {proof_files['json']}")
            self.console.print(f"  [green]✓[/green] Summary: {proof_files['summary']}")
            self.console.print(f"  [dim]{proof_report.executive_summary}[/dim]")
            if proof_report.blockers:
                self.console.print("  [yellow]待补齐项:[/yellow]")
                for artifact in proof_report.blockers[:8]:
                    self.console.print(f"    - {artifact.name}: {artifact.summary}")
                self.console.print("  [cyan]推荐动作:[/cyan]")
                for action in proof_report.next_actions[:5]:
                    self.console.print(f"    - {action}")
            else:
                self.console.print("  [green]所有关键交付证据均已就绪。[/green]")
            return 0 if proof_report.status == "ready" else 1

        if args.release_command != "readiness":
            self.console.print(
                "[yellow]请指定 release 子命令，例如 `super-dev release readiness` 或 `super-dev release proof-pack`[/yellow]"
            )
            return 1

        project_dir = Path.cwd()
        extension_service = None
        try:
            extension_service = ExtensionService(project_dir)
            verification_outcome = extension_service.run_fresh_verification(
                stage="delivery",
                actor="cli",
                on_start=(
                    None
                    if args.json
                    else lambda plan: self._verification_start(
                        plan,
                        verbose=bool(getattr(args, "verbose", False)),
                    )
                ),
            )
        except (OSError, RuntimeError, ValueError) as exc:
            verification_outcome = ProbeOutcome(
                status=ExtensionStatus.BLOCKED,
                message=f"完成前验证无法形成完整证据：{exc}",
            )
        verification_check = (
            None
            if verification_outcome.status == ExtensionStatus.NOT_APPLICABLE
            else self._completion_verification_check(verification_outcome)
        )
        evaluator = ReleaseReadinessEvaluator(project_dir)
        report = evaluator.evaluate(
            verify_tests=bool(args.verify_tests) and verification_check is None,
            preflight_checks=(verification_check,) if verification_check is not None else (),
        )
        if verification_check is not None:
            legacy_report = ReleaseReadinessReport(
                project_name=report.project_name,
                threshold=report.threshold,
                checks=[item for item in report.checks if item is not verification_check],
            )
            try:
                if extension_service is None:
                    raise ValueError("扩展证据目录无法安全初始化")
                metric_path = extension_service.record_verification_metric(
                    verification_outcome,
                    legacy_would_pass=legacy_report.passed,
                )
            except (OSError, ValueError) as exc:
                verification_check.passed = False
                verification_check.detail += f" 指标证据写入失败：{exc}"
                verification_check.evidence["status"] = "BLOCKED"
            else:
                if metric_path is not None:
                    verification_check.evidence["metric_path"] = str(metric_path)
        files = evaluator.write(report)
        payload = report.to_dict()
        payload["report_file"] = str(files["markdown"])
        payload["json_file"] = str(files["json"])

        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if report.passed else 1

        status = "[green]通过（PASS）[/green]" if report.passed else "[red]失败（FAIL）[/red]"
        self.console.print(f"[cyan]发布就绪度[/cyan] {status} 分数: {report.score}/100")
        if report.governance_notes:
            self.console.print("治理资料仅作不计分提示，详见报告；文件存在不代表验证通过。")
        if verification_check is not None:
            self._verification_summary(verification_outcome, verification_check)
            if not getattr(args, "verbose", False):
                remaining = [
                    item.name for item in report.failed_checks if item is not verification_check
                ]
                if remaining:
                    self.console.print(
                        f"其他待收尾项（{len(remaining)}）：" + "、".join(remaining[:4])
                    )
                return 0 if report.passed else 1
            self.console.print(
                json.dumps(verification_check.evidence, ensure_ascii=False, indent=2), markup=False
            )
        self.console.print(f"  [green]✓[/green] Markdown: {files['markdown']}")
        self.console.print(f"  [green]✓[/green] JSON: {files['json']}")

        if report.failed_checks:
            self.console.print("  [yellow]待收尾项:[/yellow]")
            for check in report.failed_checks[:8]:
                recommendation = f" | 建议: {check.recommendation}" if check.recommendation else ""
                self.console.print(f"    - {check.name}: {check.detail}{recommendation}")
        else:
            self.console.print("  [green]所有关键发布项均已满足。[/green]")

        return 0 if report.passed else 1

    def _cmd_quality(self, args) -> int:
        """质量检查"""
        from .reviewers import QualityGateChecker, UIReviewReviewer
        from .reviewers.redteam import load_persisted_redteam_report

        project_dir = Path.cwd()
        output_dir = project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config_manager = ConfigManager(project_dir)
        config = config_manager.load()

        project_name = resolve_current_artifact_prefix(
            project_dir,
            configured_name=self._sanitize_project_name(config.name or project_dir.name),
            fallback_name=project_dir.name,
        )
        tech_stack = {
            "platform": config.platform,
            "frontend": self._normalize_pipeline_frontend(config.frontend),
            "backend": config.backend,
            "domain": config.domain,
        }

        self.console.print(f"[cyan]运行质量检查: {args.type}[/cyan]")

        if args.type == "ui-review":
            reviewer = UIReviewReviewer(
                project_dir=project_dir,
                name=project_name,
                tech_stack=tech_stack,
            )
            report = reviewer.review()
            review_file = output_dir / f"{project_name}-ui-review.md"
            review_json_file = output_dir / f"{project_name}-ui-review.json"
            alignment_file = output_dir / f"{project_name}-ui-contract-alignment.md"
            alignment_json_file = output_dir / f"{project_name}-ui-contract-alignment.json"
            review_file.write_text(report.to_markdown(), encoding="utf-8")
            review_json_file.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            alignment_file.write_text(report.alignment_markdown(), encoding="utf-8")
            alignment_json_file.write_text(
                json.dumps(report.alignment_summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            status = "[green]通过（PASS）[/green]" if report.passed else "[red]失败（FAIL）[/red]"
            self.console.print(f"  {status} 总分: {report.score}/100")
            self.console.print(f"  [green]✓[/green] 报告: {review_file}")
            self.console.print(f"  [green]✓[/green] JSON: {review_json_file}")
            self.console.print(f"  [green]✓[/green] UI 契约对齐: {alignment_file}")
            self.console.print(f"  [green]✓[/green] UI 契约对齐 JSON: {alignment_json_file}")
            if report.findings:
                self.console.print("[yellow]主要问题:[/yellow]")
                for finding in report.findings[:5]:
                    self.console.print(f"  - [{finding.level}] {finding.title}")
            return 0 if report.passed else 1

        if args.type == "redteam":
            from .reviewers import RedTeamReviewer

            reviewer = RedTeamReviewer(
                project_dir=project_dir,
                name=project_name,
                tech_stack=tech_stack,
            )
            report = reviewer.review()
            report_file = output_dir / f"{project_name}-redteam.md"
            report_json_file = output_dir / f"{project_name}-redteam.json"
            report_file.write_text(report.to_markdown(), encoding="utf-8")
            report_json_file.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            status = "[green]通过（PASS）[/green]" if report.passed else "[red]失败（FAIL）[/red]"
            self.console.print(f"  {status} 总分: {report.total_score}/100")
            self.console.print(f"  [green]✓[/green] 报告: {report_file}")
            self.console.print(f"  [green]✓[/green] JSON: {report_json_file}")
            if report.blocking_reasons:
                self.console.print("[yellow]阻断原因:[/yellow]")
                for reason in report.blocking_reasons:
                    self.console.print(f"  - {reason}")
            return 0 if report.passed else 1

        # 轻量文档检查
        if args.type in {"prd", "architecture", "ui", "ux"}:
            suffix_map = {
                "prd": "prd",
                "architecture": "architecture",
                "ui": "uiux",
                "ux": "uiux",
            }
            suffix = suffix_map[args.type]
            active_change_id = resolve_active_change_id(project_dir)
            if active_change_id:
                artifact_prefix = sanitize_artifact_name(active_change_id)
                expected_file = output_dir / f"{artifact_prefix}-{suffix}.md"
                matched = [expected_file] if expected_file.is_file() else []
                expected_label = expected_file.name
            else:
                expected_label = f"*-{suffix}.md"
                matched = sorted(output_dir.glob(expected_label))
            if matched:
                self.console.print(
                    f"[green]✓[/green] 检测到 {len(matched)} 个文档: {expected_label}"
                )
                for file_path in matched[:5]:
                    self.console.print(f"  - {file_path}")
                return 0

            self.console.print(f"[red]未找到文档: output/{expected_label}[/red]")
            return 1

        # 代码或全量检查走质量门禁评估
        gate_checker = QualityGateChecker(
            project_dir=project_dir,
            name=project_name,
            tech_stack=tech_stack,
            threshold_override=config.quality_gate,
            host_compatibility_min_score_override=config.host_compatibility_min_score,
            host_compatibility_min_ready_hosts_override=config.host_compatibility_min_ready_hosts,
        )
        persisted_redteam = load_persisted_redteam_report(project_dir, project_name)
        gate_result = gate_checker.check(
            redteam_report=persisted_redteam[1] if persisted_redteam else None
        )

        gate_file = output_dir / f"{project_name}-quality-gate.md"
        gate_json_file = output_dir / f"{project_name}-quality-gate.json"
        quality_dependencies = [
            output_dir / f"{project_name}-uiux.md",
            *gate_checker.latest_fresh_verification_dependencies,
        ]
        if gate_checker.frontend_required:
            quality_dependencies[:0] = [
                output_dir / f"{project_name}-ui-review.json",
                output_dir / f"{project_name}-ui-contract-alignment.json",
            ]
        gate_file.write_text(gate_result.to_markdown(), encoding="utf-8")
        gate_json_file.write_text(
            json.dumps(
                attach_evidence_identity(
                    gate_result.to_dict(),
                    project_dir=project_dir,
                    artifact_name="quality-gate",
                    dependencies=quality_dependencies,
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if gate_checker.latest_ui_review_report is not None:
            ui_review_file = output_dir / f"{project_name}-ui-review.md"
            ui_review_json_file = output_dir / f"{project_name}-ui-review.json"
            alignment_file = output_dir / f"{project_name}-ui-contract-alignment.md"
            alignment_json_file = output_dir / f"{project_name}-ui-contract-alignment.json"
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
                            output_dir / ui_contract_filename(project_name),
                            output_dir / f"{project_name}-uiux.md",
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
                            output_dir / ui_contract_filename(project_name),
                            output_dir / f"{project_name}-uiux.md",
                        ],
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            if (output_dir / "frontend" / "index.html").exists():
                self._write_frontend_runtime_validation(
                    project_dir=project_dir,
                    output_dir=output_dir,
                    project_name=project_name,
                )

        scenario_label = "0-1 新建项目" if gate_result.scenario == "0-1" else "1-N+1 增量开发"
        status = "[green]通过（PASS）[/green]" if gate_result.passed else "[red]失败（FAIL）[/red]"

        self.console.print(f"  [dim]场景: {scenario_label}[/dim]")
        self.console.print(
            f"  {status} 门禁分（加权）: {gate_result.gate_score:.1f}/100 "
            f"(阈值 {gate_result.threshold:g}/100)"
        )
        self.console.print(f"  [dim]{gate_result.executive_summary}[/dim]")
        self.console.print(f"  [green]✓[/green] 报告: {gate_file}")
        if gate_checker.latest_ui_review_report is not None:
            self.console.print(
                f"  [green]✓[/green] UI 审查: {output_dir / f'{project_name}-ui-review.md'}"
            )
            self.console.print(
                f"  [green]✓[/green] UI 审查 JSON: {output_dir / f'{project_name}-ui-review.json'}"
            )
            self.console.print(
                f"  [green]✓[/green] UI 契约对齐: {output_dir / f'{project_name}-ui-contract-alignment.md'}"
            )

        if not gate_result.passed and gate_result.critical_failures:
            self.console.print("[yellow]关键失败项:[/yellow]")
            for failure in gate_result.critical_failures:
                self.console.print(f"  - {failure}")

        # Post-merge safety check: detect silently dropped code hunks
        from .merge_safety import detect_dropped_hunks

        merge_result = detect_dropped_hunks(project_dir)
        if merge_result["merge_detected"]:
            if merge_result["safe"]:
                self.console.print("[green]  ✓ 合并安全检查通过 — 未检测到丢失的代码块[/green]")
            else:
                self.console.print(
                    f"[red]  ✗ 合并安全检查: 检测到 {len(merge_result['dropped_files'])} "
                    f"个文件可能丢失代码块[/red]"
                )
                for entry in merge_result["dropped_files"]:
                    self.console.print(
                        f"    [yellow]{entry['file']}[/yellow] (来自 {entry['parent']})"
                    )
                    for block in entry["blocks"][:3]:
                        self.console.print(
                            f"      行 {block['start_line']}-{block['end_line']} "
                            f"({block['line_count']} 行)"
                        )

        return 0 if gate_result.passed else 1

    # ==================== v3.0 Intelligence Commands ====================

    def _cmd_compliance(self, args) -> int:
        """Run spec compliance checks."""
        project_dir = Path.cwd()
        output_dir = project_dir / "output"
        check_type = getattr(args, "type", "all")
        as_json = getattr(args, "json", False)
        save = getattr(args, "save", False)

        results: dict[str, Any] = {}

        if check_type in ("all", "spec"):
            from .reviewers.spec_compliance import run_spec_compliance

            spec_report = run_spec_compliance(project_dir, output_dir if save else None)
            results["spec_compliance"] = spec_report.to_dict()
            if not as_json:
                self.console.print("\n[bold]Spec Compliance[/bold]")
                self.console.print(
                    f"  Requirements: {spec_report.total_requirements} | "
                    f"Found: {spec_report.found} | Partial: {spec_report.partial} | "
                    f"Missing: {spec_report.missing}"
                )
                self.console.print(
                    f"  Coverage: {spec_report.coverage_percent}% | "
                    f"Score: {spec_report.score}/100"
                )

        if check_type in ("all", "architecture"):
            from .reviewers.architecture_drift import run_architecture_drift

            architecture_report = run_architecture_drift(project_dir, output_dir if save else None)
            results["architecture_drift"] = architecture_report.to_dict()
            if not as_json:
                self.console.print("\n[bold]Architecture Drift[/bold]")
                self.console.print(
                    f"  Drifts: {architecture_report.total_drifts} | "
                    f"Critical: {architecture_report.critical_count} | "
                    f"Score: {architecture_report.score}/100"
                )

        if check_type in ("all", "uiux"):
            from .reviewers.uiux_compliance import run_uiux_compliance

            uiux_report = run_uiux_compliance(project_dir, output_dir if save else None)
            results["uiux_compliance"] = uiux_report.to_dict()
            if not as_json:
                self.console.print("\n[bold]UIUX Compliance[/bold]")
                self.console.print(
                    f"  Files scanned: {uiux_report.files_scanned} | "
                    f"Violations: {uiux_report.total_violations} | "
                    f"Critical: {uiux_report.critical_count} | Score: {uiux_report.score}/100"
                )

        if as_json:
            self.console.print_json(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
