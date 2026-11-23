---
id: "REF-004"
title: "Agency Agents: 专家角色契约化画像库"
category: "技能与角色库"
status: "已参考·部分吸收"
upstream_url: "https://github.com/msitarzewski/agency-agents"
fixed_baseline: "6d29a9b08785a0e49ffc9818bbdd381164c2df5f"
first_audit_date: "2026-09-12"
latest_audit_date: "2026-09-14"
summary: "将 AI 角色定义从传统的“虚构叙事简历”升级为由输入、输出、权限、停止条件与交接协议构成的可测试工程契约。"
key_methods: ["expert-persona-contracts"]
ai_generated: false
verified_by: "mixyoung"
tags: ["agents", "personas", "contracts", "governance"]
---

# REF-004: Agency Agents

> **定位摘要**：Agency Agents 收集了大量垂直领域的 AI 专家角色提示词。本项目对它的核心技术吸收在于**“专家画像结构的工程化重构”**——剥离花哨的角色背景故事，把专家定义转化为由输入/输出、停止条件和权限构成的严格契约。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) |
| **固定基线** | [`6d29a9b`](https://github.com/msitarzewski/agency-agents/tree/6d29a9b08785a0e49ffc9818bbdd381164c2df5f)（2026-09-12 提取） |
| **参考状态** | 🟢 **已参考·部分吸收**（吸收专家角色画像结构与交接契约，坚决不整包导入其角色人设） |
| **原始剪藏** | [raw_sources/REF-004-agency-agents/README.md](../raw_sources/REF-004-agency-agents/README.md) |
| **决策记录** | [decisions/ADR-REF-004-agency-agents-contracts.md](../decisions/ADR-REF-004-agency-agents-contracts.md) |

---

## 2. 核心技术调研与深度分析 (What & How)

### 2.1 针对的工程痛点
市面上大量 Multi-Agent 框架中的 Prompt 充斥着无效文学修辞，例如：
> “你是一名拥有 20 年硅谷顶尖大厂经验的首席架构师，毕业于斯坦福大学，性格严谨沉稳……”
这类叙事不仅浪费昂贵的上下文 Token，而且没有任何确定性约束，模型依然会产生幻觉。

### 2.2 重构方案：可测试的专家角色契约
我们将角色画像拆解为以下核心工程字段：
1. **Domain & Lenses（评估视角）**：该角色用什么特定视角审视代码或设计；
2. **Input Contracts（预期输入）**：必须提供什么结构化材料；
3. **Output Deliverables（标准产物）**：产生什么格式的文件；
4. **Authority & Ceilings（权限天花板）**：允许读取什么、写入什么，禁止逾越什么权限；
5. **Stop Conditions（停止与交接准则）**：什么条件下必须交出控制权，不得继续自行推演。

---

## 3. 提炼出的通用方法论 (Extracted Methods)

- 📖 [可测试专家画像契约模型 (expert-persona-contracts)](./methods/expert-persona-contracts.md)

---

## 4. 关键技术取舍速查 (Trade-off Summary)

- ✅ **已吸收**：角色画像输入输出约束、权限天花板、交接停止条件。
- 🛑 **坚决拒绝**：
  1. 不直接导入其上百个未经测试的虚构角色提示词；
  2. 拒绝任何无事实依据的拟人化经历。
