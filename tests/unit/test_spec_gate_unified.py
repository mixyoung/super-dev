"""批 E（governance-remediation-2026-09）：跨入口“未确认不得推进”覆盖收尾。

入口与覆盖位置清单：
- Web /api/workflow/run（显式 phases / 空 phases 走 config 默认）
  → tests/integration/test_workflow_gate_unified.py（批 B）
- WorkflowEngine.run（显式 / config 默认）
  → tests/integration/test_workflow_gate_unified.py（批 B）
- creators 任务执行（docs/preview 确认门）
  → tests/unit/test_task_executor.py（既有）
- creators SpecBuilder.create_change（docs 确认门）→ 本文件补齐阻塞/放行两路径
"""

from pathlib import Path

import pytest

from super_dev.creators.spec_builder import SpecBuilder
from super_dev.work_item_identity import start_standard_work_item
from super_dev.workflow_guard import WorkflowGateError, save_bound_docs_confirmation


def _write_docs(project_dir: Path, prefix: str) -> None:
    output = project_dir / "output"
    output.mkdir(parents=True, exist_ok=True)
    for doc in ("prd", "architecture", "uiux"):
        (output / f"{prefix}-{doc}.md").write_text(f"# {doc}\n", encoding="utf-8")


def test_spec_builder_blocked_without_docs_confirmation(tmp_path: Path) -> None:
    start_standard_work_item(tmp_path, "ABC-change")
    _write_docs(tmp_path, "abc-change")

    with pytest.raises(WorkflowGateError) as exc_info:
        SpecBuilder(tmp_path, "ABC-change", "gate coverage").create_change(
            [],
            {"backend": "python"},
            scenario="1-N+1",
            changed_surfaces={"backend"},
        )

    assert exc_info.value.gate == "docs_confirmation"


def test_spec_builder_allowed_after_docs_confirmation(tmp_path: Path) -> None:
    start_standard_work_item(tmp_path, "ABC-change")
    _write_docs(tmp_path, "abc-change")
    save_bound_docs_confirmation(tmp_path, {"status": "confirmed", "actor": "user"})

    change_id = SpecBuilder(tmp_path, "ABC-change", "gate coverage").create_change(
        [],
        {"backend": "python"},
        scenario="1-N+1",
        changed_surfaces={"backend"},
    )

    assert change_id
    assert (tmp_path / ".super-dev" / "changes" / change_id).is_dir()
