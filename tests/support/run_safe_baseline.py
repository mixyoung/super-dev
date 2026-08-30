"""跨平台安全测试基线入口。

成功状态只表示真实用户目录安全且证据完整；测试是否全部通过由独立字段报告。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import signal
import subprocess
import sys
import sysconfig
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from defusedxml import ElementTree

from super_dev.user_directories import UserDirectoryContext
from tests.support.user_surface_snapshot import (
    SurfaceState,
    assert_safe_isolated_home,
    capture_user_surfaces,
    collect_user_surface_paths,
    diff_surface_snapshots,
    has_surface_changes,
    path_is_within,
    unsafe_surface_states,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROOT = PROJECT_ROOT / ".super-dev" / "baselines" / "windows-test-foundation"

MODE_SELECTORS: dict[str, tuple[str, ...]] = {
    "isolation-smoke": (
        "tests/unit/test_user_directories.py",
        "tests/unit/test_user_surface_snapshot.py",
    ),
    "user-surfaces": (
        "tests/unit/test_skill_manager.py",
        "tests/unit/test_integration_manager.py",
    ),
    "windows-focused": (
        "tests/unit/test_hook_manager.py",
        "tests/unit/test_knowledge.py",
        "tests/unit/test_knowledge_gates.py",
        "tests/unit/test_skill_manager.py",
        "tests/unit/test_integration_manager.py",
    ),
    "unit": ("tests/unit",),
    "repeatability": ("tests/unit",),
}

MODE_LABELS = {
    "isolation-smoke": "隔离自检",
    "user-surfaces": "用户目录检查",
    "windows-focused": "Windows 定向检查",
    "unit": "完整单元检查",
    "repeatability": "重复性检查",
}

MODE_EXECUTION_PLAN: dict[str, tuple[str, ...]] = {
    "isolation-smoke": ("isolation-smoke",),
    "user-surfaces": ("isolation-smoke", "user-surfaces"),
    "windows-focused": ("isolation-smoke", "user-surfaces", "windows-focused"),
    "unit": ("isolation-smoke", "user-surfaces", "unit"),
    "repeatability": (
        "isolation-smoke",
        "user-surfaces",
        "repeatability",
        "repeatability",
    ),
}


@dataclass(frozen=True)
class PytestRun:
    index: int
    mode: str
    command: list[str]
    returncode: int
    timed_out: bool
    junit_file: str
    output_file: str
    passed: int
    failed: int
    skipped: int
    errors: int
    failures: list[str]


def _utc_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _isolated_pytest_pythonpath() -> str:
    spec = importlib.util.find_spec("pytest")
    origin = Path(spec.origin).resolve() if spec and spec.origin else None
    package_root = origin.parent.parent if origin is not None else None
    if package_root is None or not package_root.is_dir():
        raise RuntimeError("当前 Python 环境没有可用的 pytest")
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    return os.pathsep.join([str(stdlib), str(package_root)])


def _git_value(*args: str) -> str:
    completed = subprocess.run(  # nosec B603
        ["git", "-C", str(PROJECT_ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(  # nosec B603
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
        if process.poll() is None:
            process.kill()
    else:
        kill_process_group = getattr(os, "killpg", None)
        sigkill = getattr(signal, "SIGKILL", signal.SIGTERM)
        if kill_process_group is None:
            process.kill()
        else:
            kill_process_group(process.pid, sigkill)


def _failure_ids(junit_file: Path) -> list[str]:
    if not junit_file.exists():
        return []
    root = ElementTree.parse(junit_file).getroot()
    failures: list[str] = []
    for case in root.iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue
        class_name = case.attrib.get("classname", "")
        name = case.attrib.get("name", "")
        failures.append(f"{class_name}::{name}" if class_name else name)
    return sorted(failures)


def _junit_counts(junit_file: Path) -> dict[str, int]:
    if not junit_file.exists():
        return {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    root = ElementTree.parse(junit_file).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(suite.attrib.get("tests", 0)) for suite in suites)
    failed = sum(int(suite.attrib.get("failures", 0)) for suite in suites)
    errors = sum(int(suite.attrib.get("errors", 0)) for suite in suites)
    skipped = sum(int(suite.attrib.get("skipped", 0)) for suite in suites)
    return {
        "passed": max(tests - failed - errors - skipped, 0),
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
    }


def _run_pytest(
    *,
    mode: str,
    index: int,
    output_dir: Path,
    isolated_environment: dict[str, str],
    base_temp: Path,
    timeout_seconds: int,
) -> PytestRun:
    junit_file = output_dir / f"pytest-{index}.xml"
    output_file = output_dir / f"pytest-output-{index}.txt"
    command = [
        sys.executable,
        "-m",
        "pytest",
        *MODE_SELECTORS[mode],
        "-q",
        f"--junitxml={junit_file}",
        f"--basetemp={base_temp}",
    ]
    if os.name == "nt":
        process = subprocess.Popen(  # nosec B603
            command,
            cwd=str(PROJECT_ROOT),
            env=isolated_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        process = subprocess.Popen(  # nosec B603
            command,
            cwd=str(PROJECT_ROOT),
            env=isolated_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    timed_out = False
    try:
        output, _ = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_tree(process)
        output, _ = process.communicate()
    output_file.write_text(output or "", encoding="utf-8")
    counts = _junit_counts(junit_file)
    return PytestRun(
        index=index,
        mode=mode,
        command=command,
        returncode=process.returncode if process.returncode is not None else 1,
        timed_out=timed_out,
        junit_file=str(junit_file),
        output_file=str(output_file),
        passed=counts["passed"],
        failed=counts["failed"],
        skipped=counts["skipped"],
        errors=counts["errors"],
        failures=_failure_ids(junit_file),
    )


def _write_snapshot(path: Path, states: Mapping[str, SurfaceState]) -> None:
    payload = {
        key: value.to_dict() if hasattr(value, "to_dict") else value
        for key, value in states.items()
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_output_dir(output_dir: Path) -> Path:
    resolved = Path(output_dir).resolve(strict=False)
    if resolved == PROJECT_ROOT or not path_is_within(resolved, PROJECT_ROOT):
        raise ValueError(
            f"output directory must be a dedicated path inside the project: {resolved}"
        )
    return resolved


def _summary_markdown(
    *,
    mode: str,
    safety_result: str,
    test_result: str,
    evidence_result: str,
    repeatable: bool | None,
    surface_diff: dict[str, list[str]],
    runs: list[PytestRun],
) -> str:
    repeatable_label = "不适用" if repeatable is None else ("是" if repeatable else "否")
    return "\n".join(
        [
            "# Windows 测试基础检查",
            "",
            f"- 检查范围：{MODE_LABELS[mode]}（`{mode}`）",
            f"- 隔离安全：{'是' if safety_result == 'safe' else '否'}",
            f"- 证据完整：{'是' if evidence_result == 'complete' else '否'}",
            f"- 测试全部通过：{'是' if test_result == 'pass' else '否'}",
            f"- 重复结果一致：{repeatable_label}",
            f"- 真实用户目录变化：{sum(len(items) for items in surface_diff.values())}",
            "",
            "## 运行结果",
            "",
            *[
                (
                    f"- 第 {run.index} 次（{MODE_LABELS[run.mode]}）："
                    f"通过 {run.passed}，失败 {run.failed}，"
                    f"错误 {run.errors}，跳过 {run.skipped}，退出码 {run.returncode}"
                )
                for run in runs
            ],
            "",
            "任务成功只表示隔离安全且证据完整，不代表测试全部通过。",
            "",
        ]
    )


def run_baseline(
    *,
    mode: str,
    output_dir: Path,
    timeout_seconds: int,
    fail_on_test_failure: bool,
) -> int:
    output_dir = _validate_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    real_directories = UserDirectoryContext.current()
    protected_paths = collect_user_surface_paths(PROJECT_ROOT, real_directories)
    before = capture_user_surfaces(protected_paths)
    initial_risks = unsafe_surface_states(before)
    _write_snapshot(output_dir / "user-surfaces-before.json", before)

    environment_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commit": _git_value("rev-parse", "HEAD"),
        "branch": _git_value("branch", "--show-current"),
        "worktree_status": _git_value("status", "--short"),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "mode": mode,
        "selectors": list(MODE_SELECTORS[mode]),
    }
    (output_dir / "environment.json").write_text(
        json.dumps(environment_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    runs: list[PytestRun] = []
    runner_error: str | None = (
        f"protected paths contain reparse or unreadable states: {initial_risks}"
        if initial_risks
        else None
    )
    execution_modes = MODE_EXECUTION_PLAN[mode]
    try:
        if runner_error is not None:
            raise RuntimeError(runner_error)
        with tempfile.TemporaryDirectory(prefix="super-dev-baseline-") as temp_root_raw:
            temp_root = Path(temp_root_raw).resolve()
            isolated_home = temp_root / "home"
            isolated_home.mkdir()
            assert_safe_isolated_home(
                isolated_home,
                real_home=real_directories.home,
                project_dir=PROJECT_ROOT,
                run_root=temp_root,
            )
            isolated_directories = UserDirectoryContext.from_home(isolated_home)
            isolated_environment = isolated_directories.environment(os.environ)
            isolated_environment["SUPER_DEV_BASELINE_RUN"] = "1"
            isolated_environment["PYTHONNOUSERSITE"] = "1"
            isolated_environment["PYTHONPATH"] = _isolated_pytest_pythonpath()
            for index, stage_mode in enumerate(execution_modes, start=1):
                run = _run_pytest(
                    mode=stage_mode,
                    index=index,
                    output_dir=output_dir,
                    isolated_environment=isolated_environment,
                    base_temp=temp_root / f"pytest-{index}",
                    timeout_seconds=timeout_seconds,
                )
                runs.append(run)
                interim = capture_user_surfaces(protected_paths)
                interim_diff = diff_surface_snapshots(before, interim)
                if has_surface_changes(interim_diff):
                    runner_error = f"real user surfaces changed after {stage_mode}"
                    break
                if (
                    stage_mode != mode
                    and stage_mode
                    in {
                        "isolation-smoke",
                        "user-surfaces",
                    }
                    and run.returncode != 0
                ):
                    runner_error = f"preflight failed: {stage_mode}"
                    break
    except Exception as error:  # pragma: no cover - defensive evidence path
        runner_error = f"{type(error).__name__}: {error}"
        (output_dir / "runner-error.txt").write_text(runner_error, encoding="utf-8")
    finally:
        after = capture_user_surfaces(protected_paths)

    _write_snapshot(output_dir / "user-surfaces-after.json", after)
    surface_diff = diff_surface_snapshots(before, after)
    safety_result = "unsafe" if has_surface_changes(surface_diff) else "safe"
    target_runs = [run for run in runs if run.mode == mode]
    test_result = (
        "pass"
        if runner_error is None and target_runs and all(run.returncode == 0 for run in target_runs)
        else "fail"
    )
    required_files = [
        output_dir / "environment.json",
        output_dir / "user-surfaces-before.json",
        output_dir / "user-surfaces-after.json",
        *[Path(run.junit_file) for run in runs],
        *[Path(run.output_file) for run in runs],
    ]
    evidence_result = (
        "complete"
        if runner_error is None
        and len(runs) == len(execution_modes)
        and all(path.exists() for path in required_files)
        else "incomplete"
    )
    repeatable = None
    if mode == "repeatability" and len(target_runs) == 2:
        first, second = target_runs
        repeatable = (
            first.failures == second.failures
            and first.passed == second.passed
            and first.failed == second.failed
            and first.errors == second.errors
            and first.skipped == second.skipped
        )

    result = {
        "schema_version": 1,
        "mode": mode,
        "mode_label": MODE_LABELS[mode],
        "safety_result": safety_result,
        "test_result": test_result,
        "evidence_result": evidence_result,
        "repeatable": repeatable,
        "runner_error": runner_error,
        "planned_modes": execution_modes,
        "executed_modes": [run.mode for run in runs],
        "surface_diff": surface_diff,
        "runs": [asdict(run) for run in runs],
    }
    (output_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        _summary_markdown(
            mode=mode,
            safety_result=safety_result,
            test_result=test_result,
            evidence_result=evidence_result,
            repeatable=repeatable,
            surface_diff=surface_diff,
            runs=runs,
        ),
        encoding="utf-8",
    )

    if safety_result != "safe" or evidence_result != "complete" or repeatable is False:
        return 2
    if fail_on_test_failure and test_result != "pass":
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Super Dev 安全测试基线入口")
    parser.add_argument("mode", choices=sorted(MODE_SELECTORS))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--fail-on-test-failure", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir or BASELINE_ROOT / "runs" / f"{_utc_id()}-{args.mode}"
    return run_baseline(
        mode=args.mode,
        output_dir=output_dir.resolve(),
        timeout_seconds=args.timeout_seconds,
        fail_on_test_failure=args.fail_on_test_failure,
    )


if __name__ == "__main__":
    raise SystemExit(main())
