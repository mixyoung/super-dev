"""Regression evidence for the approved Windows/readiness/performance fixes."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from super_dev.host_diagnostics import collect_host_diagnostics
from super_dev.integrations.manager import IntegrationManager
from super_dev.orchestrator.governance import PipelineGovernance
from super_dev.reviewers import validation_rules


@pytest.mark.parametrize("script", ["check_delivery_ready.py", "check_host_compatibility.py"])
def test_gate_stdout_is_utf8_even_with_legacy_pipe_encoding(tmp_path, script):
    path = tmp_path / "fixture.json"
    path.write_text(
        json.dumps(
            {
                "status": "ready",
                "missing_required": [],
                "included_files": ["中文.md"],
                "compatibility": {"overall_score": 90, "ready_hosts": 1, "total_hosts": 1},
            }
        ),
        encoding="utf-8",
    )
    option = "--manifest" if script == "check_delivery_ready.py" else "--report"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[2] / "scripts" / script),
            "--project-dir",
            str(tmp_path),
            option,
            str(path),
        ],
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "通过" in result.stdout


def test_governance_indexes_target_project_not_callers_working_directory(tmp_path, monkeypatch):
    target = tmp_path / "target"
    caller = tmp_path / "caller"
    for directory, title in [(target, "target"), (caller, "caller")]:
        (directory / "knowledge").mkdir(parents=True)
        (directory / "knowledge" / f"{title}.md").write_text(f"# {title}", encoding="utf-8")
    monkeypatch.chdir(caller)
    governance = PipelineGovernance(target)
    indexed = governance.knowledge_tracker._knowledge_index
    assert str(Path("knowledge/target.md")) in indexed
    assert str(Path("knowledge/caller.md")) not in indexed


def test_rule_cache_avoids_reparse_but_keeps_instances_and_changes_isolated(tmp_path):
    path = tmp_path / "rules.yaml"
    original = "rules:\n  - id: CACHE-READINESS\n    name: original\n    category: testing\n    severity: high\n    check_config: {items: [original]}\n"
    path.write_text(original, encoding="utf-8")
    with patch.object(
        validation_rules.yaml, "safe_load", wraps=validation_rules.yaml.safe_load
    ) as parse:
        first = validation_rules._load_rules_from_yaml(path)
        count = parse.call_count
        second = validation_rules._load_rules_from_yaml(path)
        assert count == 1
        assert parse.call_count == count
    first[0].name = "mutated"
    first[0].check_config["items"].append("mutated")
    assert second[0].name == "original"
    assert second[0].check_config["items"] == ["original"]
    stamp = path.stat()
    path.write_text(original.replace("original", "modified"), encoding="utf-8")
    os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert validation_rules._load_rules_from_yaml(path)[0].name == "modified"
    path.unlink()
    assert validation_rules._load_rules_from_yaml(path) == []


def test_project_only_host_is_ready_without_optional_user_skill(tmp_path):
    manager = IntegrationManager(tmp_path)
    manager.setup("claude-code")
    groups = manager.readiness_surface_sets(target="claude-code")
    report = collect_host_diagnostics(
        project_dir=tmp_path,
        targets=["claude-code"],
        skill_name="super-dev",
        check_integrate=True,
        check_skill=True,
        check_slash=True,
        build_usage_profile_fn=lambda *_: {},
    )["hosts"]["claude-code"]
    assert report["checks"]["skill"]["ok"] is True
    assert report["ready"] is True
    assert all(path.is_relative_to(tmp_path) for path in groups["official_skill"])
    assert report["injection_closure"]["standard_flow_ready"] is True
    assert report["injection_closure"]["explicit_user_surfaces_ready"] is False
    skill = tmp_path / ".claude/skills/super-dev/SKILL.md"
    skill.unlink()
    broken = collect_host_diagnostics(
        project_dir=tmp_path,
        targets=["claude-code"],
        skill_name="super-dev",
        check_integrate=True,
        check_skill=True,
        check_slash=True,
        build_usage_profile_fn=lambda *_: {},
    )["hosts"]["claude-code"]
    assert broken["ready"] is False
    assert broken["checks"]["skill"]["ok"] is False
    skill.write_text("not the Super Dev contract", encoding="utf-8")
    invalid = collect_host_diagnostics(
        project_dir=tmp_path,
        targets=["claude-code"],
        skill_name="super-dev",
        check_integrate=True,
        check_skill=True,
        check_slash=True,
        build_usage_profile_fn=lambda *_: {},
    )["hosts"]["claude-code"]
    assert invalid["checks"]["contract"]["ok"] is False
    assert invalid["injection_closure"]["standard_flow_ready"] is False


def test_windows_bash_resolution_prefers_git_and_rejects_wsl_shim(tmp_path, monkeypatch):
    from super_dev.utils import shell

    monkeypatch.setattr(shell, "sys", SimpleNamespace(platform="win32"))
    git = tmp_path / "Git/cmd/git.exe"
    bash = tmp_path / "Git/bin/bash.exe"
    for executable in (git, bash):
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.touch()
    shim = tmp_path / "Windows/System32/bash.exe"
    monkeypatch.setattr(shell.shutil, "which", lambda name: str(git if name == "git" else shim))
    assert Path(shell.resolve_bash()) == bash
    bash.unlink()
    with pytest.raises(FileNotFoundError, match="Git Bash"):
        shell.resolve_bash()


@pytest.mark.parametrize("passed,code", [(True, 0), (False, 1)])
def test_benchmark_exit_code_matches_threshold_result(monkeypatch, passed, code):
    from tests import benchmark

    suite = SimpleNamespace(
        run_all=lambda: passed,
        benchmark=SimpleNamespace(console=None),
    )
    monkeypatch.setattr(benchmark, "BenchmarkSuite", lambda _: suite)
    assert benchmark.main() == code
