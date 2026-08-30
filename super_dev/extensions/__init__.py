"""默认关闭的最小扩展内核。"""

from .models import (
    CandidateIdentity,
    Capability,
    CommandExecution,
    CommandSpec,
    ExtensionEvent,
    ExtensionEventType,
    ExtensionManifest,
    ExtensionResult,
    ExtensionStatus,
    PytestSummary,
    PytestVerificationPlan,
    VerificationAdvisory,
)
from .verification_metrics import VerificationMetricsSummary, summarize_verification_metrics

__all__ = [
    "Capability",
    "CandidateIdentity",
    "CommandExecution",
    "CommandSpec",
    "ExtensionEvent",
    "ExtensionEventType",
    "ExtensionManifest",
    "ExtensionResult",
    "ExtensionStatus",
    "PytestSummary",
    "PytestVerificationPlan",
    "VerificationAdvisory",
    "VerificationMetricsSummary",
    "summarize_verification_metrics",
]
