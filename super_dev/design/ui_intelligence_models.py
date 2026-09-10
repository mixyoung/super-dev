"""Data models returned by the UI intelligence advisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LibraryRecommendation:
    """组件生态推荐"""

    name: str
    category: str
    rationale: str
    strengths: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "rationale": self.rationale,
            "strengths": list(self.strengths),
            "notes": list(self.notes),
        }


@dataclass
class DesignReference:
    """设计参考锚点"""

    slug: str
    name: str
    rationale: str
    source: str
    direction: str
    signals: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)
    fit_product_types: tuple[str, ...] = ()
    fit_industries: tuple[str, ...] = ()
    fit_styles: tuple[str, ...] = ()
    fit_frontends: tuple[str, ...] = ()
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "rationale": self.rationale,
            "source": self.source,
            "direction": self.direction,
            "signals": list(self.signals),
            "cautions": list(self.cautions),
        }


@dataclass
class FrameworkPlaybook:
    """跨平台框架深优化 playbook"""

    framework: str
    focus: str
    rationale: str
    source_basis: list[str] = field(default_factory=list)
    implementation_modules: list[str] = field(default_factory=list)
    platform_constraints: list[str] = field(default_factory=list)
    execution_guardrails: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    native_capabilities: list[str] = field(default_factory=list)
    validation_surfaces: list[str] = field(default_factory=list)
    delivery_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework,
            "focus": self.focus,
            "rationale": self.rationale,
            "source_basis": list(self.source_basis),
            "implementation_modules": list(self.implementation_modules),
            "platform_constraints": list(self.platform_constraints),
            "execution_guardrails": list(self.execution_guardrails),
            "anti_patterns": list(self.anti_patterns),
            "native_capabilities": list(self.native_capabilities),
            "validation_surfaces": list(self.validation_surfaces),
            "delivery_evidence": list(self.delivery_evidence),
        }
