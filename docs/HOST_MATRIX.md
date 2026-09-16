# Super Dev 统一接入宿主矩阵

> 从项目 README 迁出的完整宿主清单与逐宿主用法。普通用户先运行 `super-dev` 完成项目级接入；主 README 只保留入口摘要。

[返回项目 README](../README.md) · [宿主使用指南](./HOST_USAGE_GUIDE.md) · [宿主接入面说明](./HOST_INSTALL_SURFACES.md)

正式产品口径：

- 当前矩阵按 `CLI / IDE / 桌面助手` 分组
- `Codex` 和 `Codex CLI` 是两个不同宿主，`Claude` 和 `Claude Code` 也是两个不同宿主
- 默认采用项目优先注入：先写项目级接入面，再按需补齐用户 / 全局接入面

### CLI 宿主（12 个）

| 宿主 | 触发方式 | 终端入口 |
|------|----------|----------|
| Claude Code | `/super-dev 需求` | `super-dev` |
| Codex CLI | `$super-dev`；回退 `super-dev: 需求` | `super-dev` |
| OpenCode | `/super-dev 需求` | `super-dev` |
| Droid CLI | `/super-dev 需求`；比赛模式 `/super-dev-seeai`；回退 `super-dev: 需求` | `super-dev` |
| Gemini CLI | `/super-dev 需求` | `super-dev` |
| Kiro CLI | `/super-dev 需求` | `super-dev` |
| Cursor CLI | `super-dev: 需求` | `super-dev` |
| Copilot CLI | `super-dev: 需求` | `super-dev` |
| Qoder CLI | `/super-dev 需求` | `super-dev` |
| CodeBuddy CLI | `/super-dev 需求` | `super-dev` |
| Kimi Code | `super-dev: 需求`；显式入口 `/skill:super-dev 需求` | `super-dev` |
| Qwen Code | `/super-dev 需求` | `super-dev` |

### IDE 宿主（9 个）

| 宿主 | 触发方式 | 终端入口 |
|------|----------|----------|
| Antigravity | `/super-dev 需求` | `super-dev` |
| Cursor | `/super-dev 需求` | `super-dev` |
| Windsurf | `/super-dev 需求` | `super-dev` |
| Kiro | `/super-dev 需求` | `super-dev` |
| Trae IDE | `super-dev: 需求` | `super-dev` |
| TraeCN | `super-dev: 需求` | `super-dev` |
| CodeBuddy | `/super-dev 需求` | `super-dev` |
| CodeBuddyCN | `/super-dev 需求` | `super-dev` |
| Qoder | `/super-dev 需求` | `super-dev` |

### 桌面助手（5 个）

| 宿主 | 触发方式 | 终端入口 |
|------|----------|----------|
| Claude | `super-dev: 需求` | `super-dev` |
| Codex | App/Desktop: 在 `/` 列表里选择 `super-dev` | `super-dev` |
| WorkBuddy | `super-dev: 需求` | `super-dev` |
| Trae SOLO | `/super-dev 需求` | `super-dev` |
| Trae SOLOCN | `super-dev: 需求` | `super-dev` |

---

### 每个宿主如何使用

#### 1. Claude Code

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Claude Code 当前会话后，直接在同一会话里触发。

触发命令：
```text
/super-dev 你的需求
```
比赛模式：
```text
/super-dev-seeai 比赛需求
```

自然语言回退：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. 推荐作为首选 CLI 宿主。
2. 维护者如需核对接入面，可执行 `super-dev doctor --host claude-code`，确认项目根 `CLAUDE.md`、项目级 `.claude/CLAUDE.md`、可选 `.claude/settings*.json`、项目/用户级 skills 与 agents 一起生效。
3. Claude Code 当前按官方 `CLAUDE.md + settings + project/user skills + subagents` 模型对齐；`.claude/commands/` 仅作为兼容增强面保留，不再当主协议面。
4. 如需增强层，Super Dev 还会补齐 `.claude-plugin/marketplace.json` 与 `plugins/super-dev-claude/.claude-plugin/plugin.json`。

#### 2. Codex

安装：
```bash
super-dev
```

触发位置：
在项目目录完成接入后，重启 `codex`，然后在新的 Codex 会话里触发。

触发命令：
```text
Codex App/Desktop: 在 `/` 列表里选择 super-dev
Codex CLI: $super-dev
回退入口: super-dev: 你的需求
```

接入后是否需要重启：是

补充说明：
1. Codex App/Desktop 优先从 `/` 列表里直接选择 `super-dev`；这是已启用 Skill 的官方入口，不是项目级自定义 slash 文件。
2. Codex CLI 优先显式输入 `$super-dev`。
3. 如果当前已经在自然语言上下文里继续流程，也可以直接输入 `super-dev: 你的需求`。
4. 默认基础接入面是项目根 `AGENTS.md` 与项目级 `.agents/skills/super-dev/SKILL.md`；官方用户级 Skill `~/.agents/skills/super-dev/SKILL.md` 仍会安装，`CODEX_HOME/AGENTS.md`（默认 `~/.codex/AGENTS.md`）改为显式 `--with-user-surfaces` 时才写入。
5. 同时会额外生成可选的 repo plugin 增强层：`.agents/plugins/marketplace.json` + `plugins/super-dev-codex/.codex-plugin/plugin.json`，让 Codex App/Desktop 在 AGENTS + Skills 之外还能看到更完整的本地 plugin 面。
6. 更新器保留旧别名和用户改动；需要迁移命名时单独复核，不在更新中自动清理。
7. 如果旧会话没加载新 Skill，重启 `codex` 再试。
8. 无论使用 `/super-dev`、`$super-dev` 还是 `super-dev:`，都必须进入同一条 Super Dev 流程；长流程里继续修改、补充、确认或恢复时，优先沿用当前入口面。

#### 3. Gemini CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Gemini CLI 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 官方主面已经收口到 `GEMINI.md + settings + custom commands`；项目内优先检查 `GEMINI.md`、可选 `.gemini/settings.json` 和 `.gemini/commands/*.toml`。
2. `/super-dev` 是 Super Dev 注入后的自定义命令面，不是 Gemini CLI 自带内建命令；若命令未刷新，优先重开当前 Gemini CLI 会话。
3. `~/.gemini/skills/` 只作为兼容增强面保留，不再当默认主协议面。
4. 优先在同一会话中完成 research -> 三文档 -> 用户确认 -> Spec -> 前端运行验证 -> 后端/交付；若宿主支持联网，先让它完成同类产品研究。

#### 4. OpenCode

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 OpenCode 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 按 CLI slash 模式使用。
2. 若你使用全局命令目录，也建议保留项目级接入文件。

#### 5. Kiro CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Kiro CLI 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：是

补充说明：
1. Kiro CLI 当前优先使用宿主已暴露的 `/super-dev` 入口；如果当前会话只接受自然语言，再回退到 `super-dev: 需求`。
2. 官方接入面是 `AGENTS.md` + `.kiro/steering/super-dev.md` + `.kiro/skills/super-dev/SKILL.md`；全局增强面是 `~/.kiro/steering/super-dev.md` 与 `~/.kiro/skills/super-dev/SKILL.md`。
3. 完成接入后建议重开 Kiro CLI，让 steering 上下文与 skills 在新会话里一起生效。

#### 6. Cursor CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Cursor CLI 当前会话后触发。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. 适合终端内连续执行研究、文档和编码。
2. 官方项目上下文面是项目根 `AGENTS.md` 与 `.cursor/rules/`；根 `CLAUDE.md` 只继续作为兼容上下文，不再当默认主协议面。
3. 若项目上下文或规则面未刷新，可重开一次 Cursor CLI 会话；恢复已有流程时优先使用 Cursor CLI 自身的会话连续性。

#### 7. Qoder CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Qoder CLI 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 适合命令行流水线开发。
2. 若 slash 未生效，先确认 `AGENTS.md`、`.qoder/commands/super-dev.md` 已生成，并检查 `.qoder/rules/` 目录是否存在。
3. 官方接入面已切到 `AGENTS.md` + `.qoder/rules/super-dev.md` + `.qoder/commands/super-dev.md` + `.qoder/skills/` / `~/.qoder/AGENTS.md` + `~/.qoder/commands/` + `~/.qoder/skills/`；`.qoder/agents/` 继续只作为增强面。

#### 8. Copilot CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 Copilot CLI 会话后触发。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. 官方主面是 `AGENTS.md`、`.github/copilot-instructions.md`、`.github/skills/` 与 `.github/agents/`；显式启用用户级 surface 时，再确认 `~/.copilot/skills/`、`~/.copilot/agents/` 与 `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` 也已被会话读取。
2. 当前使用 `super-dev: 你的需求` 作为主触发方式，不走项目级 `/super-dev` 自定义 slash。
3. 若维护者需要排障或补齐接入面，再用 `super-dev doctor --host copilot-cli` 做确认。

#### 9. CodeBuddy CLI

安装：
```bash
super-dev
```

触发位置：
在项目目录启动 CodeBuddy CLI 会话后触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 在当前 CLI 会话中直接输入即可。
2. 官方主面是 `CODEBUDDY.md` + `.codebuddy/rules/` + `.codebuddy/commands/` + `.codebuddy/skills/` + `.codebuddy/agents/`，并补充 `~/.codebuddy/CODEBUDDY.md`。
3. 如果会话已提前打开，建议重新加载项目规则后再试。
4. 黑客松/比赛场景优先使用 `/super-dev-seeai`，让宿主按半小时节奏压缩 research、三文档、Spec 和一体化开发。

#### 10. Antigravity

安装：
```bash
super-dev
```

触发位置：
打开 Antigravity 的 Agent Chat / Prompt 面板，并确保当前工作区就是目标项目。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：是

补充说明：
1. Antigravity 当前按 `GEMINI.md + custom commands` 模式接入，`.agent/workflows` 继续作为推荐增强面。
2. 接入会写入项目级 `GEMINI.md`、`.gemini/commands/super-dev.toml`、`.agent/workflows/super-dev.md`。
3. 默认只写项目级 `GEMINI.md` 与项目内命令面；用户级 `~/.gemini/GEMINI.md` 与 `~/.gemini/commands/` 仅在显式 `--with-user-surfaces` 时写入，`~/.gemini/skills/` 继续只作为兼容增强层。
4. 完成接入后请重开 Antigravity 或至少新开一个 Agent Chat，再输入 `/super-dev 你的需求`。

#### 11. Cursor

安装：
```bash
super-dev
```

触发位置：
打开 Cursor 的 Agent Chat，并确保当前工作区就是目标项目。

触发命令：
```text
/super-dev 你的需求
```
比赛模式：
```text
/super-dev-seeai 比赛需求
```

接入后是否需要重启：否

补充说明：
1. 建议固定在同一个 Agent Chat 会话里完成整条流水线。
2. 如果项目规则没加载，先重新打开工作区或重新发起聊天。

#### 12. Windsurf

安装：
```bash
super-dev
```

触发位置：
打开 Windsurf 的 Agent Chat / Workflow 入口，在项目上下文内触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 当前按 `AGENTS.md + rules + workflow + skills` 模式适配。
2. 更适合在同一个 Workflow 里连续完成研究、文档、Spec 和编码。
3. 官方文档公开 `AGENTS.md`、`.windsurf/workflows/` 与 `.windsurf/skills/`；仓库继续把 `.windsurf/rules/` 保留为项目约束面。

#### 13. Kiro

安装：
```bash
super-dev
```

触发位置：
打开 Kiro IDE 的 Agent Chat / AI 面板，在项目上下文内触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：是

补充说明：
1. Kiro IDE 当前优先使用宿主已暴露的 `/super-dev` 入口；如果当前会话只接受自然语言，再回退到 `super-dev: 你的需求`。
2. 接入会写入项目级 `AGENTS.md`、`.kiro/steering/super-dev.md`、`.kiro/skills/super-dev/SKILL.md`，并补充全局 `~/.kiro/steering/super-dev.md` 与 `~/.kiro/skills/super-dev/SKILL.md`；旧 `~/.kiro/steering/AGENTS.md` 仍作为兼容面保留。
3. 如果 steering 或 skills 未加载，先重开项目窗口或新开一个 Agent Chat。

#### 14. Qoder

安装：
```bash
super-dev
```

触发位置：
打开 Qoder IDE 的 Agent Chat，在当前项目内触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. Qoder IDE 当前优先使用项目级 `AGENTS.md + commands + rules + skills` 模式，直接在 Agent Chat 输入 `/super-dev 你的需求`。
2. 若新增命令未出现，先确认 `AGENTS.md`、`.qoder/commands/super-dev.md` 已生成，并检查 `.qoder/rules/super-dev.md` 是否存在，再重新打开项目或新开一个 Agent Chat。
3. 官方接入面已切到 `AGENTS.md` + `.qoder/rules/super-dev.md` + `.qoder/commands/super-dev.md` + `.qoder/skills/` / `~/.qoder/AGENTS.md` + `~/.qoder/commands/` + `~/.qoder/skills/`；`.qoder/agents/` 继续只作为增强面。

#### 15. Trae IDE

安装：
```bash
super-dev
```

触发位置：
打开 Trae IDE 的 Agent Chat，在当前项目上下文内直接触发。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. Trae 当前使用 `super-dev: 你的需求` 作为主触发方式。
2. 默认只写项目级 `.trae/project_rules.md`、`.trae/rules.md`；用户级 `~/.trae/user_rules.md`、`~/.trae/rules.md` 改成显式 `--with-user-surfaces` 才写入；如果检测到兼容技能目录，也会增强安装 `~/.trae/skills/super-dev/SKILL.md`。
3. 完成接入后建议重开 Trae 或至少新开一个 Agent Chat，使规则生效；如果兼容 Skill 已安装，也会一起生效。
4. 随后按 `output/*` 与 `.super-dev/changes/*/tasks.md` 推进开发。

#### 16. CodeBuddy

安装：
```bash
super-dev
```

触发位置：
打开 CodeBuddy 的 Agent Chat，在项目上下文内触发。

触发命令：
```text
/super-dev 你的需求
```

接入后是否需要重启：否

补充说明：
1. 建议在项目级 Agent Chat 中使用，不要脱离项目上下文。
2. 先让宿主完成 research，再继续文档和编码。
3. 当前按 `CODEBUDDY.md` + `.codebuddy/rules/super-dev/RULE.mdc` + `.codebuddy/commands/` + `.codebuddy/agents/` + `.codebuddy/skills/` 接入。
4. 比赛场景建议固定在同一个 Agent Chat，会比频繁切换子会话更稳。

#### 17. Copilot (VS Code)

安装：
```bash
super-dev
```

触发位置：
打开 VS Code 的 Copilot Chat 面板，在项目上下文内触发。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. 当前使用 `super-dev: 你的需求` 作为主触发方式，通过项目规则文件驱动流程。
2. 若维护者需要排障或核对接入面，再用 `super-dev doctor --host vscode-copilot` 做确认。
3. 在同一个 Copilot Chat 会话里完成整条流水线效果最佳。

#### 18. Roo Code

安装：
```bash
super-dev
```

触发位置：
打开 Roo Code 的 Agent Chat / AI 面板，在项目上下文内触发。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. 当前使用 `super-dev: 你的需求` 作为主触发方式。
2. 默认写入项目级规则文件；若宿主提供官方用户级 Skill 目录，会同步增强安装 Skill，如需用户级协议/命令面再显式启用 `--with-user-surfaces`。
3. 若维护者需要排障或核对接入面，再用 `super-dev doctor --host roo-code` 做确认。

#### 19. Kilo Code

安装：
```bash
super-dev
```

触发位置：
打开 Kilo Code 的 Agent Chat / AI 面板，在项目上下文内触发。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. 当前使用 `super-dev: 你的需求` 作为主触发方式。
2. 默认写入项目级规则文件；若宿主提供官方用户级 Skill 目录，会同步增强安装 Skill，如需用户级协议/命令面再显式启用 `--with-user-surfaces`。
3. 如果规则未加载，先重开项目窗口或新开一个 Agent Chat。

#### 20. Cline

安装：
```bash
super-dev
```

触发位置：
打开 Cline 的 Agent Chat 面板，在项目上下文内触发。

触发命令：
```text
super-dev: 你的需求
```

接入后是否需要重启：否

补充说明：
1. 当前使用 `super-dev: 你的需求` 作为主触发方式。
2. 接入会写入项目级 `.clinerules/` 目录下的规则文件。
3. 若维护者需要排障或核对接入面，再用 `super-dev doctor --host cline` 做确认。
4. 在同一个 Agent Chat 会话里完成整条流水线效果最佳。

#### 21. Droid CLI

Droid CLI 走 Factory 官方宿主模型，无需额外插件包。核心接入面是：

- 项目根 `AGENTS.md`
- `.factory/rules/super-dev.md`
- `.factory/skills/super-dev/SKILL.md`
- `.factory/skills/super-dev-seeai/SKILL.md`
- 兼容增强面：`.factory/commands/super-dev.md`、`.factory/commands/super-dev-seeai.md`
- 用户级 `~/.factory/AGENTS.md` / `~/.factory/commands/` / `~/.factory/skills/`（默认不写；仅在显式 `--with-user-surfaces` 时补齐）

安装：
```bash
super-dev
```

在安装器里选择 `Droid CLI` 后，回到当前项目的 Droid 会话触发。

触发命令：
```text
/super-dev 你的需求
```
回退入口：
```text
super-dev: 你的需求
```
比赛模式：
```text
/super-dev-seeai 比赛需求
```
需要 headless 续跑时：
```bash
droid exec --session-id <id> "continue with next steps"
```

补充说明：
1. Droid CLI 需要在目标项目目录里启动，让当前 session 先读取项目根 `AGENTS.md`。
2. `.factory/rules/` 与 `.factory/skills/` 是主协议面；`.factory/commands/` 继续作为兼容增强面承担 slash 触发补充，不再需要额外插件。
3. 比赛场景优先使用 `/super-dev-seeai`；如果 slash 面板刷新慢，再回退到 `super-dev-seeai:`。
4. 恢复已有流程时优先保持同一 Droid session，不要重新开题。

