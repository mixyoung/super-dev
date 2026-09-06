"""Read-only contribution record checks; not semantic approval or a workflow runtime."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from io import TextIOWrapper
from pathlib import Path, PurePosixPath

POLICY = "docs/CONTRIBUTION_POLICY.md"
CASES = "tests/fixtures/knowledge_adoption_cases.json"
ENTRYPOINTS = (
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/CLAUDE.md",
    "CONTRIBUTING.md",
    "README.md",
    "README_EN.md",
)
SECTIONS = (
    "问题与现有覆盖",
    "来源与适用条件",
    "取舍与核心影响",
    "改动范围",
    "验证与未验证",
    "决定与回退",
)
CONTROLLED_PREFIXES = (
    "knowledge/",
    "super_dev/experts/",
    "super_dev/skills/",
    "super_dev/specs/",
    "super_dev/creators/",
    "super_dev/orchestrator/",
    "super_dev/enforcement/",
    "super_dev/reviewers/",
    "super_dev/extensions/",
    ".agents/skills/",
    ".claude/skills/",
    "plugins/",
    ".github/",
)
CONTROLLED_FILES = {
    POLICY,
    CASES,
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/CLAUDE.md",
    "CONTRIBUTING.md",
    "docs/SUPER_DEV_EXTENSION_PLATFORM_PLAN.md",
    "super_dev/stage_policy.py",
    "scripts/check_contribution_policy.py",
    "scripts/sync_super_dev_skills.py",
    "tests/unit/test_contribution_policy.py",
}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout


def changed_paths(root: Path, base: str) -> set[str]:
    # Resolve first: missing history must not silently become a successful empty diff.
    sha = git(root, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}").strip()
    tracked = git(root, "diff", "--name-only", "--no-renames", "-z", sha, "--")
    untracked = git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return set(filter(None, (tracked + untracked).split("\0")))


def read_local(root: Path, relative: str) -> str:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"越界引用: {relative}")
    return target.read_text(encoding="utf-8")


def is_controlled(path: str) -> bool:
    return (
        path in CONTROLLED_FILES
        or path.startswith(CONTROLLED_PREFIXES)
        or (path.startswith("super_dev/workflow") and path.endswith(".py"))
    )


def record_scope(body: str) -> set[str]:
    sections = re.findall(r"^## ([^\n]+)\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    by_name: dict[str, str] = {}
    for title, text in sections:
        if title in by_name:
            raise ValueError(f"重复章节: {title}")
        by_name[title] = text.strip()
    missing = [title for title in SECTIONS if not by_name.get(title)]
    if missing:
        raise ValueError(f"记录缺少非空章节: {', '.join(missing)}")
    paths = set()
    for line in by_name["改动范围"].splitlines():
        if not line.startswith("- "):
            raise ValueError("改动范围须逐行使用 '- 仓库相对文件路径'")
        path = line[2:].strip()
        parsed = PurePosixPath(path)
        if (
            not parsed.parts
            or path != parsed.as_posix()
            or parsed.is_absolute()
            or ".." in parsed.parts
            or any(char in path for char in "\\:*?`")
        ):
            raise ValueError(f"非法范围路径: {path}")
        paths.add(path)
    if not paths:
        raise ValueError("改动范围不能为空")
    return paths


def validate_cases(body: str) -> None:
    data = json.loads(body)
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("行为基准版本须为 1")
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("行为基准缺少 cases 列表")
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("行为案例须为对象")
        identifier = case.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError("行为案例 ID 为空或重复")
        ids.add(identifier)
        if not isinstance(case.get("task"), str) or not case["task"].strip():
            raise ValueError(f"{identifier}: 缺少任务")
        for field in ("facts", "expected", "forbidden"):
            values = case.get(field)
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(value, str) and value.strip() for value in values)
            ):
                raise ValueError(f"{identifier}: {field} 须为非空文本列表")
    if not {f"K{i:02}" for i in range(1, 9)}.issubset(ids):
        raise ValueError("缺少 K01—K08 基线案例；基准变更须单独审查")


def check(root: Path, changed: set[str]) -> list[str]:
    errors: list[str] = []
    try:
        if not read_local(root, POLICY).strip():
            errors.append("贡献准则为空")
        for entry in ENTRYPOINTS:
            if POLICY not in read_local(root, entry):
                errors.append(f"缺少贡献准则入口: {entry}")
        validate_cases(read_local(root, CASES))
    except (OSError, ValueError) as exc:
        errors.append(str(exc))

    covered: set[str] = set()
    owners: dict[str, str] = {}
    for path in sorted(changed):
        if (
            re.fullmatch(r"\.super-dev/changes/[^/]+/adoption\.md", path)
            and (root / path).is_file()
        ):
            try:
                scope = record_scope(read_local(root, path))
                for target in scope:
                    if target in changed and is_controlled(target):
                        if target in owners:
                            errors.append(f"范围归属重复: {target} ({owners[target]}, {path})")
                        owners[target] = path
                covered.update(scope)
            except (OSError, ValueError) as exc:
                errors.append(f"{path}: {exc}")
    missing = {path for path in changed if is_controlled(path)} - covered
    if missing:
        errors.append("以下改动缺少本批 adoption.md 范围记录: " + ", ".join(sorted(missing)))
    return errors


def main() -> int:
    # Redirected Windows streams may start as cp1252 even when files use UTF-8.
    # Configure only the CLI process; importing the checker must not alter host streams.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", default=os.environ.get("CONTRIBUTION_BASE", "HEAD"))
    args = parser.parse_args()
    root = args.project_dir.resolve()
    try:
        errors = check(root, changed_paths(root, args.base))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        errors = [f"无法确认 Git 基线或读取贡献资料: {exc}"]
    for error in errors:
        print(f"失败（FAIL）: {error}")
    if not errors:
        print("通过（PASS）: 贡献资料与范围检查；不代表语义审查、用户批准或可发布")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
