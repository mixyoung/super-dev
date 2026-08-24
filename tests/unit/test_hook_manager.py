import sys
import time
from pathlib import Path

import yaml

from super_dev.hooks.manager import HookManager
from super_dev.review_state import save_docs_confirmation


def test_workflow_event_hook_dispatches_from_review_state(tmp_path: Path) -> None:
    project_dir = tmp_path / "demo"
    project_dir.mkdir(parents=True, exist_ok=True)
    marker = project_dir / "workflow-hook.txt"
    (project_dir / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "hooks": {
                    "WorkflowEvent": [
                        {
                            "matcher": "docs_confirmation_saved",
                            "type": "command",
                            "command": {
                                "executable": sys.executable,
                                "args": [
                                    "-c",
                                    (
                                        "from pathlib import Path; import os; "
                                        f"Path(r'{marker}').write_text("
                                        "os.environ.get('SUPER_DEV_PHASE', ''), encoding='utf-8')"
                                    ),
                                ],
                            },
                            "blocking": False,
                        }
                    ]
                }
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    save_docs_confirmation(
        project_dir,
        {
            "status": "confirmed",
            "current_step_label": "三文档已确认",
        },
    )

    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "docs_confirmation_saved"

    history = HookManager.load_recent_history(project_dir, limit=5)
    assert history
    latest = history[0]
    assert latest.event == "WorkflowEvent"
    assert latest.phase == "docs_confirmation_saved"
    assert latest.source == "config"
    assert latest.success is True


def test_legacy_command_string_is_blocked_without_execution(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist.txt"
    config = {
        "WorkflowEvent": [
            {
                "type": "command",
                "command": f"python -c \"open(r'{marker}', 'w').write('bad')\"",
                "blocking": True,
            }
        ]
    }
    manager = HookManager.from_yaml_config({"hooks": config}, project_dir=tmp_path)

    results = manager.execute("WorkflowEvent", phase="demo")

    assert len(results) == 1
    assert results[0].blocked is True
    assert results[0].success is False
    assert "command.executable" in results[0].error
    assert not marker.exists()


def test_yaml_python_hook_returns_migration_guidance(tmp_path: Path) -> None:
    manager = HookManager.from_yaml_config(
        {
            "hooks": {
                "WorkflowEvent": [
                    {
                        "type": "python",
                        "command": "package.module:function",
                        "blocking": True,
                    }
                ]
            }
        },
        project_dir=tmp_path,
    )

    result = manager.execute("WorkflowEvent", phase="demo")[0]

    assert result.blocked is True
    assert "Python callback" in result.error


def test_structured_hook_rejects_unknown_command_fields(tmp_path: Path) -> None:
    manager = HookManager.from_yaml_config(
        {
            "hooks": {
                "WorkflowEvent": [
                    {
                        "type": "command",
                        "command": {
                            "executable": sys.executable,
                            "args": [],
                            "shell": True,
                        },
                    }
                ]
            }
        },
        project_dir=tmp_path,
    )

    result = manager.execute("WorkflowEvent", phase="demo")[0]

    assert result.blocked is True
    assert "未知字段" in result.error


def test_structured_hook_rejects_invalid_control_fields(tmp_path: Path) -> None:
    manager = HookManager.from_yaml_config(
        {
            "hooks": {
                "WorkflowEvent": [
                    {
                        "type": "mystery",
                        "command": {"executable": sys.executable, "args": []},
                        "timeout": "forever",
                        "blocking": "false",
                    }
                ]
            }
        },
        project_dir=tmp_path,
    )

    result = manager.execute("WorkflowEvent", phase="demo")[0]

    assert result.blocked is True
    assert "未知 Hook 类型" in result.error
    assert "timeout" in result.error
    assert "blocking" in result.error


def test_non_blocking_hook_timeout_reports_failure_without_blocking(tmp_path: Path) -> None:
    manager = HookManager.from_yaml_config(
        {
            "hooks": {
                "WorkflowEvent": [
                    {
                        "type": "command",
                        "command": {
                            "executable": sys.executable,
                            "args": ["-c", "import time; time.sleep(2)"],
                        },
                        "timeout": 1,
                        "blocking": False,
                    }
                ]
            }
        },
        project_dir=tmp_path,
    )

    started = time.monotonic()
    result = manager.execute("WorkflowEvent", phase="demo")[0]

    assert time.monotonic() - started < 2
    assert result.success is False
    assert result.blocked is False
    assert "超时" in result.error
