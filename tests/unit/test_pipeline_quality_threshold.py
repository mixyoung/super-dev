"""The pipeline must evaluate the same threshold that its policy validated."""

import json

import pytest

from super_dev.cli import SuperDevCLI
from super_dev.reviewers.quality_gate import QualityGateChecker, QualityGateResult


@pytest.mark.parametrize(
    ("configured", "requested", "policy_minimum", "expected"),
    [
        (95, None, 80, 95),
        (90, 85, 80, 85),
        (None, None, 80, 80),
        (75, None, 70, 75),
        (90, 0, 0, 0),
        (95, 85, 90, None),
        (85, None, 90, None),
    ],
)
def test_pipeline_quality_threshold_precedence(
    tmp_path, monkeypatch, configured, requested, policy_minimum, expected
):
    monkeypatch.chdir(tmp_path)
    config = "name: threshold-demo\nplatform: cli\nfrontend: none\nbackend: python\n"
    if configured is not None:
        config += f"quality_gate: {configured}\n"
    (tmp_path / "super-dev.yaml").write_text(config, encoding="utf-8")
    state_dir = tmp_path / ".super-dev" / "runs"
    state_dir.mkdir(parents=True)
    (state_dir.parent / "policy.yaml").write_text(
        f"min_quality_threshold: {policy_minimum}\n", encoding="utf-8"
    )
    (state_dir / "last-pipeline.json").write_text(
        json.dumps({"status": "waiting_quality_revision", "resume_from_stage": "6"}),
        encoding="utf-8",
    )
    cli = SuperDevCLI()
    # Isolate threshold routing from previously tested document/preview gates.
    monkeypatch.setattr(cli, "_docs_confirmation_is_confirmed", lambda project_dir: True)
    monkeypatch.setattr(cli, "_preview_confirmation_is_confirmed", lambda project_dir: True)
    observed = []

    def failed_check(checker, redteam_report=None):
        observed.append(checker.threshold_override)
        # Stop at quality; this test must not proceed to packaging/deployment.
        return QualityGateResult(passed=False, total_score=0, weighted_score=0.0)

    monkeypatch.setattr(QualityGateChecker, "check", failed_check)
    command = [
        "pipeline",
        "threshold routing regression",
        "--name",
        "threshold-demo",
        "--platform",
        "cli",
        "--frontend",
        "none",
        "--backend",
        "python",
        "--offline",
        "--resume",
    ]
    if requested is not None:
        command.extend(["--quality-threshold", str(requested)])
    assert cli.run(command) == 1
    if expected is None:
        assert not observed
    else:
        assert observed and all(value == expected for value in observed)
    if expected is not None:
        state = json.loads((state_dir / "last-pipeline.json").read_text(encoding="utf-8"))
        assert state["failure_reason"] == "quality_gate_failed"
        assert state["pipeline_args"]["quality_threshold"] == requested
