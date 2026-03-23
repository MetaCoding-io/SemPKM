# S03: OKR Progress + Decision Matrix Weighted Scoring

**Goal:** Ship two computed-value renderers — OKR progress bars with server-side percentage computation and Decision Matrix weighted scoring with auto-ranked alternatives — following the proven 4-layer vertical pattern from S01/S02.
**Demo:** User creates an OKR Objective with Key Results showing progress bars colored by completion percentage; user creates a Decision Matrix with weighted criteria and sees alternatives auto-ranked by computed scores.

## Must-Haves

- OKR types (bp:Objective, bp:KeyResult) with SHACL shapes in the business-planning model
- Decision Matrix types (bp:DecisionMatrix, bp:Criterion, bp:Alternative, bp:Score) with SHACL shapes
- Server-side OKR progress computation: `(currentValue / targetValue) * 100` clamped 0–100, with division-by-zero guard
- Server-side Decision Matrix weighted scoring: `Σ(weight × value)` per alternative, ranked descending
- `okr` and `decision-matrix` renderer types wired through registry, `_VALID_RENDERERS`, elif branches, and service methods
- OKR template with progress bars colored green/amber/red by percentage, grouped by objective
- Decision Matrix template with sortable weighted table showing rank badges
- Both renderers support dark mode via `html[data-theme="dark"]`
- Seed data: 1 objective + 3 key results; 1 matrix + 3 criteria + 3 alternatives + 9 scores
- Unit tests covering detection, SPARQL building, computation, grouping, and edge cases for both renderers

## Proof Level

- This slice proves: contract (computed values correct) + integration (renderer wired through full backend pipeline)
- Real runtime required: no — unit tests exercise service methods with mocked triplestore
- Human/UAT required: no — visual verification deferred to S05 E2E

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_okr.py tests/test_decision_matrix.py -v` — all tests pass
- `python3 -c "import json; data=json.load(open('models/business-planning/ontology/business-planning.jsonld')); print(len(data['@graph']), 'graph entries')"` — increased from S02 baseline
- `rg '"okr"' backend/app/views/registry.py backend/app/views/router.py` — present in both
- `rg '"decision-matrix"' backend/app/views/registry.py backend/app/views/router.py` — present in both
- `rg 'data-theme="dark"' frontend/static/css/okr.css frontend/static/css/decision-matrix.css` — non-zero in both
- `test -f frontend/static/js/okr.js && test -f frontend/static/js/decision-matrix.js` — exist
- `test -f backend/app/templates/browser/okr_view.html && test -f backend/app/templates/browser/decision_matrix_view.html` — exist

## Observability / Diagnostics

- Runtime signals: `logger.info("generic_view: renderer=okr ...")` and `logger.info("generic_view: renderer=decision-matrix ...")` in router; `logger.info("execute_okr_query: type=%s ...")` and `logger.info("execute_decision_matrix_query: type=%s ...")` in service
- Inspection surfaces: `/browser/views/generic/okr/data?type=<iri>` and `/browser/views/generic/decision-matrix/data?type=<iri>` JSON endpoints
- Failure visibility: error template when type lacks required SHACL structure; `console.error` in JS on patch failure
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `backend/app/views/registry.py` (RENDERER_REGISTRY), `backend/app/views/router.py` (elif chain, _VALID_RENDERERS, generic_view_data), `backend/app/views/service.py` (ViewSpecService), model archive files from S01
- New wiring introduced: 2 renderer types through the full elif chain, 6+ service methods with server-side arithmetic
- What remains before the milestone is truly usable end-to-end: S04 (extended frameworks), S05 (cross-model edges, E2E tests, docs)

## Tasks

- [ ] **T01: Extend model archive with OKR + Decision Matrix types** `est:25m`
  - Why: OKR and Decision Matrix types must exist in the model archive before backend wiring can reference them — this adds 6 OWL classes, SHACL shapes, ViewSpecs, seed data, and manifest icon entries
  - Files: `models/business-planning/ontology/business-planning.jsonld`, `models/business-planning/shapes/business-planning.jsonld`, `models/business-planning/views/business-planning.jsonld`, `models/business-planning/seed/business-planning.jsonld`, `models/business-planning/manifest.yaml`
  - Do: Add 6 OWL classes (bp:Objective, bp:KeyResult, bp:DecisionMatrix, bp:Criterion, bp:Alternative, bp:Score) with properties. Add SHACL NodeShapes with PropertyGroups. Add ViewSpecs (table + okr for OKR types, table + decision-matrix for DM types). Add seed data (1 objective + 3 KRs + 1 matrix + 3 criteria + 3 alternatives + 9 scores). Add 6 icon entries to manifest. Use `bp:` namespace, inline `@context`, `item['key']` in any Jinja2.
  - Verify: `python3 -c "import json; data=json.load(open('models/business-planning/ontology/business-planning.jsonld')); [print(e['@id']) for e in data['@graph'] if 'owl:Class' in str(e.get('@type',''))]"` — shows all 12 classes (6 existing + 6 new)
  - Done when: All 5 model files parse without error, ontology has 12 OWL classes, shapes define NodeShapes for all 6 new types, seed data is realistic and references correct IRIs

- [ ] **T02: Wire OKR + Decision Matrix renderers through backend** `est:35m`
  - Why: The 4-layer backend wiring (registry → _VALID_RENDERERS → elif branches → service methods) must be in place before templates can render — this includes the novel server-side computation logic for progress percentages and weighted scores
  - Files: `backend/app/views/registry.py`, `backend/app/views/router.py`, `backend/app/views/service.py`, `backend/app/templates/browser/okr_view.html`, `backend/app/templates/browser/decision_matrix_view.html`
  - Do: (1) Add `okr` and `decision-matrix` entries to RENDERER_REGISTRY. (2) Add both to `_VALID_RENDERERS` set. (3) Add elif branches in `generic_view()` for both renderers with error/empty/happy-path handling. (4) Add data endpoint branches in `generic_view_data()`. (5) Add 6+ service methods: `_detect_okr_structure()` finds currentValue/targetValue decimal properties + belongsToObjective ObjectProperty; `_build_okr_select()` builds SPARQL; `execute_okr_query()` groups by objective and computes progress % clamped 0–100 with div-by-zero guard. `_detect_decision_matrix_structure()` finds weight/value decimal properties + alternative/criterion ObjectProperties; `_build_decision_matrix_select()` builds SPARQL with 3-type join; `execute_decision_matrix_query()` computes Σ(weight × value) per alternative, ranks descending. (6) Create Jinja2 templates following view-flex-column + type_filter_pills + view_toolbar pattern, using `item['key']` bracket notation for dict access.
  - Verify: `rg '"okr"' backend/app/views/registry.py backend/app/views/router.py` — present in both; `rg '"decision-matrix"' backend/app/views/registry.py backend/app/views/router.py` — present in both; templates exist and use `/css/` + `/js/` paths (not `/static/`)
  - Done when: Both renderers wired through all 4 layers, service methods handle computation with edge cases, templates render server-side content with lazy-load JS boot

- [ ] **T03: Create OKR + Decision Matrix frontend (CSS + JS)** `est:25m`
  - Why: The renderers need styled interactive frontends — OKR progress bars with color coding and Decision Matrix sortable table with rank badges, both supporting dark mode
  - Files: `frontend/static/css/okr.css`, `frontend/static/js/okr.js`, `frontend/static/css/decision-matrix.css`, `frontend/static/js/decision-matrix.js`
  - Do: (1) `okr.css`: progress bar styling (green ≥70%, amber 30–69%, red <30%), objective card layout, `.view-flex-column` full height, dark mode via `html[data-theme="dark"]`, responsive. (2) `okr.js`: IIFE with `initOKR(boardEl)`, click-to-edit on currentValue via `object.patch`, `sempkm:scope-changed` listener for refresh, `stopPropagation()` on drag events for dockview isolation. (3) `decision-matrix.css`: weighted table layout, rank badges (🥇🥈🥉), score cell color gradient, dark mode, responsive. (4) `decision-matrix.js`: IIFE with `initDecisionMatrix(boardEl)`, client-side sort on column click, `sempkm:scope-changed` listener, `stopPropagation()` for dockview isolation. All SVG icon sizing must use CSS with `flex-shrink: 0`.
  - Verify: `test -f frontend/static/js/okr.js && test -f frontend/static/css/okr.css && test -f frontend/static/js/decision-matrix.js && test -f frontend/static/css/decision-matrix.css` — all 4 exist; `rg 'data-theme="dark"' frontend/static/css/okr.css frontend/static/css/decision-matrix.css` — non-zero in both; `rg 'stopPropagation' frontend/static/js/okr.js frontend/static/js/decision-matrix.js` — present in both
  - Done when: Both CSS files have dark mode coverage, both JS files have IIFE structure with scope-changed listener and dockview isolation, progress bar colors match spec (green/amber/red), rank badges visible in decision matrix

- [ ] **T04: Unit tests for OKR + Decision Matrix pipelines** `est:20m`
  - Why: Computed values need thorough test coverage — progress percentage edge cases (0/0, over-target, negative) and weighted scoring arithmetic must be pinned by tests before integration
  - Files: `backend/tests/test_okr.py`, `backend/tests/test_decision_matrix.py`
  - Do: Follow exact test_quadrant.py / test_bmc.py pattern with `_make_property()`, `_make_form()`, `_build_service()` helpers. (1) `test_okr.py`: TestDetectOkrStructure (happy path, keyword preference, missing targetValue, no decimals), TestBuildOkrSelect (basic query, scope filter, objective join), TestExecuteOkrQuery (progress computation: 50/100=50%, 0/0=0%, 120/100=100% clamped, grouping by objective, empty results, error handling, dedup). (2) `test_decision_matrix.py`: TestDetectDecisionMatrixStructure (happy path, weight detection, alternative/criterion object property detection), TestBuildDecisionMatrixSelect (basic query, scope filter), TestExecuteDecisionMatrixQuery (weighted scoring: Σ(weight × value), ranking order, tie handling, empty results, error handling, missing scores).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_okr.py tests/test_decision_matrix.py -v` — all tests pass with 0 failures
  - Done when: ≥15 tests per file covering detection, query building, computation edge cases, and error handling; all pass

## Files Likely Touched

- `models/business-planning/ontology/business-planning.jsonld`
- `models/business-planning/shapes/business-planning.jsonld`
- `models/business-planning/views/business-planning.jsonld`
- `models/business-planning/seed/business-planning.jsonld`
- `models/business-planning/manifest.yaml`
- `backend/app/views/registry.py`
- `backend/app/views/router.py`
- `backend/app/views/service.py`
- `backend/app/templates/browser/okr_view.html`
- `backend/app/templates/browser/decision_matrix_view.html`
- `frontend/static/css/okr.css`
- `frontend/static/js/okr.js`
- `frontend/static/css/decision-matrix.css`
- `frontend/static/js/decision-matrix.js`
- `backend/tests/test_okr.py`
- `backend/tests/test_decision_matrix.py`
