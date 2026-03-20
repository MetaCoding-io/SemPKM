---
id: T01
parent: S03
milestone: M024
provides:
  - LoopGuard class with mark_pushed/is_echo/cleanup/len API
  - Comprehensive test suite (25 tests) covering TTL, edge cases, time mocking
key_files:
  - apps/monday-sync/services/loop_guard.py
  - backend/tests/test_monday_loop_guard.py
key_decisions: []
patterns_established:
  - "time.time() mocking via patch.object on the module's time import for deterministic TTL tests"
observability_surfaces:
  - "monday_sync.loop_guard logger — DEBUG events for mark_pushed and is_echo hits"
duration: 12m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Create LoopGuard module and dedicated test file

**Created LoopGuard in-memory TTL cache with mark_pushed/is_echo/cleanup API and 25 passing tests**

## What Happened

Created `apps/monday-sync/services/loop_guard.py` — a 65-line pure Python module implementing the `LoopGuard` class per D241. The class uses an internal `dict[str, float]` mapping `"{item_id}:{column_id}"` keys to `time.time()` timestamps. `mark_pushed()` records a push event, `is_echo()` checks if a key is within the TTL window (strict `<` comparison so boundary = expired), `cleanup()` sweeps expired entries, and `__len__()` reports active marks. A module-level logger at `monday_sync.loop_guard` emits DEBUG events for mark and echo-hit operations.

Created `backend/tests/test_monday_loop_guard.py` with 25 tests across three classes:
- **TestLoopGuardBasic** (8 tests): mark+check, independence, wildcard column, len tracking
- **TestLoopGuardTTL** (8 tests): within/beyond/boundary TTL, custom TTL, zero TTL, cleanup with selective expiry — all using `patch.object` on `time.time` for deterministic timing
- **TestLoopGuardEdgeCases** (9 tests): empty/None/numeric/large/special-char IDs, 500-item concurrent marks, cleanup on empty, re-mark after expiry, is_echo immutability

## Verification

- `cd backend && uv run python -m pytest tests/test_monday_loop_guard.py -v` — 25/25 passed
- `python3 -c "import ast; ast.parse(...)"` — valid syntax
- `grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py` — zero results
- LoopGuard smoke test (importlib load → mark → is_echo round-trip) — passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run python -m pytest tests/test_monday_loop_guard.py -v` | 0 | ✅ pass | 0.06s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py` | 1 | ✅ pass (no matches) | <1s |
| 4 | LoopGuard smoke test (mark→echo round-trip) | 0 | ✅ pass | <1s |

## Diagnostics

- **Logger:** `logging.getLogger("monday_sync.loop_guard")` — set to DEBUG to see mark/echo events
- **Runtime inspection:** `len(guard)` for active mark count; `guard.cleanup()` returns expired count
- **Internal state:** `guard._marks` dict is accessible for debugging (not part of public API)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/monday-sync/services/loop_guard.py` — NEW: LoopGuard class with TTL-based echo prevention
- `backend/tests/test_monday_loop_guard.py` — NEW: 25 tests covering basic, TTL, and edge-case behavior
- `.gsd/milestones/M024/slices/S03/S03-PLAN.md` — Added diagnostic verification step (pre-flight fix)
- `.gsd/milestones/M024/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
