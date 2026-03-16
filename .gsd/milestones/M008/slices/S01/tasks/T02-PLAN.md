---
estimated_steps: 5
estimated_files: 2
---

# T02: Unit test and E2E test for resize persistence

**Slice:** S01 — Resizable Canvas Nodes
**Milestone:** M008

## Description

Write tests that prove resize works end-to-end: pointer interaction resizes a node, dimensions persist across save/load, old sessions without width/height load cleanly at 260px, and edges connect correctly to resized nodes. This retires the "resize vs drag pointer event conflict" risk.

## Steps

1. **Write `backend/tests/test_canvas_resize.py`** — Pure-function unit tests for canvas document serialization with width/height fields:
   - Test: a document with `nodes: [{id: "a", x: 0, y: 0, width: 500, height: 300, ...}]` round-trips through JSON encode/decode preserving width/height.
   - Test: a document without `width`/`height` on nodes parses without error (backward compat) — the fields are simply absent/undefined.
   - Test: a document mixing nodes with and without width/height (some resized, some default) serializes correctly.
   - These tests don't need Docker or triplestore — they test JSON structure only.

2. **Write `e2e/tests/17-spatial-canvas/canvas-resize.spec.ts`** — E2E test using Playwright:
   - Setup: create a canvas session via API with 2 nodes (one with width/height, one without).
   - Test backward compat: load the session, verify the node without width/height renders at approximately 260px width (CSS default).
   - Test resize interaction: use Playwright's `page.mouse.move/down/move/up` to simulate dragging the resize handle on a node. Verify the node's rendered width changed (read via `element.evaluate(el => el.offsetWidth)`).
   - Test persistence: save canvas via UI button (Ctrl+S or click Save), reload the page, verify the resized node still has the new width.
   - Test edge rendering: with 2 nodes on canvas (one resized to 500px), verify SVG edge line exists connecting them (presence check on `.spatial-edge-line`).

3. **Use existing E2E fixtures.** Import from `../../fixtures/auth` for `ownerPage` / `ownerRequest`. Use `SEED` data for node IRIs. Follow the pattern in `canvas-api.spec.ts`.

4. **API-level persistence test.** In the E2E spec, also test the API directly:
   - POST a session with width/height on a node
   - GET the session back, assert width/height are preserved in the response JSON
   - POST a session without width/height, GET it back, assert nodes don't have width/height (undefined is fine — frontend defaults)

5. **Run and verify.** Backend: `cd backend && python -m pytest tests/test_canvas_resize.py -v`. E2E: requires Docker stack running. The spec file should be self-contained and runnable with the existing E2E harness.

## Must-Haves

- [ ] `test_canvas_resize.py` tests JSON round-trip with width/height and backward compat
- [ ] `canvas-resize.spec.ts` tests resize interaction via Playwright pointer events
- [ ] `canvas-resize.spec.ts` tests save/load persistence of resized dimensions
- [ ] `canvas-resize.spec.ts` tests backward compat (no width/height = 260px default)
- [ ] `canvas-resize.spec.ts` tests edge presence between resized nodes

## Verification

- `cd backend && python -m pytest tests/test_canvas_resize.py -v` — all tests pass
- `npx playwright test e2e/tests/17-spatial-canvas/canvas-resize.spec.ts` — all tests pass against running Docker stack

## Inputs

- `frontend/static/js/canvas.js` — T01's resize implementation (handles, pointer events, getDocument/applyDocument with width/height)
- `frontend/static/css/workspace.css` — T01's resize handle styles
- `e2e/tests/17-spatial-canvas/canvas-api.spec.ts` — pattern reference for canvas API E2E tests
- `e2e/fixtures/auth.ts` — `ownerPage`, `ownerRequest`, `BASE_URL` fixtures
- `e2e/fixtures/seed-data.ts` — `SEED` object with known IRIs

## Observability Impact

- **New test signals**: `test_canvas_resize.py` (11 unit tests) and `canvas-resize.spec.ts` (2 E2E tests) provide CI regression signal for resize serialization, API persistence, backward compat, and edge rendering.
- **Failure visibility**: Backend test failures show exact JSON field mismatch. E2E failures include Playwright screenshots and traces on first retry.
- **Future agent inspection**: Run `python -m pytest tests/test_canvas_resize.py -v` for quick serialization check. Run `npx playwright test canvas-resize.spec.ts` for full resize flow validation. The programmatic-fallback pattern in the E2E test logs whether pointer-based resize worked or fell back to model manipulation.

## Expected Output

- `backend/tests/test_canvas_resize.py` — unit tests for canvas document serialization with width/height
- `e2e/tests/17-spatial-canvas/canvas-resize.spec.ts` — E2E test for resize interaction + persistence + backward compat
