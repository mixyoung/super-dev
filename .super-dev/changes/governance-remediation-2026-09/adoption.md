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
