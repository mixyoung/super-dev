from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_dev.cli import SuperDevCLI
from super_dev.reviewers.architecture_drift import (
    inspect_architecture_drift_artifact,
    run_architecture_drift,
)
from super_dev.reviewers.quality_gate import QualityGateChecker
from super_dev.reviewers.source_inventory import SourceInventory, SourceScanError, source_scan_scope
from super_dev.reviewers.spec_compliance import (
    inspect_spec_compliance_artifact,
    run_spec_compliance,
)
from super_dev.reviewers.uiux_compliance import run_uiux_compliance


def prepare(root: Path) -> None:
    (root / "output").mkdir()
    (root / "super-dev.yaml").write_text(
        "name: demo\nplatform: cli\nfrontend: none\nbackend: python\nquality_gate: 90\n",
        encoding="utf-8",
    )
    (root / "output/demo-prd.md").write_text(
        "# PRD\n\n## Login\n\n1. User login must be supported.\n", encoding="utf-8"
    )
    (root / "output/demo-architecture.md").write_text(
        "# Architecture\n\n## Tech Stack\n\n- FastAPI\n", encoding="utf-8"
    )
    (root / "output/demo-uiux.md").write_text("# No frontend\n", encoding="utf-8")
    (root / "requirements.txt").write_text("fastapi==0.115.0\n", encoding="utf-8")
    (root / "app.py").write_text("def login_user():\n    return True\n", encoding="utf-8")


def test_real_consumers_share_one_discovery_and_one_validation(tmp_path):
    prepare(tmp_path)
    with source_scan_scope(tmp_path) as inventory:
        inspect_spec_compliance_artifact(tmp_path)
        spec = run_spec_compliance(tmp_path, persist=False)
        inspect_architecture_drift_artifact(tmp_path)
        architecture = run_architecture_drift(tmp_path, persist=False)
        uiux = run_uiux_compliance(tmp_path, persist=False)
        assert inventory.discovery_count == 1
        # Legacy unbound PRD selection matches this file by both existing patterns.
        assert spec.found == spec.total_requirements == 2
        assert architecture.score == 100
        assert uiux.files_scanned == 0
    assert inventory.discovery_count == 2
    assert sorted(p.name for p in (tmp_path / "output").iterdir()) == [
        "demo-architecture.md",
        "demo-prd.md",
        "demo-uiux.md",
    ]


def test_cli_quality_shares_inventory_and_writes_original_reports(tmp_path, monkeypatch):
    prepare(tmp_path)
    monkeypatch.chdir(tmp_path)
    discoveries = []
    original = SourceInventory._discover

    def observe(inventory):
        discoveries.append(inventory)
        return original(inventory)

    monkeypatch.setattr(SourceInventory, "_discover", observe)
    # The tiny fixture does not satisfy all delivery gates; do not mock a green gate.
    assert SuperDevCLI().run(["quality"]) == 1
    report = json.loads((tmp_path / "output/demo-quality-gate.json").read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert len(discoveries) == 2
    assert discoveries[0] is discoveries[1]
    assert (tmp_path / "output/demo-spec-compliance.json").is_file()
    assert (tmp_path / "output/demo-architecture-drift.json").is_file()


def test_pending_report_is_available_to_same_call_only(tmp_path):
    prepare(tmp_path)
    report_path = tmp_path / "output/demo-spec-compliance.json"
    with source_scan_scope(tmp_path) as inventory:
        first = run_spec_compliance(tmp_path)
        assert not report_path.exists()
        assert inspect_spec_compliance_artifact(tmp_path)["status"] == "ready"
        second = run_spec_compliance(tmp_path)
        assert second.to_dict() == first.to_dict()
        assert inventory.discovery_count == 1
    assert report_path.exists()
    assert inventory.discovery_count == 2


def test_rendering_does_not_rescan_or_use_callers_project(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    prepare(project)
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    discoveries = []
    original = SourceInventory._discover

    def observe(inventory):
        discoveries.append(inventory)
        return original(inventory)

    monkeypatch.setattr(SourceInventory, "_discover", observe)
    checker = QualityGateChecker(project_dir=project, name="demo", tech_stack={"frontend": "none"})
    result = checker.check()
    assert len(discoveries) == 2
    assert result._advisor_report is not None
    markdown = result.to_markdown()
    assert "## 质量顾问建议" in markdown
    assert result.to_markdown() == markdown
    assert len(discoveries) == 2
    assert not (other / "output").exists()
    (project / "added.py").write_text("value = 1\n", encoding="utf-8")
    checker.check()
    assert len(discoveries) == 4
    assert discoveries[0] is not discoveries[2]


def test_config_change_during_scan_invalidates_pending_report(tmp_path):
    prepare(tmp_path)
    with pytest.raises(SourceScanError, match="当前代码版本发生变化"):
        with source_scan_scope(tmp_path):
            run_spec_compliance(tmp_path)
            with (tmp_path / "super-dev.yaml").open("a", encoding="utf-8") as stream:
                stream.write("# Concurrent change\n")
    assert not (tmp_path / "output/demo-spec-compliance.json").exists()


def test_cli_scan_error_cannot_be_offset_by_other_checks(tmp_path, monkeypatch):
    prepare(tmp_path)
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "app.py"
    original = Path.read_bytes

    def deny(path):
        if path == target:
            raise PermissionError("test")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", deny)
    assert SuperDevCLI().run(["quality"]) == 1
    report = json.loads((tmp_path / "output/demo-quality-gate.json").read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert any("受阻" in item and "app.py" in item for item in report["critical_failures"])
    assert not (tmp_path / "output/demo-spec-compliance.json").exists()


@pytest.mark.parametrize(
    ("relative_path", "run"),
    [
        ("output/demo-prd.md", run_spec_compliance),
        ("output/demo-architecture.md", run_architecture_drift),
        ("output/demo-uiux.md", run_uiux_compliance),
        ("requirements.txt", run_architecture_drift),
    ],
)
def test_necessary_document_read_error_is_a_scan_failure(tmp_path, monkeypatch, relative_path, run):
    prepare(tmp_path)
    target = tmp_path / relative_path
    original = Path.read_text

    def deny(path, *args, **kwargs):
        if path == target:
            raise PermissionError("test")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", deny)
    with pytest.raises(SourceScanError, match="无法读取应检文件"):
        run(tmp_path, persist=False)


def test_new_document_in_excluded_output_invalidates_pending_report(tmp_path):
    prepare(tmp_path)
    with pytest.raises(SourceScanError, match="必要输入清单发生变化"):
        with source_scan_scope(tmp_path):
            run_spec_compliance(tmp_path)
            (tmp_path / "output/extra-prd.md").write_text(
                "# PRD\n\n## Password\n\n1. Password must be validated.\n", encoding="utf-8"
            )
    assert not (tmp_path / "output/demo-spec-compliance.json").exists()


def test_later_call_sees_new_untracked_source_and_invalidates_report(tmp_path):
    prepare(tmp_path)
    first = run_spec_compliance(tmp_path)
    (tmp_path / "new.py").write_text("def another_login(): return True\n", encoding="utf-8")
    second = run_spec_compliance(tmp_path)
    assert second.evidence_identity["inputs_digest"] != first.evidence_identity["inputs_digest"]
    assert "new.py" in second.evidence_identity["dependencies"]
