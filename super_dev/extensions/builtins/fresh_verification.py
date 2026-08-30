"""内置 pytest 完成前验证的结果解析器。"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as DefusedElementTree

from ..models import (
    CommandExecution,
    ExtensionStatus,
    PytestSummary,
    VerificationAdvisory,
)

_SUMMARY_HEADER_RE = re.compile(r"^=+\s+short test summary info\s+=+$")
_MAX_JUNIT_BYTES = 64 * 1024 * 1024


class JUnitSummaryError(ValueError):
    pass


def _digest(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_non_negative_int(raw: str | None, *, field: str) -> int:
    value = str(raw or "").strip()
    if not value.isdigit():
        raise JUnitSummaryError(f"JUnit {field} 必须是非负整数")
    return int(value)


def _parse_non_negative_float(raw: str | None, *, field: str) -> float:
    value = str(raw or "").strip()
    try:
        parsed = float(value)
    except ValueError as exc:
        raise JUnitSummaryError(f"JUnit {field} 必须是非负数") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise JUnitSummaryError(f"JUnit {field} 必须是有限非负数")
    return parsed


def _suite_counts(element: Any) -> tuple[int, int, int, int, float]:
    tests = _parse_non_negative_int(element.get("tests"), field="tests")
    failures = _parse_non_negative_int(element.get("failures"), field="failures")
    errors = _parse_non_negative_int(element.get("errors"), field="errors")
    skipped = _parse_non_negative_int(element.get("skipped"), field="skipped")
    duration = _parse_non_negative_float(element.get("time"), field="time")
    if failures + errors + skipped > tests:
        raise JUnitSummaryError("JUnit 失败、错误和跳过总数不能大于测试总数")
    return tests, failures, errors, skipped, duration


def parse_junit_summary(path: Path | str) -> PytestSummary:
    junit_path = Path(path)
    try:
        payload = junit_path.read_bytes()
    except OSError as exc:
        raise JUnitSummaryError(f"无法读取 JUnit: {exc}") from exc
    if not payload:
        raise JUnitSummaryError("JUnit 文件为空")
    if len(payload) > _MAX_JUNIT_BYTES:
        raise JUnitSummaryError("JUnit 文件超过 64 MiB 安全上限")
    try:
        root = DefusedElementTree.fromstring(
            payload,
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )
    except Exception as exc:
        raise JUnitSummaryError(f"JUnit XML 损坏或包含禁止结构: {exc}") from exc

    root_name = _local_name(root.tag)
    if root_name == "testsuite":
        suites = [root]
    elif root_name == "testsuites":
        suites = [item for item in list(root) if _local_name(item.tag) == "testsuite"]
        if not suites:
            raise JUnitSummaryError("JUnit testsuites 没有直接 testsuite 子节点")
    else:
        raise JUnitSummaryError("JUnit 根节点必须是 testsuite 或 testsuites")

    totals = [0, 0, 0, 0]
    duration = 0.0
    for suite in suites:
        suite_tests, suite_failures, suite_errors, suite_skipped, suite_duration = _suite_counts(
            suite
        )
        totals[0] += suite_tests
        totals[1] += suite_failures
        totals[2] += suite_errors
        totals[3] += suite_skipped
        duration += suite_duration
    tests, failures, errors, skipped = totals
    executed = tests - skipped
    return PytestSummary(
        tests=tests,
        failures=failures,
        errors=errors,
        skipped=skipped,
        executed=executed,
        duration_seconds=duration,
        junit_digest=_digest(payload),
    )


def extract_non_strict_xpass(
    stdout: str,
    *,
    run_id: str,
    output_digest: str,
) -> tuple[VerificationAdvisory, ...]:
    in_summary = False
    occurrences = 0
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if _SUMMARY_HEADER_RE.fullmatch(line):
            in_summary = True
            occurrences = 0
            continue
        if not in_summary:
            continue
        if line.startswith("="):
            break
        if line.startswith("XPASS "):
            occurrences += 1
    if occurrences == 0:
        return ()
    return (
        VerificationAdvisory(
            run_id=run_id,
            code="NON_STRICT_XPASS",
            occurrences=occurrences,
            output_digest=output_digest,
        ),
    )


def run(context: dict[str, Any]) -> dict[str, Any]:
    execution = context.get("execution")
    if not isinstance(execution, CommandExecution):
        raise ValueError("完成前验证缺少结构化命令结果")
    run_id = str(context.get("run_id", "")).strip()
    if not run_id:
        raise ValueError("完成前验证缺少运行编号")
    junit_path = Path(str(context.get("junit_path", "")))

    if execution.status == ExtensionStatus.BLOCKED:
        return {
            "status": ExtensionStatus.BLOCKED,
            "summary": None,
            "advisories": (),
            "blocking_findings": [execution.error or "pytest 执行被阻断"],
        }

    try:
        summary = parse_junit_summary(junit_path)
    except JUnitSummaryError as exc:
        return {
            "status": ExtensionStatus.BLOCKED,
            "summary": None,
            "advisories": (),
            "blocking_findings": [str(exc)],
        }

    advisories = extract_non_strict_xpass(
        execution.stdout,
        run_id=run_id,
        output_digest=execution.stdout_digest,
    )
    exit_code = execution.exit_code
    findings: list[str] = []
    if exit_code == 0:
        if summary.failures or summary.errors:
            status = ExtensionStatus.BLOCKED
            findings.append("pytest 退出码为 0，但 JUnit 仍包含失败或错误")
        elif summary.tests == 0:
            status = ExtensionStatus.BLOCKED
            findings.append("没有收集到测试，不能支持完成声明")
        elif summary.executed == 0:
            status = ExtensionStatus.BLOCKED
            findings.append("所有测试均被跳过或标记为预期失败")
        else:
            status = ExtensionStatus.PASS
    elif exit_code == 1:
        status = ExtensionStatus.FAIL
        findings.append("pytest 已执行，但存在失败")
    elif exit_code in {2, 3, 4, 5, 6}:
        status = ExtensionStatus.BLOCKED
        findings.append(f"pytest 退出码 {exit_code} 不能支持完成声明")
    else:
        status = ExtensionStatus.BLOCKED
        findings.append(f"pytest 返回未知退出码: {exit_code}")
    return {
        "status": status,
        "summary": summary,
        "advisories": advisories,
        "blocking_findings": findings,
    }
