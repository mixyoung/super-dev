---
id: "METH-005"
title: "可测试专家画像契约模型"
category: "方法论与规范"
source_refs: ["REF-004"]
summary: "废除花哨的虚构拟人化简历，将 AI 专家角色定义为具备明确输入、产物、权限天花板与交接停止条件的可测试工程契约。"
ai_generated: false
verified_by: "mixyoung"
tags: ["personas", "contracts", "governance", "roles"]
---

# 可测试专家画像契约模型 (Expert Persona Contracts)

> **核心哲学**：大模型不是在演话剧，不需要知道自己“毕业于哪所大学”。真正有效的高确定性角色定义，必须由输入接口、输出产物、权限红线与停止信号构成。

---

## 1. 拟人叙事 vs 工程契约

| 维度 | ❌ 拟人叙事画像 (Resume Narrative) | ✅ 可测试工程契约 (Engineering Contract) |
| :--- | :--- | :--- |
| **角色描述** | “你叫 Alice，拥有 15 年经验的敏捷教练，富有同理心……” | **Domain**: `QA Engineering & Test Integrity`<br>**Lens**: 专门从反作弊、边界破坏和覆盖率角度审查。 |
| **任务输入** | 自由文本对话，“请帮我看看这个模块” | **Input Contract**: 必须提供 `architecture.md` 与待测代码的 Git diff。 |
| **交付标准** | 随意输出一段建议 | **Deliverables**: 包含失败复现命令、严重级别（Blocker/Advisory）的审查表格。 |
| **行为权限** | 无约束，经常顺手直接改动用户业务代码 | **Authority Ceilings**: 只读权限；禁止直接修改被审查源码；只有提意见权。 |
| **退出条件** | 聊到用户不想聊为止 | **Stop Condition**: 生成审查报告并给出阻断项裁决后，立即停止输出交还终端。 |

---

## 2. 角色契约的标准模板

```yaml
role_id: "QA_CRITIC"
domain: "代码与验证完整性审查"
evaluation_lenses:
  - "是否通过删除或放宽断言换取测试通过？"
  - "是否有未处理的异步异常？"
input_contract:
  required_files: ["src/...", "tests/..."]
deliverable:
  format: "Markdown 证据审查表"
authority:
  file_write: false
  command_exec: "readonly_tests_only"
stop_trigger: "报告渲染完成即停止"
```

---

## 3. ⚡ Super Dev 流水线全自动注入路径 (Automatic Pipeline Injection)

专家画像契约模型**是 Super Dev 专家系统的底层建筑构架，而非一个对话时需要手动挂载的外挂 Prompt**：

- **生效位置**：`super_dev/experts/builtin/` 目录下所有专家角色定义（`PM.md`、`ARCHITECT.md`、`DEV.md`、`QA.md`、`SECURITY.md` 等）。
- **底层机制**：
  - 流水线引擎（`orchestrator/engine.py`）按阶段自动分派具有对应权限契约的专家；
  - 专家角色严格受其 `authority`（权限红线）、`focus_areas`（聚焦维度）与 `handoff_checklist`（交接清单）约束；
  - 例如审查角色具备只读权限，模型从物理与逻辑上被禁止在审查阶段擅自修改业务源码。

## 4. 💡 为什么必须在本项目吸纳，而不是让用户外部安装？

| 比较维度 | ❌ 用户自行安装外部 Skill / 插件 | ✅ 吸纳进 Super Dev 核心库 |
| :--- | :--- | :--- |
| **协同可控性** | 外部 Agent 角色往往是自由人设，容易越权（如代码审查时顺便修改源码） | **权限刚性天花板**：专家契约严格锁定文件读写权限与退出信号，绝不越权 |
| **流程自动化** | 用户必须手动指定“请让架构师看一眼”、“请让安全看一眼” | **引擎自动编排**：流水线到对应阶段自动激活对应专家，完成任务立刻交接 |
| **开箱可用性** | 依赖外部复杂的多 Agent 框架环境配置 | **原生轻量集成**：无需任何外部依赖，专家契约直接由 Python CLI 本地调度 |
| **负向决策留存** | 容易陷入“角色扮演游戏”式的无意义闲聊 | **ADR 护航**：在 `ADR-REF-004` 中彻底剥离虚构拟人化生平，建立契约驱动体系 |

> **可选人工调试指令**（仅在非流水线模式或独立调用特定专家视角排查时使用）：
> `“以 [PM / ARCHITECT / QA / SECURITY] 契约身份审查当前任务，遵守其权限红线并给出阻断项裁决”`
