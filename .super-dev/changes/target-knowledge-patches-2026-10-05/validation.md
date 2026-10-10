# 目标绑定与知识指导补丁验证记录

## 1. 范围、授权与环境

- 基线：`a93c12108835508d9b01ff038c537a2a6f9e1976`；维护分支：`ocx/target-knowledge-patches-2026-10-05`。
- 用户于 2026-10-05 13:24:13 授权实施，19:07:33 确认本组三文档。本记录不代替维护者最终代码审查，不授权合并或发布。
- 本轮只有本会话写生产文件。八个行为执行上下文只读；没有将代码实现交给其他写入者。
- Windows 10，项目解释器 `.venv/Scripts/python.exe`，Python 3.13.12；源码目标仍为 Python 3.10+。pytest 9.0.3、Ruff 0.15.11、Black 26.3.1、Mypy 1.20.1、build 1.6.0。
- 无 UI 实现，原前端与预览确认的不适用路径保持。合成表单只是只读任务材料，不是本次前端交付。
- 不新增产品依赖、角色、检索平台、自动学习、流程阶段或模型接口；未改版本号和 `super-dev.yaml`，未提交、推送、发布、部署。

## 2. 补丁 A：目标绑定与真实消费者

发布规格质量检查改用已解析的有效工作项，复用指定工作项评估；缺目标、无效绑定、目标目录或必要规格缺失使用原必检失败机制。保留显式查询最新变更的原能力、现有 JSON 形状及门槛：项目质量 90、发布报告 85、规格质量 75。

| 检查 | 实际结果 | 原始证据 |
| --- | --- | --- |
| 新目标绑定测试，修改前 | 失败（`FAIL`）：13 失败、4 通过 | [JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-a-red.xml) |
| 同一目标测试，核心修复后 | 通过（`PASS`）：17 通过 | [JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-a-green.xml) |
| 完整关联回归，A 单独版本 | 通过（`PASS`）：150 通过，400.33 秒 | [日志](../../../output/target-knowledge-patches-2026-10-05/command-a-related-final.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-a-related-final.xml) |
| CLI/Web 发布入口 | 通过（`PASS`）：7 通过，79.19 秒；327 个无关测试未选中 | [日志](../../../output/target-knowledge-patches-2026-10-05/command-a-cli-web-final.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-a-cli-web-second.xml) |
| 仓库外隔离回放消费者 | 通过（`PASS`）：10 通过，54.74 秒 | [日志](../../../output/target-knowledge-patches-2026-10-05/command-a-replay.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-a-replay.xml) |
| 贡献检查器原测试 | 通过（`PASS`）：31 通过，22.57 秒 | [日志](../../../output/target-knowledge-patches-2026-10-05/command-a-contribution-tests.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-a-contribution.xml) |

目标测试覆盖质量正反组合及两个目录时间方向、无绑定但有唯一合格目录、无效绑定、目录在检查器创建前后消失、必要规格缺失、特殊旧名称正常评估、其他项全部通过时仍阻断、显式 latest 查询及序列化结构。没有用模拟质量报告替代真实目标质量评估。

共享绿色夹具先绑定目标、准备 Requirement/Scenario 和原验证器需要的规格文件，再生成证据身份与最终确认。统一使用绑定后的规范化产物前缀；规格路径使用生成器返回值，避免假定 `add-` 等前缀不会被去除。证据包夹具在补齐最终需求后重新水化和确认。原通过断言没有删除、降级或新增跳过。

### 保留的首轮失败与修正

1. 关联回归首轮 149 通过、1 失败：原临时目录名含下划线，绑定后的规范化产物前缀使用短横线；测试改了错误的 PRD。修正夹具和消费者路径，不放宽 `identity_mismatch` 断言。[原始日志](../../../output/target-knowledge-patches-2026-10-05/command-a-related-first.txt)。
2. 前缀修正后，绑定规格优先于 PRD，旧负例只改 PRD 已不足以制造规格缺口；夹具也不能以零需求的缓存报告假作合规。本轮补充有效版本需求及一条已验证需求的合成缓存，负例修改实际绑定规格并保留原失败、零分和身份错位断言。[前缀轮日志](../../../output/target-knowledge-patches-2026-10-05/command-a-prefix-fix.txt)。
3. 首轮正例发现假定规格目录名错误，改为使用 `scaffold_change_artifacts()` 返回的 `spec.md` 路径；原正反断言随后均通过。[失败日志](../../../output/target-knowledge-patches-2026-10-05/command-a-fixtures-first.txt)、[修正日志](../../../output/target-knowledge-patches-2026-10-05/command-a-fixtures-second.txt)。
4. CLI 正例原来依赖没有有效规格需求时的“不适用”，补充真实规格后必须提供对应合规证据；新增与绑定规格匹配的受控缓存，保留整体通过断言。[首轮日志](../../../output/target-knowledge-patches-2026-10-05/command-a-cli-web-first.txt)。

这些缓存、确认和宿主验收均是隔离测试夹具，不是实际用户确认、真实发布验收或本仓库今天的发布评分。

## 3. 补丁 B：真实最终提示与条件一致性

生产落点只包括 `toolkit.py`、最终提示相关引用文字以及 UX 专题的三条冲突。领域扫描追加手册目录，保持原类别顺序；显式核心文件仍优先。UI/UX 引用现有正确文件；CODE 前两项保留，调试手册作为第三项按需引用。原前三项展示预算保持，不全量注入分层知识。

| 检查 | 实际结果 | 原始证据 |
| --- | --- | --- |
| 真实 `generate()` 新测试，修改前 | 失败（`FAIL`）：10 失败 | [日志](../../../output/target-knowledge-patches-2026-10-05/command-b-red.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-b-red.xml) |
| 同一入口，修改后 | 通过（`PASS`）：10 通过，3.37 秒 | [日志](../../../output/target-knowledge-patches-2026-10-05/command-b-green.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-b-green.xml) |
| 提示、专家、知识及阶段真实性关联回归 | 通过（`PASS`）：110 通过，11.47 秒 | [日志](../../../output/target-knowledge-patches-2026-10-05/command-b-related.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-b-related.xml) |

隔离项目通过真实工作项、配置、阶段记录与合成文档确认取得真实阶段，调用完整 `AIPromptGenerator.generate()`；未模拟角色选择、阶段或最终专家拼接方法。测试验证多个通用候选不能截断 CODE 调试引用、目标项目路径不跟随当前目录、普通手册扫描确实进入最终提示、UI/UX 显式引用优先、无知识目录时诊断边界自包含，以及容量、ADR、埋点条件和旧冲突文字。

生成器原有 SQLite 知识统计缓存可以更新；输入不可变测试只排除三个明确的统计缓存文件，仍比较业务、知识、文档、规格和工作流输入。没有将整个生成器描述为无任何文件副作用。

## 4. 四类独立行为对照

### 执行条件与元数据

- 前后各四个全新原生宿主上下文；同一 `claude` 执行类型、不覆盖模型参数、相同只读指令。执行者仅获得自身任务目录，不获得验收答案、作者差异解释或另一组回答。
- 主任务、业务文件、依赖声明、配置及核心任务文档字节相同；规格 Markdown 和激活角色相同。知识原文只有已授权 UX 专题变化，生成指导按本轮代码重新生成。[材料比较](../../../output/target-knowledge-patches-2026-10-05/behavior-pair-materials.json)、[规格与角色比较](../../../output/target-knowledge-patches-2026-10-05/behavior-stage-controls.json)。
- 宿主界面报告 `claude-opus-5`／`xhigh`，但父执行器及八个独立上下文原始记录均为 `gpt-6.1-sol`／`max`。这是可核对的记录标识，不是对上游模型供应方的独立认证；不能将结果写成 Opus 5 评测。前后使用同一当前宿主实际执行配置，不是跨模型比较。
- 首次命令行调用初始化成功但未登录，退出 1、没有实际模型回答或读取，保留但不计入样本。[日志](../../../output/target-knowledge-patches-2026-10-05/command-behavior-cli-auth-failure.txt)、[初始化及错误记录](../../../output/target-knowledge-patches-2026-10-05/before-case-1-observation.jsonl)。之后使用本宿主原生隔离能力，而非创建产品模型接口或切换模型设置。
- 八次实际工具均只有 Read/Glob/Grep，没有命令执行、写入工具、外部服务或下级执行者。模型“已读”自述不算证据，手册读取核对实际成功工具返回。

| 场景 | 修改前观察 | 修改后观察 | 结论与原始回答 |
| --- | --- | --- | --- |
| 无数据库离线 CSV 工具 | 只建议帮助描述与必要验证，不引入基础设施或 ADR；指出缺少直接调用入口 | 保持相同范围，不为验证顺带新增入口，不迁移架构 | 当前场景旧行为已满足；不制造提升。[前](../../../output/target-knowledge-patches-2026-10-05/before-case-1-native.answer.md)／[后](../../../output/target-knowledge-patches-2026-10-05/after-case-1-native.answer.md) |
| 无使用分析的单任务表单 | 保留范围，但报告“必须次任务”和冻结设计冲突，并按旧专题保留无条件即时校验要求 | 不增次任务、埋点或漏斗；建议操作后失焦加提交兜底，保留错误恢复、必填和无障碍；不许诺不存在的撤销 | 观察到专题条件一致性改善，不等于页面已运行。通用清单 Toast 条目仍被指出，不宣称解决所有知识冲突。[前](../../../output/target-knowledge-patches-2026-10-05/before-case-2-native.answer.md)／[后](../../../output/target-knowledge-patches-2026-10-05/after-case-2-native.answer.md) |
| 明确容量后端 | 不把 80 RPS 的合成记录当 100 RPS 达标；保留延迟/错误率目标，不预设分片 | 同样要求补测目标负载；CPU 外推明确为风险假设，不作达标证明；按瓶颈选择后续方案 | 两组都满足当前容量边界，没有普遍性能收益证明。[前](../../../output/target-knowledge-patches-2026-10-05/before-case-3-native.answer.md)／[后](../../../output/target-knowledge-patches-2026-10-05/after-case-3-native.answer.md) |
| CODE 激活的 pytest 排错 | 实际成功读取调试手册一次，分清环境导入与业务结果；仅诊断 | 同样实际成功读取一次；依赖已声明、虚拟环境未核对、业务尚未执行；不改代码或环境 | 原版已能找到并用对手册，本轮只证明显式引用稳定进入前三项，不宣称模型诊断能力提升。[前](../../../output/target-knowledge-patches-2026-10-05/before-case-4-native.answer.md)／[后](../../../output/target-knowledge-patches-2026-10-05/after-case-4-native.answer.md) |

### 实际读取与文件差异

| 场景 | 前／后实际工具数 | 前／后成功读取调试手册 | 前后文件证据 |
| --- | --- | --- | --- |
| 1 | 12／14 | 0／0 | [前记录](../../../output/target-knowledge-patches-2026-10-05/before-case-1-native.summary.json)／[后记录](../../../output/target-knowledge-patches-2026-10-05/after-case-1-native.summary.json) |
| 2 | 15／14 | 0／0 | [前记录](../../../output/target-knowledge-patches-2026-10-05/before-case-2-native.summary.json)／[后记录](../../../output/target-knowledge-patches-2026-10-05/after-case-2-native.summary.json) |
| 3 | 16／9 | 0／0 | [前记录](../../../output/target-knowledge-patches-2026-10-05/before-case-3-native.summary.json)／[后记录](../../../output/target-knowledge-patches-2026-10-05/after-case-3-native.summary.json) |
| 4 | 8／7 | 1／1 | [前记录](../../../output/target-knowledge-patches-2026-10-05/before-case-4-native.summary.json)／[后记录](../../../output/target-knowledge-patches-2026-10-05/after-case-4-native.summary.json) |

每个记录相邻的 `.jsonl` 保存完整原始消息与工具返回，没有只截取最好的一次。工具数量不是收益指标，不根据上述小样本打分或推广整体能力提升。原生记录没有可靠账单成本字段，成本未填成零。

修改前快照取于准备进程退出前，包含随后 SQLite 检查点的三个统计缓存差异；业务、知识、文档、规格和工作流状态内容未变，但没有严格的即时运行前全目录快照。因此不能宣称修改前全目录零差异。修改后增加了进程退出后、执行前快照，四次完整运行前后差异均为空。准备期自身能复现相同三个缓存差异：[缓存检查点证据](../../../output/target-knowledge-patches-2026-10-05/preparation-cache-checkpoints.json)。

容量案例的 `database: none` 与合成 README/测量中的数据库字段不一致；前后材料均保留原样，原回答中保留对此的分析或遗漏。该材料限制进一步说明：四例只支持这组边界，不能代替真实后端验收。

## 5. 组合代码与贡献收口

| 检查 | 结果与证据 |
| --- | --- |
| 两批组合版本的发布关联和隔离接口回归 | 通过（`PASS`）：157 通过，374.29 秒，[日志](../../../output/target-knowledge-patches-2026-10-05/command-ab-release-regression.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/batch-ab-release-regression.xml) |
| Ruff、Black、Mypy | 通过（`PASS`）：Ruff 无错误；Black 242 文件不变；Mypy 236 源文件无错误。[日志](../../../output/target-knowledge-patches-2026-10-05/command-b-static.txt) |
| A 单独包构建 | 通过（`PASS`）：sdist 与 wheel 均成功；第一次 `--no-isolation` 因环境缺 wheel 受阻，随后使用已有构建声明的临时环境，不改产品依赖或项目 venv。[失败](../../../output/target-knowledge-patches-2026-10-05/command-a-build-missing-wheel.txt)／[成功](../../../output/target-knowledge-patches-2026-10-05/command-a-build-isolated.txt) |
| 组合包构建 | 通过（`PASS`）：sdist 与 wheel 均成功。[日志](../../../output/target-knowledge-patches-2026-10-05/command-ab-build.txt) |
| 贡献范围与 Skill 同步 | 通过（`PASS`）：按真实基线检查；`SUPER_DEV_SKILLS_IN_SYNC=yes`。[最终日志](../../../output/target-knowledge-patches-2026-10-05/command-contribution-and-skill-final.txt)。未执行同步写入或用户安装。首次记录格式失败已修正，不改检查器。[首轮失败](../../../output/target-knowledge-patches-2026-10-05/command-a-contribution-format-failure.txt) |
| 差异复核 | 通过（`PASS`）：生产修改仅四个已确认落点；测试没有新增 skip/xfail、删除通过断言或改门槛；`git diff --check` 通过 |

2026-10-05 累计适用回归为发布相关 157、B 相关 110、隔离回放 10、贡献规则 31，共 308 个不同用例通过。四组来自不同运行，不是同一次最终代码版本的全量运行，也不自动证明 2026-10-06 P2 返工后通过。没有运行仓库全量 pytest；未验证其他 OS、Python 3.10 实际运行、其他模型、真实 UI 运行或负载性能。API 测试保留现有 Starlette/httpx 弃用警告，未为消除警告引入新依赖。

一次性归档脚本曾因 Windows 命令转义出现语法错误，未写出记录；改用明确字符编码后完成归档。它不是产品测试红灯，也未加入产品运行路径。

## 6. 保护与发布边界

[八项 SHA256 复核](../../../output/target-knowledge-patches-2026-10-05/protected-hashes-first-final.json)全部不变：旧工作流状态、会话说明、配置、历史发布 Markdown/JSON 和旧三文档。历史 65 分报告保留原样，不归属于本次当前代码版本。

所有发布与证据包消费者测试均在隔离项目中运行。构建制品仅用于本地验证，没有真实仓库发布就绪评估、证据包重跑、远端设置、提交、推送、合并或发布动作。下一次发布必须重新绑定目标版本、有效工作项与当前证据，不继承旧确认或本次合成结果。

原始日志索引见 [command-log-index.json](../../../output/target-knowledge-patches-2026-10-05/command-log-index.json)。该索引保存 2026-10-05 的历史运行；新增 P2 证据单独归档在下节，不覆盖旧日志或八次行为记录。验证记录不能替代维护者语义审查或发布许可。

## 7. 2026-10-06 用户审查返工（P2）

用户指出“缓存/队列/分片仅在已验证的瓶颈需要时选择”是本轮新增过窄条件。本次在已确认 B 的质量返工范围内，改为依据已确认的架构、功能、可靠性与容量要求及瓶颈分析决定是否采用，并保留“不预设必须引入，也不跳过已确认要求”。本次生产新增返工仅该清单一行；相邻 playbook 的瓶颈选择限定在容量或扩展情境，不是所有队列用途的排他条件。未实施任何队列、服务或依赖。

修正原先锁定过窄文字的两类输入，新增“无性能瓶颈，但已确认持久化队列、可靠投递与断网重试”的真实 `generate()` 反例；确认完整任务描述进入最终提示、ARCHITECT 实际激活，且不残留排他性旧条件。明确容量验证、无关小工具不增加基础设施及 ADR 条件仍保留。

| 检查 | 当前真实结果 | 本次原始证据 |
| --- | --- | --- |
| 返工前真实提示反例 | 失败（`FAIL`）：3 失败、8 通过，4.73 秒；失败均为过窄指导，已确认描述进入提示 | [日志](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-red.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-red.xml) |
| 返工后提示与 A 目标核心测试 | 通过（`PASS`）：28 通过，4.89 秒；提示 11 项和目标 17 项 | [日志](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-green.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-green.xml) |
| 当前同一次适用回归 | 通过（`PASS`）：309 通过，412.37 秒；历史 308 个适用用例加新 P2 反例；保留一项既有 Starlette 弃用警告，无失败或跳过 | [日志](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-current-regression.txt)、[JUnit](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-current-regression.xml) |
| 运行版本连续性 | 通过（`PASS`）：753 个源码、测试、知识及依赖声明文件在该回归运行前后摘要一致 | [命令与输入摘要](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-current-regression-inputs.json)、[运行后核对](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-current-regression-source-check.json) |
| Ruff、Black、Mypy | 通过（`PASS`）：无 lint 错误、242 文件格式不变、236 源文件类型检查无错误 | [日志](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-static.txt) |
| 临时源码副本构建 | 通过（`PASS`）：sdist 与 wheel 均成功；使用已有构建声明的隔离环境，未改项目 venv 或新增依赖，制品未发布 | [日志](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-build.txt)、[制品摘要](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-build-artifacts.json) |
| 贡献范围、Skill 同步及实际差异 | 通过（`PASS`）：按原基线检查；`SUPER_DEV_SKILLS_IN_SYNC=yes`，没有同步写入；`git diff --check` 通过，证据包生产文件未改 | [日志](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-contribution-and-skill.txt) |
| 八项保护与未实施边界 | 通过（`PASS`）：旧状态、会话说明、配置、历史报告及旧三文档摘要均不变；`proof_pack.py` 与原基线一致，HEAD 未变 | [保护核对](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-protected-boundaries.json) |

[本次用例去重核对](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-regression-summary.json)确认 309 个不同用例，无失败、错误或跳过。更新维护记录后再次核对贡献范围、Skill 同步、差异、753 项源码连续性和八项保护摘要，均通过（`PASS`）：[最终命令](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-final-closure.txt)、[最终摘要核对](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/p2-final-source-check.json)。本次新增证据文件的摘要索引为 [review-evidence-index.json](../../../output/target-knowledge-patches-2026-10-05/review-2026-10-06/review-evidence-index.json)，不覆盖原归档。

本次 309 项是同一次当前版本适用运行，不是全仓库 pytest；其中 28 个核心测试与前一行绿灯有重叠，不能相加成更多用例。2026-10-05 的 308 项仍是累计历史证据，原八次模型行为结果属于当时指导版本，不冒称 P2 返工后模型行为或队列可靠性已实测；本次不增加模型评测。

### 独立 P1 边界

只在临时合成项目复核了无绑定唯一合格目录、合格绑定目标与较新无关不合格项两个残留，输入摘要未变。没有组装整个证据包，没有在真实仓库评估。`proof_pack.py` 与基线提交一致，未修改；P1 的研究及三文档另放 `output/proof-pack-target-binding-2026-10-06-*`，停在文档确认门，未创建新正式 Spec/tasks。原 A 认可不等于跨入口闭环，也不构成新补丁批准。
