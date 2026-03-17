---
id: T03
parent: S03
milestone: M009
provides:
  - app_admin_router wired into FastAPI application via main.py
  - "Applications" nav-link in admin sidebar (owner-only)
  - "Applications" card on admin index page
key_files:
  - backend/app/main.py
  - backend/app/templates/components/_sidebar.html
  - backend/app/templates/admin/index.html
key_decisions:
  - Placed app_admin_router include immediately after admin_router (line 545), well before app_proxy_router (line 560), to prevent the proxy catch-all {path:path} from consuming /admin/apps/* URLs
patterns_established: []
observability_surfaces:
  - "Route ordering check: grep -n app_admin_router backend/app/main.py — verify it appears before app_proxy_router"
duration: 10min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: main.py wiring, sidebar nav, and admin index card

**Wired app_admin_router into FastAPI, added "Applications" sidebar link and admin index card.**

## What Happened

Three surgical edits:

1. **main.py** — Added `from app.apps.admin_router import app_admin_router` import (line 21) and `app.include_router(app_admin_router)` (line 545), placed between `admin_router` and `app_proxy_router` to ensure the proxy's catch-all `{path:path}` doesn't shadow `/admin/apps/*` routes.

2. **_sidebar.html** — Added "Applications" nav-link with `puzzle` Lucide icon inside the owner-only `{% if %}` block, after "Operations Log" and before `{% else %}`. Uses standard htmx pattern matching all other admin links.

3. **admin/index.html** — Added "Applications" card to `dashboard-cards` div after "Operations Log" card, with same htmx-based navigation pattern.

## Verification

- `grep -n "app_admin_router" backend/app/main.py` → line 21 (import) and line 545 (include_router) ✓
- `grep -c "Applications" backend/app/templates/components/_sidebar.html` → 2 ✓
- `grep -c "Applications" backend/app/templates/admin/index.html` → 2 ✓
- `python3 -c "import ast; ast.parse(open('backend/app/main.py').read())"` → Syntax OK ✓
- Router order: admin_router (544) → app_admin_router (545) → app_proxy_router (560) ✓

**Slice-level verifications (6/8 checked — pytest requires Docker):**
- `grep -c "location /app-static/" frontend/nginx.conf` → 1 ✓
- `grep -c "location /app/" frontend/nginx.conf` → 1 ✓
- `grep -c "./apps:/app/apps" docker-compose.yml` → 1 ✓
- `grep -c "Applications" backend/app/templates/components/_sidebar.html` → 2 ✓
- `grep -c "Applications" backend/app/templates/admin/index.html` → 2 ✓
- `grep -c "app_admin_router" backend/app/main.py` → 2 ✓
- `pytest tests/test_app_admin.py` — cannot run outside Docker (no virtualenv)
- `curl /admin/apps/nonexistent` → 404 — cannot test outside Docker

## Diagnostics

- Route ordering is the main diagnostic concern: if `app_admin_router` is registered after `app_proxy_router`, all `/admin/apps/*` requests silently get handled by the proxy catch-all instead of the admin endpoints
- Sidebar link visibility: only rendered inside `{% if user.role == 'owner' %}` block — if link is missing, check user role

## Deviations

First edit attempt on main.py matched an unintended location, creating a stray `asgi_dav_app)` line at the end of the file. Detected via syntax check and fixed immediately.

## Known Issues

None.

## Files Created/Modified

- `backend/app/main.py` — Added import and include_router for app_admin_router
- `backend/app/templates/components/_sidebar.html` — Added "Applications" nav-link in owner-only admin group
- `backend/app/templates/admin/index.html` — Added "Applications" card to dashboard-cards
