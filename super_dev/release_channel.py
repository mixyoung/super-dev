"""One fixed, fail-closed GitHub release channel for this fork."""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from packaging.specifiers import SpecifierSet
from packaging.version import Version

REPOSITORY = "mixyoung/super-dev"
CHANNEL = f"github:{REPOSITORY}:stable"
LATEST_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
_DOWNLOAD_HOSTS = {
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}


@dataclass(frozen=True)
class ForkRelease:
    version: str
    tag: str
    wheel_name: str
    wheel_url: str
    checksums_url: str


def _get(url: str, *, limit: int, timeout: int) -> bytes:
    """Bounded HTTPS reads; validate every redirect, not only the final response."""
    for _ in range(6):
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in _DOWNLOAD_HOSTS | {"api.github.com"}
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
        ):
            raise ValueError("发布源跳转到了不受信任的地址")
        with requests.get(
            url,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "super-dev-update"},
        ) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                url = urljoin(url, response.headers["Location"])
                continue
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(64 * 1024):
                content.extend(chunk)
                if len(content) > limit:
                    raise ValueError("发布数据超过允许大小")
            return bytes(content)
    raise ValueError("发布源重定向次数过多")


def latest_release(*, timeout: int = 10) -> ForkRelease:
    data = json.loads(_get(LATEST_URL, limit=1024 * 1024, timeout=timeout))
    if not isinstance(data, dict) or not isinstance(data.get("assets"), list):
        raise ValueError("发布元数据结构无效")
    tag = data.get("tag_name", "")
    if (
        data.get("draft") is not False
        or data.get("prerelease") is not False
        or not isinstance(tag, str)
        or not re.fullmatch(r"v\d+\.\d+\.\d+", tag)
    ):
        raise ValueError("只接受本 fork 的正式版本标签 vX.Y.Z")
    base = f"https://github.com/{REPOSITORY}/releases"
    if data.get("html_url") != f"{base}/tag/{tag}":
        raise ValueError("发布仓库与固定 fork 来源不一致")
    version = tag[1:]
    wheel = f"super_dev-{version}-py3-none-any.whl"
    selected = {}
    for asset in data.get("assets", []):
        if not isinstance(asset, dict):
            raise ValueError("发布制品元数据无效")
        name = asset.get("name")
        if name not in {wheel, "SHA256SUMS.txt"}:
            continue
        expected = f"{base}/download/{tag}/{name}"
        if name in selected or asset.get("browser_download_url") != expected:
            raise ValueError("发布制品重复或来源不一致")
        selected[name] = expected
    if set(selected) != {wheel, "SHA256SUMS.txt"}:
        raise ValueError("发布缺少 wheel 或 SHA256SUMS.txt，不回退其他源")
    return ForkRelease(version, tag, wheel, selected[wheel], selected["SHA256SUMS.txt"])


def verified_wheel(release: ForkRelease, directory: Path) -> Path:
    checksums = _get(release.checksums_url, limit=64 * 1024, timeout=15).decode("utf-8")
    matches = []
    for line in checksums.splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{64})\s+\*?([^\s]+)", line)
        if match and match[2] == release.wheel_name:
            matches.append(match[1].lower())
    if len(matches) != 1:
        raise ValueError("校验清单没有唯一的目标 wheel 摘要")
    content = _get(release.wheel_url, limit=32 * 1024 * 1024, timeout=30)
    if hashlib.sha256(content).hexdigest() != matches[0]:
        raise ValueError("wheel SHA256 不一致，未启动安装")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        name = f"super_dev-{release.version}.dist-info/METADATA"
        if archive.namelist().count(name) != 1 or archive.getinfo(name).file_size > 1024 * 1024:
            raise ValueError("wheel 元数据缺失、重复或过大")
        metadata = BytesParser().parsebytes(archive.read(name))
        if (
            metadata["Name"] not in {"super-dev", "super_dev"}
            or metadata["Version"] != release.version
        ):
            raise ValueError("wheel 包名或版本与 Release 标签不一致")
        requirement = metadata["Requires-Python"]
        current = Version(".".join(map(str, sys.version_info[:3])))
        if not requirement or current not in SpecifierSet(requirement):
            raise ValueError(f"新版不支持当前 Python；要求：{requirement or '未声明'}")
    target = directory / release.wheel_name
    target.write_bytes(content)
    return target
