"""Local, explicitly bound inputs for workflow-boundary regression tests."""

from pathlib import Path

from super_dev.config import ConfigManager
from super_dev.work_item_identity import bind_standard_work_item, start_standard_work_item
from super_dev.workflow_guard import save_bound_docs_confirmation


def prepare_work_item(
    project_dir: Path, *, frontend: str = "none", work_item_id: str = "current"
) -> Path:
    ConfigManager(project_dir).create(
        name=work_item_id,
        platform="cli" if frontend == "none" else "web",
        frontend=frontend,
        backend="python",
        database="none",
        quality_gate=90,
    )
    start_standard_work_item(project_dir, work_item_id)
    output = project_dir / "output"
    output.mkdir(exist_ok=True)
    for suffix in ("research", "prd", "architecture", "uiux"):
        (output / f"{work_item_id}-{suffix}.md").write_text(suffix, encoding="utf-8")
    save_bound_docs_confirmation(project_dir, {"status": "confirmed", "actor": "user"})
    change_dir = project_dir / ".super-dev" / "changes" / work_item_id
    change_dir.mkdir(parents=True)
    (change_dir / "change.yaml").write_text(
        f"id: {work_item_id}\ntitle: Workflow boundary regression\nstatus: proposed\n"
        "created_at: 2026-11-13T00:00:00\nupdated_at: 2026-11-13T00:00:00\n",
        encoding="utf-8",
    )
    (change_dir / "proposal.md").write_text("proposal", encoding="utf-8")
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] **1.1: 实现 core 后端模块**\n", encoding="utf-8"
    )
    bind_standard_work_item(project_dir, work_item_id)
    return output
