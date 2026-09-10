"""Shared quality-gate result models."""

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class CheckStatus(Enum):
    """检查状态"""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class QualityCheck:
    """质量检查项"""

    name: str
    category: str  # documentation, security, performance, testing, code_quality
    description: str
    status: CheckStatus
    score: int  # 0-100
    weight: float = 1.0  # 权重，用于计算加权总分
    details: str = ""


class HostProfileMetrics(TypedDict):
    label: str
    overall_score: float
    ready_hosts: int
    total_hosts: int
    bounded_score: int
