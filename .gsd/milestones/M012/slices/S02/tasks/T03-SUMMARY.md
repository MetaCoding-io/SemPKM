---
id: T03
parent: S02
milestone: M012
provides:
  - build_compensation() handles body.diff events — produces body.set compensation with old body recovered from diff
  - _reverse_apply_diff() reconstructs old body from stored unified diff
  - 34 comprehensive tests covering all body.diff code paths
  - Diff normalization fix in save_body() for correct line endings
key_files:
  - backend/app/events/query.py
  - backend/app/browser/objects.py
  - backend/tests/test_body_diff.py
key_decisions: []
patterns_established:
  - Unified diff normalization — always ensure each diff line ends with \n before storing, since difflib header lines lack trailing newlines when lineterm="" is used
  - build_compensation for body.diff reconstructs old body from context+removed lines in the diff (well-known unified diff property), then emits body.set as the compensation operation type
observability_surfaces:
  - build_compensation() for body.diff returns body.set Operation with recovered old body — visible in undo operations
  - _reverse_apply_diff() returns None on malformed diff — undo button disabled gracefully
  - Diff normalization in save_body() prevents silent undo failures from malformed stored diffs
duration: 25m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Add body.diff undo support and comprehensive unit tests

**Added body.diff undo via `_reverse_apply_diff()` and `build_compensation()`, fixed diff normalization bug in `save_body()`, and wrote 17 new tests (34 total) covering all code paths.**

## What Happened

1. **`_reverse_apply_diff()` method** added to `EventQueryService` — reconstructs the old body from a stored unified diff by keeping context lines (` ` prefix) and removed lines (`-` prefix), skipping added lines (`+` prefix). This is a well-known property of unified diffs: context + removed lines in order reconstruct the original file.

2. **`build_compensation()` body.diff case** — after the existing `body.set` handler, added a `body.diff` branch that: (a) reads the diff text and body predicate from `data_triples`, (b) gets the new body value, (c) calls `_reverse_apply_diff()` to recover the old body, (d) emits a `body.set` compensation operation that restores the old body.

3. **Diff normalization fix** in `save_body()` — discovered that `difflib.unified_diff` with `lineterm=""` produces header lines (`---`, `+++`, `@@`) without trailing `\n`, while content lines from `keepends=True` input retain `\n`. Joining without normalization concatenates headers into the first content line, breaking both `_parse_stored_diff()` and `_reverse_apply_diff()`. Fixed by normalizing each line to end with `\n` before joining.

4. **17 new tests** added to `test_body_diff.py` across 5 test classes:
   - `TestReverseApplyDiff` (6 tests): line change, addition, removal, multiple changes, empty diff, malformed input
   - `TestBuildCompensationBodyDiff` (6 tests): successful undo, no subject, missing diff, missing body, body.set still works, body.set no before value
   - `TestComputeBodyDiff` (4 tests): text change, identical, empty old, empty new
   - `TestHandlerOperationComprehensive` (1 test): full Operation shape validation

## Verification

- `python -m pytest tests/test_body_diff.py -v` — ✅ 34/34 passed
- `python -m pytest tests/ -v --tb=short -x -q` — ✅ 943 passed, 0 failures (no regressions)
- `python -c "from app.commands.dispatcher import HANDLER_REGISTRY, _register_handlers; _register_handlers(); assert 'body.diff' in HANDLER_REGISTRY; print('body.diff handler registered')"` — ✅
- `python -c "from app.commands.router import _COMMAND_EVENT_MAP; assert _COMMAND_EVENT_MAP.get('body.diff') == 'object.changed'; print('webhook mapping OK')"` — ✅

### Slice-level verification (all checks — T03 is final task):
- ✅ `handle_body_diff()` produces correct Operation with `operation_type="body.diff"`, `sempkm:bodyDiff` data triple, and correct materialize inserts/deletes
- ✅ Diff computation produces expected unified diff output for simple text changes
- ✅ `get_event_detail()` correctly parses stored diff for `body.diff` events
- ✅ `get_event_detail()` still computes diff on-the-fly for old `body.set` events (backward compat)
- ✅ `build_compensation()` for `body.diff` produces a `body.set` operation with old body restored
- ✅ `build_compensation()` for `body.set` still works (no regression)
- ✅ Handler registered in dispatcher, webhook mapping correct
- ✅ No regressions in 943-test suite

## Diagnostics

- **Test undo recovery:** `EventQueryService(client)._reverse_apply_diff(new_body, diff_text)` — returns old body string or None
- **Inspect compensation:** `await EventQueryService(client).build_compensation(event_iri, detail)` — returns Operation with `operation_type="body.set"` for body.diff events
- **Failure shape:** If stored diff is malformed or missing predicates, `build_compensation()` returns `None` (graceful degradation, undo button disabled). If `_reverse_apply_diff()` encounters an exception, it returns `None`.

## Deviations

- **Diff normalization fix** — discovered and fixed a bug in `save_body()` where `difflib.unified_diff` header lines lacked trailing `\n`, causing stored diffs to be unparseable. This was not in the original plan but was required for `_reverse_apply_diff()` to work correctly. Added `_make_normalized_diff()` test helper to match the production normalization.

## Known Issues

None.

## Files Created/Modified

- `backend/app/events/query.py` — added `_reverse_apply_diff()` method and `body.diff` case in `build_compensation()`
- `backend/app/browser/objects.py` — fixed diff normalization in `save_body()` to ensure each diff line ends with `\n`
- `backend/tests/test_body_diff.py` — added 17 new tests (34 total) with `_make_normalized_diff()` helper
- `.gsd/milestones/M012/slices/S02/tasks/T03-PLAN.md` — added Observability Impact section
- `.gsd/milestones/M012/slices/S02/S02-PLAN.md` — marked T03 done
- `.gsd/KNOWLEDGE.md` — added unified diff normalization gotcha
