# Tasks: 周期性框架维护与知识边界加固

## 1. 规格与身份

- [x] 1.1 将最终三文档摘要绑定到 `framework-maintenance-2026-09-12`
- [x] 1.2 创建 proposal、plan、tasks、checklist、spec 与 adoption
- [x] 1.3 明确本轮无 UI，`frontend` / `preview_confirm` 不适用；P2 后置

## 2. P0：内容权威安全原子批

- [x] 2.1 增加 L0-L4 内容权威、来源类型、内容类型、允许/禁止效果的类型化合同
- [x] 2.2 在知识注入链生成确定性紧凑信封；旧适用知识保守为强制约束，未吸纳外部/生成内容固定为建议
- [x] 2.3 为工作流状态、确认和高风险动作提供受信结构化输入守卫；普通已授权工作区可逆编辑不重复确认
- [x] 2.4 修正 `knowledge/ai/prompt-and-tool-guardrails.md` 中“一切写入都确认”的冲突表述
- [x] 2.5 增加恶意知识、越权效果和正常编辑反例测试

## 3. P1：阶段专家与角色合同

- [x] 3.1 让 `PHASE_EXPERT_MAP` 从 `WORKFLOW_STAGE_EXPERTS` 确定性派生并不可写
- [x] 3.2 校验 Toolkit、提示、运行状态、报告和 README 的阶段专家集合一致
- [x] 3.3 扩展 ExpertProfile v2，并保留 v1 与项目/用户/内置覆盖优先级
- [x] 3.4 把内置虚构履历改为工作立场；保持 `VERIFICATION` 与 `OVERSEER` 的兼容边界
- [x] 3.5 增加独立评审证据模型与高风险最低要求，不新建台账

## 4. P1：标准流程工作项绑定

- [x] 4.1 清查 `active_change_id`、`artifact_prefix`、文档确认与恢复状态的读写调用方
- [x] 4.2 在既有 workflow-state 中兼容加入 `work_item_id`、派生前缀和 `pre_spec` / `bound` 状态
- [x] 4.3 在 change 绑定、proposal/tasks、Spec 和后续阶段入口执行一致性与文档摘要校验
- [x] 4.4 增加旧 `delivery_ready` change 与新研究共存、缺字段旧状态、摘要不符和原子写测试
- [x] 4.5 保持 SEEAI 现有状态、绑定与模板不变

## 5. P1：交付事实与运营信号

- [x] 5.1 定义 `delivery_ready`、`released`、`deployed`、`operating` 四类独立事实及 unknown 语义
- [x] 5.2 为现有交付/产品报告增加向后兼容的可选 `operational_outcomes`
- [x] 5.3 校验运营信号来源、观察时间、目标版本、证据、可信度、影响和建议动作
- [x] 5.4 增加事实互不推导、部署后运营未知、缺来源/版本待核实以及九阶段不变测试

## 6. 验证与收尾

- [x] 6.1 运行各批定向 pytest，并保留先失败后通过的真实结果
- [x] 6.2 运行相关回归、Ruff、Black、Mypy 与 compileall
- [x] 6.3 运行贡献范围检查与 Skill 同步只读检查
- [x] 6.4 更新 adoption 的逐文件范围、实际结果、未验证项和回退说明
- [x] 6.5 已运行质量、红队、合规、发布就绪和 proof-pack；所有中间 FAIL/BLOCKED 均保留，当前结论只以绑定最新候选的 output/正式验证证据为准
- [x] 6.6 已在用户授权的小范围副本上完成 MiniMax 与 DeepSeek 不同会话只读源码复审；两者首轮均要求修改，问题已定向修复，当前候选结论继续由绑定的外部评审报告判定

## 7. 明确后置（本批不实施）

- [x] 7.1 已记录后置决定：P2 主 Skill 渐进披露需先证明行为收益与宿主读取可靠性，本批不实施
- [x] 7.2 已记录后置决定：P2 周期只读 watchlist / 自动差异发现本批不实施
