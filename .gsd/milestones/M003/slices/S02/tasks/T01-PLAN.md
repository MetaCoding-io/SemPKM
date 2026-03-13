---
estimated_steps: 5
estimated_files: 3
---

# T01: SPARQL queries, hierarchy handler, and children endpoint

**Slice:** S02 — Hierarchy Explorer Mode
**Milestone:** M003

## Description

Replace the `_handle_hierarchy` placeholder handler with a real implementation that queries the RDF4J triplestore for root objects (those without `dcterms:isPartOf`) and renders them as expandable tree nodes. Add a new `GET /browser/explorer/children?parent={iri}` endpoint for lazy child expansion. Create two Jinja2 templates (`hierarchy_tree.html`, `hierarchy_children.html`) that reuse the existing `.tree-node`/`.tree-leaf`/`.tree-children` CSS classes and htmx patterns.

## Steps

1. **Write the root objects SPARQL query and replace `_handle_hierarchy`.**
   In `workspace.py`, replace the placeholder handler with a real implementation:
   - Query root objects: `SELECT ?obj ?type WHERE { GRAPH <urn:sempkm:current> { ?obj a ?type . FILTER NOT EXISTS { ?obj dcterms:isPartOf ?parent . } } }` — uses `FILTER NOT EXISTS` (not OPTIONAL) per research pitfalls.
   - De-duplicate objects that have multiple types (pick first type per object).
   - Resolve labels via `label_service.resolve_batch()` and icons via `icon_svc.get_type_icon()`.
   - Update handler signature to accept `label_service` parameter (add `LabelService` dependency to `explorer_tree` endpoint and pass it through).
   - Render `hierarchy_tree.html` with the root objects list.
   - Add DEBUG log: `"Hierarchy roots query returned %d objects"`.
   - Empty results render an empty-state message in the template.

2. **Add the `/browser/explorer/children` endpoint.**
   New GET endpoint on `workspace_router`:
   - Query param: `parent` (required, IRI string).
   - Validate with `_validate_iri()` — return 400 on invalid.
   - SPARQL: `SELECT ?obj ?type WHERE { GRAPH <urn:sempkm:current> { ?obj dcterms:isPartOf <{parent_iri}> . ?obj a ?type . } }`
   - De-duplicate multi-typed objects, resolve labels and icons.
   - Render `hierarchy_children.html`.
   - Add DEBUG log: `"Hierarchy children query for %s returned %d objects"`.
   - Dependencies: `get_current_user`, `get_label_service`, `get_icon_service`.

3. **Create `hierarchy_tree.html` template.**
   Root-level rendering template:
   - If objects exist: render each as a `.tree-node` with `hx-get="/browser/explorer/children?parent={{ obj.iri | urlencode }}"`, `hx-trigger="click once"`, `hx-target="#hierarchy-children-{{ safe_id }}"`, `hx-swap="innerHTML"`.
   - Each node has a toggle arrow (`.tree-toggle`), per-type icon via Lucide `data-lucide="{{ obj.icon }}"`, and a label span with `onclick="handleTreeLeafClick(event, '{{ obj.iri }}', '{{ obj.label }}')"` (with `event.stopPropagation()` to prevent the node click from bubbling).
   - Each node followed by `<div id="hierarchy-children-{{ safe_id }}" class="tree-children"></div>`.
   - `safe_id` generated same way as `nav_tree.html`: `iri | replace(':', '_') | replace('/', '_') | replace('#', '_') | replace('.', '_')`.
   - If no objects: render `.tree-empty` with message "No hierarchy relationships found. Assign dcterms:isPartOf on objects to organize them here."
   - Add `data-testid="hierarchy-node"` on each node and `data-iri="{{ obj.iri }}"`.

4. **Create `hierarchy_children.html` template.**
   Child nodes template (rendered by the children endpoint):
   - Same structure as `hierarchy_tree.html` nodes — each child is a `.tree-node` (any node could itself have children).
   - Uses the same htmx lazy-loading pattern for recursive expansion.
   - If no children: render `.tree-empty` with "No children".
   - Add `data-testid="hierarchy-node"` on each node.

5. **Wire `label_service` into the `explorer_tree` dispatcher.**
   The `explorer_tree` endpoint already has `shapes_service` and `icon_svc`. Add `label_service: LabelService = Depends(get_label_service)` and pass it to the handler call. Update the handler dispatch call to include `label_service=label_service`. The `_handle_by_type` and `_handle_by_tag` handlers accept `**_kwargs` so they'll ignore the extra param.

## Must-Haves

- [ ] `_handle_hierarchy` queries triplestore for root objects with `FILTER NOT EXISTS { ?obj dcterms:isPartOf ?parent }`
- [ ] Children endpoint validates parent IRI and returns 400 for invalid
- [ ] Both SPARQL queries scoped to `GRAPH <urn:sempkm:current>`
- [ ] Labels resolved via `LabelService.resolve_batch()`
- [ ] Per-type icons resolved via `IconService.get_type_icon()`
- [ ] Templates reuse `.tree-node`/`.tree-toggle`/`.tree-children`/`.tree-leaf` CSS classes
- [ ] Hierarchy nodes have `hx-trigger="click once"` for lazy child loading
- [ ] Label click calls `handleTreeLeafClick()` to open object tab
- [ ] Empty state shows descriptive message, not generic "No models installed"

## Verification

- `GET /browser/explorer/tree?mode=hierarchy` → 200, HTML content (empty-state message with seed data since no `dcterms:isPartOf` triples exist)
- `GET /browser/explorer/children?parent=http://example.org/valid` → 200, HTML (empty children)
- `GET /browser/explorer/children?parent=not-a-valid-iri` → 400
- `GET /browser/explorer/tree?mode=by-type` still works (no regression)
- `GET /browser/nav-tree` still works (backwards compat)
- Existing unit tests `cd backend && python -m pytest tests/test_explorer_modes.py -v` still pass (may need updates if handler signature changed)

## Observability Impact

- Signals added/changed: DEBUG log `"Hierarchy roots query returned %d objects"` and `"Hierarchy children query for %s returned %d objects"` in `app.browser.workspace` logger
- How a future agent inspects this: `GET /browser/explorer/tree?mode=hierarchy` directly testable; `GET /browser/explorer/children?parent={iri}` directly testable; DEBUG logs visible with `LOG_LEVEL=DEBUG`
- Failure state exposed: HTTP 400 with `{"detail": "Invalid IRI"}` for bad parent param; SPARQL query errors logged with `exc_info=True` and fallback to empty results

## Inputs

- `backend/app/browser/workspace.py` — `_handle_hierarchy` placeholder (line 52), `EXPLORER_MODES` registry (line 80), `explorer_tree` endpoint (line 150), `tree_children` endpoint (line 178) as reference
- `backend/app/templates/browser/nav_tree.html` — reference for `.tree-node` htmx pattern
- `backend/app/templates/browser/tree_children.html` — reference for leaf node pattern with `handleTreeLeafClick`
- S01 T01-T04 summaries — handler signature pattern (`async fn(request, shapes_service, icon_svc, **kwargs)`)

## Expected Output

- `backend/app/browser/workspace.py` — `_handle_hierarchy` replaced with real implementation; new `explorer_children` endpoint added; `explorer_tree` passes `label_service` to handlers
- `backend/app/templates/browser/hierarchy_tree.html` — new template for hierarchy root nodes
- `backend/app/templates/browser/hierarchy_children.html` — new template for hierarchy child nodes
