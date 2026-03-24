# S03: YouTube Integration — Research

## Summary

Targeted research. This slice follows the exact same poll-task pattern established in S01 for podcasts. The only new element is the YouTube Data API v3 client. No new Python dependencies — raw HTTP via `ctx.http` (consistent with all sync apps). The model already has `sourceType: "youtube"` in the sh:in enum, `ms:feedUrl` for the URL, and all MediaItem properties needed for video metadata.

## Recommendation

Build a `youtube_service.py` parallel to `podcast_service.py` with pure functions for URL parsing, IRI minting, and API response-to-MediaItem conversion, plus an async `YouTubeClient` class wrapping `ctx.http`. Add a `poll-youtube` scheduled task, a `/_fragments/sources/add-youtube` POST route, and update the add-source template with a YouTube section. Store the API key in `StateClient` (same pattern as Linear sync's `api_key`). Track quota usage in StateClient with daily reset.

## Implementation Landscape

### Files to Create

| File | Purpose |
|------|---------|
| `apps/media-scheduler/services/youtube_service.py` | YouTube API client, URL parsing, video-to-MediaItem conversion, quota tracking |

### Files to Modify

| File | Change |
|------|--------|
| `apps/media-scheduler/manifest.yaml` | Add `poll-youtube` scheduled task (15m interval, same retry policy) |
| `apps/media-scheduler/app.py` | Add `poll_youtube` task handler, `add_youtube_fragment` POST route, import youtube_service |
| `apps/media-scheduler/frontend/templates/add-source.html` | Add YouTube source form (channel URL or playlist URL + API key) |
| `apps/media-scheduler/frontend/templates/sources-list.html` | Already renders YouTube sources (badge class `ms-badge-youtube` exists) — no changes needed |
| `apps/media-scheduler/frontend/templates/main.html` | Possibly add API key settings link — or handle via add-source form |
| `apps/media-scheduler/frontend/static/styles.css` | YouTube badge color already exists from S01 (hardcoded hex per KNOWLEDGE) — verify |
| `backend/tests/test_media_scheduler.py` | Add test classes for YouTube service functions and poll-youtube task |

### Files Unchanged

- `models/media-scheduler/` — ontology, shapes, views all already support YouTube source type
- `apps/media-scheduler/services/podcast_service.py` — no changes, separate concern
- `apps/media-scheduler/services/rules_service.py` — no changes
- `apps/media-scheduler/services/plan_service.py` — already handles YouTube items (15-min default duration for youtube source type)

## Key Technical Details

### YouTube Data API v3 Endpoints

Three endpoints needed, all read-only (API key auth, no OAuth):

1. **Resolve channel → uploads playlist** (for channel URL sources):
   ```
   GET https://www.googleapis.com/youtube/v3/channels
     ?part=contentDetails&id={channelId}&key={API_KEY}
   ```
   Response: `items[0].contentDetails.relatedPlaylists.uploads` → playlist ID (e.g., `UU...`)
   
   For `@handle` URLs:
   ```
   GET https://www.googleapis.com/youtube/v3/channels
     ?part=contentDetails&forHandle={handle}&key={API_KEY}
   ```

2. **List playlist items** (video discovery — the core poll operation):
   ```
   GET https://www.googleapis.com/youtube/v3/playlistItems
     ?part=snippet,contentDetails&playlistId={playlistId}&maxResults=50&key={API_KEY}
   ```
   Response per item: `snippet.title`, `snippet.description`, `snippet.publishedAt`, `snippet.thumbnails.medium.url`, `snippet.resourceId.videoId`
   
   Pagination: `nextPageToken` field, pass as `pageToken` for next page. Cap at 1 page (50 items) per poll like podcast MAX_INITIAL_ITEMS.

3. **Get video durations** (batch — up to 50 IDs per request):
   ```
   GET https://www.googleapis.com/youtube/v3/videos
     ?part=contentDetails&id={id1,id2,...}&key={API_KEY}
   ```
   Response: `items[N].contentDetails.duration` → ISO 8601 duration (e.g., `PT4M13S`, `PT1H2M30S`)

### Quota Budget

- Default: 10,000 units/day per Google Cloud project
- Read operations: 1 unit each (channels.list, playlistItems.list, videos.list)
- Per YouTube source per poll: 1 (playlistItems.list) + 1 (videos.list for durations) = 2 units
- With 20 sources, polling every 15 minutes (96 polls/day): 20 × 2 × 96 = 3,840 units/day
- **Optimization**: only call videos.list for *new* items (after dedup). Most polls find 0 new items → 1 unit/source/poll. Realistic budget: ~2,000 units/day.
- Track usage in StateClient: `youtube_quota_used` (int), `youtube_quota_reset_date` (ISO date). Check before each API call; skip poll if approaching limit (configurable threshold, default 8,000).

### URL Parsing

Users provide one of:
- `https://www.youtube.com/channel/UCxxxxxx` → extract channel ID after `/channel/`
- `https://www.youtube.com/@handlename` → extract handle, resolve via `channels.list?forHandle=`
- `https://www.youtube.com/playlist?list=PLxxxxxx` → extract playlist ID from query param
- `https://www.youtube.com/c/ChannelName` → legacy custom URL, resolve via `channels.list?forUsername=`
- Raw channel ID (`UC...`) or playlist ID (`PL...`) → use directly

Store in MediaSource:
- `ms:feedUrl` = the original URL (for display)
- `ms:externalId` = resolved playlist ID (for polling — avoids re-resolving channel → uploads playlist each poll)

### ISO 8601 Duration Parsing

YouTube returns durations like `PT4M13S`, `PT1H2M30S`, `PT45S`, `PT1H`. Need a pure function:

```python
import re
def parse_iso8601_duration(raw: str) -> int | None:
    """Parse ISO 8601 duration to seconds. E.g., PT4M13S → 253."""
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', raw or '')
    if not m:
        return None
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + s
```

### MediaItem Mapping

| YouTube API field | MediaItem property |
|---|---|
| `snippet.title` | `dcterms:title` |
| `snippet.description` | `dcterms:description` |
| `snippet.publishedAt` | `dcterms:created` |
| `snippet.thumbnails.medium.url` | `ms:thumbnailUrl` |
| `snippet.resourceId.videoId` | `ms:externalId` |
| `https://www.youtube.com/watch?v={videoId}` (constructed) | `ms:enclosureUrl` |
| `contentDetails.duration` (from videos.list, parsed) | `ms:duration` |
| Fixed: `"queued"` | `ms:status` |
| Source IRI | `ms:mediaSource` |

IRI minting: `mint_item_iri(source_iri, video_id)` — reuses podcast_service pattern.

### API Key Storage

Follow Linear sync pattern:
- Store in `StateClient`: `await ctx.state.set("youtube_api_key", key)`
- Retrieve in poll task: `api_key = await ctx.state.get("youtube_api_key")`
- Subscribe route validates key by making a test `channels.list` call before saving
- Add-source form has an "API Key" field (only shown for YouTube tab, persisted once)

### Poll Task Structure

```
poll-youtube task:
1. api_key = await ctx.state.get("youtube_api_key")
   - if missing, log warning and skip
2. Check quota budget (youtube_quota_used < threshold)
3. SPARQL query: all MediaSource where sourceType = "youtube"
4. For each source:
   a. playlist_id = source's ms:externalId (pre-resolved)
   b. GET playlistItems.list(playlistId=playlist_id, maxResults=50)
   c. Dedup against existing items (get_existing_item_iris)
   d. For new items only: batch GET videos.list for durations
   e. Convert to MediaItem dicts, bulk-create via CommandClient
   f. Update source state (lastPolled, errorCount)
   g. Increment quota counter
```

### Error Handling

- **403 quotaExceeded**: log, set source error, stop polling remaining sources for this cycle
- **403 forbidden** (invalid key): log, set all YouTube source errors, don't retry
- **404 / empty items**: playlist deleted or private — log, increment error count
- **Network errors**: standard retry via task retryPolicy (manifest: maxRetries=2)

### Source Subscription Flow

1. User enters YouTube URL + API key in add-source form
2. POST `/_fragments/sources/add-youtube`
3. Parse URL → determine if channel or playlist
4. If channel: resolve to uploads playlist ID via channels.list (validates key + URL simultaneously)
5. If playlist: validate via playlistItems.list (1 item, validates both)
6. Create MediaSource via object.create with:
   - `sourceType: "youtube"`, `feedUrl: original_url`, `externalId: resolved_playlist_id`, `title: channel/playlist title`
7. Save API key to StateClient (if not already saved)
8. Return success HTML fragment with HX-Trigger: sourcesChanged

## Natural Task Seams

1. **T01: YouTube service module** — `youtube_service.py` with URL parsing, ISO 8601 duration parsing, API response-to-MediaItem conversion (pure functions), YouTubeClient class, quota tracking helpers. Unit tests for all pure functions.

2. **T02: App integration** — Add `poll-youtube` task to manifest, add task handler + subscribe route to `app.py`, update `add-source.html` template with YouTube form, tests for poll task handler and subscribe route.

3. **T03: Verification** — Run full test suite, verify manifest validates, verify SPARQL queries return YouTube items alongside podcast items.

T01 and T02 have a dependency (T02 imports from T01). T03 depends on both.

## Constraints

- No new Python dependencies — raw HTTP only, via `ctx.http` (HttpClient wraps httpx)
- YouTube API key required — poll task must gracefully skip when unconfigured
- Quota tracking is per-Google-Cloud-project, not per-source. One counter in StateClient.
- `search.list` costs 100 units — **never use it**. Always use `channels.list` + `playlistItems.list` (1 unit each).
- API responses use `nextPageToken` pagination. Cap at 1 page (50 items) per poll to stay within quota budget and match MAX_INITIAL_ITEMS pattern.
- The `playlistItems.list` response doesn't include video duration — that requires a separate `videos.list` call. Batch IDs (up to 50 per request) to minimize quota cost.
