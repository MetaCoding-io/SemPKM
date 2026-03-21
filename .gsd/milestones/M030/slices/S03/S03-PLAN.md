# S03: Lint Filter System (Suppress, Dismiss, Presets)

**Goal:** Users can suppress entire rule types, dismiss individual lint results, save/restore named filter presets, and manage all filter state — with full SQLite persistence and htmx UI.
**Demo:** User sees warnings in the lint panel → dismisses one specific warning (it disappears) → suppresses an entire rule type from the dashboard (all results for that rule disappear) → saves a preset named "Focus Mode" → switches away → applies the preset (same suppressions restore) → opens lint settings and clears all dismissals (previously hidden results reappear).

## Must-Haves

- Three SQLite tables (`lint_suppressions`, `lint_dismissals`, `lint_presets`) via Alembic migration
- `LintFilterService` with full CRUD for suppressions, dismissals, and presets (following PersonaService pattern)
- REST API endpoints for suppress/dismiss/preset CRUD (13 endpoints on `/api/lint/`)
- `LintService.get_results()` and `get_results_for_object()` accept and apply suppression/dismissal filters in Python post-processing
- Lint panel (per-object) has dismiss buttons per result item
- Lint dashboard (global) has suppress controls per result row and preset selector
- Lint settings section for managing suppressions, dismissals, and presets with bulk clear actions
- Requirements covered: LINT-18 (suppress by rule type), LINT-19 (dismiss individual results), LINT-20 (named filter presets)

## Proof Level

- This slice proves: integration (DB + service + API + UI compose into working filter system)
- Real runtime required: yes (Docker stack for UI verification)
- Human/UAT required: no (unit tests + Docker integration cover acceptance criteria)

## Verification

- `cd backend && python -m pytest tests/test_lint_filter_service.py -v` — CRUD unit tests for LintFilterService (create/list/delete suppressions, dismissals, presets; apply preset replaces suppressions)
- `cd backend && python -m pytest tests/test_lint_filtering.py -v` — unit tests for LintService filtering extension (suppressed rules excluded, dismissed pairs excluded, empty filters are no-ops)
- `cd backend && python -m pytest tests/test_lint_filter_api.py -v` — API endpoint tests (suppress/dismiss/preset CRUD returns correct status codes and bodies)
- Docker integration: create objects with lint issues → see warnings → dismiss one → suppress a rule → save preset → apply preset → manage in settings → clear all

## Observability / Diagnostics

- Runtime signals: INFO log on suppress/dismiss/preset CRUD operations (following PersonaService logging pattern)
- Inspection surfaces: `GET /api/lint/suppressions`, `GET /api/lint/dismissals`, `GET /api/lint/presets` — list all active filters for the authenticated user
- Failure visibility: API returns 404 for non-existent filter IDs, 422 for invalid payloads (empty source_shape)
- Redaction constraints: none (rule IRIs and object IRIs are not secrets)

## Integration Closure

- Upstream surfaces consumed: `LintService.get_results()` and `get_results_for_object()` (S01 pipeline fix), `source_shape` field on lint results, `async_session_factory` from `app.db.session`, `PersonaService` pattern from `app.persona`
- New wiring introduced: `lint_filter_service` on `app.state`, `get_lint_filter_service` dependency, filter params threaded from router → LintService
- What remains before the milestone is truly usable end-to-end: S04 (E2E Playwright tests + user guide documentation)

## Tasks

- [x] **T01: SQLAlchemy models, Alembic migration, and LintFilterService CRUD with unit tests** `est:1h30m`
  - Why: Foundation layer — everything else depends on the DB schema and service CRUD. Combining models + migration + service + tests into one task because they are tightly coupled and independently testable without Docker.
  - Files: `backend/app/lint/filter_models.py`, `backend/app/lint/filter_service.py`, `backend/migrations/versions/015_lint_filters.py`, `backend/tests/test_lint_filter_service.py`
  - Do: Create 3 SQLAlchemy ORM models following UserFavorite pattern (UUID PK, user_id FK CASCADE, String(2048) for IRIs, DateTime with server_default, UniqueConstraint). Create LintFilterService following PersonaService pattern (async session_factory, dataclass read models). Create Alembic migration 015. Write unit tests covering all CRUD operations.
  - Verify: `cd backend && python -m pytest tests/test_lint_filter_service.py -v` — all tests pass
  - Done when: 3 tables defined, service has create/list/delete for suppressions and dismissals, create/list/update/delete/apply for presets, 15+ unit tests pass

- [x] **T02: Wire LintFilterService into app + API endpoints for suppress/dismiss/preset CRUD** `est:1h`
  - Why: Exposes filter CRUD via REST API so the UI can call it. Must wire into main.py and dependencies.py before adding endpoints.
  - Files: `backend/app/main.py`, `backend/app/dependencies.py`, `backend/app/lint/router.py`, `backend/app/lint/models.py`, `backend/tests/test_lint_filter_api.py`
  - Do: Register `lint_filter_service` on `app.state` in main.py's startup. Add `get_lint_filter_service` dependency. Add Pydantic request/response models. Add 13 API endpoints to lint/router.py (suppress CRUD, dismiss CRUD, preset CRUD + apply). Write API-level tests.
  - Verify: `cd backend && python -m pytest tests/test_lint_filter_api.py -v` — all tests pass
  - Done when: All 13 endpoints return correct status codes and bodies, service wired into app startup

- [x] **T03: Extend LintService with server-side filtering and wire user's filters into router** `est:1h`
  - Why: Core filtering logic — LintService must exclude suppressed rules and dismissed pairs from results. The router must fetch user's active filters and pass them through.
  - Files: `backend/app/lint/service.py`, `backend/app/lint/router.py`, `backend/app/browser/objects.py`, `backend/app/browser/pages.py`, `backend/tests/test_lint_filtering.py`
  - Do: Add `suppressed_rules: set[str] | None` and `dismissed_pairs: set[tuple[str,str]] | None` params to `get_results()` and `get_results_for_object()`. Apply Python post-filtering after SPARQL returns. For `get_results()`, use over-fetch approach (fetch all, filter, re-paginate). Update router and browser endpoints to fetch user's filters via LintFilterService and pass them through.
  - Verify: `cd backend && python -m pytest tests/test_lint_filtering.py -v` — all tests pass
  - Done when: Suppressed rules excluded from both dashboard and per-object results, dismissed pairs excluded, pagination counts reflect filtered totals

- [x] **T04: Lint panel dismiss buttons and lint dashboard suppress/preset controls** `est:1h30m`
  - Why: User-facing UI for the filter system — dismiss buttons on the per-object lint panel, suppress controls and preset selector on the dashboard sidebar.
  - Files: `backend/app/templates/browser/lint_panel.html`, `backend/app/templates/browser/lint_dashboard.html`, `frontend/static/css/workspace.css`, `frontend/static/js/workspace.js`
  - Do: Add dismiss button (×) next to each warning/info result in lint_panel.html with fetch() call to POST /api/lint/dismiss, then htmx re-fetch. Add "N dismissed" indicator. On lint_dashboard.html sidebar: add suppress button per result row, preset selector dropdown, "N rules suppressed" badge. Use existing htmx patterns for refresh after actions.
  - Verify: Docker stack: create object with lint warnings → dismiss one → warning disappears → suppress a rule type from dashboard → all results for that rule disappear → select/create preset → preset restores
  - Done when: Dismiss buttons work on lint panel, suppress controls work on dashboard, preset selector loads/saves/applies presets

- [x] **T05: Lint settings management section** `est:1h`
  - Why: Users need to manage their filter state — see all active suppressions/dismissals, remove individual items, bulk clear, manage presets.
  - Files: `backend/app/templates/browser/lint_settings.html` (new), `backend/app/browser/pages.py`, `backend/app/lint/router.py`, `frontend/static/css/workspace.css`
  - Do: Create lint settings section accessible from lint dashboard sidebar ("Manage Filters" link). List active suppressions with rule labels and remove buttons. List active dismissals grouped by object with remove buttons. Preset list with rename/delete. "Clear all suppressions" and "Clear all dismissals" bulk actions. All interactions via htmx or fetch() → refresh.
  - Verify: Docker stack: navigate to lint settings → see active suppressions → remove one → see it reappear in dashboard → clear all dismissals → previously dismissed results reappear in lint panel
  - Done when: Settings section shows all filter state with full management controls, bulk clear actions work

## Files Likely Touched

- `backend/app/lint/filter_models.py` (new — SQLAlchemy ORM models)
- `backend/app/lint/filter_service.py` (new — CRUD service)
- `backend/migrations/versions/015_lint_filters.py` (new — Alembic migration)
- `backend/app/lint/models.py` (Pydantic request/response models)
- `backend/app/lint/router.py` (13 new API endpoints)
- `backend/app/lint/service.py` (filtering extension)
- `backend/app/main.py` (service wiring)
- `backend/app/dependencies.py` (dependency getter)
- `backend/app/browser/objects.py` (wire filters into lint panel)
- `backend/app/browser/pages.py` (wire filters into dashboard, add settings route)
- `backend/app/templates/browser/lint_panel.html` (dismiss buttons)
- `backend/app/templates/browser/lint_dashboard.html` (suppress controls, preset selector)
- `backend/app/templates/browser/lint_settings.html` (new — management UI)
- `frontend/static/css/workspace.css` (dismiss/suppress/preset styling)
- `frontend/static/js/workspace.js` (dismiss/suppress JS handlers)
- `backend/tests/test_lint_filter_service.py` (new — CRUD tests)
- `backend/tests/test_lint_filtering.py` (new — filtering tests)
- `backend/tests/test_lint_filter_api.py` (new — API tests)
