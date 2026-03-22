# S01 UAT: GridStack Layout Engine + Block Registry

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (basic-pkm) with some objects
- Logged in as owner or member
- At least one existing dashboard created with an old layout (e.g., `grid-2x2`)

---

## Test 1: Block Registry Backend Validation

**Goal:** Verify the BlockRegistry validates block types and rejects invalid input.

1. Open a shell in the backend container: `docker compose exec api bash`
2. Run: `python -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"`
   - **Expected:** Prints `['create-form', 'divider', 'markdown', 'object-embed', 'sparql-result', 'view-embed']`
3. Run: `python -c "from app.dashboard.registry import BLOCK_REGISTRY; print({k: [s.type_name for s in v] for k, v in BLOCK_REGISTRY.by_category().items()})"`
   - **Expected:** Three categories printed: `content` (markdown, object-embed), `data` (view-embed, create-form, sparql-result), `layout` (divider)
4. Run: `python -c "from app.dashboard.registry import BLOCK_REGISTRY; BLOCK_REGISTRY.validate_block({'type':'bogus','config':{}})"`
   - **Expected:** `ValueError: Invalid block type: 'bogus'. Must be one of [...]`
5. Run: `python -c "from app.dashboard.registry import BLOCK_REGISTRY; BLOCK_REGISTRY.validate_block({'type':'markdown','config':{'content': 123}})"`
   - **Expected:** `ValueError` mentioning wrong type for config key 'content' (expected str)

---

## Test 2: Dashboard Builder — New Dashboard with GridStack

**Goal:** Verify the builder renders a GridStack canvas and blocks can be placed, repositioned, resized, and saved.

1. Navigate to the workspace
2. Click the **+** button next to the DASHBOARDS section in the explorer sidebar (or use command palette to create a new dashboard)
3. **Expected:** Dashboard builder opens in a dockview tab with:
   - Header area with name and description fields
   - Left sidebar palette with 3 categories: **Content** (Markdown, Object Embed), **Data** (View Embed, Create Form, SPARQL Result), **Layout** (Divider)
   - Right area: empty 12-column GridStack canvas
4. Click the **Markdown** palette item
   - **Expected:** A markdown widget appears on the canvas with a header showing "markdown" label and a trash (×) button, plus a textarea for content
5. Click the **View Embed** palette item
   - **Expected:** A second widget appears on the canvas below or beside the first, with a select dropdown for choosing a view
6. Drag the markdown widget to a different position on the grid
   - **Expected:** Widget snaps to grid cells during drag, other widgets reflow as needed
7. Resize the markdown widget by dragging its bottom-right handle
   - **Expected:** Widget resizes in grid-cell increments
8. Type "# Hello World" in the markdown widget's textarea
9. Enter a name in the Name field (e.g., "Test Dashboard")
10. Click **Save**
    - **Expected:** Success — console shows `[dashboard-builder] Saved dashboard <id> with 2 blocks at gridstack positions`. Network tab shows POST to `/api/dashboard` with `layout: "gridstack"` and blocks array where each block has `x, y, w, h` fields.

---

## Test 3: Dashboard Page — Render Saved GridStack Layout

**Goal:** Verify the dashboard page renders blocks at saved positions in read-only mode.

1. After saving the dashboard in Test 2, open it from the DASHBOARDS section in the explorer sidebar
2. **Expected:** Dashboard page renders with:
   - The markdown block at the position/size set in the builder
   - The view embed block at its saved position
   - No drag handles or resize cursors (static mode)
3. Try to drag a block
   - **Expected:** Nothing happens — blocks are locked in place
4. Right-click → Inspect one of the `.grid-stack-item` elements
   - **Expected:** Has `gs-no-resize="true"` and `gs-no-move="true"` attributes
   - Has `gs-x`, `gs-y`, `gs-w`, `gs-h` attributes matching saved positions

---

## Test 4: Edit Existing Dashboard — Positions Preserved

**Goal:** Verify editing loads saved positions back onto the GridStack canvas.

1. Open the dashboard builder for the dashboard created in Test 2 (Edit mode)
2. **Expected:** Builder loads with:
   - Name field pre-filled with "Test Dashboard"
   - Both blocks appear on the GridStack canvas at their saved positions and sizes
   - Config fields pre-populated (markdown textarea has "# Hello World")
3. Add a third block (e.g., Divider)
4. Reposition it
5. Click Save
   - **Expected:** Dashboard updates successfully with 3 blocks, all with `x, y, w, h` positions

---

## Test 5: Auto-Migration from Legacy Layout

**Goal:** Verify old CSS Grid dashboards auto-migrate to GridStack positions on first view.

1. Create a dashboard with an old layout via the API:
   ```bash
   curl -X POST http://localhost:3901/api/dashboard \
     -H "Content-Type: application/json" \
     -b "session=<your_session_cookie>" \
     -d '{
       "name": "Legacy Test",
       "layout": "grid-2x2",
       "blocks": [
         {"type": "markdown", "slot": "top-left", "config": {"content": "TL"}},
         {"type": "markdown", "slot": "top-right", "config": {"content": "TR"}},
         {"type": "markdown", "slot": "bottom-left", "config": {"content": "BL"}},
         {"type": "markdown", "slot": "bottom-right", "config": {"content": "BR"}}
       ]
     }'
   ```
2. Note the returned dashboard ID
3. Open the dashboard from the DASHBOARDS section in the explorer
4. **Expected:** All 4 blocks render in a 2×2 grid layout on the GridStack canvas:
   - top-left at position (0, 0, 6, 4)
   - top-right at position (6, 0, 6, 4)
   - bottom-left at position (0, 4, 6, 4)
   - bottom-right at position (6, 4, 6, 4)
5. Fetch the dashboard via API: `GET /api/dashboard/<id>`
   - **Expected:** `layout` is now `"gridstack"` and each block has `x, y, w, h` fields — migration was persisted

---

## Test 6: All 6 Block Types in GridStack

**Goal:** Verify all existing block types render inside GridStack widgets.

1. Create a dashboard in the builder with all 6 block types:
   - Markdown (enter some content)
   - View Embed (select any available view)
   - Object Embed (search for an object if objects exist)
   - Create Form (select a type)
   - SPARQL Result (enter a simple query like `SELECT ?s WHERE { ?s a ?t } LIMIT 5`)
   - Divider
2. Save the dashboard
3. Open the dashboard page
4. **Expected:** 
   - Markdown block renders the markdown content
   - View Embed shows the embedded view (htmx-loaded)
   - Object Embed shows the embedded object
   - Create Form shows the create form for the selected type
   - SPARQL Result shows query results (htmx-loaded)
   - Divider renders as a visual separator
5. No block overflows its GridStack widget boundary (check for scrollbar or clipping)

---

## Test 7: Dockview Event Isolation

**Goal:** Verify GridStack drag/drop does not interfere with dockview panel management.

1. Open the dashboard builder in a dockview tab
2. Open another tab (e.g., an object tab) alongside the builder
3. Drag a block on the GridStack canvas
   - **Expected:** Block moves within the canvas; the dockview tab does NOT start dragging or detaching
4. Drag a palette item onto the canvas
   - **Expected:** New widget created on canvas; no dockview panel movement
5. Drag the dockview tab header of the builder tab
   - **Expected:** Normal dockview tab drag behavior (tab can be moved between groups)

---

## Test 8: Layout Migration — All 5 Legacy Layouts

**Goal:** Verify all 5 old layouts migrate correctly (unit test level).

1. In the backend container, run:
   ```bash
   python -m pytest tests/test_layout_migration.py -v
   ```
2. **Expected:** All 14 tests pass, covering:
   - `single` → blocks stack at full width (12 cols)
   - `sidebar-main` → sidebar at (0,0,4,h), main at (4,0,8,h)
   - `grid-2x2` → 4 quadrants at (0,0), (6,0), (0,4), (6,4)
   - `grid-3` → 3 columns at (0,0,4,h), (4,0,4,h), (8,0,4,h)
   - `top-bottom` → 2 rows at (0,0,12,h) and (0,4,12,h)
   - Edge cases: unmatched slots, already-gridstack, missing positions, empty blocks, unknown layout raises error

---

## Edge Cases

### E1: Dashboard with no blocks
1. Create a new dashboard, don't add any blocks, click Save
   - **Expected:** Dashboard saves with empty blocks array. Dashboard page shows empty grid.

### E2: Browser refresh during builder
1. Open builder, add 2 blocks, do NOT save, refresh the page
   - **Expected:** Unsaved changes lost (no localStorage persistence). Builder reopens clean.

### E3: Large number of blocks
1. Add 10+ blocks to a dashboard, position them across multiple rows
   - **Expected:** All blocks render, scrolling works, save includes all blocks with positions.
