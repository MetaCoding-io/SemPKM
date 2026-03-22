# M033 Roadmap: Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul

**Status:** Planned
**Slices:** 7
**Risk Profile:** High (SPARQL federation scoping), Medium (3 new renderers + deployment), Low (catalog + icon toggle)

---

## Strategic Rationale

This milestone spans 7 independent feature areas. The decomposition follows the feature boundaries naturally — each area is a distinct user-facing capability with its own verification surface. The ordering is risk-first:

1. **Federated SPARQL** goes first because `scope_to_current_graph()` is the #1 risk. It uses regex to inject FROM clauses before WHERE — this will mangle SERVICE clauses. If this pattern can't be extended to handle federation, the entire feature needs a different approach. Proving it early de-risks the milestone.

2. **Calendar View** goes second because it establishes the "new renderer" pattern — registering in RENDERER_REGISTRY, lazy-loading a vendor library (FullCalendar follows the D272 pattern), building a SPARQL query for a new data dimension (temporal), and wiring into the generic view endpoint. Data exists (bpkm:Event has schema:startDate/endDate).

3. **Map View** goes third, following the calendar renderer pattern. It has an additional complication: no geo data exists in any model. The slice must add schema:latitude/longitude to the basic-pkm Event shape (or a new Location type) to be demoable.

4. **Isometric 2.5D Graph** is medium-high risk. Per research, this should be a custom Cytoscape layout that computes 2D projections of conceptual z-layers — NOT CSS 3D transforms on the container (which would break Cytoscape's coordinate system). The math is novel but the registration pattern (registerLayout) is proven.

5. **App Catalog Pages** is low risk. Manifest data exists for all 11 apps, screenshot capture infrastructure exists, and the UI follows existing workspace tab patterns.

6. **Graph Icon Toggle** is the smallest feature — a toolbar button in graph.js that switches between shape-only and icon-on-node rendering. Self-contained.

7. **Deployment & Onboarding** goes last because it's infrastructure-level work with a thorough approved design doc, and it doesn't block any other feature. The setup wizard, Caddy cloud profile, and mkcert integration are well-specified.

### Key Patterns to Reuse

- **RENDERER_REGISTRY** (`backend/app/views/registry.py`): register_renderer() for calendar and map, exactly like kanban was added
- **_VALID_RENDERERS** in router.py: extend the set with "calendar" and "map"
- **Lazy-loading pattern** (D272): FullCalendar and Leaflet loaded on-demand like Yasgui and Chart.js
- **Generic view endpoint** (`/browser/views/generic/{renderer}`): calendar and map branch into the existing if/elif chain
- **registerLayout()** in graph.js: isometric layout registered exactly like fcose/cose
- **InferenceService pattern**: mirrored triples service follows urn:sempkm:inferred → urn:sempkm:mirrored
- **scope_to_current_graph()**: extended to include FROM <urn:sempkm:mirrored>
- **Dockview workspace tabs**: catalog pages open as special-panel tabs like the docs viewer
- **Demo Caddy pattern** (M025, D246): cloud profile reuses the proven Caddy → nginx → API stack

### Boundary Contracts

- **SPARQL layer**: scope_to_current_graph() must detect and pass through SERVICE clauses without scoping their contents; must add FROM <urn:sempkm:mirrored> alongside current and inferred graphs
- **Renderer registry**: calendar and map registered with templates; _VALID_RENDERERS extended
- **View explorer**: new entries for Calendar, Map, and App Catalog in the sidebar
- **Graph layout registry**: isometric layout registered with registerLayout(), selectable from layout picker
- **Docker Compose**: cloud profile is a separate file (docker-compose.cloud.yml) that extends the base, not modifying docker-compose.yml

---

## Slices

- [x] **S01: Federated SPARQL & Mirrored Triples** `risk:high` `depends:[]`
  - Demo: User writes SERVICE query in SPARQL console, sees federated results, clicks Mirror, triples persist in urn:sempkm:mirrored with provenance badges.
  - Result: 95 unit tests pass. 5 tasks delivered (T01-T05, consolidating original 7 roadmap tasks).

- [x] **S02: Calendar View Renderer** `risk:medium` `depends:[]`
  - Demo: User opens "Calendar" from VIEWS explorer, sees bpkm:Event objects on a FullCalendar month grid. Clicking an event opens the object tab. Type filter pills narrow displayed events. Switching to week/day view works.

- [x] **S03: Map View Renderer** `risk:medium` `depends:[]`
  - Demo: User opens "Map" from VIEWS explorer, sees objects with geographic coordinates as markers on an OpenStreetMap. Clicking a marker shows a popup with object info. Marker clustering handles dense data.
  - Result: 25 unit tests pass. 3 tasks delivered (T01-T03). Leaflet 1.9.4 + MarkerCluster vendored. Geo detection from SHACL shapes. 4 seed events with global coordinates.

- [x] **S04: Isometric 2.5D Graph View** `risk:medium-high` `depends:[]`
  - Demo: User selects "Isometric" from the graph view layout picker. Nodes arrange on horizontal z-layers stratified by RDF type. Translucent layer planes visible behind nodes. Edges connect across layers.
  - Result: 2 tasks delivered (T01-T02). ~270-line Cytoscape layout extension with compound parent layer planes, full graph.js integration (styles, cleanup, event guards, filter propagation, expansion).

- [x] **S05: App Catalog Pages** `risk:low` `depends:[]`
  - Demo: User clicks "App Catalog" in workspace explorer, sees a browsable grid of all 11 apps. Detail page shows description, permissions, screenshots, install/uninstall button.
  - Result: 14 unit tests pass. 2 tasks delivered (T01-T02). Catalog router with list/detail/install/uninstall endpoints, card grid + detail templates, workspace JS/CSS integration, explorer sidebar entry.

- [x] **S06: Graph View Icon Toggle** `risk:low` `depends:[]`
  - Demo: User clicks a toolbar button on any graph view. Nodes switch between abstract shapes and Lucide SVG icons. Toggle state persists across page loads.
  - Result: 1 task delivered (T01). ~120 lines added across 3 files. SVG data URI construction via Lucide + module cache. Isometric layer planes excluded. localStorage persistence.

- [x] **S07: Deployment & Onboarding Overhaul** `risk:medium` `depends:[]`
  - Demo: Fresh Docker instance shows setup wizard with deployment mode step. docker-compose.cloud.yml starts Caddy + nginx + API + triplestore with automatic HTTPS.
  - Result: 26 unit tests pass. 4 tasks delivered (T01-T04). Instance config model, configure-instance endpoint with namespace guard, two-step setup wizard UI, Caddy cloud + local TLS profiles, comprehensive documentation.

---

## Requirement Coverage

M033 introduces 7 entirely new feature areas. No existing Active requirements in REQUIREMENTS.md map to these features — new requirements will be created during slice planning/execution.

### Existing Requirements Advanced by M033
| Deferred Item | M033 Coverage |
|---|---|
| "Timeline/calendar renderers — v2+" | S02 delivers Calendar View |
| "3D graph visualization — experimental" | S04 delivers Isometric 2.5D |

### New Requirements to Create (by slice)
| Slice | Prefix | Requirements |
|---|---|---|
| S01 | SPARQL-FED- | Federation SERVICE pass-through, endpoint allowlist, mirror service, mirrored graph scoping, provenance tracking, SPARQL console UI |
| S02 | CAL- | Calendar renderer, date property detection, FullCalendar lazy-load, month/week/day views, click-to-open |
| S03 | MAP- | Map renderer, geo property detection, Leaflet lazy-load, marker clustering, popup, graceful degradation |
| S04 | ISO- | Isometric layout, z-layer dimensions, layer planes, label readability |
| S05 | CATALOG- | Catalog list, detail page, screenshots, install/uninstall, explorer entry |
| S06 | GRAPH- | Icon toggle, SVG rendering, localStorage persistence |
| S07 | DEPLOY- | Setup wizard deployment step, instance config, Caddy cloud profile, mkcert, namespace guard |

### Existing Active Requirements — Not Affected
All existing Active requirements (APP-*, RSS-*, EVENT-*, GCAL-*, SYNC-*, JIRA-*, MON-*, DEMO-*, SITE-*, PERF-*, LINT-*, etc.) are outside M033 scope. The FED-01 through FED-13 requirements cover SemPKM-to-SemPKM federation (M002), not SPARQL endpoint federation — they are unaffected.

---

## Boundary Map

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (nginx + static)                               │
│  ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ SPARQL       │ │ Calendar │ │ Map View │ │ Graph   │ │
│  │ Console      │ │ View     │ │ (Leaflet)│ │ (Cyto)  │ │
│  │ (Yasgui)     │ │(FullCal) │ │          │ │+Isomet  │ │
│  │ +SERVICE UI  │ │          │ │          │ │+IconTgl │ │
│  └──────┬───────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ │
│         │              │            │             │      │
│  ┌──────┴──────┐ ┌─────┴────────────┴─────────────┘      │
│  │ setup.html  │ │ App Catalog (catalog list + detail)   │
│  │ +deploy step│ │                                        │
│  └──────┬──────┘ └────────────────────┬──────────────────┘│
└─────────┼─────────────────────────────┼──────────────────┘
          │                             │
┌─────────┼─────────────────────────────┼──────────────────┐
│  Backend (FastAPI)                    │                   │
│  ┌──────┴──────┐  ┌──────────────────┴───────────┐       │
│  │ setup/      │  │ views/                        │       │
│  │ configure-  │  │ router.py (generic/{renderer})│       │
│  │ instance    │  │ registry.py (+calendar, +map) │       │
│  └──────┬──────┘  │ service.py (+cal/map queries) │       │
│         │         └──────────────────┬────────────┘       │
│  ┌──────┴──────┐  ┌─────────────────┴─────────┐          │
│  │ config.py   │  │ sparql/client.py           │          │
│  │ +instance   │  │ scope_to_current_graph()   │          │
│  │  config     │  │ +SERVICE pass-through      │          │
│  └─────────────┘  │ +MIRRORED_GRAPH            │          │
│                   └──────────────┬──────────────┘         │
│  ┌─────────────────────────────┐│ ┌───────────────────┐   │
│  │ federation/                 ││ │ browser/           │   │
│  │ mirror_service.py           ││ │ apps.py            │   │
│  │ endpoint_manager.py         ││ │ +catalog routes    │   │
│  └─────────────────────────────┘│ └───────────────────┘   │
└─────────────────────────────────┼─────────────────────────┘
                                  │
┌─────────────────────────────────┼─────────────────────────┐
│  RDF4J Triplestore              │                         │
│  urn:sempkm:current             │                         │
│  urn:sempkm:inferred            │                         │
│  urn:sempkm:mirrored  (NEW)     │                         │
│  SERVICE → external endpoints ──┘                         │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│  Docker Compose                                           │
│  docker-compose.yml (existing — unchanged)                │
│  docker-compose.cloud.yml (NEW — adds Caddy for HTTPS)    │
└───────────────────────────────────────────────────────────┘
```

---

## Open Question Resolutions (from Context)

| Question | Resolution | Rationale |
|---|---|---|
| Mirror granularity | Entire federated result for v1 | Simpler than per-triple selection; users can narrow queries instead |
| Mirror staleness / TTL | No TTL for v1 | Adds complexity; Wikidata labels rarely change; add later if needed |
| Calendar date property discovery | Auto-detect from SHACL shapes | Properties with xsd:date/xsd:dateTime datatype; better UX than manual config |
| Map coordinate format | schema:latitude/longitude only for v1 | Most common; WKT support deferred |
| Isometric layer rendering | Custom Cytoscape layout (2D projection) | CSS 3D transforms would break Cytoscape's coordinate system (per research) |
| App catalog screenshots | Pre-captured and bundled | Simpler than dynamic capture; doesn't require running stack at install time |

---

## Milestone Definition of Done

All of the following must be true:

- [ ] **Federation works end-to-end:** User writes a SERVICE query against Wikidata in the SPARQL console, sees federated results, clicks Mirror, and mirrored triples appear in urn:sempkm:mirrored queryable alongside local and inferred data
- [ ] **Calendar view renders temporal data:** Calendar view shows bpkm:Event objects on a FullCalendar month grid; clicking an event opens the object tab; type filter pills work; week/day views accessible
- [ ] **Map view renders geographic data:** Map view shows objects with geo coordinates as Leaflet markers on OpenStreetMap tiles; popup shows object info; marker clustering handles dense data
- [ ] **Isometric graph shows layered visualization:** Graph view layout picker includes "Isometric"; selecting it arranges nodes on 3+ z-layers stratified by type; translucent layer planes visible; edges cross between layers
- [ ] **App catalog is browsable:** Workspace explorer has "App Catalog" entry; catalog page shows all 11 apps; detail page for any app shows description, permissions, screenshots, install/uninstall button
- [ ] **Graph icon toggle works:** Toolbar button toggles between shape-only and Lucide icon rendering on graph nodes; state persists per view across page loads
- [ ] **Setup wizard configures deployment:** Fresh instance shows deployment mode step; "local" sets urn:sempkm:{uuid}/ namespace; "custom domain" sets https://{domain}/data/ namespace; existing instances not affected
- [ ] **Cloud profile deploys with HTTPS:** docker-compose.cloud.yml starts Caddy + nginx + API + triplestore; Caddy handles automatic TLS
- [ ] **All new features survive Docker restart:** Mirrored triples persist; calendar/map views re-render; catalog data intact; deployment config persisted in data/.instance-config.json

---

## Skill Recommendations

No installed skills are directly relevant to the core technologies (FullCalendar, Leaflet, Cytoscape.js, SPARQL, Caddy). Skills discovered:
- `zenobi-us/dotfiles@leaflet-mapping` (73 installs) — Leaflet mapping skill, potentially useful for S03
- `letta-ai/skills@sparql-university` (42 installs) — SPARQL skill, potentially useful for S01
- `muninn-huginn/caddy-skill@caddy` (23 installs) — Caddy configuration, potentially useful for S07

Install counts are low and the project already has deep SPARQL/Caddy patterns established. Recommend skipping external skills unless a specific slice hits a blocker.
