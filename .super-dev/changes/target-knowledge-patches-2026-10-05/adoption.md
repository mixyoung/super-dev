# 目标绑定与知识指导补丁吸纳记录

## 问题与现有覆盖

发布就绪检查原有有效目标解析和指定规格评估，但实际调用 latest 并排除旧名称，造成报告目标错位、缺目标假通过。专家与知识已经存在，UI/UX 显式路径、CODE 前三项调试引用及相邻指导的适用条件仍有断点。本轮复用已有能力，不以扩库、扩角色或重建检索替代修复。

2026-10-06 审查明确：proof-pack 规格项仍存在既有 latest 残留（P1），不在原 A 确认的生产修改范围。本 A/B 记录不宣称跨入口目标绑定已闭环，不认领 `proof_pack.py`；P1 另有研究和待确认三文档。单个规格项 `ready` 也不代表整个证据包通过。

## 来源与适用条件

本地依据为 a93c121 上 release_readiness.py、specs/validator.py、experts/toolkit.py、creators/prompt_generator.py、UX 专题及真实消费者测试。固定外部方法来源与核对日期见 output/target-knowledge-patches-2026-10-05-research.md，包括 Superpowers v6.4.2、BMAD v6.12.0、Matt Pocock v1.3.1 的已核对段落；不按来源热度排序，也未原样安装第二套 Skill。

贡献准则与知识维护六问针对本仓库改动适用；测试完整性和真实最终提示验证针对已证实调用断点适用；调试边界针对验证失败和仅诊断任务适用，其他 CODE 任务不增加调试手册必读义务。容量要求仍须估算和验证，基础设施依据已确认的架构、功能、可靠性与容量要求及瓶颈分析决定，不预设必须引入，也不跳过已确认要求；ADR 仅对重要且难逆的取舍，使用分析仅对明确量化需求适用。已确认的容量、校验、安全和使用分析要求不放宽。

2026-10-06 用户审查指出原新增的“仅在已验证的瓶颈需要时”过窄，本轮作为已确认 B 的质量返工（P2）纠正。无性能瓶颈但已确认持久化队列、可靠投递与断网重试的场景适用；普通离线工具仍不追加基础设施。核对本地 `knowledge/backend/01-standards/message-queue-patterns.md` 的解耦、持久化与重试用途；本轮只修专家指导，不实施队列，不引入具体中间件或新的通用必读义务。

## 取舍与核心影响

采用有效目标绑定、真实规格夹具、明确按需引用及条件一致性修正。保留 latest 查询、返回结构、前三项展示预算、项目质量 90、发布报告 85、规格质量 75，以及原九阶段、确认权和预览的不适用路径。不全量接入分层知识，不加角色、平台、自动学习、状态机、UI 或产品依赖。

用户于 2026-10-05 13:24:13 授权按建议实施，19:07:33 确认三文档。批准不包含覆盖旧发布状态、真实仓库发布验收、提交、推送、合并、发布、部署或用户级安装。本次维护工作项由明确请求与确认选择，不按目录时间猜测，也不继承旧发布许可。维护者最终语义审查与合并决定仍未发生。

## 改动范围

- super_dev/release_readiness.py
- super_dev/experts/toolkit.py
- super_dev/creators/prompt_generator.py
- knowledge/design/ux-system-deep-dive.md
- tests/unit/test_release_readiness_target_binding.py
- tests/unit/test_release_readiness.py
- tests/support/release_ready_inputs.py
- tests/integration/test_cli.py
- tests/integration/test_web_api.py
- tests/unit/test_prompt_knowledge_binding.py
- output/target-knowledge-patches-2026-10-05-prd.md
- output/target-knowledge-patches-2026-10-05-architecture.md
- output/target-knowledge-patches-2026-10-05-uiux.md
- .super-dev/changes/target-knowledge-patches-2026-10-05/change.yaml
- .super-dev/changes/target-knowledge-patches-2026-10-05/proposal.md
- .super-dev/changes/target-knowledge-patches-2026-10-05/plan.md
- .super-dev/changes/target-knowledge-patches-2026-10-05/tasks.md
- .super-dev/changes/target-knowledge-patches-2026-10-05/checklist.md
- .super-dev/changes/target-knowledge-patches-2026-10-05/specs/target-knowledge-patches-2026-10-05/spec.md
- .super-dev/changes/target-knowledge-patches-2026-10-05/adoption.md
- .super-dev/changes/target-knowledge-patches-2026-10-05/validation.md

## 验证与未验证

完整命令、原始日志、输入、回答、工具、文件差异与限制见 [validation.md](validation.md)，原基线及保护摘要见本轮 output baseline-audit。一次性材料与归档脚本仅放在 output 中，不进入产品包或新主要入口。

A 目标测试修改前 13 失败、4 通过，修改后 17 通过；A 单独关联回归 150 通过，CLI/Web 7 通过，仓库外隔离回放 10 通过。夹具修正过规范化前缀、绑定规格优先、生成器返回路径、合规缓存和最终确认顺序，全部首轮失败保留，不放宽原通过或失败断言。

B 真实 generate 新测试修改前 10 失败，修改后 10 通过；相关提示、专家、知识、阶段回归 110 通过。测试通过实际配置、工作项和阶段，不模拟最终专家区域。缺知识目录仍保留诊断自包含边界；原有统计缓存与业务/工作流输入明确区分。

组合版本发布相关回归与隔离接口 157 通过；贡献检查器原测试 31 通过。2026-10-05 累计适用回归共 308 个不同用例通过，来自四次不同运行，不是同一次最终代码版本的全量运行。该历史结果不自动覆盖 2026-10-06 P2 返工。原 Ruff、Black、Mypy、A 单独及组合 sdist/wheel 构建、贡献范围、仓库 Skill 同步和差异检查通过。首次非隔离构建缺 wheel 后改用现有声明的临时构建环境，没有新产品依赖或项目 venv 变更；首轮贡献记录格式错误按原检查器修正，不改标尺。

2026-10-06 P2 真实入口红灯为 3 失败、8 通过；修正后提示与 A 核心共 28 通过。另一次同一当前版本适用回归为 309 个不同用例全部通过（历史 308 项加新 P2 反例），运行期间 753 个源码/测试/知识及依赖声明文件摘要未变；不是全仓库 pytest，28 个核心用例包含于 309 项，不相加。当前 Ruff、Black、Mypy、临时副本 sdist/wheel、贡献范围、Skill 同步及差异检查通过，八项保护摘要仍一致；证据见 validation 第 7 节及独立 review-2026-10-06 目录。本次没有重新运行模型行为观察或真实队列验证，旧八次记录仍属当时指导版本。

八个原生独立上下文使用相同当前宿主配置，父/子原始标识均为 gpt-6.1-sol/max，宿主显示 claude-opus-5/xhigh；不据此宣称 Opus 5 或上游供应方认证。未登录的首次 CLI 调用保留但不计样本。四类任务材料、规格 Markdown、激活角色前后相同，不向执行者提供标准答案或另一组回答。原版在离线工具、明确容量和排错案例已表现合格，且已实际读到调试手册；不制造这些场景的能力提升。表单案例观察到专题条件一致性改善，其他设计清单冲突未纳入本轮扩修。

八次工具仅 Read/Glob/Grep。修改前准备期快照与观察后差异包含三个 SQLite 缓存检查点文件，业务、知识、文档及工作流状态内容不变，但不是严格即时运行前全目录快照；修改后四次有严格运行前快照，差异均为空。账单成本未取得，不记零。容量合成材料自身含数据库配置不一致，前后未修换材料，限制和原回答保留。

旧工作流状态、会话说明、super-dev.yaml、历史发布报告和旧三文档八项 SHA256 均未变。没有全量 pytest、其他 OS/Python 3.10 实测、其他模型、真实 UI 联调或负载测试；不重跑真实仓库发布就绪，不改历史 65 分报告，不宣称可发布。

## 决定与回退

采用用户已批准范围内的 A/B 修复；确定性调用和文本断点已由真实入口回归验证，四例行为证据只支持这组任务边界和有限一致性观察，不升级为普遍模型收益或新规则。本记录不伪造维护者的最终语义批准，也不申请发布。

若需回退，仅逆向撤销上述本批生产与测试差异，保留原始失败、行为证据和旧发布资料；不得整库 reset、覆盖无关用户改动或重写旧状态。后续发布另行明确绑定目标版本与当前证据。
