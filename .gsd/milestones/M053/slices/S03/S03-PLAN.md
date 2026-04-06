# S03: Version Checking + Update Notifications

**Goal:** Installed model cards show version status badges ("Up to date" / "Update available: vX.Y.Z") and an Update button that safely re-downloads and reinstalls the latest version from the marketplace registry.
**Demo:** After this: Admin → Mental Models shows 'Up to date' or 'Update available' badges on installed model cards. Click Update to re-download and reinstall the latest version.

## Tasks
- [x] **T01: Added check_updates() with packaging.version.Version comparison, a safe download-before-remove update endpoint, and 10 unit tests** — ## Description

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
  - Estimate: 45m
  - Files: backend/app/services/marketplace.py, backend/app/admin/router.py, backend/tests/test_marketplace_service.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_marketplace_service.py -v && .venv/bin/python -c "from app.services.marketplace import MarketplaceRegistryService; print('ok')"
- [x] **T02: Added version status badges and htmx Update button to installed models table and marketplace cards** — ## Description

Wire the `update_status` context variable into the installed models table and marketplace cards. Show version status badges and an Update button for models with available updates.

## Steps

1. **Update `backend/app/templates/admin/models.html`** — Installed Models table:
   - Add a "Status" column after "Version" in the table header
   - For each model row, check `update_status.get(model.model_id, {})` (the dict from T01)
   - If `has_update` is true: show amber badge `Update available: vX.Y.Z` + Update button
   - If `has_update` is false and entry exists: show green badge `Up to date`
   - If no entry (model not in registry, e.g. bundled-only): no badge
   - Update button: `<button hx-post="/admin/models/{{ model.model_id }}/update" hx-target="#model-table" hx-swap="outerHTML" hx-indicator="find .update-indicator" hx-confirm="Update {{ model.name }} to vX.Y.Z?">Update</button>` with loading indicator span

2. **Update `backend/app/templates/admin/_marketplace.html`** — Marketplace cards:
   - Change the installed badge logic: if `model.id in installed_ids` AND `update_status.get(model.id, {}).get('has_update')`, show "Update available" badge instead of "✓ Installed"
   - Pass `update_status` in the template context (already done by T01 in the marketplace endpoint)

3. **Add CSS** in `frontend/static/css/style.css`:
   - `.version-badge` base class (inline-block, font-size, padding, border-radius)
   - `.version-badge--uptodate` — uses `color-mix(in srgb, var(--_color-green-600) 15%, transparent)` background, green text
   - `.version-badge--update` — uses `color-mix(in srgb, var(--_color-amber-500) 15%, transparent)` background, amber text
   - `.update-indicator` for htmx loading state
   - Verify theme tokens exist in `frontend/static/css/theme.css` — `--_color-green-600` and `--_color-amber-500` should already be defined from prior work; if not, add them
   - Per CLAUDE.md: zero hardcoded hex, use `color-mix()` with theme tokens, `flex-shrink: 0` on any SVG icons in flex containers

## Must-Haves

- [ ] Installed models table shows version badges when update_status is available
- [ ] Update button with htmx POST, hx-confirm, and loading indicator
- [ ] Marketplace cards show "Update available" for outdated installed models
- [ ] CSS uses theme tokens with color-mix() — zero hardcoded hex values
- [ ] Graceful degradation: no badges when update_status is empty dict (marketplace disabled/unreachable)

## Verification

- `cd backend && .venv/bin/python -c "from jinja2 import Environment, FileSystemLoader; env=Environment(loader=FileSystemLoader('app/templates')); env.get_template('admin/models.html'); env.get_template('admin/_marketplace.html'); print('templates parse ok')"` — templates parse without syntax errors
- `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/style.css | grep -v 'var(' | grep -v '//' | wc -l` — returns 0 (no hardcoded hex outside var())
- `rg 'version-badge' frontend/static/css/style.css backend/app/templates/admin/models.html` — CSS classes exist and are used
- `rg 'update_status' backend/app/templates/admin/models.html backend/app/templates/admin/_marketplace.html` — context variable referenced in both templates
  - Estimate: 30m
  - Files: backend/app/templates/admin/models.html, backend/app/templates/admin/_marketplace.html, frontend/static/css/style.css, frontend/static/css/theme.css
  - Verify: cd backend && .venv/bin/python -c "from jinja2 import Environment, FileSystemLoader; env=Environment(loader=FileSystemLoader('app/templates')); env.get_template('admin/models.html'); env.get_template('admin/_marketplace.html'); print('ok')" && rg 'version-badge' frontend/static/css/style.css | head -3
