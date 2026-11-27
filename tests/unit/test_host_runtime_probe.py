from pathlib import Path

from super_dev.host_runtime_probe import build_host_runtime_probe
from super_dev.review_state import (
    save_workflow_state,
    workflow_event_log_file,
)
from tests.support.ui_evidence_inputs import FIXTURE, create_ui_project, publish_browser


def _prepare_core_docs(project_dir: Path) -> None:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{project_dir.name}-prd.md").write_text("# prd\n", encoding="utf-8")
    (output_dir / f"{project_dir.name}-architecture.md").write_text("# arch\n", encoding="utf-8")
    (output_dir / f"{project_dir.name}-uiux.md").write_text("# uiux\n", encoding="utf-8")
    change_dir = project_dir / ".super-dev" / "changes" / "demo-change"
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "proposal.md").write_text("# proposal\n", encoding="utf-8")
    (change_dir / "tasks.md").write_text("# tasks\n", encoding="utf-8")


def test_host_runtime_probe_pending_without_active_workflow_context(temp_project_dir: Path) -> None:
    _prepare_core_docs(temp_project_dir)

    probe = build_host_runtime_probe(
        temp_project_dir,
        target="codex-cli",
        surface_ready=True,
    )

    assert probe["status"] == "pending"
    assert probe["active_context"] is False
    assert probe["blockers"] == []


def test_host_runtime_probe_passes_for_frontend_stage_with_recovery_artifacts(
    temp_project_dir: Path,
) -> None:
    _prepare_core_docs(temp_project_dir)
    (temp_project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / ".super-dev" / "SESSION_BRIEF.md").write_text(
        "当前步骤: 先做前端与运行验证\n",
        encoding="utf-8",
    )
    save_workflow_state(
        temp_project_dir,
        {
            "status": "missing_frontend",
            "workflow_mode": "continue",
            "current_step_label": "先做前端与运行验证",
            "recommended_command": "继续当前流程，进入前端实现与运行验证",
        },
    )

    probe = build_host_runtime_probe(
        temp_project_dir,
        target="codex-cli",
        surface_ready=True,
    )

    assert probe["status"] == "passed"
    assert probe["active_context"] is True
    assert probe["checks"]["core_docs_present"] is True
    assert probe["checks"]["spec_present"] is True


def test_host_runtime_probe_fails_when_active_context_lacks_workflow_event_trail(
    temp_project_dir: Path,
) -> None:
    _prepare_core_docs(temp_project_dir)
    (temp_project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / ".super-dev" / "SESSION_BRIEF.md").write_text(
        "当前步骤: 先做前端与运行验证\n",
        encoding="utf-8",
    )
    save_workflow_state(
        temp_project_dir,
        {
            "status": "missing_frontend",
            "workflow_mode": "continue",
            "current_step_label": "先做前端与运行验证",
            "recommended_command": "继续当前流程，进入前端实现与运行验证",
        },
    )
    workflow_event_log_file(temp_project_dir).unlink()

    probe = build_host_runtime_probe(
        temp_project_dir,
        target="codex-cli",
        surface_ready=True,
    )

    assert probe["status"] == "failed"
    assert any("workflow-events.jsonl" in item for item in probe["blockers"])


def test_host_runtime_probe_does_not_confuse_browser_and_source_results(
    temp_project_dir: Path,
) -> None:
    evidence = create_ui_project(temp_project_dir)
    (temp_project_dir / ".super-dev/changes" / FIXTURE / "proposal.md").write_text(
        "# proposal", encoding="utf-8"
    )
    (temp_project_dir / ".super-dev/changes" / FIXTURE / "tasks.md").write_text(
        "# tasks", encoding="utf-8"
    )
    publish_browser(evidence)
    probe = build_host_runtime_probe(temp_project_dir, target="codex-cli", surface_ready=True)

    assert probe["status"] == "failed"
    assert probe["checks"]["frontend_runtime_current"] is True
    assert probe["checks"]["ui_execution_protocol_current"] is False
    assert any("源码规则" in item for item in probe["blockers"])


def test_host_runtime_probe_reports_missing_baseline_workflow_context(
    temp_project_dir: Path,
) -> None:
    _prepare_core_docs(temp_project_dir)
    (temp_project_dir / ".super-dev").mkdir(parents=True, exist_ok=True)
    (temp_project_dir / ".super-dev" / "SESSION_BRIEF.md").write_text(
        "当前步骤: 先做 baseline\n",
        encoding="utf-8",
    )
    save_workflow_state(
        temp_project_dir,
        {
            "status": "missing_baseline",
            "workflow_mode": "continue",
            "work_mode": "evolve",
            "current_step_label": "先扫描当前项目并建立 baseline",
            "recommended_command": "在宿主里说“先扫描当前项目并建立 baseline，再继续当前流程”",
        },
    )

    probe = build_host_runtime_probe(
        temp_project_dir,
        target="codex-cli",
        surface_ready=True,
    )

    context = probe["workflow_context"]
    assert context["baseline_required"] is True
    assert context["baseline_audit_status"] == "missing"
    assert context["baseline_confirmation_status"] == "missing"
    assert context["blocking_gate"] == "missing_baseline"
    assert (
        context["recommended_host_action"]
        == "$super-dev 先扫描当前项目并建立 baseline，再继续当前流程"
    )
    assert (
        context["recommended_host_sentence"]
        == "super-dev: 先扫描当前项目并建立 baseline，再继续当前流程"
    )
    assert context["can_progress"] is False
