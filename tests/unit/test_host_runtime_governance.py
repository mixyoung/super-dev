import json
from pathlib import Path

from super_dev.host_runtime_governance import collect_layered_runtime_governance_gap
from super_dev.review_state import save_host_runtime_validation, save_workflow_state


def _write_framework_gap(project_dir: Path) -> None:
    (project_dir / "super-dev.yaml").write_text(
        "name: demo\nplatform: web\nfrontend: uni-app\nbackend: python\n",
        encoding="utf-8",
    )
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "demo-ui-contract.json").write_text(
        json.dumps(
            {
                "analysis": {"frontend": "uni-app"},
                "framework_playbook": {
                    "framework": "uni-app",
                    "implementation_modules": ["navigation"],
                    "platform_constraints": ["safe area"],
                    "execution_guardrails": ["freeze pages.json"],
                    "native_capabilities": ["login provider"],
                    "validation_surfaces": ["mini-program navigation"],
                    "delivery_evidence": ["platform matrix"],
                },
            }
        ),
        encoding="utf-8",
    )


def test_collect_layered_runtime_governance_gap_returns_impacted_hosts(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True, exist_ok=True)
    _write_framework_gap(project_dir)
    save_workflow_state(
        project_dir,
        {
            "status": "missing_frontend",
            "workflow_mode": "continue",
            "current_step_label": "先做前端与运行验证",
            "recommended_command": "继续当前流程，进入前端实现与运行验证",
        },
    )
    save_host_runtime_validation(
        project_dir,
        {
            "hosts": {
                "codex-cli": {"status": "passed", "comment": "ok", "actor": "pytest"},
                "claude-code": {"status": "pending", "comment": "", "actor": "pytest"},
            }
        },
    )

    gap = collect_layered_runtime_governance_gap(project_dir)

    assert gap["status"] == "attention"
    assert gap["impacted_hosts"] == ["codex-cli"]
    assert "codex-cli" in gap["summary"]
    assert gap["next_actions"]


def test_collect_layered_runtime_governance_gap_respects_target_filter(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True, exist_ok=True)
    _write_framework_gap(project_dir)
    save_workflow_state(
        project_dir,
        {
            "status": "missing_frontend",
            "workflow_mode": "continue",
            "current_step_label": "先做前端与运行验证",
            "recommended_command": "继续当前流程，进入前端实现与运行验证",
        },
    )
    save_host_runtime_validation(
        project_dir,
        {
            "hosts": {
                "codex-cli": {"status": "passed", "comment": "ok", "actor": "pytest"},
                "opencode": {"status": "passed", "comment": "ok", "actor": "pytest"},
            }
        },
    )

    gap = collect_layered_runtime_governance_gap(project_dir, targets=["opencode"])

    assert gap["impacted_hosts"] == ["opencode"]
    assert "opencode" in gap["summary"]
