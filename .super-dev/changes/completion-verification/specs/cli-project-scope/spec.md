# 命令行根项目范围规格
## Purpose
规定根项目作为命令行产品的阶段判定，不混入官网与示例。

追溯声明 SHALL platform cli frontend none backend python workflow_state catalog config。
## ADDED Requirements
### Requirement: 根项目技术范围（`platform=cli`、`frontend=none`、`backend=python`）
根配置必须（`SHALL`）声明命令行、无前端和 Python 后端；目录与校验器必须（`MUST`）接受这些真实值。
#### Scenario: 读取根配置
- GIVEN 读取 `super-dev.yaml`
- WHEN 分析范围
- THEN 得到 `cli`、`none`、`python`
### Requirement: 无前端跳过前端与预览门（`detect_pipeline_summary`）
前端为 `none` 时系统必须（`SHALL`）跳过前端运行和预览确认要求，不得写伪造预览确认。
#### Scenario: CLI 阶段判断
- GIVEN 根项目无前端
- WHEN 计算下一阶段
- THEN 不因缺少前端或预览确认受阻
### Requirement: 根 Python 包满足后端阶段（`root_python_backend_done`）
后端为 Python 且根目录有 `super_dev` 包和项目元数据时，系统必须（`SHALL`）识别为后端实现，不要求 `backend/` 脚手架。
#### Scenario: 根包存在
- GIVEN `super_dev/` 与 `pyproject.toml` 存在
- WHEN 判断后端
- THEN 后端实现面成立
### Requirement: 官网与示例独立子项目
官网 `super-dev-website/` 和示例必须（`MUST`）独立处理，不得把根 CLI 标成有前端或替代当前证据。
#### Scenario: 官网存在
- GIVEN 仓库有官网或示例前端
- WHEN 分析根配置
- THEN 根项目仍为无前端 CLI
### Requirement: 九阶段名称保持不变（`STANDARD_PHASE_CHAIN`）
范围适配必须（`SHALL`）只改变阶段要求，不得更名、删除或新增九阶段名称。
#### Scenario: 范围适配后
- GIVEN 无前端门被跳过
- WHEN 输出阶段表
- THEN 九阶段名称集合不变
