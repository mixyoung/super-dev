---
id: "REF-011"
title: "DeepSeek Harness: 智能体沙箱执行与可回放测试床"
category: "宿主与运行平台"
status: "已参考·待吸收"
upstream_url: "https://github.com/deepseek-ai/deepseek-harness"
fixed_baseline: "b830ec950faba0a46dda564be3e2d854afed94f1"
first_audit_date: "2026-11-05"
latest_audit_date: "2026-11-16"
summary: "DeepSeek 开源的智能体评测与运行测试床，支持回放验证、细粒度系统权限可关闭（网络/文件/终端）与环境沙箱隔离。"
key_methods: ["session-replay", "capability-toggle"]
ai_generated: false
verified_by: "mixyoung"
tags: ["deepseek", "harness", "sandbox", "replay"]
---

# REF-011: DeepSeek Harness

> **定位摘要**：DeepSeek Harness 是 DeepSeek 针对自主编码 Agent 开发的高性能测试床。其核心优势在于**确定性会话回放（Deterministic Session Replay）**和**开关式能力隔离（Capability Toggles）**。本项目已完成针对其适配器的前期调研。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) |
| **固定基线** | `dsh-v0.2.1-rc.5` / [`b830ec9`](https://github.com/deepseek-ai/deepseek-harness/tree/b830ec950faba0a46dda564be3e2d854afed94f1)（2026-11-05 复核） |
| **参考状态** | 🟡 **已参考·待吸收**（存在独立适配分支研究，但未验收前不改变主工作树） |
| **原始剪藏** | [raw_sources/REF-011-deepseek-harness/README.md](../raw_sources/REF-011-deepseek-harness/README.md) |
| **决策记录** | [decisions/ADR-REF-011-deepseek-harness-adapter.md](../decisions/ADR-REF-011-deepseek-harness-adapter.md) |

---

## 2. 核心技术调研与适配边界
1. **可回放性**：支持完整录制 Agent 的思考步与工具调用流，便于出现回归错误时精准复现；
2. **能力隔离**：支持关闭网络或限制命令白名单。
3. **团队决策边界**：DeepSeek 宿主适配必须经过独立的运行时验收套件测试通过，不能在没有完整环境支持的情况下草率声明支持。
