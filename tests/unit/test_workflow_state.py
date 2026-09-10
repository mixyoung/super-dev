from __future__ import annotations

import json
import os
from pathlib import Path

from super_dev.change_ledger import ChangeLedger
from super_dev.review_state import save_baseline_confirmation, save_resume_gate
from super_dev.workflow_guard import record_stage_progress, save_bound_docs_confirmation
from super_dev.workflow_state import (
    build_host_entry_prompts,
    build_host_flow_probe,
    detect_pipeline_summary,
)


def test_build_host_entry_prompts_supports_seeai_codex():
    payload = build_host_entry_prompts(
        target="codex-cli",
        instruction="继续当前比赛项目",
        supports_slash=False,
        flow_variant="seeai",
    )

    prompts = payload["entry_prompts"]
    assert prompts["cli"].startswith("$super-dev-seeai ")
    assert prompts["fallback"].startswith("super-dev-seeai:")


def test_build_host_entry_prompts_supports_kimi_skill_and_flow_entries():
    payload = build_host_entry_prompts(
        target="kimi-code",
        instruction="继续当前流程",
        supports_slash=False,
        flow_variant="standard",
    )

    assert payload["preferred_entry"] == "skill"
    assert payload["preferred_entry_label"] == "Skill"
    assert payload["entry_labels"]["skill"] == "Skill"
    assert payload["entry_prompts"]["skill"].startswith("/skill:super-dev ")
    assert payload["entry_prompts"]["flow"].startswith("/flow:super-dev ")
    assert payload["entry_prompts"]["fallback"].startswith("super-dev:")


def test_build_host_entry_prompts_supports_droid_headless_resume_entry():
    payload = build_host_entry_prompts(
        target="droid-cli",
        instruction="继续当前流程",
        supports_slash=True,
        flow_variant="standard",
    )

    assert payload["preferred_entry"] == "slash"
    assert payload["entry_labels"]["headless"] == "Headless"
    assert payload["entry_prompts"]["slash"].startswith("/super-dev ")
    assert "droid exec --session-id" in payload["entry_prompts"]["headless"]


def test_build_host_flow_probe_uses_adapter_for_codebuddy_and_droid_cli():
    codebuddy_probe = build_host_flow_probe("codebuddy-cli")
    droid_probe = build_host_flow_probe("droid-cli")

    assert codebuddy_probe["enabled"] is True
    assert "CodeBuddy" in codebuddy_probe["title"]
    assert any("super-dev-seeai" in step for step in codebuddy_probe["steps"])
    assert "SEEAI" in codebuddy_probe["success_signal"]

    assert droid_probe["enabled"] is True
    assert "Droid CLI" in droid_probe["title"]
    assert any("super-dev-seeai" in step for step in droid_probe["steps"])
    assert any("droid exec --session-id" in step for step in droid_probe["steps"])
    assert "SEEAI" in droid_probe["success_signal"]


def test_build_host_flow_probe_preserves_codex_special_probe():
    codex_probe = build_host_flow_probe("codex-cli")

    assert codex_probe["enabled"] is True
    assert codex_probe["title"] == "Codex CLI 双入口同流程验收"
    assert any("$super-dev" in step for step in codex_probe["steps"])


def test_build_host_flow_probe_generates_generic_probe_for_official_hosts():
    qoder_probe = build_host_flow_probe("qoder")
    workbuddy_probe = build_host_flow_probe("workbuddy")

    assert qoder_probe["enabled"] is True
    assert "Qoder" in qoder_probe["title"]
    assert any("/super-dev" in step for step in qoder_probe["steps"])

    assert workbuddy_probe["enabled"] is True
    assert "WorkBuddy" in workbuddy_probe["title"]
    assert any("super-dev: <需求描述>" in step for step in workbuddy_probe["steps"])


def test_detect_pipeline_summary_seeai_skips_preview_gate(temp_project_dir: Path):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    changes_dir = superdev_dir / "changes" / "demo-change"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    changes_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / f"{temp_project_dir.name}-research.md").write_text("research", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-architecture.md").write_text(
        "architecture", encoding="utf-8"
    )
    (output_dir / f"{temp_project_dir.name}-uiux.md").write_text("uiux", encoding="utf-8")
    (changes_dir / "proposal.md").write_text("proposal", encoding="utf-8")
    (changes_dir / "tasks.md").write_text("tasks", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-frontend-runtime.json").write_text(
        json.dumps({"passed": True}),
        encoding="utf-8",
    )
    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"flow_variant": "seeai"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["flow_variant"] == "seeai"
    assert summary["workflow_status"] == "missing_backend"
    assert "SEEAI" in summary["recommended_command"]


def _prepare_implemented_project(temp_project_dir: Path, *, frontend: str, backend: str) -> None:
    superdev_dir = temp_project_dir / ".super-dev"
    output_dir = temp_project_dir / "output"
    changes_dir = superdev_dir / "changes" / "demo-change"
    output_dir.mkdir(parents=True, exist_ok=True)
    changes_dir.mkdir(parents=True, exist_ok=True)
    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "evolve"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (temp_project_dir / "super-dev.yaml").write_text(
        "\n".join(
            [
                "name: existing-cli",
                "platform: cli",
                f"frontend: {frontend}",
                f"backend: {backend}",
                "database: none",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    for suffix in ("research", "prd", "architecture", "uiux"):
        (output_dir / f"{temp_project_dir.name}-{suffix}.md").write_text(
            suffix,
            encoding="utf-8",
        )
    (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
        "baseline",
        encoding="utf-8",
    )
    (changes_dir / "proposal.md").write_text("proposal", encoding="utf-8")
    (changes_dir / "tasks.md").write_text("tasks", encoding="utf-8")
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "confirmed",
            "comment": "existing project baseline confirmed",
            "actor": "pytest",
        },
    )


def test_detect_pipeline_summary_treats_root_python_cli_as_implemented_backend(
    temp_project_dir: Path,
) -> None:
    _prepare_implemented_project(temp_project_dir, frontend="none", backend="python")
    (temp_project_dir / "pyproject.toml").write_text(
        '[project]\nname = "existing-cli"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (temp_project_dir / "super_dev").mkdir()

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["frontend_required"] is False
    assert summary["backend_required"] is True
    assert summary["artifacts"]["frontend"] is True
    assert summary["artifacts"]["frontend_runtime_report"] == ""
    assert summary["artifacts"]["backend"] is True
    assert summary["workflow_status"] == "missing_quality"
    assert summary["workflow_status"] not in {"missing_frontend", "waiting_preview_confirmation"}
    stage_statuses = {stage["canonical_id"]: stage["status"] for stage in summary["stages"]}
    assert stage_statuses["frontend"] == "not_applicable"
    assert stage_statuses["preview_confirm"] == "not_applicable"
    assert stage_statuses["backend"] == "completed"
    expert_stages = {stage["stage"]: stage for stage in summary["expert_governance"]["stages"]}
    assert expert_stages["frontend"]["evidence_status"] == "not_required"
    assert expert_stages["preview_confirm"]["evidence_status"] == "not_required"


def test_detect_pipeline_summary_still_requires_runtime_for_configured_frontend(
    temp_project_dir: Path,
) -> None:
    _prepare_implemented_project(temp_project_dir, frontend="react", backend="none")

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["frontend_required"] is True
    assert summary["backend_required"] is False
    assert summary["artifacts"]["frontend"] is False
    assert summary["artifacts"]["backend"] is True
    assert summary["workflow_status"] == "missing_frontend"
    backend_stage = next(stage for stage in summary["stages"] if stage["canonical_id"] == "backend")
    assert backend_stage["status"] == "not_applicable"
    assert backend_stage["expert_evidence_status"] == "not_required"


def _prepare_active_change_pipeline(
    project_dir: Path,
    *,
    active_change_id: str = "active-change",
    frontend: str = "none",
) -> tuple[Path, Path]:
    superdev_dir = project_dir / ".super-dev"
    output_dir = project_dir / "output"
    change_dir = superdev_dir / "changes" / active_change_id
    output_dir.mkdir(parents=True, exist_ok=True)
    change_dir.mkdir(parents=True, exist_ok=True)
    (superdev_dir / "workflow-state.json").write_text(
        json.dumps(
            {"active_change_id": active_change_id, "work_mode": "new"},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (project_dir / "super-dev.yaml").write_text(
        f"name: configured-project\nfrontend: {frontend}\nbackend: none\n",
        encoding="utf-8",
    )
    for suffix in ("research", "prd", "architecture", "uiux"):
        (output_dir / f"{active_change_id}-{suffix}.md").write_text(
            suffix,
            encoding="utf-8",
        )
    (change_dir / "proposal.md").write_text("proposal", encoding="utf-8")
    (change_dir / "tasks.md").write_text("tasks", encoding="utf-8")
    return output_dir, change_dir


def test_active_change_research_docs_and_spec_ignore_other_changes(
    temp_project_dir: Path,
) -> None:
    superdev_dir = temp_project_dir / ".super-dev"
    output_dir = temp_project_dir / "output"
    active_dir = superdev_dir / "changes" / "active-change"
    other_dir = superdev_dir / "changes" / "other-change"
    output_dir.mkdir(parents=True)
    active_dir.mkdir(parents=True)
    other_dir.mkdir(parents=True)
    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"active_change_id": "active-change", "work_mode": "new"}),
        encoding="utf-8",
    )
    (temp_project_dir / "super-dev.yaml").write_text(
        "frontend: none\nbackend: none\n",
        encoding="utf-8",
    )
    for suffix in ("research", "prd", "architecture", "uiux"):
        (output_dir / f"other-change-{suffix}.md").write_text(suffix, encoding="utf-8")
    (other_dir / "proposal.md").write_text("proposal", encoding="utf-8")
    (other_dir / "tasks.md").write_text("tasks", encoding="utf-8")

    missing_active_docs = detect_pipeline_summary(temp_project_dir)
    assert missing_active_docs["workflow_status"] == "missing_research"
    assert missing_active_docs["artifacts"]["spec"] is False

    for suffix in ("research", "prd", "architecture", "uiux"):
        (output_dir / f"active-change-{suffix}.md").write_text(suffix, encoding="utf-8")
    save_bound_docs_confirmation(
        temp_project_dir,
        {"status": "confirmed", "actor": "pytest"},
    )

    missing_active_spec = detect_pipeline_summary(temp_project_dir)
    assert missing_active_spec["workflow_status"] == "missing_spec"
    assert missing_active_spec["artifacts"]["spec"] is False


def test_active_change_quality_requires_passed_json_not_markdown_or_failed_json(
    temp_project_dir: Path,
) -> None:
    output_dir, _ = _prepare_active_change_pipeline(temp_project_dir)
    quality_markdown = output_dir / "active-change-quality-gate.md"
    quality_json = output_dir / "active-change-quality-gate.json"
    quality_markdown.write_text("# generated only", encoding="utf-8")

    markdown_only = detect_pipeline_summary(temp_project_dir)
    assert markdown_only["active_change_id"] == "active-change"
    assert markdown_only["artifact_prefix"] == "active-change"
    assert markdown_only["workflow_status"] == "missing_quality"
    assert markdown_only["artifacts"]["quality"] is False

    quality_json.write_text(json.dumps({"passed": False}), encoding="utf-8")
    failed = detect_pipeline_summary(temp_project_dir)
    assert failed["workflow_status"] == "missing_quality"
    assert failed["artifacts"]["quality_gate_state"]["status"] == "failed"


def test_active_change_stale_quality_json_is_not_complete(temp_project_dir: Path) -> None:
    output_dir, _ = _prepare_active_change_pipeline(temp_project_dir)
    quality_json = output_dir / "active-change-quality-gate.json"
    quality_json.write_text(json.dumps({"passed": True}), encoding="utf-8")
    quality_mtime = quality_json.stat().st_mtime
    prd_file = output_dir / "active-change-prd.md"
    os.utime(prd_file, (quality_mtime + 5, quality_mtime + 5))

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["workflow_status"] == "missing_quality"
    assert summary["artifacts"]["quality"] is False
    assert summary["artifacts"]["quality_gate_state"]["stale"] is True
    assert (
        str(prd_file.resolve()) in summary["artifacts"]["quality_gate_state"]["newer_dependencies"]
    )


def test_active_change_passed_current_quality_json_enters_delivery(
    temp_project_dir: Path,
) -> None:
    output_dir, _ = _prepare_active_change_pipeline(temp_project_dir)
    quality_json = output_dir / "active-change-quality-gate.json"
    quality_json.write_text(json.dumps({"passed": True}), encoding="utf-8")

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["workflow_status"] == "missing_delivery"
    assert summary["artifacts"]["quality"] is True
    assert summary["artifacts"]["quality_gate_report"] == str(quality_json.resolve())


def test_frontend_none_quality_freshness_ignores_ui_and_other_change_artifacts(
    temp_project_dir: Path,
) -> None:
    output_dir, _ = _prepare_active_change_pipeline(temp_project_dir, frontend="none")
    quality_json = output_dir / "active-change-quality-gate.json"
    quality_json.write_text(json.dumps({"passed": True}), encoding="utf-8")
    quality_mtime = quality_json.stat().st_mtime
    for filename in (
        "active-change-ui-contract.json",
        "active-change-frontend-runtime.json",
        "other-change-ui-review.json",
        "other-change-prd.md",
    ):
        artifact = output_dir / filename
        artifact.write_text(json.dumps({"passed": True}), encoding="utf-8")
        os.utime(artifact, (quality_mtime + 5, quality_mtime + 5))

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["frontend_required"] is False
    assert summary["workflow_status"] == "missing_delivery"
    assert summary["artifacts"]["quality"] is True
    assert summary["artifacts"]["quality_gate_state"]["stale"] is False


def test_cli_delivery_does_not_require_service_rehearsal(temp_project_dir: Path) -> None:
    output_dir, _ = _prepare_active_change_pipeline(temp_project_dir, frontend="none")
    (temp_project_dir / "super-dev.yaml").write_text(
        "name: configured-project\nplatform: cli\nfrontend: none\nbackend: none\n",
        encoding="utf-8",
    )
    (output_dir / "active-change-quality-gate.json").write_text(
        json.dumps({"passed": True}),
        encoding="utf-8",
    )
    delivery_dir = output_dir / "delivery"
    delivery_dir.mkdir()
    (delivery_dir / "active-change-delivery-manifest.json").write_text(
        json.dumps({"status": "ready"}),
        encoding="utf-8",
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["artifacts"]["rehearsal_required"] is False
    assert summary["artifacts"]["rehearsal_report_passed"] is True
    assert summary["artifacts"]["delivery"] is True
    assert summary["workflow_status"] == "ready"


def test_service_delivery_still_requires_rehearsal(temp_project_dir: Path) -> None:
    output_dir, _ = _prepare_active_change_pipeline(temp_project_dir, frontend="none")
    (temp_project_dir / "super-dev.yaml").write_text(
        "name: configured-project\nplatform: web\nfrontend: none\nbackend: none\n",
        encoding="utf-8",
    )
    (output_dir / "active-change-quality-gate.json").write_text(
        json.dumps({"passed": True}),
        encoding="utf-8",
    )
    delivery_dir = output_dir / "delivery"
    delivery_dir.mkdir()
    (delivery_dir / "active-change-delivery-manifest.json").write_text(
        json.dumps({"status": "ready"}),
        encoding="utf-8",
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["artifacts"]["rehearsal_required"] is True
    assert summary["artifacts"]["rehearsal_report_passed"] is False
    assert summary["artifacts"]["delivery"] is False
    assert summary["workflow_status"] == "missing_delivery"


def test_detect_pipeline_summary_includes_read_only_shadow_ledger(
    temp_project_dir: Path,
) -> None:
    ledger = ChangeLedger.create(
        change_id="summary-ledger",
        harness_version="2.4.0",
        intent="quick_edit",
        governance_depth="bounded",
        work_mode="patch",
    )
    ledger_path = temp_project_dir / ".super-dev" / "changes" / "summary-ledger" / "ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(ledger.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = detect_pipeline_summary(temp_project_dir, include_shadow_ledger=True)

    assert summary["shadow_ledger"]["active_change_id"] == "summary-ledger"
    assert summary["shadow_ledger"]["read_only"] is True
    assert summary["shadow_ledger"]["control_authority"] == "none"


def test_shadow_ledger_does_not_change_workflow_control_fields(
    temp_project_dir: Path,
) -> None:
    without_shadow = detect_pipeline_summary(temp_project_dir)
    assert "shadow_ledger" not in without_shadow
    ledger = ChangeLedger.create(
        change_id="control-check",
        harness_version="2.4.0",
        intent="build",
        governance_depth="commercial",
        work_mode="evolve",
    )
    ledger_path = temp_project_dir / ".super-dev" / "changes" / "control-check" / "ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger.to_dict()), encoding="utf-8")

    with_shadow = detect_pipeline_summary(temp_project_dir, include_shadow_ledger=True)
    observation = with_shadow.pop("shadow_ledger")

    assert observation["control_authority"] == "none"
    for key in (
        "workflow_status",
        "recommended_command",
        "current_stage_id",
        "blocker",
        "action_card",
        "stages",
        "docs_confirmation",
        "preview_confirmation",
        "quality_revision",
    ):
        assert with_shadow[key] == without_shadow[key]
    for gate_name in ("docs_gate", "preview_gate"):
        for key in ("confirmed", "status", "reason", "binding_matches_current"):
            assert with_shadow[gate_name].get(key) == without_shadow[gate_name].get(key)
    assert with_shadow["artifacts"]["quality"] == without_shadow["artifacts"]["quality"]


def test_detect_pipeline_summary_includes_expert_governance(temp_project_dir: Path):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    changes_dir = superdev_dir / "changes" / "demo-change"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    changes_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / f"{temp_project_dir.name}-research.md").write_text("research", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-prd.md").write_text("prd", encoding="utf-8")
    (output_dir / f"{temp_project_dir.name}-architecture.md").write_text(
        "architecture", encoding="utf-8"
    )
    (output_dir / f"{temp_project_dir.name}-uiux.md").write_text("uiux", encoding="utf-8")

    record_stage_progress(temp_project_dir, stage="research", status="completed")
    record_stage_progress(temp_project_dir, stage="docs", status="completed")
    save_bound_docs_confirmation(temp_project_dir, {"status": "confirmed", "actor": "pytest"})

    summary = detect_pipeline_summary(temp_project_dir)

    governance = summary["expert_governance"]
    assert governance["missing_stages"] == []
    assert governance["covered_count"] >= 3
    docs_stage = next(stage for stage in summary["stages"] if stage["canonical_id"] == "docs")
    docs_confirm_stage = next(
        stage for stage in summary["stages"] if stage["canonical_id"] == "docs_confirm"
    )
    assert docs_stage["expert_evidence_status"] == "recorded"
    assert "PM" in docs_stage["recorded_experts"]
    assert docs_confirm_stage["expert_evidence_status"] == "recorded"
    assert "PRODUCT" in docs_confirm_stage["recorded_experts"]


def test_detect_pipeline_summary_blocks_resume_mode_on_resume_gate(temp_project_dir: Path):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "resume"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_resume_gate(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "需要先确认恢复点",
            "actor": "pytest",
        },
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == "resume"
    assert summary["workflow_status"] == "waiting_resume_gate"
    assert summary["resume_gate"]["status"] == "pending_review"
    assert "恢复点" in summary["recommended_command"]


def test_detect_pipeline_summary_waits_for_baseline_confirmation(temp_project_dir: Path):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "evolve"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
        "# baseline\n", encoding="utf-8"
    )
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "需要先确认影响范围",
            "actor": "pytest",
        },
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == "evolve"
    assert summary["workflow_status"] == "waiting_baseline_confirmation"
    assert summary["baseline_confirmation"]["status"] == "pending_review"
    assert summary["current_stage_canonical_id"] == "baseline"
    assert "baseline" in summary["recommended_command"]


def test_detect_pipeline_summary_resume_gate_precedes_missing_baseline_for_existing_project(
    temp_project_dir: Path,
):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "variant"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_resume_gate(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "先确认从哪个阶段恢复",
            "actor": "pytest",
        },
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == "variant"
    assert summary["artifacts"]["baseline_required"] is True
    assert summary["artifacts"]["baseline"] is False
    assert summary["workflow_status"] == "waiting_resume_gate"
    assert summary["resume_gate"]["status"] == "pending_review"


def test_detect_pipeline_summary_waits_for_baseline_confirmation_after_audit(
    temp_project_dir: Path,
):
    superdev_dir = temp_project_dir / ".super-dev"
    review_state_dir = superdev_dir / "review-state"
    output_dir = temp_project_dir / "output"
    review_state_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    (superdev_dir / "workflow-state.json").write_text(
        json.dumps({"work_mode": "evolve"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{temp_project_dir.name}-baseline-audit.md").write_text(
        "# baseline\n",
        encoding="utf-8",
    )
    save_baseline_confirmation(
        temp_project_dir,
        {
            "status": "pending_review",
            "comment": "先确认当前项目边界和差量计划",
            "actor": "pytest",
        },
    )

    summary = detect_pipeline_summary(temp_project_dir)

    assert summary["work_mode"] == "evolve"
    assert summary["artifacts"]["baseline_required"] is True
    assert summary["artifacts"]["baseline"] is True
    assert summary["workflow_status"] == "waiting_baseline_confirmation"
    assert summary["current_stage_canonical_id"] == "baseline"
    assert "baseline 确认" in summary["recommended_command"]
    assert any(card["id"] == "baseline_confirmation" for card in summary["scenario_cards"])
