---
estimated_steps: 2
estimated_files: 26
skills_used: []
---

# T01: Namespace bootstrap and JS file migration with backward-compat shims

Initialize the `window.SemPKM` namespace object and migrate all ~25 custom JS files from `window.X = ...` exports to `window.SemPKM.X = ...`. Add backward-compatible shims (`window.X = window.SemPKM.X`) at the end of each file so templates and E2E tests continue to work during the migration period (T02/T03 will update them, T03 will remove shims).

This is the foundational task — every other task in S03 depends on the namespace object existing and all JS files exporting into it.

## Inputs

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

## Expected Output

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

1. Syntax check all JS files: `for f in frontend/static/js/*.js; do node -c "$(cat "$f")" 2>&1 || echo "FAIL: $f"; done` — zero FAIL lines.
2. Namespace bootstrap exists: `rg 'window\.SemPKM = window\.SemPKM' frontend/static/js/api-fetch.js` returns a match.
3. Custom globals audit: `rg 'window\.\w+ =' frontend/static/js/ | grep -v 'window\.SemPKM' | grep -v '//' | grep -v 'window\.location' | grep -v 'window\.posthog' | grep -v 'window\.htmx' | grep -v 'window\.lucide' | grep -v 'window\.DockviewCore' | grep -v 'window\.Chart' | grep -v 'window\.Yasgui' | grep -v 'window\.driver' | grep -v 'window\.open(' | grep -v 'window\.confirm(' | grep -v 'window\.matchMedia' | grep -v 'window\.localStorage'` — only backward-compat shim lines of the form `window.X = window.SemPKM.X` or `window.X = SemPKM.X` remain.
4. Internal references updated: `rg 'typeof window\.[a-z]\w+ ===' frontend/static/js/ | grep -v 'typeof window\.SemPKM' | grep -v 'typeof SemPKM' | grep -v '//'` — returns zero non-comment lines (all typeof guards updated).
