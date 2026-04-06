# S04: Forms, Timeline & Final Polish — UAT

**Milestone:** M052
**Written:** 2026-04-06T02:43:34.753Z

## Preconditions

- SemPKM workspace loaded at `/browser/`
- At least one Mental Model installed (basic-pkm recommended)
- At least one object of a type with status field exists (e.g., Task)

## Test Cases

### TC1: Form Section Headers Have Accent Bar

1. Open any object in edit mode (click Edit button or create new object)
2. Observe form section headers (e.g., "CORE PROPERTIES", "RELATIONSHIPS", "METADATA")
3. **Expected:** Each section header has a 3px colored left border (primary accent), raised background, and rounded corners
4. **Expected:** Headers are visually distinct from the form fields below them

### TC2: Help Text Spacing Is Tight

1. In edit mode, locate a field with help text below it (e.g., description fields often have helper text)
2. **Expected:** Help text sits close to its field — no excessive gap between field and help text
3. **Expected:** Help text lines are compact (not double-spaced)

### TC3: Timeline Bar Status Colors

1. Open a Timeline view for a type with status field (e.g., Tasks)
2. Create or ensure tasks exist with all four statuses: done, active, blocked, cancelled
3. **Expected:** Done tasks show green bars
4. **Expected:** Active tasks show primary-color (blue) bars
5. **Expected:** Blocked tasks show red bars
6. **Expected:** Cancelled tasks show gray bars

### TC4: Right Panel Empty State

1. Navigate to `/browser/` with no object tab open
2. Look at the right panel area (read view, edit view, metadata sections)
3. **Expected:** Each empty section shows "Select an object to see its details" with a small info icon
4. **Expected:** The info icon renders as a Lucide SVG, not as raw `<i>` text
5. **Expected:** Icon and text are horizontally aligned

### TC5: Explorer Tree Links Have No Underline

1. In the left sidebar explorer, expand any section (OBJECTS, VIEWS, etc.)
2. Hover over tree leaf items
3. **Expected:** No underline decoration appears on any tree leaf link in normal or hover state

### TC6: Dark Mode Compatibility

1. Switch to dark mode (if theme toggle available)
2. Repeat TC1 — form section headers should use dark-mode surface and primary colors
3. Repeat TC3 — timeline bars should use theme-appropriate status colors
4. Repeat TC4 — empty state text and icon should be visible against dark background

### Edge Cases

- **Type without status field:** Timeline view should still render; bars use default Frappe Gantt color
- **Empty right panel after closing all tabs:** Empty state message should persist across tab close events
- **Form with no help text:** Section headers still have accent bar even when all fields lack help text
