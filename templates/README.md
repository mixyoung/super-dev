# Super Dev 配置模板

本目录包含各种 AI IDE 和工具的配置文件模板。

## 可用模板

### AI IDE 配置

| 文件 | 用途 | 适用于 |
|:---|:---|:---|
| `.cursorrules.template` | Cursor AI IDE 规则配置 | Cursor |
| `.windsurfrules.template` | Windsurf AI IDE 规则配置 | Windsurf (Codeium) |
| `continue-config.json.template` | Continue 扩展配置 | VS Code + Continue |

### 项目模板

| 文件 | 用途 | 适用于 |
|:---|:---|:---|
| `project-structure.md` | 标准项目结构 | 所有项目 |

## 使用方法

### Cursor 配置

```bash
# 复制模板到项目根目录
cp templates/.cursorrules.template .cursorrules

# 根据项目需求修改
vim .cursorrules

# 在 Cursor 中使用
# 1. 打开项目
# 2. Cursor 会自动加载 .cursorrules
# 3. 生成的代码会遵循这些规则
```

### Windsurf 配置

```bash
# 复制模板到项目根目录
cp templates/.windsurfrules.template .windsurfrules

# 根据项目需求修改
vim .windsurfrules

# 在 Windsurf 中使用
# 1. 打开项目
# 2. Windsurf 会自动加载 .windsurfrules
# 3. AI Chat 会遵循这些规则
```

### Continue 配置

```bash
# 复制配置
cp templates/continue-config.json.template ~/.continue/config.json

# 根据需求修改
vim ~/.continue/config.json

# 在 VS Code Continue 中使用
# Continue 会自动读取配置
```

## 快速开始

```bash
# 1. 使用 Super Dev 生成项目
super-dev pipeline "我的项目" \
  --platform web \
  --frontend react \
  --backend node

# 2. 安装 AI IDE 配置
cp templates/.cursorrules.template .cursorrules

# 3. 在 AI IDE 中实现代码
# 复制 output/*-ai-prompt.md 到 AI IDE
# AI 会根据配置规则生成代码
```

## 自定义规则

每个模板都包含以下部分:

### 1. 项目上下文
- 文档位置
- 技术栈信息
- 核心原则

### 2. 代码规范
- 功能实现要求
- 代码质量标准
- 测试要求
- 代码风格

### 3. 工作流程
- 如何使用 Super Dev 文档
- AI 工具最佳实践
- 团队协作指南

根据你的项目需求修改这些部分。

## 团队使用

```bash
# 1. 创建团队标准模板
mkdir team-standards
cp templates/*.template team-standards/

# 2. 自定义团队规范
vim team-standards/.cursorrules.template
vim team-standards/.windsurfrules.template

# 3. 在所有项目中使用
cp team-standards/.cursorrules.template /path/to/project/.cursorrules
```

## 最佳实践

### 1. 模板应该包含

- ✅ Super Dev 文档位置
- ✅ 技术栈信息
- ✅ 代码风格规范
- ✅ 质量标准
- ✅ 工作流程说明

### 2. 模板不应该包含

- ❌ 具体的实现细节
- ❌ 硬编码的值
- ❌ 项目特定的规则
- ❌ 过时的信息

### 3. 定期更新

- 当 Super Dev 有新功能时更新模板
- 根据团队反馈优化模板
- 保持模板和实际使用一致

## 问题排查

### Cursor 不加载 .cursorrules

确保:
- [ ] 文件在项目根目录
- [ ] 文件名是 `.cursorrules` (不是 `.cursorrules.template`)
- [ ] Cursor 已重启
- [ ] 文件格式正确

### Windsurf 不加载 .windsurfrules

确保:
- [ ] 文件在项目根目录
- [ ] 文件名是 `.windsurfrules`
- [ ] Windsurf 已重启
- [ ] AI Chat 已激活

### Continue 不读取配置

确保:
- [ ] 配置在 `~/.continue/config.json`
- [ ] JSON 格式正确
- [ ] Continue 扩展已启用
- [ ] VS Code 已重启

## 相关文档

- [集成指南](../docs/INTEGRATION_GUIDE.md) - 详细的 AI 工具集成说明
- [工作流指南](../docs/WORKFLOW_GUIDE.md) - 0-1 和 1-N+1 完整教程
- [主 README](../README.md) - Super Dev 项目说明

## 贡献

如果你创建了新的配置模板，欢迎提交 PR！

```bash
# 1. Fork 项目
# 2. 创建新模板
cp your-config.template templates/

# 3. 更新文档
vim templates/README.md

# 4. 提交 PR
```

---

**需要帮助？**
- GitHub: https://github.com/mixyoung/super-dev
- Issues: https://github.com/mixyoung/super-dev/issues
