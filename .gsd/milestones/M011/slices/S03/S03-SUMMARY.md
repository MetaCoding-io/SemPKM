---
id: S03
parent: M011
milestone: M011
provides:
  - Complete zettelkasten model archive (6 files) with 5 note types, 3 inverseOf pairs, 4 argumentation links, 3 SHACL-AF validation rules
  - Seed data with 12 objects forming full provenance chain Source→LiteratureNote→PermanentNote→StructureNote
  - 3 validation rules firing at correct severities (2 Warning, 1 Info) against trigger data
requires:
  - slice: none
    provides: independent slice (no upstream dependencies)
affects:
  - S05
key_files:
  - models/zettelkasten/manifest.yaml
  - models/zettelkasten/ontology/zettelkasten.jsonld
  - models/zettelkasten/shapes/zettelkasten.jsonld
  - models/zettelkasten/views/zettelkasten.jsonld
  - models/zettelkasten/rules/zettelkasten.ttl
  - models/zettelkasten/seed/zettelkasten.jsonld
key_decisions:
  - "Namespace is urn:sempkm:model:zettelkasten: (not zk:) — ManifestSchema validator enforces namespace == urn:sempkm:model:{modelId}:. The zk: prefix is JSON-LD shorthand only."
  - "FleetingNote dcterms:created uses xsd:date (not xsd:dateTime) — FleetingNoteShape constrains dcterms:created to xsd:date per K002"
  - "D155 broadening pattern applied: zk:body has no rdfs:domain (shared across 4 note types)"
patterns_established:
  - "Same validation-only SPARQLConstraint pattern as CRM (D153): separate NodeShapes in rules/*.ttl with sh:severity on parent"
  - "Separate FILTER NOT EXISTS blocks per predicate in OrphanPermanentNote rule — rdflib is unreliable with | in NOT EXISTS"
  - "Both sides of inverseOf pre-populated in seed data per D154"
  - "Same namespace split as CRM: shapes use sempkm=urn:sempkm:, views use sempkm=urn:sempkm:vocab:"
observability_surfaces:
  - "parse_manifest(Path('../models/zettelkasten')) — ValueError with structured message on failure"
  - "validate_archive() returns ValidationResult with .is_valid, .errors[], .warnings[]"
  - "pyshacl.validate(..., advanced=True) returns (conforms, results_graph, text) with focus node + severity + message per violation"
  - "Triple count signals: Ontology ≥100, Shapes ≥300, Views ≥60, Rules ≥20, Seed ≥100"
drill_down_paths:
  - .gsd/milestones/M011/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M011/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M011/slices/S03/tasks/T03-SUMMARY.md
duration: 57m
verification_result: passed
completed_at: 2026-03-17
---

# S03: Zettelkasten+ Model

**Complete zettelkasten model archive (747 triples across 6 files) with 5 note types, provenance chain, argumentation links, and 3 SHACL-AF validation rules — all passing offline validation with 0 errors and all rules firing at correct severities.**

## What Happened

Built the Zettelkasten+ mental model archive in 3 tasks:

**T01 (manifest + ontology):** Created `manifest.yaml` with modelId `zettelkasten`, 5 icon entries (zap/book-open/quote/gem/network) each with tree/tab/graph contexts, and entailment_defaults (owl_inverseOf + shacl_rules). Created OWL ontology (132 triples) with 5 classes aligned to gist (FleetingNote→FormattedContent, Source→Content, LiteratureNote/PermanentNote/StructureNote→FormattedContent), 9 datatype properties, 3 inverseOf pairs (derivedFrom↔hasLiteratureNote, developedInto↔developedFrom, includes↔includedInStructure), 4 argumentation links (supports/contradicts/followsFrom/relatedTo), 1 symmetric property (relatedStructure), and 1 one-directional property (processedInto).

**T02 (shapes + views):** Created SHACL shapes (399 triples) with 5 NodeShapes and 14 PropertyGroups providing form layout for all types. `sh:in` enums for sourceType (8 values) and purpose (5 values). `sempkm:editHelpText` on all key fields. Created views (60 triples) with 5 ViewSpecs (3 table, 1 card, 1 graph) and 4 SavedQueries (Unprocessed Fleeting Notes, Isolated Permanent Notes, Contradiction Map, Provenance Chain with CONSTRUCT query).

**T03 (rules + seed + validation):** Created 3 SHACL-AF validation rules in Turtle (31 triples) on separate NodeShapes per D153: UnprocessedFleetingValidation (Warning), OrphanPermanentNoteValidation (Warning), UnsourcedPermanentNoteValidation (Info). Created seed data (125 triples) with 12 objects forming a complete provenance chain: 3 Sources, 2 FleetingNotes (1 unprocessed trigger), 3 LiteratureNotes, 3 PermanentNotes (1 orphaned+unsourced trigger), 1 StructureNote. Both sides of all 3 inverseOf pairs pre-populated per D154. Fixed FleetingNote `dcterms:created` from xsd:dateTime to xsd:date to match SHACL shape constraint (K002 lesson).

## Verification

All 5 slice-level verification steps pass:

1. **Individual file parse:** All 5 files parse cleanly — ontology:132, shapes:399, views:60, seed:125, rules:31 triples
2. **Full pipeline validation:** `parse_manifest()` + `load_archive()` + `validate_archive()` → Valid: True, Errors: 0, Warnings: 0
3. **SHACL-AF validation:** `pyshacl.validate(..., advanced=True)` → conforms=False with exactly 3 violations:
   - sh:Warning — UnprocessedFleetingValidationShape → `seed-fleeting-unprocessed` ("hasn't been processed")
   - sh:Warning — OrphanPermanentNoteValidationShape → `seed-perm-confirmation-bias` ("isolated")
   - sh:Info — UnsourcedPermanentNoteValidationShape → `seed-perm-confirmation-bias` ("no literature source")
4. **Diagnostic failure path:** `parse_manifest(Path('/tmp/nonexistent-model'))` → ValueError: manifest.yaml not found
5. **Triple count sanity:** All counts in expected ranges (132/399/60/31/125 vs thresholds 100/300/60/20/100)

## Requirements Advanced

- MODEL-03 — Zettelkasten+ model archive passes offline validation with 5 types, provenance chain query, argumentation links, and 3 validation rules. Docker integration deferred to S05.

## Requirements Validated

- None yet — Docker install, form rendering, and view rendering must be verified in S05 before MODEL-03 can be marked validated.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **Namespace IRI:** Plan specified `urn:sempkm:model:zk:` but ManifestSchema validator enforces `namespace == urn:sempkm:model:{modelId}:`. With modelId `zettelkasten`, namespace is `urn:sempkm:model:zettelkasten:`. The `zk:` prefix is JSON-LD shorthand only. All SPARQL queries adapted to use full IRIs.
- **FleetingNote dcterms:created datatype:** Plan implied xsd:dateTime but FleetingNoteShape constrains to xsd:date. Changed seed data to xsd:date to avoid spurious SHACL datatype violations (K002 lesson applied).

## Known Limitations

- No Docker integration testing — S05 will verify install, form rendering, view rendering, and inference
- Provenance Chain SavedQuery uses CONSTRUCT (not SELECT) — this may need frontend rendering support in S05
- Seed data is 12 objects — a real Zettelkasten workflow would have hundreds; the seed demonstrates the pattern

## Follow-ups

- S05: Docker install + form rendering + view rendering + E2E tests for zettelkasten model
- S05: Verify Provenance Chain CONSTRUCT query renders correctly in the saved query UI

## Files Created/Modified

- `models/zettelkasten/manifest.yaml` — Model identity, 5 icon entries, entailment_defaults
- `models/zettelkasten/ontology/zettelkasten.jsonld` — OWL ontology with 5 classes, 25 properties (132 triples)
- `models/zettelkasten/shapes/zettelkasten.jsonld` — 5 SHACL NodeShapes, 14 PropertyGroups, enums, helptext (399 triples)
- `models/zettelkasten/views/zettelkasten.jsonld` — 5 ViewSpecs + 4 SavedQueries (60 triples)
- `models/zettelkasten/rules/zettelkasten.ttl` — 3 validation SPARQLConstraints (31 triples)
- `models/zettelkasten/seed/zettelkasten.jsonld` — 12 seed objects with provenance chain and trigger data (125 triples)

## Forward Intelligence

### What the next slice should know
- The zettelkasten model follows the exact same 6-file structure as CRM (S02) and basic-pkm (S01). Same namespace split pattern, same D153/D154 conventions, same validation pipeline. S04 (Research Workflow) can use any of these as structural templates.
- Namespace is `urn:sempkm:model:zettelkasten:` with `zk:` as JSON-LD shorthand — all SPARQL queries use full IRIs.
- The 3 validation rules use NOT EXISTS patterns (not date arithmetic) — K001 lesson from CRM applied proactively.

### What's fragile
- The Provenance Chain SavedQuery uses CONSTRUCT (returns a subgraph, not tabular results) — if the frontend saved query renderer only handles SELECT results, this will need special handling in S05.
- `sh:in` enum values are plain strings in `{"@list": [...]}` format — if the platform's SHACL form renderer expects IRI-valued enums, these will render as text inputs instead of dropdowns.

### Authoritative diagnostics
- `cd backend && .venv/bin/python3 -c "from pathlib import Path; from app.models.manifest import parse_manifest; from app.models.loader import load_archive; from app.models.validator import validate_archive; m=parse_manifest(Path('../models/zettelkasten')); a=load_archive(Path('../models/zettelkasten'), m); r=validate_archive(a); print(f'Valid:{r.is_valid} Errors:{len(r.errors)}')"` — must return Valid:True Errors:0
- pyshacl validation (Step 3 in plan) — must return conforms=False with exactly 3 violations at correct severities

### What assumptions changed
- Plan assumed `urn:sempkm:model:zk:` namespace — actual namespace must be `urn:sempkm:model:zettelkasten:` due to ManifestSchema validation. This was already discovered in S01/S02 for their respective namespaces.
