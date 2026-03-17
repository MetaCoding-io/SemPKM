---
estimated_steps: 5
estimated_files: 4
---

# T04: Wire subscribe route, feed discovery endpoint, and working dialog template

**Slice:** S02 — Feed service + content extraction + feed management
**Milestone:** M010

## Description

Closes the user-facing loop for S02 — users can subscribe to feeds by URL and discover feeds from website URLs. The subscribe route calls `FeedService.subscribe()`, the discover route calls `discover_feeds_from_html()`, and the dialog template provides the htmx form. This satisfies RSS-01 (user subscribes to feeds by URL) and RSS-08 (feed discovery from website URLs).

The subscribe dialog will be enhanced in S03 (reader UI) with better styling and integration into the reader page, but the functional form and route must work now so that the poll-feeds task has subscriptions to poll.

## Steps

1. Add route handlers to `apps/rss-reader/app.py`:

   **POST `/_fragments/subscribe`:**
   - Read form body: `feed_url = (await request.form()).get("feed_url", "").strip()` and `title = (await request.form()).get("title", "").strip() or None`.
   - Validate: if not `feed_url`, return HTML error fragment `<div class="rss-error">Please enter a feed URL</div>`.
   - Import `subscribe` from `services.feed_service`.
   - Call `result = await subscribe(ctx, feed_url, title=title)`.
   - If `result["status"] == "duplicate"`, return `<div class="rss-info">Already subscribed to this feed</div>`.
   - If `result["status"] == "created"`, return `<div class="rss-success">Subscribed to feed!</div>` with an HX-Trigger header `feedsChanged` to let the reader UI refresh.
   - On exception, return `<div class="rss-error">Failed: {error}</div>`.
   - Route method: `methods=["POST"]`.

   **GET `/_fragments/discover-feeds`:**
   - Read query param: `url = request.query_params.get("url", "").strip()`.
   - Validate: if not `url`, return HTML error.
   - Fetch the URL: `response = await ctx.http.get(url, follow_redirects=True)`.
   - Import `discover_feeds_from_html` from `services.feed_service`.
   - Call `feeds = discover_feeds_from_html(response.text, url)`.
   - Render HTML list of discovered feeds. Each feed has a button to pre-fill the subscribe form: `<button hx-get="..." hx-target="#feed-url-input" hx-swap="outerHTML">Subscribe to {feed.title or feed.url}</button>`.
   - If no feeds found, return `<div class="rss-info">No feeds found at that URL</div>`.
   - On HTTP error, return `<div class="rss-error">Could not fetch URL: {error}</div>`.

2. Update `apps/rss-reader/frontend/templates/subscribe-dialog.html`:
   - Replace the stub with a working htmx form:
   ```html
   <div id="rss-subscribe-dialog" class="rss-subscribe-form">
     <h3>Subscribe to Feed</h3>
     <form hx-post="/_fragments/subscribe" hx-target="#subscribe-result" hx-swap="innerHTML">
       <div class="form-group">
         <label for="feed-url-input">Feed URL</label>
         <input type="url" id="feed-url-input" name="feed_url"
                placeholder="https://example.com/feed.xml" required
                class="form-input">
       </div>
       <div class="form-group">
         <label for="feed-title-input">Title (optional)</label>
         <input type="text" id="feed-title-input" name="title"
                placeholder="My Favorite Blog"
                class="form-input">
       </div>
       <div class="form-actions">
         <button type="button"
                 hx-get="/_fragments/discover-feeds"
                 hx-include="#feed-url-input"
                 hx-target="#discover-result"
                 hx-swap="innerHTML"
                 class="btn btn-secondary">Discover Feeds</button>
         <button type="submit" class="btn btn-primary">Subscribe</button>
       </div>
     </form>
     <div id="discover-result"></div>
     <div id="subscribe-result"></div>
   </div>
   ```
   - Note: The `hx-post` and `hx-get` URLs need to be prefixed with the app's proxy path when rendered. Use the SDK's template context which should provide the app base URL. Check if `ctx.render_template()` injects an `app_base_url` variable. If not, the routes are relative to the app's own UDS server and the platform proxy handles the `/app/rss-reader/` → UDS forwarding, so relative paths like `/_fragments/subscribe` should work.

3. Update the existing `subscribe_dialog_fragment()` route handler in app.py (the GET handler already exists from S01 as a stub). Keep it as-is — it already renders the template which we just updated.

4. Write tests in `backend/tests/test_feed_service.py`:

   **Route handler tests (≥3):**
   - `test_subscribe_route_success` — verify that calling subscribe with a new URL calls `FeedService.subscribe()` and returns success (test the subscribe function directly, not the HTTP route — route testing is for E2E)
   - `test_subscribe_route_duplicate` — verify subscribe with existing URL returns duplicate status
   - `test_discover_feeds_with_real_html` — pass realistic HTML with multiple `<link>` tags through `discover_feeds_from_html()`, verify all discovered correctly

   Note: Route handler tests are integration tests that need a running Starlette app. Since we're doing contract-level testing, test the FeedService functions that the routes call. Route HTTP testing is deferred to S06 E2E.

5. Run final verification:
   - `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥37 total tests pass
   - `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — S01 tests pass
   - `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('OK')"`
   - Verify template syntax: `python3 -c "print(open('apps/rss-reader/frontend/templates/subscribe-dialog.html').read()[:50])"` — starts with `<div`

## Must-Haves

- [ ] POST `/_fragments/subscribe` route creates subscription from form data and returns HTML result
- [ ] GET `/_fragments/discover-feeds` route discovers feeds from a website URL and returns HTML list
- [ ] `subscribe-dialog.html` has working htmx form with URL input, title input, discover button, and subscribe button
- [ ] Error cases (empty URL, duplicate subscription, fetch failure) return user-friendly HTML messages
- [ ] ≥3 new tests (≥37 cumulative) pass
- [ ] All syntax checks pass (app.py, feed_service.py, template)

## Verification

- `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥37 cumulative tests pass
- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — 23 S01 tests still pass (zero regressions)
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('OK')"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"` — syntax valid
- `test -s apps/rss-reader/frontend/templates/subscribe-dialog.html` — template is non-empty

## Inputs

- `apps/rss-reader/services/feed_service.py` — from T01+T02+T03, with all FeedService functions
- `apps/rss-reader/app.py` — from T03, with refactored poll-feeds and existing stub routes
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — current stub from S01: `<div id="rss-subscribe-dialog" class="rss-dialog-stub"><h3>Subscribe to Feed</h3><p>Feed subscription dialog — coming in S03.</p></div>`
- `backend/tests/test_feed_service.py` — from T01+T02+T03, with ≥34 tests

## Observability Impact

- **POST `/_fragments/subscribe` route logging:** Logs subscription creation success/duplicate/error at INFO level via `logging.getLogger(__name__)`. On failure, returns user-facing HTML error fragment — the error message text is the observable signal for debugging.
- **GET `/_fragments/discover-feeds` route logging:** Logs HTTP fetch outcomes when discovering feeds. Returns discovered-feed count or error HTML fragment.
- **How to inspect:** Both routes return HTML fragments with CSS classes (`rss-success`, `rss-error`, `rss-info`) that encode the outcome — inspectable via browser DevTools or htmx response headers.
- **HX-Trigger header:** On successful subscription, `feedsChanged` custom event is emitted — downstream reader UI components can observe this to refresh feed lists.
- **Failure state:** Subscribe errors surface as `<div class="rss-error">` fragments; discover errors include the HTTP status or exception message in the fragment text.

## Expected Output

- `apps/rss-reader/app.py` — updated with POST subscribe route, GET discover-feeds route
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — working htmx form replacing stub
- `backend/tests/test_feed_service.py` — ≥37 total tests
