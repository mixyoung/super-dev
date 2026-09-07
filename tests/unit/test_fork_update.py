from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

from super_dev import release_channel as channel
from super_dev import update_runtime as updater
from super_dev import version_check
from super_dev.skills.skill_template import SkillTemplate
from super_dev.update_hosts import refresh_hosts, snapshot_hosts


def _release(version="9.0.0"):
    base = f"https://github.com/{channel.REPOSITORY}/releases"
    wheel = f"super_dev-{version}-py3-none-any.whl"
    return {
        "tag_name": f"v{version}",
        "draft": False,
        "prerelease": False,
        "html_url": f"{base}/tag/v{version}",
        "assets": [
            {"name": name, "browser_download_url": f"{base}/download/v{version}/{name}"}
            for name in (wheel, "SHA256SUMS.txt")
        ],
    }


def _wheel(*, version="9.0.0", requires=">=3.10"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "super_dev-9.0.0.dist-info/METADATA",
            f"Name: super-dev\nVersion: {version}\nRequires-Python: {requires}\n",
        )
        archive.writestr("super_dev/__init__.py", "__version__ = '9.0.0'\n")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "mutation", ["owner", "draft", "prerelease", "tag", "missing", "duplicate", "asset-url"]
)
def test_release_channel_rejects_ambiguous_or_foreign_releases(monkeypatch, mutation):
    data = _release()
    if mutation == "owner":
        data["html_url"] = data["html_url"].replace("mixyoung", "upstream")
    elif mutation in {"draft", "prerelease"}:
        data[mutation] = True
    elif mutation == "tag":
        data["tag_name"] = "v9.0.0rc1"
    elif mutation == "missing":
        data["assets"].pop()
    elif mutation == "duplicate":
        data["assets"].append(data["assets"][0])
    else:
        data["assets"][0]["browser_download_url"] = "https://example.com/a.whl"
    monkeypatch.setattr(channel, "_get", lambda *a, **k: json.dumps(data).encode())
    with pytest.raises(ValueError):
        channel.latest_release()


@pytest.mark.parametrize("problem", [None, "hash", "duplicate", "version", "python"])
def test_wheel_verified_before_any_install(tmp_path, monkeypatch, problem):
    content = _wheel(
        version="8.0.0" if problem == "version" else "9.0.0",
        requires=">=99" if problem == "python" else ">=3.10",
    )
    digest = "0" * 64 if problem == "hash" else hashlib.sha256(content).hexdigest()
    checksum = f"{digest}  super_dev-9.0.0-py3-none-any.whl\n"
    if problem == "duplicate":
        checksum *= 2

    def get(url, **kwargs):
        if url == channel.LATEST_URL:
            return json.dumps(_release()).encode()
        return checksum.encode() if url.endswith("SHA256SUMS.txt") else content

    monkeypatch.setattr(channel, "_get", get)
    release = channel.latest_release()
    if problem:
        with pytest.raises(ValueError):
            channel.verified_wheel(release, tmp_path)
        assert list(tmp_path.glob("*.whl")) == []
    else:
        assert channel.verified_wheel(release, tmp_path).read_bytes() == content


def test_redirect_is_checked_before_contacting_another_host(monkeypatch):
    calls = []

    class Response:
        status_code = 302
        headers = {"Location": "http://127.0.0.1/private"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def get(url, **kwargs):
        calls.append(url)
        return Response()

    monkeypatch.setattr(channel.requests, "get", get)
    with pytest.raises(ValueError):
        channel._get(channel.LATEST_URL, limit=100, timeout=1)
    assert calls == [channel.LATEST_URL]


def test_old_cache_is_not_used_for_fork(monkeypatch):
    cache = version_check._cache_file()
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"version": "99.0.0", "ts": version_check.time.time()}))
    assert version_check._read_cache() is None
    monkeypatch.setattr(
        version_check, "latest_release", lambda **k: SimpleNamespace(version="9.0.0")
    )
    assert "9.0.0" in version_check.check_for_update()
    assert json.loads(cache.read_text())["source"] == channel.CHANNEL


def test_check_is_read_only_and_shares_fork_source(monkeypatch):
    monkeypatch.setattr(updater, "latest_release", lambda: SimpleNamespace(version="9.0.0"))
    monkeypatch.setattr(
        updater, "detect_installation", lambda *a: pytest.fail("check must not install")
    )
    stream = io.StringIO()
    assert updater.run_update(SimpleNamespace(check=True), Console(file=stream)) == 0
    assert "mixyoung/super-dev" in stream.getvalue()


def test_editable_install_is_never_overwritten(monkeypatch):
    monkeypatch.setattr(
        updater.metadata,
        "distribution",
        lambda _: SimpleNamespace(read_text=lambda _: '{"dir_info":{"editable":true}}'),
    )
    with pytest.raises(ValueError, match="editable"):
        updater.detect_installation("auto")


@pytest.mark.parametrize("method", ["pip", "uv", "uv-pip"])
def test_installer_is_bound_to_verified_local_wheel(tmp_path, method):
    installation = updater.Installation(method, tmp_path / "python", "/tools/uv")
    wheel = tmp_path / "super_dev-9.0.0-py3-none-any.whl"
    command = installation.command(wheel)
    assert command[-1] == str(wheel)
    assert "super-dev" not in command  # no unpinned PyPI package request
    if method == "pip":
        assert command[:3] == [str(installation.python), "-m", "pip"]


@pytest.mark.parametrize("failure", [None, "install", "post"])
def test_new_interpreter_owns_post_install_and_partial_failure(tmp_path, monkeypatch, failure):
    monkeypatch.chdir(tmp_path)
    wheel = tmp_path / "super_dev-9.0.0-py3-none-any.whl"
    wheel.write_bytes(_wheel())
    python = tmp_path / "installed" / "python"
    monkeypatch.setattr(updater, "latest_release", lambda: SimpleNamespace(version="9.0.0"))
    monkeypatch.setattr(updater, "verified_wheel", lambda *a: wheel)
    monkeypatch.setattr(
        updater, "detect_installation", lambda _: updater.Installation("pip", python, "")
    )
    monkeypatch.setattr(updater, "snapshot_hosts", lambda *a, **k: {"entries": [], "issues": []})
    calls = []

    def execute(command, **kwargs):
        calls.append((command, kwargs))
        if len(calls) == 1:
            return SimpleNamespace(returncode=1 if failure == "install" else 0)
        return SimpleNamespace(
            returncode=2 if failure == "post" else 0,
            stdout=json.dumps(
                {"version": "9.0.0", "files_verified": 1, "changed": [], "issues": []}
            ),
            stderr="",
        )

    monkeypatch.setattr(updater.subprocess, "run", execute)
    stream = io.StringIO()
    result = updater.run_update(
        SimpleNamespace(check=False, method="auto", include_user=False), Console(file=stream)
    )
    assert result == {None: 0, "install": 1, "post": 2}[failure]
    if failure == "install":
        assert len(calls) == 1
    else:
        assert calls[1][0][:4] == [str(python), "-I", "-m", "super_dev.update_runtime"]
        assert "--include-user" not in calls[1][0]
        assert "files" in json.loads(calls[1][1]["input"])
    if failure:
        assert "升级完成：" not in stream.getvalue()


def _skill(project):
    path = project / ".agents/skills/super-dev/SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        SkillTemplate.for_builtin("super-dev", "codex-cli").render("codex-cli"), encoding="utf-8"
    )
    return path


def test_host_refresh_preserves_edits_and_defaults_to_project(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    path = _skill(project)
    user_path = _skill(Path.home())
    original_user = user_path.read_bytes()
    snapshot = snapshot_hosts(project, include_user=False)
    assert snapshot["entries"]
    assert all(Path(item["path"]).is_relative_to(project) for item in snapshot["entries"])
    path.write_text("user changed during install", encoding="utf-8")
    report = refresh_hosts(project, snapshot, include_user=False)
    assert report["issues"]
    assert path.read_text() == "user changed during install"
    assert user_path.read_bytes() == original_user


def test_host_refresh_uses_new_template_and_keeps_backup(tmp_path, monkeypatch):
    path = _skill(tmp_path)
    original = path.read_bytes().decode("utf-8")
    snapshot = snapshot_hosts(tmp_path, include_user=False)
    render = SkillTemplate.render
    monkeypatch.setattr(
        SkillTemplate, "render", lambda self, host: render(self, host) + "\nnew template\n"
    )
    report = refresh_hosts(tmp_path, snapshot, include_user=False)
    assert not report["issues"]
    assert path.read_text(encoding="utf-8").endswith("new template\n")
    backups = list(Path(report["backup_dir"]).glob("*.json"))
    assert any(json.loads(item.read_text(encoding="utf-8"))["old"] == original for item in backups)


def test_post_install_rejects_old_runtime_before_host_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(
        updater.metadata, "distribution", lambda _: SimpleNamespace(version="0.0.0")
    )
    monkeypatch.setattr(
        updater, "refresh_hosts", lambda *a, **k: pytest.fail("old runtime must not refresh")
    )
    with pytest.raises(ValueError, match="版本"):
        updater.post_install(tmp_path, {}, expected="9.0.0", include_user=False)


@pytest.mark.parametrize("kind", ["pip", "uv", "uv-pip", "unknown", "system", "wrong-source"])
def test_installation_detection_uses_receipts_not_path_substrings(tmp_path, monkeypatch, kind):
    root = tmp_path / "tools"
    prefix = root / "super-dev"
    prefix.mkdir(parents=True)
    monkeypatch.setattr(sys, "prefix", str(prefix))
    monkeypatch.setattr(
        sys, "base_prefix", str(prefix) if kind == "system" else str(tmp_path / "base")
    )
    monkeypatch.setattr(sys, "executable", str(prefix / "python"))
    monkeypatch.setattr(updater, "__file__", str(prefix / "lib/super_dev/update_runtime.py"))
    source = "another/fork" if kind == "wrong-source" else channel.REPOSITORY
    installer = "" if kind == "unknown" else "uv" if kind.startswith("uv") else "pip"
    distribution = SimpleNamespace(
        locate_file=lambda _: str(prefix / "lib/site-packages"),
        read_text=lambda name: installer if name == "INSTALLER" else "{}",
        metadata=SimpleNamespace(get_all=lambda _: [f"Repository, https://github.com/{source}"]),
    )
    monkeypatch.setattr(updater.metadata, "distribution", lambda _: distribution)
    monkeypatch.setattr(updater.shutil, "which", lambda _: str(tmp_path / "uv"))
    monkeypatch.setattr(
        updater.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=str(root))
    )
    if kind == "uv":
        (prefix / "uv-receipt.toml").write_text('[tool]\nrequirements = [{name = "super-dev"}]\n')
    if kind in {"unknown", "system", "wrong-source"}:
        with pytest.raises(ValueError):
            updater.detect_installation("auto")
    else:
        assert updater.detect_installation("auto").method == kind
        mismatch = "pip" if kind.startswith("uv") else "uv"
        with pytest.raises(ValueError, match="不一致"):
            updater.detect_installation(mismatch)


def test_shared_host_file_preserves_surrounding_user_rules(tmp_path, monkeypatch):
    from super_dev.integrations.manager import IntegrationManager

    manager = IntegrationManager(project_dir=tmp_path)
    path = tmp_path / "AGENTS.md"
    markers = manager._managed_agents_markers("codex-cli")
    content = manager._append_flow_contract(
        content=manager._build_file_content("codex-cli", "AGENTS.md"), relative="AGENTS.md"
    )
    path.write_text(
        f"User policy before\n{markers[0]}\n{content.rstrip()}\n{markers[1]}\nUser policy after\n",
        encoding="utf-8",
    )
    snapshot = snapshot_hosts(tmp_path, include_user=False)
    build = IntegrationManager._build_file_content
    monkeypatch.setattr(
        IntegrationManager,
        "_build_file_content",
        lambda self, target, relative: build(self, target, relative) + "\nUpdated rule\n",
    )
    report = refresh_hosts(tmp_path, snapshot, include_user=False)
    assert not report["issues"]
    actual = path.read_text(encoding="utf-8")
    assert actual.startswith("User policy before\n")
    assert actual.endswith("User policy after\n")
    assert "Updated rule" in actual


def test_preexisting_modified_skill_is_not_claimed(tmp_path):
    path = _skill(tmp_path)
    path.write_text(path.read_text(encoding="utf-8") + "\nmy customization\n", encoding="utf-8")
    snapshot = snapshot_hosts(tmp_path, include_user=False)
    assert not snapshot["entries"]
    assert snapshot["issues"]


def test_user_skill_requires_explicit_scope(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    user_path = _skill(Path.home())
    assert snapshot_hosts(project, include_user=False)["entries"] == []
    opted_in = snapshot_hosts(project, include_user=True)
    assert any(item["path"] == str(user_path) for item in opted_in["entries"])


@pytest.mark.parametrize(
    "command,expected",
    [
        (
            'uv tool install --force --from "git+https://github.com/mixyoung/super-dev.git@v2.5.0" super-dev',
            True,
        ),
        ("uv tool install super-dev", True),
        (
            'uv tool install --force --from "git+https://github.com/another/super-dev.git@v2.5.0" super-dev',
            False,
        ),
        (
            'uv tool install --force --from "git+https://github.com/mixyoung/super-dev.git@main" super-dev',
            False,
        ),
    ],
)
def test_release_gate_accepts_pinned_fork_install_without_weakening_old_checks(
    tmp_path, command, expected
):
    from super_dev.release_readiness import ReleaseReadinessEvaluator

    (tmp_path / "install.sh").touch()
    (tmp_path / "pyproject.toml").write_text(
        '[project.scripts]\nsuper-dev = "super_dev.cli:main"\n'
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(command + "\nsuper-dev update\n")
    (tmp_path / "docs/INSTALL_OPTIONS.md").write_text(command + "\n")
    evaluator = ReleaseReadinessEvaluator(tmp_path)
    assert evaluator._check_packaging_entrypoints().passed is expected
    (tmp_path / "install.sh").unlink()
    assert not evaluator._check_packaging_entrypoints().passed
