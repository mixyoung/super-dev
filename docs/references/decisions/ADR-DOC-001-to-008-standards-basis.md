# ADR-DOC-001~008: 官方工程规范与技术依据采纳决议

- **决策标识**：`ADR-DOC-001-to-008`
- **关联来源**：[`DOC-STANDARDS`](../reader_wiki/DOC-standards.md)
- **决策状态**：🔵 **已确认作为底层架构依据 (Adopted as Architectural Basis)**
- **审核责任人**：`mixyoung`

---

## 1. 核心裁决原则

1. **依据引用不等于整套代码依赖**：
   - 引用 W3C APG 或 PostgreSQL 18 文档是为了在代码生成和审查时拥有确定性的判定准绳，不代表在项目中强制安装某种沉重框架。
2. **防注入与边界硬隔离**：
   - 严格落实 DOC-004（不把 MCP 工具注解当权限保证）、DOC-005（拒绝 `shell=True` 防注入）、DOC-006（Windows 作业对象防孤儿进程挂起）与 DOC-008（Schema 闭合），将规范转化为 Super Dev 的确定性代码审查规则。
