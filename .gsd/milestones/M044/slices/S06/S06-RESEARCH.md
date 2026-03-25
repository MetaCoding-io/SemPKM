# S06 Research: Console Cleanup & Convention Documentation

**Depth:** Light research — straightforward cleanup work using established patterns in the codebase. No new technology, no ambiguous requirements.

## Summary

S06 has three deliverables: (1) replace all `console.log` calls with a debug utility gated by a localStorage flag, (2) document htmx conventions and frontend patterns, (3) keep console.warn/error as-is (they're legitimate). The scope is small and well-defined — 32 console.log calls across 11 JS files + 5 in template inline scripts.

## Requirement Coverage

No active requirements are directly owned by this slice. It supports the milestone-level success criterion: "htmx conventions documented, breakpoints standardized, console.log cleaned."

## Recommendation

Three tasks:
1. **T01: Debug utility + console.log migration** — Create a `SemPKM.debug(tag, ...args)` function gated by `localStorage.getItem('sempkm_debug')`, migrate all 37 console.log calls to use it.
2. **T02: Frontend convention documentation** — Write `docs/FRONTEND-CONVENTIONS.md` covering htmx patterns, JS module structure, CSS theme system, namespace convention, and debug logging.
3. **T03: Verification** — Confirm zero `console.log` in production, debug flag works, doc completeness.

T01 and T02 are independent. T03 depends on both.

## Implementation Landscape

### Console.log Inventory (37 total)

**JS files (32 calls across 11 files):**

| File | Count | Pattern | Tags |
|------|-------|---------|------|
| copilot.js | 10 | `console.log('copilot: ...')` | State tracking (init, conversations, personas) |
| calendar.js | 7 | `console.log('[calendar] ...')` | Action tracing (drop, persist, scope sync) |
| workspace.js | 5 | `console.log('SemPKM: ...')` | Persona init/switch, scope propagation |
| graph.js | 2 | `console.log('[graph] ...')` | Isometric transform apply/remove |
| tutorials.js | 2 | `console.log('[SemPKM] ...')` | Tour start/complete |
| bmc.js | 1 | `console.log('[bmc] scope sync...')` | Scope sync |
| decision-matrix.js | 1 | `console.log('[decision-matrix] scope sync...')` | Scope sync |
| kanban.js | 1 | `console.log('[kanban] scope sync...')` | Scope sync |
| okr.js | 1 | `console.log('[okr] scope sync...')` | Scope sync |
| quadrant.js | 1 | `console.log('[quadrant] scope sync...')` | Scope sync |
| recurrence-editor.js | 1 | `console.log('[recurrence-editor] loaded')` | Init |

**Template inline scripts (5 calls across 2 files):**

| File | Count | Pattern |
|------|-------|---------|
| browser/timeline_view.html | 4 | `console.log('[timeline] ...')` |
| browser/workspace.html | 1 | `console.log('[SemPKM] CTA banner shown')` |

### console.warn/error (keep as-is)

~60 console.warn/error calls across all JS files. These are legitimate operational logging:
- `console.error(...)` — actual errors (network failures, missing DOM, load failures)
- `console.warn(...)` — degraded operation (missing optional dependency, parse failures)
- `api-fetch.js` already uses `console.error('[apiFetch] ...')` for its safety-net logging

These should NOT be converted to the debug utility — they represent real operational signals.

### Debug Utility Design

**Where:** Add to `api-fetch.js` (the file that bootstraps `window.SemPKM`). This is the earliest custom script in load order.

**API:**
```javascript
window.SemPKM.debug = function(tag, ...args) {
  if (localStorage.getItem('sempkm_debug')) {
    console.log('[' + tag + ']', ...args);
  }
};
```

**localStorage flag:** `sempkm_debug` — follows the existing naming convention (`sempkm_theme`, `sempkm_demo_tour_done`, `sempkm_graph_icon_mode`). Set to any truthy value to enable (e.g., `localStorage.setItem('sempkm_debug', '1')`). Can be filtered by tag value for selective logging (future enhancement — not in scope).

**Migration pattern:**
```javascript
// Before:
console.log('[calendar] rendered with', count, 'events');

// After:
SemPKM.debug('calendar', 'rendered with', count, 'events');
```

For templates, use `window.SemPKM.debug(...)` since SemPKM isn't a bare global in template inline scripts (or use the fact that S03 made it available as `SemPKM.debug`).

### Existing console.debug Usage

One existing call: `workspace.js:2065` uses `console.debug(...)`. This is fine — `console.debug` doesn't render in production Chrome (requires Verbose log level). No action needed.

### Convention Documentation

No existing developer-facing frontend conventions doc. `.planning/codebase/CONVENTIONS.md` is a stale February planning artifact covering general naming patterns — not htmx patterns, not M044 outcomes.

**Target file:** `docs/FRONTEND-CONVENTIONS.md` — developer-facing, git-tracked.

**Sections to document:**

1. **htmx Patterns**
   - Swap modes: innerHTML (173 usages, dominant), outerHTML (19), none (11), beforeend (1)
   - Trigger patterns: `load` (14), `change` (21), `click once` (16), `input changed delay:300ms` (7), `intersect once` (3), custom events from:body
   - `hx-boost="false"` for opt-out links (7 usages)
   - htmx event listeners: `htmx:afterSwap`, `htmx:afterSettle`, `htmx:configRequest`, `htmx:responseError`, `htmx:pushedIntoHistory`
   - Partial rendering via `jinja2-fragments` block_name parameter

2. **JavaScript Module Structure**
   - IIFE pattern with `'use strict'`
   - Exports via `window.SemPKM.X = ...` (D370)
   - `api-fetch.js` bootstraps the namespace (`window.SemPKM = window.SemPKM || {}`)
   - Each file re-asserts the namespace guard before exporting

3. **CSS Theme System** (from S04 outcomes)
   - All colors via `var(--_color-*)` semantic/primitive tokens in theme.css
   - Transparent variants via `color-mix(in srgb, var(--_color-X) N%, transparent)`
   - Breakpoints: 600px (mobile), 768px (tablet) — no other values
   - Dark mode via `[data-theme="dark"]` selector on `<html>`

4. **Debug Logging**
   - `SemPKM.debug(tag, ...args)` for development tracing
   - Enable via `localStorage.setItem('sempkm_debug', '1')`
   - `console.warn/error` for operational signals (keep unconditional)

5. **Fetch Conventions** (from S01/D369)
   - All HTTP calls via `SemPKM.apiFetch()` — never raw `fetch()`
   - One exemption: `auth.js /api/auth/me`
   - Error handling: apiFetch provides safety net, callers use `{silent:true}` and handle UX locally

6. **Event Cleanup** (from S02)
   - `SemPKM.registerCleanup(elementId, fn)` / `SemPKM.runCleanup(elementId)` for dockview panel lifecycle
   - `htmx:beforeCleanupElement` event for DOM-removal cleanup

### Breakpoints

Already standardized to 600/768 by S04. Only 12 `@media` queries across all CSS, all using these two values. No action needed — just document in conventions.

### Files Changed

**T01 (debug utility + migration):**
- `frontend/static/js/api-fetch.js` — add SemPKM.debug()
- `frontend/static/js/copilot.js` — 10 replacements
- `frontend/static/js/calendar.js` — 7 replacements
- `frontend/static/js/workspace.js` — 5 replacements
- `frontend/static/js/graph.js` — 2 replacements
- `frontend/static/js/tutorials.js` — 2 replacements
- `frontend/static/js/bmc.js` — 1 replacement
- `frontend/static/js/decision-matrix.js` — 1 replacement
- `frontend/static/js/kanban.js` — 1 replacement
- `frontend/static/js/okr.js` — 1 replacement
- `frontend/static/js/quadrant.js` — 1 replacement
- `frontend/static/js/recurrence-editor.js` — 1 replacement
- `backend/app/templates/browser/timeline_view.html` — 4 replacements
- `backend/app/templates/browser/workspace.html` — 1 replacement

**T02 (convention doc):**
- `docs/FRONTEND-CONVENTIONS.md` — new file

### Verification

- `grep -rn 'console\.log' frontend/static/js/ backend/app/templates/` → zero hits
- Open browser console with `sempkm_debug` unset → clean console (no debug output)
- Set `localStorage.setItem('sempkm_debug', '1')` → debug logs appear
- Convention doc covers all six sections listed above
