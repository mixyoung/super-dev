from pathlib import Path

import pytest

from super_dev.host_diagnostics import build_host_injection_closure


def _surface_sets(
    *, default_paths: list[Path], optional_user_paths: list[Path]
) -> dict[str, list[Path]]:
    return {
        "official_project": default_paths,
        "official_user": [],
        "optional_project": [],
        "optional_user": optional_user_paths,
        "compatibility": [],
        "official_skill": [],
        "optional_skill": [],
        "compatibility_skill": [],
        "required_slash": [],
        "optional_slash": [],
        "compatibility_slash": [],
    }


def test_build_host_injection_closure_marks_project_first_ready_with_opt_in_available(
    tmp_path: Path,
) -> None:
    project_surface = tmp_path / "AGENTS.md"
    project_surface.write_text("# agents\n", encoding="utf-8")
    optional_user_surface = tmp_path / "user-command.md"

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(
            default_paths=[project_surface],
            optional_user_paths=[optional_user_surface],
        ),
    )

    assert closure["status"] == "project_default_ready_with_user_opt_in_available"
    assert closure["project_default_ready"] is True
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is True
    assert closure["user_surface_opt_in_available"] is True
    assert closure["explicit_user_surfaces_ready"] is False
    assert closure["opt_in_flag"] == "--with-user-surfaces"
    assert str(optional_user_surface) in closure["missing_optional_user_surfaces"]
    assert closure["competition_project_surfaces_ready"] is False
    assert closure["missing_managed_competition_project_surfaces"] == []


def test_build_host_injection_closure_marks_explicit_user_surfaces_ready(
    tmp_path: Path,
) -> None:
    project_surface = tmp_path / "AGENTS.md"
    optional_user_surface = tmp_path / "user-command.md"
    project_surface.write_text("# agents\n", encoding="utf-8")
    optional_user_surface.write_text("# cmd\n", encoding="utf-8")

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(
            default_paths=[project_surface],
            optional_user_paths=[optional_user_surface],
        ),
    )

    assert closure["status"] == "project_default_ready_with_user_opt_in_enabled"
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is True
    assert closure["explicit_user_surfaces_ready"] is True
    assert closure["missing_optional_user_surfaces"] == []


def test_build_host_injection_closure_marks_missing_competition_project_surfaces(
    tmp_path: Path,
) -> None:
    project_surface = tmp_path / "AGENTS.md"
    competition_surface = tmp_path / ".qoder" / "skills" / "super-dev-seeai" / "SKILL.md"
    project_surface.write_text("# agents\n", encoding="utf-8")

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(
            default_paths=[project_surface],
            optional_user_paths=[],
        ),
        managed_competition_project_paths=[competition_surface],
    )

    assert closure["competition_project_surfaces_ready"] is False
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is False
    assert str(competition_surface) in closure["missing_managed_competition_project_surfaces"]
    assert closure["status"].endswith("_competition_incomplete")


def test_build_host_injection_closure_keeps_standard_ready_when_competition_user_surface_missing(
    tmp_path: Path,
) -> None:
    user_skill_surface = tmp_path / ".workbuddy" / "skills" / "super-dev" / "SKILL.md"
    user_skill_surface.parent.mkdir(parents=True, exist_ok=True)
    user_skill_surface.write_text("# skill\n", encoding="utf-8")
    seeai_user_surface = tmp_path / ".workbuddy" / "skills" / "super-dev-seeai" / "SKILL.md"

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(
            default_paths=[],
            optional_user_paths=[],
        )
        | {
            "official_user": [user_skill_surface],
            "official_skill": [],
        },
        managed_competition_user_paths=[seeai_user_surface],
    )

    assert closure["project_default_ready"] is True
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is False
    assert closure["competition_user_surfaces_ready"] is False
    assert str(seeai_user_surface) in closure["missing_managed_competition_user_surfaces"]


@pytest.mark.parametrize("user_exists", [False, True])
def test_project_seeai_does_not_require_optional_user_copy(
    tmp_path: Path, user_exists: bool
) -> None:
    project = tmp_path / "AGENTS.local.md"
    project_seeai = tmp_path / "project-seeai.md"
    user_seeai = tmp_path / "user-seeai.md"
    project.write_text("# project\n", encoding="utf-8")
    project_seeai.write_text("# SEEAI\n", encoding="utf-8")
    if user_exists:
        user_seeai.write_text("# user SEEAI\n", encoding="utf-8")

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(default_paths=[project], optional_user_paths=[user_seeai]),
        managed_competition_project_paths=[project_seeai],
        managed_competition_user_paths=[user_seeai],
    )

    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is True
    assert closure["competition_flow_label"] == "SEEAI 比赛模式可直接开工"
    assert not closure["status"].endswith("_competition_incomplete")
    assert "SEEAI 用户级补充面待补齐" not in closure["label"]
    assert "SEEAI 用户级补充面还未闭环" not in closure["summary"]
    assert closure["managed_competition_user_surfaces"] == [str(user_seeai)]
    assert closure["competition_user_surfaces_ready"] is user_exists
    assert closure["missing_managed_competition_user_surfaces"] == (
        [] if user_exists else [str(user_seeai)]
    )
    assert closure["missing_optional_user_surfaces"] == ([] if user_exists else [str(user_seeai)])


@pytest.mark.parametrize("user_exists", [False, True])
def test_optional_user_seeai_cannot_replace_missing_project_seeai(
    tmp_path: Path, user_exists: bool
) -> None:
    project = tmp_path / "AGENTS.local.md"
    project_seeai = tmp_path / "project-seeai.md"
    user_seeai = tmp_path / "user-seeai.md"
    project.write_text("# project\n", encoding="utf-8")
    if user_exists:
        user_seeai.write_text("# user SEEAI\n", encoding="utf-8")

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(default_paths=[project], optional_user_paths=[user_seeai]),
        managed_competition_project_paths=[project_seeai],
        managed_competition_user_paths=[user_seeai],
    )

    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is False
    assert closure["competition_flow_label"] == "SEEAI 比赛模式待补齐项目补充面"
    assert closure["missing_managed_competition_project_surfaces"] == [str(project_seeai)]
    assert closure["competition_user_surfaces_ready"] is user_exists
    assert "SEEAI 用户级补充面" not in closure["summary"]


@pytest.mark.parametrize("default_exists,host_ready", [(False, True), (True, False)])
def test_seeai_files_do_not_override_failed_default_readiness(
    tmp_path: Path, default_exists: bool, host_ready: bool
) -> None:
    project = tmp_path / "AGENTS.local.md"
    project_seeai = tmp_path / "project-seeai.md"
    user_seeai = tmp_path / "user-seeai.md"
    if default_exists:
        project.write_text("# project\n", encoding="utf-8")
    project_seeai.write_text("# SEEAI\n", encoding="utf-8")
    user_seeai.write_text("# user SEEAI\n", encoding="utf-8")

    closure = build_host_injection_closure(
        host_ready=host_ready,
        surface_sets=_surface_sets(default_paths=[project], optional_user_paths=[user_seeai]),
        managed_competition_project_paths=[project_seeai],
        managed_competition_user_paths=[user_seeai],
    )

    assert closure["standard_flow_ready"] is False
    assert closure["competition_flow_ready"] is False
    assert "默认接入检查未通过" in closure["competition_flow_label"]
    assert closure["competition_project_surfaces_ready"] is True
    assert closure["competition_user_surfaces_ready"] is True


def test_user_default_seeai_becomes_ready_with_its_required_file(tmp_path: Path) -> None:
    user_standard = tmp_path / "user-standard.md"
    user_seeai = tmp_path / "user-seeai.md"
    user_standard.write_text("# standard\n", encoding="utf-8")
    user_seeai.write_text("# SEEAI\n", encoding="utf-8")

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(default_paths=[], optional_user_paths=[])
        | {"official_user": [user_standard]},
        managed_competition_user_paths=[user_seeai],
    )

    assert closure["scope"] == "user-skill-default"
    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is True
    assert closure["competition_user_surfaces_ready"] is True


def test_project_default_without_project_seeai_keeps_user_seeai_requirement(tmp_path: Path) -> None:
    project = tmp_path / "AGENTS.md"
    project.write_text("# project\n", encoding="utf-8")
    user_seeai = tmp_path / "user-seeai.md"

    closure = build_host_injection_closure(
        host_ready=True,
        surface_sets=_surface_sets(default_paths=[project], optional_user_paths=[user_seeai]),
        managed_competition_user_paths=[user_seeai],
    )

    assert closure["standard_flow_ready"] is True
    assert closure["competition_flow_ready"] is False
    assert closure["competition_flow_label"] == "SEEAI 比赛模式待补齐用户级补充面"
