"""Protect existing output shapes while tightening release type contracts."""

import json
from pathlib import Path

import pytest

from super_dev.change_ledger import EvidenceReference
from super_dev.creators.frontend_builder import FrontendScaffoldBuilder
from super_dev.creators.nextjs_scaffold import NextjsScaffoldGenerator


def test_evidence_reference_keeps_list_payload_and_round_trip() -> None:
    item = EvidenceReference(
        "fixture", "owner", "2026-09-06", "scope", invalidation_triggers=["code"]
    )
    payload = item.to_dict()
    assert payload["invalidation_triggers"] == ["code"]
    assert EvidenceReference.from_dict(json.loads(json.dumps(payload))) == item


@pytest.mark.parametrize(
    "frontend,method,kind",
    [
        ("next", "", "nextjs-app-router"),
        ("vue", "generate_vue3_project", "vue3-vite"),
        ("angular", "generate_angular_project", "angular"),
        ("svelte", "generate_svelte_project", "sveltekit"),
        ("react", "generate_react_vite_project", "react-vite"),
        ("expo", "generate_expo_project", "expo-managed"),
        ("flutter", "generate_flutter_project", "flutter"),
        ("uni-app", "generate_miniapp_project", "uni-app"),
        ("tauri", "generate_desktop_shell_project", "tauri-desktop-shell"),
        ("ionic", "generate_hybrid_shell_project", "ionic-hybrid-shell"),
    ],
)
def test_framework_dispatch_preserves_path_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frontend: str, method: str, kind: str
) -> None:
    builder = FrontendScaffoldBuilder(tmp_path, "example", "description", frontend)
    target = tmp_path / "generated.txt"
    if frontend == "next":
        monkeypatch.setattr(NextjsScaffoldGenerator, "generate", lambda *args, **kwargs: [target])
    else:
        monkeypatch.setattr(builder, method, lambda *args, **kwargs: {"file": str(target)})
    result = builder._generate_framework_scaffold({})
    assert result is not None
    assert result["kind"] == kind
    assert result["files"] == [str(target)]
