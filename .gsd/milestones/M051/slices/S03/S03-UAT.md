# S03: Command Palette & Persona/Layout Dialog UX — UAT

**Milestone:** M051
**Written:** 2026-04-06T01:31:12.106Z

## UAT: Command Palette & Persona/Layout Dialog UX

### Preconditions
- Workspace loaded at `/browser/`
- At least one Mental Model installed (for admin graph test)
- User is logged in

### Test 1: Command Palette Opens Without Scroll Jump
1. Scroll the workspace page down so the viewport is not at top
2. Press **F1** to open the command palette
3. **Expected:** Palette opens as a centered overlay. The page behind does NOT scroll or jump. Body overflow is hidden.
4. Press **Escape** to close
5. **Expected:** Page returns to the exact scroll position it was at before opening. Body overflow is restored.

### Test 2: Persona Create via Input Dialog
1. Press **F1** to open the command palette
2. Type "persona" to filter commands
3. Select **Persona: Create New**
4. **Expected:** Command palette closes. A modal dialog appears with title "Create Persona", a text input with placeholder "Persona name", and Cancel/Create buttons.
5. Type "Test Persona" and click **Create**
6. **Expected:** Dialog closes, persona is saved. Toast confirmation appears.
7. Repeat steps 1-3, but click **Cancel** in the dialog
8. **Expected:** Dialog closes, no persona created.
9. Repeat steps 1-3, leave input empty, click **Create**
10. **Expected:** Toast error "Please enter a value" (or similar). Dialog stays open.

### Test 3: Layout Save As via Input Dialog
1. Press **F1** to open the command palette
2. Type "layout" to filter commands
3. Select **Layout: Save As**
4. **Expected:** Command palette closes. A modal dialog appears with title "Save Layout", a text input with placeholder "Layout name", and Cancel/Save buttons.
5. Type "My Layout" and press **Enter** (keyboard submit)
6. **Expected:** Dialog closes, layout saved. Toast confirmation appears.
7. Repeat steps 1-3, press **Escape** in the dialog
8. **Expected:** Dialog closes, no layout saved.

### Test 4: No Shadow DOM Confirm Entries Remain
1. Press **F1** to open the command palette
2. Type "persona" — navigate into the Persona submenu
3. **Expected:** No "Confirm" or "Type name and select to confirm" child entries appear. Only the direct "Create New" action.
4. Type "layout" — navigate into the Layout submenu
5. **Expected:** No "Confirm" or "Type name and select to confirm" child entries appear. Only the direct "Save As" action.

### Test 5: Admin Graph Popover Positioning
1. Navigate to **Admin → Models → [any installed model] → Ontology**
2. Hover over a class node in the Cytoscape diagram
3. **Expected:** Popover appears adjacent to the hovered node (offset ~16px right, ~12px above). NOT displaced far from the node.
4. Hover a node near the right edge of the viewport
5. **Expected:** Popover flips to the left side of the node (no clipping off-screen).
6. Hover a node near the bottom edge of the viewport
7. **Expected:** Popover shifts upward (no clipping below viewport).
8. Hover over an edge (relationship line) between two nodes
9. **Expected:** Edge popover appears near the edge midpoint, correctly positioned (same fix applied).

### Edge Cases
- Open command palette at very top of page (scroll = 0) → no jump
- Open command palette with a very long object list causing scrollable workspace → no jump
- Input dialog: paste a very long name (100+ chars) → dialog accepts it, persona/layout created with full name
- Input dialog: type name with special characters (quotes, ampersands) → accepted without error
