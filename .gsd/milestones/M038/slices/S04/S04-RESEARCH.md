# S04: Spotify Integration — Research

## Summary

Spotify integration follows the proven two-slice pattern (podcast S01, YouTube S03): new service module with pure functions + API client class + subscribe flow, poll task in manifest, add-source route in app.py, form section in template, unit tests. The distinguishing factor is **OAuth 2.0 with PKCE** — a pattern the codebase has already implemented in `apps/google-calendar/services/auth.py` but not yet in the media-scheduler app. The OAuth flow is the riskiest component and should be built first.

**Depth calibration: Targeted.** OAuth is the one non-trivial piece. Playlist listing, track extraction, and media item creation are straightforward API calls following established patterns. The YouTube service (675 lines, 67 tests) is the structural template.

## Recommendation

Build in three tasks:

1. **T01: SpotifyClient + auth service** — OAuth 2.0 with PKCE flow (authorize URL builder, code exchange, token storage, token refresh, connection status), SpotifyClient class (playlist listing, track listing, user profile for Premium detection). This is the risk-bearing task. ~400 lines of service code + ~50 tests.

2. **T02: Poll task + subscribe flow + app wiring** — `poll-spotify` task handler, `subscribe_spotify()`, `/_fragments/sources/add-spotify` POST route, connect/disconnect routes, `add-source.html` Spotify section, manifest update. ~200 lines of app wiring + ~30 tests.

3. **T03: Verification** — Run all media-scheduler tests (should be 240 + ~80 new = ~320), verify manifest/model/template integrity, confirm the three-source pattern (podcast, YouTube, Spotify) is consistent.

## Implementation Landscape

### Files to Create

| File | Purpose |
|------|---------|
| `apps/media-scheduler/services/spotify_service.py` | Pure functions: URL parsing, track-to-MediaItem conversion, IRI minting. SpotifyClient class: OAuth flow, playlist listing, track listing, user profile. Auth helpers: authorize URL, code exchange, token refresh, connection status. |

### Files to Modify

| File | Change |
|------|--------|
| `apps/media-scheduler/app.py` | Add Spotify imports (aliased), `poll_spotify` task handler, 5 new routes: `add-spotify`, `spotify/connect`, `spotify/callback`, `spotify/disconnect`, `spotify/status` |
| `apps/media-scheduler/manifest.yaml` | Add `poll-spotify` task (15m interval), add `accounts.spotify.com` and `api.spotify.com` to network permissions |
| `apps/media-scheduler/frontend/templates/add-source.html` | Add Spotify section: connect button (when disconnected) or playlist selector + add button (when connected) |
| `backend/tests/test_media_scheduler.py` | Add ~80 tests: SpotifyURLParsing, SpotifyClient, SpotifyAuth, TrackToMediaItem, PollSpotify, SubscribeSpotify |

### Files to Read (Context Only)

| File | Why |
|------|-----|
| `apps/google-calendar/services/auth.py` | Reference OAuth implementation: `build_google_authorize_url`, `exchange_code`, `refresh_access_token`, `refresh_if_expired`, `store_auth_tokens`, `get_connection_status`, `clear_auth_state` |
| `apps/google-calendar/app.py` | Reference OAuth route wiring: `initiate_oauth`, `oauth_callback`, `disconnect`, `_oauth_result_page` |
| `apps/media-scheduler/services/youtube_service.py` | Structural template: client class, pure converters, subscribe flow, import aliasing pattern |

## Technical Findings

### 1. OAuth 2.0 Flow: Authorization Code + PKCE (Required)

Spotify requires Authorization Code flow with PKCE for all new apps (enforced since April 2025, mandatory since November 2025). Since the media-scheduler backend can store secrets, use the **confidential client** variant (client_id + client_secret + PKCE), which provides both secret-based and PKCE protection.

**OAuth endpoints:**
- Authorize: `https://accounts.spotify.com/authorize`
- Token exchange: `https://accounts.spotify.com/api/token`
- API base: `https://api.spotify.com/v1`

**PKCE addition over Google Calendar's flow:**
- Generate a `code_verifier` (43-128 char random string) and `code_challenge` (SHA-256 hash, base64url-encoded)
- Store `code_verifier` in StateClient alongside `oauth_state`
- Pass `code_challenge` + `code_challenge_method=S256` in authorize URL
- Pass `code_verifier` in token exchange POST body

The Google Calendar auth module handles: authorize URL building, code exchange, token storage, token refresh, expiry checking, connection status, auth state clearing. The Spotify auth follows the same shape with two additions: PKCE parameters and Spotify-specific scopes.

**Implementation:** All auth functions go in `spotify_service.py` (not a separate `auth.py`) to keep the module count down — the YouTube service proved that a single module per source type works well.

### 2. Redirect URI Constraint

Spotify banned `localhost` aliases (only `http://127.0.0.1` is allowed for loopback). The redirect URI must be:

```
http://127.0.0.1:3000/app/media-scheduler/_fragments/spotify/callback
```

NOT `http://localhost:3000/...`. This is different from Google Calendar which uses `http://localhost:3000/...`. The UI should show this exact URI for users to register in their Spotify Developer Dashboard.

### 3. Required Scopes

Minimal scopes for the media-scheduler use case:
- `playlist-read-private` — list user's playlists (private + public)
- `playlist-read-collaborative` — include collaborative playlists
- `user-read-playback-state` — detect Premium (check active devices)
- `user-read-private` — get user profile (display name, product tier)

Optional (Premium-only, not needed for v1):
- `user-modify-playback-state` — start/pause/skip playback
- `user-read-currently-playing` — get current track

For v1, we only need playlist browsing and Premium detection. Playback control is S05+ territory.

### 4. Premium Detection

The `GET /v1/me` endpoint returns a `product` field: `"premium"`, `"free"`, or `"open"`. This determines whether the app can offer playback controls (Premium) or only deep links (Free). Store the product tier in StateClient as `spotify_product` and check it before rendering playback UI.

### 5. SpotifyClient Class Shape

Follow YouTubeClient's pattern:
```
class SpotifyClient:
    __init__(http_client, access_token)
    _get(endpoint, params) → dict    # Bearer token auth
    get_user_profile() → dict        # GET /v1/me
    get_playlists(limit=50) → list   # GET /v1/me/playlists
    get_playlist_tracks(playlist_id, limit=100) → list  # GET /v1/playlists/{id}/tracks
```

No quota tracking needed — Spotify rate limits are per-IP (not daily quota), returning HTTP 429 with `Retry-After` header. Handle 429 with a simple retry-after delay.

### 6. Track-to-MediaItem Conversion

Spotify track objects → MediaItem properties:
- `track.name` → `dcterms:title`
- `track.duration_ms / 1000` → `ms:duration` (seconds, consistent with podcast/YouTube)
- `track.artists[0].name` → `dcterms:description` (artist name)
- `track.album.images[0].url` → `ms:thumbnailUrl`
- `track.external_urls.spotify` → `ms:enclosureUrl` (deep link)
- `track.id` → `ms:externalId`
- Source IRI → `ms:mediaSource`
- `"queued"` → `ms:status`

IRI minting: `mint_item_iri(source_iri, track_id)` — same SHA-256 pattern.

### 7. Subscribe Flow

Unlike podcast (RSS URL) and YouTube (channel/playlist URL + API key), Spotify subscription requires OAuth first:

1. User clicks "Connect Spotify" → app redirects to Spotify authorize URL
2. Spotify redirects back to callback → app exchanges code for tokens
3. App fetches user profile → stores email/product tier
4. Now "Add Spotify" section shows user's playlists (fetched via API)
5. User selects playlists → app creates MediaSource objects per playlist

This two-phase connect-then-add pattern matches Google Calendar's flow exactly.

### 8. Spotify URL Parsing

Spotify playlist URIs come in two forms:
- Web URL: `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`
- Spotify URI: `spotify:playlist:37i9dQZF1DXcBWIGoYBM5M`

The `parse_spotify_url()` function should handle both and extract the playlist ID. It's simpler than YouTube's 6-format parser.

### 9. Poll Task Pattern

The `poll-spotify` task mirrors `poll-youtube`:
1. Check OAuth connection status (skip if not connected)
2. Refresh token if expired (using `refresh_if_expired()` pattern from Google Calendar auth)
3. Query Spotify-type MediaSources from triplestore
4. For each source: fetch playlist tracks → dedup → bulk-create MediaItems
5. Update source state (lastPolled, errorCount)

The token refresh is the key difference from YouTube (which uses a static API key). The podcast `update_source_state()` function handles the SPARQL state update.

### 10. Manifest Network Permissions

Add to the `network` list in manifest.yaml:
- `accounts.spotify.com` — OAuth authorize/token endpoints
- `api.spotify.com` — Web API calls
- `i.scdn.co` — Spotify CDN (album art thumbnails, referenced but not fetched by the app)

Currently the manifest has `"*"` (unrestricted), so this is already covered. But if permissions become granular later, these are the required domains.

## Constraints

- **No new Python dependencies.** The Spotify integration uses raw HTTP via `ctx.http` (httpx), same as YouTube. PKCE code_challenge generation uses only `hashlib` and `secrets` from stdlib.
- **StateClient has no delete.** Clear auth state by setting keys to empty string (proven pattern in Google Calendar `clear_auth_state()`).
- **Token expiry comparison.** Must handle naive vs aware datetime comparison (KNOWLEDGE.md: SQLite naive datetimes pattern). Spotify token `expires_in` is seconds from now — compute expiry as `datetime.now(timezone.utc) + timedelta(seconds=expires_in)` and store as ISO 8601.
- **Test architecture.** Follow S03's importlib-based testing pattern. Spotify functions must be loaded via `importlib.util.spec_from_file_location`. Mock `httpx` responses for OAuth and API calls.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Spotify redirect URI must use `127.0.0.1`, not `localhost` | Low | Document in UI template; test confirms redirect URI format |
| Token refresh fails silently (expired refresh_token after 7 days without use) | Medium | Poll task checks connection status before API calls; log clear error on auth failure; user sees "Reconnect" prompt |
| Rate limiting (HTTP 429) on heavy playlist polling | Low | SpotifyClient handles 429 with `Retry-After` header; cap items per source; 15m poll interval is conservative |
| PKCE code_verifier stored in StateClient is accessible to other apps sharing the triplestore | Low | StateClient keys are scoped to `urn:sempkm:app:media-scheduler:state` graph; code_verifier is consumed immediately on callback |

## Don't Hand-Roll

- **OAuth state management:** Follow Google Calendar's `auth.py` pattern exactly — it handles CSRF state, token expiry comparison with timezone awareness, and the no-delete StateClient constraint.
- **PKCE code_challenge generation:** Use `secrets.token_urlsafe(32)` for code_verifier and `hashlib.sha256` + base64url for code_challenge. Don't implement custom base64url — use `base64.urlsafe_b64encode(...).rstrip(b"=").decode("ascii")`.
