# T01: 38-global-lint-dashboard-ui 01

**Slice:** S38 — **Milestone:** M001

## Description

Build the global lint dashboard backend endpoint, HTML template, and workspace tab registration.

Purpose: Users need a single view showing all SHACL validation results across every object, with filtering by severity/type/keyword and sorting capabilities. This plan creates the server-rendered htmx partial and its backend endpoint, following the inference panel pattern.

Output: Working lint dashboard tab in the bottom panel with filter controls, sortable result table, pagination, and summary bar. No JS wiring for SSE or command palette yet (Plan 02).

## Must-Haves

- [ ] "User can see a filterable table of all lint results across all objects"
- [ ] "User can filter results by severity level (Violation, Warning, Info)"
- [ ] "User can filter results by object type using the Mental Model type registry"
- [ ] "User can search lint results by keyword across message, path, and object label"
- [ ] "User can sort results by severity, object name, or property path"
- [ ] "Results paginate for large result sets (50 per page)"

## Files

- `backend/app/browser/router.py`
- `backend/app/lint/router.py`
- `backend/app/lint/service.py`
- `backend/app/templates/browser/lint_dashboard.html`
- `backend/app/templates/browser/workspace.html`
- `frontend/static/css/workspace.css`
