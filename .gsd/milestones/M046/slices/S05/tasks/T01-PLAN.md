---
estimated_steps: 50
estimated_files: 3
skills_used: []
---

# T01: Fix calendar namespace references and setup wizard test skips

## Description

Three stale bare-global references from the M044/S03 namespace migration cause all calendar E2E tests to fail. The setup wizard tests fail on non-fresh Docker stacks by design but should skip gracefully instead of reporting failures.

**Calendar bugs (2 files, 8 replacements):**
- `calendar_view.html` inline boot script calls bare `initCalendar()` — function only exists at `window.SemPKM.initCalendar`. FullCalendar never boots, `.fc` container never created.
- `calendar.js` line 172 checks bare `openTab` — undefined after M044 shim removal. Event clicks silently no-op.
- `calendar.js` lines 47/52/99/103 check bare `showToast` — undefined. Toast notifications silently disabled.
- `calendar.js` lines 1-8 JSDoc says `window.initCalendar` — stale, should reference `window.SemPKM.initCalendar`.

**Setup wizard (1 file):**
- Tests 1-5 require `setup_complete=false` which only exists on fresh stacks. Add a check against `/api/auth/status` and `test.skip()` when `setup_complete=true`.
- Tests 6-7 always pass on any stack — leave unchanged.

## Steps

1. Edit `backend/app/templates/browser/calendar_view.html`:
   - Line 20: `typeof initCalendar === 'function'` → `typeof SemPKM !== 'undefined' && typeof SemPKM.initCalendar === 'function'`
   - Line 21: `initCalendar('calendar-container', dataUrl)` → `SemPKM.initCalendar('calendar-container', dataUrl)`
   - Line 24: `typeof initCalendar === 'function'` → `typeof SemPKM !== 'undefined' && typeof SemPKM.initCalendar === 'function'`
   (Note: line 24 already has a fallback `s.onload` callback — update the check there too)

2. Edit `frontend/static/js/calendar.js`:
   - Line 172: `typeof openTab === 'function'` → `typeof SemPKM !== 'undefined' && typeof SemPKM.openTab === 'function'`, and `openTab(iri, title)` → `SemPKM.openTab(iri, title)`
   - Lines 47, 52, 99, 103: `typeof showToast === 'function'` → `typeof SemPKM !== 'undefined' && typeof SemPKM.showToast === 'function'`, and `showToast(...)` → `SemPKM.showToast(...)`
   - Lines 1-8: Update JSDoc to reference `window.SemPKM.initCalendar` instead of `window.initCalendar`

3. Edit `e2e/tests/00-setup/01-setup-wizard.spec.ts`:
   - Add a helper function at the top of the describe block that fetches `/api/auth/status` and returns `setup_complete`
   - For tests 1-5 (the ones requiring fresh stack), add `test.skip()` logic: before each test body, check if `setup_complete === true` and skip with a message like `'Setup already completed — requires fresh stack'`
   - Keep tests 6 and 7 untouched
   - Remove or update the old header comment that says 'DO NOT skip or tag these tests'

4. Verify no bare calendar globals remain:
   - `rg 'typeof initCalendar|typeof openTab|typeof showToast' frontend/static/js/calendar.js backend/app/templates/browser/calendar_view.html` must return 0 results
   - `rg 'SemPKM\.initCalendar|SemPKM\.openTab|SemPKM\.showToast' frontend/static/js/calendar.js backend/app/templates/browser/calendar_view.html` must return results for all replacements

## Must-Haves

- [ ] `calendar_view.html` boot script calls `SemPKM.initCalendar` (2 occurrences)
- [ ] `calendar.js` eventClick uses `SemPKM.openTab` (1 occurrence)
- [ ] `calendar.js` toast calls use `SemPKM.showToast` (4 occurrences)
- [ ] `calendar.js` JSDoc updated to reflect `SemPKM.initCalendar`
- [ ] Setup wizard tests 1-5 skip when `setup_complete=true`
- [ ] Setup wizard tests 6-7 always run
- [ ] Zero bare `initCalendar`/`openTab`/`showToast` references in calendar files

## Verification

- `rg 'typeof initCalendar[^.]|typeof openTab[^.]|typeof showToast[^.]' frontend/static/js/calendar.js backend/app/templates/browser/calendar_view.html | wc -l` returns 0
- `rg 'SemPKM\.initCalendar' backend/app/templates/browser/calendar_view.html | wc -l` returns 2
- `rg 'SemPKM\.openTab' frontend/static/js/calendar.js | wc -l` returns at least 1
- `rg 'SemPKM\.showToast' frontend/static/js/calendar.js | wc -l` returns at least 4
- `rg 'test\.skip' e2e/tests/00-setup/01-setup-wizard.spec.ts | wc -l` returns at least 1

## Inputs

- `backend/app/templates/browser/calendar_view.html` — template with stale `initCalendar` calls
- `frontend/static/js/calendar.js` — calendar module with stale `openTab`/`showToast` references
- `e2e/tests/00-setup/01-setup-wizard.spec.ts` — setup wizard test file needing skip logic

## Expected Output

- `backend/app/templates/browser/calendar_view.html` — fixed namespace references
- `frontend/static/js/calendar.js` — fixed namespace references and JSDoc
- `e2e/tests/00-setup/01-setup-wizard.spec.ts` — conditional skip logic added

## Inputs

- `backend/app/templates/browser/calendar_view.html`
- `frontend/static/js/calendar.js`
- `e2e/tests/00-setup/01-setup-wizard.spec.ts`

## Expected Output

- `backend/app/templates/browser/calendar_view.html`
- `frontend/static/js/calendar.js`
- `e2e/tests/00-setup/01-setup-wizard.spec.ts`

## Verification

rg 'typeof initCalendar[^.]|typeof openTab[^.]|typeof showToast[^.]' frontend/static/js/calendar.js backend/app/templates/browser/calendar_view.html | wc -l returns 0 && rg 'SemPKM\.initCalendar' backend/app/templates/browser/calendar_view.html | wc -l returns 2 && rg 'test\.skip' e2e/tests/00-setup/01-setup-wizard.spec.ts | wc -l returns >= 1
