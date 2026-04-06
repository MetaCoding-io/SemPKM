---
estimated_steps: 25
estimated_files: 3
skills_used: []
---

# T02: Add cancelled timeline bar color, right panel empty state, and tree-leaf underline fix

## Description

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

## Inputs

- ``frontend/static/css/views.css` — existing bar-done/bar-active/bar-blocked rules (line ~1547)`
- ``frontend/static/css/workspace.css` — .tree-leaf (line ~281) and .right-empty (line ~2062) rules`
- ``backend/app/templates/browser/workspace.html` — right pane sections (line ~226-256)`
- ``frontend/static/css/theme.css` — --_color-gray-400 primitive already defined`

## Expected Output

- ``frontend/static/css/views.css` — added .bar-cancelled .bar-progress CSS rule`
- ``frontend/static/css/workspace.css` — added text-decoration:none to .tree-leaf, added .right-empty-icon sizing`
- ``backend/app/templates/browser/workspace.html` — updated right pane empty state text and icon`

## Verification

rg 'bar-cancelled' frontend/static/css/views.css | grep -q bar-progress && rg 'text-decoration.*none' frontend/static/css/workspace.css | grep -q tree-leaf && test $(rg -c 'Select an object' backend/app/templates/browser/workspace.html) -ge 3 && rg 'right-empty-icon' frontend/static/css/workspace.css | grep -q flex-shrink
