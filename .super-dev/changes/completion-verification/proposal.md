# 完成前验证试点变更说明

## Description

在唯一的命令行发布就绪入口 `super-dev release readiness` 中增加默认关闭、显式启用的 pytest 新鲜验证。每次完成声明都重新执行受版本控制的测试计划，把结果绑定当前候选和唯一运行编号，并由 Super Dev Core 作最终发布裁决。

## 已确认依据

- `output/completion-verification-research.md`；
- `output/completion-verification-prd.md`；
- `output/completion-verification-architecture.md`；
- `output/completion-verification-uiux.md`；
- 用户已于 2026-08-25 明确确认最终四份文档；
- Grok Build 最终复审为 `VERDICT=ACCEPT`，两条可选建议也已关闭。

## 目标

1. 项目显式启用后，每次命令行发布就绪检查都执行当前 Python 下登记的 pytest 计划；
2. 测试、JUnit、候选摘要、扩展结果和发布报告使用同一个运行编号（`run_id`）；
3. 测试统计只来自同一份 JUnit，实际执行数（`executed`）只由测试总数减跳过数得到；
4. 普通跳过与预期失败不算实际执行，全部跳过、无测试、超时、取消、证据损坏和候选变化均阻断；
5. Core 固定注入 `-rX`，把非严格意外通过聚合成一条提醒（`NON_STRICT_XPASS`），但不改变 JUnit 基础判定；
6. 扩展只返回证据，发布阶段、Git、部署和外部系统仍由 Core 控制；
7. 为 10 个回放场景和 3 个预先登记的真实候选保留可追踪指标，但最终验收标签只能由用户填写。

## 核心决定

1. 首版只有 `super-dev release readiness` 能触发验证；证据包、质量检查、网页接口和其他调用者继续保持原行为；
2. 发布评估器增加显式调用来源参数，不能仅因复用了同一个评估器就自动执行验证；
3. 首版只允许运行编号（`run_id`），不增加调用编号（`invocation_id`）或第二套同义编号；
4. 项目只配置计划编号、pytest 参数和超时；程序、JUnit、临时目录、缓存关闭、详细摘要和隔离环境由 Core 固定；
5. 已启用但配置无效、环境不支持或无法执行时返回 `BLOCKED`，不能降级为 `NOT_APPLICABLE`；
6. 试点关闭时保留旧发布就绪行为；旧的 `--verify-tests` 只作为未启用试点时的兼容入口，不能与新验证重复执行；
7. 非严格意外通过提醒只解析同次进程的固定简短摘要区，不匹配原因文本、任意日志或历史输出；
8. 等待复核（`unreviewed`）不进入通过率、误阻断率、虚假完成率或 3 个真实候选完成数。
9. Core 把 Git 上探边界（`GIT_CEILING_DIRECTORIES`）固定为本次 pytest 临时目录，防止仓库内临时项目错误继承父仓库；真实项目根目录不受影响。

## 影响范围

- `super_dev/extensions/**`：计划、JUnit 解析、验证提醒、证据、来源锁和服务；
- `super_dev/config/manager.py` 与 `super_dev/config/schema_validator.py`：严格试点配置；
- `super_dev/release_readiness.py`：关键检查和机器可读证据；
- `super_dev/cli_release_quality_mixin.py`：唯一触发点和中文首屏反馈；
- `super_dev/cli_parser_mixin.py`：兼容帮助说明；
- `tests/extensions/**`、发布就绪与 CLI 相关测试；
- `tests/support/run_safe_baseline.py`：在临时用户目录下保留受控的当前 pytest 包可见性；
- `.super-dev/extensions/**`：运行证据和试点指标，不写主工作流状态。

## 不在范围内

- npm、pnpm、Cargo、Go 或任意自定义程序；
- 云端持续集成结果、远程缓存或旧结果复用；
- proof-pack、quality、Web API 或其他第二执行入口；
- 自动修测试、测试先行、系统化调试、独立评审产品化、Idea Forge、Grill 或知识导入；
- 通用插件注册中心、动态发现或大型 pytest 插件；
- 九阶段真实控制变更；
- 图形界面；
- 用户级 Skill、宿主全局配置或凭据修改；
- 自动提交、合并、推送、PR、部署或外部写入。

## 所有权

- 完整开发流程所有者：Super Dev；
- 工作区安排负责人：Codex root；
- 唯一生产写入者：Codex root；
- 独立审查者：Grok Build；
- 最终真实候选验收人：用户；
- 当前分支：`feature/completion-verification`；
- 不创建第二工作区、第二协调器或下级写入者。

## 风险

1. 通用发布评估器被多个入口复用，接线不当会让证据包或网页接口意外运行测试；
2. pytest 参数若不严格限制，可能覆盖 Core 的输出、缓存或隔离设置；
3. JUnit 损坏、重复套件统计或退出码矛盾可能产生错误通过；
4. `-rX` 摘要解析若匹配范围过宽，测试日志中的 `XPASS` 可能形成假提醒；
5. Windows 超时和取消若进程树清理证据不完整，可能遗留子进程；
6. 测试自身修改候选时，必须阻断而不能继续引用运行前身份；
7. 指标若允许事后挑选或由执行者自评，会掩盖误阻断。

## 回滚

- 将 `extensions.enabled` 关闭或从允许列表移除 `fresh-verification`，立即恢复旧发布就绪行为；
- 保留历史证据只读，不自动删除或改写旧结果；
- 不修改主工作流状态、Git 或用户目录；
- 如果移除新实现，旧的 `--verify-tests` 兼容路径仍可独立存在；
- 回滚不修改用户级 Skill、用户配置或远程分支。

## 验收

1. 试点关闭时现有发布就绪、证据包和网页接口行为不变；
2. 试点开启后每次命令行发布就绪调用都产生新运行编号和新证据；
3. 通过、失败、阻断、部分跳过、全部跳过、预期失败、严格与非严格意外通过口径符合确认文档；
4. 所有测试统计来自同一份 JUnit，外部第二份实际执行数被拒绝；
5. 非严格意外通过提醒绑定同次运行和输出摘要，不改变基础判定；
6. 超时、取消和异常后完整进程树停止；
7. 候选变化后旧证据失效，本次结果阻断；
8. 真实用户目录、主工作流状态、Git 和外部系统零变化；
9. Ruff、类型检查、扩展测试、发布就绪测试、CLI 测试和 Windows 安全检查通过；
10. 独立只读复审没有必须修正项。

## 范围演进记录
原始目标保持为完成前新鲜验证试点。用户后来明确授权：活动变更解析、路径安全、当前产物与确认/报告前缀治理；CLI 根项目 `platform=cli`、`frontend=none`、`backend=python` 的范围判定；中国大陆中文 Harness 及根规则、兼容镜像、唯一 Skill 模板和生成副本同步。这些只修复完成判定与用户理解，不扩展系统化排错、第三方方法或九阶段控制。
