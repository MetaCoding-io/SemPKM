---
estimated_steps: 4
estimated_files: 3
---

# T02: Add refresh-artifacts admin endpoint and UI buttons

**Slice:** S05 — Model Schema Refresh
**Milestone:** M005

## Description

Wire `ModelService.refresh_artifacts()` into the admin router as a POST endpoint. Add "Refresh" buttons to both the model list table and model detail header. Integrate with ops log (fire-and-forget per D082) and ViewSpec cache invalidation.

## Steps

1. Add `POST /admin/models/{model_id}/refresh-artifacts` route to `backend/app/admin/router.py`:
   - Require `owner` role via `Depends(require_role("owner"))`
   - Inject `ModelService`, `OperationsLogService` via existing DI
   - Call `model_service.refresh_artifacts(model_id)`
   - On success: call `request.app.state.view_spec_service.invalidate_cache()`, log `model.refresh` to ops log (try/except, D082), fetch models list, return model table partial with success message
   - On failure: log failed `model.refresh` to ops log, return model table partial with error message
   - Follow exact pattern from `admin_models_install()` and `admin_models_remove()`
2. Add "Refresh" button to model list table in `backend/app/templates/admin/models.html`:
   - Place between "Inference" and "Remove" buttons
   - Use `hx-post="/admin/models/{{ model.model_id }}/refresh-artifacts"` with `hx-target="#model-table"` and `hx-swap="outerHTML"`
   - Add `hx-confirm="Refresh artifacts for {{ model.name }}? This will reload shapes, views, ontology, and rules from disk."` for safety
   - Style as `btn btn-info btn-sm` (distinct from warning Inference and danger Remove)
3. Add "Refresh" button to model detail header in `backend/app/templates/admin/model_detail.html`:
   - Place after the version pill in `.model-title-row`
   - Same htmx attributes but target `#app-content` with `innerHTML` swap to refresh the full detail view
   - Use `hx-confirm` for safety
4. Verify in running Docker stack: navigate to admin models, click Refresh, confirm success message, check ops log

## Must-Haves

- [ ] POST endpoint at `/admin/models/{model_id}/refresh-artifacts` requiring owner role
- [ ] ViewSpec cache invalidated on success
- [ ] Ops log entry created for both success and failure (fire-and-forget)
- [ ] "Refresh" button visible on model list table
- [ ] "Refresh" button visible on model detail header
- [ ] Both buttons use hx-confirm for safety

## Verification

- Start Docker stack (`docker compose up -d`)
- Navigate to `/admin/models` → Refresh button visible next to each installed model
- Click Refresh → confirm dialog → success message shown in model table
- Navigate to `/admin/models/basic-pkm` → Refresh button visible in header
- Navigate to `/admin/ops-log` → entry with `model.refresh` activity type exists

## Observability Impact

- Signals added: `model.refresh` activity type in ops log (both success and failure)
- How a future agent inspects this: `/admin/ops-log` filtered by `model.refresh`; response includes `graphs_refreshed` list on success or `error_message` on failure
- Failure state exposed: Error message in htmx response + ops log entry with `status="failed"`

## Inputs

- `backend/app/services/models.py` — `RefreshResult` and `refresh_artifacts()` from T01
- `backend/app/admin/router.py` — `admin_models_install()` and `admin_models_remove()` as exact patterns to follow
- `backend/app/templates/admin/models.html` — existing model list table with Inference/Remove buttons
- `backend/app/templates/admin/model_detail.html` — existing model detail header with version pill

## Expected Output

- `backend/app/admin/router.py` — new `POST /admin/models/{model_id}/refresh-artifacts` route
- `backend/app/templates/admin/models.html` — "Refresh" button in actions column
- `backend/app/templates/admin/model_detail.html` — "Refresh" button in header
