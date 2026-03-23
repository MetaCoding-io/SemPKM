---
id: M036
provides:
  - business-planning Mental Model archive (5 JSON-LD files, 34 OWL classes, 1665 SHACL triples, 479 seed triples)
  - 4 custom view renderers (quadrant, bmc, okr, decision-matrix) wired through registry, router, service, template, JS, CSS
  - Eisenhower Matrix 2×2 quadrant view with drag-to-reclassify updating RDF properties via object.patch
  - Business Model Canvas 9-box poster layout with inline editing and debounced saves
  - OKR progress bars with percentage computation (current/target, clamped 0-100%)
  - Decision Matrix weighted scoring with auto-ranked alternatives (Σ weight × score)
  - 15 strategic analysis frameworks across 5 categories (prioritization, strategy, business design, goals, resources)
  - Cross-model edges (bp:relatedTask → bpkm:Task, bp:relatedGoalOutcome → ppv:GoalOutcome)
  - 124 unit tests (28 quadrant + 31 bmc + 25 okr + 26 decision matrix + 14 extended validation)
  - E2E Playwright spec covering model install → object creation → 4 renderer views → SPARQL query
  - User guide section "5. Business Planning" in chapter 39 (Mental Model Catalog) documenting all 15 frameworks
key_decisions:
  - Used gist:Category/gist:Collection upper ontology alignment for all framework types (consistent with basic-pkm pattern)
  - Kept axis values as xsd:string with sh:in constraints rather than enum IRIs — simpler drag-drop updates via object.patch
  - General axis detection (_detect_quadrant_axes finds any 2-value sh:in properties) rather than hardcoded to Eisenhower
  - BMC section detection uses 9-value sh:in count heuristic — not hardcoded property IRI
  - 10-column CSS Grid for BMC poster (not 5-column doubled) for precise section spanning
  - OKR/Decision Matrix structure detection via SHACL datatype analysis (xsd:decimal for numeric fields)
  - Extended frameworks use existing renderers (table, kanban, quadrant) rather than new custom renderers
  - Single comprehensive E2E test to stay within magic-link rate limit (1 session, sequential assertions)
patterns_established:
  - 4-layer renderer wiring pattern (registry → _VALID_RENDERERS → elif branch → service methods) proven repeatable across 4 renderers
  - SHACL-driven field detection heuristic: sh:datatype + sh:in count + keyword preference in path name
  - Drag-to-reclassify IIFE structure (stopPropagation on 4 events, optimistic DOM move, revert on failure) reused from kanban
  - Dark mode rgba() tint approach (0.07 alpha light, 0.12 alpha dark) consistent across all 4 renderer CSS files
  - Inline editing with debounce timer map keyed by IRI (BMC pattern, reusable for future editable views)
  - JSON debug endpoints (/browser/views/generic/{renderer}/data) for each custom renderer
observability_surfaces:
  - logger.info("generic_view: renderer={type} ...") on every custom view request (quadrant, bmc, okr, decision-matrix)
  - logger.info("execute_{renderer}_query: type=%s total=%d") after each renderer query execution
  - /browser/views/generic/quadrant/data?type=<iri> — JSON endpoint for quadrant debugging
  - /browser/views/generic/bmc/data?type=<iri> — JSON endpoint for BMC debugging
  - console.error in each JS file on API failure (patch, save)
  - CSS flash classes (.bmc-save-error, .bmc-save-ok) for visual save feedback
  - Error template with descriptive message when type lacks required SHACL constraints for a renderer
requirement_outcomes:
  - id: BIZ-01
    from_status: active
    to_status: validated
    proof: 5-file model archive validates via parse_manifest() as business-planning v1.0.0; rdflib parses all JSON-LD (ontology 423 + shapes 1665 + views 255 + seed 479 = 2822 triples); 34 OWL classes; E2E spec covers model install
  - id: BIZ-02
    from_status: active
    to_status: validated
    proof: quadrant renderer wired through registry/router/service/template; _detect_quadrant_axes() + execute_quadrant_query() service methods; quadrant.js drag-to-reclassify with dockview isolation (4 stopPropagation calls); 28 unit tests pass; E2E spec covers quadrant view rendering
duration: ~240m (S01:87m + S02:45m + S03:~45m + S04:~63m + S05:~42m)
verification_result: passed
completed_at: 2026-03-23
---

# M036: Business Planning Mental Models & Custom Renderers

**Shipped a library of 15 business planning frameworks as typed RDF data with 4 custom visual renderers — quadrant grids, poster canvases, progress bars, and scoring tables — backed by 124 unit tests, an E2E spec, and full user documentation.**

## What Happened

**S01 (Eisenhower Matrix)** established the foundation: a `business-planning` model archive following the exact 5-file JSON-LD structure of basic-pkm, with shared base classes (`bp:FrameworkItem`, `bp:QuadrantItem`) for downstream slices. The quadrant renderer was the highest-risk item — it required a new renderer type wired through 3 backend layers (registry, `_VALID_RENDERERS`, router elif), a SHACL-driven axis detection pipeline (`_detect_quadrant_axes` finds properties with exactly 2 `sh:in` values), SPARQL query building with non-OPTIONAL bindings, a Jinja2 template with 2×2 CSS Grid, and a drag-to-reclassify JS IIFE following the proven kanban pattern (stopPropagation for dockview isolation, optimistic DOM move with revert). 28 unit tests pin the pipeline.

**S02 (Business Model Canvas)** followed the exact same 4-layer wiring pattern, confirming it's repeatable. The BMC renderer detects types with a 9-value `sh:in` constraint (matching the 9 standard BMC sections), builds SPARQL with OPTIONAL sectionContent, and renders a 10-column CSS Grid poster with 9 color-coded sections. Inline editing uses textarea elements with debounced `object.patch` saves. 31 unit tests.

**S03 (OKR + Decision Matrix)** added two more renderers for computed-value frameworks. OKR detects two `xsd:decimal` SHACL properties (current/target), computes progress percentage (clamped 0–100%), and groups Key Results under Objectives with visual progress bars. Decision Matrix detects a value property plus alternative/criterion ObjectProperty joins, computes weighted scores (Σ weight × score), and auto-ranks alternatives. 51 unit tests covering edge cases (division by zero, missing values, tie handling).

**S04 (Extended Frameworks)** expanded the ontology from 4 to 34 OWL classes across 15 frameworks: SWOT, Porter's Five Forces, PESTLE, Balanced Scorecard, RACI, Value Chain, Lean Canvas, BCG Matrix, Ansoff Matrix, Stakeholder Map, and Risk Matrix — plus the 4 core types from S01-S03. Each framework got SHACL shapes, ViewSpecs pointing to appropriate renderers (quadrant for SWOT/BCG/Ansoff/Stakeholder/Risk, table/kanban for the rest), and seed data. The `_quadrant_label()` function was extended with framework-specific label mappings.

**S05 (Integration)** tied everything together: 3 cross-model ObjectProperty declarations (bp:relatedTask → bpkm:Task, bp:relatedGoalOutcome → ppv:GoalOutcome, bp:relatedProject → bpkm:Project), a 344-line E2E Playwright spec exercising the full vertical (install → create → render → SPARQL → cleanup), and a comprehensive user guide section documenting all 15 frameworks with field references.

## Cross-Slice Verification

**Success criterion: model installs and shows new types** — manifest validates as `business-planning v1.0.0` with namespace `urn:sempkm:model:business-planning:`. All 4 JSON-LD files parse cleanly via rdflib (2822 total triples). 34 OWL classes defined. E2E spec covers model install flow.

**Success criterion: Eisenhower quadrant view with drag-to-reclassify** — quadrant renderer wired in `_VALID_RENDERERS`, `RENDERER_REGISTRY`, and router elif branch. `_detect_quadrant_axes()` finds 2-value `sh:in` properties. `quadrant.js` handles drag events with stopPropagation, optimistic DOM move, atomic `object.patch` for both axes. 28 unit tests pass.

**Success criterion: BMC 9-box poster with inline editing** — bmc renderer wired. 10-column CSS Grid with 9 color-coded sections. `bmc.js` provides textarea inline editing with debounced saves. 31 unit tests pass.

**Success criterion: OKR progress bars from current/target** — okr renderer computes progress percentage, clamped 0–100%, grouped by Objective. Visual progress bars in template. 25 unit tests pass including division-by-zero and overflow edge cases.

**Success criterion: Decision Matrix weighted scores and rankings** — decision-matrix renderer computes Σ(weight × score) per alternative, sorts by total descending. 26 unit tests pass including tie handling and missing criteria.

**Success criterion: SPARQL structured results** — all types are queryable via standard SPARQL patterns. E2E spec includes a SPARQL query step verifying structured results from EisenhowerItem instances.

**Success criterion: cross-model edges** — `bp:relatedTask`, `bp:relatedGoalOutcome`, and `bp:relatedProject` ObjectProperty declarations with appropriate rdfs:domain and rdfs:range. Shapes include these as reference fields.

**Success criterion: valid SHACL forms** — 1665 SHACL triples with NodeShapes, PropertyShapes, and PropertyGroups for all 34 types. Forms auto-generate from shapes.

**Success criterion: dark mode** — all 4 CSS files include dark mode rules (quadrant: 10, bmc: 22, okr: 12, decision-matrix: 14) using the `html[data-theme="dark"]` selector and rgba() tint approach.

**Success criterion: E2E tests** — `e2e/tests/36-business-planning/business-planning.spec.ts` (344 lines) covers model install, object creation for all 4 custom renderers, SPARQL query verification, and cleanup.

**Success criterion: user guide** — Section "5. Business Planning" in `docs/guide/39-mental-model-catalog.md` documents all 15 frameworks with field references, relationships, and renderer information.

**Unit tests: 124 passed in 0.62s** — `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py tests/test_bmc.py tests/test_okr.py tests/test_decision_matrix.py -v`

## Requirement Changes

- BIZ-01: active → validated — 5-file model archive, manifest validates, 2822 RDF triples, 34 OWL classes, E2E install coverage
- BIZ-02: active → validated — quadrant renderer full vertical (detection → SPARQL → template → drag → patch), 28 unit tests, E2E coverage

## Forward Intelligence

### What the next milestone should know
- The `business-planning` namespace is `urn:sempkm:model:business-planning:` with prefix `bp:`. The model defines 34 OWL classes across 15 strategic frameworks.
- The 4-layer renderer wiring pattern (registry → `_VALID_RENDERERS` → router elif → service methods) is now proven across 4 custom renderers. Any future renderer type should follow this exact pattern.
- SHACL-driven field detection (axis count, datatype, keyword preference) is the established approach for renderer-specific type analysis. It generalizes across renderers.
- Cross-model edges exist but are declared as optional reference fields — they depend on basic-pkm and ppv models being installed alongside business-planning.

### What's fragile
- `_quadrant_label()` has per-framework label dicts — any new framework using the quadrant renderer needs its labels added manually
- The router's elif chain for renderers is now 11 entries long (table, card, graph, kanban, calendar, map, timeline, quadrant, bmc, okr, decision-matrix) — each new renderer adds ~100 lines. The `register_renderer()` infrastructure exists but is dead code; activating it would be a valuable refactor.
- BMC SPARQL builder hardcodes `urn:sempkm:model:business-planning:sectionContent` — acceptable coupling but not generic
- Extended framework seed data is minimal (1-2 instances per type) — enough for form testing but not for compelling demos

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py tests/test_bmc.py tests/test_okr.py tests/test_decision_matrix.py -v` — 124 tests pin all 4 renderer pipelines
- `/browser/views/generic/{renderer}/data?type=<iri>` — JSON debug endpoints for each renderer (quadrant, bmc)
- `from rdflib import Graph; g=Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld')` — 1665 triples confirms shapes are intact
- E2E: `npx playwright test e2e/tests/36-business-planning/` against running Docker stack

### What assumptions changed
- Originally planned to hardcode Eisenhower axis values — the general `_detect_quadrant_axes` approach (any 2-value sh:in) turned out cleaner and enabled S04 frameworks (SWOT, BCG, Ansoff, Stakeholder, Risk) to reuse the quadrant renderer without code changes
- Expected BMC to need a unique detection heuristic — the 9-value sh:in count works naturally and is specific enough to avoid false positives
- OKR and Decision Matrix both needed xsd:decimal detection from SHACL datatypes — the pattern was sufficiently different from quadrant/bmc that each got its own detection method rather than a shared abstraction

## Files Created/Modified

- `models/business-planning/manifest.yaml` — Model manifest (v1.0.0, namespace, prefixes, entrypoints)
- `models/business-planning/ontology/business-planning.jsonld` — 34 OWL classes, 15 frameworks (734 lines, 423 triples)
- `models/business-planning/shapes/business-planning.jsonld` — SHACL NodeShapes with PropertyGroups, sh:in constraints (2009 lines, 1665 triples)
- `models/business-planning/views/business-planning.jsonld` — ViewSpecs for all framework types (255 triples)
- `models/business-planning/seed/business-planning.jsonld` — Seed data for all frameworks (479 triples)
- `backend/app/views/router.py` — 4 new renderer elif branches (quadrant, bmc, okr, decision-matrix) + _VALID_RENDERERS
- `backend/app/views/service.py` — 12+ new methods: detect/build/execute/label for each renderer type
- `backend/app/views/registry.py` — 4 new RENDERER_REGISTRY entries
- `backend/app/templates/browser/quadrant_view.html` — 2×2 grid template (102 lines)
- `backend/app/templates/browser/bmc_view.html` — 9-box poster template
- `backend/app/templates/browser/okr_view.html` — Progress bar template
- `backend/app/templates/browser/decision_matrix_view.html` — Scoring table template
- `frontend/static/js/quadrant.js` — Drag-to-reclassify IIFE (189 lines)
- `frontend/static/js/bmc.js` — Inline editing with debounced saves (157 lines)
- `frontend/static/js/okr.js` — Click-to-expand objective groups (218 lines)
- `frontend/static/js/decision-matrix.js` — Score highlighting (169 lines)
- `frontend/static/css/quadrant.css` — 2×2 Grid + dark mode (286 lines)
- `frontend/static/css/bmc.css` — 10-column poster + dark mode (443 lines)
- `frontend/static/css/okr.css` — Progress bars + dark mode (320 lines)
- `frontend/static/css/decision-matrix.css` — Scoring table + dark mode (320 lines)
- `backend/tests/test_quadrant.py` — 28 unit tests (779 lines)
- `backend/tests/test_bmc.py` — 31 unit tests (711 lines)
- `backend/tests/test_okr.py` — 25 unit tests (612 lines)
- `backend/tests/test_decision_matrix.py` — 26 unit tests (665 lines)
- `e2e/tests/36-business-planning/business-planning.spec.ts` — E2E spec (344 lines)
- `docs/guide/39-mental-model-catalog.md` — Section 5: Business Planning (all 15 frameworks documented)
