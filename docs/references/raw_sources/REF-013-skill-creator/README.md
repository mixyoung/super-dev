# [Raw Source] REF-013: skill-creator 原始摘录与基线快照

> **不可变事实说明**：记录外部来源原作者原始表达与文本片段，用于事实溯源、版权追溯及防幻觉核对。严禁主观改动。

---

## 1. 来源与版权信息

- **项目名称**：skill-creator（身份未确认）
- **官方地址**：待补齐（历史整理仅有使用记录，未固化 URL 与发布者，严禁猜测厂商）
- **建档日期**：2026-09-06（采用前向验证）/ 2026-09-11（分层指导）

---

## 2. 核心方法原件摘录

### 2.1 隔离前向验证 (Blind Forward Verification)
> “Test skill authoring by presenting realistic user cases round-by-round without revealing target solutions in advance. Observe if the generated skill instructions guide the model to the correct edits and pass blind verification.”

### 2.2 技能分层组织与适用范围限定
> “A skill must explicitly state when it should NOT be triggered. Unbounded skills pollute global agent context and increase instruction following entropy.”
