---
estimated_steps: 5
estimated_files: 3
---

# T02: Create Jinja2 asset_url filter with dev/prod mode and unit tests

**Slice:** S01 — Build Pipeline & Local Vendoring
**Milestone:** M029

## Description

Create the Python-side bridge between the build output (manifest.json) and Jinja2 templates. The `asset_url` filter resolves logical asset names (e.g., "workspace.js") to either content-hashed production paths (/assets/workspace-a1b2c3d4.min.js) or original dev paths (/js/workspace.js), depending on whether manifest.json exists. This implements decision D270 (JSON manifest + Jinja2 filter) and D275 (dev/prod path divergence via filter mode).

## Steps

1. Create `backend/app/template_helpers.py` with:

   ```python
   """Jinja2 template helpers for asset URL resolution.
   
   In production (Docker build): manifest.json maps logical names to content-hashed filenames.
   In development (volume mounts): no manifest exists, paths return original dev locations.
   
   Decision D270: JSON manifest + Jinja2 filter
   Decision D275: manifest file presence is the dev/prod signal
   """
   import json
   import logging
   import os
   from pathlib import Path
   
   logger = logging.getLogger(__name__)
   
   # Default path where the multi-stage Docker build places the manifest
   _MANIFEST_PATH = os.environ.get(
       "ASSET_MANIFEST_PATH",
       "/usr/share/nginx/html/assets/manifest.json"
   )
   
   _manifest: dict[str, str] | None = None
   _manifest_loaded = False
   ```

   Implement `_load_manifest()` that:
   - Reads from `_MANIFEST_PATH`
   - Returns dict on success, None on FileNotFoundError
   - Logs warning on JSON parse errors
   - Sets `_manifest_loaded = True` to avoid repeated file reads

   Implement `asset_url(name: str) -> str` filter:
   - If manifest loaded and name is in manifest: return `/assets/{manifest[name]}`
   - Else for `.js` files: return `/js/{name}`
   - Else for `.css` files: return `/css/{name}`
   - Else: return `/{name}` (fallback for other extensions)

   Implement `is_asset_manifest_available() -> bool` that returns True if manifest was successfully loaded.

   Implement `init_template_helpers(app)` function that:
   - Calls `_load_manifest()`
   - Registers `asset_url` as a Jinja2 filter on `app.state.templates.env`
   - Registers `asset_manifest_available` as a Jinja2 global

2. Wire into `backend/app/main.py`:
   - After the line `templates.env.filters["compact_iri"] = _compact_iri` (approximately line 475), add:
     ```python
     from app.template_helpers import init_template_helpers
     init_template_helpers(app)
     ```

3. Create `backend/tests/test_template_helpers.py` with unit tests:
   - **test_asset_url_with_manifest**: mock manifest dict, verify `asset_url("workspace.js")` returns `/assets/workspace-abc123.min.js`
   - **test_asset_url_without_manifest**: no manifest, verify `asset_url("workspace.js")` returns `/js/workspace.js`
   - **test_asset_url_css_without_manifest**: no manifest, verify `asset_url("workspace.css")` returns `/css/workspace.css`
   - **test_asset_url_missing_key_in_manifest**: manifest loaded but key not present, verify returns dev-mode fallback path
   - **test_asset_manifest_available_true**: manifest loaded, verify `is_asset_manifest_available()` returns True
   - **test_asset_manifest_available_false**: no manifest, verify returns False
   - **test_load_manifest_valid_json**: write temp manifest file, verify loaded correctly
   - **test_load_manifest_file_not_found**: non-existent path, verify returns None gracefully
   - **test_load_manifest_invalid_json**: write invalid JSON, verify returns None with logged warning

4. All tests must use monkeypatch/tmp_path fixtures to avoid filesystem side effects. Mock `_MANIFEST_PATH` and `_manifest` module-level vars for isolated testing.

5. Ensure the filter gracefully handles edge cases: name is None, name is empty string, name has no extension.

## Must-Haves

- [ ] `asset_url` filter resolves via manifest in production mode
- [ ] `asset_url` filter returns original dev paths when no manifest exists
- [ ] `asset_manifest_available` template global is True when manifest loaded, False otherwise
- [ ] Filter registered in main.py and usable in Jinja2 templates as `{{ 'name.js' | asset_url }}`
- [ ] Unit tests cover both modes + edge cases
- [ ] ASSET_MANIFEST_PATH env var allows override (useful for testing)

## Verification

- `cd backend && python -m pytest tests/test_template_helpers.py -v` — all tests pass
- `cd backend && python -c "from app.template_helpers import asset_url; print(asset_url('workspace.js'))"` — prints `/js/workspace.js` (no manifest in dev)
- LSP diagnostics: `lsp diagnostics backend/app/template_helpers.py` — no errors

## Inputs

- Decision D270: JSON manifest + Jinja2 filter
- Decision D275: manifest file presence = dev/prod signal
- `backend/app/main.py` lines ~440-475 — existing Jinja2 filter registration pattern
- T01 output: understanding of manifest.json structure (keys are logical names like "workspace.js", values are hashed filenames like "workspace-abc123.min.js")

## Expected Output

- `backend/app/template_helpers.py` — complete module with asset_url filter, manifest loading, and init function
- `backend/app/main.py` — modified to call `init_template_helpers(app)`
- `backend/tests/test_template_helpers.py` — ≥8 unit tests covering both modes + edge cases
