from __future__ import annotations

from super_dev.config.manager import ConfigManager
from super_dev.config.schema_validator import ConfigSchemaValidator, validate_config


def test_extensions_default_to_disabled(tmp_path) -> None:
    config = ConfigManager(tmp_path).config

    assert config.extensions == {
        "enabled": False,
        "allowed_builtin_methods": [],
    }


def test_extension_config_is_strict_and_phase_one_is_bounded() -> None:
    config = ConfigSchemaValidator().get_defaults()
    config["extensions"] = {
        "enabled": True,
        "allowed_builtin_methods": ["unknown-method"],
        "surprise": True,
    }

    errors = validate_config(config)

    assert any("unknown fields" in item for item in errors)
    assert any("contract-probe" in item for item in errors)


def test_partial_extension_config_merges_safe_defaults(tmp_path) -> None:
    (tmp_path / "super-dev.yaml").write_text(
        "name: demo\nfrontend: next\nbackend: node\nextensions:\n  enabled: true\n",
        encoding="utf-8",
    )

    loaded = ConfigManager(tmp_path).config

    assert loaded.extensions == {
        "enabled": True,
        "allowed_builtin_methods": [],
    }
