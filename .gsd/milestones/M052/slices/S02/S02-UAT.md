# S02: Property Table & Popover Polish — UAT

**Milestone:** M052
**Written:** 2026-04-06T02:11:18.976Z

# S02 UAT: Property Table & Popover Polish

## Preconditions
- Dev stack running (`docker compose up -d`)
- At least one Mental Model installed (e.g., basic-pkm) with objects that have SHACL-defined properties including `sh:description`
- Browser with DevTools available for dark-mode toggle

## Test 1: Object Read View — Zebra Striping
1. Navigate to `/browser/`
2. Open any object with 4+ properties in read mode
3. **Expected:** Even-numbered property rows have a slightly recessed background color distinct from odd rows
4. Scroll through all properties to confirm alternating pattern is consistent

## Test 2: Object Read View — Hover Highlight
1. On the same object in read mode
2. Hover the mouse over any property row
3. **Expected:** Both the label cell and value cell highlight simultaneously with a hover background color
4. Move the mouse away — highlight disappears smoothly (0.15s transition)
5. Repeat on both odd and even rows — hover should override zebra background

## Test 3: Object Read View — Label/Value Distinction
1. On the same object in read mode
2. Observe property labels (left column) vs values (right column)
3. **Expected:** Labels appear in full-strength text color (bold). Values appear in a muted/lighter text color, creating clear visual hierarchy

## Test 4: Object Read View — Description Tooltips
1. On an object whose type has SHACL `sh:description` on some properties (e.g., basic-pkm Task)
2. Hover the mouse over a property label that has a description
3. **Expected:** Native browser tooltip appears showing the `sh:description` text
4. Hover over a property label that does NOT have a description (e.g., an inferred property)
5. **Expected:** No tooltip appears

## Test 5: Graph Popover — Property Row Borders
1. Open a graph view for a type with objects that have properties
2. Hover over a node to trigger the popover
3. **Expected:** Property rows inside the popover have subtle bottom borders separating them
4. The last property row has NO bottom border

## Test 6: Graph Popover — Alternating Backgrounds
1. On the same graph popover with 3+ properties
2. **Expected:** Even-numbered rows have a slightly different background color from odd rows
3. First and last rows have subtle border-radius on their outer edges

## Test 7: Ref-Pill Tooltip — Shared Styling
1. Open an object in read mode that has reference-type properties (links to other objects)
2. Hover over a ref-pill (the linked object chip/pill)
3. **Expected:** The tooltip popover shows property rows with the same styling as graph popovers — borders, alternating backgrounds, padding

## Test 8: Dark Mode — All Surfaces
1. Toggle dark mode (via theme switcher or DevTools)
2. Repeat Tests 1-3 on the object read view
3. **Expected:** Zebra striping, hover highlight, and muted text all adapt to dark theme colors. No hardcoded colors visible (no bright patches or invisible text)
4. Open a graph view and hover a node
5. **Expected:** Popover property rows have appropriate dark-mode borders and alternating backgrounds

## Edge Cases
- **Object with 1 property:** No zebra striping visible (only 1 row), but hover highlight still works
- **Object with 0 properties:** Property table area is empty, no styling issues
- **Property with very long description:** Tooltip wraps naturally (native browser behavior)
- **Property with HTML-special characters in description:** Tooltip shows escaped text, no XSS
