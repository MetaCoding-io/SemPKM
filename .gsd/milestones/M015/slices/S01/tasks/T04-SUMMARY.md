---
id: T04
parent: S01
milestone: M015
provides:
  - 23 Node.js unit tests covering rankResults, groupByType, and LRUCache from context-utils.js
key_files:
  - extension/tests/test-context-utils.js
key_decisions: []
patterns_established:
  - "node:test + node:assert with globalThis.SemPKMContextUtils import pattern for testing dual-export modules"
observability_surfaces:
  - "node --test extension/tests/test-context-utils.js — CI-runnable test suite with named pass/fail per function"
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T04: Add Node.js unit tests for ranking, grouping, and LRU cache

**Added 23 unit tests for context-utils.js pure functions — rankResults (8), groupByType (7), LRUCache (8) — all passing via node:test with zero external dependencies**

## What Happened

Created `extension/tests/test-context-utils.js` using Node.js built-in `node:test` and `node:assert`. The module loads via `require('../shared/context-utils.js')` which sets `globalThis.SemPKMContextUtils`, then destructures the three exports.

Tests cover all plan-specified cases plus extras:
- **rankResults (8 tests):** url > title > keyword ordering, stable sort within same match_type, truncation to 10, empty input, input immutability, unknown match_type as lowest priority
- **groupByType (7 tests):** grouping by type_label, null and undefined type_label → "Other", first-seen order preservation, group structure (typeLabel/typeIri/results), typeIri from first result in group, empty input
- **LRUCache (8 tests):** basic set/get, missing key → undefined, has() behavior, max size eviction, get() promotion preventing eviction, clear(), update in place, size tracking

## Verification

All 23 tests pass with `node --test`:
- 3 suites, 23 pass, 0 fail, 0 skipped
- Duration: ~63ms
- Slice-level syntax checks all pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --test extension/tests/test-context-utils.js` | 0 | ✅ pass | 63ms |
| 2 | `node --check extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 3 | `node --check extension/shared/context-utils.js` | 0 | ✅ pass | <1s |
| 4 | `node --check extension/shared/api-client.js` | 0 | ✅ pass | <1s |

Sideload verification is manual and not executed in this task (T03 covered it).

## Diagnostics

- Run `node --test extension/tests/test-context-utils.js` to see all test results
- Run `node --test --test-reporter spec extension/tests/test-context-utils.js` for verbose per-test output
- Any regression in the three exported functions surfaces as a named test failure with expected vs actual assertion details

## Deviations

None. Plan called for ≥17 tests; delivered 23.

## Known Issues

None.

## Files Created/Modified

- `extension/tests/test-context-utils.js` — 23 unit tests for rankResults, groupByType, and LRUCache
- `.gsd/milestones/M015/slices/S01/tasks/T04-PLAN.md` — added Observability Impact section (pre-flight fix)
