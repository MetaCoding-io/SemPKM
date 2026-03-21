# M033: Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul

**Gathered:** 2026-03-21
**Status:** Ready for planning

## Project Description

A mega-milestone spanning 7 feature areas that deepen SemPKM's semantic capabilities, add 3 new data visualization renderers, create a rich app browsing experience, and implement the deployment/onboarding redesign. This is the most cross-cutting milestone since M005 — touching the triplestore layer, view system, graph visualization, app platform, and deployment infrastructure.

## Why This Milestone

**Federated SPARQL** is the natural next step for a linked data platform. Users have structured knowledge (People, Projects, Notes) but no way to enrich it from the broader Linked Open Data cloud. A user with a Person object should be able to pull in Wikidata facts about that person. A music collection should be enrichable from MusicBrainz. The existing inference engine (inferred triples from OWL reasoning) establishes the pattern — "mirrored triples" extend it to external sources.

**Calendar and Map views** are the two most commonly requested visualization modes after table/cards/graph. The bpkm:Event type (shipped in M018's basic-pkm v2.1) has temporal data that currently renders only in table/card views. The spatial canvas handles free-form layout but not temporal or geographic arrangement. These are new renderer types in the existing view system.

**Isometric 2.5D graph** adds a depth dimension to the existing Cytoscape.js graph view. Configurable z-layers let users see provenance (which source contributed this triple?), type hierarchy, or temporal stratification as visual depth. This builds directly on the graph view's semantic styling and layout registry.

**App catalog pages** make the 11 installed apps discoverable and understandable. Currently apps are listed in a minimal admin table. Users can't see what an app does before installing it, can't browse screenshots, and have no tutorial content. E2E test screenshots captured by the existing `capture.spec.ts` infrastructure can populate these pages automatically.

**Graph icon toggle** is a small but impactful UX improvement. The graph view already maps type icons to node shapes (iconToShape in graph.js), but users can't toggle between the abstract shapes and actual Lucide icons rendered on nodes. This adds a toolbar button.

**Deployment overhaul** implements the 3 proposals from DEPLOYMENT-AND-ONBOARDING-DESIGN.md: setup wizard domain configuration step (solving the dangerous default BASE_NAMESPACE), Caddy cloud profile (docker-compose.cloud.yml), and local mkcert TLS. This was researched and approved — now it needs building.

## User-Visible Outcome

### When this milestone is complete, the user can:

**Federated SPARQL:**
- Write SPARQL queries with SERVICE clauses targeting Wikidata, MusicBrainz, DBpedia, or any public SPARQL endpoint
- See results from external endpoints alongside local data in the SPARQL console
- Choose to "mirror" federated results as cached triples in `urn:sempkm:mirrored` — visible in views and object pages like inferred triples but with provenance marking their external source
- Configure which external endpoints are allowed in Settings

**Isometric 2.5D Graph:**
- Switch any graph view to "Isometric" layout via the layout picker
- See nodes arranged on configurable z-layers based on a chosen dimension (provenance source, RDF type, creation date, model)
- Each layer is a translucent horizontal plane with edges connecting across layers
- Rotate/tilt the view to inspect layer relationships

**Calendar View:**
- Open a "Calendar View" from the VIEWS explorer alongside Table/Cards/Graph
- See objects with temporal properties (dcterms:created, bpkm:startDate, bpkm:dueDate, bpkm:eventStart) rendered on a FullCalendar month/week/day grid
- Click events to open the object tab
- Type filter pills narrow by type (same pattern as generic table/cards/graph views)
- Configurable date property selection per view

**Map View:**
- Open a "Map View" from the VIEWS explorer
- See objects with geographic properties (schema:latitude/longitude, schema:geo, or any WKT literal) as markers on a Leaflet/OpenStreetMap map
- Click markers to see object popups with label/type/properties
- Marker clustering for dense data
- Type filter pills

**App Catalog Pages:**
- Browse a new "App Catalog" section in the workspace explorer
- Each app has a detail page with: description, version, author, screenshots carousel, feature list, permissions summary, model dependencies, tutorial/guide links
- E2E test screenshots auto-populate the carousel for bundled apps
- Install/uninstall buttons directly from the catalog page
- Works for both installed and available-but-not-installed apps

**Graph Icon Toggle:**
- Click a toolbar button on any graph view to toggle between shape-only and icon-on-node display
- Icons render as Lucide SVG overlays on nodes, replacing the abstract ellipse/diamond/rectangle shapes
- Toggle state persists per view (localStorage)

**Deployment & Onboarding:**
- New setup wizard step asks deployment mode (local/domain/later) before account creation
- BASE_NAMESPACE auto-configured to `urn:sempkm:{uuid}/` (local) or `https://{domain}/data/` (domain)
- `docker-compose.cloud.yml` profile adds Caddy for automatic HTTPS with Let's Encrypt
- `mkcert` integration for local TLS development
- Instance config persisted in `data/.instance-config.json`

### Entry point / environment

- Entry point: `http://localhost:3000/browser/` (workspace), `http://localhost:3000/admin/` (admin), setup wizard
- Environment: Docker Compose (api + triplestore + frontend/nginx + optional Caddy)
- Live dependencies: RDF4J triplestore, external SPARQL endpoints (Wikidata, MusicBrainz), FullCalendar, Leaflet

## Completion Class

- Contract complete means: federated queries return data from external endpoints and mirror it locally; all 3 new renderers display data correctly; app catalog pages render with screenshots; graph toggle works; deployment wizard configures namespace correctly
- Integration complete means: mirrored triples appear in views and object pages; calendar shows real bpkm:Event objects; map shows objects with geo coordinates; app catalog shows real E2E screenshots; setup wizard flows end-to-end in Docker
- Operational complete means: Caddy cloud profile works with real domain/TLS; mirrored triples persist across restart; all new features work after Docker restart

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User writes a SERVICE query against Wikidata in the SPARQL console, results display, user clicks "Mirror" and the triples appear in `urn:sempkm:mirrored` queryable alongside local data
- Isometric graph view shows nodes on 3+ layers stratified by type, with edges crossing between layers
- Calendar view shows bpkm:Event objects on a FullCalendar grid, clicking opens the object
- Map view shows objects with geo coordinates as Leaflet markers, popups display object info
- App catalog page for RSS Reader shows description, screenshots carousel with real captures, install button
- Graph view toolbar toggle switches between shapes and Lucide icons on nodes
- Fresh Docker instance setup wizard asks deployment mode, configures BASE_NAMESPACE correctly for "local" and "domain" paths
- `docker-compose.cloud.yml` starts Caddy + nginx + API + triplestore and serves over HTTPS

## Risks and Unknowns

### High Risk
- **RDF4J SERVICE clause support** — RDF4J supports SPARQL 1.1 federation natively, but the SemPKM `scope_to_current_graph()` function rewrites queries by injecting FROM clauses. SERVICE clauses may be mangled or blocked by the scoping logic. Need to handle SERVICE clauses specially (pass through without scoping, or scope only the non-SERVICE parts).
- **Mirrored triples provenance** — Need a way to mark which external endpoint provided which triples. A triple `(wd:Q42, rdfs:label, "Douglas Adams")` needs to carry provenance like `(wd:Q42, rdfs:label, "Douglas Adams") prov:wasAttributedTo <https://query.wikidata.org/sparql>`. This may require reification or a side-table approach.

### Medium Risk
- **FullCalendar bundle size** — FullCalendar is ~90KB gzipped. Needs lazy loading like Chart.js (D065, D272) to avoid bloating every page. Calendar renderer activates only when calendar view is opened.
- **Leaflet tile loading in Docker** — Leaflet needs to fetch OpenStreetMap tiles from the internet. Self-hosted instances behind strict firewalls won't see map tiles. Need a graceful degradation (show markers on blank background with a "tiles unavailable" message).
- **Isometric CSS transform math** — 2.5D projection via CSS transforms (rotateX, perspective, translateZ) needs careful math to keep node labels readable and edge routing correct. May need to render labels in a separate non-transformed layer.

### Low Risk
- **App catalog screenshot capture** — The existing `capture.spec.ts` infrastructure already captures screenshots for the marketing site. Extending it to capture per-app screenshots is straightforward.
- **Graph icon toggle** — Small, self-contained change to graph.js. The icon data is already available via `window._sempkmIcons`.

## Existing Codebase / Prior Art

### Federated SPARQL
- `backend/app/sparql/client.py` — `scope_to_current_graph()` rewrites queries with FROM clauses. Must be extended to handle SERVICE.
- `backend/app/sparql/router.py` — SPARQL API endpoints. Federated queries flow through here.
- `backend/app/triplestore/client.py` — TriplestoreClient wraps RDF4J HTTP API. RDF4J handles SERVICE natively.
- `backend/app/inference/service.py` — InferenceService pattern for urn:sempkm:inferred. Mirror service follows same pattern for urn:sempkm:mirrored.
- `backend/app/rdf/namespaces.py` — `INFERRED_GRAPH_IRI = URIRef("urn:sempkm:inferred")`. Add `MIRRORED_GRAPH_IRI`.

### View Renderers
- `backend/app/views/service.py` — ViewSpecService with `execute_graph_query()`, `register_generic_views()`. Calendar and map are new generic views.
- `backend/app/views/router.py` — View rendering endpoints. Calendar/map need new renderer endpoints.
- `frontend/static/js/graph.js` — Cytoscape.js graph with layout registry, semantic styling. Isometric is a new layout.
- `backend/app/templates/browser/graph_view.html` — Graph template with layout picker, filter. Reference for calendar/map templates.
- `backend/app/templates/browser/view_toolbar.html` — Shared toolbar with filter and renderer-specific controls.

### App Catalog
- `backend/app/apps/manifest.py` — AppManifestSchema with pages, permissions, dependencies. Source for catalog data.
- `backend/app/apps/manager.py` — AppManager for install/uninstall lifecycle.
- `backend/app/browser/apps.py` — Browser sub-router for app explorer.
- `backend/app/templates/browser/apps_explorer.html` — Current minimal app list.
- `e2e/tests/screenshots/capture.spec.ts` — Existing screenshot capture infrastructure.
- `apps/*/manifest.yaml` — 11 app manifests with descriptions, permissions, dependencies.

### Deployment
- `.gsd/design/DEPLOYMENT-AND-ONBOARDING-DESIGN.md` — Approved design doc with 3 proposals.
- `frontend/static/setup.html` — Current setup wizard (token + email only).
- `backend/app/auth/router.py` — `POST /api/auth/setup` endpoint.
- `docker-compose.yml` — Current 3-service stack.
- `docker-compose.demo.yml` — Demo stack reference (uses Caddy from M025).

### Graph Icons
- `frontend/static/js/graph.js` — `iconToShape` mapping, `window._sempkmIcons.graph` data.
- `backend/app/services/icons.py` — IconService providing per-type Lucide icon names and colors.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- New requirements to be created for all 7 feature areas (FED-*, CAL-*, MAP-*, ISO-*, CATALOG-*, DEPLOY-*)
- Existing out-of-scope items that this advances: "Timeline/calendar renderers — v2+" and "3D graph visualization — experimental, deferred"

## Scope

### In Scope

**Federated SPARQL & Mirrored Triples:**
- SPARQL 1.1 SERVICE clause pass-through to RDF4J (bypass scope_to_current_graph for SERVICE blocks)
- Backend federation proxy service for managed endpoints (Wikidata, MusicBrainz, DBpedia)
- Configurable endpoint allowlist in Settings (admin only)
- "Mirror" action on federated query results → stores triples in `urn:sempkm:mirrored` named graph
- Mirrored triples queryable alongside current and inferred graphs (scope_to_current_graph extended)
- Provenance tracking: which endpoint contributed which mirrored triples
- SPARQL console UI for SERVICE clause assistance (endpoint autocomplete, PREFIX injection)
- Mirrored triple indicators in views (like inferred edge dashed lines)

**Isometric 2.5D Graph View:**
- New "Isometric" layout option in layout picker (registered via registerLayout)
- CSS 3D transforms (perspective, rotateX) on graph container
- Configurable z-layer dimension selector: provenance (urn:sempkm:current vs inferred vs mirrored), rdf:type, dcterms:created (year/month), source model
- Translucent horizontal layer planes rendered as positioned divs
- Cross-layer edge rendering
- Label readability in projected view (counter-rotate or billboard labels)

**Calendar View Renderer:**
- FullCalendar 6.x vendored locally (lazy-loaded, not in global vendor bundle per D272 pattern)
- New "Calendar" generic view registered at startup alongside Table/Cards/Graph
- SPARQL query builder for temporal data (FILTER on date properties, configurable which property drives the calendar)
- Month/week/day views with event rendering
- Click-to-open object tab
- Type filter pills (reuse existing pattern from generic views)
- Dark mode theme integration via CSS variables

**Map View Renderer:**
- Leaflet.js 1.9.x vendored locally (lazy-loaded)
- New "Map" generic view registered at startup
- SPARQL query for geographic data (schema:latitude/longitude, schema:geo, WKT literals)
- OpenStreetMap tile layer (default, no API key)
- Marker clustering (Leaflet.markercluster plugin)
- Popup on marker click with object label, type icon, key properties
- Click-through to open object tab from popup
- Graceful degradation when tiles unavailable
- Type filter pills

**App Catalog Pages:**
- New `GET /browser/app-catalog` workspace section and explorer entry
- App catalog list page showing all apps (installed + available from apps/ directory)
- App detail page with: name, version, author, description (from manifest), feature list, permissions display, model dependency list, install/uninstall action
- Screenshots carousel on detail page
- E2E screenshot capture spec extended to produce per-app screenshots
- Tutorial/guide links (to relevant user guide chapters)
- Works as dockview special-panel tab in workspace

**Graph View Icon Toggle:**
- Toolbar button on graph views to toggle icon display mode
- "Shapes" mode (current behavior): nodes rendered as ellipse/diamond/rectangle per iconToShape
- "Icons" mode: Lucide SVG icons rendered as node background-image or overlay
- Toggle state persisted per view in localStorage
- Works on both model-declared and generic graph views

**Deployment & Onboarding:**
- Setup wizard Step 1: deployment mode (local / custom domain / later)
- `POST /api/setup/configure-instance` endpoint writing `data/.instance-config.json`
- BASE_NAMESPACE auto-configuration: `urn:sempkm:{uuid}/` for local, `https://{domain}/data/` for domain
- Guard rail: refuse namespace change if user data exists in triplestore
- `docker-compose.cloud.yml` adding Caddy service for automatic HTTPS
- Caddyfile template with domain placeholder
- mkcert integration for local development TLS
- `data/.instance-config.json` loaded by config.py with priority: env var > instance config > defaults
- Updated user guide Chapter 20 (production deployment) and Chapter 3 (installation)

### Out of Scope / Non-Goals

- Full 3D WebGL graph (Three.js / force-graph-3d) — deferred
- Federated SPARQL UPDATE (read-only federation)
- Real-time calendar sync with external calendars (that's what the sync apps do)
- Map tile server bundling (users provide their own if offline needed)
- Drag-and-drop event creation on calendar
- App marketplace with external registry/download
- Kubernetes deployment profiles
- mTLS between services
- Mobile-specific calendar/map layouts

## Technical Constraints

- Frontend: htmx + vanilla JS (no React). FullCalendar and Leaflet used as standalone libraries.
- FullCalendar and Leaflet must be lazy-loaded (not in global vendor bundle) — same pattern as Yasgui and Chart.js (D272)
- Federated queries must respect the existing graph scoping security model — SERVICE clauses should not bypass the scope_to_current_graph protection for non-SERVICE parts of the query
- Mirrored triples must be distinguishable from user-created and inferred triples
- The Caddy cloud profile must not break the existing local dev docker-compose.yml
- The setup wizard changes must be backward-compatible — existing instances that already have data should not be forced through the deployment step

## Integration Points

- **RDF4J** — Native SPARQL 1.1 federation via SERVICE clauses; mirrored graph as new named graph
- **ViewSpecService** — 2 new generic views (Calendar, Map) registered at startup alongside Table/Cards/Graph
- **Layout Registry** — Isometric layout registered via registerLayout() in graph.js
- **IconService** — Graph icon toggle reads from window._sempkmIcons
- **AppManager** — Catalog pages read manifest data; install/uninstall actions
- **Screenshot infrastructure** — e2e/tests/screenshots/ extended for per-app captures
- **Docker Compose** — New cloud profile; Caddy service from M025 demo pattern
- **Settings** — Federation endpoint allowlist; calendar/map property configuration
- **Workspace explorer** — New "App Catalog" section; Calendar/Map entries in VIEWS
- **SPARQL console** — SERVICE clause awareness; endpoint autocomplete
- **scope_to_current_graph** — Extended to include FROM <urn:sempkm:mirrored>; SERVICE clause pass-through

## Open Questions

- **Mirror granularity** — Mirror entire federated query results, or let users select specific triples to mirror? Entire result is simpler for v1.
- **Mirror staleness** — Should mirrored triples have a TTL? Wikidata labels don't change often, but some data does. TTL adds complexity. Start without TTL, add later if needed.
- **Calendar date property discovery** — Auto-detect which properties are dates (xsd:date, xsd:dateTime) from SHACL shapes, or require manual configuration per view? Auto-detect from shapes is better UX.
- **Map coordinate format** — Support only schema:latitude/longitude (two separate properties), or also WKT Point literals and GeoJSON? Start with schema:lat/long, add WKT later.
- **Isometric layer rendering** — CSS transforms on the Cytoscape container, or render a separate SVG/Canvas layer under Cytoscape? CSS transforms are simpler but may interact badly with Cytoscape's internal coordinate system.
- **App catalog screenshots** — Capture at install time (dynamic) or pre-capture and bundle with app source (static)? Pre-captured and bundled is simpler and doesn't require a running stack at install time.
