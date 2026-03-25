---
estimated_steps: 13
estimated_files: 3
skills_used: []
---

# T01: Add authentication to app endpoints + setup guard + startup warnings

1. Add `user: User = Depends(get_current_user)` to all 6 unprotected endpoints in browser/apps.py:
   - GET /browser/apps/explorer
   - GET /browser/apps/{app_id}/page/{page_id}
   - GET /browser/apps/right-pane-sections
   - GET /browser/apps/views/explorer
   - GET /browser/apps/{app_id}/view/{view_id}
   - GET /browser/apps/commands

2. Guard setup endpoint: In backend/app/api/setup_routes.py, add a check that setup_mode is active before allowing POST /api/setup/configure-instance. Return 403 if not in setup mode and data already exists.

3. Add startup warnings:
   - When demo_mode=True and APP_BASE_URL is non-localhost: log WARNING
   - When cookie_secure=False and APP_BASE_URL starts with https:// or is non-localhost: log WARNING
   - Add these checks to the lifespan function in main.py

Unit tests: verify unauthenticated requests to /browser/apps/explorer return 401.

## Inputs

- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md`

## Expected Output

- `backend/app/browser/apps.py`
- `backend/app/api/setup_routes.py`
- `backend/app/main.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60
