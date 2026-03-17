# S02: Feed service + content extraction + feed management — Research

**Date:** 2026-03-17
**Status:** Complete
**Slice Risk:** medium

## Summary

S02 builds the `FeedService` — the core service layer that S01's `poll-feeds` task handler delegates to for subscription management, feed fetching, content extraction, and error tracking. S01 proved the data pipeline (feedparser → entry_to_article → bulk EventStore) but hardcoded feedparser's internal HTTP fetching and used only feed-provided summaries. S02 replaces that with a production-quality service: fetching via `ctx.http` (SDK domain enforcement), conditional GET (ETag/Last-Modified), trafilatura for full article extraction, feed discovery from website URLs, JSON Feed support (feedparser doesn't handle JSON Feeds), and per-feed error tracking via `object.patch`.

This is targeted research — the technologies are well-documented, S01 established all the SDK patterns, and the model types already have the right properties (etag, lastError, errorCount, lastPolled). The main work is implementing the `FeedService` class, adding trafilatura + JSON Feed parsing, upgrading the poll-feeds task to use FeedService, building the subscribe/unsubscribe routes, and writing unit tests.

## Recommendation

### Approach: Service class with pure-function helpers

Create `apps/rss-reader/services/feed_service.py` as a stateless service that receives SDK clients as parameters (not as class state). This matches the pattern from S01 where `entry_to_article()` is a pure function. The service should expose:

1. **`subscribe(ctx, feed_url, title?)`** — Creates a FeedSubscription object via `ctx.commands.execute("object.create", ...)`
2. **`unsubscribe(ctx, subscription_iri)`** — Removes subscription (or marks inactive)
3. **`fetch_feed(ctx, feed_url, etag?, last_modified?)`** — Fetches via `ctx.http.get()` with conditional GET headers, returns raw content + response headers
4. **`parse_feed_content(content, content_type)`** — Dispatches to feedparser (RSS/Atom) or JSON parser (JSON Feed), returns normalized list of entry dicts
5. **`extract_article_content(ctx, url)`** — Uses trafilatura to extract full article body as markdown
6. **`discover_feeds(ctx, website_url)`** — Parses HTML `<link rel="alternate">` tags to find feed URLs
7. **`update_subscription_state(ctx, sub_iri, ...)`** — Patches lastPolled, etag, lastModifiedHeader, errorCount, lastError on the subscription

### Key design decisions

- **Decouple fetch from parse**: S01's `parse_feed()` calls `feedparser.parse(url)` which uses urllib internally. This bypasses the SDK's HttpClient domain enforcement. S02 must fetch with `ctx.http.get()` then pass the response bytes to `feedparser.parse(BytesIO(content))`. feedparser supports parsing from strings/bytes natively.
- **JSON Feed as a separate parser**: feedparser doesn't support JSON Feed. Since JSON Feed is plain JSON, write a simple `parse_json_feed()` function (~30 lines) that normalizes JSON Feed items to the same dict structure as feedparser entries.
- **trafilatura as optional**: Add to requirements.txt. If import fails at runtime, fall back to feed-provided summaries. This is resilience, not permanent — trafilatura should install fine with wheels.
- **Subscription IRI minting**: Use `urn:sempkm:app:rss-reader:sub-{sha256(feed_url)}` — deterministic from the feed URL, prevents duplicate subscriptions.
- **Error tracking on the subscription object**: Use `object.patch` to update `rss:errorCount`, `rss:lastError`, `rss:lastPolled` after each poll. Reset errorCount to 0 on success.
- **Conditional GET via HTTP headers**: Store ETag and Last-Modified on the FeedSubscription object (already in the model). Pass them as `If-None-Match` / `If-Modified-Since` headers. On 304, skip parsing.

## Implementation Landscape

### Key Files

**Existing (from S01):**
- `apps/rss-reader/app.py` — Poll-feeds task handler, `entry_to_article()`, `_mint_article_iri()`, `parse_feed()`, `get_existing_article_iris()`, constants (`ARTICLE_TYPE`, `SUBSCRIPTION_TYPE`, `RSS_NS`)
- `apps/rss-reader/requirements.txt` — Currently `feedparser>=6.0`
- `apps/rss-reader/manifest.yaml` — App manifest with permissions (object.create, object.patch, body.set, sparql read, network: *)
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — Stub template for subscribe dialog
- `models/rss-feeds/ontology/rss-feeds.jsonld` — Article and FeedSubscription OWL classes with all needed properties (feedUrl, siteUrl, lastPolled, errorCount, lastError, etag, lastModifiedHeader)

**SDK clients used (read-only reference):**
- `backend/sdk/sempkm_app_sdk/clients/http.py` — `HttpClient.get(url, **kwargs)` wrapping httpx with domain enforcement. Supports any kwargs httpx accepts (headers, follow_redirects, etc.)
- `backend/sdk/sempkm_app_sdk/clients/state.py` — `StateClient.get(key)` / `.set(key, value)` for app-scoped key/value state
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — `CommandClient.execute()` and `.bulk()` for object.create / object.patch / body.set
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — `GraphClient.query(sparql)` for SPARQL reads
- `backend/sdk/sempkm_app_sdk/context.py` — `AppContext` with `.commands`, `.graph`, `.state`, `.settings`, `.http` properties

**New files (S02 creates):**
- `apps/rss-reader/services/__init__.py` — Empty init
- `apps/rss-reader/services/feed_service.py` — Core service: subscribe, unsubscribe, fetch_feed, parse_feed_content, extract_article_content, discover_feeds, update_subscription_state
- `backend/tests/test_feed_service.py` — Unit tests for FeedService (pure functions + mocked SDK clients)
- Updated `apps/rss-reader/app.py` — Refactored poll-feeds to use FeedService; new routes for subscribe/unsubscribe/discover
- Updated `apps/rss-reader/requirements.txt` — Add `trafilatura>=2.0`
- Updated `apps/rss-reader/frontend/templates/subscribe-dialog.html` — Working subscribe form

### Build Order

1. **FeedService pure functions first** — `parse_json_feed()`, `discover_feeds_from_html()`, `normalize_entry()`. These are importable and testable without mocking SDK clients. Prove JSON Feed parsing and feed discovery with unit tests before wiring to the app.

2. **fetch_feed + conditional GET second** — Wire `ctx.http.get()` with ETag/Last-Modified headers. Handle 304 response. Parse response content-type to dispatch between feedparser (XML) and JSON Feed parser. This is the critical integration point.

3. **subscribe/unsubscribe third** — Create FeedSubscription objects via `ctx.commands.execute("object.create", ...)`. IRI minting, duplicate checking (SPARQL ASK), title resolution from feed metadata.

4. **trafilatura integration fourth** — `extract_article_content(ctx, url)` fetches the article URL and runs trafilatura to get markdown. Store via `ctx.commands.execute("body.set", ...)`. Fallback to feed summary if extraction fails.

5. **Refactor poll-feeds task fifth** — Replace S01's inline feedparser call with `FeedService.fetch_feed()` + `parse_feed_content()`. Add conditional GET support. Update subscription state (lastPolled, etag, errorCount) via `object.patch` after each feed.

6. **Subscribe route + template sixth** — POST handler for `/_fragments/subscribe` that calls `FeedService.subscribe()`. Update the subscribe-dialog.html stub with a working form.

7. **Unit tests throughout** — Write tests alongside each function. Target ≥30 tests covering RSS 2.0, Atom 1.0, JSON Feed, conditional GET, error tracking, subscription CRUD, feed discovery, and trafilatura extraction.

### Verification Approach

- `cd backend && python -m pytest tests/test_feed_service.py -v` — all tests pass, ≥30 tests
- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — S01 tests still pass (no regressions)
- `python3 -c "import trafilatura; print(trafilatura.__version__)"` — trafilatura importable
- `python3 -c "import json; ..."` — JSON Feed parser handles well-formed and malformed inputs
- `ast.parse(open('apps/rss-reader/services/feed_service.py').read())` — syntax OK
- `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK after refactoring

## Constraints

- **feedparser does NOT support JSON Feed** — Verified: `feedparser.parse(json_feed_string)` returns 0 entries and `bozo=True`. Must implement a simple JSON Feed parser (~30 lines) that normalizes items to the same structure as feedparser entries.
- **feedparser.parse(url) uses urllib internally, bypassing SDK HttpClient** — Must fetch with `ctx.http.get(url)` first, then pass response bytes to `feedparser.parse(io.BytesIO(content))`. feedparser accepts BytesIO/string input natively.
- **HttpClient only has `get()` and `post()` methods** — Sufficient for feed fetching (GET) and future API calls. For conditional GET, pass headers via `**kwargs` which forwards to httpx.
- **StateClient stores strings only** — Complex per-feed metadata (multiple values) should go on the FeedSubscription object via `object.patch`, not in the state graph. State graph is for app-level config only.
- **object.patch replaces ALL values for a predicate** — When patching errorCount or lastPolled, the handler does `DELETE ?old / INSERT new`. This is correct behavior — each property is single-valued.
- **Bulk EventStore 1000-operation limit** — For feeds with 100+ items, partition into batches of 1000. Unlikely in practice for a single feed poll but handle it defensively.
- **Module name collision** — `apps/rss-reader/app.py` collides with `backend/app/`. Tests must use `importlib.util.spec_from_file_location` pattern (documented in KNOWLEDGE.md). Same applies to importing from `services/feed_service.py`.

## Common Pitfalls

- **feedparser runs synchronously** — Both `feedparser.parse()` and trafilatura's `extract()` are blocking calls. Since the app runs in its own subprocess and task handlers aren't concurrent, this is acceptable. Use `asyncio.to_thread()` if we want to be defensive about blocking the uvicorn event loop.
- **trafilatura import failure in Docker** — lxml 6.0.2 has pre-built wheels for Python 3.12 / Linux x86_64 (verified via `uv pip install --dry-run`), so this should work. The `uv pip install` output showed "Would download" not "Would build". Add a try/except import guard so the app still starts if trafilatura fails.
- **`entry._feed_url` side effect from S01** — S01 sets `entry._feed_url = feed_url` on feedparser entries before calling `entry_to_article()`. FeedService must preserve this pattern, or refactor `entry_to_article()` to accept feed_url as an explicit parameter instead of reading it from the entry object.
- **Conditional GET ETag header format** — ETags include quotes (e.g., `"abc123"`). Must store and send the full ETag string including quotes. httpx handles this correctly if passed as-is.
- **Feed discovery from HTTPS sites** — Some sites serve different HTML to different user agents. Use a browser-like user agent string in `ctx.http.get()` for feed discovery.

## Open Risks

- **trafilatura extraction quality on real sites** — Some sites block scrapers, require JavaScript rendering, or serve paywalled content. trafilatura handles most cases but will fail on some. The fallback to feed-provided summary is essential.
- **Large feed backlogs** — When subscribing to a feed for the first time, all existing items are "new." A feed with 500 items in its history would generate 500 article objects. Consider a `max_initial_articles` limit (e.g., 50 most recent).

## Sources

- feedparser `parse()` signature: accepts `etag=`, `modified=`, and parses from URLs, files, strings, or BytesIO — [feedparser docs](https://pythonhosted.org/feedparser/)
- JSON Feed spec: `version`, `title`, `items[]` with `id`, `title`, `url`, `content_text`/`content_html`, `date_published`, `authors[]` — [jsonfeed.org/version/1.1](https://www.jsonfeed.org/version/1.1/)
- trafilatura `extract()`: outputs markdown directly, handles fallback to readability-lxml — [trafilatura docs](https://trafilatura.readthedocs.io/)
- `docs/research/rss-reader-hypothesis-integration.md` §3-6 — feedparser selection rationale, feed discovery patterns, content extraction benchmarks, conditional GET mechanics
