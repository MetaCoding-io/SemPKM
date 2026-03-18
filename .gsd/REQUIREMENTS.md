# Requirements

This file is the explicit capability and coverage contract for the project.

## Active
### APP-01 — App manifest validation (Pydantic schema)
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §3 AppManifest Specification, §14 Pydantic Schema
- Acceptance: `AppManifestSchema` validates all manifest fields (identity, dependencies, permissions, backend, tasks, frontend, UI, settings). Invalid manifests produce clear error messages. All field constraints from design doc enforced.

### APP-02 — Subprocess lifecycle management
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §5 Process Architecture & Sandboxing, §10 Lifecycle Management
- Acceptance: Apps install (venv creation, dep install, process start), start, stop, restart cleanly. Crash recovery restarts up to 3 times with exponential backoff. Platform shutdown sends SIGTERM to all apps. Auto-start on platform boot.

### APP-03 — App SDK (sempkm-app-sdk in-repo package)
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §6 App SDK
- Acceptance: SDK provides App class with lifecycle decorators, AppContext with scoped clients (commands, graph, state, http, settings), task handler registration, route handler registration, template rendering. SDK runner starts HTTP server on unix socket.

### APP-04 — IPC via HTTP over unix domain socket
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §5 Process Architecture & Sandboxing
- Acceptance: Platform proxies `/app/{appId}/*` to app subprocess unix socket. App-scoped JWT tokens with hourly rotation. SDK handles token renewal transparently.

### APP-05 — Permission enforcement
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §9 Permissions & Enforcement
- Acceptance: CommandClient rejects unpermitted command types. IRI prefix enforced on all created IRIs. HttpClient rejects requests to non-permitted domains. StateClient scoped to app's own state graph. Install-time permission approval dialog shown to user.

### APP-06 — Platform-owned task scheduler
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §8 Scheduler & Background Tasks
- Acceptance: AppScheduler triggers tasks via HTTP at configured intervals. Concurrency guard skips if previous run active. Retry policy with exponential backoff. User-adjustable intervals in admin. Task history recorded in SQLite.

### APP-07 — Frontend integration Level 1 (standalone pages)
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §7 Frontend Integration — Level 1
- Acceptance: App pages appear in [Apps] sidebar section. Platform renders shell (base.html); app provides content fragment via htmx. App CSS/JS loaded when app UI is active.

### APP-08 — Frontend integration Level 2 (workspace contributions)
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §7 Frontend Integration — Level 2
- Acceptance: App right-pane sections appear alongside Relations/Lint when viewing objects. App views appear in [Views] section. App command palette entries registered with ninja-keys.

### APP-09 — Frontend integration Level 3 (object renderer overrides)
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §7 Frontend Integration — Level 3
- Acceptance: Apps replace default SHACL form for specific types with custom read/edit renderers. Renderer conflict resolution (user preference > most recent install). Object tab loads app fragment instead of default template.

### APP-10 — Admin app monitoring portal
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §11 Admin Portal — App Monitoring
- Acceptance: Admin > Applications shows app list (status, version, uptime, PID, memory). App detail page shows task history, permissions, data stats, logs, renderer assignments, start/stop/restart/uninstall actions.

### APP-11 — Bulk EventStore extension
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §12 Bulk EventStore Extension
- Acceptance: `EventStore.commit_bulk()` records summary metadata (~10 triples) instead of per-operation metadata (~5N triples). SDK exposes `ctx.commands.bulk()` context manager. Batch size limit enforced (1000 ops default). All-or-nothing undo.

### APP-12 — browserVisible field on Mental Model types
- Status: active
- Class: enhancement
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §1 Design Philosophy
- Acceptance: ManifestSchema gains `browserVisible` field per type (default true). Object browser hides types with `browserVisible: false`. Hidden types remain queryable via SPARQL and linkable via edges.

### APP-13 — App database tables and migrations
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §11 Admin Portal — SQLite tables
- Acceptance: Alembic migrations create app_instances, app_task_runs, app_task_config, app_renderer_prefs, app_permissions tables. All tables populated correctly during app lifecycle.

### APP-14 — Docker and nginx integration for apps
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §15 Disk Layout
- Acceptance: docker-compose.yml mounts ./apps volume. nginx serves /app-static/{appId}/ for app assets. nginx proxies /app/{appId}/ to API. API container has pip and venv capability at runtime.

### RSS-01 — RSS/Atom feed subscription and polling
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §13, docs/research/rss-reader-hypothesis-integration.md
- Acceptance: User subscribes to RSS/Atom/JSON feeds by URL. Feeds polled at configurable interval (default 5m). New articles ingested as rss:Article objects via bulk EventStore. Feed errors tracked per-feed with error indicator.

### RSS-02 — Reader UI with split-pane layout
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Acceptance: RSS Reader standalone page shows split-pane layout: feed sidebar, article list, reading pane. Clean typography for article reading. Star toggle and mark read/unread controls.

### RSS-03 — Custom object renderers for Article and Annotation
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md)
- Design ref: §7 Level 3 object renderers
- Acceptance: Opening an rss:Article shows custom reader view (not default SHACL form). Opening an oa:Annotation shows custom annotation view.

### RSS-04 — Hypothesis annotation sync
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md), docs/research/rss-reader-hypothesis-integration.md §8
- Acceptance: User configures Hypothesis API token in settings. Annotations sync automatically (15m default). Annotations stored as oa:Annotation objects following W3C Web Annotation vocabulary. Annotations linked to matching articles via edges.

### RSS-05 — OPML import for feed subscriptions
- Status: active
- Class: enhancement
- Source: docs/research/rss-reader-hypothesis-integration.md §7
- Acceptance: User can import an OPML file to create multiple feed subscriptions at once. Feed categories preserved as tags/folders.

### RSS-06 — Workspace contributions (views, right pane, command palette)
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md) §13 manifest
- Acceptance: "Unread Articles", "Starred Articles", "Highlights" appear in Views section. "Related Articles" appears in right pane when viewing any object. "Subscribe to Feed...", "Mark All as Read", "Open RSS Reader" in command palette.

### RSS-07 — Mental Models (rss-feeds, web-annotations)
- Status: active
- Class: core-capability
- Source: design (APP-PLATFORM-DESIGN.md) §2
- Acceptance: rss-feeds model defines FeedSubscription, Article, ReadActivity with OWL, SHACL shapes, ViewSpecs. web-annotations model defines Annotation, TextQuoteSelector following W3C vocabulary. Both models installable independently of the app.

### RSS-08 — Feed content extraction and discovery
- Status: active
- Class: enhancement
- Source: docs/research/rss-reader-hypothesis-integration.md §4-5
- Acceptance: Paste a website URL → discover its RSS feed automatically. When feeds provide only summaries, extract full article content via reader mode (trafilatura). Fallback to summary when extraction fails.

### MODEL-01 — basic-pkm v2.0 with Task and Milestone types
- Status: validated
- Class: core-capability
- Source: design (MENTAL-MODELS-EXPANSION-DESIGN.md)
- Design ref: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` §1 (basic-pkm v2.0)
- Primary Slice: M011/S01
- Acceptance: basic-pkm upgraded from v1.3 to v2.0 with Task and Milestone types added alongside existing Project, Person, Note, Concept. Task has status/priority/dueDate/assignedTo with SHACL enum constraints. Milestone has status/targetDate/tasks. SHACL-AF SPARQLConstraint fires warning for overdue tasks (dueDate in past + status "todo"). Table/Cards/Graph ViewSpecs include new types. Seed data provides example tasks and milestones. Lucide icons for Task (check-square) and Milestone (flag). Model passes offline validation. Upgrade via refresh_artifacts preserves existing data.

Offline validation (S01, 10-test suite) + cross-model coexistence (S05, test_cross_model_validation.py 10 tests) + E2E Docker lifecycle (S05, mental-model-expansion.spec.ts) + user guide Chapter 29 (S05). pyshacl fires 1 Warning for overdue task. refresh_artifacts upgrade works in Docker.

### MODEL-02 — Personal CRM model
- Status: validated
- Class: core-capability
- Source: design (MENTAL-MODELS-EXPANSION-DESIGN.md)
- Design ref: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` §2 (Personal CRM)
- Primary Slice: M011/S02
- Acceptance: New crm model with Contact, Company, Interaction, Deal types. Contact extends gist:Person with phone/email/role/tags. Company extends gist:Organization with industry/website. Interaction extends gist:Event with type enum (meeting/call/email/note). Deal extends gist:Agreement with stage pipeline (lead/qualified/proposal/negotiation/closed-won/closed-lost) and value. SHACL-AF SPARQLConstraint fires warning for stale contacts (no interaction in 90 days). owl:inverseOf for worksAt/hasEmployee, hasContact/contactOf. Table/Cards ViewSpecs with pipeline view for Deals. Seed data creates realistic CRM scenario. Passes offline validation.

Offline validation (S02, 12-test suite) + cross-model coexistence (S05, test_cross_model_validation.py 10 tests) + E2E Docker lifecycle (S05, mental-model-expansion.spec.ts) + user guide Chapter 29 (S05). pyshacl fires 2 Warnings for stale contacts.

### MODEL-03 — Zettelkasten+ model
- Status: validated
- Class: core-capability
- Source: design (MENTAL-MODELS-EXPANSION-DESIGN.md)
- Design ref: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` §3 (Zettelkasten+)
- Primary Slice: M011/S03
- Acceptance: New zettelkasten model with FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote types. Enforced provenance chain: FleetingNote → Source → LiteratureNote → PermanentNote → StructureNote. Argumentation links: supports/contradicts/followsFrom between PermanentNotes. SHACL-AF SPARQLConstraint fires warning for unprocessed fleeting notes (status "unprocessed" older than 7 days). Provenance chain saved query returns Source → LiteratureNote → PermanentNote path. owl:inverseOf for all bidirectional relationships. Passes offline validation.

Offline validation (S03, acceptance tests) + cross-model coexistence (S05, test_cross_model_validation.py 10 tests) + E2E Docker lifecycle (S05, mental-model-expansion.spec.ts) + user guide Chapter 29 (S05). pyshacl fires 2 Warnings + 1 Info for unprocessed notes.

### MODEL-04 — Research Workflow model
- Status: validated
- Class: core-capability
- Source: design (MENTAL-MODELS-EXPANSION-DESIGN.md)
- Design ref: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` §4 (Research Workflow)
- Primary Slice: M011/S04
- Acceptance: New research model with Paper, Claim, Evidence, ResearchQuestion, Argument types. Claim has confidence level (established/likely/possible/speculative/contested). Evidence has evidenceType (supporting/refuting/ambiguous) and strength (strong/moderate/weak). SHACL-AF SPARQLConstraints fire warnings for unsupported claims (no evidence linked) and contested claims (has both supporting and refuting evidence). Evidence map graph view defined via CONSTRUCT query. Saved queries for unsupported claims and research gaps. Passes offline validation.

Offline validation (S04, acceptance tests) + cross-model coexistence (S05, test_cross_model_validation.py 10 tests) + E2E Docker lifecycle (S05, mental-model-expansion.spec.ts) + user guide Chapter 29 (S05). pyshacl fires 2 Warnings + 2 Info for unsupported/contested claims.


### VIEW-01 — Generic Table/Cards/Graph views that work across all types
- Status: validated
- Class: core-capability
- Source: design (VIEWS-RETHINK.md, Phase 1)
- Design ref: `.gsd/design/VIEWS-RETHINK.md` → "Generic System-Provided Views"
- Primary Slice: M007/S01
- Acceptance: 3 generic ViewSpec entries (Table View, Cards View, Graph View) appear in explorer. Opening Table View shows all objects with common columns (label, type, created, modified). No per-type ViewSpec folders in explorer tree.

3 generic ViewSpec objects registered at startup with well-known IRIs. Explorer VIEWS section shows flat entries. `GET /browser/views/generic/{renderer}` endpoints serve all objects with common columns. 32 unit tests. Browser verification confirms explorer structure and tab opening.

### VIEW-02 — SHACL-driven dynamic columns for generic views
- Status: validated
- Class: core-capability
- Source: design (VIEWS-RETHINK.md, Phase 1)
- Design ref: `.gsd/design/VIEWS-RETHINK.md` → "SHACL Column Discovery"
- Primary Slice: M007/S01
- Acceptance: When a type is selected in a generic view, columns are discovered from ShapesService (PropertyShape.path, name, order). Fallback to default columns for types with ≤2 properties. Dynamic SPARQL SELECT built from shape properties.

`get_generic_columns()` resolves PropertyShape metadata from ShapesService, falls back to defaults for sparse/missing shapes. `build_dynamic_query()` builds SPARQL SELECT with OPTIONAL per property. Unit tests cover rich shapes, sparse shapes, exception fallback, column order stability.

### VIEW-03 — Type filter pills for generic views
- Status: validated
- Class: core-capability
- Source: design (VIEWS-RETHINK.md, Phase 1)
- Design ref: `.gsd/design/VIEWS-RETHINK.md` → "Type Filter Pills"
- Primary Slice: M007/S01
- Acceptance: Pills appear above generic view content, populated from ShapesService.get_types(). "All Types" default. Clicking a pill filters the view and changes columns. Selection persists in localStorage.

`type_filter_pills.html` partial renders pills from ShapesService.get_types(). htmx hx-get filters view. localStorage key `sempkm_generic_type_{renderer}` persists selection. "All Types" pill resets to default columns.

### VIEW-04 — Explorer tree consolidation with Saved Views folder
- Status: validated
- Class: core-capability
- Source: design (VIEWS-RETHINK.md, Phase 1 + Phase 2)
- Design ref: `.gsd/design/VIEWS-RETHINK.md` → "Explorer Tree Redesign"
- Primary Slice: M007/S01
- Acceptance: Explorer VIEWS section shows: Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View, and a Saved Views folder (merging MY VIEWS). No per-model/per-type folder tree.

`views_explorer.html` rewritten with 5 flat entries + Saved Views folder. MY VIEWS section removed from workspace.html. Saved Views lazy-loads from `/browser/my-views`. Browser verification: no per-model folders, no MY VIEWS section.

### VIEW-05 — Carousel tab bar shows model-declared views when type selected
- Status: validated
- Class: core-capability
- Source: design (VIEWS-RETHINK.md, Phase 1)
- Design ref: `.gsd/design/VIEWS-RETHINK.md` → "Type-Specific Views as Carousel Tabs"
- Primary Slice: M007/S01
- Acceptance: When a type filter pill is active in a generic view, the carousel tab bar appears showing model-declared view variants for that type alongside the generic renderers.

Generic endpoint builds `all_specs` from 3 generic specs + `get_view_specs_for_type(type_iri)`. Carousel renders when `all_specs|length > 1`. `switchCarouselView()` routes generic IRIs correctly.

### VFS-07 — Type filter for VFS mounts without SPARQL
- Status: validated
- Class: core-capability
- Source: design (VFS-V2-DESIGN.md, item 2)
- Design ref: `.gsd/design/VFS-V2-DESIGN.md` → "Type Filter (No SPARQL Required)"
- Primary Slice: M007/S02
- Acceptance: `sempkm:typeFilter` predicate on MountSpec accepts a list of type IRIs. build_scope_filter() adds VALUES clause. Type filter and saved query scope compose via AND. Mount form UI has type multi-select.

`type_filter: list[str] | None` on MountDefinition. `build_scope_filter()` emits `VALUES ?type { ... }` with `?iri a ?type .` binding. AND-composed with scope. Type multi-select checkbox UI in mount form with full CRUD round-trip. 6 unit tests for type_filter VALUES clause. Browser-verified.

### VFS-08 — Query IRI alignment (scopeQuery predicate with full IRI)
- Status: validated
- Class: core-capability
- Source: design (VFS-V2-DESIGN.md, item 3 + D099)
- Design ref: `.gsd/design/VFS-V2-DESIGN.md` → "Query IRI Alignment"
- Primary Slice: M007/S02
- Acceptance: `sempkm:savedQueryId` renamed to `sempkm:scopeQuery`. Values stored as full IRIs (`<urn:sempkm:query:{uuid}>`), not bare UUIDs. Migration SPARQL UPDATE renames predicate and wraps values.

`SCOPE_QUERY` constant with `sempkm:scopeQuery`. `scope_query` field stores full IRIs. Migration function in `backend/app/vfs/migrations.py`. Zero occurrences of `savedQueryId` outside migration (grep-verified). Frontend constructs/parses IRIs.

### VFS-09 — Mount preview resolves saved query scope
- Status: validated
- Class: core-capability
- Source: design (VFS-V2-DESIGN.md, item 4)
- Design ref: `.gsd/design/VFS-V2-DESIGN.md` → "Preview Improvements"
- Primary Slice: M007/S02
- Acceptance: Preview endpoint resolves saved query text via async TriplestoreClient (not SQLite). Preview results reflect saved query scope and type_filter. Stale "would require loading from SQLite" comment removed.

`build_scope_filter()` accepts optional `sync_client` for WebDAV resolution. Preview endpoint queries `urn:sempkm:queries` graph async, returns HTTP 404 on missing. TTL-cached query text. Stale SQLite comment removed. 5 unit tests.

### VFS-10 — Bidirectional path contract documentation
- Status: validated
- Class: quality-attribute
- Source: design (VFS-V2-DESIGN.md, item 5)
- Design ref: `.gsd/design/VFS-V2-DESIGN.md` → "Bidirectional Path Contract"
- Primary Slice: M007/S02
- Acceptance: Forward (IRI→path) and reverse (path→IRI) mapping documented with examples. Filename instability caveat documented. Test coverage for slug generation and collision dedup.

Path Contract section in `docs/guide/23-vfs.md` with forward/reverse mapping, collision dedup (IRI SHA-256 hash), filename instability caveat. 26 unit tests in `test_vfs_path_contract.py` (15 slugify + 11 file map).

### VFS-11 — Composable strategy chains (multi-level folders)
- Status: validated
- Class: core-capability
- Source: design (VFS-V2-DESIGN.md, item 6 + D100)
- Design ref: `.gsd/design/VFS-V2-DESIGN.md` → "Composable Strategy Chains"
- Primary Slice: M007/S03
- Acceptance: `strategy` field accepts `str | list[str]`. Chain of up to 3 strategies produces nested folders. Provider path dispatch extended to 6 segments. UI has "+" button to add levels with predefined combos.

Pipe-delimited chain storage (D120). `strategy_chain` and `is_chain` properties on MountDefinition. `_validate_strategy_chain()` enforces max 3 levels. `build_chain_narrowing_filter()` returns SPARQL WHERE fragments per strategy. Chain-aware `_resolve_mount_path()` for 5-6 segments. `StrategyFolderCollection` with cumulative scope narrowing via chain_depth/chain_folder_values. `mount_children` endpoint with depth/parent_values for chain folder expansion. Preview returns nested tree. Chain builder UI with add/remove/preset controls. 39 new unit tests + 14 browser assertions.

### VFS-12 — Filename templates for VFS mounts
- Status: validated
- Class: core-capability
- Source: design (VFS-V2-DESIGN.md, item 7)
- Design ref: `.gsd/design/VFS-V2-DESIGN.md` → "File Naming Control"
- Primary Slice: M007/S03
- Acceptance: Optional `filename_template` field on MountSpec. Variables: `{title}`, `{date}`, `{type}`, `{id}`. Template expansion in `_build_file_map_from_bindings()`. Dedup suffix still applies.

`filename_template` field on MountDefinition with SPARQL persistence in sync + async paths. Template expansion in `_build_file_map_from_bindings()` before slugification (D122). `{title}` from label, `{date}` from dcterms:created (or "undated"), `{type}` from type label or IRI local name, `{id}` from 8-char SHA-256 prefix. Unknown variables pass through as literal text. Mount form text input with variable hint. 12 new unit tests.

### CANVAS-01 — Resizable canvas nodes with free drag handles
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M008/S01
- Acceptance: User drags corner/edge of any canvas node to resize freely. Width and height stored per-node in canvas document JSON, persisted across sessions. Minimum size constraint enforced. Old sessions without width/height default to 260px.

Corner/edge/bottom resize handles on `.spatial-node` with `stopPropagation()` isolation from node drag. Grid-snapped resize with 160px/80px min constraints. `getDocument()`/`applyDocument()` serialize/restore width/height conditionally (undefined = 260px default). 11 unit tests + 2 E2E tests (Chromium + Firefox). Browser-verified resize interaction, persistence round-trip, backward compat, and edge rendering.

### CANVAS-02 — Property flip on canvas object nodes
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M008/S02
- Acceptance: Flip button on object node header toggles between markdown body and SHACL-derived properties table. Properties fetched via lightweight API endpoint. Compact label/value table rendered inline (no iframe). Flip back returns to markdown view.

`GET /api/canvas/properties?iri=<IRI>` endpoint returns SHACL-derived property JSON with resolved labels, body exclusion, inferred tagging. `build_property_list()` pure function. Flip button in node header with `is-flipped` accent state. `buildPropertyTable()` frontend renderer. `showProperties` serialized in `getDocument()`/`applyDocument()`. Memory-only `propertyCache` re-fetched on load. 26 unit tests + 8 browser assertions. Backward compatible with old sessions.

### CANVAS-03 — Live view and dashboard embeds on canvas
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M008/S03
- Acceptance: User places a ViewSpec (Table, Cards, Graph, or model-declared) or DashboardSpec on the canvas as a resizable live iframe. Iframe loads content URL with embed mode (no page chrome). Dashboard context filtering works inside the iframe. Embeds addable via toolbar picker or drag from explorer.

`?embed=1` on view, dashboard, object, and SPARQL result endpoints renders in `base_embed.html` (minimal, no sidebar). Dual-layer rendering: embed iframes in persistent DOM layer survive `renderNodes()` innerHTML rebuilds. `addEmbedNode()` with `nodeType:'embed'` and `embedConfig:{type, id, url, label}`. Max 8 embeds enforced. 32 unit tests + browser verification.

### CANVAS-04 — SPARQL query and object read embeds on canvas
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M008/S03
- Acceptance: User places a saved SPARQL query result or an object read view (full properties + body) on the canvas as a resizable live iframe. Embeds addable via toolbar picker or drag from explorer.

`GET /browser/sparql-result/{query_id}` renders saved query output as HTML table with enriched labels. `get_object(embed=1)` renders stripped-down `object_embed.html` (type label + property table + markdown body). Both load as iframes in canvas embed nodes via toolbar picker.

### CANVAS-05 — Embed add UX (toolbar picker + drag from explorer)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M008/S03
- Acceptance: Canvas toolbar has an "Add embed" button opening a picker (select content type → choose specific item → place on canvas). Views, dashboards, and queries in explorer sidebar are draggable onto canvas. Both paths produce the same embed node type.

Toolbar "Embed" button opens tabbed picker (Views/Dashboards/Queries) fetching from existing list APIs. Explorer entries in views_explorer.html, dashboard_explorer.html, and my_views.html have `draggable="true"` with `ondragstart` setting embed-type payload. Both paths call `addEmbedNode()` producing identical node types. Max 8 enforced on both paths.

### EVTLOG-01 — Predicate/type/object labels resolve to human-readable text in event log
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S01
- Acceptance: Event log detail shows human-readable predicate labels (e.g. "Title" not "dcterms:title") via ShapesService and LabelService batch resolution.

Unit tests (test_event_log_labels.py) + E2E (event-log-polish.spec.ts) + user guide (Ch 15 §Predicate Labels).

### EVTLOG-02 — Helptext tooltips on event log predicates from SHACL annotations
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S01
- Acceptance: Predicate labels in event log detail have helptext tooltips from SHACL sh:description / sempkm:editHelpText annotations, indicated by dotted underlines.

Unit tests (test_event_log_labels.py) + E2E (event-log-polish.spec.ts) + user guide (Ch 15 §Helptext Tooltips).

### EVTLOG-03 — Autocomplete for event log filter fields
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S01
- Acceptance: Event log filter fields provide autocomplete suggestions for operation types, predicates, and objects via three suggestion endpoints.

Unit tests (test_event_suggestions.py) + E2E (event-log-polish.spec.ts) + user guide (Ch 15 §Autocomplete Filters).

### BDIFF-01 — Body changes store incremental diffs instead of full replacements
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S02
- Acceptance: When editing an existing note body, the system computes and stores a unified diff (body.diff) instead of full replacement (body.set).

Unit tests (test_body_diff.py) + E2E (body-diff.spec.ts) + user guide (Ch 15 §Body Diff Events).

### BDIFF-02 — Event log renders body.diff events with addition/deletion highlighting
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S02
- Acceptance: Event log detail view renders body.diff events with green (added) and red (removed) line highlighting using unified diff format.

Unit tests (test_body_diff.py) + E2E (body-diff.spec.ts) + user guide (Ch 15 §Body Diff Events).

### BDIFF-03 — Existing body.set events continue to display correctly
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S02
- Acceptance: First-time body sets still create body.set events with full text display. Both body.set and body.diff events render correctly side-by-side in the event log.

E2E (body-diff.spec.ts test 3) + user guide (Ch 15 §Body Diff Events).

### PERSONA-01 — Named personas with CRUD (create, rename, delete)
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S03
- Acceptance: User can create named personas, rename them, and delete them. Single-active-per-user constraint enforced. Delete of active persona auto-activates another.

PersonaService with 8 async methods + 20 unit tests. 7 REST API endpoints verified via curl. Sidebar selector UI with create/save/switch actions. Browser-verified.

### PERSONA-02 — Persona switching restores dockview layout, sidebar positions, explorer mode
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S03
- Acceptance: Switching personas restores dockview layout via fromJSON(), sidebar panel positions, and explorer mode. Guard flag prevents localStorage corruption during layout restore.

switchPersona() saves current → fetches target → activates → applies layout/positions/mode. dv.fromJSON() wrapped in try/catch with toast fallback. _switchingPersona guard flag bridges IIFEs via window.*. Browser-verified.

### PERSONA-03 — Persona selector in user popover menu
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S03
- Acceptance: Persona selector appears in sidebar user popover between Layouts and theme row with active indicator, save button, and create button.

_persona_selector.html partial loaded via hx-trigger="load". Active persona shown with check-circle icon and accent color. Browser screenshot verified.

### PERSONA-04 — Persona switching via Ctrl+K command palette
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S03
- Acceptance: Command palette has "Persona: Switch To..." (with dynamic submenu), "Persona: Save Current", and "Persona: Create New..." entries.

Three command palette entries with _refreshPersonaPaletteItems() for dynamic submenu population. Browser screenshot verified showing all three commands.

### PERSONA-05 — Default persona created on first use
- Status: validated
- Class: core-capability
- Source: design (M012 roadmap)
- Primary Slice: M012/S03
- Acceptance: When user has no personas, initPersonas() auto-creates "Default" persona with current workspace state and activates it.

initPersonas() checks GET /api/personas; if empty, POSTs new "Default" with current dockview layout, sidebar positions, and explorer mode. Console log confirms. Browser-verified.

## Validated

### EXP-01 — Explorer mode dropdown with switchable navigation strategies
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S01

EXPLORER_MODES registry with by-type, hierarchy, by-tag handlers + mount: prefix dispatch in workspace.py. E2E spec: explorer-mode-switching.spec.ts.

### EXP-02 — By-type mode (current behavior) as default explorer mode
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S01

_handle_by_type() handler delegates to nav_tree.html. /browser/nav-tree kept for backwards compat.

### EXP-03 — Hierarchy mode via dcterms:isPartOf with arbitrary nesting depth
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S02

_handle_hierarchy() queries dcterms:isPartOf roots; /explorer/children for lazy expansion. Unit tests: test_hierarchy_explorer.py.

### EXP-04 — VFS mount specs visible as explorer modes
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S03

mount:{uuid} options in explorer dropdown; _handle_mount dispatches to 5 VFS strategies. E2E spec: vfs-explorer.spec.ts.

### EXP-05 — VFS explorer shows full rich objects with same click-to-open behavior
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S03

VFS mount tree leaves use same handleTreeLeafClick/openTab as by-type tree. Objects rendered with labels and type icons.

### TAG-01 — Tag parsing fix: comma-separated schema:keywords split into individual triples
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S04

split_tag_values() on save in object_patch.py; /admin/migrate-tags endpoint; seed data updated to arrays. Unit tests: test_tag_splitting.py.

### TAG-02 — Tags render as pills with # prefix in object view and properties panel
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S04

Tag pill CSS in workspace.css; tag_tree.html with # prefix. E2E spec: tag-explorer.spec.ts.

### TAG-03 — Tag explorer mode in explorer dropdown
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S04

_handle_by_tag() handler with UNION SPARQL across bpkm:tags and schema:keywords. Unit tests: test_tag_explorer.py.

### TAG-04 — Hierarchical tag tree with `/`-delimited nesting
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M005/S03

Tags with `/` delimiters render as nested tree nodes at arbitrary depth in By Tag explorer. `build_tag_tree()` pure function groups flat tag data into hierarchical nodes. `tag_children` endpoint extended with `prefix` parameter for lazy sub-folder loading. 61 unit tests (28 tree builder + 33 explorer).

### TAG-05 — Tag autocomplete in edit forms
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M005/S04

Tag input fields in edit forms offer autocomplete with existing tag values from the graph. `GET /browser/tag-suggestions?q=<prefix>` endpoint queries both `bpkm:tags` and `schema:keywords` via SPARQL UNION, returns frequency-ordered HTML suggestions (LIMIT 30). `_field.html` macro detects tag properties and renders `.tag-autocomplete-field` wrapper with htmx-driven dropdown. `addMultiValue()` cloning supports tag autocomplete fields. 22 unit tests.

### FAV-01 — Per-user favorites: star/unstar objects
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S05

UserFavorite SQL model; /favorites/toggle; star button on objects; Alembic migration 009. E2E spec: favorites.spec.ts.

### FAV-02 — FAVORITES collapsible section in explorer pane
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S05

FAVORITES section above OBJECTS in workspace.html; /favorites/list; HX-Trigger favoritesRefreshed auto-refresh.

### CMT-01 — Threaded collaborative comments on objects
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S06

sempkm:Comment RDF vocabulary; comment.create/reply/delete via EventStore; threaded via replyTo. E2E spec: comments.spec.ts.

### CMT-02 — Comment panel in object view with author attribution and timestamps
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S06

comments_section.html with author badges (batch-resolved from SQL), relative timestamps, reply forms, recursive comment_thread.html partial.

### ONTO-01 — TBox Explorer: unified class hierarchy across all installed models
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

TBox tree via /ontology/tbox with cross-graph FROM clause aggregation (gist + model + user-types). E2E spec: ontology-viewer.spec.ts confirms gist classes visible.

### ONTO-02 — ABox Browser: instances grouped by type with counts
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

ABox tab via /ontology/abox; types with instance counts > 0; drill-down via /ontology/abox/instances.

### ONTO-03 — RBox Legend: property reference with domains, ranges, and characteristics
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

RBox tab via /ontology/rbox; object + datatype properties with domains and ranges in rbox_legend.html.

### GIST-01 — Gist 14.0.0 loaded as foundation ontology in named graph
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

gistCore14.0.0.ttl bundled in backend/ontologies/gist/; loaded into urn:sempkm:ontology:gist via batched INSERT DATA. CC BY 4.0.

### GIST-02 — Mental model classes aligned to gist hierarchy
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S07

basic-pkm: Project→gist:Task, Person→gist:Person, Note→gist:FormattedContent, Concept→gist:KnowledgeConcept. ppv: Project→gist:Task.

### TYPE-01 — In-app class creation: name, icon, parent class, basic properties
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S08

"+ Create Class" button on Ontology Viewer page renders full form (name, icon picker, parent selector, property editor). POST /ontology/create-class endpoint. Verified in live browser 2026-03-13.

### TYPE-02 — Created classes generate valid OWL class + SHACL shape
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M003/S08

OntologyService.create_class() generates OWL class + SHACL NodeShape in urn:sempkm:user-types graph. Discoverable by ShapesService. Verified form + endpoint exist in live browser 2026-03-13.

### ADMIN-01 — Model detail page stats: avg connections, last modified, growth trend
- Status: validated
- Class: admin/support
- Source: execution (code TODO)
- Primary Slice: M003/S09

SPARQL-computed avg_connections, last_modified, growth_trend in model_detail.html. E2E spec: admin-model-detail.spec.ts.

### ADMIN-02 — Model detail page charts: sparkline, activity, link distribution
- Status: validated
- Class: admin/support
- Source: execution (code TODO)
- Primary Slice: M003/S09

Chart.js 4.4 CDN; growth sparkline (8-week) + link distribution (5-bucket histogram). Lazy init on flip transitionend.

### SEC-01 — Auth endpoints have per-IP rate limiting
- Status: validated
- Class: compliance/security
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

slowapi rate limiting: 5/min on magic-link, 10/min on verify. HTTP 429 after limit exceeded.

### SEC-02 — Magic link token not logged when SMTP is configured
- Status: validated
- Class: compliance/security
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

Token logging conditional on SMTP not configured or SMTP delivery failure fallback.

### SEC-03 — Event console requires owner role
- Status: validated
- Class: compliance/security
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

require_role("owner") on event_console_page in debug/router.py.

### SEC-04 — SPARQL filter text properly escaped against regex injection
- Status: validated
- Class: compliance/security
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

escape_sparql_regex() in sparql/utils.py escapes 14 metacharacters. 19 unit tests.

### SEC-05 — base_namespace deployment documented with production guidance
- Status: validated
- Class: operability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S01

Namespace Configuration section in docs/guide/20-production-deployment.md.

### COR-01 — Validation report IRI uses stable hash
- Status: validated
- Class: core-capability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S02

hashlib.sha256 in validation/report.py replaces non-deterministic hash().

### COR-02 — scope_to_current_graph handles FROM/GRAPH in string literals
- Status: validated
- Class: core-capability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S02

_strip_sparql_strings() preprocessor removes string literals before keyword detection. 6 unit tests.

### COR-03 — source_model attributed correctly with multiple models installed
- Status: validated
- Class: core-capability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S02

GRAPH ?g with VALUES clause constraining graph IRIs for per-spec model attribution.

### TEST-01 — Backend pytest infrastructure exists with conftest and fixtures
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S03

backend/tests/conftest.py with fixtures; 130 tests in <3s.

### TEST-02 — SPARQL serialization/escaping has unit tests
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S03

test_rdf_serialization.py and test_sparql_utils.py cover serialization, escaping, and scoping edge cases.

### TEST-03 — IRI validation has unit tests
- Status: validated
- Class: quality-attribute
- Source: user
- Primary Slice: M002/S03

test_iri_validation.py covers valid IRIs, invalid IRIs, injection chars, and edge cases.

### TEST-04 — Auth token logic has unit tests
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S03

test_auth_tokens.py covers creation, verification, expiry (max_age_seconds=0), setup token lifecycle.

### REF-01 — Browser router split into domain sub-routers with zero behavior change
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S04

8 sub-modules, 33 routes preserved, route audit matches pre-refactor count.

### DEP-01 — pyproject.toml dependency versions pinned
- Status: validated
- Class: operability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S05

All 24 dependencies use ~= compatible release pins.

### DEP-02 — uv.lock committed to source control
- Status: validated
- Class: operability
- Source: research (CONCERNS.md)
- Primary Slice: M002/S05

uv.lock exists and committed.

### PERF-01 — Event detail user lookup batched
- Status: validated
- Class: quality-attribute
- Source: research (CONCERNS.md)
- Primary Slice: M002/S05

Single WHERE IN query via resolve_user_names() replaces N+1 loop.

### FED-11 — Sync Now button auto-discovers remote URL from shared graph metadata
- Status: validated
- Class: core-capability
- Source: execution (Phase 58 verification gap)
- Primary Slice: M002/S06

discover_remote_instance_url() auto-resolves from federation graph metadata.

### FED-12 — Federation dual-instance docker-compose for E2E testing
- Status: validated
- Class: quality-attribute
- Source: user
- Primary Slice: M002/S06

docker-compose.federation-test.yml with two complete instances (ports 3911/3912).

### FED-13 — Federation E2E test covers invite → accept → sync flow
- Status: validated
- Class: quality-attribute
- Source: user
- Primary Slice: M002/S06

8-step Playwright E2E test in federation-sync.spec.ts passes in ~2s.

### OBSI-08 — Ideaverse Pro 2.5 vault imports successfully
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S07

895 objects created, 1767 edges, 29.9s import time from Ideaverse Pro 2.5 ZIP.

### OBSI-09 — Wiki-links in imported notes resolve to edges between objects
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S07

1767 dcterms:references edges from wiki-link resolution. Verified in Relations panel.

### OBSI-10 — Frontmatter from imported notes maps to RDF properties
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S07

Mapped keys (created, source, title, noteType) visible as RDF properties in workspace UI.

### SPARQL-01 — SPARQL queries are gated by role
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

SPARQL queries are gated by role — guest has no access, member queries current graph only, owner queries all graphs.

### SPARQL-02 — User's SPARQL query history is persisted server-side
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

User's SPARQL query history is persisted server-side and accessible across devices.

### SPARQL-03 — User can save a SPARQL query with a name and description
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

User can save a SPARQL query with a name and description.

### SPARQL-04 — User can share a saved query with other users
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S54

User can share a saved query with other users (read-only).

### SPARQL-05 — SPARQL result IRIs display as labeled pills
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

SPARQL result IRIs display as labeled pills with type icons that open in workspace tabs.

### SPARQL-06 — SPARQL editor provides ontology-aware autocomplete
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S53

SPARQL editor provides ontology-aware autocomplete for prefixes, classes, and predicates from installed models.

### SPARQL-07 — User can promote a saved query to a named view
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S54

User can promote a saved query to a named view browsable in the nav tree.

### SPARQL-08 — SPARQL is read-only (no graph modification)
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

User cannot modify the graph via SPARQL — all writes go through the Command API.

### FED-01 — Events serialized as RDF Patch format
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Events can be serialized as RDF Patch format (A/D operations).

### FED-02 — API endpoint exports event patches since sequence number
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

API endpoint exports event patches since a given sequence number.

### FED-03 — User can register a remote SemPKM instance for sync
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can register a remote SemPKM instance for sync.

### FED-04 — Named graph sync pulls patches from remote
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Named graph sync pulls patches from remote instance and applies via EventStore.

### FED-05 — Sync prevents infinite loops via syncSource tagging
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Sync prevents infinite loops via syncSource tagging on federation-originated events.

### FED-06 — Server exposes LDN inbox endpoint
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Server exposes LDN inbox endpoint discoverable via Link header on WebID profiles.

### FED-07 — User can send notification to remote LDN inbox
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can send a notification (e.g. shared concept) to a remote instance's LDN inbox.

### FED-08 — User can view and act on received LDN notifications
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

User can view and act on received LDN notifications in the workspace.

### FED-09 — Incoming federation requests authenticated via HTTP Signatures
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Incoming federation requests are authenticated via HTTP Signatures against WebID public keys.

### FED-10 — Collaboration UI shows sync status
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S58

Collaboration UI shows registered remote instances, sync status, and incoming changes.

### VFS-01 — MountSpec RDF vocabulary defines declarative directory structures
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

MountSpec RDF vocabulary defines declarative directory structures.

### VFS-02 — User can create a mount with 5 directory strategies
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

User can create a mount with one of 5 directory strategies (by-type, by-date, by-tag, by-property, flat).

### VFS-03 — VFS provider dispatches to correct strategy
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

VFS provider dispatches to the correct strategy based on mount path prefix.

### VFS-04 — YAML frontmatter edits map back to RDF via SHACL
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

Editing a file's YAML frontmatter via WebDAV maps changes back to RDF properties via SHACL shapes.

### VFS-05 — Mount management UI in Settings
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S56

Mount management UI in Settings for creating, editing, and deleting mounts.

### VFSX-01 — VFS browser side-by-side view
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser shows side-by-side view for open files with raw content and rendered markdown preview.

### VFSX-02 — VFS browser polished file operations
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser file operations are polished (consistent icons, loading states).

### VFSX-03 — VFS browser inline help
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

VFS browser has inline help about connecting the user's OS to the WebDAV endpoint.

### OBUI-01 — Nav tree refresh button
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Nav tree header has a refresh button to reload the object list.

### OBUI-02 — Nav tree plus button
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Nav tree header has a plus button to jump to the create new object flow.

### OBUI-03 — Multi-select via shift-click in nav tree
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

User can select multiple objects via shift-click in the nav tree.

### OBUI-04 — Bulk delete selected objects
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

User can bulk delete selected objects.

### OBUI-05 — Relationship edge inspector
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S55

Clicking a relationship in the Relations panel expands to show edge provenance, metadata, and type.

### FIX-01 — Event log diffs render correctly
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

Event log diffs render correctly for all operation types.

### FIX-02 — Lint dashboard controls at correct width
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S52

Lint dashboard controls display at correct width on all viewports.

### CANV-01 — Spatial canvas snap-to-grid
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas has snap-to-grid alignment.

### CANV-02 — Spatial canvas edge labels
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas shows edge labels between connected nodes.

### CANV-03 — Spatial canvas keyboard navigation
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Spatial canvas has keyboard navigation support.

### CANV-04 — Bulk drag-drop to canvas
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

User can multi-select objects in the nav tree and drag-drop them onto the canvas in bulk.

### CANV-05 — Wiki-link edges on canvas
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S57

Wiki-links in an object's markdown body are parsed and rendered as edges connecting to their target nodes on the canvas, with a different color than RDF links.

### PROP-01 — In-app property creation (ObjectProperty and DatatypeProperty)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S01

OntologyService.create_property() creates OWL ObjectProperty or DatatypeProperty with rdfs:label, rdfs:domain, rdfs:range in urn:sempkm:user-types graph. POST /browser/ontology/create-property endpoint with form-based UI on RBox tab. Unit tests: test_class_creation.py.

### PROP-02 — Property editing (rename, change domain/range)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S03

OntologyService.edit_property() updates label, domain, and range via DELETE/INSERT SPARQL. Accessible from both RBox tab and Custom section on Mental Models. PUT /browser/ontology/edit-property endpoint.

### PROP-03 — Property deletion with confirmation
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S02

OntologyService.delete_property() removes all triples for a user-created property. DELETE /browser/ontology/delete-property endpoint with user-types IRI guard. Unit tests: test_class_creation.py.

### TYPE-05 — Class editing (rename, icon, parent, add/remove properties, SHACL shape update)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S01

OntologyService.edit_class() updates label, icon, color, parent, and properties — replaces SHACL NodeShape via full shape regeneration. POST /browser/ontology/edit-class endpoint with edit_class_form.html modal.

### TYPE-06 — Class deletion with instance-count warnings and confirmation
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S02

OntologyService.delete_class() removes OWL class + SHACL shape triples. GET /browser/ontology/delete-class-check endpoint shows instance/subclass counts with confirmation dialog. DELETE /browser/ontology/delete-class endpoint with user-types IRI guard. Unit tests: test_class_creation.py.

### TYPE-07 — Custom section on Mental Models page listing user types/properties
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S03

OntologyService.list_user_types() queries user-types graph for classes and properties. Mental Models page renders "Custom" section with edit/delete actions inline. Accessible from /browser/mental-models.

### TAB-01 — Create-new-object opens fresh dockview tab
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M004/S04

Fixed openTab() in workspace.js to always open create-new-object in a fresh dockview tab instead of overwriting the active tab. Preserves user's current view.

### LOG-01 — Operations log with PROV-O vocabulary in admin UI
- Status: validated
- Class: admin/support
- Source: user
- Primary Slice: M005/S02

OperationsLogService with log_activity(), list_activities(), get_activity(), count_activities(). PROV-O vocabulary (prov:Activity, prov:startedAtTime, prov:endedAtTime, prov:wasAssociatedWith, prov:used) in urn:sempkm:ops-log named graph. Admin UI at /admin/ops-log with filter and cursor-based pagination. Model install/remove, inference, and validation instrumented with fire-and-forget logging. Unit tests: test_ops_log.py (35 tests).

### MIG-01 — Model schema refresh without uninstall
- Status: validated
- Class: admin/support
- Source: user
- Primary Slice: M005/S05

`POST /admin/models/{model_id}/refresh-artifacts` endpoint updates ontology, shapes, views, and rules graphs from disk without touching seed graph or user data. Transactional CLEAR+INSERT with rollback on failure. Admin UI "Refresh" button on model list and detail pages. ViewSpec cache invalidation. Ops log integration (`model.refresh` activity type). Unit tests: test_model_refresh.py (21 tests).

### PROV-01 — Event and query predicates migrated to PROV-O
- Status: validated
- Class: core-capability
- Source: design (PROV-O-ALIGNMENT.md)
- Primary Slice: M006/S01

All event graphs use `prov:startedAtTime` / `prov:wasAssociatedWith` / `rdfs:label` instead of custom `sempkm:timestamp` / `sempkm:performedBy` / `sempkm:description`. Query history uses `prov:wasAssociatedWith` instead of `vocab:executedBy`. Idempotent migration script. `sempkm:Event rdfs:subClassOf prov:Activity` vocabulary declaration. Unit tests: test_provo_migration.py (13 tests).

### PROV-02 — Comment predicates migrated to PROV-O
- Status: validated
- Class: core-capability
- Source: design (PROV-O-ALIGNMENT.md)
- Primary Slice: M006/S01

Comments use `prov:wasAttributedTo` / `prov:generatedAtTime` instead of `sempkm:commentedBy` / `sempkm:commentedAt`. Zero old comment predicates remain in triplestore.

### EXP-06 — Explorer tree groups ViewSpecs by model
- Status: validated
- Class: core-capability
- Source: design (VIEWS-RETHINK.md)
- Primary Slice: M006/S02

Explorer tree shows ~5 model-grouped folders instead of 31+ flat ViewSpec entries. `views_explorer.html` rewritten for nested model → type structure. Duplicate routes removed from views/router.py.

### VFS-06 — VFS scope dropdown with saved query resolution
- Status: validated
- Class: core-capability
- Source: design (VFS-V2-DESIGN.md)
- Primary Slice: M006/S02

VFS scope dropdown fetches `/api/sparql/saved?include_shared=true`, renders optgroups (My Queries / Model Queries / Shared). `build_scope_filter()` resolves `saved_query_id` → query text → SPARQL filter. Unit tests: test_vfs_scope.py (10 tests).

### DASH-01 — Dashboard creation, rendering, and builder UI
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M006/S03, M006/S04

DashboardSpec SQLAlchemy model with JSON blocks and CSS Grid layouts. 6 block types (view-embed, markdown, object-embed, create-form, sparql-result, divider). 5 layout templates. Form-based builder UI with layout picker and dynamic block configuration. DASHBOARDS explorer section with auto-refresh. Full CRUD via API and UI. Unit tests: test_dashboard.py (27 tests), test_dashboard_builder.py (9 tests).

### DASH-02 — Cross-view context filtering via parameterized SPARQL
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M006/S05

`inject_values_binding()` safely injects VALUES clause into SPARQL queries with IRI and variable name validation. Row click in table view-embed block → `dashboardContextChanged` custom event → htmx:configRequest context injection → server-side render_block forwarding → filtered re-fetch. Unit tests: test_values_injection.py (25 tests).

### WKFL-01 — Workflow creation, runner, and builder UI
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M006/S06, M006/S07

WorkflowSpec SQLAlchemy model with JSON steps. Step types: view, dashboard, form. Stepper runner UI with numbered indicators, prev/next navigation, context passing. Form-based builder UI with step type config. WORKFLOWS explorer section with auto-refresh. Full CRUD via API and UI. Unit tests: test_workflow.py (13 tests), test_workflow_builder.py (10 tests).

### DOCS-04 — User guide for dashboards and workflows
- Status: validated
- Class: quality-attribute
- Source: standing requirement (M006 shipped user-visible features without guide pages)
- Primary Slice: M007/S05
- Acceptance: docs/guide/ has page(s) covering dashboard creation/editing/rendering/cross-view-context and workflow creation/running/editing. Glossary updated.

Chapter 28 (28-dashboards-and-workflows.md) covers all 5 layout templates, 6 block types, cross-view context filtering, 3 workflow step types, stepper runner UI, and explorer sidebar sections. 6 glossary entries added. README TOC updated. Navigation chain ch. 27 → ch. 28 → Appendix A.

### UIPOL-01 — Explorer sidebar consistency fixes
- Status: validated
- Class: quality-attribute
- Source: user (review feedback 2026-03-15)
- Primary Slice: M007/S04
- Acceptance: Left sidebar chevrons use Lucide icons matching right sidebar. OBJECTS refresh/plus buttons always visible. DASHBOARDS/WORKFLOWS headers have plus-sign buttons (no "New X" tree-leaf entries). Inference button matches sibling sizing. Ontology Viewer button is blue. Relationships graph full-width with horizontal layout.

All 6 items verified: Lucide SVG chevrons on 6 sections with rotation. OBJECTS opacity: 1. DASHBOARDS/WORKFLOWS + buttons open builders, tree-leaf entries removed. Inference `<button>` at 32px matching siblings. Ontology Viewer accent color. Dagre LR layout at 600px min-height.

## Deferred

### TYPE-03 — Full SHACL shape editor with advanced constraints
- Class: core-capability
- Status: deferred
- Description: UI for editing SHACL shapes with advanced constraints — cardinality, patterns, value ranges, conditional shapes.
- Why it matters: Power users and model authors need fine-grained control over data validation rules.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Builds on TYPE-01/TYPE-02 class creation. Later milestone.

### TYPE-04 — Mental model export from user-created types
- Class: core-capability
- Status: deferred
- Description: Package user-created types, shapes, and views into a .sempkm-model archive for sharing.
- Why it matters: Users who create custom types should be able to share their mental models with others.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Depends on TYPE-01/TYPE-02. Later milestone.

### MCP-01 — MCP server for AI agent access to SemPKM
- Class: core-capability
- Status: deferred
- Description: MCP server exposing object browse/search, SPARQL query, graph traversal, and write operations to AI agents.
- Why it matters: Enables AI models to directly interact with the knowledge base via standardized tool-use protocol.
- Source: user (pending todo)
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Future milestone. See .planning/todos/pending/2026-03-10-build-mcp-server-for-ai-agent-access-to-sempkm.md for full spec.

### NOTION-01 — Notion workspace import wizard
- Class: core-capability
- Status: deferred
- Description: Interactive import flow for Notion workspace exports (ZIP first, API later). Databases → types, rows → objects, relations → edges, with dashboard/rollup/formula metadata preservation.
- Why it matters: Notion is the most common PKM tool users migrate from. Structured import preserves their knowledge graph.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Full research at `.planning/notion-import-research.md`. Mirrors Obsidian wizard pattern.

### VIEW-06 — Custom column selection UI
- Class: core-capability
- Status: deferred
- Description: UI for users to pick which columns to show/hide in generic table views. SHACL discovery provides defaults.
- Why it matters: Different users care about different properties — one-size-fits-all columns don't work at scale.
- Source: design (VIEWS-RETHINK.md)
- Primary owning slice: none
- Validation: unmapped
- Notes: Depends on VIEW-01/VIEW-02 (generic views + SHACL columns).

### VIEW-07 — Faceted search integration in views
- Class: core-capability
- Status: deferred
- Description: Combine type filter pills with property-value facets (e.g., "Notes tagged 'research' created this week").
- Why it matters: Type filtering alone is coarse — facets enable precise filtering without SPARQL.
- Source: design (VIEWS-RETHINK.md)
- Primary owning slice: none
- Validation: unmapped
- Notes: Depends on VIEW-03 (type filter pills). Builds on SPARQL query builder infrastructure.

### VFS-13 — VFS write support (bidirectional sync)
- Class: core-capability
- Status: deferred
- Description: Full bidirectional VFS — new file creation, file deletion via WebDAV. Requires IRI minting policy, persistent filename→IRI index, conflict resolution, EventStore integration.
- Why it matters: Read-only projection is useful for Obsidian/VS Code but users expect to create/edit/delete files.
- Source: design (VFS-V2-DESIGN.md, item 8)
- Primary owning slice: none
- Validation: unmapped
- Notes: Separate milestone. Complex edge cases (IRI minting, conflict resolution) deserve dedicated scope.

## Out of Scope

### FED-CRDT — CRDT-based real-time sync
- Class: core-capability
- Status: out-of-scope
- Description: Replace last-write-wins conflict resolution with CRDT-based real-time sync.
- Why it matters: No production Python CRDT-for-RDF library exists yet (NextGraph alpha, W3C CG standardizing).
- Source: research
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Data model designed to accommodate CRDT replacement later.

### FED-AUTO — Automatic sync polling
- Class: core-capability
- Status: out-of-scope
- Description: Background job polling remote instances on interval for automatic sync.
- Why it matters: Manual "Sync Now" is sufficient for current usage. Data model supports future automation.
- Source: research
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Deferred per Phase 58 CONTEXT.md.

### FED-FEDI — Fediverse ActivityPub interop
- Class: integration
- Status: out-of-scope
- Description: Legacy cavage HTTP Signatures + RSA for Mastodon/ActivityPub compatibility.
- Why it matters: Only needed if fediverse interop becomes a goal. SemPKM-to-SemPKM uses RFC 9421.
- Source: research
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Would require RSA key support alongside existing Ed25519.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| EXP-01 | core-capability | validated | M003/S01 | M003/S02, S03, S04 | EXPLORER_MODES registry + E2E |
| EXP-02 | core-capability | validated | M003/S01 | none | _handle_by_type handler |
| EXP-03 | core-capability | validated | M003/S02 | none | hierarchy mode + lazy expand |
| EXP-04 | core-capability | validated | M003/S03 | none | mount:{uuid} dispatch + E2E |
| EXP-05 | core-capability | validated | M003/S03 | none | rich objects in mount trees |
| TAG-01 | core-capability | validated | M003/S04 | none | split_tag_values + migration |
| TAG-02 | core-capability | validated | M003/S04 | none | tag pill CSS + # prefix |
| TAG-03 | core-capability | validated | M003/S04 | none | by-tag mode + UNION SPARQL |
| TAG-04 | core-capability | validated | M005/S03 | none | hierarchical `/` nesting + 61 tests |
| TAG-05 | core-capability | validated | M005/S04 | none | tag autocomplete + 22 tests |
| FAV-01 | core-capability | validated | M003/S05 | none | SQL table + toggle + E2E |
| FAV-02 | core-capability | validated | M003/S05 | none | FAVORITES section + auto-refresh |
| CMT-01 | core-capability | validated | M003/S06 | none | RDF comments + EventStore + E2E |
| CMT-02 | core-capability | validated | M003/S06 | none | threaded display + author badges |
| ONTO-01 | core-capability | validated | M003/S07 | none | TBox cross-graph hierarchy + E2E |
| ONTO-02 | core-capability | validated | M003/S07 | none | ABox instance counts + drill-down |
| ONTO-03 | core-capability | validated | M003/S07 | none | RBox property reference table |
| GIST-01 | core-capability | validated | M003/S07 | M003/S08 | gistCore14.0.0 loaded in named graph |
| GIST-02 | core-capability | validated | M003/S07 | none | rdfs:subClassOf in basic-pkm + ppv |
| TYPE-01 | core-capability | validated | M003/S08 | none | Create Class form on Ontology Viewer, verified 2026-03-13 |
| TYPE-02 | core-capability | validated | M003/S08 | none | OWL + SHACL generation, verified 2026-03-13 |
| ADMIN-01 | admin/support | validated | M003/S09 | none | SPARQL-computed stats |
| ADMIN-02 | admin/support | validated | M003/S09 | none | Chart.js sparkline + histogram |
| SEC-01 | compliance/security | validated | M002/S01 | none | slowapi rate limiting |
| SEC-02 | compliance/security | validated | M002/S01 | none | conditional token logging |
| SEC-03 | compliance/security | validated | M002/S01 | none | require_role on event console |
| SEC-04 | compliance/security | validated | M002/S01 | M002/S03 | escape_sparql_regex + 19 tests |
| SEC-05 | operability | validated | M002/S01 | none | deployment docs section |
| COR-01 | core-capability | validated | M002/S02 | none | hashlib.sha256 in report.py |
| COR-02 | core-capability | validated | M002/S02 | M002/S03 | _strip_sparql_strings + 6 tests |
| COR-03 | core-capability | validated | M002/S02 | none | GRAPH ?g source_model query |
| TEST-01 | quality-attribute | validated | M002/S03 | none | conftest.py + 130 tests |
| TEST-02 | quality-attribute | validated | M002/S03 | none | test_rdf_serialization + test_sparql_utils |
| TEST-03 | quality-attribute | validated | M002/S03 | none | test_iri_validation |
| TEST-04 | quality-attribute | validated | M002/S03 | none | test_auth_tokens |
| REF-01 | quality-attribute | validated | M002/S04 | none | 8 sub-modules, 33 routes |
| DEP-01 | operability | validated | M002/S05 | none | ~= pins in pyproject.toml |
| DEP-02 | operability | validated | M002/S05 | none | uv.lock committed |
| PERF-01 | quality-attribute | validated | M002/S05 | none | batched WHERE IN query |
| FED-11 | core-capability | validated | M002/S06 | none | discover_remote_instance_url |
| FED-12 | quality-attribute | validated | M002/S06 | none | docker-compose.federation-test.yml |
| FED-13 | quality-attribute | validated | M002/S06 | none | 8-step Playwright E2E test |
| OBSI-08 | core-capability | validated | M002/S07 | none | 895 objects imported |
| OBSI-09 | core-capability | validated | M002/S07 | none | 1767 wiki-link edges |
| OBSI-10 | core-capability | validated | M002/S07 | none | frontmatter properties in UI |
| PROP-01 | core-capability | validated | M004/S01 | none | create_property service + endpoint |
| PROP-02 | core-capability | validated | M004/S03 | none | edit_property service + endpoint |
| PROP-03 | core-capability | validated | M004/S02 | none | delete_property service + endpoint |
| TYPE-05 | core-capability | validated | M004/S01 | none | edit_class with SHACL shape replacement |
| TYPE-06 | core-capability | validated | M004/S02 | none | delete_class with instance warnings |
| TYPE-07 | core-capability | validated | M004/S03 | none | Custom section on Mental Models |
| TAB-01 | core-capability | validated | M004/S04 | none | fresh dockview tab for new objects |
| LOG-01 | admin/support | validated | M005/S02 | none | PROV-O ops log + admin UI + 35 tests |
| MIG-01 | admin/support | validated | M005/S05 | none | refresh_artifacts endpoint + admin UI + 21 tests |
| PROV-01 | core-capability | validated | M006/S01 | none | PROV-O event/query predicates + migration script + 13 tests |
| PROV-02 | core-capability | validated | M006/S01 | none | PROV-O comment predicates + 0 old triples |
| EXP-06 | core-capability | validated | M006/S02 | none | model-grouped explorer tree + duplicate route cleanup |
| VFS-06 | core-capability | validated | M006/S02 | none | scope dropdown + saved query resolution + 10 tests |
| DASH-01 | core-capability | validated | M006/S03 | M006/S04 | dashboard model + builder UI + explorer + 36 tests |
| DASH-02 | core-capability | validated | M006/S05 | none | cross-view context + VALUES injection + 25 tests |
| WKFL-01 | core-capability | validated | M006/S06 | M006/S07 | workflow model + runner + builder + explorer + 23 tests |
| VIEW-01 | core-capability | validated | M007/S01 | none | 3 generic ViewSpecs + explorer entries + 32 unit tests |
| VIEW-02 | core-capability | validated | M007/S01 | none | SHACL column discovery + fallback + unit tests |
| VIEW-03 | core-capability | validated | M007/S01 | none | type pills + localStorage + htmx filtering |
| VIEW-04 | core-capability | validated | M007/S01 | none | flat explorer + Saved Views + no MY VIEWS |
| VIEW-05 | core-capability | validated | M007/S01 | none | carousel with generic + model-declared specs |
| VFS-07 | core-capability | validated | M007/S02 | none | type_filter VALUES + UI + 6 tests |
| VFS-08 | core-capability | validated | M007/S02 | none | scopeQuery IRI + migration + grep-verified |
| VFS-09 | core-capability | validated | M007/S02 | none | preview + WebDAV query resolution + 5 tests |
| VFS-10 | quality-attribute | validated | M007/S02 | none | path contract docs + 26 tests |
| VFS-11 | core-capability | validated | M007/S03 | none | chain parsing + validation + narrowing + 39 tests + browser UI |
| VFS-12 | core-capability | validated | M007/S03 | none | filename template expansion + 12 tests + browser UI |
| DOCS-04 | quality-attribute | validated | M007/S05 | none | Ch. 28 guide + 6 glossary entries |
| UIPOL-01 | quality-attribute | validated | M007/S04 | none | 6 items browser-verified |
| CANVAS-01 | core-capability | validated | M008/S01 | none | resize handles + persistence + 11 unit tests + 2 E2E tests |
| CANVAS-02 | core-capability | validated | M008/S02 | none | properties endpoint + 26 unit tests + 8 browser assertions |
| CANVAS-03 | core-capability | validated | M008/S03 | none | dual-layer rendering + embed endpoints + 32 tests |
| CANVAS-04 | core-capability | validated | M008/S03 | none | sparql-result endpoint + object embed + 32 tests |
| CANVAS-05 | core-capability | validated | M008/S03 | none | toolbar picker + explorer drag-drop + 32 tests |
| PERSONA-01 | core-capability | validated | M012/S03 | M012/S04 | PersonaService + 20 unit tests + 7 API endpoints + E2E |
| PERSONA-02 | core-capability | validated | M012/S03 | M012/S04 | switchPersona() + fromJSON try/catch + guard flag + E2E |
| PERSONA-03 | core-capability | validated | M012/S03 | M012/S04 | sidebar selector UI + browser screenshot + E2E |
| PERSONA-04 | core-capability | validated | M012/S03 | M012/S04 | 3 command palette entries + dynamic submenu + E2E |
| PERSONA-05 | core-capability | validated | M012/S03 | M012/S04 | initPersonas() auto-create + browser verified + E2E |
| EVTLOG-01 | core-capability | validated | M012/S01 | M012/S04 | label resolution + unit tests + E2E + docs |
| EVTLOG-02 | core-capability | validated | M012/S01 | M012/S04 | helptext extraction + unit tests + E2E + docs |
| EVTLOG-03 | core-capability | validated | M012/S01 | M012/S04 | autocomplete endpoints + unit tests + E2E + docs |
| BDIFF-01 | core-capability | validated | M012/S02 | M012/S04 | body.diff handler + unit tests + E2E + docs |
| BDIFF-02 | core-capability | validated | M012/S02 | M012/S04 | diff rendering + unit tests + E2E + docs |
| BDIFF-03 | core-capability | validated | M012/S02 | M012/S04 | backward compat + E2E + docs |
| TYPE-03 | core-capability | deferred | none | none | unmapped |
| TYPE-04 | core-capability | deferred | none | none | unmapped |
| MCP-01 | core-capability | deferred | none | none | unmapped |
| NOTION-01 | core-capability | deferred | none | none | unmapped |
| VIEW-06 | core-capability | deferred | none | none | design: VIEWS-RETHINK.md |
| VIEW-07 | core-capability | deferred | none | none | design: VIEWS-RETHINK.md |
| VFS-13 | core-capability | deferred | none | none | design: VFS-V2-DESIGN.md item 8 |
| FED-CRDT | core-capability | out-of-scope | none | none | n/a |
| FED-AUTO | core-capability | out-of-scope | none | none | n/a |
| FED-FEDI | integration | out-of-scope | none | none | n/a |
| APP-01 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §3, §14 |
| APP-02 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §5, §10 |
| APP-03 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §6 |
| APP-04 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §5 |
| APP-05 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §9 |
| APP-06 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §8 |
| APP-07 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §7 L1 |
| APP-08 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §7 L2 |
| APP-09 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §7 L3 |
| APP-10 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §11 |
| APP-11 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §12 |
| APP-12 | enhancement | active | none | none | design: APP-PLATFORM-DESIGN.md §1 |
| APP-13 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §11 |
| APP-14 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §15 |
| RSS-01 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §13 |
| RSS-02 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md |
| RSS-03 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §7 L3 |
| RSS-04 | core-capability | active | none | none | research: rss-reader-hypothesis §8 |
| RSS-05 | enhancement | active | none | none | research: rss-reader-hypothesis §7 |
| RSS-06 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §13 |
| RSS-07 | core-capability | active | none | none | design: APP-PLATFORM-DESIGN.md §2 |
| RSS-08 | enhancement | active | none | none | research: rss-reader-hypothesis §4-5 |
| MODEL-01 | core-capability | validated | M011/S01 | M011/S05 | offline validation + cross-model test + E2E Docker lifecycle + Ch. 29 guide |
| MODEL-02 | core-capability | validated | M011/S02 | M011/S05 | offline validation + cross-model test + E2E Docker lifecycle + Ch. 29 guide |
| MODEL-03 | core-capability | validated | M011/S03 | M011/S05 | offline validation + cross-model test + E2E Docker lifecycle + Ch. 29 guide |
| MODEL-04 | core-capability | validated | M011/S04 | M011/S05 | offline validation + cross-model test + E2E Docker lifecycle + Ch. 29 guide |

## Coverage Summary

- Active requirements: 22 (14 APP + 8 RSS)
- Validated: 132 (38 from M001 + 22 from M002 + 21 from M003 + 7 from M004 + 4 from M005 + 7 from M006 + 13 from M007 + 5 from M008 + 4 from M011 + 11 from M012)
- Deferred: 7 (TYPE-03, TYPE-04, MCP-01, NOTION-01, VIEW-06, VIEW-07, VFS-13)
- Out of scope: 3
- Unmapped active requirements: 22 (14 APP + 8 RSS — pending M009/M010 roadmap planning)
