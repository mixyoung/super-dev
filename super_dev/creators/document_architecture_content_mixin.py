"""Architecture-content generators."""

from __future__ import annotations


class DocumentArchitectureContentMixin:
    def _generate_auth_module_design(self) -> str:
        """生成认证模块设计"""
        return """
### 认证模块 (Auth Module)

**职责**:
- 用户注册/登录
- Token 签发/验证
- 密码管理

**接口**:
```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
POST /api/v1/auth/verify
```

**实现要点**:
- JWT Token 签发使用 RS256
- Refresh Token 存储在 Redis
- 密码使用 bcrypt (cost=10)
"""

    def _generate_user_module_design(self) -> str:
        """生成用户模块设计"""
        return """
### 用户模块 (User Module)

**职责**:
- 用户信息管理
- 权限验证
- 用户状态管理

**接口**:
```
GET /api/v1/users/me
PATCH /api/v1/users/me
PUT /api/v1/users/me/password
GET /api/v1/users/:id
```

**实现要点**:
- 实现乐观锁防止并发修改
- 使用 RBAC 权限模型
- 敏感操作需要二次验证
"""

    def _generate_business_module_design(self) -> str:
        """生成业务模块设计"""
        return """
### 业务模块 (Business Module)

**职责**:
- 核心业务逻辑
- 数据验证
- 业务规则执行

**接口**:
```
GET /api/v1/resources
POST /api/v1/resources
GET /api/v1/resources/:id
PATCH /api/v1/resources/:id
DELETE /api/v1/resources/:id
```

**实现要点**:
- 实现幂等性
- 数据验证使用 Pydantic/Zod
- 审计日志记录所有变更
"""

    def _generate_database_schema(self) -> str:
        """生成数据库设计"""
        return """
### 表结构

**users 表**:
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_email (email),
    INDEX idx_username (username)
);
```

**sessions 表**:
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_token (token)
);
```

**audit_logs 表**:
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
```
"""

    def _generate_index_strategy(self) -> str:
        """生成索引策略"""
        return """
### 索引设计

| 表 | 索引 | 类型 | 用途 |
|:---|:---|:---|:---|
| users | idx_email | B-tree | 邮箱查询 |
| users | idx_username | B-tree | 用户名查询 |
| sessions | idx_user_id | B-tree | 用户会话查询 |
| sessions | idx_token | B-tree | Token 验证 |
| audit_logs | idx_user_id | B-tree | 用户审计日志 |
| audit_logs | idx_created_at | B-tree | 时间范围查询 |

### 查询优化
- 使用连接池 (pgbouncer)
- 实现查询缓存层
- 慢查询监控 (>100ms)
"""

    def _generate_api_endpoints(self) -> str:
        """生成 API 端点"""
        return """
### API 端点列表

#### 认证相关
```
POST   /api/v1/auth/register        # 用户注册
POST   /api/v1/auth/login           # 用户登录
POST   /api/v1/auth/logout          # 用户登出
POST   /api/v1/auth/refresh         # 刷新 Token
POST   /api/v1/auth/verify          # 验证 Token
POST   /api/v1/auth/forgot-password # 忘记密码
POST   /api/v1/auth/reset-password  # 重置密码
```

#### 用户相关
```
GET    /api/v1/users/me             # 当前用户信息
PATCH  /api/v1/users/me             # 更新用户信息
PUT    /api/v1/users/me/password    # 修改密码
GET    /api/v1/users/:id            # 用户详情 (管理员)
```

#### 业务资源
```
GET    /api/v1/resources            # 资源列表
POST   /api/v1/resources            # 创建资源
GET    /api/v1/resources/:id        # 资源详情
PATCH  /api/v1/resources/:id        # 更新资源
DELETE /api/v1/resources/:id        # 删除资源
```
"""

    def _generate_performance_optimization(self) -> str:
        """生成性能优化"""
        return """
### 后端优化

**数据库优化**:
- 连接池配置 (max_connections=100)
- 查询结果缓存 (Redis)
- 慢查询日志优化

**应用层优化**:
- 异步 I/O 处理
- 请求限流 (100 req/s)
- 响应压缩 (gzip)

**前端优化**:
- 代码分割和懒加载
- 资源 CDN 加速
- 图片优化和缓存

### 监控指标
- API 响应时间 P95 < 200ms
- 数据库查询时间 < 50ms
- 错误率 < 0.1%
"""

    def _generate_tech_comparison(self) -> str:
        """生成技术对比"""
        return """
### 技术选型对比

| 方面 | 选择 | 备选 | 理由 |
|:---|:---|:---|:---|
| 前端框架 | React | Vue, Angular | 生态成熟，组件丰富 |
| 状态管理 | Redux Toolkit | Zustand, Jotai | 标准方案，文档完善 |
| UI 库 | Ant Design | Material-UI | 设计规范完善 |
| 后端框架 | Express | Fastify, Koa | 灵活，中间件丰富 |
| ORM | Prisma | TypeORM, Sequelize | 类型安全，迁移友好 |
| 数据库 | PostgreSQL | MySQL, MongoDB | 功能强大，JSON 支持 |
| 缓存 | Redis | Memcached | 功能丰富，持久化 |
"""

    def _generate_adr(self) -> str:
        """生成架构决策记录（包含双方案比对与放弃理由契约）"""
        return """
### 架构决策记录 (ADR)

> **双方案比对契约 (Design It Twice)**：涉及高复杂度、跨模块或难逆的技术决策，须提供至少 2 个结构独立的备选方案，从实现复杂度、故障与恢复、运维负担、演进弹性四维对比，并写明**放弃备选方案的核心原因**。常规 CRUD、单字段增减或局部配置微调豁免此项，不机械套用。

#### ADR-001: 选择 JWT 作为认证方案

**状态**: 已接受

**背景**: 需要无状态的认证机制支持分布式部署与横向扩展

**备选方案对比**:
- **方案 A（采用）：JWT 无状态令牌** — 实现简单、无中心存储依赖、易于跨服务横向扩展；但令牌签发后无法单点即时吊销，需要较短过期时间或配合刷新机制。
- **方案 B（放弃）：Redis 集中式 Session** — 支持实时踢人与状态立即失效、运维可控性直观；但强依赖集中式缓存集群，引入额外连接与高可用运维负担。
- **放弃方案 B 的核心原因**: 当前首版优先降低分布式状态存储与跨节点会话同步复杂度，后续若需细粒度即时吊销能力，可通过引入黑名单或短效 Access Token + Refresh Token 渐进演进。

**决策**: 使用 JWT (JSON Web Token) 进行身份验证

**后果**:
- 正面: 无需集中式 Session 存储，支持多实例水平扩展
- 负面与补偿: Token 吊销依赖短过期窗口与刷新轮转策略

#### ADR-002: 选择 PostgreSQL 作为主数据库

**状态**: 已接受

**背景**: 需要关系型数据库支持复杂查询与强一致事务

**备选方案对比**:
- **方案 A（采用）：PostgreSQL** — 完整 ACID、强约束、原生 JSONB 与丰富索引能力，减少额外扩展数据库依赖；但水平分片较复杂。
- **方案 B（放弃）：MySQL / 文档型数据库混合** — 读性能成熟或 Schema 灵活；但混合架构增加跨库一致性、双写故障恢复与运维监控复杂度。
- **放弃方案 B 的核心原因**: 避免过早引入多引擎数据同步与事务一致性风险，优先以单主力强关系库兼顾结构化与半结构化需求。

**决策**: 使用 PostgreSQL 作为主数据库

**后果**:
- 正面: 数据完整性强、查询与演进弹性高
- 负面与补偿: 连接池与索引策略需结合实际负载调优
"""

    def _generate_k8s_config(self) -> str:
        """生成 Kubernetes 配置"""
        return """
### Deployment 配置

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: your-registry/backend:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

### ConfigMap 配置

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: "info"
  NODE_ENV: "production"
```

### Secret 配置

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
stringData:
  url: "postgresql://user:pass@host:5432/db"
```

### Ingress 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: app-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 80
```
"""
