# [Raw Source] REF-007: Agent Skills 规范原始摘录与基线快照

> **不可变事实说明**：记录外部来源原作者原始表达与文本片段，用于事实溯源、版权追溯及防幻觉核对。严禁主观改动。

---

## 1. 来源与版权信息

- **项目名称**：Agent Skills Specification
- **官方仓库**：[https://github.com/agentskills/agentskills](https://github.com/agentskills/agentskills)
- **官方规范**：[https://agentskills.io/specification](https://agentskills.io/specification)
- **固定基线**：[`69ef37e9424c0a7ea9dd2293b559e43ec8176379`](https://github.com/agentskills/agentskills/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379)
- **建档日期**：2026-09-12

---

## 2. 官方规范原件摘录

### 2.1 技能元数据与目录契约
> 来源文件：`specification/README.md`
> “A Skill is packaged as a directory containing a required `SKILL.md` file with standard YAML frontmatter (name, description, tags) and structured instructions. Optional directories include `scripts/`, `references/`, and `examples/`.”

### 2.2 渐进式加载设计 (Progressive Loading)
> 来源文件：`specification/README.md`
> “Agents should not load full skill bodies on initialization. Instead, the host registers high-level descriptions (Level 1), loads instructions on-demand when matched (Level 2), and executes external scripts only when specifically instructed (Level 3).”
