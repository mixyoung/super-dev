#!/usr/bin/env python3
"""
知识引用追踪 — 命令行报告工具

查看项目的知识引用报告、历史趋势和覆盖率。

用法:
    python scripts/knowledge_tracker_report.py --project myapp        # 查看某项目最新引用报告
    python scripts/knowledge_tracker_report.py --trend                # 查看知识引用趋势
    python scripts/knowledge_tracker_report.py --trend --project myapp  # 查看某项目的趋势
    python scripts/knowledge_tracker_report.py --coverage             # 查看当前知识覆盖率
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _find_history_files(
    metrics_dir: Path,
    project: str | None = None,
) -> list[Path]:
    """查找 metrics-history 下的知识追踪 JSON 文件，按时间戳排序"""
    if not metrics_dir.exists():
        return []

    pattern = "*-knowledge-tracking-*.json"
    files = sorted(metrics_dir.glob(pattern))

    if project:
        files = [f for f in files if f.name.startswith(f"{project}-knowledge-tracking-")]

    return files


def _load_json(filepath: Path) -> dict:
    """安全加载 JSON 文件"""
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [警告] 无法读取 {filepath}: {exc}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# 子命令实现
# ---------------------------------------------------------------------------


def cmd_project(args: argparse.Namespace) -> None:
    """查看某项目的最新知识引用报告"""
    metrics_dir = Path(args.output_dir) / "metrics-history"
    files = _find_history_files(metrics_dir, project=args.project)

    if not files:
        print(f"未找到项目 '{args.project}' 的知识引用报告。")
        print(f"  查找目录: {metrics_dir}")
        sys.exit(1)

    latest = files[-1]
    data = _load_json(latest)
    if not data:
        sys.exit(1)

    summary = data.get("summary", {})
    print("=" * 60)
    print(f"  知识引用报告 — {data.get('project_name', '?')}")
    print("=" * 60)
    print(f"  Run ID:      {data.get('pipeline_run_id', '?')}")
    print(f"  时间:        {data.get('timestamp', '?')}")
    print(f"  知识总文件:  {summary.get('total_knowledge_files', 0)}")
    print(f"  引用文件:    {summary.get('referenced_files', 0)}")
    print(f"  命中率:      {summary.get('hit_rate', 0):.1%}")
    print(f"  总引用次数:  {summary.get('total_references', 0)}")
    print()

    # 领域覆盖率
    coverage = data.get("coverage_by_domain", {})
    if coverage:
        print("  领域覆盖率:")
        print(f"  {'领域':<20} {'总计':>6} {'引用':>6} {'覆盖率':>8}")
        print("  " + "-" * 44)
        for domain in sorted(coverage):
            info = coverage[domain]
            rate = info.get("rate", 0)
            bar = "█" * int(rate * 10) + "░" * (10 - int(rate * 10))
            print(
                f"  {domain:<20} {info.get('total', 0):>6} "
                f"{info.get('referenced', 0):>6} {rate:>7.0%} {bar}"
            )
        print()

    # 未引用领域
    unreferenced = data.get("unreferenced_domains", [])
    if unreferenced:
        print(f"  未引用领域 ({len(unreferenced)}):")
        for d in sorted(unreferenced):
            print(f"    - {d}")
        print()

    # 引用明细（前 10 条）
    refs = data.get("references", [])
    if refs:
        show_count = min(len(refs), 10)
        print(f"  引用明细（最近 {show_count} 条，共 {len(refs)} 条）:")
        print(f"  {'#':>3} {'阶段':<12} {'类型':<12} {'相关性':>6}  文件")
        print("  " + "-" * 70)
        for i, ref in enumerate(refs[:show_count], 1):
            print(
                f"  {i:>3} {ref.get('phase', '?'):<12} "
                f"{ref.get('usage_type', '?'):<12} "
                f"{ref.get('relevance_score', 0):>5.2f}  "
                f"{ref.get('knowledge_file', '?')}"
            )
        if len(refs) > show_count:
            print(f"  ... 还有 {len(refs) - show_count} 条，查看完整报告请打开 Markdown 文件。")
        print()

    # Markdown 文件位置
    md_path = Path(args.output_dir) / f"{args.project}-knowledge-tracking.md"
    if md_path.exists():
        print(f"  完整 Markdown 报告: {md_path}")

    print(f"  JSON 数据: {latest}")


def cmd_trend(args: argparse.Namespace) -> None:
    """查看知识引用趋势"""
    metrics_dir = Path(args.output_dir) / "metrics-history"
    files = _find_history_files(metrics_dir, project=args.project)

    if not files:
        label = f"项目 '{args.project}' 的" if args.project else ""
        print(f"未找到{label}知识引用历史数据。")
        print(f"  查找目录: {metrics_dir}")
        sys.exit(1)

    print("=" * 60)
    title = f"知识引用趋势 — {args.project}" if args.project else "知识引用趋势（全部项目）"
    print(f"  {title}")
    print("=" * 60)
    print()
    print(f"  {'#':>3} {'日期':<22} {'项目':<16} {'引用':>4} {'命中率':>7}  趋势")
    print("  " + "-" * 65)

    prev_rate: float | None = None
    for i, filepath in enumerate(files, 1):
        data = _load_json(filepath)
        if not data:
            continue

        summary = data.get("summary", {})
        project_name = data.get("project_name", "?")
        timestamp = data.get("timestamp", "?")[:19]
        referenced = summary.get("referenced_files", 0)
        hit_rate = summary.get("hit_rate", 0.0)

        # 趋势指示
        if prev_rate is not None:
            if hit_rate > prev_rate + 0.01:
                trend = "^ UP"
            elif hit_rate < prev_rate - 0.01:
                trend = "v DOWN"
            else:
                trend = "= FLAT"
        else:
            trend = "-"

        print(
            f"  {i:>3} {timestamp:<22} {project_name:<16} "
            f"{referenced:>4} {hit_rate:>6.1%}  {trend}"
        )
        prev_rate = hit_rate

    print()
    print(f"  共 {len(files)} 条历史记录")


def cmd_coverage(args: argparse.Namespace) -> None:
    """查看当前知识库覆盖率（基于最新报告或实时扫描）"""
    # 先尝试从最新报告读取
    metrics_dir = Path(args.output_dir) / "metrics-history"
    files = _find_history_files(metrics_dir, project=args.project)

    if files:
        data = _load_json(files[-1])
        coverage = data.get("coverage_by_domain", {})
        source_label = f"来源: {files[-1].name}"
    else:
        # 无历史数据时，实时扫描知识目录
        from super_dev.knowledge_tracker import KnowledgeTracker

        tracker = KnowledgeTracker(knowledge_dir=args.knowledge_dir)
        coverage_raw = tracker.get_knowledge_coverage()
        coverage = {
            d: {"total": v["total"], "referenced": 0, "rate": 0.0} for d, v in coverage_raw.items()
        }
        source_label = f"实时扫描: {args.knowledge_dir}"

    if not coverage:
        print("未找到知识库数据。")
        sys.exit(1)

    print("=" * 60)
    print("  知识库覆盖率概览")
    print("=" * 60)
    print(f"  {source_label}")
    print()

    total_files = sum(v.get("total", 0) for v in coverage.values())
    total_referenced = sum(v.get("referenced", 0) for v in coverage.values())
    overall_rate = total_referenced / total_files if total_files > 0 else 0.0

    print(f"  总文件: {total_files}  引用: {total_referenced}  整体覆盖率: {overall_rate:.1%}")
    print()

    print(f"  {'领域':<20} {'总计':>6} {'引用':>6} {'覆盖率':>8}  可视化")
    print("  " + "-" * 56)

    for domain in sorted(coverage):
        info = coverage[domain]
        total = info.get("total", 0)
        referenced = info.get("referenced", 0)
        rate = info.get("rate", 0.0)
        bar_len = 20
        filled = int(rate * bar_len)
        bar = "#" * filled + "." * (bar_len - filled)
        print(f"  {domain:<20} {total:>6} {referenced:>6} {rate:>7.0%}  [{bar}]")

    print()

    # 未覆盖领域警告
    uncovered = [d for d, v in coverage.items() if v.get("referenced", 0) == 0]
    if uncovered:
        print(f"  [提示] {len(uncovered)} 个领域尚未被引用:")
        for d in sorted(uncovered):
            print(f"    - {d}")
        print()


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="知识引用追踪报告工具 — 查看项目知识引用、趋势和覆盖率",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  %(prog)s --project myapp        查看 myapp 的最新引用报告\n"
            "  %(prog)s --trend                 查看所有项目的引用趋势\n"
            "  %(prog)s --trend --project myapp 查看 myapp 的引用趋势\n"
            "  %(prog)s --coverage              查看知识库覆盖率\n"
        ),
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="项目名称（用于过滤报告）",
    )
    parser.add_argument(
        "--trend",
        action="store_true",
        default=False,
        help="查看知识引用趋势",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        default=False,
        help="查看知识库覆盖率",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="输出目录路径（默认: output）",
    )
    parser.add_argument(
        "--knowledge-dir",
        type=str,
        default="knowledge",
        help="知识库目录路径（默认: knowledge）",
    )
    return parser


def main() -> None:
    """CLI 入口"""
    parser = build_parser()
    args = parser.parse_args()

    if args.trend:
        cmd_trend(args)
    elif args.coverage:
        cmd_coverage(args)
    elif args.project:
        cmd_project(args)
    else:
        parser.print_help()
        print()
        print("请指定 --project <name>、--trend 或 --coverage 中的至少一个选项。")
        sys.exit(1)


if __name__ == "__main__":
    main()
