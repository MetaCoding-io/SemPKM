# S05: Interactive Dashboards — Cross-View Context — Research

**Date:** 2026-03-15

## Summary

This slice builds the cross-view context mechanism that makes dashboards interactive: clicking a row in one view-embed block filters another view-embed block in the same dashboard via parameterized SPARQL. This requires three coordinated changes:

1. **Frontend event wiring** — Table rows in dashboard-embedded views emit a `sempkm:dashboard-context-changed` custom event carrying the selected IRI. Target blocks listen for this event and re-fetch with the IRI as a query parameter.

2. **Backend parameterized queries** — ViewSpecService gains an `inject_values_binding()` function that takes an IRI and a SPARQL variable name, and injects a `VALUES ?var { <iri> }` clause into the WHERE body. The view rendering endpoints (`table_view`, `cards_view`) accept an optional `context_iri` query parameter.

3. **Block configuration** — View-embed blocks gain two new config keys: `emits_context` (bool — row clicks emit context events) and `listens_to_context` (string — the SPARQL variable to bind the context IRI to, e.g. `?project`). The dashboard page template wires these via data attributes.

The htmx `hx-trigger` + `from:body` pattern is proven in this codebase (favorites, comments, ontology) and maps directly to this use case. The VALUES clause injection follows the existing pattern used in 15+ places across the codebase.

## Recommendation

**Approach: Implicit IRI context with VALUES injection**

The simplest viable approach. A dashboard has one implicit context variable — the selected IRI. Source blocks export it, consumer blocks bind it to a named SPARQL variable.

**Why not explicit named variables?** The research doc (dashboard-builder-and-workflows.md) discusses Retool-style state management with multiple named variables. That's overengineered for v1 — a single context IRI covers the primary use case (select project → filter notes). Multiple context variables can be layered on later without breaking the single-IRI API.

**Flow:**

```
[Table row click]
    → JS: document.dispatchEvent(new CustomEvent('sempkm:dashboard-context-changed', { detail: { iri, dashboardId } }))
    → htmx: consumer block has hx-trigger="sempkm:dashboard-context-changed from:body"
    → htmx: re-fetches block endpoint with ?context_iri=<selected_iri>
    → Backend: render_block() passes context_iri to view rendering
    → ViewSpecService: inject_values_binding() adds VALUES ?var { <iri> } to WHERE body
    → RDF4J: executes parameterized query, returns filtered results
    → htmx: swaps consumer block innerHTML with filtered view
```

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Custom event → re-fetch | htmx `hx-trigger="event from:body"` | Proven in favorites (D048), comments, ontology. Zero custom JS for the re-fetch. |
| IRI validation before SPARQL interpolation | `_validate_iri()` in `browser/_helpers.py` | Blocks SPARQL injection chars (`<`, `>`, `"`, whitespace). Already tested (test_iri_validation.py). |
| Batch IRI binding in SPARQL | VALUES clause pattern | Used 15+ places across codebase (labels, canvas, ontology, VFS). RDF4J handles it reliably. |
| WHERE body extraction | `_extract_where_body()` in `views/service.py` | Regex-based brace-depth parser. Already handles nested braces. |
| Block rendering dispatch | `render_block()` in `dashboard/router.py` | Existing block type dispatch with htmx lazy-loading. Just needs context_iri passthrough. |

## Existing Code and Patterns

- `backend/app/dashboard/router.py` — `render_block()` dispatches by block type. View-embed blocks generate htmx `hx-get` to `/browser/views/{renderer}/{spec_iri}`. This is the injection point: append `?context_iri=X` to the URL when the block's config says `listens_to_context`.
- `backend/app/dashboard/models.py` — `DashboardSpec` stores blocks as JSON. Block config dict needs two new optional keys: `emits_context` (bool), `listens_to_context` (str — SPARQL variable name without `?`).
- `backend/app/views/service.py` — `execute_table_query()` and `execute_cards_query()` both extract WHERE body, inject filters, and execute. Adding a VALUES clause follows the same `_extract_where_body()` → string injection pattern as `filter_clause`.
- `backend/app/views/router.py` — `table_view()` and `cards_view()` endpoints accept Query params. Adding `context_iri: str = Query(default="")` is trivial.
- `backend/app/templates/browser/dashboard_page.html` — Renders CSS Grid with `hx-get` block slots. Needs `data-emits-context` and `data-listens-to-context` attributes plus a `<script>` block for event wiring.
- `backend/app/templates/browser/table_view.html` — Table rows have `onclick="openTab()"`. Dashboard-embedded rows need `onclick` to emit context event instead. Detect via a `dashboard_mode` template variable or a wrapping `data-dashboard-block` attribute.
- `frontend/static/js/workspace-layout.js` — Uses `CustomEvent` for `sempkm:tab-activated`. Same pattern for `sempkm:dashboard-context-changed`.
- `backend/app/browser/_helpers.py` — `_validate_iri()` for safe IRI validation before VALUES injection.
- `backend/app/templates/browser/dashboard_builder.html` — Block config UI. Needs new fields: "Emits context" checkbox and "Context variable" text input for view-embed blocks.

## Constraints

- **No string interpolation in SPARQL** — VALUES clause injection only. The context IRI must be angle-bracket-quoted inside a VALUES clause, never interpolated into arbitrary query positions. `_validate_iri()` must gate all incoming IRIs.
- **htmx-first** — Re-fetch must use htmx `hx-trigger` + `hx-get` pattern, not manual `fetch()` calls. The codebase is htmx-driven; mixing in fetch for view rendering would create an inconsistent pattern.
- **Dashboard-scoped events** — The custom event `detail` must carry `dashboardId` so consumer blocks in other dashboards (other tabs) don't react to unrelated context changes.
- **Block rendering returns HTML** — `render_block()` returns `HTMLResponse` strings. The htmx re-fetch mechanism means the consumer block's `hx-get` URL must include the context_iri as a query parameter, which means the dashboard page template needs JS to rewrite the URL on context change.
- **View spec SPARQL variable must exist** — The `listens_to_context` variable (e.g., `project`) must actually appear as `?project` in the view spec's SPARQL query. If it doesn't, the VALUES clause is harmless (RDF4J ignores unused bindings) but the filter has no effect. No validation needed — just document it.

## Common Pitfalls

- **htmx hx-get URL rewriting on event** — htmx's `hx-trigger` fires a new request using the element's current `hx-get` URL. To pass `context_iri`, we can't just add a query param to a static URL. Two approaches: (a) use `hx-vals` with `js:` prefix to dynamically inject the context IRI, or (b) use `htmx:configRequest` event to rewrite params. Approach (b) is proven in the codebase (D087 — tag autocomplete). Use `htmx:configRequest` to inject `context_iri` from a JS variable scoped to the dashboard container.
- **Table row click dual behavior** — In a dashboard, clicking a table row should emit context (not open an object tab). Outside a dashboard, it should open a tab as usual. The table_view template needs a conditional: if rendered inside a dashboard block with `emits_context`, emit context event; otherwise, `openTab()`. Detect via a query parameter like `?dashboard_mode=1` passed from the block endpoint.
- **Graph renderer blocks** — Graph views use Cytoscape.js, not htmx table rows. Node click → context event requires Cytoscape event listener, not table row onclick. For v1, limit context emission to table and card renderers. Graph can be added later.
- **Race condition on initial load** — Dashboard blocks load lazily via `hx-trigger="load"`. If a consumer block loads before the source block, the consumer has no context. This is fine — consumer shows unfiltered results until first context event. No special handling needed.
- **VALUES clause placement** — The VALUES clause must go inside the WHERE body, not before it. `_extract_where_body()` returns the body content. Prepend the VALUES clause to the extracted body before reassembly. Same position as `filter_clause` injection.

## Open Risks

- **Nested htmx swaps** — View-embed blocks contain htmx content (the table view itself has htmx-driven pagination, sorting, filtering). When the block is re-fetched via context change, the inner htmx elements are replaced entirely. Pagination state resets to page 1. This is acceptable (filtering changes the result set, so page 1 is correct), but worth documenting.
- **Card view context emission** — Cards don't have a single clickable row like tables. The card flip animation uses the front face for display and back face for details. Context emission from card click needs a dedicated "Select" action on each card, not the flip. For v1, context emission from cards can be deferred — tables are the primary use case.
- **Performance on large result sets** — Each context change triggers a full re-fetch: block endpoint → view endpoint → SPARQL query. For dashboards with 3+ consumer blocks, this means 3+ SPARQL queries per click. Acceptable for v1 with typical data volumes (hundreds, not millions of objects).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | ecelayes/roots-skills@htmx-universal-patterns | available (24 installs) — possibly useful for htmx event patterns but low install count; codebase already has proven patterns |
| SPARQL/RDF | (no relevant skills found) | none found |

No skills recommended for installation — the codebase's existing htmx and SPARQL patterns are sufficient.

## Sources

- Existing codebase patterns: htmx `hx-trigger from:body` (D048/favorites), `htmx:configRequest` (D087/tag autocomplete), VALUES clause injection (15+ call sites)
- htmx docs: custom event triggering with `HX-Trigger` header and `from:body` modifier (source: [htmx headers docs](https://htmx.org/headers/hx-trigger/))
- Research doc: `docs/research/dashboard-builder-and-workflows.md` — Airtable-style record context flowing between widgets
- Decision D103: Dashboard builder uses `fetch()` not htmx for JSON API — same fetch-based pattern can dispatch context events
- Decision D104: JS-dispatched htmx trigger for explorer refresh — same pattern for context events
