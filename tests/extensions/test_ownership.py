from __future__ import annotations

from super_dev.extensions.manifest import parse_manifest
from super_dev.extensions.models import Capability, ExtensionStatus
from super_dev.extensions.ownership import evaluate_ownership

from .helpers import manifest_payload


def test_requested_capability_requires_trusted_core_capability() -> None:
    manifest = parse_manifest(manifest_payload())

    missing = evaluate_ownership(manifest, trusted_capabilities=set())
    granted = evaluate_ownership(
        manifest, trusted_capabilities={Capability.WRITE_EVIDENCE}
    )

    assert missing.status == ExtensionStatus.NOT_APPLICABLE
    assert granted.status == ExtensionStatus.PASS


def test_lifecycle_and_high_risk_authority_are_blocked() -> None:
    payload = manifest_payload()
    payload["ownership"]["lifecycle"] = True
    payload["authority"]["push"] = True
    manifest = parse_manifest(payload)

    decision = evaluate_ownership(
        manifest, trusted_capabilities={Capability.WRITE_EVIDENCE}
    )

    assert decision.status == ExtensionStatus.BLOCKED
    assert any("ownership.lifecycle" in item for item in decision.findings)
    assert any("authority.push" in item for item in decision.findings)
