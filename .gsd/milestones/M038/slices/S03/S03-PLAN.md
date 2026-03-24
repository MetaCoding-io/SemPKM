# S03: YouTube Integration

**Goal:** YouTube channels and playlists work as media sources alongside podcasts — users add a YouTube URL, the app polls YouTube Data API v3 for new videos, and discovered videos appear as MediaItems in the daily plan.
**Demo:** User enters a YouTube channel or playlist URL with an API key in the add-source form, the source appears in the sources list with a "youtube" badge, and after polling, discovered videos show as MediaItem objects in the Episodes tab with titles, durations, and YouTube watch links.

## Must-Haves

- `youtube_service.py` with URL parsing (channel, playlist, @handle formats), ISO 8601 duration parsing, API response-to-MediaItem conversion, YouTubeClient class, and quota tracking helpers
- `poll-youtube` scheduled task in manifest and app.py that queries YouTube-type sources and discovers new videos via Data API v3
- `/_fragments/sources/add-youtube` POST route that validates the URL + API key, resolves channel → uploads playlist, creates the MediaSource
- Updated `add-source.html` template with a YouTube source form (URL + API key fields)
- API key stored in StateClient; poll task gracefully skips when unconfigured
- Quota tracking in StateClient with daily reset and configurable threshold
- Unit tests for all pure functions and async handlers

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — all existing tests still pass plus new YouTube test classes pass
- `grep -c "class Test" backend/tests/test_media_scheduler.py` returns at least 30 (current 23 + 7+ new)
- `grep -q "poll-youtube" apps/media-scheduler/manifest.yaml` — task registered
- `grep -q "add-youtube" apps/media-scheduler/app.py` — route registered
- `python -c "import yaml; m=yaml.safe_load(open('apps/media-scheduler/manifest.yaml')); tasks=[t['id'] for t in m['tasks']]; assert 'poll-youtube' in tasks"` — manifest parses and contains task

## Tasks

- [ ] **T01: YouTube service module with unit tests** `est:1h`
  - Why: All YouTube-specific logic (URL parsing, API client, response conversion, quota tracking) lives in a single service module parallel to `podcast_service.py`. Pure functions need thorough unit tests before wiring into the app.
  - Files: `apps/media-scheduler/services/youtube_service.py`, `backend/tests/test_media_scheduler.py`
  - Do: Create `youtube_service.py` with: URL parsing for 5 formats (channel ID, @handle, playlist URL, /c/ URL, raw IDs), `parse_iso8601_duration()`, `video_to_media_item()` conversion, `YouTubeClient` class wrapping `ctx.http` with methods for `resolve_channel()`, `list_playlist_items()`, `get_video_durations()`, quota tracking helpers (`check_quota()`, `increment_quota()`, `reset_quota_if_new_day()`), `get_existing_item_iris()` reusing the podcast pattern, `subscribe_youtube()` and `unsubscribe_source()` async functions. Add 7+ test classes covering URL parsing, duration parsing, video-to-item conversion, IRI minting, quota tracking, subscribe flow, and poll logic.
  - Verify: `cd backend && python -m pytest tests/test_media_scheduler.py -v -k "YouTube or youtube"` — all new tests pass
  - Done when: All YouTube pure functions are tested, YouTubeClient methods have mock-based tests, and the module imports cleanly

- [ ] **T02: Wire YouTube into app, manifest, and templates** `est:45m`
  - Why: Connects the YouTube service to the running app — registers the poll task, subscribe route, and adds the YouTube form to the UI. This completes the slice's user-facing demo.
  - Files: `apps/media-scheduler/manifest.yaml`, `apps/media-scheduler/app.py`, `apps/media-scheduler/frontend/templates/add-source.html`
  - Do: Add `poll-youtube` task to manifest (15m interval, same retry policy as poll-sources). Add YouTube service imports to app.py using the same importlib fallback pattern. Add `poll_youtube` task handler that: gets API key from StateClient, checks quota, queries YouTube-type sources via SPARQL, calls YouTubeClient methods, deduplicates, bulk-creates items. Add `/_fragments/sources/add-youtube` POST route that parses URL, validates via API test call, creates MediaSource with sourceType="youtube" and externalId=resolved playlist ID. Expand `add-source.html` with a tabbed/sectioned form for YouTube (URL input + API key input). Run full test suite to verify no regressions.
  - Verify: `cd backend && python -m pytest tests/test_media_scheduler.py -v` — all tests pass (existing + new); `grep -q "poll-youtube" apps/media-scheduler/manifest.yaml` succeeds
  - Done when: Manifest has `poll-youtube` task, app.py has the task handler and subscribe route, add-source template has the YouTube form, full test suite passes

## Files Likely Touched

- `apps/media-scheduler/services/youtube_service.py` (new)
- `apps/media-scheduler/manifest.yaml`
- `apps/media-scheduler/app.py`
- `apps/media-scheduler/frontend/templates/add-source.html`
- `backend/tests/test_media_scheduler.py`
