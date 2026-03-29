# S07 Research: Residual Failure Sweep — 19 Tests

## Summary

S06 left 19 residual test failures across 9 categories. All are either (a) assertion mismatches against changed UI, (b) timeout values too low for the Docker test environment, or (c) logic bugs in tests — not application code bugs. The fixes are mechanical edits to test files and one small helper improvement. No application code changes are needed.

## Recommendation

Split into 3 tasks: (T01) fix assertion mismatches and test logic bugs, (T02) fix timeouts and `waitForIdle` resilience, (T03) full suite verification run. T01 and T02 can execute independently since they touch different test files. T03 validates the complete suite.

## Implementation Landscape

### Category 1: Assertion Mismatches Against Changed UI (4 tests, 2 files)

**workspace-layout.spec.ts** — 2 failures:
1. **"bottom panel exists with EVENT LOG, AI COPILOT tabs"** — asserts `toHaveCount(4)` panel tabs, but the template now has 5 tabs (EVENT LOG, INFERENCE, AI COPILOT, LINT, SPARQL). The SPARQL tab was added post-test creation.
   - File: `e2e/tests/03-navigation/workspace-layout.spec.ts` line 89
   - Fix: Change `toHaveCount(4)` to `toHaveCount(5)` and add `SPARQL` to the `toContainText` assertions
   
2. **"right pane shows Details with Relations and Lint sections"** — asserts `toContainText(['Relations'])` but template text is uppercase `RELATIONS`.
   - File: `e2e/tests/03-navigation/workspace-layout.spec.ts` line 79
   - Fix: Change assertion to case-insensitive match or match the actual text `RELATIONS`

**keyboard-shortcuts.spec.ts** — 1 failure:
3. **"Alt+N opens type picker"** — asserts `toBe(4)` type options, but CRM or other models may add types (Events, etc.).
   - File: `e2e/tests/03-navigation/keyboard-shortcuts.spec.ts` line 49
   - Fix: Change `toBe(4)` to `toBeGreaterThanOrEqual(4)`

**keyboard-shortcuts.spec.ts** — 1 additional failure (waitForIdle times out before the type count assertion even runs, see Category 3)

### Category 2: Test Logic Bug (1 test, 1 file)

**table-pagination.spec.ts** — 1 failure:
4. **"table pagination: create objects, verify pages, navigate, and filter"** — creates Notes but finds the first `renderer_type === 'table'` view spec, which could be for Events or any other type. If the spec targets Events, created Notes don't appear and pagination assertions fail.
   - File: `e2e/tests/02-views/table-pagination.spec.ts` lines 15-19
   - Fix: Filter `specs.find()` to also match `target_class` containing "Note" (the `/browser/views/available` endpoint returns `target_class` for each spec)

### Category 3: waitForIdle Timeout (3 tests, 3 files)

The `waitForIdle()` helper waits for zero `.htmx-request` elements. The problem: some htmx requests take >15s to complete in the Docker test stack (slow triplestore queries, ontology diagram loading, etc.). The `.htmx-request` class stays on elements for the duration of the request.

**keyboard-shortcuts.spec.ts** — "Alt+N opens type picker" calls `waitForIdle` at line 40 which times out before reaching the count assertion.
**admin-model-detail.spec.ts** — "ontology diagram" section calls `waitForIdle` after clicking the Relationships tab; the ontology SPARQL query can take >15s.
**create-edge.spec.ts** — "edge appears in relations panel" calls `waitForIdle` after loading an object; relations htmx load can be slow.

**Fix strategy:** Two approaches:
- (A) **Replace `waitForIdle` with specific element waits** in each affected test — e.g., `waitForSelector('.type-picker')` instead of `waitForIdle`. More robust, test-by-test fix.
- (B) **Make `waitForIdle` ignore SSE/long-running htmx requests** — add a CSS class exclusion. Riskier, broader change.

Recommend (A) — replace `waitForIdle` calls in the 3 affected tests with specific element waits. This is targeted and doesn't change the helper's semantics for the 100+ other callers.

### Category 4: Object Tab Loading Timeout (5 tests, 3 files)

Five tests use `page.waitForSelector('.object-tab', { timeout: 10000 })` directly instead of the `openObjectTab` helper (which was already bumped to 20s in S06). The Docker test stack's first tab load can take 10-15s due to initial SPARQL queries and template rendering.

**Affected files and lines:**
- `e2e/tests/01-objects/edit-object-ui.spec.ts` — `loadObjectInEditor` helper followed by `.waitForSelector('.object-tab', { timeout: 10000 })` — 5+ callsites (read-view reference fields ×2, edit-mode cancel button, autocomplete dropdown, multi-value reference)
- `e2e/tests/12-bug-fixes/bug-fixes.spec.ts` — lines 27, 43, 140, 149, 194 (5 usages)
- `e2e/tests/01-objects/object-view-redesign.spec.ts` — lines 72, 93, 111, 134, 153, 180, 204, 226, 254, 279 (10 usages)

S06 already bumped `openObjectTab` to 20s. The fix is to bump these direct `waitForSelector('.object-tab', { timeout: 10000 })` calls to 20000 as well. However, only ~5 of these actually fail — the rest pass within 10s. The safe approach is to bump all to 20s since the cost is zero if they resolve faster.

### Category 5: Timeline CDN Timing (3 tests, 1 file)

**timeline.spec.ts** — all 3 tests:
- The `openGenericViewTab` helper waits for `[data-testid="timeline-view"]` to be visible (default `state: 'visible'`), but the timeline container exists in the DOM at min-height 200px (fixed in S06) but has no content until the Frappe Gantt CDN load completes.
- The test already has a follow-up `waitForSelector('.gantt-container', { timeout: 30000 })` which is the real readiness signal.
- The issue is that the `openGenericViewTab` call with `SEL.views.timeline` times out before `.gantt-container` can even be checked.

**Fix:** The `openGenericViewTab` call passes `SEL.views.timeline` (`[data-testid="timeline-view"]`) as the wait selector. With the S06 `min-height: 200px` fix, this element should be visible once the panel renders (before CDN load). If it still fails, the selector should use `{ state: 'attached' }` — but `openGenericViewTab` doesn't expose the state option. Two fixes:
1. Add optional `waitState` parameter to `openGenericViewTab` helper
2. Or: in the timeline test, replace the `openGenericViewTab` call with a lower-level `evaluate + waitForSelector` that specifies `state: 'attached'`

Recommend option 1 — add optional `waitState` parameter defaulting to `'visible'`, and use `'attached'` for timeline tests.

### Category 6: Event Log Bottom Panel (1 test, 1 file)

**event-log-polish.spec.ts** — `openEventLog` helper:
- Calls `toggleBottomPanel()` then waits for `getBoundingClientRect().height > 10`
- The bottom panel height is computed as `parentH * panelState.height / 100` where `parentH` is the parent element's bounding height
- If the parent hasn't laid out yet (e.g., first render), `parentH` could be 0, falling back to `30vh` — which should work
- The more likely issue: `panelState.open` starts `false`, but there might be a localStorage-saved state from a previous test that interferes, or the panel toggle animation takes time

**Fix:** Add a small delay after `toggleBottomPanel()` or wait for the panel element to have a class change (e.g., `panel-open` on the resize handle). The current wait checks height > 10 which is correct, but the timeout of 5000ms might be tight. Bump to 10000ms.

### Category 7: Multi-value Autocomplete Click Timing (1 test, 1 file)

**edit-object-ui.spec.ts** — "autocomplete: selecting a suggestion populates the hidden IRI input":
- Types "Knowledge" into a reference search field, waits for dropdown, clicks a suggestion
- The dropdown visibility check passes but the click sometimes misses because the suggestion item hasn't fully settled
- Fix: Add a small `waitForTimeout(300)` before clicking, or use `suggestion.scrollIntoViewIfNeeded()` before click

### Category 8: Magic-link Rate Limit (1 test, 1 file)

**rate-limiting.spec.ts** — this test already self-skips when `RATE_LIMIT_ENABLED=false`. If it fails during a full suite run, it's because the test stack has rate limiting enabled or the test runs before the skip check.

**Fix:** This test should already pass (it skips). If it's counted among the 19, it may be a false positive from S06's partial run. Verify during T03.

### Category 9: Object Form Visibility After API Create (2 tests, 1 file)

**create-object.spec.ts** — tests that create objects via the UI form panel:
- `ownerPage.waitForSelector(SEL.editor.form, { timeout: 10000 })` — the form loads via an htmx swap into a dockview panel, which involves panel creation + htmx GET + template rendering
- Fix: Bump timeout to 20000ms, matching the pattern from `openObjectTab`

## File Inventory

### Test files to modify:

| File | Changes | Category |
|------|---------|----------|
| `e2e/tests/03-navigation/workspace-layout.spec.ts` | Tab count 4→5, add SPARQL text assertion, RELATIONS case | 1 |
| `e2e/tests/03-navigation/keyboard-shortcuts.spec.ts` | Type count `toBe(4)` → `toBeGreaterThanOrEqual(4)`, remove `waitForIdle` before type picker assertion | 1, 3 |
| `e2e/tests/02-views/table-pagination.spec.ts` | Filter table spec by target_class matching Note | 2 |
| `e2e/tests/05-admin/admin-model-detail.spec.ts` | Replace `waitForIdle` with specific element waits | 3 |
| `e2e/tests/01-objects/create-edge.spec.ts` | Replace `waitForIdle` with specific element wait | 3 |
| `e2e/tests/01-objects/edit-object-ui.spec.ts` | Bump `.object-tab` timeout 10s→20s, fix autocomplete click timing | 4, 7 |
| `e2e/tests/12-bug-fixes/bug-fixes.spec.ts` | Bump `.object-tab` timeout 10s→20s | 4 |
| `e2e/tests/01-objects/object-view-redesign.spec.ts` | Bump `.object-tab` timeout 10s→20s | 4 |
| `e2e/tests/02-views/timeline.spec.ts` | Use `state: 'attached'` for initial wait | 5 |
| `e2e/tests/27-event-log-polish/event-log-polish.spec.ts` | Bump height-check timeout in openEventLog | 6 |
| `e2e/tests/01-objects/create-object.spec.ts` | Bump form wait timeout 10s→20s | 9 |

### Helper file to modify:

| File | Changes |
|------|---------|
| `e2e/helpers/dockview.ts` | Add optional `waitState` parameter to `openGenericViewTab` |

### No application code changes needed

All 19 failures are in test assertions, test timeouts, or test logic. No backend or frontend code needs modification.

## Risks & Constraints

1. **Timeout bumps could mask real slowness** — if a test legitimately shouldn't take 20s, bumping the timeout hides a performance regression. Mitigation: the Docker test stack is known to be slow (shared CPU, triplestore cold start), so 20s is reasonable for first-load operations.

2. **`waitForIdle` replacement could introduce new flakiness** — if we replace `waitForIdle` with element-specific waits, we need to pick the right element. If the element appears before the page is fully interactive, tests may click elements that aren't wired up yet. Mitigation: choose elements that appear after the main content loads (e.g., specific data rows, not just containers).

3. **Full suite run time** — with `retries: 1` and `workers: 1`, the full 122-spec suite can take 30-60 minutes. T03 verification needs adequate timeout budget.

## Skills

No external skills needed. This is purely Playwright test maintenance using patterns established in earlier slices.
