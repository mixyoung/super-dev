# P1 证据包规格项目标绑定规格

## Summary

依据用户于 2026-10-06 10:34:37 确认的三文档实施独立小修复。基线提交 a93c121，保留当前未提交的 A/B/P2；不重绑旧发布工作项。

## MODIFIED Requirements

### Requirement: P1-01-bound-target
SHALL 证据包规格项仅评估现有解析器识别的有效绑定目标，不按目录时间、唯一目录或特殊旧名称选择/免检。

#### Scenario: Opposite quality and timestamps
- GIVEN 绑定目标与无关项的质量相反，目录时间可反转
- WHEN 两入口检查规格
- THEN 都评估目标，时间变化不影响结果

#### Scenario: Legacy target name
- GIVEN 目标为 release-hardening-finalization，分别合格或不合格
- WHEN 两入口检查规格
- THEN 同等评估，不按名称免检

### Requirement: P1-02-required-inputs
SHALL 无绑定、无效绑定、目标目录消失或必要规格缺失时，证据包规格项不为 ready，说明实际原因且不改查其他目录。

#### Scenario: Unbound single valid directory
- GIVEN 无绑定但只有一个合格目录，或者没有目录
- WHEN 检查规格项
- THEN 证据包规格项为 pending，无猜测路径；发布规格项不通过

#### Scenario: Invalid or disappearing target
- GIVEN 绑定无效，或目标目录在检查器创建前后消失，或必要规格缺失
- WHEN 两入口检查规格
- THEN 不就绪或不通过，不回退到无关合格项

### Requirement: P1-03-entry-parity
SHALL 两入口在相同隔离项目与有效目标下使用同一指定规格质量结果，不模拟质量报告代替真实验证。

#### Scenario: Actual Web GET
- GIVEN 隔离项目含无绑定或已绑定目标及较新无关项
- WHEN 真实 Web GET 返回发布就绪和证据包
- THEN 两者规格项与有效目标一致，响应保持原形状，输入文件摘要不变

### Requirement: P1-04-compatibility
SHALL 保留字段、状态集合、原整体聚合、评分阈值与显式 latest 查询；单项 ready 不表示整体通过，缺目标不能被其他就绪项抵消。

#### Scenario: Aggregate and payload
- GIVEN 缺目标但其他项均就绪，或目标就绪但另有未就绪项
- WHEN 原报告聚合与序列化
- THEN 整体仍为 incomplete，单项字段不变

#### Scenario: Explicit latest and existing consumers
- GIVEN 显式 latest 查询或既有 CLI/Web 消费者
- WHEN 检查兼容性与只读/鉴权边界
- THEN latest 保持原能力，原消费者通过断言与安全边界不放宽

## Execution Context

生产接口限定为 ProofPackBuilder._spec_quality_artifact 及必要 import。复用 resolve_active_change_id、resolve_work_item_identity 和 SpecValidator.assess_change_quality。Python 3.10+，无新增依赖；无 UI，适用前端/预览路径保持不适用。

## Verification

真实生成器/验证器的隔离测试、真实 Web GET、既有 CLI/Web 和只读/鉴权回归，记录红绿与源码摘要。具体命令和结果写 validation/adoption，不以本规格当作执行证据。

## Out of Scope

其他证据项选择、全局身份解析、readiness 生产修改、阈值/状态体系、真实仓库发布验收、旧状态/报告及 A/B/P2 重写、UI/依赖/角色/平台/阶段、提交/推送/合并/发布/部署。
