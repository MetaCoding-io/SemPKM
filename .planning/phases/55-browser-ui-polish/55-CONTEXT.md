# Phase 55: Browser UI Polish - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Object browser and VFS browser have polished, productive interactions for daily use. Nav tree gets header controls (refresh, create), multi-select with bulk delete, edge inspector in the Relations panel, and VFS browser gets a side-by-side preview mode with consistent file operation polish.

</domain>

<decisions>
## Implementation Decisions

### Nav tree header controls
- Refresh and plus buttons live in the **OBJECTS section header** (inline with "OBJECTS" title, right-aligned)
- Buttons show **on hover only** (hidden by default, appear when hovering the section header) — matches VS Code Explorer pattern
- **Refresh** does a full reload: re-fetches the type list and collapses all expanded children (they lazy-load again on click)
- **Plus** button opens the command palette (Ctrl+K)
- Rename existing "new object" command palette entry to **"Create new object"**
- Add per-type create entries: "Create Note", "Create Project", etc. — all prefixed with "Create" so typing "create" in the palette shows them all
- The create form **opens in a dockview tab** (not inline/overlay)

### Multi-select & bulk delete
- **Shift-click** for range selection, **Ctrl+click** to toggle individual items — standard OS file manager pattern
- No checkboxes — selection indicated by **background highlight color**
- Selection is **independent from tab navigation**: shift/ctrl+click selects without opening tabs; regular click still opens tabs as before
- When items are selected, the OBJECTS section header shows **"[N selected]" count badge + trash icon** (next to refresh/plus)
- **Delete confirmation**: modal dialog listing selected objects — "Delete N objects? This cannot be undone." with Cancel/Delete buttons
- Deleted objects' open tabs are **not automatically closed** (selection and tabs are independent)

### Edge inspector in Relations panel
- **Click to expand inline** — clicking a relation item expands it in-place to show provenance below (no navigation). A separate **open icon** (arrow/external link) navigates to the target object
- Expanded detail shows **all four metadata fields**:
  - Predicate IRI as QName (e.g., `skos:related`)
  - Creation timestamp + author (who created the edge, when)
  - Source: user-asserted vs OWL-inferred
  - Edge event link — clickable, opens the **Event Log tab in the bottom panel** filtered/scrolled to that specific event
- **Delete button** (trash icon) shown in expanded detail for user-asserted edges only (not inferred). Confirms before deleting
- Inferred edges show provenance but no delete option

### VFS preview & polish
- **Side-by-side horizontal split**: raw (CodeMirror) on left, rendered markdown on right. Resize handle between them
- Preview is **toggled via a button** in the file tab bar (default: off, showing only raw editor). Button shows/hides the rendered pane
- Markdown rendering uses **existing marked.js + DOMPurify** from `markdown-render.js` — consistent with object read view, no new dependencies
- **File operation polish** (all four areas):
  - Save indicator: dot on tab when dirty, brief "Saved" flash on successful PUT
  - Edit/read toggle: consistent Lucide lock/unlock icon replacing text button
  - Loading states: spinner when loading tree, file content, and saving
  - Error feedback: toast or inline error for save failures, file not found, permission denied
- **Inline VFS help**: small info section or tooltip in the VFS browser explaining how to connect your OS to the WebDAV endpoint (mount instructions)

### Claude's Discretion
- Exact CSS values for selection highlight, hover animations, and transition timing
- Spinner implementation choice (CSS animation vs Lucide loader icon)
- Edge provenance API query strategy (single SPARQL query vs event store lookup)
- VFS help text content and placement (tooltip, collapsible section, or info banner)
- Modal dialog styling and animation

</decisions>

<specifics>
## Specific Ideas

- OBJECTS section header buttons should match the VS Code Explorer pattern: hidden until hover, subtle icons
- "Create" prefix convention in command palette so all create actions cluster when typing "create"
- Edge inspector expansion should feel like VS Code's git changes panel: click expands detail, separate icon opens the file
- VFS preview toggle follows the VS Code markdown preview pattern (side-by-side, toggled)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `markdown-render.js` (marked.js + DOMPurify): Reuse for VFS rendered preview
- `ninja-keys` command palette: Extend with per-type "Create X" entries
- `properties.html` Relations panel: Extend relation items with expandable detail
- Explorer section header pattern (`workspace.html` lines 26-31): Extend with action buttons
- `vfs-browser.js` file tabs: Extend with preview toggle button
- `vfs-browser.css` `.vfs-tree-header`: Reference for consistent button styling
- Inferred badge in `properties.html` line 32-33: Already distinguishes user vs inferred edges

### Established Patterns
- htmx-driven DOM updates for tree loading (`hx-get`, `hx-trigger="click once"`)
- Lucide icons with `flex-shrink: 0` (CLAUDE.md rule)
- Dockview panels for tabbed content (`workspace-layout.js`)
- Event log in bottom panel with filter/scroll capability
- `panel-btn` CSS class for header action buttons

### Integration Points
- `nav_tree.html` — Add section header action buttons
- `workspace.html` OBJECTS section header — Add hover-reveal buttons
- `properties.html` relation items — Convert from simple click-to-open to expandable
- `vfs-browser.js` — Add preview pane toggle and rendering
- Command palette entries — Add per-type create shortcuts
- Bottom panel Event Log — Accept deep-link to specific event (for edge inspector)
- `workspace.js` — Handle multi-select state in tree, bulk delete API calls

</code_context>

<deferred>
## Deferred Ideas

- Full Driver.js guided tour for VFS setup — a tutorial is a new capability, belongs in its own phase. Inline help text is in scope.

</deferred>

---

*Phase: 55-browser-ui-polish*
*Context gathered: 2026-03-09*
