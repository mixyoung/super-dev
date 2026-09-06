# 行为不变的类型表达修正

## 问题与现有覆盖

环境补齐后 63 项诊断中，大量来自重复 get 判断不能收窄、不同分支变量混用类型和声明不符合实际返回结构。按用户已确认计划只做局部类型修正。

## 来源与适用条件

基线 20138c2；Python 3.13.12 / Mypy 1.20.1，原诊断 output/release-after-env-type-gate.json。针对现有生成器和内部结构，不改公开字段与生成路径。

## 取舍与核心影响

取值一次后用原 isinstance 条件收窄；区分路径列表和文件映射；台账注解符合实际列表；引擎专家列表使用明确局部变量。保留 mixin 与流程，不新增 ignore、cast 或检查器配置。需行为修复的边界留到 C 批。

## 改动范围

- super_dev/creators/frontend_builder.py
- super_dev/creators/document_generator_content_mixin.py
- super_dev/creators/task_executor.py
- super_dev/change_ledger.py
- super_dev/orchestrator/engine.py
- tests/unit/test_release_type_contracts.py
- .super-dev/changes/release-type-contracts/proposal.md
- .super-dev/changes/release-type-contracts/tasks.md
- .super-dev/changes/release-type-contracts/adoption.md

## 验证与未验证

复用前端/文档、台账、任务和流程测试，新增 10 个框架分派及 1 个台账往返检查。结果 166 passed / 1 failed；失败与改动前相同，为 Windows 非法项目名路径，未删除/跳过断言。修正了新测试中 Ionic kind 的初始错误期望，原生产 kind 未改变。React/Vue/Next/Tauri 共 32 个方法和 HTML/CSS/JS 输出与 main 基线逐项相同。类型诊断从 63 降到 9；原门禁仍未通过。Ruff 通过，只对修改行执行 Black 格式化，未全文件重排历史代码。证据 output/release-types-after-pytest.xml；完整发布尚未通过。

## 决定与回退

按已确认 B 批执行。回退仅撤回本批差异，不回滚 A 的工具、不改其他 change 状态。通过正常 PR 合并，不绕过主线保护。
