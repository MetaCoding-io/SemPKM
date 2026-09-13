# SemPKM Feature Tour & Bug Hunt

**Purpose:** Walk through every major feature area together, verify it works, note UI issues and bugs, accumulate them into future milestone work.

**Process:** Start Docker stack → work through each section → you drive the UI, I verify/diagnose from the backend. Mark each item pass/fail/bug. At the end, we'll distill findings into concrete milestones.

**Stack:** `docker compose up -d` (port 4000 = UI, port 8001 = API)

---

## Pre-flight

- [ ] Docker stack starts cleanly (all 3 services healthy)
- [ ] Setup wizard completes (or already done)
- [ ] Login works (magic link flow)
- [ ] Basic health check (`/api/health` returns OK)

---

## 1. Mental Model Management

> Admin → Models page. Install, inspect, uninstall models.

- [x] **1.1** Navigate to Admin portal
- [x] **1.2** Install `basic-pkm` model from archive
- [x] **1.3** Install `business-planning` model
- [x] **1.4** Install `crm` model
- [x] **1.5** Install `zettelkasten` model
- [x] **1.6** Install `research` model
- [x] **1.7** Install `ppv` model
- [x] **1.8** Model detail page shows real stats + charts
- [ ] **1.9** Schema refresh works (POST without uninstall)
- [ ] **1.10** Uninstall a model (verify clean removal)

**Notes:**
```
```

---

## 2. Object CRUD

> Create, read, edit, delete objects of various types.

- [x] **2.1** Create a Note (basic-pkm) — form renders, save works
- [x] **2.2** Create a Project — verify all SHACL fields present
- [x] **2.3** Create a Concept — definition field, related concepts
- [x] **2.4** Create a Person — contact fields
- [x] **2.5** Create a Task — status, priority, due date, scheduled times
- [x] **2.6** Object read view renders (markdown body, properties)
- [x] **2.7** Flip to edit mode (CSS 3D card flip, no flicker)
- [x] **2.8** Edit properties — save persists
- [x] **2.9** Edit markdown body — save persists
- [x] **2.10** Delete object — confirmation, clean removal
- [x] **2.11** Edge creation (link two objects)
- [x] **2.12** Edge deletion
- [x] **2.13** Markdown rendering in body (headings, code, lists, links)
- [x] **2.14** Form advanced section (collapse/expand)

**Notes:**
```
```

---

## 3. Workspace & Navigation

> IDE-style workspace: tabs, sidebar, command palette, keyboard shortcuts.

- [x] **3.1** Sidebar navigation tree loads (explorer sections)
- [x] **3.2** Explorer mode dropdown works (by-type, by-hierarchy, by-tag, VFS)
- [x] **3.3** Click object in tree → opens in dockview tab
- [x] **3.4** Multiple tabs open simultaneously
- [x] **3.5** Tab close, tab switching
- [x] **3.6** Dockview drag to split (horizontal/vertical groups)
- [x] **3.7** Command palette (Ctrl+K) — search, actions
- [x] **3.8** Keyboard shortcuts (documented ones work)
- [x] **3.9** Named layouts — save and restore
- [x] **3.10** Personas — create, switch, verify layout persistence
- [x] **3.11** Sidebar panel drag-drop reordering
- [x] **3.12** Dark mode toggle (system/light/dark)
- [x] **3.13** Sidebar sections collapse/expand
- [x] **3.14** Bottom panel toggle (Ctrl+J) — SPARQL, Event Log, Copilot tabs

**Notes:**
```
```

---

## 4. Views & Data Browsing

> Table, cards, graph, kanban, calendar, timeline, map renderers.

- [x] **4.1** Table view — loads, columns correct, pagination
- [x] **4.2** Cards view — renders, flip animation
- [x] **4.3** Graph view (2D) — nodes, edges, layout
- [x] **4.4** Kanban view — columns from SHACL sh:in, drag cards
- [x] **4.5** Calendar view — tasks/events display, drag-to-reschedule
- [x] **4.6** Timeline/Gantt view — bars, dependencies, zoom
- [x] **4.7** Map view (if geo data exists)
- [x] **4.8** Generic views (any type → table/cards/graph)
- [x] **4.9** View filtering / scope select
- [x] **4.10** Column preferences (table) persist
- [x] **4.11** Save view / promoted views folder

**Notes:**
```
```

---

## 5. Business Planning Renderers

> Install business-planning model, test custom renderers.

- [x] **5.1** Quadrant view (e.g. SWOT, Eisenhower) — 2×2 grid renders
- [ ] **5.2** Drag-to-reclassify in quadrant
- [ ] **5.3** BMC (Business Model Canvas) 9-box poster
- [ ] **5.4** BMC inline editing
- [ ] **5.5** OKR progress bars
- [ ] **5.6** Decision Matrix weighted scoring
- [ ] **5.7** Extended frameworks (Porter, PESTLE, BSC, etc.)

**Notes:**
```
```

---

## 6. Spatial Canvas

> Canvas tab with Cytoscape.js graph exploration.

- [ ] **6.1** Open canvas (new session)
- [ ] **6.2** Add objects to canvas (drag from explorer or toolbar)
- [ ] **6.3** Canvas node resize (drag handles)
- [ ] **6.4** Property flip on canvas nodes
- [ ] **6.5** Live view/dashboard embeds on canvas
- [ ] **6.6** SPARQL query embed
- [ ] **6.7** Edge creation on canvas (wiki-link style)
- [ ] **6.8** Snap-to-grid, keyboard nav
- [ ] **6.9** Save/load canvas sessions

**Notes:**
```
```

---

## 7. SPARQL Console

> Bottom panel SPARQL tab with Yasgui.

- [ ] **7.1** Console loads, can type query
- [ ] **7.2** Execute SELECT query — results render
- [ ] **7.3** IRI pills in results (clickable → opens object tab)
- [ ] **7.4** Query history persists
- [ ] **7.5** Saved queries — save, load, share
- [ ] **7.6** Named queries as views (pin to explorer)

**Notes:**
```
```

---

## 8. Search

> Full-text search + command palette search.

- [ ] **8.1** Ctrl+K search finds objects by text
- [ ] **8.2** Search results show type, label, snippet
- [ ] **8.3** Fuzzy search toggle
- [ ] **8.4** Search from explorer

**Notes:**
```
```

---

## 9. Validation & Lint

> SHACL validation, lint dashboard, lint panel.

- [ ] **9.1** Create object with invalid data → validation fires
- [ ] **9.2** Lint panel shows violations in object tab
- [ ] **9.3** Global lint dashboard loads (filterable, sortable)
- [ ] **9.4** SSE auto-refresh on lint dashboard
- [ ] **9.5** Dismiss individual lint result
- [ ] **9.6** Suppress rule type
- [ ] **9.7** Named lint presets
- [ ] **9.8** Data quality rules fire (empty body, comma-in-tags, etc.)

**Notes:**
```
```

---

## 10. VFS / WebDAV

> Virtual filesystem browser and WebDAV mount.

- [ ] **10.1** VFS browser tab opens (model → type → objects tree)
- [ ] **10.2** File preview (markdown render of object body)
- [ ] **10.3** Breadcrumb navigation
- [ ] **10.4** Custom MountSpec (VFS scope dropdown, strategies)
- [ ] **10.5** VFS Settings page (API token, mount config)
- [ ] **10.6** WebDAV mount from OS file manager (if feasible to test)

**Notes:**
```
```

---

## 11. Importers

> Obsidian vault import, Notion import, RDF import.

- [ ] **11.1** Obsidian import — ZIP upload, scan, type mapping, preview, execute
- [ ] **11.2** Notion import — ZIP upload, scan, mapping, execute
- [ ] **11.3** RDF import — paste/upload, format detection, SHACL preview, import

**Notes:**
```
```

---

## 12. Apps Platform

> App lifecycle, admin monitoring, RSS reader.

- [ ] **12.1** Admin → Apps section shows installed apps
- [ ] **12.2** RSS Reader app loads
- [ ] **12.3** Add RSS feed subscription
- [ ] **12.4** Feed polling works (articles appear)
- [ ] **12.5** Article reader UI (split pane, typography)
- [ ] **12.6** OPML import
- [ ] **12.7** Star/unread toggle
- [ ] **12.8** Media Scheduler app (if applicable)

**Notes:**
```
```

---

## 13. Sync Apps

> Linear, GitHub, Jira, Monday.com, Google Calendar, Todoist, Outlook, CalDAV, Asana.

_These need API keys/OAuth to test fully. Test at minimum: settings UI loads, connect flow starts._

- [ ] **13.1** Linear Sync — settings page loads, fields present
- [ ] **13.2** GitHub Sync — settings page loads
- [ ] **13.3** Jira Sync — settings page loads
- [ ] **13.4** Monday.com Sync — settings page loads
- [ ] **13.5** Google Calendar — settings page loads
- [ ] **13.6** Todoist — settings page loads
- [ ] **13.7** Outlook Calendar — settings page loads
- [ ] **13.8** CalDAV — settings page loads
- [ ] **13.9** Asana — settings page loads

**Notes:**
```
```

---

## 14. AI Copilot

> Chat, SPARQL generation, object creation, personas. Needs LLM config.

- [ ] **14.1** Copilot tab opens (bottom panel)
- [ ] **14.2** LLM connection configured (Settings → LLM)
- [ ] **14.3** Chat message sends, streaming response renders
- [ ] **14.4** SPARQL query generated → approval flow
- [ ] **14.5** Object creation from chat
- [ ] **14.6** Conversation persistence (new, switch, history)
- [ ] **14.7** AI personas — switch, system prompt changes
- [ ] **14.8** Graph context injection (open an object, ask about it)

**Notes:**
```
```

---

## 15. Auth & Multi-User

> Passwordless auth, roles, invites, sessions.

- [ ] **15.1** Magic link login flow
- [ ] **15.2** Session persistence across browser refresh
- [ ] **15.3** Invite flow (owner invites member)
- [ ] **15.4** Member permissions (restricted access)
- [ ] **15.5** Settings page loads, user info correct
- [ ] **15.6** Logout works

**Notes:**
```
```

---

## 16. Identity & Federation

> WebID, IndieAuth, federation sync.

- [ ] **16.1** WebID profile page renders (`/users/{username}`)
- [ ] **16.2** Content negotiation (Turtle, JSON-LD, HTML)
- [ ] **16.3** IndieAuth metadata endpoint
- [ ] **16.4** Federation UI partials load

**Notes:**
```
```

---

## 17. Dashboards & Workflows

> Dashboard builder, workflow stepper.

- [ ] **17.1** Dashboard builder UI loads
- [ ] **17.2** Create a dashboard (grid layout, stat/chart/table blocks)
- [ ] **17.3** Dashboard renders in viewer
- [ ] **17.4** Cross-view context filtering works
- [ ] **17.5** Workflow builder UI loads
- [ ] **17.6** Create a workflow (steps, actions)
- [ ] **17.7** Workflow stepper runs

**Notes:**
```
```

---

## 18. Inference & Ontology

> OWL inference, SHACL-AF rules, ontology viewer.

- [ ] **18.1** Ontology viewer — TBox, ABox, RBox tabs
- [ ] **18.2** User-created class (name, icon, parent, properties)
- [ ] **18.3** User-created property
- [ ] **18.4** OWL inference fires (inverse properties materialized)
- [ ] **18.5** SHACL-AF rules fire (e.g. overdue task warning)

**Notes:**
```
```

---

## 19. Event Log

> Event timeline, diffs, undo.

- [ ] **19.1** Event log tab shows recent events
- [ ] **19.2** Event detail (inline diff)
- [ ] **19.3** Filter by type/user
- [ ] **19.4** Undo via compensating event

**Notes:**
```
```

---

## 20. Docs & Guided Tours

> User guide, Driver.js tours.

- [ ] **20.1** Docs page loads (`/guide`)
- [ ] **20.2** Driver.js welcome tour starts
- [ ] **20.3** User guide chapters render correctly

**Notes:**
```
```

---

## 21. General UI Quality

> Cross-cutting polish, performance, accessibility.

- [ ] **21.1** Page load speed (subjective)
- [ ] **21.2** Dark mode renders correctly everywhere
- [ ] **21.3** No layout shifts on load
- [ ] **21.4** Mobile/responsive (if expected to work)
- [ ] **21.5** Console errors (check DevTools)
- [ ] **21.6** Broken images or icons
- [ ] **21.7** Tooltip/helptext quality

**Notes:**
```
```

---

## Bug & Issue Log

> Running list of everything found during the tour. Each gets a severity and category.

| # | Severity | Category | Section | Description | Repro Steps |
|---|----------|----------|---------|-------------|-------------|
| 1 | 🔴 Broken | infra | Pre-flight | SQLite "attempt to write a readonly database" after `docker compose up --build` — volume data owned by root:root, process runs as uid 1000 (sempkm). Dockerfile `chown` only applies at image build, not to existing volume data. | `docker compose down && docker compose up --build -d` → API crash loop |
| 2 | 🔴 Broken | infra | Pre-flight | nginx frontend crashes with `setgid(101) failed (Operation not permitted)` — `security_opt: no-new-privileges` in docker-compose.yml prevents nginx worker setgid. Fixed by removing security_opt from frontend service. | `docker compose up -d` after a fresh build → frontend container exits immediately |
| 3 | 🟢 Polish | model-mgmt | 1 | Install UI should auto-discover models from `/app/models/` and show installable list (like Applications page does for apps) instead of requiring user to type a filesystem path. | Admin → Mental Models → Install field |
| 4a | 🔴 Broken | model-mgmt | 1 | Model installer only loads a fraction of SHACL shapes — business-planning has 33 shapes on disk but only 2 (Eisenhower) made it into the triplestore (154 triples vs expected thousands). JSON-LD parsing likely drops shapes after the first block. | Install business-planning → query shapes graph → only 2 NodeShapes |
| 4b | 🟡 Bug | model-mgmt | 1 | Model detail page has no tab/section to view SHACL shapes. Add a "Shapes" tab showing all shapes with their properties. | Click into any model → no shapes section |
| 5 | 🟢 Polish | model-mgmt | 1 | Type references (including xsd types) need consistent styling — color, icon (use model-declared icon when available). Currently unstyled plain text. | Model detail page → types listed without visual distinction |
| 6 | 🟡 Bug | model-mgmt | 1 | Analytics/growth charts show incorrect data for most new types — growth not displayed correctly. | Model detail → stats charts |
| 7 | 🟢 Polish | model-mgmt | 1 | Model detail page has too much whitespace on right side. Should use centered layout. Relationship map should use 100% width and height. | Model detail page layout |
| 8 | 🟡 Bug | model-mgmt | 1 | Inference Settings UI is confusing — no separation between items in "in this model" section. Needs unordered list formatting, better visual separation, and tooltip help text explaining each line. | Model detail → Inference section |
| 9 | 🟢 Polish | model-mgmt | 1 | Model detail page is laggy to load — API calls likely heavy. Needs performance investigation. | Click into any model → noticeable delay |
| 10 | 🟡 Bug | workspace | 3 | Bottom panel EVENT LOG tab shows stale placeholder "Event Log Explorer — coming in Phase 16" — event log was built in M012. | Object Browser → bottom panel → EVENT LOG tab |
| 11 | 🟢 Polish | workspace | 3 | Explorer shows "Project Shape", "Person Shape" etc. — the " Shape" suffix is noisy. Should show just the type name. | Object Browser → OBJECTS section |
| 12 | 🟡 Bug | workspace | 3 | OBJECTS dropdown is poorly organized — raw model IDs with `(by-type)` suffix, VFS Mounts 404s, no visual grouping between generic modes and per-model filters. | Object Browser → OBJECTS dropdown |
| 13 | 🟢 Polish | object-crud | 2 | Object view is bland/generic — no distinctive color, no type-colored accents, flat gray/white palette. Needs visual identity and warmth. | Create any object → view it |
| 14 | 🟢 Polish | object-crud | 2 | Type badge shows raw namespace IRI (`sempkm:model:basic-pkm:Note`) — should be a styled pill with type icon and just the type name "Note". | Object header bar |
| 15 | 🟢 Polish | object-crud | 2 | Body editor uses code-editor line numbers — feels wrong for note-taking. Should feel like a writing surface, not an IDE. | Object body area |
| 16 | 🟢 Polish | object-crud | 2 | "2 properties" link in header is cryptic — unclear what properties, why 2. Needs better labeling or context. | Object header bar |
| 17 | 🟢 Polish | object-crud | 2 | Right panel sections (RELATIONS, LINT, COMMENTS, INBOX, COLLABORATION) all have equal visual weight, most are empty — wall of "nothing here" messages. Needs smarter collapse/hide when empty. | Object right panel |
| 18 | 🟢 Polish | object-crud | 2 | Form helptext has too much vertical spacing — wastes screen real estate. | Create object form |
| 19 | 🟢 Polish | object-crud | 2 | Read view properties table — no visual distinction between property name and value (same font, weight, color). Needs bolder labels or muted values. No zebra striping or separators. | Object read view → properties |
| 20 | 🟢 Polish | object-crud | 2 | Read view has no `?` tooltip icons on properties — edit form has them but read view doesn't. Should show helptext in both modes. | Object read view vs edit form |
| 21 | 🟢 Polish | object-crud | 2 | Edit form inputs are fixed-width (~55% of panel) — right half is dead white space. Inputs should be responsive to panel width. Alignment feels off. | Object edit form |
| 22 | 🟢 Polish | object-crud | 2 | Edit form section headers (Content, Relationships, Metadata) have tiny orange squares — don't create strong visual grouping. Need more prominent section separation. | Object edit form |
| 23 | 🟢 Polish | ui-quality | 21 | Lists and panels across the entire Object Browser lack visual borders, zebra striping, or subtle separators — properties table, relations panel, lint results, comments, explorer tree items all blend together. Needs a systemic pass. | All panels in Object Browser |
| 24 | 🟡 Bug | workspace | 3 | Command palette (ninja-keys) has a scroll jump bug — moving mouse slowly from top to bottom, near "Create Project" the list scrolls away. Likely a hover-highlight layout shift or overflow issue inside the shadow DOM. | F1 → move mouse slowly down the command list |
| 25 | 🟡 Bug | object-crud | 2 | Relationship autocomplete dropdowns don't dismiss on click-outside or Escape — must click another element to close. Affects all relation search fields (Participants, Notes, Tasks, Milestones, About Concepts, etc.). | Edit any object → click a relation search field → type → try to dismiss |
| 26 | 🟡 Bug | object-crud | 2 | Tag autocomplete dropdown gets clipped/cutoff by the Metadata section container boundary. Dropdown renders inside parent instead of escaping to document.body. Same stacking context issue as dockview popovers (KNOWLEDGE.md). | Edit object → Metadata → Tags → type "garden" → dropdown is cut off at bottom |
| 27 | 🟡 Bug | workspace | 3 | URL never changes while browsing — no browser history integration. Can't bookmark, share, or use back/forward to navigate. Closing a tab is irreversible — no undo, no "Reopen closed tab" in command palette. | Open objects, switch tabs, close a tab → URL stays at /browser/, no way to recover |
| 28 | 🟢 Polish | workspace | 3 | Explorer OBJECTS panel entries should show hover-reveal action buttons — `?` tooltip with shape/type description from ontology, and a delete button for object instances. | Hover over entries in explorer → no actions appear |
| 29 | 🔴 Broken | object-crud | 2 | Object deletion does not exist — no `object.delete` command, no delete button in UI, no command palette entry. There is no way to delete an object. Need: backend command handler (event-sourced soft delete or hard delete), UI button on object header and explorer hover, confirmation dialog. | Try to delete any object → no mechanism exists |
| 30 | 🔴 Broken | object-crud | 2 | Save does a full replace instead of diffing — every save sends ALL fields as if new, even unchanged ones. Causes: (1) unnecessary `body.set` events when body wasn't edited, (2) event log shows `(new)` for properties that already existed (e.g. Type showing as `(new) → observation` when it was already observation), (3) pollutes event history with noise, making real changes hard to find. The editor.js save should diff current vs original values and only send changed fields. | Edit "Be Useful" → only add About Concepts → save → event log shows body.set + all properties as (new) |
| 31 | 🟢 Polish | workspace | 3 | Tab styling — tab colors too close to background color, not prominent enough. Tabs don't stand out visually. | Multiple tabs open → hard to distinguish active vs inactive |
| 32 | 🔴 Broken | ui-quality | 21 | Severe backend performance issue — opening an object takes 4+ seconds. Network tab shows "Waiting for server response" at 4.07s on individual requests. Opening one object triggers a cascade of htmx partial loads (object tab, comments, inbox, lint, relations, shapes) each hitting the API with slow SPARQL queries. Needs performance profiling and optimization (query caching, parallel loading, lazy loading of secondary panels). | Open any object → 4+ second delay, visible in Network tab |
| 33 | 🟡 Bug | workspace | 3 | Persona "Create New" doesn't work from command palette — requires typing a name in the search field first then selecting the action, which is not discoverable. No modal/dialog prompt for the name. | F1 → Persona: Create New → nothing happens unless you typed a name first |
| 34 | 🟡 Bug | workspace | 3 | Layout "Save As" has same broken UX as persona create — "type a name above, then select this item to save" is not discoverable. Should show an input dialog. | F1 → Layout: Save As → same issue |
| 35 | 🟢 Polish | workspace | 3 | Personas vs Named Layouts distinction is unclear to users. Personas = layout + sidebar positions + explorer mode (server-stored). Layouts = dockview panel arrangement only (localStorage). Consider merging into a single "Workspace" concept or at minimum clarifying the difference in UI. | F1 → see both Persona and Layout sections |
| 36 | 🔴 Broken | views | 4 | Generic Table View shows "No objects found" even with "All Types" selected — objects exist (visible in explorer + just created). The generic view query is broken. | VIEWS → Table View → All Types selected → empty table |
| 37 | 🟢 Polish | views | 4 | Type filter pills are overwhelming — 37 pills across 4 rows, all with " Shape" suffix. Unscalable. Replace with a dropdown that only shows types present in the current query's result set. | Table View → type pills area |
| 38 | 🟢 Polish | views | 4 | Remove "View Variants" dropdown — concept is confusing and adds no clear value. The query/scope dropdown is sufficient. | Table View → "All Objects" variant dropdown |
| 39 | 🟢 Polish | views | 4 | View toolbar needs clearer separation between query filter (what universe of objects) and type filter (which types within that universe). Query dropdown should be primary, type dropdown secondary and smart-filtered. | Table View toolbar |
| 40 | 🟢 Polish | workspace | 3 | View icons in explorer VIEWS section (Spatial Canvas, Ontology Viewer, Table, Cards, Graph, Kanban) are too dim/muted — need brighter colors to stand out. | Explorer → VIEWS section → first 6 entries |
| 41 | 🔴 Broken | views | 4 | Cards View is broken — doesn't render/load. | VIEWS → Cards View → broken |
| 42 | 🟡 Bug | model-mgmt | 1 | Model detail relationship graph — hover popover appears far away from the node, not anchored to it. Likely the dockview stacking context / CSS transform coordinate issue (documented in KNOWLEDGE.md for Cytoscape). | Admin → model detail → relationship graph → hover a node |
| 43 | 🟢 Polish | views | 4 | Graph view node hover popover — property names and values need alignment (left-align labels, right-align or indent values). Add borders/separators between rows. Same polish pass as the object properties table (#23). | Graph View → hover a node → popover content is unstyled |
| 44 | 🟢 Polish | views | 4 | Kanban cards are too bare — just a title in a white box. Need: type icon, priority indicator, due date, assignee, tags. Compare to Trello/Linear card density. | Kanban View → cards show only title |
| 45 | 🟢 Polish | views | 4 | Kanban column headers need color coding and icons from the Mental Model's SHACL enum values. Currently plain text + count. | Kanban View → column headers "Todo", "In Progress" etc. |
| 46 | 🟢 Polish | views | 4 | Kanban cards need hover-reveal action buttons — delete, open in new tab, and a mini popover with key properties. | Kanban View → hover a card → nothing happens |
| 47 | 🟢 Polish | views | 4 | Kanban pills should only show types that have a status field (sh:in enum) — showing all 37 types makes no sense for kanban. Smart filtering by renderer compatibility. | Kanban View → pill bar shows all types including ones without status fields |
| 48 | 🟡 Bug | views | 4 | Calendar View doesn't take 100% available width — only fills after manually collapsing explorer/details panels. Should be responsive to available space. | Open Calendar View with panels open → doesn't fill |
| 49 | 🟡 Bug | views | 4 | Calendar nav buttons (back/forward arrows) invisible in dark mode — icon stroke color matches dark button background. Only "today" button text is visible. | Calendar View → upper left nav buttons → dark rectangle with invisible icons |
| 50 | 🟢 Polish | views | 4 | Calendar filter text field shows raw namespace IRI (`sempkm:model:basic-p...`) instead of human-readable label. | Calendar View → filter field |
| 51 | 🟢 Polish | views | 4 | Timeline/Gantt bars are plain gray rectangles — no color coding by status/priority, no progress indicator, no type icon. Small empty white squares on left edge of bars look like broken checkboxes. | Timeline View → bar styling |
| 52 | 🟢 Polish | views | 4 | Timeline has no "scroll to today" button — opens showing December/January seed data instead of current date. Calendar has a "today" button but timeline doesn't. | Timeline View → shows old dates, no navigation aid |
| 53 | 🟡 Bug | views | 4 | Timeline pills should only show types with date fields (scheduledStart, dueDate, etc.) — same smart filtering issue as kanban (#47). | Timeline View → all 37 types shown |
| 54 | 🟡 Bug | views | 4 | Timeline/Gantt popover (on bar click/hover) is impossible to dismiss — no click-outside or Escape handling. Same class of issue as relation autocomplete (#25). | Timeline View → click a bar → popover sticks |
| 55 | 🟡 Bug | views | 4 | Timeline doesn't fill 100% available height — Gantt area uses ~30% of viewport, rest is empty white space below. | Timeline View → large empty area below bars |
| 56 | 🟢 Polish | views | 4 | Timeline should show object detail in a right-hand panel when a bar is selected (like calendar does when clicking an event). | Timeline View → click a bar → no detail panel |
| 57 | 🟡 Bug | views | 4 | No discoverable way to save the current view — save button/flow is missing or broken. | Any view → try to save → unclear how |
| 58 | 🟡 Bug | views | 4 | Saved Views menu/section doesn't work — saved views can't be loaded or managed. | Explorer → Saved Views |
| 59 | 🟢 Polish | workspace | 3 | View names in explorer VIEWS section are underlined (link-styled) — inconsistent with other explorer items which are plain text. | Explorer → VIEWS → entries are underlined |
| 60 | 🟢 Polish | views | 4 | No seed data exists for Map View — no models define geo properties (wgs84:lat/long). Need to add geo fields to at least one model (e.g. CRM Contact/Company with addresses, or Events with locations) and create seed data. | Map View → nothing to display |
| 61 | 🟢 Polish | views | 5 | Eisenhower Matrix creation has zero workflow guidance — user creates the matrix container but has no indication that items must be created separately and linked. The read view should show an empty 2×2 grid with "Add Item" buttons in each quadrant, or at minimum helptext explaining the workflow. | Create Eisenhower Matrix → save → now what? |
| 62 | 🔴 Broken | views | 5 | Eisenhower Matrix object read view shows generic properties table + "No content" instead of the 2×2 quadrant grid. The custom renderer only works via a separate ViewSpec view — but that ViewSpec didn't load either (see #4a). Object view should detect custom renderer and show it inline. Same likely applies to BMC, OKR, Decision Matrix. | Create Eisenhower Matrix → save → cancel edit → see flat properties, no grid |
| 63 | 🔴 Broken | object-crud | 2 | `object.create` does not set `dcterms:created` automatically — new objects have no creation timestamp. The "Eisenhower Matrices Table" shows the seed data row with a CREATED value but the user-created row has an empty CREATED cell. | Create any object → view in table → CREATED column is empty |
| 64 | 🔴 Broken | views | 5 | "Browse: Eisenhower Quadrant" view does not exist in the VIEWS section — the ViewSpec didn't load into the triplestore. Root cause is #4a (model installer only loading a fraction of artifacts). All business-planning custom renderers are effectively broken. | Explorer → VIEWS → no quadrant entry |
| 65 | 🟢 Polish | object-crud | 2 | Object tab header needs a refresh button (cycle icon, same as explorer panel) next to the star/favorite icon. Currently no way to reload an object without closing and reopening the tab. | Any object tab → no refresh action |
| 66 | 🟡 Bug | model-mgmt | 1 | Archive validator's view→class reference-integrity check never fires — it looks for predicate `urn:sempkm:targetClass` but all views files (and the runtime) use `urn:sempkm:vocab:targetClass`. A model whose ViewSpec targets a nonexistent class installs without error. Detailed fix notes below. | Install a model with a views file targeting a bogus class → no validation error |
| 67 | 🟡 Bug | object-crud | 2 | Write path ignores declared SHACL datatypes — `_to_rdf_value()` guesses `xsd:date`/`xsd:dateTime`/IRI-ness by string sniffing instead of consulting the property's `sh:datatype`/`sh:class`. Mis-typed literals cause SHACL lint violations and wrong sort/filter behavior in views. Affects all 4 write handlers via the shared helper. Detailed fix notes below. | Create object with a `sh:datatype xsd:boolean` field → value stored as plain string literal → lint flags datatype mismatch |
| 68 | 🟡 Bug | inference | 18 | `entailment_defaults` is not a declared field on `ManifestSchema` — Pydantic silently drops it, and inference + admin code work around this by re-reading the raw manifest YAML in two separate places. No schema validation on the key, and the workaround readers can drift. Detailed fix notes below. | Add a typo'd `entailment_defaults` key to a manifest → installs silently, defaults ignored |
| 69 | 🟡 Bug | validation | 9 | pyshacl runs without any ontology graph — validation sees no `rdfs:subClassOf`/OWL axioms, so an object typed as a subclass fails `sh:class` constraints that name the superclass (e.g. a `bpkm:Note` referenced by a property constrained to `gist:FormattedContent` is flagged). Inferred triples in `urn:sempkm:inferred` are also excluded from the validated data. Detailed fix notes below. | Reference a subclass-typed object from a property whose `sh:class` names the parent class → false-positive lint violation |

**Severity:** 🔴 Broken (feature doesn't work) · 🟡 Bug (works but wrong) · 🟢 Polish (cosmetic/UX)

**Category:** `model-mgmt` · `object-crud` · `workspace` · `views` · `canvas` · `sparql` · `search` · `validation` · `vfs` · `import` · `apps` · `sync` · `copilot` · `auth` · `identity` · `dashboard` · `workflow` · `inference` · `events` · `docs` · `ui-quality`

---

## Fix Notes: #66–#69 (backend model layer)

> Found during the 2026-08-20 LinkML integration assessment (`.planning/research/linkml-integration-assessment.md`). All four verified against current `main`. File:line references are exact as of that date.

### #66 — Dead view reference-integrity check (wrong predicate IRI)

**Root cause:** `backend/app/models/validator.py:20` defines

```python
SEMPKM_TARGET_CLASS = URIRef("urn:sempkm:targetClass")
```

but every shipped views file binds `"sempkm": "urn:sempkm:vocab:"` (verified across all 8 `models/*/views/*.jsonld`), and the runtime reads views with `urn:sempkm:vocab:targetClass` (`backend/app/views/service.py:38` defines `SEMPKM_VOCAB = "urn:sempkm:vocab:"`, used at line 167). Check #4 in `validate_reference_integrity()` (the loop over `views.triples((None, SEMPKM_TARGET_CLASS, None))`, ~line 168) therefore iterates zero triples and can never report an issue.

**Fix:**
1. Change the constant to `URIRef("urn:sempkm:vocab:targetClass")`.
2. Better: define the vocab namespace once (e.g. `SEMPKM_VOCAB = "urn:sempkm:vocab:"` in `backend/app/rdf/namespaces.py`) and derive both the validator constant and `views/service.py:38` from it, so they can't drift again.

**Verify:** unit test in `backend/tests/` — build a `ModelArchive` whose views graph contains a `sempkm:ViewSpec` with `urn:sempkm:vocab:targetClass` pointing at a class **not** in the ontology graph, call `validate_archive`, assert one error with rule `ref-integrity-view-class`. This test fails before the fix (no error reported) and passes after. Also re-run `pytest backend/tests -k validator` and confirm the 8 bundled models still validate cleanly (`test_model_audit.py` covers install).

**Gotcha:** after the fix, any *existing* model archive with a broken view target will start failing installation — check all 8 bundled models' views files reference real ontology classes before merging (the check only applies to targets inside the model's own namespace, so gist/external targets are unaffected).

### #67 — Write path ignores declared `sh:datatype` (string-sniffing coercion)

**Root cause:** `_to_rdf_value()` at `backend/app/commands/handlers/object_create.py:49-76` converts form values to RDF terms purely by inspecting the Python value: strings starting with `http(s)://`/`urn:` become IRIs, ISO-8601-looking strings become `xsd:dateTime`/`xsd:date`, everything else becomes an untyped string literal. The SHACL `sh:datatype` declared on the property shape is never consulted. The helper is shared — imported and called from:
- `object_create.py:116,119`
- `object_patch.py:84`
- `edge_create.py:56`
- `edge_patch.py:38`

**Symptoms:** booleans arrive from forms as `"true"`/`"false"` and are stored as plain string literals (the `isinstance(value, bool)` branch never fires for form input); integers/decimals stored as strings; a free-text field whose value happens to start with `urn:` becomes a URIRef; all of which produce SHACL datatype-mismatch lint results and break typed sorting/filtering in table views.

**Fix (shape-driven coercion with sniffing as fallback):**
1. Extend the helper signature: `_to_rdf_value(value, *, expected_datatype: str | None = None, is_object_ref: bool = False)`.
   - `expected_datatype` (an XSD IRI string) → emit `Literal(value, datatype=URIRef(expected_datatype))`, converting `"true"/"false"` → boolean, numeric strings → int/decimal first so rdflib serializes canonically.
   - `is_object_ref` (property has `sh:class` or `sh:nodeKind sh:IRI`) → emit `URIRef(value)`, error if not IRI-shaped.
   - Neither → current sniffing behavior (back-compat for untyped/unknown properties, e.g. RDF import and user-created types with no shape).
2. Thread the shape info in at the dispatch layer, not inside the pure handlers: in `backend/app/commands/dispatcher.py`, before invoking the handler, resolve the object's type → `ShapesService.get_form_for_type()` (`backend/app/services/shapes.py:356-400`, already TTL-cached) → build `{predicate_iri: PropertyShape}` and pass it through to the handlers (`PropertyShape` already carries `datatype` and `target_class` fields, `shapes.py:30-66`). For edge handlers, the predicate's shape comes from the source object's type.
3. Update all 4 handlers to pass the per-predicate shape into `_to_rdf_value`.

**Verify:** unit tests on `_to_rdf_value` per datatype (`xsd:boolean`, `xsd:integer`, `xsd:decimal`, `xsd:date`, `xsd:dateTime`, `xsd:anyURI`, `sh:class` ref, no-shape fallback). Integration: create a Task with a boolean/int field via `POST /api/commands`, SPARQL the stored literal's datatype, assert typed. E2E: `e2e/tests/04-validation/` — a freshly created valid object should produce zero datatype lint results.

**Gotcha:** existing stored data keeps its old (untyped) literals — this fix is forward-only. Don't attempt migration here; note it as a follow-up (relates to the "Mental Model Schema Migrations" idea in `.gsd/QUEUE.md`). Watch `sh:in` dropdowns: their values are plain strings by design; only coerce when `sh:datatype` says so.

### #68 — `entailment_defaults` silently dropped by `ManifestSchema`

**Root cause:** `ManifestSchema` (`backend/app/models/manifest.py:60-122`) declares `settings` and `icons` but **not** `entailment_defaults`. Pydantic's default `extra="ignore"` silently discards the key during `parse_manifest()`. Two places work around this by re-reading the raw YAML with their own parsing loops:
- `backend/app/inference/service.py:664-665`
- `backend/app/admin/router.py:1386-1410` (`_load_entailment_defaults`)

Consequences: the key gets zero schema validation (a typo'd entailment name or non-bool value is silently accepted/ignored), and the two ad-hoc readers can drift from each other and from the manifest spec.

**Fix:**
1. Add to `ManifestSchema` (next to `settings`/`icons`):
   ```python
   entailment_defaults: dict[str, bool] = Field(default_factory=dict)
   ```
   Optionally validate keys against the known entailment types in `backend/app/inference/entailments.py` — warn (don't fail install) on unknown keys, since older/newer models may name entailments this version doesn't know.
2. Replace both raw-YAML readers with the parsed manifest: `_load_entailment_defaults` in `admin/router.py` and the block in `inference/service.py:655-670` should call `parse_manifest(model_dir)` (or better, read from the model registry if the parsed manifest is stored there at install time) and return `manifest.entailment_defaults`.
3. Grep for any other raw-YAML manifest reads while in there (`rg "yaml.safe_load" backend/app`) and consolidate on `parse_manifest`.

**Verify:** unit test — manifest YAML with `entailment_defaults: {inverse_properties: true, subclass_transitivity: false}` parses into the field; manifest with a bogus value type (`entailment_defaults: {x: "yes"}`) raises a Pydantic error. Regression: `pytest backend/tests -k "manifest or inference"`; the admin model-detail Inference section (bug #8's screen) still shows correct per-model defaults.

**Gotcha:** `ppv` is the model that ships manifest extras — confirm its manifest still parses and its inference defaults still apply after the change (`test_ppv_ontology.py`).

### #69 — pyshacl validates without ontology axioms (`ont_graph` absent)

**Root cause:** `ValidationService.validate()` at `backend/app/services/validation.py:52-119` CONSTRUCTs **only** `urn:sempkm:current` as the data graph (lines 72-74) and calls `pyshacl.validate(data_graph, shacl_graph=..., advanced=True)` with no `ont_graph` and no inference (lines 99-106). The shapes loader (`model_shapes_loader`, `backend/app/services/models.py:1372-1441`) merges shapes + rules graphs but no ontologies. So SHACL validation has no knowledge of `rdfs:subClassOf`, `owl:inverseOf`, etc.

**Concrete failure:** models subclass gist (`bpkm:Note rdfs:subClassOf gist:FormattedContent`). A property shape with `sh:class gist:FormattedContent` (or `sh:class` naming any superclass) flags every reference to a subclass-typed object as a violation, because the data graph contains only `?x a bpkm:Note` and pyshacl can't derive the supertype. Separately, triples materialized by the inference engine into `urn:sempkm:inferred` (inverse edges etc.) are invisible to validation.

**Fix — two options; pick one and record it in `.gsd/DECISIONS.md`:**
- **Option A (recommended): include the inferred graph in the data.** Change the CONSTRUCT to `FROM <urn:sempkm:current> FROM <urn:sempkm:inferred>` (named-graph IRIs are in `backend/app/rdf/namespaces.py:79-91`). The inference engine (`backend/app/inference/service.py`, owlrl OWL 2 RL) already materializes subclass/inverse entailments there, so validation sees exactly what the user sees, at zero extra per-run cost. Note the interaction: only *enabled* entailment types are materialized, and user-dismissed inferred triples are excluded — that's arguably correct ("validate what's visible") but is a semantic choice worth writing down. Also add the *type hierarchy itself* (model ontology graphs + `urn:sempkm:ontology:gist`) via `ont_graph=` **without** an `inference=` argument, so pyshacl's own `sh:class` evaluation can walk `rdfs:subClassOf` — pyshacl handles subclass traversal for `sh:class` natively when the hierarchy is present.
- **Option B: full pyshacl-side inference.** Pass `ont_graph=` (merged model ontologies + gist) plus `inference="rdfs"`. Self-contained, but re-computes the closure over the whole current graph on **every** validation run (it already CONSTRUCTs the full graph each time — see bug #32's performance findings) and duplicates work the inference engine does. Avoid unless Option A proves insufficient.

**Verify:** integration test — install basic-pkm, create a shape constraint `sh:class gist:FormattedContent` on a test property, link a `bpkm:Note`, run validation, assert conforms. Before the fix this reports a violation; after, it passes. Then run the full validation-pipeline suite (`test_validation_pipeline.py`, `test_cross_model_validation.py`) and `e2e/tests/04-validation/` — expect some previously-reported violations to legitimately disappear; eyeball the diff to confirm none of the *intended* violations (required-field, datatype, `sh:in`) got swallowed.

**Gotcha:** watch validation latency after adding graphs (gist is ~138 KB Turtle, parsed per run unless cached) — cache the parsed ontology graph in the service alongside the existing shapes cache pattern (`test_shapes_cache.py` shows the convention).

---

## Milestone Candidates

> Distilled from the bug log after the tour. Each becomes a GSD milestone.

### Candidate A: Model Marketplace
**Scope:** Cloud-hosted model registry so users can discover, browse, and install Mental Models without filesystem access.
**Items:**
- Hosted model registry (cloud API) with model metadata, versions, screenshots
- In-app "Browse Models" UI that fetches from the registry
- One-click install from the marketplace (download archive → install)
- Model versioning and update notifications
- Community model submissions (later phase)

### Candidate B: Ontology Visualization Overhaul
**Scope:** Layered ontology graph with hierarchical layout, full TBox coverage, and interactive filtering.
**Items:**
- Layered graph layout: gist upper ontology at top, then model layers determined by degree-from-gist + categorical grouping
- Copy relationship graph from model detail to Ontology Viewer — show full TBox not just a single model subset
- Bottom panel in Ontology Viewer showing a graph of whatever is selected (class detail, properties, etc.)
- Multi-select filtering by Mental Model (not just "hide gist" toggle) — graph updates live as user filters
- Graph persists across tab switches (TBox/ABox/RBox) — doesn't reset when switching views
- Fix model detail relationship graph to use 100% width/height (currently has wasted whitespace)

### Candidate C: Explorer Composable Filter/Group/Sort
**Scope:** Replace the flat OBJECTS dropdown with a composable explorer where filtering, grouping, and sorting are independent stackable layers.
**Items:**
- **Filter layer:** subset objects by type, saved query, tag, or arbitrary SPARQL — controls WHAT is shown
- **Group layer:** organize results by property, tag, type, model, or custom grouping — controls HOW they're structured. Multi-level: each level is a group + sort (like VFS mount strategies)
- **Sort layer:** within each group, sort by time, label, property value
- Remove "Shape" suffix from type names in explorer — show "Project" not "Project Shape"
- Remove or relocate "VFS Mounts" from the mode dropdown (currently 404s anyway)
- Per-model filter entries need human-readable labels, not raw `model-id (by-type)` format
- Group the generic view modes (By Type / Hierarchy / By Tag) visually separate from model-specific filters
- Consider a builder UI similar to VFS MountSpec strategies where user composes levels
- Support multiple OBJECTS panels — button to duplicate an explorer instance so user can have different filter/group/sort configs side by side (e.g. "Tasks by status" + "Contacts by company")

### Candidate D: Browser History & Tab Recovery
**Scope:** Research and implement browser history integration for the workspace. Hard problem — dockview's multi-tab model doesn't map 1:1 to browser history, but the current state (URL never changes, no undo close) is a real usability gap.
**Items:**
- Research: how do other IDE-in-browser apps (VS Code web, Figma, Linear) handle URL ↔ workspace state?
- URL should reflect at minimum the active tab's object/view IRI — enables bookmarking and sharing
- Browser back/forward should navigate between recently-viewed objects (tab focus history, not DOM history)
- "Reopen closed tab" command in command palette (maintain a closed-tab stack)
- Ctrl+Z / Ctrl+Shift+T for undo close tab
- Consider: should opening a shared URL restore a single-tab view or add to existing workspace?

### Candidate E: Backend Performance & Observability
**Scope:** Profile and fix the 4+ second object load times. The backend is the bottleneck — SPARQL queries are slow, and opening one object triggers 10+ sequential htmx partial loads.
**Items:**
- Set up Jaeger/OpenTelemetry for distributed tracing — flame graphs for every request showing SPARQL query time, template render time, middleware overhead
- Profile slowest SPARQL queries (object-tab, comments, inbox, lint, relations, shapes lookups)
- Add query-level caching (label service TTL cache exists but may not cover all paths)
- Lazy-load secondary panels (comments, inbox, collaboration) — don't fetch until section is expanded
- Consider parallel loading of independent partials instead of sequential htmx cascade
- Investigate triplestore query optimization (indexes, query plans)
- Add Server-Timing headers to all htmx endpoints for easy profiling
- Basic observability dashboard (request latency percentiles, slow query log, error rates)

### Candidate F: Critical Bug Fixes
**Scope:** Fix the showstopper bugs that make core features non-functional. Highest priority — do before any polish work.
**Items:**
- **#4a** Model installer only loads fraction of SHACL shapes (cascades to #62, #64 — breaks all business-planning custom renderers)
- **#29** Object deletion doesn't exist — no command, no UI, no mechanism at all
- **#30** Save does full replace instead of diff — pollutes event store with phantom changes, unnecessary body.set events
- **#36** Generic Table View shows "No objects found" even with data present
- **#41** Cards View broken — doesn't render
- **#63** object.create doesn't set dcterms:created — new objects have no creation timestamp
- **#1, #2** Docker volume permissions / nginx setgid (already fixed but need permanent fix in Dockerfile entrypoint)

### Candidate G: UI Design System & Polish Pass
**Scope:** Systemic visual quality pass — establish a design system with consistent styling across all panels, forms, views, and popovers. Address the "bland/generic" feel.
**Items:**
- **#13, #14** Object view visual identity — type-colored accents, styled type pill with icon instead of raw IRI
- **#15** Body editor should feel like a writing surface, not a code editor
- **#19, #20** Read view property table — label/value distinction, tooltips in both read and edit modes
- **#21, #22** Edit form — responsive width inputs, stronger section headers
- **#23** Systemic zebra striping / borders / separators across ALL panels
- **#43** Graph/view popovers — aligned properties, borders
- **#44, #45, #46** Kanban cards — richer card content, column colors from model, hover actions
- **#51** Timeline bar styling — colors, progress indicators
- **#31** Tab styling — more prominent active/inactive distinction
- **#40** View icons in explorer — brighter colors
- **#59** View names underlined inconsistently

### Candidate H: View System Rework
**Scope:** Fix the view toolbar UX — pills, variants, filters, and save flow.
**Items:**
- **#37** Replace 37-pill type bar with a smart dropdown showing only relevant types for the current query
- **#38** Remove View Variants dropdown
- **#39** Clearer separation between query filter (universe) and type filter (subset)
- **#47, #53** Smart type filtering by renderer compatibility (kanban = status types only, timeline = date types only)
- **#48, #55** Views should take 100% available width and height
- **#49** Calendar nav button icons invisible in dark mode
- **#50** Filter field shows raw namespace IRIs
- **#52** Timeline "scroll to today" not working
- **#54** Timeline/Gantt popover undismissable
- **#56** Timeline should show object detail in right panel on selection
- **#57, #58** Save view flow broken / undiscoverable
- **#60** Map view needs seed data with geo properties

### Candidate I: Workspace UX Improvements
**Scope:** Fix workspace-level interaction issues — command palette, dropdowns, dismissal, discoverability.
**Items:**
- **#10** Event Log tab shows stale "Phase 16" placeholder
- **#11** Explorer shows "Shape" suffix on all type names
- **#12** OBJECTS dropdown poorly organized — raw model IDs, VFS Mounts 404
- **#24** Command palette scroll jump bug
- **#25** Relation autocomplete dropdowns don't dismiss on click-outside/Escape
- **#26** Tag autocomplete clipped by container boundary
- **#27** URL never changes / no browser history integration (→ Candidate D research)
- **#33, #34** Persona create / Layout save UX broken (type-then-select pattern not discoverable)
- **#35** Personas vs Layouts distinction unclear — consider merging
- **#42** Model detail graph popover appears far from node
- **#65** Object tab needs refresh button
