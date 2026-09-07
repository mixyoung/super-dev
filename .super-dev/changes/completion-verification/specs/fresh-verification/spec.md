# 完成前新鲜验证规格

## Purpose

规定完成前新鲜验证（`fresh-verification`）已实现的执行、证据、裁决与试点边界。

追溯声明 SHALL fresh_verification candidate_digest run_id pytest junit verification_metrics release_readiness。

## ADDED Requirements

### Requirement: 默认关闭与显式配置（`extensions.fresh_verification`）
系统必须（`SHALL`）默认关闭；只有总开关、允许列表和受限计划均合法才执行，启用后的非法配置必须（`MUST`）受阻。
#### Scenario: 未配置时兼容
- GIVEN 项目未启用方法
- WHEN 执行发布就绪
- THEN 保持旧行为且不创建运行
#### Scenario: 启用但参数越界
- GIVEN 参数覆盖核心输出、程序、Shell、绝对路径或父目录
- WHEN 解析计划
- THEN 状态为受阻（`BLOCKED`）且不启动 pytest

### Requirement: 受限 pytest 计划（`parse_pytest_verification_plan`）
核心必须（`SHALL`）只用当前 Python 运行 `python -m pytest`，固定注入 JUnit、`-rX`、缓存关闭、运行目录、临时目录和隔离环境；项目可以（`MAY`）提供计划编号、受限参数和超时。
#### Scenario: 合法计划
- GIVEN 计划只含合法 pytest 选择参数
- WHEN 构造执行请求
- THEN 程序、固定参数和路径均由核心控制

### Requirement: 唯一发布就绪入口（`ReleaseReadinessEvaluator.evaluate`）
只有 `super-dev release readiness` 必须（`SHALL`）显式触发验证；质量、证据包、网页接口和其他调用不得形成第二入口。
#### Scenario: 发布入口与只读调用者
- GIVEN 方法已启用
- WHEN 分别调用发布就绪和证据包
- THEN 只有发布就绪创建运行

### Requirement: 每次新运行与当前代码版本绑定（`run_id`、`candidate_digest`）
每次发布就绪必须（`SHALL`）创建新 `run_id`，不得复用旧通过；运行前后必须（`MUST`）计算当前代码版本摘要，变化时受阻。
#### Scenario: 同一代码连续调用
- GIVEN 当前代码未变化且上次通过
- WHEN 再次执行
- THEN 创建不同 `run_id` 并重跑计划
#### Scenario: 运行中代码变化
- GIVEN 测试期间候选文件变化
- WHEN 重算 `candidate_digest`
- THEN 状态受阻且旧证据失效

### Requirement: JUnit 单一真源与实际执行数（`PytestSummary.executed`）
测试总数、失败、错误、跳过和耗时必须（`SHALL`）来自同次同一 JUnit XML；实际执行数必须（`MUST`）只按“总数减跳过数”派生。缺失、损坏、负数、矛盾、零收集或全部跳过必须受阻。
#### Scenario: 部分跳过
- GIVEN JUnit 有已执行和跳过测试
- WHEN 解析摘要
- THEN 按公式派生且可以通过
#### Scenario: 损坏或全部跳过
- GIVEN JUnit 损坏、矛盾或实际执行数为零
- WHEN 核心裁决
- THEN 状态受阻

### Requirement: pytest 退出码与意外通过提醒（`NON_STRICT_XPASS`）
退出码 0 可以（`MAY`）支持通过，1 表示失败（`FAIL`），中断、内部错误、用法错误、无测试和警告上限必须（`MUST`）受阻；严格意外通过失败，非严格意外通过必须（`SHALL`）从本次简短摘要区聚合成一条提醒且不改变基础状态。
#### Scenario: 非严格意外通过
- GIVEN 本次摘要区含多个 `XPASS` 协议行
- WHEN 生成结果
- THEN 仅生成一条提醒并记录次数
#### Scenario: 日志中的 XPASS 文本
- GIVEN 原因或普通日志含 XPASS
- WHEN 解析输出
- THEN 不生成提醒

### Requirement: 超时取消与进程树（`StructuredExecutor`）
超时、取消、启动失败或不能证明完整清理时必须（`SHALL`）受阻；Windows Job Object 与 POSIX 进程组必须（`MUST`）终止后代并记录清理状态。
#### Scenario: 超时或取消且清理成功
- GIVEN pytest 创建后代进程
- WHEN 超时或取消
- THEN 完整进程树终止且记录 `process_tree_clean=true`
#### Scenario: 无法建立安全控制
- GIVEN 不能建立安全进程控制
- WHEN 尝试启动
- THEN 立即受阻且不留进程

### Requirement: Git 上探边界（`GIT_CEILING_DIRECTORIES`）
核心必须（`SHALL`）为临时测试项目设置 Git ceiling，防止继承父仓库，同时保持真实项目根目录识别有效。
#### Scenario: 仓库内临时项目
- GIVEN pytest 临时目录位于真实仓库下
- WHEN 临时项目查询 Git
- THEN 不把父仓库识别为自身仓库

### Requirement: 原子证据与核心最终裁决（`EvidenceStore`、`ExtensionResult`）
结果、JUnit 和摘要必须（`SHALL`）由核心原子写入运行目录；扩展只返回证据，Core 必须（`MUST`）保留发布、阶段、Git、部署和外部系统最终所有权。
#### Scenario: 证据写入完成
- GIVEN 执行结束且证据合法
- WHEN 保存结果
- THEN 三类证据绑定同一 `run_id` 且主状态不变
#### Scenario: 原子写入失败
- GIVEN 临时写入或替换失败
- WHEN 保存证据
- THEN 部分文件不算完整通过证据

### Requirement: 用户验收指标与十场景回放（`EvidenceStore`、`summarize_verification_metrics`）
系统必须（`SHALL`）执行 10 个唯一场景并记录既定指标；三个真实候选最终标签必须（`MUST`）由用户给出，等待复核不得计入完成指标。
#### Scenario: 完整回放批次
- GIVEN 10 个场景均有明确预期
- WHEN 批次完成
- THEN 记录共享 `replay_run_id` 和当前代码版本摘要
#### Scenario: 批次不完整或身份混杂
- GIVEN 场景缺失、重复、批次或版本混杂
- WHEN 汇总
- THEN 不确认试点收益条件满足

### Requirement: 试点收益观察不派生功能需求（`benefit_criteria_met`、`recommend_stage_2b`）
2026-09-07 用户条件授权撤回程序化排错需求。系统必须（`SHALL`）保留原收益公式、阈值及人工标签，以 `benefit_criteria_met` 记录观察结果；历史兼容字段 `recommend_stage_2b` 必须（`MUST`）恒为 `false`。任何收益结果均不得自动推进九阶段、创建排错需求或代替项目发布门禁。
#### Scenario: 时间指标未达线
- GIVEN 新流程成对正确验收时间中位数不优于旧流程
- WHEN 生成汇总
- THEN `benefit_criteria_met=false`，不把撤回需求当作收益达标
#### Scenario: 历史收益条件全部满足
- GIVEN 完整同版本回放、用户标签和全部原阈值满足
- WHEN 生成汇总
- THEN `benefit_criteria_met=true` 但 `recommend_stage_2b=false`，不产生程序化排错需求

### Requirement: 安全权限与中文首屏（`ReleaseReadinessCheck`、`_completion_verification_check`）
方法必须（`MUST`）拒绝生命周期、编排、生产写入、Git、PR、部署、外部写入和全局安装；首屏必须（`SHALL`）用自然中文显示状态、影响、下一步和证据路径。
#### Scenario: 高风险权限申请
- GIVEN 方法申请高风险权限
- WHEN 核心校验
- THEN 状态受阻且不执行
#### Scenario: 中文结果首屏
- GIVEN 发布就绪完成验证
- WHEN 命令行呈现
- THEN 不只显示裸英文状态并含中文行动说明
