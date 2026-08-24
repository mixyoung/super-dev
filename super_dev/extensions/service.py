"""最小扩展平台的 Core 服务入口。"""

from __future__ import annotations

import importlib
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import get_config_manager
from ..user_directories import UserDirectoryContext
from .evidence import EvidenceStore, build_candidate_identity, candidate_matches, utc_now
from .manifest import ManifestValidationError, load_manifest
from .models import (
    Capability,
    ExtensionEvent,
    ExtensionEventType,
    ExtensionManifest,
    ExtensionResult,
    ExtensionStatus,
)
from .ownership import evaluate_ownership
from .path_guard import PathGuard
from .source_lock import SourceLockVerifier, SourceVerification


@dataclass(frozen=True)
class ProbeOutcome:
    status: ExtensionStatus
    message: str
    result_path: Path | None = None
    result: ExtensionResult | None = None


class ExtensionService:
    BUILTIN_ID = "contract-probe"

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
        return load_manifest(manifest_path)

    def source_verifier(self, manifest: ExtensionManifest) -> SourceLockVerifier:
        if manifest.manifest_path and manifest.manifest_path == self.builtin_manifest_path.resolve():
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
                message="当前候选已变化，上一份扩展结果失效。",
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
            advisory = [str(item) for item in adapter_result.get("advisory_findings", [])]
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
