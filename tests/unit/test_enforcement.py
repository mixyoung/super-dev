"""Unit tests for the enforcement module."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from super_dev.utils.shell import resolve_bash


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project directory."""
    (tmp_path / ".super-dev").mkdir()
    return tmp_path


class TestHostHooksConfigurator:
    def test_generate_hooks_config_claude_code(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        cfg = HostHooksConfigurator(project_dir)
        hooks = cfg.generate_hooks_config(host="claude-code")

        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks
        assert len(hooks["PreToolUse"]) >= 3
        matchers = {entry["matcher"] for entry in hooks["PreToolUse"]}
        assert "Write|Edit" in matchers
        assert cfg.SENSITIVE_READ_MATCHER in matchers
        assert "Bash" in matchers
        assert hooks["PostToolUse"][0]["matcher"] == "Bash"
        sensitive_entry = next(
            entry for entry in hooks["PreToolUse"] if entry["matcher"] == cfg.SENSITIVE_READ_MATCHER
        )
        bash_entry = next(entry for entry in hooks["PreToolUse"] if entry["matcher"] == "Bash")
        assert ".ssh" in sensitive_entry["hooks"][0]["command"]
        assert ".env" in sensitive_entry["hooks"][0]["command"]
        assert "id_rsa" in bash_entry["hooks"][0]["command"]

    def test_generate_hooks_config_unknown_host(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        cfg = HostHooksConfigurator(project_dir)
        assert cfg.generate_hooks_config(host="unknown") == {}

    def test_install_hooks_creates_settings_file(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        cfg = HostHooksConfigurator(project_dir)
        path = cfg.install_hooks(host="claude-code")

        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "hooks" in data
        assert "PreToolUse" in data["hooks"]
        assert "PostToolUse" in data["hooks"]

    def test_install_hooks_merges_existing(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        claude_dir = project_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.local.json"
        existing = {
            "permissions": {"allow": ["Read"]},
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo hi"}]}
                ]
            },
        }
        settings_path.write_text(json.dumps(existing), encoding="utf-8")

        cfg = HostHooksConfigurator(project_dir)
        cfg.install_hooks(host="claude-code")

        data = json.loads(settings_path.read_text(encoding="utf-8"))
        # Original permission preserved
        assert data["permissions"]["allow"] == ["Read"]
        # Original Bash hook preserved + PreToolUse guards merged in
        matchers = {e["matcher"] for e in data["hooks"]["PreToolUse"]}
        assert "Bash" in matchers
        assert "Write|Edit" in matchers
        assert HostHooksConfigurator.SENSITIVE_READ_MATCHER in matchers
        bash_entry = next(e for e in data["hooks"]["PreToolUse"] if e["matcher"] == "Bash")
        assert len(bash_entry["hooks"]) == 2

    def test_install_hooks_does_not_duplicate(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        cfg = HostHooksConfigurator(project_dir)
        cfg.install_hooks(host="claude-code")
        cfg.install_hooks(host="claude-code")

        settings_path = project_dir / ".claude" / "settings.local.json"
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        pre_matchers = [e["matcher"] for e in data["hooks"]["PreToolUse"]]
        assert pre_matchers.count("Write|Edit") == 1
        assert pre_matchers.count(HostHooksConfigurator.SENSITIVE_READ_MATCHER) == 1
        assert pre_matchers.count("Bash") == 1

    def test_install_hooks_unsupported_host_raises(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        cfg = HostHooksConfigurator(project_dir)
        with pytest.raises(ValueError, match="Unsupported host"):
            cfg.install_hooks(host="unknown")

    def test_sensitive_read_guard_blocks_secret_paths_but_not_examples(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        cfg = HostHooksConfigurator(project_dir)
        pre_tool_use = cfg.generate_hooks_config(host="claude-code")["PreToolUse"]
        guard = next(
            entry for entry in pre_tool_use if entry["matcher"] == cfg.SENSITIVE_READ_MATCHER
        )["hooks"][0]["command"]

        blocked = subprocess.run(
            [resolve_bash(), "-lc", guard],
            input=json.dumps({"tool_input": {"file_path": "~/.ssh/id_rsa"}}),
            text=True,
            capture_output=True,
        )
        allowed = subprocess.run(
            [resolve_bash(), "-lc", guard],
            input=json.dumps({"tool_input": {"file_path": "./.env.example"}}),
            text=True,
            capture_output=True,
        )

        assert blocked.returncode == 0
        assert '"decision": "block"' in blocked.stdout
        assert ".ssh/id_rsa" in blocked.stdout
        assert allowed.returncode == 0
        assert allowed.stdout.strip() == "{}"

    def test_bash_guard_blocks_secret_file_reads_and_env_prints(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        cfg = HostHooksConfigurator(project_dir)
        pre_tool_use = cfg.generate_hooks_config(host="claude-code")["PreToolUse"]
        bash_guard = next(entry for entry in pre_tool_use if entry["matcher"] == "Bash")["hooks"][
            0
        ]["command"]

        file_read = subprocess.run(
            [resolve_bash(), "-lc", bash_guard],
            input=json.dumps({"tool_input": {"command": "cat ~/.ssh/id_rsa"}}),
            text=True,
            capture_output=True,
        )
        file_transform = subprocess.run(
            [resolve_bash(), "-lc", bash_guard],
            input=json.dumps({"tool_input": {"command": "base64 ~/.aws/credentials"}}),
            text=True,
            capture_output=True,
        )
        env_print = subprocess.run(
            [resolve_bash(), "-lc", bash_guard],
            input=json.dumps({"tool_input": {"command": "echo $OPENAI_API_KEY"}}),
            text=True,
            capture_output=True,
        )
        env_script = subprocess.run(
            [resolve_bash(), "-lc", bash_guard],
            input=json.dumps(
                {
                    "tool_input": {
                        "command": "python3 -c 'import os; print(os.environ.get(\"AWS_SECRET_ACCESS_KEY\"))'"
                    }
                }
            ),
            text=True,
            capture_output=True,
        )
        safe = subprocess.run(
            [resolve_bash(), "-lc", bash_guard],
            input=json.dumps({"tool_input": {"command": "cat README.md"}}),
            text=True,
            capture_output=True,
        )

        assert file_read.returncode == 0
        assert ".ssh" in file_read.stdout
        assert file_transform.returncode == 0
        assert ".aws" in file_transform.stdout.lower()
        assert env_print.returncode == 0
        assert "openai_api_key" in env_print.stdout.lower()
        assert env_script.returncode == 0
        assert "aws_secret_access_key" in env_script.stdout.lower()
        assert safe.returncode == 0
        assert safe.stdout.strip() == "{}"

    def test_get_status(self, project_dir: Path):
        from super_dev.enforcement.host_hooks import HostHooksConfigurator

        cfg = HostHooksConfigurator(project_dir)

        # Before install
        status = cfg.get_status()
        assert status["hooks_installed"] is False
        assert status["validation_script_exists"] is False
        assert status["pre_code_checklist_exists"] is False

        # After install
        cfg.install_hooks()
        cfg.generate_validation_script()
        cfg.generate_pre_code_checklist()

        status = cfg.get_status()
        assert status["hooks_installed"] is True
        assert status["validation_script_exists"] is True
        assert status["pre_code_checklist_exists"] is True


class TestValidationScriptGenerator:
    def test_generate_creates_executable_script(self, project_dir: Path):
        from super_dev.enforcement.validation import ValidationScriptGenerator

        gen = ValidationScriptGenerator()
        path = gen.generate(project_dir)

        assert path.exists()
        assert path.name == "validate-superdev.sh"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("#!/bin/bash")
        assert "ERRORS=0" in content
        assert "emoji" in content.lower()

    def test_generate_nextjs_check(self, project_dir: Path):
        from super_dev.enforcement.validation import ValidationScriptGenerator

        gen = ValidationScriptGenerator()
        path = gen.generate(project_dir, frontend="next")
        content = path.read_text(encoding="utf-8")
        assert "App Router" in content or "route" in content.lower()

    def test_generate_eslint_rules(self, project_dir: Path):
        from super_dev.enforcement.validation import ValidationScriptGenerator

        gen = ValidationScriptGenerator()
        path = gen.generate_eslint_rules(project_dir, icon_library="lucide")

        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "rules" in data
        assert "lucide-react" in json.dumps(data)

    def test_icon_package_mapping(self):
        from super_dev.enforcement.validation import ValidationScriptGenerator

        gen = ValidationScriptGenerator()
        assert gen._icon_package("lucide") == "lucide-react"
        assert gen._icon_package("heroicons") == "@heroicons/react"
        assert gen._icon_package("unknown") == "lucide-react"


class TestPreCodeGate:
    def test_generate_checklist(self, project_dir: Path):
        from super_dev.enforcement.pre_code_gate import PreCodeGate

        gate = PreCodeGate()
        path = gate.generate_checklist(project_dir, frontend="next", backend="node")

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Pre-Code Checklist" in content
        assert "App Router" in content
        assert "node" in content

    def test_check_completion_not_exists(self, project_dir: Path):
        from super_dev.enforcement.pre_code_gate import PreCodeGate

        gate = PreCodeGate()
        ok, items = gate.check_completion(project_dir)
        assert ok is False
        assert "does not exist" in items[0]

    def test_check_completion_incomplete(self, project_dir: Path):
        from super_dev.enforcement.pre_code_gate import PreCodeGate

        gate = PreCodeGate()
        gate.generate_checklist(project_dir)

        ok, items = gate.check_completion(project_dir)
        assert ok is False
        assert len(items) > 0

    def test_check_completion_all_done(self, project_dir: Path):
        from super_dev.enforcement.pre_code_gate import PreCodeGate

        gate = PreCodeGate()
        path = gate.generate_checklist(project_dir)

        # Mark all items as complete
        content = path.read_text(encoding="utf-8")
        content = content.replace("- [ ]", "- [x]")
        path.write_text(content, encoding="utf-8")

        ok, items = gate.check_completion(project_dir)
        assert ok is True
        assert items == []


class TestEnforcementBridge:
    def test_auto_install_enforcement(self, project_dir: Path):
        from super_dev._enforcement_bridge import auto_install_enforcement

        files = auto_install_enforcement(project_dir)
        # Only hooks config is installed during auto-setup;
        # validation script and checklist are generated on demand.
        assert len(files) == 1
        names = {f.name for f in files}
        assert "settings.local.json" in names
