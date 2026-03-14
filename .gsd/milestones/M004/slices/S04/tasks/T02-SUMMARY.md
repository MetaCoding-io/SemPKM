---
id: T02
parent: S04
milestone: M004
provides:
  - E2E regression test proving showTypePicker tab preservation
  - E2E test verifying __new-object temp panel lifecycle (creation, prefix, cleanup)
key_files:
  - e2e/tests/12-bug-fixes/new-object-tab.spec.ts
key_decisions:
  - Split into two tests: tab preservation (critical) and temp panel lifecycle (supplementary) rather than a single end-to-end create flow, because the SHACL-generated form makes full-flow E2E brittle
patterns_established:
  - Use page.evaluate to call window.showTypePicker() and window.openTab() directly in E2E tests
  - Assert dockview panel IDs via page.evaluate accessing window._dockview.api.panels
observability_surfaces:
  - Playwright test failure messages clearly identify which assertion failed (tab count, tab label presence, panel prefix)
duration: 15m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Add E2E test for new-object tab preservation

**Added Playwright E2E spec with 2 tests proving tab preservation and temp panel lifecycle for the showTypePicker fix.**

## What Happened

Created `e2e/tests/12-bug-fixes/new-object-tab.spec.ts` with two tests:

1. **"showTypePicker opens fresh tab without destroying existing tab"** — Opens a seed object tab, calls `showTypePicker()`, asserts the original tab still exists, a "New Object" tab appeared, and at least 2 tabs exist. This is the critical regression guard.

2. **"temp panel uses __new-object prefix and is trackable"** — Verifies the temp panel has the `__new-object-` prefix in dockview's panel list, can be closed programmatically via `closeTab()`, and that the original tab survives cleanup. This validates the contract that `objectCreated` handler depends on.

The original plan suggested a stretch test that completes the full create flow (click type card → fill form → submit → verify cleanup). This was attempted but the SHACL-generated form has dynamic field names (based on property paths like `dcterms:title`) making generic selectors fragile. Instead, test 2 validates the cleanup mechanism directly by calling `closeTab()` on the temp panel — the same code path used by the `objectCreated` handler.

## Verification

```
cd e2e && npx playwright test tests/12-bug-fixes/new-object-tab.spec.ts
```

All 4 tests pass (2 tests × 2 browsers):
- ✓ chromium: showTypePicker opens fresh tab without destroying existing tab (1.6s)
- ✓ chromium: temp panel uses __new-object prefix and is trackable (1.2s)
- ✓ firefox: showTypePicker opens fresh tab without destroying existing tab (2.1s)
- ✓ firefox: temp panel uses __new-object prefix and is trackable (1.7s)

Slice-level verification: `cd e2e && npx playwright test tests/12-bug-fixes/new-object-tab.spec.ts` — **PASS**

## Diagnostics

Run the E2E test; failure messages clearly state which assertion failed:
- Tab count assertion shows expected vs actual count
- Tab label assertions show which tab title was missing
- Panel prefix assertions confirm `__new-object-` convention

## Deviations

Replaced the stretch "full create flow" test with a "temp panel lifecycle" test that validates the same cleanup contract without depending on SHACL-generated form field selectors. This is more robust and tests the actual mechanism rather than a specific form layout.

## Known Issues

None

## Files Created/Modified

- `e2e/tests/12-bug-fixes/new-object-tab.spec.ts` — new E2E regression test (2 tests, 4 runs across chromium + firefox)
- `.gsd/milestones/M004/slices/S04/S04-PLAN.md` — marked T02 as complete
