# 四文档收尾与更新一致性

## 问题与现有覆盖

当前完成前验证已有实际执行、证据和隔离，缺运行前反馈、简洁首屏及若干前置阻断回执；Windows unit 门禁未覆盖 tests/extensions。旧更新提示和命令查询原版 PyPI，且安装后仍可能用旧进程刷新模板。

## 来源与适用条件

本地已确认 completion-verification 的 research、PRD、architecture、UIUX 四文档及 main 59298d3 的实际实现，核对日期 2026-09-07。更新链仅适用于本 fork；外部协议依据为当日核对的 GitHub Releases REST API 和 uv 官方工具升级文档（链接见 docs/FORK_UPDATES.md）。不吸纳新品牌方法或新运行程序。

## 取舍与核心影响

用户“按照建议执行”批准收尾和更新统一。保持九阶段、确认权、单一验证入口、run_id、验收阈值和用户裁决；不可信扩展的失败由 Core 自有证据范围记账，不扩大扩展权限。默认 JSON 和关闭试点兼容。最终回放在全部代码冻结后执行，以免证据立即过期。

## 改动范围

- .super-dev/changes/completion-verification/closure-plan.md
- .super-dev/changes/completion-verification/adoption.md
- super_dev/extensions/service.py
- super_dev/cli_release_quality_mixin.py
- super_dev/release_readiness.py
- super_dev/cli_parser_mixin.py
- tests/extensions/test_verification_closure.py
- tests/support/run_safe_baseline.py
- tests/unit/test_safe_baseline_runner.py
- .github/workflows/ci.yml
- super_dev/release_channel.py
- super_dev/update_runtime.py
- super_dev/update_hosts.py
- super_dev/version_check.py
- super_dev/cli_host_ops_mixin.py
- pyproject.toml
- tests/unit/test_fork_update.py
- tests/integration/test_cli.py
- docs/FORK_UPDATES.md
- README.md
- README_EN.md
- docs/INSTALL_OPTIONS.md
- tests/support/run_update_acceptance.py

## 验证与未验证

开始时工作树干净，版本 2.5.0。先跑新增验收用例复现缺口（清单、阶段回执和提示/展开/JSON 输出失败），再实现修复。初次 Windows 3.13 安全基线为隔离自检 13 通过/1 跳过、用户目录 240 通过/2 跳过、核心扩展 151 通过/2 平台跳过，真实用户目录变化为 0。后续最终复跑结果另行追加。

后续本机最终安全基线：核心扩展加更新器 186 通过/2 平台跳过，隔离自检 13/1、用户目录 240/2，用户目录变化 0；45 项定向回归通过。最新构建 wheel 与当前 251 个包源码/资源逐项一致，真实隔离 pip 升级复跑通过。

原登记计划 completion-verification-candidate-006 在 900 秒触发超时（运行 0330e8c43c324057884e5d1ec523c642），完整进程树已清理，结果正确为 BLOCKED，不能把局部结果算成全计划通过。期间出现的失败定位为固定模式集合测试未列入本轮新增 core-verification；以单测复现后补齐明确模式、选择范围与隔离前置顺序的断言，继续拒绝任意模式。未延长超时、未删原测试。完整登记计划的耗时问题保留为未解决项，后续远程 CI 与最终回放单独提供证据，不冒充这次计划通过。

更新器 34 项定向用例通过；隔离 venv 的真实 pip 更新验证已通过，保留运行中的旧 0.0.1 合成夹具进程，实际安装新 wheel 后，由新解释器验证包文件并刷新项目 Skill。旧版本是测试夹具，不是发布历史或真实用户升级数据；HTTP 传输由本地 wheel/摘要夹具替代，来源解析、摘要校验、安装器和新进程均真实执行。证据位于 output/verification-closure/isolated-update/。生产代码随后有收尾改动，最终会重新构建并验收。

原 3 项 CLI 更新集成断言按获批来源变更从 PyPI/旧 migrate 调用改为 fork 来源、方式/用户范围转发及非零退出；没有更改 10 场景答案、计时、真实候选标签或 2B 阈值。误用宽泛 -k update 曾带入无关的 detect_save_profile 集成测试，在本机因没有就绪宿主失败，未顺手修改；精确选择的更新 28 项检查通过。全量类型旧债仍存在；22 个必过入口类型检查通过，新改 5 个模块单独类型检查通过。Linux/其他 Windows 版本需要实际 CI，尚不能宣称已验证。

## 决定与回退

发布检查原先只认 `uv tool install super-dev` 字面值，与已发布 fork 的锁定标签安装说明冲突。本批对齐为兼容原写法并准确接受固定仓库的版本标签命令；补充不同来源/未锁定版本/缺安装入口拒绝测试，不移除检查或降低门槛。整份发布报告仍因测试超时和旧合规证据失效而不能作为通过声明。

该门禁修订后，更新器与基线模式的 42 项定向检查通过，仓库实际安装入口检查通过。完整当前 wheel 会在本 PR 跨平台任务中重新构建并执行隔离升级；此前本机 wheel 验收保留为上一轮局部证据，不代替当前提交的 CI。用户另行批准提交、推送及创建 PR 运行 CI，明确不自动合并或发布。

采用已获批准的增量收尾，不改产品路线。若失败则修复本批或回退本批差异，不降低门槛，不改原人工验收。更新与新发布分离，本轮不自动发布新版。
