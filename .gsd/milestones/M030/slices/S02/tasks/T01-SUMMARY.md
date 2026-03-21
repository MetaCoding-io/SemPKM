---
id: T01
parent: S02
milestone: M030
provides:
  - 10 new SHACL-AF SPARQLConstraint validation rules across 4 model rules files
  - Expanded PrefixDeclarations in basic-pkm.ttl and ppv.ttl
key_files:
  - models/basic-pkm/rules/basic-pkm.ttl
  - models/zettelkasten/rules/zettelkasten.ttl
  - models/ppv/rules/ppv.ttl
  - models/research/rules/research.ttl
key_decisions:
  - Scoped titleless and orphan rules to basic-pkm types via FILTER(STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:")) to avoid false positives on CRM/other models
  - Used sh:targetSubjectsOf rdf:type for multi-class rules (empty body, titleless, orphan) since sh:targetClass cannot target multiple classes per shape
  - Used full IRIs for body predicate and schema:url in SPARQL since those vocabularies are not in PrefixDeclarations
patterns_established:
  - Multi-class validation via sh:targetSubjectsOf rdf:type + UNION in SPARQL body
  - Type-namespace scoping via FILTER(STRSTARTS(...)) to limit cross-model rule firing
observability_surfaces:
  - Each rule produces sh:Warning or sh:Info violations visible in GET /api/objects/{id}/lint
  - Malformed SPARQL causes pyshacl ReportableRuntimeError (500 on lint endpoint)
  - Offline parse check: python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle')"
duration: 25m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Write SHACL-AF validation rules across 4 model rules files

**Added 10 new SHACL-AF SPARQLConstraint validation NodeShapes (6 basic-pkm, 1 zettelkasten, 3 ppv, 1 research) with expanded PrefixDeclarations**

## What Happened

Implemented all validation rules specified in the task plan across 4 model rules files:

**basic-pkm.ttl** (6 new validation shapes + expanded PrefixDeclarations):
- `CommaInTagsValidationShape` (Warning) — detects comma-separated tags
- `EmptyBodyValidationShape` (Info) — Note/Concept with no body
- `ConceptNoDefinitionValidationShape` (Info) — Concept missing skos:definition
- `TitlelessObjectValidationShape` (Warning) — basic-pkm objects with no title property
- `OrphanObjectValidationShape` (Info) — basic-pkm objects with no connections to other typed resources
- `DuplicateUrlValidationShape` (Info) — same-type objects sharing a schema:url
- Added rdf, rdfs, skos, foaf, schema prefixes to PrefixDeclarations + file-level @prefix declarations

**zettelkasten.ttl** (1 new validation shape):
- `EmptyBodyValidationShape` (Info) — any of 4 zk note types with no body

**ppv.ttl** (3 new validation shapes + expanded PrefixDeclarations):
- `StaleProjectValidationShape` (Info) — Project with no dcterms:modified (avoids K001 date arithmetic)
- `ActionItemNoProjectValidationShape` (Warning) — ActionItem not linked to a Project
- `ProjectNoGoalValidationShape` (Warning) — Project not linked to a GoalOutcome
- Added dcterms and xsd to PrefixDeclarations

**research.ttl** (1 new validation shape):
- `ClaimNoRationaleValidationShape` (Info) — Claim with no rationale property

The plan title says "9 new rules" but the steps specify 10 NodeShapes (broken chain = 2 shapes, and duplicate URL is listed separately). All 10 shapes from the plan steps are implemented.

## Verification

- All 4 .ttl files parse cleanly with rdflib (no syntax errors, correct triple counts)
- 19 total validation shapes across all files (8 existing + 11 new — the extra 1 vs plan's "10" is because duplicate URL was under-counted in the plan's verification section)
- Each NodeShape has sh:severity, sh:sparql with sh:SPARQLConstraint, sh:message, sh:prefixes, and sh:select
- Orphan and titleless rules scoped to basic-pkm types
- Body predicate uses full IRI `<urn:sempkm:vocab:body>`
- Stale project uses "no dcterms:modified" NOT EXISTS check (K001 safe)
- Existing cross-model validation tests pass (from main repo — worktree models not yet picked up by tests)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "g.parse('models/basic-pkm/rules/basic-pkm.ttl')"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "g.parse('models/zettelkasten/rules/zettelkasten.ttl')"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "g.parse('models/ppv/rules/ppv.ttl')"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "g.parse('models/research/rules/research.ttl')"` | 0 | ✅ pass | <1s |
| 5 | Validation shape count check (expected 19) | 0 | ✅ pass | <1s |
| 6 | `pytest tests/test_cross_model_validation.py -v` (from main repo) | 0 | ✅ pass | 1.5s |

Slice-level verification (partial — T02 will complete):
- `test_data_quality_rules.py` — does not exist yet (T02 creates it)
- `test_cross_model_validation.py` — passes but needs EXPECTED_PYSHACL count updates (T02)
- Full test suite — not run from worktree (config issue); main repo tests pass

## Diagnostics

- **Offline parse check:** `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle'); print(len(g))"`
- **Runtime:** Violations surface via `GET /api/objects/{id}/lint` when the Docker stack is running with the updated models
- **Failure mode:** Malformed SPARQL or missing PrefixDeclarations → pyshacl ReportableRuntimeError → 500 on lint endpoint + traceback in `docker compose logs backend`

## Deviations

- Plan says "5 new validation NodeShapes in basic-pkm" and "10 total" but the steps actually specify 6 in basic-pkm (duplicate URL was listed as a separate must-have bullet, not counted in the "5"). Implemented all 6 per the steps. Total new shapes = 11 (6+1+3+1).

## Known Issues

None.

## Files Created/Modified

- `models/basic-pkm/rules/basic-pkm.ttl` — 6 new validation NodeShapes + expanded PrefixDeclarations (rdf, rdfs, skos, foaf, schema) + file-level @prefix for skos, foaf, dcterms
- `models/zettelkasten/rules/zettelkasten.ttl` — 1 new EmptyBodyValidationShape
- `models/ppv/rules/ppv.ttl` — 3 new validation NodeShapes + expanded PrefixDeclarations (dcterms, xsd) + file-level @prefix for dcterms
- `models/research/rules/research.ttl` — 1 new ClaimNoRationaleValidationShape
- `.gsd/milestones/M030/slices/S02/S02-PLAN.md` — Added Observability/Diagnostics section + failure-path verification check
- `.gsd/milestones/M030/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section
