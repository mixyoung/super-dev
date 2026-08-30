from __future__ import annotations

from pathlib import Path

import pytest

from super_dev.extensions.builtins.fresh_verification import (
    JUnitSummaryError,
    extract_non_strict_xpass,
    parse_junit_summary,
    run,
)
from super_dev.extensions.models import CommandExecution, ExtensionStatus
from super_dev.extensions.pytest_plan import (
    PytestPlanValidationError,
    parse_pytest_verification_plan,
)


def _execution(
    *,
    exit_code: int = 0,
    stdout: str = "",
    status: ExtensionStatus | None = None,
    error: str = "",
) -> CommandExecution:
    return CommandExecution(
        status=status or (ExtensionStatus.PASS if exit_code == 0 else ExtensionStatus.FAIL),
        executable="python",
        args=("-m", "pytest"),
        cwd=".",
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
        stdout_digest="sha256:" + "a" * 64,
        stderr_digest="sha256:" + "b" * 64,
        started_at="2026-08-25T00:00:00+00:00",
        finished_at="2026-08-25T00:00:01+00:00",
        duration_ms=1000.0,
        timed_out=False,
        cancelled=False,
        process_tree_clean=True,
        error=error,
    )


def _write_junit(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_parse_single_suite_derives_executed_from_junit(tmp_path: Path) -> None:
    path = _write_junit(
        tmp_path / "pytest.xml",
        '<testsuite tests="5" failures="0" errors="0" skipped="2" time="1.25"/>',
    )

    summary = parse_junit_summary(path)

    assert summary.tests == 5
    assert summary.skipped == 2
    assert summary.executed == 3
    assert summary.duration_seconds == 1.25
    assert summary.junit_digest.startswith("sha256:")


def test_parse_multi_suite_sums_direct_suites(tmp_path: Path) -> None:
    path = _write_junit(
        tmp_path / "pytest.xml",
        """<testsuites>
        <testsuite tests="2" failures="1" errors="0" skipped="0" time="0.5"/>
        <testsuite tests="3" failures="0" errors="1" skipped="1" time="0.75"/>
        </testsuites>""",
    )

    summary = parse_junit_summary(path)

    assert summary.to_dict() | {"junit_digest": "ignored"} == {
        "tests": 5,
        "failures": 1,
        "errors": 1,
        "skipped": 1,
        "executed": 4,
        "duration_seconds": 1.25,
        "junit_digest": "ignored",
    }


@pytest.mark.parametrize(
    "body",
    [
        "<not-junit/>",
        '<testsuite tests="-1" failures="0" errors="0" skipped="0" time="0"/>',
        '<testsuite tests="1" failures="1" errors="1" skipped="0" time="0"/>',
        "<!DOCTYPE x [<!ENTITY bad 'x'>]><testsuite tests='1' failures='0' errors='0' skipped='0' time='0'/>",
    ],
)
def test_parse_junit_rejects_invalid_or_unsafe_xml(tmp_path: Path, body: str) -> None:
    path = _write_junit(tmp_path / "pytest.xml", body)

    with pytest.raises(JUnitSummaryError):
        parse_junit_summary(path)


def test_xpass_parser_only_reads_fixed_short_summary_section() -> None:
    stdout = """XPASS fake-log-entry
================ short test summary info ================
XPASS tests/test_one.py::test_one - known issue
XPASS tests/test_two.py::test_two - known issue
================ 2 xpassed in 0.01s ================
XPASS ignored-after-summary
"""

    advisories = extract_non_strict_xpass(
        stdout,
        run_id="run-1",
        output_digest="sha256:" + "c" * 64,
    )

    assert len(advisories) == 1
    assert advisories[0].code == "NON_STRICT_XPASS"
    assert advisories[0].occurrences == 2
    assert advisories[0].run_id == "run-1"


def test_xpass_text_outside_summary_does_not_create_advisory() -> None:
    assert (
        extract_non_strict_xpass(
            "test output says XPASS but is not a summary record",
            run_id="run-1",
            output_digest="sha256:" + "d" * 64,
        )
        == ()
    )


def test_adapter_blocks_all_skipped_even_with_zero_exit(tmp_path: Path) -> None:
    path = _write_junit(
        tmp_path / "pytest.xml",
        '<testsuite tests="2" failures="0" errors="0" skipped="2" time="0.1"/>',
    )

    result = run({"run_id": "run-1", "junit_path": path, "execution": _execution()})

    assert result["status"] == ExtensionStatus.BLOCKED
    assert result["summary"].executed == 0


def test_adapter_treats_exit_one_as_fail_even_without_junit_failure(tmp_path: Path) -> None:
    path = _write_junit(
        tmp_path / "pytest.xml",
        '<testsuite tests="1" failures="0" errors="0" skipped="1" time="0.1"/>',
    )

    result = run({"run_id": "run-1", "junit_path": path, "execution": _execution(exit_code=1)})

    assert result["status"] == ExtensionStatus.FAIL


def test_adapter_maps_no_tests_exit_to_blocked(tmp_path: Path) -> None:
    path = _write_junit(
        tmp_path / "pytest.xml",
        '<testsuite tests="0" failures="0" errors="0" skipped="0" time="0"/>',
    )

    result = run({"run_id": "run-1", "junit_path": path, "execution": _execution(exit_code=5)})

    assert result["status"] == ExtensionStatus.BLOCKED


def test_adapter_preserves_executor_block_without_parsing_junit(tmp_path: Path) -> None:
    result = run(
        {
            "run_id": "run-1",
            "junit_path": tmp_path / "missing.xml",
            "execution": _execution(
                status=ExtensionStatus.BLOCKED,
                error="命令执行超时",
            ),
        }
    )

    assert result["status"] == ExtensionStatus.BLOCKED
    assert result["summary"] is None


def test_plan_parser_accepts_bounded_pytest_plan() -> None:
    plan = parse_pytest_verification_plan(
        {
            "profile": "pytest-current-python",
            "plan_id": "completion-pilot",
            "args": ["-q", "tests/extensions"],
            "timeout_seconds": 300,
        }
    )

    assert plan.args == ("-q", "tests/extensions")


def test_plan_parser_allows_safe_compact_expression() -> None:
    plan = parse_pytest_verification_plan(
        {
            "profile": "pytest-current-python",
            "plan_id": "completion-pilot",
            "args": ["-qkunit", "tests/extensions"],
            "timeout_seconds": 300,
        }
    )

    assert plan.args == ("-qkunit", "tests/extensions")


@pytest.mark.parametrize(
    "args",
    [
        ["--junitxml=outside.xml"],
        ["--junitxml", "outside.xml"],
        ["--junit-xml", "outside.xml"],
        ["--basetemp=../outside"],
        ["--basetemp", "outside"],
        ["--confcutdir", "outside"],
        ["--rootdir", "outside"],
        ["--override-ini=addopts=-x"],
        ["-cpytest.ini"],
        ["-oaddopts=-x"],
        ["-qcpytest.ini"],
        ["-qoaddopts=-x"],
        ["-qpunsafe-plugin"],
        ["-qrA"],
        ["-p", "unsafe-plugin"],
        ["--lf"],
        ["C:\\outside\\tests"],
        ["C:relative\\tests"],
        ["../outside"],
    ],
)
def test_plan_parser_rejects_core_overrides_and_escaping_paths(args: list[str]) -> None:
    with pytest.raises(PytestPlanValidationError):
        parse_pytest_verification_plan(
            {
                "profile": "pytest-current-python",
                "plan_id": "completion-pilot",
                "args": args,
                "timeout_seconds": 300,
            }
        )


def test_plan_parser_rejects_unknown_fields() -> None:
    with pytest.raises(PytestPlanValidationError):
        parse_pytest_verification_plan(
            {
                "profile": "pytest-current-python",
                "plan_id": "completion-pilot",
                "args": ["tests"],
                "timeout_seconds": 300,
                "command": "pytest",
            }
        )
