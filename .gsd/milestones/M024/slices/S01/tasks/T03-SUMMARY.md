---
id: T03
parent: S01
milestone: M024
provides:
  - Configurable field mapper with 9 column-type extractors, build_task_properties, build_reverse_column_values, compute_slug
key_files:
  - apps/monday-sync/services/field_mapper.py
  - backend/tests/test_monday_field_mapper.py
key_decisions:
  - build_task_properties returns tuple (props, assignee_user_id) so caller can resolve person asynchronously
  - Priority uses a separate _extract_priority function (returns None for unknown) vs status _extract_status (defaults to "todo") since missing priority should be omitted while status needs a default
patterns_established:
  - Column value extraction pattern: _parse_col_value handles JSON string / dict / None normalization, then type-specific extractors handle the parsed shape
  - Configurable column mapping: build_task_properties accepts column_mapping dict keyed by bpkm property short names ("taskStatus", "dueDate") mapped to Monday.com column IDs
observability_surfaces:
  - none — pure functions, no runtime signals
duration: 18m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Configurable field mapper with per-column-type transforms and reverse mapping

**Built Monday.com field mapper with 9 column-type extractors, configurable status/priority label mappings, reverse column serializers for push sync, and 155 passing unit tests.**

## What Happened

Implemented `apps/monday-sync/services/field_mapper.py` following the Jira field mapper pattern but with Monday.com-specific adaptations for user-configurable columns. The key difference from Jira is that Monday.com columns are fully customizable, so the mapper accepts a `column_mapping` dict parameter instead of hardcoded field positions.

Built 9 column value extractors: status, priority, date, people, text, long_text, numbers, tags, dropdown — each handling JSON string, pre-parsed dict, None, empty, and malformed input gracefully. The `_parse_col_value` helper normalizes the three input shapes (JSON string, dict, None) before type-specific extraction.

`build_task_properties` returns a `(props, assignee_user_id)` tuple — the raw Monday.com person ID is separated from the properties dict so the sync engine can resolve it to a Person IRI via PersonMatcher asynchronously.

`build_reverse_column_values` handles the format asymmetry: Monday.com reads status as `{"label": "Working on it", "index": 1}` but writes as `{"label": "Done"}`. Each column type has a dedicated serializer producing the correct mutation format.

## Verification

- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"` — no syntax errors
- 155 field mapper tests pass covering all 9 extractors, build_task_properties, build_reverse_column_values, compute_slug, round-trip consistency, and edge cases
- 250 tests pass across all 3 existing test files combined (31 auth + 64 client + 155 field mapper)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | 0.1s |
| 2 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_field_mapper.py -v` | 0 | ✅ pass (155 tests) | 0.2s |
| 3 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py -v` | 0 | ✅ pass (31 tests) | 0.04s |
| 4 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_client.py -v` | 0 | ✅ pass (64 tests) | 0.06s |
| 5 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py tests/test_monday_client.py tests/test_monday_field_mapper.py -v` | 0 | ✅ pass (250 tests) | 0.2s |

## Diagnostics

- **Pure functions, no runtime signals.** Feed a Monday.com item dict to `build_task_properties()` in a REPL to inspect the exact bpkm property mapping. Feed bpkm properties to `build_reverse_column_values()` to see the mutation JSON.
- **Failure behavior:** Malformed column values silently produce None/empty defaults. Column mapping misses (column ID not in item) are skipped, not raised.
- **Test runner:** `cd backend && .venv/bin/python3 -m pytest tests/test_monday_field_mapper.py -v`

## Deviations

- Plan listed 8 column type extractors; implemented 9 (added `_extract_priority` as separate from `_extract_status` since priority returns None for unknown labels while status defaults to "todo").
- Plan suggested `_assignee_user_id` as a key in the props dict; used tuple return `(props, assignee_user_id)` instead — cleaner separation, avoids polluting the bpkm properties dict with internal metadata.
- Plan noted `DEFAULT_PRIORITY_MAP` key `""` with right-double-quotation-mark; used empty string `""` mapping to `"low"` as the actual fallback (matched the Jira pattern).

## Known Issues

None.

## Files Created/Modified

- `apps/monday-sync/services/field_mapper.py` — configurable field mapper with 9 extractors, build/reverse functions, compute_slug (~340 lines)
- `backend/tests/test_monday_field_mapper.py` — 155 unit tests covering all extractors, builders, round-trips, and edge cases (~570 lines)
- `.gsd/milestones/M024/slices/S01/tasks/T03-PLAN.md` — added missing Observability Impact section (pre-flight fix)
