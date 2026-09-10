"""知识引用追踪器单元测试"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.knowledge_tracker import (
    VALID_PHASES,
    VALID_USAGE_TYPES,
    KnowledgeReference,
    KnowledgeTracker,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def knowledge_tree(tmp_path: Path) -> Path:
    """创建模拟知识目录结构"""
    kb = tmp_path / "knowledge"
    kb.mkdir()

    # security domain
    sec_std = kb / "security" / "01-standards"
    sec_std.mkdir(parents=True)
    (sec_std / "web-security-complete.md").write_text(
        "# Web Security Standards\nOWASP Top-10 guidelines.\n", encoding="utf-8"
    )
    (sec_std / "auth-best-practices.md").write_text(
        "# Authentication Best Practices\nJWT, OAuth2, MFA.\n", encoding="utf-8"
    )

    sec_chk = kb / "security" / "03-checklists"
    sec_chk.mkdir(parents=True)
    (sec_chk / "security-checklist.md").write_text(
        "# Security Checklist\n- Input validation\n- Output encoding\n", encoding="utf-8"
    )

    # frontend domain
    fe_std = kb / "frontend" / "01-standards"
    fe_std.mkdir(parents=True)
    (fe_std / "react-complete.md").write_text(
        "# React Standards\nHooks, component patterns.\n", encoding="utf-8"
    )

    # architecture domain
    arch_std = kb / "architecture" / "01-standards"
    arch_std.mkdir(parents=True)
    (arch_std / "microservices.md").write_text(
        "# Microservices Architecture\nService mesh, gRPC.\n", encoding="utf-8"
    )

    # root-level file
    (kb / "README.md").write_text("# Knowledge Base\nOverview.\n", encoding="utf-8")

    return kb


@pytest.fixture()
def tracker(knowledge_tree: Path) -> KnowledgeTracker:
    """创建带有模拟知识库的 tracker"""
    return KnowledgeTracker(knowledge_dir=str(knowledge_tree))


# ---------------------------------------------------------------------------
# 索引构建
# ---------------------------------------------------------------------------


class TestBuildIndex:
    def test_index_counts_all_files(self, tracker: KnowledgeTracker) -> None:
        assert len(tracker._knowledge_index) == 6  # 5 domain files + 1 root README

    def test_index_extracts_domains(self, tracker: KnowledgeTracker) -> None:
        domains = tracker.get_all_domains()
        assert "security" in domains
        assert "frontend" in domains
        assert "architecture" in domains

    def test_index_extracts_title_from_heading(self, tracker: KnowledgeTracker) -> None:
        for entry in tracker._knowledge_index.values():
            if "web-security" in entry.path:
                assert entry.title == "Web Security Standards"
                break
        else:
            pytest.fail("web-security file not found in index")

    def test_empty_knowledge_dir(self, tmp_path: Path) -> None:
        t = KnowledgeTracker(knowledge_dir=str(tmp_path / "nonexistent"))
        assert len(t._knowledge_index) == 0

    def test_index_extracts_tags(self, tracker: KnowledgeTracker) -> None:
        for entry in tracker._knowledge_index.values():
            if "web-security" in entry.path:
                assert "security" in entry.tags
                assert "standards" in entry.tags
                break


# ---------------------------------------------------------------------------
# 引用追踪
# ---------------------------------------------------------------------------


class TestTrackReference:
    def test_basic_tracking(self, tracker: KnowledgeTracker) -> None:
        ref = tracker.track_reference(
            knowledge_file="knowledge/security/01-standards/web-security-complete.md",
            phase="backend",
            usage_type="constraint",
            relevance_score=0.9,
            excerpt="OWASP Top-10",
        )
        assert isinstance(ref, KnowledgeReference)
        assert ref.phase == "backend"
        assert ref.usage_type == "constraint"
        assert ref.relevance_score == 0.9
        assert tracker.get_reference_count() == 1

    def test_invalid_phase_raises(self, tracker: KnowledgeTracker) -> None:
        with pytest.raises(ValueError, match="Invalid phase"):
            tracker.track_reference("some/file.md", phase="invalid", usage_type="constraint")

    def test_invalid_usage_type_raises(self, tracker: KnowledgeTracker) -> None:
        with pytest.raises(ValueError, match="Invalid usage_type"):
            tracker.track_reference("some/file.md", phase="backend", usage_type="invalid")

    def test_score_clamping(self, tracker: KnowledgeTracker) -> None:
        ref = tracker.track_reference(
            "f.md", phase="docs", usage_type="reference", relevance_score=5.0
        )
        assert ref.relevance_score == 1.0

        ref2 = tracker.track_reference(
            "f.md", phase="docs", usage_type="reference", relevance_score=-1.0
        )
        assert ref2.relevance_score == 0.0

    def test_auto_tags(self, tracker: KnowledgeTracker) -> None:
        # 使用索引中存在的文件路径
        indexed_path = None
        for path in tracker._knowledge_index:
            if "web-security" in path:
                indexed_path = path
                break
        assert indexed_path is not None

        ref = tracker.track_reference(indexed_path, phase="backend", usage_type="constraint")
        assert len(ref.matched_tags) > 0

    def test_clear(self, tracker: KnowledgeTracker) -> None:
        tracker.track_reference("f.md", phase="docs", usage_type="reference")
        assert tracker.get_reference_count() == 1
        tracker.clear()
        assert tracker.get_reference_count() == 0


# ---------------------------------------------------------------------------
# 知识查找
# ---------------------------------------------------------------------------


class TestFindRelevantKnowledge:
    def test_finds_matching_knowledge(self, tracker: KnowledgeTracker) -> None:
        results = tracker.find_relevant_knowledge("web security OWASP", phase="backend")
        assert len(results) > 0
        assert any("security" in r["path"] for r in results)

    def test_phase_affinity_boosts_score(self, tracker: KnowledgeTracker) -> None:
        # "react" 在 frontend 阶段应该比在 delivery 阶段得分更高
        fe_results = tracker.find_relevant_knowledge("react", phase="frontend")
        dl_results = tracker.find_relevant_knowledge("react", phase="delivery")
        if fe_results and dl_results:
            assert fe_results[0]["score"] >= dl_results[0]["score"]

    def test_top_k_limit(self, tracker: KnowledgeTracker) -> None:
        results = tracker.find_relevant_knowledge("security", phase="backend", top_k=2)
        assert len(results) <= 2

    def test_empty_query(self, tracker: KnowledgeTracker) -> None:
        results = tracker.find_relevant_knowledge("", phase="docs")
        # 空查询不应崩溃
        assert isinstance(results, list)

    def test_empty_index(self, tmp_path: Path) -> None:
        t = KnowledgeTracker(knowledge_dir=str(tmp_path / "nonexistent"))
        results = t.find_relevant_knowledge("anything", phase="docs")
        assert results == []


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_report_structure(self, tracker: KnowledgeTracker) -> None:
        tracker.track_reference("f.md", phase="docs", usage_type="constraint")
        report = tracker.generate_report("testapp")
        assert report.project_name == "testapp"
        assert report.pipeline_run_id.startswith("run-")
        assert report.total_knowledge_files == 6
        assert report.referenced_files == 1
        assert 0 < report.hit_rate < 1

    def test_custom_run_id(self, tracker: KnowledgeTracker) -> None:
        report = tracker.generate_report("testapp", run_id="my-run-123")
        assert report.pipeline_run_id == "my-run-123"

    def test_unreferenced_domains(self, tracker: KnowledgeTracker) -> None:
        # 只引用 security 领域的文件
        for path in tracker._knowledge_index:
            if "security" in path:
                tracker.track_reference(path, phase="backend", usage_type="constraint")
                break
        report = tracker.generate_report("testapp")
        # frontend 和 architecture 应该在未引用列表中
        assert "frontend" in report.unreferenced_domains
        assert "architecture" in report.unreferenced_domains

    def test_to_markdown(self, tracker: KnowledgeTracker) -> None:
        tracker.track_reference("f.md", phase="docs", usage_type="guidance", excerpt="test excerpt")
        report = tracker.generate_report("testapp")
        md = report.to_markdown()
        assert "知识引用追踪报告" in md
        assert "testapp" in md
        assert "docs" in md
        assert "test excerpt" in md

    def test_to_json(self, tracker: KnowledgeTracker) -> None:
        tracker.track_reference("f.md", phase="docs", usage_type="reference")
        report = tracker.generate_report("testapp")
        data = report.to_json()
        assert data["project_name"] == "testapp"
        assert data["summary"]["total_references"] == 1
        assert isinstance(data["references"], list)
        assert isinstance(data["coverage_by_domain"], dict)


# ---------------------------------------------------------------------------
# 报告保存
# ---------------------------------------------------------------------------


class TestSaveReport:
    def test_saves_md_and_json(self, tracker: KnowledgeTracker, tmp_path: Path) -> None:
        tracker.track_reference("f.md", phase="docs", usage_type="reference")
        report = tracker.generate_report("testapp")
        md_path, json_path = tracker.save_report(report, output_dir=str(tmp_path / "output"))

        assert md_path.exists()
        assert json_path.exists()
        assert md_path.name == "testapp-knowledge-tracking.md"
        assert "knowledge-tracking" in json_path.name
        assert json_path.parent.name == "metrics-history"

        # JSON 可解析
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["project_name"] == "testapp"


# ---------------------------------------------------------------------------
# 覆盖率
# ---------------------------------------------------------------------------


class TestKnowledgeCoverage:
    def test_coverage_by_domain(self, tracker: KnowledgeTracker) -> None:
        coverage = tracker.get_knowledge_coverage()
        assert "security" in coverage
        assert coverage["security"]["total"] == 3
        assert coverage["security"]["referenced"] == 0
        assert coverage["security"]["rate"] == 0.0

    def test_coverage_after_reference(self, tracker: KnowledgeTracker) -> None:
        # 引用一个 security 文件
        for path in tracker._knowledge_index:
            if "web-security" in path:
                tracker.track_reference(path, phase="backend", usage_type="constraint")
                break
        coverage = tracker.get_knowledge_coverage()
        assert coverage["security"]["referenced"] == 1
        assert coverage["security"]["rate"] > 0


# ---------------------------------------------------------------------------
# KnowledgeReference dataclass
# ---------------------------------------------------------------------------


class TestKnowledgeReference:
    def test_to_dict(self) -> None:
        ref = KnowledgeReference(
            knowledge_file="k/security/web.md",
            phase="backend",
            usage_type="constraint",
            matched_tags=["security", "web"],
            relevance_score=0.85,
            excerpt="OWASP",
        )
        d = ref.to_dict()
        assert d["knowledge_file"] == "k/security/web.md"
        assert d["phase"] == "backend"
        assert d["relevance_score"] == 0.85
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# 常量验证
# ---------------------------------------------------------------------------


class TestConstants:
    def test_valid_phases(self) -> None:
        expected = {"research", "docs", "spec", "frontend", "backend", "quality", "delivery"}
        assert VALID_PHASES == expected

    def test_valid_usage_types(self) -> None:
        expected = {"constraint", "guidance", "reference"}
        assert VALID_USAGE_TYPES == expected
