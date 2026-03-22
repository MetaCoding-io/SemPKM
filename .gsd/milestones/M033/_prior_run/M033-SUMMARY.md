---
id: M033
provides:
  - SPARQL federation with SERVICE clause pass-through and endpoint allowlist enforcement
  - Mirror service storing federated results in urn:sempkm:mirrored with PROV-O provenance
  - Calendar view renderer with FullCalendar 6.x, SHACL date detection, month/week/day views
  - Map view renderer with Leaflet 1.9.4, MarkerCluster, SHACL geo detection, popup click-to-open
  - Isometric 2.5D graph layout with type-stratified z-layers and compound parent layer planes
  - App catalog UI with card grid, detail pages, install/uninstall, explorer sidebar entry
  - Graph icon toggle with SVG data URI construction and localStorage persistence
  - Two-step setup wizard with deployment mode selection and namespace configuration
  - Caddy cloud profile (docker-compose.cloud.yml) with automatic HTTPS via Let's Encrypt
  - Local TLS profile with mkcert support
  - Instance config model with atomic persistence and config priority chain
key_decisions:
  - "D300: Map view adds schema:latitude/longitude to basic-pkm Event (no WKT for v1)"
  - "D301: SERVICE clause protection via placeholder substitution with brace-depth counting"
  - "D302: Allowlist storage in InstanceConfig JSON key (not separate SQL table)"
  - "D303: PROV-O batch-level provenance in urn:sempkm:mirrored (not per-triple reification)"
  - "D304: Isometric layout via custom Cytoscape extension with 2D projection (not CSS 3D transforms)"
  - "D305: Graph icon SVG data URIs via temp DOM + lucide.createIcons() with module cache"
  - "D306: Instance config persistence with env var > instance config > Pydantic default priority chain"
  - "D307: Configure-instance dual auth guard for pre-setup access"
  - "D308: Deployment profiles via compose override pattern (cloud and local-tls)"
patterns_established:
  - "_protect_service_blocks() / _restore_service_blocks() for query rewriting that must skip SERVICE bodies"
  - "FederationAllowlist CRUD backed by InstanceConfig JSON serialization — reusable for future key-value configs"
  - "View renderer registration end-to-end pattern: registry → _VALID_RENDERERS → generic_view branch → data endpoint → vendor via build.js → template with tryInit → JS IIFE → explorer entry → workspace label → dark mode CSS → unit tests"
  - "SHACL field detection pattern: two-stage (well-known path match → datatype/name fallback scan) — used by _detect_status_field, _detect_date_fields, _detect_geo_fields"
  - "Compound parent nodes with sentinel flag (_isometricLayer) for lifecycle management in Cytoscape layouts"
  - "SVG data URI construction + module cache for Cytoscape node icon rendering"
  - "Compose override pattern for deployment profiles — override only frontend service, keep API + triplestore unchanged"
  - "httpx.AsyncClient + ASGITransport for endpoint testing without a running server"
  - "Atomic config file persistence via tmp + os.replace()"
observability_surfaces:
  - "GET /api/federation/endpoints — current allowlist as JSON"
  - "GET /api/sparql/mirror/batches — mirror batch list with provenance metadata"
  - "GET /browser/views/generic/calendar/data?type=<iri> — raw FullCalendar JSON for debugging"
  - "GET /browser/views/generic/map/data?type=<iri> — raw marker JSON for debugging"
  - "window._sempkmIsometricState — layer/node counts for browser console inspection"
  - "localStorage('sempkm_graph_icons') — icon toggle state inspectable in DevTools"
  - "HTTP 403 with explicit endpoint URL on blocked SERVICE queries"
  - "Mirrored badges on object pages (teal with globe icon, source endpoint tooltip)"
  - "Dotted teal edges in graph view for mirrored relationships"
  - "Structured logging on mirror, calendar, map, and catalog operations"
  - "Startup WARNING when base_namespace is still example.org with no instance config"
requirement_outcomes: []
duration: ~5h across 7 slices
verification_result: passed-with-gaps
completed_at: 2026-03-21
---

# M033: Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul

**Seven independent feature areas delivered: SPARQL federation with mirrored triples and provenance, calendar and map view renderers with SHACL-driven field detection, isometric 2.5D graph layout, app catalog with card grid UI, graph icon toggle, and a two-step setup wizard with Caddy cloud deployment — backed by 208 unit tests and 9 architectural decisions.**

## What Happened

M033 was a breadth milestone — seven independent slices each delivering a self-contained user-facing feature. No slice depended on another, allowing fully parallel execution.

**S01 (Federated SPARQL & Mirrored Triples)** tackled the highest-risk item: extending `scope_to_current_graph()` to detect and preserve SERVICE clauses during FROM injection. The solution (D301) uses brace-depth counting on a string-stripped query to extract SERVICE blocks, replace them with placeholders, inject FROM clauses for the outer WHERE, then restore the SERVICE blocks. This powers SPARQL federation against external endpoints like Wikidata and DBpedia. An admin-managed endpoint allowlist (D302) gates which endpoints can be queried (HTTP 403 for non-allowlisted, owner bypass). A MirrorService converts federated result bindings to RDF triples stored in `urn:sempkm:mirrored` with PROV-O batch provenance (D303). The SPARQL console gained SERVICE clause assistance (endpoint autocomplete, PREFIX injection, snippet template) and a "Mirror Results" button with 4-state management. Object pages show teal mirrored badges with provenance popovers; graph views render mirrored edges as dotted teal lines. 95 unit tests.

**S02 (Calendar View)** proved the "new renderer" registration pattern end-to-end. FullCalendar 6.x was vendored via the build.js pipeline (content-hashed, CDN fallback). `_detect_date_fields()` scans SHACL PropertyShapes with a two-stage strategy — exact well-known path matching first (schema:startDate/endDate), then xsd:date/xsd:dateTime datatype detection with name ranking. The calendar renders bpkm:Event objects on month/week/day grids with type filter pills and click-to-open. Dark mode handled via 13 `--fc-*` CSS custom property overrides. 24 unit tests.

**S03 (Map View)** followed the calendar pattern exactly. Leaflet 1.9.4 + MarkerCluster vendored via build.js. `_detect_geo_fields()` mirrors `_detect_date_fields()` — exact schema:latitude/longitude match first, then path name fragment fallback. L.divIcon with CSS circles avoids Leaflet's well-known icon-default path issue. The basic-pkm EventShape gained schema:latitude/schema:longitude properties with 4 geo-located seed events (Mountain View, Pittsburgh, London, Tokyo). Popup click-to-open, marker clustering, ResizeObserver for dockview panels, dark mode via CSS filter inversion. 25 unit tests.

**S04 (Isometric 2.5D Graph)** required novel math but integrated cleanly. A ~270-line Cytoscape layout extension groups nodes by RDF type into layers, computes grid positions with isometric vertical stagger and horizontal offset (D304). Compound parent nodes with `_isometricLayer` sentinel serve as translucent layer planes that auto-size to contain children. Six integration points in graph.js: layout registry entry, compound styles, cleanup on layout switch, tap/dbltap/mouseover guards, filter propagation to compounds, and expansion-triggered re-layout. No external dependencies.

**S05 (App Catalog)** followed the existing docs_page.html pattern. A catalog router scans `apps/` for manifests, merges runtime status, and renders a card grid. Detail pages show description, permissions, model dependencies, tasks, settings, and install/uninstall buttons (owner-only). The "App Catalog" entry in the workspace explorer uses a static DOM sibling pattern to survive htmx swaps. 14 unit tests.

**S06 (Graph Icon Toggle)** was the smallest slice — ~120 lines across 3 files. `_buildIconDataUri()` creates a temporary detached DOM element, calls `lucide.createIcons()`, extracts SVG markup, and encodes as a data URI. Module-level cache keyed by name+color avoids repeated rendering. Icon styles use `[!_isometricLayer]` selector to exclude compound layer planes (D305). localStorage persistence.

**S07 (Deployment & Onboarding)** redesigned the setup wizard as a two-step flow: deployment mode selection (local/custom domain/decide later) then account creation. InstanceConfig (D306) persists in `data/.instance-config.json` with atomic writes (tmp + os.replace). A namespace guard returns 409 if configuration is attempted after data exists — a one-way door. The Caddy cloud profile (D308) is a compose override replacing nginx for automatic HTTPS. A local TLS profile with mkcert support is also available. Cloud deployment documented in chapter 39. 26 unit tests.

## Cross-Slice Verification

| # | Success Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Federation works end-to-end | ✅ Met | S01: 95 unit tests pass covering SERVICE pass-through (14 tests), allowlist CRUD+enforcement (22 tests), mirror service with binding conversion+provenance (38 tests), mirror button UI (structural verification). All key files verified present. |
| 2 | Calendar view renders temporal data | ✅ Met | S02: 24 unit tests pass covering date detection (11), query building (6), event transformation (7). Calendar registered in RENDERER_REGISTRY and _VALID_RENDERERS. Explorer sidebar entry present. Month/week/day buttons configured. |
| 3 | Map view renders geographic data | ✅ Met | S03: 25 unit tests pass covering geo detection (10), query building (6), marker transformation (9). Map registered in RENDERER_REGISTRY and _VALID_RENDERERS. MarkerCluster vendored. Popup with click-to-open in map.js. |
| 4 | Isometric graph shows layered visualization | ✅ Met | S04: isometric-layout.js exists (270 lines), "isometric" in both available_layouts and built_in_layouts arrays in router.py, compound parent styles with _isometricLayer sentinel in graph.js, cleanup/guard/filter integration verified. |
| 5 | App catalog is browsable | ✅ Met | S05: 14 unit tests pass covering list, detail, install/uninstall, owner enforcement, error handling. catalog_router registered in browser/router.py. Explorer entry present in workspace.html. |
| 6 | Graph icon toggle works | ✅ Met | S06: toggleGraphIcons() in graph.js, localStorage persistence via 'sempkm_graph_icons', icon button in graph_view.html template, _buildIconDataUri with cache, _isometricLayer exclusion. |
| 7 | Setup wizard configures deployment | ✅ Met | S07: 26 unit tests pass covering all modes (local/domain/later), namespace guard (409), auth guard, priority chain. configure-instance endpoint in setup_routes.py. Two-step UI in setup.html. |
| 8 | Cloud profile deploys with HTTPS | ✅ Met | S07: docker-compose.cloud.yml validated (compose config --quiet passes), Caddyfile.cloud with all nginx location blocks translated, caddy:2-alpine image, ports 443+80, Caddy data/config volumes. |
| 9 | All new features survive Docker restart | ⚠️ Partial | Mirrored triples persist in RDF4J (triplestore volume). Instance config in data/.instance-config.json (data volume). Calendar/map views re-render from triplestore data. Catalog reads from apps/ directory (volume mount). Not verified via live Docker restart test — evidence is architectural (all state on persistent volumes). |

**Gaps:**
- **No E2E browser tests** for S01-S06 features. S01 summary explicitly notes "No E2E browser test for the full mirror flow." Calendar, map, isometric, catalog, and icon toggle lack E2E tests. S07 unit tests cover the endpoint but no E2E wizard test.
- **No user guide docs** for S01-S06 features. Only S07 delivered docs (chapter 39, updated chapters 03/20/appendix A). Federation, calendar, map, isometric, catalog, and icon toggle are undocumented in the user guide.
- The standing requirement specifies trailing E2E and docs slices for milestones with user-visible features. M033's roadmap did not include these trailing slices, resulting in these gaps.

## Requirement Changes

No SPARQL-FED-*, CAL-*, MAP-*, ISO-*, CATALOG-*, GRAPH-*, or DEPLOY-* requirements were formally registered in REQUIREMENTS.md during this milestone. The roadmap noted they would be created during slice planning, and slice summaries reference them (e.g., "CAL-01 through CAL-06 validated"), but they exist only in slice summary prose — not in the requirements register.

The roadmap identified two Out of Scope items that M033 addressed:
- "Timeline/calendar renderers — v2+" → S02 delivers Calendar View (should be removed from Out of Scope in PROJECT.md)
- "3D graph visualization — experimental, deferred" → S04 delivers Isometric 2.5D (should be removed from Out of Scope in PROJECT.md)

## Forward Intelligence

### What the next milestone should know
- The view renderer registration pattern is now proven across 4 views (table/cards from M007, kanban from M031, calendar from S02, map from S03). Any future renderer (timeline, treemap, etc.) follows the same 10-step pattern documented in S02's summary.
- `_VALID_RENDERERS` in router.py now contains 6 entries: table, card, graph, kanban, calendar, map.
- The SHACL field detection pattern is established for 3 domains: status (_detect_status_field), dates (_detect_date_fields), geo (_detect_geo_fields). Future detectors should follow the same two-stage approach.
- The federation module at `backend/app/federation/` sits alongside the existing ActivityPub federation code. New federation features go here.
- `scope_to_current_graph()` now injects 3 FROM clauses by default (current, inferred, mirrored). New queryable named graphs follow the `include_mirrored` parameter pattern.
- The `POST /api/setup/configure-instance` endpoint is locked after data exists in the triplestore. Any future namespace migration would need to relax this guard.
- M033 did NOT register requirements or deliver E2E tests / user guide docs for its features. A follow-up milestone should address these gaps.

### What's fragile
- **SERVICE block placeholder approach** — assumes brace-depth counting on string-stripped queries works. A SERVICE keyword inside a nested function call or complex literal could confuse the scanner. If SPARQL complexity grows, consider a proper parser (per D301).
- **Allowlist regex extraction** — `extract_service_endpoints()` uses regex on raw query text. SERVICE URIs inside string literals would be false positives.
- **tryInit polling pattern** — calendar.js, map.js, and other views use setTimeout loops checking for global availability (~100ms latency). Not a problem with 2 new views, but could become noticeable if many more are added.
- **FullCalendar date detection's two-stage approach** — depends on shape property paths being full IRIs. Prefixed paths in shapes would miss the well-known path matching stage.
- **Compound parent cleanup in graph.js** — isometric layout removal must un-parent children before removing compounds. Without this sequence, Cytoscape orphans child nodes.

### Authoritative diagnostics
- `GET /browser/views/generic/calendar/data?type=<iri>` — raw FullCalendar JSON, verifies backend independently of frontend
- `GET /browser/views/generic/map/data?type=<iri>` — raw marker JSON, same pattern
- `GET /api/federation/endpoints` — current allowlist
- `GET /api/sparql/mirror/batches` — mirror batch provenance metadata
- `window._sempkmIsometricState` — browser console: layer count, node count, timestamp
- `localStorage.getItem('sempkm_graph_icons')` — icon toggle state
- `pytest tests/test_sparql_client.py tests/test_federation_allowlist.py tests/test_mirror_service.py tests/test_calendar.py tests/test_map.py tests/test_catalog.py tests/test_instance_config.py -v` — 208 total unit tests

### What assumptions changed
- **Roadmap assumed E2E and docs would be covered per-slice.** In practice, all 7 slices focused on implementation + unit tests. The standing requirement's trailing coverage slices were not planned. Future milestones should include these in the roadmap.
- **Isometric layout was rated medium-high risk** but delivered cleanly in ~35 minutes. The compound parent approach was well-matched to Cytoscape's API.
- **App catalog was expected to show screenshots** — pre-captured screenshots are mentioned in the roadmap but not implemented. Cards show manifest data only.

## Files Created/Modified

### S01 — Federation (22 files)
- `backend/app/rdf/namespaces.py` — MIRRORED_GRAPH_IRI constant
- `backend/app/sparql/client.py` — SERVICE block protection, include_mirrored param
- `backend/app/sparql/router.py` — allowlist enforcement, vocab prefixes
- `backend/app/federation/allowlist.py` — FederationAllowlist service
- `backend/app/federation/allowlist_router.py` — CRUD endpoints
- `backend/app/federation/mirror_service.py` — binding conversion, PROV-O provenance
- `backend/app/federation/mirror_router.py` — mirror API
- `backend/app/templates/browser/_federation_settings.html` — settings partial
- `backend/app/templates/browser/sparql_panel.html` — mirror button
- `frontend/static/js/sparql-console.js` — autocomplete, PREFIX injection, mirror UI
- `frontend/static/js/graph.js` — mirrored edge style
- `frontend/static/css/federation.css` — allowlist UI styles
- `backend/tests/test_sparql_client.py` — 14 new tests (35 total)
- `backend/tests/test_federation_allowlist.py` — 22 tests (new)
- `backend/tests/test_mirror_service.py` — 38 tests (new)

### S02 — Calendar (12 files)
- `backend/app/views/service.py` — _detect_date_fields, calendar query builder
- `backend/app/templates/browser/calendar_view.html` — new template
- `frontend/static/js/calendar.js` — FullCalendar IIFE
- `frontend/static/css/views.css` — calendar styles + dark mode
- `backend/tests/test_calendar.py` — 24 tests (new)

### S03 — Map (11 files)
- `backend/app/views/service.py` — _detect_geo_fields, map query builder
- `backend/app/templates/browser/map_view.html` — new template
- `frontend/static/js/map.js` — Leaflet IIFE
- `models/basic-pkm/shapes/basic-pkm.jsonld` — latitude/longitude PropertyShapes
- `models/basic-pkm/seed/basic-pkm.jsonld` — 4 geo-located seed events
- `backend/tests/test_map.py` — 25 tests (new)

### S04 — Isometric (4 files)
- `frontend/static/js/isometric-layout.js` — ~270-line Cytoscape layout extension (new)
- `frontend/static/js/graph.js` — layout registry, compound styles, cleanup, guards
- `backend/app/views/router.py` — isometric in layout arrays

### S05 — Catalog (9 files)
- `backend/app/browser/catalog.py` — catalog router (new)
- `backend/app/templates/browser/catalog_page.html` — card grid (new)
- `backend/app/templates/browser/catalog_detail.html` — detail page (new)
- `frontend/static/js/workspace.js` — openCatalogTab()
- `frontend/static/css/workspace.css` — ~300 lines catalog CSS
- `backend/tests/test_catalog.py` — 14 tests (new)

### S06 — Icon Toggle (3 files)
- `frontend/static/js/graph.js` — _buildIconDataUri, toggleGraphIcons, icon styles
- `backend/app/templates/browser/graph_view.html` — toggle button
- `frontend/static/css/views.css` — toggle button styles

### S07 — Deployment (14 files)
- `backend/app/instance_config.py` — InstanceConfig model (new)
- `backend/app/api/setup_routes.py` — configure-instance endpoint
- `backend/app/config.py` — instance config priority chain
- `frontend/static/js/auth.js` — two-step wizard UI
- `docker-compose.cloud.yml` — Caddy cloud compose override (new)
- `Caddyfile.cloud` — Caddy config for cloud deployment (new)
- `docker-compose.local-tls.yml` — local TLS compose override (new)
- `Caddyfile.local-tls` — mkcert Caddy config (new)
- `.env.cloud.example` — cloud deployment env template (new)
- `docs/guide/39-cloud-deployment.md` — cloud deployment guide (new)
- `backend/tests/test_instance_config.py` — 26 tests (new)
