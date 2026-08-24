# Windows 测试基础与用户目录隔离规格

## Summary

为 Super Dev 建立安全、可重复、跨平台的测试基础。Windows 测试必须使用唯一临时用户目录，任何真实用户级接入位置的变化都必须被发现；历史失败与隔离后的当前结果分别保存。

## ADDED Requirements

### Requirement: isolated-user-directory

系统 SHALL 为可能访问用户级文件的测试提供唯一临时用户目录，并让 `HOME`、`USERPROFILE`、`HOMEDRIVE`、`HOMEPATH`、`CODEX_HOME`、XDG 目录、`Path.home()`、`expanduser()` 和两个管理器解析到同一位置。

#### Scenario 1: Windows 用户目录一致
- GIVEN 测试运行在 Windows
- WHEN 公共隔离条件建立临时用户目录
- THEN 所有用户目录变量和路径解析结果指向同一临时目录
- AND 测试不得创建第二套 `fake_home`

#### Scenario 2: 默认产品行为兼容
- GIVEN 正常用户没有传入目录说明对象
- WHEN 技能管理或宿主接入解析用户级位置
- THEN 继续使用当前真实系统目录
- AND 不根据“是否测试环境”改变业务行为

### Requirement: complete-user-surface-protection

系统 SHALL 从技能管理和宿主接入的完整用户级入口生成真实保护范围，不得使用手写短名单或按文件类别过滤。

#### Scenario 1: 完整接入面
- GIVEN `SkillManager` 或 `IntegrationManager` 声明用户级路径
- WHEN 安全入口生成保护范围
- THEN 正式、兼容、镜像、协议、命令、技能、智能体和可选用户文件全部进入摘要
- AND 代码声明范围与摘要覆盖范围不一致时隔离自检失败

#### Scenario 2: 主目录外 Codex 位置
- GIVEN `CODEX_HOME` 位于用户主目录外
- WHEN 测试运行前后生成摘要
- THEN 该位置使用完整规范化绝对路径作为内部比较键
- AND 面向人的报告可以脱敏但不得漏检

### Requirement: windows-path-identity

系统 SHALL 使用统一的 Windows 路径同一性规则保护临时目录和真实摘要。

#### Scenario 1: 大小写和盘符别名
- GIVEN 两个路径在 Windows 上指向同一位置但大小写、盘符或分隔符写法不同
- WHEN 系统比较目录或摘要键
- THEN 先解析真实位置并规范化
- AND 将它们视为同一路径

#### Scenario 2: 逃逸路径
- GIVEN 临时目录通过 `..`、符号链接或目录连接指向受保护位置
- WHEN 安全入口验证目录
- THEN 拒绝运行高风险测试

### Requirement: safe-baseline-runner

系统 SHALL 提供不依赖 Bash 的固定范围安全入口，并分别报告隔离安全、测试结果和证据完整性。

#### Scenario 1: 普通测试失败但隔离安全
- GIVEN 隔离自检通过且真实目录没有变化
- WHEN pytest 返回普通测试失败
- THEN 保存失败证据并显示“测试未全部通过”
- AND 不把它误报为隔离失败或全部通过

#### Scenario 2: 真实目录变化
- GIVEN 运行前后真实保护范围发生变化
- WHEN 安全入口完成比较
- THEN 结果为不安全
- AND 停止更宽检查
- AND 不自动删除或恢复真实文件

### Requirement: baseline-history

系统 SHALL 分开保存历史失败口径和隔离后的当前基线。

#### Scenario 1: 历史重叠
- GIVEN 历史 55 项较宽检查失败中包含 35 项用户目录失败
- WHEN 写入失败登记表
- THEN 35 项同时具有较宽检查和用户目录范围标签
- AND 明确 `35 ⊆ 55`

#### Scenario 2: 定向历史
- GIVEN 更早的 Windows 定向检查有 10 项失败
- WHEN 写入失败登记表
- THEN 使用独立定向标签
- AND 允许与 55 项部分重叠
- AND 禁止把 10、55、35 相加

#### Scenario 3: 隔离后结果
- GIVEN 用户目录隔离已经生效
- WHEN 重新运行检查
- THEN 新结果使用独立的当前基线标识
- AND 历史失败转为通过时仍保留历史记录

### Requirement: windows-evidence-matrix

系统 SHALL 在 GitHub 持续检查中实际运行 Windows Python 3.10、3.11、3.12 基线并上传证据。

#### Scenario 1: 三版本证据
- GIVEN 阶段 0 分支触发持续检查
- WHEN Windows 基线任务运行
- THEN 三个 Python 版本分别产生环境、JUnit、日志、摘要和失败登记证据

#### Scenario 2: 安全失败
- GIVEN 隔离失败、真实目录变化或证据缺失
- WHEN Windows 基线任务结束
- THEN 任务失败

## Acceptance Checklist

- [x] AC1: 唯一临时用户目录在 Windows 上可证明生效
- [x] AC2: 两个高风险测试文件不再接触真实用户位置
- [x] AC3: 完整宿主用户级接入面自动进入摘要
- [x] AC4: 主目录外 `CODEX_HOME` 被覆盖
- [x] AC5: Windows 路径同一性和逃逸检查通过
- [x] AC6: 历史和当前失败登记可追溯且不相加
- [x] AC7: Windows 3.10、3.11、3.12 证据可取得
- [x] AC8: 默认产品行为保持兼容

## Out of Scope

- 扩展平台和外部能力接入
- 全部 Windows 产品问题清零
- 完整产品写入守卫
- 图形界面
- 九阶段真实控制
- 合并、推送和用户级 Skill 同步
