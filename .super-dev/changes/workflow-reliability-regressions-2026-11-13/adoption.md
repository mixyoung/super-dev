# 七项工作流可靠性缺陷修复维护记录

## 问题与现有覆盖

本会话的只读复核确认七项既有约束未被完整执行：运行中确认失效后仍可进入后续阶段；界面项目缺少预览证据仍放行；失败运行报告可支持预览确认；质量验收前保存成功检查点；非对象 JSON 可借历史快照覆盖主状态；无身份旧项目以不完整文档通过确认；新工作项汇总借用旧产物并从下游文件倒推用户确认。

现有统一状态服务、摘要绑定、确认门和工作项解析均保留，修复复用这些权威入口，不建立替代流程。原有针对性测试多数通过但没有覆盖上述反例，因此新增稳定失败回归及合法兼容对照。模式判定使用共享解析：明确模式优先；仅在缺少明确模式时保留 SEEAI 的旧字段及步骤标签兼容，避免为旧 SEEAI 项目新增预览确认门。

## 来源与适用条件

- 本地基线：`26b0cb6c98e723b8c12c4d721785a9cb91d6f761`，2026-11-13 开始本轮维护；后续验证跨日至 2026-11-14。
- 用户直接要求“修复这 7 项问题，并补齐回归测试”，并批准本轮实施方案 `sparkling-doodling-ripple`。
- 复用 `output/super-dev-2-6-reliability-{research,prd,architecture,uiux}.md` 中状态可信、证据失效、独立确认、旧项目兼容及不扩大授权的约束；历史发布批准不充当本次执行批准。
- 仓库准则及适用方法：`docs/CONTRIBUTION_POLICY.md`、`CONTRIBUTING.md`、`knowledge/00-governance/{maintenance-policy,review-checklist}.md`；仅用于本地确定性维护、失败用例、正反例及真实证据记录，不修改知识或引入新方法品牌。
- 适用于标准流程的确认与执行、旧引擎阶段恢复、文件型状态和宿主状态汇总；普通无前端项目继续免预览确认，SEEAI 按既有合同不增加中途人工预览门。
- 不适用于 DSH 接入范围变更、版本升级、宿主安装/同步、全局配置、凭据、真实模型调用或发布部署。

## 取舍与核心影响

恢复原有合同，不改变九阶段、用户确认权、项目质量阈值或发布权限。适用性、运行证据就绪与确认摘要匹配分开计算；缺少证据不再等于不适用。旧项目仍可使用完整、同前缀的三文档，不强制先迁移身份；明确身份的工作项不退回全局扫描。

预览确认保留完整附件清单和原摘要作为审计信息，并新增稳定的预览目标摘要，绑定当前运行报告和 UI 契约。QA 刷新评审/对齐附件不额外制造一次人工预览审批；既有质量检查、UI 审查和返工要求不被取消。旧格式确认仍按其原完整摘要核对，不能无证据自动升级为有效确认。

阶段结果完成验收后才生成成功副作用；恢复检查点携带验收版本、工作项、文档/预览目标及有效技术栈，缺少依据或与当前输入不符时重跑。存储校验拒绝非对象主状态，执行及确认入口也拒绝把损坏/缺失主文件的历史降级读取当成执行授权；只读恢复候选和显式恢复接口保留。

当前 Orca 探测返回 `runtime_unavailable`，未启动或改动其安装；本宿主为唯一生产写入者，审查者只读。维护记录不激活第二工作流，不修改现有 `super-dev-dsh-desktop` 状态、确认或未提交改动。

## 改动范围

- .super-dev/changes/workflow-reliability-regressions-2026-11-13/adoption.md
- .super-dev/changes/workflow-reliability-regressions-2026-11-13/tasks.md
- .super-dev/changes/workflow-reliability-regressions-2026-11-13/validation.md
- super_dev/cli.py
- super_dev/cli_spec_mixin.py
- super_dev/creators/task_executor.py
- super_dev/orchestrator/engine.py
- super_dev/state_store.py
- super_dev/web/api.py
- super_dev/workflow_guard.py
- super_dev/workflow_stage_truth.py
- super_dev/workflow_state.py
- tests/integration/test_cli.py
- tests/integration/test_web_api.py
- tests/integration/test_workflow_reliability_boundaries.py
- tests/support/workflow_reliability.py
- tests/unit/test_cli_resume.py
- tests/unit/test_host_runtime_probe.py
- tests/unit/test_task_executor.py
- tests/unit/test_workflow_guard_active_change.py
- tests/unit/test_workflow_reliability_regressions.py
- tests/unit/test_workflow_state.py

## 验证与未验证

修复前的首批新增回归在隔离用户目录下得到 `34 failed, 8 passed`，失败覆盖七项原问题。最初未隔离整个 pytest 进程的尝试被真实 `~/.dsh` 连接点安全检查阻断，未进入用例；未修改真实目录或放宽保护断言。

最终完整 `tests/` 目录精确收集 3898 个唯一用例，四个分区及环境补测去重后为 **3891 通过（PASS）、7 跳过、0 失败**；120 项新增参数化回归全部实际执行并通过。收集清单与分区并集精确一致，每个收集节点都有终态；各分区运行前后及当前代码/测试/配置摘要一致。保留的跳过为本机符号链接能力、POSIX 语义及原混合宿主约定，不是本轮新增跳过。八项因 Git 路径布局而跳过的隔离脚本测试已在仅修正测试进程 PATH 后补测通过，没有真实发布或推送。

Ruff 全生产目录及相关测试、Black 19 个文件、Mypy 9 个受影响模块、贡献范围、只读 Skill 同步及差异检查均通过（PASS）。隔离 wheel/sdist 构建及包元数据检查通过，九个修复模块与 wheel 内文件逐字节一致；版本和质量阈值未变。

独立只读复核发现的旧 SEEAI 元数据及损坏历史边界已先补失败回归再修正；真实文档生成还覆盖产品展示名与工作项身份不同的情况，汇总恢复原有必要基线优先级。最终增量复核无范围内确定遗留问题。首次完整目录诊断的七项失败已逐项处理，原断言保留，而不是把诊断失败混入最终通过次数。

原有 DSH 用户文件保持原状；共享 CLI 测试仅在三个方法中补前置夹具，其余内容与用户原始未提交版本逐字节一致。工作流文件的并行修订 22 未被本轮回滚或覆盖。完整命令、环境、去重覆盖、输入摘要、构建哈希、跳过原因、原始日志及未覆盖环境见 `validation.md` 和 `output/workflow-reliability-regressions-2026-11-13/verification/`。这不代表正式发布就绪评分或真实宿主/模型运行验证，也未获得合并、发布或部署授权。

## 决定与回退

决定：按用户已批准的七项纠错范围实施并验证。没有提交、推送、创建 PR、合并、发布或部署授权。

回退仅撤回本记录列出的本批代码、测试及维护文档差异；不得重置整个工作区、覆盖 DSH 修改、删除历史恢复快照或回滚其他会话产生的流程记录。旧确认与旧检查点的处理以证据不足时重新验证为原则，不能以回退为由重新启用已证实的越门路径。
