"""Read-only discovery and summaries for shadow adaptive change ledgers."""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path
from typing import Any

from .change_ledger import ChangeLedger, ChangeLedgerError, StageResolution, StageStatus

MAX_LEDGER_BYTES = 1_000_000
MAX_LEDGER_FILES = 100


class ShadowLedgerReadError(ValueError):
    """Raised when a ledger path or payload cannot be read safely."""


@dataclass(frozen=True)
class ShadowLedgerRecord:
    path: Path
    ledger: ChangeLedger
    modified_at: float


@dataclass
class ShadowLedgerSummary:
    present: bool = False
    read_only: bool = True
    control_authority: str = "none"
    valid_count: int = 0
    invalid_count: int = 0
    discovery_truncated: bool = False
    active_change_id: str = ""
    governance_depth: str = ""
    intent: str = ""
    ledger_path: str = ""
    resolution_counts: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    summary: str = "未检测到影子九阶段账本"

    def to_dict(self) -> dict[str, Any]:
        return {
            "present": self.present,
            "read_only": self.read_only,
            "control_authority": self.control_authority,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "discovery_truncated": self.discovery_truncated,
            "active_change_id": self.active_change_id,
            "governance_depth": self.governance_depth,
            "intent": self.intent,
            "ledger_path": self.ledger_path,
            "resolution_counts": dict(self.resolution_counts),
            "status_counts": dict(self.status_counts),
            "errors": list(self.errors),
            "summary": self.summary,
        }


def _changes_root(project_dir: Path) -> Path:
    return Path(project_dir).resolve() / ".super-dev" / "changes"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _discover_shadow_ledger_paths(project_dir: Path) -> tuple[list[Path], bool]:
    root = _changes_root(project_dir)
    if not root.exists():
        return [], False
    paths: list[Path] = []
    try:
        discovered = list(islice(root.iterdir(), MAX_LEDGER_FILES + 1))
    except OSError:
        return [], False
    truncated = len(discovered) > MAX_LEDGER_FILES
    for change_dir in sorted(discovered[:MAX_LEDGER_FILES], key=lambda item: item.name):
        try:
            if not change_dir.is_dir():
                continue
            candidate = (change_dir / "ledger.json").resolve()
            if _is_within(candidate, root) and candidate.is_file():
                paths.append(candidate)
        except OSError:
            continue
    return paths, truncated


def list_shadow_ledger_paths(project_dir: Path) -> list[Path]:
    paths, _truncated = _discover_shadow_ledger_paths(project_dir)
    return paths


def load_shadow_ledger(project_dir: Path, path: Path) -> ShadowLedgerRecord:
    root = _changes_root(project_dir)
    candidate = Path(path).resolve()
    if candidate.name != "ledger.json" or not _is_within(candidate, root):
        raise ShadowLedgerReadError("Ledger path escapes the project changes root")
    try:
        with candidate.open("rb") as handle:
            file_stat = os.fstat(handle.fileno())
            raw_payload = handle.read(MAX_LEDGER_BYTES + 1)
        if len(raw_payload) > MAX_LEDGER_BYTES:
            raise ShadowLedgerReadError("Ledger file exceeds the read-only size limit")
        payload = json.loads(raw_payload.decode("utf-8"))
    except ShadowLedgerReadError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ShadowLedgerReadError("Ledger JSON cannot be read") from exc
    if not isinstance(payload, dict):
        raise ShadowLedgerReadError("Ledger payload must be a JSON object")
    try:
        ledger = ChangeLedger.from_dict(payload)
    except (ChangeLedgerError, KeyError, TypeError, ValueError) as exc:
        raise ShadowLedgerReadError(str(exc)) from exc
    return ShadowLedgerRecord(
        path=candidate,
        ledger=ledger,
        modified_at=file_stat.st_mtime,
    )


def _relative_display_path(project_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(Path(project_dir).resolve()).as_posix()
    except ValueError:
        return str(path)


def build_shadow_ledger_summary(project_dir: Path) -> dict[str, Any]:
    project_dir = Path(project_dir).resolve()
    records: list[ShadowLedgerRecord] = []
    errors: list[dict[str, str]] = []
    paths, discovery_truncated = _discover_shadow_ledger_paths(project_dir)
    for path in paths:
        try:
            records.append(load_shadow_ledger(project_dir, path))
        except ShadowLedgerReadError as exc:
            errors.append(
                {
                    "path": _relative_display_path(project_dir, path),
                    "error": str(exc),
                }
            )

    summary = ShadowLedgerSummary(
        present=bool(records or errors or discovery_truncated),
        valid_count=len(records),
        invalid_count=len(errors),
        discovery_truncated=discovery_truncated,
        errors=errors,
    )
    if discovery_truncated:
        summary.summary = (
            f"只读观察不完整：目录条目超过上限{MAX_LEDGER_FILES}；未选择当前账本"
        )
        return summary.to_dict()
    if not records:
        if errors:
            summary.summary = f"只读观察不可用：{len(errors)}个账本未通过校验"
        return summary.to_dict()

    active = max(records, key=lambda item: (item.modified_at, item.path.as_posix()))
    resolution_counts = Counter(entry.resolution.value for entry in active.ledger.stages)
    status_counts = Counter(entry.status.value for entry in active.ledger.stages)
    summary.active_change_id = active.ledger.change_id
    summary.governance_depth = active.ledger.governance_depth
    summary.intent = active.ledger.intent.value
    summary.ledger_path = _relative_display_path(project_dir, active.path)
    summary.resolution_counts = dict(sorted(resolution_counts.items()))
    summary.status_counts = dict(sorted(status_counts.items()))
    summary.summary = (
        f"只读观察 {summary.active_change_id}："
        f"执行{resolution_counts[StageResolution.EXECUTE.value]}、"
        f"复用{resolution_counts[StageResolution.REUSE.value]}、"
        f"不适用{resolution_counts[StageResolution.NOT_APPLICABLE.value]}、"
        f"门禁必需{resolution_counts[StageResolution.REQUIRE.value]}、"
        f"门禁免除{resolution_counts[StageResolution.WAIVE.value]}、"
        f"失效{status_counts[StageStatus.INVALIDATED.value]}"
    )
    return summary.to_dict()


__all__ = [
    "MAX_LEDGER_BYTES",
    "MAX_LEDGER_FILES",
    "ShadowLedgerReadError",
    "ShadowLedgerRecord",
    "ShadowLedgerSummary",
    "build_shadow_ledger_summary",
    "list_shadow_ledger_paths",
    "load_shadow_ledger",
]
