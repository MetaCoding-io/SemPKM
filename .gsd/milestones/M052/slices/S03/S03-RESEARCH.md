# S03 Research: Type Badge, Tabs & Navigation Chrome

## Summary

Four CSS + template surfaces to polish. All straightforward — established patterns, known files, no backend logic changes. The type badge needs a Lucide icon + color accent using context already passed to the template. Tabs need contrast enhancement via dockview bridge CSS. View explorer icons switch from Unicode glyphs to Lucide with per-renderer colors. Body editor replaces hardcoded hex in CM6 theme with CSS tokens.

## Recommendation

Light-complexity slice. Four independent surface changes that can be done in 2–3 tasks: (1) type badge + view explorer icons (template + CSS), (2) tab active/inactive contrast (CSS-only), (3) body editor writing surface (JS theme + CSS). All use existing patterns — no new libraries, no backend changes.

## Implementation Landscape

### 1. Type Badge with Icon + Color Accent

**Current state:** `object_tab.html:12` renders `<span class="object-toolbar-type">{{ object_type_label }}</span>` — plain gray pill, no icon, no type color.

**Available data:** `type_icon` dict with `icon` (Lucide name), `color` (hex), `size` is already passed in template context (`objects.py:461`) but unused in the template.

**Template change needed:**
```html
<span class="object-toolbar-type" title="{{ object_iri }}" data-iri="{{ object_iri }}"
      style="--type-color: {{ type_icon.color if type_icon else '' }}">
  {% if type_icon %}<i data-lucide="{{ type_icon.icon }}"></i>{% endif %}
  {{ object_type_label }}
</span>
```

**CSS changes** in `workspace.css` (line ~2318):
- Add `border-left: 3px solid var(--type-color, var(--color-border))` to `.object-toolbar-type`
- Add `.object-toolbar-type svg { width: 12px; height: 12px; flex-shrink: 0; stroke: currentColor; }` (per CLAUDE.md Lucide rules)
- Add `display: inline-flex; align-items: center; gap: 4px;` to make icon + text sit inline

**Post-insertion:** `lucide.createIcons()` must be called after htmx swaps the object tab. Check if existing htmx `afterSwap` handler in workspace-layout.js already calls it — yes, line 91-92 calls `lucide.createIcons({ root: iconWrap })` for panel content.

**Also applies to:** `object_tab_app.html:13` — same badge markup.

### 2. View Explorer Icons (Unicode → Lucide)

**Current state:** `views_explorer.html` uses 9 Unicode glyphs (`&#9635;`, `&#9670;`, `&#9638;`, etc.) inside `<span class="tree-leaf-icon">`. All styled as `--color-text-muted`.

**Change:** Replace each `<span class="tree-leaf-icon">&#XXXX;</span>` with `<span class="tree-leaf-icon"><i data-lucide="icon-name"></i></span>`.

**Icon mapping (Lucide names):**
| View | Current | Lucide Icon |
|------|---------|-------------|
| Spatial Canvas | &#9635; | `layout-grid` |
| Ontology Viewer | &#9670; | `diamond` |
| Table View | &#9638; | `table-2` |
| Cards View | &#9641; | `layout-grid` or `grid-2x2` |
| Graph View | &#9672; | `git-branch` or `network` |
| Kanban View | &#9707; | `columns-3` |
| Calendar View | &#128197; | `calendar` |
| Timeline View | &#128202; | `gantt-chart` |
| Map View | &#127758; | `map-pin` |

**CSS:** Add per-view color classes or inline color. Example approach: add a `style="color: var(--_color-*)"` inline or use a data attribute + CSS.

Simpler: use inline `style="color: ..."` per icon with theme primitive references, or define `.view-icon-table`, `.view-icon-graph`, etc. classes. The inline style approach is simpler since these are 9 static entries.

**Note:** `views_explorer.html` is a static partial — `lucide.createIcons()` runs on page load via `theme.js:103-104`, which handles all `data-lucide` elements in the DOM.

**CSS for icon sizing:** Add to workspace.css:
```css
.tree-leaf-icon svg {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    stroke: currentColor;
}
```

### 3. Tab Active/Inactive Contrast

**Current state:** Dockview tab styling in `dockview-sempkm-bridge.css`:
- Active tab: `border-bottom: 2px solid var(--tab-accent-color, var(--color-accent))` (line 36-37)
- Active tab text: `--dv-activegroup-visiblepanel-tab-color: var(--color-text)` (line 13)
- Inactive tab text: `--dv-activegroup-hiddenpanel-tab-color: var(--color-text-muted)` (line 14)
- Active bg: `--tab-active-bg: var(--color-surface)` (theme.css:187)
- Inactive bg: `--tab-inactive-bg: var(--color-surface-raised)` (theme.css:186)

**Gap:** The visual difference between active and inactive is subtle — same font-weight, similar background, only a 2px bottom border and slightly muted text color.

**Changes in `dockview-sempkm-bridge.css`:**
- Add font-weight rule: `.dv-active-group .dv-tab.dv-active-tab { font-weight: 600; }`
- Thicken accent bar: change `2px` → `3px` in the border-bottom rule (line 37)
- Deepen inactive tab text: change `--dv-activegroup-hiddenpanel-tab-color` from `var(--color-text-muted)` to `var(--color-text-faint)` for more contrast with active
- Add subtle box-shadow on active tab: `box-shadow: 0 -1px 3px rgba(0,0,0,0.05)` (use color-mix for dark mode compat)

### 4. Body Editor Writing Surface

**Current state:** `editor.js` lines 18-31 define dark and light CM6 themes with hardcoded hex values. The `codemirror-container` CSS (workspace.css:2550) is minimal — just flex sizing and border.

**Hex values to replace with tokens:**
| Hex | Token equivalent |
|-----|-----------------|
| `#282c34` | `var(--color-surface)` (dark) |
| `#abb2bf` | `var(--color-text)` (dark) |
| `#56b6c2` | `var(--color-accent)` (dark) |
| `#21252b` | `var(--color-surface-recessed)` (dark) |
| `#5c6370` | `var(--color-text-faint)` (dark) |
| `#3e4452` | `var(--color-border)` (dark) |
| `#2c313a` | `var(--color-surface-raised)` (dark) |
| `#ffffff` | `var(--color-surface)` (light) |
| `#1a1a2e` | `var(--color-text)` (light) |
| `#f8f9fb` | `var(--color-surface-raised)` (light) |
| `#666` | `var(--color-text-muted)` (light) |
| `#e0e0e0` | `var(--color-border)` (light) |

**Writing-surface improvements:**
- Soften gutter: use `--color-text-faint` for gutter text, `--color-surface-raised` for gutter bg (already matches tokens)
- Add left padding to `.cm-content` for breathing room: `padding-left: 8px`
- Soften border on `.codemirror-container`: change `1px solid var(--color-border)` to `1px solid var(--color-border-subtle)`
- Font: Add a writing-friendly font stack to `.cm-content`: `font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif` — keeps monospace for code blocks but uses proportional for body prose. CM6 supports CSS font overrides.

**Key constraint:** CM6 `EditorView.theme()` accepts CSS strings, including `var(--token)` references. The theme objects become CSS rules injected into the document. Using CSS variables means a single theme definition works for both light and dark — no need for the light/dark compartment switching.

**Simplification opportunity:** With CSS variable references, the dark/light distinction can be collapsed into a single theme definition. The `themeCompartment` + `getCurrentTheme()` + `onThemeChange()` machinery becomes unnecessary because the CSS variables auto-adapt when `data-theme` changes.

## Files Modified

| File | Change |
|------|--------|
| `frontend/static/css/workspace.css` | Type badge styling (`.object-toolbar-type` enhancements), view-leaf icon sizing |
| `frontend/static/css/dockview-sempkm-bridge.css` | Tab active/inactive contrast improvements |
| `backend/app/templates/browser/object_tab.html` | Add Lucide icon + color to type badge |
| `backend/app/templates/browser/object_tab_app.html` | Same type badge change |
| `backend/app/templates/browser/views_explorer.html` | Replace Unicode glyphs with Lucide icons + per-view colors |
| `frontend/static/js/editor.js` | Replace hardcoded hex with CSS var() tokens, potentially collapse to single theme |

## Constraints

- **K014:** All new decorative colors via `color-mix()` referencing `theme.css` primitives. No standalone hex/rgba.
- **CLAUDE.md Lucide rules:** Icons in flex containers need `flex-shrink: 0`, CSS-based sizing (not inline `style="width:..."`), `stroke: currentColor` for color inheritance.
- **Dark mode:** Using CSS variable tokens means dark mode works automatically via `theme.css` override block. No new dark-mode-specific CSS needed.
- **Views explorer is static HTML** — `lucide.createIcons()` runs on page load, so new `data-lucide` elements get processed automatically.
- **Type badge template** has `type_icon` in context (dict with `icon`, `color` keys) but doesn't use it yet. No backend changes needed.

## Verification

- Visual inspection at `http://localhost:4000/browser/`: open an object tab, check type badge has icon + colored border
- View explorer sidebar: confirm Lucide icons render with distinct colors per view type
- Tab bar: active tab visually pops compared to inactive tabs
- Body editor: softer gutters, no hard-coded hex visible, proportional font for prose
- Dark mode toggle: verify all four surfaces adapt correctly
- Grep: `grep -n '#[0-9a-fA-F]\{3,8\}' frontend/static/js/editor.js` should return 0 results after CM6 theme tokenization

## Skill Relevance

The `make-interfaces-feel-better` skill covers design engineering principles (borders, shadows, typography, optical alignment) relevant to tab contrast and badge styling. The planner should load it for micro-interaction guidance.

No external skills needed — this is vanilla CSS + Jinja2 + minor JS.
