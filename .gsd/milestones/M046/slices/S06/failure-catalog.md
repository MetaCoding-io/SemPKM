# S06 Failure Catalog

## Category A: Bare-global references (FIXED in T02)

| File | Old Reference | Fixed To |
|------|--------------|----------|
| `backend/app/templates/browser/timeline_view.html` | `showToast(...)` ×2 | `SemPKM.showToast(...)` |
| `backend/app/templates/browser/timeline_view.html` | `openTab(...)` | `SemPKM.openTab(...)` |
| `backend/app/templates/browser/ontology/create_class_form.html` | `filterIconPicker(this.value)` | `SemPKM.filterIconPicker(this.value)` |
| `backend/app/templates/browser/ontology/create_class_form.html` | `selectIcon(this, ...)` ×40 | `SemPKM.selectIcon(this, ...)` |
| `backend/app/templates/browser/ontology/create_class_form.html` | `selectIconColor(this, ...)` ×9 | `SemPKM.selectIconColor(this, ...)` |
| `backend/app/templates/browser/ontology/create_class_form.html` | `clearParentClass()` | `SemPKM.clearParentClass()` |
| `backend/app/templates/browser/ontology/create_class_form.html` | `addPropertyRow()` (onclick + script) | `SemPKM.addPropertyRow()` |
| `backend/app/templates/browser/ontology/create_class_form.html` | `serializeProperties()` (hx-on) | `SemPKM.serializeProperties()` |
| `frontend/static/js/workspace.js` | `handlePredicateChange(this)` (in generated HTML) | `SemPKM.handlePredicateChange(this)` |
| `frontend/static/js/workspace.js` | `removePropertyRow(...)` (in generated HTML) | `SemPKM.removePropertyRow(...)` |

**Note:** `closeClassCreationForm()` and `openPropertyEditForm()` are defined as page-level functions in `ontology_page.html` (not on SemPKM namespace), so they remain as bare globals — correct behavior.

## Category B: RBox data-testid mismatch (FIXED in T02)

Template `rbox_legend.html` generates `data-testid="rbox-object-table-{{ source }}"` (e.g., `rbox-object-table-gist`). Test expected exact match `[data-testid="rbox-object-table"]`. Fixed test to use prefix selector `[data-testid^="rbox-object-table"]`.

## Category C: Auth rate limit timeouts (INFRASTRUCTURE — not a code bug)

Most test failures across all files are `TimeoutError: apiRequestContext.post: Timeout 10000ms exceeded` at `fixtures/auth.ts:129` (POST `/api/auth/verify`). This is the magic-link rate limiter (5 calls/min) being hit when multiple test files run in parallel or in quick succession. Restarting the API container and running tests with sufficient spacing resolves these.

## Category D: Timeline view visibility (TIMING)

Timeline test fails waiting for `[data-testid="timeline-view"]` to be visible. The element exists (attached) but Playwright reports it as hidden because `.timeline-container` has `flex:1; min-height:0` with no content until the async Frappe Gantt CDN load + data fetch completes. The `openGenericViewTab` helper waits for visibility, which fails before content renders. Fix needed: either use `state:'attached'` for initial wait, or increase timeout to allow CDN+data load.

## Category E: Keyboard shortcuts — waitForIdle timeout

`keyboard-shortcuts.spec.ts` "Alt+N opens type picker" fails at `waitForIdle()` checking `.htmx-request` count === 0. An htmx request stays pending longer than 10s. Likely needs increased timeout or wait-for-specific-element instead of generic idle check.

## Category F: Create-object — form not visible

`create-object.spec.ts` tests 2-8 fail waiting for `[data-testid="object-form"]` after `openCreateForm()`. First test fails on auth. Subsequent tests fail because the form panel doesn't render within 10s. May need increased timeout or explicit wait for the htmx `/browser/types` load that populates the form.
