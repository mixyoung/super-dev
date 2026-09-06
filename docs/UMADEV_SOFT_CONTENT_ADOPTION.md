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

## 最新基线复核与第二批落实（2026-09-06）

最新正式发布为 [v1.1.1](https://github.com/umacloud/umadev/releases/tag/v1.1.1)，官方 npm 包 `@umatech/umadev` 亦为 `1.1.1`。实时核对主线仍为本文件原先固定的 `5852627`，相对正式发布领先 3 个提交，但没有知识库或 Rust 源码差异。第一批不是依据旧快照；尚未完成的是适用内容的继续筛选与落实。

第二批已查阅 14 份候选知识/模板及 2 份代码的相关段落，用户确认三文档后完成以下增量。200 项定向回归、4 个独立只读场景和 3 份实际隔离文档修订完成，详见 [本批验证记录](../.super-dev/changes/umadev-latest-soft-content/validation.md)。本表不是新的运行状态台账。

| 编号 | 已补强内容 | 取舍边界 |
| --- | --- | --- |
| U7 | 证据驱动调试与无进展时改变调查方式 | 保留现有系统化调试，不移植自动分类/重试状态 |
| U8 | 规格的实际文件、接口、版本与验证上下文 | 复用原 Spec 模板，不提前创建 Spec 或新任务引擎 |
| U9 | 受影响旧行为回归与有辨别力的断言 | 保留 TDD，不强制每次独立团队或全量变异测试 |
| U10 | 方法行为评测与经证实失败的案例复用 | 不新增评分体系、自动记忆或全局写入 |
| U11 | 消费者视角的完整接口兼容检查 | 不强制新协议，也不把新增字段一概当兼容 |
| U12 | 产品运行时模型与开发宿主分离 | 只对 AI 产品适用，不复制凭据或默认厂商 |
| U13 | 异步 UI 状态与模板适配 | 沿用现有设计，拒绝假数据、固定布局和占位完成 |
| U14 | 测试资源归属、平台证据和可验证恢复 | 不自动创建云环境、生产回滚或扩大权限 |

详细来源、不采纳项和验证方案在本地 `output/umadev-latest-soft-content-{research,prd,architecture,uiux}.md`；逐文件索引为 `output/umadev-latest-source-inventory.json`。`output/` 按仓库规则不纳入版本控制，本节保留可追踪摘要。

知识树盘点共 468 份 Markdown，其中 306 份在本仓库有同路径、162 份无同路径；这只是文件索引，不等同语义新增或吸纳覆盖率。未逐项评估的行业/框架知识保持未评估，不声称全知识库完成。上一批 U1—U6 的完成与验证结论不变。

### 第二批固定来源与实际落点

固定提交仍为 `585262706174ad4a958cd054f0948509e84ad610`。以下源码仅用于理解原则，没有移植执行逻辑。

| 编号 | 主要固定来源 | 实际落点 |
| --- | --- | --- |
| U7 | [blocker.rs](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/crates/umadev-agent/src/blocker.rs) | 原调试手册、CODE、标准 Skill 错误恢复段 |
| U8 | [spec-as-contract](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/agentic-delivery/01-standards/spec-as-contract.md) | `super_dev/specs/generator.py` 的规格/计划/检查表文字模板，标准 Skill |
| U9 | [test-discipline-for-generated-code](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/agentic-delivery/01-standards/test-discipline-for-generated-code.md) | 原测试策略、风险矩阵、CODE/QA、标准 Skill |
| U10 | [eval-driven-delivery](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/agentic-delivery/01-standards/eval-driven-delivery.md)、[经验与回归](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/agentic-delivery/01-standards/self-improving-memory-and-regression-sets.md) | `knowledge/ai/agent-evaluation-benchmark.md`、QA、标准 Skill；无自动记忆 |
| U11 | [contract-first-api-design](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/experts/architect/contract-first-api-design.md) | 原 API 契约指南、ARCHITECT、标准 Skill |
| U12 | [app-runtime-model-configurable](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/ai/01-standards/app-runtime-model-configurable.md)、[app_runtime.rs](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/crates/umadev-agent/src/app_runtime.rs) | 原 AI 模型选型指南、ARCHITECT、标准 Skill |
| U13 | [ui-states-and-resilient-data-fetching](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/frontend/01-standards/ui-states-and-resilient-data-fetching.md)、[dashboard 模板](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/seed-templates/dashboard.md) | 原跨平台 UI 手册、标准 Skill；不复制页面或示例数据 |
| U14 | [测试环境](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/testing/01-standards/test-data-and-ephemeral-environments.md)、[恢复手册](https://github.com/umacloud/umadev/blob/585262706174ad4a958cd054f0948509e84ad610/knowledge/release-engineering/02-playbooks/release-rollback-and-recovery-playbook.md) | 原测试策略、发布就绪清单、QA/DEVOPS、标准 Skill |

本批同时把 4 份相关知识文件的主标题从作者署名改为实际主题，作者信息保留为署名，使其能经现有检索正确命中；没有改变检索算法。其他重合内容继续复用；不引入外部固定次数、质量档位、技术栈或新的用户操作方式。
