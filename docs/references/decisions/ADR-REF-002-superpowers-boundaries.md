# ADR-REF-002: 关于 Superpowers 吸收边界与流程决议

- **决策标识**：`ADR-REF-002`
- **关联来源**：[`REF-002 (Superpowers)`](../reader_wiki/REF-002-superpowers.md)
- **基线提交**：`v6.4.2` / `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`
- **决策日期**：2026-09-14 / 2026-10-05
- **决策状态**：🟢 **已批准并落地 (Approved & Adopted)**
- **审核责任人**：`mixyoung`

---

## 1. 决策结论

我们决定**全面吸收其“系统化假设调试（Systematic Debugging）”、“完成前强制绑定新鲜证据（Verification before Completion）”与“TDD 核心闭环”等工作方法**；**坚决不整套安装其全部外部技能，不引入与 Super Dev 重叠的第二套开发流程**。

---

## 2. 负向经验与拒绝原因 (Negative Results)

1. **拒绝整包安装技能**：
   - Superpowers 包含大量辅助技能，若无条件全量安装，会导致宿主模型的上下文窗口被大量通用规则占满，削弱对业务代码的注意力。
2. **拒绝仪式化官僚主义**：
   - 调试与 TDD 思想必须根据任务实际风险弹性触发，不能在修改纯文档或单行注释时也强行要求撰写一套繁琐的 TDD 实验计划。
