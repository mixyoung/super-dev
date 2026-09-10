# ruff: noqa: I001
"""
数据模型增强测试 - Spec/Change/Task/Proposal 模型完整覆盖

测试对象: super_dev.specs.models
"""

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
# Scenario
# ---------------------------------------------------------------------------


class TestScenarioModel:
    def test_default_values(self):
        s = Scenario()
        assert s.given == ""
        assert s.when == ""
        assert s.then == ""

    def test_full_values(self):
        s = Scenario(given="user logged in", when="clicks save", then="data saved")
        assert s.given == "user logged in"
        assert s.when == "clicks save"
        assert s.then == "data saved"

    def test_to_markdown_full(self):
        s = Scenario(given="A", when="B", then="C")
        md = s.to_markdown()
        assert "- GIVEN A" in md
        assert "- WHEN B" in md
        assert "- THEN C" in md

    def test_to_markdown_given_only(self):
        s = Scenario(given="precondition")
        md = s.to_markdown()
        assert "GIVEN precondition" in md
        assert "WHEN" not in md
        assert "THEN" not in md

    def test_to_markdown_when_only(self):
        s = Scenario(when="user acts")
        md = s.to_markdown()
        assert "WHEN user acts" in md

    def test_to_markdown_then_only(self):
        s = Scenario(then="expected result")
        md = s.to_markdown()
        assert "THEN expected result" in md

    def test_to_markdown_empty(self):
        s = Scenario()
        assert s.to_markdown() == ""


# ---------------------------------------------------------------------------
# Requirement
# ---------------------------------------------------------------------------


class TestRequirementModel:
    def test_default_keyword_is_shall(self):
        r = Requirement(name="R1")
        assert r.keyword == "SHALL"

    def test_custom_keyword(self):
        r = Requirement(name="R1", keyword="MUST")
        assert r.keyword == "MUST"

    def test_to_markdown_with_description(self):
        r = Requirement(name="Auth", keyword="SHALL", description="authenticate users")
        md = r.to_markdown()
        assert "### Requirement: Auth" in md
        assert "SHALL authenticate users" in md

    def test_to_markdown_with_scenarios(self):
        r = Requirement(
            name="Login",
            keyword="MUST",
            description="support login",
            scenarios=[
                Scenario(given="valid creds", when="submit", then="success"),
                Scenario(given="invalid creds", when="submit", then="401"),
            ],
        )
        md = r.to_markdown()
        assert "Scenario 1" in md
        assert "Scenario 2" in md

    def test_to_markdown_no_description(self):
        r = Requirement(name="Empty")
        md = r.to_markdown()
        assert "### Requirement: Empty" in md

    def test_to_markdown_custom_level(self):
        r = Requirement(name="Nested", keyword="SHOULD", description="be nested")
        md = r.to_markdown(level=4)
        assert "#### Requirement: Nested" in md

    def test_to_dict(self):
        r = Requirement(
            name="Test",
            keyword="MAY",
            description="optional",
            scenarios=[Scenario(given="A", when="B", then="C")],
        )
        d = r.to_dict()
        assert d["name"] == "Test"
        assert d["keyword"] == "MAY"
        assert d["description"] == "optional"
        assert len(d["scenarios"]) == 1
        assert d["scenarios"][0]["given"] == "A"

    def test_to_dict_empty_scenarios(self):
        r = Requirement(name="Simple")
        d = r.to_dict()
        assert d["scenarios"] == []

    def test_scenarios_default_empty(self):
        r = Requirement(name="NoScenarios")
        assert r.scenarios == []


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------


class TestSpecModel:
    def test_default_values(self):
        s = Spec(name="test-spec")
        assert s.name == "test-spec"
        assert s.title == ""
        assert s.purpose == ""
        assert s.requirements == []

    def test_with_title_and_purpose(self):
        s = Spec(name="auth", title="Authentication Spec")
        s.purpose = "Define authentication requirements"
        assert s.title == "Authentication Spec"
        assert s.purpose == "Define authentication requirements"

    def test_with_requirements(self):
        s = Spec(name="auth", title="Auth")
        s.requirements = [
            Requirement(name="Login", keyword="SHALL", description="support login"),
            Requirement(name="Logout", keyword="SHALL", description="support logout"),
        ]
        assert len(s.requirements) == 2

    def test_to_markdown(self):
        s = Spec(name="test", title="Test Spec")
        s.purpose = "Testing purpose"
        s.requirements = [
            Requirement(name="R1", keyword="SHALL", description="do something"),
        ]
        md = s.to_markdown()
        assert "# Test Spec" in md
        assert "Purpose" in md
        assert "Requirements" in md


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class TestTaskModel:
    def test_default_status(self):
        t = Task(id="1.1", title="Setup")
        assert t.status == TaskStatus.PENDING

    def test_custom_status(self):
        t = Task(id="1.1", title="Done", status=TaskStatus.COMPLETED)
        assert t.status == TaskStatus.COMPLETED

    def test_to_markdown_pending(self):
        t = Task(id="1.1", title="Todo")
        md = t.to_markdown()
        assert "[ ]" in md
        assert "1.1" in md
        assert "Todo" in md

    def test_to_markdown_completed(self):
        t = Task(id="1.1", title="Done", status=TaskStatus.COMPLETED)
        md = t.to_markdown()
        assert "[x]" in md

    def test_to_markdown_in_progress(self):
        t = Task(id="1.1", title="WIP", status=TaskStatus.IN_PROGRESS)
        md = t.to_markdown()
        assert "[~]" in md

    def test_to_markdown_skipped(self):
        t = Task(id="1.1", title="Skip", status=TaskStatus.SKIPPED)
        md = t.to_markdown()
        assert "[_]" in md

    def test_spec_refs_default(self):
        t = Task(id="1.1", title="T")
        assert t.spec_refs == []

    def test_dependencies_default(self):
        t = Task(id="1.1", title="T")
        assert t.dependencies == []

    def test_assigned_to_default(self):
        t = Task(id="1.1", title="T")
        assert t.assigned_to == ""

    def test_description_default(self):
        t = Task(id="1.1", title="T")
        assert t.description == ""


# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------


class TestProposalModel:
    def test_default_values(self):
        p = Proposal(title="Test", description="Desc")
        assert p.title == "Test"
        assert p.description == "Desc"
        assert p.motivation == ""
        assert p.impact == ""

    def test_full_values(self):
        p = Proposal(
            title="Feature X",
            description="Add feature X",
            motivation="Users need X",
            impact="Frontend and backend",
        )
        assert p.motivation == "Users need X"
        assert p.impact == "Frontend and backend"

    def test_to_markdown(self):
        p = Proposal(title="Test", description="D", motivation="M", impact="I")
        md = p.to_markdown()
        assert "Test" in md
        assert "Description" in md or "D" in md


# ---------------------------------------------------------------------------
# Change
# ---------------------------------------------------------------------------


class TestChangeModel:
    def test_default_status(self):
        c = Change(id="test", title="Test")
        assert c.status == ChangeStatus.DRAFT

    def test_custom_status(self):
        c = Change(id="test", title="Test", status=ChangeStatus.PROPOSED)
        assert c.status == ChangeStatus.PROPOSED

    def test_default_timestamps(self):
        c = Change(id="test", title="Test")
        assert c.created_at is not None
        assert c.updated_at is not None

    def test_default_empty_lists(self):
        c = Change(id="test", title="Test")
        assert c.tasks == []
        assert c.spec_deltas == []

    def test_proposal_default_none(self):
        c = Change(id="test", title="Test")
        assert c.proposal is None

    def test_design_notes_default(self):
        c = Change(id="test", title="Test")
        assert c.design_notes is None or c.design_notes == ""


# ---------------------------------------------------------------------------
# SpecDelta
# ---------------------------------------------------------------------------


class TestSpecDeltaModel:
    def test_added_delta(self):
        d = SpecDelta(
            spec_name="auth",
            delta_type=DeltaType.ADDED,
            description="Add login",
            requirements=[Requirement(name="Login", keyword="SHALL", description="login")],
        )
        assert d.spec_name == "auth"
        assert d.delta_type == DeltaType.ADDED
        assert len(d.requirements) == 1

    def test_modified_delta(self):
        d = SpecDelta(spec_name="auth", delta_type=DeltaType.MODIFIED, description="Update")
        assert d.delta_type == DeltaType.MODIFIED

    def test_removed_delta(self):
        d = SpecDelta(spec_name="auth", delta_type=DeltaType.REMOVED, description="Remove")
        assert d.delta_type == DeltaType.REMOVED

    def test_to_markdown(self):
        d = SpecDelta(
            spec_name="auth",
            delta_type=DeltaType.ADDED,
            description="Add",
            requirements=[Requirement(name="R1", keyword="SHALL", description="do")],
        )
        md = d.to_markdown()
        assert "ADDED" in md or "auth" in md

    def test_empty_requirements(self):
        d = SpecDelta(spec_name="empty", delta_type=DeltaType.ADDED, description="Empty")
        assert d.requirements == []


# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------


class TestEnumValues:
    def test_change_status_all_values(self):
        expected = {"draft", "proposed", "approved", "in_progress", "completed", "archived"}
        actual = {s.value for s in ChangeStatus}
        assert actual == expected

    def test_task_status_all_values(self):
        expected = {"pending", "in_progress", "completed", "skipped"}
        actual = {s.value for s in TaskStatus}
        assert actual == expected

    def test_delta_type_all_values(self):
        expected = {"added", "modified", "removed"}
        actual = {d.value for d in DeltaType}
        assert actual == expected

    def test_change_status_from_string(self):
        for status in ChangeStatus:
            assert ChangeStatus(status.value) == status

    def test_task_status_from_string(self):
        for status in TaskStatus:
            assert TaskStatus(status.value) == status

    def test_delta_type_from_string(self):
        for dt in DeltaType:
            assert DeltaType(dt.value) == dt


# ---------------------------------------------------------------------------
# Spec - to_markdown 全面测试
# ---------------------------------------------------------------------------


class TestSpecToMarkdown:
    def test_minimal_spec(self):
        s = Spec(name="minimal")
        md = s.to_markdown()
        assert isinstance(md, str)

    def test_spec_with_all_fields(self):
        s = Spec(name="full", title="Full Spec")
        s.purpose = "Complete test"
        s.requirements = [
            Requirement(
                name="R1",
                keyword="SHALL",
                description="first requirement",
                scenarios=[
                    Scenario(given="A", when="B", then="C"),
                    Scenario(given="D", when="E", then="F"),
                ],
            ),
            Requirement(
                name="R2",
                keyword="MUST",
                description="second requirement",
                scenarios=[Scenario(given="X", when="Y", then="Z")],
            ),
            Requirement(name="R3", keyword="SHOULD", description="third"),
            Requirement(name="R4", keyword="MAY", description="fourth"),
        ]
        md = s.to_markdown()
        assert "# Full Spec" in md
        assert "Purpose" in md
        assert "R1" in md
        assert "R2" in md
        assert "R3" in md
        assert "R4" in md
        assert "SHALL" in md
        assert "MUST" in md
        assert "SHOULD" in md
        assert "MAY" in md


# ---------------------------------------------------------------------------
# Task - to_markdown 全面测试
# ---------------------------------------------------------------------------


class TestTaskToMarkdown:
    def test_pending_task(self):
        t = Task(id="1.1", title="Pending Task")
        md = t.to_markdown()
        assert "[ ]" in md
        assert "1.1" in md
        assert "Pending Task" in md

    def test_completed_task(self):
        t = Task(id="2.1", title="Done Task", status=TaskStatus.COMPLETED)
        md = t.to_markdown()
        assert "[x]" in md

    def test_in_progress_task(self):
        t = Task(id="3.1", title="WIP Task", status=TaskStatus.IN_PROGRESS)
        md = t.to_markdown()
        assert "[~]" in md

    def test_skipped_task(self):
        t = Task(id="4.1", title="Skip Task", status=TaskStatus.SKIPPED)
        md = t.to_markdown()
        assert "[_]" in md

    def test_task_with_spec_refs(self):
        t = Task(id="1.1", title="T", spec_refs=["auth-spec", "user-spec"])
        assert len(t.spec_refs) == 2

    def test_task_with_dependencies(self):
        t = Task(id="2.1", title="T", dependencies=["1.1", "1.2"])
        assert "1.1" in t.dependencies

    def test_task_with_assigned_to(self):
        t = Task(id="1.1", title="T", assigned_to="Alice")
        assert t.assigned_to == "Alice"


# ---------------------------------------------------------------------------
# Proposal - to_markdown 全面测试
# ---------------------------------------------------------------------------


class TestProposalToMarkdown:
    def test_minimal_proposal(self):
        p = Proposal(title="Test", description="Desc")
        md = p.to_markdown()
        assert isinstance(md, str)
        assert "Test" in md

    def test_full_proposal(self):
        p = Proposal(
            title="Full Proposal",
            description="Full description of the change",
            motivation="Users need this feature",
            impact="Affects frontend and backend",
        )
        md = p.to_markdown()
        assert "Full Proposal" in md


# ---------------------------------------------------------------------------
# SpecDelta - to_markdown
# ---------------------------------------------------------------------------


class TestSpecDeltaToMarkdown:
    def test_added_delta_to_markdown(self):
        d = SpecDelta(
            spec_name="auth",
            delta_type=DeltaType.ADDED,
            description="Add auth",
            requirements=[Requirement(name="Login", keyword="SHALL", description="login")],
        )
        md = d.to_markdown()
        assert isinstance(md, str)

    def test_modified_delta_to_markdown(self):
        d = SpecDelta(
            spec_name="auth",
            delta_type=DeltaType.MODIFIED,
            description="Update",
            requirements=[Requirement(name="Login", keyword="MUST", description="login v2")],
        )
        md = d.to_markdown()
        assert isinstance(md, str)

    def test_removed_delta_to_markdown(self):
        d = SpecDelta(
            spec_name="auth",
            delta_type=DeltaType.REMOVED,
            description="Remove",
            requirements=[Requirement(name="Legacy", keyword="SHALL", description="legacy")],
        )
        md = d.to_markdown()
        assert isinstance(md, str)

    def test_empty_delta_to_markdown(self):
        d = SpecDelta(spec_name="empty", delta_type=DeltaType.ADDED, description="Empty")
        md = d.to_markdown()
        assert isinstance(md, str)


# ---------------------------------------------------------------------------
# Change - 全面属性测试
# ---------------------------------------------------------------------------


class TestChangeModelComprehensive:
    def test_change_all_statuses(self):
        for status in ChangeStatus:
            c = Change(id="test", title="Test", status=status)
            assert c.status == status

    def test_change_with_proposal(self):
        c = Change(id="test", title="Test")
        c.proposal = Proposal(title="P", description="D")
        assert c.proposal.title == "P"

    def test_change_with_tasks(self):
        c = Change(id="test", title="Test")
        c.tasks = [
            Task(id="1.1", title="T1", status=TaskStatus.COMPLETED),
            Task(id="1.2", title="T2", status=TaskStatus.PENDING),
        ]
        assert len(c.tasks) == 2

    def test_change_with_design_notes(self):
        c = Change(id="test", title="Test")
        c.design_notes = "Microservices with event sourcing"
        assert "event sourcing" in c.design_notes

    def test_change_with_multiple_deltas(self):
        c = Change(id="test", title="Test")
        c.spec_deltas = [
            SpecDelta(spec_name="auth", delta_type=DeltaType.ADDED, description="Add"),
            SpecDelta(spec_name="user", delta_type=DeltaType.MODIFIED, description="Modify"),
        ]
        assert len(c.spec_deltas) == 2


class TestRequirementKeywords:
    def test_all_keywords_in_markdown(self):
        for kw in ["SHALL", "MUST", "SHOULD", "MAY"]:
            r = Requirement(name=f"test-{kw}", keyword=kw, description=f"test {kw}")
            md = r.to_markdown()
            assert kw in md

    def test_requirement_with_many_scenarios(self):
        scenarios = [Scenario(given=f"G{i}", when=f"W{i}", then=f"T{i}") for i in range(10)]
        r = Requirement(
            name="many", keyword="SHALL", description="many scenarios", scenarios=scenarios
        )
        md = r.to_markdown()
        assert "Scenario 10" in md
        assert "G0" in md
        assert "T9" in md

    def test_requirement_to_dict_preserves_all(self):
        r = Requirement(
            name="full",
            keyword="MUST",
            description="full desc",
            scenarios=[
                Scenario(given="A", when="B", then="C"),
                Scenario(given="D", when="E", then="F"),
            ],
        )
        d = r.to_dict()
        assert d["name"] == "full"
        assert d["keyword"] == "MUST"
        assert d["description"] == "full desc"
        assert len(d["scenarios"]) == 2
        assert d["scenarios"][0] == {"given": "A", "when": "B", "then": "C"}
        assert d["scenarios"][1] == {"given": "D", "when": "E", "then": "F"}


class TestScenarioEdgeCases:
    def test_scenario_with_special_chars(self):
        s = Scenario(
            given="user has <admin> role", when='clicks "delete"', then="item & children removed"
        )
        md = s.to_markdown()
        assert "<admin>" in md
        assert '"delete"' in md
        assert "&" in md

    def test_scenario_with_unicode(self):
        s = Scenario(
            given="user logged in", when="clicks save button", then="data is persisted to DB"
        )
        md = s.to_markdown()
        assert "user logged in" in md
        assert "clicks save button" in md
        assert "data is persisted to DB" in md

    def test_scenario_with_long_text(self):
        s = Scenario(given="x" * 500, when="y" * 500, then="z" * 500)
        md = s.to_markdown()
        assert len(md) > 1500


class TestTaskEdgeCases:
    def test_task_with_empty_id(self):
        t = Task(id="", title="Empty ID")
        md = t.to_markdown()
        assert "Empty ID" in md

    def test_task_with_complex_id(self):
        t = Task(id="1.2.3.4", title="Deep Nested Task")
        assert t.id == "1.2.3.4"

    def test_task_with_long_title(self):
        t = Task(id="1.1", title="A" * 200)
        md = t.to_markdown()
        assert "A" * 200 in md

    def test_task_with_all_optional_fields(self):
        t = Task(
            id="1.1",
            title="Full Task",
            status=TaskStatus.IN_PROGRESS,
            description="Detailed description",
            spec_refs=["spec-a", "spec-b"],
            dependencies=["0.1", "0.2"],
            assigned_to="Bob",
        )
        assert t.description == "Detailed description"
        assert len(t.spec_refs) == 2
        assert len(t.dependencies) == 2
        assert t.assigned_to == "Bob"
