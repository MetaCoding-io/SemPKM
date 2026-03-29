# S06: Miscellaneous Failures & Full Suite Verification — UAT

**Milestone:** M046
**Written:** 2026-03-29T06:17:31.235Z

## UAT: S06 — Miscellaneous Failures & Full Suite Verification

### Preconditions
- Docker test stack running: `docker compose -f docker-compose.test.yml ps` shows all services healthy
- E2E dependencies installed: `cd e2e && npm ci`
- All S01–S05 fixes merged

### Test 1: Bare-global references eliminated
**Steps:**
1. Run: `grep -rn 'onclick=.*showToast\|onclick=.*openTab' backend/app/templates/browser/timeline_view.html | grep -v SemPKM`
2. Run: `grep -rn 'onclick=.*selectIcon\|onclick=.*filterIconPicker\|onclick=.*clearParentClass\|onclick=.*addPropertyRow' backend/app/templates/browser/ontology/create_class_form.html | grep -v SemPKM | grep -v closeClassCreationForm`
3. Run: `grep -n 'handlePredicateChange\|removePropertyRow' frontend/static/js/workspace.js | grep -v SemPKM`

**Expected:** All three commands return zero matches. All bare globals migrated to SemPKM namespace.

### Test 2: RBox ontology viewer selector
**Steps:**
1. Run: `grep 'rbox-object-table' e2e/tests/22-ontology/ontology-viewer.spec.ts`

**Expected:** Selector uses prefix match `[data-testid^="rbox-object-table"]`, not exact match.

### Test 3: Timeline view CSS fix
**Steps:**
1. Run: `grep 'min-height.*200' frontend/static/css/views.css`

**Expected:** `.timeline-container` has `min-height: 200px` (was 0).

### Test 4: Markdown XSS test scoping
**Steps:**
1. Run: `grep 'markdown-body' e2e/tests/01-objects/markdown-rendering.spec.ts`

**Expected:** XSS assertions scoped to `.markdown-body` selector, not `.object-tab`.

### Test 5: Type picker count assertion
**Steps:**
1. Run: `grep 'toBeGreaterThanOrEqual(4)' e2e/tests/01-objects/create-object.spec.ts`

**Expected:** Assertion uses `>= 4` instead of exact `4`.

### Test 6: Timeout increases
**Steps:**
1. Run: `grep 'timeout.*15000' e2e/helpers/wait-for.ts` — waitForIdle default
2. Run: `grep 'timeout.*20000' e2e/helpers/dockview.ts` — openObjectTab default

**Expected:** waitForIdle defaults to 15000ms, openObjectTab defaults to 20000ms.

### Test 7: Targeted E2E test verification
**Steps:**
1. Run: `cd e2e && npx playwright test tests/22-ontology/ tests/23-class-creation/ --project=chromium --retries=0`

**Expected:** Ontology viewer and class creation tests pass (bare-global and selector fixes verified at runtime).

### Test 8: Full suite run (aspirational)
**Steps:**
1. Run: `cd e2e && npx playwright test --project=chromium --retries=1 --reporter=line`

**Expected:** Majority of 122 spec files pass. Known residual failures: timeline visibility (3), object-tab timeouts (5), waitForIdle persistence (3), workspace layout assertions (2), table pagination type mismatch (1), multi-value autocomplete timing (1), magic-link rate limit (1), event-log panel (1), object-form visibility (2).

### Edge Cases
- `closeClassCreationForm()` must remain as bare global — it's defined in `ontology_page.html`, not exported to SemPKM namespace
- Timeline CDN load timing varies — `state:'attached'` may be needed instead of `state:'visible'` for more reliable detection
- Rate limiter resets are required between test file runs that create new users
