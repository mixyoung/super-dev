# /super-dev (openclaw)

在当前项目触发 Super Dev 流水线式开发编排。

## 输入
- 需求描述: `$ARGUMENTS`
- 如果未提供参数，先要求用户补全需求后再执行。

## 定位边界（强制）

- **OpenClaw Agent 负责**：调用模型、联网搜索、文件读写、终端执行、代码生成与修改。
- **Super Dev 负责**：流程规范、设计约束、质量门禁、审计产物与交付标准。
- 需要生成治理产物时，用 `exec` 调用 `super-dev` CLI。
- 需要研究、设计、编码、运行时，直接使用 OpenClaw 自身能力。

## 10 位专家角色（按阶段自动切换）

| 角色 | 职责 | 阶段 |
|------|------|------|
| PM | 需求分析、PRD | research, docs |
| ARCHITECT | 架构设计、API、选型 | docs, spec |
| UI | 视觉设计、Token 系统 | docs, frontend |
| UX | 交互设计、用户旅程 | docs, frontend |
| SECURITY | 安全审查、OWASP | redteam, backend |
| CODE | 代码实现、审查 | frontend, backend |
| DBA | 数据库建模、索引 | backend |
| QA | 测试策略、质量门禁 | quality |
| DEVOPS | CI/CD、部署、监控 | delivery |
| RCA | 根因分析、故障排查 | bugfix |

## 首轮响应契约（首次触发必须执行）

用户输入 `/super-dev`、`super-dev:` 或 `super-dev：` 后，第一轮回复**必须**：

1. 声明"Super Dev 流水线已激活，不是普通聊天"
2. 读取 `.super-dev/WORKFLOW.md` 和 `output/*-bootstrap.md`（若存在）
3. 声明当前阶段是 `research`，先读知识库再联网研究
4. 承诺阶段顺序：research → 三文档 → 确认 → Spec → 前端 → 后端 → 质量 → 交付
5. 承诺三文档完成后暂停等确认，不自行创建 Spec 或编码

## 本地知识库契约（强制）

1. 读取 `knowledge/` 目录中与需求相关的知识文件
2. 读取 `output/knowledge-cache/*-knowledge-bundle.json`（若存在）
3. 命中的知识是**硬约束**（标准必须遵循、检查清单必须通过、反模式必须回避）
4. 约束必须继承到 PRD、架构、UIUX、Spec、实现的每个环节

## 完整流水线（9 阶段 + 2 门禁）

### Stage 1: Research
```bash
super-dev pipeline "$ARGUMENTS" --frontend react --backend node
```
- 使用 OpenClaw 的 web_search 研究 3-5 个同类产品
- 产出: `output/*-research.md`

### Stage 2: Docs（三份核心文档）
- 产出: `output/*-prd.md`, `output/*-architecture.md`, `output/*-uiux.md`

### DOC_CONFIRM_GATE — 强制暂停
```
三份核心文档已完成。请查看后确认：
  super-dev review docs --status confirmed --comment "已确认"
  super-dev run --resume
```
**未经确认不得创建 Spec 或编码。**

### Stage 3: Spec
```bash
super-dev spec propose <change-id> --title "标题"
```

### Stage 4: Frontend
- 按 tasks.md 实现前端，做到可预览
- `super-dev run frontend` 验证

### PREVIEW_CONFIRM_GATE — 强制暂停
```
前端已完成，请预览效果。不满意请说明修改要求。
```

### Stage 5-9: Backend → Quality → Code Review → Deploy → Delivery
```bash
super-dev quality                    # 红队审查 + 质量门禁
super-dev deploy --cicd github       # CI/CD 配置
super-dev release readiness          # 发布就绪度
super-dev release proof-pack         # 交付证据包
```

## UI/UX 强制规则

- **禁止** emoji 充当功能图标
- **禁止** 紫/粉渐变主视觉（AI 模板感）
- **禁止** 默认系统字体直出
- **必须** 先定义设计 Token（颜色/字体/间距/圆角/阴影）再实现页面
- **必须** 组件有完整状态（hover/focus/loading/empty/error/disabled）
- **必须** 真实内容测试排版（非 lorem ipsum）

## 返工协议

### UI 返工
1. 更新 `output/*-uiux.md`
2. 重做前端 → `super-dev run frontend` → `super-dev review ui --status confirmed`

### 架构返工
1. 更新 `output/*-architecture.md`
2. 同步 tasks → 重新实现 → `super-dev review architecture --status confirmed`

### 质量返工
1. 修复问题 → `super-dev quality` → `super-dev review quality --status confirmed`

### 未决事项与核心文档纯净
1. 挂起决策或临时妥协统一记入 `.super-dev/parking-lot.json`（`super-dev parking add`），禁止向核心 PRD/架构文档写入 `TBD`/待定补丁
2. 条件成熟需要解除时，必须先将最终定论写回对应核心文档，再引用真实 `#anchor` 执行 `super-dev parking resolve`

## 高频快捷 Tool

| Tool | 用途 | 示例 |
|------|------|------|
| `super_dev_confirm` | 快捷门禁确认 | `gate: "docs"` |
| `super_dev_jump` | 阶段跳转 | `stage: "frontend"` |
| `super_dev_task` | 任务管理 | `action: "list"` |
| `super_dev_fix` | 缺陷修复流水线 | `description: "登录页白屏"` |
| `super_dev_governance` | 治理管理 | `action: "status"` |
| `super_dev_product_audit` | 产品审查 | 无参数 |
| `super_dev_metrics` | 度量查看 | `format: "json"` |

## 恢复与状态

```bash
super-dev status          # 查看流水线状态
super-dev run --resume    # 从中断处继续
super-dev jump frontend   # 跳转到指定阶段
super-dev confirm docs    # 快捷确认门禁
```

## 汇报格式（每次回复包含）

```
[Stage N/9] 阶段名
  产出: 文件路径
  下一步: 具体动作
```

## System Flow Contract
- SUPER_DEV_FLOW_CONTRACT_V1
- PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery
- DOC_CONFIRM_GATE: required
- PREVIEW_CONFIRM_GATE: required
- HOST_PARITY: required
