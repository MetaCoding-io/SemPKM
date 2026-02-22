# Phase 4: Admin Shell and Object Creation - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Users manage the system (models, webhooks) through an admin portal and create, edit, and inspect objects through SHACL-driven forms in an IDE-style workspace with validation feedback. The application is structured as a dashboard at `/` that hosts multiple apps: Admin, Object Browser, and Health Check (existing).

</domain>

<decisions>
## Implementation Decisions

### Dashboard Architecture
- Root `/` is an htmx dashboard with a two-column layout: left sidebar with app links, right area shows the selected app
- Apps hosted by the dashboard: Admin (`/admin/`), Object Browser (IDE workspace), Health Check (existing)
- Left sidebar uses simple icon + label links — no badges or status indicators

### Workspace Layout
- Three-column layout: navigation tree (left) + editor/form (center) + properties/details (right) — like VS Code or JetBrains
- Left navigation tree organizes objects by type — top-level nodes are object types (Person, Note, Project...), objects nested under their type
- Persistent tabs — each opened object gets its own tab, stays open until explicitly closed
- Command palette supports full workspace control: object actions + toggle panels, switch views, run validation, manage models — everything reachable from keyboard

### SHACL Form Generation
- Type selection: both a type picker dialog (browse-and-choose) and command palette ("New Object" inline) for keyboard-first users
- Property groups (sh:group) render as collapsible sections — all expanded by default, user can collapse to focus
- Required fields shown first; optional fields collapsed in an "Advanced" section
- sh:in constraints use dropdown select (standard dropdown for single values, multi-select for lists)
- sh:class references use search-as-you-type dropdown with "Create new..." option that opens a nested form for the target type
- sh:defaultValue pre-filled in form fields, visually distinguishable (e.g., lighter text) until user modifies
- Multi-valued properties use add/remove button pattern — each value has a remove button, "+" button below to add another
- sh:order defines default field order, but users can drag to reorder (preference saved per user)
- Date/time properties (xsd:date, xsd:dateTime) get calendar picker widgets
- Human-readable labels (sh:name, rdfs:label) shown everywhere; hovering reveals the full URI/prefixed name as a tooltip

### Object Editing & View
- Objects open in always-editable mode — no separate view/edit toggle
- Center pane uses split view: properties form on top, Markdown body editor below — both visible at once
- Markdown body uses a rich editor (CodeMirror or similar) with syntax highlighting, toolbar, and live preview side-by-side
- Explicit save (Ctrl+S or Save button) — unsaved changes indicated by a dot on the tab
- Object detail page shows properties + body + related objects (inbound + outbound edges)
- Related objects listed in the right pane — always visible alongside the object

### Admin Portal
- Model management: table listing installed models with Install, Remove, and View Details actions per row
- Webhook configuration: target URL + event selection (object.changed, edge.changed, validation.completed) + optional filters (e.g., only fire for specific object types or namespaces)

### Validation & Lint Panel
- SHACL validation runs live as the user types, with debounce — instant feedback
- **Accepted deviation:** Live-as-you-type SHACL validation downgraded to two-tier approach: (1) client-side instant checks for required fields on blur, (2) server-side full SHACL validation triggered on save. This avoids excessive triplestore round-trips while still providing meaningful feedback. User accepted this approach during planning.
- Lint panel lives as a tab in the right pane alongside properties/relations
- Violations and warnings distinguished by color-coded icons: red circle for violations, yellow triangle for warnings
- Clicking an issue jumps to and highlights the offending field, plus shows the validation message inline below the field
- Violations block conformance-required operations (export); warnings never block

### Claude's Discretion
- Exact resizing behavior for panes (min widths, drag handles, etc.)
- Loading states and skeleton designs
- Error handling patterns (network errors, save failures)
- Exact CodeMirror configuration and toolbar buttons
- Command palette search/fuzzy-matching implementation
- Dashboard visual styling and spacing

</decisions>

<specifics>
## Specific Ideas

- Dashboard is htmx-based with a persistent left sidebar linking to hosted apps
- Object browser workspace should feel like an IDE (VS Code/JetBrains mental model)
- Forms should respect the full SHACL shape vocabulary: sh:property, sh:order, sh:group, sh:name, sh:datatype, sh:class, sh:in, sh:defaultValue
- Labels + URI on hover gives users human-readable UX while preserving access to the underlying RDF identifiers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-admin-shell-and-object-creation*
*Context gathered: 2026-02-22*
