---
estimated_steps: 5
estimated_files: 2
skills_used:
  - test
---

# T01: YouTube service module with unit tests

**Slice:** S03 — YouTube Integration
**Milestone:** M038

## Description

Create `youtube_service.py` as a parallel module to `podcast_service.py`, containing all YouTube-specific logic: URL parsing, YouTube Data API v3 client, response-to-MediaItem conversion, ISO 8601 duration parsing, quota tracking, and subscription management. Add comprehensive unit tests following the exact patterns established in S01's test classes.

The module follows the same architecture as `podcast_service.py`: pure functions at the top (no SDK dependency), async/SDK-dependent functions below, all sharing the same `MS_NS`, `APP_NS`, `MEDIA_SOURCE_TYPE`, `MEDIA_ITEM_TYPE` constants.

## Steps

1. **Create `youtube_service.py` with constants and URL parsing.** Import `MS_NS`, `APP_NS`, `MEDIA_SOURCE_TYPE`, `MEDIA_ITEM_TYPE` from `podcast_service` (or redefine — the constants are simple strings). Implement `parse_youtube_url(url: str) -> dict` that returns `{"type": "channel_id"|"handle"|"playlist"|"custom"|"raw_channel"|"raw_playlist", "value": str}` for these URL formats:
   - `https://www.youtube.com/channel/UCxxxxxx` → `{"type": "channel_id", "value": "UCxxxxxx"}`
   - `https://www.youtube.com/@handlename` → `{"type": "handle", "value": "handlename"}`
   - `https://www.youtube.com/playlist?list=PLxxxxxx` → `{"type": "playlist", "value": "PLxxxxxx"}`
   - `https://www.youtube.com/c/ChannelName` → `{"type": "custom", "value": "ChannelName"}`
   - Raw `UC...` or `PL...` → detect by prefix
   - Return `None` for unrecognized URLs.

2. **Add ISO 8601 duration parsing and video-to-item conversion.** Implement `parse_iso8601_duration(raw: str) -> int | None` using regex `r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'`. Implement `video_to_media_item(video: dict, source_iri: str) -> dict` that maps YouTube API fields to MediaItem properties exactly as specified in the S03 research (title→dcterms:title, description→dcterms:description, publishedAt→dcterms:created, thumbnails.medium.url→ms:thumbnailUrl, videoId→ms:externalId, constructed watch URL→ms:enclosureUrl, parsed duration→ms:duration, status="queued", mediaSource=source_iri). Use `mint_item_iri(source_iri, video_id)` from `podcast_service` for IRI minting.

3. **Add `YouTubeClient` class and quota tracking.** Create `YouTubeClient` class that takes `http_client` and `api_key`. Methods:
   - `async resolve_channel(channel_id=None, handle=None, username=None) -> str` — returns uploads playlist ID via `channels.list` API
   - `async list_playlist_items(playlist_id: str, max_results: int = 50) -> list[dict]` — returns video snippets from `playlistItems.list`
   - `async get_video_durations(video_ids: list[str]) -> dict[str, int]` — batch `videos.list` call, returns `{video_id: seconds}`
   All methods raise `YouTubeAPIError(status_code, error_type, message)` on API errors.
   
   Add quota helpers as module-level async functions:
   - `async check_quota(state_client, threshold=8000) -> bool` — reads `youtube_quota_used` + `youtube_quota_reset_date`, resets if new day, returns True if under threshold
   - `async increment_quota(state_client, units: int)` — adds to running count
   - `async reset_quota_if_new_day(state_client)` — checks date, resets if needed

4. **Add subscribe/get_existing helpers.** Implement `subscribe_youtube(ctx, url: str, api_key: str) -> dict` that: parses URL, creates YouTubeClient, resolves channel→playlist if needed (validating both URL and API key), creates MediaSource via `object.create` with `sourceType="youtube"`, `feedUrl=original_url`, `externalId=resolved_playlist_id`, saves API key to StateClient if not already saved. Returns `{"status": "created"|"duplicate", "iri": ...}`. Add `get_existing_item_iris()` function parallel to podcast_service's version (or import it — same SPARQL pattern).

5. **Add unit tests.** In `backend/tests/test_media_scheduler.py`, add these test classes following the exact mock patterns from the existing S01 tests (importlib-based module loading, patching on `_app_mod`):
   - `TestYouTubeURLParsing` — test all 5+ URL formats plus edge cases (None, empty, invalid)
   - `TestISO8601Duration` — test PT4M13S, PT1H2M30S, PT45S, PT1H, empty, None, invalid
   - `TestVideoToMediaItem` — test full field mapping, missing fields, IRI determinism
   - `TestYouTubeClient` — mock HTTP responses for resolve_channel, list_playlist_items, get_video_durations, test error handling (403 quota, 404, network)
   - `TestQuotaTracking` — test check/increment/reset with mock StateClient
   - `TestSubscribeYouTube` — test create flow, duplicate detection, invalid URL, API key validation failure
   - `TestYouTubeAPIError` — test exception attributes

## Must-Haves

- [ ] `parse_youtube_url()` handles all 5 URL formats plus raw IDs and returns None for invalid
- [ ] `parse_iso8601_duration()` converts PT4M13S→253, PT1H2M30S→3750, PT45S→45, returns None for invalid
- [ ] `video_to_media_item()` maps all YouTube API fields to correct RDF properties with deterministic IRI
- [ ] `YouTubeClient` class with 3 async methods wrapping the correct API endpoints
- [ ] Quota tracking helpers with daily reset logic
- [ ] `subscribe_youtube()` validates URL + API key via test API call before creating source
- [ ] `YouTubeAPIError` exception class with status_code, error_type, message
- [ ] All new test classes pass: `pytest -k "YouTube or youtube or ISO8601 or Quota"` 

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v -k "YouTube or youtube or ISO8601 or Quota"` — all new tests pass
- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — no regressions in existing tests
- `python -c "from pathlib import Path; exec(Path('apps/media-scheduler/services/youtube_service.py').read_text())"` — module has no syntax errors

## Inputs

- `apps/media-scheduler/services/podcast_service.py` — pattern reference for IRI minting, constants, module structure, pure/async function separation
- `backend/tests/test_media_scheduler.py` — existing test file to append to, mock patterns to follow

## Expected Output

- `apps/media-scheduler/services/youtube_service.py` — complete YouTube service module (~400-500 lines)
- `backend/tests/test_media_scheduler.py` — extended with 7+ YouTube test classes (~300-400 new lines)
