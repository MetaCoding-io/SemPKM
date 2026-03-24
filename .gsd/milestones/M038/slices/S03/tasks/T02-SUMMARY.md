---
id: T02
parent: S03
milestone: M038
provides:
  - poll-youtube task in manifest and app.py — queries YouTube sources, calls API, deduplicates, bulk-creates items
  - add-youtube POST route — validates URL + API key, creates MediaSource via subscribe_youtube
  - Two-section add-source template with podcast and YouTube forms using proxy-prefixed htmx URLs
key_files:
  - apps/media-scheduler/manifest.yaml
  - apps/media-scheduler/app.py
  - apps/media-scheduler/frontend/templates/add-source.html
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Alias youtube_service imports to avoid name collisions (yt_get_existing_item_iris, yt_mint_item_iri) — podcast_service already exports get_existing_item_iris at the app.py top-level
  - _update_youtube_source_state delegates to existing update_source_state from podcast_service — reuses the proven SPARQL update pattern instead of duplicating it
patterns_established:
  - poll_youtube follows same structure as poll_sources — query sources, iterate, try/except per source, bulk-create items, update source state on success/error
  - add_youtube_fragment follows same structure as add_podcast_fragment — form data extraction, URL validation, service call, HX-Trigger on success
observability_surfaces:
  - poll-youtube task handler logs sources queried, items created, quota consumed per run at INFO; errors at WARNING
  - add-youtube route logs validation failures and API errors at WARNING with error_type
  - Source error state (errorCount, lastError) updated per-source on failure — visible in sources list
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Wire YouTube into app, manifest, and templates

**Connected YouTube service to running app — registered poll-youtube task in manifest, added task handler and add-youtube route to app.py, expanded add-source template with YouTube form section, all 240 tests passing.**

## What Happened

Added `poll-youtube` task entry to `manifest.yaml` between `poll-sources` and `generate-plan`, matching the same interval (15m) and retry policy. Updated the manifest test assertion from 2→3 tasks.

Added a fourth `try/except` import block to `app.py` for `youtube_service`, following the identical importlib fallback pattern. Imported: `YOUTUBE_SOURCES_SPARQL`, `YouTubeAPIError`, `YouTubeClient`, `check_quota`, `increment_quota`, `parse_youtube_url`, `subscribe_youtube`, `video_to_media_item`, `mint_item_iri`, and `get_existing_item_iris` (both YouTube versions aliased with `yt_` prefix to avoid collision with podcast_service's identically-named exports).

The `poll_youtube` task handler follows the same structure as `poll_sources`: checks for API key in StateClient, checks daily quota, queries YouTube-type sources via `YOUTUBE_SOURCES_SPARQL`, iterates with per-source try/except, calls `YouTubeClient` methods (list_playlist_items + get_video_durations), deduplicates via IRI minting, bulk-creates items, and updates source state. On quota exceeded from the API, it breaks the loop (stops all remaining sources). On other errors, increments error count and continues.

The `add_youtube_fragment` POST route validates URL format via `parse_youtube_url()`, validates API key + resolves channel by delegating to `subscribe_youtube()`, catches `YouTubeAPIError` for clear user-facing error messages, and emits `HX-Trigger: sourcesChanged` on success.

Expanded `add-source.html` from a single form to two sections — podcast and YouTube — each in a `ms-add-section` wrapper with an `h4` heading, sharing the `#ms-add-result` div. Both forms use the `/app/media-scheduler/` proxy prefix on htmx URLs.

## Verification

- Full test suite: 240 passed, 0 failed
- `grep -q "poll-youtube" manifest.yaml` → pass
- `grep -q "add-youtube" app.py` → pass
- YAML manifest parses and contains poll-youtube task → pass
- htmx URL uses proxy prefix in template → pass
- 30 test classes (target ≥30)
- Failure-path tests (YouTubeAPIError, quota_exceeded, invalid) → 13 passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_media_scheduler.py -v` (full suite) | 0 | ✅ pass | 0.60s |
| 2 | `grep -q "poll-youtube" manifest.yaml` | 0 | ✅ pass | <0.1s |
| 3 | `grep -q "add-youtube" app.py` | 0 | ✅ pass | <0.1s |
| 4 | `python -c "import yaml; ... assert 'poll-youtube' in tasks"` | 0 | ✅ pass | <0.1s |
| 5 | `grep -q '/app/media-scheduler/_fragments/sources/add-youtube' add-source.html` | 0 | ✅ pass | <0.1s |
| 6 | `grep -c "class Test"` → 30 | 0 | ✅ pass | <0.1s |
| 7 | `pytest -k "YouTubeAPIError or quota_exceeded or invalid"` | 0 | ✅ pass | 0.28s |

## Diagnostics

- **poll-youtube logs**: grep for `poll-youtube complete:` in app logs to see per-run summary (sources polled, items created)
- **add-youtube errors**: grep for `add-youtube` in WARNING logs — includes URL format failures, API error types, and subscription failures
- **Source error state**: `errorCount` and `lastError` on YouTube MediaSource objects updated on each poll failure — queryable via SPARQL or visible in the sources list fragment
- **Quota tracking**: `ctx.state.get("youtube_quota_used")` shows daily quota consumption

## Deviations

- Aliased youtube_service's `get_existing_item_iris` as `yt_get_existing_item_iris` and `mint_item_iri` as `yt_mint_item_iri` to avoid name collision with podcast_service's identically-named exports already in app.py scope.
- Added `_update_youtube_source_state` helper that delegates to the existing `update_source_state` from podcast_service — avoids duplicating the SPARQL update logic.
- Updated `TestManifest.test_manifest_has_tasks` assertion from `len == 2` to `len == 3` and added the `poll-youtube` task ID check.

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/manifest.yaml` — added `poll-youtube` task entry (15m interval, same retry policy)
- `apps/media-scheduler/app.py` — added youtube_service import block, `poll_youtube` task handler, `_update_youtube_source_state` helper, `add_youtube_fragment` POST route
- `apps/media-scheduler/frontend/templates/add-source.html` — expanded from single form to two-section layout (podcast + YouTube) with shared result div
- `backend/tests/test_media_scheduler.py` — updated manifest task count assertion from 2→3
- `.gsd/milestones/M038/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
