"""Schema validator for super-dev.yaml configuration files."""

import re

VALID_PLATFORMS = {"web", "mobile", "desktop", "api"}
VALID_PHASES = {"discovery", "intelligence", "drafting", "redteam", "qa", "delivery", "deployment"}
VALID_EXPERTS = {"PM", "ARCHITECT", "UI", "UX", "SECURITY", "CODE"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
KNOWN_FIELDS = {
    "name",
    "version",
    "platform",
    "frontend",
    "backend",
    "description",
    "domain",
    "quality_gate",
    "phases",
    "experts",
    "output_dir",
    "license",
    "cli",
    "host_compatibility_min_score",
    "host_compatibility_min_ready_hosts",
    "host_profile_enforce_selected",
    "host_profile_targets",
    "knowledge_allowed_domains",
    "knowledge_cache_ttl_seconds",
    "language_preferences",
    "ui_library",
    "style_solution",
    "state_management",
    "testing_frameworks",
    "design_inspiration_slug",
    "database",
    "author",
    "execution_mode",
    "overseer_enabled",
    "codex_review_enabled",
    "codex_review_phases",
    "overseer_halt_on_critical",
    "plan_failure_budget",
    "adaptive_ledger",
    "extensions",
}


def validate_config(config: dict) -> list[str]:
    """Validate a super-dev.yaml configuration dict.

    Args:
        config: Parsed YAML configuration dictionary.

    Returns:
        List of validation error messages. Empty if the config is valid.
    """
    if not isinstance(config, dict):
        return ["Configuration must be a dictionary"]

    errors: list[str] = []

    # Unknown fields warning
    unknown = set(config.keys()) - KNOWN_FIELDS
    if unknown:
        errors.append(f"Unknown configuration fields (possible typos): {sorted(unknown)}")

    # Required string fields
    for field in ("name", "frontend", "backend"):
        val = config.get(field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"'{field}' is required and must be a non-empty string")

    # version — semver
    version = config.get("version")
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        errors.append("'version' must match semver pattern (x.y.z)")

    # platform
    platform = config.get("platform")
    if platform not in VALID_PLATFORMS:
        errors.append(f"'platform' must be one of {sorted(VALID_PLATFORMS)}")

    # quality_gate
    qg = config.get("quality_gate")
    if not isinstance(qg, int) or not (0 <= qg <= 100):
        errors.append("'quality_gate' must be an integer between 0 and 100")

    # phases
    phases = config.get("phases")
    if not isinstance(phases, list) or not phases:
        errors.append("'phases' must be a non-empty list")
    elif isinstance(phases, list):
        invalid = [p for p in phases if p not in VALID_PHASES]
        if invalid:
            errors.append(f"'phases' contains invalid entries: {invalid}")

    # experts
    experts = config.get("experts")
    if not isinstance(experts, list) or not experts:
        errors.append("'experts' must be a list with at least one expert")
    elif isinstance(experts, list):
        invalid = [e for e in experts if e not in VALID_EXPERTS]
        if invalid:
            errors.append(f"'experts' contains invalid entries: {invalid}")

    # Optional fields
    host_score = config.get("host_compatibility_min_score")
    if host_score is not None and (not isinstance(host_score, int) or not (0 <= host_score <= 100)):
        errors.append(
            "'host_compatibility_min_score' must be an integer between 0 and 100 if present"
        )

    ttl = config.get("knowledge_cache_ttl_seconds")
    if ttl is not None and (not isinstance(ttl, int) or ttl <= 0):
        errors.append("'knowledge_cache_ttl_seconds' must be a positive integer if present")

    design_inspiration_slug = config.get("design_inspiration_slug")
    if design_inspiration_slug is not None and not isinstance(design_inspiration_slug, str):
        errors.append("'design_inspiration_slug' must be a string if present")

    adaptive_ledger = config.get(
        "adaptive_ledger",
        {"enabled": False, "auto_create": False, "scope_advisory": False},
    )
    if not isinstance(adaptive_ledger, dict):
        errors.append("'adaptive_ledger' must be an object")
    else:
        adaptive_ledger = {
            "enabled": False,
            "auto_create": False,
            "scope_advisory": False,
            **adaptive_ledger,
        }
        for field_name in ("enabled", "auto_create", "scope_advisory"):
            if not isinstance(adaptive_ledger.get(field_name), bool):
                errors.append(f"'adaptive_ledger.{field_name}' must be a boolean")
        if (
            adaptive_ledger.get("auto_create") is True
            and adaptive_ledger.get("enabled") is not True
        ):
            errors.append("'adaptive_ledger.auto_create' requires 'adaptive_ledger.enabled'")
        if adaptive_ledger.get("scope_advisory") is True and (
            adaptive_ledger.get("enabled") is not True
            or adaptive_ledger.get("auto_create") is not True
        ):
            errors.append(
                "'adaptive_ledger.scope_advisory' requires enabled automatic creation"
            )

    extensions = config.get(
        "extensions",
        {"enabled": False, "allowed_builtin_methods": []},
    )
    if not isinstance(extensions, dict):
        errors.append("'extensions' must be an object")
    else:
        extensions = {
            "enabled": False,
            "allowed_builtin_methods": [],
            **extensions,
        }
        unknown_extension_fields = set(extensions) - {
            "enabled",
            "allowed_builtin_methods",
        }
        if unknown_extension_fields:
            errors.append(
                f"'extensions' contains unknown fields: {sorted(unknown_extension_fields)}"
            )
        if not isinstance(extensions.get("enabled"), bool):
            errors.append("'extensions.enabled' must be a boolean")
        allowed_methods = extensions.get("allowed_builtin_methods")
        if not isinstance(allowed_methods, list) or any(
            not isinstance(item, str) or not item.strip() for item in allowed_methods or []
        ):
            errors.append("'extensions.allowed_builtin_methods' must be a string list")
        elif len(set(allowed_methods)) != len(allowed_methods):
            errors.append("'extensions.allowed_builtin_methods' must not contain duplicates")
        elif any(item != "contract-probe" for item in allowed_methods):
            errors.append("only 'contract-probe' is supported in phase 1")

    return errors


class ConfigSchemaValidator:
    """Validates super-dev.yaml configuration against the expected schema."""

    def validate(self, config: dict) -> list[str]:
        """Validate config and return a list of error messages."""
        return validate_config(config)

    def validate_and_raise(self, config: dict) -> None:
        """Validate config and raise ValueError if any errors are found.

        Args:
            config: Parsed YAML configuration dictionary.

        Raises:
            ValueError: With all validation errors joined by '; '.
        """
        errors = self.validate(config)
        if errors:
            raise ValueError("; ".join(errors))

    def get_defaults(self) -> dict:
        """Return sensible default values for all configuration fields."""
        return {
            "name": "my-project",
            "version": "0.1.0",
            "platform": "web",
            "frontend": "react",
            "backend": "python",
            "quality_gate": 90,
            "phases": [
                "discovery",
                "intelligence",
                "drafting",
                "redteam",
                "qa",
                "delivery",
                "deployment",
            ],
            "experts": ["PM", "ARCHITECT", "CODE"],
            "host_compatibility_min_score": 70,
            "knowledge_cache_ttl_seconds": 3600,
            "adaptive_ledger": {
                "enabled": False,
                "auto_create": False,
                "scope_advisory": False,
            },
            "extensions": {
                "enabled": False,
                "allowed_builtin_methods": [],
            },
        }
