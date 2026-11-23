# [Raw Source] DOC-001 ~ DOC-008: 官方工程规范与技术依据摘录

> **不可变事实说明**：记录外部官方标准、RFC 与技术规范的原始链接与核心断言。严禁主观改动。

---

## 1. 规范清册与官方原件索引

| 编号 | 规范名称 | 官方来源 | 核心事实与断言摘录 |
| :--- | :--- | :--- | :--- |
| **DOC-001** | PostgreSQL 18 CREATE INDEX | [postgresql.org/docs/18/...](https://www.postgresql.org/docs/18/sql-createindex.html) | `CONCURRENTLY` 允许在不阻塞写入的情况下构建索引，但消耗更多 CPU 与 I/O，且无法在事务块内部执行。 |
| **DOC-002** | W3C APG 可访问名称与描述 | [w3.org/WAI/ARIA/apg/...](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) | 优先使用原生 HTML 语义（如 `<button>`、`<label>`），仅在语义缺失时使用 `aria-label`；必须确保屏幕阅读器有确定的 Accessible Name。 |
| **DOC-003** | OpenAI 插件与分发规范 | [developers.openai.com/...](https://developers.openai.com/plugins/build/plugins) | 插件清单元数据（manifest）必须锁定 API 端点并做域名验证，避免提示注入劫持。 |
| **DOC-004** | MCP 工具注解规范说明 | [blog.modelcontextprotocol.io/...](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/) | 工具注解（Annotations）仅作为人机交互的风险自述与意图提示，**绝不能代替系统的权限隔离检查（Permissions）**。 |
| **DOC-005** | Python subprocess 安全边界 | [docs.python.org/3/library/subprocess.html](https://docs.python.org/3/library/subprocess.html) | 执行外部命令必须使用数组传参（`args=['cmd', 'arg']`），严禁使用 `shell=True` 拼接未转义的用户输入以防命令注入。 |
| **DOC-006** | Windows Job Objects 进程组治理 | [learn.microsoft.com/.../job-objects](https://learn.microsoft.com/en-us/windows/win33/procthread/job-objects) | 使用 Windows Job Objects 将子进程与主进程绑定，在主进程异常退出或超时时保证子进程树彻底清理，避免孤儿进程悬挂。 |
| **DOC-007** | SLSA v1.2 Provenance 供应链证明 | [slsa.dev/spec/v1.2/provenance](https://slsa.dev/spec/v1.2/provenance) | 构建产物必须包含不可伪造的来源元数据（构建者、源码 commit、依赖哈希摘要），实现供应链端到端可追溯。 |
| **DOC-008** | JSON Schema Object 规范约束 | [json-schema.org/.../object](https://json-schema.org/understanding-json-schema/reference/object) | 严格声明 `required` 必填字段，并在闭合模型中使用 `additionalProperties: false` 拒绝未定义注入。 |
