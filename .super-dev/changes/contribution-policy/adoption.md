# 演进贡献准则 v1

## 问题与现有覆盖

此前已有路线、知识维护和吸纳记录，但没有统一贡献入口与增量范围检查；规则依赖当前模型理解。用户要求固定方向、让后续开发者和模型看到并遵守。本批复用原文档、Git 和 CI，不引入知识运行平台。

## 来源与适用条件

依据 2026-09-06 本任务用户明确确认、现有 `docs/SUPER_DEV_EXTENSION_PLATFORM_PLAN.md` 和 14 类已吸纳记录。GitHub CODEOWNERS/分支保护官方文档链接在贡献准则；2026-09-06 API 核实 origin= mixyoung/super-dev，owner=mixyoung，main.protected=false，规则集为空。只约束维护本仓库，不适用于普通用户项目。

## 取舍与核心影响

采用固定产品边界、六问、稳定行为案例、贡献入口及只读机械检查。新增仓库贡献审核要求，用户已确认；不改变产品九阶段、确认权、运行时或质量分数。记录齐全不等于批准；远端保护另行确认，不能谎报已经强制生效。前一批仅补吸纳记录，不重写其实现和证据。

## 改动范围

- AGENTS.md
- CLAUDE.md
- .claude/CLAUDE.md
- CONTRIBUTING.md
- README.md
- README_EN.md
- docs/CONTRIBUTION_POLICY.md
- docs/SUPER_DEV_EXTENSION_PLATFORM_PLAN.md
- knowledge/00-governance/maintenance-policy.md
- knowledge/00-governance/review-checklist.md
- .github/pull_request_template.md
- .github/CODEOWNERS
- .github/workflows/ci.yml
- scripts/check_contribution_policy.py
- tests/unit/test_contribution_policy.py
- tests/fixtures/knowledge_adoption_cases.json
- .super-dev/changes/contribution-policy/proposal.md
- .super-dev/changes/contribution-policy/tasks.md
- .super-dev/changes/contribution-policy/adoption.md
- .super-dev/changes/contribution-policy/validation.md

## 验证与未验证

首先在真实工作区未补记录时检查明确失败，列出前后两批缺少记录的文件；补齐各自记录后通过。已执行隔离 Git 案例、格式/类型、规则同步与原流程回归，共 221 项通过；实际结果记录在本目录 validation.md。没有运行跨模型评测，不宣称 Linux CI 或远端保护已生效。

## 决定与回退

采用，依据本任务用户明确确认。回退只撤回本批文档入口、只读脚本、案例和 CI job；不改前一批 U7—U14 内容，不重置仓库。源文件及检查脚本的后续语义修改需维护者审查；模型不能自行改标准后自证通过。
