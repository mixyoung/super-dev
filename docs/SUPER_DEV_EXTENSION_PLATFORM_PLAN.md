# Super Dev 宿主内增强：方法、知识与可靠性交付路线

> 状态：用户已于 2026-09-05 授权按方法重合性复核建议调整路线；本文更新不等于后续功能已实现。
> 初始计划日期：2026-08-19；本次调整日期：2026-09-05
> 研究基线：`d06e640153bd83fc63ef716e1149cf2b2bbf02ed`（Super Dev v2.4.0）
> 本次代码基线：`main@26bb222db05d5cff4920d497d4ca071103b3ae65`
> 目标仓库：`mixyoung/super-dev`
> 上游仓库：`shangyankeji/super-dev`
> 本次范围：保留宿主内使用方式，消除方法重复与固定前置关系，明确唯一结论来源和验收目标
> 明确排除：版权、许可证与商标判断
> 2026-09-07 决定：程序化排错（原 Phase 2B）需求已撤回，见第 1.5 节；不是达标、完成或等待晋级。

## 1. 执行摘要

Super Dev 是运行在已有编程宿主中的研发方法、知识与交付检查体系。用户继续在当前宿主会话里提出需求、讨论、开发和验收；Super Dev 提供方法和检查标准，宿主使用自己的模型与工具执行。

吸收 BMAD、Grill with Docs、Superpowers 和 UmaDev 时，优先改进已有知识、专家手册、Skill 与文档模板。只有确定性检查或执行安全的真实缺口才进入本地程序；不把每一种思想都实现为扩展模块。

| 层次 | 当前定位 |
| --- | --- |
| 宿主会话 | 用户入口、需求理解、代码和工具执行、按需原生协作 |
| Super Dev 方法与知识 | 阶段指导、需求和术语澄清、排错与验证方法，按当前缺口使用 |
| Super Dev 本地工具 | 安装与同步、确定性检查、已有流程状态与证据处理 |
| 已有扩展内核 | 保留受控 Python 完成前验证，不继续扩建通用执行平台 |
| 影子台账 | 保留观察与策略试验，不接管真实阶段决定 |

核心决策：

1. 不修改 Super Dev 的标准九阶段主链，不新增另一个生命周期状态机。
2. Forge 补充调研中的价值判断，BMAD 需求审查与 Grill 补充需求、架构和领域澄清；按缺口使用，互不构成固定前置条件。
3. 外部方法不得拥有项目阶段、不得推进 Super Dev gate、不得创建第二份 workflow state。
4. 完成前验证保留为已实现的 Python 试点；其他项目使用原有构建、测试与运行验证工具，TDD 为任务级策略。
5. UmaDev 知识不整库同步，只把差异主题作为候选，回到一手来源验证后重建。
6. 当前先完成已有可靠性收尾，再落实小范围方法与知识升级；排错方法直接由宿主使用，不建设程序化排错扩展。
7. 每类结论维护一个权威位置；现有答案优先复用，只澄清影响本轮工作的关键歧义。
8. 下一轮首先验收价值判断、需求缺口识别和业务概念一致性，再改善排错与任务级 TDD 的使用方式。
9. 不因方法数量增加就建设注册中心、自动路由、独立控制台或角色调度程序；新增程序能力必须证明现有宿主与工具不足。

### 1.1 本次调整的效力与范围

第 5、8、13、14 节分别维护架构边界、方法合同、工作顺序和验收要求。原 Phase 编号仅用于历史追溯，不表示必须依次实现。第 3 节保留历史基线，第 20 节保留原独立评审原文，不得将历史结论当作本次调整的独立验收。

本次只调整路线、架构说明与来源清单；未改写 `completion-verification` 的确认、任务、指标或实现。当前可靠性收尾与后续方法升级不能混用证据。文档确认、预览确认和质量门禁仍按现有合同执行；选择内部方法不授予跳阶段权限。

架构落盘说明位于 `output/super-dev-method-absorption-architecture.md`，来源摘要位于 `output/super-dev-absorb-strengths.md`；二者是本地阅读入口，不另立规则真源。`output/` 沿用忽略规则，本文保留可独立评审、随 Git 管理的完整决定。

### 1.2 2026-09-06 首批方法落实

用户要求继续后，已在独立的 `super-dev-method-absorption` 范围落实价值判断、需求缺口与业务术语三项：更新现有产品知识、PM/架构师指导、PRD 生成模板和标准 Skill 唯一模板，并同步四份仓库内副本。未引入第三方方法安装、独立命令或阶段控制。

95 项定向自动检查通过；六个隔离上下文首答演练符合三个正例和无需介入对照。详见 [本批验证记录](../.super-dev/changes/super-dev-method-absorption/validation.md)。该结果不代表跨宿主真实项目验收或项目发布通过；大生成文件仍有与基线相同的格式和 16 项类型问题。当前 `completion-verification` 的验收状态未改写。

### 1.3 2026-09-06 多轮闭环补全

用户进一步要求择优吸纳、保留 Super Dev 好的流程与功能后，本范围补齐 Forge、需求审查和 Grill with Docs 的多轮核心过程：分别支持新信息修正与调研回写、原需求逐项审查与修订复核、设计依赖讨论与场景验证。完整方法指导在已有产品知识中，标准 Skill 保留自包含步骤。

100 项定向及原流程回归检查通过；三个隔离案例经过 4/3/4 轮实际交互，更新六份获授权原文档，保留所有案例流程状态、示例代码和非目标条款。[最新验证记录](../.super-dev/changes/super-dev-method-absorption/closure-validation.md) 保留具体结果与限制，不能用此替代真实项目或全仓发布验收。

### 1.4 2026-09-06 UmaDev 软内容首批吸纳

按用户后续授权，已固定 UmaDev 来源提交，择优吸收六类需求、验证、评审与交接思想，改写到现有知识、专家指导、PRD 模板和标准 Skill。源码只用于核对方法，不移植其运行程序和状态体系。具体来源、落点与不采纳项见 [软内容吸纳映射](UMADEV_SOFT_CONTENT_ADOPTION.md)。

本批 121 项自动检查及隔离案例完成，保留此前 Forge/需求审查/Grill 方法和原 Super Dev 流程；当前项目发布状态仍需原门禁实际证据，本批不作发布批准。

### 1.5 2026-09-07 撤回程序化排错需求

用户要求判断原 Phase 2B 是否必要，若无必要就删除。复核结论是当前没有独立立项依据，因此从当前需求和候选路线撤回，而非继续等待晋级。

- 现有宿主原生工具、系统化调试手册、RCA 指导和 Skill 已覆盖复现、单一假设、最小实验、根因修复及回归，没有证据表明必须另建自动排错程序。
- 新执行模块还会增加项目适配、权限、错误分类、重试及维护负担；当前优先解决完成前验证耗时、失效证据和安装更新一致性。
- 保留排错思想、任务级 TDD、现有受控验证及安全边界，不删除历史回放、人工裁决或失败记录。
- 历史 JSON 字段 `recommend_stage_2b` 仅作兼容，新汇总恒为 `false`。原数值条件继续作为 `benefit_criteria_met` 记录试点收益，公式和阈值不变，结果不触发新功能开发，也不代替发布门禁。
- 不因本次撤回把“耗时未达线”改成“通过”。未来若出现宿主与现有工具确实无法解决的缺口，按贡献准则单独提出新需求，不恢复按 Phase 编号自动推进的路线。

该决定覆盖旧四文档及 Spec 中关于 Phase 2B 立项的前瞻性要求；已发生的历史记录仍按其产生时的语义保留。

## 2. 用户问题与产品目标

目标用户是一人公司创始人，具备有限编程经验，但没有在成熟软件组织中形成完整的产品、架构、测试、发布和运营经验。

该用户需要的不是更多角色名称，而是一个能完成以下工作的教练系统：

- 说明当前为什么处于这个阶段；
- 指出当前必须做出的产品或风险决定；
- 给出推荐答案并解释代价；
- 识别用户不知道自己应该问的问题；
- 阻止缺少关键证据的阶段推进；
- 允许明确的暂停、放弃、返工和恢复；
- 将代码、测试、运行、部署和运营证据绑定到同一个候选；
- 保持一个生命周期所有者和一个生产写入者；
- 不要求用户记忆多套工具命令和状态文件。

### 2.1 成功定义

成功不是“安装了更多 Skill”，而是：

1. 用户从一个模糊想法开始，可以在系统教练下形成可执行且边界清晰的产品定义；
2. 系统始终能回答“当前在哪、为什么、缺什么、下一步是什么”；
3. 工程方法只在匹配的阶段和任务触发，不制造双流程；
4. 完成声明具备新鲜、可检查、绑定到当前候选的证据；
5. 一个小型商业形态产品能从想法走到可运行、可发布、可监控、可回滚；
6. 增强版在相同任务上的正确验收时间、返工率和人工认知负担优于原版。

### 2.2 非目标

- 不把所有 Superpowers Skills 默认启用；
- 不移植 UmaDev 的协调者、角色团队、DAG 或状态机；
- 不运行完整 BMAD 生命周期；
- 不让 Forge、Grill 或外部 Reviewer 直接推进 Super Dev 阶段；
- 不以知识文件数量、篇幅或形式评分作为事实正确性的证明；
- 不在第一阶段重写 Super Dev 核心编排器；
- 不自动修改用户全局 Skill、Hook、MCP、凭据或模型配置；
- 不在本计划评审中讨论版权与许可证。

## 3. 历史审计基线（2026-08-19 至 2026-08-22）

本节数字与缺陷记录仅对应当时的代码版本。是否修复及是否可发布，应查当前实现和当前证据，不能把历史失败数作为新的待办总数。

### 3.1 Git与仓库基线

```text
HEAD=d06e640153bd83fc63ef716e1149cf2b2bbf02ed
branch=main
origin=mixyoung/super-dev
upstream=shangyankeji/super-dev
origin/main...upstream/main=0/0
git_fsck=pass
worktree=clean
```

### 3.2 知识库基线

```text
knowledge_files=307
markdown_files=306
total_lines=119280
total_bytes=4397712
files_with_last_updated=64
files_with_version_metadata=20
files_with_reference_section=75
files_with_url=148
```

当前文件最后源码变更：

| 日期 | 文件数 |
| --- | ---: |
| 2026-03-07 | 51 |
| 2026-03-20 | 35 |
| 2026-03-29 | 220 |
| 2026-04-22 | 1 |

项目自带 `scripts/knowledge_scorer.py` 的运行结果：

| 结果 | 数量 | 占比 |
| --- | ---: | ---: |
| Keep | 92 | 30% |
| Improve | 122 | 40% |
| Discard | 92 | 30% |
| 平均分 | 64.7/100 | - |

评分器目前根据篇幅、代码块、标题、表格、清单、关键词等形式指标评分，不验证技术版本、事实正确性、来源有效性、实际可执行性或最后验证日期。因此 `quality_score` 不得再被描述为知识正确性证明。

已确认的知识问题样例：

- `knowledge/frontend/01-standards/nextjs-complete.md` 将 App Router 的引入描述为 Next.js 14+；官方历史显示 Next.js 13 引入、13.4 稳定。
- React 内容没有覆盖 React 19 的关键变化，而当前官方主版本为 React 19。
- OWASP Top 10 文档仍固定为 2021，未声明后续版本跟踪策略。

### 3.3 UmaDev知识差异基线

基于 Git Blob 的远程比较：

```text
super_dev_knowledge_blobs=307
umadev_knowledge_blobs=469
same_paths=307
identical_blobs=1
changed_shared_paths=306
umadev_new_paths=162
super_dev_only_paths=0
```

这证明 UmaDev 是 Super Dev 知识树的后继分支，但不能证明其内容全部正确。UmaDev 新增主题可作为 gap candidates，不作为可直接覆盖的权威源。

### 3.4 扩展面基线

已存在：

- `HookManager`：Pre/Post Phase、OnError、WorkflowEvent；
- `SkillManager`：从 Git 或本地目录复制外部 Skill；
- `workflow_stage_truth.py`：内部 engine phase 到 canonical stage 的映射；
- Hook历史、workflow event、release readiness审计面；
- 自定义Validation Checker注册能力。

已发现缺陷：

1. `HookType.PYTHON` 被模型声明，但配置执行器未实现；
2. Pre/Post Phase只直接覆盖内部 engine phases，未完整覆盖 `spec/frontend/preview_confirm/backend`；
3. WorkflowEvent只覆盖部分状态保存事件，不是完整阶段事件总线；
4. Command Hook使用 `shell=True` 字符串执行；
5. 外部Skill安装仅做浅克隆和复制，不记录commit、digest、来源、适用阶段、能力需求、冲突或写入权限；
6. Windows路径写入双引号YAML时会触发反斜杠转义问题；
7. 知识来源路径在Windows使用反斜杠，破坏跨平台身份比较；
8. Skill Manager测试会命中真实用户Skill目录，测试隔离不可靠；
9. Codex Skill入口仍使用当前通用校验器不接受的旧式或自定义frontmatter字段；Claude Code入口另有Hooks等宿主字段，缺少按宿主分别验证和安全迁移的契约。

### 3.5 Windows定向测试基线

审计运行了187项Hook、Knowledge、Skill、Workflow相关测试：

```text
passed=177
failed=10
warnings=12
```

失败类别：

- WorkflowEvent Hook的Windows YAML路径转义；
- Knowledge source path跨平台规范；
- Knowledge Gate索引完整性；
- Skill Manager用户目录隔离与镜像冲突。

任何外部能力接入前，相关失败必须清零。

2026-08-22复验再次证明该问题会产生真实副作用：`test_integration_manager.py`与`test_skill_manager.py`在Windows上忽略测试设置的HOME，触碰真实用户目录，累计204项通过、35项失败，并新建49个宿主接入文件。新建文件已移动到`.super-dev/recovery/20260822-1230-global-test-pollution/`，未永久删除；此后在Home路径依赖注入修复前禁止再次运行这两组完整测试。

## 4. 不可破坏的系统不变量

### 4.1 生命周期所有权

```text
LIFECYCLE_OWNER=SUPER_DEV
WORKFLOW_STATE=.super-dev/workflow-state.json
```

扩展只能：

- 在被允许的阶段执行一个有界方法；
- 输出结构化建议、文档、测试或验证结果；
- 通过Super Dev事件总线报告状态；
- 请求当前阶段保持、阻断或交回控制。

扩展不能：

- 创建自己的项目阶段；
- 修改Super Dev下一阶段；
-自称任务已完成；
- 创建第二份生命周期状态；
- 启动第二个完整Harness；
- 向用户全局环境静默安装能力；
- 绕过docs、preview、quality或release gate。

### 4.2 单一生产写入者

每个可变工作树任何时刻只允许一个生产写入者。评审者默认只读。扩展通过受控接口声明和检查写入范围；该机制不是操作系统级沙箱，不能据此宣称任意第三方代码无法越权。

### 4.3 同一生命周期内的分层编排

Super Dev作为最外层的完整开发流程（Harness）时，可以调用宿主已有的子代理（subagent）、Orca、OMP或其他已验证执行器并行完成互不依赖的工作，但这只是增加执行能力，不是再启动一套生命周期。

层级职责必须固定：

- Super Dev Core是唯一生命周期所有者，负责阶段、状态、门禁、整合和最终完成判断；
- 宿主或协调者负责拆分任务、安排工作区和收集结果，不重新定义产品流程；
- 执行者只完成被分配的范围，不能扩大权限、推进Super Dev阶段或直接合并生产主线；
- 只读评审者只返回问题和证据，不修改生产文件；
- 规则从外层向内层继承，范围和权限逐层缩小；产物、测试证据、风险和结果回执从内层向外层归并。

工作区安排权必须唯一。若当前执行者已经由Orca、Super Dev或上层代理放入指定工作区，则默认：

```text
WORKSPACE_PREASSIGNED=yes
MAY_CREATE_BRANCH=no
MAY_CREATE_WORKTREE=no
MAY_SPAWN_SUBWORKERS=no
```

只有任务契约明确转交安排权（`PLACEMENT_OWNER`）时，执行者才可继续创建分支、工作区或下一级执行者。任何可变工作区仍然只有一个写入者。并行任务必须在文件、外部副作用或时间依赖上互不干扰。

### 4.3.1 Super Dev Skill唯一源头

Super Dev只维护一个逻辑Skill。唯一可编辑源头是：

```text
super_dev/skills/skill_template.py
```

以下文件只是按宿主生成的发布副本，不得单独手写增强：

```text
.agents/skills/super-dev/SKILL.md
.claude/skills/super-dev/SKILL.md
plugins/super-dev-codex/skills/super-dev/SKILL.md
plugins/super-dev-claude/skills/super-dev/SKILL.md
用户安装目录中的super-dev/SKILL.md
```

`scripts/sync_super_dev_skills.py`负责生成或检查这些副本。Codex与Claude Code可以保留必要的宿主格式差异，但同一宿主的项目入口、插件入口和安装入口必须由同一模板得到；出现漂移时测试直接失败。

### 4.4 候选证据绑定

所有验证证据必须至少绑定：

```text
repository
base_sha
candidate_sha_or_diff_digest
dirty_state
task_id
acceptance_command
exit_code
timestamp
```

候选代码、测试或配置发生改变后，旧验收证据失效。

### 4.5 权限边界

安装、全局配置、提交、合并、推送、PR、部署、外部写入和清理保持独立授权。扩展Manifest不能授予这些权限。

### 4.6 失败诚实性

任何扩展必须返回：

```text
PASS
FAIL
BLOCKED
NOT_APPLICABLE
```

不得用“基本完成”“应该通过”代替可判定状态。

## 5. 目标架构

| 职责 | 承担者 | 边界 |
| --- | --- | --- |
| 对话、理解需求、实现和工具执行 | 当前宿主 | 使用现有模型、账户与原生能力 |
| 阶段定义、知识与验收要求 | Super Dev Skill、知识和模板 | 单一流程，按任务范围适配深度 |
| 当前状态、确认绑定和机器可判定检查 | Super Dev 既有本地工具 | 维护唯一流程记录，不启动第二个编程代理 |
| 产品取舍和关键风险接受 | 用户 | 宿主提供依据和建议，不替用户作商业决策 |
| 方法选择 | 宿主依据现有上下文 | 先读取已有答案，补当前缺口；无通用 Method Router 或 Preflight Router |

用户仍通过当前宿主支持的 Super Dev 入口及自然语言继续工作。九阶段名称与既有确认合同保持不变；价值判断、需求审查和术语澄清嵌入现有调研、文档、架构或返工环节；排错和 TDD 用于当前实现任务内部。

### 5.1 组件边界

| 既有位置 | 方法升级时的职责 |
| --- | --- |
| `super_dev/skills/skill_template.py` | 简短的选择、交互和停止规则；通过现有同步脚本生成宿主副本 |
| `knowledge/` 与专家手册 | 可复用方法、正反例和适用条件，按需加载 |
| `super_dev/creators/document_generator_content_mixin.py` | 改进现有澄清问题、需求章节和领域术语表，不复制第三方整套文档体系 |
| `super_dev/orchestrator/knowledge.py`、`knowledge_pusher.py` | 复用检索和阶段注入，不增加独立知识服务 |
| `super_dev/extensions/` | 保留来源锁、受控执行、路径与证据能力，当前只承担已批准的用途 |
| `super_dev/change_ledger.py`、`stage_policy.py` | 保留影子模型与策略试验，不把它们描述成已全面接管真实流程 |

详细方法只维护在对应知识或手册中，Skill 和模板引用其必要规则，不能全量复制。新能力先判断能否通过上述位置解决；确有确定性检查或安全执行缺口时，才设计最小程序改动。

暂停建设通用 registry/resolver、自动方法调度、独立模型会话管理、额外角色团队或知识覆盖平台；不为吸收 Forge、Grill、Debugging 或 TDD 自动增加 `builtins/*` 模块。既有辅助 Web 接口继续按缺陷维护，不扩展为新的主要开发入口。

## 6. Extension Manifest契约（原程序扩展候选设计）

本节保留历史候选设计供已有扩展机制审查，不是宿主方法指导的必需配置，也不代表当前解析器支持全部字段。现行配置以已批准的扩展规格和实际解析器为准；任何增加字段或能力的工作需另行限定范围。

原建议 Schema：

```yaml
schema_version: 1
id: verification-before-completion
version: 1.0.0
kind: engineering-method
source:
  repository: obra/superpowers
  commit: <exact-sha>
  content_digest: <sha256>
trigger:
  mode: explicit-or-policy
  allowed_stages: [frontend, backend, quality, delivery]
  conditions:
    - completion_claim_pending
capabilities:
  required: [read_files, run_commands]
  optional: [subagents]
host_compatibility:
  min_host_version: 2.4.0
ownership:
  lifecycle: false
  orchestration: false
  production_writer: false
writes:
  allowed:
    - output/verification/**
  forbidden:
    - .super-dev/workflow-state.json
    - .git/**
authority:
  commit: false
  push: false
  deploy: false
conflicts:
  - second-lifecycle-owner
timeout_seconds: 600
result_policy: core_decides
timeout_status: BLOCKED
evidence:
  schema: extension-result-v1
tests:
  behavior:
    - tests/extensions/verification/test_stale_claim.py
    - tests/extensions/verification/test_fresh_evidence.py
```

V1在解析Manifest前必须冻结最小能力词表及判定语义：

```text
read_files      宿主能读取明确路径并返回失败
run_commands    宿主能以结构化argv执行命令并返回exit/stdout/stderr
subagents       宿主能创建与生产写入者隔离的只读上下文
```

扩展只能返回建议状态，是否阻断、保持或推进阶段始终由 Super Dev Core 裁决。方法数量达到三个不构成建设 registry/resolver/probe 的理由；只有现有能力无法满足的具体需求和单独确认的范围，才能支持新增程序平台。

### 6.1 运行结果契约

```json
{
  "schema_version": 1,
  "extension_id": "verification-before-completion",
  "status": "PASS",
  "stage": "quality",
  "candidate_digest": "...",
  "commands": [
    {
      "command": "python -m pytest -q",
      "exit_code": 0,
      "stdout_digest": "...",
      "started_at": "...",
      "finished_at": "..."
    }
  ],
  "blocking_findings": [],
  "advisory_findings": [],
  "writes": ["output/verification/task-123.json"],
  "next_action": "return-control-to-super-dev"
}
```

## 7. Canonical阶段事件模型（原程序扩展候选设计）

以下是原计划的完整事件模型候选，尚未作为本次方法升级的实施要求。优先复用既有流程状态与事件；不为知识指导引入新事件总线、锁或状态迁移。

原候选事件：

```text
StageEntered
StageMethodRequested
StageMethodStarted
StageMethodCompleted
StageMethodBlocked
StageEvidenceInvalidated
StageGateWaiting
StageGateConfirmed
StageRevisionRequested
StageExited
WorkflowParked
WorkflowAbandoned
WorkflowCompleted
```

事件至少包含：

```text
workflow_id
run_id
canonical_stage
method_id
candidate_digest
actor
timestamp
source_artifacts
result_artifact
```

字段按事件类型区分必选与可选；例如`StageEntered`不要求candidate digest，只有产生或验证候选的事件才必须绑定。`candidate`统一定义为：

```text
base_sha
head_sha（已提交候选）或 dirty_diff_digest（未提交候选）
staged_digest
untracked_manifest
worktree_identity
```

如果未来批准扩展 `.super-dev/workflow-state.json`，须评估 `schema_version`、原子写、并发保护与降级读取；旧版本不得因新状态崩溃、误推进或丢弃记录。该候选不能在本次文档调整中被直接执行。已有扩展禁用后的历史证据继续保留，不取得 Core 路由权限。

### 7.1 状态语义

- `parked`：当前工作未完成，但已安全保存，允许后续恢复；
- `abandoned`：用户明确放弃本轮工作，不再要求完成所有后续阶段；
- `blocked`：缺少外部输入或权限，不能继续；
- `failed`：执行完成但未满足标准；
- `completed`：当前定义的交付范围与全部必需gate已通过。

必须提供明确的取消/放弃出口，避免“只要没有跑完整周期，状态机就永远不通过”的使用感。

## 8. 外部方法吸收与现有能力去重

BMAD 是方法体系，Forge Idea 是其中一种方法；Grill with Docs、Systematic Debugging 和 TDD 各解决特定问题。来源名称只用于追溯，不成为用户必须学习的新入口。

| 当前需求 | 现有基础 | 吸收的增量 | 所在环节 |
| --- | --- | --- | --- |
| 项目是否值得做 | 调研、PM 用户分析、产品价值方法 | 质疑关键假设、比较替代方案、低成本验证、允许暂缓 | 调研 |
| 需求是否足够清楚 | PRD、澄清问题、验收标准 | 找出关键遗漏和矛盾，区分事实、假设与未决事项 | 文档与确认 |
| 业务用词是否一致 | PRD 术语表、架构、现有代码 | 用真实场景辨析概念与边界，明确映射 | 需求、架构及相关返工 |
| 故障如何定位 | RCA 专家、系统化调试手册 | 把复现、单一假设和最小实验应用于当前问题 | 实现、联调、质量返工 |
| 代码是否满足预期 | 测试知识、TDD 说明与质量检查 | 对适用任务保留真实失败、修复通过和回归证据 | 当前实现任务 |

现有章节和知识并不证明上述交互已经可靠执行。例如默认 `_generate_glossary()` 输出 JWT、Session 等技术词；Spec-Code 一致性检查主要覆盖接口、配置、依赖和任务，不能据此判定业务术语已统一。

### 8.1 Forge Idea：澄清、检验与改进

价值判断是 Forge 的一种用途；完整采用过程包括归纳中心主张、选择关键问题、提出反方理由、依据回答修正方案、收敛并写回原调研。信息已足够或当前并不需要检验时，复用已有决定。具体操作维护在 [产品方法知识](../knowledge/product/product-discovery-and-prd-deep-dive.md)，不为它另建运行程序。

当项目价值或核心假设不清楚，或者用户要求质疑方案时，在现有调研中使用：

1. 识别用户、场景、问题以及已观察到的证据；
2. 比较人工流程、表格、现成软件和自主开发的收益与维护成本；
3. 找出一旦不成立就需要缩小、暂缓或停止的关键假设；
4. 提出能改变判断的低成本验证，包括可观察结果；
5. 给出值得推进、先验证、缩小范围或建议暂缓的结论，标明不确定性。

商业项目按客户与收益评价，内部工具按效率与错误成本评价，学习项目按学习目标评价。不把没有市场证据等同于没有价值，也不把讨论得更清楚等同于市场验证成功。

问题与下一步已足够明确时结束。用户决定继续、缩小或放弃；助手不依据自评分数自动终止项目。结论进入现有 `output/<slug>-research.md`，不默认生成另一套 Forge 报告、JSON 或生命周期状态。

### 8.2 需求与领域澄清：吸收 BMAD 和 Grill with Docs

需求审查沿原需求编号对照意图、行为、边界、验收以及已存在的设计/任务，收到决定后定向修订，再逐项复核。Grill 按当前未决设计分支的依赖讨论领域含义、业务规则、接口与重要取舍，回写原权威文档并用争议场景检查。两者共享已有答案，但不能把只列问题或只改术语当作完整闭环。

需求审查复用当前 PRD，检查关键角色、主流程、异常和权限边界、本轮范围、验收标准。能从代码和文档得到的答案先读取；只将影响本轮工作的关键缺口交给用户，给出有依据的建议。

Grill with Docs 用于术语冲突、业务边界或难逆取舍不清楚的情形，无需先完成 Forge。用具体场景对照需求、架构和代码，例如“取消订单是否必然退款，已发货与未发货是否允许同样操作”，避免仅列同义词或批量改名。

- 每个业务概念说明定义、适用范围、别名与易混淆概念；跨业务范围允许有说明的同词异义。
- 优先维护现有 PRD 术语表；需要跨文档共享时才抽成一份领域词表，原位置改为引用。
- 项目已有 `CONTEXT.md` 等权威词表时直接复用；不强制所有项目新增该文件，不维护两份冲突定义。
- 领域词表保存业务含义；技术实现取舍进入架构，只有难逆、需要背景解释且确有备选方案的决定才写 ADR。
- 文档和代码冲突时先辨析预期与事实，不默认旧代码正确或新表述正确；只调整已确认影响范围。
- 概念变更若影响已确认需求或架构，按原确认合同回到相关门；不因为一次方法切换重复确认。

当影响本轮实现的关键歧义已解决，其他未决事项有明确边界与重启条件时结束。深度逐问讨论只用于用户请求或重要冲突；普通实现细节由宿主在已授权范围内处理。

### 8.3 完成前验证：保留方法通用性与试点边界

完成声明应有对应当前代码和适用范围的实际验证：读取退出码与关键结果，绑定代码版本，代码或相关输入变化时使旧证据失效。测试通过不能替代价值判断、需求完整性或产品验收。

`completion-verification` 目前只实现显式启用的 Python/pytest 计划，且仅由 `super-dev release readiness` 触发。该试点与通用宿主方法指导是两层：其他语言项目由宿主运行其已有构建、测试及运行检查，不因使用 Super Dev 就要求配置 pytest。

不在本次调整中扩展执行程序白名单、增加自动修复、接受未经核验的宿主自报结果或引入第二执行入口。现有质量门禁、来源锁及证据合同继续执行。

### 8.4 系统化排错（Systematic Debugging）

优先改进现有 `knowledge/development/02-playbooks/debugging-playbook.md` 与 RCA 指导，由宿主应用方法，不新建排错服务。

出现故障、根因未知或连续猜修时：读取错误与近期变化，复现或收集足够现场证据，提出单一假设，做最小实验，记录结果，再修复根因并验证受影响路径。假设不成立就更新判断，不叠加猜测性改动。

简单问题采用简短证据；多次修复不收敛时重新检查边界和设计假设，不能仅凭次数宣称架构错误。只提出诊断时不自动修改生产代码；增加日志、外部遥测或扩大修复范围仍服从当前授权。

### 8.5 评审方法（Independent Review）

复用当前宿主可用的评审能力。评审输入包括明确差异、验收标准和相关合同；意见区分必须修正与可选建议，附可核验证据。

只有实际具备隔离上下文与只读权限的评审才能称为独立评审；同一执行者自检必须如实标注。方法指导不要求新增多代理编排、角色团队或独立评审产品，也不构成自动分派许可。

### 8.6 测试驱动开发（TDD）

复用现有测试知识，对行为已明确的业务规则、缺陷回归、状态转换或可隔离接口任务采用：先观察测试因目标行为缺失而失败，再写最小实现使其通过，最后重构并保持回归通过。

TDD 是当前任务的实现策略，不以评审或排错程序建成为前置，不设为全局强制。视觉探索、低风险配置和暂不可自动验证的集成使用适合任务的替代证据；不得为补做 TDD 删除已接受实现。

测试工具由项目技术栈决定；缺依赖导致无法启动不能算作有效的失败测试。即使不采用严格 TDD，也应以适当验证证明当前改动，不能靠减少断言、关闭检查或忽略失败取得通过。

### 8.7 结论唯一来源与方法交接

| 结论 | 唯一维护位置 | 其他位置如何使用 |
| --- | --- | --- |
| 价值、替代方案、关键假设与调研证据 | 当前调研文档 | PRD 引用相关结论 |
| 用户需求、范围与可验收结果 | 当前 PRD | Spec/tasks 引用需求和验收条目 |
| 业务概念 | PRD 术语表或其引用的唯一共享词表 | 架构、接口、UI 文案和测试引用定义与作用域 |
| 技术方案与难逆取舍 | 当前架构；必要时以 ADR 记录决定 | 架构引用 ADR，避免重复维护决定正文 |
| 未决事项 | 本问题所属文档或现有项目决策记录 | 任务与恢复简报只保留引用、影响和重启条件 |
| 实际验证结果 | 当前任务的原始证据及摘要 | 质量与交付报告引用同一运行证据 |

选择方法前检查已有答案；前一方法已经解决的问题不再重复询问。方法切换只携带相关事实、决定与未决项，不创建第二计划、第二确认记录或整套文件副本。有效讨论产生的正式变更仍遵守原文档与实现门禁。

### 8.8 首轮验收目标（已落实与初步演练，真实项目试用待补）

| 编号 | 输入场景 | 预期行为 | 不得出现 |
| --- | --- | --- | --- |
| V1 价值判断 | 提出昂贵功能，但问题可先由现有工具或小实验验证 | 指出关键假设、备选方案与不宜立即开发的依据，并提供具体验证；决定交给用户 | 迎合立项、编造市场证据或自动终止项目 |
| V2 需求缺口 | 已有 PRD 缺少关键角色权限或异常流程 | 引用已有内容，只追问影响本轮实现的缺口，形成可验收行为 | 重问已回答问题、生成泛化完整 PRD 或无限追问 |
| V3 概念一致性 | 文档允许部分取消，但代码只支持整单取消 | 用具体场景揭示冲突，区分取消与退款，明确范围并指向唯一词义来源 | 仅替换字词、偷偷更改业务语义或复制词表 |

每项同时包含一个无需介入的对照：目标明确的学习项目、需求完整的已确认改动、语义相同且映射明确的代码别名。对照场景应复用决定并继续原流程，不启动重复价值审查或强制统一标识符。

原始输入、宿主输出、用户决定与产物引用均须可复查；上述预期不是当前通过证据。后续再以真实故障和业务规则任务验证排错、TDD 的增量收益。

2026-09-06 的实际观察与自动检查已单独保存在第 1.2 节链接的验证记录中；本节表格保持验收标准身份，不以勾选或文本命中替代行为证据。

### 8.9 来源与适配依据

- [BMAD：探索与验证想法](https://docs.bmad-method.org/plan/explore-and-validate-an-idea/)：按问题选择想法澄清或验证，允许不同结果。
- [BMAD：选择规划路径](https://docs.bmad-method.org/plan/choose-a-planning-path/)：方法按意图缺口组合，避免固定串行。
- [ZSL：Grill with Docs](https://superpowers.zsl.dev/skills/grill-with-docs/)：对照文档和代码澄清领域概念，按需记录取舍。
- [Superpowers：Systematic Debugging](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md)：基于证据、单一假设与最小实验排错。
- [Superpowers：TDD](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md)：验证失败—通过—重构循环，适配为任务级方法。
- 已有基础：`knowledge/product/product-discovery-and-prd-deep-dive.md`、PM/RCA 专家手册、`knowledge/testing/01-standards/testing-strategy-complete.md` 和既有知识检索/注入代码。

以上来源已在本轮会话中核对；本文吸收方法而非整包规则。后续写入知识时仍需逐项核对内容、版本和适用范围，来源更新不自动改变 Super Dev 合同。

## 9. 知识新鲜度与正确性治理

2026-09-06 已固定 [项目演进与贡献准则](CONTRIBUTION_POLICY.md) 为本仓库准入与权限的权威说明，具体吸纳方法维护于 [知识维护策略](../knowledge/00-governance/maintenance-policy.md)。下文 Schema/周期是历史候选设计，不构成另一套现行规则；不要求因到期自动删除、按季度重组或建设知识评分平台。

### 9.1 新知识Schema

以下为元数据候选。首批方法知识优先兼容已有分类与检索，只增加实际需要的来源、适用范围和核验信息；不要求先实现整套 Schema、分数系统或知识运行平台。

```yaml
id: nextjs-app-router
title: Next.js App Router
domain: frontend
category: framework-contract
status: verified
applicability:
  package: next
  version_range: ">=13.4 <17"
source_refs:
  - url: https://nextjs.org/blog/next-13-4
    kind: official
    accessed_at: 2026-08-19
last_verified: 2026-08-19
review_due: 2026-11-19
structure_score: 80
freshness_status: current
execution_evidence:
  command: npm test
  fixture: tests/knowledge/nextjs-app-router
conflicts: []
```

### 9.2 分离评分维度

不得再用一个`quality_score`混合所有含义。至少分为：

- `structure_score`：格式和可检索性；
- `source_quality`：官方、一手、二手或无来源；
- `freshness_status`：current、review-due、stale、unknown；
- `semantic_review_status`：是否通过专业审查；
- `execution_status`：是否有可重复验证；
- `retrieval_effectiveness`：实际任务中的命中与采纳情况。

### 9.3 Freshness Gate

高漂移知识必须声明版本范围和复审周期：

- Web框架、SDK、云服务、AI模型/API：30-90天；
- 安全标准与合规：90天或上游变更触发；
- 稳定工程原则：180-365天；
- 历史案例：不要求更新，但必须标记历史语境。

过期知识默认降级为参考，不得作为硬约束进入PRD、Architecture、Spec或实现。

### 9.4 UmaDev知识导入过程

1. 对照当前上游与本地内容，先确认现有知识覆盖与缺口；历史新增主题数不能直接变成导入任务数。
2. 首批围绕价值判断、需求验收、业务术语选择小批量内容，随后按需求补充测试完整性、排错、幂等、授权与发布恢复。
3. 不把 UmaDev 文件自带分数当作事实权威；回到相应一手标准、框架文档或可执行实现核验。
4. 未核验内容保留为当前研究中的参考，不进入硬约束注入；不要为此先建设知识覆盖目录或运行平台。
5. 核验后优先更新已有 `knowledge/` 条目；确有缺口才新增，保留来源、适用条件与正反例。
6. 通过已有检索与阶段注入验证：相关任务可获得正确内容，不相关任务不被增加无用约束。
7. 记录来源路径、版本或提交与本地改写依据，供后续复核；不自动整库覆盖或同步上游变更。

## 10. Windows与跨平台硬化

### 10.1 Hook命令结构化

废弃面向扩展的`shell=True`字符串命令，改为argv：

```yaml
command:
  executable: python
  args: [scripts/check.py, --project, "${SUPER_DEV_PROJECT}"]
  shell: false
```

要求：

- Windows路径不写进双引号YAML命令字符串；
- 不经过shell拼接；
- 环境变量白名单注入；
- stdout/stderr有大小上限；
- 明确timeout和kill tree；
- 退出码语义统一；
- 不打印凭据；
- Hook运行目录固定为项目根；
- 记录实际argv而非展开后的秘密值。
- `${SUPER_DEV_PROJECT}`等插值只能由Core按白名单字段展开；Manifest不得提供任意表达式；
- `.cmd/.bat`默认禁止直接执行；确有需要时必须显式声明解释器，例如`cmd.exe /d /s /c npm.cmd ...`；
- Windows超时通过Job Object终止完整子进程树，Linux/macOS使用独立进程组；
- 旧YAML `type: python`先进入一版弃用期：检测、拒绝执行、给出迁移动作，下一主版本再删除。

### 10.2 路径身份

所有证据和Manifest内部路径统一为仓库相对POSIX路径：

```text
knowledge/security/policy.md
```

展示和内容比较优先使用规范化相对路径；本地执行仍使用实际路径。当前验证摘要有意包含工作区身份，不承诺同一提交在不同机器上可以直接复用运行证据。跨平台可运行性与证据可搬运性应分别验证。

写入守卫不得只做字符串前缀判断。比较前必须：

- 解析`..`和符号链接/junction；
- 获得真实目标路径；
- Windows执行casefold；
- 验证目标仍位于允许根目录；
- 对不存在的新文件验证其最近存在父目录的真实路径；
- 覆盖大小写变体、junction出仓、UNC路径和短文件名绕过测试。

### 10.3 测试隔离

Skill Manager测试必须显式注入所有Home路径，禁止调用`Path.home()`或真实`USERPROFILE`作为隐藏fallback。

测试结束后验证：

- 用户Skill目录无变化；
- 全局配置无变化；
- 仓库无未跟踪文件；
- 临时目录已清理；
- 失败不会删除已有用户Skill。

## 11. 教练体验契约

在需要用户作重要决定或恢复中断工作时，提供简短、可展开的说明。普通执行回合根据实际进展沟通，不强制每轮重复阶段卡。必要说明包括：

```text
现在需要决定什么
当前证据缺口
系统推荐与主要反方代价
继续/暂停/放弃/返工入口
```

“当前阶段、为什么、本阶段通过条件、完整证据和下一步”等细节按需要提供。恢复说明引用已有决定、暂停原因、未决事项和第一个可执行动作，不复制第二套决策记录。

### 11.1 母语与环境适配

- 默认使用Skill使用者的母语、文字习惯和熟悉程度；面向消费者的产品文案还要服从目标用户语言，不因内部工具使用英语就强迫用户理解英语；
- 先用通俗词解释作用，再在第一次出现时把必要专用词放入括号，例如：完整开发流程（Harness）、隔离工作区（worktree）、唯一写入者（single writer）；后续优先使用已经解释过的通俗说法；
- 编程语言专用词、代码名和字段使用“中文含义（`LITERAL_NAME`）”，例如：任务编号（`TASK_ID`）、安排负责人（`PLACEMENT_OWNER`）；命令和代码继续使用代码格式，保证可以复制；
- 自动适配实际操作系统、Shell、路径形式、仓库约定、已安装运行环境和无障碍需要；Windows环境不得默认给出只能在Bash执行的命令；
- 普通进度说明避免堆叠缩写、内部状态名和工具品牌。要求用户决定前，先说明这个机制做什么、影响什么以及不决定的代价。

### 11.2 教练行为

- 先解释风险，再要求用户决定；
- 技术问题能从仓库和工具发现时不反问用户；
- 产品、预算、风险接受和发布决定必须由用户确认；
- 不用角色表演替代真实分析；
- 不用大量文档掩盖未验证事实；
- 给推荐答案，但明确它是建议而非事实；
- 用户不知道术语时提供短解释和实例；
- 一个回合只要求用户承担当前最关键的决定；
- 阻断时给出可执行恢复动作；
- 允许安全地结束部分成果，不强迫每次走完全周期。
- 重要决定的理解明显有歧义时说明后果；不能仅因用户回答简短就增加测验或重复确认；
- 同一门禁连续三轮不收敛时，提供缩小范围、降级目标、park或abandon选项；
- park/abandon必须生成短摘要：已证事实、否决理由、残余风险和可复用资产。

### 11.3 用户成熟度模式

```text
guided       解释充分、主动推荐；低风险确认合并批量处理
balanced     只解释重要取舍、默认建议可快速接受
expert       输出契约与证据，减少教学文本
```

用户模式只改变解释深度，不改变质量和权限底线。

## 12. 商业交付契约

“商业级”必须落到可检查证据，不能只靠文档数量或质量分。

证据默认由系统起草并收集，用户只确认产品取舍、预算、风险接受和发布决定。每项证据必须标注责任：`system-generated/user-confirmed`、`user-authored`或`external-evidence`，不得把约40项清单转嫁给非专业创始人手工填写。

### 12.1 产品证据

- 目标用户、买方和使用者区分；
- 问题、价值假设、替代方案；
- MVP范围和非目标；
- 功能需求与可执行验收标准；
- 成功指标和失败指标；
- 未决问题登记。

### 12.2 架构与数据证据

- 系统边界和依赖；
- 数据模型和所有权；
- API与错误契约；
- 权限与授权规则；
- 幂等、并发、事务和重试；
- 数据迁移、备份和恢复；
- 技术选择的版本与来源。

### 12.3 UI/UX证据

- 主路径与异常路径；
- loading、empty、error、permission、offline等状态；
- 可访问性和响应式；
- 设计Token与组件状态；
- 真实浏览器或目标设备预览；
- 用户确认绑定到当前候选。

### 12.4 工程质量证据

- 构建、lint、typecheck；
- 单元、集成、契约和E2E；
- 测试完整性检查；
- 安全、秘密、依赖和权限检查；
- 性能预算；
- Spec-Code一致性；
- 独立只读评审；
- 候选diff和Git状态。

### 12.5 发布与运营证据

以下按项目是否部署服务、持有数据及其风险适用；离线 CLI、文档调整和学习项目不自动承担完整 SaaS 运维清单。

- 环境与配置清单；
- 部署脚本或明确操作步骤；
- 数据迁移计划；
- 回滚演练；
- 健康检查；
- 日志、指标、告警和SLO；
- 备份与恢复验证；
- 故障和支持入口；
- 发布批准。

## 13. 当前开发顺序与历史阶段映射

### 13.1 当前顺序

本次用户授权的是按上述建议调整路线与架构；以下工作顺序不代表全部实现已启动，也不改变当前活动变更或已有验收记录。

| 顺序 | 工作 | 完成依据 |
| --- | --- | --- |
| 本次 | 对齐路线、架构与来源清单 | 固定前置和重复产物设计已修订，文档引用与边界一致 |
| 当前收尾 | 完成已有可靠性问题与质量/交付检查 | 对当前代码和环境分类处理失败；原始测试、CI 与报告一致，不能沿用失效证据 |
| 下一轮方法升级 | 价值判断、需求缺口、业务概念三个目标 | 第 8.8 节正例与无需介入对照均有真实宿主记录 |
| 配套知识升级 | 小批量补充方法与领域知识 | 复用既有分类和检索；来源、适用范围、正反例可核验 |
| 后续方法改进 | 系统化排错、任务级 TDD、适用的只读评审 | 当前任务中行为改善，未增加固定阶段或独立调度 |
| 扩大试用 | 小缺陷、已有项目增量、小型新项目 | 漏项、返工、提问负担和恢复效果可比较；使用方式保持宿主内完成 |

方法升级首先利用既有 PM/RCA 手册、知识库、Skill 唯一模板与文档模板。知识和方法不必先包装成可执行扩展。程序新增仅针对有实证的检查、安全或证据处理缺口，限定范围后再实施。

### 13.2 当前可靠性收尾

- 以当前仓库、Python、操作系统和依赖为证据建立可重复环境，区分产品缺陷、测试缺陷与环境缺口。
- 处理已发现的 Windows 路径、用户目录隔离和相应测试覆盖问题；CI 应如实反映已声明的支持范围。
- 完成前验证、质量和发布报告分别核验；同一测试范围的普通 pytest 运行不能冒充已走过完整受控验证入口。
- 保留有效的安全边界、Skill 同步与当前变更隔离；不因方法指导调整就移除已验证机制。
- 当前变更的完成由其已有任务与本次真实证据决定，不根据本文的历史阶段数量或勾选总数推算百分比。

### 13.3 原 Phase 编号的解释

| 原编号 | 保留用途 | 本次调整后的关系 |
| --- | --- | --- |
| Phase 0：基线 | 历史失败分类与可重复验证 | 修复或复测前查当前事实，不重新执行已经完成的历史工作 |
| Phase 1：最小扩展与 Windows | 已有受控执行、路径、来源与证据能力 | 保留并按缺陷维护，不要求继续做完整扩展平台 |
| Phase 2：完成前验证 | 当前 Python/pytest 单点试验 | 继续其已有合同与真实指标，和通用方法指导分开 |
| Phase 3：评审/TDD | 评审纪律与测试先行方法来源 | 先用宿主与项目现有能力；TDD 指导不依赖独立评审程序建成 |
| Phase 4：Forge/Grill | 价值、需求与领域澄清方法来源 | 按第 8 节使用，Forge 与 Grill 无固定先后，不新增主流程阶段 |
| Phase 5：知识刷新 | UmaDev 差异与一手来源研究 | 提前按小批量配合三个方法目标，不以知识覆盖运行平台为前置 |
| Phase 6：真实项目验证 | 验证方法是否改善交付 | 先做可比较的小场景，再按项目风险扩大，不将 SaaS 全套要求套给所有项目 |
| Phase 7：维护与发布 | 上游同步、兼容性与渐进试用 | 持续维护；不得把自动全局安装或新的独立开发入口作为完成条件 |

原 Phase 2B 程序化排错条目已撤回，不再列为候选工作。其他新增程序能力须有独立需求与批准，不能由宿主依据编号自动推进。试点收益的数值公式、历史结果和真实候选标签保持；任何效果结论都须绑定实际观测。

### 13.4 后续实施前的范围检查

每个改动应回答：

1. 它解决用户开发中的哪个具体问题，现有实现与知识缺在哪里？
2. 能否先通过已有知识、Skill、专家手册或模板解决？
3. 若必须写程序，现有宿主或本地工具为何不足？
4. 用什么真实场景证明收益，并观察新增的交互和维护成本？

只有“平台更完整”、文件更多或测试行数增加，不能支持立项。每次实现应限定改动面、保留既有项目差异，并记录可复查的行为结果；这里的范围检查不增加用户日常命令或独立审批系统。

## 14. 测试策略

### 14.1 单元测试

以下只针对涉及的程序改动。知识和交互指导的调整首先检验实际行为，不以新增同义断言或凑测试行数作为交付。

- Manifest解析；
- 阶段匹配；
- 所有权和写入范围；
- capability probe；
- evidence digest；
- freshness计算；
- source path规范；
- state迁移；
- Hook argv编码。

### 14.2 行为测试

首轮按第 8.8 节执行 V1、V2、V3，以及各自的无需介入对照；保留输入、原文输出、决定与产物引用。用同一批代表性场景比较调整前后行为，不能伪造调整前失败或用方法关键词命中代替真实判断。

重点检查：

- 对已明确的学习目标、内部效率目标不过度施加盈利要求；
- 能找出本轮关键需求缺口，且不重复询问已有答案；
- 能识别取消/退款等概念冲突，同时接受不同上下文的明确映射；
- 结论只更新一个权威位置，其余文档引用；
- 没有新用户命令、额外状态机、固定方法前置或无意义的确认轮次。

后续排错、TDD 与评审改进按具体任务验证；程序扩展仍另行检查下列行为：

- 虚假完成声明；
- 猜修循环；
- Reviewer被执行者叙事影响；
- TDD跳过RED；
- 模糊想法直接编码；
- 术语冲突未解决；
- 过期知识作为硬约束注入。

### 14.3 集成测试

- Host Skill触发；
- Canonical事件；
- Docs/Preview/Quality Gate；
- Windows/Linux路径；
- 扩展超时和取消；
- 恢复、放弃和重启；
- 多扩展顺序；
- 无能力宿主降级。

### 14.4 安全和副作用测试

- 命令注入；
- 路径逃逸；
- 符号链接；
- 凭据泄露；
- 真实用户目录污染；
- 未授权Git/网络/部署操作；
- 扩展写workflow state；
- 外部Skill覆盖已有Skill。

### 14.5 验收顺序

1. 文档调整：审查差异、旧规则冲突、唯一来源、链接、状态表述和工作区改动范围。
2. 方法与知识调整：第 8.8 节正例及无需介入对照、真实宿主记录、检索/引用检查；若涉及模板，运行现有受控副本同步检查。
3. 程序调整：受影响单元/集成检查与必要回归，再运行对应质量、发布和证据验证；测试命令服从项目技术栈。
4. 跨平台声明：只有实际运行过的操作系统和宿主范围可以标记为已验证；存在某个平台代码分支不能代替平台验收。
5. 扩大试用：比较小缺陷、增量功能和小型新项目的漏项、返工、人工决定、耗时与恢复效果，再决定是否扩大使用。

当前文档调整不触发整套 pytest，也不改变 `completion-verification` 中独立登记的验证计划和晋级指标。

## 15. 迁移与兼容策略

### 15.1 状态兼容

- 老项目没有`extensions`字段时视为全部关闭；
- 新事件字段必须向后兼容；
- workflow-state读取旧Schema时不得自动推进阶段；
- 迁移前保存快照；
- 迁移失败继续使用旧状态并报告阻断。

### 15.2 配置兼容

下面是原扩展配置候选示例，不是当前支持配置的完整定义。方法指导不要求用户填写这些字段；当前程序配置以已确认规格和实际解析器为准。

```yaml
extensions:
  enabled: false
  profile: guided
  methods: {}
  knowledge_overlays: []
```

默认关闭保证原版行为。只有显式项目配置才能启用实验扩展。

### 15.3 知识兼容

- 原`knowledge/`保持可读；
- 新元数据缺失时标记`freshness_status=unknown`；
- unknown知识不自动升级为硬约束；
- 新overlay优先级不能仅由自报`quality_score`决定。

## 16. 主要风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 扩展平台变成第二Harness | 双状态、重复规划 | 生命周期不变量、Manifest拒绝state owner |
| 外部Skill自动触发过多 | 上下文膨胀、行为冲突 | 默认关闭、阶段+条件双门 |
| TDD教条化 | 现有代码返工、原型变慢 | 任务级opt-in和例外 |
| Forge/Grill重复提问 | 用户疲劳 | 按缺口使用、复用已有答案、明确停止条件，无固定先后 |
| 方法吸收全部程序化 | 使用与维护负担增长 | 优先已有知识/模板，新增程序须证明实际缺口 |
| 术语与决定重复存储 | 文档互相矛盾 | 每类结论一个来源，其他产物引用 |
| UmaDev知识整库污染 | 检索稀释、错误硬约束 | quarantine、回源验证、黄金查询 |
| Windows Hook失败 | 扩展不可用 | argv、路径规范、Windows CI |
| Skill测试污染用户目录 | 用户配置损坏 | Home依赖注入、临时目录断言 |
| 完成验证过重 | 小任务延迟 | 风险分级、最小充分证据 |
| Coach输出过长 | 用户无法决策 | Coach Card、一次一个关键决定 |
| 商业级变成文档级 | 代码和上线未闭环 | 运行、部署、监控、回滚证据 |
| 上游难同步 | fork停滞 | 核心最小改动、扩展目录隔离 |

## 17. 已确认边界与后续决定

用户于 2026-09-05 明确要求“按建议调整”。该授权覆盖本次方法去重、路线与架构文档调整，不需要再次询问相同定位问题。

已确认：保持宿主内使用方式；按缺口使用方法；方法指导与程序扩展分开；每类结论只有一个来源；优先三个方法验收目标；保留现有安全与确认边界。

后续新增可执行扩展、影子台账晋级、独立服务、全局安装或扩大的业务实现仍需明确范围。已有任务中得到的具体授权继续有效；不得因本节重建一套审批或重复请求已作出的用户决定。

## 18. Claude Code独立评审要求

评审者必须保持只读，不修改本文档或仓库。忽略版权、许可证和商标，只审以下四个维度。

### 18.1 合理性

- 问题诊断是否成立；
- 是否有逻辑跳跃；
- 是否错误推断工具能力；
- 是否存在不必要的复杂度；
- 所有权和边界是否自洽；
- 顺序是否符合依赖关系。

### 18.2 工程化

- 模块边界是否可实现；
- 状态、Hook、事件、路径、能力和权限模型是否完整；
- Windows问题是否被正确处理；
- 测试与回滚是否充分；
- 是否可持续同步上游；
- 是否出现隐性全局副作用。

### 18.3 教练性

- 是否真正帮助流程经验不足的一人创始人；
- 是否解释为什么、要求决定什么、怎样过关；
- 是否允许暂停、放弃、返工和恢复；
- 是否避免角色表演和文档堆积；
- 是否控制认知负担。

### 18.4 商业交付

- 是否覆盖产品、架构、UX、测试、安全、数据、部署、监控和回滚；
- 是否把“流程结束”和“产品可交付”区分开；
- 验收证据是否绑定真实候选；
- 是否存在会放过半成品的缺口；
- 黄金项目是否足以证明商业交付能力。

### 18.5 输出格式

```text
VERDICT=ACCEPT|REVISE|REJECT

BLOCKERS
- [severity] section: finding -> required change

IMPORTANT
- section: finding -> recommended change

STRENGTHS
- evidence-backed strength

FOUR-DIMENSION SCORE
- Reasonableness: x/10
- Engineering: x/10
- Coaching: x/10
- Commercial Delivery: x/10

RECOMMENDED PHASE ORDER
1. ...

MINIMUM ACCEPTABLE V1
- ...
```

## 19. 最小交付边界

当前程序版本收尾、方法行为验证和商业项目验证分别判断，不能把长期平台愿景全部计作当前未完成任务。

### 19.1 当前程序版本收尾

以现行 `completion-verification` 规格、当前代码与真实证据为准。重点是已有 Windows/环境问题分类与修复、适用 CI、当前验证与质量/发布证据的一致性、原入口兼容和受控写入。旧失败数量和扩展候选 Schema 不是新的必做清单。

方法升级的最小边界是第 8.8 节的三个目标及无需介入对照，不要求同时完成程序化排错、自动角色调度、通用注册中心或知识覆盖平台。

### 19.2 商业验证里程碑

只有进入相应商业项目验证时，才按项目实际范围要求：

1. 单个0→1项目的部署、监控、备份和回滚实证；
2. 沙箱支付完整回调闭环；
3. 钱、权限、数据和外部写入的负面测试；
4. CI产物摘要与部署物digest一致；
5. 1名非专业创始人完成试运行并通过理解探针；
6. 正确验收时间不恶化，虚假完成为0，`FALSE_BLOCKS`增幅不超过10%。

V1不包含：

- UmaDev知识大规模导入；
- 完整Superpowers生命周期；
- BMAD角色或Sprint系统；
- 多Harness并行；
- 自动全局安装；
- 默认强制TDD。
- Systematic Debugging、Independent Review、Forge、Grill 的独立执行扩展及知识覆盖运行平台。已有方法和知识指导的改进按第 8、13 节办理，不受此项排除。

## 20. 独立评审执行记录

本节保留 2026-08 的历史评审原文。后续的方法顺序、产物位置和程序边界已按 2026-09-05 用户授权在第 5、8、13 节修订；历史意见不构成本轮独立验收，也不恢复已取消的固定前置。

完整综合评审已并入本节，不再维护第二份独立评审文档。

### 20.1 评审约束

计划要求由 Claude Code 工具在以下边界内完成独立评审；底层模型使用用户已经配置的可用大模型，不要求Anthropic官方模型：

- `--safe-mode`，禁用项目和用户自定义CLAUDE.md、Skills、Hooks、MCP与插件；
- `--permission-mode plan`；
- 只读工具，或直接把文档正文作为输入且禁用全部工具；
- 使用用户当前配置中能够稳定完成请求的大模型；
- 不创建、编辑、删除、暂存、提交或推送文件；
- 忽略版权、许可证、商标和其他法律问题；
- 只审合理性、工程化、教练性和商业交付。

### 20.2 已执行尝试

| 尝试 | 输入方式 | 请求模型 | 结果 |
| --- | --- | --- | --- |
| 1 | Claude Code读取计划与仓库，只读Read/Glob/Grep | `opus` | 进程长时间无正文，模型目录报告多条`unrecognized_model` |
| 2 | 无工具、固定文本最小探针 | `opus` | 返回固定文本后连接中断，无法建立稳定评审通道 |
| 3 | 中立目录、无工具探针 | 默认模型 | 无稳定回复，仍报告未识别的第三方模型 |
| 4 | 文档正文流式输入、固定会话名、无持久化 | `opus` | 实际流模型为`grok-4.6-build`并连续空响应重试 |
| 5 | 显式完整官方模型ID与临时settings覆盖 | `claude-opus-4-20250514` | Claude Code init仍显示`grok-4.6[1M]`，参数无法覆盖当前路由 |
| 6 | 用户确认切换后重新运行固定探针 | `opus` | 用户settings仍将Opus映射到`grok-4.6[1M]`，实际响应仍为`grok-4.6-build` |
| 7 | 排除user setting source，仅使用临时空环境 | Claude Code解析为`claude-opus-5` | Claude模型路由正确，但无可用官方登录会话，返回`Not logged in` |
| 8 | 将现有Token仅注入当前进程、移除自定义Base URL | `claude-opus-5` | 现有Token不能用于官方Claude端点，返回401；Token未打印、未持久化 |
| 9 | 按用户澄清，接受Claude Code工具内的当前配置模型，完整只读评审 | `grok-4.6[1M]` | 能开始生成，但几十个思考token后连接关闭并进入空响应重试 |
| 10 | 直接指定配置中有历史记录的模型 | `claude-opus-4-8[1m]` | Claude Code正确识别模型，网关连续返回502 |
| 11 | 直接指定另一配置模型 | `claude-sonnet-4-6` | Claude Code正确识别模型，网关连续返回502 |
| 12 | 直接指定当前settings中的基础模型 | `deepseek-v4-flash[1M]` | 短探针60秒内没有正文，无法形成完整结果 |
| 13 | 按合理性/工程化/教练性/商业交付拆分，首轮仅381行摘录、700字上限、低推理 | `grok-4.6[1M]` | 60秒仍无正文，证明失败与完整文档长度和输出规模无关 |
| 14 | 用户更换供应商后重试Claude Code固定探针 | 请求`claude-opus-4-8[1M]`，供应端实际`glm-5.3` | 每次仅返回`RE`后关闭message并触发重试，无法完成固定文本 |
| 15 | 对同一Base URL、Token、模型做非流式Anthropic Messages最小诊断 | 请求`claude-opus-4-8[1M]`，响应`glm-5.3` | HTTP成功，完整返回`REVIEW_READY`、`stop_reason=end_turn`；模型和认证正常，故障限定在SSE流式兼容层 |
| 16 | 2026-08-22再次更换供应商并做Claude Code探针 | 请求`claude-opus-4-8[1M]`，供应端实际`stealth/ox-alpha` | 供应商原始SSE完整，但Claude Code兼容路径未正确取得最终text |
| 17 | 临时本机非流式转标准SSE兼容层，固定探针 | 同上 | Claude Code完整返回`REVIEW_READY`、`end_turn`、exit code 0 |
| 18 | 完整文档单次评审 | 同上 | 第一轮受Plan Mode影响只宣布准备检查；第二轮供应端计算超过300秒，不计入评审 |
| 19 | 按合理性、工程化、教练性、商业交付分成四轮小输入 | 同上 | 四轮均完整返回，分数分别为7/6/7/6 |
| 20 | 将四轮结果交给Claude Code去重汇总 | 同上 | 完整返回`VERDICT=REVISE`、统一阻断项、阶段顺序、最小V1和实验清单 |

尝试7和8源于“必须使用Anthropic官方Claude模型”的错误前提；用户已明确纠正为“使用Claude Code工具及其已配置大模型即可”。这两项只作为诊断历史保留，不再构成评审通过条件。

只读诊断同时确认：

```text
claude_code_version=2.1.233
auth_logged_in=true
auth_method=oauth_token
api_provider=firstParty
explicit_anthropic_env_override=none
requested_model=claude-opus-4-20250514
effective_runtime_model=grok-4.6[1M]
effective_response_model=grok-4.6-build
isolated_runtime_model=claude-opus-5
isolated_official_auth=missing_or_invalid
configured_grok_status=stream_disconnect_and_retry
configured_claude_models_status=http_502
configured_deepseek_status=no_complete_response
segmented_review_status=no_response_with_small_excerpt
new_supplier_non_stream_status=pass
new_supplier_streaming_status=truncated_after_two_chars
new_supplier_root_cause=anthropic_sse_compatibility
review_shim_probe=pass
segmented_reasonableness=7/10
segmented_engineering=6/10
segmented_coaching=7/10
segmented_commercial=6/10
review_synthesis=complete
```

### 20.3 当前结论

```text
CLAUDE_REVIEW_STATUS=COMPLETE
REVIEW_VERDICT=REVISE
REVIEW_MODEL_REQUEST=claude-opus-4-8[1M]
REVIEW_MODEL_RESPONSE=stealth/ox-alpha
PLAN_MUTATION_BY_REVIEWER=none
GLOBAL_CONFIG_MUTATION=none
```

四轮独立输出和综合汇总均完整结束；没有把零散思考token或部分文本计为评审。用户已明确授权Claude Code使用其配置模型，模型品牌不是通过条件。

### 20.4 综合评审结论

Claude Code认可的核心方向：

- 唯一生命周期所有者、单一生产写入者、候选证据绑定和失败四态；
- Forge/Grill留在research内，TDD显式启用；
- 先清零基线失败，再接外部能力；
- 知识使用quarantine→verified而非整库覆盖；
- 默认关闭和禁用扩展等价原版的可证伪验收。

Claude Code要求修订的阻断面已经反映到正文：

1. 首版平台从八个模块收缩为`manifest+executor+evidence+ownership`及单一Verification调用点；
2. 先冻结最小能力词表、事件字段矩阵和状态Schema，再解析Manifest；
3. 修复Windows命令、路径绕过、进程树和Skill测试隔离；
4. 证据逐项标明由系统起草还是用户确认，避免把约40项清单交给创始人；
5. Coach Card默认折叠，增加理解探针、恢复简报和门禁不收敛降级；
6. 指标增加原版基线、采集机制、观察窗口和阈值；
7. 商业验证增加沙箱支付、真实用户、CI产物绑定、部署、监控、备份和回滚工程工作项；
8. 工程V1与商业验证里程碑分离。

### 20.5 合并后的详细评审结论

```text
VERDICT=REVISE
Reasonableness=7/10
Engineering=6/10
Coaching=7/10
Commercial Delivery=6/10
```

#### 阻断项

Critical：

1. 平台范围过大：首版收缩为最小Manifest、Executor、Evidence、Ownership和单一Verification调用点；registry、resolver与probe延后。
2. Windows执行层未就绪：先清零现有失败，替换`shell=True`字符串执行，补齐解释器、变量插值和进程树清理规则。
3. 写入守卫可被大小写、符号链接（symlink）、目录连接（junction）、`..`和UNC路径绕过，必须解析真实路径并加入负面测试。
4. 证据责任未分配：逐项标明系统起草、用户确认、用户撰写或外部证据，不能把清单转嫁给非专业创始人。
5. 指标缺采集机制、阈值、观察窗口和原版对照，必须先冻结基线再判断增强是否有效。
6. 商业交付阶段缺少CI产物、部署、健康检查、告警、备份恢复与回滚演练等真实工程工作。

High：

1. 引导模式存在用户无脑采纳风险，需要理解探针和最强反方代价。
2. 支付模拟和作者自测不足，至少需要沙箱支付完整回调和一名非专业创始人试运行。
3. `parked/abandoned`等状态需要Schema版本、降级读取和旧版本兼容测试。
4. 伪Python Hook先检测、拒绝执行并提供弃用迁移期。
5. `read_files/run_commands/subagents`等能力必须有可判定含义。
6. Idea Forge与Grill首版由用户显式选择，自动路由延后。

#### 重要修改建议

- 扩展只返回结构化建议，保持、阻断或推进由Core裁决；
- 超时或崩溃返回`BLOCKED`并提供总关闭开关；
- UmaDev首批知识候选限制在十项以内并逐条回源；
- 事件字段按类型区分必选和可选；
- Manifest增加最低宿主版本（`min_host_version`）并定义内容摘要校验时机；
- 候选身份包含基础版本、当前版本、未提交差异和工作区身份；
- 工作流状态使用锁和原子写入；
- 每个实施阶段都要有回滚方案；
- 教练卡片（Coach Card）默认只显示当前决定、证据缺口、建议和操作入口；
- 恢复首屏显示上次决定、暂停原因、未决事项和第一个安全动作；
- 同一检查点不收敛时提供缩小范围、降级、暂停或放弃；
- 黄金项目补齐关键失败路径、密钥管理、数据导出删除、部署物摘要和上线后观察窗口。

#### 必需实验

1. 陈旧完成声明必须被新验证判为失败或阻断，虚假完成数为零；
2. 压力测试中只有Core能写工作流状态，扩展越界数为零；
3. Forge或Grill必须降低文档确认返工且不增加正式阶段；
4. 关闭扩展后，黄金项目除时间戳外与原版行为一致；
5. 大小写、junction、`..`和UNC绕过全部拒绝；
6. 扩展超时后没有存活的子孙进程；
7. 旧版本读取新状态不崩溃、不误推进并给出升级提示；
8. 理解探针正确率不低于80%，误阻断不高于5%；
9. 折叠式Coach Card降低人工时间且不降低阶段理解；
10. 恢复简报提高恢复成功率并降低首个决定错误率；
11. 部署物、备份恢复、钱和权限负面测试全部通过；
12. 非专业创始人能解释各检查点并亲自做发布决定。
