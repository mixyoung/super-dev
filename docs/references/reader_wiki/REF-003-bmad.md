---
id: "REF-003"
title: "BMAD Method: 敏捷突破性 AI 开发方法论"
category: "开发框架与流程"
status: "已参考·部分吸收"
upstream_url: "https://github.com/bmad-code-org/BMAD-METHOD"
fixed_baseline: "94b6727b00c8316557828c8a8ff2a48ff60d60cc"
first_audit_date: "2026-09-06"
latest_audit_date: "2026-10-05"
summary: "强调在进入编码前对核心想法进行高烈度反证与假设测试（Forge Idea），按风险动态选择规划路径，并明确阶段交接契约。"
key_methods: ["forge-idea", "planning-path-selection"]
ai_generated: false
verified_by: "mixyoung"
tags: ["methodology", "ideation", "planning", "validation"]
---

# REF-003: BMAD Method

> **定位摘要**：BMAD Method（Breakthrough Method for Agile AI-driven Development）聚焦于研发前期（Upstream Engineering）的严密性。它的灵魂是 **Forge Idea**——在写第一行架构或任务之前，必须用反证法和低成本探针无情敲打原始需求，剥离虚假幻象。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) |
| **官方文档** | [docs.bmad-method.org](https://docs.bmad-method.org/) |
| **固定基线** | `v6.12.0` / [`94b6727`](https://github.com/bmad-code-org/BMAD-METHOD/tree/94b6727b00c8316557828c8a8ff2a48ff60d60cc)（2026-10-05 复核） |
| **参考状态** | 🟢 **已参考·部分吸收**（吸收需求价值判断与反证思想，不引入其团队管理与状态机） |
| **原始剪藏** | [raw_sources/REF-003-bmad/README.md](../raw_sources/REF-003-bmad/README.md) |
| **决策记录** | [decisions/ADR-REF-003-bmad-method-boundaries.md](../decisions/ADR-REF-003-bmad-method-boundaries.md) |

---

## 2. 核心技术调研与深度分析 (What & How)

### 2.1 针对的工程痛点
- 用户提需求时往往带着预设立场的解决方案，直接让 AI 编码容易导致“完美实现了完全没用的东西”；
- 需求在推演过程中不断发现新信息，但 AI 倾向于新起一个独立分支而不是原地修正原需求编号，导致上下文失控。

### 2.2 核心机制：Forge Idea 思想
1. **反证与假设摧毁**：
   - 找出需求中风险最高的那条假设（Riskiest Assumption）；
   - 能否用最低成本的探针/实验证明这个想法是错的？
2. **原地修正与回读**：
   - 当发现新证据推翻了旧推断时，必须原地修正原需求项的描述与编号，并带着争议场景回读；
3. **弹性规划路径**：
   - 根据需求风险高低自适应选择轻量或深度规划，拒绝固定的繁文缛节。

---

## 3. 提炼出的通用方法论 (Extracted Methods)

- 📖 [想法验证与需求审查法 (forge-idea)](./methods/forge-idea.md)

---

## 4. 关键技术取舍速查 (Trade-off Summary)

- ✅ **已吸收**：Forge Idea 价值反证审查、定向修订原需求编号、阶段交接契约。
- 🛑 **坚决拒绝**：
  1. 不引入其外部的多角色代理团队或多 Agent 状态机调度；
  2. 不将规划路径固化为必须机械执行的长流程。
