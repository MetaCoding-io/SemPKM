---
id: T03
parent: S01
milestone: M038
provides:
  - poll-sources scheduled task handler with conditional GET, dedup, bulk creation, and error tracking
  - FeedFetchError exception, fetch_feed(), and parse_feed_content() in podcast_service.py
  - SOURCES_WITH_STATE_SPARQL filtered to podcast sourceType only
key_files:
  - apps/media-scheduler/app.py
  - apps/media-scheduler/services/podcast_service.py
key_decisions:
  - Used feedparser directly for parse_feed_content rather than importing from rss-reader — podcast feeds are always XML/RSS so the JSON Feed dispatch path isn't needed, keeping the dependency graph simpler
  - Added FILTER(?sourceType = "podcast") to SOURCES_WITH_STATE_SPARQL so poll-sources only processes podcast sources (YouTube/Spotify will have separate poll tasks in S03/S04)
patterns_established:
  - poll-sources follows identical structure to rss-reader's poll-feeds — SPARQL source query → conditional GET → feedparser parse → dedup → bulk create → state update
  - MAX_INITIAL_ITEMS = 50 cap per source per poll cycle (same constant as rss-reader's MAX_INITIAL_ARTICLES)
  - _get_current_error_count() helper for safe integer extraction from SPARQL bindings (same pattern as rss-reader)
observability_surfaces:
  - poll-sources returns {"feeds_polled": N, "items_created": N} dict logged by AppScheduler
  - Per-feed structured logging with URL, new item count, and skipped count
  - Feed-level error tracking via ms:errorCount increment and ms:lastError persistence on MediaSource objects
  - ms:lastPolled timestamp updated after every poll attempt (success or failure)
duration: 8m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Implement poll-sources task and episode discovery

**Implemented poll-sources task handler with conditional GET, feedparser-based RSS parsing, dedup against existing MediaItems, bulk creation via ctx.commands.bulk(), and per-source error tracking.**

## What Happened

Added the core integration for the media-scheduler app: the `poll-sources` scheduled task handler in `app.py` and supporting feed-fetching infrastructure in `podcast_service.py`.

The task handler queries all podcast-type MediaSource objects via a SPARQL query (now filtered with `FILTER(?sourceType = "podcast")`), fetches each source's RSS feed with conditional GET headers (ETag/Last-Modified), parses episodes via feedparser (which handles iTunes namespace extensions for `<enclosure>` and `<itunes:duration>`), deduplicates against existing MediaItem IRIs, and bulk-creates new items atomically via `ctx.commands.bulk()`. A `MAX_INITIAL_ITEMS = 50` cap prevents flooding on first poll of prolific feeds.

Three new functions were added to `podcast_service.py`: `FeedFetchError` (exception with url and status_code attributes), `fetch_feed()` (conditional GET with httpx-compatible client), and `parse_feed_content()` (delegates to feedparser for RSS/Atom XML). The existing `entry_to_media_item()` and `get_existing_item_iris()` from T02 are wired into the poll pipeline.

Error handling is per-feed: failures on one source don't block others. On error, `errorCount` is incremented and `lastError` is persisted on the source. On success, `errorCount` resets to 0 and `etag`/`lastModified` are saved for the next conditional GET.

## Verification

- All five mock-context functional tests pass: empty sources, normal poll (2 episodes), dedup (1 skipped), 304 Not Modified, HTTP error (errorCount increment)
- `podcast_service.py` loads and exports FeedFetchError, fetch_feed, parse_feed_content
- `app.py` loads and exports poll_sources task function with correct MAX_INITIAL_ITEMS = 50
- Slice-level checks pass: model manifest, ontology MediaSource class, app manifest validation
- `test_media_scheduler.py` doesn't exist yet (T04 scope) — expected

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import yaml; m=yaml.safe_load(open('models/media-scheduler/manifest.yaml')); assert m['modelId']=='media-scheduler'"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); assert any(n.get('@id','').endswith('MediaSource') for n in d['@graph'])"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && PYTHONPATH=sdk .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m=parse_app_manifest('../apps/media-scheduler/manifest.yaml'); assert m.appId=='media-scheduler'"` | 0 | ✅ pass | <1s |
| 4 | Mock-context functional tests (empty, normal poll, dedup, 304, HTTP error) | 0 | ✅ pass | <1s |
| 5 | podcast_service.py module loads with FeedFetchError, fetch_feed, parse_feed_content | 0 | ✅ pass | <1s |
| 6 | app.py module loads with poll_sources, MAX_INITIAL_ITEMS=50, _get_current_error_count | 0 | ✅ pass | <1s |

## Diagnostics

- Inspect poll task: `cd backend && PYTHONPATH=sdk .venv/bin/python -c "import importlib.util, pathlib; s=importlib.util.spec_from_file_location('a', pathlib.Path('../apps/media-scheduler/app.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.poll_sources, m.MAX_INITIAL_ITEMS)"`
- Inspect SPARQL filter: `grep -A 2 'FILTER' apps/media-scheduler/services/podcast_service.py`
- Test parse_feed_content: `cd backend && .venv/bin/python -c "import importlib.util, pathlib; s=importlib.util.spec_from_file_location('ps', pathlib.Path('../apps/media-scheduler/services/podcast_service.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); r=m.parse_feed_content(b'<rss><channel><item><title>Test</title></item></channel></rss>', 'application/xml'); print(len(r['entries']), 'entries')"`

## Deviations

- Plan step 1 listed `_parse_itunes_duration()` as a new function — T02 already implemented this as `parse_duration()` in podcast_service.py, so no new duration parser was needed.
- `parse_feed_content()` delegates directly to feedparser without JSON Feed dispatch — podcast feeds are always XML/RSS, so the rss-reader's JSON Feed path is unnecessary here.

## Known Issues

- `backend/tests/test_media_scheduler.py` does not exist yet — T04's scope to create comprehensive unit tests.
- feedparser was installed into the backend venv via `uv pip install feedparser` for local testing. It's already declared in `apps/media-scheduler/requirements.txt` for Docker runtime.

## Files Created/Modified

- `apps/media-scheduler/app.py` — Added poll-sources task handler, MAX_INITIAL_ITEMS constant, _get_current_error_count helper, expanded imports (FeedFetchError, fetch_feed, parse_feed_content, entry_to_media_item, get_existing_item_iris, update_source_state)
- `apps/media-scheduler/services/podcast_service.py` — Added FeedFetchError exception, fetch_feed() with conditional GET, parse_feed_content() via feedparser, FILTER clause in SOURCES_WITH_STATE_SPARQL, feedparser+io imports
