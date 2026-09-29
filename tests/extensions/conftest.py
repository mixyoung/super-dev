"""tests/extensions 共享夹具。

批 C（governance-remediation-2026-09）起 Web API 的 project_dir 受获准工作区约束；
本目录的测试会直接调用端点函数（不经 TestClient），统一放行 pytest 临时目录。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _web_api_project_roots(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPER_DEV_API_PROJECT_ROOTS", str(Path(tempfile.gettempdir()).resolve()))
    yield
