# S09: Admin Model Detail Stats & Charts — Research

**Date:** 2026-03-12

## Summary

S09 replaces two TODO placeholders on the admin model detail page's analytics back-face with real computed data and visual charts. The current template (`model_detail.html` lines ~203 and ~233) shows "—" dashes for avg connections and last modified, and placeholder bars for link distribution. The existing `get_type_analytics()` method in `ModelService` already queries instance counts and top nodes by incoming link count from `urn:sempkm:current`. Extending it with three additional SPARQL queries (avg connections, last modified, link distribution histogram) and adding a lightweight chart library covers the full scope.

Chart.js (4.x) via CDN is the recommended charting library — it's the most widely used canvas-based chart library, supports sparklines and bar charts with minimal config, and can be included per-page via the existing `{% block scripts %}` mechanism without loading it globally. The alternative (inline SVG sparklines) would avoid a dependency but requires significantly more code for bar charts and interactivity.

Growth trend requires correlating events with types. Events are stored as named graphs (`urn:sempkm:event:{uuid}`) with `sempkm:timestamp`, `sempkm:operationType`, and `sempkm:affectedIRI`. To compute a per-type growth trend, we query events where `operationType` contains "object.create" and the affected IRI has `rdf:type` matching the type IRI in `urn:sempkm:current`. This is a cross-graph join (events graph + current graph) but is feasible since we limit to recent events with timestamp filters.

## Recommendation

**Extend `ModelService.get_type_analytics()` with three new SPARQL queries per type, add Chart.js via CDN in the model_detail template's `{% block scripts %}`, and replace the TODO placeholders with real data and canvas elements.**

Specifically:
1. **Avg connections per node** — Count all non-`rdf:type` triples where the subject or object is an instance of the type; divide by instance count. Single SPARQL aggregate query per type.
2. **Last modified** — Query `dcterms:modified` for instances of each type, take the MAX. Falls back to event timestamp if no `dcterms:modified` exists.
3. **Growth trend** — Count `object.create` events per week (last 8 weeks) whose `affectedIRI` is a current instance of the type. Returns weekly counts for a sparkline.
4. **Link distribution** — Already partially present as "top nodes by incoming links." Extend to return a histogram (buckets: 0, 1-2, 3-5, 6-10, 11+) for a horizontal bar chart.

Chart.js loaded only on model_detail.html via `{% block scripts %}`. Charts rendered via inline `<script>` after the data is available in template context (JSON-serialized via Jinja2 `|tojson` filter).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Sparkline / bar chart rendering | Chart.js 4.x via CDN | Battle-tested, canvas-based, small footprint (~60KB gzipped), supports all needed chart types. htmx-compatible (no framework dependency). |
| Instance count per type | `ModelService.get_type_analytics()` | Already implemented and working — queries `urn:sempkm:current` with batch `SELECT ... GROUP BY ?type`. |
| Top nodes by link count | `get_type_analytics()` top_nodes query | Already implemented — returns top 5 nodes ordered by incoming link count. |
| Template JSON serialization | Jinja2 `|tojson` filter | Built into Jinja2, auto-escapes for safe JS embedding. |

## Existing Code and Patterns

- `backend/app/services/models.py` — `get_type_analytics()` (line ~630) already queries instance counts and top nodes. New stats (avg connections, last modified, growth, link distribution) should be added here as additional keys in the returned dict.
- `backend/app/admin/router.py` — `admin_model_detail()` (line ~72) already calls `get_type_analytics()` and merges results into `type_map`. The new stats flow through the same pattern — no router changes needed beyond passing chart data to template context.
- `backend/app/templates/admin/model_detail.html` — Lines ~203 (TODO: avg connections, last modified, growth trend) and ~233 (TODO: sparkline chart, link distribution). Replace `.analytics-todo` divs and `.analytics-placeholder` div.
- `frontend/static/css/style.css` — `.analytics-todo`, `.todo-val`, `.analytics-placeholder`, `.placeholder-bar`, `.placeholder-label` classes (lines ~1401-1493) are the TODO styling that gets replaced/removed.
- `backend/app/templates/base.html` — Line 112: `{% block scripts %}{% endblock %}` — per-page script injection point for Chart.js CDN.
- `backend/app/events/models.py` — Event metadata predicates: `sempkm:timestamp`, `sempkm:operationType`, `sempkm:affectedIRI`. Used for growth trend queries.
- `backend/app/events/query.py` — Reference for SPARQL patterns querying event named graphs (cross-graph `GRAPH ?event { ... }` with `FILTER(STRSTARTS(...))`).

## Constraints

- **SPARQL only** — All stats come from SPARQL queries against `urn:sempkm:current` (instance data) and `urn:sempkm:event:*` named graphs (activity data). No SQL tables involved.
- **Per-page Chart.js loading** — Must not add Chart.js to `base.html` globally. Use `{% block scripts %}` to load it only on the model detail page.
- **No new endpoints** — All data flows through the existing `GET /admin/models/{model_id}` endpoint. Stats are computed server-side and passed as template context.
- **htmx compatibility** — Chart.js canvas elements need re-initialization when the page is loaded via htmx partial swap (the tab is already loaded once via full page load or htmx). The flip card `transitionend` handler must trigger chart rendering after the analytics face is visible.
- **Event graph query performance** — Growth trend queries scan event named graphs. These are cross-graph queries with timestamp filters. For large event stores, this could be slow. Mitigate with tight timestamp bounds (last 8 weeks only) and LIMIT clauses.
- **`dcterms:modified` availability** — Only objects that have been edited (not just created) have `dcterms:modified`. Fallback to event timestamps for recently created but unmodified objects. The growth trend query using events is more reliable than `dcterms:modified` for activity tracking.

## Common Pitfalls

- **Chart.js canvas sizing in hidden containers** — Chart.js reads canvas dimensions on initialization. If the analytics card face is `display:none` (via `.face-hidden`) when Chart.js initializes, the canvas has 0×0 dimensions and renders nothing. **Mitigation:** Initialize charts lazily — only when the flip card reveals the analytics face. Use the existing `flipCard()` `transitionend` callback to trigger chart init.
- **htmx re-renders destroying chart instances** — If the model detail page is re-loaded via htmx (e.g., tab switch back to schema and then back), Chart.js instances must be destroyed before re-creating. **Mitigation:** Store chart instances in a lookup object keyed by type local_name; destroy before re-init. Or use the `Chart.getChart(canvas)` API to check for existing instances.
- **Cross-graph event queries returning duplicate affected IRIs** — Events can have multiple `sempkm:affectedIRI` values (e.g., object.create + edge.create compound events). The growth trend query must `DISTINCT` count by affected IRI, not by event graph. **Mitigation:** Use `COUNT(DISTINCT ?affected)` and filter `operationType` to only `object.create`.
- **Empty data states** — Types with 0 instances should show "No data" in chart areas, not empty/broken charts. Chart.js handles empty datasets gracefully but the template should also show a text fallback.
- **Jinja2 `|tojson` in inline scripts** — Must use `{{ data|tojson }}` not `{{ data }}` to avoid XSS from label strings containing quotes or HTML. Jinja2's `tojson` filter handles this correctly.

## Open Risks

- **Event graph scan performance** — Growth trend queries over 8 weeks of events could be slow if there are thousands of events. The query scans all `urn:sempkm:event:*` named graphs. If this becomes a bottleneck, consider caching or materializing weekly counts. Risk is low for typical SemPKM usage (hundreds, not millions of events).
- **RDF4J cross-graph SPARQL support** — The growth trend query joins event graphs (for timestamps) with the current graph (for `rdf:type`). RDF4J supports this natively via `GRAPH` clauses, but performance characteristics vary. If the cross-graph join is too slow, fallback to a simpler approach: count all `object.create` events per week (ignoring type) and show a model-wide sparkline instead of per-type.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Chart.js | N/A | none found — Chart.js is simple enough to use from CDN with inline config |
| SPARQL / RDF | N/A | none found — project-specific patterns in codebase |
| Jinja2 / htmx | N/A | none found — existing patterns well-established in codebase |

## Sources

- Existing codebase: `backend/app/services/models.py`, `backend/app/admin/router.py`, `backend/app/templates/admin/model_detail.html`
- Existing codebase: `backend/app/events/query.py` for SPARQL event query patterns
- Existing codebase: `backend/app/events/models.py` for event RDF vocabulary
- Existing codebase: `frontend/static/css/style.css` for analytics CSS classes
- Chart.js documentation (source: [Chart.js](https://www.chartjs.org/docs/latest/))
