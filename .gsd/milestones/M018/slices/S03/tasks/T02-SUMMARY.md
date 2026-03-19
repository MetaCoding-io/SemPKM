---
id: T02
parent: S03
milestone: M018
provides:
  - Person matcher (email → bpkm:Person IRI) with SPARQL lookup, creation, and LRU cache
  - GCalClient.get_events() with syncToken pagination, singleEvents=false, and 410 Gone handling
  - sync_engine.pull_sync() orchestrating full Google Calendar → bpkm:Event pull sync pipeline
  - 47 tests (11 person matcher + 36 sync engine) covering all pull sync paths
key_files:
  - apps/google-calendar/services/person_matcher.py
  - apps/google-calendar/services/gcal_client.py
  - apps/google-calendar/services/sync_engine.py
  - backend/tests/test_gcal_person_matcher.py
  - backend/tests/test_gcal_sync_engine.py
key_decisions:
  - "token_expiry set to 2099 in connected state fixture means refresh_if_expired skips HTTP call — tests mock only the GCal events API, not the OAuth token flow"
patterns_established:
  - "Same importlib loading order pattern for gcal sync tests: field_mapper → person_matcher → gcal_client → auth → sync_engine"
  - "MockExternalHttpClient with sequential response queue (no token_resp needed when token_expiry is far future)"
observability_surfaces:
  - "google_calendar.sync logger: INFO per calendar (events fetched, created/updated/unchanged), WARNING on per-event errors, INFO on syncToken state"
  - "google_calendar.person_matcher logger: DEBUG on cache hits/misses and person creation"
  - "pull_sync() returns {status, created, updated, unchanged, errors} — errors array has event_id + error for diagnosis"
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Build person matcher, extend GCalClient with get_events, and build sync engine with tests

**Built full pull sync pipeline: person matcher, GCalClient.get_events(), and sync engine with two-phase bulk create, per-event error isolation, syncToken persistence — 47 tests all passing, 1609 full suite green.**

## What Happened

Created three service modules that together form the complete pull sync pipeline:

1. **person_matcher.py** — copied from linear-sync with logger name changed to `google_calendar.person_matcher`. PersonMatcher class resolves attendee/organizer emails to bpkm:Person IRIs via SPARQL lookup (foaf:mbox + crm:email), creates on miss with slugified name, and caches per sync run.

2. **GCalClient.get_events()** — added to gcal_client.py with syncToken-based incremental fetch, `singleEvents=false` for master recurring events, pagination via nextPageToken, 90-day timeMin for full syncs, and 410 Gone propagation for the sync engine to handle.

3. **sync_engine.py** — full pull_sync() orchestration following the linear-sync/github-sync two-phase bulk pattern. Per-calendar iteration with syncToken persistence, per-event error isolation via try/except, attendee/organizer resolution via PersonMatcher stored as edge.create commands (not string properties), and direct /api/commands/bulk POST bypassing SDK IRI prefix checks.

The initial test run had 17 failures due to mock response queue alignment — `_make_connected_state()` sets `token_expiry: "2099-..."` so `refresh_if_expired` returns immediately without consuming a mock HTTP response. Removing the unused `token_resp` from all response queues fixed everything.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_gcal_person_matcher.py -v` — 11 tests pass (≥8 required)
- `cd backend && .venv/bin/python -m pytest tests/test_gcal_sync_engine.py -v` — 36 tests pass (≥30 required)
- `cd backend && .venv/bin/python -m pytest -x` — 1609 tests pass, zero regressions

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_gcal_person_matcher.py -v` | 0 | ✅ pass | 4.1s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_gcal_sync_engine.py -v` | 0 | ✅ pass | 0.09s |
| 3 | `cd backend && .venv/bin/python -m pytest -x` | 0 | ✅ pass | 8.46s |

Slice-level verification (partial — T03 still pending):
| # | Command | Exit Code | Verdict | Notes |
|---|---------|-----------|---------|-------|
| 1 | `pytest tests/test_gcal_field_mapper.py -v` | 0 | ✅ pass | T01 — 64 tests |
| 2 | `pytest tests/test_gcal_sync_engine.py -v` | 0 | ✅ pass | 36 tests |
| 3 | `pytest tests/test_gcal_person_matcher.py -v` | 0 | ✅ pass | 11 tests |
| 4 | `pytest -x` | 0 | ✅ pass | 1609 full suite |
| 5 | Jinja2 template syntax check | — | ⏳ pending | T03 scope |
| 6 | htmx URL prefix check | — | ⏳ pending | T03 scope |

## Diagnostics

- **pull_sync() return dict:** `{status, created, updated, unchanged, errors}` — errors array includes `{event_id, error}` for per-event diagnosis
- **syncToken state:** `sync_token:{calendar_id}` in app state — check via state client to see if incremental or full sync needed
- **Logs:** `google_calendar.sync` at INFO for per-calendar stats, WARNING for per-event failures. `google_calendar.person_matcher` at DEBUG for cache behavior.
- **Test failure diagnosis:** Tests use importlib loading; dependency order matters (field_mapper → person_matcher → gcal_client → auth → sync_engine). Mock response queue must align with actual HTTP calls — no token_resp needed when token_expiry is far future.

## Deviations

None. All steps followed the task plan.

## Known Issues

None.

## Files Created/Modified

- `apps/google-calendar/services/person_matcher.py` — new: PersonMatcher class with SPARQL email lookup, creation, LRU cache (~140 lines)
- `apps/google-calendar/services/gcal_client.py` — modified: added get_events() method with syncToken, pagination, 410 handling (~65 new lines)
- `apps/google-calendar/services/sync_engine.py` — new: pull_sync() orchestration with two-phase bulk create (~350 lines)
- `backend/tests/test_gcal_person_matcher.py` — new: 11 tests covering email lookup, cache, edge cases, slugify
- `backend/tests/test_gcal_sync_engine.py` — new: 36 tests covering find_existing_event, command builders, batch submission, full pull_sync pipeline
