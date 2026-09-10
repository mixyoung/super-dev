#!/usr/bin/env python3
"""
宿主兼容性门禁检查工具

用途：
1. 校验 output/*-host-compatibility.json 的总体评分是否达到阈值
2. 可附加校验 ready host 最低数量
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_MIN_SCORE = 80.0
DEFAULT_MIN_READY_HOSTS = 1


def _latest_report(project_dir: Path) -> Path:
    output_dir = project_dir / "output"
    candidates = sorted(
        output_dir.glob("*-host-compatibility.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"未找到兼容性报告: {output_dir}/*-host-compatibility.json")
    return candidates[0]


def _load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"兼容性报告解析失败: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise ValueError(f"兼容性报告格式非法（非 JSON object）: {path}")
    return data


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _check_report(
    path: Path,
    min_score: float,
    min_ready_hosts: int,
    profile_targets: list[str] | None = None,
) -> tuple[bool, str]:
    data = _load_report(path)
    compatibility = data.get("compatibility", {})
    if not isinstance(compatibility, dict):
        return False, "缺少 compatibility 字段"

    if profile_targets:
        host_map = compatibility.get("hosts", {})
        if not isinstance(host_map, dict):
            return False, "兼容性报告缺少 hosts 详情，无法按宿主画像校验"
        selected = [item for item in profile_targets if item in host_map]
        if not selected:
            return False, f"宿主画像未命中报告 hosts: {', '.join(profile_targets)}"

        score_values: list[float] = []
        ready_hosts = 0
        for target in selected:
            item = host_map.get(target, {})
            if not isinstance(item, dict):
                score_values.append(0.0)
                continue
            score_values.append(_to_float(item.get("score"), 0.0))
            if bool(item.get("ready", False)):
                ready_hosts += 1
        overall_score = (sum(score_values) / len(score_values)) if score_values else 0.0
        total_hosts = len(selected)
        label = f"profile={','.join(selected)}"
    else:
        overall_score = _to_float(compatibility.get("overall_score"), 0.0)
        ready_hosts = _to_int(compatibility.get("ready_hosts"), 0)
        total_hosts = _to_int(compatibility.get("total_hosts"), 0)
        label = "scope=overall"

    if overall_score < min_score:
        return (
            False,
            f"兼容性评分未达标: {label} overall_score={overall_score:.2f} < min_score={min_score:.2f}",
        )
    if ready_hosts < min_ready_hosts:
        return (
            False,
            f"ready host 数不足: {label} ready_hosts={ready_hosts} < min_ready_hosts={min_ready_hosts}",
        )
    return (
        True,
        f"兼容性门禁通过: {label}, overall_score={overall_score:.2f}, ready_hosts={ready_hosts}, total_hosts={total_hosts}",
    )


def _load_threshold_defaults(project_dir: Path) -> tuple[float, int, list[str], bool]:
    config_file = project_dir / "super-dev.yaml"
    if not config_file.exists():
        return DEFAULT_MIN_SCORE, DEFAULT_MIN_READY_HOSTS, [], False

    try:
        raw = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_MIN_SCORE, DEFAULT_MIN_READY_HOSTS, [], False
    if not isinstance(raw, dict):
        return DEFAULT_MIN_SCORE, DEFAULT_MIN_READY_HOSTS, [], False

    min_score = _to_float(raw.get("host_compatibility_min_score"), DEFAULT_MIN_SCORE)
    min_ready_hosts = _to_int(
        raw.get("host_compatibility_min_ready_hosts"),
        DEFAULT_MIN_READY_HOSTS,
    )
    raw_targets = raw.get("host_profile_targets", [])
    profile_targets = (
        [str(item).strip() for item in raw_targets if isinstance(item, str) and str(item).strip()]
        if isinstance(raw_targets, list)
        else []
    )
    enforce_selected = bool(raw.get("host_profile_enforce_selected", False))
    return (
        max(0.0, min(100.0, min_score)),
        max(0, min_ready_hosts),
        profile_targets,
        enforce_selected,
    )


def main() -> int:
    # Match the UTF-8 report protocol independently of the caller's locale.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Super Dev 宿主兼容性门禁检查")
    parser.add_argument(
        "--project-dir",
        default=".",
        help="项目根目录（默认当前目录）",
    )
    parser.add_argument(
        "--report",
        default="",
        help="指定兼容性报告路径；不传则自动查找 output/ 最新报告",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="最低兼容性评分阈值（默认读取 super-dev.yaml，否则 80）",
    )
    parser.add_argument(
        "--min-ready-hosts",
        type=int,
        default=None,
        help="最低 ready host 数（默认读取 super-dev.yaml，否则 1）",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    default_score, default_ready_hosts, profile_targets, enforce_selected = (
        _load_threshold_defaults(project_dir)
    )
    min_score = default_score if args.min_score is None else float(args.min_score)
    min_ready_hosts = (
        default_ready_hosts if args.min_ready_hosts is None else max(0, int(args.min_ready_hosts))
    )

    try:
        report_path = Path(args.report).resolve() if args.report else _latest_report(project_dir)
        ok, message = _check_report(
            report_path,
            min_score=min_score,
            min_ready_hosts=min_ready_hosts,
            profile_targets=profile_targets if enforce_selected else [],
        )
    except Exception as exc:
        print(f"[FAIL] 宿主兼容性门禁检查失败: {exc}")
        return 1

    if not ok:
        print(f"[FAIL] {message} ({report_path})")
        return 1

    print(f"[PASS] {message}: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
