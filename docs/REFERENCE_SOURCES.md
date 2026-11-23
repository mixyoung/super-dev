# 参考项目、知识库与技能来源登记

> 维护用途：长期记录外部参考来源、历史核对基线和本地采用边界，不作为产品规则或运行时配置。
> 建档日期：2026-11-22；仓库基线：`26b0cb6c98e723b8c12c4d721785a9cb91d6f761`。
> 首次建档仅整理已有证据，没有联网检查上游当前 HEAD、安装第三方技能或新增知识吸纳；后续新增来源及实际查看范围见更新台账。

## 1. 范围与读法

本分支维护**一张参考总表**：所有已登记来源，无论已参考、待参考还是已部分吸收，都留在第 2 节，不在多个名单之间搬移。一来源一行；同一项目可以有多个类别标签。技能子清单只解释具体方法，不另算来源。

**术语统一：待参考来源**指新发现、尚未实际研究的外部项目、知识库、技能库、规范或平台。新增来源在总表中单独登记一行，状态为“待参考”；不是在已有项目中登记一个尚未研究的内容点。已有来源的后续研究方向、版本复核或未吸收内容只记在“参考方向与备注”，不计作新的待参考来源。

### 1.1 五类参考项

| 类别 | 收录范围 | 例子 |
| --- | --- | --- |
| 开发框架与流程 | 需求、规划、交付、评审、维护等流程或方法体系 | BMAD、Superpowers、Forge、SDLC Studio |
| 知识库 | 可按主题检索和择优吸收的领域知识、模板与案例集合 | UmaDev 知识树 |
| 技能与角色库 | 独立技能、技能集合、角色定义与技能编写方法 | Matt Pocock Skills、Agency Agents、skill-creator |
| 规范与技术文档 | 技能格式、协议、标准及官方工程技术依据 | Agent Skills、PostgreSQL、W3C APG |
| 宿主与运行平台 | 宿主集成、能力边界、运行机制、回放与权限隔离 | DeepSeek Harness |

类别说明“它是什么”，状态说明“我们做到哪一步”，两者不能混用。相邻产品按其参考对象归类，不另设重复类别。

### 1.2 状态与日期

- **待参考**：新发现并已登记的参考来源，尚未实际阅读或核对；吸收内容和日期填“—”。已有来源新增版本或出现未研究内容，不因此改回“待参考”。
- **已参考·待吸收**：有阅读/研究证据，尚无明确落地记录；下一步可以继续研究或决定不采用，不视为承诺吸收。
- **已参考·部分吸收**：已有明确内容落地，只指记录的部分，不代表整库导入或发布就绪；该来源的后续研究方向仍填在“参考方向与备注”栏，不作为新来源。
- **已参考·依据引用**：用作技术或格式依据，不等于安装依赖，也不自动算产品吸收。
- **暂缓 / 不采用**：保留项目及原因，不删除历史记录；情况变化时可以重新评估。
- **待核实**：额外标记身份、日期或采用范围不足，不猜测同名项目身份。

**吸收日期**记录内容实际落地的日期。历史证据只有记录日期或验证日期时，明确标注其口径；缺证据填“待核实”，未吸收填“—”。不以建档日、上游发布日期、来源核对日或 Git 文件修改时间替代吸收日期。

同一来源分批吸收，在内容及日期两栏用相同的批次标识配对追加（如 A1、A2），不得只留“最近吸收日期”而覆盖旧批次。每批链接包含实际落点与验证的原采用记录；详细差异追加至[更新台账](<REFERENCE_UPDATES.md>)。

历史版本是当时的观察，不是截至建档日的最新版。**来源核对日期、吸收日期、建档日期和后续联网核对日期必须分开。** 本表不计算“追平率”或“吸纳覆盖率”，登记候选不授予执行或吸收权限。

## 2. 参考总表（已参考与待参考统一维护）

总表现有 14 个主来源和 8 项官方技术依据，共 22 个登记项；**不是 22 个开源项目**。其中原有 21 项有历史参考证据，REF-014 已于 2026-11-22 实际研究并局部吸收，当前新来源“待参考”为 0 项；这不表示所有来源均已吸收。新发现的待参考来源追加在这里，编号不复用，不能用已有来源的未研究内容充数。“参考方向与备注”说明各来源的关注点或后续复核事项，不代表新增来源，也不代表已授权吸收。

| ID | 来源 | 类别 | 状态 | 参考方向与备注 | 已吸收内容（按批次追加） | 吸收日期（与批次配对） | 历史核对基线 | 证据 / 落点入口 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REF-001 | [UmaDev](https://github.com/umacloud/umadev) | 知识库；开发框架与流程 | 已参考·部分吸收 | 未评估知识条目；核实仓库名称差异，不整库照搬 | A1：U1–U6，需求表达、追溯、风险测试、测试完整性、证据评审、未决项与交接。<br>A2：U7–U14，调试、规格上下文、回归、评测、接口兼容、运行模型分离、UI 状态、资源与恢复。<br>A3：当前请求作为权限来源、证据优先与安全收敛，用于框架边界加固，不引入执行器。 | A1：2026-09-06（落地记录日期）。<br>A2：2026-09-06（第二批落实记录日期）。<br>A3：2026-09-14（实施记录日期）。 | 2026-09-12 研究沿用 `585262706174ad4a958cd054f0948509e84ad610`；v1.1.1 发布提交不同 | [A1/A2 来源与实际落点](<UMADEV_SOFT_CONTENT_ADOPTION.md>)；[后续框架记录](<../.super-dev/changes/framework-maintenance-2026-09-12/adoption.md>) |
| REF-002 | [Superpowers](https://github.com/obra/superpowers) | 开发框架与流程；技能与角色库 | 已参考·部分吸收 | 对比后续相关技能差异，不引入第二套流程 | A1：可验证工作方法与技能边界，用于框架合同加固；原记录未将所有改动逐项唯一归因给本来源。<br>A2：作为目标/知识补丁的方法来源，参与真实最终提示验证、按需引用及条件一致性修正，非整套技能安装。 | A1：2026-09-14（实施记录日期；09-16 后续收口）。<br>A2：2026-10-05（实施验证记录），10-06 返工验证。 | 2026-10-05：v6.4.2；2026-09-12：v6.3.0 / `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` | [目标与知识补丁记录](<../.super-dev/changes/target-knowledge-patches-2026-10-05/adoption.md>)；[框架记录](<../.super-dev/changes/framework-maintenance-2026-09-12/adoption.md>) |
| REF-003 | [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) | 开发框架与流程 | 已参考·部分吸收 | 想法验证、规划路径的后续差异；不导入团队或状态机 | A1：Forge Idea 价值判断与需求审查，包含反证、新信息修正、原需求编号核对、定向修订及回读。<br>A2：角色职责与阶段交接表达，不导入团队或状态机。<br>A3：列为目标/知识补丁的共同方法来源，不将补丁各项唯一归因于 BMAD。 | A1：2026-09-06（实施验证日期）。<br>A2：2026-09-14（实施记录日期）。<br>A3：2026-10-05（实施验证记录），10-06 返工验证。 | 2026-10-05：v6.12.0；2026-09-12：`94b6727b00c8316557828c8a8ff2a48ff60d60cc` / v6.12.0 | [框架记录](<../.super-dev/changes/framework-maintenance-2026-09-12/adoption.md>)；[方法来源](<SUPER_DEV_EXTENSION_PLATFORM_PLAN.md#L612-L621>) |
| REF-004 | [Agency Agents](https://github.com/msitarzewski/agency-agents) | 技能与角色库 | 已参考·部分吸收 | 角色指导的适用性与后续差异；不整包导入或虚构履历 | A1：角色画像结构，专家画像由履历叙事改为可测试的输入输出、权限、停止与交接契约 | A1：2026-09-14（实施记录日期；09-16 后续收口）。 | 2026-09-12：`6d29a9b08785a0e49ffc9818bbdd381164c2df5f` | [框架吸纳记录](<../.super-dev/changes/framework-maintenance-2026-09-12/adoption.md>) |
| REF-005 | [Matt Pocock Skills](https://github.com/mattpocock/skills) | 技能与角色库 | 已参考·部分吸收 | 文档、复盘与交互技能差异；核实 Grill 来源关系 | A1：v1.3.1 的 Writing for Agents / Retro 段落作为目标/知识补丁方法来源，参与真实提示验证、按需指导与条件修正；原记录不足以将每项补丁唯一归因于 Matt。不把 ZSL 的 Grill 采用日期算入本来源。 | A1：2026-10-05（共同方法来源对应的实施验证记录），10-06 返工验证；更早独立吸收日期待核实。 | 2026-10-05：v1.3.1；2026-09-12：`3cca18b368ae95cdbdebbff572ccafa662551015` | [目标与知识补丁记录](<../.super-dev/changes/target-knowledge-patches-2026-10-05/adoption.md>)；历史段落索引见第 5 节 |
| REF-006 | [gyuha/forge](https://github.com/gyuha/forge) | 开发框架与流程 | 已参考·待吸收 | 计划—执行—复盘—封存与项目角色；判断本地是否已有覆盖 | —；未找到明确落地记录，不引入其状态机或 Hook | — | 2026-09-12：`28354ac0dcfa596d654631eeac5128d695503f4e` | 历史研究摘要见第 5 节；不是 REF-003 的 Forge Idea |
| REF-007 | [Agent Skills](https://github.com/agentskills/agentskills) / [规范站](https://agentskills.io/specification) | 规范与技术文档 | 已参考·依据引用 | 元数据、渐进加载；P2 拆分仍待评估 | —；已有规范引用，不据此认定 P2 拆分已落地 | — | 2026-09-12：`69ef37e9424c0a7ea9dd2293b559e43ec8176379`；规范站未固定修订号 | [框架记录](<../.super-dev/changes/framework-maintenance-2026-09-12/adoption.md>) |
| REF-008 | [GitHub Agentic Workflows](https://github.com/github/gh-aw) | 开发框架与流程 | 已参考·待吸收 | 安全输出、周期性维护的适用性；不意味着启用定时任务 | —；未找到明确落地记录 | — | 2026-09-12：`00ab1b7e6a3ac62629c03e5eb0ce31e10bc18fbb` | 历史研究摘要见第 5 节；[原批次后置边界](<../.super-dev/changes/framework-maintenance-2026-09-12/adoption.md#L34>) |
| REF-009 | [SDLC Studio](https://github.com/DarrenBenson/sdlc-studio) | 开发框架与流程 | 已参考·待吸收 | 非技术创始人的角色合同与证据体系；核实正式发布状态 | —；未找到明确落地记录 | — | 2026-09-12：`28682ce24df2432f80f03df2f9f0d2b494cbc419`；主线自报 5.0.1、Releases 缓存 v4.1.0，不能认定 5.0.1 已发布 | 历史研究摘要见第 5 节 |
| REF-010 | [Agentic Workflow Skills](https://github.com/gtrabanco/agentic-workflow) | 技能与角色库；开发框架与流程 | 已参考·待吸收 | 跨宿主、渐进加载、文档真源；核对是否有未覆盖价值 | —；未导入完整流程，也无明确局部落地证据 | — | 2026-09-12：`af84fe869ae6f1f79451908d0542875cbd302517` | 历史研究摘要见第 5 节 |
| REF-011 | [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) | 宿主与运行平台 | 已参考·待吸收 | 运行回放、能力可关闭；宿主适配另按明确任务验收 | —；存在研究与其他工作项，不算本分支已交付 | — | 2026-11-05 研究沿用 2026-11-04 固定对照：`dsh-v0.2.1-rc.5` / `b830ec950faba0a46dda564be3e2d854afed94f1`；后续设计另有冻结版本，非当前安装版本声明 | 历史研究摘要见第 5 节；不变更桌面工作项 |
| REF-012 | [ZSL / Grill with Docs](https://superpowers.zsl.dev/skills/grill-with-docs/) | 技能与角色库；开发框架与流程 | 已参考·部分吸收；来源关系待核实 | 核实与 REF-005 的关系、文档修订身份 | A1：按设计依赖讨论词义、业务规则、接口及重要取舍；决定写回原文档并用争议场景回读；进入知识、PM/ARCHITECT、PRD 模板和标准 Skill。 | A1：2026-09-06（实施验证日期）。 | 2026-09-06 方法说明；未固定提交或文档修订号 | [正式方法来源](<SUPER_DEV_EXTENSION_PLATFORM_PLAN.md#L612-L621>)；不能只因同名合并来源 |
| REF-013 | skill-creator（身份未确认） | 技能与角色库 | 已参考·部分吸收；身份待核实 | 补发布者、官方 URL、版本；不猜厂商 | A1：隔离前向验证，按轮提供案例信息并实际修改/回读文档，不预先提供答案。<br>A2：技能分层组织与适用范围指导，配合格式校验；来源身份仍未知。 | A1：2026-09-06（验证方法采用记录日期）。<br>A2：2026-09-11（指导维护记录日期）。 | 历史整理有使用记录；URL、版本、commit 均未记录 | [知识与技能吸纳记录](<../.super-dev/changes/knowledge-expert-guidance/adoption.md>) |
| DOC-001 | [PostgreSQL 18 CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html) | 规范与技术文档 | 已参考·依据引用 | 按数据库目标版本复核索引成本与 CONCURRENTLY 的限制 | —；已有技术依据引用，未单列产品吸收批次 | — | PostgreSQL 18；2026-09-11 整理记录，非吸收日 | [整理记录](<reviews/knowledge-expert-guidance-2026-09-11.md#L72-L77>) |
| DOC-002 | [W3C APG 可访问名称](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) | 规范与技术文档 | 已参考·依据引用 | 原生语义、标签与可访问名称；按具体 UI 场景复核 | —；已有技术依据引用，未单列产品吸收批次 | — | 2026-09-11 整理记录；未固定文档修订号 | [整理记录](<reviews/knowledge-expert-guidance-2026-09-11.md#L72-L77>) |
| DOC-003 | [OpenAI 插件文档](https://developers.openai.com/plugins/build/plugins) | 规范与技术文档 | 已参考·依据引用 | 清单、分发与来源锁定；实际采用前重核接口 | —；仅登记历史设计参考 | — | 2026-08-25 最小扩展研究；未固定修订号 | 历史研究摘要见第 5 节 |
| DOC-004 | [MCP 工具注解说明](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/) | 规范与技术文档 | 已参考·依据引用 | 注解与权限执行的区别，不把风险自述当权限保证 | —；仅登记历史设计参考 | — | 2026-08-25 最小扩展研究；文章 URL 标识 2026-03-16 | 历史研究摘要见第 5 节 |
| DOC-005 | [Python subprocess](https://docs.python.org/3/library/subprocess.html) | 规范与技术文档 | 已参考·依据引用 | 结构化参数与 Shell 边界；补具体 Python 文档版本 | —；仅登记历史设计参考 | — | 2026-08-25 最小扩展研究；未记录 Python 文档快照 | 历史研究摘要见第 5 节 |
| DOC-006 | [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) | 规范与技术文档 | 已参考·依据引用 | 子进程组与超时清理；按实际 Windows 环境复核 | —；仅登记历史设计参考 | — | 2026-08-25 最小扩展研究；未固定修订号 | 历史研究摘要见第 5 节 |
| DOC-007 | [SLSA v1.2 provenance](https://slsa.dev/spec/v1.2/provenance) | 规范与技术文档 | 已参考·依据引用 | 来源证明与内容摘要绑定的适用范围 | —；仅登记历史设计参考 | — | 2026-08-25 最小扩展研究；v1.2 | 历史研究摘要见第 5 节 |
| DOC-008 | [JSON Schema object](https://json-schema.org/understanding-json-schema/reference/object) | 规范与技术文档 | 已参考·依据引用 | 必填字段与额外字段约束；补草案版本 | —；仅登记历史设计参考 | — | 2026-08-25 最小扩展研究；未记录草案版本 | 历史研究摘要见第 5 节 |
| REF-014 | [oil-oil/oil-tone](https://github.com/oil-oil/oil-tone) | 技能与角色库 | 已参考·部分吸收 | 自然、准确、易读的文档/产品表达；不套用作者身份或个人口吻，不安装整套技能。后续按实际写作缺口评估，不引入禁词评分或新门禁。 | A1：读者前置信息与信息顺序、句意关系和业务状态完整、不机械删改“的/了”、事实边界与连续回读；落入现有产品知识，UX 短引用，保留适用条件。 | A1：2026-11-22（本地实施日期，非上游提交日）。 | 2026-11-22 固定 `39cbf92f76c90b7bb27a5b5d4ed88a1fc5fa31f6`；读取 README、技能正文、检查脚本、界面元数据及 MIT 许可；脚本只读不执行 | [最初登记](<REFERENCE_UPDATES.md#oil-tone-registration>)；[A1 研究与落点验证](<../.super-dev/changes/oil-tone-adoption-2026-11-22/adoption.md>)；[本批台账](<REFERENCE_UPDATES.md#oil-tone-adoption-a1>) |

### 吸收日期的原始证据与限制

- 2026-09-06：BMAD / ZSL 的[方法落实和实际落点](<../.super-dev/changes/super-dev-method-absorption/closure-validation.md#L3-L10>)、skill-creator 的[隔离前向验证](<../.super-dev/changes/super-dev-method-absorption/closure-validation.md#L20-L30>)；不能将 ZSL 的采用日期转记给 Matt。
- 2026-09-11：skill-creator 的[分层与适用范围指导](<../.super-dev/changes/knowledge-expert-guidance/adoption.md#L3-L17>)及[格式校验](<reviews/knowledge-expert-guidance-2026-09-11.md#L91-L92>)。来源身份仍缺证据，采用过方法不等于身份已确认。
- 2026-09-14：[框架批次日期、固定来源与取舍](<../.super-dev/changes/framework-maintenance-2026-09-12/adoption.md#L3-L28>)支持 Superpowers、BMAD、Agency Agents、UmaDev 的本批记录。吸纳记录追加了 09-16 收口，而[验证记录末段](<../.super-dev/changes/framework-maintenance-2026-09-12/validation.md#L69-L75>)仍保留旧中间状态；不抹平时间层次，不由此声明本分支可发布。
- 2026-10-05 / 06：[目标与知识补丁实施及验证](<../.super-dev/changes/target-knowledge-patches-2026-10-05/adoption.md#L19-L67>)列出 Superpowers、BMAD、Matt 作为共同方法来源，但未逐项证明唯一归属。这里只登记该批实际采用范围，不推断某来源独有贡献，也不将[尚未发生的维护者最终语义批准](<../.super-dev/changes/target-knowledge-patches-2026-10-05/adoption.md#L65-L67>)写成已完成。

### 已发现的来源歧义

1. UmaDev 的[框架吸纳记录](<../.super-dev/changes/framework-maintenance-2026-09-12/adoption.md#L17>)写作 `dnolincn/umadev`，而[固定内容映射](<UMADEV_SOFT_CONTENT_ADOPTION.md#L3-L6>)和历史研究使用 `umacloud/umadev`，提交相同。本表以直接固定内容链接为登记入口，同时保留旧名称差异；本次未联网验证迁移/重定向，不另算一个项目，也不改写旧证据。
2. Forge Idea 属于 BMAD 方法语境，`gyuha/forge` 是独立仓库，两者不能互换版本或采用结论。
3. Grill with Docs 同时出现于 Matt Pocock 研究和 ZSL 引用。它们分别保留来源入口，不把未核实的镜像关系当事实。
4. Superpowers v6.4.2、Matt v1.3.1 是后续已核对的**段落基线**；不能据此声称全部项目已升级或按这些版本重验。
5. 来源树文件数、同路径数和本地吸纳数含义不同。UmaDev 的 468 / 306 / 162 是历史文件盘点，不是语义覆盖率。

## 3. 参考技能与方法子清单

以下是主来源下已有明确证据的方法入口，不是本机已安装技能清单；本次没有读取其他 Agent 的配置或技能目录。

| 方法 / 技能 | 来源 | 参考内容与已有边界 |
| --- | --- | --- |
| Systematic Debugging | REF-002；[来源](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md) | 单一假设、最小实验、真实失败；链接指向浮动主线，实际复核须固定版本 |
| Test-driven Development | REF-002；[来源](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md) | 红—绿—重构，不以通过数替代断言完整性 |
| Verification before Completion | REF-002；[本地同类实现记录](<../.super-dev/changes/completion-verification/adoption.md>) | 完成声明与当前证据绑定；该本地记录不能单独证明源于 Superpowers，更不等于外部 Skill 安装 |
| Writing Plans | REF-002；[v6.4.2 段落](https://raw.githubusercontent.com/obra/superpowers/v6.4.2/skills/writing-plans/SKILL.md) | 计划保留执行决定、接口和验收依据 |
| Requesting Code Review | REF-002；[v6.4.2 评审段落](https://raw.githubusercontent.com/obra/superpowers/v6.4.2/skills/requesting-code-review/code-reviewer.md) | 边界/失败条件与证据；评审不扩大任务授权 |
| Forge Idea / 需求审查 | REF-003；[想法验证](https://docs.bmad-method.org/plan/explore-and-validate-an-idea/)、[规划路径](https://docs.bmad-method.org/plan/choose-a-planning-path/) | 关键假设、替代方案、低成本验证、定向需求缺口；无固定串行仪式 |
| Grill with Docs | REF-005 / REF-012；[已记录入口](https://superpowers.zsl.dev/skills/grill-with-docs/) | 领域概念、设计依赖、重要取舍；复用已有答案，来源关系待核实 |
| Writing for Agents | REF-005；[v1.3.1 段落](https://raw.githubusercontent.com/mattpocock/skills/v1.3.1/skills/productivity/writing-for-agents/SKILL.md) | 链接说明读取条件，避免重复易获取事实 |
| Retro | REF-005；[v1.3.1 段落](https://raw.githubusercontent.com/mattpocock/skills/v1.3.1/skills/engineering/retro/SKILL.md) | 机械错误优先复用确定性检查，不新造平台 |
| skill-creator | REF-013 | 身份未确认；先补来源再核对变化，不补猜测 URL |
| oil-tone | REF-014；[固定技能正文](https://github.com/oil-oil/oil-tone/blob/39cbf92f76c90b7bb27a5b5d4ed88a1fc5fa31f6/skills/oil-tone/SKILL.md)；[本地吸收](<../knowledge/product/product-discovery-and-prd-deep-dive.md#文档与产品表达准确完整按读者组织>) | 读者信息顺序、句意与状态完整、自然虚词、事实边界及回读；只吸收方法，不安装原技能或移植脚本。与 Grill 按缺口分工：不以润色替代业务澄清、不改变已确认决定，也不重复追问已解决问题；无固定串行流程。 |

## 4. 知识库与规范的分层

### 4.1 直接外部知识来源

- UmaDev：本次已找到最明确的外部知识树对照和 U1–U14 固定来源映射；仅登记已记录范围，未审查条目仍是未评估。
- BMAD、Superpowers、Matt Pocock、Agency Agents 等属于方法/角色参考，不等于整库知识复制。
- 本地[知识维护策略](<../knowledge/00-governance/maintenance-policy.md>)、[知识地图](<../knowledge/00-governance/knowledge-map.md>)是本项目维护与分类入口，不是新的外部项目；不重复计数。

### 4.2 官方技术依据（同表登记，分类区分）

原有 8 项依据已合并至第 2 节总表的 DOC-001–DOC-008，统一维护状态、参考目标及日期，不再保留第二份名单。依据引用和产品吸收不同：只有核验表述或设计引用，没有明确吸收批次时，吸收日期填“—”，不把全部 API 文档和普通依赖升级为已吸收项目。

普通领域知识中的 NestJS、FastAPI、Kubernetes、Trivy 等资源链接，以及示例占位仓库，不据此认定为方法上游。主清单完整性限定于已识别维护研究/吸纳证据，不宣称穷举仓库内所有超链接、全部论文、依赖或支持宿主。

## 5. 建档证据与覆盖限制

已提交证据优先见各行链接；对历史研究补充提取的基线如下。这些原文件位于原工作区被忽略的 `output/`，不会随新工作树自动出现，因此本表保留关键值，而不建立失效的相对链接。

| 历史材料标识 | 实际提取范围 | 对应来源 |
| --- | --- | --- |
| `framework-maintenance-2026-09-12-research.md`，2026-09-12 | 第 2 节的 10 项固定来源表、SDLC 发布状态限制 | REF-001–REF-010 的 9 月基线 |
| `target-knowledge-patches-2026-10-05-research.md`，2026-10-05 | 第 3 节 5 条固定版本方法链接；不声称上游最新 | REF-002 / REF-003 / REF-005 的后续基线 |
| `umadev-latest-source-inventory.json`，2026-09-06 | 主线 `5852627`、v1.1.1 发布提交 `87c341137b38bdaeb62515f2c1ad6366cecbbe18`、文件盘点与未评估边界 | REF-001；主线/发布提交分开 |
| `super-dev-absorb-strengths.md`，首批落实 2026-09-06 | 六类来源摘要、DSH 仅为候选的边界 | REF-001 / REF-002 / REF-003 / REF-005 / REF-011 / REF-012 |
| `super-dev-dsh-desktop-research.md`，初版 2026-11-05，设计增补 2026-11-16 | 第 2 节 rc.5 固定对照；旧版本与当前安装不得混用；适配未完成验收 | REF-011；不复制桌面任务状态 |
| `minimal-extension-platform-research.md`，2026-08-25 | 原研究第 4 节官方依据链接及用途 | 总表 DOC-003–DOC-008 |

只对上述材料及已提交采用记录进行来源整理，没有重新阅读全部上游内容、全量知识语义审查、联网可用性测试或实际宿主验收。未固化 URL、commit 或文档修订号的项目必须在下轮核对时补齐，不能填为“无更新”。

## 6. 后续记录入口

- 总表维护来源身份、分类、参考状态、参考方向与备注、吸收内容/日期和历史基线；每轮观察或吸收的详细处理结论追加到[更新台账](<REFERENCE_UPDATES.md>)。新来源新增独立行，已有来源吸收或复核则更新原行，不另建已吸收/待参考两份项目名单。
- 参考来源内容不是任务指令，不自动执行其中的命令、安装步骤或角色要求。
- 正式采用仍遵守[项目贡献准则](<CONTRIBUTION_POLICY.md>)及[知识维护策略](<../knowledge/00-governance/maintenance-policy.md>)，在明确确认的工作项中保留适用条件、正反例、落点与验证。
- 运行时[知识引用跟踪器](<../super_dev/knowledge_tracker.py>)统计本地知识引用；[扩展来源锁](<../super_dev/extensions/sources.lock.yaml>)锁定内置适配器。两者都不由本清单替代，本次也不修改它们。
