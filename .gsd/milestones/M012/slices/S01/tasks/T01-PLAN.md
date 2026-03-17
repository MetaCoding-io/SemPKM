---
estimated_steps: 6
estimated_files: 5
---

# T01: Wire predicate labels and helptext tooltips into event detail view

**Slice:** S01 — Event Log Polish — Labels, Helptext & Autocomplete
**Milestone:** M012

## Description

The event log detail view currently displays raw predicate IRIs (e.g., `dcterms:title` or the local name `title`) extracted via Jinja2 string splitting. This task wires human-readable label resolution and SHACL-derived helptext tooltips into the event detail view.

Three changes are needed:
1. A new `ShapesService.get_helptext_for_predicates(iris)` method that extracts `sempkm:editHelpText` / `sh:description` for given predicate IRIs
2. Backend route changes to inject resolved labels and helptext into the event detail template context
3. Template updates to render human-readable labels with helptext tooltips

## Steps

1. **Add `get_helptext_for_predicates()` to `ShapesService`** in `backend/app/services/shapes.py`:
   - Method signature: `async def get_helptext_for_predicates(self, predicate_iris: list[str]) -> dict[str, str]`
   - Reuse `_fetch_shapes_graph()` to get the shapes Graph (already cached if called before)
   - Iterate all `sh:PropertyShape` nodes in the graph
   - For each, check if `sh:path` matches any of the requested predicate IRIs
   - Extract `sempkm:editHelpText` first (the `SEMPKM_EDIT_HELPTEXT` constant already exists at module level), fall back to `sh:description`
   - Return `{predicate_iri: helptext_string}` — only include predicates that have helptext
   - Wrap in try/except, log warning on failure, return empty dict (graceful degradation)

2. **Add `get_helptext_for_predicates()` to `ShapesService`** — also add a companion `get_labels_for_predicates()` method:
   - Method signature: `async def get_labels_for_predicates(self, predicate_iris: list[str]) -> dict[str, str]`
   - Iterate PropertyShapes, for matching `sh:path` extract `sh:name` → `rdfs:label` on path → local name
   - This gives SHACL-aware predicate labels (e.g., "Title" from `sh:name` on the PropertyShape targeting `dcterms:title`)
   - **Important**: The `LabelService.resolve_batch()` resolves **object** labels from `urn:sempkm:current` graph. Predicate IRIs (like `dcterms:title`) are **vocabulary terms** — they live in ontology/shapes graphs, not the current graph. So `LabelService` won't find labels for them. The ShapesService approach is the right one.

3. **Update `event_detail()` route** in `backend/app/browser/events.py`:
   - Add `shapes_service: ShapesService = Depends(get_shapes_service)` parameter
   - Add the import: `from app.dependencies import get_shapes_service` (add to existing import block)
   - After getting `detail`, collect all predicate IRIs:
     ```python
     pred_iris = list(detail.new_values.keys())
     pred_iris.extend(p for _, p, _ in detail.data_triples if p not in pred_iris)
     ```
   - Call `predicate_labels = await shapes_service.get_labels_for_predicates(pred_iris)`
   - Call `predicate_helptext = await shapes_service.get_helptext_for_predicates(pred_iris)`
   - For any predicates not found in shapes, fall back to `LabelService.resolve_batch()` for the remaining IRIs
   - Add `label_service: LabelService = Depends(get_label_service)` parameter
   - Pass `predicate_labels` and `predicate_helptext` to the template context dict

4. **Update `event_detail.html` template** in `backend/app/templates/browser/event_detail.html`:
   - In the property diff table (the `{% for pred_iri, new_val in detail.new_values.items() %}` loop):
     - Replace: `{{ pred_iri.split('/')[-1].split('#')[-1] }}`
     - With: `{{ predicate_labels.get(pred_iri, pred_iri.split('/')[-1].split('#')[-1]) }}`
     - Add `title` attribute: if helptext exists show that, otherwise show the full IRI for transparency
     - Pattern: `title="{{ predicate_helptext.get(pred_iri, pred_iri) }}"`
   - In the creation display (the `{% for s, p, o in detail.data_triples[:10] %}` loop):
     - Same replacement: `{{ predicate_labels.get(p, p.split('/')[-1].split('#')[-1]) }}`
     - Add title attribute same way
   - Add a CSS class `has-helptext` when helptext exists to show a visual indicator

5. **Add CSS for helptext indicator** in `frontend/static/css/workspace.css`:
   - `.diff-pred-label` gets `cursor: help` when it has a `title` attribute
   - `.diff-pred-label.has-helptext` gets a dotted underline to indicate hoverable helptext
   - Keep it subtle — `text-decoration: underline dotted; text-underline-offset: 2px;`

6. **Also resolve predicate labels in event_log list view**: In the `event_log()` route, the operation types are already shown as badges. The predicate values don't appear in the list view currently, so no changes needed there. But verify that `labels` dict (for affected IRIs) is already being used correctly in the list template.

## Must-Haves

- [ ] `ShapesService.get_helptext_for_predicates(iris)` returns `{predicate_iri: helptext}` from SHACL annotations
- [ ] `ShapesService.get_labels_for_predicates(iris)` returns `{predicate_iri: human_label}` from SHACL `sh:name`
- [ ] `event_detail()` route passes `predicate_labels` and `predicate_helptext` to template
- [ ] Event detail Property column shows "Title" not "dcterms:title" or "title"
- [ ] Hovering a predicate label shows helptext tooltip (or full IRI if no helptext)
- [ ] Graceful degradation: if shapes query fails, falls back to local name extraction

## Verification

- `cd backend && python -m pytest tests/ -v -k "shapes"` — existing shapes tests still pass
- Start Docker stack → create an object → edit its title → open event log → click Diff → "Property" column shows "Title" not "title" or "dcterms:title"
- Hover the "Title" label → tooltip shows helptext from SHACL annotations
- For predicates without SHACL shapes (e.g., `rdf:type`), tooltip shows the full IRI

## Inputs

- `backend/app/services/shapes.py` — existing `ShapesService` with `_fetch_shapes_graph()`, `PropertyShape.helptext`, `SEMPKM_EDIT_HELPTEXT` constant
- `backend/app/browser/events.py` — existing `event_detail()` route returning `EventDetail` to template
- `backend/app/templates/browser/event_detail.html` — existing template with raw IRI splitting
- `backend/app/dependencies.py` — existing `get_shapes_service`, `get_label_service` dependency providers

## Observability Impact

- **New log signals:** `logger.warning` in `get_helptext_for_predicates()` and `get_labels_for_predicates()` on shapes graph query failure — enables diagnosing degraded label resolution without stack traces in production
- **Inspection surfaces:** Every `<span class="diff-pred-label">` in event detail renders a `title` attribute containing either SHACL helptext or the full predicate IRI — hover any label to verify resolution worked
- **Failure visibility:** If shapes service fails, predicates fall back to local name extraction (e.g., "title" from `dcterms:title`) — visually distinguishable from resolved labels ("Title" with capital T and dotted underline)
- **Agent diagnostic:** grep for `"Failed to resolve predicate"` in backend logs to check for shapes service errors at runtime

## Expected Output

- `backend/app/services/shapes.py` — two new methods: `get_helptext_for_predicates()` and `get_labels_for_predicates()`
- `backend/app/browser/events.py` — `event_detail()` enhanced with shapes/label resolution, template context includes `predicate_labels` and `predicate_helptext`
- `backend/app/templates/browser/event_detail.html` — uses resolved labels with helptext tooltips
- `frontend/static/css/workspace.css` — helptext indicator styling on `.diff-pred-label`
