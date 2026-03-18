---
id: S03
parent: M010
milestone: M010
provides:
  - Platform proxy query-string forwarding fix (all apps benefit)
  - RSS Reader three-panel split-pane layout (feed sidebar, article list, reading pane)
  - 7 htmx fragment route handlers (feed-sidebar, article-list, article-reading-pane, toggle-star, toggle-read, mark-all-read, unsubscribe)
  - Client-side reader.js (markdown rendering via data-md-source/data-md-target, Lucide icon refresh, j/k keyboard nav)
  - Complete reader CSS (~330 lines, all scoped under .rss-reader, using theme variables)
  - Star toggle and mark read/unread controls via htmx POST with HX-Trigger headers
  - Unread Articles and Starred Articles workspace views
  - 43 unit tests covering all route handlers, edge cases, and helper functions
requires:
  - slice: S01
    provides: Installed rss-feeds model with type IRIs, working app process serving fragments on UDS, ctx.render_template()
affects:
  - S04
  - S06
key_files:
  - backend/app/apps/proxy.py
  - backend/tests/test_app_proxy.py
  - backend/tests/test_rss_reader_ui.py
  - apps/rss-reader/app.py
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/frontend/templates/reader.html
  - apps/rss-reader/frontend/templates/feed-sidebar.html
  - apps/rss-reader/frontend/templates/article-list.html
  - apps/rss-reader/frontend/templates/article-reading-pane.html
  - apps/rss-reader/frontend/templates/star-button.html
  - apps/rss-reader/frontend/templates/unread-view.html
  - apps/rss-reader/frontend/templates/starred-view.html
  - apps/rss-reader/frontend/static/styles.css
  - apps/rss-reader/frontend/static/reader.js
key_decisions:
  - data-md-source / data-md-target attribute convention for reader.js markdown rendering hook — all templates embedding markdown must use these attributes
  - Star button uses flat template variables (is_starred, article_iri) not nested dict — works both standalone and when included from reading pane
  - Mark-all-read uses ctx.commands.bulk() for batch patching — consistent with poll-feeds article creation pattern
  - Toggle-read defaults to mark-as-read (fire-and-forget on article open) with explicit toggle mode via form param
  - IRI sanitization via re.sub (removing angle brackets and unsafe chars) rather than urllib.parse.quote — keeps IRIs readable in SPARQL
patterns_established:
  - _sparql_bool(value, default) and _sparql_int(value, default) helpers for SPARQL binding normalization — reuse in any handler consuming SPARQL results
  - _format_date(iso_str) for ISO 8601 date formatting — handles Z suffix and timezone offsets
  - Star button micro-template pattern — standalone Jinja2 with hx-swap="outerHTML" for self-replacing htmx component
  - Fire-and-forget mark-read via hidden div with hx-trigger="load" + hx-swap="none" — no visible response needed
  - HX-Trigger header convention: articleStateChanged for star/read changes, feedsChanged for subscription changes
  - Filter tabs preserve active_feed in hx-get URLs so feed filtering persists across filter changes
  - _make_mock_request(ctx, query_params, form_data) pattern for testing Starlette route handlers with async form() mocking
observability_surfaces:
  - HX-Trigger: articleStateChanged emitted after toggle-star and toggle-read actions
  - HX-Trigger: feedsChanged emitted after unsubscribe and mark-all-read actions
  - data-feed-iri, data-article-iri, data-starred, data-read attributes on fragment elements for diagnostic inspection
  - SPARQL failures caught and rendered as <div class="rss-error"> fragments with error messages
  - Empty states rendered as .rss-empty-state divs — testable via DOM queries
drill_down_paths:
  - .gsd/milestones/M010/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T04-SUMMARY.md
duration: 48m
verification_result: passed
completed_at: 2026-03-17
---

# S03: Reader UI (split-pane layout)

**Split-pane RSS Reader UI with feed sidebar (unread counts), article list (filter tabs), reading pane (markdown-rendered body), star/read toggles, unsubscribe, and workspace views — all htmx-driven with 43 unit tests.**

## What Happened

Four tasks built the complete reader UI surface for the RSS Reader app:

**T01 — Platform fix + shell + CSS + JS:** Fixed a platform-wide bug where `AppProxy.forward()` dropped query strings from proxied requests. This was blocking all parametrized fragment requests (e.g., `?feed_iri=...`, `?filter=unread`). Built the three-panel reader shell in `reader.html` using CSS Grid with htmx lazy-load triggers. Created ~330 lines of CSS scoped under `.rss-reader` covering feed items, article list read/unread states, reading pane typography, star button states, empty states, and a loading spinner. Created `reader.js` as an IIFE handling `htmx:afterSwap` for markdown rendering (via `data-md-source`/`data-md-target` attribute convention), Lucide icon refresh, and j/k keyboard navigation with wrap-around.

**T02 — Feed sidebar + article list:** Added two SPARQL-driven fragment endpoints. `feed_sidebar_fragment()` uses GROUP BY/COUNT aggregation to show subscriptions with unread counts and error indicators. `article_list_fragment()` builds dynamic SPARQL filtered by optional `feed_iri` and `filter` (all/unread/starred) params, with IRI sanitization via regex. Created helper functions `_format_date()`, `_sparql_bool()`, `_sparql_int()` for binding normalization. Templates include filter tab pills, unread badges, subscribe button, and empty states.

**T03 — Reading pane + action handlers + workspace views:** Added five more route handlers: article reading pane (SPARQL query for single article with markdown body in `<script type="text/plain">` for client-side rendering), toggle-star (queries current state, flips, patches), toggle-read (fire-and-forget default, explicit toggle mode), mark-all-read (batch patches via `ctx.commands.bulk()`), and unsubscribe (delegates to `feed_service.unsubscribe()`). All action handlers emit HX-Trigger headers for UI refresh. Replaced workspace view stubs with htmx containers loading filtered article lists.

**T04 — Unit tests:** Created 43 tests organized into 8 test classes covering all 7 route handlers plus helper functions. Tests use mocked SDK context with the `_make_mock_request()` pattern for Starlette handler testing. Coverage includes SPARQL query structure, template argument passing, star/read toggle logic, batch operations, error handling, and edge cases (empty IRI, missing article, SPARQL errors).

## Verification

- `pytest tests/test_rss_reader_ui.py -v` — **43 passed** (0.39s)
- `pytest tests/test_app_proxy.py -v` — **25 passed** (includes 2 new query-string tests)
- `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — **77 passed** (zero S01/S02 regressions)
- **145 total tests** across all related test files pass
- `ast.parse` on `app.py` — syntax OK
- `manifest.yaml` includes `reader.js` in `frontend.js` array
- HX-Trigger headers confirmed on all 5 action route handlers
- `data-md-source`/`data-md-target` attributes confirmed on reading pane template
- All templates contain `data-*` diagnostic attributes for testability

## Requirements Advanced

- **RSS-02** — Reader UI with split-pane layout: Feed sidebar, article list, reading pane all implemented with htmx fragments. Star toggle and mark read/unread controls work. Clean typography via CSS. Awaits live runtime validation in S06.
- **RSS-01** — Feed subscription and polling: Unsubscribe handler added (soft-delete via `object.patch` on `rss:isActive`). Feed error indicators displayed in sidebar.
- **RSS-06** — Workspace contributions: Unread Articles and Starred Articles views implemented as filtered article-list loads. Command palette entries remain for S04.

## Requirements Validated

- None — live runtime verification required (S06 E2E tests) before marking RSS-02/RSS-06 as validated.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **Tests written in T03 instead of T04:** T03 wrote the initial 30 tests alongside route handlers for immediate verification. T04 then expanded to 43 tests, adding helper function tests and additional edge cases. Net result exceeded the ≥20 test target.
- **CSS additions in T02:** Filter tab and article metadata styles added to `styles.css` alongside template creation — not called out in the plan but required for the templates to render correctly.

## Known Limitations

- **No live runtime testing:** All verification is unit-test-based with mocked SDK context. Live Docker stack verification deferred to S06 E2E tests.
- **Markdown rendering depends on platform's marked.js:** The `renderMarkdownBody()` function is provided by the platform's `markdown-render.js`. If the platform function signature changes, `reader.js` will break silently.
- **IRI sanitization is heuristic:** Uses `re.sub` to strip angle brackets and unsafe characters from IRIs injected into SPARQL. Not a full SPARQL injection defense — relies on app SDK trust boundary.

## Follow-ups

- S04 needs the reader template patterns (article list rendering, reading pane, fragment endpoints) and `reader.css`/`reader.js` styling patterns established here.
- S06 E2E tests should use `data-article-iri`, `data-feed-iri`, `data-starred`, `data-read` attributes as test selectors — they're stable and diagnostic-friendly.

## Files Created/Modified

- `backend/app/apps/proxy.py` — 2-line fix appending query string to target_url
- `backend/tests/test_app_proxy.py` — 2 new tests + 5 existing tests patched with `.url.query = None`
- `backend/tests/test_rss_reader_ui.py` — **new**, 43 unit tests for all route handlers
- `apps/rss-reader/app.py` — 8 new route handlers (FEED_SIDEBAR_SPARQL, helpers, 7 fragment endpoints)
- `apps/rss-reader/manifest.yaml` — added reader.js to frontend.js
- `apps/rss-reader/frontend/templates/reader.html` — three-panel CSS Grid shell with htmx lazy-load
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — feed list with unread badges, error indicators, subscribe button
- `apps/rss-reader/frontend/templates/article-list.html` — filter tabs, article items with read/unread/starred state
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — article header + markdown body + fire-and-forget mark-read
- `apps/rss-reader/frontend/templates/star-button.html` — star toggle micro-template with hx-swap="outerHTML"
- `apps/rss-reader/frontend/templates/unread-view.html` — replaced stub with htmx filtered article list (filter=unread)
- `apps/rss-reader/frontend/templates/starred-view.html` — replaced stub with htmx filtered article list (filter=starred)
- `apps/rss-reader/frontend/static/styles.css` — complete reader CSS (~330 lines, .rss-reader scoped)
- `apps/rss-reader/frontend/static/reader.js` — IIFE with markdown rendering, Lucide icons, j/k keyboard nav

## Forward Intelligence

### What the next slice should know
- All fragment endpoints follow the pattern `/_fragments/{name}` with GET for reads and POST for mutations.
- Star button is a self-replacing htmx component — it returns its own replacement HTML with `hx-swap="outerHTML"`. S04's custom renderer can reuse this pattern.
- Workspace views (`unread-view.html`, `starred-view.html`) are thin wrappers loading `/_fragments/article-list?filter=<mode>`. S04 should register these as app view contributions via the manifest, not duplicate the templates.
- The `_sparql_bool()` and `_sparql_int()` helpers in `app.py` are not extracted to a shared module — if S04/S05 need them, they should import from `app.py` or extract to a `utils.py`.

### What's fragile
- `reader.js` depends on `renderMarkdownBody()` from platform's `markdown-render.js` existing in the global scope — if the platform renames or moves this function, reading pane markdown won't render.
- IRI sanitization in `article_list_fragment()` uses `re.sub(r'[<>"{}|\\^`]', '', iri)` — this is a minimal defense, not a full SPARQL parameterization. Acceptable because all IRIs originate from the app's own data, but fragile if external IRIs are ever passed in.

### Authoritative diagnostics
- `pytest tests/test_rss_reader_ui.py -v` — 43 named tests directly exercising each route handler with mocked context. Fastest signal for regressions.
- `document.querySelectorAll('[data-article-iri]')` in browser console — counts rendered articles in the article list.
- HX-Trigger headers in browser DevTools network tab — confirm star/read/unsubscribe actions emit correct refresh events.

### What assumptions changed
- Plan assumed T04 would be the only test task. In practice, T03 wrote 30 tests alongside route handlers (immediate verification), and T04 expanded to 43 total. The boundary between "build" and "test" tasks was fluid.
- Plan noted proxy query-string fix as a "one-line fix" — it was actually 2 lines in proxy.py plus 5 lines updating existing mock requests (`.url.query = None`) to prevent the new code path from processing truthy Mock objects as query strings.
