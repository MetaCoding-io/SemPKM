---
id: S02
parent: M030
milestone: M030
provides:
  - 10 new SHACL-AF SPARQLConstraint validation rules across 4 model rules files (6 basic-pkm, 1 zettelkasten, 3 ppv, 1 research — plan said 9 but actual implementation correctly has 10 since PPV broken chain is 2 separate shapes)
  - 24 per-rule pytest tests (11 positive + 12 negative + 1 multi-type) in test_data_quality_rules.py
  - Updated EXPECTED_PYSHACL counts in test_cross_model_validation.py reflecting new rules firing against seed data
  - Expanded PrefixDeclarations in basic-pkm.ttl and ppv.ttl
requires:
  - slice: S01
    provides: Pipeline fix (advanced=True, rules graphs loaded) that allows new rules to fire in production
affects:
  - S04
key_files:
  - models/basic-pkm/rules/basic-pkm.ttl
  - models/zettelkasten/rules/zettelkasten.ttl
  - models/ppv/rules/ppv.ttl
  - models/research/rules/research.ttl
  - backend/tests/test_data_quality_rules.py
  - backend/tests/test_cross_model_validation.py
  - backend/tests/test_basic_pkm_v2.py
key_decisions:
  - D278 (planning): Cross-model rules placed in basic-pkm's rules file with broad target patterns
  - D282 (planning): Orphan object rule implemented as SHACL-AF, not SavedQuery — monitor performance
  - Type-namespace scoping via FILTER(STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:")) limits cross-model rules to basic-pkm types only
  - sh:targetSubjectsOf rdf:type for multi-class rules (empty body, titleless, orphan) since sh:targetClass cannot target multiple classes per shape
  - sh:sourceShape filtering in test helper isolates individual rule results, avoiding cross-rule noise (K019)
  - Refactored 4 hardcoded per-model pyshacl tests into single parametrized test using EXPECTED_PYSHACL dict
patterns_established:
  - Multi-class SHACL-AF validation via sh:targetSubjectsOf rdf:type + UNION in SPARQL body
  - Type-namespace scoping via FILTER(STRSTARTS(...)) to limit cross-model rule firing
  - Per-rule test pattern using _run_rule_test helper with sh:sourceShape filtering to isolate individual rules
  - Test class per SHACL validation shape with positive (fires) and negative (doesn't fire) test methods
observability_surfaces:
  - Each rule produces sh:Warning or sh:Info violations visible in GET /api/objects/{id}/lint
  - Malformed SPARQL causes pyshacl ReportableRuntimeError → 500 on lint endpoint + traceback in Docker logs
  - Offline parse check: python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle')"
  - pytest tests/test_data_quality_rules.py -v shows per-rule pass/fail with full pyshacl results_text on failure
drill_down_paths:
  - .gsd/milestones/M030/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M030/slices/S02/tasks/T02-SUMMARY.md
duration: 43m
verification_result: passed
completed_at: 2026-03-20
---

# S02: Data Quality Rules (9 new SHACL-AF rules)

**10 new SHACL-AF SPARQLConstraint validation rules across 4 Mental Models, each proven by isolated positive/negative pytest tests against synthetic data**

## What Happened

T01 wrote 10 new validation NodeShapes across 4 model rules files, following the SPARQLConstraint pattern established by the 11 existing M011 rules. The rules target real-world data quality issues across all installed Mental Models:

**basic-pkm.ttl** (6 new shapes):
- `CommaInTagsValidationShape` (Warning) — detects comma-separated tags that should be individual tag triples
- `EmptyBodyValidationShape` (Info) — Note or Concept with no body content
- `ConceptNoDefinitionValidationShape` (Info) — Concept missing skos:definition
- `TitlelessObjectValidationShape` (Warning) — basic-pkm objects with no dcterms:title or rdfs:label
- `OrphanObjectValidationShape` (Info) — basic-pkm objects with zero connections to other typed resources
- `DuplicateUrlValidationShape` (Info) — same-type objects sharing a schema:url value

**zettelkasten.ttl** (1 new shape):
- `EmptyBodyValidationShape` (Info) — any of 4 zk note types (FleetingNote, Source, LiteratureNote, PermanentNote) with no body

**ppv.ttl** (3 new shapes):
- `StaleProjectValidationShape` (Info) — Project with no dcterms:modified (avoids K001 date arithmetic limitation)
- `ActionItemNoProjectValidationShape` (Warning) — ActionItem not linked to any Project
- `ProjectNoGoalValidationShape` (Warning) — Project not linked to a GoalOutcome

**research.ttl** (1 new shape):
- `ClaimNoRationaleValidationShape` (Info) — Claim with no rationale property

Two cross-model rules (titleless and orphan) are scoped to basic-pkm types via `FILTER(STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:"))` to avoid false positives on CRM Contacts and other models with different naming conventions (D278).

T02 created `test_data_quality_rules.py` with 11 test classes containing 24 tests total — 11 positive tests proving each rule fires, 12 negative tests proving rules don't fire on valid data, and 1 multi-type test proving all 4 zettelkasten note types trigger the empty-body rule. Each test uses a `_run_rule_test` helper that filters by `sh:sourceShape` to isolate individual rule results (K019 pattern).

T02 also updated `EXPECTED_PYSHACL` counts in `test_cross_model_validation.py` to reflect new rules firing against seed data: basic-pkm gained 6 infos (empty body on 3 Notes + 3 Concepts), zettelkasten gained 9 infos (empty body on 9 note-type objects). The 4 separate per-model test functions were refactored into a single parametrized `test_pyshacl_expected_counts[model_name]` test. An existing test in `test_basic_pkm_v2.py` was fixed to avoid false positives from the new titleless/orphan rules by adding titles and connections to its synthetic Task data.

## Verification

All 4 slice-level verification commands pass:

| # | Command | Result | Duration |
|---|---------|--------|----------|
| 1 | `pytest tests/test_data_quality_rules.py -v` | 24/24 passed | 2.0s |
| 2 | `pytest tests/test_cross_model_validation.py -v` | 10/10 passed | 7.2s |
| 3 | `pytest tests/test_data_quality_rules.py -k "negative" -v` | 12/12 passed (negative-only) | 1.2s |
| 4 | `pytest --ignore=tests/test_jira_sync_engine.py -q` | 2654/2654 passed | 26.3s |

All 4 TTL files parse cleanly with rdflib (no syntax errors). Offline parse verification confirms correct triple counts: basic-pkm 98, zettelkasten 39, ppv 52, research 47.

## Requirements Advanced

- LINT-09 (comma-in-tags rule) — Warning fires when tags contain commas; proven by positive/negative pytest
- LINT-10 (empty body rule) — Info fires for Note/Concept/zk notes with no body; proven across basic-pkm and zettelkasten
- LINT-11 (concept no definition) — Info fires for Concept missing skos:definition; proven by pytest
- LINT-12 (titleless objects) — Warning fires for basic-pkm objects with no title; proven with dcterms:title and rdfs:label negative tests
- LINT-13 (orphan objects) — Info fires for basic-pkm objects with zero connections; proven by pytest
- LINT-14 (duplicate URL) — Info fires when same-type objects share schema:url; proven by pytest
- LINT-15 (stale project) — Info fires for PPV Project with no dcterms:modified; proven by pytest
- LINT-16 (PPV broken chain — ActionItem no project) — Warning fires; proven by pytest
- LINT-17 (PPV broken chain — Project no goal) — Warning fires; proven by pytest
- (unnumbered) Claim no rationale — Info fires for research Claim with no rationale; proven by pytest

## Requirements Validated

- None moved to validated — LINT-09 through LINT-17 are advanced but not yet validated because Docker integration testing is deferred to S04 (E2E tests)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- The plan title says "9 new SHACL-AF rules" but the actual implementation has 10 distinct NodeShapes (PPV broken chain = 2 separate shapes for ActionItemNoProject and ProjectNoGoal, plus DuplicateUrl was listed separately). This is correct — the plan's step-by-step instructions specified all 10.
- T02 refactored 4 separate per-model pyshacl test functions into a single parametrized test. This is a pure improvement not in the plan — the old code had hardcoded counts in each test function.
- T02 fixed `test_pyshacl_no_warning_for_done_or_future_tasks` in test_basic_pkm_v2.py which wasn't in the plan but was necessary because the new rules fired on its minimal synthetic data.

## Known Limitations

- Orphan object rule performance on large datasets (1000+ objects) is unmeasured — D282 defers performance monitoring to Docker integration
- Stale project rule uses "no dcterms:modified" (NOT EXISTS) rather than date arithmetic due to K001 rdflib limitation — a project modified once but not recently won't be flagged
- Cross-model rules are scoped to basic-pkm types only — if new models are added with the same IRI namespace pattern, they'll be caught; if different namespace, they won't
- 5 pre-existing failures in test_jira_sync_engine.py (ImportError: `_compute_status` not found) — unrelated to this slice

## Follow-ups

- S04 will prove all rules fire in Docker stack via E2E Playwright tests
- EXPECTED_PYSHACL counts must be updated if seed data changes in any model
- Orphan rule performance should be measured with Ideaverse-scale data (~1000 objects) during S04 Docker testing

## Files Created/Modified

- `models/basic-pkm/rules/basic-pkm.ttl` — 6 new validation NodeShapes + expanded PrefixDeclarations (rdf, rdfs, skos, foaf, schema)
- `models/zettelkasten/rules/zettelkasten.ttl` — 1 new EmptyBodyValidationShape for 4 zk note types
- `models/ppv/rules/ppv.ttl` — 3 new validation NodeShapes + expanded PrefixDeclarations (dcterms, xsd)
- `models/research/rules/research.ttl` — 1 new ClaimNoRationaleValidationShape
- `backend/tests/test_data_quality_rules.py` — new: 24 per-rule tests across 11 test classes with _run_rule_test helper
- `backend/tests/test_cross_model_validation.py` — updated EXPECTED_PYSHACL counts; refactored to parametrized test
- `backend/tests/test_basic_pkm_v2.py` — added titles + connection to synthetic Tasks to prevent new rule false positives

## Forward Intelligence

### What the next slice should know
- All 10 rules follow the identical SPARQLConstraint pattern — `sh:severity`, `sh:sparql` with `sh:SPARQLConstraint`, `sh:message`, `sh:prefixes`, `sh:select`. Adding future rules is copy-paste + modify SPARQL.
- Rules are loaded automatically by `model_shapes_loader()` from S01's pipeline fix — no new wiring needed.
- The `EXPECTED_PYSHACL` dict in `test_cross_model_validation.py` is now the authoritative source for expected warning/info counts per model. Any seed data changes require updating these counts.
- S03 (lint filter system) doesn't depend on S02 — it depends only on S01's pipeline fix. S02 just adds more lint results to filter.

### What's fragile
- `EXPECTED_PYSHACL` counts are tightly coupled to seed data — adding/removing seed objects will break `test_pyshacl_expected_counts` tests. The counts are `(warnings, infos)` per model.
- The STRSTARTS type-namespace scoping assumes `urn:sempkm:model:basic-pkm:` IRI prefix convention. If this convention changes, titleless/orphan rules will silently stop firing.

### Authoritative diagnostics
- `pytest tests/test_data_quality_rules.py -v` — each test class maps to exactly one SHACL validation shape; failure output includes full pyshacl results_text
- `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle'); print(len(g))"` — validates TTL syntax offline

### What assumptions changed
- Plan said "9 new rules" but implementation correctly has 10 NodeShapes — the PPV broken chain requirement is 2 separate shapes and DuplicateUrl was under-counted. This was already specified in the plan's step-by-step instructions.
- The stale project rule was simplified from "no recent dcterms:modified" to "no dcterms:modified at all" due to K001 rdflib date arithmetic limitation. This catches projects that were never modified but misses projects modified long ago.
