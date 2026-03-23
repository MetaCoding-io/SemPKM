---
id: S04
milestone: M036
status: done
outcome: success
tasks_completed: [T01, T02, T03]
duration_total: ~63m
completed_at: 2026-03-23
requirement_ids: [BIZ-06]
---

# S04 Summary: Extended Framework Library

## What This Slice Delivered

11 new business planning framework types added to the `business-planning` model archive, bringing the total from 7 types (Eisenhower, BMC, OKR, Decision Matrix from S01-S03) to 32 types across 16 frameworks. The model archive now covers the full spectrum of strategic analysis tools.

**5 quadrant-based frameworks** (SWOT, BCG Matrix, Ansoff Matrix, Stakeholder Map, Risk Matrix) reuse S01's quadrant renderer with framework-specific quadrant labels. Each has a container class (subclassing gist:Collection) and an item class (subclassing bp:QuadrantItem) with exactly two 2-value `sh:in` axis properties — the contract `_detect_quadrant_axes()` requires.

**6 non-quadrant frameworks** (Porter's Five Forces, PESTLE Analysis, Balanced Scorecard, RACI Matrix, Value Chain, Lean Canvas) use existing table renderers. Each follows the same container+item pattern with `sh:in` enum constraints for classification fields (5 Porter forces, 6 PESTLE categories, 4 BSC perspectives, 4 RACI roles, etc.).

No new renderer types, templates, JS, or CSS were needed. All 11 frameworks work through existing infrastructure.

## Key Changes

### Backend (service.py)
- `_EISENHOWER_QUADRANT_LABELS` restructured → `_QUADRANT_LABELS` nested dict keyed by framework id (eisenhower, swot, bcg, ansoff, stakeholder, risk)
- `_AXIS_KEYWORD_PAIRS` list added — each entry maps keyword substrings to x/y axis assignment, so `_detect_quadrant_axes()` works for all 6 quadrant frameworks without hardcoding
- `_quadrant_label()` derives framework key from axis names via keyword matching, then looks up the framework-specific label dict. Falls back to generic "AxisName: val / AxisName: val" if no framework matches.

### Model Archive
- **Ontology**: 408 triples (was ~130 after S01-S03). 22 new OWL classes, ~32 new properties.
- **Shapes**: 1632 triples. 22 new NodeShapes. 21 total `sh:in` constraints (12 quadrant axes + 9 non-quadrant enum fields).
- **Views**: 255 triples. 27 new ViewSpecs (15 quadrant + 12 table).
- **Seed**: 479 triples. ~35 new seed entities with realistic business content.
- **Manifest**: 32 icon entries (was 10 after S01-S03). Each type has a distinct Lucide icon.

### Tests
- 42 total tests in `test_quadrant.py` (28 original + 14 new). New tests cover SWOT/BCG/Ansoff/Stakeholder/Risk label mappings and SWOT/BCG axis detection keywords.

## What the Next Slice Should Know

- The model archive is complete — S05 should NOT add more types. It should focus on cross-model edges, E2E tests, and documentation.
- All quadrant-based types (Eisenhower, SWOT, BCG, Ansoff, Stakeholder, Risk) share the same renderer code path. The `/browser/views/generic/quadrant/data?type=<iri>` endpoint works for any of them.
- Non-quadrant types use standard table views — no custom renderer code needed for E2E testing.
- Adding a new quadrant framework in the future requires: (1) entries in `_QUADRANT_LABELS` and `_AXIS_KEYWORD_PAIRS` in `service.py`, (2) ontology classes/properties, (3) SHACL shapes with 2-value `sh:in` axes, (4) ViewSpecs, (5) seed data, (6) manifest icons.
- The manifest now has 32 type entries — S05's manifest validation should check this count.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_quadrant.py -v` | ✅ 42/42 passed (0.48s) |
| ontology JSON-LD parse | ✅ 408 triples |
| shapes JSON-LD parse | ✅ 1632 triples |
| views JSON-LD parse | ✅ 255 triples |
| seed JSON-LD parse | ✅ 479 triples |
| `sh:in` constraint count | ✅ 21 (exceeds 10+ threshold) |
