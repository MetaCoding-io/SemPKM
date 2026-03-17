---
id: T02
parent: S02
milestone: M010
provides:
  - "fetch_feed() — async conditional GET for feed URLs with ETag/Last-Modified support"
  - "extract_article_content() — trafilatura-based full article extraction with graceful fallback"
  - "FeedFetchError — exception carrying url and status_code for downstream error tracking"
  - "HAS_TRAFILATURA — module-level flag for runtime trafilatura availability detection"
key_files:
  - apps/rss-reader/services/feed_service.py
  - apps/rss-reader/requirements.txt
  - backend/tests/test_feed_service.py
key_decisions:
  - "FeedFetchError custom exception over re-raising httpx.HTTPStatusError — cleaner API surface with .url and .status_code attrs for T03's error tracking"
  - "trafilatura import guard at module level (try/except + HAS_TRAFILATURA flag) — extraction degrades gracefully to None when not installed"
patterns_established:
  - "AsyncMock + MagicMock pattern for http_client testing — _make_mock_response() and _make_mock_http_client() helpers reusable in T03/T04 tests"
  - "patch.object(_mod, 'HAS_TRAFILATURA', ...) for testing import guard paths without actually uninstalling packages"
observability_surfaces:
  - "fetch_feed() logs INFO on 304 (conditional GET hit) and 200 (full fetch) with URL"
  - "fetch_feed() logs WARNING on HTTP errors before raising FeedFetchError"
  - "extract_article_content() logs DEBUG on success/None result, WARNING on exceptions"
  - "FeedFetchError.url and .status_code available for T03's per-feed error persistence"
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Implement HTTP fetching with conditional GET and trafilatura content extraction

**Added fetch_feed() with conditional GET (ETag/Last-Modified) and extract_article_content() via trafilatura, with 14 new tests (34 cumulative passing)**

## What Happened

Added three new exports to `feed_service.py`:

1. **`FeedFetchError`** — exception class with `.url` and `.status_code` attributes, raised on 4xx/5xx responses. Provides clean error info for T03's per-feed error tracking.

2. **`async fetch_feed(http_client, url, etag?, last_modified?)`** — builds conditional GET headers (If-None-Match, If-Modified-Since) when provided, calls `http_client.get()` with `follow_redirects=True`. Returns `(None, headers, 304)` on not-modified, `(content_bytes, headers, status)` on success, raises `FeedFetchError` on errors. Response headers are normalized to a clean dict with keys `etag`, `last_modified`, `content_type`.

3. **`async extract_article_content(http_client, url)`** — fetches article URL, runs `trafilatura.extract()` for markdown output. Returns `None` gracefully on: trafilatura not installed, HTTP error, extraction failure, or any exception. Module-level `HAS_TRAFILATURA` flag guards the import.

Also added `trafilatura>=2.0` to `apps/rss-reader/requirements.txt`.

## Verification

- `pytest tests/test_feed_service.py -v` — **34 tests passed** (20 from T01 + 14 new)
  - 9 fetch_feed tests: conditional headers sent/omitted, 304 returns None, 200 returns content+headers, 404/500 raise FeedFetchError, follow_redirects passed
  - 5 extract_article_content tests: success extraction, no-trafilatura guard, HTTP error, extraction failure, unexpected exception
- `pytest tests/test_rss_feed_parser.py -v` — **23 S01 tests pass** (zero regressions)
- `grep trafilatura apps/rss-reader/requirements.txt` — present
- `ast.parse(feed_service.py)` — syntax valid
- `ast.parse(app.py)` — syntax valid
- `services/__init__.py` exists — package intact

### Slice-level verification status (T02 is task 2 of 4):
- ✅ `pytest tests/test_feed_service.py -v` — 34 tests pass (target ≥35 at slice end)
- ✅ `pytest tests/test_rss_feed_parser.py -v` — 23 S01 tests pass
- ✅ `ast.parse(feed_service.py)` — OK
- ✅ `ast.parse(app.py)` — OK
- ✅ `services/__init__.py` exists
- ⏳ error tracking tests (T03)
- ⏳ conditional GET integration in poll_feeds (T03)

## Diagnostics

- `feed_service.HAS_TRAFILATURA` — check at runtime whether trafilatura is available
- `FeedFetchError` instances carry `.url` and `.status_code` — T03 will persist these to subscription objects
- Logging: `logging.getLogger("apps.rss-reader.services.feed_service")` at INFO (fetch outcomes) and WARNING (errors)
- Test helpers `_make_mock_response()` / `_make_mock_http_client()` in test file can be reused by T03/T04 tests

## Deviations

- Plan called for ≥9 new tests; implemented 14 (added both-headers test, no-conditional-headers test, 500 error test, follow_redirects test, exception-returns-none test) for more thorough coverage.
- Required `feedparser` and SDK packages to be installed in .venv via `uv pip install` — the worktree .venv didn't have them pre-installed.

## Known Issues

- None

## Files Created/Modified

- `apps/rss-reader/services/feed_service.py` — added trafilatura import guard, FeedFetchError, fetch_feed(), extract_article_content() with structured logging
- `apps/rss-reader/requirements.txt` — added `trafilatura>=2.0`
- `backend/tests/test_feed_service.py` — added 14 async tests for fetch_feed and extract_article_content with mock helpers
- `.gsd/milestones/M010/slices/S02/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
