---
estimated_steps: 5
estimated_files: 3
---

# T02: Implement HTTP fetching with conditional GET and trafilatura content extraction

**Slice:** S02 — Feed service + content extraction + feed management
**Milestone:** M010

## Description

Add the HTTP-layer functions to `feed_service.py`: `fetch_feed()` for feed fetching with conditional GET (ETag/Last-Modified), and `extract_article_content()` for full article body extraction via trafilatura. These are the I/O boundary functions that T03's poll-feeds refactor depends on. Also adds `trafilatura>=2.0` to requirements.txt with a try/except import guard.

`fetch_feed()` replaces S01's `feedparser.parse(url)` which bypasses SDK domain enforcement. By separating fetch from parse, we ensure all HTTP goes through `ctx.http.get()` (which enforces the app's `network` permission).

**Relevant skills:** test (for pytest patterns)

## Steps

1. Add `trafilatura>=2.0` to `apps/rss-reader/requirements.txt` (after the existing `feedparser>=6.0` line).

2. Add the following async functions to `apps/rss-reader/services/feed_service.py`:

   **`async def fetch_feed(http_client, url: str, etag: str | None = None, last_modified: str | None = None) -> tuple[bytes | None, dict, int]`**
   - Build request headers dict. If `etag` is not None, add `"If-None-Match": etag`. If `last_modified` is not None, add `"If-Modified-Since": last_modified`.
   - Call `await http_client.get(url, headers=headers, follow_redirects=True)`.
   - If status_code == 304, return `(None, response_headers_as_dict, 304)` — content is None meaning "not modified, skip parsing."
   - If status_code >= 400, raise an `httpx.HTTPStatusError` or a custom `FeedFetchError` exception with the status code and URL.
   - On success (200), return `(response.content, response_headers_as_dict, response.status_code)`.
   - Extract relevant response headers: `etag` from `response.headers.get("etag")`, `last-modified` from `response.headers.get("last-modified")`, `content-type` from `response.headers.get("content-type", "")`.
   - Return headers as a plain dict with keys `"etag"`, `"last_modified"`, `"content_type"` for clean downstream consumption.

   **`async def extract_article_content(http_client, url: str) -> str | None`**
   - Try to import trafilatura at the top of feed_service.py with: `try: import trafilatura; HAS_TRAFILATURA = True` / `except ImportError: HAS_TRAFILATURA = False`
   - If `not HAS_TRAFILATURA`, return `None` immediately (caller falls back to feed summary).
   - Fetch the article URL: `response = await http_client.get(url, follow_redirects=True)`.
   - If response.status_code != 200, return `None`.
   - Extract: `result = trafilatura.extract(response.text, output_format='markdown', include_links=True)`.
   - Return `result` (string or None if extraction failed).
   - Wrap the entire function in try/except for robustness — return None on any failure.

   **`class FeedFetchError(Exception)`** — simple exception with `url` and `status_code` attributes.

3. Write additional tests in `backend/tests/test_feed_service.py` (append to the file created in T01):

   Import the new functions via the same `importlib.util.spec_from_file_location` pattern.

   **Conditional GET tests (≥5):**
   - `test_fetch_feed_sends_etag_header` — mock http_client, call with etag="abc", assert `If-None-Match: "abc"` in headers
   - `test_fetch_feed_sends_last_modified_header` — mock http_client, call with last_modified="Sat, 01 Jan 2025 00:00:00 GMT", assert `If-Modified-Since` header
   - `test_fetch_feed_304_returns_none_content` — mock 304 response, assert content is None and status is 304
   - `test_fetch_feed_200_returns_content_and_headers` — mock 200 response with content + etag header, assert bytes content returned and etag extracted
   - `test_fetch_feed_error_raises` — mock 404 response, assert FeedFetchError raised

   **trafilatura extraction tests (≥4):**
   - `test_extract_content_success` — mock http_client returning HTML, mock trafilatura.extract returning markdown, assert result is markdown
   - `test_extract_content_no_trafilatura` — test the import guard (set `HAS_TRAFILATURA = False` on module), assert returns None
   - `test_extract_content_http_error` — mock http_client raising error, assert returns None (no crash)
   - `test_extract_content_extraction_failure` — mock trafilatura.extract returning None, assert returns None

   For trafilatura mocking: use `unittest.mock.patch` on the module-level `trafilatura` import and `HAS_TRAFILATURA` flag.

4. Verify all tests pass: `cd backend && python -m pytest tests/test_feed_service.py -v`

5. Verify syntax: `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"`

## Must-Haves

- [ ] `fetch_feed()` sends conditional GET headers (If-None-Match, If-Modified-Since) when etag/last_modified provided
- [ ] `fetch_feed()` returns `(None, headers, 304)` on HTTP 304 Not Modified
- [ ] `fetch_feed()` returns `(content_bytes, headers, status_code)` on HTTP 200
- [ ] `fetch_feed()` raises `FeedFetchError` on HTTP error responses (4xx/5xx)
- [ ] `extract_article_content()` returns markdown via trafilatura on success
- [ ] `extract_article_content()` returns None gracefully when trafilatura not installed, HTTP fails, or extraction fails
- [ ] `trafilatura>=2.0` added to `apps/rss-reader/requirements.txt`
- [ ] ≥9 new tests (≥22 cumulative) pass in test_feed_service.py

## Verification

- `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥22 cumulative tests pass
- `grep trafilatura apps/rss-reader/requirements.txt` — present
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"` — syntax valid

## Observability Impact

- `fetch_feed()` logs at INFO level on 304 (conditional GET hit) vs 200 (full fetch), with URL and status code — lets agents and operators see cache efficiency
- `fetch_feed()` logs at WARNING on HTTP errors before raising FeedFetchError — error URL and status code visible in app logs
- `extract_article_content()` logs at DEBUG on success (URL + extracted length), WARNING on failure (URL + exception type) — helps diagnose trafilatura extraction issues
- `FeedFetchError` carries `.url` and `.status_code` attributes — callers (T03's poll-feeds) can persist these to the subscription object for per-feed error tracking
- `HAS_TRAFILATURA` module-level flag is inspectable at runtime — `feed_service.HAS_TRAFILATURA` tells you whether content extraction is available

## Inputs

- `apps/rss-reader/services/feed_service.py` — from T01, with `parse_json_feed`, `discover_feeds_from_html`, `parse_feed_content` already implemented
- `backend/tests/test_feed_service.py` — from T01, with ≥12 existing tests
- `backend/sdk/sempkm_app_sdk/clients/http.py` — HttpClient API: `async get(url, **kwargs) -> httpx.Response`. Supports `headers` kwarg (dict), `follow_redirects` kwarg (bool). Response object has `.status_code`, `.content` (bytes), `.text` (str), `.headers` (httpx.Headers, acts like dict with `.get()`)
- `apps/rss-reader/requirements.txt` — currently contains `feedparser>=6.0` only

## Expected Output

- `apps/rss-reader/services/feed_service.py` — updated with `fetch_feed`, `extract_article_content`, `FeedFetchError`; trafilatura import guard
- `apps/rss-reader/requirements.txt` — now contains `feedparser>=6.0` and `trafilatura>=2.0`
- `backend/tests/test_feed_service.py` — updated with ≥9 additional tests (≥22 cumulative)
