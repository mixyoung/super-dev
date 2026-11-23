# 外部参考知识库看板 (Reference Knowledge Wiki)

> **知识复利核心信条**：
> 本知识库践行 Karpathy 的 **LLM Wiki** 与学术界《Knowledge Compounding》（arXiv:2604.11243）理念——**外部调研与参考建库的目标不是“单次检索更快”，而是让每一次对外部项目（如 BMAD、Superpowers、oil-tone）的技术调研、优缺剖析与边界取舍，永久沉淀为团队在代码仓库中可继承、可审计、随 Git 持续演进的数字资产。**

---

## 1. 知识库三层架构 (Three-Tier Architecture)

知识库严格分为三大物理层，杜绝信息污染，方便 AI 快速提取的同时极致优化人类阅读体验：

```
docs/references/
├── raw_sources/            # 【事实层】不可变的外部原始资料剪藏 (轻量 Markdown，原汁原味快照)
├── reader_wiki/            # 【可读知识库】面向人类阅读的高可读性提炼库 (实体、方法与概念网络)
└── decisions/              # 【决策层】团队技术选型、吸收取舍与否定记录 (ADR: 采纳与坚决拒绝的边界)
```

---

## 2. 外部来源全景看板 (Master Dashboard)

以下为本项目完整登记的 **22 项外部参考来源与技术依据**（14 个主项目，8 项官方标准），已全部完成三层资产化整理：

| 来源 ID | 名称 | 类别 | 当前状态 | 固定基线 | 可读精读 (reader_wiki) | 决策与取舍 (decisions) | 原始剪藏 (raw) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REF-001** | [UmaDev](https://github.com/umacloud/umadev) | 知识库；开发框架 | 🟢 已参考·部分吸收 | `5852627` | [📖 实体精读](./reader_wiki/REF-001-umadev.md) | [⚖️ ADR 决策](./decisions/ADR-REF-001-umadev-soft-content-boundaries.md) | [📄 原始快照](./raw_sources/REF-001-umadev/README.md) |
| **REF-002** | [Superpowers](https://github.com/obra/superpowers) | 框架流程；技能 | 🟢 已参考·部分吸收 | `v6.4.2` | [📖 实体精读](./reader_wiki/REF-002-superpowers.md) | [⚖️ ADR 决策](./decisions/ADR-REF-002-superpowers-boundaries.md) | [📄 原始快照](./raw_sources/REF-002-superpowers/README.md) |
| **REF-003** | [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | 开发框架与流程 | 🟢 已参考·部分吸收 | `v6.12.0` | [📖 实体精读](./reader_wiki/REF-003-bmad.md) | [⚖️ ADR 决策](./decisions/ADR-REF-003-bmad-method-boundaries.md) | [📄 原始快照](./raw_sources/REF-003-bmad/README.md) |
| **REF-004** | [Agency Agents](https://github.com/msitarzewski/agency-agents) | 技能与角色库 | 🟢 已参考·部分吸收 | `6d29a9b` | [📖 实体精读](./reader_wiki/REF-004-agency-agents.md) | [⚖️ ADR 决策](./decisions/ADR-REF-004-agency-agents-contracts.md) | [📄 原始快照](./raw_sources/REF-004-agency-agents/README.md) |
| **REF-005** | [Matt Pocock Skills](https://github.com/mattpocock/skills) | 技能与角色库 | 🟢 已参考·部分吸收 | `v1.3.1` | [📖 实体精读](./reader_wiki/REF-005-matt-pocock-skills.md) | [⚖️ ADR 决策](./decisions/ADR-REF-005-matt-pocock-skills-boundaries.md) | [📄 原始快照](./raw_sources/REF-005-matt-pocock-skills/README.md) |
| **REF-006** | [gyuha/forge](https://github.com/gyuha/forge) | 开发框架与流程 | 🟡 已参考·待吸收 | `28354ac` | [📖 实体精读](./reader_wiki/REF-006-forge.md) | [⚖️ ADR 歧义消除](./decisions/ADR-REF-006-forge-disambiguation.md) | [📄 原始快照](./raw_sources/REF-006-forge/README.md) |
| **REF-007** | [Agent Skills](https://agentskills.io/) | 规范与技术文档 | 🔵 已参考·依据引用 | `69ef37e` | [📖 实体精读](./reader_wiki/REF-007-agent-skills.md) | [⚖️ 依据引用](./decisions/ADR-DOC-001-to-008-standards-basis.md) | [📄 原始快照](./raw_sources/REF-007-agent-skills/README.md) |
| **REF-008** | [GitHub Agentic Workflows](https://github.com/github/gh-aw) | 开发框架与流程 | 🟡 已参考·待吸收 | `00ab1b7` | [📖 实体精读](./reader_wiki/REF-008-gh-aw.md) | *保持观察/不导入* | [📄 原始快照](./raw_sources/REF-008-gh-aw/README.md) |
| **REF-009** | [SDLC Studio](https://github.com/DarrenBenson/sdlc-studio) | 开发框架与流程 | 🟡 已参考·待吸收 | `28682ce` | [📖 实体精读](./reader_wiki/REF-009-sdlc-studio.md) | *版本存在历史差异* | [📄 原始快照](./raw_sources/REF-009-sdlc-studio/README.md) |
| **REF-010** | [Agentic Workflow Skills](https://github.com/gtrabanco/agentic-workflow) | 技能与角色库 | 🟡 已参考·待吸收 | `af84fe8` | [📖 实体精读](./reader_wiki/REF-010-agentic-workflow.md) | *跨宿主观察* | [📄 原始快照](./raw_sources/REF-010-agentic-workflow/README.md) |
| **REF-011** | [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) | 宿主与运行平台 | 🟡 已参考·待吸收 | `rc.5` | [📖 实体精读](./reader_wiki/REF-011-deepseek-harness.md) | [⚖️ ADR 适配边界](./decisions/ADR-REF-011-deepseek-harness-adapter.md) | [📄 原始快照](./raw_sources/REF-011-deepseek-harness/README.md) |
| **REF-012** | [ZSL / Grill with Docs](https://superpowers.zsl.dev/skills/grill-with-docs/) | 技能与流程 | 🟢 已参考·部分吸收 | 2026-09-06 | [📖 实体精读](./reader_wiki/REF-012-grill-with-docs.md) | [⚖️ ADR 决策](./decisions/ADR-REF-012-grill-with-docs-absorption.md) | [📄 原始快照](./raw_sources/REF-012-grill-with-docs/README.md) |
| **REF-013** | skill-creator | 技能与角色库 | 🟢 已参考·部分吸收 | 身份待核实 | [📖 实体精读](./reader_wiki/REF-013-skill-creator.md) | [⚖️ ADR 盲测决议](./decisions/ADR-REF-013-skill-creator-identity-and-verification.md) | [📄 原始快照](./raw_sources/REF-013-skill-creator/README.md) |
| **REF-014** | [oil-tone](https://github.com/oil-oil/oil-tone) | 技能与角色库 | 🟢 已参考·部分吸收 | `39cbf92` | [📖 实体精读](./reader_wiki/REF-014-oil-tone.md) | [⚖️ ADR 决策](./decisions/ADR-REF-014-oil-tone-adoption.md) | [📄 原始快照](./raw_sources/REF-014-oil-tone/README.md) |
| **DOC-001 ~ DOC-008** | PostgreSQL, W3C APG, MCP, SLSA 等 | 规范与技术文档 | 🔵 已参考·依据引用 | 官方基线 | [📖 规范总览](./reader_wiki/DOC-standards.md) | [⚖️ 依据决议](./decisions/ADR-DOC-001-to-008-standards-basis.md) | [📄 原始依据](./raw_sources/DOC-standards/README.md) |

---

## 3. 六大工程方法论与全自动流水线注入机制 (Methods & Pipeline Injection)

拒绝“只停留在文档上”，也“绝不让用户当人肉调度员”。以下六大方法已作为底层规约深度固化在 Super Dev 的 9 阶段流水线与专家契约中，在各阶段全自动注入生效：

| 方法名称与精读链接 | 自动注入阶段与生效载体 | 核心工程法则与自动注入机制 |
| :--- | :--- | :--- |
| 📖 [全流程自然准确表达](./reader_wiki/methods/natural-precise-writing.md) | **全生命周期底色** (`knowledge_pusher.py`) | 自动向各阶段注入表达底线，杜绝 AI 腔与伪黑话，保护业务状态完整 |
| 📖 [系统化假设驱动调试](./reader_wiki/methods/systematic-debugging.md) | `backend` / `quality` (调试 Playbook) | 单元测试或构建报错时由 `toolkit.py` 自动加载，未亲眼见红严禁改源码 |
| 📖 [想法验证与需求反证](./reader_wiki/methods/forge-idea.md) | `research` / `docs` (PM 专家) | PM `thinking_framework` 强制反证，识别致命假设，在原编号处原地更新 |
| 📖 [极限需求盘问与回读](./reader_wiki/methods/grill-with-docs.md) | `docs` 冻结前 (架构师专家) | 架构师强制单选裁决，在 `DOC_CONFIRM_GATE` 前将结论原地写回文档 |
| 📖 [专家画像契约模型](./reader_wiki/methods/expert-persona-contracts.md) | 全阶段引擎调度 (`builtin/*.md`) | 物理锁定各专家的输入、输出、只读/写入权限红线与停止信号，绝不越权 |
| 📖 [隔离前向盲测验证](./reader_wiki/methods/blind-forward-verification.md) | `quality` 门禁与 CI 发布预检 | 独立沙箱与自动化确定性断言，杜绝模型事后自评与放水作弊 |

---

## 4. 关键技术取舍与否决经验 (`decisions/`)

最宝贵的知识资产是“**为什么拒绝（Negative Results & Boundaries）**”，防止后续团队成员或 AI 随意引入已被证实行不通的方案：

- ⚖️ [ADR-REF-001: UmaDev 吸收边界](./decisions/ADR-REF-001-umadev-soft-content-boundaries.md)：*采纳 EARS 与测试反作弊；拒绝 Rust 二进制与第二状态机。*
- ⚖️ [ADR-REF-002: Superpowers 流程边界](./decisions/ADR-REF-002-superpowers-boundaries.md)：*采纳假设调试与证据绑定；拒绝整套技能全量安装与过度仪式化。*
- ⚖️ [ADR-REF-003: BMAD Method 边界](./decisions/ADR-REF-003-bmad-method-boundaries.md)：*采纳 Forge Idea 反证思想；拒绝多 Agent 调度状态机。*
- ⚖️ [ADR-REF-004: Agency Agents 角色契约](./decisions/ADR-REF-004-agency-agents-contracts.md)：*将角色叙事重构为权限与输入输出契约；拒绝虚构人设。*
- ⚖️ [ADR-REF-005: Matt Pocock Skills 边界](./decisions/ADR-REF-005-matt-pocock-skills-boundaries.md)：*采纳按需条件引用与自动化复盘；理清来源归属。*
- ⚖️ [ADR-REF-006: gyuha/forge 歧义消除](./decisions/ADR-REF-006-forge-disambiguation.md)：*消除与 BMAD Forge 歧义；确认既有覆盖，保留不吸收决策。*
- ⚖️ [ADR-REF-011: DeepSeek Harness 适配边界](./decisions/ADR-REF-011-deepseek-harness-adapter.md)：*坚持在独立分支通过运行时验收后方可合并。*
- ⚖️ [ADR-REF-012: Grill with Docs 吸收决策](./decisions/ADR-REF-012-grill-with-docs-absorption.md)：*固化极端追问与写回闭环；严禁无边界过度推演。*
- ⚖️ [ADR-REF-013: skill-creator 盲测决议](./decisions/ADR-REF-013-skill-creator-identity-and-verification.md)：*采纳前向盲测；严守来源严谨性，不臆测厂商。*
- ⚖️ [ADR-REF-014: oil-tone 表达规范决策](./decisions/ADR-REF-014-oil-tone-adoption.md)：*采纳读者认知顺序；拒绝安装整套技能、拒绝正则打分阻断 CI。*
- ⚖️ [ADR-DOC-001~008: 官方工程依据采纳](./decisions/ADR-DOC-001-to-008-standards-basis.md)：*以 W3C、PostgreSQL、SLSA、MCP 等官方标准为审查基石。*

---

## 5. 维护与自进化指南

新增外部项目或复核新版本时，按以下四步操作：
1. **剪藏原件**：在 `raw_sources/REF-XXX/` 放入关键 Markdown/文本片段（只存轻量文本，不存大二进制）；
2. **编写精读**：在 `reader_wiki/REF-XXX.md` 编写包含 YAML Frontmatter 的可读性档案；
3. **沉淀决策**：在 `decisions/ADR-REF-XXX.md` 记录吸收内容与坚决拒绝的原因；
4. **Git 提交**：在当前工作树提交 Git commit，完成知识资产的永久沉淀。
