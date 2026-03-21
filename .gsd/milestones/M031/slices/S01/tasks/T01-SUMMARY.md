---
id: T01
parent: S01
milestone: M031
provides:
  - Carousel tab bar fully removed from templates, JS, CSS, and router
  - Model-declared variant dropdown in view toolbar
key_files:
  - backend/app/views/router.py
  - backend/app/templates/browser/view_toolbar.html
  - backend/app/templates/browser/table_view.html
  - backend/app/templates/browser/cards_view.html
  - backend/app/templates/browser/graph_view.html
  - frontend/static/js/workspace.js
  - frontend/static/css/views.css
key_decisions:
  - Variant dropdown uses existing openViewTab() to navigate to model-declared views rather than inline htmx swap
  - Dedicated view endpoints pass model_view_specs as empty list since they already show a specific view
patterns_established:
  - model_view_specs replaces all_specs in all template contexts — templates check `model_view_specs is defined and model_view_specs | length > 0`
observability_surfaces:
  - .view-variant-select element presence indicates model-declared ViewSpecs exist for active type
  - Absence of dropdown for a type = no model-declared specs (not an error)
duration: 25m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Remove carousel tab bar and add model-declared variant dropdown

**Removed carousel tab bar from all view templates, JS, CSS, and router; added model-declared variant dropdown to view toolbar.**

## What Happened

Surgically removed the entire carousel system across 7 files:

1. **Templates** — Removed `{% include "browser/carousel_tab_bar.html" %}` and the `.carousel-view-body` wrapper `<div>` (opening + closing) from `table_view.html`, `cards_view.html`, and `graph_view.html`. Deleted `carousel_tab_bar.html`.

2. **Router** — Replaced the `all_specs` carousel-building block in `generic_view()` (which merged generic specs + model-declared specs) with a simpler `model_view_specs = await view_spec_service.get_view_specs_for_type(type_iri)` call. Updated all three renderer branches to pass `model_view_specs` instead of `all_specs`. For the dedicated `table_view()`, `cards_view()`, and `graph_view()` endpoints, removed the `get_view_specs_for_type()` calls and passed `model_view_specs: []` since those endpoints already serve a specific model-declared view.

3. **View toolbar** — Added a `<select class="view-variant-select">` dropdown that conditionally renders when `model_view_specs` is non-empty. Each option carries the spec IRI as value and renderer type as `data-renderer`. The `onchange` handler calls `openViewTab()` which already exists and opens model-declared views in dockview tabs.

4. **JS** — Removed `switchCarouselView()` (~65 lines) and `restoreCarouselView()` (~20 lines) functions, their `window.*` exports, and updated the `loadViewContent()` comment to remove carousel reference.

5. **CSS** — Removed all carousel styles (`.carousel-tab-bar`, `.carousel-tab`, `.carousel-tab:hover`, `.carousel-tab.active`, `.carousel-view-body`, `.view-loading-indicator`, `.view-loading-spinner`, `@keyframes carousel-spin`) and added `.view-variant-select` styling.

## Verification

All four verification checks pass:

- `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/views.css` — zero results
- `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" frontend/static/js/` — zero results
- `ls backend/app/templates/browser/carousel_tab_bar.html` — "No such file"
- `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` — no syntax errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/views.css` | 1 | ✅ pass (no matches) | <1s |
| 2 | `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" frontend/static/js/` | 1 | ✅ pass (no matches) | <1s |
| 3 | `ls backend/app/templates/browser/carousel_tab_bar.html` | 2 | ✅ pass (No such file) | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `grep -rn "all_specs" backend/app/templates/ backend/app/views/router.py` | 1 | ✅ pass (no stale refs) | <1s |

### Slice-level verification (partial — T01 is task 1 of 3)

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | `cd backend && python -m pytest tests/test_view_scope.py -v` | ⬜ not yet | Test file created by T03 |
| 2 | `grep -rn "carousel" ...` | ✅ pass | Zero results |
| 3 | `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" ...` | ✅ pass | Zero results |
| 4 | Docker stack manual check | ⬜ deferred | Requires running Docker stack — will verify in final task |

## Diagnostics

- **Variant dropdown presence:** `document.querySelector('.view-variant-select')` in browser DevTools — non-null when a type with model-declared ViewSpecs is active.
- **Missing dropdown:** If the dropdown doesn't appear for a type that should have specs, check that `view_spec_service.get_view_specs_for_type(type_iri)` returns results. The template guard is `model_view_specs | length > 0`.
- **Carousel remnants:** `grep -rn "carousel" backend/ frontend/` should return zero results from views/workspace code.

## Deviations

None — executed exactly as planned.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/carousel_tab_bar.html` — **deleted**
- `backend/app/templates/browser/table_view.html` — removed carousel include and `.carousel-view-body` wrapper
- `backend/app/templates/browser/cards_view.html` — removed carousel include and `.carousel-view-body` wrapper
- `backend/app/templates/browser/graph_view.html` — removed carousel include and `.carousel-view-body` wrapper
- `backend/app/templates/browser/view_toolbar.html` — added model-declared variant dropdown
- `backend/app/views/router.py` — replaced `all_specs` carousel logic with `model_view_specs` in all endpoints
- `frontend/static/js/workspace.js` — removed `switchCarouselView()`, `restoreCarouselView()`, and exports
- `frontend/static/css/views.css` — removed carousel CSS, added `.view-variant-select` styling
