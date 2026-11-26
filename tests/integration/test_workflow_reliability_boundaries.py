from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import super_dev.web.api as web_api
from super_dev.cli import SuperDevCLI
from super_dev.config import ConfigManager
from super_dev.creators.task_executor import SpecTaskExecutor
from super_dev.orchestrator import engine as engine_module
from super_dev.orchestrator.engine import Phase, PhaseResult, WorkflowEngine
from super_dev.review_state import save_docs_confirmation, save_preview_confirmation
from super_dev.specs import ChangeManager
from super_dev.specs.models import TaskStatus
from super_dev.work_item_identity import start_standard_work_item
from super_dev.workflow_guard import (
    collect_docs_artifact_binding,
    collect_preview_artifact_binding,
    preview_gate_status,
    save_bound_preview_confirmation,
)
from tests.support.workflow_reliability import prepare_work_item


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPER_DEV_API_KEY", "workflow-regression-test-key")
    monkeypatch.setenv("SUPER_DEV_RATE_LIMIT", "0")
    monkeypatch.setenv("SUPER_DEV_API_PROJECT_ROOTS", str(tmp_path))
    for flag in (
        "GOVERNANCE_AVAILABLE",
        "KNOWLEDGE_PUSHER_AVAILABLE",
        "HOOKS_AVAILABLE",
        "COMPACT_AVAILABLE",
        "MEMORY_AVAILABLE",
        "COST_TRACKER_AVAILABLE",
        "PLAN_EXECUTOR_AVAILABLE",
        "OVERSEER_AVAILABLE",
    ):
        monkeypatch.setattr(engine_module, flag, False)
    monkeypatch.setattr(
        engine_module, "get_logger", lambda *args, **kwargs: logging.getLogger(__name__)
    )
    monkeypatch.setattr("super_dev.webhooks.send_webhook", lambda *args, **kwargs: None)
    monkeypatch.setattr("super_dev.version_check.check_for_update", lambda: None)
    web_api._RUN_STORE.clear()
    instance = TestClient(web_api.app, headers={"X-Super-Dev-Key": "workflow-regression-test-key"})
    yield instance
    instance.close()
    web_api._RUN_STORE.clear()


def _state_bytes(project_dir: Path) -> dict[Path, bytes]:
    state = project_dir / ".super-dev"
    return {
        path.relative_to(state): path.read_bytes() for path in state.rglob("*") if path.is_file()
    }


def _install_handlers(monkeypatch: pytest.MonkeyPatch, handlers: dict[Phase, Callable]) -> None:
    original_init = WorkflowEngine.__init__

    def init(self, project_dir):
        original_init(self, project_dir)
        self.console = None
        self._calculate_quality_score = lambda *args: 95.0
        for phase, handler in handlers.items():
            self.register_phase_handler(phase, handler)

    monkeypatch.setattr(WorkflowEngine, "__init__", init)


@pytest.mark.parametrize("prefix", ["/api", "/api/v1"])
@pytest.mark.parametrize("passed", [None, False])
def test_api_cannot_confirm_missing_or_failed_preview(
    tmp_path: Path, client: TestClient, prefix: str, passed: bool | None
) -> None:
    output = prepare_work_item(tmp_path, frontend="react")
    if passed is not None:
        (output / "current-frontend-runtime.json").write_text(
            json.dumps({"passed": passed}), encoding="utf-8"
        )
    before = _state_bytes(tmp_path)

    response = client.post(
        f"{prefix}/workflow/preview-confirmation",
        params={"project_dir": str(tmp_path)},
        json={"status": "confirmed", "actor": "user"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["gate"] == "preview_confirmation"
    assert _state_bytes(tmp_path) == before


@pytest.mark.parametrize("prefix", ["/api", "/api/v1"])
def test_api_cannot_confirm_incomplete_documents(
    tmp_path: Path, client: TestClient, prefix: str
) -> None:
    ConfigManager(tmp_path).create(name="current", platform="cli", frontend="none")
    start_standard_work_item(tmp_path, "current")
    output = tmp_path / "output"
    output.mkdir()
    (output / "current-prd.md").write_text("only PRD", encoding="utf-8")
    before = _state_bytes(tmp_path)

    response = client.post(
        f"{prefix}/workflow/docs-confirmation",
        params={"project_dir": str(tmp_path)},
        json={"status": "confirmed", "actor": "user"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["gate"] == "docs_confirmation"
    assert _state_bytes(tmp_path) == before


def test_api_requesting_a_frontend_cannot_use_configured_non_ui_exemption(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_work_item(tmp_path, frontend="none")

    def forbidden_init(*args, **kwargs):
        raise AssertionError("entry gate must block before engine construction")

    monkeypatch.setattr(WorkflowEngine, "__init__", forbidden_init)
    response = client.post(
        "/api/workflow/run",
        params={"project_dir": str(tmp_path)},
        json={"phases": ["qa"], "frontend": "react"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["gate"] == "preview_confirmation"
    assert web_api._RUN_STORE == {}


def test_api_non_ui_override_is_used_by_both_entry_and_engine(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_work_item(tmp_path, frontend="react")
    calls: list[str] = []

    async def qa(context):
        assert context.user_input["frontend"] == "none"
        calls.append("qa")
        return {"passed": True}

    _install_handlers(monkeypatch, {Phase.QA: qa})
    response = client.post(
        "/api/workflow/run",
        params={"project_dir": str(tmp_path)},
        json={"phases": ["qa"], "frontend": "none"},
    )

    assert response.status_code == 200
    assert calls == ["qa"]
    run_id = response.json()["run_id"]
    status = client.get(f"/api/workflow/status/{run_id}", params={"project_dir": str(tmp_path)})
    assert status.json()["status"] == "completed"


@pytest.mark.parametrize("explicit", [False, True])
def test_api_stops_when_drafting_invalidates_existing_confirmation(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch, explicit: bool
) -> None:
    output = prepare_work_item(tmp_path)
    ConfigManager(tmp_path).update(phases=["drafting", "redteam"])
    calls: list[str] = []

    async def draft(context):
        calls.append("drafting")
        (output / "current-prd.md").write_text("new requirements", encoding="utf-8")
        return {"generated": True}

    async def redteam(context):
        calls.append("redteam")
        return {"passed": True}

    _install_handlers(monkeypatch, {Phase.DRAFTING: draft, Phase.REDTEAM: redteam})
    response = client.post(
        "/api/workflow/run",
        params={"project_dir": str(tmp_path)},
        json={"phases": ["drafting", "redteam"]} if explicit else {},
    )

    assert response.status_code == 200
    run_id = response.json()["run_id"]
    status = client.get(f"/api/workflow/status/{run_id}", params={"project_dir": str(tmp_path)})
    assert status.json()["status"] == "waiting_confirmation"
    assert status.json()["gate_error"]["gate"] == "docs_confirmation"
    assert calls == ["drafting"]


def test_api_does_not_count_rejected_phase_as_completed(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_work_item(tmp_path)

    async def qa(context):
        return PhaseResult(
            phase=Phase.QA,
            success=True,
            duration=0.01,
            quality_score=85,
            output={"report_path": "quality.md"},
        )

    _install_handlers(monkeypatch, {Phase.QA: qa})
    response = client.post(
        "/api/workflow/run", params={"project_dir": str(tmp_path)}, json={"phases": ["qa"]}
    )

    assert response.status_code == 200
    run_id = response.json()["run_id"]
    status = client.get(
        f"/api/workflow/status/{run_id}", params={"project_dir": str(tmp_path)}
    ).json()
    assert status["status"] == "failed"
    assert status["completed_phases"] == []
    assert status["results"][0]["success"] is False
    assert status["results"][0]["output"]["report_path"] == "quality.md"


def test_quality_attachment_updates_do_not_add_a_second_api_preview_gate(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    alignment = output / "current-ui-contract-alignment.json"
    alignment.write_text('{"passed": true, "run": "before"}', encoding="utf-8")
    save_bound_preview_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
    calls: list[str] = []

    async def qa(context):
        calls.append("qa")
        alignment.write_text('{"passed": true, "run": "after"}', encoding="utf-8")
        (output / "current-ui-review.json").write_text('{"passed": true}', encoding="utf-8")
        return {"passed": True}

    async def delivery(context):
        calls.append("delivery")
        return {"ready": True}

    _install_handlers(monkeypatch, {Phase.QA: qa, Phase.DELIVERY: delivery})
    response = client.post(
        "/api/workflow/run",
        params={"project_dir": str(tmp_path)},
        json={"phases": ["qa", "delivery"]},
    )

    assert response.status_code == 200
    assert calls == ["qa", "delivery"]
    assert preview_gate_status(tmp_path)["confirmed"] is True


@pytest.mark.parametrize("passed", [None, False, True])
def test_cli_backend_dispatch_obeys_runtime_and_preview_confirmation(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch, passed: bool | None
) -> None:
    output = prepare_work_item(tmp_path, frontend="react")
    if passed is not None:
        (output / "current-frontend-runtime.json").write_text(
            json.dumps({"passed": passed}), encoding="utf-8"
        )
        if passed:
            save_bound_preview_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})
        else:
            save_preview_confirmation(
                tmp_path,
                {
                    "status": "confirmed",
                    "work_item_id": "current",
                    "artifact_binding": collect_preview_artifact_binding(tmp_path),
                },
            )
    calls: list[str] = []
    monkeypatch.setattr(
        SpecTaskExecutor, "_ensure_backend_modules", lambda *args: calls.append("backend")
    )
    monkeypatch.chdir(tmp_path)
    result = SuperDevCLI().run(
        [
            "task",
            "run",
            "current",
            "--frontend",
            "react",
            "--backend",
            "python",
            "--max-retries",
            "0",
        ]
    )

    assert result == (0 if passed else 1)
    assert calls == (["backend"] if passed else [])
    change = ChangeManager(tmp_path).load_change("current")
    assert change is not None
    assert change.tasks[0].status == (TaskStatus.COMPLETED if passed else TaskStatus.PENDING)


def test_cli_frontend_task_can_run_before_preview_confirmation(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_work_item(tmp_path, frontend="react")
    tasks = tmp_path / ".super-dev/changes/current/tasks.md"
    tasks.write_text("# Tasks\n\n- [ ] **1.1: 实现 core 前端模块**\n", encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(
        SpecTaskExecutor, "_ensure_frontend_modules", lambda *args: calls.append("frontend")
    )
    monkeypatch.chdir(tmp_path)

    result = SuperDevCLI().run(
        ["task", "run", "current", "--frontend", "react", "--backend", "python"]
    )

    assert result == 0
    assert calls == ["frontend"]
    assert preview_gate_status(tmp_path)["confirmed"] is False


def test_cli_non_ui_backend_does_not_require_preview(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_work_item(tmp_path, frontend="none")
    calls: list[str] = []
    monkeypatch.setattr(
        SpecTaskExecutor, "_ensure_backend_modules", lambda *args: calls.append("backend")
    )
    monkeypatch.chdir(tmp_path)

    result = SuperDevCLI().run(
        ["task", "run", "current", "--frontend", "none", "--backend", "python"]
    )

    assert result == 0
    assert calls == ["backend"]


def test_cli_preview_confirmation_rejects_failed_runtime(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": false}', encoding="utf-8")
    before = _state_bytes(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = SuperDevCLI().run(
        ["review", "preview", "--status", "confirmed", "--actor", "user", "--json"]
    )

    assert result == 1
    assert _state_bytes(tmp_path) == before


def test_cli_legacy_incomplete_docs_cannot_create_spec(
    tmp_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    ConfigManager(tmp_path).create(name="legacy", platform="cli", frontend="none")
    output = tmp_path / "output"
    output.mkdir()
    (output / "legacy-prd.md").write_text("only PRD", encoding="utf-8")
    save_docs_confirmation(
        tmp_path,
        {"status": "confirmed", "artifact_binding": collect_docs_artifact_binding(tmp_path)},
    )
    monkeypatch.chdir(tmp_path)

    result = SuperDevCLI().run(
        [
            "spec",
            "propose",
            "legacy",
            "--title",
            "Legacy repair",
            "--description",
            "Incomplete",
            "--no-scaffold",
        ]
    )

    assert result == 1
    assert not (tmp_path / ".super-dev/changes/legacy").exists()


@pytest.mark.parametrize("invalid", ["[]", "null", "{broken", None])
def test_corrupt_authoritative_state_blocks_api_cli_and_resume_guidance(
    tmp_path: Path,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    invalid: str | None,
) -> None:
    from super_dev.workflow_state import detect_pipeline_summary

    prepare_work_item(tmp_path)
    state = tmp_path / ".super-dev/workflow-state.json"
    if invalid is None:
        state.unlink()
    else:
        state.write_text(invalid, encoding="utf-8")
    before = _state_bytes(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        SpecTaskExecutor, "_ensure_backend_modules", lambda *args: calls.append("backend")
    )

    response = client.post(
        "/api/workflow/run", params={"project_dir": str(tmp_path)}, json={"phases": ["qa"]}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["gate"] == "workflow_recovery"
    assert web_api._RUN_STORE == {}

    monkeypatch.chdir(tmp_path)
    result = SuperDevCLI().run(
        ["task", "run", "current", "--frontend", "none", "--backend", "python"]
    )
    assert result == 1
    assert calls == []
    summary = detect_pipeline_summary(tmp_path)
    assert summary["workflow_status"] == "waiting_resume_gate"
    assert summary["workflow_health"]["status"] == (
        "missing_current" if invalid is None else "corrupt"
    )
    assert _state_bytes(tmp_path) == before


@pytest.mark.parametrize("gate", ["docs", "preview"])
def test_corrupt_state_cannot_receive_new_confirmations(
    tmp_path: Path, client: TestClient, gate: str
) -> None:
    output = prepare_work_item(tmp_path, frontend="react")
    (output / "current-frontend-runtime.json").write_text('{"passed": true}', encoding="utf-8")
    (tmp_path / ".super-dev/workflow-state.json").write_text("[]", encoding="utf-8")
    before = _state_bytes(tmp_path)

    response = client.post(
        f"/api/workflow/{gate}-confirmation",
        params={"project_dir": str(tmp_path)},
        json={"status": "confirmed", "actor": "user"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["gate"] == "workflow_recovery"
    assert _state_bytes(tmp_path) == before
