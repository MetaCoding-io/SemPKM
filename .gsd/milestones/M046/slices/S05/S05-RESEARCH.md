# S05 Research: Calendar, Recurring Tasks & Setup Wizard Fixes

## Summary

Three test files fail due to two distinct root causes: (1) stale bare-global function references in `calendar_view.html` and `calendar.js` left behind by M044's namespace migration, and (2) setup wizard tests that inherently require a fresh Docker stack. The calendar issues are straightforward namespace fixes. The setup wizard tests need conditional skip logic.

## Root Cause Analysis

### Calendar Tests — `initCalendar` and `openTab` namespace breakage

After M044/S03, all window globals were migrated to `window.SemPKM.*`. The calendar module was partially migrated — `calendar.js` exports to `window.SemPKM.initCalendar` (line 301) and references `SemPKM.debug`, `window.SemPKM.__calendarDragPayload`, `window.SemPKM.registerCleanup`, `window.SemPKM.showCreateFormForType` correctly. But three references were missed:

**Bug 1 — Template can't boot FullCalendar:**
`calendar_view.html` lines 20/24 call bare `initCalendar()`. After calendar.js loads, the function exists only at `window.SemPKM.initCalendar`. The template's boot check `typeof initCalendar === 'function'` evaluates to `false`, so the FullCalendar instance is never created. The `#calendar-container` div renders empty.

Impact: ALL calendar view tests fail at `waitForSelector('.fc', ...)` — the `.fc` container is never created.

Affected tests:
- `02-views/calendar-view.spec.ts` — all 3 tests
- `02-views/recurring-tasks.spec.ts` — both tests  
- `02-views/cross-view-drag.spec.ts` — test 2 ("external drop on calendar")

**Bug 2 — Event click handler is dead:**
`calendar.js` line 172 checks `typeof openTab === 'function'` — bare `openTab` is undefined (shim removed in M044/S03 T03). The eventClick callback silently no-ops. Even if Bug 1 is fixed and the calendar renders, clicking events won't open object tabs.

Impact: `recurring-tasks.spec.ts` "clicking virtual event opens master task" would still fail.

**Bug 3 — Toast notifications silently disabled:**
`calendar.js` lines 47, 52, 99, 103 check `typeof showToast === 'function'` — bare `showToast` is undefined. These are non-critical (UX only, no test failures), but should be fixed for correctness.

### Setup Wizard Tests — Infrastructure constraint, not a code bug

`01-setup-wizard.spec.ts` has 7 tests. 5 of them require `setup_mode=true` and `setup_complete=false` — conditions that only exist on a fresh Docker stack (first boot, before the wizard has run). After the wizard runs once, these conditions are permanently changed.

The auth status check in `auth.js` redirects from `/setup.html` to `/login.html` when `setup_complete=true`, so tests 3-5 can't even reach the form.

Tests that fail on non-fresh stack (5):
1. `fresh instance reports setup_mode=true` — setup_complete is already true
2. `navigating to root redirects to setup page` — redirects to login instead
3. `setup page shows the setup form` — redirected to login.html
4. `submitting invalid token shows error` — redirected to login.html
5. `submitting valid token completes setup` — redirected to login.html

Tests that pass on non-fresh stack (2):
6. `after setup, auth status reports setup_complete=true` — always true
7. `second setup attempt returns error` — returns 400 as expected

**Fix approach:** Add a `test.beforeEach` or per-test check that queries `/api/auth/status`. If `setup_complete=true`, skip the test with `test.skip()`. This way:
- On a fresh stack: all 7 run and pass
- On a non-fresh stack: 5 skip, 2 pass
- The full suite reports 0 failures from this file

## Implementation Landscape

### Files to Modify

| File | What Changes | Why |
|------|-------------|-----|
| `backend/app/templates/browser/calendar_view.html` | Change `initCalendar` → `SemPKM.initCalendar` in the inline boot script (2 occurrences, lines 20 and 24) | Fix Bug 1 — calendar never boots |
| `frontend/static/js/calendar.js` | Line 172: `openTab(iri, title)` → `SemPKM.openTab(iri, title)` and guard check; Lines 47/52/99/103: `showToast(...)` → `SemPKM.showToast(...)` and guard checks; Line 6: update stale JSDoc | Fix Bugs 2 and 3 |
| `e2e/tests/00-setup/01-setup-wizard.spec.ts` | Add conditional skip for tests 1-5 based on `/api/auth/status` response | Make tests pass on non-fresh stacks |

### Files Not Modified (confirmed working)

- `frontend/static/js/auth.js` — `initSetupWizard()` is a true global, not namespaced. Works correctly.
- `frontend/static/setup.html` — calls `initSetupWizard()` which is a global. Works correctly.
- `backend/app/views/service.py` — `execute_calendar_query()`, `_expand_rrule()`, `execute_merged_calendar_query()` all work correctly. RRULE expansion, virtual event generation, and `masterIri`/`isVirtual` extendedProps are properly set.
- `backend/app/views/router.py` — calendar data endpoint and merged mode work correctly.
- `e2e/helpers/dockview.ts` — `openGenericViewTab()` correctly calls `window.SemPKM.openGenericViewTab()`.
- `frontend/static/js/api-fetch.js` — `window.apiFetch` backward-compat shim still exists. Used by auth.js and calendar.js.
- `e2e/tests/02-views/cross-view-drag.spec.ts` — test 2 has CDN-fallback logic, will pass once calendar boots.

### FullCalendar Loading Chain (verified working)

1. Docker build runs `node build.js` → hashes `node_modules/fullcalendar/index.global.min.js` → writes to `/build-assets/` with `manifest.json`
2. Frontend entrypoint copies build assets to `/srv/built-assets/` shared volume
3. API container reads `manifest.json` from `/app/frontend_assets/` (shared volume)
4. `asset_url('fullcalendar.js')` resolves to `/assets/<hash>.min.js`
5. Template sets `data-fullcalendar-src` attribute with the resolved URL
6. `calendar.js` reads the attribute and uses it as the CDN URL
7. When `SemPKM.initCalendar(containerId, dataUrl)` is called, it checks `typeof FullCalendar !== 'undefined'`, and if not loaded, creates a `<script>` tag with the CDN URL

The chain works — the only break is at step "when called" because the template can't call the function.

## Recommendation

### Task Decomposition

**T01: Fix calendar namespace references (primary fix)**
- Fix `calendar_view.html` inline script: `initCalendar` → `SemPKM.initCalendar` (2 occurrences)
- Fix `calendar.js` eventClick: `openTab` → `SemPKM.openTab` (line 172)  
- Fix `calendar.js` toast calls: `showToast` → `SemPKM.showToast` (4 occurrences)
- Update stale JSDoc comment (line 6)
- Verify: `rg 'typeof openTab|typeof initCalendar|typeof showToast' frontend/ backend/app/templates/ --include='*.js' --include='*.html'` should return 0 results for bare references in calendar files

**T02: Fix setup wizard test conditional skipping**
- Add `/api/auth/status` check in `test.beforeEach` or use `test.skip()` per-test
- Tests 1-5 skip when `setup_complete=true`
- Tests 6-7 always run
- Verify: the test file reports 0 failures on both fresh and non-fresh stacks

**T03: Run failing test files and verify all pass**
- Run `npx playwright test e2e/tests/02-views/calendar-view.spec.ts` 
- Run `npx playwright test e2e/tests/02-views/recurring-tasks.spec.ts`
- Run `npx playwright test e2e/tests/02-views/cross-view-drag.spec.ts`
- Run `npx playwright test e2e/tests/00-setup/01-setup-wizard.spec.ts`
- All should pass (or skip cleanly for setup wizard)

### Risk Assessment

**Low risk.** Both fixes are surgical:
- Calendar fix is 6 string replacements in 2 files with no behavioral change — just correcting function references
- Setup wizard fix adds skip logic without changing any test assertions

### Out-of-Scope (noted for S06)

Other templates with the same bare `openTab` bug:
- `backend/app/templates/browser/timeline_view.html` line 105
- `backend/app/templates/browser/map_view.html` line 82
- `backend/app/templates/browser/template_picker.html` line 39

These affect timeline, map, and template picker tests respectively. They follow the exact same pattern and fix, but belong to different test files. S06 (miscellaneous failures) should pick these up.
