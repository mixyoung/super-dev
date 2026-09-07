"""最小扩展平台的 Core 服务入口。"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import sysconfig
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any, cast

from ..config import get_config_manager
from ..user_directories import UserDirectoryContext
from .evidence import EvidenceStore, build_candidate_identity, candidate_matches, utc_now
from .executor import StructuredExecutor
from .manifest import ManifestValidationError, load_manifest
from .models import (
    CandidateIdentity,
    Capability,
    CommandExecution,
    CommandSpec,
    ExtensionEvent,
    ExtensionEventType,
    ExtensionManifest,
    ExtensionResult,
    ExtensionStatus,
    PytestSummary,
    PytestVerificationPlan,
    VerificationAdvisory,
    WriteSpec,
)
from .ownership import evaluate_ownership
from .path_guard import PathGuard
from .pytest_plan import PytestPlanValidationError, parse_pytest_verification_plan
from .source_lock import SourceLockVerifier, SourceVerification
from .verification_metrics import summarize_verification_metrics


@dataclass(frozen=True)
class ProbeOutcome:
    status: ExtensionStatus
    message: str
    result_path: Path | None = None
    result: ExtensionResult | None = None
    summary: PytestSummary | None = None
    advisories: tuple[VerificationAdvisory, ...] = ()
    run_id: str = ""
    plan: PytestVerificationPlan | None = None
    candidate_changed: bool | None = None


class ExtensionService:
    BUILTIN_ID = "contract-probe"
    FRESH_VERIFICATION_ID = "fresh-verification"
    # Core's receipt authority is independent of an untrusted extension manifest.
    _RECEIPT_WRITES = WriteSpec(
        allowed=(
            ".super-dev/extensions/runs/**",
            ".super-dev/extensions/metrics/**",
            ".super-dev/extensions/history.jsonl",
        ),
        forbidden=("$USER_SURFACES/**",),
    )

    def __init__(
        self,
        project_dir: Path,
        *,
        user_directories: UserDirectoryContext | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.user_directories = user_directories or UserDirectoryContext.current()
        self.package_root = Path(__file__).resolve().parent
        self.builtin_manifest_path = self.package_root / "builtins" / "contract_probe.yaml"
        self.fresh_verification_manifest_path = (
            self.package_root / "builtins" / "fresh_verification.yaml"
        )
        self.builtin_lock_path = self.package_root / "sources.lock.yaml"
        self.store = EvidenceStore(self.project_dir)

    def config(self) -> dict[str, Any]:
        config = get_config_manager(self.project_dir).config.extensions
        return dict(config) if isinstance(config, dict) else {}

    def enabled(self) -> bool:
        return self.config().get("enabled") is True

    def allowed_builtin_methods(self) -> tuple[str, ...]:
        raw = self.config().get("allowed_builtin_methods", [])
        if not isinstance(raw, list):
            return ()
        return tuple(str(item) for item in raw if str(item).strip())

    def load(self, manifest_path: Path | str) -> ExtensionManifest:
        return cast(ExtensionManifest, load_manifest(manifest_path))

    def source_verifier(self, manifest: ExtensionManifest) -> SourceLockVerifier:
        builtin_manifests = {
            self.builtin_manifest_path.resolve(),
            self.fresh_verification_manifest_path.resolve(),
        }
        if manifest.manifest_path and manifest.manifest_path in builtin_manifests:
            return SourceLockVerifier(
                source_root=self.package_root,
                lock_path=self.builtin_lock_path,
            )
        return SourceLockVerifier(
            source_root=self.project_dir,
            lock_path=self.project_dir / "extensions" / "sources.lock.yaml",
        )

    def verify_source(self, manifest: ExtensionManifest) -> SourceVerification:
        return self.source_verifier(manifest).verify(manifest)

    @staticmethod
    def _call_builtin(manifest: ExtensionManifest, context: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "super_dev.extensions.builtins.contract_probe:run",
            "super_dev.extensions.builtins.fresh_verification:run",
        }
        if manifest.execution.entrypoint not in allowed:
            raise ValueError("内置入口不在 Core 允许列表")
        module_name, function_name = manifest.execution.entrypoint.split(":", 1)
        module = importlib.import_module(module_name)
        function = getattr(module, function_name, None)
        if function is None or not callable(function):
            raise ValueError("内置入口不存在或不可调用")
        payload = function(context)
        if not isinstance(payload, dict):
            raise ValueError("内置适配器必须返回对象")
        return payload

    def _event(
        self,
        *,
        event: ExtensionEventType,
        run_id: str,
        extension_id: str,
        stage: str,
        actor: str,
        source_digest: str = "",
        candidate_digest: str = "",
        result_artifact: str = "",
        message: str = "",
    ) -> None:
        self.store.append_event(
            ExtensionEvent(
                schema_version=1,
                event=event,
                run_id=run_id,
                extension_id=extension_id,
                canonical_stage=stage,
                actor=actor,
                timestamp=utc_now(),
                source_digest=source_digest,
                candidate_digest=candidate_digest,
                result_artifact=result_artifact,
                message=message,
            )
        )

    def probe_contract(self, *, stage: str = "quality", actor: str = "cli") -> ProbeOutcome:
        if not self.enabled():
            return ProbeOutcome(
                status=ExtensionStatus.NOT_APPLICABLE,
                message="当前项目没有启用扩展，正在使用原有 Super Dev 流程。",
            )
        if self.BUILTIN_ID not in self.allowed_builtin_methods():
            return ProbeOutcome(
                status=ExtensionStatus.NOT_APPLICABLE,
                message="扩展已启用，但合同探针不在允许的内置方法列表中。",
            )

        run_id = uuid.uuid4().hex
        started_at = utc_now()
        started = time.monotonic()
        candidate = build_candidate_identity(self.project_dir)
        self._event(
            event=ExtensionEventType.REQUESTED,
            run_id=run_id,
            extension_id=self.BUILTIN_ID,
            stage=stage,
            actor=actor,
            candidate_digest=candidate.candidate_digest,
        )
        previous_result = self.store.latest_result(extension_id=self.BUILTIN_ID)
        if previous_result is not None and not candidate_matches(previous_result, candidate):
            self._event(
                event=ExtensionEventType.EVIDENCE_INVALIDATED,
                run_id=run_id,
                extension_id=self.BUILTIN_ID,
                stage=stage,
                actor=actor,
                candidate_digest=candidate.candidate_digest,
                message="当前代码版本已变化，上一份扩展结果失效。",
            )

        try:
            manifest = load_manifest(self.builtin_manifest_path)
        except ManifestValidationError as exc:
            self._event(
                event=ExtensionEventType.BLOCKED,
                run_id=run_id,
                extension_id=self.BUILTIN_ID,
                stage=stage,
                actor=actor,
                candidate_digest=candidate.candidate_digest,
                message=str(exc),
            )
            return ProbeOutcome(ExtensionStatus.BLOCKED, f"内置清单无效: {exc}")

        source = self.verify_source(manifest)
        if not source.passed:
            message = "; ".join(source.errors)
            self._event(
                event=ExtensionEventType.BLOCKED,
                run_id=run_id,
                extension_id=manifest.id,
                stage=stage,
                actor=actor,
                source_digest=source.identity_digest,
                candidate_digest=candidate.candidate_digest,
                message=message,
            )
            return ProbeOutcome(ExtensionStatus.BLOCKED, message)

        if stage not in manifest.trigger.allowed_stages:
            return ProbeOutcome(
                ExtensionStatus.NOT_APPLICABLE,
                f"合同探针不适用于当前阶段: {stage}",
            )
        decision = evaluate_ownership(
            manifest,
            trusted_capabilities={Capability.WRITE_EVIDENCE},
        )
        if not decision.allowed:
            message = "; ".join(decision.findings)
            if decision.status == ExtensionStatus.BLOCKED:
                self._event(
                    event=ExtensionEventType.BLOCKED,
                    run_id=run_id,
                    extension_id=manifest.id,
                    stage=stage,
                    actor=actor,
                    source_digest=source.identity_digest,
                    candidate_digest=candidate.candidate_digest,
                    message=message,
                )
            return ProbeOutcome(decision.status, message)

        result_path = self.store.run_dir(run_id) / "result.json"
        path_decision = PathGuard(
            self.project_dir,
            manifest.writes,
            user_directories=self.user_directories,
        ).check_write(result_path)
        if not path_decision.allowed:
            self._event(
                event=ExtensionEventType.BLOCKED,
                run_id=run_id,
                extension_id=manifest.id,
                stage=stage,
                actor=actor,
                source_digest=source.identity_digest,
                candidate_digest=candidate.candidate_digest,
                message=path_decision.reason,
            )
            return ProbeOutcome(ExtensionStatus.BLOCKED, path_decision.reason)

        self._event(
            event=ExtensionEventType.STARTED,
            run_id=run_id,
            extension_id=manifest.id,
            stage=stage,
            actor=actor,
            source_digest=source.identity_digest,
            candidate_digest=candidate.candidate_digest,
        )
        try:
            adapter_result = self._call_builtin(
                manifest,
                {
                    "run_id": run_id,
                    "candidate_digest": candidate.candidate_digest,
                    "canonical_stage": stage,
                },
            )
            blocking = [str(item) for item in adapter_result.get("blocking_findings", [])]
            advisory: list[str | VerificationAdvisory] = [
                str(item) for item in adapter_result.get("advisory_findings", [])
            ]
            passed = adapter_result.get("passed") is True and not blocking
            status = ExtensionStatus.PASS if passed else ExtensionStatus.FAIL
        except Exception as exc:
            blocking = [f"内置合同探针失败: {exc}"]
            advisory = []
            status = ExtensionStatus.BLOCKED

        finished_at = utc_now()
        result = ExtensionResult(
            schema_version=1,
            run_id=run_id,
            extension_id=manifest.id,
            extension_version=manifest.version,
            status=status,
            canonical_stage=stage,
            source_digest=source.identity_digest,
            candidate=candidate,
            writes=[str(result_path.relative_to(self.project_dir)).replace("\\", "/")],
            blocking_findings=blocking,
            advisory_findings=advisory,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(time.monotonic() - started) * 1000,
            process_tree_clean=True,
        )
        written = self.store.write_result(result)
        relative_written = str(written.relative_to(self.project_dir)).replace("\\", "/")
        event_type = (
            ExtensionEventType.COMPLETED
            if status in {ExtensionStatus.PASS, ExtensionStatus.FAIL}
            else ExtensionEventType.BLOCKED
        )
        self._event(
            event=event_type,
            run_id=run_id,
            extension_id=manifest.id,
            stage=stage,
            actor=actor,
            source_digest=source.identity_digest,
            candidate_digest=candidate.candidate_digest,
            result_artifact=relative_written,
            message="; ".join(blocking),
        )
        message = (
            "内置合同探针通过；没有接入真实外部方法。"
            if status == ExtensionStatus.PASS
            else "; ".join(blocking) or "合同探针未通过"
        )
        return ProbeOutcome(status=status, message=message, result_path=written, result=result)

    @staticmethod
    def _relative(project_dir: Path, path: Path) -> str:
        return str(path.relative_to(project_dir)).replace("\\", "/")

    def _finish_fresh_verification(
        self,
        *,
        manifest: ExtensionManifest,
        run_id: str,
        stage: str,
        actor: str,
        source_digest: str,
        candidate: CandidateIdentity,
        final_candidate: CandidateIdentity,
        started_at: str,
        started: float,
        status: ExtensionStatus,
        plan: PytestVerificationPlan | None,
        execution: CommandExecution | None,
        summary: PytestSummary | None,
        advisories: tuple[VerificationAdvisory, ...],
        blocking_findings: list[str],
    ) -> ProbeOutcome:
        run_dir = self.store.run_dir(run_id)
        result_path = run_dir / "result.json"
        junit_path = run_dir / "pytest.xml"
        summary_payload: dict[str, Any] = {
            "schema_version": 1,
            "run_id": run_id,
            "status": status.value,
            "plan": plan.to_dict() if plan is not None else None,
            "candidate_before": candidate.to_dict(),
            "candidate_after": final_candidate.to_dict(),
            "pytest_summary": summary.to_dict() if summary is not None else None,
            "advisories": [item.to_dict() for item in advisories],
            "blocking_findings": list(blocking_findings),
            "stdout_digest": execution.stdout_digest if execution is not None else "",
            "stderr_digest": execution.stderr_digest if execution is not None else "",
        }
        writes = []
        if junit_path.exists():
            writes.append(self._relative(self.project_dir, junit_path))
        finished_at = utc_now()
        result = ExtensionResult(
            schema_version=1,
            run_id=run_id,
            extension_id=manifest.id,
            extension_version=manifest.version,
            status=status,
            canonical_stage=stage,
            source_digest=source_digest,
            candidate=candidate,
            commands=[execution] if execution is not None else [],
            writes=writes,
            blocking_findings=list(blocking_findings),
            advisory_findings=list(advisories),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=(time.monotonic() - started) * 1000,
            process_tree_clean=(execution.process_tree_clean if execution is not None else True),
        )
        written_result = None
        try:
            self._guard_receipt(
                result_path, run_dir / "pytest-summary.json", self.store.history_path
            )
            written_summary = self.store.write_run_json(
                run_id, "pytest-summary.json", summary_payload
            )
            result.writes.extend(
                [
                    self._relative(self.project_dir, written_summary),
                    self._relative(self.project_dir, result_path),
                ]
            )
            written_result = self.store.write_result(result)
        except (OSError, ValueError) as exc:
            result.status = ExtensionStatus.BLOCKED
            result.writes = [
                item
                for item in result.writes
                if item != self._relative(self.project_dir, result_path)
            ]
            result.blocking_findings.append(f"验证已结束，但结果未落盘：{exc}")
            return ProbeOutcome(
                status=ExtensionStatus.BLOCKED,
                message="; ".join(result.blocking_findings),
                result=result,
                summary=summary,
                advisories=advisories,
                run_id=run_id,
                plan=plan,
                candidate_changed=final_candidate.candidate_digest != candidate.candidate_digest,
            )
        relative_result = self._relative(self.project_dir, written_result)
        event_type = (
            ExtensionEventType.COMPLETED
            if status in {ExtensionStatus.PASS, ExtensionStatus.FAIL}
            else ExtensionEventType.BLOCKED
        )
        try:
            self._event(
                event=event_type,
                run_id=run_id,
                extension_id=manifest.id,
                stage=stage,
                actor=actor,
                source_digest=source_digest,
                candidate_digest=candidate.candidate_digest,
                result_artifact=relative_result,
                message="; ".join(blocking_findings),
            )
        except (OSError, ValueError) as exc:
            status = result.status = ExtensionStatus.BLOCKED
            blocking_findings.append(f"结果已生成，但事件未落盘：{exc}")
            result.blocking_findings = list(blocking_findings)
            try:
                self.store.write_result(result)
            except (OSError, ValueError):
                written_result = None
        if status == ExtensionStatus.PASS and summary is not None:
            message = (
                f"完成前验证通过：测试 {summary.tests} 项，实际执行 {summary.executed} 项，"
                f"跳过 {summary.skipped} 项，失败 {summary.failures} 项。"
            )
            if advisories:
                message += (
                    f" 提醒：{advisories[0].occurrences} 项测试原本预计失败，" "但本次实际通过。"
                )
        elif status == ExtensionStatus.FAIL:
            message = "; ".join(blocking_findings) or "完成前验证未通过"
        else:
            message = "; ".join(blocking_findings) or "完成前验证已阻止"
        return ProbeOutcome(
            status=status,
            message=message,
            result_path=written_result,
            result=result,
            summary=summary,
            advisories=advisories,
            run_id=run_id,
            plan=plan,
            candidate_changed=final_candidate.candidate_digest != candidate.candidate_digest,
        )

    def _guard_receipt(self, *paths: Path) -> None:
        guard = PathGuard(
            self.project_dir,
            self._RECEIPT_WRITES,
            user_directories=self.user_directories,
        )
        for path in paths:
            decision = guard.check_write(path)
            if not decision.allowed:
                raise ValueError(decision.reason)

    def _blocked_fresh_receipt(
        self,
        *,
        run_id: str,
        candidate: CandidateIdentity,
        stage: str,
        actor: str,
        started_at: str,
        started: float,
        message: str,
        execution_uncertain: bool = False,
        plan: PytestVerificationPlan | None = None,
    ) -> ProbeOutcome:
        result = ExtensionResult(
            schema_version=1,
            run_id=run_id,
            extension_id=self.FRESH_VERIFICATION_ID,
            extension_version="",
            status=ExtensionStatus.BLOCKED,
            canonical_stage=stage,
            source_digest="",
            candidate=candidate,
            blocking_findings=[message],
            started_at=started_at,
            finished_at=utc_now(),
            duration_ms=(time.monotonic() - started) * 1000,
            process_tree_clean=not execution_uncertain,
        )
        written = None
        try:
            result_path = self.store.run_dir(run_id) / "result.json"
            self._guard_receipt(result_path, self.store.history_path)
            result.writes = [self._relative(self.project_dir, result_path)]
            written = self.store.write_result(result)
            self._event(
                event=ExtensionEventType.BLOCKED,
                run_id=run_id,
                extension_id=self.FRESH_VERIFICATION_ID,
                stage=stage,
                actor=actor,
                candidate_digest=candidate.candidate_digest,
                result_artifact=self._relative(self.project_dir, written),
                message=message,
            )
        except (OSError, ValueError) as exc:
            message += f"；阻断回执或事件未落盘：{exc}"
            result.blocking_findings.append(message)
            if written is None:
                result.writes = []
        return ProbeOutcome(
            status=ExtensionStatus.BLOCKED,
            message=message,
            result=result,
            result_path=written,
            run_id=run_id,
            plan=plan,
            candidate_changed=None if execution_uncertain else False,
        )

    def run_fresh_verification(
        self,
        *,
        stage: str = "delivery",
        actor: str = "cli",
        cancel_event: Event | None = None,
        on_start: Callable[[PytestVerificationPlan | None], None] | None = None,
    ) -> ProbeOutcome:
        if not self.enabled():
            return ProbeOutcome(
                status=ExtensionStatus.NOT_APPLICABLE,
                message="当前项目没有启用完成前验证，正在使用原有发布就绪流程。",
            )
        if self.FRESH_VERIFICATION_ID not in self.allowed_builtin_methods():
            return ProbeOutcome(
                status=ExtensionStatus.NOT_APPLICABLE,
                message="完成前验证不在允许的内置方法列表中。",
            )

        run_id = uuid.uuid4().hex
        started_at = utc_now()
        started = time.monotonic()
        candidate = build_candidate_identity(self.project_dir)
        try:
            plan = parse_pytest_verification_plan(self.config().get("fresh_verification"))
        except PytestPlanValidationError:
            plan = None
        if on_start is not None:
            on_start(plan)
        try:
            self._guard_receipt(
                self.store.run_dir(run_id) / "result.json",
                self.store.history_path,
            )
            outcome = self._execute_fresh_verification(
                run_id=run_id,
                candidate=candidate,
                started_at=started_at,
                started=started,
                stage=stage,
                actor=actor,
                cancel_event=cancel_event,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            return self._blocked_fresh_receipt(
                run_id=run_id,
                candidate=candidate,
                started_at=started_at,
                started=started,
                stage=stage,
                actor=actor,
                plan=plan,
                execution_uncertain=True,
                message=f"完成前验证无法形成完整证据，执行状态未确认：{exc}",
            )
        if outcome.result is None:
            return self._blocked_fresh_receipt(
                run_id=run_id,
                candidate=candidate,
                started_at=started_at,
                started=started,
                stage=stage,
                actor=actor,
                plan=plan,
                message=outcome.message,
            )
        return outcome

    def _execute_fresh_verification(
        self,
        *,
        run_id: str,
        candidate: CandidateIdentity,
        started_at: str,
        started: float,
        stage: str,
        actor: str,
        cancel_event: Event | None,
    ) -> ProbeOutcome:
        self._event(
            event=ExtensionEventType.REQUESTED,
            run_id=run_id,
            extension_id=self.FRESH_VERIFICATION_ID,
            stage=stage,
            actor=actor,
            candidate_digest=candidate.candidate_digest,
        )
        previous_result = self.store.latest_result(extension_id=self.FRESH_VERIFICATION_ID)
        if previous_result is not None and not candidate_matches(previous_result, candidate):
            self._event(
                event=ExtensionEventType.EVIDENCE_INVALIDATED,
                run_id=run_id,
                extension_id=self.FRESH_VERIFICATION_ID,
                stage=stage,
                actor=actor,
                candidate_digest=candidate.candidate_digest,
                message="当前代码版本已变化，上一份完成前验证结果失效。",
            )

        try:
            manifest = load_manifest(self.fresh_verification_manifest_path)
        except ManifestValidationError as exc:
            message = f"完成前验证内置清单无效: {exc}"
            self._event(
                event=ExtensionEventType.BLOCKED,
                run_id=run_id,
                extension_id=self.FRESH_VERIFICATION_ID,
                stage=stage,
                actor=actor,
                candidate_digest=candidate.candidate_digest,
                message=message,
            )
            return ProbeOutcome(ExtensionStatus.BLOCKED, message, run_id=run_id)

        source = self.verify_source(manifest)
        if not source.passed:
            message = "; ".join(source.errors)
            self._event(
                event=ExtensionEventType.BLOCKED,
                run_id=run_id,
                extension_id=manifest.id,
                stage=stage,
                actor=actor,
                source_digest=source.identity_digest,
                candidate_digest=candidate.candidate_digest,
                message=message,
            )
            return ProbeOutcome(ExtensionStatus.BLOCKED, message, run_id=run_id)
        if stage not in manifest.trigger.allowed_stages:
            message = f"完成前验证不适用于当前阶段: {stage}"
            return ProbeOutcome(ExtensionStatus.BLOCKED, message, run_id=run_id)

        decision = evaluate_ownership(
            manifest,
            trusted_capabilities={Capability.RUN_COMMANDS, Capability.WRITE_EVIDENCE},
        )
        if not decision.allowed:
            message = "; ".join(decision.findings)
            self._event(
                event=ExtensionEventType.BLOCKED,
                run_id=run_id,
                extension_id=manifest.id,
                stage=stage,
                actor=actor,
                source_digest=source.identity_digest,
                candidate_digest=candidate.candidate_digest,
                message=message,
            )
            return ProbeOutcome(ExtensionStatus.BLOCKED, message, run_id=run_id)

        run_dir = self.store.run_dir(run_id)
        targets = (
            run_dir / "result.json",
            run_dir / "pytest-summary.json",
            run_dir / "pytest.xml",
            run_dir / "pytest-temp",
            run_dir / "user-home",
            run_dir / "temp",
        )
        guard = PathGuard(
            self.project_dir,
            manifest.writes,
            user_directories=self.user_directories,
        )
        for target in targets:
            path_decision = guard.check_write(target)
            if not path_decision.allowed:
                self._event(
                    event=ExtensionEventType.BLOCKED,
                    run_id=run_id,
                    extension_id=manifest.id,
                    stage=stage,
                    actor=actor,
                    source_digest=source.identity_digest,
                    candidate_digest=candidate.candidate_digest,
                    message=path_decision.reason,
                )
                return ProbeOutcome(
                    ExtensionStatus.BLOCKED,
                    path_decision.reason,
                    run_id=run_id,
                )

        raw_plan = self.config().get("fresh_verification")
        try:
            plan = parse_pytest_verification_plan(raw_plan)
        except PytestPlanValidationError as exc:
            return self._finish_fresh_verification(
                manifest=manifest,
                run_id=run_id,
                stage=stage,
                actor=actor,
                source_digest=source.identity_digest,
                candidate=candidate,
                final_candidate=candidate,
                started_at=started_at,
                started=started,
                status=ExtensionStatus.BLOCKED,
                plan=None,
                execution=None,
                summary=None,
                advisories=(),
                blocking_findings=list(exc.errors),
            )

        pytest_spec = importlib.util.find_spec("pytest")
        pytest_origin = (
            Path(pytest_spec.origin).resolve() if pytest_spec and pytest_spec.origin else None
        )
        pytest_package_root = pytest_origin.parent.parent if pytest_origin is not None else None
        if pytest_package_root is None or not pytest_package_root.is_dir():
            return self._finish_fresh_verification(
                manifest=manifest,
                run_id=run_id,
                stage=stage,
                actor=actor,
                source_digest=source.identity_digest,
                candidate=candidate,
                final_candidate=candidate,
                started_at=started_at,
                started=started,
                status=ExtensionStatus.BLOCKED,
                plan=plan,
                execution=None,
                summary=None,
                advisories=(),
                blocking_findings=["当前 Python 环境没有可用的 pytest"],
            )

        pytest_temp = run_dir / "pytest-temp"
        isolated_home = run_dir / "user-home"
        isolated_temp = run_dir / "temp"
        for directory in (run_dir, pytest_temp, isolated_home, isolated_temp):
            directory.mkdir(parents=True, exist_ok=True)
        junit_path = run_dir / "pytest.xml"
        env = {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": os.pathsep.join(
                [str(Path(sysconfig.get_path("stdlib")).resolve()), str(pytest_package_root)]
            ),
            "HOME": str(isolated_home),
            "USERPROFILE": str(isolated_home),
            "XDG_CONFIG_HOME": str(isolated_home / ".config"),
            "XDG_CACHE_HOME": str(isolated_home / ".cache"),
            "XDG_DATA_HOME": str(isolated_home / ".local" / "share"),
            "APPDATA": str(isolated_home / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(isolated_home / "AppData" / "Local"),
            "TEMP": str(isolated_temp),
            "TMP": str(isolated_temp),
            "GIT_CEILING_DIRECTORIES": str(pytest_temp),
        }
        if os.name == "nt":
            home_drive, home_path = os.path.splitdrive(str(isolated_home))
            env["HOMEDRIVE"] = home_drive
            env["HOMEPATH"] = home_path or "\\"
        command = CommandSpec(
            executable=Path(sys.executable).resolve(),
            args=(
                "-m",
                "pytest",
                "-rX",
                f"--junitxml={junit_path}",
                f"--basetemp={pytest_temp}",
                "-p",
                "no:cacheprovider",
                *plan.args,
            ),
            cwd=self.project_dir,
            timeout_seconds=plan.timeout_seconds,
            env_allowlist=(
                "HOME",
                "USERPROFILE",
                "HOMEDRIVE",
                "HOMEPATH",
                "XDG_CONFIG_HOME",
                "XDG_CACHE_HOME",
                "XDG_DATA_HOME",
                "APPDATA",
                "LOCALAPPDATA",
                "PYTHONDONTWRITEBYTECODE",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                "PYTHONNOUSERSITE",
                "PYTHONPATH",
                "GIT_CEILING_DIRECTORIES",
            ),
            env=env,
            output_limit_bytes=4 * 1024 * 1024,
            cancel_event=cancel_event,
        )
        self._event(
            event=ExtensionEventType.STARTED,
            run_id=run_id,
            extension_id=manifest.id,
            stage=stage,
            actor=actor,
            source_digest=source.identity_digest,
            candidate_digest=candidate.candidate_digest,
        )
        execution = StructuredExecutor(project_dir=self.project_dir).run(command)
        try:
            adapter_result = self._call_builtin(
                manifest,
                {
                    "run_id": run_id,
                    "junit_path": junit_path,
                    "execution": execution,
                },
            )
            status = adapter_result.get("status")
            summary = adapter_result.get("summary")
            advisories = adapter_result.get("advisories", ())
            blocking = [str(item) for item in adapter_result.get("blocking_findings", [])]
            if not isinstance(status, ExtensionStatus):
                raise ValueError("内置完成前验证返回未知状态")
            if summary is not None and not isinstance(summary, PytestSummary):
                raise ValueError("内置完成前验证返回无效测试摘要")
            if not isinstance(advisories, tuple) or any(
                not isinstance(item, VerificationAdvisory) for item in advisories
            ):
                raise ValueError("内置完成前验证返回无效提醒")
        except Exception as exc:
            status = ExtensionStatus.BLOCKED
            summary = None
            advisories = ()
            blocking = [f"内置完成前验证失败: {exc}"]

        final_candidate = build_candidate_identity(self.project_dir)
        if final_candidate.candidate_digest != candidate.candidate_digest:
            status = ExtensionStatus.BLOCKED
            blocking.append("验证期间当前代码版本发生变化，请在修改结束后重新运行")
        return self._finish_fresh_verification(
            manifest=manifest,
            run_id=run_id,
            stage=stage,
            actor=actor,
            source_digest=source.identity_digest,
            candidate=candidate,
            final_candidate=final_candidate,
            started_at=started_at,
            started=started,
            status=status,
            plan=plan,
            execution=execution,
            summary=summary,
            advisories=advisories,
            blocking_findings=blocking,
        )

    def record_verification_metric(
        self,
        outcome: ProbeOutcome,
        *,
        legacy_would_pass: bool,
    ) -> Path | None:
        if outcome.result is None or not outcome.run_id:
            return None
        summary = outcome.summary
        payload: dict[str, Any] = {
            "schema_version": 1,
            "record_type": "verification-run",
            "recorded_at": utc_now(),
            "started_at": outcome.result.started_at,
            "run_id": outcome.run_id,
            "candidate_digest": outcome.result.candidate.candidate_digest,
            "junit_digest": summary.junit_digest if summary is not None else "",
            "tests": summary.tests if summary is not None else None,
            "executed": summary.executed if summary is not None else None,
            "skipped": summary.skipped if summary is not None else None,
            "failures": summary.failures if summary is not None else None,
            "errors": summary.errors if summary is not None else None,
            "non_strict_xpass": sum(item.occurrences for item in outcome.advisories),
            "legacy_would_pass": legacy_would_pass,
            "verification_status": outcome.status.value,
            "adjudication": "unreviewed",
            "prevented_false_completion": None,
            "false_block": None,
            "verification_duration_ms": outcome.result.duration_ms,
            "candidate_changed_during_run": any(
                "当前代码版本发生变化" in item for item in outcome.result.blocking_findings
            ),
            "time_to_accepted_ms": None,
        }
        metric_path = self.store.verification_metrics_path
        self._guard_receipt(metric_path, self.store.verification_summary_path)
        metric_path = cast(Path, self.store.append_verification_metric(payload))
        replay_contract_path = (
            self.project_dir
            / ".super-dev"
            / "changes"
            / "completion-verification"
            / "replay-scenarios.yaml"
        )
        metric_summary = summarize_verification_metrics(
            metric_path,
            replay_contract_path if replay_contract_path.exists() else None,
            current_candidate_digest=build_candidate_identity(self.project_dir).candidate_digest,
        )
        self.store.write_verification_summary(metric_summary.to_dict())
        return metric_path
