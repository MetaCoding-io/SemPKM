---
estimated_steps: 6
estimated_files: 5
---

# T02: Wire LintFilterService into app + API endpoints for suppress/dismiss/preset CRUD

**Slice:** S03 — Lint Filter System (Suppress, Dismiss, Presets)
**Milestone:** M030

## Description

Register `LintFilterService` on `app.state` during startup, add a FastAPI dependency getter, and create 13 REST API endpoints for filter CRUD operations. All endpoints require authentication via `get_current_user`.

## Steps

1. Wire service into `backend/app/main.py`:
   - Import `LintFilterService` from `app.lint.filter_service`
   - In the startup section near persona_service (~line 343): `app.state.lint_filter_service = LintFilterService(async_session_factory)`

2. Add dependency in `backend/app/dependencies.py`:
   - Add `get_lint_filter_service(request: Request) -> LintFilterService` following `get_lint_service` pattern
   - Returns `request.app.state.lint_filter_service`

3. Add Pydantic request/response models in `backend/app/lint/models.py`:
   - `SuppressRequest(BaseModel)`: `rule_source_iri: str`
   - `DismissRequest(BaseModel)`: `object_iri: str`, `rule_source_iri: str`
   - `PresetCreateRequest(BaseModel)`: `name: str`, `suppressed_rules: list[str]`
   - `PresetUpdateRequest(BaseModel)`: `name: str | None = None`, `suppressed_rules: list[str] | None = None`
   - `SuppressionResponse(BaseModel)`: `id: str`, `rule_source_iri: str`, `created_at: str`
   - `DismissalResponse(BaseModel)`: `id: str`, `object_iri: str`, `rule_source_iri: str`, `created_at: str`
   - `PresetResponse(BaseModel)`: `id: str`, `name: str`, `suppressed_rules: list[str]`, `created_at: str`, `updated_at: str`

4. Add 13 endpoints to `backend/app/lint/router.py`:
   - `POST /api/lint/suppress` — body: SuppressRequest → create suppression, return SuppressionResponse (reject empty rule_source_iri with 422)
   - `DELETE /api/lint/suppress/{id}` — remove one suppression, 404 if not found
   - `GET /api/lint/suppressions` — list active suppressions for user
   - `DELETE /api/lint/suppressions` — clear all suppressions, return `{"deleted": count}`
   - `POST /api/lint/dismiss` — body: DismissRequest → create dismissal
   - `DELETE /api/lint/dismiss/{id}` — remove one dismissal
   - `GET /api/lint/dismissals` — list active dismissals for user
   - `DELETE /api/lint/dismissals` — clear all dismissals
   - `POST /api/lint/presets` — body: PresetCreateRequest → create preset
   - `GET /api/lint/presets` — list presets for user
   - `PUT /api/lint/presets/{id}` — body: PresetUpdateRequest → update preset
   - `DELETE /api/lint/presets/{id}` — delete preset
   - `POST /api/lint/presets/{id}/apply` — apply preset (replace suppressions with preset's list)
   - All endpoints require `user: User = Depends(get_current_user)` and `filter_service: LintFilterService = Depends(get_lint_filter_service)`
   - Use `uuid.UUID` type annotation for path params to get automatic 422 on invalid UUIDs

5. Write `backend/tests/test_lint_filter_api.py`:
   - Test suppress CRUD: POST creates, GET lists, DELETE removes, DELETE all clears
   - Test dismiss CRUD: POST creates, GET lists, DELETE removes
   - Test preset CRUD: POST creates, GET lists, PUT updates, DELETE removes, POST apply
   - Test validation: empty rule_source_iri → 422, non-existent ID → 404
   - Use the existing backend test patterns (mock service or lightweight fixtures)
   - Target: 12+ tests

## Must-Haves

- [ ] LintFilterService wired into app.state in main.py
- [ ] get_lint_filter_service dependency in dependencies.py
- [ ] Pydantic request/response models added to lint/models.py
- [ ] 13 API endpoints in lint/router.py returning correct status codes
- [ ] 12+ API-level tests passing

## Verification

- `cd backend && python -m pytest tests/test_lint_filter_api.py -v` — all tests pass
- `grep "lint_filter_service" backend/app/main.py` returns the wiring line
- `grep "get_lint_filter_service" backend/app/dependencies.py` returns the dependency

## Inputs

- `backend/app/lint/filter_service.py` — T01's LintFilterService with all CRUD methods
- `backend/app/lint/filter_models.py` — T01's ORM models
- `backend/app/main.py` — existing service wiring pattern (persona_service at ~line 343)
- `backend/app/dependencies.py` — existing dependency pattern (get_lint_service)
- `backend/app/lint/router.py` — existing lint API router to extend

## Expected Output

- `backend/app/main.py` — lint_filter_service wired on app.state
- `backend/app/dependencies.py` — get_lint_filter_service dependency
- `backend/app/lint/models.py` — 7 new Pydantic models for request/response
- `backend/app/lint/router.py` — 13 new API endpoints
- `backend/tests/test_lint_filter_api.py` — 12+ passing tests

## Observability Impact

- **New inspection surfaces:** 3 GET endpoints (`/api/lint/suppressions`, `/api/lint/dismissals`, `/api/lint/presets`) expose all active filter state per authenticated user — useful for debugging why results are hidden.
- **Error visibility:** 404 for non-existent filter IDs, 422 for empty IRIs or invalid UUID path params — all returned as JSON with `detail` field.
- **Logging:** All mutations flow through LintFilterService (T01) which emits INFO-level logs on create/delete/clear/apply operations in the `app.lint.filter_service` logger.
- **How to inspect:** `curl -H "Cookie: session=..." http://localhost:8000/api/lint/suppressions` returns the full suppression list for the authenticated user. Same pattern for `/dismissals` and `/presets`.
