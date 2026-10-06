# 质量扫描效率整改吸纳记录

## 问题与现有覆盖

基线 a93c121。三类合规扫描与规则内容检查重复递归后过滤；现有 repo_map/redteam 已有预剪枝，代码身份已有 Git 差异和内容摘要。本批统一适用质量路径，不创建第二流程。

2026-10-06 路径返工基线为已提交的 `00fa50b`。PR 的三个 Windows 必需检查各有 25 项发布就绪测试失败，均为短路径与完整路径比较不一致，不是超时。隔离该提交、仅将测试进程的临时目录设为真实短路径后，本机也复现相同的 25 项失败；未混入其他工作项的发布就绪代码或夹具改动。

## 来源与适用条件

本地已确认三文档及研究记录 output/quality-scan-efficiency-2026-10-06-research.md。外部来源固定为 UmaDev 4fe51fa、Superpowers 8ca22db 和已核对 Git/Python 官方文档。借鉴剪枝、同次复用和真实验证；不安装外部技能、不复制运行时。测试与调试知识按研究记录适用，生产监控条款冲突已随三文档明确批准本地诊断边界。

路径返工核对 [Python 3.10 pathlib](https://docs.python.org/3.10/library/pathlib.html)、[CPython 3.10.16 实现](https://raw.githubusercontent.com/python/cpython/v3.10.16/Lib/pathlib.py) 与 [GetShortPathNameW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getshortpathnamew)（2026-10-06）。`resolve()` 会跟随链接，因此不能替代逐层的原始路径检查；Windows API 只用于测试构造真实短路径，生产处理仍使用跨平台标准库。该方法适用于本轮扫描路径与调用内报告，不扩展为全仓路径重构。

## 取舍与核心影响

用户通过本会话计划确认三文档后授权实现。正常输入的范围与评分不变；应检文件不可读或扫描失效从静默跳过改为明确受阻，必要检查不得由高分抵消。该证据完整性影响已在确认文档显式说明，不伪称完全无语义变化。保持时限、阶段、阈值与确认权。

用户随后以“按建议执行”确认路径统一修复。内部索引统一为规范化绝对 `Path`，外部仍接受短路径、完整路径与相对路径；未解析的组件先按顺序检查链接，不能提前消去 `link/..`。通配符仅规范化固定前缀，必要输入与报告索引使用实际返回路径，发布前再次核对报告祖先。保持大小写变动检测和原排除策略；不修改系统短文件名设置、全局临时目录、分支保护或 CI 门槛。路径检查有额外文件系统操作，其开销按本次重新测量，不沿用上一版性能成绩。

## 改动范围

- super_dev/reviewers/source_inventory.py
- super_dev/reviewers/spec_compliance.py
- super_dev/reviewers/architecture_drift.py
- super_dev/reviewers/uiux_compliance.py
- super_dev/reviewers/validation_rules.py
- super_dev/reviewers/quality_gate.py
- tests/unit/test_source_inventory.py
- tests/unit/test_quality_scan_inventory.py
- tests/integration/test_quality_scan_entrypoints.py
- output/quality-scan-efficiency-2026-10-06-research.md
- output/quality-scan-efficiency-2026-10-06-prd.md
- output/quality-scan-efficiency-2026-10-06-architecture.md
- output/quality-scan-efficiency-2026-10-06-uiux.md
- output/quality-scan-efficiency-2026-10-06-execution-plan.md
- output/quality-scan-efficiency-2026-10-06/benchmark_scan.py
- output/quality-scan-efficiency-2026-10-06/discovery-benchmark.json
- output/quality-scan-efficiency-2026-10-06/verification-inputs.json
- .super-dev/changes/quality-scan-efficiency-2026-10-06/proposal.md
- .super-dev/changes/quality-scan-efficiency-2026-10-06/plan.md
- .super-dev/changes/quality-scan-efficiency-2026-10-06/checklist.md
- .super-dev/changes/quality-scan-efficiency-2026-10-06/tasks.md
- .super-dev/changes/quality-scan-efficiency-2026-10-06/specs/source-inventory/spec.md
- .super-dev/changes/quality-scan-efficiency-2026-10-06/change.yaml
- .super-dev/changes/quality-scan-efficiency-2026-10-06/adoption.md
- .super-dev/changes/quality-scan-efficiency-2026-10-06/validation.md

## 验证与未验证

首轮修改前，项目 Python 3.13.12 下合规身份、架构否定、规则三文件 108 项通过，14.60 秒。首轮最终冻结源码的来源/规则、质量门、顾问与相关 CLI/Web、贡献政策四组共 304 项通过、1 项条件跳过；Ruff、Black、237 文件 Mypy 和 wheel/sdist 构建通过。中间失败、一次宿主批量验证超时、分组复核命令、原始 XML/日志、平台边界均记录在本工作项 validation.md，不把中间版本成绩当最终证据。

首轮同解释器三轮合成树文件发现中位数 19.188 秒降至 1.478 秒，所有消费者集合一致；根发现/复核从九次变两次。真实工作区原模式 30 秒未完成，新路径发现加复核 2.653 秒；这些历史数字不作为路径返工后的性能成绩。

本次路径返工在 Windows 的 Python 3.10.19、3.11.9、3.12.12 下分别为 226 项通过、1 项条件跳过；3.13.12 的四组不重复回归合计 366 项通过、1 项条件跳过。每个版本的原发布就绪文件均从 25 项失败恢复为 31 项全部通过；普通目录符号链接测试因本机权限条件跳过，真实短路径和目录连接点测试均执行通过。隔离提交代码的静态、类型、安全扫描与构建以及适用治理检查均完成；未改旧断言、阈值或时限。

本轮路径检查增加了开销：对上一提交的发现微基准中位数由 1.085 秒变为 1.751 秒；对最初递归后过滤算法的同环境对照仍为 15.776 秒降至 1.790 秒，集合一致。完整结果、停止过的隔离不足批次、最终测试环境与清理记录见 validation.md 第 9 节。未运行整仓全测试、正式发布验收或新的远端 CI；Linux/macOS 未验证。不把本地目标回归通过说成远端已可合并。

## 决定与回退

采用已确认最小修复；不改根活动绑定、旧报告或其他任务未提交改动。若文件集合/结论变化或资源收益不成立，仅撤本批差异并重验。首轮交接后，用户追加授权本批提交，并进一步授权推送、创建合并至 main 的 PR 与切换已有凭证；原提交已进入 [mixyoung/super-dev#22](https://github.com/mixyoung/super-dev/pull/22)，这些操作均不包含其他任务差异。

路径返工验收交接时，依据用户“按建议执行”的实施授权完成本地修改和验证，未自动推送修复。随后用户明确追加“提交并推送，更新现有 PR”，本轮仅获准提交这次已验证的路径修复、测试和工作项记录，推送既有分支并更新现有 PR；不包含其他任务差异、实际合并、自动合并、发布或部署。回退只撤本次 `source_inventory.py`、其新增测试及对应返工材料的差异，保留首轮已提交的预剪枝整改与所有其他任务文件。
