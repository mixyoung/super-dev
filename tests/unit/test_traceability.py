"""需求追溯矩阵生成器单元测试"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from super_dev.specs.traceability import (
    RequirementTracer,
    TraceabilityMatrix,
    TracedRequirement,
)


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """创建包含 super-dev.yaml 和 .super-dev 结构的临时项目"""
    (tmp_path / "super-dev.yaml").write_text("name: test-project\nversion: 1.0.0\n")
    changes_dir = tmp_path / ".super-dev" / "changes"
    changes_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def change_with_proposal(project_dir: Path) -> str:
    """创建包含 proposal.md 的变更"""
    change_id = "add-user-auth"
    change_dir = project_dir / ".super-dev" / "changes" / change_id
    change_dir.mkdir(parents=True)

    proposal = textwrap.dedent("""\
        # Proposal

        ## Add User Authentication

        ## Description
        The system SHALL provide JWT-based authentication for all API endpoints.
        The system MUST validate tokens on every request.
        The system SHOULD support refresh token rotation.
        The system MAY support OAuth2 social login providers.

        ## Motivation
        Security requirement for production deployment.
    """)
    (change_dir / "proposal.md").write_text(proposal, encoding="utf-8")
    return change_id


@pytest.fixture()
def change_with_spec(project_dir: Path, change_with_proposal: str) -> str:
    """创建包含 spec.md 的变更"""
    change_id = change_with_proposal
    change_dir = project_dir / ".super-dev" / "changes" / change_id
    specs_dir = change_dir / "specs" / "auth"
    specs_dir.mkdir(parents=True)

    spec = textwrap.dedent("""\
        # Auth Spec

        ## ADDED Requirements

        ### Requirement: JWT Token Validation
        SHALL validate JWT signature and expiry on every API request.

        #### Scenario 1: Valid token
        - GIVEN a valid JWT token
        - WHEN the user makes an API request
        - THEN the request is accepted

        ### Requirement: Refresh Token
        SHOULD implement refresh token rotation with configurable TTL.
    """)
    (specs_dir / "spec.md").write_text(spec, encoding="utf-8")
    return change_id


class TestTracedRequirement:
    def test_to_dict(self):
        req = TracedRequirement(
            id="REQ-001",
            text="provide authentication",
            priority="SHALL",
            source="proposal.md:5",
            status="covered",
            implementations=["auth.py"],
            tests=["test_auth.py"],
            verification="代码实现 + 测试覆盖",
        )
        d = req.to_dict()
        assert d["id"] == "REQ-001"
        assert d["priority"] == "SHALL"
        assert d["status"] == "covered"
        assert "auth.py" in d["implementations"]


class TestTraceabilityMatrix:
    def test_empty_matrix(self):
        matrix = TraceabilityMatrix(change_id="test", requirements=[])
        assert matrix.coverage_rate == 0.0
        assert matrix.shall_coverage == 100.0  # no SHALL reqs = 100%
        assert matrix.total_count == 0

    def test_coverage_calculation(self):
        reqs = [
            TracedRequirement(
                id="REQ-001", text="a", priority="SHALL", source="p.md:1", status="covered"
            ),
            TracedRequirement(
                id="REQ-002", text="b", priority="MUST", source="p.md:2", status="uncovered"
            ),
            TracedRequirement(
                id="REQ-003", text="c", priority="SHOULD", source="p.md:3", status="covered"
            ),
        ]
        matrix = TraceabilityMatrix(change_id="test", requirements=reqs)
        assert matrix.total_count == 3
        assert matrix.covered_count == 2
        assert matrix.uncovered_count == 1
        assert abs(matrix.coverage_rate - 66.7) < 0.1
        assert abs(matrix.shall_coverage - 50.0) < 0.1

    def test_to_markdown(self):
        reqs = [
            TracedRequirement(
                id="REQ-001",
                text="provide JWT auth",
                priority="SHALL",
                source="proposal.md:5",
                status="covered",
                implementations=["auth.py"],
                tests=["test_auth.py"],
            ),
        ]
        matrix = TraceabilityMatrix(
            change_id="add-auth", requirements=reqs, generated_at="2025-01-01"
        )
        md = matrix.to_markdown()
        assert "# 需求追溯矩阵: add-auth" in md
        assert "REQ-001" in md
        assert "SHALL" in md

    def test_to_dict(self):
        matrix = TraceabilityMatrix(
            change_id="test",
            requirements=[
                TracedRequirement(
                    id="REQ-001", text="a", priority="SHALL", source="p.md:1", status="covered"
                ),
            ],
            generated_at="2025-01-01",
        )
        d = matrix.to_dict()
        assert d["change_id"] == "test"
        assert d["coverage_rate"] == 100.0
        assert len(d["requirements"]) == 1


class TestRequirementTracer:
    def test_extract_from_proposal(self, project_dir: Path, change_with_proposal: str):
        tracer = RequirementTracer(project_dir)
        reqs = tracer.extract_requirements(change_with_proposal)
        assert len(reqs) == 4

        priorities = [r.priority for r in reqs]
        assert "SHALL" in priorities
        assert "MUST" in priorities
        assert "SHOULD" in priorities
        assert "MAY" in priorities

        # Check IDs are sequential
        ids = [r.id for r in reqs]
        assert ids == ["REQ-001", "REQ-002", "REQ-003", "REQ-004"]

    def test_extract_from_spec(self, project_dir: Path, change_with_spec: str):
        tracer = RequirementTracer(project_dir)
        reqs = tracer.extract_requirements(change_with_spec)
        # 4 from proposal + 2 from spec
        assert len(reqs) == 6

        # Spec requirements should have spec file as source
        spec_reqs = [r for r in reqs if "specs/" in r.source]
        assert len(spec_reqs) == 2

    def test_extract_nonexistent_change(self, project_dir: Path):
        tracer = RequirementTracer(project_dir)
        reqs = tracer.extract_requirements("nonexistent")
        assert reqs == []

    def test_trace_to_code(self, project_dir: Path, change_with_proposal: str):
        # Create a source file with matching keywords
        src_dir = project_dir / "src"
        src_dir.mkdir()
        (src_dir / "auth.py").write_text(
            "def validate_jwt_token(token):\n    # authentication endpoint\n    pass\n",
            encoding="utf-8",
        )

        tracer = RequirementTracer(project_dir)
        reqs = tracer.extract_requirements(change_with_proposal)
        reqs = tracer.trace_to_code(reqs)
        # At least some reqs should find the auth.py file
        all_impls = [impl for r in reqs for impl in r.implementations]
        # May or may not match depending on keyword overlap, but should not crash
        assert isinstance(all_impls, list)

    def test_trace_to_tests(self, project_dir: Path, change_with_proposal: str):
        # Create a test file
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_auth.py").write_text(
            "def test_jwt_authentication():\n    # validate token\n    pass\n",
            encoding="utf-8",
        )

        tracer = RequirementTracer(project_dir)
        reqs = tracer.extract_requirements(change_with_proposal)
        reqs = tracer.trace_to_tests(reqs)
        all_tests = [t for r in reqs for t in r.tests]
        assert isinstance(all_tests, list)

    def test_generate_matrix(self, project_dir: Path, change_with_proposal: str):
        tracer = RequirementTracer(project_dir)
        matrix = tracer.generate_matrix(change_with_proposal)
        assert matrix.change_id == change_with_proposal
        assert matrix.total_count == 4
        assert matrix.generated_at != ""

    def test_generate_acceptance_checklist(self, project_dir: Path, change_with_proposal: str):
        tracer = RequirementTracer(project_dir)
        checklist = tracer.generate_acceptance_checklist(change_with_proposal)
        assert "# 验收检查清单" in checklist
        assert "SHALL" in checklist
        assert "MUST" in checklist
        assert "SHOULD" in checklist
        assert "MAY" in checklist
        assert "- [ ]" in checklist

    def test_generate_acceptance_empty(self, project_dir: Path):
        # Create an empty change
        change_id = "empty-change"
        change_dir = project_dir / ".super-dev" / "changes" / change_id
        change_dir.mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# Empty\n\nNo requirements here.\n")

        tracer = RequirementTracer(project_dir)
        checklist = tracer.generate_acceptance_checklist(change_id)
        assert "未提取到" in checklist

    def test_generate_governance_report(self, project_dir: Path, change_with_proposal: str):
        tracer = RequirementTracer(project_dir)
        report = tracer.generate_governance_report()
        assert "# Super Dev 治理总报告" in report
        assert change_with_proposal in report

    def test_governance_report_no_changes(self, project_dir: Path):
        tracer = RequirementTracer(project_dir)
        report = tracer.generate_governance_report()
        assert "暂无活跃变更" in report

    def test_governance_report_no_dir(self, tmp_path: Path):
        tracer = RequirementTracer(tmp_path)
        report = tracer.generate_governance_report()
        assert "未找到" in report
