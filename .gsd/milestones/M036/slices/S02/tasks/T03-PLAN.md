---
estimated_steps: 3
estimated_files: 2
skills_used: []
---

# T03: Build BMC frontend — CSS Grid layout, inline editing JS, dark mode

**Slice:** S02 — Business Model Canvas — 9-Box Poster Renderer
**Milestone:** M036

## Description

Create the CSS Grid layout for the BMC 9-box poster and the JavaScript for inline content editing with debounced saves. The CSS positions 9 sections in the canonical BMC layout using a 10-column × 3-row grid, with section-specific color tints and full dark mode support. The JS handles textarea blur/input events, debounced `object.patch` calls, and dockview isolation.

## Steps

1. **Read** `frontend/static/css/quadrant.css` and `frontend/static/js/quadrant.js` to understand the established patterns (CSS Grid, dark mode, IIFE structure, drag event isolation, command API calls).
2. **Create `bmc.css`** with: (a) `.bmc-board` — the 10-column × 3-row CSS Grid container (`grid-template-columns: repeat(10, 1fr)`, `grid-template-rows: 1fr 1fr 0.6fr`). (b) `[data-section-type]` positioning selectors for all 9 sections: Key Partners (col 1-3, row 1-3), Key Activities (col 3-5, row 1-2), Key Resources (col 3-5, row 2-3), Value Propositions (col 5-7, row 1-3), Customer Relationships (col 7-9, row 1-2), Channels (col 7-9, row 2-3), Customer Segments (col 9-11, row 1-3), Cost Structure (col 1-6, row 3-4), Revenue Streams (col 6-11, row 3-4). Note: using 10 columns means positions are 1-based with max col 11. (c) Section-specific color tints — each section gets a subtle background tint (e.g., Key Partners: blue-50, Value Propositions: green-50, Revenue Streams: amber-50). (d) Dark mode via `html[data-theme="dark"]` — darker tints, lighter text, border adjustments. (e) `.bmc-section-header` styling — bold label, border-bottom, section color accent. (f) `.bmc-section-content textarea` — borderless, full-width, auto-resize styling, transparent background. (g) `.bmc-empty-hint` — italic gray placeholder when section has no content. (h) `.view-flex-column` integration for full-height in dockview panel (`flex:1; min-height:0` on `.bmc-board`). (i) Responsive: at narrow widths (< 800px), switch to single-column stacked layout.
3. **Create `bmc.js`** as an IIFE following `quadrant.js` pattern: (a) `initBMC(boardEl)` — find all textareas inside `.bmc-section`, attach `input` event listener with debounce (500ms) that calls `_saveSectionContent(textarea)`. Attach `blur` event for immediate save on focus loss. (b) `_saveSectionContent(textarea)` — read `data-iri` from closest `.bmc-item`, build `object.patch` command with `bp:sectionContent` property and textarea value, POST to `/api/commands`. Handle success (dispatch `sempkm:command-executed`) and failure (console.error, add `.bmc-save-error` class briefly). (c) `stopPropagation()` on `dragstart`, `dragover`, `drop`, `dragleave` events on `.bmc-board` to prevent dockview panel interference. (d) Listen for `sempkm:scope-changed` custom event — trigger htmx swap if the board has `hx-get`. (e) Export `window.initBMC` for the template's lazy-load boot.

## Must-Haves

- [ ] CSS Grid positions all 9 BMC sections in correct poster layout
- [ ] Each section has a distinct color tint
- [ ] Dark mode via `html[data-theme="dark"]` with readable contrast
- [ ] Inline textarea editing triggers `object.patch` on blur with debounce
- [ ] `stopPropagation()` on drag events for dockview isolation
- [ ] `.view-flex-column` integration for full-height panel rendering
- [ ] Flex-shrink: 0 on any Lucide icons per project CSS rule

## Verification

- `wc -l frontend/static/css/bmc.css` — 200+ lines
- `wc -l frontend/static/js/bmc.js` — 80+ lines
- `grep -c "data-section-type" frontend/static/css/bmc.css` — ≥ 9
- `grep -c 'data-theme="dark"' frontend/static/css/bmc.css` — ≥ 1
- `grep -c "stopPropagation" frontend/static/js/bmc.js` — ≥ 1
- `grep -c "object.patch" frontend/static/js/bmc.js` — ≥ 1
- `grep -c "initBMC" frontend/static/js/bmc.js` — ≥ 2 (definition + export)

## Observability Impact

- **JS console signals**: `console.error('bmc: failed to patch section content for', iri, err)` on save failure — visible in browser devtools and E2E `browser_get_console_logs`
- **JS console info**: `[bmc] scope sync: scopeQuery=... from panel=...` on scope-changed events
- **Visual feedback**: `.bmc-save-error` CSS class (red border flash, 1.5s) on failed patch; `.bmc-save-ok` CSS class (green border flash, 0.6s) on success
- **Failure inspection**: If the textarea shows a red flash after editing, check browser network tab for the `/api/commands` response body — the error detail is in the JSON
- **Scope sync**: When the board has a `.scope-syncing` class briefly, it's re-fetching data from the backend via htmx

## Inputs

- `frontend/static/css/quadrant.css` — CSS Grid pattern, dark mode approach, color tinting
- `frontend/static/js/quadrant.js` — IIFE structure, drag isolation, command API pattern
- `backend/app/templates/browser/bmc_view.html` — template structure from T02 (data attributes, section layout)

## Expected Output

- `frontend/static/css/bmc.css` — CSS Grid layout with 9-section positioning, color tints, dark mode
- `frontend/static/js/bmc.js` — IIFE with inline editing, debounced saves, dockview isolation
