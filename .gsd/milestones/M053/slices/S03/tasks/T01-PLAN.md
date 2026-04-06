---
estimated_steps: 45
estimated_files: 3
skills_used: []
---

# T01: Add check_updates() method and POST update endpoint with unit tests

## Description

Add version comparison logic to `MarketplaceRegistryService` and a safe model update endpoint to the admin router. The update flow must download and verify the new archive BEFORE uninstalling the old version to prevent data loss on download failure.

## Steps

1. **Add `check_updates()` to `MarketplaceRegistryService`** in `backend/app/services/marketplace.py`:
   - Accept `installed_models: list[InstalledModel]` parameter (import from `app.models.registry`)
   - Call `self.fetch_catalog()` (uses cache if warm)
   - For each installed model, find matching catalog entry by `model_id`
   - Compare versions using `packaging.version.Version` — wrap in try/except for malformed versions
   - Return `dict[str, dict]` mapping `model_id → {"installed_version": str, "latest_version": str, "has_update": bool}`
   - When marketplace is disabled, return empty dict
   - When catalog fetch fails (returns []), return empty dict

2. **Add POST `/admin/models/{model_id}/update` endpoint** in `backend/app/admin/router.py`:
   - Require `require_role("owner")`
   - Get `registry_service` from `request.app.state`
   - Fetch catalog, find entry for `model_id`
   - **Safe ordering**: download archive to tempdir → verify SHA-256 → validate tar → extract → confirm manifest.yaml exists → THEN `model_service.remove(model_id)` → `_cleanup_inference_on_uninstall(...)` → `model_service.install(extracted_dir)` → copy to `models_data_dir` → invalidate ViewSpec cache
   - Rather than duplicating `download_and_install()` logic, refactor by extracting a `_download_and_verify()` helper method that returns the validated extracted model directory path (without installing). Then the update endpoint calls: `_download_and_verify()` → `remove()` → `cleanup` → `install()` → persist. Alternatively, sequence the existing methods if refactoring would change too much tested code.
   - Log ops log entry with `activity_type="model.marketplace_update"`
   - Security audit log
   - Return updated model table partial via `templates_response`
   - On failure: return error context, log warning, ops log with status="failed"

3. **Add `update_status` to `admin_models()` and `admin_models_marketplace()` context** in `backend/app/admin/router.py`:
   - In `admin_models()`: call `registry_service.check_updates(models)` and pass result as `update_status` in context
   - In `admin_models_marketplace()`: same — pass `update_status` in context
   - Handle `registry_service` being None (marketplace not configured) — pass empty dict

4. **Add unit tests** in `backend/tests/test_marketplace_service.py`:
   - `TestCheckUpdates` class with tests:
     - `test_detects_update_available` — installed v1.0.0, registry v2.0.0 → `has_update: True`
     - `test_detects_up_to_date` — installed v2.0.0, registry v2.0.0 → `has_update: False`
     - `test_installed_newer_than_registry` — installed v3.0.0, registry v2.0.0 → `has_update: False`
     - `test_model_not_in_registry` — installed model not in catalog → not in result dict
     - `test_disabled_returns_empty` — disabled service → empty dict
     - `test_malformed_version_skipped` — registry entry with "invalid" version → skipped, no crash
     - `test_empty_catalog_returns_empty` — catalog fetch returns [] → empty dict

## Must-Haves

- [ ] `check_updates()` uses `packaging.version.Version` for comparison
- [ ] Update endpoint downloads and verifies BEFORE uninstalling
- [ ] Malformed version strings don't crash — caught with try/except
- [ ] `update_status` dict passed to both admin_models and marketplace template contexts
- [ ] At least 7 unit tests for check_updates
- [ ] Ops log and security audit for update actions

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_marketplace_service.py -v` — all tests pass including new TestCheckUpdates
- `cd backend && .venv/bin/python -c "from app.services.marketplace import MarketplaceRegistryService; print('import ok')"` — no import errors
- `rg 'check_updates' backend/app/services/marketplace.py backend/app/admin/router.py` — method exists and is called

## Inputs

- ``backend/app/services/marketplace.py` — existing MarketplaceRegistryService with fetch_catalog() and download_and_install()`
- ``backend/app/admin/router.py` — existing admin endpoints, _cleanup_inference_on_uninstall(), scan_available_models()`
- ``backend/tests/test_marketplace_service.py` — existing test helpers and patterns`
- ``backend/app/models/registry.py` — InstalledModel dataclass with model_id, version fields`

## Expected Output

- ``backend/app/services/marketplace.py` — check_updates() method added`
- ``backend/app/admin/router.py` — POST update endpoint, update_status in admin_models/marketplace contexts`
- ``backend/tests/test_marketplace_service.py` — TestCheckUpdates class with 7+ tests`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_marketplace_service.py -v && .venv/bin/python -c "from app.services.marketplace import MarketplaceRegistryService; print('ok')"
