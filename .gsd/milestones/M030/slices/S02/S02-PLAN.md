# S02: Data Quality Rules (9 new SHACL-AF rules)

**Goal:** Add 9 new SHACL-AF SPARQLConstraint validation rules across 4 Mental Model rules files, each proven by isolated pytest tests against synthetic data.
**Demo:** User creates objects with data quality issues (comma-in-tags, empty body, titleless objects, orphan objects, etc.) and sees appropriate warnings/infos in the lint panel. All 9 rules proven by offline pytest tests.

## Must-Haves

- 5 new validation NodeShapes in `basic-pkm/rules/basic-pkm.ttl`: comma-in-tags (Warning), empty body for Note/Concept (Info), concept with no definition (Info), titleless objects (Warning), orphan objects (Info)
- 1 new validation NodeShape in `zettelkasten/rules/zettelkasten.ttl`: empty body for 4 zk note types (Info)
- 2 new validation NodeShapes in `ppv/rules/ppv.ttl`: stale project (Info), PPV broken chain — ActionItem without project + Project without goalOutcome (Warning)
- 1 new validation NodeShape in `research/rules/research.ttl`: claim with no rationale (Info)
- Duplicate URL rule in `basic-pkm/rules/basic-pkm.ttl` (Info) — detects two objects of the same type sharing a `schema:url`
- PrefixDeclarations updated in basic-pkm.ttl and ppv.ttl with the additional prefixes needed by new rules
- `test_data_quality_rules.py` with per-rule positive (fires) and negative (doesn't fire) tests using minimal synthetic data graphs
- `test_cross_model_validation.py` EXPECTED_PYSHACL counts updated to reflect new rules firing against existing seed data
- All existing tests continue to pass

## Proof Level

- This slice proves: contract (offline pyshacl tests prove each rule fires correctly)
- Real runtime required: no (offline pyshacl validation sufficient; Docker integration proven by S01 pipeline fix)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/pytest tests/test_data_quality_rules.py -v` — all per-rule tests pass (≥18 tests: 9 positive + 9 negative)
- `cd backend && .venv/bin/pytest tests/test_cross_model_validation.py -v` — all cross-model tests pass with updated expected counts
- `cd backend && .venv/bin/pytest` — full test suite passes (no regressions)
- `cd backend && .venv/bin/pytest tests/test_data_quality_rules.py -k "negative" -v` — negative tests confirm rules do NOT fire on valid data (failure-path verification)

## Integration Closure

- Upstream surfaces consumed: S01's pipeline fix ensures `advanced=True` is passed to pyshacl and rules graphs are loaded alongside shapes
- New wiring introduced in this slice: none — rules are loaded automatically by `model_shapes_loader()` from S01
- What remains before the milestone is truly usable end-to-end: S03 (lint filter system), S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Write 9 SHACL-AF validation rules across 4 model rules files** `est:1h30m`
  - Why: The core deliverable — all 9 data quality rules following the established SPARQLConstraint pattern proven by the 11 existing M011 rules.
  - Files: `models/basic-pkm/rules/basic-pkm.ttl`, `models/zettelkasten/rules/zettelkasten.ttl`, `models/ppv/rules/ppv.ttl`, `models/research/rules/research.ttl`
  - Do: Add validation NodeShapes following D153 (each on its own NodeShape, separate from inference rules). Add missing sh:declare entries to PrefixDeclarations. Use full IRIs in SPARQL when prefix not available. Follow K001 pattern for date comparison (STRDT+SUBSTR). For stale project, use approximate "1st of this month" threshold. For orphan objects, check no edges to/from other typed resources in either direction (excluding rdf:type). For duplicate URL, target `sh:targetSubjectsOf schema:url`.
  - Verify: Each .ttl file parses with `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle'); print(len(g))"`
  - Done when: All 4 .ttl files parse cleanly with rdflib, contain the expected new NodeShapes, and follow existing naming conventions.

- [x] **T02: Write per-rule tests and update cross-model expected counts** `est:1h30m`
  - Why: Each rule needs isolated positive/negative tests with synthetic data, and the existing cross-model validation test expected counts must be updated to reflect new rules firing against seed data.
  - Files: `backend/tests/test_data_quality_rules.py` (new), `backend/tests/test_cross_model_validation.py` (update EXPECTED_PYSHACL)
  - Do: Write test_data_quality_rules.py following the `test_pyshacl_no_warning_for_done_or_future_tasks` pattern: create minimal rdflib Graph, load rules, run pyshacl with advanced=True + allow_infos=True + allow_warnings=True, assert correct severity fires (positive test) and doesn't fire (negative test). Update EXPECTED_PYSHACL dict — key impact: basic-pkm gains ~6 infos (empty body on 3 Notes + 3 Concepts), zettelkasten gains ~9 infos (empty body on all note types). Run the full test suite.
  - Verify: `cd backend && .venv/bin/pytest tests/test_data_quality_rules.py tests/test_cross_model_validation.py -v` — all pass
  - Done when: ≥18 new tests in test_data_quality_rules.py (positive + negative per rule), updated EXPECTED_PYSHACL counts match actual seed data, full `pytest` passes with zero failures.

## Observability / Diagnostics

- **Runtime signals:** Each validation rule fires a SHACL violation with `sh:severity` (Warning or Info) and `sh:message` containing the specific data quality issue. These violations are surfaced in the lint panel via the existing pyshacl pipeline from S01.
- **Inspection surface:** `GET /api/objects/{id}/lint` returns the full validation report including these new rules. The lint panel groups violations by severity. Each violation includes the sh:message and the source constraint URI.
- **Failure visibility:** If a rule's SPARQL is malformed or a PrefixDeclaration is missing, pyshacl raises a `ReportableRuntimeError` during validation — this surfaces as a 500 error on the lint endpoint with a traceback in Docker logs (`docker compose logs backend`). rdflib parse errors at model load time are caught by `model_shapes_loader()` and logged with the model name.
- **Diagnostic command:** `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle'); print(len(g))"` validates any rules file offline.
- **Redaction:** No sensitive data involved — all validation operates on user-created RDF triples with no PII constraints beyond what the user entered.

## Files Likely Touched

- `models/basic-pkm/rules/basic-pkm.ttl`
- `models/zettelkasten/rules/zettelkasten.ttl`
- `models/ppv/rules/ppv.ttl`
- `models/research/rules/research.ttl`
- `backend/tests/test_data_quality_rules.py` (new)
- `backend/tests/test_cross_model_validation.py`
