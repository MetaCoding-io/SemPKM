# S03: Type Badge, Tabs & Navigation Chrome

**Goal:** Type badge shows Lucide icon with type color accent. Active tab is clearly distinguishable from inactive. View explorer uses Lucide icons with per-renderer colors. Body editor feels like a writing surface with CSS-token-driven theming.
**Demo:** After this: Type badge shows Lucide icon with type color accent. Active tab is clearly distinguishable from inactive. View explorer uses Lucide icons with per-renderer colors. Body editor feels like a writing surface.

## Tasks
- [x] **T01: Added Lucide icons to type badge and view explorer, enhanced active tab contrast with bold text + thicker accent bar + shadow** — Three independent CSS/template surfaces that improve navigation chrome:

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
  - Estimate: 45m
  - Files: backend/app/templates/browser/object_tab.html, backend/app/templates/browser/object_tab_app.html, backend/app/templates/browser/views_explorer.html, frontend/static/css/workspace.css, frontend/static/css/dockview-sempkm-bridge.css
  - Verify: grep -q 'data-lucide' backend/app/templates/browser/object_tab.html && grep -q 'data-lucide' backend/app/templates/browser/views_explorer.html && grep -q 'font-weight.*600' frontend/static/css/dockview-sempkm-bridge.css && grep -c '&#[0-9]*;' backend/app/templates/browser/views_explorer.html | grep -q '^0$' && echo 'PASS'
- [x] **T02: Collapsed dual CM6 themes into single CSS-var-driven definition and added writing surface polish** — Replace hardcoded hex colors in the CM6 editor themes with CSS `var()` tokens, collapse dual light/dark theme into a single definition, and add writing-surface polish.

## 1. Collapse CM6 Themes to Single Definition

Currently `editor.js` defines two separate themes (`darkEditorTheme` at line 18, `lightEditorTheme` at line 26) with hardcoded hex values. Since CM6's `EditorView.theme()` accepts CSS including `var()` references, a single theme using CSS tokens auto-adapts when `data-theme` changes on `<html>`.

**Replace both theme definitions with a single unified theme:**
```javascript
var editorTheme = EditorView.theme({
  '&': { backgroundColor: 'var(--color-surface)', color: 'var(--color-text)' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--color-accent)' },
  '.cm-gutters': {
    backgroundColor: 'var(--color-surface-raised)',
    color: 'var(--color-text-faint)',
    borderRight: '1px solid var(--color-border)'
  },
  '.cm-activeLineGutter': { backgroundColor: 'var(--color-surface-recessed)' },
  '.cm-activeLine': { backgroundColor: 'var(--color-surface-recessed)' },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': {
    backgroundColor: 'var(--color-surface-hover)'
  }
});
```

**Remove `themeCompartment` machinery:**
- Delete the `Compartment` import from the CM_Markdown destructure (line 13)
- Delete `themeCompartment` variable (line 16)
- Delete `darkEditorTheme` and `lightEditorTheme` definitions (lines 18-31)
- Delete `getCurrentTheme()` function (lines 35-38)
- Replace `themeCompartment.of(getCurrentTheme())` in `initEditor()` (line 74) with just `editorTheme`
- Delete `switchEditorThemes()` function (lines 238-250) — CSS vars auto-adapt, no reconfigure needed
- Set `window.SemPKM.switchEditorThemes` to a no-op function or remove it entirely

**Check callers of `switchEditorThemes`:** Search for all references. If `theme.js` or another file calls `switchEditorThemes(isDark)` on theme toggle, that call becomes a no-op (CSS vars handle it). Either remove the call or leave the no-op stub.

## 2. Writing Surface CSS Polish

In `workspace.css`, enhance `.codemirror-container` and CM6 elements:

- Change `.codemirror-container` border from `1px solid var(--color-border)` to `1px solid var(--color-border-subtle)` for a softer look
- Add `.codemirror-container .cm-content { padding-left: 8px; }` for breathing room
- Add `.codemirror-container .cm-editor { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; }` for proportional prose font

## Constraints
- After changes, `grep -rn '#[0-9a-fA-F]\{3,8\}' frontend/static/js/editor.js` must return 0 results
- K014: No standalone hex values — all colors via CSS var() tokens
- The `Compartment` import may still be needed if other code uses compartments — check before removing
- The `{ dark: true }` option on the old theme affected CM6's base styles. The unified theme should omit this since both modes use the same CSS rule — CM6 will use its default base which works with CSS variables
  - Estimate: 30m
  - Files: frontend/static/js/editor.js, frontend/static/css/workspace.css
  - Verify: grep -rn '#[0-9a-fA-F]\{3,8\}' frontend/static/js/editor.js | grep -v '// ' | wc -l | grep -q '^0$' && grep -q 'color-surface' frontend/static/js/editor.js && grep -q 'border-subtle\|border-faint' frontend/static/css/workspace.css && echo 'PASS'
