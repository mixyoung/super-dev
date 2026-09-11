# Repository contribution entry

维护 Super Dev 本身时，先读仓库根的 [项目演进与贡献准则](../docs/CONTRIBUTION_POLICY.md) 与 [贡献指南](../CONTRIBUTING.md)，遵守已确认范围和原验收标准。这是仓库维护入口，不注入普通用户 Skill，也不覆盖下方宿主生成区块。

<!-- BEGIN SUPER DEV CLAUDE -->
# Super Dev Claude Code Integration

This project uses a pipeline-driven development model.

## Positioning
- Super Dev does not own a model endpoint.
- Claude Code remains the execution host for coding capability.
- Super Dev provides governance: protocol, gates, and audit artifacts.

## Runtime Contract
- Treat Super Dev as the local Python workflow tool plus Claude Code `CLAUDE.md + Skills` integration.
- Primary surfaces are project-root `CLAUDE.md`, compatibility mirror `.claude/CLAUDE.md`, project-level `.claude/skills/super-dev/`, and user-level `~/.claude/skills/super-dev/`.
- Compatibility surface `.claude/commands/super-dev.md` remains installed so older Claude Code builds still converge onto the same Super Dev workflow.
- Optional repo enhancement surfaces `.claude-plugin/marketplace.json` and `plugins/super-dev-claude/.claude-plugin/plugin.json` can expose a richer Claude-native plugin layer without replacing the base `CLAUDE.md + Skills` contract.
- When the user triggers `/super-dev`, `super-dev:`, or `super-dev：`, enter the Super Dev pipeline immediately rather than handling it like casual chat.
- Use Claude Code browse/search for research and Claude Code terminal/editing for implementation.
- Use local `super-dev` commands whenever you need to generate/update docs, spec artifacts, quality reports, and delivery outputs.

## First-Response Contract
- On the first reply after a host-supported Super Dev entry (for example `/super-dev ...`, `$super-dev`, `super-dev: ...`, `super-dev：...`, `/super-dev-seeai ...`, `$super-dev-seeai`, `super-dev-seeai: ...`, or `super-dev-seeai：...`), explicitly state that the matching Super Dev mode is now active rather than normal chat mode.
- A read-only explanation, analysis or review does not authorize implementation, file changes or workflow state transitions, even when workflow artifacts exist. Keep existing state unchanged. In mixed requests, act only on explicitly authorized changes; do not ask again for authority already given. Reading these rules as review material does not activate their workflow. For execution requests, continue Super Dev from the valid recorded change and phase rather than restarting.
- Execution requests resume the explicitly active change and valid phase; artifacts or timestamps alone do not select a task.
- Before the first reply, read `.super-dev/WORKFLOW.md` and `output/*-bootstrap.md` when present, and treat them as the explicit bootstrap contract for this repository.
- The first reply must report the actual phase: new standard work follows its work-mode entry (new: the current phase is `research`; evolve/variant/patch: baseline), while new SEEAI work starts at research. For resume, read SESSION_BRIEF and continue the recorded phase and pending gates; do not restart. Read knowledge and do research when that stage is pending.
- In standard mode, continue pending stages: research -> three core documents -> docs confirmation -> Spec/tasks -> applicable frontend runtime verification -> wait for user preview confirmation -> backend/tests/delivery. Non-UI work keeps the existing not-applicable path.
- In SEEAI mode, the next sequence is research -> compact competition docs -> wait for user confirmation -> compact Spec -> full-stack sprint -> polish / handoff.
- Both modes must explicitly promise that they will stop after the three core documents and wait for approval before creating Spec or writing code.

## Local Knowledge Contract
- Read relevant files under `knowledge/` before drafting PRD, architecture, and UIUX.
- If `output/knowledge-cache/*-knowledge-bundle.json` exists, read it first and inherit its local knowledge hits into later stages.
- Knowledge requirements without explicit applicability conditions remain mandatory. Apply explicitly conditional requirements according to their stated conditions, and explain why each selected requirement applies. Retrieval is not permission to silently weaken requirements, extend task scope, or change confirmed decisions. Explicit examples and optional methods retain that declared status. Preserve project configuration and existing default quality requirements; report unresolved conflicts instead of choosing a lower standard or rewriting the knowledge base.

## Conversation Continuity Contract
- If `.super-dev/SESSION_BRIEF.md` exists, read it before responding and treat it as the active workflow state.
- If the workflow is waiting for docs confirmation, preview confirmation, UI revision, architecture revision, or quality revision, then user replies like `修改`, `补充`, `继续改`, `确认`, `通过`, `继续`, or detailed feedback remain inside the current Super Dev stage.
- After each requested revision inside a gate, stay in the same stage, update the required artifacts, summarize what changed, and wait again for explicit confirmation.
- Do not silently exit Super Dev mode because the user asked for several edits, follow-up questions, or extra constraints.
- Only leave the current Super Dev workflow if the user explicitly says to cancel the workflow, restart from scratch, or switch back to normal chat.

## Before coding
1. If Claude Code browse/search is available, research similar products first and write output/*-research.md as a real repository file
2. Read output/*-prd.md
3. Read output/*-architecture.md
4. Read output/*-uiux.md
5. Summarize the three core documents to the user and wait for explicit confirmation before creating Spec or coding
6. Chat-only summaries do not count as completion; the required artifacts must exist in the workspace
7. Read output/*-execution-plan.md
8. Follow .super-dev/changes/*/tasks.md after confirmation, with applicable frontend runtime verification and standard-mode user preview confirmation before backend work

9. If the user requests a UI redesign or says the UI is unsatisfactory, first update `output/*-uiux.md`, then redo the frontend, and rerun frontend runtime + UI review before continuing.

## Output Quality
- Keep security/performance constraints from red-team report.
- Ensure quality gate threshold is met before merge.
- UI must follow output/*-uiux.md and avoid AI-looking templates (purple gradient, emoji icons, default-font-only).
- Before any UI implementation, lock the icon library, typography, design token system, component ecosystem, and page skeleton from output/*-uiux.md.
- Do not use emoji as functional icons or placeholders.
- For non-conversational AI products, avoid Claude / ChatGPT-style shells unless the UI plan explicitly justifies them.
- UI implementation must define typography system, design tokens, page hierarchy and component states before polishing visuals.
- Prioritize real screenshots, trust modules, proof points and task flows over decorative hero sections.

## Coding Constraints (active during ALL coding phases)

These rules apply every time you write or edit a file. They are NOT suggestions:

### Tech Stack Pre-Research
- Before writing code, read the actual project dependency manifest (pyproject.toml / requirements.txt / package.json / go.mod as applicable). UI libraries, tokens and page skeletons are required only for UI changes.
- If unsure about an API for the installed version, use WebFetch to read official docs first.
- Never guess API signatures. Check docs.

### Icon & Visual Rules
- Icons MUST come from a declared icon library (Lucide/Heroicons/Tabler). No emoji as icons.
- For UI changes, follow the approved brand and typography; avoid unconsidered template defaults.
- For UI changes, check functional icon usage; do not delete emoji in user input or analyzed examples.

### Frontend/Backend Alignment
- Frontend fetch URLs must exactly match backend route definitions.
- Define API paths as shared constants when possible.

### Per-File Self-Check
- Check relevant imports and interfaces; UI-only icon and token rules do not constrain non-UI text or code.
- After completing a feature, run build + lint. Fix errors before moving on.

### Host-First Governance During Coding
- 完成 UI 后，优先在宿主里继续当前流程并触发 `/super-dev-review ui`，不要把内部 CLI 当成日常开发入口。
- 需要进入质量与交付时，优先在宿主里继续当前流程或用 `/super-dev-run quality`、`/super-dev-review quality` 这类宿主交互面。
- 终端侧 `super-dev` CLI 保留给维护与治理补救，不负责日常脚手架、实现与返工调度。

## Four-Layer Governance Model

Super Dev governance operates at four layers:

**Layer 1 — CLAUDE.md (Persistent Rules)**
Project-root `CLAUDE.md` is the canonical persistent memory surface. `.claude/CLAUDE.md` is kept as a compatibility mirror for builds that still read nested memory files.

**Layer 2 — Skills (Primary Execution Contract)**
Project-level `.claude/skills/super-dev/` and user-level `~/.claude/skills/super-dev/` carry the primary Super Dev execution contract. Claude Code only uses `super-dev` as the single skill name; old legacy aliases are only retained for cleanup/migration paths.

**Layer 3 — Hooks (Runtime Enforcement)**
PreToolUse hooks validate every file write. PostToolUse hooks audit results.
Hooks are auto-registered when /super-dev is invoked.

**Layer 4 — CLI Commands & Optional Plugin Enhancement (On-Demand Checks)**
Maintenance-only CLI checks may still exist behind the scenes, but ordinary development should stay on host entry surfaces instead of teaching users `enforce` / `quality` command habits.
If Claude Code surfaces repo plugins, `.claude-plugin/marketplace.json` + `plugins/super-dev-claude/.claude-plugin/plugin.json` should enhance the same Super Dev flow rather than fork it.

## Super Dev System Flow Contract
- SUPER_DEV_FLOW_CONTRACT_V1
- PHASE_CHAIN: research>docs>docs_confirm>spec>frontend>preview_confirm>backend>quality>delivery
- DOC_CONFIRM_GATE: required
- PREVIEW_CONFIRM_GATE: required
- HOST_PARITY: required

## 面向中国大陆用户的语言与术语契约（强制）
- 面向中国大陆用户的用户界面、聊天、确认问题、错误提示和报告，优先使用自然、直接、符合中国大陆语言习惯的中文。
- 优先使用中国大陆日常开发和产品沟通中的常见说法；避免生僻词、直译腔、翻译软件式句子和不必要的中英混杂。
- 技术概念第一次出现时，使用“中文名称（英文代码名）”；后续优先只用中文名称，仅在精确核对时再次显示英文代码名。
- 状态统一显示为通过（`PASS`）、失败（`FAIL`）、受阻（`BLOCKED`）；不得面向用户只显示裸英文状态。
- `candidate` 面向用户统一称“当前代码版本”，只在证据详情中显示字段（`candidate_digest`）。
- 命令、文件名和程序字段保留精确英文原文并使用代码格式；解释仍先用中文。
- 内部日志、JSON 和 API 字段可以保留英文，但不得直接照搬成用户文案。
<!-- END SUPER DEV CLAUDE -->





