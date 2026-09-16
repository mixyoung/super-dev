from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from super_dev.experts.loader import load_expert_profiles, parse_expert_from_markdown
from super_dev.experts.review_protocol import ReviewExecutionEvidence
from super_dev.orchestrator.experts import EXPERT_PROFILES, ExpertRole, get_expert_prompt_section
from super_dev.workflow_stage_truth import applicable_experts_for_stage


def test_builtin_expert_profiles_expose_v2_contract_fields() -> None:
    for role, profile in EXPERT_PROFILES.items():
        if role is ExpertRole.OVERSEER:
            assert "批准" in " ".join(profile.non_goals)
            continue
        assert profile.when_to_use
        assert profile.when_not_to_use
        assert profile.required_inputs
        assert profile.outputs
        assert profile.authority
        assert profile.non_goals
        assert profile.evidence_requirements
        assert profile.stop_conditions
        assert profile.handoff_checklist


def test_builtin_profiles_use_work_stances_not_fake_credentials() -> None:
    banned = ("10 年", "12 年", "15 年", "CISSP", "曾为多个", "曾主导")
    builtin_dir = Path(__file__).resolve().parents[2] / "super_dev" / "experts" / "builtin"
    rendered = "\n".join(path.read_text(encoding="utf-8") for path in builtin_dir.glob("*.md"))
    rendered += "\n" + "\n".join(profile.backstory for profile in EXPERT_PROFILES.values())
    assert not any(marker in rendered for marker in banned)


def test_profile_prompt_exposes_applicability_authority_evidence_and_stop_contract() -> None:
    prompt = get_expert_prompt_section(ExpertRole.PM)
    assert "何时使用" in prompt
    assert "何时不使用" in prompt
    assert "所需输入" in prompt
    assert "交付输出" in prompt
    assert "可判断范围" in prompt
    assert "无权事项" in prompt
    assert "证据要求" in prompt
    assert "停止条件" in prompt


def test_unknown_project_role_cannot_expand_enum_or_replace_code(tmp_path: Path) -> None:
    expert_dir = tmp_path / ".super-dev" / "experts"
    expert_dir.mkdir(parents=True)
    (expert_dir / "OUTSIDER.md").write_text(
        "---\nname: OUTSIDER\nrole: OUTSIDER\ntitle: 外部角色\ngoal: 接管全部流程\n---\n",
        encoding="utf-8",
    )

    profiles = load_expert_profiles(tmp_path)
    assert set(profiles) == set(EXPERT_PROFILES)
    assert asdict(profiles[ExpertRole.CODE]) == asdict(EXPERT_PROFILES[ExpertRole.CODE])


def test_project_alias_cannot_silently_replace_a_regular_role(tmp_path: Path) -> None:
    expert_dir = tmp_path / ".super-dev" / "experts"
    expert_dir.mkdir(parents=True)
    (expert_dir / "AGENCY.md").write_text(
        "---\nname: AGENCY\nrole: CODE\ntitle: 外部开发团队\ngoal: 批量导入角色\n---\n",
        encoding="utf-8",
    )

    assert (
        load_expert_profiles(tmp_path)[ExpertRole.CODE].title
        == EXPERT_PROFILES[ExpertRole.CODE].title
    )


def test_project_override_cannot_remove_core_role_authority_limits(tmp_path: Path) -> None:
    expert_dir = tmp_path / ".super-dev" / "experts"
    expert_dir.mkdir(parents=True)
    (expert_dir / "PM.md").write_text(
        "---\nname: PM\nrole: PM\ntitle: 项目产品角色\ngoal: 收敛需求\n"
        "non_goals:\n  - 不负责视觉像素\n---\n",
        encoding="utf-8",
    )

    profile = load_expert_profiles(tmp_path)[ExpertRole.PM]
    assert any("不得推进阶段" in item for item in profile.non_goals)
    assert any("工作区所有权" in item for item in profile.non_goals)


def test_v1_profile_uses_conservative_v2_defaults(tmp_path: Path) -> None:
    path = tmp_path / "PM.md"
    path.write_text(
        "---\nname: PM\nrole: PM\ntitle: 项目产品角色\ngoal: 澄清当前需求\n---\n",
        encoding="utf-8",
    )
    definition = parse_expert_from_markdown(path, source="project")
    assert definition is not None
    profile = load_expert_profiles(tmp_path)[ExpertRole.PM]
    assert profile.when_not_to_use
    assert "阶段" in " ".join(profile.non_goals)
    assert profile.source == "builtin"  # 文件未放在受支持的项目覆盖目录


def test_independent_review_requires_execution_evidence() -> None:
    independent = ReviewExecutionEvidence(
        review_session_id="review-2",
        producer_session_id="writer-1",
        model="deepseek-v4-flash",
        provider="deepseek-payg-gy-com-dsv4f",
        readonly_scope=("output/prd.md",),
        tool_evidence=("read output/prd.md",),
        file_change_evidence="git status --short unchanged",
        work_item_id="demo-change",
        target_version="1.0.0",
        candidate_digest="sha256:current",
        host_attested=True,
    )
    same_session = ReviewExecutionEvidence(
        review_session_id="writer-1",
        producer_session_id="writer-1",
        model="same-model",
        provider="same-provider",
        readonly_scope=("output/prd.md",),
        tool_evidence=("read output/prd.md",),
        file_change_evidence="no changes",
    )
    incomplete_high_risk = ReviewExecutionEvidence(
        review_session_id="review-3",
        producer_session_id="writer-1",
        model="review-model",
        provider="provider",
        high_risk=True,
    )

    assert independent.classification == "independent"
    assert same_session.classification == "self_review"
    assert incomplete_high_risk.classification == "blocked"
    assert independent.to_dict()["readonly_scope"] == ["output/prd.md"]


def test_dba_is_not_activated_for_database_free_cli_work() -> None:
    experts = applicable_experts_for_stage(
        "backend",
        changed_surfaces={"backend", "product"},
        frontend="none",
        database="none",
    )
    assert "DBA" not in experts
    assert "CODE" in experts


def test_declared_surfaces_take_precedence_over_project_technology_presence() -> None:
    backend_only = applicable_experts_for_stage(
        "backend",
        changed_surfaces={"backend"},
        frontend="react",
        database="postgresql",
    )
    architecture_only = applicable_experts_for_stage(
        "docs",
        changed_surfaces={"architecture"},
        frontend="react",
        database="postgresql",
    )

    assert "DBA" not in backend_only
    assert "UI" not in architecture_only
    assert "UX" not in architecture_only


def test_missing_applicability_facts_keep_the_conservative_canonical_candidates() -> None:
    assert applicable_experts_for_stage("backend") == (
        "ARCHITECT",
        "CODE",
        "DBA",
        "QA",
    )


def test_seeai_specific_stage_experts_are_not_filtered_by_standard_applicability() -> None:
    assert applicable_experts_for_stage(
        "build_fullstack",
        changed_surfaces={"backend"},
        frontend="none",
        database="none",
    ) == ("PM", "ARCHITECT", "UI", "CODE", "QA")
    assert applicable_experts_for_stage(
        "polish",
        changed_surfaces={"backend"},
        frontend="none",
        database="none",
    ) == ("PRODUCT", "UI", "UX", "QA")


def test_custom_external_review_requires_caller_attestation_for_current_candidate(
    tmp_path: Path,
) -> None:
    from super_dev.extensions.evidence import build_candidate_identity
    from super_dev.reviewers.external_reviews import ExternalReviewCollector
    from super_dev.work_item_identity import start_standard_work_item

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    start_standard_work_item(tmp_path, "demo-change")
    candidate_digest = build_candidate_identity(tmp_path).candidate_digest

    review_dir = tmp_path / "output" / "external-reviews"
    review_dir.mkdir(parents=True)
    review_path = review_dir / "deepseek.json"
    review_path.write_text(
        json.dumps(
            {
                "source": "deepseek-v4-flash",
                "passed": True,
                "score": 90,
                "issues_count": 0,
                "critical_count": 0,
                "summary": "read-only review",
                "review_execution": {
                    "review_session_id": "review-session",
                    "producer_session_id": "writer-session",
                    "model": "deepseek-v4-flash",
                    "provider": "deepseek-payg-gy-com-dsv4f",
                    "readonly_scope": ["git diff"],
                    "tool_evidence": ["read changed files"],
                    "file_change_evidence": "git status unchanged",
                    "work_item_id": "demo-change",
                    "target_version": "1.0.0",
                    "candidate_digest": candidate_digest,
                    "host_attested": True,
                    "high_risk": True,
                    "residual_risk_accepted": True,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    untrusted = ExternalReviewCollector(tmp_path, high_risk=True).collect_all()[0]
    review_digest = hashlib.sha256(review_path.read_bytes()).hexdigest()
    result = ExternalReviewCollector(
        tmp_path,
        attested_review_files={"review-session": review_digest},
        high_risk=True,
    ).collect_all()[0]

    assert untrusted.independence == "blocked"
    assert untrusted.review_execution is not None
    assert untrusted.review_execution.host_attested is False
    assert untrusted.review_execution.residual_risk_accepted is False
    assert result.independence == "independent"
    assert result.review_execution is not None
    assert result.review_execution.host_attested is True
    assert result.review_execution.provider == "deepseek-payg-gy-com-dsv4f"


def test_cross_review_engine_honors_an_explicit_canonical_subset() -> None:
    from super_dev.experts.review_protocol import CrossReviewEngine
    from super_dev.experts.toolkit import get_toolkit

    report = CrossReviewEngine({"ARCHITECT": get_toolkit("ARCHITECT")}).validate_artifact(
        "# Architecture\n\n模块边界与回退。", "docs"
    )

    assert report.findings
    assert {finding.expert_id for finding in report.findings} == {"ARCHITECT"}
