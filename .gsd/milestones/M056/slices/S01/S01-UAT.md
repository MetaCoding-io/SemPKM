# S01: TBox Graph API + Hierarchical Rendering + Detail Panel — UAT

**Milestone:** M056
**Written:** 2026-04-06T07:32:02.127Z

## UAT: S01 — TBox Graph API + Hierarchical Rendering + Detail Panel

### Preconditions
- SemPKM running with at least one Mental Model installed (e.g., basic-pkm)
- gist upper ontology loaded (always present)
- User authenticated and on workspace page

### Test 1: Graph renders on TBox tab open
1. Navigate to Admin → Ontology Viewer
2. Click the TBox tab
3. **Expected:** A Cytoscape hierarchical graph appears with gist classes at the top layer and model-specific classes below them. Nodes are labeled with class names. The graph fills the available area.

### Test 2: Source-based node coloring
1. On the TBox graph from Test 1, observe node colors
2. **Expected:** gist classes are a neutral slate color. Model-specific classes (e.g., basic-pkm types like Task, Contact) use a distinct color from a rotating palette. User-created types (if any) use teal.

### Test 3: Graph/Tree toggle
1. On the TBox tab, locate the toggle buttons (Graph / Tree) in the toolbar
2. Click "Tree"
3. **Expected:** Graph disappears, tree view appears with the existing tree hierarchy, filter bar, and expand/collapse functionality
4. Click "Graph"
5. **Expected:** Tree disappears, graph reappears. Graph layout is preserved (not re-fetched).

### Test 4: Node click → detail panel
1. On the TBox graph, click any class node (e.g., "Task")
2. **Expected:** Bottom detail panel populates with class properties, relationships, and instance count via the existing tbox/detail endpoint. The panel replaces the "Select a class to view its details" placeholder.
3. Click a different node
4. **Expected:** Detail panel updates to show the new class's information.

### Test 5: Empty state
1. Uninstall all Mental Models (leaving only gist)
2. Open Ontology Viewer → TBox tab
3. **Expected:** Graph renders showing only gist classes. If somehow no classes exist at all, a "No ontology classes found" message appears.

### Test 6: API endpoint direct access
1. `curl -b <auth-cookie> http://localhost:4000/browser/ontology/tbox/graph-data`
2. **Expected:** JSON response with `{"nodes": [...], "edges": [...]}`. Each node has `id`, `label`, `source` fields. Each edge has `source` (parent IRI), `target` (child IRI). No owl:Thing nodes present.

### Test 7: Dark mode theme switching
1. On the TBox graph, switch to dark mode (theme toggle)
2. **Expected:** Graph node and edge colors adapt to dark theme. No visual artifacts or invisible elements.
3. Switch back to light mode
4. **Expected:** Colors revert correctly.

### Test 8: Tree view functionality preserved
1. Switch to Tree view via toggle
2. Expand a class node in the tree
3. Use the "Hide gist" checkbox
4. **Expected:** Tree expand/collapse works. Hide gist filters the tree. All existing tree functionality is intact.

### Test 9: Existing modals still work
1. In the TBox tab (either view), click "Create Class" (or equivalent)
2. **Expected:** Modal overlay appears correctly, not displaced by the layout change.
3. Close the modal
4. **Expected:** Returns to the graph/tree view cleanly.

### Edge Cases
- **Large ontology:** Install 3+ models → graph should render all classes without visible performance issues
- **Network error:** If /browser/ontology/tbox/graph-data returns an error, graph container shows an error message rather than a blank area
- **Tab switch:** Navigate away from TBox tab and back → graph re-initializes correctly
