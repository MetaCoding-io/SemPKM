---
estimated_steps: 6
estimated_files: 2
---

# T02: Author Zettelkasten shapes and views

**Slice:** S03 — Zettelkasten+ Model
**Milestone:** M011

## Description

Create the Zettelkasten model's SHACL shapes and ViewSpec/SavedQuery files. Shapes define 5 NodeShapes with PropertyGroups driving form generation, including enums for sourceType and purpose. Views define 5 ViewSpecs (table/card/graph) and 4 SavedQueries for browsing Zettelkasten data.

**Critical namespace rule:** Shapes use `"sempkm": "urn:sempkm:"`, views use `"sempkm": "urn:sempkm:vocab:"`. Mixing causes runtime failures (proven in S01 and S02).

Follow `.gsd/worktrees/M011/models/crm/shapes/crm.jsonld` and `.gsd/worktrees/M011/models/crm/views/crm.jsonld` as structural templates.

## Steps

1. **Read reference files** to confirm exact structure:
   - `.gsd/worktrees/M011/models/crm/shapes/crm.jsonld` — SHACL NodeShape with PropertyGroups, `sh:in` with `@list`, `sempkm:editHelpText`, @context pattern
   - `.gsd/worktrees/M011/models/crm/views/crm.jsonld` — ViewSpec + SavedQuery JSON-LD patterns, SPARQL query embedding, @context with `"sempkm": "urn:sempkm:vocab:"`

2. **Create `models/zettelkasten/shapes/zettelkasten.jsonld`** with:
   - `@context` with `"sempkm": "urn:sempkm:"` (NOT vocab), plus `sh`, `zk`, `rdfs`, `xsd`, `dcterms`, `schema`, `bpkm`, `rdf`
   - **5 NodeShapes** with `sh:targetClass`:
     - `zk:FleetingNoteShape` — 2 PropertyGroups:
       - "Capture" (dcterms:title required, zk:body, zk:capturedFrom)
       - "Metadata" (bpkm:tags, dcterms:created)
     - `zk:SourceShape` — 3 PropertyGroups:
       - "Source Info" (dcterms:title required, dcterms:creator, zk:sourceType with `sh:in @list` of 8 values: book/article/paper/podcast/video/website/lecture/conversation)
       - "Details" (schema:datePublished, schema:url, zk:notes, zk:rating with sh:minInclusive 1 / sh:maxInclusive 5)
       - "Metadata" (bpkm:tags)
     - `zk:LiteratureNoteShape` — 3 PropertyGroups:
       - "Content" (dcterms:title required, zk:body, zk:originalQuote, zk:pageReference)
       - "Source Link" (zk:derivedFrom)
       - "Metadata" (bpkm:tags)
     - `zk:PermanentNoteShape` — 3 PropertyGroups:
       - "Idea" (dcterms:title required, zk:body, zk:sequenceId)
       - "Connections" (zk:supports, zk:contradicts, zk:followsFrom, zk:relatedTo, zk:developedFrom, zk:includedInStructure)
       - "Metadata" (bpkm:tags)
     - `zk:StructureNoteShape` — 3 PropertyGroups:
       - "Overview" (dcterms:title required, zk:body, zk:purpose with `sh:in @list` of 5 values: argument/survey/index/sequence/comparison)
       - "Included Notes" (zk:includes, zk:relatedStructure)
       - "Metadata" (bpkm:tags)
   - `sempkm:editHelpText` on key fields:
     - zk:body: "Write in your own words. Each note should capture one atomic idea."
     - zk:capturedFrom: "Where did this thought come from? App, conversation, book, etc."
     - zk:originalQuote: "The exact quote from the source, for attribution."
     - zk:pageReference: "Page number or location in the source."
     - zk:sequenceId: "Optional Luhmann-style ID (e.g., 1a2b) for manual ordering."
     - zk:purpose: "What role does this structure note serve in your knowledge system?"
   - All `sh:in` enums use `{"@list": [...]}` format (not bare arrays)

3. **Validate shapes:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld')
   print(f'Shapes: {len(g)} triples')
   assert len(g) >= 300, f'Expected 300+ triples for 5 shapes with PropertyGroups, got {len(g)}'
   "
   ```

4. **Create `models/zettelkasten/views/zettelkasten.jsonld`** with:
   - `@context` with `"sempkm": "urn:sempkm:vocab:"` (NOT plain urn:sempkm:), plus `zk`, `rdfs`, `xsd`, `dcterms`, `rdf`
   - **5 ViewSpecs:**
     - `zk:view-fleeting-table` — type `sempkm:TableView`, targets `zk:FleetingNote`, SELECT query with title, created, processedInto status
     - `zk:view-source-table` — type `sempkm:TableView`, targets `zk:Source`, SELECT with title, creator, sourceType, datePublished
     - `zk:view-litnote-card` — type `sempkm:CardView`, targets `zk:LiteratureNote`, SELECT with title, body excerpt, source label
     - `zk:view-zettelkasten-graph` — type `sempkm:GraphView`, targets `zk:PermanentNote`, CONSTRUCT with supports/contradicts/followsFrom edges
     - `zk:view-structure-table` — type `sempkm:TableView`, targets `zk:StructureNote`, SELECT with title, purpose, included note count
   - **4 SavedQueries:**
     - "Unprocessed Fleeting Notes" — FleetingNotes older than 3 days with no processedInto. Uses `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` for date comparison.
     - "Isolated Permanent Notes" — PermanentNotes with no argumentation links (supports/contradicts/followsFrom/includedInStructure)
     - "Contradiction Map" — PermanentNote pairs connected by `zk:contradicts`
     - "Provenance Chain" — CONSTRUCT showing Source → LiteratureNote → PermanentNote chain
   - **Full IRIs** in all SPARQL query strings (e.g., `<urn:sempkm:model:zk:FleetingNote>`)

5. **Validate views:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/zettelkasten/views/zettelkasten.jsonld', format='json-ld')
   print(f'Views: {len(g)} triples')
   assert len(g) >= 60, f'Expected 60+ triples for 5 ViewSpecs + 4 SavedQueries, got {len(g)}'
   "
   ```

6. **Cross-check: shapes reference all 5 ontology classes, views reference all 5 types:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph, URIRef
   SH = 'http://www.w3.org/ns/shacl#'
   shapes = Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld')
   targets = set(str(o) for s, p, o in shapes if str(p) == SH + 'targetClass')
   print(f'Shape target classes: {targets}')
   expected = {'urn:sempkm:model:zk:FleetingNote', 'urn:sempkm:model:zk:Source', 'urn:sempkm:model:zk:LiteratureNote', 'urn:sempkm:model:zk:PermanentNote', 'urn:sempkm:model:zk:StructureNote'}
   assert expected == targets, f'Missing targets: {expected - targets}'
   print('All 5 target classes present')
   "
   ```

## Must-Haves

- [ ] `models/zettelkasten/shapes/zettelkasten.jsonld` parses to ≥300 triples
- [ ] 5 NodeShapes with correct `sh:targetClass` for all 5 Zettelkasten types
- [ ] PropertyGroups per type with logical field grouping
- [ ] `sh:in` enums for sourceType (8 values) and purpose (5 values) using `@list` format
- [ ] `sempkm:editHelpText` on key fields
- [ ] Shapes @context uses `"sempkm": "urn:sempkm:"` (NOT vocab)
- [ ] `models/zettelkasten/views/zettelkasten.jsonld` parses to ≥60 triples
- [ ] 5 ViewSpecs covering all types (3 table, 1 card, 1 graph)
- [ ] 4 SavedQueries (Unprocessed Fleeting, Isolated Permanent, Contradiction Map, Provenance Chain)
- [ ] Views @context uses `"sempkm": "urn:sempkm:vocab:"` (NOT plain urn:sempkm:)
- [ ] Full IRIs in all SPARQL query strings (no prefixed names)

## Verification

- Shapes file parses with rdflib to ≥300 triples
- Views file parses with rdflib to ≥60 triples
- All 5 target classes present in shapes
- Both files have correct sempkm namespace for their role

## Inputs

- `models/zettelkasten/manifest.yaml` — model namespace and type prefixes (from T01)
- `models/zettelkasten/ontology/zettelkasten.jsonld` — property IRIs, class IRIs, datatype ranges (from T01)
- `.gsd/worktrees/M011/models/crm/shapes/crm.jsonld` — structural template for shapes
- `.gsd/worktrees/M011/models/crm/views/crm.jsonld` — structural template for views

## Expected Output

- `models/zettelkasten/shapes/zettelkasten.jsonld` — 5 SHACL NodeShapes with PropertyGroups, enums, helptext (≥300 triples)
- `models/zettelkasten/views/zettelkasten.jsonld` — 5 ViewSpecs + 4 SavedQueries (≥60 triples)
