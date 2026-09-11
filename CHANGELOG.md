# Changelog

本文件记录 Super Dev 的所有重要变更。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [2.5.1] - 2026-09-12（仓库版本，尚未发布）

### 修复

- 提示生成绑定明确的当前变更，恢复未完成任务，不再按最新文件或固定阶段猜测执行上下文。
- 对齐只读请求、标准预览确认与无界面项目的适用边界，保留既有确认和质量要求。
- 对齐知识、专家、宿主及框架提示；无显式适用条件的知识要求继续默认强制，明确条件按条件执行。
- 修复常规 QA 被验证变体覆盖、专家自定义设定未进入提示及引号解析问题，补充相关回归。

### 保留边界

- 不增加主流程、专家或知识自循环，不改变默认质量阈值。
- SEEAI 比赛内容保持不变，仅同步版本元数据；不更新用户全局安装。
- 本条记录代码版本变更，不表示已创建 Git 标签、发布安装包或部署。详见 [2.5.1](docs/releases/2.5.1.md)。

## [2.5.0] - 2026-09-07

本 fork 的 GitHub-only 发行版；保留宿主执行、Super Dev 治理的使用方式。完整说明见 [2.5.0](docs/releases/2.5.0.md)。

### 新增与完善

- 结构化范围声明、只读阶段影子台账与对照；不授予影子台账流程控制权。
- 最小扩展机制与完成前验证：来源锁、权限、执行器、证据、所有权和路径检查。
- 择优吸收 Forge、需求审查、Grill 与 UmaDev 的软内容；固定贡献和演进边界，不引入独立 UmaDev 程序或新必经阶段。
- Windows 测试隔离与真实必过 CI，项目必需/用户可选的宿主就绪口径。

### 修复

- 类型与外部输入边界、缓存类型隔离、UI 契约安全文件名、中文编码、跨平台路径、日志释放与 Git Bash 选择。
- 规则解析内容缓存与实例隔离，知识索引绑定目标项目；性能脚本失败正确返回非零。
- 七个依赖的已知漏洞版本下限，修正安全 CI 的错误调用和吞错。
- 补齐发行包遗漏的既有规则 YAML、设计数据、文档模板及 Web 静态入口。

### 发布边界

- 不上传原作者 PyPI 包；安装/升级使用本 fork 的 Git 标签或 Release wheel。
- 标准流程、确认权与质量阈值不变；冷启动和热初始化指标分别报告。
- 可选宿主插件包不作为本次独立发行制品，旧开发任务的应用验收状态不冒充包发布结果。

## [2.3.4] - 2026-04-10

### 主题

Plan-Execute 编排升级 + Overseer 监督者 + Claude/Codex 混合审查

### 致谢

- 感谢 **staruhub** 提交并推动合入 [PR #10](https://github.com/shangyankeji/super-dev/pull/10)，本次版本的核心能力来自这次贡献。

### 新增

- **Plan-Execute 执行引擎**：结构化执行计划、拓扑波次排序、步骤状态机、步骤级验证门、失败预算和持久化计划状态。
- **Overseer 监督者角色**：独立质量观察者，在阶段与步骤检查点持续监控计划偏差、质量下降和未解决审查结果，并可在关键问题下中止流水线。
- **Claude Code + Codex 混合模式**：Claude Code 负责实现、Codex 负责独立审查，审查结果由 Overseer 统一跟踪和校验。
- 新增配置项：`execution_mode`、`overseer_enabled`、`codex_review_enabled`、`codex_review_phases`、`overseer_halt_on_critical`、`plan_failure_budget`。

### 变更

- 官网首页已同步到 `2.3.4`。
- 官网更新历史页已新增 `2.3.4` 条目。
- README、发布说明和版本真源已统一到 `2.3.4`。

## [2.3.3] - 2026-04-07

### 主题

宿主适配质量 + 安装升级体验

### 废弃

- **Claude Code 不再安装 `super-dev-core` 别名**：统一为 `super-dev` 单一入口。升级后自动清理旧版残留（对用户无感）。

### 新增

- **`super-dev update` 升级后自动迁移**：pip/uv 升级完成后自动调用新版 `super-dev migrate`，一步完成升级+迁移。
- **`super-dev` 无参数自动迁移旧版**：检测到项目配置版本低于当前 CLI 版本时自动迁移。
- **`super-dev migrate` 全宿主迁移**：重写为全宿主迁移引擎，自动检测所有已接入宿主并重建配置/Skill/slash/协议到最新版。
- **`--auto` 同族宿主智能去重**：同时检测到 cursor + cursor-cli 等同族宿主时自动选择功能更完整的 CLI 版本。
- **Roo Code**：IntegrationTarget 补齐 `.roo/commands/super-dev.md`。
- **OpenCode**：IntegrationTarget 补齐 `.opencode/commands/super-dev.md`。
- **Kilo Code**：补齐项目级 `.kilocode/skills/super-dev-core/SKILL.md` 和用户级 Skill surface。
- **VS Code Copilot**：补齐 HOST_CERTIFICATIONS 认证条目。

### 修复

- **commands 文件内容错误**：`setup()` 生成 `.roo/commands/`、`.opencode/commands/` 等 command 文件时走 fallback 生成了通用 rules 内容而非 slash command 格式。
- **SkillFrontmatter 默认 name**：从 `"super-dev-core"` 改为 `"super-dev"`。
- **所有 `skill_name="super-dev-core"` 硬编码**：全部改为 target-aware 或统一为 `"super-dev"`。
- **`install.sh` Skill 提示**：去除 `super-dev-core` 名称。
- **版本提示**：统一为 `super-dev update` 而非 `pip install -U`。

### 测试验证

- 全量 2151 测试通过，0 失败。

## [2.3.2] - 2026-04-06

### 新增

- Claude Code 按 `CLAUDE.md + .claude/skills + ~/.claude/skills + optional plugin enhancement` 收口。
- Codex 按 `AGENTS.md + .agents/skills + repo plugin enhancement` 收口，并区分 App/Desktop、CLI、fallback 三入口。
- `session_resume_card`、`doctor`、`detect`、`start`、`continue`、Web API 显示现实场景卡（第二天回来继续开发、只想知道当前唯一下一步、当前确认门内继续修改、本地流程中断后恢复）。
- `.super-dev/SESSION_BRIEF.md` 新增 `## 现实场景怎么做` 段落。
- 新增/强化 `workflow-history`、语义 workflow 事件、`hook-history`、`workflow/framework/hook/operational harness`、`recent operational timeline`，已进入 `proof-pack`、`release readiness`、恢复卡、`SESSION_BRIEF`。
- `framework_playbook` 覆盖 `uni-app`、`Taro`、`React Native`、`Flutter`、`Desktop Web Shell`，进入提示词、UIUX 文档、`ui-contract.json`、frontend/implementation builder、runtime/quality gate/proof-pack/release readiness。

### 变更

- 21 个宿主口径继续收正：`20` 个统一接入宿主 + `1` 个 OpenClaw 手动插件宿主。
- Kiro / Qoder / Cursor / Trae / CodeBuddy 等宿主的官网说明、安装引导、能力审计页与代码模型重新对齐。
- emoji 作为功能图标被系统级禁止，被 runtime、UI review、quality gate、release readiness 一起拦截。

## [2.3.1] - 2026-04-03

### 新增

- Codex 深度适配：`AGENTS.md + Skills + repo plugin 增强` 双层模型。
- Codex 三入口统一：App/Desktop `/super-dev`、CLI `$super-dev`、回退 `super-dev: 你的需求`。
- Claude Code 深度适配：`CLAUDE.md + .claude/skills + ~/.claude/skills + optional plugin enhancement`。

### 变更

- 安装引导不再使用"slash 宿主 / 非 slash 宿主"二分法，改为基于宿主真实入口模型。
- Codex 标记为 skill-first 模式（App/Desktop `/super-dev`、CLI `$super-dev`）。
- Claude Code 标记为 `CLAUDE.md + Skills` 主模型，`commands / agents` 仅作为兼容层保留。
- Onboard 完成页删除过期 `/super-dev init` 提示，改为真实宿主入口指导。
- 版本真源统一为 `2.3.1`，README / README_EN / QUICKSTART / HOST_USAGE_GUIDE / INSTALL_OPTIONS 同步更新。
- 官网首页 Hero、终端演示、更新历史同步到 `2.3.1`。

## [2.3.0] - 2026-03-31

### 新增

#### Enforcement 执行层

- `super-dev enforce install` — 自动为宿主配置 hooks（PreToolUse emoji 检查等）。
- `super-dev enforce validate` — 运行验证脚本，检查 emoji/import/color/route 合规性。
- `super-dev enforce status` — 查看当前执行层配置状态。
- `super-dev detect --auto` 时自动安装 enforcement hooks。

#### Memory 记忆系统

- `super-dev memory list` — 列出所有项目记忆。
- `super-dev memory show <name>` — 查看指定记忆内容。
- `super-dev memory forget <name>` — 删除指定记忆。
- `super-dev memory consolidate` — 触发 Dream 整合。
- 4 种记忆类型：user、feedback、project、reference。
- MEMORY.md 索引，200 行 / 25KB 自动限制。
- Dream 整合器：4 阶段后台记忆合并（去重、聚合、摘要、写回）。

#### 代码生成器

- `super-dev generate scaffold --frontend next` — Next.js App Router 项目脚手架（16 个文件）。
- `super-dev generate components` — UI 组件脚手架（Button/Card/Input/Modal/Nav/Layout）。
- `super-dev generate types` — 从架构文档生成共享 TypeScript 类型。
- `super-dev generate tailwind` — 从 UIUX 设计 tokens 生成 Tailwind 配置。

#### Expert 专家系统

- `super-dev experts list` — 列出所有专家（内置 + 自定义）。
- `super-dev experts show <name>` — 查看专家定义。
- 12 位内置专家 Markdown 定义：PM、ARCHITECT、UI、UX、SECURITY、CODE、DBA、QA、DEVOPS、RCA、PRODUCT、VERIFICATION。
- 用户可通过 `.super-dev/experts/*.md` 自定义专家。
- 新增对抗性验证专家（VERIFICATION.md），在质量门禁中担任"红方"角色。

#### Hook 系统

- `super-dev hooks list` — 列出已配置的 hooks。
- `super-dev hooks test <event>` — 测试 hook 执行。
- 8 种 hook 事件：PrePhase、PostPhase、PreDocument、PostDocument、PreQualityGate、PostQualityGate、OnError、SessionStart。
- 在 `super-dev.yaml` 中通过 YAML 配置，支持 Shell 和 Python 执行器。

#### Context Compact（上下文压缩）

- `super-dev compact list` — 列出各阶段的压缩摘要。
- `super-dev compact show` — 查看指定阶段的压缩内容。
- 9 段结构化摘要模板，自动在阶段切换时保存/恢复上下文。

#### Web API

- 11 个新端点：记忆管理、hooks 管理、专家查询、上下文压缩、会话状态等。

#### 条件规则系统

- 新模块 `super_dev/rules/` — 支持 `.super-dev/rules/*.md` 条件规则。
- 规则可通过 frontmatter `paths` 指定只对特定文件生效，支持排除模式。

#### UX 增强

- 首次使用引导：3 步快速开始面板，最多显示 4 次后自动隐藏。
- Tips 提示系统：根据当前阶段显示上下文相关的操作建议。
- 项目模板：`super-dev init --template ecommerce/saas/dashboard/mobile/api/blog/miniapp`。
- `doctor --fix`：自动修复检测到的安装问题。
- Shell 补全：`super-dev completion bash/zsh/fish`。
- 版本更新检查：PyPI 24h 缓存，有新版时提示升级。
- `super-dev feedback`：快速打开 GitHub Issues 反馈。
- `super-dev migrate`：2.2.0 → 2.3.0 一键迁移。

### 变更

- Skill 模板引擎升级：支持宿主特定 frontmatter 渲染、编码前门禁、常见错误速查、阶段宣告机制。
- Prompt 生成器重构为分层注册制（9 段优先级架构），支持数据驱动规则和行为约束模板。
- Pipeline 引擎集成 Hook 系统、上下文压缩、记忆提取、Session Brief 全链路增强。
- CLAUDE.md 增强：编码约束段、技术栈预研要求、图标与视觉规则、前后端对齐规则、每文件自检要求。
- 4-Agent 并行审查框架（复用 + 质量 + 效率 + 安全）。
- 验证脚本增强：多级输出（Level 1 阻塞 / Level 2 警告 / Level 3 建议），新增 console.log / hardcoded localhost / TODO-FIXME / 大文件 / package.json scripts 检查。
- `--help` 分组显示（核心 / 治理 / 分析）。
- 品牌输出使用纯 ASCII 字符，兼容所有终端。
- 版本号全面统一为 2.3.0。

### 破坏性变更

- 版本号从 2.2.0 升级至 2.3.0。
- `super-dev.yaml` 中 version 字段默认值变更为 2.3.0。
- 配置迁移：运行 `super-dev detect --auto` 以更新宿主集成配置。

### 修复

- `detect --auto` 现在会实际安装文件（之前仅生成报告）。
- `detect` 与 `doctor` 现在使用相同的检测逻辑（不再出现互相矛盾的结果）。
- `super-dev` 无参数时显示欢迎信息而非内部状态。
- `super-dev status` 在初始化后显示"已初始化，等待开始"。
- SKILL.md 中 `config show` 修正为 `config list`。
- 仓库地址修正为 `shangyankeji/super-dev`。

### 测试验证

- 全量测试：1643 passed。
- `ruff check`：通过。
- `python3 -m compileall super_dev`：通过。

## [2.2.0] - 2026-03-29

### 新增

- 重构工作流状态机与恢复链，补齐 `resume / next / SESSION_BRIEF / workflow-state` 语义，支持下班后、宿主关闭后、第二天回来继续当前流程。
- 宿主接入与诊断链路升级，统一 `start / detect / doctor / Web API` 的决策卡与恢复卡。
- UI 系统正式接入主流程：新增 `ui-contract.json`、`design-tokens.css`、`ui-contract-alignment`，从需求到 release 全链路治理。
- Release / proof-pack / quality gate / release readiness 进一步打通。
- UI 组件生态偏向 `shadcn/ui + Radix + Tailwind`，允许基于场景选择更合适方案。
- UI review 新增对主题入口、导航骨架、组件导入路径、反模式命中的结构化检查。
- `quality gate`、`proof-pack`、`release readiness`、`frontend-runtime` 均已纳入 UI 契约执行校验。
- 支持 Windows / 自定义安装路径发现逻辑，支持 `SUPER_DEV_HOST_PATH_<HOST>` 覆盖。

### 变更

- 正式产品口径统一为 `20` 个统一接入宿主，`OpenClaw` 改为手动插件安装路径。
- 宿主安装、检测、恢复、继续、返工、发布动作语义统一。
- 显式指定宿主时，系统会围绕该宿主给出决策，不再被自动检测结果带偏。

### 测试验证

- 全量测试：1281 passed。
- `ruff check`：通过。
- `python3 -m compileall super_dev`：通过。
