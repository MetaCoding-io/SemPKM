---
id: T04
parent: S01
milestone: M003
provides:
  - 5 E2E tests covering explorer mode dropdown, mode switching, placeholder rendering, round-trip lazy expansion, and multi-select clearing
  - Explorer mode selectors in selectors.ts (modeSelect, treeBody, placeholder)
  - Regression fix for section collapse/expand test broken by T02 dropdown addition
key_files:
  - e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts
  - e2e/helpers/selectors.ts
  - e2e/tests/03-navigation/nav-tree.spec.ts
key_decisions:
  - "Consolidated 7 tests into 5 to stay within the auth magic-link rate limit (5/minute) — combined 'dropdown options + by-type default' and 'by-tag placeholder + switch-back restore' into single tests"
  - "Fixed nav-tree collapse/expand test to click .explorer-section-chevron instead of .explorer-section-header — the header now contains the mode dropdown which has event.stopPropagation"
patterns_established:
  - "E2E test suites should stay at ≤5 tests per file to avoid hitting the auth magic-link 5/minute rate limit (pre-existing infra constraint)"
observability_surfaces:
  - "E2E test output directly maps test names to EXP-01/EXP-02 requirements — Playwright list reporter shows pass/fail per case"
duration: 30m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T04: E2E tests and final verification

**Implemented 5 E2E tests verifying explorer mode dropdown, mode switching, and by-type default behavior. Fixed a regression in the nav-tree collapse test caused by T02's dropdown addition. All slice verification checks pass.**

## What Happened

1. **Explorer selectors already in `selectors.ts`** — previous attempt had added `explorer.modeSelect`, `explorer.treeBody`, and `explorer.placeholder`. Confirmed correct.

2. **Restructured E2E tests from 7 to 5** — the previous attempt's 7 tests hit the auth magic-link rate limit (5/minute, enforced by slowapi). Consolidated related assertions into combined tests:
   - "dropdown visible with three mode options and by-type default shows nav sections"
   - "switching to hierarchy shows placeholder"
   - "switching to by-tag shows placeholder and switching back restores real tree"
   - "lazy expansion works after mode round-trip"
   - "multi-select clears on mode switch"

3. **Fixed regression in nav-tree.spec.ts** — T02 added the mode `<select>` inside `.explorer-section-header`. The "section collapse/expand toggle" test clicked the header center, which now lands on the dropdown (which has `event.stopPropagation()`). Changed the click target from `.explorer-section-header` to `.explorer-section-chevron`.

4. **Verified no regressions** — `nav-tree.spec.ts` (5/5 pass), `create-object.spec.ts` first 5 pass (remaining fail due to pre-existing rate limit), `crossfade-and-misc.spec.ts` (5/5 pass).

5. **Manual browser verification** on dev stack (localhost:3000):
   - Fresh page load shows by-type tree with dropdown showing "By Type"
   - Switching to hierarchy shows placeholder with "Hierarchy mode — coming soon"
   - Switching back to by-type restores real tree
   - `refreshNavTree()` from console works in both by-type and placeholder modes
   - All curl-based slice verification checks pass (by-type → 200, hierarchy → 200, invalid → 400)

## Verification

| Check | Result |
|-------|--------|
| `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` | **5/5 PASS** |
| `cd e2e && npx playwright test tests/03-navigation/nav-tree.spec.ts --reporter=list --project=chromium` | **5/5 PASS** |
| `cd e2e && npx playwright test tests/13-v24-coverage/crossfade-and-misc.spec.ts --reporter=list --project=chromium` | **5/5 PASS** |
| `cd backend && python -m pytest tests/test_explorer_modes.py -v` | **8/8 PASS** |
| `curl .../browser/explorer/tree?mode=by-type` → 200 | **PASS** |
| `curl .../browser/explorer/tree?mode=hierarchy` → 200 | **PASS** |
| `curl .../browser/explorer/tree?mode=invalid` → 400 | **PASS** |
| Browser: dropdown visible, by-type default, mode switching works | **PASS** |
| Browser: `refreshNavTree()` respects current mode | **PASS** |
| EXP-01: dropdown switches between modes with htmx re-render | **VERIFIED** |
| EXP-02: by-type is default, behavior identical to pre-refactor | **VERIFIED** |

## Diagnostics

- E2E test output: `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list` shows pass/fail per test
- Test names map to requirements: "dropdown visible..." → EXP-01, "by-type mode shows nav sections..." → EXP-02
- On failure: Playwright captures screenshots and traces in `e2e/test-results/`

## Deviations

- Reduced from 7 to 5 E2E tests to work around the 5/minute auth rate limit — all planned assertions are still covered via test consolidation
- Fixed a pre-existing-potential regression in `03-navigation/nav-tree.spec.ts` (collapse/expand test) that was caused by T02's dropdown addition to the section header

## Known Issues

- Auth magic-link rate limit (5/minute) is a pre-existing infrastructure constraint that prevents running >5 tests per spec file in a single run. Tests beyond the 5th in any file fail with "Magic link request did not return a token". This affects `01-objects/create-object.spec.ts` (8 tests, only first 5 pass) and the entire `03-navigation/` directory when run as a suite (22+ tests across files). Not introduced by this slice.

## Files Created/Modified

- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — 5 E2E tests for explorer mode switching (restructured from 7)
- `e2e/helpers/selectors.ts` — added `explorer` section with modeSelect, treeBody, placeholder selectors
- `e2e/tests/03-navigation/nav-tree.spec.ts` — fixed collapse/expand test to click chevron instead of header
