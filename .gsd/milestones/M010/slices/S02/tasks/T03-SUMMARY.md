---
id: T03
parent: S02
milestone: M010
provides:
  - "subscribe() — creates FeedSubscription via object.create with sha256-deterministic IRI and SPARQL dedup"
  - "unsubscribe() — soft-deletes subscription via object.patch (isActive=False)"
  - "update_subscription_state() — persists etag, lastPolled, errorCount, lastError to subscription object"
  - "mint_subscription_iri() — pure function returning deterministic IRI from feed URL"
  - "check_subscription_exists() — SPARQL query returning existing subscription IRI or None"
  - "SUBSCRIPTIONS_WITH_STATE_SPARQL — query for subscriptions with conditional GET state"
  - "poll_feeds() refactored to use fetch_feed + parse_feed_content + update_subscription_state"
  - "MAX_INITIAL_ARTICLES=50 caps first-time feed imports"
key_files:
  - apps/rss-reader/services/feed_service.py
  - apps/rss-reader/app.py
  - backend/tests/test_feed_service.py
key_decisions:
  - "try/except ImportError fallback in app.py for services.feed_service import — needed because S01 tests use importlib.util.spec_from_file_location without adding the app directory to sys.path"
  - "Soft delete for unsubscribe (isActive=False) rather than object.delete — preserves article references"
  - "Error count extracted from SPARQL binding dict with fallback to 0 — avoids extra SPARQL query per error"
patterns_established:
  - "_make_mock_ctx() helper for creating mock SDK AppContext with graph and commands clients"
  - "_make_sparql_binding() helper for constructing SPARQL result dicts matching SUBSCRIPTIONS_WITH_STATE_SPARQL"
  - "patch.object(_rss_mod, 'fetch_feed', ...) pattern for mocking FeedService calls in poll_feeds integration tests"
observability_surfaces:
  - "rss:errorCount and rss:lastError on FeedSubscription objects — queryable via SPARQL"
  - "rss:lastPolled updated on every poll attempt (success or failure)"
  - "rss:etag and rss:lastModifiedHeader persisted for conditional GET"
  - "Logger: poll_feeds logs '304 Not Modified: {url}' and 'Feed error for {url}: {error}, count now {n}'"
duration: ~20m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Implement subscription management, error tracking, and refactor poll-feeds to use FeedService

**Added subscription CRUD (subscribe/unsubscribe), per-feed error tracking, and refactored poll-feeds to use FeedService with conditional GET — 50 tests passing, zero S01 regressions.**

## What Happened

1. Added 5 subscription management functions to `feed_service.py`: `mint_subscription_iri` (deterministic sha256-based IRI), `check_subscription_exists` (SPARQL lookup), `subscribe` (object.create with dedup), `unsubscribe` (soft-delete via isActive=False), and `update_subscription_state` (object.patch for etag/lastPolled/errorCount/lastError).

2. Added `SUBSCRIPTIONS_WITH_STATE_SPARQL` query that fetches subscriptions with their etag and lastModifiedHeader for conditional GET support.

3. Refactored `poll_feeds()` in `app.py` to use `fetch_feed()` + `parse_feed_content()` instead of the old `feedparser.parse(url)`. The refactored version: sends conditional GET headers from stored subscription state, handles 304 Not Modified (skips parsing, updates lastPolled), tracks errors per-feed (increments errorCount on failure, resets to 0 on success), and caps first-time imports to 50 articles via `MAX_INITIAL_ARTICLES`.

4. Added 28 new tests across subscription management (8), error tracking (5), and poll-feeds integration (4), plus helper infrastructure. Total: 50 tests in test_feed_service.py.

## Verification

- `cd backend && python -m pytest tests/test_feed_service.py -v` — **50 passed** (28 new + 22 existing)
- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — **23 passed** (zero regressions)
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"` — syntax OK
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('OK')"` — syntax OK

### Slice-level verification (partial — T03 is 3rd of 4 tasks):
- ✅ `test_feed_service.py` — 50 tests pass (≥35 target met)
- ✅ `test_rss_feed_parser.py` — 23 S01 tests pass
- ✅ Both source files parse cleanly
- ✅ services package exists
- ✅ Error tracking tests verify correct object.patch params
- ✅ Conditional GET tests verify 304 handling and header forwarding
- ⏳ Subscribe dialog template — T04

## Diagnostics

- `rss:errorCount` integer on FeedSubscription: increments on consecutive failures, resets to 0 on success
- `rss:lastError` string on FeedSubscription: stores the exception message from the last failure
- `rss:lastPolled` ISO timestamp: updated on every poll attempt regardless of outcome
- `rss:etag` / `rss:lastModifiedHeader`: persisted after each successful fetch for next conditional GET
- All subscription state is queryable via SPARQL: `SELECT ?prop ?val WHERE { <sub_iri> ?prop ?val }`

## Deviations

- **Import fallback in app.py**: The plan specified `from services.feed_service import ...` but S01 tests use `importlib.util.spec_from_file_location` to load app.py, which doesn't set up the module search path for the sibling `services` package. Added a try/except ImportError block that falls back to path-relative importlib loading. This is the minimal change that keeps both runtime and test imports working.

- **28 new tests instead of 12**: Added more thorough coverage (IRI format validation, default title fallback, lastPolled writing) since the test infrastructure was already in place. 

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/services/feed_service.py` — Added subscription management functions (mint_subscription_iri, check_subscription_exists, subscribe, unsubscribe, update_subscription_state), SUBSCRIPTIONS_WITH_STATE_SPARQL query, and domain constants (SUBSCRIPTION_TYPE, RSS_NS)
- `apps/rss-reader/app.py` — Refactored poll_feeds to use FeedService (fetch_feed + parse_feed_content + update_subscription_state), added MAX_INITIAL_ARTICLES=50, kept old parse_feed with deprecation note, added try/except import fallback for services.feed_service
- `backend/tests/test_feed_service.py` — Added 28 new tests: subscription IRI (3), subscribe (3), unsubscribe (1), update_subscription_state (5), poll-feeds integration (4), plus test helpers (_make_mock_ctx, _make_sparql_binding, _make_poll_ctx)
