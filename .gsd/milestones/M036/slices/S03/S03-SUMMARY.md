---
slice: S03
milestone: M036
title: "OKR Progress + Decision Matrix Weighted Scoring"
status: done
started: 2026-03-22
completed: 2026-03-22
tasks_completed: 4/4
verification: passed
---

# S03 Summary: OKR Progress + Decision Matrix Weighted Scoring

## What This Slice Delivered

Two computed-value custom renderers — OKR progress tracking and Decision Matrix weighted scoring — fully wired through the 4-layer backend pipeline (registry → `_VALID_RENDERERS` → elif → service) with server-side arithmetic, Jinja2 templates, interactive frontend JS/CSS, and 51 unit tests.

**OKR renderer (`okr`):** Displays Key Results grouped by their parent Objective, each with a progress bar computed server-side as `(currentValue / targetValue) × 100`, clamped 0–100. Progress bars color-coded green (≥70%), amber (30–69%), red (<30%). Click-to-edit on currentValue updates the value via `object.patch` and recomputes the bar client-side. Aggregate objective progress shown as average of child KR percentages.

**Decision Matrix renderer (`decision-matrix`):** Displays alternatives in a table with criteria columns, computing `Σ(weight × value)` per alternative for a weighted total. Alternatives auto-ranked descending by score with tie-aware ranking. Rank badges (🥇🥈🥉) highlight top positions. Client-side column sorting on any criterion or total column re-sorts and re-ranks.

## Key Artifacts

### Model Archive (T01)
- 6 new OWL classes: `bp:Objective`, `bp:KeyResult`, `bp:DecisionMatrix`, `bp:Criterion`, `bp:Alternative`, `bp:Score`
- 10 new properties including `bp:currentValue`, `bp:targetValue`, `bp:weight`, `bp:value`, `bp:belongsToObjective`, `bp:belongsToDecisionMatrix`
- SHACL NodeShapes with PropertyGroups for all 6 types
- ViewSpecs declaring `okr` and `decision-matrix` renderer types
- Seed data: 1 Objective + 3 Key Results (80%/45%/10% progress) + 1 Matrix + 3 Criteria + 3 Alternatives + 9 Scores
- 6 manifest icon entries (target, trending-up, scale, ruler, layers, hash)
- Ontology now has 32 graph entries (12 OWL classes total across S01–S03)

### Backend Wiring (T02)
- `backend/app/views/registry.py` — `okr` and `decision-matrix` in RENDERER_REGISTRY
- `backend/app/views/router.py` — both in `_VALID_RENDERERS`, elif branches in `generic_view()` and `generic_view_data()`
- `backend/app/views/service.py` — 6 new methods per renderer:
  - OKR: `_detect_okr_structure()`, `_build_okr_select()`, `execute_okr_query()` (groups by objective, computes progress %, clamps 0–100)
  - Decision Matrix: `_detect_decision_matrix_structure()`, `_build_decision_matrix_select()`, `execute_decision_matrix_query()` (computes Σ(weight×value), ranks descending, tie-aware)
- `backend/app/templates/browser/okr_view.html` — progress bars grouped by objective, lazy-load JS boot
- `backend/app/templates/browser/decision_matrix_view.html` — weighted table with rank badges, lazy-load JS boot

### Frontend (T03)
- `frontend/static/css/okr.css` (210 lines) — progress bar colors, objective cards, dark mode (12 rules), responsive
- `frontend/static/js/okr.js` (175 lines) — click-to-edit currentValue, scope-changed sync, dockview isolation
- `frontend/static/css/decision-matrix.css` (226 lines) — sortable table, rank badges, score tinting, dark mode (14 rules)
- `frontend/static/js/decision-matrix.js` (155 lines) — column sorting with re-ranking, scope-changed sync, dockview isolation

### Tests (T04)
- `backend/tests/test_okr.py` — 25 tests covering detection, query building, progress computation edge cases (0/0, over-target, negative, grouping, dedup)
- `backend/tests/test_decision_matrix.py` — 26 tests covering detection, query building, weighted scoring, tie-aware ranking, missing/invalid values

## Patterns Established

1. **Server-side computed fields pattern:** Service methods fetch raw SPARQL results, compute derived values (progress %, weighted scores) in Python, return structured dicts to templates. Per D320 — pragmatic middle ground between SHACL-AF inference and client-side JS.

2. **Score junction node pattern:** `bp:Score` links `bp:Alternative` × `bp:Criterion` with a `bp:value`, enabling N×M scoring grids. The 3-type SPARQL join (Score→Alternative + Score→Criterion with weight) is the query pattern for any weighted matrix.

3. **Weight property derivation:** Decision Matrix weight IRI derived dynamically from the value property's namespace (replace local name with "weight") rather than hardcoded. Works for any model following the convention of co-locating value and weight in the same namespace.

4. **Click-to-edit with client-side recompute:** OKR currentValue edits via `object.patch`, then progress bar fill/color updated client-side from the new values without full re-render. Saves a round-trip.

## What the Next Slice Should Know

- The model archive now has **12 OWL classes** across 3 slices (Eisenhower 2 + BMC 2 + SWOT 2 + OKR 2 + DecisionMatrix 4). S04 adds extended framework types to the same archive.
- `_VALID_RENDERERS` now contains 11 entries: table, card, graph, kanban, calendar, map, timeline, quadrant, bmc, okr, decision-matrix.
- The elif chain in `generic_view()` is growing. D317 says don't refactor yet — extend the pattern until renderer count exceeds 15.
- All S03 renderers follow the same `view-flex-column` + `type_filter_pills` + `view_toolbar` + lazy-load JS boot template pattern established in S01/S02.
- Seed data demonstrates all three progress zones (green 80%, amber 45%, red 10%) and a complete 3×3 scoring grid for visual verification.

## Verification Summary

| Check | Result |
|-------|--------|
| `python3 -c "import json; ..."` — ontology graph entries | ✅ 32 entries |
| `rg '"okr"' registry.py router.py` | ✅ present in both |
| `rg '"decision-matrix"' registry.py router.py` | ✅ present in both |
| `rg 'data-theme="dark"' okr.css decision-matrix.css` | ✅ 12 + 14 rules |
| All 6 files exist (JS, CSS, templates) | ✅ all present |
| `pytest tests/test_okr.py tests/test_decision_matrix.py -v` | ✅ 51/51 passed |

## Deviations from Plan

- Used `bp:belongsToDecisionMatrix` instead of reusing `bp:belongsToMatrix` — the latter already targets EisenhowerMatrix from S01.
- Weight property IRI derived dynamically from namespace rather than hardcoded — more general for minimal extra complexity.
- T03 patched T02 templates to add `data-rank` attribute and `.okr-current-value` span wrappers needed by the interactive frontend.
