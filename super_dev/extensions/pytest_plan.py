"""完成前验证的严格 pytest 计划配置。"""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from .models import PytestVerificationPlan

_PLAN_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FORBIDDEN_EXACT = {
    "-c",
    "-o",
    "-p",
    "--basetemp",
    "--cache-clear",
    "--co",
    "--collect-only",
    "--confcutdir",
    "--failed-first",
    "--ff",
    "--junit-xml",
    "--junitxml",
    "--last-failed",
    "--lf",
    "--override-ini",
    "--pyargs",
    "--rootdir",
    "--stepwise",
    "--stepwise-skip",
    "--sw",
    "--",
}
_FORBIDDEN_PREFIXES = (
    "--basetemp=",
    "--confcutdir=",
    "--junit-xml=",
    "--junitxml=",
    "--override-ini=",
    "--rootdir=",
    "-p",
    "-r",
)
_COMPACT_CORE_OVERRIDE_RE = re.compile(r"^-(?:c.+|o.+)$", re.IGNORECASE)
_NO_VALUE_SHORT_OPTIONS = frozenset("hlqsvVx")
_FORBIDDEN_VALUE_SHORT_OPTIONS = frozenset("copr")


class PytestPlanValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _bundles_forbidden_short_option(value: str) -> bool:
    if not value.startswith("-") or value.startswith("--") or len(value) <= 2:
        return False
    for character in value[1:]:
        if character.lower() in _FORBIDDEN_VALUE_SHORT_OPTIONS:
            return True
        if character not in _NO_VALUE_SHORT_OPTIONS:
            return False
    return False


def _path_escapes(value: str) -> bool:
    candidate = value.split("=", 1)[1] if "=" in value else value
    if not candidate or candidate.startswith("-"):
        return False
    normalized = candidate.replace("\\", "/")
    windows_path = PureWindowsPath(candidate)
    return (
        candidate.startswith("~")
        or PurePosixPath(normalized).is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in PurePosixPath(normalized).parts
    )


def parse_pytest_verification_plan(value: Any) -> PytestVerificationPlan:
    errors: list[str] = []
    if not isinstance(value, dict):
        raise PytestPlanValidationError(["extensions.fresh_verification 必须是对象"])

    required = {"profile", "plan_id", "args", "timeout_seconds"}
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    if missing:
        errors.append(f"extensions.fresh_verification 缺少字段: {missing}")
    if unknown:
        errors.append(f"extensions.fresh_verification 包含未知字段: {unknown}")

    profile = value.get("profile")
    if profile != "pytest-current-python":
        errors.append("extensions.fresh_verification.profile 仅支持 pytest-current-python")

    plan_id = str(value.get("plan_id", "")).strip()
    if not _PLAN_ID_RE.fullmatch(plan_id):
        errors.append("extensions.fresh_verification.plan_id 必须使用小写字母、数字和连字符")

    raw_args = value.get("args")
    args: tuple[str, ...] = ()
    if not isinstance(raw_args, list) or not raw_args:
        errors.append("extensions.fresh_verification.args 必须是非空字符串数组")
    else:
        normalized_args: list[str] = []
        if len(raw_args) > 64:
            errors.append("extensions.fresh_verification.args 最多允许 64 项")
        for index, raw in enumerate(raw_args):
            if not isinstance(raw, str) or not raw.strip():
                errors.append(f"extensions.fresh_verification.args[{index}] 必须是非空字符串")
                continue
            item = raw.strip()
            if len(item) > 512 or any(char in item for char in ("\x00", "\r", "\n")):
                errors.append(f"extensions.fresh_verification.args[{index}] 包含非法字符或过长")
                continue
            lowered = item.lower()
            if (
                lowered in _FORBIDDEN_EXACT
                or lowered.startswith(_FORBIDDEN_PREFIXES)
                or _COMPACT_CORE_OVERRIDE_RE.fullmatch(item)
                or _bundles_forbidden_short_option(item)
            ):
                errors.append(
                    f"extensions.fresh_verification.args[{index}] 不能覆盖 Core 固定参数: {item}"
                )
                continue
            if _path_escapes(item):
                errors.append(
                    f"extensions.fresh_verification.args[{index}] 不能使用绝对路径、~ 或父目录: {item}"
                )
                continue
            normalized_args.append(item)
        args = tuple(normalized_args)

    timeout = value.get("timeout_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not (1 <= timeout <= 3600):
        errors.append("extensions.fresh_verification.timeout_seconds 必须是 1-3600 的整数")
        timeout = 300

    if errors:
        raise PytestPlanValidationError(errors)
    return PytestVerificationPlan(
        profile="pytest-current-python",
        plan_id=plan_id,
        args=args,
        timeout_seconds=timeout,
    )
