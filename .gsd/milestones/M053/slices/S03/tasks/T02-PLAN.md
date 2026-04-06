---
estimated_steps: 31
estimated_files: 4
skills_used: []
---

# T02: Add version badges, update button, and CSS to admin templates

## Description

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

## Inputs

- ``backend/app/admin/router.py` — T01 output: update_status dict passed in template contexts`
- ``backend/app/templates/admin/models.html` — existing installed models table`
- ``backend/app/templates/admin/_marketplace.html` — existing marketplace card partial`
- ``frontend/static/css/style.css` — existing marketplace CSS styles`
- ``frontend/static/css/theme.css` — theme token primitives for color-mix()`

## Expected Output

- ``backend/app/templates/admin/models.html` — version status column with badges and update button`
- ``backend/app/templates/admin/_marketplace.html` — update-available badge for outdated installed models`
- ``frontend/static/css/style.css` — version-badge CSS classes with theme tokens`

## Verification

cd backend && .venv/bin/python -c "from jinja2 import Environment, FileSystemLoader; env=Environment(loader=FileSystemLoader('app/templates')); env.get_template('admin/models.html'); env.get_template('admin/_marketplace.html'); print('ok')" && rg 'version-badge' frontend/static/css/style.css | head -3
