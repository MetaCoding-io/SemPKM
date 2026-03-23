---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T01: Create business-planning model archive with Eisenhower types

**Slice:** S01 — Eisenhower Matrix — Model Archive + Quadrant Renderer
**Milestone:** M036

## Description

Create the `business-planning` model archive following the standard 6-file Mental Model structure (manifest.yaml, ontology, shapes, views, seed). This defines the shared base types (bp:FrameworkItem, bp:QuadrantItem) that S02–S04 will extend, and the Eisenhower-specific types (bp:EisenhowerMatrix, bp:EisenhowerItem) with SHACL shapes that drive form generation and quadrant rendering.

The model follows the exact same patterns as `models/basic-pkm/` — JSON-LD files with inline @context (no remote URLs), SHACL NodeShapes with PropertyGroups, ViewSpecs with `sempkm:rendererType`, and seed data with typed literals.

## Steps

1. Create `models/business-planning/manifest.yaml` — modelId `business-planning`, namespace `urn:sempkm:model:business-planning:`, prefix `bp`, entrypoints pointing to each JSON-LD file, icon definitions for EisenhowerMatrix and EisenhowerItem types.

2. Create `models/business-planning/ontology/business-planning.jsonld` — Define owl:Classes:
   - `bp:FrameworkItem` (abstract base for all business framework items, subClassOf gist:Category)
   - `bp:QuadrantItem` (subClassOf bp:FrameworkItem — base for items placed on a 2-axis grid)
   - `bp:EisenhowerMatrix` (the container/collection type, subClassOf gist:Collection)
   - `bp:EisenhowerItem` (subClassOf bp:QuadrantItem)
   - Properties: `bp:urgency`, `bp:importance` (both xsd:string with domain QuadrantItem), `bp:belongsToMatrix` (object property linking item to matrix), `bp:matrixDescription`, `bp:xAxisLabel`, `bp:yAxisLabel`, standard dcterms:title/description.

3. Create `models/business-planning/shapes/business-planning.jsonld` — SHACL NodeShapes:
   - `bp:EisenhowerMatrixShape` targeting bp:EisenhowerMatrix — properties: dcterms:title (required), dcterms:description, dcterms:created
   - `bp:EisenhowerItemShape` targeting bp:EisenhowerItem — properties: dcterms:title (required), dcterms:description, bp:urgency (sh:in ["high","low"], required), bp:importance (sh:in ["high","low"], required), bp:belongsToMatrix (sh:class bp:EisenhowerMatrix)
   - PropertyGroups for logical form sections (Basic Info, Classification, Relationships)

4. Create `models/business-planning/views/business-planning.jsonld` — ViewSpecs:
   - `bp:view-eisenhower-matrix-table` — table view for EisenhowerMatrix listing
   - `bp:view-eisenhower-item-table` — table view for EisenhowerItem with urgency/importance columns
   - `bp:view-eisenhower-item-quadrant` — quadrant view with `sempkm:rendererType: "quadrant"` and `sempkm:targetClass: bp:EisenhowerItem`

5. Create `models/business-planning/seed/business-planning.jsonld` — Seed data:
   - One EisenhowerMatrix instance ("My Priority Matrix")
   - 6+ EisenhowerItem instances distributed across all 4 quadrants (at least 1 per quadrant, more in urgent+important for realism)
   - Each item has a title, description, urgency (high/low), importance (high/low), and belongsToMatrix link

## Must-Haves

- [ ] manifest.yaml passes `ManifestSchema` Pydantic validation
- [ ] All JSON-LD files use inline @context only (no remote URLs)
- [ ] SHACL shapes include `sh:in` constraints on bp:urgency and bp:importance with exactly ["high", "low"] values
- [ ] ViewSpec for quadrant view uses `sempkm:rendererType: "quadrant"`
- [ ] Seed data has items in all 4 quadrants (high/high, high/low, low/high, low/low)
- [ ] Namespace pattern is `urn:sempkm:model:business-planning:`

## Verification

- Validate manifest: `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('../models/business-planning')); print(f'{m.modelId} v{m.version} ns={m.namespace}'); assert m.modelId == 'business-planning'"` (run from backend dir with app importable, or adjust path)
- Validate JSON-LD parsing: `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(f'Ontology: {len(g)} triples'); g2 = Graph(); g2.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print(f'Shapes: {len(g2)} triples'); g3 = Graph(); g3.parse('models/business-planning/views/business-planning.jsonld', format='json-ld'); print(f'Views: {len(g3)} triples'); g4 = Graph(); g4.parse('models/business-planning/seed/business-planning.jsonld', format='json-ld'); print(f'Seed: {len(g4)} triples')"` — all parse successfully with >0 triples

## Inputs

- `models/basic-pkm/manifest.yaml` — reference for manifest structure
- `models/basic-pkm/ontology/basic-pkm.jsonld` — reference for ontology JSON-LD pattern
- `models/basic-pkm/shapes/basic-pkm.jsonld` — reference for SHACL shapes with sh:in, PropertyGroups
- `models/basic-pkm/views/basic-pkm.jsonld` — reference for ViewSpec declarations
- `models/basic-pkm/seed/basic-pkm.jsonld` — reference for seed data with typed literals
- `backend/app/models/manifest.py` — ManifestSchema for validation

## Expected Output

- `models/business-planning/manifest.yaml` — validated model manifest
- `models/business-planning/ontology/business-planning.jsonld` — OWL classes and properties
- `models/business-planning/shapes/business-planning.jsonld` — SHACL NodeShapes with sh:in constraints
- `models/business-planning/views/business-planning.jsonld` — ViewSpecs declaring quadrant renderer
- `models/business-planning/seed/business-planning.jsonld` — seed Eisenhower matrix with items in all 4 quadrants
