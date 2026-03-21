---
id: S02
parent: M030
milestone: M030
---

# S02: Data Quality Rules (9 new SHACL-AF rules) — UAT

**Milestone:** M030
**Written:** 2026-03-20

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All rules are validated via offline pyshacl tests against synthetic data. Docker integration is proven by S01's pipeline fix — rules load automatically. S04 will cover Docker E2E.

## Preconditions

- Backend virtualenv available at `backend/.venv/`
- All 4 model rules files present: `models/{basic-pkm,zettelkasten,ppv,research}/rules/*.ttl`
- `test_data_quality_rules.py` and `test_cross_model_validation.py` present in `backend/tests/`

## Smoke Test

Run `cd backend && .venv/bin/pytest tests/test_data_quality_rules.py -v` — all 24 tests should pass in <3s.

## Test Cases

### 1. Comma-in-Tags Warning

1. Run `pytest tests/test_data_quality_rules.py::TestCommaInTags -v`
2. **Expected:** 2 tests pass — positive test creates a Note with tag "foo,bar" and gets sh:Warning; negative test creates a Note with separate "foo" and "bar" tags and gets no warning.

### 2. Empty Body Info (basic-pkm)

1. Run `pytest tests/test_data_quality_rules.py::TestEmptyBodyBasicPkm -v`
2. **Expected:** 2 tests pass — positive test creates a Note with no `urn:sempkm:vocab:body` and gets sh:Info; negative test creates a Note with body and gets no info.

### 3. Concept No Definition Info

1. Run `pytest tests/test_data_quality_rules.py::TestConceptNoDefinition -v`
2. **Expected:** 2 tests pass — positive test creates a Concept with no skos:definition and gets sh:Info; negative test creates a Concept with skos:definition and gets no info.

### 4. Titleless Object Warning

1. Run `pytest tests/test_data_quality_rules.py::TestTitlelessObject -v`
2. **Expected:** 3 tests pass — positive test creates a Note with no title and gets sh:Warning; negative tests create Notes with dcterms:title or rdfs:label and get no warning.

### 5. Orphan Object Info

1. Run `pytest tests/test_data_quality_rules.py::TestOrphanObject -v`
2. **Expected:** 2 tests pass — positive test creates an isolated Note (no connections to other typed resources) and gets sh:Info; negative test creates a Note connected to another object and gets no info.

### 6. Duplicate URL Info

1. Run `pytest tests/test_data_quality_rules.py::TestDuplicateUrl -v`
2. **Expected:** 2 tests pass — positive test creates two Notes of the same type sharing the same schema:url and gets sh:Info; negative test creates two Notes with different URLs and gets no info.

### 7. Empty Body Info (zettelkasten)

1. Run `pytest tests/test_data_quality_rules.py::TestEmptyBodyZettelkasten -v`
2. **Expected:** 3 tests pass — positive test creates a FleetingNote with no body and gets sh:Info; negative test creates a FleetingNote with body and gets no info; multi-type test creates all 4 zk note types without body and gets 4 infos.

### 8. Stale Project Info (PPV)

1. Run `pytest tests/test_data_quality_rules.py::TestStaleProject -v`
2. **Expected:** 2 tests pass — positive test creates a PPV Project with no dcterms:modified and gets sh:Info; negative test creates a Project with dcterms:modified and gets no info.

### 9. PPV Broken Chain — ActionItem No Project

1. Run `pytest tests/test_data_quality_rules.py::TestActionItemNoProject -v`
2. **Expected:** 2 tests pass — positive test creates an ActionItem with no Project link and gets sh:Warning; negative test creates an ActionItem linked to a Project and gets no warning.

### 10. PPV Broken Chain — Project No Goal

1. Run `pytest tests/test_data_quality_rules.py::TestProjectNoGoal -v`
2. **Expected:** 2 tests pass — positive test creates a Project with no GoalOutcome link and gets sh:Warning; negative test creates a Project linked to a GoalOutcome and gets no warning.

### 11. Claim No Rationale Info (Research)

1. Run `pytest tests/test_data_quality_rules.py::TestClaimNoRationale -v`
2. **Expected:** 2 tests pass — positive test creates a Claim with no rationale and gets sh:Info; negative test creates a Claim with rationale and gets no info.

### 12. Cross-Model Expected Counts

1. Run `pytest tests/test_cross_model_validation.py -v`
2. **Expected:** 10 tests pass — each model's seed data produces the expected (warnings, infos) count:
   - basic-pkm: 1 warning (overdue task), 6 infos (3 Notes + 3 Concepts with no body)
   - crm: 2 warnings (stale contacts), 0 infos
   - zettelkasten: 2 warnings (unprocessed notes), 10 infos (9 notes with no body + 1 existing)
   - research: 2 warnings (unsupported/contested claims), 2 infos

### 13. Full Suite Regression Check

1. Run `pytest --ignore=tests/test_jira_sync_engine.py -q`
2. **Expected:** 2654 tests pass, 0 failures. The jira import error is pre-existing and unrelated.

## Edge Cases

### Negative tests confirm rules don't over-fire

1. Run `pytest tests/test_data_quality_rules.py -k "negative" -v`
2. **Expected:** 12/12 negative tests pass — confirms valid data does NOT trigger any rules.

### TTL files parse without errors

1. For each of the 4 rules files, run: `backend/.venv/bin/python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle'); print(len(g))"`
2. **Expected:** All parse cleanly with triple counts: basic-pkm ~98, zettelkasten ~39, ppv ~52, research ~47.

### Titleless rule respects rdfs:label as alternative

1. Run `pytest tests/test_data_quality_rules.py::TestTitlelessObject::test_negative_note_with_rdfs_label_no_warning -v`
2. **Expected:** A Note with rdfs:label (but no dcterms:title) does NOT trigger the titleless warning.

## Failure Signals

- Any test in `test_data_quality_rules.py` failing indicates a rule's SPARQL is malformed or the test synthetic data is incorrect
- `test_pyshacl_expected_counts` failures indicate seed data has changed — update EXPECTED_PYSHACL counts
- rdflib parse errors on TTL files indicate syntax errors in the rules (missing prefixes, unclosed brackets, etc.)
- `test_pyshacl_no_warning_for_done_or_future_tasks` failure indicates the titleless/orphan rules are firing on minimal synthetic data that lacks titles or connections

## Requirements Proved By This UAT

- LINT-09 through LINT-17 (data quality rules) — each proven by positive test (fires on bad data) and negative test (doesn't fire on good data) via offline pyshacl

## Not Proven By This UAT

- Docker integration — rules firing in the live lint panel (deferred to S04 E2E tests)
- Performance with large datasets — orphan rule on 1000+ objects not measured
- User-visible lint panel display — rule messages, severity indicators, grouping (deferred to S04)

## Notes for Tester

- The `--ignore=tests/test_jira_sync_engine.py` flag is needed for the full suite because of a pre-existing ImportError unrelated to this slice
- Each test class name maps directly to a SHACL validation shape name (e.g., `TestCommaInTags` → `CommaInTagsValidationShape`)
- The `_run_rule_test` helper returns `(warnings, infos)` filtered by `sh:sourceShape`, so tests are isolated from other rules in the same file
- If pyshacl fails with `ReportableRuntimeError`, it usually means a SPARQL syntax error or missing prefix declaration in the TTL
