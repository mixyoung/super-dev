# ADR-REF-011: 关于 DeepSeek Harness 适配边界与验收决议

- **决策标识**：`ADR-REF-011`
- **关联来源**：[`REF-011 (DeepSeek Harness)`](../reader_wiki/REF-011-deepseek-harness.md)
- **基线版本**：`dsh-v0.2.1-rc.5` / `b830ec950faba0a46dda564be3e2d854afed94f1`
- **决策日期**：2026-11-05
- **决策状态**：🟡 **独立分支研究 / 待验收合并 (Research / Pending Acceptance)**
- **审核责任人**：`mixyoung`

---

## 1. 决策结论

我们认可 DeepSeek Harness 的回放评测与能力开关价值，并在独立适配分支开展了工程实验；但**在通过正式的宿主运行时验收套件之前，坚决不将其合并至主干，不将未验证的适配状态写为已交付**。
