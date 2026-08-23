"""Tests for schema_validator edge cases and rate_limit robustness."""

import pytest

from super_dev.config.schema_validator import ConfigSchemaValidator, validate_config


class TestSchemaValidatorEdgeCases:
    def test_non_dict_input_returns_error(self):
        errors = validate_config(None)  # type: ignore[arg-type]
        assert any("must be a dictionary" in e for e in errors)

    def test_empty_dict_returns_errors(self):
        errors = validate_config({})
        assert (
            len(errors) >= 6
        )  # name, version, platform, frontend, backend, quality_gate, phases, experts

    def test_unknown_fields_detected(self):
        errors = validate_config(
            {
                "name": "test",
                "version": "1.0.0",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "quality_gate": 90,
                "phases": ["discovery"],
                "experts": ["PM"],
                "typo_feeld": True,
                "unknown_setting": "bad",
            }
        )
        assert any("Unknown configuration fields" in e for e in errors)
        assert any("typo_feeld" in e for e in errors)

    def test_valid_config_no_errors(self):
        errors = validate_config(
            {
                "name": "test",
                "version": "1.0.0",
                "platform": "web",
                "frontend": "react",
                "backend": "node",
                "quality_gate": 90,
                "phases": ["discovery", "drafting"],
                "experts": ["PM", "CODE"],
            }
        )
        assert errors == []

    def test_validate_and_raise_raises(self):
        v = ConfigSchemaValidator()
        with pytest.raises(ValueError, match="required"):
            v.validate_and_raise({})

    def test_get_defaults_valid(self):
        v = ConfigSchemaValidator()
        defaults = v.get_defaults()
        assert validate_config(defaults) == []

    def test_adaptive_ledger_schema_is_strict_and_backward_compatible(self):
        valid = ConfigSchemaValidator().get_defaults()
        valid["adaptive_ledger"] = {
            "enabled": True,
            "auto_create": True,
            "scope_advisory": True,
        }
        assert validate_config(valid) == []

        legacy = dict(valid)
        legacy.pop("adaptive_ledger")
        assert validate_config(legacy) == []

        invalid = dict(valid)
        invalid["adaptive_ledger"] = {"enabled": False, "auto_create": True}
        assert any("requires" in item for item in validate_config(invalid))

        invalid_advisory = dict(valid)
        invalid_advisory["adaptive_ledger"] = {
            "enabled": True,
            "auto_create": False,
            "scope_advisory": True,
        }
        assert any("scope_advisory" in item for item in validate_config(invalid_advisory))

        partial = dict(valid)
        partial["adaptive_ledger"] = {"enabled": True}
        assert validate_config(partial) == []


class TestRateLimitEdgeCases:
    def test_zero_window_corrected(self):
        import os

        os.environ["SUPER_DEV_RATE_WINDOW"] = "0"
        os.environ["SUPER_DEV_RATE_LIMIT"] = "50"
        try:
            from super_dev.web.rate_limit import RateLimitMiddleware

            class _FakeApp:
                pass

            mw = RateLimitMiddleware(_FakeApp())
            assert mw.window >= 1
        finally:
            os.environ.pop("SUPER_DEV_RATE_WINDOW", None)
            os.environ.pop("SUPER_DEV_RATE_LIMIT", None)

    def test_negative_max_requests_corrected(self):
        import os

        os.environ["SUPER_DEV_RATE_LIMIT"] = "-5"
        os.environ["SUPER_DEV_RATE_WINDOW"] = "60"
        try:
            from super_dev.web.rate_limit import RateLimitMiddleware

            class _FakeApp:
                pass

            mw = RateLimitMiddleware(_FakeApp())
            assert mw.max_requests >= 0
        finally:
            os.environ.pop("SUPER_DEV_RATE_LIMIT", None)
            os.environ.pop("SUPER_DEV_RATE_WINDOW", None)

    def test_non_numeric_env_uses_defaults(self):
        import os

        os.environ["SUPER_DEV_RATE_LIMIT"] = "abc"
        os.environ["SUPER_DEV_RATE_WINDOW"] = "xyz"
        try:
            from super_dev.web.rate_limit import RateLimitMiddleware

            class _FakeApp:
                pass

            mw = RateLimitMiddleware(_FakeApp())
            assert mw.max_requests == 100
            assert mw.window == 60
        finally:
            os.environ.pop("SUPER_DEV_RATE_LIMIT", None)
            os.environ.pop("SUPER_DEV_RATE_WINDOW", None)
