---
estimated_steps: 5
estimated_files: 4
skills_used: []
---

# T02: Add autocomplete for Target Class IRI and Object IRI fields

**Slice:** S06 — Dashboard & Workflow Builder UX
**Milestone:** M031

## Description

Replace the raw text inputs for Target Class IRI (in dashboard create-form block and workflow form step) and Object IRI (in dashboard object-embed block) with search-as-you-type autocomplete. This requires a new JSON endpoint for class search and JavaScript autocomplete widgets in both builders.

## Steps

1. **Add a `/browser/class-search` JSON endpoint** in `backend/app/browser/search.py`. This endpoint wraps `OntologyService.search_classes(query)` (which already exists at `backend/app/ontology/service.py` line 931) and returns a JSON list of `{iri, label}` objects. It needs `request.app.state.ontology_service` and a `q` query parameter. Register it on the existing `search_router`. Implementation:
   ```python
   @search_router.get("/class-search")
   async def class_search(
       request: Request,
       q: str = "",
       user: User = Depends(get_current_user),
   ):
       """JSON search for RDF classes by label. Used by builder autocomplete."""
       if not q.strip():
           return JSONResponse(content=[], status_code=200)
       ontology_service = request.app.state.ontology_service
       try:
           classes = await ontology_service.search_classes(q.strip())
       except Exception:
           return JSONResponse(content=[], status_code=200)
       return JSONResponse(
           content=[{"iri": c["iri"], "label": c["label"]} for c in classes],
           status_code=200,
       )
   ```
   Add `from starlette.responses import JSONResponse` if not already imported.

2. **Add autocomplete widget for Target Class IRI in the dashboard builder.** In `backend/app/templates/browser/dashboard_builder.html`, modify the `case 'create-form':` branch of `getTypeConfigHTML()`. Replace the plain text input with a `.reference-field` wrapper:
   ```javascript
   case 'create-form':
     return '<div class="block-config-fields">' +
       '<div class="form-field"><label>Target Class IRI</label>' +
       '<small class="field-help">The RDF type IRI for the object creation form (e.g. a class from your model).</small>' +
       '<div class="reference-field">' +
       '<input type="text" class="reference-search builder-class-search" placeholder="Search classes..." autocomplete="off" oninput="window._builderClassSearch(this)">' +
       '<input type="hidden" class="block-config-input" data-key="target_class" value="' + escapeAttr(config.target_class || '') + '">' +
       '<div class="suggestions-dropdown builder-suggestions"></div>' +
       '</div>' +
       (config.target_class ? '<span class="selected-reference-label">' + escapeAttr(config.target_class) + '</span>' : '') +
       '</div></div>';
   ```
   Add a global `window._builderClassSearch` debounced function that:
   - Gets the search input value
   - Fetches `/browser/class-search?q=<value>` after 300ms debounce
   - Renders suggestion items in the `.builder-suggestions` div (items with class, iri, label)
   - On suggestion click: sets the hidden input value, shows the selected label, clears suggestions

3. **Add autocomplete widget for Object IRI in the dashboard builder.** Same pattern as step 2, but for the `case 'object-embed':` branch. Use a different search endpoint: `/browser/search?type=&q=<value>` (empty type searches across all types). The existing search endpoint returns HTML, so either: (a) use the HTML response directly and swap into the suggestions div, or (b) create a parallel JSON endpoint. Since the builder uses vanilla JS (not htmx for its dynamic fields), the cleanest approach is to create a thin `/browser/object-search` JSON endpoint alongside `class-search` that queries the SPARQL store for objects matching a label query across all types. Alternatively, reuse the existing `/ontology/tbox/search` endpoint pattern but adapted for instances. Simplest approach: add a `format=json` query parameter to the existing `search_references` endpoint, or create a new endpoint. Create `/browser/object-search` that does a SPARQL query for instances matching a label filter:
   ```python
   @search_router.get("/object-search")
   async def object_search(
       request: Request,
       q: str = "",
       user: User = Depends(get_current_user),
       client: TriplestoreClient = Depends(get_triplestore_client),
       label_service: LabelService = Depends(get_label_service),
   ):
       """JSON search for objects by label. Used by builder autocomplete."""
       if not q.strip():
           return JSONResponse(content=[], status_code=200)
       # SPARQL: find instances matching label regex, limit 15
       escaped = _sparql_escape(q.strip())
       sparql = f"""SELECT DISTINCT ?s ?label WHERE {{
           ?s a ?type .
           ?s rdfs:label|dcterms:title|skos:prefLabel|schema:name ?label .
           FILTER(REGEX(STR(?label), "{escaped}", "i"))
       }} LIMIT 15"""
       try:
           result = await client.query(sparql)
           bindings = result.get("results", {}).get("bindings", [])
           items = [{"iri": b["s"]["value"], "label": b["label"]["value"]} for b in bindings]
       except Exception:
           items = []
       return JSONResponse(content=items, status_code=200)
   ```
   Wire the `object-embed` block type to use `window._builderObjectSearch` with the same pattern as class search but hitting `/browser/object-search`.

4. **Add autocomplete for Target Class IRI in the workflow builder.** In `backend/app/templates/browser/workflow_builder.html`, modify the `case 'form':` branch of `getTypeConfigHTML()` with the same `.reference-field` pattern as the dashboard builder. Reuse the `/browser/class-search` endpoint. Add a `window._wfBuilderClassSearch` debounced function (or share a common implementation via a helper).

5. **Ensure CSS works for autocomplete in builder context.** Check that `.reference-field` and `.suggestions-dropdown` styles from `frontend/static/css/forms.css` work inside `.dashboard-builder` and `.workflow-builder`. The `.suggestions-dropdown` needs `position: absolute`, `z-index: 9999`, and the `.reference-field` wrapper needs `position: relative`. These are already defined in `forms.css`. If the builder's `.block-config-fields` or parent elements have `overflow: hidden`, the dropdown will be clipped — check and add `overflow: visible` if needed. Also add a `.selected-reference-label` style for showing the currently selected IRI as a readable chip/badge, and a `.builder-suggestions .suggestion-item` style if not inherited.

## Must-Haves

- [ ] `/browser/class-search?q=...` returns JSON `[{iri, label}]` from ontology service
- [ ] `/browser/object-search?q=...` returns JSON `[{iri, label}]` from SPARQL store
- [ ] Dashboard builder Target Class IRI field has search-as-you-type autocomplete
- [ ] Dashboard builder Object IRI field has search-as-you-type autocomplete
- [ ] Workflow builder Target Class IRI field has search-as-you-type autocomplete
- [ ] Selecting a suggestion sets the hidden input value (data-key is preserved for save)
- [ ] Autocomplete dropdown is positioned correctly (not clipped by overflow)

## Verification

- `grep -q 'class-search' backend/app/browser/search.py` succeeds (endpoint exists)
- `grep -q 'object-search' backend/app/browser/search.py` succeeds (endpoint exists)
- `grep -q 'class-search' backend/app/templates/browser/dashboard_builder.html` succeeds
- `grep -q 'class-search' backend/app/templates/browser/workflow_builder.html` succeeds
- `grep -q 'object-search' backend/app/templates/browser/dashboard_builder.html` succeeds
- `python3 -c "import ast; ast.parse(open('backend/app/browser/search.py').read())"` succeeds (valid Python)

## Inputs

- `backend/app/browser/search.py` — existing search router with `search_references` and `tag_suggestions`
- `backend/app/ontology/service.py` — has `search_classes()` at line 931
- `backend/app/templates/browser/dashboard_builder.html` — T01 output with help text added
- `backend/app/templates/browser/workflow_builder.html` — T01 output with help text and simplified view step
- `frontend/static/css/forms.css` — has `.reference-field` and `.suggestions-dropdown` styles

## Expected Output

- `backend/app/browser/search.py` — updated with `/browser/class-search` and `/browser/object-search` JSON endpoints
- `backend/app/templates/browser/dashboard_builder.html` — target_class and object_iri fields now use autocomplete widgets
- `backend/app/templates/browser/workflow_builder.html` — target_class field now uses autocomplete widget
- `frontend/static/css/forms.css` — minor additions for `.selected-reference-label` and builder-context dropdown if needed
