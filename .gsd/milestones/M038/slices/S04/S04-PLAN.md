# S04: Spotify Integration

**Goal:** Spotify OAuth 2.0 with PKCE works end-to-end: authorize → token exchange → token refresh → playlist listing → track-to-MediaItem conversion → poll task populates triplestore.
**Demo:** User clicks "Connect Spotify" in the Media Scheduler app, completes OAuth, selects playlists, and Spotify tracks appear as MediaItems alongside podcast episodes and YouTube videos.

## Must-Haves

- OAuth 2.0 Authorization Code + PKCE flow: authorize URL with code_challenge, code exchange with code_verifier, token storage, token refresh with 5-minute buffer, CSRF state validation
- SpotifyClient class with Bearer auth: user profile (Premium detection), playlist listing, playlist track listing, HTTP 429 retry-after handling
- Track-to-MediaItem pure conversion following YouTube service's pattern (deterministic IRI, same property namespace)
- Configurable redirect URI (HTTPS required per D353 — user must register URI in Spotify Developer Dashboard)
- `poll-spotify` scheduled task: check connection → refresh token → query Spotify sources → fetch tracks → dedup → bulk-create
- Subscribe flow: connect → OAuth → list playlists → user selects → create MediaSource per playlist
- Disconnect flow: clear all Spotify auth state
- Connection status endpoint for template rendering (connected/disconnected, display name, product tier)
- Add-source template Spotify section: connect button when disconnected, playlist selector when connected
- Unit tests covering: PKCE generation, URL parsing, track conversion, auth flow mocking, poll task, subscribe/disconnect

## Proof Level

- This slice proves: integration (real OAuth flow pattern, API client, scheduled polling)
- Real runtime required: yes (OAuth tokens need real Spotify API in production; unit tests mock HTTP)
- Human/UAT required: yes (Spotify OAuth requires human browser interaction for consent)

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — all tests pass (existing ~240 + ~80 new Spotify tests = ~320 total)
- `python -c "import yaml; m=yaml.safe_load(open('apps/media-scheduler/manifest.yaml')); tasks=[t['id'] for t in m['tasks']]; assert 'poll-spotify' in tasks"` — poll-spotify task in manifest
- `grep -q 'spotify' apps/media-scheduler/frontend/templates/add-source.html` — Spotify section in template
- `python -c "import ast; ast.parse(open('apps/media-scheduler/services/spotify_service.py').read())"` — service module parses cleanly
- `python -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — app module parses cleanly
- `cd backend && python -m pytest tests/test_media_scheduler.py -v -k "connection_status or auth_error or rate_limit or SpotifyAPIError"` — failure-path and diagnostic tests pass

## Observability / Diagnostics

- Runtime signals: structured logging with `spotify.auth`, `spotify.client`, `spotify.poll` logger names; log token refresh events, API errors, rate limits, poll cycle summaries
- Inspection surfaces: `get_spotify_connection_status()` returns connected/disconnected, display_name, product_tier, token_expiry; poll task returns summary dict
- Failure visibility: HTTP 429 with Retry-After logged as warning; token refresh failures logged with status code; poll errors increment source errorCount/lastError via existing `update_source_state()`
- Redaction constraints: never log access_token, refresh_token, client_secret, or code_verifier values — log only key names and status

## Integration Closure

- Upstream surfaces consumed: `podcast_service.py` (MS_NS, APP_NS, MEDIA_SOURCE_TYPE, MEDIA_ITEM_TYPE, update_source_state, unsubscribe_source, get_existing_item_iris), `youtube_service.py` (structural template for client/converter pattern), `google-calendar/services/auth.py` (OAuth flow pattern)
- New wiring introduced: `spotify_service.py` (new module), `poll-spotify` task handler, 6 new routes in `app.py`, Spotify section in `add-source.html`, `poll-spotify` in manifest
- What remains before the milestone is truly usable end-to-end: S05 (context-driven adaptation + mobile), S06 (stats + polish), S07 (integration verification)

## Tasks

- [x] **T01: SpotifyClient, OAuth PKCE auth, and pure converters** `est:2h`
  - Why: The service module is the risk-bearing work — OAuth PKCE is a new pattern for this codebase, and the SpotifyClient must handle Bearer auth, 429 rate limiting, and Premium detection. All pure functions and the async client must be built and tested before wiring into the app.
  - Files: `apps/media-scheduler/services/spotify_service.py`, `backend/tests/test_media_scheduler.py`
  - Do: Create `spotify_service.py` with: (1) PKCE helpers — `generate_code_verifier()` (secrets.token_urlsafe), `generate_code_challenge()` (SHA-256 + base64url). (2) OAuth functions — `build_spotify_authorize_url()`, `exchange_spotify_code()`, `refresh_spotify_token()`, `refresh_spotify_if_expired()`, `store_spotify_tokens()`, `get_spotify_connection_status()`, `clear_spotify_auth()`. Follow Google Calendar auth.py pattern but add code_verifier/code_challenge params. Use `http_client.post()` with `data={}` form body (not JSON). (3) SpotifyClient class — `__init__(http_client, access_token)`, `_get(endpoint, params)` with Bearer auth header, `_handle_rate_limit()` for 429 + Retry-After, `get_user_profile()` (GET /v1/me), `get_playlists(limit=50)` (GET /v1/me/playlists), `get_playlist_tracks(playlist_id, limit=100)` (GET /v1/playlists/{id}/tracks). (4) Pure converters — `parse_spotify_url(url)` (web URL + spotify: URI → playlist_id), `track_to_media_item(track, source_iri)` following youtube_service.video_to_media_item pattern. (5) SPARQL constant `SPOTIFY_SOURCES_SPARQL` filtering `sourceType = "spotify"`. (6) `subscribe_spotify()` and `check_source_exists_spotify()` async functions. (7) ~50 unit tests: PKCE generation, URL parsing, track conversion, mock HTTP for auth flow and API calls, connection status. Redirect URI is passed as parameter (configurable per D353). Token expiry stored as UTC ISO 8601 (KNOWLEDGE: naive datetime issue).
  - Verify: `cd backend && python -m pytest tests/test_media_scheduler.py -v -k "Spotify or spotify or PKCE"` — all new tests pass
  - Done when: `spotify_service.py` exists with all functions, parses without syntax errors, and all Spotify-related tests pass

- [ ] **T02: App wiring — routes, poll task, template, manifest** `est:1.5h`
  - Why: Wire the Spotify service into the media-scheduler app: add import block, poll-spotify task handler, 6 fragment routes for the OAuth connect/disconnect flow and playlist subscription, update the add-source template with a Spotify section, and add poll-spotify to manifest. This is mechanical wiring following the YouTube + Google Calendar patterns.
  - Files: `apps/media-scheduler/app.py`, `apps/media-scheduler/manifest.yaml`, `apps/media-scheduler/frontend/templates/add-source.html`, `backend/tests/test_media_scheduler.py`
  - Do: (1) Add importlib fallback block in app.py for spotify_service imports (same pattern as youtube_service block). Import: SPOTIFY_SOURCES_SPARQL, SpotifyClient, SpotifyAuthError, build_spotify_authorize_url, exchange_spotify_code, refresh_spotify_if_expired, store_spotify_tokens, get_spotify_connection_status, clear_spotify_auth, parse_spotify_url, track_to_media_item, subscribe_spotify, get_existing_item_iris as sp_get_existing_item_iris, mint_item_iri as sp_mint_item_iri. (2) Add `poll_spotify` task handler: check connection status → refresh token → query SPOTIFY_SOURCES_SPARQL → for each source fetch tracks → dedup → cap at MAX_INITIAL_ITEMS → bulk-create. Mirror poll_youtube structure. (3) Add 6 routes: `/_fragments/spotify/connect` POST (save credentials, build authorize URL, redirect), `/_fragments/spotify/callback` GET (exchange code with PKCE, fetch profile, store tokens), `/_fragments/spotify/disconnect` POST (clear auth), `/_fragments/spotify/status` GET (return connection status HTML), `/_fragments/sources/add-spotify` POST (create MediaSource from selected playlist), `/_fragments/spotify/playlists` GET (return playlist list HTML for selector). (4) Update add-source.html: add Spotify section with connect button (when disconnected) or playlist selector (when connected). Use htmx with `/app/media-scheduler/` proxy prefix per KNOWLEDGE.md. (5) Add `poll-spotify` task to manifest.yaml (15m interval, same retry policy). (6) Add ~30 tests for poll_spotify task handler, route handlers (mock ctx), and manifest validation.
  - Verify: `cd backend && python -m pytest tests/test_media_scheduler.py -v` — all tests pass (existing + new). `python -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — no syntax errors. `python -c "import yaml; m=yaml.safe_load(open('apps/media-scheduler/manifest.yaml')); assert 'poll-spotify' in [t['id'] for t in m['tasks']]"` — manifest has poll-spotify task.
  - Done when: All tests pass, app.py parses clean, manifest has poll-spotify, template has Spotify section, all 3 source types (podcast, YouTube, Spotify) have consistent subscribe/poll/template patterns

## Files Likely Touched

- `apps/media-scheduler/services/spotify_service.py` (new)
- `apps/media-scheduler/app.py`
- `apps/media-scheduler/manifest.yaml`
- `apps/media-scheduler/frontend/templates/add-source.html`
- `backend/tests/test_media_scheduler.py`
