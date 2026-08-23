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

## Fourth-Slice Automatic Shadow Creation

The fourth slice creates a conservative shadow ledger automatically only after `SpecBuilder` has successfully created the stable change directory and tasks. It does not infer skips, waive gates, dispatch agents, or advance workflow state.

### Creation contract

- project configuration must explicitly set both `adaptive_ledger.enabled=true` and `adaptive_ledger.auto_create=true`;
- defaults remain false for old and newly initialized projects;
- `SpecBuilder` is the single production creation owner shared by the CLI pipeline and project creator;
- the change directory must already exist and the change ID must use the safe identifier contract;
- a first write uses a same-directory temporary file and an exclusive hard link, with an exclusive-create fallback for filesystems without hard-link support, so concurrent creators cannot overwrite each other;
- a valid existing ledger is reused byte-for-byte;
- an invalid existing ledger is reported and preserved rather than repaired or overwritten;
- a failed shadow write never fails the primary Spec creation or changes a gate decision;
- interrupted temporary files do not block a later retry;
- the initial plan remains the conservative full nine-stage roster;
- the newly created Spec stage is recorded as satisfied; docs and docs confirmation are recorded together only when the current document digest is confirmed; project-level historical research or document files never satisfy a new change by presence alone.

All configuration, document-binding, path-inspection, and ledger-write work is isolated behind a broad shadow-only failure boundary in `SpecBuilder`. An unexpected shadow exception becomes a `write_failed` diagnostic after proposal/tasks creation and cannot fail the primary change creation.

The repository itself opts into this path in `super-dev.yaml` as a local canary. Package defaults remain disabled.

### Still outside this slice

- no automatic changed-surface classification;
- no automatic application of the comparison lab's skip or reuse decisions;
- no ledger mutation after initial creation;
- no stage-control, confirmation, quality, integration, merge, push, or release authority.

### Fourth-slice evidence

- affected configuration, SpecBuilder, lifecycle, comparison, workflow-state, and CLI regression: 218 passed;
- one existing Windows symbolic-link permission test skipped;
- changed source and tests passed Ruff and diff whitespace checks;
- concurrent creation produced exactly one `created` and one `existing` result with one valid final ledger;
- hard-link failure used the exclusive-create fallback without overwriting;
- simulated failure of both write paths left no final ledger and did not fail Spec creation;
- historical output files did not satisfy research or docs for a new change;
- invalid JSON and mismatched change IDs were preserved byte-for-byte and reported;
- independent Grok Build review first returned `VERDICT=REVISE` for historical-file status pollution and incomplete SpecBuilder failure isolation; both mandatory findings were fixed;
- follow-up review returned `VERDICT=ACCEPT` with no remaining mandatory fixes.

The exclusive-create fallback may leave an invalid final file if a non-hard-link filesystem crashes during the fallback write. Such a file is preserved and reported rather than overwritten. The primary NTFS canary path uses the completed temporary file plus exclusive hard link and does not expose this partial-write window.

## Fifth-Slice Validation Responsibility Split

The fifth slice removes the comparison laboratory from the published `super_dev` package and separates its responsibilities:

- `super_dev/stage_scope.py` owns the production-grade pure rule that maps changed surfaces, work mode, and governance depth to required stages;
- `super_dev/stage_policy.py` consumes that same rule when rejecting illegal skips, including the aligned rule that new or commercial changes cannot skip research, docs, or document confirmation;
- representative scenarios and frozen expected answers live under `tests/fixtures/`;
- in-memory plan assembly and evaluation live under `tests/support/`;
- coaching summaries and report generation live under `tools/` and are excluded from the published package;
- `super_dev/shadow_validation.py` is removed;
- the production ledger lifecycle remains the only file writer and does not import the comparison fixtures, evaluator, or report tool.

This split removes the second positive stage-rule source from the shipped package. The comparison remains useful as a development check without presenting an unused public governance API.

### Fifth-slice evidence

- affected scope, policy, comparison, package-boundary, lifecycle, configuration, workflow-state, and CLI regression: 250 passed;
- one existing Windows symbolic-link permission test skipped;
- changed source and tests passed Ruff and diff whitespace checks;
- `python -m tools.shadow_comparison` completed and reproduced four passing representative scenarios;
- package discovery includes only `super_dev*`; tests and tools are excluded;
- syntax-tree import checks confirm production modules do not import `tests` or `tools`;
- `super_dev.shadow_validation` is no longer importable;
- production ledger lifecycle and SpecBuilder creation behavior are unchanged by this split;
- Grok Build's architecture review recommended `SPLIT`; the implementation review returned `VERDICT=ACCEPT` with no mandatory fixes;
- follow-up tests cover new or commercial changes retaining research, docs, and document confirmation even with no changed-surface hint.
