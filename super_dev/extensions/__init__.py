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
)

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
]
