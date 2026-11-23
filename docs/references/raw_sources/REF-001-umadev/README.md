# [Raw Source] REF-001: UmaDev 原始摘录与基线快照

> **不可变事实说明**：记录外部来源原作者原始表达与文本片段，用于事实溯源、版权追溯及防幻觉核对。严禁主观改动。

---

## 1. 来源与版权信息

- **项目名称**：UmaDev
- **官方仓库**：[https://github.com/umacloud/umadev](https://github.com/umacloud/umadev)（历史记录存在 `dnolincn/umadev` 重命名记录，commit 一致）
- **固定基线提交**：[`585262706174ad4a958cd054f0948509e84ad610`](https://github.com/umacloud/umadev/tree/585262706174ad4a958cd054f0948509e84ad610)
- **正式发布对比**：v1.1.1 发布提交为 `87c341137b38bdaeb62515f2c1ad6366cecbbe18`（主线领先 3 个提交，知识库无实质差异）
- **建档日期**：2026-09-06 / 2026-11-22

---

## 2. 官方核心模块与段落原件摘录

### 2.1 需求表达规范 (EARS 启发式)
> 来源文件：`knowledge/experts/product-manager/requirements-engineering-ears.md`
> “Requirements must clearly delineate between Pre-conditions, Trigger Events, and Observable System Responses. Never bundle unverified business assumptions as established system facts.”

### 2.2 测试完整性与反作弊检查
> 来源文件：`knowledge/agentic-delivery/01-standards/test-integrity-and-anti-gaming.md`
> “A test suite must be inspected for assertion downgrades, skipped tests, loosened mock behaviors, and modified golden fixtures. Passing all tests by weakening invariants is considered a critical verification failure.”

### 2.3 验证者-评审者模式 (Verifier-Critic)
> 来源文件：`knowledge/agentic-delivery/01-standards/verifier-critic-pattern.md`
> “All review findings must be coupled with concrete reproducible evidence. Blocker findings must be strictly separated from advisory suggestions. The absence of detected errors does not equal a proof of correctness.”

### 2.4 未决事项登记簿 (Parking Lot Register)
> 来源文件：`knowledge/agentic-delivery/01-standards/open-decisions-parking-lot-register.md`
> “Every paused or unresolved decision must explicitly preserve the reason for pausing and the exact criteria required to reopen it, preventing silent decision drift across sessions.”
