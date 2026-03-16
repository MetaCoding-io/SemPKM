---
estimated_steps: 7
estimated_files: 8
---

# T03: Type filter pills and carousel integration

**Slice:** S01 — Generic Views & Explorer Consolidation
**Milestone:** M007

## Description

Create the type filter pills partial template and wire carousel tab bar integration so that when a type pill is active in a generic view, SHACL-driven columns appear and model-declared view variants are shown in the carousel. Covers VIEW-03 (type pills) and VIEW-05 (carousel with model views).

## Steps

1. **Create `type_filter_pills.html` partial** at `backend/app/templates/browser/type_filter_pills.html`. Template context: `types` (list of dicts with `type_iri` and `label`), `selected_type` (str or empty), `renderer` (str — "table"/"card"/"graph"). Renders:
   - A container div `.type-filter-pills`
   - An "All Types" pill button — active when `selected_type` is empty. Uses `hx-get="/browser/views/generic/{renderer}"` (no type param), `hx-target="closest .group-editor-area"`, `hx-swap="innerHTML"`.
   - One pill per type — active when `selected_type == type_iri`. Uses `hx-get="/browser/views/generic/{renderer}?type={type_iri}"`, same target/swap.
   - Each pill shows the type label. Active pill gets `.type-pill.active` class.

2. **Add CSS for type pills** in `frontend/static/css/workspace.css`. Styles needed:
   - `.type-filter-pills` — flex container, gap, padding, wrapping, border-bottom separator
   - `.type-pill` — small button/badge style (similar to existing tag pills), border-radius, background, hover state
   - `.type-pill.active` — accent/primary color background, white text
   - Follow existing design language (check tag pill styles for reference)

3. **Update generic view endpoint** in `backend/app/views/router.py` to pass type pill data to templates. In the generic table/card/graph handler:
   - Call `shapes_service.get_types()` to get available types
   - Pass to template: `types=types_list`, `selected_type=type_param`, `renderer=renderer`, `is_generic=True`
   - Access to `ShapesService` — get it via DI dependency (check if `get_shapes_service` exists in `dependencies.py`, if not add it or use `request.app.state`)

4. **Include type pills in view templates**. In `table_view.html`, `cards_view.html`, and `graph_view.html`, add conditional include above the carousel bar:
   ```jinja2
   {% if is_generic | default(false) %}
   {% include "browser/type_filter_pills.html" %}
   {% endif %}
   ```
   This goes right before the existing `{% include "browser/carousel_tab_bar.html" %}` line.

5. **Carousel integration for generic views**. When a type is selected in a generic view:
   - The generic endpoint already calls `build_dynamic_query(type_iri)` which handles SHACL columns
   - Additionally, call `view_spec_service.get_view_specs_for_type(type_iri)` to get model-declared ViewSpecs
   - Build `all_specs` list: start with the 3 generic ViewSpecs (using their well-known IRIs), then append model-declared specs. Pass to template as `all_specs`.
   - The existing `carousel_tab_bar.html` renders tabs from `all_specs` — it will show generic renderers + model views.
   - When no type is selected: pass empty `all_specs` (carousel won't render — it checks `all_specs|length > 1`)
   - **Important**: The carousel's `switchCarouselView()` function calls `loadViewContent(specIri, rendererType)` which maps to `/browser/views/{type}/{iri}`. For generic specs (IRIs starting with `urn:sempkm:view:generic-`), the JS needs to route to `/browser/views/generic/{renderer}?type={selectedType}` instead. Add this mapping in the onclick of carousel tabs rendered for generic specs, or update `loadViewContent()` in `workspace.js` to detect generic IRIs.

6. **Update `loadViewContent()` in workspace.js** to handle generic view IRIs. Add cases before the default:
   ```javascript
   if (viewId.startsWith('urn:sempkm:view:generic-')) {
     var renderer = viewId.split('generic-')[1]; // 'table', 'cards', 'graph'
     var selectedType = localStorage.getItem('sempkm_generic_view_type_' + renderer) || '';
     url = '/browser/views/generic/' + renderer + (selectedType ? '?type=' + encodeURIComponent(selectedType) : '');
   }
   ```

7. **localStorage persistence for type selection**. Add JS to `type_filter_pills.html` (inline `<script>` block) or workspace.js:
   - On pill click (htmx `afterSwap` or via the pill's onclick): store `localStorage.setItem('sempkm_generic_view_type_' + renderer, selectedType)`
   - On page load of a generic view: read stored type and apply if present (the endpoint already accepts `?type=`, so this is about restoring state on re-open)
   - The pill template should read the stored type via a small inline `<script>` that sets the active class, OR the endpoint should read a cookie/query param. **Simpler**: the generic endpoint already receives `?type=` — if the tab reopens via `openGenericViewTab()`, the JS reads localStorage and passes the type in the URL. The pills themselves set localStorage on click via an htmx `hx-on::before-request` or a plain onclick handler.

## Must-Haves

- [ ] Type pills render above generic view content showing all available types + "All Types"
- [ ] Clicking a pill re-fetches the generic view filtered to that type with SHACL columns
- [ ] "All Types" pill shows common columns (label, type, created, modified)
- [ ] Carousel tab bar appears when a type is selected, showing model-declared views
- [ ] Carousel tab bar hidden when "All Types" is selected
- [ ] `loadViewContent()` routes generic IRIs correctly
- [ ] Type selection persists in localStorage per renderer

## Verification

- Browser: open generic Table View → type pills visible above table
- Browser: click a type pill (e.g. "Note") → table filters to Notes, columns change to SHACL properties
- Browser: with type selected, carousel bar appears with model-declared view tabs
- Browser: click a carousel tab for a model-declared view → that view loads
- Browser: click "All Types" → back to common columns, carousel disappears
- Browser: close and reopen Table View tab → same type filter is restored from localStorage

## Inputs

- `backend/app/views/router.py` — T02's generic view endpoint (needs types data added to context)
- `backend/app/views/service.py` — T01's `build_dynamic_query()`, `get_view_specs_for_type()`
- `backend/app/services/shapes.py` — `get_types()` returns `list[dict]` with type_iri and label
- `frontend/static/js/workspace.js` — `loadViewContent()` function (needs generic IRI handling)
- `backend/app/templates/browser/carousel_tab_bar.html` — existing carousel (consumed as-is, with extended `all_specs`)

## Expected Output

- `backend/app/templates/browser/type_filter_pills.html` — new partial template
- `frontend/static/css/workspace.css` — `.type-filter-pills`, `.type-pill` styles
- `backend/app/views/router.py` — generic endpoint updated with types context and carousel data
- `backend/app/templates/browser/table_view.html` — conditional type pills include
- `backend/app/templates/browser/cards_view.html` — conditional type pills include
- `backend/app/templates/browser/graph_view.html` — conditional type pills include
- `frontend/static/js/workspace.js` — `loadViewContent()` updated for generic IRIs, localStorage persistence

## Observability Impact

- **Type pills rendering**: Visible in the DOM as `.type-filter-pills` container above generic view content. Active pill has `.type-pill.active` class.
- **Type selection persistence**: Stored in `localStorage` as `sempkm_generic_type_{renderer}` keys. Inspect via browser DevTools → Application → Local Storage.
- **Carousel visibility**: When a type is selected, `all_specs` contains ≥3 entries (generic specs + model-declared), rendering the carousel tab bar. When "All Types" is active, `all_specs` is empty → no carousel.
- **Generic IRI routing**: `switchCarouselView()` detects `urn:sempkm:view:generic-*` and routes to `/browser/views/generic/{renderer}` instead of `/browser/views/{type}/{iri}`. Diagnostic: check network tab for the correct URL pattern.
- **Future agent inspection**: Check `.type-filter-pills` presence in rendered HTML. Check `all_specs` length in template context to verify carousel is shown/hidden correctly.
