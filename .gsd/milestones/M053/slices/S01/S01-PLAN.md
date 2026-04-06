# S01: Auto-Discover Bundled Models

**Goal:** Admin → Mental Models page auto-discovers bundled models from /app/models/ and displays them as installable cards with one-click install.
**Demo:** After this: Admin → Mental Models shows available bundled models as clickable cards. Click Install on one → model installs without typing a path.

## Tasks
- [x] **T01: Added scan_available_models() function that discovers bundled Mental Models from /app/models/ and wired it into all admin model routes** — Add a helper function that scans /app/models/ for directories containing valid manifest.yaml files, parses each manifest, cross-references against already-installed models, and returns the available (not-yet-installed) models as a list of dicts. Wire this into the admin_models() route so the template receives both `models` (installed) and `available_models` (discoverable, not installed). Also pass available_models context in admin_models_install() and admin_models_remove() so the available section stays current after install/remove operations.

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
  - Estimate: 30m
  - Files: backend/app/admin/router.py, backend/app/models/manifest.py
  - Verify: cd backend && python -c "from app.admin.router import scan_available_models; print('import OK')" && echo 'PASS'
- [x] **T02: Added responsive card grid showing discoverable bundled models with one-click install, replacing the text-input form as the primary install path** — Add an 'Available Models' section to the admin models template showing discoverable bundled models as styled cards. Each card displays model name, description, version, and type count from the manifest. An Install button on each card triggers installation via htmx POST to the existing /admin/models/install endpoint with the model path.

Steps:
1. Read `backend/app/templates/admin/models.html` — current template structure
2. Read `frontend/static/css/style.css` — existing admin and upper-ontology card styles (lines 415-470)
3. Add an 'Available Models' section between the install form and the installed models table:
   - Section header: `<h3 class="section-label">Available Models</h3>`
   - Grid container: `<div class="available-models-grid">`
   - For each model in available_models: a card div with:
     - Model name (h4), version badge, description (p), type count stat
     - Install button that does `hx-post="/admin/models/install"` with hidden input `name="path" value="/app/models/{{model.model_id}}"`
     - The button should use `hx-target="#model-table"` and `hx-swap="outerHTML"` to match existing install behavior
     - Add hx-indicator for loading state on the button
   - Empty state when available_models is empty: 'All bundled models are installed.'
4. Move the available models section to render INSIDE the `#model-table` div (or create a wrapper that includes both available + installed sections) so that after install/remove htmx swaps, both sections update correctly.
   - Actually, the simplest approach: keep the available section OUTSIDE #model-table but use `hx-target="body"` with full page swap — NO. Instead, wrap the available-models section + install form + model-table into a single `#models-content` div that gets swapped on install/remove.
   - The existing model_table block returns `#model-table` div. Expand this block to include both available-models and installed-models so htmx partial swaps update both.
5. Add CSS to `frontend/static/css/style.css` in the admin section:
   - `.available-models-grid` — CSS grid, 1-3 columns responsive, gap
   - `.available-model-card` — border, border-radius, padding, hover shadow
   - `.available-model-card h4` — model name styling
   - `.available-model-card .model-version` — version badge
   - `.available-model-card .model-desc` — description, muted text, line-clamp
   - `.available-model-card .model-stats` — type count row
   - `.available-model-card .btn` — install button styling
   - All colors use theme tokens (var(--color-*)), not hardcoded values
6. Remove or hide the text input install form — the available-models cards replace it. Keep the form as a fallback wrapped in a `<details>` element with summary 'Install from path...' for advanced users who might need to specify a custom path.
7. Verify the install button works by checking that the htmx attributes match the existing form's POST behavior.

CSS note per CLAUDE.md: all colors must use theme tokens. Use `color-mix()` with theme primitives for decorative tints. Follow the existing `.upper-ontology-card` pattern for card styling consistency.

Lucide icons note per CLAUDE.md: if adding any Lucide icons to cards, size via CSS not inline styles, add `flex-shrink: 0` in flex containers.
  - Estimate: 45m
  - Files: backend/app/templates/admin/models.html, frontend/static/css/style.css
  - Verify: rg 'available-models-grid' backend/app/templates/admin/models.html && rg 'available-model-card' frontend/static/css/style.css && echo 'PASS'
