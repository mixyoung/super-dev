---
id: "REF-014"
title: "oil-tone: 自然克制的技术与产品表达"
category: "技能与角色库"
status: "已参考·部分吸收"
upstream_url: "https://github.com/oil-oil/oil-tone"
fixed_baseline: "39cbf92f76c90b7bb27a5b5d4ed88a1fc5fa31f6"
first_audit_date: "2026-11-22"
latest_audit_date: "2026-11-22"
summary: "专注于工程与产品文档的自然、准确表达，消除机械翻译腔与 AI 模板化陈词，强调读者信息顺序与业务状态完整性。"
key_methods: ["natural-precise-writing"]
ai_generated: false
verified_by: "mixyoung"
tags: ["writing", "documentation", "tone", "ux-copy"]
---

# REF-014: oil-tone

> **定位摘要**：oil-tone 是一套专注于技术与产品文档的自然表达规范。它的核心价值在于帮助工程师和 AI 摆脱互联网黑话（如“深度赋能”、“端到端闭环”）与机械翻译腔，建立“以读者认知为中心、主语完整、因果分明”的工程写作习惯。

---

## 1. 档案速览 (Metadata)

| 属性 | 说明 / 链接 |
| :--- | :--- |
| **官方地址** | [github.com/oil-oil/oil-tone](https://github.com/oil-oil/oil-tone) |
| **许可协议** | MIT License |
| **固定基线** | [`39cbf92`](https://github.com/oil-oil/oil-tone/tree/39cbf92f76c90b7bb27a5b5d4ed88a1fc5fa31f6)（2026-11-22 固定核对） |
| **参考状态** | 🟢 **已参考·部分吸收**（仅吸收其表达方法，不安装整套技能或执行外部脚本） |
| **原始剪藏** | [raw_sources/REF-014-oil-tone/README.md](../raw_sources/REF-014-oil-tone/README.md) |
| **决策记录** | [decisions/ADR-REF-014-oil-tone-adoption.md](../decisions/ADR-REF-014-oil-tone-adoption.md) |

---

## 2. 核心技术调研与深度分析 (What & How)

### 2.1 针对的痛点
大型语言模型在生成产品文档和架构说明时，普遍存在两个极端的写作缺陷：
1. **黑话堆砌与假大空**：使用“深度赋能”、“多维驱动”掩盖细节缺失；
2. **机械翻译腔与无谓断裂**：有些“去油工具”过度追求精简，把中文里正常的连接词、主谓关系甚至语法助词“的/了”全部删除，导致文档艰涩难读。

### 2.2 oil-tone 提出的四项核心写作解法
- **读者前置信息顺序**：读者最先需要知道“这对我有什么用 / 解决了什么”，其次才是“底层原理”，最后是“边角案例”。
- **状态与因果关系完整**：动作必须明确主体、客体和前后状态变化，不得使用模糊动作词蒙混过关。
- **保护中文自然语感**：承认虚词在中文语境中的连贯性作用，不搞“无油但生硬”的机械清洗。
- **语速回读复核**：将“朗读时是否呼吸顺畅、概念是否具象”作为第一复核标准。

---

## 3. 提炼出的通用方法论 (Extracted Methods)

从该项目中，我们抽象出了可在多个工程场景复用的方法论：
- 📖 [自然准确的工程表达法 (natural-precise-writing)](./methods/natural-precise-writing.md)

---

## 4. 关键技术取舍速查 (Trade-off Summary)

> [!TIP]
> 完整的决策依据与背景见 [ADR-REF-014-oil-tone-adoption.md](../decisions/ADR-REF-014-oil-tone-adoption.md)。

- ✅ **已吸收**：读者信息顺序、业务主体/因果完整、保留自然虚词、回读验证。
- 🛑 **坚决拒绝**：
  1. 不安装整套外部技能（避免上下文污染）；
  2. 不引入其内置的 Python 正则打分脚本与禁词阻断（文风不适合作为硬性 CI 阻断门禁）；
  3. 不采纳原作者的个人口吻或特定情绪标签（保持客观工程基调）。
