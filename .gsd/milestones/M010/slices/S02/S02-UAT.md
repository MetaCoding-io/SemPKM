# S02: Feed service + content extraction + feed management — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is a pure service layer with unit-tested functions and mocked SDK calls. No runtime needed — all 50 unit tests cover contract correctness. Live runtime validation deferred to S03 (reader UI) and S06 (E2E tests).

## Preconditions

- Backend venv is set up at `backend/.venv/` with feedparser installed
- Test files exist: `backend/tests/test_feed_service.py`, `backend/tests/test_rss_feed_parser.py`
- App files exist: `apps/rss-reader/services/feed_service.py`, `apps/rss-reader/app.py`

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_feed_service.py -v --tb=short
```
Expected: 50 tests pass in <1s.

## Test Cases

### 1. JSON Feed 1.1 parsing produces feedparser-compatible output

1. Run `pytest tests/test_feed_service.py::TestParseJsonFeed -v`
2. **Expected:** 8 tests pass. Covers: well-formed feed (3 items), content_text vs content_html precedence, date parsing to struct_time, minimal feed with missing fields, malformed JSON (bozo=True), missing items key (bozo=True), bytes input decoded.

### 2. Feed discovery extracts correct link types from HTML

1. Run `pytest tests/test_feed_service.py::TestDiscoverFeedsFromHtml -v`
2. **Expected:** 5 tests pass. Covers: RSS + Atom links discovered, relative href resolved against base_url, no alternate links returns empty, JSON Feed type discovered, application/json type discovered.

### 3. Content type dispatch routes correctly

1. Run `pytest tests/test_feed_service.py::TestParseFeedContent -v`
2. **Expected:** 5 tests pass. `application/xml` → feedparser, `application/json` → JSON Feed parser, `application/feed+json` → JSON Feed parser, empty/None → feedparser fallback, `application/atom+xml` → feedparser.

### 4. Conditional GET sends correct headers and handles 304

1. Run `pytest tests/test_feed_service.py::TestFetchFeed -v`
2. **Expected:** 8 tests pass. Verifies: If-None-Match header sent when etag provided, If-Modified-Since header sent when last_modified provided, 304 returns (None, headers, 304), 200 returns (content, headers, 200), HTTP 4xx raises FeedFetchError with url + status_code, HTTP 5xx raises FeedFetchError, no conditional headers when both are None, follow_redirects=True passed to client.

### 5. Trafilatura content extraction with graceful fallback

1. Run `pytest tests/test_feed_service.py::TestExtractArticleContent -v`
2. **Expected:** 5 tests pass. Covers: successful extraction returns markdown string, HAS_TRAFILATURA=False returns None, HTTP error returns None, extraction failure returns None, exception during fetch returns None.

### 6. Subscription CRUD with dedup and deterministic IRI

1. Run `pytest tests/test_feed_service.py::TestMintSubscriptionIri -v`
2. Run `pytest tests/test_feed_service.py::TestSubscribe -v`
3. Run `pytest tests/test_feed_service.py::TestUnsubscribe -v`
4. **Expected:** 7 tests pass total. IRI minting is deterministic (same URL → same IRI, different URLs → different IRIs). Subscribe creates object.create with correct FeedSubscription type and dedup check. Duplicate URL returns existing subscription info. Unsubscribe patches isActive=False.

### 7. Error tracking updates subscription state correctly

1. Run `pytest tests/test_feed_service.py::TestUpdateSubscriptionState -v`
2. **Expected:** 5 tests pass. Success resets errorCount to 0 and clears lastError. Failure increments errorCount and sets lastError. ETag and lastModified headers are persisted. All-None params skip the patch call. Last-polled-only updates work.

### 8. Poll-feeds uses FeedService with conditional GET and error tracking

1. Run `pytest tests/test_feed_service.py::TestPollFeedsIntegration -v`
2. **Expected:** 4 tests pass. Verifies: etag forwarded from SPARQL to fetch_feed, 304 response creates no articles but updates lastPolled, MAX_INITIAL_ARTICLES=50 cap enforced, FeedFetchError increments error count on subscription.

### 9. Subscribe and discover routes work correctly

1. Run `pytest tests/test_feed_service.py::TestSubscribeRouteContract -v`
2. **Expected:** 4 tests pass. Subscribe-new-url calls subscribe() and returns created signal. Subscribe-duplicate returns info signal. Discover with multiple links returns feed list. Discover with no links returns empty signal.

### 10. S01 regression — all existing tests still pass

1. Run `pytest tests/test_rss_feed_parser.py -v`
2. **Expected:** 38 tests pass with zero failures. Verifies: RSS 2.0 mapping, Atom mapping, missing fields handling, article IRI determinism, date parsing, duplicate detection, bulk command assembly, error handling, realistic entries, constants.

## Edge Cases

### Malformed JSON Feed input

1. Call `parse_json_feed('not valid json')` in a test
2. **Expected:** Returns `{"bozo": True, "bozo_exception": <JSONDecodeError>, "entries": [], "feed": {"title": ""}}`

### Feed URL with no feeds discovered

1. Call `discover_feeds_from_html('<html><head></head></html>', 'https://example.com')`
2. **Expected:** Returns empty list `[]`

### Conditional GET with both etag and last_modified

1. Call `fetch_feed(client, url, etag="abc", last_modified="Mon, 01 Jan 2024")`
2. **Expected:** Both `If-None-Match: abc` and `If-Modified-Since: Mon, 01 Jan 2024` headers sent

### Subscription dedup — same URL subscribed twice

1. Call `subscribe(ctx, "https://example.com/feed.xml")` when `check_subscription_exists()` returns True
2. **Expected:** No `object.create` call made. Returns `{"status": "exists", "iri": "urn:sempkm:app:rss-reader:sub-..."}`

### MAX_INITIAL_ARTICLES cap

1. Feed returns 100 entries, no existing articles for this feed
2. **Expected:** Only first 50 entries processed. `entry_to_article()` called 50 times, not 100.

## Failure Signals

- Any test in `test_feed_service.py` fails → service logic broken
- Any test in `test_rss_feed_parser.py` fails → S01 regression introduced
- `ast.parse()` fails on feed_service.py or app.py → syntax error introduced
- `services/__init__.py` missing → package won't import
- `trafilatura>=2.0` not in requirements.txt → content extraction dependency undeclared

## Requirements Proved By This UAT

- RSS-01 (partial) — subscription management (subscribe/unsubscribe/dedup), conditional GET polling, per-feed error tracking proven via 50 unit tests
- RSS-08 (partial) — feed discovery from website URLs and trafilatura content extraction proven via unit tests

## Not Proven By This UAT

- RSS-01 full — configurable poll interval, feed list UI, unread counts (S03/S05)
- RSS-08 full — end-to-end feed discovery UX in running Docker stack (S06)
- trafilatura Docker installation — dependency declared but not proven to install in container (S06)
- Real-world feed parsing reliability — tested with synthetic data, not live feeds (S06)

## Notes for Tester

- All tests use mocked SDK clients (no running Docker stack needed)
- The `parse_feed()` function (S01) is still present with a deprecation docstring — it's unused by new code but kept for backward compatibility
- The subscribe dialog HTML is a working htmx form but cannot be tested in isolation without the app server running — functional verification deferred to S03/S06
