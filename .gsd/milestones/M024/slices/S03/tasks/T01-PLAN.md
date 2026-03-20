---
estimated_steps: 5
estimated_files: 2
---

# T01: Create LoopGuard module and dedicated test file

**Slice:** S03 — Push sync + LoopGuard + dependency edges
**Milestone:** M024

## Description

Create the `LoopGuard` module (per D241) — a lightweight in-memory TTL cache that prevents push→poll echo loops. When push sync updates a Monday.com item, it marks the item in LoopGuard. When pull sync encounters that item shortly after, LoopGuard's `is_echo()` returns True and the item is skipped.

This is a pure Python module with zero external dependencies — the simplest deliverable in S03, and it must exist before T03 can wire it into push/pull sync.

**Relevant skills:** `test` skill for test generation patterns.

## Steps

1. **Create `apps/monday-sync/services/loop_guard.py`** (~40-50 lines):
   - Class `LoopGuard` with `__init__(self, ttl_seconds: float = 30.0)`
   - Internal storage: `self._marks: dict[str, float] = {}` mapping `"{item_id}:{column_id}"` → `time.time()` timestamp
   - `mark_pushed(self, item_id: str, column_id: str = "*") -> None` — store current time for the key
   - `is_echo(self, item_id: str, column_id: str = "*") -> bool` — return True if key exists and age < TTL
   - `cleanup(self) -> int` — remove all expired entries, return count removed
   - `__len__(self) -> int` — return number of active marks
   - Add a module-level logger: `logger = logging.getLogger("monday_sync.loop_guard")`
   - Log at DEBUG level for mark and echo-hit events

2. **Validate syntax**: `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read())"`

3. **Create `backend/tests/test_monday_loop_guard.py`** with 25+ tests using importlib loading pattern (same pattern as other Monday test files):
   - Load loop_guard module via importlib from `apps/monday-sync/services/loop_guard.py`
   - **TestLoopGuardBasic** (~8 tests):
     - `test_mark_and_check` — mark an item, `is_echo` returns True
     - `test_unmarked_item_not_echo` — `is_echo` returns False for unknown items
     - `test_mark_overwrites_timestamp` — marking same key twice updates time
     - `test_different_items_independent` — marking item A doesn't affect item B
     - `test_wildcard_column_id` — default `column_id="*"` works
     - `test_specific_column_ids` — different column_ids for same item are independent
     - `test_len_reflects_mark_count` — `__len__` returns correct count
     - `test_initial_state_empty` — new LoopGuard has len 0 and no echoes
   - **TestLoopGuardTTL** (~8 tests, using `monkeypatch` or `unittest.mock.patch` on `time.time`):
     - `test_echo_within_ttl` — mark at t=0, check at t=10 with ttl=30 → True
     - `test_echo_expired_beyond_ttl` — mark at t=0, check at t=31 with ttl=30 → False
     - `test_echo_at_exact_boundary` — mark at t=0, check at t=30 with ttl=30 → False (expired at boundary)
     - `test_custom_ttl` — LoopGuard(ttl_seconds=5) expires after 5s
     - `test_zero_ttl_always_expired` — LoopGuard(ttl_seconds=0) → `is_echo` always False
     - `test_cleanup_removes_expired` — mark items, advance time past TTL, cleanup removes them
     - `test_cleanup_preserves_fresh` — mark items, advance time partially, cleanup only removes expired
     - `test_cleanup_returns_count` — cleanup return value matches number removed
   - **TestLoopGuardEdgeCases** (~9 tests):
     - `test_empty_item_id` — mark/check with empty string works without error
     - `test_none_item_id_coerced` — if someone passes None, mark/check handles gracefully (str coercion or skip)
     - `test_numeric_item_id_as_string` — item_id "12345" works
     - `test_large_item_id` — very long item_id string works
     - `test_special_characters_in_id` — item_id with colons/slashes works
     - `test_concurrent_marks_different_items` — marking many items rapidly works
     - `test_cleanup_on_empty_guard` — cleanup on empty guard returns 0, no error
     - `test_mark_after_expiry_refreshes` — mark expired item → becomes echo again
     - `test_is_echo_does_not_mutate` — calling is_echo doesn't change marks dict

4. **Run tests**: `cd backend && uv run python -m pytest tests/test_monday_loop_guard.py -v`

5. **Verify syntax of both files** and confirm all tests pass.

## Must-Haves

- [ ] `LoopGuard` class with `mark_pushed()`, `is_echo()`, `cleanup()`, `__len__()`
- [ ] Configurable TTL (default 30 seconds)
- [ ] In-memory `dict[str, float]` storage with `"{item_id}:{column_id}"` keys
- [ ] 25+ tests passing in `test_monday_loop_guard.py`
- [ ] TTL expiry tested via time mocking (not real sleeps)
- [ ] Edge cases (empty/None IDs, cleanup on empty) handled gracefully

## Verification

- `cd backend && uv run python -m pytest tests/test_monday_loop_guard.py -v` — 25+ tests pass
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read())"` — valid syntax

## Inputs

- D241 decision: LoopGuard as standalone `loop_guard.py` with `(item_id, column_id) → timestamp` TTL cache
- Importlib loading pattern from existing Monday.com test files (e.g., `test_monday_sync_engine.py` lines 22-50)
- The `_SERVICES_DIR` path resolution pattern: `Path(__file__).resolve().parent.parent.parent / "apps" / "monday-sync" / "services"`

## Expected Output

- `apps/monday-sync/services/loop_guard.py` — NEW: ~40-50 lines, pure Python LoopGuard class
- `backend/tests/test_monday_loop_guard.py` — NEW: ~200 lines, 25+ tests with time mocking

## Observability Impact

- **New logger:** `monday_sync.loop_guard` — DEBUG-level events for `mark_pushed()` calls (key, timestamp) and `is_echo()` hits (key, age, ttl). Enables tracing echo-prevention decisions without modifying calling code.
- **Inspection:** `len(loop_guard_instance)` returns active mark count; `cleanup()` return value shows expired entries removed. Both are usable from diagnostic code or REPL.
- **Failure visibility:** No exceptions raised for edge-case inputs (empty/None IDs) — graceful str coercion. Unexpected types will produce a logged warning rather than a crash.
