# Spec: Super Dev 2.6 可靠性收敛

## Summary

将工作流状态、阶段记录、会话摘要、当前代码版本证据和发布事实收敛为一条可恢复、可验证、不会静默漂移的本地链路。版本目标为 2.6.0。

## ADDED Requirements

### Requirement: STATE-001 唯一当前状态

系统 SHALL 只使用 `.super-dev/workflow-state.json` 保存当前工作项与流程状态；所有生产写入 SHALL 经过统一状态服务。

#### Scenario: 不允许直接多写入口

- GIVEN 任意 CLI、Web API、工作流引擎或工作项身份操作需要更新状态
- WHEN 提交当前状态变化
- THEN 操作通过统一服务完成，并生成新修订和审计记录
- AND 生产代码不直接覆盖 `workflow-state.json`

### Requirement: STATE-002 修订冲突与原子提交

系统 SHALL 为状态维护单调递增修订号，并在预期修订落后时拒绝覆盖；当前状态 SHALL 以原子替换提交。

#### Scenario: 两个写入者基于同一修订

- GIVEN A 与 B 都读取修订 12
- WHEN A 先提交修订 13，B 再提交
- THEN A 成功
- AND B 返回受阻与当前修订 13
- AND 修订 13 不被旧内容覆盖

#### Scenario: 写入中断

- GIVEN 正在写入新状态
- WHEN 进程在替换前或替换后异常结束
- THEN 后续读取只能看到旧完整状态或新完整状态
- AND 不读取半个 JSON

### Requirement: STATE-003 历史、恢复与摘要

系统 SHALL 在提交前保存可验证历史快照；`SESSION_BRIEF.md` SHALL 只根据最新状态生成，并携带来源工作项和修订。

#### Scenario: 摘要过期

- GIVEN 会话摘要来源修订为 18，当前状态修订为 21
- WHEN 宿主恢复任务
- THEN 摘要被标记为过期并根据修订 21 重新生成
- AND 旧摘要不能推进阶段或证明发布状态

#### Scenario: 当前状态损坏

- GIVEN 当前状态 JSON 无法解析
- WHEN 存在有效历史快照
- THEN 系统提供最新有效恢复候选和丢失区间
- AND 未经有权操作不静默写回或推进

### Requirement: STATE-004 删除第二状态文件

2.6 SHALL 不再生成或读取 `.super-dev/pipeline-state.json`。旧项目中该文件只允许一次迁移。

#### Scenario: 旧文件一次迁移

- GIVEN 旧项目存在合法 `pipeline-state.json`
- WHEN 2.6 首次执行状态写操作
- THEN 仍有效且不覆盖较新状态的信息进入统一状态或阶段记录
- AND 原文件摘要、迁移字段和忽略字段写入历史迁移记录
- AND 新状态提交成功后旧文件被删除
- AND 后续运行不会重新生成该文件

### Requirement: EVIDENCE-001 统一证据信封

关键验证证据 SHALL 记录证据类型、目标摘要、工作项、当前代码版本、产生者、运行 ID、状态、时间、操作、环境、制品和失效条件。

#### Scenario: 证据身份完整

- GIVEN 一次 Fresh Verification 或质量检查结束
- WHEN 结果用于质量或发布判断
- THEN 结果可归一化为证据信封
- AND 通过状态绑定当前工作项及当前代码版本

### Requirement: EVIDENCE-002 旧证据失效

代码、工作项、目标版本或必要输入变化后，旧关键证据 SHALL 不再支持当前通过。

#### Scenario: 代码改变后复用旧 PASS

- GIVEN 代码版本 A 的测试证据为通过
- WHEN 当前代码版本变为 B
- THEN 旧证据显示已过期
- AND Quality Gate、Release Readiness 和 Proof Pack 不得把它算作 B 的通过

### Requirement: RELEASE-001 发布事实闭环

正式 Release 成功后，系统 SHALL 记录目标版本、标签、提交、仓库、制品、摘要、观察来源与时间，并只更新 `released` 事实。

#### Scenario: 正式发布成功

- GIVEN 发布命令已获授权并成功创建或更新正式 Release
- WHEN 制品和摘要已被实际观察
- THEN `released` 为已核实
- AND 当前状态不再要求重复决定同一发布
- AND `deployed` 与 `operating` 不被自动更新

#### Scenario: 外部成功、本地记录失败

- GIVEN 外部 Release 可能已经成功
- WHEN 本地观察记录失败
- THEN 系统返回受阻并要求只读核对
- AND 不直接重试创建第二个 Release

### Requirement: VERSION-001 2.6.0 一致性

包版本、项目配置、运行常量、Skill 元数据、README、CHANGELOG、发布说明、锁文件和构建制品 SHALL 一致为 2.6.0。

#### Scenario: 发布前版本检查

- GIVEN 2.6.0 发布候选
- WHEN 运行版本与构建检查
- THEN 所有受控版本表面一致
- AND wheel/sdist 元数据与目标版本一致

## MODIFIED Requirements

### Requirement: ENGINE-001 旧引擎阶段进度

旧七阶段引擎 MAY 继续作为内部执行细分，但 SHALL 把 canonical stage、完成阶段、剩余阶段和专家记录提交到统一状态与阶段记录，不得保存第二份当前状态。

### Requirement: FLOW-001 用户确认与流程边界

九阶段、三文档确认、适用的预览确认、单一生命周期所有者、单一生产写入者和用户发布授权语义 SHALL 保持不变。

## Out of Scope

- 自适应流程控制晋级、新阶段或新确认门；
- Agent Runtime、多代理调度或并行生产写入；
- 多项目 Workspace/Fleet、Memory 2.0、Engineering OS；
- 通用插件市场、UI 页面、Dashboard；
- SBOM、Sigstore、SLSA 或供应链签名平台；
- 默认授权提交、推送、合并、发布或部署。

## Verification

- 状态服务单元测试：修订、锁、原子写、历史、损坏、事件尾行；
- 迁移测试：合法、损坏、较新状态优先、删除失败和不会复活；
- 证据测试：身份完整、代码/工作项/输入变化失效；
- 发布观察测试：正式成功、仅构建、仅 tag、外部成功本地失败；
- 集成测试：`pre_spec → docs_confirm → spec → quality → delivery_ready → released`；
- Windows/Linux、中文路径和用户目录隔离；
- 全量测试和现有质量/交付门禁。
