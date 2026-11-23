---
id: "REF-013"
title: "skill-creator: 隔离前向盲测与技能分层构建法"
category: "技能与角色库"
status: "已参考·部分吸收"
upstream_url: "身份待核实"
fixed_baseline: "2026-09-06-practice"
first_audit_date: "2026-09-06"
latest_audit_date: "2026-09-11"
summary: "在构建技能时采用隔离前向验证（不预先泄露答案的盲测验证），配合技能分层组织与反向触发限定，确保技能不污染全局。"
key_methods: ["blind-forward-verification"]
ai_generated: false
verified_by: "mixyoung"
tags: ["skill-authoring", "blind-testing", "verification"]
---

# REF-013: skill-creator

> **定位摘要**：skill-creator 沉淀了一套科学创建高质量 AI 技能的方法论。其最大亮点是**隔离前向盲测验证**——在测试编写的技能是否有效时，不能把期望结果预先塞给模型，而必须像真实用户一样按轮提问，观察技能是否能引导模型得出正确结论。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | 待补齐（历史有使用证据，但来源厂商未知，严禁臆测厂商身份） |
| **参考状态** | 🟢 **已参考·部分吸收**（吸收隔离前向验证与技能分层约束） |
| **原始剪藏** | [raw_sources/REF-013-skill-creator/README.md](../raw_sources/REF-013-skill-creator/README.md) |
| **决策记录** | [decisions/ADR-REF-013-skill-creator-identity-and-verification.md](../decisions/ADR-REF-013-skill-creator-identity-and-verification.md) |

---

## 2. 提炼出的通用方法论 (Extracted Methods)

- 📖 [隔离前向盲测验证法 (blind-forward-verification)](./methods/blind-forward-verification.md)
