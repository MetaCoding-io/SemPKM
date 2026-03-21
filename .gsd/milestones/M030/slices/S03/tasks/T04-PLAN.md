---
estimated_steps: 8
estimated_files: 5
---

# T04: Lint panel dismiss buttons and lint dashboard suppress/preset controls

**Slice:** S03 — Lint Filter System (Suppress, Dismiss, Presets)
**Milestone:** M030

## Description

Add the user-facing UI for the filter system: dismiss buttons on the per-object lint panel, suppress controls per result row on the lint dashboard, and a preset selector in the dashboard sidebar. All interactions use `fetch()` + htmx refresh patterns established in the codebase (D048 favoritesRefreshed, D104 dashboardsRefreshed).

**Important CSS rule from CLAUDE.md**: Lucide SVGs need `flex-shrink: 0` in flex containers. Use `stroke: currentColor` for SVG icon color inheritance.

## Steps

1. Add dismiss button to `backend/app/templates/browser/lint_panel.html`:
   - Add a small dismiss button (× icon via Lucide `x` or HTML entity `×`) next to each warning/info result item (NOT violations — violations are structural and shouldn't be dismissable)
   - Button needs `data-object-iri="{{ object_iri }}"` and `data-source-shape="{{ w.source_shape }}"` attributes
   - Use `onclick` handler calling a new `dismissLintResult(objectIri, sourceShape, element)` function
   - Skip rendering dismiss button if `source_shape` is empty (can't dismiss without stable identifier)
   - Show "N dismissed" indicator below results if `dismissed_count > 0`: `<div class="lint-dismissed-indicator">{{ dismissed_count }} dismissed</div>`

2. Add dismiss JS handler to `frontend/static/js/workspace.js`:
   - `function dismissLintResult(objectIri, sourceShape, btn)`:
     - `fetch('/api/lint/dismiss', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({object_iri: objectIri, rule_source_iri: sourceShape}) })`
     - On success: re-fetch lint panel via `htmx.ajax('GET', '/browser/lint/' + encodeURIComponent(objectIri), {target: btn.closest('.lint-panel'), swap: 'outerHTML'})`

3. Add suppress button to lint dashboard result rows in `backend/app/templates/browser/lint_dashboard.html`:
   - Add a small "suppress" icon button (Lucide `eye-off` or similar) in each result row (new column or inside the severity column)
   - Button calls `suppressLintRule(sourceShape)` — needs `data-source-shape` from each `item`
   - Note: the dashboard already requests `detail=full` when rendering, but currently only uses it in the API. Ensure the dashboard route passes `detail=True` so `source_shape` is available in template context for each `item`.

4. Add suppress JS handler to `frontend/static/js/workspace.js`:
   - `function suppressLintRule(sourceShape)`:
     - `fetch('/api/lint/suppress', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({rule_source_iri: sourceShape}) })`
     - On success: refresh dashboard via `htmx.ajax('GET', '/browser/lint-dashboard', {target: '#lint-dashboard-container', swap: 'outerHTML'})`

5. Add preset selector to lint dashboard sidebar in `backend/app/templates/browser/lint_dashboard.html`:
   - New sidebar group below existing Sort filter: "Preset" label with a `<select>` dropdown
   - Options: "No preset" (value="") + one option per preset from `active_presets` template variable
   - On change: call `applyLintPreset(presetId)` JS function
   - Add a "Save Current" button below the dropdown that calls `saveLintPreset()`
   - Show "N rules suppressed" badge in the sidebar summary if `suppressed_count > 0`

6. Add preset JS handlers to `frontend/static/js/workspace.js`:
   - `function applyLintPreset(presetId)`: POST `/api/lint/presets/{id}/apply`, then refresh dashboard
   - `function saveLintPreset()`: prompt for name, POST `/api/lint/presets` with name + current suppressions (fetch GET /api/lint/suppressions first to get current list), then refresh dashboard

7. Add CSS for dismiss/suppress buttons in `frontend/static/css/workspace.css`:
   - `.lint-dismiss-btn`: small inline button, muted color, hover highlight
   - `.lint-suppress-btn`: small icon button in dashboard rows
   - `.lint-dismissed-indicator`: muted text below lint panel results
   - `.lint-suppressed-badge`: badge in dashboard sidebar
   - `.lint-preset-actions`: flex container for preset selector + save button
   - All buttons with `svg { flex-shrink: 0; stroke: currentColor; }` per CLAUDE.md rules

8. Update dashboard route in `backend/app/browser/pages.py`:
   - Ensure `detail=True` is passed to `lint_service.get_results()` so `source_shape` is available in each result item for the suppress button
   - Pass `suppressed_count` and `active_presets` to template context (these should already be available from T03)

## Must-Haves

- [ ] Dismiss buttons on lint panel warning/info results (not violations)
- [ ] Suppress buttons on lint dashboard result rows
- [ ] Preset selector dropdown in dashboard sidebar
- [ ] "Save Current" button creates preset from active suppressions
- [ ] JS handlers use fetch() + htmx refresh pattern
- [ ] CSS follows CLAUDE.md Lucide SVG rules (flex-shrink: 0, stroke: currentColor)

## Verification

- Docker stack: create object with lint warnings → see dismiss buttons → click dismiss → warning disappears from panel, "1 dismissed" indicator shows
- Docker stack: open lint dashboard → see suppress buttons on result rows → click suppress → all results for that rule disappear
- Docker stack: save current suppressions as preset "My Preset" → clear suppressions → apply "My Preset" → suppressions restored

## Inputs

- `backend/app/templates/browser/lint_panel.html` — existing lint panel template with violations/warnings/infos
- `backend/app/templates/browser/lint_dashboard.html` — existing dashboard with sidebar filters
- `backend/app/lint/router.py` — T02's API endpoints for suppress/dismiss/preset
- `backend/app/browser/pages.py` — T03's dashboard route with suppressed_count + active_presets
- `backend/app/browser/objects.py` — T03's lint panel route with dismissed_count

## Expected Output

- `backend/app/templates/browser/lint_panel.html` — dismiss buttons + dismissed count indicator
- `backend/app/templates/browser/lint_dashboard.html` — suppress buttons + preset selector + suppressed badge
- `frontend/static/js/workspace.js` — dismissLintResult, suppressLintRule, applyLintPreset, saveLintPreset functions
- `frontend/static/css/workspace.css` — filter UI styling
- `backend/app/browser/pages.py` — detail=True for dashboard results

## Observability Impact

- **Browser console**: JS errors from `dismissLintResult`, `suppressLintRule`, `applyLintPreset`, `saveLintPreset` are logged to `console.error` with descriptive prefixes (e.g., `dismissLintResult error:`)
- **Network tab**: dismiss/suppress/preset actions produce observable `fetch()` calls to `/api/lint/dismiss`, `/api/lint/suppress`, `/api/lint/presets`, `/api/lint/suppressions` — inspect status codes for success/failure
- **Template context**: `dismissed_count` in lint panel template, `suppressed_count` and `active_presets` in dashboard template — visible in rendered HTML
- **Existing API surfaces unchanged**: All T02 REST endpoints continue to work; this task only adds frontend consumers
