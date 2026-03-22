# M033: Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul

**Vision:** Seven capability areas that mature the platform: safe deployment with proper namespace configuration, three new view renderers (calendar, map, isometric graph), enhanced graph icons, federated SPARQL console UX, and browsable app catalog pages.

## Success Criteria

- Setup wizard guides new users through deployment mode selection before account creation, writing a persistent instance config that eliminates the `example.org` default
- Cloud deployment works via `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up` with automatic TLS from Caddy
- Calendar view renders objects with date properties on a FullCalendar month/week/day grid, clicking an event opens the object tab
- Map view renders objects with geo coordinates as clustered Leaflet markers; shows an instructive empty state when no geo data exists
- Graph view has a working isometric 2.5D layout option with CSS 3D transforms and correct click interaction, plus a toggle between shape-only and Lucide SVG icon-on-node display
- SPARQL console detects SERVICE clauses, validates endpoints against the allowlist, shows a mirror button for allowed endpoints, and provides endpoint URL autocomplete
- App catalog detail pages show description, features, and permissions in a browsable layout accessible from both admin and workspace

## Key Risks / Unknowns

- CSS 3D transform on Cytoscape container causes event coordinate mismatch — clicks land on wrong nodes. Known Cytoscape issue #1756. Inverse matrix correction may be fragile across browsers.
- Map view ships empty for all current Mental Models — no types currently define geo coordinates. Usability depends on future model extensions or user-added properties.
- Deployment overhaul touches config loading priority chain, setup wizard auth flow, and Docker Compose profiles — cross-cutting changes that could regress existing setup flow if not carefully sequenced.

## Proof Strategy

- CSS 3D + Cytoscape coordinate mismatch → retire in S02 by building the real isometric layout with inverse transform correction and verifying that node clicks, drags, and popovers work correctly after rotation
- Map view empty state → retire in S04 by shipping a complete renderer with instructive empty-state UX and verifying it renders markers when test data with `wgs84:lat`/`wgs84:long` is provided via SPARQL
- Deployment config priority → retire in S01 by building the instance config loader with explicit precedence tests (env var > instance config > default) and verifying the setup wizard end-to-end in the browser

## Verification Classes

- Contract verification: pytest unit tests for instance config, date/geo field detection, mirror service, manifest schema; Playwright E2E for setup wizard flow, calendar/map/isometric view rendering
- Integration verification: Docker Compose cloud profile with Caddy serving TLS; FullCalendar rendering real Event data from SPARQL; Cytoscape 3D transform with live graph interaction
- Operational verification: instance config persistence across container rebuilds (Docker volume); Caddy auto-TLS certificate acquisition
- UAT / human verification: isometric graph visual quality and interaction feel; calendar usability; catalog page design quality

## Milestone Definition of Done

This milestone is complete only when all are true:

- All six slices pass their verification criteria
- Setup wizard correctly writes instance config and the API respects the config priority chain
- Cloud deployment profile starts and serves over HTTPS with valid certificates
- Calendar view renders bpkm:Event objects with correct date positioning across month/week/day views
- Map view renders test markers and shows a clear empty state when no geo data exists
- Isometric 2.5D graph layout is selectable, renders with CSS 3D perspective, and node interactions (click, popover) work correctly
- Graph icon toggle switches between shape-only and SVG icon display
- SPARQL console provides SERVICE endpoint assistance and mirror functionality
- App catalog detail pages are accessible from both admin and workspace

## Requirement Coverage

New requirements introduced by M033:

- Covers: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, CAL-01, CAL-02, CAL-03, MAP-01, MAP-02, MAP-03, ISO-01, ISO-02, ICON-01, FED-01, FED-02, FED-03, CAT-01, CAT-02
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — all 25 existing Active requirements (APP-01..APP-14, RSS-01..RSS-08, GCAL-01..GCAL-09) are prior-milestone concerns and not addressed by M033

Existing Active requirements not addressed by M033: APP-01 through APP-14 (App Platform, validated/active from M009), RSS-01 through RSS-08 (RSS Reader, active from M010), GCAL-01 through GCAL-09 (Google Calendar sync, active from M018). These are maintenance/ongoing concerns from prior milestones — none are blocked by or dependent on M033 work.

## Slices

- [ ] **S01: Deployment & Onboarding Overhaul** `risk:medium` `depends:[]`
  > After this: New instances show a two-step setup wizard (deployment mode → account creation). Instance config persists in `data/.instance-config.json`. Cloud deployment works via `docker-compose.cloud.yml` with Caddy auto-TLS.
- [ ] **S02: Isometric 2.5D Graph Layout & Icon Toggle** `risk:high` `depends:[]`
  > After this: Graph view toolbar has an "Isometric" layout option that applies CSS 3D perspective with correct click interaction, and a toggle button that switches nodes between shape-only and Lucide SVG icon display.
- [ ] **S03: Calendar View** `risk:low` `depends:[]`
  > After this: Users can open a Calendar view from the views menu. FullCalendar renders objects with date properties on month/week/day grids. Clicking an event opens the object tab. Type filter pills and scope queries work.
- [ ] **S04: Map View** `risk:low` `depends:[]`
  > After this: Users can open a Map view from the views menu. Leaflet renders objects with geo coordinates as clustered markers on OpenStreetMap tiles. An instructive empty state explains what geo properties are needed when no data matches.
- [ ] **S05: Federated SPARQL Console** `risk:low` `depends:[]`
  > After this: SPARQL console detects SERVICE clauses, validates endpoints against the configured allowlist, shows a mirror button for allowed endpoints, and provides endpoint URL autocomplete. Admin can manage the federation endpoint allowlist.
- [ ] **S06: App Catalog Pages** `risk:low` `depends:[]`
  > After this: Each app has a rich detail page showing description, features list, permissions, and install/uninstall actions. Catalog is browsable from both admin portal and workspace sidebar.

## Boundary Map

### S01 (Deployment & Onboarding)

Produces:
- `backend/app/instance_config.py` — `InstanceConfig` Pydantic model, `load_instance_config()`, `save_instance_config()` with atomic write
- `POST /api/setup/configure-instance` endpoint accepting `{mode, domain?}` and writing `data/.instance-config.json`
- Config priority chain: explicit env var > instance config file > Pydantic default
- `GET /api/auth/status` extended with `instance_configured: bool` field
- Two-step `setup.html` with deployment mode selection → account creation
- `docker-compose.cloud.yml` + `Caddyfile.cloud` for Caddy-based cloud deployment
- `.env.cloud.example` documenting required cloud vars

Consumes:
- nothing (first slice, no dependencies on other M033 work)

### S02 (Isometric Graph & Icon Toggle)

Produces:
- "isometric" entry in graph.js `LAYOUT_REGISTRY` with CSS 3D transform + inverse coordinate correction
- `_applyIsometricTransform(cy, container)` and `_removeIsometricTransform(cy, container)` functions
- Toolbar icon-toggle button with `_setIconMode(cy, mode)` switching node `background-image` between none and Lucide SVG data URIs
- User preference persistence for icon mode in localStorage

Consumes:
- nothing (graph.js is self-contained, no S01 dependency)

### S03 (Calendar View)

Produces:
- `"calendar"` added to `_VALID_RENDERERS` in views/router.py
- `backend/app/templates/browser/calendar_view.html` template with lazy-loaded FullCalendar 6.x
- `_detect_date_fields(type_iri)` in ViewSpecService — SHACL scan for `sh:datatype xsd:date|xsd:dateTime` properties
- `execute_calendar_query(type_iri, start_field, end_field, scope_filter)` in ViewSpecService
- `"calendar"` label entry in `openGenericViewTab()` workspace.js
- Calendar event click → `openObjectTab(iri)` handler

Consumes:
- nothing (follows established view renderer pattern)

### S04 (Map View)

Produces:
- `"map"` added to `_VALID_RENDERERS` in views/router.py
- `backend/app/templates/browser/map_view.html` template with lazy-loaded Leaflet + MarkerCluster
- `_detect_geo_fields(type_iri)` in ViewSpecService — SHACL scan for `wgs84:lat`/`wgs84:long` or `schema:latitude`/`schema:longitude`
- `execute_map_query(type_iri, lat_field, lng_field, scope_filter)` in ViewSpecService
- `"map"` label entry in `openGenericViewTab()` workspace.js
- Empty-state UI with instructions when no objects have geo coordinates

Consumes:
- nothing (follows same pattern as S03)

### S05 (Federated SPARQL Console)

Produces:
- SERVICE clause detection in sparql-console.js (`detectServiceEndpoints(query)` regex)
- Mirror allowlist fetch and endpoint validation UI
- Mirror button in console toolbar (visible when SERVICE targets an allowed endpoint)
- Endpoint URL autocomplete/suggestion from the allowlist
- Admin allowlist management UI (add/remove endpoints)

Consumes:
- Existing `backend/app/sparql/mirror.py` and `mirror_router.py` (GET /endpoints, POST /mirror, GET /stats, DELETE)

### S06 (App Catalog Pages)

Produces:
- `AppManifestSchema` extended with optional `category`, `features: list[str]`, `screenshots: list[str]`, `readme: str` fields
- Redesigned app detail template with description, features list, permissions display, install/uninstall actions
- Workspace-side catalog route and sidebar entry for app discovery
- Catalog list page with search/filter by category

Consumes:
- nothing (manifest schema extension is additive, existing apps continue to validate)
