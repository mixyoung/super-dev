"""扩展能力和所有权裁决。"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Capability, ExtensionManifest, ExtensionStatus


@dataclass(frozen=True)
class OwnershipDecision:
    status: ExtensionStatus
    granted_capabilities: tuple[Capability, ...]
    findings: tuple[str, ...]

    @property
    def allowed(self) -> bool:
        return self.status == ExtensionStatus.PASS


def evaluate_ownership(
    manifest: ExtensionManifest,
    *,
    trusted_capabilities: set[Capability] | frozenset[Capability],
) -> OwnershipDecision:
    findings: list[str] = []
    ownership = manifest.ownership
    for field_name in (
        "lifecycle",
        "orchestration",
        "production_writer",
        "placement",
        "may_spawn_subworkers",
    ):
        if getattr(ownership, field_name):
            findings.append(f"扩展不允许取得所有权: ownership.{field_name}")
    for field_name in (
        "commit",
        "merge",
        "push",
        "pull_request",
        "deploy",
        "external_write",
        "global_install",
    ):
        if getattr(manifest.authority, field_name):
            findings.append(f"扩展不允许取得高风险权限: authority.{field_name}")
    if findings:
        return OwnershipDecision(
            status=ExtensionStatus.BLOCKED,
            granted_capabilities=(),
            findings=tuple(findings),
        )

    requested = set(manifest.required_capabilities)
    missing = sorted(item.value for item in requested - set(trusted_capabilities))
    if missing:
        return OwnershipDecision(
            status=ExtensionStatus.NOT_APPLICABLE,
            granted_capabilities=tuple(
                sorted(requested & set(trusted_capabilities), key=lambda item: item.value)
            ),
            findings=(f"当前宿主缺少可信能力: {missing}",),
        )
    return OwnershipDecision(
        status=ExtensionStatus.PASS,
        granted_capabilities=tuple(sorted(requested, key=lambda item: item.value)),
        findings=(),
    )
