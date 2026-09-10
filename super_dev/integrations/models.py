"""Public data models used by host integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class IntegrationTarget:
    name: str
    description: str
    files: list[str]
    optional_files: list[str] = field(default_factory=list)


@dataclass
class HostAdapterProfile:
    host: str
    category: str
    adapter_mode: str
    host_model_provider: str
    certification_level: str
    certification_label: str
    certification_reason: str
    certification_evidence: list[str]
    official_docs_url: str
    docs_verified: bool
    primary_entry: str
    terminal_entry: str
    terminal_entry_scope: str
    integration_files: list[str]
    slash_command_file: str
    skill_dir: str
    detection_commands: list[str]
    detection_paths: list[str]
    notes: str
    usage_mode: str
    trigger_command: str
    entry_variants: list[dict[str, str]]
    trigger_context: str
    usage_location: str
    requires_restart_after_onboard: bool
    post_onboard_steps: list[str]
    usage_notes: list[str]
    smoke_test_prompt: str
    smoke_test_steps: list[str]
    smoke_success_signal: str
    competition_smoke_test_prompt: str
    competition_smoke_test_steps: list[str]
    competition_smoke_success_signal: str
    competition_smoke_suite: list[dict[str, object]]
    competition_acceptance_gates: list[str]
    competition_evidence_template: dict[str, object]
    precondition_status: str
    precondition_label: str
    precondition_guidance: list[str]
    precondition_signals: dict[str, bool]
    precondition_items: list[dict[str, object]]
    host_protocol_mode: str
    host_protocol_summary: str
    official_project_surfaces: list[str]
    official_user_surfaces: list[str]
    optional_project_surfaces: list[str]
    optional_user_surfaces: list[str]
    observed_compatibility_surfaces: list[str]
    official_docs_references: list[str]
    docs_check_status: str
    docs_check_summary: str
    capability_labels: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
