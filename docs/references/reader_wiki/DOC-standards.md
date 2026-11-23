---
id: "DOC-STANDARDS"
title: "官方工程规范与技术依据总览 (DOC-001 ~ DOC-008)"
category: "规范与技术文档"
status: "已参考·依据引用"
summary: "汇总 Super Dev 在数据库设计、Web 可访问性、MCP 权限、进程安全及供应链证明领域采纳的 8 项官方工业技术依据。"
ai_generated: false
verified_by: "mixyoung"
tags: ["standards", "postgresql", "accessibility", "security", "slsa", "mcp"]
---

# 官方工程规范与技术依据总览 (DOC-001 ~ DOC-008)

> **定位摘要**：本项目拒绝凭空编造架构假说，所有底层架构设计与代码生成均直接锚定业界成熟的技术规范与 RFC 依据。

---

## 1. 规范一览表

| 编号 | 规范名称 | 官方链接 | 解决的架构核心问题 |
| :--- | :--- | :--- | :--- |
| **DOC-001** | PostgreSQL 18 CREATE INDEX | [postgresql.org/...](https://www.postgresql.org/docs/18/sql-createindex.html) | 索引创建成本控制：必须明确并发构建（`CONCURRENTLY`）开销与无法在事务块中运行的硬限制。 |
| **DOC-002** | W3C APG 可访问名称 (ARIA) | [w3.org/WAI/ARIA/...](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) | 前端无障碍审计：优先使用原生语义，杜绝无意义的 `div/span` 假按钮和缺失的 Accessible Name。 |
| **DOC-003** | OpenAI 插件分发规范 | [developers.openai.com/...](https://developers.openai.com/plugins/build/plugins) | 扩展清单锁定：插件清单必须锁定具体端点与域名校验，防御注入劫持。 |
| **DOC-004** | MCP 工具注解说明 | [blog.modelcontextprotocol.io/...](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/) | 权限与安全：严格区分注解（自述意图）与真实权限（强制隔离），不把风险自述当作权限保障。 |
| **DOC-005** | Python subprocess 安全边界 | [docs.python.org/3/...](https://docs.python.org/3/library/subprocess.html) | CLI 命令注入防御：必须使用结构化参数数组传参，严禁 `shell=True` 拼接未转义字符串。 |
| **DOC-006** | Windows Job Objects 进程组治理 | [learn.microsoft.com/...](https://learn.microsoft.com/en-us/windows/win33/procthread/job-objects) | 跨平台子进程清理：Windows 下将子进程绑定至作业对象，主进程崩溃或超时时保证整树回收。 |
| **DOC-007** | SLSA v1.2 供应链来源证明 | [slsa.dev/spec/v1.2/...](https://slsa.dev/spec/v1.2/provenance) | 发布防篡改：构建产物必须生成携带 commit 哈希与依赖摘要的不可伪造证明。 |
| **DOC-008** | JSON Schema Object 规范 | [json-schema.org/...](https://json-schema.org/understanding-json-schema/reference/object) | 数据契约闭合：接口 Schema 必须显式声明必填项并使用 `additionalProperties: false` 拒绝额外字段注入。 |
