# Adaptive Nine-Stage Ledger Proposal

## Summary

Evolve Super Dev without creating a second lifecycle: every real code or product change keeps the same canonical nine-stage ledger, while each stage records whether it is executed, satisfied by reusable evidence, not applicable, or—only for a gate—explicitly waived.

The first slice is a shadow-only domain model. Super Dev v2.4.0 remains the lifecycle authority and the new ledger cannot advance gates, approve itself, dispatch external agents, or change existing workflow behavior.

The user-approved second slice promotes only read visibility: bounded shadow-ledger discovery and validation feed compact summaries into existing workflow-state and CLI read paths. The summary explicitly declares `read_only=true` and `control_authority=none`.

## Motivation

The current standard workflow preserves commercial-delivery completeness but treats stage existence, stage execution, artifact depth, and gate requirements as one fixed chain. This makes small changes feel over-governed and leaves skip/reuse decisions implicit. At the same time, removing stages would create multiple lifecycle identities and weaken auditability.

The new contract keeps one Harness and nine stable stage names while making the treatment of each stage explicit, evidence-bound, role-governed, and invalidatable when scope grows.

## Invariants

1. A real code or product change always has all nine canonical stages.
2. Pure chat or explanation with no change candidate creates no change ledger.
3. Super Dev Core is the only lifecycle and persisted-stage owner.
4. Work stages allow `EXECUTE`, `REUSE`, or `NOT_APPLICABLE`.
5. Gate stages allow `REQUIRE`, `WAIVE`, or `NOT_APPLICABLE`.
6. `quality` and `delivery` are never `NOT_APPLICABLE` for a merge or release candidate; their depth may shrink or evidence may be reused.
7. A writer cannot approve its own skip or waiver.
8. Hidden complexity can only upgrade depth within one change; it cannot downgrade.
9. Reused evidence must identify source, candidate scope, owner, timestamp, and invalidation triggers.
10. The first slice runs in shadow mode and cannot alter v2.4.0 gate decisions.

## First-Slice Scope

### New modules

- `super_dev/change_ledger.py`
- `super_dev/stage_policy.py`
- `super_dev/agent_contract.py`

### Existing modules changed

- `super_dev/workflow_contract.py`
- `super_dev/workflow_stage_truth.py`
- `super_dev/work_mode.py`

### Tests

- `tests/unit/test_change_ledger.py`
- `tests/unit/test_stage_policy.py`
- `tests/unit/test_agent_contract.py`
- existing workflow-contract and stage-truth tests as required

## Data Model

Each change ledger contains:

- change identity and current Harness version;
- intent and governance depth;
- exactly nine stage entries;
- stage kind (`work` or `gate`);
- resolution, runtime status, and artifact depth;
- reason, decision owner, evidence references, expiry, and invalidation triggers;
- shadow-only marker for the first slice.

Each agent assignment contains:

- task and parent task IDs;
- agent level and role;
- workspace, write scope, forbidden actions, placement owner, result owner;
- delegation and stage-advance authority;
- acceptance contract.

## Non-Goals

- no real subagent, Orca, OMP, or worktree dispatch;
- no CLI commands that create or mutate ledgers, and no other user-interface changes;
- no external BMAD, Superpowers, UmaDev, or Grill method integration;
- no replacement of `.super-dev/workflow-state.json`;
- no change to existing pipeline-contract JSON/Markdown output;
- no change to existing docs/preview/quality gate behavior;
- no automatic commit, merge, push, deployment, or global installation.

## Second-Slice Read Promotion

### Added read surface

- discover only `.super-dev/changes/<change-id>/ledger.json`, without recursive scanning;
- enforce project-bound paths, a one-megabyte file limit, JSON-object shape, the active Super Dev Harness identity, shadow-only mode, and the canonical nine-stage contract;
- select the most recently modified valid ledger as the active observation;
- report invalid ledger files as bounded diagnostics without failing the existing status read;
- make `detect_pipeline_summary` expose the observation only when an approved caller opts in, and include it in CLI `run status`, `next`, `continue`, and `resume` payloads;
- use direct standard-output writing for the existing `run status --json` path so long status payloads remain valid JSON.

### Authority boundary

- the read layer exposes no create, save, update, gate, dispatch, merge, or promotion API;
- it does not change `workflow_status`, `recommended_command`, gate decisions, confirmations, or run-state ownership;
- other shared status, delivery-evidence, release-readiness, and host-runtime callers do not receive the field unless separately approved;
- missing ledgers remain quiet and preserve the existing v2.4.0 behavior;
- malformed or oversized ledgers are visible as diagnostics but never become workflow authority.

## Compatibility and Rollback

- The feature is disabled by default with `adaptive_ledger.enabled=false`.
- Old projects without a ledger continue on the v2.4.0 path.
- Shadow ledgers are additive artifacts and never become the only recovery source.
- Rollback is removal of the summary calls and `shadow_ledger_store.py`; existing workflow and review state remain authoritative and ledger files need not be deleted.

## Acceptance

- a code-change ledger always contains the nine canonical stage IDs exactly once;
- chat/explain intent creates no ledger;
- work and gate resolution values are type-safe and mutually valid;
- writer/reviewer authority cannot approve skip, waiver, stage advance, or integration;
- child authority never exceeds parent authority;
- invalid reused evidence becomes `INVALIDATED`;
- UI/API/data/architecture scope changes invalidate the relevant prior decisions;
- quality and delivery cannot be marked not applicable;
- all existing v2.4.0 workflow tests remain behaviorally unchanged when the feature is disabled.

## First-Slice Evidence

- safe affected-workflow regression: 82 passed;
- lint: changed source and tests passed Ruff;
- diff check: passed;
- independent Grok Build review: `VERDICT=ACCEPT` after resolving stage-kind, evidence-expiry, shadow-bypass, authority-narrowing, and compatibility findings;
- existing pipeline-contract JSON/Markdown output remains unchanged;
- known pre-existing Windows `PlanExecutor` baseline remains outside this slice: fixed Bash invocation and POSIX-path expectation produce 2 failures when that test file is included;
- Black and mypy executables are not installed in the current environment, so those checks were not claimed.

## Second-Slice Evidence

- affected nine-stage, workflow-state, work-mode, and CLI regression: 91 passed;
- one symbolic-link test is retained but skipped because the current Windows host does not permit test symbolic-link creation; direct path escape, nested discovery, oversized payload, malformed JSON, foreign shadow mode, and directory-limit behavior passed;
- changed source and tests passed Ruff; diff whitespace check passed;
- the control-plane comparison confirms that opt-in observation does not change workflow status, recommended action, current stage, action card, stages, document/preview confirmation, quality revision, or gate outcomes;
- independent Grok Build read-only review returned `VERDICT=ACCEPT` with no mandatory fixes; its optional findings were used to make shared consumers opt-in, avoid selecting an active ledger after truncated discovery, clarify the read-only terminal message, and expand safety/control tests;
- no ledger create/save/update API, other interface presentation, gate control, agent dispatch, merge, push, or deployment was added.

## Third-Slice Shadow Comparison

The third slice adds an in-memory comparison lab and no production write path. A scope planner derives its decision without reading the frozen expected answer; a separate evaluator checks the plan against four representative expectations and the v2.4.0 all-nine-stage standard contract.

The representative set covers a bounded backend patch, a bounded user-visible UI change, an architectural API/data-contract change with one valid research-evidence reuse, and a commercial cross-stack change. The report records false skips, false blocks, evidence reuse errors, legacy reductions, required user gates, and explanation items.

The first comparison run produced:

- 4 of 4 representative scenarios passed;
- 0 false skips;
- 0 false blocks;
- 0 evidence reuse errors;
- 1 valid evidence reuse;
- 10 system-generated scope explanation items across the four scenarios;
- no production ledger write, workflow-state mutation, gate decision, or agent dispatch.

The comparison also exposed and fixed one first-slice policy inconsistency: a user-visible UI change could previously mark `docs` not applicable while `docs_confirm` remained required. UI changes now retain both the core document work and its confirmation gate.

After independent review, the final comparison contract was tightened further:

- reusable stages are declared by the scenario contract rather than selected by scenario-name special cases;
- mandatory execution is distinct from explicitly allowed evidence reuse;
- frontend, route, style, and component changes retain both core-document work and document confirmation, not only preview confirmation;
- expired, out-of-scope, and undeclared reuse are rejected directly by the planner path;
- each evaluation produces one concise coaching summary instead of exposing raw stage reasons as user questions.

Final affected regression: 110 passed and one existing Windows symbolic-link permission test skipped. Changed source and tests passed Ruff and diff whitespace checks. Independent Grok Build review returned `VERDICT=ACCEPT` with no mandatory fixes, and the follow-up review confirmed its three medium findings were resolved.
