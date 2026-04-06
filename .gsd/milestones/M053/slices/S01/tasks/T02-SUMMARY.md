---
id: T02
parent: S01
milestone: M053
key_files:
  - backend/app/templates/admin/models.html
  - frontend/static/css/style.css
key_decisions:
  - Moved available-models grid inside model_table Jinja2 block so htmx partial swaps update both sections
  - Original install form collapsed into details element as advanced fallback
duration: 
verification_result: passed
completed_at: 2026-04-06T03:09:03.593Z
blocker_discovered: false
---

# T02: Added responsive card grid showing discoverable bundled models with one-click install, replacing the text-input form as the primary install path

**Added responsive card grid showing discoverable bundled models with one-click install, replacing the text-input form as the primary install path**

## What Happened

Restructured the admin Mental Models template to display uninstalled bundled models as styled cards in a responsive grid. Each card shows name, version badge, description (line-clamped), and type/icon counts. Install button triggers hx-post with model path as hidden input. Moved available-models section inside the model_table Jinja2 block so htmx partial swaps update both sections on install/remove. Original text-input install form collapsed into a details element as advanced fallback. CSS follows upper-ontology-card pattern with theme tokens and color-mix() for decorative tints.

## Verification

Template parse check passed. Block structure verified — model_table block contains available-models-grid, install-path-details, and sparql-results table. Task plan rg verification command passed. No hardcoded colors in new CSS.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'available-models-grid' backend/app/templates/admin/models.html && rg 'available-model-card' frontend/static/css/style.css && echo 'PASS'` | 0 | ✅ pass | 500ms |
| 2 | `cd backend && .venv/bin/python -c "from jinja2 import ...; env.get_template('admin/models.html'); print('OK')"` | 0 | ✅ pass | 1000ms |
| 3 | `Block structure assertions (all sections inside model_table block)` | 0 | ✅ pass | 500ms |
| 4 | `rg hardcoded colors in new CSS | wc -l → 0` | 0 | ✅ pass | 300ms |

## Deviations

Expanded model_table block to encompass both available and installed sections instead of creating a separate wrapper div. Per-card hx-indicator uses htmx relative selector instead of global spinner.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/admin/models.html`
- `frontend/static/css/style.css`
