from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from super_dev.integrations.dsh_primary_bridge import apply_request
from super_dev.review_state import (
    load_docs_confirmation,
    load_workflow_state,
    save_baseline_confirmation,
)
from super_dev.skills.skill_template import SkillTemplate
from super_dev.workflow_guard import WorkflowGateError


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "super-dev.yaml").write_text(
        "name: native-fixture\nplatform: cli\nfrontend: none\nbackend: python\n", encoding="utf-8"
    )
    return tmp_path


def call(project: Path, op: str, *, mode: str = "standard", **fields):
    return apply_request(
        {
            "project": str(project),
            "session": "native-test-session",
            "mode": mode,
            "op": op,
            **fields,
        }
    )


def snapshots(project: Path) -> dict[str, bytes]:
    root = project / ".super-dev"
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def docs(project: Path, item: str) -> None:
    output = project / "output"
    output.mkdir()
    for suffix in ("research", "prd", "architecture", "uiux"):
        (output / f"{item}-{suffix}.md").write_text(f"# Native test {suffix}\n", encoding="utf-8")


@pytest.mark.parametrize("mode", ["standard", "seeai"])
def test_native_work_item_and_confirmed_spec_stay_bound(project, mode):
    started = call(project, "start", mode=mode)
    item = started["item"]
    assert started["policy"] == "draft"
    assert started["mode"] == mode and item.startswith("dsh-")
    assert "DSH 主开发插件契约" in started["instructions"]
    assert ".dsh/skills" not in started["instructions"]
    assert not (project / ".dsh").exists()
    state = load_workflow_state(project)
    assert state["dsh_primary_binding"]["session_id"] == "native-test-session"
    assert state["flow_variant"] == mode and state["work_item_id"] == item
    with pytest.raises(ValueError, match="未要求创建 Spec"):
        call(project, "spec", mode=mode, item=item)
    assert not (project / ".super-dev" / "changes" / item).exists()

    docs(project, item)
    before = snapshots(project)
    waiting = call(project, "inspect", mode=mode, item=item)
    assert waiting["policy"] == "wait" and waiting["stage"] == "docs_confirm"
    assert waiting["docs_digest"]
    assert snapshots(project) == before
    with pytest.raises(WorkflowGateError, match="确认版本已变化"):
        call(project, "confirm-docs", mode=mode, item=item, digest="0" * 64)
    assert load_docs_confirmation(project) is None

    approved = call(project, "confirm-docs", mode=mode, item=item, digest=waiting["docs_digest"])
    assert approved["stage"] == "spec"
    assert not (project / ".super-dev" / "changes" / item).exists()
    done = call(project, "spec", mode=mode, item=item)
    change = project / ".super-dev" / "changes" / item
    assert (change / "proposal.md").is_file() and (change / "tasks.md").is_file()
    state = load_workflow_state(project)
    assert state["active_change_id"] == item and state["flow_variant"] == mode
    assert done["policy"] == "implement"
    assert state["dsh_primary_binding"]["session_id"] == "native-test-session"

    (project / "output" / f"{item}-prd.md").write_text(
        "# revised after approval\n", encoding="utf-8"
    )
    assert call(project, "inspect", mode=mode, item=item)["policy"] == "wait"


def test_conflicting_project_owner_and_mode_do_not_replace_work(project):
    first = call(project, "start")
    before = snapshots(project)
    with pytest.raises(ValueError, match="不属于"):
        call(project, "start", mode="seeai")
    with pytest.raises(ValueError, match="不属于"):
        apply_request(
            {
                "project": str(project),
                "session": "other-session",
                "mode": "standard",
                "op": "inspect",
            }
        )
    with pytest.raises(ValueError, match="不属于"):
        call(project, "inspect", item="dsh-" + "0" * 20)
    assert snapshots(project) == before
    assert call(project, "start")["item"] == first["item"]
    assert snapshots(project) == before


def test_status_no_task_is_read_only(project):
    with pytest.raises(ValueError, match="没有已绑定"):
        call(project, "inspect")
    assert not (project / ".super-dev").exists()


@pytest.mark.parametrize("mode", ["standard", "seeai"])
def test_existing_projects_require_the_current_bound_baseline(project, mode):
    (project / "backend").mkdir()
    output = project / "output"
    output.mkdir()
    (output / "other-baseline-audit.md").write_text("# unrelated", encoding="utf-8")
    save_baseline_confirmation(project, {"status": "confirmed", "work_item_id": "other"})
    first = call(project, "start", mode=mode)
    item = first["item"]
    assert first["stage"] == "baseline" and first["policy"] == "draft"
    assert first["artifacts"] == [
        f"output/{item}-baseline-audit.md",
        f"output/{item}-baseline-audit.json",
    ]
    assert first["baseline_digest"] == ""
    audit = output / f"{item}-baseline-audit.md"
    audit.write_text("# owned current baseline", encoding="utf-8")
    waiting = call(project, "inspect", mode=mode, item=item)
    assert waiting["policy"] == "wait" and waiting["baseline_digest"]
    audit.write_text("# edited mid-review", encoding="utf-8")
    with pytest.raises(WorkflowGateError, match="确认版本已变化"):
        call(project, "confirm-baseline", mode=mode, item=item, digest=waiting["baseline_digest"])
    digest = call(project, "inspect", mode=mode, item=item)["baseline_digest"]
    opened = call(project, "confirm-baseline", mode=mode, item=item, digest=digest)
    assert opened["stage"] == "research" and opened["policy"] == "draft"
    assert opened["artifacts"] == [f"output/{item}-research.md"]
    audit.write_text("# third version", encoding="utf-8")
    assert call(project, "inspect", mode=mode, item=item)["policy"] == "wait"


def test_standard_frontend_requires_operator_evidence_and_bound_preview(project):
    (project / "super-dev.yaml").write_text(
        "name: native-fixture\nplatform: web\nfrontend: react\nbackend: python\n", encoding="utf-8"
    )
    item = call(project, "start")["item"]
    docs(project, item)
    waiting = call(project, "inspect", item=item)
    call(project, "confirm-docs", item=item, digest=waiting["docs_digest"])
    frontend = call(project, "spec", item=item)
    assert frontend["stage"] == "frontend" and frontend["policy"] == "frontend"
    assert not frontend["preview_digest"] and frontend["artifacts"] == []
    with pytest.raises(ValueError, match="不在适用的预览确认门"):
        call(project, "confirm-preview", item=item, digest="0" * 64)
    proof = project / "output" / f"{item}-frontend-runtime.json"
    # This is a Core proof-format fixture, not a successful browser run.
    proof.write_text('{"passed":true}', encoding="utf-8")
    ready = call(project, "inspect", item=item)
    assert ready["stage"] == "preview_confirm" and ready["policy"] == "wait"
    assert ready["preview_digest"]
    allowed = call(project, "confirm-preview", item=item, digest=ready["preview_digest"])
    assert allowed["stage"] == "backend" and allowed["policy"] == "implement"
    proof.write_text('{"passed":true,"revision":2}', encoding="utf-8")
    assert call(project, "inspect", item=item)["policy"] == "wait"


def test_same_approved_spec_attempt_can_resume_without_overwriting(project, monkeypatch):
    from super_dev.specs import SpecGenerator

    item = call(project, "start")["item"]
    docs(project, item)
    digest = call(project, "inspect", item=item)["docs_digest"]
    call(project, "confirm-docs", item=item, digest=digest)
    change = project / ".super-dev" / "changes" / item
    original = SpecGenerator.scaffold_change_artifacts

    def stop_after_proposal(self, *args, **kwargs):
        assert (change / "proposal.md").is_file()
        raise OSError("owned simulated interruption")

    with monkeypatch.context() as scoped:
        scoped.setattr(SpecGenerator, "scaffold_change_artifacts", stop_after_proposal)
        with pytest.raises(OSError, match="owned simulated interruption"):
            call(project, "spec", item=item)
    proposal = (change / "proposal.md").read_bytes()
    assert not (change / "plan.md").exists()
    assert load_workflow_state(project)["active_change_id"] == ""
    assert SpecGenerator.scaffold_change_artifacts is original
    assert call(project, "spec", item=item)["policy"] == "implement"
    assert (change / "proposal.md").read_bytes() == proposal
    assert (change / "plan.md").is_file()
    assert load_workflow_state(project)["active_change_id"] == item


def test_existing_spec_without_native_generation_receipt_is_not_adopted(project):
    item = call(project, "start")["item"]
    docs(project, item)
    call(
        project,
        "confirm-docs",
        item=item,
        digest=call(project, "inspect", item=item)["docs_digest"],
    )
    change = project / ".super-dev" / "changes" / item
    change.mkdir(parents=True)
    (change / "proposal.md").write_text("# user-owned proposal", encoding="utf-8")
    before = snapshots(project)
    with pytest.raises(ValueError, match="不会自动覆盖或接管"):
        call(project, "spec", item=item)
    assert snapshots(project) == before


@pytest.mark.parametrize(
    ("host", "standard", "seeai"),
    [
        (
            "claude-code",
            "288ee8c15e527b9acc3c5012387da2cfd7c27e3ad9b2189aa01ada81dd2d900b",
            "92dba112cf44e482262b1e38a4bbc46e79750dc114491cc9e2639bc65a700696",
        ),
        (
            "codex",
            "3a5aa563e4dd3771dbac601a2eedf876f314a8f442799192fa0e52f3c521bd9c",
            "059831378ccfd07853d781911012cb383d76ac4d19e406e3f5f7b887e0fd8cd7",
        ),
        (
            "codex-cli",
            "3a5aa563e4dd3771dbac601a2eedf876f314a8f442799192fa0e52f3c521bd9c",
            "059831378ccfd07853d781911012cb383d76ac4d19e406e3f5f7b887e0fd8cd7",
        ),
        (
            "deepseek-harness",
            "5d67bd0fbf4689f5829a859902bbb6f831e1c59879006a1e0235f1b689b6861c",
            "1e198e9005883c865c28d7305d645fdd0017452a5e891ed16394fbe95cda2494",
        ),
    ],
)
def test_existing_skill_templates_are_byte_stable(host, standard, seeai):
    for name, expected in (("super-dev", standard), ("super-dev-seeai", seeai)):
        text = SkillTemplate.for_builtin(name, host).render(host)
        assert sha256(text.encode("utf-8")).hexdigest() == expected
