# DSH 正式适配吸纳记录（公开摘要）

## 问题与现有覆盖

现有宿主接入缺少 DeepSeek Harness（DSH）桌面版的注册、装卸及原生开发入口。该改动把 `/super-dev` 与 `/super-dev-seeai` 接到已有 Core；可选只读伴生插件不承担项目开发。

## 来源与适用条件

依据已确认的 DSH 维护工作项及本仓库既有贡献准则。原生主开发插件和真桌面对照针对官方未修改的 DSH `0.2.2-rc.3`（Windows）；早期技能与规则的原型提供了发现、归属与回退对照，不作为当前原版的完整验收证据。其他宿主继续沿用原有接入。

## 取舍与核心影响

复用 Core 工作项、阶段状态及确认门，不建立第二状态机。保留官方 `agent-instructions`、标准和 SEEAI 的差异、项目默认质量门槛 90 及 A01～A14 的验收条件。项目内实现和隔离验收的批准不等于允许全局安装、模型外发或发布。合并比较时，兼有工作流修复和宿主接入改动的 `super_dev/workflow_guard.py` 由工作流可靠性吸纳记录统一登记，避免重复归属。

## 改动范围

- .dsh/skills/super-dev-seeai/SKILL.md
- .dsh/skills/super-dev/SKILL.md
- .super-dev/changes/super-dev-dsh-desktop/adoption.md
- .super-dev/changes/super-dev-dsh-desktop/change.yaml
- .super-dev/changes/super-dev-dsh-desktop/checklist.md
- .super-dev/changes/super-dev-dsh-desktop/ledger.json
- .super-dev/changes/super-dev-dsh-desktop/plan.md
- .super-dev/changes/super-dev-dsh-desktop/proposal.md
- .super-dev/changes/super-dev-dsh-desktop/specs/super-dev-dsh-desktop/spec.md
- .super-dev/changes/super-dev-dsh-desktop/tasks.md
- docs/HOST_USAGE_GUIDE.md
- plugins/super-dev-dsh/README.md
- plugins/super-dev-dsh/cordis.patch.yml
- plugins/super-dev-dsh/index.js
- plugins/super-dev-dsh/package.json
- plugins/super-dev-dsh/test/status.test.js
- pyproject.toml
- scripts/sync_super_dev_skills.py
- super_dev/artifact_utils.py
- super_dev/baseline_governance.py
- super_dev/catalogs.py
- super_dev/cli_host_commands_mixin.py
- super_dev/cli_host_discovery_mixin.py
- super_dev/cli_integration_runtime_mixin.py
- super_dev/host_diagnostics.py
- super_dev/host_experience_profile.py
- super_dev/host_registry.py
- super_dev/host_runtime_validation.py
- super_dev/host_usage_profile.py
- super_dev/integrations/catalog_mixin.py
- super_dev/integrations/dsh_plugin_snapshot.py
- super_dev/integrations/dsh_primary_bridge.py
- super_dev/integrations/dsh_primary_bundle/README.md
- super_dev/integrations/dsh_primary_bundle/cordis.patch.yml
- super_dev/integrations/dsh_primary_bundle/index.js
- super_dev/integrations/dsh_primary_bundle/package.json
- super_dev/integrations/install_manifest.py
- super_dev/integrations/managed_content.py
- super_dev/integrations/manager.py
- super_dev/integrations/manager_content_mixin.py
- super_dev/migrate.py
- super_dev/review_state.py
- super_dev/skills/manager.py
- super_dev/skills/skill_template.py
- super_dev/update_hosts.py
- super_dev/user_directories.py
- super_dev/web/api_host_support.py
- super_dev/work_item_identity.py
- tests/integration/test_cli.py
- tests/unit/test_catalogs.py
- tests/unit/test_dsh_integration.py
- tests/unit/test_dsh_plugin_snapshot.py
- tests/unit/test_dsh_primary_bridge.py
- tests/unit/test_fork_update.py
- tests/unit/test_host_diagnostics.py

## 验证与未验证

- 在官方未修改的 rc.3 Windows 桌面版上，隔离环境中的安装、卸载及双原生命令显示/消失对照已通过（`PASS`）。曾以离线适配器验证 Core 文档与确认门，140 项 Core 回归和八份旧宿主渲染对照通过（`PASS`）；不等同正式开发验收。
- 绑定的标准合成样例已通过原生命令进入调研（`research`）。后续真实请求曾到达上游并收到 HTTP 200，但回复未通过本地协议检查，没有写成核心文档，也没有到达文档确认门。后续候选仅经本地检查，未在原版桌面复跑；实机验收已停止。
- 原版的共享技能回退对照 A12 仍失败（`FAIL`）；隔离修复对照不替代原版。标准样例的后续确认、预览、后端、质量与交付，以及独立 SEEAI 全流程，尚未完成。原始回执、运行环境配置、模型请求和制品均不随公开分支分发。

## 决定与回退

保留已验证的源码、回归用例及局部运行结论；不将其认定为完整适配或可发布。本分支只同步脱敏后的 Git 提交，不改变验收状态或已有确认。回退只撤回对应接入差异；卸载仅删除仍归属的托管内容，不重置仓库、不清理其他宿主或用户文件。完整维护记录和原始回执保留在本地。
