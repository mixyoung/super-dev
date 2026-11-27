# UI 验收证据边界整改

## Summary

沿用用户已确认的 [PRD](../../../../../output/ui-review-evidence-boundary-prd.md)、[架构](../../../../../output/ui-review-evidence-boundary-architecture.md) 和 [UI/UX](../../../../../output/ui-review-evidence-boundary-uiux.md)。本仓库不新增前端；浏览器行为在独立 UI 测试项目核验。

## ADDED Requirements

### Requirement: review-boundary

SHALL 独立记录源码规则、浏览器实际运行和图片输入后的视觉评审；不使用 Pillow、旧像素指标或源码启发式替代真实视觉评审。默认宿主指导采用同一合同。

#### Scenario 1: 证据能追溯到当前页面与执行者
- GIVEN 已确认的 UI/UX 有明确的桌面、移动和关键状态范围
- WHEN 宿主实际运行、交互、截取原图并把图交给具备视觉能力的执行者
- THEN 输出引用当前代码版本、文件摘要、实际执行和图片输入记录的三份结果；发现或正向观察指向截图和可见位置

#### Scenario 2: 只有源码或部分图片证据
- GIVEN 已有源码检查或截图，但能力、记录或覆盖不足
- WHEN 评审或消费证据
- THEN 保留已验证部分，视觉未验证；不得把文件存在、自报标记、OCR 或旧像素阈值升级为视觉通过

### Requirement: shared-consumption

SHALL UI review、质量门禁、发布就绪、证据包及现有 Web 读取采用同一证据语义，维持既有预览确认、质量阈值和非 UI 不适用规则。

#### Scenario 1: 真实失败与缺证据同时出现
- GIVEN 某必需结果已执行且发现不合格，其他必需结果缺失或过期
- WHEN 进入验收
- THEN 已发现的问题为失败，缺失部分仍显示未验证，不能由分数抵消或由任何消费入口放行

#### Scenario 2: 安装发行包而不安装开发依赖
- GIVEN 新环境只安装基础 wheel 依赖且找不到 PIL
- WHEN 执行 PRD、UI review、全量质量入口
- THEN 可正常读取文档和生成检查结论，不出现 PIL 导入崩溃；如实表达质量是否满足

## Acceptance Checklist

- [ ] AC-01 至 AC-04、AC-07 至 AC-10、AC-15 至 AC-18：失败关闭和身份/输入校验。
- [ ] AC-05 至 AC-06：真实宿主截图与看图正反例。
- [ ] AC-11：干净 Windows wheel 安装复验。
- [ ] AC-12 至 AC-14：非 UI、消费入口一致、保留用户预览确认。

## Out of Scope

不改 DSH，不增模型服务、全局配置或图片编辑依赖，不提交、推送、发布、部署。
