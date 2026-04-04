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

- [ ] **1.1** Navigate to Admin portal
- [ ] **1.2** Install `basic-pkm` model from archive
- [ ] **1.3** Install `business-planning` model
- [ ] **1.4** Install `crm` model
- [ ] **1.5** Install `zettelkasten` model
- [ ] **1.6** Install `research` model
- [ ] **1.7** Install `ppv` model
- [ ] **1.8** Model detail page shows real stats + charts
- [ ] **1.9** Schema refresh works (POST without uninstall)
- [ ] **1.10** Uninstall a model (verify clean removal)

**Notes:**
```
```

---

## 2. Object CRUD

> Create, read, edit, delete objects of various types.

- [ ] **2.1** Create a Note (basic-pkm) — form renders, save works
- [ ] **2.2** Create a Project — verify all SHACL fields present
- [ ] **2.3** Create a Concept — definition field, related concepts
- [ ] **2.4** Create a Person — contact fields
- [ ] **2.5** Create a Task — status, priority, due date, scheduled times
- [ ] **2.6** Object read view renders (markdown body, properties)
- [ ] **2.7** Flip to edit mode (CSS 3D card flip, no flicker)
- [ ] **2.8** Edit properties — save persists
- [ ] **2.9** Edit markdown body — save persists
- [ ] **2.10** Delete object — confirmation, clean removal
- [ ] **2.11** Edge creation (link two objects)
- [ ] **2.12** Edge deletion
- [ ] **2.13** Markdown rendering in body (headings, code, lists, links)
- [ ] **2.14** Form advanced section (collapse/expand)

**Notes:**
```
```

---

## 3. Workspace & Navigation

> IDE-style workspace: tabs, sidebar, command palette, keyboard shortcuts.

- [ ] **3.1** Sidebar navigation tree loads (explorer sections)
- [ ] **3.2** Explorer mode dropdown works (by-type, by-hierarchy, by-tag, VFS)
- [ ] **3.3** Click object in tree → opens in dockview tab
- [ ] **3.4** Multiple tabs open simultaneously
- [ ] **3.5** Tab close, tab switching
- [ ] **3.6** Dockview drag to split (horizontal/vertical groups)
- [ ] **3.7** Command palette (Ctrl+K) — search, actions
- [ ] **3.8** Keyboard shortcuts (documented ones work)
- [ ] **3.9** Named layouts — save and restore
- [ ] **3.10** Personas — create, switch, verify layout persistence
- [ ] **3.11** Sidebar panel drag-drop reordering
- [ ] **3.12** Dark mode toggle (system/light/dark)
- [ ] **3.13** Sidebar sections collapse/expand
- [ ] **3.14** Bottom panel toggle (Ctrl+J) — SPARQL, Event Log, Copilot tabs

**Notes:**
```
```

---

## 4. Views & Data Browsing

> Table, cards, graph, kanban, calendar, timeline, map renderers.

- [ ] **4.1** Table view — loads, columns correct, pagination
- [ ] **4.2** Cards view — renders, flip animation
- [ ] **4.3** Graph view (2D) — nodes, edges, layout
- [ ] **4.4** Kanban view — columns from SHACL sh:in, drag cards
- [ ] **4.5** Calendar view — tasks/events display, drag-to-reschedule
- [ ] **4.6** Timeline/Gantt view — bars, dependencies, zoom
- [ ] **4.7** Map view (if geo data exists)
- [ ] **4.8** Generic views (any type → table/cards/graph)
- [ ] **4.9** View filtering / scope select
- [ ] **4.10** Column preferences (table) persist
- [ ] **4.11** Save view / promoted views folder

**Notes:**
```
```

---

## 5. Business Planning Renderers

> Install business-planning model, test custom renderers.

- [ ] **5.1** Quadrant view (e.g. SWOT, Eisenhower) — 2×2 grid renders
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
| 2 | 🔴 Broken | infra | Pre-flight | nginx frontend crashes with `setgid(101) failed (Operation not permitted)` — `security_opt: no-new-privileges` in docker-compose.yml prevents nginx worker setgid. | `docker compose up -d` after a fresh build → frontend container exits immediately |

**Severity:** 🔴 Broken (feature doesn't work) · 🟡 Bug (works but wrong) · 🟢 Polish (cosmetic/UX)

**Category:** `model-mgmt` · `object-crud` · `workspace` · `views` · `canvas` · `sparql` · `search` · `validation` · `vfs` · `import` · `apps` · `sync` · `copilot` · `auth` · `identity` · `dashboard` · `workflow` · `inference` · `events` · `docs` · `ui-quality`

---

## Milestone Candidates

> Distilled from the bug log after the tour. Each becomes a GSD milestone.

### Candidate A: _[name TBD]_
**Scope:**
**Items:**

### Candidate B: _[name TBD]_
**Scope:**
**Items:**

### Candidate C: _[name TBD]_
**Scope:**
**Items:**
