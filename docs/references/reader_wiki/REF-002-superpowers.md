---
id: "REF-002"
title: "Superpowers: 严谨可验证的智能体开发工作流"
category: "开发框架与流程；技能与角色库"
status: "已参考·部分吸收"
upstream_url: "https://github.com/obra/superpowers"
fixed_baseline: "b36e0829c6d0140e93cfef2ca599b1b07d4a7797"
first_audit_date: "2026-09-12"
latest_audit_date: "2026-10-05"
summary: "提供一套被广泛验证的 AI 辅助软件工程方法论，包括系统化假设驱动调试、红绿重构 TDD、任务完成与新鲜证据强绑定及可审查计划。"
key_methods: ["systematic-debugging", "test-driven-development", "verification-before-completion"]
ai_generated: false
verified_by: "mixyoung"
tags: ["workflow", "debugging", "tdd", "verification", "planning"]
---

# REF-002: Superpowers

> **定位摘要**：由 Jesse Vincent 开源的 Superpowers 是一套强调“确定性与可验证性”的 AI 编程技能集合。它约束了智能体最容易犯的“凭直觉胡乱改代码”和“未经验证擅自宣布完成”两大弊病，确立了“单一假设验证”与“新鲜证据绑定”的现代 Agent 铁律。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/obra/superpowers](https://github.com/obra/superpowers) |
| **固定基线** | `v6.4.2` / [`b36e082`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797)（2026-10-05 复核） |
| **参考状态** | 🟢 **已参考·部分吸收**（吸收方法论与流程边界约束，不整套安装技能） |
| **原始剪藏** | [raw_sources/REF-002-superpowers/README.md](../raw_sources/REF-002-superpowers/README.md) |
| **决策记录** | [decisions/ADR-REF-002-superpowers-boundaries.md](../decisions/ADR-REF-002-superpowers-boundaries.md) |

---

## 2. 核心技术调研与深度分析 (What & How)

### 2.1 针对的工程痛点
- **散弹枪调试（Shotgun Debugging）**：AI 遇到报错时一次性改动 5 个文件，引入更多未测试的变量；
- **过早庆祝（Premature Completion）**：代码写完就宣称“已修复”，实际上连命令都没跑过；
- **没有边界的重构**：重构时缺乏先行的失败测试，导致静默破坏既有功能。

### 2.2 核心机制
1. **Systematic Debugging（系统化假设驱动调试）**：
   - 必须先提出单一明确假设；
   - 编写最小实验复现该失败；
   - 亲眼看到预期的失败现象后，方可着手修复；
   - 修复后确保无侧面破损。
2. **Verification before Completion（完成前证据绑定）**：
   - 任务完成声明必须附带当轮刚生成的真实终端输出；
   - 没有执行命令的通过声明一律判定为无效。
3. **Writing Plans（保留接口与验收的计划法）**：
   - 计划不仅仅是步骤清单，必须保留关键接口定义、关键决策依据和阶段验收条件。

---

## 3. 提炼出的通用方法论 (Extracted Methods)

- 📖 [系统化假设驱动调试法 (systematic-debugging)](./methods/systematic-debugging.md)

---

## 4. 关键技术取舍速查 (Trade-off Summary)

- ✅ **已吸收**：单假设调试闭环、严格 TDD 流程、完成前强制绑定新鲜证据、计划保留设计决策。
- 🛑 **坚决拒绝**：
  1. 不引入其技能整包安装（保持 Super Dev 宿主环境轻量）；
  2. 不将所有非功能改动强加多余的仪式性流程。
