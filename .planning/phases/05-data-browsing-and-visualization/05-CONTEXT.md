# Phase 5: Data Browsing and Visualization - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Users browse, filter, and explore their knowledge through table, cards, and graph views. The system executes view specs (SPARQL query + renderer type + layout config) to render views, enabling Mental Models to define custom browsing experiences. Views integrate into the IDE workspace from Phase 4 as center-pane tabs.

</domain>

<decisions>
## Implementation Decisions

### Table View
- Columns auto-generated from SHACL properties (sh:order for column order, sh:name for headers) as defaults
- Users can customize which columns are visible and their order — saved as a preference per type
- Traditional numbered pagination with prev/next, total count, and jump-to-page
- Columns are sortable

### Cards View
- Flippable cards with CSS flip animation
- Front: object title/label + first ~100 chars of Markdown body snippet
- Back: all properties + outbound and inbound relationships
- Flip toggle button in upper-right corner of each card
- Flat card grid by default — no grouping. User can optionally enable grouping by a property
- Same numbered pagination as table view

### Graph Visualization
- Default layout: force-directed
- Layout picker with options: force-directed, hierarchical, radial — plus Mental Models can register custom layout algorithms
- Semantic-aware styling: Mental Models define node colors and edge styles in their shapes — falls back to auto-assigned color palette if not defined by model
- Interaction: click a node to select it (shows details in right pane), double-click to expand its neighbors into the graph
- Graph scope is contextual — shows whatever the user is currently browsing (type, search results, or full graph). Starts with everything in the current context visible
- Pan and zoom for navigation

### View Specs System
- View specs defined by both Mental Models (packaged with the model) and users at runtime (saved per-user)
- Built-in renderer types: table, cards, graph
- Mental Models can register custom renderer types (e.g., timeline, kanban, calendar) — extensible renderer registry
- Installing a model automatically makes its view specs available for the types it targets — zero config, auto-appear
- Views discoverable via both a view menu (grouped by model vs user-created) and the command palette ("Open view: ...")

### View Switching & Navigation
- Views open as tabs in the center pane alongside object tabs — shared tab bar
- Each view type opens in its own tab — user can have table and graph of the same data open simultaneously
- Filters and sort state persist when switching between view types for the same data set
- Clicking an object in any view (table row, card, graph node) opens it in a new editor tab — view stays where it is

### Claude's Discretion
- Filter UI design (sidebar vs inline vs toolbar)
- Graph rendering library choice (e.g., D3, Cytoscape, Sigma.js)
- Card grid responsive layout breakpoints
- View spec storage format and schema
- Custom renderer registration API design

</decisions>

<specifics>
## Specific Ideas

- Flippable cards are a distinctive UX element — front shows title + snippet for scanning, back reveals full structured data (properties + relationships)
- Mental Models are first-class participants in the visualization system: they define node/edge styles, custom layouts, custom renderer types, and view specs
- The graph is always contextual to what the user is looking at, not a disconnected standalone visualization

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-data-browsing-and-visualization*
*Context gathered: 2026-02-22*
