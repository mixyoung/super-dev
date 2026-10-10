# P1 证据包目标绑定吸纳记录

## 问题与现有覆盖

证据包构造器已有有效目标解析，指定规格质量评估也已存在；规格项仍调用 latest、排除旧名称、无结果时单项 ready。真实隔离基线复现两例。原 A 修了 readiness，P1 是原有残留，不是原 A 新增缺陷或原范围违规。

## 来源与适用条件

本地基线提交 a93c12108835508d9b01ff038c537a2a6f9e1976，2026-10-06 核对当前 proof_pack、readiness、artifact_utils、SpecValidator 和消费者。研究比较及来源见 [研究](../../../output/proof-pack-target-binding-2026-10-06-research.md)。外部方法只作对象绑定类比，不引入平台、依赖或授权。

贡献准则、知识维护六问、原始证据及正反例针对确定性核心检查缺口适用。绑定限制适用于证据包规格项，不限制显式 latest 查询；UI、数据库/队列和云搭建不适用。保持默认质量要求与原评分规则。

## 取舍与核心影响

复用有效目标与指定评估，缺目标用既有 pending；不增加状态、评分、身份解析、角色、主要入口或流程阶段。保留原结构、整体聚合、质量 90/发布 85/规格 75 和无 UI 不适用路径。

用户于 2026-10-06 10:34:37 明确确认三文档并授权实施 P1；2026-10-09 确认保留 GET 只读入口并授权按“四处落点、未落盘留空”方案兑现只读契约。此授权不包含根旧发布状态改写、真实仓库发布验收、提交/推送/合并/发布/部署。维护档案独立于原 A/B/P2；不用会重绑根工作项的 spec propose，本地 CLI 仅做明确目标的维护校验，不绕过或继承旧发布许可。

范围归属说明：`super_dev/release_readiness.py` 同时包含原补丁 A 的既有未提交修改；本记录只认领 2026-10-09 增加的 operational harness 检查开关一行，A 的部分仍以 target-knowledge-patches-2026-10-05 记录为准。

## 改动范围

- super_dev/proof_pack.py
- super_dev/analyzer/feature_checklist.py
- super_dev/operational_harness.py
- super_dev/release_readiness.py
- tests/unit/test_proof_pack_target_binding.py
- tests/integration/test_web_api_proof_pack_target_binding.py
- output/proof-pack-target-binding-2026-10-06-prd.md
- output/proof-pack-target-binding-2026-10-06-architecture.md
- output/proof-pack-target-binding-2026-10-06-uiux.md
- output/proof-pack-target-binding-2026-10-06-research.md
- output/proof-pack-target-binding-2026-10-06-execution-plan.md
- output/proof-pack-target-binding-2026-10-06/readonly-boundary-blocker.md
- .super-dev/changes/proof-pack-target-binding-2026-10-06/change.yaml
- .super-dev/changes/proof-pack-target-binding-2026-10-06/proposal.md
- .super-dev/changes/proof-pack-target-binding-2026-10-06/plan.md
- .super-dev/changes/proof-pack-target-binding-2026-10-06/tasks.md
- .super-dev/changes/proof-pack-target-binding-2026-10-06/checklist.md
- .super-dev/changes/proof-pack-target-binding-2026-10-06/specs/proof-pack-target-binding-2026-10-06/spec.md
- .super-dev/changes/proof-pack-target-binding-2026-10-06/adoption.md
- .super-dev/changes/proof-pack-target-binding-2026-10-06/validation.md

## 验证与未验证

完整命令、原始日志与限制见 [validation.md](validation.md)。目标绑定与 2026-10-09 GET 只读补全均已交付：

- 20 项新测试修改前 17 失败、3 通过；目标绑定修复后与原 readiness 目标测试合计 35 项通过。
- 只读补全后核心与既有消费者（含两项原失败 GET 测试、完整 Web API、证据包增强）172 项通过；新基线 `14d155d` 同一次适用回归 455 个不同用例中 454 通过、1 项 Windows 符号链接环境性跳过（PR #22 新增用例，与本批无关）。首轮其中 1 项因既有测试桩不接收新 `write_reports` 关键字失败，按新签名适配桩后重跑该文件 31 项全通过，断言未放宽。
- Ruff、Black、Mypy、临时副本 sdist/wheel 构建、贡献检查（基线 `HEAD`）、Skill 同步与差异检查通过；八项旧发布保护摘要与根状态未变。
- 真实 GET 现在不建目录、不写报告、不改输入；`persist=True` 的 POST/CLI 行为不变，未落盘产物 `path`/`markdown` 留空。

不把历史 367/309/308 项累计记录当作本批通过证明；没有真实发布结论或模型能力收益。未验证其他 OS、实际 Python 3.10、真实 UI 或负载，如实列明。

## 决定与回退

已实施用户确认的目标绑定修复与 GET 只读补全（2026-10-06 10:34:37 确认三文档；2026-10-09 确认保留 GET 只读入口并按四处落点方案修复），质量收口完成。本记录不伪造维护者最终语义批准，也不申请发布。

若回退仅逆向撤销本批生产及新测试差异，保留原 A/B/P2、历史资料与无关用户改动，不整库 reset。后续发布另行绑定目标版本和当前证据。
