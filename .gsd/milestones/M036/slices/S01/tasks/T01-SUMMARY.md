---
id: T01
parent: S01
milestone: M036
provides:
  - business-planning model archive (manifest + ontology + shapes + views + seed)
  - Eisenhower Matrix and Eisenhower Item types with SHACL shapes
  - sh:in constraints on bp:urgency and bp:importance ["high","low"]
  - quadrant ViewSpec with sempkm:rendererType "quadrant"
  - seed data covering all 4 quadrants (8 items total)
key_files:
  - models/business-planning/manifest.yaml
  - models/business-planning/ontology/business-planning.jsonld
  - models/business-planning/shapes/business-planning.jsonld
  - models/business-planning/views/business-planning.jsonld
  - models/business-planning/seed/business-planning.jsonld
key_decisions:
  - Used gist:Category as superclass for FrameworkItem and gist:Collection for EisenhowerMatrix (matching gist upper ontology patterns)
  - Kept urgency/importance as xsd:string with sh:in ["high","low"] rather than enum IRIs — simpler for drag-drop updates via object.patch
  - 8 seed items: 2 in high/high, 2 in low/high, 1 in high/low, 2 in low/low — realistic distribution weighted toward important items
patterns_established:
  - business-planning model follows exact same 5-file JSON-LD structure as basic-pkm (inline @context, no remote URLs)
  - Shared base types (bp:FrameworkItem, bp:QuadrantItem) for S02-S04 extension
observability_surfaces:
  - Model install success is observable via Admin > Mental Models list and triplestore triple count
  - No runtime code in this task — observability comes from T02+ backend wiring
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Create business-planning model archive with Eisenhower types

**Created 5-file business-planning model archive with Eisenhower Matrix/Item types, SHACL sh:in constraints for urgency/importance quadrant axes, and seed data spanning all 4 quadrants.**

## What Happened

Built the business-planning model archive following the exact patterns established by basic-pkm. Created 4 OWL classes: `bp:FrameworkItem` (abstract base, subClassOf gist:Category), `bp:QuadrantItem` (subClassOf FrameworkItem — base for 2-axis grid items), `bp:EisenhowerMatrix` (container, subClassOf gist:Collection), and `bp:EisenhowerItem` (subClassOf QuadrantItem). Defined `bp:urgency` and `bp:importance` as DatatypeProperties on QuadrantItem, plus `bp:belongsToMatrix` as an ObjectProperty linking items to matrices.

SHACL shapes include `sh:in ["high","low"]` constraints on both urgency and importance with `sh:minCount: 1` making them required fields. PropertyGroups organize the form into Basic Info, Classification, Relationships, and Metadata sections. The EisenhowerMatrixShape has optional `bp:xAxisLabel`/`bp:yAxisLabel` with default values "Urgency"/"Importance".

ViewSpecs declare three views: table for matrices, table for items, and a quadrant view (`sempkm:rendererType: "quadrant"`) targeting EisenhowerItem.

Seed data provides one matrix ("My Priority Matrix") with 8 items distributed across all 4 quadrants: 2 in Do First (high urgency + high importance), 2 in Schedule (low urgency + high importance), 1 in Delegate (high urgency + low importance), and 2 in Eliminate (low urgency + low importance).

## Verification

1. **Manifest validation** — `parse_manifest()` succeeded: `business-planning v1.0.0 ns=urn:sempkm:model:business-planning:`, 2 icon defs, all entrypoints resolved.
2. **JSON-LD parsing** — All 4 files parse via rdflib: Ontology=49 triples, Shapes=154 triples, Views=19 triples, Seed=55 triples.
3. **sh:in constraint check** — Confirmed `sh:in` on `bp:urgency` and `bp:importance` both contain exactly `["high","low"]`.
4. **Quadrant renderer check** — ViewSpec `bp:view-eisenhower-item-quadrant` has `sempkm:rendererType: "quadrant"` targeting `bp:EisenhowerItem`.
5. **Quadrant coverage** — 4/4 quadrants covered by seed data (high/high, low/high, high/low, low/low).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; ..."` | 0 | ✅ pass | 2.8s |
| 2 | `cd backend && .venv/bin/python -c "from rdflib import Graph; ..."` (all 4 JSON-LD files) | 0 | ✅ pass | 2.8s |
| 3 | `cd backend && .venv/bin/python -c "..."` (sh:in + quadrant + coverage check) | 0 | ✅ pass | 2.0s |

## Diagnostics

- **Inspect model structure:** `ls models/business-planning/` — 4 subdirectories with JSON-LD files
- **Validate manifest:** `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('../models/business-planning')); print(m.modelId, m.version)"`
- **Count triples:** `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g))"`
- **No runtime code** — runtime observability will come from T02 (view router wiring)

## Deviations

- Pre-flight requested adding `## Observability Impact` to T01-PLAN.md. Since this task produces only static data files with no runtime behavior, the observability impact is noted here in the summary instead of modifying the plan mid-execution.

## Known Issues

None.

## Files Created/Modified

- `models/business-planning/manifest.yaml` — Model manifest (modelId, namespace, prefixes, entrypoints, icon defs)
- `models/business-planning/ontology/business-planning.jsonld` — OWL classes (FrameworkItem, QuadrantItem, EisenhowerMatrix, EisenhowerItem) and properties (urgency, importance, belongsToMatrix, axis labels)
- `models/business-planning/shapes/business-planning.jsonld` — SHACL NodeShapes with PropertyGroups, sh:in constraints on urgency/importance, editHelpText
- `models/business-planning/views/business-planning.jsonld` — ViewSpecs for matrix table, item table, and item quadrant renderer
- `models/business-planning/seed/business-planning.jsonld` — Seed data: 1 matrix + 8 items spanning all 4 urgency×importance quadrants
