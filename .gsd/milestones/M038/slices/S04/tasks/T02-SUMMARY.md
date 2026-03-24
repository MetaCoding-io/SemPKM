---
id: T02
parent: S04
milestone: M038
provides:
  - poll-spotify task handler wired into media-scheduler app
  - 6 Spotify OAuth/subscription fragment routes in app.py
  - Spotify section in add-source.html template (connected/disconnected states)
  - poll-spotify task in manifest.yaml with 15m interval and retry policy
  - 27 new tests (poll task, routes, manifest, template validation, edge cases)
key_files:
  - apps/media-scheduler/app.py
  - apps/media-scheduler/manifest.yaml
  - apps/media-scheduler/frontend/templates/add-source.html
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Spotify credentials stored as spotify_client_id/spotify_client_secret/spotify_redirect_uri in state (separate from spotify_access_token/spotify_refresh_token auth keys)
  - PKCE code_verifier stored in state under spotify_code_verifier during OAuth flow, cleared after callback
  - OAuth callback returns standalone HTML page (same _oauth_result_page pattern as Google Calendar) — not an htmx fragment
  - Connect form uses hx-boost="false" to allow full-page redirect to Spotify OAuth consent
  - Playlist selector uses hx-get with hx-trigger="load" to populate options after connection
patterns_established:
  - Mock pattern for poll tasks using importlib-loaded app modules: patch on _app_mod (not _sp_svc_mod) because importlib creates separate module instances with distinct class identities
observability_surfaces:
  - poll_spotify returns {sources_polled, items_created} or {skipped: reason} — logged by AppScheduler
  - spotify.poll logger covers per-source poll events, error counts, cap warnings
  - spotify.auth logger covers token refresh events (already from T01, used by poll task)
  - Connection status via get_spotify_connection_status() — used by add-source template rendering
  - Per-source error tracking via update_source_state(errorCount, lastError)
duration: 35m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: App wiring — routes, poll task, template, manifest

**Wired Spotify service into media-scheduler app: poll-spotify task, 6 OAuth/subscription routes, template Spotify section, manifest task entry, and 27 new tests — all 321 tests pass**

## What Happened

Wired the T01 spotify_service.py module into the running media-scheduler app following the established YouTube + Google Calendar patterns:

1. **Import block** — Added try/except with importlib fallback for spotify_service (same pattern as youtube_service block, using `_ilu5`/`_pl5` aliases).

2. **poll_spotify task handler** — Decorated with `@media_scheduler_app.task("poll-spotify")`. Checks connection status → reads credentials → refreshes token → queries SPOTIFY_SOURCES_SPARQL → for each source creates SpotifyClient, fetches playlist tracks, deduplicates, caps at MAX_INITIAL_ITEMS, bulk-creates. SpotifyAPIError caught per-source (increments errorCount), SpotifyAuthError breaks loop. Returns summary dict.

3. **6 fragment routes**:
   - `/_fragments/spotify/connect` POST — saves credentials + PKCE verifier in state, 303 redirects to Spotify OAuth
   - `/_fragments/spotify/callback` GET — validates CSRF state, exchanges code with PKCE verifier, fetches profile, stores tokens
   - `/_fragments/spotify/disconnect` POST — clears auth + credentials, re-renders add-source
   - `/_fragments/spotify/status` GET — returns connection status HTML fragment
   - `/_fragments/spotify/playlists` GET — refreshes token, lists playlists as `<option>` elements
   - `/_fragments/sources/add-spotify` POST — subscribes to selected playlist, emits sourcesChanged

4. **Template update** — Spotify section with two states: disconnected (client_id/secret/redirect_uri form → Connect button with hx-boost=false for full redirect) and connected (display name/product, playlist `<select>` auto-populated via hx-get, Add/Disconnect buttons).

5. **Manifest** — Added `poll-spotify` task with 15m interval and retry policy matching poll-youtube.

6. **27 new tests** across 5 classes: TestPollSpotify (9), TestSpotifyRoutes (6), TestManifestSpotify (3), TestAddSourceTemplateSpotify (5), TestPollSpotifyEdgeCases (3). Plus updated existing TestManifest.test_manifest_has_tasks to expect 4 tasks.

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — 321 tests pass (294 existing + 27 new T02)
- `python -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — app parses cleanly
- `python -c "import yaml; m=yaml.safe_load(open('apps/media-scheduler/manifest.yaml')); assert 'poll-spotify' in [t['id'] for t in m['tasks']]"` — manifest has poll-spotify
- `grep -q 'spotify' apps/media-scheduler/frontend/templates/add-source.html` — Spotify in template
- `grep -c '/app/media-scheduler/' apps/media-scheduler/frontend/templates/add-source.html` — 10 proxy-prefixed URLs (≥5 required)
- `cd backend && python -m pytest tests/test_media_scheduler.py -v -k "connection_status or auth_error or rate_limit or SpotifyAPIError"` — 3 failure-path tests pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` | 0 | ✅ pass | 0.78s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import yaml; m=yaml.safe_load(open('apps/media-scheduler/manifest.yaml')); tasks=[t['id'] for t in m['tasks']]; assert 'poll-spotify' in tasks"` | 0 | ✅ pass | <1s |
| 4 | `grep -q 'spotify' apps/media-scheduler/frontend/templates/add-source.html` | 0 | ✅ pass | <1s |
| 5 | `grep -c '/app/media-scheduler/' apps/media-scheduler/frontend/templates/add-source.html` | 0 | ✅ pass (10 ≥ 5) | <1s |
| 6 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/spotify_service.py').read())"` | 0 | ✅ pass | <1s |
| 7 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "connection_status or auth_error or rate_limit or SpotifyAPIError"` | 0 | ✅ pass | 0.28s |

### Slice-level checks (S04 — after T02)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | All tests pass (321 total) | ✅ pass | 294 existing + 27 new T02 |
| 2 | poll-spotify task in manifest | ✅ pass | |
| 3 | Spotify section in template | ✅ pass | |
| 4 | spotify_service.py parses cleanly | ✅ pass | |
| 5 | app.py parses cleanly | ✅ pass | |
| 6 | Failure-path diagnostic tests pass | ✅ pass | |

## Diagnostics

- **Poll task inspection:** `poll_spotify(ctx)` returns `{"sources_polled": N, "items_created": N}` on success, or `{"skipped": "not_connected"|"no_credentials"|"auth_refresh_failed"}` on skip
- **Per-source errors:** SpotifyAPIError increments source errorCount/lastError via update_source_state(); visible in sources list
- **Auth errors:** SpotifyAuthError breaks the poll loop; logged via spotify.poll logger at WARNING level
- **OAuth flow tracing:** spotify.auth logger records token exchange, refresh, and PKCE flow events
- **Connection status:** `get_spotify_connection_status(state_client)` returns `{connected, display_name, product, token_expiry}`
- **Template state:** add_source_fragment passes spotify_connected and spotify_status to template for conditional rendering

## Deviations

- Added `uuid` and `RedirectResponse` imports to app.py (needed for OAuth flow but not mentioned in plan)
- Stored Spotify credentials under `spotify_client_id`/`spotify_client_secret`/`spotify_redirect_uri` state keys (plan didn't specify key names for stored credentials)
- Used `hx-boost="false"` on the connect form to allow full-page redirect to Spotify OAuth (htmx would intercept the 303 redirect otherwise)
- Tests use `_app_mod.SpotifyAuthError` / `_app_mod.SpotifyAPIError` for exception class identity — patching at `_sp_svc_mod` level doesn't work because importlib creates separate module instances with distinct class objects

## Known Issues

- Pre-existing: `poll_youtube` in app.py has an indentation bug (line with `candidate_iri` is over-indented under a comment) — not introduced by this task

## Files Created/Modified

- `apps/media-scheduler/app.py` — added Spotify import block, poll_spotify task handler, _update_spotify_source_state helper, _spotify_oauth_result_page helper, 6 fragment routes, updated add_source_fragment to pass Spotify status context
- `apps/media-scheduler/manifest.yaml` — added poll-spotify task with 15m interval and retry policy
- `apps/media-scheduler/frontend/templates/add-source.html` — added Spotify section with connected/disconnected states, playlist selector, connect/disconnect forms
- `backend/tests/test_media_scheduler.py` — added 27 tests across 5 new classes (TestPollSpotify, TestSpotifyRoutes, TestManifestSpotify, TestAddSourceTemplateSpotify, TestPollSpotifyEdgeCases) + updated TestManifest.test_manifest_has_tasks
- `.gsd/milestones/M038/slices/S04/tasks/T02-PLAN.md` — added Observability Impact section
