# Tasks — governance-remediation-2026-09

## 批 A：安装指引与链接对齐（已授权并执行，2026-09-29）

- [x] 固定基线提交 75ece32，建独立分支 ocx/governance-remediation-batch-a
- [x] 修复 docs 6 个文件共 12 处机器本地绝对路径链接（/Users/weiyou/... → 仓库相对链接）
- [x] 统一安装命令为 GitHub-only 固定 Tag：docs/WORKFLOW_GUIDE.md §2.1、docs/RELEASE_RUNBOOK.md、install.sh 报错提示、官网 7 个活跃指引文件（HeroSection、BottomCta、CodeDemoSection、ShowcasePageContent、DocsPageContent×5、lib/constants.ts×2）
- [x] 保留历史记录原语义：docs/releases/2.4.0.md、官网 Changelog 2.2.0 历史条目、completion-verification 旧 adoption 记录
- [x] 复扫确认活跃指引零残留；相关单测 80 项通过；贡献政策检查通过（--base 75ece32）
- [ ] 维护者复核并合并

## 批 A2：官网身份切换至 GitHub Pages（已授权并执行，2026-09-29）

- [x] 固定基线提交 af1d1ec，建独立分支 ocx/governance-remediation-batch-a2-website
- [x] SITE_URL 与 SITE_BASE_PATH 切至 https://mixyoung.github.io/super-dev/（assetPath 与 basePath 对齐）
- [x] lib/github.ts star API 与 Footer/Changelog/BottomCta/layout 全部身份链接切至 mixyoung/super-dev
- [x] Footer PyPI 链接改 GitHub Releases；署名改 mixyoung
- [x] 删除 public/CNAME，构建默认进入 GitHub Pages 模式（basePath /super-dev）
- [x] 新增 .github/workflows/website-pages.yml（仅手动触发，不自动发布）
- [ ] 维护者启用 GitHub Pages（Settings → Pages → Source: GitHub Actions）后手动触发部署验证
- [ ] 维护者复核并合并

## 批 C：Web 权限边界（已批准并执行，2026-09-29，基线 1754be0）

- [x] /api/hosts/doctor 的 repair/force 写动作拆为鉴权 POST /api/hosts/doctor/repair，GET 拒绝 repair（400）；逻辑收敛为 api_host_support.run_host_doctor
- [x] /api/release/readiness、/api/release/proof-pack：verify_tests/persist 拆入鉴权 POST；GET 只读拒绝写参数并以 persist_artifacts=False 评估（功能清单、spec/drift/uiux 产物、output 目录均不写）
- [x] _validate_project_dir 获准工作区约束（服务器启动目录 + SUPER_DEV_API_PROJECT_ROOTS，越界 400）
- [x] 前端 dist：修复按钮改走 POST + API Key 输入（localStorage）
- [x] 新增 tests/integration/test_web_api_write_boundaries.py（17 项：401/400/只读零写入/根约束正反例）；既有 web_api 107 项、readiness+proof-pack 76 项回归通过；ruff/black 清洁；政策检查通过
- [ ] 维护者复核并合并

## 批 B：状态/确认协议 + 门禁统一（已批准并执行，2026-09-29，基线 2fa1099）

- [x] 各入口"未确认不得推进"回归测试（tests/integration/test_workflow_gate_unified.py，4 项，锁定 Web 空 phases 绕过）
- [x] StateStore 严格 CAS：存在状态时缺 revision 的直连提交被拒；授权重置须 allow_unconditional；运行路径 preserved keys 补 revision 并显式携带 expected_revision
- [x] 权威状态损坏显式报阻（StateStoreError + 候选）+ workflow_health/prepare_recovery/apply_recovery + state_recovered 事件
- [x] 确认记录统一锁提交：StateStore.exclusive_commit 下账本先行、确认文件最后落盘；原子性测试 2 项
- [x] api.py / engine.py 门禁对最终阶段列表统一执行（显式与 config 默认同路径真阻断）
- [x] 治理降级落 .super-dev/governance-gaps.jsonl；readiness 治理注记提示人工核对（不计分、不替代确认门）
- [x] 回归：状态/守卫单测 47 项、web 集成 107 项通过；ruff/black 清洁；CLI 全量回归见提交记录
- [ ] 维护者复核并合并

## 批 D1：架构漂移否定句误报（已批准并执行，2026-09-29，基线 12b04f0）

- [x] 逐行否定语境解析（前缀否定词判定，宁少排不误排）；negated_tech_stack 字段与 "Explicitly Excluded Tech" 呈现
- [x] SQLite 案例回归测试（3 项）+ 相邻单测回归 + lint 清洁

## 批 D2：证据语义（已批准并执行，2026-09-29，基线 ce53a3b）

- [x] 宿主验收缺失 → blocked（severity high）；范围 status=unknown → blocked；结构化 evidence
- [x] 三维度 evidence_dimensions + blocked_unknowns（to_dict/to_markdown/executive summary 同步措辞）
- [x] spec_compliance 解析不到需求 → 0 分 + requirements_unparsed
- [x] 测试：新增 4 项证据语义测试；既有"产物齐备"测试按新语义更新（原依赖两个 unknown→PASS 折算口径）；readiness+proof-pack 回归 80 项通过
- [ ] 维护者复核并合并

## 批 E：覆盖与验收收尾（已执行，2026-09-30，基线 18385f2）

- [x] 跨入口"未确认不得推进"覆盖清单落档：Web run（显式/空 phases）、WorkflowEngine（显式/默认）、creators 任务执行（既有）、SpecBuilder（本批补齐阻塞/放行，tests/unit/test_spec_gate_unified.py 2 项）
- [x] 真实 readiness 评估两次留档（证据 output/super-dev-2-6-reliability-release-readiness.md）：
  - 第一次（工作区含未提交改动）：51/100 FAIL——完成前验证如实报告"验证期间代码变化"+1 个 replay 失败；该失败为夹具依赖旧口径的真实回归，本批以"合成项目真实就绪"修复（不放宽断言）
  - 第二次（干净树，提交 e98ff31）：65/100 FAIL——完成前验证 PASS（393 执行 0 失败，replay 修复经真实运行验证）、代码变化=否；三维度 process_evidence=not_ready / scope_verified=partial_unknown(unknown=49) / host_accepted=unknown；待收尾 Host Runtime Validation、Spec Quality、Delivery Closure。对比历史"100/100 通过 + unknown=49"，新口径不再吸收未核实项
- [x] 夹具诚实化：_prepare_release_ready_project 升级为 D2 下真实就绪（PRD 功能 + 任务勾选 + codex-cli 验收录入），全绿断言恢复且为诚实全绿；readiness/replay/门覆盖回归 47 项通过
- [ ] 真人宿主 runtime validation 录入（归维护者：`super-dev review runtime-validation --host <目标宿主> --status passed`，或鉴权 POST /api/hosts/runtime-validation）后复跑 readiness 验证三维度全绿
- [ ] 下一发布周期重生成 Delivery Closure / Spec Quality 证据（当前产物相对整改后代码已陈旧，属发布工作非本整改范围）
- [ ] 维护者复核并合并
