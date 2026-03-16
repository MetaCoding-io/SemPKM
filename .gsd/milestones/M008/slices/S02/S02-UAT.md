# S02: Property Flip on Object Nodes — UAT

**Milestone:** M008
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All verification was completed via unit tests (26 backend) and browser automation (8 assertions). Property data comes from real triplestore via SHACL shapes — the integration path was exercised during T02 browser verification. No human judgment needed for layout aesthetics beyond what browser assertions cover.

## Preconditions

- Docker Compose stack running (`docker compose up -d` from project root)
- At least one Mental Model installed (e.g., Basic PKM) so objects have SHACL shapes
- At least one object exists in the triplestore with typed properties (e.g., a Project or Note with title, description, tags)
- Spatial Canvas accessible via workspace explorer sidebar

## Smoke Test

Open workspace → Spatial Canvas → drag a typed object onto canvas → click the flip button (two-arrow icon between expand/delete) → property table appears with real values from the triplestore.

## Test Cases

### 1. Flip to properties on typed object

1. Open workspace, navigate to Spatial Canvas
2. Drag a typed object (e.g., a Project) from explorer onto canvas
3. Wait for node body to load (markdown content appears)
4. Click the flip button (two curved arrows icon) in the node header
5. **Expected:** Markdown body replaced by property table. Type label header visible (e.g., "GIST:TASK" or model type name). Rows show label/value pairs for the object's properties. Body property is NOT shown. Flip button has accent color (active state).

### 2. Flip back to markdown

1. With a node showing property table (from test 1)
2. Click the flip button again
3. **Expected:** Property table replaced by markdown body. Flip button returns to default color (no accent). Markdown content matches what was shown before the first flip.

### 3. Save and restore flipped state

1. Flip a node to show properties (from test 1)
2. Save the canvas session (click save or let auto-save trigger)
3. Reload the page (F5 or navigate away and back)
4. Open the same canvas session
5. **Expected:** The previously flipped node loads with property table showing (not markdown). Flip button shows accent color. Property data re-fetched from API (network tab shows GET /api/canvas/properties request).

### 4. Untyped object shows local-name labels

1. If possible, create or find an object without a SHACL shape (untyped or from a model without shapes)
2. Drag it onto the canvas
3. Click the flip button
4. **Expected:** Property table appears with local-name labels (e.g., "title" instead of a SHACL-resolved name like "Title"). No type label header (or shows "Unknown Type"). No errors in browser console.

### 5. Multiple nodes with mixed flip states

1. Place 3 object nodes on the canvas
2. Flip the first and third nodes to properties, leave the second showing markdown
3. Save the canvas
4. Reload the page and reopen the session
5. **Expected:** First and third nodes show property tables (re-fetched). Second node shows markdown. All three render without errors.

## Edge Cases

### Old canvas session without showProperties field

1. Open a canvas session that was created before S02 (e.g., from S01 testing)
2. **Expected:** All nodes load normally showing markdown bodies. No JavaScript errors in console. Flip buttons appear in all node headers. Clicking flip works normally.

### API returns empty properties

1. Drag an object with minimal/no properties onto canvas
2. Click flip
3. **Expected:** Property table appears but shows empty state (dash or "No properties"). No crash. Flip back to markdown works.

### Rapid flip toggling

1. Click the flip button rapidly 5-6 times on a node
2. **Expected:** Node settles to correct final state (markdown or properties based on odd/even click count). No visual corruption, no duplicate fetch requests stacking up, no console errors.

### Network failure during property fetch

1. Open browser DevTools → Network tab
2. Flip a node that hasn't been flipped before
3. Before properties load, simulate offline (DevTools → Network → Offline)
4. **Expected:** Node should handle the fetch failure gracefully — either shows empty state or falls back to markdown. Console may show fetch error but no uncaught exceptions.

## Failure Signals

- Flip button not visible in node header → CSS or renderNodes() regression
- Click on flip does nothing → event handler not registered or `onLayerClick` guard missing `.spatial-node-flip`
- Property table shows "undefined" values → API response format mismatch with `buildPropertyTable()`
- Body property visible in table → body exclusion logic broken in `build_property_list()`
- Flip state lost on reload → `showProperties` not serialized in `getDocument()` or not restored in `applyDocument()`
- JavaScript errors on old sessions → missing null check for `showProperties` in `applyDocument()`
- Network tab shows no `/api/canvas/properties` request on flip → `fetchNodeProperties()` not called

## Requirements Proved By This UAT

- CANVAS-02 — Property flip on canvas object nodes: all test cases exercise the flip button, SHACL property table, inline rendering, and save/load persistence

## Not Proven By This UAT

- E2E Playwright automated tests (deferred to S04)
- User guide documentation for property flip feature (deferred to S04)
- Performance with large numbers of flipped nodes (>20 simultaneously) — not tested

## Notes for Tester

- The flip button SVG is a two-curved-arrows icon (repeat-style). It sits between the expand (arrows-out) and delete (X) buttons in the node header.
- Property cache is per-session in memory — every page reload re-fetches properties for flipped nodes. This is by design.
- The `/api/canvas/properties?iri=<IRI>` endpoint is directly callable for debugging if property data looks wrong.
- Inferred properties (from OWL inference) should show with a subtle visual indicator if the object has inferred triples.
