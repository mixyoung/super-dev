"""候选身份、扩展结果和追加历史。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess  # nosec B404
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CandidateIdentity, ExtensionEvent, ExtensionResult


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _canonical_digest(payload: dict[str, Any]) -> str:
    return _sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def _git_bytes(project_dir: Path, *args: str) -> bytes:
    completed = subprocess.run(  # nosec B603
        ["git", "-c", "core.quotepath=false", *args],
        cwd=str(project_dir),
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        return b""
    return completed.stdout


def _git_text(project_dir: Path, *args: str) -> str:
    return _git_bytes(project_dir, *args).decode("utf-8", errors="replace").strip()


def _filesystem_snapshot_digest(project: Path) -> str:
    hasher = hashlib.sha256()
    excluded_roots = {
        (project / ".git").resolve(strict=False),
        (project / ".super-dev" / "extensions").resolve(strict=False),
    }
    for path in sorted(
        (item for item in project.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(project).as_posix(),
    ):
        resolved = path.resolve(strict=False)
        if any(root == resolved or root in resolved.parents for root in excluded_roots):
            continue
        if any(part in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"} for part in path.parts):
            continue
        label = path.relative_to(project).as_posix()
        hasher.update(label.encode("utf-8"))
        hasher.update(b"\0")
        try:
            hasher.update(path.read_bytes())
        except OSError:
            hasher.update(b"<unreadable>")
        hasher.update(b"\0")
    return f"sha256:{hasher.hexdigest()}"


def build_candidate_identity(project_dir: Path, *, base_sha: str = "") -> CandidateIdentity:
    project = Path(project_dir).resolve()
    repository = _git_text(project, "rev-parse", "--show-toplevel") or str(project)
    head_sha = _git_text(project, "rev-parse", "HEAD")
    resolved_base = base_sha.strip() or head_sha
    if head_sha:
        dirty_digest = _sha256(_git_bytes(project, "diff", "--binary", "--no-ext-diff"))
        staged_digest = _sha256(
            _git_bytes(project, "diff", "--cached", "--binary", "--no-ext-diff")
        )
    else:
        dirty_digest = _filesystem_snapshot_digest(project)
        staged_digest = _sha256(b"")

    untracked_raw = (
        _git_bytes(project, "ls-files", "--others", "--exclude-standard", "-z")
        if head_sha
        else b""
    )
    untracked_hasher = hashlib.sha256()
    for raw_name in sorted(item for item in untracked_raw.split(b"\0") if item):
        name = raw_name.decode("utf-8", errors="surrogateescape")
        untracked_hasher.update(raw_name)
        untracked_hasher.update(b"\0")
        path = project / name
        if path.is_file():
            try:
                untracked_hasher.update(path.read_bytes())
            except OSError:
                untracked_hasher.update(b"<unreadable>")
        untracked_hasher.update(b"\0")
    untracked_digest = (
        f"sha256:{untracked_hasher.hexdigest()}"
        if head_sha
        else _filesystem_snapshot_digest(project)
    )

    git_common = _git_text(project, "rev-parse", "--git-common-dir")
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
        self.base_dir = self.project_dir / ".super-dev" / "extensions"
        self.runs_dir = self.base_dir / "runs"
        self.history_path = self.base_dir / "history.jsonl"

    def run_dir(self, run_id: str) -> Path:
        if not run_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in run_id):
            raise ValueError("run_id 只能包含小写字母、数字和连字符")
        path = (self.runs_dir / run_id).resolve(strict=False)
        try:
            path.relative_to(self.runs_dir.resolve(strict=False))
        except ValueError as exc:
            raise ValueError("run_id 越出扩展运行目录") from exc
        return path

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
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

    def append_event(self, event: ExtensionEvent) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def load_recent(self, *, limit: int = 20) -> HistoryRead:
        if not self.history_path.exists():
            return HistoryRead(events=(), warnings=())
        warnings: list[str] = []
        events: list[dict[str, Any]] = []
        try:
            lines = self.history_path.read_text(encoding="utf-8").splitlines()
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
            artifact = str(event.get("result_artifact", "")).strip()
            if not artifact:
                continue
            path = (self.project_dir / artifact).resolve(strict=False)
            try:
                path.relative_to(self.runs_dir.resolve(strict=False))
            except ValueError:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                return payload
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
