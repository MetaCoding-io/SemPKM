---
id: S01
parent: M036
milestone: M036
provides:
  - business-planning model archive (manifest + ontology + shapes + views + seed) with namespace urn:sempkm:model:business-planning:
  - Shared base types (bp:FrameworkItem, bp:QuadrantItem) for S02-S04 extension
  - Eisenhower Matrix types (bp:EisenhowerMatrix, bp:EisenhowerItem) with sh:in constraints on bp:urgency and bp:importance
  - quadrant renderer type wired into _VALID_RENDERERS, RENDERER_REGISTRY, and generic_view elif chain
  - _detect_quadrant_axes() service method — finds two SHACL properties with exactly 2 sh:in values
  - execute_quadrant_query() service method — groups items into quadrant buckets by axis values
  - /browser/views/generic/quadrant/data JSON endpoint for debugging quadrant data
  - quadrant_view.html Jinja2 template with view-flex-column wrapper, type_filter_pills, view_toolbar, 2×2 grid
  - quadrant.css — 2×2 CSS Grid layout with Eisenhower color coding and dark mode support
  - quadrant.js — drag-to-reclassify with dockview isolation (stopPropagation), optimistic DOM move, revert on failure
  - 28 unit tests covering axis detection, SPARQL query building, Eisenhower labelling, and result grouping
  - 8 seed Eisenhower items spanning all 4 quadrants
requires: []
affects:
  - S02 (consumes model archive structure, namespace, shared ontology base)
  - S03 (consumes model archive structure, namespace, shared ontology base)
  - S04 (consumes quadrant renderer for SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix)
  - S05 (consumes quadrant renderer for E2E tests + documentation)
key_files:
  - models/business-planning/manifest.yaml
  - models/business-planning/ontology/business-planning.jsonld
  - models/business-planning/shapes/business-planning.jsonld
  - models/business-planning/views/business-planning.jsonld
  - models/business-planning/seed/business-planning.jsonld
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/views/registry.py
  - backend/app/templates/browser/quadrant_view.html
  - frontend/static/js/quadrant.js
  - frontend/static/css/quadrant.css
  - backend/tests/test_quadrant.py
key_decisions:
  - Used gist:Category as superclass for FrameworkItem and gist:Collection for EisenhowerMatrix (matching gist upper ontology patterns)
  - Kept urgency/importance as xsd:string with sh:in ["high","low"] rather than enum IRIs — simpler for drag-drop updates via object.patch
  - _detect_quadrant_axes finds properties with exactly 2 sh:in values (general), not hardcoded to "high"/"low" — any 2-value enum works
  - Eisenhower-specific quadrant labels ("Do First", "Schedule", "Delegate", "Eliminate") in a lookup dict with generic fallback
  - Single atomic object.patch command for both axis properties rather than two separate commands
  - Quadrant cell colors use rgba tints (green=Do First, blue=Schedule, amber=Delegate, red=Eliminate) — distinct in both light and dark mode
patterns_established:
  - business-planning model follows exact same 5-file JSON-LD structure as basic-pkm (inline @context, no remote URLs)
  - Quadrant axis detection follows _detect_status_field pattern — prefers keyword in path with fallback to first candidates
  - Quadrant JS follows exact kanban.js IIFE structure — onDragStart/End/Over/Leave/Drop, optimistic move, revert on failure
  - Empty cell state uses CSS :empty pseudo-element with italic "Drag items here" hint
  - Quadrant test follows kanban test structure — same mock helpers, same AsyncMock pattern
observability_surfaces:
  - logger.info("generic_view: renderer=quadrant type=%s ...") in router on each view request
  - logger.info("execute_quadrant_query: type=%s total=%d quadrants=%d") in service after query execution
  - /browser/views/generic/quadrant/data?type=<iri> JSON endpoint for debugging quadrant data
  - JS console.error "quadrant: failed to patch for <IRI>" on API failure
  - sempkm:command-executed custom event dispatched on successful drag-drop patch
  - Error template shows descriptive message when type has no quadrant-axis properties
drill_down_paths:
  - .gsd/milestones/M036/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M036/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M036/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M036/slices/S01/tasks/T04-SUMMARY.md
duration: 87m
verification_result: passed
completed_at: 2026-03-23
---

# S01: Eisenhower Matrix — Model Archive + Quadrant Renderer

**Shipped the complete vertical from model archive to interactive quadrant view: `business-planning` model with Eisenhower types, quadrant renderer wired into the view system, 2×2 CSS Grid frontend with drag-to-reclassify updating RDF properties, and 28 unit tests.**

## What Happened

**T01 — Model Archive** created the `business-planning` model with 5 JSON-LD files following basic-pkm's structure exactly. Defines 4 OWL classes: `bp:FrameworkItem` (abstract base, subClassOf gist:Category), `bp:QuadrantItem` (subClassOf FrameworkItem — base for 2-axis grid items), `bp:EisenhowerMatrix` (container, subClassOf gist:Collection), and `bp:EisenhowerItem` (subClassOf QuadrantItem). SHACL shapes include `sh:in ["high","low"]` constraints on `bp:urgency` and `bp:importance` with PropertyGroups organizing the form into 4 sections. ViewSpecs declare three views including a `sempkm:rendererType: "quadrant"` for EisenhowerItem. Seed data provides 1 matrix with 8 items across all 4 quadrants.

**T02 — Backend Wiring** added the `quadrant` renderer to all three layers: `_VALID_RENDERERS`, `RENDERER_REGISTRY`, and new elif branches in `generic_view()` and `generic_view_data()`. The ViewSpecService gained 4 new methods — `_detect_quadrant_axes()` finds two SHACL properties with exactly 2 `sh:in` values (preferring paths containing "urgency"/"importance"), `_build_quadrant_select()` generates SPARQL with non-OPTIONAL axis bindings, `_quadrant_label()` maps axis value pairs to Eisenhower labels with generic fallback, and `execute_quadrant_query()` orchestrates the pipeline. The Jinja2 template includes server-rendered quadrant cells with items, type filter pills, and view toolbar.

**T03 — Frontend** created `quadrant.css` (2×2 CSS Grid, Eisenhower color-coded cells, dark mode via `html[data-theme="dark"]`, `.view-flex-column` full-height) and `quadrant.js` (IIFE following kanban.js exactly — `stopPropagation()` on all 4 drag events, `contains(relatedTarget)` flicker guard, optimistic DOM move with revert on failure, atomic `object.patch` for both axis properties). Fixed Jinja2 `q.items` → `q['items']` in 3 places (same dict method collision as kanban M031).

**T04 — Unit Tests** created 28 tests across 5 classes covering axis detection (happy path, keyword preference, fallback, rejection of 3+ values, edge cases), SPARQL query building (basic, scope filter, non-OPTIONAL bindings), label mapping (4 Eisenhower labels + generic fallback), and result grouping (4 quadrants, unclassified bucket, deduplication, empty results, error handling).

## Verification

- **28 unit tests pass**: `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — 28 passed in 0.54s
- **Manifest validates**: `parse_manifest()` returns `business-planning v1.0.0` with namespace `urn:sempkm:model:business-planning:`
- **JSON-LD files parse**: All 4 files load via rdflib — ontology (49 triples), shapes (154 triples), views (19 triples), seed (55 triples)
- **Backend wiring**: `quadrant` present in `_VALID_RENDERERS`, `RENDERER_REGISTRY`, and all 4 ViewSpecService methods callable
- **Frontend files**: `quadrant.js` (189 lines, 4 stopPropagation calls, object.patch wiring), `quadrant.css` (286 lines, 10 dark mode rules, CSS Grid layout), `quadrant_view.html` (102 lines, /css/ path convention, q['items'] dict access)
- **Browser verification** (T03): Quadrant view renders 4 quadrants in dockview tab, drag-drop persists after reload, dark mode text readable

## Requirements Advanced

- BIZ-01 (model archive) — business-planning model archive created with manifest, ontology, shapes, views, and seed data
- BIZ-02 (quadrant renderer) — full quadrant renderer vertical shipped from backend detection through frontend drag interaction

## Requirements Validated

- None yet — BIZ-01 and BIZ-02 need live runtime integration testing (model install via Admin UI, SPARQL queryability) to reach validated status

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Fixed Jinja2 `q.items` → `q['items']` in quadrant_view.html — T02 template used `q.items` which collides with the dict `.items()` method in Jinja2's attribute resolution (same bug as kanban M031 KNOWLEDGE entry)

## Known Limitations

- Quadrant renderer is parameterized by axis values but quadrant labels are only Eisenhower-specific (high/high → "Do First"). Non-Eisenhower types get generic "Axis: value / Axis: value" labels. S04 frameworks (SWOT, BCG) will need their own label mappings added to `_quadrant_label()`.
- Items missing either axis value are excluded from the grid (non-OPTIONAL SPARQL bindings). Unclassified items section exists in template but only for unexpected axis values, not missing values.
- No E2E Playwright tests — deferred to S05 per roadmap.
- Model not yet tested in live Docker stack install (requires running triplestore).

## Follow-ups

- S04 must extend `_quadrant_label()` with SWOT, BCG, Ansoff, Stakeholder Map, and Risk Matrix label mappings
- S05 must add E2E Playwright tests for model install → quadrant view → drag interaction roundtrip
- Consider adding OPTIONAL fallback for axis values to show items with missing urgency/importance in an "Unset" row/column

## Files Created/Modified

- `models/business-planning/manifest.yaml` — Model manifest (modelId, namespace, prefixes, entrypoints, icon defs)
- `models/business-planning/ontology/business-planning.jsonld` — OWL classes (FrameworkItem, QuadrantItem, EisenhowerMatrix, EisenhowerItem) and properties
- `models/business-planning/shapes/business-planning.jsonld` — SHACL NodeShapes with PropertyGroups, sh:in constraints
- `models/business-planning/views/business-planning.jsonld` — ViewSpecs for matrix table, item table, and item quadrant renderer
- `models/business-planning/seed/business-planning.jsonld` — Seed data: 1 matrix + 8 items spanning all 4 quadrants
- `backend/app/views/router.py` — Added quadrant to _VALID_RENDERERS, elif branches in generic_view() and generic_view_data()
- `backend/app/views/service.py` — Added _detect_quadrant_axes(), _build_quadrant_select(), _quadrant_label(), execute_quadrant_query()
- `backend/app/views/registry.py` — Added quadrant entry to RENDERER_REGISTRY
- `backend/app/templates/browser/quadrant_view.html` — Jinja2 template with 2×2 grid, type filter pills, view toolbar, lazy-load JS
- `frontend/static/js/quadrant.js` — Drag-to-reclassify IIFE with dockview isolation and optimistic DOM move
- `frontend/static/css/quadrant.css` — 2×2 CSS Grid layout with color coding and dark mode
- `backend/tests/test_quadrant.py` — 28 unit tests for quadrant pipeline

## Forward Intelligence

### What the next slice should know
- The `business-planning` namespace is `urn:sempkm:model:business-planning:` and uses prefix `bp:`. All S02-S04 types should use this namespace.
- Shared base types `bp:FrameworkItem` and `bp:QuadrantItem` are ready for subclassing. QuadrantItem has urgency/importance but S04 frameworks should add their own axis properties.
- The quadrant renderer is parameterized — any type with two `sh:in` properties having exactly 2 values will work. The axis detection prefers "urgency"/"importance" keywords but falls back to first two candidates.
- S02 (BMC) and S03 (OKR/Decision Matrix) need new renderer types — they can follow the exact same pattern: add to `_VALID_RENDERERS`, add elif branch, add service method, create template + JS + CSS.

### What's fragile
- `_quadrant_label()` has a hardcoded Eisenhower label dict — S04 frameworks using the quadrant renderer will get generic labels unless the dict is extended per framework
- The non-OPTIONAL axis bindings mean items with null urgency or importance silently disappear from the view — this is intentional but could confuse users

### Authoritative diagnostics
- `/browser/views/generic/quadrant/data?type=<iri>` — returns JSON with quadrants array, axes metadata, and total count. First place to check if the view looks wrong.
- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — 28 tests pin the entire quadrant pipeline. If this passes, the backend logic is sound.

### What assumptions changed
- Planned generic "high"/"low" axis values turned out to be exactly right for Eisenhower. The general detection (`_detect_quadrant_axes` finds any 2-value sh:in properties) means S04 frameworks with different axis values (e.g., "strength"/"weakness" for SWOT) will work without code changes — only label mappings need updating.
