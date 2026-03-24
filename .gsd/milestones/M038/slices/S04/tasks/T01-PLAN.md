---
estimated_steps: 7
estimated_files: 2
skills_used:
  - test
  - best-practices
---

# T01: SpotifyClient, OAuth PKCE auth, and pure converters

**Slice:** S04 — Spotify Integration
**Milestone:** M038

## Description

Create the `spotify_service.py` module containing all Spotify-specific logic: OAuth 2.0 Authorization Code + PKCE flow helpers, SpotifyClient async API client, pure converter functions (URL parsing, track→MediaItem), and SPARQL query constants. Also add ~50 unit tests to the existing test file.

This is the risk-bearing task — PKCE is a new auth pattern for this codebase, and the Spotify API client must handle Bearer auth, 429 rate limiting, and the unique Spotify data shapes. All functions must be testable with mocked HTTP.

## Steps

1. **Read reference files** for pattern consistency:
   - `apps/media-scheduler/services/youtube_service.py` — structural template for client class, pure converters, constants, subscribe flow
   - `apps/google-calendar/services/auth.py` — OAuth flow pattern: authorize URL builder, code exchange, token storage, token refresh, connection status, clear state
   - `apps/media-scheduler/services/podcast_service.py` — shared constants (MS_NS, APP_NS, MEDIA_SOURCE_TYPE, MEDIA_ITEM_TYPE)

2. **Create `apps/media-scheduler/services/spotify_service.py`** with these sections:
   - **Constants:** Reuse MS_NS, APP_NS, MEDIA_SOURCE_TYPE, MEDIA_ITEM_TYPE from podcast_service. Add SPOTIFY_API_BASE = `https://api.spotify.com/v1`, SPOTIFY_AUTHORIZE_URL = `https://accounts.spotify.com/authorize`, SPOTIFY_TOKEN_URL = `https://accounts.spotify.com/api/token`. Add SPOTIFY_SCOPES = `"playlist-read-private playlist-read-collaborative user-read-playback-state user-read-private"`. Add AUTH_STATE_KEYS tuple for all Spotify-specific state keys. Add SPOTIFY_SOURCES_SPARQL (same pattern as YOUTUBE_SOURCES_SPARQL but filter `sourceType = "spotify"`).
   - **Exception:** `SpotifyAPIError(status_code, error_type, message)` — same shape as YouTubeAPIError. `SpotifyAuthError(message, status_code, response_body)` — same shape as GCalAuthError.
   - **PKCE helpers:** `generate_code_verifier()` → `secrets.token_urlsafe(32)`. `generate_code_challenge(verifier)` → SHA-256 hash, base64url-encode, strip `=` padding. Use only stdlib (`secrets`, `hashlib`, `base64`).
   - **OAuth functions:** `build_spotify_authorize_url(client_id, redirect_uri, state, code_challenge)` — includes `code_challenge_method=S256`, scopes, `response_type=code`. `exchange_spotify_code(http_client, code, client_id, client_secret, redirect_uri, code_verifier)` — POST form data to token endpoint with `grant_type=authorization_code`. `refresh_spotify_token(http_client, refresh_token, client_id, client_secret)` — POST form data with `grant_type=refresh_token`. `refresh_spotify_if_expired(http_client, state_client, client_id, client_secret)` — check token_expiry with 5-min buffer, refresh if needed (same pattern as Google Calendar's `refresh_if_expired`). `store_spotify_tokens(state_client, access_token, refresh_token, expires_in, display_name, product)` — store all auth state. `get_spotify_connection_status(state_client)` → dict with connected, display_name, product, token_expiry. `clear_spotify_auth(state_client)` — set all auth keys to empty string.
   - **SpotifyClient class:** `__init__(http_client, access_token)`. `_get(endpoint, params)` — Bearer token in Authorization header, handle 429 with Retry-After (log warning, raise SpotifyAPIError). `get_user_profile()` — GET /v1/me, returns dict. `get_playlists(limit=50)` — GET /v1/me/playlists, returns list of playlist dicts. `get_playlist_tracks(playlist_id, limit=100)` — GET /v1/playlists/{id}/tracks, returns list of track item dicts.
   - **Pure converters:** `parse_spotify_url(url)` — handle `https://open.spotify.com/playlist/{id}` and `spotify:playlist:{id}`, return `{"type": "playlist", "value": playlist_id}` or None. `track_to_media_item(track, source_iri)` — map Spotify track fields to MediaItem properties following `video_to_media_item` pattern. `mint_source_iri(feed_url)` and `mint_item_iri(source_iri, track_id)` — same SHA-256 pattern.
   - **Async SDK functions:** `subscribe_spotify(ctx, playlist_id, playlist_name)` — create MediaSource via ctx.commands.execute. `check_source_exists_spotify(graph_client, playlist_id)` — SPARQL check. `get_existing_item_iris(graph_client, source_iri)` — same pattern as YouTube.

3. **Add ~50 unit tests** to `backend/tests/test_media_scheduler.py`:
   - `TestPKCEGeneration` (4 tests): verifier length/charset, challenge is base64url, deterministic challenge from same verifier, no padding chars
   - `TestSpotifyURLParsing` (6 tests): web URL, spotify URI, invalid URL, None, non-playlist URL, album URL returns None
   - `TestTrackToMediaItem` (6 tests): basic conversion, duration_ms → seconds, artist name, thumbnail, external_id, IRI determinism
   - `TestSpotifyIRIMinting` (4 tests): deterministic, different inputs differ, correct prefix, item IRI from source+track
   - `TestSpotifyAuth` (8 tests): build authorize URL has all params + code_challenge, exchange code sends correct form data, refresh token, refresh_if_expired skips when valid, refresh_if_expired refreshes when expired, store tokens, get connection status connected, get connection status disconnected
   - `TestSpotifyClient` (8 tests): get_user_profile success, get_playlists success, get_playlist_tracks success, API error raises SpotifyAPIError, 429 raises with retry info, empty playlists, missing fields handled, bearer token in header
   - `TestSubscribeSpotify` (4 tests): creates source, duplicate returns existing, source IRI format correct, playlist name stored as title
   - `TestSpotifyConnectionStatus` (4 tests): connected state, disconnected state, clear auth sets all empty, product tier stored

4. **Verify** the module parses cleanly and all tests pass.

## Must-Haves

- [ ] PKCE code_verifier uses `secrets.token_urlsafe(32)` (43 chars), code_challenge uses SHA-256 + base64url without padding
- [ ] OAuth token expiry stored as UTC ISO 8601 string (timezone-aware — no naive datetime bugs per KNOWLEDGE.md)
- [ ] SpotifyClient uses Bearer token auth header, not query param
- [ ] HTTP 429 handling logs Retry-After header value as warning
- [ ] `track_to_media_item` maps all fields: title, description (artist), duration (ms→s), thumbnail, enclosureUrl (spotify external URL), externalId, status="queued", mediaSource
- [ ] Never log token values — only log key names and status
- [ ] All state keys cleared to empty string (StateClient has no delete — per Google Calendar pattern)
- [ ] Redirect URI is a function parameter, not hardcoded (D353: HTTPS required, varies by deployment)
- [ ] Tests use importlib.util.spec_from_file_location pattern to load the module (consistent with existing test architecture)

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v -k "Spotify or spotify or PKCE"` — all ~50 new tests pass
- `python -c "import ast; ast.parse(open('apps/media-scheduler/services/spotify_service.py').read())"` — module parses cleanly
- Existing tests still pass: `cd backend && python -m pytest tests/test_media_scheduler.py -v` — no regressions

## Inputs

- `apps/media-scheduler/services/youtube_service.py` — structural template for client class, converter, constants
- `apps/google-calendar/services/auth.py` — OAuth flow pattern (authorize, exchange, refresh, store, status, clear)
- `apps/media-scheduler/services/podcast_service.py` — shared constants (MS_NS, APP_NS, type IRIs)
- `backend/tests/test_media_scheduler.py` — existing test file to append to

## Expected Output

- `apps/media-scheduler/services/spotify_service.py` — new service module (~400 lines)
- `backend/tests/test_media_scheduler.py` — updated with ~50 new Spotify test methods
