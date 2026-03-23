# S02: Business Model Canvas — 9-Box Poster Renderer

**Goal:** BMC types added to the business-planning model and a new `bmc` renderer wired end-to-end — from SHACL shapes through backend service to a CSS Grid frontend with inline editing.
**Demo:** User creates a Business Model Canvas and sees the 9 standard sections (Key Partners, Key Activities, Value Propositions, etc.) in a poster-style grid layout. Editing a section's content saves via the command API.

## Must-Haves

- `bp:BusinessModelCanvas` and `bp:BMCSection` OWL classes with SHACL shapes, ViewSpecs, and seed data in the existing `business-planning` model
- `bmc` renderer registered in `_VALID_RENDERERS`, `RENDERER_REGISTRY`, with elif branches in `generic_view()` and `generic_view_data()`
- Three service methods: `_detect_bmc_sections()`, `_build_bmc_select()`, `execute_bmc_query()`
- `bmc_view.html` Jinja2 template rendering a 10-column × 3-row CSS Grid with all 9 BMC sections
- `bmc.css` with section positioning via `[data-section-type]` selectors, color coding, dark mode support
- `bmc.js` with inline editing (textarea blur → `object.patch` with debounce) and dockview `stopPropagation` isolation
- Unit tests covering section detection, SPARQL building, result grouping, and edge cases

## Proof Level

- This slice proves: integration (model archive → backend detection → SPARQL → template → frontend editing)
- Real runtime required: yes (for live browser verification)
- Human/UAT required: yes (visual inspection of CSS Grid layout and dark mode)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v` — all tests pass
- All 5 JSON-LD model files parse via rdflib without error
- `parse_manifest()` validates with updated manifest
- `bmc` present in `_VALID_RENDERERS` and `RENDERER_REGISTRY`
- `grep -c "stopPropagation" frontend/static/js/bmc.js` returns ≥ 1
- `grep -c 'data-theme="dark"' frontend/static/css/bmc.css` returns ≥ 1
- CSS Grid positions all 9 sections via `[data-section-type]` selectors

## Observability / Diagnostics

- Runtime signals: `logger.info("generic_view: renderer=bmc type=%s ...")` in router; `logger.info("execute_bmc_query: type=%s total=%d sections=%d")` in service
- Inspection surfaces: `/browser/views/generic/bmc/data?type=<iri>` JSON endpoint for debugging BMC data
- Failure visibility: Error template when type has no 9-value `sh:in` property; JS `console.error("bmc: failed to patch ...")` on save failure
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `models/business-planning/` (S01 model archive structure), `backend/app/views/service.py` (ViewSpecService), `backend/app/views/router.py` (generic_view elif chain), `backend/app/views/registry.py` (RENDERER_REGISTRY)
- New wiring introduced: `bmc` renderer type in registry + router + service; BMC types in model archive; `bmc_view.html` + `bmc.js` + `bmc.css` frontend files
- What remains before the milestone is truly usable end-to-end: S03 (OKR/Decision Matrix), S04 (extended frameworks), S05 (E2E tests + documentation)

## Tasks

- [x] **T01: Extend model archive with BMC ontology, shapes, views, and seed data** `est:25m`
  - Why: BMC types must exist in the model before the backend can detect and query them. Extends the existing business-planning model with 2 new OWL classes, SHACL shapes with 9-value `sh:in` constraint, ViewSpecs for table and BMC renderer, seed data with a complete canvas, and icon definitions.
  - Files: `models/business-planning/ontology/business-planning.jsonld`, `models/business-planning/shapes/business-planning.jsonld`, `models/business-planning/views/business-planning.jsonld`, `models/business-planning/seed/business-planning.jsonld`, `models/business-planning/manifest.yaml`
  - Do: Add `bp:BusinessModelCanvas` (subClassOf `gist:Collection`) and `bp:BMCSection` (subClassOf `bp:FrameworkItem`) classes with properties (`bp:sectionType`, `bp:sectionContent`, `bp:belongsToCanvas`). Add SHACL NodeShapes with `sh:in` constraint listing 9 kebab-case section type values. Add ViewSpecs for BMC canvas table, section table, and section BMC renderer. Add seed data with 1 canvas + 9 sections with realistic content. Add icon definitions to manifest. All files are JSON-LD with inline `@context` — follow exact S01 patterns.
  - Verify: `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g), 'triples')"` shows increased triple count. Same for shapes, views, seed. `python3 -c "from app.models.manifest import parse_manifest; m=parse_manifest('models/business-planning'); print(m.name, m.version)"` still validates.
  - Done when: All 5 model files parse without error, manifest validates, ontology has 6+ OWL classes, seed has 17+ items (8 Eisenhower + 1 canvas + 9 sections minimum)

- [x] **T02: Wire BMC backend — service detection, SPARQL query, router branches, registry** `est:30m`
  - Why: The backend must detect BMC section properties, build SPARQL queries grouping sections by type, and route BMC renderer requests to the correct template. Mirrors the quadrant wiring pattern exactly.
  - Files: `backend/app/views/service.py`, `backend/app/views/router.py`, `backend/app/views/registry.py`, `backend/app/templates/browser/bmc_view.html`
  - Do: (1) In `registry.py`, add `"bmc"` entry with template `"browser/bmc_view.html"`. (2) In `router.py`, add `"bmc"` to `_VALID_RENDERERS` set. Add elif branch for `renderer == "bmc"` in `generic_view()` before the `else: # kanban` fallback — handle no-type, no-section-property, and happy path. Add `"bmc"` to the renderer tuple check in `generic_view_data()`. Add bmc data endpoint logic. (3) In `service.py`, add `_detect_bmc_sections(type_iri)` — find SHACL property with 9 `sh:in` values (prefer path containing "sectiontype"); `_build_bmc_select(type_iri, section_path, canvas_path, scope_filter)` — SPARQL SELECT grouping by sectionType; `execute_bmc_query(type_iri, ...)` — execute and bucket into 9 sections. (4) Create `bmc_view.html` Jinja2 template with `.view-flex-column` wrapper, `type_filter_pills`, `view_toolbar`, CSS Grid container, and lazy-load JS boot pattern. Use `section['items']` not `section.items` for dict access. Reference `/css/bmc.css` and `/js/bmc.js`.
  - Verify: `python3 -c "from app.views.registry import RENDERER_REGISTRY; assert 'bmc' in RENDERER_REGISTRY"` succeeds. `grep -c "bmc" backend/app/views/router.py` returns ≥ 5. Template references correct CSS/JS paths.
  - Done when: `bmc` in `_VALID_RENDERERS` and `RENDERER_REGISTRY`, elif branch in `generic_view()`, `_detect_bmc_sections` + `_build_bmc_select` + `execute_bmc_query` methods exist on ViewSpecService, `bmc_view.html` template renders 9 section boxes

- [x] **T03: Build BMC frontend — CSS Grid layout, inline editing JS, dark mode** `est:30m`
  - Why: The visual presentation layer — CSS Grid positions the 9 BMC sections in the canonical poster layout, and the JS handles inline content editing with debounced saves via the command API.
  - Files: `frontend/static/css/bmc.css`, `frontend/static/js/bmc.js`
  - Do: (1) `bmc.css`: 10-column × 3-row CSS Grid with `[data-section-type]` positioning selectors for all 9 sections. Section-specific color tints (soft pastels for each section). Dark mode via `html[data-theme="dark"]` overrides. `.view-flex-column` full-height integration. Section header styling, textarea styling for content editing, empty-state hint via CSS `:empty` pseudo-element. Responsive: 2-column layout at narrow widths. (2) `bmc.js`: IIFE following `quadrant.js` structure. `initBMC(boardEl)` attaches blur/input event listeners to textareas. Debounced save (500ms) via `object.patch` command with `bp:sectionContent` property. `stopPropagation()` on drag events to isolate from dockview. Listen for `sempkm:scope-changed` to re-fetch via htmx. Error handling with console.error and visual feedback on save failure.
  - Verify: `wc -l frontend/static/css/bmc.css` shows 200+ lines. `grep -c "stopPropagation" frontend/static/js/bmc.js` ≥ 1. `grep -c 'data-theme="dark"' frontend/static/css/bmc.css` ≥ 1. `grep -c "data-section-type" frontend/static/css/bmc.css` ≥ 9. CSS Grid positions all 9 sections.
  - Done when: CSS Grid renders 9-box poster layout, dark mode has readable contrast, inline editing triggers `object.patch`, JS isolates drag events from dockview

- [ ] **T04: Unit tests for BMC detection, query building, and result grouping** `est:20m`
  - Why: Pins the BMC backend pipeline with the same test structure as `test_quadrant.py` — detection logic, SPARQL generation, label mapping, and result grouping. Ensures future changes don't silently break the BMC renderer.
  - Files: `backend/tests/test_bmc.py`
  - Do: Create `test_bmc.py` following `test_quadrant.py` patterns exactly. Test classes: (1) `TestDetectBmcSections` — happy path with 9 `sh:in` values, keyword preference for "sectiontype" in path, rejection of properties with ≠9 values, no shapes service, no form, shapes exception. (2) `TestBuildBmcSelect` — basic query, with scope filter, OPTIONAL for sectionContent. (3) `TestExecuteBmcQuery` — groups into 9 section buckets, handles missing sections gracefully, handles empty results, error handling returns empty sections, total count correct. Use same `_make_property`, `_make_form`, `_build_service` helper pattern from `test_quadrant.py`.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v` — all tests pass, 20+ tests total
  - Done when: All tests pass, test count ≥ 20, covers detection + SPARQL building + result grouping + edge cases

## Files Likely Touched

- `models/business-planning/ontology/business-planning.jsonld`
- `models/business-planning/shapes/business-planning.jsonld`
- `models/business-planning/views/business-planning.jsonld`
- `models/business-planning/seed/business-planning.jsonld`
- `models/business-planning/manifest.yaml`
- `backend/app/views/registry.py`
- `backend/app/views/router.py`
- `backend/app/views/service.py`
- `backend/app/templates/browser/bmc_view.html`
- `frontend/static/js/bmc.js`
- `frontend/static/css/bmc.css`
- `backend/tests/test_bmc.py`
