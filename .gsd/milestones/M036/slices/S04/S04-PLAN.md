# S04: Extended Framework Library

**Goal:** All 13+ extended framework types are defined in the `business-planning` model archive with ontology classes, SHACL shapes, ViewSpecs, seed data, and manifest icons — and the 5 quadrant-based frameworks (SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix) render correctly via the existing quadrant renderer with framework-specific quadrant labels.
**Demo:** User installs the updated business-planning model, creates a SWOT Analysis, and sees items in a quadrant view labelled "Strengths / Weaknesses / Opportunities / Threats". Porter's Five Forces, PESTLE, Balanced Scorecard, RACI, and Value Chain types are all browsable via table views with correct SHACL forms.

## Must-Haves

- 5 new quadrant framework types (SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix) with container + item classes, axis properties with `sh:in` constraints, ViewSpecs declaring `quadrant` renderer
- `_quadrant_label()` extended with framework-specific label dicts (SWOT, BCG, Ansoff, Stakeholder, Risk) keyed by axis value tuples
- `_detect_quadrant_axes()` extended with keyword preferences for new axis properties (nature/valence, growth/share, power/interest, likelihood/impact, market/product)
- 6+ non-quadrant types (Porter, PESTLE, Balanced Scorecard, RACI, Value Chain, Lean Canvas) with shapes, table ViewSpecs, seed data
- Manifest updated with icon entries for all new types
- All 4 JSON-LD files parse cleanly via rdflib
- Existing 28 quadrant tests still pass; new tests cover SWOT/BCG/Ansoff/Stakeholder/Risk label mappings and keyword detection

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — all tests pass (existing 28 + ~10 new)
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(f'ontology: {len(g)} triples')"` — parses without error
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print(f'shapes: {len(g)} triples')"` — parses without error
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/views/business-planning.jsonld', format='json-ld'); print(f'views: {len(g)} triples')"` — parses without error
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/seed/business-planning.jsonld', format='json-ld'); print(f'seed: {len(g)} triples')"` — parses without error
- `rg 'sh:in' models/business-planning/shapes/business-planning.jsonld | wc -l` — count includes 10+ new `sh:in` constraints for quadrant axes and enum fields

## Observability / Diagnostics

- Runtime signals: `_detect_quadrant_axes` debug log includes type IRI and discovered x/y axis paths — new frameworks show their axis properties
- Inspection surfaces: `/browser/views/generic/quadrant/data?type=<iri>` returns JSON for any quadrant type — works for SWOT, BCG, etc. without code changes
- Failure visibility: `_quadrant_label()` falls back to generic "X: val / Y: val" if framework key lookup misses — non-fatal but visible in UI

## Integration Closure

- Upstream surfaces consumed: S01's quadrant renderer (`quadrant_view.html`, `quadrant.js`, `quadrant.css`), `_detect_quadrant_axes()`, `_quadrant_label()`, `execute_quadrant_query()` in `service.py`
- New wiring introduced: Extended `_QUADRANT_LABELS` dict and keyword preferences in `_detect_quadrant_axes()` — no new router branches, templates, or JS
- What remains before the milestone is truly usable end-to-end: S05 (cross-model edges, E2E tests, documentation)

## Tasks

- [ ] **T01: Quadrant framework types — SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix** `est:1h30m`
  - Why: 5 frameworks reuse the quadrant renderer but need ontology types, SHACL shapes with 2-value `sh:in` axes, ViewSpecs, seed data, manifest icons, and backend label/axis detection extensions
  - Files: `models/business-planning/ontology/business-planning.jsonld`, `models/business-planning/shapes/business-planning.jsonld`, `models/business-planning/views/business-planning.jsonld`, `models/business-planning/seed/business-planning.jsonld`, `models/business-planning/manifest.yaml`, `backend/app/views/service.py`, `backend/tests/test_quadrant.py`
  - Do: (1) Add 10 OWL classes (5 containers subclassing gist:Collection + 5 items subclassing bp:QuadrantItem) and 10 axis properties to ontology. (2) Add 10 NodeShapes with sh:in axis constraints to shapes. (3) Add 15 ViewSpecs (quadrant + table for each item type, table for each container). (4) Add seed data (1 container + 2–3 items per framework = ~15 entities). (5) Add 10 icon entries to manifest. (6) Restructure `_EISENHOWER_QUADRANT_LABELS` → `_QUADRANT_LABELS` multi-framework dict and update `_quadrant_label()` dispatch. (7) Add keyword pairs to `_detect_quadrant_axes()`. (8) Add ~10 unit tests for new label mappings and axis detection keywords.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — all pass
  - Done when: all 5 quadrant framework types have ontology, shapes, views, seed, icons, and the backend renders framework-specific labels

- [ ] **T02: Non-quadrant framework types — Porter, PESTLE, BSC, RACI, Value Chain, Lean Canvas** `est:1h`
  - Why: Remaining frameworks use existing table/kanban renderers and need only model archive additions — no backend code changes
  - Files: `models/business-planning/ontology/business-planning.jsonld`, `models/business-planning/shapes/business-planning.jsonld`, `models/business-planning/views/business-planning.jsonld`, `models/business-planning/seed/business-planning.jsonld`, `models/business-planning/manifest.yaml`
  - Do: (1) Add ~8 OWL classes (Porter container + PorterForce, PESTLEAnalysis + PESTLEFactor, BalancedScorecard + BSCItem, RACIMatrix + RACIEntry, ValueChain + VCActivity, LeanCanvas + LeanCanvasSection) and ~12 properties to ontology. (2) Add NodeShapes with sh:in enum constraints (5 Porter forces, 6 PESTLE categories, 4 BSC perspectives, 4 RACI roles, primary/support for VC). (3) Add table ViewSpecs for all types. (4) Add seed data (2–3 items per type). (5) Add icon entries to manifest. (6) Update ontology description to mention new frameworks.
  - Verify: `python3 -c "import rdflib; g=rdflib.Graph(); [g.parse(f'models/business-planning/{p}/business-planning.jsonld', format='json-ld') for p in ['ontology','shapes','views','seed']]; print(f'total: {len(g)} triples')"` — parses without error
  - Done when: all 6 non-quadrant types have complete ontology, shapes, views, seed, and icons

- [ ] **T03: Full verification — parse validation, test suite, manifest check** `est:20m`
  - Why: Final quality gate — ensures all JSON-LD files are structurally sound, existing tests still pass, new tests pass, and manifest validates with all type entries
  - Files: `models/business-planning/ontology/business-planning.jsonld`, `models/business-planning/shapes/business-planning.jsonld`, `models/business-planning/views/business-planning.jsonld`, `models/business-planning/seed/business-planning.jsonld`, `models/business-planning/manifest.yaml`, `backend/tests/test_quadrant.py`
  - Do: (1) Parse all 4 JSON-LD files via rdflib, report triple counts. (2) Run `pytest tests/test_quadrant.py -v` and confirm all pass. (3) Validate manifest.yaml has entries for all new types. (4) Spot-check: verify each new quadrant type has exactly 2 `sh:in` properties with exactly 2 values. (5) Fix any issues found.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — all pass, plus all 4 JSON-LD files parse
  - Done when: zero parse errors, zero test failures, manifest covers all types

## Files Likely Touched

- `models/business-planning/ontology/business-planning.jsonld`
- `models/business-planning/shapes/business-planning.jsonld`
- `models/business-planning/views/business-planning.jsonld`
- `models/business-planning/seed/business-planning.jsonld`
- `models/business-planning/manifest.yaml`
- `backend/app/views/service.py`
- `backend/tests/test_quadrant.py`
