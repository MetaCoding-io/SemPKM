# S03: Reader UI (split-pane layout)

**Goal:** RSS Reader standalone page shows a functional split-pane layout with feed sidebar, article list, and reading pane — all driven by htmx fragment swaps against real SPARQL data.
**Demo:** User navigates to RSS Reader page → sees feed sidebar with subscriptions and unread counts → clicks a feed → article list filters to that feed → clicks an article → reading pane shows title, author, date, markdown-rendered body → star button toggles star state → article marked as read on open. "Unread Articles" and "Starred Articles" workspace views show filtered article lists.

## Must-Haves

- Split-pane layout: feed sidebar (left), article list (center), reading pane (right)
- Feed sidebar shows subscriptions with unread counts, error indicators, subscribe button
- Article list shows title, date, source, read/unread visual state, filtered by feed
- Reading pane shows article header (title, author, date, original link) + markdown-rendered body
- Star toggle persists via `object.patch` on `rss:isStarred`
- Mark-as-read fires on article open via `object.patch` on `rss:isRead`
- Mark-all-read for a feed via batch `object.patch`
- Unsubscribe (soft-delete) via `object.patch` on `rss:isActive`
- Unread Articles and Starred Articles workspace views show filtered article lists
- Platform proxy forwards query strings to app process (bug fix)
- App CSS uses platform theme variables, scoped under `.rss-reader`
- reader.js handles markdown rendering after htmx swap and Lucide icon refresh

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker stack for full verification, unit tests for route logic)
- Human/UAT required: yes (typography, layout usability)

## Verification

- `cd backend && python -m pytest tests/test_rss_reader_ui.py -v` — ≥20 tests pass covering all route handlers, SPARQL queries, star/read toggles, edge cases
- `cd backend && python -m pytest tests/test_app_proxy.py -v` — existing proxy tests pass + new query-string forwarding test
- `cd backend && python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — zero regressions on S01/S02 tests
- `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK
- `apps/rss-reader/manifest.yaml` includes `reader.js` in `frontend.js` array
- Diagnostic: route handlers return correct HX-Trigger headers for UI refresh after star/read/unsubscribe actions

## Observability / Diagnostics

- Runtime signals: `HX-Trigger: feedsChanged` after unsubscribe, `HX-Trigger: articleStateChanged` after star/read toggle
- Inspection surfaces: Each route handler returns HTML fragments with data attributes for testing (`data-feed-iri`, `data-article-iri`, `data-starred`, `data-read`)
- Failure visibility: Route handlers return `<div class="rss-error">` fragments with error messages on SPARQL failures
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `apps/rss-reader/app.py` (S01 skeleton + S02 routes), `apps/rss-reader/services/feed_service.py` (S02 subscribe/unsubscribe), `backend/app/apps/proxy.py` (platform proxy), `frontend/static/js/markdown-render.js` (client-side markdown), `frontend/static/css/theme.css` (CSS variables)
- New wiring introduced in this slice: 8 new route handlers in app.py, reader.js loaded via manifest, proxy query-string fix
- What remains before the milestone is truly usable end-to-end: S04 (workspace contributions + custom renderer), S05 (OPML import), S06 (E2E tests)

## Tasks

- [x] **T01: Fix proxy query-string forwarding + build reader shell, CSS, and reader.js** `est:30m`
  - Why: The proxy drops query strings (blocking all parametrized fragment requests). The reader shell defines the three-panel layout structure. CSS and JS are prerequisites for all subsequent templates.
  - Files: `backend/app/apps/proxy.py`, `backend/tests/test_app_proxy.py`, `apps/rss-reader/frontend/templates/reader.html`, `apps/rss-reader/frontend/static/styles.css`, `apps/rss-reader/frontend/static/reader.js`, `apps/rss-reader/manifest.yaml`
  - Do: (1) Fix `AppProxy.forward()` line ~87 to append `?{request.url.query}` when query string is non-empty. Add one test proving query params round-trip. (2) Replace reader.html stub with split-pane shell div structure using `hx-get` + `hx-trigger="load"` for each panel. (3) Write full styles.css with CSS Grid for the three-panel layout, using `var(--color-*)` theme tokens, all selectors scoped under `.rss-reader`. (4) Create reader.js with `htmx:afterSwap` handler for `renderMarkdownBody()` and `lucide.createIcons()`. (5) Add `reader.js` to manifest.yaml's `frontend.js` array.
  - Verify: `cd backend && python -m pytest tests/test_app_proxy.py -v` — all existing + new test pass. `reader.html` contains `hx-get="/_fragments/feed-sidebar"`. `styles.css` uses `.rss-reader` scope. `manifest.yaml` includes `reader.js` in js array.
  - Done when: Proxy forwards query strings, reader shell defines the three-panel layout with htmx lazy-load triggers, CSS defines the complete visual layout, reader.js handles post-swap markdown/icon rendering.

- [x] **T02: Build feed sidebar and article list route handlers + templates** `est:35m`
  - Why: The two left-side panels are the primary navigation surface. Feed sidebar shows subscriptions with unread counts. Article list shows articles filtered by feed with read/unread visual state. Both require SPARQL queries and Jinja2 templates.
  - Files: `apps/rss-reader/app.py`, `apps/rss-reader/frontend/templates/feed-sidebar.html`, `apps/rss-reader/frontend/templates/article-list.html`
  - Do: (1) Add `/_fragments/feed-sidebar` GET route handler — SPARQL query for subscriptions with unread counts (GROUP BY with COUNT), render `feed-sidebar.html`. Include subscribe button linking to existing subscribe dialog, error indicators when `errorCount > 0`. (2) Add `/_fragments/article-list` GET route handler — SPARQL query for articles filtered by optional `feed_iri` query param and `filter` param (all/unread/starred), ordered by `dcterms:created` DESC, LIMIT 100. Render `article-list.html`. (3) Create `feed-sidebar.html` — feed list items with `hx-get` to swap article list on click, unread count badges, active-feed highlight, subscribe button. (4) Create `article-list.html` — article items with title, relative date, source name, read/unread visual indicator (font-weight or opacity), `hx-get` to load reading pane on click. Handle empty states (no feeds, no articles). Format dates server-side in route handlers before passing to templates.
  - Verify: Both templates parse as valid Jinja2. Route handlers in `app.py` parse without syntax errors (`ast.parse`). SPARQL queries use correct type IRIs and property predicates from the rss-feeds model.
  - Done when: Feed sidebar and article list fragments load with real SPARQL data. Clicking a feed swaps the article list. Empty states render gracefully.

- [x] **T03: Build reading pane + star/read/unsubscribe action handlers + workspace views** `est:30m`
  - Why: The reading pane is the core reading experience. Star/read toggles and mark-all-read/unsubscribe are the user actions. Unread/starred workspace views complete the RSS-02 requirement.
  - Files: `apps/rss-reader/app.py`, `apps/rss-reader/frontend/templates/article-reading-pane.html`, `apps/rss-reader/frontend/templates/star-button.html`, `apps/rss-reader/frontend/templates/unread-view.html`, `apps/rss-reader/frontend/templates/starred-view.html`
  - Do: (1) Add `/_fragments/article-reading-pane` GET route — SPARQL query for single article (title, link, author, created, isStarred, isRead, body, feedTitle). Template shows article header + markdown body. Body stored as markdown in `urn:sempkm:body` — embed in `<script type="text/plain" id="md-source-{hash}">` for `renderMarkdownBody()`. If no body, fall back to `dcterms:description` or "No content available" with link to original. Fire-and-forget mark-read: include hidden div with `hx-post="/_fragments/toggle-read"` + `hx-trigger="load"` + `hx-swap="none"` when article is unread. (2) Add `/_fragments/toggle-star` POST route — reads `article_iri` from form body, queries current `isStarred`, patches to opposite value, returns updated `star-button.html`. (3) Add `/_fragments/toggle-read` POST route — reads `article_iri` from form, patches `isRead` to true (or toggles if explicit toggle requested). Returns empty 200 or updated indicator. (4) Add `/_fragments/mark-all-read` POST route — reads `feed_iri` from form, queries all unread articles for that feed, patches each to `isRead=true`. Returns updated feed sidebar fragment (with refreshed unread counts). (5) Add `/_fragments/unsubscribe` POST route — reads `feed_iri` from form, calls `unsubscribe()` from feed_service, returns updated feed sidebar. (6) Create `star-button.html` micro-template (just the star button with inline SVG, `hx-post` to toggle). (7) Replace `unread-view.html` and `starred-view.html` stubs — these render the article-list template with preset filters (isRead=false / isStarred=true). Add corresponding route handler logic to support `filter` param in article-list, or create dedicated handlers that call the same SPARQL with preset filters.
  - Verify: `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK. Templates contain `hx-post` for star/read toggles. Reading pane template includes markdown source element and `renderMarkdownBody` invocation setup.
  - Done when: Reading pane displays article content with markdown rendering. Star toggle and mark-read work via htmx POST. Unread/starred views show filtered articles.

- [x] **T04: Unit tests for all reader UI route handlers** `est:25m`
  - Why: Unit tests prove the route handler logic, SPARQL query construction, star/read toggle behavior, and edge cases without requiring a running Docker stack. This is the objective stopping condition for the slice.
  - Files: `backend/tests/test_rss_reader_ui.py`
  - Do: Create `test_rss_reader_ui.py` with mocked `ctx` (graph.query, commands.execute, render_template). Use the same `importlib.util.spec_from_file_location` pattern from S01/S02 tests to import route handler functions. Test: (1) Feed sidebar SPARQL returns correct structure with unread counts. (2) Article list with/without feed_iri filter. (3) Article list with unread/starred filter modes. (4) Reading pane returns article metadata and body. (5) Reading pane fallback when body is absent. (6) Star toggle calls object.patch with correct property and returns updated button. (7) Read toggle calls object.patch with isRead=true. (8) Mark-all-read queries unread articles and patches each. (9) Unsubscribe calls feed_service.unsubscribe. (10) Edge cases: no subscriptions, no articles, missing fields. (11) Proxy query-string forwarding test (in `test_app_proxy.py`).
  - Verify: `cd backend && python -m pytest tests/test_rss_reader_ui.py -v` — ≥20 tests pass. `cd backend && python -m pytest tests/test_app_proxy.py -v` — all tests pass including new query-string test.
  - Done when: ≥20 new tests in `test_rss_reader_ui.py` cover all route handlers and edge cases. Zero regressions on existing S01/S02 tests.

## Files Likely Touched

- `backend/app/apps/proxy.py` — one-line query-string fix
- `backend/tests/test_app_proxy.py` — one new test for query-string forwarding
- `backend/tests/test_rss_reader_ui.py` — new test file, ≥20 tests
- `apps/rss-reader/app.py` — 8 new route handlers replacing stubs
- `apps/rss-reader/manifest.yaml` — add reader.js to frontend.js
- `apps/rss-reader/frontend/templates/reader.html` — replace stub with split-pane shell
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — new template
- `apps/rss-reader/frontend/templates/article-list.html` — new template
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — new template
- `apps/rss-reader/frontend/templates/star-button.html` — new micro-template
- `apps/rss-reader/frontend/templates/unread-view.html` — replace stub
- `apps/rss-reader/frontend/templates/starred-view.html` — replace stub
- `apps/rss-reader/frontend/static/styles.css` — full reader CSS
- `apps/rss-reader/frontend/static/reader.js` — new JS file
