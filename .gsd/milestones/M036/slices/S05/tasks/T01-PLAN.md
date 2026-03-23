---
estimated_steps: 4
estimated_files: 2
skills_used: []
---

# T01: Add cross-model edge definitions to business-planning ontology and shapes

**Slice:** S05 — Cross-Model Integration, E2E Tests & Documentation
**Milestone:** M036

## Description

Add 3 OWL ObjectProperty declarations to the business-planning ontology that link framework items to types in other installed models (basic-pkm and ppv). Add corresponding SHACL PropertyShapes so these edges appear in the SHACL-generated forms. This is purely a model archive edit — zero platform code changes.

The edge system (`edge.create` command) already supports arbitrary object-to-object linking via predicate IRIs. The SHACL form generator renders ObjectProperty fields with `sh:class` as reference pickers. No backend or frontend changes are needed.

## Steps

1. **Edit `models/business-planning/ontology/business-planning.jsonld`:**
   - Add `bpkm` and `ppv` namespace prefixes to the `@context`:
     - `"bpkm": "urn:sempkm:model:basic-pkm:"`
     - `"ppv": "urn:sempkm:model:ppv:"`
   - Add 3 new ObjectProperty entries to `@graph`:
     - `bp:relatedTask` — domain: `bp:EisenhowerItem`, range: `bpkm:Task`, label: "Related Task", comment: "Link a prioritized item to its task tracking"
     - `bp:relatedGoalOutcome` — domain: `bp:Objective`, range: `ppv:GoalOutcome`, label: "Related Goal Outcome", comment: "Link an OKR objective to a PPV goal outcome"
     - `bp:relatedProject` — domain: `bp:FrameworkItem`, range: `bpkm:Project`, label: "Related Project", comment: "Link any framework item to a project"

2. **Edit `models/business-planning/shapes/business-planning.jsonld`:**
   - Add `bpkm` and `ppv` namespace prefixes to the `@context`
   - Add a SHACL PropertyShape on the `bp:EisenhowerItemShape` NodeShape:
     - `sh:path bp:relatedTask`, `sh:class bpkm:Task`, `sh:nodeKind sh:IRI`, `sh:maxCount 1`, `sh:name "Related Task"`, `sh:group` in a Cross-Links property group
   - Add a SHACL PropertyShape on the `bp:ObjectiveShape` NodeShape:
     - `sh:path bp:relatedGoalOutcome`, `sh:class ppv:GoalOutcome`, `sh:nodeKind sh:IRI`, `sh:maxCount 1`, `sh:name "Related Goal Outcome"`
   - Add a SHACL PropertyShape on the `bp:FrameworkItemShape` NodeShape:
     - `sh:path bp:relatedProject`, `sh:class bpkm:Project`, `sh:nodeKind sh:IRI`, `sh:maxCount 1`, `sh:name "Related Project"`
   - Add a `bp:CrossLinksGroup` PropertyGroup for organizing these in forms

3. **Verify JSON-LD parsing:**
   - `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g))"`
   - `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print(len(g))"`
   - Both must parse without error and show increased triple counts.

4. **Verify cross-model references:**
   - `rg "relatedTask|relatedGoalOutcome|relatedProject" models/business-planning/ontology/business-planning.jsonld` — 3 properties found
   - `rg "relatedTask|relatedGoalOutcome|relatedProject" models/business-planning/shapes/business-planning.jsonld` — 3 shapes found

## Must-Haves

- [ ] 3 OWL ObjectProperty declarations (bp:relatedTask, bp:relatedGoalOutcome, bp:relatedProject) in ontology
- [ ] Each property has correct domain, range, label, and comment
- [ ] bpkm: and ppv: namespace prefixes in both ontology and shapes @context blocks
- [ ] 3 SHACL PropertyShapes with sh:class pointing to cross-model type IRIs
- [ ] Both JSON-LD files parse without error via rdflib

## Verification

- `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print('OK', len(g))"` — prints OK with increased count (was 408 after S04)
- `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print('OK', len(g))"` — prints OK with increased count (was 1632 after S04)
- `rg "relatedTask|relatedGoalOutcome|relatedProject" models/business-planning/ontology/business-planning.jsonld | wc -l` returns ≥ 3

## Inputs

- `models/business-planning/ontology/business-planning.jsonld` — existing ontology with 89 @graph entries and 408 triples
- `models/business-planning/shapes/business-planning.jsonld` — existing SHACL shapes with 65 @graph entries and 1632 triples

## Expected Output

- `models/business-planning/ontology/business-planning.jsonld` — ontology with 3 new ObjectProperty entries and bpkm:/ppv: prefixes
- `models/business-planning/shapes/business-planning.jsonld` — shapes with 3 new PropertyShapes, a CrossLinksGroup, and bpkm:/ppv: prefixes

## Observability Impact

This task adds only static RDF model data (no runtime code). Observability is limited to:
- **Inspection:** `rdflib.Graph().parse()` on either JSON-LD file — triple count increases confirm data was added. Searching for `relatedTask`, `relatedGoalOutcome`, `relatedProject` in either file confirms presence.
- **Runtime signal (after model install):** The SHACL form generator will include cross-model reference pickers on Eisenhower Item and Objective edit forms. If the cross-model target types (`bpkm:Task`, `ppv:GoalOutcome`, `bpkm:Project`) are not installed, the picker will render but show no options — this is expected behavior, not a failure.
- **Failure visibility:** If the JSON-LD is malformed, `rdflib.parse()` raises an exception with line/offset info. Model install will fail at the ontology/shapes import step with a triplestore parse error.
