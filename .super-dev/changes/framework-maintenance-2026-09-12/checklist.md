# Checklist

## Before Merge
- [x] 三文档与当前 change 身份、摘要一致
- [x] Spec 与 P0/P1 任务一致，P2 明确后置
- [x] 所有 MUST 场景有正例、失败例和兼容例
- [x] 标准九阶段、SEEAI 差异、确认权与质量阈值未改变
- [x] 旧知识、画像 v1、旧 workflow-state 和旧交付报告可读
- [x] adoption 覆盖所有受控文件且只记录本批实际证据

## Release Readiness
本轮未授权发布；以下只表示本地交付准备，不授予发布、部署或合并权限。
- [ ] 质量门禁通过
- [ ] 所需运行与恢复证据可复查，未运行平台单列为未知
- [ ] 当前版本证据与文件摘要一致
- [ ] 未把 `delivery_ready` 推导成 `released`、`deployed` 或 `operating`
