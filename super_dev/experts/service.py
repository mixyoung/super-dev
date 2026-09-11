"""专家建议服务。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_EXPERT_META: list[dict[str, str]] = [
    {"id": "PRODUCT", "name": "产品负责人", "description": "产品闭环、功能缺口、体验总审查"},
    {"id": "PM", "name": "产品经理", "description": "需求分析、PRD编写"},
    {"id": "ARCHITECT", "name": "架构师", "description": "系统设计、技术选型"},
    {"id": "UI", "name": "UI设计师", "description": "视觉设计、设计规范"},
    {"id": "UX", "name": "UX设计师", "description": "交互设计、用户体验"},
    {"id": "SECURITY", "name": "安全专家", "description": "安全审查、漏洞检测"},
    {"id": "CODE", "name": "开发专家", "description": "代码实现、最佳实践"},
    {"id": "DBA", "name": "数据库专家", "description": "数据库设计、优化"},
    {"id": "QA", "name": "测试专家", "description": "质量保证、测试策略"},
    {"id": "DEVOPS", "name": "运维专家", "description": "部署、CI/CD"},
    {"id": "RCA", "name": "故障侦探", "description": "根因分析、复盘改进"},
]


_TEAM_META: list[dict[str, str]] = [
    {
        "id": "PRODUCT_AUDIT",
        "name": "产品审查团队",
        "description": "产品负责人牵头，联动 PM/UX/ARCHITECT/SECURITY/CODE/QA/DEVOPS 做全项目闭环审查",
    },
]

_TEAM_COMPOSITION: dict[str, list[str]] = {
    "PRODUCT_AUDIT": ["PRODUCT", "PM", "UX", "ARCHITECT", "SECURITY", "CODE", "QA", "DEVOPS"],
}


def list_experts() -> list[dict[str, str]]:
    return list(_EXPERT_META)


def list_expert_teams() -> list[dict[str, str]]:
    return list(_TEAM_META)


def has_expert(expert_id: str) -> bool:
    return any(item["id"] == expert_id for item in _EXPERT_META)


def has_expert_team(team_id: str) -> bool:
    return team_id in _TEAM_COMPOSITION


def render_expert_advice_markdown(expert_id: str, prompt: str = "") -> str:
    from ..orchestrator.experts import ExpertRole, get_expert_profile
    from .behavioral_prompts import EXPERT_SCOPE_GUIDANCE

    suggestions = (
        get_expert_profile(ExpertRole(expert_id)).thinking_framework
        if has_expert(expert_id)
        else []
    )
    lines = [
        f"# {expert_id} 专家建议",
        "",
        f"**输入问题**: {prompt or '(未提供，输出通用建议)'}",
        "",
        "以下内容是供宿主结合实际项目使用的指导，尚未执行审查或修改。",
        "",
        EXPERT_SCOPE_GUIDANCE,
        "",
        "## 建议清单",
        "",
    ]
    for idx, item in enumerate(suggestions, 1):
        lines.append(f"{idx}. {item}")
    lines.extend(
        [
            "",
            "## 下一步执行",
            "",
            "1. 先按本轮问题筛选适用建议，复用已有需求、决定和实际证据。",
            "2. 只要求审查时返回发现；获准实施后再将必要修改纳入原任务。",
            "3. 实施后按风险验证；项目已有必过检查继续执行，未执行项如实说明。",
            "",
        ]
    )
    return "\n".join(lines)


def render_team_advice_markdown(team_id: str, prompt: str = "") -> str:
    if team_id not in _TEAM_COMPOSITION:
        raise ValueError(f"unknown team: {team_id}")

    members = _TEAM_COMPOSITION[team_id]
    lines = [
        f"# {team_id} 团队审查报告",
        "",
        f"**输入问题**: {prompt or '(未提供，按仓库级全面审查输出)'}",
        "",
        "这是多专业视角的审查提纲，不代表已经启动独立专家或完成审查。",
        "只使用当前问题相关的维度，不把通用清单变成新增功能要求。",
        "",
        "## 团队组成",
        "",
    ]
    for member in members:
        meta = next(
            (item for item in _EXPERT_META if item["id"] == member),
            {"name": member, "description": ""},
        )
        lines.append(f"- **{member}**: {meta['name']} - {meta['description']}")

    lines.extend(
        [
            "",
            "## 审查维度",
            "",
            "1. 产品与上手路径：用户是否知道怎么开始、怎么继续、怎么确认流程完成。",
            "2. 交互与信息架构：主路径、确认门、失败恢复、状态反馈是否闭环。",
            "3. 功能完整性：是否存在承诺了但没有真实做成的能力、文档断链或命令断链。",
            "4. 技术与架构：代码结构是否支持持续迭代，协议/规则是否有单一真相源。",
            "5. 质量与安全：红队、质量门禁、proof-pack、release readiness 是否引用同一套证据。",
            "6. 交付闭环：报告、任务执行、自检、评审状态、发布证据是否一致。",
            "",
            "## 输出要求",
            "",
            "1. 先按严重级别列出问题，必须带文件路径与原因。",
            "2. 再给出按优先级排序的修复建议。",
            "3. 区分本轮必要修复、可选建议和需要用户决定的事项，不自动扩大范围。",
            "",
            "## 下一步执行",
            "",
            "1. 阅读实际产物后报告发现，按请求需要保留审查记录。",
            "2. 只读审查不修改代码；获得实施授权后处理范围内的必要问题。",
            "3. 实施后核对受影响行为；进入交付收尾时刷新对应质量与发布证据。",
            "",
        ]
    )
    return "\n".join(lines)


def save_expert_advice(project_dir: Path, expert_id: str, prompt: str = "") -> tuple[Path, str]:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    content = render_expert_advice_markdown(expert_id=expert_id, prompt=prompt)
    file_path = output_dir / f"expert-{expert_id.lower()}-advice.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path, content


def save_team_advice(project_dir: Path, team_id: str, prompt: str = "") -> tuple[Path, str]:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    content = render_team_advice_markdown(team_id=team_id, prompt=prompt)
    file_path = output_dir / f"team-{team_id.lower().replace('_', '-')}-report.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path, content


def list_expert_advice_history(project_dir: Path, limit: int = 20) -> list[dict[str, str]]:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    if not output_dir.exists():
        return []

    items: list[dict[str, str]] = []
    files = sorted(
        output_dir.glob("expert-*-advice.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for file_path in files[:limit]:
        name = file_path.name
        expert_id = name.removeprefix("expert-").removesuffix("-advice.md").upper()
        items.append(
            {
                "file_name": name,
                "file_path": str(file_path),
                "expert_id": expert_id,
                "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            }
        )
    return items


def read_expert_advice(project_dir: Path, file_name: str) -> tuple[Path, str]:
    project_dir = Path(project_dir).resolve()
    output_dir = project_dir / "output"
    if "/" in file_name or "\\" in file_name:
        raise ValueError("invalid file name")
    if not (file_name.startswith("expert-") and file_name.endswith("-advice.md")):
        raise ValueError("invalid file name")

    file_path = (output_dir / file_name).resolve()
    if not file_path.exists():
        raise FileNotFoundError(file_name)
    if output_dir.resolve() not in file_path.parents:
        raise ValueError("invalid file path")

    return file_path, file_path.read_text(encoding="utf-8")
