---
id: T04
parent: S01
milestone: M034
provides:
  - Comprehensive unit tests for all S01 backend features: 23 tests covering date detection, merged calendar query, and PATCH endpoint
  - Handler-level PATCH tests that call calendar_patch() directly with mocked dependencies, verifying predicate selection per type
  - Failure-path tests matching slice verification filter (invalid_iri, unsupported_type, no_dates)
  - Event type regression test confirming schema:startDate/endDate detection unaffected by scheduling property additions
key_files:
  - backend/tests/test_calendar_editable.py
key_decisions:
  - Patched inline imports via source module path (app.commands.dispatcher.dispatch, app.events.store.EventStore) rather than router module — inline from-imports create local bindings that resolve from the source module at call time
patterns_established:
  - Handler-level testing pattern for FastAPI endpoints with heavy Depends() injection — call the handler directly with mocked positional args, avoiding the full DI/TestClient setup; useful when testing business logic without needing the HTTP layer
observability_surfaces:
  - Test names align with slice verification -k filter for CI: "invalid_iri or unsupported_type or no_dates" matches exactly 3 failure-path tests
duration: 18m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T04: Unit tests for merged calendar query, PATCH endpoint, and date field detection with scheduling properties

**Extend test_calendar_editable.py from 13 to 23 tests covering handler-level PATCH dispatch, Event/Task predicate selection, merged query edge cases, and failure paths**

## What Happened

The existing test file (created in T02 with 13 tests) covered models, predicate maps, and service-level behavior but lacked handler-level PATCH endpoint tests and several edge cases from the T04 plan. Extended it with 10 new tests:

**Date detection (1 new → 5 total):**
- `test_event_type_unaffected` — Event with schema:startDate/endDate still detected correctly after scheduling property additions (regression guard)

**Merged calendar query (2 new → 7 total):**
- `test_events_only_when_no_tasks` — Only Event type has date fields → merged returns only event results
- `test_tasks_only_when_no_events` — Only Task type has date fields → merged returns only task results

**PATCH endpoint (7 new → 11 total):**
- `test_patch_invalid_iri_returns_400` — Calls handler directly, asserts 400 + "Invalid IRI"
- `test_patch_no_dates_returns_400` — Neither start nor end → 400 + "start or end"
- `test_patch_unsupported_type_returns_400` — Note type (not in predicate map) → 400 + "not supported"
- `test_patch_valid_task_dispatches_correct_predicates` — Task PATCH dispatches object.patch with bpkm:scheduledStart/scheduledEnd
- `test_patch_preserves_event_dates` — Event PATCH uses schema:startDate/endDate, NOT Task predicates
- `test_patch_start_only_omits_end` — Start-only PATCH omits end predicate from properties dict
- `test_patch_dispatch_failure_returns_500` — Dispatch exception → 500 + "Patch failed"

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v` — 23/23 pass
- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py tests/test_calendar_editable.py -v` — 45/45 pass (no regression)
- `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v -k "invalid_iri or unsupported_type or no_dates"` — 3/3 failure-path tests pass
- Shapes integrity check: 3 scheduling properties on TaskShape — passes

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v` | 0 | ✅ pass | 0.6s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py tests/test_calendar_editable.py -v` | 0 | ✅ pass | 0.6s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v -k "invalid_iri or unsupported_type or no_dates"` | 0 | ✅ pass | 0.5s |
| 4 | Shapes integrity check (3 scheduling props on TaskShape) | 0 | ✅ pass | <1s |

## Diagnostics

- Run `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v` for full test output
- Use `-k` filters to target specific areas: `"scheduledstart"` for date detection, `"merged"` for merged query, `"patch"` for PATCH endpoint
- Handler-level PATCH tests verify dispatched command properties via `mock_dispatch.call_args[0][0].params.properties` — inspect this dict to see exactly which predicates and values were dispatched

## Deviations

- Patched `app.commands.dispatcher.dispatch` and `app.events.store.EventStore` instead of `app.views.router.dispatch` — the latter doesn't exist at module level because these are inline imports inside the handler function body. This is a necessary adaptation, not a plan deviation.

## Known Issues

- None

## Files Created/Modified

- `backend/tests/test_calendar_editable.py` — Extended from 13 to 23 tests: added Event regression test, events-only/tasks-only merged query tests, and 7 handler-level PATCH endpoint tests with full predicate verification
