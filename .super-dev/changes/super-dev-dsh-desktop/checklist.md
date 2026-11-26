# Checklist

最新状态：用户已确认2026-11-16修订三文档，当前不使用虚拟机、模型API需要时再询问。任务8.*的同版rc.3准备与记录已完成：同版163项、旧混合版本163项回归及9项模式绑定检查通过。完整桌面启动件和真实模型准入尚未完成；原正式验收不补勾。既有已勾项仍只沿用其原代码批次证据，不代表新原型已有独立模型审查或正式适配通过。

## Before Merge

- [x] 规格、任务、原 PRD DSH-01～DSH-08 / A01～A14 一致，无新增豁免。
- [x] 新增宿主沿实际消费者接通，不生成未经核实的自定义命令文件。
- [x] DSH 双技能来自唯一模板，前置元数据符合固定 rc.5；旧 Claude/Codex 标准/SEEAI 渲染字节不变。
- [x] A08～A11 经隔离项目里的真实装卸入口通过：幂等、部分失败、卸载、用户与其他宿主字节保护。
- [x] 损坏边界、用户修改和归属不明反例保守保留；没有删除原失败断言、改阈值或新增跳过刷绿。
- [ ] A01～A07、A12、A14 有正常工具集的真实桌面证据，模块测试与守卫停止未冒充桌面通过。
- [ ] 目标 active/armed 自动续跑未代替用户批准，缺失/损坏/真实卸载分别验证。
- [x] A13 同步、诊断、覆盖、旧宿主及证据绑定通过；adoption 列表覆盖实际改动文件。
- [x] 适用测试、构建、lint、类型检查和独立只读审查已执行，失败与未验证项如实保留。
- [ ] 质量阈值保持 90，阻断问题清零；未触及全局接入、现用配置、凭据扩权或其他排除面。
- [ ] 测试资源精确归属与适用恢复已验证，清理不触及用户资源。

本轮已经补上[真实桌面双技能菜单和未发送草稿选择](../../../output/dsh-host-research/desktop-acceptance-2026-11-05/run-11/ui-result.json)，原应用退出 0，没有强制结束；不是标准/SEEAI 模型流程或原生自然等待的通过。[十次数据清理](../../../output/dsh-host-research/desktop-acceptance-2026-11-05/menu-runs-cleanup-01.json)共移除 1074 文件、616 目录，原夹具和全部失败保留。控制面约束见 [NATIVE-CONTROL-ADDENDUM](../../../output/dsh-host-research/native-validation-2026-11-05/NATIVE-CONTROL-ADDENDUM.md)；A12、首工具前完整范围、总请求预算及全部外部资源归属仍不勾选。

## Release Readiness

本轮不适用：用户只批准项目内适配实现和验收，没有授权提交、推送、开 PR、发布、部署或现用用户级安装。不勾选发布项作为通过；旧工作项的发布事实不属于本次交付。

## Evidence

实际差异、完整命令、退出结果、JUnit、环境失败及桌面未验证项见 [IMPLEMENTATION-REPORT](../../../output/dsh-host-research/implementation-2026-11-05/IMPLEMENTATION-REPORT.md)。主会话已核对旧渲染字节、同期双技能及安装内原生解析/技能加载；本项不代表正常完整桌面流程已通过。完整桌面、质量总门及交付仍未勾选。

本轮五项红灯返工的当前回执改见 [REWORK-REPORT-01](../../../output/dsh-host-research/implementation-2026-11-05/REWORK-REPORT-01.md)。上轮全量检查中断，不据旧报告或日志勾选通过；独立复审和真实桌面验收仍由主会话核实。

第二轮实施回执：[REWORK-REPORT-02](../../../output/dsh-host-research/implementation-2026-11-05/REWORK-REPORT-02.md)。主会话已按新绑定独立复核全部旧入口、原五反例、Windsurf 真实旧布局及 Windows junction，见 [POST-REWORK-02-REVIEW](../../../output/dsh-host-research/review-2026-11-05/POST-REWORK-02-REVIEW.md)。首次完整回归的 2 项夹具布局失败和修正后 17 项边界测试均保留；随后完整回归已实际结束为 3763 通过、15 原有跳过、0 失败，退出 0。原始用例集合和跳过原因已独立核对，没有漏测或新增跳过；代码回归通过不覆盖下面的规则失败或桌面受阻。

当前产品规则预算反例另见 [native-product-budget-01](../../../output/dsh-host-research/native-validation-2026-11-05/native-product-budget-01.json)：规则文件被省略的条件实际失败，不能因为观测程序退出 0 就勾选回退安全。原生 symlink 创建受阻、正常完整桌面准入和请求预算仍单列。原桌面 run-01 八个声明数据根已按 [cleanup-attempt-05](../../../output/dsh-host-research/desktop-acceptance-2026-11-05/run-01/cleanup-attempt-05.json)清理并事后核实，不扩大成全部外部资源归属已证明；完整桌面、质量总门及交付保持未完成。
