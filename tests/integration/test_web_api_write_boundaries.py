"""批 C（governance-remediation-2026-09）：Web API 写边界回归测试。

覆盖三类边界：
1. 写操作（doctor repair、readiness/proof-pack 的 verify_tests/persist）必须走鉴权 POST；
2. GET 只读：评估不落盘（persist_artifacts=False）、不执行测试；
3. project_dir 限定在获准工作区（服务器启动目录 + SUPER_DEV_API_PROJECT_ROOTS）。
"""

import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import super_dev.web.api as web_api
from super_dev.web.api_host_support import _validate_project_dir

_TEST_API_KEY = "test-write-boundary-key-super-dev"
_TEST_HEADERS = {"X-Super-Dev-Key": _TEST_API_KEY}


@pytest.fixture(autouse=True)
def _api_env(monkeypatch):
    """已知 API Key、关闭限流、放行 pytest 临时目录作为获准工作区。"""
    monkeypatch.setenv("SUPER_DEV_API_KEY", _TEST_API_KEY)
    monkeypatch.setenv("SUPER_DEV_RATE_LIMIT", "0")
    monkeypatch.setenv("SUPER_DEV_API_PROJECT_ROOTS", str(Path(tempfile.gettempdir()).resolve()))
    yield


def _client() -> TestClient:
    return TestClient(web_api.app, headers=_TEST_HEADERS)


def _client_no_key() -> TestClient:
    return TestClient(web_api.app)


# ---------- doctor：repair 属于写操作，只能走鉴权 POST ----------


def test_doctor_get_rejects_repair_param():
    response = _client().get("/api/hosts/doctor", params={"repair": "true"})
    assert response.status_code == 400
    assert "POST /api/hosts/doctor/repair" in response.json()["detail"]


def test_doctor_repair_post_requires_api_key():
    response = _client_no_key().post(
        "/api/hosts/doctor/repair", json={"auto": True}, params={"project_dir": "."}
    )
    assert response.status_code == 401


def test_doctor_repair_post_runs_doctor_with_repair(monkeypatch):
    captured = {}

    def fake_run_host_doctor(project_dir_path, **kwargs):
        captured.update(kwargs)
        captured["project_dir"] = str(project_dir_path)
        return {"status": "success", "report": {}, "compatibility": {}}

    monkeypatch.setattr(web_api, "run_host_doctor", fake_run_host_doctor)
    response = _client().post(
        "/api/hosts/doctor/repair",
        json={"auto": True, "force": True},
        params={"project_dir": "."},
    )
    assert response.status_code == 200
    assert captured["repair"] is True
    assert captured["force"] is True
    assert captured["project_dir"] == str(Path(".").resolve())


def test_doctor_get_is_read_only(monkeypatch):
    captured = {}

    def fake_run_host_doctor(project_dir_path, **kwargs):
        captured.update(kwargs)
        return {"status": "success"}

    monkeypatch.setattr(web_api, "run_host_doctor", fake_run_host_doctor)
    response = _client().get("/api/hosts/doctor", params={"force": "true"})
    assert response.status_code == 200
    assert captured["repair"] is False
    assert captured["force"] is False


# ---------- release readiness / proof pack：GET 只读，写参数走鉴权 POST ----------


class _FakeReport:
    def to_dict(self):
        return {"summary": {"executive_summary": ""}, "checks": []}


class _FakeEvaluator:
    instances: list["_FakeEvaluator"] = []

    def __init__(self, project_dir, *, persist_artifacts=True):
        self.project_dir = project_dir
        self.persist_artifacts = persist_artifacts
        self.verify_tests = None
        self.wrote = False
        _FakeEvaluator.instances.append(self)

    def evaluate(self, verify_tests=False, **kwargs):
        self.verify_tests = verify_tests
        return _FakeReport()

    def write(self, report):
        self.wrote = True
        return {
            "markdown": Path("fake-release-readiness.md"),
            "json": Path("fake-release-readiness.json"),
        }


class _FakeProofBuilder:
    instances: list["_FakeProofBuilder"] = []

    def __init__(self, project_dir, *, persist_artifacts=True):
        self.project_dir = project_dir
        self.persist_artifacts = persist_artifacts
        self.verify_tests = None
        self.wrote = False
        _FakeProofBuilder.instances.append(self)

    def build(self, verify_tests=False):
        self.verify_tests = verify_tests
        return _FakeReport()

    def write(self, report):
        self.wrote = True
        return {
            "markdown": Path("fake-proof-pack.md"),
            "json": Path("fake-proof-pack.json"),
            "summary": Path("fake-proof-pack-summary.md"),
        }


@pytest.fixture()
def fake_evaluator(monkeypatch):
    _FakeEvaluator.instances = []
    monkeypatch.setattr(web_api, "ReleaseReadinessEvaluator", _FakeEvaluator)
    return _FakeEvaluator


@pytest.fixture()
def fake_proof_builder(monkeypatch):
    _FakeProofBuilder.instances = []
    monkeypatch.setattr(web_api, "ProofPackBuilder", _FakeProofBuilder)
    return _FakeProofBuilder


@pytest.mark.parametrize("flags", [{"verify_tests": "true"}, {"persist": "true"}])
def test_release_readiness_get_rejects_write_flags(flags):
    response = _client().get("/api/release/readiness", params=flags)
    assert response.status_code == 400


@pytest.mark.parametrize("flags", [{"verify_tests": "true"}, {"persist": "true"}])
def test_proof_pack_get_rejects_write_flags(flags):
    response = _client().get("/api/release/proof-pack", params=flags)
    assert response.status_code == 400


def test_release_readiness_get_is_read_only(fake_evaluator):
    response = _client().get("/api/release/readiness", params={"project_dir": "."})
    assert response.status_code == 200
    evaluator = fake_evaluator.instances[-1]
    assert evaluator.persist_artifacts is False
    assert evaluator.verify_tests is False
    assert evaluator.wrote is False
    payload = response.json()
    assert payload["persisted"] is False
    assert payload["report_file"] == ""


def test_proof_pack_get_is_read_only(fake_proof_builder):
    response = _client().get("/api/release/proof-pack", params={"project_dir": "."})
    assert response.status_code == 200
    builder = fake_proof_builder.instances[-1]
    assert builder.persist_artifacts is False
    assert builder.verify_tests is False
    assert builder.wrote is False
    assert response.json()["persisted"] is False


def test_release_readiness_post_requires_api_key(fake_evaluator):
    response = _client_no_key().post("/api/release/readiness", json={"persist": True})
    assert response.status_code == 401


def test_proof_pack_post_requires_api_key(fake_proof_builder):
    response = _client_no_key().post("/api/release/proof-pack", json={"verify_tests": True})
    assert response.status_code == 401


def test_release_readiness_post_executes_and_persists_with_key(fake_evaluator):
    response = _client().post(
        "/api/release/readiness",
        json={"verify_tests": True, "persist": True},
        params={"project_dir": "."},
    )
    assert response.status_code == 200
    evaluator = fake_evaluator.instances[-1]
    assert evaluator.verify_tests is True
    assert evaluator.wrote is True
    payload = response.json()
    assert payload["persisted"] is True
    assert payload["report_file"].endswith("fake-release-readiness.md")


# ---------- project_dir 获准工作区约束 ----------


def test_validate_project_dir_rejects_outside_workspace(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPER_DEV_API_PROJECT_ROOTS", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        _validate_project_dir(str(tmp_path))
    assert exc_info.value.status_code == 400


def test_validate_project_dir_allows_configured_root(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPER_DEV_API_PROJECT_ROOTS", str(tmp_path))
    resolved = _validate_project_dir(str(tmp_path / "sub"))
    assert resolved == (tmp_path / "sub").resolve()


def test_validate_project_dir_rejects_traversal():
    with pytest.raises(HTTPException) as exc_info:
        _validate_project_dir("../outside")
    assert exc_info.value.status_code == 400


def test_doctor_rejects_project_dir_outside_workspace(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPER_DEV_API_PROJECT_ROOTS", raising=False)
    response = _client().get("/api/hosts/doctor", params={"project_dir": str(tmp_path)})
    assert response.status_code == 400
    assert "获准工作区" in response.json()["detail"]
