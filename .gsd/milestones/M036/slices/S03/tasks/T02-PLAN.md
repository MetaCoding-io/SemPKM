---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T02: Wire OKR + Decision Matrix renderers through backend

**Slice:** S03 — OKR Progress + Decision Matrix Weighted Scoring
**Milestone:** M036

## Description

Wire two new renderer types (`okr` and `decision-matrix`) through the full 4-layer backend pipeline: registry → `_VALID_RENDERERS` → elif branches → service methods. This follows the exact same pattern proven by `quadrant` (S01) and `bmc` (S02). The novel concern is server-side computation: OKR progress percentages and Decision Matrix weighted scores must be computed in the service methods before passing to templates.

## Steps

1. **Registry + valid renderers** — Add `"okr"` and `"decision-matrix"` entries to `RENDERER_REGISTRY` in `backend/app/views/registry.py` with template paths `browser/okr_view.html` and `browser/decision_matrix_view.html`. Add both strings to the `_VALID_RENDERERS` set in `backend/app/views/router.py`. Also add both to the renderer check in `generic_view_data()` (line ~1058: the `if renderer not in (...)` guard).

2. **Service methods — OKR** — Add 3 methods to `ViewSpecService` in `backend/app/views/service.py`:
   - `_detect_okr_structure(type_iri)`: Get form via `_shapes_service.get_form_for_type()`. Find properties with `datatype == "http://www.w3.org/2001/XMLSchema#decimal"` whose paths contain "currentvalue" or "targetvalue" (case-insensitive via `_local_name(prop.path).lower()`). Also find an ObjectProperty (has `target_class`) whose path contains "belongstoobjective". Return `(current_prop, target_prop, unit_prop, objective_prop)` or `(None, None, None, None)`.
   - `_build_okr_select(type_iri, current_path, target_path, unit_path=None, objective_path=None, scope_filter=None)`: Build SPARQL SELECT with `?s ?title ?currentValue ?targetValue ?unit ?objective ?objTitle`. currentValue and targetValue are OPTIONAL. unit is OPTIONAL. objective join is OPTIONAL. Include scope sub-select if provided. Use `PREFIX dcterms:` for title.
   - `execute_okr_query(type_iri, current_prop, target_prop, unit_prop=None, objective_prop=None, scope_filter=None)`: Execute query, compute progress per KeyResult: `float(currentValue) / float(targetValue) * 100`, clamped to `max(0, min(100, val))`. Division-by-zero: if targetValue is 0 or missing, progress = 0. Group by objective IRI. Each objective gets `title`, `progress` (average of child KR percentages), and `key_results` list. Return `{"objectives": [...], "ungrouped": [...], "total": N}`.

3. **Service methods — Decision Matrix** — Add 3 methods to `ViewSpecService`:
   - `_detect_decision_matrix_structure(type_iri)`: Find decimal properties whose paths contain "weight" or "value" (for Score type). Find ObjectProperties whose target_class path contains "alternative" or "criterion". Return `(weight_prop, value_prop, alt_prop, crit_prop)` or `(None, None, None, None)`.
   - `_build_decision_matrix_select(type_iri, value_path, alt_path, crit_path, scope_filter=None)`: Build SPARQL SELECT joining Score→Alternative and Score→Criterion: `?score ?alt ?altTitle ?crit ?critTitle ?critWeight ?scoreValue`. All joins are required (non-OPTIONAL) since a score without both references is meaningless. Criterion weight comes via the criterion's weight property. Scope sub-select optional.
   - `execute_decision_matrix_query(type_iri, value_prop, alt_prop, crit_prop, scope_filter=None)`: Execute query. Group by alternative. For each alternative compute `weighted_score = Σ(critWeight × scoreValue)`. Rank by descending weighted_score (ties get same rank). Return `{"alternatives": [...], "criteria": [...], "total_scores": N}`. Each alternative has `iri`, `title`, `weighted_score`, `rank`, and `scores` dict keyed by criterion IRI.

4. **Router elif branches** — Add elif branches in `generic_view()` for `"okr"` and `"decision-matrix"`, following the exact pattern from `"quadrant"` and `"bmc"`: (a) no-type-selected → error template, (b) detection failed → error template, (c) happy path → execute query → build context → render template. Add branches in `generic_view_data()` for both.

5. **Jinja2 templates** — Create `backend/app/templates/browser/okr_view.html` and `backend/app/templates/browser/decision_matrix_view.html`. Both must follow the established structure: `view-flex-column` wrapper → `{% include "browser/type_filter_pills.html" %}` → `{% include "browser/view_toolbar.html" %}` → renderer content → lazy-load JS boot. Use `/css/okr.css` and `/js/okr.js` (NOT `/static/` — see KNOWLEDGE entry about nginx). Use bracket notation `item['key']` for dict access in Jinja2 (NOT `item.key`). OKR template: loop over `objectives`, each renders a card with title + aggregate progress bar + child key_results rows. Decision Matrix template: table with alternatives as rows, criteria as columns + total + rank columns.

## Must-Haves

- [ ] `okr` and `decision-matrix` in RENDERER_REGISTRY with correct template paths
- [ ] Both in `_VALID_RENDERERS` set
- [ ] elif branches in `generic_view()` with error/empty/happy-path for both
- [ ] Data endpoint branches in `generic_view_data()` for both
- [ ] OKR progress: `(currentValue / targetValue) * 100` clamped 0–100, div-by-zero → 0
- [ ] Decision Matrix: `Σ(weight × value)` per alternative, ranked descending
- [ ] Templates use `/css/` and `/js/` paths, bracket notation for dict access
- [ ] Templates include type_filter_pills.html and view_toolbar.html
- [ ] Logger.info calls in router (renderer=okr/decision-matrix) and service (execute_* with counts)

## Verification

- `rg '"okr"' backend/app/views/registry.py` — present
- `rg '"decision-matrix"' backend/app/views/registry.py` — present
- `rg '_VALID_RENDERERS' backend/app/views/router.py` — both okr and decision-matrix in the set
- `rg 'elif renderer == "okr"' backend/app/views/router.py` — present
- `rg 'elif renderer == "decision-matrix"' backend/app/views/router.py` — present
- `rg 'execute_okr_query\|execute_decision_matrix_query' backend/app/views/service.py` — both present
- `test -f backend/app/templates/browser/okr_view.html && test -f backend/app/templates/browser/decision_matrix_view.html` — exist
- `rg '/css/okr.css' backend/app/templates/browser/okr_view.html` — uses /css/ not /static/
- `rg "\\['key" backend/app/templates/browser/okr_view.html backend/app/templates/browser/decision_matrix_view.html` — bracket notation used

## Inputs

- `backend/app/views/registry.py` — existing registry with quadrant + bmc entries
- `backend/app/views/router.py` — existing router with quadrant + bmc elif branches (quadrant at line ~751, bmc at line ~850, generic_view_data at line ~1037)
- `backend/app/views/service.py` — existing service with `_detect_quadrant_axes`, `_detect_bmc_sections` patterns to follow (3085 lines)
- `backend/app/templates/browser/quadrant_view.html` — reference template pattern (102 lines)
- `backend/app/templates/browser/bmc_view.html` — reference template pattern (71 lines)
- `models/business-planning/ontology/business-planning.jsonld` — T01 output with OKR + DM types and property IRIs

## Expected Output

- `backend/app/views/registry.py` — two new RENDERER_REGISTRY entries
- `backend/app/views/router.py` — two new elif branches in generic_view() + two in generic_view_data()
- `backend/app/views/service.py` — 6 new methods (3 OKR + 3 Decision Matrix)
- `backend/app/templates/browser/okr_view.html` — OKR renderer template
- `backend/app/templates/browser/decision_matrix_view.html` — Decision Matrix renderer template
