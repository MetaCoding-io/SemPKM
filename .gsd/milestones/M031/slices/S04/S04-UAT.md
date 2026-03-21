# S04: Kanban Renderer — UAT Script

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed that has a type with `sh:in` status values (basic-pkm Task type has `bpkm:taskStatus` with `todo`, `in-progress`, `done`, `cancelled`)
- At least 3 Task objects exist with different status values (e.g., one todo, one in-progress, one done)
- Browser open to workspace (`http://localhost:3000/browser`)

---

## Test Case 1: Open Kanban View from Explorer

**Steps:**
1. In the explorer sidebar, locate the **Views** section
2. Click **Kanban View**

**Expected:**
- A new tab opens titled "Kanban View"
- The kanban board area shows a message: "Select a type to use Kanban View" (no type selected yet)
- The view toolbar is visible at the top
- No carousel tab bar is present

---

## Test Case 2: Select Type with Status Property

**Steps:**
1. With the Kanban View tab active, click the **Task** type filter pill in the type filter bar

**Expected:**
- Kanban board renders with columns for each status value defined in `sh:in` (e.g., "Todo", "In Progress", "Done", "Cancelled")
- Each column header shows the status label and a count badge
- Task objects appear as cards in their respective status columns
- Each card shows the object label

---

## Test Case 3: Drag Card Between Columns

**Steps:**
1. With Task kanban visible, pick up a card from the "Todo" column
2. Drag it over the "In Progress" column body
3. Drop the card

**Expected:**
- While dragging: the source card has a visual drag state (reduced opacity)
- While hovering over target column: the column body shows a drag-over highlight
- On drop: the card moves immediately to the "In Progress" column (optimistic DOM move)
- Column count badges update (Todo decrements, In Progress increments)
- Network tab shows a `POST /api/commands` request with payload:
  ```json
  {"command": "object.patch", "params": {"iri": "<task-iri>", "properties": {"<status-predicate>": "in-progress"}}}
  ```
- No dockview panel drag is triggered (the tab does not detach or move)

---

## Test Case 4: Drag-Drop Does Not Trigger Dockview Panel Drag

**Steps:**
1. With the Kanban View tab active and columns visible, initiate a drag on a kanban card
2. Move the mouse around within the kanban board area
3. Drop on a different column

**Expected:**
- Only the kanban card is being dragged — no dockview panel chrome (tab header, panel borders) reacts to the drag
- The dockview panel remains stationary throughout the drag operation
- This confirms `stopPropagation()` isolation is working

---

## Test Case 5: Failed Patch Shows Error

**Steps:**
1. Simulate a network failure (e.g., disconnect the API container or use DevTools to block `/api/commands`)
2. Drag a kanban card from one column to another

**Expected:**
- Card moves to the target column optimistically
- After the POST fails, the card reverts back to its original column
- A toast notification or error message appears
- Browser console shows: `kanban: failed to patch status for <iri> <error>`

---

## Test Case 6: Type with No Status Property

**Steps:**
1. Open Kanban View
2. Click a type filter pill for a type that has no `sh:in` properties (e.g., Person or Note)

**Expected:**
- The kanban board shows a user-facing message: "This type has no status-like properties for Kanban grouping"
- No columns are rendered
- No JavaScript errors in the console

---

## Test Case 7: Kanban View with Scope Query

**Steps:**
1. Open Kanban View
2. Select the Task type filter pill
3. In the view toolbar, select a saved query from the scope dropdown (if one exists that filters tasks)

**Expected:**
- The kanban re-renders with only objects matching the saved query scope
- Column counts reflect the filtered set
- URL updates to include `scope_query=<query-id>` parameter

---

## Test Case 8: Multiple Kanban Tabs

**Steps:**
1. Open Kanban View from the explorer — first tab opens
2. Click Kanban View in the explorer again

**Expected:**
- A second Kanban View tab opens (separate from the first)
- Both tabs can have independent type selections
- Dragging cards in one tab does not affect the other

---

## Test Case 9: Kanban Card Dispatches Command Event

**Steps:**
1. Open browser DevTools console
2. Add event listener: `document.addEventListener('sempkm:command-executed', () => console.log('EVENT FIRED'))`
3. Drag a kanban card to a different column

**Expected:**
- Console logs "EVENT FIRED" after the successful drop
- Other UI components that react to `sempkm:command-executed` (e.g., explorer refresh) update accordingly

---

## Test Case 10: Canvas Drag-Drop for Kanban View

**Steps:**
1. Open the spatial canvas
2. In the explorer sidebar, drag the "Kanban View" entry onto the canvas

**Expected:**
- A scoped view widget appears on the canvas containing the kanban board
- The widget renders with `embed=1` parameter (no outer chrome)

---

## Edge Cases

- **No objects exist for the selected type:** Columns render but are empty — no error
- **All objects have the same status:** Only one column has cards, others are empty
- **Object has an unrecognized status value:** Card appears in an "Unset" column appended at the end
- **Rapid consecutive drags:** Each drag-drop fires its own `object.patch` — no race condition (each operates on a different object)
- **dragLeave between child elements:** Moving cursor between card elements within a column body should NOT remove the drag-over highlight (contains(relatedTarget) guard)
