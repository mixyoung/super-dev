# UI 验收证据边界：贡献记录

## 问题与现有覆盖

旧 UI review 把全图颜色分布、明暗或留白当成审美结论，部分入口还把旧源码探测视作真实运行。Pillow 只在开发依赖中声明，质量入口却在模块级加载它，导致基础 wheel 未装 Pillow 时连 PRD 检查也崩溃。既有 UI 契约、证据信封、工作项/代码身份、候选失效和宿主预览继续使用；不添加独立工作流或新的模型路由。

## 来源与适用条件

用户确认的 PRD、架构、UI/UX 和授权记录见 `output/ui-review-evidence-boundary-docs-confirmation.md`；历史和 Pillow/Playwright 能力区别见 `output/ui-review-evidence-boundary-research.md`。比对基线为 `26b0cb6c98e723b8c12c4d721785a9cb91d6f761`。用户明确要求“按照方案移除”，实施位置随后改为独立工作树。按 `knowledge/00-governance/maintenance-policy.md` 和 `knowledge/00-governance/review-checklist.md` 核对接入和回退；不改知识库。图片/视觉证据只适用于已明确需要 UI 验收的项目；本仓库是 CLI，本次不新增生产界面。

## 取舍与核心影响

采用共享证据校验和三份独立结果，仍让宿主执行浏览器与模型工具。当前记录绑定正式工作项、未提交改动在内的代码版本、确认的 UI/UX、截图字节、实际图片输入和响应。只能核对链路，不能证明模型内部理解或宿主记录不可伪造。移除全图像素审美判定及 Pillow 调用和开发安装需求；没有确认依据的结构和风格只作观察。保留冻结的设计及工程约束、质量阈值 90、标准模式独立用户预览确认和明确的非 UI 路径；SEEAI 不新增标准模式的预览门。旧报告不能自动升级为当前证据。GET 不写产物。

## 改动范围

- .super-dev/changes/ui-review-evidence-boundary/adoption.md
- .super-dev/changes/ui-review-evidence-boundary/change.yaml
- .super-dev/changes/ui-review-evidence-boundary/checklist.md
- .super-dev/changes/ui-review-evidence-boundary/ledger.json
- .super-dev/changes/ui-review-evidence-boundary/plan.md
- .super-dev/changes/ui-review-evidence-boundary/proposal.md
- .super-dev/changes/ui-review-evidence-boundary/specs/ui-review-evidence-boundary/spec.md
- .super-dev/changes/ui-review-evidence-boundary/tasks.md
- .agents/skills/super-dev/SKILL.md
- .claude/skills/super-dev/SKILL.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- pyproject.toml
- uv.lock
- super_dev/cli.py
- super_dev/cli_deploy_runtime_mixin.py
- super_dev/cli_pipeline_runtime_mixin.py
- super_dev/cli_release_quality_mixin.py
- super_dev/cli_workflow_runtime_mixin.py
- super_dev/creators/prompt_generator.py
- super_dev/framework_harness.py
- super_dev/host_runtime_probe.py
- super_dev/integrations/manager_content_mixin.py
- super_dev/proof_pack.py
- super_dev/release_readiness.py
- super_dev/reviewers/fresh_verification_evidence.py
- super_dev/reviewers/quality_gate.py
- super_dev/reviewers/quality_gate_evidence_mixin.py
- super_dev/reviewers/quality_gate_models.py
- super_dev/reviewers/ui_review.py
- super_dev/reviewers/ui_review_evidence.py
- super_dev/reviewers/ui_review_execution_mixin.py
- super_dev/reviewers/ui_review_models.py
- super_dev/reviewers/ui_review_output.py
- super_dev/skills/skill_template.py
- super_dev/templates/ui-review-evidence.md
- super_dev/ui_contract_governance.py
- super_dev/web/api.py
- super_dev/workflow_guard.py
- super_dev/workflow_state.py
- tests/integration/test_cli.py
- tests/integration/test_web_api.py
- tests/support/ui_evidence_inputs.py
- tests/unit/test_cli_resume.py
- tests/unit/test_host_runtime_probe.py
- tests/unit/test_quality_gate.py
- tests/unit/test_release_readiness.py
- tests/unit/test_release_readiness_enhanced.py
- tests/unit/test_ui_intelligence.py
- tests/unit/test_ui_review_evidence.py
- tests/unit/test_workflow_state.py

## 验证与未验证

修复前 `output/ui-clean-2026-11-27-g28y8es4/REPORT.md` 复现三类命令因 `No module named 'PIL'` 中断。最终 wheel 在 Windows x64、CPython 3.12.12 隔离环境基础安装：37 个包，依赖检查通过，无 Pillow/PIL/pytest，五次实际命令均正常出具适用状态。最终 wheel 与工作树 26 个变更打包文件逐字节一致；详见 `output/ui-clean-verified/results.json`。同一个已安装包校验了真实宿主原图与看图记录：正常样例 4 张图，浏览器和视觉均通过；移动端遮挡样例浏览器通过但视觉失败，定位 3 项；在导入当前视觉记录前两者均受阻。详见 `output/ui-clean-verified/native-receipt-results.json`。

最终四组目标回归共 288 项通过：证据与工作流 107 项、Web/CLI 9 项、证据包与发布校验 76 项、质量门禁与发布就绪 96 项。未运行全仓测试。这些回归不替代项目级质量门禁或正式完成前验证证据。用最终已安装 CLI 在任务结账后复验，Spec 任务完成度通过，但项目级门禁仍为 73.2/100（阈值 90，失败（`FAIL`））；缺当前代码版本的正式完成前验证证据，没有放行合并或发布。日志和逐条验收对应见 `output/ui-review-evidence-boundary-delivery.md`。外部视觉工具分支只用合成事件验证，不算真实服务接通；没有测试实体手机、其他宿主和其他平台的干净安装。

## 决定与回退

在独立工作树限定本批改动。确认文档字节保持原状，未改 DSH 目录、用户全局工具或配置。回退只撤销本批文件差异，保留原始截图、响应摘录、历史报告及无关变更；恢复旧报告不等于获得当前视觉验收。没有提交、推送、发布或部署。
