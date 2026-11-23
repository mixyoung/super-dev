# [Raw Source] REF-002: Superpowers 原始摘录与基线快照

> **不可变事实说明**：记录外部来源原作者原始表达与文本片段，用于事实溯源、版权追溯及防幻觉核对。严禁主观改动。

---

## 1. 来源与版权信息

- **项目名称**：Superpowers
- **官方仓库**：[https://github.com/obra/superpowers](https://github.com/obra/superpowers)
- **作者**：Jesse Vincent (obra)
- **固定基线**：`v6.4.2` / [`b36e0829c6d0140e93cfef2ca599b1b07d4a7797`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797)
- **建档日期**：2026-09-12 / 2026-10-05

---

## 2. 官方核心技能原文摘录

### 2.1 Systematic Debugging
> 来源文件：`skills/systematic-debugging/SKILL.md`
> “Never change multiple variables at once. Formulate a single testable hypothesis, design the smallest experiment that isolates the issue, observe the actual failure before fixing, and verify resolution without side effects.”

### 2.2 Test-Driven Development (TDD)
> 来源文件：`skills/test-driven-development/SKILL.md`
> “Write a failing test first. Verify that it fails for the expected reason. Implement minimal code to turn the test green. Refactor while keeping all assertions passing. Never write implementation code ahead of failing tests.”

### 2.3 Verification before Completion
> 来源文件：`skills/verification-before-completion/SKILL.md`
> “Never announce task completion without providing the exact, fresh execution output showing passing tests and clean lint logs. A statement of completion must bind directly to immutable verification evidence.”

### 2.4 Writing Plans
> 来源文件：`skills/writing-plans/SKILL.md`
> “Every engineering plan must document explicit decisions, interfaces, state invariants, and verifiable criteria. Do not write vague steps; each step must produce an inspectable outcome.”
