---
id: S02
parent: M010
milestone: M010
provides:
  - FeedService module (apps/rss-reader/services/feed_service.py) with 11 public functions
  - parse_json_feed() — JSON Feed 1.1 parser with feedparser-compatible output
  - discover_feeds_from_html() — HTML <link rel="alternate"> feed URL extractor
  - parse_feed_content() — content-type dispatcher (XML→feedparser, JSON→parse_json_feed)
  - fetch_feed() — async conditional GET with ETag/Last-Modified support
  - extract_article_content() — trafilatura-based markdown extraction with graceful fallback
  - subscribe() — creates FeedSubscription with deterministic IRI and SPARQL dedup
  - unsubscribe() — soft-deletes subscription via object.patch isActive=False
  - update_subscription_state() — persists etag, lastPolled, errorCount, lastError per subscription
  - POST /_fragments/subscribe route and GET /_fragments/discover-feeds route
  - Working subscribe-dialog.html htmx form
  - poll-feeds task refactored to use FeedService with conditional GET and per-feed error tracking
  - MAX_INITIAL_ARTICLES=50 cap for first-time feed imports
requires:
  - slice: S01
    provides: rss-reader app skeleton with poll-feeds task, entry_to_article, _mint_article_iri, feedparser dependency, rss-feeds mental model
affects:
  - S04 (workspace contributions depend on FeedService data: subscription objects with error/poll state, articles with read/star state)
  - S05 (OPML import depends on subscribe() method for creating subscriptions programmatically)
  - S03 (reader UI depends on FeedService data for feed sidebar, article list, reading pane content)
key_files:
  - apps/rss-reader/services/__init__.py
  - apps/rss-reader/services/feed_service.py
  - apps/rss-reader/app.py
  - apps/rss-reader/requirements.txt
  - apps/rss-reader/frontend/templates/subscribe-dialog.html
  - backend/tests/test_feed_service.py
key_decisions:
  - D182: Soft-delete for unsubscribe (isActive=False) rather than hard delete — preserves article references
  - D185: Feed format dispatch — content-type-based dispatch to feedparser or custom JSON Feed parser
  - D186: trafilatura optional dependency — HAS_TRAFILATURA guard flag with graceful degradation
  - D187: Conditional GET for feed polling — ETag/Last-Modified stored per-subscription
  - SimpleNamespace for JSON Feed entries (attribute access like feedparser's FeedParserDict)
  - stdlib html.parser.HTMLParser for feed discovery (no extra dependencies)
  - FeedFetchError custom exception — decouples from httpx internals, carries url + status_code
  - try/except import fallback in app.py for services.feed_service — resolves via file path when loaded by spec_from_file_location in test context
  - HTML fragment routes return CSS-classed divs (rss-success, rss-error, rss-info) as structured result signals
  - HX-Trigger feedsChanged header on successful subscription for cross-component communication
patterns_established:
  - services/ package pattern for RSS reader app — stateless pure functions + async SDK-parameterized methods
  - JSON Feed bozo pattern mirrors feedparser — bozo=True, bozo_exception, entries=[] on parse failure
  - AsyncMock + MagicMock pattern for testing async http_client functions without real network
  - patch.object on module-level flags (HAS_TRAFILATURA) for testing import guard branches
  - _mock_response() / _mock_http_client() test helpers for httpx-like response objects
  - _make_mock_ctx_for_poll() helper builds complete mock AppContext with bulk context manager
  - patch("rss_reader_app_svc.fetch_feed") pattern for mocking feed_service imports in poll_feeds integration tests
observability_surfaces:
  - rss:errorCount integer on FeedSubscription — SPARQL-queryable per-feed health indicator (0 = healthy, incrementing = consecutive failures)
  - rss:lastError string on FeedSubscription — most recent error message for failed feeds
  - rss:lastPolled ISO 8601 timestamp on FeedSubscription — when this feed was last polled
  - rss:etag and rss:lastModifiedHeader on FeedSubscription — persisted conditional GET state
  - fetch_feed() logs INFO on 304 (conditional GET hit) vs 200 (full fetch) with URL
  - extract_article_content() logs DEBUG on success, WARNING on failure
  - feed_service.HAS_TRAFILATURA flag inspectable at runtime
  - Subscribe/discover routes return CSS-classed fragments (rss-success/rss-error/rss-info) inspectable in DevTools
  - HX-Trigger: feedsChanged observable in browser network tab on successful subscription
drill_down_paths:
  - .gsd/milestones/M010/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M010/slices/S02/tasks/T04-SUMMARY.md
duration: ~64m across 4 tasks
verification_result: passed
completed_at: 2026-03-18
---

# S02: Feed service + content extraction + feed management

**Production-quality FeedService with JSON Feed parsing, HTML feed discovery, conditional GET, trafilatura content extraction, subscription CRUD with dedup, per-feed error tracking, and working subscribe UI — 50 unit tests, zero S01 regressions.**

## What Happened

This slice replaced S01's proof-of-concept inline feedparser usage with a proper `FeedService` service layer in `apps/rss-reader/services/feed_service.py`, then wired it into the existing app and exposed subscription management through htmx routes.

**T01 (pure functions):** Created the `services/` package with three pure data-transformer functions. `parse_json_feed()` normalizes JSON Feed 1.1 content into feedparser-compatible dicts using `SimpleNamespace` entries with attribute access. `discover_feeds_from_html()` uses stdlib `HTMLParser` to find `<link rel="alternate">` tags for RSS, Atom, and JSON Feed types, resolving relative URLs via `urljoin`. `parse_feed_content()` dispatches by content type — JSON to `parse_json_feed()`, everything else to feedparser. 18 unit tests established.

**T02 (HTTP fetching + content extraction):** Added `fetch_feed()` with conditional GET support — builds `If-None-Match` / `If-Modified-Since` headers, returns `(None, headers, 304)` on cache hits, raises `FeedFetchError` (custom exception with `.url` and `.status_code`) on HTTP errors. Added `extract_article_content()` with trafilatura markdown extraction and a module-level `HAS_TRAFILATURA` import guard for graceful degradation. Added `trafilatura>=2.0` to requirements.txt. 13 new tests (31 cumulative).

**T03 (subscription management + poll-feeds refactor):** Added 5 subscription management functions: `mint_subscription_iri()` (deterministic SHA-256), `check_subscription_exists()` (SPARQL dedup), `subscribe()` (object.create with dedup), `unsubscribe()` (soft-delete via isActive=False), and `update_subscription_state()` (object.patch for etag/lastPolled/errorCount/lastError). Refactored `poll_feeds()` to use `fetch_feed()` + `parse_feed_content()` with conditional GET, `MAX_INITIAL_ARTICLES=50` cap, and per-feed error tracking (success resets errorCount to 0, failure increments and sets lastError). Updated 3 S01 tests to match the new mocking surface. 15 new tests (46 cumulative).

**T04 (routes + UI):** Added POST `/_fragments/subscribe` route (creates subscription from form data, returns HTML result fragment with HX-Trigger: feedsChanged), GET `/_fragments/discover-feeds` route (fetches URL, extracts feed links, returns discoverable feed list with "Use this feed" buttons), and replaced the S01 stub `subscribe-dialog.html` with a working htmx form. 4 new tests (50 cumulative).

## Verification

All slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `test_feed_service.py` — ≥35 tests (got 50) | ✅ 50 passed in 0.29s |
| 2 | `test_rss_feed_parser.py` — S01 tests pass (got 38) | ✅ 38 passed in 0.26s (zero regressions) |
| 3 | `ast.parse(feed_service.py)` — syntax OK | ✅ OK |
| 4 | `ast.parse(app.py)` — syntax OK | ✅ OK |
| 5 | `services/__init__.py` exists | ✅ exists |
| 6 | `trafilatura>=2.0` in requirements.txt | ✅ present |
| 7 | `subscribe-dialog.html` non-empty | ✅ non-empty |
| 8 | Error tracking tests verify object.patch params | ✅ 5 tests cover success reset, failure increment, etag/last_modified, skip-when-none, last_polled-only |
| 9 | Conditional GET tests verify 304 and header forwarding | ✅ 3 tests cover etag header, last_modified header, 304 returns None |

## Requirements Advanced

- **RSS-01** — Feed subscription and polling now uses conditional GET (ETag/Last-Modified), format-aware parsing (RSS 2.0, Atom 1.0, JSON Feed), per-feed error tracking, and MAX_INITIAL_ARTICLES=50 cap. Subscribe route creates subscriptions from user input with dedup.
- **RSS-08** — Feed discovery implemented (`discover_feeds_from_html`), trafilatura content extraction added (`extract_article_content`), graceful fallback when trafilatura unavailable or extraction fails.

## Requirements Validated

- none (these requirements need runtime verification in later slices to move to validated)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **T03:** Updated 3 S01 tests in `test_rss_feed_parser.py` to match the refactored `poll_feeds` interface (binding key `feedUrl` instead of `url`, mock `fetch_feed`/`parse_feed_content` instead of `parse_feed`). Plan said "S01 tests still pass" which implied unchanged tests, but the refactored poll_feeds changed the internal mocking surface.
- **T03:** Added try/except import fallback in `app.py` for `services.feed_service` — not specified in plan but required because `spec_from_file_location` test loading doesn't resolve relative package imports.
- **T04:** Discover-feeds route reads both `url` and `feed_url` query params since htmx `hx-include` sends the input's `name` attribute.
- **T04:** Added 4 tests instead of 3 (added no-feeds empty case).

## Known Limitations

- `extract_article_content()` is implemented and tested but not yet called from `poll_feeds()` — full content extraction during polling is deferred to when reader UI (S03) can display it.
- `parse_feed()` (S01's old function) is kept with a deprecation docstring for backward compatibility but should be removed when S01 tests are fully migrated.
- Subscribe dialog doesn't have feed error indicator styling yet — that depends on S03's reader UI CSS.
- No OPML import wired through `subscribe()` yet — that's S05's scope.

## Follow-ups

- S03 should call `extract_article_content()` in the reading pane or as a background post-poll step to extract full article bodies for articles that only have summaries.
- The deprecated `parse_feed()` function in `app.py` can be removed once all tests use the new `fetch_feed() + parse_feed_content()` pattern.
- S04 will consume `FeedService.subscribe()` pattern and error tracking state for workspace contributions.
- S05 will consume `subscribe()` for OPML bulk import.

## Files Created/Modified

- `apps/rss-reader/services/__init__.py` — empty package marker (new)
- `apps/rss-reader/services/feed_service.py` — full FeedService with 11 public functions (new, ~450 lines)
- `apps/rss-reader/app.py` — refactored poll_feeds, added subscribe/discover routes, MAX_INITIAL_ARTICLES constant, import fallback
- `apps/rss-reader/requirements.txt` — added trafilatura>=2.0
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — working htmx form replacing S01 stub
- `backend/tests/test_feed_service.py` — 50 unit tests across 10 test classes (new)
- `backend/tests/test_rss_feed_parser.py` — 3 tests updated for refactored poll_feeds interface

## Forward Intelligence

### What the next slice should know
- FeedService is a stateless module — pure functions at the top, async SDK-parameterized methods below. Import it via `from services.feed_service import subscribe, ...` (or the try/except fallback for test contexts).
- The `subscribe()` function returns `{"status": "created"|"duplicate", "iri": str}` — callers should check status to handle dedup gracefully.
- `update_subscription_state()` is the single write surface for poll health — always call it after each feed poll attempt, whether success or failure.
- Conditional GET state (etag, lastModifiedHeader) is stored as RDF predicates on FeedSubscription objects and queried via `SUBSCRIPTIONS_WITH_STATE_SPARQL`.
- The `HX-Trigger: feedsChanged` pattern is established — any route that modifies feed subscriptions should emit this header for downstream UI refresh.

### What's fragile
- **Import fallback in app.py** — The try/except `spec_from_file_location` fallback for `services.feed_service` is necessary for test contexts where the app is loaded dynamically. If the services/ directory is renamed or restructured, both the normal import and the fallback path must be updated.
- **S01 test coupling** — Three S01 tests in `test_rss_feed_parser.py` were updated to mock the new `fetch_feed`/`parse_feed_content` imports. If feed_service internals change, these tests may need re-mocking.

### Authoritative diagnostics
- **Per-feed health:** SPARQL query `SELECT ?sub ?errorCount ?lastError WHERE { ?sub a <urn:sempkm:model:rss-feeds:FeedSubscription> . ?sub <urn:sempkm:model:rss-feeds:errorCount> ?errorCount . ?sub <urn:sempkm:model:rss-feeds:lastError> ?lastError }` — shows error state for all subscriptions. errorCount > 0 means consecutive failures; 0 means healthy.
- **Conditional GET hits:** `grep "304 Not Modified" /app/logs/rss-reader.log` — shows which feeds are returning cached responses (saves bandwidth).
- **Test suite:** `cd backend && .venv/bin/python -m pytest tests/test_feed_service.py -v` — 50 tests cover all FeedService functions including edge cases. This is the single command to verify S02 integrity.
- **trafilatura availability:** `python3 -c "from services.feed_service import HAS_TRAFILATURA; print(HAS_TRAFILATURA)"` — runtime check for content extraction capability.

### What assumptions changed
- **Original assumption:** S01 tests would be unchanged. **Actual:** 3 S01 poll-feeds tests required mock surface updates to match the refactored `poll_feeds()` implementation. The test count (38) didn't change but internal mocking targets did.
- **Original assumption:** trafilatura would be called during `poll_feeds()`. **Actual:** Content extraction is implemented as a standalone function but not yet wired into the poll cycle — deferred to when reader UI can display full article bodies.
