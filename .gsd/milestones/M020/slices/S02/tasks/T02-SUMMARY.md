---
id: T02
parent: S02
milestone: M020
provides:
  - Outlook Calendar sync_engine.py with pull_sync (delta queries, @removed handling, two-phase bulk, per-event error isolation) and push_sync (RSVP push-back skeleton)
  - person_matcher.py with SPARQL email lookup, create-on-miss, in-memory LRU cache
  - requirements.txt with markdownify dependency
  - 60 sync engine tests + 14 person matcher tests
key_files:
  - apps/outlook-calendar/services/sync_engine.py
  - apps/outlook-calendar/services/person_matcher.py
  - apps/outlook-calendar/requirements.txt
  - backend/tests/test_outlook_sync_engine.py
  - backend/tests/test_outlook_person_matcher.py
key_decisions:
  - Outlook delta link stored as `delta_link:{calendar_id}` state key (vs Google's `sync_token:{calendar_id}`)
  - Outlook attendee processing uses nested `emailAddress.address`/`emailAddress.name` (not Google's flat `.email`/`.displayName`)
  - Self-organizer detection compares organizer email to `microsoft_email` from state (Outlook has no `.self` flag on organizer)
  - MockOutlookClient used instead of MockExternalHttpClient for sync engine tests — cleaner than intercepting HTTP responses
patterns_established:
  - Monkey-patch OutlookClient construction via `_patch_outlook_client` context manager for test isolation
  - Same importlib-based test loading with dependency-order module registration matching the try/except import names
observability_surfaces:
  - `outlook.sync` logger — INFO per-calendar event counts and sync result; WARNING per-event errors with event_id
  - `last_pull_result` / `last_push_result` state keys — JSON with status, counts, errors array, timestamp
  - Per-event errors in result `errors` list with event_id + error string
duration: 25m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Build sync engine + person matcher with 52+ unit tests

**Built Outlook sync engine with delta query pull sync, @removed event handling, expired delta recovery, push_sync RSVP skeleton, person matcher, and 74 passing tests (178 total across all three files).**

## What Happened

Cloned person_matcher.py from Google Calendar with only the logger name changed to `outlook.sync.person_matcher`. All logic identical — `_slugify`, `_email_local_part`, `PersonMatcher` with SPARQL email lookup and create-on-miss.

Built sync_engine.py adapting Google's pattern for Outlook-specific behavior:
- Delta queries via `OutlookClient.get_events_delta()` returning `(events, delta_link)` tuples
- Delta link persistence as `delta_link:{calendar_id}` state keys
- Expired delta recovery: catches `OutlookAPIError` with status_code 410, clears stored link, retries with full sync
- `@removed` key detection in delta responses — skipped entirely, no create/update
- Outlook's nested attendee structure: `attendee["emailAddress"]["address"]` and `.name` (not Google's flat `.email`/`.displayName`)
- Self-organizer detection by comparing organizer email to `microsoft_email` from state (Outlook doesn't have a `.self` boolean)
- Two-phase bulk create: phase 1 creates events, phase 2 discovers minted IRIs then submits body.set/edge.create
- Per-event error isolation with structured error capture in result dict
- push_sync with RSVP push-back via `OutlookClient.patch_event()`

Created requirements.txt with markdownify.

Tests use a `MockOutlookClient` that stubs `get_events_delta()` and `patch_event()`, with a `_patch_outlook_client` context manager that monkey-patches the module-level `OutlookClient` class. This is cleaner than the Google Calendar approach of intercepting raw HTTP responses through `MockExternalHttpClient`.

## Verification

- `python -m pytest tests/test_outlook_person_matcher.py -v` — 14 tests pass
- `python -m pytest tests/test_outlook_sync_engine.py -v` — 60 tests pass  
- `python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` — 177 passed, 1 skipped (markdownify), 178 total collected
- `test_last_pull_result_contains_error_detail` — proves diagnostic surface: last_pull_result state key contains event_id and error string for failed events
- `test_expired_delta_410_retries_full_sync` — proves expired delta recovery: 410 caught, link cleared, full re-sync succeeds with fresh delta link
- `test_removed_event_skipped` — proves @removed handling: removed events in delta response are skipped, only normal events created

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_outlook_person_matcher.py -v` | 0 | ✅ pass | 0.2s |
| 2 | `python -m pytest tests/test_outlook_sync_engine.py -v` | 0 | ✅ pass | 0.2s |
| 3 | `python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v --tb=short` | 0 | ✅ pass | 0.2s |

## Diagnostics

- **Sync result inspection:** Read `last_pull_result` / `last_push_result` state keys — JSON with `status` (ok/partial/error/skipped), `created`/`updated`/`unchanged` counts, `errors` array, `timestamp`
- **Per-event errors:** Each error in `result["errors"]` has `event_id` and `error` string
- **Delta state:** Read `delta_link:{calendar_id}` state key to see current delta link for incremental sync
- **Re-run tests:** `cd backend && source .venv/bin/activate && python -m pytest tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py -v`

## Deviations

- Used `MockOutlookClient` pattern (directly stubbing client methods) instead of `MockExternalHttpClient` (raw HTTP response interception) — cleaner for Outlook since delta queries return tuples, not raw responses
- Module loading in sync engine tests uses generic names (`field_mapper`, `person_matcher`, `outlook_client`, `auth`, `sync_engine`) in sys.modules to match the try/except fallback import paths — the Google test used distinct prefixed names but that doesn't work when the module's own imports resolve against sys.modules
- 14 person matcher tests (plan said 12+) and 60 sync engine tests (plan said 40+) — exceeded requirements

## Known Issues

None.

## Files Created/Modified

- `apps/outlook-calendar/services/person_matcher.py` — Email-based attendee resolution with SPARQL lookup, create-on-miss, LRU cache (~140 lines)
- `apps/outlook-calendar/services/sync_engine.py` — Pull + push sync pipeline with delta queries, @removed handling, two-phase bulk, error isolation (~680 lines)
- `apps/outlook-calendar/requirements.txt` — markdownify dependency
- `backend/tests/test_outlook_sync_engine.py` — 60 sync engine tests covering all sync paths (~1500 lines)
- `backend/tests/test_outlook_person_matcher.py` — 14 person matcher tests (~220 lines)
