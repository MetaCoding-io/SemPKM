---
id: S04
milestone: M038
title: "Spotify Integration"
status: done
started: 2026-03-23
completed: 2026-03-23
tasks_completed: 2
tasks_total: 2
test_count: 321
test_pass: 321
test_fail: 0
---

# S04: Spotify Integration — Summary

## What This Slice Delivered

Full Spotify integration for the media-scheduler app: OAuth 2.0 with PKCE authorization, token management, playlist discovery, track-to-MediaItem conversion, and scheduled polling. Users connect their Spotify account, select playlists as media sources, and Spotify tracks appear alongside podcast episodes and YouTube videos as MediaItems in the triplestore.

## Key Components

### spotify_service.py (~500 lines)
- **PKCE helpers** — `generate_code_verifier()` (secrets.token_urlsafe) + `generate_code_challenge()` (SHA-256 + base64url, S256 method) per RFC 7636
- **OAuth functions** — authorize URL builder, code exchange with code_verifier, token refresh with 5-minute expiry buffer, token storage as UTC ISO 8601, connection status, clear auth. Follows Google Calendar auth.py pattern.
- **SpotifyClient class** — async HTTP client with Bearer auth for GET /v1/me, /v1/me/playlists, /v1/playlists/{id}/tracks. Dedicated HTTP 429 rate-limit handling (logs Retry-After as warning).
- **Pure converters** — `parse_spotify_url()` (web URLs + spotify: URIs → playlist_id), `track_to_media_item()` (maps title, artist→description, duration_ms→seconds, thumbnail, enclosureUrl, externalId, status=queued). Deterministic IRI minting matching podcast/YouTube patterns.
- **Async SDK functions** — `subscribe_spotify()`, `check_source_exists_spotify()`, `get_existing_item_iris()`
- **Custom exceptions** — `SpotifyAPIError(status_code, error_type, message)`, `SpotifyAuthError(message, status_code, response_body)`

### App Wiring (app.py)
- **poll_spotify task handler** — check connection → refresh token → query SPOTIFY_SOURCES_SPARQL → fetch tracks per source → dedup → cap at MAX_INITIAL_ITEMS → bulk-create. Per-source error isolation (SpotifyAPIError increments errorCount). SpotifyAuthError breaks loop.
- **6 fragment routes:**
  - `/_fragments/spotify/connect` POST — saves credentials + PKCE verifier, 303 redirect to Spotify OAuth
  - `/_fragments/spotify/callback` GET — CSRF state validation, code exchange with PKCE verifier, profile fetch, token storage
  - `/_fragments/spotify/disconnect` POST — clears all auth + credential state
  - `/_fragments/spotify/status` GET — connection status HTML fragment
  - `/_fragments/spotify/playlists` GET — refreshes token, returns playlist `<option>` elements
  - `/_fragments/sources/add-spotify` POST — creates MediaSource from selected playlist

### Template (add-source.html)
- Spotify section with two states: disconnected (client_id/secret/redirect_uri form + Connect button with hx-boost=false for full-page OAuth redirect) and connected (display name + product tier, playlist `<select>` auto-populated via hx-get with hx-trigger=load, Add Source + Disconnect buttons). All htmx URLs use `/app/media-scheduler/` proxy prefix.

### Manifest
- `poll-spotify` task added with 15-minute interval and retry policy matching poll-youtube.

## Test Coverage

321 total tests (294 pre-existing + 27 new T02 wiring tests). T01 contributed 55 Spotify service tests. Breakdown:

- PKCE generation (verifier length, challenge format, S256)
- OAuth URL construction, code exchange, token refresh, auth errors
- SpotifyClient HTTP calls, rate limiting (429 + Retry-After), profile/playlists/tracks
- Track-to-MediaItem conversion (full mapping, edge cases: missing album art, no ID, etc.)
- URL parsing (web URLs with query params, spotify: URIs, non-playlist URIs)
- Subscribe/dedup/connection status
- Poll task (skip conditions, single source, dedup, cap, per-source error, auth error breaks loop)
- Route handlers (OAuth result pages, connect saves credentials, callback validates CSRF, disconnect clears, add-spotify creates source)
- Manifest (poll-spotify present, 15m interval, network permissions cover Spotify)
- Template (Spotify section, proxy-prefix URLs, connect form, playlist selector, disconnect button)

## Patterns Established

1. **PKCE OAuth flow** — First PKCE implementation in this codebase (Google Calendar uses standard OAuth). Pattern: generate code_verifier → store in StateClient → send code_challenge (S256) in authorize URL → pass code_verifier in token exchange → clear verifier after callback. Reusable for any future PKCE-requiring integration.

2. **importlib mock patching** — When testing poll tasks that import service modules via importlib fallback, patch exception classes on `_app_mod` (the app module), not on the service module directly. importlib creates separate module instances with distinct class identities, so `isinstance()` checks fail if you patch the "wrong" module's classes.

3. **OAuth consent redirect** — htmx intercepts 303 redirects by default. Use `hx-boost="false"` on forms that need full-page redirects to external OAuth providers.

## Observability

- **Loggers:** `spotify.auth` (OAuth events, token refresh), `spotify.client` (API request diagnostics, rate limits), `spotify.poll` (poll cycle summaries, per-source errors)
- **Connection status:** `get_spotify_connection_status(state_client)` → `{connected, display_name, product, token_expiry}`
- **Poll returns:** `{sources_polled, items_created}` on success, `{skipped: "not_connected"|"no_credentials"|"auth_refresh_failed"}` on skip
- **Error tracking:** per-source errorCount/lastError via `update_source_state()`
- **Redaction:** access_token, refresh_token, client_secret, code_verifier never logged

## Risk Retirement

**Spotify OAuth 2.0 with PKCE through App SDK** (milestone key risk) — retired. Token exchange, playlist listing, and Premium detection are proven with unit tests. Real Spotify API interaction requires human OAuth consent (UAT verification).

## What S05 Should Know

- Spotify tokens are in StateClient under `spotify_access_token`, `spotify_refresh_token`, `spotify_token_expiry` keys. Credentials under `spotify_client_id`, `spotify_client_secret`, `spotify_redirect_uri`.
- Deep link format is `spotify:track:{id}` (stored as `enclosureUrl` on MediaItems).
- `get_spotify_connection_status()` tells you if Spotify is connected and the user's product tier (Premium/Free).
- Premium detection is stored in connection status — S05 can use `product == "premium"` to decide whether to show playback control hints vs plain deep links.
- `poll_spotify` runs every 15 minutes alongside `poll-sources` (podcasts) and `poll-youtube`.

## Deviations from Plan

- T01 produced 55 tests (plan estimated ~50) — extra edge cases discovered during implementation
- T02 added `uuid` and `RedirectResponse` imports to app.py (not in plan, needed for OAuth)
- Test class aliasing: `TestSpotifyTrackToMediaItem` (not `TestTrackToMediaItem`) to avoid collision with podcast tests
- Spotify credentials stored under explicit state keys (plan didn't specify naming)

## Known Issues

- Pre-existing: `poll_youtube` in app.py has a minor indentation issue on the `candidate_iri` line (cosmetic, not introduced by this slice)
