# S01: Kanban Enrichment & Column Colors

**Goal:** Kanban view shows enriched cards with priority badge, due date, and type icon. Columns have color-coded left border accents based on status keywords. Types without enrichment fields render correctly with cards showing only the title.
**Demo:** After this: Kanban view shows cards with priority badge, due date, and type icon. Columns have color-coded left border accents. Types without enrichment fields still render correctly.

## Tasks
- [x] **T01: Added _detect_enrichment_fields() to kanban backend, extended SPARQL with OPTIONAL priority/date clauses, and enriched item dicts with priority and due_date keys** — ## Description

Extend the kanban backend to detect priority-like and date-like fields from SHACL shapes, include them in the SPARQL query, and pass enrichment data through to the template context.

**Current state:** `execute_kanban_query()` fetches only `?s`, `?label`, `?statusValue`. Items are `{iri, label}` dicts.

**Target state:** A new `_detect_enrichment_fields()` method scans SHACL PropertyShapes for:
- **Priority field**: first property with `sh:in` values whose path contains 'priority' (case-insensitive). Falls back to any `sh:in` property that isn't the status field.
- **Due date field**: first property with `sh:datatype` in `{xsd:date, xsd:dateTime}` or whose path local-name matches well-known date paths (`duedate`, `deadline`, `targetdate`, `enddate`). Uses existing `_detect_date_fields()` logic but only needs the start field.

`_build_kanban_select()` adds OPTIONAL clauses for detected fields. `execute_kanban_query()` populates item dicts with `priority` and `due_date` keys (both nullable). The router passes the enrichment metadata (field names) alongside column data.

## Steps

1. Add `_detect_enrichment_fields(type_iri)` method to `ViewSpecService` that returns `{priority_field: PropertyShape|None, date_field: PropertyShape|None}`. Scan the form properties from `get_form_for_type()`. For priority: find first `sh:in` property with 'priority' in path (case-insensitive), or first non-status `sh:in` property. For date: reuse the start-field detection from `_detect_date_fields()` (call it and take the first result).

2. Update `_build_kanban_select()` signature to accept optional `priority_path` and `date_path` strings. When non-None, add `OPTIONAL { ?s <priority_path> ?priorityValue }` and `OPTIONAL { ?s <date_path> ?dateValue }` to the WHERE clause.

3. Update `execute_kanban_query()` to:
   - Call `_detect_enrichment_fields()` for the type
   - Pass priority_path/date_path to `_build_kanban_select()`
   - Extract `priorityValue` and `dateValue` from bindings into each item dict
   - Include enrichment metadata in the return dict: `enrichment: {priority_field: {path, name, values}|null, date_field: {path, name}|null}`

4. Update the kanban branch in `generic_view()` in `router.py` to pass `enrichment` to the template context.

5. Add unit tests in `test_kanban.py`:
   - `test_detect_enrichment_priority_field` — type with priority sh:in property
   - `test_detect_enrichment_date_field` — type with xsd:date property
   - `test_detect_enrichment_no_fields` — type with no enrichment fields returns nulls
   - `test_build_kanban_select_with_enrichment` — SPARQL contains OPTIONAL clauses
   - `test_execute_kanban_query_enriched_items` — items include priority/due_date keys

6. Run existing tests to confirm no regressions.

## Must-Haves

- [ ] `_detect_enrichment_fields()` returns priority and date fields correctly
- [ ] `_build_kanban_select()` adds OPTIONAL SPARQL clauses when enrichment paths provided
- [ ] Items in `execute_kanban_query()` output include `priority` and `due_date` keys (nullable)
- [ ] Router passes `enrichment` metadata to template context
- [ ] All existing kanban tests pass
- [ ] New enrichment tests pass
  - Estimate: 45m
  - Files: backend/app/views/service.py, backend/app/views/router.py, backend/tests/test_kanban.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v
- [ ] **T02: Add kanban card enrichment UI and column color accents** — ## Description

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
  - Estimate: 45m
  - Files: frontend/static/css/theme.css, frontend/static/css/views.css, backend/app/templates/browser/kanban_view.html, frontend/static/js/kanban.js
  - Verify: grep -c 'kanban-card-priority' frontend/static/css/views.css && grep -c 'kanban-card-meta' backend/app/templates/browser/kanban_view.html && grep -c '_applyColumnColors' frontend/static/js/kanban.js && rg '#[0-9a-fA-F]{3,8}' frontend/static/css/views.css --glob '!theme.css' | grep -v var | grep -v comment | wc -l
