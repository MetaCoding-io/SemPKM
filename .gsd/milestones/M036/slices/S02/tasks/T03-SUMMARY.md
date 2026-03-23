---
id: T03
parent: S02
milestone: M036
provides:
  - frontend/static/css/bmc.css — 443-line CSS Grid layout with 9-section positioning, color tints, dark mode
  - frontend/static/js/bmc.js — 157-line IIFE with inline editing, debounced saves, dockview isolation
key_files:
  - frontend/static/css/bmc.css
  - frontend/static/js/bmc.js
key_decisions:
  - Used 10-column grid (not 5-column doubled) for precise section spanning — allows Key Partners and Value Propositions to span 2 columns while Key Activities/Resources each get 2 columns in the middle stack
  - Each section gets a unique color identity (9 distinct hues) rather than grouping by category — makes the poster more visually scannable
patterns_established:
  - BMC textarea inline editing uses debounce timer map keyed by IRI — cancels pending debounce on blur for immediate save, same command API pattern as quadrant drag-drop
  - Dark mode tints use same rgba() approach as quadrant.css — 0.07 alpha for light mode, 0.12 alpha for dark mode, with 0.25 border alpha in dark
observability_surfaces:
  - console.error('bmc: failed to patch section content for', iri, err) on save failure
  - console.log('[bmc] scope sync: scopeQuery=... from panel=...') on scope-changed events
  - .bmc-save-error CSS class (red flash 1.5s) and .bmc-save-ok CSS class (green flash 0.6s) for visual save feedback
duration: 10min
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Build BMC frontend — CSS Grid layout, inline editing JS, dark mode

**Created bmc.css (443 lines) with 10×3 CSS Grid poster layout and 9 color-coded sections, plus bmc.js (157 lines) with debounced inline editing via object.patch and dockview drag isolation.**

## What Happened

Built both frontend files following the quadrant.css/quadrant.js patterns:

- **bmc.css**: 10-column × 3-row CSS Grid with `[data-section-type]` attribute selectors positioning all 9 BMC sections in the canonical layout (Key Partners spanning left column, Value Propositions center, Customer Segments right, Cost Structure/Revenue Streams bottom). Each section has a unique pastel tint (steel blue, emerald, teal, blue, rose, orange, purple, slate, amber). Full dark mode with `html[data-theme="dark"]` overrides (deeper tints, adjusted borders and header accents). `.view-flex-column` integration for dockview panel fill. Responsive single-column at < 800px. Textarea hover/focus styling with transparent background in rest state. Lucide SVG flex-shrink safety. Save error/success flash classes.

- **bmc.js**: IIFE with `initBMC(boardEl)` that attaches `input` (debounced 500ms) and `blur` (immediate) event listeners on `.bmc-item-textarea` elements. `_saveSectionContent()` POSTs `object.patch` command with `urn:sempkm:model:business-planning:sectionContent` property. Success dispatches `sempkm:command-executed` and flashes green; failure logs to console and flashes red. `stopPropagation()` on dragstart/dragover/drop/dragleave for dockview isolation. `sempkm:scope-changed` listener for htmx re-fetch. Exported as `window.initBMC` for the template's lazy-load boot.

## Verification

All 7 task-level checks pass:
1. `wc -l bmc.css` → 443 lines (≥ 200) ✅
2. `wc -l bmc.js` → 157 lines (≥ 80) ✅
3. `grep -c "data-section-type" bmc.css` → 55 (≥ 9) ✅
4. `grep -c 'data-theme="dark"' bmc.css` → 22 (≥ 1) ✅
5. `grep -c "stopPropagation" bmc.js` → 2 (≥ 1) ✅
6. `grep -c "object.patch" bmc.js` → 1 (≥ 1) ✅
7. `grep -c "initBMC" bmc.js` → 2 (≥ 2, definition + export) ✅

Slice-level checks applicable to T03:
- All 5 JSON-LD model files parse ✅
- `parse_manifest()` validates ✅
- `bmc` in `_VALID_RENDERERS` and `RENDERER_REGISTRY` ✅
- `stopPropagation` in bmc.js ✅
- `data-theme="dark"` in bmc.css ✅
- CSS Grid positions 9 sections via `[data-section-type]` ✅
- `test_bmc.py` — file not yet created (T04 task) ⏳

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `wc -l frontend/static/css/bmc.css` | 0 | ✅ pass (443 lines) | 0.1s |
| 2 | `wc -l frontend/static/js/bmc.js` | 0 | ✅ pass (157 lines) | 0.1s |
| 3 | `grep -c "data-section-type" frontend/static/css/bmc.css` | 0 | ✅ pass (55) | 0.1s |
| 4 | `grep -c 'data-theme="dark"' frontend/static/css/bmc.css` | 0 | ✅ pass (22) | 0.1s |
| 5 | `grep -c "stopPropagation" frontend/static/js/bmc.js` | 0 | ✅ pass (2) | 0.1s |
| 6 | `grep -c "object.patch" frontend/static/js/bmc.js` | 0 | ✅ pass (1) | 0.1s |
| 7 | `grep -c "initBMC" frontend/static/js/bmc.js` | 0 | ✅ pass (2) | 0.1s |
| 8 | `rdflib parse all 5 model JSON-LD files` | 0 | ✅ pass | 3.0s |
| 9 | `parse_manifest()` | 0 | ✅ pass | 1.5s |
| 10 | `bmc in RENDERER_REGISTRY and _VALID_RENDERERS` | 0 | ✅ pass | 1.5s |

## Diagnostics

- **CSS grid layout**: Inspect `frontend/static/css/bmc.css` — section positions defined at lines ~21-65 via `[data-section-type]` attribute selectors
- **Save behavior**: In browser devtools, watch Network tab for `POST /api/commands` with `object.patch` payload after editing a textarea
- **Save feedback**: `.bmc-save-ok` (green flash) and `.bmc-save-error` (red flash) CSS classes briefly applied after save attempt
- **Scope sync**: Console log `[bmc] scope sync:` when a sibling view changes scope

## Deviations

None — followed quadrant.css/quadrant.js patterns exactly as planned.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/css/bmc.css` — 443-line CSS Grid layout with 9-section positioning, 9 color tints, dark mode, responsive breakpoint, textarea editing styles
- `frontend/static/js/bmc.js` — 157-line IIFE with initBMC(), debounced inline editing via object.patch, dockview drag isolation, scope-changed listener
- `.gsd/milestones/M036/slices/S02/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
