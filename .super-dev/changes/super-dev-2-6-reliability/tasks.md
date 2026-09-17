# Tasks: Super Dev 2.6 可靠性收敛

## 1. 文档与身份

- [x] 1.1 完成 baseline、research、PRD、architecture、UI/UX 并取得最终确认
- [x] 1.2 绑定 `super-dev-2-6-reliability`、文档摘要和正式 change
- [x] 1.3 创建 proposal、plan、tasks、checklist、Spec、adoption 与只读影子账本
- [x] 1.4 最终按实际改动更新 adoption 文件清单、证据和回退

## 2. 唯一状态入口

- [x] 2.1 新增状态存储与错误模型，定义 `revision`、锁和提交结果
- [x] 2.2 实现 Windows/POSIX 文件锁、原子状态提交、历史快照和审计刷新
- [x] 2.3 让现有 workflow state 写入委托统一服务，保留旧 Schema 读取
- [x] 2.4 增加修订冲突、损坏当前状态、事件尾行损坏和恢复候选测试

## 3. 会话摘要与旧状态文件退出

- [x] 3.1 会话简报增加来源工作项和状态修订，统一为一个生产生成入口
- [x] 3.2 移除工作流引擎对旧 SessionBrief 分段格式的生产写入
- [x] 3.3 引擎阶段进度改写统一状态并继续记录阶段/专家证据
- [x] 3.4 专家阶段治理改读统一状态和阶段记录
- [x] 3.5 一次性迁移并删除旧 `pipeline-state.json`，记录来源摘要和迁移结果
- [x] 3.6 删除生产代码、Skill 和当前文档中的旧状态文件引用

## 4. 统一证据

- [x] 4.1 新增统一证据信封、状态和制品模型
- [x] 4.2 当前代码版本身份成为唯一候选摘要算法，区分代码、输入和制品摘要
- [x] 4.3 让 Fresh Verification、质量、发布就绪和证据包消费统一身份语义
- [x] 4.4 增加代码变化、工作项变化、输入变化和字段缺失的失效测试

## 5. 发布事实闭环

- [x] 5.1 新增发布观察记录，绑定版本、标签、提交、仓库、制品和摘要
- [x] 5.2 发布成功后更新 `released` 与当前状态，不推导 deployed/operating
- [x] 5.3 覆盖本地构建、仅 tag、草稿、外部已发布但本地未记录和失败路径

## 6. 版本 2.6.0

- [x] 6.1 统一包、配置、品牌、Skill、README、CHANGELOG、发布说明和锁文件版本
- [x] 6.2 构建 wheel/sdist，校验元数据、安装路径和 SHA256

## 7. 验证与交付

- [x] 7.1 运行状态/证据/迁移定向测试和受影响回归
- [x] 7.2 运行全量 pytest、Ruff、Black、Mypy、compileall 与 diff check；CLI 功能用例 227/227 通过，但会话收尾捕获到外部程序重写 Gemini 用户配置，单列为隔离阻断
- [x] 7.3 运行 Skill 同步、贡献范围、Windows/用户目录隔离验证；Skill/贡献范围通过，用户目录异常保持未覆盖并如实记录
- [x] 7.4 运行 Fresh Verification、Quality Gate、Release Readiness、Proof Pack；初轮阻断已保留，最终候选冻结后重跑
- [x] 7.5 独立只读复审本轮不适用：未获授权启动子代理或外部评审，不声称已完成独立复审
- [x] 7.6 汇总真实 PASS/FAIL/BLOCKED 与未验证项；不自行合并、发布或部署
- [x] 7.7 修复 Fresh Verification 长时运行的输出管道拖住、后台子进程清理和无心跳问题，并保持原测试范围与阈值
