---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T01: Extend model archive with OKR + Decision Matrix types

**Slice:** S03 — OKR Progress + Decision Matrix Weighted Scoring
**Milestone:** M036

## Description

Add 6 new OWL classes to the business-planning model archive for OKR and Decision Matrix frameworks. This extends the existing model (which already has FrameworkItem, QuadrantItem, EisenhowerMatrix, EisenhowerItem, BusinessModelCanvas, BMCSection from S01/S02) with:

- **OKR**: `bp:Objective` (container) and `bp:KeyResult` (measurable metric with currentValue/targetValue/unit)
- **Decision Matrix**: `bp:DecisionMatrix` (container), `bp:Criterion` (weighted evaluation dimension), `bp:Alternative` (option being evaluated), `bp:Score` (junction linking alternative×criterion with a numeric value)

All types follow the established `bp:` namespace (`urn:sempkm:model:business-planning:`) and JSON-LD inline `@context` conventions.

## Steps

1. **Ontology** — Add 6 OWL classes and ~12 new properties to `ontology/business-planning.jsonld`. Objective (subClassOf `bp:FrameworkItem`), KeyResult (subClassOf `bp:FrameworkItem`), DecisionMatrix (subClassOf `gist:Collection`), Criterion (subClassOf `bp:FrameworkItem`), Alternative (subClassOf `bp:FrameworkItem`), Score (no meaningful superclass — it's a junction node, use `owl:Thing` or `bp:FrameworkItem`). Properties: `bp:currentValue` (xsd:decimal), `bp:targetValue` (xsd:decimal), `bp:unit` (xsd:string), `bp:timeframe` (xsd:string), `bp:belongsToObjective` (ObjectProperty → bp:Objective), `bp:weight` (xsd:decimal), `bp:value` (xsd:decimal), `bp:belongsToMatrix` (ObjectProperty → bp:DecisionMatrix), `bp:scoreAlternative` (ObjectProperty → bp:Alternative), `bp:scoreCriterion` (ObjectProperty → bp:Criterion).

2. **Shapes** — Add 6 SHACL NodeShapes with PropertyGroups to `shapes/business-planning.jsonld`. KeyResult needs `sh:datatype xsd:decimal` on currentValue/targetValue/unit, and `sh:class bp:Objective` on belongsToObjective. Criterion needs `sh:datatype xsd:decimal` on weight. Score needs `sh:datatype xsd:decimal` on value, `sh:class bp:Alternative` on scoreAlternative, `sh:class bp:Criterion` on scoreCriterion. Use PropertyGroups to organize forms (e.g., "Measurement" group for currentValue/targetValue/unit on KeyResult, "Scoring" group for weight on Criterion).

3. **Views** — Add ViewSpecs to `views/business-planning.jsonld`. Six new ViewSpecs: Objectives Table (renderer=table, target=bp:Objective), Key Results Table (renderer=table, target=bp:KeyResult), OKR Progress (renderer=okr, target=bp:KeyResult), Decision Matrices Table (renderer=table, target=bp:DecisionMatrix), Alternatives Table (renderer=table, target=bp:Alternative), Decision Matrix Scoring (renderer=decision-matrix, target=bp:Score).

4. **Seed** — Add seed data to `seed/business-planning.jsonld`. OKR: 1 Objective ("Improve Product Quality") with 3 KeyResults (varying progress — one at 80%, one at 45%, one at 10% — to demonstrate green/amber/red). Decision Matrix: 1 Matrix ("Technology Selection"), 3 Criteria ("Performance" weight=8, "Cost" weight=6, "Ease of Use" weight=4), 3 Alternatives ("Option A", "Option B", "Option C"), 9 Scores (3×3 grid with realistic values 1–10).

5. **Manifest** — Add 6 icon entries to `manifest.yaml` for all new types. Use meaningful Lucide icon names: Objective=`target`, KeyResult=`trending-up`, DecisionMatrix=`scale`, Criterion=`ruler`, Alternative=`layers`, Score=`hash`.

## Must-Haves

- [ ] 6 new OWL classes in ontology with correct superclass hierarchy
- [ ] 6 new SHACL NodeShapes with PropertyGroups and datatype constraints
- [ ] `bp:belongsToObjective` links KeyResult to Objective with `sh:class bp:Objective`
- [ ] `bp:scoreAlternative` and `bp:scoreCriterion` link Score to Alternative and Criterion
- [ ] ViewSpecs with `sempkm:rendererType: "okr"` and `sempkm:rendererType: "decision-matrix"`
- [ ] Seed data with realistic values for progress computation (mix of green/amber/red)
- [ ] Seed Decision Matrix scores form a complete 3×3 grid (every alternative scored on every criterion)
- [ ] 6 icon entries in manifest with Lucide icon names
- [ ] All JSON-LD files parse without error

## Verification

- `python3 -c "import json; data=json.load(open('models/business-planning/ontology/business-planning.jsonld')); classes=[e for e in data['@graph'] if 'owl:Class' in str(e.get('@type',''))]; print(len(classes), 'classes'); [print(' ', e['@id']) for e in classes]"` — shows 12 classes
- `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g), 'triples')"` — parses without error
- `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print(len(g), 'triples')"` — parses without error
- `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/seed/business-planning.jsonld', format='json-ld'); print(len(g), 'triples')"` — parses without error
- `python3 -c "import yaml; m=yaml.safe_load(open('models/business-planning/manifest.yaml')); print(len(m['icons']), 'icons')"` — shows 10 (4 existing + 6 new)

## Inputs

- `models/business-planning/ontology/business-planning.jsonld` — existing ontology with 6 classes (FrameworkItem, QuadrantItem, EisenhowerMatrix, EisenhowerItem, BusinessModelCanvas, BMCSection)
- `models/business-planning/shapes/business-planning.jsonld` — existing shapes for 6 types
- `models/business-planning/views/business-planning.jsonld` — existing ViewSpecs (6 entries)
- `models/business-planning/seed/business-planning.jsonld` — existing seed data (Eisenhower + BMC)
- `models/business-planning/manifest.yaml` — existing manifest with 4 icon entries

## Expected Output

- `models/business-planning/ontology/business-planning.jsonld` — extended with 6 new OWL classes and ~12 properties
- `models/business-planning/shapes/business-planning.jsonld` — extended with 6 new NodeShapes
- `models/business-planning/views/business-planning.jsonld` — extended with 6 new ViewSpecs
- `models/business-planning/seed/business-planning.jsonld` — extended with OKR + Decision Matrix seed data
- `models/business-planning/manifest.yaml` — extended with 6 new icon entries
