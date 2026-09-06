"""Mechanical checks must reject missing evidence structure without judging its meaning."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.check_contribution_policy import (
    CASES,
    ENTRYPOINTS,
    POLICY,
    SECTIONS,
    changed_paths,
    check,
    git,
    read_local,
    record_scope,
    validate_cases,
)

ROOT = Path(__file__).resolve().parents[2]
NOTE = ".super-dev/changes/example/adoption.md"


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def record(*paths: str) -> str:
    return "\n\n".join(
        f"## {section}\n"
        + (
            "\n".join(f"- {p}" for p in paths)
            if section == "改动范围"
            else "实际依据；不代表程序验证其语义。"
        )
        for section in SECTIONS
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    write(tmp_path, POLICY, "# Policy\n实际政策")
    for entry in ENTRYPOINTS:
        write(tmp_path, entry, f"Read {POLICY}")
    write(tmp_path, CASES, (ROOT / CASES).read_text(encoding="utf-8"))
    return tmp_path


def test_unrelated_edit_needs_no_adoption_record(repo: Path) -> None:
    assert check(repo, {"example.txt"}) == []


def test_missing_entrypoint_is_detected(repo: Path) -> None:
    write(repo, "AGENTS.md", "unrelated instructions")
    assert any("AGENTS.md" in error for error in check(repo, set()))


def test_missing_record_fails_and_current_record_covers_change(repo: Path) -> None:
    paths = {"knowledge/example.md"}
    assert check(repo, paths)
    write(repo, NOTE, record(*paths))
    # A pre-existing unchanged note cannot silently authorize a new diff.
    assert check(repo, paths)
    assert check(repo, paths | {NOTE}) == []


def test_records_do_not_cover_unlisted_files(repo: Path) -> None:
    write(repo, NOTE, record("knowledge/a.md"))
    errors = check(repo, {NOTE, "knowledge/a.md", "knowledge/b.md"})
    assert any("knowledge/b.md" in error for error in errors)


def test_multiple_changes_cannot_claim_the_same_file(repo: Path) -> None:
    another = ".super-dev/changes/another/adoption.md"
    for note in (NOTE, another):
        write(repo, note, record("knowledge/a.md"))
    assert any("归属重复" in error for error in check(repo, {NOTE, another, "knowledge/a.md"}))


@pytest.mark.parametrize(
    "bad",
    [
        "../outside.md",
        "/absolute.md",
        "C:/x.md",
        "a\\b.md",
        "knowledge/*",
        "a/../b.md",
        "a//b.md",
        "`a.md`",
        ".",
    ],
)
def test_record_scope_rejects_ambiguous_or_escaping_paths(bad: str) -> None:
    with pytest.raises(ValueError):
        record_scope(record(bad))


def test_record_requires_nonempty_unique_sections() -> None:
    with pytest.raises(ValueError):
        record_scope(record("a.md").replace("## 来源与适用条件", "## 来源已删除"))
    with pytest.raises(ValueError):
        record_scope(record("a.md") + "\n\n## 决定与回退\n重复")


def test_scope_uses_literal_paths_not_glob_expansion() -> None:
    assert record_scope(record("pages/[id].tsx", "docs/中文 说明.md")) == {
        "pages/[id].tsx",
        "docs/中文 说明.md",
    }


def test_behavior_baseline_rejects_missing_duplicate_or_empty_cases() -> None:
    original = json.loads((ROOT / CASES).read_text(encoding="utf-8"))
    validate_cases(json.dumps(original))
    for mutation in ("missing", "duplicate", "empty"):
        data = json.loads(json.dumps(original))
        if mutation == "missing":
            data["cases"].pop()
        elif mutation == "duplicate":
            data["cases"].append(data["cases"][0])
        else:
            data["cases"][0]["expected"] = []
        with pytest.raises(ValueError):
            validate_cases(json.dumps(data))


def test_read_local_rejects_outside_path(repo: Path) -> None:
    with pytest.raises(ValueError):
        read_local(repo, "../outside.md")


def test_git_diff_tracks_committed_staged_unstaged_untracked_and_rename(repo: Path) -> None:
    git(repo, "init")
    hooks = repo / ".git" / "fixture-hooks"
    hooks.mkdir()
    write(repo, "knowledge/原文件.md", "baseline")
    write(repo, "knowledge/staged.md", "baseline")
    write(repo, "knowledge/unstaged.md", "baseline")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        f"core.hooksPath={hooks}",
        "commit",
        "-m",
        "fixture baseline",
    )
    base = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "mv", "knowledge/原文件.md", "knowledge/新文件.md")
    write(repo, "knowledge/staged.md", "staged")
    git(repo, "add", "knowledge/staged.md")
    write(repo, "knowledge/unstaged.md", "unstaged")
    write(repo, "knowledge/untracked.md", "untracked")
    expected = {
        "knowledge/原文件.md",
        "knowledge/新文件.md",
        "knowledge/staged.md",
        "knowledge/unstaged.md",
        "knowledge/untracked.md",
    }
    assert changed_paths(repo, base) == expected
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        f"core.hooksPath={hooks}",
        "commit",
        "-m",
        "fixture change",
    )
    assert changed_paths(repo, base) == expected
    with pytest.raises(subprocess.CalledProcessError):
        changed_paths(repo, "nonexistent-base")
    before = git(repo, "status", "--porcelain")
    changed_paths(repo, base)
    assert git(repo, "status", "--porcelain") == before


def test_cli_invalid_baseline_returns_failure(repo: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_contribution_policy.py"),
            "--project-dir",
            str(repo),
            "--base",
            "nonexistent",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 1


def test_ci_uses_failing_checks_without_privileged_pr_context() -> None:
    workflow = yaml.load(
        (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    assert "pull_request_target" not in workflow["on"]
    job = workflow["jobs"]["contribution-policy"]
    assert job["permissions"] == {"contents": "read"}
    assert set(job["strategy"]["matrix"]["os"]) == {"ubuntu-latest", "windows-latest"}
    steps = job["steps"]
    checkout = steps[0]["with"]
    assert checkout["fetch-depth"] == "0"
    assert checkout["persist-credentials"] == "false"
    commands = [step["run"] for step in steps if "run" in step]
    assert "python scripts/check_contribution_policy.py" in commands
    assert "python scripts/sync_super_dev_skills.py" in commands
    assert all("continue-on-error" not in step for step in steps)
    assert all("|| true" not in command for command in commands)
