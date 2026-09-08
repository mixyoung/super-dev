from __future__ import annotations

import json

import pytest

from super_dev.hook_harness import HookHarnessBuilder
from super_dev.hooks.manager import HookManager
from super_dev.hooks.models import HookResult
from super_dev.release_readiness import (
    ReleaseReadinessCheck,
    ReleaseReadinessEvaluator,
    ReleaseReadinessReport,
)
from super_dev.skills.skill_template import SkillTemplate


def test_release_spec_uses_bound_change_without_legacy_layout(tmp_path):
    current = tmp_path / ".super-dev/changes/current-fix"
    current.mkdir(parents=True)
    (current / "proposal.md").write_text("# Proposal\n")
    (current / "tasks.md").write_text("# Tasks\n")
    (tmp_path / ".super-dev/workflow-state.json").write_text(
        json.dumps({"active_change_id": "current-fix"})
    )
    evaluator = ReleaseReadinessEvaluator(tmp_path)
    check = evaluator._check_release_spec_exists()
    assert check.passed
    assert "current-fix" in check.detail
    (current / "tasks.md").unlink()
    assert not evaluator._check_release_spec_exists().passed


def test_release_spec_does_not_guess_from_old_directory(tmp_path):
    old = tmp_path / ".super-dev/changes/release-hardening-finalization"
    old.mkdir(parents=True)
    for name in ("change.yaml", "proposal.md", "tasks.md"):
        (old / name).write_text("old\n")
    assert not ReleaseReadinessEvaluator(tmp_path)._check_release_spec_exists().passed


def test_governance_inventory_is_not_pass_evidence_or_score(tmp_path):
    evaluator = ReleaseReadinessEvaluator(tmp_path)
    before = evaluator._governance_artifact_notes()
    (tmp_path / "output/governance-report-other-change.md").write_text("not a valid report")
    notes = evaluator._governance_artifact_notes()
    assert notes != before
    assert all("不计分" in note for note in notes)
    checks = [ReleaseReadinessCheck("real test", True, "executed", "critical")]
    report = ReleaseReadinessReport("demo", checks=checks, governance_notes=notes)
    assert report.score == 100
    assert report.passed
    assert report.to_dict()["governance_notes"] == notes
    assert "不计分" in report.to_markdown()
    checks[0].passed = False
    assert not report.passed
    assert report.threshold == 85


@pytest.mark.parametrize("difference", [None, "hook_name", "phase", "event", "source"])
def test_only_matching_later_hook_success_resolves_failure(tmp_path, difference):
    failure = HookResult(
        "python check.py", "PostPhase", False, blocked=True, phase="quality", source="config"
    )
    success = HookResult("python check.py", "PostPhase", True, phase="quality", source="config")
    if difference:
        setattr(success, difference, "unrelated")
    history = HookManager.hook_history_file(tmp_path)
    history.parent.mkdir(parents=True)
    history.write_text("\n".join(json.dumps(x.to_dict()) for x in (failure, success)) + "\n")
    original = history.read_bytes()
    assert ReleaseReadinessEvaluator(tmp_path)._check_hook_audit_trail().passed is (
        difference is None
    )
    harness = HookHarnessBuilder(tmp_path).build()
    assert harness.passed is (difference is None)
    assert harness.blocked_count == 1  # history is still visible, not rewritten
    assert len(harness.recent_events) == 2
    assert history.read_bytes() == original


def test_latest_hook_failure_still_blocks(tmp_path):
    history = HookManager.hook_history_file(tmp_path)
    history.parent.mkdir(parents=True)
    records = [
        HookResult("check", "PrePhase", True),
        HookResult("check", "PrePhase", False, blocked=True),
    ]
    history.write_text("\n".join(json.dumps(x.to_dict()) for x in records))
    assert not ReleaseReadinessEvaluator(tmp_path)._check_hook_audit_trail().passed
    assert not HookHarnessBuilder(tmp_path).build().passed


def test_unidentified_hook_cannot_be_resolved_by_another_unknown_success():
    failure = HookResult("", "", False, blocked=True)
    success = HookResult("", "", True)
    assert failure in HookManager.latest_results([success, failure])


@pytest.mark.parametrize("host", ["codex", "claude-code"])
def test_skill_keeps_gates_but_routes_resume_and_non_ui_work(host):
    template = SkillTemplate.for_builtin("super-dev", host)
    text = template.render(host)
    assert "恢复已有流程" in text
    assert "不得重置为 research" in text
    assert "仅当本轮涉及 UI" in text
    assert "DOC_CONFIRM_GATE: required" in text
    assert "PREVIEW_CONFIRM_GATE: required" in text
    assert "未经确认不创建 Spec" in text
