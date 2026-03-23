---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T03: Create OKR + Decision Matrix frontend (CSS + JS)

**Slice:** S03 — OKR Progress + Decision Matrix Weighted Scoring
**Milestone:** M036

## Description

Create the CSS and JS files for both renderers. OKR gets progress bars with color-coded completion percentages. Decision Matrix gets a sortable weighted table with rank badges. Both must support dark mode and dockview panel isolation following the same IIFE patterns as `quadrant.js` and `bmc.js`.

## Steps

1. **okr.css** — Create `frontend/static/css/okr.css`. Layout: `.okr-board` with `.view-flex-column` and `flex: 1; min-height: 0; overflow-y: auto`. Objective cards: `.okr-objective` with border, padding, margin-bottom. Key result rows: `.okr-kr-row` with flex layout (title | current/target | progress bar). Progress bar: `.okr-progress-bar` container (background: neutral gray) with `.okr-progress-fill` inner div (width set via inline style). Color classes: `.okr-progress-green` (≥70%, use `#22c55e`/`#16a34a`), `.okr-progress-amber` (30–69%, use `#f59e0b`/`#d97706`), `.okr-progress-red` (<30%, use `#ef4444`/`#dc2626`). Dark mode: `html[data-theme="dark"]` overrides using rgba tints (0.07/0.12 alpha pattern from quadrant.css/bmc.css). Responsive: stack key result rows at < 600px width. Lucide icon sizing: any `svg` inside okr containers gets `width: 16px; height: 16px; flex-shrink: 0; stroke: currentColor`.

2. **okr.js** — Create `frontend/static/js/okr.js`. IIFE structure matching `quadrant.js`/`bmc.js`. `initOKR(boardEl)` called on DOMContentLoaded and via lazy-load boot. Features: (a) Click-to-edit on `.okr-current-value` elements — click reveals input, blur/enter saves via `object.patch` command with `bp:currentValue` property, shows save feedback. (b) `sempkm:scope-changed` event listener for view refresh (re-fetch via htmx). (c) `stopPropagation()` on dragstart/dragover/drop/dragleave for dockview isolation. (d) Error handling: `console.error("okr: failed to patch ...")` on API failure with visual feedback class.

3. **decision-matrix.css** — Create `frontend/static/css/decision-matrix.css`. Layout: `.dm-board` with `.view-flex-column` and overflow-y auto. Table: `.dm-table` with full width, border-collapse. Header cells: criteria names with weight in parentheses below. Score cells: centered numbers with subtle background tint based on value (optional gradient). Total column: bold, wider, with background gradient from green (highest) to red (lowest). Rank column: `.dm-rank-1` (🥇 gold background), `.dm-rank-2` (🥈 silver), `.dm-rank-3` (🥉 bronze), `.dm-rank-n` (neutral). Dark mode: `html[data-theme="dark"]` overrides. Responsive: horizontal scroll wrapper at narrow widths.

4. **decision-matrix.js** — Create `frontend/static/js/decision-matrix.js`. IIFE structure. `initDecisionMatrix(boardEl)` called via lazy-load boot. Features: (a) Client-side column sorting — click header to sort alternatives by that criterion's score (ascending/descending toggle). Re-ranks after sort. (b) `sempkm:scope-changed` event listener for refresh. (c) `stopPropagation()` on drag events for dockview isolation. (d) Error handling on any API calls.

## Must-Haves

- [ ] `okr.css` has progress bar with 3 color levels (green/amber/red) and dark mode
- [ ] `okr.js` has IIFE with `initOKR`, click-to-edit, scope-changed listener, stopPropagation
- [ ] `decision-matrix.css` has table styling, rank badges, and dark mode
- [ ] `decision-matrix.js` has IIFE with `initDecisionMatrix`, sort, scope-changed listener, stopPropagation
- [ ] All CSS files have `html[data-theme="dark"]` rules
- [ ] All JS files use `stopPropagation()` on drag events for dockview isolation
- [ ] SVG icon sizing via CSS with `flex-shrink: 0` (not inline styles)

## Verification

- `test -f frontend/static/js/okr.js && test -f frontend/static/css/okr.css` — exist
- `test -f frontend/static/js/decision-matrix.js && test -f frontend/static/css/decision-matrix.css` — exist
- `rg 'data-theme="dark"' frontend/static/css/okr.css` — at least 3 rules
- `rg 'data-theme="dark"' frontend/static/css/decision-matrix.css` — at least 3 rules
- `rg 'stopPropagation' frontend/static/js/okr.js` — at least 1 occurrence
- `rg 'stopPropagation' frontend/static/js/decision-matrix.js` — at least 1 occurrence
- `rg 'initOKR' frontend/static/js/okr.js` — function defined
- `rg 'initDecisionMatrix' frontend/static/js/decision-matrix.js` — function defined
- `rg 'scope-changed' frontend/static/js/okr.js frontend/static/js/decision-matrix.js` — present in both

## Inputs

- `frontend/static/js/quadrant.js` — reference IIFE pattern (189 lines)
- `frontend/static/js/bmc.js` — reference IIFE pattern (157 lines)
- `frontend/static/css/quadrant.css` — reference dark mode pattern (286 lines)
- `frontend/static/css/bmc.css` — reference dark mode pattern (443 lines)
- `backend/app/templates/browser/okr_view.html` — T02 output template referencing CSS classes and JS init function
- `backend/app/templates/browser/decision_matrix_view.html` — T02 output template referencing CSS classes and JS init function

## Expected Output

- `frontend/static/css/okr.css` — OKR progress bar styling with dark mode (~150–250 lines)
- `frontend/static/js/okr.js` — OKR interactivity IIFE (~120–180 lines)
- `frontend/static/css/decision-matrix.css` — Decision Matrix table styling with dark mode (~150–250 lines)
- `frontend/static/js/decision-matrix.js` — Decision Matrix sorting IIFE (~100–150 lines)
