# 剩余发布阻碍最小整改记录

## 问题与现有覆盖

基线 main@4881862。Windows CI 原始单元结果为 2592 passed / 23 failed / 2 skipped：11 项编码、7 项路径、3 项 Shell、2 项日志释放。初始化基准曾为 312.75ms>100ms；宿主项目级接入完整但缺用户级 Skill 被扣为 75<80。用户在逐类诊断后明确要求“按最小修法修复”。

## 来源与适用条件

本地原始报告 output/release-baseline-pr5-all；前轮剖析表明重复 YAML 解析和错误工作目录下的知识索引构建是主要初始化热点。沿用已有项目优先、用户级可选、标准流与 SEEAI 分开判断合同。
技术依据：Python pathlib/subprocess 文档（https://docs.python.org/3/library/pathlib.html、https://docs.python.org/3/library/subprocess.html）；Claude Code Hook Shell 合同（https://code.claude.com/docs/en/hooks#exec-form-and-shell-form）。只使用现有 Bash 合同，Windows 查找已安装 Git Bash，不安装解释器或采用 WSL 启动器。

## 取舍与核心影响

明确 UTF-8 文件/输出协议，保留原成功/失败和中文断言；子进程读取按协议解码，不设置全局编码掩盖问题。知识逻辑引用用正斜杠，真实文件身份按 resolve 比较；原路径/证据守卫不降级。日志测试释放自己专用 logger 的处理器，不更改业务日志 API。
Bash Hook 安全内容保持原样，仅显式声明 shell；测试通过实际 Bash 运行，PlanExecutor 使用相同解析器，无可用 Bash 则明确失败。未添加 Shell 执行权限、平台运行程序或新用户入口。
宿主只要求当前模式真正必需的接入面，缺必需/无效合同仍失败；用户级缺项继续报告，未安装任何用户 Skill、未改选定宿主或 80 分阈值。
KnowledgeTracker 增加可选项目目录绑定，但保留既有引用键/构造调用兼容。只缓存规则解析结果（内容键、128 项上限），每次返回深拷贝；同时间戳内容更改也失效，不缓存判定结果或跨项目可变状态。不新增知识索引缓存，因为先纠正扫描范围已消除当前不必要工作。
性能脚本把原阈值判定映射为退出码 0/1；不提高 100ms 阈值、不关闭治理功能。冷启动和首次检查另测，不把重复初始化均值当全部体验。

## 改动范围

- .github/workflows/ci.yml
- .super-dev/changes/release-windows-readiness/proposal.md
- .super-dev/changes/release-windows-readiness/tasks.md
- scripts/check_delivery_ready.py
- scripts/check_host_compatibility.py
- scripts/check_knowledge_gates.py
- super_dev/enforcement/host_hooks.py
- super_dev/host_diagnostics.py
- super_dev/integrations/manager.py
- super_dev/knowledge_tracker.py
- super_dev/orchestrator/governance.py
- super_dev/orchestrator/knowledge.py
- super_dev/orchestrator/plan_executor.py
- super_dev/reviewers/validation_rules.py
- super_dev/utils/shell.py
- tests/benchmark.py
- tests/unit/test_delivery_enhanced.py
- tests/unit/test_delivery_gate_script.py
- tests/unit/test_enforcement.py
- tests/unit/test_frontend_builder_enhanced.py
- tests/unit/test_governance.py
- tests/unit/test_host_compat_gate_script.py
- tests/unit/test_logger.py
- tests/unit/test_plan_executor.py
- tests/unit/test_redteam_enhanced.py
- tests/unit/test_release_minimal_regressions.py
- tests/unit/test_workflow_state.py
- .super-dev/changes/release-windows-readiness/adoption.md

## 验证与未验证

本地 Python 3.13.12 / Mypy 1.20.1。23 个原失败定向重放在本机为 10 failed / 13 passed，差异来自本机编码/路径环境；保留 CI 23 失败与本机报告，两者不互相替代。新增回归先复现非 UTF-8 管道、跨项目索引、重复规则解析和项目级宿主误报；规则测试先纠正缺 category/check_config 的测试样本，再观察重复解析导致失败，未修改产品解析合同。
关联回归 135 passed；宿主/知识/规则/状态回归 369 passed / 2 原有平台跳过。新增缓存深拷贝、同 mtime 内容更新、文件删除、无 Bash、缺必需/无效 Skill、性能退出码检查通过。原发布类型门禁、Ruff、Skill 同步和知识门禁通过。
性能原五项阈值复测全部通过，Engine Init 平均 25.04ms（同机器、原脚本，期间有其他测试负载）。额外冷/热与首次检查测量仍单列，不宣称全部启动都在 100ms 内。完整 Windows 单元、远端矩阵和安全结果尚待最终核对，不以局部通过宣布发布。
原始证据为 output/release-minimal-before.xml、release-minimal-extra-before.xml、release-minimal-focused.xml、release-minimal-related.xml、release-minimal-unit.xml（完成后读取）；只读宿主报告 release-minimal-host-compatibility.json 不修改全局接入或活动绑定。

补充：原 23 项本机定向复跑全部通过（release-minimal-original-23-after.xml）；4 份内置规则文件与基线原加载函数逐字段对照一致。Bandit 与依赖审计均通过。本地完整单元跑到约 63% 后在 test_quality_gate_executive_summary_explains_layered_host_runtime_gap 超时，栈为默认项目目录递归扫描本仓库（包含本地运行环境）；不是已完成结果，不算通过，也没有顺带改该扫描器。完整范围等待干净 CI checkout 的实际结果。

## 决定与回退

执行用户明确批准的最小整改；不修改未授权历史缺陷、正式验收标准或其他 change。通过正常 PR 验证合并，不强推、不管理员绕过。回退只撤本批差异；不把回退后的历史失败标成通过。版本发布与正式 quality/readiness/proof-pack 仍需各自真实证据，不借本批通过代替。

沿用已确认的“Windows 稳定通过后变成真实阻断检查”要求：现有三个 Windows baseline job 保留名称、范围、隔离与证据上传，只让单元失败返回非零；三版本全部通过后再纳入远端必过检查。原五项检查及管理员/PR 保护保留，不扩矩阵或降低条件。
