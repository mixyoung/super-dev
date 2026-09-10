"""Static host catalog and compatibility contracts."""

from __future__ import annotations

from .models import IntegrationTarget


class IntegrationCatalogMixin:
    TEXT_TRIGGER_PREFIX = "super-dev:"

    TEXT_TRIGGER_PREFIX_FULLWIDTH = "super-dev："

    SEEAI_TEXT_TRIGGER_PREFIX = "super-dev-seeai:"

    SEEAI_TEXT_TRIGGER_PREFIX_FULLWIDTH = "super-dev-seeai："

    CODEX_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV CODEX -->"

    CODEX_AGENTS_END = "<!-- END SUPER DEV CODEX -->"

    OPENCODE_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV OPENCODE -->"

    OPENCODE_AGENTS_END = "<!-- END SUPER DEV OPENCODE -->"

    QODER_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV QODER -->"

    QODER_AGENTS_END = "<!-- END SUPER DEV QODER -->"

    CURSOR_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV CURSOR -->"

    CURSOR_AGENTS_END = "<!-- END SUPER DEV CURSOR -->"

    KIRO_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV KIRO -->"

    KIRO_AGENTS_END = "<!-- END SUPER DEV KIRO -->"

    DROID_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV DROID -->"

    DROID_AGENTS_END = "<!-- END SUPER DEV DROID -->"

    COPILOT_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV COPILOT -->"

    COPILOT_AGENTS_END = "<!-- END SUPER DEV COPILOT -->"

    KIMI_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV KIMI -->"

    KIMI_AGENTS_END = "<!-- END SUPER DEV KIMI -->"

    TRAE_SOLO_AGENTS_BEGIN = "<!-- BEGIN SUPER DEV TRAE SOLO -->"

    TRAE_SOLO_AGENTS_END = "<!-- END SUPER DEV TRAE SOLO -->"

    CLAUDE_RULES_BEGIN = "<!-- BEGIN SUPER DEV CLAUDE -->"

    CLAUDE_RULES_END = "<!-- END SUPER DEV CLAUDE -->"

    NO_SKILL_TARGETS: set[str] = {
        "claude",
        "cline",
        "kilo-code",
        "vscode-copilot",
    }

    HOST_USAGE_LOCATIONS: dict[str, str] = {
        "antigravity": "打开 Antigravity 的 Agent Chat / Prompt 面板，并确保当前工作区就是目标项目。",
        "claude": "打开 Claude Desktop 当前 Project，对准目标项目的 instructions / knowledge / extensions 后触发。",
        "claude-code": "在项目目录启动 Claude Code 当前会话后，直接在同一会话里触发。",
        "cline": "在 VS Code 的 Cline 面板中，绑定当前项目后触发。",
        "codebuddy-cli": "在项目目录启动 CodeBuddy CLI 会话后触发。",
        "codebuddy": "打开 CodeBuddy 的 Agent Chat，在项目上下文内触发。",
        "codebuddy-cn": "打开 CodeBuddyCN IDE 的 Agent Chat，在项目上下文内触发。",
        "droid-cli": "在项目目录启动 Droid CLI 会话后触发，优先沿用当前 Factory session；需要无界面续跑时再用 droid exec。",
        "codex": "打开 Codex App/Desktop 当前会话，并确保工作区就是目标项目后触发。",
        "codex-cli": "在项目目录完成接入后，重启 codex，然后在新的 Codex 会话里触发。",
        "copilot-cli": "在项目目录启动 Copilot CLI 会话后触发。",
        "cursor-cli": "在项目目录启动 Cursor CLI 当前会话后触发。",
        "cursor": "打开 Cursor 的 Agent Chat，并确保当前工作区就是目标项目。",
        "windsurf": "打开 Windsurf 的 Agent Chat 或 Workflow 入口，在项目上下文内触发。",
        "gemini-cli": "在项目目录启动 Gemini CLI 会话后触发。",
        "kimi-code": "在项目目录启动 Kimi Code 会话后触发，优先沿用同一个 session。",
        "kiro-cli": "在项目目录启动 Kiro CLI 会话后触发。",
        "opencode": "在项目目录启动 OpenCode 会话后触发。",
        "qoder-cli": "在项目目录启动 Qoder CLI 会话后触发。",
        "qwen-code": "在项目目录启动 Qwen Code 会话后触发，优先沿用当前 session 的 /resume 能力；/restore 仅用于 checkpoint 回滚。",
        "roo-code": "在 VS Code 的 Roo Code 聊天面板中触发。",
        "vscode-copilot": "在 VS Code Copilot Chat 绑定当前项目后触发。",
        "kilo-code": "在 VS Code 的 Kilo Code 聊天面板中触发。",
        "kiro": "打开 Kiro IDE 的 Agent Chat 或 AI 面板，在项目上下文内触发。",
        "qoder": "打开 Qoder IDE 的 Agent Chat，在当前项目内触发。",
        "trae": "打开 Trae IDE Agent Chat，在当前项目上下文内直接触发。",
        "trae-cn": "打开 TraeCN IDE 当前工作区，在项目上下文内直接触发。",
        "trae-solo": "打开 Trae SOLO Desktop/Web 工作区，在当前项目上下文内直接触发。",
        "trae-solocn": "打开 Trae SOLOCN 当前工作区，在目标项目上下文内直接触发。",
        "workbuddy": "打开 WorkBuddy 当前任务/对话会话，并确保工作目录或授权文件夹指向目标项目后触发。",
    }

    @classmethod
    def _managed_agents_markers(cls, target: str) -> tuple[str, str] | None:
        markers = {
            "codex": (cls.CODEX_AGENTS_BEGIN, cls.CODEX_AGENTS_END),
            "codex-cli": (cls.CODEX_AGENTS_BEGIN, cls.CODEX_AGENTS_END),
            "opencode": (cls.OPENCODE_AGENTS_BEGIN, cls.OPENCODE_AGENTS_END),
            "qoder": (cls.QODER_AGENTS_BEGIN, cls.QODER_AGENTS_END),
            "qoder-cli": (cls.QODER_AGENTS_BEGIN, cls.QODER_AGENTS_END),
            "cursor": (cls.CURSOR_AGENTS_BEGIN, cls.CURSOR_AGENTS_END),
            "cursor-cli": (cls.CURSOR_AGENTS_BEGIN, cls.CURSOR_AGENTS_END),
            "kiro": (cls.KIRO_AGENTS_BEGIN, cls.KIRO_AGENTS_END),
            "kiro-cli": (cls.KIRO_AGENTS_BEGIN, cls.KIRO_AGENTS_END),
            "droid-cli": (cls.DROID_AGENTS_BEGIN, cls.DROID_AGENTS_END),
            "copilot-cli": (cls.COPILOT_AGENTS_BEGIN, cls.COPILOT_AGENTS_END),
            "kimi-code": (cls.KIMI_AGENTS_BEGIN, cls.KIMI_AGENTS_END),
            "trae-solo": (cls.TRAE_SOLO_AGENTS_BEGIN, cls.TRAE_SOLO_AGENTS_END),
        }
        return markers.get(target)

    HOST_USAGE_NOTES: dict[str, list[str]] = {
        "antigravity": [
            "Antigravity 当前优先按 `GEMINI.md + custom commands` 模式接入，`.agent/workflows/` 继续作为当前推荐增强面。",
            "项目内会写入 `GEMINI.md`、`.gemini/commands/super-dev.toml` 与 `.agent/workflows/super-dev.md`。",
            "默认只写项目级 `GEMINI.md` 与项目命令面；用户级 `~/.gemini/GEMINI.md`、`~/.gemini/commands/` 仅在显式 `--with-user-surfaces` 时补齐，`~/.gemini/skills/` 继续只作为兼容增强层。",
            "接入后建议新开一个 Antigravity Chat，使 GEMINI 上下文、custom command 与推荐 workflow 一起生效。",
        ],
        "claude": [
            "Claude Desktop 当前官方优先面是 Projects、Project Instructions、Project Knowledge 与 desktop extensions / local MCP。",
            "Super Dev 不再假装 Claude Desktop 存在稳定的项目级 dotfile 自动注入；默认按 Project 模板和会话继续心智来适配。",
            "如果你需要最强项目内文件注入与可重复执行，优先选择 Claude Code；Claude Desktop 更适合项目审阅、方向确认与轻量协作。",
        ],
        "claude-code": [
            "推荐作为首选 CLI 宿主之一。",
            "若维护者需要核对接入面，可执行 super-dev doctor --host claude-code，确认根 `CLAUDE.md`、`.claude/CLAUDE.md`、可选 `.claude/settings*.json`、`.claude/skills/`、`.claude/agents/` 与可选 plugin enhancement 一起生效。",
            "Claude Code 当前更接近官方主模型：项目根 `CLAUDE.md`、可选 `.claude/settings*.json`、项目/用户 `.claude/skills/` 与项目/用户 `.claude/agents/` 是正式主面。",
            "`.claude/commands/` 仅保留为兼容增强面，不再作为唯一主接入面。",
            "仓库内还会额外生成可选的 repo plugin enhancement：`.claude-plugin/marketplace.json` + `plugins/super-dev-claude/.claude-plugin/plugin.json`。",
        ],
        "cline": [
            "Cline 优先使用 `.clinerules/` 规则目录，并补充项目级 `.cline/skills/` 让宿主在当前工作区内直接理解 Super Dev 协议。",
            "用户级 `~/.cline/skills/super-dev/SKILL.md` 会作为全局增强面一起安装。",
            "当前按文本触发 `super-dev: <需求描述>` 适配，减少与内建 slash 的语义冲突。",
        ],
        "codebuddy-cli": [
            "在当前 CLI 会话中直接输入即可。",
            "如果会话早于接入动作启动，建议重开会话后再试。",
            "官方文档已公开 `CODEBUDDY.md`、`.codebuddy/rules/`、`.codebuddy/commands/`、`.codebuddy/skills/`、`.codebuddy/agents/` 与对应用户级目录。",
            "比赛场景优先使用 `/super-dev-seeai` 或 `super-dev-seeai:`，让宿主按半小时时间盒压缩 research / 文档 / spec / 一体化开发。",
        ],
        "codebuddy": [
            "建议在项目级 Agent Chat 中使用，不要脱离项目上下文。",
            "先让宿主完成 research，再继续文档和编码。",
            "官方文档对 IDE 侧更强的是 `CODEBUDDY.md`、rules、skills 与任务/workspace 连续性；commands/agents 保留为当前实现增强面。",
            "比赛模式下优先固定一个 Agent Chat，使用 `/super-dev-seeai` 或 `super-dev-seeai:`，减少切换子会话带来的上下文损耗。",
        ],
        "codebuddy-cn": [
            "CodeBuddyCN 当前按 `CODEBUDDY.md + rules + skills + 中文任务/workspace continuity` 建模，commands/agents 仅保留为当前实现增强面。",
            "建议固定同一个 Agent Chat 完成 research、三文档、确认门与实现，减少跨线程导致的上下文丢失。",
        ],
        "droid-cli": [
            "Droid CLI 官方核心面是 `AGENTS.md + .factory/rules + .factory/skills`；`.factory/commands/` 继续保留为 legacy slash compatibility。",
            "Factory 官方文档已经明确 skills 可以直接暴露 `/command`，新的工作流优先写进 `.factory/skills/`，而不是只依赖 `.factory/commands/`。",
            "项目级 `.factory/skills/` 会作为优先 slash/skill 面；`.factory/commands/` 仅作为兼容补强一起保留。",
            "需要跨项目保持同一宿主习惯时，再显式启用 `--with-user-surfaces`，补齐 `~/.factory/AGENTS.md`、`~/.factory/commands/` 与 `~/.factory/skills/`。",
            "恢复已有 session 时，优先沿用当前 Droid session；需要 headless 继续时再使用 `droid exec --session-id <id>`。",
        ],
        "codex": [
            "Codex Desktop/App 当前官方优先面是仓库 AGENTS.md、仓库/用户级 Skills 与 App 内 `/` 列表的已启用 Skill 入口。",
            "默认先在 App/Desktop 的 `/` 列表里选择 `super-dev`；需要显式终端治理时再切回 Codex CLI 的 `$super-dev`。",
            "若想跨项目复用统一协作心智，再显式启用 `--with-user-surfaces` 写入 `~/.codex/AGENTS.md`。",
        ],
        "codex-cli": [
            "Codex CLI 官方不走自定义项目 slash；CLI 显式入口是 `$super-dev`。",
            "默认依赖项目根 AGENTS.md、项目级 .agents/skills/super-dev/SKILL.md 与官方用户级技能目录 ~/.agents/skills/super-dev/SKILL.md；全局 CODEX_HOME/AGENTS.md（默认 ~/.codex/AGENTS.md）只在显式 `--with-user-surfaces` 时写入。",
            "仓库内还会额外生成 `.agents/plugins/marketplace.json` 与 `plugins/super-dev-codex/`，作为可选 repo plugin 增强层。",
            "所有宿主统一使用 super-dev 技能名称，onboard / migrate 会自动清理旧版 Super Dev 遗留别名残留。",
            "如果旧会话没加载新 Skill，重启 codex 再试。",
        ],
        "copilot-cli": [
            "Copilot CLI 官方优先面是 `AGENTS.md`、`.github/copilot-instructions.md`、`.github/skills/` 与 custom agents 目录 `.github/agents/` / `~/.copilot/agents/`。",
            "如需跨项目沿用同一套上下文，再显式启用 `--with-user-surfaces` 写入 `~/.copilot/copilot-instructions.md`。",
            "如果团队把额外 instructions 放进其他目录，可通过 `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` 继续纳入加载面。",
            "当前按文本触发 `super-dev: <需求描述>` 适配，不走自定义 slash。",
            "如果宿主未加载项目规则，重启 copilot 会话再试。",
        ],
        "cursor-cli": [
            "适合终端内连续执行研究、文档和编码。",
            "若命令列表未刷新，可重开一次 Cursor CLI 会话。",
            "官方文档确认 Cursor CLI 会读取项目根 `AGENTS.md` 与 `.cursor/rules/` 作为规则上下文；根 `CLAUDE.md` 只保留为兼容说明。",
        ],
        "cursor": [
            "建议固定在同一个 Agent Chat 会话里完成整条流水线。",
            "如果项目规则没加载，先重新打开工作区或重新发起聊天。",
            "Cursor 官方项目上下文面是项目根 `AGENTS.md` 与 `.cursor/rules/`；根 `CLAUDE.md` 只保留为兼容说明，`.cursor/commands/` 作为 beta 增强面使用。",
        ],
        "windsurf": [
            "当前按 IDE slash/workflow 模式适配。",
            "更适合在同一个 Workflow 里连续完成研究、三文档、确认门、Spec 与编码。",
            "官方文档公开 `AGENTS.md`、`.windsurf/workflows/` 与 `.windsurf/skills/`，仓库同时把 `.windsurf/rules/` 保留为当前项目约束面。",
            "当前项目侧以 `AGENTS.md` + `.windsurf/rules/` + `.windsurf/workflows/` + `.windsurf/skills/` 为主接入面。",
        ],
        "gemini-cli": [
            "优先在同一会话中完成 research -> 三文档 -> 用户确认 -> Spec -> 前端运行验证 -> 后端/交付。",
            "若宿主支持联网，先让它完成同类产品研究。",
            "Gemini CLI 官方文档明确 `GEMINI.md`、`.gemini/settings.json` 与 `.gemini/commands/*.toml` 的项目级上下文与命令目录；`/super-dev` 应理解为注入出来的 custom command，而不是宿主原生命令。",
            "用户级 `~/.gemini/GEMINI.md`、`~/.gemini/settings.json` 与 `~/.gemini/commands/` 仅在显式 `--with-user-surfaces` 时补齐，`~/.gemini/skills/` 继续只保留为兼容增强面。",
        ],
        "kimi-code": [
            "Kimi Code 官方主链按项目根 `AGENTS.md` + `/skill:` / `/flow:` + native session resume 建模。",
            "`.kimi/skills/` 与 `~/.kimi/skills/` 继续保留为当前增强面，`.kimi/AGENTS.md` 保留为兼容增强面，不再把这些路径对外宣称为唯一官方硬合同。",
            "显式官方入口优先使用 `/skill:super-dev <需求描述>`；需要结构化流程时再考虑 `/flow:super-dev <需求描述>`，自然语言 `super-dev:` 保留为统一宿主回退入口。",
            "Kimi Code 恢复时优先沿用 `kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume`，而不是重新开题。",
        ],
        "kiro-cli": [
            "Kiro CLI 当前优先按 `AGENTS.md + .kiro/steering/super-dev.md + .kiro/skills/` 适配，steering 负责长期上下文与行为约束。",
            "如果 steering 或 skills 未刷新，重新进入项目目录后重开 Kiro CLI 会话。",
            "官方文档已公开工作区 `AGENTS.md`、`.kiro/steering/`、`.kiro/skills/`，以及全局 `~/.kiro/steering/`、`~/.kiro/skills/`。",
        ],
        "opencode": [
            "按 CLI slash 模式使用。",
            "即使你也使用全局命令目录，仍建议保留项目级接入文件。",
            "官方文档已公开项目根 `AGENTS.md`、`.opencode/commands/`、`.opencode/skills/` 与对应用户级目录；`.opencode/agents/` 继续作为当前增强层管理。",
        ],
        "qoder-cli": [
            "适合命令行流水线开发。",
            "若 slash 未生效，先确认 `AGENTS.md`、`.qoder/commands/super-dev.md` 已生成，并检查 `.qoder/rules/` 与 `.qoder/skills/` 是否存在；`.qoder/agents/` 继续作为增强层核对。",
            "官方文档核心接入面是 `AGENTS.md`、`.qoder/rules/`、`.qoder/commands/` 与 `.qoder/skills/`，`.qoder/agents/` 继续作为当前增强层。",
            "Qoder 官方规则目录是 `.qoder/rules/`，不要再依赖单文件 `.qoder/rules.md`。",
        ],
        "qwen-code": [
            "Qwen Code 官方文档已公开 `QWEN.md`、`.qwen/settings.json`、`.qwen/commands/`、`.qwen/skills/` 与 `.qwen/agents/`。",
            "Qwen Code 的会话续跑主入口是 `/resume`；`/restore` 只负责 checkpoint 回滚，不应被当成继续当前流程的主入口。",
            "当前最佳接入面是 `QWEN.md + settings + commands + skills + agents`，优先在同一个 session 内完成 research、三文档、Spec 与实现。",
        ],
        "roo-code": [
            "Roo Code 支持项目级 `.roo/rules/` 与 `.roo/commands/`，建议与 `/super-dev` 命令一起使用。",
            "在同一会话连续完成 research、三文档确认、Spec 与开发实现。",
        ],
        "vscode-copilot": [
            "VS Code Copilot 建议使用 `.github/copilot-instructions.md` 固化流水线约束。",
            "当前按文本触发 `super-dev: <需求描述>` 适配，确保与 Copilot Chat 一致。",
        ],
        "kilo-code": [
            "Kilo Code 优先使用 `.kilocode/rules/` 规则目录，确保项目约束在每次任务开始时自动注入。",
            "当前按文本触发 `super-dev: <需求描述>` 适配，减少与内建 slash 的语义冲突。",
        ],
        "kiro": [
            "Kiro IDE 当前优先按 `AGENTS.md + steering + skills` 模式触发，steering 负责长期上下文与行为约束。",
            "如果 steering 或 Skill 未加载，先重开项目窗口或新开一个 Agent Chat。",
            "Kiro 官方已公开工作区 `AGENTS.md`、`.kiro/steering/`、`.kiro/skills/` 与全局 `~/.kiro/steering/`、`~/.kiro/skills/`。",
        ],
        "qoder": [
            "Qoder IDE 当前优先按项目级 `AGENTS.md + commands + rules + skills` 模式触发，可直接使用 /super-dev；`.qoder/agents/` 继续作为增强层。",
            "若新增命令未出现，重新打开项目或新开一个 Agent Chat。",
            "官方文档核心接入面是 `AGENTS.md`、`.qoder/rules/`、`.qoder/commands/` 与 `.qoder/skills/`。",
        ],
        "trae": [
            "不要输入 /super-dev。",
            "Trae 默认优先依赖项目级 `.trae/project_rules.md` 与 `.trae/rules.md`；用户级 `~/.trae/user_rules.md` / `~/.trae/rules.md` 仅在显式 `--with-user-surfaces` 时写入，用于跨项目复用当前已观测到的规则加载面。",
            "若检测到宿主级 ~/.trae/skills/super-dev/SKILL.md，则会额外增强。",
            "安装后建议新开一个 Trae Agent Chat，让新的规则与 Skill 一起生效。",
            "随后按 output/* 与 .super-dev/changes/*/tasks.md 推进开发。",
        ],
        "trae-cn": [
            "TraeCN 当前按中文工作区流建模，优先保持在同一个工作区/线程里完成 baseline、文档确认与实现。",
            "如果当前工作区已经进入 MTC / Code 某一侧，恢复时优先续跑当前任务，不要重新开题。",
        ],
        "trae-solo": [
            "Trae SOLO 当前优先按 `AGENTS.md + .trae/rules + .trae/commands + .trae/skills` 这套工作区接入模型来承接 Super Dev，并直接在工作区里使用 `/super-dev`。",
            "这套 `.trae/*` 文件面应视为当前最稳的集成模型，而不是对外宣称为宿主唯一官方文件合同。",
            "如果桌面端 slash 刷新慢，可以先回退到 `super-dev: <需求描述>`；恢复时优先沿用当前 workspace continuity，不要重新开题。",
        ],
        "trae-solocn": [
            "Trae SOLOCN 当前优先按 `.trae/rules + .trae/skills + ~/.trae-cn/skills` 这套中文工作区接入模型承接 Super Dev，主入口仍用 `super-dev: <需求描述>`。",
            "中国区公开面更明确的是 `MTC / Code` 双模式、Skills 以及内建 `/plan` `/spec`；`.trae/*` 文件面在仓库里属于当前推荐集成模型，而不是硬编码成唯一官方合同。",
            "如果需要继续当前流程，优先在同一工作区直接说“继续当前流程”；只有在维护场景里才显式回到内部命令面。",
        ],
        "workbuddy": [
            "WorkBuddy 当前推荐通过任务工作台 + Skills + MCP 承接 Super Dev；若启用文件导入型 Skill，仓库会把它视为当前接入模型的补充面，而不是官方主合同。",
            "主入口是 `super-dev: <需求描述>`；赛事模式使用 `super-dev-seeai: <需求描述>`。",
            "也可在 WorkBuddy 技能市场搜索 Super Dev 手动启用，并确认 MCP 与项目目录授权已经就绪。",
        ],
    }

    HOST_PRECONDITION_GUIDANCE: dict[str, list[str]] = {
        "claude": [
            "Claude Desktop 触发前先确认当前 Project 已挂上 Project Instructions、Project Knowledge 与需要的 extensions / MCP。",
            "如果当前会话还没切到目标项目的 Project，不要直接继续流程。",
        ],
        "codex-cli": [
            "Codex 接入后必须重启 `codex`，旧会话不会自动重新加载 AGENTS.md 与宿主级 Skill。",
            "触发前确认当前终端已经进入目标项目目录，并重新打开新的 Codex 会话。",
        ],
        "codex": [
            "Codex Desktop 触发前确认当前会话就是目标项目，并且 `/` 列表里的 super-dev Skill 已启用。",
            "若刚完成接入，优先完全关闭旧会话并重开 App/Desktop 会话。",
        ],
        "antigravity": [
            "Antigravity 接入后建议重新打开 Prompt / Agent Chat，让 GEMINI.md、custom commands 与当前推荐 workflow 一起加载。",
            "触发前确认当前工作区就是目标项目。",
        ],
        "trae": [
            "Trae 接入后建议完全关闭旧 Agent Chat，重新打开项目后再发起新会话。",
            "触发前确认当前 Agent Chat 绑定的是目标项目工作区。",
        ],
        "cursor": [
            "Cursor 需要在目标项目工作区的 Agent Chat 中触发，避免把 `AGENTS.md`、`.cursor/rules/` 与 beta `.cursor/commands/` 加载到错误工作区。",
        ],
        "cursor-cli": [
            "Cursor CLI 触发前确认当前终端已进入目标项目目录，并让会话读取项目根 `AGENTS.md` 与 `.cursor/rules/`；根 `CLAUDE.md` 只保留为兼容说明。",
        ],
        "gemini-cli": [
            "Gemini CLI 触发前确认当前终端已进入目标项目目录，并让新的会话读取 `GEMINI.md`、可选 `.gemini/settings.json` 与 `.gemini/commands/`。",
        ],
        "kimi-code": [
            "Kimi Code 触发前确认当前终端已进入目标项目目录，并让当前会话读取项目根 `AGENTS.md`。",
            "如果项目或用户级 `.kimi/skills/` 已启用，再确认这些增强面也已被当前会话读取。",
            "如果刚完成接入，优先新开一个 Kimi Code session；显式入口优先 `/skill:super-dev`，恢复时优先使用 `kimi --continue`、`kimi --session <id>` 或运行中的 `/sessions` / `/resume`。",
        ],
        "kiro": [
            "Kiro IDE 接入后建议重新打开 Agent Chat，让 `AGENTS.md`、steering / skills 在新会话里生效。",
            "触发前确认当前工作区就是目标项目。",
        ],
        "kiro-cli": [
            "Kiro CLI 触发前确认当前终端已进入目标项目目录，并让新会话读取 `AGENTS.md`、`.kiro/steering/` 与 skills。",
        ],
        "qoder": [
            "Qoder IDE 触发前确认当前 Agent Chat 绑定的是目标项目；若新命令未出现，重新打开项目或新建会话。",
            "若项目里额外启用了 `.qoder/agents/`，把它视为增强层，而不是当前最小官方必需面。",
        ],
        "qoder-cli": [
            "Qoder CLI 触发前确认当前终端已进入目标项目目录。",
            "若项目里额外启用了 `.qoder/agents/`，把它视为增强层，而不是当前最小官方必需面。",
        ],
        "qwen-code": [
            "Qwen Code 触发前确认当前终端已进入目标项目目录，并让当前会话读取 `QWEN.md`、`.qwen/commands/`、`.qwen/skills/` 与 `.qwen/agents/`。",
            "如果显式启用了用户级 surface，再确认 `~/.qwen/QWEN.md` 已被当前会话读取。",
            "如果刚完成接入，优先新开一个 Qwen Code session；恢复时优先使用 `/resume`，只有需要回滚工具修改时才使用 `/restore`。",
        ],
        "trae-solo": [
            "Trae SOLO 接入后建议重新打开当前 workspace，让 Rules / Commands / Skills 一起在新会话里生效。",
            "触发前确认当前 workspace 就是目标项目，并优先沿用当前 workspace 的连续恢复能力。",
        ],
        "trae-solocn": [
            "Trae SOLOCN 触发前确认当前工作区就是目标项目，并且 `.trae/skills/` 与 `~/.trae-cn/skills/` 已同步。",
            "如果当前会话已在 MTC / Code 双模式中的某一侧工作，恢复时优先续跑当前任务，而不是重新开题。",
        ],
        "trae-cn": [
            "TraeCN 触发前确认当前工作区就是目标项目，并优先在同一工作区/线程内继续当前流程。",
            "若当前工作区已进入 MTC / Code 某一侧，恢复时优先续跑当前任务。",
        ],
        "codebuddy": [
            "CodeBuddy 触发前确认当前 Agent Chat 位于目标项目上下文。",
            "比赛模式建议固定同一个 Agent Chat，并优先准备主展示路径需要的素材和上下文。",
        ],
        "codebuddy-cn": [
            "CodeBuddyCN 触发前确认当前 Agent Chat 位于目标项目上下文。",
            "优先固定同一个 Agent Chat 完成 research、三文档、Spec 与实现。",
        ],
        "codebuddy-cli": [
            "CodeBuddy CLI 触发前确认当前终端已进入目标项目目录。",
            "确认项目级 `.codebuddy/rules/`、`.codebuddy/commands/`、`.codebuddy/skills/` 与 `.codebuddy/agents/` 都已被当前会话加载。",
            "比赛模式优先使用当前已加载规则的会话，避免重新开多个 CLI 会话打散时间盒。",
        ],
        "droid-cli": [
            "Droid CLI 触发前确认当前终端已进入目标项目目录，并让当前会话读取项目根 `AGENTS.md`。",
            "若 slash 或技能目录刚更新，优先在同一项目目录重开一个 Droid 会话后再触发。",
        ],
        "copilot-cli": [
            "Copilot CLI 触发前确认当前终端已进入目标项目目录，并让新的会话读取 `AGENTS.md`、`.github/copilot-instructions.md` 与 `.github/skills/`。",
            "如果显式启用了用户级 surface，再确认 `~/.copilot/copilot-instructions.md` 也已被新会话加载。",
        ],
        "windsurf": [
            "Windsurf 触发前确认当前 Agent Chat / Workflow 绑定的是目标项目工作区，并已读取项目根 `AGENTS.md`。",
        ],
        "opencode": [
            "OpenCode 触发前确认当前终端已进入目标项目目录。",
            "若项目里额外启用了 `.opencode/agents/`，把它视为增强层，而不是当前最小官方必需面。",
        ],
        "claude-code": [
            "Claude Code 触发前确认当前会话就是目标项目目录下的当前会话。",
        ],
        "cline": [
            "Cline 触发前确认当前聊天绑定的是目标工作区，并让 `.clinerules/` 已被重新加载。",
        ],
        "kilo-code": [
            "Kilo Code 触发前确认当前聊天绑定的是目标工作区，并让 `.kilocode/rules/` 已被重新加载。",
        ],
        "roo-code": [
            "Roo Code 触发前确认当前聊天位于目标项目工作区，并重新加载 `.roo/` 规则与命令。",
        ],
        "vscode-copilot": [
            "VS Code Copilot 触发前确认当前工作区就是目标项目，并让新的 Chat 会话读取项目级说明文件。",
        ],
        "workbuddy": [
            "WorkBuddy 触发前确认当前授权目录或工作目录已经指向目标项目。",
            "确认当前任务会话已启用 Super Dev 相关 Skills；比赛模式优先启用 SEEAI 版本。",
        ],
    }

    HOST_FAMILY_MAP: dict[str, str] = {
        "antigravity": "antigravity",
        "claude": "claude",
        "claude-code": "claude",
        "cline": "cline",
        "codebuddy-cli": "codebuddy",
        "codebuddy": "codebuddy",
        "codebuddy-cn": "codebuddy",
        "droid-cli": "droid-cli",
        "codex": "codex",
        "codex-cli": "codex",
        "copilot-cli": "copilot-cli",
        "cursor-cli": "cursor",
        "cursor": "cursor",
        "windsurf": "windsurf",
        "gemini-cli": "gemini",
        "kimi-code": "kimi-code",
        "kilo-code": "kilo-code",
        "kiro-cli": "kiro",
        "kiro": "kiro",
        "qoder-cli": "qoder",
        "qoder": "qoder",
        "qwen-code": "qwen",
        "roo-code": "roo-code",
        "vscode-copilot": "vscode-copilot",
        "opencode": "opencode",
        "trae": "trae",
        "trae-cn": "trae",
        "trae-solo": "trae",
        "trae-solocn": "trae",
        "workbuddy": "workbuddy",
    }

    PREFERRED_FAMILY_TARGETS: dict[str, str] = {
        "codebuddy": "codebuddy-cli",
        "cursor": "cursor-cli",
        "kiro": "kiro-cli",
        "qoder": "qoder-cli",
        "trae": "trae-solo",
    }

    SHARED_DETECTION_FILES: set[str] = {
        "AGENTS.md",
        "CODEBUDDY.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".cursor/rules/super-dev.mdc",
        ".kiro/steering/super-dev.md",
    }

    TARGETS: dict[str, IntegrationTarget] = {
        "antigravity": IntegrationTarget(
            name="antigravity",
            description="Antigravity IDE 工作流 + Gemini 上下文注入",
            files=["GEMINI.md", ".gemini/commands/super-dev.toml", ".agent/workflows/super-dev.md"],
        ),
        "claude": IntegrationTarget(
            name="claude",
            description="Claude Desktop Project / Instructions / Knowledge 手动接入",
            files=[],
        ),
        "claude-code": IntegrationTarget(
            name="claude-code",
            description="Claude Code CLI 深度集成",
            files=[
                "CLAUDE.md",
                ".claude/CLAUDE.md",
                ".claude/skills/super-dev/SKILL.md",
                ".claude/agents/super-dev.md",
                ".claude/commands/super-dev.md",
                ".claude-plugin/marketplace.json",
                "plugins/super-dev-claude/.claude-plugin/plugin.json",
                "plugins/super-dev-claude/README.md",
                "plugins/super-dev-claude/skills/super-dev/SKILL.md",
            ],
            optional_files=[
                ".claude/CLAUDE.md",
                ".claude/commands/super-dev.md",
                ".claude-plugin/marketplace.json",
                "plugins/super-dev-claude/.claude-plugin/plugin.json",
                "plugins/super-dev-claude/README.md",
                "plugins/super-dev-claude/skills/super-dev/SKILL.md",
            ],
        ),
        "cline": IntegrationTarget(
            name="cline",
            description="Cline IDE 规则注入",
            files=[".clinerules/super-dev.md", ".cline/skills/super-dev/SKILL.md"],
        ),
        "codebuddy-cli": IntegrationTarget(
            name="codebuddy-cli",
            description="CodeBuddy CLI 项目规则注入",
            files=[
                "CODEBUDDY.md",
                ".codebuddy/rules/super-dev.md",
                ".codebuddy/commands/super-dev.md",
                ".codebuddy/skills/super-dev/SKILL.md",
                ".codebuddy/agents/super-dev.md",
            ],
        ),
        "codebuddy": IntegrationTarget(
            name="codebuddy",
            description="CodeBuddy rules + agent protocol 注入",
            files=[
                "CODEBUDDY.md",
                ".codebuddy/rules/super-dev/RULE.mdc",
                ".codebuddy/commands/super-dev.md",
                ".codebuddy/agents/super-dev.md",
                ".codebuddy/skills/super-dev/SKILL.md",
            ],
        ),
        "codebuddy-cn": IntegrationTarget(
            name="codebuddy-cn",
            description="CodeBuddyCN IDE rules + agent protocol 注入",
            files=[
                "CODEBUDDY.md",
                ".codebuddy/rules/super-dev/RULE.mdc",
                ".codebuddy/commands/super-dev.md",
                ".codebuddy/agents/super-dev.md",
                ".codebuddy/skills/super-dev/SKILL.md",
            ],
        ),
        "droid-cli": IntegrationTarget(
            name="droid-cli",
            description="Droid CLI 官方 AGENTS + .factory rules/commands/skills 接入",
            files=[
                "AGENTS.md",
                ".factory/rules/super-dev.md",
                ".factory/commands/super-dev.md",
                ".factory/commands/super-dev-seeai.md",
                ".factory/skills/super-dev/SKILL.md",
                ".factory/skills/super-dev-seeai/SKILL.md",
            ],
        ),
        "codex": IntegrationTarget(
            name="codex",
            description="Codex App/Desktop 项目上下文注入",
            files=[
                "AGENTS.md",
                ".agents/skills/super-dev/SKILL.md",
                ".agents/plugins/marketplace.json",
                "plugins/super-dev-codex/.codex-plugin/plugin.json",
                "plugins/super-dev-codex/README.md",
                "plugins/super-dev-codex/skills/super-dev/SKILL.md",
            ],
            optional_files=[
                ".agents/plugins/marketplace.json",
                "plugins/super-dev-codex/.codex-plugin/plugin.json",
                "plugins/super-dev-codex/README.md",
                "plugins/super-dev-codex/skills/super-dev/SKILL.md",
            ],
        ),
        "codex-cli": IntegrationTarget(
            name="codex-cli",
            description="Codex 项目上下文注入",
            files=[
                "AGENTS.md",
                ".agents/skills/super-dev/SKILL.md",
                ".agents/plugins/marketplace.json",
                "plugins/super-dev-codex/.codex-plugin/plugin.json",
                "plugins/super-dev-codex/README.md",
                "plugins/super-dev-codex/skills/super-dev/SKILL.md",
            ],
            optional_files=[
                ".agents/plugins/marketplace.json",
                "plugins/super-dev-codex/.codex-plugin/plugin.json",
                "plugins/super-dev-codex/README.md",
                "plugins/super-dev-codex/skills/super-dev/SKILL.md",
            ],
        ),
        "copilot-cli": IntegrationTarget(
            name="copilot-cli",
            description="Copilot CLI 指令注入",
            files=[
                "AGENTS.md",
                ".github/copilot-instructions.md",
                ".github/skills/super-dev/SKILL.md",
                ".github/agents/super-dev.md",
            ],
        ),
        "cursor-cli": IntegrationTarget(
            name="cursor-cli",
            description="Cursor CLI 项目规则注入",
            files=["AGENTS.md", ".cursor/rules/super-dev.mdc"],
        ),
        "windsurf": IntegrationTarget(
            name="windsurf",
            description="Windsurf IDE AGENTS + 规则 + Workflow 注入",
            files=[
                "AGENTS.md",
                ".windsurf/rules/super-dev.md",
                ".windsurf/workflows/super-dev.md",
                ".windsurf/skills/super-dev/SKILL.md",
            ],
        ),
        "gemini-cli": IntegrationTarget(
            name="gemini-cli",
            description="Gemini CLI 项目规则注入",
            files=["GEMINI.md", ".gemini/commands/super-dev.toml"],
        ),
        "kimi-code": IntegrationTarget(
            name="kimi-code",
            description="Kimi Code AGENTS + Skill 增强接入",
            files=[
                "AGENTS.md",
                ".kimi/AGENTS.md",
                ".kimi/skills/super-dev/SKILL.md",
            ],
        ),
        "kilo-code": IntegrationTarget(
            name="kilo-code",
            description="Kilo Code 规则 + Skill 注入",
            files=[".kilocode/rules/super-dev.md", ".kilocode/skills/super-dev/SKILL.md"],
        ),
        "kiro-cli": IntegrationTarget(
            name="kiro-cli",
            description="Kiro CLI 项目规则注入",
            files=["AGENTS.md", ".kiro/steering/super-dev.md", ".kiro/skills/super-dev/SKILL.md"],
        ),
        "qoder-cli": IntegrationTarget(
            name="qoder-cli",
            description="Qoder CLI 项目规则 + 命令 + Skill 注入（agents 增强）",
            files=[
                "AGENTS.md",
                ".qoder/rules/super-dev.md",
                ".qoder/commands/super-dev.md",
                ".qoder/skills/super-dev/SKILL.md",
                ".qoder/agents/super-dev.md",
            ],
        ),
        "qwen-code": IntegrationTarget(
            name="qwen-code",
            description="Qwen Code 项目规则 + 命令 + Skill + Agent 注入",
            files=[
                "QWEN.md",
                ".qwen/commands/super-dev.md",
                ".qwen/skills/super-dev/SKILL.md",
                ".qwen/agents/super-dev.md",
            ],
        ),
        "roo-code": IntegrationTarget(
            name="roo-code",
            description="Roo Code 规则 + 命令注入",
            files=[".roo/rules/super-dev.md", ".roo/commands/super-dev.md"],
        ),
        "vscode-copilot": IntegrationTarget(
            name="vscode-copilot",
            description="Copilot 仓库级指令注入",
            files=[".github/copilot-instructions.md"],
        ),
        "opencode": IntegrationTarget(
            name="opencode",
            description="OpenCode 项目规则 + 命令 + Skill 注入（agents 增强）",
            files=[
                "AGENTS.md",
                ".opencode/commands/super-dev.md",
                ".opencode/skills/super-dev/SKILL.md",
                ".opencode/agents/super-dev.md",
            ],
        ),
        "cursor": IntegrationTarget(
            name="cursor",
            description="Cursor IDE 规则注入",
            files=["AGENTS.md", ".cursor/rules/super-dev.mdc"],
        ),
        "kiro": IntegrationTarget(
            name="kiro",
            description="Kiro IDE 项目规则注入",
            files=["AGENTS.md", ".kiro/steering/super-dev.md", ".kiro/skills/super-dev/SKILL.md"],
        ),
        "qoder": IntegrationTarget(
            name="qoder",
            description="Qoder IDE 规则 + 命令 + Skill 注入（agents 增强）",
            files=[
                "AGENTS.md",
                ".qoder/rules/super-dev.md",
                ".qoder/commands/super-dev.md",
                ".qoder/skills/super-dev/SKILL.md",
                ".qoder/agents/super-dev.md",
            ],
        ),
        "trae": IntegrationTarget(
            name="trae",
            description="Trae IDE 项目规则 + 宿主 Skill 注入",
            files=[".trae/project_rules.md", ".trae/rules.md"],
        ),
        "trae-cn": IntegrationTarget(
            name="trae-cn",
            description="TraeCN IDE 中文工作区规则 + Skills 接入",
            files=[".trae/project_rules.md", ".trae/rules.md", ".trae/skills/super-dev/SKILL.md"],
        ),
        "trae-solo": IntegrationTarget(
            name="trae-solo",
            description="Trae SOLO Rules + Commands + Skills 接入",
            files=[
                "AGENTS.md",
                ".trae/rules/super-dev.md",
                ".trae/commands/super-dev.md",
                ".trae/skills/super-dev/SKILL.md",
            ],
        ),
        "trae-solocn": IntegrationTarget(
            name="trae-solocn",
            description="Trae SOLOCN Rules + Skills 接入",
            files=[
                ".trae/rules/super-dev.md",
                ".trae/skills/super-dev/SKILL.md",
            ],
        ),
        "workbuddy": IntegrationTarget(
            name="workbuddy",
            description="WorkBuddy 桌面工作台 Skill 接入",
            files=[],
        ),
    }

    SLASH_COMMAND_FILES: dict[str, str] = {
        "antigravity": ".gemini/commands/super-dev.toml",
        "claude-code": ".claude/commands/super-dev.md",
        "codebuddy-cli": ".codebuddy/commands/super-dev.md",
        "codebuddy": ".codebuddy/commands/super-dev.md",
        "codebuddy-cn": ".codebuddy/commands/super-dev.md",
        "droid-cli": ".factory/commands/super-dev.md",
        "cursor-cli": ".cursor/commands/super-dev.md",
        "windsurf": ".windsurf/workflows/super-dev.md",
        "gemini-cli": ".gemini/commands/super-dev.toml",
        "kiro-cli": ".kiro/steering/super-dev.md",
        "kiro": ".kiro/steering/super-dev.md",
        "opencode": ".opencode/commands/super-dev.md",
        "qoder-cli": ".qoder/commands/super-dev.md",
        "qwen-code": ".qwen/commands/super-dev.md",
        "qoder": ".qoder/commands/super-dev.md",
        "roo-code": ".roo/commands/super-dev.md",
        "cursor": ".cursor/commands/super-dev.md",
        "trae-solo": ".trae/commands/super-dev.md",
    }

    GLOBAL_SLASH_COMMAND_FILES: dict[str, str] = {
        "antigravity": ".gemini/commands/super-dev.toml",
        "claude-code": ".claude/commands/super-dev.md",
        "codebuddy-cli": ".codebuddy/commands/super-dev.md",
        "codebuddy": ".codebuddy/commands/super-dev.md",
        "codebuddy-cn": ".codebuddy/commands/super-dev.md",
        "droid-cli": ".factory/commands/super-dev.md",
        "opencode": ".config/opencode/commands/super-dev.md",
        "qoder-cli": ".qoder/commands/super-dev.md",
        "qoder": ".qoder/commands/super-dev.md",
        "qwen-code": ".qwen/commands/super-dev.md",
    }

    NO_SLASH_TARGETS: set[str] = {
        "claude",
        "cline",
        "codex",
        "codex-cli",
        "copilot-cli",
        "kimi-code",
        "kilo-code",
        "trae",
        "trae-cn",
        "trae-solocn",
        "vscode-copilot",
        "workbuddy",
    }

    OFFICIAL_DOCS_INDEX: dict[str, tuple[str, ...]] = {
        "antigravity": ("https://antigravity.im/documentation",),
        "claude": (
            "https://support.anthropic.com/en/articles/9487310-what-are-projects",
            "https://support.anthropic.com/en/articles/10185728-understanding-and-managing-project-knowledge",
            "https://support.anthropic.com/en/articles/11433263-using-styles-in-claude",
        ),
        "claude-code": (
            "https://docs.anthropic.com/en/docs/claude-code/slash-commands",
            "https://docs.anthropic.com/en/docs/claude-code/hooks",
            "https://docs.anthropic.com/en/docs/claude-code/sdk",
            "https://docs.anthropic.com/en/docs/claude-code/settings#claude-md-memory",
            "https://docs.anthropic.com/en/docs/claude-code/sub-agents",
        ),
        "cline": ("https://docs.cline.bot/customization/cline-rules",),
        "codebuddy-cli": (
            "https://www.codebuddy.ai/docs/cli/slash-commands",
            "https://www.codebuddy.ai/docs/cli/skills",
            "https://www.codebuddy.ai/docs/cli/plugins",
        ),
        "codebuddy": (
            "https://www.codebuddy.ai/docs/cli/ide-integrations",
            "https://www.codebuddy.ai/docs/zh/ide/User-guide/Rules",
            "https://www.codebuddy.ai/docs/ide/Features/Subagents",
            "https://www.codebuddy.ai/docs/zh/ide/Features/Skills",
        ),
        "codebuddy-cn": (
            "https://www.codebuddy.ai/docs/zh/ide/User-guide/Rules",
            "https://www.codebuddy.ai/docs/zh/ide/Features/Commands",
            "https://www.codebuddy.ai/docs/zh/ide/Features/Skills",
        ),
        "droid-cli": (
            "https://docs.factory.ai/factory-cli/configuration/agents-md",
            "https://docs.factory.ai/factory-cli/configuration/skills",
            "https://docs.factory.ai/factory-cli/configuration/custom-slash-commands",
            "https://docs.factory.ai/cli/configuration/custom-droids",
            "https://docs.factory.ai/reference/cli-reference",
        ),
        "codex-cli": (
            "https://developers.openai.com/codex/cli",
            "https://developers.openai.com/codex/guides/agents-md",
            "https://developers.openai.com/codex/skills",
            "https://developers.openai.com/codex/app/commands",
        ),
        "codex": (
            "https://developers.openai.com/codex/cli",
            "https://developers.openai.com/codex/guides/agents-md",
            "https://developers.openai.com/codex/skills",
            "https://developers.openai.com/codex/app/commands",
        ),
        "copilot-cli": (
            "https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli",
            "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions",
            "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills",
            "https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-agents/invoke-custom-agents",
        ),
        "cursor-cli": (
            "https://docs.cursor.com/en/cli/overview",
            "https://docs.cursor.com/en/cli/using",
            "https://docs.cursor.com/en/context/rules",
        ),
        "windsurf": (
            "https://docs.windsurf.com/plugins/cascade/workflows",
            "https://docs.windsurf.com/windsurf/cascade/memories#custom-skills",
            "https://docs.windsurf.com/windsurf/cascade/memories",
        ),
        "gemini-cli": (
            "https://google-gemini.github.io/gemini-cli/docs/",
            "https://google-gemini.github.io/gemini-cli/docs/cli/gemini-md.html",
            "https://google-gemini.github.io/gemini-cli/docs/get-started/configuration.html",
            "https://google-gemini.github.io/gemini-cli/docs/cli/custom-commands.html",
            "https://google-gemini.github.io/gemini-cli/docs/cli/commands.html",
        ),
        "kimi-code": (
            "https://www.kimi.com/code/docs/en/kimi-cli/guides/getting-started.html",
            "https://www.kimi.com/code/docs/en/kimi-cli/guides/interaction.html",
            "https://www.kimi.com/code/docs/en/kimi-cli/guides/sessions.html",
            "https://www.kimi.com/code/docs/en/kimi-cli.html",
        ),
        "kilo-code": ("https://kilocode.ai/docs/features/rules",),
        "kiro-cli": (
            "https://kiro.dev/docs/cli/",
            "https://kiro.dev/docs/steering/",
            "https://kiro.dev/docs/cli/skills/",
            "https://kiro.dev/docs/cli/reference/slash-commands/",
        ),
        "opencode": (
            "https://opencode.ai/docs/rules/",
            "https://opencode.ai/docs/commands/",
            "https://opencode.ai/docs/skills/",
            "https://opencode.ai/docs/agents/",
        ),
        "qoder-cli": (
            "https://docs.qoder.com/cli/using-cli",
            "https://docs.qoder.com/zh/user-guide/rules",
            "https://docs.qoder.com/user-guide/commands",
            "https://docs.qoder.com/cli/skills",
            "https://docs.qoder.com/en/cli/user-guide/subagent",
        ),
        "qwen-code": (
            "https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/",
            "https://qwenlm.github.io/qwen-code-docs/en/users/features/commands/",
            "https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/",
            "https://qwenlm.github.io/qwen-code-docs/en/subagents/",
            "https://qwenlm.github.io/qwen-code-docs/en/users/features/headless/",
        ),
        "roo-code": (
            "https://docs.roocode.com/features/slash-commands",
            "https://docs.roocode.com/features/custom-instructions",
            "https://docs.roocode.com/features/custom-modes",
        ),
        "vscode-copilot": (
            "https://docs.github.com/en/copilot/how-tos/copilot-chat/customize-copilot/add-repository-instructions",
            "https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot",
        ),
        "cursor": (
            "https://docs.cursor.com/en/agent/chat/commands",
            "https://docs.cursor.com/en/context/rules",
        ),
        "kiro": (
            "https://kiro.dev/docs/",
            "https://kiro.dev/docs/steering/",
            "https://kiro.dev/docs/cli/skills/",
        ),
        "qoder": (
            "https://docs.qoder.com/zh/user-guide/rules",
            "https://docs.qoder.com/user-guide/commands",
            "https://docs.qoder.com/user-guide/skills",
            "https://docs.qoder.com/en/cli/user-guide/subagent",
        ),
        "trae": ("https://docs.trae.ai/docs/what-is-trae-rules",),
        "trae-cn": (
            "https://www.trae.cn/",
            "https://www.trae.cn/changelog",
            "https://forum.trae.cn/t/topic/36",
        ),
        "trae-solo": (
            "https://docs.trae.ai/solo?_lang=en",
            "https://docs.trae.ai/solo/rules?_lang=en",
            "https://docs.trae.ai/solo/slash-commands?_lang=en",
            "https://docs.trae.ai/solo/skills?_lang=en",
        ),
        "trae-solocn": (
            "https://www.trae.cn/solo",
            "https://www.trae.cn/changelog",
            "https://forum.trae.cn/t/topic/36",
            "https://forum.trae.cn/t/topic/7556",
        ),
        "workbuddy": (
            "https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Product-Guide",
            "https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide",
            "https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Right-Sidebar",
        ),
    }

    OFFICIAL_DOCS: dict[str, str] = {
        key: (values[0] if values else "") for key, values in OFFICIAL_DOCS_INDEX.items()
    }

    DOCS_VERIFIED_TARGETS: set[str] = {
        key for key, values in OFFICIAL_DOCS_INDEX.items() if bool(values)
    }

    HOST_CERTIFICATIONS: dict[str, dict[str, object]] = {
        "antigravity": {
            "level": "experimental",
            "reason": "Antigravity 当前按公开可证实的 GEMINI 上下文 + custom commands 建模，并结合仓库推荐的 workflow 增强面接入；安装面可用，但官方本地注入文档证据仍偏弱。",
            "evidence": [
                "公开资料能确认 GEMINI 上下文、命令面与自然语言/Prompt 工作方式",
                "`.agent/workflows/` 与 `~/.gemini/skills/` 继续按当前推荐增强模型保留，不再对外宣称为严格官方硬合同",
                "Super Dev 已按项目 `GEMINI.md` + `.gemini/commands/` 主面接入，并把 workflow / skill 面降成推荐增强模型",
            ],
        },
        "claude": {
            "level": "compatible",
            "reason": "Claude Desktop 官方明确支持 Projects、Project Instructions、Project Knowledge 与 desktop extensions / MCP，当前接入按这些正式面而不是猜测 dotfile 路径建模。",
            "evidence": [
                "官方帮助中心公开 Projects、Project Knowledge 与 Styles/Instructions",
                "Super Dev 已把 Claude Desktop 建模成项目/知识/扩展驱动的桌面助手，而不是伪装成文件注入宿主",
            ],
        },
        "claude-code": {
            "level": "certified",
            "reason": "已收敛到 Claude Code 的官方主模型：项目根 CLAUDE.md + 可选 settings + 项目/用户 skills + 项目/用户 subagents，并仅把 commands/plugin 保留为增强层。",
            "evidence": [
                "Anthropic 官方文档公开项目/用户 settings、CLAUDE.md 与 `.claude/agents/`",
                "Anthropic 官方文档公开 project/user subagents 位于 `.claude/agents/` 与 `~/.claude/agents/`",
                "Super Dev 已补齐 `CLAUDE.md + .claude/CLAUDE.md + .claude/skills + .claude/agents`，并把 `.claude/commands` 留作兼容增强面",
            ],
        },
        "codebuddy-cn": {
            "level": "compatible",
            "reason": "CodeBuddyCN 当前按 `CODEBUDDY.md + rules + skills + 中文任务/workspace continuity` 建模，commands/agents 仅保留为当前实现增强面。",
            "evidence": [
                "官方中文 IDE 文档公开 Rules、Skills 与工作流能力",
                "Super Dev 已为 CodeBuddyCN 建模 CODEBUDDY.md + rules + skills 主面，并保留 commands/agents 增强层",
            ],
        },
        "codex-cli": {
            "level": "certified",
            "reason": "已按 Codex CLI 的真实能力改成 AGENTS.md + Skills 主面，CLI 官方显式入口是 `$super-dev`，不再把 `/super-dev` 误当成 CLI 原生入口。",
            "evidence": [
                "官方产品说明明确 Skills 是 Codex 的主扩展面",
                "Super Dev 已为 Codex CLI 修正成 AGENTS.md + `.agents/skills` + `~/.agents/skills`",
                "repo plugin enhancement 保留为可选高级增强，不再和 CLI 官方入口混写",
                "接入后需要重启的行为已被显式建模与测试覆盖",
            ],
        },
        "codex": {
            "level": "certified",
            "reason": "Codex App/Desktop 与 CLI 共用 AGENTS.md + Skills 主面，当前已单独建模桌面端 Skill 入口与项目级接入面。",
            "evidence": [
                "官方文档明确 AGENTS.md、Skills 与 Codex App/Desktop commands",
                "Super Dev 已把 Codex App/Desktop 从 Codex CLI 中拆出，形成独立桌面助手宿主模型",
            ],
        },
        "kimi-code": {
            "level": "compatible",
            "reason": "Kimi Code 官方文档已明确 AGENTS.md、/skill:/flow: 与 session continue / resume；仓库继续把 `.kimi/skills/` 保留为当前增强层而不是对外宣称的唯一官方文件合同。",
            "evidence": [
                "官方文档公开项目级 `AGENTS.md` 与官方 `/skill:`、`/flow:` 入口",
                "官方文档公开 `/skill:`、`/flow:`、`kimi --continue`、`kimi --session` 与运行中的 `/sessions` / `/resume`",
                "Super Dev 已改为 AGENTS + explicit entry + native resume 的 Kimi 宿主模型接入，并把 `.kimi/skills/` 收成增强层",
            ],
        },
        "trae": {
            "level": "compatible",
            "reason": "Trae 官方公开面当前可确认的是项目 rules；用户 rules 与兼容 rules 继续作为可选增强面建模，skills 仍按增强处理，因此当前保持稳定兼容而非认证级。",
            "evidence": [
                "公开文档确认 Trae project rules 机制，user rules 作为可选增强面保留",
                "本机已存在 ~/.trae/rules.md，可作为兼容规则面在显式启用用户级面时协同生效",
                "本机若存在 ~/.trae/skills，可作为兼容增强路径协同生效",
                "Super Dev 已同时建模项目 rules、用户 rules、兼容 rules 面与可选宿主级 Skill 增强",
            ],
        },
        "trae-solo": {
            "level": "compatible",
            "reason": "Trae SOLO 公开资料能确认 workspace continuity 与 rules/commands/skills 能力；仓库已把 `.trae/*` 收成当前推荐工作区接入模型，而不是过度宣称为唯一官方文件合同。",
            "evidence": [
                "公开 SOLO 文档可确认 workspace continuity 与 rules / commands / skills 能力",
                "仓库把 `.trae/rules/` + `.trae/commands/` + `.trae/skills/` 作为当前推荐接入模型",
                "Super Dev 保留 `super-dev:` 作为 slash 未刷新的自然语言回退入口",
            ],
        },
        "trae-solocn": {
            "level": "compatible",
            "reason": "Trae SOLOCN 中国区资料更明确的是 MTC / Code、Skills 与内建 `/plan` `/spec`；仓库已把 `.trae/*` + `~/.trae-cn/skills` 收成当前推荐中文工作区模型，而不是把这些路径硬写成唯一官方合同。",
            "evidence": [
                "官方中国区页面与 changelog 明确 MTC / Code 双模式",
                "官方 changelog 明确内建 `/plan` 与 `/spec`",
                "Super Dev 已改为中文工作区 continuity + rules/skills + natural-language primary entry 模型",
            ],
        },
        "codebuddy-cli": {
            "level": "compatible",
            "reason": "官方文档已明确 CODEBUDDY.md + rules + commands + skills + subagents，当前接入已扩展到完整主面，但仍缺少长期真机回归矩阵。",
            "evidence": [
                "官方文档公开 CODEBUDDY.md、CLI rules、slash commands、skills 与 sub-agents",
                "Super Dev 已改为写入 CODEBUDDY.md + rules + commands + skills + agents，并保留 AGENTS.md compatibility 观察面",
            ],
        },
        "droid-cli": {
            "level": "compatible",
            "reason": "Factory Droid 官方文档已经明确 `AGENTS.md`、`.factory/rules/`、`.factory/skills/`、legacy `.factory/commands/` 与 `droid exec` 的 session 模型，当前接入已按官方宿主面建模。",
            "evidence": [
                "官方文档公开 `AGENTS.md` 作为 Droid 的仓库/用户 briefing packet",
                "官方文档公开 `.factory/rules/`、`.factory/skills/` 与 `.factory/commands/` 目录，并明确 skills 已能直接作为 `/command` 使用",
                "官方文档公开 `droid exec --session-id` 作为会话续跑方式",
                "Super Dev 已改为 `AGENTS.md + .factory/rules + .factory/skills` 主面接入，并把 `.factory/commands` 留作 legacy slash compatibility",
            ],
        },
        "cursor-cli": {
            "level": "compatible",
            "reason": "Cursor CLI 官方文档已明确项目根 AGENTS.md 与 `.cursor/rules/` 的上下文模型，当前接入链路完整；根 `CLAUDE.md` 仅保留为兼容说明，但仍需更多运行级认证样本。",
            "evidence": [
                "官方文档公开 Cursor CLI 会读取项目根 `AGENTS.md` 与 `.cursor/rules/`",
                "Super Dev 已改为共享 AGENTS.md + `.cursor/rules/` 宿主模型，并保留根 `CLAUDE.md` 作为兼容说明",
            ],
        },
        "gemini-cli": {
            "level": "compatible",
            "reason": "Gemini CLI 已按官方 GEMINI.md + settings + custom commands 建模，兼容 skill 面已降到增强层，但还未提升到认证级真机矩阵。",
            "evidence": [
                "官方文档公开 GEMINI.md、settings、custom commands 与会话/恢复命令",
                "Super Dev 已提供项目级 GEMINI.md + .gemini/commands 主面，并把 skills 降到兼容增强层",
            ],
        },
        "kiro-cli": {
            "level": "compatible",
            "reason": "已按 Kiro 官方 AGENTS.md + steering + skills 机制接入，steering 负责长期上下文与行为约束，不再把它误写成 slash 本身。",
            "evidence": [
                "官方文档公开 Kiro CLI 会读取工作区/全局 AGENTS.md、steering 与 skills",
                "Super Dev 已改为 AGENTS.md + `.kiro/steering/` + `.kiro/skills/` + `~/.kiro/steering/` + `~/.kiro/skills/` 接入",
            ],
        },
        "qoder-cli": {
            "level": "compatible",
            "reason": "Qoder CLI 已按官方 `AGENTS.md + .qoder/rules + .qoder/commands + .qoder/skills` 接入，并把 `.qoder/agents/` 收成增强层。",
            "evidence": [
                "官方文档公开项目/用户 `AGENTS.md`、`.qoder/rules/`、commands、skills 与 subagents",
                "Super Dev 已改为 AGENTS + rules + slash command + skills 主接入面，并把 agents 保留为增强层",
            ],
        },
        "qwen-code": {
            "level": "compatible",
            "reason": "Qwen Code 官方文档已明确 QWEN.md、settings、commands、skills、subagents 与 `/resume` / checkpoint restore，当前接入已按官方宿主面建模。",
            "evidence": [
                "官方文档公开 `QWEN.md`、`.qwen/settings.json`、`.qwen/commands/`、`.qwen/skills/` 与 `.qwen/agents/`",
                "官方文档说明 `/resume` 用于继续会话，`/restore` 用于 checkpoint 回滚",
                "Super Dev 已改为 QWEN.md + settings + commands + skills + agents 的 Qwen Code 接入模型",
            ],
        },
        "codebuddy": {
            "level": "experimental",
            "reason": "IDE 侧已对齐官方 CODEBUDDY.md + rules + skills + 任务/workspace 连续性；commands/agents 保留为当前实现增强面，但长期行为仍缺少持续真机验证。",
            "evidence": [
                "官方文档公开 IDE rules、skills 与工作流能力",
                "Super Dev 已写入 CODEBUDDY.md、rules、skills 主接入面，并保留 commands/agents 作为增强层",
            ],
        },
        "copilot-cli": {
            "level": "compatible",
            "reason": "Copilot CLI 已按官方 copilot-instructions + AGENTS.md + skills + agents 面建模，文本触发稳定，但自定义 agent 的长期真机回归仍不足。",
            "evidence": [
                "官方文档公开 AGENTS.md、.github/copilot-instructions.md 与 .github/instructions/**/*.instructions.md",
                "官方文档公开 .github/skills 与 ~/.copilot/skills",
                "官方文档公开 Copilot CLI custom agents 目录 .github/agents 与 ~/.copilot/agents",
                "Super Dev 已写入 AGENTS.md、.github/copilot-instructions.md、.github/skills/super-dev/SKILL.md 与 .github/agents/super-dev.md",
            ],
        },
        "cursor": {
            "level": "experimental",
            "reason": "IDE Agent Chat 能力已按官方 AGENTS.md + rules 建模；根 `CLAUDE.md` 只作为兼容说明，`.cursor/commands/` 作为 beta 增强面，项目级 slash 行为仍需持续运行级验证。",
            "evidence": [
                "官方文档公开 Agent commands、rules，以及项目根 AGENTS.md 上下文",
                "Super Dev 已改为共享 AGENTS.md + `.cursor/rules/` 宿主模型，并保留 `.cursor/commands/` 作为增强层",
            ],
        },
        "windsurf": {
            "level": "experimental",
            "reason": "当前已按官方 AGENTS.md + workflows + skills 与仓库项目 rules 收敛到同一模型，交互模式可用但还未达到认证级稳定性。",
            "evidence": [
                "官方文档公开 AGENTS.md、workflows 与 custom skills",
                "Super Dev 已写入 `AGENTS.md`、`.windsurf/rules/`、`.windsurf/workflows/` 与 skills",
            ],
        },
        "opencode": {
            "level": "experimental",
            "reason": "官方 AGENTS + commands + skills 路径已适配，`.opencode/agents/` 继续作为增强层管理，但仍需要更强的运行级认证覆盖。",
            "evidence": [
                "官方文档公开项目根 AGENTS.md、~/.config/opencode/AGENTS.md、commands、skills 与 agents",
                "Super Dev 已写入项目级 AGENTS、commands、skills，并把 agents 保留为增强层，同时补齐用户级 AGENTS / commands / skills 管理链",
            ],
        },
        "kilo-code": {
            "level": "experimental",
            "reason": "Kilo Code 按 .kilocode/rules/ 规则目录适配，与 Roo Code 生态类似，但仍需更多真机验证。",
            "evidence": [
                "Kilo Code 支持项目级 .kilocode/rules/ 规则目录",
                "Super Dev 已写入规则文件",
            ],
        },
        "kiro": {
            "level": "experimental",
            "reason": "IDE 侧已按官方 AGENTS.md + steering + skills + Agent Chat continuity 对齐；steering 只负责长期上下文，不再误写成 slash 本体。",
            "evidence": [
                "官方文档公开工作区/全局 steering、skills，以及工作区和全局 AGENTS.md 支持",
                "Super Dev 已改为 AGENTS.md + `.kiro/steering/` + `.kiro/skills/` + `~/.kiro/steering/` + `~/.kiro/skills/` 接入",
            ],
        },
        "qoder": {
            "level": "experimental",
            "reason": "官方文档已明确 `AGENTS.md + .qoder/rules + commands + skills`；当前已切到完整主面，并把 `.qoder/agents/` 收成增强层，但仍需要更多真机样本。",
            "evidence": [
                "官方文档公开项目/用户 `AGENTS.md`、`.qoder/rules/`、commands、skills 与 subagents",
                "Super Dev 已改为 AGENTS + `.qoder/rules/super-dev.md` + `.qoder/commands/super-dev.md` + `.qoder/skills/` 主接入面，并把 `.qoder/agents/` 保留为增强层",
            ],
        },
        "workbuddy": {
            "level": "experimental",
            "reason": "WorkBuddy 公开资料能确认任务工作台、Skills、MCP 与项目目录授权；仓库保留 `~/.workbuddy/skills/` 作为当前接入模型的补充面，但不再把它对外宣称为唯一官方文件合同。",
            "evidence": [
                "官方文档公开 WorkBuddy 支持自然语言任务、Skills 扩展、MCP 与本地文件夹授权执行",
                "官方文档公开右侧边栏与任务工作台协同查看项目文件和结果",
                "Super Dev 已为 WorkBuddy 建立标准模式、SEEAI 比赛模式、任务线程恢复与 MCP 验收指引",
            ],
        },
        "vscode-copilot": {
            "level": "experimental",
            "reason": "VS Code Copilot 仅支持 .github/copilot-instructions.md 作为项目指令面，不支持自定义 Skill 或 slash 命令，因此接入深度有限。",
            "evidence": [
                "官方文档公开 .github/copilot-instructions.md 作为项目级指令",
                "Copilot Chat 的 @workspace 指令会读取 copilot-instructions.md",
                "Super Dev 已写入 .github/copilot-instructions.md，但不支持 Skill 和 slash",
            ],
        },
    }

    CERTIFICATION_LABELS: dict[str, str] = {
        "certified": "Certified",
        "compatible": "Compatible",
        "experimental": "Experimental",
    }

    TEXT_TRIGGER_PREFIXES: tuple[str, str] = (TEXT_TRIGGER_PREFIX, TEXT_TRIGGER_PREFIX_FULLWIDTH)

    SEEAI_TEXT_TRIGGER_PREFIXES: tuple[str, str] = (
        SEEAI_TEXT_TRIGGER_PREFIX,
        SEEAI_TEXT_TRIGGER_PREFIX_FULLWIDTH,
    )

    CONTRACT_TRIGGER_GROUPS: dict[str, tuple[str, ...]] = {
        "slash": ("/super-dev", "/super-dev-seeai"),
        "text": TEXT_TRIGGER_PREFIXES + SEEAI_TEXT_TRIGGER_PREFIXES,
    }

    CONTRACT_DOC_GROUP: tuple[str, ...] = (
        "output/*-research.md",
        "output/*-prd.md",
        "output/*-architecture.md",
        "output/*-uiux.md",
        "three core documents",
        "three core docs",
        "三份核心文档",
        "PRD, architecture, and UIUX",
        "PRD / Architecture / UIUX",
        "PRD / 架构 / UIUX",
        "Draft PRD, architecture, and UIUX",
    )

    CONTRACT_CONFIRMATION_GROUP: tuple[str, ...] = (
        "wait for explicit confirmation",
        "wait for approval",
        "wait for user confirmation",
        "for user confirmation",
        "Stop for user confirmation",
        "Create Spec/tasks only after confirmation",
        "先向用户汇报文档摘要与路径，等待明确确认",
        "等待确认",
        "用户未确认前禁止创建 Spec",
        "未经确认不得创建 Spec",
        "暂停等待用户确认",
        "等待用户确认",
        "stop after the three core documents",
    )

    CONTRACT_ARTIFACT_GROUP: tuple[str, ...] = (
        "workspace files",
        "project files",
        "repository workspace",
        "project workspace",
        "项目文件",
        "真实写入项目文件",
        "chat-only summaries do not count",
        "只在聊天里总结不算完成",
        "instead of only replying in chat",
    )

    CONTRACT_FLOW_GROUP: tuple[str, ...] = (
        "SUPER_DEV_FLOW_CONTRACT_V1",
        "PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery",
        "DOC_CONFIRM_GATE: required",
        "PREVIEW_CONFIRM_GATE: required",
        "HOST_PARITY: required",
    )
