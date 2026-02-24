# Roadmap: SemPKM

## Milestones

- ✅ **v1.0 MVP** — Phases 1-9 (shipped 2026-02-23) — [Full details](milestones/v1.0-ROADMAP.md)
- 🚧 **v2.0 Tighten Web UI** — Phases 10-18 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-9) — SHIPPED 2026-02-23</summary>

- [x] Phase 1: Core Data Foundation (4/4 plans) — completed 2026-02-21
- [x] Phase 2: Semantic Services (2/2 plans) — completed 2026-02-21
- [x] Phase 3: Mental Model System (3/3 plans) — completed 2026-02-22
- [x] Phase 4: Admin Shell and Object Creation (6/6 plans) — completed 2026-02-22
- [x] Phase 5: Data Browsing and Visualization (3/3 plans) — completed 2026-02-22
- [x] Phase 6: User and Team Management (4/4 plans) — completed 2026-02-22
- [x] Phase 7: Route Protection and Provenance (2/2 plans) — completed 2026-02-23
- [x] Phase 8: Integration Bug Fixes (1/1 plan) — completed 2026-02-23
- [x] Phase 9: Provenance and Redirect Micro-Fixes (1/1 plan) — completed 2026-02-23

**26 plans, ~354 tasks, 43/43 requirements satisfied**

</details>

### 🚧 v2.0 Tighten Web UI

**Milestone Goal:** Polish the web UI into a product-grade experience with bug fixes, read-only object views, VS Code-style workspace enhancements, dark mode, settings system, event log explorer, and LLM connection configuration.

- [x] **Phase 10: Bug Fixes and Cleanup Architecture** - Fix broken core flows and establish htmx cleanup patterns that prevent listener/instance accumulation (completed 2026-02-23)
- [x] **Phase 11: Read-Only Object View** - Objects open in a styled read-only mode by default with an edit toggle (completed 2026-02-23)
- [x] **Phase 12: Sidebar and Navigation** - Collapsible sidebar with grouped navigation sections and user menu (completed 2026-02-23)
- [x] **Phase 13: Dark Mode and Visual Polish** - Tri-state theme system, rounded tabs, and styled error panels (completed 2026-02-24)
- [ ] **Phase 14: Split Panes and Bottom Panel** - VS Code-style editor groups with tab drag and a collapsible bottom panel
- [ ] **Phase 15: Settings System and Node Type Icons** - Layered settings infrastructure and type-specific visual richness
- [ ] **Phase 16: Event Log Explorer** - Browsable, filterable event timeline with inline diffs and undo
- [ ] **Phase 17: LLM Connection Configuration** - Generic OpenAI-compatible LLM endpoint with server-side key storage and streaming proxy
- [ ] **Phase 18: Tutorials and Documentation** - Driver.js guided tours and a Docs page for onboarding

## Phase Details

### Phase 10: Bug Fixes and Cleanup Architecture
**Goal**: Core workspace interactions work reliably and the htmx cleanup architecture prevents resource leaks as new features are added
**Depends on**: Phase 9 (v1.0 complete)
**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04, FIX-05
**Success Criteria** (what must be TRUE):
  1. Opening an object tab shows a loading skeleton, then the CodeMirror editor with body content loaded; if the editor fails to load within 3 seconds, a fallback textarea appears with a clear message
  2. The CodeMirror editor is always editable with at least 200px height regardless of Split.js initialization timing
  3. Autocomplete dropdown for reference properties renders on top of all content (never clipped) and clicking a suggestion populates the field
  4. Views explorer section loads its tree content on workspace initialization without requiring a user click
  5. Navigating between tabs repeatedly for 30+ cycles does not accumulate duplicate event listeners, Split.js gutters, or CodeMirror instances (htmx:beforeCleanupElement tears down library instances before DOM removal)
**Plans**: 3 plans

Plans:
- [ ] 10-01-PLAN.md — Body loading skeleton, Promise-based editor init with 3s timeout, CodeMirror bump, min-height fix
- [ ] 10-02-PLAN.md — Autocomplete dropdown position:fixed escape, views explorer eager loading
- [ ] 10-03-PLAN.md — htmx cleanup registry, library teardown registration, editor group data model design

### Phase 11: Read-Only Object View
**Goal**: Users see a polished, readable presentation of their objects by default and switch to edit mode only when they intend to make changes
**Depends on**: Phase 10
**Requirements**: VIEW-01, VIEW-02, VIEW-03, VIEW-04
**Success Criteria** (what must be TRUE):
  1. Clicking an object in the explorer opens it in read-only mode showing styled property key-value pairs (labels, formatted values, hidden empty optionals) and rendered Markdown body
  2. User can toggle between read-only and edit mode via an Edit/Done button or Ctrl+E shortcut; newly created objects open in edit mode
  3. Reference properties in read-only mode render as clickable links that open the target object in a new tab
  4. In edit mode, the body text area is resizable via the Split.js gutter and has a maximize/restore toggle that gives the editor 100% of the object tab area
**Plans**: 2 plans

Plans:
- [x] 11-01-PLAN.md — Backend enhancements (multi-value, ref labels, mode param), CDN libs, read-only template, flip container, and all CSS
- [x] 11-02-PLAN.md — Mode toggle JS (Edit/Done, Ctrl+E, unsaved changes), deferred editor init, body maximize/restore toggle

### Phase 12: Sidebar and Navigation
**Goal**: The sidebar provides organized, collapsible navigation with a user menu that makes logout, settings access, and identity visible at a glance
**Depends on**: Phase 10
**Requirements**: NAV-01, NAV-02, NAV-03, NAV-04, NAV-05, NAV-06
**Success Criteria** (what must be TRUE):
  1. Pressing Ctrl+B collapses the sidebar to a 48px icon rail with smooth CSS transition; pressing again expands to 220px with labels; collapsed state persists across page reloads
  2. Sidebar navigation is organized into grouped sections (Home, Admin, Meta, Apps, Debug) with collapsible section headers
  3. Apps section contains Object Browser and SPARQL Console; Debug section contains Commands, API Docs, Health Check, and Event Log; Meta section contains Docs and Tutorials
  4. A user menu at the bottom of the sidebar shows user name/avatar and opens a popover with Settings link, Theme toggle placeholder, and working Logout action that ends the session
**Plans**: 2 plans

Plans:
- [ ] 12-01-PLAN.md — Sidebar restructure with grouped sections, Lucide icons, collapse-to-icon-rail toggle (Ctrl+B), CSS transitions, localStorage persistence
- [ ] 12-02-PLAN.md — User menu popover with colored initials avatar, Settings/Theme placeholders, and working Logout action

### Phase 13: Dark Mode and Visual Polish
**Goal**: Users can choose their preferred theme (system, light, or dark) with instant switching, no flash, and consistent styling across all UI components including third-party libraries
**Depends on**: Phase 12 (sidebar must exist for user menu theme toggle and icon-rail dark styling)
**Requirements**: DARK-01, DARK-02, DARK-03, DARK-04, WORK-06, ERR-01
**Success Criteria** (what must be TRUE):
  1. User can toggle between System, Light, and Dark theme via the user menu or command palette; preference persists across reloads with zero flash of wrong theme (inline head script applies theme before first paint)
  2. Dark mode applies consistently to all UI components: base layout, sidebar, tabs, SHACL forms, CodeMirror editor (via Compartment reconfigure), Cytoscape graph, command palette (ninja-keys), and Split.js gutters
  3. Dark mode color tokens follow VS Code "Dark+" palette (dark surfaces, muted text, blue accents)
  4. Tab styling uses rounded top corners (border-radius 8px) with a recessed tab bar background in both light and dark modes
  5. 403 Forbidden responses display a styled permission panel with lock icon, role explanation, and navigation buttons instead of a raw error fragment
**Plans**: 4 plans

Plans:
- [ ] 13-01-PLAN.md — CSS custom property token system (light+dark), anti-FOUC script, theme toggle UI, full hardcoded color migration
- [ ] 13-02-PLAN.md — Third-party component dark mode (CodeMirror Compartment, Cytoscape style rebuild, ninja-keys, highlight.js)
- [ ] 13-03-PLAN.md — Rounded tab styling with teal accent and styled 403 permission panel
- [ ] 13-04-PLAN.md — UAT gap closure: Ctrl+K command palette fix, tab accent/radius fixes, card border fixes

### Phase 14: Split Panes and Bottom Panel
**Goal**: Users can work with multiple objects side-by-side in editor groups and access panel-based tools (SPARQL, Event Log, AI Copilot) in a collapsible bottom panel
**Depends on**: Phase 10 (cleanup architecture), Phase 11 (read-only view exists for meaningful side-by-side), Phase 13 (dark mode styling for new UI elements)
**Requirements**: WORK-01, WORK-02, WORK-03, WORK-04, WORK-05
**Success Criteria** (what must be TRUE):
  1. User can split the editor into up to 4 horizontal editor groups via context menu "Split Right" or Ctrl+\ shortcut; each group has its own tab bar with independent tabs
  2. Tabs can be dragged between editor groups; the tab moves (not copies) to the target group
  3. Closing the last tab in an editor group removes that group and remaining groups expand to fill the space
  4. A bottom panel toggled via Ctrl+J exists below the editor area with tabbed interface (SPARQL, Event Log, AI Copilot placeholder tabs) and collapse/maximize controls
**Plans**: ~3 plans

Plans:
- [ ] 14-01: Editor group manager (WorkspaceLayout class, multi-group tab state, dynamic Split.js)
- [ ] 14-02: Tab drag between groups and group lifecycle
- [ ] 14-03: Bottom panel infrastructure with placeholder tabs

### Phase 15: Settings System and Node Type Icons
**Goal**: A layered settings system provides extensible configuration (system defaults, mental model defaults, user overrides) and type-specific icons bring visual richness to the explorer and graph
**Depends on**: Phase 13 (dark mode is first settings consumer), Phase 14 (settings page opens as a tab in editor area)
**Requirements**: SETT-01, SETT-02, SETT-03, SETT-04, ICON-01, ICON-02, ICON-03
**Success Criteria** (what must be TRUE):
  1. A Settings page opens as a tab in the editor area (via Ctrl+, or user menu) with categorized settings, search filter, and current values with "Modified" indicators
  2. Settings resolve in layered order: system defaults < mental model defaults < user overrides; changes dispatch a `sempkm:setting-changed` DOM event that consuming components react to
  3. Mental Models can contribute settings via a `settings` key in their manifest, which appear in the Settings page under the model's category
  4. Object explorer tree and graph view display type-specific Lucide icons with color coding; Mental Models can declare icon and color mappings in their manifest
**Plans**: ~3 plans

Plans:
- [ ] 15-01: Settings registry, store, and page UI
- [ ] 15-02: Layered resolution and mental model contributed settings
- [ ] 15-03: Lucide icon integration for explorer tree and graph view

### Phase 16: Event Log Explorer
**Goal**: Users can browse, filter, and understand the full history of changes to their knowledge base, with inline diffs and the ability to undo reversible operations
**Depends on**: Phase 14 (event log lives in bottom panel), Phase 10 (cleanup architecture for htmx partials)
**Requirements**: EVNT-01, EVNT-02, EVNT-03, EVNT-04
**Success Criteria** (what must be TRUE):
  1. Event log displays a paginated timeline of events in reverse chronological order with operation type badge, affected object link, user, and timestamp; page 50 loads as fast as page 1 (cursor-based pagination)
  2. Events are filterable by operation type, user, object, and date range with removable filter chips; filters combine with AND logic
  3. Clicking an object.patch or body.set event shows an inline diff of the changes (property before/after or line-by-line body diff)
  4. Reversible events (object.patch, body.set, edge.create, edge.patch) have an Undo button that creates a compensating event after user confirmation
**Plans**: ~3 plans

Plans:
- [ ] 16-01: Event API endpoint with cursor pagination and event index graph
- [ ] 16-02: Event log timeline UI with filtering
- [ ] 16-03: Inline diff view and undo operations

### Phase 17: LLM Connection Configuration
**Goal**: Administrators can configure and validate a generic LLM connection, with API keys stored securely server-side and a streaming proxy ready for future AI features
**Depends on**: Phase 15 (settings system for LLM config UI)
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05
**Success Criteria** (what must be TRUE):
  1. Admin can configure an OpenAI-compatible LLM connection (API base URL, API key, default model) via the Settings page under an LLM Connection category
  2. API keys are stored server-side only (encrypted in database), never exposed to the browser; the settings UI shows a masked key after save
  3. A "Test Connection" button validates the configured endpoint and displays connection status; a "Fetch Models" button retrieves and populates available models from the provider
  4. Backend provides a streaming proxy endpoint (SSE) for LLM chat completions with proper nginx configuration (proxy_buffering off, increased read timeout)
**Plans**: ~2 plans

Plans:
- [ ] 17-01: LLM settings UI, server-side key storage, test and fetch endpoints
- [ ] 17-02: SSE streaming proxy endpoint with nginx configuration

### Phase 18: Tutorials and Documentation
**Goal**: New users can orient themselves through guided interactive tours, and a documentation hub provides ongoing reference
**Depends on**: Phase 11 (read-only view referenced in tours), Phase 12 (sidebar referenced in tours), Phase 14 (editor groups referenced in tours)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. A Docs and Tutorials page accessible from the Meta sidebar section lists available interactive tutorials and documentation links
  2. Driver.js (MIT licensed) is integrated for guided tours with lazy element resolution that handles htmx-rendered content
  3. A "Welcome to SemPKM" tutorial walks through the workspace (sidebar, explorer, opening objects, read/edit toggle, command palette, saving) with properly positioned step popovers
  4. A "Creating Your First Object" tutorial walks through object creation from type selection to save, with each step waiting for htmx content to load before attaching
**Plans**: ~2 plans

Plans:
- [ ] 18-01: Driver.js integration, tour infrastructure, and Docs page
- [ ] 18-02: Welcome tour and first-object tutorial

## Progress

**Execution Order:**
Phases execute in numeric order: 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core Data Foundation | v1.0 | 4/4 | Complete | 2026-02-21 |
| 2. Semantic Services | v1.0 | 2/2 | Complete | 2026-02-21 |
| 3. Mental Model System | v1.0 | 3/3 | Complete | 2026-02-22 |
| 4. Admin Shell and Object Creation | v1.0 | 6/6 | Complete | 2026-02-22 |
| 5. Data Browsing and Visualization | v1.0 | 3/3 | Complete | 2026-02-22 |
| 6. User and Team Management | v1.0 | 4/4 | Complete | 2026-02-22 |
| 7. Route Protection and Provenance | v1.0 | 2/2 | Complete | 2026-02-23 |
| 8. Integration Bug Fixes | v1.0 | 1/1 | Complete | 2026-02-23 |
| 9. Provenance and Redirect Micro-Fixes | v1.0 | 1/1 | Complete | 2026-02-23 |
| 10. Bug Fixes and Cleanup Architecture | 3/3 | Complete    | 2026-02-23 | - |
| 11. Read-Only Object View | 1/2 | In Progress|  | - |
| 12. Sidebar and Navigation | 2/2 | Complete    | 2026-02-23 | - |
| 13. Dark Mode and Visual Polish | 4/4 | Complete   | 2026-02-24 | - |
| 14. Split Panes and Bottom Panel | v2.0 | 0/3 | Not started | - |
| 15. Settings System and Node Type Icons | v2.0 | 0/3 | Not started | - |
| 16. Event Log Explorer | v2.0 | 0/3 | Not started | - |
| 17. LLM Connection Configuration | v2.0 | 0/2 | Not started | - |
| 18. Tutorials and Documentation | v2.0 | 0/2 | Not started | - |

---
*Roadmap created: 2026-02-21*
*v1.0 archived: 2026-02-23*
*v2.0 roadmap added: 2026-02-23 — 9 phases, 46 requirements, ~23 plans*
