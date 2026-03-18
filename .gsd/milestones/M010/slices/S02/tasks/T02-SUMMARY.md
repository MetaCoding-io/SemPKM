---
id: T02
parent: S02
milestone: M010
provides:
  - fetch_feed() — async conditional GET with ETag/Last-Modified, returns (bytes|None, headers, status)
  - extract_article_content() — trafilatura-based markdown extraction with graceful fallback
  - FeedFetchError — exception carrying url and status_code for downstream error tracking
  - HAS_TRAFILATURA — runtime-inspectable flag for content extraction availability
key_files:
  - apps/rss-reader/services/feed_service.py
  - apps/rss-reader/requirements.txt
  - backend/tests/test_feed_service.py
key_decisions:
  - Return plain dict with normalized keys (etag, last_modified, content_type) from fetch_feed rather than raw httpx.Headers — cleaner downstream consumption
  - FeedFetchError as custom exception rather than re-raising httpx.HTTPStatusError — decouples from httpx internals, carries url + status_code attributes for per-feed error tracking
  - trafilatura import guard at module level (HAS_TRAFILATURA flag) — allows graceful degradation when dep not installed
patterns_established:
  - AsyncMock + MagicMock pattern for testing async http_client functions without real network
  - patch.object(_mod, "HAS_TRAFILATURA", ...) pattern for testing import guard branches
  - _mock_response() / _mock_http_client() test helpers for httpx-like response objects
observability_surfaces:
  - fetch_feed() logs INFO on 304 (conditional GET hit) and 200 (full fetch) with URL
  - fetch_feed() logs WARNING on HTTP errors before raising FeedFetchError
  - extract_article_content() logs DEBUG on success (URL + extracted length), WARNING on failure
  - FeedFetchError.url and .status_code available for callers to persist per-feed error tracking
  - feed_service.HAS_TRAFILATURA inspectable at runtime
duration: 12m
verification_result: passed
completed_at: 2026-03-18T14:27:00-04:00
blocker_discovered: false
---

# T02: Implement HTTP fetching with conditional GET and trafilatura content extraction

**Added fetch_feed() with conditional GET (ETag/Last-Modified) and extract_article_content() with trafilatura markdown extraction to feed_service.py; 31 cumulative tests pass.**

## What Happened

Added three components to `apps/rss-reader/services/feed_service.py`:

1. **`FeedFetchError`** — Exception class with `.url` and `.status_code` attributes, raised by `fetch_feed()` on HTTP 4xx/5xx. Enables per-feed error tracking in T03.

2. **`fetch_feed(http_client, url, etag, last_modified)`** — Async function that builds conditional GET headers (If-None-Match / If-Modified-Since) and calls `http_client.get()`. Returns a 3-tuple `(content, headers, status_code)` where content is `None` on 304 (cache hit), bytes on 200, and raises `FeedFetchError` on error. Response headers are returned as a plain dict with `etag`, `last_modified`, `content_type` keys.

3. **`extract_article_content(http_client, url)`** — Async function that fetches an article URL and extracts the main body as markdown via `trafilatura.extract()`. Uses a module-level `HAS_TRAFILATURA` flag with try/except import guard — returns `None` gracefully when trafilatura is not installed, HTTP fails, or extraction produces no output. Wrapped in a broad try/except for robustness.

Added `trafilatura>=2.0` to `apps/rss-reader/requirements.txt`. Added logging at INFO/WARNING/DEBUG levels for observability.

## Verification

- 31/31 tests pass in `test_feed_service.py` (18 existing from T01 + 13 new)
- 38/38 S01 tests pass in `test_rss_feed_parser.py` (zero regressions)
- Syntax checks pass for both `feed_service.py` and `app.py`
- `trafilatura>=2.0` present in requirements.txt

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_feed_service.py -v` | 0 | ✅ pass | 0.10s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v` | 0 | ✅ pass | 0.26s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('OK')"` | 0 | ✅ pass | <1s |
| 5 | `grep trafilatura apps/rss-reader/requirements.txt` | 0 | ✅ pass | <1s |

## Diagnostics

- `fetch_feed()` returns `(None, headers, 304)` on conditional GET hit — callers check `content is None` to skip parsing
- `FeedFetchError` carries `.url` and `.status_code` — T03's `update_subscription_state()` will persist these as lastError/errorCount
- `feed_service.HAS_TRAFILATURA` flag is `True`/`False` at module level — inspectable to check whether content extraction is available
- All 13 new tests use `AsyncMock`/`MagicMock` — no real network calls

## Deviations

None. Implementation follows the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/services/feed_service.py` — added FeedFetchError, fetch_feed(), extract_article_content(), trafilatura import guard, logging
- `apps/rss-reader/requirements.txt` — added trafilatura>=2.0
- `backend/tests/test_feed_service.py` — added 13 new tests (8 fetch_feed, 5 extract_article_content) for 31 cumulative
