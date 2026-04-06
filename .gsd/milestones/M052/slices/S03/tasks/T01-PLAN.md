---
estimated_steps: 35
estimated_files: 5
skills_used: []
---

# T01: Type badge icon + view explorer Lucide icons + tab contrast

Three independent CSS/template surfaces that improve navigation chrome:

## 1. Type Badge with Icon + Color Accent

The object toolbar type badge (`object_tab.html:12` and `object_tab_app.html:12-13`) currently renders plain text. The `type_icon` dict (with `icon` and `color` keys) is already in the template context but unused.

**Template changes:**
- In both `object_tab.html` and `object_tab_app.html`: add `style="--type-color: {{ type_icon.color if type_icon else '' }}"` to the `.object-toolbar-type` span
- Add `{% if type_icon %}<i data-lucide="{{ type_icon.icon }}"></i>{% endif %}` inside the span, before the label text

**CSS changes in `workspace.css` (line ~2318):**
- Add `display: inline-flex; align-items: center; gap: 4px;` to `.object-toolbar-type`
- Add `border-left: 3px solid var(--type-color, var(--color-border))` to `.object-toolbar-type`
- Add `.object-toolbar-type svg { width: 12px; height: 12px; flex-shrink: 0; stroke: currentColor; }` per CLAUDE.md Lucide rules

Lucide `createIcons()` already runs after htmx swaps (`workspace-layout.js:91-92`), so newly inserted `data-lucide` icons will be processed automatically.

## 2. View Explorer Icons (Unicode → Lucide)

Replace 9 Unicode glyphs in `views_explorer.html` with Lucide `<i data-lucide="...">` elements. Each icon gets a per-renderer inline color using `color-mix()` referencing theme.css primitives (K014 compliance).

**Icon mapping:**
- Spatial Canvas: `layout-grid` (blue-500)
- Ontology Viewer: `gem` (violet-500)
- Table View: `table-2` (emerald-500)
- Cards View: `grid-2x2` (amber-500)
- Graph View: `network` (blue-500)
- Kanban View: `columns-3` (orange-600)
- Calendar View: `calendar` (red-500)
- Timeline View: `gantt-chart` (green-500)
- Map View: `map-pin` (amber-400)

**CSS in `workspace.css`:** Add `.tree-leaf-icon svg` sizing rule: `width: 14px; height: 14px; flex-shrink: 0; stroke: currentColor;` — this already exists at line 7453 for `#section-my-views .tree-leaf-icon svg`, but needs a broader rule for the views explorer section.

Since `views_explorer.html` is a static partial loaded on page init, `lucide.createIcons()` runs on page load via `theme.js:103-104` and will process these icons automatically.

## 3. Tab Active/Inactive Contrast

Enhance the visual difference between active and inactive dockview tabs in `dockview-sempkm-bridge.css`:

- **Bold active tab text:** Add `font-weight: 600;` to `.dv-active-group .dv-tab.dv-active-tab`
- **Thicker accent bar:** Change `border-bottom: 2px solid` → `3px solid` on the active tab rule (line 37)
- **Subtle active tab lift:** Add `box-shadow: 0 -1px 3px color-mix(in srgb, var(--_color-black-shadow-sm) 50%, transparent)` to the active tab

**Important:** Do NOT change `--dv-activegroup-hiddenpanel-tab-color` from `--color-text-muted` to `--color-text-faint` — the research suggested this but the existing muted color already provides sufficient contrast against the bold active tab.

## Constraints
- K014: All decorative colors via `color-mix()` with theme primitives — no standalone hex/rgba
- CLAUDE.md: Lucide SVGs in flex containers need `flex-shrink: 0`, CSS sizing, `stroke: currentColor`
- Both object_tab.html AND object_tab_app.html need the type badge update

## Inputs

- ``backend/app/templates/browser/object_tab.html` — current type badge markup (line 12-13)`
- ``backend/app/templates/browser/object_tab_app.html` — app variant type badge (line 12-13)`
- ``backend/app/templates/browser/views_explorer.html` — 9 Unicode glyph view entries`
- ``frontend/static/css/workspace.css` — `.object-toolbar-type` (line 2318), `.tree-leaf-icon` (line 310)`
- ``frontend/static/css/dockview-sempkm-bridge.css` — active tab border rule (line 36-37)`
- ``frontend/static/css/theme.css` — color primitives (`--_color-blue-500`, `--_color-violet-500`, etc.)`

## Expected Output

- ``backend/app/templates/browser/object_tab.html` — type badge with Lucide icon + `--type-color` CSS variable`
- ``backend/app/templates/browser/object_tab_app.html` — same type badge enhancement`
- ``backend/app/templates/browser/views_explorer.html` — 9 Lucide icons replacing Unicode glyphs with per-renderer colors`
- ``frontend/static/css/workspace.css` — enhanced `.object-toolbar-type` with flex layout + icon sizing, `.tree-leaf-icon svg` sizing rule`
- ``frontend/static/css/dockview-sempkm-bridge.css` — bold active tab, thicker accent bar, subtle shadow`

## Verification

grep -q 'data-lucide' backend/app/templates/browser/object_tab.html && grep -q 'data-lucide' backend/app/templates/browser/views_explorer.html && grep -q 'font-weight.*600' frontend/static/css/dockview-sempkm-bridge.css && grep -c '&#[0-9]*;' backend/app/templates/browser/views_explorer.html | grep -q '^0$' && echo 'PASS'
