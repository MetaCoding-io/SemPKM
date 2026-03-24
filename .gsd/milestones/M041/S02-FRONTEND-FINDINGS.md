# S02: Frontend Code Quality Audit — Findings

**Audit date:** 2026-03-23
**Total frontend JS:** 18,587 LOC across 28 files
**Total frontend CSS:** 20,495 LOC across 16 files
**Scope:** JavaScript structure, global state, DOM/event patterns, error handling, CSS architecture & theming

---

## JS Structure & Global State

### Finding JS-01: workspace.js is a 5,409-line monolith with 170 functions

**Severity:** High
**Effort:** Large (multi-sprint decomposition)
**Category:** Maintainability / Modularity

`frontend/static/js/workspace.js` contains 170 functions across 5,409 lines in a single IIFE — the largest file by 3x. It handles at least 12 unrelated concerns: tab management, object CRUD, editor wiring, persona switching, command palette, VFS mounts, lint dashboard, favorites, SPARQL widgets, chart rendering, relation panels, and event undo. This makes it difficult to reason about, test, or modify any single feature without risk of side effects.

**Detection command:**
```bash
wc -l frontend/static/js/workspace.js
grep -cE "function\s+\w+\(|=\s*function\s*\(|=>\s*\{" frontend/static/js/workspace.js
```

**Files >500 LOC (all IIFE pattern unless noted):**

| File | LOC | Functions | Pattern | Notes |
|------|-----|-----------|---------|-------|
| workspace.js | 5,409 | 170 | IIFE (×5) | 12+ concerns in one file |
| canvas.js | 1,783 | 51 | IIFE | Canvas session management |
| copilot.js | 1,771 | 50 | ESM (dynamic import) | AI chat feature |
| sparql-console.js | 1,769 | 43 | ESM | SPARQL editor/console |
| vfs-browser.js | 1,076 | 32 | IIFE | Virtual file system |
| graph.js | 1,020 | 23 | IIFE | Cytoscape graph view |
| recurrence-editor.js | 640 | 29 | IIFE | RRULE editor widget |
| workspace-layout.js | 626 | 21 | IIFE | Dockview panel layout |
| auth.js | 501 | 10 | IIFE | Auth flows (setup, login, invite) |

---

### Finding JS-02: 124 global state assignments on window object in workspace.js

**Severity:** Medium
**Effort:** Medium (incremental migration)
**Category:** Encapsulation / Testability

`workspace.js` assigns to `window.*` 124 times. Total across all JS files: ~222 assignments. The `window` namespace is used for cross-IIFE communication (documented in KNOWLEDGE.md as a deliberate pattern), but the scale creates collision risk and makes the dependency graph invisible.

**Top contributors:**

| File | `window.* =` count |
|------|---------------------|
| workspace.js | 124 |
| graph.js | 15 |
| workspace-layout.js | 14 |
| federation.js | 13 |
| tutorials.js | 10 |
| editor.js | 8 |
| canvas.js | 7 |
| calendar.js | 5 |

**Detection command:**
```bash
rg "window\.\w+ =" frontend/static/js/ -n --count
```

---

### Finding JS-03: Inconsistent module patterns — 25 IIFE files vs 3 ESM files

**Severity:** Low
**Effort:** Large (full migration to ESM would need bundler)
**Category:** Architecture Consistency

25 of 28 JS files use the IIFE pattern (`(function() { ... })();`). Only 3 newer files use ESM (`import`/`export`): `copilot.js`, `editor.js`, `sparql-console.js`. The codebase has no bundler — files are loaded via `<script>` tags, so the IIFE pattern is necessary for non-module scripts. The ESM files use dynamic `import()` called from workspace.js.

This is a documented architectural choice, not a defect. But the split means newer features can use modern patterns while older code cannot be incrementally migrated without adding a build step.

**Detection command:**
```bash
grep -l "^(function" frontend/static/js/*.js | wc -l   # IIFE count
grep -l "^export\|^import " frontend/static/js/*.js     # ESM files
```

---

### Finding JS-04: console.log/console.error in production code

**Severity:** Low
**Effort:** Small
**Category:** Code Hygiene

126 `console.*` calls remain across 19 JS files. Most are `console.error` for debugging, with some `console.log` and `console.warn`. The heaviest offenders:

| File | console.* count |
|------|-----------------|
| workspace.js | 45 |
| copilot.js | 23 |
| calendar.js | 13 |
| graph.js | 9 |
| sparql-console.js | 6 |
| vfs-browser.js | 5 |
| tutorials.js | 5 |

Some of these are intentional (error logging in catch blocks), but many are diagnostic leftovers. A structured approach would be: keep `console.error` in catch blocks, remove `console.log` from production paths, and use a gated debug logger for development-only output.

**Detection command:**
```bash
rg "console\." frontend/static/js/ --count
```

---

## DOM & Event Patterns

### Finding DOM-01: 188 unmatched addEventListener calls (208 add vs 20 remove)

**Severity:** High
**Effort:** Medium (requires per-file audit to determine which are intentional)
**Category:** Memory Leaks / Resource Management

Across all JS files, 208 event listeners are added but only 20 are removed. The 188 unmatched listeners represent a potential memory leak surface — especially in views that are created and destroyed dynamically (dockview panels, tab content).

**Not all are bugs:** Page-level listeners (DOMContentLoaded, resize, keydown) are intentionally permanent. But listeners attached to dynamically created elements inside dockview panels (graph nodes, editor instances, kanban cards) should be cleaned up when the panel is destroyed.

**Files with highest listener imbalance:**

| File | addEventListener | removeEventListener | Imbalance |
|------|-----------------|---------------------|-----------|
| workspace.js | 37 | 3 | 34 |
| copilot.js | 26 | 2 | 24 |
| sparql-console.js | 23 | 0 | 23 |
| recurrence-editor.js | 18 | 2 | 16 |
| canvas.js | 17 | 1 | 16 |
| vfs-browser.js | 19 | 4 | 15 |
| kanban.js | 6 | 0 | 6 |
| quadrant.js | 6 | 0 | 6 |

**Detection command:**
```bash
rg "addEventListener" frontend/static/js/ -n --count
rg "removeEventListener" frontend/static/js/ -n --count
```

---

### Finding DOM-02: 48 setTimeout calls with only 9 clearTimeout — timers not tracked

**Severity:** Medium
**Effort:** Small per-instance
**Category:** Resource Management / Race Conditions

48 `setTimeout` calls exist across the codebase but only 9 `clearTimeout` calls. Most setTimeout calls are fire-and-forget UI animations (class removal after 300ms, toast auto-dismiss). These are generally safe. However, some are used for debouncing (FTS search, BMC autosave, VFS preview) where the timer reference IS tracked and cleared — this is the correct pattern.

**Timers with proper cleanup (good):**
- `workspace.js:1921` — `_ftsDebounce` cleared before re-set
- `bmc.js:51` — `_timers[iri]` cleared before re-set
- `vfs-browser.js:735` — `_previewTimers[path]` cleared before re-set
- `graph.js:445,636` — `_hoverTimer`, `_edgeHoverTimer` cleared on mouseout

**One `setInterval` with no `clearInterval`:**
- `federation.js:62` — `setInterval(updateInboxBadge, 60000)` runs forever. If the federation panel is closed and reopened, a second interval starts. No dedup guard.

**Detection command:**
```bash
rg "setInterval|setTimeout" frontend/static/js/ -n
rg "clearInterval|clearTimeout" frontend/static/js/ -n
```

---

### Finding DOM-03: 67 of 131 fetch() calls (51%) have incomplete error handling

**Severity:** High
**Effort:** Medium (mechanical fix per call site)
**Category:** Error Handling / User Experience

Of 131 `fetch()` calls across 19 JS files, 67 (51%) are missing either a `.catch()` handler, a `response.ok` check, or both. This means network failures or server errors silently fail, leaving the UI in an inconsistent state with no user feedback.

**Breakdown:**
- Missing `.catch()`: 51 calls — network errors (offline, timeout, DNS failure) produce an uncaught Promise rejection
- Missing `response.ok` check: 32 calls — server 4xx/5xx responses are silently treated as success
- Missing both: 16 calls — worst case, any failure is invisible

**Worst offenders (by count of unhandled fetches):**

| File | Total fetch | Missing error handling | % unhandled |
|------|-------------|----------------------|-------------|
| workspace.js | 49 | 30 | 61% |
| copilot.js | 13 | 13 | 100% |
| sparql-console.js | 15 | 5 | 33% |
| canvas.js | 11 | 4 | 36% |
| settings.js | 3 | 3 | 100% |
| calendar.js | 4 | 3 | 75% |
| federation.js | 8 | 3 | 38% |
| vfs-browser.js | 6 | 3 | 50% |
| graph.js | 2 | 2 | 100% |
| markdown-render.js | 1 | 1 | 100% |

**Sample high-risk unhandled fetches:**

| Location | URL | Missing |
|----------|-----|---------|
| workspace.js:670 | `/browser/object/{iri}` | .catch + resp.ok |
| workspace.js:1790 | `/api/apps/commands` | .catch + resp.ok |
| workspace.js:1821 | `/browser/views/available` | .catch + resp.ok |
| workspace.js:3221 | relation detail endpoint | .catch + resp.ok |
| copilot.js:929 | `/api/copilot/approve` | .catch + resp.ok |
| canvas.js:220 | `/api/canvas/sessions/` | .catch + resp.ok |
| settings.js:7 | `/browser/settings/data` | .catch + resp.ok |

**Detection command:**
```bash
rg "fetch\(" frontend/static/js/ -A10 -n  # then inspect for .catch and resp.ok
```

**Recommended fix pattern:**
```javascript
fetch(url, options)
  .then(function(resp) {
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  })
  .then(function(data) { /* handle */ })
  .catch(function(err) {
    console.error('Operation failed:', err);
    showToast('Operation failed: ' + err.message, 4000);
  });
```

---

### Finding DOM-04: No centralized fetch wrapper — error handling duplicated ad hoc

**Severity:** Medium
**Effort:** Small (create utility, large to migrate all callers)
**Category:** DRY / Error Handling Architecture

Every fetch call reinvents the error-handling wheel. Some check `resp.ok`, some don't. Some have `.catch`, some don't. Some show user-facing errors, some silently fail. There is no shared `apiFetch()` utility that enforces consistent error handling, auth redirect on 401, or request cancellation.

The closest pattern is the `fetch` + `.then(resp.ok check)` + `.catch` chain used in `kanban.js`, `okr.js`, and some `workspace.js` calls. But it's copy-pasted, not extracted.

A centralized wrapper would:
1. Check `resp.ok` and throw on non-2xx
2. Handle 401 → redirect to login
3. Always have a `.catch` that shows user feedback
4. Optionally support AbortController

**Detection:** Compare any two fetch calls in workspace.js — the error handling (when present) varies in approach and user feedback mechanism.

---

## CSS Architecture & Theming

**Total CSS:** 20,495 LOC across 16 files
**CSS variable adoption:** 89.7% (2,517 var() references vs 286 standalone hardcoded color values)
**Theme system:** Two-tier token architecture in `theme.css` — primitives (`--_*`) + semantics (`--color-*`)

**CSS files by size:**

| File | LOC | var() refs | Hardcoded hex | Hardcoded rgba | `!important` |
|------|-----|-----------|---------------|----------------|-------------|
| workspace.css | 9,203 | 1,205 | 201 (169 as fallbacks) | 101 | 40 |
| style.css | 2,749 | 322 | 12 | 8 | 6 |
| views.css | 1,819 | 257 | 25 | 8 | 9 |
| import.css | 997 | 120 | 78 (67 as fallbacks) | 8 | 0 |
| copilot.css | 972 | 105 | 18 | 10 | 0 |
| settings.css | 950 | 115 | 39 | 0 | 2 |
| vfs-browser.css | 772 | 74 | 24 | 0 | 0 |
| federation.css | 503 | 45 | 9 | 0 | 0 |
| theme.css | 477 | 108 | 55 (definitions) | 30 (definitions) | 1 |
| forms.css | 455 | 63 | 0 | 0 | 2 |
| bmc.css | 443 | 17 | 8 | 61 | 0 |
| okr.css | 320 | 24 | 15 | 16 | 0 |
| decision-matrix.css | 320 | 11 | 4 | 26 | 0 |
| quadrant.css | 286 | 23 | 7 | 25 | 0 |
| context-indicator.css | 129 | 7 | 4 | 0 | 0 |
| dockview-sempkm-bridge.css | 100 | 21 | 0 | 0 | 1 |

---

### Finding CSS-01: 84 standalone hardcoded hex colors bypass the theme system

**Severity:** Medium
**Effort:** Small-Medium (mechanical variable replacement)
**Category:** Theming Consistency / Dark Mode

Of 499 hex color instances across all CSS files, 360 are used as `var()` fallback values (acceptable degradation pattern), 55 are variable definitions in `theme.css` (expected), and **84 are standalone hardcoded values** that bypass the theme system entirely. These will not respond to theme changes (e.g., dark mode).

**Most-shared standalone colors (appearing in 3+ files — candidates for variable extraction):**

| Color | Files using it | Semantic mapping |
|-------|---------------|-----------------|
| `#fff` | 10 files | → `var(--color-surface)` or `var(--_color-white)` |
| `#1e1e1e` | 5 files | → `var(--color-text)` (dark mode surface?) |
| `#ef4444` | 4 files | → `var(--color-error)` |
| `#dc2626` | 4 files | → `var(--color-error)` variant |
| `#888` | 4 files | → `var(--color-text-muted)` |
| `#3b82f6` | 4 files | → `var(--color-primary)` |
| `#333` | 4 files | → `var(--color-text)` |
| `#22c55e` | 4 files | → `var(--color-success)` |
| `#16a34a` | 4 files | → `var(--color-success)` variant |

**Worst offenders by standalone hardcoded count:**

| File | Standalone hex | Notes |
|------|---------------|-------|
| workspace.css | 32 | Status colors, syntax highlighting, drag states |
| views.css | 12 | FullCalendar event colors, button states |
| import.css | 11 | Legacy status borders and text colors |
| vfs-browser.css | 9 | File-type icon colors, accent blue |
| okr.css | 6 | Progress bar RAG colors |

**Detection command:**
```bash
rg "#[0-9a-fA-F]{3,8}\b" frontend/static/css/ -n | grep -v "var(--" | grep -v "theme.css"
```

---

### Finding CSS-02: 202 standalone hardcoded rgba() values bypass theme system

**Severity:** Medium
**Effort:** Medium (need `color-mix()` or additional CSS variables)
**Category:** Theming Consistency / Dark Mode

202 `rgba()` values across CSS files use raw RGB values instead of referencing CSS variables. These are harder to fix than hex colors because CSS custom properties can't be directly interpolated inside `rgba()` in older syntax. The modern `color-mix(in srgb, var(--color-x) 15%, transparent)` pattern is already used in some places (e.g., workspace.css:8462) but not consistently.

**Worst offenders:**

| File | Hardcoded rgba | Notes |
|------|---------------|-------|
| workspace.css | 101 | Shadows, overlays, status backgrounds |
| bmc.css | 61 | Quadrant background tints |
| decision-matrix.css | 26 | Cell background gradients |
| quadrant.css | 25 | Quadrant region fills |
| okr.css | 16 | Progress indicators |

**Detection command:**
```bash
rg "rgba\(" frontend/static/css/ -n | grep -v "var(--" | grep -v "theme.css" | wc -l
```

---

### Finding CSS-03: 61 `!important` declarations — 30 are necessary vendor overrides, 31 are avoidable

**Severity:** Low
**Effort:** Medium (refactor specificity for the 31 avoidable ones)
**Category:** Specificity / Maintainability

61 `!important` declarations exist across 8 CSS files. Categorization:

**Necessary (vendor library overrides) — 30 total:**
- workspace.css lines 4354–4411: **30** declarations overriding driver.js (guided tour library) default styles. These are standard practice — the library's own CSS loads first, application theming overrides via `!important`.

**Avoidable — 31 total:**

| File | Count | Purpose | Why avoidable |
|------|-------|---------|---------------|
| workspace.css | 10 | Field highlight, drag indicators, form resets | Could increase selector specificity instead |
| views.css | 9 | FullCalendar button colors, kanban drag states | FC overrides could use `:where()` or higher specificity |
| style.css | 6 | Modal/toast styling | Modal context should have naturally higher specificity |
| settings.css | 2 | Layout fixes for flex direction / width | Structural issue — specificity war between layout rules |
| forms.css | 2 | Disabled state text color | Could use `[disabled]` attribute selector for higher specificity |
| dockview-sempkm-bridge.css | 1 | Tab border accent | Overrides dockview's default styles — borderline necessary |
| theme.css | 1 | Unknown context | Should be unnecessary in the theme definition file |

**Detection command:**
```bash
rg "!important" frontend/static/css/ -n --count | sort -t: -k2 -rn
# Categorize driver.js block:
awk 'NR>=4354 && NR<=4411' frontend/static/css/workspace.css | grep -c "!important"
```

---

### Finding CSS-04: Inconsistent responsive breakpoints — 4 different values, no shared tokens

**Severity:** Low
**Effort:** Small (define breakpoint variables or document standard set)
**Category:** Responsive Design Consistency

12 `@media` queries use 4 different breakpoint values with no CSS custom property tokens:

| Breakpoint | Usage count | Files |
|-----------|-------------|-------|
| 600px | 5 | workspace.css, style.css, import.css, okr.css, decision-matrix.css |
| 640px | 3 | style.css (×2), views.css |
| 768px | 3 | workspace.css, style.css, import.css |
| 800px | 1 | bmc.css |

**Issues:**
1. **No breakpoint tokens** — values are hardcoded in each `@media` query. CSS custom properties can't be used in media queries, but a documented standard set (e.g., `--bp-sm: 600px`, `--bp-md: 768px`) with a comment convention would prevent drift.
2. **640px vs 600px overlap** — `style.css` uses both 640px and 600px for different sections. The 40px gap means some layouts change at 640px while sibling content changes at 600px, causing a jarring intermediate state.
3. **800px outlier** — `bmc.css` uses 800px while all other files use 600/640/768. This may be intentional (BMC layout is wider) but it's undocumented.
4. **workspace.css has only 2 breakpoints** for 9,203 lines — the main workspace has minimal responsive design, relying on dockview's panel system instead.

**Detection command:**
```bash
rg "@media" frontend/static/css/ -n
```

---

### Finding CSS-05: Repeated property patterns suggest missing shared utility classes

**Severity:** Low
**Effort:** Medium (extract utilities, update selectors)
**Category:** DRY / Maintainability

workspace.css alone contains heavily repeated property patterns that could be extracted into shared utility classes:

| Pattern | Occurrences in workspace.css | Candidate utility |
|---------|------------------------------|-------------------|
| `display: flex` | 165 | `.flex` |
| `align-items: center` | 134 | `.items-center` |
| `flex-shrink: 0` | 134 | `.shrink-0` |
| `cursor: pointer` | 101 | `.pointer` |
| `font-size: 0.8*rem` | 115 | `.text-sm` family |
| `border-radius: 4px` | 68 | `.rounded` |
| `border-radius: 6px` | 43 | `.rounded-md` |
| `gap: 8px` | 32 | `.gap-2` |
| `padding: 4px 8px` | 17 | `.px-2 .py-1` |
| `padding: 6px 12px` | 12 | `.px-3 .py-1.5` |

This is not necessarily a problem — CSS naturally repeats common properties. But the `flex + align-items: center + flex-shrink: 0` triplet appears ~130 times, suggesting a `.flex-center` utility class would significantly reduce file size and improve consistency.

**Note:** Without a bundler or utility framework (Tailwind, etc.), utility classes would need to be defined in a shared CSS file and used via class names in templates. The trade-off is: fewer CSS lines but more HTML class attributes.

**Detection command:**
```bash
rg "display: flex" frontend/static/css/workspace.css -c
rg "border-radius: 4px" frontend/static/css/workspace.css -c
rg "font-size:\s*0\.8[0-9]*rem" frontend/static/css/workspace.css -c
```

---

*Remaining dimension sections (Jinja2 Template Hygiene, htmx Consistency) will be added by T03.*
