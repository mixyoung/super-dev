---
id: "REF-007"
title: "Agent Skills: 开放智能体技能分发与目录规范"
category: "规范与技术文档"
status: "已参考·依据引用"
upstream_url: "https://github.com/agentskills/agentskills"
fixed_baseline: "69ef37e9424c0a7ea9dd2293b559e43ec8176379"
first_audit_date: "2026-09-12"
latest_audit_date: "2026-09-12"
summary: "定义了现代智能体技能（Skill）的目录结构、YAML 元数据规范与渐进式按需加载（Progressive Loading）协议。"
key_methods: ["progressive-loading"]
ai_generated: false
verified_by: "mixyoung"
tags: ["specification", "skills", "progressive-loading"]
---

# REF-007: Agent Skills 规范

> **定位摘要**：Agent Skills 规范（agentskills.io）是目前大模型生态中事实上的技能组织标准。它定义了技能如何被打包、元数据如何暴露以及如何通过渐进式加载（Level 1 摘要 -> Level 2 正文 -> Level 3 脚本）节约上下文。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/agentskills/agentskills](https://github.com/agentskills/agentskills) / [agentskills.io](https://agentskills.io/) |
| **固定基线** | [`69ef37e`](https://github.com/agentskills/agentskills/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379)（2026-09-12 提取） |
| **参考状态** | 🔵 **已参考·依据引用**（作为技能格式与元数据解析的规范技术依据） |
| **原始剪藏** | [raw_sources/REF-007-agent-skills/README.md](../raw_sources/REF-007-agent-skills/README.md) |

---

## 2. 核心技术价值

1. **三级渐进加载（Progressive Disclosure）**：
   - Level 1：宿主仅读取 `name` 和 `description`，几乎零 Token 消耗；
   - Level 2：触发特定意图时，才读取 `SKILL.md` 正文；
   - Level 3：明确执行指令时，才调用 `scripts/` 中的代码。
2. **Super Dev 的应用**：Super Dev 的各宿主适配器及内置技能均严格参考该规范设计，确保在 Claude Code、Gemini CLI 与 Codex 间保持最大兼容性。
