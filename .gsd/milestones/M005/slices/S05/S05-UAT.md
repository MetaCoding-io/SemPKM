# S05: Model Schema Refresh — UAT

**Milestone:** M005
**Written:** 2026-03-14

## UAT Type

- UAT mode: mixed (artifact-driven unit tests + live-runtime browser verification)
- Why this mode is sufficient: Unit tests verify service logic with mocked triplestore; browser verification confirms admin UI buttons, htmx responses, and ops log integration in the running stack

## Preconditions

- Docker stack running: `docker compose up -d` (api, triplestore, frontend all healthy)
- At least one model installed (basic-pkm is the default)
- Logged in as owner role (only owner can access admin pages and trigger refresh)

## Smoke Test

Navigate to `/admin/models` → confirm "Refresh" button (blue) is visible in the Actions column for the installed model → click it → confirm dialog appears → dismiss or accept.

## Test Cases

### 1. Refresh button visible on model list page

1. Navigate to `/admin/models`
2. Look at the installed model row (e.g. "Basic PKM") in the Actions column
3. **Expected:** Three action buttons visible in order: "Inference" (yellow/warning), "Refresh" (blue/info), "Remove" (red/danger)

### 2. Refresh button visible on model detail page

1. Click the model name link (e.g. "Basic PKM") to navigate to `/admin/models/basic-pkm`
2. Look at the model header area, next to the version pill (e.g. "v1.3.0")
3. **Expected:** "Refresh" button (blue/teal) is visible after the version pill

### 3. Refresh confirm dialog on list page

1. On `/admin/models`, click the "Refresh" button for the installed model
2. **Expected:** Browser native confirm dialog appears with text: "Refresh artifacts for Basic PKM? This will reload shapes, views, ontology, and rules from disk."
3. Click "Cancel"
4. **Expected:** No changes made, model table unchanged

### 4. Refresh confirm dialog on detail page

1. On `/admin/models/basic-pkm`, click the "Refresh" button
2. **Expected:** Browser native confirm dialog appears with similar text
3. Click "Cancel"
4. **Expected:** No changes made, detail page unchanged

### 5. Refresh execution creates ops log entry

1. On `/admin/models`, click the "Refresh" button and confirm
2. Wait for the htmx response (model table updates)
3. Navigate to `/admin/ops-log`
4. **Expected:** A `model.refresh` entry appears at the top of the log with:
   - Activity label containing "Refresh artifacts for model 'basic-pkm'"
   - Type badge showing `model.refresh`
   - Actor showing the current user's IRI
   - Status showing either `✓ completed` (success) or `✗ failed` (error)

### 6. Ops log filter for model.refresh

1. Navigate to `/admin/ops-log`
2. Open the "Filter by type" dropdown
3. **Expected:** "Model Refresh" option is available in the dropdown
4. Select "Model Refresh"
5. **Expected:** Only `model.refresh` entries are shown

### 7. Refresh error handling (expected with current basic-pkm archive)

1. On `/admin/models`, click "Refresh" for basic-pkm and confirm
2. **Expected:** An error message box appears in the model table area with red/danger styling, containing the error description (JSON parsing error from archive loader)
3. **Expected:** Model remains installed and functional — no data lost

### 8. Unit tests pass

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_model_refresh.py -v`
2. **Expected:** 21/21 tests pass:
   - `TestRefreshHappyPath` (7 tests): success result, 4 graphs refreshed, CLEAR/INSERT counts, transaction commit, empty/None rules handling
   - `TestSeedExclusion` (3 tests): seed graph never cleared, never inserted, registry never touched
   - `TestModelNotInstalled` (2 tests): failure result, no transaction started
   - `TestModelDirMissing` (2 tests): failure result, no transaction started
   - `TestTransactionRollback` (3 tests): rollback on INSERT failure, CLEAR failure, rollback failure
   - `TestLoadingErrors` (2 tests): manifest parse error, archive load error
   - `TestRefreshResultDataclass` (2 tests): default values, field assignment

### 9. Owner-only access enforcement

1. Log in as a member role user
2. Try to access `/admin/models`
3. **Expected:** Access Denied page (403) — member cannot reach admin pages
4. Try to POST to `/admin/models/basic-pkm/refresh-artifacts` directly (e.g. via curl without owner session)
5. **Expected:** 403 Forbidden response

## Edge Cases

### Model not installed

1. If somehow a model directory exists but the model is not registered as installed in the triplestore
2. **Expected:** `refresh_artifacts()` returns failure with "not installed" error message
3. Covered by `TestModelNotInstalled` unit tests

### Model directory missing from disk

1. If a model is registered as installed but the model directory has been deleted from the filesystem
2. **Expected:** `refresh_artifacts()` returns failure with "not found on disk" error message
3. Covered by `TestModelDirMissing` unit tests

### Transaction failure mid-refresh

1. If the triplestore fails during INSERT DATA after CLEAR SILENT has already run
2. **Expected:** Transaction is rolled back, preserving the old graph state
3. Covered by `TestTransactionRollback` unit tests

### Seed graph protection

1. During any refresh operation
2. **Expected:** The seed graph (`urn:sempkm:model:{id}:seed`) is never cleared or modified — only ontology, shapes, views, and rules graphs are touched
3. Covered by `TestSeedExclusion` unit tests

## Failure Signals

- "Refresh" button missing from model list or detail page — CSS or template issue
- Refresh click produces no response — htmx routing or endpoint not wired
- Ops log has no `model.refresh` entry after clicking Refresh — ops log integration broken
- "Model Refresh" missing from ops log filter dropdown — `OPS_LOG_ACTIVITY_TYPES` not updated
- Unit tests fail — service logic regression
- Model becomes unusable after refresh — transaction rollback not working (critical)

## Requirements Proved By This UAT

- MIG-01 — `refresh_artifacts` endpoint updates shapes/views/ontology/rules graphs without touching user data; admin UI has Refresh button; ops log records activity; ViewSpec cache invalidated

## Not Proven By This UAT

- End-to-end successful refresh with reloaded graph content — blocked by pre-existing archive parsing issue with basic-pkm model format
- ViewSpec cache invalidation effect on actual view rendering — requires a model with changed views to observe
- E2E Playwright test coverage — deferred to S09

## Notes for Tester

- The current basic-pkm archive has a JSON parsing error that causes the refresh to fail at runtime. This is expected and pre-existing (not introduced by S05). The important thing to verify is that the error is handled gracefully: error message displayed, ops log entry created with failed status, model still functional.
- The "Refresh" button on the detail page targets `#app-content` and re-renders the full detail view. If it instead shows the model list table, that indicates the HX-Target routing is broken.
- All 21 unit tests use mocked triplestore calls, so they don't need Docker to run. Use the local venv: `cd backend && .venv/bin/python -m pytest tests/test_model_refresh.py -v`
