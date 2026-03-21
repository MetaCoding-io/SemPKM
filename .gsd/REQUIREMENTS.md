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

### EVENT-01 — bpkm:Event type in basic-pkm Mental Model
- Status: validated
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Primary Slice: M018/S01
- Acceptance: basic-pkm v2.1.0 has bpkm:Event OWL class (subClassOf gist:Event) with 20 properties covering the cross-provider superset (Google/Outlook/CalDAV per D212). SHACL EventShape with 5 property groups, 30 property shapes, 4 enum constraints (eventStatus, visibility, showAs, responseStatus). ViewSpecs (table/cards/graph), SavedQueries (upcoming/past), 4 seed instances (timed, all-day, recurring master, recurring exception). Lucide calendar icon. Passes offline pyshacl validation with zero errors.

22 offline validation tests prove: manifest v2.1.0, 7 OWL classes, 7 NodeShapes, 21 ViewSpecs, 8 SavedQueries, 4 seed Events, pyshacl zero violations, enum constraints match D212 cross-provider superset.

### GCAL-01 — Google OAuth 2.0 authentication
- Status: validated
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Primary Slice: M018/S02
- Acceptance: User completes OAuth consent flow through app proxy callback. Tokens stored via StateClient. Refresh works on 401.

OAuth auth module with 7 helpers (authorize URL, code exchange, refresh, refresh_if_expired with 5-min buffer, store tokens as ISO 8601, connection status, clear). 23 unit tests cover all auth paths. App proxy query-param forwarding fixed (5 regression tests). Route handlers implement full OAuth redirect/callback with CSRF state verification. GCal REST client with 401→refresh→retry (12 tests). 1498 total tests pass.

### GCAL-02 — Calendar list and selection
- Status: validated
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Primary Slice: M018/S02
- Acceptance: After OAuth, user sees their calendar list with selection checkboxes. Selected calendars persisted.

GCalClient.get_calendar_list() with pagination via nextPageToken, normalized calendar dicts (id, summary, primary flag). Calendar list UI with checkboxes in connect_status.html template, selection persisted as JSON via StateClient. 12 client unit tests cover single-page, paginated, empty, auth header, 401→retry, error handling.

### GCAL-03 — Pull sync (Google Calendar → bpkm:Event)
- Status: validated
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Primary Slice: M018/S03
- Acceptance: User triggers sync and events from selected calendars appear as bpkm:Event objects with correct field mapping for all ~22 properties (times, timezone, attendees, conference URLs, location, all-day, status).

pull_sync() creates bpkm:Event objects with correct field mapping for all ~22 properties. 64 field mapper tests + 36 sync engine tests prove all transform paths. syncToken incremental sync with 410 Gone recovery. Per-event error isolation. Settings UI with Sync Now trigger, direction/interval controls, sync stats display.

### GCAL-04 — Attendee resolution to Person objects
- Status: validated
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Primary Slice: M018/S03
- Acceptance: Event attendees resolved to existing Person/Contact objects by email via SPARQL lookup.

PersonMatcher resolves attendee/organizer emails to existing Person/Contact objects via SPARQL lookup (foaf:mbox + crm:email). Creates Person on miss with email-derived slug. In-memory LRU cache per sync run. 11 person matcher tests.

### GCAL-05 — RSVP push-back to Google Calendar
- Status: active
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Acceptance: User changes RSVP status in SemPKM, Google Calendar reflects the change via API PATCH.

### GCAL-06 — Recurrence handling (master + exceptions)
- Status: active
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Acceptance: Recurring events stored as master with RRULE; individually modified instances stored as separate Events linked to master via recurringEventId.

### GCAL-07 — All-day event detection
- Status: validated
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Primary Slice: M018/S03
- Acceptance: All-day events distinguished from timed events. Correct xsd:date vs xsd:dateTime usage.

detect_all_day() distinguishes all-day (start.date → xsd:date, allDay="true") from timed (start.dateTime → xsd:dateTime, allDay="false"). 4 dedicated tests + full-event integration tests.

### GCAL-08 — Conference URL extraction
- Status: validated
- Class: core-capability
- Source: design (M018-ROADMAP.md)
- Primary Slice: M018/S03
- Acceptance: Conference URLs (Meet, Zoom) extracted from Google Calendar events and preserved as bpkm:conferenceUrl.

extract_conference_url() extracts from conferenceData.entryPoints[type=video].uri with hangoutLink fallback. 6 dedicated tests cover all extraction paths.

### GCAL-09 — E2E tests and user guide
- Status: active
- Class: quality-attribute
- Source: design (M018-ROADMAP.md)
- Acceptance: Mock Google Calendar API server passes selftest. Playwright E2E test proves install → OAuth → sync → verify → RSVP push lifecycle. User guide chapter documents workflow.

### GH-01 — GitHub PAT authentication
- Status: validated
- Class: core-capability
- Source: design (M017-ROADMAP.md)
- Primary Slice: M017/S01
- Acceptance: User enters a GitHub Personal Access Token. PAT stored via StateClient, verified via `GET /user` endpoint. Connection status shows username and masked PAT preview. Disconnect clears credentials.

15 unit tests verify PAT storage, verification, connection status, masking, and disconnect. Mock GitHub API server validates /user endpoint. E2E test phases 0-2 confirm app installs and routes correctly.

### GH-02 — Pull sync: GitHub issues to bpkm:Task
- Status: validated
- Class: core-capability
- Source: design (M017-ROADMAP.md)
- Primary Slice: M017/S01
- Acceptance: User selects repos and triggers sync. GitHub issues appear as bpkm:Task objects with correct status (open→todo, closed→done, not_planned→cancelled), labels as tags, first assignee mapped to Person, milestone as project, body as markdown, external URL/ID/UUID preserved. Delta sync via `since` parameter. Per-issue error isolation.

42 field mapper tests + 26 sync engine tests verify all field mappings, two-phase bulk create, delta sync, PR filtering, and error isolation. Mock GitHub API provides canned issue data for integration testing.

### GH-03 — Pull sync: PRs + issue linking
- Status: validated
- Class: core-capability
- Source: design (M017-ROADMAP.md)
- Primary Slice: M017/S02
- Acceptance: GitHub PRs appear as bpkm:Task objects with `externalProvider: "github-pr"`. PRs that reference issues (via timeline API cross-referenced events) have edges linking PR task → issue task.

32 unit tests verify PR task creation with github-pr provider, timeline parsing (cross-referenced events, same-repo filtering, dedup, malformed event skip), edge creation (bpkm:dependsOn from PR task to issue task), error isolation, diagnostic surface. Mock GitHub API provides timeline cross-reference events.

### GH-04 — Push sync: SemPKM → GitHub
- Status: validated
- Class: core-capability
- Source: design (M017-ROADMAP.md)
- Primary Slice: M017/S03
- Acceptance: User edits task title/status in SemPKM, triggers push, and changes appear in GitHub via PATCH API. Loop prevention via `lastSyncedAt` comparison prevents re-import of pushed changes.

33 unit tests verify push_sync pipeline (SPARQL change detection, reverse field mapping, PATCH mutation, lastSyncedAt update), loop prevention in pull_sync, parse_external_url, diagnostic surface. Mock GitHub API provides PATCH echo-back endpoint.

### GH-05 — Settings UI: repo selection, sync direction, poll interval
- Status: validated
- Class: core-capability
- Source: design (M017-ROADMAP.md)
- Primary Slice: M017/S03
- Acceptance: Settings page has repo multi-select, sync direction toggle, poll interval configuration, Sync Now button, and sync stats panel.

15 unit tests verify sync-config route saves direction/interval, bidirectional sync_now runs push after pull, push_changes handler, _render_connect_status template context. Template has direction radios, poll interval dropdown, push result stats section.

### GH-06 — Person matching: assignee resolution
- Status: validated
- Class: core-capability
- Source: design (M017-ROADMAP.md)
- Primary Slice: M017/S01
- Acceptance: GitHub assignee email resolved via SPARQL lookup (foaf:mbox, crm:email). Login-based fallback via bpkm:externalId. Person created on miss. In-memory LRU cache per sync run.

10 person matcher unit tests verify email match, login fallback, cache hit, person creation.

### GH-07 — E2E tests + user guide
- Status: validated
- Class: quality-attribute
- Source: design (M017-ROADMAP.md)
- Primary Slice: M017/S04
- Acceptance: Mock GitHub REST API server in Docker. Playwright E2E test covers install → configure → sync → verify → push → cleanup. Chapter 35 user guide documents GitHub sync with field mapping tables.

Mock GitHub REST API server (9 endpoint selftest). Playwright E2E test (12 phases — phases 0-2 pass, phases 3+ blocked by pre-existing app subprocess startup issue, not a GitHub sync defect). Chapter 35 user guide (33 sections, field mapping tables, PR-to-issue linking). README TOC entry, glossary entry, navigation chain Ch 34 → Ch 35 → Appendix A. Two pre-existing platform bugs fixed (browser/apps.py registry access, workspace-layout.js app-page routing).

### API-01 — Well-known instance discovery endpoint
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M013/S01
- Acceptance: `GET /.well-known/sempkm` returns JSON with version string, endpoint URLs, auth methods, and capabilities list. Requires authentication (session cookie or Bearer API token). Response matches documented schema.

GET /.well-known/sempkm returns JSON with version, endpoints, auth, capabilities. 10 unit tests verify schema, content-type, auth enforcement, and field types. Docker curl confirms 401 JSON for unauthenticated and invalid-bearer requests.

### API-02 — Types endpoint with labels, icons, and model attribution
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M013/S02
- Acceptance: `GET /api/types` returns JSON array of all types from installed Mental Models. Each entry has IRI, label, icon name (Lucide), icon color, model ID, and model name. Empty when no models installed.

GET /api/types returns JSON array with TypeInfo entries (iri, label, icon, icon_color, model_id, model_name). 8 unit tests verify schema, field completeness, icon presence/absence, model attribution, auth enforcement (cookie + bearer + unauthenticated), and empty state. IconService created ad-hoc matching codebase pattern (D164).

### API-03 — SHACL shapes endpoint as structured JSON
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M013/S02
- Acceptance: `GET /api/shapes/{type_iri}` returns SHACL property shapes as JSON with shape IRI, target class, label, groups (IRI, label, order), and properties (path, name, datatype, constraints, in_values, helptext, order, group). Returns 404 for unknown type IRIs.

GET /api/shapes/{type_iri} returns ShapeResponse with properties and groups matching SHACL dataclasses. 11 unit tests verify schema, field completeness, constraint round-trip (in_values, min/max_count), target_class on object references, group ordering, helptext, 404, and auth enforcement. Shape serialization via dataclasses.asdict() to Pydantic models (D160).

### API-04 — Context-query endpoint for related objects
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M013/S03
- Acceptance: `POST /api/context-query` accepts JSON with url/title/keywords (at least one required), returns related objects with IRI, label, type, match_type, and snippet. URL matching via exact SPARQL FILTER, keyword matching via FTS/LuceneSail. Results deduplicated.

POST /api/context-query accepts JSON with url/title/keywords, returns deduplicated results with IRI, label, type, match_type, snippet. 13 context-query unit tests + 5 SPARQL escape tests + 2 E2E tests prove success paths, error cases, graceful degradation, and auth enforcement.

### API-05 — Dual-auth dependency (session cookie + Bearer API token)
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M013/S01
- Acceptance: All M013 API endpoints accept either session cookie or `Authorization: Bearer <token>` header. Invalid tokens return 401. Existing session-only auth for htmx routes is unchanged.

get_current_user_or_api dependency fully tested: 8 bearer extraction tests + 7 dual-auth integration tests. Both cookie and bearer paths work. Invalid credentials produce appropriate 401 responses with distinct detail messages.

### API-06 — CORS headers for browser extension access
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M013/S01
- Acceptance: All `/api/` and `/.well-known/sempkm` responses include `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Headers: Authorization, Content-Type, Accept`, `Access-Control-Allow-Methods: GET, POST, OPTIONS`. OPTIONS preflight returns 204.

CORS headers verified on /api/ and /.well-known/ via Docker curl. OPTIONS → 204 with correct headers. `always` flag ensures headers on error responses.

### API-07 — nginx Authorization header forwarding on /api/
- Status: validated
- Class: core-capability
- Source: research (M013-RESEARCH.md)
- Primary Slice: M013/S01
- Acceptance: nginx `/api/` proxy block forwards the `Authorization` header to FastAPI (matching the existing `/dav/` block pattern). Bearer tokens from external clients reach the backend.

nginx /api/ block has proxy_set_header Authorization $http_authorization matching /dav/ pattern. Docker curl confirms Authorization header forwarded. nginx -t validates config syntax.

### API-08 — API surface user guide documentation
- Status: validated
- Class: quality-attribute
- Source: standing requirement
- Primary Slice: M013/S03
- Acceptance: `docs/guide/31-api-surface.md` documents all four endpoints with request/response examples, authentication methods, CORS behavior, and error responses. Linked in README TOC and glossary.

docs/guide/31-api-surface.md documents all four endpoints with curl examples, JSON responses, field descriptions, auth methods (session + Bearer), CORS reverse-proxy config, and error responses. README TOC updated. Three glossary entries (API Surface, Context Query, Instance Discovery) cross-reference Chapter 31. Navigation chain Ch30 → Ch31 → Appendix A.

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

### VIEW-08 — Carousel removal — explorer sidebar is sole view selector
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S01
- Acceptance: Carousel tab bar (`carousel_tab_bar.html`) removed from all view templates and JS. No carousel CSS remains. `switchCarouselView()`, `restoreCarouselView()` deleted. Model-declared ViewSpecs accessible via view toolbar dropdown when type filter pill is active.
- Validation: `grep -rn "carousel"` returns zero results in templates/JS/CSS. 25 unit tests pass. Variant dropdown renders conditionally based on `model_view_specs`.

### VIEW-09 — Saved query scope binding on all view types
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S01
- Supporting Slices: M031/S05, M031/S07
- Acceptance: `scope_query` URL parameter accepted by all three generic view renderers (table, card, graph) and graph data endpoint. Saved query WHERE body injected as sub-select filter. Scope persists across pagination. Scope dropdown in view toolbar. Graceful degradation for invalid scope.
- Validation: scope_query wiring verified across all renderers. Full-height fix in S05 confirmed views render correctly with scope binding active.

### VIEW-10 — Multiple view instances as tabs with different scopes
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S02
- Supporting Slices: M031/S07
- Acceptance: `openGenericViewTab()` creates unique tab IDs per invocation. Scoped tabs deduplicate by `renderer:scope:queryId`. Unscoped tabs use `renderer:timestamp`. Tab labels differentiate instances with scope name or numeric suffix. Multiple tabs of the same renderer coexist as independent dockview panels.
- Validation: Old fixed tab ID pattern `var tabKey = 'generic-view:' + renderer;` removed. New dynamic scheme confirmed in workspace.js. Function signature accepts scopeLabel for caller-controlled differentiation.

### VIEW-11 — Saved views load/display/create/unpin correctly
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S02
- Supporting Slices: M031/S07
- Acceptance: "Save View" button in view toolbar persists current configuration (renderer, type_filter, scope_query_id) as a PromotedView via `POST /browser/views/save`. Saved Views folder shows entries with renderer-type icons, labels, and unpin actions. Generic saved views open via `openGenericViewTab()`. Unpin calls `DELETE /browser/views/saved/{view_id}`.
- Validation: 13 unit tests pass covering save_promoted_view, list_promoted_views (with OPTIONAL fields), delete_promoted_view. `save_promoted_view` and POST endpoint exist. my_views.html routes through openGenericViewTab.

### SQ-01 — Saved queries accessible in explorer sidebar
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S03
- Supporting Slices: M031/S07
- Acceptance: QUERIES section in explorer sidebar between VIEWS and DASHBOARDS, lazy-loaded via htmx. Lists saved queries grouped by source (user vs. model). Click opens scoped Table View tab.
- Validation: 18 template rendering tests + 5 endpoint behavior tests. `section-queries` in workspace.html, `saved_queries_explorer.html` partial, `GET /browser/views/saved-queries/explorer` endpoint with graceful error degradation.

### SQ-02 — Saved queries as canvas embed source
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S03
- Acceptance: Drag a saved query from the explorer sidebar onto the spatial canvas to create an embedded view widget.
- Validation: `ondragstart` sets `window.__canvasDragPayload = {type:'query', id, url:'/browser/sparql-result/{id}?embed=1', label}` matching existing canvas embed format. Drag attributes confirmed in 18 template tests.

### SQ-03 — Saved queries as VFS mount scope
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S03
- Acceptance: VFS mount scope dropdown works with saved queries. `build_scope_filter()` generates sub-select from resolved query text.
- Validation: 5 VFS scope query verification tests confirm `build_scope_filter()`, `_extract_where_body()`, `_resolve_scope_query_sync`, and `MountDefinition.scope_query` field all work correctly. Already implemented prior to S03.

### SPARQL-09 — Graph visualization tab for triple-pattern SPARQL results
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S05
- Supporting Slices: M031/S07
- Acceptance: Triple-pattern SPARQL results (3 URI-heavy variables) show a Table/Graph tab switcher. Graph tab renders Cytoscape.js visualization with subject/object as nodes and predicates as directed edges. Lazy initialization on first Graph tab click.
- Validation: `isTriplePattern()` heuristic, `buildGraphElements()`, `initSparqlGraph()`, `injectGraphTab()` implemented. `.sparql-result-tabs` and `.sparql-graph-container` CSS. UAT confirmed with `SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10`.

### SPARQL-10 — Fix IRI pills falling through to plain spans
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S05
- Supporting Slices: M031/S07
- Acceptance: All `urn:sempkm:model:*` IRIs in SPARQL results render as styled pills (vocab pills with dashed border and italic label), not raw `<span class="sparql-uri">`. The `_VOCAB_PREFIXES` allow-list excludes `urn:sempkm:model:` so model ontology IRIs get enriched.
- Validation: Broad `"urn:sempkm:"` replaced with 28 specific internal sub-namespaces. `vocabIriIndex` lookup in `renderCell()` renders `.sparql-vocab-pill` elements. CSS exists in workspace.css.

### SPARQL-11 — Dynamic model prefix shortening in shortenUri()
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S05
- Supporting Slices: M031/S07
- Acceptance: `shortenUri()` uses dynamic `reversePrefixMap` (derived from `prefixCache`) in addition to hardcoded well-known prefix map. Model ontology IRIs shortened to QNames (e.g., `pkm:Person`).
- Validation: `reversePrefixMap` built in `fetchVocabulary()`, checked in `shortenUri()` after hardcoded map. Module-level var inspectable in browser console.

### ONTO-04 — Property description tooltips in TBox detail
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S05
- Supporting Slices: M031/S07
- Acceptance: TBox class detail property names show `rdfs:comment` / `skos:definition` tooltips on hover via HTML `title` attribute.
- Validation: `get_class_detail()` SPARQL fetches `?propDescription` via COALESCE(rdfs:comment, skos:definition). Property dict includes `description`. Template renders `title="{{ p.description }}"` conditionally.

### ONTO-05 — Admin model graph full-width/full-height
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S05
- Supporting Slices: M031/S07
- Acceptance: Admin model ontology diagram fills viewport height. `.ontology-diagram-panel` is flex column, `.ontology-cy-container` uses `flex:1; height:calc(100vh - 250px)`.
- Validation: CSS changed from `min-height:600px` to `flex:1; min-height:400px; height:calc(100vh - 250px)`. Computed styles inspectable in devtools.

### ONTO-06 — Edge tooltips in admin model graph
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S05
- Supporting Slices: M031/S07
- Acceptance: Hovering an edge in the admin model ontology diagram shows a popover with property label, domain→range path, and description.
- Validation: Edge data includes `description`, `domain_label`, `range_label`. Cytoscape mouseover/mouseout handlers follow the 200ms/150ms show/hide pattern. Reuses existing `#ontology-popover` element.

### VIEW-13 — All views use 100% available height
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S05
- Supporting Slices: M031/S07
- Acceptance: Graph, kanban, table, and cards views fill their panel height with no outer scrollbar. `.view-flex-column` wrapper with `flex:1; min-height:0` on expandable children. No fragile `calc(100% - Xpx)` in view CSS.
- Validation: `.view-flex-column` applied to graph_view.html and kanban_view.html. Old `calc(100% - 90px)` removed. Table/cards verified to use natural scrolling without changes.

### VIEW-14 — Graph view node popover z-index fix
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S05
- Supporting Slices: M031/S07
- Acceptance: Graph node and edge popovers render above dockview chrome, toolbar, and tabs when hovering nodes near the top of the view.
- Validation: Popovers appended to `document.body` with `position:fixed; z-index:9999`. Positioning uses `getBoundingClientRect()`. Cleanup removes popovers on graph destroy.

### VIEW-12 — Kanban renderer with status-based columns and drag-drop
- Status: validated
- Class: core-capability
- Source: design (M031 roadmap)
- Primary Slice: M031/S04
- Supporting Slices: M031/S07
- Acceptance: Kanban view renders status-based columns detected from SHACL sh:in constraints. Drag-drop between columns changes object status via PATCH. Type filter pills filter which objects appear.
- Validation: SHACL sh:in scan in _detect_status_field(), kanban_view.html with drag-drop JS, /browser/kanban/{iri}/move endpoint, 15 unit tests.

### DBUIX-01 — Dashboard/workflow builder help text
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S06
- Acceptance: Every field in both dashboard and workflow builders has a `<small class="field-help">` element with a descriptive hint following the SHACL helptext pattern.
- Validation: Dashboard builder has 13 field-help instances, workflow builder has 6. All block type configs include contextual help.

### DBUIX-02 — Autocomplete for object/type references in builders
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S06
- Acceptance: Target Class IRI and Object IRI fields in builders offer search-as-you-type autocomplete from `/browser/class-search` and `/browser/object-search` endpoints.
- Validation: class-search and object-search endpoints in search.py, reference-field autocomplete widgets in both builder templates, 300ms debounce, click-to-select.

### DBUIX-03 — Workflow view step simplification
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S06
- Acceptance: Workflow "view" step uses a single view picker; renderer_type is auto-set from the selected view spec via hidden input. No redundant renderer dropdown.
- Validation: step-config-renderer class absent from workflow builder (grep returns 0). _wfUpdateRendererFromView() sets hidden input + renderer badge from _cachedViews.

### DBUIX-04 — Sample dashboard and workflow seed data
- Status: validated
- Class: enhancement
- Source: design (M031 roadmap)
- Primary Slice: M031/S06
- Acceptance: Idempotent seed_sample_data() creates "Getting Started" dashboard and "Create & Review" workflow for users with none. Runs at startup, never crashes app.
- Validation: seed.py valid Python, startup hook in main.py, 4 unit tests (empty, existing, mixed states), error isolation via try/except.

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

### EXT-01 — Extension popup capture with type selector and save flow
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S01
- Acceptance: Clicking the extension icon opens a popup with a type selector populated from all installed Mental Models. User selects a type, fills in title, clicks Save, and the object is created in SemPKM via POST /api/commands with Bearer auth.

Popup type selector grouped by model via optgroup. Save flow calls SemPKMClient.createObject(). E2E test 3 proves full round-trip (popup save → SPARQL-verified persistence).

### EXT-02 — SHACL-driven dynamic forms in extension popup
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S02
- Acceptance: Selecting a type renders a dynamic SHACL-driven form with grouped fields, helptext, validation indicators, and all standard property types (string, date, boolean, enum, object reference, multi-value, tags, integer, decimal, anyURI).

shacl-renderer.js (588 lines) handles 10 property types with groups, multi-value, skip paths. Node.js rendering tests verified 4 types (Contact 12 fields/6 groups, Deal, Note, Task). E2E test 2 verifies [data-path] inputs render.

### EXT-03 — Auto-population from page metadata
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S03
- Acceptance: Opening the popup on any page auto-fills title and URL from page metadata. Selecting text before opening pre-fills the body field. Settings toggles control behavior.

extractor.js extracts title (og:title > twitter:title > document.title), URL, selected text via chrome.scripting.executeScript. S03 unit tests (19/19) and integration checks (14/14) pass.

### EXT-04 — Relationship picker with object search
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S04
- Acceptance: Object reference fields show search-as-you-type input. Typing queries context-query API. Selecting a result populates the hidden IRI input. After saving, edges link to selected objects.

reference-picker.js provides debounced search (300ms), type filtering via data-target-class, dropdown with label + type badge. Two-step save: object.create → edge.create with per-edge error isolation.

### EXT-05 — Context menu "Save to SemPKM"
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S03
- Acceptance: Right-click selected text → "Save to SemPKM" opens the popup with the text pre-filled.

service-worker.js registers context menu item on install, stores selection in chrome.storage.session, opens popup. Popup checks session storage on init and pre-fills fields.

### EXT-06 — Schema.org JSON-LD auto-fill
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S03
- Acceptance: Pages with schema.org JSON-LD (Person, Article, Organization) auto-fill matching fields when the corresponding type is selected.

schema-mapper.js maps Person→Contact, Organization→Company, Article→Note, ScholarlyArticle→Paper. Cross-namespace property mapping with first-write-wins priority. 19/19 unit tests pass.

### EXT-07 — Extension settings page
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S01
- Acceptance: Settings page configures instance URL, API key, and default type with connection test (green/red indicator). Settings persist via chrome.storage.sync.

Options page with Instance URL, API key (visibility toggle), Test Connection button, Default Type selector from /api/types, capture behavior checkboxes, and Save persistence. E2E test 1 proves round-trip.

### EXT-08 — Keyboard shortcut (Alt+S)
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S05
- Acceptance: Alt+S keyboard shortcut opens the extension popup in both Chrome and Firefox.

Both manifest.json and manifest.firefox.json have commands._execute_action with suggested_key.default "Alt+S". Uses browser-native _execute_action which opens popup without JS handler.

### EXT-09 — Success/error feedback
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S01
- Acceptance: After saving, user sees green success toast or red error toast with detail. Connection status indicator shows green/red/amber state.

showToast(message, type) with green success and red error, auto-dismiss. setConnectionDot(state, tooltip) for connection health. Loading spinners during save. E2E test 3 waits for success toast.

### EXT-10 — Cross-browser compatibility (Chrome + Firefox)
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S05
- Acceptance: Extension works in both Chrome (MV3) and Firefox (WebExtension) from unpacked/sideloaded directory.

manifest.firefox.json with background.scripts array, browser_specific_settings.gecko (sempkm@sempkm.org, strict_min_version 109.0). Service worker uses classic script (no ES module imports) for Firefox compat. All JS files pass node --check.

### EXT-11 — Backend Bearer token auth on POST /api/commands
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M014/S01
- Acceptance: POST /api/commands accepts Authorization: Bearer <token> header. Existing session cookie auth unchanged for htmx routes.

require_role_or_api(*roles) factory in dependencies.py chains to get_current_user_or_api. 10 unit tests in test_commands_bearer_auth.py proving Bearer acceptance, cookie acceptance, role rejection, no-auth rejection, invalid-Bearer rejection.

### EXT-12 — User guide for browser extension
- Status: validated
- Class: quality-attribute
- Source: standing requirement
- Primary Slice: M014/S05
- Acceptance: docs/guide/ has a chapter covering extension installation (Chrome + Firefox), configuration, capture workflow, auto-population, schema.org, context menu, relationship picker, keyboard shortcut, and troubleshooting.

Chapter 32 (32-browser-extension.md) with 12 sections, 25 headings. README TOC updated. 2 glossary entries (API Token, Browser Extension). Navigation chain Ch 31 → Ch 32 → Appendix A.

### EXT-13 — E2E tests for extension capture flow
- Status: validated
- Class: quality-attribute
- Source: standing requirement
- Primary Slice: M014/S05
- Acceptance: Playwright E2E tests exercise the capture flow against Docker stack: options configuration, type loading, SHACL form rendering, object save, persistence verification.

e2e/tests/25-extension/extension-capture.spec.ts with 3 serial tests. Custom persistent context fixture in e2e/fixtures/extension.ts. Chromium-only (Firefox lacks --load-extension support in Playwright).

### EXT-14 — Badge shows context count after page load, cached per URL
- Status: partial
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M015/S01
- Acceptance: Extension badge displays the count of related SemPKM objects after page load. Results cached per URL to avoid redundant queries.
- Validation: Partially validated — badge text not accessible via Playwright (chrome.action.getBadgeText unavailable from test context). Badge set from same pipeline as sidebar results (proven by E2E test 2). Badge-setting code verified by review of service-worker.js _setBadge().

### EXT-15 — Sidebar opens via Alt+K showing grouped results from context query
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M015/S01
- Acceptance: Alt+K opens the knowledge sidebar showing results from the context query, grouped by match type (URL match, keyword match).
- Validation: E2E test "sidebar shows context results for matching URL" — sidebar renders grouped .type-group sections with .result-card elements containing seed Note title.

### EXT-16 — Open action navigates to SemPKM object in new tab
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M015/S01
- Acceptance: Clicking "Open" on a sidebar result opens the SemPKM object in a new browser tab.
- Validation: E2E test "Open action creates new tab pointing to SemPKM object" — clicking .action-open creates new context page with URL containing /browser/objects/ and seed Note IRI.

### EXT-17 — Link to this page action creates schema:url edge
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M015/S01
- Acceptance: Clicking "Link to this page" on a sidebar result creates a schema:url edge between the object and the current page URL.
- Validation: E2E test "Link to this page creates schema:url edge" — linkToPage message via service worker, toast confirms success, SPARQL verifies sempkm:Edge with schema:url predicate.

### EXT-18 — Add Evidence action captures highlighted text and creates linked Evidence object
- Status: partial
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M015/S01
- Acceptance: Clicking "Add Evidence" captures highlighted text from the page and creates a linked Evidence object in SemPKM.
- Validation: Partially validated — evidence capture requires content script text selection, hard to automate in persistent context. Code review confirms implementation in sidebar.js and service-worker.js addEvidence handler.

### EXT-19 — Auto-context toggle in settings controls badge/check behavior
- Status: validated
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M015/S03
- Acceptance: Options page has autoCheckContext toggle that enables/disables automatic context checking and badge display on page load.
- Validation: E2E test "settings round-trip for context overlay options" — #auto-check-context, #context-check-delay, #context-timeout exist, accept values, persist through save+reload.

### EXT-20 — URL→results cache (LRU, max 100) in service worker memory
- Status: partial
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M015/S01
- Acceptance: Service worker maintains an LRU cache (max 100 entries) mapping URLs to context query results to avoid redundant API calls.
- Validation: Partially validated — cache exercised implicitly by E2E tests. 23 unit tests in extension/tests/ prove LRU eviction, max entries, and timestamp ordering.

### EXT-21 — Cross-browser support (Chrome Side Panel + Firefox sidebar_action)
- Status: partial
- Class: core-capability
- Source: design (BROWSER-EXTENSION-DESIGN.md)
- Primary Slice: M015/S01
- Acceptance: Knowledge sidebar uses Chrome Side Panel API on Chrome and sidebar_action on Firefox, with feature detection for cross-browser compatibility.
- Validation: Partially validated — Chromium E2E tests pass with persistent context. Firefox manifest.json verified by syntax check in S01. Firefox sidebar_action not E2E tested (Playwright lacks Firefox extension loading).

### SYNC-01 — Linear OAuth and API key authentication
- Status: validated
- Class: core-capability
- Source: design (M016-ROADMAP.md)
- Primary Slice: M016/S01
- Acceptance: User authenticates with Linear via OAuth or API key. Connection verified by querying Linear viewer endpoint. Both auth methods store credentials via StateClient.

OAuth helpers and API key auth implemented with 39 unit tests. E2E test connects via API key through app proxy. OAuth code exchange and callback route implemented and tested.

### SYNC-02 — Pull sync (Linear issues to bpkm:Task)
- Status: validated
- Class: core-capability
- Source: design (M016-ROADMAP.md)
- Primary Slice: M016/S02
- Acceptance: User selects a Linear team/project, triggers poll, and issues appear as correctly-mapped bpkm:Task objects with status, priority, assignee, labels, due date, effort, and external link.

pull_sync() creates/updates bpkm:Task objects with correct field mapping for all mappable fields. 81 unit tests cover mapping, matching, sync logic. E2E test verifies tasks appear via SPARQL after sync.

### SYNC-03 — Push sync (SemPKM changes to Linear)
- Status: validated
- Class: core-capability
- Source: design (M016-ROADMAP.md)
- Primary Slice: M016/S03
- Acceptance: User changes a task's status in SemPKM, triggers push, and the change appears in Linear. Loop prevention ensures pushed changes are not re-imported.

push_sync() detects changed tasks via SPARQL, reverse-maps properties, executes issueUpdate mutations. Loop prevention via lastSyncedAt comparison. 69 unit tests.

### SYNC-04 — Settings UI (team selection, sync direction, poll interval)
- Status: validated
- Class: core-capability
- Source: design (M016-ROADMAP.md)
- Primary Slice: M016/S03
- Acceptance: Settings page allows team/project selection, sync direction toggle (pull-only/bidirectional), poll interval configuration, and manual Sync Now button.

Full settings control panel with team checkboxes, direction radios, interval dropdown, Sync Now button. All controls persist via StateClient and POST routes. E2E test configures settings through UI.

### SYNC-05 — Admin sync history
- Status: validated
- Class: core-capability
- Source: design (M016-ROADMAP.md)
- Primary Slice: M016/S03
- Acceptance: Admin detail page shows sync run history with success/failure, object counts, and last sync time.

Platform scheduler Task History shows push-changes and poll-tasks run history. Settings page sync stats section shows last sync time, result counts, errors.

### SYNC-06 — Person matching (assignee email lookup)
- Status: validated
- Class: core-capability
- Source: design (M016-ROADMAP.md)
- Primary Slice: M016/S02
- Acceptance: Assignee emails resolved via SPARQL lookup (foaf:mbox, crm:email). Person created on miss with email-derived slug and title.

PersonMatcher with SPARQL lookup, command creation, in-memory LRU cache. 12 unit tests.

### SYNC-07 — Provider icon and external link on synced tasks
- Status: validated
- Class: core-capability
- Source: design (M016-ROADMAP.md)
- Primary Slice: M016/S02
- Acceptance: Synced tasks have bpkm:externalUrl (Linear issue URL) and bpkm:externalUuid (Linear issue UUID) for provider attribution.

build_task_properties() stores both external URL and UUID during pull sync. 49 field mapper unit tests.

### JIRA-01 — ADF→Markdown conversion
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S01
- Acceptance: Jira ADF documents convert to Markdown covering ~12 common node types (paragraph, heading, bulletList, orderedList, codeBlock, blockquote, table, text with marks, mention, inlineCard, mediaGroup, rule).

95 ADF converter unit tests prove all 12 node types convert correctly with nested structures and inline formatting marks.

### JIRA-02 — Markdown→ADF reverse conversion
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S01
- Acceptance: SemPKM Markdown converts back to Jira ADF JSON for push sync (paragraphs, headings, lists, code blocks, links, blockquotes, rules with inline formatting).

markdown_to_adf() handles the Markdown subset SemPKM produces. Proven by unit tests in S01.

### JIRA-03 — statusCategory-based status normalization
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S01
- Acceptance: Status mapping uses statusCategory.key (new→todo, indeterminate→in-progress, done→done), not custom status names. Original status.name stored in bpkm:externalStatus.

STATUS_MAP proven by 5 direct tests + 9 round-trip tests. Pull sync uses statusCategory.key for all status mapping.

### JIRA-04 — Priority mapping
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S01
- Acceptance: Jira priority names (Highest/Critical/Blocker→critical, High→high, Medium→medium, Low/Lowest/Trivial→low) map correctly with reverse maps for push.

PRIORITY_MAP covers 8 Jira names → 4 bpkm values with REVERSE_PRIORITY_MAP. Proven by unit tests.

### JIRA-05 — Jira REST API client
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S01
- Acceptance: JiraClient with search_issues (JQL, pagination), get_issue, update_issue, get_projects, get_user with error hierarchy and auth header construction.

Full client with pagination, error hierarchy (JiraApiError, JiraAuthError, JiraNotFoundError, JiraRateLimitError). Unit tested in S01.

### JIRA-06 — API token authentication
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S01
- Acceptance: User enters email + API token + site URL. Credentials stored via StateClient. Basic auth header constructed as base64(email:token). Connection verified via GET /myself.

Email+token credential management with masking and connection verification. 3-field form in connect.html.

### JIRA-07 — Person matching (assignee resolution)
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S01
- Acceptance: Jira accountId resolved via extra API call to GET /user, then SPARQL lookup for existing Person/Contact. Person created on miss. LRU cache per sync run.

5-step resolution cascade with cache and graceful API failure handling. Unit tested in S01.

### JIRA-08 — Pull sync (Jira issues → bpkm:Task)
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S02
- Acceptance: User triggers sync and Jira issues appear as bpkm:Task objects with Markdown descriptions, correct status/priority/assignee, sprint as taskGroup, components and labels as tags.

pull_sync() creates Task objects with correct field mapping, ADF→Markdown body conversion, assignee resolution via PersonMatcher. 95 unit tests with mocked clients.

### JIRA-09 — Epic→Milestone mapping
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S02
- Acceptance: Jira Epics (issuetype.name="Epic") create bpkm:Milestone objects. Child issues linked to parent milestone via edges.

Epics detected via issuetype.name, converted to Milestone objects via build_milestone_properties, child tasks linked via edge creation. 8 dedicated unit tests.

### JIRA-10 — Push sync (SemPKM → Jira)
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S03
- Acceptance: User edits task title/description/priority in SemPKM, changes push back to Jira via REST API PUT. Loop prevention via lastSyncedAt. No status transitions (D237).

push_sync with SPARQL change detection, reverse field mapping, Markdown→ADF description conversion, Jira API update. 53 new unit tests. Loop prevention via lastSyncedAt.

### JIRA-11 — Issue links (Blocks→dependsOn)
- Status: validated
- Class: core-capability
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S03
- Acceptance: Jira issue links of type "Blocks" create bpkm:dependsOn edges between tasks. Inward-only dedup prevents duplicate edges.

_process_issue_links Phase 4 creates bpkm:dependsOn edges from "Blocks" links. Inward-only dedup per D240. Per-link error isolation.

### JIRA-12 — E2E tests and user guide
- Status: validated
- Class: quality-attribute
- Source: design (M023-ROADMAP.md)
- Primary Slice: M023/S04
- Acceptance: Mock Jira REST API server in Docker with selftest. Playwright E2E test covers install → configure → sync → verify lifecycle. Chapter 36 user guide documents Jira sync with field mapping tables.

Mock Jira REST API server (12-check selftest). Playwright E2E test (12 phases). Chapter 36 user guide (383 lines, field mapping tables, statusCategory explanation, ADF conversion notes). README TOC, 3 glossary entries, appendix-a JIRA_API_URL, navigation chain Ch 35 → Ch 36 → Appendix A.

### MON-01 — Monday.com API token authentication
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S01
- Acceptance: User enters API token, stored via StateClient, verified via `{ me { id name email } }` GraphQL query. Connection status shows username and masked token preview.

31 auth unit tests prove API token storage, verification via me query, masked display, connection status dict. Auth header is bare `Authorization: <api_key>` (no Basic/Bearer prefix).

### MON-02 — Board discovery and selection
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S01
- Acceptance: After authentication, user sees their boards with selection checkboxes. Board columns discovered with type metadata via `get_board_columns()`.

64 client unit tests prove get_boards(), get_board_columns() with column type metadata. Board selection UI in connect_status.html with checkboxes and column discovery.

### MON-03 — Column mapping configuration
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S02
- Acceptance: User configures which Monday.com columns map to which bpkm properties via type-filtered dropdowns. Per-board mapping stored as JSON in settings.

107 column mapping unit tests prove COLUMN_TYPE_COMPATIBILITY filtering, per-board mapping save/load, route handler logic, error paths.

### MON-04 — Status label mapping
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S02
- Acceptance: User maps Monday.com custom status labels (e.g., "Working on it") to bpkm:taskStatus enum values (e.g., "in-progress").

Column mapping tests prove settings_str JSON parsing discovers Monday.com labels, save-label-mapping stores status_label_mapping dict per board.

### MON-05 — Priority label mapping
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S02
- Acceptance: User maps Monday.com custom priority labels to bpkm:taskPriority enum values.

Column mapping tests prove priority label discovery and mapping to bpkm:taskPriority enum values, stored in label_mapping_{board_id}.

### MON-06 — Pull sync (Monday.com items → bpkm:Task)
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S02
- Acceptance: User triggers sync and Monday.com items appear as bpkm:Task objects with correct field values derived from the user-configured column mapping.

106 sync engine unit tests prove pull_sync creates/updates bpkm:Task objects with correct field values from stored column mapping, two-phase bulk create, per-item error isolation.

### MON-07 — Groups as taskGroup
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S02
- Acceptance: Monday.com groups appear as taskGroup values on synced tasks. Group title sourced from item.group structural metadata, not column_values.

Sync engine tests prove group title from item["group"]["title"] mapped to bpkm:taskGroup property per D243.

### MON-08 — Subitems as parentTask
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S02
- Acceptance: Monday.com subitems appear as separate bpkm:Task objects with bpkm:parentTask edge linking to parent task.

Sync engine tests prove get_subitems() fetches subitems with parent_item_id augmentation, Phase 3 creates bpkm:parentTask edges.

### MON-09 — Push sync (SemPKM → Monday.com)
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S03
- Acceptance: User edits a task in SemPKM and changes push back to Monday.com via change_multiple_column_values mutations with correct per-column-type JSON format.

53 push sync unit tests prove SPARQL change detection, reverse column mapping via build_reverse_column_values(), change_multiple_column_values mutation, lastSyncedAt update, per-task error isolation.

### MON-10 — LoopGuard echo prevention
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S03
- Acceptance: LoopGuard prevents push→poll echo loops via in-memory TTL cache. Push marks item/column pairs; pull checks and skips echoed items within TTL window.

25 LoopGuard unit tests + 8 pull integration tests + 3 push-pull round-trip tests prove TTL cache prevents re-import of pushed changes. Module-level singleton shared between push and pull sync.

### MON-11 — Dependency edges
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S03
- Acceptance: Monday.com dependency column values create bpkm:dependsOn edges between tasks via linkedPulseIds JSON parsing.

19 dependency tests prove _extract_dependency() parses dependency column values, _process_dependencies() creates bpkm:dependsOn edge.create commands with per-dependency error isolation.

### MON-12 — Tags mapping
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S03
- Acceptance: Monday.com tag columns map to bpkm:tags. Tag IDs batch-resolved to names via get_tags() API per board.

Tag resolution tests prove tag IDs collected during per-item processing, batch-resolved via MondayClient.get_tags() per board, names substituted into task properties. API failure falls back to string IDs.

### MON-13 — Person matching
- Status: validated
- Class: core-capability
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S01
- Acceptance: Monday.com user IDs resolved to existing Person/Contact objects via SPARQL email lookup. Person created on miss with email-derived slug. LRU cache per sync run.

27 person matcher unit tests prove 5-step cascade: cache → email SPARQL → API fetch → externalId fallback → create person. Numeric user_id stored as string for SPARQL compatibility.

### MON-14 — E2E tests and mock server
- Status: validated
- Class: quality-attribute
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S04
- Acceptance: Mock Monday.com GraphQL server in Docker with selftest. Playwright E2E test covers install → auth → column mapping → sync → verify → push lifecycle.

Mock Monday.com GraphQL server (697 lines, 12-check selftest, 10 query shapes). Playwright E2E test (13 phases, 372 lines). Docker compose mock-monday service with MONDAY_API_URL env var. mondaySync selector block (14 selectors).

### MON-15 — User guide
- Status: validated
- Class: quality-attribute
- Source: design (M024-ROADMAP.md)
- Primary Slice: M024/S04
- Acceptance: Chapter 37 user guide documents Monday.com setup, column mapping walkthrough, label mapping, LoopGuard, and troubleshooting.

Chapter 37 (393 lines) with column mapping type compatibility table, status/priority label mapping, LoopGuard echo prevention, groups/subitems/dependencies, troubleshooting. README TOC, index.html sidebar, guide.html in-app page all updated. Appendix A MONDAY_API_URL entry. 3 glossary entries (Column Mapping, LoopGuard, Monday.com Sync).

### DEMO-01 — Anonymous workspace access without login
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S01
- Acceptance: Anonymous visitor navigates to demo instance URL and sees the workspace immediately — no login page, no setup wizard, no redirect.

DEMO_MODE=true env var makes get_current_user return synthetic guest user (id=00000000-..., email=demo@sempkm.app, role=guest). /api/auth/status returns setup_complete=true in demo mode. E2E Playwright test proves fresh browser hits /browser/ and sees workspace.

### DEMO-02 — Read-only enforcement via nginx
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S01
- Acceptance: All write HTTP methods (POST/PUT/DELETE/PATCH) return 403 JSON error at the nginx layer for all routes except health check and auth status.

nginx.demo.conf uses error_page 495 + @read_only named location to return 403 {"error": "Demo instance is read-only"} with application/json Content-Type. E2E Playwright test proves POST/PUT/DELETE/PATCH on multiple endpoints return 403.

### DEMO-03 — Sample data with cross-model edges and validation triggers
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S02
- Acceptance: 30-50 interconnected sample objects across 4 Mental Models (basic-pkm, CRM, zettelkasten, research) are visible in the explorer, graph, and table views. Cross-model edges connect objects across model boundaries. Validation warnings appear on seed data (overdue task, stale contact, unprocessed fleeting note).

scripts/seed-demo-data.py installs 3 additional models and creates 12 cross-model edges across all 5 model pairs + 10 rich markdown bodies. SPARQL verification confirms 74 objects, 4 models, 12 edges, 10 bodies. Idempotent re-runs confirmed. Browser-level visibility verified by E2E Playwright test (demo-full-flow.spec.ts test 1 confirms explorer sidebar has items, test 4 confirms dashboard renders with data).

### DEMO-04 — Demo tour completes 7 steps without errors
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S03
- Acceptance: 7-step Driver.js tour starts on fresh anonymous session, auto-navigates between views (explorer, graph, object, lint, canvas, dashboard, CTA), and completes with localStorage flag set. Tour handles htmx timing with 500ms navigation delays.

window.startDemoTour() in tutorials.js with 7 auto-navigating steps. Auto-start on first visit via workspace.html script block. localStorage sempkm_demo_tour_done flag set on completion. Custom event sempkm:demo-tour-done dispatched. E2E test demo-full-flow.spec.ts test 2 clicks through all tour steps and verifies localStorage flag.

### DEMO-05 — Pre-built demo dashboard renders with cross-view context filtering
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S03
- Acceptance: Demo dashboard with deterministic UUID (aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee) renders with sidebar-main layout and two view-embed blocks demonstrating cross-view context filtering.

Seed script Phase 4 creates DashboardSpec with deterministic UUID, sidebar-main layout, table+graph blocks. Tour step 6 opens dashboard via openDashboardTab(). E2E test demo-full-flow.spec.ts test 4 verifies dashboard tab opens and renders content.

### DEMO-06 — CTA banner visible after tour completion with install link
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S03
- Acceptance: Dismissible "Try SemPKM" CTA banner appears after tour completion with GitHub install link, rocket icon, and dismiss button. localStorage persistence prevents re-showing after dismissal.

Fixed-bottom .demo-cta-banner in workspace.html with slide-up animation. Shown on sempkm:demo-tour-done event (first visit) or on load when sempkm_demo_tour_done localStorage set (return visit). Dismiss sets sempkm_demo_cta_dismissed. E2E test demo-full-flow.spec.ts test 3 verifies CTA banner visibility and GitHub link presence.

### DEMO-07 — Docker Compose with SSL termination
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S04
- Acceptance: docker-compose.demo.yml deploys full demo stack with Caddy reverse proxy providing automatic HTTPS via Let's Encrypt. X-Robots-Tag: noindex prevents search engine indexing.

Caddyfile configures Caddy as host-level reverse proxy to Docker nginx on port 3902 with automatic Let's Encrypt HTTPS and X-Robots-Tag header. deploy-demo.sh includes DNS/SSL setup instructions.

### DEMO-08 — Periodic reset mechanism
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S04
- Acceptance: Automated reset script restores clean demo state via 5-phase cycle (down → build → health wait → seed → verify) designed for 6-hourly cron execution.

scripts/reset-demo.sh with set -euo pipefail, 120s health wait timeout, 5-phase progress output. Cron configuration documented in deploy-demo.sh. Log output to /var/log/sempkm-demo-reset.log.

### DEMO-09 — Health monitoring
- Status: validated
- Class: core-capability
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S04
- Acceptance: Health check endpoint (/api/health) documented for external uptime monitoring services. Used by both reset and deploy scripts for readiness probing.

Health endpoint documented in deploy-demo.sh for external monitoring (UptimeRobot, Healthchecks.io). Used by reset script for readiness detection with 120s timeout.

### DEMO-10 — User guide documentation
- Status: validated
- Class: quality-attribute
- Source: design (M025-ROADMAP.md)
- Primary Slice: M025/S04
- Acceptance: Chapter 38 documents complete demo deployment including DEMO_MODE configuration, docker-compose.demo.yml, seed script, Caddy SSL, periodic reset, CTA customization, health monitoring, and troubleshooting.

docs/guide/38-hosted-demo.md (~329 lines). README.md TOC entry, index.html sidebar entry, guide.html in-app button all updated. DEMO_MODE row in Appendix A. "Demo Mode" and "Hosted Demo" glossary entries in Appendix D. Navigation chain Ch 37 → Ch 38 → Appendix A.

### SITE-01 — Homepage rewrite with outcome-focused messaging
- Status: validated
- Class: core-capability
- Source: design (USER-CONVERSION-STRATEGY.md)
- Primary Slice: M026/S01
- Acceptance: Homepage leads with outcome-focused hero ("Build knowledge that doesn't decay"), not technology-first messaging. Shared CSS extracted. All content sections present.

docs/index.html fully rewritten (619 lines) with outcome-focused hero, persona selector, competitive comparison, domain kits, condensed features, dual CTAs. docs/styles.css shared design system (1109 lines). Browser-verified at 3 breakpoints.

### SITE-02 — Persona landing path pages
- Status: validated
- Class: core-capability
- Source: design (USER-CONVERSION-STRATEGY.md)
- Primary Slice: M026/S02
- Acceptance: 3 persona pages (from-obsidian, from-notion, fresh-start) with tailored messaging, feature comparisons, and CTAs specific to each audience.

docs/from-obsidian.html (536 lines), docs/from-notion.html (536 lines), docs/fresh-start.html (510 lines). All link to shared styles.css, have persona-specific SEO tags, replicate nav pattern.

### SITE-03 — Competitive positioning
- Status: validated
- Class: core-capability
- Source: design (USER-CONVERSION-STRATEGY.md)
- Primary Slice: M026/S01
- Acceptance: Comparison table shows SemPKM vs Obsidian/Notion/Tana/Capacities across 6+ capabilities.

6-capability × 5-tool comparison table on homepage. Persona-specific mini-comparisons on each landing page.

### SITE-04 — Mental Models explained as domain kits
- Status: validated
- Class: core-capability
- Source: design (USER-CONVERSION-STRATEGY.md)
- Primary Slice: M026/S01
- Acceptance: Mental Models framed as "domain kits" without requiring ontology knowledge. No ontology jargon above the fold.

8 "domain kit" mentions on homepage. 4 domain kit cards (Basic PKM, Personal CRM, Zettelkasten+, Research Workflow). No ontology jargon above the fold on any page.

### SITE-05 — Updated screenshots from current UI
- Status: validated
- Class: quality-attribute
- Source: design (M026-ROADMAP.md)
- Primary Slice: M026/S03
- Acceptance: Screenshots reflect current UI state, captured from running demo stack.

5 fresh screenshots from M025 demo stack dated 2026-03-20: workspace overview, explorer types, command palette, canvas, object read.

### SITE-06 — Mobile responsive and performance
- Status: validated
- Class: quality-attribute
- Source: design (M026-ROADMAP.md)
- Primary Slice: M026/S03
- Acceptance: All pages mobile-responsive at 375px, 768px, 1200px+. Lighthouse mobile ≥ 90.

Lighthouse default mobile audit 0.99 (FCP 1.6s, LCP 1.6s, TBT 0ms). Responsive verified at all 3 breakpoints with browser assertions.

### SITE-07 — SEO basics
- Status: validated
- Class: quality-attribute
- Source: design (M026-ROADMAP.md)
- Primary Slice: M026/S03
- Acceptance: Meta description, OG tags, structured data present on all pages.

Meta descriptions × 4, og:image with absolute URLs × 4, JSON-LD (Organization + WebSite @graph) × 4. All internal links verified working.

### PERF-02 — All 18 CDN dependencies replaced with locally served files
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S01

S01: 18 deps in package.json, vendor bundle produced, 37 manifest entries, all templates use conditional local/CDN blocks.

### PERF-03 — Build pipeline produces minified, content-hashed assets automatically via docker compose build
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S01

S01: esbuild build.js, manifest.json with 37 entries, multi-stage Dockerfile, 0.8s build time.

### PERF-04 — nginx serves gzip-compressed responses for CSS/JS/HTML/JSON/SVG
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S02

S02: gzip_static on for pre-compressed .gz siblings, gzip_proxied any for dynamic HTML, curl confirms Content-Encoding: gzip.

### PERF-05 — HTTP caching with immutable headers on hashed assets, no-cache with ETag on auth pages
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S02

S02: Cache-Control: public, max-age=31536000, immutable on /assets/; no-cache + ETag + 304 on auth pages; curl verified all 8 checks.

### PERF-06 — CSS code-splitting by route — admin pages load only shared CSS
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S03

S03: 19 templates override page_css block, curl confirms 0 workspace CSS links on admin pages, 5 on workspace pages.

### PERF-07 — Lighthouse Performance score on workspace page (desktop preset)
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S05

S05/T01: Median score 80 (range 74-81) desktop preset, up from estimated ~40-60 pre-M029. FCP 984ms, LCP 2585ms, TBT 15ms, CLS 0.094.

### PERF-08 — Backend response timing middleware with top-5 slowest endpoint report
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S04

S04: TimingMiddleware + /api/admin/timing-report endpoint, Server-Timing header, 20 unit tests pass.

### PERF-09 — Backend HTTP cache headers — ETag, conditional GET returning 304
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S04

S04: ConditionalGetMiddleware, weak ETags on JSON API GET responses, 304 Not Modified, 16 unit tests pass.

### PERF-10 — QUIC/HTTP/3 decision documented with rationale
- Status: validated
- Class: quality-attribute
- Source: design (M029-ROADMAP.md)
- Primary Slice: M029/S05

S05/T02: Decision D277 recorded — defer, nginx:stable-alpine lacks HTTP/3, minimal benefit for self-hosted single-user.

### LINT-08 — Validation pipeline fix (rules load, advanced=True)
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S01

S01: model_shapes_loader includes rules graphs, ValidationService passes advanced=True, Docker logs confirm rules loading, lint panel shows M011 warnings.

### LINT-09 — Comma-in-tags data quality rule
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 2 pytest tests. S04 E2E test verifies result appears after creating Note with comma-in-tags.

### LINT-10 — Empty body data quality rule
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 3 pytest tests (basic-pkm + zettelkasten). S04 E2E test verifies result appears.

### LINT-11 — Concept no definition data quality rule
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 2 pytest tests (positive + negative).

### LINT-12 — Titleless objects data quality rule
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 3 pytest tests with type-namespace scoping.

### LINT-13 — Orphan objects data quality rule
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 2 pytest tests (positive + negative).

### LINT-14 — Duplicate URL data quality rule
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 2 pytest tests (positive + negative).

### LINT-15 — Stale project data quality rule
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 2 pytest tests (positive + negative).

### LINT-16 — PPV broken chain: ActionItem no project
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 2 pytest tests (positive + negative).

### LINT-17 — PPV broken chain: Project no goal
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S02

S02: 2 pytest tests. ClaimNoRationaleValidationShape also added as bonus rule in research model.

### LINT-18 — Suppress lint results by rule type
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S03

S03: 59 unit tests. S04 E2E test suppresses CommaInTags and verifies results excluded.

### LINT-19 — Dismiss individual lint results
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S03

S03: 59 unit tests. S04 E2E test dismisses EmptyBody for specific object and verifies exclusion.

### LINT-20 — Named lint filter presets
- Status: validated
- Class: core-capability
- Source: design (M030-ROADMAP.md)
- Primary Slice: M030/S03

S03: 59 unit tests. S04 E2E test saves/applies preset, verifies restoration.

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
- Status: active
- Description: Interactive import flow for Notion workspace exports (ZIP first, API later). Databases → types, rows → objects, relations → edges, with dashboard/rollup/formula metadata preservation.
- Why it matters: Notion is the most common PKM tool users migrate from. Structured import preserves their knowledge graph.
- Source: user
- Primary owning slice: M027/S03
- Supporting slices: M027/S01, M027/S02
- Validation: S01 proves scanner (CSV parsing, ID stripping, type inference, relation detection — 31 unit tests) + upload/scan/results UI. S02+S03 will validate mapping and import execution.
- Notes: Full research at `.planning/notion-import-research.md`. Mirrors Obsidian wizard pattern. Activated from deferred by M027.

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
| NOTION-01 | core-capability | active | M027/S03 | M027/S01, M027/S02 | S01: 31 scanner tests + upload/scan/results UI |
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
| API-01 | core-capability | validated | M013/S01 | none | 10 unit tests + Docker curl — well-known JSON schema verified |
| API-02 | core-capability | validated | M013/S02 | none | 8 unit tests — types JSON array with icons/model attribution |
| API-03 | core-capability | validated | M013/S02 | none | 11 unit tests — shapes JSON with constraints/groups/helptext |
| API-04 | core-capability | validated | M013/S03 | none | 13 context-query unit tests + 5 SPARQL escape tests + 2 E2E tests — URL + keyword match, dedup, graceful degradation |
| API-05 | core-capability | validated | M013/S01 | none | 15 unit tests — dual-auth cookie + bearer paths |
| API-06 | core-capability | validated | M013/S01 | none | Docker curl — CORS headers + OPTIONS 204 |
| API-07 | core-capability | validated | M013/S01 | none | Docker curl — Authorization forwarded + nginx -t |
| API-08 | quality-attribute | validated | M013/S03 | none | Ch. 31 guide + 3 glossary entries |
| EXT-01 | core-capability | validated | M014/S01 | M014/S02 | popup type selector + save flow + E2E test 3 |
| EXT-02 | core-capability | validated | M014/S02 | none | shacl-renderer.js 10 property types + Node.js rendering tests + E2E test 2 |
| EXT-03 | core-capability | validated | M014/S03 | none | extractor.js + popup auto-fill + S03 unit tests 19/19 |
| EXT-04 | core-capability | validated | M014/S04 | none | reference-picker.js + two-step save + S04 verification |
| EXT-05 | core-capability | validated | M014/S03 | none | service-worker.js context menu handler + session storage bridge |
| EXT-06 | core-capability | validated | M014/S03 | none | schema-mapper.js type suggestion + property mapping + 19/19 unit tests |
| EXT-07 | core-capability | validated | M014/S01 | M014/S05 | options page + connection test + E2E test 1 |
| EXT-08 | core-capability | validated | M014/S05 | none | Alt+S in both Chrome + Firefox manifests |
| EXT-09 | core-capability | validated | M014/S01 | M014/S05 | toast notifications + connection dot + E2E test 3 |
| EXT-10 | core-capability | validated | M014/S05 | none | manifest.firefox.json + classic service worker |
| EXT-11 | core-capability | validated | M014/S01 | none | require_role_or_api + 10 unit tests |
| EXT-12 | quality-attribute | validated | M014/S05 | none | Ch. 32 guide + 2 glossary entries |
| EXT-13 | quality-attribute | validated | M014/S05 | none | 3 Playwright E2E tests + persistent context fixture |
| EXT-14 | core-capability | partial | M015/S01 | M015/S03 | badge from same pipeline as sidebar (E2E test 2); badge API not testable from Playwright |
| EXT-15 | core-capability | validated | M015/S01 | M015/S03 | E2E test "sidebar shows context results for matching URL" |
| EXT-16 | core-capability | validated | M015/S01 | M015/S03 | E2E test "Open action creates new tab pointing to SemPKM object" |
| EXT-17 | core-capability | validated | M015/S01 | M015/S03 | E2E test "Link to this page creates schema:url edge" + SPARQL verification |
| EXT-18 | core-capability | partial | M015/S01 | none | code review confirms implementation; content script selection not E2E testable |
| EXT-19 | core-capability | validated | M015/S03 | none | E2E test "settings round-trip for context overlay options" |
| EXT-20 | core-capability | partial | M015/S01 | none | cache implicitly exercised by E2E; 23 unit tests prove LRU logic |
| EXT-21 | core-capability | partial | M015/S01 | none | Chromium E2E passes; Firefox manifest syntax-checked; no Firefox E2E |
| SYNC-01 | core-capability | validated | M016/S01 | none | OAuth helpers + API key auth + 39 unit tests + E2E API key connect |
| SYNC-02 | core-capability | validated | M016/S02 | none | pull_sync() + 81 unit tests + E2E SPARQL verification |
| SYNC-03 | core-capability | validated | M016/S03 | none | push_sync() + reverse mapping + loop prevention + 69 unit tests |
| SYNC-04 | core-capability | validated | M016/S03 | none | settings page team/direction/interval/sync-now + E2E |
| SYNC-05 | core-capability | validated | M016/S03 | none | platform Task History + settings sync stats |
| SYNC-06 | core-capability | validated | M016/S02 | none | PersonMatcher SPARQL lookup + creation + 12 unit tests |
| SYNC-07 | core-capability | validated | M016/S02 | none | bpkm:externalUrl + bpkm:externalUuid in pull sync |
| JIRA-01 | core-capability | validated | M023/S01 | none | 95 ADF converter unit tests — all 12 node types |
| JIRA-02 | core-capability | validated | M023/S01 | none | markdown_to_adf() — paragraphs, headings, lists, code, links |
| JIRA-03 | core-capability | validated | M023/S01 | none | STATUS_MAP — 5 direct + 9 round-trip tests |
| JIRA-04 | core-capability | validated | M023/S01 | none | PRIORITY_MAP — 8 Jira names → 4 bpkm values |
| JIRA-05 | core-capability | validated | M023/S01 | none | JiraClient — JQL search, pagination, error hierarchy |
| JIRA-06 | core-capability | validated | M023/S01 | none | email+token auth — credential management + connection verify |
| JIRA-07 | core-capability | validated | M023/S01 | none | PersonMatcher — accountId resolution + LRU cache |
| JIRA-08 | core-capability | validated | M023/S02 | none | pull_sync — 95 unit tests with mocked clients |
| JIRA-09 | core-capability | validated | M023/S02 | none | Epic→Milestone — 8 dedicated unit tests |
| JIRA-10 | core-capability | validated | M023/S03 | none | push_sync — SPARQL change detection + reverse mapping + 53 tests |
| JIRA-11 | core-capability | validated | M023/S03 | none | Blocks→dependsOn — inward-only dedup + per-link isolation |
| JIRA-12 | quality-attribute | validated | M023/S04 | none | mock server (12 selftest) + E2E test (12 phases) + Ch 36 guide |
| GH-01 | core-capability | validated | M017/S01 | none | 15 unit tests + mock GitHub API + E2E app install |
| GH-02 | core-capability | validated | M017/S01 | none | 42 field mapper + 26 sync engine tests + mock GitHub API |
| GH-03 | core-capability | validated | M017/S02 | none | 32 unit tests + mock timeline API + edge creation |
| GH-04 | core-capability | validated | M017/S03 | none | 33 unit tests — push_sync pipeline + PATCH + loop prevention |
| GH-05 | core-capability | validated | M017/S03 | none | 15 unit tests — settings routes + template context |
| GH-06 | core-capability | validated | M017/S01 | none | 10 unit tests — email/login SPARQL lookup + creation + cache |
| GH-07 | quality-attribute | validated | M017/S04 | none | mock server (9 selftest) + E2E test (partial) + Ch 35 guide + glossary |
| EVENT-01 | core-capability | validated | M018/S01 | none | 22 offline tests — manifest, ontology, shapes, views, seed, pyshacl, enum constraints |
| GCAL-01 | core-capability | validated | M018/S02 | none | 23 auth unit tests + 5 proxy regression tests + full OAuth route handlers |
| GCAL-02 | core-capability | validated | M018/S02 | none | 12 client unit tests + calendar list UI with checkboxes + state persistence |
| GCAL-03 | core-capability | validated | M018/S03 | none | 64 field mapper tests + 36 sync engine tests — all property transforms + sync orchestration |
| GCAL-04 | core-capability | validated | M018/S03 | none | 11 person matcher tests — email SPARQL lookup + creation + cache |
| GCAL-05 | core-capability | active | none | none | design: M018-ROADMAP.md |
| GCAL-06 | core-capability | active | none | none | design: M018-ROADMAP.md |
| GCAL-07 | core-capability | validated | M018/S03 | none | 4 all-day detection tests + full-event integration tests |
| GCAL-08 | core-capability | validated | M018/S03 | S04 | 6 conference URL extraction tests — conferenceData + hangoutLink fallback |
| GCAL-09 | quality-attribute | active | none | none | design: M018-ROADMAP.md |
| MON-01 | core-capability | validated | M024/S01 | none | 31 auth unit tests — API token storage, verification, masked display |
| MON-02 | core-capability | validated | M024/S01 | none | 64 client tests — get_boards/get_board_columns with board selection UI |
| MON-03 | core-capability | validated | M024/S02 | none | 107 column mapping tests — type-filtered dropdowns, per-board mapping |
| MON-04 | core-capability | validated | M024/S02 | none | column mapping tests — status label discovery + bpkm:taskStatus mapping |
| MON-05 | core-capability | validated | M024/S02 | none | column mapping tests — priority label discovery + bpkm:taskPriority mapping |
| MON-06 | core-capability | validated | M024/S02 | none | 106 sync engine tests — pull_sync creates Task objects from stored mapping |
| MON-07 | core-capability | validated | M024/S02 | none | sync engine tests — group title from item.group → bpkm:taskGroup (D243) |
| MON-08 | core-capability | validated | M024/S02 | none | sync engine tests — subitems as separate Tasks with parentTask edges |
| MON-09 | core-capability | validated | M024/S03 | none | 53 push sync tests — change_multiple_column_values + reverse mapping |
| MON-10 | core-capability | validated | M024/S03 | none | 25 LoopGuard + 8 integration + 3 round-trip tests — echo prevention |
| MON-11 | core-capability | validated | M024/S03 | none | 19 dependency tests — bpkm:dependsOn edges from dependency columns |
| MON-12 | core-capability | validated | M024/S03 | none | tag resolution tests — batch ID→name via get_tags(), fallback to string IDs |
| MON-13 | core-capability | validated | M024/S01 | none | 27 person matcher tests — 5-step cascade with LRU cache |
| MON-14 | quality-attribute | validated | M024/S04 | none | mock server (12 selftest) + 13-phase E2E spec + Docker compose |
| MON-15 | quality-attribute | validated | M024/S04 | none | Ch 37 guide (393 lines) + 3 nav files + appendix + 3 glossary entries |
| DEMO-01 | core-capability | validated | M025/S01 | none | DEMO_MODE auth bypass + /api/auth/status guard + E2E Playwright test |
| DEMO-02 | core-capability | validated | M025/S01 | none | nginx.demo.conf error_page 495 + E2E Playwright test (POST/PUT/DELETE/PATCH → 403) |
| DEMO-03 | core-capability | validated | M025/S02 | M025/S03, M025/S04 | 74 objects, 4 models, 12 cross-model edges, 10 bodies — SPARQL verified + E2E Playwright test confirms browser visibility |
| DEMO-04 | core-capability | validated | M025/S03 | M025/S04 | 7-step Driver.js tour with auto-navigation + E2E click-through + localStorage flag verification |
| DEMO-05 | core-capability | validated | M025/S03 | M025/S04 | deterministic UUID dashboard with sidebar-main layout + E2E dashboard render verification |
| DEMO-06 | core-capability | validated | M025/S03 | M025/S04 | CTA banner with GitHub link + E2E visibility check |
| DEMO-07 | core-capability | validated | M025/S04 | none | Caddyfile with automatic HTTPS + deploy script DNS/SSL instructions |
| DEMO-08 | core-capability | validated | M025/S04 | none | reset-demo.sh 5-phase script with 120s health timeout + cron documentation |
| DEMO-09 | core-capability | validated | M025/S04 | none | /api/health endpoint documented for external monitoring |
| DEMO-10 | quality-attribute | validated | M025/S04 | none | Chapter 38 (~329 lines) + 3 nav files + appendix + 2 glossary entries |
| SITE-01 | core-capability | validated | M026/S01 | M026/S03 | docs/index.html rewritten with outcome-focused messaging + shared CSS |
| SITE-02 | core-capability | validated | M026/S02 | M026/S03 | 3 persona pages with tailored messaging + feature comparisons |
| SITE-03 | core-capability | validated | M026/S01 | none | 6×5 comparison table on homepage + persona mini-comparisons |
| SITE-04 | core-capability | validated | M026/S01 | none | "domain kits" framing, 8 mentions, no ontology jargon above fold |
| SITE-05 | quality-attribute | validated | M026/S03 | none | 5 fresh screenshots from demo stack dated 2026-03-20 |
| SITE-06 | quality-attribute | validated | M026/S03 | M026/S01 | Lighthouse 0.99 + responsive at 3 breakpoints |
| SITE-07 | quality-attribute | validated | M026/S03 | M026/S01 | meta descriptions + og:image (absolute) + JSON-LD on all 4 pages |
| PERF-02 | quality-attribute | validated | M029/S01 | none | 18 CDN deps replaced, vendor bundle, 37 manifest entries |
| PERF-03 | quality-attribute | validated | M029/S01 | none | esbuild build.js, manifest.json, multi-stage Dockerfile, 0.8s |
| PERF-04 | quality-attribute | validated | M029/S02 | none | gzip_static + gzip_proxied, curl confirms Content-Encoding: gzip |
| PERF-05 | quality-attribute | validated | M029/S02 | none | immutable 1yr on /assets/, no-cache + ETag on auth, 8 curl checks |
| PERF-06 | quality-attribute | validated | M029/S03 | none | 19 templates override page_css, 0 workspace CSS on admin pages |
| PERF-07 | quality-attribute | validated | M029/S05 | none | Lighthouse desktop 80 (range 74-81), FCP 984ms, LCP 2585ms, TBT 15ms |
| PERF-08 | quality-attribute | validated | M029/S04 | none | TimingMiddleware + timing-report endpoint + 20 unit tests |
| PERF-09 | quality-attribute | validated | M029/S04 | none | ConditionalGetMiddleware + weak ETags + 304 + 16 unit tests |
| PERF-10 | quality-attribute | validated | M029/S05 | none | D277 QUIC/HTTP/3 defer — nginx lacks HTTP/3, minimal benefit |
| LINT-08 | core-capability | validated | M030/S01 | none | Pipeline fix — rules load, advanced=True, Docker lint panel shows M011 warnings |
| LINT-09 | core-capability | validated | M030/S02 | M030/S04 | CommaInTagsValidationShape — 2 pytest + E2E test |
| LINT-10 | core-capability | validated | M030/S02 | M030/S04 | EmptyBodyValidationShape — 3 pytest + E2E test |
| LINT-11 | core-capability | validated | M030/S02 | none | ConceptNoDefinitionValidationShape — 2 pytest |
| LINT-12 | core-capability | validated | M030/S02 | none | TitlelessObjectValidationShape — 3 pytest |
| LINT-13 | core-capability | validated | M030/S02 | none | OrphanObjectValidationShape — 2 pytest |
| LINT-14 | core-capability | validated | M030/S02 | none | DuplicateUrlValidationShape — 2 pytest |
| LINT-15 | core-capability | validated | M030/S02 | none | StaleProjectValidationShape — 2 pytest |
| LINT-16 | core-capability | validated | M030/S02 | none | ActionItemNoProjectValidationShape — 2 pytest |
| LINT-17 | core-capability | validated | M030/S02 | none | ProjectNoGoalValidationShape — 2 pytest |
| LINT-18 | core-capability | validated | M030/S03 | M030/S04 | Suppress rule type — 59 unit tests + E2E |
| LINT-19 | core-capability | validated | M030/S03 | M030/S04 | Dismiss individual results — 59 unit tests + E2E |
| LINT-20 | core-capability | validated | M030/S03 | M030/S04 | Named presets — 59 unit tests + E2E |
| VIEW-08 | core-capability | validated | M031/S01 | M031/S07 | carousel removed, variant dropdown, 25 unit tests |
| VIEW-09 | core-capability | validated | M031/S01 | M031/S05,S07 | scope_query param + dropdown + graceful degradation, full-height views confirmed |
| VIEW-10 | core-capability | validated | M031/S02 | M031/S07 | unique tab IDs, scoped dedup, unscoped fresh, 13 unit tests |
| VIEW-11 | core-capability | validated | M031/S02 | M031/S07 | save/list/delete promoted views, toolbar button, my_views routing |
| VIEW-13 | core-capability | validated | M031/S05 | M031/S07 | .view-flex-column wrapper, flex:1 children, no fragile calc() |
| VIEW-14 | core-capability | validated | M031/S05 | M031/S07 | popovers on document.body, position:fixed, z-index:9999 |
| SPARQL-09 | enhancement | validated | M031/S05 | M031/S07 | triple-pattern detection, Table/Graph tab switcher, Cytoscape graph |
| SPARQL-10 | core-capability | validated | M031/S05 | M031/S07 | 28 specific sub-namespaces, vocabIriIndex, .sparql-vocab-pill |
| SPARQL-11 | enhancement | validated | M031/S05 | M031/S07 | reversePrefixMap from prefixCache, dynamic QName shortening |
| ONTO-04 | enhancement | validated | M031/S05 | M031/S07 | propDescription COALESCE, title attribute on property labels |
| ONTO-05 | enhancement | validated | M031/S05 | M031/S07 | flex column + calc(100vh-250px), no fixed min-height |
| ONTO-06 | enhancement | validated | M031/S05 | M031/S07 | edge hover popover with label, domain→range, description |
| SQ-01 | core-capability | validated | M031/S03 | M031/S07 | QUERIES explorer section, 18 template + 5 endpoint tests |
| SQ-02 | enhancement | validated | M031/S03 | none | canvas drag payload on query entries, template test coverage |
| SQ-03 | enhancement | validated | M031/S03 | none | VFS build_scope_filter + resolve_scope_query already working, 5 verification tests |
| VIEW-12 | core-capability | validated | M031/S04 | M031/S07 | SHACL sh:in scan, kanban_view.html, drag-drop status change, 15 unit tests |
| DBUIX-01 | enhancement | validated | M031/S06 | none | 13 field-help in dashboard builder, 6 in workflow builder |
| DBUIX-02 | enhancement | validated | M031/S06 | none | class-search + object-search endpoints, autocomplete widgets in both builders |
| DBUIX-03 | enhancement | validated | M031/S06 | none | renderer dropdown removed, auto-set via _wfUpdateRendererFromView + hidden input |
| DBUIX-04 | enhancement | validated | M031/S06 | none | seed.py idempotent, startup hook, 4 unit tests |

## Coverage Summary

- Active requirements: 25 (14 APP + 8 RSS + 3 GCAL)
- Validated: 265 (38 from M001 + 22 from M002 + 21 from M003 + 7 from M004 + 4 from M005 + 7 from M006 + 13 from M007 + 5 from M008 + 4 from M011 + 11 from M012 + 8 from M013 + 13 from M014 + 4 from M015 + 7 from M016 + 7 from M017 + 5 from M018 + 12 from M023 + 15 from M024 + 10 from M025 + 7 from M026 + 9 from M029 + 13 from M030 + 21 from M031 + 2 from other)
- Partial: 4 (EXT-14, EXT-18, EXT-20, EXT-21)
- Deferred: 6 (TYPE-03, TYPE-04, MCP-01, VIEW-06, VIEW-07, VFS-13)
- Out of scope: 3
- Unmapped active requirements: 25 (14 APP + 8 RSS + 3 GCAL — pending remaining milestones)
