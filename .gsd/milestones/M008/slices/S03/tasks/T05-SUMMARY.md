---
id: T05
parent: S03
milestone: M008
provides:
  - 32-test unit test suite covering embed document serialization, backward compat, URL construction, max embed enforcement, mixed documents, and malformed edge cases
  - Malformed embedConfig guard in renderNodes() preventing JS crashes from corrupted data
  - Verified browser save/load round-trip with mixed regular + embed nodes
key_files:
  - backend/tests/test_canvas_embeds.py
  - frontend/static/js/canvas.js
key_decisions:
  - Python test simulation uses `is not None` checks (not truthiness) to match JS behavior where `{}` is truthy but Python `{}` is falsy
  - Added defensive guard in renderNodes() embed loop to skip embed nodes with missing/invalid embedConfig rather than crashing
patterns_established:
  - js_get_document_node/js_apply_document_node Python simulations mirror exact JS canvas.js serialization logic for testing without a browser
observability_surfaces:
  - Unit tests: `cd backend && .venv/bin/pytest tests/test_canvas_embeds.py -v` — 32 tests, 0.07s
  - Malformed embed guard: embed nodes with missing embedConfig are silently skipped in renderNodes() instead of throwing TypeError
duration: 30m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T05: Persistence round-trip and unit tests

**Wrote 32 unit tests for canvas embed document handling and verified full browser save/load round-trip with mixed node types.**

## What Happened

Rewrote `backend/tests/test_canvas_embeds.py` from the thin T01-era version (13 tests, mostly trivial URL string checks) to a comprehensive 32-test suite organized into 6 test classes:

- **TestEmbedDocumentSerialization** (5 tests): nodeType/embedConfig round-trip, regular nodes excluded, mixed documents, embedConfig key structure, dimension preservation
- **TestEmbedBackwardCompat** (6 tests): minimal old docs, full old docs with all pre-embed fields, old docs with edges, empty docs, applyDocument simulation for missing nodeType, mixed old+new in same document
- **TestEmbedURLConstruction** (7 tests): each embed type URL format, class filter params, special character encoding, all-types coverage
- **TestMaxEmbedCount** (5 tests): at-limit validity, over-limit rejection, regular nodes don't count, mixed counting, zero embeds
- **TestMixedNodeDocument** (5 tests): realistic 5-node doc with fixture, regular+embed field preservation, positions, full JS simulation round-trip
- **TestMalformedEmbedConfig** (4 tests): missing embedConfig, empty embedConfig, partial embedConfig, malformed-doesn't-corrupt-others

Tests include Python simulations of the JS `getDocument()`/`applyDocument()` logic that mirror the exact conditional serialization patterns in canvas.js (using `is not None` instead of truthiness to match JS semantics).

Verified canvas API doesn't strip unknown fields — `CanvasPutBody.document` is `dict[str, Any]` and `CanvasService.save_document()` does raw `json.dumps()`, so nodeType/embedConfig survive round-trip transparently.

Added a defensive guard in the embed layer rendering loop in canvas.js: `if (!eNode.embedConfig || !eNode.embedConfig.url) continue;` — skips malformed embed nodes instead of throwing a TypeError when accessing `.type`, `.label`, or `.url` on undefined.

Browser verification: created a session with 2 regular nodes + 2 embeds via API, saved to named session, cleared canvas, reloaded from API — all 4 nodes restored with correct positions, sizes, types, and iframe URLs. Old pre-embed document loaded cleanly with no nodeType contamination. 9th embed correctly rejected by max-8 enforcement.

## Verification

- `cd backend && .venv/bin/pytest tests/test_canvas_embeds.py -v` — **32/32 passed** (0.07s)
- Browser: saved canvas with 2 regular + 2 embed nodes → API round-trip → all fields preserved (nodeType, embedConfig.type/id/url/label, width, height, markdown)
- Browser: cleared canvas → loaded from API → all 4 nodes restored with iframes rendering live content
- Browser: loaded pre-embed document (no nodeType on any node) → no errors, no nodeType contamination
- Browser: 9th embed attempt rejected (embedCount stays at 8)
- Browser: `SemPKMCanvas.exportState()` returns nodeType:'embed' and full embedConfig for embed nodes
- Browser: X-Embed-Mode response header present on embed endpoints (value "1")
- Browser: no JS console errors related to canvas or embeds

### Slice-level verification status (T05 is final task):
- ✅ `cd backend && .venv/bin/pytest tests/test_canvas_embeds.py -v` — 32/32 passed
- ✅ Browser: `/browser/views/generic/table?embed=1` → full HTML page, no sidebar (T01)
- ✅ Browser: embed node via toolbar picker → iframe loads real content (T03)
- ✅ Browser: save canvas, reload → embed nodes restore, iframes reload content
- ✅ Browser: 9th embed → rejection (max 8 enforced)
- ✅ Browser: `SemPKMCanvas.exportState()` includes nodeType/embedConfig for embed nodes
- ✅ Diagnostic: X-Embed-Mode header present on embed endpoints

## Diagnostics

- **Unit tests**: `cd backend && .venv/bin/pytest tests/test_canvas_embeds.py -v`
- **Round-trip inspection**: Save a session via `POST /api/canvas/sessions`, load via `GET /api/canvas/{id}`, compare document.nodes for nodeType/embedConfig presence
- **Malformed embed handling**: A node with `nodeType:'embed'` but no `embedConfig` is silently skipped in renderNodes() — no DOM element created, no error thrown
- **State inspection**: `SemPKMCanvas.exportState()` in browser devtools returns full document including all embed fields

## Deviations

- Existing `test_canvas_embeds.py` from T01 was entirely replaced rather than extended — the T01 version had 13 trivial tests (URL string assertions, dict key checks) that didn't simulate the actual JS serialization logic. The new suite is 32 tests with proper round-trip simulation.
- Added a defensive guard in `renderNodes()` for malformed embedConfig (Step 5 edge case) — this is a one-line change in canvas.js not originally in the plan as a code change, but was identified as necessary by the plan's edge case analysis.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_canvas_embeds.py` — Rewrote from 13 to 32 tests: 6 test classes covering serialization, backward compat, URL construction, max embed count, mixed documents, malformed edge cases
- `frontend/static/js/canvas.js` — Added malformed embedConfig guard in renderNodes() embed loop (line ~1036)
- `.gsd/milestones/M008/slices/S03/tasks/T05-PLAN.md` — Added Observability Impact section per pre-flight requirement
