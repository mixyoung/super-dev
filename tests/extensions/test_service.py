from __future__ import annotations

import json
from pathlib import Path

import yaml

from super_dev.extensions.models import ExtensionStatus
from super_dev.extensions.service import ExtensionService
from super_dev.user_directories import UserDirectoryContext


def _write_config(project: Path, *, enabled: bool, allowed: list[str]) -> None:
    (project / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "extension-test",
                "frontend": "next",
                "backend": "node",
                "extensions": {
                    "enabled": enabled,
                    "allowed_builtin_methods": allowed,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_disabled_extension_does_not_create_history(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write_config(project, enabled=False, allowed=[])
    service = ExtensionService(
        project,
        user_directories=UserDirectoryContext.from_home(tmp_path / "isolated-user"),
    )

    outcome = service.probe_contract()

    assert outcome.status == ExtensionStatus.NOT_APPLICABLE
    assert not service.store.history_path.exists()


def test_enabled_contract_probe_writes_core_owned_result_and_events(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write_config(project, enabled=True, allowed=["contract-probe"])
    service = ExtensionService(
        project,
        user_directories=UserDirectoryContext.from_home(tmp_path / "isolated-user"),
    )

    outcome = service.probe_contract()

    assert outcome.status == ExtensionStatus.PASS
    assert outcome.result_path is not None and outcome.result_path.exists()
    payload = json.loads(outcome.result_path.read_text(encoding="utf-8"))
    assert payload["next_action"] == "return-control-to-super-dev"
    assert payload["commands"] == []
    history = service.store.load_recent(limit=10)
    events = {item["event"] for item in history.events}
    assert {"ExtensionRequested", "ExtensionStarted", "ExtensionCompleted"} <= events


def test_changed_candidate_records_evidence_invalidation(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write_config(project, enabled=True, allowed=["contract-probe"])
    service = ExtensionService(
        project,
        user_directories=UserDirectoryContext.from_home(tmp_path / "isolated-user"),
    )
    assert service.probe_contract().status == ExtensionStatus.PASS
    (project / "new-candidate.txt").write_text("changed", encoding="utf-8")

    assert service.probe_contract().status == ExtensionStatus.PASS

    events = [item["event"] for item in service.store.load_recent(limit=20).events]
    assert "ExtensionEvidenceInvalidated" in events
