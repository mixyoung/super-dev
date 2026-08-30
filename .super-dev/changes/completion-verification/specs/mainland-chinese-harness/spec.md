# 中国大陆中文 Harness 规格
## Purpose
规定根规则、兼容镜像和唯一技能模板中已同步的中文合同。

追溯声明 SHALL mainland chinese candidate_digest skill_template claude codex harness。
## ADDED Requirements
### Requirement: 自然中文与术语首次双名（`SkillTemplate._section_language_and_environment`）
面向中国大陆用户必须（`SHALL`）使用自然中文；技术概念首次必须（`MUST`）写中文名称（英文代码名），后续应该（`SHOULD`）只用中文。
#### Scenario: 首次与后续提及
- GIVEN 首次介绍技术字段
- WHEN 生成说明
- THEN 首次双名，后续优先中文
### Requirement: 三状态与当前代码版本术语
状态必须（`SHALL`）显示通过（`PASS`）、失败（`FAIL`）、受阻（`BLOCKED`）；`candidate` 必须（`MUST`）称当前代码版本，仅证据详情保留 `candidate_digest`。
#### Scenario: 结果展示
- GIVEN JSON 含摘要和英文状态
- WHEN 生成首屏
- THEN 显示中文状态与当前代码版本
### Requirement: 精确字段使用代码格式（`SkillTemplate._section_language_and_environment`）
命令、文件名和程序字段必须（`SHALL`）保留原文并用代码格式；解释必须（`MUST`）先用中文，内部字段不得直接充当用户文案。
#### Scenario: 命令与路径说明
- GIVEN 需要核对命令和文件
- WHEN 输出说明
- THEN 精确字段用反引号且解释为中文
### Requirement: 根规则兼容镜像与唯一技能模板同步（`SkillTemplate`）
根 `CLAUDE.md`、兼容镜像及 Codex/Claude Skill 必须（`SHALL`）含相同合同；生成副本必须（`MUST`）由唯一模板生成并逐字同步。
#### Scenario: 生成副本一致
- GIVEN 渲染两类 Skill
- WHEN 与受控副本比较
- THEN 对应内容逐字一致
#### Scenario: 任一镜像漂移
- GIVEN 手工修改生成副本
- WHEN 执行合同测试
- THEN 测试失败
