# 质量扫描来源清单

## ADDED Requirements

### Requirement: SCAN-001 Preserve scope while pruning

系统 SHALL 在进入所有相关消费者均排除的目录前剪枝，保留各消费者原后缀、路径、大小写和模式语义。未跟踪、非 Git、根目录源码不得遗漏；不新增数量截断。

#### Scenario: Large excluded tree
- GIVEN 项目包含有效源码和巨大的排除子树
- WHEN 执行质量扫描
- THEN 排除子树不被递归访问，正常文件集合与原规则一致

### Requirement: SCAN-002 Invocation-scoped reuse

系统 SHALL 在同次质量调用中共享路径发现；独立入口保持兼容，下一次调用重新建立清单，不跨项目缓存结果。

#### Scenario: Multiple consumers
- GIVEN 一次质量调用含规则、规格、架构和适用 UIUX 检查
- WHEN 消费者核对证据与读取源码
- THEN 共用本次清单，不为每个消费者重新遍历根目录

### Requirement: SCAN-003 Explicit documents

系统 SHALL 保留当前工作项的必要规格、PRD、架构、UIUX 与配置读取和内容摘要绑定；源码排除不排除明确文档。

#### Scenario: Documents inside output
- GIVEN 当前材料在 output 或 .super-dev 内
- WHEN 源码视图剪掉这些目录
- THEN 仍按原绑定显式读取必要材料，不回退他项

### Requirement: SCAN-004 Incomplete evidence blocks

系统 SHALL 明确报告应检路径枚举/读取失败或失效；必要扫描未完成不能通过，不能被高分抵消或旧报告替代。

#### Scenario: Unreadable source
- GIVEN 应检文件无法读取
- WHEN 执行检查
- THEN 报告受阻及相对位置，不发布可通过结果

### Requirement: SCAN-005 Freshness and safety

系统 SHALL 在报告持久化前核对本次输入有效性；不跟随目录链接越界或循环，不以修改时间替代现有内容摘要；保持 persist=False 只读。

#### Scenario: File added during checking
- GIVEN 同次调用已建立清单
- WHEN 应检文件新增、删除或重命名
- THEN 拒绝以过期清单给出可通过结论，下次调用重新发现

### Requirement: SCAN-006 Existing gates remain

系统 SHALL 保留原阶段、质量评分与阈值、时限和清理机制，不把本批定向验证说成整仓发布就绪。

#### Scenario: Normal complete inputs
- GIVEN 输入完整且可读
- WHEN 优化前后执行相同检查
- THEN 关键发现、分数和必检项保持一致
