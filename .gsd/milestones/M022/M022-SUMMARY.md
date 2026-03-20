---
id: M022
provides:
  - Asana Sync app with dual OAuth 2.0/PAT auth, configurable field mapping (3 status modes), bidirectional pull/push sync
  - "Configure before sync" UX pattern — user discovers custom fields, maps enum values to bpkm status/priority, persists config before first sync
  - Subtask recursion bounded at 5 levels with dcterms:isPartOf parent linking
  - Section-based status push via POST /sections/{gid}/addTask (distinct from custom field PATCH)
  - Two-path push dispatch — custom field PATCH and section move can fire on the same task
  - Mock Asana REST API server with 14-check selftest
  - 7-phase Playwright E2E spec covering full install → configure → sync → verify → cleanup lifecycle
  - Chapter 40 user guide with 3 status mapping modes and field mapping reference tables
key_decisions:
  - D227: Dual OAuth 2.0/PAT auth (matching M016 pattern, Asana OAuth has implicit scopes)
  - D228: Configurable field mapping as explicit setup step before sync (3 status modes: completed_only, custom_field, section)
  - D229: Subtask recursion bounded at 5 levels with per-level API calls
  - D230: ASANA- prefix for requirement IDs
  - D231: Section-based status push via addTask API, not field PATCH
  - D232: _raw_request/_request two-layer pattern for Asana's data envelope API
patterns_established:
  - "Configure before sync" pattern — reusable for Monday.com and other custom-field-heavy providers
  - _raw_request/_request two-layer pattern for APIs with response wrappers containing pagination metadata
  - Two-path push dispatch (custom field PATCH + section move) based on status_source configuration
  - Field mapping E2E test pattern — projects → discover → select source → save mapping → sync config → sync now
observability_surfaces:
  - Logger asana.sync.auth — OAuth exchange, refresh, PAT verification, store, clear events
  - Logger asana.sync.client — token refresh, API error status codes
  - Logger asana.sync.engine — pull_sync/push_sync start/complete, per-task errors, subtask recursion depth
  - Logger asana.sync.app — route handler events (credential save, OAuth redirect/callback, PAT verify, disconnect, project selection, field discovery, mapping save)
  - StateClient keys — last_pull_result, last_push_result (JSON with status, created/pushed, errors, duration_ms, timestamp)
  - get_connection_status(state_client) — {connected, auth_method, asana_email, token_expiry}
  - Mock server — [mock-asana] request logs on stderr, GET /health, --selftest mode
requirement_outcomes:
  - id: ASANA-01
    from_status: active
    to_status: validated
    proof: 30 auth unit tests cover OAuth exchange, refresh, PAT verification, store/clear. App routes implement full OAuth redirect/callback with CSRF state.
  - id: ASANA-02
    from_status: active
    to_status: validated
    proof: 28 client unit tests cover paginated project list, workspace retrieval, task queries with opt_fields, rate limit backoff. UI presents workspace-grouped project checkboxes.
  - id: ASANA-03
    from_status: active
    to_status: validated
    proof: discover-fields route unions custom fields and sections across selected projects. Discovered data persisted in StateClient. 125 field mapper tests cover all extraction paths.
  - id: ASANA-04
    from_status: active
    to_status: validated
    proof: Status mapping supports 3 modes (completed_only, custom_field, section). Priority mapping supports custom enum field. Both configurable via UI and persisted in StateClient. 125 field mapper tests verify forward and reverse mapping.
  - id: ASANA-05
    from_status: active
    to_status: validated
    proof: pull_sync creates bpkm:Task objects via two-phase bulk create. 84 sync engine tests cover create/update, incremental sync, per-task error isolation, diagnostic surface.
  - id: ASANA-06
    from_status: active
    to_status: validated
    proof: _fetch_subtasks_recursive walks up to MAX_SUBTASK_DEPTH=5 levels, annotates _parent_gid for dcterms:isPartOf edge creation in Phase 2. Tests verify 1, 3, and 5 levels with depth enforcement.
  - id: ASANA-07
    from_status: active
    to_status: validated
    proof: Field mapper extracts Asana tags and maps to SemPKM tags. Covered by field mapper unit tests.
  - id: ASANA-08
    from_status: active
    to_status: validated
    proof: PersonMatcher resolves followers via SPARQL email lookup with create-on-miss and LRU cache. 18 person matcher unit tests.
  - id: ASANA-09
    from_status: active
    to_status: validated
    proof: push_sync with two-path dispatch — custom field PATCH for enum status/priority, POST /sections/{gid}/addTask for section-based status moves. 84 sync engine tests cover both paths.
  - id: ASANA-10
    from_status: active
    to_status: validated
    proof: Settings UI with sync direction radios (pull-only/bidirectional), poll interval dropdown, Sync Now button, pull/push stat-group/stat-row displays. sync-config POST route persists settings.
  - id: ASANA-11
    from_status: active
    to_status: validated
    proof: Mock Asana REST API server (14-check selftest). 7-phase Playwright E2E spec. Chapter 40 user guide (351 lines) with field mapping walkthrough. README TOC, glossary, appendix A, nav chain updated.
duration: 197min
verification_result: passed
completed_at: 2026-03-19
---

# M022: Asana Sync App

**Seventh bidirectional sync app on the App Platform — Asana tasks sync to bpkm:Task objects via configurable field mapping with 3 status modes (completed_only, custom_field, section), subtask nesting up to 5 levels, and two-path push dispatch (custom field PATCH + section move), backed by 285 unit tests, mock API server, E2E spec, and Chapter 40 user guide.**

## What Happened

S01 built the foundation — dual OAuth 2.0/PAT authentication (30 tests), REST client with `_raw_request/_request` two-layer pattern for Asana's data envelope API (28 tests), 8 route handlers, and the novel "configure before sync" field mapping UI. This was the highest-risk piece: Asana has no native status or priority fields, so users must discover custom fields from their projects and map enum values to bpkm status/priority before any sync can run. Three status modes emerged: `completed_only` (just Asana's completed boolean), `custom_field` (enum field matched by GID), and `section` (section membership as status). All configuration persists in 10 StateClient keys.

S02 built the pull sync pipeline — field mapper with configurable status/priority extraction reading from the S01-configured field_config dict (125 tests), person matcher with SPARQL email lookup and create-on-miss (18 tests), and sync engine with two-phase bulk create, subtask recursion bounded at 5 levels, incremental sync via `modified_since`, and per-task error isolation (84 tests). Tasks with `resource_subtype: "milestone"` create bpkm:Milestone objects. HTML notes convert to markdown via markdownify with regex fallback.

S03 added push sync with the milestone's second novel contribution: two-path dispatch. When status_source is `custom_field`, push builds an Asana PATCH body resolving enum option names to GIDs via discovered_enum_fields. When status_source is `section`, push calls `POST /sections/{gid}/addTask` to move the task between sections. Both paths can fire on the same task (section status + priority change). Reverse mapping functions invert the forward configuration. Settings UI added sync direction, poll interval, and sync stats display.

S04 tied everything together with integration testing and documentation. Mock Asana REST API server (~550 lines) provides canned responses for all 11 endpoints the client calls, with 14-check selftest. Docker compose wired with healthcheck and env vars. 7-phase Playwright E2E spec exercises install → PAT connect → field mapping → sync → SPARQL verify → cleanup. Chapter 40 user guide (351 lines) covers all three status mapping modes with field mapping reference tables.

## Cross-Slice Verification

| Success Criterion | Evidence |
|---|---|
| OAuth 2.0 + PAT auth both work with connection test | 30 auth unit tests: OAuth exchange, refresh, PAT verification, store/clear, connection status |
| Workspace/project selection persists and drives sync scope | connect_status.html with workspace-grouped checkboxes, StateClient `selected_projects` persistence |
| Custom field discovery returns real field metadata | discover-fields route unions enum/number fields and sections from selected projects. 125 field mapper tests |
| Status mapping (custom field or section-based) configures and persists | 3 status_source modes tested in field mapper (completed_only, custom_field, section). StateClient persistence verified |
| Priority mapping configures and persists | priority_field_gid + priority_mapping StateClient keys. Forward + reverse mapping unit tests |
| Pull sync creates bpkm:Task objects with all mapped fields including subtask nesting | 84 sync engine tests cover two-phase bulk create, subtask recursion at 1/3/5 levels, per-task error isolation |
| Push sync reverses field mapping including section-based status moves | Two-path dispatch tested: PATCH for custom field, addTask for section move. 84 sync engine tests |
| 200+ unit tests pass | **285 passed in 0.23s** (30 auth + 28 client + 125 field mapper + 18 person matcher + 84 sync engine) |
| Mock Asana REST API server selftest passes | 14/14 checks pass via `python3 e2e/mock-asana-api/server.py --selftest` |
| Playwright E2E test exercises full lifecycle | 7-phase spec at `e2e/tests/40-asana-sync/asana-sync.spec.ts` (~280 lines) |
| Chapter 40 user guide published with field mapping walkthrough | `docs/guide/40-asana-sync.md` (351 lines), 3 status mapping modes, 2 reference tables |
| README TOC, glossary, appendix A, navigation chain updated | README line 40, glossary "Asana Sync" entry, appendix A ASANA_API_URL/ASANA_TOKEN_URL, Ch 39→Ch 40 nav |
| All ASANA requirements validated | ASANA-01 through ASANA-11 all validated with test evidence |

## Requirement Changes

- ASANA-01: active → validated — 30 auth unit tests, full OAuth redirect/callback + PAT verify routes
- ASANA-02: active → validated — 28 client unit tests, workspace/project list with pagination and rate limit backoff
- ASANA-03: active → validated — discover-fields route, StateClient persistence, 125 field mapper tests
- ASANA-04: active → validated — 3 status modes + priority mapping with forward/reverse transforms, 125 field mapper tests
- ASANA-05: active → validated — pull_sync two-phase bulk create, 84 sync engine tests
- ASANA-06: active → validated — bounded subtask recursion (5 levels), depth-limited tests at 1/3/5 levels
- ASANA-07: active → validated — tag extraction and mapping in field mapper unit tests
- ASANA-08: active → validated — PersonMatcher SPARQL email lookup + create-on-miss, 18 unit tests
- ASANA-09: active → validated — two-path push dispatch (PATCH + section move), 84 sync engine tests
- ASANA-10: active → validated — settings UI with direction/interval/sync-now/stats, sync-config POST route
- ASANA-11: active → validated — mock server (14 selftest), E2E spec (7 phases), Chapter 40 (351 lines), README/glossary/appendix/nav-chain

## Forward Intelligence

### What the next milestone should know
- The "configure before sync" pattern established here (field discovery → mapping → persist → use at sync time) is directly reusable for Monday.com (M024) and any provider with custom-field-based status/priority. The key abstraction is `field_config` dict read from StateClient at sync time.
- The `_raw_request/_request` two-layer pattern works well for any API that wraps data in an envelope with pagination metadata as a sibling. Future sync apps with similar API shapes should adopt it.
- Asana's section-based status push requires `POST /sections/{gid}/addTask` (not a field PATCH) — this is the first sync app with a non-PATCH push path. The two-path dispatch pattern (check status_source, choose API call) may recur.

### What's fragile
- `_resolve_enum_option_gid()` scans discovered_enum_fields (a JSON blob from StateClient) to resolve option names to GIDs. If the discovered data structure changes shape, GID resolution silently returns None and push skips the field update.
- The `--noconftest` requirement for running Asana tests will persist until the backend Settings model accepts Asana env vars. Tests are fully self-contained with mocks.
- The inline JS in connect_status.html uses `window._asanaFieldMapping` IIFE — if the template is loaded in a context where the IIFE doesn't execute, mapping tables won't render.

### Authoritative diagnostics
- `last_pull_result` / `last_push_result` StateClient keys — JSON with full sync stats (status, created/pushed, errors, error_details, duration_ms, timestamp). Most trustworthy sync health signal.
- `python3 e2e/mock-asana-api/server.py --selftest` — exercises all 14 mock endpoints
- Logger `asana.sync.engine` — per-task error warnings include task GID and project GID

### What assumptions changed
- Plan assumed `get_user(user_gid)` endpoint — only `get_user_me()` is needed (connection identity + PAT verification)
- Plan assumed `get_connection_status` takes (state_client, http_client) — actual implementation takes only state_client
- Test count significantly exceeded targets: 285 actual vs 200+ planned

## Files Created/Modified

- `apps/asana-sync/services/__init__.py` — empty package init
- `apps/asana-sync/services/auth.py` — OAuth 2.0 + PAT auth module (~300 lines)
- `apps/asana-sync/services/asana_client.py` — REST client with 9 endpoints, exception hierarchy (~400 lines)
- `apps/asana-sync/services/field_mapper.py` — configurable field mapping with 3-mode status + reverse mapping (~450 lines)
- `apps/asana-sync/services/person_matcher.py` — SPARQL email lookup + create-on-miss + LRU cache (~130 lines)
- `apps/asana-sync/services/sync_engine.py` — pull + push sync with two-phase bulk create, subtask recursion, two-path push dispatch (~620 lines)
- `apps/asana-sync/manifest.yaml` — App manifest with permissions, tasks, UI config
- `apps/asana-sync/app.py` — 11 route handlers + 2 task handlers (~640 lines)
- `apps/asana-sync/requirements.txt` — markdownify dependency
- `apps/asana-sync/frontend/templates/connect.html` — Dual-auth connect form (OAuth + PAT)
- `apps/asana-sync/frontend/templates/connect_status.html` — Connection status + project selection + field mapping + settings UI (~360 lines)
- `apps/asana-sync/frontend/static/styles.css` — Scoped CSS for asana-sync UI (~380 lines)
- `backend/tests/test_asana_auth.py` — 30 auth unit tests
- `backend/tests/test_asana_client.py` — 28 client unit tests
- `backend/tests/test_asana_field_mapper.py` — 125 field mapper unit tests (forward + reverse mapping)
- `backend/tests/test_asana_person_matcher.py` — 18 person matcher unit tests
- `backend/tests/test_asana_sync_engine.py` — 84 sync engine unit tests (pull + push)
- `e2e/mock-asana-api/server.py` — Mock Asana REST API server (~550 lines), 14 endpoints, selftest
- `e2e/helpers/selectors.ts` — added asanaSync selector block (13 selectors)
- `e2e/tests/40-asana-sync/asana-sync.spec.ts` — 7-phase Playwright E2E spec (~280 lines)
- `docker-compose.test.yml` — added mock-asana service + env vars + depends_on
- `docs/guide/40-asana-sync.md` — Chapter 40 user guide (351 lines)
- `docs/guide/README.md` — added line 40 TOC entry
- `docs/guide/appendix-d-glossary.md` — added Asana Sync glossary entry
- `docs/guide/appendix-a-environment-variables.md` — added ASANA_API_URL and ASANA_TOKEN_URL rows
- `docs/guide/39-caldav-calendar-sync.md` — updated nav footer Next → Chapter 40
