# 最小扩展平台规格

## Summary

为 Super Dev 建立默认关闭的最小扩展合同，严格限制来源、能力、所有权、写入、命令执行和证据复用；阶段 1 只提供内置合同探针。

## ADDED Requirements

### Requirement: disabled-by-default

系统 SHALL 在缺少扩展配置或 `extensions.enabled=false` 时关闭全部扩展加载与执行。

#### Scenario 1: 旧项目没有扩展配置
- GIVEN 项目配置没有 `extensions`
- WHEN Core 加载项目
- THEN 扩展状态为关闭
- AND 不读取扩展清单
- AND 不启动扩展子进程

#### Scenario 2: 显式关闭
- GIVEN `extensions.enabled=false`
- WHEN 用户执行普通 Super Dev 流程
- THEN 扩展内核不改变 Core 阶段、输出或证据

### Requirement: strict-manifest

系统 SHALL 使用版本化严格合同校验扩展清单，并拒绝未知字段、未知枚举、非法路径和缺失必填字段。

#### Scenario 1: 合法内置清单
- GIVEN 清单包含版本、编号、来源、阶段、能力、所有权、写入、权限、执行和结果合同
- WHEN 维护者校验清单
- THEN 返回通过
- AND 不执行扩展

#### Scenario 2: 未知字段或能力
- GIVEN 清单包含未知字段或未知能力
- WHEN 维护者校验清单
- THEN 返回字段级错误
- AND 不静默忽略

#### Scenario 3: 项目清单请求执行
- GIVEN 清单不是仓库内置受信适配器
- WHEN 请求执行
- THEN 返回 `BLOCKED`
- AND 不运行项目或远程代码

### Requirement: source-lock

系统 SHALL 在每次执行前核对清单、来源锁和本地内容摘要。

#### Scenario 1: 内置来源匹配
- GIVEN 内置适配器的仓库路径和 SHA-256 与来源锁一致
- WHEN 请求运行合同探针
- THEN 来源校验通过

#### Scenario 2: 内容漂移
- GIVEN 本地适配器内容与来源锁摘要不同
- WHEN 请求运行
- THEN 返回 `BLOCKED`
- AND 不自动更新来源锁

#### Scenario 3: 外部改编来源合同
- GIVEN 清单类型为外部改编
- WHEN 校验来源字段
- THEN 必须包含上游仓库、完整提交、路径和摘要
- AND 阶段 1 仍不下载或执行该来源

### Requirement: ownership-and-capabilities

系统 SHALL 将清单能力视为申请，并由 Core 根据可信能力和所有权规则裁决。

#### Scenario 1: 缺少能力
- GIVEN 扩展需要 `run_commands`
- AND Core 没有提供该可信能力
- WHEN 请求运行
- THEN 返回 `NOT_APPLICABLE`

#### Scenario 2: 申请生命周期或高风险权限
- GIVEN 清单申请生命周期、编排、生产写入、Git、PR、部署、外部写入或全局安装权限
- WHEN 校验所有权
- THEN 返回 `BLOCKED`

#### Scenario 3: 自报能力
- GIVEN 清单声明自身只读或幂等
- WHEN Core 没有可信证明
- THEN 不根据自报声明提升权限

### Requirement: path-guard

系统 SHALL 使用真实路径和跨平台路径身份判断允许写入，并拒绝所有逃逸和永久禁止范围。

#### Scenario 1: 正常证据写入
- GIVEN Core 创建 `.super-dev/extensions/runs/<run-id>`
- WHEN 内置合同探针写结果
- THEN 写入被允许

#### Scenario 2: 路径逃逸
- GIVEN 候选路径通过 `..`、大小写别名、符号链接、目录连接、UNC 或不同盘符指向允许根外
- WHEN 检查写入
- THEN 返回 `BLOCKED`

#### Scenario 3: 永久禁止路径
- GIVEN 候选路径位于 `.git`、主工作流状态、真实用户目录或仓库外
- WHEN 检查写入
- THEN 返回 `BLOCKED`

### Requirement: candidate-evidence

系统 SHALL 将扩展结果绑定当前仓库、提交、未提交差异、暂存内容、未跟踪文件和工作区身份。

#### Scenario 1: 候选身份完整
- GIVEN 项目包含已提交、未提交、暂存或未跟踪变化的任意组合
- WHEN 生成候选身份
- THEN 每类状态都有稳定摘要
- AND 组合为候选摘要

#### Scenario 2: 候选变化
- GIVEN 已存在扩展结果
- WHEN 代码、测试、配置、暂存或未跟踪清单变化
- THEN 旧结果判定为失效
- AND 记录 `ExtensionEvidenceInvalidated`

### Requirement: structured-executor

系统 SHALL 使用程序和参数列表运行命令，固定工作目录，使用最小环境，并限制超时与输出。

#### Scenario 1: Shell 字符作为普通参数
- GIVEN 参数包含空格、中文、管道符或重定向符
- WHEN 使用结构化执行器运行 Core 白名单中的当前 Python 解释器
- THEN 参数不经过 Shell 解释

#### Scenario 2: 禁止脚本类型
- GIVEN 程序是 `.cmd`、`.bat`、`.ps1` 或 Shell 脚本
- WHEN 请求运行
- THEN 返回 `BLOCKED`

#### Scenario 3: 输出和凭据
- GIVEN 子进程输出超过限制或包含敏感字段
- WHEN 保存结果
- THEN 输出被截断并保留摘要
- AND 敏感值被脱敏

### Requirement: process-tree-cleanup

系统 SHALL 在超时、取消和异常时结束完整子进程树并记录是否清理完成。

#### Scenario 1: Windows 孙进程
- GIVEN Windows 子进程创建孙进程
- WHEN 执行超时
- THEN Job Object 结束完整进程树
- AND `process_tree_clean=true`

#### Scenario 1A: Windows 启动竞态
- GIVEN Windows 准备运行目标程序
- WHEN 创建进程
- THEN 受信启动器先等待
- AND 启动器加入 Job Object 后才放行目标程序

#### Scenario 2: POSIX 孙进程
- GIVEN POSIX 子进程创建孙进程
- WHEN 执行超时
- THEN 独立进程组被终止
- AND 没有存活子进程

#### Scenario 3: 无法建立安全进程组
- GIVEN 执行器无法建立 Job Object 或进程组
- WHEN 请求执行
- THEN 立即终止新进程
- AND 返回 `BLOCKED`

### Requirement: hook-migration

系统 SHALL 将新配置型命令 Hook 路由到结构化执行器，并阻止旧命令字符串继续执行。

#### Scenario 1: 新结构化 Hook
- GIVEN Hook 声明程序和参数列表
- WHEN Hook 触发
- THEN 通过结构化执行器运行

#### Scenario 2: 旧字符串 Hook
- GIVEN Hook 使用旧 `command: "..."` 字符串
- WHEN Hook 触发
- THEN 不执行字符串
- AND 返回 `BLOCKED`
- AND 提供结构化迁移示例

#### Scenario 3: Python 和日志 Hook
- GIVEN Hook 是代码内可信 Python 回调或日志 Hook
- WHEN Hook 触发
- THEN 保持现有兼容行为

#### Scenario 4: YAML 伪 Python Hook
- GIVEN YAML 使用 `type: python`
- WHEN Hook 触发
- THEN 不把模块路径当命令执行
- AND 返回明确迁移说明

### Requirement: evidence-store

系统 SHALL 由 Core 原子写入单次结果并追加最小扩展事件历史，不写主工作流状态。

#### Scenario 1: 成功运行
- GIVEN 内置合同探针通过全部前置检查
- WHEN 运行完成
- THEN 写入版本化 `result.json`
- AND 追加请求、开始和完成事件

#### Scenario 2: 阻断运行
- GIVEN 来源、所有权、路径、进程或证据检查失败
- WHEN Core 处理结果
- THEN 追加阻断事件
- AND 主工作流状态不变

#### Scenario 3: 损坏历史
- GIVEN 历史中包含损坏行
- WHEN 读取最近历史
- THEN 跳过损坏行并返回警告
- AND 不推进阶段

### Requirement: maintenance-cli

系统 SHALL 提供清单校验、检查、来源核对、内置合同探针和历史查看入口，并使用稳定退出码和中文摘要。

#### Scenario 1: 只读检查
- GIVEN 维护者调用 `validate`、`inspect` 或 `verify-source`
- WHEN 命令完成
- THEN 不执行真实扩展
- AND 不修改用户级配置

#### Scenario 2: 合同探针
- GIVEN 扩展已显式启用并允许 `contract-probe`
- WHEN 维护者运行 `probe-contract`
- THEN 只运行仓库内置测试适配器
- AND 不接入真实产品方法

#### Scenario 3: 退出码
- GIVEN 结果为通过、阻断、不适用、未通过或内部错误
- WHEN CLI 结束
- THEN 分别使用 0、2、3、4 或 5

## Acceptance Checklist

- [x] AC1: 扩展默认关闭且不启动扩展操作
- [x] AC2: 严格清单拒绝未知和越界输入
- [x] AC3: 来源锁和内容摘要在运行前核对
- [x] AC4: 所有权和高风险权限申请全部拒绝
- [x] AC5: 路径逃逸和永久禁止范围全部拒绝
- [x] AC6: 候选身份完整且变化后证据失效
- [x] AC7: 命令不经过 Shell 字符串
- [x] AC8: Windows/POSIX 超时后无存活子进程
- [x] AC9: 旧 Hook 字符串被阻止且有迁移说明
- [x] AC10: Python 回调和日志 Hook 保持兼容
- [x] AC11: Core 独占扩展历史写入且不改主工作流状态
- [x] AC12: 维护入口和退出码符合合同
- [x] AC13: 阶段 1 没有真实外部方法接线
- [x] AC14: 真实用户目录变化为 0

## Out of Scope

- 动态注册、解析、发现和远程安装
- 真实外部工程方法与知识覆盖
- 新图形界面
- 第二生命周期或九阶段控制变更
- 用户级 Skill、配置、提交、合并、推送、PR 或部署
