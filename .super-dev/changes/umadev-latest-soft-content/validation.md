# U7—U14 验证记录

> 2026-09-06。用户确认三文档后实施。结果：本批适配与定向验证通过（`PASS`）；不是全项目发布通过。

## 已落实范围

8 份已有知识条目、4 个既有专家定义、标准 Skill 唯一模板与 4 份生成副本，以及现有 Spec 文字模板。来源与取舍见 [吸纳映射](../../../docs/UMADEV_SOFT_CONTENT_ADOPTION.md)。没有新依赖、命令、角色调度、状态、评分或平台执行器。

静态语法树对照 HEAD `4911930`：仅改变 `skill_template.py` 的 `_section_evidence_and_handoff_guidance`、`_section_error_recovery` 和 `specs/generator.py` 的 `_render_spec_template`、`_render_plan_template`、`_render_checklist_template`。其他方法不变，SEEAI 在 codex、claude-code、generic 三个渲染输入下与 HEAD 逐字相同。

4 份知识文件主标题原为作者署名，导致相关中文查询未命中；改为实际主题并保留署名后，原检索路径可达。未改检索算法。空上下文/验证表不填假路径、版本或完成记录，既有用户文件仍不会被重新生成覆盖。

## 自动检查

环境：Windows；项目 `.venv/Scripts/python.exe`，Python 3.13.12。

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_umadev_latest_soft_content.py tests/unit/test_umadev_soft_content.py tests/unit/test_method_absorption.py tests/unit/test_document_generator_enhanced.py tests/unit/test_super_dev_skill_contracts.py tests/unit/test_expert_service.py tests/unit/test_engine_knowledge.py tests/unit/test_workflow_contract.py tests/unit/test_workflow_guard_active_change.py tests/unit/test_new_modules.py::TestSkillTemplate tests/unit/test_new_modules.py::TestExpertLoader tests/unit/test_spec_manager.py tests/unit/test_spec_manager_enhanced.py -q -p no:cacheprovider --junitxml=output/umadev-latest-soft-content-pytest.xml
```

实际结果：**200 passed**，0 failed/errors/skipped。终端耗时 23.28 秒；JUnit 23.144 秒。包括实际生成、既有文件保留、已有文档未确认时拒绝 Spec、8 个知识路径、专家、安装、原方法及流程合同。测试夹具提供独立用户目录，整次会话对真实接入面做前后快照检查。

首次新测试为 6 failed / 4 passed：1 项缺少新 Spec 上下文结构，4 项知识主标题影响命中，另 1 项是测试未建立工作流文档上下文，错误地期待通用生成器拒绝空项目。修正测试夹具加入未确认 PRD，没有修改确认门；结构和知识修正后 10 项新测试通过，再执行上面的 200 项回归。不能把首次所有失败都描述为发现了产品回归。

其他实际通过检查：

- `ruff check super_dev tests/unit/test_umadev_latest_soft_content.py`。
- `black --check super_dev/skills/skill_template.py super_dev/specs/generator.py tests/unit/test_umadev_latest_soft_content.py`。
- `mypy super_dev/skills/skill_template.py super_dev/specs/generator.py`：2 份源文件无问题；仅有既有 unused-section 配置提示。
- 改动 Python 文件编译检查。
- `scripts/sync_super_dev_skills.py --write` 后再校验：`SUPER_DEV_SKILLS_IN_SYNC=yes`，仅 4 个仓库副本。
- Skill 的 `quick_validate.py .agents/skills/super-dev` 与 `git diff --check`。

没有执行全仓所有测试或全项目发布命令；不借本批重写原 `completion-verification` 的质量报告。既有发布债务保持独立，未调分或降低阈值。

## 独立行为观察

依据 Skill 编写规范，在隔离临时目录提供原始任务与资料、更新后的标准 Skill，不给评估者预期答案或生产差异。只读评估不写文件；文档评估仅允许改三份指定文档，不运行程序、联网、访问凭据或生产。

| 场景 | 实际观察 |
| --- | --- |
| 缺依赖、测试零收集 | 没有归罪业务代码，也没有凭解释器版本猜不兼容；提出核对环境并复跑原检查 |
| 相同失败三次、源码未变 | 提出调查具体调用链与有效日期对照，不做第四次原样重试；识别两个受影响消费者 |
| URL 未变但价格类型和权限响应变化 | 指出消费者计算与重新授权行为被破坏；没有把 Mock HTTP200 当集成成功 |
| 本地模型配置未提供、另有非 AI 工具 | 保留本地产品模型边界，不借宿主凭据；配置缺失待补，非 AI 工具不加模型依赖 |
| 实际修订规格 | 保留 FR-1/FR-2 与非目标；源码位置、函数、项目 Python 约束未知时不编造；加入按风险验证计划 |
| 实际修订 UIUX | 保留冻结布局/组件；处理乱序回包、身份隔离、保存失败和演示标识，不把说明当已实现 |
| 实际修订交接 | abc111 的 Windows 8 passed 保留为历史范围；当前版/其他平台未验证；schema_v2 到旧版恢复受阻，无自动生产动作 |

前后逐文件 SHA256 和正文对照：7 份夹具文件中，仅授权的 `spec.md`、`uiux.md`、`handoff.md` 变化；`state.json`、`resources.json` 和两份任务输入未变。未新增文件。文档修订的隔离状态仍为 quality、docs_confirmed=true、released=false。

## 证据与保护边界

- 原始 JUnit：`output/umadev-latest-soft-content-pytest.xml`。
- 文件哈希、独立答复观察、隔离夹具前后全文与检查结果：`output/umadev-latest-soft-content-evidence.json`。
- 隔离目录：`C:/Users/admin/AppData/Local/Temp/superdev-uma-latest-ec39f092c0074e7b94e2851f22e5ecb5`。保留供复核；可随系统临时目录清理而消失，本记录不依赖其永久存在。
- `output/` 依仓库规则留在本地，本文件保留验证摘要。

`completion-verification` 工作流状态、阶段台账、tasks 和三份核心文档的 SHA256 均与实施前一致；阶段合同、确认守卫、SpecBuilder 调度、知识检索引擎、扩展及质量门禁源码无改动。没有全局 Skill 同步、提交、推送、发布或自动追更。

## 限度

此结果证明本批文字指导可通过当前生成/检索/安装路径取得，且在这些隔离任务中表现符合要求；不是宿主模型未来每次行为的形式化保证。没有执行真实产品的模型调用、UI 联调、生产恢复或 Linux/macOS 运行。本轮仅选择性落实 U7—U14，不代表全部 468 份知识已逐项吸收。
