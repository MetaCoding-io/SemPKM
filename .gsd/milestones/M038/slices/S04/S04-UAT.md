# S04: Spotify Integration — UAT Script

## Preconditions

- SemPKM Docker stack running (`docker compose up -d`)
- Media Scheduler app installed and visible in sidebar
- Spotify Developer account with a registered app (client ID + client secret)
- HTTPS redirect URI registered in Spotify developer portal (per D353)
- At least one Spotify playlist with tracks in the test account

---

## Test Cases

### TC-01: Connect Spotify Account (Happy Path)

1. Open Media Scheduler app from sidebar
2. Click "Add Source" to open the add-source panel
3. Scroll to the **Spotify** section — verify it shows the "disconnected" state: three input fields (Client ID, Client Secret, Redirect URI) and a "Connect to Spotify" button
4. Enter valid Spotify client ID, client secret, and the registered HTTPS redirect URI
5. Click "Connect to Spotify"
6. **Expected:** Browser performs a full-page redirect to Spotify's OAuth consent page (not an htmx partial swap)
7. Approve the consent prompt on Spotify
8. **Expected:** Browser redirects back to the callback URL. A standalone result page shows "Connected successfully" with the Spotify display name
9. Navigate back to the Media Scheduler app → Add Source
10. **Expected:** Spotify section now shows "connected" state: display name, product tier (Premium/Free), a playlist dropdown auto-populating, and a Disconnect button

### TC-02: Add Spotify Playlist as Media Source

1. Complete TC-01 (Spotify connected)
2. In the Spotify section, wait for the playlist dropdown to load (hx-trigger="load")
3. **Expected:** Dropdown contains playlists from the connected Spotify account
4. Select a playlist from the dropdown
5. Click "Add Source"
6. **Expected:** Success message. The playlist appears in the Media Sources list with sourceType "spotify"
7. Verify in SPARQL: `SELECT ?s WHERE { ?s a ms:MediaSource ; ms:sourceType "spotify" }` returns the new source

### TC-03: Duplicate Spotify Source Prevention

1. Complete TC-02 (one Spotify playlist added)
2. Attempt to add the same playlist again
3. **Expected:** Info message indicating the source already exists (not an error, not a duplicate created)

### TC-04: Poll Spotify Discovers Tracks

1. Complete TC-02 (Spotify source exists)
2. Trigger the `poll-spotify` scheduled task (via Admin > Applications > Media Scheduler > Tasks, or wait 15 minutes)
3. **Expected:** Poll returns `{sources_polled: 1, items_created: N}` where N > 0
4. Verify MediaItems exist: `SELECT ?item ?title WHERE { ?item a ms:MediaItem ; ms:mediaSource <source_iri> ; dcterms:title ?title }` returns tracks from the playlist
5. **Expected:** Each track has: title, description (artist name), duration (seconds), enclosureUrl (`spotify:track:{id}`), externalId, status "queued"

### TC-05: Spotify Track Deduplication

1. Complete TC-04 (tracks already polled)
2. Trigger `poll-spotify` again
3. **Expected:** Poll returns `{sources_polled: 1, items_created: 0}` — no duplicates created
4. Verify item count hasn't changed

### TC-06: Premium vs Free Tier Detection

1. Connect with a Spotify Premium account
2. Check connection status (Add Source → Spotify section)
3. **Expected:** Product tier shows "premium"
4. Disconnect and reconnect with a Spotify Free account (if available)
5. **Expected:** Product tier shows "open" or "free"

### TC-07: Disconnect Spotify

1. Complete TC-01 (Spotify connected)
2. Click "Disconnect" in the Spotify section
3. **Expected:** Spotify section returns to disconnected state (input fields + Connect button)
4. **Expected:** Existing Spotify media sources remain in the triplestore (disconnect doesn't delete sources)
5. Trigger `poll-spotify` — **Expected:** Returns `{skipped: "not_connected"}`

### TC-08: OAuth CSRF State Validation

1. Manually construct a callback URL with an invalid `state` parameter
2. Navigate to it
3. **Expected:** Error page saying "Invalid state parameter" — not a successful auth

### TC-09: Poll Spotify When Not Connected

1. Ensure Spotify is disconnected (or never connected)
2. Trigger `poll-spotify`
3. **Expected:** Returns `{skipped: "not_connected"}` — no errors, no API calls

### TC-10: Spotify API Rate Limiting

1. This is best verified via unit tests (TestSpotifyClient::test_429_rate_limit_raises_with_retry_info)
2. When Spotify returns HTTP 429, the client raises SpotifyAPIError with rate limit info
3. The poll task catches per-source SpotifyAPIError, increments errorCount on the source, and continues to next source
4. **Expected:** Rate-limited source gets errorCount incremented; other sources still poll successfully

### TC-11: Token Refresh on Expired Token

1. Connect Spotify account
2. Wait for token to expire (or manually set token_expiry to a past time in StateClient)
3. Trigger `poll-spotify`
4. **Expected:** Token refreshes automatically (5-minute buffer). Poll completes successfully.
5. If refresh fails (e.g., user revoked access on Spotify side): **Expected:** Returns `{skipped: "auth_refresh_failed"}`

### TC-12: Mixed Media Sources in Plan

1. Have at least one podcast source, one YouTube source, and one Spotify source — all with discovered items
2. Generate a daily plan (via schedule rules or manual trigger)
3. **Expected:** Plan entries include items from all three source types. Spotify items have `spotify:track:{id}` deep links.

---

## Edge Cases

- **Missing album art:** Spotify tracks without album images should still create MediaItems (thumbnail field omitted, not empty)
- **Podcast-only tracks in playlist:** Spotify playlists can contain podcast episodes — these should still be ingested as MediaItems with correct metadata
- **Empty playlist:** Adding a playlist with zero tracks creates the MediaSource. Next poll discovers nothing (items_created: 0). No error.
- **Invalid credentials:** Entering wrong client ID/secret → Spotify OAuth returns an error page. Callback may not fire. User can retry with correct credentials.
- **Network failure during poll:** HTTP errors from Spotify API are caught per-source. Other sources in the same poll cycle still process.
