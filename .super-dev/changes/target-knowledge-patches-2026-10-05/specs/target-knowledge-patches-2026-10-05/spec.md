# 目标绑定与知识指导补丁规格

## Summary

实现已确认 PRD 的 A-01—A-03、B-01—B-04，基线 a93c121。授权为本次仓库维护，不覆盖旧发布工作项或历史验收。

## MODIFIED Requirements

### Requirement: A-01-bound-spec-quality
SHALL 发布规格质量检查仅评估现有解析器识别的有效目标，不按目录时间、唯一目录或特殊旧名称选择/免检；显式 latest 查询保持原能力。

#### Scenario: Target and unrelated quality differ
- GIVEN 目标与较新无关工作项质量相反
- WHEN 发布入口检查规格且目录时间被反转
- THEN 返回目标工作项的质量，时间变化不影响选择

#### Scenario: Unbound or invalid target
- GIVEN 无绑定、无效绑定、目标目录消失或必要规格缺失
- WHEN 发布入口检查规格
- THEN 不免检通过，报告对应原因，不选择其他目录

### Requirement: A-02-required-target-blocks
SHALL 无有效目标时整体不通过，即使其他检查全部通过；不改既有评分阈值。

#### Scenario: Other checks pass
- GIVEN 必需目标缺失且其他检查全通过
- WHEN 报告聚合
- THEN critical 必检失败使整体不通过

### Requirement: A-03-consumer-compatibility
SHALL 绿色夹具先绑定目标、提供真实规格再水化证据与最终确认，保留原通过断言；CLI/Web 结构、鉴权及只读边界保持。

#### Scenario: Read-only release inspection
- GIVEN 隔离项目和 GET 请求
- WHEN 检查发布就绪
- THEN 返回原结构，不写项目文件，不接受写参数

### Requirement: B-01-knowledge-entry
SHALL 专家引用纳入相关手册、修复 UI/UX 显式路径并保留核心优先；排错/验证失败时 CODE 可从最终提示读取调试手册，其他任务不新增通用必读义务。

#### Scenario: More than three generic files
- GIVEN CODE 已激活且存在多个通用候选和调试手册
- WHEN 真实 AIPromptGenerator.generate() 生成提示
- THEN 最终提示含目标项目的调试手册路径及适用条件，不被通用文件截断

### Requirement: B-02-conditional-guidance
SHALL 专家与 UX 知识按明确适用条件一致执行，重要取舍记录依据，明确容量/校验/安全/使用分析要求不放宽；无关任务不新增基础设施、ADR、次任务、埋点或漏斗。

#### Scenario: Small non-applicable tasks
- GIVEN 无数据库小工具或无使用分析需求的页面
- WHEN 使用本轮指导
- THEN 保持原形态、交互和错误反馈，不追加无关义务

#### Scenario: Explicit capacity requirement
- GIVEN 已给定容量目标
- WHEN 使用本轮架构指导
- THEN 验证目标与瓶颈，不跳过，也不预设必须分片

#### Scenario: Confirmed reliability without a performance bottleneck
- GIVEN 无性能瓶颈，但已确认使用持久化队列实现可靠投递与断网重试
- WHEN 真实最终提示提供架构实施指导
- THEN 保留已确认的队列要求，允许架构、功能、可靠性与容量依据，不以“仅在已验证的瓶颈需要时”否定，不添加无关基础设施

### Requirement: B-03-real-path-tests
SHALL 路径、顺序和条件通过隔离项目的真实 generate 测试，不以候选列表或独立 L3 格式化代替接入证据。

#### Scenario: Missing local knowledge
- GIVEN 隔离项目无知识目录
- WHEN 生成最终提示
- THEN 保留既有自包含指导，不崩溃或要求安装第三方知识平台

### Requirement: B-04-bounded-behavior-evidence
SHALL 四类场景用同宿主、模型配置、输入和权限在独立新上下文比较前后，保留全部原始回答、读取及文件差异；证据缺失如实列明，不声称全面能力提升。

#### Scenario: Diagnosis only
- GIVEN CODE 激活且任务仅要求诊断测试环境失败
- WHEN 执行隔离观察
- THEN 记录实际读取和回答，区分环境/业务，不改业务代码

## Execution Context

生产接口：ReleaseReadinessEvaluator._check_spec_quality、SpecValidator.assess_change_quality、ExpertKnowledge.resolve、AIPromptGenerator.generate。知识对象：knowledge/design/ux-system-deep-dive.md。项目 Python 3.10+；实际验证 Python 3.13.12；现有工具和依赖保持。

## Verification

任务及已确认 PRD 是验收依据；实际结果记录 validation.md/adoption.md 和 output 中原始证据，不把本规格当已执行证据。

## Out of Scope

真实仓库发布验收、旧状态/报告重写、全量 L3 接入、检索/评测平台、自动学习、新角色/阶段/UI/依赖，以及提交、推送、发布和用户级配置。
