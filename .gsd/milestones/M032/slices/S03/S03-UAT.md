# S03: Multi-Object Form Groups — UAT Script

## Preconditions

- Docker stack running (`docker compose up -d`) with triplestore healthy
- At least one Mental Model installed with SHACL shapes (e.g., basic-pkm with Project, Task types)
- A dashboard exists (create one via the builder if not)
- Browser open at `http://localhost:8080`

---

## Test 1: Batch Endpoint — Valid Slot Resolution

**Purpose:** Verify `POST /api/commands/batch` creates linked objects atomically with slot-based IRI cross-references.

1. Open browser DevTools → Console or use `curl`
2. POST to `/api/commands/batch` with:
   ```json
   {
     "commands": [
       {"command_type": "object.create", "params": {"type_iri": "<Project type IRI>", "properties": {"dcterms:title": "UAT Project"}}, "_slot_id": "project1"},
       {"command_type": "object.create", "params": {"type_iri": "<Task type IRI>", "properties": {"dcterms:title": "UAT Task"}}, "_slot_id": "task1"},
       {"command_type": "edge.create", "params": {"source": "$slot:task1", "target": "$slot:project1", "predicate": "bpkm:relatedTo"}}
     ]
   }
   ```
3. **Expected:** HTTP 200 response containing:
   - `event_iri` (non-empty string)
   - `operation_count: 3`
   - `affected_count >= 2`
   - `slot_map` with `{"project1": "<IRI>", "task1": "<IRI>"}` — both real IRIs
4. Navigate to Object Browser → verify "UAT Project" and "UAT Task" exist
5. Open "UAT Task" → Relations panel → verify edge to "UAT Project" exists

---

## Test 2: Batch Endpoint — Unresolved Slot Error

**Purpose:** Verify server rejects commands with forward references or missing slots.

1. POST to `/api/commands/batch` with:
   ```json
   {
     "commands": [
       {"command_type": "edge.create", "params": {"source": "$slot:nonexistent", "target": "$slot:also-missing", "predicate": "bpkm:relatedTo"}},
       {"command_type": "object.create", "params": {"type_iri": "<Project type IRI>"}, "_slot_id": "project1"}
     ]
   }
   ```
2. **Expected:** HTTP 400 with error message naming `$slot:nonexistent` as unresolved

---

## Test 3: Batch Endpoint — Empty Commands

**Purpose:** Verify server rejects empty batch requests.

1. POST to `/api/commands/batch` with `{"commands": []}`
2. **Expected:** HTTP 400 or 422 error

---

## Test 4: Form-Group Block in Dashboard Builder

**Purpose:** Verify the builder config panel for form-group blocks.

1. Open Dashboard Builder (create new or edit existing dashboard)
2. Click the block palette → find "Form Group" in the Data category (icon: layers)
3. Click to add the block to the canvas
4. **Expected:** A form-group block appears on the GridStack canvas
5. Click the block to open its config panel
6. **Expected:** Config panel shows:
   - "Shape Entries" section with an "Add Shape" button
   - Empty state (no shapes configured yet)
7. Click "Add Shape" 
8. **Expected:** A shape entry card appears with:
   - Type IRI picker (autocomplete input)
   - Label input
   - Slot ID input  
   - Collapsible "Edge Linking" section
9. Type a known type name (e.g., "Project") in the type IRI picker
10. **Expected:** Autocomplete suggestions appear (dropdown visible, not clipped by GridStack)
11. Select a type, enter label "My Project", slot ID "proj1"
12. Click "Add Shape" again, configure a second shape (e.g., "Task", label "My Task", slot "task1")
13. Expand "Edge Linking" on the Task shape → set target slot to "proj1" and predicate to a relation IRI
14. Save the dashboard
15. **Expected:** Save succeeds. Re-open the dashboard in builder → form-group block still has both shapes configured with correct values

---

## Test 5: Form-Group Block Rendering on Dashboard Page

**Purpose:** Verify the form-group block renders SHACL-driven sub-forms.

1. Open the dashboard page (view mode, not builder) containing the form-group block from Test 4
2. **Expected:** The form-group block renders with:
   - A collapsible `<details>` section per configured shape
   - Each section has a heading (the label configured in builder)
   - SHACL form fields rendered via `_field.html` macro (text inputs, dropdowns, etc.)
   - An edge badge showing the linking relationship (if configured)
   - A submit button at the bottom
3. Expand/collapse sections by clicking headers
4. **Expected:** Smooth collapse/expand, all form fields remain intact

---

## Test 6: Form-Group Submission — Atomic Multi-Object Creation

**Purpose:** Verify submitting a form-group creates linked objects atomically.

1. On the dashboard page with the form-group block from Test 5
2. Fill in all required fields for both sub-forms (e.g., title for Project, title for Task)
3. Click the submit button
4. **Expected:** 
   - Status area shows "Submitting…" then "Created 2 object(s) successfully" (or similar)
   - Form fields are cleared after success
5. Navigate to Object Browser
6. **Expected:** Both new objects appear with the values entered
7. Open the Task object → check Relations
8. **Expected:** Edge to the Project object exists (per the edge config)

---

## Test 7: Form-Group Error Handling — Partial Shape Failure

**Purpose:** Verify graceful degradation when one SHACL shape can't be loaded.

1. In the builder, configure a form-group with one valid type IRI and one invalid/nonexistent type IRI
2. Save and open the dashboard page
3. **Expected:**
   - The valid sub-form renders correctly with SHACL fields
   - The invalid sub-form shows an error message in its section (not a full block crash)
   - The block is still usable (can fill and submit the valid sub-form)

---

## Test 8: Form-Group CSS and Visual Quality

**Purpose:** Verify form-group styling is correct in both builder and viewer.

1. View a form-group block on the dashboard page
2. **Expected:**
   - Block has a scrollable container (overflow visible when content exceeds block height)
   - Sub-form sections have left border accent (visual grouping)
   - Edge badges render as pills
   - Submit button row is clearly visible
   - Lucide icons (if any) are properly sized (not collapsed in flex containers)
3. Open the dashboard builder
4. **Expected:**
   - Shape entry cards have visible borders and remove buttons
   - Autocomplete dropdown in type picker is not clipped by GridStack (z-index 1000)

---

## Test 9: Block Registry Validation

**Purpose:** Verify form-group appears correctly in the block type registry.

1. Navigate to `/api/blocks/types` (or equivalent JSON endpoint)
2. **Expected:** Response includes `form-group` entry with:
   - `icon: "layers"`
   - `category: "data"`
   - `min_width` and `min_height` values present
   - Config schema accepting `shapes` as a list

---

## Edge Cases

- **Empty shapes config:** Add a form-group block with no shapes configured → dashboard page should show an error div (not crash)
- **Duplicate slot IDs:** Configure two shapes with the same slot ID → first object.create claims the slot, behavior is defined
- **Large form:** Configure 5+ shapes in one form-group → verify scrolling works within the GridStack widget
- **Save round-trip:** Save a dashboard with a form-group block, close builder, reopen builder → all nested shape config preserved exactly
