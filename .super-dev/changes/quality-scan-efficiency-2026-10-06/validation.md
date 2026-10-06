# 质量扫描效率整改验证记录

- 工作项：`quality-scan-efficiency-2026-10-06`。
- 日期：2026-10-06。
- 状态：本批定向验收通过（`PASS`）；不等同整仓发布就绪。
- 实施验收范围：六个生产文件、三个新增测试文件及本工作项材料；验收时不提交、不发布、不更新根活动工作项。后续本地提交的追加授权见文末。
- 本记录是宿主自检，不是独立审查或整仓发布就绪证明。

## 1. 环境与授权

用户先明确要求按最小建议实施，再通过本会话计划确认三份核心文档及范围。基线为 `a93c12108835508d9b01ff038c537a2a6f9e1976`，分支保持 `ocx/target-knowledge-patches-2026-10-05`。

使用 Windows 10 19045 与项目 `.venv/Scripts/python.exe`（Python 3.13.12），不是初始诊断用的系统 Python 3.14.3。pytest 9.0.3、Ruff 0.15.11、Black 26.3.1、Mypy 1.20.1、build 1.6.0；首次构建发现缺少 `wheel`，仅向项目虚拟环境补装 wheel 0.48.0，未修改依赖声明或系统安装。

根 `.super-dev/SESSION_BRIEF.md` 与 `workflow-state.json` 仍属于旧工作项 `super-dev-2-6-reliability` 的已部署状态。本批使用经确认的独立维护档案，不冒用旧发布确认，不执行会覆盖旧报告的根目录正式质量命令。

## 2. 修改与验收对应

| 需求 | 实现与验证 |
| --- | --- |
| SCAN-001 保持范围并提前剪枝 | 三种消费者各自保留原忽略/后缀/大小写；共同清单只剪掉忽略集合交集。新旧合成树集合对照，包含根源码、隐藏目录、`.nuxt`、`coverage`、`.egg-info` 与大小写差异。 |
| SCAN-002 同次复用 | 规则、合规 `inspect/run`、报告质量建议共享调用内清单；真实 CLI 观察到一次发现加一次结束复核。下一次 `check()` 使用新对象，渲染不再重新扫描或使用调用者的另一个工作目录。 |
| SCAN-003 必要文档 | 当前规格子树和明确输出目录独立枚举，隐藏文档保留；PRD、架构、UIUX、依赖清单通过受控读取。原工作项/前缀绑定回归保持。 |
| SCAN-004 不完整受阻 | 源码、文档、目录不可读均明确抛出扫描错误；规则和质量入口不能通过。真实 CLI 输出受阻原因且不发布成功合规报告，未用高分抵消。 |
| SCAN-005 新鲜度与安全 | 中途增删、普通及大小写重命名、同大小同时间内容修改、配置修改、必要文档新增、跨项目复用均有测试；最终一致性复核前不写报告，`persist=False` 不写报告；真实 Windows 目录连接点拒绝跟随。 |
| SCAN-006 原门禁保持 | 阈值、既有业务规则权重、时限、根配置与流程状态不变。增加零权重但必需的扫描完整性失败，不给正常业务规则加分。 |

报告缓冲仅在本次调用内提供待发布报告，保留原证据身份核对。它不是跨调用质量结论缓存。原磁盘报告仍按原规则检查有效性。没有扩展公共状态枚举。

## 3. 基线、红灯与中间失败

这些是迭代证据，不能拿来替代最终版本验证：

1. 修改前：合规身份、架构否定与规则三个原测试文件 **108 项通过，14.60 秒**。
2. 初始剪枝观察桩只监视 `os.scandir`，被 Python 3.13 pathlib 的内部引用绕过；增加对原 `Path.rglob` 产出的观察后，七个目标用例均真实失败。不是导入失败充当红灯。
3. 第一轮接入后，同组原测试及新增用例 **115 项通过，14.00 秒**；后续来源清单与质量门组 **97 项通过、1 项跳过，33.99 秒**。
4. 单元与集成测试同名导致一次 pytest 收集失败；将本批集成文件从 `test_quality_scan_inventory.py` 改为 `test_quality_scan_entrypoints.py`，没有删除原测试或修改导入模式求通过。
5. 较早定向回归 **4 项失败、215 项通过、1 项跳过，110.19 秒**，保留于 `output/quality-scan-efficiency-2026-10-06/focused.xml`：
   - 两个尾斜杠 glob 用例：修正新帮助器，保持旧调用先经 `Path` 去掉尾分隔符的语义。
   - PRD 夹具原期望 1 条，旧未绑定选材会被两个原模式重复匹配；保留产品旧行为，将夹具改为 2 条，不顺便修订需求解析。
   - CLI 原观察到 10 次来源发现；修复报告阶段额外扫描，没有放宽两次调用的断言或关闭质量顾问。
6. 报告调用边界复测 **38 项通过、1 项跳过，54.30 秒**，见 `invocation-recheck.xml`。
7. 必要文档读取测试最初四项全部失败，见 `doc-read-red.xml`：三种文档异常没有转换为扫描错误，架构依赖读错误被吞掉。已将这些读取接入同一完整性边界。
8. 一轮完整定向复核 **230 项通过、1 项跳过，205.42 秒**；顾问与筛选后的原 CLI/Web 消费者 **42 项通过、318 项未选中，239.46 秒**。这是最终 Windows 大小写修复之前的版本，分别保留于 `focused-final.xml` 与 `consumers-final.xml`。
9. 最后自检补出 Windows 仅改变文件名大小写的真实失败，见 `case-rename-red.xml`：`WindowsPath` 集合相等会折叠大小写。现改为比较实际路径字符串，保留原大小写选择语义，并重新跑最终验证。
10. 首次构建因环境未装 `wheel` 失败；补齐项目环境后构建通过。最后源码修订后仍重新构建，不交付之前版本的包。
11. 初次规格格式检查缺 `ADDED Requirements`，并提示缺 plan/checklist；已修复。最后一个建议为 plan 缺 Context 章节，已补标题，未改变计划内容或验收标准。
12. 最后一轮长串行命令被宿主 900 秒后台时限停止，原始输出保留于 `host-timeout-final.log`，该次未完成不计为通过。进程检查未发现遗留的本次 pytest 进程；停止位置附近的独立用例重新执行通过，3.90 秒，未复现单用例卡死。随后拆成来源/规则组、质量门组和消费者组，保留每例 120 秒限制；不改产品运行时限，也不把“重跑通过”解释成已查明宿主超时的根因。

## 4. 最终版本命令与结果

最后生产修改为 Windows 大小写重命名保护。以下最后一轮使用同一份冻结源码，不在测试运行中编辑生产或测试文件。原始 XML、日志及源码摘要集中在 `output/quality-scan-efficiency-2026-10-06/`。

### 4.1 定向功能回归

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -B -m pytest tests/unit/test_source_inventory.py tests/unit/test_quality_scan_inventory.py tests/integration/test_quality_scan_entrypoints.py tests/unit/test_compliance_evidence_identity.py tests/unit/test_architecture_drift_negation.py tests/unit/test_validation_rules.py -q -p no:cacheprovider --timeout=120 --tb=short --durations=10 --junitxml=output/quality-scan-efficiency-2026-10-06/source-consumers-final.xml
```

结果：通过（`PASS`），**164 项通过、1 项跳过，78.13 秒**。

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -B -m pytest tests/unit/test_quality_gate.py -vv -p no:cacheprovider --timeout=120 --tb=short --durations=10 --junitxml=output/quality-scan-efficiency-2026-10-06/quality-gate-final.xml
```

结果：通过（`PASS`），**67 项通过，112.98 秒**。两组完整覆盖原定的七个测试文件，没有因宿主超时删选其中用例。

### 4.2 真实消费者与质量建议回归

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -B -m pytest tests/unit/test_quality_advisor.py tests/integration/test_cli.py tests/integration/test_web_api.py -q -p no:cacheprovider --timeout=120 --tb=short -k 'quality or compliance or release_readiness or proof_pack' --junitxml=output/quality-scan-efficiency-2026-10-06/consumers-final-v2.xml
```

结果：通过（`PASS`），**42 项通过、318 项未选中，158.64 秒**。有 1 条既有 TestClient/httpx 弃用提示。过滤条件保留；不是整个 CLI/Web 测试套件。来源组、质量门组、消费者组与贡献政策组共 **304 项通过、1 项条件跳过**，不把诊断重跑重复计数。

### 4.3 贡献政策单测

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -B -m pytest tests/unit/test_contribution_policy.py -q -p no:cacheprovider --timeout=120 --tb=short --junitxml=output/quality-scan-efficiency-2026-10-06/contribution-final.xml
```

结果：通过（`PASS`），**31 项通过，11.25 秒**。

### 4.4 静态、类型与构建

- Ruff：整个 `super_dev/` 和三个新增测试文件，日志 `lint-final-v2.log`。
- Black：六个生产文件和三个新增测试文件，最终执行 `--check`，不自动格式化无关文件。
- Mypy：整个 `super_dev/`，日志 `typecheck-final-v2.log`。
- Python 构建：`python -m build --no-isolation --outdir output/quality-scan-efficiency-2026-10-06/build-final`，日志 `build-final-v2.log`。
- 构建包仅落在本轮输出目录，没有安装到系统、上传或发布。

结果：通过（`PASS`）。Ruff 无错误，Black 九个文件均无需变更，Mypy **237 个源文件无类型错误**；成功生成 `super_dev-2.6.0.tar.gz` 和 `super_dev-2.6.0-py3-none-any.whl`，包含新的 `source_inventory.py`。保留原始构建日志中的禁用字节码提示。

### 4.5 本地治理检查

最后核对本工作项 `spec validate --verbose`、`scripts/check_contribution_policy.py --base a93c12108835508d9b01ff038c537a2a6f9e1976`、`scripts/sync_super_dev_skills.py`，仅验证，不同步写入用户级 Skill，不改变根工作流绑定。

结果：通过（`PASS`）。规格格式无警告；贡献资料与范围检查通过；`SUPER_DEV_SKILLS_IN_SYNC=yes`。日志分别为 `spec-final.log`、`policy-final.log`、`skills-final.log`。这些机械检查不代替维护者语义审查或发布批准。

## 5. 性能与资源对照

可复现脚本：`output/quality-scan-efficiency-2026-10-06/benchmark_scan.py`。合成树含 360 个保留文件、6,000 个排除文件，比较三个消费者各三次查询；旧实现九次根遍历，新实现一次发现加一次结束复核。三轮交错顺序，全部结果保留，均启用 `tracemalloc`，不清理系统文件缓存。

最后修订前的一组结果已保留为 `discovery-benchmark-initial.json`，不作为最后源码的性能数据。最后结果写入 `discovery-benchmark.json`；完整源码身份、正文读取、质量顾问其他分析和测试子进程不在这个微基准内，不能由此推导整个质量流程的加速倍数。

真实工作区旧扫描有 30 秒诊断上限；若未完成，只记录未完成和已访问条目，不声称其最终文件集合等价，也不算精确加速比。不会取消正式流程时限来换取结果。

最终数据（同一 Python 3.13.12，测量时未并行运行本会话测试/构建）：

| 项目 | 原递归后过滤 | 调用内清单 |
| --- | ---: | ---: |
| 合成树第 1 轮 | 21.772 秒 | 1.703 秒 |
| 合成树第 2 轮 | 19.188 秒 | 1.362 秒 |
| 合成树第 3 轮 | 17.958 秒 | 1.478 秒 |
| 合成树耗时中位数 | **19.188 秒** | **1.478 秒** |
| 九次消费者查询的根发现/复核次数 | 9 | 2 |
| Python 分配跟踪峰值（各轮约值） | 2.07 MiB | 0.80 MiB |

三轮所有消费者的文件集合完全一致；该文件发现微基准耗时约缩短 92.3%，不是全量质量命令的加速承诺。内存是 `tracemalloc` 的 Python 分配跟踪峰值，不是系统进程常驻内存。

真实工作区：原模式 **30.000 秒仍未完成**，已枚举 83,100 个条目；新路径 **2.653 秒完成发现与复核**，保留树含 1,147 个文件和 294 个目录。因为原模式没有完成，真实工作区的最终集合等价与完整加速比均不作结论。完整原始数据与全部轮次见 `discovery-benchmark.json`，复现脚本和日志均保留。

## 6. 明确保留的边界与未验证项

- 执行的是本批定向回归与真实调用夹具，不是整仓所有测试、正式全量质量验收或发布就绪检查。
- 本机不能创建目录符号链接的测试保留原条件跳过；没有把它改成通过。Windows 目录连接点是独立的真实测试，不等同 Linux/macOS 符号链接验证。
- 没有执行 Linux、macOS 或 Python 3.10/3.11/3.12 矩阵。Python 3.10 目标语法和类型配置通过不代表这些解释器实际运行过。
- 来源清单不是原子文件系统快照；处理已观察到的成员和内容变化，不承诺任意恶意竞态都能原子隔离。多报告落盘也不是文件系统事务。
- 未修改通用证据身份算法。非 Git 项目身份回退、规则 `file_exists` 和顾问的其他分析仍可使用原有遍历。正则检查在仅有被排除匹配时保留存在性探测，避免将旧失败变成通过；不宣称所有目录访问已经消除。
- 应检链接/重解析点采取明确受阻，而不是越界读取或静默省略。大型源码树仍须枚举和读取，不能承诺瞬时扫描。
- Starlette TestClient/httpx 弃用提示属于现有测试依赖提示，本批不换库。构建的禁用字节码提示不影响 wheel/sdist 生成。
- 没有修改其他会话的知识、提示、发布就绪、证据包与 Web GET 边界问题；也不把其他会话旧报告当作本批验证证据。

## 7. 交付范围与保护

生产文件：`source_inventory.py`、`spec_compliance.py`、`architecture_drift.py`、`uiux_compliance.py`、`validation_rules.py`、`quality_gate.py`，均在 `super_dev/reviewers/` 下。

测试文件：`tests/unit/test_source_inventory.py`、`tests/unit/test_quality_scan_inventory.py`、`tests/integration/test_quality_scan_entrypoints.py`。原有测试只运行，未删除或放宽旧断言。

最终已核对 git 差异、九份源码/测试摘要和三份受保护状态文件：验证期间均未再改变；六个生产模块在最终 wheel 中的内容摘要与被测源码完全一致。`git diff --check` 通过，未改其他任务文件。本工作项 tasks/checklist 已登记完成；根状态保持原样。实施验收交接时无提交、推送、合并、发布或部署。

## 8. 后续提交授权

实施交接后，用户于本会话追加要求“提交，并检查是否能够合并至main”。本次允许本批本地提交和主分支合并条件检查，不包括其他任务差异，也不授权推送、实际合并或发布。以上验收仍对应原冻结源码；提交后的检查将另行核对已提交树，不能默认继承工作区中其他未提交改动的验证结果。
