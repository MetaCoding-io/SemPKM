---
id: T02
parent: S03
milestone: M003
provides:
  - 17 unit tests for mount handler dispatch, SPARQL structure, children endpoint, and edge cases
key_files:
  - backend/tests/test_mount_explorer.py
key_decisions:
  - Test triplestore error on mount fetch as RuntimeError propagation (not caught by _handle_mount since _get_mount_definition has no try/except), matching the real behavior
patterns_established:
  - Mock-capture SPARQL pattern extended to multi-query handlers (side_effect list for sequential queries within one handler call)
  - _mount_bindings() helper to build mock SPARQL response for _get_mount_definition
observability_surfaces:
  - none (tests are verification, not runtime)
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Backend unit tests for mount handler and children endpoint

**17 unit tests across 4 test classes covering mount handler dispatch, all 5 strategy SPARQL structures, children endpoint routing, and edge cases.**

## What Happened

Created `backend/tests/test_mount_explorer.py` with 4 test classes:

1. **TestMountHandlerDispatch (4 tests)** — Verifies `mount:` prefix routes to `_handle_mount`, invalid UUID format returns 400, nonexistent mount returns 400, and existing modes (by-type, hierarchy) still route correctly.

2. **TestMountStrategySPARQL (5 tests)** — For each of the 5 strategies (flat, by-type, by-date, by-tag, by-property), mocks the triplestore and verifies the SPARQL query contains strategy-specific patterns (e.g. `DISTINCT ?typeIri` for by-type, `YEAR` for by-date, `?tagValue` for by-tag, `?groupValue`/`?groupLabel` for by-property).

3. **TestMountChildrenEndpoint (4 tests)** — Verifies by-type folder expansion passes type IRI to query, by-date year expansion returns month folders (no subfolder), by-date year+month expansion returns objects (subfolder present), and invalid mount_id returns 400.

4. **TestMountEdgeCases (4 tests)** — Verifies by-date with null date_property returns empty tree with message, by-tag `_uncategorized` folder calls uncategorized query, by-property `_uncategorized` folder calls uncategorized query, and triplestore error on mount fetch propagates correctly.

## Verification

- `cd backend && python -m pytest tests/test_mount_explorer.py -v` — **17 passed** in 0.54s
- `cd backend && python -m pytest tests/ -v --tb=short` — **171 passed**, 0 failures, no regressions

### Slice-level verification status

- ✅ `cd backend && python -m pytest tests/test_mount_explorer.py -v` — all pass
- ⬜ `cd e2e && npx playwright test tests/20-vfs-explorer/` — not yet created (T04)
- ⬜ Manual curl tests — verified in T01

## Diagnostics

Run `pytest tests/test_mount_explorer.py -v` — test names directly map to mount handler behaviors. Failure output shows which strategy, endpoint, or edge case broke.

## Deviations

Added a 4th edge case test (by-property `_uncategorized`) beyond the 3 specified in the plan, bringing total to 17 tests (vs 16 minimum from the plan's 4+5+4+3 structure). This strengthens coverage of the uncategorized path for both by-tag and by-property strategies.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_mount_explorer.py` — 17 unit tests across 4 test classes for mount explorer handler and children endpoint
