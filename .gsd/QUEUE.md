# GSD Queue

Append-only log of queued future milestones and ideas.

---

## Rethink Views: Generic Views with Query Binding

**Queued:** 2026-03-14  
**Status:** Idea  

The current VIEWS section is cluttered with per-type duplicates (e.g., "Concept Graph", "Concept Card", "Note Card", "Project Card"). These should be **generic view types** — Graph View, Card View, Table View — that work across all objects by default and can optionally be scoped via saved queries or type filters.

**Problems with current approach:**
- VIEWS section is crowded with near-duplicates (one per type × view mode)
- Adding a new type multiplies the view count
- Users see "Concept Card" and "Note Card" as separate things when they're the same view with a type filter

**Proposed model:**
- **Generic views**: Graph, Card, Table (and future: Timeline, Kanban, etc.) — each is a single entry
- **Default scope**: All objects (no type filter)
- **Optional binding**: Connect a view to a saved SPARQL query for custom scoping
- **In-view filtering**: Type filter dropdown/pills within the view itself (like faceted search)
- **Saved view instances**: Users can save a configured view (e.g., "My Project Cards" = Card view + Project type filter + sort by modified) as a named entry under MY VIEWS

This connects to the VFS v2 saved query scoping work — views and VFS mounts could share the same query binding mechanism.

---

## Workspace UX Enhancements

**Queued:** 2026-03-12  
**Status:** Partially done (M003 shipped hierarchy, tags, comments, favorites)  

### Remaining Ideas

1. **Hierarchical Tag Tree** — Tags using `/` as delimiter (e.g. `garden/cultivate`, `output/newsletter`) should nest in the By Tag explorer mode. Group by prefix so `#garden` becomes a parent folder containing `cultivate`, `plant`, `question`, etc. Currently renders as a flat list. Affects: `_handle_by_tag()` in workspace.py, `tag_tree.html` template.

2. **Tag Autocomplete in Edit Form** — Tag fields (`bpkm:tags`, `schema:keywords`) render as plain text inputs in edit mode. Should have autocomplete that suggests existing tag values from the graph. Read mode already shows tag pills correctly. Affects: `forms/_field.html` template, needs new endpoint or reuse of tag-children query.

---

## MCP Server for AI Agent Access

**Queued:** 2026-03-10  
**Status:** Idea — deferred from M002  

MCP server exposing object browse/search, SPARQL query, graph traversal, and write operations to AI agents via the Model Context Protocol. Enables Claude, GPT, etc. to interact with the knowledge base directly.

**Research:** `.planning/todos/pending/2026-03-10-build-mcp-server-for-ai-agent-access-to-sempkm.md`

---

## Notion Import Wizard

**Queued:** 2026-03-12  
**Status:** Researched  

Interactive import flow for Notion workspace exports (ZIP first, API later), mirroring the Obsidian import wizard pattern. Covers databases → types, rows → objects, relations → edges, with dashboard/rollup/formula metadata preservation.

**Research:** `.planning/notion-import-research.md`

---

## Data Quality & Backend Error Fixes

**Queued:** 2026-03-13  
**Status:** Documented  

Two known backend error classes found during M003 testing: (1) malformed `xsd:dateTime` literals from Obsidian import containing text after the date portion (rdflib warnings, non-fatal), and (2) validation report store returning HTTP 415 from RDF4J (validation works but report not persisted). Neither blocks normal usage.

**Details:** `.gsd/design/KNOWN-BACKEND-ERRORS.md`

---

## VFS Mount Spec v2

**Queued:** 2026-03-13  
**Status:** Designed  

Next-generation mount capabilities: saved query scoping, composable strategy chains (multi-level folders), type filters without SPARQL, preview improvements, filename templates. Write support deferred to its own milestone.

**Design:** `.gsd/design/VFS-V2-DESIGN.md`

---

## In-App Relationship (Property) Creation

**Queued:** 2026-03-13  
**Status:** ✅ Done (M004) — Full property CRUD from RBox tab and Custom section

---

## Full CRUD for Custom Types & Relationships

**Queued:** 2026-03-13  
**Status:** ✅ Done (M004) — Edit, delete, and Custom section all shipped. Only "cascade delete orphaned instances" remains as a minor enhancement.

---

## "Create New Object" Opens in New Tab

**Queued:** 2026-03-13  
**Status:** ✅ Done (M004) — showCreateFormForType always creates fresh dockview panel

---

## Mental Model Schema Migrations

**Queued:** 2026-03-14  
**Status:** Idea  

The model lifecycle is currently binary: install or full uninstall. Uninstall is blocked when user data (ABox) exists, which means once users create objects of a model's types, the model author cannot update TBox (ontology) or RBox (shapes, rules, views) without the user deleting all their data first.

**The problem this causes:**
- Adding `sh:description` or `editHelpText` to shapes requires manual SPARQL graph surgery
- Adding a new optional property to an existing class has no safe path
- Reordering form fields, changing groups, updating view definitions — all blocked
- Model authors have no iteration loop once a model is in use

**What's needed — Alembic-style migrations for RDF models:**
- **Versioned migration files** per model describing forward (and ideally reverse) schema transformations
- **Safe RBox refresh**: CLEAR + rewrite shapes/views/rules graphs without touching registry or ABox (covers ~90% of real iteration — field descriptions, form layout, validation rules)
- **TBox additions**: New classes, new optional properties on existing classes — append-only, no ABox impact
- **TBox modifications**: Rename property path, change datatype, deprecate field — need transformation logic to update existing triples
- **Version tracking**: Model registry stores current schema version; migrations run forward from current to target

**Minimum viable fix:** A `refresh_artifacts` endpoint that CLEARs and rewrites individual artifact graphs (shapes, views, rules) from the model's files on disk — no registry change, no ABox impact. This was done manually via SPARQL to unblock `editHelpText` deployment.

**Context:** Discovered during M004 when `sh:description` and `editHelpText` additions to `basic-pkm.jsonld` couldn't reach the triplestore through normal install/uninstall.

---

## Ontology Viewer & Gist Upper Ontology

**Queued:** 2026-03-12  
**Status:** ✅ Done (M003) — TBox/RBox viewer, gist 14.0.0, class creation all shipped

---

## UI Polish & Consistency Fixes

**Queued:** 2026-03-15  
**Status:** Pending  

Small styling and UX inconsistencies found during M006 review:

1. **Inference button sizing on Mental Models page** — The "Inference" button (`btn-warning btn-sm`) on the models table is visually larger/more prominent than "Refresh" and "Remove" beside it. Normalize sizing.

2. **Ontology Viewer button color** — "Open Ontology Viewer" button on Mental Models page uses default/neutral styling (`upper-ontology-btn`). Should be blue (accent/primary) to indicate primary action.

3. **Relationships graph layout** — Cytoscape relationship diagram on model detail page is constrained width. Should take full width of content area. Layout should default to horizontal flow (left-to-right) rather than the default Cytoscape layout, since ontology hierarchies read better horizontally.

4. **Explorer chevron inconsistency** — Left sidebar explorer sections use Unicode triangles (`&#9656;`) while right sidebar sections (Relations, Lint, Comments) use Lucide `chevron-right` icons. Update left side to match right side's Lucide chevrons.

5. **OBJECTS header actions always visible** — Refresh (↻) and plus (+) buttons on the OBJECTS section header have `opacity: 0` by default, only visible on hover. These should always be visible — they're primary navigation actions, not overflow options.

6. **Dashboard/Workflow explorer: plus-sign pattern instead of "New" buttons** — DASHBOARDS and WORKFLOWS explorer sections use a tree-leaf "New Dashboard" / "New Workflow" button at the bottom of the list. Should match the OBJECTS pattern: a `+` button in the section header (always visible). Remove the "New Dashboard" / "New Workflow" tree-leaf action entries.

**Files involved:**
- `backend/app/templates/admin/models.html` — buttons #1, #2
- `frontend/static/css/style.css` — button styling #1, #2
- `backend/app/admin/router.py` — Cytoscape layout config #3
- `backend/app/templates/browser/workspace.html` — chevrons #4, header actions #5, dashboard/workflow headers #6
- `frontend/static/css/workspace.css` — chevron styles #4, action visibility #5
- `backend/app/templates/browser/dashboard_explorer.html` — remove "New Dashboard" leaf #6
- `backend/app/templates/browser/workflow_explorer.html` — remove "New Workflow" leaf #6

---

## Dashboard & Workflow User Guide Documentation

**Queued:** 2026-03-15  
**Status:** Pending  

M006 shipped dashboards and workflows but no user guide documentation was written. Need new guide pages covering:

- **Dashboards:** What they are, creating via builder (layout picker, block types, block configuration), opening dashboards, cross-view context filtering (how row selection in one block filters another), editing and deleting dashboards
- **Workflows:** What they are, creating via builder (step types, step configuration), running workflows (stepper UI, prev/next navigation, context passing), editing and deleting workflows
- **Explorer sections:** DASHBOARDS and WORKFLOWS sections in the sidebar, how they auto-refresh

Should be new guide page(s) — likely `docs/guide/28-dashboards-and-workflows.md` or split into two pages.

**Relevant code for reference:**
- `backend/app/templates/browser/dashboard_builder.html` — builder UI
- `backend/app/templates/browser/dashboard_page.html` — rendering
- `backend/app/templates/browser/workflow_builder.html` — builder UI  
- `backend/app/templates/browser/workflow_runner.html` — runner UI
- `.gsd/milestones/M006/slices/S03/S03-SUMMARY.md` through `S07-SUMMARY.md` — feature details

---

## Spatial Canvas — Resizable Nodes, Property Flip & Live Embeds

**Queued:** 2026-03-15
**Status:** Queued as M008 (depends on M007)

Transform the spatial canvas from a graph exploration surface into a composable working surface:

1. **Resizable nodes** — Free drag handles on corners/edges. Width and height stored per-node, persisted across sessions. Old sessions gracefully default to 260px.

2. **Property flip** — Button on object node header toggles between markdown body and SHACL-derived properties table. Compact label/value table rendered inline (no iframe needed).

3. **Live embeds** — Place Views, Dashboards, SPARQL query results, and object read views on the canvas as resizable iframes with full interactivity (clickable rows, context filtering). `?embed=1` mode suppresses page chrome.

4. **Embed add UX** — Toolbar picker (button → dropdown → select → place) and drag-from-explorer (extending existing DnD infrastructure).

**Requirements:** CANVAS-01 through CANVAS-05
**Context:** `.gsd/milestones/M008/M008-CONTEXT.md`
**Depends on:** M007 (generic views must exist to be embeddable)

---

## App Platform

**Queued:** 2026-03-16
**Status:** Queued as M009

Sandboxed app platform enabling third-party and first-party Python applications to extend SemPKM with custom UI, background tasks, external API integrations, and object renderer overrides. Apps run as isolated subprocesses communicating via HTTP-over-unix-socket IPC.

Key subsystems:
1. **AppManifest validation** — Pydantic schema for manifest.yaml (identity, dependencies, permissions, backend, tasks, frontend, UI integration, settings)
2. **Subprocess lifecycle** — Per-app venv, process supervision, crash recovery, auto-start
3. **App SDK** — `sempkm-app-sdk` in-repo package with CommandClient, GraphClient, StateClient, HttpClient, SettingsClient
4. **3-level frontend integration** — Standalone pages, workspace contributions (right pane, views, command palette), object renderer overrides
5. **Platform-owned scheduler** — Trigger app tasks on interval, concurrency guard, retry policy
6. **Permission enforcement** — Command whitelist, IRI prefix, network domain restriction, JWT scoping
7. **Admin monitoring** — App list/detail pages, task history, logs, renderer assignments
8. **Bulk EventStore** — `commit_bulk()` with summary metadata for batch ingestion
9. **browserVisible** field on Mental Model types

**Design:** `.gsd/design/APP-PLATFORM-DESIGN.md`
**Context:** `.gsd/milestones/M009/M009-CONTEXT.md`

---

## RSS Reader & Hypothesis App

**Queued:** 2026-03-16
**Status:** Queued as M010 (depends on M009)

First app built on the app platform. RSS/Atom feed reader with Hypothesis annotation sync — subscribe to feeds, read articles in a clean reader interface, sync annotations, store everything as first-class RDF objects.

Key components:
1. **Mental Models** — `rss-feeds` (FeedSubscription, Article, ReadActivity) and `web-annotations` (Annotation, TextQuoteSelector)
2. **Feed service** — Parsing (feedparser), content extraction (trafilatura), feed discovery (feedfinder2), OPML import
3. **Hypothesis service** — API client, cursor-based annotation sync, W3C Web Annotation mapping
4. **Reader UI** — Split-pane reader interface with feed sidebar, article list, reading pane
5. **Frontend integration** — All 3 levels: standalone page, workspace contributions (3 views, right pane, 3 command palette entries), custom object renderers (Article, Annotation)

**Research:** `docs/research/rss-reader-hypothesis-integration.md`
**Design:** `.gsd/design/APP-PLATFORM-DESIGN.md` §13
**Context:** `.gsd/milestones/M010/M010-CONTEXT.md`
**Depends on:** M009 (app platform must exist)

---

## Mental Models Expansion

**Queued:** 2026-03-16
**Status:** Queued as M011

Expand Mental Model lineup to 6 user-facing models: basic-pkm v2 (Task + Milestone + Event integration hub), Personal CRM (Contact, Company, Interaction, Deal), Zettelkasten+ (5-type provenance chain), Research Workflow (claims-first academic PKM). Each with full OWL ontology, SHACL shapes, ViewSpecs, SHACL-AF rules, seed data, pre-built dashboards, and icon manifests.

**Design:** `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md`
**Context:** `.gsd/milestones/M011/M011-CONTEXT.md`

---

## Workspace & Event Log Polish

**Queued:** 2026-03-16
**Status:** Queued as M012

Event log autocomplete and helptext (matching SHACL form quality), body.diff incremental storage for readable change history, and user personas (named workspace layouts + settings per context).

**Context:** `.gsd/milestones/M012/M012-CONTEXT.md`

---

## API Surface for External Clients

**Queued:** 2026-03-16
**Status:** Queued as M013 (depends on M011)

Four new JSON API endpoints for external clients: `/.well-known/sempkm` (discovery), `/api/types` (available types), `/api/shapes/{type}` (SHACL shapes as JSON), `/api/context-query` (related objects by page metadata). Needed by browser extension and useful standalone.

**Context:** `.gsd/milestones/M013/M013-CONTEXT.md`
**Depends on:** M011

---

## Browser Extension Phase 1 — Smart Structured Capture

**Queued:** 2026-03-16
**Status:** Queued as M014 (depends on M013)

Chrome/Firefox extension with popup capture UI, dynamic SHACL-driven forms, type selector, auto-population from page metadata and schema.org, relationship picker, context menu integration.

**Design:** `.gsd/design/BROWSER-EXTENSION-DESIGN.md`
**Context:** `.gsd/milestones/M014/M014-CONTEXT.md`
**Depends on:** M013

---

## Browser Extension Phase 2 — Knowledge Context Overlay

**Queued:** 2026-03-16
**Status:** Queued as M015 (depends on M014)

Sidebar showing related objects from your graph while browsing. Badge count, context matching (URL + title keywords), in-context actions (link, add evidence). First tool to make browsing a bidirectional conversation with your knowledge.

**Design:** `.gsd/design/BROWSER-EXTENSION-DESIGN.md`
**Context:** `.gsd/milestones/M015/M015-CONTEXT.md`
**Depends on:** M014

---

## Linear Sync App

**Queued:** 2026-03-16
**Status:** Queued as M016 (depends on M009)

First task provider integration. Bidirectional Linear ↔ bpkm:Task sync. Establishes the sync pattern for all subsequent provider apps. Best API quality (rich webhooks, state.type enum, GraphQL, delta sync).

**Design:** `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md`
**Context:** `.gsd/milestones/M016/M016-CONTEXT.md`
**Depends on:** M009

---

## GitHub Issues Sync App

**Queued:** 2026-03-16
**Status:** Queued as M017 (depends on M009)

GitHub Issues + PRs bidirectional sync. Developer audience. Maps issues to bpkm:Task, PRs linked via edges, cross-repo dependency visualization.

**Context:** `.gsd/milestones/M017/M017-CONTEXT.md`
**Depends on:** M009

---

## Google Calendar Sync App

**Queued:** 2026-03-16
**Status:** Queued as M018 (depends on M009, M011)

First calendar provider. Google Calendar ↔ bpkm:Event sync with syncToken incremental sync, push notifications, attendee→Person matching, RRULE recurrence handling.

**Design:** `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md`
**Context:** `.gsd/milestones/M018/M018-CONTEXT.md`
**Depends on:** M009, M011

---

## Todoist Sync App

**Queued:** 2026-03-16
**Status:** Queued as M019 (depends on M009)

Todoist bidirectional sync. Simple REST API, individual user focus. Quick build leveraging M016 patterns.

**Context:** `.gsd/milestones/M019/M019-CONTEXT.md`
**Depends on:** M009

---

## Outlook Calendar Sync App

**Queued:** 2026-03-16
**Status:** Queued as M020 (depends on M009, M011)

Microsoft Graph API calendar sync. Delta queries, webhook subscriptions, recurrence pattern→RRULE conversion. Enterprise/Microsoft 365 users.

**Design:** `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md`
**Context:** `.gsd/milestones/M020/M020-CONTEXT.md`
**Depends on:** M009, M011

---

## CalDAV Calendar Sync App

**Queued:** 2026-03-16
**Status:** Queued as M021 (depends on M009, M011)

Standards-compliant CalDAV sync covering Fastmail, Nextcloud, Synology, and any CalDAV server. Native iCalendar format — cleanest field mapping.

**Context:** `.gsd/milestones/M021/M021-CONTEXT.md`
**Depends on:** M009, M011

---

## Asana Sync App

**Queued:** 2026-03-16
**Status:** Queued as M022 (depends on M009)

Asana bidirectional sync with configurable field mapping for custom-field-based status/priority. Section-based Kanban mapping. Establishes "configurable mapping" pattern.

**Design:** `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md`
**Context:** `.gsd/milestones/M022/M022-CONTEXT.md`
**Depends on:** M009

---

## Jira Sync App

**Queued:** 2026-03-16
**Status:** Queued as M023 (depends on M009)

Jira Cloud sync with ADF↔Markdown conversion, statusCategory normalization, JQL filtering, Epic→Milestone mapping. Most complex task provider.

**Design:** `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md`
**Context:** `.gsd/milestones/M023/M023-CONTEXT.md`
**Depends on:** M009

---

## Monday.com Sync App

**Queued:** 2026-03-16
**Status:** Queued as M024 (depends on M009)

Monday.com sync with LoopGuard for webhook echo prevention. Column-centric model requires user-configurable mapping. Lowest priority task provider.

**Design:** `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md`
**Context:** `.gsd/milestones/M024/M024-CONTEXT.md`
**Depends on:** M009

---

## Hosted Demo Instance

**Queued:** 2026-03-16
**Status:** Queued as M025 (depends on M011)

Pre-populated public SemPKM instance with all Mental Models, 30-50 interconnected sample objects, optimized guided tour, and pre-built demo dashboard. Removes the Docker barrier for first-time visitors.

**Context:** `.gsd/milestones/M025/M025-CONTEXT.md`
**Depends on:** M011

---

## Homepage & Messaging Rewrite

**Queued:** 2026-03-16
**Status:** Queued as M026 (depends on M025)

Outcome-focused homepage rewrite. Lead with "Structure that enforces itself" not "RDF/SHACL/SPARQL." Persona paths (Obsidian, Notion, Fresh Start), competitive positioning, demo CTA.

**Design:** `.gsd/design/USER-CONVERSION-STRATEGY.md`
**Context:** `.gsd/milestones/M026/M026-CONTEXT.md`
**Depends on:** M025

---

## Notion Import Wizard

**Queued:** 2026-03-16
**Status:** Queued as M027 (depends on M011)
**Supersedes:** Previous "Notion Import Wizard" queue entry (status: Researched)

Interactive import for Notion workspace exports. ZIP first, API later. Databases→types, rows→objects, relations→edges. Mirrors Obsidian import pattern.

**Research:** `.planning/notion-import-research.md`
**Context:** `.gsd/milestones/M027/M027-CONTEXT.md`
**Depends on:** M011

---

## Browser Extension Phase 3 — Active Intelligence

**Queued:** 2026-03-16
**Status:** Queued as M028 (depends on M015)

AI-powered extension features: claim detection on web pages, contradiction surfacing against existing knowledge, knowledge gap alerts, relationship suggestions, personalized summaries using graph context. Uses SemPKM's LLM proxy.

**Design:** `.gsd/design/BROWSER-EXTENSION-DESIGN.md`
**Context:** `.gsd/milestones/M028/M028-CONTEXT.md`
**Depends on:** M015

---

## Frontend Performance & Build Pipeline

**Queued:** 2026-03-17
**Status:** Queued as M029

Measurable frontend performance improvement cycle: Lighthouse/WebPageTest audit baseline, full build pipeline (esbuild or Vite) for bundling/minification/content-hashing, local vendoring of all 18 CDN JS/CSS dependencies, gzip/brotli compression in nginx, proper HTTP caching with immutable hashed assets, CSS code-splitting by route, backend response profiling with ETag/conditional GET support, and QUIC/HTTP/3 research with implementation if low-cost.

Key problems addressed:
1. **18 CDN dependencies** on every page load (htmx, Cytoscape×5, marked, highlight.js, DOMPurify, Lucide, Split.js, Driver.js, dockview-core)
2. **Zero compression** — nginx serves uncompressed 160KB CSS and 12K-line JS
3. **No caching** — `no-store, no-cache` on all static assets
4. **No minification** — raw source files served directly
5. **No build pipeline** — no bundler, no tree-shaking, no content-hashed filenames
6. **All CSS loaded everywhere** — workspace CSS loaded on admin pages

**Context:** `.gsd/milestones/M029/M029-CONTEXT.md`

---

## Data Quality Linting & Lint UX

**Queued:** 2026-03-17
**Status:** Queued as M030

Three-part milestone: (1) Fix the production validation pipeline — `model_shapes_loader` currently loads only shapes graphs, not rules graphs, and `ValidationService` doesn't pass `advanced=True` to pyshacl, so all 11 existing SHACL-AF validation rules from M011 are inert in the live app. (2) Add 9 data quality rules across all 5 Mental Models targeting real-world data problems: comma-in-tags (Warning), empty body (Info), duplicate URLs on same type (Info), titleless objects (Warning), orphan objects (Info), stale projects/goals (Info), PPV broken chain (Warning), concept with no definition (Info), research claim with no rationale (Info). (3) Build a lint filter/dismiss system with rule-type suppression, per-object dismissal, named filter presets, and a settings UI for managing suppressions.

**Context:** `.gsd/milestones/M030/M030-CONTEXT.md`
**Key discovery:** Production `ValidationService` only loads `:shapes` graphs and omits `advanced=True` — all M011 SPARQLConstraint rules (overdue tasks, stale contacts, etc.) are silently broken in the live app.

---

## Views Overhaul, Saved Queries as First-Class, & UI Polish

**Queued:** 2026-03-20
**Status:** Queued as M031

Overhaul the views system: remove the redundant carousel view picker (user already chose via sidebar), add saved query scoping to all views, support multiple ephemeral view instances that can be saved as named views, add a new kanban renderer (status-based with drag-drop), and fix full-height layout + graph tooltip z-index.

Make saved queries prominent throughout: explorer sidebar, VFS browser, spatial canvas, view toolbar scope dropdown, and object browser dropdown.

SPARQL console polish: graph visualization of results, clickable object links in table, `urn:sempkm:model:*` prefix shortening.

Ontology viewer: property description tooltips in TBox detail, full-size model relationship graph with edge tooltips (domain, range, description).

Dashboard/workflow UX: contextual help text, autocomplete for type/object fields, simplified workflow view step (remove Renderer dropdown — views know their own renderer), sample dashboards and workflows in seed data.

**Context:** `.gsd/milestones/M031/M031-CONTEXT.md`

---

## Block-Based Custom UI Builder (Research & Design)

**Queued:** 2026-03-20
**Status:** Queued as M032 (depends on M031)

Research and design for a Notion/Zabbix-inspired block composition system. Users build custom dashboards, views, and multi-object creation forms by arranging reusable widget blocks. Research covers: RDF data model for block layouts, widget type registry and config schemas, layout engine approach (linear blocks vs. 2D grid), and custom SHACL-form blocks for multi-object creation workflows.

Deliverables: research document (Notion/Zabbix survey), design document (RDF data model, widget registry, form semantics), proof-of-concept (minimal block editor with 2-3 widget types), and widget inventory with config schemas.

**Context:** `.gsd/milestones/M032/M032-CONTEXT.md`
**Depends on:** M031

---

## Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul

**Queued:** 2026-03-21
**Status:** Queued as M033

Seven feature areas in one mega-milestone:

1. **Federated SPARQL with mirrored triples** — SERVICE clause pass-through to RDF4J, cache-and-mirror layer storing federated results in `urn:sempkm:mirrored` named graph (pattern from inferred triples), configurable endpoint allowlist (Wikidata, MusicBrainz, DBpedia), provenance tracking, SPARQL console SERVICE assistance. Backend federation proxy service mediates between SemPKM's scoping layer and RDF4J's native federation.

2. **Isometric 2.5D graph view** — New "Isometric" layout in Cytoscape.js layout registry using CSS 3D transforms (perspective, rotateX, translateZ). Configurable z-layer dimension: provenance source, rdf:type, dcterms:created, source model. Translucent layer planes, cross-layer edges, billboard labels.

3. **Calendar view** — FullCalendar 6.x vendored and lazy-loaded. New generic view alongside Table/Cards/Graph. SPARQL query builder for temporal data. Month/week/day views. Type filter pills. Dark mode via CSS variables. Date property auto-detection from SHACL shapes.

4. **Map view** — Leaflet.js 1.9.x + OpenStreetMap tiles vendored and lazy-loaded. New generic view. SPARQL query for schema:latitude/longitude. Marker clustering via Leaflet.markercluster. Popup with object info and click-through. Graceful tile degradation.

5. **Rich app catalog pages** — New "App Catalog" workspace section with detail pages per app (description, screenshots carousel, feature list, permissions, model dependencies, tutorial links, install/uninstall). E2E screenshot capture extended for per-app captures. Works for installed and available-but-not-installed apps.

6. **Graph view icon toggle** — Toolbar button switching between shape-only and Lucide SVG icon-on-node display. Reads from existing `window._sempkmIcons`. localStorage persistence per view.

7. **Deployment & onboarding implementation** — All 3 proposals from DEPLOYMENT-AND-ONBOARDING-DESIGN.md: setup wizard deployment mode step (local/domain/later), `docker-compose.cloud.yml` with Caddy for automatic HTTPS, mkcert for local TLS. BASE_NAMESPACE auto-configuration, instance config persistence, guard rails against namespace changes after data creation.

**Context:** `.gsd/milestones/M033/M033-CONTEXT.md`
**Design ref:** `.gsd/design/DEPLOYMENT-AND-ONBOARDING-DESIGN.md`
**Key decisions (pending):** Lib choices (FullCalendar, Leaflet+OSM), 2.5D CSS approach (not WebGL), cache-and-mirror (not pass-through federation)

---

## Task Planning, Time-Blocking & Calendar UX

**Queued:** 2026-03-21
**Status:** Queued as M034 (depends on M033)

Full task planning workflow: time-blocking fields on bpkm:Task (scheduledStart/scheduledEnd), interactive editable FullCalendar (drag, resize, click-to-create, external drag from kanban), custom open-source timeline/Gantt renderer with dependency arrows, recurring tasks with RRULE, task templates, PPV weekly/monthly/quarterly/yearly review workflows using existing WorkflowSpec runner, and composable planning surfaces (calendar + kanban side by side sharing saved query scope).

Data model additions: bpkm:scheduledStart, bpkm:scheduledEnd, bpkm:estimatedDuration, bpkm:recurrenceRule on Task. Leverages existing ppv:doDate concept ("when to DO it" vs "when it's DUE").

Key technical decisions: custom timeline renderer (vis-timeline MIT or SVG) instead of FullCalendar Premium ($480 license); RRULE expansion at query time without creating phantom objects; cross-dockview drag with stopPropagation() pattern.

**Context:** `.gsd/milestones/M034/M034-CONTEXT.md`
**Depends on:** M033 (calendar view renderer)

---

## AI Copilot & LLM Test Harness

**Queued:** 2026-03-21
**Status:** Queued as M035 (depends on M033)

Workspace AI Copilot in the existing "AI COPILOT" bottom panel placeholder: graph-aware chat with SPARQL generation and execution (with approval controls), writing assistance referencing existing objects, configurable personas (Research Assistant, Project Manager, Writing Coach) with system prompt templates, automatic graph context injection (1-hop/2-hop neighborhood serialized as readable text), object creation from chat, and conversation persistence in SQLite.

3-tier LLM test harness: (1) Mock LLM server for CI — deterministic canned responses, <5s, $0; (2) Local Ollama in Docker — llama3.2:1b on CPU for prompt quality evaluation, <60s, $0; (3) Cloud provider with budget caps — OpenAI/Anthropic with per-run token counting and configurable cost limits (default $1.00/run).

M028 AI endpoints (ai.py, 6 endpoints) recovered and on disk but not wired into main.py — this milestone wires and extends them.

**Context:** `.gsd/milestones/M035/M035-CONTEXT.md`
**Depends on:** M033 (M028 AI endpoints need to be operational first)

---

## Business Planning Mental Models & Custom Renderers

**Queued:** 2026-03-22
**Status:** Queued as M036 (depends on M033)

Comprehensive library of business planning and strategic decision-making frameworks as Mental Models with custom visual renderers. Core frameworks with dedicated renderers: Eisenhower Matrix (2×2 quadrant with drag-to-reclassify), Business Model Canvas (9-box poster layout), SWOT Analysis (2×2 quadrant), OKR Framework (progress bars), Decision Matrix (weighted-score table). Extended library using existing table/kanban/graph views: Porter's Five Forces, Value Chain, Lean Canvas, BCG Matrix, Ansoff Matrix, PESTLE, Balanced Scorecard, RACI Matrix, Stakeholder Map, Risk Matrix, and more. All stored as typed RDF for AI copilot queryability. Custom renderers registered via existing register_renderer() pattern from M033.

**Context:** `.gsd/milestones/M036/M036-CONTEXT.md`
**Depends on:** M033

---

## User Context & Mobile App

**Queued:** 2026-03-22
**Status:** Queued as M037 (depends on M033)

Native mobile app (React Native, iOS + Android) acting as a real-time context provider for SemPKM. Background GPS geofencing for location zones (home/work/custom), activity detection (stationary/walking/driving), time-of-day classification, device calendar integration for current event context. Backend Context API (POST/GET/SSE stream) with SQLite ephemeral storage. Automatic persona switching via rules engine (if location=office AND time=workHours then persona=ProjectManager). Context-filtered push notifications via FCM/APNs. Workspace context indicator showing real-time detected state.

**Context:** `.gsd/milestones/M037/M037-CONTEXT.md`
**Depends on:** M033

---

## Personal Media Scheduler App

**Queued:** 2026-03-22
**Status:** Queued as M038 (depends on M037)

SemPKM platform app managing a personalized daily media queue. Integrates podcast RSS feeds (reuses M010 feedparser), YouTube Data API v3, and Spotify Web API. Context-driven schedule rules: "when commuting play podcasts", "at noon play YouTube news", "when focus-mode play lo-fi music", "at 4:30pm play wind-down playlist". Daily plan auto-generated and adapts in real-time to context changes from M037. Mobile app (M037) displays current suggestion with playback controls/deep links. Mental Model with MediaSource, MediaItem, MediaScheduleRule, DailyMediaPlan, MediaCategory types.

**Context:** `.gsd/milestones/M038/M038-CONTEXT.md`
**Depends on:** M037 (User Context)

---

## RDF Data Import & API Documentation Cleanup

**Queued:** 2026-03-22
**Status:** Queued as M039 (depends on M033)

Workspace UI for importing structured RDF data (JSON-LD, Turtle, N-Triples) with SHACL validation preview and event-sourced object creation. Upload or paste RDF content, see parse results and SHACL warnings per subject, selectively import as event-sourced objects with full provenance. Two-pass import (objects then edges) following the Obsidian/Notion importer pattern. Plus: Redoc/OpenAPI tag cleanup — 84 routes across 10 routers currently under "default" properly categorized with descriptive tags (commands, sparql, validation, health, admin, inference, lint, app-management).

**Context:** `.gsd/milestones/M039/M039-CONTEXT.md`
**Depends on:** M033

---

## Cleanup — Documentation, UI Fixes & Bug Squashing

**Queued:** 2026-03-23
**Status:** Queued as M040 (depends on M034)

Catch-all milestone for accumulated documentation gaps, UI polish issues, and bugs found during app review. Initial slice: user guide documentation for all M034 features (editable calendar, timeline/Gantt, recurring tasks, task templates, review workflows, cross-view drag, composable planning) — 7 user-visible features shipped with zero guide chapters. Additional slices to be added as issues are discovered.

**Process fix:** M034's validation flagged ❌ on "User guide docs for new features" but no remediation was created. This milestone ensures validation findings produce actionable follow-up.

**Context:** `.gsd/milestones/M040/M040-CONTEXT.md`
**Depends on:** M034

---

## Code Quality Audit — Backend & Frontend

**Queued:** 2026-03-23
**Status:** Queued as M041

Systematic code quality audit of the core SemPKM platform producing a prioritized recommendation report. Covers backend Python (60k LOC, 233 modules), frontend JS (19k LOC, 28 files), CSS (20k LOC, 16 files), and 165 Jinja2 templates. Examines readability, module structure, logging, error handling, type safety, SPARQL construction, CSS architecture, JS structure, test gaps, duplication, dead code, and tech debt. Each recommendation categorized, severity-rated, effort-estimated, and file-anchored. No code changes — report feeds a subsequent execution milestone.

**Context:** `.gsd/milestones/M041/M041-CONTEXT.md`
**Depends on:** None (can run immediately)

---

## Security Audit — OWASP Web Security & Backend Hardening

**Queued:** 2026-03-23
**Status:** Queued as M042

Systematic security audit against OWASP Top 10 2021 (A01–A10) plus backend hardening and infrastructure security review. Covers the full attack surface: SPARQL injection via f-string construction in 24 modules, zero HTTP security headers in nginx (no CSP, X-Frame-Options, HSTS), CORS wildcard on all API routes, no CSRF protection, shell/debug endpoint exposure, federation auth gaps, cookie/session management, API token lifecycle, Docker security, and Fernet key management. Each finding mapped to OWASP category with severity, exploit scenario, affected files, and remediation guidance. Report only — no fixes. Feeds a subsequent remediation milestone.

**Context:** `.gsd/milestones/M042/M042-CONTEXT.md`
**Depends on:** None (can run immediately)

---

## E2E Test Suite Remediation

**Queued:** 2026-03-27
**Status:** Ready
**Priority:** High — 62 of 331 core tests failing, many pre-existing since M029

### Context

Full E2E run on 2026-03-27 after fixing the critical htmx/vendor.js loading issue (test compose used raw nginx instead of built frontend image). Results: 262 passed, 3 flaky, 62 failed. The failures cluster into 7 distinct categories that need separate fixes.

### Category A: Auth fixture — member login failures (~15 tests)

**Symptoms:** `Magic link request did not return a token for member@test.local` or `Token has already been used`
**Affected:** admin-access-control (3), member-permissions (6), dark-mode per-user (1), debug-pages member (1), session-management (1), plus cascading from setup tests (3+)
**Root cause:** The `memberPage` fixture invites `member@test.local` then requests a magic link. When tests run close together, the invite may not complete before the login attempt. The itsdangerous same-second token collision was fixed (nonce added) but may also interact with rate limiting on the magic-link endpoint.
**Fix approach:** The auth fixture needs to cache the session token across tests in the same file rather than re-authenticating per test. Or use a test-only "create session directly" endpoint that bypasses magic link entirely for E2E environments.

### Category B: App platform — sync apps not starting (~10 tests)

**Symptoms:** `#connect-content` not visible after 60s, status badge never shows "running"
**Affected:** linear-sync, github-sync, jira-sync, monday-sync, todoist-sync, caldav-calendar, asana-sync, app-platform lifecycle
**Root cause:** The app platform starts apps as subprocesses with their own Python venvs. In the test Docker container, the apps directory is mounted read-only (`./apps:/app/apps:ro`) and the SDK is at `./backend/sdk:/app/backend/sdk:ro`. The apps need writable venvs — the `ro` mount prevents pip install of the SDK. The app processes likely crash on startup with import errors.
**Fix approach:** Either (1) make the apps volume writable in test compose, (2) pre-build app venvs in the Docker image, or (3) add the SDK to the API container's Python path so apps inherit it. Check `docker compose -f docker-compose.test.yml exec api cat /app/data/apps/*/stderr.log` for the actual errors.

### Category C: Ontology viewer / class creation — duplicate testid (~6 tests)

**Symptoms:** `strict mode violation: locator '[data-testid="tbox-tree"]' resolved to 2 elements`
**Affected:** ontology-viewer (3 tests: TBox, ABox, RBox tabs), class-creation (3 tests)
**Root cause:** The ontology viewer opens in a dockview tab. When the tab is opened twice (e.g., from a previous test that didn't close it), two instances of the same panel exist in the DOM with identical `data-testid` attributes. Playwright strict mode rejects ambiguous locators.
**Fix approach:** Tests should scope locators to the active dockview panel (`.dv-view:not(.dv-hidden)`) or use `.first()` on the locator. Alternatively, ensure each test closes the ontology tab before opening a new one.

### Category D: Copilot — bottom panel click intercepted (~5 tests)

**Symptoms:** `<div class="editor-empty">` or `<html>` intercepts pointer events on the AI COPILOT tab button
**Affected:** All 5 copilot tests (basic chat, SPARQL approval, persistence, personas, object creation)
**Root cause:** The bottom panel tab buttons sit behind the editor-empty overlay in z-index stacking. When no object is open, the `.editor-empty` div covers the bottom panel tabs. The copilot tab button is visible but not clickable.
**Fix approach:** Either (1) fix the CSS z-index so bottom panel tabs are always above the editor area, or (2) have the test open an object first to dismiss the empty overlay, or (3) use `{ force: true }` on the click (last resort).

### Category E: Calendar/recurring tasks — view rendering timeouts (~5 tests)

**Symptoms:** Timeout waiting for FullCalendar container or calendar events
**Affected:** calendar-view (3 tests), recurring-tasks (2 tests)
**Root cause:** FullCalendar loads via CDN lazy-load pattern (script tag in template). The CDN fetch may be slow or blocked in the Docker test environment. If the script fails to load, the calendar never initializes.
**Fix approach:** Vendor FullCalendar into the build pipeline (it's already in `frontend/build.js` as `fullcalendar.js`). Check if the calendar template is using the vendored version or still referencing a CDN.

### Category F: Setup wizard UI tests (~5 tests)

**Symptoms:** `setup.html` form elements not found or submit not working
**Affected:** setup-wizard tests 3-6 (form visibility, invalid token, valid token, post-setup status)
**Root cause:** `setup.html` is a static HTML file served by nginx. It doesn't use htmx or the vendor bundle — it has its own inline JS. The form submit uses `fetch()` to POST to `/api/setup/configure-instance` and `/api/auth/setup`. Need to check if the setup endpoint is working correctly and if the JS is finding the form elements.
**Fix approach:** Run just the setup wizard test with `--headed` to see what the page looks like. May be a simple selector mismatch or a timing issue with the fetch response.

### Category G: Miscellaneous UI interaction failures (~16 tests)

Individual failures that don't cluster into a pattern:

- **table-pagination**: 422 from bad request (test data issue)
- **markdown-rendering**: Timeout waiting for rendered markdown
- **create-edge relations panel**: Object tab not opening
- **create-object type picker**: Type picker overlay not appearing
- **edit-object multi-value ref**: Reference field save not persisting
- **keyboard Alt+N**: Type picker shortcut not firing
- **workspace layout right pane**: Details pane sections not found
- **workspace layout bottom panel**: EVENT LOG/COPILOT tabs not found
- **event-log Alt+J**: Bottom panel open shortcut not firing
- **ops-log badge text**: Expected "Model Install" got "model.install" (display format change)
- **vfs-mountspec**: 422 instead of 400 for bad strategy
- **canvas-resize UI**: Backward compat interaction test
- **tags tag-explorer**: Tag pills not visible
- **comments (3)**: Object tab not opening (comment thread tests)
- **crossfade inferred badge**: Relations panel badge not appearing
- **dm-board business-planning**: Decision matrix view not rendering
- **lint-dashboard sorting**: Sort order assertion off

**Fix approach:** Each needs individual investigation. Many may be resolved by fixing categories A-F first (auth failures cascade, z-index issues affect multiple panels). Start by re-running after the auth and z-index fixes to see which of these are truly independent.

### Recommended execution order

1. **Category A** (auth fixture) — highest ROI, unblocks ~15 tests and may resolve cascading failures in G
2. **Category D** (copilot z-index) — quick CSS fix, unblocks 5 tests
3. **Category B** (app platform) — infrastructure fix, unblocks 10 tests
4. **Category C** (ontology testid) — test-side fix, unblocks 6 tests
5. **Category E** (calendar) — check vendoring, unblocks 5 tests
6. **Category F** (setup wizard) — investigate, unblocks 5 tests
7. **Category G** (misc) — re-evaluate after A-F are done

---

## PPV Model v2 — Versioned Manifests, TBox Dashboards/Workflows & Review System

**Queued:** 2026-04-04
**Status:** Queued as M047 (depends on M046)

Two-part milestone: (1) Extend the Mental Model manifest format to support TBox dashboards, workflows, and task templates that ship as part of the model definition — not as runtime-seeded user data. (2) Expand the PPV ontology with PillarScore, GuidingPrinciples, enriched review fields, and the full review system (daily through yearly) modeled as TBox operational surfaces.

### Part 1: Versioned Model Manifests with TBox Operational Surfaces

The model archive format currently supports ontology, shapes, views, rules, and seed data. Dashboards, workflows, and task templates are conceptually TBox — they define how a model operates — but they're currently hardcoded in `backend/app/dashboard/seed.py` as runtime user data.

**Problem:** When someone installs PPV, the dashboards and workflows that make PPV a *system* don't travel with the model. They're seeded at first launch via Python code, not declared in the archive. This means they're non-portable, fragile, and conceptually wrong (ABox when they should be TBox).

**Solution:** Extend `manifest.yaml` with new entrypoints:

```yaml
manifest_version: "2.0"  # Backward-compat: v1 manifests still work
entrypoints:
  ontology: "ontology/ppv.jsonld"
  shapes: "shapes/ppv.jsonld"
  views: "views/ppv.jsonld"
  dashboards: "dashboards/ppv.jsonld"     # NEW — TBox operational surfaces
  workflows: "workflows/ppv.jsonld"       # NEW — TBox operational processes
  templates: "templates/ppv.jsonld"       # NEW — reusable creation blueprints
  seed: "seed/ppv.jsonld"
  rules: "rules/ppv.ttl"
```

Key requirements:
- **Backward compatibility:** v1 manifests (no `manifest_version` field) continue to install exactly as before. The model installer detects the version and handles both paths.
- **Install/uninstall lifecycle:** TBox dashboards/workflows are created on model install and removed on uninstall, distinct from user-created dashboards/workflows. Need a `source_model` or `is_model_tbox` flag to distinguish.
- **Refresh support:** When a model's TBox dashboards/workflows are updated (new version), the installer can refresh them without affecting user data or user-created dashboards.
- **Migration from seed.py:** The existing `seed.py` review workflows move into the PPV model archive. The seed.py "Getting Started" dashboard (non-PPV) stays as a platform seed.

### Part 2: PPV Ontology Expansion — Review System & Operational Model

**New classes:**

| Class | Purpose |
|---|---|
| `ppv:PillarScore` | Per-pillar weekly scoring (1-10) with reflection — the core weekly review mechanic |
| `ppv:GuidingPrinciples` | Values anchor (singleton per user): values, purpose, meaning, manifestation, foundational statement, guiding word |

**Enriched review fields:**

| Class | New Properties | Source (Bradley's Templates) |
|---|---|---|
| `WeeklyReview` | `wins`, `challenges`, `supportingPriorities` | Weekly template sections III, IV |
| `MonthlyReview` | `biggestWins`, `biggestChallenges`, `focusAreas` | Monthly template Planning section |
| `QuarterlyReview` | `accomplishments`, `disappointments`, `whatWorked`, `whatDidntWork`, `howToImprove` | Quarterly template Section I |
| `YearlyReview` | `intentionWord`, `yearTheme` | Yearly template Visualize section |

**New ViewSpecs:**

| View | Renderer | Purpose |
|---|---|---|
| Pillar Scores Table | table | All PillarScores with pillar, score, week |
| Action Items Kanban | kanban | Actions grouped by status — daily work view |
| Projects Kanban | kanban | Projects grouped by status |
| Action Items by Context | table | Filtered by context field — GTD context lists |

**TBox Dashboards (5 — Bradley's Alignment Zone):**

| Dashboard | Role | Cadence |
|---|---|---|
| Action Items | Daily driver — actions by priority, by context, waiting, completed today | Daily |
| Life Dashboard | Strategic context — pillars, goals, projects, weekly focus, pillar score trends | Daily |
| Projects Board | Pipeline view — projects by status (Future → Next Up → Active → On Hold → Completed) | Weekly |
| Goals Overview | Strategic view — value goals by pillar, goal outcomes with progress, alignment checks | Monthly |
| Review Hub | Meta-dashboard — recent reviews, review schedule, launch points | All cadences |

**TBox Workflows (5 — the full review cycle):**

| Workflow | Steps | Duration |
|---|---|---|
| Daily Check-in | (1) Life Dashboard context → (2) Action Items dashboard → (3) Quick-add ActionItem form | 3-5 min |
| Weekly Review | (1) Guiding Principles dashboard → (2) Pillar Scoring form-group → (3) Work Review dashboard → (4) Life Maintenance checklist → (5) Plan Next Week dashboard + WeeklyReview form → (6) Confirm graph | 30-40 min |
| Monthly Review | (1) Weekly Rollup dashboard (this month's weeklies + pillar score trend chart) → (2) Pillar Assessment → (3) Pipeline Review dashboard → (4) Create MonthlyReview form → (5) Plan Next Month | 45-60 min |
| Quarterly Review | (1) Debrief dashboard (monthly reviews + pillar trends + accomplishments) → (2) Pipeline Audit → (3) Someday/Maybe triage → (4) Create QuarterlyReview form | 60-90 min |
| Yearly Review | (1) Year in Review dashboard (quarterly reviews + year-long charts) → (2) Reflect/Interpret/Visualize → (3) System Audit → (4) Create YearlyReview form → (5) Update GuidingPrinciples form | 2-3 hrs |

**TBox Task Template:**

| Template | Purpose |
|---|---|
| Life Maintenance Checklist | Weekly recurring: email inbox, calendar review, downloads cleanup, paper filing, event booking |

### Source Material

The original PPV research and templates are available at:
- **Schema Spec:** `/home/james/Documents/Vaults/PPV/System/Schema Spec.md` — the single source of truth for all property schemas, Notion provenance annotations, and query patterns
- **Review Templates:** `/home/james/Documents/Vaults/PPV/Templates/Weekly Review.md`, `Monthly Review.md`, `Quarterly Review.md`, `Yearly Review.md` — full body structure with Bases queries and checklists
- **Alignment Dashboards:** `/home/james/Documents/Vaults/PPV/Alignment/` — Action Items, Life Dashboard, Goals Overview, Projects Board, Review Hub
- **How-To Guides:** `/home/james/Documents/Vaults/PPV/System/How-To Guides/Conduct Weekly Review.md` — step-by-step review process with troubleshooting
- **System Guide:** `/home/james/Documents/Vaults/PPV/System/PPV System Guide.md` — daily/weekly/monthly/quarterly/yearly workflow descriptions
- **Guiding Principles Template:** `/home/james/Documents/Vaults/PPV/System/Guiding Principles.md` — values, purpose, meaning, manifestation, foundational statement, guiding word
- **M001 Research:** `.gsd/milestones/M001/M001-RESEARCH.md` (lines 4977-6277) — original full Turtle ontology translated from Schema Spec
- **Current PPV Model:** `models/ppv/` — shipped ontology, shapes, views, rules, seed data
- **Current Seed Workflows:** `backend/app/dashboard/seed.py` — the 5 workflows that should migrate to TBox
- **Life Plan Seed Data:** `models/ppv/seed/james-life.jsonld` — real ABox data (9 pillars, 9 value goals, 12 goal outcomes, 13 projects, 28 action items, review scaffold). Needs Career and Mental Health filled in.

### Key Design Decisions to Make During Planning

1. **Dashboard/workflow serialization format** — JSON-LD matching the existing `DashboardService.create()` / `WorkflowService.create()` parameter shape? Or a new RDF vocabulary for dashboard/workflow definitions?
2. **TBox vs user-created disambiguation** — `source_model` foreign key on dashboard/workflow rows? A `is_tbox` boolean? A separate table?
3. **Manifest version detection** — Presence of `manifest_version` field? Or feature-detect based on which entrypoint keys exist?
4. **Existing model migration** — Do all 6 existing models (basic-pkm, crm, zettelkasten, research, ppv, business-planning) get v2 manifests, or just PPV for now?
5. **What NOT to model** — Vaults (handled by other models), Habits/Routines (separate domain), Accomplishments/Disappointments (free-text fields sufficient), Daily Tracking (separate domain). The daily review is a workflow + dashboard, not a data entry event.

### What NOT to Include (Explicit Exclusions)

- **Vaults** — Intentionally excluded. SemPKM's knowledge models (basic-pkm Notes, Zettelkasten, Research) handle note-taking better than PPV's vault concept.
- **Habits & Routines database** — Separate domain. Could be its own mental model later.
- **Daily Tracking database** — Separate domain. The daily review is operational (dashboard + workflow), not a formal data entry.
- **Accomplishments/Disappointments databases** — Free-text fields on QuarterlyReview are sufficient.

**Context:** To be written at `.gsd/milestones/M047/M047-CONTEXT.md` during planning
**Depends on:** M046
