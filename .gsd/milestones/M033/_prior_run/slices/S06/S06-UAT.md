# S06 UAT: Graph View Icon Toggle

## Preconditions
- SemPKM running in Docker (`docker compose up`)
- At least one Mental Model installed (basic-pkm recommended — has types with Lucide icons configured)
- Objects exist in the triplestore (seed data or manually created)
- Browser open at the workspace (`/browser/`)

---

## Test Cases

### TC-01: Icon toggle button exists and is styled
**Steps:**
1. Open any graph view (e.g., explorer → VIEWS → Graph, or open an object tab → Relations graph)
2. Locate the graph toolbar (top of the graph panel)

**Expected:**
- An icon toggle button is visible in the toolbar alongside the Fit button
- Button shows a Lucide `image` icon
- Button matches the visual style of adjacent toolbar buttons (same size, padding, border-radius)
- Button is NOT in active state initially (no highlight color) unless icons were previously enabled

### TC-02: Toggling icons on — nodes show SVG icons
**Steps:**
1. Open a graph view with multiple node types visible
2. Note the current node appearance (colored shapes — circles, diamonds, etc.)
3. Click the icon toggle button

**Expected:**
- Button gains an active visual state (primary color highlight, `.active` class)
- Nodes transition from abstract shapes to showing Lucide SVG icons matching their type's configured icon
- Node backgrounds change to white (light theme) or dark (dark theme)
- Nodes gain a colored border matching their type color
- Edges remain visible and correctly connected

### TC-03: Toggling icons off — nodes revert to shapes
**Steps:**
1. With icons enabled (button in active state), click the icon toggle button again

**Expected:**
- Button loses active state (returns to default appearance)
- Nodes revert to their original abstract shape rendering (colored fills, no background images)

### TC-04: LocalStorage persistence across page reload
**Steps:**
1. Enable icon mode by clicking the toggle button
2. Verify `localStorage.getItem('sempkm_graph_icons')` returns `'true'` (DevTools → Console)
3. Reload the page (F5 / Ctrl+R)
4. Open the same graph view

**Expected:**
- Icon toggle button is in active state immediately
- Nodes render with icons without requiring another click
- `localStorage.getItem('sempkm_graph_icons')` still returns `'true'`

### TC-05: Persistence — disabling icons persists
**Steps:**
1. With icons enabled, click the toggle button to disable
2. Verify `localStorage.getItem('sempkm_graph_icons')` returns `'false'`
3. Reload the page
4. Open a graph view

**Expected:**
- Button is in default (inactive) state
- Nodes render as abstract shapes

### TC-06: Theme switching preserves icon state
**Steps:**
1. Enable icon mode
2. Switch the application theme (e.g., light → dark or dark → light)

**Expected:**
- Icons remain visible on nodes after theme switch
- Icon colors and node backgrounds update appropriately for the new theme
- Toggle button remains in active state

### TC-07: Isometric layout — layer planes excluded from icons
**Steps:**
1. Open a graph view
2. Select "Isometric" from the layout picker
3. Enable icon mode via the toggle button

**Expected:**
- Individual nodes within layers show Lucide icons
- The translucent layer plane backgrounds (compound parent nodes) do NOT show icons — they remain as plain translucent rectangles
- Layer labels are still visible

### TC-08: Missing icon graceful degradation
**Steps:**
1. Open DevTools Console
2. Enable icon mode on a graph where some types may not have icons configured

**Expected:**
- Types with valid Lucide icon names show icons normally
- Types without icons (or with invalid icon names) retain their original shape rendering — no crash, no blank nodes
- Console shows `[graph] Failed to create Lucide icon "..."` warnings for any lookup failures (if applicable)

### TC-09: Toggle before graph initialization
**Steps:**
1. Open DevTools Console
2. Navigate to a page without a graph view
3. Execute `toggleGraphIcons()` in the console

**Expected:**
- Console shows: `[graph] toggleGraphIcons called but no graph instance exists`
- No errors thrown, no crash

---

## Edge Cases

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| E1 | Empty graph (no nodes) | Toggle button works, no visual change, state persists |
| E2 | Graph with single node type | That type gets icons; toggle works normally |
| E3 | Rapid clicking toggle button | State settles to final click; no style corruption |
| E4 | Multiple graph tabs open | Each reads shared localStorage; toggling in one doesn't auto-update others (requires re-opening or manual style rebuild) |
