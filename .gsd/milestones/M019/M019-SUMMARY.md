---
id: M019
provides:
  - Todoist Sync app — fourth bidirectional sync app on App Platform
  - PAT authentication with token verification via GET /rest/v2/projects
  - TodoistClient REST wrapper (get_tasks/projects/labels, close/reopen/create/update)
  - Bidirectional field mapper with priority inversion (Todoist 1→low, 2→medium, 3→high, 4→critical)
  - pull_sync() creating bpkm:Task objects with project selection, labels as tags, due dates, descriptions
  - push_sync() with close/reopen endpoint branching for completion state changes
  - Settings UI with project selection, sync direction, poll interval, Sync Now
  - PersonMatcher with email-based SPARQL lookup and LRU cache
  - Mock Todoist REST API v2 server (10 endpoints, 10-point selftest)
  - 11-phase Playwright E2E test (structurally complete)
  - Chapter 37 user guide (358 lines) with field mapping tables and troubleshooting
key_decisions:
  - D215 — PAT-only auth for v1 (no OAuth), matching GitHub sync approach
  - D216 — TD- prefix for Todoist sync requirements
  - Auth verification via GET /rest/v2/projects (Todoist has no /user endpoint)
  - close/reopen as separate POST endpoints rather than PATCH status field (matches Todoist API design)
  - externalId (not externalUuid) for task identity — Todoist pull_sync only populates externalId
  - TODOIST_API_URL env var override in both client and auth for mock server testability
patterns_established:
  - Fourth sync app confirming the established pattern — auth/client/field_mapper/person_matcher/sync_engine module structure
  - Todoist close/reopen endpoint pattern (POST /tasks/{id}/close and /tasks/{id}/reopen) as alternative to PATCH-based status update
  - Mock API server selftest pattern reused from GitHub and Google Calendar
  - TODOIST_API_URL env var override pattern matching GITHUB_API_URL and GOOGLE_CALENDAR_API_URL
observability_surfaces:
  - todoist.sync.auth logger — INFO on token store/verify/clear, WARNING on verification failures
  - todoist.sync.client logger — DEBUG for each REST request (method + URL)
  - todoist.sync logger — INFO per pull/push cycle with aggregate counts, WARNING per task failure
  - get_connection_status() — returns connected flag, auth_method, projects_count, token_preview
  - last_pull_result state key — JSON with status, created, updated, unchanged, errors, error_details, duration_ms, timestamp
  - last_push_result state key — JSON with status, pushed, skipped, closed, reopened, updated, errors, timestamp
  - sync_direction and poll_interval readable via ctx.settings.get()
requirement_outcomes: []
duration: 138m
verification_result: passed
completed_at: 2026-03-19
---

# M019: Todoist Sync App

**Fourth bidirectional sync app on the App Platform — Todoist tasks sync to bpkm:Task objects with inverted priority mapping, close/reopen endpoint pattern, and 239 unit tests proving all paths.**

## What Happened

Three slices delivered the complete Todoist Sync app following the established sync app architecture from M016 (Linear), M017 (GitHub), and M018 (Google Calendar).

**S01 — Auth + Client + Pull Sync (61m).** Built the app scaffold with PAT authentication (token storage, verification via GET /rest/v2/projects, connection status, disconnect), TodoistClient REST wrapper covering all CRUD operations plus close/reopen, bidirectional field mapper (priority inversion all 4 levels, status mapping, due date extraction, labels passthrough), PersonMatcher adapted from prior sync apps, and pull_sync engine with two-phase bulk create, existing task detection via externalId SPARQL lookup, and per-task error isolation. 168 unit tests.

**S02 — Push Sync + Settings UI (38m).** Added push_sync pipeline: SPARQL-based change detection via _find_changed_tasks(), status change direction detection (close vs reopen), dedicated Todoist endpoint calls before field updates, lastSyncedAt loop prevention in both push and pull paths. Settings UI with sync direction radios, poll interval dropdown, push result stats. Bidirectional sync_now handler and real push_changes task handler. 71 additional push-specific tests (239 total).

**S03 — E2E Tests + User Guide (39m).** Mock Todoist REST API v2 server with 10 endpoints (including 204-response close/reopen matching real Todoist behavior) and 10-point selftest. TODOIST_API_URL env var override added to both client and auth modules. Docker service wiring in docker-compose.test.yml. 11-phase Playwright E2E test following the established pattern. Chapter 37 user guide (~358 lines) with priority inversion tables, close/reopen endpoint documentation, troubleshooting. README TOC, glossary, appendix A, and Ch 36→37 navigation chain updates.

The Todoist REST API v2 turned out to be the simplest sync target of the four — no pagination, no OAuth, no GraphQL. The only novel pattern was the close/reopen endpoint design (POST to separate URLs rather than PATCH status), which push_sync handles by branching on status change direction before any field updates.

## Cross-Slice Verification

Each roadmap success criterion verified with specific evidence:

| # | Success Criterion | Evidence | Result |
|---|---|---|---|
| 1 | User installs app, enters API token, connects | manifest.yaml valid, auth.py store/verify/status/disconnect, 25 auth unit tests | ✅ |
| 2 | User selects projects, triggers sync, sees tasks as bpkm:Task with correct priorities, due dates, labels | pull_sync engine with project selection, field mapper with all 4 priority levels bidirectional, 168 S01 tests | ✅ |
| 3 | User completes task in SemPKM → Todoist task closed via close endpoint | push_sync branches on status change, calls POST /tasks/{id}/close, 71 push-specific tests | ✅ |
| 4 | User reopens task in SemPKM → Todoist task reopened | push_sync calls POST /tasks/{id}/reopen, tested in push pipeline | ✅ |
| 5 | Settings UI with project selection, direction, interval, Sync Now | connect_status.html with all controls, 25 route/handler tests, htmx URLs grep-verified prefixed | ✅ |
| 6 | 150+ unit tests | `pytest backend/tests/test_todoist_*.py` — **239 passed in 0.49s** | ✅ |
| 7 | Mock Todoist API server passes selftest | `python3 e2e/mock-todoist-api/server.py --selftest` — **10/10 passed** | ✅ |
| 8 | E2E Playwright test structurally complete | `npx playwright test tests/37-todoist-sync/ --list` — **2 tests listed** (chromium + firefox), 11 phases | ✅ |
| 9 | Chapter 37 user guide with field mapping tables | `docs/guide/37-todoist-sync.md` — 358 lines with priority inversion, close/reopen, troubleshooting | ✅ |
| 10 | Docker compose config valid | `docker compose -f docker-compose.test.yml config --quiet` — valid | ✅ |

**Definition of done:**
- ✅ All three slices complete (S01 ✓, S02 ✓, S03 ✓)
- ✅ App installable from Admin > Applications (manifest validates against AppManifestSchema)
- ✅ PAT auth connects and verifies via GET /rest/v2/projects
- ✅ Pull sync creates bpkm:Task objects with all mapped fields
- ✅ Push sync closes/reopens tasks and updates fields
- ✅ Settings UI with project selection, direction, interval, Sync Now
- ✅ 239 pytest unit tests pass in <1s (target was 150+)
- ✅ Mock Todoist API server passes selftest (10/10)
- ✅ Playwright E2E test structurally complete (11 phases, may hit pre-existing subprocess issue)
- ✅ Chapter 37 user guide published with field mapping tables
- ✅ All htmx URLs use /app/todoist-sync/ prefix (grep-verified empty)
- ✅ README TOC, glossary entry, appendix A env var, Ch 36 navigation footer all updated

## Requirement Changes

The roadmap used TD-01 through TD-08 as informal coverage references — these were never registered as formal requirements in REQUIREMENTS.md (per D216, they used a TD- prefix for tracking). No formal requirement status transitions occurred during this milestone.

Coverage evidence for the informal TD requirements:
- TD-01 (PAT auth) — 25 auth unit tests, verified in S01
- TD-02 (pull sync) — 38 sync engine tests, pull_sync creates bpkm:Task with all fields
- TD-03 (push sync) — 71 push-specific tests, close/reopen/update pipeline proven
- TD-04 (project selection) — project checkboxes in UI, selection persisted as JSON state
- TD-05 (priority mapping) — 65 field mapper tests covering all 4 levels bidirectionally
- TD-06 (label→tag mapping) — labels passed through as bpkm:tags array, unit tested
- TD-07 (settings UI) — direction radios, poll interval, sync stats, all route-tested
- TD-08 (E2E + user guide) — mock server (10/10 selftest), E2E test (11 phases), Chapter 37 (358 lines)

## Forward Intelligence

### What the next milestone should know
- The sync app pattern is now proven across four providers (Linear, GitHub, Google Calendar, Todoist) with consistent architecture: auth/client/field_mapper/person_matcher/sync_engine module structure, mock API server with selftest, TODOIST_API_URL-style env var override for testability, 11-phase E2E test structure.
- Todoist was the simplest implementation — no pagination, no OAuth, no GraphQL. Future providers (Asana, Jira, Monday.com) will likely be more complex. Jira in particular has complex pagination and auth flows.
- The close/reopen endpoint pattern (separate POST endpoints rather than PATCH status) worked cleanly. Future providers with similar patterns (e.g., Asana has complete/uncomplete) can follow the same branching logic in push_sync.

### What's fragile
- The pre-existing subprocess startup issue continues to block full E2E runtime across all sync apps (M016–M019). A platform-level fix would unblock all app E2E tests simultaneously.
- The importlib test loading with types.ModuleType pseudo-packages generates a DeprecationWarning on Python 3.14 (`__package__ != __spec__.parent`). Works correctly on current Python but may need revision.
- externalId vs externalUuid divergence: Todoist uses externalId exclusively while GitHub uses externalUuid. Future agents comparing implementations should note this distinction.

### Authoritative diagnostics
- `python3 -m pytest backend/tests/test_todoist_*.py -v` — 239 tests, <1s, the fastest way to verify all Todoist sync behavior
- `python3 e2e/mock-todoist-api/server.py --selftest` — exercises all 10 mock endpoints without Docker
- `last_pull_result` and `last_push_result` state keys — JSON with status, counts, error_details, duration_ms. Single source of truth for sync health.

### What assumptions changed
- Original plan assumed 150+ tests — delivered 239 (59% over target). The field mapper's bidirectional priority/status/due-date coverage and the push pipeline's branching logic each required more test paths than initially estimated.
- The roadmap assumed formal TD requirements would be registered in REQUIREMENTS.md — in practice they were tracked informally in the roadmap only. This is fine since the unit test evidence is comprehensive.

## Files Created/Modified

- `apps/todoist-sync/manifest.yaml` — App manifest with identity, permissions, two background tasks
- `apps/todoist-sync/app.py` — Route handlers for connect/disconnect/projects/sync-now/sync-config/poll-tasks/push-changes
- `apps/todoist-sync/services/__init__.py` — Package init
- `apps/todoist-sync/services/auth.py` — Token storage, verification via /rest/v2/projects, connection status, masking, TODOIST_API_URL override
- `apps/todoist-sync/services/todoist_client.py` — REST client with Bearer auth, all CRUD + close/reopen, TODOIST_API_URL override
- `apps/todoist-sync/services/field_mapper.py` — Bidirectional field mapping (priority inversion, status, due date, labels, properties, reverse mapping)
- `apps/todoist-sync/services/person_matcher.py` — Email/name SPARQL person resolution with LRU cache
- `apps/todoist-sync/services/sync_engine.py` — pull_sync + push_sync engines with two-phase bulk create, change detection, close/reopen branching, loop prevention
- `apps/todoist-sync/frontend/templates/connect.html` — PAT input form with htmx
- `apps/todoist-sync/frontend/templates/connect_status.html` — Connected status with project selection, sync config, sync/push stats
- `apps/todoist-sync/frontend/templates/projects.html` — Project checkbox form
- `apps/todoist-sync/frontend/static/styles.css` — App-specific styles
- `backend/tests/test_todoist_auth.py` — 25 auth unit tests
- `backend/tests/test_todoist_client.py` — 22 client unit tests
- `backend/tests/test_todoist_field_mapper.py` — 65 field mapper unit tests
- `backend/tests/test_todoist_person_matcher.py` — 18 person matcher unit tests
- `backend/tests/test_todoist_sync_engine.py` — 38 sync engine unit tests
- `backend/tests/test_todoist_push_sync.py` — 71 push sync unit tests
- `e2e/mock-todoist-api/server.py` — Mock Todoist REST API v2 server (10 endpoints, selftest)
- `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` — 11-phase Playwright E2E test
- `e2e/helpers/selectors.ts` — Added todoistSync selector block
- `docker-compose.test.yml` — Added mock-todoist service, TODOIST_API_URL on api service
- `docs/guide/37-todoist-sync.md` — Chapter 37 user guide (358 lines)
- `docs/guide/README.md` — Added line 37 to TOC
- `docs/guide/appendix-d-glossary.md` — Added Todoist Sync glossary entry
- `docs/guide/appendix-a-environment-variables.md` — Added TODOIST_API_URL row
- `docs/guide/36-google-calendar-sync.md` — Updated navigation footer (Next → Ch 37)
