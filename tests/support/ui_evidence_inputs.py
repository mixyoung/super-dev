"""Synthetic test inputs only. They do not attest to a real host run."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from super_dev.evidence_contract import EvidenceStatus
from super_dev.reviewers.ui_review_evidence import (
    DIMENSIONS,
    RUNTIME,
    VISUAL,
    UIReviewEvidence,
)
from super_dev.work_item_identity import bind_standard_work_item, start_standard_work_item
from super_dev.workflow_guard import save_bound_docs_confirmation

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGMQEpUAAAB8AECFvjD9AAAAAElFTkSuQmCC"
)
TIME = "2026-11-27T01:00:00+08:00"
FIXTURE = "ui-fixture"


def dump(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def ref(project: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(project).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def create_ui_project(project: Path) -> UIReviewEvidence:
    output = project / "output"
    output.mkdir(parents=True, exist_ok=True)
    (project / "super-dev.yaml").write_text(
        "name: ui-fixture\nplatform: web\nfrontend: react\nbackend: none\n", encoding="utf-8"
    )
    for doc in ("research", "prd", "architecture", "uiux"):
        (output / f"{FIXTURE}-{doc}.md").write_text(
            "# Test contract: visible title and status", encoding="utf-8"
        )
    (project / "frontend").mkdir(exist_ok=True)
    (project / "frontend" / "index.html").write_text(
        "<!doctype html><title>Test fixture</title>", encoding="utf-8"
    )
    dump(
        output / f"{FIXTURE}-ui-contract.json",
        {"screen_recipes": [{"id": "home", "required_states": ["saved"]}]},
    )
    start_standard_work_item(project, FIXTURE)
    save_bound_docs_confirmation(project, {"status": "confirmed", "actor": "pytest"})
    (project / ".super-dev" / "changes" / FIXTURE).mkdir(parents=True, exist_ok=True)
    bind_standard_work_item(project, FIXTURE)
    return UIReviewEvidence(project, FIXTURE)


def publish_source(
    evidence: UIReviewEvidence, *, status: EvidenceStatus = EvidenceStatus.PASS
) -> None:
    evidence.save_source(
        evidence.source_result(
            status=status,
            detail="合成源码检查",
            score=98,
            findings=[],
            alignment={},
            files=[evidence.project / "frontend/index.html"],
        )
    )


def browser_record(
    evidence: UIReviewEvidence,
    *,
    workflow_run_id: str = "",
    mobile: bool = True,
    fail: bool = False,
    asset: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    store = evidence.output / "ui-review"
    store.mkdir(exist_ok=True)
    page_asset = ref(evidence.project, asset or evidence.project / "frontend/index.html")
    pages = []
    for screen, device, state in sorted(evidence._matrix()):
        if device == "mobile" and not mobile:
            continue
        page_id = f"{screen}-{device}-{state}"
        shot = store / f"{page_id}.png"
        shot.write_bytes(PNG)
        pages.append(
            {
                "id": page_id,
                "screen": screen,
                "state": state,
                "url": "http://127.0.0.1:8765/",
                "viewport": {
                    "device": device,
                    "width": 375 if device == "mobile" else 1280,
                    "height": 800,
                },
                "observed_at": TIME,
                "event_id": f"synthetic-event-{page_id}",
                "file": ref(evidence.project, shot),
                "loaded_files": [page_asset],
                "steps": [
                    {
                        "kind": "navigation",
                        "action": "Navigate to fixture",
                        "expected": "Title is visible",
                        "observed": "Found fixture title",
                        "status": "PASS",
                    },
                    {
                        "kind": "interaction",
                        "action": "Activate save",
                        "expected": "Show status",
                        "observed": "Control unresponsive" if fail else "Visible saved status",
                        "status": "FAIL" if fail else "PASS",
                    },
                ],
            }
        )
    raw = {
        "format": "super-dev-browser-run/v1",
        "producer": {"kind": "browser", "host": "pytest", "id": "synthetic-browser"},
        "run_id": "synthetic-browser-run",
        "observed_at": TIME,
        "binding": evidence.capture_binding(),
        "workflow_run_id": workflow_run_id,
        "pages": pages,
    }
    return dump(store / "browser.json", raw), raw


def vision_record(
    evidence: UIReviewEvidence,
    pages: list[dict[str, Any]],
    *,
    fail: bool = False,
    content_type: str = "image",
    producer_kind: str = "host_model",
) -> tuple[Path, dict[str, Any]]:
    store = evidence.output / "ui-review"
    producer = {"kind": producer_kind, "host": "pytest", "id": "synthetic-visual-checker"}
    attachments = []
    for page in pages:
        event_id = f"synthetic-image-event-{page['id']}"
        event = dump(
            store / f"{event_id}.json",
            {
                "type": "image_message",
                "id": event_id,
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64.b64encode(PNG).decode(),
                        },
                    }
                ],
            },
        )
        attachments.append(
            {
                "screenshot_id": page["id"],
                "content_type": content_type,
                "sha256": page["file"]["sha256"],
                "media_type": "image/png",
                "event_id": event_id,
                "input_event": ref(evidence.project, event),
            }
        )
    run_id = "synthetic-review-run"
    input_id = attachments[0]["event_id"] if attachments else "no-synthetic-images"
    response_id = "synthetic-visual-response"
    inputs = dump(
        store / "image-input.json",
        {
            "format": "super-dev-host-image-input/v1",
            "producer": producer,
            "run_id": run_id,
            "observed_at": TIME,
            "input_event_id": input_id,
            "attachments": attachments,
        },
    )
    raw = {
        "format": "super-dev-image-review/v1",
        "producer": producer,
        "run_id": run_id,
        "observed_at": TIME,
        "binding": evidence.capture_binding(),
        "browser_run_id": "synthetic-browser-run",
        "response_event_id": response_id,
        "response_to": input_id,
        "input_record": ref(evidence.project, inputs),
        "observations": [
            {
                "screenshot_id": page["id"],
                "dimension": dimension,
                "status": "FAIL" if fail and dimension == "layout" else "PASS",
                "location": "below the title at start of note",
                "requirement": "note and status text in order without overlap",
                "observation": (
                    "Status covers explanatory note"
                    if fail and dimension == "layout"
                    else f"{dimension}: note and status have separate positions"
                ),
                "impact": "Note is unreadable",
                "recommendation": "Place the status below the save control",
            }
            for page in pages
            for dimension in DIMENSIONS
        ],
    }
    response = dump(
        store / "image-response.json",
        {
            "type": "tool_result" if producer_kind == "vision_tool" else "review_message",
            "id": response_id,
            "timestamp": TIME,
            "content": raw["observations"] or ["No observations in synthetic response"],
        },
    )
    raw["response_record"] = ref(evidence.project, response)
    return dump(store / "vision.json", raw), raw


def publish_browser(evidence: UIReviewEvidence, **kwargs: Any) -> dict[str, Any]:
    path, raw = browser_record(evidence, **kwargs)
    evidence.record_host_result(RUNTIME, path.relative_to(evidence.project).as_posix())
    return raw


def publish_vision(
    evidence: UIReviewEvidence, pages: list[dict[str, Any]], **kwargs: Any
) -> dict[str, Any]:
    path, raw = vision_record(evidence, pages, **kwargs)
    evidence.record_host_result(VISUAL, path.relative_to(evidence.project).as_posix())
    return raw
