from __future__ import annotations

from pathlib import Path

import pytest

from super_dev.cli import SuperDevCLI
from super_dev.config import ConfigManager
from super_dev.creators import SpecBuilder
from super_dev.scope_advisory import resolve_pipeline_scope_declaration
from super_dev.shadow_ledger_store import load_shadow_ledger


def _enable_scope_advisory(project_dir: Path) -> None:
    ConfigManager(project_dir).create(
        name="scope-declaration",
        adaptive_ledger={
            "enabled": True,
            "auto_create": True,
            "scope_advisory": True,
        },
    )


def test_pipeline_parser_accepts_structured_changed_surfaces() -> None:
    cli = SuperDevCLI()

    args = cli.parser.parse_args(
        [
            "pipeline",
            "修复订单接口",
            "--changed-surfaces",
            "backend",
            "api",
            "--governance-depth",
            "bounded",
        ]
    )

    assert args.changed_surfaces == ["backend", "api"]
    assert args.governance_depth == "bounded"


def test_spec_parser_accepts_structured_scope_and_work_mode() -> None:
    cli = SuperDevCLI()

    args = cli.parser.parse_args(
        [
            "spec",
            "propose",
            "fix-order-api",
            "--title",
            "修复订单接口",
            "--description",
            "修复订单状态错误",
            "--changed-surfaces",
            "backend",
            "api",
            "--work-mode",
            "patch",
            "--governance-depth",
            "bounded",
        ]
    )

    assert args.changed_surfaces == ["backend", "api"]
    assert args.work_mode == "patch"
    assert args.governance_depth == "bounded"


def test_parser_rejects_unknown_changed_surface() -> None:
    cli = SuperDevCLI()

    with pytest.raises(SystemExit):
        cli.parser.parse_args(
            [
                "pipeline",
                "未知范围",
                "--changed-surfaces",
                "unknown-surface",
            ]
        )


def test_empty_pipeline_scope_remains_incomplete_and_conservative() -> None:
    declaration = resolve_pipeline_scope_declaration(
        changed_surfaces=[],
        request_mode="bugfix",
        scenario="1-N+1",
    )

    assert declaration.changed_surfaces == ()
    assert declaration.scope_complete is False
    assert declaration.work_mode == "patch"
    assert declaration.governance_depth == "bounded"


def test_pipeline_bugfix_scope_survives_resume_and_reaches_spec_ledger(
    temp_project_dir: Path,
) -> None:
    _enable_scope_advisory(temp_project_dir)
    initial = resolve_pipeline_scope_declaration(
        changed_surfaces=["backend", "api", "backend"],
        request_mode="bugfix",
        scenario="1-N+1",
    )
    resumed = resolve_pipeline_scope_declaration(
        changed_surfaces=list(initial.changed_surfaces),
        request_mode="bugfix",
        scenario="1-N+1",
        governance_depth=initial.governance_depth,
    )

    assert resumed == initial
    assert resumed.changed_surfaces == ("api", "backend")
    assert resumed.work_mode == "patch"
    assert resumed.governance_depth == "bounded"

    builder = SpecBuilder(
        project_dir=temp_project_dir,
        name="pipeline-bugfix-scope",
        description="修复订单接口",
    )
    change_id = builder.create_change(
        requirements=[],
        tech_stack={"platform": "web", "frontend": "react", "backend": "node"},
        scenario="1-N+1",
        changed_surfaces=set(resumed.changed_surfaces),
        work_mode=resumed.work_mode,
        governance_depth=resumed.governance_depth,
    )
    ledger = load_shadow_ledger(
        temp_project_dir,
        temp_project_dir / ".super-dev" / "changes" / change_id / "ledger.json",
    ).ledger

    assert ledger.work_mode == "patch"
    assert ledger.governance_depth == "bounded"
    assert ledger.intent.value == "debug"
    assert ledger.scope_advisory is not None
    assert ledger.scope_advisory.scope_complete is True
    assert ledger.scope_advisory.changed_surfaces == ["api", "backend"]
    assert ledger.get_stage("frontend").resolution.value == "EXECUTE"


def test_spec_propose_creates_complete_advisory_from_declared_scope(
    temp_project_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_scope_advisory(temp_project_dir)
    cli = SuperDevCLI()
    monkeypatch.chdir(temp_project_dir)
    monkeypatch.setattr(cli, "_ensure_execution_gates", lambda *_args, **_kwargs: True)
    args = cli.parser.parse_args(
        [
            "spec",
            "propose",
            "fix-order-api",
            "--title",
            "修复订单接口",
            "--description",
            "修复订单状态错误",
            "--changed-surfaces",
            "backend",
            "api",
            "--work-mode",
            "patch",
            "--governance-depth",
            "bounded",
        ]
    )

    assert cli._cmd_spec(args) == 0

    ledger_path = (
        temp_project_dir / ".super-dev" / "changes" / "fix-order-api" / "ledger.json"
    )
    ledger = load_shadow_ledger(temp_project_dir, ledger_path).ledger
    assert ledger.work_mode == "patch"
    assert ledger.governance_depth == "bounded"
    assert ledger.intent.value == "debug"
    assert ledger.scope_advisory is not None
    assert ledger.scope_advisory.scope_complete is True
    assert ledger.scope_advisory.changed_surfaces == ["api", "backend"]
    assert ledger.get_stage("frontend").resolution.value == "EXECUTE"
    frontend_advice = next(
        item for item in ledger.scope_advisory.recommendations if item.stage == "frontend"
    )
    assert frontend_advice.recommended_resolution.value == "NOT_APPLICABLE"
    assert frontend_advice.approval_required is True


def test_spec_propose_without_declared_scope_keeps_full_advisory(
    temp_project_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_scope_advisory(temp_project_dir)
    cli = SuperDevCLI()
    monkeypatch.chdir(temp_project_dir)
    monkeypatch.setattr(cli, "_ensure_execution_gates", lambda *_args, **_kwargs: True)
    args = cli.parser.parse_args(
        [
            "spec",
            "propose",
            "unknown-scope",
            "--title",
            "范围尚未明确",
            "--description",
            "先保持完整流程",
        ]
    )

    assert cli._cmd_spec(args) == 0

    ledger = load_shadow_ledger(
        temp_project_dir,
        temp_project_dir / ".super-dev" / "changes" / "unknown-scope" / "ledger.json",
    ).ledger
    assert ledger.scope_advisory is not None
    assert ledger.scope_advisory.scope_complete is False
    assert all(not item.approval_required for item in ledger.scope_advisory.recommendations)


def test_spec_propose_without_scaffold_does_not_create_ledger_early(
    temp_project_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_scope_advisory(temp_project_dir)
    cli = SuperDevCLI()
    monkeypatch.chdir(temp_project_dir)
    monkeypatch.setattr(cli, "_ensure_execution_gates", lambda *_args, **_kwargs: True)
    args = cli.parser.parse_args(
        [
            "spec",
            "propose",
            "proposal-only",
            "--title",
            "只创建提案",
            "--description",
            "暂不生成任务清单",
            "--changed-surfaces",
            "backend",
            "--no-scaffold",
        ]
    )

    assert cli._cmd_spec(args) == 0
    assert not (
        temp_project_dir / ".super-dev" / "changes" / "proposal-only" / "ledger.json"
    ).exists()


def test_spec_propose_never_overwrites_existing_scope_ledger(
    temp_project_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_scope_advisory(temp_project_dir)
    cli = SuperDevCLI()
    monkeypatch.chdir(temp_project_dir)
    monkeypatch.setattr(cli, "_ensure_execution_gates", lambda *_args, **_kwargs: True)
    first_args = cli.parser.parse_args(
        [
            "spec",
            "propose",
            "stable-scope",
            "--title",
            "修复订单接口",
            "--description",
            "第一次登记后端范围",
            "--changed-surfaces",
            "backend",
            "api",
            "--work-mode",
            "patch",
            "--governance-depth",
            "bounded",
        ]
    )
    assert cli._cmd_spec(first_args) == 0
    ledger_path = (
        temp_project_dir / ".super-dev" / "changes" / "stable-scope" / "ledger.json"
    )
    original = ledger_path.read_bytes()

    second_args = cli.parser.parse_args(
        [
            "spec",
            "propose",
            "stable-scope",
            "--title",
            "改成前端范围",
            "--description",
            "尝试再次登记前端范围",
            "--changed-surfaces",
            "frontend",
            "--work-mode",
            "evolve",
            "--governance-depth",
            "architectural",
        ]
    )
    assert cli._cmd_spec(second_args) == 0

    assert ledger_path.read_bytes() == original
    ledger = load_shadow_ledger(temp_project_dir, ledger_path).ledger
    assert ledger.scope_advisory is not None
    assert ledger.scope_advisory.changed_surfaces == ["api", "backend"]
