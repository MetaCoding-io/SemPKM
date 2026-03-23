---
id: T01
parent: S02
milestone: M036
provides:
  - bp:BusinessModelCanvas OWL class and SHACL shape
  - bp:BMCSection OWL class and SHACL shape with 9-value sh:in on sectionType
  - 3 BMC ViewSpecs (2 table + 1 bmc renderer)
  - Seed data with 1 canvas + 9 sections
  - Manifest icon definitions for both BMC types
key_files:
  - models/business-planning/ontology/business-planning.jsonld
  - models/business-planning/shapes/business-planning.jsonld
  - models/business-planning/views/business-planning.jsonld
  - models/business-planning/seed/business-planning.jsonld
  - models/business-planning/manifest.yaml
key_decisions:
  - BMCSection sectionType uses kebab-case string enum (key-partners, value-propositions, etc.) via sh:in — matches CSS data-attribute selectors in the frontend
  - Canvas is subClassOf gist:Collection (same pattern as EisenhowerMatrix); Section is subClassOf bp:FrameworkItem
  - BMC ViewSpec SPARQL includes belongsToCanvas for canvas-scoped filtering in the renderer
patterns_established:
  - PropertyGroup-based form organization for BMC shapes (SectionBasicInfoGroup, SectionClassificationGroup, SectionContentGroup, SectionRelationshipsGroup, SectionMetadataGroup)
  - ViewSpec with rendererType "bmc" targets BMCSection (sections are the items; the canvas is the container)
observability_surfaces:
  - rdflib parse validates all 5 JSON-LD files without error
  - parse_manifest() validates updated manifest with 4 icon definitions
duration: 12min
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Extend model archive with BMC ontology, shapes, views, and seed data

**Extended business-planning model with BusinessModelCanvas and BMCSection types — 2 OWL classes, 3 properties, 2 SHACL NodeShapes (9-value sh:in on sectionType), 3 ViewSpecs including bmc renderer, and seed data with 1 canvas + 9 realistic sections.**

## What Happened

Extended all 5 model files following the exact patterns established by the Eisenhower types in S01:

- **Ontology**: Added `bp:BusinessModelCanvas` (subClassOf `gist:Collection`) and `bp:BMCSection` (subClassOf `bp:FrameworkItem`), plus 3 properties: `bp:sectionType` (DatatypeProperty), `bp:sectionContent` (DatatypeProperty), `bp:belongsToCanvas` (ObjectProperty). Updated ontology description. Total: 72 triples (up from 49).

- **Shapes**: Added `bp:BMCCanvasShape` with Basic Info + Metadata groups, and `bp:BMCSectionShape` with 5 PropertyGroups (Basic Info, Classification, Content, Relationships, Metadata). The `sectionType` property has `sh:in` with exactly 9 kebab-case values. Total: 287 triples.

- **Views**: Added 3 ViewSpecs — `bp:view-bmc-canvas-table` (table for canvases), `bp:view-bmc-section-table` (table for sections), and `bp:view-bmc-section-bmc` (bmc renderer for sections, includes canvas reference in SPARQL). Total: 38 triples.

- **Seed**: Added 1 `bp:BusinessModelCanvas` instance ("SemPKM Business Model") and 9 `bp:BMCSection` instances, each with a unique `sectionType`, realistic 3-4 bullet-point content, and `belongsToCanvas` link. Total: 113 triples.

- **Manifest**: Added icon definitions for `bp:BusinessModelCanvas` (layout-grid, #2563eb) and `bp:BMCSection` (sticky-note, #f59e0b). Updated description to mention BMC. Total: 4 icon configs.

## Verification

All task-level verification checks pass:

1. Ontology parses: 72 triples (> 55 threshold) ✅
2. Shapes parse: 287 triples (> 180 threshold) ✅
3. Views parse: 38 triples (> 25 threshold) ✅
4. Seed parses: 113 triples (> 80 threshold) ✅
5. Manifest has BMC Canvas icon ✅
6. `sh:in` on sectionType has exactly 9 values ✅
7. `parse_manifest()` validates with 4 icon definitions ✅
8. `bmc` rendererType present in ViewSpec ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `backend/.venv/bin/python -c "...ontology parse + assert > 55"` | 0 | ✅ pass | 3.0s |
| 2 | `backend/.venv/bin/python -c "...shapes parse + assert > 180"` | 0 | ✅ pass | 3.0s |
| 3 | `backend/.venv/bin/python -c "...views parse + assert > 25"` | 0 | ✅ pass | 3.0s |
| 4 | `backend/.venv/bin/python -c "...seed parse + assert > 80"` | 0 | ✅ pass | 3.0s |
| 5 | `python3 -c "import yaml; ...assert BMC Canvas icon"` | 0 | ✅ pass | 3.6s |
| 6 | `backend/.venv/bin/python -c "...sh:in 9 values"` | 0 | ✅ pass | 3.3s |
| 7 | `backend/.venv/bin/python -c "...parse_manifest()"` | 0 | ✅ pass | 3.3s |

## Diagnostics

- Parse any individual file: `backend/.venv/bin/python -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/<subdir>/business-planning.jsonld', format='json-ld'); print(len(g))"`
- Validate manifest: `backend/.venv/bin/python -c "import sys; sys.path.insert(0,'backend'); from pathlib import Path; from app.models.manifest import parse_manifest; m=parse_manifest(Path('models/business-planning')); print(m.name, len(m.icons))"`
- Check sh:in values: use rdflib Collection on the sectionType property shape

## Deviations

None — all files followed the existing patterns exactly.

## Known Issues

None.

## Files Created/Modified

- `models/business-planning/ontology/business-planning.jsonld` — added BMC classes and properties (2 classes, 3 properties)
- `models/business-planning/shapes/business-planning.jsonld` — added BMCCanvasShape and BMCSectionShape with PropertyGroups
- `models/business-planning/views/business-planning.jsonld` — added 3 BMC ViewSpecs (2 table, 1 bmc renderer)
- `models/business-planning/seed/business-planning.jsonld` — added 1 canvas + 9 section instances
- `models/business-planning/manifest.yaml` — added 2 icon definitions, updated description
