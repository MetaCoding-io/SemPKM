---
id: T02
parent: S10
milestone: M003
provides:
  - e2e tests for event undo (compensating events) via API
  - e2e tests for event detail endpoint (create and patch diff HTML)
  - e2e test for event log UI panel with Diff button expansion
key_files:
  - e2e/tests/06-settings/event-undo.spec.ts
key_decisions:
  - Consolidated multiple test cases into fewer Playwright tests (3 instead of 6) to stay within the 5/minute magic-link rate limit imposed by auth rate limiting
  - Used ownerPage.evaluate() to call toggleBottomPanel() directly instead of Alt+j keyboard shortcut, which was unreliable in headless Chromium (the keydown handler was registered but Alt+j didn't trigger it on first page load)
patterns_established:
  - For bottom panel interaction in e2e tests, call window.toggleBottomPanel() via evaluate() rather than simulating Alt+j keyboard shortcut — more reliable in headless browsers
  - Combine related API assertions into a single test case to reduce magic-link auth calls and avoid rate limiting
observability_surfaces:
  - none (test-only, no production code)
duration: 20m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Event undo & event log detail tests

**Added e2e tests for event undo round-trip, event detail HTML diff endpoints, and event log UI panel interaction — all 3 tests passing.**

## What Happened

The test file `event-undo.spec.ts` already existed with a prior implementation. It had 6 separate tests — 2 API undo tests, 3 API detail tests, and 1 UI test. Two issues were fixed:

1. **Rate limiting**: 6 tests each required a separate magic-link auth call, exceeding the 5/minute rate limit and causing the last test to fail on auth. Consolidated into 3 tests (one per describe block) that cover the same assertions within fewer auth sessions.

2. **Flaky UI test**: The Alt+j keyboard shortcut to open the bottom panel was unreliable in headless Chromium — the keydown handler was registered but the shortcut didn't trigger `toggleBottomPanel()` on first page load. Replaced with direct `evaluate(() => window.toggleBottomPanel())` call. Also added `force: true` on the EVENT LOG tab click and proper waits for panel height transition.

The 3 tests now cover:
- **Event Undo API**: Create object → verify exists → undo event → verify object reverted + 404 for nonexistent event
- **Event Detail API**: object.create detail shows diff panel with created triples + 404 shows error HTML + object.patch detail shows before/after diff table
- **Event Log UI**: Open bottom panel → click EVENT LOG tab → verify event rows load → click Diff button → verify diff panel expands with close button

## Verification

```
cd e2e && npx playwright test tests/06-settings/event-undo.spec.ts --project=chromium
# 3 passed (3.9s) — run twice to confirm no flakiness
```

Slice-level checks (partial — T02 is second of 12 tasks):
- `rg "test.skip(" e2e/tests/ -c -g '*.ts' | awk -F: '{sum+=$2} END{print sum}'` → 17 remaining stubs (expected, other tasks will address these)

## Diagnostics

None — test-only task with no production code changes.

## Deviations

- Consolidated from 6 tests to 3 to avoid auth rate limiting (was not anticipated in the plan)
- Replaced Alt+j keyboard shortcut with direct JS function call for panel opening (reliability improvement)

## Known Issues

Rate limiting can cause auth fixture failures when many tests run in rapid succession within the same minute. Restarting the API container clears the in-memory rate limiter state. This is a known test infrastructure issue, not a test bug. (Same issue noted in T01.)

## Files Created/Modified

- `e2e/tests/06-settings/event-undo.spec.ts` — rewrote with 3 consolidated tests covering event undo API, event detail API (create/patch/404), and event log UI panel interaction
