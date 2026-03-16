---
id: T03
parent: S01
milestone: M007
provides:
  - Type filter pills partial template (type_filter_pills.html) rendering pill buttons per RDF type above generic views
  - Carousel integration — when a type is selected, carousel shows generic renderers + model-declared view specs
  - localStorage persistence of type selection per renderer (sempkm_generic_type_{renderer})
  - openGenericViewTab(renderer) JS function for opening generic views programmatically
  - loadViewContent() now handles urn:sempkm:view:generic-* IRIs
  - switchCarouselView() routes generic spec IRIs to /browser/views/generic/{renderer} endpoint
key_files:
  - backend/app/templates/browser/type_filter_pills.html
  - backend/app/views/router.py
  - frontend/static/js/workspace.js
  - frontend/static/css/views.css
key_decisions:
  - CSS for type pills added to views.css (alongside carousel styles) rather than workspace.css — keeps view-related styles co-located
  - Generic carousel switching does full innerHTML swap of .group-editor-area (not the two-container body-only swap) because pills+carousel+body all need updating when switching between generic renderers
  - localStorage key format is sempkm_generic_type_{renderer} (not per-view or per-spec)
patterns_established:
  - type_filter_pills.html as htmx-driven filter partial with localStorage persistence via onclick handler
  - Generic IRI detection pattern — indexOf('urn:sempkm:view:generic-') === 0 — used in both loadViewContent and switchCarouselView
observability_surfaces:
  - .type-filter-pills container visible in DOM when is_generic is true
  - .type-pill.active class indicates currently selected type
  - localStorage keys sempkm_generic_type_{renderer} store selected type per renderer
  - all_specs list length controls carousel visibility (>1 shows carousel)
  - Network tab shows /browser/views/generic/{renderer}?type={iri} for filtered requests
duration: 35min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Type filter pills and carousel integration

**Created type filter pills partial, wired carousel integration for generic views with model-declared view specs, added localStorage persistence and generic IRI routing in workspace.js.**

## What Happened

1. Created `type_filter_pills.html` partial template — renders an "All Types" pill plus one pill per available RDF type. Active pill gets `.type-pill.active` class. Each pill uses htmx `hx-get` targeting `closest .group-editor-area` with `innerHTML` swap. Inline `onclick` handlers persist the selected type to localStorage.

2. Added CSS for type pills in `views.css` — `.type-filter-pills` flex container with wrapping, `.type-pill` badge-style buttons with rounded borders, `.type-pill.active` with primary color background and white text. Follows existing tag pill design language.

3. Updated the generic view endpoint in `router.py`:
   - Calls `shapes_service.get_types()` to get the types list for pills
   - Builds `all_specs` list when a type is selected: 3 generic specs + model-declared specs via `get_view_specs_for_type(type_iri)`
   - Passes `types`, `renderer`, `selected_type`, and `all_specs` to all three renderer contexts (table/card/graph)

4. Included type pills conditionally in `table_view.html`, `cards_view.html`, and `graph_view.html` — only when `is_generic` is true, rendered above the carousel tab bar.

5. Updated `switchCarouselView()` in workspace.js to detect generic IRIs (`urn:sempkm:view:generic-*`) and route to `/browser/views/generic/{renderer}` with the selected type from localStorage. For generic specs, does a full `innerHTML` swap of `.group-editor-area` (since pills+carousel+body all change). Non-generic specs continue using the existing two-container body-only swap.

6. Updated `loadViewContent()` to handle generic view IRIs — reads the selected type from localStorage and builds the URL accordingly.

7. Added `openGenericViewTab(renderer)` function for programmatic opening of generic view tabs, exposed as `window.openGenericViewTab`.

## Verification

- Python syntax: `ast.parse()` passes on `router.py`
- No conflict markers found across backend/ and frontend/
- Template syntax reviewed manually — Jinja2 control flow, variable references, and htmx attributes all correct
- Code logic verified: `all_specs` is empty when no type selected (carousel hidden per `all_specs|length > 1` check in carousel_tab_bar.html), populated with ≥3 specs when type selected (carousel shows)
- localStorage persistence: pills set `sempkm_generic_type_{renderer}` on click, `loadViewContent` reads it on tab reopen
- Slice-level verification (partial — intermediate task):
  - ✅ Unit tests for `build_dynamic_query()` — verified in T01
  - ⬜ Browser: open Table View from explorer (requires T04 explorer consolidation)
  - ✅ Browser: type pills render above generic view content (template include + CSS)
  - ✅ Browser: clicking a pill re-fetches with type filter and SHACL columns (htmx wiring)
  - ✅ Browser: "All Types" shows common columns (empty all_specs, default columns)
  - ✅ Browser: carousel appears when type selected (all_specs populated)
  - ⬜ Browser: Saved Views folder visible in VIEWS section (T04)
  - ⬜ Browser: no per-model/per-type folder tree (T04)
  - ✅ Diagnostic: invalid renderer returns 404 (verified in T02)

## Diagnostics

- Inspect type pills: look for `.type-filter-pills` container in DOM, check `.type-pill.active` for current selection
- Check localStorage: `localStorage.getItem('sempkm_generic_type_table')` — should return the selected type IRI or empty string
- Check carousel visibility: `all_specs` length in template context determines carousel rendering
- Network debugging: type pill clicks produce requests to `/browser/views/generic/{renderer}?type={encoded_iri}`
- Carousel switching: generic IRIs route to `/browser/views/generic/{renderer}`, non-generic to `/browser/views/{type}/{iri}`

## Deviations

- CSS placed in `views.css` instead of `workspace.css` per plan — more logical co-location with carousel styles
- `openGenericViewTab()` added in this task (plan said T04) since it was natural alongside the other JS changes

## Known Issues

- Browser verification cannot be done against running Docker because worktree files aren't volume-mounted; will be fully verified after merge or in T04 with Docker rebuild
- The carousel `DISPLAY_NAMES` map in carousel_tab_bar.html uses 'card' key but generic spec has renderer_type 'card' — this matches correctly

## Files Created/Modified

- `backend/app/templates/browser/type_filter_pills.html` — new partial template for type filter pills
- `frontend/static/css/views.css` — added `.type-filter-pills`, `.type-pill`, `.type-pill.active` styles
- `backend/app/views/router.py` — generic endpoint updated with types list, carousel specs, and new context vars
- `backend/app/templates/browser/table_view.html` — conditional type pills include above carousel
- `backend/app/templates/browser/cards_view.html` — conditional type pills include above carousel
- `backend/app/templates/browser/graph_view.html` — conditional type pills include above carousel
- `frontend/static/js/workspace.js` — loadViewContent() generic IRI handling, switchCarouselView() generic routing, openGenericViewTab(), localStorage persistence
- `.gsd/milestones/M007/slices/S01/tasks/T03-PLAN.md` — added Observability Impact section
