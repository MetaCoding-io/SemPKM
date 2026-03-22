# M033 Research: Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul

## 1. Codebase Findings

### 1.1 Federated SPARQL Infrastructure (Already Substantial)

The federation/mirror infrastructure is more built-out than the CONTEXT implies:

- **`backend/app/sparql/mirror.py`** (MirrorService) — stores federated query results in `urn:sempkm:mirrored` with per-batch provenance graphs (`urn:sempkm:mirror-prov:{uuid}`). Validates endpoints against a configurable allowlist (`federation_allowed_endpoints` in Settings).
- **`backend/app/sparql/mirror_router.py`** — 4 endpoints: `POST /api/sparql/mirror` (execute+mirror), `GET /endpoints` (allowlist), `GET /stats`, `DELETE` (clear).
- **`frontend/static/js/sparql-console.js`** — Already has `detectServiceEndpoints()` (regex extraction of SERVICE URLs from query text), `fetchMirrorAllowlist()` (cached), `isEndpointAllowed()` validation, `handleMirrorClick()` for the mirror button, and a UI flow that shows the mirror button when a SERVICE clause targets an allowed endpoint.
- **`backend/app/sparql/client.py`** — `check_member_query_safety()` blocks SERVICE clauses for member role (owner-only). The comment notes "RDF4J handles SERVICE clause federation natively."
- **476 lines** of mirror tests, **145 lines** of federation discovery tests.

**Key insight:** SERVICE clause pass-through to RDF4J already works. The "Federated SPARQL" scope in M033 is primarily about UI polish (SERVICE endpoint assistance in the console, better result display) and mirror layer refinement — not building federation from scratch.

**Risk: Low.** Infrastructure exists. Work is incremental.

### 1.2 View Renderer System

The view system has a clear, well-bounded extension pattern:

- **Backend:** `backend/app/views/router.py` — `_VALID_RENDERERS = {"table", "card", "graph", "kanban"}`. Adding a new renderer means: (1) add to this set, (2) create a template in `backend/app/templates/browser/`, (3) add an `elif renderer == "calendar":` branch in `generic_view()`, (4) add the JS initialization in the template's `<script>` block.
- **Frontend:** `openGenericViewTab(renderer, scopeQuery, scopeLabel)` in `workspace.js` handles tab creation. The labels dict at the top just needs a new entry.
- **Templates:** Each renderer has its own template (`table_view.html`, `cards_view.html`, `graph_view.html`, `kanban_view.html`). They all follow the same pattern: include type_filter_pills.html, include view_toolbar.html, create a container div, inline a `<script>` that initializes the JS component.
- **CSS:** `.view-flex-column` wrapper for full-height views (graph, kanban use it; table/cards don't need it). Calendar and map would use it.

**Adding a new view renderer is a well-trodden path.** The risk is in the JS library integration, not the backend plumbing.

### 1.3 Existing Graph View (Cytoscape.js)

- **`frontend/static/js/graph.js`** — 709 lines. Uses Cytoscape.js 3.33.1 (CDN). 
- Layout registry with `fcose`, `dagre`, `concentric`. Model-contributed layouts via `registerLayout()`.
- Icon→shape mapping: 6 hardcoded Lucide icon→Cytoscape shape entries. Per-type shapes applied via `window._sempkmIcons.graph`. **No actual SVG icons on nodes** — just shape differentiation (rectangle, diamond, ellipse, round-rectangle).
- Node popovers appended to `document.body` (D293 pattern — escapes dockview stacking context).

**For the isometric 2.5D view:** Cytoscape.js is strictly 2D — its canvas renderer has no z-axis. The "isometric" effect must be achieved through CSS 3D transforms on the container (rotateX + rotateY to simulate isometric projection) or through a completely different rendering approach. CSS transforms on a Cytoscape container are known to cause interaction coordinate mapping issues (Issue #1756).

**For the icon toggle:** Adding Lucide SVG icons to Cytoscape nodes requires using `background-image` with SVG data URIs or the `cytoscape-svg` extension. The current shape-only approach is simpler; toggle would switch between shape mode (current) and icon mode (SVG on node face).

### 1.4 Date/Time Properties in Models

Calendar view needs date properties to map events to a timeline:

- **bpkm:Event** — `schema:startDate`, `schema:endDate`, `bpkm:allDay` (perfect for FullCalendar)
- **bpkm:Project** — `schema:startDate`, `schema:endDate` (can render as date ranges)
- **bpkm:Task** — has `bpkm:dueDate` (from sync apps), `dcterms:created`, `dcterms:modified`
- **bpkm:Milestone** — likely has date properties similar to Project

The calendar view's SPARQL temporal query builder needs to discover which properties hold date values. The pattern from kanban (D291 — SHACL `sh:in` scan) can be adapted: scan SHACL PropertyShapes for `sh:datatype xsd:date` or `xsd:dateTime`, prefer properties with "date"/"start"/"end" in the path name.

### 1.5 Geolocation Properties

No models currently define lat/long or geo properties. `bpkm:location` on Event is a string (e.g. "Conference Room A"), not a coordinate pair.

**Implication for map view:** Either (a) geocode string locations via an external service (adds a network dependency), or (b) require dedicated lat/long properties. For v1, the map view should work with any type that has `wgs84:lat`/`wgs84:long` or `schema:latitude`/`schema:longitude` properties. It won't have data to show unless a model defines geo properties or the user adds them manually.

**Recommendation:** Ship the renderer but don't try to force-fit it to existing models. A "Research Workflow" or "CRM" model extension could add geo-enabled types later. The map view with no data shows a centered-on-world-map empty state with instructions.

### 1.6 App Catalog Infrastructure

- **Manifest schema** (`backend/app/apps/manifest.py`): `AppManifestSchema` has `description: str`, `author: AppAuthor | None`, `license: str`, `permissions: AppPermissions`, `dependencies: AppDependencies`. Missing: `screenshots`, `features`, `category`, `readme`, `icon`.
- **Admin pages**: `list.html` shows cards with name, version, status badge, description snippet. `detail.html` shows status, PID, uptime, restarts, error message, permissions, logs.
- **11 apps** in `apps/` directory (10 sync apps + 1 test app + RSS reader). Only RSS reader is v1.0.0; others are v0.1.0.
- **No workspace-side catalog** — apps are only visible in the admin portal.

**To build rich catalog pages:** Extend `AppManifestSchema` with optional `category`, `screenshots: list[str]`, `features: list[str]`, `readme: str` fields. The detail page template needs a redesign from admin-monitoring-focused to catalog-showcase-focused. Consider exposing catalog in workspace (not just admin) for discoverability.

### 1.7 Deployment & Onboarding Infrastructure

- **`frontend/static/setup.html`** — 41 lines, single-step form (token + email). No deployment mode selection.
- **`backend/app/config.py`** — `base_namespace: str = "https://example.org/data/"`. No instance config file support.
- **`docker-compose.yml`** — nginx frontend, no Caddy profile. `docker-compose.demo.yml` uses Caddy already.
- **Existing `Caddyfile`** at project root (for demo instance).
- **Design doc** (`.gsd/design/DEPLOYMENT-AND-ONBOARDING-DESIGN.md`) — 566 lines, thorough. Covers setup wizard redesign, Caddy cloud profile, local TLS, BASE_NAMESPACE strategy, instance config file, implementation phases.

The design doc is essentially a complete spec. Implementation is mostly about following it.

### 1.8 CDN Loading Pattern

All external libraries are loaded via CDN `<script>` tags in `base.html`:
- Cytoscape.js 3.33.1 + fcose + dagre (unpkg)
- htmx 2.0.4 (unpkg)
- GridStack 10 (jsdelivr)
- Lucide 0.575.0 (unpkg)
- marked + marked-highlight (jsdelivr)
- highlight.js 11.11.1 (cdnjs)
- DOMPurify (jsdelivr)
- ninja-keys 1.2.2 (unpkg)
- Driver.js 1.4.0 (jsdelivr)
- Split.js 1.6.5 (unpkg)

**Pattern for new libraries:** Add `<script>` tags to `base.html` or lazy-load in the view template. FullCalendar and Leaflet should lazy-load only in their view templates (not all pages) to avoid blocking the initial workspace load.

## 2. Technology Assessment

### 2.1 FullCalendar 6.x

- **CDN:** `https://cdn.jsdelivr.net/npm/fullcalendar@6/index.global.min.js` — single file includes core + dayGrid + timeGrid + list views. ~115KB gzipped.
- **Initialization:** `new FullCalendar.Calendar(el, { initialView: 'dayGridMonth', events: [...] })`. Clean vanilla JS API.
- **Event format:** `{ title, start, end, allDay, color, url, extendedProps }` — maps directly to SPARQL result bindings.
- **Views:** dayGridMonth, timeGridWeek, timeGridDay, listWeek built-in. No additional plugins needed for M033 scope.
- **Risk: Low.** Well-established library, good vanilla JS support, CDN distribution, clear API.

### 2.2 Leaflet.js + MarkerCluster

- **CDN:** Leaflet 1.9.4 (~42KB gzipped) + Leaflet.markercluster (~10KB gzipped). Both have CDN distributions.
- **Initialization:** `L.map('container').setView([lat, lng], zoom)` + `L.tileLayer(url).addTo(map)`.
- **Clustering:** `L.markerClusterGroup({ chunkedLoading: true })` + `markers.addLayer(L.marker([lat, lng]))`.
- **Tile source:** OpenStreetMap tiles (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`). Free, no API key required.
- **Offline graceful degradation:** Leaflet handles tile loading errors silently — map shows a grey grid when tiles can't load. Good for air-gapped self-hosted instances.
- **Risk: Low.** But usability depends on models having geo properties, which none currently do.

### 2.3 Isometric 2.5D Graph View

Three technical approaches considered:

**A. CSS 3D transform on Cytoscape container:**
Apply `transform: rotateX(60deg) rotateY(0deg) rotateZ(-45deg)` to the Cytoscape container. This creates an isometric projection of the existing 2D graph. Problem: Cytoscape's event handling uses clientX/clientY which don't account for CSS transforms — click coordinates will be wrong. The Cytoscape team acknowledges this issue (#1756). Workaround exists (transform the mouse coordinates inversely) but is fragile.

**B. Cytoscape with z-position and CSS perspective:**
Cytoscape's `position()` API only supports x,y. There's no z-coordinate. Can simulate depth via node size, opacity, and y-offset (parallax), but this isn't true isometric.

**C. Custom rendering with HTML/CSS 3D layers:**
Render each "layer" as a separate CSS-transformed plane (like stacked glass panes). Nodes on each layer are absolutely positioned. Edges drawn as SVG lines. This gives true isometric with correct interaction but requires building a graph renderer from scratch.

**Recommendation:** Option A with CSS transform + coordinate correction. It reuses all existing Cytoscape infrastructure (layouts, styling, popover). The coordinate correction is ~20 lines of matrix math. Ship as a "layout" option in the graph view, not a separate renderer. A configurable z-layer dimension (e.g., group by type, group by tag) determines vertical stacking via node y-offset before the CSS transform is applied.

**Risk: Medium.** CSS 3D + Cytoscape coordinate mapping is novel. Needs prototyping.

### 2.4 Graph View Icon Toggle

- Current: Cytoscape `shape` property maps icon names to shapes (ellipse, rectangle, diamond, round-rectangle).
- Needed: Toggle between shape mode and icon-on-node mode (Lucide SVG rendered on the node face).
- Cytoscape supports `background-image` with data URIs. Lucide provides SVG strings. Convert to data URI: `'data:image/svg+xml;utf8,' + encodeURIComponent(svgString)`.
- Toggle is a toolbar button that re-applies styles with/without background-image.
- **Risk: Low.** Standard Cytoscape styling feature.

## 3. Dependency and Integration Map

```
M032 (Block-Based Custom UI Builder) → M033

External libraries (new):
  - FullCalendar 6.x (CDN, lazy-loaded in calendar_view.html)
  - Leaflet 1.9.x (CDN, lazy-loaded in map_view.html)
  - Leaflet.markercluster 1.5.x (CDN, lazy-loaded with Leaflet)

Existing systems touched:
  - SPARQL mirror service (refinement, UI assistance)
  - View renderer system (2 new renderers: calendar, map)
  - Graph view (icon toggle, isometric layout option)
  - App manifest schema (catalog metadata fields)
  - Admin app templates (catalog page redesign)
  - Setup wizard (2-step flow with deployment mode)
  - Docker Compose (Caddy cloud profile)
  - Config system (instance config file, priority chain)
```

## 4. Risk Assessment

| Area | Risk | Reasoning | Mitigation |
|------|------|-----------|------------|
| Federated SPARQL | Low | Infrastructure already built; incremental UI polish | Start here for quick wins |
| Calendar view | Low | FullCalendar is well-documented, Event type has date fields, view pattern is established | Follow table/graph view template pattern exactly |
| Map view | Low-Medium | Library is simple but **no models have geo properties** — view ships empty for all current data | Document clearly, ship as capability for custom types. Don't block on model changes. |
| Isometric 2.5D | Medium-High | CSS 3D + Cytoscape coordinate mapping is untested. May hit rendering bugs, interaction glitches | Prototype early (S01 or S02). If coordinate correction is unreliable, fall back to parallax depth simulation. |
| Graph icon toggle | Low | Standard Cytoscape background-image feature | Implement alongside isometric or as a small standalone slice |
| App catalog | Low-Medium | Manifest extension is straightforward, but template redesign from monitoring→catalog is nontrivial UI work | Keep v1 simple — description, features list, permissions. Screenshots can be a future enhancement. |
| Deployment overhaul | Medium | Design doc is thorough but touches config loading, setup wizard, Docker Compose, and Caddy — cross-cutting | Follow the design doc phases sequentially. Instance config + namespace strategy first, then wizard UI, then Caddy profile. |

## 5. Slice Boundary Recommendations

### Natural boundaries:

1. **Federated SPARQL polish** — SERVICE assistance UI, mirror allowlist management, console improvements. Low risk, high completion confidence. Proves nothing architecturally new — good warm-up slice.

2. **Calendar view** — New FullCalendar renderer + temporal query builder. Self-contained (1 template, 1 JS file, backend changes to generic_view, SPARQL date field detection). Demoable end-to-end with existing Event data.

3. **Map view** — Leaflet renderer + geo property detection. Similar scope to calendar but ships with empty-state UX (no current models have geo properties). Could be parallel with calendar since they're independent renderers.

4. **Graph icon toggle** — Small, self-contained. Toolbar button + Cytoscape style update. Could combine with isometric slice if timeline allows.

5. **Isometric 2.5D graph** — Medium risk. CSS 3D transform + coordinate correction. Should be its own slice or combined with icon toggle. Needs prototyping before committing to full implementation. **Prove first.**

6. **App catalog pages** — Manifest extension + template redesign. Independent of other slices. UI-heavy.

7. **Deployment & onboarding** — Instance config, setup wizard, Caddy cloud profile. Cross-cutting, touches config loading, auth status, Docker Compose. Independent of all other slices. **Prove early** because BASE_NAMESPACE misconfiguration is a data-integrity risk.

### Recommended ordering by risk:

1. **Deployment & onboarding first** — Eliminates the `example.org` default (data-integrity risk). Design doc provides a complete spec. Changes to config loading affect all subsequent work.
2. **Isometric 2.5D graph second** — Highest technical risk. Prove the CSS 3D + Cytoscape approach works or fail fast to a simpler alternative.
3. **Calendar view third** — High-value, medium complexity, demoable.
4. **Map view + graph icon toggle** — Lower priority, lower risk.
5. **Federated SPARQL polish** — Incremental improvements on existing infrastructure.
6. **App catalog** — Least coupled, can slide late without blocking anything.

## 6. Requirements Analysis

### Active requirements that M033 should address:

None of the 25 active requirements (14 APP + 8 RSS + 3 GCAL) are directly addressed by M033. M033 introduces new capability areas.

### Candidate requirements for M033:

| ID Prefix | Requirement | Category | Notes |
|-----------|-------------|----------|-------|
| FED-01 | SERVICE clause queries execute against allowed endpoints and results are displayed | core-capability | Already largely works — polish pass |
| FED-02 | Mirror allowlist is configurable from admin settings UI | enhancement | Currently env-var only |
| FED-03 | SPARQL console provides SERVICE endpoint URL assistance | enhancement | Autocomplete/suggestion for known endpoints |
| CAL-01 | Calendar view shows objects with date properties on month/week/day calendar | core-capability | FullCalendar integration |
| CAL-02 | Calendar view auto-detects date fields from SHACL shapes | core-capability | Like kanban status detection (D291) |
| CAL-03 | Type filter pills work on calendar view | enhancement | Follows established pattern |
| MAP-01 | Map view shows objects with geo coordinates as markers | core-capability | Leaflet integration |
| MAP-02 | Marker clustering groups nearby objects at low zoom | enhancement | Leaflet.markercluster |
| MAP-03 | Marker popup shows object label and type with click-to-open | enhancement | Standard popup pattern |
| ISO-01 | Isometric 2.5D graph layout option in graph view | enhancement | CSS 3D transform approach |
| ISO-02 | Configurable z-layer dimension (group by type, tag, etc.) | enhancement | Determines vertical stacking |
| ICON-01 | Graph view icon toggle switches between shape-only and SVG icon display | enhancement | Toolbar button |
| CAT-01 | App catalog detail pages show description, features, permissions | core-capability | Manifest extension + template |
| CAT-02 | Catalog pages are browsable from workspace (not just admin) | enhancement | Discovery surface |
| DEPLOY-01 | Setup wizard collects deployment mode before account creation | core-capability | Per design doc |
| DEPLOY-02 | Local instances use `urn:sempkm:{uuid}/` as BASE_NAMESPACE | core-capability | Per design doc |
| DEPLOY-03 | Cloud deployment Caddy profile with automatic TLS | core-capability | Per design doc |
| DEPLOY-04 | Instance config file persists across container rebuilds | core-capability | Per design doc |

### Deferred requirements that may interact:

- **VIEW-06** (deferred): Configurable card fields per view spec — calendar/map views don't need this.
- **VIEW-07** (deferred): View export (CSV, JSON) — applies to new views too, but still deferred.
- **VFS-13** (deferred): VFS writes — doesn't interact with M033.

### Missing/implicit requirements:

- **Calendar event click → open object tab** — Table/cards/graph all do this; calendar must too. Table stakes.
- **Map graceful degradation when offline** — Tiles won't load in air-gapped environments. Show a message, not a broken grid.
- **Isometric fallback** — If CSS 3D + Cytoscape coordinate mapping fails, there should be a simpler "layered" visualization that doesn't require 3D transforms.
- **Caddy config validation** — SEMPKM_DOMAIN must be validated before writing Caddyfile. DNS resolution check or at least format check.
- **BASE_NAMESPACE one-way door warning** — Setup wizard must clearly state this cannot be changed after data creation. The design doc specifies this but it should be a requirement.

## 7. Technology-Specific Constraints

### FullCalendar CDN loading

FullCalendar 6.x provides `fullcalendar/index.global.min.js` as a single-file CDN bundle. This includes core + dayGrid + timeGrid + list views. The file is ~115KB gzipped — should be lazy-loaded only in `calendar_view.html`, not in `base.html`.

### Leaflet CSS requirement

Leaflet requires its CSS file loaded before JS initialization. The Leaflet CSS handles marker icons, popup styling, and tile rendering. Must include in the map view template:
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

### Cytoscape.js + CSS 3D transforms

Known issue: CSS transforms on a Cytoscape container ancestor cause coordinate mismatch between browser events and Cytoscape's internal coordinate space. The fix involves intercepting mouse events and applying the inverse transform matrix. Cytoscape's `cytoscape.util.getWheelDelta` and core renderer also need the correction applied.

### Instance config file + Docker volumes

The `data/` directory is volume-mounted (`sempkm_data:/app/data`). `data/.instance-config.json` persists across container rebuilds because it's on the Docker volume. The file must be written atomically (write to `.tmp`, rename) to avoid corruption if the container is killed mid-write.

## 8. Existing Patterns to Reuse

| Pattern | Where Used | Reuse In |
|---------|-----------|----------|
| View renderer registration | `_VALID_RENDERERS` set, template pattern | Calendar, map renderers |
| SHACL property detection | `_detect_status_field()` in kanban | Date field detection for calendar, geo field detection for map |
| CDN lazy loading | Graph view script tags in template | FullCalendar, Leaflet loading |
| `.view-flex-column` wrapper | Graph, kanban views | Calendar, map views |
| Document.body popover escape | Graph popovers (D293) | Map popups (if custom), calendar event tooltips |
| Manifest schema extension | `AppManifestSchema` Pydantic model | Add `category`, `screenshots`, `features` fields |
| Type filter pills | `type_filter_pills.html` include | Calendar, map views |
| View toolbar | `view_toolbar.html` include | Calendar, map views |
| openGenericViewTab | `workspace.js` | Add "calendar" and "map" to labels dict |

## 9. Skills Assessment

No relevant installable skills found for FullCalendar, Leaflet, or Cytoscape. The `frontend-design` and `make-interfaces-feel-better` bundled skills are relevant for the catalog page redesign and calendar/map view styling. The `best-practices` skill is relevant for the deployment overhaul (security, config management).

## 10. Open Questions for Planner

1. **Isometric 2.5D: How hard to commit?** The CSS 3D approach is technically novel for this codebase. Should the planner allocate a time-boxed spike in an early slice, with a defined fallback (e.g., depth-by-opacity/size simulation without CSS transforms)?

2. **Map view without data: Ship or defer?** No current models have geo coordinates. The renderer would ship functional but empty for all existing types. Is the capability worth the slice cost, or should it wait until a model with geo properties is planned?

3. **App catalog workspace surface: How much?** The CONTEXT says "rich app catalog pages" but doesn't specify whether these are admin-only or workspace-visible. A simple enhancement of the existing admin app detail page is much less work than building a new workspace catalog tab.

4. **Deployment overhaul vs. new features ordering:** The design doc suggests instance config first (data-integrity risk), but view renderers are more user-visible. Should deployment ship before or after the new views?

5. **FullCalendar event editing:** Should clicking a calendar event open the object tab for editing, or should the calendar support inline drag-to-reschedule (which would require a write-back path for date changes)? The CONTEXT says "month/week/day views" but doesn't mention editing. Read-only display is the safe v1 scope.
