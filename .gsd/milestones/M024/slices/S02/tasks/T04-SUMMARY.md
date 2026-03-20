---
id: T04
parent: S02
milestone: M024
provides:
  - 106 unit tests for Monday.com sync engine covering SPARQL lookups, pull sync pipeline, push stub, command builders, result helpers, and error isolation
key_files:
  - backend/tests/test_monday_sync_engine.py
key_decisions:
  - Extended existing 56-test file to 106 tests by adding SPARQL edge cases, assignee resolution, all-fail/partial status, timestamp validation, MockResponse falsy-data correctness, batch boundary, and slug integration tests
patterns_established:
  - AlwaysFailGraph / FailOnSecondItem patterns for testing per-item error isolation and partial-failure status computation
  - TestMockResponseFalsyData class validates KNOWLEDGE.md Pattern #2 compliance in test infrastructure
observability_surfaces:
  - Test run command: `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v` — 106 tests
  - Error-path tests validate `failed_items` and `error_count` surfacing in sync results
duration: 20m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T04: Sync engine unit tests

**Created 106 unit tests for Monday.com sync engine covering SPARQL helpers, pull sync pipeline (create/update/skip/error paths), two-phase bulk, group→taskGroup, subitem→parentTask, assignee resolution, push stub, and result helpers**

## What Happened

Extended the existing `test_monday_sync_engine.py` (56 tests from previous session's partial work on main) to 106 tests by adding 50 new tests covering all plan requirements:

- **SPARQL lookup extras (4):** slug edge cases, multi-slug selectivity, lastSyncedAt, Task type in query
- **Command builder extras (8):** empty properties, IRI correctness, body.set format, edge.create format, empty-string description
- **Status computation extras (5):** skipped-only, large counts, one-error-is-partial, combined create+update
- **Result builder extras (4):** defaults, duration positive, status passthrough, all-counts preserved
- **Batch submission extras (3):** exact BATCH_SIZE boundary, summary in payload, returns list
- **Push sync extras (3):** is-async verification, no state interaction, no graph interaction
- **Assignee resolution (2):** person present triggers resolve, failure doesn't crash item
- **All-fail/partial status (2):** AlwaysFailGraph → "error" status, FailOnSecondItem → "partial" status
- **Empty results (2):** zero-count success, timestamp still stored
- **Timestamp format (2):** ISO format with timezone, stored result is valid JSON
- **Column mapping flow (2):** multi-field mapping, priority label mapping
- **Change detection extras (2):** full property set, None existing values
- **MockResponse falsy data (5):** empty list, zero, False preserved; None → empty dict (KNOWLEDGE.md Pattern #2)
- **Batch size constant (2):** value is 1000, positive
- **Slug integration (3):** format, determinism, uniqueness
- **Board query extras (1):** string board_id accepted

## Verification

All tests pass. Combined Monday test count (490) exceeds the 427+ target.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_monday_sync_engine.py -v` | 0 | ✅ 106 passed | 0.11s |
| 2 | `pytest tests/test_monday_column_mapping.py -v` | 0 | ✅ 107 passed | 0.08s |
| 3 | `pytest tests/test_monday_*.py -v` | 0 | ✅ 490 passed | 0.40s |
| 4 | `ast.parse(sync_engine.py)` | 0 | ✅ syntax valid | <1s |
| 5 | `ast.parse(app.py)` | 0 | ✅ syntax valid | <1s |
| 6 | `ls apps/monday-sync/services/*.py` | 0 | ✅ 6 modules | <1s |
| 7 | `ls configure_*.html` | 0 | ✅ 2 templates | <1s |
| 8 | `pytest -k "error or malformed or missing"` | 0 | ✅ 14 passed | 0.04s |
| 9 | `wc -l test_monday_sync_engine.py` | 0 | ✅ 1857 lines | <1s |

## Diagnostics

- **Run all sync engine tests:** `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v`
- **Run error-path subset:** `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v -k "Fail or error or Error"`
- **Run assignee tests:** `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v -k "Assignee"`
- **Run MockResponse tests:** `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v -k "MockResponseFalsy"`
- **conftest issue:** When running from the worktree root (not `backend/`), conftest.py imports app.config which fails on pydantic settings validation for `linear_api_key`. Run from the `backend/` directory to avoid this.
