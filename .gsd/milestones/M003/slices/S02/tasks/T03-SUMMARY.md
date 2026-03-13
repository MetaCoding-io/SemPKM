---
id: T03
parent: S02
milestone: M003
provides:
  - Updated E2E test verifying hierarchy mode shows real empty state (not placeholder)
  - All 5 explorer-mode E2E tests pass with hierarchy-aware assertions
key_files:
  - e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts
key_decisions:
  - E2E hierarchy test checks for either hierarchy-node elements OR .tree-empty element, since seed data has no dcterms:isPartOf triples — empty state is expected
  - Also updated the "lazy expansion after round-trip" test that switches through hierarchy, replacing placeholder assertion with hierarchy content/empty-state assertion
patterns_established:
  - Hierarchy empty state selector pattern: `.tree-empty` with case-insensitive text check for "hierarchy"
observability_surfaces:
  - E2E test names map directly to mode behaviors; Playwright traces/screenshots in e2e/test-results/ on failure
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: E2E tests and final integration verification

**Updated E2E hierarchy test from placeholder expectation to real empty-state/nodes verification; all 5 explorer-mode tests pass.**

## What Happened

Updated `explorer-mode-switching.spec.ts` to replace the "switching to hierarchy shows placeholder" test with a test that verifies real hierarchy mode behavior:

1. Renamed test to "switching to hierarchy shows empty state or hierarchy nodes"
2. After switching to hierarchy mode, the test verifies:
   - `[data-testid="explorer-placeholder"]` is NOT present (placeholder is gone)
   - Either `[data-testid="hierarchy-node"]` elements OR `.tree-empty` element is visible
   - If empty state is shown, its text contains "hierarchy" (case-insensitive)
   - Nav sections from by-type mode are NOT present
3. Updated the "lazy expansion works after mode round-trip" test which also switches through hierarchy — replaced `expect(placeholder).toBeVisible()` with an assertion that hierarchy content or empty state is visible
4. Updated the file header comment to match the new test title

The multi-select test (test 5) switches to hierarchy mode but only checks that the selection badge clears — it worked without changes since hierarchy now returns real content instead of a placeholder.

## Verification

- `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — **5/5 passed** (11.8s)
- `cd backend && .venv/bin/python -m pytest tests/test_explorer_modes.py tests/test_hierarchy_explorer.py -v` — **24/24 passed** (0.50s)
- Test stack started fresh with `docker compose -f docker-compose.test.yml down -v && up -d --build` to ensure clean state

### Slice-level verification status (final task — all must pass):
- ✅ `cd backend && python -m pytest tests/test_explorer_modes.py tests/test_hierarchy_explorer.py -v` — 24/24 pass
- ✅ `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — 5/5 pass
- ✅ `GET /browser/explorer/tree?mode=hierarchy` — returns tree HTML (empty state message in test env, confirmed by E2E)
- ✅ `GET /browser/explorer/children?parent={iri}` — endpoint wired, confirmed by unit tests (no isPartOf data in seed)
- ✅ EXP-03 requirement verified: hierarchy mode functional with SPARQL queries, lazy expansion via htmx click-once, recursive template depth, empty state for no isPartOf data

## Diagnostics

- `npx playwright test tests/19-explorer-modes/ --reporter=list` — test names map to mode behaviors
- Playwright captures trace/screenshot on failure in `e2e/test-results/`
- Backend unit tests: `python -m pytest tests/test_hierarchy_explorer.py -v` — test names map to specific SPARQL structure checks

## Deviations

Also updated the "lazy expansion works after mode round-trip" test (test 4) which had `await expect(placeholder).toBeVisible()` when switching to hierarchy — replaced with hierarchy content/empty-state assertion. This wasn't explicitly called out in the plan but was required since hierarchy no longer shows a placeholder.

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — Updated hierarchy test to verify real behavior (empty state or hierarchy nodes) instead of placeholder; updated round-trip test hierarchy assertion; updated header comment
