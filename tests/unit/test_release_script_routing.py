"""Exercise release routing with fake tools, never publish or push anything."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def release_sandbox(tmp_path):
    git = shutil.which("git")
    bash = (
        (Path(git).parent.parent / "bin/bash.exe")
        if os.name == "nt" and git
        else Path(shutil.which("bash") or "/missing")
    )
    if not bash.is_file():
        pytest.skip("Git Bash / bash is required for isolated release script tests")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "release.sh").write_text(
        (ROOT / "scripts/release.sh").read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
    )
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    tools = {
        "git": 'echo "git $*" >> "$RELEASE_TEST_LOG"\nif [[ "$1" == branch ]]; then echo main; fi\nif [[ "$1" == rev-parse ]]; then exit 1; fi\nif [[ "$1" == rev-list ]]; then echo abc123def456; fi\n',
        "gh": 'echo "gh $*" >> "$RELEASE_TEST_LOG"\nif [[ "$1 $2" == "release view" ]]; then exit 1; fi\n',
        "python3": """echo "python3 $*" >> "$RELEASE_TEST_LOG"
if [[ "$*" == *"from super_dev import __version__"* ]]; then
  echo 9.9.9
elif [[ "$*" == "-m build" ]]; then
  mkdir -p dist
  printf wheel > dist/super_dev-9.9.9-py3-none-any.whl
  printf source > dist/super_dev-9.9.9.tar.gz
elif [[ "$*" == "-m twine check "* ]]; then
  exit 0
else
  exec "$RELEASE_TEST_PYTHON" "$@"
fi
""",
        "uv": """echo "uv $*" >> "$RELEASE_TEST_LOG"
if [[ "$1" == "build" ]]; then
  mkdir -p dist
  printf wheel > dist/super_dev-9.9.9-py3-none-any.whl
  printf source > dist/super_dev-9.9.9.tar.gz
fi
""",
        "uvx": 'echo "uvx $*" >> "$RELEASE_TEST_LOG"\n',
    }
    for name, body in tools.items():
        path = bin_dir / name
        path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8", newline="\n")
        path.chmod(0o755)
    for name in ("preflight.sh", "publish.sh"):
        path = scripts / name
        path.write_text(
            f'#!/usr/bin/env bash\necho "{name} $*" >> "$RELEASE_TEST_LOG"\n', newline="\n"
        )
        path.chmod(0o755)
    log = tmp_path / "calls.log"
    env = {
        **os.environ,
        "RELEASE_TEST_LOG": log.as_posix(),
        "RELEASE_TEST_PYTHON": Path(sys.executable).as_posix(),
    }

    def run(*args):
        result = subprocess.run(
            [
                str(bash),
                "-c",
                'export PATH="$PWD/fakebin:$PATH"; exec bash scripts/release.sh "$@"',
                "test-release",
                "--yes",
                *args,
            ],
            cwd=tmp_path,
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=30,
            check=False,
        )
        return result, log.read_text(encoding="utf-8") if log.exists() else ""

    return tmp_path, run


def test_default_prepares_github_artifacts_without_upload(release_sandbox):
    _, run = release_sandbox
    result, calls = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "preflight.sh --skip-package" in calls
    assert "python3 -m build" in calls
    assert "python3 -m twine check" in calls
    assert "publish.sh" not in calls
    assert "gh release" not in calls
    assert "git push" not in calls
    assert "mixyoung/super-dev" in result.stdout
    assert "no GitHub Release published" in result.stdout


def test_locked_project_builds_and_checks_with_uv(release_sandbox):
    root, run = release_sandbox
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    result, calls = run()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "uv build" in calls
    assert "uvx twine check" in calls
    assert "python3 -m build" not in calls
    assert "python3 -m twine check" not in calls


def test_explicit_github_release_is_bound_to_fork_with_checksums(release_sandbox):
    root, run = release_sandbox
    result, calls = run("--github-release")
    assert result.returncode == 0, result.stdout + result.stderr
    gh_calls = [line for line in calls.splitlines() if line.startswith("gh ")]
    assert gh_calls and all("--repo mixyoung/super-dev" in line for line in gh_calls)
    assert "dist/SHA256SUMS.txt" in gh_calls[-1]
    assert (root / "dist/SHA256SUMS.txt").read_text().count("\n") == 2
    assert "publish.sh" not in calls


def test_explicit_github_release_records_fact_for_active_workflow(release_sandbox):
    root, run = release_sandbox
    superdev = root / ".super-dev"
    superdev.mkdir()
    (superdev / "workflow-state.json").write_text(
        '{"work_item_id":"release-test","artifact_prefix":"release-test",'
        '"binding_status":"bound","active_change_id":"release-test"}',
        encoding="utf-8",
    )

    result, calls = run("--github-release")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "python3 -m super_dev.release_observation" in calls
    observation = root / "output" / "release" / "release-test-9.9.9-release-observation.json"
    assert observation.is_file()


def test_tag_without_github_release_does_not_record_released_fact(release_sandbox):
    root, run = release_sandbox
    result, calls = run("--push-tag")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "git tag -a v9.9.9" in calls
    assert "super_dev.release_observation" not in calls
    assert not (root / "output" / "release").exists()


def test_external_release_success_with_local_record_failure_stops_without_retry(
    release_sandbox,
):
    root, run = release_sandbox
    superdev = root / ".super-dev"
    superdev.mkdir()
    (superdev / "workflow-state.json").write_text("{}", encoding="utf-8")

    result, calls = run("--github-release")

    assert result.returncode == 1
    assert calls.count("gh release create") == 1
    assert "请先只读核对，不要直接重发" in result.stdout


def test_pypi_route_requires_explicit_selection(release_sandbox):
    _, run = release_sandbox
    result, calls = run("--repository", "testpypi")
    assert result.returncode == 0
    assert "publish.sh --repository testpypi" in calls


def test_unknown_repository_is_rejected_before_tool_actions(release_sandbox):
    _, run = release_sandbox
    result, calls = run("--repository", "unknown")
    assert result.returncode == 2
    assert not calls
