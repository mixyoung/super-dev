"""只验证扩展合同，不提供产品工程方法。"""

from __future__ import annotations

from typing import Any


def run(context: dict[str, Any]) -> dict[str, Any]:
    required = {"run_id", "candidate_digest", "canonical_stage"}
    missing = sorted(required - set(context))
    if missing:
        return {
            "passed": False,
            "blocking_findings": [f"合同探针缺少上下文字段: {missing}"],
            "advisory_findings": [],
        }
    return {
        "passed": True,
        "blocking_findings": [],
        "advisory_findings": ["合同探针只验证平台边界，没有接入真实外部方法。"],
    }
