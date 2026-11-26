"""Project-only snapshot for the opt-in DeepSeek Harness companion plugin."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
import threading
from pathlib import Path
from typing import Any

from ..artifact_utils import normalize_work_item_id, work_item_identity_from_snapshot
from ..skills.skill_template import SkillTemplate
from ..state_store import STATE_STORE_SCHEMA_VERSION, StateStore
from ..user_directories import ensure_plain_path
from ..workflow_stage_truth import (
    CANONICAL_WORKFLOW_STAGE_CHAIN,
    SEEAI_WORKFLOW_STAGE_CHAIN,
    canonical_stage_for_engine_phase,
)
from .manager import IntegrationManager

HOST = "deepseek-harness"
SCHEMA = 1
MAX_FILE_BYTES = 1024 * 1024
# Independent bound for the Windows venv interpreter even if its launcher is cancelled.
WORKER_LIMIT_SECONDS = 5.0


def _workflow(state: str, **fields: Any) -> dict[str, Any]:
    return {
        "state": state,
        "flow": "",
        "stage": "",
        "work_item": "",
        "revision": 0,
        "next": "",
        **fields,
    }


def _result(reason: str = "") -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "outcome": "blocked" if reason else "observed",
        "reason": reason,
        "checks": dict.fromkeys(("standard", "seeai", "rules"), "unchecked"),
        "workflow": _workflow("unchecked"),
    }


def _local_project(path: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts or path == Path(path.anchor):
        raise ValueError("not a project directory")
    if os.name == "nt" and not re.fullmatch(r"[A-Za-z]:", path.drive):
        raise ValueError("not a local Windows drive")
    ensure_plain_path(path)
    if not path.is_dir():
        raise ValueError("not a directory")
    return path


def _read_file(path: Path) -> bytes | None:
    """Read the one preselected file; refuse links, device files and oversized input."""
    ensure_plain_path(path)
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
        raise ValueError("unsupported file")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(before, opened):
            raise ValueError("file changed before read")
        data = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(data) != before.st_size or after.st_mtime_ns != before.st_mtime_ns:
        raise ValueError("file changed during read")
    return data


def _checks(project: Path, name: str) -> str:
    try:
        path = project / ".dsh" / "skills" / name / "SKILL.md"
        actual = _read_file(path)
        if actual is None:
            return "missing"
        expected = SkillTemplate.for_builtin(name, HOST).render(HOST).encode("utf-8")
        return "valid" if actual == expected else "modified"
    except (OSError, ValueError):
        return "unreadable"


def _rules(project: Path) -> str:
    path = project / "AGENTS.local.md"
    try:
        data = _read_file(path)
        if data is None:
            return "missing"
        missing = IntegrationManager.audit_surface_contract(
            HOST, "project:AGENTS.local.md", path, data.decode("utf-8")
        )
    except (OSError, ValueError):
        return "unreadable"
    return "modified" if missing else "valid"


def _committed_workflow(project: Path) -> dict[str, Any]:
    store = StateStore(project)
    try:
        raw = _read_file(store.workflow_path)
        if raw is None:
            # Observe presence only. Never load or select a historical snapshot.
            ensure_plain_path(store.history_dir)
            return _workflow("invalid" if store.history_dir.exists() else "not_started")
        payload = json.loads(raw)
        version = payload.get("state_store_schema_version") if isinstance(payload, dict) else None
        if type(version) is not int or version != STATE_STORE_SCHEMA_VERSION:
            return _workflow("invalid")
        revision = payload.get("revision")
        flow = payload.get("flow_variant", "standard")
        stage = payload.get("current_stage")
        if type(revision) is not int or not 0 < revision < 2**53:
            return _workflow("invalid")
        if flow not in ("standard", "seeai") or not isinstance(stage, str):
            return _workflow("invalid")
        stage = canonical_stage_for_engine_phase(stage)
        stages = SEEAI_WORKFLOW_STAGE_CHAIN if flow == "seeai" else CANONICAL_WORKFLOW_STAGE_CHAIN
        if stage not in stages:
            return _workflow("invalid")
        raw_active = payload.get("active_change_id", payload.get("change_id", ""))
        active = normalize_work_item_id(raw_active)
        recorded = normalize_work_item_id(payload.get("work_item_id", ""))
        if raw_active not in (None, "") and not active:
            return _workflow("invalid")
        if active:
            if recorded and recorded != active:
                return _workflow("invalid")
            ensure_plain_path(project / ".super-dev" / "changes" / active)
        identity = work_item_identity_from_snapshot(project, payload)
        if not identity.valid or (active and identity.active_change_id != active):
            return _workflow("invalid")
        # SEEAI deliberately uses the Core legacy change binding; it can also
        # have a recorded item during document drafting before a change exists.
        item = identity.work_item_id or (recorded if flow == "seeai" else "")
        if not item:
            return _workflow("invalid")
    except (OSError, ValueError, RuntimeError):
        return _workflow("invalid")

    next_step = {
        "docs_confirm": "review_documents",
        "preview_confirm": "review_preview",
    }.get(stage, "continue_existing")
    if payload.get("status") in ("completed", "cancelled", "aborted", "delivered"):
        next_step = ""
    return _workflow(
        "recorded", flow=flow, stage=stage, work_item=item, revision=revision, next=next_step
    )


def collect_snapshot(project: Path) -> dict[str, Any]:
    try:
        project = _local_project(project)
    except (OSError, ValueError):
        return _result("workspace")

    result = _result()
    result["checks"]["standard"] = _checks(project, "super-dev")
    result["checks"]["seeai"] = _checks(project, "super-dev-seeai")
    result["workflow"] = _committed_workflow(project)
    if (
        result["checks"]["standard"] == result["checks"]["seeai"] == "missing"
        and result["workflow"]["state"] == "not_started"
    ):
        result.update(outcome="blocked", reason="not_setup")
    else:
        result["checks"]["rules"] = _rules(project)
    return result


def main() -> int:
    # Only this worker owns its deadline; the library API never exits the host.
    deadline = threading.Timer(WORKER_LIMIT_SECONDS, os._exit, args=(124,))
    deadline.daemon = True
    deadline.start()
    try:
        result = collect_snapshot(Path(sys.argv[1])) if len(sys.argv) == 2 else _result("workspace")
        print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
        return 0
    finally:
        deadline.cancel()


if __name__ == "__main__":
    raise SystemExit(main())
