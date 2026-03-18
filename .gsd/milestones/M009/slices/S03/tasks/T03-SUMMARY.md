---
id: T03
parent: S03
milestone: M009
provides:
  - app_admin_router wired into FastAPI main.py (between admin_router and app_proxy_router)
  - "Applications" sidebar nav link in admin group (owner-only, puzzle icon)
  - "Applications" card on admin index page
key_files:
  - backend/app/main.py
  - backend/app/templates/components/_sidebar.html
  - backend/app/templates/admin/index.html
key_decisions:
  - Router ordering: app_admin_router placed immediately before app_proxy_router to prevent catch-all {path:path} from consuming /admin/apps/* URLs
patterns_established:
  - Sidebar nav link pattern: href + hx-get + hx-target="#app-content" + hx-swap="innerHTML" + hx-push-url="true" + lucide icon
observability_surfaces:
  - none (pure wiring — no new runtime behavior)
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: main.py wiring, sidebar nav, and admin index card

**Wired app_admin_router into main.py, added Applications sidebar nav link and admin index card to complete S03 admin portal integration**

## What Happened

Three edits across three files:

1. **main.py**: Added `from app.apps.admin_router import app_admin_router` import (line 20) and `app.include_router(app_admin_router)` (line 570) — placed immediately before `app_proxy_router` to prevent the proxy's catch-all `{path:path}` pattern from swallowing `/admin/apps/*` URLs.

2. **_sidebar.html**: Added "Applications" nav-link with `lucide:puzzle` icon inside the owner-only `{% if user.role == 'owner' %}` block, after "Operations Log" and before the `{% else %}` block. Uses the standard htmx pattern (`hx-get`, `hx-target="#app-content"`, `hx-push-url`).

3. **admin/index.html**: Added "Applications" card after the "Operations Log" card in the `dashboard-cards` div, with description text and htmx-enabled link.

Also fixed a pre-existing stray `asgi_dav_app)` line at the end of main.py that caused a SyntaxError.

## Verification

- `grep -n "app_admin_router" backend/app/main.py` → matches import (line 20) and include_router (line 570)
- `grep -n "Applications" backend/app/templates/components/_sidebar.html` → matches nav-link and label
- `grep -n "Applications" backend/app/templates/admin/index.html` → matches card heading and button
- `python3 -c "import ast; ast.parse(open('app/main.py').read()); print('Syntax OK')"` → passes
- Router ordering confirmed: `app_admin_router` at line 570, `app_proxy_router` at line 571
- All 33 test_app_admin.py tests pass in 1.4s

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "app_admin_router" backend/app/main.py` | 0 (count=2) | ✅ pass | <1s |
| 2 | `grep -c "Applications" backend/app/templates/components/_sidebar.html` | 0 (count=2) | ✅ pass | <1s |
| 3 | `grep -c "Applications" backend/app/templates/admin/index.html` | 0 (count=2) | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(...)"` | 0 | ✅ pass | <1s |
| 5 | `.venv/bin/pytest tests/test_app_admin.py -v` | 0 (33 passed) | ✅ pass | 1.4s |
| 6 | `grep -c "location /app-static/" frontend/nginx.conf` | 0 (count=1) | ✅ pass | <1s |
| 7 | `grep -c "location /app/" frontend/nginx.conf` | 0 (count=1) | ✅ pass | <1s |
| 8 | `grep -c "./apps:/app/apps" docker-compose.yml` | 0 (count=1) | ✅ pass | <1s |
| 9 | `grep -c "_copy_static_assets" backend/app/apps/manager.py` | 0 (count=2) | ✅ pass | <1s |

## Diagnostics

- **Router registration**: `grep -n "app_admin_router" backend/app/main.py` — must show both import and include_router
- **Route ordering**: `app_admin_router` must appear before `app_proxy_router` in the include sequence; otherwise the proxy catch-all swallows `/admin/apps/*` requests
- **Sidebar visibility**: "Applications" link only renders for `user.role == 'owner'` — check the `{% if %}` block in `_sidebar.html`

## Deviations

- Fixed pre-existing stray `asgi_dav_app)` line at end of `backend/app/main.py` that was not in the HEAD commit but present in the working tree — caused SyntaxError on import.

## Known Issues

None.

## Files Created/Modified

- `backend/app/main.py` — added import and include_router for app_admin_router; fixed stray syntax error
- `backend/app/templates/components/_sidebar.html` — added "Applications" nav-link in owner-only admin group
- `backend/app/templates/admin/index.html` — added "Applications" card in dashboard-cards grid
