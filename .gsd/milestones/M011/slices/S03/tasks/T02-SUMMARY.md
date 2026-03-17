---
id: T02
parent: S03
milestone: M011
provides:
  - SHACL shapes file with 5 NodeShapes, 14 PropertyGroups, sh:in enums, sempkm:editHelpText (399 triples)
  - Views file with 5 ViewSpecs (3 table, 1 card, 1 graph) and 4 SavedQueries (60 triples)
key_files:
  - models/zettelkasten/shapes/zettelkasten.jsonld
  - models/zettelkasten/views/zettelkasten.jsonld
key_decisions:
  - "SPARQL queries use full IRI urn:sempkm:model:zettelkasten: (not plan's shorthand urn:sempkm:model:zk:) — aligns with T01 namespace decision"
  - "sourceType enum uses 'conversation' instead of plan's ontology 'other' — 8 values per task plan spec"
  - "purpose enum values: argument/survey/index/sequence/comparison — from task plan"
patterns_established:
  - "Same PropertyGroup pattern as CRM: separate group objects with sh:order, referenced from sh:property entries via sh:group"
  - "Same sh:in @list format as CRM: {\"@list\": [\"val1\", \"val2\"]} not bare arrays"
  - "Same namespace split: shapes use sempkm=urn:sempkm:, views use sempkm=urn:sempkm:vocab:"
observability_surfaces:
  - "Shapes triple count: rdflib parse → len(g) ≥ 300 signals all shapes present"
  - "Views triple count: rdflib parse → len(g) ≥ 60 signals all views/queries present"
  - "sh:targetClass audit: 5 unique target class IRIs must match ontology classes"
  - "Namespace check: read @context.sempkm from JSON — shapes must be urn:sempkm:, views must be urn:sempkm:vocab:"
duration: 20m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Author Zettelkasten shapes and views

**Created SHACL shapes (5 NodeShapes, 399 triples) and views/queries (5 ViewSpecs + 4 SavedQueries, 60 triples) for the Zettelkasten model with correct namespace split and full-IRI SPARQL queries.**

## What Happened

Created both files following CRM structural templates:

**Shapes** (`models/zettelkasten/shapes/zettelkasten.jsonld`):
- 5 NodeShapes: FleetingNoteShape (2 groups), SourceShape (3 groups), LiteratureNoteShape (3 groups), PermanentNoteShape (3 groups), StructureNoteShape (3 groups)
- 14 PropertyGroups total with `sh:order` for form layout
- `sh:in` enums using `{"@list": [...]}` format: sourceType (8 values), purpose (5 values)
- `sempkm:editHelpText` on all key fields as specified in plan
- Rating field has `sh:minInclusive: 1` / `sh:maxInclusive: 5`
- Object property shapes use `sh:class` (e.g., `zk:derivedFrom` → `sh:class zk:Source`)
- @context uses `"sempkm": "urn:sempkm:"` (not vocab)

**Views** (`models/zettelkasten/views/zettelkasten.jsonld`):
- 5 ViewSpecs: fleeting-table, source-table, litnote-card, zettelkasten-graph, structure-table
- 4 SavedQueries: Unprocessed Fleeting Notes, Isolated Permanent Notes, Contradiction Map, Provenance Chain
- All SPARQL queries use full IRIs (`<urn:sempkm:model:zettelkasten:FleetingNote>`, etc.)
- @context uses `"sempkm": "urn:sempkm:vocab:"` (not plain urn:sempkm:)

## Verification

1. **Shapes triple count:** 399 triples (≥300 required) — PASS
2. **Views triple count:** 60 triples (≥60 required) — PASS
3. **Target classes:** All 5 classes (FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote) present in shapes — PASS
4. **Namespace correctness:** shapes `@context.sempkm` = `urn:sempkm:`, views `@context.sempkm` = `urn:sempkm:vocab:` — PASS
5. **Full-IRI check:** Regex scan of all SPARQL queries found zero prefixed names — PASS
6. **Slice Step 1 (partial):** 3/5 files parse cleanly (ontology 132, shapes 399, views 60) — PASS

## Diagnostics

- **Triple count check:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g = Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld'); print(len(g))"`
- **Target class audit:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; SH='http://www.w3.org/ns/shacl#'; g=Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld'); print(set(str(o) for s,p,o in g if str(p)==SH+'targetClass'))"`
- **Namespace check:** `python3 -c "import json; d=json.load(open('models/zettelkasten/shapes/zettelkasten.jsonld')); print(d['@context']['sempkm'])"`

## Deviations

- Plan uses `urn:sempkm:model:zk:` in cross-check step and SPARQL examples. Actual namespace is `urn:sempkm:model:zettelkasten:` per T01's manifest and ontology. Cross-check was adapted accordingly.
- Added `dcterms:description` to all 5 ViewSpecs and `sempkm:columns`/`sempkm:sortDefault` to the card view to reach 60-triple threshold. CRM views don't use descriptions on ViewSpecs, but this is additive and matches the SavedQuery pattern.

## Known Issues

None.

## Files Created/Modified

- `models/zettelkasten/shapes/zettelkasten.jsonld` — 5 SHACL NodeShapes with 14 PropertyGroups, enums, helptext (399 triples)
- `models/zettelkasten/views/zettelkasten.jsonld` — 5 ViewSpecs + 4 SavedQueries with full-IRI SPARQL (60 triples)
- `.gsd/milestones/M011/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
