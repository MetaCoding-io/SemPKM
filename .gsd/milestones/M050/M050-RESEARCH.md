# M050 Research: View System Rework

**Date:** 2026-04-05
**Status:** Complete

## Executive Summary

The view system has a solid backend architecture with SHACL-driven field detection already working for 8 specialty renderers. The core problem is the **type_filter_pills.html** template included by all 11 view templates — it renders every SHACL-defined type as an htmx button, producing 37+ pills when multiple models are installed. The fix is surgical: replace this single template with a `<select>` dropdown, pre-filter by renderer compatibility, and clean up the toolbar. The View Variants dropdown, save flow, and sizing issues are all isolated, low-coupling changes.

## Architecture Analysis

### Current View Rendering Pipeline

1. **Explorer sidebar** → user clicks "Table View" / "Kanban View" etc.
2. **workspace.js** `openGenericViewTab(renderer)` → creates dockview panel with `specialType: 'generic-view'`
3. **workspace-layout.js** `createComponentFn` → builds URL `/browser/views/generic/{renderer}?type=...&scope_query=...`
4. **router.py** `generic_view()` → 1000-line if/elif chain dispatching to 11 renderer blocks
5. Each block calls `shapes_service.get_types()` for the pill bar, then renderer-specific `_detect_*()` for field detection
6. **Template** renders `type_filter_pills.html` (pill bar) + `view_toolbar.html` (filter/scope/save controls)

### Key Files

| File | Lines | Role |
|------|-------|------|
| `backend/app/views/router.py` | 1960 | View endpoints — `generic_view()` is the megafunction |
| `backend/app/views/service.py` | 3675 | ViewSpecService with all `_detect_*()` and `execute_*()` methods |
| `backend/app/templates/browser/type_filter_pills.html` | 22 | The pill bar template — included by all 11 view templates |
| `backend/app/templates/browser/view_toolbar.html` | 80 | Toolbar with variant dropdown, scope select, save button, filter |
| `frontend/static/css/views.css` | 1800+ | All view CSS including pills, toolbar, per-renderer styles |
| `frontend/static/js/workspace.js` | 5400+ | `openViewTab`, `openGenericViewTab`, `applyScopeQuery`, `saveCurrentView` |
| `frontend/static/js/workspace-layout.js` | 640+ | dockview component factory — `generic-view` special panel |

### The 37-Pill Problem

`shapes_service.get_types()` returns all SHACL NodeShape target classes, minus hidden types. With 8 models installed, that's potentially 73 total types — filtered down to ~37 visible ones. These render as `<button>` elements in a flex-wrap container, consuming ~140px of viewport and spanning 4 rows.

**Current flow:** Every renderer gets the same `types_list` — all types in the system. Clicking a type pill for kanban view reloads with that type, but if the type has no `sh:in` status field, the view shows "This type has no properties..." error. The user must trial-and-error through pills to find compatible types.

### Existing Field Detection Infrastructure

The backend already has the detection methods needed for smart filtering:

| Renderer | Detection Method | What It Checks |
|----------|-----------------|----------------|
| kanban | `_detect_status_field()` | SHACL properties with `sh:in` values (prefers "status" in path) |
| calendar | `_detect_date_fields()` | `sh:datatype` is xsd:date/dateTime OR path in well-known date list |
| timeline | `_detect_date_fields()` | Same as calendar |
| map | `_detect_geo_fields()` | lat/lng pairs from well-known IRIs or local-name heuristic |
| quadrant | `_detect_quadrant_axes()` | Properties with exactly 2 `sh:in` values + keyword pairs |
| bmc | `_detect_bmc_sections()` | Property with exactly 9 `sh:in` values |
| okr | `_detect_okr_structure()` | decimal currentValue/targetValue properties |
| decision-matrix | `_detect_decision_matrix_structure()` | Specific structural detection |
| table | None needed | Works with any type |
| card | None needed | Works with any type |
| graph | None needed | Works with any type |

**Key insight:** All `_detect_*()` methods accept a single `type_iri` and return None/empty when incompatible. To build a smart dropdown, we'd need a new method that iterates all types and calls the appropriate detector per renderer. This is a batch of SHACL shape lookups — potentially expensive but cacheable.

### View Variants Dropdown

The `view-variant-select` dropdown in `view_toolbar.html` shows `model_view_specs` — ViewSpec objects from installed Mental Models. It's only populated when a type is selected. The dropdown says "— View Variants —" and shows entries like "Task Board" or "Project Timeline" defined by model manifests.

**Assessment:** This is confusing because (a) it's unclear what "variant" means vs. the renderer you're already in, (b) it only appears when a type is selected, and (c) the naming overlaps with the generic renderers. Removing it is clean — no data model changes, just template deletion and CSS removal. Existing saved views don't reference variant IDs — they store `renderer_type` and `type_filter`.

### Save View Flow

The save flow exists and mostly works:

1. `saveCurrentView()` in `view_toolbar.html` inline script → calls `POST /browser/views/save`
2. Backend `save_promoted_view()` stores in RDF as a `PromotedView` with label, renderer_type, type_filter, scope_query_id
3. Saved views appear in `my_views.html` sidebar section
4. Click reopens via `openGenericViewTab(renderer, scopeQuery, label)`

**Issues found:**
- The save button is a bookmark-plus icon with no label — undiscoverable
- Save doesn't persist the current `type_filter` from the pill bar. Looking at the JS: `toolbar.dataset.typeFilter` reads from `data-type-filter="{{ selected_type | default('') }}"` — this should work IF `selected_type` is populated, but the `openGenericViewTab` function reads type from localStorage, not from the saved view data
- When restoring, `openGenericViewTab` passes `scopeQuery` but NOT `selectedType` from the saved view data — the type filter is lost on restore
- The `my_views.html` template has `data-type-filter` and `data-scope-query` attributes on each entry but they're not used in the onclick handler

### View Sizing

dockview panels get `.group-editor-area` with inline `width:100%;height:100%;overflow:auto;`. Views using `.view-flex-column` wrapper (graph, kanban, timeline, calendar, map) correctly flex-fill. Table and cards use natural scrolling.

**Potential issue:** The pill bar + toolbar take vertical space. With pills consuming ~140px and toolbar ~40px, a 600px panel has only ~420px for content. Replacing pills with a dropdown reclaims ~100px immediately.

### Calendar Dark Mode

FullCalendar dark mode overrides exist at `views.css:1420+`. Button colors are styled: `background: var(--color-bg-secondary)`, `color: var(--color-text)`. The nav icons (prev/next arrows) are FullCalendar's default SVG icons embedded as `background-image` on the buttons.

**Root cause:** FullCalendar uses `color` CSS property for its button icons via `currentColor` in the embedded SVG. The dark mode override sets `color: var(--color-text)` which should work. Need to verify — may be an SVG `fill` vs `stroke` issue, or the icons may use hardcoded black in the SVG path. FullCalendar 6.x uses CSS custom properties `--fc-button-text-color` which we're not setting.

### Timeline Issues

The Frappe Gantt integration already has `scroll_to: 'today'` and `today_button: true` configured (line 112-113 of timeline_view.html). `on_click` opens the object tab via `SemPKM.openTab()`.

**#52 scroll-to-today:** Already implemented in the config. If it's not working, it's a Frappe Gantt version issue or a timing issue (gantt may scroll before the container has its final height).

**#54 popover dismiss:** The `.gantt .popup-wrapper` has `z-index: 10000` in CSS, but there's no click-outside or Escape dismiss handler. Frappe Gantt's built-in popup doesn't dismiss automatically — this needs a JS listener.

**#56 selection → detail:** Already implemented via `on_click: function(task) { SemPKM.openTab(task.id, task.name) }`.

### Geo Fields for Map View

Issue #60 asks for geo fields on CRM Contact/Company or basic-pkm Event + seed data. Currently no model ships with lat/lng fields. Adding them requires SHACL shape changes + seed data — model modification rather than view code.

## Technology Constraints

### SHACL Shape Querying Performance

Each `_detect_*()` method calls `shapes_service.get_form_for_type(type_iri)` which does a SPARQL query to the triplestore. For smart type filtering across all types, this would be N queries (one per type). With 37 types × 1 SPARQL query each, this adds ~37 queries on every view open.

**Mitigation options:**
1. **Batch approach:** New endpoint that returns all types with their renderer compatibility in one call. Cache the result (shapes don't change within a session).
2. **Client-side caching:** First view load populates a type→renderer compatibility map, subsequent view opens use cached data.
3. **Lazy evaluation:** Show all types initially, mark incompatible ones as disabled/dimmed after async check.

Option 1 (batch + cache) is cleanest. `shapes_service.get_node_shapes()` returns all forms at once — we can iterate once and check each form's properties against all renderer requirements. One call, cache the result.

### htmx Pill Replacement

The pills use htmx `hx-get` to reload the entire view when clicked. Replacing with a `<select>` dropdown just needs an `onchange` handler that does the same htmx GET. The `hx-get` URL pattern is already known: `/browser/views/generic/{renderer}?type={encoded_type_iri}`.

### Saved View Data Model

PromotedViewData already stores `renderer_type`, `type_filter`, `scope_query_id`. The model is sufficient for save/restore — the bug is in the JS restoration path, not the data model.

## Risk Assessment

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| 1 | Smart type filtering adds N SPARQL queries per view open | Medium | High | Batch detection with caching |
| 2 | Removing View Variants breaks saved views | Low | Low | Saved views don't reference variant IDs |
| 3 | Calendar nav icon fix requires FullCalendar version-specific CSS | Low | Medium | Test against actual CDN version |
| 4 | Type dropdown doesn't fit narrow panels | Low | Low | Standard `<select>` handles overflow natively |
| 5 | Breaking existing E2E tests (13 test files, ~90 tests) | Medium | High | Pill removal changes selectors that tests may depend on |

## Natural Slice Boundaries

### S01: Type Dropdown + Smart Filtering (highest risk — proves the core concept)
- Replace `type_filter_pills.html` with a `<select>` dropdown
- Build backend endpoint for type→renderer compatibility map
- Pre-filter the dropdown by renderer (kanban shows only status-capable types, etc.)
- All 11 view templates updated
- **Risk:** Performance of batch shape detection, correct filtering across all 8 specialty renderers

### S02: Toolbar Cleanup + Sizing
- Remove View Variants dropdown from `view_toolbar.html`
- Remove `.view-variant-select` CSS
- Audit and fix full-height sizing for all views
- Fix calendar dark mode nav icons
- **Risk:** Low — removals and CSS fixes

### S03: Save/Restore Flow Fix
- Fix `saveCurrentView()` to persist type filter
- Fix `openGenericViewTab` to accept and apply type filter from saved view
- Fix `my_views.html` to pass type filter in onclick
- Add visible "Save View" label/tooltip
- **Risk:** Low — JS-only changes, clear bug path

### S04: Timeline Polish + E2E Tests
- Fix timeline scroll-to-today (verify Frappe Gantt behavior)
- Add popover dismiss on click-outside/Escape
- Write E2E tests for the new dropdown, save/restore, sizing
- Update existing E2E selectors for pill→dropdown change
- **Risk:** Medium — E2E tests may need significant updates

### S05: Map View Seed Data (optional)
- Add lat/lng fields to a model type (e.g., CRM Contact or basic-pkm Event)
- Add seed data with coordinates
- **Risk:** Low — model file changes only

## Candidate Requirements

These emerged from research. The planner should evaluate whether to adopt them:

1. **Type dropdown shows human-readable labels** — already the case via `shapes_service.get_types()`. Verified: type pill labels come from SHACL NodeShape labels, not raw IRIs.

2. **Smart type filtering should be cached** — the batch shape detection result should be cached per session or with TTL, not recalculated on every view open. This is a performance requirement.

3. **Saved view restore must preserve type filter** — currently broken. The `openGenericViewTab` function ignores the stored `type_filter`. This is a bug fix, not a new feature.

4. **E2E test selectors need migration plan** — existing selectors reference `.type-pill`, `.view-variant-select`. The pill→dropdown change will break these. A selector migration should be part of the implementation plan.

## Existing Patterns to Reuse

- **`view-flex-column` wrapper** — established pattern for full-height views (Knowledge: "Views needing full-height must use .view-flex-column wrapper")
- **`_detect_*()` methods** — all return None/empty for incompatible types, making them natural filter predicates
- **`shapes_service.get_node_shapes()`** — already returns all forms in one call, cacheable
- **`type_filter_pills.html` include** — single-file change propagates to all 11 view templates
- **`openGenericViewTab` params** — already accepts `selectedType` via localStorage, just needs to accept it directly
- **E2E `openGenericViewTab` helper** — in `e2e/helpers/dockview.ts`, wraps the JS API

## Open Questions (with recommendations)

**Q: Single-select or multi-select type dropdown?**
Recommend: **Single-select.** The backend's `generic_view()` already takes a single `type` parameter. Multi-select would require UNION queries and significant backend changes. A `<select>` with single selection is the simplest drop-in replacement for pills.

**Q: How should saved views store configuration — RDF or localStorage?**
Recommend: **Keep RDF** (current approach). The `PromotedView` RDF data model already works. localStorage would be lost on device switch. The fix is in the JS restore path, not the storage layer.

**Q: Should the batch type compatibility endpoint be a new API or inline in the view render?**
Recommend: **Inline in the view render.** The `generic_view()` function already calls `shapes_service.get_types()`. Replace that with a richer call that also returns compatibility flags. No new endpoint needed — just richer template context.
