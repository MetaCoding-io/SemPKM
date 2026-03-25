---
estimated_steps: 13
estimated_files: 1
skills_used: []
---

# T02: Write frontend conventions documentation

Create `docs/FRONTEND-CONVENTIONS.md` — a developer-facing reference documenting the frontend patterns and conventions established by M044 and prior milestones. This is the codebase's definitive frontend guide.

The document covers six sections:

1. **htmx Patterns** — Swap modes (innerHTML dominant, outerHTML for replacements, none for side-effect triggers), trigger patterns (load, change, click once, input changed delay:300ms, intersect once, custom events from:body), hx-boost="false" for opt-out links, htmx event listeners used (htmx:afterSwap, htmx:afterSettle, htmx:configRequest, htmx:responseError, htmx:pushedIntoHistory), partial rendering via jinja2-fragments block_name.

2. **JavaScript Module Structure** — IIFE pattern with 'use strict', exports via `window.SemPKM.X = ...` (D370), api-fetch.js bootstraps the namespace (`window.SemPKM = window.SemPKM || {}`), each file re-asserts the namespace guard before exporting.

3. **CSS Theme System** — All colors via `var(--_color-*)` semantic/primitive tokens in theme.css, transparent variants via `color-mix(in srgb, var(--_color-X) N%, transparent)`, breakpoints: 600px (mobile), 768px (tablet) — no other values, dark mode via `[data-theme="dark"]` selector on `<html>` (D371).

4. **Debug Logging** — `SemPKM.debug(tag, ...args)` for development tracing, enable via `localStorage.setItem('sempkm_debug', '1')`, console.warn/error for operational signals (unconditional).

5. **Fetch Conventions** — All HTTP calls via `SemPKM.apiFetch()` — never raw `fetch()` (D369), one exemption: auth.js `/api/auth/me`, error handling: apiFetch provides safety net, callers use `{silent:true}` and handle UX locally.

6. **Event Cleanup** — `SemPKM.registerCleanup(elementId, fn)` / `SemPKM.runCleanup(elementId)` for dockview panel lifecycle, `htmx:beforeCleanupElement` event for DOM-removal cleanup.

**Key sources to reference** (read these before writing):
- `frontend/static/js/api-fetch.js` — namespace bootstrap, apiFetch, debug utility
- `frontend/static/css/theme.css` — CSS variable system, breakpoints, dark mode
- D369, D370, D371 decision rationale from `.gsd/DECISIONS.md`
- S01 (fetch), S02 (event cleanup), S03 (namespace), S04 (CSS theme) slice summaries

## Inputs

- `frontend/static/js/api-fetch.js`
- `frontend/static/css/theme.css`

## Expected Output

- `docs/FRONTEND-CONVENTIONS.md`

## Verification

test -f docs/FRONTEND-CONVENTIONS.md && grep -c '^## ' docs/FRONTEND-CONVENTIONS.md  # must be >= 6 sections
