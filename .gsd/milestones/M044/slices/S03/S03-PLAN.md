# S03: Window Namespace Consolidation

**Goal:** All cross-IIFE communication uses window.SemPKM.functionName instead of window.functionName — zero collision risk with third-party libraries
**Demo:** After this: all cross-IIFE communication uses window.SemPKM.functionName instead of window.functionName — zero collision risk with third-party libraries

## Must-Haves

- All ~231 `window.X =` assignments in frontend/static/js/ migrated to `window.SemPKM.X =`
- All template onclick handlers and inline scripts reference `SemPKM.X()` instead of bare `X()` or `window.X()`
- All E2E test `page.evaluate()` calls use `window.SemPKM.X` instead of `window.X`
- Zero backward-compat shims remain — all `window.X = window.SemPKM.X` lines removed
- `rg 'window\.\w+ =' frontend/static/js/ | grep -v 'window\.SemPKM' | grep -v '//'` returns zero lines (excluding browser builtins)
- All modified JS files pass `node -c` syntax check
- Existing `window.SemPKMSettings`, `window.SemPKMLayouts`, `window.SemPKMCanvas` left untouched (already namespaced)

## Proof Level

- This slice proves: Contract — all JS files export to SemPKM namespace, all templates consume from it, E2E tests reference it. Full runtime proof deferred to S07 E2E regression suite.

## Integration Closure

Upstream: S01 produced `apiFetch()` in api-fetch.js — S03 migrates its export to `window.SemPKM.apiFetch`. S02 produced `registerCleanup()`/`runCleanup()` in cleanup.js — S03 migrates those exports. No new wiring — purely moving existing globals under a namespace object. What remains: S07 E2E regression suite proves the namespace migration doesn't break runtime behavior.

## Verification

- None — this is a pure namespace refactoring with no runtime behavior changes. No new logs, metrics, or state surfaces.

## Tasks

- [x] **T01: Namespace bootstrap and JS file migration with backward-compat shims** `est:3h`
  Initialize `window.SemPKM = window.SemPKM || {}` at the top of the earliest-loading custom JS file (api-fetch.js). Then migrate all ~25 JS files: change every `window.X = ...` to `window.SemPKM.X = ...`, and add backward-compat shims `window.X = window.SemPKM.X` at the end of each file's export block. Also update all internal cross-IIFE references within JS files (typeof guards, window.X() calls) to use SemPKM.X. Shims ensure templates and E2E tests continue working during the migration period.
  - Files: `frontend/static/js/api-fetch.js`, `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`, `frontend/static/js/graph.js`, `frontend/static/js/federation.js`, `frontend/static/js/editor.js`, `frontend/static/js/tutorials.js`, `frontend/static/js/canvas.js`, `frontend/static/js/calendar.js`, `frontend/static/js/cleanup.js`, `frontend/static/js/sidebar.js`, `frontend/static/js/theme.js`, `frontend/static/js/settings.js`, `frontend/static/js/named-layouts.js`, `frontend/static/js/markdown-render.js`, `frontend/static/js/column-prefs.js`, `frontend/static/js/bmc.js`, `frontend/static/js/okr.js`, `frontend/static/js/quadrant.js`, `frontend/static/js/decision-matrix.js`, `frontend/static/js/kanban.js`, `frontend/static/js/recurrence-editor.js`, `frontend/static/js/vfs-browser.js`, `frontend/static/js/context-indicator.js`, `frontend/static/js/copilot.js`, `frontend/static/js/sparql-console.js`
  - Verify: Run `for f in frontend/static/js/*.js; do node -c "$(cat $f)" 2>&1 || echo "FAIL: $f"; done` — zero FAIL lines. Run `rg 'window\.\w+ =' frontend/static/js/ | grep -v 'window\.SemPKM' | grep -v '//' | grep -v 'window\.location' | grep -v 'window\.open' | grep -v 'window\.__' | grep -v 'window\.confirm' | grep -v 'window\.matchMedia' | grep -v 'window\.localStorage' | grep -v 'window\.posthog' | grep -v 'window\.htmx' | grep -v 'window\.lucide' | grep -v 'window\.DockviewCore' | grep -v 'window\.Chart' | grep -v 'window\.Yasgui' | grep -v 'window\.driver'` — only backward-compat shim lines remain (to be removed in T03).

- [x] **T02: Migrate template onclick handlers and inline script globals to SemPKM namespace** `est:2h`
  Update all Jinja2 template files that reference custom workspace globals. Three categories: (1) onclick handlers calling bare globals like `openTab(...)` become `SemPKM.openTab(...)`, (2) inline `<script>` blocks that export `window.X = function` become `window.SemPKM.X = function`, (3) typeof guards like `typeof window.X === 'function'` become `typeof SemPKM.X === 'function'`. Skip: debug/admin templates that use page-local functions from app.js (switchTab, executeCommand, etc.), browser builtins (window.location, window.confirm, window.open), and third-party libs (window.htmx, window.lucide). ~20 template files, ~67 onclick handlers, ~30 window.X assignments in inline scripts.
  - Files: `backend/app/templates/browser/object_tab.html`, `backend/app/templates/browser/object_tab_app.html`, `backend/app/templates/browser/object_read.html`, `backend/app/templates/browser/object_embed.html`, `backend/app/templates/browser/workspace.html`, `backend/app/templates/browser/okr_view.html`, `backend/app/templates/browser/bmc_view.html`, `backend/app/templates/browser/cards_view.html`, `backend/app/templates/browser/kanban_view.html`, `backend/app/templates/browser/quadrant_view.html`, `backend/app/templates/browser/decision_matrix_view.html`, `backend/app/templates/browser/table_view.html`, `backend/app/templates/browser/lint_dashboard.html`, `backend/app/templates/browser/settings_page.html`, `backend/app/templates/browser/event_log.html`, `backend/app/templates/browser/ref_tooltip.html`, `backend/app/templates/browser/partials/shared_nav_content.html`, `backend/app/templates/browser/saved_queries_explorer.html`, `backend/app/templates/browser/tag_tree_objects.html`, `backend/app/templates/browser/_llm_settings.html`, `backend/app/templates/browser/workflow_runner.html`, `backend/app/templates/browser/dashboard_builder.html`, `backend/app/templates/browser/workflow_builder.html`, `backend/app/templates/browser/docs_viewer.html`, `backend/app/templates/forms/object_form.html`, `backend/app/templates/forms/_field.html`, `backend/app/templates/guide_article.html`, `backend/app/templates/components/_tabs.html`, `backend/app/templates/components/_sidebar.html`, `backend/app/templates/admin/sparql.html`, `backend/app/templates/admin/models.html`, `backend/app/templates/browser/ontology/abox_instances.html`
  - Verify: Run `rg 'onclick=.*window\.' backend/app/templates/ | grep -v 'window\.(location|confirm|prompt|open|matchMedia|lucide|htmx|posthog|close|print|getComputedStyle|innerWidth|scrollTo|addEventListener|removeEventListener|setTimeout|clearTimeout|setInterval|clearInterval|requestAnimationFrame|getSelection|DOMParser|MutationObserver|IntersectionObserver|ResizeObserver|URL|fetch|history|navigator|performance|CustomEvent|dispatchEvent|Event|localStorage|sessionStorage)' | wc -l` returns 0. Run `rg 'typeof window\.[a-z]\w+ ==' backend/app/templates/ | grep -v 'window\.(renderMarkdownBody|renderMarkdownFromUrl|initRecurrenceEditor|initExdateEditor|initEditor|markDirty|SemPKM)' | wc -l` returns 0 — all typeof guards migrated or already use SemPKM.

- [x] **T03: Update E2E tests and remove backward-compat shims from JS files** `est:1h30m`
  Final cutover: (1) Update all 6 E2E test files to use `window.SemPKM.X` in page.evaluate() calls instead of `window.X`. (2) Remove all backward-compat shim lines (`window.X = window.SemPKM.X`) from the 25 JS files. After this, the only `window.X =` assignments should be `window.SemPKM.*`. (3) Run final verification grep to confirm zero non-SemPKM custom globals remain. The shims are dead code now that templates (T02) and E2E tests (this task) all use the SemPKM namespace.
  - Files: `e2e/helpers/dockview.ts`, `e2e/tests/02-views/graph-interaction.spec.ts`, `e2e/tests/03-navigation/split-panes.spec.ts`, `e2e/tests/03-navigation/named-layouts.spec.ts`, `e2e/tests/50-demo/demo-full-flow.spec.ts`, `e2e/tests/screenshots/capture.spec.ts`, `frontend/static/js/api-fetch.js`, `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`, `frontend/static/js/graph.js`, `frontend/static/js/federation.js`, `frontend/static/js/editor.js`, `frontend/static/js/tutorials.js`, `frontend/static/js/canvas.js`, `frontend/static/js/calendar.js`, `frontend/static/js/cleanup.js`, `frontend/static/js/sidebar.js`, `frontend/static/js/theme.js`, `frontend/static/js/settings.js`, `frontend/static/js/named-layouts.js`, `frontend/static/js/markdown-render.js`, `frontend/static/js/column-prefs.js`, `frontend/static/js/bmc.js`, `frontend/static/js/okr.js`, `frontend/static/js/quadrant.js`, `frontend/static/js/decision-matrix.js`, `frontend/static/js/kanban.js`, `frontend/static/js/recurrence-editor.js`, `frontend/static/js/vfs-browser.js`, `frontend/static/js/context-indicator.js`, `frontend/static/js/copilot.js`, `frontend/static/js/sparql-console.js`
  - Verify: Run `cd e2e && npx tsc --noEmit 2>&1 | tail -5` — zero type errors. Run `rg 'window\.[a-zA-Z_]\w* =' frontend/static/js/ | grep -v 'window\.SemPKM' | grep -v '//' | grep -v 'window\.location' | grep -v 'window\.posthog' | grep -v 'window\.htmx' | grep -v 'window\.lucide' | grep -v 'window\.DockviewCore' | grep -v 'window\.Chart' | grep -v 'window\.Yasgui' | grep -v 'window\.driver' | grep -v 'window\.open(' | grep -v 'window\.confirm(' | grep -v 'window\.matchMedia' | grep -v 'window\.localStorage'` returns zero lines. Run `rg 'window\.[a-z]\w+' e2e/ -g '*.ts' | grep -v 'window\.(SemPKM|location|dispatchEvent|document|addEventListener|removeEventListener|setTimeout|clearTimeout|navigator|localStorage|innerWidth|innerHeight|scrollY|getComputedStyle|history|performance|matchMedia|open|close|confirm)' | wc -l` returns 0.

## Files Likely Touched

- frontend/static/js/api-fetch.js
- frontend/static/js/workspace.js
- frontend/static/js/workspace-layout.js
- frontend/static/js/graph.js
- frontend/static/js/federation.js
- frontend/static/js/editor.js
- frontend/static/js/tutorials.js
- frontend/static/js/canvas.js
- frontend/static/js/calendar.js
- frontend/static/js/cleanup.js
- frontend/static/js/sidebar.js
- frontend/static/js/theme.js
- frontend/static/js/settings.js
- frontend/static/js/named-layouts.js
- frontend/static/js/markdown-render.js
- frontend/static/js/column-prefs.js
- frontend/static/js/bmc.js
- frontend/static/js/okr.js
- frontend/static/js/quadrant.js
- frontend/static/js/decision-matrix.js
- frontend/static/js/kanban.js
- frontend/static/js/recurrence-editor.js
- frontend/static/js/vfs-browser.js
- frontend/static/js/context-indicator.js
- frontend/static/js/copilot.js
- frontend/static/js/sparql-console.js
- backend/app/templates/browser/object_tab.html
- backend/app/templates/browser/object_tab_app.html
- backend/app/templates/browser/object_read.html
- backend/app/templates/browser/object_embed.html
- backend/app/templates/browser/workspace.html
- backend/app/templates/browser/okr_view.html
- backend/app/templates/browser/bmc_view.html
- backend/app/templates/browser/cards_view.html
- backend/app/templates/browser/kanban_view.html
- backend/app/templates/browser/quadrant_view.html
- backend/app/templates/browser/decision_matrix_view.html
- backend/app/templates/browser/table_view.html
- backend/app/templates/browser/lint_dashboard.html
- backend/app/templates/browser/settings_page.html
- backend/app/templates/browser/event_log.html
- backend/app/templates/browser/ref_tooltip.html
- backend/app/templates/browser/partials/shared_nav_content.html
- backend/app/templates/browser/saved_queries_explorer.html
- backend/app/templates/browser/tag_tree_objects.html
- backend/app/templates/browser/_llm_settings.html
- backend/app/templates/browser/workflow_runner.html
- backend/app/templates/browser/dashboard_builder.html
- backend/app/templates/browser/workflow_builder.html
- backend/app/templates/browser/docs_viewer.html
- backend/app/templates/forms/object_form.html
- backend/app/templates/forms/_field.html
- backend/app/templates/guide_article.html
- backend/app/templates/components/_tabs.html
- backend/app/templates/components/_sidebar.html
- backend/app/templates/admin/sparql.html
- backend/app/templates/admin/models.html
- backend/app/templates/browser/ontology/abox_instances.html
- e2e/helpers/dockview.ts
- e2e/tests/02-views/graph-interaction.spec.ts
- e2e/tests/03-navigation/split-panes.spec.ts
- e2e/tests/03-navigation/named-layouts.spec.ts
- e2e/tests/50-demo/demo-full-flow.spec.ts
- e2e/tests/screenshots/capture.spec.ts
