# S07: Integration Verification — UAT Script

## Preconditions

- Docker test stack running (`docker compose -f docker-compose.test.yml up -d`)
- `media-scheduler` model archive present at `models/media-scheduler/`
- `media-scheduler` app present at `apps/media-scheduler/`
- E2E test environment configured (`e2e/.env` with `BASE_URL=http://localhost:3901`)
- Node.js + Playwright installed (`cd e2e && npm install`)

---

## Test Case 1: Spec File Structure

**Goal:** Verify the E2E spec exists, compiles, and has adequate coverage.

1. Run `test -f e2e/tests/55-media-scheduler/media-scheduler.spec.ts`
   - **Expected:** Exit code 0 — file exists
2. Run `grep -c 'mediaScheduler' e2e/helpers/selectors.ts`
   - **Expected:** ≥ 1 — selectors registered
3. Run `cd e2e && npx tsc --noEmit 2>&1 | grep '55-media-scheduler\|selectors.ts'`
   - **Expected:** No output — zero compilation errors in our files
4. Run `grep -c 'Phase' e2e/tests/55-media-scheduler/media-scheduler.spec.ts`
   - **Expected:** ≥ 10 — sufficient lifecycle phases covered

---

## Test Case 2: Full Lifecycle E2E Execution

**Goal:** Prove the Media Scheduler app works end-to-end against Docker.

1. Ensure Docker test stack is healthy: `curl -s http://localhost:3901/api/auth/status | jq .`
   - **Expected:** JSON response with `setup_complete: true`
2. Run `cd e2e && npx playwright test tests/55-media-scheduler/media-scheduler.spec.ts --reporter=list`
   - **Expected:** Test passes (1 passed) or fails with actionable phase-specific error
3. Verify Phase 0 (cleanup) is idempotent — run the test twice in succession
   - **Expected:** Second run succeeds — cleanup handles "already absent" state gracefully
4. Check console output for Phase 8 conditional skip message
   - **Expected:** Either status tracking actions pass OR "Phase 8: No plan entries — skipping status tracking test" appears

---

## Test Case 3: Selector Accuracy

**Goal:** Verify selectors match real DOM elements.

1. Navigate to `http://localhost:3901/app/media-scheduler/` (after model+app install)
2. Open browser DevTools, run: `document.querySelector('#ms-container')`
   - **Expected:** Returns the main app container element
3. Run: `document.querySelector('#ms-sidebar')`
   - **Expected:** Returns the sidebar element with source list
4. Run: `document.querySelectorAll('.ms-tab').length`
   - **Expected:** 4 (Today, Episodes, Rules, Stats)
5. Click Rules tab, then Add Rule button, verify: `document.querySelector('#ms-rule-form-area form')`
   - **Expected:** Returns the rule creation form element
6. Click Stats tab, verify: `document.querySelector('#ms-chart-hours')`
   - **Expected:** Returns the hours-per-category chart canvas

---

## Test Case 4: Podcast Subscription CRUD

**Goal:** Verify podcast source creation through the UI.

1. Click the + button (`#ms-toggle-add-form`) in the sidebar
   - **Expected:** Add section (`#ms-add-section`) becomes visible
2. Fill feed URL field with `http://example.com/test-podcast.xml`, title with `Test Podcast`
3. Click Submit on the podcast form
   - **Expected:** Success message appears in `#ms-add-result`
4. Check sources list refreshes with new source item
   - **Expected:** At least one `.ms-source-item` element present in `#ms-sources-list`

---

## Test Case 5: Rule Creation and Display

**Goal:** Verify schedule rule CRUD.

1. Navigate to Rules tab (`.ms-tab[data-tab="rules"]`)
   - **Expected:** Rules view (`.ms-rules-view`) is visible
2. Click "Add Rule" button
   - **Expected:** Rule form appears in `#ms-rule-form-area`
3. Fill name "Commute Podcasts", select activity "commuting"
4. Submit the form
   - **Expected:** Rule card (`.ms-rule-card`) appears in `#ms-rules-list` with name "Commute Podcasts"

---

## Test Case 6: Plan Generation

**Goal:** Verify daily plan generation responds correctly.

1. Navigate to Today tab
   - **Expected:** Today view (`.ms-today-view`) is visible
2. Click "Generate Plan" button
   - **Expected:** Either plan entries (`.ms-plan-entry`) appear OR empty state (`.ms-today-empty`) is shown — both are valid when using a dummy podcast URL with no real episodes

---

## Test Case 7: Stats Dashboard

**Goal:** Verify stats view renders chart canvases.

1. Navigate to Stats tab
   - **Expected:** Stats view (`.ms-stats-view`) is visible
2. Check for three chart canvases:
   - `#ms-chart-hours` — hours per category
   - `#ms-chart-top-sources` — most played sources
   - `#ms-chart-weekly` — weekly trends
   - **Expected:** All three `<canvas>` elements are attached to the DOM

---

## Edge Cases

- **Idempotent cleanup:** Running the test against an environment where the app was never installed should not fail Phase 0
- **Empty plan state:** When no real podcast episodes exist, plan generation should return gracefully (empty state or zero-entry plan, not an error)
- **CDN chart loading:** Chart.js loads from CDN — canvas elements may be in DOM but not visually rendered. The test uses `toBeAttached()` which handles this correctly
- **Dialog handling:** Delete operations use `hx-confirm` — the test's dialog auto-accept handler must fire before the first delete action
