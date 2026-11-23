---
id: "REF-005"
title: "Matt Pocock Skills: 智能体高效写作与工程复盘技巧"
category: "技能与角色库"
status: "已参考·部分吸收"
upstream_url: "https://github.com/mattpocock/skills"
fixed_baseline: "3cca18b368ae95cdbdebbff572ccafa662551015"
first_audit_date: "2026-09-12"
latest_audit_date: "2026-10-05"
summary: "提供高质量的生产力与工程技能，强调按需限定阅读条件以节省智能体上下文（Writing for Agents），以及用确定性检查代替繁琐流程的复盘法（Retro）。"
key_methods: ["writing-for-agents", "engineering-retro"]
ai_generated: false
verified_by: "mixyoung"
tags: ["skills", "productivity", "context-engineering", "retro"]
---

# REF-005: Matt Pocock Skills

> **定位摘要**：Matt Pocock 维护的技能库以极高的实用性和对 LLM 行为的敏锐洞察著称。本项目核心吸收其在**上下文工程（Context Engineering）**方面的指导——特别是“明确给出阅读条件，避免全量文件倾倒”，以及“遇到故障优先加确定性脚本，不建官僚平台”。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/mattpocock/skills](https://github.com/mattpocock/skills) |
| **固定基线** | `v1.3.1` / [`3cca18b`](https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015)（2026-10-05 复核） |
| **参考状态** | 🟢 **已参考·部分吸收**（吸收特定段落指导，不把 ZSL Grill 采用历史混入） |
| **原始剪藏** | [raw_sources/REF-005-matt-pocock-skills/README.md](../raw_sources/REF-005-matt-pocock-skills/README.md) |
| **决策记录** | [decisions/ADR-REF-005-matt-pocock-skills-boundaries.md](../decisions/ADR-REF-005-matt-pocock-skills-boundaries.md) |

---

## 2. 核心技术调研与深度分析 (What & How)

### 2.1 Writing for Agents（给智能体的高效引用）
- **核心观点**：不要直接告诉 Agent“去读 `doc.md`”，而是必须指明“当遇到 [特定条件] 时，阅读 `doc.md` 中的 [第 X 节]”。
- **价值**：极大减少不必要的 Token 消耗，防止无关长文挤占模型的短期记忆窗口。

### 2.2 Retro（工程复盘法）
- **核心观点**：复盘的核心产物必须是“可落地的代码或自动化检查”。如果一次事故发生，复盘结论只是“以后大家要更加小心”，复盘就是失败的。必须优先增加一条 linter、测试或静态断言。

---

## 3. 关键技术取舍速查 (Trade-off Summary)

- ✅ **已吸收**：按需引用指导、确定性检查替代繁文缛节。
- 🛑 **坚决拒绝**：
  1. 不引入其专有的提示词管理生态；
  2. 严格核实来源关系，不将未证实的第三方技能合并入本项目。
