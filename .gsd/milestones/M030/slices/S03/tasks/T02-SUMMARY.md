---
id: T02
parent: S03
milestone: M030
provides:
  - 13 REST API endpoints for lint filter CRUD (suppress/dismiss/preset)
  - LintFilterService wired into app.state and FastAPI dependency injection
  - 7 Pydantic request/response models for filter API
key_files:
  - backend/app/lint/router.py
  - backend/app/lint/models.py
  - backend/app/main.py
  - backend/app/dependencies.py
  - backend/tests/test_lint_filter_api.py
key_decisions:
  - POST suppress/dismiss return 201 on success; DELETE returns 200 with {ok: true} or {deleted: count}
  - UUID path params use uuid.UUID type annotation for automatic 422 on invalid format
patterns_established:
  - Filter API endpoints follow existing lint router pattern with get_current_user + get_lint_filter_service dependencies
  - API test pattern uses minimal FastAPI app with dependency_overrides for auth and service injection
observability_surfaces:
  - GET /api/lint/suppressions — list active suppressions for authenticated user
  - GET /api/lint/dismissals — list active dismissals for authenticated user
  - GET /api/lint/presets — list filter presets for authenticated user
  - 404 responses for non-existent filter IDs, 422 for empty IRIs or invalid UUIDs
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Wire LintFilterService into app + API endpoints for suppress/dismiss/preset CRUD

**Added 13 REST API endpoints for lint filter CRUD (suppress/dismiss/preset), wired LintFilterService into app startup and dependency injection, with 18 passing API tests.**

## What Happened

Wired `LintFilterService` into `app.state` in `main.py` following the existing PersonaService pattern. Added `get_lint_filter_service` dependency getter in `dependencies.py`. Added 7 Pydantic models (3 request, 4 response) to `lint/models.py`. Implemented all 13 API endpoints in `lint/router.py`:

- **Suppressions (4):** POST /suppress, DELETE /suppress/{id}, GET /suppressions, DELETE /suppressions
- **Dismissals (4):** POST /dismiss, DELETE /dismiss/{id}, GET /dismissals, DELETE /dismissals
- **Presets (5):** POST /presets, GET /presets, PUT /presets/{id}, DELETE /presets/{id}, POST /presets/{id}/apply

All endpoints require authentication via `get_current_user` and delegate to `LintFilterService` CRUD methods. ValueError from the service layer is caught and returned as HTTP 422. Not-found cases return 404. UUID path params use `uuid.UUID` type annotations for automatic 422 on invalid format.

Wrote 18 API-level tests covering all endpoints including validation edge cases.

## Verification

- All 18 API tests pass (`test_lint_filter_api.py`)
- All 30 service-level tests pass (`test_lint_filter_service.py` from T01)
- `grep "lint_filter_service" backend/app/main.py` confirms wiring line
- `grep "get_lint_filter_service" backend/app/dependencies.py` confirms dependency

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_lint_filter_api.py -v` | 0 | ✅ pass | 2.3s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_lint_filter_service.py -v` | 0 | ✅ pass | 1.6s |
| 3 | `grep "lint_filter_service" backend/app/main.py` | 0 | ✅ pass | <1s |
| 4 | `grep "get_lint_filter_service" backend/app/dependencies.py` | 0 | ✅ pass | <1s |

### Slice-level verification status (intermediate — T02 of 5):

| # | Check | Status |
|---|-------|--------|
| 1 | `test_lint_filter_service.py` — 30 tests | ✅ pass |
| 2 | `test_lint_filtering.py` — filtering tests | ⬜ not yet created (T03) |
| 3 | `test_lint_filter_api.py` — 18 tests | ✅ pass |
| 4 | Docker integration | ⬜ not yet applicable (T04-T05) |

## Diagnostics

- **Inspect active filters:** `GET /api/lint/suppressions`, `GET /api/lint/dismissals`, `GET /api/lint/presets` — authenticated endpoints that list all active filters for the user
- **Error shapes:** 404 with `{"detail": "Suppression not found"}` for missing IDs; 422 with `{"detail": "rule_source_iri must not be empty"}` for validation failures
- **Logging:** All CRUD mutations emit INFO-level logs in `app.lint.filter_service` logger (from T01)

## Deviations

None. All 13 endpoints match the plan specification exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/main.py` — wired `LintFilterService` on `app.state` during startup
- `backend/app/dependencies.py` — added `get_lint_filter_service` dependency getter
- `backend/app/lint/models.py` — added 7 Pydantic request/response models for filter API
- `backend/app/lint/router.py` — added 13 REST API endpoints for suppress/dismiss/preset CRUD
- `backend/tests/test_lint_filter_api.py` — 18 API-level tests
- `.gsd/milestones/M030/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section
