---
estimated_steps: 4
estimated_files: 3
skills_used:
  - test
---

# T02: Wire YouTube into app, manifest, and templates

**Slice:** S03 — YouTube Integration
**Milestone:** M038

## Description

Connect the YouTube service module (from T01) into the running app — register the `poll-youtube` scheduled task in the manifest, add the task handler and subscribe route to `app.py`, and expand the add-source template with a YouTube form. This completes the user-facing demo: users can add YouTube sources and the poll task discovers videos.

## Steps

1. **Add `poll-youtube` task to manifest.** In `apps/media-scheduler/manifest.yaml`, add a second task entry under `tasks:`:
   ```yaml
   - id: "poll-youtube"
     description: "Poll YouTube sources for new videos"
     interval: "15m"
     configurable: true
     retryPolicy:
       maxRetries: 2
       backoffMultiplier: 2
       maxBackoff: "5m"
   ```
   This mirrors the existing `poll-sources` task exactly.

2. **Add YouTube imports and `poll_youtube` task handler to `app.py`.** Add a third `try/except` import block for `youtube_service` following the exact importlib fallback pattern used for `podcast_service` and `rules_service`. Import: `YouTubeClient`, `YouTubeAPIError`, `parse_youtube_url`, `video_to_media_item`, `subscribe_youtube`, `check_quota`, `increment_quota`, `get_existing_item_iris` (from youtube_service). Add a `YOUTUBE_SOURCES_SPARQL` query constant that selects MediaSource objects where `sourceType = "youtube"`, with OPTIONAL fields for `title`, `externalId` (the pre-resolved playlist ID), `errorCount`, `lastError`. Register `@media_scheduler_app.task("poll-youtube")` handler that:
   - Gets API key from `ctx.state.get("youtube_api_key")`; if missing, log warning and return `{"skipped": "no_api_key"}`
   - Checks quota via `check_quota(ctx.state)`; if over, log and return `{"skipped": "quota_exceeded"}`
   - Queries YouTube sources via `YOUTUBE_SOURCES_SPARQL`
   - For each source: creates `YouTubeClient(ctx.http, api_key)`, calls `list_playlist_items(playlist_id)`, deduplicates via `get_existing_item_iris()`, for new items calls `get_video_durations()` to get lengths, converts each to MediaItem via `video_to_media_item()`, bulk-creates via `ctx.commands.bulk()`, updates source state, increments quota
   - Catches `YouTubeAPIError` — on 403 quotaExceeded, stops polling remaining sources; on other errors, increments source error count and continues
   - Returns `{"sources_polled": N, "items_created": N}`

3. **Add `/_fragments/sources/add-youtube` POST route.** Register the route with `@media_scheduler_app.route("/_fragments/sources/add-youtube", methods=["POST"])`. Handler reads `youtube_url` and `api_key` from form data. Validates URL via `parse_youtube_url()` — returns error HTML if None. Calls `subscribe_youtube(ctx, youtube_url, api_key)` which validates the API key via a test API call, resolves channel→playlist, creates the MediaSource. On success, returns success HTML with `HX-Trigger: sourcesChanged`. On `YouTubeAPIError`, returns error HTML with the API message.

4. **Expand `add-source.html` with YouTube form.** Replace the current single podcast form with a two-section layout. Keep the podcast form as-is inside a `<div class="ms-add-section">` with a heading. Add a second section for YouTube with:
   - A `<input type="url" name="youtube_url" placeholder="YouTube channel or playlist URL">` 
   - A `<input type="text" name="api_key" placeholder="YouTube Data API key">` 
   - A submit button "Add YouTube Source"
   - Form action: `/app/media-scheduler/_fragments/sources/add-youtube` (htmx POST, target `#ms-add-result`)
   Use the same `ms-add-form` class and `ms-input`, `ms-btn` styling. The result div `#ms-add-result` is shared between both forms.

   Run the full test suite to confirm no regressions.

## Must-Haves

- [ ] `poll-youtube` task registered in manifest YAML and parses correctly
- [ ] `app.py` imports youtube_service with importlib fallback pattern
- [ ] `poll_youtube` task handler queries YouTube sources, calls API, deduplicates, bulk-creates items
- [ ] `/_fragments/sources/add-youtube` POST route validates URL + API key, creates MediaSource
- [ ] `add-source.html` has YouTube form section with proper `/app/media-scheduler/` proxy prefix on htmx URLs
- [ ] Full test suite passes with zero regressions

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — all tests pass
- `grep -q "poll-youtube" apps/media-scheduler/manifest.yaml` — task registered
- `grep -q "add-youtube" apps/media-scheduler/app.py` — route registered
- `python -c "import yaml; m=yaml.safe_load(open('apps/media-scheduler/manifest.yaml')); tasks=[t['id'] for t in m['tasks']]; assert 'poll-youtube' in tasks; print('OK')"` — manifest valid
- `grep -q '/app/media-scheduler/_fragments/sources/add-youtube' apps/media-scheduler/frontend/templates/add-source.html` — htmx URL uses proxy prefix

## Inputs

- `apps/media-scheduler/services/youtube_service.py` — T01 output: all YouTube functions and classes
- `apps/media-scheduler/manifest.yaml` — existing manifest to extend with poll-youtube task
- `apps/media-scheduler/app.py` — existing app module to extend with imports, task handler, and route
- `apps/media-scheduler/frontend/templates/add-source.html` — existing template to expand with YouTube form
- `backend/tests/test_media_scheduler.py` — test file with existing + T01 tests for regression check

## Expected Output

- `apps/media-scheduler/manifest.yaml` — updated with `poll-youtube` task entry
- `apps/media-scheduler/app.py` — extended with YouTube imports, SPARQL query, poll_youtube handler, add-youtube route
- `apps/media-scheduler/frontend/templates/add-source.html` — expanded with YouTube source form
