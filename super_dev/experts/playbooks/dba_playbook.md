# 数据库专家（DBA）操作手册

> 使用范围：这是 DBA 的按需方法参考，职责与交接见[专家设定](../builtin/DBA.md)。按当前请求选择相关章节，复用已有决定；示例数值、模板和流程不自动成为新需求或覆盖项目已确认门禁。只读审查给出发现，实施和外部操作依据已有授权。

## 概述

数据库专家负责数据模型设计、查询优化、迁移策略和数据库运维。核心目标是确保数据的正确性、一致性、安全性和查询性能。DBA 不只关心"数据存得下"，更关心"查得快、改得动、丢不了"。

### 核心原则

1. **数据正确性优先**：约束和校验在数据库层面执行，不依赖应用层
2. **查询可预测**：性能敏感查询根据数据规模核对执行计划，顺序扫描本身不等于缺陷
3. **可迁移**：每次 schema 变更都有版本化迁移脚本和回滚方案
4. **最小暴露**：应用层只拥有必要的数据库权限

---

## 方法论

### 一、数据建模流程

#### 1.1 概念建模

- 从 PRD 提取核心业务实体
- 识别实体间关系（1:1, 1:N, M:N）
- 绘制 ER 图（使用 Mermaid/dbdiagram.io/PlantUML）
- 与 PM 确认实体和关系是否完整

#### 1.2 逻辑建模

- 确定每个实体的属性和数据类型
- 标注主键、外键、唯一约束
- 标注 NOT NULL、DEFAULT 值
- 识别枚举类型字段
- 评估是否需要软删除（`deleted_at`）
- 添加审计字段：`created_at`、`updated_at`、`created_by`

#### 1.3 范式化

按需应用范式化规则：

| 范式 | 要求 | 何时违反 |
|------|------|---------|
| 1NF | 每个字段存储原子值 | JSON 字段用于灵活扩展时 |
| 2NF | 非键字段完全依赖主键 | 通常不应违反 |
| 3NF | 非键字段不依赖其他非键字段 | 性能需要冗余时（有明确理由） |

#### 1.4 反范式化决策

仅在以下条件同时满足时允许反范式化：

1. 有明确的查询性能瓶颈（EXPLAIN 证据）
2. 读写比 > 10:1
3. 有数据一致性保障机制（触发器/应用层同步/最终一致）
4. 有文档记录决策理由

典型反范式化场景：
- 计数器冗余（避免 COUNT 查询）
- 聚合字段冗余（订单总金额）
- 嵌套数据展平（减少 JOIN）

#### 1.5 索引策略

**索引设计原则**：

1. 每个 WHERE/JOIN/ORDER BY 中的高频列都应有索引
2. 组合索引遵循最左前缀原则
3. 选择性低的列（如 boolean/status）单独索引意义不大
4. 覆盖索引优先（查询列全在索引中，避免回表）
5. 每张表索引不超过 6-8 个（写入性能考虑）

**索引类型选择**：

| 场景 | 索引类型 | 示例 |
|------|---------|------|
| 等值查询 | B-Tree（默认） | `WHERE user_id = 123` |
| 范围查询 | B-Tree | `WHERE created_at > '2026-01-01'` |
| 前缀匹配 | B-Tree | `WHERE name LIKE 'abc%'` |
| 全文搜索 | GIN + tsvector | `WHERE to_tsvector('english', content) @@ query` |
| JSON 字段查询 | GIN | `WHERE metadata @> '{"type": "a"}'` |
| 地理位置 | GiST/SP-GiST | `WHERE ST_DWithin(location, point, 1000)` |
| 数组包含 | GIN | `WHERE tags @> ARRAY['python']` |

**组合索引设计**：

```sql
-- 查询: WHERE status = 'active' AND created_at > '2026-01-01' ORDER BY score DESC
-- 索引: (status, created_at, score DESC)
-- 原则: 等值条件在前, 范围条件在后, 排序字段在末
CREATE INDEX idx_users_status_created_score
ON users (status, created_at, score DESC);
```

### 二、查询优化方法论

#### 2.1 EXPLAIN 分析

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT u.name, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.status = 'active'
GROUP BY u.name
ORDER BY order_count DESC
LIMIT 20;
```

**关键指标**：

| 指标 | 理想值 | 警告值 |
|------|-------|-------|
| Seq Scan（全表扫描） | 按选择性、规模和读取成本判断 | 有瓶颈时比较索引方案，不按固定行数强制添加 |
| Rows Removed by Filter | 低 | 高说明索引缺失或无效 |
| Sort Method: external merge | 不出现 | 出现说明 work_mem 不足 |
| Nested Loop 行数 | 小 | 大说明可能 N+1 |
| Actual Time | <100ms | >500ms 需要优化 |

#### 2.2 索引优化

**识别缺失索引**：
```sql
-- PostgreSQL: 查找慢查询
SELECT query, calls, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- 查找未使用的索引
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%_pkey';
```

**索引维护**：
```sql
-- 查看索引膨胀
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- 重建索引 (不锁表)
REINDEX INDEX CONCURRENTLY idx_name;
```

#### 2.3 查询重写

**常见优化模式**：

```sql
-- 反模式: SELECT *
SELECT * FROM users WHERE id = 1;
-- 正确: 只查需要的列
SELECT id, name, email FROM users WHERE id = 1;

-- 反模式: 子查询
SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE status = 'active');
-- 正确: JOIN
SELECT o.* FROM orders o JOIN users u ON o.user_id = u.id WHERE u.status = 'active';

-- 反模式: OFFSET 分页 (大偏移量)
SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 10000;
-- 正确: 游标分页
SELECT * FROM orders WHERE id > 10000 ORDER BY id LIMIT 20;

-- 反模式: 在索引列上使用函数
SELECT * FROM users WHERE LOWER(email) = 'test@example.com';
-- 正确: 函数索引或应用层标准化
CREATE INDEX idx_users_email_lower ON users (LOWER(email));

-- 反模式: OR 查询不走索引
SELECT * FROM users WHERE name = 'a' OR email = 'b@c.com';
-- 正确: UNION ALL
SELECT * FROM users WHERE name = 'a'
UNION ALL
SELECT * FROM users WHERE email = 'b@c.com' AND name != 'a';
```

### 三、迁移策略

#### 3.1 迁移脚本规范

```sql
-- migrations/20260328_001_add_user_avatar.sql

-- UP
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);
COMMENT ON COLUMN users.avatar_url IS '用户头像 URL';

-- DOWN
ALTER TABLE users DROP COLUMN avatar_url;
```

**规范要求**：
- 文件名格式：`{日期}_{序号}_{描述}.sql`
- 迁移记录前向变更及恢复方式；可逆变更可提供 DOWN，不可逆变更说明备份恢复或前向修复条件
- 明确迁移工具的一次性执行与重复执行行为，不把失败静默当成幂等
- PostgreSQL 创建索引可按需使用 `CREATE INDEX CONCURRENTLY` 减少对写入的阻塞；它不适用于所有 DDL，也不意味着完全无锁

#### 3.2 前向兼容原则

发布期间新旧版本代码共存，迁移必须对旧版本兼容：

| 操作 | 安全做法 | 危险做法 |
|------|---------|---------|
| 添加列 | 添加可空列或有默认值的列 | 添加 NOT NULL 无默认值的列 |
| 删除列 | 先停止读写 → 再删除 | 直接删除仍在使用的列 |
| 重命名列 | 添加新列 → 双写 → 迁移数据 → 删旧列 | 直接 RENAME |
| 修改类型 | 添加新列 → 迁移 → 切换 → 删旧列 | 直接 ALTER TYPE |
| 添加索引 | `CREATE INDEX CONCURRENTLY` | `CREATE INDEX`（锁表） |
| 添加约束 | `NOT VALID` + `VALIDATE CONSTRAINT` | 直接添加（锁表校验） |

#### 3.3 蓝绿迁移

1. **准备阶段**：在蓝环境执行迁移脚本
2. **验证阶段**：运行数据一致性检查
3. **切换阶段**：将流量切到蓝环境
4. **观察阶段**：监控错误率和性能指标 30 分钟
5. **清理阶段**：确认稳定后清理绿环境旧资源

#### 3.4 回滚计划

每次迁移前必须准备：
- 适用的 DOWN、备份恢复或前向修复方案经过隔离验证
- 数据备份（大表至少备份受影响的数据）
- 回滚时间估算
- 回滚后的数据一致性验证方法

### 四、数据库安全

#### 4.1 权限最小化

```sql
-- 应用账号只给 CRUD 权限，不给 DDL
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- 迁移账号额外给 DDL 权限
GRANT CREATE, ALTER, DROP ON SCHEMA public TO migration_user;
-- 只读账号（报表/分析）
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

#### 4.2 敏感数据处理

- PII（个人身份信息）字段标注并加密存储
- 日志/备份中的敏感数据脱敏
- 开发/测试环境使用脱敏后的数据
- 定期审计敏感数据访问记录

---

## 数据库审查检查清单

### 数据模型（7 项）

- [ ] ER 图是否与当前 schema 一致
- [ ] 主键选择是否合理（自增 ID vs UUID vs 业务键）
- [ ] 外键约束是否定义（或文档化为什么不使用）
- [ ] 枚举字段是否使用 CHECK 约束或枚举类型
- [ ] NOT NULL 约束是否合理设置
- [ ] 默认值是否有意义
- [ ] 审计字段（created_at/updated_at）是否存在

### 索引与性能（6 项）

- [ ] 所有 WHERE/JOIN 高频列是否有索引
- [ ] 组合索引是否遵循最左前缀和查询模式
- [ ] 是否存在冗余索引
- [ ] 是否存在未使用的索引
- [ ] 大表查询是否有 EXPLAIN 分析
- [ ] 分页是否使用游标而非 OFFSET（大数据量时）

### 迁移与变更（6 项）

- [ ] 迁移是否有前向变更和适用恢复方案，不可逆限制是否明确
- [ ] 是否核对当前数据库与具体 DDL 的锁和并发限制
- [ ] 新列是否可空或有默认值（前向兼容）
- [ ] 数据迁移是否分批执行（避免长事务）
- [ ] 回滚方案是否准备并测试
- [ ] 迁移前是否有数据备份

### 安全与运维（6 项）

- [ ] 应用账号权限是否最小化
- [ ] 敏感数据是否加密存储
- [ ] 连接池配置是否合理
- [ ] 慢查询日志是否开启
- [ ] 备份策略是否定义（频率/保留期/恢复测试）
- [ ] 监控是否覆盖（连接数/慢查询/磁盘空间/复制延迟）

---

## 交叉审查要点

### 审查架构师输出时

- 数据库选型是否匹配数据访问模式
- 读写分离/分库分表策略是否合理
- 缓存层设计是否与数据库一致性需求匹配

### 审查代码专家输出时

- ORM 使用是否有 N+1 查询风险
- 事务范围是否合理（不过大也不遗漏）
- 数据库连接是否正确释放

### 审查 DevOps 输出时

- 数据库备份是否纳入 CI/CD 流程
- 迁移脚本是否在部署流程中自动执行
- 数据库监控告警是否配置

---

## 常见反模式

### 1. EAV（Entity-Attribute-Value）模型

**症状**：用一张通用表存储所有实体的所有属性

**问题**：查询复杂、无法加约束、性能差

**正确做法**：为每种实体建独立表，灵活部分使用 JSONB 字段

### 2. 无索引裸查询

**症状**：生产环境全表扫描，查询超时

**正确做法**：上线前对本轮性能敏感的关键查询核对执行计划与实际数据规模

### 3. 过度范式化

**症状**：一个简单查询需要 JOIN 6 张表

**正确做法**：适度反范式化，用冗余换查询性能

### 4. 硬删除

**症状**：直接 DELETE 数据，无法恢复也无法审计

**正确做法**：软删除（`deleted_at`）+ 定期归档清理

### 5. 无版本化迁移

**症状**：直接在生产数据库手动执行 DDL

**正确做法**：使用迁移工具（Alembic/Flyway/Prisma Migrate）管理所有 schema 变更

---

## 知识依据

该专家依赖以下知识库文件：

- `knowledge/development/01-standards/postgresql-complete.md` — PostgreSQL 完整标准
- `knowledge/development/01-standards/mongodb-complete.md` — MongoDB 使用标准
- `knowledge/development/01-standards/redis-complete.md` — Redis 使用标准
- `knowledge/development/01-standards/elasticsearch-complete.md` — Elasticsearch 标准
- `knowledge/development/01-standards/performance-optimization-complete.md` — 性能优化标准

索引语法与并发限制核对依据：[PostgreSQL 18 CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)，核对日期 2026-09-11。
