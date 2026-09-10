# ruff: noqa: I001
"""
Spec 管理器增强测试 - 覆盖模板差异化、时间估算、变更影响分析

测试对象: super_dev.specs.manager (SpecManager + ChangeManager)
"""

import textwrap

import pytest
import yaml
from super_dev.specs.manager import ChangeManager, SpecManager
from super_dev.specs.models import (
    Change,
    ChangeStatus,
    DeltaType,
    Proposal,
    Requirement,
    Scenario,
    Spec,
    SpecDelta,
    Task,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_dir(tmp_path):
    return tmp_path


@pytest.fixture()
def spec_manager(project_dir):
    mgr = SpecManager(project_dir)
    mgr.init()
    return mgr


@pytest.fixture()
def change_manager(project_dir):
    mgr = ChangeManager(project_dir)
    mgr.init()
    return mgr


# ---------------------------------------------------------------------------
# SpecManager 基本操作
# ---------------------------------------------------------------------------


class TestSpecManagerBasics:
    def test_init_creates_specs_dir(self, spec_manager, project_dir):
        specs_dir = project_dir / ".super-dev" / "specs"
        assert specs_dir.exists()
        assert (specs_dir / ".gitkeep").exists()

    def test_get_spec_path(self, spec_manager):
        path = spec_manager.get_spec_path("auth-module")
        assert path.name == "spec.md"

    def test_get_spec_path_rejects_traversal(self, spec_manager):
        with pytest.raises(ValueError):
            spec_manager.get_spec_path("../../etc/passwd")

    def test_save_and_load_spec(self, spec_manager):
        spec = Spec(name="user-auth", title="User Authentication")
        spec.purpose = "Handle user login and registration"
        spec.requirements.append(
            Requirement(
                name="Login",
                keyword="SHALL",
                description="support email/password login",
                scenarios=[
                    Scenario(
                        given="valid credentials",
                        when="user submits login form",
                        then="user receives auth token",
                    )
                ],
            )
        )
        spec_manager.save_spec(spec)
        loaded = spec_manager.load_spec("user-auth")
        assert loaded is not None
        assert loaded.title == "User Authentication"
        assert len(loaded.requirements) == 1

    def test_load_nonexistent_returns_none(self, spec_manager):
        assert spec_manager.load_spec("nonexistent") is None

    def test_list_specs_empty(self, spec_manager):
        assert spec_manager.list_specs() == []

    def test_list_specs_with_entries(self, spec_manager):
        spec_manager.save_spec(Spec(name="spec-a", title="A"))
        spec_manager.save_spec(Spec(name="spec-b", title="B"))
        specs = spec_manager.list_specs()
        assert "spec-a" in specs and "spec-b" in specs

    def test_delete_spec(self, spec_manager):
        spec_manager.save_spec(Spec(name="to-delete", title="Delete Me"))
        spec_manager.delete_spec("to-delete")
        assert spec_manager.load_spec("to-delete") is None


# ---------------------------------------------------------------------------
# Spec 模板差异化
# ---------------------------------------------------------------------------


class TestSpecTemplateDifferentiation:
    def test_shall_keyword_persists(self, spec_manager):
        spec = Spec(name="test-shall", title="SHALL test")
        spec.requirements.append(
            Requirement(name="R1", keyword="SHALL", description="be implemented")
        )
        spec_manager.save_spec(spec)
        loaded = spec_manager.load_spec("test-shall")
        assert loaded.requirements[0].keyword == "SHALL"

    def test_must_keyword_persists(self, spec_manager):
        spec = Spec(name="test-must", title="MUST test")
        spec.requirements.append(Requirement(name="R1", keyword="MUST", description="be enforced"))
        spec_manager.save_spec(spec)
        loaded = spec_manager.load_spec("test-must")
        assert loaded.requirements[0].keyword == "MUST"

    def test_should_keyword_persists(self, spec_manager):
        spec = Spec(name="test-should", title="SHOULD test")
        spec.requirements.append(
            Requirement(name="R1", keyword="SHOULD", description="be recommended")
        )
        spec_manager.save_spec(spec)
        loaded = spec_manager.load_spec("test-should")
        assert loaded.requirements[0].keyword == "SHOULD"

    def test_may_keyword_persists(self, spec_manager):
        spec = Spec(name="test-may", title="MAY test")
        spec.requirements.append(Requirement(name="R1", keyword="MAY", description="be optional"))
        spec_manager.save_spec(spec)
        loaded = spec_manager.load_spec("test-may")
        assert loaded.requirements[0].keyword == "MAY"

    def test_multiple_requirements_preserved(self, spec_manager):
        spec = Spec(name="multi", title="Multi Req")
        spec.requirements = [
            Requirement(name="R1", keyword="SHALL", description="first"),
            Requirement(name="R2", keyword="MUST", description="second"),
            Requirement(name="R3", keyword="SHOULD", description="third"),
        ]
        spec_manager.save_spec(spec)
        loaded = spec_manager.load_spec("multi")
        assert len(loaded.requirements) == 3

    def test_scenario_roundtrip(self, spec_manager):
        spec = Spec(name="scenario-test", title="Scenario Test")
        spec.requirements.append(
            Requirement(
                name="Auth",
                keyword="SHALL",
                description="authenticate users",
                scenarios=[
                    Scenario(given="valid token", when="request made", then="200 OK"),
                    Scenario(given="invalid token", when="request made", then="401 Unauthorized"),
                ],
            )
        )
        spec_manager.save_spec(spec)
        loaded = spec_manager.load_spec("scenario-test")
        assert len(loaded.requirements[0].scenarios) == 2


# ---------------------------------------------------------------------------
# ChangeManager 基本操作
# ---------------------------------------------------------------------------


class TestChangeManagerBasics:
    def test_init_creates_changes_dir(self, change_manager, project_dir):
        assert (project_dir / ".super-dev" / "changes").exists()

    def test_get_change_path_rejects_traversal(self, change_manager):
        with pytest.raises(ValueError):
            change_manager.get_change_path("../../etc/passwd")

    def test_save_and_load_change(self, change_manager):
        change = Change(id="feature-login", title="Add Login")
        change.proposal = Proposal(title="Login", description="Add user login flow")
        change.tasks = [
            Task(id="1", title="Design API", status=TaskStatus.COMPLETED),
            Task(id="2", title="Implement backend", status=TaskStatus.PENDING),
        ]
        change_manager.save_change(change)
        loaded = change_manager.load_change("feature-login")
        assert loaded is not None
        assert loaded.title == "Add Login"
        assert len(loaded.tasks) == 2

    def test_load_nonexistent_returns_none(self, change_manager):
        assert change_manager.load_change("nonexistent") is None

    def test_list_changes_empty(self, change_manager):
        assert change_manager.list_changes() == []

    def test_list_changes_with_entries(self, change_manager):
        change_manager.save_change(Change(id="c1", title="C1", status=ChangeStatus.DRAFT))
        change_manager.save_change(Change(id="c2", title="C2", status=ChangeStatus.PROPOSED))
        assert len(change_manager.list_changes()) == 2

    def test_list_changes_filter_by_status(self, change_manager):
        change_manager.save_change(Change(id="c1", title="C1", status=ChangeStatus.DRAFT))
        change_manager.save_change(Change(id="c2", title="C2", status=ChangeStatus.PROPOSED))
        drafts = change_manager.list_changes(status=ChangeStatus.DRAFT)
        assert len(drafts) == 1

    def test_delete_change(self, change_manager):
        change_manager.save_change(Change(id="to-delete", title="Delete Me"))
        change_manager.delete_change("to-delete")
        assert change_manager.load_change("to-delete") is None


# ---------------------------------------------------------------------------
# 变更影响分析 (archive_change)
# ---------------------------------------------------------------------------


class TestChangeImpactAnalysis:
    def test_archive_adds_new_requirements(self, change_manager, spec_manager):
        delta = SpecDelta(
            spec_name="auth",
            delta_type=DeltaType.ADDED,
            description="Add",
            requirements=[Requirement(name="Login", keyword="SHALL", description="support login")],
        )
        change = Change(id="add-login", title="Add Login")
        change.spec_deltas = [delta]
        change_manager.save_change(change)
        change_manager.archive_change("add-login", spec_manager)
        spec = spec_manager.load_spec("auth")
        assert spec is not None
        assert len(spec.requirements) == 1

    def test_archive_modifies_existing(self, change_manager, spec_manager):
        spec = Spec(name="auth", title="Auth")
        spec.requirements = [Requirement(name="Login", keyword="SHALL", description="v1")]
        spec_manager.save_spec(spec)
        delta = SpecDelta(
            spec_name="auth",
            delta_type=DeltaType.MODIFIED,
            description="Update",
            requirements=[Requirement(name="Login", keyword="MUST", description="v2 with MFA")],
        )
        change = Change(id="update-login", title="Update")
        change.spec_deltas = [delta]
        change_manager.save_change(change)
        change_manager.archive_change("update-login", spec_manager)
        loaded = spec_manager.load_spec("auth")
        assert loaded.requirements[0].keyword == "MUST"

    def test_archive_removes_requirements(self, change_manager, spec_manager):
        spec = Spec(name="auth", title="Auth")
        spec.requirements = [
            Requirement(name="Login", keyword="SHALL", description="login"),
            Requirement(name="Register", keyword="SHALL", description="register"),
        ]
        spec_manager.save_spec(spec)
        delta = SpecDelta(
            spec_name="auth",
            delta_type=DeltaType.REMOVED,
            description="Remove",
            requirements=[Requirement(name="Register", keyword="SHALL", description="register")],
        )
        change = Change(id="remove", title="Remove")
        change.spec_deltas = [delta]
        change_manager.save_change(change)
        change_manager.archive_change("remove", spec_manager)
        loaded = spec_manager.load_spec("auth")
        assert len(loaded.requirements) == 1

    def test_archive_nonexistent_raises(self, change_manager, spec_manager):
        with pytest.raises(FileNotFoundError):
            change_manager.archive_change("nonexistent", spec_manager)

    def test_archive_moves_to_archive_dir(self, change_manager, spec_manager, project_dir):
        change_manager.save_change(Change(id="archivable", title="Archivable"))
        change_manager.archive_change("archivable", spec_manager)
        assert (project_dir / ".super-dev" / "archive" / "archivable").exists()


# ---------------------------------------------------------------------------
# Task 解析
# ---------------------------------------------------------------------------


class TestTaskParsing:
    def test_parse_standard_format(self, change_manager):
        content = "- [x] **1.1: Done**\n- [ ] **1.2: Todo**\n- [~] **1.3: WIP**\n"
        tasks = change_manager._parse_tasks(content)
        assert len(tasks) == 3
        assert tasks[0].status == TaskStatus.COMPLETED
        assert tasks[1].status == TaskStatus.PENDING
        assert tasks[2].status == TaskStatus.IN_PROGRESS

    def test_parse_fallback_format(self, change_manager):
        content = "- [x] 1.1: Setup\n- [ ] 1.2: Implement\n"
        tasks = change_manager._parse_tasks(content)
        assert len(tasks) == 2

    def test_parse_skipped_task(self, change_manager):
        tasks = change_manager._parse_tasks("- [_] **1.1: Skipped**\n")
        assert tasks[0].status == TaskStatus.SKIPPED

    def test_parse_task_with_refs(self, change_manager):
        content = "- [ ] **1.1: Auth**\n  - Refs: `auth-spec`, `user-spec`\n"
        tasks = change_manager._parse_tasks(content)
        assert "auth-spec" in tasks[0].spec_refs

    def test_parse_task_with_deps(self, change_manager):
        content = "- [ ] **2.1: Backend**\n  - Depends on: 1.1, 1.2\n"
        tasks = change_manager._parse_tasks(content)
        assert "1.1" in tasks[0].dependencies

    def test_parse_task_with_assigned(self, change_manager):
        content = "- [ ] **3.1: QA**\n  - Assigned to: Alice\n"
        tasks = change_manager._parse_tasks(content)
        assert tasks[0].assigned_to == "Alice"

    def test_parse_empty(self, change_manager):
        assert change_manager._parse_tasks("") == []

    def test_parse_uppercase_x(self, change_manager):
        tasks = change_manager._parse_tasks("- [X] **1.1: Done**\n")
        assert tasks[0].status == TaskStatus.COMPLETED


# ---------------------------------------------------------------------------
# Task 格式化
# ---------------------------------------------------------------------------


class TestTaskFormatting:
    def test_format_groups_by_number(self, change_manager):
        tasks = [
            Task(id="1.1", title="Plan", status=TaskStatus.COMPLETED),
            Task(id="2.1", title="Frontend", status=TaskStatus.PENDING),
            Task(id="3.1", title="Backend", status=TaskStatus.PENDING),
        ]
        md = change_manager._format_tasks(tasks)
        assert "1. Planning" in md
        assert "2. Frontend" in md
        assert "3. Backend" in md

    def test_format_preserves_markers(self, change_manager):
        tasks = [
            Task(id="1.1", title="Done", status=TaskStatus.COMPLETED),
            Task(id="1.2", title="Todo", status=TaskStatus.PENDING),
            Task(id="1.3", title="WIP", status=TaskStatus.IN_PROGRESS),
        ]
        md = change_manager._format_tasks(tasks)
        assert "[x]" in md
        assert "[ ]" in md
        assert "[~]" in md

    def test_format_empty_tasks(self, change_manager):
        md = change_manager._format_tasks([])
        assert "# Tasks" in md

    def test_format_all_groups(self, change_manager):
        tasks = [Task(id=f"{i}.1", title=f"T{i}", status=TaskStatus.PENDING) for i in range(1, 7)]
        md = change_manager._format_tasks(tasks)
        assert "1. Planning" in md
        assert "6. Documentation" in md


# ---------------------------------------------------------------------------
# Proposal 解析
# ---------------------------------------------------------------------------


class TestProposalParsing:
    def test_parse_extracts_fields(self, change_manager):
        content = textwrap.dedent("""\
            # Add Login Feature
            ## Description
            Implement user authentication.
            ## Motivation
            Users need secure access.
            ## Impact
            Affects frontend and backend.
        """)
        proposal = change_manager._parse_proposal(content)
        assert proposal.title == "Add Login Feature"
        assert "authentication" in proposal.description
        assert "secure" in proposal.motivation

    def test_parse_empty(self, change_manager):
        proposal = change_manager._parse_proposal("")
        assert proposal.title == ""


# ---------------------------------------------------------------------------
# Spec Delta 解析
# ---------------------------------------------------------------------------


class TestSpecDeltaParsing:
    def test_parse_added_delta(self, change_manager, project_dir):
        specs_dir = project_dir / ".super-dev" / "changes" / "test" / "specs" / "auth"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text(
            "## ADDED\n\n### Requirement: Login\nSHALL support login\n"
        )
        deltas = change_manager._parse_spec_deltas(specs_dir.parent)
        assert len(deltas) == 1
        assert deltas[0].delta_type == DeltaType.ADDED

    def test_parse_modified_delta(self, change_manager, project_dir):
        specs_dir = project_dir / ".super-dev" / "changes" / "t2" / "specs" / "auth"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text(
            "## MODIFIED\n\n### Requirement: Login\nMUST support login with MFA\n"
        )
        deltas = change_manager._parse_spec_deltas(specs_dir.parent)
        assert deltas[0].delta_type == DeltaType.MODIFIED

    def test_parse_removed_delta(self, change_manager, project_dir):
        specs_dir = project_dir / ".super-dev" / "changes" / "t3" / "specs" / "auth"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec.md").write_text("## REMOVED\n\n### Requirement: Legacy\nSHALL legacy\n")
        deltas = change_manager._parse_spec_deltas(specs_dir.parent)
        assert deltas[0].delta_type == DeltaType.REMOVED


# ---------------------------------------------------------------------------
# Change metadata
# ---------------------------------------------------------------------------


class TestChangeMetadata:
    def test_status_persisted_as_yaml(self, change_manager, project_dir):
        change_manager.save_change(
            Change(id="meta-test", title="Meta", status=ChangeStatus.PROPOSED)
        )
        meta_path = project_dir / ".super-dev" / "changes" / "meta-test" / "change.yaml"
        data = yaml.safe_load(meta_path.read_text())
        assert data["status"] == "proposed"

    def test_title_persisted(self, change_manager):
        change_manager.save_change(Change(id="title-test", title="My Title"))
        loaded = change_manager.load_change("title-test")
        assert loaded.title == "My Title"

    def test_invalid_status_no_crash(self, change_manager, project_dir):
        change_manager.save_change(Change(id="bad-status", title="Bad"))
        meta_path = project_dir / ".super-dev" / "changes" / "bad-status" / "change.yaml"
        data = yaml.safe_load(meta_path.read_text())
        data["status"] = "invalid_status"
        meta_path.write_text(yaml.dump(data))
        loaded = change_manager.load_change("bad-status")
        assert loaded is not None


# ---------------------------------------------------------------------------
# Design notes
# ---------------------------------------------------------------------------


class TestDesignNotes:
    def test_design_notes_saved_and_loaded(self, change_manager):
        change = Change(id="design-test", title="Design")
        change.design_notes = "Use microservices architecture."
        change_manager.save_change(change)
        loaded = change_manager.load_change("design-test")
        assert "microservices" in loaded.design_notes


# ---------------------------------------------------------------------------
# Spec 数据模型
# ---------------------------------------------------------------------------


class TestSpecModels:
    def test_scenario_to_markdown(self):
        scenario = Scenario(given="logged in", when="clicks save", then="data persisted")
        md = scenario.to_markdown()
        assert "GIVEN logged in" in md
        assert "WHEN clicks save" in md
        assert "THEN data persisted" in md

    def test_scenario_empty(self):
        assert Scenario().to_markdown() == ""

    def test_requirement_to_dict(self):
        req = Requirement(
            name="Auth",
            keyword="MUST",
            description="authenticate",
            scenarios=[Scenario(given="t", when="r", then="200")],
        )
        d = req.to_dict()
        assert d["name"] == "Auth"
        assert len(d["scenarios"]) == 1

    def test_change_status_values(self):
        assert ChangeStatus.DRAFT.value == "draft"
        assert ChangeStatus.ARCHIVED.value == "archived"

    def test_task_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.COMPLETED.value == "completed"

    def test_delta_type_values(self):
        assert DeltaType.ADDED.value == "added"
        assert DeltaType.MODIFIED.value == "modified"
        assert DeltaType.REMOVED.value == "removed"


# ---------------------------------------------------------------------------
# Spec roundtrip
# ---------------------------------------------------------------------------


class TestSpecRoundTrip:
    def test_spec_with_purpose(self, spec_manager):
        spec = Spec(name="rt", title="RT")
        spec.purpose = "Test roundtrip"
        spec_manager.save_spec(spec)
        loaded = spec_manager.load_spec("rt")
        assert loaded.purpose == "Test roundtrip"

    def test_spec_overwrite(self, spec_manager):
        spec_manager.save_spec(Spec(name="ow", title="V1"))
        spec2 = Spec(name="ow", title="V2")
        spec2.requirements.append(Requirement(name="R1", keyword="MUST", description="v2"))
        spec_manager.save_spec(spec2)
        loaded = spec_manager.load_spec("ow")
        assert loaded.title == "V2"


# ---------------------------------------------------------------------------
# ChangeManager completeness
# ---------------------------------------------------------------------------


class TestChangeManagerCompleteness:
    def test_change_with_all_fields(self, change_manager):
        change = Change(id="full", title="Full", status=ChangeStatus.IN_PROGRESS)
        change.proposal = Proposal(title="P", description="D", motivation="M", impact="I")
        change.tasks = [Task(id="1.1", title="T1", status=TaskStatus.COMPLETED)]
        change.design_notes = "Notes"
        change.spec_deltas = [
            SpecDelta(
                spec_name="a",
                delta_type=DeltaType.ADDED,
                description="",
                requirements=[Requirement(name="R", keyword="SHALL", description="d")],
            )
        ]
        change_manager.save_change(change)
        loaded = change_manager.load_change("full")
        assert loaded.proposal is not None
        assert len(loaded.tasks) == 1
        assert loaded.design_notes == "Notes"
        assert len(loaded.spec_deltas) == 1

    def test_normalize_datetime_naive(self, change_manager):
        from datetime import datetime

        result = change_manager._normalize_datetime(datetime(2026, 1, 1))
        assert result.tzinfo is not None

    def test_normalize_datetime_aware(self, change_manager):
        from datetime import datetime, timezone

        result = change_manager._normalize_datetime(datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert result.tzinfo is not None
