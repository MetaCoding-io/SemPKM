# S02: Property Flip on Object Nodes

**Goal:** Object nodes on the spatial canvas have a flip button that toggles between markdown body and a compact SHACL-derived property table fetched from a lightweight JSON endpoint, with state persisted across save/load.
**Demo:** Open workspace → Spatial Canvas → drag an object onto canvas → click flip button in node header → see property table with real values → click flip again → markdown body returns → save canvas → reload → flipped state persists.

## Must-Haves

- `GET /api/canvas/properties?iri=<IRI>` endpoint returns SHACL-derived property JSON with resolved labels
- Flip button in object node header between expand and delete buttons
- Click handler toggles `node.showProperties`, fetches/caches properties on first flip
- Property table replaces markdown body when flipped, with type label header and compact label/value rows
- Body property excluded from property table (both `urn:sempkm:body` and SHACL body detection)
- Multi-value properties rendered as comma-separated or pill items
- Inferred properties tagged with source indicator
- `showProperties` serialized in `getDocument()`/`applyDocument()` for save/load persistence
- Flip button has visual active state when properties are showing
- Property table scrolls within node height via `overflow-y: auto`
- Old canvas sessions without `showProperties` field load without errors

## Proof Level

- This slice proves: integration (backend API → triplestore → SHACL → JSON → frontend rendering)
- Real runtime required: yes (Docker for browser verification against real triplestore data)
- Human/UAT required: no (browser automation sufficient)

## Verification

- `cd backend && .venv/bin/pytest tests/test_canvas_properties.py -v` — all unit tests pass
- Browser: open canvas → drag object → click flip → property table visible with correct values
- Browser: click flip again → markdown body returns
- Browser: save canvas → reload → flipped state persists
- Browser: old session without showProperties loads without errors

## Observability / Diagnostics

- Runtime signals: endpoint returns structured JSON with `type_label` and `properties` array; fetch errors in browser console
- Inspection surfaces: `GET /api/canvas/properties?iri=<IRI>` callable directly for debugging; `state.propertyCache` inspectable in browser console
- Failure visibility: endpoint returns 400 for invalid IRI, empty properties array for unknown IRI, browser console logs fetch failures
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `ShapesService.get_form_for_type()` (shapes.py), `LabelService.resolve_batch()` (dependencies.py), `TriplestoreClient.query()` (triplestore client), `_is_valid_iri()` (canvas/router.py), objects.py property query pattern (lines 78-165)
- New wiring introduced in this slice: `/api/canvas/properties` route registered in canvas router, `fetchNodeProperties()` function in canvas.js, `state.propertyCache` in-memory cache
- What remains before the milestone is truly usable end-to-end: S03 (live embeds), S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Backend properties endpoint and unit tests** `est:1h`
  - Why: The JSON endpoint is the data source for the property flip. It must exist and be correct before frontend work can consume it. Self-contained and testable without Docker.
  - Files: `backend/app/canvas/router.py`, `backend/tests/test_canvas_properties.py`
  - Do: Add `GET /api/canvas/properties?iri=<IRI>` to canvas router. Validate IRI via existing `_is_valid_iri()`. Query `urn:sempkm:current` and `urn:sempkm:inferred` for `<IRI> ?p ?o` (same pattern as objects.py lines 78-165). Resolve type via `rdf:type`, get SHACL form via `ShapesService.get_form_for_type()`. Build property list from SHACL form properties that have values, ordered by `sh:order`. Exclude body properties (both `urn:sempkm:body` and SHACL body detection via `prop.name.lower() == "body"`). Include unmatched graph properties with local-name labels. Tag inferred properties with `source: "inferred"`. Resolve IRI reference labels via `LabelService.resolve_batch()`. Return JSON: `{type_label, properties: [{name, path, value, values, datatype, source, ref_label?}]}`. Multi-value properties as arrays. Add new dependency imports (`get_shapes_service`, `get_label_service`). Write unit tests mocking `ShapesService`, `TriplestoreClient`, and `LabelService`: happy path typed object, no SHACL form fallback, reference label resolution, inferred tagging, invalid IRI 400, empty result, body exclusion.
  - Verify: `cd backend && .venv/bin/pytest tests/test_canvas_properties.py -v` — all tests pass
  - Done when: Endpoint returns correct JSON shape for typed objects, untyped objects, inferred properties, and edge cases. All unit tests green.

- [x] **T02: Frontend flip button, property table rendering, serialization, and CSS** `est:1.5h`
  - Why: Completes the user-facing feature — the flip button, fetch/cache, property table rendering, save/load persistence, and styling. Depends on T01's endpoint.
  - Files: `frontend/static/js/canvas.js`, `frontend/static/css/workspace.css`
  - Do: (1) Add `propertyCache: {}` to `state` object. (2) Add `SVG_FLIP` inline SVG constant (Lucide `repeat` or `arrow-left-right` — 2-arrow rotate icon matching existing icon pattern). (3) In `renderNodes()` header (line ~857), add flip button between expand and delete: `<button class="spatial-node-flip" type="button" title="Toggle properties">SVG_FLIP</button>`. Add `is-flipped` class when `node.showProperties` is true. (4) In `renderNodes()` body section, replace the unconditional markdown div with conditional: if `node.showProperties && state.propertyCache[node.id]`, call `buildPropertyTable(state.propertyCache[node.id])`, else render markdown. (5) Add `buildPropertyTable(data)` function returning HTML string — `.spatial-node-properties` wrapper, type label header, `.prop-row` divs with `.prop-label` and `.prop-value` spans. Format: tags get `#` prefix pills, booleans get ✓/✗, IRIs show ref_label when available, inferred rows get `.prop-inferred` class. (6) In `onLayerClick()` early-exit guard (line ~459), add `.spatial-node-flip` to the list. Add flip click handler after expand handler: find node model, toggle `showProperties`, if flipping to true and no cache entry call `fetchNodeProperties(nodeId, model.uri)`, else `renderNodes()`. (7) Add `fetchNodeProperties(nodeId, iri)` function following `fetchNodeBody` pattern — `fetch('/api/canvas/properties?iri=' + encodeURIComponent(iri))`, cache in `state.propertyCache[nodeId]`, call `renderNodes()`. (8) In `getDocument()` (line ~1142), add `if (n.showProperties) serialized.showProperties = true;` to the node serialization loop. In `applyDocument()` (line ~1167), add `if (n.showProperties) node.showProperties = true;` to the node restoration loop. (9) CSS: Add `.spatial-node-flip` to the existing button group rule (lines 4907-4909). Add `.spatial-node-flip.is-flipped` with accent color (`var(--color-accent)`). Add `.spatial-node-properties` styles: `overflow-y: auto; max-height: 100%; padding: 8px`. Add `.prop-row` as flex row with gap. `.prop-label` bold, muted, nowrap. `.prop-value` flex-grow, word-break. `.prop-inferred` with subtle background. `.prop-type-header` for type label. Add `.spatial-node-flip svg` with `flex-shrink: 0` per project convention.
  - Verify: Docker Compose up → browser: open canvas → drag typed object → click flip → property table with values → flip back → markdown → save → reload → flip state preserved. Also: untyped object shows local-name labels, old session loads without errors.
  - Done when: Flip button toggles between markdown and property table. Properties show real triplestore data. Save/load round-trips `showProperties`. CSS styling complete with active state indicator.

## Files Likely Touched

- `backend/app/canvas/router.py`
- `backend/tests/test_canvas_properties.py` (new)
- `frontend/static/js/canvas.js`
- `frontend/static/css/workspace.css`
