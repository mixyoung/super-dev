from __future__ import annotations

from typing import Any


def manifest_payload(
    *,
    digest: str = "sha256:" + "0" * 64,
    source_path: str = "builtins/probe.py",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "contract-probe",
        "version": "0.1.0",
        "kind": "builtin-test-adapter",
        "source": {
            "kind": "builtin",
            "path": source_path,
            "content_digest": digest,
        },
        "trigger": {"mode": "explicit", "allowed_stages": ["quality"]},
        "capabilities": {"required": ["write_evidence"]},
        "ownership": {
            "lifecycle": False,
            "orchestration": False,
            "production_writer": False,
            "placement": False,
            "may_spawn_subworkers": False,
        },
        "writes": {
            "allowed": [".super-dev/extensions/runs/**"],
            "forbidden": [
                ".git/**",
                ".super-dev/workflow-state.json",
                "$USER_SURFACES/**",
            ],
        },
        "authority": {
            "commit": False,
            "merge": False,
            "push": False,
            "pull_request": False,
            "deploy": False,
            "external_write": False,
            "global_install": False,
        },
        "execution": {
            "executor": "builtin-python",
            "entrypoint": "super_dev.extensions.builtins.contract_probe:run",
            "timeout_seconds": 30,
        },
        "result": {"schema": "extension-result-v1"},
    }
