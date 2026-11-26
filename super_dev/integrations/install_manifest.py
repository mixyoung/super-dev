"""Host integration install manifest helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def install_manifest_path(project_dir: Path) -> Path:
    return project_dir / ".super-dev" / "install-manifest.json"


def load_install_manifest(project_dir: Path) -> dict[str, Any]:
    file_path = install_manifest_path(project_dir)
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
        **payload,
        "version": int(payload.get("version", 1) or 1),
        "targets": targets,
        "updated_at": str(payload.get("updated_at", "")).strip(),
    }


def save_install_manifest(project_dir: Path, payload: dict[str, Any]) -> Path:
    from .managed_content import atomic_write

    normalized = load_install_manifest(project_dir)
    normalized.update(payload)
    normalized["version"] = int(normalized.get("version", 1) or 1)
    normalized["updated_at"] = _utc_now()
    file_path = install_manifest_path(project_dir)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(
        file_path,
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
    )
    return file_path


def record_install_manifest(
    project_dir: Path,
    *,
    host: str,
    family: str,
    scopes: dict[str, bool],
    paths: list[str],
) -> Path:
    payload = load_install_manifest(project_dir)
    targets = payload.get("targets", {})
    if not isinstance(targets, dict):
        targets = {}
    targets[host] = {
        "host": host,
        "family": family,
        "scopes": {key: bool(value) for key, value in scopes.items()},
        "paths": sorted({item for item in paths if item}),
        "installed_at": _utc_now(),
    }
    return save_install_manifest(project_dir, {"targets": targets})
