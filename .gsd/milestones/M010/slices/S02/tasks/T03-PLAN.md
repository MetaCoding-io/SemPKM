---
estimated_steps: 6
estimated_files: 3
---

# T03: Implement subscription management, error tracking, and refactor poll-feeds to use FeedService

**Slice:** S02 — Feed service + content extraction + feed management
**Milestone:** M010

## Description

This is the integration task — wiring FeedService into the existing app. Adds subscription CRUD (subscribe/unsubscribe), per-feed error tracking (errorCount/lastError/lastPolled via `object.patch`), and refactors the poll-feeds task handler to use `FeedService.fetch_feed()` + `parse_feed_content()` instead of S01's inline `feedparser.parse(url)`. This replaces urllib-based fetching with SDK-enforced HTTP, adds conditional GET support, and updates subscription state after each poll.

The subscribe method is a boundary contract consumed by S05 (OPML import) — it must be a clean standalone function that creates a FeedSubscription from a URL.

**Relevant skills:** test (for pytest patterns)

## Steps

1. Add subscription management functions to `apps/rss-reader/services/feed_service.py`:

   **`def mint_subscription_iri(feed_url: str) -> str`**
   - Pure function. Returns `urn:sempkm:app:rss-reader:sub-{sha256(feed_url)}`.
   - Deterministic from feed URL — prevents duplicate subscriptions.

   **`async def check_subscription_exists(graph_client, feed_url: str) -> str | None`**
   - SPARQL ASK/SELECT: `SELECT ?sub WHERE { ?sub a <SUBSCRIPTION_TYPE> . ?sub <rss:feedUrl> ?feedUrl } LIMIT 1`
   - Return the subscription IRI if exists, None otherwise.

   **`async def subscribe(ctx, feed_url: str, title: str | None = None) -> dict`**
   - Call `check_subscription_exists()`. If exists, return `{"status": "duplicate", "iri": existing_iri}`.
   - Mint subscription IRI via `mint_subscription_iri(feed_url)`.
   - Build properties dict: `rss:feedUrl` = feed_url, `dcterms:title` = title or feed_url, `rss:errorCount` = 0, `rss:lastError` = "".
   - Call `ctx.commands.execute("object.create", {"iri": iri, "type": SUBSCRIPTION_TYPE, "properties": props})`.
   - Return `{"status": "created", "iri": iri}`.
   - Import constants from `app.py` or define locally: `SUBSCRIPTION_TYPE = "urn:sempkm:model:rss-feeds:FeedSubscription"`, `RSS_NS = "urn:sempkm:model:rss-feeds:"`.

   **`async def unsubscribe(ctx, subscription_iri: str) -> dict`**
   - Verify subscription exists via SPARQL ASK.
   - Call `ctx.commands.execute("object.patch", {"iri": subscription_iri, "properties": {f"{RSS_NS}isActive": False}})` — soft delete (mark inactive rather than hard delete, preserves article references).
   - Return `{"status": "unsubscribed", "iri": subscription_iri}`.

   **`async def update_subscription_state(ctx, sub_iri: str, last_polled: str | None = None, etag: str | None = None, last_modified: str | None = None, error_count: int | None = None, last_error: str | None = None) -> None`**
   - Build properties dict from non-None params: `rss:lastPolled`, `rss:etag`, `rss:lastModifiedHeader`, `rss:errorCount`, `rss:lastError`.
   - Call `ctx.commands.execute("object.patch", {"iri": sub_iri, "properties": props})`.
   - Skip the call if all params are None (no update needed).

2. Add a SPARQL query for fetching subscription details with etag/lastModifiedHeader to `feed_service.py`:

   ```python
   SUBSCRIPTIONS_WITH_STATE_SPARQL = f"""
   SELECT ?sub ?feedUrl ?title ?etag ?lastModified WHERE {{
       ?sub a <{SUBSCRIPTION_TYPE}> .
       ?sub <{RSS_NS}feedUrl> ?feedUrl .
       OPTIONAL {{ ?sub <http://purl.org/dc/terms/title> ?title }}
       OPTIONAL {{ ?sub <{RSS_NS}etag> ?etag }}
       OPTIONAL {{ ?sub <{RSS_NS}lastModifiedHeader> ?lastModified }}
   }}
   """
   ```

3. Refactor `poll_feeds()` in `apps/rss-reader/app.py`:
   - Import from `services.feed_service`: `fetch_feed`, `parse_feed_content`, `update_subscription_state`, `FeedFetchError`, `SUBSCRIPTIONS_WITH_STATE_SPARQL`.
   - Replace the old `SUBSCRIPTIONS_SPARQL` with `SUBSCRIPTIONS_WITH_STATE_SPARQL` to get etag/lastModifiedHeader.
   - For each subscription binding:
     - Extract `etag` and `lastModified` from SPARQL results.
     - Call `content, headers, status = await fetch_feed(ctx.http, feed_url, etag=etag, last_modified=last_mod)`.
     - If status == 304: log "Not modified", update lastPolled, continue.
     - Call `parsed = parse_feed_content(content, headers.get("content_type", ""))`.
     - Continue with existing dedup + bulk create logic.
     - On success: `await update_subscription_state(ctx, sub_iri, last_polled=now_iso, etag=headers.get("etag"), last_modified=headers.get("last_modified"), error_count=0, last_error="")`.
     - On `FeedFetchError` or any exception: query current `errorCount` (or default 0), increment, `await update_subscription_state(ctx, sub_iri, last_polled=now_iso, error_count=current+1, last_error=str(e))`.
   - Add `MAX_INITIAL_ARTICLES = 50` constant. When creating articles for a feed, if `len(new_articles) > MAX_INITIAL_ARTICLES`, keep only the most recent 50 (sort by published date, or just take the first 50 from the feed since feeds are typically reverse-chronological).
   - Keep `entry_to_article()`, `_mint_article_iri()`, `_time_struct_to_iso()`, and `get_existing_article_iris()` in app.py — they're already tested and consumed by S01 tests.
   - Keep the old `parse_feed()` function but add a deprecation docstring — S01 tests import it.

4. Write tests in `backend/tests/test_feed_service.py`:

   **Subscription tests (≥5):**
   - `test_mint_subscription_iri_deterministic` — same URL produces same IRI
   - `test_mint_subscription_iri_different_urls` — different URLs produce different IRIs
   - `test_subscribe_creates_correct_params` — mock ctx, verify object.create called with SUBSCRIPTION_TYPE and correct properties
   - `test_subscribe_dedup_returns_existing` — mock check_subscription_exists returning IRI, assert status="duplicate"
   - `test_unsubscribe_patches_inactive` — mock ctx, verify object.patch called

   **Error tracking tests (≥4):**
   - `test_update_state_success_resets_error` — call with error_count=0, last_error="", assert correct object.patch params
   - `test_update_state_failure_increments` — call with error_count=3, last_error="404 Not Found", assert params
   - `test_update_state_with_etag` — call with etag and last_modified, assert rss:etag and rss:lastModifiedHeader in params
   - `test_update_state_skips_when_all_none` — call with all None, assert object.patch not called

   **Poll-feeds integration test (≥3):**
   - `test_poll_feeds_uses_conditional_get` — mock full flow, verify fetch_feed called with etag from SPARQL
   - `test_poll_feeds_handles_304` — mock 304 response, verify no articles created, lastPolled still updated
   - `test_max_initial_articles_capped` — generate 100 mock entries, verify only 50 articles passed to bulk

5. Verify all tests pass: `cd backend && python -m pytest tests/test_feed_service.py -v`

6. Verify S01 tests still pass: `cd backend && python -m pytest tests/test_rss_feed_parser.py -v`

## Must-Haves

- [ ] `subscribe()` creates FeedSubscription via object.create with deterministic IRI from sha256(feed_url)
- [ ] `subscribe()` returns duplicate status when subscription already exists (SPARQL ASK dedup)
- [ ] `unsubscribe()` soft-deletes subscription via object.patch
- [ ] `update_subscription_state()` builds correct object.patch params for etag, lastPolled, errorCount, lastError
- [ ] `update_subscription_state()` skips HTTP call when all params are None
- [ ] Poll-feeds uses `fetch_feed()` instead of `feedparser.parse(url)` — all HTTP goes through SDK HttpClient
- [ ] Poll-feeds sends conditional GET headers (etag/lastModified from subscription SPARQL query)
- [ ] Poll-feeds updates subscription state after each feed (success resets error, failure increments)
- [ ] `MAX_INITIAL_ARTICLES = 50` caps first-time feed imports
- [ ] S01 tests (`test_rss_feed_parser.py`) still pass — no regressions
- [ ] ≥12 new tests (≥34 cumulative) pass

## Verification

- `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥34 cumulative tests pass
- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — 23 S01 tests still pass
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('OK')"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"` — syntax valid

## Observability Impact

- Signals added/changed: poll-feeds now logs conditional GET results ("304 Not Modified: {url}", "Fetched {url}: {len(content)} bytes"); error tracking logs ("Feed error for {url}: {error}, count now {n}")
- How a future agent inspects this: SPARQL query for `rss:errorCount` and `rss:lastError` on any FeedSubscription IRI; `update_subscription_state` params are fully visible in test assertions
- Failure state exposed: `rss:lastError` stores the exception message string; `rss:errorCount` is an integer that increments on consecutive failures and resets to 0 on success

## Inputs

- `apps/rss-reader/services/feed_service.py` — from T01+T02, with `parse_json_feed`, `discover_feeds_from_html`, `parse_feed_content`, `fetch_feed`, `extract_article_content`, `FeedFetchError`
- `apps/rss-reader/app.py` — from S01, with poll-feeds task handler, `entry_to_article()`, constants
- `backend/tests/test_feed_service.py` — from T01+T02, with ≥22 existing tests
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — CommandClient API: `execute(command_type, params)` returns response dict; `bulk(summary, source)` context manager
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — GraphClient API: `query(sparql)` returns SPARQL JSON results dict
- S01 constants: `ARTICLE_TYPE = "urn:sempkm:model:rss-feeds:Article"`, `SUBSCRIPTION_TYPE = "urn:sempkm:model:rss-feeds:FeedSubscription"`, `RSS_NS = "urn:sempkm:model:rss-feeds:"`
- S01 Forward Intelligence: `entry._feed_url` side effect must be preserved; `_mint_article_iri` is deterministic; poll-feeds expects subscriptions to exist

## Expected Output

- `apps/rss-reader/services/feed_service.py` — updated with `mint_subscription_iri`, `check_subscription_exists`, `subscribe`, `unsubscribe`, `update_subscription_state`, `SUBSCRIPTIONS_WITH_STATE_SPARQL`
- `apps/rss-reader/app.py` — poll-feeds refactored to use FeedService (fetch_feed + parse_feed_content + update_subscription_state); MAX_INITIAL_ARTICLES constant added; old parse_feed kept with deprecation note
- `backend/tests/test_feed_service.py` — updated with ≥12 additional tests (≥34 cumulative)
