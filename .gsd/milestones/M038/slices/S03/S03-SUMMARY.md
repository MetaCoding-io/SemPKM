---
id: S03
milestone: M038
title: "YouTube Integration"
status: done
completed_at: 2026-03-23
tasks_completed: [T01, T02]
duration_total: 40m
test_count_before: 173
test_count_after: 240
key_risks_retired:
  - "YouTube API quota — retired by proving quota tracking with daily reset, configurable threshold, and graceful skip on quota exhaustion"
---

# S03: YouTube Integration — Summary

## What This Slice Delivered

YouTube channels and playlists now work as media sources alongside podcasts. The user adds a YouTube URL (channel, @handle, playlist, or raw ID — 6 formats supported), the app validates the URL and API key against the live YouTube Data API v3, creates a MediaSource with `sourceType="youtube"`, and the `poll-youtube` scheduled task discovers new videos as MediaItems with titles, durations, thumbnails, and YouTube watch links.

## Architecture

### youtube_service.py (~675 lines)

Parallel to `podcast_service.py` — same layered architecture:

1. **Pure functions** (top): `parse_youtube_url()` (6 URL formats → type + ID), `parse_iso8601_duration()` (PT format → seconds), `video_to_media_item()` (API response → MediaItem dict)
2. **YouTubeClient class**: wraps `ctx.http` for 3 Data API v3 endpoints (channels.list, playlistItems.list, videos.list). `_get()` extracts structured `error_type` from YouTube's error response body for machine-readable failure classification.
3. **Quota tracking**: `check_quota()`, `increment_quota()`, `reset_quota_if_new_day()` — state stored in StateClient as `youtube_quota_used` + `youtube_quota_reset_date`. Daily reset at configurable threshold (default 10,000 units).
4. **Subscribe flow**: `subscribe_youtube()` validates URL + API key via test API call before creating MediaSource — fail-fast pattern matching podcast subscribe.

### App wiring (app.py + manifest)

- `poll-youtube` task in manifest (15m interval, same retry policy as `poll-sources`)
- Task handler: get API key → check quota → query YouTube-type sources → per-source try/except → YouTubeClient calls → dedup → bulk-create → update source state
- `/_fragments/sources/add-youtube` POST route: parse URL → validate via API → create MediaSource → HX-Trigger on success

### Template

`add-source.html` expanded from single form to two sections (Podcast + YouTube) with shared result div. Both forms use proxy-prefixed htmx URLs (`/app/media-scheduler/_fragments/...`).

## Key Patterns

- **Module independence**: youtube_service.py redefines `MS_NS`, `APP_NS`, `mint_source_iri()`, `mint_item_iri()` locally instead of importing from podcast_service. Constants are trivial strings — duplication is harmless, decoupling is valuable.
- **Import aliasing**: app.py aliases YouTube exports as `yt_get_existing_item_iris`, `yt_mint_item_iri` to avoid name collision with identically-named podcast_service exports.
- **Cross-service reuse**: `_update_youtube_source_state()` delegates to podcast_service's `update_source_state()` — same SPARQL update pattern, no duplication.
- **Structured error classification**: `YouTubeAPIError` carries `status_code`, `error_type`, `message` — downstream handlers branch on `error_type` (quotaExceeded, forbidden, notFound, playlistNotFound).

## Risk Retirement

**YouTube API quota (milestone key risk)**: Retired. Quota tracking stores daily usage in StateClient with automatic reset on new day. `check_quota()` returns boolean before any API call. `poll_youtube` breaks the source loop on quota exhaustion. 10 unit tests cover threshold boundary conditions, daily reset, and increment-from-zero paths.

## Test Coverage

- 7 new test classes: TestYouTubeURLParsing (20), TestISO8601Duration (15), TestVideoToMediaItem (10), TestYouTubeClient (12), TestYouTubeAPIError (4), TestQuotaTracking (10), TestSubscribeYouTube (6) = 67 new tests
- Total: 30 test classes, 240 tests, 0 regressions, 0.50s runtime
- Failure paths covered: invalid URLs, invalid API keys (403), quota exhaustion, network errors, duplicate sources, malformed API responses

## Observability

- `YouTubeAPIError` with structured `error_type` for machine-readable failure classification
- StateClient keys `youtube_quota_used` and `youtube_quota_reset_date` inspectable via state API
- Poll task logs: sources queried, items discovered, items deduplicated, quota consumed per run
- Per-source error state (`errorCount`, `lastError`) updated on poll failure — visible in sources list

## What S04 (Spotify) Should Know

- The MediaSource → poll → MediaItem pattern is now proven for two source types (podcast, YouTube). Spotify follows the same architecture: service module with pure functions + client class + subscribe flow, poll task in manifest, add-source route in app.py, form section in template.
- Import aliasing will be needed again if Spotify exports `get_existing_item_iris` or `mint_item_iri`.
- `update_source_state()` from podcast_service is the canonical SPARQL update helper — reuse it.
- Quota tracking pattern (StateClient keys with daily reset) is reusable if Spotify has API rate limits.

## Files Created/Modified

| File | Change |
|------|--------|
| `apps/media-scheduler/services/youtube_service.py` | New — 675 lines |
| `apps/media-scheduler/manifest.yaml` | Added `poll-youtube` task |
| `apps/media-scheduler/app.py` | Added YouTube imports, `poll_youtube` handler, `add_youtube_fragment` route |
| `apps/media-scheduler/frontend/templates/add-source.html` | Expanded to two-section form (podcast + YouTube) |
| `backend/tests/test_media_scheduler.py` | +67 tests across 7 new classes |
