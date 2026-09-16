# 周期性框架维护与知识边界加固

## Summary

在不改变单一 Core、标准九阶段、确认权、宿主执行边界与质量阈值的前提下，补齐内容权威、专家合同、标准流程工作项身份以及交付后事实语义。本文的 SHALL 是当前 change 的实现合同；PRD、架构和 UIUX 是其上游权威依据。

## ADDED Requirements

### Requirement: FR-01/FR-06 内容权威与知识信封

SHALL 系统以 L0-L4 表达宿主/核心合同、用户授权、当前工作项事实、适用知识与外部内容的权威顺序。任何 L3/L4 正文均只能产生显式允许的实现指导、验证指导或术语效果，永久禁止改变阶段、权限、确认、发布与工作区所有权。

分类 SHALL 由来源和受控元数据确定：已命中适用领域且无元数据的旧正式知识默认为 `applicable_constraint`；未正式吸纳的 external/generated 内容固定为 `advisory`。正文不能自抬权威。注入 SHALL 携带来源、内容类型、权威、适用原因、版本/核对日期、允许与禁止效果，并使用明确边界包住正文。

#### Scenario 1: 适用旧知识保持强制
- GIVEN 一份已在仓库正式维护、无显式权威元数据且命中当前领域的旧知识
- WHEN 构造知识信封
- THEN 权威为 `applicable_constraint`
- AND 允许效果不包含任何控制面效果

#### Scenario 2: 恶意正文无控制权
- GIVEN 知识正文要求跳过文档确认、读取工作区外凭据并直接发布
- WHEN 它被注入提示并尝试转换为状态或工具授权
- THEN 信封明确标为无控制权
- AND 状态/确认写入与高风险动作守卫拒绝该来源

#### Scenario 3: 正常编辑不重复确认
- GIVEN 用户已授权当前工作区内的可逆实现编辑
- WHEN 适用知识要求进行该编辑或编写迁移代码
- THEN 不因知识条目本身再次要求确认
- BUT 破坏性操作、工作区外写、Git 远端写、外部系统写、生产操作、生产数据迁移执行、凭据读取和权限扩大仍要求明确权限

### Requirement: FR-02 单一阶段专家真源

SHALL `WORKFLOW_STAGE_EXPERTS` 是标准与现有 SEEAI 阶段专家集合的唯一字面真源。旧 `PHASE_EXPERT_MAP` 只能是从 canonical 映射确定性派生的只读兼容视图；Toolkit、提示、运行状态、报告和 README 说明必须与真源一致。

#### Scenario 1: 兼容视图不可漂移
- GIVEN 任一 canonical 阶段
- WHEN 读取兼容映射并尝试修改
- THEN 读取结果与 canonical 集合一致
- AND 修改失败，不存在第二份角色字面量

#### Scenario 2: SEEAI 组合保持不变
- GIVEN `build_fullstack` 与 `polish` 等已有 SEEAI 阶段
- WHEN 完成映射收敛
- THEN 角色集合、模板与状态路径逐字保持本批基线行为

### Requirement: FR-03 ExpertProfile v2 与独立评审证据

SHALL 常规 ExpertProfile 表达 identity、applicability、contract、assurance 与 customization 字段，包括 `when_to_use`、`when_not_to_use`、required inputs、outputs、authority、non-goals、evidence requirements、stop conditions 和 handoff checklist。v1 文件仍可读，缺失字段采用不扩大权限的保守默认。

内置角色 SHALL 使用可验证的工作立场而非年限、证书或虚构经历。项目覆盖优先级保持不变，但不能批量导入外部角色集合或静默扩大全局角色枚举。`VERIFICATION` 保持 QA 变体，`OVERSEER` 保持无批准权的兼容观察角色。

独立评审声明 SHALL 至少可回读不同会话身份、实际模型/提供方、只读范围以及工具/文件变化证据。同一会话或仅换角色只能标为自检。安全信任边界、资金、生产数据迁移或不可逆外部写入默认要求不同会话只读复审；不可取得时标为未验证/受阻或记录用户残余风险接受，但不能改称独立。

#### Scenario 1: 不适用角色不激活
- GIVEN 无数据库影响的 CLI 文案变更
- WHEN 选择阶段专家
- THEN 不仅为了“全面”激活 DBA

#### Scenario 2: 同模型换角色仍是自检
- GIVEN 同一会话模型从 CODE 切换到 QA
- WHEN 写评审证据
- THEN 独立性为 self-review，而非 independent

### Requirement: FR-04 风险缩放不削弱门禁

SHALL `bounded / architectural / commercial` 只调整文档密度、适用角色和适用知识；它们不能替代用户确认、降低项目门禁或让高风险工作绕过安全、质量与交付证据。范围不明时采用保守范围。

#### Scenario 1: 小改动不制造无关义务
- GIVEN 已确认范围的纯文案 patch 且无数据、UI、云或运营影响
- WHEN 生成适用任务
- THEN 不要求数据库、云监控或完整商业计划

#### Scenario 2: 高风险不能借 bounded 降级
- GIVEN 涉及资金或权限边界的变更
- WHEN 请求 `bounded`
- THEN 仍保留适用的安全、质量与交付证据要求

### Requirement: FR-05 标准流程 Spec 前工作项身份

SHALL 标准流程在 baseline/research 起始即在现有 workflow-state 中持有唯一 `work_item_id`；`artifact_prefix` 只能由该身份通过既有确定性净化规则派生。Spec 前 `binding_status=pre_spec`，不创建 change、不继承确认、不允许进入实现；文档确认后只可绑定同名正式 change 并转为 `bound`。

绑定 SHALL 同时校验 work item、派生前缀、正式 change 与当前文档摘要。不一致时失败关闭：阻止 active change 绑定、proposal/tasks、Spec 生成和 docs_confirm 后阶段；仍允许只读旧 change、修订当前文档和用户选择正确 work item。不得按时间、最新目录或模型推断自动修复。缺少新字段的旧状态继续安全读取，不崩溃、不误推进。SEEAI 现有路径不变。

#### Scenario 1: 旧交付证据不污染新研究
- GIVEN 旧 change 为 `delivery_ready`
- AND 新标准工作项已进入 research/pre_spec
- WHEN 恢复流程
- THEN 只显示新工作项文档
- AND 旧 proof-pack 不作为新任务证据

#### Scenario 2: 身份或摘要不匹配
- GIVEN work item、artifact prefix、change id 或确认摘要任一不一致
- WHEN 尝试创建 Spec 或推进后续阶段
- THEN 操作失败并报告具体不匹配
- AND 不自动改写成一致

### Requirement: FR-08 独立交付事实与运营信号

SHALL `delivery` 保持九阶段终点；`delivery_ready`、`released`、`deployed`、`operating` 只是阶段后的独立事实标签。每项在无自身证据时为 unknown，不能互相推导或成为第十阶段。

现有交付或产品报告 MAY 以向后兼容的可选 `operational_outcomes` 承载真实信号。每条记录 SHALL 包含 signal、source、observed_at、target_version、evidence、confidence、impact 和 recommended_action；confidence 至少为 verified、pending 或 refuted。缺来源或目标版本时不得 verified。反馈不自动改知识或重开工作流，只能作为下一次 patch/evolve/baseline 的有来源输入。

#### Scenario 1: 部署不等于运营成功
- GIVEN 已有目标环境部署证据
- AND 没有用户或运行结果证据
- WHEN 汇总交付事实
- THEN `deployed` 可核实
- AND `operating` 保持 unknown

#### Scenario 2: 不完整信号待核实
- GIVEN 一个没有来源或目标版本的事故描述
- WHEN 写入可选运营结果
- THEN confidence 为 pending
- AND 不自动升级为全局知识或新开发任务

## MODIFIED Requirements

### Requirement: 现有提示、状态与报告消费者

SHALL 现有消费者引用上述 canonical 合同，不复制新的权威层级、角色集合或事实推导逻辑。README 可由测试保护而不要求引入生成器。缓存、模板与报告均不是授权来源。

## Execution Context

| 影响面 | 当前入口 | 本次变化 | 兼容风险 |
| --- | --- | --- | --- |
| 核心与提示 | `workflow_contract.py`、`prompt_generator.py`、Skill 模板 | 统一内容权威合同并在低权威内容前引用 | 宿主文案同步漂移 |
| 知识 | `orchestrator/knowledge_pusher.py` | 确定性信封与内容边界 | 旧知识被误降级 |
| 专家 | `workflow_stage_truth.py`、`experts/*` | 单一映射、画像 v2、独立性证据 | 覆盖文件/提示兼容 |
| 工作项 | `artifact_utils.py`、`review_state.py`、`workflow_guard.py`、Spec 入口 | pre_spec/bound 与摘要校验 | 旧状态读取、SEEAI 隔离 |
| 交付 | 现有 release/proof/product 报告模型 | 独立事实与可选运营结果 | 旧 JSON 读者兼容 |

## Acceptance Checklist

- [ ] AC-01 恶意知识不能改变阶段、权限、确认、发布或工作区所有权
- [ ] AC-02 适用旧知识不被运行模型降级，未吸纳外部内容不能自升权威
- [ ] AC-03 所有指定阶段专家消费者与唯一真源一致，兼容视图不可写
- [ ] AC-04 ExpertProfile v1/v2、覆盖优先级、停止/交接与独立评审证据通过正反例
- [ ] AC-05 新旧工作项共存、摘要不符、旧状态缺字段和原子写均失败安全
- [ ] AC-06 四类交付事实互不推导，运营信号缺来源/版本时不得 verified
- [ ] AC-07 标准九阶段与 SEEAI 现有合同未变化
- [ ] AC-08 贡献范围、格式、类型、相关回归与质量门禁给出当前版本真实结果

## Out of Scope

- FR-07 Skill 渐进拆分与宿主加载实验
- FR-09 周期自动观察、定时任务或自动 PR
- 第二 Core、第二状态机、DAG、角色团队、模型运行程序或新主入口
- 新质量分数、降低门槛、自动改知识、自动发布/部署
- UI、前端、组件、设计 token 与预览确认

## Verification

- 先为每个新增合同写失败用例，再实现并复跑；保留实际失败原因，不调分、不删场景。
- 定向覆盖知识、专家、工作项绑定、交付事实；随后运行受影响旧回归。
- 冻结代码后运行 Ruff、Black、Mypy、compileall、贡献范围和 Skill 同步检查。
- 质量门禁与证据必须绑定当前文件摘要；超时仅表示未完成，旧 CI 或旧 proof-pack 不替代当前版本。
