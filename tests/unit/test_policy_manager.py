import json
from pathlib import Path

from super_dev.config import ConfigManager
from super_dev.policy import PipelinePolicyManager


class _Args:
    def __init__(
        self,
        *,
        skip_redteam: bool = False,
        skip_quality_gate: bool = False,
        skip_rehearsal_verify: bool = False,
        quality_threshold: int | None = None,
        cicd: str = "all",
    ) -> None:
        self.skip_redteam = skip_redteam
        self.skip_quality_gate = skip_quality_gate
        self.skip_rehearsal_verify = skip_rehearsal_verify
        self.quality_threshold = quality_threshold
        self.cicd = cicd


def test_policy_manager_returns_default_when_missing(temp_project_dir: Path) -> None:
    manager = PipelinePolicyManager(temp_project_dir)
    policy = manager.load()
    assert policy.require_redteam is True
    assert policy.require_quality_gate is True
    assert policy.require_rehearsal_verify is True
    assert policy.min_quality_threshold == 80
    assert policy.enforce_required_hosts_ready is False
    assert policy.min_required_host_score == 80


def test_policy_manager_init_and_load(temp_project_dir: Path) -> None:
    manager = PipelinePolicyManager(temp_project_dir)
    policy_file = manager.ensure_exists()
    assert policy_file.exists()
    loaded = manager.load()
    assert loaded.allowed_cicd_platforms


def test_policy_manager_enterprise_preset(temp_project_dir: Path) -> None:
    manager = PipelinePolicyManager(temp_project_dir)
    policy_file = manager.ensure_exists(preset="enterprise", force=True)
    assert policy_file.exists()
    loaded = manager.load()
    assert loaded.require_host_profile is True
    assert loaded.enforce_required_hosts_ready is False
    assert loaded.required_hosts == []


def test_validate_pipeline_args_blocks_skip_flags(temp_project_dir: Path) -> None:
    manager = PipelinePolicyManager(temp_project_dir)
    manager.ensure_exists()
    config = ConfigManager(temp_project_dir).create(name="demo")

    violations = manager.validate_pipeline_args(
        args=_Args(skip_redteam=True, skip_quality_gate=True, skip_rehearsal_verify=True),
        config=config,
    )
    assert any("skip-redteam" in item for item in violations)
    assert any("skip-quality-gate" in item for item in violations)
    assert any("skip-rehearsal-verify" in item for item in violations)


def test_validate_pipeline_args_checks_min_quality_threshold(temp_project_dir: Path) -> None:
    manager = PipelinePolicyManager(temp_project_dir)
    manager.ensure_exists()
    manager.policy_path.write_text(
        (
            "require_redteam: true\n"
            "require_quality_gate: true\n"
            "min_quality_threshold: 90\n"
            "allowed_cicd_platforms:\n"
            "  - all\n"
        ),
        encoding="utf-8",
    )
    config = ConfigManager(temp_project_dir).create(name="demo", quality_gate=85)
    violations = manager.validate_pipeline_args(
        args=_Args(quality_threshold=85),
        config=config,
    )
    assert any("质量阈值过低" in item for item in violations)


def test_validate_pipeline_args_requires_latest_host_report_when_enforced(
    temp_project_dir: Path,
) -> None:
    manager = PipelinePolicyManager(temp_project_dir)
    manager.policy_path.parent.mkdir(parents=True, exist_ok=True)
    manager.policy_path.write_text(
        (
            "require_redteam: true\n"
            "require_quality_gate: true\n"
            "min_quality_threshold: 80\n"
            "allowed_cicd_platforms:\n"
            "  - all\n"
            "require_host_profile: true\n"
            "required_hosts:\n"
            "  - codex-cli\n"
            "enforce_required_hosts_ready: true\n"
            "min_required_host_score: 85\n"
        ),
        encoding="utf-8",
    )
    config = ConfigManager(temp_project_dir).create(
        name="demo",
        host_profile_targets=["codex-cli"],
        host_profile_enforce_selected=True,
    )
    violations = manager.validate_pipeline_args(args=_Args(), config=config)
    assert any("未找到宿主兼容报告" in item for item in violations)


def test_validate_pipeline_args_checks_required_host_readiness(temp_project_dir: Path) -> None:
    manager = PipelinePolicyManager(temp_project_dir)
    manager.policy_path.parent.mkdir(parents=True, exist_ok=True)
    manager.policy_path.write_text(
        (
            "require_redteam: true\n"
            "require_quality_gate: true\n"
            "require_rehearsal_verify: true\n"
            "min_quality_threshold: 85\n"
            "allowed_cicd_platforms:\n"
            "  - github\n"
            "require_host_profile: true\n"
            "required_hosts:\n"
            "  - codex-cli\n"
            "  - claude-code\n"
            "enforce_required_hosts_ready: true\n"
            "min_required_host_score: 85\n"
        ),
        encoding="utf-8",
    )
    config = ConfigManager(temp_project_dir).create(
        name="demo",
        host_profile_targets=["codex-cli", "claude-code"],
        host_profile_enforce_selected=True,
    )

    output_dir = temp_project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    compatibility_file = output_dir / "demo-host-compatibility.json"
    compatibility_file.write_text(
        json.dumps(
            {
                "compatibility": {
                    "hosts": {
                        "codex-cli": {"ready": True, "score": 88.0},
                        "claude-code": {"ready": False, "score": 84.0},
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    violations = manager.validate_pipeline_args(args=_Args(cicd="github"), config=config)
    assert any("claude-code" in item and "ready" in item for item in violations)
