# 代码专家（CODE）操作手册

> 使用范围：这是 CODE 的按需方法参考，职责与交接见[专家设定](../builtin/CODE.md)。按当前请求选择相关章节，复用已有决定；示例数值、模板和流程不自动成为新需求或覆盖项目已确认门禁。只读审查给出发现，实施和外部操作依据已有授权。

## 概述

代码专家负责代码质量的守护，核心职责包括代码审查、编码规范制定、性能优化、错误处理标准化和技术债务管理。目标是确保代码库在功能正确的基础上，保持可读、可维护、可测试。

### 核心原则

1. **可读性优先**：代码是写给人看的，顺便给机器执行
2. **单一职责**：每个函数/类/模块只做一件事
3. **显式优于隐式**：依赖关系、副作用、错误条件都应显式表达
4. **持续重构**：在添加新功能时改善相关代码，而非积累技术债

---

## 方法论

### 一、代码审查方法论

#### 1.1 审查维度与优先级

审查顺序按影响程度从高到低：

| 优先级 | 维度 | 说明 |
|--------|------|------|
| P0 | 正确性 | 逻辑是否正确，边界条件是否处理 |
| P0 | 安全性 | 是否有注入/越权/信息泄露风险 |
| P1 | 设计 | 架构是否合理，职责是否清晰 |
| P1 | 错误处理 | 异常是否捕获/传播/记录 |
| P2 | 性能 | 是否有明显的性能问题 |
| P2 | 可测试性 | 是否方便编写单元测试 |
| P3 | 可读性 | 命名/注释/代码组织 |
| P3 | 规范一致性 | 是否符合项目编码规范 |

#### 1.2 审查反馈格式

```
[级别] 文件:行号 - 问题描述

级别说明：
  MUST:    必须修改，阻断合并
  SHOULD:  强烈建议修改
  COULD:   可选优化建议
  NOTE:    信息性备注
  PRAISE:  值得表扬的实践
```

示例：
```
[MUST] src/auth/handler.py:45 - SQL 查询使用字符串拼接，存在注入风险。
应使用参数化查询: cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

[SHOULD] src/api/routes.py:120 - 函数 process_order 有 85 行，建议拆分为
验证、处理、通知三个子函数。

[PRAISE] src/utils/retry.py - 重试逻辑抽象得很好，支持指数退避和自定义异常过滤。
```

#### 1.3 审查流程

1. 先看 PR 描述，理解变更目的
2. 看测试代码，理解预期行为
3. 看核心逻辑变更
4. 看错误处理和边界条件
5. 看配置和基础设施变更
6. 全局审视：模块间交互是否合理

### 二、代码质量标准

#### 2.1 函数设计

| 指标 | 参考值 | 说明 |
|------|------|------|
| 函数行数 | ≤ 40 行 | 超过则考虑拆分 |
| 参数个数 | ≤ 5 个 | 结合接口语义判断是否使用参数对象 |
| 嵌套深度 | ≤ 3 层 | 超过则使用 early return 或提取函数 |
| 圈复杂度 | ≤ 10 | 超过时检查可读性与分支测试，再决定是否拆分 |
| 认知复杂度 | ≤ 15 | SonarQube 标准 |

#### 2.2 命名规范

**通用原则**：
- 变量名描述"是什么"，函数名描述"做什么"
- 布尔变量/函数使用 is/has/can/should 前缀
- 避免缩写（除非是领域内广泛认知的：`id`/`url`/`http`/`api`）
- 集合变量使用复数：`users`/`order_items`

**Python 特定**：
```python
# 模块: snake_case
user_service.py

# 类: PascalCase
class OrderProcessor:

# 函数/方法: snake_case
def calculate_total_price():

# 常量: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# 私有: 前缀下划线
def _validate_input():
_internal_cache = {}
```

**TypeScript 特定**：
```typescript
// 接口/类型: PascalCase
interface UserProfile {}
type OrderStatus = 'pending' | 'completed';

// 函数/变量: camelCase
function calculateTotalPrice() {}
const maxRetryCount = 3;

// 组件: PascalCase
function UserProfileCard() {}

// 常量: UPPER_SNAKE_CASE 或 camelCase
const API_BASE_URL = '/api/v1';
```

#### 2.3 注释要求

**需要注释的场景**：
- 为什么这样做（业务原因/历史原因/性能原因）
- 非直觉的算法/逻辑
- 临时解决方案（必须标注 TODO/FIXME + 原因 + 计划修复时间）
- 公共 API 的文档注释

**不需要注释的场景**：
- 代码自身能解释的逻辑（命名清晰即不需要注释）
- 变更日志（使用 git 记录）

**TODO/FIXME 规范**：
```python
# TODO(weiyou): 当用户量超过 10 万时需要引入分页缓存 [2026-Q2]
# FIXME: 这里的时区处理在夏令时切换时会有 1 小时偏差 #issue-123
```

### 三、错误处理规范

#### 3.1 异常层级

```
应用异常基类 (AppError)
├── 业务异常 (BusinessError)
│   ├── ValidationError      — 输入验证失败 (400)
│   ├── NotFoundError        — 资源不存在 (404)
│   ├── ConflictError        — 资源冲突 (409)
│   └── ForbiddenError       — 业务规则阻止 (422)
├── 基础设施异常 (InfraError)
│   ├── DatabaseError        — 数据库操作失败
│   ├── CacheError           — 缓存操作失败
│   ├── ExternalServiceError — 外部服务调用失败
│   └── MessageQueueError    — 消息队列操作失败
└── 系统异常 (SystemError)
    ├── ConfigurationError   — 配置错误
    └── UnexpectedError      — 未预期的错误
```

#### 3.2 错误处理原则

1. **不吞掉异常**：`except: pass` 是严重的反模式
2. **捕获具体异常**：避免 `except Exception`，捕获具体类型
3. **添加上下文**：重新抛出时添加有用的上下文信息
4. **分层处理**：业务层抛出业务异常，基础设施层抛出基础设施异常
5. **统一转换**：在 API 层将异常统一转换为 HTTP 响应

```python
# 反模式
try:
    result = do_something()
except:
    pass

# 正确做法
try:
    result = do_something()
except SpecificError as e:
    logger.warning("操作失败: %s, user_id=%s", e, user_id)
    raise BusinessError(f"无法完成操作: {e}") from e
```

#### 3.3 日志级别

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| ERROR | 需要立即关注的错误 | 数据库连接失败、外部服务不可用 |
| WARNING | 不正常但可恢复的情况 | 重试成功、降级处理、接近限流 |
| INFO | 关键业务事件 | 用户登录、订单创建、支付完成 |
| DEBUG | 开发调试信息 | 函数参数、中间计算结果 |

**日志格式要求**：
```python
# 必须包含：时间、级别、模块、关联ID、消息
logger.info(
    "订单创建成功",
    extra={
        "request_id": request_id,
        "user_id": user_id,
        "order_id": order_id,
        "amount": amount,
    }
)
```

#### 3.4 重试策略

```python
# 指数退避 + 抖动
retry_config = {
    "max_retries": 3,
    "base_delay": 1.0,        # 秒
    "max_delay": 30.0,        # 秒
    "exponential_base": 2,
    "jitter": True,           # 随机抖动防止雷群效应
    "retryable_errors": [
        ConnectionError,
        TimeoutError,
        HTTPError(status=503),
    ],
    "non_retryable_errors": [
        ValidationError,
        AuthenticationError,
        HTTPError(status=400),
        HTTPError(status=401),
        HTTPError(status=403),
    ],
}
```

### 四、性能审查

#### 4.1 N+1 查询

**识别方式**：
- 循环中调用数据库查询
- ORM 的 lazy loading 在循环中触发

**修复方式**：
```python
# 反模式: N+1 查询
for order in orders:
    items = db.query(OrderItem).filter_by(order_id=order.id).all()

# 正确: 使用 JOIN 或 batch 加载
orders = db.query(Order).options(joinedload(Order.items)).all()
# 或
order_ids = [o.id for o in orders]
items = db.query(OrderItem).filter(OrderItem.order_id.in_(order_ids)).all()
```

#### 4.2 内存泄漏

**常见原因**：
- 全局变量/类变量持有大对象引用
- 事件监听器未取消注册
- 缓存无上限增长
- 闭包意外捕获大对象

**检测方式**：
- Python: `tracemalloc`、`objgraph`、`memory_profiler`
- Node.js: `--inspect` + Chrome DevTools Heap Snapshot
- 生产环境: 监控进程 RSS 内存趋势

#### 4.3 连接池

| 资源 | 默认池大小 | 注意事项 |
|------|-----------|---------|
| 数据库 | 5-20 | 不超过数据库最大连接数 / 应用实例数 |
| Redis | 10-50 | 注意 pipeline 和 pub/sub 不共享连接 |
| HTTP 客户端 | 10-100 | 按目标主机分池 |

**连接池检查项**：
- [ ] 是否设置了最大连接数
- [ ] 是否设置了连接超时
- [ ] 是否设置了空闲超时
- [ ] 是否有连接泄漏检测
- [ ] 是否在优雅关闭时释放连接

#### 4.4 缓存策略

- 识别读多写少的热点数据
- 设置合理的 TTL（不是永不过期）
- 考虑缓存一致性（写后失效 vs 写后更新）
- 大 Value 注意序列化/反序列化开销
- 缓存 Key 要有命名空间和版本号

---

## 代码审查检查清单

### 正确性（7 项）

- [ ] 功能是否符合需求描述
- [ ] 边界条件是否处理（空值/零/最大值/空集合）
- [ ] 并发场景是否安全（竞态条件/死锁）
- [ ] 数据类型是否正确（整数溢出/浮点精度/时区）
- [ ] 资源是否正确释放（文件句柄/连接/锁）
- [ ] 幂等性是否保证（重复调用不产生副作用）
- [ ] 向后兼容性是否维护（API/数据库/配置）

### 设计（6 项）

- [ ] 是否符合单一职责原则
- [ ] 依赖关系是否合理（不存在循环依赖）
- [ ] 抽象层级是否一致（同一函数内操作在同一抽象层）
- [ ] 是否有不必要的耦合
- [ ] 是否过度抽象（YAGNI 原则）
- [ ] 接口设计是否稳定（变更不影响调用方）

### 错误处理（5 项）

- [ ] 所有可能失败的操作是否有错误处理
- [ ] 异常是否传播到正确的层级
- [ ] 错误信息是否有足够的上下文
- [ ] 重试逻辑是否有退避和上限
- [ ] 降级策略是否合理

### 性能（6 项）

- [ ] 是否有 N+1 查询
- [ ] 大数据量操作是否分批处理
- [ ] 是否有不必要的重复计算
- [ ] 字符串拼接是否在循环中（应使用 join/builder）
- [ ] 是否有不必要的同步阻塞
- [ ] 缓存使用是否合理

### 可读性（5 项）

- [ ] 命名是否清晰表达意图
- [ ] 复杂逻辑是否有注释说明原因
- [ ] 代码组织是否逻辑清晰
- [ ] 是否有魔术数字（应使用命名常量）
- [ ] 函数长度是否合理（≤ 40 行）

### 测试（4 项）

- [ ] 核心逻辑是否有单元测试
- [ ] 边界条件是否有测试覆盖
- [ ] 异常路径是否有测试
- [ ] 测试是否可重复运行（不依赖外部状态）

---

## 交叉审查要点

### 审查架构师输出时

- 模块拆分是否有利于代码复用
- API 设计是否符合实际编码模式
- 技术选型是否有足够的社区支持和文档

### 审查 QA 输出时

- 测试用例是否覆盖了关键路径和边界条件
- 测试代码本身的质量是否合格
- mock/stub 使用是否合理（不过度 mock）

### 审查安全专家输出时

- 安全需求是否可以在当前代码架构下高效实现
- 安全措施是否引入了过高的代码复杂度

---

## 常见反模式

### 1. 上帝对象（God Object）

**症状**：一个类/模块包含几百个方法，处理所有业务逻辑

**修复**：按职责拆分为多个类/模块

### 2. 复制粘贴编程

**症状**：相同或类似的代码出现在多个地方

**修复**：提取公共函数/基类/工具模块

### 3. 过早优化

**症状**：在没有性能问题时就引入复杂的优化方案

**修复**：先写正确的代码，有性能瓶颈时再用 profiler 定位优化点

### 4. 异常吞噬

**症状**：`except: pass` 或空的 catch 块

**修复**：在适当边界保留诊断信息并明确失败传播，避免重复记录或泄露敏感数据

### 5. 魔术数字/字符串

**症状**：代码中出现 `if status == 3` 或 `if role == "admin"`

**修复**：使用枚举或命名常量

### 6. 深层嵌套

**症状**：多层 if/for 嵌套，代码向右飘移

**修复**：使用 early return、提取函数、使用 guard clause

---

## 知识依据

该专家依赖以下知识库文件：

- `knowledge/development/01-standards/python-complete.md` — Python 编码标准
- `knowledge/development/01-standards/javascript-typescript-complete.md` — JS/TS 编码标准
- `knowledge/development/01-standards/golang-complete.md` — Go 编码标准
- `knowledge/development/01-standards/rust-complete.md` — Rust 编码标准
- `knowledge/development/01-standards/performance-optimization-complete.md` — 性能优化标准
- `knowledge/development/01-standards/git-complete.md` — Git 使用规范
