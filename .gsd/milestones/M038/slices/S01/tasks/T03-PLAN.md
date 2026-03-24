---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T03: Implement poll-sources task and episode discovery

**Slice:** S01 — Mental Model + Podcast Sources
**Milestone:** M038

## Description

Implement the `poll-sources` scheduled task handler in `app.py` and add the supporting feed-fetching functions to `podcast_service.py`. This is the core integration — the task queries all podcast MediaSource objects, fetches their RSS feeds, parses episodes, deduplicates against existing MediaItems, and bulk-creates new items.

The pattern follows `apps/rss-reader/app.py`'s `poll_feeds()` task exactly:
1. Query all MediaSource objects with sourceType="podcast" and their conditional GET state (etag, lastModified)
2. For each source, call `fetch_feed()` with conditional GET headers
3. Parse the RSS content via `parse_feed_content()` (reusing the feedparser dispatch from rss-reader's feed_service)
4. Convert entries to MediaItem params via `entry_to_media_item()`
5. Query existing MediaItem IRIs for dedup
6. Bulk-create new items via `ctx.commands.bulk()`
7. Update source state (lastPolled, etag, errorCount, lastError)

Key difference from rss-reader: podcast episodes often have `<enclosure>` elements with audio URLs and `<itunes:duration>` metadata. `entry_to_media_item()` extracts these.

## Steps

1. Add feed-fetching functions to `apps/media-scheduler/services/podcast_service.py`:
   - `fetch_feed(http_client, url, etag, last_modified) -> tuple[bytes|None, dict, int]` — same conditional GET pattern as `apps/rss-reader/services/feed_service.py:fetch_feed()`. Sends If-None-Match/If-Modified-Since headers, returns (content, headers_dict, status_code). Raises `FeedFetchError` on 4xx/5xx.
   - `parse_feed_content(raw_bytes, content_type) -> dict` — dispatch XML to feedparser, JSON to JSON feed parser. Can import these directly from rss-reader's feed_service or reimplement (simpler to reimplement the feedparser call since it's one line: `feedparser.parse(io.BytesIO(raw_bytes))`).
   - `FeedFetchError` exception class with url and status_code attributes.
   - `_parse_itunes_duration(raw: str) -> int | None` — parses iTunes duration strings ("HH:MM:SS", "MM:SS", or raw seconds) to integer seconds. Returns None on parse failure.

2. Implement `@media_scheduler_app.task("poll-sources")` in `apps/media-scheduler/app.py`:
   - Query all podcast sources using `SOURCES_WITH_STATE_SPARQL` (filter sourceType="podcast")
   - For each source: try/except around fetch_feed + parse + dedup + create
   - Use `ctx.commands.bulk()` context manager for efficient batch creation
   - Cap at `MAX_INITIAL_ITEMS = 50` per source per poll cycle
   - Update source state after each feed (success: reset errorCount, save etag; failure: increment errorCount, save lastError)
   - Return summary dict: `{"feeds_polled": N, "items_created": N}`
   - Log structured info: "Polled {url}: {N} new items (skipped {M} existing)"

3. Update `SOURCES_WITH_STATE_SPARQL` in podcast_service.py to include a `FILTER(?sourceType = "podcast")` clause so the poll task only processes podcast sources (YouTube and Spotify sources will have their own poll tasks in S03/S04).

4. Add `_get_current_error_count(binding: dict) -> int` helper in app.py (same pattern as rss-reader) for extracting error count from SPARQL binding results with safe integer parsing.

## Must-Haves

- [ ] poll-sources task handler queries only podcast-type MediaSource objects
- [ ] Conditional GET via ETag/Last-Modified headers for efficient polling
- [ ] Deduplication: existing MediaItem IRIs are skipped (no duplicate creation)
- [ ] Bulk creation via ctx.commands.bulk() for atomicity
- [ ] Error handling: feed-level errors don't block other feeds, errorCount incremented on failure
- [ ] MAX_INITIAL_ITEMS cap (50) prevents flooding on first poll of a prolific feed
- [ ] Source state (lastPolled, etag, errorCount, lastError) updated after every poll attempt

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v -k "poll"` — poll-related tests pass (T04 writes these tests, but this task ensures the code is correct)
- The poll_sources function is importable and callable with a mock context

## Observability Impact

- Signals added/changed: poll-sources returns `{"feeds_polled": N, "items_created": N}` dict (logged by AppScheduler), per-feed logging with URL, item counts, and error details
- How a future agent inspects this: SPARQL query on MediaSource objects shows lastPolled, errorCount, lastError per source; app_task_runs table shows poll-sources execution history
- Failure state exposed: errorCount increments per feed, lastError stores the exception message, task run status is "error" if all feeds fail

## Inputs

- `apps/media-scheduler/app.py` — app entrypoint to add task handler to
- `apps/media-scheduler/services/podcast_service.py` — pure functions for IRI minting, entry conversion, dedup queries
- `apps/rss-reader/app.py` — reference pattern for poll_feeds() task implementation
- `apps/rss-reader/services/feed_service.py` — reference pattern for fetch_feed() and FeedFetchError

## Expected Output

- `apps/media-scheduler/app.py` — updated with poll-sources task handler
- `apps/media-scheduler/services/podcast_service.py` — updated with fetch_feed(), parse_feed_content(), FeedFetchError, _parse_itunes_duration()
