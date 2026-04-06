---
id: T02
parent: S03
milestone: M053
key_files:
  - backend/app/templates/admin/models.html
  - backend/app/templates/admin/_marketplace.html
  - frontend/static/css/style.css
key_decisions:
  - Used --_color-green-500 instead of --_color-green-600 (only green primitive available in theme.css)
duration: 
verification_result: passed
completed_at: 2026-04-06T03:48:16.395Z
blocker_discovered: false
---

# T02: Added version status badges and htmx Update button to installed models table and marketplace cards

**Added version status badges and htmx Update button to installed models table and marketplace cards**

## What Happened

Wired the update_status context variable from T01's check_updates() into both admin templates. Added a Status column to models.html with green "Up to date" / amber "Update available: vX.Y.Z" badges and a conditional Update button with hx-post, hx-confirm, and loading indicator. Updated _marketplace.html to show update-available badges instead of static "✓ Installed" for outdated models. Added CSS using color-mix() with theme tokens — zero hardcoded hex values. Both templates degrade gracefully when update_status is empty.

## Verification

All 7 verification checks passed: templates parse without Jinja2 errors, zero hardcoded hex in style.css, version-badge classes exist in CSS and templates, update_status referenced in both templates, all 30 pytest tests pass, MarketplaceRegistryService imports cleanly, check_updates method exists and is called from router.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from jinja2 import Environment, FileSystemLoader; ..." (template parse)` | 0 | ✅ pass | 500ms |
| 2 | `rg '#[0-9a-fA-F]{3,8}' style.css | grep -v var( | wc -l` | 0 | ✅ pass | 200ms |
| 3 | `rg 'version-badge' frontend/static/css/style.css backend/app/templates/admin/models.html` | 0 | ✅ pass | 200ms |
| 4 | `rg 'update_status' backend/app/templates/admin/models.html backend/app/templates/admin/_marketplace.html` | 0 | ✅ pass | 200ms |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_marketplace_service.py -v` | 0 | ✅ pass | 820ms |
| 6 | `cd backend && .venv/bin/python -c "from app.services.marketplace import MarketplaceRegistryService; print('ok')"` | 0 | ✅ pass | 300ms |
| 7 | `rg 'check_updates' backend/app/services/marketplace.py backend/app/admin/router.py` | 0 | ✅ pass | 200ms |

## Deviations

Used --_color-green-500 instead of plan's --_color-green-600 (token doesn't exist in theme.css)

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/admin/models.html`
- `backend/app/templates/admin/_marketplace.html`
- `frontend/static/css/style.css`
