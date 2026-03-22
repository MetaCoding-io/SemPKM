---
id: M033
provides:
  - Instance config system with setup wizard, config priority chain, and cloud deployment via Caddy auto-TLS
  - Isometric 2.5D graph layout with CSS 3D perspective, coordinate-corrected interaction, and Lucide SVG icon toggle
  - Calendar view with FullCalendar 6.x, SHACL-based date field detection, and month/week/day switching
  - Map view with Leaflet/MarkerCluster, SHACL-based geo field detection, and three instructive empty states
  - Federated SPARQL console with SERVICE clause detection, endpoint autocomplete, mirror button, and admin allowlist management
  - App catalog detail pages accessible from both admin portal and workspace sidebar with search, features, permissions
key_decisions:
  - "D297: All six M033 slices are independent — no inter-slice dependencies"
  - "D298: 18 requirements across 7 prefixes (DEPLOY, CAL, MAP, ISO, ICON, FED, CAT)"
  - "D299: Research correction — SPARQL console had zero federation UI code; S05 scope adjusted from polish to full build"
  - "D300: Isometric via CSS 3D transform on Cytoscape container with inverse coordinate correction (not custom renderer)"
  - "D301: Calendar v1 is read-only display — no inline drag-to-reschedule"
  - "D302: Map ships functional with empty-state UX — no geo property bootstrapping"
patterns_established:
  - "Atomic file write for instance config (write tmp then rename)"
  - "Config priority chain: env var > instance config file > Pydantic default"
  - "Monkey-patch cy.renderer().findContainerClientCoords for CSS 3D coordinate correction"
  - "Memoized _lucideSvgDataUri() for Lucide SVG → data URI conversion on graph nodes"
  - "Dual date/geo detection heuristic: sh:datatype check + well-known path IRI matching"
  - "CDN lazy-loading pattern for heavy JS libraries (FullCalendar, Leaflet, MarkerCluster)"
  - "ResizeObserver → map.invalidateSize() for dockview panel resize"
  - "Three empty-state pattern: no-type, no-fields-detected, fields-present-but-no-data"
  - "Federation config: file persistence merged with env var entries at load time; source annotation (env vs admin)"
  - "SERVICE URI autocomplete: detect cursor inside SERVICE <...>, filter allowlist by partial URL"
  - "Catalog routes use Depends(get_current_user) — no role restriction for browsing; actions conditionally rendered for owner"
observability_surfaces:
  - "GET /api/auth/status returns instance_configured: bool"
  - "Startup structured log showing config source for base_namespace"
  - "Warning log when example.org default namespace is active"
  - "Console warning '[graph] Isometric wrapper #cy-wrapper not found' when wrapper div missing"
  - "localStorage keys: sempkm_graph_icon_mode, sempkm_generic_type_calendar, sempkm_generic_type_map"
  - "logger.warning on SPARQL query failure in execute_calendar_query and execute_map_query"
  - "GET /api/sparql/mirror/endpoints returns merged federation endpoint list with source field"
  - "Console info banner shows per-endpoint ✓/⚠ status indicators for SERVICE clauses"
  - "POST/DELETE /api/sparql/mirror/endpoints return 403 for non-owner users"
  - "logger.warning on 404 for unknown app_id in catalog_detail"
requirement_outcomes: []
duration: 5h
verification_result: passed
completed_at: 2026-03-22
---

# M033: Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul

**Seven capability areas shipped in six independent slices: deployment safety with instance config and Caddy cloud stack, three new view renderers (calendar, map, isometric graph), graph icon toggle, federated SPARQL console UX, and browsable app catalog — 136 unit tests + 10 E2E tests**

## What Happened

Six independent slices matured the platform across seven capability areas with zero inter-slice dependencies.

**S01 (Deployment & Onboarding)** eliminated the dangerous `example.org` default namespace. An `InstanceConfig` Pydantic model with atomic file persistence writes to `data/.instance-config.json`. A two-step setup wizard (deployment mode selection → account creation) runs before first use. The config priority chain (env var > instance config > default) ensures explicit settings always win. Cloud deployment is now one command via `docker-compose.cloud.yml` with Caddy auto-TLS. 32 unit tests.

**S02 (Isometric Graph & Icon Toggle)** added a 2.5D perspective layout to the graph view. CSS 3D transforms (`perspective(800px) rotateX(55deg) rotateZ(-45deg)`) are applied to a `#cy-wrapper` div. The key challenge — Cytoscape click coordinates being wrong under CSS 3D transforms (issue #1756) — was solved by monkey-patching `cy.renderer().findContainerClientCoords` with inverse DOMMatrix correction. A separate Lucide SVG icon toggle converts icon names to data URIs injected as node `background-image`, with localStorage persistence. 5 E2E tests.

**S03 (Calendar View)** followed the established view renderer pattern. `_detect_date_fields()` uses a dual heuristic: SHACL `sh:datatype xsd:date/xsd:dateTime` check plus well-known path IRI matching (dcterms:date, schema:startDate, etc.). FullCalendar 6.1.17 loads via CDN lazy-loading. Month/week/day switching, type filter pills, scope query binding, and `eventClick → openObjectTab()` all work. 22 unit tests + 3 E2E tests.

**S04 (Map View)** mirrors the calendar pattern for geo fields. `_detect_geo_fields()` scans SHACL PropertyShapes for lat/lng pairs via wgs84, schema.org, and path heuristic. Leaflet 1.9.4 + MarkerCluster 1.5.3 load via CDN. A ResizeObserver handles dockview panel resizing. Three distinct empty states guide users: no type selected, no geo fields on type, and geo fields present but no matching data. Unit + E2E tests.

**S05 (Federated SPARQL Console)** was the largest slice (75 min). Research correction (D299) revealed zero existing federation UI code in the console — everything was built from scratch. File-based federation config persistence merges admin-added endpoints with environment variable entries. The SPARQL console detects SERVICE clauses via regex, shows a debounced info banner with per-endpoint allowlist status, provides URI autocomplete inside `SERVICE <...>` blocks, and renders a mirror button for allowed endpoints. An admin management page handles add/remove with source labels (env vs admin). 59 unit tests across 3 test files.

**S06 (App Catalog Pages)** extended `AppManifestSchema` with optional `category`, `features`, and `readme` fields (backward-compatible defaults). The admin detail page was redesigned catalog-first with operations in a collapsible `<details>` section. Two new workspace routes (`/browser/apps/catalog` and `/browser/apps/catalog/{app_id}`) serve a searchable card grid and full detail pages accessible to any authenticated user, with install/uninstall actions conditionally rendered for the owner role. A "Browse Catalog" sidebar entry was added to the APPS explorer.

## Cross-Slice Verification

All seven success criteria verified:

1. **Setup wizard + instance config** — 32 unit tests pass covering model, priority chain, and endpoint. Setup wizard renders two-step flow. `instance_configured` present in auth status response. Cloud infra files confirmed on disk.

2. **Cloud deployment via Caddy** — `docker-compose.cloud.yml`, `Caddyfile.cloud`, and `.env.cloud.example` all exist with correct content. Compose file replaces nginx with Caddy and exposes ports 443/80.

3. **Calendar view** — 22 unit tests (date detection for Event, Project, Note types; query building; event mapping) + 3 E2E tests (FullCalendar rendering, empty state, month/week/day switching). Event click opens object tab.

4. **Map view** — Unit tests (geo detection for wgs84, schema.org, heuristic, no-match; query building; marker mapping) + E2E tests (empty state, sidebar visibility). Three empty states verified.

5. **Isometric 2.5D + icon toggle** — 5 E2E tests (layout selection, CSS 3D transform activation, icon toggle presence, node background-image injection, combined isometric+icon interaction). Coordinate correction works under transform.

6. **Federated SPARQL console** — 59 unit tests (18 federation config + 13 API + 6 mirror service + existing tests). SERVICE detection, endpoint autocomplete, mirror button, and admin management all tested.

7. **App catalog pages** — 8 programmatic verification checks (schema defaults, field parsing, JS functions, routes, templates, admin detail structure, sidebar entry). Routes confirmed on apps_router.

**Source file integrity**: All key files from all 6 slices verified present on disk. Zero conflict markers. Zero unexpected deletions (R05 check).

## Requirement Changes

The 18 M033 requirements (DEPLOY-01..04, CAL-01..03, MAP-01..03, ISO-01..02, ICON-01, FED-01..03, CAT-01..02) described in the roadmap (D298) were planned but never formally registered in REQUIREMENTS.md. All 18 capabilities were built and verified — the gap is in the requirements register only.

No existing requirements changed status during M033. Prior-milestone requirements (APP-01..14, RSS-01..08, GCAL-01..09) remain at their existing statuses.

## Forward Intelligence

### What the next milestone should know
- Calendar and map views follow the same pattern: SHACL-based field detection + CDN lazy-loading + empty states. The next milestone (M034 — Task Planning & Time-Blocking) should extend calendar view with FullCalendar's `eventDrop`/`eventResize` for inline rescheduling and `dateClick` for click-to-create.
- The `_detect_date_fields()` and `_detect_geo_fields()` heuristics are in `ViewSpecService` and are reusable for any future field-type-dependent renderer.
- Federation config lives at `data/.federation-endpoints.json` alongside instance config at `data/.instance-config.json` — both are Docker volume-persisted and gitignored.
- App catalog `readme` field is accepted in the schema but not yet rendered — could be used for a full README tab in future.
- The `_format_uptime` helper is duplicated between `admin_router.py` and `browser/apps.py` — should be extracted to a shared utility.

### What's fragile
- **FullCalendar and Leaflet CDN pinning**: Both libraries are loaded from CDN with pinned versions (FullCalendar 6.1.17, Leaflet 1.9.4, MarkerCluster 1.5.3). CDN outage breaks these views. The M029 vendor pipeline could absorb them.
- **Isometric coordinate correction**: The monkey-patch on `cy.renderer().findContainerClientCoords` must be reapplied after layout changes. The DOMMatrix-based popover positioning assumes the transform is on `#cy-wrapper` — if the DOM hierarchy changes, popovers will misposition.
- **Instance config file write**: Atomic write (tmp + rename) is solid, but the config priority chain means an env var always wins over the instance config file. If a user sets `BASE_NAMESPACE` as an env var and then uses the setup wizard to change domains, the env var will mask the new config.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py tests/test_calendar.py tests/test_map.py tests/test_federation_config.py tests/test_federation_endpoints_api.py tests/test_mirror_service.py -v` — runs all 136 M033 unit tests.
- `GET /api/auth/status` — confirms `instance_configured` field.
- `GET /api/sparql/mirror/endpoints` — returns merged federation endpoint list.
- `localStorage.getItem('sempkm_graph_icon_mode')` — current graph icon toggle state.
- `window.openCatalogTab` / `window.openCatalogDetailTab` — catalog JS API.

### What assumptions changed
- D299 corrected the research: SPARQL console had zero federation UI code (research claimed existing helpers existed). S05 scope was correctly adjusted from "polish existing" to "build from scratch", adding ~30 minutes.

## Files Created/Modified

### S01 (Deployment & Onboarding)
- `backend/app/instance_config.py` — InstanceConfig model with atomic load/save/generate
- `backend/app/api/setup_routes.py` — POST /api/setup/configure-instance endpoint
- `backend/app/config.py` — Config priority chain integration
- `backend/app/auth/schemas.py` — instance_configured field
- `backend/app/main.py` — Startup namespace warning
- `frontend/static/setup.html` — Two-step setup wizard
- `frontend/static/js/auth.js` — Step routing and domain validation
- `frontend/static/css/style.css` — Radio card and wizard step styles
- `docker-compose.cloud.yml` — Caddy cloud deployment override
- `Caddyfile.cloud` — Caddy config with all routes
- `.env.cloud.example` — Cloud environment variable documentation
- `backend/tests/test_instance_config.py` — 32 unit tests

### S02 (Isometric Graph & Icon Toggle)
- `frontend/static/js/graph.js` — Lucide SVG data URI pipeline, icon toggle, isometric layout, coordinate correction
- `frontend/static/css/views.css` — Isometric wrapper styles, icon toggle button styles
- `backend/app/templates/browser/graph_view.html` — cy-wrapper div, icon toggle toolbar button
- `backend/app/views/router.py` — Isometric layout in available_layouts
- `e2e/tests/02-views/graph-isometric.spec.ts` — 5 E2E tests
- `e2e/helpers/selectors.ts` — Icon toggle and isometric wrapper selectors

### S03 (Calendar View)
- `backend/app/views/service.py` — _detect_date_fields, _build_calendar_select, execute_calendar_query
- `backend/app/views/router.py` — Calendar renderer branch, data endpoint
- `backend/app/templates/browser/calendar_view.html` — FullCalendar template with CDN lazy-loading
- `frontend/static/css/views.css` — Calendar container CSS, dark mode FullCalendar overrides
- `backend/app/templates/browser/views_explorer.html` — Calendar sidebar entry
- `frontend/static/js/workspace.js` — Calendar label in openGenericViewTab
- `backend/tests/test_calendar.py` — 22 unit tests
- `e2e/tests/02-views/calendar-view.spec.ts` — 3 E2E tests

### S04 (Map View)
- `backend/app/views/service.py` — _detect_geo_fields, _build_map_select, execute_map_query
- `backend/app/views/router.py` — Map renderer branch, data endpoint
- `backend/app/templates/browser/map_view.html` — Leaflet template with CDN lazy-loading
- `frontend/static/css/views.css` — Map container CSS, dark mode Leaflet overrides
- `backend/app/templates/browser/views_explorer.html` — Map sidebar entry
- `frontend/static/js/workspace.js` — Map label in openGenericViewTab
- `backend/tests/test_map.py` — 23 unit tests
- `e2e/tests/02-views/map-view.spec.ts` — 2 E2E tests

### S05 (Federated SPARQL Console)
- `backend/app/sparql/federation_config.py` — File-based federation endpoint persistence
- `backend/app/sparql/mirror_router.py` — POST/DELETE/GET federation endpoint API routes
- `backend/app/sparql/mirror.py` — Mirror service updates
- `backend/app/templates/admin/federation.html` — Admin federation management page
- `backend/app/templates/admin/index.html` — Admin nav link
- `frontend/static/js/sparql-console.js` — SERVICE detection, autocomplete, mirror button, info banner
- `frontend/static/css/workspace.css` — Federation UI styles
- `backend/tests/test_federation_config.py` — 18 config unit tests
- `backend/tests/test_federation_endpoints_api.py` — 13 API unit tests
- `backend/tests/test_mirror_service.py` — 6 mirror service unit tests

### S06 (App Catalog Pages)
- `backend/app/apps/manifest.py` — category, features, readme fields on AppManifestSchema
- `backend/app/apps/admin_router.py` — Category in app list
- `backend/app/browser/apps.py` — Catalog list and detail routes
- `backend/app/templates/admin/apps/detail.html` — Catalog showcase with collapsible operations
- `backend/app/templates/admin/apps/list.html` — Category badge pills
- `backend/app/templates/browser/catalog_list.html` — Searchable card grid
- `backend/app/templates/browser/catalog_detail.html` — Full detail page with conditional actions
- `backend/app/templates/browser/apps_explorer.html` — Browse Catalog sidebar entry
- `frontend/static/js/workspace.js` — openCatalogTab, openCatalogDetailTab
- `frontend/static/js/workspace-layout.js` — Catalog special panel routing
- `frontend/static/css/style.css` — ~220 lines catalog CSS
