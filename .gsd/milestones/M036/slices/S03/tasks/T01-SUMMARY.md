---
id: T01
parent: S03
milestone: M036
provides:
  - 6 new OWL classes for OKR and Decision Matrix frameworks
  - 6 new SHACL NodeShapes with PropertyGroups
  - 6 new ViewSpecs including okr and decision-matrix renderers
  - Seed data with 1 Objective, 3 Key Results (80%/45%/10%), 1 Matrix, 3 Criteria, 3 Alternatives, 9 Scores
  - 6 new icon entries in manifest
key_files:
  - models/business-planning/ontology/business-planning.jsonld
  - models/business-planning/shapes/business-planning.jsonld
  - models/business-planning/views/business-planning.jsonld
  - models/business-planning/seed/business-planning.jsonld
  - models/business-planning/manifest.yaml
key_decisions:
  - "Used bp:belongsToDecisionMatrix instead of bp:belongsToMatrix for Decision Matrix relationships to avoid collision with existing Eisenhower property"
patterns_established:
  - "OKR progress computed as currentValue/targetValue ratio — seed data demonstrates green (80%), amber (45%), red (10%) thresholds"
  - "Score junction node pattern: bp:Score links bp:Alternative × bp:Criterion with bp:value, enabling Decision Matrix weighted scoring"
observability_surfaces:
  - "ViewSpecs with sempkm:rendererType 'okr' and 'decision-matrix' enable downstream renderer registration"
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Extend model archive with OKR + Decision Matrix types

**Added 6 OWL classes (Objective, KeyResult, DecisionMatrix, Criterion, Alternative, Score), SHACL shapes, ViewSpecs with okr/decision-matrix renderers, seed data with green/amber/red progress spread and complete 3×3 scoring grid, and 6 manifest icon entries to business-planning model**

## What Happened

Extended all 5 business-planning model archive files with OKR and Decision Matrix types:

**Ontology** — Added 6 classes: Objective and KeyResult (subClassOf FrameworkItem) for OKR, DecisionMatrix (subClassOf gist:Collection), Criterion, Alternative, and Score (all subClassOf FrameworkItem) for Decision Matrix. Added 10 new properties: currentValue, targetValue, unit, timeframe, belongsToObjective for OKR; weight, value, belongsToDecisionMatrix, scoreAlternative, scoreCriterion for Decision Matrix. Used `bp:belongsToDecisionMatrix` instead of reusing `bp:belongsToMatrix` (which already targets EisenhowerMatrix).

**Shapes** — Added 6 NodeShapes with PropertyGroups. KeyResult shape has Measurement group (currentValue xsd:decimal, targetValue xsd:decimal, unit xsd:string) and Relationships group (belongsToObjective with sh:class bp:Objective). Criterion shape has Scoring group (weight xsd:decimal required). Score shape has required value (xsd:decimal) plus required links to Alternative (sh:class) and Criterion (sh:class).

**Views** — Added 6 ViewSpecs: Objectives Table, Key Results Table, OKR Progress (renderer=okr), Decision Matrices Table, Alternatives Table, Decision Matrix Scoring (renderer=decision-matrix). The OKR view query joins Key Results to their Objective for grouped display. The Decision Matrix view query joins Score→Alternative→Criterion with weight for weighted scoring computation.

**Seed** — 1 Objective ("Improve Product Quality", Q2 2026) with 3 Key Results at 80% (green), 45% (amber), 10% (red). 1 Decision Matrix ("Technology Selection") with 3 Criteria (Performance weight=8, Cost weight=6, Ease of Use weight=4), 3 Alternatives (Rust/Go/Python), and 9 Scores forming a complete 3×3 grid.

**Manifest** — 6 icon entries: Objective=target, KeyResult=trending-up, DecisionMatrix=scale, Criterion=ruler, Alternative=layers, Score=hash.

## Verification

All task-level checks pass:
- 12 OWL classes found (6 existing + 6 new)
- All 4 JSON-LD files parse via rdflib without error (145 ontology, 659 shapes, 76 views, 233 seed triples)
- 10 icons in manifest (4 existing + 6 new)
- 9 seed scores forming complete 3×3 grid
- Key Result progress percentages: 80%, 45%, 10%

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import json; ... print(len(classes), 'classes')"` (ontology class count) | 0 | ✅ 12 classes | 0.1s |
| 2 | `backend/.venv/bin/python -c "from rdflib ... ontology"` (rdflib parse) | 0 | ✅ 145 triples | 3.0s |
| 3 | `backend/.venv/bin/python -c "from rdflib ... shapes"` (rdflib parse) | 0 | ✅ 659 triples | 3.0s |
| 4 | `backend/.venv/bin/python -c "from rdflib ... views"` (rdflib parse) | 0 | ✅ 76 triples | 3.0s |
| 5 | `backend/.venv/bin/python -c "from rdflib ... seed"` (rdflib parse) | 0 | ✅ 233 triples | 3.0s |
| 6 | `python3 -c "import yaml; ... print(len(m['icons']), 'icons')"` (manifest icon count) | 0 | ✅ 10 icons | 0.1s |
| 7 | Score grid check (9 scores, 3 alternatives × 3 criteria) | 0 | ✅ complete 3×3 | 0.1s |
| 8 | KR progress check (80%, 45%, 10%) | 0 | ✅ green/amber/red | 0.1s |

## Diagnostics

- Parse any model file: `backend/.venv/bin/python -c "from rdflib import Graph; g=Graph(); g.parse('models/business-planning/<file>.jsonld', format='json-ld'); print(len(g))"`
- List classes: `python3 -c "import json; [print(e['@id']) for e in json.load(open('models/business-planning/ontology/business-planning.jsonld'))['@graph'] if 'owl:Class' in str(e.get('@type',''))]"`
- List view specs: `python3 -c "import json; [print(e.get('rdfs:label'), '->', e.get('sempkm:rendererType')) for e in json.load(open('models/business-planning/views/business-planning.jsonld'))['@graph']]"`

## Deviations

- Used `bp:belongsToDecisionMatrix` instead of plan's `bp:belongsToMatrix` — the latter already exists with domain EisenhowerItem → range EisenhowerMatrix. Reusing it would create an ambiguous domain/range.
- Adjusted seed KR values from plan's original numbers to achieve exact 80%/45%/10% progress ratios for clear green/amber/red demonstration.

## Known Issues

None.

## Files Created/Modified

- `models/business-planning/ontology/business-planning.jsonld` — Added 6 OWL classes (Objective, KeyResult, DecisionMatrix, Criterion, Alternative, Score) and 10 new properties
- `models/business-planning/shapes/business-planning.jsonld` — Added 6 SHACL NodeShapes with PropertyGroups and datatype/class constraints
- `models/business-planning/views/business-planning.jsonld` — Added 6 ViewSpecs including okr and decision-matrix renderer types
- `models/business-planning/seed/business-planning.jsonld` — Added OKR seed (1 Objective + 3 KRs) and Decision Matrix seed (1 Matrix + 3 Criteria + 3 Alternatives + 9 Scores)
- `models/business-planning/manifest.yaml` — Added 6 icon entries for new types
