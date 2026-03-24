# S02: Frontend Code Quality Audit — Findings

**Audit date:** 2026-03-23
**Total frontend JS:** 18,587 LOC across 28 files
**Total frontend CSS:** 20,495 LOC across 16 files
**Total Jinja2 templates:** 18,323 LOC across 165 files
**Scope:** JavaScript structure, global state, DOM/event patterns, error handling, CSS architecture & theming, Jinja2 template hygiene, htmx consistency

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

## Jinja2 Template Hygiene

**Total templates:** 165 files, 18,323 LOC
**Logic density:** 1,002 control-flow statements ({% if/for/set/macro %})
**Partial reuse:** 67 {% include %} calls across 35 templates
**Template inheritance:** 28 templates use {% extends %}, 137 are standalone partials/fragments

---

### Finding TPL-01: 23 templates >200 LOC with zero partial extraction ({% include %})

**Severity:** Medium
**Effort:** Medium (extract shared sections into partials)
**Category:** DRY / Maintainability

23 templates exceed 200 lines of code and contain zero `{% include %}` statements. These are monolithic templates where common patterns (form buttons, status badges, permission checks, navigation elements) are inlined rather than extracted into reusable partials.

**Worst offenders:**

| Template | LOC | Logic stmts | Notes |
|----------|-----|-------------|-------|
| dashboard_builder.html | 749 | 14 | Complex builder UI, no shared components |
| guide.html | 578 | 5 | 55 identical hx-swap/hx-get chapter buttons |
| admin/model_detail.html | 481 | 23 | Model admin, deeply nested conditionals |
| workflow_builder.html | 477 | 11 | Workflow editor, parallel to dashboard_builder |
| admin/apps/detail.html | 356 | 34 | App admin detail, highest logic density |
| ontology/ontology_page.html | 345 | 15 | 6 tabbed sections, each could be a partial |
| admin/models.html | 333 | 18 | Model listing with inline table logic |
| forms/object_form.html | 312 | 28 | Object CRUD form with inline field rendering |
| docs_page.html | 286 | 3 | 26 identical hx-swap/hx-get doc chapter buttons |
| admin/model_ontology_diagram.html | 281 | 3 | SVG diagram generation |
| indieauth/consent.html | 275 | 7 | OAuth consent screen |
| ontology/edit_class_form.html | 266 | 13 | Class editor form |
| _webid_settings.html | 265 | 6 | WebID settings panel |

**Detection command:**
```bash
for f in $(fd -e html . backend/app/templates/); do
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 200 ]; then
    inc=$(rg -c "\{%\s*include" "$f" 2>/dev/null || echo "0")
    if [ "$inc" = "0" ]; then
      echo "  $f ($lines LOC, 0 includes)"
    fi
  fi
done
```

---

### Finding TPL-02: Computation logic in templates via namespace() hacks and .append() side-effects

**Severity:** High
**Effort:** Medium (move logic to Python view functions)
**Category:** Separation of Concerns / Testability

7 templates use Jinja2's `namespace()` workaround (to mutate variables across scopes) and 10 use `.append()` side-effects to build lists in-place. This is computation that belongs in the Python view function, not in the template. These patterns are untestable, hard to debug, and fragile.

**`namespace()` usage (mutating variables across scopes):**

| Template | Line | Purpose |
|----------|------|---------|
| object_read.html | 44 | `namespace(has_values=false)` — check if any property has values |
| object_read.html | 69 | `namespace(any_prop=false)` — check if any property exists |
| object_form.html | 81 | `namespace(required_props=[], optional_ungrouped=[])` — partition properties |
| object_form.html | 110 | `namespace(group_props=[])` — filter properties per group |
| object_tab.html | 24 | `namespace(n=0)` — count items |
| object_embed.html | 22 | `namespace(any_prop=false)` — duplicate of object_read.html logic |
| notion/.../property_mapping.html | 45 | `namespace(iri=None)` — auto-match lookup |

**`.append()` side-effects (building lists in templates):**

| Template | Line | Purpose |
|----------|------|---------|
| dashboard_builder.html | 59 | Group block types by category |
| object_read.html | 54 | Build form_paths list |
| object_embed.html | 18 | Build form_paths list (duplicate) |
| saved_queries_explorer.html | 9,11 | Split queries into model/user lists |
| _context_rules.html | 49 | Build has_conds list (boolean accumulator hack) |
| admin/models.html | 195,198 | Flatten property lists |
| notion/.../scan_results.html | 150 | Group warnings by category |
| obsidian/.../scan_results.html | 145 | Group warnings by category |

**Why this matters:** The `object_read.html` template has 45 logic statements in 284 lines — a 15.8% logic density — performing property filtering, path comparison, source attribution (inferred vs mirrored), and empty-state detection. All of this could be precomputed in the view function and passed as simple template variables.

**Detection command:**
```bash
rg "namespace\(" backend/app/templates/ -n
rg "\.append\(" backend/app/templates/ -n
```

---

### Finding TPL-03: Notion/Obsidian importer templates are near-duplicate sets (9 matching files)

**Severity:** Medium
**Effort:** Medium (extract shared base templates with importer-specific blocks)
**Category:** DRY / Maintenance Cost

The Notion and Obsidian importers have 9 templates with identical filenames and largely similar structure. The total diff surface is significant but the structural patterns are the same — a shared base template with importer-specific slots would eliminate ~800 LOC of duplication.

| Template | Notion LOC | Obsidian LOC | Diff lines | Similarity |
|----------|-----------|-------------|------------|------------|
| upload_form.html | 90 | 90 | 18 | ~90% identical |
| import_progress.html | 109 | 109 | 10 | ~95% identical |
| step_bar.html | 28 | 27 | 7 | ~87% identical |
| scan_trigger.html | 95 | 89 | 14 | ~92% identical |
| type_mapping.html | 125 | 89 | 80 | ~63% similar |
| property_mapping.html | 145 | 125 | 60 | ~78% similar |
| import_summary.html | 140 | 138 | 70 | ~75% similar |
| preview.html | 152 | 111 | 95 | ~64% similar |
| scan_results.html | 213 | 192 | 183 | ~55% similar |

The most similar templates (upload_form, import_progress, step_bar, scan_trigger) are >87% identical and are strong candidates for extraction. The less similar ones (scan_results, preview) have importer-specific fields but share the same HTML structure.

**Detection command:**
```bash
for tpl in upload_form.html import_progress.html step_bar.html scan_trigger.html type_mapping.html property_mapping.html import_summary.html preview.html scan_results.html; do
  diff backend/app/templates/notion/partials/$tpl backend/app/templates/obsidian/partials/$tpl | grep -c "^[<>]"
done
```

---

### Finding TPL-04: Zero url_for() usage — all 349 URLs are hardcoded strings

**Severity:** Medium
**Effort:** Large (architectural decision — url_for or path constants)
**Category:** Maintainability / Refactoring Safety

Across 165 templates, there are 349 hardcoded URL references (59 `href="/"`, 19 `action="/"`, 212 `hx-get="/"`, 49 `hx-post="/"`, 10 `hx-delete="/"`) and **zero** `url_for()` calls. Every route reference is a raw string like `hx-get="/browser/objects/{{ iri }}"`.

This means renaming any backend route requires updating every template that references it — a mechanical but error-prone process with no compiler assistance.

**Mitigating factor:** 107 of the 349 URLs contain Jinja2 `{{ }}` expressions (dynamic segments), meaning they're already coupled to the view's context variables. Jinja2's `url_for()` wouldn't eliminate this coupling but would make route-name changes safer.

**Breakdown by htmx method:**

| Method | Count | Notes |
|--------|-------|-------|
| hx-get | 212 | Primary htmx interaction pattern |
| href | 59 | Static navigation links |
| hx-post | 49 | Form submissions, create/update |
| action | 19 | Traditional form submissions |
| hx-delete | 10 | Delete operations |

**Detection command:**
```bash
rg '(href|action|hx-get|hx-post|hx-put|hx-delete|hx-patch)="/' backend/app/templates/ --count | awk -F: '{sum+=$2} END{print sum}'
rg "url_for" backend/app/templates/ --count
```

---

## htmx Consistency

**Total htmx interactions:** 283 (224 hx-get, 49 hx-post, 10 hx-delete, 0 hx-put, 0 hx-patch)
**Explicit hx-swap:** 265 (of which 242 on elements without hx-get/hx-post on the same line — separate targets)
**Explicit hx-trigger:** 82

---

### Finding HTMX-01: 88% of hx-swap is innerHTML, but no documented convention exists

**Severity:** Low
**Effort:** Small (document convention)
**Category:** Consistency / Developer Guidance

Of 265 explicit `hx-swap` values:

| Strategy | Count | % | Usage |
|----------|-------|---|-------|
| innerHTML | 230 | 86.8% | Content replacement inside container |
| outerHTML | 21 | 7.9% | Full element replacement (admin CRUD) |
| none | 11 | 4.2% | Fire-and-forget (import step navigation) |
| outerHTML swap:0.3s | 2 | 0.8% | Animated replacement (models.html only) |
| beforeend | 1 | 0.4% | Append (event_log.html only) |

The overwhelmingly consistent use of `innerHTML` is good — but 242 htmx interactions rely on the default swap behavior (no explicit `hx-swap` attribute). Since htmx's default is `innerHTML`, this works, but explicit is better than implicit for maintainability.

**Convention inconsistency:** `admin/models.html` uses `outerHTML swap:0.3s` (transition timing) in 2 places but no other template uses swap transitions. Either adopt transitions broadly or remove this outlier.

**Detection command:**
```bash
rg 'hx-swap="([^"]*)"' backend/app/templates/ -or '$1' | sed 's/.*://' | sort | uniq -c | sort -rn
```

---

### Finding HTMX-02: Inconsistent hx-trigger patterns — 14 unique trigger types, mixed conventions

**Severity:** Medium
**Effort:** Small-Medium (standardize on fewer patterns)
**Category:** Consistency / Predictability

82 explicit `hx-trigger` values use 14 distinct patterns:

| Trigger | Count | Usage |
|---------|-------|-------|
| change | 21 | Select/dropdown changes |
| click once | 16 | Tree expand/collapse (lazy load) |
| load | 14 | Initial content load for panels |
| custom events from:body | 9 | Cross-component communication |
| input changed delay:300ms | 9 | Search/filter debounce |
| intersect once | 3 | Lazy load on scroll into view |
| revealed / revealed once | 3 | Similar to intersect — redundant? |
| keyup changed delay:300ms, focus | 2 | Search with focus trigger |
| load, every 60s | 1 | Polling (inbox_panel only) |
| loadForm / loadPropertyForm | 2 | Custom event names (ontology editor) |
| input changed delay:200ms, focus | 1 | Different debounce than 300ms variant |
| focus | 1 | Standalone focus trigger |

**Issues:**
1. **Debounce inconsistency:** `_field.html` uses `delay:200ms` while all other search inputs use `delay:300ms`. No documented standard debounce interval.
2. **`revealed` vs `intersect once`:** Both achieve lazy loading but use different htmx mechanisms. `intersect once` is the newer, documented approach; `revealed` is a legacy trigger.
3. **Custom event names** (`loadForm`, `loadPropertyForm`, `workflowsRefreshed`, `dashboardsRefreshed`, etc.) are ad hoc with no naming convention or registry. Finding all listeners for `classCreated` requires grepping templates.
4. **183 htmx interactions have NO explicit hx-trigger** — they rely on the element's natural event (click for buttons/links, submit for forms). This is usually correct but makes the trigger behavior implicit.

**Detection command:**
```bash
rg 'hx-trigger="([^"]*)"' backend/app/templates/ -or '$1' | sed 's/.*://' | sort | uniq -c | sort -rn
```

---

### Finding HTMX-03: guide.html and docs_page.html contain 81 near-identical htmx button blocks

**Severity:** Low
**Effort:** Small (extract into a Jinja2 macro or loop)
**Category:** DRY / Maintainability

`guide.html` has 55 and `docs_page.html` has 26 nearly identical `<button>` elements with `hx-get`, `hx-target`, `hx-swap`, and `onclick` attributes. Each button loads a chapter/doc section. The only variation is the URL path, button text, and icon.

**Example (one of 55 identical patterns in guide.html):**
```html
<button class="chapter-btn" hx-get="/guide/chapter/..." hx-target="#guide-content" hx-swap="innerHTML" onclick="...">
  <i data-lucide="..."></i> Chapter Title
</button>
```

These could be generated from a Jinja2 loop over a chapters list variable passed from the view function, reducing 550+ lines to ~15 lines.

**Detection command:**
```bash
rg 'hx-swap=' backend/app/templates/guide.html -c
rg 'hx-swap=' backend/app/templates/browser/docs_page.html -c
```

---

### Finding HTMX-04: No hx-put or hx-patch usage — all mutations via hx-post

**Severity:** Low
**Effort:** N/A (informational — may be intentional)
**Category:** REST Semantics / API Design

All 49 mutation htmx calls use `hx-post`. Zero use `hx-put` (full update) or `hx-patch` (partial update). This is common in htmx applications where the backend determines create-vs-update from the presence of an identifier, but it means the template doesn't communicate intent — every mutation looks the same to a developer reading the HTML.

The 10 `hx-delete` calls do follow REST semantics correctly.

**Detection command:**
```bash
rg -c 'hx-put=' backend/app/templates/   # 0
rg -c 'hx-patch=' backend/app/templates/  # 0
rg -c 'hx-post=' backend/app/templates/   # 49
rg -c 'hx-delete=' backend/app/templates/ # 10
```
