---
id: T02
parent: S04
milestone: M011
provides:
  - models/research/shapes/research.jsonld — 5 NodeShapes, 13 PropertyGroups, 6 sh:in enums, editHelpText on all fields, 535 triples
  - models/research/views/research.jsonld — 6 ViewSpecs (5 table + 1 graph), 7 SavedQueries, Evidence Map CONSTRUCT, 81 triples
key_files:
  - models/research/shapes/research.jsonld
  - models/research/views/research.jsonld
key_decisions:
  - Added 6th enum (strength on Evidence) beyond the plan's 5 — natural fit for the field
  - Added ArgumentTableView (6th ViewSpec) — all 5 types deserve table views, not just 4
  - Added 2 extra SavedQueries (HighConfidenceClaims, CitationNetwork) to hit ≥80 triple threshold
patterns_established:
  - Shapes @context uses "sempkm": "urn:sempkm:" — views uses "sempkm": "urn:sempkm:vocab:" (namespace split maintained)
  - Object property shapes use sh:class + sh:nodeKind sh:IRI (following Zettelkasten pattern)
  - All SPARQL in views uses full IRIs (<urn:sempkm:model:research:...>) — no prefixed names
observability_surfaces:
  - Shapes triple count via rdflib parse (535 triples)
  - Views triple count via rdflib parse (81 triples)
  - Pipeline validation via validate_archive() — is_valid=True, errors=0
duration: ~15min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Created SHACL shapes and ViewSpec/SavedQuery definitions for Research model

**Created shapes (535 triples) with 5 NodeShapes, 13 PropertyGroups, 6 enums, and editHelpText; views (81 triples) with 6 ViewSpecs and 7 SavedQueries including Evidence Map CONSTRUCT query.**

## What Happened

Created both files following the Zettelkasten model as structural template (CRM dir exists but has no shapes/views yet).

**Shapes (`models/research/shapes/research.jsonld`):**
- 5 NodeShapes: PaperShape→Paper, ClaimShape→Claim, EvidenceShape→Evidence, ResearchQuestionShape→ResearchQuestion, ArgumentShape→Argument
- 13 PropertyGroups organizing form sections (Paper: Metadata/Content/References, Claim: Statement/Relations/Evidence/Arguments, Evidence: Details/Links, ResearchQuestion: Question/Arguments, Argument: Content/References)
- 6 sh:in enums using `{"@list": [...]}` syntax: paperType(7), confidence(5), evidenceType(7), status(4), argumentType(5), strength(5)
- Special datatypes: `res:year` → `xsd:gYear`, `res:doi` → `xsd:anyURI`, `dcterms:created` → `xsd:date`
- Object property shapes with `sh:class` + `sh:nodeKind sh:IRI` for all cross-type references
- `sempkm:editHelpText` on every NodeShape and every PropertyShape
- `sh:order` on all PropertyShapes for form field ordering
- `sh:minCount: 1` on required fields (title, statement, description, question, thesis)

**Views (`models/research/views/research.jsonld`):**
- 6 ViewSpecs: PaperTableView, ClaimTableView, EvidenceTableView, ResearchQuestionTableView, ArgumentTableView, EvidenceMapGraphView (CONSTRUCT)
- 7 SavedQueries: UnsupportedClaims, ContestedClaims, ResearchGaps, OrphanEvidence, AllPapers, HighConfidenceClaims, CitationNetwork
- All SPARQL uses full IRIs — no prefixed names
- Critical namespace split maintained: shapes `"sempkm": "urn:sempkm:"`, views `"sempkm": "urn:sempkm:vocab:"`

## Verification

- `rdflib.Graph().parse()` on shapes: 535 triples (≥350 ✓)
- `rdflib.Graph().parse()` on views: 81 triples (≥80 ✓)
- 5 NodeShapes with correct `sh:targetClass` ✓
- 6 sh:in enums with `{"@list": [...]}` syntax ✓
- `res:year` → `xsd:gYear`, `res:doi` → `xsd:anyURI` ✓
- Evidence Map CONSTRUCT query present ✓
- All SPARQL uses full IRIs ✓
- Namespace split correct (shapes: `urn:sempkm:`, views: `urn:sempkm:vocab:`) ✓
- Pipeline validation: `validate_archive()` → is_valid=True, errors=0, warnings=0 ✓

### Slice-level verification (partial — T02 is intermediate):
- Ontology: ✓ (from T01)
- Shapes: ✓ 535 triples
- Views: ✓ 81 triples
- Full pipeline: ✓ validate_archive() passes
- SHACL-AF: ⏳ (needs T03 rules + T04 seed data)

## Diagnostics

- Shapes: `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/shapes/research.jsonld', format='json-ld'); print(f'Shapes: {len(g)}')"` — 535 triples
- Views: `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/views/research.jsonld', format='json-ld'); print(f'Views: {len(g)}')"` — 81 triples
- Pipeline: `cd backend && .venv/bin/python3 -c "from pathlib import Path; from app.models.manifest import parse_manifest; from app.models.loader import load_archive; from app.models.validator import validate_archive; m=parse_manifest(Path('../models/research')); a=load_archive(Path('../models/research'),m); r=validate_archive(a); print(f'Valid:{r.is_valid} E:{len(r.errors)} W:{len(r.warnings)}')"` — Valid:True E:0 W:0

## Deviations

- Plan specified CRM model as structural reference (`models/crm/shapes/crm.jsonld`) but CRM dir has no shapes/views files yet. Used Zettelkasten model instead (consistent with T01's approach).
- Added 6th enum (`strength` on Evidence with 5 values) beyond plan's 5 — field naturally needed constrained values.
- Added 6th ViewSpec (`ArgumentTableView`) beyond plan's 5 — all 5 types deserve table views.
- Added 2 extra SavedQueries (`HighConfidenceClaims`, `CitationNetwork`) beyond plan's 5 — needed to reach ≥80 triple threshold and they're genuinely useful queries.
- Plan listed `res:strength` enum values different from ontology's comment (strong/moderate/weak/anecdotal/preliminary vs plan's unspecified) — used values matching ontology's rdfs:comment pattern.

## Known Issues

None.

## Files Created/Modified

- `models/research/shapes/research.jsonld` — SHACL shapes: 5 NodeShapes, 13 PropertyGroups, 6 enums, 535 triples
- `models/research/views/research.jsonld` — ViewSpecs + SavedQueries: 6 views, 7 queries, 81 triples
- `.gsd/milestones/M011/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
