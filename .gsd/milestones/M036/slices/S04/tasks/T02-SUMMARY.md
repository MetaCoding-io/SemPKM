---
id: T02
parent: S04
milestone: M036
provides:
  - 6 non-quadrant framework types (Porter, PESTLE, BSC, RACI, Value Chain, Lean Canvas) with ontology, shapes, views, seed, icons
  - 12 OWL classes (6 containers + 6 items) with correct subclass hierarchy
  - 12 SHACL NodeShapes with sh:in enum constraints
  - 12 table ViewSpecs for browsing all new types
  - ~20 seed entities with realistic business content
  - 12 icon entries in manifest
key_files:
  - models/business-planning/ontology/business-planning.jsonld
  - models/business-planning/shapes/business-planning.jsonld
  - models/business-planning/views/business-planning.jsonld
  - models/business-planning/seed/business-planning.jsonld
  - models/business-planning/manifest.yaml
key_decisions:
  - Used capitalized enum values ("High"/"Medium"/"Low") for Porter intensity and PESTLE impact to match UI readability, while RACI uses full words ("Responsible"/"Accountable"/"Consulted"/"Informed")
  - Reused existing PropertyGroups (MatrixBasicInfoGroup, ItemBasicInfoGroup, ItemClassificationGroup, ItemRelationshipsGroup, ItemMetadataGroup, MatrixMetadataGroup) rather than creating framework-specific groups
patterns_established:
  - Non-quadrant frameworks follow container+item pattern with sh:in enums, table ViewSpecs, and belongsTo linking properties — same structure as quadrant types minus axis properties
observability_surfaces:
  - All new types are browsable via table views — no special renderer needed
  - sh:in constraints produce dropdown select fields in SHACL forms for all enum properties
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Non-quadrant framework types — Porter, PESTLE, BSC, RACI, Value Chain, Lean Canvas

**Add 6 non-quadrant framework types (Porter, PESTLE, BSC, RACI, Value Chain, Lean Canvas) with 12 OWL classes, 12 SHACL shapes, 12 table ViewSpecs, ~20 seed entities, and 12 manifest icon entries**

## What Happened

Added 12 OWL classes to the ontology: 6 container types (PorterAnalysis, PESTLEAnalysis, BalancedScorecard, RACIMatrix, ValueChain, LeanCanvas — all subclassing gist:Collection) and 6 item types (PorterForce, PESTLEFactor, BSCItem, RACIEntry, VCActivity, LeanCanvasSection — all subclassing bp:FrameworkItem). Added ~22 datatype and object properties covering force type/intensity, PESTLE category/impact, BSC perspective/measure/target, RACI role/person/activity, activity type/category, lean section type/content, and 6 belongsTo linking properties.

Added 12 SHACL NodeShapes with sh:in enum constraints for the framework-specific classification fields: 5 Porter forces, 6 PESTLE categories, 4 BSC perspectives, 4 RACI roles, 2 Value Chain activity types, and 9 Lean Canvas sections. Container shapes follow the standard title+description+created pattern. Item shapes include the enum field(s) plus a belongsTo relation.

Added 12 table ViewSpecs (one per container type, one per item type) with SPARQL queries that SELECT the framework-specific fields. Sort defaults are set to the primary classification field (forceType, pestleCategory, etc.).

Added ~20 seed entities: 6 containers and ~14 items with realistic business content (SaaS market Porter analysis, European market PESTLE, strategy scorecard, platform rewrite RACI, SaaS value chain, knowledge graph Lean Canvas).

Added 12 icon entries to manifest using distinct Lucide icons per type. Updated ontology and manifest descriptions to list all 15 framework types.

## Verification

- All 4 JSON-LD files parse cleanly via rdflib with significant triple count increases from T01
- All 42 existing quadrant tests still pass
- 21 sh:in constraints in shapes file (13 from T01 + 8 new enum fields)
- 32 icon entries in manifest (20 from T01 + 12 new)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `backend/.venv/bin/python3 -c "rdflib parse ontology"` | 0 | ✅ pass (408 triples, up from 260) | 4.1s |
| 2 | `backend/.venv/bin/python3 -c "rdflib parse shapes"` | 0 | ✅ pass (1632 triples, up from 1094) | 4.1s |
| 3 | `backend/.venv/bin/python3 -c "rdflib parse views"` | 0 | ✅ pass (255 triples, up from 171) | 4.1s |
| 4 | `backend/.venv/bin/python3 -c "rdflib parse seed"` | 0 | ✅ pass (479 triples, up from 344) | 4.1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` | 0 | ✅ pass (42/42) | 0.48s |
| 6 | `rg 'sh:in' shapes \| wc -l` | 0 | ✅ pass (21 lines) | <1s |
| 7 | `grep -c 'type: "bp:' manifest.yaml` | 0 | ✅ pass (32 entries) | <1s |

## Diagnostics

- All new types are table-rendered — no custom backend code, so diagnostic surface is the standard table view pipeline
- sh:in constraints generate dropdown selects in the SHACL form editor — visible when creating/editing any item of these types
- Seed data provides immediate browsable content after model installation

## Deviations

- Added ~22 properties instead of ~12 — the plan underestimated because each framework needed 2-4 properties plus a belongsTo relation
- Added 12 ViewSpecs instead of 14 — exactly one container table + one item table per framework (6×2=12), which is correct; the plan's "~14" was an overcount
- Added 8 new sh:in constraints instead of 6 — Porter intensity and PESTLE impact also use sh:in (High/Medium/Low) for consistent dropdown behavior

## Known Issues

None.

## Files Created/Modified

- `models/business-planning/ontology/business-planning.jsonld` — added 12 OWL classes, ~22 properties; updated ontology description
- `models/business-planning/shapes/business-planning.jsonld` — added 12 NodeShapes with sh:in enum constraints
- `models/business-planning/views/business-planning.jsonld` — added 12 table ViewSpecs
- `models/business-planning/seed/business-planning.jsonld` — added ~20 seed entities (6 containers + 14 items)
- `models/business-planning/manifest.yaml` — added 12 icon entries; updated description
