# S03: Type Badge, Tabs & Navigation Chrome — UAT

**Milestone:** M052
**Written:** 2026-04-06T02:24:05.012Z

## UAT: S03 — Type Badge, Tabs & Navigation Chrome

### Preconditions
- SemPKM running with at least one Mental Model installed (e.g., basic-pkm)
- At least one object of a type that has a type_icon defined (e.g., Task, Project)
- Browser with DevTools available

---

### Test 1: Type Badge Displays Lucide Icon with Color Accent

**Steps:**
1. Navigate to workspace (`/browser/`)
2. Open an object that has a type icon defined (e.g., a Task or Project)
3. Observe the type badge in the object toolbar (top-left area of the object tab)

**Expected:**
- Type badge shows a Lucide SVG icon before the type label text
- Badge has a colored left border matching the type's defined color
- Icon is properly sized (~12px) and aligned with the text
- No Unicode characters or broken icon placeholders

**Edge case:** Open an object of a type without a defined icon — the badge should show the label text only, with a default border color.

---

### Test 2: View Explorer Shows Lucide Icons with Per-Renderer Colors

**Steps:**
1. In the workspace sidebar, expand the VIEWS section
2. Observe the list of available view renderers

**Expected:**
- Each renderer row shows a distinct Lucide icon:
  - Spatial Canvas → layout-grid icon (blue)
  - Ontology Viewer → gem icon (violet)
  - Table View → table-2 icon (green/emerald)
  - Cards View → grid-2x2 icon (amber)
  - Graph View → network icon (blue)
  - Kanban View → columns-3 icon (orange)
  - Calendar View → calendar icon (red)
  - Timeline View → gantt-chart icon (green)
  - Map View → map-pin icon (amber)
- No Unicode characters (🔲, 📊, etc.) visible — all replaced by SVG icons
- Icons have distinct colors per renderer

**Edge case:** Switch to dark mode — icon colors should remain visible and distinct (color-mix with theme primitives adapts automatically).

---

### Test 3: Active Tab Is Clearly Distinguishable

**Steps:**
1. Open two or more tabs in the workspace (e.g., two different objects, or an object + a view)
2. Click between tabs to switch active state

**Expected:**
- Active tab has bold text (font-weight 600)
- Active tab has a thicker bottom accent bar (3px, visibly thicker than inactive)
- Active tab has a subtle upward shadow distinguishing it from inactive tabs
- Inactive tabs have normal weight text and no shadow
- Switching tabs immediately updates the visual distinction

---

### Test 4: Body Editor Writing Surface Polish

**Steps:**
1. Open an object that has a body/notes field (e.g., a Task with notes)
2. Click to edit the body content (enter edit mode if needed)
3. Observe the CodeMirror editor area

**Expected:**
- Editor has a soft border (subtle, not harsh)
- Text content has visible left padding (breathing room from the border)
- Text renders in a proportional system font (not monospace), making prose feel natural
- Cursor and selection highlights use theme colors, not hardcoded values

**Edge case:** Toggle dark mode while the editor is open — the editor should adapt colors immediately without page refresh or flickering (CSS vars handle the transition, no JS reconfigure).

---

### Test 5: Dark Mode Adaptation

**Steps:**
1. With the workspace open showing an object tab and the view explorer expanded
2. Toggle dark mode via the theme switcher

**Expected:**
- Type badge icon and border color adapt to dark mode
- View explorer icon colors remain distinct and visible
- Active tab styling (bold, accent bar, shadow) adapts cleanly
- Body editor background, text, cursor, gutter all adapt via CSS vars
- No flicker or momentary unstyled state during transition
