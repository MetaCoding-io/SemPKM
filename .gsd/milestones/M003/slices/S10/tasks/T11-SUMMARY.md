---
id: T11
parent: S10
milestone: M003
provides:
  - e2e tests for lint API endpoints (results, status, diff) with full response shape validation
  - e2e test for validation lifecycle through lint surface (create object → verify lint status reflects run)
  - e2e tests for monitoring config, icons, my-views, nav-tree, explorer/tree endpoints
key_files:
  - e2e/tests/04-validation/lint-api.spec.ts
  - e2e/tests/04-validation/validation-api.spec.ts
  - e2e/tests/06-settings/misc-endpoints.spec.ts
key_decisions:
  - Validation API endpoints (/api/validation/*) were removed in 37-02 and replaced by /api/lint/* — rewrote validation-api.spec.ts to test validation lifecycle through the lint surface instead of calling non-existent endpoints
  - Consolidated from 11 test() functions (4 lint + 2 validation + 5 misc) down to 3 test() functions (1 per file) to stay within the 5/minute magic-link rate limit
patterns_established:
  - For deprecated/removed endpoints, test the replacement surface with the original intent (validation lifecycle tested via lint status after mutation)
  - Icons endpoint returns {tree, tab, graph} context maps — assert all three contexts exist and at least one has entries
observability_surfaces:
  - none — test-only task with no production code changes
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T11: Lint API, validation endpoints, monitoring config, icons, my-views tests

**Rewrote 3 test files into 3 consolidated test functions covering lint API response shapes, validation lifecycle through lint surface, and 5 miscellaneous endpoints — all passing.**

## What Happened

Rewrote the pre-existing test files for lint API, validation API, and miscellaneous endpoints. The lint-api tests now validate the full LintResultsResponse, LintStatusResponse, and LintDiffResponse model shapes (all fields, correct types, nullable fields). The validation-api tests were updated to reflect that `/api/validation/*` endpoints were removed in 37-02 — the test now verifies validation runs are visible through the lint surface by creating an object and checking lint status. The misc-endpoints tests cover monitoring config (PostHog model shape), icons (tree/tab/graph context maps), my-views (HTML fragment), nav-tree, and explorer/tree endpoints.

## Verification

```
cd e2e && npx playwright test tests/04-validation/lint-api.spec.ts tests/04-validation/validation-api.spec.ts tests/06-settings/misc-endpoints.spec.ts --project=chromium
# 3 passed (4.7s)
```

Slice-level checks (partial — T11 is not the final task):
- `rg "test\.skip\(" e2e/tests/ -c -g '*.ts' | awk -F: '{sum+=$2} END{print sum}'` → 18 (remaining stubs in other test areas, to be addressed in T12)
- All backend routers targeted by this task (lint, monitoring, browser/icons, browser/my-views, browser/nav-tree, browser/explorer/tree) now have corresponding e2e tests

## Diagnostics

None — test-only task with no production code changes.

## Deviations

- `/api/validation/latest` and `/api/validation/{event_id}` endpoints no longer exist (removed in 37-02, replaced by `/api/lint/*`). Rewrote validation-api.spec.ts to verify the validation lifecycle through the lint API surface instead of calling non-existent endpoints.

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/04-validation/lint-api.spec.ts` — consolidated 4 test() into 1; added full LintResultsResponse/LintStatusResponse/LintDiffResponse shape assertions
- `e2e/tests/04-validation/validation-api.spec.ts` — rewrote to test validation lifecycle via lint surface (original endpoints removed)
- `e2e/tests/06-settings/misc-endpoints.spec.ts` — consolidated 5 test() into 1; added PostHog config model assertions, icon context map assertions
