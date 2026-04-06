---
estimated_steps: 29
estimated_files: 2
skills_used: []
---

# T02: Add available-models card grid UI and one-click install

Add an 'Available Models' section to the admin models template showing discoverable bundled models as styled cards. Each card displays model name, description, version, and type count from the manifest. An Install button on each card triggers installation via htmx POST to the existing /admin/models/install endpoint with the model path.

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

## Inputs

- ``backend/app/admin/router.py` — T01 output with available_models in template context`
- ``backend/app/templates/admin/models.html` — existing template to modify`
- ``frontend/static/css/style.css` — existing admin styles to extend`

## Expected Output

- ``backend/app/templates/admin/models.html` — updated with available-models card grid and one-click install buttons`
- ``frontend/static/css/style.css` — updated with available-model-card grid styles`

## Verification

rg 'available-models-grid' backend/app/templates/admin/models.html && rg 'available-model-card' frontend/static/css/style.css && echo 'PASS'
