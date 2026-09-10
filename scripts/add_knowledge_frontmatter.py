#!/usr/bin/env python3
"""
为知识库文件添加 YAML frontmatter 摘要头。

让每个知识文件自描述：什么阶段激活、token 预算、关联路径。
借鉴 Knowledge Activation 论文的 agent-optimized 摘要头设计。

frontmatter 格式:
---
id: owasp-top10-complete
title: OWASP Top 10 完整指南
domain: security
category: standards
phase_trigger: [backend, quality]
tech_trigger: [python, javascript]
token_budget: 500
priority: high
summary: "OWASP Top 10 安全风险的完整检查指南"
related: [api-security-complete, supply-chain-security]
---

用法:
    python scripts/add_knowledge_frontmatter.py              # 扫描并添加
    python scripts/add_knowledge_frontmatter.py --dry-run    # 仅预览
    python scripts/add_knowledge_frontmatter.py --force      # 覆盖已有 frontmatter

开发：Excellent（11964948@qq.com）
创建时间：2026-03-28
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# 推断规则
# ---------------------------------------------------------------------------

# domain -> 默认 phase_trigger 映射
DOMAIN_PHASE_MAP: dict[str, list[str]] = {
    "product": ["research", "docs"],
    "architecture": ["docs", "spec", "backend"],
    "design": ["docs", "frontend"],
    "development": ["frontend", "backend", "spec"],
    "frontend": ["frontend"],
    "backend": ["backend"],
    "security": ["backend", "quality", "redteam"],
    "testing": ["quality", "qa"],
    "operations": ["delivery", "deployment"],
    "devops": ["delivery", "deployment"],
    "cicd": ["delivery", "deployment"],
    "cloud-native": ["backend", "deployment"],
    "data": ["backend"],
    "data-engineering": ["backend"],
    "database": ["backend", "spec"],
    "mobile": ["frontend"],
    "ai": ["research", "docs", "backend"],
    "incident": ["quality", "deployment"],
    "edge-iot": ["backend", "deployment"],
    "blockchain": ["backend"],
    "industries": ["research", "docs"],
    "quantum": ["research"],
}

# 文件名关键词 -> tech_trigger 映射
FILENAME_TECH_MAP: dict[str, list[str]] = {
    "react": ["react", "javascript", "typescript"],
    "vue": ["vue", "javascript", "typescript"],
    "angular": ["angular", "typescript"],
    "svelte": ["svelte", "javascript"],
    "next": ["react", "nextjs", "typescript"],
    "nuxt": ["vue", "nuxt", "typescript"],
    "flutter": ["flutter", "dart"],
    "react-native": ["react-native", "javascript"],
    "python": ["python"],
    "django": ["python", "django"],
    "fastapi": ["python", "fastapi"],
    "flask": ["python", "flask"],
    "node": ["node", "javascript", "typescript"],
    "express": ["node", "express"],
    "nestjs": ["node", "nestjs", "typescript"],
    "golang": ["go"],
    "go-": ["go"],
    "rust": ["rust"],
    "java": ["java"],
    "spring": ["java", "spring"],
    "postgresql": ["postgresql"],
    "postgres": ["postgresql"],
    "mongodb": ["mongodb"],
    "redis": ["redis"],
    "mysql": ["mysql"],
    "elasticsearch": ["elasticsearch"],
    "graphql": ["graphql"],
    "rest-api": ["rest"],
    "kubernetes": ["kubernetes"],
    "docker": ["docker"],
    "terraform": ["terraform"],
    "airflow": ["python", "airflow"],
    "spark": ["spark"],
    "playwright": ["playwright", "typescript"],
    "jest": ["jest", "javascript"],
    "pytest": ["python", "pytest"],
    "oauth2": ["oauth2"],
    "tailwind": ["tailwind", "css"],
    "sass": ["sass", "css"],
}

# category 子目录 -> 标准分类名
CATEGORY_MAP: dict[str, str] = {
    "01-standards": "standards",
    "02-playbooks": "playbooks",
    "03-checklists": "checklists",
    "04-antipatterns": "antipatterns",
    "05-cases": "cases",
    "06-glossary": "glossary",
    "09-maturity": "maturity",
    "11-ui-excellence": "standards",
    "13-implementation-assets": "playbooks",
    "00-governance": "governance",
}

# priority 推断规则：category -> 默认优先级
CATEGORY_PRIORITY: dict[str, str] = {
    "standards": "high",
    "checklists": "high",
    "antipatterns": "medium",
    "playbooks": "medium",
    "governance": "medium",
    "maturity": "low",
    "cases": "low",
    "glossary": "low",
}


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------


def has_frontmatter(content: str) -> bool:
    """检查文件是否已有 YAML frontmatter"""
    return content.startswith("---\n") or content.startswith("---\r\n")


def extract_existing_frontmatter(content: str) -> dict[str, str] | None:
    """提取已有的 frontmatter（如果有）"""
    if not has_frontmatter(content):
        return None
    end = content.find("\n---", 3)
    if end < 0:
        return None
    fm_text = content[4:end]
    result: dict[str, str] = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def infer_domain(rel_path: Path) -> str:
    """从相对路径推断 domain"""
    parts = rel_path.parts
    if len(parts) >= 1:
        return parts[0]
    return "unknown"


def infer_category(rel_path: Path) -> str:
    """从相对路径推断 category"""
    parts = rel_path.parts
    if len(parts) >= 2:
        second = parts[1]
        if re.match(r"^\d{2}-", second):
            return CATEGORY_MAP.get(second, second)
    # 根目录下的文件，从文件名推断
    filename = rel_path.stem.lower()
    if "checklist" in filename:
        return "checklists"
    if "antipattern" in filename:
        return "antipatterns"
    if "playbook" in filename or "guide" in filename:
        return "playbooks"
    if "glossary" in filename:
        return "glossary"
    if "case" in filename:
        return "cases"
    if "deep-dive" in filename or "complete" in filename:
        return "standards"
    return "standards"


def infer_phase_triggers(domain: str, category: str, filename: str) -> list[str]:
    """推断文件在哪些 pipeline 阶段被激活"""
    phases = list(DOMAIN_PHASE_MAP.get(domain, ["docs"]))

    # antipatterns 和 checklists 通常在 quality/redteam 中也激活
    if category in ("antipatterns", "checklists"):
        for p in ("quality", "redteam"):
            if p not in phases:
                phases.append(p)

    return phases


def infer_tech_triggers(filename: str, content_head: str) -> list[str]:
    """从文件名和内容头部推断关联的技术栈"""
    techs: set[str] = set()
    filename_lower = filename.lower()

    for keyword, tech_list in FILENAME_TECH_MAP.items():
        if keyword in filename_lower:
            techs.update(tech_list)

    # 如果文件名没匹配到，从内容头部找
    if not techs:
        content_lower = content_head.lower()
        for keyword, tech_list in FILENAME_TECH_MAP.items():
            # 只在内容前 500 字符中找，避免误匹配
            if keyword in content_lower[:500]:
                techs.update(tech_list)

    return sorted(techs)


def infer_priority(category: str, file_size: int) -> str:
    """推断推送优先级"""
    base = CATEGORY_PRIORITY.get(category, "medium")
    # 大文件（>50KB）降级，小文件不变
    if file_size > 100_000 and base == "high":
        return "medium"
    return base


def extract_summary(content: str) -> str:
    """从文件的第一段正文提取 summary"""
    # 跳过已有 frontmatter
    text = content
    if has_frontmatter(text):
        end = text.find("\n---", 3)
        if end > 0:
            text = text[end + 4 :]

    lines = text.split("\n")
    paragraphs: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        # 跳过标题行
        if stripped.startswith("#"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        # 跳过注释行（# 开头但没有空格的不是标题）
        if stripped.startswith("# ") and "开发：" in stripped:
            continue
        # 跳过空行
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        # 跳过代码块
        if stripped.startswith("```"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        # 收集正文
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    # 取第一个至少 20 字符的段落
    for p in paragraphs:
        if len(p) >= 20:
            # 截断到 200 字符
            summary = p[:200]
            if len(p) > 200:
                summary = summary.rsplit("，", 1)[0] if "，" in summary[150:] else summary
                summary = summary.rsplit(",", 1)[0] if "," in summary[150:] else summary
            return summary

    return ""


def extract_title(content: str) -> str:
    """提取 # 标题"""
    text = content
    if has_frontmatter(text):
        end = text.find("\n---", 3)
        if end > 0:
            text = text[end + 4 :]

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("# 开发："):
            return stripped[2:].strip()
    return ""


def infer_related(filename: str, domain: str, all_stems: set[str]) -> list[str]:
    """推断关联文件"""
    related: list[str] = []
    stem = Path(filename).stem.lower()

    # 同 domain 下的其他文件
    # 基于共享关键词
    stem_parts = set(re.split(r"[-_]", stem))
    stem_parts.discard("complete")
    stem_parts.discard("deep")
    stem_parts.discard("dive")

    for other_stem in sorted(all_stems):
        if other_stem == stem:
            continue
        other_parts = set(re.split(r"[-_]", other_stem))
        overlap = stem_parts & other_parts
        # 至少有一个有意义的词重叠
        meaningful_overlap = {w for w in overlap if len(w) > 3}
        if meaningful_overlap:
            related.append(other_stem)
            if len(related) >= 5:
                break

    return related


def estimate_token_budget(file_size: int, priority: str) -> int:
    """估算注入 prompt 时的 token 预算"""
    if priority == "high":
        return min(800, max(300, file_size // 8))
    elif priority == "medium":
        return min(500, max(200, file_size // 12))
    else:
        return min(300, max(100, file_size // 16))


def build_frontmatter(
    file_id: str,
    title: str,
    domain: str,
    category: str,
    phase_trigger: list[str],
    tech_trigger: list[str],
    token_budget: int,
    priority: str,
    summary: str,
    related: list[str],
) -> str:
    """构建 YAML frontmatter 字符串"""
    lines = ["---"]
    lines.append(f"id: {file_id}")
    lines.append(f'title: "{title}"' if title else f"id: {file_id}")
    lines.append(f"domain: {domain}")
    lines.append(f"category: {category}")
    lines.append(f"phase_trigger: [{', '.join(phase_trigger)}]")
    if tech_trigger:
        lines.append(f"tech_trigger: [{', '.join(tech_trigger)}]")
    lines.append(f"token_budget: {token_budget}")
    lines.append(f"priority: {priority}")
    if summary:
        # 转义双引号
        safe_summary = summary.replace('"', '\\"')
        lines.append(f'summary: "{safe_summary}"')
    if related:
        lines.append(f"related: [{', '.join(related)}]")
    lines.append("---")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def process_knowledge_dir(
    knowledge_dir: Path,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, int]:
    """扫描知识目录，为文件添加 frontmatter

    Returns
    -------
    dict[str, int]
        统计结果: added, skipped, error
    """
    stats = {"added": 0, "skipped": 0, "error": 0, "total": 0}

    if not knowledge_dir.is_dir():
        print(f"错误: 知识目录不存在: {knowledge_dir}")
        return stats

    md_files = sorted(knowledge_dir.rglob("*.md"))
    stats["total"] = len(md_files)

    # 收集所有文件 stem 用于 related 推断
    all_stems = {f.stem.lower() for f in md_files}

    for md_path in md_files:
        # 跳过隐藏目录
        if any(part.startswith(".") for part in md_path.parts):
            stats["skipped"] += 1
            continue

        try:
            content = md_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  错误: 无法读取 {md_path}: {e}")
            stats["error"] += 1
            continue

        # 如果已有 frontmatter 且不 force，跳过
        if has_frontmatter(content) and not force:
            stats["skipped"] += 1
            continue

        rel_path = md_path.relative_to(knowledge_dir)
        domain = infer_domain(rel_path)
        category = infer_category(rel_path)
        file_id = md_path.stem.lower()
        title = extract_title(content) or md_path.stem.replace("-", " ").replace("_", " ").title()
        phase_trigger = infer_phase_triggers(domain, category, md_path.name)
        tech_trigger = infer_tech_triggers(md_path.name, content[:500])
        priority = infer_priority(category, md_path.stat().st_size)
        summary = extract_summary(content)
        related = infer_related(md_path.name, domain, all_stems)
        token_budget = estimate_token_budget(md_path.stat().st_size, priority)

        fm = build_frontmatter(
            file_id=file_id,
            title=title,
            domain=domain,
            category=category,
            phase_trigger=phase_trigger,
            tech_trigger=tech_trigger,
            token_budget=token_budget,
            priority=priority,
            summary=summary,
            related=related,
        )

        if dry_run:
            print(f"  [DRY-RUN] {rel_path}")
            print(f"    domain={domain} category={category} priority={priority}")
            print(f"    phases={phase_trigger} techs={tech_trigger}")
            print(f"    summary={summary[:80]}...")
            stats["added"] += 1
            continue

        # 如果 force 且已有 frontmatter，先移除旧的
        if has_frontmatter(content):
            end = content.find("\n---", 3)
            if end > 0:
                content = content[end + 4 :].lstrip("\n")

        new_content = fm + "\n" + content
        try:
            md_path.write_text(new_content, encoding="utf-8")
            stats["added"] += 1
            print(f"  ✓ {rel_path}")
        except OSError as e:
            print(f"  错误: 无法写入 {md_path}: {e}")
            stats["error"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="为知识库文件添加 YAML frontmatter 摘要头")
    parser.add_argument(
        "--knowledge-dir",
        type=Path,
        default=None,
        help="知识库目录路径（默认: 项目根目录/knowledge）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览，不实际写入文件",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已有的 frontmatter",
    )
    args = parser.parse_args()

    # 查找项目根目录
    knowledge_dir = args.knowledge_dir
    if knowledge_dir is None:
        # 从脚本位置向上找
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        knowledge_dir = project_root / "knowledge"

    print(f"知识库目录: {knowledge_dir}")
    print(f"模式: {'预览 (dry-run)' if args.dry_run else '写入'}")
    if args.force:
        print("强制模式: 将覆盖已有 frontmatter")
    print()

    stats = process_knowledge_dir(knowledge_dir, dry_run=args.dry_run, force=args.force)

    print()
    print(f"统计: 总计 {stats['total']} 文件")
    print(f"  添加: {stats['added']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {stats['error']}")


if __name__ == "__main__":
    main()
