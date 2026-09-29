"""批 B（governance-remediation-2026-09）：各入口“未确认不得推进”门禁统一回归测试。

锁定已定位的绕过：/api/workflow/run 不带 phases（走 config 默认全阶段）曾可跳过
docs/preview 确认门禁；修复后该路径与显式 phases 在同一位置被真阻断。
"""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import super_dev.web.api as web_api
from super_dev.orchestrator.engine import Phase, WorkflowEngine
from super_dev.workflow_guard import WorkflowGateError, save_bound_docs_confirmation

_TEST_API_KEY = "test-gate-unified-key"
_TEST_HEADERS = {"X-Super-Dev-Key": _TEST_API_KEY}


@pytest.fixture(autouse=True)
def _api_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPER_DEV_API_KEY", _TEST_API_KEY)
    monkeypatch.setenv("SUPER_DEV_RATE_LIMIT", "0")
    monkeypatch.setenv("SUPER_DEV_API_PROJECT_ROOTS", str(tmp_path.resolve()))
    yield


def _prepare_project(project_dir: Path) -> None:
    output = project_dir / "output"
    (project_dir / ".super-dev" / "review-state").mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    (project_dir / "super-dev.yaml").write_text(
        "name: gate-unified\nfrontend: none\nbackend: python\n",
        encoding="utf-8",
    )
    for doc in ("prd", "architecture", "uiux"):
        (output / f"gate-unified-{doc}.md").write_text(f"# {doc}\n", encoding="utf-8")


def test_api_run_without_phases_blocked_without_docs_confirmation(tmp_path: Path):
    _prepare_project(tmp_path)
    client = TestClient(web_api.app, headers=_TEST_HEADERS)

    response = client.post("/api/workflow/run", params={"project_dir": str(tmp_path)}, json={})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail.get("gate") == "docs_confirmation"


def test_api_run_without_phases_allowed_after_docs_confirmation(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    save_bound_docs_confirmation(
        tmp_path, {"status": "confirmed", "actor": "tester", "comment": "gate test"}
    )

    async def fake_run(self, phases=None, context=None, stop_requested=None, **kwargs):
        return {}

    monkeypatch.setattr(web_api.WorkflowEngine, "run", fake_run)
    client = TestClient(web_api.app, headers=_TEST_HEADERS)

    response = client.post("/api/workflow/run", params={"project_dir": str(tmp_path)}, json={})

    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_engine_run_default_phases_enforces_docs_gate(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    engine = WorkflowEngine(tmp_path)
    monkeypatch.setattr(engine, "_get_phases_from_config", lambda: [Phase.DELIVERY])

    with pytest.raises(WorkflowGateError):
        asyncio.run(engine.run())


def test_engine_run_explicit_phases_still_enforced(tmp_path: Path):
    _prepare_project(tmp_path)
    engine = WorkflowEngine(tmp_path)

    with pytest.raises(WorkflowGateError):
        asyncio.run(engine.run(phases=[Phase.DELIVERY]))
