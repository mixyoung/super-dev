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

## 批 B：状态/确认协议 + 门禁统一（待维护者批准）

- [ ] 先写各入口"未确认不得推进"运行时回归测试，锁定 Web 空 phases 绕过（api.py:1094 + engine.py:565）
- [ ] StateStore.commit_workflow 的 expected_revision 必填；运行路径 preserved keys 补 revision
- [ ] 权威状态损坏显式报阻 + 恢复候选展示 + state_recovered 审计事件
- [ ] 确认记录统一经 StateStore 提交（review-state 文件 + 阶段账本 + 事件同锁）
- [ ] api.py/engine.py 门禁移出显式分支，对最终阶段列表统一执行；workflow_guard.py:522/552 同步
- [ ] 治理降级与确认门分离：governance_gap 仅记录降级事实；可选治理组件继续运行的条件与就绪检查处理方式单独写明

## 批 D1：架构漂移否定句误报（有界缺陷，待执行）

- [ ] 漂移解析限定显式技术栈上下文；否定表述（"不采用/不使用"）排除 NOT FOUND 判定；以 SQLite 案例为回归测试

## 批 D2：证据语义（待维护者批准）

- [ ] 发布就绪三维度呈现（流程证据/范围核实/宿主验收）；unknown 不折算 PASS；无宿主验收记录不再判 PASS
- [ ] spec_compliance 解析不到需求不再给 100 分
- [ ] 报告模板与 executive summary 措辞同步；历史报告不回溯重打分

## 批 E：覆盖与验收收尾（待排期）

- [ ] 跨入口、跨宿主"未确认不得推进"覆盖测试与真人宿主验收记录
