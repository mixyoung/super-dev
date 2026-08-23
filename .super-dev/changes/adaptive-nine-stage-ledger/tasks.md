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
- [x] F5. Verify the default path does not expose or consume shadow decisions and preserves v2.4.0 control behavior.
- [x] F6. Run targeted tests, lint, diff inspection, and clean-worktree/global-side-effect audit for the promoted read slice.

## G. Review and Promotion Gate

- [x] G1. Obtain an independent read-only review of the unchanged candidate.
- [x] G2. Compare shadow decisions against the v2.4.0 all-nine-stage standard contract on four representative changes.
- [x] G3. Record false skips, false blocks, evidence reuse errors, valid reuse, required user gates, and explanation burden.
- [x] G4. Require user approval before wiring the ledger into workflow-state and CLI read surfaces; Web surfaces and real agent dispatch remain unapproved.

## H. User-Approved Read-Only Promotion

- [x] H1. Add a bounded, project-local shadow-ledger reader with size, path, schema, Harness-identity, and nine-stage validation.
- [x] H2. Report malformed ledgers as read diagnostics without breaking existing workflow-state reads.
- [x] H3. Add `shadow_ledger` to the workflow-state summary without changing workflow status, recommendation, or gates.
- [x] H4. Add compact shadow-ledger visibility to `run status`, `next`, `continue`, and `resume`, including valid JSON output.
- [x] H5. Add focused tests for absent, valid, malformed, nested, escaped, and oversized ledger cases plus state/CLI integration.
- [x] H6. Run the affected regression suite, lint, independent read-only review, and prepare the approved local commit; do not push.

## I. Representative Shadow Comparison

- [x] I1. Freeze bounded backend, bounded UI, architectural API/data, and commercial cross-stack expectations.
- [x] I2. Add an in-memory planner that derives stage treatment from change scope without reading the frozen expected answer.
- [x] I3. Add an independent evaluator for false skip, false block, evidence reuse error, legacy reduction, user gates, and explanation burden.
- [x] I4. Add one valid project-scoped evidence reuse and negative tests for stale or out-of-scope reuse.
- [x] I5. Write the repeatable comparison results to `shadow-comparison-report.md` and keep production writes disabled.
- [x] I6. Run the affected regression suite, lint, independent read-only review, and prepare the local commit; do not push.

## J. Automatic Shadow Ledger Creation

- [x] J1. Add strict nested configuration with both feature and automatic-creation switches disabled by default.
- [x] J2. Make `SpecBuilder` the single creation owner after a stable change ID, proposal, and tasks exist.
- [x] J3. Add safe-path validation, atomic exclusive creation, idempotent reuse, and no-overwrite handling.
- [x] J4. Preserve invalid existing evidence and keep shadow failures from blocking primary Spec creation.
- [x] J5. Record the newly created Spec as satisfied, bind docs satisfaction to current digest confirmation, reject historical-file inference, and keep the initial plan conservative.
- [x] J6. Add disabled, repeat, concurrent, interrupted, unsafe-path, invalid-existing, configuration, and SpecBuilder integration tests.
- [x] J7. Run the affected regression suite, lint, independent read-only review, and prepare the local commit; do not push.

## K. Comparison Responsibility Split

- [x] K1. Add production stage-range rules in `super_dev/stage_scope.py` with one shared surface vocabulary.
- [x] K2. Make `stage_policy.py` consume the same required-stage rule and close the research-skip gap for new or commercial changes.
- [x] K3. Move representative scenarios and frozen expectations to `tests/fixtures/`.
- [x] K4. Move in-memory plan assembly and evaluation to `tests/support/`.
- [x] K5. Move coaching summaries and report generation to `tools/`, outside the published package.
- [x] K6. Remove `super_dev/shadow_validation.py` and verify that production lifecycle code has no test/tool dependency.
- [x] K7. Run the affected regression suite, package-boundary check, independent read-only review, and prepare the local commit; do not push.
