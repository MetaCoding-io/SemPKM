# S03: Push Sync + Bidirectional Write — UAT

**Milestone:** M021
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Push sync is contract-proven via 36 unit tests with mocks. Runtime proof deferred to S04 E2E test with mock CalDAV server.

## Preconditions

- Working directory: `backend/` within M018 worktree
- `uv` available for running pytest
- All CalDAV app source files in `apps/caldav-calendar/services/`

## Smoke Test

Run `cd backend && uv run python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -x` — 149 tests pass in <1s.

## Test Cases

### 1. Reverse field mapper returns correct PARTSTAT for all mapped statuses

1. Run `uv run python -m pytest tests/test_caldav_field_mapper.py -v -k "BuildEventPatch"`
2. **Expected:** 8 tests pass — accepted→ACCEPTED, declined→DECLINED, tentative→TENTATIVE, needsAction→NEEDS-ACTION, plus empty/unmapped/no-email/empty-email edge cases all return `{}`

### 2. modify_vevent_partstat correctly modifies .ics ATTENDEE

1. Run `uv run python -m pytest tests/test_caldav_field_mapper.py -v -k "ModifyVevent"`
2. **Expected:** 7 tests pass — single attendee modified, correct attendee selected from multiple, email not found returns original, case-insensitive matching works, round-trip consistency with extract_attendees, parameter preservation (CN, ROLE, RSVP kept intact)

### 3. Push sync pipeline orchestrates GET→modify→PUT cycle

1. Run `uv run python -m pytest tests/test_caldav_sync_engine.py -v -k "test_successful_rsvp_push"`
2. **Expected:** Test passes — asserts GET called with externalUrl, PUT called with modified .ics and ETag, lastSyncedAt updated

### 4. Push sync stores last_push_result in state

1. Run `uv run python -m pytest tests/test_caldav_sync_engine.py -v -k "test_last_push_result_stored"`
2. **Expected:** Test passes — state contains `last_push_result` with status/pushed/skipped/errors/timestamp fields

### 5. ETag conflict (412) recorded as error, not crash

1. Run `uv run python -m pytest tests/test_caldav_sync_engine.py -v -k "test_etag_conflict_412"`
2. **Expected:** Test passes — CalDAVConflictError caught, error message contains "ETag conflict (412)", push result status reflects the error

### 6. Per-event error isolation (one failure doesn't block others)

1. Run `uv run python -m pytest tests/test_caldav_sync_engine.py -v -k "test_error_isolation or test_etag_conflict_does_not_block"`
2. **Expected:** 2 tests pass — first event fails but second event still processed and pushed successfully

### 7. Direction and auth guards skip gracefully

1. Run `uv run python -m pytest tests/test_caldav_sync_engine.py -v -k "test_not_connected_skips or test_pull_only_skips"`
2. **Expected:** 2 tests pass — not connected → skipped result stored, pull-only direction → skipped result stored

### 8. Zero stubs remain in production code

1. Run `rg "not yet implemented|stub|S03" apps/caldav-calendar/services/sync_engine.py apps/caldav-calendar/services/field_mapper.py`
2. **Expected:** Zero matches (exit code 1)

### 9. Total test count meets target

1. Run `cd backend && uv run python -m pytest tests/test_caldav_*.py --co -q`
2. **Expected:** 229+ tests collected across all CalDAV test files (auth, client, field_mapper, sync_engine, person_matcher)

### 10. Failure-path tests exist and pass

1. Run `uv run python -m pytest tests/test_caldav_field_mapper.py tests/test_caldav_sync_engine.py -v -k "error or conflict or fail or empty" --no-header`
2. **Expected:** 17 tests pass — covers empty inputs, unmapped values, malformed data, ETag conflicts, error isolation, missing fields

## Edge Cases

### Missing externalUrl on changed event

1. Run `uv run python -m pytest tests/test_caldav_sync_engine.py -v -k "test_missing_external_url"`
2. **Expected:** Error recorded with descriptive message, other events still processed

### Multiple events with mixed success/failure

1. Run `uv run python -m pytest tests/test_caldav_sync_engine.py -v -k "test_partial_status_on_mixed or test_all_errors_status"`
2. **Expected:** 2 tests pass — partial status when some succeed/fail, error status when all fail

### Empty patch skipped (no pushable changes)

1. Run `uv run python -m pytest tests/test_caldav_sync_engine.py -v -k "test_empty_patch_skipped"`
2. **Expected:** Event skipped (not pushed), skipped count incremented

## Failure Signals

- Any test failure in `test_caldav_field_mapper.py` or `test_caldav_sync_engine.py` — push pipeline broken
- `rg` finding "stub" or "S03" in production code — incomplete implementation
- Test count below 229 — tests removed or broken during merge
- Failure-path test count below 17 — diagnostic coverage regression

## Requirements Proved By This UAT

- CDAV-05 (RSVP push-back via PUT with ETag concurrency) — proven by tests 3, 4, 5, 6
- CDAV-06 (bidirectional sync) — proven by tests 3, 7 (direction guard acknowledges bidirectional mode)

## Not Proven By This UAT

- Runtime behavior against a real or mock CalDAV server — deferred to S04 E2E test
- UI integration (Sync Now button triggering push_sync) — deferred to S04 E2E test
- End-to-end RSVP change visible in CalDAV server — deferred to S04 E2E test

## Notes for Tester

- All tests use mocks (MockCalDAVHttpClient, MockGraphClient) — no Docker stack needed
- The 229 test count includes tests from S01 (auth, client) and S02 (field_mapper, sync_engine, person_matcher) — not just S03's 36 new tests
- CalDAV push uses fetch-modify-PUT (not REST PATCH like Google/Outlook) — the PUT sends the full VCALENDAR document back, not a partial update
