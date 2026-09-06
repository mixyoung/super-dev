# 已确认 U7—U14 的范围与依据补录

## 问题与现有覆盖

前一批用户确认的 U7—U14 已实现且仍未提交。本次安装贡献记录检查时补录其范围，不重新实施或混用新批次证据；具体缺口见原 proposal.md。

## 来源与适用条件

UmaDev v1.1.1 / 585262706174ad4a958cd054f0948509e84ad610；2026-09-06 已核对。原始来源映射在 docs/UMADEV_SOFT_CONTENT_ADOPTION.md；仅适用选择性的软内容，不代表全知识库吸收。

## 取舍与核心影响

保留宿主使用方式、九阶段、确认门和 SEEAI，只改变已有知识、专家、Spec 文字和标准 Skill 指导。拒绝独立运行程序、全局记忆、默认厂商和第二评分体系。用户在三文档后明确确认，批准依据在本任务历史与原 proposal.md。

## 改动范围

- .agents/skills/super-dev/SKILL.md
- .claude/skills/super-dev/SKILL.md
- plugins/super-dev-codex/skills/super-dev/SKILL.md
- plugins/super-dev-claude/skills/super-dev/SKILL.md
- docs/UMADEV_SOFT_CONTENT_ADOPTION.md
- knowledge/ai/agent-evaluation-benchmark.md
- knowledge/ai/ai-model-selection-and-routing-strategy.md
- knowledge/cicd/release-readiness-gate.md
- knowledge/design/ui-full-lifecycle-cross-platform-playbook.md
- knowledge/development/02-playbooks/debugging-playbook.md
- knowledge/development/api-contract-and-versioning-guide.md
- knowledge/testing/risk-based-test-matrix.md
- knowledge/testing/testing-strategy-deep-dive.md
- super_dev/experts/builtin/ARCHITECT.md
- super_dev/experts/builtin/CODE.md
- super_dev/experts/builtin/DEVOPS.md
- super_dev/experts/builtin/QA.md
- super_dev/skills/skill_template.py
- super_dev/specs/generator.py
- tests/unit/test_umadev_latest_soft_content.py
- .super-dev/changes/umadev-latest-soft-content/proposal.md
- .super-dev/changes/umadev-latest-soft-content/tasks.md
- .super-dev/changes/umadev-latest-soft-content/validation.md
- .super-dev/changes/umadev-latest-soft-content/adoption.md

## 验证与未验证

原验证为 200 项通过，4 个只读场景及 3 份隔离文档修订；实际命令、环境、原始报告和限度仍以本目录 validation.md 为准。补录不生成新的运行成功证据，不代替全项目或跨平台发布验证。

## 决定与回退

原用户确认范围已采用并通过定向验证，未提交推送。本文件只是补录。回退按 U7—U14 原差异处理，不影响新的贡献准则或 completion-verification 状态。
