---
id: "REF-006"
title: "gyuha/forge: 阶段式开发驱动 CLI"
category: "开发框架与流程"
status: "已参考·待吸收"
upstream_url: "https://github.com/gyuha/forge"
fixed_baseline: "28354ac0dcfa596d654631eeac5128d695503f4e"
first_audit_date: "2026-09-12"
latest_audit_date: "2026-09-12"
summary: "基于 Plan-Act-Review-Archive 四阶段生命周期与项目 Hook 的开发编排工具。本项目已完成调研，确认其状态机与本地既有流程重叠，暂无额外吸收价值。"
key_methods: []
ai_generated: false
verified_by: "mixyoung"
tags: ["cli", "state-machine", "workflow"]
---

# REF-006: gyuha/forge

> **定位摘要**：gyuha/forge 是一个用独立命令行工具管理 AI 编程周期的项目。本项目对其完成了深度源码调研，并做出了明确的**来源歧义澄清**与**暂不吸收决策**。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/gyuha/forge](https://github.com/gyuha/forge) |
| **固定基线** | [`28354ac`](https://github.com/gyuha/forge/tree/28354ac0dcfa596d654631eeac5128d695503f4e)（2026-09-12 提取） |
| **参考状态** | 🟡 **已参考·待吸收**（已完成调研，未发现必须落地的增量，保留记录防止重复调研） |
| **原始剪藏** | [raw_sources/REF-006-forge/README.md](../raw_sources/REF-006-forge/README.md) |
| **决策记录** | [decisions/ADR-REF-006-forge-disambiguation.md](../decisions/ADR-REF-006-forge-disambiguation.md) |

---

## 2. 关键技术调研与来源辨析

### 2.1 极其重要的来源辨析 (Disambiguation)
在本项目早期的技术文档中经常出现“Forge”字样，必须严格区分：
1. **BMAD Method 的 Forge Idea**（属于 REF-003）：是一种“想法反证与需求审查”的思维方法；
2. **gyuha/forge**（属于本项 REF-006）：是一个由韩国开发者开发的独立 CLI 仓库，管理 `.forge/` 目录。
两者完全独立，不得互换版本号或混用采用结论。

### 2.2 评估结论
gyuha/forge 核心的 `Plan -> Act -> Review -> Archive` 四阶段流转与外部 Hook 机制，在 Super Dev 现有的成熟流程中均已有完整或更优的实现。引入其状态机会造成架构臃肿。因此保留为“已调研·不吸收”资产。
