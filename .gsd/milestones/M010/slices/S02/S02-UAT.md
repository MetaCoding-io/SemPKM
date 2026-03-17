# S02: Feed service + content extraction + feed management — UAT

**Milestone:** M010
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 delivers a service layer with pure functions and mocked SDK integration. All 54 tests verify contract correctness without a running Docker stack. Live runtime testing is deferred to S06 (E2E tests). The subscribe dialog and routes are verified via unit test contracts.

## Preconditions

- Backend venv exists at `backend/.venv` with feedparser installed
- Test files exist: `backend/tests/test_feed_service.py`, `backend/tests/test_rss_feed_parser.py`
- Source files exist: `apps/rss-reader/services/feed_service.py`, `apps/rss-reader/app.py`

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_feed_service.py -v --tb=short
```
**Expected:** 54 tests pass in under 2 seconds. Zero failures.

## Test Cases

### 1. JSON Feed parsing produces feedparser-compatible output

1. Run `pytest tests/test_feed_service.py::TestParseJsonFeed -v`
2. **Expected:** 9 tests pass — well-formed feed, content_text/html priority, date parsing, minimal items, malformed JSON (bozo), missing items key, bytes input, author extraction

### 2. Feed discovery extracts alternate links from HTML

1. Run `pytest tests/test_feed_service.py::TestDiscoverFeedsFromHtml -v`
2. **Expected:** 5 tests pass — RSS+Atom links discovered, relative URL resolved, empty page returns empty list, JSON Feed type discovered, non-feed alternates ignored

### 3. Content type dispatch routes to correct parser

1. Run `pytest tests/test_feed_service.py::TestParseFeedContent -v`
2. **Expected:** 6 tests pass — XML dispatches to feedparser, JSON dispatches to parse_json_feed, application/json works, empty/unknown content types fall back to feedparser, Atom content type uses feedparser

### 4. Conditional GET sends correct headers and handles 304

1. Run `pytest tests/test_feed_service.py::TestFetchFeed -v`
2. **Expected:** 9 tests pass — etag sends If-None-Match, last_modified sends If-Modified-Since, both headers sent together, no headers when None, 304 returns (None, headers, 304), 200 returns (content, headers, 200), 404/500 raise FeedFetchError, follow_redirects passed

### 5. Trafilatura extraction with graceful fallback

1. Run `pytest tests/test_feed_service.py::TestExtractArticleContent -v`
2. **Expected:** 5 tests pass — successful extraction returns markdown, no-trafilatura returns None, HTTP error returns None, extraction failure returns None, unexpected exception returns None

### 6. Subscription CRUD with dedup and deterministic IRIs

1. Run `pytest tests/test_feed_service.py::TestMintSubscriptionIri tests/test_feed_service.py::TestSubscribe tests/test_feed_service.py::TestUnsubscribe -v`
2. **Expected:** 7 tests pass — same URL produces same IRI, different URLs produce different IRIs, IRI format matches `urn:sempkm:app:rss-reader:sub-{hex}`, subscribe creates correct object.create params, duplicate URL returns existing IRI, empty title defaults to URL, unsubscribe patches isActive=False

### 7. Per-feed error tracking via update_subscription_state

1. Run `pytest tests/test_feed_service.py::TestUpdateSubscriptionState -v`
2. **Expected:** 5 tests pass — success resets errorCount to 0, failure increments errorCount and sets lastError, etag and lastModified written, all-None is skipped, lastPolled always written

### 8. Refactored poll_feeds uses FeedService pipeline

1. Run `pytest tests/test_feed_service.py::TestPollFeedsIntegration -v`
2. **Expected:** 4 tests pass — conditional GET headers passed from subscription state, 304 skips parsing, max_initial_articles capped at 50, errors increment feed error count

### 9. Subscribe route contract

1. Run `pytest tests/test_feed_service.py::TestSubscribeRouteContract -v`
2. **Expected:** 3 tests pass — success returns created status info, duplicate returns existing IRI, empty title defaults to URL

### 10. Feed discovery comprehensive test

1. Run `pytest tests/test_feed_service.py::TestDiscoverFeedsComprehensive -v`
2. **Expected:** 1 test passes — discovers RSS, Atom, and JSON Feed links from HTML page

### 11. S01 regression check

1. Run `pytest tests/test_rss_feed_parser.py -v`
2. **Expected:** All 23 S01 tests pass with zero failures — entry mapping, article IRI minting, duplicate detection, bulk command assembly, error handling, date parsing, constants

### 12. Source file syntax validation

1. Run:
   ```bash
   python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"
   python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('OK')"
   ```
2. **Expected:** Both print "OK" with no SyntaxError

## Edge Cases

### Malformed JSON Feed returns bozo without crashing

1. Call `parse_json_feed("not json at all")`
2. **Expected:** Returns dict with `bozo=True`, `bozo_exception` set, `entries=[]` — no exception raised

### Feed with no entries produces empty article list

1. Call `parse_feed_content(b'<rss><channel></channel></rss>', 'application/rss+xml')`
2. **Expected:** Returns feedparser result with empty entries list

### Trafilatura unavailable degrades gracefully

1. Patch `HAS_TRAFILATURA=False` on the module
2. Call `extract_article_content(mock_client, "https://example.com/article")`
3. **Expected:** Returns `None` immediately — no ImportError, no crash

### Subscription to same URL is idempotent

1. Call `subscribe(ctx, "https://example.com/feed.xml")` twice
2. **Expected:** First call creates subscription, second returns existing IRI without creating a duplicate

### HTTP 500 on fetch raises FeedFetchError with status code

1. Mock HTTP client to return 500 status
2. Call `fetch_feed(client, "https://example.com/feed.xml")`
3. **Expected:** Raises `FeedFetchError` with `.status_code == 500` and `.url == "https://example.com/feed.xml"`

## Failure Signals

- Any of the 54 `test_feed_service.py` tests failing
- Any of the 23 `test_rss_feed_parser.py` tests failing (S01 regression)
- `SyntaxError` when parsing feed_service.py or app.py
- `services/__init__.py` missing (broken package structure)
- `trafilatura` missing from requirements.txt
- `subscribe-dialog.html` empty or missing

## Requirements Proved By This UAT

- **RSS-01** (partial) — Feed subscription CRUD via `subscribe()`/`unsubscribe()`, polling via refactored `poll_feeds()` with conditional GET and error tracking. Full validation requires E2E in S06.
- **RSS-08** (partial) — Feed discovery via `discover_feeds_from_html()`, content extraction via `extract_article_content()`. Full validation requires live trafilatura in Docker container.

## Not Proven By This UAT

- **Runtime data pipeline**: All tests use mocked SDK clients. The subscribe → poll → articles-in-triplestore flow has not been verified against a live Docker stack.
- **trafilatura Docker installation**: The library is in requirements.txt but has not been installed/tested in the Docker container's app venv.
- **UI interaction**: The subscribe dialog HTML is verified structurally (non-empty, correct template) but not rendered in a browser.
- **Discover-feeds param mismatch**: Known issue where htmx sends `feed_url` but route reads `url` — will need fix in S03.

## Notes for Tester

- Tests run fast (< 1 second) — all I/O is mocked
- The `_make_mock_ctx()`, `_make_mock_http_client()`, and `_make_mock_response()` helper functions in the test file establish patterns reused across all test classes
- If running tests fails with import errors, ensure the backend venv has feedparser installed: `cd backend && .venv/bin/python -m pip install feedparser`
- The test file uses `importlib.util.spec_from_file_location` to avoid the `app` module name collision between `apps/rss-reader/app.py` and `backend/app/` — this is an intentional pattern documented in KNOWLEDGE.md
