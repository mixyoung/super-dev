"""Record a successfully observed formal release without inferring deployment."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .atomic_io import atomic_write_text
from .delivery_facts import DeliveryFacts, build_delivery_facts
from .evidence_contract import EvidenceArtifact, EvidenceEnvelope, EvidenceStatus
from .review_state import load_workflow_state, save_workflow_state


class ReleaseObservationError(ValueError):
    """Raised when a formal release observation is incomplete or unsafe."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _safe_asset(project_dir: Path, path: Path) -> Path:
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(project_dir)
    except ValueError as exc:
        raise ReleaseObservationError(f"release asset escapes project directory: {path}") from exc
    if not resolved.is_file():
        raise ReleaseObservationError(f"release asset is missing: {path}")
    return resolved


def record_release_observation(
    *,
    project_dir: Path,
    target_version: str,
    tag: str,
    repository: str,
    target_sha: str,
    release_url: str,
    asset_paths: list[Path],
    source: str,
    observed_at: str = "",
) -> Path:
    project = Path(project_dir).resolve()
    values = {
        "target_version": target_version,
        "tag": tag,
        "repository": repository,
        "target_sha": target_sha,
        "release_url": release_url,
        "source": source,
    }
    missing = [name for name, value in values.items() if not str(value).strip()]
    if missing:
        raise ReleaseObservationError("missing release observation fields: " + ", ".join(missing))
    assets = [_safe_asset(project, item) for item in asset_paths]
    if not assets:
        raise ReleaseObservationError("a formal release observation requires at least one asset")

    state = load_workflow_state(project) or {}
    work_item_id = str(state.get("work_item_id", "")).strip()
    if not work_item_id:
        raise ReleaseObservationError("current work_item_id is required")
    candidate_digest = str(state.get("candidate_digest", "")).strip() or f"git:{target_sha}"
    timestamp = str(observed_at).strip() or _utc_now()
    artifacts = tuple(
        EvidenceArtifact(
            path=path.relative_to(project).as_posix(),
            digest=_sha256(path),
            media_type="application/octet-stream",
        )
        for path in assets
    )
    envelope = EvidenceEnvelope(
        schema_version=1,
        evidence_id=f"release-{tag}-{target_sha[:12]}",
        evidence_type="release_observation",
        subject_type="git_commit",
        subject_digest=f"git:{target_sha}",
        work_item_id=work_item_id,
        candidate_digest=candidate_digest,
        producer=str(source).strip(),
        run_id=f"release-{tag}",
        status=EvidenceStatus.PASS,
        observed_at=timestamp,
        operation=("formal_release",),
        environment={"repository": repository, "tag": tag},
        artifacts=artifacts,
        invalidation_triggers=("target_version_changed", "release_assets_changed"),
    )

    release_facts = build_delivery_facts(
        released=True,
        evidence={"released": [release_url, *(item.path for item in artifacts)]},
        sources={"released": source},
        observed_at={"released": timestamp},
        target_versions={"released": target_version},
    )
    existing = DeliveryFacts.from_dict(
        state.get("delivery_facts", {}) if isinstance(state.get("delivery_facts"), dict) else {}
    )
    merged = DeliveryFacts(
        delivery_ready=existing.delivery_ready,
        released=release_facts.released,
        deployed=existing.deployed,
        operating=existing.operating,
    )

    payload: dict[str, Any] = {
        "schema_version": 1,
        "observation_type": "formal_release",
        "target_version": target_version,
        "tag": tag,
        "repository": repository,
        "target_sha": target_sha,
        "release_url": release_url,
        "observed_at": timestamp,
        "source": source,
        "evidence_envelope": envelope.to_dict(),
        "delivery_facts": merged.to_dict(),
        "assets": [item.to_dict() for item in artifacts],
    }
    prefix = str(state.get("artifact_prefix", "")).strip() or project.name
    output_path = (
        project / "output" / "release" / f"{prefix}-{target_version}-release-observation.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(output_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    updated_state = {
        **state,
        "status": "released",
        "current_stage": "delivery",
        "current_step_label": "正式版本已发布",
        "reason": f"已观察到 {tag} 正式 Release 及其制品。",
        "evidence": str(output_path.relative_to(project).as_posix()),
        "delivery_facts": merged.to_dict(),
    }
    save_workflow_state(project, updated_state)
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="记录已经成功的正式 Release 观察结果")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--release-url", required=True)
    parser.add_argument("--source", default="release-script")
    parser.add_argument("--asset", action="append", default=[])
    args = parser.parse_args(argv)
    record_release_observation(
        project_dir=Path(args.project_dir),
        target_version=args.target_version,
        tag=args.tag,
        repository=args.repository,
        target_sha=args.target_sha,
        release_url=args.release_url,
        asset_paths=[Path(item) for item in args.asset],
        source=args.source,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ReleaseObservationError", "record_release_observation"]
