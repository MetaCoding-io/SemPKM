---
estimated_steps: 3
estimated_files: 3
---

# T03: main.py wiring, sidebar nav, and admin index card

**Slice:** S03 — Admin Portal & Docker/nginx Integration
**Milestone:** M009

## Description

Wire the app admin router into the FastAPI application, add the "Applications" navigation entry to the admin sidebar, and add an "Applications" card to the admin index page.

## Steps

1. **Wire `app_admin_router` into `backend/app/main.py`:**
   - Add import: `from app.apps.admin_router import app_admin_router`
   - Add `app.include_router(app_admin_router)` AFTER `admin_router` (line 543) and BEFORE `app_proxy_router` (line 558). The admin router must come before the proxy router because the proxy has a catch-all `{path:path}` pattern that would consume `/admin/apps/*` URLs.
   - The include needs no prefix argument — the routes in `admin_router.py` already use full `/admin/apps` paths.

2. **Add "Applications" nav-link to `backend/app/templates/components/_sidebar.html`:**
   - Inside the Admin sidebar group's `sidebar-group-items` div, within the `{% if user is defined and user.role == 'owner' %}` block
   - Place it AFTER the "Operations Log" link (the last current owner-only link) and BEFORE the `{% else %}` block
   - Use this markup:
     ```html
     <a href="/admin/apps" class="nav-link" data-tooltip="Applications"
        hx-get="/admin/apps" hx-target="#app-content" hx-swap="innerHTML" hx-push-url="true">
         <i data-lucide="puzzle" class="nav-icon"></i>
         <span class="nav-label">Applications</span>
     </a>
     ```
   - Follows exact same pattern as Mental Models, Webhooks, and Operations Log links above it.

3. **Add "Applications" card to `backend/app/templates/admin/index.html`:**
   - Inside the `dashboard-cards` div, after the "Operations Log" card
   - Use this markup:
     ```html
     <div class="card">
         <h2>Applications</h2>
         <p>Install, monitor, and manage platform applications that extend SemPKM with custom functionality.</p>
         <a href="/admin/apps" class="btn btn-primary"
            hx-get="/admin/apps" hx-target="#app-content" hx-swap="innerHTML" hx-push-url="true">
             Manage Applications
         </a>
     </div>
     ```
   - Follows exact same pattern as the three existing cards.

## Must-Haves

- [ ] `app_admin_router` included in main.py between admin_router and app_proxy_router
- [ ] Sidebar shows "Applications" link in Admin group (owner-only)
- [ ] Admin index page shows "Applications" card

## Verification

- `grep "app_admin_router" backend/app/main.py` matches import and include_router
- `grep "Applications" backend/app/templates/components/_sidebar.html` matches
- `grep "Applications" backend/app/templates/admin/index.html` matches
- `cd backend && python -c "from app.main import app; print('OK')"` — import succeeds (proves router wiring doesn't break startup)

## Inputs

- `backend/app/apps/admin_router.py` — T01 output: `app_admin_router` APIRouter to import
- `backend/app/main.py` — router include order: `admin_router` at line 543, `app_proxy_router` at line 558, `browser_router` at line 559
- `backend/app/templates/components/_sidebar.html` — Admin group with owner-only links (Mental Models, Webhooks, Operations Log), then `{% else %}` block
- `backend/app/templates/admin/index.html` — `dashboard-cards` div with 3 existing cards (Mental Models, Webhooks, Operations Log)

## Expected Output

- `backend/app/main.py` — modified: import + include_router for app_admin_router
- `backend/app/templates/components/_sidebar.html` — modified: "Applications" nav-link added
- `backend/app/templates/admin/index.html` — modified: "Applications" card added

## Observability Impact

This task is pure wiring — no new runtime behavior. The admin router (T01) already has its own logging. What to check:

- **Router registration:** `grep -n "app_admin_router" backend/app/main.py` — must show both import and include_router lines
- **Route ordering:** `app_admin_router` must appear before `app_proxy_router` in the include sequence; otherwise the proxy catch-all `{path:path}` swallows `/admin/apps/*` requests (silent 404 or wrong handler)
- **Sidebar visibility:** "Applications" link only renders for `user.role == 'owner'` — guest/member users won't see it. If link is missing, check the Jinja `{% if %}` block in `_sidebar.html`
- **No new failure modes:** No new exceptions, logs, or error states introduced by this task
