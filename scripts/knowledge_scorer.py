#!/usr/bin/env python3
"""
Super Dev 知识库质量评分器
为每个知识文件计算质量分数。
质量分 >= 80 为生产可用，60-79 需改进，< 60 标记为 discard。

用法:
    python scripts/knowledge_scorer.py                    # 评估所有知识文件
    python scripts/knowledge_scorer.py --domain security  # 评估指定领域
    python scripts/knowledge_scorer.py --min-score 80     # 只显示低于阈值的文件
    python scripts/knowledge_scorer.py --output results   # 输出 results.tsv
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class KnowledgeScore:
    file_path: str
    domain: str
    category: str
    total_score: float
    completeness: float  # 内容完整性 (0-100)
    executability: float  # 可执行性/代码示例 (0-100)
    structure: float  # 结构清晰度 (0-100)
    depth: float  # 内容深度 (0-100)
    agent_ready: float  # Agent 可用性 (0-100)
    status: str  # keep / improve / discard
    line_count: int
    code_blocks: int
    sections: int
    has_agent_checklist: bool
    issues: list[str]


class KnowledgeScorer:
    """知识库质量评分器"""

    # 权重配置 (总和 = 1.0)
    WEIGHTS = {
        "completeness": 0.25,
        "executability": 0.25,
        "structure": 0.20,
        "depth": 0.15,
        "agent_ready": 0.15,
    }

    # 质量门禁
    THRESHOLD_KEEP = 80
    THRESHOLD_IMPROVE = 60

    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = Path(knowledge_dir)

    def score_file(self, file_path: Path) -> KnowledgeScore:
        """评估单个知识文件"""
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        line_count = len(lines)

        # 提取领域和分类
        rel_path = file_path.relative_to(self.knowledge_dir)
        parts = rel_path.parts
        domain = parts[0] if len(parts) > 0 else "unknown"
        category = parts[1] if len(parts) > 1 else "unknown"

        # 分析内容
        code_blocks = len(re.findall(r"```\w*\n", content))
        sections = len(re.findall(r"^#{1,3}\s+", content, re.MULTILINE))
        has_agent_checklist = bool(
            re.search(r"agent.*(checklist|指令|instruction)", content, re.IGNORECASE)
        )

        issues = []

        # 1. 完整性评分 (0-100)
        completeness = self._score_completeness(content, lines, line_count, issues)

        # 2. 可执行性评分 (0-100)
        executability = self._score_executability(content, code_blocks, issues)

        # 3. 结构清晰度评分 (0-100)
        structure = self._score_structure(content, sections, line_count, issues)

        # 4. 内容深度评分 (0-100)
        depth = self._score_depth(content, line_count, sections, code_blocks, issues)

        # 5. Agent 可用性评分 (0-100)
        agent_ready = self._score_agent_ready(content, has_agent_checklist, issues)

        # 总分
        total = (
            completeness * self.WEIGHTS["completeness"]
            + executability * self.WEIGHTS["executability"]
            + structure * self.WEIGHTS["structure"]
            + depth * self.WEIGHTS["depth"]
            + agent_ready * self.WEIGHTS["agent_ready"]
        )

        # 状态判定
        if total >= self.THRESHOLD_KEEP:
            status = "keep"
        elif total >= self.THRESHOLD_IMPROVE:
            status = "improve"
        else:
            status = "discard"

        return KnowledgeScore(
            file_path=str(file_path),
            domain=domain,
            category=category,
            total_score=round(total, 1),
            completeness=round(completeness, 1),
            executability=round(executability, 1),
            structure=round(structure, 1),
            depth=round(depth, 1),
            agent_ready=round(agent_ready, 1),
            status=status,
            line_count=line_count,
            code_blocks=code_blocks,
            sections=sections,
            has_agent_checklist=has_agent_checklist,
            issues=issues,
        )

    def _score_completeness(
        self, content: str, lines: list, line_count: int, issues: list
    ) -> float:
        score = 0.0
        # 行数基础分
        if line_count >= 500:
            score += 40
        elif line_count >= 200:
            score += 30
        elif line_count >= 100:
            score += 20
        elif line_count >= 50:
            score += 10
        else:
            issues.append(f"内容过短 ({line_count} 行)")

        # 必须有概述/Overview
        if re.search(r"(概述|overview|introduction|简介)", content, re.IGNORECASE):
            score += 15
        else:
            issues.append("缺少概述/Overview 章节")

        # 必须有最佳实践
        if re.search(r"(最佳实践|best.?practice|推荐)", content, re.IGNORECASE):
            score += 15
        else:
            issues.append("缺少最佳实践章节")

        # 必须有参考资料
        if re.search(r"(参考|reference|资料|官方文档|链接)", content, re.IGNORECASE):
            score += 15
        else:
            issues.append("缺少参考资料")

        # 有常见陷阱/反模式
        if re.search(r"(陷阱|pitfall|反模式|antipattern|常见错误|mistake)", content, re.IGNORECASE):
            score += 15

        return min(score, 100)

    def _score_executability(self, content: str, code_blocks: int, issues: list) -> float:
        score = 0.0
        # 代码块数量
        if code_blocks >= 10:
            score += 50
        elif code_blocks >= 5:
            score += 35
        elif code_blocks >= 3:
            score += 25
        elif code_blocks >= 1:
            score += 15
        else:
            issues.append("缺少代码示例")

        # 代码语言标注
        annotated = len(
            re.findall(
                r"```(python|javascript|typescript|go|rust|java|sql|bash|yaml|dockerfile)",
                content,
                re.IGNORECASE,
            )
        )
        if annotated >= 5:
            score += 20
        elif annotated >= 2:
            score += 10

        # 配置模板
        if re.search(r"(配置|config|template|模板|yaml|toml|json)", content, re.IGNORECASE):
            score += 15

        # 命令行示例
        if re.search(r"```(bash|shell|sh)\n", content, re.IGNORECASE):
            score += 15

        return min(score, 100)

    def _score_structure(self, content: str, sections: int, line_count: int, issues: list) -> float:
        score = 0.0
        # 标题层次
        h1_count = len(re.findall(r"^# ", content, re.MULTILINE))
        h2_count = len(re.findall(r"^## ", content, re.MULTILINE))
        h3_count = len(re.findall(r"^### ", content, re.MULTILINE))

        if h1_count >= 1:
            score += 15
        if h2_count >= 3:
            score += 25
        elif h2_count >= 1:
            score += 15
        if h3_count >= 3:
            score += 15

        # 章节密度 (每100行至少1个章节)
        if line_count > 0:
            density = sections / (line_count / 100)
            if density >= 1.5:
                score += 20
            elif density >= 1.0:
                score += 15
            elif density >= 0.5:
                score += 10
            else:
                issues.append("章节密度过低")

        # 有列表
        if re.search(r"^[\-\*]\s", content, re.MULTILINE):
            score += 10

        # 有表格
        if re.search(r"\|.*\|.*\|", content):
            score += 15

        return min(score, 100)

    def _score_depth(
        self, content: str, line_count: int, sections: int, code_blocks: int, issues: list
    ) -> float:
        score = 0.0

        # 字数评估
        word_count = len(content)
        if word_count >= 20000:
            score += 40
        elif word_count >= 10000:
            score += 30
        elif word_count >= 5000:
            score += 20
        elif word_count >= 2000:
            score += 10
        else:
            issues.append("内容深度不足")

        # 代码密度 (代码行占比)
        code_line_count = 0
        in_code = False
        for line in content.split("\n"):
            if line.startswith("```"):
                in_code = not in_code
            elif in_code:
                code_line_count += 1
        if line_count > 0:
            code_ratio = code_line_count / line_count
            if code_ratio >= 0.3:
                score += 25
            elif code_ratio >= 0.2:
                score += 20
            elif code_ratio >= 0.1:
                score += 15

        # 技术深度指标 (有原理解释、架构图、性能数据)
        if re.search(r"(原理|principle|internals|底层|实现)", content, re.IGNORECASE):
            score += 15
        if re.search(r"(性能|performance|benchmark|基准测试|延迟|吞吐)", content, re.IGNORECASE):
            score += 10
        if re.search(r"(架构|architecture|设计模式|design.?pattern)", content, re.IGNORECASE):
            score += 10

        return min(score, 100)

    def _score_agent_ready(self, content: str, has_agent_checklist: bool, issues: list) -> float:
        score = 0.0

        # Agent Checklist
        if has_agent_checklist:
            score += 40
        else:
            issues.append("缺少 Agent Checklist")

        # 明确的 DO/DON'T 指令
        if re.search(r"(✅|✓|DO:|MUST:|SHALL:)", content):
            score += 15
        if re.search(r"(❌|✗|DON'T|MUST NOT|SHALL NOT)", content):
            score += 15

        # 检查项/清单格式
        checkbox_count = len(re.findall(r"- \[[ x]\]", content))
        if checkbox_count >= 5:
            score += 15
        elif checkbox_count >= 1:
            score += 10

        # 分层标记 (immutable/iterable/strategy)
        if re.search(
            r"(immutable|不可变|固定标准|iterable|可迭代|strategy|策略)", content, re.IGNORECASE
        ):
            score += 15

        return min(score, 100)

    def score_all(self, domain_filter: str | None = None) -> list[KnowledgeScore]:
        """评估所有知识文件"""
        scores = []
        for md_file in sorted(self.knowledge_dir.rglob("*.md")):
            if domain_filter:
                rel = md_file.relative_to(self.knowledge_dir)
                if not str(rel).startswith(domain_filter):
                    continue
            try:
                score = self.score_file(md_file)
                scores.append(score)
            except Exception as e:
                print(f"Error scoring {md_file}: {e}", file=sys.stderr)
        return scores

    def generate_report(self, scores: list[KnowledgeScore]) -> str:
        """生成质量报告"""
        keep = [s for s in scores if s.status == "keep"]
        improve = [s for s in scores if s.status == "improve"]
        discard = [s for s in scores if s.status == "discard"]

        total = len(scores)
        avg_score = sum(s.total_score for s in scores) / total if total > 0 else 0

        lines = [
            "# 知识库质量评分报告",
            "",
            f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**评估文件数**: {total}",
            f"**平均质量分**: {avg_score:.1f}/100",
            "",
            "## 质量分布",
            "",
            "| 状态 | 数量 | 占比 | 阈值 |",
            "|------|------|------|------|",
            (
                f"| ✅ Keep (生产可用) | {len(keep)} | {len(keep)/total*100:.0f}% | >= {self.THRESHOLD_KEEP} |"
                if total > 0
                else ""
            ),
            (
                f"| ⚠️ Improve (需改进) | {len(improve)} | {len(improve)/total*100:.0f}% | {self.THRESHOLD_IMPROVE}-{self.THRESHOLD_KEEP-1} |"
                if total > 0
                else ""
            ),
            (
                f"| ❌ Discard (需重写) | {len(discard)} | {len(discard)/total*100:.0f}% | < {self.THRESHOLD_IMPROVE} |"
                if total > 0
                else ""
            ),
            "",
        ]

        # 各领域评分
        domain_scores: dict[str, list] = {}
        for s in scores:
            domain_scores.setdefault(s.domain, []).append(s)

        lines.append("## 各领域质量")
        lines.append("")
        lines.append("| 领域 | 文件数 | 平均分 | Keep | Improve | Discard |")
        lines.append("|------|--------|--------|------|---------|---------|")
        for domain in sorted(domain_scores.keys()):
            ds = domain_scores[domain]
            d_avg = sum(s.total_score for s in ds) / len(ds)
            d_keep = sum(1 for s in ds if s.status == "keep")
            d_improve = sum(1 for s in ds if s.status == "improve")
            d_discard = sum(1 for s in ds if s.status == "discard")
            lines.append(
                f"| {domain} | {len(ds)} | {d_avg:.1f} | {d_keep} | {d_improve} | {d_discard} |"
            )

        # 需要改进的文件列表
        lines.append("")
        lines.append("## 需要改进的文件 (按分数排序)")
        lines.append("")
        for s in sorted(scores, key=lambda x: x.total_score):
            if s.status != "keep":
                issues_str = "; ".join(s.issues[:3]) if s.issues else "无"
                lines.append(f"- **{s.total_score:.0f}分** `{s.file_path}` — {issues_str}")

        return "\n".join(lines)

    def generate_tsv(self, scores: list[KnowledgeScore]) -> str:
        """生成 results.tsv"""
        header = "file\ttotal\tcompleteness\texecutability\tstructure\tdepth\tagent_ready\tstatus\tlines\tcode_blocks\tissues"
        rows = [header]
        for s in sorted(scores, key=lambda x: -x.total_score):
            issues = "; ".join(s.issues[:3]) if s.issues else ""
            rows.append(
                f"{s.file_path}\t{s.total_score}\t{s.completeness}\t{s.executability}\t"
                f"{s.structure}\t{s.depth}\t{s.agent_ready}\t{s.status}\t"
                f"{s.line_count}\t{s.code_blocks}\t{issues}"
            )
        return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description="Super Dev 知识库质量评分器")
    parser.add_argument("--domain", type=str, help="只评估指定领域")
    parser.add_argument("--min-score", type=int, default=0, help="只显示低于此分数的文件")
    parser.add_argument("--output", type=str, help="输出TSV文件名（不含扩展名）")
    parser.add_argument("--report", action="store_true", help="生成Markdown报告")
    parser.add_argument("--knowledge-dir", type=str, default="knowledge", help="知识库目录")
    args = parser.parse_args()

    scorer = KnowledgeScorer(args.knowledge_dir)
    scores = scorer.score_all(args.domain)

    if not scores:
        print("没有找到知识文件")
        return

    # 过滤
    if args.min_score > 0:
        scores = [s for s in scores if s.total_score < args.min_score]

    # 输出 TSV
    if args.output:
        tsv = scorer.generate_tsv(scores)
        tsv_path = f"{args.output}.tsv"
        with open(tsv_path, "w", encoding="utf-8") as f:
            f.write(tsv)
        print(f"TSV saved to {tsv_path}")

    # 输出报告
    if args.report:
        report = scorer.generate_report(scores)
        report_path = "output/knowledge-quality-report.md"
        os.makedirs("output", exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to {report_path}")

    # 控制台摘要
    total = len(scores)
    keep = sum(1 for s in scores if s.status == "keep")
    improve = sum(1 for s in scores if s.status == "improve")
    discard = sum(1 for s in scores if s.status == "discard")
    avg = sum(s.total_score for s in scores) / total if total > 0 else 0

    print(f"\n{'='*60}")
    print(" 知识库质量评分摘要")
    print(f"{'='*60}")
    print(f" 评估文件: {total}")
    print(f" 平均分数: {avg:.1f}/100")
    print(f" ✅ Keep:    {keep} ({keep/total*100:.0f}%)" if total > 0 else "")
    print(f" ⚠️  Improve: {improve} ({improve/total*100:.0f}%)" if total > 0 else "")
    print(f" ❌ Discard: {discard} ({discard/total*100:.0f}%)" if total > 0 else "")
    print(f"{'='*60}")

    # 显示 Top 10 最高分
    top10 = sorted(scores, key=lambda x: -x.total_score)[:10]
    print("\n Top 10 最高质量:")
    for s in top10:
        print(f"  {s.total_score:5.1f}  {s.status:8s}  {s.file_path}")

    # 显示 Bottom 10 最低分
    bottom10 = sorted(scores, key=lambda x: x.total_score)[:10]
    print("\n Bottom 10 最低质量:")
    for s in bottom10:
        issues_str = "; ".join(s.issues[:2]) if s.issues else ""
        print(f"  {s.total_score:5.1f}  {s.status:8s}  {s.file_path}  [{issues_str}]")


if __name__ == "__main__":
    main()
