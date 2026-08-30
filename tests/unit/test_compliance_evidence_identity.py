from __future__ import annotations

import json
from pathlib import Path

from super_dev.reviewers.architecture_drift import (
    inspect_architecture_drift_artifact,
    run_architecture_drift,
)
from super_dev.reviewers.spec_compliance import (
    inspect_spec_compliance_artifact,
    run_spec_compliance,
)
from super_dev.reviewers.uiux_compliance import (
    inspect_uiux_compliance_artifact,
    run_uiux_compliance,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _activate_change(project_dir: Path, change_id: str = "current-change") -> None:
    (project_dir / ".super-dev" / "changes" / change_id).mkdir(parents=True)
    _write(
        project_dir / ".super-dev" / "workflow-state.json",
        json.dumps({"active_change_id": change_id}),
    )


def _write_config(project_dir: Path, *, frontend: str) -> None:
    _write(
        project_dir / "super-dev.yaml",
        f"name: demo\nplatform: cli\nfrontend: {frontend}\nbackend: python\n",
    )


def test_spec_compliance_persists_and_reuses_evidence_identity(temp_project_dir: Path) -> None:
    output_dir = temp_project_dir / "output"
    _write(output_dir / "demo-prd.md", "# PRD\n\n## Login\n\n1. User login must be supported.\n")
    _write(temp_project_dir / "app.py", "def login_user():\n    return True\n")

    first = run_spec_compliance(temp_project_dir, output_dir)
    assert first.evidence_identity["artifact_name"] == "spec-compliance"
    assert first.evidence_identity["inputs_digest"]

    payload = json.loads(
        (output_dir / f"{first.project_name}-spec-compliance.json").read_text(encoding="utf-8")
    )
    assert payload["evidence_identity"]["inputs_digest"] == first.evidence_identity["inputs_digest"]
    assert (output_dir / "spec-compliance.json").is_file()

    second = run_spec_compliance(temp_project_dir, output_dir)
    assert second.to_dict() == first.to_dict()


def test_architecture_drift_recomputes_when_dependency_changes(temp_project_dir: Path) -> None:
    output_dir = temp_project_dir / "output"
    _write(output_dir / "demo-architecture.md", "# Architecture\n\n## Tech Stack\n\n- FastAPI\n")
    _write(temp_project_dir / "requirements.txt", "fastapi==0.115.0\n")
    _write(temp_project_dir / "service.py", "import fastapi\n")

    first = run_architecture_drift(temp_project_dir, output_dir)
    first_digest = first.evidence_identity["inputs_digest"]
    assert first_digest

    _write(temp_project_dir / "requirements.txt", "flask==3.0.0\n")
    second = run_architecture_drift(temp_project_dir, output_dir)
    second_digest = second.evidence_identity["inputs_digest"]

    assert second_digest
    assert second_digest != first_digest
    assert (output_dir / "architecture-drift.json").is_file()


def test_uiux_compliance_persists_evidence_identity(temp_project_dir: Path) -> None:
    output_dir = temp_project_dir / "output"
    _write(output_dir / "demo-uiux.md", "# UIUX\n\nicon_library: lucide\n")
    _write(
        temp_project_dir / "frontend" / "src" / "page.tsx",
        "import { Home } from 'lucide-react';\nexport function Page(){ return <Home /> }\n",
    )

    report = run_uiux_compliance(temp_project_dir, output_dir)
    assert report.evidence_identity["artifact_name"] == "uiux-compliance"
    assert report.evidence_identity["inputs_digest"]

    payload = json.loads(
        (output_dir / f"{report.project_name}-uiux-compliance.json").read_text(encoding="utf-8")
    )
    assert (
        payload["evidence_identity"]["inputs_digest"] == report.evidence_identity["inputs_digest"]
    )
    assert (output_dir / "uiux-compliance.json").is_file()


def test_active_change_spec_and_architecture_use_only_current_documents(
    temp_project_dir: Path,
) -> None:
    _activate_change(temp_project_dir)
    _write_config(temp_project_dir, frontend="none")
    output_dir = temp_project_dir / "output"
    _write(
        output_dir / "current-change-prd.md",
        "# PRD\n\n## Login\n\n1. Current login uses current_login_handler for users.\n",
    )
    _write(
        output_dir / "historical-prd.md",
        "# PRD\n\n## Billing\n\n1. Historical billing export is not implemented anywhere.\n",
    )
    _write(
        output_dir / "current-change-architecture.md",
        "# Architecture\n\n## Tech Stack\n\nFastAPI\n",
    )
    _write(
        output_dir / "historical-architecture.md",
        "# Architecture\n\n## Tech Stack\n\nReact\n",
    )
    _write(temp_project_dir / "requirements.txt", "fastapi==0.115.0\n")
    _write(
        temp_project_dir / "service.py",
        "import fastapi\n\ndef current_login_handler():\n    return True\n",
    )
    generic_spec = output_dir / "spec-compliance.json"
    generic_architecture = output_dir / "architecture-drift.json"
    _write(generic_spec, "spec sentinel\n")
    _write(generic_architecture, "architecture sentinel\n")

    spec_report = run_spec_compliance(temp_project_dir, output_dir)
    architecture_report = run_architecture_drift(temp_project_dir, output_dir)

    assert spec_report.project_name == "current-change"
    assert spec_report.total_requirements == 1
    assert architecture_report.project_name == "current-change"
    assert [item.lower() for item in architecture_report.declared_tech_stack] == ["fastapi"]
    assert generic_spec.read_text(encoding="utf-8") == "spec sentinel\n"
    assert generic_architecture.read_text(encoding="utf-8") == "architecture sentinel\n"
    assert inspect_spec_compliance_artifact(temp_project_dir, output_dir)["status"] == "ready"
    assert inspect_architecture_drift_artifact(temp_project_dir, output_dir)["status"] == "ready"
    spec_dependencies = {
        item.replace("\\", "/") for item in spec_report.evidence_identity["dependencies"]
    }
    architecture_dependencies = {
        item.replace("\\", "/") for item in architecture_report.evidence_identity["dependencies"]
    }
    assert "output/current-change-prd.md" in spec_dependencies
    assert "output/historical-prd.md" not in spec_dependencies
    assert "output/current-change-architecture.md" in architecture_dependencies
    assert "output/historical-architecture.md" not in architecture_dependencies


def test_active_change_specs_replace_prd_as_compliance_contract(
    temp_project_dir: Path,
) -> None:
    _activate_change(temp_project_dir)
    _write_config(temp_project_dir, frontend="none")
    output_dir = temp_project_dir / "output"
    _write(
        output_dir / "current-change-prd.md",
        "# PRD\n\n## Historical wording\n\n1. Missing legacy_handler must exist.\n",
    )
    spec_path = (
        temp_project_dir
        / ".super-dev"
        / "changes"
        / "current-change"
        / "specs"
        / "core"
        / "spec.md"
    )
    _write(
        spec_path,
        """# Current contract

## ADDED Requirements
### Requirement: Current handler (`current_handler`)
The current handler SHALL call `current_handler` for current requests.
#### Scenario: Request
- GIVEN a current request
- WHEN the handler runs
- THEN current_handler returns the current response
""",
    )
    _write(
        temp_project_dir / "service.py",
        'def current_handler():\n    """Current handler for current requests."""\n    return True\n',
    )

    report = run_spec_compliance(temp_project_dir, output_dir)

    assert report.total_requirements == 1
    assert report.found == 1
    assert report.score == 100
    dependencies = {item.replace("\\", "/") for item in report.evidence_identity["dependencies"]}
    assert ".super-dev/changes/current-change/specs/core/spec.md" in dependencies
    assert "output/current-change-prd.md" not in dependencies


def test_mixed_case_active_change_uses_sanitized_artifact_prefix(
    temp_project_dir: Path,
) -> None:
    _activate_change(temp_project_dir, "My_Change")
    _write_config(temp_project_dir, frontend="none")
    output_dir = temp_project_dir / "output"
    _write(
        output_dir / "my-change-prd.md",
        "# PRD\n\n## Login\n\n1. Login must use current_login_handler.\n",
    )
    _write(
        output_dir / "my-change-architecture.md",
        "# Architecture\n\n## Tech Stack\n\nFastAPI\n",
    )
    _write(output_dir / "my-change-uiux.md", "# 使用体验\n\nCLI 输出保持清晰。\n")
    _write(temp_project_dir / "requirements.txt", "fastapi==0.115.0\n")
    _write(
        temp_project_dir / "service.py",
        "import fastapi\n\ndef current_login_handler():\n    return True\n",
    )

    spec_report = run_spec_compliance(temp_project_dir, output_dir)
    architecture_report = run_architecture_drift(temp_project_dir, output_dir)
    uiux_report = run_uiux_compliance(temp_project_dir, output_dir)

    assert spec_report.project_name == "my-change"
    assert architecture_report.project_name == "my-change"
    assert uiux_report.project_name == "my-change"
    assert (output_dir / "my-change-spec-compliance.json").is_file()
    assert (output_dir / "my-change-architecture-drift.json").is_file()
    assert (output_dir / "my-change-uiux-compliance.json").is_file()
    assert inspect_spec_compliance_artifact(temp_project_dir, output_dir)["status"] == "ready"
    assert inspect_architecture_drift_artifact(temp_project_dir, output_dir)["status"] == "ready"
    assert inspect_uiux_compliance_artifact(temp_project_dir, output_dir)["status"] == "ready"


def test_frontend_none_uiux_report_is_current_not_applicable_and_does_not_scan(
    temp_project_dir: Path,
) -> None:
    _activate_change(temp_project_dir)
    _write_config(temp_project_dir, frontend="none")
    output_dir = temp_project_dir / "output"
    _write(output_dir / "current-change-uiux.md", "# 使用体验\n\nCLI 输出保持清晰。\n")
    _write(output_dir / "historical-uiux.md", "# UIUX\n\nicon_library: material\n")
    for relative in (
        "frontend/src/page.tsx",
        "super-dev-website/src/page.tsx",
        "examples/demo/page.tsx",
    ):
        _write(temp_project_dir / relative, "export const color = '#ffffff';\n")
    generic_report = output_dir / "uiux-compliance.json"
    _write(generic_report, "uiux sentinel\n")

    report = run_uiux_compliance(temp_project_dir, output_dir)

    assert report.project_name == "current-change"
    assert report.score == 100
    assert report.files_scanned == 0
    assert report.violations == []
    assert generic_report.read_text(encoding="utf-8") == "uiux sentinel\n"
    assert inspect_uiux_compliance_artifact(temp_project_dir, output_dir)["status"] == "ready"
    dependencies = [item.replace("\\", "/") for item in report.evidence_identity["dependencies"]]
    assert dependencies == ["output/current-change-uiux.md"]


def test_frontend_project_uiux_compliance_still_scans_source(temp_project_dir: Path) -> None:
    _activate_change(temp_project_dir)
    _write_config(temp_project_dir, frontend="react")
    output_dir = temp_project_dir / "output"
    _write(output_dir / "current-change-uiux.md", "# UIUX\n\nicon_library: lucide\n")
    _write(
        temp_project_dir / "frontend" / "src" / "theme.css",
        ".button { color: #ffffff; }\n",
    )

    report = run_uiux_compliance(temp_project_dir, output_dir)

    assert report.project_name == "current-change"
    assert report.files_scanned == 1
    assert report.score < 100
    assert any(item.rule == "no_hardcoded_colors" for item in report.violations)
    assert not (output_dir / "uiux-compliance.json").exists()


def test_generic_egg_info_is_excluded_but_root_sources_still_match_and_fail(
    temp_project_dir: Path,
) -> None:
    _write_config(temp_project_dir, frontend="react")
    output_dir = temp_project_dir / "output"
    _write(
        output_dir / "demo-prd.md",
        "# PRD\n\n## Root handler\n\n1. Root handler must support account access.\n",
    )
    _write(
        output_dir / "demo-architecture.md",
        "# Architecture\n\n## Tech Stack\n\nFastAPI\n",
    )
    _write(output_dir / "demo-uiux.md", "# UIUX\n\nicon_library: lucide\n")
    _write(temp_project_dir / "requirements.txt", "fastapi==0.115.0\n")
    _write(
        temp_project_dir / "app.py",
        "import fastapi\n\ndef root_handler():\n    return 'account access'\n",
    )
    _write(
        temp_project_dir / "frontend" / "theme.css",
        ".button { color: #ffffff; }\n",
    )
    _write(
        temp_project_dir / "demo.egg-info" / "generated.py",
        "import forbidden_generated_dependency\n\ndef root_handler():\n    return True\n",
    )
    _write(
        temp_project_dir / "demo.egg-info" / "generated.tsx",
        "export const Generated = () => <button style={{color: '#ff0000'}}>x</button>;\n",
    )

    spec_report = run_spec_compliance(temp_project_dir, output_dir)
    architecture_report = run_architecture_drift(temp_project_dir, output_dir)
    uiux_report = run_uiux_compliance(temp_project_dir, output_dir)

    spec_dependencies = [
        item.replace("\\", "/") for item in spec_report.evidence_identity["dependencies"]
    ]
    architecture_dependencies = [
        item.replace("\\", "/") for item in architecture_report.evidence_identity["dependencies"]
    ]
    uiux_dependencies = [
        item.replace("\\", "/") for item in uiux_report.evidence_identity["dependencies"]
    ]
    assert not any("demo.egg-info" in item for item in spec_dependencies)
    assert not any("demo.egg-info" in item for item in architecture_dependencies)
    assert not any("demo.egg-info" in item for item in uiux_dependencies)
    assert any("app.py" in item.files for item in spec_report.matches)
    assert all(
        "demo.egg-info" not in matched_file
        for item in spec_report.matches
        for matched_file in item.files
    )
    assert uiux_report.files_scanned == 1
    assert any(
        item.rule == "no_hardcoded_colors"
        and item.file.replace("\\", "/").endswith("frontend/theme.css")
        for item in uiux_report.violations
    )
    assert all("demo.egg-info" not in item.file for item in uiux_report.violations)
