# S04: E2E Tests & User Guide

**Goal:** Playwright E2E tests cover property flip and live embeds; user guide chapter 27 documents all canvas features added in M008.
**Demo:** Run `cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list` — all 5 spec files pass. Open `docs/guide/27-spatial-canvas.md` — resize, property flip, and embed sections present with consistent formatting.

## Must-Haves

- `canvas-property-flip.spec.ts` — API test for `/api/canvas/properties?iri=`, UI test for flip toggle, showProperties save/load persistence, backward compat
- `canvas-embeds.spec.ts` — API test for embed node serialization round-trip, `?embed=1` X-Embed-Mode header verification, UI test for toolbar picker placement, max-8 enforcement, mixed regular+embed save/load
- Chapter 27 updated with sections on Node Resizing, Property Flip, Live Embeds (types, toolbar picker, explorer drag)
- "What Gets Saved" and "Node Anatomy" sections updated for new features
- Glossary entries for "Embed Node" and "Property Flip"

## Verification

- `cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list` — 5 spec files (canvas-api, canvas-resize, canvas-ui, canvas-property-flip, canvas-embeds) all pass
- `backend/.venv/bin/pytest tests/test_canvas_properties.py tests/test_canvas_embeds.py tests/test_canvas_resize.py -v` — existing unit tests still pass (no regressions)
- `docs/guide/27-spatial-canvas.md` — markdown renders cleanly, navigation chain ch.26 → ch.27 → ch.28 intact
- Glossary entries alphabetically placed

## Tasks

- [x] **T01: E2E Playwright tests for property flip and embeds** `est:1h30m`
  - Why: S01 has resize E2E coverage; S02/S03 have unit tests but no E2E tests. Playwright tests exercise the real running system end-to-end.
  - Files: `e2e/tests/17-spatial-canvas/canvas-property-flip.spec.ts`, `e2e/tests/17-spatial-canvas/canvas-embeds.spec.ts`
  - Do: Create two spec files following established patterns — combined-test-per-file, `openCanvas()` helper, `SemPKMCanvas.exportState()/importState()` for state inspection, `ownerRequest` for API tests, `ownerPage` for UI tests. Property flip spec: (1) API — `/api/canvas/properties?iri=` returns JSON with properties array and type_label, (2) UI — flip button toggles between markdown and property table, showProperties persists in save/load, old sessions without showProperties load fine. Embeds spec: (1) API — embed node serialization round-trip (nodeType + embedConfig preserved, old sessions backward compat), (2) API — embed endpoints return X-Embed-Mode header when `?embed=1`, (3) UI — toolbar picker opens, places embed node, exportState includes embed config, (4) UI — max 8 enforcement (try 9th, verify rejection), (5) UI — save/load with mixed regular + embed nodes.
  - Verify: `cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list` — all 5 spec files pass
  - Done when: Both new spec files pass on Chromium and Firefox alongside existing canvas specs

- [x] **T02: User guide chapter 27 update and glossary** `est:45m`
  - Why: M008 shipped 3 major features (resize, property flip, embeds) without documentation. Chapter 27 currently only covers base canvas features.
  - Files: `docs/guide/27-spatial-canvas.md`, `docs/guide/appendix-d-glossary.md`
  - Do: Add 3 new sections after "Expanding Neighborhoods" and before "Practical Workflows": (1) "Resizing Nodes" — corner/edge handles, min constraints, grid snapping, default 260px; (2) "Property Flip" — flip button in header, SHACL-derived property table, inline display, toggle back; (3) "Live Embeds" — embed concept, four embed types (view, dashboard, SPARQL, object read), toolbar picker (button → tabs → select → place), explorer drag-drop. Update "Node Anatomy" to mention resize handles and flip button. Update "What Gets Saved" to include node dimensions, showProperties, embedConfig. Update "The Toolbar" table to include Embed button. Add comparison table row about embeds. Add practical workflow example for building a research dashboard on canvas. Add glossary entries: "Embed Node", "Property Flip" in alphabetical order.
  - Verify: Markdown renders cleanly, nav footer chain ch.26 → ch.27 → ch.28 intact, glossary entries alphabetically placed, no mentions of features that don't exist
  - Done when: Chapter 27 covers all M008 features, glossary updated, docs consistent with implemented behavior

## Observability / Diagnostics

- **E2E test output**: `cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list` — shows per-spec pass/fail with timing. Failures include Playwright trace screenshots in `e2e/test-results/`.
- **Backend unit tests**: `backend/.venv/bin/pytest tests/test_canvas_properties.py tests/test_canvas_embeds.py tests/test_canvas_resize.py -v` — per-test pass/fail with assertion details.
- **Canvas state inspection**: `SemPKMCanvas.exportState()` in browser console — returns full document JSON including `showProperties`, `nodeType`, `embedConfig` fields for debugging test scenarios.
- **Embed header check**: `curl -sI 'http://localhost:3000/browser/views/generic/table?embed=1' | grep X-Embed-Mode` — confirms embed mode active without browser.
- **Properties API check**: `curl 'http://localhost:3000/api/canvas/properties?iri=urn:sempkm:model:basic-pkm:seed-note-architecture'` — returns JSON with `properties` array and `type_label`.
- **Failure artifacts**: Playwright stores trace files and screenshots for failed tests in `e2e/test-results/` with test name and browser as directory key.

## Verification (failure-path)

- `cd e2e && npx playwright test tests/17-spatial-canvas/canvas-property-flip.spec.ts --reporter=list` with an invalid API response shape → test fails with clear assertion message showing expected vs actual JSON structure.
- `cd e2e && npx playwright test tests/17-spatial-canvas/canvas-embeds.spec.ts --reporter=list` with max-embed exceeded → test verifies rejection message or node count stability.
- `grep -c '^## ' docs/guide/27-spatial-canvas.md` — returns section count; if lower than expected, a section is missing.
- `grep -n 'Embed Node\|Property Flip' docs/guide/appendix-d-glossary.md` — confirms glossary entries exist and are at expected line numbers between surrounding terms.

## Files Likely Touched

- `e2e/tests/17-spatial-canvas/canvas-property-flip.spec.ts` (new)
- `e2e/tests/17-spatial-canvas/canvas-embeds.spec.ts` (new)
- `docs/guide/27-spatial-canvas.md`
- `docs/guide/appendix-d-glossary.md`
