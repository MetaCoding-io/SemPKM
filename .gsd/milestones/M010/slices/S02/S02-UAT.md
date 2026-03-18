# S02: Feed service + content extraction + feed management — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 delivers a service layer with pure functions and mocked-SDK integration tests. All 50 unit tests pass. No runtime UI verification needed — the subscribe dialog and feed discovery are simple htmx forms whose routes are contract-tested. Reader UI verification happens in S03.

## Preconditions

- Backend venv exists at `backend/.venv` with feedparser and test dependencies installed
- `apps/rss-reader/services/feed_service.py` exists
- `backend/tests/test_feed_service.py` exists
- `backend/tests/test_rss_feed_parser.py` exists (S01 tests)

## Smoke Test

Run `cd backend && .venv/bin/python -m pytest tests/test_feed_service.py -v` — should see 50 tests pass in <1s.

## Test Cases

### 1. JSON Feed 1.1 parsing (pure function)

1. Import `parse_json_feed` from feed_service.py
2. Pass a well-formed JSON Feed string with 3 items
3. **Expected:** Returns dict with `entries` list of 3 `SimpleNamespace` objects, each with `id`, `title`, `link`, `author`, `summary`, `published_parsed` attributes. `bozo` is False.

### 2. JSON Feed malformed input handling

1. Pass invalid JSON to `parse_json_feed`
2. **Expected:** Returns dict with `bozo=True`, `bozo_exception` set, `entries=[]`

### 3. Feed discovery from HTML

1. Pass HTML containing `<link rel="alternate" type="application/rss+xml" href="/feed.xml" title="My Blog">` with base_url `https://example.com`
2. **Expected:** Returns `[{"url": "https://example.com/feed.xml", "title": "My Blog", "type": "application/rss+xml"}]`

### 4. Feed discovery — relative URL resolution

1. Pass HTML with relative href `href="/rss"` and base_url `https://example.com/blog/`
2. **Expected:** Returns `[{"url": "https://example.com/rss", ...}]` with resolved absolute URL

### 5. Feed discovery — no feeds

1. Pass HTML with no `<link rel="alternate">` tags
2. **Expected:** Returns empty list `[]`

### 6. Content type dispatch — XML to feedparser

1. Call `parse_feed_content(rss_xml_bytes, "application/rss+xml")`
2. **Expected:** Returns feedparser result dict with `entries` from the RSS XML

### 7. Content type dispatch — JSON to parse_json_feed

1. Call `parse_feed_content(json_feed_bytes, "application/feed+json")`
2. **Expected:** Returns parse_json_feed result dict

### 8. Conditional GET — ETag forwarded

1. Call `fetch_feed(mock_http, url, etag="abc123")`
2. **Expected:** `mock_http.get` called with `headers={"If-None-Match": "abc123"}`

### 9. Conditional GET — 304 Not Modified

1. Mock HTTP client returns status 304
2. Call `fetch_feed(mock_http, url, etag="abc")`
3. **Expected:** Returns `(None, headers, 304)` — content is None, caller should skip parsing

### 10. HTTP error raises FeedFetchError

1. Mock HTTP client returns status 404
2. Call `fetch_feed(mock_http, url)`
3. **Expected:** Raises `FeedFetchError` with `.url` and `.status_code=404`

### 11. trafilatura content extraction

1. Mock HTTP returning HTML, mock trafilatura.extract returning markdown
2. Call `extract_article_content(mock_http, url)`
3. **Expected:** Returns markdown string

### 12. trafilatura not installed — graceful fallback

1. Patch `HAS_TRAFILATURA = False`
2. Call `extract_article_content(mock_http, url)`
3. **Expected:** Returns `None` without error

### 13. Subscribe — new feed creates subscription

1. Mock `check_subscription_exists` returns None (no existing sub)
2. Call `subscribe(mock_ctx, "https://example.com/feed.xml", title="Test")`
3. **Expected:** Returns `{"status": "created", "iri": "urn:sempkm:app:rss-reader:sub-{sha256}"}`. `ctx.commands.execute` called with `object.create` and FeedSubscription type.

### 14. Subscribe — duplicate feed detected

1. Mock `check_subscription_exists` returns existing IRI
2. Call `subscribe(mock_ctx, "https://example.com/feed.xml")`
3. **Expected:** Returns `{"status": "duplicate", "iri": existing_iri}`. No `object.create` call.

### 15. Unsubscribe — soft delete

1. Call `unsubscribe(mock_ctx, "urn:sempkm:app:rss-reader:sub-abc")`
2. **Expected:** `ctx.commands.execute` called with `object.patch` setting `rss:isActive` to False

### 16. Update subscription state — success resets error

1. Call `update_subscription_state(ctx, sub_iri, error_count=0, last_error="")`
2. **Expected:** `object.patch` called with errorCount=0 and lastError=""

### 17. Update subscription state — failure increments

1. Call `update_subscription_state(ctx, sub_iri, error_count=3, last_error="HTTP 500")`
2. **Expected:** `object.patch` called with errorCount=3 and lastError="HTTP 500"

### 18. Update subscription state — skips when all None

1. Call `update_subscription_state(ctx, sub_iri)` with all params defaulting to None
2. **Expected:** No `object.patch` call made

### 19. Poll-feeds uses conditional GET

1. Mock SPARQL returns subscription with etag="abc" and lastModified="Wed, 01 Jan 2025..."
2. Run `poll_feeds(mock_ctx)`
3. **Expected:** `fetch_feed` called with etag="abc" and last_modified="Wed, 01 Jan 2025..."

### 20. Poll-feeds caps at MAX_INITIAL_ARTICLES

1. Mock feed returning 100 entries, no existing articles
2. Run `poll_feeds(mock_ctx)`
3. **Expected:** Only 50 articles created (MAX_INITIAL_ARTICLES cap)

### 21. Subscribe route contract — success

1. Simulate POST to `/_fragments/subscribe` with `feed_url=https://example.com/feed.xml`
2. **Expected:** Route calls `subscribe()` and returns HTML with class `rss-success`

### 22. Subscribe route contract — duplicate

1. Mock `subscribe()` returns `{"status": "duplicate"}`
2. **Expected:** Route returns HTML with class `rss-info` containing "Already subscribed"

### 23. Discover feeds route contract

1. Mock HTTP returns HTML with 2 feed links
2. Simulate GET to `/_fragments/discover-feeds?url=https://example.com`
3. **Expected:** Returns HTML with `rss-discovered-feeds` class listing 2 feeds

### 24. S01 regression check

1. Run `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v`
2. **Expected:** All 38 S01 tests pass

## Edge Cases

### Empty feed URL submitted to subscribe route

1. POST to `/_fragments/subscribe` with `feed_url=` (empty string)
2. **Expected:** Returns HTML with class `rss-error` saying "Please enter a feed URL"

### Malformed JSON Feed with valid items key but empty array

1. Call `parse_json_feed('{"version":"...","items":[]}')`
2. **Expected:** Returns dict with `entries=[]`, `bozo=False` (valid but empty)

### HTML with non-feed link tags (rel="stylesheet", etc.)

1. Pass HTML with only `<link rel="stylesheet">` tags to `discover_feeds_from_html`
2. **Expected:** Returns empty list (only `rel="alternate"` with feed types is matched)

### Feed with more than 50 articles on first poll

1. Configure mock to return 75 new articles
2. **Expected:** Only first 50 are created; log message indicates capping

### Consecutive poll failures increment errorCount

1. First poll raises FeedFetchError → errorCount=1
2. Second poll raises FeedFetchError → errorCount=2
3. Third poll succeeds → errorCount=0 (reset)
4. **Expected:** Error tracking follows increment-on-failure, reset-on-success pattern

## Failure Signals

- `test_feed_service.py` has fewer than 50 passing tests → missing test coverage
- `test_rss_feed_parser.py` has failures → S01 regression introduced
- `ast.parse()` fails on `feed_service.py` or `app.py` → syntax error
- `trafilatura>=2.0` missing from `requirements.txt` → content extraction dependency not declared
- `subscribe-dialog.html` is empty or stub content → form not implemented
- ImportError when `app.py` tries to import from `services.feed_service` → package structure broken

## Requirements Proved By This UAT

- **RSS-01** (partial) — feed subscription with dedup, conditional GET, per-feed error tracking, format-aware parsing proven by 50 contract tests
- **RSS-08** (partial) — feed discovery from HTML and trafilatura content extraction proven by unit tests

## Not Proven By This UAT

- **RSS-01** (runtime) — actual feed polling against live feeds in Docker (deferred to S06 E2E tests)
- **RSS-08** (runtime) — trafilatura installation and execution inside Docker container (proven by requirements.txt declaration but not Docker build verification)
- Reader UI rendering of articles (S03)
- Workspace contributions and custom renderer (S04)
- OPML import flow (S05)

## Notes for Tester

- All tests are pure-function or mocked-SDK tests — no Docker stack needed
- The `extract_article_content()` function is implemented but not wired into `poll_feeds()` yet — that's intentional (S03 will add it)
- The deprecated `parse_feed()` function in `app.py` still exists for S01 backward compatibility — not a bug
- Test run should be <1s total for both test files
