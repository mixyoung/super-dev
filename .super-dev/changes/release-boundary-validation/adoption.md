# 剩余类型与输入边界修复

## 问题与现有覆盖

B 后剩余 9 项。先前已复现 issues=None 引起提取失败；缓存将两种对象装入同一声明，指标和外部数据可能为空。只处理这些已确认范围，不增加新功能。

## 来源与适用条件

用户批准的 release-remediation 三文档，基线 f484d66。Python 3.13.12 / Mypy 1.20.1；数据来自现有报告/契约，网络与数据库验证在隔离测试中执行。

## 取舍与核心影响

合法缺省和正常数据保持；无效 issues 单独告警且不丢后续有效报告；仅明确 bool 写入遵守/违反统计；缓存区分普通与分层并遵守按阶段失效合同。非对象 UI 契约和非文本库名报明确错误，缺运行指标不制造分数。DNS/证书缺有效数据时不得当真实目标通过。无 schema 迁移，无质量阈值或阶段变化。

## 改动范围

- super_dev/memory/extractor.py
- super_dev/knowledge_evolution.py
- super_dev/orchestrator/knowledge_pusher.py
- super_dev/creators/document_generator_content_mixin.py
- super_dev/creators/frontend_builder.py
- super_dev/deployers/rehearsal_runner.py
- tests/unit/test_release_boundary_validation.py
- .super-dev/changes/release-boundary-validation/proposal.md
- .super-dev/changes/release-boundary-validation/tasks.md
- .super-dev/changes/release-boundary-validation/adoption.md

## 验证与未验证

先跑 None、错误类型、False、缺指标、缓存返回/失效、证书/契约边界与正常对照：原实现 15 failed / 9 passed；修复后 24 passed。自定义日志器不传播到 caplog，测试改为调用真实 warning 的 spy，未改变产品日志配置或删掉告警断言。相关回归 244 passed / 1 failed，唯一失败是基线已有 Windows 文件名问题，未隐藏。原类型门禁通过，无新 ignore/cast，Ruff 与编译检查通过。网络使用模拟响应，存储仅临时目录；证据 output/release-boundaries-regression.xml、release-type-gate-pass.json，完整发布尚待 D。

## 决定与回退

按已确认 C 批执行，回退只撤本批差异。保持原五项 CI 与主线保护，不以局部成功宣布发布完成。
