---
estimated_steps: 13
estimated_files: 32
skills_used: []
---

# T03: Update E2E tests and remove backward-compat shims from JS files

Final cutover: update E2E tests to use the SemPKM namespace and remove all backward-compat shims from JS files.

**Part 1 — E2E test updates (~6 files, ~10 references):**
Update `page.evaluate()` calls in E2E test files:
- `e2e/helpers/dockview.ts`: `window._dockview` → `window.SemPKM._dockview`, `window.openGenericViewTab` → `window.SemPKM.openGenericViewTab`, `window.openTab` → `window.SemPKM.openTab`
- `e2e/tests/02-views/graph-interaction.spec.ts`: `window._sempkmGraph` → `window.SemPKM._sempkmGraph` (used in dispatchEvent)
- `e2e/tests/03-navigation/split-panes.spec.ts`: `window._dockview` → `window.SemPKM._dockview`
- `e2e/tests/03-navigation/named-layouts.spec.ts`: `window.SemPKMLayouts` — leave as-is (already namespaced differently)
- `e2e/tests/50-demo/demo-full-flow.spec.ts`: `window.startDemoTour` → `window.SemPKM.startDemoTour`
- `e2e/tests/screenshots/capture.spec.ts`: `window.openDashboardTab` → `window.SemPKM.openDashboardTab`

**Part 2 — Remove backward-compat shims from all ~25 JS files:**
Delete all lines of the form `window.X = window.SemPKM.X;` or `window.X = SemPKM.X;` added in T01. After this, the only `window.X =` assignments in frontend/static/js/ should be `window.SemPKM.*` exports.

**Part 3 — Final verification:**
Run comprehensive grep checks to confirm zero non-SemPKM custom globals remain in both JS files and templates.

## Inputs

- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/graph.js`
- `e2e/helpers/dockview.ts`
- `e2e/tests/02-views/graph-interaction.spec.ts`
- `e2e/tests/03-navigation/split-panes.spec.ts`
- `e2e/tests/03-navigation/named-layouts.spec.ts`
- `e2e/tests/50-demo/demo-full-flow.spec.ts`
- `e2e/tests/screenshots/capture.spec.ts`

## Expected Output

- `e2e/helpers/dockview.ts`
- `e2e/tests/02-views/graph-interaction.spec.ts`
- `e2e/tests/03-navigation/split-panes.spec.ts`
- `e2e/tests/03-navigation/named-layouts.spec.ts`
- `e2e/tests/50-demo/demo-full-flow.spec.ts`
- `e2e/tests/screenshots/capture.spec.ts`
- `frontend/static/js/api-fetch.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/federation.js`
- `frontend/static/js/editor.js`
- `frontend/static/js/tutorials.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/calendar.js`
- `frontend/static/js/cleanup.js`
- `frontend/static/js/sidebar.js`
- `frontend/static/js/theme.js`
- `frontend/static/js/settings.js`
- `frontend/static/js/named-layouts.js`
- `frontend/static/js/markdown-render.js`
- `frontend/static/js/column-prefs.js`
- `frontend/static/js/bmc.js`
- `frontend/static/js/okr.js`
- `frontend/static/js/quadrant.js`
- `frontend/static/js/decision-matrix.js`
- `frontend/static/js/kanban.js`
- `frontend/static/js/recurrence-editor.js`
- `frontend/static/js/vfs-browser.js`
- `frontend/static/js/context-indicator.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/sparql-console.js`

## Verification

1. E2E type-check: `cd e2e && npx tsc --noEmit 2>&1 | tail -5` — zero type errors.
2. All JS files syntax-valid: `for f in frontend/static/js/*.js; do node -c "$(cat "$f")" 2>&1 || echo "FAIL: $f"; done` — zero FAIL lines.
3. Zero non-SemPKM custom window globals: `rg 'window\.[a-zA-Z_]\w* =' frontend/static/js/ | grep -v 'window\.SemPKM' | grep -v '//' | grep -v 'window\.(location|posthog|htmx|lucide|DockviewCore|Chart|Yasgui|driver|open\(|confirm\(|matchMedia|localStorage|close\()' | wc -l` returns 0.
4. Zero bare window globals in E2E: `rg 'window\.\w+' e2e/ -g '*.ts' | grep -v 'window\.(SemPKM|location|dispatchEvent|document|addEventListener|removeEventListener|setTimeout|clearTimeout|navigator|localStorage|innerWidth|innerHeight|scrollY|getComputedStyle|history|performance|matchMedia|open|close|confirm|__playwright)' | grep -v '//' | grep -v 'node_modules' | wc -l` returns 0.
5. No backward-compat shim lines remain: `rg '= window\.SemPKM\.' frontend/static/js/ | grep -v '//' | wc -l` returns 0 (or only the namespace init line).
