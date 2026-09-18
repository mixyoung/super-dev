"""Authoritative local workflow-state persistence for Super Dev 2.6.

Requirement traceability: STATE-002 owns revision conflicts and atomic commits.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .atomic_io import atomic_write_text

STATE_STORE_SCHEMA_VERSION = 1


class StateStoreError(RuntimeError):
    """Base class for authoritative state persistence failures."""


class StateConflictError(StateStoreError):
    """Raised when a caller tries to overwrite a newer state revision."""


class StateLockTimeoutError(StateStoreError):
    """Raised when the project state lock cannot be acquired in time."""


class PipelineStateMigrationError(StateStoreError):
    """Raised when the retired pipeline-state file cannot be migrated safely."""


@dataclass(frozen=True)
class CommitResult:
    path: Path
    revision: int
    payload: dict[str, Any]
    migration_receipt: Path | None = None


class _ProjectStateLock:
    def __init__(self, path: Path, *, timeout_seconds: float) -> None:
        self.path = path
        self.timeout_seconds = max(0.0, float(timeout_seconds))
        self._stream: Any = None

    def __enter__(self) -> _ProjectStateLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a+b")
        self._stream.seek(0, os.SEEK_END)
        if self._stream.tell() == 0:
            self._stream.write(b"\0")
            self._stream.flush()
            os.fsync(self._stream.fileno())
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self._lock_once()
                return self
            except OSError as exc:
                if time.monotonic() >= deadline:
                    self._stream.close()
                    self._stream = None
                    raise StateLockTimeoutError(
                        f"state lock timed out after {self.timeout_seconds:.2f}s: {self.path}"
                    ) from exc
                time.sleep(0.05)

    def _lock_once(self) -> None:
        assert self._stream is not None
        self._stream.seek(0)
        if os.name == "nt":
            msvcrt: Any = importlib.import_module("msvcrt")

            msvcrt.locking(self._stream.fileno(), msvcrt.LK_NBLCK, 1)
            return
        fcntl: Any = importlib.import_module("fcntl")

        fcntl.flock(self._stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._stream is None:
            return
        try:
            self._stream.seek(0)
            if os.name == "nt":
                msvcrt: Any = importlib.import_module("msvcrt")

                msvcrt.locking(self._stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl: Any = importlib.import_module("fcntl")

                fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
        finally:
            self._stream.close()
            self._stream = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _stamp(value: str) -> str:
    return value.replace(":", "").replace("-", "").replace(".", "")


class StateStore:
    """Own workflow-state commits, history, audit events, and legacy migration."""

    def __init__(self, project_dir: Path, *, lock_timeout_seconds: float = 5.0) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.state_dir = self.project_dir / ".super-dev"
        self.workflow_path = self.state_dir / "workflow-state.json"
        self.history_dir = self.state_dir / "workflow-history"
        self.latest_path = self.history_dir / "latest.json"
        self.event_path = self.state_dir / "workflow-events.jsonl"
        self.session_brief_path = self.state_dir / "SESSION_BRIEF.md"
        self.lock_path = self.state_dir / "state.lock"
        self.legacy_pipeline_path = self.state_dir / "pipeline-state.json"
        self.lock_timeout_seconds = lock_timeout_seconds

    def load_workflow(self) -> dict[str, Any]:
        return _read_json(self.workflow_path) or _read_json(self.latest_path) or {}

    def session_brief_health(self, *, repair: bool = False) -> dict[str, Any]:
        state = self.load_workflow()
        if not self.session_brief_path.is_file():
            return {"status": "missing", "current": False}
        try:
            lines = self.session_brief_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            return {"status": "unreadable", "current": False}
        fields: dict[str, str] = {}
        for line in lines:
            if line.startswith("- 来源工作项:"):
                fields["work_item_id"] = line.partition(":")[2].strip()
            elif line.startswith("- 状态修订:"):
                fields["revision"] = line.partition(":")[2].strip()
        expected_work_item = str(state.get("work_item_id", "")).strip() or "-"
        expected_revision = str(int(state.get("revision", 0) or 0))
        current = (
            fields.get("work_item_id") == expected_work_item
            and fields.get("revision") == expected_revision
        )
        result = {
            "status": "current" if current else "stale",
            "current": current,
            "expected_work_item_id": expected_work_item,
            "expected_revision": int(expected_revision),
            "observed_work_item_id": fields.get("work_item_id", ""),
            "observed_revision": fields.get("revision", ""),
        }
        if not current and repair and state:
            try:
                self._refresh_session_brief(state)
            except OSError as exc:
                return {**result, "status": "repair_failed", "repair_error": str(exc)}
            return {
                **result,
                "status": "repaired",
                "current": True,
                "observed_work_item_id": expected_work_item,
                "observed_revision": expected_revision,
            }
        return result

    def commit_workflow(
        self,
        payload: dict[str, Any],
        *,
        expected_revision: int | None = None,
        event: str = "workflow_state_saved",
    ) -> CommitResult:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with _ProjectStateLock(self.lock_path, timeout_seconds=self.lock_timeout_seconds):
            current = _read_json(self.workflow_path) or _read_json(self.latest_path) or {}
            current_revision = int(current.get("revision", 0) or 0)
            supplied_revision = payload.get("revision")
            expected = expected_revision
            if expected is None and isinstance(supplied_revision, int):
                expected = supplied_revision
            if expected is not None and int(expected) != current_revision:
                raise StateConflictError(
                    f"expected revision {int(expected)}, current revision {current_revision}"
                )

            normalized = dict(payload)
            migration = self._prepare_pipeline_state_migration(normalized)
            revision = current_revision + 1
            updated_at = _utc_now()
            normalized["state_store_schema_version"] = STATE_STORE_SCHEMA_VERSION
            normalized["revision"] = revision
            normalized["updated_at"] = updated_at
            serialized = json.dumps(normalized, ensure_ascii=False, indent=2) + "\n"

            self.history_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = self.history_dir / (
                f"workflow-state-r{revision:08d}-{_stamp(updated_at)}.json"
            )
            atomic_write_text(snapshot_path, serialized)
            atomic_write_text(self.latest_path, serialized)
            atomic_write_text(self.workflow_path, serialized)
            self._append_event(event=event, payload=normalized, source_path=self.workflow_path)
            try:
                self._refresh_session_brief(normalized)
            except OSError:
                self._append_event(
                    event="session_brief_refresh_failed",
                    payload=normalized,
                    source_path=self.session_brief_path,
                )

            receipt_path = self._finish_pipeline_state_migration(
                migration,
                target_revision=revision,
                updated_at=updated_at,
            )
            return CommitResult(
                path=self.workflow_path,
                revision=revision,
                payload=normalized,
                migration_receipt=receipt_path,
            )

    def _refresh_session_brief(self, payload: dict[str, Any]) -> None:
        work_item_id = str(payload.get("work_item_id", "")).strip() or "-"
        revision = int(payload.get("revision", 0) or 0)
        status = str(payload.get("status", "")).strip() or "-"
        step = str(payload.get("current_step_label", "")).strip() or status
        next_action = str(payload.get("recommended_command", "")).strip() or "-"
        reason = str(payload.get("reason", "")).strip()
        evidence = str(payload.get("evidence", "")).strip()
        lines = [
            "# Super Dev Session Brief",
            "",
            f"- 来源工作项: {work_item_id}",
            f"- 状态修订: {revision}",
            f"- 当前步骤: {step}",
            f"- 当前状态: {status}",
            f"- 下一步: {next_action}",
            "- 流程状态卡: .super-dev/SESSION_BRIEF.md",
            "- 工作流状态: .super-dev/workflow-state.json",
            "- 状态事件: .super-dev/workflow-events.jsonl",
            "- Hook 审计日志: .super-dev/hook-history.jsonl",
        ]
        if reason:
            lines.append(f"- 原因: {reason}")
        if evidence:
            lines.append(f"- 依据: {evidence}")
        lines.extend(
            [
                "",
                "## 运行验证摘要",
                "- 详细结果以 output/ 中的最新验证报告为准。",
                "",
                "## 最近 Hook 事件",
                "- 详细记录见 `.super-dev/hook-history.jsonl`。",
                "",
                "## 最近关键时间线",
                "- 当前状态与时间线以 `.super-dev/workflow-state.json` 和事件日志为准。",
                "",
                "该文件根据 `.super-dev/workflow-state.json` 自动生成，不是独立状态源。",
                "",
            ]
        )
        atomic_write_text(self.session_brief_path, "\n".join(lines))

    def _append_event(
        self,
        *,
        event: str,
        payload: dict[str, Any],
        source_path: Path,
    ) -> None:
        record = {
            "timestamp": str(payload.get("updated_at", "")).strip() or _utc_now(),
            "event": event,
            "revision": int(payload.get("revision", 0) or 0),
            "work_item_id": str(payload.get("work_item_id", "")).strip(),
            "status": str(payload.get("status", "")).strip(),
            "current_step_label": str(payload.get("current_step_label", "")).strip(),
            "source_path": str(source_path),
        }
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _prepare_pipeline_state_migration(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.legacy_pipeline_path.exists():
            return None
        try:
            raw = self.legacy_pipeline_path.read_bytes()
            legacy = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PipelineStateMigrationError(
                f"legacy pipeline state is invalid: {self.legacy_pipeline_path}"
            ) from exc
        if not isinstance(legacy, dict):
            raise PipelineStateMigrationError("legacy pipeline state must be a JSON object")

        keys = (
            "current_phase",
            "canonical_phase",
            "phase_index",
            "total_phases",
            "phases_completed",
            "phases_remaining",
            "canonical_phases_completed",
            "canonical_phases_remaining",
            "active_experts",
            "started_at",
            "last_updated",
        )
        engine_progress = {key: legacy[key] for key in keys if key in legacy}
        migrated_fields: list[str] = []
        if engine_progress and not isinstance(payload.get("engine_progress"), dict):
            payload["engine_progress"] = engine_progress
            migrated_fields.append("engine_progress")
        canonical = str(legacy.get("canonical_phase", "")).strip()
        if canonical and not str(payload.get("current_stage", "")).strip():
            payload["current_stage"] = canonical
            migrated_fields.append("current_stage")
        return {
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "source_size": len(raw),
            "migrated_fields": migrated_fields,
            "ignored_fields": sorted(set(legacy) - set(keys)),
        }

    def _finish_pipeline_state_migration(
        self,
        migration: dict[str, Any] | None,
        *,
        target_revision: int,
        updated_at: str,
    ) -> Path | None:
        if migration is None:
            return None
        receipt = {
            "schema_version": 1,
            "status": "prepared",
            "source_path": ".super-dev/pipeline-state.json",
            **migration,
            "target_path": ".super-dev/workflow-state.json",
            "target_revision": target_revision,
            "migrated_at": updated_at,
            "legacy_file_removed": False,
        }
        receipt_path = self.history_dir / f"pipeline-state-migration-{_stamp(updated_at)}.json"
        atomic_write_text(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        try:
            self.legacy_pipeline_path.unlink()
        except OSError as exc:
            receipt["status"] = "state_committed_cleanup_blocked"
            receipt["cleanup_error"] = str(exc)
            atomic_write_text(
                receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
            )
            raise PipelineStateMigrationError(
                "workflow state committed but legacy pipeline-state cleanup was blocked"
            ) from exc
        receipt["status"] = "migrated"
        receipt["legacy_file_removed"] = True
        atomic_write_text(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        return receipt_path


__all__ = [
    "CommitResult",
    "PipelineStateMigrationError",
    "STATE_STORE_SCHEMA_VERSION",
    "StateConflictError",
    "StateLockTimeoutError",
    "StateStore",
    "StateStoreError",
]
