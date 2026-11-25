# 上游前沿工程方法论吸收立项记录 (2026-11-24)

- **Change 标识**：`upstream-method-absorption-2026-11-24`
- **关联来源**：
  - [`REF-005 (Matt Pocock Skills)`](../../../docs/references/reader_wiki/REF-005-matt-pocock-skills.md)：`abeeaf9`（基线 `3cca18b`）
  - [`REF-003 (BMAD Method)`](../../../docs/references/reader_wiki/REF-003-bmad.md)：`e435a22`（基线 `94b6727`）
- **立项日期**：2026-11-24（2026-11-25 契约深化与缺陷修复）
- **当前分支**：`mixyoung/reference-updates`
- **执行责任人**：`mixyoung` / AI Assistant

---

## 问题与现有覆盖

本批对应用户在完成参考源周期性巡检后下达的方法论吸收与后续质量/工作流修复请求，工作项为 `upstream-method-absorption-2026-11-24`。

1. **现有覆盖**：
   - 本项目已吸收 BMAD 的 Forge Idea 需求反证思想（`REF-003/A1`）；
   - 已吸收 Matt Pocock 的按需引用与自动化复盘脚本化（`REF-005/A1`）；
   - 已吸收 oil-tone 的读者信息顺序与自然准确表达（`REF-014/A1`，其对 `knowledge/product/product-discovery-and-prd-deep-dive.md` 的改动归属保留在 `oil-tone-adoption-2026-11-22/adoption.md`）。
2. **实际工程缺口**：
   - **架构设计缺乏方案比对**：模型在架构设计时倾向于直接给出第一直觉方案，缺乏方案 A 与方案 B 的四维权衡对比与放弃理由（对应 `DESIGN-IT-TWICE`）；
   - **业务术语缺乏统一规范**：PM、架构师与前后端在长会话中容易出现名词漂移或歧义（对应 `GLOSSARY` 领域词汇表）；
   - **代码审查与提示契约脱节**：`KnowledgePusher` 摘要截断（300/120 字符）导致仅靠文档末尾段落难以稳定进入真实任务，必须写入生成器、评审器与专家画像契约；
   - **测试反作弊探针误报与巡检工作流断链**：初版 `TestIntegrityChecker` 误报字符串夹具、条件 `skipif`、嵌套辅助函数与校验 helper；`.github/workflows/reference-watch.yml` 使用 `env.has_actionable` 而非 `steps.checker.outputs.has_actionable` 导致报警条件不生效。

---

## 来源与适用条件

1. **Matt Pocock Skills (REF-005)**：
   - 关注 `skills/engineering/codebase-design/DESIGN-IT-TWICE.md` 与 `skills/engineering/domain-modeling/GLOSSARY-FORMAT.md`。
2. **BMAD Method (REF-003)**：
   - 关注 `PR #2861` 的多视角审查与严格度分级思想。
3. **适用范围**：
   - 适用于架构文档/ADR 生成、PRD 词汇表建模、Code Review 指南与 AI 提示词收尾自审、测试完整性检查以及参考源巡检脚本/工作流。
4. **不适用反例**：
   - 修改单行注释、纯拼写修正或常规配置微调时，严禁强行触发双方案比对或深度渗透审查；合法平台/环境条件跳过不判作测试作弊。

---

## 取舍与核心影响

### ✅ 择优吸收与修复项
1. **契约层落地**：将双方案比对、领域词汇表（唯一术语/禁止别名/概念边界）、多视角审查与三档严格度直接写入 `super_dev/creators/`、`super_dev/reviewers/code_review.py`、`super_dev/orchestrator/experts.py` 与 `super_dev/experts/`。
2. **反作弊探针精确化**：`TestIntegrityChecker` 改用 `tokenize` 识别真实注释、区分无条件逃避跳过与条件环境跳过、仅检查顶层及测试类方法、识别 Mock/校验 helper，并将仅有业务调用的冒烟用例降级为提示（`warning`）而非硬阻断。
3. **巡检工作流与范围账本对齐**：修复 `.github/workflows/reference-watch.yml` 的 `steps.checker.outputs.has_actionable` 条件判断与 `scripts/check_reference_updates.py` 的版本正则/纯文件名报告路径问题。
   - 注：`knowledge/product/product-discovery-and-prd-deep-dive.md` 在本分支已由 `oil-tone-adoption-2026-11-22/adoption.md` 声明主要归属，本批在其上的词汇表追加与 2026-11-25 方案 2 未决事项归口措辞对齐不另行重复认领；同时在 [ADR-REF-001](../../../docs/references/decisions/ADR-REF-001-umadev-soft-content-boundaries.md) 与 [扩展平台方案](../../../docs/SUPER_DEV_EXTENSION_PLATFORM_PLAN.md) 同步增补了独立账本边界注记。
4. **旧版残留清理与测试环境对齐**：清退 `.claude/skills/super-dev/` 下的 63 个历史 v1 存档文件（保留规范入口 `.claude/skills/super-dev/SKILL.md`）及 3 处已于 `2.4.0` 废止的 `super-dev-core` 仓库残留存根（`.cline/skills/super-dev-core/SKILL.md`、`.github/skills/super-dev-core/SKILL.md`、`.kilocode/skills/super-dev-core/SKILL.md`）；修复 `scripts/check_delivery_ready.py` 根路径与 `tests/conftest.py`、`tests/e2e/test_full_flow.py`、`tests/unit/test_release_script_routing.py`、`tests/unit/test_upstream_method_absorption.py` 的环境隔离及 CWD ADR 写入问题。

### 🛑 拒绝与架构边界调整
1. **坚决不引入外部多智能体调度状态机或外部技能整包安装**，保持 Super Dev 原生流水线。
2. **明确采用独立未决事项账本方案并实现全链路闭环硬门禁（2026-11-25 用户拍板）**：经对比 `v2.5.0`“不建第二册”原边界后，正式采用独立 `.super-dev/parking-lot.json`（`ParkingLotRegister` + `super-dev parking` CLI + `/api/parking-lot` Web API + `StateStore`/`SessionBrief` 双向同步），以保持核心 PRD/架构文档纯净、防止反复打补丁稀释模型注意力；同时完成三层闭环封堵：`resolve` 强制校验 `resolution_notes`、文档扩展名、真实存在的 `#anchor` 标题与登记后核心文档内容实改摘要（`source_doc_digests` / `resolved_target_digest`），反向扫描 `output/*-prd.md` / `*-architecture.md` 是否残留未入账的 `TBD`/`[待定]`/暂缓补丁（`scan_core_docs_for_untracked_deferrals`），并将 `summarize_parking_lot` 接入 `workflow_guard`、`host_workflow_context`、`workflow_state`、`QualityGateChecker`、`quality_evidence_dependency_paths`、`ReleaseReadinessEvaluator._check_delivery_closure()` 与 `DeliveryPackager.package()` 全链路拦截。

---

## 改动范围

- .agents/skills/super-dev/SKILL.md
- .claude/CLAUDE.md
- .claude/agents/super-dev.md
- .claude/commands/super-dev.md
- .claude/skills/super-dev/SKILL.md
- .claude/skills/super-dev/creators/__init__.py
- .claude/skills/super-dev/creators/creator.py
- .claude/skills/super-dev/creators/document_generator.py
- .claude/skills/super-dev/creators/prompt_generator.py
- .claude/skills/super-dev/creators/spec_builder.py
- .claude/skills/super-dev/discovery/INTAKE.md
- .claude/skills/super-dev/experts/ARCHITECT.md
- .claude/skills/super-dev/experts/CODE.md
- .claude/skills/super-dev/experts/DBA.md
- .claude/skills/super-dev/experts/DEVOPS.md
- .claude/skills/super-dev/experts/PM.md
- .claude/skills/super-dev/experts/QA.md
- .claude/skills/super-dev/experts/RCA.md
- .claude/skills/super-dev/experts/SECURITY.md
- .claude/skills/super-dev/experts/TEMPLATE.md
- .claude/skills/super-dev/experts/UI.md
- .claude/skills/super-dev/experts/UX.md
- .claude/skills/super-dev/knowledge/compliance/mlps.md
- .claude/skills/super-dev/knowledge/compliance/pipl.md
- .claude/skills/super-dev/knowledge/components/arch/base.md
- .claude/skills/super-dev/knowledge/components/prd/base.md
- .claude/skills/super-dev/knowledge/components/prd/mobile.md
- .claude/skills/super-dev/knowledge/components/prd/web.md
- .claude/skills/super-dev/knowledge/components/prd/wechat.md
- .claude/skills/super-dev/knowledge/components/prototype/base.html
- .claude/skills/super-dev/knowledge/domains/ecommerce.md
- .claude/skills/super-dev/knowledge/domains/education.md
- .claude/skills/super-dev/knowledge/domains/fintech.md
- .claude/skills/super-dev/knowledge/domains/iot.md
- .claude/skills/super-dev/knowledge/domains/medical.md
- .claude/skills/super-dev/knowledge/domains/social.md
- .claude/skills/super-dev/knowledge/handover/deployment.md
- .claude/skills/super-dev/knowledge/handover/user_manual.md
- .claude/skills/super-dev/knowledge/platforms/desktop.md
- .claude/skills/super-dev/knowledge/platforms/mobile.md
- .claude/skills/super-dev/knowledge/platforms/web.md
- .claude/skills/super-dev/knowledge/platforms/wechat.md
- .claude/skills/super-dev/quality/CHECKLIST.md
- .claude/skills/super-dev/quality/MULTI_ROUND.md
- .claude/skills/super-dev/research/PROTOCOL.md
- .claude/skills/super-dev/scripts/auto_quality_check.py
- .claude/skills/super-dev/scripts/clone_dna.py
- .claude/skills/super-dev/scripts/competitor_analysis.py
- .claude/skills/super-dev/scripts/domain_research.py
- .claude/skills/super-dev/scripts/generate_ci_cd.py
- .claude/skills/super-dev/scripts/generate_doc.py
- .claude/skills/super-dev/scripts/generate_dockerfile.py
- .claude/skills/super-dev/scripts/generate_preview.py
- .claude/skills/super-dev/scripts/hire_expert.py
- .claude/skills/super-dev/scripts/init_project.py
- .claude/skills/super-dev/scripts/market_research.py
- .claude/skills/super-dev/scripts/quality_check.py
- .claude/skills/super-dev/scripts/requirements.txt
- .claude/skills/super-dev/scripts/research_orchestrator.py
- .claude/skills/super-dev/scripts/template_engine.py
- .claude/skills/super-dev/scripts/test_workflow.py
- .claude/skills/super-dev/scripts/utils.py
- .claude/skills/super-dev/specs/__init__.py
- .claude/skills/super-dev/specs/generator.py
- .claude/skills/super-dev/specs/manager.py
- .claude/skills/super-dev/specs/models.py
- .claude/skills/super-dev/wisdom/PATTERNS.md
- .claude/skills/super-dev/wisdom/PITFALLS.md
- .cline/skills/super-dev-core/SKILL.md
- .clinerules/super-dev.md
- .codex/AGENTS.md
- .cursor/rules/super-dev.mdc
- .github/skills/super-dev-core/SKILL.md
- .github/workflows/reference-watch.yml
- .junie/AGENTS.md
- .kilocode/rules/super-dev.md
- .kilocode/skills/super-dev-core/SKILL.md
- .openclaw/commands/super-dev.md
- .openclaw/rules/super-dev.md
- .roo/commands/super-dev.md
- .roo/rules/super-dev.md
- .super-dev/COMMAND_ROUTING.md
- AGENTS.md
- CLAUDE.md
- docs/UMADEV_SOFT_CONTENT_ADOPTION.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- scripts/check_delivery_ready.py
- scripts/check_reference_updates.py
- knowledge/architecture/adr-template-and-examples.md
- knowledge/backend/01-standards/nestjs-complete.md
- knowledge/development/04-antipatterns/code-smell-antipatterns.md
- knowledge/development/code-review-quality-complete.md
- super_dev/creators/adr_generator.py
- super_dev/creators/document_architecture_content_mixin.py
- super_dev/creators/document_delivery_content_mixin.py
- super_dev/creators/document_product_content_mixin.py
- super_dev/creators/document_ui_content_mixin.py
- super_dev/creators/frontend_builder.py
- super_dev/creators/prompt_generator.py
- super_dev/experts/builtin/ARCHITECT.md
- super_dev/experts/builtin/CODE.md
- super_dev/experts/builtin/PM.md
- super_dev/experts/builtin/QA.md
- super_dev/experts/toolkit.py
- super_dev/orchestrator/experts.py
- super_dev/reviewers/code_review.py
- super_dev/reviewers/fresh_verification_evidence.py
- super_dev/reviewers/quality_gate.py
- super_dev/reviewers/quality_gate_evidence_mixin.py
- super_dev/reviewers/test_integrity.py
- super_dev/reviewers/ui_review_execution_mixin.py
- super_dev/specs/generator.py
- super_dev/deployers/delivery.py
- super_dev/enforcement/pre_code_gate.py
- super_dev/host_workflow_context.py
- super_dev/integrations/manager_content_mixin.py
- super_dev/parking_lot.py
- super_dev/release_readiness.py
- super_dev/session/brief.py
- super_dev/skills/skill_template.py
- super_dev/state_store.py
- super_dev/web/api.py
- super_dev/web/frontend/dist/index.html
- super_dev/workflow_guard.py
- super_dev/workflow_state.py
- super_dev/cli.py
- super_dev/cli_parser_mixin.py
- super_dev/cli_spec_mixin.py
- README.md
- README_EN.md
- docs/REFERENCE_SOURCES.md
- docs/REFERENCE_UPDATES.md
- docs/SUPER_DEV_EXTENSION_PLATFORM_PLAN.md
- docs/references/decisions/ADR-REF-001-umadev-soft-content-boundaries.md
- tests/conftest.py
- tests/e2e/test_full_flow.py
- tests/unit/test_check_reference_updates.py
- tests/unit/test_upstream_method_absorption.py
- tests/unit/test_parking_lot.py
- tests/unit/test_release_script_routing.py
- tests/unit/test_test_integrity.py
- tests/unit/test_find_available_port.py
- tests/unit/test_frontend_builder_enhanced.py
- tests/unit/test_requirement_parser.py
- .super-dev/changes/upstream-method-absorption-2026-11-24/adoption.md

## 验证与未验证

1. **验证环境**：Windows 11，本项目独立虚拟环境 `.venv`（`uv sync --python 3.13 --dev`，CPython 3.13.12，`super-dev==2.6.0` editable + 完整 dev 依赖含 `mypy==1.20.1`、`black==26.3.1`、`ruff==0.15.11`、`bandit==1.9.4`、`pytest==9.0.3`）。
2. **本轮已运行验证**：
   - `.venv\Scripts\python.exe scripts/check_contribution_policy.py --base 26b0cb6`（PR 分支基线）：通过；注：未提交工作区下对 `--base HEAD` 运行会提示 `knowledge/product/product-discovery-and-prd-deep-dive.md` 未列入本批范围记录（因该文件主归属保留在同分支 `oil-tone-adoption-2026-11-22/adoption.md`，两批不能在 `--base 26b0cb6` 下重复认领同一文件）；
   - `.venv\Scripts\python.exe scripts/sync_super_dev_skills.py`：确认 `SUPER_DEV_SKILLS_IN_SYNC=yes`；
   - `.venv\Scripts\python.exe -m ruff check .` 与 `black super_dev/ --check`：清理旧 v1 残留后全仓 `ruff` 与 `black` 格式校验全部通过；
   - `.venv\Scripts\python.exe scripts/check_type_gates.py --project-dir .` 与 `.venv\Scripts\python.exe -m mypy super_dev`：22 项核心发布门禁与全量 `mypy super_dev` 全部通过；
   - `.venv\Scripts\python.exe -m bandit -ll -r super_dev` 与 `TestIntegrityChecker.scan_project('.')`：安全扫描 0 问题，测试完整性 0 blocking；
   - `.venv\Scripts\python.exe scripts/check_delivery_ready.py --smoke`：离线 11 阶段交付链路 smoke 通过；
   - `.venv\Scripts\python.exe -m pytest tests/unit tests/integration tests/e2e tests/extensions`：完整开发模式下全仓四区测试运行通过。
3. **未验证事项**：
   - GitHub Actions 线上实际运行（`reference-watch.yml` 的 `schedule` 需合入默认分支后由 GitHub 定时触发）；
   - Web 前端 `super_dev/web/frontend/dist/index.html` 已通过 `node --check` 语法与 `TestClient` API/HTML 返回校验，未在本机真实浏览器窗口做手工点击实测。

---

## 决定与回退

- **决定**：按用户明确确认采用“独立未决事项账本闭环方案（方案 2）”并完成全部修复与契约落地；正式 PR 合并批准仍待维护者最终审查（本记录不代签合并批准）。
- **回退方式**：按受影响文件列表定向回退对应修改与新增测试，不影响现有流水线阶段定义与确认门机制。
