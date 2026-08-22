# Adaptive Nine-Stage Ledger Proposal

## Summary

Evolve Super Dev without creating a second lifecycle: every real code or product change keeps the same canonical nine-stage ledger, while each stage records whether it is executed, satisfied by reusable evidence, not applicable, or—only for a gate—explicitly waived.

The first slice is a shadow-only domain model. Super Dev v2.4.0 remains the lifecycle authority and the new ledger cannot advance gates, approve itself, dispatch external agents, or change existing workflow behavior.

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
- no CLI or Web UI changes;
- no external BMAD, Superpowers, UmaDev, or Grill method integration;
- no replacement of `.super-dev/workflow-state.json`;
- no change to existing pipeline-contract JSON/Markdown output;
- no change to existing docs/preview/quality gate behavior;
- no automatic commit, merge, push, deployment, or global installation.

## Compatibility and Rollback

- The feature is disabled by default with `adaptive_ledger.enabled=false`.
- Old projects without a ledger continue on the v2.4.0 path.
- Shadow ledgers are additive artifacts and never become the only recovery source.
- Rollback is removal/disablement of the shadow ledger path; existing workflow and review state remain authoritative.

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
