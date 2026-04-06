# S02: Multi-Model Filter + Visual Polish + Persistence — UAT

**Milestone:** M056
**Written:** 2026-04-06T07:45:19.212Z

# S02 UAT: Multi-Model Filter + Visual Polish + Persistence

## Preconditions
- At least 2 Mental Models installed (e.g., basic-pkm + crm, or basic-pkm + business-planning)
- Ontology Viewer accessible at `/browser/ontology`
- TBox tab showing Cytoscape.js graph (not tree view)

---

## Test 1: Filter Checkboxes Render Per Model

1. Open Ontology Viewer → TBox tab
2. Verify filter checkboxes appear in the toolbar area
3. Verify an 'All' checkbox is present
4. Verify each installed model appears as a labeled checkbox with a color dot
5. Verify 'gist' appears first if gist classes are in the graph
6. Verify color dots match the node colors in the graph

**Expected:** One checkbox per distinct source in the graph data, color dots matching `_colorForSource()` palette, 'All' checkbox present.

---

## Test 2: Unchecking a Source Hides Nodes and Edges

1. With all checkboxes checked, note the total visible nodes
2. Uncheck one model source (e.g., 'crm')
3. Verify all nodes from that source disappear from the graph
4. Verify edges connected to hidden nodes also disappear
5. Re-check the source → nodes and edges reappear

**Expected:** Graph updates live without page reload. Edges touching hidden nodes are hidden. Re-checking restores full visibility.

---

## Test 3: 'All' Checkbox Toggles All Sources

1. Uncheck 'All' → all individual checkboxes uncheck, graph shows no nodes
2. Check 'All' → all individual checkboxes check, all nodes visible
3. Manually uncheck one source → 'All' checkbox unchecks automatically
4. Manually re-check all sources one by one → 'All' checkbox checks automatically

**Expected:** 'All' is a convenience toggle that stays in sync with individual checkbox state.

---

## Test 4: Tab Switch Preserves Graph State

1. Zoom into a specific area of the TBox graph and pan to an offset position
2. Switch to the ABox tab
3. Switch back to the TBox tab
4. Verify the graph is in the same zoom level and pan position as before

**Expected:** Graph position preserved. No reset to default zoom/pan on tab switch. cy.resize() fires to fix container measurement without cy.fit().

---

## Test 5: Hover Popover Appears Correctly

1. Hover over any node in the TBox graph
2. After ~250ms delay, verify a popover appears near the node
3. Verify the popover shows: class label, source badge (colored), and full IRI
4. Move mouse away from the node → popover disappears after ~100ms
5. Hover a node, then move mouse INTO the popover → verify popover stays visible
6. Move mouse out of the popover → popover disappears

**Expected:** Popover anchored adjacent to the hovered node (not displaced to a corner). Source badge color matches the node's source color. Hover-into-popover keeps it open.

---

## Test 6: Popover Viewport Clamping

1. Pan the graph so a node is near the right edge of the viewport
2. Hover that node → verify popover appears but does not extend off-screen to the right
3. Pan a node near the bottom edge → hover → verify popover clamps to stay within viewport

**Expected:** Popover repositions to stay fully visible within the browser window.

---

## Test 7: Filter + Popover Interaction

1. Filter to show only one model source
2. Hover a visible node → popover appears with correct source badge
3. Verify popover source badge matches the filtered model name

**Expected:** Popover works correctly on filtered graph subset.

---

## Edge Cases

- **Single model installed:** Only one checkbox (plus 'All') appears. Unchecking it hides all nodes.
- **Rapid tab switching:** Switch TBox → ABox → TBox rapidly. Graph should render correctly each time.
- **Theme switch during graph view:** Toggle dark/light theme. Filter dots and popover should reflect theme-appropriate colors.
