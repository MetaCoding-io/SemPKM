---
estimated_steps: 20
estimated_files: 11
skills_used: []
---

# T02: Replace pill bar with type dropdown and remove View Variants

Replace the `type_filter_pills.html` template (37 buttons across 4 rows) with a `<select>` dropdown in a new `type_filter_dropdown.html` partial. Remove the View Variants dropdown from `view_toolbar.html` (D389). Update all 7 view templates. Update CSS.

**Steps:**
1. Create `backend/app/templates/browser/type_filter_dropdown.html`:
   - Single `<select class="type-filter-select">` with `<option value="">All Types</option>` default
   - Loop `{% for t in types %}` rendering `<option value="{{ t.iri }}" {% if selected_type == t.iri %}selected{% endif %}>{{ t.label }}</option>`
   - `onchange` handler: build URL `/browser/views/generic/{{ renderer }}?type=<value>` + preserve scope_query, then `htmx.ajax('GET', url, {target: 'closest .group-editor-area', swap: 'innerHTML'})`
   - Also persist selection: `localStorage.setItem('sempkm_generic_type_' + renderer, this.value)`
   - Wrap in a small container div `<div class="type-filter-dropdown">`
2. Update all 7 view templates — change `{% include "browser/type_filter_pills.html" %}` to `{% include "browser/type_filter_dropdown.html" %}`:
   - `table_view.html`, `cards_view.html`, `kanban_view.html`, `graph_view.html`, `calendar_view.html`, `timeline_view.html`, `map_view.html`
3. In `view_toolbar.html`, remove the View Variants dropdown block (the `{% if model_view_specs ... %}` select with class `view-variant-select`)
4. Update `frontend/static/css/views.css`:
   - Remove `.type-filter-pills`, `.type-pill`, `.type-pill:hover`, `.type-pill.active` rules
   - Add `.type-filter-dropdown` and `.type-filter-select` styling (compact select, matching toolbar aesthetic)
   - Remove `.view-variant-select` styles
5. Verify: open each view renderer in the browser and confirm dropdown appears, pills are gone, View Variants is gone

**Important constraints:**
- The `onchange` handler must preserve `scope_query` from the toolbar's `data-scope-query` attribute or the scope select's value
- The dropdown must show only the types passed in the `types` template variable (already filtered by T01's backend work)
- The `type_filter_pills.html` file should be kept but emptied (or deleted) — keeping it prevents include errors if any non-generic view still references it

## Inputs

- ``backend/app/views/service.py` — get_compatible_types() method from T01`
- ``backend/app/views/router.py` — updated generic_view() passing filtered types from T01`
- ``backend/app/templates/browser/type_filter_pills.html` — current pill template to replace`
- ``backend/app/templates/browser/view_toolbar.html` — current toolbar with View Variants to remove`
- ``frontend/static/css/views.css` — current pill CSS to replace`

## Expected Output

- ``backend/app/templates/browser/type_filter_dropdown.html` — new dropdown partial`
- ``backend/app/templates/browser/type_filter_pills.html` — emptied or deleted`
- ``backend/app/templates/browser/view_toolbar.html` — View Variants dropdown removed`
- ``backend/app/templates/browser/table_view.html` — updated include`
- ``backend/app/templates/browser/cards_view.html` — updated include`
- ``backend/app/templates/browser/kanban_view.html` — updated include`
- ``backend/app/templates/browser/graph_view.html` — updated include`
- ``backend/app/templates/browser/calendar_view.html` — updated include`
- ``backend/app/templates/browser/timeline_view.html` — updated include`
- ``backend/app/templates/browser/map_view.html` — updated include`
- ``frontend/static/css/views.css` — pill styles removed, dropdown styles added`

## Verification

grep -r 'type_filter_pills' backend/app/templates/browser/ | grep -v 'type_filter_pills.html' | wc -l should return 0 (no templates include the old pills). grep -c 'type_filter_dropdown' backend/app/templates/browser/table_view.html backend/app/templates/browser/kanban_view.html returns 1 per file. grep -c 'view-variant-select' backend/app/templates/browser/view_toolbar.html returns 0.
