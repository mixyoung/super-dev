from __future__ import annotations

from pathlib import Path

import yaml

from super_dev.cli import SuperDevCLI


def test_extension_validate_and_disabled_probe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "frontend": "next",
                "backend": "node",
                "extensions": {"enabled": False, "allowed_builtin_methods": []},
            }
        ),
        encoding="utf-8",
    )
    service_manifest = (
        Path(__file__).parents[2]
        / "super_dev"
        / "extensions"
        / "builtins"
        / "contract_probe.yaml"
    )
    cli = SuperDevCLI()

    assert cli.run(["extension", "validate", str(service_manifest), "--json"]) == 0
    assert cli.run(["extension", "inspect", str(service_manifest), "--json"]) == 0
    assert cli.run(["extension", "verify-source", str(service_manifest), "--json"]) == 0
    assert cli.run(["extension", "probe-contract", "--json"]) == 3


def test_enabled_probe_and_history_are_wired(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "super-dev.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "cli-test",
                "frontend": "next",
                "backend": "node",
                "extensions": {
                    "enabled": True,
                    "allowed_builtin_methods": ["contract-probe"],
                },
            }
        ),
        encoding="utf-8",
    )
    cli = SuperDevCLI()

    assert cli.run(["extension", "probe-contract", "--json"]) == 0
    assert cli.run(["extension", "history", "--limit", "10", "--json"]) == 0
    assert (tmp_path / ".super-dev" / "extensions" / "history.jsonl").exists()
