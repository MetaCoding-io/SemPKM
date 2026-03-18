---
id: T03
parent: S02
milestone: M010
provides:
  - subscribe() — creates FeedSubscription with deterministic IRI and SPARQL dedup
  - unsubscribe() — soft-deletes subscription via object.patch isActive=False
  - update_subscription_state() — persists etag, lastPolled, errorCount, lastError
  - mint_subscription_iri() — deterministic IRI from sha256(feed_url)
  - check_subscription_exists() — SPARQL check for duplicate subscriptions
  - SUBSCRIPTIONS_WITH_STATE_SPARQL — query returning subs with conditional GET state
  - MAX_INITIAL_ARTICLES=50 cap on first-time feed imports
  - poll-feeds refactored to use fetch_feed + parse_feed_content + update_subscription_state
key_files:
  - apps/rss-reader/services/feed_service.py
  - apps/rss-reader/app.py
  - backend/tests/test_feed_service.py
  - backend/tests/test_rss_feed_parser.py
key_decisions:
  - try/except import fallback in app.py for services.feed_service — resolves via file path when loaded by spec_from_file_location in test context
  - Soft-delete for unsubscribe (isActive=False) rather than hard delete — preserves article references
  - SimpleNamespace→dict conversion in poll_feeds for JSON Feed entries — entry_to_article expects dict interface
patterns_established:
  - patch("rss_reader_app_svc.fetch_feed") pattern for mocking feed_service imports in poll_feeds integration tests
  - _make_mock_ctx_for_poll() helper builds complete mock AppContext with bulk context manager
observability_surfaces:
  - rss:errorCount and rss:lastError on FeedSubscription objects — queryable via SPARQL for per-feed health
  - rss:lastPolled — ISO 8601 timestamp of last poll attempt per subscription
  - rss:etag and rss:lastModifiedHeader — persisted conditional GET state per subscription
  - poll-feeds logs "304 Not Modified: {url}" and "Fetched {url}: {n} bytes" for conditional GET observability
  - poll-feeds logs "Feed error for {url}: {error}, count now {n}" on failure
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Implement subscription management, error tracking, and refactor poll-feeds to use FeedService

**Added subscription CRUD (subscribe/unsubscribe), per-feed error tracking, and refactored poll-feeds to use FeedService with conditional GET and MAX_INITIAL_ARTICLES=50 cap; 46 cumulative tests pass with zero S01 regressions.**

## What Happened

Added 5 subscription management functions to `feed_service.py`: `mint_subscription_iri()` (deterministic SHA-256 IRI), `check_subscription_exists()` (SPARQL dedup), `subscribe()` (object.create with dedup check), `unsubscribe()` (soft-delete via isActive=False), and `update_subscription_state()` (object.patch for etag/lastPolled/errorCount/lastError). Added `SUBSCRIPTIONS_WITH_STATE_SPARQL` query that returns subscription details with conditional GET state.

Refactored `poll_feeds()` in `app.py` to replace the old `parse_feed(url)` direct-fetch with `fetch_feed()` + `parse_feed_content()` from FeedService. The new implementation: (1) queries subscriptions with etag/lastModifiedHeader via SPARQL, (2) passes conditional GET headers to `fetch_feed()`, (3) handles 304 Not Modified by updating only lastPolled, (4) dispatches content via `parse_feed_content()` for format-aware parsing, (5) caps new articles at `MAX_INITIAL_ARTICLES=50`, (6) updates subscription state after each feed (success resets error, failure increments errorCount and sets lastError).

The old `parse_feed()` function was kept with a deprecation docstring for S01 test backward compatibility. Three S01 tests that exercised `poll_feeds` were updated to mock the new `fetch_feed`/`parse_feed_content`/`update_subscription_state` functions instead of the old `parse_feed`, and to use the new SPARQL binding key `feedUrl` instead of `url`.

Used a try/except import pattern in `app.py` to handle the `services.feed_service` import — falls back to `importlib.util.spec_from_file_location` when loaded in test context where the relative package isn't on sys.path.

## Verification

- 46 tests pass in `test_feed_service.py` (31 from T01+T02 + 15 new)
- 38 tests pass in `test_rss_feed_parser.py` (zero S01 regressions)
- Both `feed_service.py` and `app.py` pass `ast.parse()` syntax validation

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `.venv/bin/python -m pytest tests/test_feed_service.py -v` | 0 | ✅ pass | 0.30s |
| 2 | `.venv/bin/python -m pytest tests/test_rss_feed_parser.py -v` | 0 | ✅ pass | 0.28s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Per-feed error tracking:** SPARQL query for `rss:errorCount` and `rss:lastError` on any FeedSubscription IRI reveals health status. Consecutive failures increment errorCount; success resets to 0.
- **Conditional GET state:** `rss:etag` and `rss:lastModifiedHeader` are persisted per subscription and forwarded on subsequent poll cycles.
- **Test assertions verify:** `update_subscription_state()` params are fully visible in test assertions — check `test_success_resets_error`, `test_failure_increments`, `test_with_etag_and_last_modified`, `test_skips_when_all_none`.
- **Poll-feeds integration:** `test_uses_conditional_get` verifies etag forwarding; `test_handles_304_no_articles_created` verifies 304 skip behavior; `test_max_initial_articles_capped` verifies 50-article cap.

## Deviations

- Updated 3 S01 tests in `test_rss_feed_parser.py` to match the refactored `poll_feeds` interface (binding key `feedUrl` instead of `url`, mock `fetch_feed`/`parse_feed_content` instead of `parse_feed`). This was necessary because the plan said "S01 tests still pass" but the refactored poll_feeds changes the mocking surface.
- Added try/except import fallback in `app.py` — not specified in plan but required because `spec_from_file_location` test loading doesn't resolve relative package imports.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/services/feed_service.py` — added `mint_subscription_iri`, `check_subscription_exists`, `subscribe`, `unsubscribe`, `update_subscription_state`, `SUBSCRIPTIONS_WITH_STATE_SPARQL`, constants
- `apps/rss-reader/app.py` — refactored `poll_feeds` to use FeedService, added `MAX_INITIAL_ARTICLES=50`, added try/except import fallback, added deprecation docstring to `parse_feed`
- `backend/tests/test_feed_service.py` — added 15 tests: subscription management (5), error tracking (5), poll-feeds integration (4), IRI minting (1 additional via subscribe test)
- `backend/tests/test_rss_feed_parser.py` — updated 3 S01 poll_feeds tests to match refactored interface
