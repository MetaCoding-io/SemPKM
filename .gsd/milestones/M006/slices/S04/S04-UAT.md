# S04: Dashboard Builder UI & Explorer Integration — UAT

**Milestone:** M006
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All verification can be done through route tests and Docker browser inspection. No live runtime external dependencies beyond the existing triplestore.

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (e.g. basic-pkm) so view-embed specs are available
- User logged in to workspace

## Smoke Test

Open the workspace, look for "DASHBOARDS" section in the explorer sidebar. Click "+ New Dashboard" — builder form should open in a new tab with layout picker and block configuration.

## Test Cases

### 1. Create a dashboard via the builder

1. In the explorer sidebar, locate the DASHBOARDS section
2. Click "+ New Dashboard"
3. Builder tab opens with empty form
4. Enter name: "Test UAT Dashboard"
5. Enter description: "Created during UAT"
6. Select the "sidebar-main" layout
7. Click "+ Add Block"
8. Set block type to "markdown", slot to "sidebar"
9. Enter markdown content: "# Hello\nThis is a test block."
10. Click "+ Add Block" again
11. Set block type to "view-embed", slot to "main"
12. Select a view spec from the dropdown and renderer "table"
13. Click "Save Dashboard"
14. **Expected:** Builder tab closes, a new tab opens showing the rendered dashboard with the markdown block in the sidebar slot and the view-embed block in the main slot

### 2. Dashboard appears in explorer after creation

1. After creating a dashboard in Test 1
2. Look at the DASHBOARDS section in the explorer sidebar
3. **Expected:** "Test UAT Dashboard" appears as a clickable leaf node in the list

### 3. Open dashboard from explorer

1. In the DASHBOARDS explorer section, click "Test UAT Dashboard"
2. **Expected:** Dashboard renders in a workspace tab showing the configured blocks

### 4. Edit a dashboard via the pencil button

1. Open "Test UAT Dashboard" by clicking it in the explorer
2. In the dashboard header bar, click the pencil (edit) icon
3. **Expected:** Builder tab opens in edit mode with name "Test UAT Dashboard", description "Created during UAT", layout "sidebar-main", and the two configured blocks pre-populated
4. Change the name to "Test UAT Dashboard (Edited)"
5. Click "Save Dashboard"
6. **Expected:** Builder closes, dashboard tab reopens with the updated name in the header

### 5. Explorer refreshes after edit

1. After editing the dashboard in Test 4
2. Check the DASHBOARDS explorer section
3. **Expected:** The list shows "Test UAT Dashboard (Edited)" (updated name)

### 6. Create dashboard with all block types

1. Click "+ New Dashboard" in the explorer
2. Name: "All Block Types"
3. Select "full-width" layout
4. Add blocks one at a time, each with type:
   - "markdown" — enter some content text
   - "view-embed" — select a spec, choose "cards" renderer
   - "create-form" — enter a class IRI (e.g. `urn:sempkm:basic-pkm:Note`)
   - "divider" — no config fields should appear
5. Click "Save Dashboard"
6. **Expected:** Dashboard renders with all 4 block types visible in the full-width layout

### 7. Builder validation — empty name

1. Click "+ New Dashboard"
2. Leave the name field empty
3. Click "Save Dashboard"
4. **Expected:** Error message "Name is required." appears inline in the builder. No network request is sent. Builder stays open.

## Edge Cases

### Empty explorer state

1. If no dashboards exist yet, open the workspace
2. Look at the DASHBOARDS explorer section
3. **Expected:** Shows "No dashboards yet" message and the "+ New Dashboard" action

### Edit with invalid dashboard ID

1. Navigate to `/browser/dashboard/99999/edit` directly
2. **Expected:** Returns 404 or displays an error (dashboard not found)

### Multiple block rows with same slot

1. Open builder, select "two-column" layout
2. Add two blocks, both assigned to slot "left"
3. Save the dashboard
4. **Expected:** Dashboard renders with both blocks stacked in the left column

### Cancel from builder

1. Open builder, fill in some fields
2. Click "Cancel"
3. **Expected:** Builder tab closes. No dashboard is created. Explorer list unchanged.

## Failure Signals

- DASHBOARDS section missing from explorer sidebar → `workspace.html` include broken
- Builder opens but layout picker is empty → `LAYOUT_DEFINITIONS` not passed in template context
- Save button does nothing → fetch() JS error; check browser console for "Dashboard save error:"
- Dashboard appears in explorer but clicking doesn't open → `openDashboardTab()` wiring broken
- Edit button missing from rendered dashboard → `dashboard_page.html` header bar not added
- Explorer doesn't refresh after create → `dashboardsRefreshed` htmx event not dispatched
- `#builder-error` shows "Name is required" when name is provided → client-side validation bug

## Requirements Proved By This UAT

- User can create a DashboardSpec via the UI, choosing a grid layout and assigning blocks to slots (milestone success criterion)
- Dashboards appear in the explorer sidebar (milestone success criterion, partial — workflows in S07)

## Not Proven By This UAT

- Cross-view filtering (S05 — parameterized SPARQL, interactive context)
- Workflow creation and running (S06/S07)
- Dashboard delete from UI (S07)
- Persistence across Docker restart (milestone-level verification)

## Notes for Tester

- The view-embed spec dropdown fetches lazily from `/browser/views/available` — if no Mental Models are installed, the dropdown will be empty. Install basic-pkm first.
- The `sparql-result` and `object-embed` block types require manual IRI entry — these are less common and harder to test without knowing specific IRIs in the triplestore.
- Delete is only available via API (`DELETE /api/dashboard/{id}`) — no UI delete button yet.
