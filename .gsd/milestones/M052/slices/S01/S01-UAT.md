# S01: Kanban Enrichment & Column Colors — UAT

**Milestone:** M052
**Written:** 2026-04-06T02:02:43.412Z

## UAT: Kanban Enrichment & Column Colors

### Preconditions
- SemPKM running with basic-pkm model installed (has Task type with status, priority, due date fields)
- At least 3 tasks exist with varying status values (e.g., "To Do", "In Progress", "Done")
- At least 1 task has a priority value set (e.g., "high" or "critical")
- At least 1 task has a due date set
- A second type with status but NO priority field (e.g., Event or Project) has at least 2 instances

### Test Cases

#### TC1: Priority Badge Rendering
1. Navigate to workspace → open Kanban view for Task type
2. Find a card for a task that has priority set
3. **Expected:** Card shows a small colored pill below the title with the priority label (capitalized)
4. Verify color mapping:
   - Critical priority → red-tinted pill
   - High priority → amber-tinted pill
   - Medium priority → blue-tinted pill
   - Low priority → green-tinted pill

#### TC2: Due Date Rendering
1. In the same Kanban view, find a card for a task with a due date
2. **Expected:** Card shows a muted-text line below the title with a small calendar icon and the formatted date
3. The calendar icon should be a Lucide SVG, properly sized (not collapsed to 0px)

#### TC3: Type Icon Rendering
1. In the same Kanban view, inspect any card
2. **Expected:** Card header area contains a small Lucide icon matching the type's manifest icon entry
3. If the type has no manifest icon, the icon area should be empty (no broken icon placeholder)

#### TC4: Column Color Accents
1. View the Kanban board columns
2. **Expected:** Each column has a 3px colored left border based on its status keyword:
   - "To Do" / "Backlog" / "New" → blue left border
   - "In Progress" / "Doing" / "Active" → amber left border
   - "Done" / "Complete" / "Closed" → green left border
   - "Blocked" / "Stuck" → red left border
3. If a column status doesn't match any keyword → transparent/no accent border

#### TC5: Graceful Degradation — Type Without Enrichment Fields
1. Open Kanban view for a type that has status (sh:in) but NO priority field and NO date field
2. **Expected:** Cards render with only the title — no empty priority pill, no empty date line
3. Column color accents still apply based on the status keywords

#### TC6: Dark Mode
1. Toggle dark mode in the workspace
2. View the Kanban board
3. **Expected:** All priority pill colors, date text, column accents adapt to dark mode
4. No hardcoded hex or rgba values — all colors should shift with the theme

#### TC7: Empty Board
1. Open Kanban view for a type with no instances
2. **Expected:** Empty columns render with correct color accents, no JS errors in console

### Edge Cases
- Card with priority but no due date → shows only priority pill
- Card with due date but no priority → shows only date line
- Card with neither → shows only title (same as TC5)
- Column with status value not matching any keyword → no color accent (transparent border)
