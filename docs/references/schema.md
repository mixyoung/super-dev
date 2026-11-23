# 外部参考知识库规范与排版准则 (Schema & Guidelines)

> **定位与愿景**：基于 Karpathy 的 **LLM Wiki** 范式与学术界《Knowledge Compounding》（知识复利）经济学理论，本知识库不追求“单次检索更快”，而是通过三层结构，将每一次对外部项目的调研、试错与技术取舍，永久沉淀为团队在代码仓库中可继承、可审计的数字资产。

---

## 1. 架构分层设计

知识库完全依托项目 Git 进行单向递进维护，严格划分为三大物理层：

```
docs/references/
├── raw_sources/            # 【事实层】不可变的外部原始资料剪藏 (轻量 Markdown)
├── reader_wiki/            # 【知识层】面向人类阅读与复核的高可读性提炼库
└── decisions/              # 【决策层】团队技术选型、吸收取舍与否定记录 (ADR)
```

| 层次 | 目录名 | 核心职责 | 内容特征 | 变动规则 |
| :--- | :--- | :--- | :--- | :--- |
| **事实层** | `raw_sources/` | 忠实记录外部来源原作者表达与原文段落 | 纯文本/Markdown 剪藏，记录固定 commit 快照，严禁大二进制 | 不可变，只追加不篡改 |
| **知识层** | `reader_wiki/` | 提炼来源核心技术、实体画像与通用方法论 | 对人阅读友好，图文表卡片化编排，保留机器可读 Frontmatter | 自进化，随理解深入重构 |
| **决策层** | `decisions/` | 记录“为什么吸收 A”、“为什么坚决拒绝 B” | 采用 ADR 格式，聚焦“技术取舍”与“负向路径/失败经验” | 审慎记录，代表团队裁决 |

---

## 2. 元数据规范 (Frontmatter Schema)

位于 `reader_wiki/` 下的所有实体或方法文档，顶部必须携带以下 YAML Frontmatter，以便 AI 能够毫秒级完成元数据检索：

```yaml
---
id: "REF-XXX" 或 "METH-XXX"     # 唯一标识符
title: "项目或方法名称"
category: "开发框架与流程 | 知识库 | 技能与角色库 | 规范与技术文档 | 宿主与运行平台"
status: "待参考 | 已参考·待吸收 | 已参考·部分吸收 | 已参考·依据引用 | 暂缓/不采用"
upstream_url: "https://github.com/..."
fixed_baseline: "commit-hash 或 tag"
first_audit_date: "YYYY-MM-DD"
latest_audit_date: "YYYY-MM-DD"
summary: "一句话阐明该来源或方法的核心价值与本质。"
key_methods: ["method-slug-1", "method-slug-2"]
ai_generated: false            # 若为 AI 预生成草稿填 true，人工复核后改为 false
verified_by: "审核人用户名"
tags: ["tag1", "tag2"]
---
```

---

## 3. 人类高可读性排版准则 (Human-Friendly Formatting)

为保证团队成员在 GitHub 网页、VS Code 或 Obsidian 中阅读时体验良好，排版必须遵循以下排版纪律：

1. **信息头卡片化**：正文起始处必须有引用块摘要（`> **定位摘要**`）与 3~5 行的关键元数据对比表（官方地址、协议、基线、状态），让人在 10 秒内了解全貌。
2. **结构化分级**：
   - `## 1. 档案速览`：元数据与基本面。
   - `## 2. 核心技术调研`：原理解析与架构闪光点。
   - `## 3. 提炼出的通用方法论`：抽离出的跨项目可用技巧。
   - `## 4. 关联档案与决策`：反向链接到 `raw_sources/`、`methods/` 与 `decisions/`。
3. **视觉提示与符号增强**：
   - 充分利用 GitHub 风格 Alert 提示框（`> [!NOTE]`、`> [!TIP]`、`> [!IMPORTANT]`、`> [!WARNING]`）。
   - 列表明确使用 `✅`（采纳项）与 `🛑`（拒绝/禁忌项），形成强视觉锚点。
4. **轻量与清洁**：禁止引入非标准插件语法，完全遵循 GitHub Flavored Markdown (GFM)。
