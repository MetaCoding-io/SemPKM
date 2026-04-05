---
id: T02
parent: S04
milestone: M047
key_files:
  - e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts
key_decisions:
  - Used admin form endpoint (POST /admin/models/install with form data) instead of the non-existent JSON API path from the task plan
duration: 
verification_result: passed
completed_at: 2026-04-05T00:29:04.336Z
blocker_discovered: false
---

# T02: Created Playwright E2E test covering PPV v2 model install, dashboard/workflow verification, UI rendering, and graceful uninstall handling

**Created Playwright E2E test covering PPV v2 model install, dashboard/workflow verification, UI rendering, and graceful uninstall handling**

## What Happened

Created `e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts` — a consolidated single-test Playwright spec that exercises the full PPV v2 lifecycle in 7 phases: pre-clean, install via admin form endpoint, verify 5 dashboards via API, verify 5 workflows via API, open Action Items dashboard and verify GridStack rendering, launch Daily Check-in workflow and verify runner/stepper/navigation rendering, and graceful uninstall handling (200 with error HTML, 409, or 404). Adapted the task plan's API paths to match the real admin endpoints (form data, HTML responses).

## Verification

TypeScript compilation verified with zero errors from the new file. Both slice-level verification checks pass (seed data type counts + enriched fields). The test file follows the established pattern from mental-model-expansion.spec.ts — single consolidated test, generous timeouts, best-effort cleanup.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx tsc --noEmit 2>&1 | grep '47-ppv' | wc -l` | 0 | ✅ pass | 8000ms |
| 2 | `python3 -c "...assert types.get('ppv:GuidingPrinciples')==1; assert types.get('ppv:PillarScore')==3..."` | 0 | ✅ pass | 200ms |
| 3 | `python3 -c "...assert 'ppv:wins' in weekly..."` | 0 | ✅ pass | 150ms |

## Deviations

Used POST /admin/models/install with form data instead of the plan's non-existent POST /api/models/install with JSON. Used ownerRequest fixture directly instead of manual cookie extraction.

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts`
