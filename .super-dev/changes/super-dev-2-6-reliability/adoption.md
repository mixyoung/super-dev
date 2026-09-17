# 2.6 可靠性收敛吸纳记录

## 问题与现有覆盖

2.5.1 已有工作项身份、原子写工具、历史快照、Fresh Verification、候选摘要和四类交付事实，但状态仍有多个生产写入口，旧引擎另写 `pipeline-state.json`，会话简报存在两种格式；验证身份和发布事实尚未形成同一闭环。当前仓库已发生“版本已经发布、状态仍等待发布”的真实漂移。

## 来源与适用条件

- 本地基线：`7ef3903a2f0979535a903adb4cc7d9668d995b11`，2026-09-17 核对；
- 本地文档：`output/super-dev-2-6-reliability-{baseline-audit,research,prd,architecture,uiux}.md`；
- Temporal：只吸收权威状态、可恢复历史和确定生成摘要，不引入服务/Worker/分布式编排；
- GitHub Checks/Actions：只吸收检查绑定仓库和提交 SHA 的原则；
- in-toto Statement：只吸收目标摘要与陈述类型分离，不实现签名或供应链平台；
- SQLite：用于比较事务方案，2.6 明确不采用状态数据库。

适用于 Super Dev 本地 CLI 的工作流状态、验证证据和发布记录；不适用于增加新阶段、模型运行时、多项目调度或普通用户入口。

## 取舍与核心影响

采用文件型统一状态服务，不采用全量事件溯源或 SQLite。`workflow-state.json` 保持唯一当前状态；`SESSION_BRIEF.md` 自动生成；`pipeline-state.json` 一次迁移后删除。统一证据信封只覆盖关键验证消费者，旧报告通过适配读取，不搬迁成第二证据数据库。

本批改变核心状态持久化合同和 2.6 版本目标，依据是用户于 2026-09-17 对最终三文档的明确确认。九阶段、确认权、宿主执行边界、质量阈值及 Git/发布授权不变。

## 改动范围

- .super-dev/changes/super-dev-2-6-reliability/checklist.md
- .super-dev/changes/super-dev-2-6-reliability/ledger.json
- .super-dev/changes/super-dev-2-6-reliability/plan.md
- .super-dev/changes/super-dev-2-6-reliability/proposal.md
- .super-dev/changes/super-dev-2-6-reliability/specs/super-dev-2-6-reliability/spec.md
- .super-dev/changes/super-dev-2-6-reliability/tasks.md
- .super-dev/changes/super-dev-2-6-reliability/validation.md
- output/super-dev-2-6-reliability-architecture.md
- output/super-dev-2-6-reliability-baseline-audit.json
- output/super-dev-2-6-reliability-baseline-audit.md
- output/super-dev-2-6-reliability-prd.md
- output/super-dev-2-6-reliability-research.md
- output/super-dev-2-6-reliability-uiux.md
- .agents/skills/super-dev-seeai/SKILL.md
- .agents/skills/super-dev/SKILL.md
- .claude/skills/super-dev/SKILL.md
- .github/skills/super-dev-core/SKILL.md
- .gitignore
- CHANGELOG.md
- README.md
- README_EN.md
- docs/releases/2.6.0.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev-seeai/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- pyproject.toml
- scripts/release.sh
- super-dev.yaml
- super_dev/__init__.py
- super_dev/artifact_utils.py
- super_dev/branding.py
- super_dev/cli_governance_mixin.py
- super_dev/cli_parser_mixin.py
- super_dev/cli_release_quality_mixin.py
- super_dev/cli_workflow_runtime_mixin.py
- super_dev/config/manager.py
- super_dev/creators/document_generator.py
- super_dev/deployers/delivery.py
- super_dev/evidence_contract.py
- super_dev/evidence_identity.py
- super_dev/expert_stage_governance.py
- super_dev/extensions/evidence.py
- super_dev/extensions/executor.py
- super_dev/extensions/models.py
- super_dev/extensions/service.py
- super_dev/orchestrator/engine.py
- super_dev/release_observation.py
- super_dev/reviewers/spec_compliance.py
- super_dev/review_state.py
- super_dev/skills/skill_template.py
- super_dev/state_store.py
- super_dev/workflow_guard.py
- super_dev/workflow_harness.py
- super_dev/workflow_contract.py
- tests/extensions/test_evidence.py
- tests/extensions/test_executor.py
- tests/extensions/test_verification_closure.py
- tests/integration/test_cli.py
- tests/unit/test_evidence_contract.py
- tests/unit/test_compliance_evidence_identity.py
- tests/unit/test_host_runtime_governance.py
- tests/unit/test_pipeline_state_retirement.py
- tests/unit/test_product_audit.py
- tests/unit/test_quality_advisor.py
- tests/unit/test_quality_gate.py
- tests/unit/test_release_observation.py
- tests/unit/test_release_readiness.py
- tests/unit/test_release_script_routing.py
- tests/unit/test_state_store.py
- uv.lock

## 验证与未验证

基线定向测试为 `104 passed, 2 skipped`。当前候选的 2.6 核心回归为 `163 passed, 1 skipped`；合规解析与状态/证据回归为 `19 passed`；其余 unit/extensions/e2e/integration 分区为 `2986 passed, 6 skipped`，Web API 为 `107 passed`。CLI 功能用例 `227/227` 通过，但会话结束时检测到外部程序重写真实 Gemini 用户配置，因此用户目录隔离门禁未通过；本轮未覆盖或回退该文件。Fresh Verification 稳定性修复后，正式计划 `392 collected, 390 executed, 2 skipped, 0 failed`，候选前后一致且进程树清理已确认；执行器回归 `10 passed, 1 skipped`，服务/CLI 回归 `44 passed`，完整扩展回归 `165 passed, 2 skipped`。Ruff、本轮 Black、22 项类型门、核心模块 Mypy、compileall、贡献范围、Skill 同步、Bash 语法和 diff check 通过。Spec Compliance 已由 `65/100` 修复为 `100/100`，Red Team 为 `76/100 PASS`。2.6.0 wheel/sdist 构建及 Twine 检查通过；稳定版 wheel SHA256 为 `A3D5DA902733FF4258A5270F03CA55B46F7C322156100609CBF404439D71B3A2`，sdist SHA256 为 `F0B432FB254A0F1AE05BAF414B7B3BCBB4B4ACA93D49D9920720FF8FA3113877`。初轮质量/发布就绪/Proof Pack 阻断已保留，当前冻结候选将重跑完成前验证与最终交付门禁；未提交、未推送、未合并、未发布、未部署。

## 决定与回退

决定：采用并进入实现。若统一状态服务无法满足跨平台和旧项目恢复要求，回退本批代码，但保留迁移前快照和证据；不得恢复 `pipeline-state.json` 为第二当前状态。外部发布已经发生时只回退本地记录逻辑，不删除或重发外部 Release。
