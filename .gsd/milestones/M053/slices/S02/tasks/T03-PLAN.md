---
estimated_steps: 45
estimated_files: 7
skills_used: []
---

# T03: Wire admin endpoints, marketplace UI, model path resolution, and startup integration

Add admin endpoints for marketplace catalog and install, wire `MarketplaceRegistryService` into app startup, update model path resolution call sites, and extend the admin models template with a Browse Marketplace section.

## Steps

1. **Startup wiring** in `backend/app/main.py`:
   - Import `MarketplaceRegistryService` from `app.services.marketplace`
   - After model_service creation, create `MarketplaceRegistryService(settings.marketplace_registry_url, Path(settings.marketplace_models_dir))`
   - Store on `app.state.registry_service`
   - Ensure `Path(settings.marketplace_models_dir)` directory exists (`os.makedirs(..., exist_ok=True)`)

2. **Model path resolution** — update 3 critical call sites to search both directories:
   - `backend/app/services/models.py` line ~616 in `refresh_artifacts()`: replace `Path(f"/app/models/{model_id}")` with `resolve_model_dir(model_id)` from `app.models.paths`. If None, return error.
   - `backend/app/admin/router.py` `_load_entailment_defaults()` line ~1074: replace `os.path.join("/app/models", model_id, ...)` with `resolve_model_dir(model_id)` lookup. If None, return defaults.
   - `backend/app/services/icons.py` `IconService._build_cache()`: update to scan BOTH `/app/models/` and settings `marketplace_models_dir`. Accept a list of model directories or add a second scan loop.

3. **Admin endpoints** in `backend/app/admin/router.py`:
   - Add `GET /admin/models/marketplace` endpoint that fetches catalog from `request.app.state.registry_service`, cross-references with installed model IDs, renders a marketplace partial template
   - Add `POST /admin/models/marketplace-install` endpoint with `model_id: str = Form(...)` that calls `registry_service.download_and_install(model_id, model_service, user.id)`, returns updated model table partial. On success, invalidate ViewSpec cache. On failure, return error in context.
   - Both endpoints require `owner` role

4. **Admin template** `backend/app/templates/admin/models.html`:
   - Add a "Browse Marketplace" section between the Available Models grid and Installed Models table
   - Use htmx lazy loading: `<div hx-get="/admin/models/marketplace" hx-trigger="load" hx-swap="innerHTML">Loading marketplace…</div>`
   - Create marketplace partial template at `backend/app/templates/admin/_marketplace.html` that renders marketplace model cards:
     - Card grid using same `.available-model-card` CSS pattern from S01
     - Each card shows: name, version badge, description, size badge, tag pills
     - Install button: htmx POST to `/admin/models/marketplace-install` with hidden model_id input, `hx-target="#model-table"`, `hx-indicator` for loading state (R007)
     - "Already installed" badge if model_id matches an installed model (R003/R008)
   - Show error message when registry is unreachable: "Marketplace unavailable. Check your internet connection."

5. **CSS additions** in `frontend/static/css/style.css`:
   - Add marketplace-specific badge styles (size badge, tag pills) using theme tokens and `color-mix()` per project convention
   - Reuse the `.available-model-card` and `.available-models-grid` classes from S01 for consistency

6. **Verify** the template renders without Jinja2 errors and endpoints exist in the router

## Must-Haves

- [x] `MarketplaceRegistryService` created at startup and stored on `app.state.registry_service`
- [x] `/app/data/models/` directory ensured to exist at startup
- [x] `refresh_artifacts()` finds models in both `/app/models/` and `/app/data/models/`
- [x] `_load_entailment_defaults()` finds models in both directories
- [x] `IconService` scans both model directories
- [x] `GET /admin/models/marketplace` returns marketplace cards from registry
- [x] `POST /admin/models/marketplace-install` downloads, verifies, extracts, installs model
- [x] Install button shows loading indicator during operation (R007)
- [x] Already-installed models show badge instead of install button (R003/R008)
- [x] Registry failure shows graceful error message, does not crash (R006)
- [x] Template uses theme tokens, no hardcoded hex values

## Verification

- `cd backend && python -c "from app.admin.router import router; from app.services.marketplace import MarketplaceRegistryService; from app.models.paths import resolve_model_dir; print('imports OK')"` — imports succeed
- `cd backend && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('app/templates')); env.get_template('admin/models.html'); env.get_template('admin/_marketplace.html'); print('templates OK')"` — templates parse
- `rg 'resolve_model_dir' backend/app/services/models.py backend/app/admin/router.py` — confirms call sites updated
- `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/style.css | grep -v 'var(' | wc -l` — zero hardcoded hex values outside theme references

## Inputs

- `backend/app/services/marketplace.py`
- `backend/app/security/tar_validator.py`
- `backend/app/models/paths.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/admin/router.py`
- `backend/app/services/models.py`
- `backend/app/services/icons.py`
- `backend/app/templates/admin/models.html`
- `frontend/static/css/style.css`

## Expected Output

- `backend/app/main.py`
- `backend/app/admin/router.py`
- `backend/app/services/models.py`
- `backend/app/services/icons.py`
- `backend/app/templates/admin/models.html`
- `backend/app/templates/admin/_marketplace.html`
- `frontend/static/css/style.css`

## Verification

cd backend && python -c "from app.admin.router import router; from app.services.marketplace import MarketplaceRegistryService; from app.models.paths import resolve_model_dir; print('imports OK')" && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('app/templates')); env.get_template('admin/models.html'); env.get_template('admin/_marketplace.html'); print('templates OK')"
