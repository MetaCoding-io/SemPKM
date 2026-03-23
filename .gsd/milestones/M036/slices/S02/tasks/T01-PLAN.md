---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T01: Extend model archive with BMC ontology, shapes, views, and seed data

**Slice:** S02 — Business Model Canvas — 9-Box Poster Renderer
**Milestone:** M036

## Description

Add `bp:BusinessModelCanvas` and `bp:BMCSection` OWL classes to the existing business-planning model, with SHACL shapes (including a 9-value `sh:in` constraint on `bp:sectionType`), ViewSpecs for table and BMC renderer, seed data with 1 canvas + 9 sections, and icon definitions in the manifest. All files are JSON-LD with inline `@context` — follow the exact patterns established in S01 for Eisenhower types.

## Steps

1. **Read** all 5 existing model files to understand current structure: `models/business-planning/ontology/business-planning.jsonld`, `shapes/...`, `views/...`, `seed/...`, `manifest.yaml`.
2. **Extend ontology** (`ontology/business-planning.jsonld`): Add `bp:BusinessModelCanvas` (subClassOf `gist:Collection`, like `bp:EisenhowerMatrix`), `bp:BMCSection` (subClassOf `bp:FrameworkItem`), and 3 new properties: `bp:sectionType` (DatatypeProperty, range `xsd:string`), `bp:sectionContent` (DatatypeProperty, range `xsd:string`), `bp:belongsToCanvas` (ObjectProperty, range `bp:BusinessModelCanvas`).
3. **Extend shapes** (`shapes/business-planning.jsonld`): Add `bp:BMCCanvasShape` NodeShape targeting `bp:BusinessModelCanvas` with PropertyGroups (Basic Info, Configuration). Add `bp:BMCSectionShape` NodeShape targeting `bp:BMCSection` with properties for `dcterms:title` (required), `bp:sectionType` (required, `sh:in` with 9 kebab-case values: `key-partners`, `key-activities`, `key-resources`, `value-propositions`, `customer-relationships`, `channels`, `customer-segments`, `cost-structure`, `revenue-streams`), `bp:sectionContent` (optional, `sh:datatype xsd:string`), and `bp:belongsToCanvas` (optional, `sh:class bp:BusinessModelCanvas`). Use PropertyGroups for form organization.
4. **Extend views** (`views/business-planning.jsonld`): Add 3 ViewSpecs — `bp:view-bmc-canvas-table` (table renderer for `bp:BusinessModelCanvas`), `bp:view-bmc-section-table` (table renderer for `bp:BMCSection`), `bp:view-bmc-section-bmc` (bmc renderer for `bp:BMCSection`, `sempkm:rendererType: "bmc"`).
5. **Extend seed** (`seed/business-planning.jsonld`): Add 1 `bp:BusinessModelCanvas` instance ("SemPKM Business Model") + 9 `bp:BMCSection` instances, each with a distinct `bp:sectionType` value and realistic `bp:sectionContent` (2-4 bullet points). All sections link to the canvas via `bp:belongsToCanvas`. Update **manifest** (`manifest.yaml`): add icon definitions for `bp:BusinessModelCanvas` (layout-grid, #2563eb) and `bp:BMCSection` (sticky-note, #f59e0b). Update the description to mention BMC.

## Must-Haves

- [ ] `bp:BusinessModelCanvas` class exists as subClassOf `gist:Collection`
- [ ] `bp:BMCSection` class exists as subClassOf `bp:FrameworkItem`
- [ ] `bp:sectionType` has `sh:in` constraint with exactly 9 kebab-case values
- [ ] ViewSpec with `sempkm:rendererType: "bmc"` targeting `bp:BMCSection`
- [ ] Seed data has 1 canvas + 9 sections with realistic content
- [ ] Manifest has icon definitions for both new types
- [ ] All 5 files parse via rdflib without error

## Verification

- `cd /home/james/Code/SemPKM && python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g), 'triples'); assert len(g) > 55"` — passes (was 49 triples in S01)
- `cd /home/james/Code/SemPKM && python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print(len(g), 'triples'); assert len(g) > 180"` — passes
- `cd /home/james/Code/SemPKM && python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/views/business-planning.jsonld', format='json-ld'); print(len(g), 'triples'); assert len(g) > 25"` — passes
- `cd /home/james/Code/SemPKM && python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/seed/business-planning.jsonld', format='json-ld'); print(len(g), 'triples'); assert len(g) > 80"` — passes (was 55)
- `cd /home/james/Code/SemPKM && python3 -c "import yaml; m=yaml.safe_load(open('models/business-planning/manifest.yaml')); assert any(i['type']=='bp:BusinessModelCanvas' for i in m['icons']); print('OK')"` — passes

## Inputs

- `models/business-planning/ontology/business-planning.jsonld` — existing ontology with 4 OWL classes (FrameworkItem, QuadrantItem, EisenhowerMatrix, EisenhowerItem)
- `models/business-planning/shapes/business-planning.jsonld` — existing SHACL shapes for Eisenhower types
- `models/business-planning/views/business-planning.jsonld` — existing ViewSpecs for Eisenhower types
- `models/business-planning/seed/business-planning.jsonld` — existing seed data with 8 Eisenhower items
- `models/business-planning/manifest.yaml` — existing manifest with Eisenhower icon definitions

## Expected Output

- `models/business-planning/ontology/business-planning.jsonld` — extended with BMC classes + properties
- `models/business-planning/shapes/business-planning.jsonld` — extended with BMC NodeShapes
- `models/business-planning/views/business-planning.jsonld` — extended with 3 BMC ViewSpecs
- `models/business-planning/seed/business-planning.jsonld` — extended with 1 canvas + 9 sections
- `models/business-planning/manifest.yaml` — extended with BMC icon definitions + updated description
