"""UI evidence boundary: synthetic records never stand in for real host testing."""

from pathlib import Path

import pytest

from super_dev.evidence_contract import EvidenceStatus
from super_dev.proof_pack import ProofPackBuilder
from super_dev.release_readiness import ReleaseReadinessEvaluator
from super_dev.reviewers.quality_gate import CheckStatus, QualityGateChecker
from super_dev.reviewers.ui_review_evidence import (
    RUNTIME,
    SOURCE,
    VISUAL,
    UIReviewEvidence,
    aggregate_ui_status,
)
from super_dev.workflow_guard import WorkflowGateError, require_preview_confirmation
from tests.support.ui_evidence_inputs import (
    FIXTURE,
    browser_record,
    create_ui_project,
    dump,
    publish_browser,
    publish_source,
    publish_vision,
    ref,
    vision_record,
)


def test_no_reading_is_not_visual_pass_or_failure(tmp_path: Path):
    evidence = create_ui_project(tmp_path)
    publish_browser(evidence)
    publish_source(evidence)
    aggregate = UIReviewEvidence(tmp_path, FIXTURE)
    assert aggregate.result(SOURCE).status is EvidenceStatus.PASS
    assert aggregate.result(RUNTIME).status is EvidenceStatus.PASS
    assert aggregate.result(VISUAL).status is EvidenceStatus.BLOCKED
    assert aggregate_ui_status(aggregate.results()) is EvidenceStatus.BLOCKED
    pack = ProofPackBuilder(tmp_path, persist_artifacts=False)
    assert pack._frontend_runtime_artifact().status == "ready"
    assert pack._ui_review_artifact().details["status"] == "BLOCKED"
    closure = ReleaseReadinessEvaluator(tmp_path)._check_delivery_closure()
    assert not closure.passed
    assert closure.evidence["ui_results"][VISUAL]["status"] == "BLOCKED"
    quality = QualityGateChecker(tmp_path, FIXTURE, {"frontend": "react", "platform": "web"})
    quality._check_ui_review()
    assert quality.latest_ui_review_report.to_dict()["results"][VISUAL]["status"] == "BLOCKED"


@pytest.mark.parametrize("producer", ["host_model", "vision_tool"])
def test_complete_synthetic_bundle_still_requires_user_preview(tmp_path: Path, producer: str):
    evidence = create_ui_project(tmp_path)
    raw = publish_browser(evidence)
    publish_vision(evidence, raw["pages"], producer_kind=producer)
    publish_source(evidence)
    results = evidence.results()
    assert aggregate_ui_status(results) is EvidenceStatus.PASS
    assert evidence.result(VISUAL).payload["producer"]["kind"] == producer
    assert (
        ProofPackBuilder(tmp_path, persist_artifacts=False)._ui_review_artifact().status == "ready"
    )
    with pytest.raises(WorkflowGateError, match="预览尚未确认"):
        require_preview_confirmation(tmp_path, action="test independent preview gate")


def test_real_findings_take_precedence_over_uncovered(tmp_path: Path):
    evidence = create_ui_project(tmp_path)
    raw = publish_browser(evidence, mobile=False)
    publish_vision(evidence, raw["pages"], fail=True)
    assert evidence.result(RUNTIME).status is EvidenceStatus.BLOCKED
    visual = evidence.result(VISUAL)
    assert visual.status is EvidenceStatus.FAIL
    assert visual.payload["uncovered"]
    assert visual.payload["findings"][0]["location"]
    assert aggregate_ui_status(evidence.results()) is EvidenceStatus.FAIL
    report = QualityGateChecker(tmp_path, FIXTURE, {"frontend": "react", "platform": "web"})
    assert report._check_ui_review().status is CheckStatus.FAILED


@pytest.mark.parametrize("content_type", ["text", "path", "ocr", "pixels"])
def test_partial_capability_cannot_claim_visual_pass(tmp_path: Path, content_type: str):
    evidence = create_ui_project(tmp_path)
    raw = publish_browser(evidence)
    publish_vision(evidence, raw["pages"], content_type=content_type)
    result = evidence.result(VISUAL)
    assert result.status is EvidenceStatus.BLOCKED
    assert result.reason == "visual_coverage"


@pytest.mark.parametrize(
    "changed_input", ["code", "shot", "input_log", "response", "uiux", "contract"]
)
def test_changed_input_invalidates_visual_result(tmp_path: Path, changed_input: str):
    evidence = create_ui_project(tmp_path)
    raw = publish_browser(evidence)
    publish_vision(evidence, raw["pages"])
    assert evidence.result(VISUAL).status is EvidenceStatus.PASS
    paths = {
        "code": tmp_path / "frontend/index.html",
        "shot": evidence.output / raw["pages"][0]["file"]["path"].removeprefix("output/"),
        "input_log": evidence.output / "ui-review/image-input.json",
        "response": evidence.output / "ui-review/image-response.json",
        "uiux": evidence.uiux,
        "contract": evidence.contract,
    }
    path = paths[changed_input]
    path.write_bytes(path.read_bytes() + b"\n ")
    assert UIReviewEvidence(tmp_path, FIXTURE).result(VISUAL).status is EvidenceStatus.BLOCKED


def test_host_input_from_another_work_item_cannot_be_published(tmp_path: Path):
    evidence = create_ui_project(tmp_path)
    path, receipt = browser_record(evidence)
    receipt["binding"]["work_item_id"] = "different-fixture"
    dump(path, receipt)
    with pytest.raises(ValueError, match="不属于当前工作项"):
        evidence.record_host_result(RUNTIME, path.relative_to(tmp_path).as_posix())
    assert evidence.result(RUNTIME).status is EvidenceStatus.BLOCKED


def test_legacy_pixel_pass_is_not_visual_evidence(tmp_path: Path):
    evidence = create_ui_project(tmp_path)
    dump(
        evidence.path(VISUAL),
        {"passed": True, "vision_used": True, "screenshot_visual_judge": {"passed": True}},
    )
    assert evidence.result(VISUAL).status is EvidenceStatus.BLOCKED
    assert evidence.result(VISUAL).reason == "legacy"


def test_blocked_result_envelope_is_not_fail(tmp_path: Path):
    evidence = create_ui_project(tmp_path)
    raw = publish_browser(evidence, mobile=False)
    publish_vision(evidence, raw["pages"])
    content = evidence._json(evidence.path(VISUAL))
    assert content["passed"] is False
    assert content["status"] == content["evidence_envelope"]["status"] == "BLOCKED"


@pytest.mark.parametrize(
    "reason", ["no_image_capability", "image_transfer_failed", "tool_unavailable"]
)
def test_explicit_capability_gap_retains_other_evidence(tmp_path: Path, reason: str):
    evidence = create_ui_project(tmp_path)
    publish_source(evidence)
    raw = publish_browser(evidence)
    path, report = vision_record(evidence, raw["pages"])
    dump(path, {**report, "blocked_reason": reason, "input_record": {}, "observations": []})
    evidence.record_host_result(VISUAL, path.relative_to(tmp_path).as_posix())
    source, runtime, visual = evidence.results()
    assert source.status is runtime.status is EvidenceStatus.PASS
    assert visual.status is EvidenceStatus.BLOCKED and visual.reason == reason


@pytest.mark.parametrize("gap", ["text_block", "derivation", "response", "vague"])
def test_picture_event_and_specific_response_are_required(tmp_path: Path, gap: str):
    evidence = create_ui_project(tmp_path)
    runtime = publish_browser(evidence)
    path, report = vision_record(evidence, runtime["pages"])
    if gap in {"text_block", "derivation"}:
        input_path = tmp_path / report["input_record"]["path"]
        inputs = evidence._json(input_path)
        for attachment in inputs["attachments"]:
            if gap == "derivation":
                attachment["derivation"] = {
                    "operation": "crop",
                    "original_sha256": attachment["sha256"],
                }
            else:
                event_path = tmp_path / attachment["input_event"]["path"]
                event = evidence._json(event_path)
                dump(
                    event_path,
                    {**event, "content": [{"type": "text", "text": attachment["sha256"]}]},
                )
                attachment["input_event"] = ref(tmp_path, event_path)
        report["input_record"] = ref(tmp_path, dump(input_path, inputs))
    elif gap == "response":
        report.pop("response_record")
    else:
        for observation in report["observations"]:
            observation["observation"] = "已检查"
    dump(path, report)
    evidence.record_host_result(VISUAL, path.relative_to(tmp_path).as_posix())
    assert evidence.result(VISUAL).status is EvidenceStatus.BLOCKED
    assert evidence.result(VISUAL).reason == (
        "image_response_missing" if gap == "response" else "visual_coverage"
    )


def test_source_probe_and_navigation_do_not_prove_browser_interaction(tmp_path: Path):
    evidence = create_ui_project(tmp_path)
    path, record = browser_record(evidence)
    for page in record["pages"]:
        page["steps"] = page["steps"][:1]
    dump(path, record)
    result = evidence.record_host_result(RUNTIME, path.relative_to(tmp_path).as_posix())
    assert result.status is EvidenceStatus.BLOCKED and result.reason == "browser_coverage"
    assert result.payload["uncovered"]


def test_browser_navigation_failure_can_be_reported_without_a_screenshot(tmp_path: Path):
    evidence = create_ui_project(tmp_path)
    path, record = browser_record(evidence, mobile=False)
    for page in record["pages"]:
        page.pop("file")
        page["steps"][0].update(status="FAIL", observed="Browser received HTTP 500")
        page["steps"] = page["steps"][:1]
    dump(path, record)
    result = evidence.record_host_result(RUNTIME, path.relative_to(tmp_path).as_posix())
    assert result.status is EvidenceStatus.FAIL and result.reason == "browser_failed"
    assert result.payload["findings"][0]["observed"] == "Browser received HTTP 500"


def test_non_ui_does_not_open_ui_artifacts(tmp_path: Path):
    evidence = UIReviewEvidence(tmp_path, FIXTURE, required=False)
    assert aggregate_ui_status(evidence.results()) is EvidenceStatus.NOT_APPLICABLE
    assert not (tmp_path / "output").exists()
