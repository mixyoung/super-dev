"""代码版本身份、扩展结果和追加历史。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess  # nosec B404
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CandidateIdentity, ExtensionEvent, ExtensionResult

# Owned by KnowledgeStatsDB, not project source or application databases.
_RUNTIME_CACHE_PATHS = (
    ".super-dev/knowledge-stats.db",
    ".super-dev/knowledge-stats.db-wal",
    ".super-dev/knowledge-stats.db-shm",
)


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _canonical_digest(payload: dict[str, Any]) -> str:
    return _sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def _git_bytes(project_dir: Path, *args: str) -> bytes | None:
    completed = subprocess.run(  # nosec B603
        ["git", "-c", "core.quotepath=false", *args],
        cwd=str(project_dir),
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def _git_text(project_dir: Path, *args: str) -> str:
    payload = _git_bytes(project_dir, *args)
    if payload is None:
        return ""
    return payload.decode("utf-8", errors="replace").strip()


def _filesystem_snapshot_digest(project: Path, file_manifest: dict[str, str] | None = None) -> str:
    hasher = hashlib.sha256()
    excluded_roots = {
        (project / ".git").resolve(strict=False),
        (project / ".super-dev" / "extensions").resolve(strict=False),
        (project / "output").resolve(strict=False),
    }
    for path in sorted(
        (item for item in project.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(project).as_posix(),
    ):
        label = path.relative_to(project).as_posix()
        if label in _RUNTIME_CACHE_PATHS:
            continue
        resolved = path.resolve(strict=False)
        if any(root == resolved or root in resolved.parents for root in excluded_roots):
            continue
        if any(
            part in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
            for part in path.parts
        ):
            continue
        hasher.update(label.encode("utf-8"))
        hasher.update(b"\0")
        try:
            content = path.read_bytes()
            fingerprint = _sha256(content) if file_manifest is not None else ""
        except OSError:
            content = b"<unreadable>"
            fingerprint = "<unreadable>"
        hasher.update(content)
        if file_manifest is not None:
            file_manifest[label] = fingerprint
        hasher.update(b"\0")
    return f"sha256:{hasher.hexdigest()}"


def build_candidate_identity(
    project_dir: Path,
    *,
    base_sha: str = "",
    file_manifest: dict[str, str] | None = None,
) -> CandidateIdentity:
    """Optionally collect diagnostic fingerprints from the same bytes being hashed.

    Git snapshots collect untracked files; the filesystem fallback collects all
    included files. Diagnostics do not participate in the identity schema.
    """
    if file_manifest is not None:
        file_manifest.clear()
    project = Path(project_dir).resolve()
    repository = _git_text(project, "rev-parse", "--show-toplevel") or str(project)
    head_sha = _git_text(project, "rev-parse", "HEAD")
    resolved_base = base_sha.strip() or head_sha
    git_common = ""
    excluded_paths = (
        ":!.super-dev/extensions",
        ":!output",
        *(f":!{path}" for path in _RUNTIME_CACHE_PATHS),
    )

    if head_sha:
        dirty_raw = _git_bytes(
            project,
            "diff",
            "--binary",
            "--no-ext-diff",
            "--",
            ".",
            *excluded_paths,
        )
        staged_raw = _git_bytes(
            project,
            "diff",
            "--cached",
            "--binary",
            "--no-ext-diff",
            "--",
            ".",
            *excluded_paths,
        )
        untracked_raw = _git_bytes(
            project,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            ".",
            *excluded_paths,
        )
        git_common_raw = _git_bytes(project, "rev-parse", "--git-common-dir")
        git_snapshot_available = all(
            payload is not None
            for payload in (dirty_raw, staged_raw, untracked_raw, git_common_raw)
        )
    else:
        dirty_raw = staged_raw = untracked_raw = git_common_raw = None
        git_snapshot_available = False

    if head_sha and git_snapshot_available:
        assert dirty_raw is not None
        assert staged_raw is not None
        assert untracked_raw is not None
        assert git_common_raw is not None
        dirty_digest = _sha256(dirty_raw)
        staged_digest = _sha256(staged_raw)
        untracked_hasher = hashlib.sha256()
        for raw_name in sorted(item for item in untracked_raw.split(b"\0") if item):
            name = raw_name.decode("utf-8", errors="surrogateescape")
            untracked_hasher.update(raw_name)
            untracked_hasher.update(b"\0")
            path = project / name
            fingerprint = "<not-file>"
            if path.is_file():
                try:
                    content = path.read_bytes()
                    fingerprint = _sha256(content) if file_manifest is not None else ""
                except OSError:
                    content = b"<unreadable>"
                    fingerprint = "<unreadable>"
                untracked_hasher.update(content)
            if file_manifest is not None:
                file_manifest[name] = fingerprint
            untracked_hasher.update(b"\0")
        untracked_digest = f"sha256:{untracked_hasher.hexdigest()}"
        git_common = git_common_raw.decode("utf-8", errors="replace").strip()
    else:
        filesystem_digest = _filesystem_snapshot_digest(project, file_manifest)
        dirty_digest = filesystem_digest
        staged_digest = _sha256(b"<git-state-unavailable>") if head_sha else _sha256(b"")
        untracked_digest = filesystem_digest
        if head_sha:
            git_common = "<git-state-unavailable>"

    worktree_identity = _canonical_digest(
        {
            "project_dir": os.path.normcase(str(project)),
            "git_common_dir": git_common,
        }
    )
    identity_fields = {
        "repository": repository,
        "base_sha": resolved_base,
        "head_sha": head_sha,
        "dirty_diff_digest": dirty_digest,
        "staged_digest": staged_digest,
        "untracked_manifest_digest": untracked_digest,
        "worktree_identity": worktree_identity,
    }
    return CandidateIdentity(
        **identity_fields,
        candidate_digest=_canonical_digest(identity_fields),
    )


def candidate_matches(result_payload: dict[str, Any], current: CandidateIdentity) -> bool:
    candidate = result_payload.get("candidate", {})
    if not isinstance(candidate, dict):
        return False
    return str(candidate.get("candidate_digest", "")) == current.candidate_digest


@dataclass(frozen=True)
class HistoryRead:
    events: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]


class EvidenceStore:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self.base_dir = self._project_path(self.project_dir / ".super-dev" / "extensions")
        self.runs_dir = self._project_path(self.base_dir / "runs")
        self.history_path = self._project_path(self.base_dir / "history.jsonl")
        self.metrics_dir = self._project_path(self.base_dir / "metrics")
        self.verification_metrics_path = self._project_path(
            self.metrics_dir / "verification-pilot.jsonl"
        )
        self.verification_summary_path = self._project_path(
            self.metrics_dir / "verification-pilot-summary.json"
        )

    def _project_path(self, path: Path) -> Path:
        resolved = Path(path).resolve(strict=False)
        try:
            resolved.relative_to(self.project_dir)
        except ValueError as exc:
            raise ValueError("扩展证据路径越出项目目录") from exc
        return resolved

    def run_dir(self, run_id: str) -> Path:
        if not run_id or any(
            char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in run_id
        ):
            raise ValueError("run_id 只能包含小写字母、数字和连字符")
        path = self._project_path(self.runs_dir / run_id)
        try:
            path.relative_to(self.runs_dir)
        except ValueError as exc:
            raise ValueError("run_id 越出扩展运行目录") from exc
        return path

    def _atomic_json(self, path: Path, payload: dict[str, Any]) -> None:
        path = self._project_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def write_result(self, result: ExtensionResult) -> Path:
        path = self.run_dir(result.run_id) / "result.json"
        self._atomic_json(path, result.to_dict())
        return path

    def write_run_json(self, run_id: str, name: str, payload: dict[str, Any]) -> Path:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*\.json", name):
            raise ValueError("运行附件名称必须是小写连字符 JSON 文件名")
        path = self.run_dir(run_id) / name
        self._atomic_json(path, payload)
        return path

    def append_verification_metric(self, payload: dict[str, Any]) -> Path:
        metrics_dir = self._project_path(self.metrics_dir)
        path = self._project_path(self.verification_metrics_path)
        metrics_dir.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return path

    def write_verification_summary(self, payload: dict[str, Any]) -> Path:
        path = self._project_path(self.verification_summary_path)
        self._atomic_json(path, payload)
        return path

    def append_event(self, event: ExtensionEvent) -> None:
        base_dir = self._project_path(self.base_dir)
        path = self._project_path(self.history_path)
        base_dir.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def load_recent(self, *, limit: int = 20) -> HistoryRead:
        path = self._project_path(self.history_path)
        if not path.exists():
            return HistoryRead(events=(), warnings=())
        warnings: list[str] = []
        events: list[dict[str, Any]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return HistoryRead(events=(), warnings=(f"无法读取扩展历史: {exc}",))
        for index, line in reversed(list(enumerate(lines, start=1))):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                warnings.append(f"扩展历史第 {index} 行损坏，已跳过")
                continue
            if not isinstance(payload, dict):
                warnings.append(f"扩展历史第 {index} 行不是对象，已跳过")
                continue
            events.append(payload)
            if len(events) >= max(1, limit):
                break
        return HistoryRead(events=tuple(events), warnings=tuple(warnings))

    def latest_result(self, *, extension_id: str) -> dict[str, Any] | None:
        history = self.load_recent(limit=200)
        for event in history.events:
            if event.get("extension_id") != extension_id:
                continue
            event_run_id = str(event.get("run_id", "")).strip()
            artifact = str(event.get("result_artifact", "")).strip()
            if not artifact or not event_run_id:
                continue
            try:
                expected_path = self.run_dir(event_run_id) / "result.json"
            except ValueError:
                continue
            try:
                path = self._project_path(self.project_dir / artifact)
            except ValueError:
                continue
            if path != expected_path:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            payload_run_id = str(payload.get("run_id", "")).strip()
            if payload_run_id != event_run_id:
                continue
            return payload
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
