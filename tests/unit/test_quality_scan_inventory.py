import os
from pathlib import Path

import pytest

from super_dev.reviewers import architecture_drift, spec_compliance, uiux_compliance
from super_dev.reviewers.validation_rules import ValidationRule, ValidationRuleEngine


@pytest.mark.parametrize(
    "scan",
    [
        spec_compliance._scan_code_files,
        architecture_drift._scan_imports,
        uiux_compliance._scan_frontend_files,
    ],
)
def test_source_scanners_do_not_enter_excluded_subtrees(tmp_path, monkeypatch, scan):
    (tmp_path / "app.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "page.tsx").write_text("export const title = 'hello';\n", encoding="utf-8")
    excluded = tmp_path / "node_modules"
    (excluded / "deep").mkdir(parents=True)
    (excluded / "deep" / "dependency.py").write_text("import sys\n", encoding="utf-8")
    original = os.scandir
    entered = []

    def observe(path):
        entered.append(Path(path))
        return original(path)

    original_rglob = Path.rglob

    def observe_rglob(path, *args, **kwargs):
        for item in original_rglob(path, *args, **kwargs):
            entered.append(item.parent)
            yield item

    monkeypatch.setattr(os, "scandir", observe)
    monkeypatch.setattr(Path, "rglob", observe_rglob)
    scan(tmp_path)
    assert not any(path == excluded or excluded in path.parents for path in entered)


@pytest.mark.parametrize(
    ("scan", "name", "content"),
    [
        (spec_compliance._scan_code_files, "app.py", "def login(): return True\n"),
        (architecture_drift._scan_imports, "app.py", "import os\n"),
        (uiux_compliance._scan_frontend_files, "page.tsx", "export const title = 'hi';\n"),
    ],
)
def test_unreadable_source_is_not_silently_omitted(tmp_path, monkeypatch, scan, name, content):
    target = tmp_path / name
    target.write_text(content, encoding="utf-8")
    original = Path.read_text

    def deny(path, *args, **kwargs):
        if path == target:
            raise PermissionError("denied by test")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny)
    with pytest.raises(RuntimeError, match="受阻.*" + name):
        scan(tmp_path)


def test_rule_scan_unreadable_source_blocks_standalone_validation(tmp_path, monkeypatch):
    target = tmp_path / "app.py"
    target.write_text("password = 'example'\n", encoding="utf-8")
    engine = ValidationRuleEngine(tmp_path)
    engine.rules = [
        ValidationRule(
            id="TEST-SCAN",
            name="source check",
            category="security",
            severity="high",
            phase="quality",
            description="do not omit unreadable input",
            check_type="content_not_contains",
            check_config={"file_pattern": "**/*.py", "patterns": ["password"]},
        )
    ]
    original = Path.read_text

    def deny(path, *args, **kwargs):
        if path == target:
            raise PermissionError("denied by test")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny)
    report = engine.validate("quality")
    assert not report.passed
    assert any("受阻" in item.message and "app.py" in item.message for item in report.results)


def test_regex_generated_only_matching_keeps_legacy_failure(tmp_path):
    generated = tmp_path / "build" / "app.py"
    generated.parent.mkdir()
    generated.write_text("required_pattern\n", encoding="utf-8")
    rule = ValidationRule(
        id="REGEX-SCAN",
        name="regex",
        category="code_quality",
        severity="high",
        phase="quality",
        description="must match real source",
        check_type="regex_match",
        check_config={"file_pattern": "**/*.py", "pattern": "required_pattern"},
    )
    engine = ValidationRuleEngine(tmp_path)
    result = engine._check_regex_match(rule, {"project_dir": str(tmp_path)})
    assert not result.passed
    assert "未匹配" in result.message


def test_single_spec_scan_prunes_its_additional_exclusions(tmp_path, monkeypatch):
    target = tmp_path / ".nuxt" / "generated.py"
    target.parent.mkdir()
    target.write_text("x = 1\n", encoding="utf-8")
    original = os.scandir
    entered = []

    def observe(path):
        entered.append(Path(path))
        return original(path)

    monkeypatch.setattr(os, "scandir", observe)
    assert spec_compliance._scan_code_files(tmp_path) == {}
    assert target.parent not in entered
