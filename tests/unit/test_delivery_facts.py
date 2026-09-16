from __future__ import annotations

from super_dev.delivery_facts import (
    DeliveryFacts,
    DeliveryFactStatus,
    OperationalOutcome,
    build_delivery_facts,
    merge_preserved_post_delivery_facts,
    resolve_project_target_version,
)
from super_dev.proof_pack import ProofPackReport
from super_dev.release_readiness import ReleaseReadinessCheck, ReleaseReadinessReport
from super_dev.workflow_contract import CANONICAL_NINE_STAGE_IDS


def test_delivery_facts_are_independent_and_not_workflow_stages() -> None:
    facts = build_delivery_facts(
        delivery_ready=True,
        deployed=True,
        evidence={
            "delivery_ready": ["quality gate passed"],
            "deployed": ["target health check passed"],
        },
        sources={"delivery_ready": "quality", "deployed": "deployment"},
        observed_at={"delivery_ready": "2026-09-14", "deployed": "2026-09-14"},
        target_versions={"delivery_ready": "2.5.1", "deployed": "2.5.1"},
    )

    assert facts.delivery_ready.status is DeliveryFactStatus.VERIFIED
    assert facts.deployed.status is DeliveryFactStatus.VERIFIED
    assert facts.released.status is DeliveryFactStatus.UNKNOWN
    assert facts.operating.status is DeliveryFactStatus.UNKNOWN
    assert not {"delivery_ready", "released", "deployed", "operating"} & set(
        CANONICAL_NINE_STAGE_IDS
    )


def test_operational_outcome_without_source_or_version_is_pending() -> None:
    outcome = OperationalOutcome.from_dict(
        {
            "signal": "出现一次事故",
            "observed_at": "2026-09-14T00:00:00Z",
            "evidence": ["口头描述"],
            "confidence": "verified",
            "impact": "待分析",
            "recommended_action": "进入下一次 baseline 核对",
        }
    )
    assert outcome.confidence == "pending"
    assert outcome.target_version == ""


def test_deployed_does_not_imply_operating() -> None:
    facts = build_delivery_facts(
        deployed=True,
        evidence={"deployed": ["deployment id=123"]},
        sources={"deployed": "deployment api"},
        observed_at={"deployed": "2026-09-14"},
        target_versions={"deployed": "2.5.1"},
    )
    assert facts.deployed.status is DeliveryFactStatus.VERIFIED
    assert facts.operating.status is DeliveryFactStatus.UNKNOWN
    assert facts.delivery_ready.status is DeliveryFactStatus.UNKNOWN


def test_release_and_proof_reports_expose_optional_backward_compatible_facts() -> None:
    readiness = ReleaseReadinessReport(
        project_name="demo",
        target_version="1.0.0",
        threshold=1,
        checks=[ReleaseReadinessCheck(name="gate", passed=True, detail="ok")],
    ).to_dict()
    proof = ProofPackReport(project_name="demo", target_version="1.0.0").to_dict()

    assert readiness["delivery_facts"]["delivery_ready"]["status"] == "verified"
    assert readiness["delivery_facts"]["released"]["status"] == "unknown"
    assert readiness["operational_outcomes"] == []
    assert proof["delivery_facts"]["released"]["status"] == "unknown"
    assert proof["operational_outcomes"] == []


def test_report_dict_facts_are_revalidated_and_bound_to_current_version() -> None:
    readiness = ReleaseReadinessReport(
        project_name="demo",
        target_version="2.0.0",
        threshold=1,
        checks=[ReleaseReadinessCheck(name="gate", passed=True, detail="ok")],
        delivery_facts={
            "released": {
                "status": "verified",
                "evidence": ["old asset"],
                "source": "release api",
                "observed_at": "2026-09-14",
                "target_version": "1.0.0",
            },
            "deployed": {"status": "verified"},
        },
    ).to_dict()

    assert readiness["delivery_facts"]["delivery_ready"]["status"] == "verified"
    assert readiness["delivery_facts"]["released"]["status"] == "pending"
    assert readiness["delivery_facts"]["deployed"]["status"] == "pending"


def test_regeneration_recomputes_readiness_but_preserves_valid_later_facts() -> None:
    current = build_delivery_facts(
        delivery_ready=False,
        evidence={"delivery_ready": ["quality gate failed"]},
        target_versions={"delivery_ready": "2.5.1"},
    )
    preserved = build_delivery_facts(
        delivery_ready=True,
        released=True,
        deployed=True,
        evidence={
            "delivery_ready": ["old readiness"],
            "released": ["release asset"],
            "deployed": ["deployment health"],
        },
        sources={"released": "release api", "deployed": "deployment api"},
        observed_at={"released": "2026-09-14", "deployed": "2026-09-14"},
        target_versions={"released": "2.5.1", "deployed": "2.5.1"},
    ).to_dict()

    merged = merge_preserved_post_delivery_facts(current, preserved)
    assert merged.delivery_ready.status is DeliveryFactStatus.REFUTED
    assert merged.released.status is DeliveryFactStatus.VERIFIED
    assert merged.deployed.status is DeliveryFactStatus.VERIFIED
    assert merged.operating.status is DeliveryFactStatus.UNKNOWN


def test_unbound_verified_fact_is_downgraded_when_loaded() -> None:
    facts = DeliveryFacts.from_dict(
        {"released": {"status": "verified", "evidence": ["asset exists"]}}
    )
    assert facts.released.status is DeliveryFactStatus.PENDING


def test_programmatic_fact_without_source_time_or_version_is_pending() -> None:
    facts = build_delivery_facts(
        deployed=True,
        evidence={"deployed": ["deployment id=123"]},
    )
    assert facts.deployed.status is DeliveryFactStatus.PENDING


def test_string_evidence_is_one_item_not_one_item_per_character() -> None:
    facts = build_delivery_facts(
        deployed=True,
        evidence={"deployed": "deployment id=123"},
        sources={"deployed": "deployment api"},
        observed_at={"deployed": "2026-09-14"},
        target_versions={"deployed": "2.5.1"},
    )

    assert facts.deployed.evidence == ("deployment id=123",)


def test_preserved_fact_for_another_version_is_not_currently_verified() -> None:
    current = build_delivery_facts(
        delivery_ready=True,
        evidence={"delivery_ready": ["quality passed"]},
        sources={"delivery_ready": "quality"},
        observed_at={"delivery_ready": "2026-09-14"},
        target_versions={"delivery_ready": "2.5.1"},
    )
    old = build_delivery_facts(
        released=True,
        evidence={"released": ["old asset"]},
        sources={"released": "release api"},
        observed_at={"released": "2026-09-01"},
        target_versions={"released": "2.4.0"},
    ).to_dict()

    merged = merge_preserved_post_delivery_facts(current, old)

    assert merged.released.status is DeliveryFactStatus.PENDING
    assert merged.released.target_version == "2.4.0"


def test_preserved_verified_fact_is_pending_when_current_version_is_unknown() -> None:
    current = build_delivery_facts(
        delivery_ready=False,
        evidence={"delivery_ready": ["quality failed"]},
    )
    preserved = build_delivery_facts(
        released=True,
        evidence={"released": ["old asset"]},
        sources={"released": "release api"},
        observed_at={"released": "2026-09-01"},
        target_versions={"released": "2.4.0"},
    ).to_dict()

    merged = merge_preserved_post_delivery_facts(current, preserved)

    assert merged.released.status is DeliveryFactStatus.PENDING


def test_project_target_version_prefers_reviewed_project_manifest(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "3.4.5"\n',
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"name": "demo-web", "version": "9.9.9"}',
        encoding="utf-8",
    )

    assert resolve_project_target_version(tmp_path, configured_version="1.0.0") == "3.4.5"


def test_project_target_version_falls_back_to_project_config(tmp_path) -> None:
    assert resolve_project_target_version(tmp_path, configured_version="1.2.3") == "1.2.3"
