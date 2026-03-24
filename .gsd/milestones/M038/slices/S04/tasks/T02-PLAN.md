---
estimated_steps: 7
estimated_files: 4
skills_used:
  - test
  - best-practices
---

# T02: App wiring — routes, poll task, template, manifest

**Slice:** S04 — Spotify Integration
**Milestone:** M038

## Description

Wire the Spotify service module (from T01) into the media-scheduler app: add the importlib fallback import block, create the `poll-spotify` task handler, add 6 fragment routes for the OAuth connect/disconnect flow and playlist subscription, update the add-source template with a Spotify section, and add the `poll-spotify` task to the manifest. Also add ~30 tests for the poll task, route handlers, and manifest validation.

This is mechanical wiring following the YouTube + Google Calendar patterns. The service logic is already built and tested — this task assembles it into the running app.

## Steps

1. **Read T01 output** to understand the exact function signatures:
   - `apps/media-scheduler/services/spotify_service.py` — all exported functions and constants
   - `apps/media-scheduler/app.py` — current state, look at youtube_service import block (lines ~85-110) for exact pattern
   - `apps/google-calendar/app.py` — OAuth route pattern: `initiate_oauth`, `oauth_callback`, `disconnect`, `_oauth_result_page`

2. **Add Spotify imports to `app.py`** using the try/except importlib fallback pattern:
   - Import from `services.spotify_service`: SPOTIFY_SOURCES_SPARQL, SpotifyAPIError, SpotifyAuthError, SpotifyClient, build_spotify_authorize_url, exchange_spotify_code, refresh_spotify_if_expired, store_spotify_tokens, get_spotify_connection_status, clear_spotify_auth, parse_spotify_url, track_to_media_item, subscribe_spotify, get_existing_item_iris as sp_get_existing_item_iris, mint_item_iri as sp_mint_item_iri, generate_code_verifier, generate_code_challenge
   - Fallback: importlib.util.spec_from_file_location pointing to `services/spotify_service.py`

3. **Add `poll_spotify` task handler** decorated with `@media_scheduler_app.task("poll-spotify")`:
   - Check connection: `get_spotify_connection_status(ctx.state)` → skip if not connected
   - Refresh token: `refresh_spotify_if_expired(ctx.http, ctx.state, client_id, client_secret)` — read client_id/client_secret from state
   - Query sources: `ctx.graph.query(SPOTIFY_SOURCES_SPARQL)` → loop bindings
   - For each source: create SpotifyClient, `get_playlist_tracks(external_id)`, dedup via `sp_get_existing_item_iris`, cap at MAX_INITIAL_ITEMS, `track_to_media_item` for each, bulk-create via `ctx.commands.bulk()`
   - Error handling: SpotifyAPIError caught per-source (increment errorCount), SpotifyAuthError breaks the loop (auth is shared)
   - Return summary dict: `{"sources_polled": N, "items_created": N}`

4. **Add 6 Spotify fragment routes** to `app.py`:
   - `/_fragments/spotify/connect` POST: read client_id + client_secret + redirect_uri from form, save to state, generate PKCE verifier+challenge, store verifier in state, build authorize URL, return 303 redirect. Use `generate_code_verifier()` and `generate_code_challenge()`.
   - `/_fragments/spotify/callback` GET: validate CSRF state, read code_verifier from state, call `exchange_spotify_code()`, create SpotifyClient with new access_token, call `get_user_profile()` to get display_name + product tier, call `store_spotify_tokens()`, clear oauth_state + code_verifier from state, return success HTML page (same `_oauth_result_page` pattern as Google Calendar).
   - `/_fragments/spotify/disconnect` POST: call `clear_spotify_auth(ctx.state)`, re-render add-source form.
   - `/_fragments/spotify/status` GET: call `get_spotify_connection_status(ctx.state)`, return JSON or HTML fragment with connected state.
   - `/_fragments/spotify/playlists` GET: check connection, refresh token, create SpotifyClient, call `get_playlists()`, render playlist list HTML for the selector dropdown.
   - `/_fragments/sources/add-spotify` POST: read playlist_id + playlist_name from form, call `subscribe_spotify(ctx, playlist_id, playlist_name)`, return success/duplicate HTML, emit `HX-Trigger: sourcesChanged`.

5. **Update `add-source.html`** — add Spotify section after YouTube section:
   - When disconnected: show form with client_id, client_secret, redirect_uri fields + "Connect Spotify" button that POSTs to `/_fragments/spotify/connect`
   - When connected: show display name + product tier, playlist selector (loaded via `hx-get="/_fragments/spotify/playlists"` with `hx-trigger="load"`), "Add Selected Playlist" button that POSTs to `/_fragments/sources/add-spotify`, and "Disconnect" button
   - All htmx URLs use `/app/media-scheduler/` proxy prefix per KNOWLEDGE.md
   - The template needs the `spotify_connected` and `spotify_status` context variables — add a helper in app.py that the `add_source_fragment` route calls before rendering

6. **Update `manifest.yaml`** — add `poll-spotify` task entry after `poll-youtube`:
   ```yaml
   - id: "poll-spotify"
     description: "Poll Spotify playlists for new tracks"
     interval: "15m"
     configurable: true
     retryPolicy:
       maxRetries: 2
       backoffMultiplier: 2
       maxBackoff: "5m"
   ```
   Also add `accounts.spotify.com` and `api.spotify.com` to network permissions (currently `"*"` so this is documentation-only, but correct for when permissions become granular).

7. **Add ~30 tests** to `backend/tests/test_media_scheduler.py`:
   - `TestPollSpotify` (8 tests): skips when not connected, skips when auth refresh fails, polls single source, dedup filters existing items, caps at MAX_INITIAL_ITEMS, handles SpotifyAPIError per-source, handles SpotifyAuthError breaks loop, returns summary dict
   - `TestSpotifyRoutes` (6 tests): connect route saves credentials and redirects, callback exchanges code with verifier, callback validates CSRF state, disconnect clears auth, add-spotify creates source, add-spotify duplicate returns info message
   - `TestManifestSpotify` (3 tests): manifest has poll-spotify task, manifest has correct interval, manifest network permissions cover Spotify domains
   - `TestAddSourceTemplate` (2 tests): template file contains "spotify" section, template uses proxy prefix URLs

## Must-Haves

- [ ] Import block uses try/except with importlib fallback (same pattern as youtube_service)
- [ ] All htmx URLs in template use `/app/media-scheduler/` proxy prefix
- [ ] Poll task checks connection before any API calls (skip if disconnected)
- [ ] Poll task refreshes token before creating SpotifyClient
- [ ] OAuth callback validates CSRF state parameter before exchanging code
- [ ] OAuth callback passes code_verifier to exchange function (PKCE)
- [ ] `_oauth_result_page` helper provides standalone HTML (user's browser lands here after redirect)
- [ ] Manifest has `poll-spotify` with 15m interval and retry policy
- [ ] Template shows different UI for connected vs disconnected state
- [ ] Existing podcast and YouTube tests still pass (no regressions)

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — all tests pass (existing + T01 + T02 = ~320 total)
- `python -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — app module parses cleanly
- `python -c "import yaml; m=yaml.safe_load(open('apps/media-scheduler/manifest.yaml')); tasks=[t['id'] for t in m['tasks']]; assert 'poll-spotify' in tasks"` — manifest has poll-spotify
- `grep -q 'spotify' apps/media-scheduler/frontend/templates/add-source.html` — Spotify section exists in template
- `grep -c '/app/media-scheduler/' apps/media-scheduler/frontend/templates/add-source.html` returns >= 5 (proxy-prefixed URLs)

## Observability Impact

- **New poll task logging:** `poll_spotify` task handler uses `spotify.poll` logger for cycle summaries (sources_polled, items_created), `spotify.auth` for token refresh events, `spotify.client` for per-source API calls. Same structured logging pattern as `poll_sources` and `poll_youtube`.
- **Connection status:** `get_spotify_connection_status()` callable from any route — returns `{connected, display_name, product, token_expiry}`. Used by the add-source template to render connected/disconnected state.
- **Per-source error tracking:** SpotifyAPIError increments `errorCount` and sets `lastError` on the source via `update_source_state()`. SpotifyAuthError (shared auth) breaks the poll loop and is visible in the task return summary.
- **OAuth flow tracing:** `spotify.auth` logger records token exchange success/failure, CSRF state validation, code_verifier usage, and token refresh cycles. Never logs token values.
- **Inspection:** Poll task returns `{"sources_polled": N, "items_created": N}` — logged by AppScheduler. Route handlers return HTML fragments with inline success/error status. Manifest `poll-spotify` task visible via standard task listing.

## Inputs

- `apps/media-scheduler/services/spotify_service.py` — T01 output: all Spotify service functions
- `apps/media-scheduler/app.py` — existing app with podcast + YouTube wiring
- `apps/media-scheduler/manifest.yaml` — existing manifest with poll-sources and poll-youtube tasks
- `apps/media-scheduler/frontend/templates/add-source.html` — existing template with Podcast + YouTube sections
- `apps/google-calendar/app.py` — OAuth route pattern reference
- `backend/tests/test_media_scheduler.py` — existing test file with T01 additions

## Expected Output

- `apps/media-scheduler/app.py` — updated with Spotify imports, poll-spotify task, 6 new routes
- `apps/media-scheduler/manifest.yaml` — updated with poll-spotify task
- `apps/media-scheduler/frontend/templates/add-source.html` — updated with Spotify section
- `backend/tests/test_media_scheduler.py` — updated with ~30 more tests
