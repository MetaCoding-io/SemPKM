# S02: Frontend Code Quality Audit — Findings

**Audit date:** 2026-03-23
**Total frontend JS:** 18,587 LOC across 28 files
**Scope:** JavaScript structure, global state, DOM/event patterns, error handling

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

*Remaining dimension sections (CSS Architecture & Theming, Jinja2 Template Hygiene, htmx Consistency) will be added by T02 and T03.*
