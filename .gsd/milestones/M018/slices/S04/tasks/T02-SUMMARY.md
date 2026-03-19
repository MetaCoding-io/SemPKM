---
id: T02
parent: S04
milestone: M018
provides:
  - Recurrence exception→master edge linking in pull_sync via SPARQL-resolved IRIs
  - _find_event_by_external_id() SPARQL helper for Google event ID → SemPKM IRI resolution
  - 14 new tests (3 for external ID lookup, 11 for recurrence linking)
key_files:
  - apps/google-calendar/services/sync_engine.py
  - backend/tests/test_gcal_sync_engine.py
key_decisions:
  - Recurrence linking runs as a separate phase after phase 2, using the same _find_existing_event + new _find_event_by_external_id lookups
  - Edge predicate reuses bpkm:recurringEventId (same property already stored as string) for the typed edge from exception to master
  - Pull result gains recurrence_edges count field for observability
patterns_established:
  - Phase-based linking: collect linking data during event processing, resolve IRIs after all events are created/updated
observability_surfaces:
  - google_calendar.sync logger INFO for recurrence linking count
  - google_calendar.sync logger WARNING for orphan exceptions and linking errors
  - last_pull_result state key includes recurrence_edges count
duration: 25min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Recurrence exception linking in pull_sync

**Added recurrence exception→master edge linking in pull_sync: SPARQL-resolves recurringEventId to master IRI, creates edge.create commands, handles orphans and self-links gracefully**

## What Happened

Implemented the three-part recurrence linking pipeline in sync_engine.py:

1. **Tracking**: Added `recurrence_links` dict populated during the per-event processing loop. Any event with a `recurringEventId` key gets its slug→recurringEventId mapping recorded.

2. **SPARQL lookup**: Added `_find_event_by_external_id()` helper that queries for a bpkm:Event matching a specific `bpkm:externalId` value with `externalProvider = "google-calendar"`. Returns `{"iri": ...}` or None.

3. **Linking phase**: After phase 2 (body.set + attendee/organizer edges), iterates `recurrence_links`. For each exception, resolves both the exception IRI (via slug) and the master IRI (via externalId). Creates `edge.create` commands with `bpkm:recurringEventId` predicate from exception to master. Skips orphans (master not found), self-links (same IRI), and isolates per-link errors.

Extended MockGraphClient with `external_id_map` parameter to support the new SPARQL query pattern in tests.

## Verification

- `pytest backend/tests/test_gcal_sync_engine.py -v` — 71 tests pass (57 existing + 14 new)
- `pytest -x` — full suite 1655 tests pass, no regressions

New test classes:
- `TestFindEventByExternalId` (3 tests): found, not found, query correctness
- `TestRecurrenceLinking` (11 tests): exception→master linking, orphan handling, self-link skip, multiple exceptions, no-recurringEventId, correct predicate, source/target verification, error isolation, full mixed sync, result field presence, updated exception linking

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest backend/tests/test_gcal_sync_engine.py -v` | 0 | ✅ pass | 0.15s |
| 2 | `pytest -x` (full suite) | 0 | ✅ pass | 8.56s |

## Diagnostics

- **Recurrence edges created**: `last_pull_result` state key contains `recurrence_edges` integer count
- **Orphan warnings**: `google_calendar.sync` logger at WARNING when master externalId not found — includes the orphan slug and unresolved recurringEventId
- **Linking errors**: Caught per-exception and logged at WARNING — don't block the sync or appear in the error list (they're linking failures, not sync failures)

## Deviations

None.

## Known Issues

- Running tests from project root fails due to `LINEAR_API_KEY` in root `.env` being rejected by pydantic Settings (pre-existing config issue, not introduced by this task). Tests must run from `backend/` directory.

## Files Created/Modified

- `apps/google-calendar/services/sync_engine.py` — Added `_find_event_by_external_id()` helper (~22 lines), `recurrence_links` tracking in processing loop (~4 lines), recurrence linking phase after phase 2 (~45 lines), `recurrence_edges` in pull result
- `backend/tests/test_gcal_sync_engine.py` — Added `TestFindEventByExternalId` class (3 tests), `TestRecurrenceLinking` class (11 tests), extended `MockGraphClient` with `external_id_map` support
- `.gsd/milestones/M018/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
