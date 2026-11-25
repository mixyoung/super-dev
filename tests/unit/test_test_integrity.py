"""Unit tests for TestIntegrityChecker (Anti-Gaming Probe)."""

from pathlib import Path

from super_dev.reviewers.test_integrity import TestIntegrityChecker


def test_clean_python_test_passes(tmp_path: Path) -> None:
    code = """
import pytest

def test_addition():
    x = 1 + 1
    assert x == 2

def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        _ = 1 / 0
"""
    test_file = tmp_path / "test_math.py"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    assert violations == []

    report = TestIntegrityChecker.scan_project(tmp_path)
    assert report.passed is True
    assert report.scanned_files_count == 1


def test_detects_commented_assertions_python(tmp_path: Path) -> None:
    code = """
def test_user_login():
    response = {"status": 500}
    # assert response["status"] == 200
    print("login executed")
    assert response is not None
"""
    test_file = tmp_path / "test_auth.py"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    assert len(violations) == 1
    assert violations[0].violation_type == "commented_assertion"
    assert violations[0].severity == "error"
    assert "assert response" in violations[0].snippet


def test_ignores_commented_assert_inside_multiline_string_fixture(tmp_path: Path) -> None:
    code = '''
def test_fixture_with_hash_assert():
    sample = """
def test_inner():
    # assert 1 == 2
    assert True
"""
    assert "assert 1 == 2" in sample
'''
    test_file = tmp_path / "test_fixture.py"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    assert violations == []


def test_detects_unconditional_skipped_tests_and_allows_conditional_skips(tmp_path: Path) -> None:
    code = """
import os
import pytest

@pytest.mark.skip(reason="broken test")
def test_payment_charge():
    assert True

@pytest.mark.skipif(True, reason="hardcoded skip")
def test_hardcoded_skipif():
    assert True

def test_unguarded_runtime_skip():
    pytest.skip("always skipped")
    assert True

@pytest.mark.skipif(os.name != "nt", reason="Windows only")
def test_windows_platform_guard():
    assert os.name in ("nt", "posix")

def test_conditional_runtime_guard():
    if os.name == "nonexistent":
        pytest.skip("missing tool")
    try:
        x = 1
    except ImportError:
        pytest.skip("optional dependency missing")
    assert x == 1
"""
    test_file = tmp_path / "test_payment.py"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    skipped_lines = {v.line_number for v in violations if v.violation_type == "skipped_test"}
    assert len(skipped_lines) == 3


def test_ignores_nested_helper_and_recognizes_mock_and_validator_assertions(tmp_path: Path) -> None:
    code = """
from unittest.mock import MagicMock

def validate_contract(val):
    if val <= 0:
        raise ValueError("invalid")

def test_outer_with_nested_handler():
    async def test_handler(ctx):
        return {"ok": True}

    mock_fn = MagicMock()
    mock_fn("ok")
    mock_fn.assert_called_once_with("ok")
    assert callable(test_handler)

def test_contract_validator_helper():
    validate_contract(42)
"""
    test_file = tmp_path / "test_helpers.py"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    assert violations == []


def test_detects_assertion_free_empty_test_python(tmp_path: Path) -> None:
    code = """
def test_fake_feature():
    result = 42
    # No assert statement here!
"""
    test_file = tmp_path / "test_fake.py"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    assert len(violations) == 1
    assert violations[0].violation_type == "assertion_free_test"
    assert violations[0].severity == "error"


def test_detects_js_test_violations_and_ignores_commented_skip(tmp_path: Path) -> None:
    code = """
describe('Cart Component', () => {
  // it.skip('disabled example in comment', () => {});
  it.skip('should calculate total price', () => {
    // expect(price).toBe(100);
  });
});
"""
    test_file = tmp_path / "cart.test.js"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    types = [v.violation_type for v in violations]
    assert types.count("commented_assertion") == 1
    assert types.count("skipped_test") == 1


def test_scan_project_summary_and_ignores_host_dirs(tmp_path: Path) -> None:
    (tmp_path / "test_good.py").write_text("def test_ok(): assert 1 == 1", encoding="utf-8")
    (tmp_path / "test_bad.py").write_text("def test_bad(): # assert false\n pass", encoding="utf-8")
    # 宿主/技能目录中的脚本不应被当作项目单元测试误扫描
    skill_scripts = tmp_path / ".claude" / "skills" / "demo" / "scripts"
    skill_scripts.mkdir(parents=True)
    (skill_scripts / "test_workflow.py").write_text("def test_demo(): pass", encoding="utf-8")

    report = TestIntegrityChecker.scan_project(tmp_path)
    assert report.passed is False
    assert report.scanned_files_count == 2
    assert len(report.blocking_violations) >= 1
    assert "拦截" in report.summary


def test_scan_super_dev_repository_has_zero_blocking_errors() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report = TestIntegrityChecker.scan_project(repo_root)
    assert report.passed is True, report.blocking_violations
    assert report.blocking_violations == []
