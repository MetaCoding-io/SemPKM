# S02 — Research: Property Flip on Object Nodes

**Date:** 2026-03-15

## Summary

S02 adds a flip button to canvas object node headers that toggles between the markdown body and a compact SHACL-derived property table. This is a targeted feature with a clean backend + frontend split: a new JSON API endpoint (`GET /api/canvas/properties?iri=<IRI>`) returns property metadata, and the canvas JS adds a button + inline rendering + per-node cache.

The pattern is well-established. The existing `get_object()` handler in `objects.py` already queries `urn:sempkm:current` and `urn:sempkm:inferred` for `<IRI> ?p ?o`, resolves types, and calls `ShapesService.get_form_for_type()` — the new endpoint reuses the same queries but returns JSON instead of HTML. The canvas JS already delegates button clicks via `event.target.closest()` in `onLayerClick()` and rebuilds node HTML in `renderNodes()` — adding a flip button and conditional property table follows the exact same patterns.

No new libraries, no risky integration, no architectural novelty. The main implementation question is the JSON response shape and how much label resolution to include (predicate labels, reference IRI labels, type label). Including predicate labels and a type label keeps the frontend simple — no secondary label resolution needed.

## Recommendation

**Build backend endpoint first, then frontend flip logic.**

The backend endpoint is self-contained and unit-testable without Docker. Once it works, the frontend just needs: (1) a flip button in the node header, (2) a click handler that fetches/caches properties, (3) conditional rendering in `renderNodes()` that replaces the markdown div with a property table when `node.showProperties === true`, (4) serialization of `showProperties` in `getDocument()`/`applyDocument()`.

**JSON response should include resolved labels.** Return `{type_label, properties: [{name, value, path, source, datatype}]}` where `name` is the SHACL `sh:name` (already resolved by ShapesService). This avoids a second round-trip for label resolution on the frontend. For reference properties (IRIs), include the label inline from `LabelService.resolve_batch()`.

**Cache properties per-node in `state.propertyCache[nodeId]`.** Avoids re-fetching on every flip toggle. Cache is in-memory only — no persistence needed. Invalidation: none for v1 (properties are stable during a canvas session).

## Implementation Landscape

### Key Files

- `backend/app/canvas/router.py` (361 LOC) — Add `GET /api/canvas/properties?iri=<IRI>` endpoint. Import `get_shapes_service`, `get_label_service` from dependencies. Endpoint: validate IRI → query current+inferred graphs → resolve type → get SHACL form → build JSON response with resolved names and labels.

- `backend/app/services/shapes.py` (405 LOC) — `ShapesService.get_form_for_type(type_iri)` returns `NodeShapeForm` with `properties: list[PropertyShape]`. Each `PropertyShape` has `path`, `name`, `datatype`, `target_class`, `order`. This is the metadata source for the property table columns. **Read-only dependency — no changes needed.**

- `backend/app/browser/objects.py` (lines 78-165) — Reference implementation for the query pattern. Queries `urn:sempkm:current` for `<IRI> ?p ?o`, separates `rdf:type` and `urn:sempkm:body`, queries `urn:sempkm:inferred` for additional properties, deduplicates. The new endpoint follows the same pattern but returns JSON.

- `backend/app/dependencies.py` — Existing dependency providers: `get_shapes_service`, `get_label_service`, `get_triplestore_client`. Canvas router currently only imports `get_triplestore_client` and `get_view_spec_service` — add the two new imports.

- `frontend/static/js/canvas.js` (1399 LOC) — Changes in multiple functions:
  - `state` object: add `propertyCache: {}` (line ~11)
  - SVG icons: add `SVG_FLIP` (a rotate/flip icon, line ~42)
  - `renderNodes()` (line 816): add flip button in header HTML between expand and delete, add conditional property table vs markdown rendering based on `node.showProperties`
  - `onLayerClick()` (line 524): add handler for `.spatial-node-flip` click delegation
  - `getDocument()` (line 1143): serialize `showProperties` when true
  - `applyDocument()` (line 1166): restore `showProperties` with fallback to false/undefined

- `frontend/static/css/workspace.css` (line ~4908) — Add `.spatial-node-flip` to the existing button group (`.spatial-node-chevron, .spatial-node-expand, .spatial-node-delete`). Add `.spatial-node-properties` table styling (compact label/value grid). Add `.spatial-node-flip.is-flipped` active state color.

- `backend/tests/test_canvas_properties.py` (new) — Unit tests for the properties endpoint response shape, type resolution, label inclusion, IRI validation, graceful degradation for unknown types.

### Build Order

**1. Backend endpoint** — `GET /api/canvas/properties?iri=<IRI>` in `canvas/router.py`

This is the data source everything else depends on. Reuses the same query pattern as `get_object()` lines 78-165:
- Validate IRI via existing `_is_valid_iri()`
- Query `urn:sempkm:current` for `<IRI> ?p ?o`
- Extract `rdf:type` IRIs, separate `urn:sempkm:body`
- Query `urn:sempkm:inferred` for `<IRI> ?p ?o`, deduplicate vs current
- Call `ShapesService.get_form_for_type(type_iri)` for property metadata
- Resolve labels for reference IRI values via `LabelService.resolve_batch()`
- Return JSON: `{type_label, properties: [{name, path, value, datatype, source, ref_label?}]}`

Properties are ordered by SHACL `sh:order` (already sorted in `NodeShapeForm.properties`). Only properties with values are included. Inferred properties tagged with `source: "inferred"`. Properties not in the SHACL form but present in the graph are included with a local-name label (same as `object_read.html` does for inferred-only predicates).

**2. Backend unit tests** — `test_canvas_properties.py`

Pure-function tests that mock `ShapesService` and `TriplestoreClient`:
- Happy path: typed object with SHACL form → correct property list with names
- No SHACL form: properties returned with local-name labels
- Reference properties: IRI values include resolved labels
- Inferred properties: tagged with source=inferred
- Invalid IRI: 400 response
- Empty result: no properties for non-existent IRI
- Body predicate excluded from property list

**3. Frontend: flip button + click handler**

Add `SVG_FLIP` icon (a rotate icon from Lucide's repeat/refresh-cw family — inline SVG matching existing pattern). Add button in `renderNodes()` header between expand and delete:
```
'<button class="spatial-node-flip" type="button" title="Toggle properties">', SVG_FLIP, '</button>'
```

Add click handler in `onLayerClick()`:
```javascript
var flipBtn = event.target.closest('.spatial-node-flip');
if (flipBtn) {
  var flipNode = flipBtn.closest('.spatial-node');
  if (!flipNode) return;
  var nodeId = flipNode.dataset.nodeId;
  var model = findNode(nodeId);
  if (!model) return;
  model.showProperties = !model.showProperties;
  if (model.showProperties && !state.propertyCache[nodeId]) {
    // Fetch properties, cache, and re-render
    fetchNodeProperties(nodeId, model.uri);
  } else {
    renderNodes();
  }
  return;
}
```

New `fetchNodeProperties(nodeId, iri)` function (follows `fetchNodeBody` pattern):
```javascript
function fetchNodeProperties(nodeId, iri) {
  fetch('/api/canvas/properties?iri=' + encodeURIComponent(iri))
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (data) {
        state.propertyCache[nodeId] = data;
      }
      renderNodes();
    })
    .catch(function () { renderNodes(); });
}
```

**4. Frontend: property table rendering in `renderNodes()`**

In the node body section of `renderNodes()`, replace:
```javascript
(node.collapsed ? '' : '<div class="spatial-node-markdown">' + renderMarkdown(node.markdown || '') + '</div>')
```
With conditional logic:
```javascript
node.collapsed ? '' :
  (node.showProperties && state.propertyCache[node.id]
    ? buildPropertyTable(state.propertyCache[node.id])
    : '<div class="spatial-node-markdown">' + renderMarkdown(node.markdown || '') + '</div>')
```

New `buildPropertyTable(data)` function returns HTML string:
- `<div class="spatial-node-properties">` wrapper
- Type label header if available
- For each property: `<div class="prop-row"><span class="prop-label">{name}</span><span class="prop-value">{value}</span></div>`
- Tag values get `#` prefix pills, dates get formatted, booleans get ✓/✗, IRIs get ref labels

**5. Frontend: serialization in `getDocument()`/`applyDocument()`**

`getDocument()`: add `if (n.showProperties) serialized.showProperties = true;`
`applyDocument()`: add `if (n.showProperties) node.showProperties = true;`

**6. CSS styling**

Add `.spatial-node-flip` to the existing button rule. Add property table styles: compact grid, alternating row backgrounds, monospace values, overflow handling. Add `.spatial-node-flip.is-flipped` with accent color indicator.

### Verification Approach

**Unit tests:** `cd backend && .venv/bin/pytest tests/test_canvas_properties.py -v` — properties endpoint returns correct JSON shape, handles edge cases.

**Browser verification:** Docker Compose up → open workspace → Spatial Canvas → drag an object onto canvas → click flip button → verify property table appears with correct values → click flip again → verify markdown returns → save canvas → reload → verify flipped state persists.

**Specific checks:**
- Typed object (e.g. Note with tags, date, body) shows SHACL-ordered properties
- Untyped object shows properties with local-name labels
- Reference property values show resolved labels
- Inferred properties display with "inferred" indicator
- Property table scrolls within node height (doesn't expand the node beyond its set dimensions)
- Flip button shows visual active state when properties are showing
- Old canvas sessions (no `showProperties` field) load without errors

## Constraints

- **No iframe for property flip** (D126) — inline HTML table, not an iframe. The data is lightweight (10-30 key/value pairs).
- **renderNodes() rebuilds innerHTML every call** — property table HTML is rebuilt each time, but the data comes from `state.propertyCache[nodeId]` so no re-fetch. The dual-layer split (D124) doesn't affect property flip since it's regular HTML, not an iframe.
- **Property table must respect node height** — if the user has resized a node, the property table should scroll via `overflow-y: auto` rather than expanding the node.

## Common Pitfalls

- **SHACL body property appears in property list** — The `get_object()` handler explicitly detects `prop.name.lower() == "body"` and excludes it from the property table, using it for the markdown body instead. The new endpoint must do the same — otherwise the body text shows up as a property AND as the markdown content.
- **Multi-value properties** — Some properties (tags, references) have multiple values. The endpoint should return them as arrays per property path, not flatten to individual rows. The frontend table joins multiple values with commas or renders as pills.
- **Cache key is nodeId (IRI), not position** — If the same IRI appears on canvas twice (shouldn't happen, but defensive), the cache works correctly since `findNode()` returns the first match and nodeId === IRI in the current model.

## Sources

- Codebase: `canvas.js` (1399 LOC), `canvas/router.py` (361 LOC), `shapes.py` (405 LOC), `objects.py` property query pattern (lines 78-165), `object_read.html` property table template, `test_canvas_resize.py` test patterns
- Decisions: D126 (inline rendering not iframes), D124 (dual-layer for embeds, not property flip)
