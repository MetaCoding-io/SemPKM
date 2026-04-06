# S04: Forms, Timeline & Final Polish

**Goal:** Form sections have prominent headers with accent bars and tighter help text. Timeline bars have status colors for all four states (including cancelled). Right panel shows helpful empty state. View name underline inconsistency resolved.
**Demo:** After this: Form sections have prominent headers with accent bars and tighter help text. Timeline bars have status colors. Right panel shows helpful empty state. View name underline inconsistency resolved.

## Tasks
- [x] **T01: Added 3px primary accent bar, raised background, and border-radius to .form-group-summary; reduced .field-help margin and line-height for tighter spacing** — ## Description

Add visual prominence to form section headers (`.form-group-summary`) and tighten the spacing on help text (`.field-help`). Both are CSS-only edits in `workspace.css`.

## Steps

1. Read `frontend/static/css/workspace.css` around line 2788 to see the current `.form-group-summary` rules.
2. Add `border-left: 3px solid var(--color-primary)` to `.form-group-summary`.
3. Add `background: var(--color-surface-raised)` and increase font size to `0.88rem`.
4. Add subtle `border-radius: 4px` for polish.
5. Read `.field-help` around line 2656. Reduce `margin-bottom` from `6px` to `3px`. Reduce `line-height` from `1.45` to `1.35`.
6. Verify with grep that the accent bar and spacing changes are present.

## Must-Haves

- [ ] `.form-group-summary` has `border-left` with `--color-primary`
- [ ] `.form-group-summary` has `background: var(--color-surface-raised)`
- [ ] `.field-help` `margin-bottom` is 3px or less
- [ ] `.field-help` `line-height` is 1.35 or less
- [ ] Zero hardcoded hex values in the edited rules

## Verification

- `rg 'border-left.*primary' frontend/static/css/workspace.css | grep -q form-group-summary` exits 0
- `rg 'surface-raised' frontend/static/css/workspace.css | grep -q form-group-summary` exits 0
- `rg 'margin-bottom.*3px' frontend/static/css/workspace.css | grep -q field-help` exits 0
  - Estimate: 15m
  - Files: frontend/static/css/workspace.css
  - Verify: rg 'border-left.*primary' frontend/static/css/workspace.css | grep -q form-group-summary && rg 'surface-raised' frontend/static/css/workspace.css | grep -q form-group-summary && rg 'margin-bottom.*3px' frontend/static/css/workspace.css | grep -q field-help
- [x] **T02: Added all four Frappe Gantt timeline bar status colors, updated right-panel empty state with info icon and descriptive text, and fixed tree-leaf link underlines** — ## Description

Three independent CSS/template fixes bundled together because each is a one-line or small edit.

### Timeline cancelled bar color
The backend maps cancelled status to CSS class `bar-cancelled` (see `_TIMELINE_STATUS_CLASSES` in `service.py:3224`). S01 added CSS rules for `.bar-done`, `.bar-active`, and `.bar-blocked` in `views.css` — but `.bar-cancelled` is missing. Add it with a gray fill using the `--_color-gray-400` primitive from theme.css.

### Right panel empty state
The right pane in `workspace.html` shows three `<div class="right-empty">No object selected</div>` elements as default content. Replace these with a more helpful prompt: 'Select an object to see its details' and add a Lucide info icon. Add CSS styling for the empty state.

### Tree-leaf underline fix
`.tree-leaf` in workspace.css is an `<a>` tag but has no `text-decoration: none`. Browser default underline shows on all tree leaf links (objects, views, saved views). Add `text-decoration: none` to the `.tree-leaf` rule.

## Steps

1. Read `frontend/static/css/views.css` around line 1547 to see existing bar status rules. Add `.bar-cancelled .bar-progress` rule after `.bar-blocked .bar-progress` with `fill: var(--_color-gray-400);` (the primitive already exists in theme.css).
2. Read `frontend/static/css/workspace.css` around line 281 (`.tree-leaf`). Add `text-decoration: none;` to the existing rule block.
3. Edit `backend/app/templates/browser/workspace.html` to replace the three `<div class="right-empty">No object selected</div>` elements in the right pane sections with `<div class="right-empty"><i data-lucide="info" class="right-empty-icon"></i> Select an object to see its details</div>`.
4. Add CSS for `.right-empty-icon` in workspace.css near the existing `.right-empty` rule (line ~2062): `width: 14px; height: 14px; flex-shrink: 0; stroke: currentColor; vertical-align: -2px;` (inline SVG from Lucide). Also add `display: inline-flex; align-items: center; gap: 4px;` to `.right-empty` so the icon sits properly.
5. Verify all three changes with grep.

## Must-Haves

- [ ] `.bar-cancelled .bar-progress` CSS rule exists in views.css
- [ ] `.tree-leaf` has `text-decoration: none` in workspace.css
- [ ] Right panel shows 'Select an object to see its details' instead of 'No object selected'
- [ ] Right empty icon has `flex-shrink: 0` (per CLAUDE.md Lucide icon rule)
- [ ] Zero hardcoded hex values in new CSS rules

## Verification

- `rg 'bar-cancelled' frontend/static/css/views.css | grep -q bar-progress` exits 0
- `rg 'text-decoration.*none' frontend/static/css/workspace.css | grep -q tree-leaf` exits 0
- `rg 'Select an object' backend/app/templates/browser/workspace.html | wc -l` returns 3
- `rg 'right-empty-icon' frontend/static/css/workspace.css | grep -q flex-shrink` exits 0
  - Estimate: 20m
  - Files: frontend/static/css/views.css, frontend/static/css/workspace.css, backend/app/templates/browser/workspace.html
  - Verify: rg 'bar-cancelled' frontend/static/css/views.css | grep -q bar-progress && rg 'text-decoration.*none' frontend/static/css/workspace.css | grep -q tree-leaf && test $(rg -c 'Select an object' backend/app/templates/browser/workspace.html) -ge 3 && rg 'right-empty-icon' frontend/static/css/workspace.css | grep -q flex-shrink
