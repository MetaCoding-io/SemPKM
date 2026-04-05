# S03: Object Delete UI — UAT

**Milestone:** M048
**Written:** 2026-04-05T18:44:34.037Z

## UAT: Object Delete UI

### Preconditions
- SemPKM running with at least one Mental Model installed
- At least 3 objects exist (to test delete without emptying the store)
- User is logged in with owner role

---

### Test 1: Delete from Object Toolbar

1. Open an object by clicking it in the explorer tree
2. Verify the object tab opens with a trash icon (trash-2) in the toolbar, between the star button and properties toggle
3. Click the trash icon
4. **Expected:** A confirmation dialog appears with text: 'Delete "[object label]"? This cannot be undone.'
5. Click the confirm button
6. **Expected:** The object tab closes, the explorer tree refreshes (object no longer listed), and a toast says "Object deleted"
7. Open Table View from explorer → verify the deleted object is not in the table
8. Run SPARQL: `SELECT * WHERE { <deleted_iri> ?p ?o }` → **Expected:** zero results
9. Run SPARQL: `SELECT * WHERE { ?s ?p <deleted_iri> }` → **Expected:** zero results (inbound edges cleaned up)

### Test 2: Delete from Command Palette

1. Open an object tab (click any object in explorer)
2. Press Ctrl+K to open the command palette
3. Type "Delete" to filter commands
4. **Expected:** "Delete Object" appears in the Objects section
5. Select "Delete Object"
6. **Expected:** Confirmation dialog appears with the active object's label
7. Confirm the delete
8. **Expected:** Tab closes, explorer refreshes, toast shown

### Test 3: Command Palette — No Object Selected

1. Open a view tab (e.g., Table View) so no object tab is active
2. Press Ctrl+K → type "Delete" → select "Delete Object"
3. **Expected:** Toast says "No object selected" — no confirmation dialog appears

### Test 4: Delete from Explorer Tree Hover

1. Hover over an object in the explorer tree
2. **Expected:** A small trash icon appears on the right side of the tree item row
3. Click the trash icon
4. **Expected:** Confirmation dialog with the object's label
5. Confirm the delete
6. **Expected:** Object disappears from explorer tree, toast shown
7. If the deleted object had a tab open, verify the tab is closed

### Test 5: Cancel Delete — Confirmation Dialog Dismiss

1. Open an object tab
2. Click the toolbar trash icon
3. **Expected:** Confirmation dialog appears
4. Click "Cancel" or press Escape
5. **Expected:** Dialog closes, object is NOT deleted, tab remains open, explorer unchanged

### Test 6: Inbound Edge Cleanup

1. Create Object A and Object B
2. Add a relationship from Object B pointing to Object A (e.g., an edge where A is the target)
3. Delete Object A via any surface
4. Run SPARQL: `SELECT * WHERE { ?s ?p <object_a_iri> }` → **Expected:** zero results (inbound edge from B→A removed)
5. Open Object B → verify no broken references in its properties/relations

### Test 7: Delete Button Styling

1. Open an object tab
2. Verify the delete (trash) icon is muted grey by default
3. Hover over the delete icon
4. **Expected:** Icon turns red (var(--color-error))
5. Verify the icon doesn't shrink or disappear in the flex toolbar layout
