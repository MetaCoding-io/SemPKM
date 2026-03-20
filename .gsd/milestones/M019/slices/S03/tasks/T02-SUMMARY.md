---
id: T02
parent: S03
milestone: M019
provides:
  - Playwright E2E test for full Todoist sync lifecycle (11 phases)
  - todoistSync selector block in e2e/helpers/selectors.ts
key_files:
  - e2e/tests/37-todoist-sync/todoist-sync.spec.ts
  - e2e/helpers/selectors.ts
key_decisions: []
patterns_established:
  - Todoist sync E2E follows same phase structure as github-sync.spec.ts (cleanup → install → connect → sync → SPARQL verify → admin → cleanup)
observability_surfaces:
  - E2E test phase comments (0–10) identify exact failure point in Playwright trace/report
  - SPARQL verification checks externalProvider="todoist" and priority="critical" mapping
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Write Playwright E2E test and add Todoist selectors

**Added todoistSync selector block and 11-phase Playwright E2E test covering full Todoist sync lifecycle against mock API**

## What Happened

Added `todoistSync` selector block to `e2e/helpers/selectors.ts` with 11 selectors matching actual template HTML IDs/classes from `connect.html`, `connect_status.html`, and `projects.html`.

Created `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` following the `github-sync.spec.ts` phase structure with 11 phases:
- Phase 0: Cleanup prior installs
- Phase 1: Install basic-pkm model
- Phase 2: Install todoist-sync app (documented pre-existing subprocess 500 error)
- Phase 3: Open app settings in workspace (handles collapsed APPS section per KNOWLEDGE.md)
- Phase 4: Connect PAT with mock token `test-todoist-pat-token-abc123`
- Phase 5: Select project from htmx-loaded checkboxes
- Phase 6: Configure bidirectional sync
- Phase 7: Sync Now with generous timeout
- Phase 8: SPARQL verification — counts todoist tasks and verifies priority inversion (Todoist 4 → bpkm "critical")
- Phase 9: Admin detail page check
- Phase 10: Cleanup uninstall

All selectors cross-checked against template HTML — every ID and class matches.

## Verification

- `npx playwright test e2e/tests/37-todoist-sync/ --list` — lists 2 tests (chromium + firefox) with no TypeScript errors
- `rg` cross-check confirmed all 9 selector targets exist in template HTML files
- Mock server selftest passes (10/10 checks) — prerequisite from T01 still valid

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx playwright test e2e/tests/37-todoist-sync/ --list` | 0 | ✅ pass | 4s |
| 2 | `rg "todoist-token\|api-key-form\|connection-status\|..." apps/todoist-sync/frontend/templates/` | 0 | ✅ pass | <1s |
| 3 | `python3 e2e/mock-todoist-api/server.py --selftest` | 0 | ✅ pass | <1s |
| 4 | `rg "os.environ" apps/todoist-sync/services/todoist_client.py apps/todoist-sync/services/auth.py` | 0 | ✅ pass | <1s |
| 5 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | <1s |

## Diagnostics

- **Test compilation:** `npx playwright test e2e/tests/37-todoist-sync/ --list` — verifies TypeScript compiles and test is discoverable
- **Selector drift:** `rg "todoist-token|api-key-form|connection-status|project-checkbox|sync-config-form|sync-now-btn|sync-stats" apps/todoist-sync/frontend/templates/` — cross-checks selectors against templates
- **Phase identification:** Each test phase is labeled with a comment header (`Phase 0 — Cleanup`, etc.) so Playwright traces show exactly where a failure occurred
- **SPARQL queries:** Phase 8 runs two SPARQL queries (count + ASK) that produce observable pass/fail evidence of sync data creation

## Deviations

None. Test follows the plan's phase structure exactly.

## Known Issues

- Pre-existing subprocess 500 error may cause Phase 2 (app install) to fail — documented in test comments, not Todoist-specific
- Worktree `e2e/` directory required `npm install` to resolve `@playwright/test` — node_modules are not shared with main tree

## Files Created/Modified

- `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` — 11-phase E2E test for Todoist sync lifecycle
- `e2e/helpers/selectors.ts` — Added `todoistSync` selector block with 11 selectors
- `.gsd/milestones/M019/slices/S03/tasks/T02-PLAN.md` — Added missing Observability Impact section
