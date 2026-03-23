---
id: T02
parent: S03
milestone: M036
provides:
  - OKR renderer wired through 4-layer backend pipeline (registry → _VALID_RENDERERS → elif → service)
  - Decision Matrix renderer wired through same 4-layer pipeline
  - 6 new ViewSpecService methods for OKR detection, query building, and progress computation
  - 6 new ViewSpecService methods for Decision Matrix detection, query building, and weighted scoring
  - OKR Jinja2 template with progress bars grouped by objective
  - Decision Matrix Jinja2 template with weighted scoring table and rank badges
  - JSON data endpoints for both renderers
key_files:
  - backend/app/views/registry.py
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/templates/browser/okr_view.html
  - backend/app/templates/browser/decision_matrix_view.html
key_decisions:
  - "Decision Matrix weight property derived by namespace from value property IRI (bp:value → bp:weight) rather than hardcoded, enabling model-agnostic weight resolution"
  - "OKR progress clamped to 0–100 with negative targetValue treated as division-by-zero (progress=0) for safety"
patterns_established:
  - "OKR service returns {objectives: [{iri, title, progress, key_results}], ungrouped: [...], total} — grouped by objective with aggregate progress as average of child KR percentages"
  - "Decision Matrix service returns {alternatives: [{iri, title, weighted_score, rank, scores}], criteria: [...], total_scores} — ranked descending with tie-aware ranking"
  - "Weight property IRI derived from value property IRI by replacing local name with 'weight' in same namespace — works for any model that follows this convention"
observability_surfaces:
  - "logger.info in router: generic_view: renderer=okr/decision-matrix with type and scope context"
  - "logger.info in service: execute_okr_query/execute_decision_matrix_query with total counts"
  - "JSON data endpoints: /browser/views/generic/okr/data and /browser/views/generic/decision-matrix/data"
  - "Error templates rendered when SHACL detection fails (missing currentValue/targetValue or value/alt/crit)"
duration: 18m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Wire OKR + Decision Matrix renderers through backend

**Wired okr and decision-matrix renderer types through the full 4-layer backend pipeline with server-side progress computation (currentValue/targetValue clamped 0-100) and weighted scoring (Σ weight×value ranked descending), plus Jinja2 templates and JSON data endpoints**

## What Happened

Added both renderer types to all four backend layers following the established quadrant/bmc pattern:

**Registry** — Added `"okr"` and `"decision-matrix"` entries to `RENDERER_REGISTRY` with template paths `browser/okr_view.html` and `browser/decision_matrix_view.html`.

**Router** — Added both to `_VALID_RENDERERS` set and the `generic_view_data()` renderer guard. Added elif branches in `generic_view()` for both with three-path handling: (a) no type selected → error template, (b) SHACL detection failed → error template with explanation, (c) happy path → execute query → build context → render template. Added matching branches in `generic_view_data()` returning JSON.

**Service — OKR** — Three methods on `ViewSpecService`:
- `_detect_okr_structure()`: Scans SHACL for xsd:decimal properties with "currentvalue"/"targetvalue" in path, plus ObjectProperty with "belongstoobjective" in path
- `_build_okr_select()`: SPARQL with OPTIONAL currentValue/targetValue/unit/objective joins
- `execute_okr_query()`: Computes `(currentValue/targetValue)*100` clamped 0–100, groups by objective, computes average progress per objective

**Service — Decision Matrix** — Three methods on `ViewSpecService`:
- `_detect_decision_matrix_structure()`: Scans SHACL for xsd:decimal "value" property, ObjectProperties targeting "alternative" and "criterion"
- `_build_decision_matrix_select()`: SPARQL joining Score→Alternative and Score→Criterion with weight from criterion (weight IRI derived from value IRI namespace)
- `execute_decision_matrix_query()`: Computes `Σ(weight×value)` per alternative, ranks descending with tie-aware ranking

**Templates** — Created both templates following the view-flex-column + type_filter_pills + view_toolbar + lazy-load JS boot pattern. OKR template renders objective cards with aggregate progress bars + child KR rows. Decision Matrix template renders a table with criteria columns, rank badges (🥇🥈🥉), and weighted totals. Both use `/css/` and `/js/` paths (not `/static/`), bracket notation for dict access.

## Verification

All 9 task-level verification checks pass:

1. `rg '"okr"' backend/app/views/registry.py` — present ✅
2. `rg '"decision-matrix"' backend/app/views/registry.py` — present ✅
3. `_VALID_RENDERERS` contains both okr and decision-matrix ✅
4. `elif renderer == "okr"` in router ✅
5. `elif renderer == "decision-matrix"` in router ✅
6. `execute_okr_query` and `execute_decision_matrix_query` in service ✅
7. Both template files exist ✅
8. OKR template uses `/css/okr.css` (not `/static/`) ✅
9. Both templates use bracket notation for dict access ✅

All three Python files pass AST parse check (no syntax errors).

Slice-level checks status (intermediate — T03/T04 not started):
- ✅ `rg '"okr"' backend/app/views/registry.py backend/app/views/router.py` — present in both
- ✅ `rg '"decision-matrix"' backend/app/views/registry.py backend/app/views/router.py` — present in both
- ✅ Templates exist
- ✅ 32 graph entries in ontology (up from S02 baseline)
- ⏳ CSS/JS files — T03
- ⏳ Unit tests — T04

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg '"okr"' backend/app/views/registry.py` | 0 | ✅ present | 0.1s |
| 2 | `rg '"decision-matrix"' backend/app/views/registry.py` | 0 | ✅ present | 0.1s |
| 3 | `rg '_VALID_RENDERERS' backend/app/views/router.py` | 0 | ✅ both in set | 0.1s |
| 4 | `rg 'elif renderer == "okr"' backend/app/views/router.py` | 0 | ✅ present | 0.1s |
| 5 | `rg 'elif renderer == "decision-matrix"' backend/app/views/router.py` | 0 | ✅ present | 0.1s |
| 6 | `rg 'execute_okr_query\|execute_decision_matrix_query' backend/app/views/service.py` | 0 | ✅ both present | 0.1s |
| 7 | `test -f backend/app/templates/browser/okr_view.html && test -f backend/app/templates/browser/decision_matrix_view.html` | 0 | ✅ both exist | 0.1s |
| 8 | `rg '/css/okr.css' backend/app/templates/browser/okr_view.html` | 0 | ✅ uses /css/ | 0.1s |
| 9 | `rg "\['" backend/app/templates/browser/okr_view.html backend/app/templates/browser/decision_matrix_view.html` | 0 | ✅ bracket notation | 0.1s |
| 10 | `python -c "import ast; ast.parse(open('app/views/service.py').read())"` (from backend/) | 0 | ✅ no syntax errors | 0.5s |
| 11 | `python -c "import ast; ast.parse(open('app/views/router.py').read())"` (from backend/) | 0 | ✅ no syntax errors | 0.3s |
| 12 | `python -c "import ast; ast.parse(open('app/views/registry.py').read())"` (from backend/) | 0 | ✅ no syntax errors | 0.1s |

## Diagnostics

- OKR data endpoint: `curl http://localhost:3901/browser/views/generic/okr/data?type=urn:sempkm:model:business-planning:KeyResult`
- DM data endpoint: `curl http://localhost:3901/browser/views/generic/decision-matrix/data?type=urn:sempkm:model:business-planning:Score`
- Check renderer registration: `python3 -c "from app.views.registry import RENDERER_REGISTRY; print([k for k in RENDERER_REGISTRY])"`
- Grep for logger signals: `rg 'execute_okr_query|execute_decision_matrix_query' backend/app/views/service.py`
- Check SHACL detection: search for `_detect_okr_structure` or `_detect_decision_matrix_structure` in service logs

## Deviations

- Decision Matrix weight property IRI is derived dynamically from the value property's namespace (replace local name with "weight") rather than hardcoding `bp:weight`. This makes the approach work for any model that follows the convention of co-locating value and weight properties in the same namespace, with fallback to a well-known IRI.
- Added 4th return value to `_detect_decision_matrix_structure()` (always None) to maintain consistent 4-tuple return pattern with OKR detection, even though weight is fetched via SPARQL join rather than SHACL detection.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/registry.py` — Added "okr" and "decision-matrix" entries to RENDERER_REGISTRY
- `backend/app/views/router.py` — Added both to _VALID_RENDERERS, elif branches in generic_view(), data branches in generic_view_data()
- `backend/app/views/service.py` — Added 6 methods: _detect_okr_structure, _build_okr_select, execute_okr_query, _detect_decision_matrix_structure, _build_decision_matrix_select, execute_decision_matrix_query
- `backend/app/templates/browser/okr_view.html` — OKR template with progress bars grouped by objective, lazy-load JS boot
- `backend/app/templates/browser/decision_matrix_view.html` — Decision Matrix table with rank badges, weighted totals, lazy-load JS boot
- `.gsd/milestones/M036/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
