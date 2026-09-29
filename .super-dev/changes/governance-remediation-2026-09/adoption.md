# 批 A 吸纳记录：安装指引统一为 GitHub-only 口径 + 修复机器本地链接

## 问题与现有覆盖

README.md:31 已明确本 fork 只在 GitHub 发布、未上传 PyPI，且 README/README_EN/INSTALL_OPTIONS/QUICKSTART 均已使用固定 Tag 安装命令；但 docs/WORKFLOW_GUIDE.md:207 与 docs/RELEASE_RUNBOOK.md:102 仍给出 `uv tool install super-dev` / `uv tool install super-dev==<version>`（PyPI 式）命令，install.sh:428-429 的报错提示指向 PyPI 安装，官网 super-dev-website 全部活跃指引组件（Hero、Bottom CTA、Code Demo、Showcase、Docs、终端模拟常量）展示同一失效命令。另有 6 个文档共 12 处链接指向维护者个人机器绝对路径 `/Users/weiyou/Documents/kaifa/super-dev/...`。此前 completion-verification 批只对齐了 README 与 INSTALL_OPTIONS 的发布检查口径，未覆盖上述其余用户入口。

## 来源与适用条件

来源：2026-09-29 维护者会话中的全项目只读审查结论 + 本轮全库 grep 复核（含初次扫描因 head 截断漏掉、复扫补提的 DocsPageContent.tsx:686/689 与 lib/constants.ts:83/105）。适用条件：所有仍在指导当前安装的用户入口（docs、install.sh、官网源文本）。不适用：历史记录（docs/releases/2.4.0.md、官网 Changelog 2.2.0 条目、旧 change 的 adoption 记录按"保留原语义"不改）、行为代码（super_dev/release_readiness.py:831 的兼容分支）、测试中的合成字符串。

## 取舍与核心影响

统一为 README 已确立的 GitHub-only 固定 Tag 命令（`uv tool install --force --from "git+https://github.com/mixyoung/super-dev.git@v2.6.0" super-dev`），消除"未上 PyPI"与失效安装命令的公开矛盾；绝对路径链接改为仓库相对链接。JSX 属性中的命令改用单引号包裹以容纳内嵌双引号。不改变任何产品行为、质量门槛或验收语义；不包含官网构建与部署。发现但不在本批处理（超出授权范围，已在 proposal.md 列出待维护者决定）：RELEASE_RUNBOOK 的 `--repository pypi` 发布链路残留、官网指向 `shangyankeji/super-dev` 的仓库身份问题、官网模拟终端中的 2.4.0 版本号陈旧。批准依据：维护者 2026-09-29 会话明确授权批 A 范围（安装指引与链接，不含官网部署）。

## 改动范围

- docs/WORKFLOW_GUIDE.md
- docs/WORKFLOW_GUIDE_EN.md
- docs/QUICKSTART.md
- docs/INSTALL_OPTIONS.md
- docs/INTEGRATION_GUIDE.md
- docs/RELEASE_RUNBOOK.md
- install.sh
- super-dev-website/components/sections/HeroSection.tsx
- super-dev-website/components/sections/BottomCta.tsx
- super-dev-website/components/sections/CodeDemoSection.tsx
- super-dev-website/components/pages/ShowcasePageContent.tsx
- super-dev-website/components/pages/DocsPageContent.tsx
- super-dev-website/lib/constants.ts
- .github/workflows/website-pages.yml
- super_dev/reviewers/spec_compliance.py
- super_dev/reviewers/architecture_drift.py
- super_dev/reviewers/uiux_compliance.py
- super_dev/orchestrator/engine.py
- super_dev/workflow_guard.py

## 验证与未验证

- 复扫（grep 全库 md/sh/ts/tsx）：裸 `uv tool install super-dev` 在活跃指引中清零；剩余 3 处均为有意保留的历史记录（docs/releases/2.4.0.md 两处、completion-verification 旧 adoption 一处）。`weiyou` 在 docs/ 与 README/README_EN 中清零（super_dev/experts/playbooks/code_playbook.md 中的 `TODO(weiyou)` 是示例人名非路径，不属链接问题）。
- 相关单测：`.venv/Scripts/python.exe -m pytest tests/unit/test_release_readiness.py tests/unit/test_product_audit.py tests/unit/test_fork_update.py -q` → 80 passed（198.65s）。发布检查的 `documented_uv_install` 兼容固定 Tag 形式，README/INSTALL_OPTIONS 未受本批影响。
- 贡献政策检查：`python scripts/check_contribution_policy.py --base 75ece3262880334ae0e06ffc113dd633f2755767` 通过（本批无受控路径改动，本记录为按政策自愿保留的短记录）。
- 未验证：super-dev-website 无 node_modules，未运行 tsc/build（改动均为字符串字面量替换，JSX 属性引号已人工核对）；官网未部署（超出本批范围）。install.sh 为 bash 脚本，本机未执行冒烟。

## 决定与回退

采用。授权：维护者 2026-09-29 会话（批 A 范围）。回退：`git revert` 本批提交即可；无数据迁移、无工作流状态变更、无产品行为影响。

## 2026-09-29 批 A2：官网身份切换至 GitHub Pages

问题与范围：官网（super-dev-website）身份全部指向原维护者——lib/site-locale.ts 的 SITE_URL 为原域名 superdev.goder.ai，public/CNAME（同域名）使 next.config.mjs 强制走自定义域模式（basePath 为空），lib/github.ts 的 star API 与 Footer（13 处）/ChangelogPageContent/BottomCta/app/layout.tsx 链接指向 shangyankeji/super-dev，Footer 另有 2 处 PyPI 链接与本 fork "未上 PyPI" 事实矛盾。维护者明确原维护者官网无法修改、官网改建 GitHub Pages（2026-09-29 会话授权）。

改动（分支 ocx/governance-remediation-batch-a2-website，基线 af1d1ec）：super-dev-website/lib/site-locale.ts（SITE_URL → https://mixyoung.github.io/super-dev/，SITE_BASE_PATH 改为与 next.config.mjs basePath 逻辑一致的动态值：dev 空、生产 /super-dev）、lib/github.ts（仓库与 star API 切 mixyoung）、components/layout/Footer.tsx（仓库链接切 mixyoung、PyPI 改 GitHub Releases、作者与版权署名 mixyoung）、app/layout.tsx（authors 元数据）、components/pages/ChangelogPageContent.tsx、components/sections/BottomCta.tsx、删除 public/CNAME、新增 .github/workflows/website-pages.yml（仅 workflow_dispatch 手动触发的 Pages 构建+部署，不自动发布）。

取舍：star 数改为拉取 mixyoung 仓库真实数据（初期会明显低于原仓库展示值），是身份正确性的直接结果；上游署名保留在仓库 LICENSE 与 docs/SUPER_DEV_EXTENSION_PLATFORM_PLAN.md 的上游标注（该文件中 shangyankeji 为上游仓库说明，有意保留）；DEFAULT_STAR_COUNT=108 兜底值未动（仅 API 失败时使用）。

验证与未验证：全库扫描确认 website 中 shangyankeji/goder.ai/pypi.org 清零（仅余上游标注文档）；check_contribution_policy.py --base af1d1ec 通过。未验证：website 无 node_modules，未运行 tsc/build 与 lint；GitHub Pages 未启用、未实际部署（部署门保留在维护者手中：Settings → Pages → Source: GitHub Actions，再手动触发 workflow）。

回退：`git revert` 本批提交并恢复 CNAME 即回到自定义域模式；workflow 为手动触发，无自动发布副作用。

## 2026-09-29 批 C：Web 接口写边界收紧（核心层：权限）

核心影响（维护者已分别批准，2026-09-29"合并 批准继续"按既定顺序授权批 C）：本批改变 Web API 的对外契约——无鉴权的 GET 不再能触发任何写入或测试执行；这是权限边界的产品核心变更，不是普通缺陷修复。

问题与现有覆盖：审查核实 `GET /api/hosts/doctor?repair=true` 无 API Key 即可安装项目级与用户级宿主接入文件（api_host_support.py 的 `_repair_host_diagnostics` 调 `setup_global_slash_command` 写用户目录）；`GET /api/release/readiness|proof-pack` 无鉴权可执行测试（verify_tests）与持久化报告，且 `_check_scope_coverage` 在任何评估中无条件写功能清单，`_check_compliance_closure` 会经 run_spec_compliance / run_architecture_drift / run_uiux_compliance 重算并写产物；`_validate_project_dir` 只拦 `..`，任意绝对路径放行。缓解前提（默认 127.0.0.1 监听）不变，但本机访问与对外暴露场景计入设计。

改动（分支 ocx/governance-remediation-batch-c-web-boundary，基线 1754be0）：
- super_dev/web/api_host_support.py：doctor 全量逻辑收敛为 `run_host_doctor`（repair=True 为唯一写路径）；`_validate_project_dir` 增加获准工作区约束（服务器启动目录 + `SUPER_DEV_API_PROJECT_ROOTS`，os.pathsep 分隔），越界返回 400
- super_dev/web/api.py：GET /api/hosts/doctor 拒绝 repair 参数（400）；新增鉴权 POST /api/hosts/doctor/repair；GET /api/release/readiness、/api/release/proof-pack 拒绝 verify_tests/persist（400）并以 persist_artifacts=False 只读评估；新增两条鉴权 POST（verify_tests/persist 走请求体）
- super_dev/release_readiness.py、super_dev/proof_pack.py：`persist_artifacts=False` 时不建目录、不写功能清单、compliance runner 以 persist=False 只算不写；CLI 默认值 True 行为不变
- super_dev/reviewers/spec_compliance.py、architecture_drift.py、uiux_compliance.py：run_* 增加 `persist: bool = True` 关键字参数，只读评估跳过全部报告写入（默认 True 兼容 CLI 与既有调用）
- super_dev/web/frontend/dist/index.html：修复按钮改调 POST /api/hosts/doctor/repair，新增 API Key 输入（localStorage 持久化，对应 SUPER_DEV_API_KEY）；诊断按钮仍走只读 GET
- tests/integration/test_web_api_write_boundaries.py（新增 17 项）：无 key 写操作 401、GET 写参数 400、GET 只读（persist_artifacts=False 且零 write 调用）、根约束正反例；tests/integration/test_web_api.py：fixture 增加 SUPER_DEV_API_PROJECT_ROOTS 放行 pytest 临时目录，两个编码旧行为的测试更新为新契约（doctor patch 目标随逻辑迁移至 api_host_support；release 持久化改走 POST）

取舍：GET 携带写参数返回 400 而非静默忽略（防止旧调用方以为生效）；前端修复功能在未配置 Key 时按 401 提示而非隐藏按钮（边界可见）。verify_tests 归入 POST 是因为它会运行测试套件（CPU/缓存写入）。

验证与未验证：新增边界测试 17 项通过；tests/integration/test_web_api.py 107 项全部通过（含 2 项按新契约更新）；tests/unit/test_release_readiness.py + test_proof_pack_enhanced.py 76 项通过；ruff/black 全部清洁；check_contribution_policy.py --base 1754be0 通过。未验证：前端 dist 为构建产物，无独立构建管线，仅在代码层面人工核对了 axios 调用与 Vue 绑定；实际浏览器端到端未执行。

回退：`git revert` 本批提交即恢复旧契约（无数据迁移；工作流状态不受影响）。

## 2026-09-29 批 B：状态提交协议 + 确认统一提交 + 门禁统一（核心层：权威状态与确认合同）

核心影响（维护者 2026-09-29"全部批准"授权）：① 提交协议升级为强制 CAS——存在状态时，不带旧 revision 的 StateStore 直连提交被拒绝（授权重置须显式 allow_unconditional=True）；② 权威 workflow-state.json 损坏时提交被阻断并给出恢复候选，不再静默回退 latest.json；③ 确认记录的账本/文件/事件写入收进同一把项目状态锁；④ 已定位的 Web 空 phases 绕过被真阻断——未确认状态下发起默认全阶段 run 将收到 409，这是行为变更。

问题与现有覆盖：审查核实 expected_revision 可省略（state_store.py 原 187 行默认 None、不校验）、运行路径 preserved keys 不含 revision（cli_workflow_runtime_mixin.py:1499）、损坏静默回退（load_workflow）、确认记录三步独立写入无共享锁（review_state.save_docs_confirmation + workflow_guard._update_stage_ledger）、api.py:1094 else 分支与 engine.py 默认分支均不执行确认门禁（静态链条：config 默认 7 阶段含 delivery ∈ _DOCS/_PREVIEW_CONFIRM_LATE_STAGES）。

改动（分支 ocx/governance-remediation-batch-b-state-protocol，基线 2fa1099）：
- super_dev/state_store.py：commit_workflow 损坏阻断（StateStoreError + 候选列表）+ 严格 CAS（expected/payload revision/allow_unconditional/全新状态免检）；新增 exclusive_commit() 共享锁、workflow_health()、prepare_recovery()、apply_recovery()（state_recovered 审计事件）
- super_dev/review_state.py：save_workflow_state 增加 expected_revision/allow_unconditional；两者缺省且 payload 无 revision 时按当前 revision 自 CAS（兼容存量调用方；全新状态免检）
- super_dev/work_item_identity.py：start_standard_work_item 显式 allow_unconditional=True（授权重置语义）；bind_standard_work_item 经 payload 携带 revision 自 CAS
- super_dev/workflow_guard.py：save_bound_docs_confirmation / save_bound_preview_confirmation 的账本+确认文件+事件写入收进 StateStore.exclusive_commit()，顺序为账本先行、确认文件最后落盘（中途失败时 docs_gate_status 以确认文件为准，安全阻断而非半开）
- super_dev/cli_workflow_runtime_mixin.py：preserved keys 补 "revision"；提交显式携带构造时 revision（并发写入时提交被拒而非覆盖）
- super_dev/orchestrator/engine.py：run() 的两个确认门禁移出显式分支，对最终阶段列表（显式或 config 默认）统一执行；治理组件降级继续时写入 .super-dev/governance-gaps.jsonl（降级记录不等于确认门放行）
- super_dev/web/api.py：/api/workflow/run 的门禁移出 if request.phases 分支，对最终 requested_phase_names 统一执行
- super_dev/release_readiness.py：_governance_artifact_notes 增加 governance-gaps 降级提示（不计分，提示人工核对）
- 测试：tests/integration/test_workflow_gate_unified.py（4 项：API 空 phases 未确认 409 / 确认后放行 / engine 默认路径阻断 / 显式路径阻断）、tests/unit/test_confirmation_atomicity.py（2 项：账本失败不留确认文件 / 正常路径文件+事件一致）、tests/unit/test_state_store.py 扩展（严格 CAS + 损坏阻断 + 恢复闭环）

取舍：StateStore 直连层严格必填，但 save_workflow_state 包装层对不带 revision 的存量调用方自 CAS（否则 15+ 调用点全断）；架构文档的"类型化 WorkflowMutation/commit_confirmation 完整迁移"仍为后续增量，本批以共享锁+顺序保证先行落地。引擎崩溃在"账本后、文件前"的窗口仍存在，docs_gate_status 的摘要绑定核对继续作为兜底（文件最后落盘使失败方向为安全阻断）。

验证与未验证：新增 14 项测试通过（4 门禁统一 + 2 原子性 + 8 状态存储含 2 项扩展）；tests/unit 状态/守卫相关 7 个文件 47 项通过；tests/integration/test_web_api.py 107 项通过；ruff/black 清洁。批内曾以 git stash 演示修复前红态，因当时测试文件导入笔误未取得有效红态记录，绕过结论仍以静态链条（前次汇报）+ 修复后绿测为准。未验证：tests/integration/test_cli.py 全量回归于本批提交前在后台执行，结果补记于提交信息；跨进程并发锁竞争仅靠单元级验证，未做真实多进程压测。

回退：`git revert` 本批提交；旧状态文件读取兼容不受影响，写入协议退回可选项。

## 2026-09-29 批 D1：架构漂移否定语境误报（有界缺陷修复）

问题与现有覆盖：`_parse_architecture_doc` 按全文正则抓取技术名，不区分否定语境。实证：`output/super-dev-2-6-reliability-architecture-drift.md:17` 把 "SQLite [NOT FOUND]" 列为技术缺失，而架构文档第 6 行明确"不采用……SQLite 状态数据库"。本批只修误报算法，不改质量门槛或"通过"含义（后者属批 D2）。

改动（分支 ocx/governance-remediation-batch-d1-drift-negation，基线 12b04f0）：super_dev/reviewers/architecture_drift.py——技术名提取改为逐行匹配，命中前缀含否定词（不采用/不使用/不引入/不用/不基于/不依赖/排除/而非/not using/without/rather than/instead of）的归入 negated_tech_stack，不再进入声明清单；DriftReport 增加 negated_tech_stack 字段（to_dict 同步），markdown 新增 "Explicitly Excluded Tech" 小节标注"明确排除，不计入缺失"。仅按前缀判定、宁少排不误排：无法确认否定语境的技术名仍按声明处理。新增 tests/unit/test_architecture_drift_negation.py（3 项：SQLite 否定案例不入声明清单、markdown 不再标 NOT FOUND、肯定句技术名正常声明）。

验证与未验证：3 项新测试通过；ruff/black 清洁；drift 相邻单测（compliance_evidence_identity / quality_gate）通过（见提交记录）；未验证：全库重跑 drift 报告对比（历史报告按约定不回溯重生成）。

回退：`git revert` 本批提交即恢复全文抓取行为。

## 2026-09-29 批 D2：发布就绪证据语义（核心层：验收标准）

核心影响（维护者 2026-09-29"全部批准"授权）：readiness 的"通过"含义收窄为"流程证据就绪"。无宿主真人验收记录、范围覆盖 status=unknown 不再折算为 PASS；报告新增三维度（流程证据/范围核实/宿主验收）与 blocked_unknowns 列表；spec compliance 解析不到需求时给 0 分并标记 requirements_unparsed，不再给 100。历史报告不回溯重打分。

问题与现有覆盖：审查核实 `_check_host_runtime_validation` 无记录判 PASS（release_readiness.py 原 919）、`_check_scope_coverage` status unknown 判 PASS（原 1083）、spec_compliance 解析不到需求给 100 分（spec_compliance.py 原 586），实证为 2026-09-18 报告 100/100 通过同时记载无宿主验收、coverage=12.5%、unknown=49。

改动（分支 ocx/governance-remediation-batch-d2-evidence-semantics，基线 ce53a3b）：
- super_dev/release_readiness.py：Host Runtime Validation 无记录 → passed=False（severity high，evidence.state=unknown）；Scope Coverage status unknown → passed=False（severity medium）；两项检查带结构化 evidence；ReleaseReadinessReport 新增 evidence_dimensions / blocked_unknowns（to_dict 同步），evaluate 末尾经 _evidence_dimensions 计算（process_evidence=report.passed、scope_verified∈{verified/partial_unknown/unknown/blocked/not_evaluated}、host_accepted∈{accepted/unknown/blocked/not_evaluated}，partial 场景 unknown_count>0 计入 blocked_unknowns 但不额外阻断检查）；to_markdown 新增 Evidence Dimensions 小节与"未核实验收项"列表；executive summary 通过分支改为"流程证据就绪"措辞并在存在 blocked_unknowns 时显式声明"不代表全部需求已验证"
- super_dev/reviewers/spec_compliance.py：ComplianceReport 新增 requirements_unparsed 字段；解析不到需求时 score=0 + 标记（不再 100）
- 测试：新增 tests/unit/test_release_readiness_evidence_dimensions.py（4 项）；tests/unit/test_release_readiness.py 的 test_release_readiness_passes_when_required_artifacts_exist 原同时依赖两个 unknown→PASS 折算口径，按新语义更新为仅有的两个预期失败项并断言三维度与 blocked_unknowns

取舍：partial（有清单但存在 unknown 条目）不额外阻断检查本身，只在维度与 blocked_unknowns 中显式呈现——避免把"未核对"一律升级为硬阻断；status=unknown（连清单都没有）才阻断。绿径（三维度全 verified）需真实 product-audit 清单与宿主验收记录，留待批 E 实际验收时验证。

验证与未验证：新增 4 项 + test_release_readiness + proof_pack 回归共 80 项通过；ruff/black 清洁。未验证：真实仓库重跑 readiness 的前后对比（历史报告不回溯，当前仓库的重新评估属批 E 实际验收）。

回退：`git revert` 本批提交恢复原折算口径。

## 2026-09-30 批 E：跨入口覆盖收尾 + 真实 readiness 评估

问题与现有覆盖：批 B/D2 后，跨入口"未确认不得推进"测试覆盖了 Web run（显式/空 phases）与 WorkflowEngine（显式/默认），creators 任务执行门有既有单测；SpecBuilder 的 docs 门只有放行路径测试，阻塞路径缺失。真实 readiness 评估此前未在 D2 新语义下跑过本仓库。

改动（分支 ocx/governance-remediation-batch-e-coverage，基线 18385f2）：
- 新增 tests/unit/test_spec_gate_unified.py（2 项）：SpecBuilder.create_change 未确认 docs 抛 WorkflowGateError(gate=docs_confirmation)；确认后正常生成 change。
- tests/unit/test_release_readiness.py 的 _prepare_release_ready_project 夹具升级为 D2 下真实就绪：PRD 带可解析功能条目（### 功能标题）、change tasks.md 勾选、经 update_host_runtime_validation_state 录入 codex-cli 验收；这些输入先于 evidence_identity 产物水化写入以保持缓存身份自洽。test_release_readiness_passes_when_required_artifacts_exist 断言从"两个旧口径折算出的全绿"（批 D2 时临时改为两项预期失败）回到"真实就绪的全绿"，并断言 host_accepted=accepted、scope_verified∈{verified, partial_unknown}。

被真实评估抓到的回归（本批修复）：`super-dev release readiness` 的完成前验证在合成项目上运行 replay 测试 test_representative_scenarios_execute_real_new_and_legacy_flows，其旧流程断言"无关发布项全过"在 D2 下因合成项目缺宿主验收/范围核实而失败（旧流程因无关发布项未通过: Host Runtime Validation, Scope Coverage）。夹具升级后该测试恢复通过——修复方式是让合成项目真实就绪，不是放宽 replay 断言。tests/extensions 此前不在批 B/D2 的回归范围，这一盲区由本仓库自身的完成前验证机制暴露。

验证与未验证：新增/更新测试与回归共 47 项通过（readiness 全套 + replay + 门覆盖 + D2 语义）；ruff/black 清洁；政策检查 --base 18385f2 通过。真实评估两次：第一次（2026-09-30，工作区含本批未提交改动）51/100 FAIL——完成前验证如实报告"验证期间当前代码版本发生变化"（评估运行 pytest 时正在编辑夹具）与 1 个 replay 失败，Host Runtime Validation 进入待收尾清单，D2 语义在真实数据上生效；第二次（干净树，提交后）结果见 tasks.md 与 output/super-dev-2-6-reliability-release-readiness.md。未验证：真人宿主 runtime validation 录入仍归维护者（命令：`super-dev review runtime-validation --host <目标宿主> --status passed` 或鉴权 POST /api/hosts/runtime-validation），录入后复跑 readiness 即可验证三维度全绿路径。

回退：`git revert` 本批提交；夹具退回旧口径后 replay 与 readiness 全绿断言需一并回退。

### 2026-09-30 PR #21 CI 修复（随批 E 提交）

PR #21 首轮 CI：Contribution policy/Security/Windows baseline 通过；Quality×3 与 Core verification×5 失败，两处均为本整改引入、本地回归盲区：

- Quality（mypy，scripts/check_type_gates.py）：批 D2 在 to_markdown 新增的 `for item in self.blocked_unknowns`（str）与既有 recent_timeline 循环的 `item`（dict）撞名，mypy 按首个绑定推断报 4 错。改名为 unknown_item；本地全量 type gate（22 文件）与全库 ruff 通过。
- Core verification（run_safe_baseline）：tests/extensions/test_cli.py 的 test_proof_pack_and_web_api_do_not_trigger_fresh_verification 直接调用 get_release_readiness 端点函数（不经 TestClient，此前 grep TestClient 未覆盖），tmp 项目目录被批 C 的获准工作区约束拒绝（400）。新增 tests/extensions/conftest.py autouse 夹具统一放行 pytest 临时目录（与 tests/integration/test_web_api.py 同口径）。该测试本地复现通过、CI 失败的差异源于 safe-baseline 运行器的隔离环境，夹具修复与环境无关。

教训已计入：后续涉及 Web API 边界的改动，回归范围需包含 tests/extensions 与 scripts/check_type_gates.py 全量。

同轮第二处 CI 失败（Quality 全量 pytest）修复：tests/integration 的 test_web_api.py 与 test_cli.py 各自持有 `_prepare_release_ready_project` 拷贝（区别于 test_release_readiness.py 的那份），三处测试断言"readiness passed is True / proof-pack ready"，在批 D2 下因夹具仍依赖两个折算口径而失败。新增 tests/support/release_ready_inputs.py 统一提供真实就绪输入，并按依赖顺序拆为两步：write_release_ready_docs（PRD 功能条目 + 任务勾选 + 缺失文档补写，须先于 evidence_identity 水化）与 record_release_ready_acceptance（按最终产物重绑 docs/preview 确认、补建 workflow-state/SESSION_BRIEF 以满足 repo 连续性探针、录入 codex-cli 真人验收，须在一切会改写绑定文件的产物水化之后）。三处夹具分别接入；其中 _prepare_proof_pack_project 因覆盖 architecture/uiux 且水化重写 preview 绑定文件，acceptance 置于最后。验证：三个目标测试 + tests/integration/test_web_api.py 与 test_cli.py 全量 334 项 + readiness/replay/门覆盖 53 项全部通过；type gate/ruff/black/政策检查通过。
