# S04 Research: Forms, Timeline & Final Polish

## Summary

Straightforward CSS polish slice with four independent surfaces: (1) form section headers with accent bars, (2) timeline bar status colors, (3) right panel empty state, (4) view name underline fix. All work is CSS-only except a small template tweak for the right panel empty state. No backend changes needed — the timeline already queries and maps status→CSS classes but those classes have no CSS definitions.

## Recommendation

Three tasks: T01 for form section headers + help text tightening, T02 for timeline status bar colors, T03 for right panel empty state + view name underline fix. All CSS-focused, no backend changes.

## Implementation Landscape

### 1. Form Section Headers (#18, #22)

**Current state:** `.form-group-summary` in `workspace.css:2788` — 0.85rem, font-weight 600, plain background. No accent bar, no visual hierarchy beyond bold text. `.field-help` in `workspace.css:2656` has `margin-bottom: 6px` which creates decent spacing but `line-height: 1.45` and `font-size: 0.76rem` could be tighter.

**Files:**
- `frontend/static/css/workspace.css` — `.form-group-summary` (line ~2788), `.field-help` (line ~2656)
- `frontend/static/css/forms.css` — duplicate `.field-help` at line 50 (less specific, workspace.css wins in the cascade)

**Approach:** Add a colored left border accent (3px solid `var(--color-primary)`) to `.form-group-summary`, give it a subtle background (`var(--color-surface-raised)`), and slightly increase font size to 0.88rem. For help text, reduce `margin-bottom` from 6px to 3px and tighten `line-height` to 1.35. All token-based — no new primitives needed.

**Template file:** `backend/app/templates/forms/_group.html` — the `<summary class="form-group-summary">` element is where the accent bar CSS applies. No template changes needed.

### 2. Timeline Bar Status Colors (#51)

**Current state:** Backend (`service.py:3224`) already defines `_TIMELINE_STATUS_CLASSES`:
```
done/completed → "bar-done"
in-progress/in progress → "bar-active"  
blocked → "bar-blocked"
cancelled → "bar-cancelled"
```

These classes are set as `custom_class` on each Gantt task object. Frappe Gantt applies `custom_class` to the bar's `<g>` SVG group element. **But zero CSS rules exist for these classes** — grep for `bar-done`, `bar-active`, `bar-blocked`, `bar-cancelled` across all CSS files returns nothing.

The template (`timeline_view.html`) passes `custom_class` through to the Gantt constructor at line ~91. The wiring is complete — only CSS is missing.

**Files:**
- `frontend/static/css/views.css` — add Frappe Gantt bar color overrides
- `frontend/static/css/theme.css` — may need new primitives if existing ones don't cover the palette

**Approach:** Frappe Gantt renders bars as `<rect class="bar">` inside `<g class="bar-wrapper {custom_class}">`. Override with:
```css
.bar-done .bar { fill: color-mix(in srgb, var(--_color-green-500) 70%, transparent); }
.bar-active .bar { fill: color-mix(in srgb, var(--_color-amber-500) 70%, transparent); }
.bar-blocked .bar { fill: color-mix(in srgb, var(--_color-red-500) 70%, transparent); }
.bar-cancelled .bar { fill: color-mix(in srgb, var(--_color-gray-400) 50%, transparent); }
```

Check if `--_color-green-500`, `--_color-amber-500`, `--_color-red-500` already exist in theme.css (they do — used by kanban enrichment in S01). `--_color-gray-400` was added in S01. No new primitives needed.

**Risk:** Frappe Gantt's CSS specificity may override our styles. The CDN stylesheet loads its own `.bar` fill. Our overrides need sufficient specificity — `.bar-done .bar` should work since Frappe only applies `.bar` to the rect. Verify with `.gantt .bar-done .bar` if needed.

**Dark mode:** Using `color-mix()` with theme primitives that already have dark-mode overrides means no extra dark-mode CSS blocks needed.

### 3. Right Panel Empty State (#17)

**Current state:** Right pane (`workspace.html:218`) has three `<details class="right-section">` sections (RELATIONS, LINT, COMMENTS), each with `<div class="right-empty">No object selected</div>` as default content. These sections display regardless of whether an object is selected.

**What `workspace.js` does:** When a tab is activated, `_loadRightPaneForObject(objectIri)` fetches `/browser/apps/right-pane-sections?iri=...` and replaces `#right-pane-dynamic` innerHTML. When tabs are empty (`sempkm:tabs-empty` event), it could show a helpful prompt instead.

**Approach:** Replace the generic "No object selected" text with a more helpful empty state:
- Add an icon (Lucide `info`) and instructive text: "Select an object to view its details"
- Style with `.right-pane-empty-state` class — centered, muted, with icon
- This is pure CSS + minor HTML tweak in `workspace.html`

**Files:**
- `backend/app/templates/browser/workspace.html` — modify `#right-pane-dynamic` default content
- `frontend/static/css/workspace.css` — add `.right-pane-empty-state` styling

### 4. View Name Underline (#59)

**Current state:** View entries in the explorer sidebar are `<a class="tree-leaf view-leaf">` elements. The `.tree-leaf` class does NOT set `text-decoration: none`. The global CSS reset (`style.css`) does NOT have `a { text-decoration: none }`. So browser default `text-decoration: underline` applies to these `<a>` tags.

**Approach:** Add `text-decoration: none` to `.tree-leaf` in `workspace.css`. One line. This fixes all tree leaf links (objects, views, saved views) consistently.

**Files:**
- `frontend/static/css/workspace.css` — add `text-decoration: none` to `.tree-leaf` (line ~281)

## Constraints

1. **color-mix() pattern mandatory** (K014) — all new decorative colors via `color-mix(in srgb, var(--_color-*) N%, transparent)`
2. **Lucide icons in flex containers** need `flex-shrink: 0` and CSS-based sizing (CLAUDE.md)
3. **SVG stroke inheritance** — `stroke: currentColor` on any new icon elements
4. **Dark mode** — all new CSS must use semantic tokens or primitives with existing dark-mode overrides
5. **workspace.css is ~9200 lines** — surgical edits only, use `edit` tool precisely

## Task Decomposition Recommendation

**T01: Form Section Headers & Help Text Polish**
- Files: `frontend/static/css/workspace.css` (`.form-group-summary`, `.field-help`)
- Scope: Add accent bar + background to section headers, tighten help text spacing
- Verify: `grep -c 'border-left.*primary' workspace.css` > 0, visual inspection

**T02: Timeline Bar Status Colors**
- Files: `frontend/static/css/views.css` (new Frappe Gantt overrides)
- Scope: CSS rules for `.bar-done`, `.bar-active`, `.bar-blocked`, `.bar-cancelled`
- Verify: `grep -c 'bar-done' views.css` > 0, all 4 classes present

**T03: Right Panel Empty State + View Name Underline Fix**
- Files: `backend/app/templates/browser/workspace.html` (right pane default content), `frontend/static/css/workspace.css` (`.tree-leaf` text-decoration, empty state styling)
- Scope: Replace generic empty text with styled prompt, fix underline on tree leaf links
- Verify: `grep 'text-decoration.*none' workspace.css | grep tree-leaf` matches, right pane has empty state class

## Skills Assessment

No external skills needed. Established CSS patterns from S01-S03 cover all techniques. The `make-interfaces-feel-better` skill could inform the form header accent design, but the approach is straightforward enough from existing codebase patterns.
