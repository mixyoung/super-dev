# 第二批 UmaDev 软内容吸纳：U7—U14

## 授权与基线

2026-09-06 用户在三份核心文档之后回复“确认”，批准 `output/umadev-latest-soft-content-{prd,architecture,uiux}.md` 的 U7—U14 范围。基线为 Super Dev `4911930`、UmaDev `5852627`（已核实最新正式版 v1.1.1）。详细来源和不采纳项见 `output/umadev-latest-soft-content-research.md` 与 `docs/UMADEV_SOFT_CONTENT_ADOPTION.md`。

## 实施范围

- U7：原调试知识与 Skill 错误恢复段，区分诊断/修复，原检查复验，无进展换调查。
- U8：`super_dev/specs/generator.py` 现有文字模板的范围、接口/版本依据及验证提示；不改调度。
- U9/U10：已有测试策略、风险矩阵和 AI 评测条目，补影响面、断言辨别力和真实行为案例。
- U11/U12：已有 API 契约和模型选型知识，补消费者兼容与开发/产品模型分离。
- U13/U14：已有跨平台 UI 手册、测试与发布知识，补异步状态、资源归属和恢复证据。
- 必要提醒进入 CODE/QA/ARCHITECT/DEVOPS 和标准 Skill 唯一模板；脚本同步四份仓库副本。

## 验收与非目标

每项对应已确认 PRD 的可观察场景；测试实际生成、检索、安装和原合同，增加隔离行为评估。保留 TDD、Forge/需求审查/Grill、九阶段、确认门、SEEAI、现有门禁与运行能力。没有新 UI 实现，不为文字指导制造页面或预览。

不改变 `completion-verification` 的活动状态、台账、任务和证据；本记录不是另一个运行状态机。当前宿主直接完成已授权内容修订，避免无范围 CLI 动作推进旧 change。不引入 Rust/模型驱动/自动记忆、新命令、新评分或全局安装，不提交推送或发布。

## 回退与限制

按本批文件差异回退知识及模板即可；来源盘点只说明本轮已评估内容，不代表 468 份知识完整吸纳。验证结果不得替代全项目发布验收。
