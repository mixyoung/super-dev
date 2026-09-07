"""Real isolated pip upgrade, using a synthetic old version, never a public release.

Network is used only to install dependencies in a disposable venv. Release transport
is supplied by local wheel/checksum bytes; the production resolver/verifier still runs.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from super_dev import __version__
from super_dev.user_directories import UserDirectoryContext
from tests.support.user_surface_snapshot import (
    capture_user_surfaces,
    collect_user_surface_paths,
    diff_surface_snapshots,
    has_surface_changes,
)

DRIVER = r"""
import hashlib, json, os, sys
if sys.platform == "win32":
    # Reproduce an English Windows pipe even on a Chinese developer machine.
    sys.stdout.reconfigure(encoding="cp1252")
    sys.stderr.reconfigure(encoding="cp1252")
from pathlib import Path
from super_dev import __version__
from super_dev import release_channel, update_runtime
from super_dev.cli import SuperDevCLI
from super_dev.skills.skill_template import SkillTemplate
assert __version__ == "0.0.1", __version__
wheel, project, target_version = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
project.mkdir()
os.chdir(project)
skill = project / ".agents/skills/super-dev/SKILL.md"
skill.parent.mkdir(parents=True)
skill.write_text(SkillTemplate.for_builtin("super-dev", "codex-cli").render("codex-cli"), encoding="utf-8")
original = skill.read_bytes()
data = wheel.read_bytes()
base = "https://github.com/mixyoung/super-dev/releases"
release = {"draft":False, "prerelease":False, "tag_name":"v"+target_version,
           "html_url":base+"/tag/v"+target_version,
           "assets":[{"name":name, "browser_download_url":base+"/download/v"+target_version+"/"+name}
                     for name in (wheel.name, "SHA256SUMS.txt")]}
def transport(url, **kwargs):
    if url == release_channel.LATEST_URL:
        return json.dumps(release).encode()
    if url.endswith("SHA256SUMS.txt"):
        return (hashlib.sha256(data).hexdigest()+"  "+wheel.name+"\n").encode()
    assert url.endswith(wheel.name)
    return data
release_channel._get = transport
code = SuperDevCLI().run(["update", "--method", "pip"])
assert code == 0, code
assert update_runtime.__version__ == "0.0.1"  # old process really remains loaded
assert skill.read_bytes() != original
assert "0.0.1" not in skill.read_text(encoding="utf-8")
assert list((project / ".super-dev/update-backups").glob("*/*.json"))
print("ISOLATED_OLD_PROCESS_NEW_INSTALL_PASS")
"""


def _old_fixture(wheel: Path, directory: Path) -> Path:
    old_info = "super_dev-0.0.1.dist-info"
    contents = {}
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith("/RECORD"):
                continue
            data = archive.read(name)
            renamed = name.replace(f"super_dev-{__version__}.dist-info", old_info)
            if name in {
                "super_dev/__init__.py",
                "super_dev/skills/skill_template.py",
            } or name.endswith("/METADATA"):
                data = data.replace(__version__.encode(), b"0.0.1")
            contents[renamed] = data
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, data in contents.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow((name, "sha256=" + digest, len(data)))
    writer.writerow((old_info + "/RECORD", "", ""))
    contents[old_info + "/RECORD"] = record.getvalue().encode()
    target = directory / "super_dev-0.0.1-py3-none-any.whl"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[2]
    output = args.output_dir.resolve()
    if output == project or not output.is_relative_to(project):
        raise ValueError("证据目录必须是仓库内专用子目录")
    output.mkdir(parents=True, exist_ok=True)
    wheels = list(args.wheel_dir.resolve().glob("super_dev-*.whl"))
    if len(wheels) != 1:
        raise ValueError("需要唯一的当前代码 wheel")
    surfaces = collect_user_surface_paths(project, UserDirectoryContext.current())
    before = capture_user_surfaces(surfaces)
    error = ""
    try:
        with tempfile.TemporaryDirectory(prefix="super-dev-upgrade-acceptance-") as temporary:
            root = Path(temporary)
            env = UserDirectoryContext.from_home(root / "home").environment(os.environ)
            env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            old = _old_fixture(wheels[0], root)
            python = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            commands = [
                [sys.executable, "-m", "venv", str(root / "venv")],
                [str(python), "-m", "pip", "install", str(old)],
                [
                    str(python),
                    "-I",
                    "-c",
                    DRIVER,
                    str(wheels[0]),
                    str(root / "project"),
                    __version__,
                ],
            ]
            for index, command in enumerate(commands):
                result = subprocess.run(
                    command,
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=600,
                    check=False,
                )
                (output / f"step-{index}.log").write_text(
                    result.stdout + result.stderr, encoding="utf-8"
                )
                if result.returncode:
                    raise RuntimeError(f"步骤 {index} 失败，退出码 {result.returncode}")
    except Exception as exc:
        error = str(exc)
    diff = diff_surface_snapshots(before, capture_user_surfaces(surfaces))
    passed = not error and not has_surface_changes(diff)
    (output / "result.json").write_text(
        json.dumps(
            {
                "passed": passed,
                "error": error,
                "surface_diff": diff,
                "old_version": "0.0.1 (synthetic fixture, not a released version)",
                "new_version": __version__,
                "wheel_sha256": hashlib.sha256(wheels[0].read_bytes()).hexdigest(),
                "python": sys.version,
                "platform": sys.platform,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"隔离升级验收：{'通过（PASS）' if passed else '失败（FAIL）'}；{error or '真实用户目录变化为 0'}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
