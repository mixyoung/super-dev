"""
Expert 定义加载器 — 支持从 Markdown frontmatter 加载专家定义。

支持从 Markdown frontmatter 加载专家定义，
允许用户通过 Markdown 文件自定义专家角色。

加载优先级 (后者覆盖前者):
  1. 内置专家: super_dev/experts/builtin/*.md
  2. 用户全局: ~/.super-dev/experts/*.md
  3. 项目级:   .super-dev/experts/*.md

开发：Super Dev Team
创建时间：2026-03-31
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..orchestrator.experts import ExpertProfile, ExpertRole
from ..utils import get_logger

logger = get_logger("expert_loader")


@dataclass
class ExpertDefinition:
    """从 Markdown frontmatter 解析的专家定义。

    从 Markdown frontmatter 解析的专家定义。
    """

    name: str
    role: str  # ExpertRole.value
    title: str
    description: str
    goal: str
    backstory: str = ""
    focus_areas: list[str] = field(default_factory=list)
    thinking_framework: list[str] = field(default_factory=list)
    quality_criteria: list[str] = field(default_factory=list)
    handoff_checklist: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)  # 绑定到哪些 pipeline 阶段
    tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    model: str = ""
    effort: str = ""  # min/low/medium/high/max
    when_to_use: str = ""
    source: str = "builtin"  # builtin / user / project
    file_path: str = ""


def _unquote(value: str) -> str:
    """Remove a matching YAML quote pair without damaging quotes in plain text."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str]:
    """解析 Markdown 文件的 YAML frontmatter。

    Returns:
        (frontmatter_dict, body_content)
    """
    if not text.startswith("---"):
        return {}, text

    end_match = re.search(r"\n---\s*\n", text[3:])
    if not end_match:
        return {}, text

    fm_text = text[3 : 3 + end_match.start()]
    body = text[3 + end_match.end() :]

    result: dict[str, str | list[str]] = {}
    current_key = ""
    current_list: list[str] | None = None

    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item under current key
        if stripped.startswith("- ") and current_key:
            item = _unquote(stripped[2:].strip())
            if current_list is not None:
                current_list.append(item)
            continue

        # Key: value pair
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = _unquote(val.strip())
            current_key = key
            if val:
                result[key] = val
                current_list = None
            else:
                # Start a list
                current_list = []
                result[key] = current_list

    return result, body.strip()


def _parse_list_field(fm: dict, key: str) -> list[str]:
    """从 frontmatter 中提取列表字段。"""
    val = fm.get(key, [])
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val:
        return [item.strip() for item in val.split(",") if item.strip()]
    return []


def parse_expert_from_markdown(
    file_path: Path,
    source: str = "builtin",
) -> ExpertDefinition | None:
    """从 Markdown 文件解析专家定义。

    文件格式:
    ```markdown
    ---
    name: PM
    role: PM
    title: 产品经理
    description: 需求分析、PRD 编写、用户故事、业务规则
    goal: 将模糊的用户需求转化为清晰、可执行、可验收的产品规范
    phases: discovery, intelligence, drafting
    effort: high
    ---
    # 专家正文（backstory + thinking framework 等）
    ```
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"无法读取专家文件 {file_path}: {e}")
        return None

    fm, body = parse_frontmatter(text)
    if not fm:
        return None

    name = str(fm.get("name", ""))
    if not name:
        logger.warning(f"专家文件缺少 name 字段: {file_path}")
        return None

    role = str(fm.get("role", name)).upper()
    title = str(fm.get("title", name))
    description = str(fm.get("description", ""))
    goal = str(fm.get("goal", ""))

    if not goal:
        logger.warning(f"专家文件缺少 goal 字段: {file_path}")
        return None

    return ExpertDefinition(
        name=name,
        role=role,
        title=title,
        description=description,
        goal=goal,
        backstory=_extract_section(body, "backstory") or str(fm.get("backstory", "")),
        focus_areas=_parse_list_field(fm, "focus_areas"),
        thinking_framework=_parse_list_field(fm, "thinking_framework"),
        quality_criteria=_parse_list_field(fm, "quality_criteria"),
        handoff_checklist=_parse_list_field(fm, "handoff_checklist"),
        phases=_parse_list_field(fm, "phases"),
        tools=_parse_list_field(fm, "tools"),
        disallowed_tools=_parse_list_field(fm, "disallowed_tools"),
        model=str(fm.get("model", "")),
        effort=str(fm.get("effort", "")),
        when_to_use=str(fm.get("when_to_use", "")),
        source=source,
        file_path=str(file_path),
    )


def _extract_section(body: str, heading: str) -> str:
    """从 Markdown body 中提取指定 heading 下的内容。"""
    pattern = rf"(?:^|\n)##?\s+{re.escape(heading)}\s*\n(.*?)(?=\n##?\s|\Z)"
    match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def definition_to_profile(defn: ExpertDefinition) -> ExpertProfile:
    """将 ExpertDefinition 转换为现有的 ExpertProfile 格式。"""
    try:
        role = ExpertRole(defn.role)
    except ValueError:
        role = ExpertRole.CODE  # 默认回退

    return ExpertProfile(
        role=role,
        title=defn.title,
        goal=defn.goal,
        backstory=defn.backstory,
        focus_areas=defn.focus_areas,
        thinking_framework=defn.thinking_framework,
        quality_criteria=defn.quality_criteria,
        handoff_checklist=defn.handoff_checklist,
    )


def load_expert_definitions(
    project_dir: Path | None = None,
) -> dict[str, ExpertDefinition]:
    """从多来源加载专家定义。

    优先级 (后者覆盖前者):
      1. 内置专家
      2. 用户全局 (~/.super-dev/experts/)
      3. 项目级 (.super-dev/experts/)
    """
    experts: dict[str, ExpertDefinition] = {}

    # 1. 内置专家
    builtin_dir = Path(__file__).parent / "builtin"
    if builtin_dir.is_dir():
        for md_file in sorted(builtin_dir.glob("*.md")):
            defn = parse_expert_from_markdown(md_file, source="builtin")
            if defn:
                experts[defn.name] = defn

    # 2. 用户全局
    user_dir = Path.home() / ".super-dev" / "experts"
    if user_dir.is_dir():
        for md_file in sorted(user_dir.glob("*.md")):
            defn = parse_expert_from_markdown(md_file, source="user")
            if defn:
                experts[defn.name] = defn

    # 3. 项目级
    if project_dir:
        project_expert_dir = Path(project_dir) / ".super-dev" / "experts"
        if project_expert_dir.is_dir():
            for md_file in sorted(project_expert_dir.glob("*.md")):
                defn = parse_expert_from_markdown(md_file, source="project")
                if defn:
                    experts[defn.name] = defn

    return experts


def load_expert_profiles(
    project_dir: Path | None = None,
) -> dict[ExpertRole, ExpertProfile]:
    """加载所有专家定义并转换为 ExpertProfile 格式。

    兼容现有的 EXPERT_PROFILES 接口。
    """
    definitions = load_expert_definitions(project_dir)
    profiles: dict[ExpertRole, ExpertProfile] = {}

    source_priority = {"builtin": 0, "user": 1, "project": 2}
    for defn in sorted(definitions.values(), key=lambda item: source_priority.get(item.source, 0)):
        # Built-in variants remain explicitly selectable definitions. They must not
        # replace the general role just because their filenames sort after it.
        if defn.source == "builtin" and defn.name.upper() != defn.role.upper():
            continue
        profile = definition_to_profile(defn)
        profiles[profile.role] = profile

    # 如果 Markdown 没有覆盖所有内置角色，从硬编码回退
    from ..orchestrator.experts import EXPERT_PROFILES as BUILTIN_PROFILES

    for role, profile in BUILTIN_PROFILES.items():
        if role not in profiles:
            profiles[role] = profile

    return profiles
