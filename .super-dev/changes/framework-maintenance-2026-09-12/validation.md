# Validation: framework-maintenance-2026-09-12

验证环境：Windows，仓库 `E:\33_dev_env\super-dev`，实现基线 `af875a92b6828896a923c5c7cfc680519647e2fd`。本文件记录实际运行结果；计划、旧报告和模型自评分不算通过。

## 先失败后修复

- 新增合同首次收集：4 个导入错误，分别缺少内容权威、独立评审证据、work item 身份和交付事实实现；这是预期红灯。
- CLI work item 回归首次运行：2 失败、30 通过。失败原因是中文自动项目名被 ASCII 身份规则误拒绝；规则改为安全 Unicode 字母/数字及原分隔符后，相关 9 项通过。
- 影子账本显式选择首次回归：3 失败、12 通过、1 跳过。失败夹具没有声明活动 change；补充明确 workflow-state 身份后，15 通过、1 个既有符号链接平台跳过。
- 完整 Mypy 首次运行：1 个 `workflow_payload` 推断错误；补明确 `dict[str, Any]` 后，233 个源码文件通过。
- 质量角色适用性新增用例首次失败：`CrossReviewEngine` 接收筛选后的工具箱却执行全局集合，导致 PM/UI/UX 继续审查纯架构文档；改为只使用传入的 canonical 子集后，相关 11 项通过。
- OpenCode MiniMax-M3 与 DeepSeek-v4-flash 首轮源码复审均为 `CHANGES_REQUIRED`。DeepSeek 发现外部评审 JSON 可自报独立/风险接受且收集异常会被吞掉；MiniMax 发现显式工作项大小写在 `SpecBuilder` 中可能漂移。已按当前 Core 定向修复，没有降低门禁或把首轮结论改写为通过。
- 用户授权后的第二轮仍为两份 `CHANGES_REQUIRED`：确认了风险 scope 未知时的 fail-open、SEEAI 专属阶段角色被标准过滤、当前版本未知时旧 verified 事实残留，以及未见证低风险评审仍可计分。已分别改为保守要求复审、冻结 SEEAI 专属集合、降级旧事实和零权重 advisory；差异包完整性/后置见证意见按明确披露范围与两步信任合同未采纳。
- 第三轮双模型均 PASS 后，uv formal fresh-verification 本身通过，但其高权限进程候选摘要与受限质量进程不一致。字段对比证明唯一差异来自用户本地 `.claude/settings.local.json` 是否被机器级 Git ignore 排除。候选计算现显式排除该本地配置，并覆盖 `core.excludesFile` 的机器差异；没有用环境相关摘要继续拼接证据。
- delivery 阶段首次刷新 Feature Checklist 时把 research 的“建议吸收优先级”及“暂缓项”误作当前 missing，产生 7 个虚假 P0/P1 gap。新增反例首跑 1 失败、3 通过，失败来自夹具声明 active change 后仍使用错误 PRD 前缀。简单忽略所有优先级行又使既有“P0 路线图 + 未完成任务”验收在 formal run 中 1 项失败；最终规则为：明确 gap 章节/同行含未实现语义始终是 gap，纯优先级路线图只有在关联当前未完成任务时才是 gap。对应 6 项定向回归全部通过。
- 系统 Python 全量单元测试：2750 通过、4 失败、4 跳过；4 个失败均为子进程使用 `C:\Python314\python.exe` 时缺少项目必需的 PyYAML。相同失败项在锁定 uv 环境为 5 项通过，随后锁定环境完整单元集为 2754 通过、4 跳过。
- 贡献范围首次检查按预期失败：adoption 尚未列出全部受控文件；随后补全逐文件范围并重跑，最终结果另见下节。

## 最终已通过

| 检查 | 实际结果 |
| --- | --- |
| 新增内容权威、ExpertProfile v2、work item、交付事实合同 | 32 通过；后续扩展定向组 18、23、15 项分别通过 |
| 专家/提示/阶段/状态/发布证据关联回归 | 197 通过，耗时 362.73 秒 |
| 知识注入、方法吸收、Prompt 与各宿主 Skill | 103 通过 |
| CLI 文档确认与恢复、Spec/影子账本/任务执行 | 首轮 2 失败后修复；相关 9 通过，另 30 通过 |
| 影子账本显式身份与恢复摘要 | 15 通过、1 个既有平台跳过 |
| 完整单元测试 | 主体实现版本、最终 CrossReview 适用性小修前：`uv run --frozen --offline python -m pytest tests/unit -q`，2754 通过、4 跳过，860.15 秒 |
| 外部评审信任边界与关联回归 | 第二轮问题收口后 `132 passed in 374.84s`；此前 Black 修正单个新增集成测试格式后，3 个质量 CLI 用例再次通过，13.27 秒 |
| 候选身份跨环境确定性 | `tests/extensions/test_evidence.py`：6 通过、1 个既有平台跳过；受限 Python 与高权限 uv Python 复算摘要逐字相同 |
| Feature Checklist gap 语义 | 两轮各暴露 1 个真实夹具/兼容失败；最终 Feature Checklist 全组与 formal 唯一失败用例共 6 项通过。真实项目重建为 0 个显式 gap、0 个 P0/P1 gap，33 个未知项仍保留为 unknown |
| Ruff | 全部生产代码及本轮测试通过 |
| Black | 392 个生产/测试 Python 文件无需再格式化 |
| Mypy | `uv run --frozen --offline mypy super_dev/`：233 个源码文件通过 |
| 编译 | `python -m compileall -q super_dev`：退出码 0 |
| 差异空白检查 | `git diff --check`：退出码 0 |
| Skill 同步 | `python scripts/sync_super_dev_skills.py --write` 后 `SUPER_DEV_SKILLS_IN_SYNC=yes` |
| 贡献范围 | `python scripts/check_contribution_policy.py --base af875a92b6828896a923c5c7cfc680519647e2fd`：通过；不代表语义审查或可发布 |
| Spec | 格式验证通过；质量 100/100，7 个需求、13 个场景、无 blocker |
| 红队 | 72/70 通过，0 critical；1 个 high 指向旧输出虚拟环境的 CA 证书文件，未作为本轮源码私钥问题处理 |
| 合规 | Spec coverage 92.9%、92/100；Architecture drift 1 个非 critical、90/100；UIUX 本轮不适用 |
| 产品审查 | 64/100、`attention`；0 critical、0 high，剩余项为交付证据、宿主真人验证和既有大模块 |
| 最终质量门禁 | FAIL，82.6/90；唯一 critical 为当前完成前验证 `BLOCKED`，外部独立复审另为 warning/blocked |
| 发布就绪 | FAIL，50/100；`delivery_ready=refuted`，`released/deployed/operating=unknown` |
| Proof pack | `incomplete`，27/35；没有把不完整证据推导为已发布、已部署或已运营 |

## 独立评审状态

用户随后明确授权只披露本 change 的源码、测试和文档差异。OpenCode 在 21 文件临时小范围副本上完成两个不同会话的只读复审：MiniMax 会话 `ses_f5bda7b90ffeFIXjmLSrQbmfQM`，实际路由 `mgate-agy-mxg-re/mmx-sub-dno-a/MiniMax-M3`；DeepSeek 会话 `ses_f5bda8698ffeBJ5FpzpFYmVTq1`，实际路由 `deepseek-payg-gy-com-dsv4f/deepseek-v4-flash`。副本审查前后摘要均为 `3C36BB6C8900D7ACA8D5232C01BC31B5E6CA5CA1588F2E3CA5CD5267E63788A1`，没有文件变化。两份首轮结论均为 `CHANGES_REQUIRED`，不能作为通过证据；原始结论与取舍分别保存在 output 的两份模型报告和综合报告中。

针对复审暴露的自证问题，质量门禁不再相信外部 JSON 自报的 `host_attested` 或 `residual_risk_accepted`。独立通过必须由调用方显式提供会话 ID 与精确 JSON SHA-256，并同时匹配当前 work item、项目目标版本和候选摘要；任何收集异常都会生成失败/警告检查。最终当前候选是否通过仍以这套绑定后的报告为准，不能仅凭本段文字或模型自述推进。

用户明确授权后，MiniMax 会话 `ses_f5b17f57dffe6vPof8q03oaffG` 与 DeepSeek 会话 `ses_f5b177aa9ffe8NQVAbecDQIkSZ` 对候选 `sha256:b9a8abbe2022fee24eb5d1ce0e615821d6f85887b89159f647d6269ac05b6747` 完成第二轮只读复审，两者仍为 `CHANGES_REQUIRED`。所有结果按失败证据保留；本节列出的四项有效发现已修复并完成 132 项受影响回归。最终评审文件的精确摘要只能在模型结束后由宿主生成和见证，模型无法预先自证。

## 完成前验证与质量结算

`python -m super_dev.cli release readiness` 启动登记计划 `completion-verification-candidate-006`，运行编号 `0370b161473044c9bd535be81483e377`。1801.22 秒后触发 1800 秒运行保护：测试未完成，状态 `BLOCKED`；进程树清理已确认，候选变化为否，文件新增/删除/修改均为 0。该结果不代表代码质量失败，也不能记作 PASS；未擅自延长预算或原样重跑。

随后改用锁定 uv 解释器的同等覆盖计划曾完成 385 项收集、383 项执行、2 项跳过、0 失败/错误，但跨权限候选摘要不一致暴露了上述身份缺陷，因此该次 PASS 不冒充修复后候选证据。修复后任何 fresh-verification 必须与受限/高权限进程共同算出的 canonical 摘要一致；当前正式结果以最新 `.super-dev/extensions/runs/*`、quality、readiness 与 proof-pack 绑定证据为准，本文件不预先声明其结论。

随后重跑合规和产品审查，并在不重复 fresh-verification 的情况下刷新质量与 proof-pack：质量门禁由 75.4 提升到 82.6，但仍因上述 fresh-verification 受阻而 FAIL；proof-pack 为 27/35、`incomplete`。发布就绪报告早于最后一次质量刷新，已被 proof-pack 正确标为 stale；没有再次触发耗时验证来伪造新鲜度。

最终 CrossReview 适用性小修后，质量门禁与四类核心合同定向回归命令退出码为 0，新增失败用例及相关 11 项复跑通过；全生产 Ruff、Black、233 文件 Mypy、compileall 和贡献范围再次通过。当前候选没有再次取得完整 `tests/unit` PASS；正式候选绑定计划即上述 1800 秒 `BLOCKED`，必须保持这一差别。

## 操作异常与恢复

探查不存在的 `ledger resolve --help` 命令时，旧 CLI 把未知参数误解释为需求直达并生成 `ledger-resolve-help` 产物。已按创建时间和精确绝对路径只删除该次生成的 change、ADR、输出、前端、预览与两份状态快照，恢复 `super-dev.yaml` 内容；没有删除用户原有文件。该 UX 缺陷不在本次确认范围，未顺带修复。

## 未验证

- 不同会话源码复审已执行；未携带“会话 ID + 精确评审 JSON 摘要”见证或候选绑定不符时，质量门禁仍会失败关闭。
- Linux/macOS 与远端 CI：未运行。
- 完整 `tests/integration` / `tests/e2e`：未全量运行；只运行了与 CLI 文档确认、恢复和 Spec 绑定直接相关的集成场景。
- 完成前验证未在 1800 秒内完成；质量门禁、release readiness、proof-pack 均未通过，不声明质量或交付闭环。
- 提交、推送、合并、发布、部署、真实运营结果和全局安装：均未授权、未执行。
