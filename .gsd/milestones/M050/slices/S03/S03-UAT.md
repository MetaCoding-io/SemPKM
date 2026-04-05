# S03: Save/Restore Flow + E2E Tests — UAT

**Milestone:** M050
**Written:** 2026-04-05T22:33:00.084Z

## UAT: Save/Restore Flow + E2E Tests

### Preconditions
- SemPKM running with at least one Mental Model installed (basic-pkm)
- Logged in as owner
- At least one type with instances exists (e.g., Tasks)

### Test 1: Save a view with type filter

1. Open the workspace
2. Open a Table view (via explorer sidebar VIEWS section or command palette)
3. In the view toolbar, select a type from the type filter dropdown (e.g., "Task")
4. Verify the table updates to show only objects of that type
5. Click the Save View button (bookmark icon in toolbar)
6. Enter a name in the prompt dialog (e.g., "My Task Table")
7. Click OK
8. **Expected:** Toast confirms view saved. The SAVED VIEWS section in the explorer sidebar shows "My Task Table"

### Test 2: Restore a saved view with type filter preserved

1. Close the current view tab
2. In the explorer sidebar, expand the SAVED VIEWS section
3. Wait for the saved views list to load (htmx lazy-load)
4. Click "My Task Table" in the saved views list
5. **Expected:** A new Table view tab opens with the type filter dropdown pre-selected to "Task" — the same type that was active when the view was saved

### Test 3: Restore from sidebar passes type_filter to openGenericViewTab

1. Inspect the saved view entry in the sidebar HTML
2. **Expected:** The onclick handler includes the type_filter value as the 4th argument to openGenericViewTab

### Test 4: Delete a saved view

1. In the SAVED VIEWS section, hover over "My Task Table"
2. Click the unpin/delete button
3. Confirm the deletion in the dialog
4. **Expected:** "My Task Table" is removed from the sidebar. The view tab (if open) remains but is now unsaved.

### Test 5: Backward compatibility — opening views without type filter

1. Open a Table view via the explorer sidebar (not from Saved Views)
2. **Expected:** The type filter dropdown shows the last-used type from localStorage (or empty if none). No errors in console. The 4th selectedType parameter is optional and defaults to localStorage fallback.

### Edge Cases

- **Empty type filter:** Save a view without selecting a type → restore → type dropdown should be empty/default
- **Scope query + type filter:** Save a view with both a scope query and type filter → restore → both should be preserved
- **Multiple saved views:** Save several views with different type filters → each restores its own type independently
