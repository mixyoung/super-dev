from pathlib import Path

from tests.support.run_safe_baseline import (
    MODE_EXECUTION_PLAN,
    MODE_LABELS,
    MODE_SELECTORS,
    _failure_ids,
    _junit_counts,
    _validate_output_dir,
    build_parser,
)


def test_modes_are_fixed_and_have_chinese_labels():
    assert set(MODE_SELECTORS) == {
        "isolation-smoke",
        "user-surfaces",
        "windows-focused",
        "unit",
        "repeatability",
    }
    assert set(MODE_LABELS) == set(MODE_SELECTORS)
    assert MODE_LABELS["user-surfaces"] == "用户目录检查"
    assert MODE_EXECUTION_PLAN["unit"] == (
        "isolation-smoke",
        "user-surfaces",
        "unit",
    )
    assert MODE_EXECUTION_PLAN["repeatability"][-2:] == (
        "repeatability",
        "repeatability",
    )


def test_parser_rejects_arbitrary_mode():
    parser = build_parser()
    try:
        parser.parse_args(["arbitrary-command"])
    except SystemExit as error:
        assert error.code != 0
    else:
        raise AssertionError("arbitrary mode should be rejected")


def test_failure_ids_read_generated_junit(tmp_path: Path):
    junit = tmp_path / "pytest.xml"
    junit.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite tests="3" failures="1" errors="1" skipped="0">
  <testcase classname="tests.unit.test_demo" name="test_pass" />
  <testcase classname="tests.unit.test_demo" name="test_fail"><failure /></testcase>
  <testcase classname="tests.unit.test_demo" name="test_error"><error /></testcase>
</testsuite></testsuites>
""",
        encoding="utf-8",
    )

    assert _failure_ids(junit) == [
        "tests.unit.test_demo::test_error",
        "tests.unit.test_demo::test_fail",
    ]
    assert _junit_counts(junit) == {
        "passed": 1,
        "failed": 1,
        "skipped": 0,
        "errors": 1,
    }


def test_output_directory_must_be_dedicated_and_inside_project():
    accepted = _validate_output_dir(Path(".super-dev") / "baselines" / "test-run")
    assert accepted.is_relative_to(Path.cwd().resolve())

    try:
        _validate_output_dir(Path.cwd().resolve().parent / "outside")
    except ValueError:
        pass
    else:
        raise AssertionError("outside output directory should be rejected")
