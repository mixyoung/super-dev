# 完成前验证映射与验证说明

本文只引用稳定路径。回放运行编号、当前代码版本摘要和耗时不得写死；从 `.super-dev/extensions/metrics/verification-pilot-summary.json` 读取当前 `replay_run_id`，再定位同批次 `completion-report.md`。

## 完成前新鲜验证 Requirement 组

- 实现：`super_dev/extensions/builtins/fresh_verification.py`、`super_dev/extensions/pytest_plan.py`、`super_dev/extensions/verification_metrics.py`、`super_dev/extensions/evidence.py`、`super_dev/extensions/executor.py`、`super_dev/release_readiness.py`、`super_dev/cli_release_quality_mixin.py`。
- 测试：`tests/extensions/test_fresh_verification.py`、`tests/extensions/test_fresh_verification_service.py`、`tests/extensions/test_verification_metrics.py`、`tests/extensions/test_verification_replay_contract.py`、`tests/extensions/test_verification_replay_runner.py`、`tests/extensions/test_executor.py`、`tests/extensions/test_evidence.py`、`tests/unit/test_release_readiness.py`、`tests/unit/test_release_readiness_enhanced.py`。
- 验收：`pytest -q tests/extensions tests/unit/test_release_readiness.py tests/unit/test_release_readiness_enhanced.py tests/unit/test_safe_baseline_runner.py tests/unit/test_super_dev_skill_contracts.py tests/unit/test_quality_gate.py tests/unit/test_proof_pack_enhanced.py tests/unit/test_delivery_packager.py tests/unit/test_analyzer.py`（由完成前验证固定计划执行）。
- 证据：`.super-dev/extensions/metrics/verification-pilot-summary.json`、`.super-dev/changes/completion-verification/replay-scenarios.yaml`、三个 `pilot-candidate-*.md`。

## 活动变更治理 Requirement 组

- 实现：`super_dev/artifact_utils.py`、`super_dev/workflow_guard.py`、`super_dev/workflow_state.py`、`super_dev/reviewers/quality_gate.py`、`super_dev/proof_pack.py`、`super_dev/release_readiness.py`。
- 测试：`tests/unit/test_artifact_utils.py`、`tests/unit/test_workflow_guard_active_change.py`、`tests/unit/test_workflow_state.py`、`tests/unit/test_release_readiness.py`、`tests/unit/test_release_readiness_enhanced.py`。
- 验收：`pytest -q tests/unit/test_artifact_utils.py tests/unit/test_workflow_guard_active_change.py tests/unit/test_workflow_state.py tests/unit/test_release_readiness.py tests/unit/test_release_readiness_enhanced.py`。
- 证据：`.super-dev/workflow-state.json`、`.super-dev/review-state/document-confirmation.json`、`output/completion-verification-quality-gate.json`、`output/completion-verification-release-readiness.json`、`output/completion-verification-proof-pack.json`。

## CLI 根项目范围 Requirement 组

- 实现：`super-dev.yaml`、`super_dev/catalogs.py`、`super_dev/config/manager.py`、`super_dev/config/schema_validator.py`、`super_dev/workflow_state.py`。
- 测试：`tests/unit/test_catalogs.py`、`tests/unit/test_workflow_state.py`。
- 验收：`pytest -q tests/unit/test_catalogs.py tests/unit/test_workflow_state.py`。
- 证据：`super-dev.yaml`、`.super-dev/workflow-state.json`。

## 中国大陆中文 Harness Requirement 组

- 实现：`super_dev/skills/skill_template.py`、`CLAUDE.md`、`.claude/CLAUDE.md`、`.agents/skills/super-dev/SKILL.md`、`.claude/skills/super-dev/SKILL.md`、`plugins/super-dev-codex/skills/super-dev/SKILL.md`、`plugins/super-dev-claude/skills/super-dev/SKILL.md`。
- 测试：`tests/unit/test_super_dev_skill_contracts.py`。
- 验收：`pytest -q tests/unit/test_super_dev_skill_contracts.py`。
- 证据：上述受版本控制模板与镜像；不读取或修改用户级副本。

## Spec 与静态验证

- `super-dev spec validate completion-verification -v`
- `super-dev spec quality completion-verification --json`
- `pytest -q tests/unit/test_traceability.py tests/extensions/test_verification_replay_contract.py`
- 范围内 `ruff check`、`black --check`、`mypy`、`python -m compileall` 与 `git diff --check`。

## 当前收敛事实

- 阶段 2B：`false`。新流程成对正确验收时间中位数未优于旧流程，保持阶段 2 且不接系统化排错。
- 回放：10 个隔离场景均得到预期的新流程判断；稳定证据从指标汇总中的 `replay_run_id` 定位，不在本文写死运行编号、摘要或毫秒数。
- 规格合规：通过（`PASS`），活动 Spec 共 26 个 Requirement，找到 26 个，缺失 0 个，100/100。
- 架构漂移：通过（`PASS`），100/100。
- 界面合规：通过（`PASS`）。根项目为 CLI 且 `frontend=none`，扫描文件 0、违规 0、100/100。
- 红队：通过（`PASS`），84/100，关键和高风险问题均为 0；扫描范围只包含当前 CLI 发布面。
- Spec-Code 一致性：通过（`PASS`），100/100、问题 0；任务编号、只读复审和负向范围声明不再误作实现缺失。
- 完成前验证：通过（`PASS`）。固定计划收集 357 项，实际执行并通过 355 项，跳过 2 项，失败和错误均为 0；证据与当前代码版本一致。
- 整体质量：通过（`PASS`）。门禁分（加权）90.9/100，阈值 90/100；未加权平均分 89/100。
- 发布就绪：通过（`PASS`），85/100；发布就绪的新验证运行与质量证据运行编号不同，但 `candidate_digest` 相同。
- CLI 交付清单：就绪，纳入 10 项、缺失必需项 0；服务部署与数据库迁移面按项目配置标记为不适用。
- 证据包：通过（`PASS`），35/35 项就绪、阻断项 0。
- 报告前缀：质量、发布就绪和证据包均严格使用 `completion-verification`；不得回退到历史变更或根项目猜测前缀。
- 文档确认：只绑定当前变更四份文档；CLI 根项目不写预览确认。

## 本轮静态、测试与隔离检查事实

- Ruff 全范围通过（`PASS`）；当前修改范围 Black 通过（`PASS`）；`compileall` 与 `git diff --check` 通过（`PASS`）。
- 全仓 Black 仍有 106 个既有范围外文件待格式化，少于 `main` 基线 154 个；不批量改写范围外文件。
- 全仓 Mypy 仍有 174 个既有错误，少于 `main` 基线 231 个；差异复核未发现本轮新增错误类型，本轮未新增类型债务。
- 完成前验证固定计划收集 357 项，执行通过 355 项、跳过 2 项、失败和错误均为 0；覆盖扩展平台、发布就绪、质量门禁、证据包、CLI 交付适用性与完整分析器回归。
- 隔离自检通过（`PASS`）：13 项通过、1 项跳过，真实用户目录新增、删除和变化均为 0。
- CLI 主帮助、`release readiness` 与 `quality` 路由冒烟均返回 0。
- Windows 非隔离的历史大范围测试仍存在 Rich 自动换行、HOME 和宿主探测相关既有失败；分析器 JSON 的路径分隔符问题已修复，完整分析器测试 32 项通过。本轮最终以受控完成前验证计划为发布执行事实。
- 所有直接 pytest、最终验证与回放使用一次性用户目录和临时目录，不读取或修改真实用户级 Skill、配置或凭据。

## 最终关闭条件

只有以下条件全部真实满足后，才能勾选 checklist 最后四项并判定可合并：

1. 最新当前代码版本的完成前验证通过（`PASS`）。
2. 配置阈值 90 的整体质量门禁通过（`PASS`）。
3. 发布就绪通过（`PASS`），且其新验证运行与质量证据的 `candidate_digest` 一致。
4. 证据包通过（`PASS`）。
5. checklist 与本文件的最终修改完成后，重新执行上述证据链，避免使用过期证据。
