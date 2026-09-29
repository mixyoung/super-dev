"""批 D2（governance-remediation-2026-09）后的"真实就绪"测试输入。

发布就绪夹具自批 D2 起不能再依赖 unknown/缺失折算为 PASS 的旧口径。
使用顺序约束：
- write_release_ready_docs 必须先于夹具内 evidence_identity 产物水化（身份自洽）；
- record_release_ready_acceptance 必须在一切会改写 docs/preview 绑定文件的
  产物水化之后调用（绑定摘要对最终内容成立）。
若夹具没有后续水化，可用 hydrate_release_ready_inputs 一次完成两步。
"""

from __future__ import annotations

from pathlib import Path

from super_dev.host_runtime_validation import update_host_runtime_validation_state
from super_dev.workflow_guard import (
    save_bound_docs_confirmation,
    save_bound_preview_confirmation,
)


def write_release_ready_docs(
    project_dir: Path,
    *,
    change_id: str = "release-hardening-finalization",
) -> None:
    project_dir = Path(project_dir)
    name = project_dir.name
    output = project_dir / "output"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{name}-prd.md").write_text(
        "# PRD\n\n## 2. 功能需求\n\n### 版本信息展示\n\n在 README 与包内元数据中展示当前版本号。\n",
        encoding="utf-8",
    )
    for doc in ("architecture", "uiux"):
        target = output / f"{name}-{doc}.md"
        if not target.exists():
            target.write_text(f"# {doc}\n", encoding="utf-8")
    change_dir = project_dir / ".super-dev" / "changes" / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n- [x] 版本信息展示：README 与包内版本一致\n",
        encoding="utf-8",
    )


def record_release_ready_acceptance(
    project_dir: Path,
    *,
    change_id: str = "release-hardening-finalization",
) -> None:
    """按当前最终文档与 preview 产物重绑 docs/preview 确认，并录入宿主真人验收。

    repo 连续性探针要求 workflow-state.json 与 SESSION_BRIEF 存在；夹具若无任何
    工作流状态，这里补一个与阶段账本一致的交付就绪状态。
    """
    project_dir = Path(project_dir)
    if not (project_dir / ".super-dev" / "workflow-state.json").exists():
        from super_dev.review_state import save_workflow_state

        # 不设置 active_change_id：避免改变产物前缀解析（夹具产物按目录名前缀水化）。
        save_workflow_state(
            project_dir,
            {
                "status": "delivery",
                "current_step_label": "交付证据已就绪",
            },
        )
    save_bound_docs_confirmation(
        project_dir,
        {"status": "confirmed", "actor": "fixture", "comment": "release-ready fixture"},
    )
    save_bound_preview_confirmation(
        project_dir,
        {"status": "confirmed", "actor": "fixture", "comment": "release-ready fixture"},
    )
    update_host_runtime_validation_state(
        project_dir=project_dir,
        host="codex-cli",
        status="passed",
        comment="release-ready fixture",
        actor="fixture",
    )


def hydrate_release_ready_inputs(
    project_dir: Path,
    *,
    change_id: str = "release-hardening-finalization",
) -> None:
    write_release_ready_docs(project_dir, change_id=change_id)
    record_release_ready_acceptance(project_dir)
