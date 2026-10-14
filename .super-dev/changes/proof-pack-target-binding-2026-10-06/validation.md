# P1 证据包目标绑定验证记录

## 1. 范围与授权

用户于 2026-10-06 10:34:37 确认三份精简核心文档并授权 P1 实施。维护工作项 `proof-pack-target-binding-2026-10-06`，沿用当前分支 `ocx/target-knowledge-patches-2026-10-05`，基线提交 `a93c12108835508d9b01ff038c537a2a6f9e1976`。

本次只有本会话写生产代码；无多代理或模型观察。只改已确认的证据包规格项与测试/维护记录；无 UI 或依赖变更。所有发布消费者测试使用隔离项目，不对本仓库重跑发布就绪或证据包，不提交/推送/发布。

## 2. 实施前保护

[基线保护摘要](../../../output/proof-pack-target-binding-2026-10-06/implementation/baseline-protection.json)冻结 24 个已有改动文件、八项旧发布保护文件及证据包生产文件修改前摘要。原 A/B 与 P2 证据保持历史归属，不作为本次执行结果。

## 3. 当前实现与核心结果

生产差异只有 `proof_pack.py` 的必要 import 和 `_spec_quality_artifact()`：无有效目标复用身份诊断，返回既有 pending；有目标调用指定评估，不查 latest、不按名称免检。原结构、状态集合、聚合和阈值不变。

| 检查 | 实际结果 | 原始证据 |
| --- | --- | --- |
| 20 项新测试，修改前 | 失败（`FAIL`）：17 失败、3 通过，25.61 秒；两个真实 GET 的规格项亦错选 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-red.txt)、[JUnit](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-red.xml) |
| 首次修复后完整新测试 | 失败（`FAIL`）：18 通过、2 失败，26.55 秒；目标/结构已对齐，实际只读断言失败 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-green.txt)、[JUnit](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-green.xml) |
| P1 与原 readiness 目标核心测试 | 通过（`PASS`）：35 通过，5.04 秒；含 P1 18 项与原 17 项 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-core-green.txt)、[JUnit](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-core-green.xml) |
| Ruff / Black / Mypy | 通过（`PASS`）：无 lint 错误、238 文件格式不变、236 源文件无类型错误 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-static.txt) |
| 临时副本构建 | 通过（`PASS`）：sdist/wheel 成功；原构建依赖、项目 venv 不变，制品未发布 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-build.txt)、[摘要](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-build-artifacts.json) |
| 本地 CLI 定向维护 Spec 初次校验 | 通过（`PASS`），2 项格式警告；Description 与 Plan 标题随后按原解析器补齐，不改检查器 | [原始日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-spec-validate.txt) |

## 4. 质量受阻：真实 Web GET 副作用

当前阶段为质量复核，整体受阻（`BLOCKED`）；没有将维护工作项标成 completed 或宣称全部适用验证通过。

两条 GET 目标与结构断言均通过，后续目录断言失败；另行真实隔离诊断还确认新增报告文件，响应的 persisted=False 并不能证明没有落盘。调用栈指向 FeatureChecklistBuilder 的构造器，以及其他 scope/framework/operational 和嵌套治理报告路径，均不是本次规格项修复新增。

[目录调用栈](../../../output/proof-pack-target-binding-2026-10-06/implementation/get-directory-diagnosis.json)、[文件差异](../../../output/proof-pack-target-binding-2026-10-06/implementation/get-file-diagnosis.json)、[既有来源复核](../../../output/proof-pack-target-binding-2026-10-06/implementation/get-side-effect-origin-check.json)、[受阻说明](../../../output/proof-pack-target-binding-2026-10-06/readonly-boundary-blocker.md)。没有删断言、跳过/xfail、预生成输出或扩改其他生产方法；该受阻已于 2026-10-09 经用户确认范围后解决，见第 6 节。

## 5. 当前同一次适用回归与保护

| 检查 | 实际结果 | 原始证据 |
| --- | --- | --- |
| 当前同一次适用回归 | 失败（`FAIL`）：365 通过、2 失败，471.25 秒，367 个不同用例；仅两项新真实 GET 文件系统断言失败，无错误或跳过，保留一项既有 Starlette 弃用警告 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-current-regression.txt)、[JUnit](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-current-regression.xml)、[去重与失败核对](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-regression-summary.json) |
| 源码连续性 | 通过（`PASS`）：755 项源码、测试、知识及依赖声明在运行前后及复核时摘要一致 | [命令与输入摘要](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-current-regression-inputs.json)、[运行后核对](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-current-regression-source-check.json) |
| 贡献、Skill 与差异 | 通过（`PASS`）：按原基线检查，SUPER_DEV_SKILLS_IN_SYNC=yes；没有同步写入或用户安装，git diff --check 通过 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-contribution-and-skill.txt) |
| 定向维护 Spec 最终校验 | 通过（`PASS`）：补齐原解析器所需的 Description/Plan 标题后无警告，不改验证器 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-spec-validate-final.txt) |
| 生产范围及模型兼容 | 通过（`PASS`）：语法树确认仅 _spec_quality_artifact 改变，返回模型、聚合及显式 latest 验证器保持 | [范围复核](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-production-scope-check.json) |
| 原改动与发布保护 | 通过（`PASS`）：24 项已有改动、八项旧发布保护文件和 HEAD 均未变；不对真实仓库评估发布 | [最终保护](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-final-protection.json) |

367 项覆盖原 309 个适用用例、新 P1 20 项、既有 Web 写边界、身份/产物工具与交付事实回归。既有消费者全部通过，未修改其夹具或断言。35 项核心绿灯包含于该回归，不能相加；原 308 累计和 P2 309 项不作为本次通过证明。

更新最终维护记录后再次复核贡献、Skill、源码与保护摘要及本地证据链接，均通过（`PASS`），但质量状态仍受阻（`BLOCKED`）：[最终命令](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-final-record-check.txt)、[最终记录核对](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-final-source-and-record-check.json)、[新增证据摘要索引](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-evidence-index.json)。

一次性语法树核验脚本首轮少一个引号，语法错误且未写出结果；[原始失败](../../../output/proof-pack-target-binding-2026-10-06/implementation/p1-scope-helper-first-failure.txt)保留，修正后核验通过，不是产品红灯或新的发布评估。

## 6. 2026-10-09 只读补全：真实 GET 不再落盘（当前最终状态）

用户于 2026-10-09 确认保留 GET 只读入口，按“四处落点、未落盘留空”方案完成修复。生产差异：[feature_checklist.py](../../../super_dev/analyzer/feature_checklist.py) 目录改为仅在 `write()` 创建；[operational_harness.py](../../../super_dev/operational_harness.py) `build()` 增加 `write_reports` 参数；[release_readiness.py](../../../super_dev/release_readiness.py) operational harness 检查传递 `self.persist_artifacts`；[proof_pack.py](../../../super_dev/proof_pack.py) 六处产物按 `persist_artifacts` 守卫写盘，未落盘时 `path`/`markdown` 留空。默认值与 `persist=True` 的 POST/CLI 行为不变。

| 检查 | 实际结果 | 原始证据 |
| --- | --- | --- |
| 核心与既有消费者（含两项原失败 GET 只读测试、完整 Web API、证据包增强） | 通过（`PASS`）：172 通过，368.88 秒 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-core-green.txt) |
| 新基线 `14d155d` 上同一次适用回归（含 PR #22 质量扫描测试） | 453 通过、1 失败、1 跳过，798.33 秒；失败为既有测试桩不接收新 `write_reports` 关键字的 `TypeError`，跳过为 Windows 无法创建目录符号链接的环境性跳过（PR #22 新增用例，与本修复无关） | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-regression.txt)、[JUnit](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-regression.xml)、[输入摘要](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-regression-inputs.json) |
| 桩签名适配后重跑 readiness 增强测试 | 通过（`PASS`）：31 通过，292.08 秒；仅将 `build` 桩改为 `lambda self, **kwargs`，断言未放宽 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-enhanced-rerun.txt)、[JUnit](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-enhanced-rerun.xml) |
| Ruff / Black / Mypy | 通过（`PASS`）：无 lint 错误、237 文件格式不变、237 源文件无类型错误 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-static-contribution.txt) |
| 贡献检查（基线 `HEAD=14d155d`）、Skill 同步、差异 | 通过（`PASS`）：未同步写入或用户安装，`git diff --check` 通过 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-static-contribution.txt) |
| 临时副本构建 | 通过（`PASS`）：sdist/wheel 成功，制品未发布 | [日志](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-build.txt)、[摘要](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-build-artifacts.json) |
| 源码连续性 | 通过（`PASS`）：回归运行前后源码摘要一致 | [核对](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-regression-source-check.json) |

两项原失败断言（GET 不建目录、不改输入）转绿，未删除、未跳过、未预生成输出。455 个不同用例中 454 通过、1 项环境性跳过；适用回归不是全仓库 pytest，历史 367 项/309 项/308 项记录分别属于其当时版本。

收口后最终复核：贡献范围（基线 `HEAD`）、Skill 同步、`git diff --check`、冻结范围外无文件漂移、八项发布保护摘要及全部本地证据链接均通过（`PASS`）：[最终命令](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-final-record-check-final.txt)、[最终汇总](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-summary.json)、[证据摘要索引](../../../output/proof-pack-target-binding-2026-10-06/implementation/readonly-fix-evidence-index.json)。首轮范围核对脚本曾因误把本批合法修改的四个生产文件计为漂移而中断，修正排除逻辑后通过；一次贡献记录因说明段落误放在改动范围节被检查器拒绝，移至取舍节后通过，均不改检查器或标尺。

## 7. 交付状态与未验证

目标绑定修复与 GET 只读补全均已交付并通过适用验证，质量收口完成，工作项转为 completed。受限说明：仅 Windows 本机、Python 3.13.12 环境；未验证其他 OS、实际 Python 3.10、真实 UI、负载或模型行为；`test_directory_link_is_not_followed` 在本机环境性跳过。真实仓库发布验收未重跑，旧状态/会话说明/配置及历史 65 分报告未改；未提交、推送、合并、发布或部署，维护者最终语义审查与发布许可仍未发生。
