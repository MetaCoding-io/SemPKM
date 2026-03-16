---
estimated_steps: 8
estimated_files: 8
---

# T01: Embed template and endpoint support

**Slice:** S03 — Live Embeds — Infrastructure, Types & Add UX
**Milestone:** M008

## Description

Create the backend infrastructure that makes views, dashboards, SPARQL results, and object read views loadable as standalone HTML pages for iframe embedding. This is purely backend work — no frontend canvas changes. Each endpoint gains `?embed=1` support that wraps content in a minimal `base_embed.html` template instead of the full `base.html` (which loads 15+ CDN scripts and the sidebar).

A new SPARQL result endpoint is needed because the existing SPARQL console renders results client-side via CodeMirror + custom JS — there's no server-rendered HTML for saved query results.

## Steps

1. **Create `base_embed.html`** at `backend/app/templates/base_embed.html`. Minimal full HTML page: doctype, `<html>`, `<head>` with theme CSS (`/static/css/theme.css`, `/static/css/style.css`, `/static/css/workspace.css`), htmx CDN, Lucide CDN. `<body>` with `{% block content %}{% endblock %}`. No sidebar, no Cytoscape/dockview/CodeMirror/split.js/ninja-keys/driver.js. Include marked + DOMPurify CDNs only (needed for object read markdown rendering). ~25 lines total. Add a Lucide `createIcons()` call at bottom of body.

2. **Create `embed_wrapper.html`** at `backend/app/templates/browser/embed_wrapper.html`. Extends `base_embed.html`, provides `{% block content %}` that includes the variable `{{ content | safe }}` or an inner template via `{% include inner_template %}`. This wrapper lets existing fragment templates be served as full pages. Decide on approach: if view templates are fragments, the endpoint should render the fragment to string and pass it as context; alternatively, use Jinja2 `{% include %}` with the template name as a variable.

3. **Add `embed` param to `generic_view()` in `backend/app/views/router.py`** (line 114). Add `embed: int = Query(default=0)` parameter. When `embed=1`, instead of returning the fragment template directly, render it inside `embed_wrapper.html`. The generic view handler already renders `table_view.html` / `cards_view.html` / `graph_view.html` as fragments — for embed mode, wrap the fragment HTML in the embed base. Use `templates.TemplateResponse("browser/embed_wrapper.html", {... , "inner_template": "browser/table_view.html"})` or render the fragment first and pass as content string.

4. **Add `embed` param to `render_dashboard()` in `backend/app/dashboard/router.py`** (line 148). Add `embed: int = Query(default=0)`. When embed=1, render `dashboard_page.html` inside `embed_wrapper.html`. Dashboard template is already a fragment that expects CSS Grid layout context.

5. **Add `embed` param to `get_object()` in `backend/app/browser/objects.py`** (line 53). Add `embed: int = Query(default=0)`. When embed=1, render a new `object_embed.html` template instead of the full `object_tab.html`. The embed template extends `base_embed.html` and renders only the property table + markdown body — no flip container, no favorites star, no edit form, no relations panel, no lint panel.

6. **Create `object_embed.html`** at `backend/app/templates/browser/object_embed.html`. Extends `base_embed.html`. Content block: type label heading, property table (iterate over form properties with label/value rows), markdown body rendered via `{{ body | safe }}`. Minimal styling — reuse existing `.object-read-*` CSS classes where applicable.

7. **Create SPARQL result endpoint** in `backend/app/sparql/router.py`. Add `GET /browser/sparql-result/{query_id}` route. Implementation: fetch saved query by ID from `QueryService`, execute via `_execute_sparql()`, enrich results via `_enrich_sparql_results()`, render `sparql_result_embed.html`. Route needs the `embed` param defaulting to 1 (this endpoint is primarily for embedding). Handle errors: 404 if query_id not found, 500 if SPARQL execution fails.

8. **Create `sparql_result_embed.html`** at `backend/app/templates/browser/sparql_result_embed.html`. Extends `base_embed.html`. Content block: query name as heading, HTML `<table>` with column headers from result variable names, rows from result bindings. IRI values rendered as `<span class="iri-pill">` with local name display. Simple, functional table — no CodeMirror, no custom JS table builder.

## Must-Haves

- [ ] `base_embed.html` loads htmx + theme CSS + Lucide + marked + DOMPurify — nothing else
- [ ] View endpoints (`/browser/views/generic/{renderer}?embed=1`) return valid full HTML pages
- [ ] Dashboard endpoint (`/browser/dashboard/{id}?embed=1`) returns valid full HTML page
- [ ] Object read endpoint (`/browser/object/{iri}?embed=1`) returns read-only property table + markdown body
- [ ] SPARQL result endpoint (`/browser/sparql-result/{query_id}`) returns HTML table of results
- [ ] No `base.html` inheritance in any embed template (no sidebar, no heavy CDN)
- [ ] All embed pages functional — htmx interactions work within the iframe context

## Verification

- Navigate to `http://localhost:3000/browser/views/generic/table?embed=1` in browser → see table with real data, no sidebar
- Navigate to a dashboard URL with `?embed=1` → see dashboard grid, no sidebar
- Navigate to an object URL with `?embed=1` → see property table + markdown, no edit form
- Navigate to `/browser/sparql-result/{query_id}` → see HTML table of query results
- View page source on each → confirm no Cytoscape/dockview/CodeMirror/split.js scripts loaded
- htmx interactions inside embed pages work (e.g., pagination in table view, filtering)

## Inputs

- Existing view templates: `table_view.html`, `cards_view.html`, `graph_view.html` — fragments without `<html>` wrapper
- Existing `dashboard_page.html` — fragment with CSS Grid layout
- Existing `_execute_sparql()` and `_enrich_sparql_results()` in sparql/router.py
- Existing `get_object()` in objects.py — heavy endpoint with 8 queries, full page context
- `base.html` as anti-example — shows what NOT to include (18 CDN scripts)

## Expected Output

- `backend/app/templates/base_embed.html` — minimal base template for all iframe content
- `backend/app/templates/browser/embed_wrapper.html` — wrapper for existing fragment templates
- `backend/app/templates/browser/object_embed.html` — stripped-down object read view
- `backend/app/templates/browser/sparql_result_embed.html` — tabular SPARQL results
- `backend/app/views/router.py` — `embed` param on `generic_view()`
- `backend/app/dashboard/router.py` — `embed` param on `render_dashboard()`
- `backend/app/browser/objects.py` — `embed` param on `get_object()`
- `backend/app/sparql/router.py` — new `/browser/sparql-result/{query_id}` endpoint

## Observability Impact

- **New signal:** All embed endpoints add `X-Embed-Mode: 1` response header when `embed=1` — lets agents/tests distinguish embed vs normal responses without parsing HTML
- **Failure visibility:** SPARQL result endpoint returns 404 JSON for unknown query IDs, 500 with error detail for SPARQL execution failures — both visible in browser network tab or curl
- **Inspection:** View page source on any embed URL to confirm no `base.html` inheritance — check for absence of `cytoscape`, `dockview`, `codemirror`, `split.js`, `ninja-keys` script tags
- **Diagnostic command:** `curl -sI 'http://localhost:3000/browser/views/generic/table?embed=1' | grep X-Embed-Mode` — quick health check for embed mode
