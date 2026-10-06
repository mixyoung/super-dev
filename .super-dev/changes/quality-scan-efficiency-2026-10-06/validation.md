# 质量扫描效率整改验证记录

- 工作项：`quality-scan-efficiency-2026-10-06`。
- 日期：2026-10-06。
- 状态：第 1–8 节保留首轮本地定向验收历史；Windows CI 路径返工及当前结果见第 9 节。不等同整仓发布就绪。
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

## 9. Windows CI 路径一致性返工

### 9.1 授权与真实失败

后续用户另行授权推送、创建 PR 及切换已有凭证，本批提交 `00fa50bb559a26143085e1be74004b112d164672` 已进入 [mixyoung/super-dev#22](https://github.com/mixyoung/super-dev/pull/22)。未开启自动合并。

[CI 运行记录](https://github.com/mixyoung/super-dev/actions/runs/37442875626) 中，Windows Python 3.10、3.11、3.12 各有 25 项 `test_release_readiness.py` 用例失败，`timed_out=false`；项目根由 `resolve()` 转为完整路径，而 `document_paths()` 的 `abspath()` 保留 `RUNNER~1` 短路径，造成项目内目录被误报为项目外。用户随后明确授权“按建议执行”，允许在当前扫描模块内统一路径并验证，不改变系统短文件名配置、门禁或其他任务。

### 9.2 红灯与修复边界

- 新增真实 Windows 8.3 短路径、相对路径索引及链接保护回归，旧实现 **13 项失败、7 项通过**，见 `path-normalization-red.xml/.log`。
- 补齐活动工作项目录后再次验证规格存在/缺失两种状态，三类原消费者 **6 项失败**，见 `path-consumer-red.xml/.log`。这一步确保覆盖 CI 的 `_active_change_spec_files()`，不只验证未绑定 PRD 回退。
- 使用 `git archive 00fa50b` 导出独立副本，在仅影响测试子进程的 `TEMP/TMP` 中传入真实短路径；首次原提交测试为 **25 项失败、6 项通过，104.22 秒**，见 `path-release-original-red.xml/.log`。补齐父级 Git 隔离后再次运行同一原测试，仍为 **25 项失败、6 项通过，54.02 秒**，见 `path-release-original-isolated-red.xml/.log`。两次原始堆栈与 CI 相同，都是文档路径比较失败，而非测试收集或环境失败。
- 生产只修改 `super_dev/reviewers/source_inventory.py`；测试只修改 `tests/unit/test_source_inventory.py`。先逐层检查原始组件，再统一规范化文件、文档、固定模式前缀、依赖与报告索引；既有链接、越界、大小写变动和发布前复核仍生效。
- 补出待发布报告父目录在检查期间变为连接点的反例；所有报告的路径复核先于发布，不将排队时间当成最终路径安全证明。
- 无生产 Windows API 分支、无路径全小写、无 `RUNNER~1` 特判；保留原 glob 匹配和项目根的字面值语义。

### 9.3 本次验证隔离

本机工作区含其他任务的 `release_readiness.py`、`proof_pack.py` 与测试夹具修改，均保留。隔离副本仅叠加上述两个文件，其余 1,263 个归档文件保持提交内容；原发布就绪测试及其依赖没有为了求绿而改写。`path-verification-inputs.json` 保存基线、叠加文件摘要、归档文件摘要、受保护根状态及其他任务文件摘要。

首次修复后矩阵运行发现，输出目录内的临时项目仍可向上发现真实仓库；这会干扰本应为非 Git 项目的证据身份。该批次主动停止，确认无遗留测试进程，已有日志保留且不计通过。随后仅在测试子进程中设置 `GIT_CEILING_DIRECTORIES`，启动时断言临时目录与归档目录都不能继承父级 Git 仓库；测试自己初始化的仓库仍可正常使用。先重跑上段原提交红灯，再在相同条件下验证修复。没有通过关闭产品 Git 能力或改写测试断言求绿。

测试通过 `run_path_snapshot_tests.py` 执行，每组都校验实际导入位置和 Git 隔离边界，并记录原生短 `TEMP` 路径；不修改全局环境。每例保留 120 秒限制，测试子进程整体保留 1,200 秒限制。Python 3.10.19 在本工作项输出目录内安装，并使用 `--no-bin --no-registry`，不改变系统默认解释器；3.11.9 与 3.12.12 复用已安装解释器。三个测试虚拟环境和依赖缓存均位于本工作项输出目录。

### 9.4 当前验证状态

工作区回归为 **183 项通过、1 项条件跳过，23.45 秒**，见 `path-source-regression.xml`。最终矩阵使用相同的隔离提交副本和真实短路径环境：

| 环境 | 适用范围 | 结果 | pytest 耗时 |
| --- | --- | --- | --- |
| Windows / Python 3.10.19 | 来源清单、原扫描消费者、完整发布就绪文件及新 CLI 入口 | 226 项通过、1 项条件跳过 | 606.93 秒 |
| Windows / Python 3.11.9 | 同上 | 226 项通过、1 项条件跳过 | 599.20 秒 |
| Windows / Python 3.12.12 | 同上 | 226 项通过、1 项条件跳过 | 620.06 秒 |
| Windows / Python 3.13.12 | 相同扫描与新入口组 | 195 项通过、1 项条件跳过 | 95.45 秒 |
| Windows / Python 3.13.12 | 原完整发布就绪文件 | 31 项通过 | 487.99 秒 |
| Windows / Python 3.13.12 | 原质量门、质量顾问与筛选后的 CLI/Web | 109 项通过；318 项未选中 | 343.59 秒 |
| Windows / Python 3.13.12 | 贡献政策 | 31 项通过 | 10.11 秒 |

每个版本的原 `test_release_readiness.py` 均为 **31 项全部通过**，包括原 CI 的 25 项失败。三个较低版本日志为 `path-target-py310-isolated`、`path-target-py311-isolated`、`path-target-py312-isolated`；3.13 日志为 `path-source-entrypoints-py313-isolated`、`path-release-py313-isolated`。每组均保留 `.xml`、`.log` 与 `-command.json`，不把重复执行计为新增测试覆盖。矩阵并行运行，耗时不能作为解释器或新旧实现的性能对照。

唯一条件跳过为既有普通目录符号链接测试：本机创建操作返回 `OSError`。原生短路径测试没有跳过，Windows 目录连接点与 `link/..` 的实际反例也没有跳过。3.10–3.12 使用 pytest 9.1.1，3.13 使用 pytest 9.0.3；完整版本记录在 `path-environments.json`。

隔离代码的 Ruff、Black、237 文件 Mypy 通过；当前安装版本的 Ruff 0.16.10 与 Mypy 2.4.0 的 CI 类型门复核也通过。Bandit 中/高严重级别均为 0，另有 155 项低严重级别发现；不能称为零风险。wheel/sdist 构建通过，六个评审模块在 wheel 中的摘要与被测代码一致，详见 `path-snapshot-*.log`、`path-ci-type-gate.log`、`path-current-ruff.log` 与 `path-wheel-binding.json`。

本工作项规格格式、限定本批文件集合的贡献记录检查、仓库 Skill 同步检查通过，见 `path-spec.log`、`path-contribution-scope.log` 与 `path-skill-sync.log`。补充回归原始证据为 `path-quality-entrypoints-py313-isolated.xml/.log` 与 `path-policy-py313-isolated.xml/.log`。CLI/Web 的筛选条件仍为 `quality or compliance or release_readiness or proof_pack`，不是整个集成测试目录；保留 1 条既有 Starlette/TestClient 弃用提示，不通过更换依赖或删除测试求绿。

3.13 四组在测试标识去重后合计 **366 项通过、1 项条件跳过**，与各较低版本的 226 项不累加成不同案例数。汇总与源文件绑定见 `path-final-verification.json`。所有功能、静态和构建验证使用同一修复代码，未在验证运行期间修改生产或测试源码。

### 9.5 重新测量的开销与收益

所有本会话测试和构建结束后，使用同一 Python 3.13.12、同一合成树（360 个保留文件、6,000 个排除文件）交错执行三轮；两侧都启用 `tracemalloc`，未清空文件系统缓存，完整保留所有轮次。

- 对比本次路径返工之前的 `00fa50b`：发现加复核耗时中位数 **1.085 秒 → 1.751 秒**，增加约 **0.666 秒（61.4%）**；两者都是两次根发现/复核，所有消费者集合相同。新增的逐层检查和规范化确实有开销，不把正确性修复说成进一步提速。见 `path-discovery-benchmark.json` 及 `benchmark_path_normalization.py`。
- 同轮对比最初“递归后过滤”的算法：三轮耗时分别为 **15.601/1.781、15.776/1.790、16.795/1.840 秒**（旧算法/当前代码）。中位数 **15.776 秒 → 1.790 秒**，文件发现部分约减少 **88.7%**；根发现/复核次数仍是 **9 → 2**，每轮集合相同。Python 分配跟踪峰值约 **2.07 MiB → 0.88 MiB**。见 `path-legacy-discovery-benchmark.json`。
- 真实工作区诊断：旧算法 **30 秒未完成**，已访问 64,152 个条目；当前代码 **6.991 秒**完成发现与复核，保留 1,147 个文件和 294 个目录。旧算法没有完成，因此不能证明其最终集合相同，也不能给出完整加速比。

以上只测文件发现与成员复核，不含正文、证据身份、质量建议及测试进程，不代表整个质量流程的耗时。保留路径安全与原时限，不为改善微基准删除检查。

### 9.6 最终边界与资源清理

- 当前源码和测试摘要与冻结输入一致，原归档除本批两个叠加文件外全部一致；根配置、根工作流状态及其他任务文件均经摘要复核未变。
- 已清理本轮归档副本、三个隔离测试环境、项目内临时 Python 3.10、依赖缓存及主动停止批次留下的五个临时目录。清理前核对原归档摘要、允许生成项与停止批次日志中的目录归属，未清理其他输出。原失败/成功日志、命令、环境信息、脚本、源码摘要及 wheel/sdist 均保留，见 `path-cleanup.json`。
- 这是宿主自检和本地 Windows 定向回归；没有重跑整仓完整 CI、Linux/macOS、全部 Windows baseline 或正式发布验收。多报告写入不是原子事务，任意恶意文件系统竞态也不在本次保证内。
- 路径返工验收交接时，没有新提交、推送、合并或发布。当时读取 PR 状态，远端仍为原提交，11 项 CI 通过、3 项 Windows 检查失败，合并受阻（`BLOCKED`）；本地修复通过不替代修复进入 PR 后的必需 CI。未开启自动修复或自动合并。

### 9.7 路径修复的提交与推送授权

用户在验收交接后明确要求“提交并推送，更新现有 PR”。本轮范围固定为上述已验证的路径修复、测试及对应工作项记录，共七个已跟踪文件；保留其他任务的未提交改动。提交前再次按 `path-verification-inputs.json` 核对源码与测试摘要、其他任务文件和根状态，均与最终验证时一致，因此复用相同源码的有效测试、类型与构建证据，不重跑无变化的长批次。

授权目标为既有分支 `ocx/target-knowledge-patches-2026-10-05` 和 [mixyoung/super-dev#22](https://github.com/mixyoung/super-dev/pull/22)，基础分支仍为 `main`。只提交、普通推送并更新 PR 说明，不强推、不新建 PR、不执行合并、发布或部署，不开启自动合并。实际提交和远端写入结果以 Git 与 GitHub 回执为准，新提交仍须接受原必需 CI。
