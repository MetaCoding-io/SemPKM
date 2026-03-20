# M031 — Views Overhaul, Saved Queries as First-Class, & UI Polish

## Goal

Overhaul the views system so users control what they see through the explorer sidebar, not through an in-view carousel picker. Make saved queries prominent throughout the UI. Fix several UX gaps in SPARQL console, ontology viewer, admin model graph, and dashboard/workflow builders.

## Background

The current views system has a "carousel tab bar" rendered inside each view that lets users switch between renderers (table/card/graph). But the explorer sidebar already has explicit menu entries for "Table View", "Cards View", "Graph View" — the user has already chosen. The carousel is redundant and confusing.

Additionally, saved queries were designed to be first-class citizens in the UI but currently only appear in the SPARQL console and as "promoted views" in a mostly-broken "Saved Views" folder in the sidebar. They need to be surfaced everywhere: explorer, VFS, spatial canvas, views (as scope), and object browser dropdown.

## Scope

### 1. Views Overhaul

**Remove the carousel picker.** When a user clicks "Graph View" in the explorer, they get a graph view — no in-view switcher. The type filter pills at the top stay (useful for quick sub-filtering).

**Saved query scoping.** Each view (table, card, graph, kanban) should accept an optional saved query as its data scope. Instead of "show all objects", it shows "objects matching this query". The view toolbar should have a dropdown to select/change the scope query.

**Multiple view instances.** Users can open multiple instances of the same view type as tabs (e.g., two graph views with different query scopes). Each is ephemeral until the user explicitly saves it as a named view. Saved views appear in the "Saved Views" folder in the explorer and can be reopened.

**New kanban renderer.** Status-based kanban view. Columns are status values (todo, in-progress, done, cancelled, or whatever status-like field the type declares). Drag-drop to change status. Uses the same data pipeline as other views (type filter + optional query scope).

**Full height.** All views must use 100% of available height. No unnecessary scrolling of the view container itself.

**Graph tooltip z-index.** The graph view's node popover is hidden underneath the top toolbar. Fix z-index stacking.

### 2. Fix & Enhance Saved Views

The "Saved Views" folder in the explorer (`views_explorer.html`) lazily loads from `/browser/my-views`. The backend (`workspace.py:my_views`, `query_service.py:promote_query/list_promoted_views`) exists but the UI rendering is broken or incomplete. Fix this flow:

- Saved views load and display correctly in the explorer folder
- Each saved view entry shows its renderer type icon, label, and an "unpin" action
- Clicking a saved view opens it as a tab with its configured renderer + query scope
- Users can save any current view configuration (renderer + type filter + query scope + filter text) as a named saved view

### 3. Saved Queries Everywhere

Make saved queries accessible in:
- **Explorer sidebar** — dedicated "Saved Queries" section (or integrate into existing sections)
- **VFS browser** — filter/scope by saved query
- **Spatial canvas** — drag a saved query onto the canvas to create a view widget scoped to it
- **View toolbar** — dropdown to select a saved query as the view's data scope
- **Object browser dropdown** — wherever objects are listed, option to scope by saved query

### 4. SPARQL Console Polish

- **Graph view for results** — when results contain subject-predicate-object patterns (or any triples), offer a graph visualization tab alongside the table
- **Clickable object links in table** — object IRIs in results should be clickable (the enriched IRI pill rendering exists but some IRIs fall through to plain `<span class="sparql-uri">`)
- **Prefix shortening** — `shortenUri()` in `sparql-console.js` doesn't handle `urn:sempkm:model:*` prefixes. Add shortening so `urn:sempkm:model:basic-pkm:Person` renders as `pkm:Person` (or `basic-pkm:Person`). Should dynamically detect installed model prefixes.

### 5. Ontology Viewer & Admin Graph

- **Property description tooltips** — in TBox detail (`tbox_detail.html`), property names in the Properties table should have a hover tooltip showing `rdfs:comment` or `skos:definition` of that property. The current SPARQL query in `ontology/service.py` doesn't fetch property descriptions — needs an additional OPTIONAL clause.
- **Admin model relationship graph** — the Cytoscape.js graph in `model_ontology_diagram.html` should be full-width and full-height within its container, giving ample room for nodes. Currently has `min-height: 600px` but not full viewport height.
- **Edge tooltips** — relationship edges in the model graph should show domain, range, and `rdfs:comment`/description on hover.

### 6. Dashboard & Workflow UX

- **Help text** — dashboard builder and workflow builder forms need contextual help text like the SHACL object forms have.
- **Autocomplete** — any form field that references an object or type should have appropriate autocomplete (type-ahead search against the triplestore).
- **Workflow view step simplification** — the current workflow builder's "view" step type has a "Renderer" dropdown (table/card/graph) that's confusing. The user should pick from provided views and saved views. Each view knows its own renderer. Remove the separate renderer selector.
- **Sample data** — seed data / test fixtures should include sample dashboards and workflows so the UI isn't empty on first install.

## Key Files

| Area | Files |
|------|-------|
| View explorer | `templates/browser/views_explorer.html`, `views_menu.html`, `view_menu_all.html` |
| Carousel (to remove) | `templates/browser/carousel_tab_bar.html`, workspace.js `switchCarouselView()` |
| View templates | `templates/browser/table_view.html`, `cards_view.html`, `graph_view.html` |
| View toolbar | `templates/browser/view_toolbar.html` |
| Generic view routing | workspace.js `openGenericViewTab()`, view service |
| Saved views | `templates/browser/my_views.html`, `workspace.py:my_views()`, `query_service.py:promote_query/list_promoted_views` |
| View registry | `backend/app/views/registry.py` |
| SPARQL console | `frontend/static/js/sparql-console.js` |
| Ontology viewer | `templates/browser/ontology/tbox_detail.html`, `ontology/service.py` |
| Admin model graph | `templates/admin/model_ontology_diagram.html`, `frontend/static/css/style.css` |
| Graph.js | `frontend/static/js/graph.js` |
| Dashboard builder | `templates/browser/dashboard_builder.html`, `dashboard/models.py`, `dashboard/service.py` |
| Workflow builder | `templates/browser/workflow_builder.html` |

## Constraints

- htmx-driven — no SPA framework. Views load as HTML fragments via htmx.
- Cytoscape.js for all graph rendering (already a dependency).
- Saved queries are RDF-backed via `QueryService` (triplestore), not SQLite.
- Promoted views use SQLite (`promoted_query_views` table) via `PromotedQueryView` model.
- Must work with the existing tab system (workspace.js `openTab`, `openGenericViewTab`, special panels).
