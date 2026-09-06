"""
宿主侧 hooks 配置器 — 为 AI coding host 生成和安装执行 hooks。

支持的宿主:
- claude-code: 通过 .claude/settings.local.json 的 hooks 配置
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class HostHooksConfigurator:
    """为 AI coding host 生成和安装执行 hooks。"""

    SUPPORTED_HOSTS = ("claude-code",)
    SENSITIVE_READ_MATCHER = (
        "Read|Grep|Glob|LS|mcp__acp__Read|mcp__acp__Grep|mcp__acp__Glob|mcp__acp__LS"
    )

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def generate_hooks_config(self, host: str = "claude-code") -> dict[str, Any]:
        """生成宿主 hooks 配置。

        For Claude Code, this generates settings.json hooks:
        - PreToolUse for Write/Edit: validate no emoji, correct imports
        - PostToolUse for Bash: remind architecture conformance
        """
        if host == "claude-code":
            return self._claude_code_hooks()
        return {}

    def install_hooks(self, host: str = "claude-code") -> Path:
        """安装 hooks 到宿主配置文件。

        For Claude Code:
        - Reads existing .claude/settings.local.json
        - Merges Super Dev hooks into the hooks section
        - Does NOT overwrite user's existing hooks

        Returns:
            Path to the updated settings file.
        """
        if host == "claude-code":
            return self._install_claude_code_hooks()
        raise ValueError(f"Unsupported host: {host}")

    def generate_validation_script(self) -> Path:
        """生成 scripts/validate-superdev.sh 验证脚本。

        Delegates to ValidationScriptGenerator for the actual content.

        Returns:
            Path to the generated script.
        """
        from .validation import ValidationScriptGenerator

        generator = ValidationScriptGenerator()
        return generator.generate(self.project_dir)

    def generate_pre_code_checklist(self, frontend: str = "", backend: str = "") -> Path:
        """生成 .super-dev/PRE_CODE_CHECKLIST.md。

        Delegates to PreCodeGate for the actual content.

        Returns:
            Path to the generated checklist.
        """
        from .pre_code_gate import PreCodeGate

        gate = PreCodeGate()
        return gate.generate_checklist(self.project_dir, frontend=frontend, backend=backend)

    def get_status(self, host: str = "claude-code") -> dict[str, Any]:
        """返回当前 enforcement 状态摘要。"""
        status: dict[str, Any] = {
            "host": host,
            "hooks_installed": False,
            "validation_script_exists": False,
            "pre_code_checklist_exists": False,
        }
        try:
            if host == "claude-code":
                settings_path = self.project_dir / ".claude" / "settings.local.json"
                if settings_path.exists():
                    data = json.loads(settings_path.read_text(encoding="utf-8"))
                    hooks = data.get("hooks", {})
                    status["hooks_installed"] = bool(hooks.get("PreToolUse"))
            status["validation_script_exists"] = (
                self.project_dir / "scripts" / "validate-superdev.sh"
            ).exists()
            status["pre_code_checklist_exists"] = (
                self.project_dir / ".super-dev" / "PRE_CODE_CHECKLIST.md"
            ).exists()
        except Exception:
            pass
        return status

    # ------------------------------------------------------------------
    # Claude Code hooks
    # ------------------------------------------------------------------

    def _claude_code_hooks(self) -> dict[str, Any]:
        """Generate hooks config dict for Claude Code settings.local.json."""
        emoji_check_cmd = (
            'python3 -c "'
            "import sys,re,json; "
            "c=sys.stdin.read(); d=json.loads(c); "
            "ti=d.get('tool_input',{}); "
            "p=ti.get('file_path',''); "
            "ext=p.rsplit('.',1)[-1] if '.' in p else ''; "
            "content=ti.get('content','') or ti.get('new_string','') or ''; "
            "found=re.findall("
            "r'[\\u2600-\\u27BF\\U0001F300-\\U0001FAFF]', content) "
            "if ext in ('tsx','ts','jsx','js','vue','svelte') else []; "
            "unique=list(dict.fromkeys(found))[:5]; "
            "print(json.dumps("
            "{'decision':'block',"
            "'reason':'Super Dev: emoji ' + ' '.join(unique) + "
            "' found in .' + ext + ' file — use icon library instead'}"
            ' if unique else {}))"'
        )

        bash_remind_cmd = (
            'python3 -c "'
            "import sys,json; d=json.loads(sys.stdin.read()); "
            "cmd=d.get('tool_input',{}).get('command',''); "
            "print(json.dumps("
            "{'notify':'Super Dev: confirm output matches architecture docs'}"
            " if 'npm run' in cmd or 'pytest' in cmd else {}))\""
        )

        secret_read_guard_cmd = """python3 -c "$(cat <<'PY'
import fnmatch
import json
import os
import sys

data = json.loads(sys.stdin.read())
tool_input = data.get("tool_input", {})
if not isinstance(tool_input, dict):
    tool_input = {}

values: list[str] = []
for key in ("file_path", "path", "directory", "cwd", "pattern", "glob"):
    value = tool_input.get(key)
    if value:
        values.append(str(value))

for key in ("paths", "file_paths"):
    value = tool_input.get(key)
    if isinstance(value, list):
        values.extend(str(item) for item in value if item)

home = os.path.expanduser("~").replace("\\\\", "/").rstrip("/")
safe_suffixes = (".example", ".sample", ".template", ".dist", ".md")
sensitive_rules = (
    f"{home}/.ssh/*",
    f"{home}/.aws/*",
    f"{home}/.kube/*",
    f"{home}/.gnupg/*",
    f"{home}/.docker/*",
    f"{home}/.config/gcloud/*",
    f"{home}/.config/gh/*",
    f"{home}/.config/sops/*",
    f"{home}/.npmrc",
    f"{home}/.pypirc",
    f"{home}/.netrc",
    f"{home}/.git-credentials",
    f"{home}/.codex/auth.json",
    f"{home}/.claude.json",
    "*/.env",
    "*/.env.*",
    "*/.envrc",
    "*/secrets/*",
    "*/credentials/*",
    "*/id_rsa",
    "*/id_dsa",
    "*/id_ecdsa",
    "*/id_ed25519",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.key",
    "*/auth.json",
    "*/credentials.json",
)
config_like_secret_dirs = ("/.aws/", "/.kube/", "/.docker/", "/.config/gcloud/", "/.config/sops/")

matched: list[str] = []
for raw in values:
    candidate = os.path.expanduser(str(raw)).replace("\\\\", "/").rstrip("/")
    base = os.path.basename(candidate).lower()
    if not candidate or candidate.lower().endswith(safe_suffixes):
        continue
    if any(fnmatch.fnmatch(candidate, rule) for rule in sensitive_rules):
        matched.append(candidate)
        continue
    if base in {"credentials", "config", "config.json"} and any(
        segment in candidate.lower() for segment in config_like_secret_dirs
    ):
        matched.append(candidate)

matched = list(dict.fromkeys(matched))[:3]
if matched:
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": "Super Dev: blocked read/glob/grep on sensitive secret location(s): "
                + ", ".join(matched),
            }
        )
    )
else:
    print("{}")
PY
)" """

        bash_secret_guard_cmd = """python3 -c "$(cat <<'PY'
import json
import re
import sys

data = json.loads(sys.stdin.read())
tool_input = data.get("tool_input", {})
if not isinstance(tool_input, dict):
    tool_input = {}

command = str(tool_input.get("command", "") or "")
lower = command.lower().replace("\\\\", "/")
read_op = re.search(r"(^|[;&|()\\s])(cat|less|more|head|tail|grep|rg|sed|awk|find|ls|tree|bat|nl)\\b", lower)
transform_op = re.search(
    r"(^|[;&|()\\s])(cp|mv|tar|zip|unzip|gzip|base64|xxd|openssl|scp|rsync)\\b",
    lower,
)
env_secret_op = re.search(
    r"(^|[;&|()\\s])(printenv|env|echo|export|python|python3|node|ruby|perl|curl|wget|nc|ncat|ssh|scp|rsync)\\b",
    lower,
)
sensitive_markers = (
    "~/.ssh",
    "/.ssh/",
    "~/.aws",
    "/.aws/",
    "~/.kube",
    "/.kube/",
    "~/.docker",
    "/.docker/",
    "~/.gnupg",
    "/.gnupg/",
    "~/.config/gcloud",
    "/.config/gcloud/",
    "~/.config/sops",
    "/.config/sops/",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".git-credentials",
    ".codex/auth.json",
    ".claude.json",
    "/.env",
    " secrets/",
    " credentials/",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".pem",
    ".p12",
    ".pfx",
    ".key",
    "auth.json",
    "credentials.json",
)
env_secret_markers = (
    "openai_api_key",
    "anthropic_api_key",
    "gemini_api_key",
    "google_api_key",
    "google_application_credentials",
    "azure_openai_api_key",
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_session_token",
    "gh_token",
    "github_token",
    "gitlab_token",
    "slack_bot_token",
    "notion_api_key",
    "linear_api_key",
    "figma_api_key",
    "huggingface_token",
    "hf_token",
    "sentry_auth_token",
    "vercel_token",
    "cloudflare_api_token",
    "tavily_api_key",
)
matched = [marker for marker in sensitive_markers if marker in lower][:3]
if (read_op or transform_op) and matched:
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": "Super Dev: blocked bash command that accesses sensitive secret location(s): "
                + ", ".join(matched),
            }
        )
    )
else:
    env_matches = [marker for marker in env_secret_markers if marker in lower][:3]
    if env_secret_op and env_matches:
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": "Super Dev: blocked bash command that prints, exports, or transmits sensitive environment variable(s): "
                    + ", ".join(env_matches),
                }
            )
        )
    else:
        print("{}")
PY
)" """

        return {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": emoji_check_cmd,
                            "timeout": 5,
                        }
                    ],
                },
                {
                    "matcher": self.SENSITIVE_READ_MATCHER,
                    "hooks": [
                        {
                            "type": "command",
                            "command": secret_read_guard_cmd,
                            "shell": "bash",
                            "timeout": 5,
                        }
                    ],
                },
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": bash_secret_guard_cmd,
                            "shell": "bash",
                            "timeout": 5,
                        }
                    ],
                },
            ],
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": bash_remind_cmd,
                            "timeout": 5,
                        }
                    ],
                }
            ],
        }

    def _install_claude_code_hooks(self) -> Path:
        """Merge Super Dev hooks into .claude/settings.local.json."""
        claude_dir = self.project_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.local.json"

        existing: dict[str, Any] = {}
        if settings_path.exists():
            try:
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = {}

        new_hooks = self._claude_code_hooks()
        merged_hooks = self._merge_hooks(existing.get("hooks", {}), new_hooks)
        existing["hooks"] = merged_hooks

        settings_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return settings_path

    @staticmethod
    def _merge_hooks(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        """Merge incoming hooks into existing without duplicating.

        Strategy:
        - if matcher does not exist, append the full incoming entry
        - if matcher already exists, merge the nested hooks list and de-duplicate by command
        """
        merged = dict(existing)
        for phase, entries in incoming.items():
            if phase not in merged or not merged[phase]:
                merged[phase] = entries
                continue
            for entry in entries:
                matcher = entry.get("matcher") if isinstance(entry, dict) else None
                matched_entry = next(
                    (
                        existing_entry
                        for existing_entry in merged[phase]
                        if isinstance(existing_entry, dict)
                        and existing_entry.get("matcher") == matcher
                    ),
                    None,
                )
                if not matched_entry:
                    merged[phase].append(entry)
                    continue

                existing_hooks = matched_entry.get("hooks")
                incoming_hooks = entry.get("hooks") if isinstance(entry, dict) else None
                if not isinstance(existing_hooks, list) or not isinstance(incoming_hooks, list):
                    continue

                existing_commands = {
                    (
                        str(hook.get("type", "")),
                        str(hook.get("command", "")),
                    )
                    for hook in existing_hooks
                    if isinstance(hook, dict)
                }
                for hook in incoming_hooks:
                    if not isinstance(hook, dict):
                        continue
                    signature = (str(hook.get("type", "")), str(hook.get("command", "")))
                    if signature not in existing_commands:
                        existing_hooks.append(hook)
                        existing_commands.add(signature)
        return merged
