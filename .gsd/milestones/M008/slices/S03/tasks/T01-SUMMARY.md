---
id: T01
parent: S03
milestone: M008
provides:
  - base_embed.html minimal template for all iframe content
  - embed_wrapper.html for wrapping existing fragment templates as full pages
  - ?embed=1 query param on view, dashboard, and object endpoints
  - GET /browser/sparql-result/{query_id} endpoint for saved query HTML rendering
  - object_embed.html read-only object property table + markdown body
  - sparql_result_embed.html tabular SPARQL results with enriched labels
key_files:
  - backend/app/templates/base_embed.html
  - backend/app/templates/browser/embed_wrapper.html
  - backend/app/templates/browser/object_embed.html
  - backend/app/templates/browser/sparql_result_embed.html
  - backend/app/views/router.py
  - backend/app/dashboard/router.py
  - backend/app/browser/objects.py
  - backend/app/browser/sparql_result.py
  - backend/app/browser/router.py
  - backend/tests/test_canvas_embeds.py
key_decisions:
  - Render fragment to string then pass as content to embed_wrapper.html, rather than using Jinja2 {% include inner_template %} — simpler and avoids template variable scoping issues
  - SPARQL result endpoint lives in browser/sparql_result.py (new sub-router) registered before objects_router to avoid catch-all :path consumption
  - Reuse _execute_sparql and _enrich_sparql_results from sparql/router.py to avoid code duplication
patterns_established:
  - _embed_response() helper pattern for wrapping fragment templates in embed base
  - X-Embed-Mode response header on all embed responses for agent/test inspection
observability_surfaces:
  - X-Embed-Mode: 1 response header on all embed endpoint responses
  - SPARQL result endpoint returns 404 for unknown query IDs, 500 for execution failures
  - curl diagnostic: curl -sI 'host/browser/views/generic/table?embed=1' | grep X-Embed-Mode
duration: 1.5h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Embed template and endpoint support

**Created backend infrastructure for rendering views, dashboards, objects, and SPARQL results as standalone HTML pages for iframe embedding via ?embed=1.**

## What Happened

Built the complete embed endpoint layer across 4 template files and 5 endpoint modifications:

1. **base_embed.html** — minimal full HTML page with theme CSS, htmx, Lucide, marked, DOMPurify. No sidebar, no Cytoscape/dockview/CodeMirror/split.js/ninja-keys/driver.js. Only 5 script tags total vs 18+ in base.html.

2. **embed_wrapper.html** — extends base_embed, accepts pre-rendered fragment HTML as `{{ content | safe }}`. The `_embed_response()` helper in views/router.py renders fragment templates to strings first, then wraps them.

3. **View endpoints** — added `embed: int = Query(default=0)` to `generic_view()`. All three renderers (table, card, graph) gain embed support. When embed=1, the fragment is rendered to string and wrapped in embed_wrapper.html.

4. **Dashboard endpoint** — added `embed: int = Query(default=0)` to `render_dashboard()`. Same pattern: renders dashboard_page.html fragment to string, wraps in embed_wrapper.

5. **Object endpoint** — added `embed: int = Query(default=0)` to `get_object()`. When embed=1, renders the new `object_embed.html` directly (extends base_embed) instead of the full object_tab.html with flip container, favorites, edit form, etc. Shows just the type label, property table, and markdown body.

6. **SPARQL result endpoint** — new `GET /browser/sparql-result/{query_id}` in `browser/sparql_result.py`. Fetches saved query, executes via `_execute_sparql()`, enriches results, renders `sparql_result_embed.html` with HTML table. Registered as a sub-router in browser/router.py before objects_router (to avoid catch-all :path consumption).

7. **Unit tests** — created `tests/test_canvas_embeds.py` with 13 tests covering URL construction, document serialization with embed nodes, backward compat, and max embed enforcement logic.

## Verification

- **Unit tests**: 13/13 passed via `docker compose exec api python -m pytest tests/test_canvas_embeds.py -v`
- **Browser: table embed** (`/browser/views/generic/table?embed=1`): renders full HTML page with table content, "SemPKM Embed" title, no sidebar, filter input present. Script audit: 5 scripts total, no cytoscape/dockview/codemirror/split/ninja/driver.
- **Browser: object embed** (`/browser/object/{iri}?embed=1`): renders "Hierarchy Test Note" heading, type label, no edit form, no favorites star. X-Embed-Mode: 1 header present.
- **Browser: SPARQL result** (`/browser/sparql-result/{query_id}`): renders "All Objects" heading, "10 results", full HTML table with s/type columns showing real triplestore data. X-Embed-Mode: 1 header present.
- **X-Embed-Mode header**: confirmed via `fetch()` — present on embed responses, absent on non-embed responses.
- **404 handling**: `/browser/sparql-result/nonexistent-id` returns 404. Invalid UUID returns 404.
- **Backward compat**: non-embed endpoints work normally (no X-Embed-Mode header, same response as before).

### Slice-level verification status (partial — T01 is task 1 of 5):
- ✅ Unit tests pass
- ✅ Browser: `/browser/views/generic/table?embed=1` → table content, no sidebar
- ⬜ Browser: `/browser/dashboard/{id}?embed=1` → no test dashboards available, but endpoint code verified
- ✅ Browser: `/browser/sparql-result/{query_id}?embed=1` → HTML table of results
- ⬜ Browser: embed node via toolbar picker → T03
- ⬜ Browser: drag regular node → T02
- ⬜ Browser: save/reload → T05
- ⬜ Browser: 9th embed → T02
- ⬜ Browser: `exportState()` → T02
- ✅ Invalid query ID returns 404 (failure path diagnostic)
- ✅ X-Embed-Mode header on embed responses (diagnostic signal)

## Diagnostics

- **X-Embed-Mode header**: `curl -sI 'host/browser/views/generic/table?embed=1' | grep X-Embed-Mode` — returns `1` for embed mode, absent otherwise
- **SPARQL result errors**: 404 JSON body for unknown query IDs, 500 with detail message for execution failures — visible in browser network tab
- **Script audit**: view page source on any embed URL, search for `cytoscape|dockview|codemirror|split.js|ninja-keys|driver.js` — should find none
- **Template inheritance**: all 4 embed templates extend `base_embed.html`, not `base.html` — verified by absence of sidebar HTML

## Deviations

- Added `views.css` to `base_embed.html` — the table view fragment uses `.view-table` and other view-specific CSS classes that live in views.css, not workspace.css. Without it, the table styling breaks. This is a reasonable addition since views are a primary embed target.
- SPARQL result endpoint registered in browser/sparql_result.py sub-module rather than directly in sparql/router.py — the sparql router uses `/api` prefix but the embed endpoint needs `/browser` prefix, so a new browser sub-router was the cleanest fit.

## Known Issues

- Dashboard embed path could not be tested with real data (no dashboards exist in the test instance). The code is identical in pattern to the view embed and is verified by code inspection + 404 behavior for invalid IDs.

## Files Created/Modified

- `backend/app/templates/base_embed.html` — NEW: minimal base template for all iframe content (htmx + theme CSS + Lucide + marked/DOMPurify)
- `backend/app/templates/browser/embed_wrapper.html` — NEW: wrapper that takes pre-rendered fragment HTML
- `backend/app/templates/browser/object_embed.html` — NEW: read-only object view (type label + property table + markdown body)
- `backend/app/templates/browser/sparql_result_embed.html` — NEW: tabular SPARQL results with enriched labels
- `backend/app/views/router.py` — added `embed` param to `generic_view()`, `_embed_response()` helper
- `backend/app/dashboard/router.py` — added `embed` param to `render_dashboard()`
- `backend/app/browser/objects.py` — added `embed` param to `get_object()`
- `backend/app/browser/sparql_result.py` — NEW: SPARQL result embed sub-router
- `backend/app/browser/router.py` — registered sparql_result_router before objects_router
- `backend/tests/test_canvas_embeds.py` — NEW: 13 unit tests for embed URL construction, document serialization, backward compat
