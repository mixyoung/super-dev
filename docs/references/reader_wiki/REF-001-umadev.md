---
id: "REF-001"
title: "UmaDev: 智能体交付标准与工程规范知识树"
category: "知识库；开发框架与流程"
status: "已参考·部分吸收"
upstream_url: "https://github.com/umacloud/umadev"
fixed_baseline: "585262706174ad4a958cd054f0948509e84ad610"
first_audit_date: "2026-09-06"
latest_audit_date: "2026-09-14"
summary: "提供基于 Rust 与工程知识树的严密软件交付标准，涵盖 EARS 需求工程、测试反作弊检查、验证者-评审者分离及未决事项登记。"
key_methods: ["ears-requirements", "test-integrity-check", "parking-lot-register"]
ai_generated: false
verified_by: "mixyoung"
tags: ["standards", "delivery", "testing", "product-management"]
---

# REF-001: UmaDev

> **定位摘要**：UmaDev 是一个注重严密性与规范性的 AI 智能体开发与交付体系。其最大价值在于沉淀了极具工业水准的**软内容规范（Soft Content Standards）**，包括需求表达的因果闭环、测试断言反作弊审查、以及将未决决策显式归档的未决事项登记簿。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/umacloud/umadev](https://github.com/umacloud/umadev)（历史记录存在 `dnolincn/umadev`） |
| **固定基线** | [`5852627`](https://github.com/umacloud/umadev/tree/585262706174ad4a958cd054f0948509e84ad610)（对比 v1.1.1 发布提交 `87c3411`，知识库内容无差异） |
| **参考状态** | 🟢 **已参考·部分吸收**（吸收 U1–U14 核心软内容规范，坚决不引入其外部二进制执行器或第二状态机） |
| **原始剪藏** | [raw_sources/REF-001-umadev/README.md](../raw_sources/REF-001-umadev/README.md) |
| **决策记录** | [decisions/ADR-REF-001-umadev-soft-content-boundaries.md](../decisions/ADR-REF-001-umadev-soft-content-boundaries.md) |

---

## 2. 核心技术调研与深度分析 (What & How)

### 2.1 针对的工程痛点
- AI 编写的需求模糊：常常把未经证实的业务假设当成已确立的系统事实；
- AI 跑测试“刷绿”作弊：通过把失败的断言注释掉、跳过测试（`skip`）或弱化 mock 行为来制造全部通过的假象；
- 跨会话决策丢失：复杂项目中悬而未决的技术分歧在多轮对话后被遗忘，导致架构反复横跳。

### 2.2 核心机制与贡献（U1–U14）
- **U1–U6（需求、追溯与测试完整性）**：
  - 以前置条件（Pre-condition）、触发事件（Event）、可观察结果（Response）三段式表达需求；
  - 需求编号与验收标准、设计决策、测试用例建立不可伪造的溯源网；
  - 强制检查测试断言的完整性，禁止弱化断言换取绿灯。
- **U7–U14（调试、上下文与交付治理）**：
  - 运行模型与规格说明分离；
  - 引入未决事项登记簿（Parking Lot Register），显式记录“为什么挂起、何时重启”。

---

## 3. 关键技术取舍速查 (Trade-off Summary)

- ✅ **已吸收**：EARS 需求表达逻辑、测试完整性反作弊规则、未决决策显式停泊、交付评审证据分离。
- 🛑 **坚决拒绝**：
  1. 不移植其 Rust 二进制模块（`crates/umadev-agent`）或外部可执行程序；
  2. 不引入其专有的 `umadev continue`、`.umadev/coach` 状态机；
  3. 不照搬其固定的 API 数量限制或强行规定的云端 Kubernetes 部署模板。
