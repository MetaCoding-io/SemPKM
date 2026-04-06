---
estimated_steps: 17
estimated_files: 2
skills_used: []
---

# T01: Add bundled-model discovery to admin models route

Add a helper function that scans /app/models/ for directories containing valid manifest.yaml files, parses each manifest, cross-references against already-installed models, and returns the available (not-yet-installed) models as a list of dicts. Wire this into the admin_models() route so the template receives both `models` (installed) and `available_models` (discoverable, not installed). Also pass available_models context in admin_models_install() and admin_models_remove() so the available section stays current after install/remove operations.

Steps:
1. Read `backend/app/admin/router.py` — the admin_models() route and admin_models_install() route
2. Read `backend/app/models/manifest.py` — parse_manifest() function
3. Add a `scan_available_models(models_dir: str, installed_ids: set[str]) -> list[dict]` function in `backend/app/admin/router.py` that:
   - Iterates subdirectories of models_dir
   - For each, tries parse_manifest(dir) wrapped in try/except (skip invalid manifests)
   - Filters out any model whose modelId is in installed_ids
   - Returns list of dicts: {model_id, name, description, version, path, type_count, icon_count}
   - type_count = count of icons with distinct types in manifest (proxy for number of types)
4. In admin_models(), after listing installed models, call scan_available_models('/app/models', {m.model_id for m in models}) and add the result to the template context as `available_models`
5. In admin_models_install() — after a successful install, rescan available models so the htmx partial swap shows the updated state. Same for admin_models_remove() — a removed model should reappear in the available list.
6. Add structured logging: `logger.info('Scanned %s: found %d available models', models_dir, len(available))` at the end of the scan function

Constraints:
- The scan function must be tolerant of malformed manifests (try/except around parse_manifest, log warning, continue)
- Must not import anything new — parse_manifest is already importable from app.models.manifest
- The /app/models path must not be hardcoded deep in the function — pass it as a parameter for testability

## Inputs

- ``backend/app/admin/router.py` — existing admin_models route to modify`
- ``backend/app/models/manifest.py` — parse_manifest function to reuse`

## Expected Output

- ``backend/app/admin/router.py` — updated with scan_available_models() function and modified admin_models/install/remove routes`

## Verification

cd backend && python -c "from app.admin.router import scan_available_models; print('import OK')" && echo 'PASS'
