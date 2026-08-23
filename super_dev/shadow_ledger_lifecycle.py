"""Safe, idempotent lifecycle for automatically created shadow change ledgers."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .change_ledger import ChangeLedger, ChangeLedgerError, StageStatus
from .scope_advisory import build_scope_advisory
from .shadow_ledger_store import ShadowLedgerReadError, load_shadow_ledger
from .workflow_contract import CANONICAL_NINE_STAGE_IDS

ShadowLedgerCreationStatus = Literal[
    "disabled",
    "created",
    "existing",
    "missing_change",
    "unsafe_path",
    "invalid_existing",
    "write_failed",
]

_CHANGE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ShadowLedgerCreationResult:
    status: ShadowLedgerCreationStatus
    change_id: str
    ledger_path: str = ""
    read_only: bool = True
    control_authority: str = "none"
    scope_advisory_created: bool = False
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status in {"created", "existing", "disabled"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "change_id": self.change_id,
            "ledger_path": self.ledger_path,
            "read_only": self.read_only,
            "control_authority": self.control_authority,
            "scope_advisory_created": self.scope_advisory_created,
            "succeeded": self.succeeded,
            "error": self.error,
        }


def adaptive_ledger_auto_create_enabled(config: Any) -> bool:
    payload = getattr(config, "adaptive_ledger", {})
    return (
        isinstance(payload, dict)
        and payload.get("enabled") is True
        and payload.get("auto_create") is True
    )


def adaptive_ledger_scope_advisory_enabled(config: Any) -> bool:
    payload = getattr(config, "adaptive_ledger", {})
    return (
        adaptive_ledger_auto_create_enabled(config)
        and isinstance(payload, dict)
        and payload.get("scope_advisory") is True
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _display_path(project_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(project_dir).as_posix()
    except ValueError:
        return str(path)


def _existing_result(project_dir: Path, change_id: str, ledger_path: Path) -> ShadowLedgerCreationResult:
    display_path = _display_path(project_dir, ledger_path)
    try:
        record = load_shadow_ledger(project_dir, ledger_path)
    except ShadowLedgerReadError as exc:
        return ShadowLedgerCreationResult(
            status="invalid_existing",
            change_id=change_id,
            ledger_path=display_path,
            error=str(exc),
        )
    if record.ledger.change_id != change_id:
        return ShadowLedgerCreationResult(
            status="invalid_existing",
            change_id=change_id,
            ledger_path=display_path,
            error="Existing ledger change_id does not match its directory",
        )
    return ShadowLedgerCreationResult(
        status="existing",
        change_id=change_id,
        ledger_path=display_path,
        scope_advisory_created=record.ledger.scope_advisory is not None,
    )


def _write_exclusive_fallback(ledger_path: Path, serialized: str) -> None:
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(
            ledger_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        created = True
        with os.fdopen(descriptor, mode="w", encoding="utf-8", newline="\n") as handle:
            descriptor = None
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                ledger_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def ensure_shadow_change_ledger(
    project_dir: Path,
    *,
    change_id: str,
    harness_version: str,
    intent: str,
    governance_depth: str,
    work_mode: str,
    enabled: bool,
    satisfied_stages: set[str] | None = None,
    scope_advisory_enabled: bool = False,
    changed_surfaces: set[str] | None = None,
    scope_complete: bool = False,
) -> ShadowLedgerCreationResult:
    """Create one shadow ledger without overwriting or controlling the workflow."""

    project_dir = Path(project_dir).resolve()
    if enabled is not True:
        return ShadowLedgerCreationResult(status="disabled", change_id=change_id)
    if not _CHANGE_ID_PATTERN.fullmatch(str(change_id)):
        return ShadowLedgerCreationResult(
            status="unsafe_path",
            change_id=str(change_id),
            error="change_id contains unsupported path characters",
        )

    try:
        changes_root = (project_dir / ".super-dev" / "changes").resolve()
    except OSError as exc:
        return ShadowLedgerCreationResult(
            status="write_failed",
            change_id=change_id,
            error=f"Changes root cannot be inspected: {exc}",
        )
    if not _is_within(changes_root, project_dir):
        return ShadowLedgerCreationResult(
            status="unsafe_path",
            change_id=change_id,
            error="Changes root escapes the project directory",
        )
    try:
        change_dir = (changes_root / change_id).resolve()
    except OSError as exc:
        return ShadowLedgerCreationResult(
            status="write_failed",
            change_id=change_id,
            error=f"Change directory cannot be inspected: {exc}",
        )
    if not _is_within(change_dir, changes_root):
        return ShadowLedgerCreationResult(
            status="unsafe_path",
            change_id=change_id,
            error="Change directory escapes the changes root",
        )
    try:
        change_exists = change_dir.is_dir()
    except OSError as exc:
        return ShadowLedgerCreationResult(
            status="write_failed",
            change_id=change_id,
            error=f"Change directory cannot be inspected: {exc}",
        )
    if not change_exists:
        return ShadowLedgerCreationResult(
            status="missing_change",
            change_id=change_id,
            error="Change directory must exist before shadow ledger creation",
        )

    ledger_path = change_dir / "ledger.json"
    try:
        ledger_exists = ledger_path.exists()
    except OSError as exc:
        return ShadowLedgerCreationResult(
            status="write_failed",
            change_id=change_id,
            ledger_path=_display_path(project_dir, ledger_path),
            error=f"Ledger path cannot be inspected: {exc}",
        )
    if ledger_exists:
        return _existing_result(project_dir, change_id, ledger_path)

    satisfied = set(satisfied_stages or set())
    unknown_stages = satisfied - set(CANONICAL_NINE_STAGE_IDS)
    if unknown_stages:
        return ShadowLedgerCreationResult(
            status="write_failed",
            change_id=change_id,
            ledger_path=_display_path(project_dir, ledger_path),
            error=f"Unknown satisfied stages: {sorted(unknown_stages)}",
        )
    try:
        ledger = ChangeLedger.create(
            change_id=change_id,
            harness_version=harness_version,
            intent=intent,
            governance_depth=governance_depth,
            work_mode=work_mode,
        )
        for stage in satisfied:
            ledger.get_stage(stage).status = StageStatus.SATISFIED
        if scope_advisory_enabled is True:
            ledger.scope_advisory = build_scope_advisory(
                changed_surfaces=changed_surfaces or set(),
                work_mode=work_mode,
                governance_depth=governance_depth,
                scope_complete=scope_complete,
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
        serialized = json.dumps(ledger.to_dict(), ensure_ascii=False, indent=2) + "\n"
    except (ChangeLedgerError, KeyError, TypeError, ValueError) as exc:
        return ShadowLedgerCreationResult(
            status="write_failed",
            change_id=change_id,
            ledger_path=_display_path(project_dir, ledger_path),
            error=str(exc),
        )

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=change_dir,
            prefix=".ledger-",
            suffix=".tmp",
            delete=False,
            newline="\n",
        ) as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        try:
            os.link(temp_path, ledger_path)
        except FileExistsError:
            return _existing_result(project_dir, change_id, ledger_path)
        except OSError:
            _write_exclusive_fallback(ledger_path, serialized)
    except FileExistsError:
        return _existing_result(project_dir, change_id, ledger_path)
    except OSError as exc:
        return ShadowLedgerCreationResult(
            status="write_failed",
            change_id=change_id,
            ledger_path=_display_path(project_dir, ledger_path),
            error=f"Shadow ledger could not be written: {exc}",
        )
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    return ShadowLedgerCreationResult(
        status="created",
        change_id=change_id,
        ledger_path=_display_path(project_dir, ledger_path),
        scope_advisory_created=ledger.scope_advisory is not None,
    )


__all__ = [
    "ShadowLedgerCreationResult",
    "ShadowLedgerCreationStatus",
    "adaptive_ledger_auto_create_enabled",
    "adaptive_ledger_scope_advisory_enabled",
    "ensure_shadow_change_ledger",
]
