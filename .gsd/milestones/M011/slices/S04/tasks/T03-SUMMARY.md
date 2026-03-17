---
id: T03
parent: S04
milestone: M011
provides:
  - 4 SHACL-AF SPARQLConstraint validation rules (research.ttl)
  - 16 seed objects with 4 trigger objects for rule firing (research.jsonld)
  - Full pipeline + pyshacl validation passing end-to-end
key_files:
  - models/research/rules/research.ttl
  - models/research/seed/research.jsonld
key_decisions:
  - Used full URIs in SPARQL (not prefixed names) — consistent with Zettelkasten rules pattern and avoids prefix resolution issues in pyshacl
patterns_established:
  - Seed trigger data pattern — dedicated objects designed to fire specific SHACL-AF rules (orphan evidence, unsupported claim, contested claim, unanswered question)
  - Both sides of all inverseOf pairs pre-populated in seed data per D154
observability_surfaces:
  - "pyshacl.validate(advanced=True) text report lists each violation with source shape IRI, focus node, severity"
  - "validate_archive() returns ValidationResult with is_valid, errors[], warnings[]"
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Created validation rules, seed data, and verified full Research model pipeline

**Created 4 SHACL-AF rules (39 triples) and 16 seed objects (175 triples) with trigger data that fires all 4 rules — pipeline returns 0 errors, pyshacl returns exactly 2 Warning + 2 Info violations on correct focus nodes.**

## What Happened

Created `models/research/rules/research.ttl` with 4 SPARQLConstraint validation rules on separate NodeShapes per D153:
1. **UnsupportedClaimValidationShape** (Warning) — fires when a claim's confidence is "established" or "supported" but no evidence supports it
2. **ContestedClaimValidationShape** (Info) — fires when a claim has both supporting AND refuting evidence
3. **OrphanEvidenceValidationShape** (Warning) — fires when evidence isn't linked to any claim
4. **UnansweredQuestionValidationShape** (Info) — fires when an open research question has no arguments

Created `models/research/seed/research.jsonld` with 16 objects (3 Papers, 5 Claims, 5 Evidence, 2 ResearchQuestions, 1 Argument) including 4 dedicated trigger objects:
- `seed-claim-kg-reduce-silos` — confidence "supported" with no evidence → triggers UnsupportedClaim
- `seed-claim-pkm-failure` — has both supporting and refuting evidence → triggers ContestedClaim
- `seed-evidence-orphan` — not linked to any claim → triggers OrphanEvidence
- `seed-rq-scaling-limits` — status "open" with no arguments → triggers UnansweredQuestion

All 6 inverseOf pairs pre-populated on both sides per D154. Typed literals use correct xsd datatypes per K002.

## Verification

1. **Rules parse:** 39 triples (≥30 threshold) ✓
2. **Seed parse:** 175 triples (≥120 threshold) ✓
3. **Pipeline validation:** `validate_archive()` → `Valid: True, Errors: 0, Warnings: 0` ✓
4. **pyshacl validation:** `conforms=False` with exactly 4 violations ✓
   - Warning: UnsupportedClaimValidationShape → `seed-claim-kg-reduce-silos` ✓
   - Info: ContestedClaimValidationShape → `seed-claim-pkm-failure` ✓
   - Warning: OrphanEvidenceValidationShape → `seed-evidence-orphan` ✓
   - Info: UnansweredQuestionValidationShape → `seed-rq-scaling-limits` ✓
5. **Slice-level triple counts:** Ontology 230, Shapes 535, Views 81 — all above thresholds ✓
6. **All slice verification commands pass** — this is the final task, slice S04 is complete ✓

## Diagnostics

- **Rules parsing:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/rules/research.ttl', format='turtle'); print(f'Rules: {len(g)}')"` — 39 triples
- **Seed parsing:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/seed/research.jsonld', format='json-ld'); print(f'Seed: {len(g)}')"` — 175 triples
- **Full pipeline:** `cd backend && .venv/bin/python3 -c "from pathlib import Path; from app.models.manifest import parse_manifest; from app.models.loader import load_archive; from app.models.validator import validate_archive; m=parse_manifest(Path('../models/research')); a=load_archive(Path('../models/research'),m); r=validate_archive(a); print(f'Valid:{r.is_valid} E:{len(r.errors)} W:{len(r.warnings)}')"` — Valid:True E:0 W:0
- **SHACL-AF validation:** `pyshacl.validate(data, shacl_graph=combined, ont_graph=ontology, advanced=True)` — conforms=False, 2 Warning + 2 Info

## Deviations

- Plan said "emerging" in confidence enum context; shapes actually use "established, supported, contested, speculative, refuted" — seed data uses correct values from shapes
- Plan said argumentType "literature-review" for seed-argument-1; shapes enum actually includes this value — no deviation needed

## Known Issues

None.

## Files Created/Modified

- `models/research/rules/research.ttl` — 4 SHACL-AF SPARQLConstraint rules on separate NodeShapes (39 triples)
- `models/research/seed/research.jsonld` — 16 seed objects with trigger data for all 4 rules (175 triples)
- `.gsd/milestones/M011/slices/S04/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
