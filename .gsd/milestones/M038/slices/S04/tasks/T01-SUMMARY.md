---
id: T01
parent: S04
milestone: M038
provides:
  - spotify_service.py module with PKCE helpers, OAuth flow, SpotifyClient, pure converters
  - 55 unit tests covering PKCE, URL parsing, track conversion, IRI minting, auth, client, subscribe, connection status, dedup
key_files:
  - apps/media-scheduler/services/spotify_service.py
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Used spotify_access_token / spotify_refresh_token / spotify_token_expiry state key prefix to avoid collision with Google Calendar auth keys
  - check_source_exists_spotify searches by externalId (playlist ID) rather than feedUrl, since canonical URL is spotify:playlist:{id} URI
  - track_to_media_item takes inner track dict (not playlist item wrapper) — caller must extract item["track"]
patterns_established:
  - PKCE OAuth flow pattern (generate_code_verifier + generate_code_challenge + build_authorize_url with S256) reusable for any future OAuth PKCE integration
  - Spotify state keys all prefixed with spotify_ to namespace within StateClient
observability_surfaces:
  - get_spotify_connection_status() returns {connected, display_name, product, token_expiry}
  - Structured loggers: spotify.auth (OAuth events), spotify.client (API diagnostics), spotify.poll (poll cycle summaries)
  - SpotifyAPIError(status_code, error_type, message) for API failures; SpotifyAuthError(message, status_code, response_body) for OAuth failures
  - HTTP 429 logged as warning with Retry-After value
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: SpotifyClient, OAuth PKCE auth, and pure converters

**Created spotify_service.py with PKCE OAuth flow, SpotifyClient API client, track-to-MediaItem converter, and 55 passing unit tests**

## What Happened

Built the complete Spotify service module following the established youtube_service.py and google-calendar/auth.py patterns. The module contains:

- **PKCE helpers** (`generate_code_verifier`, `generate_code_challenge`) using only stdlib (`secrets`, `hashlib`, `base64`) — RFC 7636 S256 method
- **OAuth functions** — authorize URL builder, code exchange with code_verifier, token refresh, refresh-if-expired with 5-minute buffer, token storage, connection status, clear auth — all following the Google Calendar pattern
- **SpotifyClient class** — async HTTP client with Bearer auth, GET /v1/me, /v1/me/playlists, /v1/playlists/{id}/tracks, dedicated 429 rate-limit handling
- **Pure converters** — `parse_spotify_url` (web URL + spotify: URI), `track_to_media_item` (maps all fields: title, artist→description, duration_ms→seconds, thumbnail, enclosureUrl, externalId, status=queued, mediaSource), `mint_source_iri`, `mint_item_iri`
- **Async SDK functions** — `subscribe_spotify`, `check_source_exists_spotify`, `get_existing_item_iris`

Token expiry is stored as timezone-aware UTC ISO 8601 string. Redirect URI is a function parameter (not hardcoded). Token values are never logged.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "Spotify or spotify or PKCE"` — 55 new tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` — all 294 tests pass (239 existing + 55 new), zero regressions
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/spotify_service.py').read())"` — module parses cleanly
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — app module unchanged, still parses

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "Spotify or spotify or PKCE"` | 0 | ✅ pass | 0.48s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` | 0 | ✅ pass | 0.55s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/spotify_service.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "connection_status or auth_error or rate_limit or SpotifyAPIError"` | 0 | ✅ pass | 0.28s |

### Slice-level checks (partial — T01 only)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | All tests pass (294 total) | ✅ pass | Exceeds expected count slightly (plan said ~240+80=320, actual is 239+55=294 — plan estimated higher new test count for T02) |
| 2 | poll-spotify task in manifest | ⏳ T02 | Not yet wired |
| 3 | Spotify section in template | ⏳ T02 | Not yet created |
| 4 | spotify_service.py parses cleanly | ✅ pass | |
| 5 | app.py parses cleanly | ✅ pass | |
| 6 | Failure-path diagnostic tests pass | ✅ pass | auth_error + rate_limit tests verified |

## Diagnostics

- **Connection status:** Call `get_spotify_connection_status(state_client)` — returns `{connected: bool, display_name, product, token_expiry}`
- **Loggers:** `spotify.auth` for OAuth flow events, `spotify.client` for API request diagnostics, `spotify.poll` for poll cycle summaries (used by T02)
- **Error shapes:** `SpotifyAPIError(status_code, error_type, message)` — raised on HTTP 4xx/5xx from Spotify API; `SpotifyAuthError(message, status_code, response_body)` — raised on token exchange/refresh failures
- **Rate limiting:** HTTP 429 responses log `Retry-After` header value as warning before raising `SpotifyAPIError`

## Deviations

- Renamed test class `TestTrackToMediaItem` → `TestSpotifyTrackToMediaItem` to avoid collision with the existing podcast `TestEntryToMediaItem` class
- Aliased `track_to_media_item` import as `track_to_media_item_sp` in tests to avoid shadowing the podcast `entry_to_media_item` binding
- Added 55 tests (plan estimated ~50) — the extra tests cover edge cases discovered during implementation (web URL with query params, non-playlist URIs, missing album images, etc.)

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/services/spotify_service.py` — new Spotify service module (~500 lines): PKCE helpers, OAuth flow, SpotifyClient, pure converters, async SDK functions
- `backend/tests/test_media_scheduler.py` — appended 55 Spotify test methods across 8 test classes
- `.gsd/milestones/M038/slices/S04/S04-PLAN.md` — added diagnostic verification step
- `.gsd/milestones/M038/slices/S04/tasks/T01-PLAN.md` — added Observability Impact section
