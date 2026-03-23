---
id: T01
parent: S04
milestone: M036
provides:
  - 5 quadrant framework types (SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix) with ontology, shapes, views, seed, icons
  - Multi-framework quadrant label dispatch in _quadrant_label()
  - Extended axis detection keywords in _detect_quadrant_axes()
  - 14 new unit tests covering label mappings and axis detection
key_files:
  - models/business-planning/ontology/business-planning.jsonld
  - models/business-planning/shapes/business-planning.jsonld
  - models/business-planning/views/business-planning.jsonld
  - models/business-planning/seed/business-planning.jsonld
  - models/business-planning/manifest.yaml
  - backend/app/views/service.py
  - backend/tests/test_quadrant.py
key_decisions:
  - Restructured _EISENHOWER_QUADRANT_LABELS from flat dict to _QUADRANT_LABELS nested dict keyed by framework id, with _AXIS_KEYWORD_PAIRS list for axis assignment
patterns_established:
  - Adding a new quadrant framework requires entries in _QUADRANT_LABELS, _AXIS_KEYWORD_PAIRS, plus ontology/shapes/views/seed/manifest
observability_surfaces:
  - _detect_quadrant_axes debug log includes type IRI and x/y axis paths for all 6 frameworks
  - _quadrant_label generic fallback visible in UI when framework key not matched
duration: 35m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Quadrant framework types — SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix

**Add 5 quadrant-based framework types (SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix) with full model archive entries and multi-framework label dispatch in the quadrant renderer backend**

## What Happened

Added 10 new OWL classes (5 containers subclassing gist:Collection + 5 items subclassing bp:QuadrantItem) and 10 axis properties to the business-planning ontology. Each item type has exactly two 2-value sh:in axis properties that the existing _detect_quadrant_axes() auto-discovers.

Added 10 new SHACL NodeShapes — one for each container type (title, description, created) and one for each item type (title, description, two axis properties with sh:in constraints, belongsTo relation, created). Reused existing PropertyGroups (BasicInfo, Classification, Relationships, Metadata).

Added 15 new ViewSpecs: for each item type a quadrant view + table view, for each container type a table view.

Added ~20 seed entities: 5 containers + 15 items spanning different quadrants with realistic labels.

Added 10 icon entries to the manifest using distinct Lucide icons per type.

Restructured backend from single-framework `_EISENHOWER_QUADRANT_LABELS` to multi-framework `_QUADRANT_LABELS` nested dict with `_AXIS_KEYWORD_PAIRS` for axis assignment. The `_quadrant_label()` method now derives framework key from axis names via keyword matching, then looks up the framework-specific label dict. The `_detect_quadrant_axes()` method now iterates all keyword pairs instead of just urgency/importance.

## Verification

- All 42 tests pass (28 existing + 14 new): `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v`
- All 4 JSON-LD files parse cleanly: ontology (260 triples), shapes (1094 triples), views (171 triples), seed (344 triples)
- 13 sh:in constraints in shapes file (2 Eisenhower + 1 BMC + 10 new quadrant axes)
- 20 icon entries in manifest (10 original + 10 new)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` | 0 | ✅ pass | 0.52s |
| 2 | `rdflib parse ontology/business-planning.jsonld` | 0 | ✅ pass (260 triples) | ~5s |
| 3 | `rdflib parse shapes/business-planning.jsonld` | 0 | ✅ pass (1094 triples) | ~5s |
| 4 | `rdflib parse views/business-planning.jsonld` | 0 | ✅ pass (171 triples) | ~5s |
| 5 | `rdflib parse seed/business-planning.jsonld` | 0 | ✅ pass (344 triples) | ~5s |
| 6 | `rg 'sh:in' shapes/business-planning.jsonld \| wc -l` | 0 | ✅ pass (13 lines) | <1s |

## Diagnostics

- Inspect axis detection for any type: check debug logs from `_detect_quadrant_axes` (logger at WARNING+ in prod, DEBUG in dev)
- Test label output: `/browser/views/generic/quadrant/data?type=urn:sempkm:model:business-planning:SWOTItem` should return JSON with labels like "Strengths", "Weaknesses", etc.
- Generic fallback label ("AxisName: val / AxisName: val") indicates framework key wasn't matched — check _AXIS_KEYWORD_PAIRS

## Deviations

- Added 14 new tests instead of the planned ~10 — covered all 4 SWOT quadrants and all 4 BCG quadrants individually for completeness
- Used "Market Growth" / "Market Share" as BCG axis names (matching SHACL sh:name), which contain the keywords "growth" and "share" — the keyword matching picks these up correctly

## Known Issues

None.

## Files Created/Modified

- `models/business-planning/ontology/business-planning.jsonld` — added 10 OWL classes (5 containers + 5 items), 10 axis properties, 5 belongsTo properties; updated description
- `models/business-planning/shapes/business-planning.jsonld` — added 10 NodeShapes with sh:in axis constraints
- `models/business-planning/views/business-planning.jsonld` — added 15 ViewSpecs (quadrant + table for items, table for containers)
- `models/business-planning/seed/business-planning.jsonld` — added ~20 seed entities (5 containers + 15 items)
- `models/business-planning/manifest.yaml` — added 10 icon entries; updated description
- `backend/app/views/service.py` — restructured _EISENHOWER_QUADRANT_LABELS → _QUADRANT_LABELS + _AXIS_KEYWORD_PAIRS; updated _quadrant_label() and _detect_quadrant_axes()
- `backend/tests/test_quadrant.py` — added 14 new tests for SWOT/BCG/Ansoff/Stakeholder/Risk label mappings and axis detection
