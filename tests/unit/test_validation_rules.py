"""验证规则引擎单元测试"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from super_dev.reviewers.validation_rules import (
    VALID_CATEGORIES,
    VALID_CHECK_TYPES,
    VALID_PHASES,
    VALID_SEVERITIES,
    ValidationReport,
    ValidationResult,
    ValidationRule,
    ValidationRuleEngine,
    _load_rules_from_yaml,
    _parse_rule_dict,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule(**overrides) -> ValidationRule:
    """快捷构造合法的 ValidationRule。"""
    defaults = dict(
        id="TEST-001",
        name="Test Rule",
        category="security",
        severity="high",
        phase="all",
        description="A test rule",
        check_type="file_exists",
        check_config={},
    )
    defaults.update(overrides)
    return ValidationRule(**defaults)


def _write_rules_yaml(path: Path, rules: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump({"rules": rules}), encoding="utf-8")


def _minimal_rule_dict(**overrides) -> dict:
    defaults = dict(
        id="R-001",
        name="Rule",
        category="security",
        severity="high",
        phase="all",
        check_type="file_exists",
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# ValidationRule dataclass
# ---------------------------------------------------------------------------


class TestValidationRule:
    def test_valid_construction(self):
        rule = _make_rule()
        assert rule.id == "TEST-001"
        assert rule.enabled is True
        assert rule.tags == []

    def test_invalid_category(self):
        with pytest.raises(ValueError, match="Invalid category"):
            _make_rule(category="bogus")

    def test_invalid_severity(self):
        with pytest.raises(ValueError, match="Invalid severity"):
            _make_rule(severity="extreme")

    def test_invalid_phase(self):
        with pytest.raises(ValueError, match="Invalid phase"):
            _make_rule(phase="nowhere")

    def test_invalid_check_type(self):
        with pytest.raises(ValueError, match="Invalid check_type"):
            _make_rule(check_type="magic")

    @pytest.mark.parametrize("category", sorted(VALID_CATEGORIES))
    def test_all_valid_categories(self, category: str):
        rule = _make_rule(category=category)
        assert rule.category == category

    @pytest.mark.parametrize("severity", sorted(VALID_SEVERITIES))
    def test_all_valid_severities(self, severity: str):
        rule = _make_rule(severity=severity)
        assert rule.severity == severity

    @pytest.mark.parametrize("phase", sorted(VALID_PHASES))
    def test_all_valid_phases(self, phase: str):
        rule = _make_rule(phase=phase)
        assert rule.phase == phase

    @pytest.mark.parametrize("ct", sorted(VALID_CHECK_TYPES))
    def test_all_valid_check_types(self, ct: str):
        rule = _make_rule(check_type=ct)
        assert rule.check_type == ct


# ---------------------------------------------------------------------------
# _parse_rule_dict / _load_rules_from_yaml
# ---------------------------------------------------------------------------


class TestParseHelpers:
    def test_parse_rule_dict_minimal(self):
        rule = _parse_rule_dict(_minimal_rule_dict())
        assert rule.id == "R-001"
        assert rule.enabled is True
        assert rule.description == ""

    def test_parse_rule_dict_with_all_fields(self):
        d = _minimal_rule_dict(
            description="desc",
            enabled=False,
            tags=["a", "b"],
            check_config={"file_pattern": "*.py"},
        )
        rule = _parse_rule_dict(d)
        assert rule.description == "desc"
        assert rule.enabled is False
        assert rule.tags == ["a", "b"]

    def test_load_rules_from_yaml_file(self, tmp_path: Path):
        yaml_path = tmp_path / "rules.yaml"
        _write_rules_yaml(yaml_path, [_minimal_rule_dict()])
        rules = _load_rules_from_yaml(yaml_path)
        assert len(rules) == 1
        assert rules[0].id == "R-001"

    def test_load_rules_from_yaml_missing_file(self, tmp_path: Path):
        assert _load_rules_from_yaml(tmp_path / "missing.yaml") == []

    def test_load_rules_from_yaml_empty(self, tmp_path: Path):
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("{}", encoding="utf-8")
        assert _load_rules_from_yaml(yaml_path) == []

    def test_load_rules_from_yaml_no_rules_key(self, tmp_path: Path):
        yaml_path = tmp_path / "bad.yaml"
        yaml_path.write_text(yaml.dump({"other": 1}), encoding="utf-8")
        assert _load_rules_from_yaml(yaml_path) == []

    def test_load_rules_from_yaml_skips_non_dict_items(self, tmp_path: Path):
        yaml_path = tmp_path / "rules.yaml"
        yaml_path.write_text(
            yaml.dump({"rules": ["not_a_dict", _minimal_rule_dict()]}),
            encoding="utf-8",
        )
        rules = _load_rules_from_yaml(yaml_path)
        assert len(rules) == 1


# ---------------------------------------------------------------------------
# ValidationRuleEngine — 规则加载
# ---------------------------------------------------------------------------


class TestEngineLoading:
    def test_engine_loads_default_rules(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        # 至少内置了默认规则（如果文件存在）
        # 不做精确数量断言，只确保不报错
        assert isinstance(engine.rules, list)

    def test_custom_rules_override_defaults(self, tmp_path: Path):
        # 先创建引擎加载默认规则
        engine = ValidationRuleEngine(tmp_path)
        if not engine.rules:
            pytest.skip("No default rules found")

        first_default = engine.rules[0]
        custom_name = "Overridden Rule Name"

        custom_dir = tmp_path / ".super-dev" / "rules"
        _write_rules_yaml(
            custom_dir / "custom_rules.yaml",
            [
                _minimal_rule_dict(
                    id=first_default.id,
                    name=custom_name,
                    category=first_default.category,
                    severity=first_default.severity,
                    phase=first_default.phase,
                    check_type=first_default.check_type,
                )
            ],
        )

        engine.reload_rules()
        overridden = engine.get_rule(first_default.id)
        assert overridden is not None
        assert overridden.name == custom_name

    def test_reload_rules(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        count_before = len(engine.rules)
        engine.reload_rules()
        assert len(engine.rules) == count_before


# ---------------------------------------------------------------------------
# ValidationRuleEngine — 规则管理
# ---------------------------------------------------------------------------


class TestEngineManagement:
    def test_add_rule_new(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        count = len(engine.rules)
        rule = _make_rule(id="NEW-001")
        engine.add_rule(rule)
        assert len(engine.rules) == count + 1
        assert engine.get_rule("NEW-001") is rule

    def test_add_rule_replaces_existing(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        rule1 = _make_rule(id="DUP-001", name="Original")
        rule2 = _make_rule(id="DUP-001", name="Replacement")
        engine.add_rule(rule1)
        engine.add_rule(rule2)
        assert engine.get_rule("DUP-001").name == "Replacement"

    def test_remove_rule_success(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.add_rule(_make_rule(id="DEL-001"))
        assert engine.remove_rule("DEL-001") is True
        assert engine.get_rule("DEL-001") is None

    def test_remove_rule_not_found(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        assert engine.remove_rule("NONEXISTENT") is False

    def test_get_rule_none_when_missing(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        assert engine.get_rule("MISSING") is None

    def test_get_rules_for_phase(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = []
        engine.add_rule(_make_rule(id="A", phase="docs"))
        engine.add_rule(_make_rule(id="B", phase="all"))
        engine.add_rule(_make_rule(id="C", phase="frontend"))
        engine.add_rule(_make_rule(id="D", phase="docs", enabled=False))

        docs_rules = engine.get_rules_for_phase("docs")
        ids = {r.id for r in docs_rules}
        assert "A" in ids
        assert "B" in ids  # phase="all" 应匹配
        assert "C" not in ids
        assert "D" not in ids  # disabled

    def test_list_rules_filter_by_category(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(id="X1", category="security"),
            _make_rule(id="X2", category="testing"),
        ]
        result = engine.list_rules(category="security")
        assert len(result) == 1
        assert result[0].id == "X1"

    def test_list_rules_filter_by_severity(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(id="X1", severity="critical"),
            _make_rule(id="X2", severity="low"),
        ]
        result = engine.list_rules(severity="critical")
        assert len(result) == 1

    def test_list_rules_filter_by_phase(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(id="X1", phase="docs"),
            _make_rule(id="X2", phase="all"),
            _make_rule(id="X3", phase="backend"),
        ]
        result = engine.list_rules(phase="docs")
        ids = {r.id for r in result}
        assert ids == {"X1", "X2"}


# ---------------------------------------------------------------------------
# ValidationRuleEngine — check_type: file_exists
# ---------------------------------------------------------------------------


class TestCheckFileExists:
    def test_file_exists_pass(self, tmp_path: Path):
        (tmp_path / "output").mkdir()
        (tmp_path / "output" / "my-prd.md").write_text("content", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="FE-1",
                check_type="file_exists",
                check_config={"file_pattern": "output/*.md", "min_count": 1},
            ),
        ]
        report = engine.validate("docs")
        assert report.passed is True
        assert report.results[0].passed is True

    def test_file_exists_fail(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="FE-2",
                check_type="file_exists",
                check_config={"file_pattern": "nonexistent/*.md", "min_count": 1},
            ),
        ]
        report = engine.validate("docs")
        assert report.results[0].passed is False
        assert report.results[0].fix_suggestion != ""


# ---------------------------------------------------------------------------
# ValidationRuleEngine — check_type: content_contains
# ---------------------------------------------------------------------------


class TestCheckContentContains:
    def test_content_contains_pass(self, tmp_path: Path):
        (tmp_path / "doc.md").write_text("# Title\n目标用户\n核心功能", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CC-1",
                check_type="content_contains",
                check_config={
                    "file_pattern": "doc.md",
                    "required_sections": ["目标用户", "核心功能"],
                },
            ),
        ]
        report = engine.validate("docs")
        assert report.results[0].passed is True

    def test_content_contains_fail_missing_section(self, tmp_path: Path):
        (tmp_path / "doc.md").write_text("# Title\n目标用户", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CC-2",
                check_type="content_contains",
                check_config={
                    "file_pattern": "doc.md",
                    "required_sections": ["目标用户", "核心功能"],
                },
            ),
        ]
        report = engine.validate("docs")
        assert report.results[0].passed is False

    def test_content_contains_fail_no_file(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CC-3",
                check_type="content_contains",
                check_config={
                    "file_pattern": "missing.md",
                    "required_sections": ["something"],
                },
            ),
        ]
        report = engine.validate("docs")
        assert report.results[0].passed is False


# ---------------------------------------------------------------------------
# ValidationRuleEngine — check_type: content_not_contains
# ---------------------------------------------------------------------------


class TestCheckContentNotContains:
    def test_no_violation(self, tmp_path: Path):
        (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CNC-1",
                check_type="content_not_contains",
                check_config={
                    "file_pattern": "clean.py",
                    "patterns": [r"password\s*=\s*['\"]"],
                },
            ),
        ]
        report = engine.validate("all")
        assert report.results[0].passed is True

    def test_violation_found(self, tmp_path: Path):
        (tmp_path / "bad.py").write_text('password = "secret123"\n', encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CNC-2",
                check_type="content_not_contains",
                check_config={
                    "file_pattern": "bad.py",
                    "patterns": [r"password\s*=\s*['\"]"],
                },
            ),
        ]
        report = engine.validate("all")
        assert report.results[0].passed is False

    def test_generated_build_tree_is_ignored_but_root_source_still_fails(
        self,
        tmp_path: Path,
    ):
        (tmp_path / "build" / "lib").mkdir(parents=True)
        (tmp_path / "build" / "lib" / "generated.py").write_text(
            'password = "generated"\n',
            encoding="utf-8",
        )
        (tmp_path / "demo.egg-info").mkdir()
        (tmp_path / "demo.egg-info" / "generated.py").write_text(
            'password = "egg-generated"\n',
            encoding="utf-8",
        )
        (tmp_path / "source.py").write_text(
            'password = "real-source"\n',
            encoding="utf-8",
        )
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CNC-SCOPE",
                check_type="content_not_contains",
                check_config={
                    "file_pattern": "**/*.py",
                    "patterns": [r"password\s*=\s*['\"]"],
                },
            )
        ]

        report = engine.validate("quality")

        assert report.results[0].passed is False
        assert "source.py" in report.results[0].message
        assert "build" not in report.results[0].message
        assert "demo.egg-info" not in report.results[0].message

    def test_frontend_tagged_rule_is_skipped_when_frontend_is_not_required(
        self,
        tmp_path: Path,
    ):
        (tmp_path / "page.tsx").write_text("forbidden-ui-pattern\n", encoding="utf-8")
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CNC-FRONTEND",
                phase="quality",
                tags=["frontend"],
                check_type="content_not_contains",
                check_config={
                    "file_pattern": "**/*.tsx",
                    "patterns": ["forbidden-ui-pattern"],
                },
            )
        ]

        not_applicable = engine.validate("quality", {"frontend_required": False})
        applicable = engine.validate("quality", {"frontend_required": True})

        assert not_applicable.results == []
        assert not_applicable.passed is True
        assert applicable.results[0].passed is False

    def test_relative_project_context_reports_violation(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        (tmp_path / "sample.py").write_text('password = "secret"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CNC-RELATIVE",
                check_type="content_not_contains",
                check_config={
                    "file_pattern": "*.py",
                    "patterns": [r"password\s*=\s*['\"]"],
                },
            )
        ]

        report = engine.validate("all", {"project_dir": "."})

        assert report.results[0].passed is False
        assert "sample.py" in report.results[0].message
        assert "规则执行异常" not in report.results[0].message


# ---------------------------------------------------------------------------
# ValidationRuleEngine — check_type: python_sensitive_logging
# ---------------------------------------------------------------------------


class TestPythonSensitiveLogging:
    def _rule(self):
        return _make_rule(
            id="CQ-BE-001",
            severity="critical",
            check_type="python_sensitive_logging",
            check_config={
                "file_pattern": "**/*.py",
                "sensitive_names": ["password", "secret", "token", "api_key"],
            },
        )

    def test_detects_sensitive_values_passed_to_output_calls(self, tmp_path: Path):
        (tmp_path / "bad.py").write_text(
            "import logging\n"
            "logger = logging.getLogger(__name__)\n"
            "password = 'value'\n"
            "logger.info('password=%s', password)\n"
            "print(settings.api_key)\n",
            encoding="utf-8",
        )
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [self._rule()]

        report = engine.validate("quality")

        assert report.results[0].passed is False
        assert "bad.py:4" in report.results[0].message
        assert "bad.py:5" in report.results[0].message

    def test_detects_sensitive_mapping_access(self, tmp_path: Path):
        (tmp_path / "bad.py").write_text(
            "import logging\n"
            "logger = logging.getLogger(__name__)\n"
            "logger.error('request failed: %s', config['token'])\n",
            encoding="utf-8",
        )
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [self._rule()]

        report = engine.validate("quality")

        assert report.results[0].passed is False
        assert "bad.py:3" in report.results[0].message

    def test_metric_exemption_does_not_hide_access_tokens(self, tmp_path: Path):
        (tmp_path / "bad.py").write_text(
            "import logging\n"
            "logger = logging.getLogger(__name__)\n"
            "logger.info('access token=%s', access_token_used)\n",
            encoding="utf-8",
        )
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [self._rule()]

        report = engine.validate("quality")

        assert report.results[0].passed is False
        assert "bad.py:3" in report.results[0].message

    def test_ignores_static_labels_and_generated_source_strings(self, tmp_path: Path):
        (tmp_path / "clean.py").write_text(
            "import logging\n"
            "logger = logging.getLogger(__name__)\n"
            "logger.debug('Could not extract tokens; using defaults.')\n"
            "logger.info('usage=%s/%s', tokens_used, total_token_budget)\n"
            "logger.info('limit=%s', _DEFAULT_TOKEN_BUDGET)\n"
            "generated = \"print(f'secret={secret}')\"\n"
            "print('Configure secrets before release')\n",
            encoding="utf-8",
        )
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [self._rule()]

        report = engine.validate("quality")

        assert report.results[0].passed is True

    def test_validate_file_uses_the_same_ast_check(self, tmp_path: Path):
        source = tmp_path / "single.py"
        source.write_text("print(getattr(settings, 'token'))\n", encoding="utf-8")
        engine = ValidationRuleEngine(tmp_path)

        result = engine.validate_file(source, [self._rule()])

        assert result[0].passed is False
        assert "lines 1" in result[0].message


# ---------------------------------------------------------------------------
# ValidationRuleEngine — check_type: regex_match
# ---------------------------------------------------------------------------


class TestCheckRegexMatch:
    def test_regex_match_found(self, tmp_path: Path):
        (tmp_path / "api.py").write_text('app.get("/api/v1/users")', encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="RX-1",
                check_type="regex_match",
                check_config={
                    "file_pattern": "api.py",
                    "pattern": r"/api/v[0-9]+",
                    "description": "API versioning",
                },
            ),
        ]
        report = engine.validate("backend")
        assert report.results[0].passed is True

    def test_regex_match_not_found(self, tmp_path: Path):
        (tmp_path / "api.py").write_text('app.get("/users")', encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="RX-2",
                check_type="regex_match",
                check_config={
                    "file_pattern": "api.py",
                    "pattern": r"/api/v[0-9]+",
                    "description": "API versioning",
                },
            ),
        ]
        report = engine.validate("backend")
        assert report.results[0].passed is False

    def test_regex_match_no_matching_files_skips(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="RX-3",
                check_type="regex_match",
                check_config={
                    "file_pattern": "nonexistent.py",
                    "pattern": r"anything",
                },
            ),
        ]
        report = engine.validate("backend")
        assert report.results[0].passed is True  # 无文件时跳过

    def test_relative_project_context_finds_regex(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        (tmp_path / "sample.py").write_text('app.get("/api/v2/users")\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="RX-RELATIVE",
                check_type="regex_match",
                check_config={
                    "file_pattern": "*.py",
                    "pattern": r"/api/v[0-9]+",
                },
            )
        ]

        report = engine.validate("all", {"project_dir": "."})

        assert report.results[0].passed is True
        assert "规则执行异常" not in report.results[0].message


# ---------------------------------------------------------------------------
# ValidationRuleEngine — check_type: metric_threshold
# ---------------------------------------------------------------------------


class TestCheckMetricThreshold:
    def test_metric_within_range(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="MT-1",
                check_type="metric_threshold",
                check_config={"metric": "coverage", "min_value": 80},
            ),
        ]
        report = engine.validate("quality", {"metrics": {"coverage": 85}})
        assert report.results[0].passed is True

    def test_metric_below_min(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="MT-2",
                check_type="metric_threshold",
                check_config={"metric": "coverage", "min_value": 80},
            ),
        ]
        report = engine.validate("quality", {"metrics": {"coverage": 50}})
        assert report.results[0].passed is False

    def test_metric_above_max(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="MT-3",
                check_type="metric_threshold",
                check_config={"metric": "bundle_size", "max_value": 500},
            ),
        ]
        report = engine.validate("frontend", {"metrics": {"bundle_size": 600}})
        assert report.results[0].passed is False

    def test_metric_unavailable_skips(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="MT-4",
                check_type="metric_threshold",
                check_config={"metric": "missing_metric", "min_value": 10},
            ),
        ]
        report = engine.validate("quality", {"metrics": {}})
        assert report.results[0].passed is True  # 指标不可用时跳过


# ---------------------------------------------------------------------------
# ValidationRuleEngine — custom checker
# ---------------------------------------------------------------------------


class TestCustomChecker:
    def test_registered_custom_checker_invoked(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)

        def my_checker(rule, context):
            return ValidationResult(
                rule_id=rule.id,
                passed=True,
                message="custom ok",
                severity=rule.severity,
            )

        engine.register_custom_checker("custom", my_checker)
        engine.rules = [
            _make_rule(id="CUS-1", check_type="custom", check_config={"checker": "custom"}),
        ]
        report = engine.validate("all")
        assert report.results[0].passed is True
        assert report.results[0].message == "custom ok"

    def test_unregistered_custom_checker_skips(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(id="CUS-2", check_type="custom", check_config={"checker": "unknown"}),
        ]
        report = engine.validate("all")
        assert report.results[0].passed is True  # 未注册时跳过

    def test_custom_check_type_override(self, tmp_path: Path):
        """通过 register_custom_checker 注册一个自定义 check_type（非 'custom'）。"""
        engine = ValidationRuleEngine(tmp_path)

        def special(rule, context):
            return ValidationResult(
                rule_id=rule.id,
                passed=False,
                message="special fail",
                severity=rule.severity,
            )

        engine.register_custom_checker("file_exists", special)
        engine.rules = [_make_rule(id="OV-1", check_type="file_exists")]
        report = engine.validate("all")
        assert report.results[0].passed is False
        assert "special fail" in report.results[0].message


# ---------------------------------------------------------------------------
# ValidationRuleEngine — critical 规则导致整体不通过
# ---------------------------------------------------------------------------


class TestCriticalFailure:
    def test_critical_fail_makes_report_fail(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="CRIT-1",
                severity="critical",
                check_type="file_exists",
                check_config={"file_pattern": "nonexistent_file", "min_count": 1},
            ),
        ]
        report = engine.validate("docs")
        assert report.passed is False
        assert len(report.critical_failures) == 1

    def test_non_critical_fail_still_passes(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="LOW-1",
                severity="low",
                check_type="file_exists",
                check_config={"file_pattern": "nonexistent_file", "min_count": 1},
            ),
        ]
        report = engine.validate("docs")
        assert report.passed is True  # 非 critical 失败不影响 passed
        assert len(report.failed_results) == 1

    def test_mixed_critical_and_non_critical(self, tmp_path: Path):
        (tmp_path / "exists.txt").write_text("ok", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="OK-1",
                severity="critical",
                check_type="file_exists",
                check_config={"file_pattern": "exists.txt", "min_count": 1},
            ),
            _make_rule(
                id="FAIL-LOW",
                severity="low",
                check_type="file_exists",
                check_config={"file_pattern": "missing.txt", "min_count": 1},
            ),
        ]
        report = engine.validate("docs")
        assert report.passed is True
        assert len(report.failed_results) == 1
        assert len(report.passed_results) == 1


# ---------------------------------------------------------------------------
# ValidationRuleEngine — validate_file
# ---------------------------------------------------------------------------


class TestValidateFile:
    def test_validate_file_content_contains(self, tmp_path: Path):
        f = tmp_path / "readme.md"
        f.write_text("# Hello\nSecurity section here", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        rules = [
            _make_rule(
                id="VF-1",
                check_type="content_contains",
                check_config={"required_sections": ["Security"]},
            ),
        ]
        results = engine.validate_file(f, rules)
        assert len(results) == 1
        assert results[0].passed is True

    def test_validate_file_missing(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        results = engine.validate_file(tmp_path / "nope.txt")
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].rule_id == "SYS"

    def test_validate_file_regex_match(self, tmp_path: Path):
        f = tmp_path / "code.py"
        f.write_text("def foo() -> int: ...", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        rules = [
            _make_rule(
                id="VF-2",
                check_type="regex_match",
                check_config={"pattern": r"def \w+\(.*\)\s*->"},
            ),
        ]
        results = engine.validate_file(f, rules)
        assert results[0].passed is True

    def test_validate_file_content_not_contains(self, tmp_path: Path):
        f = tmp_path / "safe.py"
        f.write_text("x = 1", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        rules = [
            _make_rule(
                id="VF-3",
                check_type="content_not_contains",
                check_config={"patterns": [r"eval\("]},
            ),
        ]
        results = engine.validate_file(f, rules)
        assert results[0].passed is True

    def test_validate_file_skips_irrelevant_check_types(self, tmp_path: Path):
        f = tmp_path / "any.txt"
        f.write_text("data", encoding="utf-8")

        engine = ValidationRuleEngine(tmp_path)
        rules = [_make_rule(id="VF-4", check_type="file_exists")]
        results = engine.validate_file(f, rules)
        assert results == []  # file_exists 不由 validate_file 处理


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


class TestValidationReport:
    def _build_report(
        self, results: list[ValidationResult], passed: bool = True
    ) -> ValidationReport:
        return ValidationReport(
            phase="docs",
            timestamp="2026-01-01T00:00:00",
            results=results,
            passed=passed,
            score=80,
        )

    def test_critical_failures_property(self):
        results = [
            ValidationResult("R1", True, "ok", "critical"),
            ValidationResult("R2", False, "bad", "critical"),
            ValidationResult("R3", False, "bad", "low"),
        ]
        report = self._build_report(results, passed=False)
        assert len(report.critical_failures) == 1
        assert report.critical_failures[0].rule_id == "R2"

    def test_failed_results_property(self):
        results = [
            ValidationResult("R1", True, "ok", "high"),
            ValidationResult("R2", False, "fail", "high"),
        ]
        report = self._build_report(results)
        assert len(report.failed_results) == 1

    def test_passed_results_property(self):
        results = [
            ValidationResult("R1", True, "ok", "high"),
            ValidationResult("R2", False, "fail", "high"),
        ]
        report = self._build_report(results)
        assert len(report.passed_results) == 1

    def test_to_markdown_contains_key_sections(self):
        results = [
            ValidationResult("R1", True, "pass msg", "high"),
            ValidationResult("R2", False, "fail msg", "critical", fix_suggestion="fix it"),
        ]
        report = self._build_report(results, passed=False)
        md = report.to_markdown()
        assert "验证规则报告" in md
        assert "未通过" in md
        assert "80/100" in md
        assert "关键失败项" in md
        assert "fix it" in md
        assert "详细结果" in md
        assert "R1" in md
        assert "R2" in md

    def test_to_markdown_no_critical_failures(self):
        results = [ValidationResult("R1", True, "ok", "low")]
        report = self._build_report(results)
        md = report.to_markdown()
        assert "关键失败项" not in md
        assert "通过" in md

    def test_to_dict(self):
        results = [
            ValidationResult("R1", True, "ok", "high"),
            ValidationResult("R2", False, "bad", "critical"),
        ]
        report = self._build_report(results, passed=False)
        d = report.to_dict()
        assert d["phase"] == "docs"
        assert d["passed"] is False
        assert d["score"] == 80
        assert d["total_rules"] == 2
        assert d["passed_count"] == 1
        assert d["failed_count"] == 1
        assert d["critical_failure_count"] == 1
        assert len(d["results"]) == 2


# ---------------------------------------------------------------------------
# Score calculation
# ---------------------------------------------------------------------------


class TestScoreCalculation:
    def test_all_pass_score_100(self, tmp_path: Path):
        results = [
            ValidationResult("R1", True, "ok", "critical"),
            ValidationResult("R2", True, "ok", "high"),
        ]
        score = ValidationRuleEngine._calculate_score(results)
        assert score == 100

    def test_all_fail_score_0(self, tmp_path: Path):
        results = [
            ValidationResult("R1", False, "fail", "critical"),
            ValidationResult("R2", False, "fail", "high"),
        ]
        score = ValidationRuleEngine._calculate_score(results)
        assert score == 0

    def test_empty_results_score_100(self, tmp_path: Path):
        assert ValidationRuleEngine._calculate_score([]) == 100

    def test_weighted_score(self, tmp_path: Path):
        # critical(4) passes, high(3) fails => 4/7 = 57
        results = [
            ValidationResult("R1", True, "ok", "critical"),
            ValidationResult("R2", False, "fail", "high"),
        ]
        score = ValidationRuleEngine._calculate_score(results)
        assert score == round((4.0 / 7.0) * 100)


# ---------------------------------------------------------------------------
# Disabled rules
# ---------------------------------------------------------------------------


class TestDisabledRules:
    def test_disabled_rule_not_executed(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)
        engine.rules = [
            _make_rule(
                id="DIS-1",
                enabled=False,
                check_type="file_exists",
                check_config={"file_pattern": "missing", "min_count": 1},
            ),
        ]
        report = engine.validate("all")
        assert len(report.results) == 0  # disabled 不被 get_rules_for_phase 返回


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_rule_execution_exception_returns_failed_result(self, tmp_path: Path):
        engine = ValidationRuleEngine(tmp_path)

        def exploding_checker(rule, context):
            raise RuntimeError("boom")

        engine.register_custom_checker("file_exists", exploding_checker)
        engine.rules = [_make_rule(id="ERR-1", check_type="file_exists")]
        report = engine.validate("all")
        assert report.results[0].passed is False
        assert "异常" in report.results[0].message
