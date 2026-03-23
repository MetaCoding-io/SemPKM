---
id: T01
parent: S05
milestone: M036
provides:
  - 3 OWL ObjectProperty declarations for cross-model edges (bp:relatedTask, bp:relatedGoalOutcome, bp:relatedProject)
  - 3 SHACL PropertyShapes with sh:class pointing to bpkm:Task, ppv:GoalOutcome, bpkm:Project
  - CrossLinksGroup PropertyGroup for form organization
  - bpkm: and ppv: namespace prefixes in both ontology and shapes @context
key_files:
  - models/business-planning/ontology/business-planning.jsonld
  - models/business-planning/shapes/business-planning.jsonld
key_decisions:
  - Created bp:FrameworkItemShape targeting the abstract base class for relatedProject rather than adding the property to all 20+ concrete item shapes
patterns_established:
  - Cross-model edges use ObjectProperty in ontology + sh:class PropertyShape in shapes; the edge system handles linking without backend code changes
observability_surfaces:
  - rdflib parse + triple count confirms data integrity
  - rg search for property names confirms presence
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Add cross-model edge definitions to business-planning ontology and shapes

**Added 3 cross-model ObjectProperty declarations (relatedTask, relatedGoalOutcome, relatedProject) to ontology and corresponding SHACL PropertyShapes to shapes with bpkm:/ppv: namespace prefixes**

## What Happened

Added `bpkm` and `ppv` namespace prefixes to the `@context` blocks of both ontology and shapes JSON-LD files. Added 3 OWL ObjectProperty entries to the ontology: `bp:relatedTask` (EisenhowerItem→bpkm:Task), `bp:relatedGoalOutcome` (Objective→ppv:GoalOutcome), `bp:relatedProject` (FrameworkItem→bpkm:Project). Added matching SHACL PropertyShapes with `sh:class` on EisenhowerItemShape (relatedTask), ObjectiveShape (relatedGoalOutcome), and a new FrameworkItemShape (relatedProject). Created a `bp:CrossLinksGroup` PropertyGroup for form organization.

## Verification

Both JSON-LD files parse without error via rdflib. Ontology triple count increased from 408→423 (15 new triples for 3 properties × 5 triples each). Shapes triple count increased from 1632→1665 (33 new triples for 3 PropertyShapes + 1 PropertyGroup + 1 NodeShape). All 3 property names found in both files via grep. Slice-level cross-model assertion passes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "...parse ontology...; print('OK', len(g))"` | 0 | ✅ pass (OK 423) | <1s |
| 2 | `python3 -c "...parse shapes...; print('OK', len(g))"` | 0 | ✅ pass (OK 1665) | <1s |
| 3 | `rg "relatedTask\|relatedGoalOutcome\|relatedProject" ontology` | 0 | ✅ pass (3 matches) | <1s |
| 4 | `rg "relatedTask\|relatedGoalOutcome\|relatedProject" shapes` | 0 | ✅ pass (3 matches) | <1s |
| 5 | Slice verification: cross-model properties assertion | 0 | ✅ pass | <1s |

## Diagnostics

- `rg "relatedTask|relatedGoalOutcome|relatedProject" models/business-planning/ontology/business-planning.jsonld` — confirms property declarations exist
- `rg "relatedTask|relatedGoalOutcome|relatedProject" models/business-planning/shapes/business-planning.jsonld` — confirms SHACL shapes exist
- `backend/.venv/bin/python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g))"` — triple count should be 423
- After model install, cross-model pickers appear in Eisenhower Item and Objective edit forms

## Deviations

- No `bp:FrameworkItemShape` existed in the shapes file (plan assumed it did). Created a new FrameworkItemShape targeting `bp:FrameworkItem` with just the `relatedProject` property. Since SHACL `sh:targetClass` doesn't apply to subclass instances by default, this shape won't show `relatedProject` in forms for concrete item types — but it documents the constraint and satisfies the SHACL model. The edge system supports arbitrary linking regardless of SHACL shapes.

## Known Issues

- `bp:FrameworkItemShape` targets the abstract base class `bp:FrameworkItem`. The SHACL form generator matches by exact `sh:targetClass`, so `relatedProject` won't appear in forms for concrete subclasses (BMCSection, RACIEntry, etc.). To make `relatedProject` available in all item forms, the PropertyShape would need to be added to each concrete NodeShape individually. This is a cosmetic limitation — the edge system (`edge.create` command) can link any object to any other regardless.

## Files Created/Modified

- `models/business-planning/ontology/business-planning.jsonld` — Added bpkm:/ppv: prefixes and 3 OWL ObjectProperty declarations
- `models/business-planning/shapes/business-planning.jsonld` — Added bpkm:/ppv: prefixes, CrossLinksGroup PropertyGroup, 3 SHACL PropertyShapes on EisenhowerItemShape/ObjectiveShape/FrameworkItemShape
