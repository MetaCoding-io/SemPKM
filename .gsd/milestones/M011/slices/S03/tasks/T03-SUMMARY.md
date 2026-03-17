---
id: T03
parent: S03
milestone: M011
provides:
  - SHACL-AF validation rules with 3 separate NodeShapes (31 triples) — UnprocessedFleeting (Warning), OrphanPermanent (Warning), UnsourcedPermanent (Info)
  - Seed data with 12 objects (125 triples) forming complete provenance chain Source→LiteratureNote→PermanentNote→StructureNote with trigger data for all 3 validation rules
  - Full pipeline validation (0 errors) and pyshacl fires all 3 rules at correct severities
key_files:
  - models/zettelkasten/rules/zettelkasten.ttl
  - models/zettelkasten/seed/zettelkasten.jsonld
key_decisions:
  - "FleetingNote dcterms:created uses xsd:date (not xsd:dateTime) in seed data — FleetingNoteShape constrains dcterms:created to xsd:date, so dateTime values cause spurious sh:Violation from SHACL datatype validation"
patterns_established:
  - "Same validation-only SPARQLConstraint pattern as CRM: sh:severity on NodeShape, sh:sparql with SPARQLConstraint, full IRIs in SPARQL SELECT, PrefixDeclarations for pyshacl"
  - "Separate FILTER NOT EXISTS blocks per predicate in OrphanPermanentNote rule (not property path |) — rdflib inconsistency with | in NOT EXISTS"
  - "Both sides of inverseOf pre-populated in seed data per D154: derivedFrom↔hasLiteratureNote, developedInto↔developedFrom, includes↔includedInStructure"
observability_surfaces:
  - "pyshacl.validate(..., advanced=True) returns (conforms, results_graph, text) with focus node + severity + message per violation"
  - "validate_archive() returns ValidationResult with .is_valid, .errors[], .warnings[]"
  - "Triple count signals: Rules ≥20, Seed ≥100"
duration: 25m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Author Zettelkasten rules, seed data, and run full pipeline validation

**Created 3 SHACL-AF validation rules (31 triples) and 12 seed objects (125 triples) forming a complete Zettelkasten provenance chain, with all 3 rules firing at correct severities (2 Warning, 1 Info) against trigger data.**

## What Happened

Created the rules file (`zettelkasten.ttl`) with 3 validation-only SPARQLConstraints on separate NodeShapes per D153:
1. **UnprocessedFleetingValidationShape** (Warning) — fires when FleetingNote has no `processedInto` link
2. **OrphanPermanentNoteValidationShape** (Warning) — fires when PermanentNote has no supports/contradicts/followsFrom/includedInStructure (uses 4 separate FILTER NOT EXISTS blocks, not property paths)
3. **UnsourcedPermanentNoteValidationShape** (Info) — fires when PermanentNote has no `developedFrom` link

Created seed data (`zettelkasten.jsonld`) with 12 objects forming a complete provenance chain:
- 3 Sources (Ahrens book, Dobelli book, Le Cunff article)
- 2 FleetingNotes (1 unprocessed → triggers Rule 1, 1 processed with `processedInto` link)
- 3 LiteratureNotes (derived from Sources, with originalQuote and pageReference)
- 3 PermanentNotes (1 well-connected, 1 in structure but no argumentation links, 1 completely orphaned+unsourced → triggers Rules 2+3)
- 1 StructureNote (purpose: "argument", includes 2 of 3 PermanentNotes)

Both sides of all 3 inverseOf pairs pre-populated per D154 (derivedFrom↔hasLiteratureNote, developedInto↔developedFrom, includes↔includedInStructure).

Initial SHACL validation revealed 2 spurious `sh:Violation` errors because FleetingNote `dcterms:created` used `xsd:dateTime` but the FleetingNoteShape constrains it to `xsd:date`. Fixed by changing FleetingNote created dates to `xsd:date` format.

## Verification

All 5 slice verification steps pass:

1. **Individual file parse:** All 5 files parse — ontology:132, shapes:399, views:60, seed:125, rules:31 triples
2. **Full pipeline validation:** `validate_archive()` returns `Valid: True, Errors: 0, Warnings: 0`
3. **SHACL-AF validation:** `pyshacl.validate(..., advanced=True)` returns `conforms=False` with exactly 3 violations:
   - sh:Warning — UnprocessedFleetingValidationShape → `seed-fleeting-unprocessed`
   - sh:Warning — OrphanPermanentNoteValidationShape → `seed-perm-confirmation-bias`
   - sh:Info — UnsourcedPermanentNoteValidationShape → `seed-perm-confirmation-bias`
4. **Diagnostic failure-path:** `parse_manifest(Path('/tmp/nonexistent-model'))` raises `ValueError: manifest.yaml not found`
5. **Triple count sanity:** Ontology:132, Shapes:399, Views:60, Rules:31, Seed:125 — all in expected ranges

## Diagnostics

- **Inspect rules:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/zettelkasten/rules/zettelkasten.ttl', format='turtle'); print(len(g), 'triples')"`
- **Inspect seed:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/zettelkasten/seed/zettelkasten.jsonld', format='json-ld'); print(len(g), 'triples')"`
- **Run full SHACL-AF validation:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; import pyshacl; r=Graph().parse('../models/zettelkasten/rules/zettelkasten.ttl', format='turtle'); s=Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld'); d=Graph().parse('../models/zettelkasten/seed/zettelkasten.jsonld', format='json-ld'); o=Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld'); c,_,t=pyshacl.validate(d, shacl_graph=s+r, ont_graph=o, advanced=True); print(t[:2000])"`

## Deviations

- FleetingNote `dcterms:created` changed from `xsd:dateTime` to `xsd:date` in seed data — the plan specified `xsd:dateTime` format (`2026-03-12T09:00:00Z`) but the FleetingNoteShape (from T02) constrains `dcterms:created` to `xsd:date`, causing spurious SHACL datatype violations. Using `xsd:date` (`2026-03-12`) eliminates the mismatch.

## Known Issues

None.

## Files Created/Modified

- `models/zettelkasten/rules/zettelkasten.ttl` — 3 SHACL-AF validation rules in Turtle (31 triples): UnprocessedFleeting (Warning), OrphanPermanent (Warning), UnsourcedPermanent (Info)
- `models/zettelkasten/seed/zettelkasten.jsonld` — 12 seed objects in JSON-LD (125 triples): 3 Sources, 2 FleetingNotes, 3 LiteratureNotes, 3 PermanentNotes, 1 StructureNote with trigger data for all 3 validation rules
- `.gsd/milestones/M011/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section per pre-flight requirement
