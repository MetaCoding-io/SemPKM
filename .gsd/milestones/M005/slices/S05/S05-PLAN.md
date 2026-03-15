# S05: Model Schema Refresh

**Goal:** A `refresh_artifacts` endpoint updates a model's shapes/views/ontology/rules graphs from disk without touching user data or requiring uninstall. Admin UI has a "Refresh" button on installed models.

**Demo:** Owner clicks "Refresh" on the basic-pkm model in the admin UI → shapes/views/ontology/rules graphs are reloaded from disk → ViewSpec cache invalidated → ops log entry created → model continues working with updated artifacts, all user data untouched.

## Must-Haves

- `ModelService.refresh_artifacts(model_id)` clears and reloads ontology, shapes, views, and rules graphs in a single transaction — NOT seed graph
- Transaction rollback on partial failure preserves old graphs
- Error handling for model-not-installed and model-dir-not-on-disk
- `POST /admin/models/{model_id}/refresh-artifacts` endpoint requiring owner role
- ViewSpec cache invalidation after successful refresh
- Ops log integration (fire-and-forget, D082)
- "Refresh" button on both model list table and model detail page header
- Unit tests covering happy path, missing model, missing disk dir, and transaction rollback

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (browser verification of admin UI button)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_model_refresh.py -v` — all unit tests pass
- Browser: navigate to admin models page → "Refresh" button visible → click → success message shown → ops log has entry

## Observability / Diagnostics

- Runtime signals: ops log `prov:Activity` with `activity_type="model.refresh"` for every refresh attempt (success/failure)
- Inspection surfaces: Admin ops log page at `/admin/ops-log`; filter by `model.refresh`
- Failure visibility: Error message returned in htmx response; ops log entry with `status="failed"` and `error_message`

## Integration Closure

- Upstream surfaces consumed: `ModelService`, `ModelGraphs`, `load_archive()`, `parse_manifest()`, `_build_insert_data_sparql()`, `is_model_installed()`, `OperationsLogService.log_activity()`, `ViewSpecService.invalidate_cache()`
- New wiring introduced in this slice: `POST /admin/models/{model_id}/refresh-artifacts` route in admin router, "Refresh" buttons in 2 templates
- What remains before the milestone is truly usable end-to-end: S06/S07/S08 (design docs), S09 (E2E tests)

## Tasks

- [x] **T01: Implement ModelService.refresh_artifacts() with unit tests** `est:45m`
  - Why: Core service logic — clear 4 artifact graphs (not seed), reload from disk, INSERT DATA in transaction. Must be tested before wiring into the router.
  - Files: `backend/app/services/models.py`, `backend/tests/test_model_refresh.py`
  - Do: Add `RefreshResult` dataclass and `refresh_artifacts(model_id)` async method to `ModelService`. Verify model is installed via `is_model_installed()`. Locate model dir at `/app/models/{model_id}/`. Parse manifest, load archive. Begin transaction, CLEAR SILENT the 4 artifact graph IRIs (ontology, shapes, views, rules — NOT seed), INSERT DATA for each non-empty graph, commit. On any failure, rollback transaction. Return `RefreshResult` with success/graphs_refreshed/errors. Write unit tests with mock triplestore covering: happy path (4 graphs refreshed), model not installed, model dir missing from disk, transaction rollback on INSERT failure.
  - Verify: `cd backend && python -m pytest tests/test_model_refresh.py -v`
  - Done when: All unit tests pass, `refresh_artifacts()` correctly skips seed graph in both CLEAR and INSERT phases

- [x] **T02: Add refresh-artifacts admin endpoint and UI buttons** `est:30m`
  - Why: Wire the service method into the admin router with htmx buttons, ops log, and cache invalidation — following the exact patterns from `admin_models_install()` and `admin_models_remove()`.
  - Files: `backend/app/admin/router.py`, `backend/app/templates/admin/models.html`, `backend/app/templates/admin/model_detail.html`
  - Do: Add `POST /admin/models/{model_id}/refresh-artifacts` route to admin router requiring owner role. Call `model_service.refresh_artifacts(model_id)`. On success: invalidate ViewSpec cache, log `model.refresh` to ops log (fire-and-forget, D082), return updated model table partial with success message. On failure: log failed `model.refresh` to ops log, return model table with error message. Add "Refresh" button to model list table (next to Inference/Remove). Add "Refresh" button to model detail header (next to version pill). Both use `hx-post` targeting `#model-table` (list) or appropriate target (detail), with `hx-confirm` for safety.
  - Verify: Start Docker stack, navigate to admin models page, verify Refresh button is visible next to each model, click it and confirm success message appears. Check ops log shows the entry.
  - Done when: Refresh button works on both model list and model detail pages; ops log entry created; ViewSpec cache invalidated

## Files Likely Touched

- `backend/app/services/models.py`
- `backend/tests/test_model_refresh.py`
- `backend/app/admin/router.py`
- `backend/app/templates/admin/models.html`
- `backend/app/templates/admin/model_detail.html`
