# Adaptive Nine-Stage Ledger — Tasks

## A. Baseline and Contract Freeze

- [x] A1. Record the current repository base, dirty state, Python version, and safe targeted test commands.
- [x] A2. Reconcile the existing uncommitted Skill/source-sync candidate before production-code writes.
- [x] A3. Freeze the exact nine canonical stage IDs and identify every duplicated definition currently used by workflow state, gates, Skill generation, CLI, and tests.
- [x] A4. Freeze the first-slice enums and reject ambiguous aliases.

## B. Agent Authority Contract

- [x] B1. Add `super_dev/agent_contract.py` with root, coordinator, writer, and reviewer levels.
- [x] B2. Model parent task, workspace, write scope, forbidden actions, placement owner, result owner, delegation authority, stage-advance authority, and acceptance.
- [x] B3. Implement downward authority narrowing validation.
- [x] B4. Reject writer self-approval, reviewer production writes, and child permission expansion.
- [x] B5. Add `tests/unit/test_agent_contract.py`.

## C. Nine-Stage Change Ledger

- [x] C1. Add `super_dev/change_ledger.py` with one immutable stage roster derived from the canonical workflow contract.
- [x] C2. Separate stage resolution from runtime status and artifact depth.
- [x] C3. Model reason, decision owner, evidence reference, evidence scope, freshness, and invalidation triggers.
- [x] C4. Add shadow-only serialization without changing workflow-state ownership.
- [x] C5. Add `tests/unit/test_change_ledger.py`.

## D. Stage Policy

- [x] D1. Add `super_dev/stage_policy.py` with legal resolution rules for work stages and gate stages.
- [x] D2. Require coordinator or human authority for skip/waiver decisions.
- [x] D3. Forbid `NOT_APPLICABLE` on quality and delivery for merge/release candidates.
- [x] D4. Require preview confirmation after executed user-visible frontend work.
- [x] D5. Require docs confirmation after product, architecture, UI/UX, API, authorization, or data-contract changes.
- [x] D6. Implement one-way depth escalation and related evidence invalidation.
- [x] D7. Add `tests/unit/test_stage_policy.py`.

## E. Existing Contract Alignment

- [x] E1. Extend `super_dev/workflow_contract.py` without changing the canonical nine stage names.
- [x] E2. Make `super_dev/workflow_stage_truth.py` consume the same canonical roster.
- [ ] E3. Defer `super_dev/orchestrator/contracts.py` wiring until promotion; the shadow slice must not change existing pipeline-contract output.
- [x] E4. Keep `new/evolve/variant/patch/resume` in `super_dev/work_mode.py` orthogonal to governance depth.
- [x] E5. Update existing workflow-contract and stage-truth tests.

## F. Shadow-Mode Verification

- [x] F1. Generate ledgers only for explicit test fixtures in the first slice; do not wire automatic production creation yet.
- [x] F2. Verify pure chat/explain creates no ledger.
- [x] F3. Verify bounded backend, bounded frontend, and architectural-commercial scenarios all retain nine stages with different resolutions/depths.
- [x] F4. Verify stale or out-of-scope evidence invalidation.
- [ ] F5. Verify the feature-disabled path is behaviorally identical to v2.4.0.
- [x] F6. Run targeted tests, lint, diff inspection, and clean-worktree/global-side-effect audit for the promoted read slice.

## G. Review and Promotion Gate

- [x] G1. Obtain an independent read-only review of the unchanged candidate.
- [ ] G2. Compare the shadow ledger decisions against current v2.4.0 behavior on representative changes.
- [ ] G3. Record false skips, false blocks, evidence reuse errors, and user explanation burden.
- [x] G4. Require user approval before wiring the ledger into workflow-state and CLI read surfaces; Web surfaces and real agent dispatch remain unapproved.

## H. User-Approved Read-Only Promotion

- [x] H1. Add a bounded, project-local shadow-ledger reader with size, path, schema, Harness-identity, and nine-stage validation.
- [x] H2. Report malformed ledgers as read diagnostics without breaking existing workflow-state reads.
- [x] H3. Add `shadow_ledger` to the workflow-state summary without changing workflow status, recommendation, or gates.
- [x] H4. Add compact shadow-ledger visibility to `run status`, `next`, `continue`, and `resume`, including valid JSON output.
- [x] H5. Add focused tests for absent, valid, malformed, nested, escaped, and oversized ledger cases plus state/CLI integration.
- [x] H6. Run the affected regression suite, lint, independent read-only review, and prepare the approved local commit; do not push.
