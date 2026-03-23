# S03 Research: OKR Progress + Decision Matrix Weighted Scoring

**Researched:** 2026-03-23
**Status:** Complete
**Depth:** Targeted — repeats proven S01/S02 pattern with new computed-field concern

## Summary

S03 ships two new renderers (OKR progress bars, Decision Matrix weighted table) following the exact 4-layer vertical pattern proven by S01 (quadrant) and S02 (BMC): model types → SHACL shapes → service methods → renderer wiring → template + CSS + JS → unit tests. The novel concern is server-side computation of OKR progress percentages and Decision Matrix weighted scores — the first computed values in the view pipeline. Both computations are arithmetic over SPARQL-bound values, not new infrastructure.

## Recommendation

Follow the S01/S02 pattern exactly. Four tasks:

1. **T01 — Model Archive Extension** (~20 min): Add 5 OWL classes + SHACL shapes + ViewSpecs + seed data to the existing business-planning model. OKR: `bp:Objective`, `bp:KeyResult`. Decision Matrix: `bp:DecisionMatrix`, `bp:Criterion`, `bp:Alternative`, `bp:Score`.
2. **T02 — Backend Wiring** (~30 min): Add `okr` and `decision-matrix` renderers. Service methods with server-side computation: OKR progress = `currentValue / targetValue * 100`, Decision Matrix score = `Σ(weight × value)` per alternative.
3. **T03 — Frontend** (~25 min): Two templates + CSS + JS files. OKR: progress bars with % labels. Decision Matrix: sortable table with score column and rank badges.
4. **T04 — Unit Tests** (~15 min): ~30 tests covering detection, query building, computation, and grouping for both renderers.

## Implementation Landscape

### Files to Create (new)

| File | Purpose |
|------|---------|
| `backend/app/templates/browser/okr_view.html` | OKR progress renderer template |
| `frontend/static/js/okr.js` | OKR interactivity (inline progress edit, scope-changed listener) |
| `frontend/static/css/okr.css` | OKR progress bar styling, dark mode |
| `backend/app/templates/browser/decision_matrix_view.html` | Weighted scoring table template |
| `frontend/static/js/decision-matrix.js` | Decision Matrix sorting, inline weight editing |
| `frontend/static/css/decision-matrix.css` | Weighted table styling, rank badges, dark mode |
| `backend/tests/test_okr.py` | OKR detection + computation + grouping tests |
| `backend/tests/test_decision_matrix.py` | Decision Matrix detection + computation tests |

### Files to Modify (existing)

| File | Change |
|------|--------|
| `models/business-planning/ontology/business-planning.jsonld` | Add 6 OWL classes (Objective, KeyResult, DecisionMatrix, Criterion, Alternative, Score) and ~10 new properties |
| `models/business-planning/shapes/business-planning.jsonld` | Add 6 NodeShapes with PropertyGroups |
| `models/business-planning/views/business-planning.jsonld` | Add ViewSpecs (2 table + 1 okr + 2 table + 1 decision-matrix) |
| `models/business-planning/seed/business-planning.jsonld` | Add seed data (1 objective + 3 key results + 1 matrix + 3 criteria + 3 alternatives + 9 scores) |
| `models/business-planning/manifest.yaml` | Add icon definitions for new types |
| `backend/app/views/router.py` | Add `okr` and `decision-matrix` to `_VALID_RENDERERS`; add elif branches in `generic_view()` and `generic_view_data()` |
| `backend/app/views/service.py` | Add 6+ methods: `_detect_okr_structure()`, `_build_okr_select()`, `execute_okr_query()`, `_detect_decision_matrix_structure()`, `_build_decision_matrix_select()`, `execute_decision_matrix_query()` |
| `backend/app/views/registry.py` | Add `okr` and `decision-matrix` entries to `RENDERER_REGISTRY` |

### Established Patterns to Follow

**4-layer renderer wiring** (proven S01, confirmed S02):
1. `RENDERER_REGISTRY` entry in `registry.py`
2. Renderer string in `_VALID_RENDERERS` set in `router.py`
3. `elif renderer == "xxx":` branch in `generic_view()` and `generic_view_data()`
4. `_detect_*()`, `_build_*_select()`, `execute_*_query()` methods on `ViewSpecService`

**Template structure**: `view-flex-column` wrapper → `type_filter_pills.html` → `view_toolbar.html` → renderer content → lazy-load JS boot

**JS structure**: IIFE → `initXxx(boardEl)` → event listeners → `sempkm:scope-changed` listener for refresh

**CSS structure**: Renderer-specific layout → dark mode via `html[data-theme="dark"]` → rgba() tints with 0.07/0.12 alpha

**Test structure**: `_make_property()`, `_make_form()`, `_build_service()` helpers → detection tests → query building tests → computation tests → grouping tests

**JSON-LD conventions**: Inline `@context` with `bp:`, `sempkm:`, `dcterms:`, etc. No remote URLs. All types use `bp:` namespace (`urn:sempkm:model:business-planning:`).

**Jinja2 dict access**: Use `item['key']` not `item.key` for dict values (Jinja2 attribute resolution collides with dict methods — see KNOWLEDGE entry re: Kanban, confirmed in S01/S02).

## OKR Data Model Design

### OWL Classes

- `bp:Objective` — subClassOf `bp:FrameworkItem`. Container for key results. Properties: `dcterms:title`, `dcterms:description`, `bp:timeframe` (optional string).
- `bp:KeyResult` — subClassOf `bp:FrameworkItem`. Measurable metric. Properties: `dcterms:title`, `bp:currentValue` (xsd:decimal), `bp:targetValue` (xsd:decimal), `bp:unit` (xsd:string, e.g. "%", "$", "count"), `bp:belongsToObjective` (ObjectProperty → bp:Objective).

### Computation

Server-side in `execute_okr_query()`:
- Progress % per KeyResult = `(currentValue / targetValue) * 100`, clamped to 0–100
- Objective-level progress = average of all child KeyResult progress percentages
- Division by zero guard: if `targetValue == 0`, progress = 0

### Detection Heuristic

`_detect_okr_structure()`: Find SHACL properties with `xsd:decimal` datatype whose paths contain "currentvalue" or "targetvalue" (case-insensitive). Also detect the `belongsToObjective` ObjectProperty for parent grouping.

### SPARQL Shape

```sparql
SELECT ?s ?title ?currentValue ?targetValue ?unit ?objective ?objTitle WHERE {
  ?s a <bp:KeyResult> ; dcterms:title ?title .
  OPTIONAL { ?s bp:currentValue ?currentValue }
  OPTIONAL { ?s bp:targetValue ?targetValue }
  OPTIONAL { ?s bp:unit ?unit }
  OPTIONAL { ?s bp:belongsToObjective ?objective .
             ?objective dcterms:title ?objTitle }
}
```

Results grouped by objective, then compute progress server-side before passing to template.

### Frontend

- Each objective renders as a card with title + description + aggregate progress bar
- Each key result renders as a row: title | current/target | unit | progress bar with % label
- Progress bar color: green (≥70%), amber (30–69%), red (<30%)
- Inline click-to-edit on currentValue for quick updates via `object.patch`

## Decision Matrix Data Model Design

### OWL Classes

- `bp:DecisionMatrix` — subClassOf `gist:Collection`. Container. Properties: `dcterms:title`, `dcterms:description`.
- `bp:Criterion` — subClassOf `bp:FrameworkItem`. Evaluation dimension. Properties: `dcterms:title`, `bp:weight` (xsd:decimal, 1–10), `bp:belongsToMatrix` (→ bp:DecisionMatrix).
- `bp:Alternative` — subClassOf `bp:FrameworkItem`. Option being evaluated. Properties: `dcterms:title`, `dcterms:description`, `bp:belongsToMatrix` (→ bp:DecisionMatrix).
- `bp:Score` — scoring junction. Properties: `bp:scoreAlternative` (→ bp:Alternative), `bp:scoreCriterion` (→ bp:Criterion), `bp:value` (xsd:decimal, 1–10), `bp:belongsToMatrix` (→ bp:DecisionMatrix).

### Computation

Server-side in `execute_decision_matrix_query()`:
- Weighted score per alternative = `Σ(criterion.weight × score.value)` for all criteria
- Alternatives ranked by descending weighted score
- Normalized score = weighted_score / max_possible_score * 100 (optional, for display)

### Detection Heuristic

`_detect_decision_matrix_structure()`: Find SHACL property with path containing "weight" (xsd:decimal) on the Criterion shape. Find ObjectProperty pointing to "Alternative" and "Criterion" on the Score shape. This is more structural than the quadrant/BMC detectors — it needs to recognise the junction pattern.

Alternative approach (simpler): detect based on the DecisionMatrix type having a specific ViewSpec renderer declaration, without SHACL-based auto-detection. The Score type always exists alongside DecisionMatrix in the same model, so the relationship is guaranteed.

**Recommended**: Use ViewSpec renderer declaration as the entry point (like all existing renderers), and hardcode the SPARQL query structure for decision-matrix scoring. The detection method just validates the presence of required properties on the Score shape (weight, value, alternative, criterion paths). This is consistent — quadrant and BMC also have model-specific knowledge in their SPARQL builders.

### SPARQL Shape

Two queries for the decision matrix data endpoint:

**Query 1 — Criteria:**
```sparql
SELECT ?s ?title ?weight WHERE {
  ?s a bp:Criterion ; dcterms:title ?title .
  OPTIONAL { ?s bp:weight ?weight }
}
```

**Query 2 — Scores with joins:**
```sparql
SELECT ?alt ?altTitle ?crit ?critWeight ?scoreValue WHERE {
  ?score a bp:Score ;
         bp:scoreAlternative ?alt ;
         bp:scoreCriterion ?crit ;
         bp:value ?scoreValue .
  ?alt dcterms:title ?altTitle .
  ?crit bp:weight ?critWeight .
}
```

Server-side: group by alternative, compute Σ(critWeight × scoreValue), rank descending.

### Frontend

- Table layout: rows = alternatives, columns = criteria + total score + rank
- Cell values: individual scores (1–10)
- Total column: bold weighted sum
- Rank column: 🥇🥈🥉 badges or #1/#2/#3
- Header row: criterion name + weight in parentheses
- Color gradient on total column (green = highest, red = lowest)
- Inline editing on score cells via `object.patch` on the Score instance

## Constraints and Risks

1. **Service file size**: `service.py` is 3085 lines. Adding ~200 lines for OKR + ~250 for Decision Matrix brings it to ~3500. Not ideal but consistent with the established pattern — each renderer adds ~100-150 lines of service methods.

2. **Router file size**: `router.py` is 1708 lines. Two more elif branches add ~200 lines. Same growth pattern as S01/S02.

3. **Decision Matrix SPARQL complexity**: The Score junction pattern requires joining 3 types (Score → Alternative + Criterion). This is more complex than the single-type queries used by quadrant and BMC. The SPARQL must be a single query with JOINs, not multiple queries, for performance.

4. **Decimal handling**: SPARQL returns decimal values as strings. Python must parse to `float`/`Decimal` for arithmetic. Guard against non-numeric values and division by zero.

5. **Seed data volume**: Decision Matrix seed needs 3 alternatives × 3 criteria × 9 scores = 15+ seed entities. More verbose than Eisenhower (8 items) or BMC (9 sections) but structurally necessary.

6. **No external dependencies**: Both renderers use pure HTML/CSS/JS. OKR progress bars are CSS `width: N%` on colored divs. Decision Matrix is a standard HTML table with computed cells. No third-party libraries needed.

## Verification Plan

- `cd backend && .venv/bin/python -m pytest tests/test_okr.py tests/test_decision_matrix.py -v` — all tests pass
- All 5 JSON-LD model files parse via rdflib with no errors
- `parse_manifest()` validates business-planning model
- `okr` and `decision-matrix` in `_VALID_RENDERERS` and `RENDERER_REGISTRY`
- OKR progress computation: 50/100 = 50%, 0/0 = 0%, 120/100 = 100% (clamped)
- Decision Matrix scoring: Σ(weight × value) matches expected totals for seed data
- Dark mode coverage in both CSS files via `html[data-theme="dark"]`
- Template files use `/css/` and `/js/` paths (not `/static/` — see KNOWLEDGE entry)
- Templates use bracket notation for dict access (not dot notation)
