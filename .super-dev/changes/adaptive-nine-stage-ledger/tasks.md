# Adaptive Nine-Stage Ledger — Tasks

## A. Baseline and Contract Freeze

- [ ] A1. Record the current repository base, dirty state, Python version, and safe targeted test commands.
- [ ] A2. Reconcile the existing uncommitted Skill/source-sync candidate before production-code writes.
- [ ] A3. Freeze the exact nine canonical stage IDs and identify every duplicated definition currently used by workflow state, gates, Skill generation, CLI, and tests.
- [ ] A4. Freeze the first-slice enums and reject ambiguous aliases.

## B. Agent Authority Contract

- [ ] B1. Add `super_dev/agent_contract.py` with root, coordinator, writer, and reviewer levels.
- [ ] B2. Model parent task, workspace, write scope, forbidden actions, placement owner, result owner, delegation authority, stage-advance authority, and acceptance.
- [ ] B3. Implement downward authority narrowing validation.
- [ ] B4. Reject writer self-approval, reviewer production writes, and child permission expansion.
- [ ] B5. Add `tests/unit/test_agent_contract.py`.

## C. Nine-Stage Change Ledger

- [ ] C1. Add `super_dev/change_ledger.py` with one immutable stage roster derived from the canonical workflow contract.
- [ ] C2. Separate stage resolution from runtime status and artifact depth.
- [ ] C3. Model reason, decision owner, evidence reference, evidence scope, freshness, and invalidation triggers.
- [ ] C4. Add shadow-only serialization without changing workflow-state ownership.
- [ ] C5. Add `tests/unit/test_change_ledger.py`.

## D. Stage Policy

- [ ] D1. Add `super_dev/stage_policy.py` with legal resolution rules for work stages and gate stages.
- [ ] D2. Require coordinator or human authority for skip/waiver decisions.
- [ ] D3. Forbid `NOT_APPLICABLE` on quality and delivery for merge/release candidates.
- [ ] D4. Require preview confirmation after executed user-visible frontend work.
- [ ] D5. Require docs confirmation after product, architecture, UI/UX, API, authorization, or data-contract changes.
- [ ] D6. Implement one-way depth escalation and related evidence invalidation.
- [ ] D7. Add `tests/unit/test_stage_policy.py`.

## E. Existing Contract Alignment

- [ ] E1. Extend `super_dev/workflow_contract.py` without changing the canonical nine stage names.
- [ ] E2. Make `super_dev/workflow_stage_truth.py` consume the same canonical roster.
- [ ] E3. Extend `super_dev/orchestrator/contracts.py` with change identity and evidence-binding fields needed by the shadow ledger.
- [ ] E4. Keep `new/evolve/variant/patch/resume` in `super_dev/work_mode.py` orthogonal to governance depth.
- [ ] E5. Update existing workflow-contract and stage-truth tests.

## F. Shadow-Mode Verification

- [ ] F1. Generate ledgers only for explicit test fixtures in the first slice; do not wire automatic production creation yet.
- [ ] F2. Verify pure chat/explain creates no ledger.
- [ ] F3. Verify bounded backend, bounded frontend, and architectural-commercial scenarios all retain nine stages with different resolutions/depths.
- [ ] F4. Verify stale or out-of-scope evidence invalidation.
- [ ] F5. Verify the feature-disabled path is behaviorally identical to v2.4.0.
- [ ] F6. Run targeted tests, lint, diff inspection, and clean-worktree/global-side-effect audit.

## G. Review and Promotion Gate

- [ ] G1. Obtain an independent read-only review of the unchanged candidate.
- [ ] G2. Compare the shadow ledger decisions against current v2.4.0 behavior on representative changes.
- [ ] G3. Record false skips, false blocks, evidence reuse errors, and user explanation burden.
- [ ] G4. Require user approval before wiring the ledger into workflow state, CLI/Web surfaces, or real agent dispatch.
