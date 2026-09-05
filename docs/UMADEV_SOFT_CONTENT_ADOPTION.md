# UmaDev 软内容吸纳：来源、取舍与落点

> 日期：2026-09-06
> 来源仓库：`umacloud/umadev`
> 固定提交：`585262706174ad4a958cd054f0948509e84ad610`
> 范围：首批六类软内容；不代表完整复制或吸收全部知识树。
> 状态：已改写落地；121 项自动检查及六个隔离行为观察完成，详见 [验证记录](../.super-dev/changes/umadev-soft-content/validation.md)。

## 原则

吸收能改善需求、实现指导与验收的做法，保留 Super Dev 的宿主入口、九阶段、确认合同和运行能力。已有知识优先增补；来源中的数值阈值、目录、强制步骤和自动放行逻辑不能直接成为本项目规则。外部代码只用于理解与核验，不移植其运行模块。

## 来源映射

以下链接均固定到上述提交。实际调用的指导在各落点维护，本文件只记录来源与取舍。

| 编号 | 吸收内容 | 来源 | Super Dev 落点 |
| --- | --- | --- | --- |
| U1 | 以条件、事件、可观察结果表达需求，分开假设与已知事实 | [需求表达](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/experts/product-manager/requirements-engineering-ears.md) | `knowledge/product/product-discovery-and-prd-deep-dive.md`、PM 定义、PRD 验收指导 |
| U2 | 原需求编号关联验收、设计与验证；保持三文档信息一致 | [PRD 模板](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/experts/product-manager/prd-template-and-structure.md)、[coach.rs 的 render_docs](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/crates/umadev-agent/src/coach.rs#L1145) | 同上，以及 `_generate_acceptance_matrix()` |
| U3 | 测试范围、风险、层次、环境与退出条件相互对应 | [测试计划模板](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/experts/qa-lead/test-plan-template.md) | `knowledge/testing/risk-based-test-matrix.md`、`testing-strategy-deep-dive.md`、QA 定义 |
| U4 | 单独审查断言、跳过项、快照、夹具和门禁变化，避免以弱化验证换取通过 | [测试完整性](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/agentic-delivery/01-standards/test-integrity-and-anti-gaming.md) | `knowledge/testing/testing-strategy-deep-dive.md`、CODE/QA 定义、标准 Skill |
| U5 | 评审发现附证据，必须修正与可选建议分开；报告复用原始证据，未验证不计通过 | [验证者/评审者](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/agentic-delivery/01-standards/verifier-critic-pattern.md)、[review.rs](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/crates/umadev-agent/src/review.rs)、[生产就绪审查](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/operations/01-standards/production-readiness-review.md) | `knowledge/development/code-review-quality-complete.md`、QA/DEVOPS 定义、PRD 交付验收指导 |
| U6 | 未决事项保留原因与重启条件，交接保留决定、文件、验证与下一步，按需读原文 | [未决事项](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/agentic-delivery/01-standards/open-decisions-parking-lot-register.md)、[交付上下文](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/agentic-delivery/01-standards/context-engineering-for-delivery.md)、[coach.rs](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/crates/umadev-agent/src/coach.rs) | `knowledge/architecture/adr-template-and-examples.md`、产品知识、标准 Skill，复用现有文档和恢复简报 |

## 择优保留与不采纳项

- 保留可验证的需求表达，不机械强制英文 EARS 句式；目标数值和环境必须由项目证据或已确认约束支持，不能复制例子的延迟、并发、覆盖率或可用性数字。
- 保留追溯思想；测试也可保护缺陷、不变量和兼容合同，不将“没有功能需求编号的测试”一概判作范围膨胀。
- 保留风险驱动测试，不要求每个小改动都拥有全套 E2E、负载、渗透和发布演练；不放松项目已经确定的门禁。
- 保留验证完整性复核，不将所有快照或断言更新都定为作弊；预期行为变更有依据时应更新测试，并证明没有丢失必要保护。
- 保留独立视角，缺少真实隔离时诚实标作自检；不强制增加角色团队或独立评审程序。
- `review.rs` 将缺资料显示为信息项，可借鉴“诚实显示未知”；它的辅助报告聚合规则不能被搬作 Super Dev 发布许可。报告成功生成、没有扫描到问题、测试通过，都不能单独证明全部验收完成。
- `coach.rs::render_docs` 中只返回文本、固定 API 条数、统一分层/暗色等要求不直接采用。Super Dev 仍由宿主写真实文件，并按已确认的架构与 UIUX 执行。
- 不吸收 `umadev continue`、`.umadev/coach`、第二计划/状态、自动模型调用或向量服务；未决事项复用原文档，而不建立新的记忆运行通道。
- 保留部署可恢复的思想，只对相关交付要求运行证据；离线 CLI 不因模板而强制配置云端值班或 Kubernetes。

## 与已有方法的关系

Forge、需求审查和 Grill 已完成的交互过程继续保留。本批补充其中“怎样表达可验收结果、怎样记录未决项”，并完善实现/质量/交接指导，不把它们重新命名或替换为 UmaDev 流程。

本批实现与验证分别记录在 `.super-dev/changes/umadev-soft-content/`。整体发布状态仍由原 Super Dev 门禁与当前证据决定，来源自身的评分不算本项目验收。
