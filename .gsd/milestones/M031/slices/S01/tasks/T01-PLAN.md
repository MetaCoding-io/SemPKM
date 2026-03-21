---
estimated_steps: 9
estimated_files: 8
---

# T01: Remove carousel tab bar and add model-declared variant dropdown

**Slice:** S01 — Carousel Removal + View Scope Binding
**Milestone:** M031

## Description

Remove the carousel tab bar from all view templates, JS, and CSS. This is the highest-risk change in the slice because the carousel is currently the ONLY way to access model-declared ViewSpecs when a type filter pill is active (VIEW-05). Per decision D284, model-declared view variants move to a dropdown in the view toolbar.

The carousel system consists of:
- `carousel_tab_bar.html` — the tab bar partial template
- `.carousel-view-body` wrapper divs in table/cards/graph view templates
- `switchCarouselView()` and `restoreCarouselView()` JS functions in `workspace.js`
- Carousel CSS in `views.css`
- `all_specs` carousel-building logic in `views/router.py` `generic_view()`
- `sempkm_carousel_view` localStorage persistence

The replacement is a `<select>` dropdown in `view_toolbar.html` that appears when model-declared ViewSpecs exist for the currently selected type. Selecting a variant navigates to the model-declared view's dedicated endpoint.

**Skill:** No special skills needed — this is template/JS/CSS surgery.

## Steps

1. **Remove carousel includes from view templates.** In `table_view.html`, `cards_view.html`, and `graph_view.html`:
   - Remove the line `{% include "browser/carousel_tab_bar.html" %}`
   - Remove the `<div class="carousel-view-body">` opening tag (line after the carousel include)
   - Remove the matching closing `</div>` at the very end of each template (the last `</div>` in each file)

2. **Remove carousel-building logic from router.** In `backend/app/views/router.py` `generic_view()`:
   - Remove the `all_specs: list[ViewSpec] = []` block and the `if type_iri:` block that builds `all_specs` with generic specs + model-declared specs (~10 lines, appears 3 times in the table/card/graph branches)
   - Instead, add: `model_view_specs = await view_spec_service.get_view_specs_for_type(type_iri) if type_iri else []`
   - Replace `"all_specs": all_specs` with `"model_view_specs": model_view_specs` in all three context dicts
   - Also remove `all_specs` from the non-generic table/card/graph view endpoints (they pass `all_specs` too — check `table_view()`, `cards_view()`, `graph_view()` functions). In these endpoints, set `model_view_specs = []` since they already show a specific model-declared view.

3. **Add variant dropdown to view toolbar.** In `backend/app/templates/browser/view_toolbar.html`:
   - After the `<span class="view-label">` and before the `<div class="view-toolbar-right">`, add a variant dropdown:
   ```html
   {% if model_view_specs is defined and model_view_specs | length > 0 %}
   <select class="view-variant-select" onchange="if(this.value) openViewTab(this.value, this.options[this.selectedIndex].dataset.renderer)">
       <option value="" selected>— View Variants —</option>
       {% for vs in model_view_specs %}
       <option value="{{ vs.spec_iri }}" data-renderer="{{ vs.renderer_type }}">{{ vs.label }}</option>
       {% endfor %}
   </select>
   {% endif %}
   ```
   - The `openViewTab()` function already exists in `workspace.js` and opens a model-declared view in a dockview tab.

4. **Remove carousel JS from workspace.js.** Remove:
   - The `switchCarouselView()` function (starts with `function switchCarouselView(tabEl, specIri, rendererType, typeIri)` — approximately lines 2964-3030)
   - The `restoreCarouselView()` function (starts with `function restoreCarouselView(currentSpecIri, typeIri)` — approximately lines 3032-3050)
   - The `window.switchCarouselView = switchCarouselView;` export
   - The `window.restoreCarouselView = restoreCarouselView;` export
   - The comment `// Handle generic view IRIs (from carousel or reopening tabs)` in `loadViewContent()` — update to just say `// Handle generic view IRIs`
   - Any `localStorage.getItem('sempkm_carousel_view')` or `localStorage.setItem('sempkm_carousel_view', ...)` references

5. **Remove carousel CSS from views.css.** Remove these blocks:
   - `.carousel-tab-bar { ... }` (~8 lines)
   - `.carousel-tab { ... }` (~12 lines)
   - `.carousel-tab:hover { ... }` (~4 lines)
   - `.carousel-tab.active { ... }` (~5 lines)
   - `.carousel-view-body { ... }` (~5 lines)
   - `.view-loading-indicator { ... }` (~12 lines)
   - `.view-loading-spinner { ... }` (~8 lines)
   - `@keyframes carousel-spin { ... }` (~3 lines)

6. **Add CSS for variant dropdown.** In `views.css`, add styling for `.view-variant-select`:
   ```css
   .view-variant-select {
       padding: 4px 8px;
       font-size: 0.8rem;
       border: 1px solid var(--color-border);
       border-radius: 4px;
       background: var(--color-surface);
       color: var(--color-text);
       cursor: pointer;
       margin-left: 8px;
   }
   ```

7. **Delete the carousel_tab_bar.html template file.** Remove `backend/app/templates/browser/carousel_tab_bar.html`.

8. **Update non-generic view endpoints.** In `views/router.py`, for the dedicated `table_view()`, `cards_view()`, and `graph_view()` endpoints:
   - Replace `"all_specs": all_specs` with `"model_view_specs": []` in their context dicts (these endpoints serve a specific model-declared view, so no variant dropdown needed)
   - Remove the `all_specs = await view_spec_service.get_view_specs_for_type(spec.target_class)` calls from these endpoints

9. **Verify no carousel references remain.** Run grep commands to confirm complete removal.

## Must-Haves

- [ ] No `carousel_tab_bar.html` include in any template
- [ ] No `.carousel-view-body` wrapper div in any view template
- [ ] `switchCarouselView()` and `restoreCarouselView()` functions deleted from workspace.js
- [ ] `window.switchCarouselView` and `window.restoreCarouselView` exports deleted
- [ ] Carousel CSS fully removed from views.css
- [ ] `carousel_tab_bar.html` file deleted
- [ ] `sempkm_carousel_view` localStorage references removed
- [ ] Model-declared variant dropdown appears in toolbar when type with variants is selected
- [ ] Selecting a variant from dropdown opens the model-declared view

## Verification

- `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/views.css` returns zero results
- `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" frontend/static/js/` returns zero results
- `ls backend/app/templates/browser/carousel_tab_bar.html` returns "No such file"
- The three view templates (table, cards, graph) render without errors when loaded via htmx

## Inputs

- `backend/app/templates/browser/carousel_tab_bar.html` — the carousel partial to delete
- `backend/app/templates/browser/table_view.html` — includes carousel, has `.carousel-view-body` wrapper
- `backend/app/templates/browser/cards_view.html` — includes carousel, has `.carousel-view-body` wrapper
- `backend/app/templates/browser/graph_view.html` — includes carousel, has `.carousel-view-body` wrapper
- `backend/app/templates/browser/view_toolbar.html` — will gain variant dropdown
- `backend/app/views/router.py` — has `all_specs` carousel logic in `generic_view()` and dedicated view endpoints
- `frontend/static/js/workspace.js` — has `switchCarouselView()`, `restoreCarouselView()`, and their exports
- `frontend/static/css/views.css` — has carousel CSS rules

## Expected Output

- `backend/app/templates/browser/carousel_tab_bar.html` — deleted
- `backend/app/templates/browser/table_view.html` — no carousel include, no `.carousel-view-body` wrapper
- `backend/app/templates/browser/cards_view.html` — no carousel include, no `.carousel-view-body` wrapper
- `backend/app/templates/browser/graph_view.html` — no carousel include, no `.carousel-view-body` wrapper
- `backend/app/templates/browser/view_toolbar.html` — has model-declared variant dropdown
- `backend/app/views/router.py` — `all_specs` replaced with `model_view_specs`, no carousel logic
- `frontend/static/js/workspace.js` — no carousel functions or localStorage references
- `frontend/static/css/views.css` — no carousel CSS, has `.view-variant-select` style
