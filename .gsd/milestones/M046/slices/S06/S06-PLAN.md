# S06: Miscellaneous Failures & Full Suite Verification

**Goal:** Full `npx playwright test` run passes with 0 failures across all 122 specs
**Demo:** After this: Full `npx playwright test` run passes with 0 failures across all 122 specs

## Tasks
- [x] **T01: Run full E2E suite and catalog all failures with error messages** — Run the complete 122-spec E2E suite against the Docker test stack and catalog every failure with its file path, test name, and error message. Group failures by likely root cause category. The partial research run (tests 1–118, chromium only) found 14 failures. This task completes the catalog by running all 122 files across both chromium and firefox.

Steps:
1. Ensure Docker test stack is healthy: `docker compose -f docker-compose.test.yml ps` and check all services are Up/healthy.
2. Run the full suite from project root: `cd e2e && npx playwright test --reporter=list 2>&1 | tee /tmp/e2e-full-run.log`
   - If the full run times out (>900s), run per-directory: `npx playwright test tests/00-setup/ tests/01-objects/ tests/02-views/` etc.
3. Extract all failures: grep for 'FAILED\|Error\|Timeout\|expect(' in the output.
4. Write a structured failure catalog to `.gsd/milestones/M046/slices/S06/failure-catalog.md` with columns: File, Test Name, Error Summary, Root Cause Category.
5. Categorize failures into groups: A=bare-global refs (M044 migration), B=template testid mismatch, C=timing/flaky, D=assertion logic, E=missing feature/selector, F=other.

Known failures from S06 research to expect:
- Timeline view (3 tests) — bare globals in timeline_view.html
- RBox ontology viewer — data-testid naming mismatch
- Class creation — bare globals in onclick handlers
- Type picker / keyboard shortcuts — timing
- Object create/edit — timing/flaky
- Table pagination — assertion
- Markdown rendering — CDN timing
- Magic-link member role — invite flow
  - Estimate: 30m
  - Files: e2e/tests/, .gsd/milestones/M046/slices/S06/failure-catalog.md
  - Verify: test -f .gsd/milestones/M046/slices/S06/failure-catalog.md && grep -c '|' .gsd/milestones/M046/slices/S06/failure-catalog.md
- [x] **T02: Fix 14 bare-global references across timeline_view.html, create_class_form.html, and workspace.js; fix RBox test selector; create failure catalog** — Fix every failure cataloged in T01. The research and pre-exploration identified these root causes:

**Category A: Bare-global references after M044 namespace migration**

The M044/S03 migration moved all window globals to `window.SemPKM.*` and removed backward-compat shims. Several templates still use bare globals in `onclick=` handlers and inline `<script>` blocks:

1. `backend/app/templates/browser/timeline_view.html` — Two `showToast` calls (lines with `if (typeof showToast === 'function') showToast(...)`) and one `openTab` call (line with `if (task && task.id && typeof openTab === 'function')`). Replace with `SemPKM.showToast` and `SemPKM.openTab` respectively. Keep the `typeof` guard but check `SemPKM.showToast`/`SemPKM.openTab`.

2. `backend/app/templates/browser/ontology/create_class_form.html` — Multiple `onclick=` handlers use bare globals:
   - `onclick="closeClassCreationForm()"` → `onclick="SemPKM.closeClassCreationForm()"`  (BUT check if this function exists on SemPKM — if not, it may be defined in the template's own script or another file)
   - `onclick="filterIconPicker(this.value)"` → `oninput="SemPKM.filterIconPicker(this.value)"`
   - `onclick="selectIcon(this, '{{ icon_name }}')"` → `onclick="SemPKM.selectIcon(this, '{{ icon_name }}')"`
   - `onclick="selectIconColor(this, '...')"` → `onclick="SemPKM.selectIconColor(this, '...')"`
   - `onclick="clearParentClass()"` → `onclick="SemPKM.clearParentClass()"`
   - `onclick="addPropertyRow()"` → `onclick="SemPKM.addPropertyRow()"`
   - `onclick="removePropertyRow('...')"` → `onclick="SemPKM.removePropertyRow('...')"`
   - `onchange="handlePredicateChange(this)"` → `onchange="SemPKM.handlePredicateChange(this)"`
   - The inline `<script>` block at the bottom: `if (typeof addPropertyRow === 'function') { addPropertyRow(); }` → `if (typeof SemPKM !== 'undefined' && typeof SemPKM.addPropertyRow === 'function') { SemPKM.addPropertyRow(); }`
   - The `hx-on::config-request` attribute calls `serializeProperties()` → `SemPKM.serializeProperties()`
   - `closeClassCreationForm` — check workspace.js for `SemPKM.closeClassCreationForm`. If it's defined there, use `SemPKM.closeClassCreationForm()`. If not, check if it's a local function in the template or in another file.

**Category B: RBox data-testid mismatch**

`backend/app/templates/browser/ontology/rbox_legend.html` — The macro `render_property_table(properties, testid)` produces `data-testid="{{ testid }}-{{ source }}"` (e.g., `rbox-object-table-gist`). The E2E test `e2e/tests/22-ontology/ontology-viewer.spec.ts` expects `[data-testid="rbox-object-table"]` without the source suffix. Two options:
- Option 1: Fix the test to use a prefix-match selector: `[data-testid^="rbox-object-table"]`
- Option 2: Fix the template to use bare testid: `data-testid="{{ testid }}"`
Prefer Option 1 (test fix) since the per-source testid is more specific and useful for debugging.

**Category C: Test timing and flakiness**

After fixing A and B, re-run failing tests to see which are genuinely flaky vs fixed by the template repairs. Common timing fixes:
- Increase timeouts on `.waitForSelector()` calls that are marginal (15s → 20s or 30s)
- Add `waitForIdle()` before assertions that depend on htmx content loading
- For create-object:17 (type picker shows 4 types), the test opens a dockview panel via `_dockview.addPanel()` which triggers htmx load of `/browser/types`. If the htmx load is slow, the type picker may not render in time. Add a longer timeout.

**Category D: Table pagination assertion**

The table-pagination test fetches `/browser/views/table/{specIri}?page=1&page_size=5` and expects `Page 1 of` text. If the response format changed (e.g., pagination partial uses different text), fix the assertion to match reality. Run the endpoint manually to see what it returns.

**Category E: Markdown rendering**

The markdown-rendering test creates a Note with markdown body, then checks for rendered `h1`/`h2`/`strong`/`pre` elements inside `.markdown-body`. The rendering depends on `marked.js` being loaded via the vendor bundle. In the Docker test stack, vendor.js is built by the frontend container. If it's a timing issue (CDN/script load order), add a `waitForFunction` with longer timeout.

**Category F: Other failures from T01 catalog**

Fix any additional failures discovered by T01 that weren't in the research list.

Steps:
1. Read T01's failure catalog from `.gsd/milestones/M046/slices/S06/failure-catalog.md`.
2. Fix Category A (bare globals) in timeline_view.html and create_class_form.html.
3. Fix Category B (RBox testid) — update the test selectors to use prefix match.
4. Fix Category C/D/E/F based on T01 catalog.
5. Run affected test files to verify fixes: `cd e2e && npx playwright test tests/02-views/timeline.spec.ts tests/22-ontology/ tests/23-class-creation/ tests/01-objects/ tests/02-views/table-pagination.spec.ts tests/01-objects/markdown-rendering.spec.ts tests/03-navigation/keyboard-shortcuts.spec.ts --project=chromium`
6. Fix any remaining failures and re-run until all targeted files pass.
  - Estimate: 2h
  - Files: backend/app/templates/browser/timeline_view.html, backend/app/templates/browser/ontology/create_class_form.html, backend/app/templates/browser/ontology/rbox_legend.html, e2e/tests/22-ontology/ontology-viewer.spec.ts, e2e/tests/23-class-creation/class-creation.spec.ts, e2e/tests/01-objects/create-object.spec.ts, e2e/tests/01-objects/markdown-rendering.spec.ts, e2e/tests/02-views/table-pagination.spec.ts, e2e/tests/02-views/timeline.spec.ts, e2e/tests/03-navigation/keyboard-shortcuts.spec.ts
  - Verify: cd e2e && npx playwright test tests/02-views/timeline.spec.ts tests/22-ontology/ tests/23-class-creation/ tests/01-objects/create-object.spec.ts tests/01-objects/markdown-rendering.spec.ts tests/02-views/table-pagination.spec.ts tests/03-navigation/keyboard-shortcuts.spec.ts --project=chromium 2>&1 | tail -5
- [ ] **T03: Full suite green-light verification — 0 failures across all 122 specs** — Run the complete E2E suite and verify 0 failures. Fix any remaining failures discovered during this run.

Steps:
1. Run full suite: `cd e2e && npx playwright test --reporter=list 2>&1 | tee /tmp/e2e-greenlight.log`
   - If timeout is an issue, run in batches by directory.
2. If any tests fail:
   a. Read the error output carefully.
   b. Apply targeted fixes (template edits, test timeout increases, selector adjustments).
   c. Re-run the failing tests to confirm the fix.
   d. Re-run the full suite again to check for regressions.
3. Repeat until 0 failures.
4. Record the final pass count and any skipped tests in the verification output.

Expected: 122 spec files, majority passing, some skipped (setup wizard fresh-stack tests, demo mode tests, etc.), 0 failures.

Note: Tests that skip due to prerequisites (e.g., fresh Docker stack, demo mode, rate limiting) are acceptable — they're gated by `test.skip()` conditions. Only actual failures (assertion errors, timeouts, crashes) count.
  - Estimate: 45m
  - Files: e2e/tests/
  - Verify: cd e2e && npx playwright test --reporter=list 2>&1 | grep -E 'failed|passed|skipped' | tail -3
