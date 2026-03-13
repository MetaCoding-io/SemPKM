---
estimated_steps: 4
estimated_files: 1
---

# T03: E2E tests and final integration verification

**Slice:** S02 — Hierarchy Explorer Mode
**Milestone:** M003

## Description

Update the existing E2E test that expected hierarchy placeholder content to verify real hierarchy mode behavior. With the default seed data (no `dcterms:isPartOf` triples), hierarchy mode should show a descriptive empty-state message — not the generic "coming soon" placeholder. Run all verification checks to confirm the slice is complete.

## Steps

1. **Update the "switching to hierarchy shows placeholder" E2E test.**
   In `explorer-mode-switching.spec.ts`, change the second test ("switching to hierarchy shows placeholder"):
   - Switch to hierarchy mode
   - Wait for content to load (htmx swap)
   - Verify the `[data-testid="explorer-placeholder"]` element is NOT present (placeholder is gone)
   - Verify the tree body contains either hierarchy nodes (`[data-testid="hierarchy-node"]`) OR an empty-state message containing "hierarchy" (case-insensitive)
   - Verify nav sections from by-type mode are NOT present
   - Update test title from "switching to hierarchy shows placeholder" to "switching to hierarchy shows empty state or hierarchy nodes"

2. **Verify other existing E2E tests still pass unchanged.**
   The remaining 4 tests should be unaffected:
   - "dropdown visible with three mode options..." — unchanged (hierarchy is still in the dropdown)
   - "switching to by-tag shows placeholder..." — unchanged (by-tag is still a placeholder)
   - "lazy expansion works after mode round-trip" — unchanged (tests by-type after round-trip)
   - "multi-select clears on mode switch" — may switch to hierarchy; verify it still works since hierarchy now shows real content instead of placeholder

3. **Run full verification suite.**
   - `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — all 5 pass
   - `cd backend && python -m pytest tests/test_explorer_modes.py tests/test_hierarchy_explorer.py -v` — all pass
   - Browser manual check: switch to hierarchy, see empty state message; switch back to by-type, tree restores

4. **Confirm EXP-03 requirement is met.**
   - EXP-03: "Explorer hierarchy mode shows objects nested by dcterms:isPartOf parent/child relationships with lazy-expanding arbitrary depth"
   - With seed data: empty state confirmed (no isPartOf data)
   - Backend implementation: SPARQL queries for roots and children confirmed working
   - Lazy expansion: children endpoint wired with htmx `click once` trigger
   - Arbitrary depth: recursive template pattern supports any nesting level

## Must-Haves

- [ ] E2E hierarchy test no longer expects placeholder content
- [ ] E2E hierarchy test verifies either hierarchy nodes or descriptive empty state
- [ ] All 5 E2E tests in the explorer-modes spec pass
- [ ] All backend unit tests pass (explorer_modes + hierarchy_explorer)
- [ ] No regressions in other E2E test files

## Verification

- `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — 5/5 pass
- `cd backend && python -m pytest tests/test_explorer_modes.py tests/test_hierarchy_explorer.py -v` — all pass
- Browser: hierarchy mode shows empty state with descriptive message (not "coming soon")
- Browser: switching between all three modes works correctly
- EXP-03 requirement status: verified at contract + integration level

## Observability Impact

- Signals added/changed: None (E2E tests are verification)
- How a future agent inspects this: `npx playwright test tests/19-explorer-modes/ --reporter=list` — test names map to mode behaviors; Playwright screenshots in `e2e/test-results/` on failure
- Failure state exposed: Playwright captures trace/screenshot on test failure for post-mortem

## Inputs

- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — current 5 tests, second test expects placeholder
- T01 output — hierarchy handler returns real content, templates use `data-testid="hierarchy-node"`
- T02 output — backend tests all pass

## Expected Output

- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — updated: hierarchy test verifies real behavior instead of placeholder; all 5 tests pass
