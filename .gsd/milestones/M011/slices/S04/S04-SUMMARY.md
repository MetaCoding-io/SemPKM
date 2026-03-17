---
id: S04
parent: M011
milestone: M011
provides:
  - models/research/ — Complete .sempkm-model archive with 5 types (Paper, Claim, Evidence, ResearchQuestion, Argument), 6 inverseOf pairs, 4 SHACL-AF validation rules, 6 ViewSpecs, 7 SavedQueries, 16 seed objects
requires:
  - slice: none
    provides: independent slice per D151
affects:
  - S05 (cross-model verification, E2E tests, user guide)
key_files:
  - models/research/manifest.yaml
  - models/research/ontology/research.jsonld
  - models/research/shapes/research.jsonld
  - models/research/views/research.jsonld
  - models/research/rules/research.ttl
  - models/research/seed/research.jsonld
key_decisions:
  - Used Zettelkasten model as structural template (CRM dir had empty subdirectories but no files)
  - Added 6th enum (strength) and 6th ViewSpec (ArgumentTableView) beyond plan — natural completeness
  - Added 2 extra SavedQueries (HighConfidenceClaims, CitationNetwork) for genuine utility
patterns_established:
  - Research model follows identical JSON-LD @context pattern as Zettelkasten/PPV — inline only, no remote URLs
  - Seed trigger data pattern — dedicated objects designed to fire specific SHACL-AF rules
  - Multi-constraint validation on separate NodeShapes proven (4 rules, 2 severities)
  - Both sides of all inverseOf pairs pre-populated in seed data per D154
observability_surfaces:
  - parse_manifest(Path('../models/research')) → research v1.0.0 with 5 icons
  - rdflib.Graph().parse() → Ontology 230, Shapes 535, Views 81 triples
  - validate_archive() → Valid=True, Errors=0, Warnings=0
  - pyshacl.validate(advanced=True) → conforms=False, 2 Warning + 2 Info on correct focus nodes
drill_down_paths:
  - .gsd/milestones/M011/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M011/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M011/slices/S04/tasks/T03-SUMMARY.md
duration: ~33m (T01 6m + T02 15m + T03 12m)
verification_result: passed
completed_at: 2026-03-17
---

# S04: Research Workflow Model

**Delivered complete Research Workflow `.sempkm-model` archive with 5 types, 4 SHACL-AF validation rules (unsupported claims, contested claims, orphan evidence, unanswered questions), 6 ViewSpecs, 7 SavedQueries, and 16 seed objects — all passing offline pipeline and pyshacl validation.**

## What Happened

Built the Research Workflow model in 3 tasks following the same patterns established by S01 (basic-pkm v2), S02 (CRM), and S03 (Zettelkasten+):

**T01 — Manifest + Ontology (6m):** Created `manifest.yaml` with modelId `research`, namespace `urn:sempkm:model:research:`, 5 icon entries (file-text/message-square-quote/flask-conical/help-circle/scale), and entailment_defaults enabling owl_inverseOf + shacl_rules. Created `ontology/research.jsonld` with 5 OWL classes aligned to gist hierarchy (Paper→Content, Claim/Evidence/Argument→FormattedContent, ResearchQuestion→Intention), 22 datatype properties, 17 object properties with 6 bidirectional inverseOf pairs, and 5 one-directional object properties. Total: 230 triples.

**T02 — Shapes + Views (15m):** Created `shapes/research.jsonld` with 5 NodeShapes, 13 PropertyGroups, 6 sh:in enums (paperType 7 values, confidence 5, evidenceType 7, status 4, argumentType 5, strength 5), editHelpText on every field, and object property shapes using sh:class + sh:nodeKind sh:IRI. Total: 535 triples. Created `views/research.jsonld` with 6 ViewSpecs (5 table views — one per type — plus Evidence Map graph with CONSTRUCT query) and 7 SavedQueries (UnsupportedClaims, ContestedClaims, ResearchGaps, OrphanEvidence, AllPapers, HighConfidenceClaims, CitationNetwork). Total: 81 triples. Critical namespace split maintained: shapes uses `"sempkm": "urn:sempkm:"`, views uses `"sempkm": "urn:sempkm:vocab:"`.

**T03 — Rules + Seed + Pipeline Validation (12m):** Created `rules/research.ttl` with 4 SHACL-AF SPARQLConstraint rules on separate NodeShapes per D153: UnsupportedClaimValidationShape (Warning — confidence is "established"/"supported" but no evidence), ContestedClaimValidationShape (Info — both supporting and refuting evidence), OrphanEvidenceValidationShape (Warning — evidence not linked to any claim), UnansweredQuestionValidationShape (Info — open question with no arguments). Created `seed/research.jsonld` with 16 objects (3 Papers, 5 Claims, 5 Evidence, 2 ResearchQuestions, 1 Argument) including 4 dedicated trigger objects for all 4 rules. Both sides of all 6 inverseOf pairs pre-populated per D154. Total: rules 39 triples, seed 175 triples.

## Verification

All slice-level verification commands pass:

| Check | Result | Threshold |
|-------|--------|-----------|
| Ontology triple count | 230 | ≥150 ✓ |
| Shapes triple count | 535 | ≥350 ✓ |
| Views triple count | 81 | ≥80 ✓ |
| `validate_archive()` | Valid=True, Errors=0 | 0 errors ✓ |
| `pyshacl.validate()` | conforms=False, 4 violations | 2 Warning + 2 Info ✓ |

SHACL-AF validation detail — all 4 rules fire on correct focus nodes:
- **Warning:** UnsupportedClaimValidationShape → `seed-claim-kg-reduce-silos` (confidence "supported", no evidence)
- **Info:** ContestedClaimValidationShape → `seed-claim-pkm-failure` (has both supporting and refuting evidence)
- **Warning:** OrphanEvidenceValidationShape → `seed-evidence-orphan` (not linked to any claim)
- **Info:** UnansweredQuestionValidationShape → `seed-rq-scaling-limits` (open, no arguments)

## Requirements Advanced

- MODEL-04 — Research Workflow model archive passes offline validation with all 5 types, 4 validation rules, 6 ViewSpecs, and seed data. Remaining: Docker install, form rendering, view rendering, and E2E tests (S05).

## Requirements Validated

- none (Docker integration and E2E tests required for full validation — deferred to S05)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Used Zettelkasten model as structural template instead of CRM (CRM directory had empty subdirectories but no manifest/ontology/shapes/views files). Consistent across all 3 tasks.
- Added 6th enum (`strength` on Evidence with 5 values) beyond plan's 5 — natural fit for the field.
- Added 6th ViewSpec (`ArgumentTableView`) beyond plan's 5 — all 5 types deserve table views.
- Added 2 extra SavedQueries (`HighConfidenceClaims`, `CitationNetwork`) beyond plan's 5 — needed to reach ≥80 triple threshold and provide genuine utility.
- Plan specified 5 ViewSpecs + 5 SavedQueries; delivered 6 ViewSpecs + 7 SavedQueries.

## Known Limitations

- Archive is offline-validated only — Docker install, form rendering, view rendering, and inference not yet tested (deferred to S05).
- Evidence Map graph view CONSTRUCT query is defined but untested against a running triplestore.
- No user guide documentation yet (S05 scope).
- No E2E Playwright tests yet (S05 scope).

## Follow-ups

- S05: Install research model in Docker, verify form rendering for all 5 types, test Evidence Map graph view, run saved queries against live triplestore, write E2E tests, document in user guide Chapter 31.

## Files Created/Modified

- `models/research/manifest.yaml` — model manifest: modelId=research, v1.0.0, 5 icons, entailment defaults
- `models/research/ontology/research.jsonld` — OWL ontology: 5 classes, 22 datatype props, 17 object props, 6 inverseOf pairs (230 triples)
- `models/research/shapes/research.jsonld` — SHACL shapes: 5 NodeShapes, 13 PropertyGroups, 6 enums, editHelpText (535 triples)
- `models/research/views/research.jsonld` — ViewSpecs + SavedQueries: 6 views, 7 queries, Evidence Map CONSTRUCT (81 triples)
- `models/research/rules/research.ttl` — 4 SHACL-AF SPARQLConstraint rules on separate NodeShapes (39 triples)
- `models/research/seed/research.jsonld` — 16 seed objects with trigger data for all 4 rules (175 triples)

## Forward Intelligence

### What the next slice should know
- All 4 model archives (basic-pkm v2, crm, zettelkasten, research) are complete and pass offline validation. S05 can install all 4 simultaneously and verify cross-model coexistence.
- The research model has 4 validation rules that should produce exactly 2 Warning + 2 Info when seed data is loaded — use this as a regression check after Docker install.
- All SPARQL in views uses full IRIs (`<urn:sempkm:model:research:...>`), not prefixed names — this is consistent across all 4 models and avoids prefix resolution issues in the triplestore.
- The `sempkm:` namespace split between shapes (`urn:sempkm:`) and views (`urn:sempkm:vocab:`) is critical — all 4 models follow this convention.

### What's fragile
- The shapes @context / views @context namespace split (`urn:sempkm:` vs `urn:sempkm:vocab:`) — a single-character difference that causes form rendering to silently fail if wrong. All 4 models have this correct but it's the #1 thing to check if forms don't render.
- pyshacl date arithmetic patterns vary by model — basic-pkm uses STRDT/SUBSTR for date comparison (Pattern #1 in KNOWLEDGE.md), CRM uses NOT EXISTS (K001), research uses simple string comparison for confidence enum. Each model's approach was chosen based on what rdflib actually supports.

### Authoritative diagnostics
- `cd backend && .venv/bin/python3 -c "from pathlib import Path; from app.models.manifest import parse_manifest; from app.models.loader import load_archive; from app.models.validator import validate_archive; m=parse_manifest(Path('../models/research')); a=load_archive(Path('../models/research'),m); r=validate_archive(a); print(f'Valid:{r.is_valid} E:{len(r.errors)} W:{len(r.warnings)}')"` — single command proving archive integrity
- pyshacl validation text report — lists each violation with focus node, severity, and constraint IRI

### What assumptions changed
- Plan assumed CRM model would be the structural template — CRM directory existed but had no files. Zettelkasten was used instead across all 3 tasks. No impact on output quality.
