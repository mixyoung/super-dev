"""批 B（governance-remediation-2026-09）：确认记录统一锁提交的原子性测试。

账本更新失败时不得留下确认文件（账本先行、确认文件最后落盘），避免记录与账本不一致。
"""

from pathlib import Path

import pytest

import super_dev.workflow_guard as guard
from super_dev.review_state import load_docs_confirmation
from super_dev.workflow_guard import save_bound_docs_confirmation


def _prepare_docs(project_dir: Path) -> None:
    output = project_dir / "output"
    (project_dir / ".super-dev" / "review-state").mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    for doc in ("prd", "architecture", "uiux"):
        (output / f"atomic-{doc}.md").write_text(f"# {doc}\n", encoding="utf-8")


def test_docs_confirmation_ledger_failure_leaves_no_confirmation_file(tmp_path: Path, monkeypatch):
    _prepare_docs(tmp_path)

    def ledger_boom(*args, **kwargs):
        raise RuntimeError("ledger write failed")

    monkeypatch.setattr(guard, "_update_stage_ledger", ledger_boom)

    with pytest.raises(RuntimeError, match="ledger write failed"):
        save_bound_docs_confirmation(tmp_path, {"status": "confirmed"})

    assert load_docs_confirmation(tmp_path) is None


def test_docs_confirmation_commit_writes_file_and_event_consistently(tmp_path: Path):
    _prepare_docs(tmp_path)

    file_path, ledger_entry = save_bound_docs_confirmation(
        tmp_path, {"status": "confirmed", "actor": "tester", "comment": "atomic"}
    )

    assert file_path.is_file()
    payload = load_docs_confirmation(tmp_path) or {}
    assert payload.get("status") == "confirmed"
    assert ledger_entry.get("stage") == "docs_confirm"
    events = (tmp_path / ".super-dev" / "workflow-events.jsonl").read_text(encoding="utf-8")
    assert "docs_confirmation_saved" in events
