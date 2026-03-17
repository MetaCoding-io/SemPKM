---
estimated_steps: 5
estimated_files: 2
---

# T02: Create SHACL shapes and ViewSpec/SavedQuery definitions

**Slice:** S04 — Research Workflow Model
**Milestone:** M011

## Description

Create SHACL shapes with 5 NodeShapes, ~20 PropertyGroups, 5 enums, and editHelpText for form generation. Create views with 5 ViewSpecs (4 table views + 1 Evidence Map graph) and 5 SavedQueries. This follows the exact CRM/Zettelkasten pattern — shapes drive form rendering, views drive table/card/graph display.

**Critical namespace split:** Shapes `@context` uses `"sempkm": "urn:sempkm:"` while views `@context` uses `"sempkm": "urn:sempkm:vocab:"`. Mixing these causes runtime failures. This is the #1 pitfall from S02/S03.

## Steps

1. **Read the CRM shapes for structural reference:** `models/crm/shapes/crm.jsonld` — copy JSON-LD structure, NodeShape pattern, PropertyGroup pattern, sh:in enum pattern, editHelpText pattern. Pay attention to `@context` which uses `"sempkm": "urn:sempkm:"`.

2. **Create `models/research/shapes/research.jsonld`:**
   - **@context:** inline with `"sempkm": "urn:sempkm:"` (NOT `urn:sempkm:vocab:`), plus sh, rdfs, rdf, xsd, dcterms, owl, res (= `urn:sempkm:model:research:`).
   - **5 NodeShapes** (`sh:targetClass` pointing to each OWL class):
     - `res:PaperShape` → `res:Paper`
     - `res:ClaimShape` → `res:Claim`
     - `res:EvidenceShape` → `res:Evidence`
     - `res:ResearchQuestionShape` → `res:ResearchQuestion`
     - `res:ArgumentShape` → `res:Argument`
   - **PropertyGroups** (~20 groups for logical form sections):
     - Paper: Metadata (title, authors, year, venue, doi, paperType), Content (abstract), References (cites, citedBy, hasClaim)
     - Claim: Statement (statement, confidence, rationale), Relations (extractedFrom, corroborates, contradicts, dependsOn), Evidence (supportedBy, refutedBy), Arguments (addressedBy)
     - Evidence: Details (description, evidenceType, source, methodology, strength), Links (supports, refutes, fromPaper)
     - ResearchQuestion: Question (question, status, context, significance), Arguments (hasArgument)
     - Argument: Content (thesis, argumentType, summary), References (addresses, usesClaim, usesEvidence)
   - **5 sh:in enums** (using `{"@list": [...]}` syntax):
     - `res:paperType`: journal-article, conference-paper, preprint, book-chapter, thesis, report, other
     - `res:confidence`: established, supported, contested, speculative, refuted
     - `res:evidenceType`: empirical-data, statistical-finding, case-study, expert-opinion, logical-argument, observation, quote
     - `res:status`: open, partially-answered, answered, abandoned
     - `res:argumentType`: literature-review, position-paper, analysis, synthesis, rebuttal
   - **sh:datatype** on all datatype property shapes:
     - Most string fields: `xsd:string`
     - `res:doi`: `xsd:anyURI`
     - `res:year`: `xsd:gYear`
     - `dcterms:created`: `xsd:date`
   - **Object property shapes** with `sh:class` + `sh:nodeKind sh:IRI`:
     - Claim→Claim self-references (corroborates, contradicts, dependsOn): `sh:class res:Claim`
     - Cross-type links: appropriate `sh:class` for target type
   - **sempkm:editHelpText** on key fields (e.g., "The central assertion this claim makes", "DOI or permanent URL for this paper")
   - **sh:order** on PropertyShapes for form field ordering within each group

3. **Read the CRM views for structural reference:** `models/crm/views/crm.jsonld` — copy ViewSpec and SavedQuery patterns. Note `@context` uses `"sempkm": "urn:sempkm:vocab:"`.

4. **Create `models/research/views/research.jsonld`:**
   - **@context:** inline with `"sempkm": "urn:sempkm:vocab:"` (different from shapes!)
   - **5 ViewSpecs:**
     - `res:PaperTableView` — SELECT ?iri ?title ?authors ?year ?venue ?paperType for Paper
     - `res:ClaimTableView` — SELECT ?iri ?statement ?confidence for Claim
     - `res:EvidenceTableView` — SELECT ?iri ?description ?evidenceType ?strength for Evidence
     - `res:ResearchQuestionTableView` — SELECT ?iri ?question ?status for ResearchQuestion
     - `res:EvidenceMapGraphView` — CONSTRUCT query joining Claims, Evidence, and Papers (most complex SPARQL in M011)
   - **5 SavedQueries:**
     - `res:UnsupportedClaimsQuery` — claims with confidence established/supported but no supporting evidence
     - `res:ContestedClaimsQuery` — claims with both supporting and refuting evidence
     - `res:ResearchGapsQuery` — open research questions with no arguments
     - `res:OrphanEvidenceQuery` — evidence not linked to any claim
     - `res:AllPapersQuery` — all papers with claim counts
   - All SPARQL uses **full IRIs** (`<urn:sempkm:model:research:...>`) not prefixed names
   - ViewSpec properties: `sempkm:renderer` (table/graph), `sempkm:forType`, `sempkm:sparqlSelect`/`sempkm:sparqlConstruct`, `rdfs:label`, `sempkm:columns`
   - SavedQuery properties: `sempkm:queryText`, `rdfs:label`, `dcterms:description`

5. **Verify both files:**
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/research/shapes/research.jsonld', format='json-ld')
   print(f'Shapes triples: {len(g)}')
   assert len(g) >= 350, f'Expected ≥350, got {len(g)}'
   "
   ```
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/research/views/research.jsonld', format='json-ld')
   print(f'Views triples: {len(g)}')
   assert len(g) >= 80, f'Expected ≥80, got {len(g)}'
   "
   ```

## Must-Haves

- [ ] 5 NodeShapes with sh:targetClass pointing to correct OWL classes
- [ ] 5 sh:in enums using `{"@list": [...]}` syntax
- [ ] Shapes @context uses `"sempkm": "urn:sempkm:"` (NOT vocab)
- [ ] Views @context uses `"sempkm": "urn:sempkm:vocab:"` (NOT bare)
- [ ] All SPARQL in views uses full IRIs, not prefixed names
- [ ] `res:year` uses `sh:datatype xsd:gYear`, `res:doi` uses `sh:datatype xsd:anyURI`
- [ ] Shapes ≥350 triples, views ≥80 triples
- [ ] Evidence Map graph view has CONSTRUCT query

## Verification

- `rdflib.Graph().parse()` on shapes succeeds with ≥350 triples
- `rdflib.Graph().parse()` on views succeeds with ≥80 triples
- No Python exceptions during parsing

## Inputs

- `models/research/manifest.yaml` — from T01 (namespace, type IRIs)
- `models/research/ontology/research.jsonld` — from T01 (class and property IRIs to reference in shapes)
- `models/crm/shapes/crm.jsonld` — structural template for NodeShape/PropertyGroup/enum patterns
- `models/crm/views/crm.jsonld` — structural template for ViewSpec/SavedQuery patterns

## Observability Impact

- **Shapes triple count** — `rdflib.Graph().parse()` on `models/research/shapes/research.jsonld` reports triple count. ≥350 confirms adequate PropertyShape/PropertyGroup/enum coverage.
- **Views triple count** — `rdflib.Graph().parse()` on `models/research/views/research.jsonld` reports triple count. ≥80 confirms ViewSpec and SavedQuery coverage.
- **Pipeline validation** — `validate_archive()` on the research model returns `is_valid=True, errors=0` when shapes and views are structurally sound.
- **Failure shapes:** JSON-LD parse errors surface as Python exceptions with descriptive messages. Missing `sh:targetClass` or wrong namespace causes downstream form/view rendering failures (empty forms, missing columns).
- **Diagnostic commands:**
  - Shapes: `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/shapes/research.jsonld', format='json-ld'); print(f'Shapes: {len(g)}')"` — reports triple count
  - Views: `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/views/research.jsonld', format='json-ld'); print(f'Views: {len(g)}')"` — reports triple count

## Expected Output

- `models/research/shapes/research.jsonld` — 5 NodeShapes, ~20 PropertyGroups, 5 enums, editHelpText, ≥350 triples
- `models/research/views/research.jsonld` — 5 ViewSpecs, 5 SavedQueries, Evidence Map CONSTRUCT, ≥80 triples
