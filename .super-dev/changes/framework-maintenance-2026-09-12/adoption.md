# 周期性框架维护与知识边界加固

日期：2026-09-14，外部复审与发布门禁收口于 2026-09-16。基线：`af875a92b6828896a923c5c7cfc680519647e2fd`。本记录只对应用户已确认的 `framework-maintenance-2026-09-12` 三文档与 P0/P1 实施范围；P2 保持后置评估，不因本记录自动进入实现。

## 问题与现有覆盖

Super Dev 已有单一 Core、标准九阶段、文档/预览确认门、知识推送、专家画像、变更目录和交付证据，但存在五类结构性缺口：知识文本的权威层级和可产生效果未形成机器可判定边界；阶段到专家的映射有重复来源；专家画像缺少完整输入输出、权限、停止与交接契约；文档确认与 change 身份在 Spec 前缺少稳定绑定；交付就绪、发布、部署和运营结果的事实语义尚未完全解耦。

现有 `workflow_contract.py`、`workflow_stage_truth.py`、`workflow_guard.py`、`artifact_utils.py`、`review_state.py`、专家加载链、知识推送链和发布证据链继续作为唯一实现基础。本批不引入第二流程所有者、第二状态机、DAG、额外主入口或新的人工确认门。

## 来源与适用条件

- 本地权威依据：用户于 2026-09-14 明确确认三文档；PRD、架构与 UIUX 的确认版本 SHA-256 分别为 `7659E059F728D84524D3F6C59EEB2531314E93F40911A613CED8074E8685409A`、`083CEB955781DED14823D12548948FD1FCCEB29B84B86D44E25886432ED138E2`、`4F8DA6CDA84B411597DB0527F1A6CA390A02FC37861C580D81F84BAFB95B6BF7`。
- `obra/superpowers`：提交 `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`（v6.3.0），只吸收可验证的工作方法和技能边界，不复制其入口或流程所有权。
- `bmad-code-org/BMAD-METHOD`：提交 `94b6727b00c8316557828c8a8ff2a48ff60d60cc`（v6.12.0），只参考角色职责与阶段交接表达，不导入其团队、状态机或工作流。
- `msitarzewski/agency-agents`：提交 `6d29a9b08785a0e49ffc9818bbdd381164c2df5f`，只参考角色画像结构，不采用虚构资历或整套角色目录。
- `dnolincn/umadev`：提交 `585262706174ad4a958cd054f0948509e84ad610`（v1.1.1），只参考当前请求作为权限来源、证据优先和安全收敛原则，不引入 Director、第二状态机或执行器。
- Agent Skills 规范：提交 `69ef37e9424c0a7ea9dd2293b559e43ec8176379`，仅在后置 P2 中评估渐进披露；本批不拆 Skill。

这些来源是候选方法证据，不是项目授权。只有与已确认需求匹配、可在现有架构内增量实现且通过本地验收的部分才适用。

## 取舍与核心影响

本批加固既有核心合同，但不改变产品初心、标准九阶段、SEEAI 差异、用户确认权、默认质量阈值或宿主执行边界。知识命中不等于权限；仓库内部或外部文档中的指令性内容均只能按来源与内容类型进入允许效果集合。正常、已授权且位于工作区内的实现编辑不新增重复确认；破坏性、工作区外、远端写入、生产操作、凭据读取或权限扩张仍要求明确权限。

阶段专家映射收敛为一个权威来源，旧名称保留只读兼容视图。专家画像从履历叙事改为可测试的工作契约。标准流程增加 Spec 前身份绑定字段，但 `pre_spec` 仅为内部过渡语义，不新增阶段或门禁；SEEAI 绑定与状态保持不变。交付事实独立记录，不允许由 `delivery_ready` 推导 `released`、`deployed` 或 `operating`。

外部评审结果仍是低权威证据内容，不能凭 JSON 正文自证独立或替用户接受风险。高风险独立评审只有在调用方显式见证精确评审文件摘要，并同时匹配当前工作项、目标版本和候选摘要时才成立；收集异常失败关闭。残余风险接受是单独的显式质量命令输入，即使存在也不会把未验证或自检结果改称独立。

候选摘要只描述项目候选，不受机器级 Git ignore 或用户本地宿主配置影响。候选清单显式排除 `.claude/settings.local.json`，并覆盖 `core.excludesFile` 的跨机器差异；否则高权限验证与受限质量进程会对同一源码产生不同身份，破坏证据绑定。

发布门禁收口只修复可复现的验证基础设施问题：内置专家摘要统一按 UTF-8 规范化文本计算，避免 CRLF/LF 造成同内容假差异；红队依赖审计继续检查真实 `frontend/`/`backend/`，但不把 `output/` 下的生成参考副本当成第二个发布根重复扣分；GitHub-only 发行构建在存在 `uv.lock` 时使用锁定的 uv 环境，仍保留无 uv 项目的 Python 回退。上述修复不降低红队阈值、不跳过真实锁文件检查，也不改变发布目标。

不采纳项：P2 Skill 拆分和周期自动跟踪本批不实施；不增加知识自治写回、角色团队、评分门槛、第二账本或自动发布/部署。

## 改动范围

- .agents/skills/super-dev/SKILL.md
- .claude/skills/super-dev/SKILL.md
- .super-dev/SESSION_BRIEF.md
- .super-dev/changes/framework-maintenance-2026-09-12/adoption.md
- .super-dev/changes/framework-maintenance-2026-09-12/change.yaml
- .super-dev/changes/framework-maintenance-2026-09-12/checklist.md
- .super-dev/changes/framework-maintenance-2026-09-12/ledger.json
- .super-dev/changes/framework-maintenance-2026-09-12/plan.md
- .super-dev/changes/framework-maintenance-2026-09-12/proposal.md
- .super-dev/changes/framework-maintenance-2026-09-12/specs/framework-maintenance-2026-09-12/spec.md
- .super-dev/changes/framework-maintenance-2026-09-12/tasks.md
- .super-dev/changes/framework-maintenance-2026-09-12/validation.md
- .super-dev/extensions/history.jsonl
- .super-dev/extensions/metrics/verification-pilot.jsonl
- .super-dev/extensions/runs/0370b161473044c9bd535be81483e377/pytest-summary.json
- .super-dev/extensions/runs/0370b161473044c9bd535be81483e377/result.json
- .super-dev/review-state/document-confirmation.json
- .super-dev/review-state/quality-revision.json
- .super-dev/review-state/stage-ledger.json
- .super-dev/workflow-events.jsonl
- .super-dev/workflow-history/latest.json
- .super-dev/workflow-history/workflow-state-20260914T022859985437+0000.json
- .super-dev/workflow-history/workflow-state-20260914T032734065009+0000.json
- .super-dev/workflow-history/workflow-state-20260914T032735961903+0000.json
- .super-dev/workflow-history/workflow-state-20260914T032736284966+0000.json
- .super-dev/workflow-history/workflow-state-20260914T051153426742+0000.json
- .super-dev/workflow-state.json
- README.md
- README_EN.md
- knowledge/ai/prompt-and-tool-guardrails.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- scripts/release.sh
- output/external-reviews/framework-maintenance-2026-09-12-independent-review-blocked.json
- output/framework-maintenance-2026-09-12-architecture-drift.json
- output/framework-maintenance-2026-09-12-architecture-drift.md
- output/framework-maintenance-2026-09-12-feature-checklist.json
- output/framework-maintenance-2026-09-12-feature-checklist.md
- output/framework-maintenance-2026-09-12-product-audit.json
- output/framework-maintenance-2026-09-12-product-audit.md
- output/framework-maintenance-2026-09-12-opencode-code-review-synthesis.md
- output/framework-maintenance-2026-09-12-opencode-deepseek-v4-flash-code-review.md
- output/framework-maintenance-2026-09-12-opencode-minimax-m3-code-review.md
- output/framework-maintenance-2026-09-12-proof-pack-summary.md
- output/framework-maintenance-2026-09-12-proof-pack.json
- output/framework-maintenance-2026-09-12-proof-pack.md
- output/framework-maintenance-2026-09-12-quality-gate.json
- output/framework-maintenance-2026-09-12-quality-gate.md
- output/framework-maintenance-2026-09-12-redteam.json
- output/framework-maintenance-2026-09-12-redteam.md
- output/framework-maintenance-2026-09-12-release-readiness.json
- output/framework-maintenance-2026-09-12-release-readiness.md
- output/framework-maintenance-2026-09-12-spec-compliance.json
- output/framework-maintenance-2026-09-12-spec-compliance.md
- output/framework-maintenance-2026-09-12-task-execution.md
- output/framework-maintenance-2026-09-12-uiux-compliance.json
- output/framework-maintenance-2026-09-12-uiux-compliance.md
- super_dev/artifact_utils.py
- super_dev/atomic_io.py
- super_dev/analyzer/feature_checklist.py
- super_dev/cli_parser_mixin.py
- super_dev/cli_pipeline_runtime_mixin.py
- super_dev/cli_release_quality_mixin.py
- super_dev/cli_spec_mixin.py
- super_dev/cli_workflow_runtime_mixin.py
- super_dev/creators/prompt_generator.py
- super_dev/creators/spec_builder.py
- super_dev/creators/task_executor.py
- super_dev/delivery_facts.py
- super_dev/expert_stage_governance.py
- super_dev/extensions/evidence.py
- super_dev/experts/builtin/ARCHITECT.md
- super_dev/experts/builtin/CODE.md
- super_dev/experts/builtin/DBA.md
- super_dev/experts/builtin/DEVOPS.md
- super_dev/experts/builtin/PM.md
- super_dev/experts/builtin/PRODUCT.md
- super_dev/experts/builtin/QA.md
- super_dev/experts/builtin/RCA.md
- super_dev/experts/builtin/SECURITY.md
- super_dev/experts/builtin/UI.md
- super_dev/experts/builtin/UX.md
- super_dev/experts/builtin/VERIFICATION.md
- super_dev/experts/loader.py
- super_dev/experts/review_protocol.py
- super_dev/experts/toolkit.py
- super_dev/orchestrator/engine.py
- super_dev/orchestrator/experts.py
- super_dev/orchestrator/knowledge_pusher.py
- super_dev/proof_pack.py
- super_dev/release_readiness.py
- super_dev/review_state.py
- super_dev/reviewers/external_reviews.py
- super_dev/reviewers/quality_gate.py
- super_dev/reviewers/quality_gate_evidence_mixin.py
- super_dev/reviewers/redteam.py
- super_dev/shadow_ledger_store.py
- super_dev/skills/skill_template.py
- super_dev/specs/generator.py
- super_dev/work_item_identity.py
- super_dev/workflow_contract.py
- super_dev/workflow_guard.py
- super_dev/workflow_stage_truth.py
- tests/integration/test_cli.py
- tests/extensions/test_evidence.py
- tests/unit/test_analyzer.py
- tests/unit/test_cli_resume.py
- tests/unit/test_content_authority.py
- tests/unit/test_delivery_facts.py
- tests/unit/test_expert_profile_v2.py
- tests/unit/test_quality_gate.py
- tests/unit/test_redteam.py
- tests/unit/test_release_script_routing.py
- tests/unit/test_shadow_ledger_store.py
- tests/unit/test_work_item_identity.py
- tests/unit/test_workflow_stage_truth.py
- tests/unit/test_workflow_state.py
- uv.lock

## 验证与未验证

实施前关联基线：`python -m pytest tests/unit/test_expert_service.py tests/unit/test_prompt_guidance_scope.py tests/unit/test_workflow_stage_truth.py -q`，35 项通过，耗时 4.63 秒；这只证明基线，不代表本批实现通过。

主体实现版本在最终 CrossReview 适用性小修前，锁定离线项目环境完整单元集 2754 通过、4 个既有平台跳过；第二轮外部评审问题收口后的完整受影响回归为 132 通过，新增质量 CLI 三项在格式化后再次通过。当前候选的全生产 Ruff、233 个源码文件 Mypy、392 个生产/测试 Python 文件 Black、compileall 和差异空白检查均通过；当前候选完整测试计划在 1800 秒时受阻，不能用前述相邻版本全量结果冒充 PASS。恶意知识、正常工作区编辑、高风险动作、风险 scope 未知时的保守复审、单一阶段专家映射、SEEAI 专属角色集合、画像 v1/v2 与覆盖限制、未见证评审零控制效力、外部评审精确文件/候选绑定、中文 work item、旧状态、新旧 change 共存、摘要不符、原子写、影子账本不猜最新、四类交付事实与运营信号均有正反例。详细命令、首轮失败、修复后结果和运行时间见 `validation.md`。

源码披露获得明确授权后，OpenCode MiniMax 与 DeepSeek 在不同会话完成两轮小范围副本复审；四份结论均按 `CHANGES_REQUIRED` 原样保留，有效问题已定向修复，未用模型自报替代当前候选见证。正式 fresh-verification 在 1800 秒时受阻，候选未变化且进程已清理；此前质量 82.6/90、发布就绪 50/100、proof-pack 27/35，均未通过。尚未全量运行 integration/e2e、跨平台 CI、真实发布、部署或生产运营观察；旧模型审查或未绑定当前候选的报告不能作为当前实现验收。

上述中间态随后完成收口：正式 fresh-verification 运行 `18f6fe3d06174d58a756e092d2bb78e7` 收集 388 项、执行 386 项、跳过 2 项、0 失败/错误；MiniMax-M3 会话 `ses_f59fc1607ffeyAmORScUs6CbQY` 与 DeepSeek-v4-flash 会话 `ses_f59fb6702ffeAZdJJ3jo0WUeM3` 对最终审查包均给出 PASS 且无必改项。Quality Gate 90.6/90、Release Readiness 100/85、Proof Pack 35/35，workflow 持久化为 `delivery_ready`。发布前完整 preflight `output/release/preflight-20260916-100903` 为 PASS：Pytest 3297 通过、10 跳过，Ruff、类型门禁、完整 Mypy、知识审计/门禁、交付 smoke、宿主兼容、Bandit、pip-audit 与 benchmark 全部通过；wheel 与 sdist 随后实际构建并通过 Twine 校验。

## 决定与回退

用户已确认三文档并授权按确认范围进入 Spec 与实现，后续明确授权提交、合并并发布本 fork 的 GitHub Release。P0/P1 采用；P2 暂缓。发布授权不包含 PyPI、部署、生产运营或全局安装；`released` 不得推导为 `deployed` 或 `operating`。

若验证失败，只回退本 change 在上述明确文件中的差异，并保留用户原有未跟踪文件与其他 change；不得重置整个工作树、降低质量阈值、删失败用例或把未知记为通过。核心语义如需超出已确认文档，必须重新回到架构/文档确认。
