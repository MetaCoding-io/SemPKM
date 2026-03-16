# S04 — Research: E2E Tests & User Guide

**Date:** 2026-03-16

## Summary

Straightforward slice — write Playwright E2E tests for the three features delivered in S01–S03 and update the user guide chapter 27 (Spatial Canvas) with documentation for resize, property flip, and live embeds. All patterns are established: three existing canvas E2E specs in `e2e/tests/17-spatial-canvas/` demonstrate the `openCanvas` helper, `SemPKMCanvas.exportState()`/`importState()` API, and the combined-test-per-file pattern to respect rate limits. Chapter 27 already covers the base canvas features and needs new sections appended before the "Practical Workflows" and comparison table.

No new technology, no risky integration, no architectural decisions needed.

## Recommendation

**Two tasks: E2E tests first, user guide second.** Tests exercise the real running system and may surface issues worth documenting. Both tasks are independent from a code perspective (different file trees), but running tests first gives confidence that the features work end-to-end before writing docs.

**E2E test organization:** Two new spec files:
1. `canvas-property-flip.spec.ts` — property flip API endpoint + UI toggle + save/load persistence
2. `canvas-embeds.spec.ts` — embed node serialization, toolbar picker, embed endpoint responses, save/load with mixed nodes, max-8 enforcement

Resize already has full E2E coverage (`canvas-resize.spec.ts` with 2 tests). No new resize tests needed.

**User guide:** Update chapter 27 (`docs/guide/27-spatial-canvas.md`) — add sections for Node Resizing, Property Flip, and Live Embeds (toolbar picker + explorer drag). Update the glossary with new terms. Update the Node Anatomy section to mention resize handles and flip button. Update the "What Gets Saved" list to include node dimensions and embed configs. No new chapter needed — the content belongs in the existing canvas chapter.

## Implementation Landscape

### Key Files

**E2E tests (to create):**
- `e2e/tests/17-spatial-canvas/canvas-property-flip.spec.ts` — New. Tests: (1) API: `GET /api/canvas/properties?iri=<IRI>` returns JSON with properties array and type_label; (2) UI: flip button toggles between markdown and property table, `showProperties` persists in save/load, old sessions without `showProperties` load fine.
- `e2e/tests/17-spatial-canvas/canvas-embeds.spec.ts` — New. Tests: (1) API: embed node serialization round-trip (nodeType + embedConfig preserved, old sessions backward compat); (2) API: embed endpoints return `X-Embed-Mode: 1` header when `?embed=1`; (3) UI: toolbar picker opens, places embed node, `SemPKMCanvas.exportState()` includes embed config; (4) UI: max 8 enforcement (try to add 9th, verify rejection); (5) UI: save/load with mixed regular + embed nodes.

**E2E test infrastructure (existing, to reuse):**
- `e2e/fixtures/auth.ts` — `ownerRequest` (API context), `ownerPage` (browser context), `BASE_URL`
- `e2e/fixtures/seed-data.ts` — `SEED` constants with known object IRIs/titles
- `e2e/helpers/wait-for.ts` — `waitForWorkspace(page)` helper
- `e2e/tests/17-spatial-canvas/canvas-resize.spec.ts` — Reference for `openCanvas()` helper pattern
- `e2e/tests/17-spatial-canvas/canvas-ui.spec.ts` — Reference for complex UI interaction tests

**User guide (to modify):**
- `docs/guide/27-spatial-canvas.md` — Add sections: "Resizing Nodes", "Property Flip", "Live Embeds", "Embed Picker", "Dragging Embeds from Explorer". Update "Node Anatomy", "What Gets Saved", and comparison table. Update nav footer if chapter numbering changes.
- `docs/guide/appendix-d-glossary.md` — Add: "Embed Node", "Property Flip". Update "Spatial Canvas" entry to mention new features.
- `docs/guide/README.md` — No change needed (chapter 27 already listed).

### Build Order

**T01: E2E tests** — Two new spec files. Property flip tests exercise `/api/canvas/properties` endpoint and UI flip toggle. Embed tests exercise serialization, `?embed=1` endpoints, toolbar picker, max-8 limit, and mixed save/load. Follow the established pattern: `openCanvas()` helper, combined tests per file, `SemPKMCanvas.exportState()`/`importState()` for state inspection.

Key patterns to follow:
- Single `test.describe` block per file with combined test functions (rate-limit friendly)
- `openCanvas(page)` helper: `goto → waitForWorkspace → openCanvasTab → waitForSelector → waitForFunction`
- API tests use `ownerRequest` (no browser), UI tests use `ownerPage`
- Use `page.evaluate()` for canvas state inspection — `SemPKMCanvas.exportState()` and `SemPKMCanvas.importState()`
- `SemPKMCanvas.addEmbed()` exposed on window for programmatic embed creation in tests
- `X-Embed-Mode: 1` header for verifying embed endpoint responses
- `SEED.notes.architecture.iri` and `SEED.concepts.eventSourcing.iri` as known test objects

**T02: User guide update** — Extend chapter 27 with 3 new sections after "Expanding Neighborhoods" and before "Practical Workflows". Update glossary. Keep the same style: short paragraphs, tables for controls, `> **Tip:**` callouts, numbered step lists.

Sections to add:
1. **Resizing Nodes** — drag corner/edge handles, min constraints, grid snapping, default 260px
2. **Property Flip** — flip button in header, SHACL-derived property table, inline display, toggle back
3. **Live Embeds** — embed concept, four embed types (view, dashboard, SPARQL, object read)
4. **Adding Embeds** — toolbar picker (button → tabs → select → place) and explorer drag-drop
5. Update "Node Anatomy" header controls to include flip button and resize handles
6. Update "What Gets Saved" to include node dimensions, showProperties, embedConfig
7. Update comparison table to mention embeds as a differentiator
8. Add "Practical Workflows" example: building a research dashboard on canvas
9. Glossary: "Embed Node", "Property Flip"

### Verification Approach

**E2E tests:** Run the full spatial canvas test suite:
```bash
cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list
```
All 4 spec files (canvas-api, canvas-resize, canvas-ui, canvas-property-flip, canvas-embeds) should pass.

**User guide:** Verify:
- `docs/guide/27-spatial-canvas.md` renders clean markdown (no broken links, tables render)
- Navigation chain intact: ch. 26 → ch. 27 → ch. 28
- Glossary entries added and alphabetically placed
- No mentions of features that don't exist (e.g., no "auto-layout embeds")

**Backend unit tests:** Run existing test suite to confirm no regressions:
```bash
cd backend && .venv/bin/pytest tests/test_canvas_properties.py tests/test_canvas_embeds.py tests/test_canvas_resize.py -v
```
