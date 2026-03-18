---
id: T03
parent: S03
milestone: M010
provides:
  - Article reading pane route handler with SPARQL query and markdown body rendering (/_fragments/article-reading-pane)
  - Star toggle POST handler with SPARQL query + object.patch cycle (/_fragments/toggle-star)
  - Read toggle POST handler with fire-and-forget and explicit toggle modes (/_fragments/toggle-read)
  - Mark-all-read POST handler with batch object.patch (/_fragments/mark-all-read)
  - Unsubscribe POST handler calling feed_service.unsubscribe (/_fragments/unsubscribe)
  - Workspace views for Unread Articles and Starred Articles using filtered article-list
  - 30 unit tests covering all route handlers and edge cases
key_files:
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/article-reading-pane.html
  - apps/rss-reader/frontend/templates/star-button.html
  - apps/rss-reader/frontend/templates/unread-view.html
  - apps/rss-reader/frontend/templates/starred-view.html
  - backend/tests/test_rss_reader_ui.py
key_decisions:
  - Star button uses flat variables (is_starred, article_iri) not nested article dict — works both when included from reading pane (via {% set %}) and when rendered standalone from toggle-star route
  - Mark-all-read uses ctx.commands.bulk() for batch patching — consistent with poll-feeds article creation pattern
  - Toggle-read defaults to mark-as-read (fire-and-forget on article open) but supports explicit toggle via form param
patterns_established:
  - Star button micro-template pattern: standalone Jinja2 template with hx-swap="outerHTML" for self-replacing htmx component
  - Fire-and-forget mark-read via hidden div with hx-trigger="load" + hx-swap="none" — no visible response needed
  - HX-Trigger header convention: articleStateChanged for star/read changes, feedsChanged for subscription changes
observability_surfaces:
  - HX-Trigger: articleStateChanged after toggle-read/toggle-star; HX-Trigger: feedsChanged after unsubscribe
  - data-article-iri, data-starred, data-read attributes on reading pane root for diagnostic inspection
  - All handlers return <div class="rss-error"> fragments on SPARQL failures
  - curl /_fragments/article-reading-pane?article_iri=<IRI> returns full pane HTML
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Build reading pane + star/read/unsubscribe action handlers + workspace views

**Added 5 route handlers (reading pane, toggle-star, toggle-read, mark-all-read, unsubscribe), 3 templates, replaced 2 workspace view stubs, and wrote 30 passing unit tests.**

## What Happened

Implemented all user-facing interactivity for the RSS Reader UI:

1. **Article reading pane** (`/_fragments/article-reading-pane`): SPARQL query for single article fetching title, link, author, date, star/read state, body (from `urn:sempkm:body`), and feed title. Falls back to `dcterms:description` when no body. Embeds markdown in `<script type="text/plain">` with `data-md-source`/`data-md-target` attributes for reader.js to render via `renderMarkdownBody()`. Includes fire-and-forget mark-read on load for unread articles.

2. **Star toggle** (`/_fragments/toggle-star`): Queries current `isStarred` via SPARQL, flips it, patches via `object.patch`, returns updated star-button.html with inline SVG (filled star vs outline). Emits `HX-Trigger: articleStateChanged`.

3. **Read toggle** (`/_fragments/toggle-read`): Default marks as read (fire-and-forget). Supports explicit toggle mode via `toggle=true` form param. Returns empty 200 with `HX-Trigger: articleStateChanged`.

4. **Mark-all-read** (`/_fragments/mark-all-read`): Queries all unread articles (optionally filtered by feed), batch-patches to read via `ctx.commands.bulk()`. Returns refreshed feed sidebar HTML.

5. **Unsubscribe** (`/_fragments/unsubscribe`): Calls `feed_service.unsubscribe()` for soft-delete, returns refreshed sidebar with `HX-Trigger: feedsChanged`.

6. **Workspace views**: Replaced stubs with htmx containers loading `/_fragments/article-list?filter=unread` and `?filter=starred` respectively.

7. **Tests**: Created `test_rss_reader_ui.py` with 30 tests covering all handlers, edge cases (empty IRI, missing article, SPARQL errors, IRI sanitization, md_id determinism).

## Verification

- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` → syntax OK
- `grep` confirms all 5 route handler paths exist in app.py
- All templates exist: article-reading-pane.html, star-button.html
- unread-view.html contains `filter=unread`, starred-view.html contains `filter=starred`
- **30/30 tests pass** in `test_rss_reader_ui.py`
- **25/25 tests pass** in `test_app_proxy.py` (zero regressions)
- **77/77 tests pass** in `test_rss_feed_parser.py` + `test_feed_service.py` (zero regressions)
- **132 total tests pass** across all related test files

## Diagnostics

- `curl /_fragments/article-reading-pane?article_iri=<IRI>` — full reading pane HTML with data attributes
- `curl -X POST /_fragments/toggle-star -d article_iri=<IRI>` — updated star button HTML + `HX-Trigger: articleStateChanged` header
- `curl -X POST /_fragments/toggle-read -d article_iri=<IRI>` — empty body + `HX-Trigger: articleStateChanged` header
- `curl -X POST /_fragments/mark-all-read -d feed_iri=<IRI>` — refreshed sidebar HTML + `HX-Trigger: articleStateChanged` header
- `curl -X POST /_fragments/unsubscribe -d feed_iri=<IRI>` — refreshed sidebar HTML + `HX-Trigger: feedsChanged` header
- SPARQL errors produce `<div class="rss-error">` fragments with error messages

## Deviations

- **Tests written in T03 instead of T04**: The plan allocated T04 for tests, but tests are verification — writing them alongside the route handlers ensures correctness. T04 can add integration-level tests or increase coverage if needed.
- **Star button template uses flat variables**: Plan showed `article.is_starred` in the star template, but this doesn't work when rendered standalone from toggle-star (which passes `is_starred` directly). Used flat `is_starred`/`article_iri` variables with `{% set %}` in the including template.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/app.py` — Added `unsubscribe` import + 5 new route handlers (article-reading-pane, toggle-star, toggle-read, mark-all-read, unsubscribe)
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — New: reading pane with article header, markdown body, and fire-and-forget mark-read
- `apps/rss-reader/frontend/templates/star-button.html` — New: star toggle micro-template with inline SVG and hx-swap="outerHTML"
- `apps/rss-reader/frontend/templates/unread-view.html` — Replaced stub with htmx-driven filtered article list
- `apps/rss-reader/frontend/templates/starred-view.html` — Replaced stub with htmx-driven filtered article list
- `backend/tests/test_rss_reader_ui.py` — New: 30 unit tests for all route handlers and edge cases
- `.gsd/milestones/M010/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section
