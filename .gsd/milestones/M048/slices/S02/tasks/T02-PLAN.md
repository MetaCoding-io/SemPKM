---
estimated_steps: 23
estimated_files: 2
skills_used: []
---

# T02: Add unit tests for save diff logic

## Why
The diff logic in `save_object()` handles datetime normalization, multi-value comparison, and no-op detection. Unit tests ensure these edge cases are covered and prevent regressions.

## Steps

1. **Create `backend/tests/test_save_diff.py`** with tests for the `_normalize_value_for_compare()` helper:
   - Full ISO datetime with timezone `2026-04-05T12:30:45.123456+00:00` → `2026-04-05T12:30`
   - Datetime with Z suffix `2026-04-05T12:30:45Z` → `2026-04-05T12:30`
   - Datetime-local format (already truncated) `2026-04-05T12:30` → `2026-04-05T12:30`
   - Plain date `2026-04-05` → `2026-04-05` (pass-through)
   - Non-datetime string `hello world` → `hello world` (pass-through)
   - URI string `http://example.org/thing` → `http://example.org/thing` (pass-through)
   - Empty string → empty string

2. **Add integration-style tests** that exercise the diff filtering logic (can test inline or via extracted helper):
   - Unchanged properties → empty changed dict
   - One property changed → only that property in changed dict
   - DateTime property unchanged (different format) → not in changed dict
   - Multi-valued property with same values in different order → not in changed dict
   - New property (in form but not in current) → in changed dict
   - `dcterms:modified` only present when other changes exist

3. **Follow the existing test pattern** from `test_object_create_timestamps.py` — use pytest with async tests, import from `app.browser.objects` or test the helper directly.

## Key Constraints
- Tests must be runnable with `cd backend && python -m pytest tests/test_save_diff.py -v`
- The `_normalize_value_for_compare` function should be importable from `app.browser.objects`
- If the diff filtering logic is inline in `save_object()`, extract the comparison into a testable helper function (e.g., `_compute_changed_properties(form_props, current_props)`) that T02 can import and test directly.

## Inputs

- ``backend/app/browser/objects.py` — _normalize_value_for_compare() and diff logic from T01`
- ``backend/tests/test_object_create_timestamps.py` — reference test pattern`

## Expected Output

- ``backend/tests/test_save_diff.py` — unit tests for normalization and diff filtering`
- ``backend/app/browser/objects.py` — possible extraction of _compute_changed_properties() helper if diff logic was inline`

## Verification

cd backend && python -m pytest tests/test_save_diff.py -v
