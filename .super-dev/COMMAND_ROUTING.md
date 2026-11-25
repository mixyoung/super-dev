# Super Dev Command Routing Map

> Version: 2.3.0 | Last updated: 2026-03-31

## Routing Principle

There are exactly TWO execution contexts:

1. **Terminal** — The user's shell. Only used for `pip install super-dev`.
2. **Host** — The AI coding host (Claude Code, Cursor, Codex, etc.). Everything else.

When the host receives `/super-dev <args>`, it routes based on the first token:

- **Known subcommand** → Execute via Bash tool: `super-dev <full args>`
- **Natural language** → Enter pipeline mode (research-first workflow)
- **No args** → Execute via Bash tool: `super-dev` (check status, continue)

---

## Terminal ONLY

```bash
pip install super-dev           # Install
pip install -U super-dev        # Upgrade
pip install super-dev[dev]      # Install with dev dependencies
```

These are the ONLY commands a user ever runs in a terminal.

---

## Host Commands (via `/super-dev <args>`)

All commands below are entered in the host as `/super-dev <command>`.
The host executes them via Bash tool automatically.
You do NOT need to open a terminal.

### Pipeline Flow

| Command | What it does |
|:--------|:-------------|
| `/super-dev <natural language>` | Start new pipeline with requirement |
| `/super-dev` (no args) | Check status and continue current pipeline |
| `/super-dev run <phase>` | Jump to specific phase (research/prd/architecture/uiux/spec/frontend/backend/quality/delivery) |
| `/super-dev status` | Show current pipeline status |
| `/super-dev next` | Recommend next step |
| `/super-dev continue` | Continue current phase |
| `/super-dev resume` | Resume after break (reads SESSION_BRIEF) |
| `/super-dev confirm <phase>` | Confirm a gate (docs/preview/ui/architecture/quality) |
| `/super-dev jump <stage>` | Jump to a specific stage |

### Project Setup

| Command | What it does |
|:--------|:-------------|
| `/super-dev init` | Initialize project config (super-dev.yaml) |
| `/super-dev bootstrap` | Initialize workflow contract and bootstrap summary |
| `/super-dev setup <host>` | One-step host integration (rules + skill + slash) |
| `/super-dev install` | Interactive host selection and setup |
| `/super-dev start` | Non-technical user onboarding |
| `/super-dev onboard` | Full onboarding wizard |
| `/super-dev detect --auto` | Detect installed hosts and report compatibility |
| `/super-dev doctor --fix` | Diagnose and fix integration issues |
| `/super-dev migrate` | Migrate project config to latest version |
| `/super-dev update` | Check for and install CLI updates |

### Governance & Quality

| Command | What it does |
|:--------|:-------------|
| `/super-dev enforce install` | Install enforcement hooks |
| `/super-dev enforce validate` | Run validation checks |
| `/super-dev enforce status` | View enforcement status |
| `/super-dev quality` | Run quality gate |
| `/super-dev review docs` | View/update three-document confirmation |
| `/super-dev review ui` | View/update UI review state |
| `/super-dev review preview` | View/update preview confirmation |
| `/super-dev review architecture` | View/update architecture revision |
| `/super-dev review quality` | View/update quality revision |
| `/super-dev parking list` / `add` / `resolve` / `check` | Manage standalone `.super-dev/parking-lot.json` deferred items |
| `/super-dev governance report` | Generate governance report |

### Delivery

| Command | What it does |
|:--------|:-------------|
| `/super-dev release readiness` | Release readiness check |
| `/super-dev release proof-pack` | Generate delivery evidence package |

### Spec Management

| Command | What it does |
|:--------|:-------------|
| `/super-dev spec list` | List all changes |
| `/super-dev spec show <id>` | Show change details |
| `/super-dev spec propose <id>` | Create change proposal |
| `/super-dev spec validate` | Validate spec format |
| `/super-dev spec view` | Interactive spec dashboard |
| `/super-dev spec trace <id>` | Requirements traceability matrix |
| `/super-dev spec quality <id>` | Spec completeness score |
| `/super-dev spec consistency <id>` | Spec-code drift detection |
| `/super-dev spec acceptance <id>` | Generate acceptance checklist |
| `/super-dev task list` | List spec tasks |
| `/super-dev task status <id>` | Task completion status |

### Analysis

| Command | What it does |
|:--------|:-------------|
| `/super-dev analyze` | Analyze project structure |
| `/super-dev repo-map` | Generate repository structure map |
| `/super-dev impact <description>` | Change impact analysis |
| `/super-dev regression-guard <desc>` | Regression checklist |
| `/super-dev dependency-graph` | Dependency graph and critical paths |
| `/super-dev feature-checklist` | PRD scope coverage audit |
| `/super-dev product-audit` | Cross-team product audit report |

### Query

| Command | What it does |
|:--------|:-------------|
| `/super-dev config list` | View project config |
| `/super-dev memory list` | View memory entries |
| `/super-dev experts list` | View expert roles |
| `/super-dev hooks list` | View configured hooks |
| `/super-dev compact list` | View compact summaries |
| `/super-dev policy show` | View current policy |
| `/super-dev knowledge stats` | Knowledge usage statistics |
| `/super-dev metrics` | Pipeline metrics |

### Code Generation

| Command | What it does |
|:--------|:-------------|
| `/super-dev create <description>` | One-shot: docs + spec from description |
| `/super-dev pipeline <description>` | Full pipeline with advanced options |
| `/super-dev fix <description>` | Bugfix mode |
| `/super-dev wizard` | Zero-barrier guided mode |
| `/super-dev generate scaffold` | Generate project scaffold |
| `/super-dev generate components` | Generate UI component stubs |
| `/super-dev generate types` | Generate shared TypeScript types |
| `/super-dev generate tailwind` | Generate tailwind config from UIUX |
| `/super-dev expert <role>` | Invoke specific expert |

### Design

| Command | What it does |
|:--------|:-------------|
| `/super-dev design search <query>` | Search design assets |
| `/super-dev design generate` | Generate design system |
| `/super-dev design tokens` | Generate design tokens |
| `/super-dev design landing` | Landing page patterns |
| `/super-dev design chart <desc>` | Chart type recommendations |
| `/super-dev design ux <query>` | UX best practices |
| `/super-dev design stack <name>` | Tech stack best practices |
| `/super-dev design codegen <comp>` | Component code snippets |

### Host Integration

| Command | What it does |
|:--------|:-------------|
| `/super-dev skill install super-dev -t <host>` | Install skill for host |
| `/super-dev skill list -t <host>` | List installed skills |
| `/super-dev skill uninstall <name> -t <host>` | Remove skill |
| `/super-dev integrate setup -t <host>` | Generate integration config |
| `/super-dev integrate audit --auto` | Audit all detected hosts |

### Misc

| Command | What it does |
|:--------|:-------------|
| `/super-dev deploy --docker` | Generate Dockerfile |
| `/super-dev deploy --cicd github` | Generate CI/CD config |
| `/super-dev clean` | Clean old output artifacts |
| `/super-dev feedback` | Open GitHub Issues page |
| `/super-dev completion zsh` | Generate shell completions |

---

## Complete Known Subcommand List

These are the tokens that trigger Bash execution (not pipeline mode):

```
init, bootstrap, setup, install, start, onboard, detect, doctor, migrate, update,
run, status, next, continue, resume, jump, confirm,
review, release, quality, enforce, parking,
spec, task, config, policy, governance, knowledge,
memory, hooks, experts, compact,
analyze, repo-map, impact, regression-guard, dependency-graph,
feature-checklist, product-audit,
create, pipeline, fix, wizard,
generate, design, deploy, preview, expert, metrics,
skill, integrate, clean, completion, feedback,
studio, workflow
```

Anything NOT in this list is treated as natural language and enters pipeline mode.
