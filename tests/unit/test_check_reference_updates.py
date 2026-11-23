"""Unit tests for scripts/check_reference_updates.py"""

import os
import sys

# Ensure scripts dir is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts")))

from check_reference_updates import classify_changes, matches_any_pattern, render_markdown_report


def test_matches_any_pattern():
    watch = ["skills/", "prompts/"]
    assert matches_any_pattern("skills/my_skill/SKILL.md", watch)
    assert matches_any_pattern("prompts/templates/pm.md", watch)
    assert not matches_any_pattern("tests/unit/test.py", watch)

    ignore = [".github/", "*.lock", "*lock*"]
    assert matches_any_pattern(".github/workflows/ci.yml", ignore)
    assert matches_any_pattern("yarn.lock", ignore)
    assert matches_any_pattern("package-lock.json", ignore)
    assert not matches_any_pattern("src/main.py", ignore)


def test_classify_changes_ignored_when_only_ignore_paths():
    files = [{"filename": ".github/workflows/ci.yml"}, {"filename": "tests/test_foo.py"}]
    commits = [{"commit": {"message": "ci: update node version"}}]
    watch = ["skills/"]
    ignore = [".github/", "tests/"]

    cat, reason, touched = classify_changes(files, commits, watch, ignore)
    assert cat == "ignored"
    assert len(touched) == 0


def test_classify_changes_actionable_when_watch_hit_and_feat_commit():
    files = [{"filename": "skills/forge/SKILL.md"}]
    commits = [{"commit": {"message": "feat: introduce hypothesis testing rule"}}]
    watch = ["skills/"]
    ignore = [".github/"]

    cat, reason, touched = classify_changes(files, commits, watch, ignore)
    assert cat == "actionable"
    assert len(touched) == 1
    assert "skills/forge/SKILL.md" in touched


def test_classify_changes_watch_when_minor_watch_touch():
    files = [{"filename": "skills/misc/note.txt"}]
    commits = [{"commit": {"message": "docs: update typo"}}]
    watch = ["skills/"]
    ignore = [".github/"]

    cat, reason, touched = classify_changes(files, commits, watch, ignore)
    assert cat == "watch"
    assert len(touched) == 1


def test_render_markdown_report_structure():
    mock_results = [
        {
            "id": "REF-014",
            "name": "oil-tone",
            "type": "github_repo",
            "status": "up_to_date",
            "message": "当前已对齐基线 (39cbf92)",
            "new_commit": "39cbf92f76c90b7bb27a5b5d4ed88a1fc5fa31f6",
            "old_commit": "39cbf92f76c90b7bb27a5b5d4ed88a1fc5fa31f6",
            "commits_count": 0,
            "commits": [],
            "files_changed": [],
            "details": "",
        },
        {
            "id": "REF-003",
            "name": "BMAD Method",
            "type": "github_repo",
            "status": "actionable",
            "message": "命中关注路径且包含重要功能演化",
            "new_commit": "abcdef1234567890",
            "old_commit": "94b6727b00c83165",
            "commits_count": 3,
            "commits": [
                {"sha": "abcdef1", "message": "feat: new prompt schema", "author": "Alice", "date": "2026-11-23"}
            ],
            "files_changed": ["docs/plan/new.md"],
            "details": "",
        },
    ]

    report = render_markdown_report(mock_results, "2026-11-23 22:30:00 UTC")
    assert "# 🔍 Super Dev 外部参考源上游巡检报告" in report
    assert "REF-014" in report
    assert "REF-003" in report
    assert "🟢 建议跟进" in report
    assert "docs/plan/new.md" in report
    assert "docs/CONTRIBUTION_POLICY.md" in report
