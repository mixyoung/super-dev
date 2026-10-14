# Plan：P1 实施方案

验收依据是已确认 [PRD](../../../output/proof-pack-target-binding-2026-10-06-prd.md)，技术方案见 [架构](../../../output/proof-pack-target-binding-2026-10-06-architecture.md)，次序见 [执行计划](../../../output/proof-pack-target-binding-2026-10-06-execution-plan.md)。

调用链：`ProofPackBuilder.active_change_id` → `SpecValidator.assess_change_quality()` → 原 `ProofPackArtifact` → 原 `ProofPackReport`。

无有效目标时复用身份诊断，返回既有 `pending`，无猜测路径；有目标则指定评估，目录消失/缺规格保留失败详情。生产只涉及 `proof_pack.py` 的相关方法与 import。不改变其他证据项、readiness、解析器、质量算法或聚合。

先写真实跨入口红灯，再修调用处和复核绿灯；补真实 Web GET，回归既有 CLI/Web 及只读/鉴权边界。单项和整体结论分开，现有绿色夹具只有真实失败后才修实，保留原断言。

原分支和基线提交保持，已有改动已冻结。所有发布消费者验证在隔离项目运行；构建在临时源码副本。最后核对贡献、Skill、源码与八项保护摘要，不生成本仓库新的发布就绪或证据包报告。
