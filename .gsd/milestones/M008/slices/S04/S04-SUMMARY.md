---
id: S04
parent: M008
milestone: M008
provides:
  - canvas-property-flip.spec.ts — 2 E2E tests (API + UI) for property flip
  - canvas-embeds.spec.ts — 2 E2E tests (API + UI) for live embeds
  - Chapter 27 updated with Resizing Nodes, Property Flip, Live Embeds sections
  - Glossary entries for "Embed Node" and "Property Flip"
  - Resolved conflict marker in basic-pkm.jsonld
requires:
  - slice: S01
    provides: resize interaction testable end-to-end (existing specs)
  - slice: S02
    provides: /api/canvas/properties endpoint, flip button UI, showProperties state
  - slice: S03
    provides: embed node type, toolbar picker, dual-layer rendering, ?embed=1 endpoints
affects: []
key_files:
  - e2e/tests/17-spatial-canvas/canvas-property-flip.spec.ts
  - e2e/tests/17-spatial-canvas/canvas-embeds.spec.ts
  - docs/guide/27-spatial-canvas.md
  - docs/guide/appendix-d-glossary.md
  - models/basic-pkm/ontology/basic-pkm.jsonld
key_decisions:
  - Embed UI E2E test uses SemPKMCanvas.addEmbed() JS API instead of picker item clicks — picker's outside-click dismissal handler races with click handler in headless Playwright
patterns_established:
  - E2E embed testing pattern: open picker → verify tabs → read config from DOM → place via JS API → verify exportState(). More reliable than clicking picker items in headless mode.
  - Feature doc pattern: section heading → explanation → bullet details → persistence note → tip callout
observability_surfaces:
  - cd e2e && npx playwright test tests/17-spatial-canvas/canvas-property-flip.spec.ts --project=chromium
  - cd e2e && npx playwright test tests/17-spatial-canvas/canvas-embeds.spec.ts --project=chromium
  - grep '^## ' docs/guide/27-spatial-canvas.md — 14 section headings including 3 new ones
  - grep -n 'Embed Node\|Property Flip' docs/guide/appendix-d-glossary.md — lines 28 and 91
drill_down_paths:
  - .gsd/milestones/M008/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M008/slices/S04/tasks/T02-SUMMARY.md
duration: 2h20m
verification_result: passed
completed_at: 2026-03-16
---

# S04: E2E Tests & User Guide

**4 Playwright E2E tests covering property flip and live embeds, plus full Chapter 27 documentation for all M008 canvas features (resize, property flip, embeds).**

## What Happened

**T01 — E2E Playwright tests** created two spec files (4 tests total) rounding out the 17-spatial-canvas test directory to 5 spec files:

- `canvas-property-flip.spec.ts`: API test validates `/api/canvas/properties?iri=<IRI>` returns properties array and type_label for notes and concepts, plus error handling (missing/empty IRI → 4xx). UI test exercises flip button toggle between markdown and property table, verifies `is-flipped` CSS class, `showProperties` in exportState, persistence via importState, and backward compat with old sessions.

- `canvas-embeds.spec.ts`: API test validates embed node serialization round-trip (nodeType + embedConfig preserved), backward compat with old sessions, and `X-Embed-Mode: 1` header on `?embed=1` endpoints. UI test verifies toolbar picker (3 tabs), places embed via JS API, verifies exportState, tests max-8 enforcement (9th rejected), and mixed regular+embed save/load.

Also fixed a git conflict marker in `models/basic-pkm/ontology/basic-pkm.jsonld` (Project vs Task subclass — kept gist:Project) that was blocking model installation in the test Docker stack.

**T02 — User guide** extended Chapter 27 with 3 new feature sections (~117 new lines):

- "Resizing Nodes" — corner/edge/bottom handles, 24px grid snap, 160px/80px min constraints, 260px default
- "Property Flip" — flip button behavior, property table contents (type label, SHACL rows, multi-value pills, boolean markers, inferred properties)
- "Live Embeds" — concept, 4 embed types (View/Dashboard/SPARQL/Object Read), toolbar picker flow, explorer drag-drop, max 8 limit, default size

Updated existing sections: Node Anatomy (flip button, resize handles), Toolbar table (Embed row), What Gets Saved (dimensions, flip state, embed config), Canvas vs Graph View comparison (Embeds row). Added practical workflow "Building a Research Dashboard on Canvas". Two glossary entries (Embed Node, Property Flip) in alphabetical order.

## Verification

- **5 spec files exist**: canvas-api, canvas-resize, canvas-ui, canvas-property-flip, canvas-embeds
- **Individual spec runs pass**: property flip 2/2 (chromium), embeds 2/2 (chromium)
- **Full suite note**: 5 specs × 2 tests = 10 auth tokens needed in rapid succession. Rate limit is 5/min. Tests pass individually and in pairs; full-suite auth failures are a pre-existing environment constraint, not test code bugs.
- **Backend unit tests**: 69/69 passed (26 properties + 32 embeds + 11 resize) in 0.52s
- **Chapter 27**: 14 `##` sections including 3 new. Nav footer ch.26 → ch.27 → ch.28 intact.
- **Glossary**: Embed Node at line 28 (between Edge/Entailment), Property Flip at line 91 (between PKCE/Property)
- **Zero conflict markers** across backend/, frontend/, e2e/, docs/, models/

## Requirements Advanced

- None — S04 is a test and docs slice; all CANVAS requirements were already validated by S01–S03.

## Requirements Validated

- None newly validated — CANVAS-01 through CANVAS-05 were validated by S01, S02, and S03 respectively.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Embed UI test places embeds via `SemPKMCanvas.addEmbed()` JS API instead of clicking picker items — picker's outside-click handler races with click handler in headless Playwright.
- Property API validation test checks `>= 400 && < 500` range instead of exactly 400 — missing `iri` param returns 422 (Pydantic) not 400.
- Used `.spatial-node-properties` (actual DOM class) instead of `.spatial-node-property-table` (plan's class name).
- Resolved conflict marker in `basic-pkm.jsonld` — not in plan but blocking test environment.

## Known Limitations

- Full 5-spec suite hits 5/min magic-link rate limit when all 10 tests run consecutively. Tests pass individually and in pairs. Fix options: increase rate limit for test env, share auth session via worker-scoped fixture, or add inter-spec delays.
- Docker test stack must be started from the worktree directory for M008 code to be volume-mounted.

## Follow-ups

- Consider worker-scoped auth fixture to share magic-link token across all tests in a spec file, reducing total auth requests per suite run.

## Files Created/Modified

- `e2e/tests/17-spatial-canvas/canvas-property-flip.spec.ts` — New: 2 E2E tests (API + UI) for property flip
- `e2e/tests/17-spatial-canvas/canvas-embeds.spec.ts` — New: 2 E2E tests (API + UI) for live embeds
- `models/basic-pkm/ontology/basic-pkm.jsonld` — Fixed git conflict marker (gist:Project vs gist:Task)
- `docs/guide/27-spatial-canvas.md` — Extended with 3 new feature sections, updated existing sections (~117 new lines)
- `docs/guide/appendix-d-glossary.md` — Added Embed Node and Property Flip entries

## Forward Intelligence

### What the next slice should know
- This is the final slice of M008. The spatial canvas now has: resizable nodes (S01), property flip (S02), live embeds with dual-layer rendering (S03), E2E tests and docs (S04). All 5 CANVAS requirements validated.

### What's fragile
- E2E test rate limiting — running all 5 canvas specs together exceeds 5/min magic-link limit. Must run individually or in pairs until auth fixture is optimized.
- Embed picker interaction in Playwright — the outside-click dismissal handler conflicts with headless browser timing. JS API workaround is stable but means picker click flow isn't E2E-tested via real user interaction.

### Authoritative diagnostics
- `cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list` — per-spec pass/fail with timing. Rate-limit failures show as auth errors, not test logic errors.
- `backend/.venv/bin/pytest tests/test_canvas_properties.py tests/test_canvas_embeds.py tests/test_canvas_resize.py -v` — 69 unit tests, <1s, no Docker needed.

### What assumptions changed
- Plan assumed picker items could be clicked in E2E tests — actual behavior requires JS API placement due to outside-click handler timing in headless mode.
- Plan assumed property API returns 400 for missing params — Pydantic returns 422.
