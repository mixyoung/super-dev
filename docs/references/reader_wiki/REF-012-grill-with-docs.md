---
id: "REF-012"
title: "ZSL / Grill with Docs: 极限需求深度盘问与回读澄清法"
category: "技能与角色库；开发框架与流程"
status: "已参考·部分吸收"
upstream_url: "https://superpowers.zsl.dev/skills/grill-with-docs/"
fixed_baseline: "2026-09-06-method-spec"
first_audit_date: "2026-09-06"
latest_audit_date: "2026-09-14"
summary: "通过对设计依赖、晦涩词汇、业务边界与架构取舍进行极限盘问（Grill），并强制将澄清结果写回原始文档，带着争议场景回读。"
key_methods: ["grill-with-docs"]
ai_generated: false
verified_by: "mixyoung"
tags: ["requirements", "grill", "interview", "clarification"]
---

# REF-012: ZSL / Grill with Docs

> **定位摘要**：Grill with Docs 是一种被证明极其有效的交互式需求挖掘方法。它要求 AI 放弃一味附和用户的讨好姿态，扮演冷酷的审查者，追问边界与暗含假设，并在达成一致后立刻原地写回设计文档。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [superpowers.zsl.dev/skills/grill-with-docs/](https://superpowers.zsl.dev/skills/grill-with-docs/) |
| **固定基线** | 2026-09-06 方法说明快照（未固定 git commit） |
| **参考状态** | 🟢 **已参考·部分吸收**（吸收盘问思想、写回文档与争议回读，已落入 PM/ARCHITECT 定义） |
| **原始剪藏** | [raw_sources/REF-012-grill-with-docs/README.md](../raw_sources/REF-012-grill-with-docs/README.md) |
| **决策记录** | [decisions/ADR-REF-012-grill-with-docs-absorption.md](../decisions/ADR-REF-012-grill-with-docs-absorption.md) |

---

## 2. 核心技术调研与深度分析 (What & How)

### 2.1 针对的工程痛点
- 很多时候架构师或用户写的设计文档看起来很完备，但实际上充满了模糊用词（如“必要时”、“合理重试”、“高性能同步”）；
- 如果不加以追问，不同角色（前端、后端、测试）会各自按照自己的理解去实现，在集成时必然大崩盘。

### 2.2 盘问三步法
1. **挑刺（Interrogate）**：抓住模糊动词、隐含边界与未定义状态进行多轮穷追猛打；
2. **决断（Decide）**：强迫用户在互斥方案之间做单选，不接受“都要”；
3. **回写与回读（Write-back & Re-read）**：将决断原地写回文档，并以极端争议场景反复测试文档表述。

---

## 3. 提炼出的通用方法论 (Extracted Methods)

- 📖 [极限需求澄清与文档回写盘问法 (grill-with-docs)](./methods/grill-with-docs.md)
