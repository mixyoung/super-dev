#!/usr/bin/env python3
"""
check_reference_updates.py

Super Dev 外部参考源周期性巡检与差异捕获脚本。
读取 docs/references/.upstream_tracking.json，检查 GitHub 仓库最新 Commit 与 Release，
基于路径白名单与关键字进行智能初筛，生成结构化 Markdown 巡检报告。

零外部依赖，使用 Python 标准库运行。
"""

import argparse
import fnmatch
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


def get_headers(token: str | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": "SuperDev-ReferenceWatcher/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def http_get_json(url: str, token: str | None = None) -> tuple[Any | None, str | None]:
    req = urllib.request.Request(url, headers=get_headers(token))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data, None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"Network error: {e.reason}"
    except Exception as e:
        return None, str(e)


def matches_any_pattern(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if pat.endswith("/"):
            if path.startswith(pat) or f"/{pat}" in path:
                return True
        elif fnmatch.fnmatch(path, pat):
            return True
        elif pat in path:
            return True
    return False


def classify_changes(
    files: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    watch_paths: list[str],
    ignore_paths: list[str],
) -> tuple[str, str, list[str]]:
    """
    分类变更:
    - actionable (🟢 建议跟进)
    - watch (🟡 挂起观察)
    - ignored (⚪ 忽略)
    """
    touched_watch = []
    touched_ignore_only = True

    for f in files:
        filename = f.get("filename", "")
        if matches_any_pattern(filename, watch_paths):
            touched_watch.append(filename)
            touched_ignore_only = False
        elif not matches_any_pattern(filename, ignore_paths):
            touched_ignore_only = False

    if not files:
        return "ignored", "无文件变更", []

    if touched_ignore_only or (files and not touched_watch):
        return "ignored", "变更仅涉及 CI/测试/文档格式等忽略项，无需跟进", []

    # 分析提交信息中是否包含核心功能词汇
    actionable_keywords = [
        "feat", "breaking", "spec", "rule", "prompt", "skill",
        "method", "architecture", "contract", "v[0-9]"
    ]
    has_key_feature = False
    for c in commits:
        msg = c.get("commit", {}).get("message", "").lower()
        if any(kw in msg for kw in actionable_keywords):
            has_key_feature = True
            break

    if has_key_feature or len(touched_watch) >= 3:
        reason = f"命中了核心关注路径 ({len(touched_watch)} 个文件) 且包含重要方法/功能演化"
        return "actionable", reason, touched_watch

    return "watch", f"涉及关注路径 ({len(touched_watch)} 个文件)，建议列入日常观察清单", touched_watch


def inspect_source(
    source_id: str,
    meta: dict[str, Any],
    token: str | None = None,
) -> dict[str, Any]:
    name = meta.get("name", source_id)
    stype = meta.get("type", "unknown")

    result = {
        "id": source_id,
        "name": name,
        "type": stype,
        "status": "up_to_date",
        "message": "已是最新基线",
        "new_commit": None,
        "old_commit": meta.get("last_checked_commit"),
        "commits_count": 0,
        "commits": [],
        "files_changed": [],
        "details": "",
    }

    if stype == "unconfirmed":
        result["status"] = "unconfirmed"
        result["message"] = meta.get("status_note", "身份待核实，跳过自动抓取")
        return result

    if stype == "web_document":
        result["status"] = "web_document"
        result["message"] = f"文档站静态页面，上次基线日期: {meta.get('last_checked_date', '-')}"
        return result

    if stype != "github_repo":
        result["status"] = "skipped"
        result["message"] = f"未知来源类型: {stype}"
        return result

    repo = meta.get("repo")
    branch = meta.get("track_branch", "main")
    old_commit = meta.get("last_checked_commit")

    if not repo:
        result["status"] = "error"
        result["message"] = "未配置 repo 字段"
        return result

    # 1. 查询分支最新 commit
    commit_url = f"https://api.github.com/repos/{repo}/commits/{branch}"
    commit_data, err = http_get_json(commit_url, token)

    if err:
        result["status"] = "error"
        result["message"] = f"查询最新提交失败: {err}"
        return result

    latest_sha = commit_data.get("sha")
    result["new_commit"] = latest_sha

    if not old_commit or latest_sha == old_commit or latest_sha.startswith(old_commit) or old_commit.startswith(latest_sha):
        result["status"] = "up_to_date"
        result["message"] = f"当前已对齐基线 ({latest_sha[:7]})"
        return result

    # 2. 调用 compare API 查看差异
    compare_url = f"https://api.github.com/repos/{repo}/compare/{old_commit}...{latest_sha}"
    compare_data, err = http_get_json(compare_url, token)

    if err:
        result["status"] = "has_updates"
        result["message"] = f"发现新提交 ({latest_sha[:7]})，但 compare API 调用失败: {err}"
        return result

    total_commits = compare_data.get("total_commits", 0)
    commits_list = compare_data.get("commits", [])
    files_list = compare_data.get("files", [])

    watch_paths = meta.get("watch_paths", [])
    ignore_paths = meta.get("ignore_paths", [])

    category, reason, touched_files = classify_changes(files_list, commits_list, watch_paths, ignore_paths)

    result["status"] = category
    result["message"] = reason
    result["commits_count"] = total_commits
    result["commits"] = [
        {
            "sha": c.get("sha", "")[:7],
            "message": c.get("commit", {}).get("message", "").split("\n")[0],
            "author": c.get("commit", {}).get("author", {}).get("name", "unknown"),
            "date": c.get("commit", {}).get("author", {}).get("date", ""),
        }
        for c in commits_list[:5]  # 最多保留前 5 条
    ]
    result["files_changed"] = touched_files
    return result


def render_markdown_report(results: list[dict[str, Any]], check_time: str) -> str:
    total = len(results)
    actionable = [r for r in results if r["status"] == "actionable"]
    watch = [r for r in results if r["status"] == "watch"]
    ignored = [r for r in results if r["status"] == "ignored"]
    up_to_date = [r for r in results if r["status"] == "up_to_date"]
    others = [r for r in results if r["status"] in ("unconfirmed", "web_document", "error")]

    lines = []
    lines.append("# 🔍 Super Dev 外部参考源上游巡检报告")
    lines.append(f"\n> **巡检时间**：`{check_time}` | **检查来源总数**：{total} 个")
    lines.append(f"> **状态概览**：🟢 建议跟进 `{len(actionable)}` 个 | 🟡 观察挂起 `{len(watch)}` 个 | ⚪ 忽略更新 `{len(ignored)}` 个 | ✅ 已是最新 `{len(up_to_date)}` 个 | ⚠️ 其他/待核 `{len(others)}` 个\n")

    lines.append("## 1. 巡检结果总览表\n")
    lines.append("| 来源 ID | 名称 | 上游状态 | 变更摘要 / 判定理由 | 新提交 SHA |")
    lines.append("| :--- | :--- | :---: | :--- | :---: |")

    status_badges = {
        "actionable": "🟢 建议跟进",
        "watch": "🟡 观察暂缓",
        "ignored": "⚪ 忽略更新",
        "up_to_date": "✅ 已是最新",
        "unconfirmed": "⚠️ 待核实",
        "web_document": "📄 静态文档",
        "error": "❌ 抓取失败",
    }

    for r in results:
        badge = status_badges.get(r["status"], r["status"])
        sha_str = f"`{r['new_commit'][:7]}`" if r.get("new_commit") else "-"
        msg = r["message"].replace("|", "\\|")
        lines.append(f"| **{r['id']}** | {r['name']} | {badge} | {msg} | {sha_str} |")

    if actionable:
        lines.append("\n## 2. 🟢 建议跟进项详细审查 (Actionable Items)\n")
        for r in actionable:
            lines.append(f"### {r['id']} - {r['name']}\n")
            lines.append(f"- **判定理由**：{r['message']}")
            lines.append(f"- **基线对比**：`{r['old_commit'][:7]}` ──> `{r['new_commit'][:7]}` (共领先 {r['commits_count']} 次提交)")
            if r["files_changed"]:
                lines.append("- **命中关注路径**：")
                for f in r["files_changed"][:10]:
                    lines.append(f"  - `{f}`")
            if r["commits"]:
                lines.append("- **最新提交摘要**：")
                for c in r["commits"]:
                    lines.append(f"  - [`{c['sha']}`] {c['message']} *(by {c['author']} at {c['date']})*")
            lines.append("- **建议动作**：")
            lines.append("  1. 在 `mixyoung/reference-updates` 分支由维护者人工阅读上述差异；")
            lines.append("  2. 如确实具有工程价值，按标准流程追加 `docs/REFERENCE_UPDATES.md` 台账并更新 `docs/references/` 下的实体与 ADR。")
            lines.append("")

    lines.append("\n## 3. 贡献准则守卫备忘\n")
    lines.append("> ⚠️ **重要守则**：自动化巡检仅具备**探测、初筛与建议权**。新版本并不自动意味着需要吸纳，任何正式代码或方法论吸收必须遵循 `docs/CONTRIBUTION_POLICY.md` 并在明确授权的 change 中实施，严禁自动合并或静默变更。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Super Dev 外部参考源更新检查器")
    parser.add_argument(
        "--config",
        default="docs/references/.upstream_tracking.json",
        help="配置文件路径 (默认: docs/references/.upstream_tracking.json)",
    )
    parser.add_argument(
        "--output-report",
        default="",
        help="Markdown 报告输出路径 (可选，如 output/reference-scan-latest.md)",
    )
    parser.add_argument(
        "--source",
        default="",
        help="指定仅检查单个来源 ID (如 REF-014)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="是否自动将已检测到的最新提交写回配置文件基线",
    )
    args = parser.parse_args()

    config_path = os.path.normpath(args.config)
    if not os.path.exists(config_path):
        print(f"[ERROR] 配置文件未找到: {config_path}")
        sys.exit(1)

    with open(config_path, encoding="utf-8") as fp:
        config = json.load(fp)

    sources = config.get("sources", {})
    token = os.environ.get("GITHUB_TOKEN")

    print(f"[*] 开始检查参考源更新 (共 {len(sources)} 个登记项)...")
    if token:
        print("[*] 已检测到 GITHUB_TOKEN，使用鉴权 API 调用。")
    else:
        print("[!] 未检测到 GITHUB_TOKEN，使用公开匿名 API (可能受速率限制)。")

    results = []
    target_ids = [args.source] if args.source else list(sources.keys())

    for sid in target_ids:
        if sid not in sources:
            print(f"[!] 警告: 来源 {sid} 不在配置列表中")
            continue
        meta = sources[sid]
        print(f" -> 正在检查 {sid} ({meta.get('name')})...", end="", flush=True)
        res = inspect_source(sid, meta, token)
        results.append(res)
        print(f" [{res['status'].upper()}] - {res['message']}")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 是否写回基线
    if args.update_baseline:
        updated_count = 0
        for r in results:
            if r.get("new_commit") and r["status"] in ("actionable", "watch", "ignored"):
                sources[r["id"]]["last_checked_commit"] = r["new_commit"]
                sources[r["id"]]["last_checked_date"] = now_iso.split(" ")[0]
                updated_count += 1
        config["last_check_time"] = now_iso
        with open(config_path, "w", encoding="utf-8") as fp:
            json.dump(config, fp, indent=2, ensure_ascii=False)
            fp.write("\n")
        print(f"[+] 已将 {updated_count} 个最新提交更新写回 {config_path}")

    # 生成 Markdown 报告
    report_md = render_markdown_report(results, now_iso)

    if args.output_report:
        out_path = os.path.normpath(args.output_report)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fp:
            fp.write(report_md)
            fp.write("\n")
        print(f"[+] 报告已写入: {out_path}")

    # GitHub Actions output
    has_actionable = any(r["status"] == "actionable" for r in results)
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output and os.path.exists(gh_output):
        with open(gh_output, "a", encoding="utf-8") as fp:
            fp.write(f"has_actionable={'true' if has_actionable else 'false'}\n")

    # GitHub Actions Step Summary (直接在线渲染，无需下载解压 zip)
    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_summary and os.path.exists(gh_summary):
        with open(gh_summary, "a", encoding="utf-8") as fp:
            fp.write(report_md)
            fp.write("\n")

    print("\n[✓] 巡检完成！")
    print(f"    - 建议跟进: {sum(1 for r in results if r['status'] == 'actionable')}")
    print(f"    - 观察暂缓: {sum(1 for r in results if r['status'] == 'watch')}")
    print(f"    - 忽略变更: {sum(1 for r in results if r['status'] == 'ignored')}")
    print(f"    - 已是最新: {sum(1 for r in results if r['status'] == 'up_to_date')}")


if __name__ == "__main__":
    main()
