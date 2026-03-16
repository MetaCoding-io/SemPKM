---
estimated_steps: 5
estimated_files: 2
---

# T05: Persistence round-trip and unit tests

**Slice:** S03 — Live Embeds — Infrastructure, Types & Add UX
**Milestone:** M008

## Description

Formal verification of the full embed integration. Writes backend unit tests for canvas document serialization with embed nodes, validates backward compat, tests embed URL construction, and performs a full browser round-trip verification of save/load with mixed node types.

## Steps

1. **Create `backend/tests/test_canvas_embeds.py`** with the following test classes:

   - **TestEmbedDocumentSerialization**: Test that canvas document JSON with embed nodes round-trips correctly. Create a document with mixed node types (regular + embed). Verify `nodeType` and `embedConfig` fields are preserved. Verify regular nodes don't have nodeType field. Test that `embedConfig` includes `type`, `id`, `url`, `label` keys.

   - **TestEmbedBackwardCompat**: Test that old-format documents (no nodeType field on any node) load without errors. Parse a document with only regular nodes (id, title, uri, x, y, markdown, collapsed, width, height). Confirm no KeyError or missing field issues. This mirrors the backward compat tests in `test_canvas_resize.py`.

   - **TestEmbedURLConstruction**: Test that embed URLs are constructed correctly for each embed type:
     - View: `/browser/views/generic/table?embed=1`
     - Dashboard: `/browser/dashboard/{uuid}?embed=1`
     - SPARQL: `/browser/sparql-result/{uuid}?embed=1`
     - Object: `/browser/object/{iri}?embed=1`
     Validate URL format, query parameter presence, proper encoding.

   - **TestMaxEmbedCount**: Test the max-8-embed enforcement logic. Create a document with 8 embed nodes — verify it's valid. Add a 9th — verify the enforcement would reject it. This tests the counting logic, not the UI toast.

   - **TestMixedNodeDocument**: Test a realistic document with: 2 regular nodes (one resized with width/height), 1 regular node with showProperties, 1 view embed, 1 dashboard embed. Serialize and deserialize. Verify all fields preserved, positions correct, widths correct, nodeType correct on embeds, absent on regular nodes.

2. **Verify canvas API save/load endpoint handles embed nodes.** The canvas save API (`POST /api/canvas/sessions/{id}`) already accepts arbitrary JSON in the document field. Verify that the existing endpoint doesn't strip unknown fields — `nodeType` and `embedConfig` must round-trip through the API. If the API does field validation, extend it to accept the new fields.

3. **Check the canvas save/load implementation in canvas.js.** Verify that `save()` calls `getDocument()` (which T02 extended) and that `loadSession()` calls `applyDocument()` (which T02 extended). These should work without additional changes, but verify the data flows correctly end-to-end.

4. **Browser integration verification.** In the running app:
   - Place 2 regular nodes (resize one), add 1 view embed, add 1 dashboard embed via toolbar picker
   - Save the canvas session
   - Reload the page (or switch sessions and switch back)
   - Verify: all nodes restore at correct positions/sizes, embed nodes have correct types, iframes reload content from persisted URLs, regular nodes show markdown/properties correctly

5. **Edge case: empty embedConfig handling.** Test that a malformed document with `nodeType: 'embed'` but missing `embedConfig` doesn't crash `applyDocument()` or `renderNodes()`. The code should handle this gracefully — skip rendering the iframe, show an error state, or treat as a regular node.

## Must-Haves

- [ ] Unit tests cover: serialization round-trip, backward compat, URL construction, max embed count, mixed node document
- [ ] All unit tests pass: `docker compose exec api python -m pytest tests/test_canvas_embeds.py -v`
- [ ] Browser save/load round-trip preserves embed nodes with correct iframe URLs
- [ ] Old sessions load without errors in the presence of embed-aware code

## Verification

- `docker compose exec api python -m pytest tests/test_canvas_embeds.py -v` — all tests pass
- Browser: save canvas with mixed nodes → reload → all nodes restored correctly
- Browser: load an old session (pre-embed) → no JS errors, regular nodes render fine

## Inputs

- T02's `getDocument()` / `applyDocument()` extensions for nodeType/embedConfig
- T02's `addEmbedNode()` for max-embed counting logic
- Existing `test_canvas_resize.py` as a pattern for canvas document tests (serialization approach, backward compat structure)
- Existing canvas save/load API: `POST /api/canvas/sessions/{id}`, `GET /api/canvas/sessions/{id}`

## Observability Impact

- **Unit test suite**: `backend/tests/test_canvas_embeds.py` — 32 tests covering serialization, backward compat, URL construction, max embed enforcement, mixed documents, and malformed embed edge cases. Run with `cd backend && .venv/bin/pytest tests/test_canvas_embeds.py -v`.
- **Malformed embed guard**: `renderNodes()` in canvas.js now skips embed nodes with missing/invalid `embedConfig` instead of throwing — prevents JS crashes from corrupted document data.
- **Inspection surface**: `SemPKMCanvas.exportState()` returns full document with `nodeType`/`embedConfig` for embed nodes — round-trips through `POST /api/canvas/sessions` and `GET /api/canvas/{id}`.

## Expected Output

- `backend/tests/test_canvas_embeds.py` — comprehensive unit tests for embed document handling
- Verified browser round-trip with mixed node types (documented in task summary)
