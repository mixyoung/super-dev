---
name: super-dev
description: Use when the user explicitly enters or resumes the Super Dev pipeline in Codex for research-first, commercial-grade delivery.
metadata:
  version: "2.4.0"
---
# super-dev for Codex CLI

## 关键约束提醒（每次操作前必读）

以下规则在整个开发过程中始终有效，不得以任何理由违反：

1. **图标系统**: 功能图标只能来自 Lucide / Heroicons / Tabler 图标库。绝对禁止使用 emoji 表情 作为功能图标、装饰图标或临时占位。如果你发现自己即将输出包含 emoji 的 UI 代码，停下来，改用图标库组件。

2. **AI 模板化禁令**: 禁止紫/粉渐变主色调、禁止 emoji 图标、禁止无信息层级的卡片墙、禁止默认系统字体直出。

3. **代码即交付**: 不允许“先用 emoji 顶上后面再换”。图标库必须在第一行 UI 代码前就锁定。

4. **自检规则**: 在向用户展示任何 UI 代码或预览前，必须自检源码中不存在任何 emoji 字符（Unicode range U+2600-U+27BF, U+1F300-U+1FAFF）。发现后先替换为正式图标库再继续。

## Direct Activation Rule（强制）

- If this skill is invoked, Super Dev pipeline mode is already active.
- Do not spend a turn saying you will read the skill first, explain the skill, or decide whether to enter the workflow.
- Do not answer with variants of "我先读取 skill 再判断流程".
- If this file is loaded from `~/.codex/skills`, treat it as the compatibility mirror of the same Super Dev contract.

## 沟通与环境适配（强制）

- 默认使用 Skill 使用者的母语、文字习惯和熟悉程度；面向消费者的产品文案服从目标用户语言，不因内部工具使用英语就要求用户理解英语。
- 面向中国大陆用户的用户界面、聊天、确认问题、错误提示和报告，优先使用自然、直接、符合中国大陆语言习惯的中文。
- 技术概念第一次出现时，使用“中文名称（英文代码名）”；后续优先只用中文名称，仅在精确核对时再次显示英文代码名。
- 状态统一显示为通过（`PASS`）、失败（`FAIL`）、受阻（`BLOCKED`）；不得面向用户只显示裸英文状态。
- `candidate` 面向用户统一称“当前代码版本”，只在证据详情中显示字段（`candidate_digest`）。
- 命令、文件名和程序字段保留精确英文原文并使用代码格式；解释仍先用中文。
- 内部日志、JSON 和 API 字段可以保留英文，但不得直接照搬成用户文案。
- 适配实际操作系统、Shell、路径形式、仓库约定和已安装运行环境。Windows环境不得默认给出只能在Bash执行的命令；要求用户决定前，先说明机制做什么、影响什么和不决定的代价。

## 分层编排与工作区所有权（强制）

- Super Dev是当前任务唯一的完整开发流程（Harness）和阶段状态所有者。宿主可以使用子代理（subagent）、Orca、OMP或其他已验证工具完成互不干扰的有界任务，但它们只是同一流程里的执行者，不是第二套Harness。
- 目标、验收条件、权限、仓库规则和工作区安排从外层向内层继承；每往下一层，范围和权限只能缩小，不能自行扩大。
- 只有已声明的安排负责人（`PLACEMENT_OWNER`）可以创建分支和工作区。若执行者已由Orca、Super Dev或上层代理放入指定工作区，默认不得再创建分支、工作区、协调器或下一级执行者，除非任务契约明确授权。
- 每个可变工作区同时只能有一个生产写入者。只读研究和评审只有在范围与副作用互不干扰时才可并行。
- 执行者向上回传产物、测试证据、风险和结果回执；只有上层整合负责人合并候选，只有Super Dev Core推进持久化阶段状态。
- 默认下一级分派（`MAY_SPAWN_SUBWORKERS`）为`no`。已经被安排的执行者不得用新的分支或工作区重复上层已完成的隔离工作。

## 触发方式（强制）

- Treat `super-dev: <需求描述>` and `super-dev：<需求描述>` as the AGENTS-driven natural-language fallback entry point.
- Treat `$super-dev` as the explicit official Skill mention when the Codex host exposes skills by name.
- In Codex desktop/app, if the slash list shows this enabled skill, selecting `/super-dev` from that list is valid because it resolves to this Skill rather than a custom project slash command.
- Do not treat it as ordinary chat.
- 当前宿主负责调用模型、工具、终端与实际代码修改。
- Super Dev 不是大模型平台，也不提供自己的代码生成 API。

## Runtime Contract（强制）

- Super Dev 由两部分组成：
  1. 当前项目内的本地 Python CLI 工具
  2. 当前宿主里的规则/Skill/命令映射
- 当前宿主负责调用模型、联网、终端、编辑器与实际代码修改。
- 当用户通过 Codex App/Desktop 的 `/super-dev` skill 入口、Codex CLI 的 `$super-dev`，或 `super-dev: ...` / `super-dev：...` 回退入口触发时，都意味着你必须进入 Super Dev 流水线。
- 需要研究、设计、编码、运行、调试时，优先使用 Codex 自身的 web/search/terminal/edit 能力。
- 需要做治理动作时，才使用本地 `super-dev` CLI。

## 宿主交互边界

普通用户只需要记住 3 个终端命令：

```bash
super-dev
super-dev update
super-dev uninstall
```

普通用户优先只记住这些宿主表达：

```text
/super-dev <goal>
/super-dev-seeai <goal>
继续当前流程
现在下一步是什么
```

文本回退宿主优先使用：

```text
super-dev: <goal>
super-dev-seeai: <goal>
```

维护/治理场景才显式进入：

```text
/super-dev-work <mode> <goal>
/super-dev-run <stage|resume|status|next>
/super-dev-review <target> <action>
```

工作模式固定为：

- `new`：从 0 到 1
- `evolve`：已有项目增量迭代
- `variant`：从现有项目派生新版本
- `patch`：在现有项目上修 bug / 做整改
- `resume`：继续当前中断流程

硬规则：

- `new` 才能直接从 `research -> docs` 开始
- `evolve / variant / patch` 必须先 `baseline`
- baseline 必须先分析现有功能、架构、代码、路由/API、UI 与约束，再进入差量 research 和三文档
- `resume` 是默认场景，不是异常场景

恢复是默认场景，不是补充场景。优先理解这些表达：

- `继续当前流程`
- `现在下一步是什么`
- `/super-dev 继续当前流程`

内部 CLI 能力仍可存在，但不应再被当成普通用户主心智。

## 首轮响应契约（强制）

- 首次触发时第一轮回复必须说明：流水线已激活，当前阶段是 `research`。
- 先读取 `.super-dev/WORKFLOW.md` 与 `output/*-bootstrap.md`（若存在）。
- 说明固定顺序：research -> 三份核心文档 -> 等待确认 -> Spec/tasks -> 前端优先 -> 后端/测试/交付。
- 三份核心文档完成后暂停等待确认；未经确认不创建 Spec 也不编码。

### research 双引擎

**引擎 1: 本地知识发现** — 优先读取 `knowledge/` 和 knowledge-bundle.json，并在当前宿主里把结论沉入 `output/*-research.md`。

**引擎 2: 宿主联网研究** — WebFetch/WebSearch 搜索同类产品、竞品和官方文档，写入 `output/*-research.md`。

两个引擎的结果都必须在 PRD/架构/UIUX 文档中被继承。

## 改动范围登记（文档确认后、创建 Spec 时执行）

- 只登记已经由文档和用户确认的改动范围，不根据项目技术栈猜测已有项目的范围。
- 普通流程在三份核心文档确认前启动完整流水线时，不填写改动范围参数（`--changed-surfaces`）；文档已经确认后的恢复或定向执行才可以填写。
- 可用范围包括：产品（`product`）、架构（`architecture`）、界面规范（`uiux`）、前端（`frontend`）、界面与交互（`ui`）、路由（`route`）、样式（`style`）、组件（`component`）、后端（`backend`）、接口（`api`）、数据（`data`）、权限（`authorization`）。
- 范围明确时，优先通过本地治理命令创建 Spec，例如：`super-dev spec propose <id> --title <标题> --description <描述> --changed-surfaces backend api --work-mode evolve --governance-depth architectural`。这里的已有项目增量迭代（`evolve`）和架构级治理（`architectural`）分别说明改动方式与检查强度。
- 修复明确缺陷时可使用：`super-dev spec propose <id> --title <标题> --description <描述> --changed-surfaces backend api --work-mode patch --governance-depth bounded`。缺陷修复（`patch`）和边界清楚（`bounded`）不会自动跳过阶段，只生成只读建议。
- 文档已经确认后，运行完整流水线的恢复或定向执行可使用：`super-dev pipeline <需求> --changed-surfaces backend api --governance-depth architectural`。
- 范围不确定时不要填写（`--changed-surfaces`）；系统必须保留完整九阶段建议，不能为了省步骤而猜测。
- 阶段范围建议（`scope_advisory`）只用于说明，缩减建议必须审批，不能自动修改真正阶段决定（`resolution`）或跳过确认步骤。

## 本地知识库契约（强制）

- 存在 `knowledge/` 时，research 与文档阶段优先读取相关知识文件。
- 存在 `output/knowledge-cache/*-knowledge-bundle.json` 时，先读取 local_knowledge / web_knowledge / research_summary。
- 命中的知识是项目约束（标准/检查清单/反模式/场景包/质量门禁），必须继承到 PRD、架构、UIUX、Spec 和实现阶段。
- 未经用户确认禁止创建 `.super-dev/changes/*` 或开始编码。
- 产物必须真实写入项目文件，不能只在聊天中口头描述。

## 方法吸纳：Forge、需求审查与 Grill with Docs

- 先读已有需求、决定和相关代码，复用已回答内容；这些方法没有固定先后，不增加阶段、用户命令或独立流程。
- 价值不清时，比较问题证据、替代方案、收益与维护成本，提出关键假设和可观察的低成本验证。商业、内部效率和学习目标分别评价；不编造证据，是否继续由用户决定。目标已明确时不重复立项论证。
- 需求审查只追问影响本轮的角色、主流程、异常、权限、范围和验收缺口，给出建议与依据。能从资料回答的先读取；关键歧义解决后即结束，其他未决事项记录影响和重启条件，不无限追问。
- 业务词义冲突时，对照文档和代码，用具体场景明确含义、作用域、别名与边界；不默认旧代码正确，不机械改名。优先复用项目权威词表，否则写入 PRD 术语表；不臆造定义或用通用技术缩写填充业务词表。
- 价值结论留在调研，需求和验收留在 PRD，词义只维护一个来源，技术取舍留在架构。只有难逆、需背景解释且有真实取舍的决定才写 ADR。方法切换不复制文档；变更已确认需求时仍遵守原确认合同。

### 在当前阶段完成方法闭环

- **Forge**：从用户目标判断是澄清、检验还是改进想法；归纳中心主张与事实/假设，先查资料，再针对最影响决定的问题给出建议与反方理由。每轮依据回答更新判断、备选方案和理由；信息推翻原假设时修正方案，不要重复已解决问题。结尾保留采用/放弃选项、依据、待验证项和下一步。
- **需求审查**：引用原需求编号或章节，逐项对照意图、角色、行为、边界、验收及已存在的设计/任务。发现项说明来源、影响与建议，区分关键缺口和可选优化。收到决定后定向更新原文，保留编号与无关内容；回读并逐项复核矛盾、验收与引用，不为补追溯而提前创建 Spec。
- **Grill with Docs**：先读词表、需求、架构和相关代码，只列本轮未决设计分支与依赖，先解决影响下游的决定。用具体场景讨论词义、业务规则、接口或重要取舍，给建议与代价；收到回答后更新相关分支与原权威文档，再用场景检查一致性。未修复的代码差异须留作待实现。
- **写入与交接**：只要求审查时给发现与拟修改内容；已有修改授权时定向写回并回读，不重复索要同一授权。暂停时记录已决定、未决影响与继续动作，恢复先读后接续。方法结论不能代替用户文档/预览确认，不重置当前阶段、不跳过质量与交付，不自动修改确认状态或扩大实施范围。
- 需要详细方法且项目中存在 `knowledge/product/product-discovery-and-prd-deep-dive.md` 时按需读取。文件不存在时使用以上自包含步骤，不要求用户安装第三方方法。

## 需求、验证与交接：吸收 UmaDev 的适用方法

- 需求写清前提/触发、主体与可观察结果，沿用原编号关联验收和已有设计。数值目标须有项目依据；表格与模板示例不是已确认需求或已通过证据。未进入 Spec 时不为填追溯表提前创建任务。
- 测试按风险选择层次、环境和范围，使用项目现有工具；验证可对应需求、缺陷、不变量或兼容合同。先确认环境可执行，区分计划、实际执行、跳过与失败，不因局部测试通过就宣称整个项目可发布。
- 单独核对测试与门禁差异：删除断言、新增跳过、修改快照或阈值须解释原因和保护范围。正式预期变化可以更新测试；不能把真实缺陷静音换绿，也不能见到测试变更就一概判为作弊。
- 评审发现附位置、触发条件、影响和证据；正确性、需求、契约、安全或数据问题可阻断，风格与额外功能归可选。缺资料说明未验证，独立性不足如实标为自检；报告生成成功不等于检查通过。既有质量阈值与确认门不变。
- 未决事项留在原文档，注明来源、影响、阻碍与重新处理条件。交接保留已定理由、改动文件、验证命令/环境/结果和下一步，引用原始证据；恢复先核对文件与状态，不复制第二套计划或记忆系统。
- 需要细节且文件存在时，按问题读取 `knowledge/testing/testing-strategy-deep-dive.md`、`knowledge/development/code-review-quality-complete.md` 或 `knowledge/architecture/adr-template-and-examples.md`；不存在则使用以上指导。

## 编码前门禁（Spec 确认后、编码开始前必须执行）

跳过任何一步都会导致大量返工：

### 第 1 步：技术栈预研（最关键）
- 读取项目依赖文件（package.json / requirements.txt / go.mod 等），找到主要依赖的精确版本号
- 用 WebFetch 查阅每个主要框架的官方文档：Getting Started、Migration Guide、API Reference
- **不确定 API 写法时，先查官方文档再写代码，永远不要猜**

### 第 2 步：读取项目配置
- `super-dev.yaml` 确认技术栈选择
- 框架配置文件、tsconfig.json、.env.example
- 已有代码目录结构

### 第 3 步：声明 UI 工具链
- 声明并确认图标库（Lucide/Heroicons/Tabler）和组件库已安装
- 不声明 = 不允许写 UI 代码

### 第 4 步：确认 API 契约和设计 token
- 读取 output/*-architecture.md 中的 API 定义
- 读取 output/*-uiux.md 中的设计 token

### 第 5 步：在宿主里建立页面结构与共享类型并验证构建
- 按 `output/*-architecture.md` 与 `output/*-uiux.md` 直接在宿主里生成/更新页面结构、组件实现参考与共享类型
- 运行宿主原生构建命令确认零错误后才开始写业务代码


## 会话连续性契约（强制）

- 若存在 `.super-dev/SESSION_BRIEF.md`，每次继续前必须先读取。
- 用户在确认门/返工门说"改/补充/确认/继续"等，属于流程内动作，不退回普通聊天。
- 修改后留在当前门里，总结变化并再次等待确认。
- UI 不满意 -> 先更新 `output/*-uiux.md`，再重做前端 + UI review。
- 架构不合理 -> 先更新 `output/*-architecture.md`，再调整 Spec/实现。
- 质量不达标 -> 先修复，重新执行 quality gate + proof-pack。
- 启用 policy 时不得默认建议降低治理强度。

## 实现闭环契约（强制）

- 每轮修改后先做最小 diff review 再汇报完成。
- 运行 build / type-check / test / runtime smoke。
- 新增代码必须接入真实调用链；未接入则删除，禁止留 unused code。
- 新增日志/告警/埋点必须验证会在真实路径触发。

## 编码阶段持续治理

读取 `.super-dev/pipeline-state.json` 了解当前在哪个阶段。
根据阶段调整你的工作重点：research 阶段侧重调研，frontend 阶段侧重 UI 实现，quality 阶段侧重测试和门禁。

每次进入新阶段时宣告: `Super Dev | [N/9] 阶段名 开始 | 主导专家: XXX`

### 每次写文件前自检
- [ ] "use client" 是否需要？（Next.js）
- [ ] 图标来自声明的图标库？（不是 emoji）
- [ ] 颜色来自设计 token？（不是硬编码 hex）
- [ ] import 路径正确？API 路径与架构文档一致？

### 每完成一个功能后
1. build 无错误 2. lint 无 error 3. 无控制台红色错误
4. 对比 output/*-uiux.md 视觉一致 5. 运行 validate-superdev.sh（如有）

## Required behavior

1. First reply: say Super Dev pipeline mode is active and the current phase is `research`.
2. Before the first reply, read `.super-dev/WORKFLOW.md` and `output/*-bootstrap.md` when present and treat them as the explicit bootstrap contract for this repository.
3. Read `knowledge/` and `output/knowledge-cache/*-knowledge-bundle.json` when present.
4. Use Codex native web/search/edit/terminal capabilities to produce:
   - `output/*-research.md`
   - `output/*-prd.md`
   - `output/*-architecture.md`
   - `output/*-uiux.md`
5. Write the required artifacts into the repository workspace. Chat-only summaries do not count as completion.
6. Stop after the three core documents and wait for explicit confirmation.
7. Only after confirmation, create `.super-dev/changes/*/proposal.md` and `.super-dev/changes/*/tasks.md`, then continue with frontend-first implementation.
8. If the user says the UI is unsatisfactory, requests a redesign, or says the page looks AI-generated, first update `output/*-uiux.md`, then redo the frontend, rerun frontend runtime and UI review, and only then continue.
9. If the user says the architecture is wrong or the technical plan must change, first update `output/*-architecture.md`, then realign Spec/tasks and implementation before continuing.
10. If the user says quality or security is not acceptable, first fix the issues, rerun the quality gate, refresh any delivery evidence the reports ask for, and only then continue.

## Never do this

- Never jump straight into coding after `super-dev:` or `super-dev：`.
- Never create Spec or implementation work before the documents are confirmed.
- 未经用户明确确认，禁止创建 `.super-dev/changes/*`。
- Use local `super-dev` CLI for governance actions only; keep research, drafting, coding, and debugging inside Codex.

## 宿主常犯错误速查（每次编码前扫一眼）

### 错误 1: 使用 emoji 作为图标
```tsx
// ❌ <button>🔍 搜索</button>
// ✅ import { Search } from 'lucide-react'
//    <button><Search size={16} /> 搜索</button>
```

### 错误 2: 紫色渐变 AI 模板
```tsx
// ❌ bg-gradient-to-r from-purple-500 to-pink-500
// ✅ 使用 output/*-uiux.md 定义的品牌色: bg-primary + text-heading-1
```

### 错误 3: 前后端 API 路径不一致
```
// ❌ 架构文档写 /api/users，后端实际是 /api/v1/users
// ✅ 编码前先确认 output/*-architecture.md 中的 API 路径
```

## 错误恢复策略

遇到错误时按以下优先级恢复：

**阶段 1 -- 便宜恢复（不丢失上下文）**
- Token 超限？注入"继续，不要回顾"然后重试
- 工具失败？注入错误详情 + 备选方案，继续
- 权限拒绝？说明允许什么，继续

**阶段 2 -- 上下文重建（可能丢失细节）**
- Prompt 过长？压缩旧上下文，保留最近内容
- 多次失败？丢弃非关键历史，只保留关键决策

**阶段 3 -- 暴露错误（无法恢复）**
- 提供: 什么失败了 + 为什么 + 下一步建议
- 回到终端重新运行 `super-dev` 校验宿主接入；若本地版本或注入面不一致，再执行 `super-dev update`

永远不要在尝试阶段 1-2 之前就暴露错误给用户。

## Agent Teams 协作（支持 Teams 功能的宿主）

如果宿主支持 Agent Teams（如 Claude Code 的 /teams），可以让多位 Super Dev 专家并行工作：

**研究阶段**: PM + ARCHITECT 并行调研
**文档阶段**: PRD / Architecture / UIUX 可并行起草
**编码阶段**: 前端 + 后端可并行开发（注意 API 契约对齐）
**质量阶段**: Security + QA + Performance 并行审查

使用 Teams 时的约束：
- 每个 teammate 必须声明自己的专家角色
- teammates 之间通过共享文件（output/*.md）传递上下文
- 修改同一文件前必须协调（避免冲突）
- 质量门禁结果必须等所有 teammates 完成后汇总

## Super Dev System Flow Contract

- SUPER_DEV_FLOW_CONTRACT_V1
- PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery
- DOC_CONFIRM_GATE: required
- PREVIEW_CONFIRM_GATE: required
- HOST_PARITY: required
