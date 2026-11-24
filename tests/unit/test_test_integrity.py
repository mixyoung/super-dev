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
    assert "assert response" in violations[0].snippet


def test_detects_skipped_tests_python(tmp_path: Path) -> None:
    code = """
import pytest

@pytest.mark.skip(reason="broken test")
def test_payment_charge():
    assert True
"""
    test_file = tmp_path / "test_payment.py"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    assert any(v.violation_type == "skipped_test" for v in violations)


def test_detects_assertion_free_empty_test_python(tmp_path: Path) -> None:
    code = """
def test_fake_feature():
    result = 42
    # No assert statement here!
"""
    test_file = tmp_path / "test_fake.py"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    assert any(v.violation_type == "assertion_free_test" for v in violations)


def test_detects_js_test_violations(tmp_path: Path) -> None:
    code = """
describe('Cart Component', () => {
  it.skip('should calculate total price', () => {
    // expect(price).toBe(100);
  });
});
"""
    test_file = tmp_path / "cart.test.js"
    test_file.write_text(code, encoding="utf-8")

    violations = TestIntegrityChecker.scan_file(test_file)
    types = {v.violation_type for v in violations}
    assert "commented_assertion" in types
    assert "skipped_test" in types


def test_scan_project_summary(tmp_path: Path) -> None:
    # 正常文件
    (tmp_path / "test_good.py").write_text("def test_ok(): assert 1 == 1", encoding="utf-8")
    # 作弊文件
    (tmp_path / "test_bad.py").write_text("def test_bad(): # assert false\n pass", encoding="utf-8")

    report = TestIntegrityChecker.scan_project(tmp_path)
    assert report.passed is False
    assert report.scanned_files_count == 2
    assert len(report.violations) >= 1
    assert "拦截" in report.summary
