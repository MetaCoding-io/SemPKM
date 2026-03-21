---
id: S03
parent: M030
milestone: M030
provides:
  - Three SQLite tables (lint_suppressions, lint_dismissals, lint_presets) via Alembic migration 015
  - LintFilterService with full async CRUD for suppressions, dismissals, and presets
  - 13 REST API endpoints on /api/lint/ for filter CRUD (suppress/dismiss/preset)
  - Server-side Python post-filtering in LintService — suppressed rules and dismissed pairs excluded from results
  - Lint panel dismiss buttons (×) on warning/info results with htmx refresh
  - Lint dashboard suppress buttons, preset selector, and "Manage Filters" link
  - Lint settings management section with remove/clear/rename/delete actions
requires:
  - slice: S01
    provides: Validation pipeline producing real lint results with source_shape identifiers
affects:
  - S04
key_files:
  - backend/app/lint/filter_models.py
  - backend/app/lint/filter_service.py
  - backend/app/lint/service.py
  - backend/app/lint/router.py
  - backend/app/lint/models.py
  - backend/app/main.py
  - backend/app/dependencies.py
  - backend/app/browser/pages.py
  - backend/app/browser/objects.py
  - backend/app/templates/browser/lint_panel.html
  - backend/app/templates/browser/lint_dashboard.html
  - backend/app/templates/browser/lint_settings.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/migrations/versions/015_lint_filters.py
  - backend/tests/test_lint_filter_service.py
  - backend/tests/test_lint_filter_api.py
  - backend/tests/test_lint_filtering.py
key_decisions:
  - D279 — Lint filter storage in SQLite with server-side Python filtering (suppressions/dismissals are user preferences, not graph data)
  - D280 — Additive preset model (presets store what to suppress, starting from "show all")
  - D283 — Violations not dismissable (structural issues must be resolved; only warnings/infos get dismiss)
  - Duplicate suppressions/dismissals idempotent (return existing); duplicate preset names raise ValueError
  - Over-fetch approach for filtered pagination (fetch all, filter in Python, re-slice)
  - source_shape always populated on LintResultItem from SPARQL (not just detail mode) for filter matching
patterns_established:
  - LintFilterService follows PersonaService session_factory pattern (async session factory, dataclass read models)
  - Filter ORM models follow UserFavorite pattern (UUID PK, user_id FK CASCADE, UniqueConstraint)
  - Over-fetch re-pagination pattern — when filters active, skip OFFSET/LIMIT, fetch all results, filter in Python, slice for requested page
  - Lint filter JS handlers use fetch() + htmx.ajax() refresh pattern (same as favorites, dashboards)
  - Destructive bulk actions use confirm() dialog before executing
observability_surfaces:
  - GET /api/lint/suppressions — list active suppressions for authenticated user
  - GET /api/lint/dismissals — list active dismissals for authenticated user
  - GET /api/lint/presets — list presets for authenticated user
  - dismissed_count in lint panel template context
  - suppressed_count and active_presets in lint dashboard template context
  - INFO logs on all CRUD mutations in app.lint.filter_service logger
  - Settings section shows count badges in section headers
drill_down_paths:
  - .gsd/milestones/M030/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M030/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M030/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M030/slices/S03/tasks/T04-SUMMARY.md
  - .gsd/milestones/M030/slices/S03/tasks/T05-SUMMARY.md
duration: 1h47m
verification_result: passed
completed_at: 2026-03-21
---

# S03: Lint Filter System (Suppress, Dismiss, Presets)

**Full lint filter CRUD with SQLite persistence — users can suppress rule types, dismiss individual results, save/restore named presets, and manage all filter state from a settings UI. 59 passing tests across 3 test files.**

## What Happened

Built the complete lint filter system in 5 tasks, layered bottom-up:

**T01 — Persistence layer.** Three SQLAlchemy ORM models (`LintSuppression`, `LintDismissal`, `LintPreset`) following the `UserFavorite` pattern, Alembic migration 015, and `LintFilterService` with 15 async CRUD methods following the `PersonaService` pattern. Duplicate suppressions/dismissals are idempotent; duplicate preset names raise `ValueError`. `apply_preset` atomically replaces all user suppressions. 30 unit tests.

**T02 — API wiring.** Wired `LintFilterService` into `app.state` during startup and added `get_lint_filter_service` dependency. 7 Pydantic request/response models. 13 REST API endpoints: suppressions (POST/DELETE/GET/DELETE-all), dismissals (POST/DELETE/GET/DELETE-all), presets (POST/GET/PUT/DELETE/apply). 18 API tests.

**T03 — Server-side filtering.** Extended `LintService.get_results()` and `get_results_for_object()` with `suppressed_rules` and `dismissed_pairs` parameters. When filters are active, the over-fetch approach runs a single SPARQL query (no OFFSET/LIMIT, no count query), filters in Python, then re-paginates. Results with empty `source_shape` are never excluded (they have no identifiable rule). Wired user filters into all three consumer routes (API, browser lint panel, lint dashboard). 11 filtering tests.

**T04 — UI controls.** Dismiss buttons (×) on lint panel warning/info results (violations intentionally excluded per D283). Suppress buttons (eye-off) on lint dashboard result rows with hover-reveal. Preset selector dropdown in dashboard sidebar with "No preset" clear option and "Save Current" button. "N dismissed" indicator and "N rules suppressed" badge. All JS handlers use the established `fetch() + htmx.ajax()` refresh pattern.

**T05 — Settings management.** Created `lint_settings.html` with three collapsible `<details>` sections: Suppressions (per-rule remove + clear all), Dismissals (per-object grouping + remove + clear all), Presets (apply/rename/delete). "Manage Filters" link in dashboard sidebar navigates to settings via htmx swap. "← Back to Dashboard" returns. Rule labels use `_local_name()` for clean display since SHACL shapes lack `rdfs:label` in the store.

## Verification

All 59 unit tests pass across 3 test files:
- `test_lint_filter_service.py` — 30 tests: CRUD for suppressions/dismissals/presets, validation, duplicate handling, preset application, user isolation, filter aggregation
- `test_lint_filter_api.py` — 18 tests: all 13 endpoints including validation errors, 404s, UUID format checking
- `test_lint_filtering.py` — 11 tests: suppression exclusion, dismissal exclusion, empty filter no-ops, empty source_shape protection, over-fetch pagination (both pages), SPARQL pagination without filters, count query skipping

Docker integration verified:
- Dismiss warning → disappears from lint panel, "1 dismissed" indicator appears
- Suppress rule from dashboard → all results for that rule disappear, "1 rule suppressed" badge
- Save preset → appears in dropdown, apply preset → restores suppressions
- "No preset" → clears all suppressions
- Manage Filters → settings section with all sections rendering correctly
- Remove suppression → count updates, empty state message shows
- Back to Dashboard → returns to normal view

## Requirements Advanced

- LINT-18 (suppress by rule type) — fully implemented: API endpoint, dashboard UI button, server-side filtering, settings management
- LINT-19 (dismiss individual results) — fully implemented: API endpoint, lint panel dismiss button, server-side filtering, settings management
- LINT-20 (named filter presets) — fully implemented: API CRUD, dashboard preset selector, save/apply/rename/delete, settings management

## Requirements Validated

- LINT-18 — 59 unit tests proving CRUD + filtering + API + UI integration, Docker verification of suppress → disappear → preset save/apply cycle
- LINT-19 — 59 unit tests proving dismiss CRUD + filtering, Docker verification of dismiss → "N dismissed" indicator → settings remove → reappear
- LINT-20 — 59 unit tests proving preset CRUD + apply (atomic replacement), Docker verification of save → apply → rename → delete cycle

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- `source_shape` is now always populated on `LintResultItem` from SPARQL (previously only in `detail=True` mode). This backward-compatible enhancement was needed for both the filtering logic and the dismiss/suppress buttons to function.
- Rule labels in settings use `_local_name()` instead of `LabelService.resolve()` because SHACL shape IRIs lack `rdfs:label` — LabelService returns verbose QNames (e.g., `sempkm:model:basic-pkm:EmptyBodyValidationShape`) while `_local_name()` returns clean names (e.g., `EmptyBodyValidationShape`).

## Known Limitations

- **Frontend build pipeline required:** The JS/CSS changes require `cd frontend && npm ci && node build.js` to produce hashed assets, then a Docker frontend rebuild. Volume-mounted raw files work in dev mode but production serves built assets from the `frontend_assets` volume.
- **No E2E Playwright tests yet** — covered by S04.
- **LINT-08 through LINT-20 requirements not formally added to REQUIREMENTS.md** — they're referenced in the roadmap but weren't created during S01/S02 execution. The validation evidence exists in task summaries.

## Follow-ups

- S04 will add E2E Playwright tests covering the full lint filter workflow and user guide documentation.
- LINT-08 through LINT-20 requirements should be formally added to REQUIREMENTS.md during S04 or milestone completion.

## Files Created/Modified

- `backend/app/lint/filter_models.py` — 3 SQLAlchemy ORM models (LintSuppression, LintDismissal, LintPreset)
- `backend/app/lint/filter_service.py` — LintFilterService with 15 async CRUD methods + 3 dataclass read models
- `backend/migrations/versions/015_lint_filters.py` — Alembic migration 015 (create 3 tables)
- `backend/app/lint/models.py` — 7 Pydantic request/response models for filter API
- `backend/app/lint/router.py` — 13 REST API endpoints for suppress/dismiss/preset CRUD + filter wiring
- `backend/app/lint/service.py` — Python post-filtering with over-fetch re-pagination
- `backend/app/main.py` — LintFilterService wired into app.state
- `backend/app/dependencies.py` — get_lint_filter_service dependency getter
- `backend/app/browser/pages.py` — lint dashboard filter wiring + lint settings route
- `backend/app/browser/objects.py` — lint panel filter wiring
- `backend/app/templates/browser/lint_panel.html` — dismiss buttons + dismissed count indicator
- `backend/app/templates/browser/lint_dashboard.html` — suppress buttons + preset selector + manage filters link
- `backend/app/templates/browser/lint_settings.html` — settings management section (suppressions/dismissals/presets)
- `frontend/static/js/workspace.js` — 10 lint filter JS handler functions
- `frontend/static/css/workspace.css` — lint filter UI styling (~230 lines)
- `backend/tests/test_lint_filter_service.py` — 30 CRUD unit tests
- `backend/tests/test_lint_filter_api.py` — 18 API endpoint tests
- `backend/tests/test_lint_filtering.py` — 11 server-side filtering tests

## Forward Intelligence

### What the next slice should know
- The 13 API endpoints at `/api/lint/` are the stable interface for all filter operations — E2E tests should exercise these directly rather than trying to test internal service methods.
- The lint dashboard is the hub — suppressions, preset selector, and "Manage Filters" link are all in the dashboard sidebar.
- Dismiss buttons only appear on warnings/infos (not violations) in the per-object lint panel.
- The Docker stack must be running with worktree code synced to the main tree for the volume mounts to pick up changes (see KNOWLEDGE.md).

### What's fragile
- The `_local_name()` approach for rule labels is a pragmatic workaround. If SHACL shapes ever get `rdfs:label` annotations, `LabelService` should be preferred instead.
- The over-fetch approach for filtered pagination loads ALL results when filters are active. For users with thousands of lint results, this could be slow. Acceptable for current scale (~50-200 results).

### Authoritative diagnostics
- `GET /api/lint/suppressions` + `GET /api/lint/dismissals` — show exactly what's being filtered for the current user.
- `GET /api/lint/results?page=1` — compare `total` before and after adding suppressions to verify filtering is working.
- Browser DevTools Network tab — all filter actions produce observable `fetch()` calls to `/api/lint/*` endpoints.

### What assumptions changed
- `source_shape` was originally only populated in detail mode — changed to always populate it since both filtering and UI buttons depend on it. This is backward compatible.
