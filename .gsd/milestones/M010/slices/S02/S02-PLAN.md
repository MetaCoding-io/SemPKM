# S02: Feed service + content extraction + feed management

**Goal:** Build the `FeedService` — production-quality feed fetching, parsing (RSS/Atom/JSON Feed), content extraction (trafilatura), subscription management, conditional GET, per-feed error tracking, and feed discovery from website URLs. Replace S01's proof-of-concept inline feedparser with a proper service layer.

**Demo:** User subscribes to a feed by URL (via POST route). `FeedService.fetch_feed()` uses `ctx.http.get()` with conditional GET. `parse_feed_content()` handles RSS 2.0, Atom 1.0, and JSON Feed formats. `extract_article_content()` extracts full article body via trafilatura (falling back to feed summary). `update_subscription_state()` tracks etag, lastPolled, errorCount, and lastError on the FeedSubscription object. Feed discovery finds feeds from a website URL via HTML `<link>` tags. ≥35 unit tests pass covering all functions.

## Must-Haves

- `FeedService` in `apps/rss-reader/services/feed_service.py` — stateless service with pure helper functions + SDK-parameterized async methods
- `parse_json_feed(content)` — normalizes JSON Feed items to the same dict structure as feedparser entries
- `discover_feeds_from_html(html, base_url)` — extracts feed URLs from `<link rel="alternate">` tags
- `parse_feed_content(content, content_type)` — dispatches to feedparser (XML) or JSON parser (JSON Feed)
- `fetch_feed(http_client, url, etag?, last_modified?)` — conditional GET via `ctx.http.get()` with ETag/Last-Modified headers; handles 304
- `extract_article_content(http_client, url)` — trafilatura extraction with feed-summary fallback
- `subscribe(ctx, feed_url, title?)` — creates FeedSubscription via `object.create` with dedup (SPARQL ASK); deterministic IRI
- `unsubscribe(ctx, subscription_iri)` — marks subscription as inactive or removes
- `update_subscription_state(ctx, sub_iri, ...)` — patches lastPolled, etag, lastModifiedHeader, errorCount, lastError via `object.patch`
- Poll-feeds task refactored to use FeedService (HTTP fetch → parse → conditional GET → error tracking)
- POST `/_fragments/subscribe` route creates subscription from user-provided URL
- Working subscribe dialog template with htmx form
- `trafilatura>=2.0` in requirements.txt
- ≥35 new unit tests in `backend/tests/test_feed_service.py`
- S01 tests still pass (zero regressions)

## Proof Level

- This slice proves: contract (pure function correctness + mocked SDK integration)
- Real runtime required: no (unit tests with mocked SDK clients)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥35 tests pass
- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — S01 tests still pass (23 tests, zero regressions)
- `ast.parse(open('apps/rss-reader/services/feed_service.py').read())` — syntax OK
- `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK after refactoring
- `python3 -c "import json; json.loads(open('apps/rss-reader/services/__init__.py').read() if open('apps/rss-reader/services/__init__.py').read() else '{}')"` — services package exists
- Diagnostic: error tracking tests verify that `update_subscription_state()` produces correct `object.patch` params with lastError message and errorCount increment
- Diagnostic: conditional GET tests verify 304 response returns `None` content (skip parsing) and that ETag/Last-Modified headers are forwarded correctly

## Observability / Diagnostics

- Runtime signals: `FeedService.fetch_feed()` logs conditional GET hits (304) vs full fetches; `subscribe()` logs new subscription creation with IRI
- Inspection surfaces: `update_subscription_state()` writes lastPolled, errorCount, lastError to the FeedSubscription object — queryable via SPARQL
- Failure visibility: Per-feed error tracking exposes lastError message + errorCount integer on the subscription object; consecutive failures increment count, success resets to 0
- Redaction constraints: none (feed URLs are not secrets)

## Integration Closure

- Upstream surfaces consumed: `apps/rss-reader/app.py` (poll-feeds task, entry_to_article, _mint_article_iri, constants); `backend/sdk/sempkm_app_sdk/clients/http.py` (HttpClient.get); `backend/sdk/sempkm_app_sdk/clients/commands.py` (CommandClient.execute, .bulk); `backend/sdk/sempkm_app_sdk/clients/graph.py` (GraphClient.query)
- New wiring introduced in this slice: `services/feed_service.py` is imported by `app.py`; poll-feeds task delegates to FeedService; subscribe route calls FeedService.subscribe()
- What remains before the milestone is truly usable end-to-end: S03 (reader UI), S04 (workspace contributions + custom renderer), S05 (OPML import), S06 (E2E tests)

## Tasks

- [x] **T01: Implement FeedService pure functions — JSON Feed parser, feed discovery, and content type dispatch** `est:40m`
  - Why: These are the foundational parsing functions that all other FeedService methods depend on. They're pure (no SDK dependency), so they can be tested thoroughly without mocking. Establishes the `services/` module structure that T02-T04 build on. Covers the JSON Feed support gap (feedparser doesn't handle JSON Feed) and feed discovery from website URLs (RSS-08).
  - Files: `apps/rss-reader/services/__init__.py`, `apps/rss-reader/services/feed_service.py`, `backend/tests/test_feed_service.py`
  - Do: Create services package. Implement `parse_json_feed(content)` normalizing JSON Feed 1.1 items to feedparser-compatible dicts (title, link, id, published_parsed, summary, author). Implement `discover_feeds_from_html(html, base_url)` parsing `<link rel="alternate" type="application/rss+xml|atom+xml|feed+json">` tags, resolving relative URLs against base_url. Implement `parse_feed_content(raw_bytes, content_type)` that dispatches XML content to `feedparser.parse(BytesIO(raw_bytes))` and JSON content to `parse_json_feed()`. Write ≥12 unit tests covering JSON Feed (well-formed, minimal, malformed), feed discovery (multiple links, relative URLs, no feeds), and content dispatch.
  - Verify: `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥12 tests pass
  - Done when: `parse_json_feed`, `discover_feeds_from_html`, and `parse_feed_content` all have passing tests; `services/` package importable

- [x] **T02: Implement HTTP fetching with conditional GET and trafilatura content extraction** `est:40m`
  - Why: S01's `parse_feed()` calls `feedparser.parse(url)` which bypasses SDK domain enforcement. This task replaces it with `fetch_feed()` using `ctx.http.get()` and adds conditional GET (ETag/Last-Modified) to avoid redundant downloads. Also adds trafilatura for full article content extraction (RSS-08). These are the I/O boundary functions that T03's poll-feeds refactor depends on.
  - Files: `apps/rss-reader/services/feed_service.py`, `apps/rss-reader/requirements.txt`, `backend/tests/test_feed_service.py`
  - Do: Implement `fetch_feed(http_client, url, etag=None, last_modified=None)` — builds conditional GET headers (`If-None-Match`, `If-Modified-Since`), calls `http_client.get(url, headers=...)`, returns `(content_bytes, response_headers, status_code)` or `(None, headers, 304)` on not-modified. Implement `extract_article_content(http_client, url)` — fetches article URL, runs `trafilatura.extract(html, output_format='markdown')`, returns markdown string or None on failure. Add `trafilatura>=2.0` to requirements.txt with try/except import guard in feed_service.py. Write ≥10 tests with mocked HttpClient covering: conditional GET headers sent correctly, 304 returns None content, 200 returns content + new etag, HTTP error handling, trafilatura extraction success, trafilatura fallback on import failure, trafilatura fallback on extraction failure.
  - Verify: `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥22 cumulative tests pass
  - Done when: `fetch_feed` sends conditional GET headers and handles 304; `extract_article_content` returns markdown via trafilatura with graceful fallback; requirements.txt includes trafilatura

- [x] **T03: Implement subscription management, error tracking, and refactor poll-feeds to use FeedService** `est:45m`
  - Why: This is the integration task — wiring FeedService into the existing app. Creates the subscription CRUD that S05 (OPML import) depends on, the error tracking that the reader UI (S03) displays, and the refactored poll-feeds task that actually uses conditional GET and per-feed error tracking. Covers the S02 → S04 and S02 → S05 boundary contracts.
  - Files: `apps/rss-reader/services/feed_service.py`, `apps/rss-reader/app.py`, `backend/tests/test_feed_service.py`
  - Do: Implement `subscribe(ctx, feed_url, title=None)` — mint subscription IRI as `urn:sempkm:app:rss-reader:sub-{sha256(feed_url)}`, SPARQL ASK for dedup, `ctx.commands.execute("object.create", ...)` with FeedSubscription type. Implement `unsubscribe(ctx, subscription_iri)` — SPARQL ASK to verify exists, `ctx.commands.execute("object.patch", ...)` to set inactive or delete. Implement `update_subscription_state(ctx, sub_iri, last_polled=None, etag=None, last_modified=None, error_count=None, last_error=None)` — builds `object.patch` params for each non-None field. Refactor `poll_feeds()` in app.py: replace `parse_feed(url)` with `fetch_feed(ctx.http, url, etag, last_modified)` → `parse_feed_content(content, content_type)`, call `update_subscription_state()` after each feed (success resets errorCount to 0, failure increments and sets lastError), add `max_initial_articles=50` cap for first-time feed imports, query subscription etag/lastModifiedHeader from SPARQL. Add constants to app.py for subscription IRI minting. Write ≥12 tests covering: subscribe creates correct object.create params, subscribe dedup rejects duplicate URL, unsubscribe calls correct patch/delete, update_subscription_state builds correct patch params, error count resets on success, poll-feeds uses FeedService (mocked end-to-end), max_initial_articles cap.
  - Verify: `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥34 cumulative tests pass; `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — S01 tests still pass
  - Done when: `subscribe()` creates FeedSubscription with dedup; `poll_feeds()` uses FeedService for HTTP fetch + conditional GET + error tracking; all S01 tests still pass

- [x] **T04: Wire subscribe route, feed discovery endpoint, and working dialog template** `est:30m`
  - Why: Closes the user-facing loop — users can actually subscribe to feeds by URL from the UI. The subscribe route calls `FeedService.subscribe()`, the discover route calls `discover_feeds_from_html()`, and the dialog template provides the form. This is the S02 → S05 boundary contract (subscribe method pattern) and satisfies the "user subscribes to feeds by URL" requirement (RSS-01).
  - Files: `apps/rss-reader/app.py`, `apps/rss-reader/frontend/templates/subscribe-dialog.html`, `backend/tests/test_feed_service.py`
  - Do: Add POST `/_fragments/subscribe` route in app.py — reads `feed_url` and optional `title` from form body, calls `FeedService.subscribe(ctx, feed_url, title)`, returns HTML fragment confirming subscription (or error). Add GET `/_fragments/discover-feeds?url=` route — fetches URL via `ctx.http.get()`, calls `discover_feeds_from_html(html, url)`, returns HTML list of discovered feeds. Update `subscribe-dialog.html` with working htmx form: text input for URL, "Discover" button that triggers feed discovery, submit button that POSTs to subscribe route, success/error feedback area. Write ≥3 tests for route handlers: subscribe success, subscribe duplicate, discover returns feed list.
  - Verify: `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥37 cumulative tests pass; `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK
  - Done when: Subscribe dialog has working htmx form; POST subscribe creates subscription; discover-feeds returns feed URLs; all tests pass

## Files Likely Touched

- `apps/rss-reader/services/__init__.py` (new)
- `apps/rss-reader/services/feed_service.py` (new — core service)
- `apps/rss-reader/app.py` (modified — poll-feeds refactor, new routes)
- `apps/rss-reader/requirements.txt` (modified — add trafilatura)
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` (modified — working form)
- `backend/tests/test_feed_service.py` (new — ≥35 tests)
