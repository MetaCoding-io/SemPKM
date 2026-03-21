---
id: T02
parent: S02
milestone: M030
provides:
  - 24 per-rule tests (11 positive + 12 negative + 1 multi-type) for 10 SHACL-AF data quality rules
  - Updated EXPECTED_PYSHACL counts in test_cross_model_validation.py
  - Fixed test_basic_pkm_v2.py to add titles and connections to synthetic Task data
key_files:
  - backend/tests/test_data_quality_rules.py
  - backend/tests/test_cross_model_validation.py
  - backend/tests/test_basic_pkm_v2.py
key_decisions:
  - Used sh:sourceShape filtering in test helper to isolate individual rule results and avoid false positives from other rules in the same rules file
  - Refactored 4 hardcoded per-model pyshacl tests into a single parametrized test_pyshacl_expected_counts using EXPECTED_PYSHACL dict
patterns_established:
  - Per-rule test pattern using _run_rule_test helper with source_shape filtering
  - Test class per SHACL validation shape with positive/negative test methods
observability_surfaces:
  - pytest tests/test_data_quality_rules.py -v shows individual rule pass/fail
  - Each test failure includes full pyshacl results_text for diagnosis
duration: 18m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Write per-rule tests and update cross-model expected counts

**Added 24 per-rule tests for 10 SHACL-AF data quality rules and updated cross-model expected pyshacl counts**

## What Happened

Created `test_data_quality_rules.py` with 11 test classes (one per rule) containing 24 tests total:
- 11 positive tests proving each rule fires on synthetic data with quality issues
- 12 negative tests proving rules don't fire on valid data (titleless rule gets 2 negatives — dcterms:title and rdfs:label)
- 1 bonus multi-type test proving all 4 zettelkasten note types fire the empty-body rule

Each test uses a minimal rdflib Graph with synthetic data, loads only the relevant rules TTL file, runs pyshacl with `advanced=True, allow_infos=True, allow_warnings=True`, and asserts the correct count of warnings/infos from the specific `sh:sourceShape` being tested.

Updated `EXPECTED_PYSHACL` counts by running pyshacl against each model's seed data:
- **basic-pkm**: (1, 0) → (1, 6) — 6 new EmptyBody infos (3 Notes + 3 Concepts with no body)
- **zettelkasten**: (2, 1) → (2, 10) — 9 new EmptyBody infos (9 note-type objects with no body)
- **crm**: unchanged (2, 0) — no new rules target CRM types
- **research**: unchanged (2, 2) — all 5 seed Claims have rationale

Also refactored the 4 separate per-model pyshacl test functions into a single parametrized `test_pyshacl_expected_counts[model_name]` that reads from the `EXPECTED_PYSHACL` dict.

Fixed the existing `test_pyshacl_no_warning_for_done_or_future_tasks` in test_basic_pkm_v2.py which now failed because the new TitlelessObject and OrphanObject rules fired on the synthetic Task objects (which lacked titles and connections). Added dcterms:title to both tasks and a connecting edge between them.

## Verification

- `pytest tests/test_data_quality_rules.py -v` — 24/24 tests pass
- `pytest tests/test_cross_model_validation.py -v` — 10/10 tests pass with updated counts
- `pytest tests/test_data_quality_rules.py -k "negative" -v` — 12/12 negative tests pass
- `pytest --ignore=tests/test_jira_sync_engine.py -q` — 2654 passed, 0 failed (jira tests excluded, pre-existing import error)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_data_quality_rules.py -v` | 0 | ✅ pass | 2.0s |
| 2 | `pytest tests/test_cross_model_validation.py -v` | 0 | ✅ pass | 7.2s |
| 3 | `pytest tests/test_data_quality_rules.py -k "negative" -v` | 0 | ✅ pass | 1.2s |
| 4 | `pytest --ignore=tests/test_jira_sync_engine.py -q` (full suite) | 0 | ✅ pass | 26.3s |

## Diagnostics

- `pytest tests/test_data_quality_rules.py -v` — shows per-rule pass/fail status, test class names map to SHACL validation shapes
- On test failure: full pyshacl results_text is printed showing all violations, their severity, source shape URI, and focus node
- `EXPECTED_PYSHACL` dict serves as a living document of expected validation counts per model — if seed data changes, update these counts

## Deviations

- Refactored 4 separate per-model pyshacl test functions in `test_cross_model_validation.py` into a single parametrized test to reduce code duplication and make the EXPECTED_PYSHACL dict authoritative. This is a pure improvement over the plan which said "update EXPECTED_PYSHACL dict" — the old code had hardcoded counts in each test function and didn't reference the dict.
- Fixed existing `test_pyshacl_no_warning_for_done_or_future_tasks` in test_basic_pkm_v2.py — the new titleless/orphan rules fired on its minimal synthetic Tasks. Added titles and a connecting edge to prevent false positives.

## Known Issues

- 5 pre-existing failures in `test_jira_sync_engine.py` (ImportError: `_compute_status` not found) — unrelated to this task.

## Files Created/Modified

- `backend/tests/test_data_quality_rules.py` — new: 24 per-rule tests across 11 test classes with shared _run_rule_test helper
- `backend/tests/test_cross_model_validation.py` — updated EXPECTED_PYSHACL counts; refactored 4 per-model tests into 1 parametrized test
- `backend/tests/test_basic_pkm_v2.py` — added titles + connection to synthetic Task data to avoid new rule false positives
