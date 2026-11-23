# ADR-REF-006: 关于 gyuha/forge 的来源歧义消除与暂不吸收决议

- **决策标识**：`ADR-REF-006`
- **关联来源**：[`REF-006 (gyuha/forge)`](../reader_wiki/REF-006-forge.md)
- **基线提交**：`28354ac0dcfa596d654631eeac5128d695503f4e`
- **决策日期**：2026-09-12
- **决策状态**：🟡 **暂不吸收 / 保留记录 (Deferred / Documented)**
- **审核责任人**：`mixyoung`

---

## 1. 核心歧义判定 (Crucial Disambiguation)

必须在知识库中永久固化一条认知：
- **`BMAD Forge Idea`（REF-003）** $\neq$ **`gyuha/forge`（REF-006）**。
- 前者是方法论，后者是独立 CLI 仓库。

---

## 2. 暂不吸收原因 (Why Not Adopted)

经代码级审查，gyuha/forge 的阶段流转与 Hook 体系在 Super Dev 中均已有更强健的原生实现。引入其工具链没有任何架构收益，反而会增加双重状态维护成本。故决定将其列为“已调研·不吸收”资产，防止未来团队重复立项调研。
