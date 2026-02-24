# Requirements: SemPKM v2.0 Tighten Web UI

**Defined:** 2026-02-23
**Core Value:** Polish the web UI into a product-grade experience with bug fixes, read-only object views, VS Code-style workspace enhancements, dark mode, settings system, and LLM connection configuration.

## v2.0 Requirements

### Bug Fixes (FIX)

- [x] **FIX-01**: Body content loads reliably into the Markdown editor with a visible loading skeleton and graceful fallback after timeout
- [x] **FIX-02**: CodeMirror editor is editable with proper minimum height regardless of Split.js initialization timing
- [x] **FIX-03**: Autocomplete dropdown for reference properties positions correctly and clicking a suggestion populates the field
- [x] **FIX-04**: Views explorer section loads its content eagerly on workspace init (no perpetual "Loading..." state)
- [x] **FIX-05**: htmx afterSwap cleanup architecture prevents listener accumulation and properly destroys library instances (Split.js, CodeMirror, Cytoscape) before DOM removal

### Object View (VIEW)

- [x] **VIEW-01**: Objects open in read-only mode by default showing styled property key-value pairs and rendered Markdown body
- [ ] **VIEW-02**: User can switch between read-only and edit mode via an Edit/Done button or Ctrl+E keyboard shortcut
- [x] **VIEW-03**: Reference properties in read-only mode render as clickable links that open the target object in a new tab
- [ ] **VIEW-04**: The Markdown body text area in edit mode is resizable via the Split.js gutter, with a maximize/restore toggle

### Workspace Layout (WORK)

- [ ] **WORK-01**: User can split the editor into multiple editor groups (horizontal split) via context menu "Split Right" or Ctrl+\ shortcut, up to 4 groups max
- [ ] **WORK-02**: Each editor group has its own tab bar with independent tabs; tabs can be dragged between groups
- [ ] **WORK-03**: Closing the last tab in an editor group removes that group and remaining groups expand to fill space
- [ ] **WORK-04**: A bottom panel with tabbed interface exists below the editor area, toggled via Ctrl+J, with collapse/maximize controls
- [ ] **WORK-05**: Bottom panel has placeholder tabs for SPARQL console, Event Log, and AI Copilot
- [x] **WORK-06**: Tab styling uses rounded top corners (border-radius 8px) with a recessed tab bar background

### Sidebar and Navigation (NAV)

- [x] **NAV-01**: Sidebar collapses to a 48px icon rail via Ctrl+B toggle with smooth CSS transition
- [x] **NAV-02**: Sidebar navigation is reorganized into grouped sections: Home, Admin, Meta, Apps, Debug
- [x] **NAV-03**: Apps section contains Object Browser and SPARQL Console; Debug section contains Commands, API Docs, Health Check, and Event Log
- [x] **NAV-04**: Meta section contains a Docs & Tutorials page
- [x] **NAV-05**: A VS Code-style user menu at the bottom of the sidebar shows user name/avatar with a popover containing Settings, Theme toggle, and Logout
- [x] **NAV-06**: Logout action in user menu ends the session and redirects to login

### Dark Mode (DARK)

- [x] **DARK-01**: User can toggle between System, Light, and Dark theme modes via the user menu or command palette
- [x] **DARK-02**: Theme preference persists across page reloads with no flash of wrong theme (anti-FOUC inline script)
- [x] **DARK-03**: Dark mode applies to all UI components including CodeMirror editor, Cytoscape graph, command palette, and Split.js gutters
- [x] **DARK-04**: Dark mode color tokens follow VS Code "Dark+" palette (dark surface, muted text, blue accents)

### Settings System (SETT)

- [ ] **SETT-01**: A Settings page opens as a tab in the editor area (accessible via Ctrl+, or user menu) with categorized settings and a search filter
- [ ] **SETT-02**: Settings use a layered resolution: system defaults < mental model defaults < user overrides
- [ ] **SETT-03**: Settings changes dispatch a `sempkm:setting-changed` DOM event that consuming components listen to
- [ ] **SETT-04**: Mental Models can contribute settings via a `settings` key in their manifest, which appear in the Settings page under the model's category

### Node Type Icons (ICON)

- [ ] **ICON-01**: Object explorer tree displays type-specific icons (from Lucide icon set) next to each object, with color coding
- [ ] **ICON-02**: Graph view nodes display type-appropriate colors and optional shape differentiation
- [ ] **ICON-03**: Mental Models can declare icon and color mappings for their types in the model manifest

### Event Log Explorer (EVNT)

- [ ] **EVNT-01**: Event log displays a paginated timeline of all events in reverse chronological order with operation type badge, affected object link, user, and timestamp
- [ ] **EVNT-02**: Events are filterable by operation type, user, object, and date range with removable filter chips
- [ ] **EVNT-03**: Clicking an object.patch or body.set event shows an inline diff of the changes (property before/after or line-by-line body diff)
- [ ] **EVNT-04**: Reversible events (object.patch, body.set, edge.create, edge.patch) have an Undo button that creates a compensating event after confirmation

### LLM Configuration (LLM)

- [ ] **LLM-01**: Admin can configure a generic OpenAI-compatible LLM connection (API base URL, API key, default model) via the Settings page
- [ ] **LLM-02**: API keys are stored server-side only (encrypted in database), never exposed to the browser
- [ ] **LLM-03**: A "Test Connection" button validates the configured endpoint and shows connection status
- [ ] **LLM-04**: A "Fetch Models" button retrieves available models from the configured provider
- [ ] **LLM-05**: Backend provides a streaming proxy endpoint (SSE) for LLM chat completions with proper nginx SSE configuration

### Tutorials and Documentation (DOCS)

- [ ] **DOCS-01**: A Docs & Tutorials page accessible from the Meta sidebar section lists available interactive tutorials and documentation links
- [ ] **DOCS-02**: Driver.js (MIT) is integrated for guided tours with lazy element resolution for htmx-rendered content
- [ ] **DOCS-03**: A "Welcome to SemPKM" tutorial walks through the workspace (sidebar, explorer, opening objects, read/edit toggle, command palette, saving)
- [ ] **DOCS-04**: A "Creating Your First Object" tutorial walks through creating an object from type selection to save

### Error Handling (ERR)

- [x] **ERR-01**: 403 Forbidden responses display a styled permission panel with lock icon, role explanation, and navigation buttons instead of a raw error fragment

## Deferred to Future Milestones

### AI Copilot (v2.1)

- **COPL-01**: AI Copilot chat interface in bottom panel that can query the knowledge graph and answer questions
- **COPL-02**: Smart assistant that suggests relationships, helps fill forms, and summarizes objects

### Workflow Engine (v2.1+)

- **WKFL-01**: Built-in workflow system (n8n-style) with event triggers
- **WKFL-02**: Mental models can define custom workflows in their manifest
- **WKFL-03**: Optional callout to external n8n instance

## Out of Scope

| Feature | Reason |
|---------|--------|
| Vertical/grid split panes | Horizontal-only delivers 80% value at 40% cost; expand in v2.1 |
| WYSIWYG Markdown editor | CodeMirror 6 with rendered read-only view is sufficient |
| Drag-and-drop file upload | No file storage backend exists |
| Floating/detachable panels | Extreme implementation cost for minimal gain |
| Mobile-responsive split panes | Bad UX on mobile; collapse to single pane |
| JSON settings editor | GUI-only for v2.0; JSON export/import later |
| Real-time collaborative editing | CRDT/OT complexity is months of work |
| Full AI copilot chat | Connection config is the foundation; copilot is v2.1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 10 | Complete |
| FIX-02 | Phase 10 | Complete |
| FIX-03 | Phase 10 | Complete |
| FIX-04 | Phase 10 | Complete |
| FIX-05 | Phase 10 | Complete |
| VIEW-01 | Phase 11 | Complete |
| VIEW-02 | Phase 11 | Pending |
| VIEW-03 | Phase 11 | Complete |
| VIEW-04 | Phase 11 | Pending |
| WORK-01 | Phase 14 | Pending |
| WORK-02 | Phase 14 | Pending |
| WORK-03 | Phase 14 | Pending |
| WORK-04 | Phase 14 | Pending |
| WORK-05 | Phase 14 | Pending |
| WORK-06 | Phase 13 | Complete |
| NAV-01 | Phase 12 | Complete |
| NAV-02 | Phase 12 | Complete |
| NAV-03 | Phase 12 | Complete |
| NAV-04 | Phase 12 | Complete |
| NAV-05 | Phase 12 | Complete |
| NAV-06 | Phase 12 | Complete |
| DARK-01 | Phase 13 | Complete |
| DARK-02 | Phase 13 | Complete |
| DARK-03 | Phase 13 | Complete |
| DARK-04 | Phase 13 | Complete |
| SETT-01 | Phase 15 | Pending |
| SETT-02 | Phase 15 | Pending |
| SETT-03 | Phase 15 | Pending |
| SETT-04 | Phase 15 | Pending |
| ICON-01 | Phase 15 | Pending |
| ICON-02 | Phase 15 | Pending |
| ICON-03 | Phase 15 | Pending |
| EVNT-01 | Phase 16 | Pending |
| EVNT-02 | Phase 16 | Pending |
| EVNT-03 | Phase 16 | Pending |
| EVNT-04 | Phase 16 | Pending |
| LLM-01 | Phase 17 | Pending |
| LLM-02 | Phase 17 | Pending |
| LLM-03 | Phase 17 | Pending |
| LLM-04 | Phase 17 | Pending |
| LLM-05 | Phase 17 | Pending |
| DOCS-01 | Phase 18 | Pending |
| DOCS-02 | Phase 18 | Pending |
| DOCS-03 | Phase 18 | Pending |
| DOCS-04 | Phase 18 | Pending |
| ERR-01 | Phase 13 | Complete |

**Coverage:**
- v2.0 requirements: 46 total
- Mapped to phases: 46/46
- Unmapped: 0

---
*Requirements defined: 2026-02-23*
*Last updated: 2026-02-23 — roadmap traceability complete*
