# S38: Global Lint Dashboard Ui

**Goal:** Build the global lint dashboard backend endpoint, HTML template, and workspace tab registration.
**Demo:** Build the global lint dashboard backend endpoint, HTML template, and workspace tab registration.

## Must-Haves


## Tasks

- [x] **T01: 38-global-lint-dashboard-ui 01** `est:5min`
  - Build the global lint dashboard backend endpoint, HTML template, and workspace tab registration.

Purpose: Users need a single view showing all SHACL validation results across every object, with filtering by severity/type/keyword and sorting capabilities. This plan creates the server-rendered htmx partial and its backend endpoint, following the inference panel pattern.

Output: Working lint dashboard tab in the bottom panel with filter controls, sortable result table, pagination, and summary bar. No JS wiring for SSE or command palette yet (Plan 02).
- [x] **T02: 38-global-lint-dashboard-ui 02** `est:2min`
  - Wire up SSE auto-refresh, health badge, and Command Palette for the lint dashboard.

Purpose: The dashboard from Plan 01 is static on load. This plan adds real-time auto-refresh via SSE events, a persistent health badge on the LINT tab showing violation counts (LINT-03), and Command Palette access.

Output: Live-updating lint dashboard with health badge visible on the LINT tab at all times, Command Palette integration.

## Files Likely Touched

- `backend/app/browser/router.py`
- `backend/app/lint/router.py`
- `backend/app/lint/service.py`
- `backend/app/templates/browser/lint_dashboard.html`
- `backend/app/templates/browser/workspace.html`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
