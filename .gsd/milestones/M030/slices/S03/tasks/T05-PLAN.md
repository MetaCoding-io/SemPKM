---
estimated_steps: 6
estimated_files: 5
---

# T05: Lint settings management section

**Slice:** S03 — Lint Filter System (Suppress, Dismiss, Presets)
**Milestone:** M030

## Description

Create a lint settings section where users can view and manage all their active suppressions, dismissals, and presets. Accessible from a "Manage Filters" link in the lint dashboard sidebar. Provides individual remove actions and bulk clear for each filter type.

This follows the htmx partial pattern used throughout the browser — the settings section is an htmx-rendered partial that can replace its own container on updates.

## Steps

1. Create `backend/app/templates/browser/lint_settings.html`:
   - Overall layout: three collapsible sections (Suppressions, Dismissals, Presets) using `<details>` elements
   - **Suppressions section**: list each active suppression showing `rule_source_iri` (extract local name for display), created_at timestamp, and a "Remove" button. "Clear All Suppressions" button at bottom. Show count in section header: "Suppressions (N)"
   - **Dismissals section**: list dismissals grouped by object_iri showing object label + rule_source_iri, with per-item "Remove" button. "Clear All Dismissals" button at bottom. Show count in header.
   - **Presets section**: list presets with name, rule count, created_at. Each has "Rename" (inline edit), "Apply", and "Delete" buttons. "New Preset" button at top.
   - All actions use `fetch()` calls to the T02 API endpoints, then refresh the settings section via htmx
   - Template accepts: `suppressions` (list), `dismissals` (list), `presets` (list)
   - For rule label display: use a local name extraction filter (last segment after # or / in the IRI), same pattern as `_local_name()` in lint/service.py. Add a Jinja2 filter or just pass pre-resolved labels.

2. Add browser route in `backend/app/browser/pages.py`:
   - `GET /browser/lint-settings` — fetches suppressions, dismissals, and presets for current user via LintFilterService, renders lint_settings.html
   - Resolve labels for rule IRIs and object IRIs using LabelService (batch resolve for display)
   - Requires `get_current_user` + `get_lint_filter_service` + label service dependencies

3. Add "Manage Filters" link in `backend/app/templates/browser/lint_dashboard.html`:
   - Add a link/button in the sidebar below the preset selector: `<a href="#" hx-get="/browser/lint-settings" hx-target="#lint-dashboard-container" hx-swap="innerHTML">Manage Filters</a>`
   - This replaces the dashboard content with the settings section inline
   - Add a "← Back to Dashboard" link at the top of lint_settings.html that does `hx-get="/browser/lint-dashboard" hx-target="#lint-dashboard-container" hx-swap="innerHTML"`

4. Add JS handlers for settings actions in `frontend/static/js/workspace.js` (or inline in template):
   - `removeSuppression(id)`: DELETE `/api/lint/suppress/{id}` → refresh settings
   - `clearAllSuppressions()`: DELETE `/api/lint/suppressions` → refresh settings
   - `removeDismissal(id)`: DELETE `/api/lint/dismiss/{id}` → refresh settings
   - `clearAllDismissals()`: DELETE `/api/lint/dismissals` → refresh settings
   - `deletePreset(id)`: DELETE `/api/lint/presets/{id}` → refresh settings
   - `renamePreset(id)`: prompt for new name, PUT `/api/lint/presets/{id}` → refresh settings
   - All refresh via `htmx.ajax('GET', '/browser/lint-settings', {target: '#lint-dashboard-container', swap: 'innerHTML'})`

5. Add CSS for settings section in `frontend/static/css/workspace.css`:
   - `.lint-settings`: padding, max-width
   - `.lint-settings-section`: collapsible section with header count badge
   - `.lint-settings-item`: flex row with label + remove button
   - `.lint-settings-empty`: muted text for empty lists
   - `.lint-settings-clear-btn`: destructive action button (red/muted)
   - `.lint-settings-back`: back link styling

6. Docker verification:
   - Navigate to lint dashboard → click "Manage Filters" → see settings section
   - With active suppressions: see them listed with "Remove" buttons → click Remove → item disappears
   - Click "Clear All Suppressions" → all suppressions removed → previously hidden lint results reappear in dashboard
   - Dismissals: similar — remove individual, clear all, verify results reappear in lint panel
   - Presets: rename works, delete works, "← Back to Dashboard" returns to normal dashboard view

## Must-Haves

- [ ] lint_settings.html template with three management sections
- [ ] GET /browser/lint-settings route with label resolution
- [ ] "Manage Filters" link in dashboard sidebar
- [ ] Individual remove and bulk clear actions for suppressions and dismissals
- [ ] Preset management (rename, delete) in settings
- [ ] Back navigation to dashboard

## Verification

- Docker stack: dashboard → "Manage Filters" → see settings with active suppressions/dismissals → remove one → verify reappears in dashboard → clear all → verify all reappear → back to dashboard
- `grep "lint-settings" backend/app/browser/pages.py` — route exists
- `ls backend/app/templates/browser/lint_settings.html` — template exists

## Observability Impact

- **New route:** `GET /browser/lint-settings` — renders lint filter management UI. Served as htmx partial for dashboard container swap.
- **Inspection:** Active suppressions/dismissals/presets listed with IDs and timestamps. All management actions (remove, clear, rename, delete) call existing T02 API endpoints — no new API routes.
- **Failure visibility:** JS console errors prefixed with function names (`removeSuppression error:`, `clearAllSuppressions error:`). Network errors visible in DevTools.
- **Diagnostics:** Count badges in section headers (`Suppressions (N)`, `Dismissals (N)`, `Presets (N)`) provide at-a-glance filter state.

## Inputs

- `backend/app/lint/filter_service.py` — T01's LintFilterService for list/delete/clear operations
- `backend/app/lint/router.py` — T02's API endpoints that the JS handlers call
- `backend/app/templates/browser/lint_dashboard.html` — T04's dashboard with sidebar for "Manage Filters" link placement
- `backend/app/browser/pages.py` — existing lint_dashboard route pattern

## Expected Output

- `backend/app/templates/browser/lint_settings.html` — new management template
- `backend/app/browser/pages.py` — lint_settings route added
- `backend/app/templates/browser/lint_dashboard.html` — "Manage Filters" link added
- `frontend/static/js/workspace.js` — settings action handlers
- `frontend/static/css/workspace.css` — settings section styling
