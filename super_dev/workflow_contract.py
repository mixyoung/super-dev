from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .seeai_design_system import SEEAI_JUDGE_CHECKLIST, SEEAI_QUALITY_FLOOR

FlowVariant = Literal["standard", "seeai"]
StageKind = Literal["work", "gate", "work_gate"]


@dataclass(frozen=True)
class WorkflowPhase:
    key: str
    title: str
    description: str


@dataclass(frozen=True)
class WorkflowGate:
    key: str
    title: str
    required: bool
    description: str


@dataclass(frozen=True)
class WorkflowAgent:
    key: str
    title: str
    responsibility: str


@dataclass(frozen=True)
class WorkflowContractSpec:
    flow_variant: FlowVariant
    name: str
    summary: str
    sprint_horizon_minutes: int
    phase_chain: tuple[WorkflowPhase, ...]
    gates: tuple[WorkflowGate, ...]
    agent_team: tuple[WorkflowAgent, ...]
    quality_floor: tuple[str, ...]
    judge_checklist: tuple[str, ...]
    artifacts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "flow_variant": self.flow_variant,
            "name": self.name,
            "summary": self.summary,
            "sprint_horizon_minutes": self.sprint_horizon_minutes,
            "phase_chain": [
                {
                    "key": phase.key,
                    "title": phase.title,
                    "description": phase.description,
                }
                for phase in self.phase_chain
            ],
            "gates": [
                {
                    "key": gate.key,
                    "title": gate.title,
                    "required": gate.required,
                    "description": gate.description,
                }
                for gate in self.gates
            ],
            "agent_team": [
                {
                    "key": agent.key,
                    "title": agent.title,
                    "responsibility": agent.responsibility,
                }
                for agent in self.agent_team
            ],
            "quality_floor": list(self.quality_floor),
            "judge_checklist": list(self.judge_checklist),
            "artifacts": list(self.artifacts),
        }


STANDARD_PHASE_CHAIN: tuple[WorkflowPhase, ...] = (
    WorkflowPhase(
        key="research",
        title="同类产品研究",
        description="先研究同类产品、页面结构与关键交互，再进入文档阶段。",
    ),
    WorkflowPhase(
        key="docs",
        title="三份核心文档",
        description="生成 PRD、架构与 UI/UX 三份核心文档。",
    ),
    WorkflowPhase(
        key="docs_confirm",
        title="等待用户确认",
        description="三文档生成后先汇报并等待确认或修改。",
    ),
    WorkflowPhase(
        key="spec",
        title="Spec 与任务清单",
        description="用户确认后创建 proposal 与 tasks.md。",
    ),
    WorkflowPhase(
        key="frontend",
        title="前端实现与运行验证",
        description="先交付可演示前端，并运行验证可用状态。",
    ),
    WorkflowPhase(
        key="preview_confirm",
        title="等待预览确认",
        description="前端可演示后，先等待用户确认预览或继续修改。",
    ),
    WorkflowPhase(
        key="backend",
        title="后端实现与联调",
        description="在预览确认后，再进入后端、数据层与联调。",
    ),
    WorkflowPhase(
        key="quality",
        title="质量门禁",
        description="执行红队审查、UI 审查与质量门禁。",
    ),
    WorkflowPhase(
        key="delivery",
        title="交付与发布",
        description="生成交付包、部署配置和审计产物。",
    ),
)

CANONICAL_NINE_STAGE_IDS: tuple[str, ...] = tuple(phase.key for phase in STANDARD_PHASE_CHAIN)
CANONICAL_STAGE_KINDS: dict[str, StageKind] = {
    stage: (
        "gate"
        if stage in {"docs_confirm", "preview_confirm"}
        else ("work_gate" if stage == "quality" else "work")
    )
    for stage in CANONICAL_NINE_STAGE_IDS
}

SEEAI_PHASE_CHAIN: tuple[WorkflowPhase, ...] = (
    WorkflowPhase(
        key="research",
        title="比赛研究",
        description="快速识别题型、亮点和展示路径，不展开成长分析。",
    ),
    WorkflowPhase(
        key="docs",
        title="比赛短文档",
        description="生成压缩版研究、PRD、架构与 UI/UX 文档。",
    ),
    WorkflowPhase(
        key="docs_confirm",
        title="等待文档确认",
        description="三文档生成后先汇报并等待确认或修改。",
    ),
    WorkflowPhase(
        key="spec",
        title="Sprint Spec",
        description="把比赛范围压成一页 sprint 清单，马上进入执行。",
    ),
    WorkflowPhase(
        key="build_fullstack",
        title="前后端一体化开发",
        description="前后端一起推进，优先保住主演示路径和 wow 点。",
    ),
    WorkflowPhase(
        key="polish",
        title="演示打磨",
        description="做最小 polish、文案收口和演示讲解路径。",
    ),
    WorkflowPhase(
        key="quality",
        title="快速质量门禁",
        description="进行轻量质量检查，确保成品能稳定展示。",
    ),
    WorkflowPhase(
        key="delivery",
        title="交付与讲解",
        description="收口为可演示、可讲解、可提交的比赛成品。",
    ),
)

STANDARD_GATES: tuple[WorkflowGate, ...] = (
    WorkflowGate(
        key="docs_confirm",
        title="文档确认门",
        required=True,
        description="三份核心文档完成后必须等待用户确认。",
    ),
    WorkflowGate(
        key="preview_confirm",
        title="预览确认门",
        required=True,
        description="前端预览可演示后必须等待用户确认。",
    ),
    WorkflowGate(
        key="quality",
        title="质量门禁",
        required=True,
        description="交付前必须完成质量门禁检查。",
    ),
)

SEEAI_GATES: tuple[WorkflowGate, ...] = (
    WorkflowGate(
        key="docs_confirm",
        title="文档确认门",
        required=True,
        description="比赛短文档完成后必须等待用户确认。",
    ),
    WorkflowGate(
        key="preview_confirm",
        title="预览确认门",
        required=False,
        description="比赛模式不等待中途预览确认，直接进入前后端一体化开发。",
    ),
    WorkflowGate(
        key="quality",
        title="质量门禁",
        required=True,
        description="比赛收口前仍需做轻量质量检查。",
    ),
)

STANDARD_AGENT_TEAM: tuple[WorkflowAgent, ...] = (
    WorkflowAgent(
        key="researcher",
        title="Researcher",
        responsibility="研究同类产品与需求边界。",
    ),
    WorkflowAgent(
        key="pm",
        title="PM",
        responsibility="拆解需求、定义范围与验收标准。",
    ),
    WorkflowAgent(
        key="architect",
        title="Architect",
        responsibility="设计整体架构与关键接口。",
    ),
    WorkflowAgent(
        key="uiux",
        title="UI/UX",
        responsibility="定义视觉、交互与组件骨架。",
    ),
    WorkflowAgent(
        key="builder",
        title="Builder",
        responsibility="实现前后端与联调。",
    ),
    WorkflowAgent(
        key="qa",
        title="QA",
        responsibility="验证质量门禁与回归。",
    ),
)

SEEAI_AGENT_TEAM: tuple[WorkflowAgent, ...] = (
    WorkflowAgent(
        key="rapid_researcher",
        title="Rapid Researcher",
        responsibility="快速锁定题型、wow 点与主演示路径。",
    ),
    WorkflowAgent(
        key="sprint_pm",
        title="Sprint PM",
        responsibility="把比赛范围压成最小可交付 sprint。",
    ),
    WorkflowAgent(
        key="fullstack_builder",
        title="Full-Stack Builder",
        responsibility="前后端一体化推进可展示成品。",
    ),
    WorkflowAgent(
        key="visual_polish",
        title="Visual Polish",
        responsibility="完成比赛视觉打磨和讲解收口。",
    ),
    WorkflowAgent(
        key="qa",
        title="QA",
        responsibility="做快速验收和质量守门。",
    ),
)

STANDARD_WORKFLOW_CONTRACT = WorkflowContractSpec(
    flow_variant="standard",
    name="standard-workflow-contract",
    summary="适用于标准 Super Dev 的研究-文档-确认-实现-预览-后端-质量-交付流程。",
    sprint_horizon_minutes=240,
    phase_chain=STANDARD_PHASE_CHAIN,
    gates=STANDARD_GATES,
    agent_team=STANDARD_AGENT_TEAM,
    quality_floor=(
        "文档、实现、验证和交付必须完整闭环。",
        "预览确认门必须保留。",
        "交付前必须完成完整质量门禁。",
    ),
    judge_checklist=(),
    artifacts=("research.md", "prd.md", "architecture.md", "uiux.md", "proposal.md", "tasks.md"),
)

SEEAI_WORKFLOW_CONTRACT = WorkflowContractSpec(
    flow_variant="seeai",
    name="seeai-workflow-contract",
    summary="适用于比赛/黑客松的 30 分钟快速交付流程，保留最小研究、短文档、一次确认和一体化开发。",
    sprint_horizon_minutes=30,
    phase_chain=SEEAI_PHASE_CHAIN,
    gates=SEEAI_GATES,
    agent_team=SEEAI_AGENT_TEAM,
    quality_floor=SEEAI_QUALITY_FLOOR,
    judge_checklist=SEEAI_JUDGE_CHECKLIST,
    artifacts=("research.md", "prd.md", "architecture.md", "uiux.md", "tasks.md"),
)


def _normalize_flow_variant(flow_variant: str) -> FlowVariant:
    normalized = str(flow_variant).strip().lower()
    if normalized == "seeai":
        return "seeai"
    return "standard"


def get_workflow_contract(flow_variant: str = "standard") -> WorkflowContractSpec:
    normalized = _normalize_flow_variant(flow_variant)
    if normalized == "seeai":
        return SEEAI_WORKFLOW_CONTRACT
    return STANDARD_WORKFLOW_CONTRACT


def get_phase_chain(flow_variant: str = "standard") -> tuple[str, ...]:
    return tuple(phase.key for phase in get_workflow_contract(flow_variant).phase_chain)


def get_phase_kinds(flow_variant: str = "standard") -> dict[str, StageKind]:
    contract = get_workflow_contract(flow_variant)
    if contract.flow_variant == "standard":
        return dict(CANONICAL_STAGE_KINDS)
    return {
        phase.key: (
            "gate"
            if phase.key == "docs_confirm"
            else ("work_gate" if phase.key == "quality" else "work")
        )
        for phase in contract.phase_chain
    }


def get_gate_config(flow_variant: str = "standard") -> dict[str, bool]:
    return {gate.key: gate.required for gate in get_workflow_contract(flow_variant).gates}


def get_agent_team(flow_variant: str = "standard") -> tuple[WorkflowAgent, ...]:
    return get_workflow_contract(flow_variant).agent_team


def knowledge_authority_guidance(language: str = "zh") -> str:
    """Shared wording for the existing standard-mode knowledge contract."""
    if language == "en":
        return (
            "Knowledge requirements without explicit applicability conditions remain mandatory. "
            "Apply explicitly conditional requirements according to their stated conditions, "
            "and explain why each selected requirement applies. Retrieval is not permission "
            "to silently weaken requirements, extend task scope, or change confirmed decisions. "
            "Explicit examples and optional methods retain that declared status. Preserve project "
            "configuration and existing default quality requirements; report unresolved conflicts "
            "instead of choosing a lower standard or rewriting the knowledge base."
        )
    return (
        "知识要求无显式适用条件时继续默认强制；明确带条件的按原条件适用，"
        "说明命中内容为何适用。不得由模型自行降级原有要求，也不因检索命中扩大任务或权限。"
        "明确标注为示例或可选方法的内容保留原含义。项目配置和现有默认质量要求继续有效；"
        "未解决的冲突说明依据并交回原决定方，不自行选择较低标准或改写知识库。"
    )


def readonly_request_guidance(language: str = "zh") -> str:
    """A request boundary, not another workflow mode or state transition."""
    if language == "en":
        return (
            "A read-only explanation, analysis or review does not authorize implementation, "
            "file changes or workflow state transitions, even when workflow artifacts exist. "
            "Keep existing state unchanged. In mixed requests, act only on explicitly authorized "
            "changes; do not ask again for authority already given. Reading these rules as review "
            "material does not activate their workflow. For execution requests, continue Super Dev "
            "from the valid recorded change and phase rather than restarting."
        )
    return (
        "解释、分析和审查等只读请求不授权实现、文件修改或阶段推进，即使已有流程产物也保持状态不变。"
        "混合请求只实施明确获准的部分；已有授权不重复索取。阅读或评审这些规则不等于激活其中流程。"
    )


__all__ = [
    "FlowVariant",
    "StageKind",
    "WorkflowAgent",
    "WorkflowContractSpec",
    "WorkflowGate",
    "WorkflowPhase",
    "SEEAI_WORKFLOW_CONTRACT",
    "STANDARD_WORKFLOW_CONTRACT",
    "CANONICAL_NINE_STAGE_IDS",
    "CANONICAL_STAGE_KINDS",
    "get_agent_team",
    "get_gate_config",
    "get_phase_chain",
    "get_phase_kinds",
    "get_workflow_contract",
]
