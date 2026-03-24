---
id: T01
parent: S03
milestone: M038
provides:
  - youtube_service.py module with URL parsing, ISO 8601 duration, YouTubeClient, quota tracking, subscribe flow
  - 7 new test classes (67 tests) covering all YouTube service functions
key_files:
  - apps/media-scheduler/services/youtube_service.py
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Redefine MS_NS/APP_NS constants locally rather than import from podcast_service — keeps modules independent
  - YouTubeClient._get() extracts error_type from YouTube's structured error response for machine-readable failure classification
  - Thumbnail fallback: medium → high → default (YouTube API returns multiple sizes)
patterns_established:
  - YouTubeClient class wraps ctx.http for YouTube Data API v3 — same pattern as podcast_service's fetch_feed but object-oriented for multi-endpoint API
  - Quota tracking via StateClient keys youtube_quota_used + youtube_quota_reset_date with daily auto-reset
  - subscribe_youtube validates URL + API key via test API call before creating MediaSource — fail-fast pattern
observability_surfaces:
  - YouTubeAPIError with status_code, error_type, message for structured error handling
  - Logging at INFO for API calls (endpoint, quota cost, result count) and WARNING for quota limits and API errors
  - StateClient keys youtube_quota_used and youtube_quota_reset_date for quota inspection
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: YouTube service module with unit tests

**Created youtube_service.py with URL parsing (6 formats), ISO 8601 duration parser, YouTubeClient class wrapping Data API v3, quota tracking helpers, and subscribe flow — plus 7 test classes (67 tests) all passing with zero regressions.**

## What Happened

Built `apps/media-scheduler/services/youtube_service.py` as a parallel module to `podcast_service.py`. The module follows the same architecture: pure functions at the top (URL parsing, duration conversion, video-to-MediaItem mapping), then an async `YouTubeClient` class wrapping the HTTP client for three YouTube Data API v3 endpoints (channels, playlistItems, videos), quota tracking helpers with daily reset via StateClient, and an async `subscribe_youtube()` function that validates both URL format and API key before creating the MediaSource.

Added 7 test classes to `backend/tests/test_media_scheduler.py` using the same importlib-based module loading pattern: TestYouTubeURLParsing (20 tests), TestISO8601Duration (15 tests), TestVideoToMediaItem (10 tests), TestYouTubeClient (12 tests), TestYouTubeAPIError (4 tests), TestQuotaTracking (10 tests), TestSubscribeYouTube (6 tests). Total test count went from 23 classes / 173 tests to 30 classes / 240 tests.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "YouTube or youtube or ISO8601 or Quota"` — 67 passed
- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` — 240 passed, 0 regressions
- `grep -c "class Test" backend/tests/test_media_scheduler.py` — 30 (target: ≥30)
- `python3 -c "from pathlib import Path; exec(Path('apps/media-scheduler/services/youtube_service.py').read_text())"` — no syntax errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest -v -k "YouTube or youtube or ISO8601 or Quota"` | 0 | ✅ pass | 0.45s |
| 2 | `pytest -v` (full suite) | 0 | ✅ pass | 0.48s |
| 3 | `grep -c "class Test"` → 30 | 0 | ✅ pass | <0.1s |
| 4 | `python3 -c exec(youtube_service.py)` | 0 | ✅ pass | <0.1s |
| 5 | `pytest -v -k "YouTubeAPIError or invalid"` (failure paths) | 0 | ✅ pass | 0.28s |

## Diagnostics

- **Quota state**: Inspect via `StateClient.get("youtube_quota_used")` and `StateClient.get("youtube_quota_reset_date")` — these are the two keys the quota helpers read/write
- **Error classification**: `YouTubeAPIError.error_type` distinguishes `quotaExceeded`, `forbidden`, `notFound`, `playlistNotFound` etc. — downstream handlers can branch on this
- **Logging**: Module logger `youtube_service` at INFO level shows API request outcomes and quota consumption; DEBUG shows individual quota increments

## Deviations

- Redefined `MS_NS`, `APP_NS`, `MEDIA_SOURCE_TYPE`, `MEDIA_ITEM_TYPE` constants locally instead of importing from podcast_service — keeps the modules decoupled and avoids a circular dependency risk. The constants are trivial strings so duplication is harmless.
- Added `mint_source_iri()` and `mint_item_iri()` locally rather than importing — same reason, and the implementations are identical (SHA-256 hash, same prefix pattern).

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/services/youtube_service.py` — new YouTube service module (~480 lines) with URL parsing, ISO 8601 duration, video-to-MediaItem conversion, YouTubeClient class, quota tracking, subscribe flow
- `backend/tests/test_media_scheduler.py` — extended with 7 YouTube test classes (~400 new lines, 67 new tests)
- `.gsd/milestones/M038/slices/S03/S03-PLAN.md` — added Observability/Diagnostics section, failure-path verification check, marked T01 done
