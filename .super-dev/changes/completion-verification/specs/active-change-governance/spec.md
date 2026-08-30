# 活动变更治理规格
## Purpose
规定活动变更解析、前缀隔离及确认与交付证据绑定。

追溯声明 SHALL active_change_id artifact_prefix docs_confirmation quality_gate release_readiness proof_pack。
## ADDED Requirements
### Requirement: 活动变更解析优先级与路径安全（`resolve_active_change_id`）
系统必须（`SHALL`）优先从工作流状态的 `active_change_id` 或 `change_id` 解析，再用受控兼容来源；值必须（`MUST`）是安全单段编号。
#### Scenario: 状态指定活动变更
- GIVEN 状态指定 `completion-verification`
- WHEN 解析
- THEN 返回该编号且不被历史产物覆盖
#### Scenario: 恶意变更路径
- GIVEN 值含绝对路径、`..` 或分隔符
- WHEN 解析
- THEN 拒绝且不读取目录外文件
### Requirement: 当前产物前缀严格隔离（`latest_artifact`）
存在活动变更时，文档、预览、质量、发布和证据包必须（`SHALL`）只选择该前缀；其他前缀即使更新也不得混入。
#### Scenario: 多变更产物并存
- GIVEN 三个变更文件并存
- WHEN 查询当前产物
- THEN 只返回 `completion-verification-*`
#### Scenario: 当前前缀缺失
- GIVEN 只有其他变更同类报告
- WHEN 严格查询
- THEN 返回缺失而不借用
### Requirement: 文档与预览确认绑定（`collect_docs_artifact_binding`、`collect_preview_artifact_binding`）
文档确认必须（`MUST`）绑定当前调研、需求、架构和使用体验；适用的预览确认也只绑定当前预览证据。切换变更或文件变化后旧确认不得有效。
#### Scenario: 当前四文档确认
- GIVEN 当前四文档完整
- WHEN 保存确认
- THEN 绑定只含当前前缀且有效
#### Scenario: 缺文档或切换变更
- GIVEN 核心文档不足或活动变更改变
- WHEN 读取门
- THEN 确认无效
### Requirement: 质量发布与证据包前缀一致（`resolve_current_artifact_prefix`）
质量、发布和证据包必须（`SHALL`）使用同一前缀；失败、未通过或相对依赖过期的质量报告必须（`MUST`）算未完成。
#### Scenario: 当前质量通过且新鲜
- GIVEN 当前报告通过且不早于依赖
- WHEN 汇总
- THEN 可以计为完成
#### Scenario: 失败或过期质量报告
- GIVEN 当前质量失败或过期
- WHEN 汇总
- THEN 保持失败或待处理
### Requirement: 无活动变更兼容旧行为（`resolve_current_artifact_prefix`）
无活动变更时系统应该（`SHOULD`）保持原有项目产物发现，不使旧项目不可用。
#### Scenario: 旧项目无活动变更
- GIVEN 状态未登记编号
- WHEN 查询产物
- THEN 使用既有兼容规则
