"""Verify bound spec quality through real, read-only release Web endpoints."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import super_dev.web.api as web_api
from tests.unit.test_release_readiness_target_binding import _bind, _quality_change, _snapshot


@pytest.mark.parametrize("bound", [False, True])
def test_release_get_spec_items_share_the_target_and_do_not_change_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound: bool
) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "super-dev.yaml").write_text(
        "name: target-fix\nplatform: cli\nfrontend: none\nbackend: python\nquality_gate: 90\n",
        encoding="utf-8",
    )
    target = _quality_change(project_dir, "target-fix")
    if bound:
        unrelated = _quality_change(project_dir, "unrelated-fix", valid=False)
        _bind(project_dir, "target-fix")
        os.utime(target, (1_700_000_000,) * 2)
        os.utime(unrelated, (1_700_010_000,) * 2)
    monkeypatch.setenv("SUPER_DEV_API_PROJECT_ROOTS", str(tmp_path.resolve()))
    monkeypatch.setenv("SUPER_DEV_API_KEY", "test-proof-target-binding-key")
    monkeypatch.setenv("SUPER_DEV_RATE_LIMIT", "0")
    before = _snapshot(project_dir)

    with TestClient(web_api.app) as client:
        readiness_response = client.get(
            "/api/release/readiness", params={"project_dir": str(project_dir)}
        )
        proof_response = client.get(
            "/api/release/proof-pack", params={"project_dir": str(project_dir)}
        )

    assert readiness_response.status_code == proof_response.status_code == 200
    readiness, proof = readiness_response.json(), proof_response.json()
    check = next(item for item in readiness["checks"] if item["name"] == "Spec Quality")
    artifact = next(item for item in proof["artifacts"] if item["name"] == "Spec Quality")
    assert check["passed"] is bound
    assert artifact["status"] == ("ready" if bound else "pending")
    assert set(artifact) == {"name", "status", "summary", "path", "details"}
    assert set(check) == {"name", "passed", "detail", "severity", "recommendation", "evidence"}
    if bound:
        assert artifact["details"]["change_id"] == check["evidence"]["change_id"] == "target-fix"
    else:
        assert artifact["details"] == check["evidence"]
        assert artifact["details"]["reason"] == "missing_active_change"
    for payload in (readiness, proof):
        assert payload["persisted"] is False
        assert payload["report_file"] == payload["json_file"] == ""
    assert proof["summary_file"] == ""
    assert proof["status"] == "incomplete"  # A ready spec item is not a whole release.
    assert not (project_dir / "output").exists()
    assert _snapshot(project_dir) == before
