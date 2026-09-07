"""Fork update orchestration and a fresh-process, scope-limited post-install check."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.version import Version

from . import __version__
from .release_channel import REPOSITORY, latest_release, verified_wheel
from .update_hosts import refresh_hosts, snapshot_hosts


@dataclass(frozen=True)
class Installation:
    method: str
    python: Path
    installer: str

    def command(self, wheel: Path) -> list[str]:
        if self.method == "uv":
            base = str(getattr(sys, "_base_executable", self.python))
            return [self.installer, "tool", "install", "--force", "--python", base, str(wheel)]
        if self.method == "uv-pip":
            return [
                self.installer,
                "pip",
                "install",
                "--python",
                str(self.python),
                "--upgrade",
                str(wheel),
            ]
        return [str(self.python), "-m", "pip", "install", "--upgrade", str(wheel)]


def detect_installation(preferred: str) -> Installation:
    distribution = metadata.distribution("super-dev")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    if "dir_info" in direct or not Path(__file__).resolve().is_relative_to(
        Path(sys.prefix).resolve()
    ):
        raise ValueError("源码/editable 安装：请在源码仓库审查后更新并重新安装；本命令不操作 Git")
    location = Path(str(distribution.locate_file(""))).resolve()
    if not location.is_relative_to(Path(sys.prefix).resolve()) or sys.prefix == sys.base_prefix:
        raise ValueError("不是可确认归属的隔离安装；请在原 pip/uv 环境手工安装本 fork wheel")
    urls = distribution.metadata.get_all("Project-URL") or []
    if not any(url.endswith(f"https://github.com/{REPOSITORY}") for url in urls):
        raise ValueError("当前安装来源不能确认为本 fork，未自动覆盖")
    python = Path(sys.executable).absolute()  # resolve() would lose POSIX venv symlinks
    uv = shutil.which("uv")
    receipt = Path(sys.prefix) / "uv-receipt.toml"
    if receipt.exists():
        if not uv:
            raise ValueError("这是 uv tool 安装，但未找到 uv")
        root = subprocess.run(
            [uv, "tool", "dir"], check=True, capture_output=True, text=True, timeout=15
        ).stdout.strip()
        if Path(sys.prefix).resolve() != (Path(root) / "super-dev").resolve():
            raise ValueError("uv tool 目录与当前解释器不一致")
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        config = tomllib.loads(receipt.read_text(encoding="utf-8"))
        requirements = config.get("tool", {}).get("requirements", [])
        if len(requirements) != 1 or requirements[0].get("name") != "super-dev":
            raise ValueError("uv tool 含自定义依赖约束，请在原环境手工更新，避免丢失配置")
        method = "uv"
    else:
        installed_by = (distribution.read_text("INSTALLER") or "").strip()
        if installed_by not in {"pip", "uv"}:
            raise ValueError("安装器归属未知，未猜测 pip 或 uv")
        method = "uv-pip" if installed_by == "uv" and uv else "pip"
    if preferred != "auto" and preferred != ("uv" if method.startswith("uv") else "pip"):
        raise ValueError(
            f"指定方式 {preferred} 与现有安装 {method} 不一致；不会切换或新建另一套安装"
        )
    return Installation(method, python, uv or "")


def _wheel_hashes(wheel: Path) -> dict[str, str]:
    with zipfile.ZipFile(wheel) as archive:
        return {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith("super_dev/") and not name.endswith("/")
        }


def post_install(
    project: Path, payload: dict[str, Any], *, expected: str, include_user: bool
) -> dict[str, Any]:
    distribution = metadata.distribution("super-dev")
    if __version__ != expected or distribution.version != expected:
        raise ValueError("新进程的模块/安装版本与目标版本不一致，未刷新宿主")
    hashes = payload["files"]
    if not hashes or "super_dev/__init__.py" not in hashes:
        raise ValueError("缺少制品文件校验范围")
    for relative, digest in hashes.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.parts[0] != "super_dev":
            raise ValueError("制品校验路径无效")
        installed = Path(str(distribution.locate_file(relative)))
        if hashlib.sha256(installed.read_bytes()).hexdigest() != digest:
            raise ValueError(f"新安装文件或静态资源不一致：{relative}")
    from .cli import SuperDevCLI

    SuperDevCLI()  # Import and construct from the new runtime; no workflow/doctor writes.
    report = refresh_hosts(project, payload["hosts"], include_user=include_user)
    return {"version": __version__, "files_verified": len(hashes), **report}


def run_update(args: Any, console: Any) -> int:
    try:
        release = latest_release()
        console.print(f"当前版本：{__version__}")
        console.print(f"本 fork 最新版本：{release.version}（GitHub {REPOSITORY}）")
        if args.check:
            console.print(
                "发现新版本，可执行 super-dev update。"
                if Version(release.version) > Version(__version__)
                else "当前版本不低于本 fork 最新发布；不会降级。"
            )
            return 0
        if Version(release.version) < Version(__version__):
            console.print("当前为更高的开发版本，未安装、未迁移、未降级。")
            return 0
        installation = detect_installation(args.method)
        project = Path.cwd().resolve()
        include_user = bool(getattr(args, "include_user", False))
        hosts = snapshot_hosts(project, include_user=include_user)
        console.print(
            f"升级方式：{installation.method}；宿主刷新范围：{'项目和已存在的用户级面' if include_user else '仅当前项目'}"
        )
        with tempfile.TemporaryDirectory(prefix="super-dev-update-") as temporary:
            wheel = verified_wheel(release, Path(temporary))
            payload = {"hosts": hosts, "files": _wheel_hashes(wheel)}
            if release.version != __version__:
                completed = subprocess.run(installation.command(wheel), check=False, timeout=600)
                if completed.returncode:
                    console.print(
                        "升级失败：安装器未成功，未刷新宿主。若 Windows 文件被占用，请关闭相关会话后重试；未强杀进程。"
                    )
                    console.print(
                        f"恢复：先用原解释器检查 super-dev --version；必要时从 https://github.com/{REPOSITORY}/releases 重新安装已校验 wheel。"
                    )
                    return 1
            command = [
                str(installation.python),
                "-I",
                "-m",
                "super_dev.update_runtime",
                "--post-install",
                "--expected",
                release.version,
                "--project",
                str(project),
            ]
            if include_user:
                command.append("--include-user")
            result = subprocess.run(
                command,
                input=json.dumps(payload),
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
                timeout=120,
                cwd=temporary,
            )
            if result.returncode:
                console.print("安装阶段已结束，但新进程验证或宿主刷新受阻，不能宣称升级全部完成。")
                console.print((result.stdout or result.stderr)[-4000:], markup=False)
                return 2
            report = json.loads(result.stdout)
            console.print(
                f"升级完成：新进程确认版本 {report['version']}，校验 {report['files_verified']} 个包文件。"
            )
            console.print(
                f"已刷新 {len(report['changed'])} 个已有宿主文件；未安装新宿主、未修改项目阶段。"
            )
            if report.get("backup_dir"):
                console.print(f"原托管内容备份：{report['backup_dir']}", markup=False)
            return 0
    except (
        OSError,
        ValueError,
        RuntimeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
        metadata.PackageNotFoundError,
    ) as exc:
        console.print(f"更新受阻：{exc}。没有回退原版 PyPI。", markup=False)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal fresh-process update verification")
    parser.add_argument("--post-install", action="store_true", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--include-user", action="store_true")
    args = parser.parse_args()
    try:
        report = post_install(
            args.project.resolve(),
            json.load(sys.stdin),
            expected=args.expected,
            include_user=args.include_user,
        )
        # -I ignores PYTHONIOENCODING; ASCII JSON also works on legacy Windows code pages.
        print(json.dumps(report, ensure_ascii=True))
        return 2 if report["issues"] else 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
