# Checklist: Super Dev 2.6 可靠性收敛

## 范围

- [x] 只有 `workflow-state.json` 保存当前真实流程状态
- [x] `SESSION_BRIEF.md` 只由最新状态自动生成
- [x] `pipeline-state.json` 一次迁移后删除且不会重新生成
- [x] 没有增加阶段、Agent Runtime、多项目层、Memory 2.0、UI 或插件市场

## 正确性

- [x] 并发旧修订不能覆盖新状态
- [x] 半写、损坏和截断记录有安全恢复路径
- [x] 用户确认、工作项和文档摘要保持绑定
- [x] 当前代码版本变化会使旧关键证据失效
- [x] `delivery_ready`、`released`、`deployed`、`operating` 互不推导
- [x] 外部发布已发生、本地记录失败时不会直接重发

## 兼容与平台

- [x] 旧 Schema 可保守读取且不自动推进
- [x] Windows 实际路径及 POSIX 锁分支单测试、中文路径、锁和原子替换已验证
- [x] 现有宿主入口和普通用户命令不变
- [ ] 用户自有文件和用户级环境未被测试污染：Super Dev 未修改用户文件，但测试期间外部 Orca 流程重写了 Gemini 配置，保留为环境阻断

## Before Merge
- [x] 规范与任务一致
- [x] 已确认的 MUST 场景有适用验证，受影响旧行为已复核
- [x] 风险与适用恢复策略已确认

## Release Readiness
仅在本轮涉及发布时使用；不适用须说明，不能勾选作通过。
- [ ] 质量门禁通过
- [ ] 所需运行与恢复证据可复查，未运行平台单列
- [ ] 发布说明已准备
