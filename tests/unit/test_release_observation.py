from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.release_observation import ReleaseObservationError, record_release_observation
from super_dev.review_state import load_workflow_state, save_workflow_state


def test_release_observation_updates_only_released_fact(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "super_dev-2.6.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    save_workflow_state(
        tmp_path,
        {
            "work_item_id": "release-test",
            "artifact_prefix": "release-test",
            "binding_status": "bound",
            "active_change_id": "release-test",
            "status": "delivery_ready",
        },
    )

    path = record_release_observation(
        project_dir=tmp_path,
        target_version="2.6.0",
        tag="v2.6.0",
        repository="mixyoung/super-dev",
        target_sha="abc123",
        release_url="https://github.com/mixyoung/super-dev/releases/tag/v2.6.0",
        asset_paths=[wheel],
        source="release-script",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    facts = payload["delivery_facts"]
    assert facts["released"]["status"] == "verified"
    assert facts["deployed"]["status"] == "unknown"
    assert facts["operating"]["status"] == "unknown"
    state = load_workflow_state(tmp_path) or {}
    assert state["status"] == "released"
    assert state["delivery_facts"]["released"]["target_version"] == "2.6.0"


def test_release_observation_rejects_tag_without_formal_assets(tmp_path: Path) -> None:
    save_workflow_state(
        tmp_path,
        {
            "work_item_id": "release-test",
            "artifact_prefix": "release-test",
            "binding_status": "bound",
            "active_change_id": "release-test",
        },
    )

    with pytest.raises(ReleaseObservationError, match="at least one asset"):
        record_release_observation(
            project_dir=tmp_path,
            target_version="2.6.0",
            tag="v2.6.0",
            repository="mixyoung/super-dev",
            target_sha="abc123",
            release_url="https://github.com/mixyoung/super-dev/releases/tag/v2.6.0",
            asset_paths=[],
            source="release-script",
        )
