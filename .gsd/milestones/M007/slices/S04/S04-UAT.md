# S04: UI Polish & Consistency — UAT

**Milestone:** M007
**Written:** 2026-03-15

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: All changes are visual HTML/CSS — must be verified by inspecting the running UI.

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one mental model installed (for admin model pages)
- Browser open at `http://localhost:3000/browser`

## Smoke Test

Open the workspace at `/browser`. The left sidebar should show SVG chevron icons (not text triangles ▸) next to every section header. OBJECTS section should have refresh and plus buttons visible without hovering.

## Test Cases

### 1. Left sidebar chevrons render as Lucide SVGs

1. Open `http://localhost:3000/browser`
2. Inspect any section header chevron (e.g., OBJECTS) in browser DevTools
3. **Expected:** Element is `<svg>` (not `<span>`), rendered by Lucide from `data-lucide="chevron-right"`
4. Run in console: `document.querySelectorAll('.explorer-section-chevron').forEach(e => console.log(e.tagName))`
5. **Expected:** All entries log `svg` — should be 6 total (Favorites, Objects, Views, Dashboards, Workflows, Shared)

### 2. Chevrons rotate on expand/collapse

1. Click the VIEWS section header to expand it
2. Inspect the chevron's computed transform
3. **Expected:** Transform includes `rotate(90deg)` (or equivalent matrix) when expanded
4. Click again to collapse
5. **Expected:** Transform resets to `none`

### 3. OBJECTS header actions always visible

1. Open workspace, look at the OBJECTS section header
2. Do NOT hover over the header
3. **Expected:** Refresh (↻) and plus (+) buttons are visible at rest
4. Inspect computed style of `#section-objects .explorer-header-actions`
5. **Expected:** `opacity: 1`

### 4. DASHBOARDS plus-button opens builder

1. Expand the DASHBOARDS section in the left sidebar
2. Click the `+` button in the DASHBOARDS header
3. **Expected:** A "New Dashboard" builder tab opens in the main content area
4. **Expected:** The DASHBOARDS section does NOT toggle collapsed — `event.stopPropagation()` prevents it

### 5. No "New Dashboard" tree-leaf entry

1. Expand the DASHBOARDS section
2. Inspect the tree content
3. **Expected:** No entry with text "New Dashboard" appears as a tree-leaf action item

### 6. WORKFLOWS plus-button opens builder

1. Expand the WORKFLOWS section in the left sidebar
2. Click the `+` button in the WORKFLOWS header
3. **Expected:** A "New Workflow" builder tab opens in the main content area
4. **Expected:** The WORKFLOWS section does NOT toggle collapsed

### 7. No "New Workflow" tree-leaf entry

1. Expand the WORKFLOWS section
2. Inspect the tree content
3. **Expected:** No entry with text "New Workflow" appears as a tree-leaf action item

### 8. Inference button matches sibling sizing

1. Navigate to `http://localhost:3000/admin/models`
2. Look at the action buttons for any installed model (Inference, Refresh, Remove)
3. **Expected:** All three buttons are the same height (~32px) and vertically aligned
4. Inspect the Inference button in DevTools
5. **Expected:** Tag is `<button>` (not `<a>`)

### 9. Ontology Viewer has accent color

1. Open workspace at `/browser`
2. Expand the VIEWS section in the left sidebar
3. Find the "Ontology Viewer" entry
4. **Expected:** Label text is teal/blue accent color, distinct from other entries
5. Inspect element: should have class `view-leaf--accent`

### 10. Relationships graph renders horizontally

1. Navigate to admin → Mental Models → click any installed model
2. Click the "Relationships" tab
3. **Expected:** Graph renders with nodes flowing left-to-right (horizontal dagre layout)
4. **Expected:** Container is full-width, at least 600px tall
5. Inspect `.ontology-cy-container` dimensions: width should fill container, height ≥ 600px

## Edge Cases

### SHARED section chevron after htmx load

1. Open workspace — the SHARED section loads via htmx (may show briefly, then replace)
2. After the htmx response loads, inspect the SHARED section chevron
3. **Expected:** Still an SVG, not reverted to `<span>` text triangle (shared_nav_content.html was also updated)

### Narrow sidebar doesn't break chevrons

1. Drag the sidebar resize handle to make the sidebar narrow (~200px)
2. **Expected:** Chevron SVGs still visible, not clipped. Section headers remain legible.

### Plus-buttons don't toggle section

1. Click the `+` button on DASHBOARDS header rapidly 3 times
2. **Expected:** Builder tabs open (or the same tab activates). The section stays in its current expanded/collapsed state — it does not toggle with each click.

## Failure Signals

- Text triangle characters (▸ or ▶) visible instead of SVG chevrons
- OBJECTS buttons only appear on hover
- "New Dashboard" or "New Workflow" text entries visible in expanded tree sections
- Inference button is taller/shorter than Remove/Refresh siblings
- Ontology Viewer label is same color as other view entries
- Relationships graph renders top-to-bottom instead of left-to-right
- Console errors related to Lucide icon initialization

## Requirements Proved By This UAT

- UIPOL-01 — All 6 items: chevrons, button visibility, header plus-buttons, inference sizing, accent color, graph layout

## Not Proven By This UAT

- Long-term CSS regressions from future template changes
- Behavior on browsers other than Chromium (WebKit/Firefox chevron rotation, dagre rendering)

## Notes for Tester

- Pre-existing issue: OBJECTS header buttons slightly clipped when sidebar is very narrow. This predates S04.
- The SHARED section may flash briefly before htmx replaces it — this is normal lazy-load behavior.
- Dagre layout requires the cytoscape-dagre extension loaded via CDN — if offline, the graph may fall back to a default layout.
