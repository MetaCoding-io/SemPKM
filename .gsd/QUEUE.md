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
