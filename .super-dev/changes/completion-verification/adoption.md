# 四文档收尾与更新一致性

## 问题与现有覆盖

2026-09-08 通过质量检查期间的只读文件观察，捕获到 .super-dev/knowledge-stats.db-wal 与 knowledge-stats.db-shm 被纳入未跟踪清单；knowledge_pusher 创建 KnowledgeStatsDB 并启用 SQLite WAL，原 .gitignore 只排除了主数据库。已定位同类误判的具体来源；仅将这一组 3 个固定的工具统计缓存路径排除，Git 与无 Git 路径一致，不忽略用户数据库或其他临时文件。

2026-09-08 用户批准三步最小修复：本项目运行保护预算改为 1800 秒；文件校验在同次读取中补充逐文件明细，能够指出新增/删除/修改；质量与发布验证串行执行。原 f8d6c13673614b44aa73b235d396e5b6 超时且只有未跟踪清单总摘要变化，具体文件未留存，不能预设根因或忽略全部未跟踪文件。

2026-09-07 后续授权“按建议执行”：仅修复 pipeline 未指定质量参数时没有读取 super-dev.yaml 的 quality_gate。quality 命令与策略校验已使用该配置，流水线评估却回落到内置 80；本次对齐读取行为并完成本地验证收尾，不扩展功能或自动提交、推送、合并、发布。

2026-09-07 六项最小修正：用户授权只修复上轮列出的不合理要求。发布检查绑定旧目录、可选治理文件按存在计分、历史已恢复 Hook 继续扣分、首次启动与恢复混用、UI 前置缺适用条件，以及旧发布默认 PyPI；不扩大到超时优化、其他旧债或新功能。具体范围见 minimal-rule-fixes.md。

当前完成前验证已有实际执行、证据和隔离，缺运行前反馈、简洁首屏及若干前置阻断回执；Windows unit 门禁未覆盖 tests/extensions。旧更新提示和命令查询原版 PyPI，且安装后仍可能用旧进程刷新模板。

## 来源与适用条件

本地已确认 completion-verification 的 research、PRD、architecture、UIUX 四文档及 main 59298d3 的实际实现，核对日期 2026-09-07。更新链仅适用于本 fork；外部协议依据为当日核对的 GitHub Releases REST API 和 uv 官方工具升级文档（链接见 docs/FORK_UPDATES.md）。不吸纳新品牌方法或新运行程序。

## 取舍与核心影响

2026-09-08 新授权仅覆盖本项目 timeout_seconds 从 900 到 1800 的运行保护预算，不是性能合格线；原测试参数、评分线、失败/受阻语义和进程清理保留。逐文件信息仅作诊断，原身份字段与摘要算法不变，不新增执行入口、主流程或执行器。超时显示“测试未完成，不代表代码质量不合格”。本次授权覆盖前文历史批次“不改 900 秒”的约束，不改写旧记录。

质量门槛读取优先级保持显式 --quality-threshold > 项目 quality_gate > 原配置默认值；保留参数快照中的显式/未指定区别，策略下限和必检项阻断不变。本次不改 85/90 数值、900 秒计划、人工验收记录，不新增发布门槛配置。

本批保留 85/90 数值门槛、权重公式、当前必需的质量/合规/安全检查和全部确认门。只有原先按文件存在打分的五类资料移到不计分提示，因此分数可能变化但不代表产品质量变好，也不改历史分数。Hook 当前判断仅合并同名/事件/阶段/来源的重复记录，保留历史计数；不能由无关成功消除失败。没有新增通用适用性引擎或流程状态。

用户“按照建议执行”批准收尾和更新统一。保持九阶段、确认权、单一验证入口、run_id、验收阈值和用户裁决；不可信扩展的失败由 Core 自有证据范围记账，不扩大扩展权限。默认 JSON 和关闭试点兼容。最终回放在全部代码冻结后执行，以免证据立即过期。

## 改动范围

- tests/integration/test_web_api.py
- .gitignore
- super-dev.yaml
- super_dev/extensions/evidence.py
- tests/extensions/test_verification_diagnostics.py
- super_dev/cli.py
- tests/unit/test_pipeline_quality_threshold.py
- .super-dev/changes/completion-verification/minimal-rule-fixes.md
- super_dev/hooks/manager.py
- super_dev/hook_harness.py
- super_dev/proof_pack.py
- super_dev/skills/skill_template.py
- super_dev/integrations/manager.py
- super_dev/integrations/manager_content_mixin.py
- scripts/release.sh
- tests/unit/test_minimal_rule_fixes.py
- tests/unit/test_release_script_routing.py
- tests/unit/test_release_readiness.py
- AGENTS.md
- CLAUDE.md
- .claude/CLAUDE.md
- .agents/skills/super-dev/SKILL.md
- .agents/skills/super-dev-seeai/SKILL.md
- .claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev-seeai/SKILL.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- .super-dev/changes/completion-verification/closure-plan.md
- .super-dev/changes/completion-verification/adoption.md
- super_dev/extensions/service.py
- super_dev/cli_release_quality_mixin.py
- super_dev/release_readiness.py
- super_dev/cli_parser_mixin.py
- tests/extensions/test_verification_closure.py
- tests/support/run_safe_baseline.py
- tests/unit/test_safe_baseline_runner.py
- .github/workflows/ci.yml
- super_dev/release_channel.py
- super_dev/update_runtime.py
- super_dev/update_hosts.py
- super_dev/version_check.py
- super_dev/cli_host_ops_mixin.py
- pyproject.toml
- tests/unit/test_fork_update.py
- tests/integration/test_cli.py
- docs/FORK_UPDATES.md
- README.md
- README_EN.md
- docs/INSTALL_OPTIONS.md
- tests/support/run_update_acceptance.py
- docs/SUPER_DEV_EXTENSION_PLATFORM_PLAN.md
- .super-dev/changes/completion-verification/specs/fresh-verification/spec.md
- super_dev/extensions/verification_metrics.py
- tests/support/run_verification_replays.py
- tests/extensions/test_verification_metrics.py
- tests/extensions/test_verification_replay_runner.py
- tests/extensions/test_fresh_verification_service.py
- output/completion-verification-research.md
- output/completion-verification-prd.md
- output/completion-verification-architecture.md
- output/completion-verification-uiux.md
- super_dev/creators/document_architecture_content_mixin.py
- super_dev/creators/document_delivery_content_mixin.py
- super_dev/creators/document_generator.py
- super_dev/creators/document_generator_content_mixin.py
- super_dev/creators/document_product_content_mixin.py
- super_dev/creators/document_ui_content_mixin.py
- super_dev/creators/frontend_builder.py
- super_dev/creators/frontend_framework_projects_mixin.py
- super_dev/creators/frontend_quality_config_mixin.py
- super_dev/creators/implementation_builder.py
- super_dev/creators/implementation_project_templates_mixin.py
- super_dev/creators/prompt_generator.py
- super_dev/creators/requirement_parser.py
- super_dev/creators/spec_builder.py
- super_dev/creators/task_executor.py
- super_dev/orchestrator/knowledge_pusher.py
- super_dev/reviewers/fresh_verification_evidence.py
- super_dev/reviewers/quality_gate.py
- super_dev/reviewers/quality_gate_evidence_mixin.py
- super_dev/reviewers/quality_gate_models.py
- super_dev/reviewers/ui_review.py
- super_dev/reviewers/ui_review_execution_mixin.py
- super_dev/reviewers/ui_review_models.py
- super_dev/stage_policy.py
- super_dev/workflow_contract.py
- super_dev/workflow_stage_truth.py
- super_dev/workflow_state.py

## 验证与未验证

PR #9 首轮 CI（34189308042）：Linux 三个 Python 版本均在两个发布就绪集成样例失败，原样例依赖旧固定目录且没有当前变更声明。仅为这两个样例显式指定原有的发布整理变更，名称与隔离样例目录及输出前缀保持一致，避免随机临时目录中的下划线影响名称规范化，不引入新的业务需求；保留 passed、score >= 90、接口只读等原断言，并增加当前变更检查通过断言。不改生产代码、评分线或原测试保护范围；本地复跑及新提交 CI 另行核验。

上述两个集成样例及“无当前变更时不得猜旧目录”的反例，本地 3 项复跑通过；差异和贡献范围检查通过。测试文件的两项旧导入 lint 提示已在 dd82f2f 基线复核存在，本次未顺带修改；生产 lint 首轮 CI 通过。随后以新提交重跑全部 PR CI。

缓存误判修复后的最终关联回归：57 通过、1 平台跳过（output/minimal-rule-fixes/verification-diagnostics-regression-final.xml）；Git/无 Git 精确缓存排除与原证据回归 13 通过、1 跳过。4 文件格式、生产 Ruff、2 核心模块类型检查、22 入口类型门禁、贡献范围、Skill 同步、最终 wheel 构建和 twine check 通过。质量扫描期间的真实文件清单观察保存在 output/minimal-rule-fixes/untracked-cache-observations.json；不再把旧 f8d 运行的具体文件名说成已留存，它没有逐文件附件。完整计划和最终报告在此记录冻结后串行运行，不再编辑生产代码或本记录。

运行预算与文件诊断修复：新增回归先复现 6 项失败，修复后 6 项通过；含同次读取与原身份不变、Git/无 Git 的新增/删除/修改明细、既有报告目录不影响源文件校验、超时仍未完成且进程清理正常。关联回归 55 通过/1 平台跳过（output/minimal-rule-fixes/verification-diagnostics-regression.xml）；生产 Ruff、4 文件 Black、2 个改动核心模块 mypy、22 入口类型门禁和 Skill 同步通过。逐文件清单仅覆盖 Git 未跟踪文件，Git 不可用时覆盖原文件系统扫描范围；不改原身份模型或摘要算法。实际观察到缓存附属文件后，又以 2 个失败用例复现，定向补齐三个工具缓存路径的排除，不使用 *.db、*.tmp 或所有未跟踪文件的宽泛规则。之后重新冻结实现并串行验证，最终结果写 output/minimal-rule-fixes/verification-diagnostics-closure.md；不引用旧通过结果冒充新版本。本轮不提交、推送、合并或发布。

质量门槛读取修复：Python 3.14 先复现 3 项取值失败、4 项原行为通过（测试夹具先对齐流水线原有两次评估，不限制调用次数），修复后连同策略与 quality 配置入口 15 项通过。项目 Python 3.13.12 再跑本轮与六项修复相关回归 31 项通过，另有 6 项评分/必检项保护回归通过；原始结果为 output/minimal-rule-fixes/threshold-and-rules-regression.xml 与 threshold-hard-gates.xml。生产 Ruff、3 文件 Black 检查、22 入口类型门禁、贡献范围、Skill 同步、wheel 构建和 twine check 通过。

本记录在最终本地验收前冻结，不改 900 秒登记计划；后续实际验证与质量/发布回执汇总至 output/minimal-rule-fixes/threshold-closure.md，日志和 JUnit 留在原证据目录。当前批次尚无远程 CI，不引用旧 CI 冒充本批通过，不自动填写人工确认或发布结论。

首轮完整登记计划（999e12c82574473ea1921878d650079e）在 638.465 秒完成：363 通过、1 失败、2 跳过，没有超时或代码变化，进程树清理通过。失败是六项修复的关联夹具遗漏：回放创建了旧布局/未绑定的变更，新发布检查正确拒绝。仅在回放隔离项目内先创建并绑定与其产物前缀一致的当前变更，再准备原有文档及确认；不改场景答案、评分、断言、生产检查或真实用户记录。保留首轮失败证据，修订后重新验证；后续结果仍写上述 output 汇总。

六项最小修正验证（基线 740f276）：新回归先复现 6 项失败，修复后 16 项针对性检查通过；宿主、Skill、Hook 等关联回归 268 通过/2 平台跳过，CLI 扩展回归 20 通过。发布与证据包回归最初 106 通过/1 旧夹具失败，该夹具原先依赖旧目录，现明确选择其已创建的 add-proof-ready 变更，保留原断言并单独复跑通过；没有把未知当前变更当通过。

Ruff、22 个入口类型门禁、3 个直接改动模块类型检查、Skill 同步与 Codex/SEEAI Skill 结构检查、Bash 语法检查、wheel 构建及 twine check 通过。两份 integrations 大文件在基线 740f276 已不符合整文件 Black 格式，本批未为此扩大格式化范围。发布脚本只在隔离目录中使用假 git/gh/publish 工具验证路由与校验和附件，未执行实际标签推送或发布。历史阶段账本与原 tasks 摘要未变；没有改 900 秒计划、重跑全仓 CI、安装用户级 Skill 或发布新版。改动保留在本地 ocx/minimal-rule-fixes，等待用户决定提交与后续交付。

2026-09-07 撤回程序化排错需求的定向验证：先以新合同观察到 10 项缺少中性收益字段的失败，再实现兼容调整。指标与回放执行器 26 项测试、服务指标落盘 1 项测试通过；Ruff、5 文件格式检查、指标模块类型检查、贡献规则与 Skill 同步检查通过。AST 比较确认原收益公式完全相同。未重跑整仓 CI、未修改历史回放/人工裁决；本次撤回暂为当前分支本地改动，未提交、推送、合并或发布。

开始时工作树干净，版本 2.5.0。先跑新增验收用例复现缺口（清单、阶段回执和提示/展开/JSON 输出失败），再实现修复。初次 Windows 3.13 安全基线为隔离自检 13 通过/1 跳过、用户目录 240 通过/2 跳过、核心扩展 151 通过/2 平台跳过，真实用户目录变化为 0。后续最终复跑结果另行追加。

后续本机最终安全基线：核心扩展加更新器 186 通过/2 平台跳过，隔离自检 13/1、用户目录 240/2，用户目录变化 0；45 项定向回归通过。最新构建 wheel 与当前 251 个包源码/资源逐项一致，真实隔离 pip 升级复跑通过。

原登记计划 completion-verification-candidate-006 在 900 秒触发超时（运行 0330e8c43c324057884e5d1ec523c642），完整进程树已清理，结果正确为 BLOCKED，不能把局部结果算成全计划通过。期间出现的失败定位为固定模式集合测试未列入本轮新增 core-verification；以单测复现后补齐明确模式、选择范围与隔离前置顺序的断言，继续拒绝任意模式。未延长超时、未删原测试。完整登记计划的耗时问题保留为未解决项，后续远程 CI 与最终回放单独提供证据，不冒充这次计划通过。

更新器 34 项定向用例通过；隔离 venv 的真实 pip 更新验证已通过，保留运行中的旧 0.0.1 合成夹具进程，实际安装新 wheel 后，由新解释器验证包文件并刷新项目 Skill。旧版本是测试夹具，不是发布历史或真实用户升级数据；HTTP 传输由本地 wheel/摘要夹具替代，来源解析、摘要校验、安装器和新进程均真实执行。证据位于 output/verification-closure/isolated-update/。生产代码随后有收尾改动，最终会重新构建并验收。

原 3 项 CLI 更新集成断言按获批来源变更从 PyPI/旧 migrate 调用改为 fork 来源、方式/用户范围转发及非零退出；没有更改 10 场景答案、计时、真实候选标签或 2B 阈值。误用宽泛 -k update 曾带入无关的 detect_save_profile 集成测试，在本机因没有就绪宿主失败，未顺手修改；精确选择的更新 28 项检查通过。全量类型旧债仍存在；22 个必过入口类型检查通过，新改 5 个模块单独类型检查通过。Linux/其他 Windows 版本需要实际 CI，尚不能宣称已验证。

## 决定与回退

2026-09-08 用户明确要求“提交 推送 合并”：本批六项规则修复、质量配置读取对齐及运行预算/文件诊断修复获准提交到当前 ocx/minimal-rule-fixes，推送 mixyoung/super-dev，并在当前提交的必要 CI 通过后合并 main；不发布新版。前文未提交/未授权的说明保留为相应历史时点记录。本地完整计划为提交前代码的 372 通过/2 平台跳过，最终质量检查 92.4/90，现有证据只读复核通过；远端结果以本次 PR 实际 CI 为准，不把旧运行的代码摘要改成新提交。

2026-09-07 交付授权更新：用户随后明确要求“提交推送 合并”。本次撤回随 PR #8 提交、推送，并在新提交全部适用 CI 通过后合并 main；不发布新版。此前“本地改动/不自动合并”是先前轮次边界，不代表本次仍缺少合并授权。

2026-09-07 用户要求“有必要做这个功能吗？如果没有就删除这个需求”。按现有宿主、系统化调试手册和 RCA/Skill 覆盖判断，无独立程序缺口证据，撤回程序化排错（原 2B）需求，不是等待晋级。路线第 1.5 节为权威决定，四文档、Spec 和当前收尾计划同步对齐；历史任务、回放、人工标签、原数值阈值及发布门禁不改写。指标用 benefit_criteria_met 保留同一公式；recommend_stage_2b 保留兼容且新汇总恒为 false，防止继续提示已撤回功能。测试保留原所有数值/身份保护，并补“收益条件满足也不推荐 2B”反例。需要恢复时必须另有实际缺口与用户批准，而不是按阶段编号推进。

发布检查原先只认 `uv tool install super-dev` 字面值，与已发布 fork 的锁定标签安装说明冲突。本批对齐为兼容原写法并准确接受固定仓库的版本标签命令；补充不同来源/未锁定版本/缺安装入口拒绝测试，不移除检查或降低门槛。整份发布报告仍因测试超时和旧合规证据失效而不能作为通过声明。

该门禁修订后，更新器与基线模式的 42 项定向检查通过，仓库实际安装入口检查通过。完整当前 wheel 会在本 PR 跨平台任务中重新构建并执行隔离升级；此前本机 wheel 验收保留为上一轮局部证据，不代替当前提交的 CI。用户另行批准提交、推送及创建 PR 运行 CI，明确不自动合并或发布。

PR #8 首轮 CI：Linux 3.10/3.11/3.12 全量质量检查、Linux 3.13 核心及真实 pip 升级通过。Windows 3.10–3.13 核心测试通过，但隔离升级夹具绕过了正式 CLI 的 UTF-8 终端初始化，英文 Windows cp1252 无法打印中文，失败发生在安装前。夹具改为直接调用 SuperDevCLI.run，沿用产品正式入口，不关闭断言、不改变产品编码合同。首轮本机真实 uv tool 升级另行通过，用户目录变化 0，原始记录 output/verification-closure/uv-isolated-update/。

修正后在隔离子进程主动设置 cp1252，正式 CLI 的初始化恢复 UTF-8，真实 pip 升级通过，用户目录变化 0（output/verification-closure/cp1252-native-cli-update/）。该修订只改验收夹具和本记录，随后重新推送 CI，并按新提交重新回放。

第二轮 Windows CI 的升级结果 JSON 与子进程日志均已通过，失败仅在验收脚本最后打印中文汇总；外层验收入口同样使用已有 initialize_terminal_output，不改产品编码策略。权限复查还以 3 个失败用例复现 cwd=用户主目录/父目录/用户接入目录时，用户 Skill 被路径包含关系误归项目的风险；改为按宿主声明排除用户面，即使它在 cwd 内也需要 --include-user。正例仍允许真实项目的已有 Skill 更新，无新增权限。

上述修复后 45 项更新/基线定向回归、类型与 Ruff 检查通过；重新构建当前 wheel，并在外层与旧进程均使用 cp1252 的隔离环境完成真实升级，用户目录变化 0（output/verification-closure/scope-cp1252-update/）。以随后 CI 与新提交回放作为最终版本证据，不引用旧回放推荐。

采用已获批准的增量收尾，不改产品路线。若失败则修复本批或回退本批差异，不降低门槛，不改原人工验收。更新与新发布分离，本轮不自动发布新版。

## 2026-09-10 主线真实性与技术债收尾

用户明确要求修复产物前缀、CLI 发布演练适用性、当前代码版本验证、会话状态、任务台账、版本说明，并全量处理类型、格式和超大模块问题；同时要求面向中国大陆用户使用自然、常见的简体中文，避免生僻词、直译腔和不必要的中英混杂。

本批保持原公开入口、流程所有权、确认权、质量阈值和用户验收记录不变。结构调整只按职责搬迁现有方法与静态目录，保留原公开类名和导入路径；不新增第二套流程或执行入口。格式化属于全库机械整理，不改变功能。当前工作只准备修复和验证，不代表已经合并、发布或部署。

### 改动范围

- .agents/skills/super-dev-seeai/SKILL.md
- .agents/skills/super-dev/SKILL.md
- .claude/CLAUDE.md
- .claude/skills/super-dev/SKILL.md
- CLAUDE.md
- README.md
- docs/HOST_CAPABILITY_AUDIT.md
- docs/PUBLISHING.md
- docs/WORKFLOW_GUIDE.md
- docs/WORKFLOW_GUIDE_EN.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev-seeai/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- pyproject.toml
- super-dev.yaml
- super_dev/artifact_utils.py
- super_dev/cli.py
- super_dev/cli_host_commands_mixin.py
- super_dev/cli_host_discovery_mixin.py
- super_dev/cli_host_guidance_mixin.py
- super_dev/cli_host_ops_mixin.py
- super_dev/cli_integration_runtime_mixin.py
- super_dev/cli_pipeline_runtime_mixin.py
- super_dev/cli_workflow_runtime_mixin.py
- super_dev/creators/document_architecture_content_mixin.py
- super_dev/creators/document_delivery_content_mixin.py
- super_dev/creators/document_generator.py
- super_dev/creators/document_generator_content_mixin.py
- super_dev/creators/document_product_content_mixin.py
- super_dev/creators/document_ui_content_mixin.py
- super_dev/creators/frontend_builder.py
- super_dev/creators/frontend_framework_projects_mixin.py
- super_dev/creators/frontend_quality_config_mixin.py
- super_dev/creators/implementation_builder.py
- super_dev/creators/implementation_project_templates_mixin.py
- super_dev/creators/prompt_generator.py
- super_dev/creators/requirement_parser.py
- super_dev/creators/spec_builder.py
- super_dev/creators/task_executor.py
- super_dev/design/ui_intelligence.py
- super_dev/design/ui_intelligence_foundation_catalog.py
- super_dev/design/ui_intelligence_models.py
- super_dev/design/ui_intelligence_stack_catalog.py
- super_dev/host_diagnostics.py
- super_dev/host_session_resume.py
- super_dev/integrations/catalog_mixin.py
- super_dev/integrations/manager.py
- super_dev/integrations/models.py
- super_dev/migrate.py
- super_dev/orchestrator/knowledge_pusher.py
- super_dev/release_readiness.py
- super_dev/reviewers/fresh_verification_evidence.py
- super_dev/reviewers/quality_gate.py
- super_dev/reviewers/quality_gate_evidence_mixin.py
- super_dev/reviewers/quality_gate_models.py
- super_dev/reviewers/ui_review.py
- super_dev/reviewers/ui_review_execution_mixin.py
- super_dev/reviewers/ui_review_models.py
- super_dev/skills/skill_template.py
- super_dev/stage_policy.py
- super_dev/user_directories.py
- super_dev/web/api.py
- super_dev/web/api_host_support.py
- super_dev/workflow_contract.py
- super_dev/workflow_stage_truth.py
- super_dev/workflow_state.py
- tests/e2e/test_full_flow.py
- tests/integration/test_cli.py
- tests/integration/test_web_api.py
- tests/unit/test_artifact_utils.py
- tests/unit/test_quality_gate.py
- tests/unit/test_release_readiness.py
- tests/unit/test_release_readiness_enhanced.py
- tests/unit/test_super_dev_skill_contracts.py
- tests/unit/test_user_directories.py
- tests/unit/test_workflow_state.py

其余由 Black 产生的文件变化只包含格式调整，统一通过全库 Ruff、Black、类型检查和完整测试核对；不把格式变化解释为新增功能。

### 验证与回退

文件冻结后依次执行全库 Ruff、Black、Mypy、字节码编译、贡献范围检查、Skill 同步、完整 pytest、当前代码版本验证、质量门禁、发布就绪和证据包。任何一项未完成或失败都不记为通过。若结构拆分出现回归，按本批文件搬迁反向恢复，不改原流程语义、阈值或用户验收标签。
