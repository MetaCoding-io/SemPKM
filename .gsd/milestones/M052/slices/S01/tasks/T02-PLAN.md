---
estimated_steps: 45
estimated_files: 4
skills_used: []
---

# T02: Add kanban card enrichment UI and column color accents

## Description

Update the kanban template, CSS, and minimal JS to render enriched cards and colored column borders.

**Card enrichment rendering:**
- Priority badge: a small colored pill below the title. Color mapping: critical→red, high→amber, medium→blue, low→green (using theme primitives via color-mix). Only rendered when `item.priority` is truthy.
- Due date: a small muted-text line with a calendar icon. Format the date for display. Only rendered when `item.due_date` is truthy.
- Type icon: a small Lucide icon in the card header area. The type_iri is available on the board element's `data-type-iri` attribute, and icon data is in `window.SemPKM._sempkmIcons`. Render via JS after htmx swap by looking up the icon name and using `lucide.createElement()`.

**Column color accents (D393):**
Apply a 3px colored left border to `.kanban-column` based on the column's `data-status` value. Use keyword matching:
- todo/new/open/backlog → blue (`--_color-blue-500`)
- progress/doing/active/in-progress → amber (`--_color-amber-500`)
- done/complete/closed → green (`--_color-green-500`)
- block/stuck → red (`--_color-red-500`)
- cancel/archive → gray (`--color-text-muted`)
- default → transparent (no accent)

This is implemented in JS because the status values are dynamic and come from the data attribute. A small function in `kanban.js` runs after `initKanban()` to set `border-left` style on each column based on keyword scan of `data-status`.

**Dark mode:** All colors use existing theme tokens via `color-mix(in srgb, var(--_color-X) N%, transparent)`. No new standalone hex/rgba values outside theme.css. Add `--_color-gray-400` primitive to theme.css for the cancel/archive column accent.

## Steps

1. Add kanban-specific CSS primitives to `theme.css`: `--_color-gray-400` in both light and dark blocks. Add `--_color-kanban-priority-critical`, `--_color-kanban-priority-high`, `--_color-kanban-priority-medium`, `--_color-kanban-priority-low` as aliases of existing primitives for semantic clarity.

2. Add CSS classes to `views.css`:
   - `.kanban-card-meta` — flex row for priority + date badges below title
   - `.kanban-card-priority` — small pill with background via color-mix, font-size 0.7rem
   - `.kanban-card-priority[data-priority='critical']` etc. — per-priority colors
   - `.kanban-card-date` — muted text with calendar icon, font-size 0.75rem
   - `.kanban-card-type-icon` — small icon area at top-right or inline with title
   - `.kanban-column` updated: `border-left: 3px solid transparent` as default

3. Update `kanban_view.html` template:
   - Add a `.kanban-card-meta` div inside each card, below the title
   - Conditionally render priority badge: `{% if item.priority %}<span class="kanban-card-priority" data-priority="{{ item.priority }}">{{ item.priority | capitalize }}</span>{% endif %}`
   - Conditionally render due date: `{% if item.due_date %}<span class="kanban-card-date"><i data-lucide="calendar" class="kanban-date-icon"></i>{{ item.due_date }}</span>{% endif %}`
   - Add a type icon placeholder `<span class="kanban-card-type-icon"></span>` that JS populates

4. Update `kanban.js`:
   - Add `_applyColumnColors(boardEl)` function that iterates `.kanban-column` elements, reads `data-status`, runs keyword matching, sets `style.borderLeftColor` using CSS variable references
   - Add `_applyTypeIcons(boardEl)` function that reads `data-type-iri` from the board, looks up icon from `window.SemPKM._sempkmIcons.tree[typeIri]`, and uses `lucide.createElement()` to render an SVG into each `.kanban-card-type-icon` element
   - Call both functions at end of `initKanban()`
   - Re-init Lucide icons on the board for the date icons: `if (typeof lucide !== 'undefined') lucide.createIcons({attrs: {class: 'kanban-date-icon'}});`

5. Verify: open kanban view with basic-pkm Task type (has status, priority, dates), confirm cards show badges. Open with a type that lacks priority (e.g., Event has status but no priority field) — confirm cards render with only the title. Toggle dark mode — confirm all colors adapt.

## Must-Haves

- [ ] Priority badge renders with correct color for each priority level
- [ ] Due date renders with calendar icon when present
- [ ] Type icon renders in cards from the manifest icon registry
- [ ] Column left borders are color-coded by status keyword matching
- [ ] Cards without enrichment data show only the title (no empty badges)
- [ ] Dark mode renders correctly — no standalone hex/rgba values added outside theme.css
- [ ] Lucide icons sized via CSS with flex-shrink: 0 (per CLAUDE.md rules)
- [ ] All color values use color-mix() with theme primitives (per Knowledge R14)

## Inputs

- ``backend/app/views/service.py` — enrichment field detection and query output from T01`
- ``backend/app/views/router.py` — enrichment context variable from T01`
- ``backend/app/templates/browser/kanban_view.html` — current kanban template`
- ``frontend/static/css/views.css` — existing kanban CSS block at line ~1102`
- ``frontend/static/css/theme.css` — existing color primitives and dark mode overrides`
- ``frontend/static/js/kanban.js` — existing drag-drop module`

## Expected Output

- ``frontend/static/css/theme.css` — new --_color-gray-400 primitive in light and dark blocks`
- ``frontend/static/css/views.css` — kanban enrichment CSS classes (priority pill, date, type icon, column border)`
- ``backend/app/templates/browser/kanban_view.html` — enriched card template with conditional priority/date/icon rendering`
- ``frontend/static/js/kanban.js` — _applyColumnColors() and _applyTypeIcons() functions`

## Verification

grep -c 'kanban-card-priority' frontend/static/css/views.css && grep -c 'kanban-card-meta' backend/app/templates/browser/kanban_view.html && grep -c '_applyColumnColors' frontend/static/js/kanban.js && rg '#[0-9a-fA-F]{3,8}' frontend/static/css/views.css --glob '!theme.css' | grep -v var | grep -v comment | wc -l
